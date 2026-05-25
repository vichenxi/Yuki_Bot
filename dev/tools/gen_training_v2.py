"""
训练集候选 v2 — 增加服装颜色丰富度
显式指定颜色词，加暖色/冷色光源，强制饱和度
base AOM3 × 10，AOM3 + LoRA × 10
"""
import torch, os
from diffusers import StableDiffusionPipeline
from peft import PeftModel

MODEL_PATH = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
LORA_PATH  = r"C:\Users\Violet\.claude\yukibot\lora\yuki_lora"
OUT_BASE   = r"C:\Users\Violet\.claude\yukibot\candidates\base_aom3"
OUT_LORA   = r"C:\Users\Violet\.claude\yukibot\candidates\with_lora"
os.makedirs(OUT_BASE, exist_ok=True)
os.makedirs(OUT_LORA, exist_ok=True)

CHAR = (
    "1girl, solo, long straight black hair, natural center part, "
    "pale cold white skin, oval face, thin lips, calm serene expression, "
    "slim elegant, "
)

NEGATIVE = (
    "worst quality, low quality, monochrome, grayscale, desaturated, "
    "bad anatomy, bad proportions, deformed body, "
    "extra limbs, missing limbs, fused fingers, extra fingers, "
    "bad hands, floating limbs, distorted torso, "
    "blurry, nsfw, loli, childish, text, watermark"
)

PROMPTS = [
    {
        "name": "v2_01_terracotta_dress",
        "scene": (
            "terracotta orange slip dress, thin straps, "
            "standing in warm afternoon sunlight, golden hour, "
            "soft shadow on wall, outdoor terrace, vibrant warm tones"
        ),
    },
    {
        "name": "v2_02_sage_green_coat",
        "scene": (
            "sage green long coat, cream turtleneck inside, "
            "walking in park, autumn, red and orange fallen leaves, "
            "dappled sunlight, rich autumn color palette"
        ),
    },
    {
        "name": "v2_03_dusty_rose_knit",
        "scene": (
            "dusty rose ribbed knit sweater, light blue wide-leg trousers, "
            "sitting on windowsill, late afternoon warm light, "
            "pastel tones, soft blush and blue contrast"
        ),
    },
    {
        "name": "v2_04_cobalt_blue_blazer",
        "scene": (
            "cobalt blue structured blazer, white inner shirt, black trousers, "
            "standing in modern gallery, clean white walls, "
            "cool saturated blue against neutral background"
        ),
    },
    {
        "name": "v2_05_caramel_cardigan",
        "scene": (
            "caramel brown oversized cardigan, white shirt underneath, dark jeans, "
            "sitting at wooden cafe table, warm amber lamp light, "
            "cozy interior, rich warm browns"
        ),
    },
    {
        "name": "v2_06_olive_jacket",
        "scene": (
            "olive green utility jacket, rust orange inner, "
            "leaning against brick wall, overcast day, "
            "urban street, muted but richly colored palette"
        ),
    },
    {
        "name": "v2_07_lavender_dress",
        "scene": (
            "soft lavender midi dress, light floral fabric, "
            "standing in morning light, open window, white curtain, "
            "gentle purple and white tones, airy spring atmosphere"
        ),
    },
    {
        "name": "v2_08_burgundy_turtleneck",
        "scene": (
            "deep burgundy turtleneck, black high-waist skirt, "
            "sitting on library steps, evening light from lantern, "
            "rich jewel tones, warm red against dark background"
        ),
    },
    {
        "name": "v2_09_teal_windbreaker",
        "scene": (
            "teal windbreaker jacket, grey joggers, white sneakers, "
            "walking along riverside at golden hour, "
            "vibrant teal against warm sky reflection in water"
        ),
    },
    {
        "name": "v2_10_mustard_blouse",
        "scene": (
            "mustard yellow loose blouse, dark wide skirt, "
            "standing in art bookstore, colorful book spines behind, "
            "warm yellow accent, eclectic colorful background"
        ),
    },
]

SEEDS = [301, 402, 503, 604, 705, 806, 907, 1008, 1109, 1210]

def run_batch(pipe, prompts, seeds, out_dir, prefix=""):
    for i, (p, seed) in enumerate(zip(prompts, seeds)):
        prompt = "masterpiece, best quality, highly detailed, " + prefix + CHAR + p["scene"]
        out_path = os.path.join(out_dir, f"{p['name']}.png")
        print(f"  [{i+1}/10] {p['name']} (seed={seed})...")
        gen = torch.Generator("cuda").manual_seed(seed)
        result = pipe(
            prompt=prompt, negative_prompt=NEGATIVE,
            width=512, height=768,
            num_inference_steps=30, guidance_scale=7.5, generator=gen,
        )
        result.images[0].save(out_path)

print("=" * 50)
print("第一轮：Base AOM3")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH, torch_dtype=torch.float16, safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()
run_batch(pipe, PROMPTS, SEEDS, OUT_BASE)
del pipe
torch.cuda.empty_cache()
print("Base AOM3 完成\n")

print("=" * 50)
print("第二轮：AOM3 + LoRA")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH, torch_dtype=torch.float16, safety_checker=None,
)
pipe.unet = PeftModel.from_pretrained(pipe.unet, LORA_PATH)
pipe.unet = pipe.unet.merge_and_unload()
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()
run_batch(pipe, PROMPTS, SEEDS, OUT_LORA, prefix="yukixue, ")
del pipe
torch.cuda.empty_cache()
print("\nLoRA 轮完成")
print(f"全部完成：base={OUT_BASE}  lora={OUT_LORA}")
