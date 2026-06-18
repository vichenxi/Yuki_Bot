"""Generate LoRA test images using diffusers directly (no WebUI needed)."""
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

MODEL  = r"E:\stable-diffusion-webui\models\Stable-Diffusion\Realistic_Vision_V5.1_fp16.safetensors"
LORA   = r"F:\bot\data\lora\output\yuki_lora_v1.safetensors"
OUTDIR = Path(r"F:\bot\data\lora\test_images")
OUTDIR.mkdir(parents=True, exist_ok=True)

NEG = ("worst quality, low quality, bad anatomy, bad hands, extra fingers, "
       "blurry, watermark, text, logo, cropped")

TESTS = [
    {
        "name": "01_fullbody_front",
        "prompt": "yukixue, 1girl, white hair, long hair, purple eyes, school uniform, "
                  "full body, standing, simple background, white background",
        "lora_scale": 0.8,
        "width": 512, "height": 768,
    },
    {
        "name": "02_portrait_34",
        "prompt": "yukixue, 1girl, white hair, long hair, purple eyes, school uniform, "
                  "upper body, portrait, 3/4 view, looking at viewer, soft light",
        "lora_scale": 0.8,
        "width": 512, "height": 512,
    },
    {
        "name": "03_fullbody_lora06",
        "prompt": "yukixue, 1girl, white hair, long hair, purple eyes, "
                  "full body, standing, white background",
        "lora_scale": 0.6,
        "width": 512, "height": 768,
    },
    {
        "name": "04_no_lora_baseline",
        "prompt": "1girl, white hair, long hair, purple eyes, school uniform, "
                  "full body, standing, white background",
        "lora_scale": 0.0,   # LoRA 不激活，作为对照
        "width": 512, "height": 768,
    },
]

print(f"Loading base model from {MODEL} ...")
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

# Load LoRA weights once
print(f"Loading LoRA from {LORA} ...")
pipe.load_lora_weights(str(Path(LORA).parent), weight_name=Path(LORA).name)

for t in TESTS:
    print(f"\n[{t['name']}] scale={t['lora_scale']} ...")
    pipe.set_adapters(["default_0"], adapter_weights=[t["lora_scale"]])

    out = pipe(
        prompt=t["prompt"],
        negative_prompt=NEG,
        num_inference_steps=30,
        guidance_scale=7,
        clip_skip=2,
        width=t["width"],
        height=t["height"],
        generator=torch.Generator("cuda").manual_seed(42),
    )
    img_path = OUTDIR / f"{t['name']}.png"
    out.images[0].save(img_path)
    print(f"  saved: {img_path}")

print(f"\nDone. All images in {OUTDIR}")
