import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "02_extreme_poverty")
META_PATH = os.path.join(SEC_DIR, "assets", "metadata.json")
TIMING_PATH = os.path.join(SEC_DIR, "timing", "drawing_timeline.json")
LAYOUT_PATH = os.path.join(SEC_DIR, "placed_elements_layout.json")

with open(META_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

# Comprehensive Sentence-Level Storyboard Manifest for Section 02
# 37 True Visual Items across 15 Micro-Zones
# 100% Speech-Synced to rapid audio beats
sentence_manifest = [
    # --- Zone 1: Section Title & Barely Safe Roof ---
    ("r0_00_title_banner",        0.00,   2.40, "الطبقة الثانية: الفقر المدقع", "zone_01", "outside_in_pen", 5),
    ("r1_01_roof_shack",          3.80,   6.00, "هنا عندك سقف، لكنه بالكاد يعتبر أمان", "zone_01", "outside_in_pen", 5),

    # --- Zone 2: Crowded Room, Mattress & Broken AC ---
    ("r1_02_crowded_room",        8.90,  11.40, "ممكن تصحى في غرفة صغيرة مستأجرة بالأسبوع أو شقة زحمة", "zone_02", "outside_in_pen", 5),
    ("r1_03_mattress_floor",     15.00,  16.80, "مرتبة على الأرض", "zone_02", "slide_down", 4),
    ("r1_04_broken_ac_heater",   16.80,  18.20, "وأحياناً المكيف أو الدفاية خربانة", "zone_02", "slide_down", 4),

    # --- Zone 3: Checking Phone, No Signal, Counting Wallet & Bus Tickets ---
    ("r1_05_check_phone",        18.30,  20.00, "أول شيء تشيك على جوالك مسبق الدفع", "zone_03", "outside_in_pen", 5),
    ("r1_06_phone_no_service",   20.10,  21.30, "هل الخدمة لسه شغالة؟", "zone_03", "jelly_pop", 4),
    ("r1_07_wallet_money",       21.30,  22.15, "بعدها تعد تذاكر الباص اللي باقي في محفظتك", "zone_03", "slide_down", 4),
    ("r1_08_bus_tickets",        22.15,  23.30, "تذاكر الباص", "zone_03", "slide_down", 4),

    # --- Zone 4: Planning Budget, Breakfast & Groceries ---
    ("r2_01_plan_day_budget",    23.30,  25.20, "وتبدأ تخطط يومك حول الفلوس", "zone_04", "outside_in_pen", 5),
    ("r2_02_breakfast_oats_eggs",25.25,  27.45, "الفطور أساسي: شوفان، بيض، توست", "zone_04", "outside_in_pen", 5),
    ("r2_03_grocery_basket",     27.50,  28.60, "مقاضي بسيطة", "zone_04", "slide_down", 4),

    # --- Zone 5: Coupons, Charity & Kids School Meals ---
    ("r2_04_coupons_rations",    28.60,  30.20, "تستخدم كوبونات، وبطاقات التموين", "zone_05", "outside_in_pen", 5),
    ("r2_05_charity_box",        30.25,  32.20, "ومواعيد الجمعيات الخيرية.. كل شيء محسوب", "zone_05", "slide_down", 4),
    ("r2_06_kids_school_snacks", 32.40,  35.40, "وإذا عندك أطفال ممكن يعتمد جزء من أكلهم على وجبات المدرسة", "zone_05", "outside_in_pen", 5),

    # --- Zone 6: Delayed Bus & Broken Car Engine ---
    ("r3_01_waiting_delayed_bus",38.45,  41.05, "المشوار للدوام ياخذ وقت.. تنتظر باص يتأخر", "zone_06", "outside_in_pen", 5),
    ("r3_02_broken_car_engine",  41.15,  43.95, "أو تسوق سيارة متهالكة ولمبة المكينة فيها شغالة", "zone_06", "outside_in_pen", 5),

    # --- Zone 7: Unpredictable Schedule, Extra Shift & Overtime & Tips ---
    ("r3_03_unpredictable_schedule", 45.75, 48.35, "ساعات دوامك ممكن تتغير كل أسبوع", "zone_07", "outside_in_pen", 5),
    ("r3_04_extra_shift_thumbsup",   50.00, 52.40, "ولهذا تقول نعم لأي شفت إضافي أو شغل يومي تقدر عليه", "zone_07", "outside_in_pen", 5),
    ("r3_05_overtime_clock",         53.80, 55.40, "والأوفر تايم..", "zone_07", "jelly_pop", 4),
    ("r3_06_tips_money",             55.60, 57.80, "الإكراميات والأوفر تايم هنا مو رفاهية", "zone_07", "slide_down", 4),

    # --- Zone 8: Bills Puzzle, Rent Due Date & Late Electricity ---
    ("r3_07_bills_puzzle",       58.55,  60.50, "الفواتير نفسها صارت لغز تحله كل شهر", "zone_08", "outside_in_pen", 5),
    ("r4_01_rent_due_date",      60.55,  61.55, "الإيجار له موعد", "zone_08", "outside_in_pen", 5),
    ("r4_02_late_electric_coins",61.60,  63.40, "الكهرباء متأخرة.. والفاتورة الثانية تنتظر", "zone_08", "slide_down", 4),

    # --- Zone 9: Fine App Payment & Money Transfer ---
    ("r4_03_fine_app_payment",   63.50,  65.70, "تختار أي غرامة توجع أقل.. حتى طريقة الدفع تفكر فيها", "zone_09", "outside_in_pen", 5),
    ("r4_04_money_transfer",     66.80,  69.20, "تشتري حوالة مالية لأنك تبي تتجنب رسوم البنك", "zone_09", "slide_down", 4),

    # --- Zone 10: Endless Paperwork, Clinic/ER, Toothache & Dental Postponed ---
    ("r4_05_endless_paperwork",  69.60,  71.10, "والأوراق ما تخلص", "zone_10", "outside_in_pen", 5),
    ("r4_06_clinic_er_hospital", 71.30,  73.90, "الصحة؟ موعد عيادة بعد أسابيع أو طوارئ لما الألم يصير أقوى", "zone_10", "outside_in_pen", 5),
    ("r4_07_toothache_pain",     75.20,  77.60, "والتأمين إذا موجود ممكن يكون محدود أو عالي التحمل", "zone_10", "slide_down", 4),
    ("r4_08_dental_postponed",   79.60,  81.80, "حتى إصلاح الأسنان يتأجل لأن عندك أشياء أهم", "zone_10", "slide_down", 4),

    # --- Zone 11: Laundromat & Free WiFi Job Search ---
    ("r5_01_laundromat_coins",   82.45,  84.65, "الغسيل يحتاج فلوس ووقت", "zone_11", "outside_in_pen", 5),
    ("r5_02_laundromat_wifi_jobs", 85.00, 87.80, "فتجمعه مع مشوار المغسلة وتستفيد من الواي فاي المجاني عشان تدور وظائف", "zone_11", "slide_down", 4),

    # --- Zone 12: YouTube Repair & DIY Extended Lifespan ---
    ("r5_03_youtube_diy_repair", 89.10,  92.30, "وتتعلم من يوتيوب كيف تصلح أغراضك بشطرطون وصمغ", "zone_12", "outside_in_pen", 5),

    # --- Zone 13: Soap/Gas/Data & Patience Limit ---
    ("r5_04_soap_gas_data",      93.85,  96.25, "الصابون.. البنزين.. بيانات الجوال", "zone_13", "outside_in_pen", 5),
    ("r5_05_patience_limit",     96.45,  97.85, "حتى الصبر", "zone_13", "outside_in_pen", 5),

    # --- Zone 14: Night Schedule Planning & Checklist ---
    ("r5_06_night_schedule_planning", 97.80, 101.00, "وبالليل تشيك جدول بكرة تضبط منبهين وتسوي قائمة بسيطة", "zone_14", "outside_in_pen", 5),

    # --- Zone 15: Sleeping & Daily Hamster Wheel Race ---
    ("r5_07_sleeping_daily_race", 103.40, 106.00, "وبعدها تنام لأن بكرة عندك نفس السباق", "zone_15", "outside_in_pen", 5),
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
    "section_id": "02_extreme_poverty",
    "duration": 106.56,
    "events": drawing_events
}

with open(TIMING_PATH, "w", encoding="utf-8") as f:
    json.dump(timeline_data, f, indent=2, ensure_ascii=False)
print(f"✓ Saved {len(drawing_events)} sentence-aligned events to: {TIMING_PATH}")

# 2. Generate placed_elements_layout.json
CAM_ZOOM = 0.68
FIXED_Y = 800.0

zone_names = [f"zone_{i:02d}" for i in range(1, 16)]

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
    
    num_elems = len(aids)
    if z_name == "zone_01":
        elem_scale = 3.8
        spacing = 100.0
    elif num_elems <= 2:
        elem_scale = 3.8
        spacing = 140.0
    elif num_elems == 3:
        elem_scale = 3.4
        spacing = 100.0
    else: # 4 elements
        elem_scale = 3.0
        spacing = 80.0

    cur_x = cur_zone_x
    for aid in aids:
        meta = metadata.get(aid, {})
        orig_size = meta.get("orig_size", [150, 150])

        if aid == "r0_00_title_banner":
            w_px = 1100.0
            h_px = 242.0
            x_px = cur_zone_x + 100.0
            y_px = 180.0
        elif aid == "r1_01_roof_shack":
            w_px = float(orig_size[0]) * elem_scale
            h_px = float(orig_size[1]) * elem_scale
            x_px = cur_zone_x + 150.0
            y_px = 880.0 - (h_px / 2.0)
            cur_x = max(cur_x, x_px + w_px + spacing)
        else:
            w_px = float(orig_size[0]) * elem_scale
            h_px = float(orig_size[1]) * elem_scale
            y_px = FIXED_Y - (h_px / 2.0)
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

    non_banner_elems = [e for e in placed_elements[z_name] if e["aid"] != "r0_00_title_banner"]
    if non_banner_elems:
        min_x = min(e["x"] for e in non_banner_elems)
        max_x = max(e["x"] + e["w"] for e in non_banner_elems)
        mid_x = (min_x + max_x) / 2.0
    else:
        mid_x = cur_zone_x + 650.0

    zones_dict[z_name] = {
        "cam_pos": [round(mid_x, 1), FIXED_Y],
        "zoom": CAM_ZOOM
    }

    cur_zone_x = max(cur_x, mid_x + 1200.0) + 1600.0

layout_data = {
    "section_id": "02_extreme_poverty",
    "fixed_y": FIXED_Y,
    "cam_zoom": CAM_ZOOM,
    "zones": zones_dict,
    "elements": placed_elements
}

with open(LAYOUT_PATH, "w", encoding="utf-8") as f:
    json.dump(layout_data, f, indent=2, ensure_ascii=False)
print(f"✓ Saved layout with {len(zone_names)} zones to: {LAYOUT_PATH}")

align_out = os.path.join(SEC_DIR, "alignment_data.json")
align_data = {
    "duration_sec": 106.56,
    "staging_specs": staging_specs
}
with open(align_out, "w", encoding="utf-8") as f:
    json.dump(align_data, f, indent=2, ensure_ascii=False)
print(f"✓ Saved alignment specs to: {align_out}")

print("\n🎉 Section 02 complete 37-item pipeline structure rebuilt successfully!")
