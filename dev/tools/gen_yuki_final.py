"""
用 Anything V5 强化服装 prompt，多 seed 生成对比
"""
import torch
from diffusers import StableDiffusionPipeline
import os

MODEL = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AnythingV5_v5PrtRE.safetensors"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot"

POSITIVE = (
    "masterpiece, best quality, highres, "
    "1girl, solo, "
    "long black hair, straight hair, loose bangs, "
    "pale skin, cold expression, calm eyes, looking at viewer, "
    "(dark navy blue long dress:1.3), (white loose cardigan:1.2), "
    "full body, standing by window, soft indoor light, "
    "elegant, quiet, slim, clean background"
)

NEGATIVE = (
    "(worst quality, low quality:1.4), bad anatomy, bad hands, "
    "extra fingers, missing fingers, deformed, ugly, "
    "text, watermark, signature, "
    "smile, open mouth, "
    "white dress, bright dress, colorful outfit, "
    "hair covering face, hair over eyes, "
    "nsfw"
)

SEEDS = [42, 123, 789, 2024]

print("加载模型...")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL,
    torch_dtype=torch.float16,
    safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

for seed in SEEDS:
    out_path = os.path.join(OUT_DIR, f"yuki_s{seed}.png")
    print(f"生成 seed={seed}...")
    generator = torch.Generator("cuda").manual_seed(seed)
    result = pipe(
        prompt=POSITIVE,
        negative_prompt=NEGATIVE,
        width=512,
        height=768,
        num_inference_steps=35,
        guidance_scale=7.5,
        generator=generator,
    )
    result.images[0].save(out_path)
    print(f"保存：{out_path}")

del pipe
torch.cuda.empty_cache()
print("完成")
