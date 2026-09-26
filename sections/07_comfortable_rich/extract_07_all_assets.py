import os
import sys
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "07_comfortable_rich")
STORYBOARD_PATH = os.path.join(SEC_DIR, "storyboard.png")
OUT_DIR = os.path.join(SEC_DIR, "assets")
os.makedirs(OUT_DIR, exist_ok=True)

img = cv2.imread(STORYBOARD_PATH)
if img is None:
    raise FileNotFoundError(f"Cannot load {STORYBOARD_PATH}")

h, w = img.shape[:2]
print(f"Loaded Section 07 storyboard: {w}x{h}")

# Generate Title Banner
def generate_title_banner():
    banner_path = os.path.join(OUT_DIR, "r0_00_title_banner.png")
    title_text = "الطبقة السابعة: الغني المرتاح"
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
        'C:/Windows/Fonts/tradbdo.ttf',
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

# Define precise asset manifest with bounding boxes: (x1, y1, x2, y2)
# Row 1 (y: 25..230)
# Row 2 (y: 240..425)
# Row 3 (y: 430..635)
# Row 4 (y: 640..825)
# Row 5 (y: 825..1015)
manifest = [
    # Row 1
    ("r1_01_waking_bed",             (9,    25,  189, 230), 1, 1, "تصحى في بيت هادي تملكه في حي مرغوب"),
    ("r1_02_luxury_house",           (190,  25,  515, 230), 1, 2, "البيت تملكه والرهن بسيط أو شبه مدفوع"),
    ("r1_03_smart_control",          (520,  25,  660, 230), 1, 3, "الإضاءة والحرارة والأمان كلها تعمل بشكل ذكي"),
    ("r1_04_home_office",            (660,  25,  865, 230), 1, 4, "عندك مكتب منزلي"),
    ("r1_05_guest_bedroom",          (867,  25,  995, 230), 1, 5, "غرفة ضيوف"),
    ("r1_06_yard_robot",             (1000, 25, 1215, 230), 1, 6, "حوش والحديقة لها صيانة وروبوت"),
    ("r1_07_housekeeper",            (1215, 25, 1360, 230), 1, 7, "عاملة نظافة تجي بانتظام"),
    ("r1_08_gardener",               (1365, 25, 1527, 230), 1, 8, "أنت هنا تشتري وقتك وتفوض المهام"),

    # Row 2
    ("r2_01_real_estate_wealth",     (11,   240,  215, 425), 2, 1, "ثروتك موزعة بين قيمة البيت"),
    ("r2_02_retirement_jar",         (225,  240,  385, 425), 2, 2, "وحسابات التقاعد"),
    ("r2_03_portfolio_tablet",       (395,  240,  540, 425), 2, 3, "ومحفظة استثمارية"),
    ("r2_04_commercial_property",   (545,  240,  715, 425), 2, 4, "ويمكن عقار أو بزنس صغير"),
    ("r2_05_emergency_safe",         (720,  240,  848, 425), 2, 5, "وعندك صندوق طوارئ كبير"),
    ("r2_06_insurance_shield",       (850,  240,  970, 425), 2, 6, "وتأمين قوي"),
    ("r2_07_accountant_advisor",     (980,  240, 1210, 425), 2, 7, "ومحاسب يضبط الضرائب ومستشار مالي"),
    ("r2_08_monthly_transfer",       (1220, 240, 1340, 425), 2, 8, "الفلوس تتحرك تلقائياً للاستثمار"),
    ("r2_09_iphone_replacement",     (1350, 240, 1515, 425), 2, 9, "جوالك انكسر تبدله نفس اليوم"),

    # Row 3
    ("r3_01_luxury_suv",             (8,    430,  245, 635), 3, 1, "السيارة فخمة وحديثة ومدفوعة"),
    ("r3_02_private_jet",            (246,  430,  440, 635), 3, 2, "تقدر تأخذ إجازة حقيقية"),
    ("r3_03_executive_meeting",      (445,  430,  665, 635), 3, 3, "في الشغل أنت في مستوى أعلى تدير فريق"),
    ("r3_04_beach_work",             (675,  430,  818, 635), 3, 4, "وجدولك تتحكم فيه ودخلك مستمر"),
    ("r3_05_beach_vacation",         (823,  430,  990, 635), 3, 5, "إجازة واسترخاء تام"),
    ("r3_06_preventative_doctor",    (992,  430, 1160, 635), 3, 6, "الصحة وقائية وفحوصات دورية"),
    ("r3_07_dental_checkup",         (1168, 430, 1360, 635), 3, 7, "ولا تنتظر الألم عشان تبدأ تتحرك"),
    ("r3_08_plumber_repair",         (1368, 430, 1530, 635), 3, 8, "توافق على إصلاح بالبيت بدون تردد"),

    # Row 4
    ("r4_01_private_school",         (9,    640,  218, 825), 4, 1, "تعليم متميز في أرقى المدارس الخاصة"),
    ("r4_02_soccer_boy",             (222,  640,  348, 825), 4, 2, "أنشطة رياضية وكرة قدم"),
    ("r4_03_ballet_girl",            (348,  640,  480, 825), 4, 3, "دروس باليه وفنون"),
    ("r4_04_piano_lesson",           (482,  640,  662, 825), 4, 4, "دروس بيانو وموسيقى"),
    ("r4_05_laptop_study",           (665,  640,  870, 825), 4, 5, "دراسة واستشارات وتطوير"),
    ("r4_06_family_travel",          (872,  640, 1108, 825), 4, 6, "سفر عائلي فاخر وحجز مريح"),
    ("r4_07_vacation_planning",      (1110, 640, 1335, 825), 4, 7, "تخطيط الرحلات القادمة باسترخاء"),
    ("r4_08_charity_donation",       (1335, 640, 1525, 825), 4, 8, "تبرع للمدارس والقضايا والمجتمع"),

    # Row 5
    ("r5_01_night_investments",      (15,   825,  265, 1015), 5, 1, "تراجع استثماراتك ليلاً في هدوء"),
    ("r5_02_accountant_signing",     (270,  825,  510, 1015), 5, 2, "توقع ورقة من المحاسب المالي"),
    ("r5_03_gift_ordering",          (515,  825,  735, 1015), 5, 3, "تطلب هدية بدون ما تشيك رصيدك"),
    ("r5_04_year_planning",          (742,  825,  990, 1015), 5, 4, "تخطط للسنة الجاية وسفر وتطوير"),
    ("r5_05_home_renovation",        (995,  825, 1208, 1015), 5, 5, "تجديد للبيت واستثمار جديد"),
    ("r5_06_peaceful_sunset",        (1212, 825, 1528, 1015), 5, 6, "مساحة تخطط للمستقبل وأنت مرتاح")
]

