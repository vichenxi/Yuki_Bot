"""
用 MeinaMix V11 生成雪，多 seed 对比
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
    "pale skin, cold expression, calm eyes, looking at viewer, "
    "dark navy long skirt, white button-up blouse, tucked in, "
    "simple minimalist outfit, everyday clothing, "
    "full body, standing by window, soft natural daylight, clean room, "
    "slim, quiet, elegant, art student"
)

NEGATIVE = (
    "worst quality, low quality, bad anatomy, bad hands, "
    "extra fingers, missing fingers, deformed, "
    "text, watermark, signature, "
    "smile, open mouth, "
    "loli, childish, cute, moe, baby face, "
    "oversized clothes, costume, fantasy, "
    "sexy, suggestive, nsfw"
)

SEEDS = [42, 789, 2024, 512]

print("加载模型...")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL,
    torch_dtype=torch.float16,
    safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

for seed in SEEDS:
    out_path = os.path.join(OUT_DIR, f"yuki_meina_s{seed}.png")
    print(f"生成 seed={seed}...")
    generator = torch.Generator("cuda").manual_seed(seed)
    result = pipe(
        prompt=POSITIVE,
        negative_prompt=NEGATIVE,
        width=512,
        height=768,
        num_inference_steps=30,
        guidance_scale=7.0,
        generator=generator,
    )
    result.images[0].save(out_path)
    print(f"保存：{out_path}")

del pipe
torch.cuda.empty_cache()
print("完成")
