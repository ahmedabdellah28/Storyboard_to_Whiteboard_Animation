import os
import sys
import json
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "11_outro")
META_PATH = os.path.join(SEC_DIR, "assets", "metadata.json")
OUT_LAYOUT = os.path.join(SEC_DIR, "placed_elements_layout.json")

with open(META_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

SCALE = 2.8
FIXED_Y = 800.0
CAM_ZOOM = 0.58
WORLD_HALF = (1920.0 / 2.0) / CAM_ZOOM  # ~1655.17 px

horizontal_spec = [
    # Zone 1A (Sidewalk vs silk, same ultimate result, shroud has no pockets)
    ('zone_1A', 500.0, [
        ('r1_01_sidewalk_vs_silk', 140),
        ('r1_02_same_ultimate_result', 140),
        ('r1_03_shroud_no_pockets', 0)
    ]),
    # Zone 1B (Leaving as we came, everything is temporary)
    ('zone_1B', 5200.0, [
        ('r1_04_leaving_as_we_came', 160),
        ('r1_05_everything_is_temporary', 0)
    ]),
    # Zone 2A (Supplication for contentment, blessed halal provision)
    ('zone_2A', 9800.0, [
        ('r2_01_supplication_contentment', 160),
        ('r2_02_blessed_halal_provision', 0)
    ]),
    # Zone 2B (Independent by his grace, dunya in hands not hearts, community question start)
    ('zone_2B', 14400.0, [
        ('r2_03_independent_by_his_grace', 140),
        ('r2_04_dunya_in_hands_not_hearts', 140),
        ('r2_05_community_question_start', 0)
    ]),
    # Zone 3A (Which tier closest to peace, not most money, balanced life and peace)
    ('zone_3A', 19200.0, [
        ('r3_01_which_tier_closest_peace', 140),
        ('r3_02_not_most_money', 140),
        ('r3_03_balanced_life_peace', 0)
    ]),
    # Zone 3B (Audience comments discussion, like channel support)
    ('zone_3B', 23800.0, [
        ('r3_04_audience_comments_discussion', 160),
        ('r3_05_like_channel_support', 0)
    ]),
    # Zone 4A (Subscription bell action, share with friends, next video teaser)
    ('zone_4A', 28400.0, [
        ('r4_01_subscription_bell_action', 140),
        ('r4_02_share_with_friends', 140),
        ('r4_03_next_video_teaser', 0)
    ]),
    # Zone 4B (Farewell blessings, end slate credits)
    ('zone_4B', 33400.0, [
        ('r4_04_farewell_blessings', 160),
        ('r4_05_end_slate_credits', 0)
    ])
]

placed_elements = {}
zones_info = {}

print("=" * 80, flush=True)
print("📐 SECTION 11 PURE HORIZONTAL CINEMATIC LAYOUT (CONSTANT Y = 800.0)", flush=True)
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

print(f"\n✅ Section 11 pure horizontal layout successfully saved to {OUT_LAYOUT}", flush=True)
