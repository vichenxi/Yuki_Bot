# -*- coding: utf-8 -*-
"""
agent.py — Provider-agnostic function-calling agent loop (方案 C)

让"雪的生活引擎"（Life Tick / 日记 / 归档 / 断联恢复）脱离 Anthropic CLI，改由
任意支持 tool-calling 的 LLM 通过工具循环驱动：模型请求工具 → 本地执行 → 回灌结果 →
直到模型给出最终文本。

支持两类后端（读 config.json 的 llm 块；provider）：
  - OpenAI 兼容：openai / deepseek / gemini / ollama / custom（用 openai SDK 的 tools）
  - anthropic：claude（用 anthropic SDK 的 tools；需真实 API key 或 oauth）

公开接口：
  run_agent(system, user, tools, executor, llm=None, max_steps=40, max_tokens=2048, verbose=False) -> str
    tools    : OpenAI function schema 列表 [{"type":"function","function":{name,description,parameters}}]
    executor : callable(name:str, args:dict) -> str   工具执行器（返回结果字符串）
"""
import json
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

_PROVIDER_URLS = {
    "openai":   "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "gemini":   "https://generativelanguage.googleapis.com/v1beta/openai",
    "ollama":   "http://localhost:11434/v1",
}
_ENV_KEYS = {
    "openai":   "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "gemini":   "GEMINI_API_KEY",
}


def _load_llm() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f).get("llm", {"provider": "claude", "model": "claude-sonnet-4-6"})


def _resolve_key(llm: dict) -> str:
    return llm.get("api_key") or os.environ.get(_ENV_KEYS.get(llm.get("provider", ""), ""), "")


def _to_anthropic_tools(tools: list) -> list:
    out = []
    for t in tools:
        fn = t["function"]
        out.append({"name": fn["name"], "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}})})
    return out


def _run_openai_compat(system, user, tools, executor, llm, max_steps, max_tokens, verbose) -> str:
    from openai import OpenAI
    provider = llm.get("provider", "openai")
    base_url = (llm.get("base_url") or _PROVIDER_URLS.get(provider, "https://api.openai.com/v1")).rstrip("/")
    client = OpenAI(base_url=base_url, api_key=_resolve_key(llm) or "none")
    model = llm.get("model", "gpt-4o-mini")

    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    for step in range(max_steps):
        resp = client.chat.completions.create(
            model=model, messages=messages, tools=tools, max_tokens=max_tokens,
        )
        msg = resp.choices[0].message
        asst = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            asst["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
        messages.append(asst)

        if not msg.tool_calls:
            return msg.content or ""

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            try:
                result = executor(name, args)
            except Exception as e:
                result = f"ERROR: {e}"
            if verbose:
                print(f"[agent] step{step} tool={name} args={str(args)[:120]} -> {str(result)[:120]}")
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)[:8000]})
    return "(agent: max_steps reached)"


def _run_anthropic(system, user, tools, executor, llm, max_steps, max_tokens, verbose) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=_resolve_key(llm)) if _resolve_key(llm) else anthropic.Anthropic()
    model = llm.get("model", "claude-sonnet-4-6")
    atools = _to_anthropic_tools(tools)
    messages = [{"role": "user", "content": user}]

    for step in range(max_steps):
        resp = client.messages.create(
            model=model, max_tokens=max_tokens, system=system, messages=messages, tools=atools,
        )
        content_blocks = []
        tool_uses = []
        text_out = []
        for b in resp.content:
            if b.type == "text":
                content_blocks.append({"type": "text", "text": b.text})
                text_out.append(b.text)
            elif b.type == "tool_use":
                content_blocks.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
                tool_uses.append(b)
        messages.append({"role": "assistant", "content": content_blocks})

        if not tool_uses:
            return "\n".join(text_out).strip()

        results = []
        for tu in tool_uses:
            try:
                result = executor(tu.name, tu.input or {})
            except Exception as e:
                result = f"ERROR: {e}"
            if verbose:
                print(f"[agent] step{step} tool={tu.name} -> {str(result)[:120]}")
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": str(result)[:8000]})
        messages.append({"role": "user", "content": results})
    return "(agent: max_steps reached)"


def run_agent(system: str, user: str, tools: list, executor, llm: dict = None,
              max_steps: int = 40, max_tokens: int = 2048, verbose: bool = False) -> str:
    """Run a provider-agnostic tool-calling loop. Returns the model's final text."""
    llm = llm or _load_llm()
    provider = llm.get("provider", "claude")
    if provider == "claude":
        return _run_anthropic(system, user, tools, executor, llm, max_steps, max_tokens, verbose)
    return _run_openai_compat(system, user, tools, executor, llm, max_steps, max_tokens, verbose)
