"""
ControlNet + LoRA — corrected COCO-18 skeletons, pose-matched scenes.
AnythingV5 + CounterfeitV3, each model runs all poses.
"""
import torch
from pathlib import Path
from PIL import Image, ImageDraw
from diffusers import StableDiffusionControlNetPipeline, ControlNetModel, DPMSolverMultistepScheduler
from compel import Compel

# ── Corrected COCO-18 ────────────────────────────────────────────────────────
# 0:nose  1:neck  2:R_sho  3:R_elb  4:R_wri  5:L_sho  6:L_elb  7:L_wri
# 8:R_hip  9:R_kne  10:R_ank  11:L_hip  12:L_kne  13:L_ank
# 14:R_eye  15:L_eye  16:R_ear  17:L_ear
#
# Neck connects ONLY to: shoulders (2,5) + nose (0).
# Hips connect to same-side shoulder: R_sho(2)→R_hip(8), L_sho(5)→L_hip(11).

LIMBS = [
    (1, 2), (1, 5),               # neck → shoulders
    (2, 3), (3, 4),               # R arm
    (5, 6), (6, 7),               # L arm
    (2, 8),  (8, 9),  (9, 10),   # R_sho → R_hip → R_kne → R_ank
    (5, 11), (11, 12), (12, 13), # L_sho → L_hip → L_kne → L_ank
    (1, 0),                       # neck → nose
    (0, 14), (14, 16),            # nose → R_eye → R_ear
    (0, 15), (15, 17),            # nose → L_eye → L_ear
]

LIMB_COLORS = [
    (255, 0, 0),   (255, 85, 0),  (255, 170, 0), (255, 255, 0),
    (170, 255, 0), (85, 255, 0),  (0, 255, 0),   (0, 255, 85),
    (0, 255, 170), (0, 255, 255), (0, 170, 255), (0, 85, 255),
    (0, 0, 255),   (85, 0, 255),  (170, 0, 255), (255, 0, 255), (255, 0, 170),
]

KP_COLOR = (255, 255, 255)


def draw_pose(keypoints, w=512, h=768, r=6, lw=4):
    canvas = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    for i, (a, b) in enumerate(LIMBS):
        if keypoints[a] is None or keypoints[b] is None:
            continue
        draw.line([keypoints[a], keypoints[b]], fill=LIMB_COLORS[i], width=lw)
    for kp in keypoints:
        if kp is None:
            continue
        x, y = kp
        draw.ellipse([x - r, y - r, x + r, y + r], fill=KP_COLOR)
    return canvas


# ── Poses (512×768, COCO-18 keypoint order) ──────────────────────────────────

def pose_sit_front():
    return [
        (256, 108),  #  0 nose
        (256, 168),  #  1 neck
        (208, 192),  #  2 R_sho
        (178, 260),  #  3 R_elb
        (158, 320),  #  4 R_wri
        (304, 192),  #  5 L_sho
        (334, 260),  #  6 L_elb
        (354, 320),  #  7 L_wri
        (222, 370),  #  8 R_hip
        (222, 530),  #  9 R_kne
        (215, 640),  # 10 R_ank
        (290, 370),  # 11 L_hip
        (290, 530),  # 12 L_kne
        (297, 640),  # 13 L_ank
        (244,  96),  # 14 R_eye
        (268,  96),  # 15 L_eye
        (232, 106),  # 16 R_ear
        (280, 106),  # 17 L_ear
    ]


def pose_sit_3q():
    return [
        (240, 108),  #  0 nose
        (248, 168),  #  1 neck
        (190, 188),  #  2 R_sho
        (155, 255),  #  3 R_elb
        (138, 315),  #  4 R_wri
        (306, 190),  #  5 L_sho
        (328, 252),  #  6 L_elb
        (340, 308),  #  7 L_wri
        (210, 365),  #  8 R_hip
        (210, 525),  #  9 R_kne
        (205, 638),  # 10 R_ank
        (286, 368),  # 11 L_hip
        (280, 525),  # 12 L_kne
        (278, 638),  # 13 L_ank
        (228,  96),  # 14 R_eye
        (255,  97),  # 15 L_eye
        (215, 107),  # 16 R_ear
        (270, 107),  # 17 L_ear
    ]


def pose_stand_3q():
    return [
        (240,  80),  #  0 nose
        (248, 148),  #  1 neck
        (188, 172),  #  2 R_sho
        (162, 268),  #  3 R_elb
        (148, 356),  #  4 R_wri
        (308, 174),  #  5 L_sho
        (330, 268),  #  6 L_elb
        (342, 352),  #  7 L_wri
        (210, 360),  #  8 R_hip
        (208, 520),  #  9 R_kne
        (205, 680),  # 10 R_ank
        (288, 362),  # 11 L_hip
        (284, 520),  # 12 L_kne
        (282, 680),  # 13 L_ank
        (228,  68),  # 14 R_eye
        (255,  69),  # 15 L_eye
        (215,  78),  # 16 R_ear
        (268,  78),  # 17 L_ear
    ]


