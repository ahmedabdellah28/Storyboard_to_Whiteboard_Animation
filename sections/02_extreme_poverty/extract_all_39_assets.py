import cv2
import numpy as np
import os
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "02_extreme_poverty")
STORYBOARD_PATH = os.path.join(SEC_DIR, "storyboard.png")
OUT_DIR = os.path.join(SEC_DIR, "assets")
os.makedirs(OUT_DIR, exist_ok=True)

img = cv2.imread(STORYBOARD_PATH)
h, w = img.shape[:2]

# Exact cell intervals (x1, x2) for each row from column valley analysis
row_specs = [
    # Row 1 (y: 10 .. 230) - 8 cells
    (1, 10, 230, [
        (16, 273),
        (280, 540),
        (550, 753),
        (757, 904),
        (930, 1053),
        (1072, 1149),
        (1204, 1339),
        (1351, 1525)
    ]),
    # Row 2 (y: 235 .. 440) - 6 cells
    (2, 235, 440, [
        (26, 252),
        (279, 572),
        (595, 775),
        (817, 949),
        (981, 1132),
        (1183, 1507)
    ]),
    # Row 3 (y: 445 .. 630) - 8 cells
    (3, 445, 630, [
        (23, 274),
        (290, 513),
        (525, 565),
        (569, 732),
        (761, 892),
        (901, 975),
        (979, 1170),
        (1229, 1491)
    ]),
    # Row 4 (y: 630 .. 815) - 9 cells
    (4, 630, 815, [
        (18, 140),
        (148, 279),
        (291, 416),
        (434, 510),
        (529, 560),
        (567, 699),
        (732, 1117),
        (1145, 1262),
        (1290, 1518)
    ]),
    # Row 5 (y: 815 .. 1020) - 8 cells
    (5, 815, 1020, [
        (22, 255),
        (285, 451),
        (482, 705),
        (727, 961),
        (965, 1003),
        (1003, 1079),
        (1095, 1274),
        (1281, 1525)
    ])
]

