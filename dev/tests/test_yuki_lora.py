"""
雪 LoRA 推理测试
验证角色一致性：不同场景/姿势下，面部和气质是否稳定
"""
import torch, os
from diffusers import StableDiffusionPipeline
from peft import PeftModel

MODEL_PATH = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
LORA_PATH  = r"C:\Users\Violet\.claude\yukibot\lora\yuki_lora"
OUT_DIR    = r"C:\Users\Violet\.claude\yukibot\lora_test"
os.makedirs(OUT_DIR, exist_ok=True)

NEGATIVE = (
    "worst quality, low quality, "
    "bad anatomy, bad proportions, deformed body, "
    "extra limbs, missing limbs, fused fingers, extra fingers, "
    "bad hands, wrong hands, floating limbs, distorted torso, "
    "blurry, jpeg artifacts, nsfw, loli, childish, moe, "
    "smile, open mouth, text, watermark, signature"
)

TESTS = [
    {
        "name": "01_portrait",
        "prompt": "yukixue, 1girl, long straight black hair, pale cold white skin, oval face, thin lips, calm expression, looking at viewer, upper body, soft light, simple background",
        "seed": 42,
    },
    {
        "name": "02_library",
        "prompt": "yukixue, 1girl, long straight black hair, pale cold white skin, calm expression, standing in library, holding book, dark turtleneck, dark midi skirt, soft warm light",
        "seed": 202,
    },
    {
        "name": "03_rooftop_night",
        "prompt": "yukixue, 1girl, long straight black hair, pale cold white skin, calm serene expression, standing on rooftop, city lights, night, oversized dark sweater, dark midi skirt",
        "seed": 303,
    },
    {
        "name": "04_subway",
        "prompt": "yukixue, 1girl, long straight black hair, pale cold white skin, calm expression, sitting in subway, looking out window, navy coat, dark skirt, contemplative",
        "seed": 512,
    },
    {
        "name": "05_side_profile",
        "prompt": "yukixue, 1girl, long straight black hair, pale cold white skin, side profile, standing, elegant posture, simple background, soft light",
        "seed": 888,
    },
    {
        "name": "06_sitting_steps",
        "prompt": "yukixue, 1girl, long straight black hair, pale cold white skin, calm expression, sitting on steps, knees slightly raised, oversized sweater, quiet solitude",
        "seed": 1024,
    },
]

print("加载基础模型...")
pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH, torch_dtype=torch.float16, safety_checker=None,
)
print("挂载 LoRA 权重...")
pipe.unet = PeftModel.from_pretrained(pipe.unet, LORA_PATH)
pipe.unet = pipe.unet.merge_and_unload()

pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

print(f"\n开始推理测试，共 {len(TESTS)} 张...\n")
for t in TESTS:
    out_path = os.path.join(OUT_DIR, f"{t['name']}.png")
    print(f"生成：{t['name']} (seed={t['seed']})...")
    generator = torch.Generator("cuda").manual_seed(t["seed"])
    result = pipe(
        prompt=t["prompt"],
        negative_prompt=NEGATIVE,
        width=512, height=768,
        num_inference_steps=30,
        guidance_scale=7.5,
        generator=generator,
    )
    result.images[0].save(out_path)
    print(f"保存：{out_path}")

del pipe
torch.cuda.empty_cache()
print("\n全部完成，结果在 lora_test/")
