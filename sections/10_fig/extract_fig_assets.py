import os
import sys
import json
import cv2
import numpy as np

ROOT_DIR = r"E:\image_to_animate"
sec_dir = os.path.join(ROOT_DIR, "sections/10_fig")
assets_dir = os.path.join(sec_dir, "assets")
scratch_dir = os.path.join(sec_dir, "scratch")
os.makedirs(assets_dir, exist_ok=True)
os.makedirs(scratch_dir, exist_ok=True)

storyboard_path = os.path.join(sec_dir, "storyboard.png")
img = cv2.imread(storyboard_path)
H, W = img.shape[:2]

severing = [
    # Between top-left hero and bottom-left magnified flowers
    (265, 272, 5, 340),
    # Between gatherers and Jordan valley village
    (5, 275, 555, 558),
    # Between village and botanical syconium below
    (270, 276, 340, 850),
    # Between wheat stalk and comparison fig
    (80, 255, 1320, 1324),
    # Between wasp arrow and interior fig
    (540, 760, 583, 587),
    # Between varieties lineup and sapling
    (780, 990, 676, 682),
    # Between sapling and mature tree
    (780, 990, 868, 872),
    # Between mature tree and ripe branch
    (780, 990, 1208, 1215),
]

is_bg = (img[:, :, 0] > 235) & (img[:, :, 1] > 235) & (img[:, :, 2] > 235)
fg = (~is_bg).astype(np.uint8) * 255

for y1, y2, x1, x2 in severing:
    fg[y1:y2, x1:x2] = 0

kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_closed = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel)
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_closed, connectivity=8)

manifest = [
    # Row 1: Ancient History & Prehistoric Origins
    ("r1_01_fig_hero_fresh_cut", (5, 5, 340, 268), "Fresh purple whole fig with ripe cut half and green fig leaf", 1),
    ("r1_02_ancient_prehistoric_gatherers", (338, 5, 556, 272), "Prehistoric human hunter-gatherers harvesting wild figs", 1),
    ("r1_03_jordan_valley_neolithic_village", (556, 5, 850, 272), "Ancient Neolithic settlement in Jordan Valley with early fig cultivation", 1),
    ("r1_04_ancient_stone_carvings_fig", (855, 15, 1190, 275), "Two ancient stone relief carvings depicting fig leaf, fruit, and tree", 1),
    ("r1_05_fig_older_than_grains_comparison", (1190, 5, 1525, 255), "Comparison showing fig cultivation is older than wheat and grains", 1),

    # Row 2: Inverted Inflorescence (Syconium) & Seeds
    ("r2_01_fig_magnified_internal_flowers", (5, 268, 340, 525), "Cross-section of fig with loupe showing internal inverted flowers", 2),
    ("r2_02_botanical_syconium_florets_loupe", (340, 272, 645, 520), "Botanical illustration of fig syconium with internal male and female florets", 2),
    ("r2_03_crunchy_seeds_florets_detail", (645, 285, 910, 515), "Detailed view of the crunchy seeds and microscopic floret structures", 2),
    ("r2_04_trio_fresh_figs_leaf", (920, 280, 1225, 520), "Three ripe figs: green Kadota, dark purple, and cut red half with leaf", 2),
    ("r2_05_dried_figs_platter", (1230, 275, 1515, 520), "Dried figs whole and cut open showing concentrated golden seed pulp", 2),

    # Row 3: Fig Wasp Symbiosis & Modern Cultivation
    ("r3_01_fig_ostiole_wasp_entering", (5, 535, 340, 775), "Extreme close-up of fig ostiole eye with wasp entering inside", 3),
    ("r3_02_fig_wasp_illustrated", (345, 540, 584, 750), "Illustrated specialized fig pollinator wasp (Blastophaga psenes)", 3),
    ("r3_03_wasp_inside_fig_interior", (585, 530, 845, 770), "Cross section of fig showing wasp inside pollinating the internal florets", 3),
    ("r3_04_fig_enzymes_breakdown_diagram", (860, 520, 1235, 760), "Scientific diagram of fig ficin enzymes breaking down organic material", 3),
    ("r3_05_commercial_fig_no_wasp_sign", (1185, 535, 1525, 775), "Commercial fig branch with prohibition sign showing parthenocarpic fruit", 3),

    # Row 4: Varieties, Tree & Harvest
    ("r4_01_fig_varieties_lineup", (15, 780, 676, 990), "Lineup of 5 fig varieties showing black, purple, green, yellow, and red interiors", 4),
    ("r4_02_fig_sapling_soil", (680, 785, 868, 990), "Fig sapling sprout growing from rich fertile soil mound", 4),
    ("r4_03_mature_fruiting_fig_tree", (870, 755, 1208, 992), "Majestic mature fig tree with spreading canopy laden with ripe figs", 4),
    ("r4_04_fig_branch_ripe_unripe", (1215, 780, 1525, 995), "Fig tree branch with ripe purple fig and developing green figs", 4),
]

