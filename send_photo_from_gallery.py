"""
从预生成图库随机取一张图发给薰。
用法：python send_photo_from_gallery.py [chat_id]
图库：C:/Users/Violet/.claude/yukibot/controlnet_matrix/with_lora/*.png
"""
import json, os, sys, random
import urllib.request

BASE        = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "config.json")
GALLERY_DIR = os.path.join(BASE, "controlnet_matrix", "with_lora")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def send_photo(chat_id: str = None) -> dict:
    cfg     = load_config()
    token   = cfg["bot_token"]
    chat_id = chat_id or str(cfg["default_chat_id"])

    candidates = [
        os.path.join(GALLERY_DIR, f)
        for f in os.listdir(GALLERY_DIR)
        if f.lower().endswith(".png")
    ] if os.path.isdir(GALLERY_DIR) else []

    if not candidates:
        raise RuntimeError(f"图库为空：{GALLERY_DIR}")

    chosen = random.choice(candidates)
    print(f"[send_photo] 发送：{os.path.basename(chosen)}", file=sys.stderr)

    boundary = "yuki_photo_bdry"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n"
    ).encode()
    with open(chosen, "rb") as f:
        body += (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"photo.png\"\r\n"
            f"Content-Type: image/png\r\n\r\n"
        ).encode() + f.read() + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


if __name__ == "__main__":
    cid    = sys.argv[1] if len(sys.argv) > 1 else None
    result = send_photo(cid)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result.get("ok") else 1)
