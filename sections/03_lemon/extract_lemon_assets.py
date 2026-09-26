import os
import cv2
import numpy as np

img = cv2.imread('sections/03_lemon/storyboard.png')
h, w = img.shape[:2]

out_dir = 'sections/03_lemon/assets'
os.makedirs(out_dir, exist_ok=True)

# Calculate difference from pure white
diff = 255.0 - img.astype(np.float32)
dist = np.max(diff, axis=2)

# Precise manifests with tight crops and separation of touching boundaries
manifest = [
    # --- ROW 1: Origins, Hybrid, Dr. James Lind, Scurvy Cure ---
    ("r1_01_hero_lemon", (15, 38, 320, 335)),
    ("r1_02_hybrid_citrus_dna", (335, 50, 615, 330)),
    ("r1_03_india_asia_map", (612, 30, 865, 325)),
    ("r1_04_dr_james_lind", (865, 30, 1175, 330)),
    ("r1_05_scurvy_clipboard_cure", (1175, 30, 1530, 330)),

    # --- ROW 2: Naval Scurvy, Secret Ink, Year-Round Tree ---
    ("r2_01_naval_scurvy_ship", (10, 340, 355, 655)),
    ("r2_02_lemon_squeezing_ink", (360, 355, 558, 650)),
    ("r2_03_red_arrow", (558, 475, 612, 620)),
    ("r2_04_heat_lamp_reveal_writing", (612, 355, 822, 650)),
    ("r2_05_lush_lemon_tree", (822, 348, 1085, 655)),
    ("r2_06_year_round_production_cycle", (1085, 360, 1530, 650)),

    # --- ROW 3: Detox Myth vs Truth, Vitamin C, Citric Acid, Kidney Stones ---
    ("r3_01_glass_lemon_water_liver_check", (15, 680, 226, 955)),
    ("r3_02_divider_line", (226, 685, 235, 955)),
    ("r3_03_cloudy_water_toxic_liver_cross", (240, 680, 480, 955)),
    ("r3_04_vitamin_c_glowing_emblem", (482, 690, 830, 955)),
    ("r3_05_citric_acid_molecule", (832, 685, 1075, 955)),
    ("r3_06_kidney_stones_anatomy", (1075, 695, 1295, 955)),
    ("r3_07_stone_reduction_arrow", (1295, 695, 1530, 955)),
]

metadata = {}
catalog_preview = np.full((h, w, 3), 255, dtype=np.uint8)

for idx, (name, (x1, y1, x2, y2)) in enumerate(manifest):
    crop_bgr = img[y1:y2+1, x1:x2+1].copy()
    crop_dist = dist[y1:y2+1, x1:x2+1].copy()
    
    # Generate smooth, high-fidelity organic alpha
    # Background threshold: < 8 is pure white transparent
    # Core element: > 28 is fully opaque 255
    # Smooth cubic hermite / linear transition in between for anti-aliased edge
    alpha = np.zeros_like(crop_dist, dtype=np.float32)
    ramp_mask = (crop_dist >= 6) & (crop_dist <= 26)
    alpha[crop_dist > 26] = 255.0
    alpha[ramp_mask] = ((crop_dist[ramp_mask] - 6.0) / 20.0) * 255.0
    alpha = np.clip(alpha, 0, 255).astype(np.uint8)
    
    # Tight bounding box to remove extra padding
    ys, xs = np.where(alpha > 10)
    if len(ys) == 0:
        continue
    min_y, max_y = int(np.min(ys)), int(np.max(ys))
    min_x, max_x = int(np.min(xs)), int(np.max(xs))
    
    tight_bgr = crop_bgr[min_y:max_y+1, min_x:max_x+1]
    tight_alpha = alpha[min_y:max_y+1, min_x:max_x+1]
    
    # Construct RGBA image
    rgba = np.dstack([tight_bgr, tight_alpha])
    
    # Absolute canvas position
    orig_x = x1 + min_x
    orig_y = y1 + min_y
    orig_w = max_x - min_x + 1
    orig_h = max_y - min_y + 1
    
    out_png = os.path.join(out_dir, f"{name}.png")
    cv2.imwrite(out_png, rgba)
    
    row_id = int(name[1])
    col_id = int(name.split('_')[1]) if name.split('_')[1].isdigit() else idx + 1
    
    metadata[name] = {
        "file": f"{name}.png",
        "row": row_id,
        "col": col_id,
        "orig_box": [int(orig_x), int(orig_y), int(orig_w), int(orig_h)],
        "area": int(np.sum(tight_alpha > 20))
    }
    
    # Composite onto catalog preview
    a_norm = tight_alpha.astype(np.float32) / 255.0
    for c in range(3):
        catalog_preview[orig_y:orig_y+orig_h, orig_x:orig_x+orig_w, c] = (
            tight_bgr[:, :, c] * a_norm + 
            catalog_preview[orig_y:orig_y+orig_h, orig_x:orig_x+orig_w, c] * (1.0 - a_norm)
        ).astype(np.uint8)

import json
with open(os.path.join(out_dir, "metadata.json"), "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

cv2.imwrite("sections/03_lemon/debug_crops/extracted_catalog_preview.png", catalog_preview)
print(f"Successfully extracted {len(metadata)} assets into {out_dir}!")
