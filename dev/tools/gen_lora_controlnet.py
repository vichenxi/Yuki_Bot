"""
ControlNet + LoRA — programmatic COCO-17 skeletons, no reference images needed.
CounterfeitV3 + yuki_lora_v3_counterfeit, classroom / various scenes.
"""
import numpy as np
import torch
from pathlib import Path
from PIL import Image, ImageDraw
from diffusers import StableDiffusionControlNetPipeline, ControlNetModel, DPMSolverMultistepScheduler
from compel import Compel

# ── COCO 17-point skeleton ───────────────────────────────────────────────────
# 0:nose  1:L_eye  2:R_eye  3:L_ear  4:R_ear
# 5:L_sho 6:R_sho  7:L_elb  8:R_elb  9:L_wri 10:R_wri
# 11:L_hip 12:R_hip 13:L_kne 14:R_kne 15:L_ank 16:R_ank

LIMBS = [
    (0, 1),   # nose → L_eye
    (0, 2),   # nose → R_eye
    (1, 3),   # L_eye → L_ear
    (2, 4),   # R_eye → R_ear
    (5, 6),   # L_sho → R_sho  (shoulder bar)
    (5, 7),   # L_sho → L_elb
    (7, 9),   # L_elb → L_wri
    (6, 8),   # R_sho → R_elb
    (8, 10),  # R_elb → R_wri
    (5, 11),  # L_sho → L_hip  (left torso side)
    (6, 12),  # R_sho → R_hip  (right torso side)
    (11, 12), # L_hip → R_hip  (hip bar)
    (11, 13), # L_hip → L_kne
    (13, 15), # L_kne → L_ank
    (12, 14), # R_hip → R_kne
    (14, 16), # R_kne → R_ank
]

LIMB_COLORS = [
    (255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0),
    (170, 255, 0), (85, 255, 0), (0, 255, 0), (0, 255, 85),
    (0, 255, 170), (0, 255, 255), (0, 170, 255), (0, 85, 255),
    (0, 0, 255), (85, 0, 255), (170, 0, 255), (255, 0, 255),
]

KP_COLOR = (255, 255, 255)


def draw_pose(keypoints, w=512, h=768, r=6, lw=4):
    """Draw a COCO-17 skeleton. keypoints: list of (x,y) or None (17 items)."""
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


# ── Pose definitions (512×768 canvas) ──────────────────────────────────────
# Index order: nose, L_eye, R_eye, L_ear, R_ear,
#              L_sho, R_sho, L_elb, R_elb, L_wri, R_wri,
#              L_hip, R_hip, L_kne, R_kne, L_ank, R_ank

def pose_sit_front():
    """Sitting, facing camera, arms resting on desk."""
    return [
        (256, 108),   #  0 nose
        (268,  96),   #  1 L_eye
        (244,  96),   #  2 R_eye
        (280, 106),   #  3 L_ear
        (232, 106),   #  4 R_ear
        (304, 192),   #  5 L_sho
        (208, 192),   #  6 R_sho
        (334, 260),   #  7 L_elb
        (178, 260),   #  8 R_elb
        (354, 320),   #  9 L_wri
        (158, 320),   # 10 R_wri
        (290, 370),   # 11 L_hip
        (222, 370),   # 12 R_hip
        (290, 530),   # 13 L_kne (bent, sitting)
        (222, 530),   # 14 R_kne
        (297, 640),   # 15 L_ank
        (215, 640),   # 16 R_ank
    ]


def pose_sit_3q():
    """Sitting, 3/4 view (turned slightly right)."""
    return [
        (240, 108),   #  0 nose
        (255,  97),   #  1 L_eye
        (228,  96),   #  2 R_eye
        (270, 107),   #  3 L_ear
        (215, 107),   #  4 R_ear
        (306, 190),   #  5 L_sho
        (190, 188),   #  6 R_sho
        (328, 252),   #  7 L_elb
        (155, 255),   #  8 R_elb
        (340, 308),   #  9 L_wri
        (138, 315),   # 10 R_wri
        (286, 368),   # 11 L_hip
        (210, 365),   # 12 R_hip
        (280, 525),   # 13 L_kne
        (210, 525),   # 14 R_kne
        (278, 638),   # 15 L_ank
        (205, 638),   # 16 R_ank
    ]


def pose_stand_3q():
    """Standing, 3/4 view, arms at sides."""
    return [
        (240,  80),   #  0 nose
        (255,  69),   #  1 L_eye
        (228,  68),   #  2 R_eye
        (268,  78),   #  3 L_ear
        (215,  78),   #  4 R_ear
        (308, 174),   #  5 L_sho
        (188, 172),   #  6 R_sho
        (330, 268),   #  7 L_elb
        (162, 268),   #  8 R_elb
        (342, 352),   #  9 L_wri
        (148, 356),   # 10 R_wri
        (288, 362),   # 11 L_hip
        (210, 360),   # 12 R_hip
        (284, 520),   # 13 L_kne
        (208, 520),   # 14 R_kne
        (282, 680),   # 15 L_ank
        (205, 680),   # 16 R_ank
    ]


