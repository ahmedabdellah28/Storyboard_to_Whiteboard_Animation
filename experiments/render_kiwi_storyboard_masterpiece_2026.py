import os
import sys
import json
import math
import cv2
import numpy as np
import subprocess

# Safe console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

print("=====================================================================================")
print("  🥝 MASTERPIECE WHITEBOARD ANIMATION ENGINE 2026 — KIWI STORYBOARD 🥝")
print("=====================================================================================")

WIDTH, HEIGHT = 1920, 1080
FPS = 30
DURATION_SEC = 41.18
TOTAL_FRAMES = int(DURATION_SEC * FPS)

SCALE = 2.5
PAD_X = 120
PAD_Y = 120

CANVAS_W = int(round(1536 * SCALE + 2 * PAD_X)) # 4080
CANVAS_H = int(round(1024 * SCALE + 2 * PAD_Y)) # 2800

raw_video_mp4 = "output_animations/raw_kiwi_video.mp4"
out_mp4 = "output_animations/kiwi_storyboard_masterpiece_2026.mp4"
os.makedirs("output_animations", exist_ok=True)

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
TARGET_HAND_H = 500
TARGET_HAND_W = int(hw * (TARGET_HAND_H / hh))
hand_bgra = cv2.resize(raw_hand, (TARGET_HAND_W, TARGET_HAND_H), interpolation=cv2.INTER_AREA)
HAND_TIP_X = int(round(62 * (TARGET_HAND_H / hh)))
HAND_TIP_Y = int(round(40 * (TARGET_HAND_H / hh)))
print(f"Loaded Drawing Hand: {TARGET_HAND_W}x{TARGET_HAND_H}, Pen Tip: ({HAND_TIP_X}, {HAND_TIP_Y})")

# 2. Load Extracted Kiwi Assets
assets_dir = "project_content/kiwi_assets"
metadata_path = os.path.join(assets_dir, "metadata.json")
with open(metadata_path, "r", encoding="utf-8") as mf:
    metadata = json.load(mf)

assets = {}
for aid, info in metadata.items():
    p = os.path.join(assets_dir, info["file"])
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

# Pre-cache Hero Inking
hero_cache = {}
hero_configs = [
    ("r1_01", 0.25, 2.2), # Giant Kiwi
    ("r1_03", 1.8,  1.8), # Chinese Sage
    ("r2_01", 8.0,  1.8), # NZ Farmer
    ("r5_01", 28.0, 1.8), # Man Eating Kiwi
]
for h_name, t_start, t_dur in hero_configs:
    if h_name in assets:
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

# Coordinate Mapping from 1536x1024 to 4080x2800 Canvas
def S_BOX(rx, ry, rw, rh):
    return (int(round(PAD_X + rx * SCALE)), int(round(PAD_Y + ry * SCALE)), int(round(rw * SCALE)), int(round(rh * SCALE)))

def GET_BOX(aid):
    b = metadata[aid]['orig_box']
    return S_BOX(b[0], b[1], b[2], b[3])

