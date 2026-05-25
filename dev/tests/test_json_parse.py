"""验证 handle_reply.py 三层解析逻辑：JSON → 正则 → 文字分割。"""
import json
import re

VALID_EMOTIONS = {"neutral", "tender", "playful", "happy", "sad", "excited"}


def _strip_markdown(s):
    s = s.strip()
    if s.startswith("```"):
        chunks = s.split("```")
        s = chunks[-2] if len(chunks) >= 2 else s
        s = s.lstrip("json").strip()
    return s


def parse_llm_output(reply_raw, last_mood="平静"):
    thought = ""
    mood = last_mood
    voice_index = -1
    voice_emotion = "neutral"
    parts = []

    raw_clean = _strip_markdown(reply_raw)
    try:
        parsed = json.loads(raw_clean)
        parts = [p.strip() for p in parsed.get("messages", []) if p.strip()]
        thought = parsed.get("thought", "")
        mood = parsed.get("mood", last_mood) or last_mood
        voice_index = int(parsed.get("voice_index", -1))
        voice_emotion = parsed.get("voice_emotion", "neutral").lower()
        if voice_emotion not in VALID_EMOTIONS:
            voice_emotion = "neutral"
        return parts, thought, mood, voice_index, voice_emotion, "json"
    except (json.JSONDecodeError, ValueError, KeyError):
        try:
            msg_match = re.search(r'"messages"\s*:\s*\[([^\]]+)\]', raw_clean, re.DOTALL)
            if msg_match:
                parts = [p.strip().strip('"') for p in
                         re.findall(r'"((?:[^"\\]|\\.)*)"', msg_match.group(1)) if p.strip()]
            mood_match = re.search(r'"mood"\s*:\s*"([^"]+)"', raw_clean)
            if mood_match:
                mood = mood_match.group(1) or last_mood
            thought_match = re.search(r'"thought"\s*:\s*"([^"]+)"', raw_clean)
            if thought_match:
                thought = thought_match.group(1)
            if parts:
                return parts, thought, mood, voice_index, voice_emotion, "regex"
            raise ValueError("no messages")
        except Exception:
            candidates = [p.strip() for p in reply_raw.split("---") if p.strip()]
            parts = [p for p in candidates if not p.startswith("```")]
            if not parts and any(not c.startswith("```") for c in candidates):
                parts = candidates
            return parts, "", last_mood, -1, "neutral", "fallback"


# ── 正常路径 ─────────────────────────────────────────────────────────

def test_clean_json():
    r = json.dumps({"messages": ["周日了", "先去吃"], "thought": "...", "mood": "暗涌压着",
                    "voice_index": -1, "voice_emotion": "neutral"}, ensure_ascii=False)
    parts, thought, mood, vi, ve, mode = parse_llm_output(r, "散漫")
    assert mode == "json" and len(parts) == 2 and mood == "暗涌压着"
    print(f"[PASS] 正常JSON")

def test_markdown_wrapped():
    inner = json.dumps({"messages": ["薰吃了没"], "thought": ".", "mood": "挂念",
                        "voice_index": 0, "voice_emotion": "tender"}, ensure_ascii=False)
    parts, _, mood, vi, ve, mode = parse_llm_output(f"```json\n{inner}\n```")
    assert mode == "json" and vi == 0 and ve == "tender"
    print(f"[PASS] Markdown包裹JSON")

def test_missing_mood_inherits():
    r = json.dumps({"messages": ["好"], "thought": ".", "voice_index": -1}, ensure_ascii=False)
    _, _, mood, _, _, mode = parse_llm_output(r, "暗涌")
    assert mode == "json" and mood == "暗涌"
    print(f"[PASS] mood缺失沿用last_mood")

def test_invalid_emotion_corrected():
    r = json.dumps({"messages": ["嗯"], "thought": ".", "mood": "平",
                    "voice_index": 0, "voice_emotion": "seductive"}, ensure_ascii=False)
    _, _, _, _, ve, mode = parse_llm_output(r)
    assert mode == "json" and ve == "neutral"
    print(f"[PASS] 非法emotion→neutral")

def test_empty_messages_filtered():
    r = json.dumps({"messages": ["  ", "一句话", ""], "thought": ".", "mood": "平静",
                    "voice_index": -1, "voice_emotion": "neutral"}, ensure_ascii=False)
    parts, _, _, _, _, mode = parse_llm_output(r)
    assert mode == "json" and parts == ["一句话"]
    print(f"[PASS] 空消息过滤")

# ── 正则中间层（JSON 里 thought 含双引号导致解析失败）────────────────

def test_regex_fallback_unescaped_quotes():
    # 模拟 Claude 在 thought 里用了 ASCII 双引号
    raw = '{"messages": ["嗯"], "thought": "说到"嗯"让我停了一下", "mood": "有点在意", "voice_index": -1, "voice_emotion": "neutral"}'
    parts, thought, mood, _, _, mode = parse_llm_output(raw, "散漫")
    assert mode == "regex", f"expected regex, got {mode}"
    assert parts == ["嗯"], f"expected ['嗯'], got {parts}"
    assert mood == "有点在意"
    print(f"[PASS] 正则提取（thought含双引号）: parts={parts}, mood={mood}")

def test_regex_fallback_markdown_wrapped_bad_json():
    # 带代码块包裹且 JSON 非法
    raw = '```json\n{"messages": ["好"], "thought": "说到"好"停了", "mood": "温柔", "voice_index": -1}\n```'
    parts, _, mood, _, _, mode = parse_llm_output(raw, "平静")
    assert mode == "regex"
    assert parts == ["好"]
    assert mood == "温柔"
    print(f"[PASS] Markdown包裹+JSON非法→正则提取: mood={mood}")

# ── 硬 fallback ──────────────────────────────────────────────────────

def test_hard_fallback_text_split():
    r = "没什么\n---\n先去吃"
    parts, _, mood, _, _, mode = parse_llm_output(r, "散漫")
    assert mode == "fallback" and len(parts) == 2 and mood == "散漫"
    print(f"[PASS] 硬fallback---分割: parts={parts}")

def test_hard_fallback_filters_codeblock():
    # 完全不是 JSON，且含代码块 → 过滤掉代码块部分
    r = "```json\n{invalid}\n```"
    parts, _, _, _, _, mode = parse_llm_output(r, "平静")
    assert mode == "fallback"
    # 代码块被过滤，parts 为空或不含 ``` 开头的行
    assert all(not p.startswith("```") for p in parts)
    print(f"[PASS] 硬fallback过滤代码块: parts={parts}")


if __name__ == "__main__":
    test_clean_json()
    test_markdown_wrapped()
    test_missing_mood_inherits()
    test_invalid_emotion_corrected()
    test_empty_messages_filtered()
    test_regex_fallback_unescaped_quotes()
    test_regex_fallback_markdown_wrapped_bad_json()
    test_hard_fallback_text_split()
    test_hard_fallback_filters_codeblock()
    print("\nAll 9 tests passed.")
