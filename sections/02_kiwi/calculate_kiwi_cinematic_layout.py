import os
import json

# Scale factor for individual elements (large and bold)
SCALE = 2.9
ROW_GAP_Y = 2000.0  # 2000px vertical gap between rows
BASE_Y = 800.0
START_X = 500.0

with open("sections/02_kiwi/assets/metadata.json", "r", encoding="utf-8") as f:
    meta = json.load(f)

# Define element gaps per row
rows_elements = {
    1: [
        ('r1_01', 130), # Giant kiwi
        ('r1_02', 140), # Leaves
        ('r1_03', 200), # Chinese sage (gap before wild berries)
        ('r1_04', 130), # Gooseberry
        ('r1_05', 130), # Berries bowl
        ('r1_06', 0),   # Mortar & pestle
    ],
    2: [
        ('r2_01', 130), # NZ Farmer
        ('r2_02', 120), # NZ Map
        ('r2_03', 120), # Seed sack
        ('r2_04', 180), # Hand with seeds (gap before growth)
        ('r2_05', 90),  # Sprout
        ('r2_06', 90),  # Seedling
        ('r2_07', 130), # Vine tree
        ('r2_08', 0),   # Size progression
    ],
    3: [
        ('r3_01', 50),  # Kiwi bird
        ('r3_02', 160), # Speech bubble
        ('r3_03', 130), # Cargo ship
        ('r3_04', 130), # Airplane
        ('r3_05', 130), # Globe
        ('r3_06', 0),   # Truck
    ],
    4: [
        ('r4_01', 130), # Vineyard
        ('r4_02', 130), # Crate
        ('r4_03', 130), # Scale
        ('r4_04', 120), # Knife slicing
        ('r4_05', 120), # Fresh slice
        ('r4_06', 130), # Bowl
        ('r4_07', 0),   # Family eating
    ],
    5: [
        ('r5_01', 120), # Stomach
        ('r5_02', 120), # Enzymes
        ('r5_03', 180), # Sparkles
        ('r5_04', 60),  # Shield
        ('r5_05', 60),  # Vitamin C badge
        ('r5_06', 150), # Checkmark
        ('r5_07', 140), # Grocery display
        ('r5_08', 0),   # Happy consumer
    ]
}

placed_elements = {}
row_zones = {}

MARGIN_PX = 140.0
ZOOM = 0.58
WORLD_HALF = (1920.0 / 2.0) / ZOOM
WORLD_MARGIN = MARGIN_PX / ZOOM
OFFSET = WORLD_HALF - WORLD_MARGIN

for r_idx, elems in rows_elements.items():
    row_y = BASE_Y + (r_idx - 1) * ROW_GAP_Y
    cur_x = START_X
    row_placed = []
    
    for aid, gap in elems:
        b = meta[aid]['orig_box']
        ow, oh = b[2], b[3]
        w = int(round(ow * SCALE))
        h = int(round(oh * SCALE))
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
        
    placed_elements[r_idx] = row_placed
    
    xmin = row_placed[0]['x']
    xmax = row_placed[-1]['x'] + row_placed[-1]['w']
    za_x = xmin + OFFSET
    zb_x = xmax - OFFSET
    
    row_zones[r_idx] = {
        'row_y': row_y,
        'zone_A': (za_x, row_y),
        'zone_B': (zb_x, row_y)
    }
    print(f"Kiwi Row {r_idx} (Y={row_y:.0f}): Width={cur_x - START_X:.0f}px, Zone A X={za_x:.1f}, Zone B X={zb_x:.1f}")

with open("sections/02_kiwi/placed_elements_layout.json", "w", encoding="utf-8") as f:
    json.dump({'elements': placed_elements, 'zones': row_zones}, f, indent=2)

print("\nSaved sections/02_kiwi/placed_elements_layout.json successfully!")
