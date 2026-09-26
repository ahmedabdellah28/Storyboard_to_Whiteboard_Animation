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
print("  🍎 MASTERPIECE WHITEBOARD ENGINE 2026 — SECTION 01: APPLE (MODULAR RE-CREATION) 🍎")
print("=====================================================================================")

WIDTH, HEIGHT = 1920, 1080
FPS = 30
DURATION_SEC = 60.864
TOTAL_FRAMES = int(round(DURATION_SEC * FPS)) # 1826 frames

SCALE = 2.5
PAD_X = 120
PAD_Y = 120

raw_video_mp4 = "sections/01_apple/raw_apple_paragraph_video.mp4"
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
TARGET_HAND_H = 460
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

# Pre-cache Hero Inking for Apple (Strict Hand Discipline)
hero_cache = {}
hero_configs = [
    ("01_giant_red_apple", 0.0,  1.8),  # Giant Apple Hero (takes 1.8s, finishes before wild apple appears!)
    ("08_roman_soldier",   14.2, 2.6),  # Roman Soldier Hero (takes 2.6s, finishes before map & cart appear!)
    ("11_farmer_planting", 19.5, 2.0),  # Farmer Planting Hero (takes 2.0s, finishes before tree stages grow!)
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

# Bounding Box Helper
def S_BOX(rx, ry, rw, rh):
    return (int(round(PAD_X + rx * SCALE)), int(round(PAD_Y + ry * SCALE)), int(round(rw * SCALE)), int(round(rh * SCALE)))

# Complete Staging for 34 Elements across 60.864s
# Grouped into 5 Paragraphs with Disciplined Sequential Inking (Hand finishes BEFORE next element appears!)
elements_staging = [
    # === ROW 1: Origins & Wild Apples (0.0s - 13.5s) ===
    # p1: "التفاح. غالبا هو أشهر فاكهة في العالم، خصوصا في المناطق الباردة" (0.0s - 4.5s)
    {
        'id': '01_giant_apple', 'asset': '01_giant_red_apple',
        't_start': 0.0, 't_dur': 1.8, 'type': 'outside_in_pen', # Hero drawn alone
        'pos': (S_BOX(32, 31, 196, 221)[0], S_BOX(32, 31, 196, 221)[1]),
        'size': (S_BOX(32, 31, 196, 221)[2], S_BOX(32, 31, 196, 221)[3]),
        'depth': 5
    },
    # Wild apple appears ONLY AFTER giant apple hand drawing is finished at 1.8s!
    {
        'id': '02_wild_apple', 'asset': '02_wild_sour_apple',
        't_start': 2.0, 't_dur': 1.0, 'type': 'jelly_pop',
        'pos': (S_BOX(257, 94, 113, 144)[0], S_BOX(257, 94, 113, 144)[1]),
        'size': (S_BOX(257, 94, 113, 144)[2], S_BOX(257, 94, 113, 144)[3]),
        'depth': 5
    },
    {
        'id': '03_branch', 'asset': '03_wild_branch',
        't_start': 3.2, 't_dur': 1.0, 'type': 'slide_down',
        'pos': (S_BOX(386, 38, 245, 228)[0], S_BOX(386, 38, 245, 228)[1]),
        'size': (S_BOX(386, 38, 245, 228)[2], S_BOX(386, 38, 245, 228)[3]),
        'depth': 3
    },
    {
        'id': '04_flower', 'asset': '04_apple_blossom_flower',
        't_start': 4.5, 't_dur': 0.9, 'type': 'jelly_pop',
        'pos': (S_BOX(630, 90, 154, 176)[0], S_BOX(630, 90, 154, 176)[1]),
        'size': (S_BOX(630, 90, 154, 176)[2], S_BOX(630, 90, 154, 176)[3]),
        'depth': 4
    },
    # p2: "لكن الغريب إن التفاح اللي نعرفه اليوم بدأ قصته من الغابات البرية في آسيا الوسطى..." (4.5s - 11.0s)
    {
        'id': '05_tree', 'asset': '05_blooming_apple_tree',
        't_start': 6.5, 't_dur': 1.4, 'type': 'organic_grow',
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
    # p3: "وهناك لسة تنمو نسخته الأصلية إلى اليوم" (11.0s - 14.0s)
    {
        'id': '07_asia_map', 'asset': '07_central_asia_map',
        't_start': 11.2, 't_dur': 1.4, 'type': 'jelly_pop', # "في آسيا الوسطى"
        'pos': (S_BOX(1306, 75, 218, 189)[0], S_BOX(1306, 75, 218, 189)[1]),
        'size': (S_BOX(1306, 75, 218, 189)[2], S_BOX(1306, 75, 218, 189)[3]),
        'depth': 1
    },

    # === ROW 2: Roman Era & Cultivation (14.0s - 24.8s) ===
    # p4: "وانتشار التفاح في العالم يرجع بشكل كبير للإمبراطورية الرومانية" (14.0s - 18.0s)
    {
        'id': '08_soldier', 'asset': '08_roman_soldier',
        't_start': 14.2, 't_dur': 2.6, 'type': 'outside_in_pen', # Roman soldier hero drawn alone
        'pos': (S_BOX(18, 270, 180, 239)[0], S_BOX(18, 270, 180, 239)[1]),
        'size': (S_BOX(18, 270, 180, 239)[2], S_BOX(18, 270, 180, 239)[3]),
        'depth': 5
    },
    # Elements appear ONLY AFTER soldier hand inking finishes at 16.8s!
    {
        'id': '10_europe_map', 'asset': '10_europe_map_arrow',
        't_start': 17.2, 't_dur': 1.0, 'type': 'slide_down',
        'pos': (S_BOX(550, 301, 212, 197)[0], S_BOX(550, 301, 212, 197)[1]),
        'size': (S_BOX(550, 301, 212, 197)[2], S_BOX(550, 301, 212, 197)[3]),
        'depth': 1
    },
    {
        'id': '09_horse_cart', 'asset': '09_horse_cart_apples',
        't_start': 18.2, 't_dur': 2.0, 'type': 'travel_slide',
        'pos_start': (S_BOX(226, 325, 314, 186)[0] - 150, S_BOX(226, 325, 314, 186)[1]),
        'pos_end': (S_BOX(226, 325, 314, 186)[0], S_BOX(226, 325, 314, 186)[1]),
        'size': (S_BOX(226, 325, 314, 186)[2], S_BOX(226, 325, 314, 186)[3]),
        'depth': 6
    },
    # p5: "الجنود الرومان أخذوا الفاكهة معهم لأوروبا، وهناك بدأ المزارعين يزرعونها..." (18.0s - 25.0s)
    {
        'id': '11_farmer', 'asset': '11_farmer_planting',
        't_start': 19.5, 't_dur': 2.0, 'type': 'outside_in_pen', # Farmer hero drawn alone
        'pos': (S_BOX(776, 319, 232, 192)[0], S_BOX(776, 319, 232, 192)[1]),
        'size': (S_BOX(776, 319, 232, 192)[2], S_BOX(776, 319, 232, 192)[3]),
        'depth': 5
    },
    # Tree stages grow ONLY AFTER farmer hand inking finishes at 21.5s!
    {
        'id': '12_stage_1', 'asset': '12_tree_stage_1_seedling',
        't_start': 22.0, 't_dur': 0.7, 'type': 'organic_grow',
        'pos': (S_BOX(1024, 410, 73, 92)[0], S_BOX(1024, 410, 73, 92)[1]),
        'size': (S_BOX(1024, 410, 73, 92)[2], S_BOX(1024, 410, 73, 92)[3]),
        'depth': 4
    },
    {
        'id': '12_stage_2', 'asset': '12_tree_stage_2_sapling',
        't_start': 22.6, 't_dur': 0.7, 'type': 'organic_grow',
        'pos': (S_BOX(1118, 365, 82, 137)[0], S_BOX(1118, 365, 82, 137)[1]),
        'size': (S_BOX(1118, 365, 82, 137)[2], S_BOX(1118, 365, 82, 137)[3]),
        'depth': 4
    },
    {
        'id': '12_stage_3', 'asset': '12_tree_stage_3_growing',
        't_start': 23.2, 't_dur': 0.7, 'type': 'organic_grow',
        'pos': (S_BOX(1218, 320, 109, 179)[0], S_BOX(1218, 320, 109, 179)[1]),
        'size': (S_BOX(1218, 320, 109, 179)[2], S_BOX(1218, 320, 109, 179)[3]),
        'depth': 4
    },
    {
        'id': '12_stage_4', 'asset': '12_tree_stage_4_mature',
        't_start': 23.8, 't_dur': 0.8, 'type': 'organic_grow',
        'pos': (S_BOX(1338, 296, 177, 204)[0], S_BOX(1338, 296, 177, 204)[1]),
        'size': (S_BOX(1338, 296, 177, 204)[2], S_BOX(1338, 296, 177, 204)[3]),
        'depth': 4
    },

    # === ROW 3: Evolution Scale & Diversity (25.0s - 44.0s) ===
    # p6: "والتفاح اللي نشتريه اليوم، الحلو والمليان عصير، يختلف تقريبا 180 درجة..." (25.0s - 33.0s)
    {
        'id': '13_evo_1', 'asset': '13_evo_1_ancient_sour',
        't_start': 25.5, 't_dur': 1.0, 'type': 'jelly_pop', # "النسخ القديمة"
        'pos': (S_BOX(27, 561, 163, 100)[0], S_BOX(27, 561, 163, 100)[1]),
        'size': (S_BOX(27, 561, 163, 100)[2], S_BOX(27, 561, 163, 100)[3]),
        'depth': 4
    },
    {
        'id': '13_evo_2', 'asset': '13_evo_2_selection_growth',
        't_start': 27.2, 't_dur': 1.0, 'type': 'slide_up', # "الحلو والمليان عصير"
        'pos': (S_BOX(198, 560, 258, 99)[0], S_BOX(198, 560, 258, 99)[1]),
        'size': (S_BOX(198, 560, 258, 99)[2], S_BOX(198, 560, 258, 99)[3]),
        'depth': 4
    },
    {
        'id': '13_evo_3', 'asset': '13_evo_3_giant_honeycrisp',
        't_start': 29.0, 't_dur': 1.2, 'type': 'jelly_pop', # "180 درجة"
        'pos': (S_BOX(455, 510, 243, 151)[0], S_BOX(455, 510, 243, 151)[1]),
        'size': (S_BOX(455, 510, 243, 151)[2], S_BOX(455, 510, 243, 151)[3]),
        'depth': 4
    },
    # p7: "وهذا التحول ما صار بسرعة. استمر آلاف السنين، لأن المزارعين كانوا يختارون أفضل الثمار..." (33.0s - 40.0s)
    {
        'id': '14_hand_picking', 'asset': '14_hand_picking_apple',
        't_start': 35.0, 't_dur': 2.0, 'type': 'slide_down', # "يختارون أفضل الثمار"
        'pos': (S_BOX(744, 510, 274, 171)[0], S_BOX(744, 510, 274, 171)[1]),
        'size': (S_BOX(744, 510, 274, 171)[2], S_BOX(744, 510, 274, 171)[3]),
        'depth': 5
    },
    # p8: "لين طلع لنا آلاف الأنواع الحديثة..." (40.0s - 47.0s)
    {
        'id': '15_var_1', 'asset': '15_var_1_red',
        't_start': 40.5, 't_dur': 0.6, 'type': 'jelly_pop',
        'pos': (S_BOX(1053, 545, 93, 117)[0], S_BOX(1053, 545, 93, 117)[1]),
        'size': (S_BOX(1053, 545, 93, 117)[2], S_BOX(1053, 545, 93, 117)[3]),
        'depth': 4
    },
    {
        'id': '15_var_2', 'asset': '15_var_2_green',
        't_start': 41.2, 't_dur': 0.6, 'type': 'jelly_pop',
        'pos': (S_BOX(1145, 550, 91, 112)[0], S_BOX(1145, 550, 91, 112)[1]),
        'size': (S_BOX(1145, 550, 91, 112)[2], S_BOX(1145, 550, 91, 112)[3]),
        'depth': 4
    },
    {
        'id': '15_var_3', 'asset': '15_var_3_yellow',
        't_start': 41.9, 't_dur': 0.6, 'type': 'jelly_pop',
        'pos': (S_BOX(1235, 548, 86, 114)[0], S_BOX(1235, 548, 86, 114)[1]),
        'size': (S_BOX(1235, 548, 86, 114)[2], S_BOX(1235, 548, 86, 114)[3]),
        'depth': 4
    },
    {
        'id': '15_var_4', 'asset': '15_var_4_dark',
        't_start': 42.6, 't_dur': 0.6, 'type': 'jelly_pop',
        'pos': (S_BOX(1320, 549, 86, 113)[0], S_BOX(1320, 549, 86, 113)[1]),
        'size': (S_BOX(1320, 549, 86, 113)[2], S_BOX(1320, 549, 86, 113)[3]),
        'depth': 4
    },
    {
        'id': '15_var_5', 'asset': '15_var_5_striped',
        't_start': 43.3, 't_dur': 0.6, 'type': 'jelly_pop',
        'pos': (S_BOX(1413, 549, 96, 113)[0], S_BOX(1413, 549, 96, 113)[1]),
        'size': (S_BOX(1413, 549, 96, 113)[2], S_BOX(1413, 549, 96, 113)[3]),
        'depth': 4
    },

    # === ROW 4: Harvest Crate, Sliced Apples & Quality (44.0s - 51.5s) ===
    # p9 (start): "ومن ناحية الفوائد، التفاح غني بالألياف..." (47.0s - 54.0s)
    {
        'id': '16_seedling', 'asset': '16_seedling_cycle',
        't_start': 45.0, 't_dur': 1.0, 'type': 'slide_up',
        'pos': (S_BOX(26, 702, 351, 107)[0], S_BOX(26, 702, 351, 107)[1]),
        'size': (S_BOX(26, 702, 351, 107)[2], S_BOX(26, 702, 351, 107)[3]),
        'depth': 3
    },
    {
        'id': '17_crate', 'asset': '17_harvest_crate',
        't_start': 46.2, 't_dur': 1.0, 'type': 'slide_down',
        'pos': (S_BOX(423, 680, 211, 144)[0], S_BOX(423, 680, 211, 144)[1]),
        'size': (S_BOX(423, 680, 211, 144)[2], S_BOX(423, 680, 211, 144)[3]),
        'depth': 4
    },
    {
        'id': '18_sliced_juice', 'asset': '18_sliced_apples_juice',
        't_start': 47.8, 't_dur': 1.2, 'type': 'golden_burst', # Golden apple burst
        'pos': (S_BOX(653, 690, 414, 133)[0], S_BOX(653, 690, 414, 133)[1]),
        'size': (S_BOX(653, 690, 414, 133)[2], S_BOX(653, 690, 414, 133)[3]),
        'depth': 5
    },
    {
        'id': '19_farmer_inspect', 'asset': '19_farmer_inspecting_apple',
        't_start': 49.3, 't_dur': 1.0, 'type': 'jelly_pop',
        'pos': (S_BOX(1108, 678, 179, 145)[0], S_BOX(1108, 678, 179, 145)[1]),
        'size': (S_BOX(1108, 678, 179, 145)[2], S_BOX(1108, 678, 179, 145)[3]),
        'depth': 4
    },
    # 4 Checkmarks
    {
        'id': '20_check_1', 'asset': '20_check_1_green',
        't_start': 50.2, 't_dur': 0.4, 'type': 'jelly_pop',
        'pos': (S_BOX(1301, 701, 55, 90)[0], S_BOX(1301, 701, 55, 90)[1]),
        'size': (S_BOX(1301, 701, 55, 90)[2], S_BOX(1301, 701, 55, 90)[3]),
        'depth': 6
    },
    {
        'id': '20_check_2', 'asset': '20_check_2_green',
        't_start': 50.5, 't_dur': 0.4, 'type': 'jelly_pop',
        'pos': (S_BOX(1355, 701, 56, 90)[0], S_BOX(1355, 701, 56, 90)[1]),
        'size': (S_BOX(1355, 701, 56, 90)[2], S_BOX(1355, 701, 56, 90)[3]),
        'depth': 6
    },
    {
        'id': '20_check_3', 'asset': '20_check_3_green',
        't_start': 50.8, 't_dur': 0.4, 'type': 'jelly_pop',
        'pos': (S_BOX(1410, 701, 56, 90)[0], S_BOX(1410, 701, 56, 90)[1]),
        'size': (S_BOX(1410, 701, 56, 90)[2], S_BOX(1410, 701, 56, 90)[3]),
        'depth': 6
    },
    {
        'id': '20_check_4', 'asset': '20_check_4_red_x',
        't_start': 51.1, 't_dur': 0.4, 'type': 'jelly_pop',
        'pos': (S_BOX(1465, 701, 52, 90)[0], S_BOX(1465, 701, 52, 90)[1]),
        'size': (S_BOX(1465, 701, 52, 90)[2], S_BOX(1465, 701, 52, 90)[3]),
        'depth': 6
    },

    # === ROW 5: Health & Modern Refrigerator (51.5s - 60.864s) ===
    # p10: "باختصار، الفاكهة اللي تشوفها شيء عادي في الثلاجة اليوم، وراها رحلة زراعية عمرها آلاف السنين" (54.0s - 60.0s)
    {
        'id': '21_digestive', 'asset': '21_digestive_health_gut',
        't_start': 52.0, 't_dur': 1.0, 'type': 'pulse_pop', # "تساعد على الهضم"
        'pos': (S_BOX(32, 833, 199, 162)[0], S_BOX(32, 833, 199, 162)[1]),
        'size': (S_BOX(32, 833, 199, 162)[2], S_BOX(32, 833, 199, 162)[3]),
        'depth': 4
    },
    {
        'id': '22_vitamins', 'asset': '22_vitamins_bubbles',
        't_start': 52.8, 't_dur': 1.0, 'type': 'pulse_pop', # "فيتامينات"
        'pos': (S_BOX(261, 850, 211, 143)[0], S_BOX(261, 850, 211, 143)[1]),
        'size': (S_BOX(261, 850, 211, 143)[2], S_BOX(261, 850, 211, 143)[3]),
        'depth': 4
    },
    {
        'id': '23_heart', 'asset': '23_heart_health_pulse',
        't_start': 53.6, 't_dur': 1.0, 'type': 'pulse_pop', # "عناصر غذائية"
        'pos': (S_BOX(501, 873, 190, 109)[0], S_BOX(501, 873, 190, 109)[1]),
        'size': (S_BOX(501, 873, 190, 109)[2], S_BOX(501, 873, 190, 109)[3]),
        'depth': 5
    },
    {
        'id': '24_wheat', 'asset': '24_wheat_fiber_apples',
        't_start': 54.8, 't_dur': 0.8, 'type': 'slide_up', # "باختصار"
        'pos': (S_BOX(713, 849, 215, 146)[0], S_BOX(713, 849, 215, 146)[1]),
        'size': (S_BOX(713, 849, 215, 146)[2], S_BOX(713, 849, 215, 146)[3]),
        'depth': 4
    },
    {
        'id': '25_pile', 'asset': '25_apple_harvest_pile',
        't_start': 55.6, 't_dur': 1.0, 'type': 'slide_up',
        'pos': (S_BOX(966, 844, 275, 152)[0], S_BOX(966, 844, 275, 152)[1]),
        'size': (S_BOX(966, 844, 275, 152)[2], S_BOX(966, 844, 275, 152)[3]),
        'depth': 4
    },
    {
        'id': '26_refrigerator', 'asset': '26_refrigerator_modern_apples',
        't_start': 56.5, 't_dur': 1.2, 'type': 'jelly_pop', # "في الثلاجة اليوم"
        'pos': (S_BOX(1300, 806, 219, 192)[0], S_BOX(1300, 806, 219, 192)[1]),
        'size': (S_BOX(1300, 806, 219, 192)[2], S_BOX(1300, 806, 219, 192)[3]),
        'depth': 6
    }
]

# Sort elements by depth
elements_staging.sort(key=lambda x: x.get('depth', 0))

# 4. Paragraph-Based Stage Camera Architecture (Apple 60.864s)
# Wide stable shot (Zoom = 0.49), center X = 2040.0
# The camera stays COMPLETELY STATIONARY throughout each row!
# Only glides down vertically at paragraph boundaries.
# AT ROW 5: IT FREEZES AND STAYS HELD STEADILY UNTIL 60.864s (ZERO OUTRO ZOOM-OUT!)
def get_camera_state(t):
    # Row 1 (0.0s - 13.5s) -> Stationary at Y = 450
    if t < 13.5:
        return (2040.0, 450.0, 0.49)
    # Transition 1 -> 2 (13.5s - 14.1s, 0.6s smooth glide)
    elif t < 14.1:
        p = smootherstep((t - 13.5) / 0.6)
        cy = 450.0 + (1050.0 - 450.0) * p
        return (2040.0, cy, 0.49)
    # Row 2 (14.1s - 24.8s) -> Stationary at Y = 1050
    elif t < 24.8:
        return (2040.0, 1050.0, 0.49)
    # Transition 2 -> 3 (24.8s - 25.5s, 0.7s smooth glide)
    elif t < 25.5:
        p = smootherstep((t - 24.8) / 0.7)
        cy = 1050.0 + (1550.0 - 1050.0) * p
        return (2040.0, cy, 0.49)
    # Row 3 (25.5s - 44.0s) -> Stationary at Y = 1550
    elif t < 44.0:
        return (2040.0, 1550.0, 0.49)
    # Transition 3 -> 4 (44.0s - 44.7s, 0.7s smooth glide)
    elif t < 44.7:
        p = smootherstep((t - 44.0) / 0.7)
        cy = 1550.0 + (1950.0 - 1550.0) * p
        return (2040.0, cy, 0.49)
    # Row 4 (44.7s - 51.5s) -> Stationary at Y = 1950
    elif t < 51.5:
        return (2040.0, 1950.0, 0.49)
    # Transition 4 -> 5 (51.5s - 52.2s, 0.7s smooth glide)
    elif t < 52.2:
        p = smootherstep((t - 51.5) / 0.7)
        cy = 1950.0 + (2390.0 - 1950.0) * p
        return (2040.0, cy, 0.49)
    # Row 5 (52.2s - 60.864s) -> COMPLETELY FROZEN & STATIONARY ON FINAL SCENE UNTIL END!
    else:
        return (2040.0, 2390.0, 0.49)

# 5. Direct Viewport Blending Function (Pure 1080p, Zero 34MB Canvas)
def blend_sprite_screen(frame, sprite_bgra, scr_x, scr_y, scr_w, scr_h, alpha_mult=1.0):
    if scr_w <= 2 or scr_h <= 2:
        return
    # Frustum Culling
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
    "-cq", "18",
    "-bf", "2",
    "-b_ref_mode", "middle",
    "-pix_fmt", "yuv420p",
    raw_video_mp4
]

ffmpeg_log = open("sections/01_apple/ffmpeg_apple_render.log", "w", encoding="utf-8")
pipe = subprocess.Popen(nvenc_cmd, stdin=subprocess.PIPE, stdout=ffmpeg_log, stderr=ffmpeg_log)

print(f"Started Fast NVENC render pipe for Section 01 Apple.")
print(f"Rendering {TOTAL_FRAMES} frames ({DURATION_SEC:.2f}s) with Steady Paragraph Zones...")

t_render_start = time.time()

# FAST DIRECT VIEWPORT RENDER LOOP
for frame_idx in range(TOTAL_FRAMES):
    time_s = frame_idx / float(FPS)
    
    # Pure clean 1080p studio white frame
    frame = np.full((HEIGHT, WIDTH, 3), 255, dtype=np.uint8)
    
    active_hand_screen_pt = None
    cam_x, cam_y, cam_zoom = get_camera_state(time_s)
    
    # Render all visible elements
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

    # Pipe frame to FFmpeg NVENC
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

print("Multiplexing Apple video with STEREO 48kHz master audio track...")
mux_proc = subprocess.run(final_mux_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if mux_proc.returncode == 0:
    print(f"\n🎉 SUCCESS: Final Apple Masterpiece saved to: {final_video_mp4}")
else:
    print(f"Multiplexing error: {mux_proc.stderr.decode('utf-8', errors='ignore')}")
