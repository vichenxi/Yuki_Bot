# -*- coding: utf-8 -*-
"""Deterministic mock test of memory/agent.py loop mechanics (no live API)."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "memory"))
import openai
import agent

OUT = ROOT / "test_agent_out.txt"
if OUT.exists():
    OUT.unlink()

_n = {"i": 0}


def _msg(content, tool_calls):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _tc(cid, name, args):
    return SimpleNamespace(id=cid, function=SimpleNamespace(name=name, arguments=json.dumps(args)))


class _Comp:
    def create(self, model, messages, tools, max_tokens):
        _n["i"] += 1
        i = _n["i"]
        if i == 1:
            return SimpleNamespace(choices=[SimpleNamespace(message=_msg(None, [_tc("c1", "get_current_time", {})]))])
        if i == 2:
            return SimpleNamespace(choices=[SimpleNamespace(message=_msg(
                None, [_tc("c2", "write_file", {"path": str(OUT), "content": "MOCK-TIME"})]))])
        return SimpleNamespace(choices=[SimpleNamespace(message=_msg("DONE", None))])


class _FakeOpenAI:
    def __init__(self, **kw):
        self.chat = SimpleNamespace(completions=_Comp())


openai.OpenAI = _FakeOpenAI

executed = []


def executor(name, args):
    executed.append(name)
    if name == "get_current_time":
        return "2026-06-18T15:00:00+08:00"
    if name == "write_file":
        Path(args["path"]).write_text(args["content"], encoding="utf-8")
        return "written ok"
    return "unknown"


TOOLS = [
    {"type": "function", "function": {"name": "get_current_time", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "write_file", "parameters": {"type": "object", "properties": {}}}},
]

out = agent.run_agent("system", "go", TOOLS, executor,
                      llm={"provider": "openai", "model": "x", "api_key": "k"},
                      max_steps=6, verbose=True)
print("FINAL:", repr(out))
print("executed:", executed)
print("file content:", OUT.read_text(encoding="utf-8") if OUT.exists() else None)
assert out == "DONE", "final text mismatch"
assert executed == ["get_current_time", "write_file"], "tool exec order mismatch"
assert OUT.exists() and OUT.read_text(encoding="utf-8") == "MOCK-TIME", "file not written"
print("MOCK LOOP TEST PASSED")
OUT.unlink()
