"""
天台夜景 — 基于视觉特征基准 v1.0
strength 降至 0.62-0.68，优先保留源图身型结构
多 seed 对比，取身材比例最稳的
"""
import torch
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import os

MODEL   = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
SRC     = r"C:\Users\Violet\.claude\yukibot\yuki_warm_s789.png"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot\rooftop"
os.makedirs(OUT_DIR, exist_ok=True)

POSITIVE = (
    "masterpiece, best quality, "
    "1girl, solo, "
    "long straight black hair, natural center part, "
    "pale cold white skin, oval face, thin lips, "
    "calm serene expression, looking at city, "
    "slim body, correct proportions, natural anatomy, "
    "elegant posture, "
    "standing on rooftop, leaning slightly on railing, "
    "city lights below, night sky, dusk to night, "
    "oversized dark knit sweater, dark midi skirt, "
    "quiet solitude, gentle wind in hair, "
    "soft city glow on face, moody lighting"
)

NEGATIVE = (
    "worst quality, low quality, "
    "bad anatomy, bad proportions, deformed body, "
    "extra limbs, missing limbs, fused fingers, extra fingers, "
    "bad hands, wrong hands, floating limbs, "
    "distorted torso, long neck, short legs, "
    "blurry, jpeg artifacts, "
    "nsfw, loli, childish, moe, "
    "smile, open mouth, laughing, "
    "text, watermark, signature"
)

SEEDS = [101, 202, 303, 404, 505]
STRENGTHS = [0.62, 0.65, 0.68]

print("加载模型...")
pipe = StableDiffusionImg2ImgPipeline.from_single_file(
    MODEL, torch_dtype=torch.float16, safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

src = Image.open(SRC).convert("RGB")

for strength in STRENGTHS:
    for seed in SEEDS:
        name = f"rooftop_s{strength}_seed{seed}"
        out_path = os.path.join(OUT_DIR, f"{name}.png")
        print(f"\n生成：{name}...")
        generator = torch.Generator("cuda").manual_seed(seed)
        result = pipe(
            prompt=POSITIVE,
            negative_prompt=NEGATIVE,
            image=src,
            strength=strength,
            num_inference_steps=40,
            guidance_scale=7.5,
            generator=generator,
        )
        result.images[0].save(out_path)
        print(f"保存：{out_path}")

del pipe
torch.cuda.empty_cache()
print("\n全部完成，共生成", len(SEEDS) * len(STRENGTHS), "张")
