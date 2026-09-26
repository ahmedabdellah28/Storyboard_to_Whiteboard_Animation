import os
import sys
import json
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "01_homeless")
META_PATH = os.path.join(SEC_DIR, "assets", "metadata.json")
OUT_LAYOUT = os.path.join(SEC_DIR, "placed_elements_layout.json")

with open(META_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

SCALE = 2.8
FIXED_Y = 800.0
CAM_ZOOM = 0.58
WORLD_HALF = (1920.0 / 2.0) / CAM_ZOOM  # ~1655.17 px

horizontal_spec = [
    # Zone 1A (Waking on street, back pain, checking bag)
    ('zone_1A', 500.0, [
        ('r1_01_waking_street', 140),
        ('r1_02_back_pain', 140),
        ('r1_03_check_backpack', 0)
    ]),
    # Zone 1B (Broken phone, search wifi, outdoor charge)
    ('zone_1B', 5200.0, [
        ('r1_04_broken_phone', 140),
        ('r1_05_search_wifi', 140),
        ('r1_06_outdoor_charge', 0)
    ]),
    # Zone 2A (Public bathroom, wash sink, clean shirt)
    ('zone_2A', 9800.0, [
        ('r2_01_goto_bathroom', 140),
        ('r2_02_wash_sink', 140),
        ('r2_03_clean_shirt', 0)
    ]),
    # Zone 2B (Charity food line, eating sidewalk, grocery no kitchen)
    ('zone_2B', 14200.0, [
        ('r2_04_charity_food', 140),
        ('r2_05_eating_sidewalk', 140),
        ('r2_06_grocery_no_kitchen', 0)
    ]),
    # Zone 3A (Park bench thinking, public library)
    ('zone_3A', 18800.0, [
        ('r3_01_park_bench_think', 160),
        ('r3_02_public_library', 0)
    ]),
    # Zone 3B (Begging on cardboard, missing ID, clinic/hospital)
    ('zone_3B', 23200.0, [
        ('r3_03_begging_cardboard', 140),
        ('r3_04_missing_id', 140),
        ('r3_05_clinic_hospital', 0)
    ]),
    # Zone 4A (Shelter line, sleeping under bridge, sleeping moon)
    ('zone_4A', 28200.0, [
        ('r4_01_shelter_line', 140),
        ('r4_02_under_bridge', 140),
        ('r4_03_sleeping_moon', 0)
    ]),
    # Zone 4B (Survival cycle loop, walking into sunrise)
    ('zone_4B', 33200.0, [
        ('r4_04_survival_loop', 160),
        ('r4_05_walk_sunrise', 0)
    ])
]

placed_elements = {}
zones_info = {}

print("=" * 80)
print("📐 SECTION 01 PURE HORIZONTAL CINEMATIC LAYOUT (CONSTANT Y = 800.0)")
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
