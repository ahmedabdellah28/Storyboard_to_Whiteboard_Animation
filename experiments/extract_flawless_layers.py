import os
import cv2
import numpy as np

clean_base = "experiments/choreographed_layers"
out_base = "experiments/flawless_layers"
os.makedirs(out_base, exist_ok=True)

def make_solid_rgba(img_bgr, spatial_mask):
    """
    Creates RGBA image where foreground within spatial_mask retains
    100% of its original colors, skin, clothing, and shading.
    """
    h, w = img_bgr.shape[:2]
    # A pixel is ink/content if it is not pure background white
    b, g, r = cv2.split(img_bgr)
    # Background paper is pure white
    is_paper = (b >= 246) & (g >= 246) & (r >= 246)
    
    # Foreground is everything not paper, restricted to spatial_mask
    fg_mask = (~is_paper) & spatial_mask
    
    # Fill small interior gaps (white highlights, eye reflections, collar)
    # Using morphological closing on fg_mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    fg_closed = cv2.morphologyEx(fg_mask.astype(np.uint8) * 255, cv2.MORPH_CLOSE, kernel)
    
    # Find bounding box of content
    ys, xs = np.where(fg_closed > 0)
    if len(ys) == 0:
        return None, 0, 0, 0, 0
    
    x1, x2 = int(np.min(xs)), int(np.max(xs))
    y1, y2 = int(np.min(ys)), int(np.max(ys))
    
    # Crop
    crop_bgr = img_bgr[y1:y2+1, x1:x2+1].copy()
    crop_a = fg_closed[y1:y2+1, x1:x2+1].copy()
    
    # Soften outer edge slightly for antialiasing
    crop_a_blur = cv2.GaussianBlur(crop_a, (3, 3), 0)
    
    cb, cg, cr = cv2.split(crop_bgr)
    rgba = cv2.merge([cb, cg, cr, crop_a_blur])
    return rgba, x1, y1, x2 - x1 + 1, y2 - y1 + 1

# ================= PANEL 1 =================
p1_dir = os.path.join(out_base, "panel_01")
os.makedirs(p1_dir, exist_ok=True)
p1_img = cv2.imread("experiments/choreographed_layers/panel_01/clean_panel.png")
h, w = p1_img.shape[:2]

# 1. Narrator (Left): x < 330
m_narrator = np.zeros((h, w), dtype=bool)
m_narrator[:, :330] = True
r1, x1, y1, w1, h1 = make_solid_rgba(p1_img, m_narrator)
cv2.imwrite(os.path.join(p1_dir, "narrator.png"), r1)
open(os.path.join(p1_dir, "narrator.txt"), "w").write(f"{x1},{y1},{w1},{h1}")

# 2. Thermometer (Middle): 330 <= x <= 550
m_thermo = np.zeros((h, w), dtype=bool)
m_thermo[:, 330:550] = True
r2, x2, y2, w2, h2 = make_solid_rgba(p1_img, m_thermo)
cv2.imwrite(os.path.join(p1_dir, "thermometer.png"), r2)
open(os.path.join(p1_dir, "thermometer.txt"), "w").write(f"{x2},{y2},{w2},{h2}")

# 3. Crowd & 2% (Right): x > 550
m_crowd = np.zeros((h, w), dtype=bool)
m_crowd[:, 550:] = True
r3, x3, y3, w3, h3 = make_solid_rgba(p1_img, m_crowd)
cv2.imwrite(os.path.join(p1_dir, "crowd_complete.png"), r3)
open(os.path.join(p1_dir, "crowd_complete.txt"), "w").write(f"{x3},{y3},{w3},{h3}")
print("Panel 1 flawless layers extracted!")

# ================= PANEL 2 =================
p2_dir = os.path.join(out_base, "panel_02")
os.makedirs(p2_dir, exist_ok=True)
p2_img = cv2.imread("experiments/choreographed_layers/panel_02/clean_panel.png")

