"""
A: 纯 Real-ESRGAN 放大，不做脸部修复
B: GFPGAN weight=0.3（轻微修复）
"""
import os
import numpy as np
import cv2

SRC = r"C:\Users\Violet\.claude\yukibot\yuki_meina_s42.png"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot"
WEIGHTS_DIR = r"C:\Users\Violet\.claude\yukibot\weights"
GFPGAN_PATH = os.path.join(WEIGHTS_DIR, "GFPGANv1.4.pth")
ESRGAN_PATH = os.path.join(WEIGHTS_DIR, "RealESRGAN_x4plus_anime_6B.pth")

img_bgr = cv2.imread(SRC, cv2.IMREAD_COLOR)

# ── 共用：Real-ESRGAN 放大 ─────────────────────────────────────
print("Real-ESRGAN 放大...")
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                num_block=6, num_grow_ch=32, scale=4)
upsampler = RealESRGANer(
    scale=4, model_path=ESRGAN_PATH, model=model,
    tile=256, tile_pad=10, pre_pad=0, half=True,
)
upscaled, _ = upsampler.enhance(img_bgr, outscale=2)
print(f"放大：{img_bgr.shape[:2]} → {upscaled.shape[:2]}")

# ── A: 纯放大，不动脸 ─────────────────────────────────────────
out_a = os.path.join(OUT_DIR, "yuki_upscale_only.png")
cv2.imwrite(out_a, upscaled)
print(f"A 保存：{out_a}")

# ── B: GFPGAN weight=0.3 ─────────────────────────────────────
print("GFPGAN 修复 weight=0.3...")
from gfpgan import GFPGANer

restorer = GFPGANer(
    model_path=GFPGAN_PATH, upscale=1,
    arch="clean", channel_multiplier=2, bg_upsampler=None,
)
_, _, restored = restorer.enhance(
    upscaled, has_aligned=False,
    only_center_face=False, paste_back=True,
    weight=0.3,
)
out_b = os.path.join(OUT_DIR, "yuki_gfpgan_03.png")
cv2.imwrite(out_b, restored)
print(f"B 保存：{out_b}")

print("完成")