def pose_lean_wall():
    return [
        (268,  88),  #  0 nose
        (262, 155),  #  1 neck
        (200, 178),  #  2 R_sho
        (185, 262),  #  3 R_elb
        (192, 342),  #  4 R_wri
        (318, 182),  #  5 L_sho
        (308, 268),  #  6 L_elb
        (280, 338),  #  7 L_wri
        (220, 368),  #  8 R_hip
        (228, 525),  #  9 R_kne
        (232, 682),  # 10 R_ank
        (300, 362),  # 11 L_hip
        (288, 520),  # 12 L_kne
        (278, 680),  # 13 L_ank
        (256,  76),  # 14 R_eye
        (280,  77),  # 15 L_eye
        (244,  86),  # 16 R_ear
        (292,  87),  # 17 L_ear
    ]


# ── Character base + per-pose scene prompts ──────────────────────────────────

BASE = (
    "yukixue, 1girl, solo, mature woman, adult, "
    "very long straight hair, center part, "
    "grey eyes, (narrow eyes:1.5), thin eyes, hooded eyes, half-closed eyes, "
    "sharp features, high cheekbones, pale skin, "
    "cold expression, expressionless, aloof, detached, cool, dignified, "
)

NEG = (
    "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
    "missing feet, cropped, blurry, watermark, text, logo, 3d, vroid"
)

POSES = {
    "sit_front": {
        "kps":    pose_sit_front(),
        "scene":  "sitting, upper body, classroom, blackboard background, wooden desks, chalk dust, indoor, soft natural lighting, looking at viewer",
    },
    "sit_3q": {
        "kps":    pose_sit_3q(),
        "scene":  "sitting, library, wooden bookshelves background, reading room, warm indoor lighting, books, quiet atmosphere",
    },
    "stand_3q": {
        "kps":    pose_stand_3q(),
        "scene":  "standing, full body, school corridor, hallway, large windows, afternoon sunlight, indoor, clean floor",
    },
    "lean_wall": {
        "kps":    pose_lean_wall(),
        "scene":  "leaning against wall, full body, school rooftop, blue sky, wind, casual, looking away",
    },
}

MODELS = [
    {
        "tag":       "cf",
        "model":     r"E:\stable-diffusion-webui\models\Stable-diffusion\Counterfeit-V3.0_fix_fp16.safetensors",
        "lora":      r"F:\bot\data\lora\output\yuki_lora_v3_counterfeit.safetensors",
        "clip_skip": 2,
        "scale":     0.7,
    },
    {
        "tag":       "any",
        "model":     r"E:\stable-diffusion-webui\models\Stable-diffusion\AnythingV5_v5PrtRE.safetensors",
        "lora":      r"F:\bot\data\lora\output\yuki_lora_v3_anything.safetensors",
        "clip_skip": 1,
        "scale":     0.7,
    },
]

SEEDS = [42, 123]

OUTDIR = Path(r"F:\bot\data\lora\test_images_v3_coco18_scenes")
OUTDIR.mkdir(parents=True, exist_ok=True)

POSE_DIR = OUTDIR / "poses"
POSE_DIR.mkdir(exist_ok=True)

for name, p in POSES.items():
    draw_pose(p["kps"]).save(POSE_DIR / f"{name}_skeleton.png")
print(f"Skeletons saved to {POSE_DIR}\n")

# ── Load ControlNet once ──────────────────────────────────────────────────────

print("Loading ControlNet ...")
controlnet = ControlNetModel.from_pretrained(
    "lllyasviel/control_v11p_sd15_openpose",
    torch_dtype=torch.float16,
)

# ── Per-model loop ────────────────────────────────────────────────────────────

for m in MODELS:
    print(f"\n{'='*55}")
    print(f"Model: {m['tag']}")
    pipe = StableDiffusionControlNetPipeline.from_single_file(
        m["model"],
        controlnet=controlnet,
        torch_dtype=torch.float16,
        use_safetensors=True,
    )
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(
        pipe.scheduler.config, use_karras_sigmas=True,
    )
    pipe = pipe.to("cuda")
    pipe.enable_attention_slicing()

    lora_path = Path(m["lora"])
    pipe.load_lora_weights(str(lora_path.parent), weight_name=lora_path.name)
    pipe.set_adapters(["default_0"], adapter_weights=[m["scale"]])

    for pose_name, pose_data in POSES.items():
        prompt = BASE + pose_data["scene"]
        compel = Compel(tokenizer=pipe.tokenizer, text_encoder=pipe.text_encoder)
        pos_embeds = compel(prompt)
        neg_embeds = compel(NEG)
        pos_embeds, neg_embeds = compel.pad_conditioning_tensors_to_same_length(
            [pos_embeds, neg_embeds]
        )
        skeleton_img = draw_pose(pose_data["kps"])

        for seed in SEEDS:
            name = f"{pose_name}_{m['tag']}_seed{seed}"
            print(f"  [{name}]")
            out = pipe(
                prompt_embeds=pos_embeds,
                negative_prompt_embeds=neg_embeds,
                image=skeleton_img,
                num_inference_steps=30,
                guidance_scale=7.5,
                controlnet_conditioning_scale=1.0,
                clip_skip=m["clip_skip"],
                width=512,
                height=768,
                generator=torch.Generator("cuda").manual_seed(seed),
            )
            p_out = OUTDIR / f"{name}.png"
            out.images[0].save(p_out)
            print(f"    saved: {p_out}")

    del pipe
    torch.cuda.empty_cache()

print(f"\nDone. Output → {OUTDIR}")
