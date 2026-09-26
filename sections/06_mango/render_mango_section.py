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
print("  🥭 MASTERPIECE WHITEBOARD ENGINE 2026 — SECTION 06: MANGO (CALIBRATED 57.0s) 🥭")
print("=====================================================================================")

WIDTH, HEIGHT = 1920, 1080
FPS = 30
DURATION_SEC = 57.00
TOTAL_FRAMES = int(round(DURATION_SEC * FPS))  # 1710 frames

CAM_ZOOM = 0.58
raw_video_mp4 = "sections/06_mango/raw_mango_cinematic_panned.mp4"
final_video_mp4 = "sections/06_mango/final_whiteboard_1080p.mp4"
master_audio_wav = "sections/06_mango/master_audio.wav"

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
assets_dir = "sections/06_mango/assets"
asset_files = [f for f in os.listdir(assets_dir) if f.endswith(".png")]
assets = {}
for af in asset_files:
    aid = os.path.splitext(af)[0]
    p = os.path.join(assets_dir, af)
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im is not None:
        assets[aid] = im

print(f"Loaded {len(assets)} clean Mango assets.")

# Pre-cache Concentric Inking Frames for Hero Assets
def build_solid_inking_cache(img_bgra, duration_sec, fps, ring_step=5):
    total_f = max(1, int(round(duration_sec * fps)))
    h, w = img_bgra.shape[:2]
    alpha = img_bgra[:, :, 3]
    binary_fg = (alpha > 20).astype(np.uint8)
    dist_map = cv2.distanceTransform(binary_fg, cv2.DIST_L2, 5)
    max_dist = np.max(dist_map)
    if max_dist <= 0:
        max_dist = 1.0

    cx, cy = w // 2, h // 2
    y_idx, x_idx = np.indices((h, w))
    ang = np.arctan2(y_idx - cy, x_idx - cx) + np.pi

    frames = []
    pen_tips = []
    pen_angles = []

    for f_idx in range(total_f):
        prog = (f_idx + 1) / float(total_f)
        cur_d_lim = max_dist * (1.0 - prog)
        ring_idx = int(prog * 16)
        ang_cutoff = ((prog * 16) - ring_idx) * 2.0 * np.pi

        in_revealed_rings = dist_map >= (cur_d_lim + ring_step)
        in_curr_ring = (dist_map >= cur_d_lim) & (dist_map < (cur_d_lim + ring_step))
        in_curr_wedge = ang <= ang_cutoff
        mask = in_revealed_rings | (in_curr_ring & in_curr_wedge)

        frame_bgra = img_bgra.copy()
        frame_bgra[:, :, 3] = np.where(mask, alpha, 0).astype(np.uint8)

        front_pts = np.argwhere((dist_map >= (cur_d_lim - 2)) & (dist_map <= (cur_d_lim + ring_step + 2)) & (np.abs(ang - ang_cutoff) < 0.25))
        if len(front_pts) > 0:
            tip_y, tip_x = front_pts[0]
            tip_pt = (int(tip_x), int(tip_y))
            rad = np.sqrt((tip_x - cx)**2 + (tip_y - cy)**2) + 0.001
            p_ang = math.degrees(math.atan2(tip_y - cy, tip_x - cx)) + 90.0
        else:
            tip_pt = (w // 2, h // 2)
            p_ang = 0.0

        frames.append((frame_bgra, tip_pt, p_ang))
    return frames

hero_cache = {}
hero_configs = [
    ("r1_01_hero_mango",                  0.0,  1.0),
    ("r2_01_ancient_scroll_manuscript",   18.4, 1.8),
    ("r3_01_portuguese_explorer_caravel", 33.8, 1.8),
    ("r4_05_mango_smoothie_dessert_bowl", 52.0, 1.8),
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
with open("sections/06_mango/placed_elements_layout.json", "r", encoding="utf-8") as f:
    layout_data = json.load(f)

placed_elements = layout_data['elements']
row_zones = layout_data['zones']

elem_coord = {}
for r_k, r_elems in placed_elements.items():
    for e in r_elems:
        elem_coord[e['aid']] = (e['x'], e['y'], e['w'], e['h'])

# 3. Elements Staging (Calibrated with user timestamps table and 57.0s duration)
elements_staging = [
    # === ROW 1: King of Fruits, Origins & Culture ===
    # p1 (0.0s - 1.0s): "المانجو."
    {
        'id': 'r1_01', 'asset': 'r1_01_hero_mango',
        't_start': 0.0, 't_dur': 1.0, 'type': 'outside_in_pen',
        'pos': (elem_coord['r1_01_hero_mango'][0], elem_coord['r1_01_hero_mango'][1]),
        'size': (elem_coord['r1_01_hero_mango'][2], elem_coord['r1_01_hero_mango'][3]),
        'depth': 5
    },
    # p2 (1.0s - 7.0s): "في جنوب آسيا يسمونها ملكة الفواكه، وهي من أشهر الفواكه في الهند وباكستان وغيرها."
    {
        'id': 'r1_02', 'asset': 'r1_02_crowned_king_mango',
        't_start': 1.2, 't_dur': 1.4, 'type': 'pulse_pop',
        'pos': (elem_coord['r1_02_crowned_king_mango'][0], elem_coord['r1_02_crowned_king_mango'][1]),
        'size': (elem_coord['r1_02_crowned_king_mango'][2], elem_coord['r1_02_crowned_king_mango'][3]),
        'depth': 4
    },
    {
        'id': 'r1_03', 'asset': 'r1_03_indian_man_taj_mahal',
        't_start': 3.6, 't_dur': 1.5, 'type': 'slide_down',
        'pos': (elem_coord['r1_03_indian_man_taj_mahal'][0], elem_coord['r1_03_indian_man_taj_mahal'][1]),
        'size': (elem_coord['r1_03_indian_man_taj_mahal'][2], elem_coord['r1_03_indian_man_taj_mahal'][3]),
        'depth': 4
    },
    # Pan 1A -> 1B at 7.0s - 7.8s
    # p3 (7.0s - 13.5s): "أصلها يرجع إلى مناطق من الهند وميانمار وزراعتها تمتد لآلاف السنين."
    {
        'id': 'r1_04', 'asset': 'r1_04_ancient_map_india_myanmar',
        't_start': 7.8, 't_dur': 1.6, 'type': 'slide_down',
        'pos': (elem_coord['r1_04_ancient_map_india_myanmar'][0], elem_coord['r1_04_ancient_map_india_myanmar'][1]),
        'size': (elem_coord['r1_04_ancient_map_india_myanmar'][2], elem_coord['r1_04_ancient_map_india_myanmar'][3]),
        'depth': 4
    },
    # p4 (13.5s - 18.0s): "ودخلت بقوة في التاريخ والثقافة والديانات الآسيوية."
    {
        'id': 'r1_05', 'asset': 'r1_05_buddha_temple_mango_tree',
        't_start': 13.6, 't_dur': 1.8, 'type': 'slide_up',
        'pos': (elem_coord['r1_05_buddha_temple_mango_tree'][0], elem_coord['r1_05_buddha_temple_mango_tree'][1]),
        'size': (elem_coord['r1_05_buddha_temple_mango_tree'][2], elem_coord['r1_05_buddha_temple_mango_tree'][3]),
        'depth': 4
    },

    # === ROW 2: Varieties & Textures ===
    # Transition Row 1 -> Row 2 at 17.6s - 18.4s
    # p5 (18.0s - 25.5s): "وفي الهند تحديدا عندك مئات الأنواع من المانجو وكل نوع تقريبا له شخصية مختلفة."
    {
        'id': 'r2_01', 'asset': 'r2_01_ancient_scroll_manuscript',
        't_start': 18.4, 't_dur': 1.8, 'type': 'outside_in_pen',
        'pos': (elem_coord['r2_01_ancient_scroll_manuscript'][0], elem_coord['r2_01_ancient_scroll_manuscript'][1]),
        'size': (elem_coord['r2_01_ancient_scroll_manuscript'][2], elem_coord['r2_01_ancient_scroll_manuscript'][3]),
        'depth': 5
    },
    {
        'id': 'r2_02', 'asset': 'r2_02_mango_varieties_grid',
        't_start': 20.5, 't_dur': 1.8, 'type': 'jelly_pop',
        'pos': (elem_coord['r2_02_mango_varieties_grid'][0], elem_coord['r2_02_mango_varieties_grid'][1]),
        'size': (elem_coord['r2_02_mango_varieties_grid'][2], elem_coord['r2_02_mango_varieties_grid'][3]),
        'depth': 4
    },
    # Pan 2A -> 2B at 25.0s - 25.8s
    # p6 (25.5s - 33.5s): "في أنواع قوامها كريمي وأنواع فيها ألياف أكثر وأنواع طعمها يوصل للحلاوة الشديدة."
    {
        'id': 'r2_03', 'asset': 'r2_03_creamy_texture_mango',
        't_start': 25.8, 't_dur': 1.4, 'type': 'jelly_pop',
        'pos': (elem_coord['r2_03_creamy_texture_mango'][0], elem_coord['r2_03_creamy_texture_mango'][1]),
        'size': (elem_coord['r2_03_creamy_texture_mango'][2], elem_coord['r2_03_creamy_texture_mango'][3]),
        'depth': 4
    },
    {
        'id': 'r2_04', 'asset': 'r2_04_fibrous_texture_mango',
        't_start': 27.8, 't_dur': 1.4, 'type': 'jelly_pop',
        'pos': (elem_coord['r2_04_fibrous_texture_mango'][0], elem_coord['r2_04_fibrous_texture_mango'][1]),
        'size': (elem_coord['r2_04_fibrous_texture_mango'][2], elem_coord['r2_04_fibrous_texture_mango'][3]),
        'depth': 4
    },
    {
        'id': 'r2_05', 'asset': 'r2_05_super_sweet_mango_sugar',
        't_start': 30.0, 't_dur': 1.4, 'type': 'pulse_pop',
        'pos': (elem_coord['r2_05_super_sweet_mango_sugar'][0], elem_coord['r2_05_super_sweet_mango_sugar'][1]),
        'size': (elem_coord['r2_05_super_sweet_mango_sugar'][2], elem_coord['r2_05_super_sweet_mango_sugar'][3]),
        'depth': 4
    },

    # === ROW 3: Portuguese Traders & Global Spread ===
    # Transition Row 2 -> Row 3 at 33.0s - 33.8s
    # p7 (33.5s - 40.0s): "والتجار البرتغاليون كان لهم دور مهم في نشر المانجو إلى أماكن خارج آسيا،"
    {
        'id': 'r3_01', 'asset': 'r3_01_portuguese_explorer_caravel',
        't_start': 33.8, 't_dur': 1.8, 'type': 'outside_in_pen',
        'pos': (elem_coord['r3_01_portuguese_explorer_caravel'][0], elem_coord['r3_01_portuguese_explorer_caravel'][1]),
        'size': (elem_coord['r3_01_portuguese_explorer_caravel'][2], elem_coord['r3_01_portuguese_explorer_caravel'][3]),
        'depth': 5
    },
    {
        'id': 'r3_02', 'asset': 'r3_02_world_map_trade_routes',
        't_start': 36.0, 't_dur': 1.8, 'type': 'slide_down',
        'pos': (elem_coord['r3_02_world_map_trade_routes'][0], elem_coord['r3_02_world_map_trade_routes'][1]),
        'size': (elem_coord['r3_02_world_map_trade_routes'][2], elem_coord['r3_02_world_map_trade_routes'][3]),
        'depth': 4
    },
    # Pan 3A -> 3B at 39.5s - 40.3s
    # p8 (40.0s - 45.0s): "حتى وصلت إلى أفريقيا والبرازيل ومناطق استوائية كثيرة."
    {
        'id': 'r3_03', 'asset': 'r3_03_tropical_harbor_mango_crates',
        't_start': 40.3, 't_dur': 1.5, 'type': 'slide_down',
        'pos': (elem_coord['r3_03_tropical_harbor_mango_crates'][0], elem_coord['r3_03_tropical_harbor_mango_crates'][1]),
        'size': (elem_coord['r3_03_tropical_harbor_mango_crates'][2], elem_coord['r3_03_tropical_harbor_mango_crates'][3]),
        'depth': 4
    },
    {
        'id': 'r3_04', 'asset': 'r3_04_globe_mango_distribution',
        't_start': 42.0, 't_dur': 1.5, 'type': 'pulse_pop',
        'pos': (elem_coord['r3_04_globe_mango_distribution'][0], elem_coord['r3_04_globe_mango_distribution'][1]),
        'size': (elem_coord['r3_04_globe_mango_distribution'][2], elem_coord['r3_04_globe_mango_distribution'][3]),
        'depth': 4
    },

    # === ROW 4: Nutrition, Botanical Splendor & Finale ===
    # Transition Row 3 -> Row 4 at 44.5s - 45.3s
    # p9 (45.0s - 49.5s): "والحلو في المانجو إنها مو بس متنوعة بشكل مرعب،"
    {
        'id': 'r4_02', 'asset': 'r4_02_mango_blossoms_inflorescence',
        't_start': 45.3, 't_dur': 1.4, 'type': 'slide_up',
        'pos': (elem_coord['r4_02_mango_blossoms_inflorescence'][0], elem_coord['r4_02_mango_blossoms_inflorescence'][1]),
        'size': (elem_coord['r4_02_mango_blossoms_inflorescence'][2], elem_coord['r4_02_mango_blossoms_inflorescence'][3]),
        'depth': 4
    },
    # p10 (49.5s - 55.0s): "هي أيضا غنية بفيتامين سي ومركبات نباتية مفيدة."
    {
        'id': 'r4_01', 'asset': 'r4_01_vitamin_c_shield_molecules',
        't_start': 46.8, 't_dur': 1.6, 'type': 'pulse_pop',
        'pos': (elem_coord['r4_01_vitamin_c_shield_molecules'][0], elem_coord['r4_01_vitamin_c_shield_molecules'][1]),
        'size': (elem_coord['r4_01_vitamin_c_shield_molecules'][2], elem_coord['r4_01_vitamin_c_shield_molecules'][3]),
        'depth': 4
    },
    # Pan 4A -> 4B at 49.0s - 49.8s
    # Finale: Halves, Trio, and Grand Smoothie Bowl Hold
    {
        'id': 'r4_03', 'asset': 'r4_03_cross_section_mango_halves',
        't_start': 49.8, 't_dur': 1.2, 'type': 'jelly_pop',
        'pos': (elem_coord['r4_03_cross_section_mango_halves'][0], elem_coord['r4_03_cross_section_mango_halves'][1]),
        'size': (elem_coord['r4_03_cross_section_mango_halves'][2], elem_coord['r4_03_cross_section_mango_halves'][3]),
        'depth': 4
    },
    {
        'id': 'r4_04', 'asset': 'r4_04_three_mangoes_trio',
        't_start': 50.8, 't_dur': 1.2, 'type': 'jelly_pop',
        'pos': (elem_coord['r4_04_three_mangoes_trio'][0], elem_coord['r4_04_three_mangoes_trio'][1]),
        'size': (elem_coord['r4_04_three_mangoes_trio'][2], elem_coord['r4_04_three_mangoes_trio'][3]),
        'depth': 4
    },
    {
        'id': 'r4_05', 'asset': 'r4_05_mango_smoothie_dessert_bowl',
        't_start': 52.0, 't_dur': 1.8, 'type': 'outside_in_pen',
        'pos': (elem_coord['r4_05_mango_smoothie_dessert_bowl'][0], elem_coord['r4_05_mango_smoothie_dessert_bowl'][1]),
        'size': (elem_coord['r4_05_mango_smoothie_dessert_bowl'][2], elem_coord['r4_05_mango_smoothie_dessert_bowl'][3]),
        'depth': 5
    },
]

# Sort elements by depth
elements_staging.sort(key=lambda e: e['depth'])

# 4. Camera Trajectory (4 Rows, 8 Zones, Ultra-Smooth S-Curves, Synced with Narration)
def smootherstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

def get_camera_state(t):
    # --- ROW 1 (0.0s - 17.6s, Y = 800) ---
    if t < 7.0:
        return (row_zones['1']['zone_A'][0], 800.0, CAM_ZOOM)
    elif t < 7.8:
        p = smootherstep((t - 7.0) / 0.8)
        cx = row_zones['1']['zone_A'][0] + (row_zones['1']['zone_B'][0] - row_zones['1']['zone_A'][0]) * p
        return (cx, 800.0, CAM_ZOOM)
    elif t < 17.6:
        return (row_zones['1']['zone_B'][0], 800.0, CAM_ZOOM)
        
    # Transition Row 1 -> Row 2 (17.6s - 18.4s, 0.8s smooth diagonal glide)
    elif t < 18.4:
        p = smootherstep((t - 17.6) / 0.8)
        cx = row_zones['1']['zone_B'][0] + (row_zones['2']['zone_A'][0] - row_zones['1']['zone_B'][0]) * p
        cy = 800.0 + (2800.0 - 800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 2 (18.4s - 33.0s, Y = 2800) ---
    elif t < 25.0:
        return (row_zones['2']['zone_A'][0], 2800.0, CAM_ZOOM)
    elif t < 25.8:
        p = smootherstep((t - 25.0) / 0.8)
        cx = row_zones['2']['zone_A'][0] + (row_zones['2']['zone_B'][0] - row_zones['2']['zone_A'][0]) * p
        return (cx, 2800.0, CAM_ZOOM)
    elif t < 33.0:
        return (row_zones['2']['zone_B'][0], 2800.0, CAM_ZOOM)

    # Transition Row 2 -> Row 3 (33.0s - 33.8s, 0.8s smooth diagonal glide)
    elif t < 33.8:
        p = smootherstep((t - 33.0) / 0.8)
        cx = row_zones['2']['zone_B'][0] + (row_zones['3']['zone_A'][0] - row_zones['2']['zone_B'][0]) * p
        cy = 2800.0 + (4800.0 - 2800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 3 (33.8s - 44.5s, Y = 4800) ---
    elif t < 39.5:
        return (row_zones['3']['zone_A'][0], 4800.0, CAM_ZOOM)
    elif t < 40.3:
        p = smootherstep((t - 39.5) / 0.8)
        cx = row_zones['3']['zone_A'][0] + (row_zones['3']['zone_B'][0] - row_zones['3']['zone_A'][0]) * p
        return (cx, 4800.0, CAM_ZOOM)
    elif t < 44.5:
        return (row_zones['3']['zone_B'][0], 4800.0, CAM_ZOOM)

    # Transition Row 3 -> Row 4 (44.5s - 45.3s, 0.8s smooth diagonal glide)
    elif t < 45.3:
        p = smootherstep((t - 44.5) / 0.8)
        cx = row_zones['3']['zone_B'][0] + (row_zones['4']['zone_A'][0] - row_zones['3']['zone_B'][0]) * p
        cy = 4800.0 + (6800.0 - 4800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 4 (45.3s - 57.0s, Y = 6800) ---
    elif t < 49.0:
        return (row_zones['4']['zone_A'][0], 6800.0, CAM_ZOOM)
    elif t < 49.8:
        p = smootherstep((t - 49.0) / 0.8)
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
    
    src_x1 = int(round((clip_x1 - x1) * sprite_bgra.shape[1] / float(scr_w)))
    src_y1 = int(round((clip_y1 - y1) * sprite_bgra.shape[0] / float(scr_h)))
    src_x2 = int(round((clip_x2 - x1) * sprite_bgra.shape[1] / float(scr_w)))
    src_y2 = int(round((clip_y2 - y1) * sprite_bgra.shape[0] / float(scr_h)))
    
    src_x2 = max(src_x1 + 1, min(sprite_bgra.shape[1], src_x2))
    src_y2 = max(src_y1 + 1, min(sprite_bgra.shape[0], src_y2))
    
    cropped_src = sprite_bgra[src_y1:src_y2, src_x1:src_x2]
    dst_w = clip_x2 - clip_x1
    dst_h = clip_y2 - clip_y1
    
    if dst_w <= 0 or dst_h <= 0:
        return
        
    resized_patch = cv2.resize(cropped_src, (dst_w, dst_h), interpolation=cv2.INTER_LINEAR)
    
    alpha = (resized_patch[:, :, 3].astype(np.float32) / 255.0) * alpha_mult
    alpha_3d = alpha[:, :, np.newaxis]
    
    roi = frame[clip_y1:clip_y2, clip_x1:clip_x2].astype(np.float32)
    fg = resized_patch[:, :, :3].astype(np.float32)
    
    blended = fg * alpha_3d + roi * (1.0 - alpha_3d)
    frame[clip_y1:clip_y2, clip_x1:clip_x2] = blended.astype(np.uint8)

# 6. Initialize Video Encoding Pipe
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
    "-pix_fmt", "yuv420p",
    raw_video_mp4
]

libx264_cmd = [
    "ffmpeg", "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-s", f"{WIDTH}x{HEIGHT}",
    "-pix_fmt", "bgr24",
    "-r", str(FPS),
    "-i", "-",
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-crf", "18",
    "-pix_fmt", "yuv420p",
    raw_video_mp4
]

ffmpeg_log = open("sections/06_mango/ffmpeg_mango_render.log", "w", encoding="utf-8")
try:
    pipe = subprocess.Popen(nvenc_cmd, stdin=subprocess.PIPE, stderr=ffmpeg_log)
    print("Using hardware-accelerated NVIDIA NVENC encoder (p7 quality).")
except Exception:
    pipe = subprocess.Popen(libx264_cmd, stdin=subprocess.PIPE, stderr=ffmpeg_log)
    print("Using CPU libx264 ultrafast encoder.")

t_render_start = time.time()
print(f"\nStarting video rendering pipeline with FFmpeg (Duration: {DURATION_SEC:.1f}s, {TOTAL_FRAMES} frames)...")

for frame_idx in range(TOTAL_FRAMES):
    time_s = frame_idx / float(FPS)
    cam_x, cam_y, cam_zoom = get_camera_state(time_s)
    
    # Whiteboard canvas background
    frame = np.full((HEIGHT, WIDTH, 3), 255, dtype=np.uint8)
    active_inking_hand = None
    
    for elem in elements_staging:
        t_start = elem['t_start']
        t_dur = elem['t_dur']
        aid = elem['asset']
        
        if time_s < t_start:
            continue
            
        wx, wy = elem['pos']
        ww, wh = elem['size']
        anim_type = elem['type']
        
        rel_t = time_s - t_start
        prog = min(1.0, rel_t / max(0.001, t_dur))
        
        # World to Screen Viewport Transform
        scr_x = int(round((wx - cam_x) * cam_zoom + (WIDTH / 2.0)))
        scr_y = int(round((wy - cam_y) * cam_zoom + (HEIGHT / 2.0)))
        scr_w = int(round(ww * cam_zoom))
        scr_h = int(round(wh * cam_zoom))
        
        if aid not in assets:
            continue
        base_asset = assets[aid]
        
        if anim_type == 'outside_in_pen':
            if prog < 1.0 and aid in hero_cache:
                cf = hero_cache[aid]['frames']
                sub_f_idx = min(len(cf) - 1, int(round(prog * (len(cf) - 1))))
                cur_spr, tip_pt, p_ang = cf[sub_f_idx]
                blend_sprite_screen(frame, cur_spr, scr_x, scr_y, scr_w, scr_h)
                
                # Screen pen tip position
                orig_w, orig_h = hero_cache[aid]['orig_size']
                tip_scr_x = scr_x + int(round(tip_pt[0] * (scr_w / float(orig_w))))
                tip_scr_y = scr_y + int(round(tip_pt[1] * (scr_h / float(orig_h))))
                active_inking_hand = (tip_scr_x, tip_scr_y, p_ang)
            else:
                blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h)
                
        elif anim_type == 'slide_down':
            if prog < 1.0:
                p = smootherstep(prog)
                cur_scr_y = scr_y - int(round(60 * (1.0 - p) * cam_zoom))
                blend_sprite_screen(frame, base_asset, scr_x, cur_scr_y, scr_w, scr_h, alpha_mult=p)
            else:
                blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h)
                
        elif anim_type == 'slide_up':
            if prog < 1.0:
                p = smootherstep(prog)
                cur_scr_y = scr_y + int(round(60 * (1.0 - p) * cam_zoom))
                blend_sprite_screen(frame, base_asset, scr_x, cur_scr_y, scr_w, scr_h, alpha_mult=p)
            else:
                blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h)
                
        elif anim_type == 'jelly_pop':
            if prog < 1.0:
                osc = math.sin(prog * math.pi * 3.0) * math.exp(-prog * 4.0)
                scale = (1.0 + 0.18 * osc) * prog
                cur_w = int(round(scr_w * scale))
                cur_h = int(round(scr_h * scale))
                cur_x = scr_x + (scr_w - cur_w) // 2
                cur_y = scr_y + (scr_h - cur_h) // 2
                blend_sprite_screen(frame, base_asset, cur_x, cur_y, cur_w, cur_h, alpha_mult=min(1.0, prog * 1.5))
            else:
                blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h)
                
        elif anim_type == 'pulse_pop':
            if prog < 1.0:
                pulse = 1.0 + 0.15 * math.sin(prog * math.pi * 2.0)
                cur_w = int(round(scr_w * pulse))
                cur_h = int(round(scr_h * pulse))
                cur_x = scr_x + (scr_w - cur_w) // 2
                cur_y = scr_y + (scr_h - cur_h) // 2
                blend_sprite_screen(frame, base_asset, cur_x, cur_y, cur_w, cur_h)
            else:
                blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h)
                
        else:
            blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h)
            
    # Composite Drawing Hand on top
    if active_inking_hand is not None and hand_bgra is not None:
        tx, ty, rot = active_inking_hand
        if -100 <= tx <= WIDTH + 100 and -100 <= ty <= HEIGHT + 100:
            frame = composite_hand_on_canvas_fast(frame, hand_bgra, HAND_TIP_X, HAND_TIP_Y, tx, ty)
        
    pipe.stdin.write(frame.tobytes())
    
    if (frame_idx + 1) % 300 == 0 or (frame_idx + 1) == TOTAL_FRAMES:
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
print("\n🎉 SECTION 06 MANGO VIDEO COMPLETE!")
print(f"Final video: {final_video_mp4}")
