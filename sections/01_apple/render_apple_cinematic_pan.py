import os
import sys
import json
import math
import cv2
import numpy as np
import subprocess
import time

# Safe console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

print("=====================================================================================")
print("  🍎 MASTERPIECE WHITEBOARD ENGINE 2026 — SECTION 01: APPLE (CINEMATIC PAN & EXPAND) 🍎")
print("=====================================================================================")

WIDTH, HEIGHT = 1920, 1080
FPS = 30
DURATION_SEC = 60.864
TOTAL_FRAMES = int(round(DURATION_SEC * FPS)) # 1826 frames

CAM_ZOOM = 0.58  # 18% larger zoom than 0.49 -> elements appear ~28% larger on screen!
raw_video_mp4 = "sections/01_apple/raw_apple_cinematic_panned.mp4"
final_video_mp4 = "sections/01_apple/final_whiteboard_1080p.mp4"
master_audio_wav = "sections/01_apple/master_audio.wav"

# 1. Load Hand Sprite
ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
kivy_dir = os.path.join(ROOT_DIR, 'kivy')
if kivy_dir not in sys.path:
    sys.path.insert(0, kivy_dir)

from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast

HAND_PATH = r"E:\image_to_animate\kivy\data\images\drawing-hand.png"
HAND_MASK_PATH = r"E:\image_to_animate\kivy\data\images\hand-mask.png"
raw_hand = load_hand_asset_bgra(HAND_PATH, HAND_MASK_PATH)
if raw_hand is None:
    raise FileNotFoundError(f"Hand sprite not found at {HAND_PATH}")

hh, hw = raw_hand.shape[:2]
TARGET_HAND_H = 480
TARGET_HAND_W = int(hw * (TARGET_HAND_H / hh))
hand_bgra = cv2.resize(raw_hand, (TARGET_HAND_W, TARGET_HAND_H), interpolation=cv2.INTER_AREA)
HAND_TIP_X = int(round(62 * (TARGET_HAND_H / hh)))
HAND_TIP_Y = int(round(40 * (TARGET_HAND_H / hh)))
print(f"Loaded Drawing Hand: {TARGET_HAND_W}x{TARGET_HAND_H}, Pen Tip: ({HAND_TIP_X}, {HAND_TIP_Y})")

# 2. Load Assets
assets_dir = "sections/01_apple/assets"
asset_files = [f for f in os.listdir(assets_dir) if f.endswith(".png")]
assets = {}
for af in asset_files:
    aid = os.path.splitext(af)[0]
    p = os.path.join(assets_dir, af)
    img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if img is not None:
        assets[aid] = img
print(f"Loaded {len(assets)} exact-contour Apple assets.")

# Easing Functions
def ease_out_cubic(t):
    return 1.0 - math.pow(1.0 - t, 3)

def ease_in_out_quad(t):
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - math.pow(-2.0 * t + 2.0, 2) / 2.0

def ease_out_back(t, s=1.70158):
    t -= 1.0
    return (t * t * ((s + 1.0) * t + s) + 1.0)

def smootherstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

