"""
Apple Storyboard Masterpiece 2026 Production Engine (v2 - Calibrated to Storyboard Layout)
- Sequence and spatial positions 100% strictly matched to the storyboard image (5 Rows, Left to Right)
- Moderate, comfortable whiteboard camera distance (Zoom ~1.02, completely eliminating excessive close-ups)
- Smooth horizontal reading pans along each row matching narrative flow
- Genuine Layer-Fill Outside-In Orbital Pen Inking with Hand Sprite (Zero Missing Pixels / Zero Holes)
- 100% Solid Full-Alpha Sprite Reveal on Inking Completion
- Sequential Piece-by-Piece Drawing/Reveal of Multi-Part Elements:
  * 4 Tree Stages (Seedling -> Sapling -> Growing -> Mature)
  * 3 Evolution Stages (Sour Ancient -> Selection Growth Arrow -> Giant Honeycrisp)
  * 5 Rainbow Varieties (Red -> Green -> Yellow -> Dark -> Striped)
  * 4 Quality Checkboxes (Check -> Check -> Check -> Red X)
- Zero Overlap Spatial Staging (Directly scaled from master reference layout)
- Grand Outro Panoramic Zoom-out Reveal (0.44x) revealing the entire 5-row storyboard
- Stereo 48kHz Ducked Audio with Subtle, Gentle 50% Reduced SFX
"""
import os
import sys
import math
import cv2
import numpy as np
import subprocess

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
kivy_dir = os.path.join(ROOT_DIR, 'kivy')
if kivy_dir not in sys.path:
    sys.path.insert(0, kivy_dir)

from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
from engine.render.concentric_engine import build_gapless_orbital_path

sys.stdout.reconfigure(line_buffering=True)

# Video Parameters
WIDTH, HEIGHT = 1920, 1080
FPS = 30
TOTAL_DURATION = 60.88
TOTAL_FRAMES = int(TOTAL_DURATION * FPS) # 1826 frames

# Storyboard 5-Row Canvas (Scaled 2.5x from 1536x1024 with 120px margins)
SCALE = 2.5
PAD_X = 120
PAD_Y = 120
CANVAS_W = int(1536 * SCALE + 2 * PAD_X) # 4080
CANVAS_H = int(1024 * SCALE + 2 * PAD_Y) # 2800

# Hand Sprite Assets
HAND_PATH = r"E:\image_to_animate\kivy\data\images\drawing-hand.png"
HAND_MASK_PATH = r"E:\image_to_animate\kivy\data\images\hand-mask.png"
raw_hand = load_hand_asset_bgra(HAND_PATH, HAND_MASK_PATH)
if raw_hand is not None:
    hh, hw = raw_hand.shape[:2]
    # Hand scaled to natural size on 1080p screen (height = 500px)
    TARGET_HAND_H = 500
    TARGET_HAND_W = int(hw * (TARGET_HAND_H / hh))
    hand_bgra = cv2.resize(raw_hand, (TARGET_HAND_W, TARGET_HAND_H), interpolation=cv2.INTER_AREA)
    HAND_TIP_X = int(round(62 * (TARGET_HAND_H / hh)))
    HAND_TIP_Y = int(round(40 * (TARGET_HAND_H / hh)))
else:
    hand_bgra = None
    HAND_TIP_X, HAND_TIP_Y = 33, 21

# Easing Functions
def smootherstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

def ease_out_back(t: float, overshoot: float = 1.30) -> float:
    t = max(0.0, min(1.0, t)) - 1.0
    return t * t * ((overshoot + 1.0) * t + overshoot) + 1.0

def get_jelly_scales(t: float) -> tuple:
    t = max(0.0, min(1.0, t))
    if t >= 1.0: return 1.0, 1.0
    if t <= 0.0: return 0.0, 0.0
    decay = math.exp(-t * 5.2)
    osc = decay * math.cos(18.0 * t)
    base = 1.0 - math.pow(1.0 - t, 4)
    return max(0.01, base + 0.35 * osc), max(0.01, base - 0.28 * osc)

# Load All Assets & Sub-Assets
assets_dir = "experiments/exact_contour_assets"
asset_names = [
    # Base Assets
    "01_giant_red_apple", "02_wild_sour_apple", "03_wild_branch", "04_apple_blossom_flower",
    "05_blooming_apple_tree", "06_snowy_mountains_winter", "07_central_asia_map",
    "08_roman_soldier", "09_horse_cart_apples", "10_europe_map_arrow",
    "11_farmer_planting", "14_hand_picking_apple",
    "16_seedling_cycle", "17_harvest_crate", "18_sliced_apples_juice",
    "19_farmer_inspecting_apple",
    "21_digestive_health_gut", "22_vitamins_bubbles", "23_heart_health_pulse",
    "24_wheat_fiber_apples", "25_apple_harvest_pile", "26_refrigerator_modern_apples",
    # Tree Stages Sub-Assets (4 Pieces)
    "12_tree_stage_1_seedling", "12_tree_stage_2_sapling", "12_tree_stage_3_growing", "12_tree_stage_4_mature",
    # Evolution Scale Sub-Assets (3 Pieces)
    "13_evo_1_ancient_sour", "13_evo_2_selection_growth", "13_evo_3_giant_honeycrisp",
    # Rainbow Varieties Sub-Assets (5 Pieces)
    "15_var_1_red", "15_var_2_green", "15_var_3_yellow", "15_var_4_dark", "15_var_5_striped",
    # Quality Checkboxes Sub-Assets (4 Pieces)
    "20_check_1_green", "20_check_2_green", "20_check_3_green", "20_check_4_red_x"
]

