"""
高分辨率生成雪，脸部细节更丰富
"""
import torch
from diffusers import StableDiffusionPipeline
import os

MODEL = r"E:\stable-diffusion-webui\models\Stable-Diffusion\meinamix_meinaV11.safetensors"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot"

POSITIVE = (
    "masterpiece, best quality, "
    "1girl, solo, 23 years old, "
    "long black hair, straight hair, natural bangs, "
    "pale skin, detailed face, beautiful detailed eyes, "
    "defined nose bridge, thin lips, cold expression, calm gaze, looking at viewer, "
    "dark navy long skirt, white button-up blouse, tucked in, "
    "simple minimalist outfit, everyday clothing, "
    "full body, standing by window, soft natural daylight, clean room, "
    "slim, quiet, elegant, art student"
)

NEGATIVE = (
    "worst quality, low quality, bad anatomy, bad hands, "
    "extra fingers, missing fingers, deformed, "
    "blurry face, flat face, featureless, "
    "text, watermark, signature, "
    "smile, open mouth, "
    "loli, childish, cute, moe, baby face, round face, "
    "oversized clothes, costume, fantasy, "
    "sexy, suggestive, nsfw"
)

print("加载模型...")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL,
    torch_dtype=torch.float16,
    safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

generator = torch.Generator("cuda").manual_seed(42)
print("生成 768x1024...")
result = pipe(
    prompt=POSITIVE,
    negative_prompt=NEGATIVE,
    width=768,
    height=1024,
    num_inference_steps=40,
    guidance_scale=7.5,
    generator=generator,
)

out_path = os.path.join(OUT_DIR, "yuki_hires.png")
result.images[0].save(out_path)
print(f"保存：{out_path}")

del pipe
torch.cuda.empty_cache()
