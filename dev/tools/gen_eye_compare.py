"""
瞳色对比图 — 胸像特写，让眼睛清晰可辨
候选：纯黑 / 深棕近黑 / 冷灰 / 琥珀棕
每种 3 张，seed 各异
"""
import torch, os
from diffusers import StableDiffusionPipeline

MODEL_PATH = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
OUT_DIR    = r"C:\Users\Violet\.claude\yukibot\eye_compare"
os.makedirs(OUT_DIR, exist_ok=True)

CHAR_BASE = (
    "masterpiece, best quality, "
    "1girl, solo, long straight black hair, natural center part, "
    "pale cold white skin, oval face, thin lips, "
    "calm serene expression, looking at viewer, "
    "upper body close-up, detailed face, detailed eyes, "
    "soft neutral light, simple background, "
)

NEGATIVE = (
    "worst quality, low quality, bad anatomy, deformed face, "
    "blurry eyes, unclear eyes, closed eyes, "
    "extra fingers, bad hands, blurry, "
    "nsfw, loli, childish, text, watermark"
)

EYE_COLORS = [
    {
        "name": "pure_black",
        "label": "纯黑",
        "eye": "(pure black eyes:1.4), deep black iris, dark pupils, no highlight color",
    },
    {
        "name": "dark_brown",
        "label": "深棕近黑",
        "eye": "(very dark brown eyes:1.4), deep dark brown iris, warm dark tone",
    },
    {
        "name": "cold_grey",
        "label": "冷灰",
        "eye": "(cold grey eyes:1.4), steel grey iris, cool silver-grey tone, clear",
    },
    {
        "name": "amber_brown",
        "label": "琥珀棕",
        "eye": "(amber brown eyes:1.4), warm golden-brown iris, honey amber tone",
    },
]

SEEDS = [42, 303, 789]

print("加载模型...")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH, torch_dtype=torch.float16, safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

total = len(EYE_COLORS) * len(SEEDS)
count = 0

for ec in EYE_COLORS:
    for seed in SEEDS:
        count += 1
        name = f"{ec['name']}_seed{seed}"
        out_path = os.path.join(OUT_DIR, f"{name}.png")
        prompt = CHAR_BASE + ec["eye"]
        print(f"[{count}/{total}] {ec['label']} seed={seed}...")
        gen = torch.Generator("cuda").manual_seed(seed)
        result = pipe(
            prompt=prompt, negative_prompt=NEGATIVE,
            width=512, height=512,
            num_inference_steps=35, guidance_scale=8.0, generator=gen,
        )
        result.images[0].save(out_path)

del pipe
torch.cuda.empty_cache()
print(f"\n完成，共 {total} 张 → {OUT_DIR}")
