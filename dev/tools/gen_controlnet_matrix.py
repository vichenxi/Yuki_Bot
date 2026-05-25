"""
ControlNet + OpenPose 全矩阵生成
骨架控制姿态：10 姿态 × 8 场景 × 2 模型 = 160 张
输出：controlnet_matrix/base_aom3/ 和 controlnet_matrix/with_lora/
"""
import torch, os
from PIL import Image
from diffusers import StableDiffusionControlNetPipeline, ControlNetModel, UniPCMultistepScheduler
from peft import PeftModel

MODEL_PATH     = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
LORA_PATH      = r"C:\Users\Violet\.claude\yukibot\lora\yuki_lora"
CONTROLNET_DIR = r"C:\Users\Violet\.claude\yukibot\weights\controlnet_openpose"
SKELETON_DIR   = r"C:\Users\Violet\.claude\yukibot\pose_skeletons"
OUT_BASE       = r"C:\Users\Violet\.claude\yukibot\controlnet_matrix\base_aom3"
OUT_LORA       = r"C:\Users\Violet\.claude\yukibot\controlnet_matrix\with_lora"
os.makedirs(OUT_BASE, exist_ok=True)
os.makedirs(OUT_LORA, exist_ok=True)

# ── 角色基准 v1.1 ────────────────────────────────────────────────────
CHAR = (
    "1girl, solo, "
    "long straight black hair, natural center part, "
    "pale cold white skin, oval face, thin lips, "
    "(cold grey eyes:1.5), silver grey iris, "
    "calm serene expression, "
    "slim body, correct proportions, natural anatomy, elegant posture, "
    "dark midi skirt, simple top, "
)

NEGATIVE = (
    "worst quality, low quality, "
    "bad anatomy, bad proportions, deformed body, "
    "extra limbs, missing limbs, fused fingers, extra fingers, "
    "bad hands, floating limbs, distorted torso, long neck, "
    "amber eyes, brown eyes, yellow eyes, purple eyes, "
    "white hair, grey hair, silver hair, "
    "blurry, nsfw, loli, childish, moe, text, watermark"
)

# ── 场景 ─────────────────────────────────────────────────────────────
SCENES = [
    ("sc01_library",   "library aisle, warm reading lamp, tall bookshelves, quiet"),
    ("sc02_convstore", "convenience store at night, soft fluorescent light, empty aisle"),
    ("sc03_subway",    "subway car interior, soft interior light, blurred city outside window"),
    ("sc04_corridor",  "covered outdoor corridor, rain falling outside, wet ground reflection"),
    ("sc05_dorm",      "dorm room by window, morning curtain light, warm interior"),
    ("sc06_gallery",   "modern art gallery, white walls, clean spotlight, minimal space"),
    ("sc07_busstop",   "bus stop at dusk, street lamp beginning to glow, quiet road, fallen leaves"),
    ("sc08_studio",    "design studio desk, monitor glow, afternoon side window light, papers"),
]

# ── 姿态（骨架文件名） ───────────────────────────────────────────────
POSES = [
    "p01_stand", "p02_arms_cross", "p03_pockets", "p04_hair_touch",
    "p05_sit_chair", "p06_sit_steps", "p07_lean_wall",
    "p08_back_glance", "p09_side", "p10_look_up",
]

SEED = 303


def load_skeletons():
    skels = {}
    for p_id in POSES:
        path = os.path.join(SKELETON_DIR, f"{p_id}.png")
        skels[p_id] = Image.open(path).convert("RGB")
    return skels


def run_batch(pipe, out_dir, skeletons, prefix=""):
    total = len(SCENES) * len(POSES)
    count = 0
    for s_id, s_bg in SCENES:
        for p_id in POSES:
            count += 1
            name = f"{s_id}_{p_id}"
            out_path = os.path.join(out_dir, f"{name}.png")
            if os.path.exists(out_path):
                print(f"  [{count}/{total}] {name} 已存在，跳过")
                continue
            prompt = (
                "masterpiece, best quality, "
                + prefix
                + CHAR
                + s_bg
            )
            gen = torch.Generator("cuda").manual_seed(SEED)
            result = pipe(
                prompt=prompt,
                negative_prompt=NEGATIVE,
                image=skeletons[p_id],
                width=512, height=768,
                num_inference_steps=30,
                guidance_scale=7.5,
                controlnet_conditioning_scale=0.9,
                generator=gen,
            )
            result.images[0].save(out_path)
            print(f"  [{count}/{total}] {name}")


print("加载骨架图...")
skeletons = load_skeletons()
print(f"  共 {len(skeletons)} 个姿态")

print("\n加载 ControlNet 模型...")
controlnet = ControlNetModel.from_pretrained(CONTROLNET_DIR, torch_dtype=torch.float16)

# ── 第一轮：Base AOM3 ─────────────────────────────────────────────────
print("=" * 55)
print("第一轮：Base AOM3  (80 张)")
print("=" * 55)
pipe = StableDiffusionControlNetPipeline.from_single_file(
    MODEL_PATH,
    controlnet=controlnet,
    torch_dtype=torch.float16,
    safety_checker=None,
)
pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()
run_batch(pipe, OUT_BASE, skeletons)
del pipe
torch.cuda.empty_cache()
print("Base AOM3 完成\n")

# ── 第二轮：AOM3 + LoRA ──────────────────────────────────────────────
print("=" * 55)
print("第二轮：AOM3 + LoRA  (80 张)")
print("=" * 55)
pipe = StableDiffusionControlNetPipeline.from_single_file(
    MODEL_PATH,
    controlnet=controlnet,
    torch_dtype=torch.float16,
    safety_checker=None,
)
pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
pipe.unet = PeftModel.from_pretrained(pipe.unet, LORA_PATH)
pipe.unet = pipe.unet.merge_and_unload()
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()
run_batch(pipe, OUT_LORA, skeletons, prefix="yukixue, ")
del pipe
torch.cuda.empty_cache()

print(f"\n全部完成：160 张")
print(f"  base → {OUT_BASE}")
print(f"  lora → {OUT_LORA}")
