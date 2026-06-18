"""
Gen LoRA v3 AOM3 — bust portrait, revised temperament tags.
Remove aggressive gaze words, lower cfg back to 7.5, let expressionless breathe.
"""
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

MODEL  = r"E:\stable-diffusion-webui\models\Stable-diffusion\AOM3A1B_orangemixs.safetensors"
LORA   = r"F:\bot\data\lora\output\yuki_lora_v3_aom3.safetensors"
OUTDIR = Path(r"F:\bot\data\lora\test_images_v3_aom3_bust2")
OUTDIR.mkdir(parents=True, exist_ok=True)

NEG = (
    "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
    "blurry, watermark, text, logo, cropped, 3d, vroid, "
    "white hair, blonde hair, silver hair, purple eyes, brown eyes, "
    "school uniform, sailor uniform, "
    "loli, young, childlike, teen, juvenile, petite, chibi, "
    "smile, smiling, happy, cheerful, open mouth, angry, glaring"
)

BUST = (
    "yukixue, 1girl, solo, mature female, adult, "
    "black hair, very long straight black hair, center part, "
    "grey eyes, pale skin, "
    "cold expression, expressionless, aloof, detached, "
    "white turtleneck sweater, "
    "upper body, portrait, looking at viewer"
)

SEEDS = [42, 7, 123, 256, 512]

TESTS = []
for scale in [0.7, 0.6, 0.5, 0.4]:
    for seed in SEEDS[:2]:  # 先只跑 seed 42/7
        TESTS.append({
            "name": f"scale{int(scale*10):02d}_seed{seed}",
            "lora_scale": scale,
            "cfg": 7.5,
            "seed": seed,
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

print("Loading LoRA v3 aom3 ...")
pipe.load_lora_weights(str(Path(LORA).parent), weight_name=Path(LORA).name)

for t in TESTS:
    print(f"\n[{t['name']}] scale={t['lora_scale']} cfg={t['cfg']} seed={t['seed']}")
    pipe.set_adapters(["default_0"], adapter_weights=[t["lora_scale"]])
    out = pipe(
        prompt=BUST,
        negative_prompt=NEG,
        num_inference_steps=30,
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
