import os
import sys
import json
import cv2
import numpy as np

# Safe console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

print("=====================================================================================")
print("  🥭 ZERO-BOX CONNECTED-COMPONENTS EXTRACTION — SECTION 06: MANGO (PERFECT SILHOUETTES) 🥭")
print("=====================================================================================")

storyboard_path = "sections/06_mango/storyboard.png"
out_dir = "sections/06_mango/assets"
scratch_dir = "sections/06_mango/scratch"
os.makedirs(out_dir, exist_ok=True)
os.makedirs(scratch_dir, exist_ok=True)

img = cv2.imread(storyboard_path)
if img is None:
    raise FileNotFoundError(f"Storyboard not found: {storyboard_path}")

H, W = img.shape[:2]
print(f"Loaded storyboard: {W}x{H}")

# 1. Background detection
is_bg = (img[:, :, 0] > 238) & (img[:, :, 1] > 238) & (img[:, :, 2] > 238)
fg = (~is_bg).astype(np.uint8) * 255

# 2. Precise micro-severing
# Row 1
fg[0:270, 362:368] = 0   # r1_01 and r1_02
fg[0:270, 626:631] = 0   # r1_02 and r1_03
fg[0:270, 948:954] = 0   # r1_03 and r1_04
fg[0:270, 1231:1236] = 0 # r1_04 and r1_05
fg[258:268, :] = 0       # Row 1 and Row 2

# Row 2
fg[265:505, 356:366] = 0   # r2_01 and r2_02
fg[265:505, 822:832] = 0   # r2_02 and r2_03
fg[265:505, 1055:1058] = 0 # r2_03 and r2_04
fg[265:505, 1286:1290] = 0 # r2_04 and r2_05
fg[500:508, :] = 0       # Row 2 and Row 3

# Row 3
fg[505:745, 400:410] = 0   # r3_01 and r3_02
fg[505:745, 896:904] = 0   # r3_02 and r3_03
fg[505:745, 1195:1204] = 0 # r3_03 and r3_04
fg[740:748, :] = 0       # Row 3 and Row 4

# Row 4
fg[745:1024, 404:412] = 0  # r4_01 and r4_02
fg[745:1024, 668:675] = 0  # r4_02 and r4_03
fg[745:1024, 938:942] = 0  # r4_03 and r4_04
# Note: For r4_04 and r4_05, sever precisely at x=1224..1228 where the hanging trio leaf touches the bowl leaf
fg[745:1024, 1224:1229] = 0 # r4_04 and r4_05

kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_closed = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel)
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_closed, connectivity=8)

asset_manifest = [
    # Row 1 (King of Fruits, Origins & Culture)
    ('r1_01_hero_mango',                 (10, 10, 360, 260), "Hero ripe whole mango with diced cubes and slice"),
    ('r1_02_crowned_king_mango',         (368, 10, 626, 260), "Royal crowned mango with golden laurel wreath"),
    ('r1_03_indian_man_taj_mahal',       (631, 10, 948, 260), "Smiling Indian man smelling mango with Taj Mahal and baskets"),
    ('r1_04_ancient_map_india_myanmar',  (954, 10, 1231, 260), "Ancient parchment map of India and Myanmar highlighted in green/orange"),
    ('r1_05_buddha_temple_mango_tree',   (1236, 10, 1530, 260), "Meditating Buddha under sacred mango tree and ancient temple tower"),
    
    # Row 2 (Varieties & Textures)
    ('r2_01_ancient_scroll_manuscript',  (10, 270, 356, 500), "Ancient manuscript scroll showing mango tree and studying scholars"),
    ('r2_02_mango_varieties_grid',       (366, 270, 822, 500), "Vibrant 3x7 collection of 21 diverse mango varieties"),
    ('r2_03_creamy_texture_mango',       (832, 270, 1055, 500), "Halved mango with magnifying zoom on creamy swirl texture"),
    ('r2_04_fibrous_texture_mango',      (1058, 270, 1286, 500), "Mango with magnifying zoom on golden fibrous strands"),
    ('r2_05_super_sweet_mango_sugar',    (1290, 270, 1530, 500), "Red-blush mango with cubes and magnifying zoom on sugar sweetness"),
    
    # Row 3 (Portuguese Traders & Global Spread)
    ('r3_01_portuguese_explorer_caravel', (10, 505, 400, 740), "Portuguese explorer in velvet holding mango before Caravela ship"),
    ('r3_02_world_map_trade_routes',     (410, 505, 896, 740), "Parchment world map with red arrows radiating to Americas and Africa"),
    ('r3_03_tropical_harbor_mango_crates', (904, 505, 1195, 740), "Tropical harbor dock with ships and wooden crates of ripe mangoes"),
    ('r3_04_globe_mango_distribution',   (1204, 505, 1530, 740), "Earth globe with orbiting mangoes and global trade arcs"),
    
    # Row 4 (Nutrition & Culinary Splendor)
    ('r4_01_vitamin_c_shield_molecules', (10, 745, 404, 1024), "Glowing Vitamin C bubble with molecular lattice and mangoes"),
    ('r4_02_mango_blossoms_inflorescence', (412, 745, 668, 1024), "Mango branch with delicate blooming inflorescence and young fruitlets"),
    ('r4_03_cross_section_mango_halves', (675, 745, 938, 1024), "Whole plump mango and juicy halved fruit with pit"),
    ('r4_04_three_mangoes_trio',         (942, 745, 1224, 1024), "Trio of green, yellow, and red mangoes with fresh leaves"),
    ('r4_05_mango_smoothie_dessert_bowl', (1228, 745, 1530, 1024), "Iced mango smoothie glass and wooden bowl filled with diced mango cubes"),
]

