import os
import sys
import json

# Safe console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCALE = 2.7
ROW_GAP_Y = 2000.0  # 2000px vertical gap between rows
BASE_Y = 800.0

meta_file = "sections/06_mango/assets/metadata.json"
with open(meta_file, "r", encoding="utf-8") as f:
    meta = json.load(f)

# Layout specification: 4 rows x 2 zones (8 zones total)
layout_spec = {
    1: {
        'zone_A': {
            'x_start': 500.0,
            'elements': [
                ('r1_01_hero_mango', 140),
                ('r1_02_crowned_king_mango', 140),
                ('r1_03_indian_man_taj_mahal', 0),
            ]
        },
        'zone_B': {
            'x_start': 5000.0,
            'elements': [
                ('r1_04_ancient_map_india_myanmar', 160),
                ('r1_05_buddha_temple_mango_tree', 0),
            ]
        }
    },
    2: {
        'zone_A': {
            'x_start': 550.0,
            'elements': [
                ('r2_01_ancient_scroll_manuscript', 160),
                ('r2_02_mango_varieties_grid', 0),
            ]
        },
        'zone_B': {
            'x_start': 5000.0,
            'elements': [
                ('r2_03_creamy_texture_mango', 140),
                ('r2_04_fibrous_texture_mango', 140),
                ('r2_05_super_sweet_mango_sugar', 0),
            ]
        }
    },
    3: {
        'zone_A': {
            'x_start': 500.0,
            'elements': [
                ('r3_01_portuguese_explorer_caravel', 160),
                ('r3_02_world_map_trade_routes', 0),
            ]
        },
        'zone_B': {
            'x_start': 4900.0,
            'elements': [
                ('r3_03_tropical_harbor_mango_crates', 160),
                ('r3_04_globe_mango_distribution', 0),
            ]
        }
    },
    4: {
        'zone_A': {
            'x_start': 600.0,
            'elements': [
                ('r4_01_vitamin_c_shield_molecules', 160),
                ('r4_02_mango_blossoms_inflorescence', 0),
            ]
        },
        'zone_B': {
            'x_start': 4900.0,
            'elements': [
                ('r4_03_cross_section_mango_halves', 140),
                ('r4_04_three_mangoes_trio', 140),
                ('r4_05_mango_smoothie_dessert_bowl', 0),
            ]
        }
    }
}

placed_elements = {}
row_zones = {}

ZOOM = 0.58
WORLD_HALF = (1920.0 / 2.0) / ZOOM  # ~1655.17 px

print("=== CALCULATING CINEMATIC 4-ROW / 8-ZONE LAYOUT FOR MANGO ===")

for r_idx, row_data in layout_spec.items():
    row_y = BASE_Y + (r_idx - 1) * ROW_GAP_Y
    row_placed = []
    
    # Place Zone A
    cur_x = row_data['zone_A']['x_start']
    za_start_x = cur_x
    for aid, gap in row_data['zone_A']['elements']:
        info = meta[aid]
        elem_scale = SCALE
        if aid in ['r3_01_portuguese_explorer_caravel', 'r3_02_world_map_trade_routes', 'r4_01_vitamin_c_shield_molecules']:
            elem_scale = 2.6
        elif aid in ['r1_04_ancient_map_india_myanmar', 'r1_05_buddha_temple_mango_tree', 'r2_03_creamy_texture_mango', 'r2_04_fibrous_texture_mango', 'r2_05_super_sweet_mango_sugar']:
            elem_scale = 2.8

        w = int(info['width'] * elem_scale)
        h = int(info['height'] * elem_scale)
        y = row_y - (h / 2.0)
        
        row_placed.append({
            'aid': aid,
            'file': info['file'],
            'x': cur_x,
            'y': y,
            'w': w,
            'h': h,
            'cx': cur_x + w / 2.0,
            'cy': y + h / 2.0,
            'zone': 'A'
        })
        cur_x += w + gap
    za_end_x = cur_x - (gap if 'gap' in locals() else 0)
    za_cam_x = (za_start_x + za_end_x) / 2.0
    
    # Place Zone B
    cur_x = row_data['zone_B']['x_start']
    zb_start_x = cur_x
    for aid, gap in row_data['zone_B']['elements']:
        info = meta[aid]
        elem_scale = SCALE
        if aid in ['r1_04_ancient_map_india_myanmar', 'r1_05_buddha_temple_mango_tree', 'r2_03_creamy_texture_mango', 'r2_04_fibrous_texture_mango', 'r2_05_super_sweet_mango_sugar', 'r3_03_tropical_harbor_mango_crates', 'r3_04_globe_mango_distribution']:
            elem_scale = 2.8

        w = int(info['width'] * elem_scale)
        h = int(info['height'] * elem_scale)
        y = row_y - (h / 2.0)
        
        row_placed.append({
            'aid': aid,
            'file': info['file'],
            'x': cur_x,
            'y': y,
            'w': w,
            'h': h,
            'cx': cur_x + w / 2.0,
            'cy': y + h / 2.0,
            'zone': 'B'
        })
        cur_x += w + gap
    zb_end_x = cur_x - (gap if 'gap' in locals() else 0)
    zb_cam_x = (zb_start_x + zb_end_x) / 2.0
    
    placed_elements[str(r_idx)] = row_placed
    row_zones[str(r_idx)] = {
        'row_y': row_y,
        'zone_A': [za_cam_x, row_y],
        'zone_B': [zb_cam_x, row_y],
        'za_span': [za_start_x, za_end_x],
        'zb_span': [zb_start_x, zb_end_x]
    }
    
    # Calculate isolation clearance
    # When cam is at za_cam_x, right screen boundary is za_cam_x + WORLD_HALF
    # Zb elements must be to the right of za_cam_x + WORLD_HALF
    clearance_A_to_B = zb_start_x - (za_cam_x + WORLD_HALF)
    
    # When cam is at zb_cam_x, left screen boundary is zb_cam_x - WORLD_HALF
    # Za elements must be to the left of zb_cam_x - WORLD_HALF
    clearance_B_to_A = (zb_cam_x - WORLD_HALF) - za_end_x
    
    print(f"Row {r_idx} (Y={row_y:.0f}):")
    print(f"  Zone A: [{za_start_x:.0f} .. {za_end_x:.0f}], CamX={za_cam_x:.1f}, Screen=[{za_cam_x - WORLD_HALF:.0f} .. {za_cam_x + WORLD_HALF:.0f}]")
    print(f"  Zone B: [{zb_start_x:.0f} .. {zb_end_x:.0f}], CamX={zb_cam_x:.1f}, Screen=[{zb_cam_x - WORLD_HALF:.0f} .. {zb_cam_x + WORLD_HALF:.0f}]")
    print(f"  Clearance: A→B offscreen={clearance_A_to_B:.0f}px | B→A offscreen={clearance_B_to_A:.0f}px")
    if clearance_A_to_B < 200 or clearance_B_to_A < 200:
        print("  ⚠️ WARNING: Clearance is below 200px!")
    else:
        print("  ✅ CLEARANCE EXCELLENT (>200px)")

output_json = "sections/06_mango/placed_elements_layout.json"
with open(output_json, "w", encoding="utf-8") as f:
    json.dump({
        'scale': SCALE,
        'zoom': ZOOM,
        'world_half': WORLD_HALF,
        'elements': placed_elements,
        'zones': row_zones
    }, f, indent=2, ensure_ascii=False)

print(f"\nLayout saved to {output_json}")
