"""
Gen LoRA v1 test — corrected prompts (Realistic_Vision base).
Mirror of gen_lora_test_v2_fixed.py, using V1 LoRA for comparison.
"""
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

MODEL  = r"E:\stable-diffusion-webui\models\Stable-Diffusion\Realistic_Vision_V5.1_fp16.safetensors"
LORA   = r"F:\bot\data\lora\output\yuki_lora_v1.safetensors"
OUTDIR = Path(r"F:\bot\data\lora\test_images_v1_fixed")
OUTDIR.mkdir(parents=True, exist_ok=True)

NEG = (
    "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
    "blurry, watermark, text, logo, cropped, "
    "white hair, blonde hair, silver hair, purple eyes, brown eyes, "
    "school uniform, sailor uniform"
)

CHAR_FULL = (
    "yukixue, 1girl, solo, "
    "black hair, very long straight black hair, center part, hair past chest, "
    "grey eyes, cold grey eyes, pale skin, "
    "cold expression, expressionless, detached, "
    "white turtleneck sweater, black skirt, "
    "full body, standing, simple background, white background"
)

CHAR_BUST = (
    "yukixue, 1girl, solo, "
    "black hair, very long straight black hair, center part, "
    "grey eyes, cold grey eyes, pale skin, "
    "cold expression, expressionless, "
    "white turtleneck sweater, "
    "upper body, portrait, 3/4 view, looking at viewer, soft light"
)

BASELINE = (
    "1girl, solo, "
    "black hair, very long straight black hair, center part, hair past chest, "
    "grey eyes, cold grey eyes, pale skin, "
    "cold expression, expressionless, detached, "
    "white turtleneck sweater, black skirt, "
    "full body, standing, simple background, white background"
)

TESTS = [
    {
        "name": "01_fullbody_scale08",
        "prompt": CHAR_FULL,
        "lora_scale": 0.8,
        "width": 512, "height": 768, "seed": 42,
    },
    {
        "name": "02_fullbody_scale07",
        "prompt": CHAR_FULL,
        "lora_scale": 0.7,
        "width": 512, "height": 768, "seed": 42,
    },
    {
        "name": "03_fullbody_scale05",
        "prompt": CHAR_FULL,
        "lora_scale": 0.5,
        "width": 512, "height": 768, "seed": 42,
    },
    {
        "name": "04_portrait_scale08",
        "prompt": CHAR_BUST,
        "lora_scale": 0.8,
        "width": 512, "height": 512, "seed": 42,
    },
    {
        "name": "05_portrait_scale06",
        "prompt": CHAR_BUST,
        "lora_scale": 0.6,
        "width": 512, "height": 512, "seed": 42,
    },
    {
        "name": "06_no_lora_baseline_corrected",
        "prompt": BASELINE,
        "lora_scale": 0.0,
        "width": 512, "height": 768, "seed": 42,
    },
]

print(f"Loading Realistic_Vision V5.1 ...")
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

print(f"Loading LoRA v1 ...")
pipe.load_lora_weights(str(Path(LORA).parent), weight_name=Path(LORA).name)

for t in TESTS:
    print(f"\n[{t['name']}] lora_scale={t['lora_scale']} seed={t['seed']}")
    pipe.set_adapters(["default_0"], adapter_weights=[t["lora_scale"]])
    out = pipe(
        prompt=t["prompt"],
        negative_prompt=NEG,
        num_inference_steps=30,
        guidance_scale=7.5,
        clip_skip=2,
        width=t["width"],
        height=t["height"],
        generator=torch.Generator("cuda").manual_seed(t["seed"]),
    )
    p = OUTDIR / f"{t['name']}.png"
    out.images[0].save(p)
    print(f"  saved: {p}")

print(f"\nDone. Output → {OUTDIR}")
