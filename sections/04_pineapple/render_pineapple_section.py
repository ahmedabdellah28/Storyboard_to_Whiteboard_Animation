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
print("  🍍 MASTERPIECE WHITEBOARD ENGINE 2026 — SECTION 04: PINEAPPLE (EXACT SYNC) 🍍")
print("=====================================================================================")

WIDTH, HEIGHT = 1920, 1080
FPS = 30
DURATION_SEC = 57.00
TOTAL_FRAMES = int(round(DURATION_SEC * FPS))  # 1710 frames

CAM_ZOOM = 0.58
raw_video_mp4 = "sections/04_pineapple/raw_pineapple_cinematic_panned.mp4"
final_video_mp4 = "sections/04_pineapple/final_whiteboard_1080p.mp4"
master_audio_wav = "sections/04_pineapple/master_audio.wav"

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

# 2. Load Extracted Assets
assets_dir = "sections/04_pineapple/assets"
asset_files = [f for f in os.listdir(assets_dir) if f.endswith(".png")]
assets = {}
for af in asset_files:
    aid = os.path.splitext(af)[0]
    p = os.path.join(assets_dir, af)
    img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if img is not None:
        assets[aid] = img
print(f"Loaded {len(assets)} clean Pineapple assets.")

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

# Pre-cache Hero Inking for Pineapple (matched to speech phrases)
hero_cache = {}
hero_configs = [
    ("r1_01_hero_pineapple",                0.0,  1.0),
    ("r1_06_wealthy_gentleman_england_gold", 8.0,  2.6),
    ("r2_02_admiring_guests",               20.8, 2.0),
    ("r3_01_cross_section_cells",           37.6, 1.8),
    ("r4_01_pineapple_slice_dripping",      51.0, 1.0),
    ("r4_04_carnivorous_monster_pineapple", 52.8, 1.8),
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
        print(f"Pre-cached Inking for {h_name}: {len(cf)} frames ({t_dur}s)")

# Load Decoupled Spaced Layout
with open("sections/04_pineapple/placed_elements_layout.json", "r", encoding="utf-8") as f:
    layout_data = json.load(f)

placed_elements = layout_data['elements']
row_zones = layout_data['zones']

elem_coord = {}
for r_k, r_elems in placed_elements.items():
    for e in r_elems:
        elem_coord[e['aid']] = (e['x'], e['y'], e['w'], e['h'])

# 3. Elements Staging (100% Synced with speech phrases and 57.0s duration)
elements_staging = [
    # === ROW 1: Phrase 1 (0.0-1.1s), Phrase 2/3 (1.2-7.6s), Phrase 4-6 (8.0-19.0s) ===
    # Phrase 1: "الأناناس."
    {
        'id': 'r1_01', 'asset': 'r1_01_hero_pineapple',
        't_start': 0.0, 't_dur': 1.0, 'type': 'outside_in_pen',
        'pos': (elem_coord['r1_01_hero_pineapple'][0], elem_coord['r1_01_hero_pineapple'][1]),
        'size': (elem_coord['r1_01_hero_pineapple'][2], elem_coord['r1_01_hero_pineapple'][3]),
        'depth': 5
    },
    # Phrase 2 & 3: "الأناناس أصله من أمريكا الجنوبية واسمه نفسه ارتبط بشكله اللي يشبه كوز الصنوبر."
    {
        'id': 'r1_02', 'asset': 'r1_02_south_america_map',
        't_start': 1.2, 't_dur': 1.6, 'type': 'jelly_pop',
        'pos': (elem_coord['r1_02_south_america_map'][0], elem_coord['r1_02_south_america_map'][1]),
        'size': (elem_coord['r1_02_south_america_map'][2], elem_coord['r1_02_south_america_map'][3]),
        'depth': 3
    },
    {
        'id': 'r1_03', 'asset': 'r1_03_pineapple_comparison',
        't_start': 3.6, 't_dur': 1.2, 'type': 'slide_down',
        'pos': (elem_coord['r1_03_pineapple_comparison'][0], elem_coord['r1_03_pineapple_comparison'][1]),
        'size': (elem_coord['r1_03_pineapple_comparison'][2], elem_coord['r1_03_pineapple_comparison'][3]),
        'depth': 4
    },
    {
        'id': 'r1_04', 'asset': 'r1_04_double_arrow',
        't_start': 4.4, 't_dur': 0.6, 'type': 'jelly_pop',
        'pos': (elem_coord['r1_04_double_arrow'][0], elem_coord['r1_04_double_arrow'][1]),
        'size': (elem_coord['r1_04_double_arrow'][2], elem_coord['r1_04_double_arrow'][3]),
        'depth': 3
    },
    {
        'id': 'r1_05', 'asset': 'r1_05_pine_cone',
        't_start': 4.8, 't_dur': 1.4, 'type': 'jelly_pop',
        'pos': (elem_coord['r1_05_pine_cone'][0], elem_coord['r1_05_pine_cone'][1]),
        'size': (elem_coord['r1_05_pine_cone'][2], elem_coord['r1_05_pine_cone'][3]),
        'depth': 4
    },
    # Camera pans from Zone 1A -> Zone 1B (7.2s - 8.0s)
    # Phrase 4-6: "رمز ثراء بشكل جنوني... وصلت قيمة الثمرة الواحدة في إنجلترا إلى مبالغ ضخمة جدا بمقاييس اليوم."
    {
        'id': 'r1_06', 'asset': 'r1_06_wealthy_gentleman_england_gold',
        't_start': 8.0, 't_dur': 2.6, 'type': 'outside_in_pen',
        'pos': (elem_coord['r1_06_wealthy_gentleman_england_gold'][0], elem_coord['r1_06_wealthy_gentleman_england_gold'][1]),
        'size': (elem_coord['r1_06_wealthy_gentleman_england_gold'][2], elem_coord['r1_06_wealthy_gentleman_england_gold'][3]),
        'depth': 5
    },

    # === ROW 2: Phrase 7 (19.6-23.9s), Phrase 8 (24.2-29.9s), Phrase 9/10 (30.5-37.0s) ===
    # Transition Row 1 -> Row 2 at 19.0s - 19.8s
    # Phrase 7: "لدرجة إن بعض الأغنياء كانوا يستأجرون الأناناسة لليلة واحدة."
    {
        'id': 'r2_01', 'asset': 'r2_01_butler_velvet_pillow',
        't_start': 19.6, 't_dur': 1.6, 'type': 'slide_down',
        'pos': (elem_coord['r2_01_butler_velvet_pillow'][0], elem_coord['r2_01_butler_velvet_pillow'][1]),
        'size': (elem_coord['r2_01_butler_velvet_pillow'][2], elem_coord['r2_01_butler_velvet_pillow'][3]),
        'depth': 4
    },
    # Phrase 8: "مو عشان يأكلونها، بس عشان يمشون فيها أو يحطونها وسط الطاولة ويستعرضون فيها قدام الضيوف."
    {
        'id': 'r2_02', 'asset': 'r2_02_admiring_guests',
        't_start': 20.8, 't_dur': 2.0, 'type': 'outside_in_pen',
        'pos': (elem_coord['r2_02_admiring_guests'][0], elem_coord['r2_02_admiring_guests'][1]),
        'size': (elem_coord['r2_02_admiring_guests'][2], elem_coord['r2_02_admiring_guests'][3]),
        'depth': 5
    },
    # Camera pans from Zone 2A -> Zone 2B (23.8s - 24.6s)
    {
        'id': 'r2_04', 'asset': 'r2_04_lavish_banquet_table',
        't_start': 24.6, 't_dur': 1.8, 'type': 'slide_up',
        'pos': (elem_coord['r2_04_lavish_banquet_table'][0], elem_coord['r2_04_lavish_banquet_table'][1]),
        'size': (elem_coord['r2_04_lavish_banquet_table'][2], elem_coord['r2_04_lavish_banquet_table'][3]),
        'depth': 4
    },
    # Phrase 9 & 10: "وبعضهم كان يخلي الأناناس على الطاولة لين تخرب، فقط لإثبات إن عنده فلوس لدرجة يقدر يرميها."
    {
        'id': 'r2_05', 'asset': 'r2_05_rich_man_throwing',
        't_start': 30.6, 't_dur': 1.4, 'type': 'slide_down',
        'pos': (elem_coord['r2_05_rich_man_throwing'][0], elem_coord['r2_05_rich_man_throwing'][1]),
        'size': (elem_coord['r2_05_rich_man_throwing'][2], elem_coord['r2_05_rich_man_throwing'][3]),
        'depth': 4
    },
    {
        'id': 'r2_06', 'asset': 'r2_06_trash_rotting_pineapple',
        't_start': 33.6, 't_dur': 1.4, 'type': 'jelly_pop',
        'pos': (elem_coord['r2_06_trash_rotting_pineapple'][0], elem_coord['r2_06_trash_rotting_pineapple'][1]),
        'size': (elem_coord['r2_06_trash_rotting_pineapple'][2], elem_coord['r2_06_trash_rotting_pineapple'][3]),
        'depth': 3
    },

    # === ROW 3: Phrase 11/12 (37.6-40.5s), Phrase 13/14 (41.1-45.0s), Phrase 15 (45.5-50.5s) ===
    # Transition Row 2 -> Row 3 at 36.8s - 37.6s
    # Phrase 11 & 12: "لكن داخل الأناناس في شيء مثير للاهتمام."
    {
        'id': 'r3_01', 'asset': 'r3_01_cross_section_cells',
        't_start': 37.6, 't_dur': 1.8, 'type': 'outside_in_pen',
        'pos': (elem_coord['r3_01_cross_section_cells'][0], elem_coord['r3_01_cross_section_cells'][1]),
        'size': (elem_coord['r3_01_cross_section_cells'][2], elem_coord['r3_01_cross_section_cells'][3]),
        'depth': 5
    },
    # Phrase 13 & 14: "إنزيم اسمه بروميلين، وله قدرة على تكسير البروتينات."
    {
        'id': 'r3_02', 'asset': 'r3_02_protein_molecule',
        't_start': 41.0, 't_dur': 1.4, 'type': 'jelly_pop',
        'pos': (elem_coord['r3_02_protein_molecule'][0], elem_coord['r3_02_protein_molecule'][1]),
        'size': (elem_coord['r3_02_protein_molecule'][2], elem_coord['r3_02_protein_molecule'][3]),
        'depth': 3
    },
    {
        'id': 'r3_03', 'asset': 'r3_03_blue_arrow',
        't_start': 42.2, 't_dur': 0.6, 'type': 'slide_down',
        'pos': (elem_coord['r3_03_blue_arrow'][0], elem_coord['r3_03_blue_arrow'][1]),
        'size': (elem_coord['r3_03_blue_arrow'][2], elem_coord['r3_03_blue_arrow'][3]),
        'depth': 2
    },
    {
        'id': 'r3_04', 'asset': 'r3_04_broken_protein_fragments',
        't_start': 43.0, 't_dur': 1.4, 'type': 'pulse_pop',
        'pos': (elem_coord['r3_04_broken_protein_fragments'][0], elem_coord['r3_04_broken_protein_fragments'][1]),
        'size': (elem_coord['r3_04_broken_protein_fragments'][2], elem_coord['r3_04_broken_protein_fragments'][3]),
        'depth': 3
    },
    # Camera pans from Zone 3A -> Zone 3B (44.8s - 45.6s)
    # Phrase 15: "وعشان كذا، بعد ما تأكل أناناس طازج، ممكن تحس بتنميل أو وخز في لسانك."
    {
        'id': 'r3_05', 'asset': 'r3_05_meat_tenderizer_bromelain',
        't_start': 45.6, 't_dur': 1.6, 'type': 'slide_up',
        'pos': (elem_coord['r3_05_meat_tenderizer_bromelain'][0], elem_coord['r3_05_meat_tenderizer_bromelain'][1]),
        'size': (elem_coord['r3_05_meat_tenderizer_bromelain'][2], elem_coord['r3_05_meat_tenderizer_bromelain'][3]),
        'depth': 4
    },
    {
        'id': 'r3_06', 'asset': 'r3_06_stinging_tongue',
        't_start': 47.0, 't_dur': 1.5, 'type': 'jelly_pop',
        'pos': (elem_coord['r3_06_stinging_tongue'][0], elem_coord['r3_06_stinging_tongue'][1]),
        'size': (elem_coord['r3_06_stinging_tongue'][2], elem_coord['r3_06_stinging_tongue'][3]),
        'depth': 4
    },
    {
        'id': 'r3_07', 'asset': 'r3_07_man_touching_stinging_tongue',
        't_start': 48.5, 't_dur': 1.4, 'type': 'slide_down',
        'pos': (elem_coord['r3_07_man_touching_stinging_tongue'][0], elem_coord['r3_07_man_touching_stinging_tongue'][1]),
        'size': (elem_coord['r3_07_man_touching_stinging_tongue'][2], elem_coord['r3_07_man_touching_stinging_tongue'][3]),
        'depth': 4
    },

    # === ROW 4: Phrase 16 & 17 (51.0-54.7s) ===
    # Transition Row 3 -> Row 4 at 50.5s - 51.2s
    # Phrase 16: "إنت تاكل الأناناس..."
    {
        'id': 'r4_01', 'asset': 'r4_01_pineapple_slice_dripping',
        't_start': 51.0, 't_dur': 1.0, 'type': 'outside_in_pen',
        'pos': (elem_coord['r4_01_pineapple_slice_dripping'][0], elem_coord['r4_01_pineapple_slice_dripping'][1]),
        'size': (elem_coord['r4_01_pineapple_slice_dripping'][2], elem_coord['r4_01_pineapple_slice_dripping'][3]),
        'depth': 5
    },
    {
        'id': 'r4_02', 'asset': 'r4_02_red_curved_arrow',
        't_start': 51.6, 't_dur': 0.5, 'type': 'slide_down',
        'pos': (elem_coord['r4_02_red_curved_arrow'][0], elem_coord['r4_02_red_curved_arrow'][1]),
        'size': (elem_coord['r4_02_red_curved_arrow'][2], elem_coord['r4_02_red_curved_arrow'][3]),
        'depth': 2
    },
    {
        'id': 'r4_03', 'asset': 'r4_03_mouth_eating_pineapple',
        't_start': 52.0, 't_dur': 1.4, 'type': 'jelly_pop',
        'pos': (elem_coord['r4_03_mouth_eating_pineapple'][0], elem_coord['r4_03_mouth_eating_pineapple'][1]),
        'size': (elem_coord['r4_03_mouth_eating_pineapple'][2], elem_coord['r4_03_mouth_eating_pineapple'][3]),
        'depth': 4
    },
    # Camera pans from Zone 4A -> Zone 4B (52.5s - 53.0s)
    # Phrase 17: "والأناناس بعد ياكل شوي منك!"
    {
        'id': 'r4_04', 'asset': 'r4_04_carnivorous_monster_pineapple',
        't_start': 52.8, 't_dur': 1.8, 'type': 'outside_in_pen',
        'pos': (elem_coord['r4_04_carnivorous_monster_pineapple'][0], elem_coord['r4_04_carnivorous_monster_pineapple'][1]),
        'size': (elem_coord['r4_04_carnivorous_monster_pineapple'][2], elem_coord['r4_04_carnivorous_monster_pineapple'][3]),
        'depth': 5
    },
    {
        'id': 'r4_05', 'asset': 'r4_05_terrified_man_running',
        't_start': 53.6, 't_dur': 1.6, 'type': 'jelly_pop',
        'pos': (elem_coord['r4_05_terrified_man_running'][0], elem_coord['r4_05_terrified_man_running'][1]),
        'size': (elem_coord['r4_05_terrified_man_running'][2], elem_coord['r4_05_terrified_man_running'][3]),
        'depth': 4
    },
]

elements_staging.sort(key=lambda x: x.get('depth', 0))

# 4. Camera Trajectory (4 Rows, 8 Zones, Ultra-Smooth S-Curves, Synced with Narration)
def get_camera_state(t):
    # --- ROW 1 (0.0s - 19.0s, Y = 800) ---
    if t < 7.2:
        return (row_zones['1']['zone_A'][0], 800.0, CAM_ZOOM)
    elif t < 8.0:
        p = smootherstep((t - 7.2) / 0.8)
        cx = row_zones['1']['zone_A'][0] + (row_zones['1']['zone_B'][0] - row_zones['1']['zone_A'][0]) * p
        return (cx, 800.0, CAM_ZOOM)
    elif t < 19.0:
        return (row_zones['1']['zone_B'][0], 800.0, CAM_ZOOM)
        
    # Transition Row 1 -> Row 2 (19.0s - 19.8s, 0.8s smooth diagonal glide)
    elif t < 19.8:
        p = smootherstep((t - 19.0) / 0.8)
        cx = row_zones['1']['zone_B'][0] + (row_zones['2']['zone_A'][0] - row_zones['1']['zone_B'][0]) * p
        cy = 800.0 + (2800.0 - 800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 2 (19.8s - 36.8s, Y = 2800) ---
    elif t < 23.8:
        return (row_zones['2']['zone_A'][0], 2800.0, CAM_ZOOM)
    elif t < 24.6:
        p = smootherstep((t - 23.8) / 0.8)
        cx = row_zones['2']['zone_A'][0] + (row_zones['2']['zone_B'][0] - row_zones['2']['zone_A'][0]) * p
        return (cx, 2800.0, CAM_ZOOM)
    elif t < 36.8:
        return (row_zones['2']['zone_B'][0], 2800.0, CAM_ZOOM)

    # Transition Row 2 -> Row 3 (36.8s - 37.6s, 0.8s smooth diagonal glide)
    elif t < 37.6:
        p = smootherstep((t - 36.8) / 0.8)
        cx = row_zones['2']['zone_B'][0] + (row_zones['3']['zone_A'][0] - row_zones['2']['zone_B'][0]) * p
        cy = 2800.0 + (4800.0 - 2800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 3 (37.6s - 50.5s, Y = 4800) ---
    elif t < 44.8:
        return (row_zones['3']['zone_A'][0], 4800.0, CAM_ZOOM)
    elif t < 45.6:
        p = smootherstep((t - 44.8) / 0.8)
        cx = row_zones['3']['zone_A'][0] + (row_zones['3']['zone_B'][0] - row_zones['3']['zone_A'][0]) * p
        return (cx, 4800.0, CAM_ZOOM)
    elif t < 50.5:
        return (row_zones['3']['zone_B'][0], 4800.0, CAM_ZOOM)

    # Transition Row 3 -> Row 4 (50.5s - 51.2s, 0.7s smooth diagonal glide)
    elif t < 51.2:
        p = smootherstep((t - 50.5) / 0.7)
        cx = row_zones['3']['zone_B'][0] + (row_zones['4']['zone_A'][0] - row_zones['3']['zone_B'][0]) * p
        cy = 4800.0 + (6800.0 - 4800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 4 (51.2s - 57.0s, Y = 6800) ---
    elif t < 52.5:
        return (row_zones['4']['zone_A'][0], 6800.0, CAM_ZOOM)
    elif t < 53.0:
        p = smootherstep((t - 52.5) / 0.5)
        cx = row_zones['4']['zone_A'][0] + (row_zones['4']['zone_B'][0] - row_zones['4']['zone_A'][0]) * p
        return (cx, 6800.0, CAM_ZOOM)
    else:
        # Finale: Freeze & hold steadily on Zone 4B until 57.0s (ZERO OUTRO ZOOM-OUT!)
        return (row_zones['4']['zone_B'][0], 6800.0, CAM_ZOOM)

# 5. Direct Viewport Blending Function
def blend_sprite_screen(frame, sprite_bgra, scr_x, scr_y, scr_w, scr_h, alpha_mult=1.0):
    if scr_w <= 2 or scr_h <= 2:
        return
        
    x1 = scr_x
    y1 = scr_y
    x2 = scr_x + scr_w
    y2 = scr_y + scr_h
    
    if x2 <= 0 or x1 >= WIDTH or y2 <= 0 or y1 >= HEIGHT:
        return
        
    clip_x1 = max(0, x1)
    clip_y1 = max(0, y1)
    clip_x2 = min(WIDTH, x2)
    clip_y2 = min(HEIGHT, y2)
    
    src_x1 = int(round((clip_x1 - x1) * (sprite_bgra.shape[1] / float(scr_w))))
    src_y1 = int(round((clip_y1 - y1) * (sprite_bgra.shape[0] / float(scr_h))))
    src_x2 = int(round((clip_x2 - x1) * (sprite_bgra.shape[1] / float(scr_w))))
    src_y2 = int(round((clip_y2 - y1) * (sprite_bgra.shape[0] / float(scr_h))))
    
    src_x1 = max(0, min(sprite_bgra.shape[1], src_x1))
    src_y1 = max(0, min(sprite_bgra.shape[0], src_y1))
    src_x2 = max(src_x1, min(sprite_bgra.shape[1], src_x2))
    src_y2 = max(src_y1, min(sprite_bgra.shape[0], src_y2))
    
    target_w = clip_x2 - clip_x1
    target_h = clip_y2 - clip_y1
    
    if target_w <= 0 or target_h <= 0 or src_x2 <= src_x1 or src_y2 <= src_y1:
        return
        
    crop_sprite = sprite_bgra[src_y1:src_y2, src_x1:src_x2]
    resized = cv2.resize(crop_sprite, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
    
    alpha = (resized[:, :, 3].astype(np.float32) / 255.0) * alpha_mult
    alpha_3d = np.dstack([alpha, alpha, alpha])
    
    target_region = frame[clip_y1:clip_y2, clip_x1:clip_x2].astype(np.float32)
    bgr = resized[:, :, :3].astype(np.float32)
    
    blended = bgr * alpha_3d + target_region * (1.0 - alpha_3d)
    frame[clip_y1:clip_y2, clip_x1:clip_x2] = np.clip(blended, 0, 255).astype(np.uint8)

# 6. Render Loop with FFmpeg Pipe
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-s", f"{WIDTH}x{HEIGHT}",
    "-pix_fmt", "bgr24",
    "-r", str(FPS),
    "-i", "-",
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-crf", "17",
    "-pix_fmt", "yuv420p",
    raw_video_mp4
]

print("\nStarting video rendering pipeline with FFmpeg...")
ffmpeg_log = open("sections/04_pineapple/ffmpeg_pineapple_render.log", "w")
pipe = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=ffmpeg_log, stderr=ffmpeg_log)

t_render_start = time.time()

for frame_idx in range(TOTAL_FRAMES):
    time_s = frame_idx / float(FPS)
    
    cam_x, cam_y, cam_zoom = get_camera_state(time_s)
    
    # Crisp whiteboard background
    frame = np.full((HEIGHT, WIDTH, 3), 255, dtype=np.uint8)
    
    active_hand_screen_pt = None
    
    for elem in elements_staging:
        t_start = elem['t_start']
        t_dur = elem['t_dur']
        anim_type = elem['type']
        
        if time_s < t_start:
            continue
            
        prog = (time_s - t_start) / t_dur if t_dur > 0 else 1.0
        prog = min(1.0, max(0.0, prog))
        
        orig_x, orig_y = elem['pos']
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
        elif anim_type == 'pulse_pop':
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

print(f"Multiplexing audio + video into: {final_video_mp4}")
subprocess.run(final_mux_cmd, check=True)
print("\n🎉 SECTION 04 PINEAPPLE VIDEO COMPLETE!")
print(f"Final video: {final_video_mp4}")
