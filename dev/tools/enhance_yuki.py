"""
对 yuki_meina_s42.png 做脸部修复（GFPGAN）+ 放大（Real-ESRGAN anime）
输出：yuki_enhanced.png
"""
import urllib.request
import os
import numpy as np
import cv2
from PIL import Image

SRC  = r"C:\Users\Violet\.claude\yukibot\yuki_meina_s42.png"
OUT  = r"C:\Users\Violet\.claude\yukibot\yuki_enhanced.png"
WEIGHTS_DIR = r"C:\Users\Violet\.claude\yukibot\weights"

os.makedirs(WEIGHTS_DIR, exist_ok=True)

GFPGAN_URL  = "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth"
ESRGAN_URL  = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth"
GFPGAN_PATH = os.path.join(WEIGHTS_DIR, "GFPGANv1.4.pth")
ESRGAN_PATH = os.path.join(WEIGHTS_DIR, "RealESRGAN_x4plus_anime_6B.pth")


def download(url, path):
    if os.path.exists(path):
        print(f"已存在：{os.path.basename(path)}")
        return
    print(f"下载 {os.path.basename(path)}...")
    urllib.request.urlretrieve(url, path)
    print("完成")


download(GFPGAN_URL, GFPGAN_PATH)
download(ESRGAN_URL, ESRGAN_PATH)

# ── Real-ESRGAN 放大 ────────────────────────────────────────────
print("\n[1/2] Real-ESRGAN 放大（anime 4x）...")
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                num_block=6, num_grow_ch=32, scale=4)
upsampler = RealESRGANer(
    scale=4,
    model_path=ESRGAN_PATH,
    model=model,
    tile=256,
    tile_pad=10,
    pre_pad=0,
    half=True,
)

img_bgr = cv2.imread(SRC, cv2.IMREAD_COLOR)
output_bgr, _ = upsampler.enhance(img_bgr, outscale=2)  # 放大 2x（512→1024）
print(f"放大完成：{img_bgr.shape[:2]} → {output_bgr.shape[:2]}")

# ── GFPGAN 脸部修复 ─────────────────────────────────────────────
print("\n[2/2] GFPGAN 脸部修复...")
from gfpgan import GFPGANer

restorer = GFPGANer(
    model_path=GFPGAN_PATH,
    upscale=1,
    arch="clean",
    channel_multiplier=2,
    bg_upsampler=None,
)

_, _, restored_bgr = restorer.enhance(
    output_bgr,
    has_aligned=False,
    only_center_face=False,
    paste_back=True,
    weight=0.7,   # 修复强度，0=原图，1=全修复
)

cv2.imwrite(OUT, restored_bgr)
print(f"\n保存：{OUT}")
