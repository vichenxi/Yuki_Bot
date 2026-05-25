import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta

TZ8 = timezone(timedelta(hours=8))
DB_PATH = Path(r"C:\Users\Violet\.claude\yukibot\data\memory.db")
EMBED_MODEL = "BAAI/bge-small-zh-v1.5"

DEFAULTS = {
    "max_memories_inject": "15",
    "memory_extract_interval": "3",
    "semantic_threshold": "0.25",
    "dedup_threshold": "0.55",
    "heat_half_life_normal": "3",
    "heat_half_life_important": "7",
    "heat_recall_extend": "0.5",
    "heat_threshold_high": "0.7",
    "heat_threshold_medium": "0.3",
    "autolock_access_count": "10",
    "autolock_diversity": "5",
    "embedding_enabled": "true",
    "anthropic_api_key": "",
    "dream_fragment_threshold": "30",
    "calendar_inject_days": "7",
    "extract_every_n": "20",
    "last_extract_at_count": "0",
}

LABELS = {
    "max_memories_inject": "每次对话最多注入记忆条数",
    "memory_extract_interval": "每N轮对话提取一次记忆",
    "semantic_threshold": "向量相似度阈值",
    "dedup_threshold": "去重相似度阈值",
    "heat_half_life_normal": "普通记忆热度半衰期（天）",
    "heat_half_life_important": "重要记忆热度半衰期（天）",
    "heat_recall_extend": "每次访问热度延长倍数",
    "heat_threshold_high": "热记忆阈值（全文注入）",
    "heat_threshold_medium": "温记忆阈值（摘要注入）",
    "autolock_access_count": "自动锁定所需访问次数",
    "autolock_diversity": "自动锁定所需查询多样性",
    "embedding_enabled": "启用向量检索",
    "anthropic_api_key": "Anthropic API Key",
    "dream_fragment_threshold": "触发Dream的碎片数量阈值",
    "calendar_inject_days": "日历注入天数",
    "extract_every_n": "每N条对话触发一次记忆提取",
    "last_extract_at_count": "上次提取时的对话总条数",
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_config(key: str) -> str:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
        if row:
            return row["value"]
        return DEFAULTS.get(key, "")


def set_config(key: str, value: str):
    now = datetime.now(TZ8).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO config(key,value,label,updated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, LABELS.get(key, key), now),
        )
        conn.commit()


def get_all_config() -> dict:
    result = dict(DEFAULTS)
    with get_db() as conn:
        rows = conn.execute("SELECT key, value, label, updated_at FROM config").fetchall()
        for row in rows:
            result[row["key"]] = row["value"]
    return result


def now8() -> str:
    return datetime.now(TZ8).isoformat()
