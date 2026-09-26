import os
import sys
import json
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "05_middle_class")
META_PATH = os.path.join(SEC_DIR, "assets", "metadata.json")
OUT_LAYOUT = os.path.join(SEC_DIR, "placed_elements_layout.json")

with open(META_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

SCALE = 2.8
FIXED_Y = 800.0
CAM_ZOOM = 0.58
WORLD_HALF = (1920.0 / 2.0) / CAM_ZOOM  # ~1655.17 px

horizontal_spec = [
    # Zone 1A (Three bedroom home, stable mortgage lease)
    ('zone_1A', 500.0, [
        ('r1_01_three_bedroom_home', 160),
        ('r1_02_stable_mortgage_lease', 0)
    ]),
    # Zone 1B (Coffee routine, shared family calendar, fresh breakfast)
    ('zone_1B', 5200.0, [
        ('r1_03_coffee_official_routine', 140),
        ('r1_04_shared_family_calendar', 140),
        ('r1_05_fresh_healthy_breakfast', 0)
    ]),
    # Zone 2A (Clean car / reliable train, flexible office control)
    ('zone_2A', 10400.0, [
        ('r2_01_clean_car_reliable_train', 160),
        ('r2_02_flexible_office_control', 0)
    ]),
    # Zone 2B (Meetings and projects, paid vacations pension, long-term savings)
    ('zone_2B', 15000.0, [
        ('r2_03_meetings_and_projects', 140),
        ('r2_04_paid_vacations_pension', 140),
        ('r2_05_long_term_savings_goals', 0)
    ]),
    # Zone 3A (Lunch banking check, monthly installment, repair/tire fund)
    ('zone_3A', 20200.0, [
        ('r3_01_banking_app_lunch_check', 140),
        ('r3_02_monthly_installment_check', 140),
        ('r3_03_home_repair_car_tire_fund', 0)
    ]),
    # Zone 3B (Gym and sports with friends, home cooking & takeout)
    ('zone_3B', 25200.0, [
        ('r3_04_gym_and_friends_sports', 160),
        ('r3_05_home_cooking_and_takeout', 0)
    ]),
    # Zone 4A (Calling plumber, routine dentist, helping kids homework)
    ('zone_4A', 29800.0, [
        ('r4_01_calling_plumber_repair', 140),
        ('r4_02_routine_dentist_visit', 140),
        ('r4_03_helping_kids_homework', 0)
    ]),
    # Zone 4B (Online gifts, stability habit)
    ('zone_4B', 34800.0, [
        ('r4_04_birthday_gift_online', 160),
        ('r4_05_established_habit_stability', 0)
    ])
]

placed_elements = {}
zones_info = {}

print("=" * 80, flush=True)
print("📐 SECTION 05 PURE HORIZONTAL CINEMATIC LAYOUT (CONSTANT Y = 800.0)", flush=True)
print("=" * 80, flush=True)

for z_name, start_x, elements in horizontal_spec:
    cur_x = start_x
    placed_elements[z_name] = []
    
    for eid, gap in elements:
        item_meta = metadata[eid]
        ow = item_meta.get('width', 200)
        oh = item_meta.get('height', 200)
        w = ow * SCALE
        h = oh * SCALE
        y = FIXED_Y - h / 2.0
        placed_elements[z_name].append({
            'aid': eid,
            'file': f"{eid}.png",
            'x': round(cur_x, 1),
            'y': round(y, 1),
            'w': round(w, 1),
            'h': round(h, 1),
            'cx': round(cur_x + w / 2.0, 1),
            'cy': round(FIXED_Y, 1),
            'zone': z_name
        })
        cur_x += w + gap

    end_x = cur_x - (elements[-1][1] if elements else 0)
    cam_x = (start_x + end_x) / 2.0

    zones_info[z_name] = {
        'start_x': round(start_x, 1),
        'end_x': round(end_x, 1),
        'width': round(end_x - start_x, 1),
        'cam_pos': [round(cam_x, 1), FIXED_Y],
        'zoom': CAM_ZOOM,
        'visible_range_x': [round(cam_x - WORLD_HALF, 1), round(cam_x + WORLD_HALF, 1)]
    }

    print(f"  [{z_name}] {len(elements)} items | x: {start_x:7.1f} -> {end_x:7.1f} | Cam: ({cam_x:7.1f}, {FIXED_Y:.1f})", flush=True)

layout_output = {
    'fixed_y': FIXED_Y,
    'cam_zoom': CAM_ZOOM,
    'zones': zones_info,
    'elements': placed_elements
}

with open(OUT_LAYOUT, "w", encoding="utf-8") as f:
    json.dump(layout_output, f, ensure_ascii=False, indent=2)

print(f"\n✅ Section 05 pure horizontal layout successfully saved to {OUT_LAYOUT}", flush=True)
