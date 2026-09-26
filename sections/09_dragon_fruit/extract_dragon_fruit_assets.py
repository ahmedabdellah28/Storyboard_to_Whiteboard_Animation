import os
import sys
import json
import cv2
import numpy as np

ROOT_DIR = r"E:\image_to_animate"
sec_dir = os.path.join(ROOT_DIR, "sections/09_dragon_fruit")
assets_dir = os.path.join(sec_dir, "assets")
scratch_dir = os.path.join(sec_dir, "scratch")
os.makedirs(assets_dir, exist_ok=True)
os.makedirs(scratch_dir, exist_ok=True)

storyboard_path = os.path.join(sec_dir, "storyboard.png")
img = cv2.imread(storyboard_path)
H, W = img.shape[:2]

# Severing cuts to cleanly detach touching objects
severing = [
    # Between cactus tree and flower stem at x=714
    (5, 385, 712, 716),
    # Between smoothie bowl and glass mint leaf at x=334
    (700, 1005, 333, 335),
    # Between varieties halves: x=718 and x=878
    (400, 650, 717, 720),
    (400, 650, 876, 879),
    # Between slices and cactus branch at x=1215
    (690, 1000, 1214, 1217),
    # Between plate and slices at x=912
    (740, 1000, 911, 914),
]

# Detect white background
is_bg = (img[:, :, 0] > 235) & (img[:, :, 1] > 235) & (img[:, :, 2] > 235)
fg = (~is_bg).astype(np.uint8) * 255

for y1, y2, x1, x2 in severing:
    fg[y1:y2, x1:x2] = 0

kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_closed = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel)
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_closed, connectivity=8)

manifest = [
    # Row 1
    ("r1_01_dragon_fruit_white_flesh_hero", (10, 5, 425, 400), "Hero dragon fruit with white flesh cross section and whole fruit", 1),
    ("r1_02_dragon_fruit_cactus_tree", (350, 5, 714, 385), "Dragon fruit cactus tree bush with ripe red hanging fruits", 1),
    ("r1_03_blooming_night_flower_stem", (714, 5, 980, 385), "Green cactus rib stem with giant yellow-white blooming night flower", 1),
    ("r1_04_dragon_fruit_red_flesh_hero", (1285, 30, 1530, 380), "Red-fleshed dragon fruit pitaya roja whole and slices", 1),

    # Row 2
    ("r2_01_world_migration_map", (960, 70, 1350, 310), "World map with migration arrow from Central America to Southeast Asia", 2),
    ("r2_02_cactus_branch_harvest", (1215, 695, 1530, 1015), "Vertical cactus branch heavy with ripe dragon fruits ready for harvest", 2),

    # Row 3
    ("r3_01_vietnam_plantation_landscape", (10, 395, 560, 705), "Vietnam dragon fruit plantation rows with mountain backdrop and sign", 3),
    ("r3_02a_white_flesh_half", (565, 400, 718, 670), "Pitaya half with white flesh and black seeds (لب أبيض)", 3),
    ("r3_02b_red_flesh_half", (718, 400, 877, 670), "Pitaya half with deep red flesh (لب أحمر)", 3),
    ("r3_02c_yellow_flesh_half", (877, 400, 1025, 670), "Pitaya half with yellow peel and white-yellow flesh (لب أصفر)", 3),
    ("r3_02_three_varieties_lineup", (565, 400, 1025, 670), "Trio of three pitaya varieties side-by-side: white, red, yellow", 3),

    # Row 4
    ("r4_01_nutritional_benefits_composition", (1020, 375, 1520, 695), "Dragon fruit with 4 nutritional badges (antioxidants, vit C, fiber, vit B)", 4),
    ("r4_02_pitaya_smoothie_bowl", (10, 705, 334, 1005), "Wooden bowl with vibrant pink pitaya smoothie, bananas, blueberries, granola", 4),
    ("r4_03_smoothie_tall_glass_straw", (334, 705, 560, 995), "Tall glass dragon fruit smoothie with striped straw and fresh mint", 4),
    ("r4_04_cubed_dragon_fruit_plate", (560, 740, 915, 1005), "Plate of white and red checkered dragon fruit cubes with mint garnish", 4),
    ("r4_05_dragon_fruit_slices_composition", (912, 690, 1215, 995), "Dragon fruit with triangular slices and cut wedges", 4),
]

metadata = {}
catalog_crops = []

print("Extracting clean Zero-Box assets for Section 09 Dragon Fruit...")

