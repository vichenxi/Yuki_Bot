# -*- coding: utf-8 -*-
"""Smoke test for memory/agent.py tool loop via Gemini (OpenAI-compatible)."""
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "memory"))
import agent

OUT = ROOT / "test_agent_out.txt"

TOOLS = [
    {"type": "function", "function": {
        "name": "get_current_time", "description": "返回当前北京时间 ISO 字符串",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "write_file", "description": "把文本写入指定文件",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"]}}},
]


def executor(name, args):
    if name == "get_current_time":
        return datetime.now(timezone(timedelta(hours=8))).isoformat()
    if name == "write_file":
        Path(args["path"]).write_text(args["content"], encoding="utf-8")
        return "written ok"
    return "unknown tool"


if __name__ == "__main__":
    llm = {"provider": "gemini", "model": "gemini-2.0-flash"}  # key from GEMINI_API_KEY
    out = agent.run_agent(
        system=f"你是测试助手。必须：1) 调用 get_current_time 取时间；2) 调用 write_file 把该时间写入 {OUT.as_posix()}；3) 最后回复 DONE。",
        user="开始执行。",
        tools=TOOLS, executor=executor, llm=llm, max_steps=8, verbose=True,
    )
    print("FINAL:", repr(out))
    print("FILE EXISTS:", OUT.exists(), "CONTENT:", OUT.read_text(encoding="utf-8") if OUT.exists() else "(none)")
