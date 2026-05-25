"""
一次性脚本：生成雪的参考立绘，保存到本地。
用法：python gen_yuki_portrait.py
输出：C:/Users/Violet/.claude/yukibot/yuki_portrait.png
"""
import torch
from diffusers import StableDiffusionPipeline

MODEL_PATH = r"E:\stable-diffusion-webui\models\Stable-Diffusion\Realistic_Vision_V5.1_fp16.safetensors"
OUTPUT_PATH = r"C:\Users\Violet\.claude\yukibot\yuki_portrait.png"

POSITIVE = (
    "RAW photo, (best quality, masterpiece:1.2), "
    "1girl, solo, 23 years old, chinese young woman, "
    "long black hair, slight natural wave, side part, loose casual bangs, "
    "pale cool-toned skin, calm quiet expression, cold beauty, "
    "slightly distant gaze, defined nose bridge, thin lips, serene, "
    "wearing dark navy linen maxi dress, loose off-white cardigan, minimalist outfit, "
    "standing near window, soft natural daylight, clean simple interior, "
    "shallow depth of field, elegant understated beauty, clean aesthetic, "
    "film photography, 85mm portrait lens"
)

NEGATIVE = (
    "ugly, deformed, bad anatomy, bad hands, extra fingers, missing fingers, "
    "lowres, blurry, jpeg artifacts, watermark, text, logo, signature, "
    "heavy makeup, bright lipstick, colorful clothing, messy hair, "
    "smile, open mouth, laughing, teeth, "
    "anime, illustration, cartoon, painting, drawing, "
    "oversaturated, harsh lighting, studio lighting, flash"
)

print("[gen_yuki] 加载模型...")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH,
    torch_dtype=torch.float16,
    safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

print("[gen_yuki] 生成中（约 30 秒）...")
generator = torch.Generator("cuda").manual_seed(42)
result = pipe(
    prompt=POSITIVE,
    negative_prompt=NEGATIVE,
    width=512,
    height=768,
    num_inference_steps=35,
    guidance_scale=7.0,
    generator=generator,
)

image = result.images[0]
image.save(OUTPUT_PATH)
print(f"[gen_yuki] 完成，保存至：{OUTPUT_PATH}")