assets = {}
for name in asset_names:
    path = os.path.join(assets_dir, f"{name}.png")
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None:
        raise FileNotFoundError(f"Missing asset: {path}")
    assets[name] = im

print(f"Loaded {len(assets)} exact-contour assets and sub-assets.")

# Pre-generate Layer-Fill Outside-In Inking Cache
def build_solid_inking_cache(asset, t_dur, fps=30, ring_step=5):
    ah, aw = asset.shape[:2]
    mask = (asset[:, :, 3] > 10).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ring_step * 2 + 1, ring_step * 2 + 1))
    
    layer_masks = []
    curr = mask.copy()
    while cv2.countNonZero(curr) > 0 and len(layer_masks) < 150:
        layer_masks.append(curr.copy())
        eroded = cv2.erode(curr, kernel)
        if cv2.countNonZero(eroded) == cv2.countNonZero(curr):
            break
        curr = eroded
    num_layers = len(layer_masks)
    
    strokes = build_gapless_orbital_path(
        asset[:, :, :3], ring_step=ring_step, sample_interval=3.0,
        brush_radius=10, drawing_direction='OUTSIDE_IN', mask=mask
    )
    flat_pts = [p for s in strokes for p in s]
    n_pts = len(flat_pts)
    draw_frames = int(t_dur * fps)
    
    frames = []
    for f in range(draw_frames):
        prog = (f + 1) / float(draw_frames)
        active_layer = min(num_layers - 1, int(prog * num_layers))
        
        if active_layer > 0:
            solid_outer = cv2.bitwise_and(mask, cv2.bitwise_not(layer_masks[active_layer]))
        else:
            solid_outer = np.zeros((ah, aw), dtype=np.uint8)
            
        cur_idx = min(n_pts - 1, int(prog * n_pts))
        tip_pos = flat_pts[cur_idx] if n_pts > 0 else (aw / 2, ah / 2)
        
        start_pt_idx = max(0, int((active_layer / float(num_layers)) * n_pts))
        brush_mask = solid_outer.copy()
        for pi in range(start_pt_idx, cur_idx + 1):
            p = flat_pts[pi]
            cv2.circle(brush_mask, (int(round(p[0])), int(round(p[1]))), 10, 255, -1)
            
        if prog >= 0.95:
            blend_w = (prog - 0.95) / 0.05
            final_alpha = (brush_mask.astype(np.float32) * (1.0 - blend_w) + mask.astype(np.float32) * blend_w).astype(np.uint8)
        else:
            final_alpha = brush_mask
            
        inked = asset.copy()
        inked[:, :, 3] = cv2.bitwise_and(asset[:, :, 3], final_alpha)
        frames.append((inked, tip_pos))
        
    return frames

hero_cache = {}
hero_configs = [
    ("01_giant_red_apple", 0.25, 2.8),
    ("08_roman_soldier", 14.3, 3.2),
    ("11_farmer_planting", 20.6, 1.8)
]
for h_name, t_start, t_dur in hero_configs:
    asset = assets[h_name]
    ah, aw = asset.shape[:2]
    cf = build_solid_inking_cache(asset, t_dur, FPS, ring_step=5)
    hero_cache[h_name] = {
        't_start': t_start,
        't_dur': t_dur,
        'frames': cf,
        'orig_size': (aw, ah)
    }
    print(f"Pre-cached 100% Solid Inking for {h_name}: {len(cf)} frames")

# 5 Rows Staging directly mapped from the storyboard image
# Scaled by 2.5 with PAD_X = 120, PAD_Y = 120
def S_BOX(rx, ry, rw, rh):
    return (int(round(PAD_X + rx * SCALE)), int(round(PAD_Y + ry * SCALE)), int(round(rw * SCALE)), int(round(rh * SCALE)))

