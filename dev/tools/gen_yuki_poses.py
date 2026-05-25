"""
雪 — 姿势泛化
中性背景，姿势为主体，基准锚点不变
strength 0.65，seed 202 + 303
"""
import torch
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import os

MODEL   = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
SRC     = r"C:\Users\Violet\.claude\yukibot\yuki_warm_s789.png"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot\poses"
os.makedirs(OUT_DIR, exist_ok=True)

BASE_POS = (
    "masterpiece, best quality, "
    "1girl, solo, "
    "long straight black hair, natural center part, "
    "pale cold white skin, oval face, thin lips, "
    "calm serene expression, "
    "slim body, correct proportions, natural anatomy, "
    "elegant posture, "
    "dark midi skirt, simple top, "
    "clean neutral background, soft ambient light, "
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

POSES = [
    {
        "name": "01_arms_crossed",
        "pose": (
            "arms loosely crossed at chest, "
            "weight on one leg, slight hip shift, "
            "looking slightly to the side, "
            "full body, standing"
        ),
    },
    {
        "name": "02_hands_in_pockets",
        "pose": (
            "both hands in coat pockets, "
            "standing straight, looking at viewer, "
            "relaxed shoulders, "
            "full body, standing"
        ),
    },
    {
        "name": "03_hair_touch",
        "pose": (
            "one hand lightly touching hair near ear, "
            "slight downward gaze, "
            "other arm at side, "
            "full body, standing"
        ),
    },
    {
        "name": "04_sitting_chair",
        "pose": (
            "sitting on chair, "
            "legs together, ankles slightly crossed, "
            "hands resting on lap, "
            "upright posture, looking at viewer, "
            "upper body to full body"
        ),
    },
    {
        "name": "05_sitting_steps",
        "pose": (
            "sitting on stone steps, "
            "knees slightly raised, "
            "arms resting on knees, "
            "looking down or to the side, "
            "relaxed, unhurried"
        ),
    },
    {
        "name": "06_leaning_wall",
        "pose": (
            "leaning back against wall, "
            "arms loosely at sides, "
            "one knee slightly bent, "
            "looking forward, calm, "
            "full body"
        ),
    },
    {
        "name": "07_back_glance",
        "pose": (
            "back facing viewer, "
            "turning head to look over shoulder, "
            "slight pause in step, "
            "three-quarter back view, "
            "hair falling over shoulder"
        ),
    },
    {
        "name": "08_side_profile",
        "pose": (
            "strict side profile, "
            "standing, arms at sides, "
            "looking straight ahead, "
            "clean silhouette, "
            "full body"
        ),
    },
    {
        "name": "09_looking_up",
        "pose": (
            "head tilted slightly upward, "
            "as if noticing something above, "
            "eyes looking up, "
            "arms at sides, standing, "
            "soft expression, curious"
        ),
    },
    {
        "name": "10_crouching",
        "pose": (
            "crouching down low, "
            "knees bent, skirt draped naturally, "
            "looking at something on ground level, "
            "one hand near ground, "
            "focused, gentle"
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
total = len(POSES) * len(SEEDS)
count = 0

for p in POSES:
    for seed in SEEDS:
        count += 1
        name = f"{p['name']}_seed{seed}"
        out_path = os.path.join(OUT_DIR, f"{name}.png")
        prompt = BASE_POS + p["pose"]
        print(f"\n[{count}/{total}] {name}...")
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
print(f"\n完成，共 {total} 张，保存至 {OUT_DIR}")