metadata = {
    "r0_00_title_banner": {
        "file": "r0_00_title_banner.png",
        "row": 0,
        "col": 0,
        "orig_box": [0, 0, bw, bh],
        "orig_size": [bw, bh],
        "area": 25000,
        "desc": "الطبقة السابعة: الغني المرتاح"
    }
}

print(f"Extracting {len(manifest)} detailed visual assets...")

for aid, (x1, y1, x2, y2), row, col, desc in manifest:
    crop = img[y1:y2, x1:x2].copy()
    ch, cw = crop.shape[:2]

    # Convert to BGRA with feathered alpha
    # Background is white/near white (> 242)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    
    # Create smooth alpha: 0 for >245, 255 for <235, linear ramp in between
    alpha = np.ones((ch, cw), dtype=np.float32)
    # Thresholding
    is_white = (crop[:, :, 0] > 240) & (crop[:, :, 1] > 240) & (crop[:, :, 2] > 240)
    
    # Connected component flood fill from corners to eliminate external white background only
    # preventing internal whites (like white shirts or white paper) from becoming transparent!
    flood_mask = np.zeros((ch + 2, cw + 2), dtype=np.uint8)
    # create binary mask where 1 is white
    white_bin = is_white.astype(np.uint8)
    # flood fill from borders
    cv2.floodFill(white_bin, flood_mask, (0, 0), 2)
    cv2.floodFill(white_bin, flood_mask, (cw - 1, 0), 2)
    cv2.floodFill(white_bin, flood_mask, (0, ch - 1), 2)
    cv2.floodFill(white_bin, flood_mask, (cw - 1, ch - 1), 2)

    bg_mask = (white_bin == 2)
    
    # Smooth edges of bg_mask
    bg_dist = cv2.distanceTransform((~bg_mask).astype(np.uint8), cv2.DIST_L2, 3)
    alpha = np.clip(bg_dist / 1.5, 0.0, 1.0) * 255.0
    alpha = alpha.astype(np.uint8)

    bgra = np.dstack([crop, alpha])

    # Crop to non-transparent bounding box
    nonzero = np.argwhere(alpha > 10)
    if len(nonzero) > 0:
        ymin, xmin = nonzero.min(axis=0)
        ymax, xmax = nonzero.max(axis=0)
        # add 2px margin
        ymin = max(0, ymin - 2)
        xmin = max(0, xmin - 2)
        ymax = min(ch, ymax + 3)
        xmax = min(cw, xmax + 3)
        bgra_tight = bgra[ymin:ymax, xmin:xmax]
    else:
        bgra_tight = bgra

    out_file = f"{aid}.png"
    out_path = os.path.join(OUT_DIR, out_file)
    cv2.imwrite(out_path, bgra_tight)

    th, tw = bgra_tight.shape[:2]
    metadata[aid] = {
        "file": out_file,
        "row": row,
        "col": col,
        "orig_box": [int(x1), int(y1), int(x2), int(y2)],
        "orig_size": [int(tw), int(th)],
        "area": int(tw * th),
        "desc": desc
    }
    print(f"  ✓ Extracted {aid}: {tw}x{th} -> {desc}")

meta_path = os.path.join(OUT_DIR, "metadata.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print(f"\n🎉 Successfully extracted {len(metadata)} assets with metadata saved to: {meta_path}")
