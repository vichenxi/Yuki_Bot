# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from send_voice import send_voice
import json

# 日语语音，符合当前语境（刚买了截奇怪的胶带，随口一句）
result = send_voice("なんか変な色のテープ買っちゃった[emotion: neutral]")
print(json.dumps({
    "ok": result.get("ok"),
    "msg_id": result.get("result", {}).get("message_id"),
    "duration": result.get("result", {}).get("voice", {}).get("duration"),
}, ensure_ascii=False))
