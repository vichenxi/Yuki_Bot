"""
Step 2：以 yuki_portrait_s123.png 为底，img2img 生成全身图
"""
import torch
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import os

MODEL   = r"E:\stable-diffusion-webui\models\Stable-Diffusion\meinamix_meinaV11.safetensors"
SRC     = r"C:\Users\Violet\.claude\yukibot\yuki_portrait_s123.png"
OUT_DIR = r"C:\Users\Violet\.claude\yukibot"

POSITIVE = (
    "masterpiece, best quality, "
    "1girl, solo, full body, "
    "long black hair, straight hair, natural bangs, "
    "pale skin, detailed face, cold expression, looking at viewer, "
    "(dark navy pleated long skirt:1.5), (white button-up blouse:1.4), tucked in, "
    "(everyday clothing:1.3), minimalist, no accessories, "
    "standing by window, soft natural daylight, wooden floor, clean room, "
    "slim, quiet, elegant, art student, casual"
)

NEGATIVE = (
    "worst quality, low quality, bad anatomy, bad hands, "
    "extra fingers, missing fingers, deformed, "
    "text, watermark, smile, open mouth, "
    "loli, childish, moe, baby face, "
    "(fantasy:1.5), (armor:1.5), (costume:1.5), (gothic:1.4), "
    "(necklace:1.3), (jewelry:1.3), (crown:1.4), (tiara:1.4), "
    "(lace:1.3), (corset:1.3), dark background, dramatic lighting, "
    "sexy, nsfw"
)

print("加载模型...")
pipe = StableDiffusionImg2ImgPipeline.from_single_file(
    MODEL, torch_dtype=torch.float16, safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

src = Image.open(SRC).convert("RGB").resize((512, 768), Image.LANCZOS)

for strength, seed in [(0.65, 123), (0.65, 42), (0.70, 456)]:
    out_path = os.path.join(OUT_DIR, f"yuki_body_str{int(strength*100)}_s{seed}.png")
    print(f"生成 strength={strength} seed={seed}...")
    generator = torch.Generator("cuda").manual_seed(seed)
    result = pipe(
        prompt=POSITIVE,
        negative_prompt=NEGATIVE,
        image=src,
        strength=strength,
        num_inference_steps=40,
        guidance_scale=8.0,
        generator=generator,
    )
    result.images[0].save(out_path)
    print(f"保存：{out_path}")

del pipe
torch.cuda.empty_cache()
print("完成")