for aid, (x1, y1, x2, y2), desc, row_num in manifest:
    # Match components inside box
    matched = []
    for cid in range(1, num_labels):
        cx, cy = centroids[cid]
        area = stats[cid, cv2.CC_STAT_AREA]
        if x1 <= cx <= x2 and y1 <= cy <= y2 and area > 100:
            matched.append(cid)

    # For trio lineup or special boxes without severing cut
    if aid == "r3_02_three_varieties_lineup":
        # Match all components in x1..x2, y1..y2
        mask = np.zeros((H, W), dtype=np.uint8)
        raw_fg = ((img[:, :, 0] <= 240) | (img[:, :, 1] <= 240) | (img[:, :, 2] <= 240)).astype(np.uint8) * 255
        mask[y1:y2, x1:x2] = raw_fg[y1:y2, x1:x2]
    elif aid == "r2_01_world_migration_map":
        mask = np.zeros((H, W), dtype=np.uint8)
        raw_fg = ((img[:, :, 0] <= 240) | (img[:, :, 1] <= 240) | (img[:, :, 2] <= 240)).astype(np.uint8) * 255
        mask[y1:y2, x1:x2] = raw_fg[y1:y2, x1:x2]
    else:
        mask = np.isin(labels, matched).astype(np.uint8) * 255
        # Exclude background pixels
        bg_in = (img[:, :, 0] > 242) & (img[:, :, 1] > 242) & (img[:, :, 2] > 242)
        mask[bg_in] = 0

    mask_blur = cv2.GaussianBlur(mask, (3, 3), 0.5)
    alpha = np.clip(mask_blur.astype(np.float32) / 255.0 * 255.0, 0, 255).astype(np.uint8)

    coords = cv2.findNonZero(alpha)
    if coords is None:
        print(f"⚠️ Warning: No pixels found for {aid}!")
        continue

    bx, by, bw, bh = cv2.boundingRect(coords)
    crop_bgr = img[by:by+bh, bx:bx+bw]
    crop_alpha = alpha[by:by+bh, bx:bx+bw]

    rgba = cv2.merge([crop_bgr[:, :, 0], crop_bgr[:, :, 1], crop_bgr[:, :, 2], crop_alpha])
    out_file = os.path.join(assets_dir, f"{aid}.png")
    cv2.imwrite(out_file, rgba)

    meta = {
        "aid": aid,
        "desc": desc,
        "row": row_num,
        "storyboard_box": [int(bx), int(by), int(bw), int(bh)],
        "width": int(bw),
        "height": int(bh),
        "file": f"{aid}.png"
    }
    metadata[aid] = meta
    catalog_crops.append((aid, rgba, row_num))
    print(f"  Extracted: {aid:40s} | Size: {bw:4d}x{bh:4d} | Row: {row_num}")

# Save metadata.json
meta_path = os.path.join(assets_dir, "metadata.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

# Build Visual Catalog Grid
cat_w, cat_h = 1920, 1080
catalog = np.full((cat_h, cat_w, 3), 248, dtype=np.uint8)

# Title banner
cv2.putText(catalog, "SECTION 09: DRAGON FRUIT (PITAYA) - ZERO-BOX CLEAN ASSETS CATALOG", (50, 45),
            cv2.FONT_HERSHEY_DUPLEX, 0.9, (40, 40, 40), 2)
cv2.putText(catalog, f"Total Extracted Assets: {len(catalog_crops)} | Pure Transparent Silhouettes", (50, 80),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 80, 20), 1)

# Grid layout (4 cols x 4 rows)
cols, rows = 4, 4
cell_w, cell_h = cat_w // cols, (cat_h - 100) // rows

for idx, (aid, rgba, r_num) in enumerate(catalog_crops):
    c_idx = idx % cols
    r_idx = idx // cols
    cx_box = c_idx * cell_w
    cy_box = 100 + r_idx * cell_h

    # Card background
    cv2.rectangle(catalog, (cx_box + 10, cy_box + 10), (cx_box + cell_w - 10, cy_box + cell_h - 10), (255, 255, 255), -1)
    cv2.rectangle(catalog, (cx_box + 10, cy_box + 10), (cx_box + cell_w - 10, cy_box + cell_h - 10), (220, 220, 220), 1)

    # Scale asset to fit card
    ah, aw = rgba.shape[:2]
    max_sw, max_sh = cell_w - 40, cell_h - 60
    scale = min(max_sw / float(aw), max_sh / float(ah))
    nw, nh = int(aw * scale), int(ah * scale)
    scaled_rgba = cv2.resize(rgba, (nw, nh), interpolation=cv2.INTER_AREA)

    px = cx_box + (cell_w - nw) // 2
    py = cy_box + 20 + (cell_h - 60 - nh) // 2

    # Blend onto white card
    fg_rgb = scaled_rgba[:, :, :3]
    fg_a = scaled_rgba[:, :, 3].astype(np.float32) / 255.0
    fg_a_3d = fg_a[:, :, np.newaxis]
    roi = catalog[py:py+nh, px:px+nw].astype(np.float32)
    blended = fg_rgb.astype(np.float32) * fg_a_3d + roi * (1.0 - fg_a_3d)
    catalog[py:py+nh, px:px+nw] = blended.astype(np.uint8)

    # Label
    cv2.putText(catalog, f"R{r_num}: {aid}", (cx_box + 15, cy_box + cell_h - 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (50, 50, 50), 1)

cat_out = os.path.join(scratch_dir, "clean_assets_catalog.png")
cv2.imwrite(cat_out, catalog)
print(f"\nCatalog saved: {cat_out}")
