import os
import json
import cv2
import numpy as np

sec_dir = r"E:\image_to_animate\sections\03_working_poor"
assets_dir = os.path.join(sec_dir, "assets")
meta_path = os.path.join(assets_dir, "metadata.json")

with open(meta_path, "r", encoding="utf-8") as f:
    meta = json.load(f)

# Add title banner if missing
banner_path = os.path.join(assets_dir, "r0_00_title_banner.png")
if os.path.exists(banner_path):
    img = cv2.imread(banner_path, cv2.IMREAD_UNCHANGED)
    h, w = img.shape[:2]
    meta["r0_00_title_banner"] = {
        "file": "r0_00_title_banner.png",
        "row": 0,
        "col": 0,
        "orig_box": [0, 0, w, h],
        "orig_size": [w, h],
        "area": int(np.sum(img[:, :, 3] > 20)),
        "desc": "الطبقة الثالثة: الفقر العامل"
    }

# Remove r4_05_online_course and add r4_05a & r4_05b
if "r4_05_online_course" in meta:
    del meta["r4_05_online_course"]

p_top = os.path.join(assets_dir, "r4_05a_watch_series.png")
if os.path.exists(p_top):
    img = cv2.imread(p_top, cv2.IMREAD_UNCHANGED)
    h, w = img.shape[:2]
    meta["r4_05a_watch_series"] = {
        "file": "r4_05a_watch_series.png",
        "row": 4,
        "col": 5,
        "orig_box": [1046, 762, w, h],
        "orig_size": [w, h],
        "area": int(np.sum(img[:, :, 3] > 20)),
        "desc": "يمكن تتابع مسلسل على حساب مشترك"
    }

p_bot = os.path.join(assets_dir, "r4_05b_online_course.png")
if os.path.exists(p_bot):
    img = cv2.imread(p_bot, cv2.IMREAD_UNCHANGED)
    h, w = img.shape[:2]
    meta["r4_05b_online_course"] = {
        "file": "r4_05b_online_course.png",
        "row": 4,
        "col": 6,
        "orig_box": [1046, 858, w, h],
        "orig_size": [w, h],
        "area": int(np.sum(img[:, :, 3] > 20)),
        "desc": "ويمكن تبدأ كورس أونلاين لشهادة تساعدك"
    }

# Sort meta by row, then col
sorted_items = sorted(meta.items(), key=lambda kv: (kv[1].get("row", 0), kv[1].get("col", 0)))
meta_sorted = {k: v for k, v in sorted_items}

with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta_sorted, f, indent=2, ensure_ascii=False)

print(f"Updated metadata.json with {len(meta_sorted)} assets!")
