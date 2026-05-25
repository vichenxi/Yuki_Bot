# -*- coding: utf-8 -*-
"""
llm_client.py — Universal LLM client

Reads llm config from config.json:
  provider : "claude" | "openai" | "deepseek" | "gemini" | "ollama" | "custom"
  model    : model name string
  api_key  : API key (leave empty for claude-cli mode or ollama)
  base_url : override endpoint (auto-detected for known providers)

Public API:
  chat(prompt, max_tokens, timeout) -> str
  chat_with_image(prompt, image_path, max_tokens, timeout) -> str
"""
import base64
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE / "config.json"

_PROVIDER_URLS = {
    "openai":   "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "gemini":   "https://generativelanguage.googleapis.com/v1beta/openai",
    "ollama":   "http://localhost:11434/v1",
}


def _load_cfg() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        full = json.load(f)
    return full.get("llm", {"provider": "claude", "model": "claude-sonnet-4-6"})


def _openai_compat(messages: list, llm: dict, max_tokens: int, timeout: int) -> str:
    provider = llm.get("provider", "openai")
    base_url = (llm.get("base_url") or _PROVIDER_URLS.get(provider, "https://api.openai.com/v1")).rstrip("/")
    api_key  = llm.get("api_key", "")
    model    = llm.get("model", "gpt-4o-mini")

    payload = json.dumps(
        {"model": model, "messages": messages, "max_tokens": max_tokens},
        ensure_ascii=False,
    ).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(f"{base_url}/chat/completions", data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[llm_client] HTTP {e.code}: {body[:300]}")
        return ""
    except Exception as e:
        print(f"[llm_client] request error: {e}")
        return ""


def _claude_cli(prompt: str, timeout: int) -> str:
    bash_candidates = [
        os.environ.get("CLAUDE_BASH_PATH", ""),
        r"D:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\bin\bash.exe",
        "bash",
    ]
    bash = next((b for b in bash_candidates if b and (b == "bash" or Path(b).exists())), "bash")
    env = os.environ.copy()
    if bash != "bash":
        env["CLAUDE_CODE_GIT_BASH_PATH"] = bash
    try:
        r = subprocess.run(
            [bash, "-c", "claude -p"],
            input=prompt, capture_output=True, text=True,
            encoding="utf-8", env=env, timeout=timeout,
        )
        if r.returncode != 0:
            print(f"[llm_client] claude -p error: {r.stderr.strip()[:200]}")
            return ""
        return r.stdout.strip()
    except Exception as e:
        print(f"[llm_client] claude -p failed: {e}")
        return ""


def _claude_sdk(messages: list, llm: dict, max_tokens: int, timeout: int) -> str:
    try:
        import anthropic
    except ImportError:
        print("[llm_client] anthropic package not installed")
        return ""

    api_key = llm.get("api_key", "")
    if not api_key:
        for cred in [Path.home() / ".claude" / ".credentials.json",
                     BASE.parent / ".credentials.json"]:
            if cred.exists():
                try:
                    d = json.loads(cred.read_text(encoding="utf-8"))
                    api_key = d.get("claudeAiOauth", {}).get("accessToken", "")
                    if api_key:
                        break
                except Exception:
                    pass

    model = llm.get("model", "claude-sonnet-4-6")
    try:
        client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        msg = client.messages.create(model=model, max_tokens=max_tokens, messages=messages)
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"[llm_client] anthropic SDK error: {e}")
        return ""


def chat(prompt: str, max_tokens: int = 1024, timeout: int = 120) -> str:
    """Send a text prompt, return the reply string."""
    llm = _load_cfg()
    provider = llm.get("provider", "claude")

    if provider == "claude":
        result = _claude_cli(prompt, timeout)
        if result:
            return result
        return _claude_sdk([{"role": "user", "content": prompt}], llm, max_tokens, timeout)

    return _openai_compat([{"role": "user", "content": prompt}], llm, max_tokens, timeout)


def chat_with_image(prompt: str, image_path: str, max_tokens: int = 1024, timeout: int = 180) -> str:
    """Send a prompt with a local image, return the reply string."""
    llm = _load_cfg()
    provider = llm.get("provider", "claude")

    ext = os.path.splitext(image_path)[-1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
    media_type = mime_map.get(ext, "image/jpeg")

    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.standard_b64encode(f.read()).decode()
    except Exception as e:
        print(f"[llm_client] image read failed: {e}, falling back to text")
        return chat(prompt, max_tokens=max_tokens, timeout=timeout)

    if provider == "claude":
        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_b64}},
                {"type": "text", "text": prompt},
            ],
        }]
        result = _claude_sdk(messages, llm, max_tokens, timeout)
        if result:
            return result
        return chat(prompt, max_tokens=max_tokens, timeout=timeout)

    # OpenAI vision format
    messages = [{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{img_b64}"}},
            {"type": "text", "text": prompt},
        ],
    }]
    return _openai_compat(messages, llm, max_tokens, timeout)
