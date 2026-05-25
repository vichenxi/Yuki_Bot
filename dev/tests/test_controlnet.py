"""
ControlNet OpenPose 冒烟测试
用内置 OpenPose 生成器从参考图提取骨架，再用骨架控制生图
"""
import torch
from diffusers import StableDiffusionControlNetPipeline, ControlNetModel, UniPCMultistepScheduler
from controlnet_aux import OpenposeDetector
from PIL import Image
import os

MODEL_PATH     = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
CONTROLNET_DIR = r"C:\Users\Violet\.claude\yukibot\weights\controlnet_openpose"
SRC_IMG        = r"C:\Users\Violet\.claude\yukibot\yuki_warm_s789.png"
OUT_DIR        = r"C:\Users\Violet\.claude\yukibot\controlnet_test"
os.makedirs(OUT_DIR, exist_ok=True)

PROMPT = (
    "masterpiece, best quality, yukixue, "
    "1girl, solo, long straight black hair, natural center part, "
    "pale cold white skin, oval face, thin lips, "
    "(cold grey eyes:1.5), silver grey iris, "
    "calm serene expression, looking at viewer, "
    "dark midi skirt, simple dark top, "
    "soft ambient light, simple background"
)
NEGATIVE = (
    "worst quality, low quality, bad anatomy, bad proportions, "
    "extra limbs, fused fingers, bad hands, blurry, "
    "nsfw, loli, childish, text, watermark"
)

print("加载 OpenPose 检测器...")
detector = OpenposeDetector.from_pretrained("lllyasviel/ControlNet")

print("从源图提取骨架...")
src = Image.open(SRC_IMG).convert("RGB")
pose = detector(src)
pose.save(os.path.join(OUT_DIR, "pose_skeleton.png"))
print(f"骨架已保存")

print("加载 ControlNet 模型...")
controlnet = ControlNetModel.from_pretrained(CONTROLNET_DIR, torch_dtype=torch.float16)

print("加载 SD pipeline...")
pipe = StableDiffusionControlNetPipeline.from_single_file(
    MODEL_PATH,
    controlnet=controlnet,
    torch_dtype=torch.float16,
    safety_checker=None,
)
pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

print("生成测试图...")
generator = torch.Generator("cuda").manual_seed(303)
result = pipe(
    prompt=PROMPT,
    negative_prompt=NEGATIVE,
    image=pose,
    num_inference_steps=30,
    guidance_scale=7.5,
    controlnet_conditioning_scale=1.0,
    generator=generator,
)
result.images[0].save(os.path.join(OUT_DIR, "controlnet_test_result.png"))
print("完成：controlnet_test/controlnet_test_result.png")

del pipe
torch.cuda.empty_cache()
