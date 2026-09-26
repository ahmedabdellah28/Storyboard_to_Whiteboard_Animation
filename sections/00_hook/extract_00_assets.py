import os
import sys
import json
import cv2
import numpy as np

# Safe UTF-8 console output
sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "00_hook")
STORYBOARD_PATH = os.path.join(SEC_DIR, "storyboard.png")
OUT_DIR = os.path.join(SEC_DIR, "assets")
SCRATCH_DIR = os.path.join(SEC_DIR, "scratch")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(SCRATCH_DIR, exist_ok=True)

img = cv2.imread(STORYBOARD_PATH)
if img is None:
    raise FileNotFoundError(f"Cannot load {STORYBOARD_PATH}")

h, w = img.shape[:2]
print(f"Loaded storyboard: {w}x{h}")

# Step 1: Detect pure white background
is_bg = (img[:, :, 0] > 242) & (img[:, :, 1] > 242) & (img[:, :, 2] > 242)
fg_mask = (~is_bg).astype(np.uint8) * 255

# Step 2: Solidify fine strokes
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

# Step 3: Connected Components Labeling
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)
print(f"Connected components: {num_labels}")

# Define Asset Search Regions: (asset_name, (bx1, by1, bx2, by2), row_id, col_id)
# Each asset window captures all component centroids belonging to that logical element
manifest = [
    # Row 1 (y: 10 - 245)
    ("r1_01_waking_bed",         (20,   15,  300, 240), 1, 1),
    ("r1_02_sad_sitting",        (315,  35,  575, 240), 1, 2),
    ("r1_03_no_job_fly_gym",     (575,  15,  810, 240), 1, 3),
    ("r1_04_city_dawn",          (910,  20, 1195, 240), 1, 4),
    ("r1_05_crowd_safety",      (1220,  10, 1525, 245), 1, 5),

    # Row 2 (y: 260 - 475)
    ("r2_01_homeless_sidewalk",   (15, 260,  210, 475), 2, 1),
    ("r2_02_small_room",         (225, 265,  430, 475), 2, 2),
    ("r2_03_neat_apartment",     (465, 265,  685, 475), 2, 3),
    ("r2_04_comfortable_room",   (715, 265,  940, 475), 2, 4),
    ("r2_05_luxury_suite",       (975, 265, 1205, 475), 2, 5),
    ("r2_06_mansion_staff",     (1215, 265, 1525, 480), 2, 6),

    # Row 3 (y: 475 - 625)
    ("r3_01_stretching_man",      (45, 480,  280, 625), 3, 1),
    ("r3_02_timeline_24h",       (320, 475, 1140, 625), 3, 2),

    # Row 4 (y: 625 - 805)
    ("r4_01_time_clock",          (50, 625,  330, 805), 4, 1),
    ("r4_02_money_cash",         (460, 630,  660, 805), 4, 2),
    ("r4_03_health_gym",         (820, 630, 1070, 805), 4, 3),
    ("r4_04_problems_mind",     (1195, 620, 1515, 805), 4, 4),

    # Row 5 (y: 805 - 1010)
    ("r5_01_homeless_man",        (15, 820,  205, 1005), 5, 1),
    ("r5_02_billionaire_car",    (150, 805,  770, 1010), 5, 2),
    ("r5_03_thinking_question",  (840, 810, 1215, 1010), 5, 3),
    ("r5_04_rising_chart",      (1230, 815, 1520, 1005), 5, 4),
]

metadata = {}
catalog_chips = []

