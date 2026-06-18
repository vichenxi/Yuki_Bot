"""
Gen LoRA v2 — mature push test.
Same AOM3 + v2_aom3 LoRA, adds mature/adult tags to positive,
adds loli/young/childlike to negative.
"""
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

MODEL  = r"E:\stable-diffusion-webui\models\Stable-diffusion\AOM3A1B_orangemixs.safetensors"
LORA   = r"F:\bot\data\lora\output\yuki_lora_v2_aom3.safetensors"
OUTDIR = Path(r"F:\bot\data\lora\test_images_v2_mature")
OUTDIR.mkdir(parents=True, exist_ok=True)

NEG = (
    "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
    "blurry, watermark, text, logo, cropped, 3d, vroid, "
    "white hair, blonde hair, silver hair, purple eyes, brown eyes, "
    "school uniform, sailor uniform, "
    "loli, young, childlike, teen, juvenile, petite, cute, chibi, small"
)

CHAR_FULL = (
    "yukixue, 1girl, solo, mature female, adult, "
    "black hair, very long straight black hair, center part, hair past chest, "
    "grey eyes, cold grey eyes, pale skin, "
    "cold expression, expressionless, detached, aloof, "
    "white turtleneck sweater, black skirt, "
    "full body, standing, simple background"
)

CHAR_BUST = (
    "yukixue, 1girl, solo, mature female, adult, "
    "black hair, very long straight black hair, center part, "
    "grey eyes, cold grey eyes, pale skin, "
    "cold expression, expressionless, aloof, "
    "white turtleneck sweater, "
    "upper body, portrait, looking at viewer, soft lighting"
)

TESTS = [
    # scale sweep — 先找成熟感和 LoRA 还原度的平衡点
    {
        "name": "01_full_scale07_mature",
        "prompt": CHAR_FULL,
        "lora_scale": 0.7,
        "width": 512, "height": 768, "seed": 42,
    },
    {
        "name": "02_full_scale06_mature",
        "prompt": CHAR_FULL,
        "lora_scale": 0.6,
        "width": 512, "height": 768, "seed": 42,
    },
    {
        "name": "03_full_scale05_mature",
        "prompt": CHAR_FULL,
        "lora_scale": 0.5,
        "width": 512, "height": 768, "seed": 42,
    },
    {
        "name": "04_full_scale04_mature",
        "prompt": CHAR_FULL,
        "lora_scale": 0.4,
        "width": 512, "height": 768, "seed": 42,
    },
    # portrait
    {
        "name": "05_bust_scale06_mature",
        "prompt": CHAR_BUST,
        "lora_scale": 0.6,
        "width": 512, "height": 512, "seed": 42,
    },
    {
        "name": "06_bust_scale05_mature",
        "prompt": CHAR_BUST,
        "lora_scale": 0.5,
        "width": 512, "height": 512, "seed": 42,
    },
    # seed 稳定性（最优 scale 找到后再看）
    {
        "name": "07_full_scale06_seed123",
        "prompt": CHAR_FULL,
        "lora_scale": 0.6,
        "width": 512, "height": 768, "seed": 123,
    },
    {
        "name": "08_full_scale06_seed7",
        "prompt": CHAR_FULL,
        "lora_scale": 0.6,
        "width": 512, "height": 768, "seed": 7,
    },
]

print(f"Loading AOM3 ...")
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

print(f"Loading LoRA v2 ...")
pipe.load_lora_weights(str(Path(LORA).parent), weight_name=Path(LORA).name)

for t in TESTS:
    print(f"\n[{t['name']}] lora_scale={t['lora_scale']} seed={t['seed']}")
    pipe.set_adapters(["default_0"], adapter_weights=[t["lora_scale"]])
    out = pipe(
        prompt=t["prompt"],
        negative_prompt=NEG,
        num_inference_steps=30,
        guidance_scale=7.5,
        clip_skip=1,
        width=t["width"],
        height=t["height"],
        generator=torch.Generator("cuda").manual_seed(t["seed"]),
    )
    p = OUTDIR / f"{t['name']}.png"
    out.images[0].save(p)
    print(f"  saved: {p}")

print(f"\nDone. Output → {OUTDIR}")
