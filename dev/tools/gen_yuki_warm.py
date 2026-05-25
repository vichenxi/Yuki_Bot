"""
789 基础上调温度：去掉 cold，加 serene / gentle / quiet warmth
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
    "(serene expression:1.2), (gentle gaze:1.2), quiet warmth, calm, "
    "looking at viewer, "
    "white blouse, dark navy long skirt, "
    "standing by window, natural light, clean room, "
    "slim, elegant, understated"
)

NEGATIVE = (
    "worst quality, low quality, bad anatomy, bad hands, "
    "extra fingers, missing fingers, deformed, "
    "blurry face, flat face, featureless, "
    "text, watermark, "
    "(smile:1.3), open mouth, laughing, "
    "loli, childish, moe, baby face, "
    "cold, icy, stern, angry, "
    "fantasy, armor, costume, jewelry, nsfw"
)

print("加载模型...")
pipe = StableDiffusionImg2ImgPipeline.from_single_file(
    MODEL, torch_dtype=torch.float16, safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

src = Image.open(SRC).convert("RGB")

for seed in [789, 790, 791, 888]:
    out_path = os.path.join(OUT_DIR, f"yuki_warm_s{seed}.png")
    print(f"生成 seed={seed}...")
    generator = torch.Generator("cuda").manual_seed(seed)
    result = pipe(
        prompt=POSITIVE,
        negative_prompt=NEGATIVE,
        image=src,
        strength=0.45,
        num_inference_steps=40,
        guidance_scale=7.5,
        generator=generator,
    )
    result.images[0].save(out_path)
    print(f"保存：{out_path}")

del pipe
torch.cuda.empty_cache()
print("完成")
