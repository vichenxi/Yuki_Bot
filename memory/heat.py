"""Memory heat decay system — mirrors kiwi-mem's heat model."""
import math
from datetime import datetime, timezone, timedelta
from config import get_config, TZ8


def compute_heat(
    current_heat: float,
    importance: int,
    permanent: bool,
    last_accessed: str | None,
    access_count: int = 0,
) -> float:
    if permanent:
        return max(current_heat, 0.8)

    now = datetime.now(TZ8)
    if last_accessed is None:
        return current_heat

    try:
        la = datetime.fromisoformat(last_accessed)
        if la.tzinfo is None:
            la = la.replace(tzinfo=TZ8)
    except Exception:
        return current_heat

    days_elapsed = (now - la).total_seconds() / 86400

    if importance >= 7:
        half_life = float(get_config("heat_half_life_important"))
    else:
        half_life = float(get_config("heat_half_life_normal"))

    # recall frequency extends effective half-life
    extend_factor = 1 + float(get_config("heat_recall_extend")) * min(access_count, 20) * 0.1
    effective_half_life = half_life * extend_factor

    decay = math.exp(-math.log(2) * days_elapsed / effective_half_life)
    return max(current_heat * decay, 0.0)


def heat_on_access(current_heat: float) -> float:
    """Boost heat when a memory is recalled."""
    boosted = current_heat + (1.0 - current_heat) * 0.4
    return min(boosted, 1.0)


def injection_tier(heat: float) -> str:
    high = float(get_config("heat_threshold_high"))
    med = float(get_config("heat_threshold_medium"))
    if heat >= high:
        return "hot"
    elif heat >= med:
        return "warm"
    return "cold"


def update_memory_heat(conn, memory_id: int, query_token: str = ""):
    """Recalculate and persist heat for a single memory after access."""
    from config import now8
    row = conn.execute(
        "SELECT heat_score, importance, permanent, last_accessed, access_count, access_query_diversity "
        "FROM memories WHERE id=?", (memory_id,)
    ).fetchone()
    if not row:
        return

    new_heat = heat_on_access(row["heat_score"])
    new_count = row["access_count"] + 1
    diversity = row["access_query_diversity"]

    # track query diversity (simple: count unique first 4 chars of query)
    if query_token and len(query_token) >= 2:
        diversity += 1

    # auto-lock check
    lock_count = int(get_config("autolock_access_count"))
    lock_div = int(get_config("autolock_diversity"))
    permanent = row["permanent"]
    if new_count >= lock_count and diversity >= lock_div:
        permanent = 1

    conn.execute(
        "UPDATE memories SET heat_score=?, access_count=?, access_query_diversity=?, "
        "last_accessed=?, permanent=? WHERE id=?",
        (new_heat, new_count, diversity, now8(), permanent, memory_id),
    )


def decay_all(conn):
    """Recalculate heat for all non-permanent memories. Call periodically (e.g., daily)."""
    rows = conn.execute(
        "SELECT id, heat_score, importance, permanent, last_accessed, access_count "
        "FROM memories WHERE permanent=0"
    ).fetchall()
    for row in rows:
        new_heat = compute_heat(
            row["heat_score"],
            row["importance"],
            bool(row["permanent"]),
            row["last_accessed"],
            row["access_count"],
        )
        conn.execute("UPDATE memories SET heat_score=? WHERE id=?", (new_heat, row["id"]))
    conn.commit()
    print(f"[heat] decayed {len(rows)} memories")
