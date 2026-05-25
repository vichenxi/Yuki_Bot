import sqlite3
from config import DB_PATH, DEFAULTS, LABELS, TZ8
from datetime import datetime


SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    importance INTEGER DEFAULT 5,
    emotional_weight REAL DEFAULT 5.0,
    embedding BLOB,
    category TEXT DEFAULT 'general',
    source TEXT DEFAULT 'ai_extracted',
    memory_type TEXT DEFAULT 'fragment',
    permanent INTEGER DEFAULT 0,
    locked INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    last_accessed TEXT,
    heat_score REAL DEFAULT 1.0,
    access_count INTEGER DEFAULT 0,
    access_query_diversity INTEGER DEFAULT 0,
    date_ref TEXT,
    tags TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS memory_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    to_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    edge_type TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_scenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    narrative TEXT NOT NULL,
    atomic_facts TEXT NOT NULL DEFAULT '[]',
    related_memory_ids TEXT NOT NULL DEFAULT '[]',
    foresight TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS calendar_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    page_type TEXT NOT NULL,
    content TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    UNIQUE(date, page_type)
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    ts TEXT NOT NULL,
    thought TEXT DEFAULT '',
    proactive INTEGER DEFAULT 0,
    date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS life_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    activity TEXT NOT NULL,
    mood TEXT NOT NULL,
    should_message INTEGER DEFAULT 0,
    message_type TEXT DEFAULT 'none',
    message_seed TEXT DEFAULT '',
    sleeping INTEGER DEFAULT 0,
    offline INTEGER DEFAULT 0,
    date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dream_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    fragment_count INTEGER DEFAULT 0,
    changes_made TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    label TEXT DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memories_heat ON memories(heat_score DESC);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_date ON memories(date_ref);
CREATE INDEX IF NOT EXISTS idx_conversations_date ON conversations(date);
CREATE INDEX IF NOT EXISTS idx_life_logs_date ON life_logs(date);
CREATE INDEX IF NOT EXISTS idx_calendar_pages_date ON calendar_pages(date, page_type);
"""


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        now = datetime.now(TZ8).isoformat()
        for key, value in DEFAULTS.items():
            conn.execute(
                "INSERT OR IGNORE INTO config(key,value,label,updated_at) VALUES(?,?,?,?)",
                (key, value, LABELS.get(key, key), now),
            )
        conn.commit()
    print(f"[db] initialized at {DB_PATH}")


if __name__ == "__main__":
    init_db()
