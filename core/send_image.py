"""
雪的图片发送工具
用法：
  python send_image.py url "https://..." ["caption"]       # 下载URL图片发送
  python send_image.py generate "场景描述（中文）" ["caption"]  # 本地SD生成后发送

generate 模式使用 HuggingFace diffusers 直接加载本地模型，无需运行 A1111 服务器。
"""
import json
import os
import sys
import tempfile
import urllib.request

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
MODEL_PATH = r"E:\stable-diffusion-webui\models\Stable-Diffusion\Realistic_Vision_V5.1_fp16.safetensors"

# 手机随拍风格词
_SNAP_POSITIVE = (
    "shot on iphone, casual snapshot, candid, lo-fi, film grain, "
    "slightly overexposed, natural lighting, real photo, everyday life, "
    "amateur photography, handheld"
)
_SNAP_NEGATIVE = (
    "studio lighting, professional photography, HDR, artificial light, "
    "oversaturated, watermark, text, logo, render, 3d, anime, painting"
)


def _load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _send_photo_file(filepath: str, caption: str, chat_id: str) -> dict:
    """multipart 上传本地图片到 Telegram sendPhoto。"""
    cfg = _load_config()
    token = cfg["bot_token"]
    url = f"https://api.telegram.org/bot{token}/sendPhoto"

    boundary = "yukibot_boundary_xyz"

    def part(name: str, value: str) -> bytes:
        return (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode("utf-8")

    with open(filepath, "rb") as f:
        img_data = f.read()

    ext = os.path.splitext(filepath)[1] or ".jpg"
    mime = "image/png" if ext == ".png" else "image/jpeg"

    body = b""
    body += part("chat_id", chat_id)
    if caption:
        body += part("caption", caption)
    body += (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="photo"; filename="photo{ext}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8")
    body += img_data
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def send_url(image_url: str, caption: str = "", chat_id: str = None) -> dict:
    """下载远程图片后发送。"""
    cfg = _load_config()
    if chat_id is None:
        chat_id = cfg["default_chat_id"]

    print(f"[send_image] downloading {image_url}", file=sys.stderr)
    req = urllib.request.Request(
        image_url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            with open(tmp_path, "wb") as f:
                f.write(resp.read())
        return _send_photo_file(tmp_path, caption, chat_id)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def send_generate(scene_prompt: str, caption: str = "", chat_id: str = None) -> dict:
    """用本地 diffusers 生成手机随拍风图片后发送（无需 A1111 服务器）。"""
    import torch
    from diffusers import StableDiffusionPipeline

    cfg = _load_config()
    if chat_id is None:
        chat_id = cfg["default_chat_id"]

    full_prompt = f"{scene_prompt}, {_SNAP_POSITIVE}"
    print(f"[send_image] loading model from {MODEL_PATH}", file=sys.stderr)

    pipe = StableDiffusionPipeline.from_single_file(
        MODEL_PATH,
        torch_dtype=torch.float16,
        safety_checker=None,
    )
    pipe = pipe.to("cuda")
    pipe.enable_attention_slicing()

    print(f"[send_image] generating: {full_prompt[:80]}...", file=sys.stderr)
    result = pipe(
        prompt=full_prompt,
        negative_prompt=_SNAP_NEGATIVE,
        width=512,
        height=768,
        num_inference_steps=25,
        guidance_scale=6.5,
    )
    image = result.images[0]

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    image.save(tmp_path)

    try:
        return _send_photo_file(tmp_path, caption, chat_id)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法：")
        print('  python send_image.py url "https://..." ["caption"]')
        print('  python send_image.py generate "场景描述" ["caption"]')
        sys.exit(1)

    mode = sys.argv[1]
    arg = sys.argv[2]
    cap = sys.argv[3] if len(sys.argv) > 3 else ""

    if mode == "url":
        res = send_url(arg, cap)
    elif mode == "generate":
        res = send_generate(arg, cap)
    else:
        print(f"未知模式：{mode}（应为 url 或 generate）", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(res, ensure_ascii=False, indent=2))
