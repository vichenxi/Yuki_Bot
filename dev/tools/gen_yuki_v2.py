"""
雪立绘 v2 — 成熟日常风，去媚宅
"""
import torch
from diffusers import StableDiffusionPipeline
import os

MODEL = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AnythingV5_v5PrtRE.safetensors"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot"

POSITIVE = (
    "masterpiece, best quality, highres, "
    "(mature:1.3), 1girl, solo, 23 years old, graduate student, "
    "long black hair, straight hair, natural side part, "
    "pale skin, (cold expression:1.2), calm eyes, looking at viewer, "
    "(dark navy blue maxi skirt:1.4), (simple white blouse:1.3), tucked in, "
    "(linen fabric, minimalist fashion:1.2), "
    "full body, standing by window, soft natural light, clean interior, "
    "slim, elegant, understated, quiet atmosphere"
)

NEGATIVE = (
    "(worst quality, low quality:1.4), bad anatomy, bad hands, "
    "extra fingers, missing fingers, deformed, "
    "text, watermark, signature, "
    "smile, open mouth, teeth, "
    "(loli:1.4), (childish face:1.3), (cute:1.2), (moe:1.3), baby face, round face, "
    "(oversized clothes:1.2), robe, yukata, kimono, school uniform, costume, fantasy, "
    "dramatic lighting, dark background, "
    "nsfw"
)

SEEDS = [789, 2024]

print("加载模型...")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL,
    torch_dtype=torch.float16,
    safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

for seed in SEEDS:
    out_path = os.path.join(OUT_DIR, f"yuki_v2_s{seed}.png")
    print(f"生成 seed={seed}...")
    generator = torch.Generator("cuda").manual_seed(seed)
    result = pipe(
        prompt=POSITIVE,
        negative_prompt=NEGATIVE,
        width=512,
        height=768,
        num_inference_steps=35,
        guidance_scale=8.0,
        generator=generator,
    )
    result.images[0].save(out_path)
    print(f"保存：{out_path}")

del pipe
torch.cuda.empty_cache()
print("完成")