elements_staging = [
    # === ROW 1: Origins & Wild Apples (0.0s - 14.0s) [Word-for-Word Synchronized] ===
    {
        'id': '01_giant_apple', 'asset': '01_giant_red_apple',
        't_start': 0.25, 't_dur': 2.8, 'type': 'outside_in_pen', # "التفاح"
        'pos': (S_BOX(32, 31, 196, 221)[0], S_BOX(32, 31, 196, 221)[1]),
        'size': (S_BOX(32, 31, 196, 221)[2], S_BOX(32, 31, 196, 221)[3]),
        'depth': 5
    },
    {
        'id': '02_wild_apple', 'asset': '02_wild_sour_apple',
        't_start': 1.8, 't_dur': 1.0, 'type': 'jelly_pop', # "أشهر فاكهة في العالم"
        'pos': (S_BOX(257, 94, 113, 144)[0], S_BOX(257, 94, 113, 144)[1]),
        'size': (S_BOX(257, 94, 113, 144)[2], S_BOX(257, 94, 113, 144)[3]),
        'depth': 5
    },
    {
        'id': '03_branch', 'asset': '03_wild_branch',
        't_start': 3.2, 't_dur': 1.2, 'type': 'slide_down', # "خصوصاً في المناطق الباردة"
        'pos': (S_BOX(386, 38, 245, 228)[0], S_BOX(386, 38, 245, 228)[1]),
        'size': (S_BOX(386, 38, 245, 228)[2], S_BOX(386, 38, 245, 228)[3]),
        'depth': 3
    },
    {
        'id': '04_flower', 'asset': '04_apple_blossom_flower',
        't_start': 4.8, 't_dur': 1.0, 'type': 'jelly_pop', # "لكن الغريب إن التفاح"
        'pos': (S_BOX(630, 90, 154, 176)[0], S_BOX(630, 90, 154, 176)[1]),
        'size': (S_BOX(630, 90, 154, 176)[2], S_BOX(630, 90, 154, 176)[3]),
        'depth': 4
    },
    {
        'id': '05_tree', 'asset': '05_blooming_apple_tree',
        't_start': 6.9, 't_dur': 1.4, 'type': 'organic_grow', # "من الغابات البرية"
        'pos': (S_BOX(803, 36, 213, 224)[0], S_BOX(803, 36, 213, 224)[1]),
        'size': (S_BOX(803, 36, 213, 224)[2], S_BOX(803, 36, 213, 224)[3]),
        'depth': 2
    },
    {
        'id': '06_mountains', 'asset': '06_snowy_mountains_winter',
        't_start': 9.5, 't_dur': 1.4, 'type': 'slide_down', # "قريب من جبال القوقاز"
        'pos': (S_BOX(1028, 57, 258, 203)[0], S_BOX(1028, 57, 258, 203)[1]),
        'size': (S_BOX(1028, 57, 258, 203)[2], S_BOX(1028, 57, 258, 203)[3]),
        'depth': 1
    },
    {
        'id': '07_asia_map', 'asset': '07_central_asia_map',
        't_start': 11.0, 't_dur': 1.5, 'type': 'jelly_pop', # "في آسيا الوسطى"
        'pos': (S_BOX(1306, 75, 218, 189)[0], S_BOX(1306, 75, 218, 189)[1]),
        'size': (S_BOX(1306, 75, 218, 189)[2], S_BOX(1306, 75, 218, 189)[3]),
        'depth': 1
    },

    # === ROW 2: Roman Era & Cultivation (14.0s - 25.0s) [Word-for-Word Synchronized] ===
    {
        'id': '08_soldier', 'asset': '08_roman_soldier',
        't_start': 14.3, 't_dur': 3.2, 'type': 'outside_in_pen', # "للإمبراطورية الرومانية"
        'pos': (S_BOX(18, 270, 180, 239)[0], S_BOX(18, 270, 180, 239)[1]),
        'size': (S_BOX(18, 270, 180, 239)[2], S_BOX(18, 270, 180, 239)[3]),
        'depth': 5
    },
    {
        'id': '09_horse_cart', 'asset': '09_horse_cart_apples',
        't_start': 19.0, 't_dur': 2.5, 'type': 'travel_slide', # "أخذوا الفاكهة معهم لأوروبا"
        'pos_start': (S_BOX(226, 325, 314, 186)[0] - 150, S_BOX(226, 325, 314, 186)[1]),
        'pos_end': (S_BOX(226, 325, 314, 186)[0], S_BOX(226, 325, 314, 186)[1]),
        'size': (S_BOX(226, 325, 314, 186)[2], S_BOX(226, 325, 314, 186)[3]),
        'depth': 6
    },
    {
        'id': '10_europe_map', 'asset': '10_europe_map_arrow',
        't_start': 18.2, 't_dur': 1.2, 'type': 'slide_down', # "لأوروبا"
        'pos': (S_BOX(550, 301, 212, 197)[0], S_BOX(550, 301, 212, 197)[1]),
        'size': (S_BOX(550, 301, 212, 197)[2], S_BOX(550, 301, 212, 197)[3]),
        'depth': 1
    },
    {
        'id': '11_farmer', 'asset': '11_farmer_planting',
        't_start': 20.6, 't_dur': 1.8, 'type': 'outside_in_pen', # "بدأ المزارعين يزرعونها"
        'pos': (S_BOX(776, 319, 232, 192)[0], S_BOX(776, 319, 232, 192)[1]),
        'size': (S_BOX(776, 319, 232, 192)[2], S_BOX(776, 319, 232, 192)[3]),
        'depth': 5
    },
    # 4 Tree Stages Sequentially Growing ("ويحسنون جودتها جيل بعد جيل")
    {
        'id': '12_stage_1', 'asset': '12_tree_stage_1_seedling',
        't_start': 22.5, 't_dur': 0.8, 'type': 'organic_grow',
        'pos': (S_BOX(1024, 410, 73, 92)[0], S_BOX(1024, 410, 73, 92)[1]),
        'size': (S_BOX(1024, 410, 73, 92)[2], S_BOX(1024, 410, 73, 92)[3]),
        'depth': 4
    },
    {
        'id': '12_stage_2', 'asset': '12_tree_stage_2_sapling',
        't_start': 23.0, 't_dur': 0.8, 'type': 'organic_grow',
        'pos': (S_BOX(1118, 365, 82, 137)[0], S_BOX(1118, 365, 82, 137)[1]),
        'size': (S_BOX(1118, 365, 82, 137)[2], S_BOX(1118, 365, 82, 137)[3]),
        'depth': 4
    },
    {
        'id': '12_stage_3', 'asset': '12_tree_stage_3_growing',
        't_start': 23.6, 't_dur': 0.8, 'type': 'organic_grow',
        'pos': (S_BOX(1218, 320, 109, 179)[0], S_BOX(1218, 320, 109, 179)[1]),
        'size': (S_BOX(1218, 320, 109, 179)[2], S_BOX(1218, 320, 109, 179)[3]),
        'depth': 4
    },
    {
        'id': '12_stage_4', 'asset': '12_tree_stage_4_mature',
        't_start': 24.2, 't_dur': 1.0, 'type': 'organic_grow',
        'pos': (S_BOX(1338, 296, 177, 204)[0], S_BOX(1338, 296, 177, 204)[1]),
        'size': (S_BOX(1338, 296, 177, 204)[2], S_BOX(1338, 296, 177, 204)[3]),
        'depth': 4
    },

    # === ROW 3: Evolution Scale & Diversity (25.0s - 44.5s) [Word-for-Word Synchronized] ===
    # 3 Evolution Stages ("يختلف تقريباً 180 درجة عن النسخ القديمة")
    {
        'id': '13_evo_1', 'asset': '13_evo_1_ancient_sour',
        't_start': 25.3, 't_dur': 1.2, 'type': 'jelly_pop', # "النسخ القديمة"
        'pos': (S_BOX(27, 561, 163, 100)[0], S_BOX(27, 561, 163, 100)[1]),
        'size': (S_BOX(27, 561, 163, 100)[2], S_BOX(27, 561, 163, 100)[3]),
        'depth': 4
    },
    {
        'id': '13_evo_2', 'asset': '13_evo_2_selection_growth',
        't_start': 27.0, 't_dur': 1.0, 'type': 'slide_up', # "الحلو والمليان عصير"
        'pos': (S_BOX(198, 560, 258, 99)[0], S_BOX(198, 560, 258, 99)[1]),
        'size': (S_BOX(198, 560, 258, 99)[2], S_BOX(198, 560, 258, 99)[3]),
        'depth': 4
    },
    {
        'id': '13_evo_3', 'asset': '13_evo_3_giant_honeycrisp',
        't_start': 28.5, 't_dur': 1.4, 'type': 'jelly_pop', # "180 درجة"
        'pos': (S_BOX(455, 510, 243, 151)[0], S_BOX(455, 510, 243, 151)[1]),
        'size': (S_BOX(455, 510, 243, 151)[2], S_BOX(455, 510, 243, 151)[3]),
        'depth': 4
    },
    {
        'id': '14_hand_picking', 'asset': '14_hand_picking_apple',
        't_start': 37.0, 't_dur': 2.5, 'type': 'slide_down', # "يختارون أفضل الثمار"
        'pos': (S_BOX(744, 510, 274, 171)[0], S_BOX(744, 510, 274, 171)[1]),
        'size': (S_BOX(744, 510, 274, 171)[2], S_BOX(744, 510, 274, 171)[3]),
        'depth': 5
    },
    # 5 Rainbow Varieties Sequentially Popping ("لين طلع لنا آلاف الأنواع الحديثة")
    {
        'id': '15_var_1', 'asset': '15_var_1_red',
        't_start': 40.9, 't_dur': 0.6, 'type': 'jelly_pop',
        'pos': (S_BOX(1053, 545, 93, 117)[0], S_BOX(1053, 545, 93, 117)[1]),
        'size': (S_BOX(1053, 545, 93, 117)[2], S_BOX(1053, 545, 93, 117)[3]),
        'depth': 4
    },
    {
        'id': '15_var_2', 'asset': '15_var_2_green',
        't_start': 41.5, 't_dur': 0.6, 'type': 'jelly_pop',
        'pos': (S_BOX(1145, 550, 91, 112)[0], S_BOX(1145, 550, 91, 112)[1]),
        'size': (S_BOX(1145, 550, 91, 112)[2], S_BOX(1145, 550, 91, 112)[3]),
        'depth': 4
    },
    {
        'id': '15_var_3', 'asset': '15_var_3_yellow',
        't_start': 42.1, 't_dur': 0.6, 'type': 'jelly_pop',
        'pos': (S_BOX(1235, 548, 86, 114)[0], S_BOX(1235, 548, 86, 114)[1]),
        'size': (S_BOX(1235, 548, 86, 114)[2], S_BOX(1235, 548, 86, 114)[3]),
        'depth': 4
    },
    {
        'id': '15_var_4', 'asset': '15_var_4_dark',
        't_start': 42.7, 't_dur': 0.6, 'type': 'jelly_pop',
        'pos': (S_BOX(1320, 549, 86, 113)[0], S_BOX(1320, 549, 86, 113)[1]),
        'size': (S_BOX(1320, 549, 86, 113)[2], S_BOX(1320, 549, 86, 113)[3]),
        'depth': 4
    },
    {
        'id': '15_var_5', 'asset': '15_var_5_striped',
        't_start': 43.3, 't_dur': 0.7, 'type': 'jelly_pop',
        'pos': (S_BOX(1413, 549, 96, 113)[0], S_BOX(1413, 549, 96, 113)[1]),
        'size': (S_BOX(1413, 549, 96, 113)[2], S_BOX(1413, 549, 96, 113)[3]),
        'depth': 4
    },

    # === ROW 4: Harvest Crate, Sliced Apples & Quality (44.8s - 51.5s) [Word-for-Word Synchronized] ===
    {
        'id': '16_seedling', 'asset': '16_seedling_cycle',
        't_start': 45.1, 't_dur': 1.2, 'type': 'slide_up', # "ومن ناحية الفوائد"
        'pos': (S_BOX(26, 702, 351, 107)[0], S_BOX(26, 702, 351, 107)[1]),
        'size': (S_BOX(26, 702, 351, 107)[2], S_BOX(26, 702, 351, 107)[3]),
        'depth': 3
    },
    {
        'id': '17_crate', 'asset': '17_harvest_crate',
        't_start': 46.2, 't_dur': 1.2, 'type': 'slide_down',
        'pos': (S_BOX(423, 680, 211, 144)[0], S_BOX(423, 680, 211, 144)[1]),
        'size': (S_BOX(423, 680, 211, 144)[2], S_BOX(423, 680, 211, 144)[3]),
        'depth': 4
    },
    {
        'id': '18_sliced_juice', 'asset': '18_sliced_apples_juice',
        't_start': 48.0, 't_dur': 1.5, 'type': 'juice_burst', # "غني بالألياف"
        'pos': (S_BOX(653, 690, 414, 133)[0], S_BOX(653, 690, 414, 133)[1]),
        'size': (S_BOX(653, 690, 414, 133)[2], S_BOX(653, 690, 414, 133)[3]),
        'depth': 5
    },
    {
        'id': '19_farmer_inspect', 'asset': '19_farmer_inspecting_apple',
        't_start': 49.3, 't_dur': 1.2, 'type': 'jelly_pop', # "تساعد على الهضم"
        'pos': (S_BOX(1108, 678, 179, 145)[0], S_BOX(1108, 678, 179, 145)[1]),
        'size': (S_BOX(1108, 678, 179, 145)[2], S_BOX(1108, 678, 179, 145)[3]),
        'depth': 4
    },
    # 4 Quality Checkboxes Sequentially Popping
    {
        'id': '20_check_1', 'asset': '20_check_1_green',
        't_start': 50.2, 't_dur': 0.5, 'type': 'jelly_pop',
        'pos': (S_BOX(1301, 701, 55, 90)[0], S_BOX(1301, 701, 55, 90)[1]),
        'size': (S_BOX(1301, 701, 55, 90)[2], S_BOX(1301, 701, 55, 90)[3]),
        'depth': 6
    },
    {
        'id': '20_check_2', 'asset': '20_check_2_green',
        't_start': 50.5, 't_dur': 0.5, 'type': 'jelly_pop',
        'pos': (S_BOX(1355, 701, 56, 90)[0], S_BOX(1355, 701, 56, 90)[1]),
        'size': (S_BOX(1355, 701, 56, 90)[2], S_BOX(1355, 701, 56, 90)[3]),
        'depth': 6
    },
    {
        'id': '20_check_3', 'asset': '20_check_3_green',
        't_start': 50.8, 't_dur': 0.5, 'type': 'jelly_pop',
        'pos': (S_BOX(1410, 701, 56, 90)[0], S_BOX(1410, 701, 56, 90)[1]),
        'size': (S_BOX(1410, 701, 56, 90)[2], S_BOX(1410, 701, 56, 90)[3]),
        'depth': 6
    },
    {
        'id': '20_check_4', 'asset': '20_check_4_red_x',
        't_start': 51.1, 't_dur': 0.5, 'type': 'jelly_pop',
        'pos': (S_BOX(1465, 701, 52, 90)[0], S_BOX(1465, 701, 52, 90)[1]),
        'size': (S_BOX(1465, 701, 52, 90)[2], S_BOX(1465, 701, 52, 90)[3]),
        'depth': 6
    },

    # === ROW 5: Health & Modern Refrigerator (51.6s - 60.88s) [Word-for-Word Synchronized] ===
    {
        'id': '21_digestive', 'asset': '21_digestive_health_gut',
        't_start': 51.6, 't_dur': 1.2, 'type': 'pulse_pop', # "فيتامينات"
        'pos': (S_BOX(32, 833, 199, 162)[0], S_BOX(32, 833, 199, 162)[1]),
        'size': (S_BOX(32, 833, 199, 162)[2], S_BOX(32, 833, 199, 162)[3]),
        'depth': 4
    },
    {
        'id': '22_vitamins', 'asset': '22_vitamins_bubbles',
        't_start': 52.4, 't_dur': 1.2, 'type': 'bubble_float',
        'pos': (S_BOX(261, 850, 211, 143)[0], S_BOX(261, 850, 211, 143)[1]),
        'size': (S_BOX(261, 850, 211, 143)[2], S_BOX(261, 850, 211, 143)[3]),
        'depth': 4
    },
    {
        'id': '23_heart', 'asset': '23_heart_health_pulse',
        't_start': 53.2, 't_dur': 1.2, 'type': 'heartbeat_pop', # "عناصر غذائية"
        'pos': (S_BOX(501, 873, 190, 109)[0], S_BOX(501, 873, 190, 109)[1]),
        'size': (S_BOX(501, 873, 190, 109)[2], S_BOX(501, 873, 190, 109)[3]),
        'depth': 5
    },
    {
        'id': '24_wheat', 'asset': '24_wheat_fiber_apples',
        't_start': 54.8, 't_dur': 1.0, 'type': 'slide_up', # "باختصار"
        'pos': (S_BOX(713, 849, 215, 146)[0], S_BOX(713, 849, 215, 146)[1]),
        'size': (S_BOX(713, 849, 215, 146)[2], S_BOX(713, 849, 215, 146)[3]),
        'depth': 4
    },
    {
        'id': '25_pile', 'asset': '25_apple_harvest_pile',
        't_start': 55.5, 't_dur': 1.2, 'type': 'slide_up',
        'pos': (S_BOX(966, 844, 275, 152)[0], S_BOX(966, 844, 275, 152)[1]),
        'size': (S_BOX(966, 844, 275, 152)[2], S_BOX(966, 844, 275, 152)[3]),
        'depth': 4
    },
    {
        'id': '26_refrigerator', 'asset': '26_refrigerator_modern_apples',
        't_start': 56.5, 't_dur': 1.5, 'type': 'fridge_door_open', # "في الثلاجة اليوم"
        'pos': (S_BOX(1300, 806, 219, 192)[0], S_BOX(1300, 806, 219, 192)[1]),
        'size': (S_BOX(1300, 806, 219, 192)[2], S_BOX(1300, 806, 219, 192)[3]),
        'depth': 6
    },
]

