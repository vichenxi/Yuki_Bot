"""
Gen LoRA v3 — scene variety, JK outfit, high saturation.
cf + any, multiple scenes/actions.
"""
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from compel import Compel

BASE_CHAR = (
    "yukixue, 1girl, solo, mature woman, adult, "
    "very long straight hair, center part, "
    "grey eyes, (narrow eyes:1.5), thin eyes, hooded eyes, half-closed eyes, "
    "sharp features, high cheekbones, pale skin, "
    "cold expression, expressionless, aloof, detached, "
    "cool, dignified, "
    "plaid skirt, collared shirt, "
)

NEG = (
    "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
    "blurry, watermark, text, logo, cropped, 3d, vroid, "
    "loli, young, childlike, teen, juvenile, petite, chibi, "
    "smile, smiling, happy, cheerful, open mouth, angry, glaring, "
    "(big eyes:1.5), (large eyes:1.5), wide eyes, doe eyes, round eyes, "
    "dull colors, desaturated, grey background, flat lighting"
)

SCENES = [
    {
        "name": "street_walk",
        "suffix": (
            "walking, full body, "
            "autumn street, fallen leaves, warm sunlight, "
            "vibrant colors, vivid, colorful background, bokeh, "
            "looking ahead"
        ),
        "w": 512, "h": 768,
    },
    {
        "name": "park_stand",
        "suffix": (
            "standing, full body, "
            "park, cherry blossom, pink flowers, vivid colors, "
            "bright saturated background, petals falling, "
            "looking to the side"
        ),
        "w": 512, "h": 768,
    },
    {
        "name": "cafe_sit",
        "suffix": (
            "sitting, upper body, "
            "cafe interior, colorful decor, warm light, "
            "vibrant, saturated warm tones, "
            "holding cup, looking out window"
        ),
        "w": 512, "h": 512,
    },
    {
        "name": "night_street",
        "suffix": (
            "standing, full body, "
            "night city, neon lights, vivid neon colors, "
            "glowing signs, high saturation, colorful reflections, "
            "looking at viewer"
        ),
        "w": 512, "h": 768,
    },
]

SEEDS = [42, 123]

OUTDIR = Path(r"F:\bot\data\lora\test_images_v3_scene")
OUTDIR.mkdir(parents=True, exist_ok=True)

MODELS = [
    {
        "tag":       "cf",
        "model":     r"E:\stable-diffusion-webui\models\Stable-diffusion\Counterfeit-V3.0_fix_fp16.safetensors",
        "lora":      r"F:\bot\data\lora\output\yuki_lora_v3_counterfeit.safetensors",
        "clip_skip": 2,
        "scale":     0.7,
    },
    {
        "tag":       "any",
        "model":     r"E:\stable-diffusion-webui\models\Stable-diffusion\AnythingV5_v5PrtRE.safetensors",
        "lora":      r"F:\bot\data\lora\output\yuki_lora_v3_anything.safetensors",
        "clip_skip": 1,
        "scale":     0.7,
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
    pipe.set_adapters(["default_0"], adapter_weights=[m["scale"]])

    compel = Compel(tokenizer=pipe.tokenizer, text_encoder=pipe.text_encoder)

    for scene in SCENES:
        prompt = BASE_CHAR + scene["suffix"]
        for seed in SEEDS:
            name = f"{m['tag']}_{scene['name']}_seed{seed}"
            print(f"  [{name}]")

            pos_embeds = compel(prompt)
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
                width=scene["w"],
                height=scene["h"],
                generator=torch.Generator("cuda").manual_seed(seed),
            )
            p = OUTDIR / f"{name}.png"
            out.images[0].save(p)
            print(f"    saved: {p}")

    del pipe
    torch.cuda.empty_cache()

print(f"\nDone. Output → {OUTDIR}")
