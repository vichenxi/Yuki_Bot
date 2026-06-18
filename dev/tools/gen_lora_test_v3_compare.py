"""
Gen LoRA v3 — CounterfeitV3 vs AnythingV5, same folder for side-by-side compare.
Filenames prefixed with model tag.
"""
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from compel import Compel

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

OUTDIR = Path(r"F:\bot\data\lora\test_images_v3_compare")
OUTDIR.mkdir(parents=True, exist_ok=True)

MODELS = [
    {
        "tag":       "cf",
        "model":     r"E:\stable-diffusion-webui\models\Stable-diffusion\Counterfeit-V3.0_fix_fp16.safetensors",
        "lora":      r"F:\bot\data\lora\output\yuki_lora_v3_counterfeit.safetensors",
        "clip_skip": 2,
    },
    {
        "tag":       "any",
        "model":     r"E:\stable-diffusion-webui\models\Stable-diffusion\AnythingV5_v5PrtRE.safetensors",
        "lora":      r"F:\bot\data\lora\output\yuki_lora_v3_anything.safetensors",
        "clip_skip": 1,
    },
]

for m in MODELS:
    print(f"\n{'='*50}")
    print(f"Loading {m['tag']} ...")
    pipe = StableDiffusionPipeline.from_single_file(
        m["model"],
        torch_dtype=torch.float16,
        use_safetensors=True,
    )
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(
        pipe.scheduler.config,
        use_karras_sigmas=True,
    )
    pipe = pipe.to("cuda")
    pipe.enable_attention_slicing()

    lora_path = Path(m["lora"])
    pipe.load_lora_weights(str(lora_path.parent), weight_name=lora_path.name)

    compel = Compel(tokenizer=pipe.tokenizer, text_encoder=pipe.text_encoder)

    for t in TESTS:
        print(f"  [{m['tag']}_{t['name']}] scale={t['lora_scale']} seed={t['seed']}")
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
            clip_skip=m["clip_skip"],
            width=512,
            height=512,
            generator=torch.Generator("cuda").manual_seed(t["seed"]),
        )
        p = OUTDIR / f"{m['tag']}_{t['name']}.png"
        out.images[0].save(p)
        print(f"    saved: {p}")

    del pipe
    torch.cuda.empty_cache()

print(f"\nDone. Output → {OUTDIR}")
