import os
import json

SCALE = 2.9
ROW_GAP_Y = 2000.0  # 2000px vertical gap between rows
BASE_Y = 800.0

with open("sections/03_lemon/assets/metadata.json", "r", encoding="utf-8") as f:
    meta = json.load(f)

# Layout specification with 2 isolated zones per row
# (element_id, x_start_or_gap, is_new_zone_start)
layout_spec = {
    1: {
        'zone_A': {
            'x_start': 500.0,
            'elements': [
                ('r1_01_hero_lemon', 160),
                ('r1_02_hybrid_citrus_dna', 160),
                ('r1_03_india_asia_map', 0),
            ]
        },
        'zone_B': {
            'x_start': 4000.0,
            'elements': [
                ('r1_04_dr_james_lind', 160),
                ('r1_05_scurvy_clipboard_cure', 0),
            ]
        }
    },
    2: {
        'zone_A': {
            'x_start': 595.0,
            'elements': [
                ('r2_01_naval_scurvy_ship', 150),
                ('r2_02_lemon_squeezing_ink', 80),
                ('r2_03_red_arrow', 80),
                ('r2_04_heat_lamp_reveal_writing', 0),
            ]
        },
        'zone_B': {
            'x_start': 4000.0,
            'elements': [
                ('r2_05_lush_lemon_tree', 180),
                ('r2_06_year_round_production_cycle', 0),
            ]
        }
    },
    3: {
        'zone_A': {
            'x_start': 1222.0,
            'elements': [
                ('r3_01_glass_lemon_water_liver_check', 60),
                ('r3_02_divider_line', 60),
                ('r3_03_cloudy_water_toxic_liver_cross', 0),
            ]
        },
        'zone_B': {
            'x_start': 3600.0,
            'elements': [
                ('r3_04_vitamin_c_glowing_emblem', 100),
                ('r3_05_citric_acid_molecule', 90),
                ('r3_06_kidney_stones_anatomy', 60),
                ('r3_07_stone_reduction_arrow', 0),
            ]
        }
    }
}

placed_elements = {}
row_zones = {}

ZOOM = 0.58
WORLD_HALF = (1920.0 / 2.0) / ZOOM

for r_idx, row_data in layout_spec.items():
    row_y = BASE_Y + (r_idx - 1) * ROW_GAP_Y
    row_placed = []
    
    # Place Zone A
    cur_x = row_data['zone_A']['x_start']
    za_start_x = cur_x
    for aid, gap in row_data['zone_A']['elements']:
        b = meta[aid]['orig_box']
        w = int(round(b[2] * SCALE))
        h = int(round(b[3] * SCALE))
        y = int(round(row_y - h / 2.0))
        x = int(round(cur_x))
        row_placed.append({
            'aid': aid,
            'file': meta[aid]['file'],
            'x': x,
            'y': y,
            'w': w,
            'h': h,
            'cx': x + w / 2.0,
            'cy': y + h / 2.0
        })
        cur_x += w + gap
    za_end_x = row_placed[-1]['x'] + row_placed[-1]['w']
    za_cam_x = (za_start_x + za_end_x) / 2.0
    
    # Place Zone B
    cur_x = row_data['zone_B']['x_start']
    zb_start_x = cur_x
    for aid, gap in row_data['zone_B']['elements']:
        b = meta[aid]['orig_box']
        w = int(round(b[2] * SCALE))
        h = int(round(b[3] * SCALE))
        y = int(round(row_y - h / 2.0))
        x = int(round(cur_x))
        row_placed.append({
            'aid': aid,
            'file': meta[aid]['file'],
            'x': x,
            'y': y,
            'w': w,
            'h': h,
            'cx': x + w / 2.0,
            'cy': y + h / 2.0
        })
        cur_x += w + gap
    zb_end_x = row_placed[-1]['x'] + row_placed[-1]['w']
    zb_cam_x = (zb_start_x + zb_end_x) / 2.0
    
    placed_elements[r_idx] = row_placed
    row_zones[r_idx] = {
        'row_y': row_y,
        'zone_A': (za_cam_x, row_y),
        'zone_B': (zb_cam_x, row_y)
    }
    
    print(f"Row {r_idx} (Y={row_y:.0f}):")
    print(f"  Zone A: [{za_start_x:.0f} .. {za_end_x:.0f}], CamX={za_cam_x:.1f}, Screen=[{za_cam_x-WORLD_HALF:.1f} .. {za_cam_x+WORLD_HALF:.1f}]")
    print(f"  Zone B: [{zb_start_x:.0f} .. {zb_end_x:.0f}], CamX={zb_cam_x:.1f}, Screen=[{zb_cam_x-WORLD_HALF:.1f} .. {zb_cam_x+WORLD_HALF:.1f}]")
    print(f"  Isolation Gap: {zb_start_x - za_end_x:.0f}px (Offscreen clearance: {zb_cam_x - WORLD_HALF - za_end_x:.1f}px)\n")

with open("sections/03_lemon/placed_elements_layout.json", "w", encoding="utf-8") as f:
    json.dump({'elements': placed_elements, 'zones': row_zones}, f, indent=2)

print("Saved sections/03_lemon/placed_elements_layout.json successfully!")
