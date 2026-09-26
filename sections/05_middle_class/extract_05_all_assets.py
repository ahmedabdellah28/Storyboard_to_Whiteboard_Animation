import os
import sys
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

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
print(f"Loaded Section 05 storyboard: {w}x{h}")

is_bg = (img[:, :, 0] > 242) & (img[:, :, 1] > 242) & (img[:, :, 2] > 242)
fg_mask = (~is_bg).astype(np.uint8) * 255
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)

# 23 cells accurately defined across the 4 rows:
manifest = [
    # Row 1 (y: 20 .. 270)
    ("r1_01_waking_happy",      (10,   20,  260, 270), 1, 1, "تصحى في بيت ثلاث غرف أو شقة مريحة"),
    ("r1_02_suburban_house",    (265,  20,  585, 270), 1, 2, "عندك رهن عقاري أو عقد إيجار مستقر"),
    ("r1_03_robot_vacuum",      (600,  80,  780, 270), 1, 3, "التدفئة والمكيف والأجهزة شغالة"),
    ("r1_04_espresso_machine",  (790,  30,  980, 270), 1, 4, "والقهوة جاهزة تقريباً كأنها روتين"),
    ("r1_05_shared_calendar",   (1000, 20, 1235, 270), 1, 5, "تشيك تقويم مشترك بينك وبين العائلة"),
    ("r1_06_autopay_bills",    (1240, 20, 1520, 270), 1, 6, "الرواتب ثابتة والفواتير تنخصم تلقائياً"),

    # Row 2 (y: 295 .. 520)
    ("r2_01_fresh_breakfast",   (15,  295,  300, 520), 2, 1, "الفطور بسيط لكن طازج: بيض، توست، فاكهة"),
    ("r2_02_kids_lunch_prep",  (320,  295,  590, 520), 2, 2, "تجهز غدا الأطفال وتراجع واجباتهم"),
    ("r2_03_luxury_suv",       (600,  295,  935, 520), 2, 3, "سيارة نظيفة ومصاريف محسوبة مو مفاجآت"),
    ("r2_04_team_management",  (945,  295, 1235, 520), 2, 4, "في الدوام دور واضح وإدارة ومشاريع"),
    ("r2_05_corner_office",   (1245,  295, 1525, 520), 2, 5, "مساحة تحكم وإجازات وتأمين طبيعي"),

    # Row 3 (y: 540 .. 770)
    ("r3_01_doctor_checkup",    (10,  540,  225, 770), 3, 1, "تحجز فحص طبي وفحص الأسنان قبل الألم"),
    ("r3_02_gym_weights",      (235,  540,  450, 770), 3, 2, "بعد الدوام تروح نادي أو تلعب كورة"),
    ("r3_03_vacation_dream",   (470,  540,  765, 770), 3, 3, "إجازات مدفوعة ومدخرات لأهداف ثانية"),
    ("r3_04_investment_app",   (800,  540,  955, 770), 3, 4, "تحط جزء للتقاعد واستثمارات"),
    ("r3_05_plumber_repair",   (970,  540, 1240, 770), 3, 5, "إذا صار تسريب في البيت تجيب سباك"),
    ("r3_06_gardener_hedge",  (1255,  540, 1530, 770), 3, 6, "صندوق مخصص لتصليح البيت والصيانة"),

    # Row 4 (y: 775 .. 1015)
    ("r4_01_housekeeper",       (10,  775,  250, 1015), 4, 1, "خدمات منزلية واستقرار يومي"),
    ("r4_02_kids_activities",  (255,  775,  525, 1015), 4, 2, "أنشطة الأطفال ورياضة وتعليم"),
    ("r4_03_online_gift",      (535,  775,  790, 1015), 4, 3, "تطلب هدية أونلاين بدون ما تشيك الرصيد"),
    ("r4_04_charity_donation", (820,  775, 1010, 1015), 4, 4, "مساهمة ومشاركة مجتمعية وعطاء"),
    ("r4_05_tomorrow_agenda", (1020,  775, 1265, 1015), 4, 5, "أجندة الغد وتنظيم وقت العائلة"),
    ("r4_06_peaceful_sleep",  (1275,  775, 1530, 1015), 4, 6, "هنا الاستقرار صار عادة وهامش أمان"),
]

# Generate Authentic Arabic Title Banner
def generate_title_banner():
    banner_path = os.path.join(OUT_DIR, "r0_00_title_banner.png")
    title_text = "الطبقة الخامسة: الطبقة المتوسطة"
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(title_text)
        bidi_t = get_display(reshaped)
    except Exception:
        bidi_t = title_text

    w_b, h_b = 1100, 220
    b_img = Image.new('RGBA', (w_b, h_b), (255, 255, 255, 0))
    draw = ImageDraw.Draw(b_img)

    font_paths = [
        'C:/Windows/Fonts/arialbd.ttf',
        'C:/Windows/Fonts/tahomabd.ttf'
    ]
    font = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, 56)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), bidi_t, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (w_b - tw) // 2
    ty = (h_b - th) // 2 - 14

    draw.text((tx, ty), bidi_t, font=font, fill=(25, 25, 30, 255))
    line_y = ty + th + 16
    draw.line([(tx - 25, line_y), (tx + tw + 25, line_y)], fill=(35, 35, 40, 255), width=6)

    b_img.save(banner_path)
    print(f"Generated Title Banner: {banner_path}")
    return banner_path, w_b, h_b

banner_path, bw, bh = generate_title_banner()

metadata = {
    "r0_00_title_banner": {
        "file": "r0_00_title_banner.png",
        "row": 0,
        "col": 0,
        "orig_box": [0, 0, bw, bh],
        "orig_size": [bw, bh],
        "area": 25000,
        "desc": "الطبقة الخامسة: الطبقة المتوسطة"
    }
}

print("\nExtracting all 23 Section 05 cells along organic silhouettes:")
for name, (bx1, by1, bx2, by2), row_id, col_id, desc in manifest:
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
        "area": int(np.sum(alpha_final > 20)),
        "desc": desc
    }
    print(f"  ✅ {name:28s} -> {crop_w}x{crop_h} px | Row {row_id}, Col {col_id}")

meta_path = os.path.join(OUT_DIR, "metadata.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print(f"\n🎉 Successfully extracted {len(metadata)} assets (1 title + 23 cells)!")
print(f"Catalog saved: {meta_path}")
