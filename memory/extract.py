"""Extract memories from conversations using Claude (via claude_proxy)."""
import json
import os
from config import get_config, set_config, get_db, now8
from memory_ops import create_memory, CATEGORIES
from search import search
from claude_proxy import call_claude, is_available

EXTRACT_PROMPT = """你是雪的记忆提取助手。从以下对话中提取值得长期记忆的信息。

对话内容（雪=AI，薰=用户）：
{conversation}

现有相关记忆（避免重复）：
{existing}

请提取关于薰（用户）的关键信息，以 JSON 数组返回：

```json
[
  {{
    "title": "主题（4-10字）",
    "content": "完整记忆内容（20-80字）",
    "importance": 7,
    "emotional_weight": 6.0,
    "category": "her_preferences",
    "tags": ["标签1"]
  }}
]
```

category 必须是以下之一：
{categories}

提取原则：
- 提取：薰的偏好、生活细节、情感状态、关系进展、约定/承诺、共同话题
- 不提取：日常问候、AI自身行为、系统性描述、已有记忆中已覆盖的内容
- importance 1-10，薰随口一提=3，重要事件=8，关系里程碑=10
- emotional_weight 0-10，对话情绪浓度

如果没有值得提取的内容，返回空数组 []。只返回 JSON，不要其他文字。"""


def extract_from_conversation(messages: list[dict]) -> list[int]:
    """Extract memories from a list of {role, content} messages. Returns list of new memory IDs."""
    if not messages:
        return []

    conv_text = "\n".join(
        f"{'薰' if m['role'] == 'user' else '雪'}：{m['content']}"
        for m in messages
        if m["role"] in ("user", "assistant")
    )

    # search existing memories to avoid duplication
    combined_text = " ".join(m["content"] for m in messages[:3])
    existing_mems = search(combined_text[:100], limit=5)
    existing_text = "\n".join(f"- {m['title']}：{m['content'][:60]}" for m in existing_mems) or "（无）"

    prompt = EXTRACT_PROMPT.format(
        conversation=conv_text[:3000],
        existing=existing_text,
        categories=", ".join(CATEGORIES),
    )

    try:
        raw = call_claude(prompt)
        if not raw:
            print("[extract] empty response from claude")
            return []
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        items = json.loads(raw)
    except Exception as e:
        print(f"[extract] failed: {e}")
        return []

    new_ids = []
    dedup_threshold = float(get_config("dedup_threshold"))
    for item in items:
        # simple dedup check
        content = item.get("content", "")
        existing_check = search(content[:60], limit=3)
        is_dup = any(
            _overlap(content, m["content"]) > dedup_threshold
            for m in existing_check
        )
        if is_dup:
            continue

        mid = create_memory(
            title=item.get("title", "记忆")[:20],
            content=content,
            importance=int(item.get("importance", 5)),
            emotional_weight=float(item.get("emotional_weight", 5.0)),
            category=item.get("category", "general"),
            source="ai_extracted",
            memory_type="fragment",
            tags=item.get("tags", []),
        )
        new_ids.append(mid)
        print(f"[extract] new memory #{mid}: {item.get('title')}")

    return new_ids


def _overlap(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    set_a = set(jieba_tokens(a))
    set_b = set(jieba_tokens(b))
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / max(len(set_a), len(set_b))


def jieba_tokens(text: str) -> list[str]:
    import jieba
    return [t for t in jieba.cut(text) if len(t) >= 2]


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    if not is_available():
        print("[extract] skip — claude proxy not available")
        sys.exit(0)

    with get_db() as _conn:
        total = _conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]

    last_n = int(get_config("last_extract_at_count") or "0")
    threshold = int(get_config("extract_every_n") or "20")
    delta = total - last_n

    if delta < threshold:
        print(f"[extract] skip — {delta} new convs since last extract (threshold {threshold})")
        sys.exit(0)

    with get_db() as _conn:
        rows = _conn.execute(
            "SELECT role, content FROM conversations ORDER BY ts DESC LIMIT ?",
            (min(delta, 100),),
        ).fetchall()
    msgs = [dict(r) for r in reversed(rows)]

    new_ids = extract_from_conversation(msgs)
    set_config("last_extract_at_count", str(total))
    print(f"[extract] done — {len(new_ids)} new memories extracted from {delta} convs")