metadata = {}
catalog_crops = []

print("Extracting clean Zero-Box assets for Section 10 Fig (التين)...")

for aid, (x1, y1, x2, y2), desc, row_num in manifest:
    # Match components inside box
    matched = []
    for cid in range(1, num_labels):
        cx, cy = centroids[cid]
        area = stats[cid, cv2.CC_STAT_AREA]
        if x1 <= cx <= x2 and y1 <= cy <= y2 and area > 100:
            matched.append(cid)

    if aid == "r1_05_fig_older_than_grains_comparison":
        mask = np.zeros((H, W), dtype=np.uint8)
        raw_fg = ((img[:, :, 0] <= 240) | (img[:, :, 1] <= 240) | (img[:, :, 2] <= 240)).astype(np.uint8) * 255
        mask[y1:y2, x1:x2] = raw_fg[y1:y2, x1:x2]
    else:
        mask = np.isin(labels, matched).astype(np.uint8) * 255
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
    print(f"  Extracted: {aid:42s} | Size: {bw:4d}x{bh:4d} | Row: {row_num}")

meta_path = os.path.join(assets_dir, "metadata.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

# Build Visual Catalog Grid
cat_w, cat_h = 1920, 1080
catalog = np.full((cat_h, cat_w, 3), 248, dtype=np.uint8)

cv2.putText(catalog, "SECTION 10: FIG (التين) - ZERO-BOX CLEAN ASSETS CATALOG", (50, 45),
            cv2.FONT_HERSHEY_DUPLEX, 0.9, (40, 40, 40), 2)
cv2.putText(catalog, f"Total Extracted Assets: {len(catalog_crops)} | Pure Transparent Silhouettes", (50, 80),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 80, 20), 1)

cols, rows = 5, 4
cell_w, cell_h = cat_w // cols, (cat_h - 100) // rows

for idx, (aid, rgba, r_num) in enumerate(catalog_crops):
    c_idx = idx % cols
    r_idx = idx // cols
    cx_box = c_idx * cell_w
    cy_box = 100 + r_idx * cell_h

    cv2.rectangle(catalog, (cx_box + 8, cy_box + 8), (cx_box + cell_w - 8, cy_box + cell_h - 8), (255, 255, 255), -1)
    cv2.rectangle(catalog, (cx_box + 8, cy_box + 8), (cx_box + cell_w - 8, cy_box + cell_h - 8), (220, 220, 220), 1)

    ah, aw = rgba.shape[:2]
    max_sw, max_sh = cell_w - 30, cell_h - 50
    scale = min(max_sw / float(aw), max_sh / float(ah))
    nw, nh = int(aw * scale), int(ah * scale)
    scaled_rgba = cv2.resize(rgba, (nw, nh), interpolation=cv2.INTER_AREA)

    px = cx_box + (cell_w - nw) // 2
    py = cy_box + 15 + (cell_h - 50 - nh) // 2

    fg_rgb = scaled_rgba[:, :, :3]
    fg_a = scaled_rgba[:, :, 3].astype(np.float32) / 255.0
    fg_a_3d = fg_a[:, :, np.newaxis]
    roi = catalog[py:py+nh, px:px+nw].astype(np.float32)
    blended = fg_rgb.astype(np.float32) * fg_a_3d + roi * (1.0 - fg_a_3d)
    catalog[py:py+nh, px:px+nw] = blended.astype(np.uint8)

    cv2.putText(catalog, f"R{r_num}: {aid}", (cx_box + 12, cy_box + cell_h - 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (50, 50, 50), 1)

cat_out = os.path.join(scratch_dir, "clean_assets_catalog.png")
cv2.imwrite(cat_out, catalog)
print(f"\nCatalog saved: {cat_out}")