# Comfortable, Natural Whiteboard Camera Keyframes (Zoom 0.98, Zero Right-Side Clipping)
# Synchronized with spoken phrases across each of the 5 rows
cam_keyframes = [
    # --- ROW 1 (Y ≈ 450) ---
    ( 0.0,   1100,  450, 0.98), # Left side: Hero giant apple & wild apple ("التفاح")
    ( 5.5,   1100,  450, 0.98),
    ( 7.5,   1950,  450, 0.98), # Middle: Branch, blossom, tree ("من الغابات البرية")
    ( 9.8,   3110,  450, 0.98), # Right side: Snowy mountains, Asia map ("القوقاز / آسيا")
    (13.8,   3110,  450, 0.98),
    
    # --- ROW 2 (Y ≈ 1050) ---
    (14.3,   1100, 1050, 0.98), # Left side: Roman soldier drawing ("للإمبراطورية الرومانية")
    (17.8,   1100, 1050, 0.98),
    (19.2,   1950, 1050, 0.98), # Middle: Europe map, cart, farmer planting ("يزرعونها")
    (22.0,   3110, 1050, 0.98), # Right side: Tree stages 1, 2, 3, 4 growing ("جيل بعد جيل")
    (24.8,   3110, 1050, 0.98),
    
    # --- ROW 3 (Y ≈ 1550) ---
    (25.3,   1100, 1550, 0.98), # Left side: Evolution scale 1, 2, 3 ("180 درجة عن النسخ القديمة")
    (33.5,   1100, 1550, 0.98),
    (36.5,   1950, 1550, 0.98), # Middle: Hand picking apple ("يختارون أفضل الثمار")
    (40.5,   3110, 1550, 0.98), # Right side: 5 Rainbow varieties popping in ("آلاف الأنواع الحديثة")
    (44.5,   3110, 1550, 0.98),
    
    # --- ROW 4 (Y ≈ 1950) ---
    (44.8,   1100, 1950, 0.98), # Left side: Seedling cycle, crate, sliced juice burst ("غني بالألياف")
    (48.5,   1100, 1950, 0.98),
    (49.8,   3110, 1950, 0.98), # Right side: Farmer inspecting, 4 quality checkboxes ("تساعد على الهضم")
    (51.4,   3110, 1950, 0.98),
    
    # --- ROW 5 (Y ≈ 2380) ---
    (51.6,   1100, 2380, 0.98), # Left side: Gut health, vitamins, heartbeat ("فيتامينات وعناصر")
    (54.0,   1100, 2380, 0.98),
    (55.2,   3110, 2380, 0.98), # Right side: Wheat fiber, harvest pile, refrigerator opening ("في الثلاجة")
    (57.8,   3110, 2380, 0.98),
    
    # --- THE GRAND OUTRO REVEAL (57.8s - 60.88s) ---
    (60.88,  2040, 1400, 0.44), # Majestic pullout revealing the complete 5-row masterpiece whiteboard!
]

