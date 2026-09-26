import os
import sys
import json
import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "02_extreme_poverty")
STORYBOARD_PATH = os.path.join(SEC_DIR, "storyboard.png")
OUT_DIR = os.path.join(SEC_DIR, "assets")
os.makedirs(OUT_DIR, exist_ok=True)

img = cv2.imread(STORYBOARD_PATH)
if img is None:
    raise FileNotFoundError(f"Cannot load {STORYBOARD_PATH}")

h, w = img.shape[:2]
print(f"Loaded Section 02 storyboard: {w}x{h}")

is_bg = (img[:, :, 0] > 242) & (img[:, :, 1] > 242) & (img[:, :, 2] > 242)
fg_mask = (~is_bg).astype(np.uint8) * 255
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)
print(f"Connected components: {num_labels}")

# Search manifest: (name, (bx1, by1, bx2, by2), row_id, col_id)
manifest = [
    # Row 1 (y: 0 - 265)
    ("r1_01_waking_up",            (0,     0,  300, 260), 1, 1),
    ("r1_02_crowded_room",        (310,    0,  610, 260), 1, 2),
    ("r1_03_broken_ac",           (620,    0,  910, 260), 1, 3),
    ("r1_04_prepaid_phone",       (920,    0, 1220, 260), 1, 4),
    ("r1_05_counting_tickets",   (1230,    0, 1536, 260), 1, 5),

    # Row 2 (y: 265 - 510)
    ("r2_01_basic_breakfast",       (0,  265,  305, 510), 2, 1),
    ("r2_02_shopping_coupons",    (310,  265,  605, 510), 2, 2),
    ("r2_03_kids_snacks",         (605,  265,  910, 510), 2, 3),
    ("r2_04_waiting_bus",         (910,  265, 1220, 510), 2, 4),
    ("r2_05_broken_car",         (1220,  265, 1536, 510), 2, 5),

    # Row 3 (y: 510 - 760)
    ("r3_01_work_schedule",         (0,  510,  305, 760), 3, 1),
    ("r3_02_overtime_work",       (310,  510,  605, 760), 3, 2),
    ("r3_03_overdue_bills",       (605,  510,  910, 760), 3, 3),
    ("r3_04_money_transfer",      (910,  510, 1235, 760), 3, 4),
    ("r3_05_clinic_wait",        (1235,  510, 1536, 760), 3, 5),

    # Row 4 (y: 760 - 1024)
    ("r4_01_laundry_mat",           (0,  760,  295, 1024), 4, 1),
    ("r4_02_diy_repair",          (295,  760,  605, 1024), 4, 2),
    ("r4_03_stretching_resources",(605,  760,  905, 1024), 4, 3),
    ("r4_04_night_planning",      (905,  760, 1230, 1024), 4, 4),
    ("r4_05_sleeping_night",     (1230,  760, 1536, 1024), 4, 5),
]

metadata = {}

print("\nExtracting Section 02 assets along organic silhouettes (على حدود العنصر):")
for name, (bx1, by1, bx2, by2), row_id, col_id in manifest:
    matched_cids = []
    for cid in range(1, num_labels):
        cx, cy = centroids[cid]
        area = stats[cid, cv2.CC_STAT_AREA]
        if bx1 <= cx <= bx2 and by1 <= cy <= by2 and area >= 15:
            matched_cids.append(cid)

    if not matched_cids:
        print(f"  ⚠️ Warning: No components matched for {name}")
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
        "orig_box": [int(x1), int(y1), crop_w, crop_h],
        "orig_size": [crop_w, crop_h],
        "area": int(np.sum(alpha_final > 20))
    }
    print(f"  ✅ {name:28s} -> {crop_w}x{crop_h} px | row {row_id}, col {col_id}")

meta_path = os.path.join(OUT_DIR, "metadata.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print(f"\n🎉 Successfully extracted {len(metadata)} / {len(manifest)} assets!")
print(f"Metadata saved: {meta_path}")
