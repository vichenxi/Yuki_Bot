"""
Gen LoRA v3 — AOM3 base, corrected captions + regularization.
Testing higher scales since training is now correct.
"""
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

MODEL  = r"E:\stable-diffusion-webui\models\Stable-diffusion\AOM3A1B_orangemixs.safetensors"
LORA   = r"F:\bot\data\lora\output\yuki_lora_v3_aom3.safetensors"
OUTDIR = Path(r"F:\bot\data\lora\test_images_v3_aom3")
OUTDIR.mkdir(parents=True, exist_ok=True)

NEG = (
    "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
    "blurry, watermark, text, logo, cropped, 3d, vroid, "
    "white hair, blonde hair, silver hair, purple eyes, brown eyes, "
    "school uniform, sailor uniform, "
    "loli, young, childlike, teen, juvenile, petite, chibi, "
    "smile, smiling, happy, cheerful, open mouth"
)

FULL = (
    "yukixue, 1girl, solo, mature female, adult, "
    "black hair, very long straight black hair, center part, hair past chest, "
    "grey eyes, cold grey eyes, pale skin, "
    "cold expression, expressionless, detached, aloof, "
    "white turtleneck sweater, black skirt, "
    "full body, standing, simple background, white background"
)

BUST = (
    "yukixue, 1girl, solo, mature female, adult, "
    "black hair, very long straight black hair, center part, "
    "grey eyes, cold grey eyes, sharp eyes, pale skin, "
    "cold expression, expressionless, aloof, detached, stoic, "
    "cold gaze, "
    "white turtleneck sweater, "
    "upper body, portrait, looking at viewer"
)

TESTS = [
    # 全身 — scale sweep
    {"name": "01_full_scale08", "prompt": FULL, "lora_scale": 0.8, "w": 512, "h": 768, "seed": 42},
    {"name": "02_full_scale07", "prompt": FULL, "lora_scale": 0.7, "w": 512, "h": 768, "seed": 42},
    {"name": "03_full_scale06", "prompt": FULL, "lora_scale": 0.6, "w": 512, "h": 768, "seed": 42},
    {"name": "04_full_scale05", "prompt": FULL, "lora_scale": 0.5, "w": 512, "h": 768, "seed": 42},
    # 全身 seed 稳定性
    {"name": "05_full_scale07_seed7",   "prompt": FULL, "lora_scale": 0.7, "w": 512, "h": 768, "seed": 7},
    {"name": "06_full_scale07_seed123", "prompt": FULL, "lora_scale": 0.7, "w": 512, "h": 768, "seed": 123},
    # 半身 — scale sweep
    {"name": "07_bust_scale07", "prompt": BUST, "lora_scale": 0.7, "w": 512, "h": 512, "seed": 42, "cfg": 8.5},
    {"name": "08_bust_scale06", "prompt": BUST, "lora_scale": 0.6, "w": 512, "h": 512, "seed": 42, "cfg": 8.5},
    {"name": "09_bust_scale05", "prompt": BUST, "lora_scale": 0.5, "w": 512, "h": 512, "seed": 42, "cfg": 8.5},
    {"name": "10_bust_scale04", "prompt": BUST, "lora_scale": 0.4, "w": 512, "h": 512, "seed": 42, "cfg": 8.5},
    # baseline 对照
    {"name": "11_no_lora_baseline", "prompt": FULL.replace("yukixue, ", ""), "lora_scale": 0.0, "w": 512, "h": 768, "seed": 42},
]

print("Loading AOM3 ...")
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

print("Loading LoRA v3 aom3 ...")
pipe.load_lora_weights(str(Path(LORA).parent), weight_name=Path(LORA).name)

for t in TESTS:
    cfg = t.get("cfg", 7.5)
    print(f"\n[{t['name']}] scale={t['lora_scale']} cfg={cfg} seed={t['seed']}")
    pipe.set_adapters(["default_0"], adapter_weights=[t["lora_scale"]])
    out = pipe(
        prompt=t["prompt"],
        negative_prompt=NEG,
        num_inference_steps=30,
        guidance_scale=cfg,
        clip_skip=1,
        width=t["w"],
        height=t["h"],
        generator=torch.Generator("cuda").manual_seed(t["seed"]),
    )
    p = OUTDIR / f"{t['name']}.png"
    out.images[0].save(p)
    print(f"  saved: {p}")

print(f"\nDone. Output → {OUTDIR}")
