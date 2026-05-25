"""
雪 全矩阵生成 — 角色基准 v1.1
8 场景 × 10 姿态 × 2 模型 = 160 张
输出：full_matrix/base_aom3/ 和 full_matrix/with_lora/
"""
import torch, os
from diffusers import StableDiffusionPipeline
from peft import PeftModel

MODEL_PATH = r"E:\stable-diffusion-webui\models\Stable-Diffusion\AOM3A1B_orangemixs.safetensors"
LORA_PATH  = r"C:\Users\Violet\.claude\yukibot\lora\yuki_lora"
OUT_BASE   = r"C:\Users\Violet\.claude\yukibot\full_matrix\base_aom3"
OUT_LORA   = r"C:\Users\Violet\.claude\yukibot\full_matrix\with_lora"
os.makedirs(OUT_BASE, exist_ok=True)
os.makedirs(OUT_LORA, exist_ok=True)

# ── 角色基准 v1.1 ───────────────────────────────────────────────────
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
    "blurry, nsfw, loli, childish, moe, text, watermark"
)

# ── 场景 ────────────────────────────────────────────────────────────
SCENES = [
    ("sc01_library",    "library aisle, warm reading lamp, tall bookshelves, quiet"),
    ("sc02_convstore",  "convenience store at night, soft fluorescent light, empty aisle"),
    ("sc03_subway",     "subway car interior, soft interior light, blurred city outside window"),
    ("sc04_corridor",   "covered outdoor corridor, rain falling outside, wet ground reflection"),
    ("sc05_dorm",       "dorm room by window, morning curtain light, warm interior"),
    ("sc06_gallery",    "modern art gallery, white walls, clean spotlight, minimal space"),
    ("sc07_busstop",    "bus stop at dusk, street lamp beginning to glow, quiet road, fallen leaves"),
    ("sc08_studio",     "design studio desk, monitor glow, afternoon side window light, papers"),
]

# ── 姿态 ────────────────────────────────────────────────────────────
POSES = [
    ("p01_stand",       "standing upright, arms at sides, full body, looking at viewer"),
    ("p02_arms_cross",  "arms loosely crossed at chest, weight on one leg, slight hip shift"),
    ("p03_pockets",     "both hands in pockets, relaxed shoulders, full body"),
    ("p04_hair_touch",  "one hand lightly touching hair near ear, slight downward gaze"),
    ("p05_sit_chair",   "sitting on chair, legs together, hands on lap, upright posture"),
    ("p06_sit_steps",   "sitting on steps, knees slightly raised, arms resting on knees"),
    ("p07_lean_wall",   "leaning back against wall, arms loosely at sides, one knee slightly bent"),
    ("p08_back_glance", "back facing viewer, turning head to look over shoulder, hair falling forward"),
    ("p09_side",        "strict side profile, standing, arms at sides, looking straight ahead"),
    ("p10_look_up",     "head tilted slightly upward, eyes looking up, arms at sides, standing"),
]

SEED = 303

def run_batch(pipe, out_dir, prefix=""):
    total = len(SCENES) * len(POSES)
    count = 0
    for s_id, s_bg in SCENES:
        for p_id, p_pose in POSES:
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
                + s_bg + ", "
                + p_pose
            )
            gen = torch.Generator("cuda").manual_seed(SEED)
            result = pipe(
                prompt=prompt, negative_prompt=NEGATIVE,
                width=512, height=768,
                num_inference_steps=30, guidance_scale=7.5, generator=gen,
            )
            result.images[0].save(out_path)
            print(f"  [{count}/{total}] {name}")

print("=" * 55)
print("第一轮：Base AOM3  (80 张)")
print("=" * 55)
pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH, torch_dtype=torch.float16, safety_checker=None,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()
run_batch(pipe, OUT_BASE)
del pipe
torch.cuda.empty_cache()
print("Base AOM3 完成\n")

print("=" * 55)
print("第二轮：AOM3 + LoRA  (80 张)")
print("=" * 55)
pipe = StableDiffusionPipeline.from_single_file(
    MODEL_PATH, torch_dtype=torch.float16, safety_checker=None,
)
pipe.unet = PeftModel.from_pretrained(pipe.unet, LORA_PATH)
pipe.unet = pipe.unet.merge_and_unload()
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()
run_batch(pipe, OUT_LORA, prefix="yukixue, ")
del pipe
torch.cuda.empty_cache()

print(f"\n全部完成：160 张")
print(f"  base → {OUT_BASE}")
print(f"  lora → {OUT_LORA}")
