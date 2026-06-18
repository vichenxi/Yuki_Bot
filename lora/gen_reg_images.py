"""
Generate 150 regularization images for LoRA training.
Generic 1girl, diverse hair/outfit/pose — no yukixue trigger word.
Output: F:/bot/data/yuki_lora/reg/1_1girl/
"""
import torch
import random
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

MODEL  = r"E:\stable-diffusion-webui\models\Stable-diffusion\AOM3A1B_orangemixs.safetensors"
OUTDIR = Path(r"F:\bot\data\yuki_lora\reg\1_1girl")
OUTDIR.mkdir(parents=True, exist_ok=True)

NEG = (
    "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
    "blurry, watermark, text, logo, cropped, 3d, vroid"
)

HAIR_COLORS = [
    "blonde hair", "brown hair", "red hair", "pink hair",
    "blue hair", "green hair", "orange hair", "silver hair",
    "dark brown hair", "light brown hair", "purple hair", "white hair",
]
HAIR_STYLES = [
    "long hair", "short hair", "medium hair", "twin tails",
    "ponytail", "braid", "bob cut", "wavy hair",
]
OUTFITS = [
    "school uniform", "casual clothes", "sweater", "jacket",
    "dress", "hoodie", "blouse", "coat",
]
POSES = [
    "full body, standing",
    "upper body, portrait",
    "full body, sitting",
    "upper body, 3/4 view",
    "full body, 3/4 view",
]
EXPRESSIONS = [
    "smile", "neutral expression", "serious", "happy",
    "surprised", "calm", "looking at viewer",
]
SIZES = [
    (512, 768),
    (512, 512),
    (512, 768),
]

random.seed(0)
prompts = []
for i in range(150):
    hair  = random.choice(HAIR_COLORS)
    style = random.choice(HAIR_STYLES)
    outfit= random.choice(OUTFITS)
    pose  = random.choice(POSES)
    expr  = random.choice(EXPRESSIONS)
    w, h  = random.choice(SIZES)
    p = f"1girl, solo, {hair}, {style}, {outfit}, {pose}, {expr}, simple background"
    prompts.append((p, w, h, i))

print("Loading AOM3 (no LoRA) ...")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL,
    torch_dtype=torch.float16,
    use_safetensors=True,
)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(
    pipe.scheduler.config,
    use_karras_sigmas=True,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

for prompt, w, h, idx in prompts:
    seed = 1000 + idx
    print(f"[{idx+1:03d}/150] seed={seed} {w}x{h}")
    out = pipe(
        prompt=prompt,
        negative_prompt=NEG,
        num_inference_steps=25,
        guidance_scale=7.0,
        width=w,
        height=h,
        generator=torch.Generator("cuda").manual_seed(seed),
    )
    img_path = OUTDIR / f"reg_{idx:03d}.png"
    txt_path = OUTDIR / f"reg_{idx:03d}.txt"
    out.images[0].save(img_path)
    txt_path.write_text("1girl")

print(f"\nDone. {len(prompts)} reg images → {OUTDIR}")
