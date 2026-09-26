import os
import cv2
import numpy as np

src_dir = "experiments/apple_storyboard"
out_dir = "experiments/apple_elements"
os.makedirs(out_dir, exist_ok=True)

def extract_element(panel_img, mask, name):
    b, g, r = cv2.split(panel_img)
    # Ensure white background is transparent, content is opaque
    # Paper threshold
    is_paper = (b >= 246) & (g >= 246) & (r >= 246)
    alpha = ((~is_paper) & mask).astype(np.uint8) * 255
    
    # Close small interior gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    alpha_closed = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel)
    
    ys, xs = np.where(alpha_closed > 0)
    if len(ys) == 0:
        return None
    x1, x2 = int(np.min(xs)), int(np.max(xs))
    y1, y2 = int(np.min(ys)), int(np.max(ys))
    
    crop_bgr = panel_img[y1:y2+1, x1:x2+1]
    crop_a = alpha_closed[y1:y2+1, x1:x2+1]
    crop_a_blur = cv2.GaussianBlur(crop_a, (3, 3), 0)
    
    cb, cg, cr = cv2.split(crop_bgr)
    rgba = cv2.merge([cb, cg, cr, crop_a_blur])
    
    out_p = os.path.join(out_dir, f"{name}.png")
    cv2.imwrite(out_p, rgba)
    with open(os.path.join(out_dir, f"{name}.txt"), "w") as f:
        f.write(f"{x1},{y1},{x2-x1+1},{y2-y1+1}")
    print(f"Extracted {name}: bbox=({x1},{y1},{x2-x1+1},{y2-y1+1})")
    return rgba

# PANEL 1
p1 = cv2.imread(os.path.join(src_dir, "apple_panel_01.png"))
h, w = p1.shape[:2]

# 1. Traveler / Explorer (Left): x < 350
m_trav = np.zeros((h, w), dtype=bool)
m_trav[:, :350] = True
extract_element(p1, m_trav, "p1_traveler")

# 2. Caucasus Mountains & Forest: y > 550 and x >= 250
m_mount = np.zeros((h, w), dtype=bool)
m_mount[550:, 250:] = True
extract_element(p1, m_mount, "p1_mountains")

# 3. Wild Apple Branch: 420 <= y <= 720 and x >= 280
m_branch = np.zeros((h, w), dtype=bool)
m_branch[420:720, 280:] = True
# exclude mountains overlapping
m_branch[580:, 450:] = False
extract_element(p1, m_branch, "p1_branch")

# 4. Big Red Apple & Wild Apple: y < 450 and x >= 320
m_apples = np.zeros((h, w), dtype=bool)
m_apples[:450, 320:] = True
extract_element(p1, m_apples, "p1_apples")

# PANEL 2
p2 = cv2.imread(os.path.join(src_dir, "apple_panel_02.png"))

# 1. Roman Soldier: x < 220
m_rom = np.zeros((h, w), dtype=bool)
m_rom[:, :220] = True
extract_element(p2, m_rom, "p2_soldier")

# 2. Horse & Cart: y < 450 and x >= 180
m_cart = np.zeros((h, w), dtype=bool)
m_cart[:450, 180:] = True
extract_element(p2, m_cart, "p2_horse_cart")

# 3. Farmer & Apple Trees: 400 <= y < 750 and x >= 180
m_farm = np.zeros((h, w), dtype=bool)
m_farm[400:750, 180:] = True
extract_element(p2, m_farm, "p2_farmer_trees")

# 4. Apple Growth Stages: y >= 720 and x >= 180
m_stages = np.zeros((h, w), dtype=bool)
m_stages[720:, 180:] = True
extract_element(p2, m_stages, "p2_apple_stages")

# PANEL 3
p3 = cv2.imread(os.path.join(src_dir, "apple_panel_03.png"))

# 1. Selecting Hand & Apples: y < 450 and x >= 350
m_hand = np.zeros((h, w), dtype=bool)
m_hand[:450, 350:] = True
extract_element(p3, m_hand, "p3_hand_selection")

# 2. Wild-to-Cultivated Arrow & Progress Apples: y >= 400 and x < 620
m_prog = np.zeros((h, w), dtype=bool)
m_prog[400:, :620] = True
extract_element(p3, m_prog, "p3_evolution_progression")

# 3. Giant Final Modern Apple: y >= 400 and x >= 620
m_giant = np.zeros((h, w), dtype=bool)
m_giant[400:, 620:] = True
extract_element(p3, m_giant, "p3_giant_apple")

print("All apple elements extracted flawlessly!")
