# -*- coding: utf-8 -*-
"""
check_tg_updates.py — Life Tick 实时消息扫描

每次 Life Tick 开始时调用，查询 Telegram 是否有未处理的新消息。
- 若 tg_daemon 正常运行：只补充 DB 上下文（不发送，避免重复）
- 若 tg_daemon 未运行：补充 DB 上下文 + 调用 handle_reply.py 自动回复

输出 JSON（stdout）：
  {"new_count": N, "messages": [...], "replied": bool, "daemon_running": bool}
"""

import json
import os
import sys
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE    = Path(__file__).resolve().parent.parent
DATA    = BASE / "data"
CONFIG  = BASE / "config.json"
OFFSET  = DATA / "tg_offset.json"
PENDING_REPLY = DATA / "pending_reply.json"
LT_IF   = BASE / "memory" / "lt_interface.py"
HANDLE  = BASE / "core" / "handle_reply.py"
TG_PID  = BASE / "tg_daemon.pid"

CST = timezone(timedelta(hours=8))


def now_cst() -> datetime:
    return datetime.now(CST)


def now_iso() -> str:
    return now_cst().isoformat()


def load_config() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def read_offset() -> int:
    if OFFSET.exists():
        try:
            return json.loads(OFFSET.read_text(encoding="utf-8-sig")).get("offset", 0)
        except Exception:
            pass
    return 0


def save_offset(offset: int):
    OFFSET.write_text(json.dumps({"offset": offset}), encoding="utf-8")


def ts_to_iso(unix_ts: int) -> str:
    return datetime.fromtimestamp(unix_ts, tz=CST).isoformat()


def get_updates(token: str, offset: int) -> list:
    url = (
        f"https://api.telegram.org/bot{token}/getUpdates"
        f"?offset={offset}&timeout=0&allowed_updates=[\"message\"]"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("result", [])
    except Exception:
        return []


def add_to_db(subcmd: str, payload: dict):
    subprocess.run(
        ["python", str(LT_IF), subcmd, json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True, encoding="utf-8"
    )


def daemon_is_running() -> bool:
    if not TG_PID.exists():
        return False
    try:
        pid = int(TG_PID.read_text().strip())
        r = subprocess.run(
            f'tasklist /FI "PID eq {pid}" /NH',
            capture_output=True, shell=True
        )
        return str(pid).encode() in r.stdout
    except Exception:
        return False


def main():
    cfg = load_config()
    token = cfg["bot_token"]
    chat_id = str(cfg["default_chat_id"])

    # tg_daemon 正在运行时跳过 getUpdates，避免与长轮询同时请求产生 409
    if daemon_is_running():
        print(json.dumps({"new_count": 0, "messages": [], "replied": False, "daemon_running": True}))
        return

    offset = read_offset()
    updates = get_updates(token, offset)

    if not updates:
        print(json.dumps({"new_count": 0, "messages": [], "replied": False,
                           "daemon_running": daemon_is_running()}))
        return

    new_messages = []
    max_uid = offset - 1

    for upd in updates:
        uid = upd.get("update_id", 0)
        max_uid = max(max_uid, uid)
        msg = upd.get("message")
        if not msg:
            continue
        if str(msg.get("chat", {}).get("id", "")) != chat_id:
            continue
        text = msg.get("text", "") or msg.get("caption", "") or "[非文字消息]"
        new_messages.append({
            "update_id": uid,
            "text": text,
            "ts": ts_to_iso(msg.get("date", 0)),
            "from": msg.get("from", {}).get("first_name", ""),
        })

    new_offset = max_uid + 1
    if new_offset > offset:
        save_offset(new_offset)

    replied = False
    running = daemon_is_running()

    if new_messages:
        today = now_cst().strftime("%Y-%m-%d")
        # 存入对话 DB（供 Life Tick 读取上下文）
        for m in new_messages:
            add_to_db("add_conversation", {
                "role": "user",
                "content": m["text"],
                "ts": m["ts"]
            })

        # 若 tg_daemon 未运行，调用 handle_reply.py 自动回复
        if not running:
            try:
                payload = {
                    "requested_at": now_iso(),
                    "messages": new_messages,
                }
                PENDING_REPLY.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                r = subprocess.run(
                    ["python", str(HANDLE)],
                    capture_output=True, text=True, encoding="utf-8",
                    cwd=str(BASE), timeout=90
                )
                replied = r.returncode == 0
            except Exception:
                PENDING_REPLY.unlink(missing_ok=True)

    print(json.dumps({
        "new_count": len(new_messages),
        "messages": [{"text": m["text"], "ts": m["ts"]} for m in new_messages],
        "replied": replied,
        "daemon_running": running,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
