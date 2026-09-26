import os
import cv2
import numpy as np

WIDTH, HEIGHT = 1920, 1080
CAM_ZOOM = 0.55
CAM_X = 2040.0

ROW_Y = {
    1: 500.0,
    2: 2000.0,
    3: 3500.0,
    4: 5000.0,
    5: 6500.0
}

ROW_BOUNDS = {
    1: (25, 1530, 25, 270),
    2: (15, 1525, 260, 520),
    3: (25, 1520, 505, 680),
    4: (20, 1525, 670, 830),
    5: (25, 1530, 800, 1015)
}

SAFE_X_MIN = 450.0
SAFE_X_MAX = 3630.0
SAFE_SPAN = SAFE_X_MAX - SAFE_X_MIN

ELEMENT_SCALE = 2.75

def map_element(row, rx, ry, rw, rh):
    xmin, xmax, ymin, ymax = ROW_BOUNDS[row]
    row_center_y = ROW_Y[row]
    
    rcx = rx + rw / 2.0
    rcy = ry + rh / 2.0
    
    norm_x = (rcx - xmin) / float(xmax - xmin)
    world_cx = SAFE_X_MIN + norm_x * SAFE_SPAN
    
    orig_row_mid = (ymin + ymax) / 2.0
    rel_y = (rcy - orig_row_mid) * ELEMENT_SCALE
    world_cy = row_center_y + rel_y
    
    world_w = rw * ELEMENT_SCALE
    world_h = rh * ELEMENT_SCALE
    
    world_x = world_cx - world_w / 2.0
    world_y = world_cy - world_h / 2.0
    
    scr_x = int(round(WIDTH / 2.0 + (world_x - CAM_X) * CAM_ZOOM))
    scr_y = int(round(HEIGHT / 2.0 + (world_y - row_center_y) * CAM_ZOOM))
    scr_w = int(round(world_w * CAM_ZOOM))
    scr_h = int(round(world_h * CAM_ZOOM))
    
    return (int(round(world_x)), int(round(world_y)), int(round(world_w)), int(round(world_h))), (scr_x, scr_y, scr_w, scr_h)

all_rows = {
    1: [
        ('01_giant_red_apple', (32, 31, 196, 221)),
        ('02_wild_sour_apple', (257, 94, 113, 144)),
        ('03_wild_branch', (386, 38, 245, 228)),
        ('04_apple_blossom_flower', (630, 90, 154, 176)),
        ('05_blooming_apple_tree', (803, 36, 213, 224)),
        ('06_snowy_mountains_winter', (1028, 57, 258, 203)),
        ('07_central_asia_map', (1306, 75, 218, 189)),
    ],
    2: [
        ('08_roman_soldier', (18, 270, 180, 239)),
        ('09_horse_cart_apples', (226, 325, 314, 186)),
        ('10_europe_map_arrow', (550, 301, 212, 197)),
        ('11_farmer_planting', (775, 312, 235, 194)),
        ('12_tree_stage_1_seedling', (1027, 408, 71, 98)),
        ('12_tree_stage_2_sapling', (1124, 367, 74, 139)),
        ('12_tree_stage_3_growing', (1222, 317, 102, 189)),
        ('12_tree_stage_4_mature', (1341, 298, 174, 208)),
    ],
    3: [
        ('13_evo_1_ancient_sour', (34, 558, 154, 98)),
        ('13_evo_2_selection_growth', (202, 568, 246, 88)),
        ('13_evo_3_giant_honeycrisp', (462, 518, 231, 138)),
        ('14_hand_picking_apple', (742, 518, 291, 158)),
        ('15_var_1_red', (1057, 542, 81, 119)),
        ('15_var_2_green', (1152, 542, 76, 119)),
        ('15_var_3_yellow', (1242, 542, 71, 119)),
        ('15_var_4_dark', (1327, 542, 76, 119)),
        ('15_var_5_striped', (1417, 542, 91, 119)),
    ],
    4: [
        ('16_seedling_cycle', (26, 702, 351, 107)),
        ('17_harvest_crate', (423, 680, 211, 144)),
        ('18_sliced_apples_juice', (653, 690, 414, 133)),
        ('19_farmer_inspecting_apple', (1108, 678, 179, 145)),
        ('20_check_1_green', (1301, 701, 55, 90)),
        ('20_check_2_green', (1355, 701, 56, 90)),
        ('20_check_3_green', (1410, 701, 56, 90)),
        ('20_check_4_red_x', (1465, 701, 52, 90)),
    ],
    5: [
        ('21_digestive_health_gut', (32, 833, 199, 162)),
        ('22_vitamins_bubbles', (261, 850, 211, 143)),
        ('23_heart_health_pulse', (501, 873, 190, 109)),
        ('24_wheat_fiber_apples', (713, 849, 215, 146)),
        ('25_apple_harvest_pile', (966, 844, 275, 152)),
        ('26_refrigerator_modern_apples', (1300, 806, 219, 192)),
    ]
}

assets_dir = "sections/01_apple/assets"
os.makedirs("sections/01_apple/layout_preview", exist_ok=True)

for r_idx in range(1, 6):
    test_frame = np.full((HEIGHT, WIDTH, 3), 255, dtype=np.uint8)
    for name, (rx, ry, rw, rh) in all_rows[r_idx]:
        world_box, (sx, sy, sw, sh) = map_element(r_idx, rx, ry, rw, rh)
        p = os.path.join(assets_dir, f"{name}.png")
        if os.path.exists(p):
            sprite = cv2.imread(p, cv2.IMREAD_UNCHANGED)
            if sprite is not None:
                resized = cv2.resize(sprite, (sw, sh), interpolation=cv2.INTER_AREA)
                x1, y1 = max(0, sx), max(0, sy)
                x2, y2 = min(WIDTH, sx + sw), min(HEIGHT, sy + sh)
                if x2 > x1 and y2 > y1:
                    crop = resized[y1-sy:y2-sy, x1-sx:x2-sx]
                    alpha = crop[:, :, 3].astype(np.float32) / 255.0
                    alpha_3 = cv2.merge([alpha, alpha, alpha])
                    dst = test_frame[y1:y2, x1:x2].astype(np.float32)
                    src = crop[:, :, :3].astype(np.float32)
                    test_frame[y1:y2, x1:x2] = (src * alpha_3 + dst * (1.0 - alpha_3)).astype(np.uint8)
    
    out_img = f"sections/01_apple/layout_preview/row_{r_idx}.png"
    cv2.imwrite(out_img, test_frame)
    print(f"Saved {out_img}")

print("All 5 rows successfully verified!")