def pose_lean_wall():
    """Leaning against wall, weight on one side, arms loosely crossed."""
    return [
        (268,  88),   #  0 nose
        (280,  77),   #  1 L_eye
        (256,  76),   #  2 R_eye
        (292,  87),   #  3 L_ear
        (244,  86),   #  4 R_ear
        (318, 182),   #  5 L_sho
        (200, 178),   #  6 R_sho
        (308, 268),   #  7 L_elb
        (185, 262),   #  8 R_elb
        (280, 338),   #  9 L_wri
        (192, 342),   # 10 R_wri
        (300, 362),   # 11 L_hip
        (220, 368),   # 12 R_hip
        (288, 520),   # 13 L_kne
        (228, 525),   # 14 R_kne
        (278, 680),   # 15 L_ank
        (232, 682),   # 16 R_ank
    ]


POSES = {
    "sit_front": (pose_sit_front(), 512, 768),
    "sit_3q":    (pose_sit_3q(),    512, 768),
    "stand_3q":  (pose_stand_3q(), 512, 768),
    "lean_wall": (pose_lean_wall(), 512, 768),
}

# ── Prompt ──────────────────────────────────────────────────────────────────

PROMPT = (
    "yukixue, 1girl, solo, mature woman, adult, "
    "very long straight hair, center part, "
    "grey eyes, (narrow eyes:1.5), thin eyes, hooded eyes, half-closed eyes, "
    "sharp features, high cheekbones, pale skin, "
    "cold expression, expressionless, aloof, detached, cool, dignified, "
    "classroom, blackboard background, indoor, soft lighting"
)

NEG = (
    "worst quality, low quality, bad anatomy, bad hands, extra fingers, "
    "missing feet, cropped, blurry, watermark, text, logo, 3d, vroid"
)

OUTDIR = Path(r"F:\bot\data\lora\test_images_v3_coco17")
OUTDIR.mkdir(parents=True, exist_ok=True)

POSE_DIR = OUTDIR / "poses"
POSE_DIR.mkdir(exist_ok=True)

# Save skeleton previews
for name, (kps, w, h) in POSES.items():
    draw_pose(kps, w, h).save(POSE_DIR / f"{name}_skeleton.png")
print(f"Skeletons saved to {POSE_DIR}")

# ── Pipeline ─────────────────────────────────────────────────────────────────

print("\nLoading ControlNet ...")
controlnet = ControlNetModel.from_pretrained(
    "lllyasviel/control_v11p_sd15_openpose",
    torch_dtype=torch.float16,
)

print("Loading CounterfeitV3 ...")
pipe = StableDiffusionControlNetPipeline.from_single_file(
    r"E:\stable-diffusion-webui\models\Stable-diffusion\Counterfeit-V3.0_fix_fp16.safetensors",
    controlnet=controlnet,
    torch_dtype=torch.float16,
    use_safetensors=True,
)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(
    pipe.scheduler.config,
    use_karras_sigmas=True,
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

print("Loading LoRA ...")
lora_path = Path(r"F:\bot\data\lora\output\yuki_lora_v3_counterfeit.safetensors")
pipe.load_lora_weights(str(lora_path.parent), weight_name=lora_path.name)
pipe.set_adapters(["default_0"], adapter_weights=[0.7])

compel = Compel(tokenizer=pipe.tokenizer, text_encoder=pipe.text_encoder)
pos_embeds = compel(PROMPT)
neg_embeds = compel(NEG)
pos_embeds, neg_embeds = compel.pad_conditioning_tensors_to_same_length(
    [pos_embeds, neg_embeds]
)

SEEDS = [42, 123]

for pose_name, (kps, w, h) in POSES.items():
    skeleton_img = draw_pose(kps, w, h)
    for seed in SEEDS:
        name = f"{pose_name}_seed{seed}"
        print(f"  [{name}]")
        out = pipe(
            prompt_embeds=pos_embeds,
            negative_prompt_embeds=neg_embeds,
            image=skeleton_img,
            num_inference_steps=30,
            guidance_scale=7.5,
            controlnet_conditioning_scale=1.0,
            clip_skip=2,
            width=w,
            height=h,
            generator=torch.Generator("cuda").manual_seed(seed),
        )
        p = OUTDIR / f"{name}.png"
        out.images[0].save(p)
        print(f"    saved: {p}")

print(f"\nDone. Output → {OUTDIR}")
