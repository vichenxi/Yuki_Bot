"""
用三个动漫模型分别生成雪的立绘，保存到本地对比。
输出：
  yuki_anything.png
  yuki_counterfeit.png
  yuki_aom3.png
"""
import torch
from diffusers import StableDiffusionPipeline
import os

SD_DIR = r"E:\stable-diffusion-webui\models\Stable-Diffusion"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot"

POSITIVE = (
    "masterpiece, best quality, highres, "
    "1girl, solo, 23 years old, "
    "long black hair, loose bangs, slight natural wave, "
    "pale skin, cold expression, calm deep eyes, "
    "navy blue long dress, white loose cardigan, "
    "standing by window, soft indoor light, clean background, "
    "elegant, quiet, understated beauty, slim"
)

NEGATIVE = (
    "(worst quality, low quality:1.4), bad anatomy, bad hands, "
    "extra fingers, missing fingers, deformed, "
    "text, watermark, signature, logo, "
    "smile, open mouth, laughing, "
    "bright colors, heavy makeup, colorful outfit, "
    "nsfw, suggestive"
)

MODELS = [
    ("AnythingV5_v5PrtRE.safetensors",      "yuki_anything.png"),
    ("Counterfeit-V3.0_fix_fp16.safetensors", "yuki_counterfeit.png"),
    ("AOM3A1B_orangemixs.safetensors",        "yuki_aom3.png"),
]

for model_file, out_name in MODELS:
    model_path = os.path.join(SD_DIR, model_file)
    out_path = os.path.join(OUT_DIR, out_name)
    print(f"\n=== {model_file} ===")
    print("加载模型...")
    pipe = StableDiffusionPipeline.from_single_file(
        model_path,
        torch_dtype=torch.float16,
        safety_checker=None,
    )
    pipe = pipe.to("cuda")
    pipe.enable_attention_slicing()

    print("生成中...")
    generator = torch.Generator("cuda").manual_seed(42)
    result = pipe(
        prompt=POSITIVE,
        negative_prompt=NEGATIVE,
        width=512,
        height=768,
        num_inference_steps=30,
        guidance_scale=7.5,
        generator=generator,
    )
    result.images[0].save(out_path)
    print(f"保存至：{out_path}")

    del pipe
    torch.cuda.empty_cache()

print("\n全部完成")
