"""
训练集候选生成
- base AOM3（无 LoRA）×10 张
- AOM3 + LoRA ×10 张
- txt2img，自由场景/服装，供用户筛选后手动加入基准集
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
    "worst quality, low quality, "
    "bad anatomy, bad proportions, deformed body, "
    "extra limbs, missing limbs, fused fingers, extra fingers, "
    "bad hands, floating limbs, distorted torso, "
    "blurry, nsfw, loli, childish, text, watermark"
)

PROMPTS = [
    {
        "name": "01_summer_dress_park",
        "scene": "white linen summer dress, sleeveless, standing in sunlit park, dappled light through trees, looking slightly away",
    },
    {
        "name": "02_oversized_hoodie_dorm",
        "scene": "oversized grey hoodie, shorts, sitting cross-legged on bed, laptop in front, indoor warm light, relaxed",
    },
    {
        "name": "03_school_uniform_rooftop",
        "scene": "dark navy school uniform, white collar, standing on rooftop, wind in hair, daytime blue sky",
    },
    {
        "name": "04_trench_coat_rain",
        "scene": "beige trench coat, holding umbrella, walking in light rain, wet pavement reflection, city street",
    },
    {
        "name": "05_knit_sweater_cafe",
        "scene": "cream ribbed knit turtleneck, sitting at cafe window, cup of tea, rainy window, soft warm light",
    },
    {
        "name": "06_blazer_office",
        "scene": "fitted dark blazer, white inner shirt, standing in modern office corridor, glass walls, clean professional look",
    },
    {
        "name": "07_pajamas_morning",
        "scene": "loose striped pajamas, sitting on floor leaning against bed, morning light, drowsy calm expression",
    },
    {
        "name": "08_gallery_formal",
        "scene": "black midi dress, simple cut, standing in art gallery, white walls, soft spotlight, absorbed in artwork",
    },
    {
        "name": "09_sportswear_campus",
        "scene": "dark athletic jacket, jogger pants, standing on campus path, earphones in, afternoon light",
    },
    {
        "name": "10_hanbok_inspired",
        "scene": "modern hanbok-inspired outfit, dark jeogori, soft grey chima, standing in traditional courtyard, warm light",
    },
]

SEEDS = [11, 22, 33, 44, 55, 66, 77, 88, 99, 111]

# ── Base AOM3（无 LoRA）──────────────────────────────────────────────
print("=" * 50)
print("第一轮：Base AOM3（无 LoRA）")
print("=" * 50)
pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH, torch_dtype=torch.float16, safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

for i, (p, seed) in enumerate(zip(PROMPTS, SEEDS)):
    prompt = "masterpiece, best quality, " + CHAR + p["scene"]
    out_path = os.path.join(OUT_BASE, f"{p['name']}.png")
    print(f"[{i+1}/10] {p['name']} (seed={seed})...")
    gen = torch.Generator("cuda").manual_seed(seed)
    result = pipe(
        prompt=prompt, negative_prompt=NEGATIVE,
        width=512, height=768,
        num_inference_steps=30, guidance_scale=7.5, generator=gen,
    )
    result.images[0].save(out_path)

del pipe
torch.cuda.empty_cache()
print("Base AOM3 完成\n")

# ── AOM3 + LoRA ─────────────────────────────────────────────────────
print("=" * 50)
print("第二轮：AOM3 + LoRA")
print("=" * 50)
pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH, torch_dtype=torch.float16, safety_checker=None,
)
pipe.unet = PeftModel.from_pretrained(pipe.unet, LORA_PATH)
pipe.unet = pipe.unet.merge_and_unload()
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

for i, (p, seed) in enumerate(zip(PROMPTS, SEEDS)):
    prompt = "masterpiece, best quality, yukixue, " + CHAR + p["scene"]
    out_path = os.path.join(OUT_LORA, f"{p['name']}.png")
    print(f"[{i+1}/10] {p['name']} (seed={seed})...")
    gen = torch.Generator("cuda").manual_seed(seed)
    result = pipe(
        prompt=prompt, negative_prompt=NEGATIVE,
        width=512, height=768,
        num_inference_steps=30, guidance_scale=7.5, generator=gen,
    )
    result.images[0].save(out_path)

del pipe
torch.cuda.empty_cache()
print("\nLoRA 轮完成")
print(f"\n全部完成：")
print(f"  base AOM3 → {OUT_BASE}")
print(f"  with LoRA → {OUT_LORA}")
