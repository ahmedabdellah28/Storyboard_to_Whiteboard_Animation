import os
import cv2
import numpy as np

# Test the new decoupled row and larger element layout for Section 01: Apple
WIDTH, HEIGHT = 1920, 1080
CAM_ZOOM = 0.55
CAM_X = 2040.0

# 5 Decoupled Row Y Centers
ROW_Y = {
    1: 500.0,
    2: 2000.0,
    3: 3500.0,
    4: 5000.0,
    5: 6500.0
}

# Original raw bounds for each row (xmin, xmax, ymin, ymax)
ROW_BOUNDS = {
    1: (25, 1530, 25, 270),
    2: (15, 1525, 260, 520),
    3: (25, 1520, 505, 680),
    4: (20, 1525, 670, 830),
    5: (25, 1530, 800, 1015)
}

# Target Safe Span in World Space
# Visible screen width at zoom 0.55 is 1920 / 0.55 = 3490.9 px
# Left edge = 2040 - 1745.5 = 294.5
# Right edge = 2040 + 1745.5 = 3785.5
# With 120px safe margin on each side:
SAFE_X_MIN = 450.0
SAFE_X_MAX = 3630.0
SAFE_SPAN = SAFE_X_MAX - SAFE_X_MIN # 3180 px

# Element Scale Boost: 2.75 instead of 2.5 (10% larger in world space, +23.5% larger on 1080p screen!)
ELEMENT_SCALE = 2.75

def map_element(row, rx, ry, rw, rh):
    xmin, xmax, ymin, ymax = ROW_BOUNDS[row]
    row_center_y = ROW_Y[row]
    
    # Map original rx center to safe span
    rcx = rx + rw / 2.0
    rcy = ry + rh / 2.0
    
    # Normalized position across row [0.0, 1.0]
    norm_x = (rcx - xmin) / float(xmax - xmin)
    world_cx = SAFE_X_MIN + norm_x * SAFE_SPAN
    
    # Relative vertical offset from row midline
    orig_row_mid = (ymin + ymax) / 2.0
    rel_y = (rcy - orig_row_mid) * ELEMENT_SCALE
    world_cy = row_center_y + rel_y
    
    world_w = rw * ELEMENT_SCALE
    world_h = rh * ELEMENT_SCALE
    
    world_x = world_cx - world_w / 2.0
    world_y = world_cy - world_h / 2.0
    
    # Screen projection
    scr_x = int(round(WIDTH / 2.0 + (world_x - CAM_X) * CAM_ZOOM))
    scr_y = int(round(HEIGHT / 2.0 + (world_y - row_center_y) * CAM_ZOOM))
    scr_w = int(round(world_w * CAM_ZOOM))
    scr_h = int(round(world_h * CAM_ZOOM))
    
    return (int(round(world_x)), int(round(world_y)), int(round(world_w)), int(round(world_h))), (scr_x, scr_y, scr_w, scr_h)

# Test Row 1 elements
r1_elements = [
    ('01_giant_red_apple', (32, 31, 196, 221)),
    ('02_wild_sour_apple', (257, 94, 113, 144)),
    ('03_wild_branch', (386, 38, 245, 228)),
    ('04_apple_blossom_flower', (630, 90, 154, 176)),
    ('05_blooming_apple_tree', (803, 36, 213, 224)),
    ('06_snowy_mountains_winter', (1028, 57, 258, 203)),
    ('07_central_asia_map', (1306, 75, 218, 189)),
]

assets_dir = "sections/01_apple/assets"
test_frame = np.full((HEIGHT, WIDTH, 3), 255, dtype=np.uint8)

print("Row 1 Screen Projections (1920x1080):")
for name, (rx, ry, rw, rh) in r1_elements:
    world_box, (sx, sy, sw, sh) = map_element(1, rx, ry, rw, rh)
    print(f"  {name:28s}: Screen X={sx:4d}..{sx+sw:4d}, Y={sy:4d}..{sy+sh:4d}, Size={sw:3d}x{sh:3d}")
    
    # Draw on test frame
    p = os.path.join(assets_dir, f"{name}.png")
    if os.path.exists(p):
        sprite = cv2.imread(p, cv2.IMREAD_UNCHANGED)
        if sprite is not None:
            resized = cv2.resize(sprite, (sw, sh), interpolation=cv2.INTER_AREA)
            
            # Blend
            x1, y1 = max(0, sx), max(0, sy)
            x2, y2 = min(WIDTH, sx + sw), min(HEIGHT, sy + sh)
            if x2 > x1 and y2 > y1:
                crop = resized[y1-sy:y2-sy, x1-sx:x2-sx]
                alpha = crop[:, :, 3].astype(np.float32) / 255.0
                alpha_3 = cv2.merge([alpha, alpha, alpha])
                dst = test_frame[y1:y2, x1:x2].astype(np.float32)
                src = crop[:, :, :3].astype(np.float32)
                test_frame[y1:y2, x1:x2] = (src * alpha_3 + dst * (1.0 - alpha_3)).astype(np.uint8)

os.makedirs("sections/01_apple/layout_preview", exist_ok=True)
cv2.imwrite("sections/01_apple/layout_preview/test_row1_frame.png", test_frame)
print("Saved sections/01_apple/layout_preview/test_row1_frame.png successfully!")
