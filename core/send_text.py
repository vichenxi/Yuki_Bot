# -*- coding: utf-8 -*-
"""
send_text.py — 文字消息直发工具（urllib 直连 Telegram Bot API，不依赖任何插件）

用法：
  python core/send_text.py "要发送的一条消息" [chat_id]

token / 默认 chat_id 读自仓库根目录 config.json。
退出码：0 = 成功；非 0 = 失败（调用方可据此降级）。
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
CONFIG_PATH = os.path.join(ROOT, "config.json")


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def send_message(token: str, chat_id: str, text: str) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({"chat_id": chat_id, "text": text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("usage: send_text.py \"message\" [chat_id]", file=sys.stderr)
        return 2

    text = sys.argv[1]
    cfg = load_config()
    token = cfg["bot_token"]
    chat_id = str(sys.argv[2]) if len(sys.argv) >= 3 else str(cfg["default_chat_id"])

    last_err = None
    for attempt in range(3):
        try:
            result = send_message(token, chat_id, text)
            if result.get("ok"):
                print(f"[send_text] ok message_id={result['result'].get('message_id')}")
                return 0
            last_err = result
        except Exception as e:
            last_err = e
        time.sleep(1.5 * (attempt + 1))

    print(f"[send_text] 发送失败：{last_err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
