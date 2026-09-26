import os
import sys
import json
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "02_extreme_poverty")
META_PATH = os.path.join(SEC_DIR, "assets", "metadata.json")
OUT_LAYOUT = os.path.join(SEC_DIR, "placed_elements_layout.json")

with open(META_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

SCALE = 2.8
FIXED_Y = 800.0
CAM_ZOOM = 0.58
WORLD_HALF = (1920.0 / 2.0) / CAM_ZOOM  # ~1655.17 px

horizontal_spec = [
    # Zone 1A (Small rented room, crowded space, broken AC)
    ('zone_1A', 500.0, [
        ('r1_01_waking_up', 140),
        ('r1_02_crowded_room', 140),
        ('r1_03_broken_ac', 0)
    ]),
    # Zone 1B (Prepaid phone balance, counting bus tickets)
    ('zone_1B', 5200.0, [
        ('r1_04_prepaid_phone', 160),
        ('r1_05_counting_tickets', 0)
    ]),
    # Zone 2A (Basic breakfast, shopping with coupons, packing kids snacks)
    ('zone_2A', 9800.0, [
        ('r2_01_basic_breakfast', 140),
        ('r2_02_shopping_coupons', 140),
        ('r2_03_kids_snacks', 0)
    ]),
    # Zone 2B (Waiting delayed bus, driving broken car with check engine light)
    ('zone_2B', 14200.0, [
        ('r2_04_waiting_bus', 160),
        ('r2_05_broken_car', 0)
    ]),
    # Zone 3A (Unpredictable work hours, desperate overtime shifts, overdue bills)
    ('zone_3A', 18800.0, [
        ('r3_01_work_schedule', 140),
        ('r3_02_overtime_work', 140),
        ('r3_03_overdue_bills', 0)
    ]),
    # Zone 3B (Buying money orders to avoid fees, long clinic wait times)
    ('zone_3B', 23200.0, [
        ('r3_04_money_transfer', 160),
        ('r3_05_clinic_wait', 0)
    ]),
    # Zone 4A (Laundromat costs, YouTube DIY repairs, stretching every resource)
    ('zone_4A', 28200.0, [
        ('r4_01_laundry_mat', 140),
        ('r4_02_diy_repair', 140),
        ('r4_03_stretching_resources', 0)
    ]),
    # Zone 4B (Simple tomorrow task list, sleeping to repeat the cycle)
    ('zone_4B', 33200.0, [
        ('r4_04_night_planning', 160),
        ('r4_05_sleeping_night', 0)
    ])
]

placed_elements = {}
zones_info = {}

print("=" * 80)
print("📐 SECTION 02 PURE HORIZONTAL CINEMATIC LAYOUT (CONSTANT Y = 800.0)")
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