# 1. Saturn (Top-Left): y < 290 and x < 490
m_saturn = np.zeros((h, w), dtype=bool)
m_saturn[:290, :490] = True
rs, xs, ys, ws, hs = make_solid_rgba(p2_img, m_saturn)
cv2.imwrite(os.path.join(p2_dir, "saturn.png"), rs)
open(os.path.join(p2_dir, "saturn.txt"), "w").write(f"{xs},{ys},{ws},{hs}")

# 2. Charts (Top-Right): y < 350 and x >= 490
m_charts = np.zeros((h, w), dtype=bool)
m_charts[:350, 490:] = True
rc, xc, yc, wc, hc = make_solid_rgba(p2_img, m_charts)
cv2.imwrite(os.path.join(p2_dir, "charts.png"), rc)
open(os.path.join(p2_dir, "charts.txt"), "w").write(f"{xc},{yc},{wc},{hc}")

# 3. Math Symbols (Mid-Right): 350 <= y < 620 and x >= 550
m_math = np.zeros((h, w), dtype=bool)
m_math[350:620, 550:] = True
rm, xm, ym, wm, hm = make_solid_rgba(p2_img, m_math)
cv2.imwrite(os.path.join(p2_dir, "math_symbols.png"), rm)
open(os.path.join(p2_dir, "math_symbols.txt"), "w").write(f"{xm},{ym},{wm},{hm}")

# 4. Stressed Person (Bottom-Right): y >= 620 and x >= 550
m_stressed = np.zeros((h, w), dtype=bool)
m_stressed[620:, 550:] = True
rst, xst, yst, wst, hst = make_solid_rgba(p2_img, m_stressed)
cv2.imwrite(os.path.join(p2_dir, "stressed_person.png"), rst)
open(os.path.join(p2_dir, "stressed_person.txt"), "w").write(f"{xst},{yst},{wst},{hst}")

# 5. Warning Badge (Bottom-Center): y >= 740 and 420 <= x < 550
m_warn = np.zeros((h, w), dtype=bool)
m_warn[740:, 420:550] = True
rw, xw, yw, ww, hw = make_solid_rgba(p2_img, m_warn)
cv2.imwrite(os.path.join(p2_dir, "warning_error.png"), rw)
open(os.path.join(p2_dir, "warning_error.txt"), "w").write(f"{xw},{yw},{ww},{hw}")

# 6. Profile Character with Brain & Masks (Remaining Central-Left):
m_char = ~(m_saturn | m_charts | m_math | m_stressed | m_warn)
rch, xch, ych, wch, hch = make_solid_rgba(p2_img, m_char)
cv2.imwrite(os.path.join(p2_dir, "profile_thinker.png"), rch)
open(os.path.join(p2_dir, "profile_thinker.txt"), "w").write(f"{xch},{ych},{wch},{hch}")
print("Panel 2 flawless layers extracted!")

# ================= PANEL 3 =================
p3_dir = os.path.join(out_base, "panel_03")
os.makedirs(p3_dir, exist_ok=True)
p3_img = cv2.imread("experiments/choreographed_layers/panel_03/clean_panel.png")

# Dual Brain in Center: 180 <= x <= 720 and 120 <= y <= 760
m_brain = np.zeros((h, w), dtype=bool)
m_brain[120:760, 180:720] = True
rb, xb, yb, wb, hb = make_solid_rgba(p3_img, m_brain)
cv2.imwrite(os.path.join(p3_dir, "dual_brain.png"), rb)
open(os.path.join(p3_dir, "dual_brain.txt"), "w").write(f"{xb},{yb},{wb},{hb}")

# Surrounding Icons: everything else
m_icons = ~m_brain
ri, xi, yi, wi, hi = make_solid_rgba(p3_img, m_icons)
cv2.imwrite(os.path.join(p3_dir, "mind_icons.png"), ri)
open(os.path.join(p3_dir, "mind_icons.txt"), "w").write(f"{xi},{yi},{wi},{hi}")
print("Panel 3 flawless layers extracted!")

