"""
claude_proxy.py — Thin wrapper kept for backward compatibility.

New code should use llm_client directly.
This module auto-detects git-bash and Claude credentials instead of hardcoding paths.
"""
import json
import os
import subprocess
from pathlib import Path

VISION_MODEL = "claude-sonnet-4-6"

_BASH_CANDIDATES = [
    os.environ.get("CLAUDE_BASH_PATH", ""),
    r"D:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files\Git\bin\bash.exe",
    "bash",
]
BASH_PATH = next((b for b in _BASH_CANDIDATES if b and (b == "bash" or Path(b).exists())), "bash")

_CREDS_CANDIDATES = [
    Path.home() / ".claude" / ".credentials.json",
    Path(__file__).resolve().parent.parent.parent / ".credentials.json",
]
CREDS_PATH = next((str(p) for p in _CREDS_CANDIDATES if p.exists()), "")


def _get_token() -> str:
    if not CREDS_PATH:
        raise FileNotFoundError("Claude credentials not found. Run 'claude login' first.")
    with open(CREDS_PATH, encoding="utf-8") as f:
        d = json.load(f)
    return d["claudeAiOauth"]["accessToken"]


def call_claude(prompt: str, max_tokens: int = 4096, timeout: int = 300) -> str:
    env = os.environ.copy()
    if BASH_PATH != "bash":
        env["CLAUDE_CODE_GIT_BASH_PATH"] = BASH_PATH
    try:
        result = subprocess.run(
            [BASH_PATH, "-c", "claude -p"],
            input=prompt, capture_output=True, text=True,
            encoding="utf-8", env=env, timeout=timeout,
        )
        if result.returncode != 0:
            print(f"[claude_proxy] error: {result.stderr.strip()[:200]}")
            return ""
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"[claude_proxy] timeout after {timeout}s")
        return ""
    except Exception as e:
        print(f"[claude_proxy] failed: {e}")
        return ""


def call_claude_with_image(prompt: str, image_path: str,
                           max_tokens: int = 1024, timeout: int = 180) -> str:
    import base64
    import anthropic

    ext = os.path.splitext(image_path)[-1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
    media_type = mime_map.get(ext, "image/jpeg")

    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.standard_b64encode(f.read()).decode()
    except Exception as e:
        print(f"[claude_proxy] image read failed: {e}, falling back to text")
        return call_claude(prompt, max_tokens, timeout)

    try:
        token = _get_token()
        client = anthropic.Anthropic(api_key=token)
        msg = client.messages.create(
            model=VISION_MODEL,
            max_tokens=max_tokens,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": media_type, "data": img_b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"[claude_proxy] vision call failed: {e}, falling back to text")
        return call_claude(prompt, max_tokens, timeout)


def is_available() -> bool:
    out = call_claude("ok")
    return bool(out)
