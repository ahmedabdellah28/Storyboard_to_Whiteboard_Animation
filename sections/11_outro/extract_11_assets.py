import os
import sys
import json
import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "11_outro")
STORYBOARD_PATH = os.path.join(SEC_DIR, "storyboard.png")
ANALYSIS_PATH = os.path.join(SEC_DIR, "scratch", "storyboard_analysis.json")
OUT_DIR = os.path.join(SEC_DIR, "assets")
os.makedirs(OUT_DIR, exist_ok=True)

img = cv2.imread(STORYBOARD_PATH)
if img is None:
    raise FileNotFoundError(f"Cannot load {STORYBOARD_PATH}")

h, w = img.shape[:2]
print(f"Loaded Section 11 storyboard: {w}x{h}", flush=True)

is_bg = (img[:, :, 0] > 242) & (img[:, :, 1] > 242) & (img[:, :, 2] > 242)
fg_mask = (~is_bg).astype(np.uint8) * 255
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)
print(f"Connected components: {num_labels}", flush=True)

with open(ANALYSIS_PATH, "r", encoding="utf-8") as f:
    elements = json.load(f)

metadata = {}
print("\nExtracting Section 11 assets along organic silhouettes (على حدود العنصر):", flush=True)

for el in elements:
    name = el["element_id"]
    bx1, by1, bx2, by2 = el["box"]
    
    parts = name.split("_")
    row_id = int(parts[0][1:])
    col_id = int(parts[1])

    matched_cids = []
    for cid in range(1, num_labels):
        cx, cy = centroids[cid]
        area = stats[cid, cv2.CC_STAT_AREA]
        if bx1 <= cx <= bx2 and by1 <= cy <= by2 and area >= 15:
            matched_cids.append(cid)

    if not matched_cids:
        print(f"  ⚠️ Warning: No components matched for {name}", flush=True)
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
    out_file = os.path.join(OUT_DIR, f"{name}.png")
    cv2.imwrite(out_file, rgba)

    crop_w = int(x2 - x1 + 1)
    crop_h = int(y2 - y1 + 1)
    metadata[name] = {
        "file": f"{name}.png",
        "row": row_id,
        "col": col_id,
        "width": crop_w,
        "height": crop_h,
        "original_bbox": [x1, y1, x2, y2]
    }
    print(f"  ✅ {name:32s} -> {crop_w}x{crop_h} px", flush=True)

meta_path = os.path.join(OUT_DIR, "metadata.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)

print(f"\n🎉 Successfully extracted {len(metadata)} Section 11 assets to {OUT_DIR}", flush=True)
