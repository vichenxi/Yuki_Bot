"""FastAPI admin panel for yukibot memory system."""
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
DESKTOP_DIR = Path("F:/bot/desktop")
VRM_FILE    = Path("F:/bot/Yuki.vrm")

# Serve Three.js + three-vrm locally so admin panel works offline
_three_dir    = DESKTOP_DIR / "node_modules" / "three"
_three_vrm_dir = DESKTOP_DIR / "node_modules" / "@pixiv" / "three-vrm" / "lib"
if _three_dir.exists():
    app.mount("/static/three", StaticFiles(directory=str(_three_dir)), name="three")
if _three_vrm_dir.exists():
    app.mount("/static/three-vrm", StaticFiles(directory=str(_three_vrm_dir)), name="three-vrm")


@app.get("/", response_class=HTMLResponse)
async def admin_ui():
    return PANEL_HTML.read_text(encoding="utf-8")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "ts": now8()}


# ── VRM Model ─────────────────────────────────────────────────────────────────

@app.get("/model/vrm")
async def get_vrm_model():
    if not VRM_FILE.exists():
        raise HTTPException(404, "VRM file not found")
    return FileResponse(str(VRM_FILE), media_type="model/gltf-binary")


@app.get("/vrm-viewer", response_class=HTMLResponse)
async def vrm_viewer():
    p = Path(__file__).parent / "vrm_viewer.html"
    if not p.exists():
        raise HTTPException(404, "VRM viewer not found")
    return p.read_text(encoding="utf-8")


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
            "SELECT ts, mood, mood_valence FROM life_logs WHERE date=? ORDER BY ts",
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
        "today_logs": [{"ts": r["ts"], "mood": r["mood"], "v": r["mood_valence"]} for r in today_logs],
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
        [f for f in YUKIBOT_DIR.glob("*_yuki.txt") if "_lt" not in f.name],
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


# ── Bot Config (config.json) ──────────────────────────────────────────────────

BOT_CONFIG_PATH = YUKIBOT_DIR / "config.json"
BOT_CONFIG_KEYS = [
    "gpt_model_path", "sovits_model_path", "ref_audio_path",
    "ref_text", "voice_lang", "gptsovits_api",
]
BOT_CONFIG_LABELS = {
    "gpt_model_path":    "GPT 权重路径 (.ckpt)",
    "sovits_model_path": "SoVITS 权重路径 (.pth)",
    "ref_audio_path":    "参考音频路径 (.wav)",
    "ref_text":          "参考音频文本",
    "voice_lang":        "合成语言 (zh / ja / en)",
    "gptsovits_api":     "GPT-SoVITS API 地址",
}


def _read_bot_config() -> dict:
    return json.loads(BOT_CONFIG_PATH.read_text(encoding="utf-8"))


def _write_bot_config(cfg: dict):
    BOT_CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )


@app.get("/bot-config")
async def get_bot_config():
    cfg = _read_bot_config()
    return {
        k: {"value": cfg.get(k, ""), "label": BOT_CONFIG_LABELS.get(k, k)}
        for k in BOT_CONFIG_KEYS
    }


class BotConfigUpdate(BaseModel):
    value: str


@app.put("/bot-config/{key}")
async def update_bot_config(key: str, body: BotConfigUpdate):
    if key not in BOT_CONFIG_KEYS:
        raise HTTPException(400, f"key '{key}' not allowed")
    cfg = _read_bot_config()
    cfg[key] = body.value
    _write_bot_config(cfg)
    return {"ok": True}


@app.post("/bot-config/apply-weights")
async def apply_weights():
    """Hot-switch GPT-SoVITS model weights via running API."""
    import urllib.request as _req, urllib.parse as _parse
    cfg = _read_bot_config()
    api = cfg.get("gptsovits_api", "http://127.0.0.1:9880")
    results = {}
    for endpoint, key in [("set_gpt_weights", "gpt_model_path"),
                           ("set_sovits_weights", "sovits_model_path")]:
        url = f"{api}/{endpoint}?weights_path={_parse.quote(cfg.get(key,''), safe='')}"
        try:
            with _req.urlopen(url, timeout=15) as r:
                results[endpoint] = json.loads(r.read()).get("message", "ok")
        except Exception as e:
            results[endpoint] = f"error: {e}"
    return results


@app.post("/bot-config/test-voice")
async def test_voice():
    """Synthesize a short test sentence and return audio as base64."""
    import urllib.request as _req, base64 as _b64
    cfg = _read_bot_config()
    api = cfg.get("gptsovits_api", "http://127.0.0.1:9880")
    lang = cfg.get("voice_lang", "zh")
    payload = json.dumps({
        "text": "好的，我知道了。",
        "text_lang": lang,
        "ref_audio_path": cfg["ref_audio_path"],
        "prompt_text": cfg["ref_text"],
        "prompt_lang": lang,
        "media_type": "wav",
        "streaming_mode": False,
        "top_k": 5, "top_p": 1.0, "temperature": 1.0,
        "speed_factor": 1.0, "repetition_penalty": 1.35,
    }, ensure_ascii=False).encode("utf-8")
    try:
        req = _req.Request(f"{api}/tts", data=payload,
                           headers={"Content-Type": "application/json"})
        with _req.urlopen(req, timeout=60) as r:
            audio = r.read()
        return {"ok": True, "audio_b64": _b64.b64encode(audio).decode(), "size": len(audio)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/bot-config/voice-status")
async def voice_status():
    import urllib.request as _req
    cfg = _read_bot_config()
    api = cfg.get("gptsovits_api", "http://127.0.0.1:9880")
    try:
        _req.urlopen(api, timeout=3)
        return {"online": True, "api": api}
    except Exception as e:
        try:
            import urllib.error
            if isinstance(e, urllib.error.HTTPError):
                return {"online": True, "api": api}
        except Exception:
            pass
        return {"online": False, "api": api, "error": str(e)}


@app.get("/settings", response_class=HTMLResponse)
async def settings_page():
    p = Path(__file__).parent / "settings.html"
    return p.read_text(encoding="utf-8")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8765, reload=False)
