"""
第一步：生成高质量半身/面部主图
第二步：以主图为参考 img2img 生成全身图
"""
import torch
from diffusers import StableDiffusionPipeline, StableDiffusionImg2ImgPipeline
from PIL import Image
import os

MODEL   = r"E:\stable-diffusion-webui\models\Stable-Diffusion\meinamix_meinaV11.safetensors"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot"

PORTRAIT_POSITIVE = (
    "masterpiece, best quality, "
    "1girl, solo, upper body, portrait, "
    "long black hair, straight hair, natural side-part bangs, "
    "pale skin, (highly detailed face:1.4), (beautiful detailed eyes:1.3), "
    "defined nose bridge, thin lips, (cold expression:1.2), "
    "calm steady gaze, looking at viewer, "
    "white button-up blouse, soft indoor light from window, "
    "clean background, slim, quiet, art student"
)

PORTRAIT_NEGATIVE = (
    "worst quality, low quality, bad anatomy, "
    "extra fingers, missing fingers, deformed, "
    "blurry, flat face, featureless face, "
    "text, watermark, smile, open mouth, "
    "loli, childish, moe, baby face, "
    "nsfw"
)

BODY_POSITIVE = (
    "masterpiece, best quality, "
    "1girl, solo, full body, "
    "long black hair, straight hair, natural side-part bangs, "
    "pale skin, detailed face, cold expression, looking at viewer, "
    "dark navy long skirt, white button-up blouse, tucked in, "
    "minimalist everyday outfit, "
    "standing by window, soft natural daylight, clean room, "
    "slim, quiet, elegant, art student"
)

BODY_NEGATIVE = (
    "worst quality, low quality, bad anatomy, bad hands, "
    "extra fingers, missing fingers, deformed, "
    "blurry face, featureless, "
    "text, watermark, smile, open mouth, "
    "loli, childish, moe, baby face, "
    "oversized clothes, costume, fantasy, nsfw"
)

# ── Step 1: 半身主图 ───────────────────────────────────────────
print("=== Step 1: 生成面部/半身主图 ===")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL, torch_dtype=torch.float16, safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

best_seed = None
for seed in [42, 123, 512, 999, 1234]:
    out_path = os.path.join(OUT_DIR, f"yuki_portrait_s{seed}.png")
    generator = torch.Generator("cuda").manual_seed(seed)
    result = pipe(
        prompt=PORTRAIT_POSITIVE,
        negative_prompt=PORTRAIT_NEGATIVE,
        width=512, height=640,
        num_inference_steps=40,
        guidance_scale=7.5,
        generator=generator,
    )
    result.images[0].save(out_path)
    print(f"portrait seed={seed} → {out_path}")

del pipe
torch.cuda.empty_cache()

print("\nStep 1 完成，请选择最佳半身图 seed 后继续 Step 2")
print("（Step 2 脚本：gen_yuki_body_from_portrait.py）")
