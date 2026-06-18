"""
生成 LoRA 训练数据：多角度渲染 VRM + 自动生成 caption。
输出到 F:/bot/data/yuki_lora/img/20_yukixue/
"""
import sys
import os

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..', 'core')))

from vrm_render import render_vrm

OUT_DIR    = r"F:\bot\data\yuki_lora\img\20_yukixue"
TRIGGER    = "yukixue"
BASE_TAGS  = "1girl, solo, white hair, long hair, purple eyes, school uniform, full body, standing"
BUST_TAGS  = "1girl, solo, white hair, long hair, purple eyes, school uniform, upper body, portrait"

os.makedirs(OUT_DIR, exist_ok=True)

# Full-body: 8 angles 0°,45°,90°,135°,180°,225°,270°,315°
full_angles = [i * 45 for i in range(8)]
# Bust: front + two 3/4 views
bust_angles = [0, 30, 330]

generated = []

print("[gen_data] Generating full-body shots...")
for angle in full_angles:
    stem = f"yuki_full_a{int(angle):03d}"
    png  = os.path.join(OUT_DIR, f"{stem}.png")
    txt  = os.path.join(OUT_DIR, f"{stem}.txt")
    ok = render_vrm(png, angle=angle, bust=False, width=512, height=768)
    if ok:
        caption = f"{TRIGGER}, {BASE_TAGS}"
        if angle != 0:
            caption += f", {'side view' if angle in (90,270) else 'from behind' if angle == 180 else '3/4 view'}"
        with open(txt, "w", encoding="utf-8") as f:
            f.write(caption)
        generated.append(png)
        print(f"  OK {stem}")
    else:
        print(f"  FAIL {stem}")

print("[gen_data] Generating bust shots...")
for angle in bust_angles:
    stem = f"yuki_bust_a{int(angle):03d}"
    png  = os.path.join(OUT_DIR, f"{stem}.png")
    txt  = os.path.join(OUT_DIR, f"{stem}.txt")
    ok = render_vrm(png, angle=angle, bust=True, width=512, height=512)
    if ok:
        caption = f"{TRIGGER}, {BUST_TAGS}"
        if angle != 0:
            caption += ", 3/4 view"
        with open(txt, "w", encoding="utf-8") as f:
            f.write(caption)
        generated.append(png)
        print(f"  OK {stem}")
    else:
        print(f"  FAIL {stem}")

print(f"\n[gen_data] Done: {len(generated)} images → {OUT_DIR}")
