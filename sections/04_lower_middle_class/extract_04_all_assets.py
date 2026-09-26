import os
import sys
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "04_lower_middle_class")
STORYBOARD_PATH = os.path.join(SEC_DIR, "storyboard.png")
OUT_DIR = os.path.join(SEC_DIR, "assets")
os.makedirs(OUT_DIR, exist_ok=True)

img = cv2.imread(STORYBOARD_PATH)
if img is None:
    raise FileNotFoundError(f"Cannot load {STORYBOARD_PATH}")

h, w = img.shape[:2]
print(f"Loaded Section 04 storyboard: {w}x{h}")

is_bg = (img[:, :, 0] > 242) & (img[:, :, 1] > 242) & (img[:, :, 2] > 242)
fg_mask = (~is_bg).astype(np.uint8) * 255
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
fg_clean = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)

manifest = [
    # Row 1 (y: 10 .. 240)
    ("r1_01_waking_happy",        (15,   10,  250, 240), 1, 1, "تصحى في شقة غرفتين وصالة"),
    ("r1_02_modest_bedroom",      (280,  10,  570, 240), 1, 2, "المكان نظيف وبسيط"),
    ("r1_03_coffee_morning",      (630,  10,  900, 240), 1, 3, "القهوة تتجهز"),
    ("r1_04_calendar_bills",      (935,  10, 1170, 240), 1, 4, "وعلى الثلاجة قائمة للفواتير ومواعيدها"),
    ("r1_05_modest_house",       (1200,  10, 1525, 240), 1, 5, "أو بيت صغير متواضع"),

    # Row 2 (y: 245 .. 455)
    ("r2_01_stable_job_checklist",(10,  245,  330, 455), 2, 1, "عندك وظيفة ثابتة بساعات واضحة"),
    ("r2_02_healthy_breakfast",  (350,  245,  570, 455), 2, 2, "الفطور بسيط: بيض، توست، فاكهة"),
    ("r2_03_kids_lunch_prep",    (600,  245,  900, 455), 2, 3, "تجهز غدا الأطفال وتشيك واجباتهم"),
    ("r2_04_used_clean_car",     (930,  245, 1230, 455), 2, 4, "سيارة مستعملة ونظيفة عليها أقساط"),
    ("r2_05_commuter_train",    (1260,  245, 1525, 455), 2, 5, "أو قطار باشتراك شهري"),

    # Row 3 (y: 460 .. 675)
    ("r3_01_office_desk_tasks",   (10,  460,  330, 675), 3, 1, "في الدوام دورك واضح: إيميلات وطلبات"),
    ("r3_02_paid_break_dream",   (350,  460,  610, 675), 3, 2, "بريك مدفوع ووقت غداء وجدول واضح"),
    ("r3_03_banking_app",        (700,  460,  870, 675), 3, 3, "تفتح تطبيق البنك: قسط القرض والتوفير"),
    ("r3_04_retirement_jar",     (960,  460, 1190, 675), 3, 4, "تحفظ جزء بسيط للتقاعد وصندوق الطوارئ"),
    ("r3_05_home_maintenance",  (1240,  460, 1525, 675), 3, 5, "مصاريف صيانة تعرف مكانها قبل ما تدفعها"),

    # Row 4 (y: 685 .. 860)
    ("r4_01_gym_treadmill",       (10,  685,  260, 860), 4, 1, "بعد الدوام تمر نادي رخيص أو تمشي"),
    ("r4_02_family_dinner",      (310,  685,  605, 860), 4, 2, "العشاء غالباً طبخ بيت"),
    ("r4_03_dental_checkup",     (680,  685,  860, 860), 4, 3, "تأمين صحي ورعاية دورية"),
    ("r4_04_streaming_tv",       (910,  685, 1225, 860), 4, 4, "نتفليكس وأخواتها والترفيه المتبادل"),
    ("r4_05_online_shopping",   (1280,  685, 1525, 860), 4, 5, "إدارة الميزانية والتسوق الذكي"),

    # Row 5 (y: 865 .. 1020)
    ("r5_01_desk_studying",       (20,  865,  255, 1020), 5, 1, "تطوير الذات والدراسة المنظمة"),
    ("r5_02_roadtrip_mountains", (305,  865,  570, 1020), 5, 2, "رحلة برية قصيرة مرة في السنة"),
    ("r5_03_reading_armchair",   (620,  865,  860, 1020), 5, 3, "هدوء المساء وقراءة كتاب"),
    ("r5_04_peaceful_sleep",     (920,  865, 1180, 1020), 5, 4, "تنام منظم وتحس بالاستقرار"),
    ("r5_05_safety_checklist",  (1290,  865, 1475, 1020), 5, 5, "هامش بسيط للأمان"),
]

# Generate Authentic Arabic Title Banner
def generate_title_banner():
    banner_path = os.path.join(OUT_DIR, "r0_00_title_banner.png")
    title_text = "الطبقة الرابعة: الطبقة المتوسطة الدنيا"
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
        "desc": "الطبقة الرابعة: الطبقة المتوسطة الدنيا"
    }
}

print("\nExtracting all 25 Section 04 cells along organic silhouettes:")
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

print(f"\n🎉 Successfully extracted {len(metadata)} assets (1 title + 25 cells)!")
print(f"Catalog saved: {meta_path}")
