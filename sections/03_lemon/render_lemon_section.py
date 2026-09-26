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
print("  🍋 MASTERPIECE WHITEBOARD ENGINE 2026 — SECTION 03: LEMON (STANDARD SPACING) 🍋")
print("=====================================================================================")

WIDTH, HEIGHT = 1920, 1080
FPS = 30
DURATION_SEC = 63.96
TOTAL_FRAMES = int(round(DURATION_SEC * FPS)) # 1919 frames

CAM_ZOOM = 0.58
raw_video_mp4 = "sections/03_lemon/raw_lemon_cinematic_panned.mp4"
final_video_mp4 = "sections/03_lemon/final_whiteboard_1080p.mp4"
master_audio_wav = "sections/03_lemon/master_audio.wav"

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

# 2. Load Clean Assets
assets_dir = "sections/03_lemon/assets"
asset_files = [f for f in os.listdir(assets_dir) if f.endswith(".png")]
assets = {}
for af in asset_files:
    aid = os.path.splitext(af)[0]
    p = os.path.join(assets_dir, af)
    img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if img is not None:
        assets[aid] = img
print(f"Loaded {len(assets)} clean Lemon assets.")

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

# Pre-cache Hero Inking for Lemon (Strict Clean-Hand Inking Discipline)
hero_cache = {}
hero_configs = [
    ("r1_01_hero_lemon", 0.0,  1.2),  # Hand draws hero lemon alone, finishes at 1.2s before r1_02 at 1.6s
    ("r1_04_dr_james_lind", 8.2, 2.4),
    ("r2_01_naval_scurvy_ship", 24.0, 2.4),
    ("r2_05_lush_lemon_tree", 37.4, 2.4),
    ("r3_04_vitamin_c_glowing_emblem", 54.5, 2.0),
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
with open("sections/03_lemon/placed_elements_layout.json", "r", encoding="utf-8") as f:
    layout_data = json.load(f)

placed_elements = layout_data['elements']
row_zones = layout_data['zones']

elem_coord = {}
for r_k, r_elems in placed_elements.items():
    for e in r_elems:
        elem_coord[e['aid']] = (e['x'], e['y'], e['w'], e['h'])

# 3. Complete Staging for 18 Elements across 63.96s
elements_staging = [
    # === ROW 1: Origins, Hybrid, Dr. James Lind & Scurvy Cure (0.0s - 23.4s) ===
    # p1: "الليمون." (0.0s - 1.2s) -> Hero lemon drawn alone by hand
    {
        'id': 'r1_01', 'asset': 'r1_01_hero_lemon',
        't_start': 0.0, 't_dur': 1.2, 'type': 'outside_in_pen',
        'pos': (elem_coord['r1_01_hero_lemon'][0], elem_coord['r1_01_hero_lemon'][1]),
        'size': (elem_coord['r1_01_hero_lemon'][2], elem_coord['r1_01_hero_lemon'][3]),
        'depth': 5
    },
    # p2: "الليمون نفسه يعتبر هجين، ويرجح أن أصله يرجع إلى شمال شرق الهند." (1.6s - 7.4s)
    {
        'id': 'r1_02', 'asset': 'r1_02_hybrid_citrus_dna',
        't_start': 1.6, 't_dur': 1.5, 'type': 'jelly_pop',
        'pos': (elem_coord['r1_02_hybrid_citrus_dna'][0], elem_coord['r1_02_hybrid_citrus_dna'][1]),
        'size': (elem_coord['r1_02_hybrid_citrus_dna'][2], elem_coord['r1_02_hybrid_citrus_dna'][3]),
        'depth': 3
    },
    {
        'id': 'r1_03', 'asset': 'r1_03_india_asia_map',
        't_start': 4.5, 't_dur': 1.6, 'type': 'slide_down',
        'pos': (elem_coord['r1_03_india_asia_map'][0], elem_coord['r1_03_india_asia_map'][1]),
        'size': (elem_coord['r1_03_india_asia_map'][2], elem_coord['r1_03_india_asia_map'][3]),
        'depth': 2
    },
    # p3: "لكن أشهر شيء في تاريخه صار سنة 1747، لما الدكتور جيمس ليند..." (7.85s - 23.4s)
    # [Camera smoothly pans from Zone 1A to Zone 1B at 7.4s - 8.2s]
    {
        'id': 'r1_04', 'asset': 'r1_04_dr_james_lind',
        't_start': 8.2, 't_dur': 2.4, 'type': 'outside_in_pen',
        'pos': (elem_coord['r1_04_dr_james_lind'][0], elem_coord['r1_04_dr_james_lind'][1]),
        'size': (elem_coord['r1_04_dr_james_lind'][2], elem_coord['r1_04_dr_james_lind'][3]),
        'depth': 5
    },
    {
        'id': 'r1_05', 'asset': 'r1_05_scurvy_clipboard_cure',
        't_start': 14.5, 't_dur': 1.8, 'type': 'jelly_pop',
        'pos': (elem_coord['r1_05_scurvy_clipboard_cure'][0], elem_coord['r1_05_scurvy_clipboard_cure'][1]),
        'size': (elem_coord['r1_05_scurvy_clipboard_cure'][2], elem_coord['r1_05_scurvy_clipboard_cure'][3]),
        'depth': 4
    },

    # === ROW 2: Naval Scurvy, Secret Ink, Year-Round Tree (23.4s - 43.2s) ===
    # Transition Row 1 -> Row 2 at 23.4s - 24.2s
    # p4: "والمرض هذا كان يضرب البحارة بشكل خطير جداً." (24.0s - 27.4s)
    {
        'id': 'r2_01', 'asset': 'r2_01_naval_scurvy_ship',
        't_start': 24.0, 't_dur': 2.4, 'type': 'outside_in_pen',
        'pos': (elem_coord['r2_01_naval_scurvy_ship'][0], elem_coord['r2_01_naval_scurvy_ship'][1]),
        'size': (elem_coord['r2_01_naval_scurvy_ship'][2], elem_coord['r2_01_naval_scurvy_ship'][3]),
        'depth': 5
    },
    # p5: "والأغرب من كذا، إن الليمون استُخدم كحبر سري..." (28.2s - 36.5s)
    {
        'id': 'r2_02', 'asset': 'r2_02_lemon_squeezing_ink',
        't_start': 28.2, 't_dur': 1.4, 'type': 'slide_down',
        'pos': (elem_coord['r2_02_lemon_squeezing_ink'][0], elem_coord['r2_02_lemon_squeezing_ink'][1]),
        'size': (elem_coord['r2_02_lemon_squeezing_ink'][2], elem_coord['r2_02_lemon_squeezing_ink'][3]),
        'depth': 4
    },
    {
        'id': 'r2_03', 'asset': 'r2_03_red_arrow',
        't_start': 31.5, 't_dur': 0.6, 'type': 'jelly_pop',
        'pos': (elem_coord['r2_03_red_arrow'][0], elem_coord['r2_03_red_arrow'][1]),
        'size': (elem_coord['r2_03_red_arrow'][2], elem_coord['r2_03_red_arrow'][3]),
        'depth': 3
    },
    {
        'id': 'r2_04', 'asset': 'r2_04_heat_lamp_reveal_writing',
        't_start': 32.5, 't_dur': 1.4, 'type': 'slide_down',
        'pos': (elem_coord['r2_04_heat_lamp_reveal_writing'][0], elem_coord['r2_04_heat_lamp_reveal_writing'][1]),
        'size': (elem_coord['r2_04_heat_lamp_reveal_writing'][2], elem_coord['r2_04_heat_lamp_reveal_writing'][3]),
        'depth': 4
    },
    # p6: "وشجرة الليمون نفسها مميزة، لأنها تقدر تنتج الثمار..." (37.1s - 43.15s)
    # [Camera smoothly pans from Zone 2A to Zone 2B at 36.6s - 37.4s]
    {
        'id': 'r2_05', 'asset': 'r2_05_lush_lemon_tree',
        't_start': 37.4, 't_dur': 2.4, 'type': 'outside_in_pen',
        'pos': (elem_coord['r2_05_lush_lemon_tree'][0], elem_coord['r2_05_lush_lemon_tree'][1]),
        'size': (elem_coord['r2_05_lush_lemon_tree'][2], elem_coord['r2_05_lush_lemon_tree'][3]),
        'depth': 5
    },
    {
        'id': 'r2_06', 'asset': 'r2_06_year_round_production_cycle',
        't_start': 40.2, 't_dur': 1.8, 'type': 'organic_grow',
        'pos': (elem_coord['r2_06_year_round_production_cycle'][0], elem_coord['r2_06_year_round_production_cycle'][1]),
        'size': (elem_coord['r2_06_year_round_production_cycle'][2], elem_coord['r2_06_year_round_production_cycle'][3]),
        'depth': 4
    },

    # === ROW 3: Detox Myth vs Truth, Vitamin C, Citric Acid, Kidney Stones (43.2s - 63.96s) ===
    # Transition Row 2 -> Row 3 at 43.2s - 44.0s
    # p7: "لكن فيه معلومة مشهورة عن الليمون لازم نفرق فيها بين الفائدة المؤكدة..." (43.7s - 53.65s)
    {
        'id': 'r3_01', 'asset': 'r3_01_glass_lemon_water_liver_check',
        't_start': 44.0, 't_dur': 1.5, 'type': 'slide_down',
        'pos': (elem_coord['r3_01_glass_lemon_water_liver_check'][0], elem_coord['r3_01_glass_lemon_water_liver_check'][1]),
        'size': (elem_coord['r3_01_glass_lemon_water_liver_check'][2], elem_coord['r3_01_glass_lemon_water_liver_check'][3]),
        'depth': 4
    },
    {
        'id': 'r3_02', 'asset': 'r3_02_divider_line',
        't_start': 47.0, 't_dur': 0.5, 'type': 'slide_down',
        'pos': (elem_coord['r3_02_divider_line'][0], elem_coord['r3_02_divider_line'][1]),
        'size': (elem_coord['r3_02_divider_line'][2], elem_coord['r3_02_divider_line'][3]),
        'depth': 2
    },
    {
        'id': 'r3_03', 'asset': 'r3_03_cloudy_water_toxic_liver_cross',
        't_start': 47.5, 't_dur': 1.5, 'type': 'jelly_pop',
        'pos': (elem_coord['r3_03_cloudy_water_toxic_liver_cross'][0], elem_coord['r3_03_cloudy_water_toxic_liver_cross'][1]),
        'size': (elem_coord['r3_03_cloudy_water_toxic_liver_cross'][2], elem_coord['r3_03_cloudy_water_toxic_liver_cross'][3]),
        'depth': 4
    },
    # p8: "اللي نعرفه بشكل أوضح إن الليمون غني بفيتامين سي..." (54.15s - 63.96s)
    # [Camera smoothly pans from Zone 3A to Zone 3B at 53.7s - 54.5s]
    {
        'id': 'r3_04', 'asset': 'r3_04_vitamin_c_glowing_emblem',
        't_start': 54.5, 't_dur': 2.0, 'type': 'outside_in_pen',
        'pos': (elem_coord['r3_04_vitamin_c_glowing_emblem'][0], elem_coord['r3_04_vitamin_c_glowing_emblem'][1]),
        'size': (elem_coord['r3_04_vitamin_c_glowing_emblem'][2], elem_coord['r3_04_vitamin_c_glowing_emblem'][3]),
        'depth': 5
    },
    {
        'id': 'r3_05', 'asset': 'r3_05_citric_acid_molecule',
        't_start': 56.8, 't_dur': 1.2, 'type': 'pulse_pop',
        'pos': (elem_coord['r3_05_citric_acid_molecule'][0], elem_coord['r3_05_citric_acid_molecule'][1]),
        'size': (elem_coord['r3_05_citric_acid_molecule'][2], elem_coord['r3_05_citric_acid_molecule'][3]),
        'depth': 4
    },
    {
        'id': 'r3_06', 'asset': 'r3_06_kidney_stones_anatomy',
        't_start': 58.5, 't_dur': 1.4, 'type': 'slide_down',
        'pos': (elem_coord['r3_06_kidney_stones_anatomy'][0], elem_coord['r3_06_kidney_stones_anatomy'][1]),
        'size': (elem_coord['r3_06_kidney_stones_anatomy'][2], elem_coord['r3_06_kidney_stones_anatomy'][3]),
        'depth': 4
    },
    {
        'id': 'r3_07', 'asset': 'r3_07_stone_reduction_arrow',
        't_start': 60.5, 't_dur': 1.5, 'type': 'jelly_pop',
        'pos': (elem_coord['r3_07_stone_reduction_arrow'][0], elem_coord['r3_07_stone_reduction_arrow'][1]),
        'size': (elem_coord['r3_07_stone_reduction_arrow'][2], elem_coord['r3_07_stone_reduction_arrow'][3]),
        'depth': 5
    }
]

elements_staging.sort(key=lambda x: x.get('depth', 0))

# 4. Camera Trajectory for Lemon (100% Isolated 2-Stage Glide)
def get_camera_state(t):
    # --- ROW 1 (0.0s - 23.4s, Y = 800) ---
    if t < 7.4:
        return (row_zones['1']['zone_A'][0], 800.0, CAM_ZOOM)
    elif t < 8.2:
        p = smootherstep((t - 7.4) / 0.8)
        cx = row_zones['1']['zone_A'][0] + (row_zones['1']['zone_B'][0] - row_zones['1']['zone_A'][0]) * p
        return (cx, 800.0, CAM_ZOOM)
    elif t < 23.4:
        return (row_zones['1']['zone_B'][0], 800.0, CAM_ZOOM)
        
    # Transition Row 1 -> Row 2 (23.4s - 24.2s, 0.8s smooth glide)
    elif t < 24.2:
        p = smootherstep((t - 23.4) / 0.8)
        cx = row_zones['1']['zone_B'][0] + (row_zones['2']['zone_A'][0] - row_zones['1']['zone_B'][0]) * p
        cy = 800.0 + (2800.0 - 800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 2 (24.2s - 43.2s, Y = 2800) ---
    elif t < 36.6:
        return (row_zones['2']['zone_A'][0], 2800.0, CAM_ZOOM)
    elif t < 37.4:
        p = smootherstep((t - 36.6) / 0.8)
        cx = row_zones['2']['zone_A'][0] + (row_zones['2']['zone_B'][0] - row_zones['2']['zone_A'][0]) * p
        return (cx, 2800.0, CAM_ZOOM)
    elif t < 43.2:
        return (row_zones['2']['zone_B'][0], 2800.0, CAM_ZOOM)

    # Transition Row 2 -> Row 3 (43.2s - 44.0s, 0.8s smooth glide)
    elif t < 44.0:
        p = smootherstep((t - 43.2) / 0.8)
        cx = row_zones['2']['zone_B'][0] + (row_zones['3']['zone_A'][0] - row_zones['2']['zone_B'][0]) * p
        cy = 2800.0 + (4800.0 - 2800.0) * p
        return (cx, cy, CAM_ZOOM)

    # --- ROW 3 (44.0s - 63.96s, Y = 4800) ---
    elif t < 53.7:
        return (row_zones['3']['zone_A'][0], 4800.0, CAM_ZOOM)
    elif t < 54.5:
        p = smootherstep((t - 53.7) / 0.8)
        cx = row_zones['3']['zone_A'][0] + (row_zones['3']['zone_B'][0] - row_zones['3']['zone_A'][0]) * p
        return (cx, 4800.0, CAM_ZOOM)
    else:
        # Finale: Freeze & hold steadily on Zone 3B until end (ZERO OUTRO ZOOM-OUT!)
        return (row_zones['3']['zone_B'][0], 4800.0, CAM_ZOOM)

# 5. Direct Viewport Blending Function
def blend_sprite_screen(frame, sprite_bgra, scr_x, scr_y, scr_w, scr_h, alpha_mult=1.0):
    if scr_w <= 2 or scr_h <= 2:
        return
        
    x1 = scr_x
    y1 = scr_y
    x2 = scr_x + scr_w
    y2 = scr_y + scr_h
    
    # Check if completely outside viewport
    if x2 <= 0 or x1 >= WIDTH or y2 <= 0 or y1 >= HEIGHT:
        return
        
    # Clipping against screen bounds
    clip_x1 = max(0, x1)
    clip_y1 = max(0, y1)
    clip_x2 = min(WIDTH, x2)
    clip_y2 = min(HEIGHT, y2)
    
    # Source mapping
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
ffmpeg_log = open("sections/03_lemon/ffmpeg_lemon_render.log", "w")
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
    print(f"--- SUCCESS: Lemon Masterpiece Video created ({os.path.getsize(final_video_mp4) / (1024*1024):.2f} MB) ---")
