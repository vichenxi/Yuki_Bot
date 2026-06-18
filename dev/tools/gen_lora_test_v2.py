"""Generate LoRA v2 test images using AOM3 base model."""
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

MODEL  = r"E:\stable-diffusion-webui\models\Stable-diffusion\AOM3A1B_orangemixs.safetensors"
LORA   = r"F:\bot\data\lora\output\yuki_lora_v2_aom3.safetensors"
OUTDIR = Path(r"F:\bot\data\lora\test_images_v2")
OUTDIR.mkdir(parents=True, exist_ok=True)

NEG = ("worst quality, low quality, bad anatomy, bad hands, extra fingers, "
       "blurry, watermark, text, logo, cropped, 3d, vroid")

TESTS = [
    {
        "name": "01_fullbody_08",
        "prompt": "yukixue, 1girl, white hair, long hair, purple eyes, school uniform, "
                  "full body, standing, simple background",
        "lora_scale": 0.8,
        "width": 512, "height": 768,
    },
    {
        "name": "02_portrait_08",
        "prompt": "yukixue, 1girl, white hair, long hair, purple eyes, "
                  "upper body, portrait, looking at viewer, soft lighting",
        "lora_scale": 0.8,
        "width": 512, "height": 512,
    },
    {
        "name": "03_fullbody_07",
        "prompt": "yukixue, 1girl, white hair, long hair, purple eyes, school uniform, "
                  "full body, standing, simple background",
        "lora_scale": 0.7,
        "width": 512, "height": 768,
    },
    {
        "name": "04_no_lora_baseline",
        "prompt": "1girl, white hair, long hair, purple eyes, school uniform, "
                  "full body, standing, simple background",
        "lora_scale": 0.0,
        "width": 512, "height": 768,
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
    print(f"\n[{t['name']}] lora_scale={t['lora_scale']} ...")
    pipe.set_adapters(["default_0"], adapter_weights=[t["lora_scale"]])
    out = pipe(
        prompt=t["prompt"],
        negative_prompt=NEG,
        num_inference_steps=30,
        guidance_scale=7,
        clip_skip=1,
        width=t["width"],
        height=t["height"],
        generator=torch.Generator("cuda").manual_seed(42),
    )
    p = OUTDIR / f"{t['name']}.png"
    out.images[0].save(p)
    print(f"  saved: {p}")

print(f"\nDone. {OUTDIR}")
