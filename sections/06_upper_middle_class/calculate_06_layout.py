import os
import sys
import json
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "06_upper_middle_class")
META_PATH = os.path.join(SEC_DIR, "assets", "metadata.json")
OUT_LAYOUT = os.path.join(SEC_DIR, "placed_elements_layout.json")

with open(META_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

SCALE = 2.8
FIXED_Y = 800.0
CAM_ZOOM = 0.58
WORLD_HALF = (1920.0 / 2.0) / CAM_ZOOM  # ~1655.17 px

horizontal_spec = [
    # Zone 1A (Peaceful upscale home, smart home robot vacuum)
    ('zone_1A', 500.0, [
        ('r1_01_peaceful_upscale_home', 160),
        ('r1_02_smart_home_appliances', 0)
    ]),
    # Zone 1B (Coffee schedule, calendar & cleaner, automated savings)
    ('zone_1B', 5200.0, [
        ('r1_03_coffee_machine_schedule', 140),
        ('r1_04_calendar_and_cleaner', 140),
        ('r1_05_automated_bills_savings', 0)
    ]),
    # Zone 2A (Varied fresh breakfast, modern paid-off car)
    ('zone_2A', 10400.0, [
        ('r2_01_varied_fresh_breakfast', 160),
        ('r2_02_modern_paid_off_car', 0)
    ]),
    # Zone 2B (Expected costs, coding/leadership career, remote projects)
    ('zone_2B', 15200.0, [
        ('r2_03_expected_costs_insurance', 140),
        ('r2_04_professional_career_coding', 140),
        ('r2_05_complex_projects_remote', 0)
    ]),
    # Zone 3A (Strong health insurance, auto retirement, travel booked ahead)
    ('zone_3A', 20200.0, [
        ('r3_01_strong_health_insurance', 140),
        ('r3_02_automatic_retirement_rewards', 140),
        ('r3_03_booking_travel_months_ahead', 0)
    ]),
    # Zone 3B (Calling pros / time value, lawn care & regular cleaning)
    ('zone_3B', 25200.0, [
        ('r3_04_calling_pros_time_value', 160),
        ('r3_05_lawn_care_regular_cleaning', 0)
    ]),
    # Zone 4A (Personal trainer gym, kids lessons & sports, evening signing)
    ('zone_4A', 29800.0, [
        ('r4_01_personal_trainer_gym', 140),
        ('r4_02_kids_sports_and_lessons', 140),
        ('r4_03_evening_agenda_signing', 0)
    ]),
    # Zone 4B (Online gifts & charity, secure future thinking)
    ('zone_4B', 34800.0, [
        ('r4_04_online_gift_charity', 160),
        ('r4_05_secure_future_thinking', 0)
    ])
]

placed_elements = {}
zones_info = {}

print("=" * 80, flush=True)
print("📐 SECTION 06 PURE HORIZONTAL CINEMATIC LAYOUT (CONSTANT Y = 800.0)", flush=True)
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

print(f"\n✅ Section 06 pure horizontal layout successfully saved to {OUT_LAYOUT}", flush=True)
