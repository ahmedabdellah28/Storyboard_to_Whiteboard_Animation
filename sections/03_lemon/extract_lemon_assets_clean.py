import os
import cv2
import json
import numpy as np

img = cv2.imread('sections/03_lemon/storyboard.png')
h, w = img.shape[:2]

out_dir = 'sections/03_lemon/assets'
os.makedirs(out_dir, exist_ok=True)

# Calculate difference from pure white background
diff = 255.0 - img.astype(np.float32)
dist = np.max(diff, axis=2)

manifest = [
    # Row 1
    ("r1_01_hero_lemon", 15, 38, 325, 335, "hero_lemon"),
    ("r1_02_hybrid_citrus_dna", 335, 50, 615, 330, "hybrid_dna"),
    ("r1_03_india_asia_map", 618, 30, 895, 325, "map"),
    ("r1_04_dr_james_lind", 855, 30, 1180, 330, "lind"),
    ("r1_05_scurvy_clipboard_cure", 1180, 30, 1530, 330, "clipboard"),

    # Row 2
    ("r2_01_naval_scurvy_ship", 10, 340, 355, 655, "ship"),
    ("r2_02_lemon_squeezing_ink", 360, 355, 552, 650, "lemon_squeeze"),
    ("r2_03_red_arrow", 554, 475, 610, 620, "red_arrow"),
    ("r2_04_heat_lamp_reveal_writing", 612, 355, 822, 650, "heat_lamp"),
    ("r2_05_lush_lemon_tree", 822, 348, 1075, 655, "lemon_tree"),
    ("r2_06_year_round_production_cycle", 1065, 355, 1530, 650, "cycle"),

    # Row 3
    ("r3_01_glass_lemon_water_liver_check", 15, 680, 224, 955, "glass_check"),
    ("r3_02_divider_line", 225, 685, 235, 955, "divider"),
    ("r3_03_cloudy_water_toxic_liver_cross", 238, 680, 480, 955, "liver_cross"),
    ("r3_04_vitamin_c_glowing_emblem", 482, 690, 830, 955, "vit_c"),
    ("r3_05_citric_acid_molecule", 832, 685, 1076, 955, "citric"),
    ("r3_06_kidney_stones_anatomy", 1068, 690, 1293, 955, "kidney"),
    ("r3_07_stone_reduction_arrow", 1295, 695, 1530, 955, "stone_arrow"),
]

metadata = {}
catalog_preview = np.full((h, w, 3), 255, dtype=np.uint8)

