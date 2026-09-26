import os
import sys
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "06_upper_middle_class")
STORYBOARD_PATH = os.path.join(SEC_DIR, "storyboard.png")
OUT_DIR = os.path.join(SEC_DIR, "assets")
os.makedirs(OUT_DIR, exist_ok=True)

img = cv2.imread(STORYBOARD_PATH)
if img is None:
    raise FileNotFoundError(f"Cannot load {STORYBOARD_PATH}")

h, w = img.shape[:2]
print(f"Loaded Section 06 storyboard: {w}x{h}")

is_bg = (img[:, :, 0] > 242) & (img[:, :, 1] > 242) & (img[:, :, 2] > 242)
fg_mask = (~is_bg).astype(np.uint8) * 255
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)

manifest = [
    # Row 1 (y: 30 .. 255)
    ("r1_01_waking_happy",         (10,   30,  260, 255), 1, 1, "تصحى في بيت هادي تملكه في حي ممتاز"),
    ("r1_02_upscale_villa",       (270,   30,  615, 255), 1, 2, "بيت ممتاز أو منزل مستقر جداً"),
    ("r1_03_smart_home",          (635,   30,  840, 255), 1, 3, "المكيف ضبط نفسه ومكنسة روبوت تتحرك"),
    ("r1_04_home_office",         (845,   30, 1060, 255), 1, 4, "بعض الأيام تشتغل من البيت"),
    ("r1_05_master_bedroom",     (1070,   30, 1300, 255), 1, 5, "منزل مستقر وراحة يومية"),
    ("r1_06_gardener_hedge",     (1305,   30, 1525, 255), 1, 6, "تدفع للعناية بالحديقة ومحترفين"),

    # Row 2 (y: 295 .. 515)
    ("r2_01_housekeeper",          (10,  295,  185, 515), 2, 1, "عاملة نظافة تزورك بانتظام"),
    ("r2_02_investment_growth",   (190,  295,  450, 515), 2, 2, "الفلوس تتحول للتوفير والاستثمار تلقائياً"),
    ("r2_03_financial_advisor",   (460,  295,  720, 515), 2, 3, "الضرائب والتخطيط المالي والمراجعة"),
    ("r2_04_mercedes_suv",        (730,  295, 1010, 515), 2, 4, "السيارة حديثة ومدفوعة وتكاليف متوقعة"),
    ("r2_05_iphone_replacement", (1020,  295, 1270, 515), 2, 5, "وقتك أغلى من تصليح الأشياء بنفسك"),
    ("r2_06_flight_vacation",    (1275,  295, 1530, 515), 2, 6, "تحجز رحلة قبلها بشهور ونقاط مكافآت"),

    # Row 3 (y: 550 .. 770)
    ("r3_01_executive_boardroom",  (10,  550,  295, 770), 3, 1, "وظيفتك احترافية تدير فريق أو مشاريع"),
    ("r3_02_executive_schedule",  (305,  550,  500, 770), 3, 2, "عندك تحكم أكبر في جدولك اليومي"),
    ("r3_03_medical_specialist",  (510,  550,  870, 770), 3, 3, "تأمين صحي قوي وفحوصات دورية"),
    ("r3_04_private_school_kids", (875,  550, 1270, 770), 3, 4, "العيال عندهم دروس ورياضة وتدفع رسومها"),
    ("r3_05_global_charity",     (1280,  550, 1525, 770), 3, 5, "تتبرع لقضية تهمك وعطاء مجتمعي"),

    # Row 4 (y: 790 .. 1005)
    ("r4_01_trainer_gym",          (15,  790,  275, 1005), 4, 1, "تروح جيم مع مدرب أو تاخذ كلاس"),
    ("r4_02_family_movie_night",  (280,  790,  660, 1005), 4, 2, "في الليل تشوف مسلسل أو تقرأ"),
    ("r4_03_next_year_plans",     (670,  790,  890, 1005), 4, 3, "تراجع أجندة بكرة وتخطط للمستقبل"),
    ("r4_04_infinity_pool",       (895,  790, 1235, 1005), 4, 4, "تحس بالأمان ومرتاح من ضغط اليوم"),
    ("r4_05_peaceful_sleep",     (1245,  790, 1530, 1005), 4, 5, "تنام مرتاح وتفكر في المستقبل بأمان"),
]

# Generate Authentic Arabic Title Banner
def generate_title_banner():
    banner_path = os.path.join(OUT_DIR, "r0_00_title_banner.png")
    title_text = "الطبقة السادسة: الطبقة المتوسطة العليا"
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
        "desc": "الطبقة السادسة: الطبقة المتوسطة العليا"
    }
}

print("\nExtracting all 22 Section 06 cells along organic silhouettes:")
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

print(f"\n🎉 Successfully extracted {len(metadata)} assets (1 title + 22 cells)!")
print(f"Catalog saved: {meta_path}")