# ================= PANEL 4 =================
p4_dir = os.path.join(out_base, "panel_04")
os.makedirs(p4_dir, exist_ok=True)
p4_img = cv2.imread("experiments/choreographed_layers/panel_04/clean_panel.png")

# Top: The 3 Growth Figures: y < 600
m_figures = np.zeros((h, w), dtype=bool)
m_figures[:600, :] = True
rf, xf, yf, wf, hf = make_solid_rgba(p4_img, m_figures)
cv2.imwrite(os.path.join(p4_dir, "growth_figures.png"), rf)
open(os.path.join(p4_dir, "growth_figures.txt"), "w").write(f"{xf},{yf},{wf},{hf}")

# Bottom: Learning Icons: y >= 600
m_learn = np.zeros((h, w), dtype=bool)
m_learn[600:, :] = True
rl, xl, yl, wl, hl = make_solid_rgba(p4_img, m_learn)
cv2.imwrite(os.path.join(p4_dir, "learning_elements.png"), rl)
open(os.path.join(p4_dir, "learning_elements.txt"), "w").write(f"{xl},{yl},{wl},{hl}")
print("Panel 4 flawless layers extracted!")

# ================= PANEL 5 =================
p5_dir = os.path.join(out_base, "panel_05")
os.makedirs(p5_dir, exist_ok=True)
p5_img = cv2.imread("experiments/choreographed_layers/panel_05/clean_panel.png")

# Central Thinker: x between 140 and 720, y > 320
m_thinker = np.zeros((h, w), dtype=bool)
m_thinker[320:, 140:720] = True
# Exclude right-bottom bubble (plant): x > 650 and y > 560
m_thinker[560:, 650:] = False
rth, xth, yth, wth, hth = make_solid_rgba(p5_img, m_thinker)
cv2.imwrite(os.path.join(p5_dir, "thinker_char.png"), rth)
open(os.path.join(p5_dir, "thinker_char.txt"), "w").write(f"{xth},{yth},{wth},{hth}")

# The 6 Thought Bubbles:
# 1. House: x < 350, y < 350
m_b1 = np.zeros((h, w), dtype=bool); m_b1[:350, :350] = True
r_b1, xb1, yb1, wb1, hb1 = make_solid_rgba(p5_img, m_b1)
cv2.imwrite(os.path.join(p5_dir, "b_house.png"), r_b1)
open(os.path.join(p5_dir, "b_house.txt"), "w").write(f"{xb1},{yb1},{wb1},{hb1}")

# 2. People: 350 <= x <= 580, y < 300
m_b2 = np.zeros((h, w), dtype=bool); m_b2[:300, 350:580] = True
r_b2, xb2, yb2, wb2, hb2 = make_solid_rgba(p5_img, m_b2)
cv2.imwrite(os.path.join(p5_dir, "b_people.png"), r_b2)
open(os.path.join(p5_dir, "b_people.txt"), "w").write(f"{xb2},{yb2},{wb2},{hb2}")

# 3. Money: x > 580, y < 350
m_b3 = np.zeros((h, w), dtype=bool); m_b3[:350, 580:] = True
r_b3, xb3, yb3, wb3, hb3 = make_solid_rgba(p5_img, m_b3)
cv2.imwrite(os.path.join(p5_dir, "b_money.png"), r_b3)
open(os.path.join(p5_dir, "b_money.txt"), "w").write(f"{xb3},{yb3},{wb3},{hb3}")

# 4. Time: x > 580, 350 <= y < 620
m_b4 = np.zeros((h, w), dtype=bool); m_b4[350:620, 580:] = True
r_b4, xb4, yb4, wb4, hb4 = make_solid_rgba(p5_img, m_b4)
cv2.imwrite(os.path.join(p5_dir, "b_time.png"), r_b4)
open(os.path.join(p5_dir, "b_time.txt"), "w").write(f"{xb4},{yb4},{wb4},{hb4}")