for idx, (name, x1, y1, x2, y2, rule) in enumerate(manifest):
    crop_bgr = img[y1:y2+1, x1:x2+1].copy()
    crop_dist = dist[y1:y2+1, x1:x2+1].copy()
    ch, cw = crop_dist.shape
    
    # Custom separation logic per element
    if rule == "map":
        # Remove any green leaves from r1_02 on the left (gy >= 180 and gx <= 625)
        # Remove Dr Lind on the right (gy >= 135 and gx >= 850)
        for cy in range(ch):
            gy = y1 + cy
            for cx in range(cw):
                gx = x1 + cx
                if gy >= 180 and gx <= 626:
                    crop_dist[cy, cx] = 0.0
                if gy >= 135 and gx >= 850:
                    crop_dist[cy, cx] = 0.0
    elif rule == "lind":
        # Remove Asian continent pieces on left
        for cy in range(ch):
            gy = y1 + cy
            for cx in range(cw):
                gx = x1 + cx
                if gy < 165 and gx < 895:
                    crop_dist[cy, cx] = 0.0
                elif 165 <= gy < 185 and gx < 888:
                    crop_dist[cy, cx] = 0.0
                elif 185 <= gy < 205 and gx < 878:
                    crop_dist[cy, cx] = 0.0
                elif 205 <= gy < 225 and gx < 868:
                    crop_dist[cy, cx] = 0.0
                elif 225 <= gy < 245 and gx < 862:
                    crop_dist[cy, cx] = 0.0
                elif gy >= 245 and gx < 860:
                    crop_dist[cy, cx] = 0.0
    elif rule == "lemon_tree":
        # Lemon tree leaves vs white flower leaf
        for cy in range(ch):
            gy = y1 + cy
            for cx in range(cw):
                gx = x1 + cx
                if 420 <= gy <= 560 and gx > 1058:
                    crop_dist[cy, cx] = 0.0
    elif rule == "cycle":
        # Cycle flowers vs lemon tree leaves
        for cy in range(ch):
            gy = y1 + cy
            for cx in range(cw):
                gx = x1 + cx
                if (gy < 420 or gy > 560) and gx < 1083:
                    crop_dist[cy, cx] = 0.0
                elif 420 <= gy <= 560 and gx <= 1058:
                    crop_dist[cy, cx] = 0.0
    elif rule == "citric":
        # Molecule vs kidney
        for cy in range(ch):
            gy = y1 + cy
            for cx in range(cw):
                gx = x1 + cx
                if gy < 840 and gx > 1068:
                    crop_dist[cy, cx] = 0.0
                if gy >= 840 and gx > 1076:
                    crop_dist[cy, cx] = 0.0
    elif rule == "kidney":
        # Kidney vs molecule and stone arrow
        for cy in range(ch):
            gy = y1 + cy
            for cx in range(cw):
                gx = x1 + cx
                if gy < 840 and gx < 1069:
                    crop_dist[cy, cx] = 0.0
                if gy >= 840 and gx < 1077:
                    crop_dist[cy, cx] = 0.0
    
    # Generate smooth alpha
    alpha = np.zeros_like(crop_dist, dtype=np.float32)
    ramp_mask = (crop_dist >= 6) & (crop_dist <= 26)
    alpha[crop_dist > 26] = 255.0
    alpha[ramp_mask] = ((crop_dist[ramp_mask] - 6.0) / 20.0) * 255.0
    alpha = np.clip(alpha, 0, 255).astype(np.uint8)
    
    # Filter out tiny noise specs (keep significant components)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats((alpha > 20).astype(np.uint8))
    if num_labels > 1:
        if rule == "lind":
            # For Dr Lind, keep the single main body component
            largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
            alpha = np.where(labels == largest_label, alpha, 0).astype(np.uint8)
        else:
            # For other assets, filter out components smaller than 25 pixels
            valid_mask = np.zeros_like(alpha, dtype=bool)
            for li in range(1, num_labels):
                if stats[li, cv2.CC_STAT_AREA] >= 25:
                    valid_mask |= (labels == li)
            alpha = np.where(valid_mask, alpha, 0).astype(np.uint8)

    # Tight crop
    ys, xs = np.where(alpha > 10)
    if len(ys) == 0:
        continue
    min_y, max_y = int(np.min(ys)), int(np.max(ys))
    min_x, max_x = int(np.min(xs)), int(np.max(xs))
    
    tight_bgr = crop_bgr[min_y:max_y+1, min_x:max_x+1]
    tight_alpha = alpha[min_y:max_y+1, min_x:max_x+1].astype(np.float32)
    th, tw = tight_alpha.shape
    
    # Natural soft feathering for cuts
    if rule == "lind":
        # Bottom desk feather (12px)
        f_b = min(12, th)
        for fi in range(f_b):
            row_idx = th - f_b + fi
            tight_alpha[row_idx, :] *= (1.0 - float(fi) / float(f_b))
        # Right desk feather (below y = 170, feather rightmost 10px)
        f_r = min(10, tw)
        for fi in range(f_r):
            col_idx = tw - f_r + fi
            weight = (1.0 - float(fi) / float(f_r))
            tight_alpha[170:, col_idx] *= weight
    elif rule == "ship":
        # Bottom sea wave feather (8px)
        f_b = min(8, th)
        for fi in range(f_b):
            row_idx = th - f_b + fi
            tight_alpha[row_idx, :] *= (1.0 - float(fi) / float(f_b))
    elif rule == "clipboard":
        # Bottom shadow feather (8px)
        f_b = min(8, th)
        for fi in range(f_b):
            row_idx = th - f_b + fi
            tight_alpha[row_idx, :] *= (1.0 - float(fi) / float(f_b))

    tight_alpha = np.clip(tight_alpha, 0, 255).astype(np.uint8)
    rgba = np.dstack([tight_bgr, tight_alpha])
    
    orig_x = x1 + min_x
    orig_y = y1 + min_y
    orig_w = max_x - min_x + 1
    orig_h = max_y - min_y + 1
    
    out_png = os.path.join(out_dir, f"{name}.png")
    cv2.imwrite(out_png, rgba)
    
    row_id = int(name[1])
    col_id = idx + 1
    
    metadata[name] = {
        "file": f"{name}.png",
        "row": row_id,
        "col": col_id,
        "orig_box": [int(orig_x), int(orig_y), int(orig_w), int(orig_h)],
        "area": int(np.sum(tight_alpha > 20))
    }
    
    a_norm = tight_alpha.astype(np.float32) / 255.0
    for c in range(3):
        catalog_preview[orig_y:orig_y+orig_h, orig_x:orig_x+orig_w, c] = (
            tight_bgr[:, :, c] * a_norm + 
            catalog_preview[orig_y:orig_y+orig_h, orig_x:orig_x+orig_w, c] * (1.0 - a_norm)
        ).astype(np.uint8)

with open(os.path.join(out_dir, "metadata.json"), "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

cv2.imwrite("sections/03_lemon/preview_frames/clean_extracted_catalog.png", catalog_preview)
print(f"Successfully extracted {len(metadata)} clean assets into {out_dir}!")
