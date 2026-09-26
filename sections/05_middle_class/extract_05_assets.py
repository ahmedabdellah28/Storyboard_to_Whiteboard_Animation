import os
import sys
import json
import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "05_middle_class")
STORYBOARD_PATH = os.path.join(SEC_DIR, "storyboard.png")
OUT_DIR = os.path.join(SEC_DIR, "assets")
os.makedirs(OUT_DIR, exist_ok=True)

img = cv2.imread(STORYBOARD_PATH)
if img is None:
    raise FileNotFoundError(f"Cannot load {STORYBOARD_PATH}")

h, w = img.shape[:2]
print(f"Loaded Section 05 storyboard: {w}x{h}", flush=True)

is_bg = (img[:, :, 0] > 242) & (img[:, :, 1] > 242) & (img[:, :, 2] > 242)
fg_mask = (~is_bg).astype(np.uint8) * 255
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)
print(f"Connected components: {num_labels}", flush=True)

# Search manifest: (name, (bx1, by1, bx2, by2), row_id, col_id)
manifest = [
    # Row 1 (y: 0 - 250)
    ("r1_01_three_bedroom_home",         (0,     0,  260, 250), 1, 1),
    ("r1_02_stable_mortgage_lease",     (265,    0,  600, 250), 1, 2),
    ("r1_03_coffee_official_routine",   (605,    0,  970, 250), 1, 3),
    ("r1_04_shared_family_calendar",    (975,    0, 1235, 250), 1, 4),
    ("r1_05_fresh_healthy_breakfast",  (1240,    0, 1536, 250), 1, 5),

    # Row 2 (y: 250 - 495)
    ("r2_01_clean_car_reliable_train",   (0,  250,  305, 495), 2, 1),
    ("r2_02_flexible_office_control",   (310,  250,  585, 495), 2, 2),
    ("r2_03_meetings_and_projects",     (590,  250,  945, 495), 2, 3),
    ("r2_04_paid_vacations_pension",    (950,  250, 1245, 495), 2, 4),
    ("r2_05_long_term_savings_goals",  (1250,  250, 1536, 495), 2, 5),

    # Row 3 (y: 495 - 740)
    ("r3_01_banking_app_lunch_check",    (0,  495,  240, 740), 3, 1),
    ("r3_02_monthly_installment_check", (245,  495,  470, 740), 3, 2),
    ("r3_03_home_repair_car_tire_fund", (475,  495,  770, 740), 3, 3),
    ("r3_04_gym_and_friends_sports",    (775,  495, 1245, 740), 3, 4),
    ("r3_05_home_cooking_and_takeout", (1250,  495, 1536, 740), 3, 5),

    # Row 4 (y: 740 - 1024)
    ("r4_01_calling_plumber_repair",     (0,  740,  260, 1024), 4, 1),
    ("r4_02_routine_dentist_visit",     (265,  740,  535, 1024), 4, 2),
    ("r4_03_helping_kids_homework",     (540,  740,  820, 1024), 4, 3),
    ("r4_04_birthday_gift_online",      (825,  740, 1260, 1024), 4, 4),
    ("r4_05_established_habit_stability",(1265, 740, 1536, 1024), 4, 5),
]

metadata = {}

print("\nExtracting Section 05 assets along organic silhouettes (على حدود العنصر):", flush=True)
for name, (bx1, by1, bx2, by2), row_id, col_id in manifest:
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

print(f"\n🎉 Successfully extracted {len(metadata)} Section 05 assets to {OUT_DIR}", flush=True)
