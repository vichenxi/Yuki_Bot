"""
用 AOM3 对 meina s42 做低强度 img2img 风格迁移
保留构图和服装，把画风拉向 AOM3
"""
import torch
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import os

MODEL   = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
SRC     = r"C:\Users\Violet\.claude\yukibot\yuki_meina_s42.png"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot"

POSITIVE = (
    "masterpiece, best quality, "
    "1girl, solo, full body, "
    "long black hair, straight hair, natural bangs, "
    "pale skin, detailed face, beautiful eyes, defined nose, thin lips, "
    "cold expression, calm gaze, looking at viewer, "
    "white blouse, dark navy long skirt, "
    "standing by window, natural light, clean room, "
    "slim, quiet, elegant"
)

NEGATIVE = (
    "worst quality, low quality, bad anatomy, bad hands, "
    "extra fingers, missing fingers, deformed, "
    "blurry face, flat face, featureless, "
    "text, watermark, smile, open mouth, "
    "loli, childish, moe, baby face, "
    "fantasy, armor, costume, jewelry, nsfw"
)

print("加载模型...")
pipe = StableDiffusionImg2ImgPipeline.from_single_file(
    MODEL, torch_dtype=torch.float16, safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

src = Image.open(SRC).convert("RGB")

for strength, seed in [(0.35, 42), (0.40, 42), (0.40, 123), (0.45, 789)]:
    out_path = os.path.join(OUT_DIR, f"yuki_aom3_str{int(strength*100)}_s{seed}.png")
    print(f"生成 strength={strength} seed={seed}...")
    generator = torch.Generator("cuda").manual_seed(seed)
    result = pipe(
        prompt=POSITIVE,
        negative_prompt=NEGATIVE,
        image=src,
        strength=strength,
        num_inference_steps=40,
        guidance_scale=7.5,
        generator=generator,
    )
    result.images[0].save(out_path)
    print(f"保存：{out_path}")

del pipe
torch.cuda.empty_cache()
print("完成")
