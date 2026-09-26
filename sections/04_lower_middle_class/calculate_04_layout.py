import os
import sys
import json
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "04_lower_middle_class")
META_PATH = os.path.join(SEC_DIR, "assets", "metadata.json")
OUT_LAYOUT = os.path.join(SEC_DIR, "placed_elements_layout.json")

with open(META_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

SCALE = 2.8
FIXED_Y = 800.0
CAM_ZOOM = 0.58
WORLD_HALF = (1920.0 / 2.0) / CAM_ZOOM  # ~1655.17 px

horizontal_spec = [
    # Zone 1A (Modest apartment, fridge bills list, coffee and calendar)
    ('zone_1A', 500.0, [
        ('r1_01_modest_apartment', 140),
        ('r1_02_fridge_bills_list', 140),
        ('r1_03_coffee_calendar', 0)
    ]),
    # Zone 1B (Budget app paycheck, healthy home breakfast)
    ('zone_1B', 5200.0, [
        ('r1_04_budget_app_paycheck', 160),
        ('r1_05_healthy_breakfast', 0)
    ]),
    # Zone 2A (Clean used car, commuter train pass)
    ('zone_2A', 9600.0, [
        ('r2_01_used_reliable_car', 160),
        ('r2_02_commuter_train', 0)
    ]),
    # Zone 2B (Office desk emails, meeting clients, paid break and pension)
    ('zone_2B', 14200.0, [
        ('r2_03_office_desk_emails', 140),
        ('r2_04_meeting_clients', 140),
        ('r2_05_paid_break_pension', 0)
    ]),
    # Zone 3A (Lunch banking check, student loan auto-deduct, savings buffer)
    ('zone_3A', 19000.0, [
        ('r3_01_lunch_banking_check', 140),
        ('r3_02_student_loan_deduct', 140),
        ('r3_03_savings_buffer', 0)
    ]),
    # Zone 3B (Affordable gym, warm home-cooked dinner)
    ('zone_3B', 23600.0, [
        ('r3_04_affordable_gym', 160),
        ('r3_05_home_cooked_dinner', 0)
    ]),
    # Zone 4A (Streaming Netflix, roadtrip savings, ironing and charging phone)
    ('zone_4A', 28200.0, [
        ('r4_01_streaming_netflix', 140),
        ('r4_02_roadtrip_plan', 140),
        ('r4_03_ironing_phone_charge', 0)
    ]),
    # Zone 4B (Checking calendar organized, sleeping with safety margin)
    ('zone_4B', 33200.0, [
        ('r4_04_calendar_recheck', 160),
        ('r4_05_safety_margin_sleep', 0)
    ])
]

placed_elements = {}
zones_info = {}

print("=" * 80, flush=True)
print("📐 SECTION 04 PURE HORIZONTAL CINEMATIC LAYOUT (CONSTANT Y = 800.0)", flush=True)
print("=" * 80, flush=True)

for z_name, start_x, elements in horizontal_spec:
    cur_x = start_x
    placed_elements[z_name] = []
    
    for eid, gap in elements:
        item_meta = metadata[eid]
        ow = item_meta.get('width', item_meta.get('orig_size', [200, 200])[0])
        oh = item_meta.get('height', item_meta.get('orig_size', [200, 200])[1])
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

print(f"\n✅ Section 04 pure horizontal layout successfully saved to {OUT_LAYOUT}", flush=True)