def get_camera_state(time_s: float):
    if time_s <= cam_keyframes[0][0]:
        return float(cam_keyframes[0][1]), float(cam_keyframes[0][2]), float(cam_keyframes[0][3])
    if time_s >= cam_keyframes[-1][0]:
        return float(cam_keyframes[-1][1]), float(cam_keyframes[-1][2]), float(cam_keyframes[-1][3])
    for i in range(len(cam_keyframes) - 1):
        t0, x0, y0, z0 = cam_keyframes[i]
        t1, x1, y1, z1 = cam_keyframes[i + 1]
        if t0 <= time_s <= t1:
            ratio = (time_s - t0) / (t1 - t0)
            e = smootherstep(ratio)
            cx = x0 + (x1 - x0) * e
            cy = y0 + (y1 - y0) * e
            cz = z0 + (z1 - z0) * e
            return cx, cy, cz
    return cam_keyframes[-1][1:]

# Helper function to overlay RGBA sprite onto canvas
def overlay_sprite(canvas, sprite_rgba, x, y, w, h, alpha_mult=1.0, scale_x=1.0, scale_y=1.0):
    if alpha_mult <= 0.01:
        return
    sh, sw = sprite_rgba.shape[:2]
    tw = max(2, int(w * scale_x))
    th = max(2, int(h * scale_y))
    if tw != sw or th != sh:
        resized = cv2.resize(sprite_rgba, (tw, th), interpolation=cv2.INTER_LINEAR)
    else:
        resized = sprite_rgba
        
    cx = int(x + w / 2.0)
    cy = int(y + h / 2.0)
    x1 = cx - tw // 2
    y1 = cy - th // 2
    x2 = x1 + tw
    y2 = y1 + th
    
    cw, ch = canvas.shape[1], canvas.shape[0]
    c_x1 = max(0, x1)
    c_y1 = max(0, y1)
    c_x2 = min(cw, x2)
    c_y2 = min(ch, y2)
    if c_x1 >= c_x2 or c_y1 >= c_y2:
        return
        
    s_x1 = c_x1 - x1
    s_y1 = c_y1 - y1
    s_x2 = s_x1 + (c_x2 - c_x1)
    s_y2 = s_y1 + (c_y2 - c_y1)
    
    sub_s = resized[s_y1:s_y2, s_x1:s_x2]
    sub_c = canvas[c_y1:c_y2, c_x1:c_x2]
    
    s_bgr = sub_s[:, :, :3].astype(np.float32)
    s_a = (sub_s[:, :, 3].astype(np.float32) / 255.0) * alpha_mult
    s_a3 = np.repeat(s_a[:, :, np.newaxis], 3, axis=2)
    c_bgr = sub_c.astype(np.float32)
    canvas[c_y1:c_y2, c_x1:c_x2] = np.clip(s_bgr * s_a3 + c_bgr * (1.0 - s_a3), 0, 255).astype(np.uint8)

