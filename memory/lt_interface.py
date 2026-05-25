"""CLI interface for LT system to interact with the memory DB.

Usage:
  python lt_interface.py get_life_context <date>
  python lt_interface.py add_life_log <json>
  python lt_interface.py get_conversations <date> [limit]
  python lt_interface.py add_conversation <json>
  python lt_interface.py get_memory_context [query]
  python lt_interface.py get_today_sent <date>
  python lt_interface.py update_heat            # run daily decay on all memories
"""
import json
import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
sys.stdout.reconfigure(encoding='utf-8')

from config import get_db, get_config, now8, TZ8
from datetime import datetime


def get_life_context(date: str) -> dict:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT ts, activity, mood, mood_intensity, emotional_note, should_message, message_type, message_seed, sleeping, offline "
            "FROM life_logs WHERE date=? ORDER BY ts",
            (date,),
        ).fetchall()
        last = rows[-1] if rows else None
        today_sent = sum(1 for r in rows if r["should_message"])
    return {
        "date": date,
        "entries": [dict(r) for r in rows],
        "last_ts": last["ts"] if last else None,
        "last_mood": last["mood"] if last else None,
        "today_sent": today_sent,
    }


def add_life_log(entry: dict):
    date = entry.get("ts", now8())[:10]
    intensity = entry.get("mood_intensity", None)
    if intensity is not None:
        intensity = float(intensity)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO life_logs(ts,activity,mood,mood_intensity,emotional_note,should_message,message_type,message_seed,sleeping,offline,date) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                entry.get("ts", now8()),
                entry.get("activity", ""),
                entry.get("mood", "unknown"),
                intensity,
                entry.get("emotional_note", ""),
                int(entry.get("should_message", False)),
                entry.get("message_type", "none"),
                entry.get("message_seed", ""),
                int(entry.get("sleeping", False)),
                int(entry.get("offline", False)),
                date,
            ),
        )
        conn.commit()
    return {"ok": True}


def get_conversations(date: str, limit: int = 30) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content, ts, thought, proactive FROM conversations "
            "WHERE date=? ORDER BY ts DESC LIMIT ?",
            (date, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def add_conversation(entry: dict):
    ts = entry.get("ts", now8())
    date = ts[:10]
    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversations(role,content,ts,thought,proactive,date) VALUES(?,?,?,?,?,?)",
            (
                entry.get("role", "user"),
                entry.get("content", ""),
                ts,
                entry.get("thought", ""),
                int(entry.get("proactive", False)),
                date,
            ),
        )
        conn.commit()
    return {"ok": True}


def get_memory_context(query: str = "") -> str:
    from search import search as mem_search, format_for_injection
    from calendar_mem import get_calendar_context
    from memory_ops import list_memories

    lines = []

    # calendar context (recent days)
    cal = get_calendar_context(days_back=3)
    if cal:
        lines.append(cal)

    # permanent memories always injected
    perm_mems, _ = list_memories(per_page=10, permanent_only=True)
    if perm_mems:
        lines.append("### 永久记忆")
        for m in perm_mems:
            lines.append(f"🔒 [{m['category']}] {m['title']}：{m['content'][:100]}")

    # searched memories
    if query:
        results = mem_search(query, limit=10)
        if results:
            lines.append(format_for_injection(results))

    return "\n".join(lines)


UNREAD_PATH = Path(__file__).parent.parent / "data" / "unread_queue.json"


def save_unread(message: dict):
    """Save a message received during sleep to the unread queue."""
    queue = {"messages": []}
    if UNREAD_PATH.exists():
        try:
            queue = json.loads(UNREAD_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    queue.setdefault("messages", [])
    queue["messages"].append({
        "content": message.get("content", ""),
        "ts": message.get("ts", now8()),
        "saved_at": now8(),
    })
    UNREAD_PATH.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "queued": len(queue["messages"])}


def get_unread() -> dict:
    """Return all unread messages from the queue."""
    if not UNREAD_PATH.exists():
        return {"messages": [], "count": 0}
    try:
        queue = json.loads(UNREAD_PATH.read_text(encoding="utf-8"))
        msgs = queue.get("messages", [])
        return {"messages": msgs, "count": len(msgs)}
    except Exception:
        return {"messages": [], "count": 0}


def clear_unread():
    """Clear the unread queue after processing."""
    if UNREAD_PATH.exists():
        UNREAD_PATH.unlink()
    return {"ok": True}


def get_today_sent(date: str) -> int:
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM life_logs WHERE date=? AND should_message=1",
            (date,),
        ).fetchone()
    return row["c"] if row else 0


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python lt_interface.py <command> [args]")
        return

    cmd = args[0]

    if cmd == "get_life_context":
        date = args[1] if len(args) > 1 else now8()[:10]
        result = get_life_context(date)
        print(json.dumps(result, ensure_ascii=False))

    elif cmd == "add_life_log":
        entry = json.loads(args[1]) if len(args) > 1 else {}
        result = add_life_log(entry)
        print(json.dumps(result))

    elif cmd == "get_conversations":
        date = args[1] if len(args) > 1 else now8()[:10]
        limit = int(args[2]) if len(args) > 2 else 30
        result = get_conversations(date, limit)
        print(json.dumps(result, ensure_ascii=False))

    elif cmd == "add_conversation":
        entry = json.loads(args[1]) if len(args) > 1 else {}
        result = add_conversation(entry)
        print(json.dumps(result))

    elif cmd == "get_memory_context":
        query = args[1] if len(args) > 1 else ""
        print(get_memory_context(query))

    elif cmd == "get_today_sent":
        date = args[1] if len(args) > 1 else now8()[:10]
        print(get_today_sent(date))

    elif cmd == "save_unread":
        entry = json.loads(args[1]) if len(args) > 1 else {}
        result = save_unread(entry)
        print(json.dumps(result))

    elif cmd == "get_unread":
        result = get_unread()
        print(json.dumps(result, ensure_ascii=False))

    elif cmd == "clear_unread":
        result = clear_unread()
        print(json.dumps(result))

    elif cmd == "add_memory":
        entry = json.loads(args[1]) if len(args) > 1 else {}
        from memory_ops import create_memory
        mid = create_memory(**entry)
        print(json.dumps({"id": mid, "ok": True}))

    elif cmd == "update_heat":
        from heat import decay_all
        from memory_ops import get_heat_stats
        with get_db() as conn:
            decay_all(conn)
        stats = get_heat_stats()
        print(json.dumps(stats, ensure_ascii=False))

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
