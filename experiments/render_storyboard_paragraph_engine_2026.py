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
print("  🥝 MASTERPIECE WHITEBOARD ENGINE 2026 — DYNAMIC PARAGRAPH-BASED STAGING 🥝")
print("=====================================================================================")

WIDTH, HEIGHT = 1920, 1080
FPS = 30
DURATION_SEC = 58.24
TOTAL_FRAMES = int(round(DURATION_SEC * FPS)) # 1747 frames

SCALE = 2.5
PAD_X = 120
PAD_Y = 120

raw_video_mp4 = "output_animations/raw_kiwi_paragraph_video.mp4"
out_mp4 = "output_animations/kiwi_masterpiece_paragraph_engine_2026.mp4"
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
TARGET_HAND_H = 460
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

# Pre-cache Hero Inking for 58.24s Timeline
hero_cache = {}
hero_configs = [
    ("r1_01", 0.0,  1.0), # Giant Kiwi (takes 1.0s, hand finishes completely at 1.0s)
    ("r1_03", 1.5,  1.7), # Chinese Sage (takes 1.7s, hand finishes completely at 3.2s)
    ("r2_01", 10.6, 2.0), # NZ Farmer (takes 2.0s, hand finishes completely at 12.6s)
    ("r5_01", 48.2, 2.0), # Man Eating Kiwi (takes 2.0s, hand finishes completely at 50.2s)
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

def GET_BOX(aid):
    b = metadata[aid]['orig_box']
    return S_BOX(b[0], b[1], b[2], b[3])

# 3. Complete Staging for 35 Elements across 58.24s
# Grouped into 5 Paragraphs with Disciplined Sequential Inking (Hand finishes BEFORE next element appears!)
elements_staging = [
    # === PARAGRAPH 1: Origins, China, Gooseberry & Medicine (0.0s - 10.5s) ===
    # p1: "الكيوي" (0.0s - 1.0s) -> Hand draws giant kiwi alone until 1.0s
    {
        'id': 'r1_01', 'asset': 'r1_01',
        't_start': 0.0, 't_dur': 1.0, 'type': 'outside_in_pen',
        'pos': (GET_BOX('r1_01')[0], GET_BOX('r1_01')[1]),
        'size': (GET_BOX('r1_01')[2], GET_BOX('r1_01')[3]),
        'depth': 5
    },
    # Leaves appear ONLY AFTER hand is finished with giant kiwi at 1.0s!
    {
        'id': 'r1_02', 'asset': 'r1_02',
        't_start': 1.0, 't_dur': 0.5, 'type': 'organic_grow',
        'pos': (GET_BOX('r1_02')[0], GET_BOX('r1_02')[1]),
        'size': (GET_BOX('r1_02')[2], GET_BOX('r1_02')[3]),
        'depth': 3
    },
    # p2: "الكيوي أصلها الحقيقي من الصين..." (1.0s - 7.0s)
    # Hand draws Chinese Sage alone (1.5s - 3.2s)
    {
        'id': 'r1_03', 'asset': 'r1_03',
        't_start': 1.5, 't_dur': 1.7, 'type': 'outside_in_pen',
        'pos': (GET_BOX('r1_03')[0], GET_BOX('r1_03')[1]),
        'size': (GET_BOX('r1_03')[2], GET_BOX('r1_03')[3]),
        'depth': 4
    },
    # Gooseberry appears ONLY AFTER hand finishes with Sage at 3.2s!
    {
        'id': 'r1_04', 'asset': 'r1_04',
        't_start': 3.5, 't_dur': 0.8, 'type': 'organic_grow',
        'pos': (GET_BOX('r1_04')[0], GET_BOX('r1_04')[1]),
        'size': (GET_BOX('r1_04')[2], GET_BOX('r1_04')[3]),
        'depth': 3
    },
    # Bowl of wild berries
    {
        'id': 'r1_05', 'asset': 'r1_05',
        't_start': 4.5, 't_dur': 0.8, 'type': 'jelly_pop',
        'pos': (GET_BOX('r1_05')[0], GET_BOX('r1_05')[1]),
        'size': (GET_BOX('r1_05')[2], GET_BOX('r1_05')[3]),
        'depth': 4
    },
    # p3: "وكان يستخدم كغذاء وحتى كدواء" (7.0s - 10.5s)
    {
        'id': 'r1_06', 'asset': 'r1_06',
        't_start': 7.2, 't_dur': 1.0, 'type': 'slide_up',
        'pos': (GET_BOX('r1_06')[0], GET_BOX('r1_06')[1]),
        'size': (GET_BOX('r1_06')[2], GET_BOX('r1_06')[3]),
        'depth': 5
    },

    # === PARAGRAPH 2: New Zealand, Seeds & Size Evolution (10.5s - 18.0s) ===
    # p4: "لكن في أوائل القرن العشرين المزارعين في نيوزيلندا حصلوا على بذوره" (10.5s - 15.0s)
    # Hand draws NZ Farmer alone (10.6s - 12.6s)
    {
        'id': 'r2_01', 'asset': 'r2_01',
        't_start': 10.6, 't_dur': 2.0, 'type': 'outside_in_pen',
        'pos': (GET_BOX('r2_01')[0], GET_BOX('r2_01')[1]),
        'size': (GET_BOX('r2_01')[2], GET_BOX('r2_01')[3]),
        'depth': 5
    },
    # Elements appear ONLY AFTER hand finishes with Farmer at 12.6s!
    {
        'id': 'r2_02', 'asset': 'r2_02',
        't_start': 12.8, 't_dur': 0.8, 'type': 'jelly_pop', # NZ Map with flag
        'pos': (GET_BOX('r2_02')[0], GET_BOX('r2_02')[1]),
        'size': (GET_BOX('r2_02')[2], GET_BOX('r2_02')[3]),
        'depth': 2
    },
    {
        'id': 'r2_03', 'asset': 'r2_03',
        't_start': 13.5, 't_dur': 0.7, 'type': 'jelly_pop', # Seed sack
        'pos': (GET_BOX('r2_03')[0], GET_BOX('r2_03')[1]),
        'size': (GET_BOX('r2_03')[2], GET_BOX('r2_03')[3]),
        'depth': 4
    },
    {
        'id': 'r2_04', 'asset': 'r2_04',
        't_start': 14.0, 't_dur': 0.7, 'type': 'jelly_pop', # Hand with seeds
        'pos': (GET_BOX('r2_04')[0], GET_BOX('r2_04')[1]),
        'size': (GET_BOX('r2_04')[2], GET_BOX('r2_04')[3]),
        'depth': 5
    },
    # p5: "وبدأوا يطورون النوع اللي نعرفه اليوم" (15.0s - 18.0s)
    {
        'id': 'r2_05', 'asset': 'r2_05',
        't_start': 15.1, 't_dur': 0.6, 'type': 'organic_grow', # Sprout
        'pos': (GET_BOX('r2_05')[0], GET_BOX('r2_05')[1]),
        'size': (GET_BOX('r2_05')[2], GET_BOX('r2_05')[3]),
        'depth': 3
    },
    {
        'id': 'r2_06', 'asset': 'r2_06',
        't_start': 15.5, 't_dur': 0.6, 'type': 'organic_grow', # Seedling
        'pos': (GET_BOX('r2_06')[0], GET_BOX('r2_06')[1]),
        'size': (GET_BOX('r2_06')[2], GET_BOX('r2_06')[3]),
        'depth': 3
    },
    {
        'id': 'r2_07', 'asset': 'r2_07',
        't_start': 16.0, 't_dur': 0.9, 'type': 'organic_grow', # Pergola vine tree ("يطورون")
        'pos': (GET_BOX('r2_07')[0], GET_BOX('r2_07')[1]),
        'size': (GET_BOX('r2_07')[2], GET_BOX('r2_07')[3]),
        'depth': 4
    },
    {
        'id': 'r2_08', 'asset': 'r2_08',
        't_start': 16.8, 't_dur': 1.0, 'type': 'jelly_pop', # 5 Size progression cascade
        'pos': (GET_BOX('r2_08')[0], GET_BOX('r2_08')[1]),
        'size': (GET_BOX('r2_08')[2], GET_BOX('r2_08')[3]),
        'depth': 4
    },

    # === PARAGRAPH 3: Kiwi Bird & Global Shipping (18.0s - 25.5s) ===
    # p6: "وحتى غيروا اسمه إلى الكيوي نسبة لطائر الكيوي..." (18.0s - 25.5s)
    {
        'id': 'r3_01', 'asset': 'r3_01',
        't_start': 18.2, 't_dur': 1.2, 'type': 'jelly_pop', # Kiwi bird pops right at 18.2s!
        'pos': (GET_BOX('r3_01')[0], GET_BOX('r3_01')[1]),
        'size': (GET_BOX('r3_01')[2], GET_BOX('r3_01')[3]),
        'depth': 5
    },
    {
        'id': 'r3_02', 'asset': 'r3_02',
        't_start': 18.8, 't_dur': 0.6, 'type': 'jelly_pop', # Bird companion details
        'pos': (GET_BOX('r3_02')[0], GET_BOX('r3_02')[1]),
        'size': (GET_BOX('r3_02')[2], GET_BOX('r3_02')[3]),
        'depth': 4
    },
    {
        'id': 'r3_03', 'asset': 'r3_03',
        't_start': 20.0, 't_dur': 0.7, 'type': 'slide_down', # Wooden crate "تسويقه أسهل"
        'pos': (GET_BOX('r3_03')[0], GET_BOX('r3_03')[1]),
        'size': (GET_BOX('r3_03')[2], GET_BOX('r3_03')[3]),
        'depth': 4
    },
    {
        'id': 'r3_04', 'asset': 'r3_04',
        't_start': 20.8, 't_dur': 1.5, 'type': 'travel_slide', # Container ship "حول العالم"
        'pos': (GET_BOX('r3_04')[0], GET_BOX('r3_04')[1]),
        'pos_start': (GET_BOX('r3_04')[0] - 120, GET_BOX('r3_04')[1]),
        'pos_end': (GET_BOX('r3_04')[0], GET_BOX('r3_04')[1]),
        'size': (GET_BOX('r3_04')[2], GET_BOX('r3_04')[3]),
        'depth': 6
    },
    {
        'id': 'r3_05', 'asset': 'r3_05',
        't_start': 22.0, 't_dur': 0.9, 'type': 'jelly_pop', # Globe pops
        'pos': (GET_BOX('r3_05')[0], GET_BOX('r3_05')[1]),
        'size': (GET_BOX('r3_05')[2], GET_BOX('r3_05')[3]),
        'depth': 4
    },
    {
        'id': 'r3_06', 'asset': 'r3_06',
        't_start': 23.5, 't_dur': 0.9, 'type': 'jelly_pop', # Classic green kiwis
        'pos': (GET_BOX('r3_06')[0], GET_BOX('r3_06')[1]),
        'size': (GET_BOX('r3_06')[2], GET_BOX('r3_06')[3]),
        'depth': 5
    },

    # === PARAGRAPH 4: Scientific Berry, Skin Fiber & Varieties (25.5s - 48.0s) ===
    # p7: "والأغرب الكيوي علميا يعتبر نوعا من التوت" (25.5s - 29.5s)
    {
        'id': 'r4_01', 'asset': 'r4_01',
        't_start': 25.8, 't_dur': 1.0, 'type': 'jelly_pop', # Berry comparison
        'pos': (GET_BOX('r4_01')[0], GET_BOX('r4_01')[1]),
        'size': (GET_BOX('r4_01')[2], GET_BOX('r4_01')[3]),
        'depth': 4
    },
    # p8: "وحتى القشرة تقدر تاكلها لأنها مليانة ألياف" (29.5s - 33.5s)
    {
        'id': 'r4_02', 'asset': 'r4_02',
        't_start': 29.8, 't_dur': 1.0, 'type': 'jelly_pop', # Microscope on skin fibers
        'pos': (GET_BOX('r4_02')[0], GET_BOX('r4_02')[1]),
        'size': (GET_BOX('r4_02')[2], GET_BOX('r4_02')[3]),
        'depth': 5
    },
    {
        'id': 'r4_03', 'asset': 'r4_03',
        't_start': 31.0, 't_dur': 0.8, 'type': 'slide_up', # Fiber strands
        'pos': (GET_BOX('r4_03')[0], GET_BOX('r4_03')[1]),
        'size': (GET_BOX('r4_03')[2], GET_BOX('r4_03')[3]),
        'depth': 3
    },
    {
        'id': 'r4_04', 'asset': 'r4_04',
        't_start': 32.0, 't_dur': 0.8, 'type': 'pulse_pop', # Digestive Gut
        'pos': (GET_BOX('r4_04')[0], GET_BOX('r4_04')[1]),
        'size': (GET_BOX('r4_04')[2], GET_BOX('r4_04')[3]),
        'depth': 4
    },
    # p9: "وأغلب الناس يعرفون الكيوي الأخضر..." (33.5s - 40.0s)
    {
        'id': 'r4_05', 'asset': 'r4_05',
        't_start': 34.0, 't_dur': 1.0, 'type': 'jelly_pop', # Green kiwi pair
        'pos': (GET_BOX('r4_05')[0], GET_BOX('r4_05')[1]),
        'size': (GET_BOX('r4_05')[2], GET_BOX('r4_05')[3]),
        'depth': 4
    },
    # p10: "الذهبي قشرته أنعم وطعمه أحلى والأحمر نادر أكثر..." (40.0s - 48.0s)
    {
        'id': 'r4_06', 'asset': 'r4_06',
        't_start': 40.5, 't_dur': 1.0, 'type': 'jelly_pop', # Golden kiwi
        'pos': (GET_BOX('r4_06')[0], GET_BOX('r4_06')[1]),
        'size': (GET_BOX('r4_06')[2], GET_BOX('r4_06')[3]),
        'depth': 4
    },
    {
        'id': 'r4_07', 'asset': 'r4_07',
        't_start': 44.0, 't_dur': 1.0, 'type': 'jelly_pop', # Ruby red kiwi
        'pos': (GET_BOX('r4_07')[0], GET_BOX('r4_07')[1]),
        'size': (GET_BOX('r4_07')[2], GET_BOX('r4_07')[3]),
        'depth': 4
    },

    # === PARAGRAPH 5: Nutrition, Protein Enzymes & Vitamin C (48.0s - 58.5s) ===
    # p11: "والكيوي فيه إنزيم طبيعي يساعد على تكسير البروتين وفوق هذا غني بفيتامين سي" (48.0s - 54.0s)
    # Hand draws tasting man alone (48.2s - 50.2s)
    {
        'id': 'r5_01', 'asset': 'r5_01',
        't_start': 48.2, 't_dur': 2.0, 'type': 'outside_in_pen',
        'pos': (GET_BOX('r5_01')[0], GET_BOX('r5_01')[1]),
        'size': (GET_BOX('r5_01')[2], GET_BOX('r5_01')[3]),
        'depth': 5
    },
    # Elements appear ONLY AFTER hand is finished with tasting man at 50.2s!
    {
        'id': 'r5_02', 'asset': 'r5_02',
        't_start': 50.4, 't_dur': 0.7, 'type': 'slide_up', # Trio heap
        'pos': (GET_BOX('r5_02')[0], GET_BOX('r5_02')[1]),
        'size': (GET_BOX('r5_02')[2], GET_BOX('r5_02')[3]),
        'depth': 4
    },
    {
        'id': 'r5_03', 'asset': 'r5_03',
        't_start': 51.0, 't_dur': 0.7, 'type': 'jelly_pop', # Red slice
        'pos': (GET_BOX('r5_03')[0], GET_BOX('r5_03')[1]),
        'size': (GET_BOX('r5_03')[2], GET_BOX('r5_03')[3]),
        'depth': 5
    },
    {
        'id': 'r5_04', 'asset': 'r5_04',
        't_start': 51.8, 't_dur': 0.8, 'type': 'jelly_pop', # Protein enzymes
        'pos': (GET_BOX('r5_04')[0], GET_BOX('r5_04')[1]),
        'size': (GET_BOX('r5_04')[2], GET_BOX('r5_04')[3]),
        'depth': 4
    },
    {
        'id': 'r5_05', 'asset': 'r5_05',
        't_start': 52.2, 't_dur': 0.5, 'type': 'jelly_pop', # Enzyme companion
        'pos': (GET_BOX('r5_05')[0], GET_BOX('r5_05')[1]),
        'size': (GET_BOX('r5_05')[2], GET_BOX('r5_05')[3]),
        'depth': 4
    },
    {
        'id': 'r5_06', 'asset': 'r5_06',
        't_start': 52.4, 't_dur': 0.5, 'type': 'jelly_pop', # Enzyme companion
        'pos': (GET_BOX('r5_06')[0], GET_BOX('r5_06')[1]),
        'size': (GET_BOX('r5_06')[2], GET_BOX('r5_06')[3]),
        'depth': 4
    },
    {
        'id': 'r5_07', 'asset': 'r5_07',
        't_start': 52.8, 't_dur': 1.0, 'type': 'golden_burst', # Vitamin C burst
        'pos': (GET_BOX('r5_07')[0], GET_BOX('r5_07')[1]),
        'size': (GET_BOX('r5_07')[2], GET_BOX('r5_07')[3]),
        'depth': 6
    },
    # p12: "يعني مو بس شكله غريب حتى تركيبه الغذائي مختلف" (54.0s - 58.5s)
    {
        'id': 'r5_08', 'asset': 'r5_08',
        't_start': 54.5, 't_dur': 1.2, 'type': 'jelly_pop', # Complete nutrition finale
        'pos': (GET_BOX('r5_08')[0], GET_BOX('r5_08')[1]),
        'size': (GET_BOX('r5_08')[2], GET_BOX('r5_08')[3]),
        'depth': 5
    }
]

# Sort elements by depth
elements_staging.sort(key=lambda x: x.get('depth', 0))

# 4. Paragraph-Based Stage Camera Architecture (58.24s)
# Wide stable shot (Zoom = 0.49), center X = 2040.0
# The camera stays COMPLETELY STATIONARY throughout each paragraph!
# Only glides down vertically at paragraph boundaries.
# AT PARAGRAPH 5: IT FREEZES AND STAYS HELD STEADILY UNTIL 58.24s (NO OUTRO ZOOM-OUT!)
def get_camera_state(t):
    # Paragraph 1 (0.0s - 9.8s) -> Stationary at Y = 450
    if t < 9.8:
        return (2040.0, 450.0, 0.49)
    # Transition 1 -> 2 (9.8s - 10.5s, 0.7s smooth glide)
    elif t < 10.5:
        p = smootherstep((t - 9.8) / 0.7)
        cy = 450.0 + (1040.0 - 450.0) * p
        return (2040.0, cy, 0.49)
    # Paragraph 2 (10.5s - 17.6s) -> Stationary at Y = 1040
    elif t < 17.6:
        return (2040.0, 1040.0, 0.49)
    # Transition 2 -> 3 (17.6s - 18.2s, 0.6s smooth glide)
    elif t < 18.2:
        p = smootherstep((t - 17.6) / 0.6)
        cy = 1040.0 + (1530.0 - 1040.0) * p
        return (2040.0, cy, 0.49)
    # Paragraph 3 (18.2s - 24.8s) -> Stationary at Y = 1530
    elif t < 24.8:
        return (2040.0, 1530.0, 0.49)
    # Transition 3 -> 4 (24.8s - 25.5s, 0.7s smooth glide)
    elif t < 25.5:
        p = smootherstep((t - 24.8) / 0.7)
        cy = 1530.0 + (1960.0 - 1530.0) * p
        return (2040.0, cy, 0.49)
    # Paragraph 4 (25.5s - 47.4s) -> Stationary at Y = 1960
    elif t < 47.4:
        return (2040.0, 1960.0, 0.49)
    # Transition 4 -> 5 (47.4s - 48.1s, 0.7s smooth glide)
    elif t < 48.1:
        p = smootherstep((t - 47.4) / 0.7)
        cy = 1960.0 + (2390.0 - 1960.0) * p
        return (2040.0, cy, 0.49)
    # Paragraph 5 (48.1s - 58.24s) -> COMPLETELY FROZEN & STATIONARY ON FINAL SCENE UNTIL END!
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

ffmpeg_log = open("output_animations/ffmpeg_kiwi_paragraph_render.log", "w", encoding="utf-8")
pipe = subprocess.Popen(nvenc_cmd, stdin=subprocess.PIPE, stdout=ffmpeg_log, stderr=ffmpeg_log)

print(f"Started Fast NVENC render pipe for Paragraph Engine.")
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
            if eid in hero_cache and prog < 1.0:
                c_info = hero_cache[eid]
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

# 7. Multiplex with Crisp Stereo 48kHz Ducked Audio (58.24s Sweetspot Voiceover)
audio_path = "project_content/audio/kiwi_master_ducked_audio_sweetspot.wav"
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

print("Multiplexing Kiwi video with STEREO 48kHz sweetspot ducked audio track...")
mux_proc = subprocess.run(final_mux_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if mux_proc.returncode == 0:
    print(f"SUCCESS: Final Paragraph-Engine Kiwi Masterpiece saved to: {out_mp4}")
else:
    print(f"Multiplexing error: {mux_proc.stderr.decode('utf-8', errors='ignore')}")
