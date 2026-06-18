"""Call Claude via the claude CLI (git-bash), replacing direct API key usage."""
import subprocess
import os

BASH_PATH = "D:\\Program Files\\Git\\bin\\bash.exe"
GIT_BASH_ENV_KEY = "CLAUDE_CODE_GIT_BASH_PATH"


def call_claude(prompt: str, max_tokens: int = 4096, timeout: int = 300) -> str:
    """Send a prompt to Claude via claude -p and return the response text."""
    env = os.environ.copy()
    env[GIT_BASH_ENV_KEY] = BASH_PATH

    try:
        result = subprocess.run(
            [BASH_PATH, "-c", "claude -p"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=timeout,
        )
        if result.returncode != 0:
            err = result.stderr.strip()
            print(f"[claude_proxy] error: {err[:200]}")
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
    """Send a prompt with a local image to Claude via CLI stream-json."""
    import base64
    import json as _json

    if not os.path.exists(image_path):
        print(f"[claude_proxy] 图片不存在：{image_path}，降级为纯文字")
        return call_claude(prompt, max_tokens, timeout)

    ext = os.path.splitext(image_path)[-1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
    media_type = mime_map.get(ext, "image/jpeg")

    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.standard_b64encode(f.read()).decode()
    except Exception as e:
        print(f"[claude_proxy] 图片读取失败：{e}，降级为纯文字")
        return call_claude(prompt, max_tokens, timeout)

    payload = _json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": media_type, "data": img_b64}},
                {"type": "text", "text": prompt},
            ]
        }
    }, ensure_ascii=False)

    env = os.environ.copy()
    env[GIT_BASH_ENV_KEY] = BASH_PATH

    try:
        result = subprocess.run(
            [BASH_PATH, "-c",
             "claude -p --verbose --input-format stream-json --output-format stream-json"],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=timeout,
        )
        if result.returncode != 0:
            err = result.stderr.strip()
            print(f"[claude_proxy] image error (rc={result.returncode}): {err[:200]}，降级为纯文字")
            return call_claude(prompt, max_tokens, timeout)

        texts = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = _json.loads(line)
                if ev.get("type") == "assistant":
                    for block in ev.get("message", {}).get("content", []):
                        if block.get("type") == "text":
                            texts.append(block["text"])
            except Exception:
                pass
        text = "\n".join(texts).strip()
        if not text:
            print("[claude_proxy] image call 返回空，降级为纯文字")
            return call_claude(prompt, max_tokens, timeout)
        return text

    except subprocess.TimeoutExpired:
        print(f"[claude_proxy] image timeout after {timeout}s，降级为纯文字")
        return call_claude(prompt, max_tokens, timeout)
    except Exception as e:
        print(f"[claude_proxy] image failed: {e}，降级为纯文字")
        return call_claude(prompt, max_tokens, timeout)


def is_available() -> bool:
    """Quick check that the proxy can reach claude."""
    out = call_claude("ok")
    return bool(out)