# 5 Rows Staging (Synchronized Word-for-Word with Kiwi Audio)
elements_staging = [
    # === ROW 1: Origins, China & Chinese Gooseberry (0.0s - 6.5s) ===
    {
        'id': 'r1_01', 'asset': 'r1_01',
        't_start': 0.25, 't_dur': 2.2, 'type': 'outside_in_pen', # "الكيوي"
        'pos': (GET_BOX('r1_01')[0], GET_BOX('r1_01')[1]),
        'size': (GET_BOX('r1_01')[2], GET_BOX('r1_01')[3]),
        'depth': 5
    },
    {
        'id': 'r1_02', 'asset': 'r1_02',
        't_start': 1.2, 't_dur': 1.4, 'type': 'slide_down',
        'pos': (GET_BOX('r1_02')[0], GET_BOX('r1_02')[1]),
        'size': (GET_BOX('r1_02')[2], GET_BOX('r1_02')[3]),
        'depth': 3
    },
    {
        'id': 'r1_03', 'asset': 'r1_03',
        't_start': 1.8, 't_dur': 1.8, 'type': 'outside_in_pen', # "أصله من الصين"
        'pos': (GET_BOX('r1_03')[0], GET_BOX('r1_03')[1]),
        'size': (GET_BOX('r1_03')[2], GET_BOX('r1_03')[3]),
        'depth': 5
    },
    {
        'id': 'r1_04', 'asset': 'r1_04',
        't_start': 2.6, 't_dur': 1.2, 'type': 'jelly_pop', # "عنب الثعلب الصيني"
        'pos': (GET_BOX('r1_04')[0], GET_BOX('r1_04')[1]),
        'size': (GET_BOX('r1_04')[2], GET_BOX('r1_04')[3]),
        'depth': 4
    },
    {
        'id': 'r1_05', 'asset': 'r1_05',
        't_start': 3.3, 't_dur': 1.2, 'type': 'jelly_pop',
        'pos': (GET_BOX('r1_05')[0], GET_BOX('r1_05')[1]),
        'size': (GET_BOX('r1_05')[2], GET_BOX('r1_05')[3]),
        'depth': 4
    },
    {
        'id': 'r1_06', 'asset': 'r1_06',
        't_start': 4.8, 't_dur': 1.4, 'type': 'slide_down', # "غذاء وحتى كدواء"
        'pos': (GET_BOX('r1_06')[0], GET_BOX('r1_06')[1]),
        'size': (GET_BOX('r1_06')[2], GET_BOX('r1_06')[3]),
        'depth': 4
    },

    # === ROW 2: New Zealand, Seeds & Size Evolution (6.5s - 11.8s) ===
    {
        'id': 'r2_01', 'asset': 'r2_01',
        't_start': 8.0, 't_dur': 1.8, 'type': 'outside_in_pen', # "المزارعين في نيوزيلندا"
        'pos': (GET_BOX('r2_01')[0], GET_BOX('r2_01')[1]),
        'size': (GET_BOX('r2_01')[2], GET_BOX('r2_01')[3]),
        'depth': 5
    },
    {
        'id': 'r2_02', 'asset': 'r2_02',
        't_start': 8.8, 't_dur': 1.0, 'type': 'slide_down', # خريطة نيوزيلندا
        'pos': (GET_BOX('r2_02')[0], GET_BOX('r2_02')[1]),
        'size': (GET_BOX('r2_02')[2], GET_BOX('r2_02')[3]),
        'depth': 2
    },
    {
        'id': 'r2_03', 'asset': 'r2_03',
        't_start': 9.3, 't_dur': 1.0, 'type': 'jelly_pop', # كيس البذور
        'pos': (GET_BOX('r2_03')[0], GET_BOX('r2_03')[1]),
        'size': (GET_BOX('r2_03')[2], GET_BOX('r2_03')[3]),
        'depth': 4
    },
    {
        'id': 'r2_04', 'asset': 'r2_04',
        't_start': 9.6, 't_dur': 1.0, 'type': 'jelly_pop', # اليد الممسكة بالبذور
        'pos': (GET_BOX('r2_04')[0], GET_BOX('r2_04')[1]),
        'size': (GET_BOX('r2_04')[2], GET_BOX('r2_04')[3]),
        'depth': 5
    },
    {
        'id': 'r2_05', 'asset': 'r2_05',
        't_start': 10.1, 't_dur': 0.8, 'type': 'organic_grow', # برعم الشتلة
        'pos': (GET_BOX('r2_05')[0], GET_BOX('r2_05')[1]),
        'size': (GET_BOX('r2_05')[2], GET_BOX('r2_05')[3]),
        'depth': 3
    },
    {
        'id': 'r2_06', 'asset': 'r2_06',
        't_start': 10.4, 't_dur': 0.8, 'type': 'organic_grow', # شتلة أكبر
        'pos': (GET_BOX('r2_06')[0], GET_BOX('r2_06')[1]),
        'size': (GET_BOX('r2_06')[2], GET_BOX('r2_06')[3]),
        'depth': 3
    },
    {
        'id': 'r2_07', 'asset': 'r2_07',
        't_start': 10.7, 't_dur': 1.2, 'type': 'organic_grow', # تعريشة الكيوي الكبيرة
        'pos': (GET_BOX('r2_07')[0], GET_BOX('r2_07')[1]),
        'size': (GET_BOX('r2_07')[2], GET_BOX('r2_07')[3]),
        'depth': 4
    },
    {
        'id': 'r2_08', 'asset': 'r2_08',
        't_start': 11.1, 't_dur': 1.4, 'type': 'jelly_pop', # تدرج الأحجام الـ 5
        'pos': (GET_BOX('r2_08')[0], GET_BOX('r2_08')[1]),
        'size': (GET_BOX('r2_08')[2], GET_BOX('r2_08')[3]),
        'depth': 4
    },

    # === ROW 3: Kiwi Bird, Global Export & Green Kiwis (11.8s - 17.0s) ===
    {
        'id': 'r3_01', 'asset': 'r3_01',
        't_start': 12.0, 't_dur': 1.4, 'type': 'jelly_pop', # طائر الكيوي والفاكهة
        'pos': (GET_BOX('r3_01')[0], GET_BOX('r3_01')[1]),
        'size': (GET_BOX('r3_01')[2], GET_BOX('r3_01')[3]),
        'depth': 5
    },
    {
        'id': 'r3_03', 'asset': 'r3_03',
        't_start': 13.5, 't_dur': 1.2, 'type': 'slide_down', # صندوق الشحن الخشبي
        'pos': (GET_BOX('r3_03')[0], GET_BOX('r3_03')[1]),
        'size': (GET_BOX('r3_03')[2], GET_BOX('r3_03')[3]),
        'depth': 4
    },
    {
        'id': 'r3_04', 'asset': 'r3_04',
        't_start': 14.2, 't_dur': 1.8, 'type': 'travel_slide', # سفينة الحاويات في المحيط
        'pos': (GET_BOX('r3_04')[0], GET_BOX('r3_04')[1]),
        'pos_start': (GET_BOX('r3_04')[0] - 120, GET_BOX('r3_04')[1]),
        'pos_end': (GET_BOX('r3_04')[0], GET_BOX('r3_04')[1]),
        'size': (GET_BOX('r3_04')[2], GET_BOX('r3_04')[3]),
        'depth': 6
    },
    {
        'id': 'r3_05', 'asset': 'r3_05',
        't_start': 15.2, 't_dur': 1.4, 'type': 'jelly_pop', # الكرة الأرضية والتسويق الدولي
        'pos': (GET_BOX('r3_05')[0], GET_BOX('r3_05')[1]),
        'size': (GET_BOX('r3_05')[2], GET_BOX('r3_05')[3]),
        'depth': 4
    },
    {
        'id': 'r3_06', 'asset': 'r3_06',
        't_start': 16.0, 't_dur': 1.2, 'type': 'jelly_pop', # الكيوي الأخضر الكلاسيكي
        'pos': (GET_BOX('r3_06')[0], GET_BOX('r3_06')[1]),
        'size': (GET_BOX('r3_06')[2], GET_BOX('r3_06')[3]),
        'depth': 5
    },

    # === ROW 4: Scientific Berry, Skin Fiber & Varieties (17.0s - 27.8s) ===
    {
        'id': 'r4_01', 'asset': 'r4_01',
        't_start': 18.0, 't_dur': 1.4, 'type': 'jelly_pop', # الكيوي مقارنة بالتوت
        'pos': (GET_BOX('r4_01')[0], GET_BOX('r4_01')[1]),
        'size': (GET_BOX('r4_01')[2], GET_BOX('r4_01')[3]),
        'depth': 4
    },
    {
        'id': 'r4_02', 'asset': 'r4_02',
        't_start': 20.5, 't_dur': 1.4, 'type': 'jelly_pop', # عدسة مكبرة على ألياف القشرة
        'pos': (GET_BOX('r4_02')[0], GET_BOX('r4_02')[1]),
        'size': (GET_BOX('r4_02')[2], GET_BOX('r4_02')[3]),
        'depth': 5
    },
    {
        'id': 'r4_03', 'asset': 'r4_03',
        't_start': 21.9, 't_dur': 1.2, 'type': 'slide_up', # ألياف الغذاء
        'pos': (GET_BOX('r4_03')[0], GET_BOX('r4_03')[1]),
        'size': (GET_BOX('r4_03')[2], GET_BOX('r4_03')[3]),
        'depth': 3
    },
    {
        'id': 'r4_04', 'asset': 'r4_04',
        't_start': 22.2, 't_dur': 1.2, 'type': 'pulse_pop', # الجهاز الهضمي
        'pos': (GET_BOX('r4_04')[0], GET_BOX('r4_04')[1]),
        'size': (GET_BOX('r4_04')[2], GET_BOX('r4_04')[3]),
        'depth': 4
    },
    {
        'id': 'r4_05', 'asset': 'r4_05',
        't_start': 23.6, 't_dur': 1.0, 'type': 'jelly_pop', # زوج الكيوي الأخضر
        'pos': (GET_BOX('r4_05')[0], GET_BOX('r4_05')[1]),
        'size': (GET_BOX('r4_05')[2], GET_BOX('r4_05')[3]),
        'depth': 4
    },
    {
        'id': 'r4_06', 'asset': 'r4_06',
        't_start': 25.3, 't_dur': 1.2, 'type': 'jelly_pop', # الكيوي الذهبي
        'pos': (GET_BOX('r4_06')[0], GET_BOX('r4_06')[1]),
        'size': (GET_BOX('r4_06')[2], GET_BOX('r4_06')[3]),
        'depth': 4
    },
    {
        'id': 'r4_07', 'asset': 'r4_07',
        't_start': 26.5, 't_dur': 1.2, 'type': 'jelly_pop', # الكيوي الأحمر النادر
        'pos': (GET_BOX('r4_07')[0], GET_BOX('r4_07')[1]),
        'size': (GET_BOX('r4_07')[2], GET_BOX('r4_07')[3]),
        'depth': 4
    },

    # === ROW 5: Nutrition, Protein Enzymes & Vitamin C (27.8s - 41.18s) ===
    {
        'id': 'r5_01', 'asset': 'r5_01',
        't_start': 28.0, 't_dur': 1.8, 'type': 'outside_in_pen', # شخص يتذوق الكيوي
        'pos': (GET_BOX('r5_01')[0], GET_BOX('r5_01')[1]),
        'size': (GET_BOX('r5_01')[2], GET_BOX('r5_01')[3]),
        'depth': 5
    },
    {
        'id': 'r5_02', 'asset': 'r5_02',
        't_start': 30.0, 't_dur': 1.2, 'type': 'slide_up', # كومة الأصناف الثلاثة
        'pos': (GET_BOX('r5_02')[0], GET_BOX('r5_02')[1]),
        'size': (GET_BOX('r5_02')[2], GET_BOX('r5_02')[3]),
        'depth': 4
    },
    {
        'id': 'r5_03', 'asset': 'r5_03',
        't_start': 31.3, 't_dur': 1.4, 'type': 'jelly_pop', # قطاع عرضي أحمر فني
        'pos': (GET_BOX('r5_03')[0], GET_BOX('r5_03')[1]),
        'size': (GET_BOX('r5_03')[2], GET_BOX('r5_03')[3]),
        'depth': 5
    },
    {
        'id': 'r5_04', 'asset': 'r5_04',
        't_start': 33.6, 't_dur': 1.8, 'type': 'jelly_pop', # تكسير الإنزيم للبروتين
        'pos': (GET_BOX('r5_04')[0], GET_BOX('r5_04')[1]),
        'size': (GET_BOX('r5_04')[2], GET_BOX('r5_04')[3]),
        'depth': 5
    },
    {
        'id': 'r5_07', 'asset': 'r5_07',
        't_start': 36.5, 't_dur': 1.5, 'type': 'golden_burst', # درع فيتامين C الذهبي المتوهج
        'pos': (GET_BOX('r5_07')[0], GET_BOX('r5_07')[1]),
        'size': (GET_BOX('r5_07')[2], GET_BOX('r5_07')[3]),
        'depth': 6
    },
    {
        'id': 'r5_08', 'asset': 'r5_08',
        't_start': 38.5, 't_dur': 1.8, 'type': 'jelly_pop', # التكوين الغذائي المتكامل
        'pos': (GET_BOX('r5_08')[0], GET_BOX('r5_08')[1]),
        'size': (GET_BOX('r5_08')[2], GET_BOX('r5_08')[3]),
        'depth': 6
    },
]