metadata = {}
extracted_assets = []

for aid, (x1, y1, x2, y2), desc in asset_manifest:
    matched = []
    for cid in range(1, num_labels):
        cx, cy = centroids[cid]
        area = stats[cid, cv2.CC_STAT_AREA]
        if x1 <= cx <= x2 and y1 <= cy <= y2 and area > 100:
            matched.append(cid)
    
    # Build mask strictly on matched component IDs
    mask = np.isin(labels, matched).astype(np.uint8) * 255
    
    # Remove pure white background pixels
    bg_inside = (img[:, :, 0] > 242) & (img[:, :, 1] > 242) & (img[:, :, 2] > 242)
    mask[bg_inside] = 0
    
    # Edge antialiasing feathering
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
    out_file = os.path.join(out_dir, f"{aid}.png")
    cv2.imwrite(out_file, rgba)
    
    row_num = int(aid[1])
    meta = {
        "aid": aid,
        "desc": desc,
        "row": row_num,
        "storyboard_box": [int(bx), int(by), int(bw), int(bh)],
        "width": int(bw),
        "height": int(bh),
        "cids": matched,
        "file": f"{aid}.png"
    }
    metadata[aid] = meta
    extracted_assets.append((aid, rgba, meta))
    print(f"Extracted: {aid:36s} | Size: {bw:4d}x{bh:4d} | BBox: ({bx:4d}, {by:4d}, {bw:4d}, {bh:4d})")

meta_path = os.path.join(out_dir, "metadata.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)
print(f"\nMetadata saved to {meta_path} (Total: {len(metadata)} assets)")

# Visual Catalog
cat_cols = 4
cat_rows = (len(extracted_assets) + cat_cols - 1) // cat_cols
cell_w, cell_h = 420, 320
catalog = np.full((cat_rows * cell_h, cat_cols * cell_w, 3), 250, dtype=np.uint8)

for idx, (aid, asset_rgba, meta) in enumerate(extracted_assets):
    r = idx // cat_cols
    c = idx % cat_cols
    cx0 = c * cell_w
    cy0 = r * cell_h
    
    cv2.rectangle(catalog, (cx0, cy0), (cx0 + cell_w - 1, cy0 + cell_h - 1), (220, 220, 220), 1)
    
    ah, aw = asset_rgba.shape[:2]
    scale = min((cell_w - 40) / float(aw), (cell_h - 60) / float(ah))
    nw, nh = int(aw * scale), int(ah * scale)
    scaled = cv2.resize(asset_rgba, (nw, nh), interpolation=cv2.INTER_AREA)
    
    off_x = cx0 + (cell_w - nw) // 2
    off_y = cy0 + 10 + (cell_h - 60 - nh) // 2
    
    # Alpha blend onto catalog
    alpha_s = scaled[:, :, 3].astype(float) / 255.0
    for ch in range(3):
        catalog[off_y:off_y+nh, off_x:off_x+nw, ch] = (
            scaled[:, :, ch] * alpha_s + catalog[off_y:off_y+nh, off_x:off_x+nw, ch] * (1.0 - alpha_s)
        ).astype(np.uint8)
        
    lbl = f"{aid} ({aw}x{ah})"
    cv2.putText(catalog, lbl, (cx0 + 15, cy0 + cell_h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (40, 40, 40), 1, cv2.LINE_AA)

cat_path = os.path.join(scratch_dir, "clean_mango_catalog.png")
cv2.imwrite(cat_path, catalog)
print(f"Visual catalog saved to {cat_path}")