# Output Paths
out_mp4 = "output_animations/apple_storyboard_masterpiece_2026.mp4"
raw_video_mp4 = "output_animations/raw_apple_video.mp4"
if os.path.exists(raw_video_mp4):
    try: os.remove(raw_video_mp4)
    except: pass

ffmpeg_log = open("experiments/ffmpeg_render_v2.log", "w")
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-s", f"{WIDTH}x{HEIGHT}",
    "-pix_fmt", "bgr24",
    "-r", str(FPS),
    "-i", "-",
    "-c:v", "h264_nvenc",
    "-preset", "p4",
    "-b:v", "9M",
    "-pix_fmt", "yuv420p",
    raw_video_mp4
]

try:
    pipe = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=ffmpeg_log, stderr=ffmpeg_log)
    print("Started FFmpeg NVENC render pipe.")
except Exception as e:
    print(f"NVENC fallback to libx264: {e}")
    ffmpeg_cmd[ffmpeg_cmd.index("h264_nvenc")] = "libx264"
    pipe = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=ffmpeg_log, stderr=ffmpeg_log)

sorted_elements = sorted(elements_staging, key=lambda x: x.get('depth', 1))

print(f"Rendering {TOTAL_FRAMES} frames ({TOTAL_DURATION}s) with 5-Row Storyboard Layout, Comfortable Zoom & Solid Inking...")

