"""
Gen LoRA v2 — bust scale 0.3 seed stability.
03 (cfg7.5) and 08 (cfg8.5) both OK. Find which cfg is more consistent.
"""
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

MODEL  = r"E:\stable-diffusion-webui\models\Stable-diffusion\AOM3A1B_orangemixs.safetensors"
LORA   = r"F:\bot\data\lora\output\yuki_lora_v2_aom3.safetensors"
OUTDIR = Path(r"F:\bot\data\lora\test_images_v2_bust_stable")
OUTDIR.mkdir(parents=True, exist_ok=True)

NEG = (
    "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
    "blurry, watermark, text, logo, cropped, 3d, vroid, "
    "white hair, blonde hair, silver hair, purple eyes, brown eyes, "
    "school uniform, sailor uniform, "
    "loli, young, childlike, teen, juvenile, petite, chibi, "
    "smile, smiling, happy, cheerful, warm, friendly, open mouth"
)

BUST = (
    "yukixue, 1girl, solo, mature female, adult, "
    "black hair, very long straight black hair, center part, "
    "grey eyes, cold grey eyes, sharp eyes, pale skin, "
    "cold expression, expressionless, aloof, detached, stoic, reserved, "
    "cold gaze, piercing gaze, "
    "white turtleneck sweater, "
    "upper body, portrait, looking at viewer"
)

SEEDS = [42, 7, 123, 256, 512, 1024, 2025, 99]

TESTS = []
for s in SEEDS:
    TESTS.append({
        "name": f"cfg75_seed{s}",
        "cfg": 7.5,
        "seed": s,
    })
for s in SEEDS:
    TESTS.append({
        "name": f"cfg85_seed{s}",
        "cfg": 8.5,
        "seed": s,
    })

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
pipe.set_adapters(["default_0"], adapter_weights=[0.3])

for t in TESTS:
    print(f"\n[{t['name']}] cfg={t['cfg']} seed={t['seed']}")
    out = pipe(
        prompt=BUST,
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
