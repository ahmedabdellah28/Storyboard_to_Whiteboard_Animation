import os
import json

SCALE = 2.9
ROW_GAP_Y = 2000.0  # 2000px vertical gap between rows
BASE_Y = 800.0

with open("sections/04_pineapple/assets/metadata.json", "r", encoding="utf-8") as f:
    meta = json.load(f)

# Layout specification with 2 isolated zones per row across 4 narrative rows
layout_spec = {
    1: {
        'zone_A': {
            'x_start': 500.0,
            'elements': [
                ('r1_01_hero_pineapple', 150),
                ('r1_02_south_america_map', 150),
                ('r1_03_pineapple_comparison', 80),
                ('r1_04_double_arrow', 80),
                ('r1_05_pine_cone', 0),
            ]
        },
        'zone_B': {
            'x_start': 5000.0,
            'elements': [
                ('r1_06_wealthy_gentleman_england_gold', 0),
            ]
        }
    },
    2: {
        'zone_A': {
            'x_start': 650.0,
            'elements': [
                ('r2_01_butler_velvet_pillow', 180),
                ('r2_02_admiring_guests', 0),
            ]
        },
        'zone_B': {
            'x_start': 4300.0,
            'elements': [
                ('r2_04_lavish_banquet_table', 180),
                ('r2_05_rich_man_throwing', 80),
                ('r2_06_trash_rotting_pineapple', 0),
            ]
        }
    },
    3: {
        'zone_A': {
            'x_start': 600.0,
            'elements': [
                ('r3_01_cross_section_cells', 150),
                ('r3_02_protein_molecule', 80),
                ('r3_03_blue_arrow', 80),
                ('r3_04_broken_protein_fragments', 0),
            ]
        },
        'zone_B': {
            'x_start': 4300.0,
            'elements': [
                ('r3_05_meat_tenderizer_bromelain', 150),
                ('r3_06_stinging_tongue', 150),
                ('r3_07_man_touching_stinging_tongue', 0),
            ]
        }
    },
    4: {
        'zone_A': {
            'x_start': 650.0,
            'elements': [
                ('r4_01_pineapple_slice_dripping', 80),
                ('r4_02_red_curved_arrow', 80),
                ('r4_03_mouth_eating_pineapple', 0),
            ]
        },
        'zone_B': {
            'x_start': 4300.0,
            'elements': [
                ('r4_04_carnivorous_monster_pineapple', 180),
                ('r4_05_terrified_man_running', 0),
            ]
        }
    }
}

placed_elements = {}
row_zones = {}

ZOOM = 0.58
WORLD_HALF = (1920.0 / 2.0) / ZOOM  # ~1655.17 px

print("=== CALCULATING CINEMATIC 4-ROW / 8-ZONE LAYOUT ===")

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
        'zone_A': [round(za_cam_x, 1), round(row_y, 1)],
        'zone_B': [round(zb_cam_x, 1), round(row_y, 1)]
    }

    # Isolation Verification
    za_screen_right = za_cam_x + WORLD_HALF
    zb_screen_left = zb_cam_x - WORLD_HALF
    gap_between_zones = zb_start_x - za_end_x
    clearance_a_to_b = zb_start_x - za_screen_right
    clearance_b_to_a = zb_screen_left - za_end_x

    print(f"\n--- Row {r_idx} (Y = {row_y}) ---")
    print(f"  Zone A: [{za_start_x:.0f} .. {za_end_x:.0f}], Width={za_end_x - za_start_x:.0f}px, CamX={za_cam_x:.1f}")
    print(f"          Camera View: [{za_cam_x - WORLD_HALF:.1f} .. {za_screen_right:.1f}]")
    print(f"  Zone B: [{zb_start_x:.0f} .. {zb_end_x:.0f}], Width={zb_end_x - zb_start_x:.0f}px, CamX={zb_cam_x:.1f}")
    print(f"          Camera View: [{zb_screen_left:.1f} .. {zb_cam_x + WORLD_HALF:.1f}]")
    print(f"  Physical Gap Between Zones: {gap_between_zones:.1f}px")
    print(f"  Clearance (Cam in Zone A -> Zone B start): {clearance_a_to_b:.1f}px (> 0 = ZERO BLEED)")
    print(f"  Clearance (Cam in Zone B -> Zone A end):   {clearance_b_to_a:.1f}px (> 0 = ZERO BLEED)")
    assert clearance_a_to_b > 200, f"Row {r_idx} Zone B bleeds into Zone A camera view!"
    assert clearance_b_to_a > 200, f"Row {r_idx} Zone A bleeds into Zone B camera view!"

output = {
    'scale': SCALE,
    'zoom': ZOOM,
    'row_gap_y': ROW_GAP_Y,
    'zones': row_zones,
    'elements': placed_elements
}

out_path = "sections/04_pineapple/placed_elements_layout.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\nLayout calculation SUCCESS! Saved to {out_path}")
