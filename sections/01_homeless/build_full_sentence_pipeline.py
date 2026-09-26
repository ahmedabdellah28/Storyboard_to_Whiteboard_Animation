import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "01_homeless")
META_PATH = os.path.join(SEC_DIR, "assets", "metadata.json")
TIMING_PATH = os.path.join(SEC_DIR, "timing", "drawing_timeline.json")
LAYOUT_PATH = os.path.join(SEC_DIR, "placed_elements_layout.json")

# Load existing metadata
with open(META_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

# Comprehensive Sentence-Level Storyboard Manifest (43 Events across 17 focused zones)
# (aid, start_s, end_s, anchor_text, zone, anim_type, depth)
# start_s is calibrated to the exact start of speech for each concept (no late appearance)
sentence_manifest = [
    # --- Zone 1A: Waking before dawn & street noise ---
    ("r0_00_title_banner",    0.00,   1.80, "بلا مأوى", "zone_1A", "outside_in_pen", 5),
    ("r1_01_waking_alarm",    1.80,   3.40, "تصحى قبل الفجر", "zone_1A", "outside_in_pen", 5),
    ("r1_02_city_noise",      3.40,   5.10, "لأن الشارع يصير مزعج مع بداية حركة المدينة", "zone_1A", "slide_down", 4),

    # --- Zone 1B: Sleep hard surfaces & body pain ---
    ("r1_03_body_pain",       5.26,   6.80, "جسمك مكسر ومتصلب", "zone_1B", "outside_in_pen", 5),
    ("r1_04_sleep_concrete",  6.80,   8.20, "من النوم على صبة", "zone_1B", "slide_down", 4),
    ("r1_05_sleep_bench",     8.20,   9.50, "أو كرسي حديقة", "zone_1B", "slide_down", 4),
    ("r1_06_sleep_shelter",   9.50,  10.72, "أو فرشة في ملجأ", "zone_1B", "slide_down", 4),

    # --- Zone 1C: Checking backpack & belongings ---
    ("r1_07_check_backpack", 10.72,  13.00, "أول شيء تسويه؟ تشيك على أغراضك القليلة", "zone_1C", "outside_in_pen", 5),
    ("r1_08_backpack_items", 13.00,  15.50, "وتتأكد إن ما انسرق منك شيء في الليل", "zone_1C", "slide_down", 4),

    # --- Zone 2A: Broken phone & battery ---
    ("r2_01_phone_broken",   16.22,  18.20, "إذا عندك جوال، غالباً يكون قديم", "zone_2A", "outside_in_pen", 5),
    ("r2_02_screen_cracked", 18.20,  19.80, "الشاشة مكسورة", "zone_2A", "jelly_pop", 4),
    ("r2_03_battery_dead",   19.80,  21.00, "والبطارية تفصل بسرعة", "zone_2A", "jelly_pop", 4),

    # --- Zone 2B: Searching wifi & charger struggle ---
    ("r2_04_search_wifi",    21.00,  23.20, "فتدور على واي فاي مجاني", "zone_2B", "outside_in_pen", 5),
    ("r2_05_wifi_icon",      23.20,  24.80, "كأنك تدور كنز", "zone_2B", "jelly_pop", 4),
    ("r2_06_charger_problem",25.00,  27.50, "والشاحن؟ مشكلة ثانية لحالها", "zone_2B", "outside_in_pen", 5),

    # --- Zone 2C: Bathroom search & washing in sink ---
    ("r2_07_goto_bathroom",  28.00,  33.00, "بعدها أول هدف: حمام ومويه... تروح مطعم محطة", "zone_2C", "outside_in_pen", 5),
    ("r2_08_wash_face_sink", 33.44,  37.50, "تدخل بسرعة تغسل وجهك وجسمك", "zone_2C", "outside_in_pen", 5),
    ("r2_09_shower_clean",   37.50,  41.40, "بأبسط طريقة ممكنة وتحاول ترتب نفسك", "zone_2C", "slide_down", 4),

    # --- Zone 3A: Clean clothes as rare currency ---
    ("r3_01_clean_shirt",    41.40,  43.60, "الملابس النظيفة هنا مو شيء عادي", "zone_3A", "outside_in_pen", 5),
    ("r3_02_folded_clothes", 43.60,  45.80, "الملابس النظيفة عملة نادرة", "zone_3A", "slide_down", 4),

    # --- Zone 3B: Food seeking & charity breakfast ---
    ("r3_05_eating_sandwich",46.16,  48.10, "بعدها يجي الأكل", "zone_3B", "outside_in_pen", 5),
    ("r3_06_charity_food",   48.10,  50.20, "تدور على فطور مجاني في جمعية خيرية", "zone_3B", "outside_in_pen", 5),

    # --- Zone 3C: Cheap meals, groceries & no kitchen/home ---
    ("r3_07_soup_kitchen",       50.40,  53.50, "أو أرخص وجبة تقدر تشتريها بالدولارات القليلة", "zone_3C", "outside_in_pen", 5),
    ("r3_08_grocery_card",       53.96,  58.20, "وإذا عندك بطاقة تموين تشتري مقاضي بسيطة", "zone_3C", "outside_in_pen", 5),
    ("r3_09_no_kitchen_home",    58.72,  62.00, "لكن عندك مشكلة: أنت ما تملك مطبخ فتاكل اللي تقدر تشيله معك", "zone_3C", "slide_down", 4),

    # --- Zone 4A: Hunger, safety plan & park bench ---
    ("r4_01_hunger_craving", 62.00,  65.50, "فتاكل اللي تقدر تشيله معك... الجوع دائماً قريب", "zone_4A", "outside_in_pen", 5),
    ("r4_02_safety_planning",66.50,  69.80, "حتى خطة يومك ما تنبني على الراحة تنبني على الأمان", "zone_4A", "outside_in_pen", 5),
    ("r4_03_bench_rest",     70.00,  73.00, "والأماكن اللي تقدر تجلس فيها بدون ما أحد يطردك", "zone_4A", "slide_down", 4),

    # --- Zone 4B: Public library treasure & job search ---
    ("r4_04_library_books",  73.50,  76.00, "المكتبة العامة بالنسبة لك كنز", "zone_4B", "outside_in_pen", 5),
    ("r4_05_bench_chair",    76.02,  78.50, "كرسي... واي فاي... فيش كهرباء", "zone_4B", "slide_down", 4),
    ("r4_06_laptop_search",  78.50,  80.80, "ومكان تقدر فيه تدور على شغل", "zone_4B", "outside_in_pen", 5),

    # --- Zone 5A: Street begging & slow coins ---
    ("r5_01_begging_cup",    81.00,  83.50, "حتى لو كنت تتسول، تختار زاوية فيها حركة ناس", "zone_5A", "outside_in_pen", 5),
    ("r5_02_coins_money",    83.74,  85.80, "الفلوس القليلة تتجمع ببطء", "zone_5A", "jelly_pop", 4),
    ("r5_03_day_no_money",   86.00,  88.50, "وأحياناً يمر يوم كامل وما يجيك ولا شيء", "zone_5A", "slide_down", 4),

    # --- Zone 5B: Missing ID card & legal court documents & no address ---
    ("r5_04_missing_id_card",88.94,  93.00, "ثم تجي المشكلة الأكبر: الأوراق الرسمية. ما عندك هوية؟", "zone_5B", "outside_in_pen", 5),
    ("r5_05_court_documents",93.36,  99.00, "يصير الوصول أصعب... تبي تطلع هوية تحتاج وقت ورسوم", "zone_5B", "slide_down", 4),
    ("r5_06_no_address",     99.50, 103.14, "وأحياناً عنوان وأنت أصلاً ما عندك عنوان", "zone_5B", "outside_in_pen", 5),

    # --- Zone 5C: Health, Clinic & Medicine (قبل جزء النوم) ---
    ("r5_07_hospital_clinic",    103.14, 107.00, "الصحة بعد موضوع ثاني... زيارتك للطوارئ هي الحل الوحيد", "zone_5C", "outside_in_pen", 5),
    ("r5_08_free_clinic",        107.20, 109.08, "أو تنتظر عيادة مجانية ساعات", "zone_5C", "outside_in_pen", 5),
    ("r5_09_medicine_treatment", 109.08, 112.14, "حتى الأدوية تحتاج تحفظها والنوم نفسه صعب تحفظه", "zone_5C", "slide_down", 4),

    # --- Zone 6A: Shelter rules, lines & street danger ---
    ("r6_01_shelter_bunk",   112.14, 114.50, "وبالليل تبدأ نفس الدائرة: وين تنام؟", "zone_6A", "outside_in_pen", 5),
    ("r6_02_shelter_line",   114.50, 116.50, "الملجأ له قوانين وطوابير", "zone_6A", "outside_in_pen", 5),
    ("r6_03_street_sleeping",116.50, 117.80, "والشارع فيه ضوضاء", "zone_6A", "slide_down", 4),
    ("r6_04_siren_danger",   117.80, 118.76, "وخطر", "zone_6A", "jelly_pop", 4),

    # --- Zone 6B: Hiding valuables & light cautious sleep ---
    ("r6_05_hide_valuables", 118.76, 120.80, "تخبي أغراضك الثمينة داخل ملابسك", "zone_6B", "outside_in_pen", 5),
    ("r6_06_sleep_light",    120.80, 122.96, "وتنام نوم خفيف", "zone_6B", "slide_down", 4),

    # --- Zone 6C: Early sunrise walk & daily survival cycle ---
    ("r6_07_walk_sunrise",   122.96, 125.50, "وبكرة الصبح يجي بدري... وتعيد نفس الدوامة", "zone_6C", "outside_in_pen", 5),
    ("r6_08_survival_cycle", 126.20, 129.80, "مويه... أكل... أمان... وخطة تكمل فيها يوم واحد زيادة", "zone_6C", "outside_in_pen", 5),
]

# 1. Generate drawing_timeline.json
drawing_events = []
staging_specs = []
for i, item in enumerate(sentence_manifest, 1):
    aid, st, en, anchor, zone, anim_type, depth = item
    drawing_events.append({
        "id": f"D{i:03d}",
        "type": "reveal" if i == 1 else "draw",
        "asset_id": aid,
        "start_s": round(st, 3),
        "end_s": round(en, 3),
        "duration_s": round(en - st, 3),
        "trigger": "semantic",
        "anchor_text": anchor,
        "confidence": 0.99,
        "layer_order": i - 1
    })
    staging_specs.append([aid, round(st, 3), round(en - st, 3), anim_type, depth])

timeline_data = {
    "section_id": "01_homeless",
    "duration": 130.833,
    "events": drawing_events
}

with open(TIMING_PATH, "w", encoding="utf-8") as f:
    json.dump(timeline_data, f, indent=2, ensure_ascii=False)
print(f"✓ Saved {len(drawing_events)} sentence-aligned events to: {TIMING_PATH}")

# 2. Generate placed_elements_layout.json with PROMINENT, LARGE element sizes
CAM_ZOOM = 0.68
FIXED_Y = 800.0

zone_names = [
    "zone_1A", "zone_1B", "zone_1C",
    "zone_2A", "zone_2B", "zone_2C",
    "zone_3A", "zone_3B", "zone_3C",
    "zone_4A", "zone_4B",
    "zone_5A", "zone_5B", "zone_5C",
    "zone_6A", "zone_6B", "zone_6C"
]

zone_elements = {z: [] for z in zone_names}
for item in sentence_manifest:
    aid, st, en, anchor, zone, anim_type, depth = item
    zone_elements[zone].append(aid)

placed_elements = {}
zones_dict = {}

cur_zone_x = 600.0
for z_idx, z_name in enumerate(zone_names):
    aids = zone_elements[z_name]
    placed_elements[z_name] = []
    
    # Adaptive scale based on element density in zone so elements are large and prominent
    num_elems = len(aids)
    if num_elems <= 1:
        elem_scale = 4.2
        spacing = 150.0
    elif num_elems == 2:
        elem_scale = 3.8
        spacing = 140.0
    elif num_elems == 3:
        elem_scale = 3.5
        spacing = 110.0
    else: # 4 elements
        elem_scale = 3.1
        spacing = 90.0

    # Calculate widths and layout
    cur_x = cur_zone_x
    for aid in aids:
        meta = metadata.get(aid, {})
        orig_size = meta.get("orig_size", [150, 150])
        w_px = float(orig_size[0]) * elem_scale
        h_px = float(orig_size[1]) * elem_scale
        
        # Position centered around FIXED_Y
        y_px = FIXED_Y - (h_px / 2.0)
        
        # Title banner special case (top center of zone_1A)
        if aid == "r0_00_title_banner":
            w_px = 1350.0
            h_px = 270.0
            y_px = 220.0
            x_px = cur_zone_x + 150.0
        else:
            x_px = cur_x
            cur_x += w_px + spacing
            
        placed_elements[z_name].append({
            "aid": aid,
            "file": f"{aid}.png",
            "x": round(x_px, 1),
            "y": round(y_px, 1),
            "w": round(w_px, 1),
            "h": round(h_px, 1),
            "cx": round(x_px + w_px / 2.0, 1),
            "cy": round(y_px + h_px / 2.0, 1),
            "zone": z_name
        })

    # Zone camera position centered on its elements
    non_banner_elems = [e for e in placed_elements[z_name] if e["aid"] != "r0_00_title_banner"]
    if non_banner_elems:
        min_x = min(e["x"] for e in non_banner_elems)
        max_x = max(e["x"] + e["w"] for e in non_banner_elems)
        mid_x = (min_x + max_x) / 2.0
    else:
        mid_x = cur_zone_x + 800.0

    zones_dict[z_name] = {
        "cam_pos": [round(mid_x, 1), FIXED_Y],
        "zoom": CAM_ZOOM
    }

    # Advance to next zone with clean camera gap
    cur_zone_x = max(cur_x, mid_x + 1200.0) + 1600.0

layout_data = {
    "section_id": "01_homeless",
    "fixed_y": FIXED_Y,
    "cam_zoom": CAM_ZOOM,
    "zones": zones_dict,
    "elements": placed_elements
}

with open(LAYOUT_PATH, "w", encoding="utf-8") as f:
    json.dump(layout_data, f, indent=2, ensure_ascii=False)
print(f"✓ Saved layout with {len(zone_names)} zones to: {LAYOUT_PATH}")

# 3. Update alignment_data.json
align_out = os.path.join(SEC_DIR, "alignment_data.json")
align_data = {
    "duration_sec": 130.833,
    "staging_specs": staging_specs
}
with open(align_out, "w", encoding="utf-8") as f:
    json.dump(align_data, f, indent=2, ensure_ascii=False)
print(f"✓ Saved alignment specs to: {align_out}")

print("\n🎉 Upgraded 17-zone high-impact pipeline structure built successfully!")
