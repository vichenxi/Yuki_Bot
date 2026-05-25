"""Hybrid search: vector (cosine) + jieba keyword, merged via RRF."""
import json
import jieba
from config import get_db, get_config
from embedding import encode, from_blob, cosine_similarity
from heat import update_memory_heat, injection_tier

RRF_K = 60


def _keyword_search(conn, query: str, limit: int = 30) -> list[tuple[int, float]]:
    tokens = list(jieba.cut(query))
    if not tokens:
        return []

    rows = conn.execute(
        "SELECT id, title, content FROM memories WHERE memory_type != 'digested'"
    ).fetchall()

    scored = []
    for row in rows:
        score = 0.0
        for token in tokens:
            if len(token) < 2:
                continue
            if token in row["title"]:
                score += 1.5
            if token in row["content"]:
                score += 1.0
        if score > 0:
            scored.append((row["id"], score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def _vector_search(conn, query: str, limit: int = 30) -> list[tuple[int, float]]:
    if get_config("embedding_enabled").lower() != "true":
        return []
    try:
        q_vec = encode(query)
    except Exception as e:
        print(f"[search] embed failed: {e}")
        return []

    threshold = float(get_config("semantic_threshold"))
    rows = conn.execute(
        "SELECT id, embedding FROM memories WHERE embedding IS NOT NULL AND memory_type != 'digested'"
    ).fetchall()

    scored = []
    for row in rows:
        try:
            m_vec = from_blob(row["embedding"])
            sim = cosine_similarity(q_vec, m_vec)
            if sim >= threshold:
                scored.append((row["id"], sim))
        except Exception:
            continue

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def _rrf_merge(
    vec_results: list[tuple[int, float]],
    kw_results: list[tuple[int, float]],
    k: int = RRF_K,
) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}
    for rank, (mid, _) in enumerate(vec_results):
        scores[mid] = scores.get(mid, 0) + 1 / (k + rank + 1)
    for rank, (mid, _) in enumerate(kw_results):
        scores[mid] = scores.get(mid, 0) + 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def search(query: str, limit: int | None = None) -> list[dict]:
    max_inject = int(get_config("max_memories_inject"))
    limit = limit or max_inject

    with get_db() as conn:
        vec_res = _vector_search(conn, query, limit * 2)
        kw_res = _keyword_search(conn, query, limit * 2)
        merged = _rrf_merge(vec_res, kw_res)[:limit]

        results = []
        for mid, rrf_score in merged:
            row = conn.execute("SELECT * FROM memories WHERE id=?", (mid,)).fetchone()
            if not row:
                continue
            update_memory_heat(conn, mid, query[:4])
            tier = injection_tier(row["heat_score"])
            if tier == "cold":
                continue
            d = dict(row)
            d["rrf_score"] = rrf_score
            d["tier"] = tier
            results.append(d)
        conn.commit()

    return results


def format_for_injection(memories: list[dict]) -> str:
    """Format search results for system prompt injection."""
    if not memories:
        return ""
    lines = ["### 长期记忆（关于薰）"]
    for m in memories:
        tier = m.get("tier", "warm")
        content = m["content"] if tier == "hot" else m["content"][:80] + "…" if len(m["content"]) > 80 else m["content"]
        heat_indicator = "🔥" if tier == "hot" else "·"
        lines.append(f"{heat_indicator} [{m['category']}] {m['title']}：{content}")
    return "\n".join(lines)
