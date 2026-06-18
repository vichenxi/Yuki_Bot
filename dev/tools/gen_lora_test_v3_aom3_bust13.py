"""
Gen LoRA v3 AOM3 — bust13. Remove elegant + graceful.
"""
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from compel import Compel

MODEL  = r"E:\stable-diffusion-webui\models\Stable-diffusion\AOM3A1B_orangemixs.safetensors"
LORA   = r"F:\bot\data\lora\output\yuki_lora_v3_aom3.safetensors"
OUTDIR = Path(r"F:\bot\data\lora\test_images_v3_aom3_bust13")
OUTDIR.mkdir(parents=True, exist_ok=True)

NEG = (
    "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
    "blurry, watermark, text, logo, cropped, 3d, vroid, "
    "school uniform, sailor uniform, "
    "loli, young, childlike, teen, juvenile, petite, chibi, "
    "smile, smiling, happy, cheerful, open mouth, angry, glaring, "
    "(big eyes:1.5), (large eyes:1.5), wide eyes, doe eyes, round eyes"
)

BUST = (
    "yukixue, 1girl, solo, mature woman, adult, "
    "very long straight hair, center part, "
    "grey eyes, (narrow eyes:1.5), thin eyes, hooded eyes, half-closed eyes, "
    "sharp features, high cheekbones, pale skin, "
    "cold expression, expressionless, aloof, detached, indifferent, "
    "cool, dignified, composed, "
    "upper body, portrait, looking at viewer"
)

TESTS = [
    {"name": "01_scale07_seed42",  "lora_scale": 0.7, "seed": 42},
    {"name": "06_scale05_seed7",   "lora_scale": 0.5, "seed": 7},
    {"name": "07_scale07_seed123", "lora_scale": 0.7, "seed": 123},
    {"name": "08_scale06_seed123", "lora_scale": 0.6, "seed": 123},
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

compel = Compel(tokenizer=pipe.tokenizer, text_encoder=pipe.text_encoder)

for t in TESTS:
    print(f"\n[{t['name']}] scale={t['lora_scale']} seed={t['seed']}")
    pipe.set_adapters(["default_0"], adapter_weights=[t["lora_scale"]])

    pos_embeds = compel(BUST)
    neg_embeds = compel(NEG)
    pos_embeds, neg_embeds = compel.pad_conditioning_tensors_to_same_length(
        [pos_embeds, neg_embeds]
    )

    out = pipe(
        prompt_embeds=pos_embeds,
        negative_prompt_embeds=neg_embeds,
        num_inference_steps=30,
        guidance_scale=7.5,
        clip_skip=1,
        width=512,
        height=512,
        generator=torch.Generator("cuda").manual_seed(t["seed"]),
    )
    p = OUTDIR / f"{t['name']}.png"
    out.images[0].save(p)
    print(f"  saved: {p}")

print(f"\nDone. Output → {OUTDIR}")
