"""
Gen LoRA v2 — bust portrait temperament push.
Based on v2_mature result: scale 0.5 best direction, need more 气质.
Try lower scale (0.4/0.3) + stronger temperament tags + higher cfg.
"""
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

MODEL  = r"E:\stable-diffusion-webui\models\Stable-diffusion\AOM3A1B_orangemixs.safetensors"
LORA   = r"F:\bot\data\lora\output\yuki_lora_v2_aom3.safetensors"
OUTDIR = Path(r"F:\bot\data\lora\test_images_v2_bust")
OUTDIR.mkdir(parents=True, exist_ok=True)

NEG = (
    "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
    "blurry, watermark, text, logo, cropped, 3d, vroid, "
    "white hair, blonde hair, silver hair, purple eyes, brown eyes, "
    "school uniform, sailor uniform, "
    "loli, young, childlike, teen, juvenile, petite, chibi, "
    "smile, smiling, happy, cheerful, warm, friendly, open mouth"
)

BUST_BASE = (
    "yukixue, 1girl, solo, mature female, adult, "
    "black hair, very long straight black hair, center part, "
    "grey eyes, cold grey eyes, sharp eyes, pale skin, "
    "cold expression, expressionless, aloof, detached, stoic, reserved, "
    "cold gaze, piercing gaze, "
    "white turtleneck sweater, "
    "upper body, portrait, looking at viewer, soft lighting"
)

TESTS = [
    # scale sweep — 找气质甜点
    {
        "name": "01_bust_scale05_cfg75",
        "prompt": BUST_BASE,
        "lora_scale": 0.5,
        "cfg": 7.5,
        "seed": 42,
    },
    {
        "name": "02_bust_scale04_cfg75",
        "prompt": BUST_BASE,
        "lora_scale": 0.4,
        "cfg": 7.5,
        "seed": 42,
    },
    {
        "name": "03_bust_scale03_cfg75",
        "prompt": BUST_BASE,
        "lora_scale": 0.3,
        "cfg": 7.5,
        "seed": 42,
    },
    # 同 scale 0.4 提高 cfg
    {
        "name": "04_bust_scale04_cfg85",
        "prompt": BUST_BASE,
        "lora_scale": 0.4,
        "cfg": 8.5,
        "seed": 42,
    },
    {
        "name": "05_bust_scale04_cfg95",
        "prompt": BUST_BASE,
        "lora_scale": 0.4,
        "cfg": 9.5,
        "seed": 42,
    },
    # 不同 seed 看稳定性（scale 0.4 cfg 8.5）
    {
        "name": "06_bust_scale04_cfg85_seed7",
        "prompt": BUST_BASE,
        "lora_scale": 0.4,
        "cfg": 8.5,
        "seed": 7,
    },
    {
        "name": "07_bust_scale04_cfg85_seed123",
        "prompt": BUST_BASE,
        "lora_scale": 0.4,
        "cfg": 8.5,
        "seed": 123,
    },
    # scale 0.3 cfg 8.5
    {
        "name": "08_bust_scale03_cfg85",
        "prompt": BUST_BASE,
        "lora_scale": 0.3,
        "cfg": 8.5,
        "seed": 42,
    },
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

print("Loading LoRA v2 ...")
pipe.load_lora_weights(str(Path(LORA).parent), weight_name=Path(LORA).name)

for t in TESTS:
    print(f"\n[{t['name']}] scale={t['lora_scale']} cfg={t['cfg']} seed={t['seed']}")
    pipe.set_adapters(["default_0"], adapter_weights=[t["lora_scale"]])
    out = pipe(
        prompt=t["prompt"],
        negative_prompt=NEG,
        num_inference_steps=35,
        guidance_scale=t["cfg"],
        clip_skip=1,
        width=512,
        height=512,
        generator=torch.Generator("cuda").manual_seed(t["seed"]),
    )
    p = OUTDIR / f"{t['name']}.png"
    out.images[0].save(p)
    print(f"  saved: {p}")

print(f"\nDone. Output → {OUTDIR}")
