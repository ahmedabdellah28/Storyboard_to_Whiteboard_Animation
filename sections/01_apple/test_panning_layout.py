import os
import cv2
import numpy as np

WIDTH, HEIGHT = 1920, 1080
ZOOM = 0.62  # Crisp, large element zoom (visible world width = 1920 / 0.62 ≈ 3096 px)

# Row 1 Elements: spaced out with clear horizontal gaps (NO OVERLAP / NO CLUTTER!)
# Let's specify exact element widths and comfortable gaps
# Element sizes scaled up by 1.3x from original
scale = 3.2

# Original elements with scaled sizes
r1_specs = [
    # id, name, orig_w, orig_h, gap_after
    ("01_giant", "01_giant_red_apple", 196, 221, 160),
    ("02_wild",  "02_wild_sour_apple",  113, 144, 140),
    ("03_branch","03_wild_branch",      245, 228, 150),
    ("04_flower","04_apple_blossom_flower", 154, 176, 200), # Bigger gap before the shift to Asia/Wild forest!
    ("05_tree",  "05_blooming_apple_tree", 213, 224, 150),
    ("06_mount", "06_snowy_mountains_winter", 258, 203, 140),
    ("07_map",   "07_central_asia_map", 218, 189, 0),
]

# Calculate spaced out X positions starting at X = 400
current_x = 400.0
r1_elements_placed = []
for eid, name, ow, oh, gap in r1_specs:
    w = int(round(ow * scale))
    h = int(round(oh * scale))
    # Vertical alignment: align bottoms or centers comfortably
    # Row baseline Y = 600
    y = int(round(600 - h / 2.0))
    r1_elements_placed.append((eid, name, int(round(current_x)), y, w, h))
    current_x += w + gap

total_row_width = current_x - 400.0
print(f"Total Row 1 Width with generous gaps: {total_row_width:.1f} px")
for e in r1_elements_placed:
    print(f"  {e[1]:28s}: World X = {e[2]:4d}..{e[2]+e[4]:4d}, Y = {e[3]:4d}..{e[3]+e[5]:4d}, Size = {e[4]:3d}x{e[5]:3d}")

# Two Camera Anchors for Row 1:
# Zone A (Left): frames Giant Apple, Wild Apple, Branch, Blossom (X from 400 to ~2400)
# Center A: (400 + 2400) / 2 = 1400.0
# Zone B (Right): frames Tree, Mountains, Asia Map (X from ~2200 to ~4600)
# Center B: (2200 + 4600) / 2 = 3400.0

cam_A = (1350.0, 600.0, ZOOM)
cam_B = (3450.0, 600.0, ZOOM)

assets_dir = "sections/01_apple/assets"
os.makedirs("sections/01_apple/layout_preview", exist_ok=True)

def render_camera_view(cam_pos, filename):
    cx, cy, cz = cam_pos
    frame = np.full((HEIGHT, WIDTH, 3), 255, dtype=np.uint8)
    
    for eid, name, ex, ey, ew, eh in r1_elements_placed:
        # Screen projection
        sx = int(round(WIDTH / 2.0 + (ex - cx) * cz))
        sy = int(round(HEIGHT / 2.0 + (ey - cy) * cz))
        sw = int(round(ew * cz))
        sh = int(round(eh * cz))
        
        # Frustum cull
        if sx + sw < 0 or sx >= WIDTH or sy + sh < 0 or sy >= HEIGHT:
            continue
            
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
                    dst = frame[y1:y2, x1:x2].astype(np.float32)
                    src = crop[:, :, :3].astype(np.float32)
                    frame[y1:y2, x1:x2] = (src * alpha_3 + dst * (1.0 - alpha_3)).astype(np.uint8)
                    
    cv2.imwrite(filename, frame)
    print(f"Saved {filename}")

render_camera_view(cam_A, "sections/01_apple/layout_preview/row1_zone_A.png")
render_camera_view(cam_B, "sections/01_apple/layout_preview/row1_zone_B.png")
