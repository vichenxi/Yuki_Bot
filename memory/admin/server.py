"""FastAPI admin panel for yukibot memory system."""
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import get_all_config, set_config, get_db, now8
from memory_ops import (
    create_memory, get_memory, update_memory, delete_memory,
    toggle_permanent, toggle_locked, list_memories, batch_delete, get_heat_stats,
)
from search import search as mem_search
from heat import decay_all
from dream import run_dream, get_scenes
from calendar_mem import (
    generate_day_page, generate_week_summary, generate_month_summary,
    get_calendar_context, list_pages,
)

app = FastAPI(title="Yukibot Memory Admin", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PANEL_HTML = Path(__file__).parent / "index.html"
YUKIBOT_DIR = Path(__file__).parent.parent.parent
PROFILE_DIR = YUKIBOT_DIR / "data" / "profiles"


@app.get("/", response_class=HTMLResponse)
async def admin_ui():
    return PANEL_HTML.read_text(encoding="utf-8")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "ts": now8()}


# ── Status ────────────────────────────────────────────────────────────────────

@app.get("/status")
async def get_status():
    import json as _json
    from pathlib import Path
    data_dir = Path(__file__).parent.parent.parent / "data"
    today = now8()[:10]

    with get_db() as conn:
        latest_log = conn.execute(
            "SELECT ts, activity, mood, should_message FROM life_logs ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        today_sent = conn.execute(
            "SELECT COUNT(*) as c FROM life_logs WHERE date=? AND should_message=1", (today,)
        ).fetchone()["c"]
        today_ticks = conn.execute(
            "SELECT COUNT(*) as c FROM life_logs WHERE date=?", (today,)
        ).fetchone()["c"]
        latest_user_msg = conn.execute(
            "SELECT content, ts FROM conversations WHERE role='user' ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        latest_asst_msg = conn.execute(
            "SELECT content, ts FROM conversations WHERE role='assistant' ORDER BY ts DESC LIMIT 1"
        ).fetchone()

    next_tick = None
    try:
        next_tick = _json.loads((data_dir / "next_tick.json").read_text())["next_tick"]
    except Exception:
        pass

    emotional_arc = None
    try:
        ef = data_dir / f"daily_events_{today}.json"
        emotional_arc = _json.loads(ef.read_text(encoding="utf-8")).get("emotional_arc")
    except Exception:
        pass

    with get_db() as conn:
        today_logs = conn.execute(
            "SELECT ts, mood FROM life_logs WHERE date=? ORDER BY ts",
            (today,)
        ).fetchall()

    return {
        "today": today,
        "latest_log": dict(latest_log) if latest_log else None,
        "today_sent": today_sent,
        "today_ticks": today_ticks,
        "latest_user_msg": dict(latest_user_msg) if latest_user_msg else None,
        "latest_asst_msg": dict(latest_asst_msg) if latest_asst_msg else None,
        "next_tick": next_tick,
        "emotional_arc": emotional_arc,
        "today_logs": [{"ts": r["ts"], "mood": r["mood"]} for r in today_logs],
    }


# ── Config ───────────────────────────────────────────────────────────────────

@app.get("/admin/config")
async def get_config_all():
    return get_all_config()


class ConfigUpdate(BaseModel):
    value: str


class ProfileImage(BaseModel):
    data_url: str  # data:image/png;base64,...

@app.put("/admin/config/{key}")
async def update_config(key: str, body: ConfigUpdate):
    set_config(key, body.value)
    return {"ok": True}


# ── Diaries ──────────────────────────────────────────────────────────────────

@app.get("/diaries")
async def list_diaries():
    diary_files = sorted(
        [f for f in (YUKIBOT_DIR / "data" / "logs").glob("*_yuki.txt") if "_lt" not in f.name],
        reverse=True,
    )
    result = []
    for f in diary_files:
        date = f.name.replace("_yuki.txt", "")
        try:
            content = f.read_text(encoding="utf-8").strip()
        except Exception:
            content = ""
        result.append({"date": date, "content": content})
    return {"diaries": result}


# ── Profile Images ────────────────────────────────────────────────────────────

@app.get("/profile/{name}")
async def get_profile_image(name: str):
    if name not in ("portrait", "fullbody", "xun", "avatar"):
        raise HTTPException(404, "not found")
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "jpg", "jpeg"):
        path = PROFILE_DIR / f"{name}.{ext}"
        if path.exists():
            return FileResponse(str(path), media_type=f"image/{'jpeg' if ext=='jpeg' else ext}")
    raise HTTPException(404, "no image yet")


@app.post("/profile/{name}")
async def upload_profile_image(name: str, body: ProfileImage):
    if name not in ("portrait", "fullbody", "xun", "avatar"):
        raise HTTPException(400, "invalid name")
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    import base64 as _b64
    try:
        _, data_part = body.data_url.split(",", 1)
        data = _b64.b64decode(data_part)
    except Exception as e:
        raise HTTPException(400, f"invalid data_url: {e}")
    path = PROFILE_DIR / f"{name}.png"
    path.write_bytes(data)
    return {"ok": True}


