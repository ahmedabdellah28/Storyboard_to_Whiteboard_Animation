import os
import sys
import json
import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "01_homeless")
STORYBOARD_PATH = os.path.join(SEC_DIR, "storyboard.png")
OUT_DIR = os.path.join(SEC_DIR, "assets")
os.makedirs(OUT_DIR, exist_ok=True)

data = np.fromfile(STORYBOARD_PATH, dtype=np.uint8)
img = cv2.imdecode(data, cv2.IMREAD_COLOR)
h, w = img.shape[:2]
print(f"Loaded storyboard: {w}x{h}")

is_bg = (img[:, :, 0] > 242) & (img[:, :, 1] > 242) & (img[:, :, 2] > 242)
fg_mask = (~is_bg).astype(np.uint8) * 255

# Morphological clustering
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (12, 12))
fg_grouped = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_grouped, connectivity=8)

boxes = []
for i in range(1, num_labels):
    x, y, bw, bh, area = stats[i]
    if area > 1000 and bw > 30 and bh > 30:
        boxes.append((x, y, bw, bh, area))

print(f"Detected {len(boxes)} element clusters.")

# Group into 6 rows
row_height = h / 6.0
rows = [[] for _ in range(6)]
for b in boxes:
    cx = b[0] + b[2] / 2
    cy = b[1] + b[3] / 2
    r_idx = min(5, int(cy / row_height))
    rows[r_idx].append(b)

# Define semantic names and descriptors for each row and element
manifest_definitions = [
    # Row 1
    [
        ("r1_01_waking_alarm", "استيقاظ مبكر وصوت المنبه", "تصحى قبل الفجر"),
        ("r1_02_city_noise", "ضوضاء الشارع وحركة السيارات", "لأن الشارع يصير مزعج مع بداية حركة المدينة"),
        ("r1_03_body_pain", "ألم وتصلب الجسم", "جسمك مكسر ومتصلب"),
        ("r1_04_sleep_concrete", "النوم على صبة في الشارع", "من النوم على صبة"),
        ("r1_05_sleep_bench", "النوم على كرسي حديقة", "أو كرسي حديقة"),
        ("r1_06_sleep_shelter", "النوم على فرشة في ملجأ", "أو فرشة في ملجأ"),
        ("r1_07_check_backpack", "فحص أغراض الحقيبة", "أول شيء تسويه؟ تشيك على أغراضك القليلة"),
        ("r1_08_backpack_items", "الأغراض المتبقية والتأكد منها", "وتتأكد إن ما انسرق منك شيء في الليل"),
    ],
    # Row 2
    [
        ("r2_01_phone_broken", "جوال قديم مكسور", "إذا عندك جوال، غالباً يكون قديم"),
        ("r2_02_screen_cracked", "الشاشة مكسورة", "الشاشة مكسورة"),
        ("r2_03_battery_dead", "البطارية تفصل بسرعة", "والبطارية تفصل بسرعة"),
        ("r2_04_search_wifi", "البحث عن واي فاي", "فتدور على واي فاي مجاني"),
        ("r2_05_wifi_icon", "رمز شبكة الواي فاي ككنز", "كأنك تدور كنز"),
        ("r2_06_charger_problem", "مشكلة شاحن الكهرباء", "والشاحن؟ مشكلة ثانية لحالها"),
        ("r2_07_goto_bathroom", "البحث عن حمام عام", "بعدها أول هدف: حمام ومويه"),
        ("r2_08_wash_face_sink", "غسل الوجه في المغسلة", "تدخل بسرعة، تغسل وجهك وجسمك بأبسط طريقة"),
        ("r2_09_shower_clean", "الاستحمام وترتيب النفس", "وتحاول ترتب نفسك"),
    ],
    # Row 3
    [
        ("r3_01_clean_shirt", "قميص نظيف", "الملابس النظيفة هنا مو شيء عادي"),
        ("r3_02_folded_clothes", "ملابس نظيفة عملة نادرة", "الملابس النظيفة عملة نادرة"),
        ("r3_03_dirty_shirt", "ملابس متسخة وقديمة", "صعوبة الحصول على ثياب نظيفة"),
        ("r3_04_look_dirty_shirt", "النظر بحسرة للملابس المتسخة", "معاناة المظهر والنظافة"),
        ("r3_05_eating_sandwich", "وجبة طعام سريعة", "بعدها يجي الأكل"),
        ("r3_06_charity_food", "فطور مجاني في جمعية خيرية", "تدور على فطور مجاني في جمعية خيرية"),
        ("r3_07_soup_kitchen", "وجبة رخيصة بالدولارات القليلة", "أو أرخص وجبة تقدر تشتريها"),
        ("r3_08_grocery_card", "مقاضي تموين بدون مطبخ", "وإذا عندك بطاقة تموين، تشتري مقاضي لكن ما عندك مطبخ"),
    ],
    # Row 4
    [
        ("r4_01_hunger_craving", "الجوع دائماً قريب", "فتاكل اللي تقدر تشيله.. الجوع دائماً قريب"),
        ("r4_02_safety_planning", "خطة اليوم تنبني على الأمان", "حتى خطة يومك ما تنبني على الراحة تنبني على الأمان"),
        ("r4_03_bench_rest", "مكان للجلوس بدون طرد", "والأماكن اللي تقدر تجلس فيها بدون ما أحد يطردك"),
        ("r4_04_library_books", "المكتبة العامة كنز وكتب", "المكتبة العامة بالنسبة لك كنز"),
        ("r4_05_bench_chair", "كرسي متاح للراحة", "كرسي.. واي فاي.. فيش كهرباء"),
        ("r4_06_laptop_search", "البحث عن عمل بالكمبيوتر", "ومكان تقدر فيه تدور على شغل"),
        ("r4_07_job_profile", "السعي وراء وظيفة", "محاولة التقديم على فرصة عمل"),
    ],
    # Row 5
    [
        ("r5_01_begging_cup", "التسول بكرتونة وزاوية الشارع", "حتى لو كنت تتسول، تختار زاوية فيها حركة ناس"),
        ("r5_02_coins_money", "الفلوس القليلة تتجمع ببطء", "الفلوس القليلة تتجمع ببطء"),
        ("r5_03_day_no_money", "يوم كامل بدون دخل", "وأحياناً يمر يوم كامل وما يجيك ولا شيء"),
        ("r5_04_missing_id_card", "مشكلة الأوراق الرسمية والهوية", "ثم تجي المشكلة الأكبر: الأوراق الرسمية. ما عندك هوية؟"),
        ("r5_05_court_documents", "إجراءات ورسوم استخراج هوية", "تحتاج وقت، ورسوم، وإجراءات، وأحياناً عنوان"),
        ("r5_06_no_address", "انعدام العنوان السكني", "وأنت أصلاً ما عندك عنوان"),
        ("r5_07_hospital_clinic", "الصحة ومراجعة الطوارئ والعيادة", "الصحة.. زيارتك للطوارئ هي الحل أو عيادة مجانية"),
    ],
    # Row 6
    [
        ("r6_01_shelter_bunk", "قوانين وطوابير الملجأ", "الملجأ له قوانين وطوابير"),
        ("r6_02_shelter_line", "الوقوف في طابور الملجأ", "وبالليل تبدأ نفس الدائرة: وين تنام؟"),
        ("r6_03_street_sleeping", "النوم في الشارع وضوضاء الليل", "والشارع فيه ضوضاء وخطر"),
        ("r6_04_siren_danger", "الخوف والمخاطر الليلية", "ضوضاء وخطر الشارع"),
        ("r6_05_hide_valuables", "تخبئة الأغراض الثمينة داخل الملابس", "تخبي أغراضك الثمينة داخل ملابسك"),
        ("r6_06_sleep_light", "النوم الخفيف الحذر", "وتنام نوم خفيف"),
        ("r6_07_walk_sunrise", "شروق الشمس وبداية يوم جديد", "وبكرة؟ الصبح يجي بدري"),
        ("r6_08_survival_cycle", "دوامة البقاء اليومية", "وتعيد نفس الدوامة: مويه، أكل، أمان، وخطة تكمل فيها يوم واحد زيادة"),
    ]
]

