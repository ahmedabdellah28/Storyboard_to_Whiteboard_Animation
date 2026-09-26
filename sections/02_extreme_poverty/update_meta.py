import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "02_extreme_poverty")
META_PATH = os.path.join(SEC_DIR, "assets", "metadata.json")

with open(META_PATH, "r", encoding="utf-8") as f:
    meta = json.load(f)

# Update Title Banner
meta["r0_00_title_banner"] = {
    "file": "r0_00_title_banner.png",
    "row": 0,
    "col": 0,
    "desc": "عنوان القسم: الطبقة الثانية: الفقر المدقع",
    "anchor_text": "الطبقة الثانية: الفقر المدقع",
    "orig_box": [0, 0, 1000, 220],
    "orig_size": [1000, 220],
    "area": 220000,
    "drawing_demand": 2.4
}

# Update Cell 1.1 as Roof Shack
meta["r1_01_roof_shack"] = {
    "file": "r1_01_roof_shack.png",
    "row": 1,
    "col": 1,
    "desc": "سقف بالكاد يعتبر أمان (شخص جالس في مأوى)",
    "anchor_text": "هنا عندك سقف، لكنه بالكاد يعتبر أمان",
    "orig_box": [16, 16, 258, 201],
    "orig_size": [258, 201],
    "area": 35756,
    "drawing_demand": 2.2
}

# Remove old misleading key if present
meta.pop("r1_01_title_banner", None)

with open(META_PATH, "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2, ensure_ascii=False)

print("✓ Updated metadata.json successfully with r0_00_title_banner and r1_01_roof_shack")