# ── Memories ─────────────────────────────────────────────────────────────────

class MemoryCreate(BaseModel):
    title: str
    content: str
    importance: int = 5
    emotional_weight: float = 5.0
    category: str = "general"
    source: str = "user_explicit"
    permanent: bool = False
    date_ref: Optional[str] = None
    tags: list[str] = []


@app.get("/memories")
async def list_mems(
    page: int = 1,
    per_page: int = 20,
    category: Optional[str] = None,
    memory_type: Optional[str] = None,
    permanent_only: bool = False,
):
    mems, total = list_memories(page, per_page, category, memory_type, permanent_only)
    # strip embedding blob from response
    for m in mems:
        m.pop("embedding", None)
    return {"memories": mems, "total": total, "page": page, "per_page": per_page}


@app.post("/memories")
async def create_mem(body: MemoryCreate):
    mid = create_memory(**body.model_dump())
    return {"id": mid, "ok": True}


@app.get("/memories/{mid}")
async def get_mem(mid: int):
    m = get_memory(mid)
    if not m:
        raise HTTPException(404, "not found")
    m.pop("embedding", None)
    return m


class MemoryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    importance: Optional[int] = None
    emotional_weight: Optional[float] = None
    category: Optional[str] = None
    permanent: Optional[bool] = None


@app.put("/memories/{mid}")
async def update_mem(mid: int, body: MemoryUpdate):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    ok = update_memory(mid, **fields)
    return {"ok": ok}


@app.delete("/memories/{mid}")
async def delete_mem(mid: int):
    ok = delete_memory(mid)
    return {"ok": ok}


@app.post("/memories/{mid}/toggle-permanent")
async def toggle_perm(mid: int):
    new_val = toggle_permanent(mid)
    return {"permanent": new_val}


@app.post("/memories/{mid}/toggle-locked")
async def toggle_lock(mid: int):
    new_val = toggle_locked(mid)
    return {"locked": new_val}


@app.post("/memories/batch-delete")
async def batch_del(ids: list[int] = Body(...)):
    batch_delete(ids)
    return {"ok": True, "deleted": len(ids)}


@app.get("/memories/search")
async def search_mems(q: str = Query(..., min_length=1), limit: int = 15):
    results = mem_search(q, limit)
    for r in results:
        r.pop("embedding", None)
    return {"results": results, "count": len(results)}


@app.get("/memories/heat-stats")
async def heat_stats():
    return get_heat_stats()


@app.post("/memories/decay-all")
async def trigger_decay():
    with get_db() as conn:
        decay_all(conn)
    return {"ok": True}


# ── Dream ─────────────────────────────────────────────────────────────────────

@app.post("/dream/start")
async def start_dream(force: bool = False):
    result = run_dream(force=force)
    return result


@app.get("/dream/scenes")
async def list_dream_scenes():
    return {"scenes": get_scenes()}


@app.get("/dream/logs")
async def dream_logs(limit: int = 10):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM dream_logs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return {"logs": [dict(r) for r in rows]}


# ── Calendar ─────────────────────────────────────────────────────────────────

@app.post("/calendar/day")
async def gen_day(date: str):
    content = generate_day_page(date)
    return {"date": date, "content": content}


@app.post("/calendar/week")
async def gen_week(week_start: str):
    content = generate_week_summary(week_start)
    return {"week_start": week_start, "content": content}


@app.post("/calendar/month")
async def gen_month(month: str):
    content = generate_month_summary(month)
    return {"month": month, "content": content}


@app.get("/calendar/context")
async def calendar_ctx(days: int = 7):
    return {"context": get_calendar_context(days)}


@app.get("/calendar/pages")
async def cal_pages(page_type: Optional[str] = None, limit: int = 30):
    return {"pages": list_pages(page_type, limit)}


# ── Conversations & LifeLogs ──────────────────────────────────────────────────

@app.get("/conversations")
async def get_conversations(date: Optional[str] = None, limit: int = 50):
    with get_db() as conn:
        if date:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE date=? ORDER BY ts DESC LIMIT ?",
                (date, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM conversations ORDER BY ts DESC LIMIT ?", (limit,)
            ).fetchall()
    return {"conversations": [dict(r) for r in rows]}


@app.get("/lifelogs")
async def get_lifelogs(date: Optional[str] = None, limit: int = 50):
    with get_db() as conn:
        if date:
            rows = conn.execute(
                "SELECT * FROM life_logs WHERE date=? ORDER BY ts DESC LIMIT ?",
                (date, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM life_logs ORDER BY ts DESC LIMIT ?", (limit,)
            ).fetchall()
    return {"logs": [dict(r) for r in rows]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8765, reload=False)
