"""
img2img：以 yuki_meina_s42.png 为底，低强度精修脸部
"""
import torch
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import os

MODEL = r"E:\stable-diffusion-webui\models\Stable-Diffusion\meinamix_meinaV11.safetensors"
SRC   = r"C:\Users\Violet\.claude\yukibot\yuki_meina_s42.png"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot"

POSITIVE = (
    "masterpiece, best quality, "
    "1girl, solo, "
    "long black hair, straight hair, natural bangs, "
    "pale skin, (detailed face:1.3), (beautiful detailed eyes:1.2), "
    "defined nose bridge, thin lips, cold expression, calm gaze, looking at viewer, "
    "dark navy long skirt, white button-up blouse, tucked in, "
    "full body, standing by window, soft natural daylight, "
    "slim, quiet, elegant, art student"
)

NEGATIVE = (
    "worst quality, low quality, bad anatomy, bad hands, "
    "extra fingers, missing fingers, deformed, "
    "(blurry face:1.3), (flat face:1.2), featureless, "
    "text, watermark, smile, open mouth, "
    "loli, childish, moe, baby face, round face, "
    "sexy, suggestive, nsfw"
)

print("加载模型...")
pipe = StableDiffusionImg2ImgPipeline.from_single_file(
    MODEL,
    torch_dtype=torch.float16,
    safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

src_image = Image.open(SRC).convert("RGB")

for strength in [0.35, 0.45]:
    out_path = os.path.join(OUT_DIR, f"yuki_refined_{int(strength*100)}.png")
    print(f"生成 strength={strength}...")
    generator = torch.Generator("cuda").manual_seed(42)
    result = pipe(
        prompt=POSITIVE,
        negative_prompt=NEGATIVE,
        image=src_image,
        strength=strength,
        num_inference_steps=40,
        guidance_scale=7.5,
        generator=generator,
    )
    result.images[0].save(out_path)
    print(f"保存：{out_path}")

del pipe
torch.cuda.empty_cache()
print("完成")
