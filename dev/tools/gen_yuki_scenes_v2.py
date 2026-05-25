"""
雪 — 场景泛化 v2
基于视觉特征基准 v1.0，沿用 rooftop 验证过的生图结构
每个场景跑 seed 202 + 303，strength 固定 0.65
"""
import torch
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import os

MODEL   = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
SRC     = r"C:\Users\Violet\.claude\yukibot\yuki_warm_s789.png"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot\scenes_v2"
os.makedirs(OUT_DIR, exist_ok=True)

BASE_POS = (
    "masterpiece, best quality, "
    "1girl, solo, "
    "long straight black hair, natural center part, "
    "pale cold white skin, oval face, thin lips, "
    "calm serene expression, "
    "slim body, correct proportions, natural anatomy, "
    "elegant posture, "
)

BASE_NEG = (
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

SCENES = [
    {
        "name": "01_library",
        "scene": (
            "standing in library aisle, "
            "one hand trailing along book spines, "
            "slight downward gaze, absorbed, "
            "warm reading lamp light, tall bookshelves, "
            "dark turtleneck, dark midi skirt"
        ),
    },
    {
        "name": "02_convenience_store_night",
        "scene": (
            "inside convenience store late at night, "
            "looking at shelf, soft fluorescent light, "
            "holding a small item, alone, "
            "oversized coat, dark inner wear, "
            "quiet empty store, city night through glass door"
        ),
    },
    {
        "name": "03_subway",
        "scene": (
            "sitting in subway car, "
            "looking out window at passing darkness, "
            "hands in lap, earphones in, "
            "navy coat, dark skirt, "
            "soft interior light, blurred lights outside, "
            "alone in frame, contemplative"
        ),
    },
    {
        "name": "04_rainy_corridor",
        "scene": (
            "standing in covered outdoor corridor, "
            "watching rain fall outside, "
            "arms loosely crossed, "
            "grey knit sweater, dark skirt, "
            "diffuse grey rainy light, wet ground reflection, "
            "quiet, unhurried"
        ),
    },
    {
        "name": "05_dorm_morning",
        "scene": (
            "sitting on bed edge by window, "
            "morning light through curtain gap, "
            "holding phone loosely, not quite looking at it, "
            "oversized white shirt, "
            "soft warm morning light, unmade bed slightly visible, "
            "slow quiet morning"
        ),
    },
    {
        "name": "06_gallery",
        "scene": (
            "standing in art gallery, "
            "looking at large artwork on white wall, "
            "slight tilt of head, focused, "
            "dark blazer, dark midi skirt, simple inner, "
            "clean white gallery light, "
            "alone in room, contemplative"
        ),
    },
    {
        "name": "07_bus_stop_evening",
        "scene": (
            "standing at bus stop, dusk, "
            "looking down the empty road, "
            "canvas tote bag on shoulder, "
            "long dark wool coat, "
            "golden hour fading to blue, streetlamp beginning to glow, "
            "quiet street, a few fallen leaves"
        ),
    },
    {
        "name": "08_studio_working",
        "scene": (
            "sitting at design studio desk, "
            "leaning on one arm, staring at monitor, "
            "late afternoon sun from side window, "
            "dark mock-neck sweater, "
            "papers and drawing tablet on desk, "
            "focused, slight fatigue, not unhappy"
        ),
    },
]

SEEDS = [202, 303]
STRENGTH = 0.65

print("加载模型...")
pipe = StableDiffusionImg2ImgPipeline.from_single_file(
    MODEL, torch_dtype=torch.float16, safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

src = Image.open(SRC).convert("RGB")
total = len(SCENES) * len(SEEDS)
count = 0

for s in SCENES:
    for seed in SEEDS:
        count += 1
        name = f"{s['name']}_seed{seed}"
        out_path = os.path.join(OUT_DIR, f"{name}.png")
        prompt = BASE_POS + s["scene"]
        print(f"\n[{count}/{total}] 生成：{name}...")
        generator = torch.Generator("cuda").manual_seed(seed)
        result = pipe(
            prompt=prompt,
            negative_prompt=BASE_NEG,
            image=src,
            strength=STRENGTH,
            num_inference_steps=40,
            guidance_scale=7.5,
            generator=generator,
        )
        result.images[0].save(out_path)
        print(f"保存：{out_path}")

del pipe
torch.cuda.empty_cache()
print(f"\n全部完成，共 {total} 张，保存至 {OUT_DIR}")
