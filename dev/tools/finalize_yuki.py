import os, cv2
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

SRC  = r"C:\Users\Violet\.claude\yukibot\yuki_warm_s789.png"
OUT  = r"C:\Users\Violet\.claude\yukibot\yuki_final_v2.png"
ESRGAN_PATH = r"C:\Users\Violet\.claude\yukibot\weights\RealESRGAN_x4plus_anime_6B.pth"

model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                num_block=6, num_grow_ch=32, scale=4)
upsampler = RealESRGANer(
    scale=4, model_path=ESRGAN_PATH, model=model,
    tile=256, tile_pad=10, pre_pad=0, half=True,
)

img = cv2.imread(SRC, cv2.IMREAD_COLOR)
output, _ = upsampler.enhance(img, outscale=2)
cv2.imwrite(OUT, output)
print(f"完成：{OUT}  {img.shape[:2]} → {output.shape[:2]}")