# 5. Plant: x > 620, y >= 620
m_b5 = np.zeros((h, w), dtype=bool); m_b5[620:, 620:] = True
r_b5, xb5, yb5, wb5, hb5 = make_solid_rgba(p5_img, m_b5)
cv2.imwrite(os.path.join(p5_dir, "b_plant.png"), r_b5)
open(os.path.join(p5_dir, "b_plant.txt"), "w").write(f"{xb5},{yb5},{wb5},{hb5}")

# 6. Heart: x < 350, y >= 350
m_b6 = np.zeros((h, w), dtype=bool); m_b6[350:, :350] = True
r_b6, xb6, yb6, wb6, hb6 = make_solid_rgba(p5_img, m_b6)
cv2.imwrite(os.path.join(p5_dir, "b_heart.png"), r_b6)
open(os.path.join(p5_dir, "b_heart.txt"), "w").write(f"{xb6},{yb6},{wb6},{hb6}")
print("Panel 5 flawless layers extracted!")

# ================= PANEL 6 =================
p6_dir = os.path.join(out_base, "panel_06")
os.makedirs(p6_dir, exist_ok=True)
p6_img = cv2.imread("experiments/choreographed_layers/panel_06/clean_panel.png")

# 1. Central Hero & Stairs (Core Journey):
# Hero: x: [0, 480], y: [400, 900]
# Stairs: x: [280, 850], y: [20, 750]
m_journey = np.zeros((h, w), dtype=bool)
# Hero
m_journey[400:, :480] = True
# Stairs & Door
m_journey[20:760, 280:850] = True
# Exclude mountain (x > 680 and y > 350)
m_journey[350:, 680:] = False
# Exclude compass (x > 500 and y > 520)
m_journey[520:, 500:] = False
# Exclude cloud & chain (x < 320 and y < 500)
m_journey[:500, :320] = False
# Exclude target (350 < x < 550 and y < 250)
m_journey[:250, 350:550] = False

rj, xj, yj, wj, hj = make_solid_rgba(p6_img, m_journey)
cv2.imwrite(os.path.join(p6_dir, "hero_journey.png"), rj)
open(os.path.join(p6_dir, "hero_journey.txt"), "w").write(f"{xj},{yj},{wj},{hj}")

# 2. Compass: x >= 500 and y >= 520
m_comp = np.zeros((h, w), dtype=bool)
m_comp[520:, 500:] = True
rcp, xcp, ycp, wcp, hcp = make_solid_rgba(p6_img, m_comp)
cv2.imwrite(os.path.join(p6_dir, "compass.png"), rcp)
open(os.path.join(p6_dir, "compass.txt"), "w").write(f"{xcp},{ycp},{wcp},{hcp}")

# 3. Mountain with Flag: x >= 680 and y >= 350
m_mount = np.zeros((h, w), dtype=bool)
m_mount[350:, 680:] = True
rmn, xmn, ymn, wmn, hmn = make_solid_rgba(p6_img, m_mount)
cv2.imwrite(os.path.join(p6_dir, "mountain_flag.png"), rmn)
open(os.path.join(p6_dir, "mountain_flag.txt"), "w").write(f"{xmn},{ymn},{wmn},{hmn}")

# 4. Obstacles (Cloud, Chain, Target): everything else
m_obs = ~(m_journey | m_comp | m_mount)
ro, xo, yo, wo, ho = make_solid_rgba(p6_img, m_obs)
cv2.imwrite(os.path.join(p6_dir, "symbols_obstacles.png"), ro)
open(os.path.join(p6_dir, "symbols_obstacles.txt"), "w").write(f"{xo},{yo},{wo},{ho}")
print("Panel 6 flawless layers extracted!")

print("All flawless layers successfully extracted across all 6 panels!")
