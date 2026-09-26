import os
import sys
import json
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "03_working_poor")
META_PATH = os.path.join(SEC_DIR, "assets", "metadata.json")
OUT_LAYOUT = os.path.join(SEC_DIR, "placed_elements_layout.json")

with open(META_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

SCALE = 2.8
FIXED_Y = 800.0
CAM_ZOOM = 0.58
WORLD_HALF = (1920.0 / 2.0) / CAM_ZOOM  # ~1655.17 px

horizontal_spec = [
    # Zone 1A (5:30 AM alarm, small rented apartment, checking bank app)
    ('zone_1A', 500.0, [
        ('r1_01_alarm_wake', 140),
        ('r1_02_small_apartment', 140),
        ('r1_03_check_bank_app', 0)
    ]),
    # Zone 1B (Home coffee/lunch prep, public bus commute, counting fuel budget)
    ('zone_1B', 5200.0, [
        ('r1_04_coffee_meal_prep', 140),
        ('r1_05_bus_commute', 140),
        ('r1_06_old_car_fuel', 0)
    ]),
    # Zone 2A (Service jobs: cashier, warehouse logistics, line cook, elderly caregiver)
    ('zone_2A', 9800.0, [
        ('r2_01_cashier_job', 120),
        ('r2_02_warehouse_job', 120),
        ('r2_03_restaurant_job', 120),
        ('r2_04_caregiver_job', 0)
    ]),
    # Zone 2B (Strict manager rules, eating packed lunch, next week shifts schedule)
    ('zone_2B', 14200.0, [
        ('r2_05_shift_checklist', 140),
        ('r2_06_eating_lunchbox', 140),
        ('r2_07_shifts_schedule', 0)
    ]),
    # Zone 3A (Delayed doctor visit, high deductible stress, bargain shopping)
    ('zone_3A', 18800.0, [
        ('r3_01_doctor_visit', 140),
        ('r3_02_family_thinking', 140),
        ('r3_03_shopping_discounts', 0)
    ]),
    # Zone 3B (Store loyalty card, juggling overdue bills, 20-dollar emergency jar)
    ('zone_3B', 23200.0, [
        ('r3_04_loyalty_card', 140),
        ('r3_05_utility_bills', 140),
        ('r3_06_savings_jar', 0)
    ]),
    # Zone 4A (Cooking humble dinner, laundry uniform drying, bill notices in mail)
    ('zone_4A', 28200.0, [
        ('r4_01_cooking_dinner', 140),
        ('r4_02_laundry_hanging', 140),
        ('r4_03_mail_notices', 0)
    ]),
    # Zone 4B (Texting for weekend side gig, certificate course study, 6-hour sleep)
    ('zone_4B', 33200.0, [
        ('r4_04_side_job_msg', 140),
        ('r4_05_online_course', 140),
        ('r4_06_sleep_night', 0)
    ])
]

placed_elements = {}
zones_info = {}

print("=" * 80)
print("📐 SECTION 03 PURE HORIZONTAL CINEMATIC LAYOUT (CONSTANT Y = 800.0)")
print("=" * 80)

for z_name, start_x, elements in horizontal_spec:
    cur_x = start_x
    placed_elements[z_name] = []
    
    for eid, gap in elements:
        ow, oh = metadata[eid]['orig_size']
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
        'row_y': FIXED_Y,
        'cam_pos': [round(cam_x, 1), FIXED_Y],
        'span': [round(start_x, 1), round(end_x, 1)]
    }

    screen_left = cam_x - WORLD_HALF
    screen_right = cam_x + WORLD_HALF
    print(f"{z_name:10s}: [{start_x:.0f} .. {end_x:.0f}], CamX={cam_x:.1f} | Screen: [{screen_left:.1f} .. {screen_right:.1f}]")

out_data = {
    'elements': placed_elements,
    'zones': zones_info,
    'fixed_y': FIXED_Y,
    'scale': SCALE,
    'cam_zoom': CAM_ZOOM
}

with open(OUT_LAYOUT, "w", encoding="utf-8") as f:
    json.dump(out_data, f, indent=2, ensure_ascii=False)

print(f"\n✅ Pure horizontal layout saved: {OUT_LAYOUT}")
