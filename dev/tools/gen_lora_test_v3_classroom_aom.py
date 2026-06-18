"""
Gen LoRA v3 — AOM3, classroom scene, append to existing compare folder.
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
    "standing, full body, "
    "classroom, blackboard background, desks, indoor, "
    "looking at viewer"
)

NEG = (
    "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
    "missing feet, cropped legs, "
    "blurry, watermark, text, logo, 3d, vroid"
)

OUTDIR = Path(r"F:\bot\data\lora\test_images_v3_classroom")
OUTDIR.mkdir(parents=True, exist_ok=True)

SEEDS = [42, 123]

print("Loading AOM3 ...")
pipe = StableDiffusionPipeline.from_single_file(
    r"E:\stable-diffusion-webui\models\Stable-diffusion\AOM3A1B_orangemixs.safetensors",
    torch_dtype=torch.float16,
    use_safetensors=True,
)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(
    pipe.scheduler.config,
    use_karras_sigmas=True,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

lora_path = Path(r"F:\bot\data\lora\output\yuki_lora_v3_aom3.safetensors")
pipe.load_lora_weights(str(lora_path.parent), weight_name=lora_path.name)
pipe.set_adapters(["default_0"], adapter_weights=[0.7])

compel = Compel(tokenizer=pipe.tokenizer, text_encoder=pipe.text_encoder)
pos_embeds = compel(PROMPT)
neg_embeds = compel(NEG)
pos_embeds, neg_embeds = compel.pad_conditioning_tensors_to_same_length(
    [pos_embeds, neg_embeds]
)

for seed in SEEDS:
    name = f"aom_seed{seed}"
    print(f"  [{name}]")
    out = pipe(
        prompt_embeds=pos_embeds,
        negative_prompt_embeds=neg_embeds,
        num_inference_steps=30,
        guidance_scale=7.5,
        clip_skip=1,
        width=512,
        height=768,
        generator=torch.Generator("cuda").manual_seed(seed),
    )
    p = OUTDIR / f"{name}.png"
    out.images[0].save(p)
    print(f"    saved: {p}")

print(f"\nDone. Output → {OUTDIR}")
