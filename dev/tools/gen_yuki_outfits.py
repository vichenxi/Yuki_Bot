"""
雪的四套服饰变体，以 yuki_warm_s789.png 为底
"""
import torch
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import os

MODEL   = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
SRC     = r"C:\Users\Violet\.claude\yukibot\yuki_warm_s789.png"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot\outfits"
os.makedirs(OUT_DIR, exist_ok=True)

BASE_NEG = (
    "worst quality, low quality, bad anatomy, bad hands, "
    "extra fingers, missing fingers, deformed, "
    "blurry face, featureless, text, watermark, "
    "smile, open mouth, loli, childish, moe, nsfw"
)

OUTFITS = [
    {
        "name": "02_winter_coat",
        "positive": (
            "masterpiece, best quality, "
            "1girl, solo, full body, "
            "long black hair, straight hair, natural bangs, "
            "pale skin, detailed face, serene expression, looking at viewer, "
            "(long dark charcoal wool coat:1.5), (off-white knit scarf:1.3), "
            "coat buttoned, hands in pockets, "
            "standing outdoors, winter light, cold air, clean street background, "
            "slim, quiet, elegant"
        ),
        "strength": 0.62,
        "seed": 789,
    },
    {
        "name": "03_secret_dress",
        "positive": (
            "masterpiece, best quality, "
            "1girl, solo, full body, "
            "long black hair, straight hair, natural bangs, "
            "pale skin, detailed face, soft serene expression, looking at viewer, "
            "(light dusty rose midi dress:1.5), (soft flowing fabric:1.3), "
            "simple cut, minimal detail, feminine but understated, "
            "standing by window, soft afternoon light, clean room, "
            "slim, quiet, elegant, slightly surprised at herself"
        ),
        "strength": 0.65,
        "seed": 789,
    },
    {
        "name": "04_home_casual",
        "positive": (
            "masterpiece, best quality, "
            "1girl, solo, full body, "
            "long black hair, straight hair, natural bangs, "
            "pale skin, detailed face, relaxed expression, looking at viewer, "
            "(oversized grey hoodie:1.5), (black casual shorts:1.3), "
            "sleeves slightly past hands, comfortable, "
            "indoors, warm room light, cozy background, "
            "slim, quiet, at home, relaxed"
        ),
        "strength": 0.62,
        "seed": 789,
    },
    {
        "name": "05_semi_formal",
        "positive": (
            "masterpiece, best quality, "
            "1girl, solo, full body, "
            "long black hair, straight hair, natural bangs, "
            "pale skin, detailed face, composed expression, looking at viewer, "
            "(dark navy blazer:1.5), (white simple inner shirt:1.3), "
            "(straight trousers:1.3), clean cut, minimalist, "
            "standing in corridor, neutral light, clean background, "
            "slim, professional, composed, art student"
        ),
        "strength": 0.60,
        "seed": 789,
    },
]

print("加载模型...")
pipe = StableDiffusionImg2ImgPipeline.from_single_file(
    MODEL, torch_dtype=torch.float16, safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

src = Image.open(SRC).convert("RGB")

for outfit in OUTFITS:
    out_path = os.path.join(OUT_DIR, f"{outfit['name']}.png")
    print(f"\n生成：{outfit['name']}...")
    generator = torch.Generator("cuda").manual_seed(outfit["seed"])
    result = pipe(
        prompt=outfit["positive"],
        negative_prompt=BASE_NEG,
        image=src,
        strength=outfit["strength"],
        num_inference_steps=40,
        guidance_scale=8.0,
        generator=generator,
    )
    result.images[0].save(out_path)
    print(f"保存：{out_path}")

del pipe
torch.cuda.empty_cache()
print("\n全部完成")
