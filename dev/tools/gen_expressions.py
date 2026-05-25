"""
雪的表情集
7种表情 × 2个模型 × 5个seed = 70张
输出：candidates/expressions/base_aom3/ 和 with_lora/
"""
import torch, os
from diffusers import StableDiffusionPipeline
from peft import PeftModel

MODEL_PATH = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
LORA_PATH  = r"C:\Users\Violet\.claude\yukibot\lora\yuki_lora"
OUT_BASE   = r"C:\Users\Violet\.claude\yukibot\candidates\expressions\base_aom3"
OUT_LORA   = r"C:\Users\Violet\.claude\yukibot\candidates\expressions\with_lora"
os.makedirs(OUT_BASE, exist_ok=True)
os.makedirs(OUT_LORA, exist_ok=True)

CHAR = (
    "1girl, solo, long straight black hair, natural center part, "
    "pale cold white skin, oval face, thin lips, "
    "slim, upper body portrait, simple neutral background, soft studio light, "
)

NEGATIVE = (
    "worst quality, low quality, bad anatomy, deformed face, "
    "extra fingers, bad hands, blurry, "
    "nsfw, loli, childish, text, watermark"
)

EXPRESSIONS = [
    {
        "name": "calm",
        "label": "平静",
        "expr": (
            "calm neutral expression, half-lidded eyes, "
            "relaxed mouth, quiet, composed, "
            "looking at viewer, serene"
        ),
    },
    {
        "name": "focused",
        "label": "专注",
        "expr": (
            "focused concentrated expression, eyes slightly narrowed, "
            "brow lightly furrowed, lips pressed together, "
            "looking slightly downward, absorbed in thought"
        ),
    },
    {
        "name": "contemplative",
        "label": "若有所思",
        "expr": (
            "contemplative thoughtful expression, distant gaze, "
            "eyes looking to the side or slightly upward, "
            "soft unfocused look, something on her mind, "
            "slight parting of lips"
        ),
    },
    {
        "name": "mild_surprise",
        "label": "轻微惊讶",
        "expr": (
            "mild surprise expression, eyes slightly widened, "
            "brows raised just a little, "
            "lips parted slightly, quiet astonishment, "
            "not dramatic, understated reaction"
        ),
    },
    {
        "name": "tired",
        "label": "疲惫",
        "expr": (
            "tired exhausted expression, heavy eyelids, "
            "eyes drooping slightly, pale and drained, "
            "subtle dark circles, calm despite fatigue, "
            "not dramatic, quietly worn out"
        ),
    },
    {
        "name": "slightly_sad",
        "label": "轻微难过",
        "expr": (
            "slightly sad melancholic expression, "
            "eyes cast down or to the side, "
            "soft mouth, brows slightly drawn together, "
            "not crying, just quietly carrying something heavy, "
            "restrained emotion"
        ),
    },
    {
        "name": "faint_smile",
        "label": "淡淡微笑",
        "expr": (
            "very faint barely-there smile, "
            "corners of mouth just slightly upturned, "
            "eyes soft and warm, "
            "the kind of smile she almost never shows, "
            "quiet and genuine, not wide, not performative"
        ),
    },
]

SEEDS = [21, 42, 63, 84, 105]

def run_batch(pipe, out_dir, prefix=""):
    total = len(EXPRESSIONS) * len(SEEDS)
    count = 0
    for expr in EXPRESSIONS:
        for seed in SEEDS:
            count += 1
            name = f"{expr['name']}_seed{seed}"
            out_path = os.path.join(out_dir, f"{name}.png")
            prompt = "masterpiece, best quality, " + prefix + CHAR + expr["expr"]
            print(f"  [{count}/{total}] {expr['label']} seed={seed}...")
            gen = torch.Generator("cuda").manual_seed(seed)
            result = pipe(
                prompt=prompt, negative_prompt=NEGATIVE,
                width=512, height=640,
                num_inference_steps=30, guidance_scale=7.5, generator=gen,
            )
            result.images[0].save(out_path)
    print(f"  完成，共 {total} 张 → {out_dir}")

print("=" * 50)
print("第一轮：表情集 Base AOM3")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH, torch_dtype=torch.float16, safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()
run_batch(pipe, OUT_BASE)
del pipe
torch.cuda.empty_cache()

print("\n" + "=" * 50)
print("第二轮：表情集 AOM3 + LoRA")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH, torch_dtype=torch.float16, safety_checker=None,
)
pipe.unet = PeftModel.from_pretrained(pipe.unet, LORA_PATH)
pipe.unet = pipe.unet.merge_and_unload()
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()
run_batch(pipe, OUT_LORA, prefix="yukixue, ")
del pipe
torch.cuda.empty_cache()

print("\n全部完成")
print(f"  base → {OUT_BASE}")
print(f"  lora → {OUT_LORA}")
print(f"  共 {len(EXPRESSIONS) * len(SEEDS) * 2} 张")
