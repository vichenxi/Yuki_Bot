"""
雪 — 不同场景与姿势，让模型自由发挥
strength 提高到 0.70-0.75，给模型更多创作空间
"""
import torch
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import os

MODEL   = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
SRC     = r"C:\Users\Violet\.claude\yukibot\yuki_warm_s789.png"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot\scenes"
os.makedirs(OUT_DIR, exist_ok=True)

BASE_NEG = (
    "worst quality, low quality, bad anatomy, bad hands, "
    "extra fingers, missing fingers, deformed, "
    "text, watermark, nsfw, loli, childish"
)

SCENES = [
    {
        "name": "01_desk_studying",
        "prompt": (
            "masterpiece, best quality, "
            "1girl, long black hair, pale skin, detailed face, "
            "sitting at wooden desk, leaning on hand, looking at papers, "
            "soft lamp light, late afternoon, books and stationery, "
            "quiet focused expression, dark turtleneck sweater, "
            "cozy study room, depth of field"
        ),
        "strength": 0.75, "seed": 42,
    },
    {
        "name": "02_window_gazing",
        "prompt": (
            "masterpiece, best quality, "
            "1girl, long black hair, pale skin, detailed face, "
            "standing by large window, looking outside, side profile, "
            "soft grey winter light, city view, bare trees, "
            "long dark coat, hands wrapped around warm cup, "
            "contemplative, quiet, alone"
        ),
        "strength": 0.75, "seed": 123,
    },
    {
        "name": "03_walking_street",
        "prompt": (
            "masterpiece, best quality, "
            "1girl, long black hair, pale skin, detailed face, "
            "walking on quiet street, looking slightly down, "
            "earphones in, canvas tote bag on shoulder, "
            "navy coat, autumn afternoon, fallen leaves, "
            "natural candid movement, gentle wind in hair"
        ),
        "strength": 0.78, "seed": 789,
    },
    {
        "name": "04_cafe_reading",
        "prompt": (
            "masterpiece, best quality, "
            "1girl, long black hair, pale skin, detailed face, "
            "sitting at cafe window seat, reading book, "
            "one hand holding book, other holding coffee cup, "
            "soft warm cafe light, rainy window behind, "
            "cream knit sweater, completely absorbed, unaware of surroundings"
        ),
        "strength": 0.75, "seed": 2024,
    },
    {
        "name": "05_corridor_glance",
        "prompt": (
            "masterpiece, best quality, "
            "1girl, long black hair, pale skin, detailed face, "
            "walking through corridor, turning to look back over shoulder, "
            "slight pause mid-step, calm but attentive expression, "
            "university hallway, afternoon sunlight through windows, "
            "dark navy blazer, skirt, natural elegant posture"
        ),
        "strength": 0.73, "seed": 512,
    },
    {
        "name": "06_rooftop_evening",
        "prompt": (
            "masterpiece, best quality, "
            "1girl, long black hair, pale skin, detailed face, "
            "sitting on rooftop steps, knees drawn up, "
            "looking at horizon, dusk sky, city lights beginning to glow, "
            "oversized sweater, earphones around neck, "
            "quiet solitude, something on her mind, golden hour light"
        ),
        "strength": 0.78, "seed": 888,
    },
]

print("加载模型...")
pipe = StableDiffusionImg2ImgPipeline.from_single_file(
    MODEL, torch_dtype=torch.float16, safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

src = Image.open(SRC).convert("RGB")

for s in SCENES:
    out_path = os.path.join(OUT_DIR, f"{s['name']}.png")
    print(f"\n生成：{s['name']} (strength={s['strength']}, seed={s['seed']})...")
    generator = torch.Generator("cuda").manual_seed(s["seed"])
    result = pipe(
        prompt=s["prompt"],
        negative_prompt=BASE_NEG,
        image=src,
        strength=s["strength"],
        num_inference_steps=40,
        guidance_scale=7.5,
        generator=generator,
    )
    result.images[0].save(out_path)
    print(f"保存：{out_path}")

del pipe
torch.cuda.empty_cache()
print("\n全部完成")
