import os
import cv2
import numpy as np

img = cv2.imread('project_content/images/ChatGPT Image Sep 18, 2026, 11_33_57 PM.png')
h, w = img.shape[:2]
diff = 255.0 - img.astype(np.float32)
dist = np.max(diff, axis=2)

def get_bbox(x1, y1, x2, y2):
    sub = dist[y1:y2+1, x1:x2+1]
    m = (sub > 12).astype(np.uint8)
    ys, xs = np.where(m > 0)
    if len(ys) == 0:
        return (x1, y1, x2-x1+1, y2-y1+1)
    return (x1 + int(np.min(xs)), y1 + int(np.min(ys)), int(np.max(xs) - np.min(xs) + 1), int(np.max(ys) - np.min(ys) + 1))

all_elements = [
    # Row 1
    ('01_giant_red_apple', (20, 20, 240, 265)),
    ('02_wild_sour_apple', (245, 80, 380, 255)),
    ('03_wild_branch', (380, 25, 630, 265)),
    ('04_apple_blossom_flower', (630, 90, 790, 265)),
    ('05_blooming_apple_tree', (790, 25, 1025, 265)),
    ('06_snowy_mountains_winter', (1025, 50, 1300, 265)),
    ('07_central_asia_map', (1300, 60, 1530, 265)),

    # Row 2
    ('08_roman_soldier', (10, 260, 210, 515)),
    ('09_horse_cart_apples', (215, 310, 545, 515)),
    ('10_europe_map_arrow', (545, 290, 770, 510)),
    ('11_farmer_planting', (770, 305, 1015, 510)),
    ('12_tree_stage_1_seedling', (1020, 400, 1105, 510)),
    ('12_tree_stage_2_sapling', (1115, 360, 1205, 510)),
    ('12_tree_stage_3_growing', (1215, 310, 1330, 510)),
    ('12_tree_stage_4_mature', (1335, 290, 1520, 510)),

    # Row 3
    ('13_evo_1_ancient_sour', (25, 550, 195, 660)),
    ('13_evo_2_selection_growth', (195, 560, 455, 660)),
    ('13_evo_3_giant_honeycrisp', (455, 510, 700, 660)),
    ('14_hand_picking_apple', (735, 510, 1040, 680)),
    ('15_var_1_red', (1050, 535, 1145, 665)),
    ('15_var_2_green', (1145, 535, 1235, 665)),
    ('15_var_3_yellow', (1235, 535, 1320, 665)),
    ('15_var_4_dark', (1320, 535, 1410, 665)),
    ('15_var_5_striped', (1410, 535, 1515, 665)),

    # Row 4
    ('16_seedling_cycle', (15, 675, 410, 830)),
    ('17_harvest_crate', (410, 670, 645, 830)),
    ('18_sliced_apples_juice', (645, 690, 1095, 830)),
    ('19_farmer_inspecting_apple', (1095, 670, 1295, 830)),
    ('20_check_1_green', (1300, 690, 1355, 795)),
    ('20_check_2_green', (1355, 690, 1410, 795)),
    ('20_check_3_green', (1410, 690, 1465, 795)),
    ('20_check_4_red_x', (1465, 690, 1520, 795)),

    # Row 5
    ('21_digestive_health_gut', (15, 825, 250, 1015)),
    ('22_vitamins_bubbles', (250, 840, 490, 1010)),
    ('23_heart_health_pulse', (490, 860, 705, 995)),
    ('24_wheat_fiber_apples', (705, 840, 955, 1010)),
    ('25_apple_harvest_pile', (955, 835, 1290, 1015)),
    ('26_refrigerator_modern_apples', (1290, 795, 1530, 1015)),
]

for name, (x1, y1, x2, y2) in all_elements:
    bx, by, bw, bh = get_bbox(x1, y1, x2, y2)
    print(f'"{name}": ({bx}, {by}, {bw}, {bh}),')
