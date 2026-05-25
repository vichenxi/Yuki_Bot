"""
从 yuki_final_v2.png 裁切半身像和胸像，Real-ESRGAN 锐化
半身：腰部以上
胸像：胸线以上（头肩）
"""
import cv2
import os
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

SRC = r"C:\Users\Violet\.claude\yukibot\yuki_final_v2.png"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot"
ESRGAN_PATH = r"C:\Users\Violet\.claude\yukibot\weights\RealESRGAN_x4plus_anime_6B.pth"

img = cv2.imread(SRC, cv2.IMREAD_COLOR)
H, W = img.shape[:2]
print(f"原图尺寸：{W}x{H}")

# 胸像：顶部 42%（头 + 肩 + 胸线）
bust_h = int(H * 0.42)
bust   = img[0:bust_h, 0:W]

# 半身：顶部 62%（头 + 上半身 + 腰）
half_h = int(H * 0.62)
half   = img[0:half_h, 0:W]

print("加载 Real-ESRGAN...")
model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                num_block=6, num_grow_ch=32, scale=4)
upsampler = RealESRGANer(
    scale=4, model_path=ESRGAN_PATH, model=model,
    tile=256, tile_pad=10, pre_pad=0, half=True,
)

for name, crop in [("bust", bust), ("halfbody", half)]:
    print(f"处理 {name}...")
    out_crop, _ = upsampler.enhance(crop, outscale=2)
    out_path = os.path.join(OUT_DIR, f"yuki_{name}.png")
    cv2.imwrite(out_path, out_crop)
    print(f"保存：{out_path}  {crop.shape[:2][::-1]} → {out_crop.shape[:2][::-1]}")

print("完成")