# Manifest definitions: (aid, desc, anchor_text)
manifest_definitions = [
    # Row 1
    [
        ("r1_01_title_banner", "عنوان الطبقة الثانية: الفقر المدقع", "الطبقة الثانية: الفقر المدقع"),
        ("r1_02_crowded_room", "غرفة صغيرة مستأجرة أو شقة زحمة", "ممكن تصحى في غرفة صغيرة مستأجرة بالأسبوع أو شقة زحمة"),
        ("r1_03_broken_ac", "مرتبة على الأرض ومكيف أو دفاية خربانة", "مرتبة على الأرض وأحياناً المكيف أو الدفاية خربانة"),
        ("r1_04_prepaid_phone", "تشييك جوال مسبق الدفع", "أول شيء تشيك على جوالك مسبق الدفع: هل الخدمة لسه شغالة؟"),
        ("r1_05_counting_tickets", "عد تذاكر الباص في المحفظة", "بعدها تعد تذاكر الباص اللي باقي في محفظتك"),
        ("r1_06_plan_budget", "تخطيط اليوم حول الفلوس", "وتبدأ تخطط يومك حول الفلوس"),
        ("r1_07_basic_breakfast", "الفطور الأساسي: شوفان بيض توست", "الفطور أساسي: شوفان، بيض، توست، مقاضي بسيطة"),
        ("r1_08_coupons_charity", "كوبونات وبطاقات التموين والجمعيات", "تستخدم كوبونات، وبطاقات التموين، ومواعيد الجمعيات الخيرية"),
    ],
    # Row 2
    [
        ("r2_01_kids_school_meals", "اعتماد أكل الأطفال على المدرسة وسناك البيت", "وإذا عندك أطفال ممكن يعتمد جزء من أكلهم على وجبات المدرسة"),
        ("r2_02_waiting_delayed_bus", "المشوار للدوام وانتظار باص يتأخر", "المشوار للدوام ياخذ وقت.. تنتظر باص يتأخر"),
        ("r2_03_broken_car_light", "سيارة متهالكة ولمبة المكينة شغالة", "أو تسوق سيارة متهالكة ولمبة المكينة فيها شغالة"),
        ("r2_04_unpredictable_schedule", "ساعات الدوام المتغيرة كل أسبوع", "ساعات دوامك ممكن تتغير كل أسبوع.. يوم يطلبونك ويوم ما يطلبونك"),
        ("r2_05_extra_shift_work", "الموافقة على أي شفت إضافي أو شغل يومي", "ولهذا تقول نعم لأي شفت إضافي أو شغل يومي تقدر عليه"),
        ("r2_06_tips_overtime", "الإكراميات والأوفر تايم لتشغيل الكهرباء", "الإكراميات والأوفر تايم هنا مو رفاهية.. هي اللي تخلي الكهرب شغال"),
    ],
    # Row 3
    [
        ("r3_01_bills_puzzle", "الفواتير ولغز كل شهر", "الفواتير نفسها صارت لغز تحله كل شهر"),
        ("r3_02_rent_electric_bills", "الإيجار والكهرباء المتأخرة", "الإيجار له موعد، الكهرباء متأخرة، والفاتورة الثانية تنتظر"),
        ("r3_03_less_painful_fine", "اختيار الغرامة الأقل وجعاً", "تختار أي غرامة توجع أقل"),
        ("r3_04_money_order", "شراء حوالة مالية لتجنب رسوم البنك", "تشتري حوالة مالية لأنك تبي تتجنب رسوم البنك"),
        ("r3_05_paperwork_clinic_wait", "الأوراق التي لا تنتهي وموعد العيادة", "والأوراق ما تخلص.. الصحة؟ موعد عيادة بعد أسابيع"),
        ("r3_06_emergency_pain", "زيارة الطوارئ عند اشتداد الألم", "أو طوارئ لما الألم يصير أقوى من الانتظار"),
        ("r3_07_limited_insurance", "تأمين محدود أو عالي التحمل", "والتأمين، إذا موجود، ممكن يكون محدود أو عالي التحمل"),
        ("r3_08_postpone_dental", "تأجيل إصلاح الأسنان للأولويات", "حتى إصلاح الأسنان يتأجل لأن عندك أشياء أهم"),
    ],
    # Row 4
    [
        ("r4_01_laundromat_cost", "الغسيل يحتاج فلوس ووقت", "الغسيل يحتاج فلوس ووقت"),
        ("r4_02_laundromat_wifi", "مشوار المغسلة والاستفادة من الواي فاي", "فتجمعه مع مشوار المغسلة وتستفيد من الواي فاي المجاني"),
        ("r4_03_job_search_wifi", "البحث عن وظائف عبر الإنترنت", "عشان تدور وظائف"),
        ("r4_04_youtube_diy_repair", "التعلم من يوتيوب تصليح الأغراض", "وتتعلم من يوتيوب كيف تصلح أغراضك بشطرطون وصمغ"),
        ("r4_05_duct_tape_glue", "تصليح الأغراض بالشطرطون والصمغ", "بشطرطون وصمغ"),
        ("r4_06_extended_lifespan", "عمر أطول مما يستحق لكل شيء", "هنا كل شيء له عمر أطول مما يستحق"),
        ("r4_07_soap_gas_data", "اقتصاد الصابون والبنزين وبيانات الجوال", "الصابون.. البنزين.. بيانات الجوال"),
        ("r4_08_patience_limit", "حتى الصبر له حدود واستهلاك", "حتى الصبر"),
        ("r4_09_night_schedule_prep", "تشييك جدول بكرة بالليل", "وبالليل تشيك جدول بكرة"),
    ],
    # Row 5
    [
        ("r5_01_two_alarms", "ضبط منبهين للاستيقاظ", "تضبط منبهين"),
        ("r5_02_simple_todo_list", "قائمة بسيطة لمهام الغد", "وتسوي قائمة بسيطة"),
        ("r5_03_todo_call", "مهمة اتصال", "اتصال"),
        ("r5_04_todo_appointment", "مهمة موعد", "موعد"),
        ("r5_05_todo_charity", "مهمة مراجعة الجمعية", "جمعية"),
        ("r5_06_todo_work", "مهمة الشغل", "شغل"),
        ("r5_07_sleeping_night", "النوم الليلي المتعب", "وبعدها تنام"),
        ("r5_08_daily_race_cycle", "تكرار نفس السباق يومياً", "لأن بكرة عندك نفس السباق"),
    ]
]

