# -*- coding: utf-8 -*-
"""
handle_reply.py — 自主处理薰的来消息

由 tg_daemon 直接调用，不依赖 Claude Code cron。
流程：读 pending_reply.json → 构建上下文 → 调 claude -p → 发 Telegram → 存 DB → 删文件
"""
import json
import os
import re
import sys
import subprocess
import tempfile
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

VOICE_RE = re.compile(r'^\[voice(?::(\w+))?\]\s*', re.IGNORECASE)
VALID_EMOTIONS = {"neutral", "tender", "playful", "happy", "sad", "excited"}

BASE    = Path(__file__).resolve().parent.parent
DATA    = BASE / "data"
CONFIG  = BASE / "config.json"
PENDING = DATA / "pending_reply.json"
LT_INTERFACE = BASE / "memory" / "lt_interface.py"

sys.path.insert(0, str(BASE))
from persona import CHARACTER_NAME, PARTNER_NAME, SYSTEM_PROMPT, SLEEP_START, SLEEP_END, is_sleeping

CST = timezone(timedelta(hours=8))


def now_cst() -> datetime:
    return datetime.now(CST)


def now_iso() -> str:
    return now_cst().isoformat()


def load_config() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def run_lt(cmd: str) -> str:
    r = subprocess.run(
        ["python", str(LT_INTERFACE)] + cmd.split(),
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(BASE)
    )
    return r.stdout.strip()


def run_lt_with_arg(subcmd: str, arg: str) -> str:
    r = subprocess.run(
        ["python", str(LT_INTERFACE), subcmd, arg],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(BASE)
    )
    return r.stdout.strip()


def notify_owner(token: str, chat_id: str, text: str):
    """向主人发送系统错误通知。"""
    try:
        send_telegram_message(token, chat_id, text)
    except Exception:
        pass