for frame_idx in range(TOTAL_FRAMES):
    time_s = frame_idx / float(FPS)
    
    # 1. Clean Whiteboard Canvas
    canvas = np.full((CANVAS_H, CANVAS_W, 3), 255, dtype=np.uint8)
    active_hand_screen_pt = None
    
    # Camera state for this frame
    cam_x, cam_y, cam_zoom = get_camera_state(time_s)
    vp_w = WIDTH / cam_zoom
    vp_h = HEIGHT / cam_zoom
    x1 = cam_x - vp_w / 2.0
    y1 = cam_y - vp_h / 2.0
    x2 = x1 + vp_w
    y2 = y1 + vp_h
    
    src_pts = np.float32([[x1, y1], [x2, y1], [x1, y2]])
    dst_pts = np.float32([[0, 0], [WIDTH, 0], [0, HEIGHT]])
    M = cv2.getAffineTransform(src_pts, dst_pts)
    
    # 2. Render elements onto canvas
    for elem in sorted_elements:
        t_start = elem['t_start']
        t_dur = elem['t_dur']
        if time_s < t_start:
            continue
            
        progress = min(1.0, (time_s - t_start) / max(0.01, t_dur))
        asset = assets[elem['asset']]
        m_type = elem['type']
        px, py = elem.get('pos', (0, 0))
        pw, ph = elem['size']
        
        if m_type == 'outside_in_pen':
            h_data = hero_cache[elem['asset']]
            h_frames = h_data['frames']
            
            if progress >= 1.0:
                # 100% COMPLETE: Render the pristine original asset directly (ZERO missing pixels!)
                overlay_sprite(canvas, asset, px, py, pw, ph)
            else:
                frame_num = min(len(h_frames) - 1, int(progress * len(h_frames)))
                inked_crop, (tip_rx, tip_ry) = h_frames[frame_num]
                overlay_sprite(canvas, inked_crop, px, py, pw, ph)
                
                # Active hand marker tip screen position
                ow, oh = h_data['orig_size']
                canvas_tip_x = px + (tip_rx / ow) * pw
                canvas_tip_y = py + (tip_ry / oh) * ph
                scr_pt = cv2.transform(np.array([[[canvas_tip_x, canvas_tip_y]]], dtype=np.float32), M)[0][0]
                active_hand_screen_pt = (int(round(scr_pt[0])), int(round(scr_pt[1])))
                
        elif m_type == 'jelly_pop':
            sx, sy = get_jelly_scales(progress)
            overlay_sprite(canvas, asset, px, py, pw, ph, alpha_mult=min(1.0, progress * 3.0), scale_x=sx, scale_y=sy)
            
        elif m_type == 'slide_down':
            e = ease_out_back(progress, 1.1)
            y_offset = int((1.0 - e) * 80)
            overlay_sprite(canvas, asset, px, py - y_offset, pw, ph, alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'slide_up':
            e = ease_out_back(progress, 1.1)
            y_offset = int((1.0 - e) * 80)
            overlay_sprite(canvas, asset, px, py + y_offset, pw, ph, alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'travel_slide':
            e = smootherstep(progress)
            x_start, y_start = elem['pos_start']
            x_end, y_end = elem['pos_end']
            cur_x = int(x_start + (x_end - x_start) * e)
            cur_y = int(y_start + (y_end - y_start) * e)
            bob = int(math.sin(progress * 25.0) * 4.0) if progress < 1.0 else 0
            overlay_sprite(canvas, asset, cur_x, cur_y + bob, pw, ph, alpha_mult=min(1.0, progress * 3.0))
            
        elif m_type == 'organic_grow':
            e = ease_out_back(progress, 0.9)
            sx = 0.5 + 0.5 * e
            sy = e
            overlay_sprite(canvas, asset, px, py + int(ph * (1.0 - sy)), pw, ph, scale_x=sx, scale_y=sy, alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'juice_burst':
            sx, sy = get_jelly_scales(progress)
            burst_scale = 1.0 + 0.08 * math.sin(progress * math.pi) if progress < 1.0 else 1.0
            overlay_sprite(canvas, asset, px, py, pw, ph, scale_x=sx * burst_scale, scale_y=sy * burst_scale, alpha_mult=min(1.0, progress * 3.0))
            
        elif m_type == 'pulse_pop':
            pulse = 1.0 + 0.04 * math.sin(time_s * 6.0)
            sx, sy = get_jelly_scales(progress)
            overlay_sprite(canvas, asset, px, py, pw, ph, scale_x=sx * pulse, scale_y=sy * pulse, alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'bubble_float':
            float_y = int(math.sin(time_s * 4.0) * 6.0)
            sx, sy = get_jelly_scales(progress)
            overlay_sprite(canvas, asset, px, py + float_y, pw, ph, scale_x=sx, scale_y=sy, alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'heartbeat_pop':
            beat = math.pow(math.sin(time_s * 5.0), 10.0) * 0.12
            sx, sy = get_jelly_scales(progress)
            overlay_sprite(canvas, asset, px, py, pw, ph, scale_x=(sx + beat), scale_y=(sy + beat), alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'fridge_door_open':
            e = ease_out_back(progress, 1.1)
            overlay_sprite(canvas, asset, px, py, pw, ph, scale_x=e, scale_y=1.0, alpha_mult=min(1.0, progress * 2.5))
            
        else:
            overlay_sprite(canvas, asset, px, py, pw, ph)

    # 3. Apply Camera Transform to get 1920x1080 Viewport Frame
    viewport_frame = cv2.warpAffine(
        canvas, M, (WIDTH, HEIGHT),
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
        flags=cv2.INTER_LINEAR
    )
    
    # 4. Composite Drawing Hand Directly onto 1080p Viewport (Natural Studio Proportions)
    if active_hand_screen_pt is not None and hand_bgra is not None:
        hx, hy = active_hand_screen_pt
        if -100 <= hx <= WIDTH + 100 and -100 <= hy <= HEIGHT + 100:
            viewport_frame = composite_hand_on_canvas_fast(
                viewport_frame, hand_bgra, HAND_TIP_X, HAND_TIP_Y, hx, hy
            )

    # 5. Pipe frame to FFmpeg
    pipe.stdin.write(viewport_frame.tobytes())
    
    if (frame_idx + 1) % 150 == 0 or frame_idx == TOTAL_FRAMES - 1:
        pct = (frame_idx + 1) / float(TOTAL_FRAMES) * 100.0
        print(f"Render progress: {frame_idx + 1}/{TOTAL_FRAMES} frames ({pct:.1f}%) [time: {time_s:.2f}s]")

pipe.stdin.close()
pipe.wait()
ffmpeg_log.close()
print(f"Raw video render completed: {raw_video_mp4}")

# 6. Multiplex with Crisp Stereo 48kHz Ducked Audio via FFmpeg
audio_path = "project_content/audio/apple_master_ducked_audio.wav"
final_mux_cmd = [
    "ffmpeg", "-y",
    "-i", raw_video_mp4,
    "-i", audio_path,
    "-c:v", "copy",
    "-c:a", "aac",
    "-ac", "2",
    "-b:a", "256k",
    "-shortest",
    out_mp4
]

print("Multiplexing video with STEREO 48kHz ducked audio track...")
mux_proc = subprocess.run(final_mux_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if mux_proc.returncode == 0:
    print(f"SUCCESS: Final Masterpiece 2026 saved to: {out_mp4}")
else:
    print(f"Multiplexing error: {mux_proc.stderr.decode('utf-8', errors='ignore')}")
