"""CRUD operations for memories."""
import json
import sqlite3
from config import get_db, now8
from embedding import encode, to_blob, from_blob
from heat import update_memory_heat, decay_all, injection_tier

CATEGORIES = [
    "relationship_status",
    "her_preferences",
    "her_life",
    "promises",
    "emotional_events",
    "shared_knowledge",
    "personal_facts",
    "general",
]


def create_memory(
    title: str,
    content: str,
    importance: int = 5,
    emotional_weight: float = 5.0,
    category: str = "general",
    source: str = "ai_extracted",
    memory_type: str = "fragment",
    permanent: bool = False,
    date_ref: str | None = None,
    tags: list[str] | None = None,
    embed: bool = True,
) -> int:
    blob = None
    if embed:
        try:
            vec = encode(content)
            blob = to_blob(vec)
        except Exception as e:
            print(f"[memory_ops] embed failed: {e}")

    ts = now8()
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO memories
               (title,content,importance,emotional_weight,embedding,category,source,
                memory_type,permanent,created_at,last_accessed,heat_score,access_count,
                access_query_diversity,date_ref,tags)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,1.0,0,0,?,?)""",
            (
                title, content, importance, emotional_weight, blob,
                category, source, memory_type, int(permanent),
                ts, ts, date_ref, json.dumps(tags or []),
            ),
        )
        conn.commit()
        return cur.lastrowid


def get_memory(memory_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        return dict(row) if row else None


def update_memory(memory_id: int, **fields) -> bool:
    allowed = {"title", "content", "importance", "emotional_weight", "category",
               "permanent", "locked", "heat_score", "date_ref", "tags"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    if "tags" in updates and isinstance(updates["tags"], list):
        updates["tags"] = json.dumps(updates["tags"])
    if "content" in updates:
        try:
            vec = encode(updates["content"])
            updates["embedding"] = to_blob(vec)
        except Exception:
            pass
    clauses = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [memory_id]
    with get_db() as conn:
        conn.execute(f"UPDATE memories SET {clauses} WHERE id=?", values)
        conn.commit()
    return True


def delete_memory(memory_id: int) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        conn.commit()
    return True


def toggle_permanent(memory_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute("SELECT permanent FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not row:
            return False
        new_val = 1 - row["permanent"]
        conn.execute("UPDATE memories SET permanent=? WHERE id=?", (new_val, memory_id))
        conn.commit()
        return bool(new_val)


def toggle_locked(memory_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute("SELECT locked FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not row:
            return False
        new_val = 1 - row["locked"]
        conn.execute("UPDATE memories SET locked=? WHERE id=?", (new_val, memory_id))
        conn.commit()
        return bool(new_val)


def list_memories(
    page: int = 1,
    per_page: int = 20,
    category: str | None = None,
    memory_type: str | None = None,
    permanent_only: bool = False,
) -> tuple[list[dict], int]:
    conds = []
    params = []
    if category:
        conds.append("category=?")
        params.append(category)
    if memory_type:
        conds.append("memory_type=?")
        params.append(memory_type)
    if permanent_only:
        conds.append("permanent=1")
    where = "WHERE " + " AND ".join(conds) if conds else ""
    with get_db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM memories {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM memories {where} ORDER BY heat_score DESC, created_at DESC LIMIT ? OFFSET ?",
            params + [per_page, (page - 1) * per_page],
        ).fetchall()
    return [dict(r) for r in rows], total


def add_edge(from_id: int, to_id: int, edge_type: str):
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO memory_edges(from_id,to_id,edge_type,created_at) VALUES(?,?,?,?)",
            (from_id, to_id, edge_type, now8()),
        )
        conn.commit()


def get_edges(memory_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM memory_edges WHERE from_id=? OR to_id=?",
            (memory_id, memory_id),
        ).fetchall()
    return [dict(r) for r in rows]


def batch_delete(ids: list[int]):
    with get_db() as conn:
        conn.executemany("DELETE FROM memories WHERE id=?", [(i,) for i in ids])
        conn.commit()


def get_heat_stats() -> dict:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT heat_score, permanent FROM memories"
        ).fetchall()
    hot = sum(1 for r in rows if r["heat_score"] >= 0.7)
    warm = sum(1 for r in rows if 0.3 <= r["heat_score"] < 0.7)
    cold = sum(1 for r in rows if r["heat_score"] < 0.3)
    perm = sum(1 for r in rows if r["permanent"])
    return {"total": len(rows), "hot": hot, "warm": warm, "cold": cold, "permanent": perm}
