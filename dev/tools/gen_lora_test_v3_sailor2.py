"""
Gen LoRA v3 — sailor uniform v2, minimal negative prompt.
"""
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from compel import Compel

PROMPT = (
    "yukixue, 1girl, solo, mature woman, adult, "
    "very long straight hair, center part, "
    "grey eyes, (narrow eyes:1.5), thin eyes, hooded eyes, half-closed eyes, "
    "sharp features, high cheekbones, pale skin, "
    "cold expression, expressionless, aloof, detached, cool, dignified, "
    "white sailor uniform, navy blue sailor collar, navy blue double stripe trim, "
    "navy blue pleated skirt, mid-thigh length, "
    "navy blue calf socks, brown loafers, "
    "standing, full body, "
    "classroom, blackboard background, "
    "looking at viewer"
)

NEG = (
    "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
    "missing feet, missing shoes, cropped legs, "
    "blurry, watermark, text, logo, 3d, vroid"
)

OUTDIR = Path(r"F:\bot\data\lora\test_images_v3_sailor2")
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

SEEDS = [42, 123]

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
    pos_embeds = compel(PROMPT)
    neg_embeds = compel(NEG)
    pos_embeds, neg_embeds = compel.pad_conditioning_tensors_to_same_length(
        [pos_embeds, neg_embeds]
    )

    for seed in SEEDS:
        name = f"{m['tag']}_seed{seed}"
        print(f"  [{name}]")
        out = pipe(
            prompt_embeds=pos_embeds,
            negative_prompt_embeds=neg_embeds,
            num_inference_steps=30,
            guidance_scale=7.5,
            clip_skip=m["clip_skip"],
            width=512,
            height=768,
            generator=torch.Generator("cuda").manual_seed(seed),
        )
        p = OUTDIR / f"{name}.png"
        out.images[0].save(p)
        print(f"    saved: {p}")

    del pipe
    torch.cuda.empty_cache()

print(f"\nDone. Output → {OUTDIR}")
