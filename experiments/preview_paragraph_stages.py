import os
import sys
import json
import cv2
import numpy as np

# Verify the layout of the 5 Paragraph Stages on clean 1920x1080 frames
assets_dir = "project_content/kiwi_assets"
metadata_path = os.path.join(assets_dir, "metadata.json")
with open(metadata_path, "r", encoding="utf-8") as mf:
    metadata = json.load(mf)

assets = {}
for aid, info in metadata.items():
    p = os.path.join(assets_dir, info["file"])
    img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if img is not None:
        assets[aid] = img

os.makedirs("output_animations/stage_previews", exist_ok=True)

# Define 16:9 stage layout for each paragraph
stages_layout = {
    1: [
        ('r1_01', 80, 260, 480, 400),
        ('r1_02', 450, 60, 600, 420),
        ('r1_03', 750, 260, 400, 500),
        ('r1_04', 1100, 240, 320, 420),
        ('r1_05', 1320, 360, 340, 280),
        ('r1_06', 1520, 260, 360, 380),
    ],
    2: [
        ('r2_01', 80, 250, 400, 500),
        ('r2_02', 400, 150, 320, 420),
        ('r2_03', 650, 320, 260, 250),
        ('r2_04', 820, 260, 250, 280),
        ('r2_05', 1000, 300, 280, 350),
        ('r2_06', 1180, 280, 300, 370),
        ('r2_07', 1380, 220, 450, 450),
        ('r2_08', 1580, 340, 300, 220),
    ],
    3: [
        ('r3_01', 120, 280, 400, 360),
        ('r3_03', 480, 280, 360, 350),
        ('r3_04', 780, 240, 460, 340),
        ('r3_05', 1150, 220, 380, 380),
        ('r3_06', 1450, 280, 420, 360),
    ],
    4: [
        ('r4_01', 100, 280, 380, 350),
        ('r4_02', 450, 250, 360, 380),
        ('r4_03', 750, 290, 300, 320),
        ('r4_04', 980, 260, 280, 380),
        ('r4_05', 1200, 300, 320, 280),
        ('r4_06', 1420, 280, 300, 320),
        ('r4_07', 1620, 280, 300, 320),
    ],
    5: [
        ('r5_01', 100, 240, 400, 520),
        ('r5_02', 450, 290, 380, 340),
        ('r5_03', 750, 260, 380, 380),
        ('r5_04', 1050, 240, 400, 360),
        ('r5_05', 1350, 240, 360, 350),
        ('r5_06', 1580, 260, 360, 350),
    ]
}

def blend_sprite(frame, sprite, x, y, w, h):
    resized = cv2.resize(sprite, (w, h), interpolation=cv2.INTER_AREA)
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(1920, x + w), min(1080, y + h)
    if x2 <= x1 or y2 <= y1:
        return
    crop = resized[y1-y:y2-y, x1-x:x2-x]
    alpha = (crop[:, :, 3].astype(np.float32) / 255.0)
    alpha_3 = cv2.merge([alpha, alpha, alpha])
    frame[y1:y2, x1:x2] = (crop[:, :, :3] * alpha_3 + frame[y1:y2, x1:x2] * (1.0 - alpha_3)).astype(np.uint8)

for st_idx, elems in stages_layout.items():
    frame = np.full((1080, 1920, 3), 255, dtype=np.uint8)
    for aid, x, y, w, h in elems:
        if aid in assets:
            blend_sprite(frame, assets[aid], x, y, w, h)
    out_p = f"output_animations/stage_previews/stage_{st_idx:02d}.jpg"
    cv2.imwrite(out_p, frame)
    print(f"Saved: {out_p}")

print("All 5 Paragraph Stage Previews Generated!")
