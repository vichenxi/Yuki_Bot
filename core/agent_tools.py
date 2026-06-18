# -*- coding: utf-8 -*-
"""
agent_tools.py — 雪生活引擎的工具集（供 memory/agent.py 的工具循环调用）

把原本"让 claude agent 用 Bash 跑 lt_interface / 读写文件 / 发消息"的能力，
封装成一组 provider 无关的本地函数 + OpenAI function schema。

对外：
  TOOLS            : OpenAI function schema 列表（传给 run_agent）
  execute(name, args) -> str : 工具执行器（传给 run_agent）
"""
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LT_IF = ROOT / "memory" / "lt_interface.py"
CONFIG = ROOT / "config.json"
CST = timezone(timedelta(hours=8))


def _lt(*args) -> str:
    r = subprocess.run([sys.executable, str(LT_IF), *args],
                       capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    out = (r.stdout or "").strip()
    return out if out else (r.stderr or "").strip()


def _cfg() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


# ── 工具实现 ─────────────────────────────────────────────────────────
def get_current_time() -> str:
    return datetime.now(CST).isoformat()


def get_life_context(date: str) -> str:
    return _lt("get_life_context", date)


def add_life_log(entry: dict) -> str:
    return _lt("add_life_log", json.dumps(entry, ensure_ascii=False))


def get_conversations(date: str, limit: int = 30) -> str:
    return _lt("get_conversations", date, str(limit))


def add_conversation(entry: dict) -> str:
    return _lt("add_conversation", json.dumps(entry, ensure_ascii=False))


def get_memory_context(query: str) -> str:
    return _lt("get_memory_context", query)


def get_today_sent(date: str) -> str:
    return _lt("get_today_sent", date)


def get_unread() -> str:
    return _lt("get_unread")


def read_file(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"(file not found: {path})"
    except Exception as e:
        return f"ERROR reading {path}: {e}"


def write_file(path: str, content: str) -> str:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"written {path} ({len(content)} chars)"
    except Exception as e:
        return f"ERROR writing {path}: {e}"


def send_text(text: str, chat_id: str = None) -> str:
    cfg = _cfg()
    token = cfg["bot_token"]
    cid = str(chat_id or cfg["default_chat_id"])
    body = json.dumps({"chat_id": cid, "text": text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=body,
        headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            ok = json.loads(r.read()).get("ok")
            return "sent ok" if ok else "send failed"
    except Exception as e:
        return f"ERROR send: {e}"


def web_search(query: str) -> str:
    # 本部署未接入搜索 API；返回明确提示，让模型自然降级（不要编造链接）
    return "（web_search 未配置：基于已知内容自然表达即可，不要编造链接或具体出处）"


_REGISTRY = {
    "get_current_time": get_current_time,
    "get_life_context": get_life_context,
    "add_life_log": add_life_log,
    "get_conversations": get_conversations,
    "add_conversation": add_conversation,
    "get_memory_context": get_memory_context,
    "get_today_sent": get_today_sent,
    "get_unread": get_unread,
    "read_file": read_file,
    "write_file": write_file,
    "send_text": send_text,
    "web_search": web_search,
}


def execute(name: str, args: dict) -> str:
    fn = _REGISTRY.get(name)
    if fn is None:
        return f"unknown tool: {name}"
    try:
        return str(fn(**(args or {})))
    except TypeError as e:
        return f"ERROR bad args for {name}: {e}"


def _obj(props, required=None):
    return {"type": "object", "properties": props, "required": required or []}


TOOLS = [
    {"type": "function", "function": {"name": "get_current_time",
        "description": "返回当前北京时间(UTC+8) ISO 字符串", "parameters": _obj({})}},
    {"type": "function", "function": {"name": "get_life_context",
        "description": "读取某日生活日志，返回 JSON（含 entries/last_ts/last_mood/last_valence/last_arousal/today_sent）",
        "parameters": _obj({"date": {"type": "string", "description": "YYYY-MM-DD"}}, ["date"])}},
    {"type": "function", "function": {"name": "add_life_log",
        "description": "追加一条生活日志到数据库",
        "parameters": _obj({"entry": {"type": "object", "description": "含 ts/activity/mood/mood_valence/mood_arousal/emotional_note/should_message/message_type/message_seed 等字段"}}, ["entry"])}},
    {"type": "function", "function": {"name": "get_conversations",
        "description": "读取某日对话记录（JSON 数组）",
        "parameters": _obj({"date": {"type": "string"}, "limit": {"type": "integer"}}, ["date"])}},
    {"type": "function", "function": {"name": "add_conversation",
        "description": "追加一条对话记录到数据库",
        "parameters": _obj({"entry": {"type": "object", "description": "含 role/content/ts 等"}}, ["entry"])}},
    {"type": "function", "function": {"name": "get_memory_context",
        "description": "按查询词检索长期记忆上下文（纯文本）",
        "parameters": _obj({"query": {"type": "string"}}, ["query"])}},
    {"type": "function", "function": {"name": "get_today_sent",
        "description": "返回某日雪已主动发消息的条数",
        "parameters": _obj({"date": {"type": "string"}}, ["date"])}},
    {"type": "function", "function": {"name": "get_unread",
        "description": "返回睡眠期间积压的未读消息（JSON）", "parameters": _obj({})}},
    {"type": "function", "function": {"name": "read_file",
        "description": "读取文本文件内容", "parameters": _obj({"path": {"type": "string"}}, ["path"])}},
    {"type": "function", "function": {"name": "write_file",
        "description": "把文本写入文件（覆盖）", "parameters": _obj({"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"])}},
    {"type": "function", "function": {"name": "send_text",
        "description": "通过 Telegram 给薰发一条文字消息",
        "parameters": _obj({"text": {"type": "string"}, "chat_id": {"type": "string"}}, ["text"])}},
    {"type": "function", "function": {"name": "web_search",
        "description": "联网搜索（若未配置则返回提示，按提示降级）",
        "parameters": _obj({"query": {"type": "string"}}, ["query"])}},
]
