"""
Gen LoRA v2 test — corrected prompts.

Changes from gen_lora_test_v2.py:
  - white hair  → black hair, very long straight black hair, center part
  - purple eyes → grey eyes, cold grey eyes
  - school uniform → white turtleneck sweater, black skirt
  - Negative prompt now explicitly rejects wrong colors
  - Tests multiple lora_scale values to find sweet spot
"""
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

MODEL  = r"E:\stable-diffusion-webui\models\Stable-diffusion\AOM3A1B_orangemixs.safetensors"
LORA   = r"F:\bot\data\lora\output\yuki_lora_v2_aom3.safetensors"
OUTDIR = Path(r"F:\bot\data\lora\test_images_v2_fixed")
OUTDIR.mkdir(parents=True, exist_ok=True)

# Negative: explicitly reject what the LoRA wrongly learned
NEG = (
    "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
    "blurry, watermark, text, logo, cropped, 3d, vroid, "
    "white hair, blonde hair, silver hair, purple eyes, brown eyes, "
    "school uniform, sailor uniform"
)

# 修正后的核心 prompt（角色外貌按实际视觉基准）
CHAR_FULL = (
    "yukixue, 1girl, solo, "
    "black hair, very long straight black hair, center part, hair past chest, "
    "grey eyes, cold grey eyes, pale skin, "
    "cold expression, expressionless, detached, "
    "white turtleneck sweater, black skirt, "
    "full body, standing, simple background"
)

CHAR_BUST = (
    "yukixue, 1girl, solo, "
    "black hair, very long straight black hair, center part, "
    "grey eyes, cold grey eyes, pale skin, "
    "cold expression, expressionless, "
    "white turtleneck sweater, "
    "upper body, portrait, looking at viewer"
)

# Baseline: no trigger word, pure prompt-only test
BASELINE = (
    "1girl, solo, "
    "black hair, very long straight black hair, center part, hair past chest, "
    "grey eyes, cold grey eyes, pale skin, "
    "cold expression, expressionless, detached, "
    "white turtleneck sweater, black skirt, "
    "full body, standing, simple background"
)

TESTS = [
    # ── LoRA scale sweep: 找发色与人物还原的平衡点 ──────────────
    {
        "name": "01_fullbody_scale08",
        "prompt": CHAR_FULL,
        "lora_scale": 0.8,
        "width": 512, "height": 768, "seed": 42,
    },
    {
        "name": "02_fullbody_scale07",
        "prompt": CHAR_FULL,
        "lora_scale": 0.7,
        "width": 512, "height": 768, "seed": 42,
    },
    {
        "name": "03_fullbody_scale05",
        "prompt": CHAR_FULL,
        "lora_scale": 0.5,
        "width": 512, "height": 768, "seed": 42,
    },
    # ── Portrait ────────────────────────────────────────────────
    {
        "name": "04_portrait_scale08",
        "prompt": CHAR_BUST + ", soft lighting",
        "lora_scale": 0.8,
        "width": 512, "height": 512, "seed": 42,
    },
    {
        "name": "05_portrait_scale06",
        "prompt": CHAR_BUST + ", soft lighting",
        "lora_scale": 0.6,
        "width": 512, "height": 512, "seed": 42,
    },
    # ── 不同 seed 验证稳定性（scale 0.7）────────────────────────
    {
        "name": "06_fullbody_scale07_seed123",
        "prompt": CHAR_FULL,
        "lora_scale": 0.7,
        "width": 512, "height": 768, "seed": 123,
    },
    {
        "name": "07_fullbody_scale07_seed7",
        "prompt": CHAR_FULL,
        "lora_scale": 0.7,
        "width": 512, "height": 768, "seed": 7,
    },
    # ── Baseline 对照（无 trigger，纯 prompt）───────────────────
    {
        "name": "08_no_lora_baseline_corrected",
        "prompt": BASELINE,
        "lora_scale": 0.0,
        "width": 512, "height": 768, "seed": 42,
    },
]

print(f"Loading AOM3 from {MODEL} ...")
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

print(f"Loading LoRA v2 from {LORA} ...")
pipe.load_lora_weights(str(Path(LORA).parent), weight_name=Path(LORA).name)

for t in TESTS:
    print(f"\n[{t['name']}] lora_scale={t['lora_scale']} seed={t['seed']}")
    pipe.set_adapters(["default_0"], adapter_weights=[t["lora_scale"]])
    out = pipe(
        prompt=t["prompt"],
        negative_prompt=NEG,
        num_inference_steps=30,
        guidance_scale=7.5,
        clip_skip=1,
        width=t["width"],
        height=t["height"],
        generator=torch.Generator("cuda").manual_seed(t["seed"]),
    )
    p = OUTDIR / f"{t['name']}.png"
    out.images[0].save(p)
    print(f"  saved: {p}")

print(f"\nDone. Output → {OUTDIR}")
print("\nKey comparisons:")
print("  01 vs 02 vs 03: scale 0.8/0.7/0.5 — find hair-color vs face-structure balance")
print("  04 vs 05:       portrait scale 0.8/0.6")
print("  06+07:          seed stability at scale 0.7")
print("  08:             baseline with corrected prompt (no LoRA, no trigger)")