# Solid Concentric Outside-In Inking Cache
def build_solid_inking_cache(asset, duration_sec, fps, ring_step=5):
    ah, aw = asset.shape[:2]
    total_frames = max(1, int(round(duration_sec * fps)))
    mask = asset[:, :, 3]
    
    dist_map = cv2.distanceTransform((mask > 20).astype(np.uint8), cv2.DIST_L2, 5)
    max_d = float(dist_map.max()) if dist_map.max() > 0 else 1.0
    
    num_layers = max(3, int(max_d / ring_step))
    ordered_points_by_layer = []
    
    for layer_idx in range(num_layers):
        d_min = layer_idx * ring_step
        d_max = (layer_idx + 1) * ring_step
        ring_mask = ((dist_map >= d_min) & (dist_map < d_max)).astype(np.uint8) * 255
        
        contours, _ = cv2.findContours(ring_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        layer_pts = []
        for c in contours:
            pts = c.reshape(-1, 2)
            step = max(1, len(pts) // 30)
            layer_pts.extend(pts[::step])
            
        if len(layer_pts) > 0:
            ordered_points_by_layer.append(layer_pts)
            
    flat_pts = []
    for l_pts in ordered_points_by_layer:
        flat_pts.extend(l_pts)
        
    n_pts = len(flat_pts)
    frames = []
    
    for f in range(total_frames):
        prog = float(f) / float(total_frames - 1) if total_frames > 1 else 1.0
        cur_idx = min(n_pts - 1, int(prog * n_pts))
        active_layer = int(prog * num_layers)
        
        d_threshold = active_layer * ring_step
        solid_outer = ((dist_map <= d_threshold) & (dist_map > 0)).astype(np.uint8) * 255
        
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

# Pre-cache Hero Inking
hero_cache = {}
hero_configs = [
    ("01_giant_red_apple", 0.0,  1.8),
    ("08_roman_soldier",   14.2, 2.6),
    ("11_farmer_planting", 19.2, 2.0),
]
for h_name, t_start, t_dur in hero_configs:
    if h_name in assets:
        asset = assets[h_name]
        ah, aw = asset.shape[:2]
        cf = build_solid_inking_cache(asset, t_dur, FPS, ring_step=5)
        hero_cache[h_name] = {
            'frames': cf,
            'orig_size': (aw, ah)
        }
        print(f"Pre-cached 100% Solid Inking for {h_name}: {len(cf)} frames ({t_dur}s)")

# Load Decoupled Spaced Layout
with open("sections/01_apple/placed_elements_layout.json", "r", encoding="utf-8") as f:
    layout_data = json.load(f)

placed_elements = layout_data['elements']
row_zones = layout_data['zones']

# Build elements dictionary for quick coordinate lookup
elem_coord = {}
for r_k, r_elems in placed_elements.items():
    for e in r_elems:
        elem_coord[e['name']] = (e['x'], e['y'], e['w'], e['h'])

# 3. Choreographed Elements Staging (Timing strictly synced with narration)
elements_staging = [
    # === ROW 1: Origins & Wild Apples (0.0s - 13.5s) ===
    # p1: "التفاح. غالبا هو أشهر فاكهة في العالم، خصوصا في المناطق الباردة" (0.0s - 4.5s)
    {
        'id': '01_giant_apple', 'asset': '01_giant_red_apple',
        't_start': 0.0, 't_dur': 1.8, 'type': 'outside_in_pen',
        'pos': (elem_coord['01_giant_red_apple'][0], elem_coord['01_giant_red_apple'][1]),
        'size': (elem_coord['01_giant_red_apple'][2], elem_coord['01_giant_red_apple'][3]),
        'depth': 5
    },
    {
        'id': '02_wild_apple', 'asset': '02_wild_sour_apple',
        't_start': 2.0, 't_dur': 1.0, 'type': 'jelly_pop',
        'pos': (elem_coord['02_wild_sour_apple'][0], elem_coord['02_wild_sour_apple'][1]),
        'size': (elem_coord['02_wild_sour_apple'][2], elem_coord['02_wild_sour_apple'][3]),
        'depth': 5
    },
    {
        'id': '03_branch', 'asset': '03_wild_branch',
        't_start': 3.2, 't_dur': 1.0, 'type': 'slide_down',
        'pos': (elem_coord['03_wild_branch'][0], elem_coord['03_wild_branch'][1]),
        'size': (elem_coord['03_wild_branch'][2], elem_coord['03_wild_branch'][3]),
        'depth': 3
    },
    {
        'id': '04_flower', 'asset': '04_apple_blossom_flower',
        't_start': 4.5, 't_dur': 0.9, 'type': 'jelly_pop',
        'pos': (elem_coord['04_apple_blossom_flower'][0], elem_coord['04_apple_blossom_flower'][1]),
        'size': (elem_coord['04_apple_blossom_flower'][2], elem_coord['04_apple_blossom_flower'][3]),
        'depth': 4
    },
    # p2: "لكن الغريب إن التفاح اللي نعرفه اليوم بدأ قصته من الغابات البرية في آسيا الوسطى..." (4.5s - 11.0s)
    # [Camera smoothly pans from Zone 1A to Zone 1B at 4.8s - 5.6s]
    {
        'id': '05_tree', 'asset': '05_blooming_apple_tree',
        't_start': 6.2, 't_dur': 1.4, 'type': 'organic_grow',
        'pos': (elem_coord['05_blooming_apple_tree'][0], elem_coord['05_blooming_apple_tree'][1]),
        'size': (elem_coord['05_blooming_apple_tree'][2], elem_coord['05_blooming_apple_tree'][3]),
        'depth': 2
    },
    {
        'id': '06_mountains', 'asset': '06_snowy_mountains_winter',
        't_start': 9.2, 't_dur': 1.4, 'type': 'slide_down',
        'pos': (elem_coord['06_snowy_mountains_winter'][0], elem_coord['06_snowy_mountains_winter'][1]),
        'size': (elem_coord['06_snowy_mountains_winter'][2], elem_coord['06_snowy_mountains_winter'][3]),
        'depth': 1
    },
    # p3: "وهناك لسة تنمو نسخته الأصلية إلى اليوم" (11.0s - 14.0s)
    {
        'id': '07_asia_map', 'asset': '07_central_asia_map',
        't_start': 11.2, 't_dur': 1.4, 'type': 'jelly_pop',
        'pos': (elem_coord['07_central_asia_map'][0], elem_coord['07_central_asia_map'][1]),
        'size': (elem_coord['07_central_asia_map'][2], elem_coord['07_central_asia_map'][3]),
        'depth': 1
    },

    # === ROW 2: Roman Era & Cultivation (14.0s - 24.8s) ===
    # p4: "وانتشار التفاح في العالم يرجع بشكل كبير للإمبراطورية الرومانية" (14.0s - 18.0s)
    {
        'id': '08_soldier', 'asset': '08_roman_soldier',
        't_start': 14.2, 't_dur': 2.6, 'type': 'outside_in_pen',
        'pos': (elem_coord['08_roman_soldier'][0], elem_coord['08_roman_soldier'][1]),
        'size': (elem_coord['08_roman_soldier'][2], elem_coord['08_roman_soldier'][3]),
        'depth': 5
    },
    {
        'id': '10_europe_map', 'asset': '10_europe_map_arrow',
        't_start': 17.0, 't_dur': 1.0, 'type': 'slide_down',
        'pos': (elem_coord['10_europe_map_arrow'][0], elem_coord['10_europe_map_arrow'][1]),
        'size': (elem_coord['10_europe_map_arrow'][2], elem_coord['10_europe_map_arrow'][3]),
        'depth': 1
    },
    {
        'id': '09_horse_cart', 'asset': '09_horse_cart_apples',
        't_start': 17.8, 't_dur': 1.2, 'type': 'travel_slide',
        'pos_start': (elem_coord['09_horse_cart_apples'][0] - 150, elem_coord['09_horse_cart_apples'][1]),
        'pos_end': (elem_coord['09_horse_cart_apples'][0], elem_coord['09_horse_cart_apples'][1]),
        'pos': (elem_coord['09_horse_cart_apples'][0], elem_coord['09_horse_cart_apples'][1]),
        'size': (elem_coord['09_horse_cart_apples'][2], elem_coord['09_horse_cart_apples'][3]),
        'depth': 3
    },
    # p5: "الجنود الرومان أخذوا الفاكهة معهم لأوروبا، وهناك بدأ المزارعين..." (18.0s - 25.0s)
    # [Camera smoothly pans from Zone 2A to Zone 2B at 18.5s - 19.3s]
    {
        'id': '11_farmer', 'asset': '11_farmer_planting',
        't_start': 19.5, 't_dur': 2.0, 'type': 'outside_in_pen',
        'pos': (elem_coord['11_farmer_planting'][0], elem_coord['11_farmer_planting'][1]),
        'size': (elem_coord['11_farmer_planting'][2], elem_coord['11_farmer_planting'][3]),
        'depth': 5
    },
    {
        'id': '12_tree_s1', 'asset': '12_tree_stage_1_seedling',
        't_start': 21.8, 't_dur': 0.6, 'type': 'organic_grow',
        'pos': (elem_coord['12_tree_stage_1_seedling'][0], elem_coord['12_tree_stage_1_seedling'][1]),
        'size': (elem_coord['12_tree_stage_1_seedling'][2], elem_coord['12_tree_stage_1_seedling'][3]),
        'depth': 4
    },
    {
        'id': '12_tree_s2', 'asset': '12_tree_stage_2_sapling',
        't_start': 22.4, 't_dur': 0.6, 'type': 'organic_grow',
        'pos': (elem_coord['12_tree_stage_2_sapling'][0], elem_coord['12_tree_stage_2_sapling'][1]),
        'size': (elem_coord['12_tree_stage_2_sapling'][2], elem_coord['12_tree_stage_2_sapling'][3]),
        'depth': 4
    },
    {
        'id': '12_tree_s3', 'asset': '12_tree_stage_3_growing',
        't_start': 23.0, 't_dur': 0.7, 'type': 'organic_grow',
        'pos': (elem_coord['12_tree_stage_3_growing'][0], elem_coord['12_tree_stage_3_growing'][1]),
        'size': (elem_coord['12_tree_stage_3_growing'][2], elem_coord['12_tree_stage_3_growing'][3]),
        'depth': 4
    },
    {
        'id': '12_tree_s4', 'asset': '12_tree_stage_4_mature',
        't_start': 23.7, 't_dur': 0.9, 'type': 'organic_grow',
        'pos': (elem_coord['12_tree_stage_4_mature'][0], elem_coord['12_tree_stage_4_mature'][1]),
        'size': (elem_coord['12_tree_stage_4_mature'][2], elem_coord['12_tree_stage_4_mature'][3]),
        'depth': 4
    },

    # === ROW 3: Size Evolution & Rainbow Varieties (25.0s - 44.0s) ===
    # p6: "والتفاح اللي نشتريه اليوم، الحلو والمليان عصير..." (25.0s - 33.0s)
    {
        'id': '13_evo_1', 'asset': '13_evo_1_ancient_sour',
        't_start': 25.5, 't_dur': 0.9, 'type': 'jelly_pop',
        'pos': (elem_coord['13_evo_1_ancient_sour'][0], elem_coord['13_evo_1_ancient_sour'][1]),
        'size': (elem_coord['13_evo_1_ancient_sour'][2], elem_coord['13_evo_1_ancient_sour'][3]),
        'depth': 3
    },
    {
        'id': '13_evo_2', 'asset': '13_evo_2_selection_growth',
        't_start': 27.2, 't_dur': 1.0, 'type': 'jelly_pop',
        'pos': (elem_coord['13_evo_2_selection_growth'][0], elem_coord['13_evo_2_selection_growth'][1]),
        'size': (elem_coord['13_evo_2_selection_growth'][2], elem_coord['13_evo_2_selection_growth'][3]),
        'depth': 3
    },
    {
        'id': '13_evo_3', 'asset': '13_evo_3_giant_honeycrisp',
        't_start': 29.5, 't_dur': 1.2, 'type': 'pulse_pop',
        'pos': (elem_coord['13_evo_3_giant_honeycrisp'][0], elem_coord['13_evo_3_giant_honeycrisp'][1]),
        'size': (elem_coord['13_evo_3_giant_honeycrisp'][2], elem_coord['13_evo_3_giant_honeycrisp'][3]),
        'depth': 4
    },
    # p7: "وهذا التحول ما صار بسرعة. استمر آلاف السنين..." (33.0s - 40.0s)
    {
        'id': '14_hand_pick', 'asset': '14_hand_picking_apple',
        't_start': 33.5, 't_dur': 1.4, 'type': 'slide_down',
        'pos': (elem_coord['14_hand_picking_apple'][0], elem_coord['14_hand_picking_apple'][1]),
        'size': (elem_coord['14_hand_picking_apple'][2], elem_coord['14_hand_picking_apple'][3]),
        'depth': 5
    },
    # p8: "لين طلع لنا آلاف الأنواع الحديثة..." (40.0s - 47.0s)
    # [Camera smoothly pans from Zone 3A to Zone 3B at 39.5s - 40.3s]
    {
        'id': '15_var_1', 'asset': '15_var_1_red',
        't_start': 40.5, 't_dur': 0.7, 'type': 'jelly_pop',
        'pos': (elem_coord['15_var_1_red'][0], elem_coord['15_var_1_red'][1]),
        'size': (elem_coord['15_var_1_red'][2], elem_coord['15_var_1_red'][3]),
        'depth': 4
    },
    {
        'id': '15_var_2', 'asset': '15_var_2_green',
        't_start': 41.3, 't_dur': 0.7, 'type': 'jelly_pop',
        'pos': (elem_coord['15_var_2_green'][0], elem_coord['15_var_2_green'][1]),
        'size': (elem_coord['15_var_2_green'][2], elem_coord['15_var_2_green'][3]),
        'depth': 4
    },
    {
        'id': '15_var_3', 'asset': '15_var_3_yellow',
        't_start': 42.1, 't_dur': 0.7, 'type': 'jelly_pop',
        'pos': (elem_coord['15_var_3_yellow'][0], elem_coord['15_var_3_yellow'][1]),
        'size': (elem_coord['15_var_3_yellow'][2], elem_coord['15_var_3_yellow'][3]),
        'depth': 4
    },
    {
        'id': '15_var_4', 'asset': '15_var_4_dark',
        't_start': 42.9, 't_dur': 0.7, 'type': 'jelly_pop',
        'pos': (elem_coord['15_var_4_dark'][0], elem_coord['15_var_4_dark'][1]),
        'size': (elem_coord['15_var_4_dark'][2], elem_coord['15_var_4_dark'][3]),
        'depth': 4
    },
    {
        'id': '15_var_5', 'asset': '15_var_5_striped',
        't_start': 43.7, 't_dur': 0.7, 'type': 'jelly_pop',
        'pos': (elem_coord['15_var_5_striped'][0], elem_coord['15_var_5_striped'][1]),
        'size': (elem_coord['15_var_5_striped'][2], elem_coord['15_var_5_striped'][3]),
        'depth': 4
    },

    # === ROW 4: Harvest Crate, Sliced Apples & Quality (44.5s - 51.5s) ===
    # p9 (start): "ومن ناحية الفوائد، التفاح غني بالألياف..." (47.0s - 54.0s)
    {
        'id': '16_seedling', 'asset': '16_seedling_cycle',
        't_start': 45.0, 't_dur': 1.0, 'type': 'slide_up',
        'pos': (elem_coord['16_seedling_cycle'][0], elem_coord['16_seedling_cycle'][1]),
        'size': (elem_coord['16_seedling_cycle'][2], elem_coord['16_seedling_cycle'][3]),
        'depth': 3
    },
    {
        'id': '17_crate', 'asset': '17_harvest_crate',
        't_start': 46.2, 't_dur': 1.0, 'type': 'slide_down',
        'pos': (elem_coord['17_harvest_crate'][0], elem_coord['17_harvest_crate'][1]),
        'size': (elem_coord['17_harvest_crate'][2], elem_coord['17_harvest_crate'][3]),
        'depth': 4
    },
    {
        'id': '18_sliced_juice', 'asset': '18_sliced_apples_juice',
        't_start': 47.6, 't_dur': 1.2, 'type': 'golden_burst',
        'pos': (elem_coord['18_sliced_apples_juice'][0], elem_coord['18_sliced_apples_juice'][1]),
        'size': (elem_coord['18_sliced_apples_juice'][2], elem_coord['18_sliced_apples_juice'][3]),
        'depth': 5
    },
    # [Camera smoothly pans from Zone 4A to Zone 4B at 48.8s - 49.6s]
    {
        'id': '19_farmer_inspect', 'asset': '19_farmer_inspecting_apple',
        't_start': 49.8, 't_dur': 1.0, 'type': 'jelly_pop',
        'pos': (elem_coord['19_farmer_inspecting_apple'][0], elem_coord['19_farmer_inspecting_apple'][1]),
        'size': (elem_coord['19_farmer_inspecting_apple'][2], elem_coord['19_farmer_inspecting_apple'][3]),
        'depth': 4
    },
    {
        'id': '20_check_1', 'asset': '20_check_1_green',
        't_start': 50.4, 't_dur': 0.35, 'type': 'jelly_pop',
        'pos': (elem_coord['20_check_1_green'][0], elem_coord['20_check_1_green'][1]),
        'size': (elem_coord['20_check_1_green'][2], elem_coord['20_check_1_green'][3]),
        'depth': 6
    },
    {
        'id': '20_check_2', 'asset': '20_check_2_green',
        't_start': 50.7, 't_dur': 0.35, 'type': 'jelly_pop',
        'pos': (elem_coord['20_check_2_green'][0], elem_coord['20_check_2_green'][1]),
        'size': (elem_coord['20_check_2_green'][2], elem_coord['20_check_2_green'][3]),
        'depth': 6
    },
    {
        'id': '20_check_3', 'asset': '20_check_3_green',
        't_start': 51.0, 't_dur': 0.35, 'type': 'jelly_pop',
        'pos': (elem_coord['20_check_3_green'][0], elem_coord['20_check_3_green'][1]),
        'size': (elem_coord['20_check_3_green'][2], elem_coord['20_check_3_green'][3]),
        'depth': 6
    },
    {
        'id': '20_check_4', 'asset': '20_check_4_red_x',
        't_start': 51.3, 't_dur': 0.35, 'type': 'jelly_pop',
        'pos': (elem_coord['20_check_4_red_x'][0], elem_coord['20_check_4_red_x'][1]),
        'size': (elem_coord['20_check_4_red_x'][2], elem_coord['20_check_4_red_x'][3]),
        'depth': 6
    },

    # === ROW 5: Health & Modern Refrigerator (52.0s - 60.864s) ===
    # p10: "باختصار، الفاكهة اللي تشوفها شيء عادي في الثلاجة اليوم، وراها رحلة زراعية عمرها آلاف السنين" (54.0s - 60.0s)
    {
        'id': '21_digestive', 'asset': '21_digestive_health_gut',
        't_start': 52.4, 't_dur': 1.0, 'type': 'pulse_pop',
        'pos': (elem_coord['21_digestive_health_gut'][0], elem_coord['21_digestive_health_gut'][1]),
        'size': (elem_coord['21_digestive_health_gut'][2], elem_coord['21_digestive_health_gut'][3]),
        'depth': 4
    },
    {
        'id': '22_vitamins', 'asset': '22_vitamins_bubbles',
        't_start': 53.2, 't_dur': 1.0, 'type': 'pulse_pop',
        'pos': (elem_coord['22_vitamins_bubbles'][0], elem_coord['22_vitamins_bubbles'][1]),
        'size': (elem_coord['22_vitamins_bubbles'][2], elem_coord['22_vitamins_bubbles'][3]),
        'depth': 4
    },
    {
        'id': '23_heart', 'asset': '23_heart_health_pulse',
        't_start': 54.0, 't_dur': 1.0, 'type': 'pulse_pop',
        'pos': (elem_coord['23_heart_health_pulse'][0], elem_coord['23_heart_health_pulse'][1]),
        'size': (elem_coord['23_heart_health_pulse'][2], elem_coord['23_heart_health_pulse'][3]),
        'depth': 5
    },
    # [Camera smoothly pans from Zone 5A to Zone 5B at 54.8s - 55.6s]
    {
        'id': '24_wheat', 'asset': '24_wheat_fiber_apples',
        't_start': 55.8, 't_dur': 0.8, 'type': 'slide_up',
        'pos': (elem_coord['24_wheat_fiber_apples'][0], elem_coord['24_wheat_fiber_apples'][1]),
        'size': (elem_coord['24_wheat_fiber_apples'][2], elem_coord['24_wheat_fiber_apples'][3]),
        'depth': 4
    },
    {
        'id': '25_pile', 'asset': '25_apple_harvest_pile',
        't_start': 56.5, 't_dur': 1.0, 'type': 'slide_up',
        'pos': (elem_coord['25_apple_harvest_pile'][0], elem_coord['25_apple_harvest_pile'][1]),
        'size': (elem_coord['25_apple_harvest_pile'][2], elem_coord['25_apple_harvest_pile'][3]),
        'depth': 4
    },
    {
        'id': '26_refrigerator', 'asset': '26_refrigerator_modern_apples',
        't_start': 57.4, 't_dur': 1.2, 'type': 'jelly_pop',
        'pos': (elem_coord['26_refrigerator_modern_apples'][0], elem_coord['26_refrigerator_modern_apples'][1]),
        'size': (elem_coord['26_refrigerator_modern_apples'][2], elem_coord['26_refrigerator_modern_apples'][3]),
        'depth': 6
    }
]

elements_staging.sort(key=lambda x: x.get('depth', 0))

# 4. Cinematic Two-Stage Camera Choreography
# Camera tracks smoothly across Zone A and Zone B of each row,
# and glides vertically between the decoupled rows (2000px gap).
def get_camera_state(t):
    # --- ROW 1 (Y = 800) ---
    if t < 4.8:
        # Zone 1A: Giant apple, wild apple, branch, flower
        return (row_zones['1']['zone_A'][0], 800.0, CAM_ZOOM)
    elif t < 5.6:
        # Smooth horizontal pan 1A -> 1B (0.8s)
        p = smootherstep((t - 4.8) / 0.8)
        cx = row_zones['1']['zone_A'][0] + (row_zones['1']['zone_B'][0] - row_zones['1']['zone_A'][0]) * p
        return (cx, 800.0, CAM_ZOOM)
    elif t < 13.5:
        # Zone 1B: Tree, Caucasus snowy mountains, Asia map
        return (row_zones['1']['zone_B'][0], 800.0, CAM_ZOOM)
    
    # Transition Row 1 -> Row 2 (13.5s - 14.3s, 0.8s smooth glide)
    elif t < 14.3:
        p = smootherstep((t - 13.5) / 0.8)
        cx = row_zones['1']['zone_B'][0] + (row_zones['2']['zone_A'][0] - row_zones['1']['zone_B'][0]) * p
        cy = 800.0 + (2800.0 - 800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 2 (Y = 2800) ---
    elif t < 18.5:
        # Zone 2A: Roman soldier hero, Europe map, cart
        return (row_zones['2']['zone_A'][0], 2800.0, CAM_ZOOM)
    elif t < 19.3:
        # Smooth horizontal pan 2A -> 2B (0.8s)
        p = smootherstep((t - 18.5) / 0.8)
        cx = row_zones['2']['zone_A'][0] + (row_zones['2']['zone_B'][0] - row_zones['2']['zone_A'][0]) * p
        return (cx, 2800.0, CAM_ZOOM)
    elif t < 24.8:
        # Zone 2B: Farmer planting hero, 4 growing tree stages
        return (row_zones['2']['zone_B'][0], 2800.0, CAM_ZOOM)

    # Transition Row 2 -> Row 3 (24.8s - 25.6s, 0.8s smooth glide)
    elif t < 25.6:
        p = smootherstep((t - 24.8) / 0.8)
        cx = row_zones['2']['zone_B'][0] + (row_zones['3']['zone_A'][0] - row_zones['2']['zone_B'][0]) * p
        cy = 2800.0 + (4800.0 - 2800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 3 (Y = 4800) ---
    elif t < 39.5:
        # Zone 3A: Evolution scale & hand picking
        return (row_zones['3']['zone_A'][0], 4800.0, CAM_ZOOM)
    elif t < 40.3:
        # Smooth horizontal pan 3A -> 3B (0.8s)
        p = smootherstep((t - 39.5) / 0.8)
        cx = row_zones['3']['zone_A'][0] + (row_zones['3']['zone_B'][0] - row_zones['3']['zone_A'][0]) * p
        return (cx, 4800.0, CAM_ZOOM)
    elif t < 44.5:
        # Zone 3B: 5 Apple varieties
        return (row_zones['3']['zone_B'][0], 4800.0, CAM_ZOOM)

    # Transition Row 3 -> Row 4 (44.5s - 45.3s, 0.8s smooth glide)
    elif t < 45.3:
        p = smootherstep((t - 44.5) / 0.8)
        cx = row_zones['3']['zone_B'][0] + (row_zones['4']['zone_A'][0] - row_zones['3']['zone_B'][0]) * p
        cy = 4800.0 + (6800.0 - 4800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 4 (Y = 6800) ---
    elif t < 48.8:
        # Zone 4A: Seedling cycle, crate, sliced juice
        return (row_zones['4']['zone_A'][0], 6800.0, CAM_ZOOM)
    elif t < 49.6:
        # Smooth horizontal pan 4A -> 4B (0.8s)
        p = smootherstep((t - 48.8) / 0.8)
        cx = row_zones['4']['zone_A'][0] + (row_zones['4']['zone_B'][0] - row_zones['4']['zone_A'][0]) * p
        return (cx, 6800.0, CAM_ZOOM)
    elif t < 51.5:
        # Zone 4B: Farmer inspect, 4 checkmarks
        return (row_zones['4']['zone_B'][0], 6800.0, CAM_ZOOM)

    # Transition Row 4 -> Row 5 (51.5s - 52.3s, 0.8s smooth glide)
    elif t < 52.3:
        p = smootherstep((t - 51.5) / 0.8)
        cx = row_zones['4']['zone_B'][0] + (row_zones['5']['zone_A'][0] - row_zones['4']['zone_B'][0]) * p
        cy = 6800.0 + (8800.0 - 6800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 5 (Y = 8800) ---
    elif t < 54.8:
        # Zone 5A: Gut, vitamins, heart pulse
        return (row_zones['5']['zone_A'][0], 8800.0, CAM_ZOOM)
    elif t < 55.6:
        # Smooth horizontal pan 5A -> 5B (0.8s)
        p = smootherstep((t - 54.8) / 0.8)
        cx = row_zones['5']['zone_A'][0] + (row_zones['5']['zone_B'][0] - row_zones['5']['zone_A'][0]) * p
        return (cx, 8800.0, CAM_ZOOM)
    else:
        # Zone 5B: Modern refrigerator, wheat, harvest pile
        # COMPLETELY FROZEN & STATIONARY UNTIL END (ZERO OUTRO ZOOM-OUT!)
        return (row_zones['5']['zone_B'][0], 8800.0, CAM_ZOOM)

# 5. Direct Viewport Blending Function
def blend_sprite_screen(frame, sprite_bgra, scr_x, scr_y, scr_w, scr_h, alpha_mult=1.0):
    if scr_w <= 2 or scr_h <= 2:
        return
    if scr_x + scr_w <= 0 or scr_x >= WIDTH or scr_y + scr_h <= 0 or scr_y >= HEIGHT:
        return
        
    interp = cv2.INTER_AREA if scr_w < sprite_bgra.shape[1] else cv2.INTER_LINEAR
    resized = cv2.resize(sprite_bgra, (scr_w, scr_h), interpolation=interp)
    
    x1 = max(0, scr_x)
    y1 = max(0, scr_y)
    x2 = min(WIDTH, scr_x + scr_w)
    y2 = min(HEIGHT, scr_y + scr_h)
    
    if x2 <= x1 or y2 <= y1:
        return
        
    sx1 = x1 - scr_x
    sy1 = y1 - scr_y
    sx2 = sx1 + (x2 - x1)
    sy2 = sy1 + (y2 - y1)
    
    src_crop = resized[sy1:sy2, sx1:sx2]
    alpha = (src_crop[:, :, 3].astype(np.float32) / 255.0) * alpha_mult
    alpha_3 = cv2.merge([alpha, alpha, alpha])
    
    dst_roi = frame[y1:y2, x1:x2].astype(np.float32)
    src_bgr = src_crop[:, :, :3].astype(np.float32)
    
    frame[y1:y2, x1:x2] = (src_bgr * alpha_3 + dst_roi * (1.0 - alpha_3)).astype(np.uint8)

# 6. FFmpeg NVENC Video Render Pipe
nvenc_cmd = [
    "ffmpeg", "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-s", f"{WIDTH}x{HEIGHT}",
    "-pix_fmt", "bgr24",
    "-r", str(FPS),
    "-i", "-",
    "-c:v", "h264_nvenc",
    "-preset", "p7",
    "-tune", "hq",
    "-rc", "vbr",
    "-cq", "19",
    "-b:v", "14M",
    "-maxrate", "24M",
    "-pix_fmt", "yuv420p",
    raw_video_mp4
]

print(f"\nLaunching FFmpeg NVENC hardware pipeline for {TOTAL_FRAMES} frames ({DURATION_SEC}s)...")
ffmpeg_log = open("sections/01_apple/ffmpeg_apple_render.log", "w")
pipe = subprocess.Popen(nvenc_cmd, stdin=subprocess.PIPE, stderr=ffmpeg_log)

t_render_start = time.time()

# FAST DIRECT VIEWPORT RENDER LOOP
for frame_idx in range(TOTAL_FRAMES):
    time_s = frame_idx / float(FPS)
    
    frame = np.full((HEIGHT, WIDTH, 3), 255, dtype=np.uint8)
    
    active_hand_screen_pt = None
    cam_x, cam_y, cam_zoom = get_camera_state(time_s)
    
    for elem in elements_staging:
        t_start = elem['t_start']
        if time_s < t_start:
            continue
            
        eid = elem['id']
        t_dur = elem['t_dur']
        elapsed = time_s - t_start
        prog = min(1.0, elapsed / t_dur)
        anim_type = elem['type']
        
        orig_x, orig_y = elem['pos'] if 'pos' in elem else elem['pos_end']
        w, h = elem['size']
        
        cur_w = w
        cur_h = h
        cur_x = orig_x
        cur_y = orig_y
        alpha_mult = 1.0
        active_sprite = assets[elem['asset']]
        
        if anim_type == 'outside_in_pen':
            if elem['asset'] in hero_cache and prog < 1.0:
                c_info = hero_cache[elem['asset']]
                f_idx = min(len(c_info['frames']) - 1, int(prog * len(c_info['frames'])))
                active_sprite, (tip_ax, tip_ay) = c_info['frames'][f_idx]
                
                ow, oh = c_info['orig_size']
                tip_wx = orig_x + (tip_ax / float(ow)) * w
                tip_wy = orig_y + (tip_ay / float(oh)) * h
                
                active_hand_screen_pt = (
                    int(round(WIDTH / 2.0 + (tip_wx - cam_x) * cam_zoom)),
                    int(round(HEIGHT / 2.0 + (tip_wy - cam_y) * cam_zoom))
                )
        elif anim_type == 'jelly_pop':
            if prog < 1.0:
                e_prog = ease_out_back(prog, s=1.8)
                scale = max(0.01, e_prog)
                cur_w = int(w * scale)
                cur_h = int(h * scale)
                cur_x = int(orig_x + (w - cur_w) / 2.0)
                cur_y = int(orig_y + (h - cur_h) / 2.0)
                alpha_mult = min(1.0, prog / 0.3)
        elif anim_type == 'organic_grow':
            if prog < 1.0:
                e_prog = ease_out_cubic(prog)
                scale_x = max(0.01, 0.4 + 0.6 * e_prog)
                scale_y = max(0.01, e_prog)
                cur_w = int(w * scale_x)
                cur_h = int(h * scale_y)
                cur_x = int(orig_x + (w - cur_w) / 2.0)
                cur_y = int(orig_y + (h - cur_h))
                alpha_mult = min(1.0, prog / 0.3)
        elif anim_type == 'slide_down':
            if prog < 1.0:
                e_prog = ease_out_cubic(prog)
                cur_y = (orig_y - 80) + 80 * e_prog
                alpha_mult = min(1.0, prog / 0.35)
        elif anim_type == 'slide_up':
            if prog < 1.0:
                e_prog = ease_out_cubic(prog)
                cur_y = (orig_y + 80) - 80 * e_prog
                alpha_mult = min(1.0, prog / 0.35)
        elif anim_type == 'travel_slide':
            if prog < 1.0:
                e_prog = ease_in_out_quad(prog)
                cur_x = elem['pos_start'][0] + (elem['pos_end'][0] - elem['pos_start'][0]) * e_prog
                alpha_mult = min(1.0, prog / 0.25)
        elif anim_type == 'golden_burst' or anim_type == 'pulse_pop':
            if prog < 1.0:
                pulse = 1.0 + 0.12 * math.sin(prog * math.pi * 3) * (1.0 - prog)
                cur_w = int(w * pulse)
                cur_h = int(h * pulse)
                cur_x = int(orig_x + (w - cur_w) / 2.0)
                cur_y = int(orig_y + (h - cur_h) / 2.0)
                alpha_mult = min(1.0, prog / 0.25)

        # Direct projection from World Canvas space to Screen space
        scr_x = int(round(WIDTH / 2.0 + (cur_x - cam_x) * cam_zoom))
        scr_y = int(round(HEIGHT / 2.0 + (cur_y - cam_y) * cam_zoom))
        scr_w = int(round(cur_w * cam_zoom))
        scr_h = int(round(cur_h * cam_zoom))
        
        blend_sprite_screen(frame, active_sprite, scr_x, scr_y, scr_w, scr_h, alpha_mult=alpha_mult)
        
    # Composite Drawing Hand on screen
    if active_hand_screen_pt is not None and hand_bgra is not None:
        hx, hy = active_hand_screen_pt
        if -100 <= hx <= WIDTH + 100 and -100 <= hy <= HEIGHT + 100:
            frame = composite_hand_on_canvas_fast(
                frame, hand_bgra, HAND_TIP_X, HAND_TIP_Y, hx, hy
            )

    pipe.stdin.write(frame.tobytes())
    
    if (frame_idx + 1) % 300 == 0 or frame_idx == TOTAL_FRAMES - 1:
        elapsed_time = time.time() - t_render_start
        fps_speed = (frame_idx + 1) / max(0.001, elapsed_time)
        pct = (frame_idx + 1) / float(TOTAL_FRAMES) * 100.0
        print(f"Render progress: {frame_idx + 1}/{TOTAL_FRAMES} frames ({pct:.1f}%) [Speed: {fps_speed:.1f} FPS, Time: {time_s:.2f}s]")

pipe.stdin.close()
pipe.wait()
ffmpeg_log.close()

total_render_sec = time.time() - t_render_start
print(f"Raw video render completed in {total_render_sec:.2f}s (Average Speed: {TOTAL_FRAMES / total_render_sec:.1f} FPS): {raw_video_mp4}")

# 7. Multiplex with Master Stereo Ducked Audio
final_mux_cmd = [
    "ffmpeg", "-y",
    "-i", raw_video_mp4,
    "-i", master_audio_wav,
    "-c:v", "copy",
    "-c:a", "aac",
    "-ac", "2",
    "-b:a", "256k",
    "-shortest",
    final_video_mp4
]

print(f"\nMultiplexing master video with audio -> {final_video_mp4}...")
mux_res = subprocess.run(final_mux_cmd, capture_output=True, text=True)
if mux_res.returncode != 0:
    print(f"Multiplex Error: {mux_res.stderr}")
else:
    print(f"--- SUCCESS: Apple Cinematic Whiteboard Video created ({os.path.getsize(final_video_mp4) / (1024*1024):.2f} MB) ---")