metadata = {}
extracted_count = 0

for r_idx in range(6):
    r_boxes = rows[r_idx]
    r_boxes.sort(key=lambda b: b[0])
    defs = manifest_definitions[r_idx]
    print(f"\n--- Extracting Row {r_idx+1} ({len(r_boxes)} detected, {len(defs)} mapped) ---")
    
    for c_idx, b in enumerate(r_boxes):
        if c_idx >= len(defs):
            name = f"r{r_idx+1}_{c_idx+1:02d}_extra"
            desc = "عنصر توضيحي إضافي"
            anchor = ""
        else:
            name, desc, anchor = defs[c_idx]

        bx, by, bw, bh, area = b
        # Add slight margin
        pad = 6
        x1 = max(0, bx - pad)
        y1 = max(0, by - pad)
        x2 = min(w, bx + bw + pad)
        y2 = min(h, by + bh + pad)

        crop_rgb = img[y1:y2, x1:x2]
        crop_bg = (crop_rgb[:, :, 0] > 240) & (crop_rgb[:, :, 1] > 240) & (crop_rgb[:, :, 2] > 240)
        
        # Build transparent BGRA
        crop_bgra = np.zeros((y2 - y1, x2 - x1, 4), dtype=np.uint8)
        crop_bgra[:, :, :3] = crop_rgb
        crop_bgra[:, :, 3] = (~crop_bg).astype(np.uint8) * 255

        # Smooth edges
        alpha = crop_bgra[:, :, 3]
        alpha_blurred = cv2.GaussianBlur(alpha, (3, 3), 0)
        crop_bgra[:, :, 3] = alpha_blurred

        out_name = f"{name}.png"
        out_path = os.path.join(OUT_DIR, out_name)
        
        # Save PNG with unicode support
        ok, buf = cv2.imencode(".png", crop_bgra)
        if ok:
            buf.tofile(out_path)
            extracted_count += 1
            print(f"  ✓ {out_name:28s}: {bw}x{bh} -> {desc}")

            metadata[name] = {
                "file": out_name,
                "row": r_idx + 1,
                "col": c_idx + 1,
                "semantic_description": desc,
                "anchor_text": anchor,
                "orig_box": [int(x1), int(y1), int(x2 - x1), int(y2 - y1)],
                "orig_size": [int(x2 - x1), int(y2 - y1)],
                "area": int(area)
            }

# Also ensure title banner is preserved
banner_path = os.path.join(OUT_DIR, "r0_00_title_banner.png")
metadata["r0_00_title_banner"] = {
    "file": "r0_00_title_banner.png",
    "row": 0,
    "col": 0,
    "semantic_description": "شعار العنوان الرئيسي بلا مأوى",
    "anchor_text": "بلا مأوى",
    "orig_box": [1128, 180, 1000, 220],
    "orig_size": [1000, 220],
    "area": 220000
}

meta_out_path = os.path.join(OUT_DIR, "metadata.json")
with open(meta_out_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print(f"\n🎉 Successfully extracted {extracted_count} clean organic assets + metadata.json!")