print("\nExtracting assets along natural organic silhouettes (على حدود العنصر):")
for name, (bx1, by1, bx2, by2), row_id, col_id in manifest:
    # Find all component labels with centroids in the search window
    matched_cids = []
    for cid in range(1, num_labels):
        cx, cy = centroids[cid]
        area = stats[cid, cv2.CC_STAT_AREA]
        if bx1 <= cx <= bx2 and by1 <= cy <= by2 and area >= 15:
            matched_cids.append(cid)

    if not matched_cids:
        print(f"  ⚠️ Warning: No components matched for {name} in window ({bx1},{by1},{bx2},{by2})")
        continue

    # Create component mask
    comp_mask = np.isin(labels, matched_cids).astype(np.uint8) * 255
    ys, xs = np.where(comp_mask > 0)
    if len(xs) == 0 or len(ys) == 0:
        continue

    x1, x2 = int(np.min(xs)), int(np.max(xs))
    y1, y2 = int(np.min(ys)), int(np.max(ys))

    # Add 1px padding
    x1 = max(0, x1 - 1)
    y1 = max(0, y1 - 1)
    x2 = min(w - 1, x2 + 1)
    y2 = min(h - 1, y2 + 1)

    crop_bgr = img[y1:y2+1, x1:x2+1].copy()
    crop_mask = comp_mask[y1:y2+1, x1:x2+1]

    # Smooth alpha feathering on contour edges
    alpha = np.where(crop_mask > 0, 255, 0).astype(np.uint8)
    # Anti-alias mask edges slightly
    alpha_soft = cv2.GaussianBlur(alpha, (3, 3), 0)
    alpha_final = np.where(crop_mask > 0, np.maximum(alpha, alpha_soft), 0).astype(np.uint8)

    rgba = np.dstack([crop_bgr, alpha_final])
    out_png = os.path.join(OUT_DIR, f"{name}.png")
    cv2.imwrite(out_png, rgba)

    cw = int(x2 - x1 + 1)
    ch = int(y2 - y1 + 1)
    pix_area = int(np.sum(alpha_final > 0))

    metadata[name] = {
        "file": f"{name}.png",
        "row": row_id,
        "col": col_id,
        "orig_box": [x1, y1, cw, ch],
        "orig_size": [cw, ch],
        "area": pix_area
    }
    print(f"  ✅ Extracted: {name:25s} | Box: [{x1:4d}, {y1:4d}, {cw:4d}x{ch:4d}] | Pixels: {pix_area:6d}")

# Save metadata
meta_path = os.path.join(OUT_DIR, "metadata.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)
print(f"\nMetadata saved: {meta_path} ({len(metadata)} assets)")

# Generate Visual Catalog Image (checkerboard background)
cat_cols = 5
cat_rows = (len(manifest) + cat_cols - 1) // cat_cols
tile_w, tile_h = 320, 220
catalog = np.full((cat_rows * tile_h, cat_cols * tile_w, 3), 235, dtype=np.uint8)

for idx, (name, _, _, _) in enumerate(manifest):
    if name not in metadata:
        continue
    r = idx // cat_cols
    c = idx % cat_cols
    tx1, ty1 = c * tile_w, r * tile_h

    # Draw soft checkerboard tile
    for cy in range(ty1, ty1 + tile_h, 20):
        for cx in range(tx1, tx1 + tile_w, 20):
            if ((cx - tx1) // 20 + (cy - ty1) // 20) % 2 == 0:
                catalog[cy:min(cy+20, ty1+tile_h), cx:min(cx+20, tx1+tile_w)] = (245, 245, 245)
            else:
                catalog[cy:min(cy+20, ty1+tile_h), cx:min(cx+20, tx1+tile_w)] = (220, 220, 220)

    asset = cv2.imread(os.path.join(OUT_DIR, f"{name}.png"), cv2.IMREAD_UNCHANGED)
    if asset is not None:
        ah, aw = asset.shape[:2]
        scale = min((tile_w - 40) / float(aw), (tile_h - 50) / float(ah))
        nw, nh = max(1, int(aw * scale)), max(1, int(ah * scale))
        resized = cv2.resize(asset, (nw, nh), interpolation=cv2.INTER_AREA)

        ox = tx1 + (tile_w - nw) // 2
        oy = ty1 + (tile_h - 30 - nh) // 2 + 5

        # Alpha blend onto catalog
        res_bgr = resized[:, :, :3]
        res_a = resized[:, :, 3] / 255.0
        bg_roi = catalog[oy:oy+nh, ox:ox+nw].astype(float)
        composite = bg_roi * (1.0 - res_a[:, :, None]) + res_bgr.astype(float) * res_a[:, :, None]
        catalog[oy:oy+nh, ox:ox+nw] = composite.astype(np.uint8)

        # Label
        cv2.putText(catalog, name, (tx1 + 10, ty1 + tile_h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 40, 40), 1)

catalog_path = os.path.join(SCRATCH_DIR, "extraction_catalog.png")
cv2.imwrite(catalog_path, catalog)
print(f"Visual catalog saved to: {catalog_path}")