metadata = {}
extracted_count = 0

print("=" * 80)
print("🎨 EXTRACTING 100% OF SECTION 02 STORYBOARD ASSETS (ZERO-BOX ORGANIC MASKING)")
print("=" * 80)

for r_idx, (r_num, y1, y2, intervals) in enumerate(row_specs):
    defs = manifest_definitions[r_idx]
    print(f"\n--- Row {r_num}: Extracting {len(intervals)} elements ---")
    
    for c_idx, (x1, x2) in enumerate(intervals):
        aid, desc, anchor = defs[c_idx]
        
        # Add small padding
        pad = 4
        px1 = max(0, x1 - pad)
        py1 = max(0, y1 - pad)
        px2 = min(w, x2 + pad)
        py2 = min(h, y2 + pad)
        
        crop_rgb = img[py1:py2, px1:px2]
        
        # Build transparent mask: whiteboard pure white background -> 0
        gray = cv2.cvtColor(crop_rgb, cv2.COLOR_BGR2GRAY)
        is_fg = gray < 240
        
        # Morphological feathering / clean contour
        mask = is_fg.astype(np.uint8) * 255
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
        
        # Crop tight around actual content
        ys, xs = np.where(mask > 0)
        if len(xs) > 0 and len(ys) > 0:
            tx1, tx2 = np.min(xs), np.max(xs)
            ty1, ty2 = np.min(ys), np.max(ys)
            
            tight_crop = crop_rgb[ty1:ty2+1, tx1:tx2+1]
            tight_mask = mask[ty1:ty2+1, tx1:tx2+1]
            
            # 4-channel BGRA
            bgra = np.dstack([tight_crop, tight_mask])
            out_file = f"{aid}.png"
            cv2.imwrite(os.path.join(OUT_DIR, out_file), bgra)
            
            actual_w = tx2 - tx1 + 1
            actual_h = ty2 - ty1 + 1
            area = int(np.count_nonzero(tight_mask))
            
            metadata[aid] = {
                "file": out_file,
                "row": r_num,
                "col": c_idx + 1,
                "desc": desc,
                "anchor_text": anchor,
                "orig_box": [int(px1 + tx1), int(py1 + ty1), int(actual_w), int(actual_h)],
                "orig_size": [int(actual_w), int(actual_h)],
                "area": area,
                "drawing_demand": 1.5
            }
            extracted_count += 1
            print(f"  ✓ [{aid:<26}] {actual_w:3d}x{actual_h:3d} | {desc}")

# Special Title Banner: Row 1 Item 1
metadata["r0_00_title_banner"] = {
    "file": "r0_00_title_banner.png",
    "row": 0,
    "col": 0,
    "desc": "عنوان القسم: الفقر المدقع",
    "anchor_text": "الفقر المدقع",
    "orig_box": [16, 16, 258, 201],
    "orig_size": [258, 201],
    "area": 36000,
    "drawing_demand": 1.8
}
# Also copy r1_01_title_banner to r0_00_title_banner.png
import shutil
shutil.copyfile(os.path.join(OUT_DIR, "r1_01_title_banner.png"), os.path.join(OUT_DIR, "r0_00_title_banner.png"))

with open(os.path.join(OUT_DIR, "metadata.json"), "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print(f"\n🎉 Successfully extracted {extracted_count} assets + title banner to: {OUT_DIR}")
print(f"✓ Saved metadata to: {os.path.join(OUT_DIR, 'metadata.json')}")
