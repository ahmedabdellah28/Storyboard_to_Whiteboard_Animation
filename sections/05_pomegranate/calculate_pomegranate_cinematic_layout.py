import os
import sys
import json

# Safe console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCALE = 2.8
ROW_GAP_Y = 2000.0  # 2000px vertical gap between rows
BASE_Y = 800.0

with open("sections/05_pomegranate/assets/metadata.json", "r", encoding="utf-8") as f:
    meta = json.load(f)

# Layout specification with 2 isolated zones per row across 4 narrative rows
layout_spec = {
    1: {
        'zone_A': {
            'x_start': 600.0,
            'elements': [
                ('r1_01_hero_pomegranate', 140),
                ('r1_02_ancient_ruins_tree', 0),
            ]
        },
        'zone_B': {
            'x_start': 4400.0,
            'elements': [
                ('r1_03_ancient_map_iran_afghanistan', 120),
                ('r1_04_pomegranate_sprout_growing', 120),
                ('r1_05_mature_fruitful_tree', 0),
            ]
        }
    },
    2: {
        'zone_A': {
            'x_start': 650.0,
            'elements': [
                ('r2_01_persian_king', 140),
                ('r2_02_greek_and_roman_figures', 0),
            ]
        },
        'zone_B': {
            'x_start': 4300.0,
            'elements': [
                ('r2_03_fertility_pregnant_silhouette', 100),
                ('r2_04_prosperity_tree_sunburst', 100),
                ('r2_05_resurrection_stairway_heaven', 100),
                ('r2_06_unity_hands_pomegranate', 0),
            ]
        }
    },
    3: {
        'zone_A': {
            'x_start': 600.0,
            'elements': [
                ('r3_01_torah_scroll_star_and_seed_zoom', 140),
                ('r3_02_pomegranate_cross_section_seed_zoom', 0),
            ]
        },
        'zone_B': {
            'x_start': 4400.0,
            'elements': [
                ('r3_03_antioxidant_shield_molecules', 160),
                ('r3_04_cardiovascular_heart_ecg', 0),
            ]
        }
    },
    4: {
        'zone_A': {
            'x_start': 600.0,
            'elements': [
                ('r4_01_pomegranate_juice_glass', 140),
                ('r4_02_salad_bowl_walnuts', 0),
            ]
        },
        'zone_B': {
            'x_start': 4600.0,
            'elements': [
                ('r4_03_botanical_blossoms_branch', 0),
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
        info = meta[aid]
        # Custom fine-tuned scale per asset type
        elem_scale = SCALE
        if aid in ['r2_02_greek_and_roman_figures', 'r4_03_botanical_blossoms_branch']:
            elem_scale = 2.6
        elif aid in ['r2_03_fertility_pregnant_silhouette', 'r2_04_prosperity_tree_sunburst', 'r2_05_resurrection_stairway_heaven', 'r2_06_unity_hands_pomegranate']:
            elem_scale = 2.7

        w = int(info['width'] * elem_scale)
        h = int(info['height'] * elem_scale)
        y = row_y - (h / 2.0)
        
        row_placed.append({
            'aid': aid,
            'x': cur_x,
            'y': y,
            'w': w,
            'h': h,
            'zone': 'A'
        })
        cur_x += w + gap
    za_end_x = cur_x - row_data['zone_A']['elements'][-1][1]
    
    # Camera center for Zone A: center of bounding elements
    za_cam_center_x = (za_start_x + za_end_x) / 2.0
    
    # Place Zone B
    cur_x = row_data['zone_B']['x_start']
    zb_start_x = cur_x
    for aid, gap in row_data['zone_B']['elements']:
        info = meta[aid]
        elem_scale = SCALE
        if aid in ['r2_02_greek_and_roman_figures', 'r4_03_botanical_blossoms_branch']:
            elem_scale = 2.6
        elif aid in ['r2_03_fertility_pregnant_silhouette', 'r2_04_prosperity_tree_sunburst', 'r2_05_resurrection_stairway_heaven', 'r2_06_unity_hands_pomegranate']:
            elem_scale = 2.7

        w = int(info['width'] * elem_scale)
        h = int(info['height'] * elem_scale)
        y = row_y - (h / 2.0)
        
        row_placed.append({
            'aid': aid,
            'x': cur_x,
            'y': y,
            'w': w,
            'h': h,
            'zone': 'B'
        })
        cur_x += w + gap
    zb_end_x = cur_x - row_data['zone_B']['elements'][-1][1]
    
    zb_cam_center_x = (zb_start_x + zb_end_x) / 2.0
    
    placed_elements[r_idx] = row_placed
    row_zones[r_idx] = {
        'zone_A': [za_cam_center_x, row_y],
        'zone_B': [zb_cam_center_x, row_y],
        'clearance': zb_start_x - (za_cam_center_x + WORLD_HALF)
    }

print("\nRow Zones & Visual Isolation Verification:")
for r_idx, zinfo in row_zones.items():
    clr = zinfo['clearance']
    za_cx = zinfo['zone_A'][0]
    zb_cx = zinfo['zone_B'][0]
    status = "✅ PERFECT CLEARANCE" if clr > 400 else "⚠️ WARNING"
    print(f"Row {r_idx} (Y={zinfo['zone_A'][1]:.0f}):")
    print(f"  Zone A Cam X: {za_cx:.1f} (Viewport: [{za_cx - WORLD_HALF:.1f} to {za_cx + WORLD_HALF:.1f}])")
    print(f"  Zone B Cam X: {zb_cx:.1f} (Viewport: [{zb_cx - WORLD_HALF:.1f} to {zb_cx + WORLD_HALF:.1f}])")
    print(f"  Clearance between Zone A edge & Zone B start: {clr:.1f}px -> {status}")

out_layout = "sections/05_pomegranate/placed_elements_layout.json"
with open(out_layout, "w", encoding="utf-8") as f:
    json.dump({
        'elements': placed_elements,
        'zones': row_zones,
        'zoom': ZOOM,
        'base_y': BASE_Y,
        'row_gap_y': ROW_GAP_Y
    }, f, indent=2, ensure_ascii=False)

print(f"\nSaved layout to: {out_layout}")
