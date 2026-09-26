import os
import sys
import json
import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "01_homeless")
STORYBOARD_PATH = os.path.join(SEC_DIR, "storyboard.png")
OUT_DIR = os.path.join(SEC_DIR, "assets")
SCRATCH_DIR = os.path.join(SEC_DIR, "scratch")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(SCRATCH_DIR, exist_ok=True)

img = cv2.imread(STORYBOARD_PATH)
if img is None:
    raise FileNotFoundError(f"Cannot load {STORYBOARD_PATH}")

h, w = img.shape[:2]
print(f"Loaded Section 01 storyboard: {w}x{h}")

is_bg = (img[:, :, 0] > 242) & (img[:, :, 1] > 242) & (img[:, :, 2] > 242)
fg_mask = (~is_bg).astype(np.uint8) * 255
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)
print(f"Connected components: {num_labels}")

# Asset search manifest: (name, (x1, y1, x2, y2), row_id, col_id)
manifest = [
    # Row 1 (y: 10 - 250)
    ("r1_01_waking_street",       (15,   10,  250, 250), 1, 1),
    ("r1_02_back_pain",           (265,  55,  510, 250), 1, 2),
    ("r1_03_check_backpack",      (520,  60,  760, 250), 1, 3),
    ("r1_04_broken_phone",        (780,  35,  950, 255), 1, 4),
    ("r1_05_search_wifi",         (975,  35, 1220, 255), 1, 5),
    ("r1_06_outdoor_charge",     (1235,  15, 1525, 255), 1, 6),

    # Row 2 (y: 270 - 500)
    ("r2_01_goto_bathroom",       (20,  275,  255, 500), 2, 1),
    ("r2_02_wash_sink",          (290,  275,  485, 500), 2, 2),
    ("r2_03_clean_shirt",        (495,  300,  715, 500), 2, 3),
    ("r2_04_charity_food",       (740,  290, 1005, 500), 2, 4),
    ("r2_05_eating_sidewalk",   (1015,  305, 1245, 500), 2, 5),
    ("r2_06_grocery_no_kitchen",(1275,  275, 1520, 500), 2, 6),

    # Row 3 (y: 520 - 750)
    ("r3_01_park_bench_think",    (20,  520,  280, 755), 3, 1),
    ("r3_02_public_library",     (310,  520,  585, 755), 3, 2),
    ("r3_03_begging_cardboard",  (595,  525,  880, 755), 3, 3),
    ("r3_04_missing_id",         (910,  525, 1215, 755), 3, 4),
    ("r3_05_clinic_hospital",   (1220,  530, 1520, 755), 3, 5),

    # Row 4 (y: 760 - 1015)
    ("r4_01_shelter_line",        (15,  770,  265, 1015), 4, 1),
    ("r4_02_under_bridge",       (285,  770,  595, 1015), 4, 2),
    ("r4_03_sleeping_moon",      (605,  775,  900, 1015), 4, 3),
    ("r4_04_survival_loop",      (930,  755, 1235, 1015), 4, 4),
    ("r4_05_walk_sunrise",      (1250,  770, 1520, 1015), 4, 5),
]

metadata = {}

print("\nExtracting Section 01 assets along organic silhouettes (على حدود العنصر):")
for name, (bx1, by1, bx2, by2), row_id, col_id in manifest:
    matched_cids = []
    for cid in range(1, num_labels):
        cx, cy = centroids[cid]
        area = stats[cid, cv2.CC_STAT_AREA]
        if bx1 <= cx <= bx2 and by1 <= cy <= by2 and area >= 15:
            matched_cids.append(cid)

    if not matched_cids:
        print(f"  ⚠️ Warning: No components matched for {name} in window ({bx1},{by1},{bx2},{by2})")
        continue

    comp_mask = np.isin(labels, matched_cids).astype(np.uint8) * 255
    ys, xs = np.where(comp_mask > 0)
    if len(xs) == 0 or len(ys) == 0:
        continue

    x1, x2 = int(np.min(xs)), int(np.max(xs))
    y1, y2 = int(np.min(ys)), int(np.max(ys))

    x1 = max(0, x1 - 1)
    y1 = max(0, y1 - 1)
    x2 = min(w - 1, x2 + 1)
    y2 = min(h - 1, y2 + 1)

    crop_bgr = img[y1:y2+1, x1:x2+1].copy()
    crop_mask = comp_mask[y1:y2+1, x1:x2+1]

    alpha = np.where(crop_mask > 0, 255, 0).astype(np.uint8)
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

meta_path = os.path.join(OUT_DIR, "metadata.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)
print(f"\nMetadata saved: {meta_path} ({len(metadata)} assets)")

# Catalog Image
cat_cols = 6
cat_rows = (len(manifest) + cat_cols - 1) // cat_cols
tile_w, tile_h = 280, 200
catalog = np.full((cat_rows * tile_h, cat_cols * tile_w, 3), 235, dtype=np.uint8)

for idx, (name, _, _, _) in enumerate(manifest):
    if name not in metadata:
        continue
    r = idx // cat_cols
    c = idx % cat_cols
    tx1, ty1 = c * tile_w, r * tile_h

    for cy in range(ty1, ty1 + tile_h, 20):
        for cx in range(tx1, tx1 + tile_w, 20):
            if ((cx - tx1) // 20 + (cy - ty1) // 20) % 2 == 0:
                catalog[cy:min(cy+20, ty1+tile_h), cx:min(cx+20, tx1+tile_w)] = (245, 245, 245)
            else:
                catalog[cy:min(cy+20, ty1+tile_h), cx:min(cx+20, tx1+tile_w)] = (220, 220, 220)

    asset = cv2.imread(os.path.join(OUT_DIR, f"{name}.png"), cv2.IMREAD_UNCHANGED)
    if asset is not None:
        ah, aw = asset.shape[:2]
        scale = min((tile_w - 30) / float(aw), (tile_h - 40) / float(ah))
        nw, nh = max(1, int(aw * scale)), max(1, int(ah * scale))
        resized = cv2.resize(asset, (nw, nh), interpolation=cv2.INTER_AREA)

        ox = tx1 + (tile_w - nw) // 2
        oy = ty1 + (tile_h - 25 - nh) // 2 + 5

        res_bgr = resized[:, :, :3]
        res_a = resized[:, :, 3] / 255.0
        bg_roi = catalog[oy:oy+nh, ox:ox+nw].astype(float)
        composite = bg_roi * (1.0 - res_a[:, :, None]) + res_bgr.astype(float) * res_a[:, :, None]
        catalog[oy:oy+nh, ox:ox+nw] = composite.astype(np.uint8)

        cv2.putText(catalog, name, (tx1 + 5, ty1 + tile_h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (40, 40, 40), 1)

catalog_path = os.path.join(SCRATCH_DIR, "extraction_catalog.png")
cv2.imwrite(catalog_path, catalog)
print(f"Visual catalog saved to: {catalog_path}")
