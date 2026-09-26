import os
import cv2
import numpy as np

# Scale factor for individual elements (large and bold)
SCALE = 3.0
ROW_GAP_Y = 2000.0  # Massive 2000px vertical gap between rows (100% vertical isolation)
BASE_Y = 800.0

# Define elements per row with custom horizontal gaps (breathing room)
# (id, name, orig_w, orig_h, gap_after)
rows_data = {
    1: [
        ("01_giant", "01_giant_red_apple", 196, 221, 140),
        ("02_wild", "02_wild_sour_apple", 113, 144, 130),
        ("03_branch", "03_wild_branch", 245, 228, 140),
        ("04_flower", "04_apple_blossom_flower", 154, 176, 220), # Gap between zones
        ("05_tree", "05_blooming_apple_tree", 213, 224, 140),
        ("06_mount", "06_snowy_mountains_winter", 258, 203, 130),
        ("07_map", "07_central_asia_map", 218, 189, 0),
    ],
    2: [
        ("08_soldier", "08_roman_soldier", 180, 239, 140),
        ("10_map", "10_europe_map_arrow", 212, 197, 130),
        ("09_cart", "09_horse_cart_apples", 314, 186, 220), # Gap between zones
        ("11_farmer", "11_farmer_planting", 235, 194, 150),
        ("12_s1", "12_tree_stage_1_seedling", 71, 98, 80),
        ("12_s2", "12_tree_stage_2_sapling", 74, 139, 80),
        ("12_s3", "12_tree_stage_3_growing", 102, 189, 90),
        ("12_s4", "12_tree_stage_4_mature", 174, 208, 0),
    ],
    3: [
        ("13_e1", "13_evo_1_ancient_sour", 154, 98, 100),
        ("13_e2", "13_evo_2_selection_growth", 246, 88, 100),
        ("13_e3", "13_evo_3_giant_honeycrisp", 231, 138, 130),
        ("14_hand", "14_hand_picking_apple", 291, 158, 220), # Gap between zones
        ("15_v1", "15_var_1_red", 81, 119, 70),
        ("15_v2", "15_var_2_green", 76, 119, 70),
        ("15_v3", "15_var_3_yellow", 71, 119, 70),
        ("15_v4", "15_var_4_dark", 76, 119, 70),
        ("15_v5", "15_var_5_striped", 91, 119, 0),
    ],
    4: [
        ("16_cycle", "16_seedling_cycle", 351, 107, 140),
        ("17_crate", "17_harvest_crate", 211, 144, 140),
        ("18_juice", "18_sliced_apples_juice", 414, 133, 240), # Gap between zones
        ("19_inspect", "19_farmer_inspecting_apple", 179, 145, 140),
        ("20_c1", "20_check_1_green", 55, 90, 50),
        ("20_c2", "20_check_2_green", 56, 90, 50),
        ("20_c3", "20_check_3_green", 56, 90, 50),
        ("20_c4", "20_check_4_red_x", 52, 90, 0),
    ],
    5: [
        ("21_gut", "21_digestive_health_gut", 199, 162, 130),
        ("22_vitamins", "22_vitamins_bubbles", 211, 143, 130),
        ("23_heart", "23_heart_health_pulse", 190, 109, 220), # Gap between zones
        ("24_wheat", "24_wheat_fiber_apples", 215, 146, 130),
        ("25_pile", "25_apple_harvest_pile", 275, 152, 140),
        ("26_fridge", "26_refrigerator_modern_apples", 219, 192, 0),
    ]
}

placed_elements = {}
row_zones = {}

START_X = 500.0

for r_idx, elems in rows_data.items():
    row_y = BASE_Y + (r_idx - 1) * ROW_GAP_Y
    cur_x = START_X
    row_placed = []
    
    for eid, name, ow, oh, gap in elems:
        w = int(round(ow * SCALE))
        h = int(round(oh * SCALE))
        y = int(round(row_y - h / 2.0))
        x = int(round(cur_x))
        row_placed.append({
            'eid': eid,
            'name': name,
            'x': x,
            'y': y,
            'w': w,
            'h': h,
            'cx': x + w / 2.0,
            'cy': y + h / 2.0
        })
        cur_x += w + gap
        
    placed_elements[r_idx] = row_placed
    
    # Calculate optimal Camera Centers for Zone A (Left) and Zone B (Right)
    # Zone A center: covers elements up to the midpoint
    # Zone B center: covers elements from midpoint to end
    half = len(row_placed) // 2
    left_elems = row_placed[:max(1, half)]
    right_elems = row_placed[max(1, half):]
    
    zone_A_cx = (left_elems[0]['x'] + left_elems[-1]['x'] + left_elems[-1]['w']) / 2.0
    zone_B_cx = (right_elems[0]['x'] + right_elems[-1]['x'] + right_elems[-1]['w']) / 2.0
    
    row_zones[r_idx] = {
        'row_y': row_y,
        'zone_A': (zone_A_cx, row_y),
        'zone_B': (zone_B_cx, row_y)
    }
    
    print(f"Row {r_idx} (Y={row_y:.0f}):")
    print(f"  Total Width: {cur_x - START_X:.0f} px")
    print(f"  Zone A Cam: X={zone_A_cx:.1f}, Y={row_y:.1f}")
    print(f"  Zone B Cam: X={zone_B_cx:.1f}, Y={row_y:.1f}")

import json
with open("sections/01_apple/placed_elements_layout.json", "w", encoding="utf-8") as f:
    json.dump({'elements': placed_elements, 'zones': row_zones}, f, indent=2)

print("\nSaved sections/01_apple/placed_elements_layout.json successfully!")
