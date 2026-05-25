"""
用 AOM3 模型对 yuki_meina_s42.png 做脸部 inpainting
保留服装和构图，只换脸部画风
"""
import torch
from diffusers import StableDiffusionInpaintPipeline
from PIL import Image, ImageDraw, ImageFilter
import cv2
import numpy as np
import os

MODEL   = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
SRC     = r"C:\Users\Violet\.claude\yukibot\yuki_meina_s42.png"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot"

POSITIVE = (
    "masterpiece, best quality, "
    "1girl, "
    "pale skin, (highly detailed face:1.4), (beautiful detailed eyes:1.3), "
    "defined nose bridge, thin lips, cold expression, calm gaze, looking at viewer, "
    "long black hair, natural bangs"
)

NEGATIVE = (
    "worst quality, low quality, bad anatomy, "
    "blurry face, flat face, featureless, "
    "text, watermark, smile, open mouth, teeth, "
    "loli, childish, moe, baby face, round face, "
    "nsfw"
)

# ── 自动检测脸部区域，生成 mask ────────────────────────────────
img_cv = cv2.imread(SRC)
gray   = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(60, 60))

src_img = Image.open(SRC).convert("RGB")
W, H    = src_img.size

if len(faces) > 0:
    x, y, fw, fh = faces[0]
    # 扩大 mask 区域，包含发际线和下巴
    pad_x = int(fw * 0.35)
    pad_y_top = int(fh * 0.6)
    pad_y_bot = int(fh * 0.45)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y_top)
    x2 = min(W, x + fw + pad_x)
    y2 = min(H, y + fh + pad_y_bot)
    print(f"检测到脸部：({x},{y},{fw},{fh}) → mask ({x1},{y1},{x2},{y2})")
else:
    # 人脸检测失败时手动指定（meina s42 的脸大约在此区域）
    x1, y1, x2, y2 = 130, 20, 390, 260
    print(f"未检测到脸，使用默认 mask ({x1},{y1},{x2},{y2})")

mask = Image.new("L", (W, H), 0)
draw = ImageDraw.Draw(mask)
draw.ellipse([x1, y1, x2, y2], fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(radius=12))

mask.save(os.path.join(OUT_DIR, "yuki_face_mask.png"))

# ── 用 AOM3 inpainting ────────────────────────────────────────
print("加载 AOM3 inpaint 模型...")
pipe = StableDiffusionInpaintPipeline.from_single_file(
    MODEL, torch_dtype=torch.float16, safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

for seed in [42, 123, 789]:
    out_path = os.path.join(OUT_DIR, f"yuki_inpaint_s{seed}.png")
    print(f"inpaint seed={seed}...")
    generator = torch.Generator("cuda").manual_seed(seed)
    result = pipe(
        prompt=POSITIVE,
        negative_prompt=NEGATIVE,
        image=src_img,
        mask_image=mask,
        width=W, height=H,
        num_inference_steps=40,
        guidance_scale=8.0,
        strength=0.95,
        generator=generator,
    )
    result.images[0].save(out_path)
    print(f"保存：{out_path}")

del pipe
torch.cuda.empty_cache()
print("完成")
