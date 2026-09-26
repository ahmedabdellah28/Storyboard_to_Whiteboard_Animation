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
print("  🥝 MASTERPIECE WHITEBOARD ENGINE 2026 — SECTION 02: KIWI (PERFECT AUDIO SYNC) 🥝")
print("=====================================================================================")

WIDTH, HEIGHT = 1920, 1080
FPS = 30
DURATION_SEC = 58.24
TOTAL_FRAMES = int(round(DURATION_SEC * FPS)) # 1747 frames

CAM_ZOOM = 0.58
raw_video_mp4 = "sections/02_kiwi/raw_kiwi_cinematic_panned.mp4"
final_video_mp4 = "sections/02_kiwi/final_whiteboard_1080p.mp4"
master_audio_wav = "sections/02_kiwi/master_audio.wav"

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
assets_dir = "sections/02_kiwi/assets"
asset_files = [f for f in os.listdir(assets_dir) if f.endswith(".png")]
assets = {}
for af in asset_files:
    aid = os.path.splitext(af)[0]
    p = os.path.join(assets_dir, af)
    img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if img is not None:
        assets[aid] = img
print(f"Loaded {len(assets)} exact-contour Kiwi assets.")

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

# Pre-cache Hero Inking for Kiwi (Strict Hand Discipline)
hero_cache = {}
hero_configs = [
    ("r1_01", 0.0,  1.0),
    ("r1_03", 1.5,  1.7),
    ("r2_01", 10.6, 2.0),
    ("r5_01", 48.2, 2.0),
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
with open("sections/02_kiwi/placed_elements_layout.json", "r", encoding="utf-8") as f:
    layout_data = json.load(f)

placed_elements = layout_data['elements']
row_zones = layout_data['zones']

elem_coord = {}
for r_k, r_elems in placed_elements.items():
    for e in r_elems:
        elem_coord[e['aid']] = (e['x'], e['y'], e['w'], e['h'])

# 3. Complete Staging for 35 Elements with EXACT VERIFIED TIMESTAMPS matching Voiceover
elements_staging = [
    # === PARAGRAPH 1: Origins, China, Gooseberry & Medicine (0.0s - 10.5s) ===
    # p1: "الكيوي" (0.0s - 1.0s) -> Hand draws giant kiwi alone
    {
        'id': 'r1_01', 'asset': 'r1_01',
        't_start': 0.0, 't_dur': 1.0, 'type': 'outside_in_pen',
        'pos': (elem_coord['r1_01'][0], elem_coord['r1_01'][1]),
        'size': (elem_coord['r1_01'][2], elem_coord['r1_01'][3]),
        'depth': 5
    },
    # Leaves appear ONLY AFTER giant kiwi hand finishes at 1.0s
    {
        'id': 'r1_02', 'asset': 'r1_02',
        't_start': 1.0, 't_dur': 0.5, 'type': 'organic_grow',
        'pos': (elem_coord['r1_02'][0], elem_coord['r1_02'][1]),
        'size': (elem_coord['r1_02'][2], elem_coord['r1_02'][3]),
        'depth': 3
    },
    # p2: "الكيوي أصلها الحقيقي من الصين..." (1.0s - 7.0s)
    # Hand draws Chinese Sage alone (1.5s - 3.2s)
    {
        'id': 'r1_03', 'asset': 'r1_03',
        't_start': 1.5, 't_dur': 1.7, 'type': 'outside_in_pen',
        'pos': (elem_coord['r1_03'][0], elem_coord['r1_03'][1]),
        'size': (elem_coord['r1_03'][2], elem_coord['r1_03'][3]),
        'depth': 4
    },
    # Gooseberry appears ONLY AFTER hand finishes with Sage at 3.2s!
    {
        'id': 'r1_04', 'asset': 'r1_04',
        't_start': 3.5, 't_dur': 0.8, 'type': 'organic_grow',
        'pos': (elem_coord['r1_04'][0], elem_coord['r1_04'][1]),
        'size': (elem_coord['r1_04'][2], elem_coord['r1_04'][3]),
        'depth': 3
    },
    {
        'id': 'r1_05', 'asset': 'r1_05',
        't_start': 4.5, 't_dur': 0.8, 'type': 'jelly_pop',
        'pos': (elem_coord['r1_05'][0], elem_coord['r1_05'][1]),
        'size': (elem_coord['r1_05'][2], elem_coord['r1_05'][3]),
        'depth': 4
    },
    # p3: "وكان يستخدم كغذاء وحتى كدواء" (7.0s - 10.5s)
    {
        'id': 'r1_06', 'asset': 'r1_06',
        't_start': 7.2, 't_dur': 1.0, 'type': 'slide_up',
        'pos': (elem_coord['r1_06'][0], elem_coord['r1_06'][1]),
        'size': (elem_coord['r1_06'][2], elem_coord['r1_06'][3]),
        'depth': 5
    },

    # === PARAGRAPH 2: New Zealand, Seeds & Size Evolution (10.5s - 18.0s) ===
    # p4: "لكن في أوائل القرن العشرين المزارعين في نيوزيلندا حصلوا على بذوره" (10.5s - 15.0s)
    # Hand draws NZ Farmer alone (10.6s - 12.6s)
    {
        'id': 'r2_01', 'asset': 'r2_01',
        't_start': 10.6, 't_dur': 2.0, 'type': 'outside_in_pen',
        'pos': (elem_coord['r2_01'][0], elem_coord['r2_01'][1]),
        'size': (elem_coord['r2_01'][2], elem_coord['r2_01'][3]),
        'depth': 5
    },
    # Elements appear ONLY AFTER hand finishes with Farmer at 12.6s!
    {
        'id': 'r2_02', 'asset': 'r2_02',
        't_start': 12.8, 't_dur': 0.8, 'type': 'jelly_pop',
        'pos': (elem_coord['r2_02'][0], elem_coord['r2_02'][1]),
        'size': (elem_coord['r2_02'][2], elem_coord['r2_02'][3]),
        'depth': 2
    },
    {
        'id': 'r2_03', 'asset': 'r2_03',
        't_start': 13.5, 't_dur': 0.7, 'type': 'jelly_pop',
        'pos': (elem_coord['r2_03'][0], elem_coord['r2_03'][1]),
        'size': (elem_coord['r2_03'][2], elem_coord['r2_03'][3]),
        'depth': 4
    },
    {
        'id': 'r2_04', 'asset': 'r2_04',
        't_start': 14.0, 't_dur': 0.7, 'type': 'jelly_pop',
        'pos': (elem_coord['r2_04'][0], elem_coord['r2_04'][1]),
        'size': (elem_coord['r2_04'][2], elem_coord['r2_04'][3]),
        'depth': 5
    },
    # p5: "وبدأوا يطورون النوع اللي نعرفه اليوم" (15.0s - 18.0s)
    {
        'id': 'r2_05', 'asset': 'r2_05',
        't_start': 15.1, 't_dur': 0.6, 'type': 'organic_grow',
        'pos': (elem_coord['r2_05'][0], elem_coord['r2_05'][1]),
        'size': (elem_coord['r2_05'][2], elem_coord['r2_05'][3]),
        'depth': 3
    },
    {
        'id': 'r2_06', 'asset': 'r2_06',
        't_start': 15.5, 't_dur': 0.6, 'type': 'organic_grow',
        'pos': (elem_coord['r2_06'][0], elem_coord['r2_06'][1]),
        'size': (elem_coord['r2_06'][2], elem_coord['r2_06'][3]),
        'depth': 3
    },
    {
        'id': 'r2_07', 'asset': 'r2_07',
        't_start': 16.0, 't_dur': 0.9, 'type': 'organic_grow',
        'pos': (elem_coord['r2_07'][0], elem_coord['r2_07'][1]),
        'size': (elem_coord['r2_07'][2], elem_coord['r2_07'][3]),
        'depth': 4
    },
    {
        'id': 'r2_08', 'asset': 'r2_08',
        't_start': 16.8, 't_dur': 1.0, 'type': 'jelly_pop',
        'pos': (elem_coord['r2_08'][0], elem_coord['r2_08'][1]),
        'size': (elem_coord['r2_08'][2], elem_coord['r2_08'][3]),
        'depth': 4
    },

    # === PARAGRAPH 3: Kiwi Bird & Global Shipping (18.0s - 25.5s) ===
    # p6: "وحتى غيروا اسمه إلى الكيوي نسبة لطائر الكيوي..." (18.0s - 25.5s)
    {
        'id': 'r3_01', 'asset': 'r3_01',
        't_start': 18.2, 't_dur': 1.2, 'type': 'jelly_pop',
        'pos': (elem_coord['r3_01'][0], elem_coord['r3_01'][1]),
        'size': (elem_coord['r3_01'][2], elem_coord['r3_01'][3]),
        'depth': 5
    },
    {
        'id': 'r3_02', 'asset': 'r3_02',
        't_start': 18.8, 't_dur': 0.6, 'type': 'jelly_pop',
        'pos': (elem_coord['r3_02'][0], elem_coord['r3_02'][1]),
        'size': (elem_coord['r3_02'][2], elem_coord['r3_02'][3]),
        'depth': 4
    },
    {
        'id': 'r3_03', 'asset': 'r3_03',
        't_start': 20.0, 't_dur': 0.7, 'type': 'slide_down',
        'pos': (elem_coord['r3_03'][0], elem_coord['r3_03'][1]),
        'size': (elem_coord['r3_03'][2], elem_coord['r3_03'][3]),
        'depth': 4
    },
    {
        'id': 'r3_04', 'asset': 'r3_04',
        't_start': 20.8, 't_dur': 1.5, 'type': 'travel_slide',
        'pos_start': (elem_coord['r3_04'][0] - 120, elem_coord['r3_04'][1]),
        'pos_end': (elem_coord['r3_04'][0], elem_coord['r3_04'][1]),
        'pos': (elem_coord['r3_04'][0], elem_coord['r3_04'][1]),
        'size': (elem_coord['r3_04'][2], elem_coord['r3_04'][3]),
        'depth': 6
    },
    {
        'id': 'r3_05', 'asset': 'r3_05',
        't_start': 22.0, 't_dur': 0.9, 'type': 'jelly_pop',
        'pos': (elem_coord['r3_05'][0], elem_coord['r3_05'][1]),
        'size': (elem_coord['r3_05'][2], elem_coord['r3_05'][3]),
        'depth': 4
    },
    {
        'id': 'r3_06', 'asset': 'r3_06',
        't_start': 23.5, 't_dur': 0.9, 'type': 'jelly_pop',
        'pos': (elem_coord['r3_06'][0], elem_coord['r3_06'][1]),
        'size': (elem_coord['r3_06'][2], elem_coord['r3_06'][3]),
        'depth': 5
    },

    # === PARAGRAPH 4: Scientific Berry, Skin Fiber & Varieties (25.5s - 48.0s) ===
    # p7: "والأغرب الكيوي علميا يعتبر نوعا من التوت" (25.5s - 29.5s)
    {
        'id': 'r4_01', 'asset': 'r4_01',
        't_start': 25.8, 't_dur': 1.0, 'type': 'jelly_pop',
        'pos': (elem_coord['r4_01'][0], elem_coord['r4_01'][1]),
        'size': (elem_coord['r4_01'][2], elem_coord['r4_01'][3]),
        'depth': 4
    },
    # p8: "وحتى القشرة تقدر تاكلها لأنها مليانة ألياف" (29.5s - 33.5s)
    {
        'id': 'r4_02', 'asset': 'r4_02',
        't_start': 29.8, 't_dur': 1.0, 'type': 'jelly_pop',
        'pos': (elem_coord['r4_02'][0], elem_coord['r4_02'][1]),
        'size': (elem_coord['r4_02'][2], elem_coord['r4_02'][3]),
        'depth': 5
    },
    {
        'id': 'r4_03', 'asset': 'r4_03',
        't_start': 31.0, 't_dur': 0.8, 'type': 'slide_up',
        'pos': (elem_coord['r4_03'][0], elem_coord['r4_03'][1]),
        'size': (elem_coord['r4_03'][2], elem_coord['r4_03'][3]),
        'depth': 3
    },
    {
        'id': 'r4_04', 'asset': 'r4_04',
        't_start': 32.0, 't_dur': 0.8, 'type': 'pulse_pop',
        'pos': (elem_coord['r4_04'][0], elem_coord['r4_04'][1]),
        'size': (elem_coord['r4_04'][2], elem_coord['r4_04'][3]),
        'depth': 4
    },
    # p9: "وأغلب الناس يعرفون الكيوي الأخضر..." (33.5s - 40.0s)
    {
        'id': 'r4_05', 'asset': 'r4_05',
        't_start': 34.0, 't_dur': 1.0, 'type': 'jelly_pop',
        'pos': (elem_coord['r4_05'][0], elem_coord['r4_05'][1]),
        'size': (elem_coord['r4_05'][2], elem_coord['r4_05'][3]),
        'depth': 4
    },
    # p10: "الذهبي قشرته أنعم وطعمه أحلى والأحمر نادر أكثر..." (40.0s - 48.0s)
    {
        'id': 'r4_06', 'asset': 'r4_06',
        't_start': 40.5, 't_dur': 1.0, 'type': 'jelly_pop',
        'pos': (elem_coord['r4_06'][0], elem_coord['r4_06'][1]),
        'size': (elem_coord['r4_06'][2], elem_coord['r4_06'][3]),
        'depth': 4
    },
    {
        'id': 'r4_07', 'asset': 'r4_07',
        't_start': 44.0, 't_dur': 1.0, 'type': 'jelly_pop',
        'pos': (elem_coord['r4_07'][0], elem_coord['r4_07'][1]),
        'size': (elem_coord['r4_07'][2], elem_coord['r4_07'][3]),
        'depth': 4
    },

    # === PARAGRAPH 5: Nutrition, Protein Enzymes & Vitamin C (48.0s - 58.24s) ===
    # p11: "والكيوي فيه إنزيم طبيعي يساعد على تكسير البروتين وفوق هذا غني بفيتامين سي" (48.0s - 54.0s)
    # Hand draws tasting man alone (48.2s - 50.2s)
    {
        'id': 'r5_01', 'asset': 'r5_01',
        't_start': 48.2, 't_dur': 2.0, 'type': 'outside_in_pen',
        'pos': (elem_coord['r5_01'][0], elem_coord['r5_01'][1]),
        'size': (elem_coord['r5_01'][2], elem_coord['r5_01'][3]),
        'depth': 5
    },
    # Elements appear ONLY AFTER hand is finished with tasting man at 50.2s!
    {
        'id': 'r5_02', 'asset': 'r5_02',
        't_start': 50.4, 't_dur': 0.7, 'type': 'slide_up',
        'pos': (elem_coord['r5_02'][0], elem_coord['r5_02'][1]),
        'size': (elem_coord['r5_02'][2], elem_coord['r5_02'][3]),
        'depth': 4
    },
    {
        'id': 'r5_03', 'asset': 'r5_03',
        't_start': 51.0, 't_dur': 0.7, 'type': 'jelly_pop',
        'pos': (elem_coord['r5_03'][0], elem_coord['r5_03'][1]),
        'size': (elem_coord['r5_03'][2], elem_coord['r5_03'][3]),
        'depth': 5
    },
    {
        'id': 'r5_04', 'asset': 'r5_04',
        't_start': 51.8, 't_dur': 0.8, 'type': 'jelly_pop',
        'pos': (elem_coord['r5_04'][0], elem_coord['r5_04'][1]),
        'size': (elem_coord['r5_04'][2], elem_coord['r5_04'][3]),
        'depth': 4
    },
    {
        'id': 'r5_05', 'asset': 'r5_05',
        't_start': 52.2, 't_dur': 0.5, 'type': 'jelly_pop',
        'pos': (elem_coord['r5_05'][0], elem_coord['r5_05'][1]),
        'size': (elem_coord['r5_05'][2], elem_coord['r5_05'][3]),
        'depth': 4
    },
    {
        'id': 'r5_06', 'asset': 'r5_06',
        't_start': 52.4, 't_dur': 0.5, 'type': 'jelly_pop',
        'pos': (elem_coord['r5_06'][0], elem_coord['r5_06'][1]),
        'size': (elem_coord['r5_06'][2], elem_coord['r5_06'][3]),
        'depth': 4
    },
    {
        'id': 'r5_07', 'asset': 'r5_07',
        't_start': 52.8, 't_dur': 1.0, 'type': 'golden_burst',
        'pos': (elem_coord['r5_07'][0], elem_coord['r5_07'][1]),
        'size': (elem_coord['r5_07'][2], elem_coord['r5_07'][3]),
        'depth': 6
    },
    # p12: "يعني مو بس شكله غريب حتى تركيبه الغذائي مختلف" (54.0s - 58.24s)
    {
        'id': 'r5_08', 'asset': 'r5_08',
        't_start': 54.5, 't_dur': 1.2, 'type': 'jelly_pop',
        'pos': (elem_coord['r5_08'][0], elem_coord['r5_08'][1]),
        'size': (elem_coord['r5_08'][2], elem_coord['r5_08'][3]),
        'depth': 5
    }
]

elements_staging.sort(key=lambda x: x.get('depth', 0))

# 4. Camera Trajectory: Synchronized strictly with Voiceover Paragraph Boundaries
def get_camera_state(t):
    # --- ROW 1 (0.0s - 9.8s, Y = 800) ---
    if t < 3.2:
        # Zone 1A: Giant Kiwi, leaves, Chinese Sage
        return (row_zones['1']['zone_A'][0], 800.0, CAM_ZOOM)
    elif t < 4.0:
        # Pan 1A -> 1B (0.8s) right as sage drawing finishes
        p = smootherstep((t - 3.2) / 0.8)
        cx = row_zones['1']['zone_A'][0] + (row_zones['1']['zone_B'][0] - row_zones['1']['zone_A'][0]) * p
        return (cx, 800.0, CAM_ZOOM)
    elif t < 9.8:
        # Zone 1B: Gooseberry, berries bowl, mortar medicine
        return (row_zones['1']['zone_B'][0], 800.0, CAM_ZOOM)
        
    # Transition Row 1 -> Row 2 (9.8s - 10.5s, 0.7s smooth glide)
    elif t < 10.5:
        p = smootherstep((t - 9.8) / 0.7)
        cx = row_zones['1']['zone_B'][0] + (row_zones['2']['zone_A'][0] - row_zones['1']['zone_B'][0]) * p
        cy = 800.0 + (2800.0 - 800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 2 (10.5s - 17.6s, Y = 2800) ---
    elif t < 14.5:
        # Zone 2A: NZ Farmer hero, NZ Map, seed sack, hand with seeds
        return (row_zones['2']['zone_A'][0], 2800.0, CAM_ZOOM)
    elif t < 15.1:
        # Pan 2A -> 2B (0.6s) as cultivation and breeding begins
        p = smootherstep((t - 14.5) / 0.6)
        cx = row_zones['2']['zone_A'][0] + (row_zones['2']['zone_B'][0] - row_zones['2']['zone_A'][0]) * p
        return (cx, 2800.0, CAM_ZOOM)
    elif t < 17.6:
        # Zone 2B: Sprout, seedling, pergola vine tree, 5 size progression
        return (row_zones['2']['zone_B'][0], 2800.0, CAM_ZOOM)

    # Transition Row 2 -> Row 3 (17.6s - 18.2s, 0.6s smooth glide)
    elif t < 18.2:
        p = smootherstep((t - 17.6) / 0.6)
        cx = row_zones['2']['zone_B'][0] + (row_zones['3']['zone_A'][0] - row_zones['2']['zone_B'][0]) * p
        cy = 2800.0 + (4800.0 - 2800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 3 (18.2s - 24.8s, Y = 4800) ---
    elif t < 20.2:
        # Zone 3A: Kiwi bird & speech bubble ("نسبة لطائر الكيوي")
        return (row_zones['3']['zone_A'][0], 4800.0, CAM_ZOOM)
    elif t < 21.0:
        # Pan 3A -> 3B (0.8s) as shipping and global trade begins
        p = smootherstep((t - 20.2) / 0.8)
        cx = row_zones['3']['zone_A'][0] + (row_zones['3']['zone_B'][0] - row_zones['3']['zone_A'][0]) * p
        return (cx, 4800.0, CAM_ZOOM)
    elif t < 24.8:
        # Zone 3B: Container ship, airplane, globe, green kiwis
        return (row_zones['3']['zone_B'][0], 4800.0, CAM_ZOOM)

    # Transition Row 3 -> Row 4 (24.8s - 25.5s, 0.7s smooth glide)
    elif t < 25.5:
        p = smootherstep((t - 24.8) / 0.7)
        cx = row_zones['3']['zone_B'][0] + (row_zones['4']['zone_A'][0] - row_zones['3']['zone_B'][0]) * p
        cy = 4800.0 + (6800.0 - 4800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 4 (25.5s - 47.4s, Y = 6800) ---
    elif t < 33.5:
        # Zone 4A: Berry science, microscope skin fiber, fiber strands, gut
        return (row_zones['4']['zone_A'][0], 6800.0, CAM_ZOOM)
    elif t < 34.3:
        # Pan 4A -> 4B (0.8s) right at "وأغلب الناس يعرفون الكيوي الأخضر"
        p = smootherstep((t - 33.5) / 0.8)
        cx = row_zones['4']['zone_A'][0] + (row_zones['4']['zone_B'][0] - row_zones['4']['zone_A'][0]) * p
        return (cx, 6800.0, CAM_ZOOM)
    elif t < 47.4:
        # Zone 4B: Green kiwi (34.0s), Golden kiwi (40.5s), Ruby red kiwi (44.0s)
        return (row_zones['4']['zone_B'][0], 6800.0, CAM_ZOOM)

    # Transition Row 4 -> Row 5 (47.4s - 48.1s, 0.7s smooth glide)
    elif t < 48.1:
        p = smootherstep((t - 47.4) / 0.7)
        cx = row_zones['4']['zone_B'][0] + (row_zones['5']['zone_A'][0] - row_zones['4']['zone_B'][0]) * p
        cy = 6800.0 + (8800.0 - 6800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 5 (48.1s - 58.24s, Y = 8800) ---
    elif t < 51.5:
        # Zone 5A: Tasting man hero (48.2s), trio heap (50.4s), red slice (51.0s)
        return (row_zones['5']['zone_A'][0], 8800.0, CAM_ZOOM)
    elif t < 52.3:
        # Pan 5A -> 5B (0.8s) right before "وفوق هذا غني بفيتامين سي" at 52.8s
        p = smootherstep((t - 51.5) / 0.8)
        cx = row_zones['5']['zone_A'][0] + (row_zones['5']['zone_B'][0] - row_zones['5']['zone_A'][0]) * p
        return (cx, 8800.0, CAM_ZOOM)
    else:
        # Zone 5B: Protein enzymes, Vitamin C golden burst (52.8s), Nutrition finale (54.5s)
        # COMPLETELY FROZEN & HELD STEADILY UNTIL 58.24s! (ZERO OUTRO ZOOM-OUT!)
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
ffmpeg_log = open("sections/02_kiwi/ffmpeg_kiwi_render.log", "w")
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
    print(f"--- SUCCESS: Kiwi Perfectly Synced Video created ({os.path.getsize(final_video_mp4) / (1024*1024):.2f} MB) ---")