# Comfortable, Natural Whiteboard Camera Keyframes (Zoom 0.98, Zero Right-Side Clipping)
cam_keyframes = [
    # --- ROW 1 (Y ≈ 450) ---
    ( 0.0,   1100,  450, 0.98), # Left: Giant Kiwi & branch
    ( 2.5,   1100,  450, 0.98),
    ( 3.5,   1950,  450, 0.98), # Middle: Chinese sage & gooseberry plant
    ( 4.8,   3110,  450, 0.98), # Right: Gooseberry bowl & herbal medicine (+160px margin)
    ( 6.5,   3110,  450, 0.98),
    
    # --- ROW 2 (Y ≈ 1050) ---
    ( 7.0,   1100, 1050, 0.98), # Left: NZ farmer planting & NZ map
    ( 9.2,   1100, 1050, 0.98),
    (10.2,   1950, 1050, 0.98), # Middle: Seeds sack, seedlings, trellis pergola
    (11.0,   3110, 1050, 0.98), # Right: 5 Size evolution stages (+170px margin)
    (11.8,   3110, 1050, 0.98),
    
    # --- ROW 3 (Y ≈ 1550) ---
    (12.0,   1100, 1550, 0.98), # Left: Kiwi bird & kiwi fruit comparison
    (13.5,   1100, 1550, 0.98),
    (14.5,   1950, 1550, 0.98), # Middle: Shipping crate & ocean cargo ship
    (15.5,   3110, 1550, 0.98), # Right: Export globe & classic green kiwis (+180px margin)
    (17.0,   3110, 1550, 0.98),
    
    # --- ROW 4 (Y ≈ 1950) ---
    (17.2,   1100, 1950, 0.98), # Left: Berries comparison & skin microscope
    (21.5,   1100, 1950, 0.98),
    (23.0,   1950, 1950, 0.98), # Middle: Dietary fiber & digestive gut
    (25.0,   3110, 1950, 0.98), # Right: Green, Gold & Red varieties (+175px margin)
    (27.5,   3110, 1950, 0.98),
    
    # --- ROW 5 (Y ≈ 2380) ---
    (27.8,   1100, 2380, 0.98), # Left: Man tasting kiwi & trio heap
    (31.0,   1100, 2380, 0.98),
    (33.5,   1950, 2380, 0.98), # Middle: Red artistic slice & protein enzyme split
    (36.0,   3110, 2380, 0.98), # Right: Golden Vitamin C burst & complete nutrition (+165px margin)
    (39.5,   3110, 2380, 0.98),
    
    # --- THE GRAND OUTRO REVEAL (39.5s - 41.18s) ---
    (41.18,  2040, 1400, 0.44), # Panoramic pullout revealing all 5 completed Kiwi rows!
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
    
    src_x1 = max(0, -x1)
    src_y1 = max(0, -y1)
    src_x2 = tw - max(0, x2 - CANVAS_W)
    src_y2 = th - max(0, y2 - CANVAS_H)
    
    dst_x1 = max(0, x1)
    dst_y1 = max(0, y1)
    dst_x2 = min(CANVAS_W, x2)
    dst_y2 = min(CANVAS_H, y2)
    
    if dst_x2 <= dst_x1 or dst_y2 <= dst_y1:
        return
        
    crop_src = resized[src_y1:src_y2, src_x1:src_x2]
    alpha = (crop_src[:, :, 3].astype(np.float32) / 255.0) * alpha_mult
    alpha_3 = cv2.merge([alpha, alpha, alpha])
    
    canvas_roi = canvas[dst_y1:dst_y2, dst_x1:dst_x2].astype(np.float32)
    src_bgr = crop_src[:, :, :3].astype(np.float32)
    
    blended = src_bgr * alpha_3 + canvas_roi * (1.0 - alpha_3)
    canvas[dst_y1:dst_y2, dst_x1:dst_x2] = blended.astype(np.uint8)

def composite_hand_on_canvas_fast(frame, hand_bgra, tip_x, tip_y, screen_x, screen_y):
    hh, hw = hand_bgra.shape[:2]
    top = int(round(screen_y - tip_y))
    left = int(round(screen_x - tip_x))
    bottom = top + hh
    right = left + hw
    
    src_x1 = max(0, -left)
    src_y1 = max(0, -top)
    src_x2 = hw - max(0, right - WIDTH)
    src_y2 = hh - max(0, bottom - HEIGHT)
    
    dst_x1 = max(0, left)
    dst_y1 = max(0, top)
    dst_x2 = min(WIDTH, right)
    dst_y2 = min(HEIGHT, bottom)
    
    if dst_x2 <= dst_x1 or dst_y2 <= dst_y1:
        return frame
        
    hand_crop = hand_bgra[src_y1:src_y2, src_x1:src_x2]
    alpha = hand_crop[:, :, 3].astype(np.float32) / 255.0
    alpha_3 = cv2.merge([alpha, alpha, alpha])
    
    frame_roi = frame[dst_y1:dst_y2, dst_x1:dst_x2].astype(np.float32)
    hand_bgr = hand_crop[:, :, :3].astype(np.float32)
    
    blended = hand_bgr * alpha_3 + frame_roi * (1.0 - alpha_3)
    frame[dst_y1:dst_y2, dst_x1:dst_x2] = blended.astype(np.uint8)
    return frame

# 5. FFmpeg NVENC Video Render Pipe
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

ffmpeg_log = open("output_animations/ffmpeg_kiwi_render.log", "w", encoding="utf-8")
pipe = subprocess.Popen(nvenc_cmd, stdin=subprocess.PIPE, stdout=ffmpeg_log, stderr=ffmpeg_log)

print("Started FFmpeg NVENC render pipe.")
print(f"Rendering {TOTAL_FRAMES} frames ({DURATION_SEC:.2f}s) for Kiwi Masterpiece...")

# Base Canvas (Pure Clean White Studio Whiteboard)
base_canvas = np.full((CANVAS_H, CANVAS_W, 3), 255, dtype=np.uint8)

# RENDER LOOP
for frame_idx in range(TOTAL_FRAMES):
    time_s = frame_idx / float(FPS)
    canvas = base_canvas.copy()
    
    active_hand_screen_pt = None
    cam_x, cam_y, cam_zoom = get_camera_state(time_s)
    
    # 1. Render all elements that have started
    for elem in elements_staging:
        eid = elem['id']
        t_start = elem['t_start']
        t_dur = elem['t_dur']
        
        if time_s < t_start:
            continue
            
        elapsed = time_s - t_start
        prog = min(1.0, elapsed / t_dur)
        anim_type = elem['type']
        x, y = elem['pos'] if 'pos' in elem else elem['pos_end']
        w, h = elem['size']
        
        # Solid Pen Inking
        if anim_type == 'outside_in_pen':
            if eid in hero_cache and prog < 1.0:
                c_info = hero_cache[eid]
                f_idx = min(len(c_info['frames']) - 1, int(prog * len(c_info['frames'])))
                inked_sprite, (tip_ax, tip_ay) = c_info['frames'][f_idx]
                overlay_sprite(canvas, inked_sprite, x, y, w, h, alpha_mult=1.0)
                
                # World tip coord on canvas
                ow, oh = c_info['orig_size']
                tip_wx = x + (tip_ax / float(ow)) * w
                tip_wy = y + (tip_ay / float(oh)) * h
                
                # Project to screen
                sx = WIDTH / 2.0 + (tip_wx - cam_x) * cam_zoom
                sy = HEIGHT / 2.0 + (tip_wy - cam_y) * cam_zoom
                active_hand_screen_pt = (sx, sy)
            else:
                overlay_sprite(canvas, assets[elem['asset']], x, y, w, h, alpha_mult=1.0)
                
        # Jelly Pop
        elif anim_type == 'jelly_pop':
            if prog < 1.0:
                e_prog = ease_out_back(prog, s=1.8)
                scale = max(0.01, e_prog)
                alpha = min(1.0, prog / 0.3)
                overlay_sprite(canvas, assets[elem['asset']], x, y, w, h, alpha_mult=alpha, scale_x=scale, scale_y=scale)
            else:
                overlay_sprite(canvas, assets[elem['asset']], x, y, w, h, alpha_mult=1.0)
                
        # Organic Grow
        elif anim_type == 'organic_grow':
            if prog < 1.0:
                e_prog = ease_out_cubic(prog)
                scale_y = max(0.01, e_prog)
                scale_x = max(0.01, math.sqrt(e_prog))
                alpha = min(1.0, prog / 0.25)
                # Anchor at bottom
                grow_y = y + h * (1.0 - scale_y)
                overlay_sprite(canvas, assets[elem['asset']], x, grow_y, w, h, alpha_mult=alpha, scale_x=scale_x, scale_y=scale_y)
            else:
                overlay_sprite(canvas, assets[elem['asset']], x, y, w, h, alpha_mult=1.0)
                
        # Slide Down
        elif anim_type == 'slide_down':
            if prog < 1.0:
                e_prog = ease_out_cubic(prog)
                cur_y = (y - 80) + 80 * e_prog
                alpha = min(1.0, prog / 0.35)
                overlay_sprite(canvas, assets[elem['asset']], x, cur_y, w, h, alpha_mult=alpha)
            else:
                overlay_sprite(canvas, assets[elem['asset']], x, y, w, h, alpha_mult=1.0)
                
        # Slide Up
        elif anim_type == 'slide_up':
            if prog < 1.0:
                e_prog = ease_out_cubic(prog)
                cur_y = (y + 80) - 80 * e_prog
                alpha = min(1.0, prog / 0.35)
                overlay_sprite(canvas, assets[elem['asset']], x, cur_y, w, h, alpha_mult=alpha)
            else:
                overlay_sprite(canvas, assets[elem['asset']], x, y, w, h, alpha_mult=1.0)
                
        # Travel Slide
        elif anim_type == 'travel_slide':
            if prog < 1.0:
                e_prog = ease_in_out_quad(prog)
                cur_x = elem['pos_start'][0] + (elem['pos_end'][0] - elem['pos_start'][0]) * e_prog
                cur_y = elem['pos_start'][1]
                alpha = min(1.0, prog / 0.25)
                overlay_sprite(canvas, assets[elem['asset']], cur_x, cur_y, w, h, alpha_mult=alpha)
            else:
                overlay_sprite(canvas, assets[elem['asset']], elem['pos_end'][0], elem['pos_end'][1], w, h, alpha_mult=1.0)
                
        # Golden Burst / Pulse Pop
        elif anim_type == 'golden_burst' or anim_type == 'pulse_pop':
            if prog < 1.0:
                pulse = 1.0 + 0.12 * math.sin(prog * math.pi * 3) * (1.0 - prog)
                alpha = min(1.0, prog / 0.25)
                overlay_sprite(canvas, assets[elem['asset']], x, y, w, h, alpha_mult=alpha, scale_x=pulse, scale_y=pulse)
            else:
                overlay_sprite(canvas, assets[elem['asset']], x, y, w, h, alpha_mult=1.0)

    # Permanent Canvas Stamping
    for elem in elements_staging:
        if time_s >= elem['t_start'] + elem['t_dur']:
            if elem['id'] not in base_canvas:
                x, y = elem['pos'] if 'pos' in elem else elem['pos_end']
                w, h = elem['size']
                overlay_sprite(base_canvas, assets[elem['asset']], x, y, w, h, alpha_mult=1.0)

    # 3. Camera Transformation (Affine Matrix)
    M = np.array([
        [cam_zoom, 0.0, WIDTH / 2.0 - cam_x * cam_zoom],
        [0.0, cam_zoom, HEIGHT / 2.0 - cam_y * cam_zoom]
    ], dtype=np.float32)
    
    viewport_frame = cv2.warpAffine(
        canvas, M, (WIDTH, HEIGHT),
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
        flags=cv2.INTER_LINEAR
    )
    
    # 4. Composite Drawing Hand
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
audio_path = "project_content/audio/kiwi_master_ducked_audio.wav"
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

print("Multiplexing Kiwi video with STEREO 48kHz ducked audio track...")
mux_proc = subprocess.run(final_mux_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if mux_proc.returncode == 0:
    print(f"SUCCESS: Final Kiwi Masterpiece 2026 saved to: {out_mp4}")
else:
    print(f"Multiplexing error: {mux_proc.stderr.decode('utf-8', errors='ignore')}")
