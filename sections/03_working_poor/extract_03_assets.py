import os
import sys
import json
import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "03_working_poor")
STORYBOARD_PATH = os.path.join(SEC_DIR, "storyboard.png")
OUT_DIR = os.path.join(SEC_DIR, "assets")
os.makedirs(OUT_DIR, exist_ok=True)

img = cv2.imread(STORYBOARD_PATH)
if img is None:
    raise FileNotFoundError(f"Cannot load {STORYBOARD_PATH}")

h, w = img.shape[:2]
print(f"Loaded Section 03 storyboard: {w}x{h}")

is_bg = (img[:, :, 0] > 242) & (img[:, :, 1] > 242) & (img[:, :, 2] > 242)
fg_mask = (~is_bg).astype(np.uint8) * 255
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)
print(f"Connected components: {num_labels}")

# Search manifest: (name, (bx1, by1, bx2, by2), row_id, col_id)
manifest = [
    # Row 1 (y: 20 - 270)
    ("r1_01_alarm_wake",         (10,   30,  250, 260), 1, 1),
    ("r1_02_small_apartment",    (250,  40,  500, 260), 1, 2),
    ("r1_03_check_bank_app",     (500,  20,  715, 260), 1, 3),
    ("r1_04_coffee_meal_prep",   (720,  40,  965, 260), 1, 4),
    ("r1_05_bus_commute",        (970,  50, 1225, 260), 1, 5),
    ("r1_06_old_car_fuel",      (1230,  40, 1530, 260), 1, 6),

    # Row 2 (y: 280 - 520)
    ("r2_01_cashier_job",        (10,  280,  210, 520), 2, 1),
    ("r2_02_warehouse_job",     (210,  280,  415, 520), 2, 2),
    ("r2_03_restaurant_job",    (420,  280,  615, 520), 2, 3),
    ("r2_04_caregiver_job",     (620,  290,  820, 520), 2, 4),
    ("r2_05_shift_checklist",   (820,  280, 1055, 520), 2, 5),
    ("r2_06_eating_lunchbox",  (1060,  300, 1265, 520), 2, 6),
    ("r2_07_shifts_schedule",  (1290,  280, 1535, 520), 2, 7),

    # Row 3 (y: 515 - 745)
    ("r3_01_doctor_visit",       (10,  515,  265, 745), 3, 1),
    ("r3_02_family_thinking",   (270,  515,  575, 745), 3, 2),
    ("r3_03_shopping_discounts",(580,  515,  810, 745), 3, 3),
    ("r3_04_loyalty_card",      (810,  520,  960, 745), 3, 4),
    ("r3_05_utility_bills",     (960,  515, 1205, 745), 3, 5),
    ("r3_06_savings_jar",      (1210,  515, 1525, 745), 3, 6),

    # Row 4 (y: 740 - 1010)
    ("r4_01_cooking_dinner",     (10,  740,  225, 1010), 4, 1),
    ("r4_02_laundry_hanging",   (225,  740,  505, 1010), 4, 2),
    ("r4_03_mail_notices",      (510,  740,  805, 1010), 4, 3),
    ("r4_04_side_job_msg",      (810,  740, 1035, 1010), 4, 4),
    ("r4_05_online_course",    (1035,  740, 1295, 1010), 4, 5),
    ("r4_06_sleep_night",      (1295,  740, 1535, 1010), 4, 6),
]

metadata = {}

print("\nExtracting Section 03 assets along organic silhouettes (على حدود العنصر):")
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
