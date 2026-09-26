import os
import cv2
import json
import numpy as np

img_path = 'sections/04_pineapple/storyboard.png'
bgr = cv2.imread(img_path)
if bgr is None:
    raise FileNotFoundError(f"Storyboard not found at {img_path}")

h, w = bgr.shape[:2]
out_dir = 'sections/04_pineapple/assets'
os.makedirs(out_dir, exist_ok=True)

# 1. Pure white background mask
is_bg = (bgr[:, :, 0] > 245) & (bgr[:, :, 1] > 245) & (bgr[:, :, 2] > 245)
fg_mask = (~is_bg).astype(np.uint8) * 255

# 2. Morphological closure (keep thin pencil strokes solid)
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

# 3. Micro-severing contact bridges
# In Row 2: Sever contact between admiring guests (red dress) and strutting gentleman (blue coat)
# Using color discrimination in the overlap window [x: 450..475, y: 340..490]
for y in range(340, 490):
    for x in range(450, 475):
        b, g, r = int(bgr[y, x, 0]), int(bgr[y, x, 1]), int(bgr[y, x, 2])
        # If boundary between red dress and blue coat
        if abs(b - r) < 20 and (r > 80 or b > 80):
            fg_clean[y, x] = 0

# 4. Connected components labeling
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)
print(f"Total connected components: {num_labels}")

# 5. Semantic Asset Manifest (Search boxes for component centroids)
# Each entry: (asset_id, search_box, min_area)
manifest = [
    # === ROW 1 ===
    ("r1_01_hero_pineapple",                (10,   5,  300, 315), 1000),
    ("r1_02_south_america_map",             (300, 15,  530, 315), 1000),
    ("r1_03_pineapple_comparison",          (545, 10,  705, 315), 1000),
    ("r1_04_double_arrow",                  (685, 175, 755, 230),  500),
    ("r1_05_pine_cone",                     (755, 125, 880, 300), 1000),
    ("r1_06_wealthy_gentleman_england_gold", (890,   5, 1535, 315), 2000),

    # === ROW 2 ===
    ("r2_01_butler_velvet_pillow",          (15,  315, 290, 565), 1000),
    ("r2_02_admiring_guests",               (290, 315, 465, 565), 1000),
    ("r2_03_gentleman_strutting",           (465, 315, 605, 575), 1000),
    ("r2_04_lavish_banquet_table",          (605, 315, 1010, 560), 2000),
    ("r2_05_rich_man_throwing",             (1010, 315, 1310, 565), 2000),
    ("r2_06_trash_rotting_pineapple",       (1300, 335, 1530, 565), 1000),

    # === ROW 3 ===
    ("r3_01_cross_section_cells",           (10,  555, 295, 775), 2000),
    ("r3_02_protein_molecule",              (295, 575, 500, 770), 2000),
    ("r3_03_blue_arrow",                    (490, 650, 565, 715),  500),
    ("r3_04_broken_protein_fragments",      (560, 595, 700, 770),  300),
    ("r3_05_meat_tenderizer_bromelain",     (695, 555, 1015, 765), 300),
    ("r3_06_stinging_tongue",               (1015, 560, 1260, 770), 300),
    ("r3_07_man_touching_stinging_tongue",  (1250, 555, 1530, 775), 2000),

    # === ROW 4 ===
    ("r4_01_pineapple_slice_dripping",      (20,  765, 280, 995), 300),
    ("r4_02_red_curved_arrow",              (230, 780, 390, 870),  500),
    ("r4_03_mouth_eating_pineapple",        (335, 760, 670, 1005), 2000),
    ("r4_04_carnivorous_monster_pineapple", (815, 745, 1115, 1010), 300),
    ("r4_05_terrified_man_running",         (1100, 760, 1525, 1010), 2000),
]

metadata = {}
catalog_preview = np.full((h, w, 3), 255, dtype=np.uint8)

for idx, (name, (bx1, by1, bx2, by2), min_a) in enumerate(manifest):
    # Match components whose centroid falls inside the search box
    matched_cids = []
    for cid in range(1, num_labels):
        cx, cy = centroids[cid]
        area = stats[cid, cv2.CC_STAT_AREA]
        if bx1 <= cx <= bx2 and by1 <= cy <= by2 and area >= min_a:
            matched_cids.append(cid)
            
    if not matched_cids:
        print(f"WARNING: No components found for {name} in box ({bx1},{by1},{bx2},{by2})")
        continue

    # 6. Exact silhouette mask
    comp_mask = np.isin(labels, matched_cids).astype(np.uint8) * 255
    ys, xs = np.where(comp_mask > 0)
    x1, x2 = int(np.min(xs)), int(np.max(xs))
    y1, y2 = int(np.min(ys)), int(np.max(ys))

    crop_bgr = bgr[y1:y2+1, x1:x2+1].copy()
    crop_mask = comp_mask[y1:y2+1, x1:x2+1]

    # Binary alpha strictly on the natural silhouette contour (Zero Boxes)
    alpha = np.where(crop_mask > 0, 255, 0).astype(np.uint8)
    rgba = np.dstack([crop_bgr, alpha])

    out_file = os.path.join(out_dir, f"{name}.png")
    cv2.imwrite(out_file, rgba)

    row_id = int(name[1])
    col_id = idx + 1
    orig_w = x2 - x1 + 1
    orig_h = y2 - y1 + 1

    metadata[name] = {
        "file": f"{name}.png",
        "row": row_id,
        "col": col_id,
        "orig_box": [int(x1), int(y1), int(orig_w), int(orig_h)],
        "area": int(np.sum(alpha > 0))
    }

    # Add to visual inspection catalog
    a_norm = alpha.astype(np.float32) / 255.0
    for c in range(3):
        catalog_preview[y1:y1+orig_h, x1:x1+orig_w, c] = (
            crop_bgr[:, :, c] * a_norm +
            catalog_preview[y1:y1+orig_h, x1:x1+orig_w, c] * (1.0 - a_norm)
        ).astype(np.uint8)

    print(f"Extracted {name:38s} | Box=[X={x1:4d}, Y={y1:4d}, W={orig_w:3d}, H={orig_h:3d}] | Area={metadata[name]['area']:6d}")

with open(os.path.join(out_dir, "metadata.json"), "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

cv2.imwrite("sections/04_pineapple/scratch/clean_extracted_catalog.png", catalog_preview)
print(f"\nSuccessfully extracted all {len(metadata)} clean zero-box assets into {out_dir}/!")
