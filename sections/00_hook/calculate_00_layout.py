import os
import sys
import json
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "00_hook")
META_PATH = os.path.join(SEC_DIR, "assets", "metadata.json")
OUT_LAYOUT = os.path.join(SEC_DIR, "placed_elements_layout.json")

with open(META_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

SCALE = 2.8
FIXED_Y = 800.0  # Constant Y for 100% purely horizontal panning
CAM_ZOOM = 0.58
WORLD_HALF = (1920.0 / 2.0) / CAM_ZOOM  # ~1655.17 px

# Continuous Horizontal Layout (Pure X axis tracking)
# All zones share the exact same Y center (800.0)
horizontal_spec = [
    # Zone 1A
    ('zone_1A', 500.0, [
        ('r1_01_waking_bed', 160),
        ('r1_02_sad_sitting', 160),
        ('r1_03_no_job_fly_gym', 0)
    ]),
    # Zone 1B
    ('zone_1B', 5200.0, [
        ('r1_04_city_dawn', 180),
        ('r1_05_crowd_safety', 0)
    ]),
    # Zone 2A (Bedrooms part 1)
    ('zone_2A', 9800.0, [
        ('r2_01_homeless_sidewalk', 140),
        ('r2_02_small_room', 140),
        ('r2_03_neat_apartment', 0)
    ]),
    # Zone 2B (Bedrooms part 2)
    ('zone_2B', 14200.0, [
        ('r2_04_comfortable_room', 140),
        ('r2_05_luxury_suite', 140),
        ('r2_06_mansion_staff', 0)
    ]),
    # Zone 3A (Same day)
    ('zone_3A', 19200.0, [
        ('r3_01_stretching_man', 0)
    ]),
    # Zone 3B (24h Timeline)
    ('zone_3B', 22800.0, [
        ('r3_02_timeline_24h', 0)
    ]),
    # Zone 4A (Time & Money)
    ('zone_4A', 27400.0, [
        ('r4_01_time_clock', 180),
        ('r4_02_money_cash', 0)
    ]),
    # Zone 4B (Health & Problems)
    ('zone_4B', 31800.0, [
        ('r4_03_health_gym', 180),
        ('r4_04_problems_mind', 0)
    ]),
    # Zone 5A (Homeless -> Billionaire)
    ('zone_5A', 36200.0, [
        ('r5_01_homeless_man', 120),
        ('r5_02_billionaire_car', 0)
    ]),
    # Zone 5B (Question & Chart)
    ('zone_5B', 41200.0, [
        ('r5_03_thinking_question', 180),
        ('r5_04_rising_chart', 0)
    ])
]

placed_elements = {}
zones_info = {}

print("=" * 80)
print("📐 COMPUTING 100% PURE HORIZONTAL CINEMATIC LAYOUT (CONSTANT Y = 800.0)")
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

print(f"\n✅ Pure horizontal layout successfully saved to: {OUT_LAYOUT}")