def send_telegram_message(token: str, chat_id: str, text: str) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({"chat_id": chat_id, "text": text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def call_claude(prompt: str, image_path: str = None) -> str:
    """通过 llm_client 调用 LLM，返回回复文本。"""
    sys.path.insert(0, str(BASE / "memory"))
    import llm_client
    if image_path:
        return llm_client.chat_with_image(prompt, image_path, max_tokens=1024, timeout=180)
    return llm_client.chat(prompt, max_tokens=1024, timeout=120)


def is_voice_api_up() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:9880", timeout=2)
        return True
    except urllib.error.HTTPError as e:
        return e.code < 500
    except Exception:
        return False


def try_send_voice(token: str, chat_id: str, text: str, emotion: str = "neutral") -> bool:
    """合成语音并通过 Telegram 发送。成功返回 True，API 不在线返回 False。"""
    if not is_voice_api_up():
        print("[handle_reply] voice API 不在线，降级为文字")
        return False

    cfg = load_config()
    api_base = cfg.get("gptsovits_api", "http://127.0.0.1:9880")

    def _resolve(p: str) -> str:
        return str((BASE / p).resolve()) if p and not Path(p).is_absolute() else p

    # 切换模型权重
    for endpoint, path_key in [("set_gpt_weights", "gpt_model_path"),
                                 ("set_sovits_weights", "sovits_model_path")]:
        try:
            url = f"{api_base}/{endpoint}?weights_path={urllib.parse.quote(_resolve(cfg[path_key]), safe='')}"
            urllib.request.urlopen(url, timeout=30)
        except Exception as e:
            print(f"[handle_reply] {endpoint} 失败：{e}")

    # TTS 合成
    payload = json.dumps({
        "text": text,
        "text_lang": "ja",
        "ref_audio_path": _resolve(cfg["ref_audio_path"]),
        "prompt_text": cfg["ref_text"],
        "prompt_lang": "ja",
        "media_type": "wav",
        "streaming_mode": False,
        "top_k": 5, "top_p": 1.0, "temperature": 1.0,
        "speed_factor": 1.0, "repetition_penalty": 1.35,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base}/tts", data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            audio_data = resp.read()
    except Exception as e:
        print(f"[handle_reply] TTS 合成失败：{e}")
        return False

    # 发送 Telegram 语音
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = tmp.name
    try:
        boundary = "yuki_voice_bdry"
        body = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n"
        ).encode()
        with open(tmp_path, "rb") as f:
            body += (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"voice\"; filename=\"voice.wav\"\r\n"
                f"Content-Type: audio/wav\r\n\r\n"
            ).encode() + f.read() + f"\r\n--{boundary}--\r\n".encode()
        tg_req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendVoice",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(tg_req, timeout=30) as resp:
            result = json.loads(resp.read())
            ok = result.get("ok", False)
            print(f"[handle_reply] voice 发送：ok={ok} emotion={emotion}")
            return ok
    except Exception as e:
        print(f"[handle_reply] voice Telegram 发送失败：{e}")
        return False
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def maybe_save_image_memory(image_path: str, msg_text: str, reply_text: str):
    """Ask LLM to evaluate the image and save a memory entry if it's worth keeping."""
    sys.path.insert(0, str(BASE / "memory"))
    import llm_client
    prompt = f"""{PARTNER_NAME}发来了一张图片（附带文字：「{msg_text[:60]}」），{CHARACTER_NAME}的回复是「{reply_text[:60]}」。

请评估这张图片是否值得以{CHARACTER_NAME}的视角存入长期记忆，判断标准：
- 值得保存：{PARTNER_NAME}的自拍/生活照、她做的东西、她去的地方、有情感意义的内容
- 不值得保存：截图/梗图/随手转发的表情包/普通截图

如果值得保存，输出以下 JSON（不要有任何其他文字）：
{{"save": true, "title": "（15字内的标题）", "content": "（50字内描述图片内容和情境）", "category": "her_life", "importance": 6}}

如果不值得保存，只输出：{{"save": false}}"""
    try:
        raw = llm_client.chat_with_image(prompt, image_path, max_tokens=256, timeout=60)
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw)
    except Exception as e:
        print(f"[handle_reply] 图片记忆评估失败：{e}")
        return
    if not data.get("save"):
        print("[handle_reply] 图片不值得保存，跳过")
        return
    entry = {
        "title": data.get("title", "薰发来的图片"),
        "content": data.get("content", ""),
        "category": data.get("category", "her_life"),
        "importance": data.get("importance", 6),
        "emotional_weight": 6.0,
        "source": "image_from_xun",
        "memory_type": "fragment",
        "permanent": False,
    }
    result_raw = run_lt_with_arg("add_memory", json.dumps(entry, ensure_ascii=False))
    try:
        result = json.loads(result_raw)
        print(f"[handle_reply] 图片记忆已保存：id={result.get('id')}, title={entry['title']}")
    except Exception:
        print(f"[handle_reply] 图片记忆保存响应：{result_raw}")


def main():
    if not PENDING.exists():
        print("[handle_reply] pending_reply.json 不存在，退出")
        return

    # 读消息
    payload = json.loads(PENDING.read_text(encoding="utf-8-sig"))
    messages = payload.get("messages", [])
    _trace = payload.get("trace_id", "????????")

    def log(msg: str):
        print(f"[{_trace}] {msg}")
    if not messages:
        PENDING.unlink(missing_ok=True)
        return

    # 睡眠检查
    now = now_cst()
    hour = now.hour
    if is_sleeping(hour):
        log(f"{CHARACTER_NAME}在睡觉（{hour:02d}时），跳过")
        PENDING.unlink(missing_ok=True)
        return

    today = now.strftime("%Y-%m-%d")

    life_ctx_raw = run_lt(f"get_life_context {today}")
    try:
        life_ctx = json.loads(life_ctx_raw)
        last_mood = life_ctx.get("last_mood", "平")
        sleeping = life_ctx.get("entries", [{}])[-1].get("sleeping", 0) if life_ctx.get("entries") else 0
        if sleeping:
            log("雪在睡觉，跳过")
            PENDING.unlink(missing_ok=True)
            return
        last_activity = life_ctx.get("entries", [{}])[-1].get("activity", "") if life_ctx.get("entries") else ""
    except Exception:
        last_mood = "平"
        last_activity = ""

    # 读取最近对话（最多 10 条，完整内容）
    conv_raw = run_lt(f"get_conversations {today} 10")
    try:
        conv_list = json.loads(conv_raw)
        recent = conv_list[-8:] if len(conv_list) > 8 else conv_list
        conv_text = "\n".join(
            f"[{'薰' if c['role']=='user' else '雪'}] {c['content']}"
            for c in recent if c["role"] in ("user", "assistant")
        )
    except Exception:
        conv_text = "（无近期记录）"

    # 读取长期记忆上下文（返回纯文本，过滤掉 [embedding] 加载行）
    mem_ctx_raw = run_lt_with_arg("get_memory_context", "薰 关系 情绪 约定")
    mem_lines = [l for l in mem_ctx_raw.splitlines() if not l.startswith("[embedding]")]
    mem_text = "\n".join(mem_lines).strip()[:1200] if mem_lines else "（无记忆上下文）"

    # 构建新消息文本，检测图片
    image_path = None
    new_msgs_text_parts = []
    for m in messages:
        line = f"「{m['text']}」({m['ts'][11:16]})"
        if m.get("image_path"):
            image_path = m["image_path"]  # 取最后一张图
            line = f"[附图] {line}"
        new_msgs_text_parts.append(line)
    new_msgs_text = "\n".join(new_msgs_text_parts)

    # 图片提示补充
    image_hint = ""
    if image_path:
        image_hint = "\n[图片说明] 薰发来了一张图，你能看到图片内容，请根据图片内容自然回应。"

    # 当前时间描述
    time_desc = now.strftime("%H:%M")

    prompt = f"""{SYSTEM_PROMPT}

[当前时间] {time_desc} 北京时间
[{CHARACTER_NAME}当前状态] 心情：{last_mood}　最近活动：{last_activity}

[长期记忆]
{mem_text}

[今日近期对话]
{conv_text}

[{PARTNER_NAME}刚刚发来]
{new_msgs_text}{image_hint}

请以{CHARACTER_NAME}的身份回复{PARTNER_NAME}。
输出严格的 JSON，不要有任何其他文字：
{{
  "messages": ["第一条回复", "第二条回复"],
  "thought": "（内心OS：雪这一刻真实的内部情绪活动，20-60字，不外露）",
  "mood": "（一个词，描述雪现在的心情，如：平静/温柔/有点在意/无聊/烦躁/被触动）",
  "voice_index": -1,
  "voice_emotion": "neutral"
}}
voice_index：哪条消息最适合用语音说出来（0-based），绝大多数时候填 -1（不用语音）；只有那句真的有情感重量的话才考虑。
voice_emotion 从 neutral/tender/playful/happy/sad/excited 中选一个。
重要：JSON 字段值内不使用英文双引号（需要引用时改用「」）。"""

    log(f"调用 LLM{'（含图片）' if image_path else ''}...")
    cfg = load_config()
    token = cfg["bot_token"]
    owner_id = str(cfg.get("owner_chat_id", cfg.get("default_chat_id", "")))

    try:
        reply_raw = call_claude(prompt, image_path=image_path)
    except Exception as e:
        log(f"LLM 调用异常：{e}")
        if owner_id:
            notify_owner(token, owner_id, f"[雪系统] ❌ handle_reply 调用 claude 失败：{e}")
        PENDING.unlink(missing_ok=True)
        return

    if not reply_raw:
        log("LLM 返回空，跳过")
        if owner_id:
            notify_owner(token, owner_id, "[雪系统] ⚠️ handle_reply: LLM 返回空（可能上下文溢出或 API 错误）")
        PENDING.unlink(missing_ok=True)
        return

    # 解析 LLM 输出（JSON → 正则提取 → 文字分割 三层 fallback）
    thought = ""
    mood = last_mood
    voice_index = -1
    voice_emotion = "neutral"
    parts = []

    def _strip_markdown(s):
        s = s.strip()
        if s.startswith("```"):
            chunks = s.split("```")
            s = chunks[-2] if len(chunks) >= 2 else s
            s = s.lstrip("json").strip()
        return s

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
        log(f"JSON 解析成功，{len(parts)} 条，mood={mood}")
    except (json.JSONDecodeError, ValueError, KeyError) as _je:
        log(f"JSON解析失败：{_je}。raw={raw_clean[:200]!r}")
        # 中间层：正则提取 messages 数组（应对 thought 里含双引号导致 JSON 非法）
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
                log(f"正则提取成功，{len(parts)} 条，mood={mood}")
            else:
                raise ValueError("regex found no messages")
        except Exception:
            # 硬 fallback：--- 分割，过滤掉 ``` 代码块
            candidates = [p.strip() for p in reply_raw.split("---") if p.strip()]
            parts = [p for p in candidates if not p.startswith("```")]
            if not parts and any(not c.startswith("```") for c in candidates):
                parts = candidates
            log(f"硬 fallback 文字分割，{len(parts)} 条")

    # 安全过滤：防止把 LLM 原始 JSON 整体当消息发出去
    safe_parts = [p for p in parts if not (
        p.strip().startswith("{") and '"messages"' in p and '"mood"' in p
    )]
    if not safe_parts and parts:
        log(f"[安全过滤] 检测到原始 LLM 输出被放入 parts，跳过发送。raw={reply_raw[:120]!r}")
        PENDING.unlink(missing_ok=True)
        return
    parts = safe_parts

    log(f"回复内容：{parts}")

    chat_id = str(cfg["default_chat_id"])

    import time
    sent_parts = []
    for i, part in enumerate(parts):
        try:
            # fallback 路径：检查旧式 [voice:emotion] 标签
            vm = VOICE_RE.match(part)
            if vm:
                emotion = (vm.group(1) or "neutral").lower()
                if emotion not in VALID_EMOTIONS:
                    emotion = "neutral"
                clean_text = VOICE_RE.sub("", part).strip()
                if not clean_text:
                    continue
                sent_as_voice = try_send_voice(token, chat_id, clean_text, emotion)
                if not sent_as_voice:
                    send_telegram_message(token, chat_id, clean_text)
                label = f"[voice:{emotion}]" if sent_as_voice else f"[voice→text:{emotion}]"
                sent_parts.append(f"{label} {clean_text}")
            elif i == voice_index:
                # JSON 路径：voice_index 指定的消息用语音
                sent_as_voice = try_send_voice(token, chat_id, part, voice_emotion)
                if not sent_as_voice:
                    send_telegram_message(token, chat_id, part)
                label = f"[voice:{voice_emotion}]" if sent_as_voice else f"[voice→text:{voice_emotion}]"
                sent_parts.append(f"{label} {part}")
            else:
                send_telegram_message(token, chat_id, part)
                sent_parts.append(part)
            log(f"已发送第 {i+1} 条")
            if i < len(parts) - 1:
                time.sleep(0.8)
        except Exception as e:
            log(f"发送失败：{e}")

    if not sent_parts:
        PENDING.unlink(missing_ok=True)
        return

    reply_ts = now_iso()

    # 保存用户消息
    for m in messages:
        entry = {"role": "user", "content": m["text"], "ts": m["ts"]}
        run_lt_with_arg("add_conversation", json.dumps(entry, ensure_ascii=False))

    # 保存雪的回复（使用 LLM 返回的真实 thought 和 mood）
    reply_content = "\\n".join(sent_parts)
    asst_entry = {
        "role": "assistant",
        "content": reply_content,
        "ts": reply_ts,
        "thought": thought or f"mood={mood}",
    }
    run_lt_with_arg("add_conversation", json.dumps(asst_entry, ensure_ascii=False))

    # 追加 life log（使用本次回复后的真实心情）
    msg_summary = messages[0]["text"][:15] if messages else ""
    log_entry = {
        "ts": reply_ts,
        "activity": f"{PARTNER_NAME}发来消息「{msg_summary}」，{CHARACTER_NAME}自动回复了",
        "mood": mood,
        "should_message": False,
        "message_type": "none",
        "message_seed": ""
    }
    run_lt_with_arg("add_life_log", json.dumps(log_entry, ensure_ascii=False))

    # 追加 lt.txt
    lt_file = BASE / "data" / "logs" / f"{today}_yuki_lt.txt"
    try:
        with open(lt_file, "a", encoding="utf-8") as f:
            summary = " / ".join(m["text"][:40] for m in messages)
            reply_summary = " / ".join(
                p[:30] if not p.startswith("[voice") else p[:35]
                for p in sent_parts
            )
            f.write(f"[{now.strftime('%H:%M')}] {PARTNER_NAME}发来：「{summary}」\n")
            f.write(f"       {CHARACTER_NAME}回：「{reply_summary}」（自主处理）\n")
            f.write("---\n")
    except Exception as e:
        log(f"lt.txt 写入失败：{e}")

    # 图片记忆（评估后决定是否保存）
    if image_path and Path(image_path).exists():
        first_msg_text = messages[0]["text"] if messages else ""
        first_reply = sent_parts[0] if sent_parts else ""
        try:
            maybe_save_image_memory(image_path, first_msg_text, first_reply)
        except Exception as e:
            log(f"图片记忆处理异常：{e}")

    # 清理临时图片文件
    if image_path:
        try:
            Path(image_path).unlink(missing_ok=True)
        except Exception:
            pass

    # 删除信号文件
    PENDING.unlink(missing_ok=True)
    log("完成，pending_reply.json 已删除")


if __name__ == "__main__":
    main()
