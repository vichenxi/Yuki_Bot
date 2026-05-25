"""Migrate existing JSON files to the new SQLite memory DB."""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from db import init_db
from config import get_db, TZ8
from memory_ops import create_memory

DATA_DIR = Path(__file__).parent.parent / "data"


def _date_from_ts(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ8)
        return dt.astimezone(TZ8).strftime("%Y-%m-%d")
    except Exception:
        return ts[:10] if len(ts) >= 10 else "2026-01-01"


def migrate_full_archive(path: Path | None = None):
    """Migrate full_archive*.json files into conversations table."""
    files = sorted((path or DATA_DIR).glob("full_archive*.json"))
    total = 0
    with get_db() as conn:
        for f in files:
            try:
                entries = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[migrate] skip {f.name}: {e}")
                continue
            for entry in entries:
                if entry.get("role") == "system":
                    continue
                ts = entry.get("ts", "2026-01-01T00:00:00+08:00")
                date = _date_from_ts(ts)
                conn.execute(
                    "INSERT OR IGNORE INTO conversations(role,content,ts,thought,proactive,date) "
                    "VALUES(?,?,?,?,?,?)",
                    (
                        entry.get("role", "user"),
                        entry.get("content", ""),
                        ts,
                        entry.get("thought", ""),
                        int(entry.get("proactive", False)),
                        date,
                    ),
                )
                total += 1
        conn.commit()
    print(f"[migrate] conversations: {total} entries from {len(files)} files")


def migrate_life_logs():
    """Migrate life_log_*.json files into life_logs table."""
    files = sorted(DATA_DIR.glob("life_log_*.json"))
    total = 0
    with get_db() as conn:
        for f in files:
            date = f.stem.replace("life_log_", "")
            try:
                entries = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[migrate] skip {f.name}: {e}")
                continue
            for entry in entries:
                conn.execute(
                    "INSERT OR IGNORE INTO life_logs(ts,activity,mood,should_message,message_type,"
                    "message_seed,sleeping,offline,date) VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        entry.get("ts", ""),
                        entry.get("activity", ""),
                        entry.get("mood", "unknown"),
                        int(entry.get("should_message", False)),
                        entry.get("message_type", "none"),
                        entry.get("message_seed", ""),
                        int(entry.get("sleeping", False)),
                        int(entry.get("offline", False)),
                        date,
                    ),
                )
                total += 1
        conn.commit()
    print(f"[migrate] life_logs: {total} entries from {len(files)} files")


def migrate_key_events():
    """Migrate key_events.json into memories table (source=seed_import)."""
    kf = DATA_DIR / "key_events.json"
    if not kf.exists():
        print("[migrate] key_events.json not found, skipping")
        return

    try:
        data = json.loads(kf.read_text(encoding="utf-8"))
        events = data.get("events", [])
    except Exception as e:
        print(f"[migrate] key_events error: {e}")
        return

    category_map = {
        "relationship_milestone": "relationship_status",
        "her_preferences": "her_preferences",
        "her_life": "her_life",
        "promise": "promises",
        "emotional_event": "emotional_events",
        "shared_knowledge": "shared_knowledge",
    }

    count = 0
    for ev in events:
        cat = category_map.get(ev.get("category", ""), "general")
        mid = create_memory(
            title=ev.get("id", "事件"),
            content=ev.get("content", ""),
            importance=7,
            emotional_weight=6.0,
            category=cat,
            source="seed_import",
            memory_type="fragment",
            date_ref=ev.get("date"),
            embed=True,
        )
        count += 1
    print(f"[migrate] key_events: {count} memories created")


def migrate_daily_memory(date: str | None = None):
    """Migrate daily_memory_*.json baseline_summary into memories as permanent seeds."""
    files = sorted(DATA_DIR.glob(f"daily_memory_{date or '*'}.json"))
    count = 0
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[migrate] skip {f.name}: {e}")
            continue

        date_str = data.get("date", f.stem.replace("daily_memory_", ""))

        # baseline_summary → permanent memory
        summary = data.get("baseline_summary", "")
        if summary:
            create_memory(
                title=f"{date_str} 日记忆",
                content=summary,
                importance=8,
                emotional_weight=6.0,
                category="relationship_status",
                source="seed_import",
                memory_type="daily_digest",
                permanent=True,
                date_ref=date_str,
            )
            count += 1

        # key_facts_about_xun → individual memories
        for fact in data.get("key_facts_about_xun", []):
            create_memory(
                title="关于薰",
                content=fact,
                importance=6,
                emotional_weight=4.0,
                category="personal_facts",
                source="seed_import",
                memory_type="fragment",
                date_ref=date_str,
            )
            count += 1

    print(f"[migrate] daily_memory: {count} memories from {len(files)} files")


def run_all():
    print("[migrate] initializing database ...")
    init_db()
    print("[migrate] starting migration ...")
    migrate_full_archive()
    migrate_life_logs()
    migrate_key_events()
    migrate_daily_memory()
    print("[migrate] all done.")


if __name__ == "__main__":
    run_all()
