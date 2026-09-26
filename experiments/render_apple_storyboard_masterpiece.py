"""
Apple Storyboard Masterpiece Renderer (2026 Edition)
- 26 Exact Organic Contour Assets (Zero Rectangles / Zero Boxes)
- 5 Cinematic Narrative Acts (Left-to-Right Flow)
- Spatial Depth Layering (Background Maps/Mountains, Foreground Characters, Dynamic Travel)
- 2026 Motion Effects: Pen Inking with Hand Sprite, Elastic Squash & Stretch, Velocity Slides, Organic Tree Growth, Juice Splash Burst
- Cinematic Gliding Camera with Grand Outro Zoom-out Reveal
- High-Performance NVENC H.264 Video Rendering & Audio Multiplexing
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

# Configuration Constants
WIDTH, HEIGHT = 1920, 1080
FPS = 30
TOTAL_DURATION = 60.88
TOTAL_FRAMES = int(TOTAL_DURATION * FPS) # 1826 frames

CANVAS_W, CANVAS_H = 3400, 2000

HAND_PATH = r"E:\image_to_animate\kivy\data\images\drawing-hand.png"
HAND_MASK_PATH = r"E:\image_to_animate\kivy\data\images\hand-mask.png"
PEN_TIP_X = 62
PEN_TIP_Y = 40

# Easing Functions
def smootherstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

def ease_out_back(t: float, overshoot: float = 1.35) -> float:
    t = max(0.0, min(1.0, t)) - 1.0
    return t * t * ((overshoot + 1.0) * t + overshoot) + 1.0

def ease_out_elastic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    if t <= 0.0: return 0.0
    if t >= 1.0: return 1.0
    return math.pow(2, -10 * t) * math.sin((t - 0.075) * (2 * math.pi) / 0.3) + 1.0

def get_jelly_scales(t: float) -> tuple:
    t = max(0.0, min(1.0, t))
    if t >= 1.0: return 1.0, 1.0
    if t <= 0.0: return 0.0, 0.0
    decay = math.exp(-t * 5.5)
    osc = decay * math.cos(18.0 * t)
    base = 1.0 - math.pow(1.0 - t, 4)
    return max(0.01, base + 0.35 * osc), max(0.01, base - 0.28 * osc)

# Load Hand Asset
hand_bgra = load_hand_asset_bgra(HAND_PATH, HAND_MASK_PATH)
if hand_bgra is not None:
    # Resize hand slightly for natural 1080p scale
    hw, hh = hand_bgra.shape[1], hand_bgra.shape[0]
    hand_bgra = cv2.resize(hand_bgra, (int(hw * 0.75), int(hh * 0.75)), interpolation=cv2.INTER_AREA)
    pen_x_scaled = int(PEN_TIP_X * 0.75)
    pen_y_scaled = int(PEN_TIP_Y * 0.75)
else:
    pen_x_scaled, pen_y_scaled = 45, 30

# Load All 26 Assets
assets_dir = "experiments/exact_contour_assets"
asset_names = [
    "01_giant_red_apple", "02_wild_sour_apple", "03_wild_branch", "04_apple_blossom_flower",
    "05_blooming_apple_tree", "06_snowy_mountains_winter", "07_central_asia_map",
    "08_roman_soldier", "09_horse_cart_apples", "10_europe_map_arrow",
    "11_farmer_planting", "12_tree_growing_stages",
    "13_evolution_scale", "14_hand_picking_apple", "15_apple_varieties_rainbow",
    "16_seedling_cycle", "17_harvest_crate", "18_sliced_apples_juice",
    "19_farmer_inspecting_apple", "20_quality_checkboxes",
    "21_digestive_health_gut", "22_vitamins_bubbles", "23_heart_health_pulse",
    "24_wheat_fiber_apples", "25_apple_harvest_pile", "26_refrigerator_modern_apples"
]

assets = {}
for name in asset_names:
    path = os.path.join(assets_dir, f"{name}.png")
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None:
        raise FileNotFoundError(f"Missing asset: {path}")
    assets[name] = im

print(f"Loaded {len(assets)} clean exact-contour assets.")

# Elements Staging Layout & Animation Keyframes on the 3400x2000 Whiteboard
# Format: { 'asset': name, 't_start': float, 't_dur': float, 'type': str, 'pos': (x, y), 'size': (w, h), ... }
# Layered Depth: lower depth is drawn first (background), higher depth drawn later (foreground)
elements_meta = [
    # === ACT 1: Ancient Origins in Central Asia & Caucasus (0.0s - 15.0s) ===
    # Background scenery
    {
        'id': '06_mountains', 'asset': '06_snowy_mountains_winter',
        't_start': 7.8, 't_dur': 1.6, 'type': 'slide_down',
        'pos': (780, 160), 'size': (380, 290), 'depth': 1
    },
    {
        'id': '07_asia_map', 'asset': '07_central_asia_map',
        't_start': 9.8, 't_dur': 1.5, 'type': 'slide_down',
        'pos': (1160, 220), 'size': (320, 270), 'depth': 1
    },
    {
        'id': '05_tree', 'asset': '05_blooming_apple_tree',
        't_start': 6.2, 't_dur': 1.4, 'type': 'organic_grow',
        'pos': (720, 360), 'size': (280, 290), 'depth': 2
    },
    {
        'id': '03_branch', 'asset': '03_wild_branch',
        't_start': 4.6, 't_dur': 1.4, 'type': 'slide_down',
        'pos': (440, 190), 'size': (340, 290), 'depth': 3
    },
    {
        'id': '04_flower', 'asset': '04_apple_blossom_flower',
        't_start': 6.5, 't_dur': 1.0, 'type': 'jelly_pop',
        'pos': (620, 310), 'size': (170, 190), 'depth': 4
    },
    # Foreground Hero inking
    {
        'id': '01_giant_apple', 'asset': '01_giant_red_apple',
        't_start': 0.4, 't_dur': 3.2, 'type': 'pen_ink',
        'pos': (160, 330), 'size': (310, 350), 'depth': 5
    },
    # Beside giant apple (contrast comparison)
    {
        'id': '02_wild_apple', 'asset': '02_wild_sour_apple',
        't_start': 3.8, 't_dur': 1.2, 'type': 'jelly_pop',
        'pos': (470, 440), 'size': (180, 230), 'depth': 5
    },

    # === ACT 2: Roman Expansion, Transport & Cultivation (15.0s - 32.0s) ===
    # Background Map
    {
        'id': '10_europe_map', 'asset': '10_europe_map_arrow',
        't_start': 15.2, 't_dur': 1.5, 'type': 'fade_in',
        'pos': (1720, 180), 'size': (420, 380), 'depth': 1
    },
    # Foreground Soldier
    {
        'id': '08_soldier', 'asset': '08_roman_soldier',
        't_start': 15.8, 't_dur': 3.0, 'type': 'pen_ink',
        'pos': (1520, 340), 'size': (280, 370), 'depth': 5
    },
    # Horse cart traveling across the map in foreground
    {
        'id': '09_horse_cart', 'asset': '09_horse_cart_apples',
        't_start': 19.5, 't_dur': 4.2, 'type': 'travel_slide',
        'pos_start': (1650, 490), 'pos_end': (1980, 490), 'size': (420, 250), 'depth': 6
    },
    # Farmer planting seedling
    {
        'id': '11_farmer', 'asset': '11_farmer_planting',
        't_start': 24.2, 't_dur': 2.5, 'type': 'pen_ink',
        'pos': (2220, 450), 'size': (350, 290), 'depth': 5
    },
    # 4 Tree stages unfolding beside the farmer
    {
        'id': '12_tree_stages', 'asset': '12_tree_growing_stages',
        't_start': 27.2, 't_dur': 4.2, 'type': 'tree_stages_grow',
        'pos': (2570, 420), 'size': (680, 290), 'depth': 4
    },

    # === ACT 3: Size Evolution, Selection & Diversity (32.0s - 46.0s) ===
    # Size evolution scale (crabapple to giant honeycrisp)
    {
        'id': '13_evolution', 'asset': '13_evolution_scale',
        't_start': 32.8, 't_dur': 3.5, 'type': 'horizontal_reveal',
        'pos': (1680, 1080), 'size': (840, 195), 'depth': 4
    },
    # Hand reaching and picking best fruit from branch
    {
        'id': '14_hand_picking', 'asset': '14_hand_picking_apple',
        't_start': 37.8, 't_dur': 2.8, 'type': 'hand_reach_pick',
        'pos': (2480, 1020), 'size': (420, 250), 'depth': 5
    },
    # Rainbow of apple varieties (5 distinct apples)
    {
        'id': '15_rainbow', 'asset': '15_apple_varieties_rainbow',
        't_start': 41.2, 't_dur': 3.8, 'type': 'rainbow_stagger',
        'pos': (1820, 1310), 'size': (680, 175), 'depth': 4
    },

    # === ACT 4: Harvest Crate, Sliced Apples & Quality (46.0s - 54.0s) ===
    # Seedling cycle beside crate
    {
        'id': '16_seedling', 'asset': '16_seedling_cycle',
        't_start': 45.4, 't_dur': 2.2, 'type': 'slide_up',
        'pos': (480, 1220), 'size': (360, 160), 'depth': 3
    },
    # Harvest crate
    {
        'id': '17_crate', 'asset': '17_harvest_crate',
        't_start': 46.2, 't_dur': 1.6, 'type': 'slide_down',
        'pos': (780, 1200), 'size': (320, 220), 'depth': 4
    },
    # Sliced apples & golden juice splash burst
    {
        'id': '18_sliced_juice', 'asset': '18_sliced_apples_juice',
        't_start': 47.5, 't_dur': 2.2, 'type': 'juice_burst',
        'pos': (1080, 1220), 'size': (580, 170), 'depth': 5
    },
    # Farmer inspecting apple
    {
        'id': '19_farmer_inspect', 'asset': '19_farmer_inspecting_apple',
        't_start': 49.2, 't_dur': 1.8, 'type': 'jelly_pop',
        'pos': (1520, 1200), 'size': (280, 230), 'depth': 4
    },
    # Quality inspection checkboxes on top
    {
        'id': '20_checkboxes', 'asset': '20_quality_checkboxes',
        't_start': 50.8, 't_dur': 2.4, 'type': 'checkbox_stagger',
        'pos': (1500, 1100), 'size': (320, 135), 'depth': 6
    },

    # === ACT 5: Health Benefits & Modern Refrigerator (54.0s - 60.88s) ===
    # Digestive health
    {
        'id': '21_digestive', 'asset': '21_digestive_health_gut',
        't_start': 54.0, 't_dur': 1.8, 'type': 'pulse_pop',
        'pos': (180, 1420), 'size': (280, 230), 'depth': 4
    },
    # Vitamins bubbles
    {
        'id': '22_vitamins', 'asset': '22_vitamins_bubbles',
        't_start': 54.8, 't_dur': 1.6, 'type': 'bubble_float',
        'pos': (440, 1440), 'size': (270, 180), 'depth': 4
    },
    # Heart health pulse
    {
        'id': '23_heart', 'asset': '23_heart_health_pulse',
        't_start': 55.4, 't_dur': 1.6, 'type': 'heartbeat_pop',
        'pos': (680, 1460), 'size': (260, 150), 'depth': 5
    },
    # Wheat fiber
    {
        'id': '24_wheat', 'asset': '24_wheat_fiber_apples',
        't_start': 55.8, 't_dur': 1.5, 'type': 'slide_up',
        'pos': (910, 1440), 'size': (280, 190), 'depth': 4
    },
    # Harvest pile
    {
        'id': '25_pile', 'asset': '25_apple_harvest_pile',
        't_start': 56.2, 't_dur': 1.6, 'type': 'slide_up',
        'pos': (1160, 1440), 'size': (340, 190), 'depth': 4
    },
    # Refrigerator reveal
    {
        'id': '26_refrigerator', 'asset': '26_refrigerator_modern_apples',
        't_start': 56.8, 't_dur': 2.0, 'type': 'fridge_door_open',
        'pos': (1480, 1380), 'size': (340, 300), 'depth': 6
    },
]

# Camera Timeline (Center X, Center Y, Zoom)
# Camera interpolates smoothly across narrative scenes
cam_keyframes = [
    ( 0.0,  350,  450, 1.45), # Act 1: Giant apple focus
    ( 4.0,  520,  400, 1.35), # Act 1: Sour apple & branch
    ( 9.0,  780,  360, 1.25), # Act 1: Mountains & Asia map
    (14.2,  850,  360, 1.20),
    (16.5, 1750,  440, 1.30), # Act 2: Roman soldier & Europe map
    (20.5, 1850,  480, 1.30), # Act 2: Horse cart journey
    (25.0, 2400,  500, 1.30), # Act 2: Farmer planting
    (29.0, 2750,  500, 1.25), # Act 2: Tree growing stages
    (32.0, 2600,  550, 1.20),
    (34.0, 2100, 1150, 1.30), # Act 3: Evolution scale
    (38.5, 2550, 1120, 1.35), # Act 3: Hand picking apple
    (42.5, 2150, 1320, 1.30), # Act 3: Rainbow varieties
    (45.5, 1800, 1300, 1.25),
    (47.5, 1150, 1260, 1.35), # Act 4: Sliced apple & juice burst
    (51.0, 1550, 1200, 1.35), # Act 4: Quality checkboxes
    (53.5, 1300, 1250, 1.25),
    (55.0,  580, 1450, 1.30), # Act 5: Health & vitamins
    (57.0, 1450, 1460, 1.30), # Act 5: Modern Refrigerator
    (60.88, 1600, 950, 0.58), # GRAND OUTRO: Zoom out to see full panoramic whiteboard!
]

def get_camera_state(time_s: float):
    if time_s <= cam_keyframes[0][0]:
        _, x, y, z = cam_keyframes[0]
        return float(x), float(y), float(z)
    if time_s >= cam_keyframes[-1][0]:
        _, x, y, z = cam_keyframes[-1]
        return float(x), float(y), float(z)
    
    for i in range(len(cam_keyframes) - 1):
        t0, x0, y0, z0 = cam_keyframes[i]
        t1, x1, y1, z1 = cam_keyframes[i + 1]
        if t0 <= time_s <= t1:
            ratio = (time_s - t0) / (t1 - t0)
            e = smootherstep(ratio)
            # Special grand outro easing
            if i == len(cam_keyframes) - 2:
                e = smootherstep(ratio)
            cx = x0 + (x1 - x0) * e
            cy = y0 + (y1 - y0) * e
            cz = z0 + (z1 - z0) * e
            return cx, cy, cz
    return cam_keyframes[-1][1:]

# Helper function to overlay RGBA sprite onto canvas
def overlay_sprite(canvas, sprite_rgba, x, y, w, h, alpha_mult=1.0, scale_x=1.0, scale_y=1.0, rot_deg=0.0):
    if alpha_mult <= 0.01:
        return
    
    sh, sw = sprite_rgba.shape[:2]
    tw = max(2, int(w * scale_x))
    th = max(2, int(h * scale_y))
    
    if tw != sw or th != sh:
        resized = cv2.resize(sprite_rgba, (tw, th), interpolation=cv2.INTER_LINEAR)
    else:
        resized = sprite_rgba
        
    if rot_deg != 0.0:
        M = cv2.getRotationMatrix2D((tw / 2.0, th / 2.0), rot_deg, 1.0)
        resized = cv2.warpAffine(resized, M, (tw, th), borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
    
    # Coordinates centered
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
    
    sub_sprite = resized[s_y1:s_y2, s_x1:s_x2]
    sub_canvas = canvas[c_y1:c_y2, c_x1:c_x2]
    
    s_bgr = sub_sprite[:, :, :3].astype(np.float32)
    s_a = (sub_sprite[:, :, 3].astype(np.float32) / 255.0) * alpha_mult
    s_a3 = np.repeat(s_a[:, :, np.newaxis], 3, axis=2)
    
    c_bgr = sub_canvas.astype(np.float32)
    blended = np.clip(s_bgr * s_a3 + c_bgr * (1.0 - s_a3), 0, 255).astype(np.uint8)
    canvas[c_y1:c_y2, c_x1:c_x2] = blended

sys.stdout.reconfigure(line_buffering=True)

# Start FFmpeg pipe process
out_mp4 = "output_animations/apple_storyboard_masterpiece_2026.mp4"
raw_video_mp4 = "output_animations/raw_apple_video.mp4"
os.makedirs("output_animations", exist_ok=True)

# Clean previous temp file
if os.path.exists(raw_video_mp4):
    try:
        os.remove(raw_video_mp4)
    except:
        pass

# Log file for FFmpeg to prevent pipe buffer deadlocks
ffmpeg_log_file = open("experiments/ffmpeg_render.log", "w")

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
    pipe = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=ffmpeg_log_file, stderr=ffmpeg_log_file)
    print("Opened FFmpeg pipe with NVENC encoder.")
except Exception as e:
    print(f"NVENC failed, falling back to libx264: {e}")
    ffmpeg_cmd[ffmpeg_cmd.index("h264_nvenc")] = "libx264"
    pipe = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=ffmpeg_log_file, stderr=ffmpeg_log_file)

# Master Whiteboard Render Loop
print(f"Rendering {TOTAL_FRAMES} frames ({TOTAL_DURATION}s) at {WIDTH}x{HEIGHT}...")

# Pre-sort elements by depth
sorted_elements = sorted(elements_meta, key=lambda x: x.get('depth', 1))

# Live canvas on which all elements are rendered
white_canvas = np.full((CANVAS_H, CANVAS_W, 3), 255, dtype=np.uint8)

for frame_idx in range(TOTAL_FRAMES):
    time_s = frame_idx / float(FPS)
    
    # 1. Reset canvas to clean white
    frame_canvas = np.full((CANVAS_H, CANVAS_W, 3), 255, dtype=np.uint8)
    
    active_hand_pos = None # (x, y) if pen is currently drawing
    
    # 2. Render all active elements according to their progress and depth
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
        
        if m_type == 'pen_ink':
            # Pen Inking: reveals inside contour while hand traces outline
            if progress < 1.0:
                # Radial/concentric sweep reveal
                reveal_ratio = ease_out_back(progress, 0.4)
                # Create mask revealing from center outward
                ah, aw = asset.shape[:2]
                mask_circ = np.zeros((ah, aw), dtype=np.uint8)
                radius = int(math.hypot(aw, ah) * 0.7 * min(1.0, progress * 1.15))
                cv2.circle(mask_circ, (aw // 2, ah // 2), radius, 255, -1)
                
                inked_asset = asset.copy()
                inked_asset[:, :, 3] = cv2.bitwise_and(asset[:, :, 3], mask_circ)
                overlay_sprite(frame_canvas, inked_asset, px, py, pw, ph)
                
                # Orbiting pen tip position
                angle = progress * math.pi * 6.0
                tip_cx = px + pw // 2 + int((pw * 0.35 * (1.0 - progress * 0.5)) * math.cos(angle))
                tip_cy = py + ph // 2 + int((ph * 0.35 * (1.0 - progress * 0.5)) * math.sin(angle))
                active_hand_pos = (tip_cx, tip_cy)
            else:
                overlay_sprite(frame_canvas, asset, px, py, pw, ph)
                
        elif m_type == 'jelly_pop':
            sx, sy = get_jelly_scales(progress)
            overlay_sprite(frame_canvas, asset, px, py, pw, ph, alpha_mult=min(1.0, progress * 3.0), scale_x=sx, scale_y=sy)
            
        elif m_type == 'slide_down':
            e = ease_out_back(progress, 1.1)
            y_offset = int((1.0 - e) * 70)
            overlay_sprite(frame_canvas, asset, px, py - y_offset, pw, ph, alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'slide_up':
            e = ease_out_back(progress, 1.1)
            y_offset = int((1.0 - e) * 70)
            overlay_sprite(frame_canvas, asset, px, py + y_offset, pw, ph, alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'fade_in':
            alpha_m = smootherstep(progress)
            overlay_sprite(frame_canvas, asset, px, py, pw, ph, alpha_mult=alpha_m)
            
        elif m_type == 'travel_slide':
            # Smooth movement from pos_start to pos_end
            e = smootherstep(progress)
            x_start, y_start = elem['pos_start']
            x_end, y_end = elem['pos_end']
            cur_x = int(x_start + (x_end - x_start) * e)
            cur_y = int(y_start + (y_end - y_start) * e)
            # Gentle horse gallop bobbing
            bob = int(math.sin(progress * 25.0) * 4.0) if progress < 1.0 else 0
            overlay_sprite(frame_canvas, asset, cur_x, cur_y + bob, pw, ph, alpha_mult=min(1.0, progress * 3.0))
            
        elif m_type == 'organic_grow':
            # Tree branches expand from bottom upward
            e = ease_out_back(progress, 0.8)
            sx = 0.4 + 0.6 * e
            sy = e
            overlay_sprite(frame_canvas, asset, px, py + int(ph * (1.0 - sy)), pw, ph, scale_x=sx, scale_y=sy, alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'tree_stages_grow':
            # 4 stages sequence
            sx, sy = get_jelly_scales(progress)
            overlay_sprite(frame_canvas, asset, px, py, pw, ph, scale_x=sx, scale_y=sy, alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'horizontal_reveal':
            # Scale evolution progression
            ah, aw = asset.shape[:2]
            crop_w = max(1, int(aw * smootherstep(progress)))
            revealed = asset.copy()
            revealed[:, crop_w:, 3] = 0
            overlay_sprite(frame_canvas, revealed, px, py, pw, ph)
            
        elif m_type == 'hand_reach_pick':
            e = ease_out_back(progress, 1.2)
            y_offset = int((1.0 - e) * 80)
            overlay_sprite(frame_canvas, asset, px, py - y_offset, pw, ph, alpha_mult=min(1.0, progress * 3.0))
            
        elif m_type == 'rainbow_stagger':
            sx, sy = get_jelly_scales(progress)
            overlay_sprite(frame_canvas, asset, px, py, pw, ph, scale_x=sx, scale_y=sy, alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'juice_burst':
            # Sliced apple & golden juice splash expanding outward
            sx, sy = get_jelly_scales(progress)
            burst_scale = 1.0 + 0.08 * math.sin(progress * math.pi) if progress < 1.0 else 1.0
            overlay_sprite(frame_canvas, asset, px, py, pw, ph, scale_x=sx * burst_scale, scale_y=sy * burst_scale, alpha_mult=min(1.0, progress * 3.0))
            
        elif m_type == 'checkbox_stagger':
            sx, sy = get_jelly_scales(progress)
            overlay_sprite(frame_canvas, asset, px, py, pw, ph, scale_x=sx, scale_y=sy, alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'pulse_pop':
            pulse = 1.0 + 0.05 * math.sin(time_s * 6.0)
            sx, sy = get_jelly_scales(progress)
            overlay_sprite(frame_canvas, asset, px, py, pw, ph, scale_x=sx * pulse, scale_y=sy * pulse, alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'bubble_float':
            float_y = int(math.sin(time_s * 4.0) * 5.0)
            sx, sy = get_jelly_scales(progress)
            overlay_sprite(frame_canvas, asset, px, py + float_y, pw, ph, scale_x=sx, scale_y=sy, alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'heartbeat_pop':
            # Rhythmic double-beat
            beat = math.pow(math.sin(time_s * 5.0), 10.0) * 0.12
            sx, sy = get_jelly_scales(progress)
            overlay_sprite(frame_canvas, asset, px, py, pw, ph, scale_x=(sx + beat), scale_y=(sy + beat), alpha_mult=min(1.0, progress * 2.5))
            
        elif m_type == 'fridge_door_open':
            e = ease_out_back(progress, 1.1)
            overlay_sprite(frame_canvas, asset, px, py, pw, ph, scale_x=e, scale_y=1.0, alpha_mult=min(1.0, progress * 2.5))
            
        else:
            overlay_sprite(frame_canvas, asset, px, py, pw, ph)

    # 3. Composite Hand on canvas if currently inking
    if active_hand_pos is not None and hand_bgra is not None:
        hx, hy = active_hand_pos
        frame_canvas = composite_hand_on_canvas_fast(frame_canvas, hand_bgra, pen_x_scaled, pen_y_scaled, hx, hy)

    # 4. Apply Dynamic Cinematic Viewport / Camera Transform
    cam_x, cam_y, cam_zoom = get_camera_state(time_s)
    
    # Calculate source viewport box on canvas
    vp_w = WIDTH / cam_zoom
    vp_h = HEIGHT / cam_zoom
    
    x1 = cam_x - vp_w / 2.0
    y1 = cam_y - vp_h / 2.0
    x2 = x1 + vp_w
    y2 = y1 + vp_h
    
    # Affine transform matrix mapping (x1, y1) -> (0, 0) and (x2, y2) -> (WIDTH, HEIGHT)
    src_pts = np.float32([[x1, y1], [x2, y1], [x1, y2]])
    dst_pts = np.float32([[0, 0], [WIDTH, 0], [0, HEIGHT]])
    M = cv2.getAffineTransform(src_pts, dst_pts)
    
    viewport_frame = cv2.warpAffine(
        frame_canvas, M, (WIDTH, HEIGHT),
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
        flags=cv2.INTER_LINEAR
    )
    
    # 5. Write to FFmpeg pipe
    pipe.stdin.write(viewport_frame.tobytes())
    
    if (frame_idx + 1) % 150 == 0 or frame_idx == TOTAL_FRAMES - 1:
        percent = (frame_idx + 1) / TOTAL_FRAMES * 100.0
        print(f"Render progress: {frame_idx + 1}/{TOTAL_FRAMES} frames ({percent:.1f}%) [time: {time_s:.2f}s]")

pipe.stdin.close()
pipe.wait()
ffmpeg_log_file.close()
print(f"Raw video render complete: {raw_video_mp4}")

# 6. Multiplex with Ducked Audio via FFmpeg
audio_path = "project_content/audio/apple_master_ducked_audio.wav"
final_mux_cmd = [
    "ffmpeg", "-y",
    "-i", raw_video_mp4,
    "-i", audio_path,
    "-c:v", "copy",
    "-c:a", "aac",
    "-b:a", "192k",
    "-shortest",
    out_mp4
]

print("Multiplexing video and ducked audio...")
mux_proc = subprocess.run(final_mux_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if mux_proc.returncode == 0:
    print(f"SUCCESS: Final Masterpiece saved to: {out_mp4}")
else:
    print(f"Multiplexing error: {mux_proc.stderr.decode('utf-8', errors='ignore')}")

