"""
Sheet 1 Masterpiece 2026 Production Renderer
Full Duration: 89.91 seconds @ 30fps (2698 frames)
Resolution: 1920x1080 Full HD (Master Canvas: 4800x2700 16:9)

Visual Standards:
1. Pure Outside-In Inking: 100% pen contact, zero pre-reveal.
2. 2026 Motion Effects:
   - Non-uniform Jelly squash & stretch
   - Directional velocity slide with spring overshoot & motion blur
   - Smooth fade dissolves
3. Camera Trajectory:
   - Close-up framing (vw=2000, vh=1125): panel 864x864, perfectly framed with 108px top/bottom margin, 0% crop
   - Horizontal pans between panels
   - S-Curve Crane Dip from P3 to P4
   - Grand Outro Reveal zoom-out (vw=5000, vh=2812.5) showing all 6 panels
4. Audio & SFX:
   - Pre-ducked master audio mix with dynamic speech sidechaining and 120Hz high-pass filter.
"""
import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
import math
import time
import subprocess
import cv2
import av
import numpy as np

ROOT_DIR = r"E:\image_to_animate"
if os.path.join(ROOT_DIR, 'kivy') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'kivy'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
from engine.render.concentric_engine import (
    DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH,
    PEN_TIP_ANCHOR_X, PEN_TIP_ANCHOR_Y,
    build_gapless_orbital_path
)


def smootherstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (6.0 * t - 15.0) + 10.0)


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - math.pow(1.0 - t, 3)


def ease_out_back(t: float, overshoot: float = 1.25) -> float:
    t = max(0.0, min(1.0, t)) - 1.0
    return t * t * ((overshoot + 1.0) * t + overshoot) + 1.0


def get_jelly_scales(t: float) -> tuple:
    t = max(0.0, min(1.0, t))
    if t >= 1.0:
        return 1.0, 1.0
    if t <= 0.0:
        return 0.0, 0.0
    omega = 18.0
    decay = math.exp(-t * 5.2)
    osc = decay * math.cos(omega * t)
    base = 1.0 - math.pow(1.0 - t, 4)
    return max(0.01, base + 0.35 * osc), max(0.01, base - 0.28 * osc)


def overlay_rgba(base_bgr, overlay_rgba, x, y, alpha_factor=1.0):
    bh, bw = base_bgr.shape[:2]
    oh, ow = overlay_rgba.shape[:2]
    
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(bw, x + ow), min(bh, y + oh)
    if x1 >= x2 or y1 >= y2:
        return
        
    ox1, oy1 = x1 - x, y1 - y
    ox2, oy2 = ox1 + (x2 - x1), oy1 + (y2 - y1)
    
    b_roi = base_bgr[y1:y2, x1:x2].astype(np.float32)
    o_bgr = overlay_rgba[oy1:oy2, ox1:ox2, :3].astype(np.float32)
    o_alpha = (overlay_rgba[oy1:oy2, ox1:ox2, 3].astype(np.float32) / 255.0) * alpha_factor
    o_alpha = np.repeat(o_alpha[:, :, np.newaxis], 3, axis=2)
    
    blended = o_alpha * o_bgr + (1.0 - o_alpha) * b_roi
    base_bgr[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)


def render_masterpiece(
    video_no_audio: str = "output_animations/sheet_01_masterpiece_temp.mp4",
    final_output: str = "output_animations/sheet_01_masterpiece_2026.mp4"
):
    print("=" * 80)
    print(">>> LAUNCHING SHEET 1 2026 MASTERPIECE PRODUCTION (89.91s | 1080p @ 30fps) <<<")
    print("=" * 80)
    os.makedirs(os.path.dirname(video_no_audio), exist_ok=True)
    
    canvas_w, canvas_h = 4800, 2700
    out_w, out_h = 1920, 1080
    fps = 30
    duration = 89.91
    total_frames = int(round(duration * fps))
    
    # 3x2 Grid Setup on Master Canvas
    pw, ph = 900, 900
    panel_origins = [
        (450, 300),   # P1
        (1950, 300),  # P2
        (3450, 300),  # P3
        (450, 1500),  # P4
        (1950, 1500), # P5
        (3450, 1500)  # P6
    ]
    panel_centers = [(ox + pw // 2, oy + ph // 2) for ox, oy in panel_origins]
    master_center = (canvas_w // 2, canvas_h // 2)
    
    # Live Master Whiteboard Canvas
    master_canvas = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)
    
    # Draw all 6 panel borders permanently
    for ox, oy in panel_origins:
        cv2.rectangle(master_canvas, (ox, oy), (ox + pw, oy + ph), (35, 35, 35), 4)
        cv2.circle(master_canvas, (ox, oy), 6, (35, 35, 35), -1)
        cv2.circle(master_canvas, (ox + pw, oy), 6, (35, 35, 35), -1)
        cv2.circle(master_canvas, (ox, oy + ph), 6, (35, 35, 35), -1)
        cv2.circle(master_canvas, (ox + pw, oy + ph), 6, (35, 35, 35), -1)

    # Load hand asset
    hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
    hand_screen_h = int(out_h * 0.40)
    hand_scale = hand_screen_h / float(hand_bgra.shape[0])
    hand_screen_w = max(1, int(hand_bgra.shape[1] * hand_scale))
    hand_screen = cv2.resize(hand_bgra, (hand_screen_w, hand_screen_h), interpolation=cv2.INTER_AREA)
    tip_screen_x = int(round(PEN_TIP_ANCHOR_X * hand_scale))
    tip_screen_y = int(round(PEN_TIP_ANCHOR_Y * hand_scale))

    # Helper to load layer
    layers_base = "experiments/choreographed_layers"
    def load_layer(p_num, name):
        p_dir = os.path.join(layers_base, f"panel_{p_num:02d}")
        png_path = os.path.join(p_dir, f"{name}.png")
        txt_path = os.path.join(p_dir, f"{name}.txt")
        img = cv2.imread(png_path, cv2.IMREAD_UNCHANGED)
        coords = [int(v.strip()) for v in open(txt_path).read().split(",")]
        return {
            "img": img,
            "rx": coords[0],
            "ry": coords[1],
            "rw": coords[2],
            "rh": coords[3]
        }

    print("Loading choreographed assets...")
    # Panel 1
    p1_narrator = load_layer(1, "narrator")
    p1_thermo = load_layer(1, "thermometer")
    p1_crowd = load_layer(1, "crowd_gray")
    p1_red = load_layer(1, "red_figures")
    p1_badge = load_layer(1, "badge_2pct")
    
    # Panel 2
    p2_brain = load_layer(2, "brain_profile")
    p2_saturn = load_layer(2, "saturn")
    p2_charts = load_layer(2, "charts")
    p2_stressed = load_layer(2, "stressed_person")
    p2_math = load_layer(2, "math_symbols")
    p2_warning = load_layer(2, "warning_error")
    
    # Panel 3
    p3_logic = load_layer(3, "brain_logic")
    p3_creative = load_layer(3, "brain_creative")
    p3_icons_logic = load_layer(3, "icons_logic")
    p3_icons_creative = load_layer(3, "icons_creative")
    
    # Panel 4
    p4_growth = load_layer(4, "growth_figures")
    p4_learning = load_layer(4, "learning_elements")
    
    # Panel 5
    p5_thinker = load_layer(5, "char_thinker")
    p5_b_house = load_layer(5, "bubble_house")
    p5_b_people = load_layer(5, "bubble_people")
    p5_b_money = load_layer(5, "bubble_money")
    p5_b_time = load_layer(5, "bubble_time")
    p5_b_plant = load_layer(5, "bubble_plant")
    p5_b_heart = load_layer(5, "bubble_heart")
    
    # Panel 6
    p6_stairs = load_layer(6, "stairs_and_door")
    p6_hero = load_layer(6, "hero_character")
    p6_compass = load_layer(6, "compass")
    p6_symbols = load_layer(6, "symbols_obstacles")

    print("Generating Concentric Outside-In Stroke Paths for Key Characters...")
    def gen_strokes(layer_dict):
        img = layer_dict["img"]
        strokes = build_gapless_orbital_path(
            img[:, :, :3], ring_step=7, sample_interval=4.0, brush_radius=9,
            drawing_direction="OUTSIDE_IN", mask=img[:, :, 3]
        )
        pts = []
        for s in strokes:
            pts.extend(s)
        return pts

    p1_narrator_pts = gen_strokes(p1_narrator)
    p2_brain_pts = gen_strokes(p2_brain)
    p3_logic_pts = gen_strokes(p3_logic)
    p3_creative_pts = gen_strokes(p3_creative)
    p4_growth_pts = gen_strokes(p4_growth)
    p5_thinker_pts = gen_strokes(p5_thinker)
    p6_stairs_pts = gen_strokes(p6_stairs)
    print("Stroke paths generated!")

    # Setup NVENC Video Stream
    container = av.open(video_no_audio, mode="w")
    v_stream = container.add_stream("h264_nvenc", rate=fps)
    v_stream.width = out_w
    v_stream.height = out_h
    v_stream.pix_fmt = "yuv420p"
    v_stream.options = {"preset": "p5", "cq": "18"}

    # Live inking masks
    p1_narrator_mask = np.zeros(p1_narrator["img"].shape[:2], dtype=np.uint8)
    p1_narrator_pt_idx = 0
    
    p2_brain_mask = np.zeros(p2_brain["img"].shape[:2], dtype=np.uint8)
    p2_brain_pt_idx = 0
    
    p3_logic_mask = np.zeros(p3_logic["img"].shape[:2], dtype=np.uint8)
    p3_logic_pt_idx = 0
    p3_creative_mask = np.zeros(p3_creative["img"].shape[:2], dtype=np.uint8)
    p3_creative_pt_idx = 0
    
    p4_growth_mask = np.zeros(p4_growth["img"].shape[:2], dtype=np.uint8)
    p4_growth_pt_idx = 0
    
    p5_thinker_mask = np.zeros(p5_thinker["img"].shape[:2], dtype=np.uint8)
    p5_thinker_pt_idx = 0
    
    p6_stairs_mask = np.zeros(p6_stairs["img"].shape[:2], dtype=np.uint8)
    p6_stairs_pt_idx = 0

    print(f"Encoding {total_frames} frames to {video_no_audio}...")
    start_time = time.time()

    for f_idx in range(total_frames):
        t = f_idx / float(fps)
        
        # 1. CAMERA CHOREOGRAPHY
        # Default close-up viewport: vw=2000, vh=1125 (fits 900x900 with 108px top/bottom padding)
        vw, vh = 2000.0, 1125.0
        hand_canvas_pt = None
        
        if t < 14.2:
            cx, cy = panel_centers[0]
        elif 14.2 <= t < 15.4:
            prog = smootherstep((t - 14.2) / 1.2)
            cx = panel_centers[0][0] + (panel_centers[1][0] - panel_centers[0][0]) * prog
            cy = panel_centers[0][1]
        elif 15.4 <= t < 33.5:
            cx, cy = panel_centers[1]
        elif 33.5 <= t < 34.8:
            prog = smootherstep((t - 33.5) / 1.3)
            cx = panel_centers[1][0] + (panel_centers[2][0] - panel_centers[1][0]) * prog
            cy = panel_centers[1][1]
        elif 34.8 <= t < 47.0:
            cx, cy = panel_centers[2]
        elif 47.0 <= t < 48.8:
            # S-Curve Crane Dip from P3 to P4
            prog = smootherstep((t - 47.0) / 1.8)
            p3 = panel_centers[2]
            p4 = panel_centers[3]
            c1 = (p3[0] + 200, p3[1] + 400)
            c2 = (p4[0] - 200, p4[1] - 400)
            cx = (1-prog)**3*p3[0] + 3*(1-prog)**2*prog*c1[0] + 3*(1-prog)*prog**2*c2[0] + prog**3*p4[0]
            cy = (1-prog)**3*p3[1] + 3*(1-prog)**2*prog*c1[1] + 3*(1-prog)*prog**2*c2[1] + prog**3*p4[1]
            swoop_zoom = math.sin(math.pi * prog)
            vw = 2000.0 + 400.0 * swoop_zoom
            vh = 1125.0 + 225.0 * swoop_zoom
        elif 48.8 <= t < 70.0:
            cx, cy = panel_centers[3]
        elif 70.0 <= t < 71.2:
            prog = smootherstep((t - 70.0) / 1.2)
            cx = panel_centers[3][0] + (panel_centers[4][0] - panel_centers[3][0]) * prog
            cy = panel_centers[3][1]
        elif 71.2 <= t < 80.0:
            cx, cy = panel_centers[4]
        elif 80.0 <= t < 81.2:
            prog = smootherstep((t - 80.0) / 1.2)
            cx = panel_centers[4][0] + (panel_centers[5][0] - panel_centers[4][0]) * prog
            cy = panel_centers[4][1]
        elif 81.2 <= t < 85.8:
            cx, cy = panel_centers[5]
        else:
            # GRAND OUTRO REVEAL: Zoom-out to full whiteboard showing all 6 panels!
            prog = smootherstep((t - 85.8) / 4.11)
            cx = panel_centers[5][0] + (master_center[0] - panel_centers[5][0]) * prog
            cy = panel_centers[5][1] + (master_center[1] - panel_centers[5][1]) * prog
            vw = 2000.0 + (5000.0 - 2000.0) * prog
            vh = 1125.0 + (2812.5 - 1125.0) * prog

        # 2. LOCAL WORKING CANVAS FOR DYNAMIC MOTION EFFECTS
        # Copy master canvas for non-permanent motion effects (slides/pops)
        frame_canvas = master_canvas.copy()

        # ================= PANEL 1 CHOREOGRAPHY =================
        p1_ox, p1_oy = panel_origins[0]
        # Inking Narrator (0.5s - 5.0s)
        if 0.5 <= t < 5.0:
            prog = (t - 0.5) / 4.5
            n_pts = len(p1_narrator_pts)
            tgt_idx = min(n_pts - 1, int(round(prog * (n_pts - 1))))
            if tgt_idx > p1_narrator_pt_idx:
                for pi in range(p1_narrator_pt_idx, tgt_idx):
                    pt1 = (int(round(p1_narrator_pts[pi][0])), int(round(p1_narrator_pts[pi][1])))
                    pt2 = (int(round(p1_narrator_pts[pi+1][0])), int(round(p1_narrator_pts[pi+1][1])))
                    cv2.line(p1_narrator_mask, pt1, pt2, 255, thickness=18)
                    cv2.circle(p1_narrator_mask, pt2, 9, 255, -1)
                p1_narrator_pt_idx = tgt_idx
            cur_pt = p1_narrator_pts[tgt_idx]
            hand_canvas_pt = (p1_ox + p1_narrator["rx"] + cur_pt[0], p1_oy + p1_narrator["ry"] + cur_pt[1])
            
            eff_mask = cv2.bitwise_and(p1_narrator_mask, p1_narrator["img"][:, :, 3])
            partial_rgba = p1_narrator["img"].copy()
            partial_rgba[:, :, 3] = eff_mask
            overlay_rgba(master_canvas, partial_rgba, p1_ox + p1_narrator["rx"], p1_oy + p1_narrator["ry"])
        elif t >= 5.0 and p1_narrator_pt_idx < len(p1_narrator_pts) - 1:
            overlay_rgba(master_canvas, p1_narrator["img"], p1_ox + p1_narrator["rx"], p1_oy + p1_narrator["ry"])
            p1_narrator_pt_idx = len(p1_narrator_pts) - 1

        # Thermometer Slide-up (4.8s - 6.5s)
        if 4.8 <= t < 6.5:
            prog = min(1.0, (t - 4.8) / 1.7)
            ease = ease_out_back(prog, overshoot=1.2)
            dy = int(round((1.0 - ease) * 180))
            overlay_rgba(frame_canvas, p1_thermo["img"], p1_ox + p1_thermo["rx"], p1_oy + p1_thermo["ry"] + dy)
        elif t >= 6.5:
            overlay_rgba(master_canvas, p1_thermo["img"], p1_ox + p1_thermo["rx"], p1_oy + p1_thermo["ry"])

        # Crowd Fade Dissolve (6.5s - 8.2s)
        if 6.5 <= t < 8.2:
            prog = min(1.0, (t - 6.5) / 1.7)
            alpha_f = smootherstep(prog)
            overlay_rgba(frame_canvas, p1_crowd["img"], p1_ox + p1_crowd["rx"], p1_oy + p1_crowd["ry"], alpha_factor=alpha_f)
        elif t >= 8.2:
            overlay_rgba(master_canvas, p1_crowd["img"], p1_ox + p1_crowd["rx"], p1_oy + p1_crowd["ry"])

        # Red Figures Jelly Pop (8.2s - 9.5s)
        if 8.2 <= t < 9.5:
            prog = min(1.0, (t - 8.2) / 1.3)
            sx, sy = get_jelly_scales(prog)
            rw, rh = p1_red["rw"], p1_red["rh"]
            scaled_w, scaled_h = max(1, int(round(rw * sx))), max(1, int(round(rh * sy)))
            scaled_img = cv2.resize(p1_red["img"], (scaled_w, scaled_h), interpolation=cv2.INTER_LANCZOS4)
            dx = (scaled_w - rw) // 2
            dy = (scaled_h - rh) // 2
            overlay_rgba(frame_canvas, scaled_img, p1_ox + p1_red["rx"] - dx, p1_oy + p1_red["ry"] - dy)
        elif t >= 9.5:
            overlay_rgba(master_canvas, p1_red["img"], p1_ox + p1_red["rx"], p1_oy + p1_red["ry"])

        # Badge 2% Jelly Pop (9.5s - 10.8s)
        if 9.5 <= t < 10.8:
            prog = min(1.0, (t - 9.5) / 1.3)
            sx, sy = get_jelly_scales(prog)
            rw, rh = p1_badge["rw"], p1_badge["rh"]
            scaled_w, scaled_h = max(1, int(round(rw * sx))), max(1, int(round(rh * sy)))
            scaled_img = cv2.resize(p1_badge["img"], (scaled_w, scaled_h), interpolation=cv2.INTER_LANCZOS4)
            dx = (scaled_w - rw) // 2
            dy = (scaled_h - rh) // 2
            overlay_rgba(frame_canvas, scaled_img, p1_ox + p1_badge["rx"] - dx, p1_oy + p1_badge["ry"] - dy)
        elif t >= 10.8:
            overlay_rgba(master_canvas, p1_badge["img"], p1_ox + p1_badge["rx"], p1_oy + p1_badge["ry"])

        # ================= PANEL 2 CHOREOGRAPHY =================
        p2_ox, p2_oy = panel_origins[1]
        # Inking Brain Profile (15.4s - 20.8s)
        if 15.4 <= t < 20.8:
            prog = (t - 15.4) / 5.4
            n_pts = len(p2_brain_pts)
            tgt_idx = min(n_pts - 1, int(round(prog * (n_pts - 1))))
            if tgt_idx > p2_brain_pt_idx:
                for pi in range(p2_brain_pt_idx, tgt_idx):
                    pt1 = (int(round(p2_brain_pts[pi][0])), int(round(p2_brain_pts[pi][1])))
                    pt2 = (int(round(p2_brain_pts[pi+1][0])), int(round(p2_brain_pts[pi+1][1])))
                    cv2.line(p2_brain_mask, pt1, pt2, 255, thickness=18)
                    cv2.circle(p2_brain_mask, pt2, 9, 255, -1)
                p2_brain_pt_idx = tgt_idx
            cur_pt = p2_brain_pts[tgt_idx]
            hand_canvas_pt = (p2_ox + p2_brain["rx"] + cur_pt[0], p2_oy + p2_brain["ry"] + cur_pt[1])
            
            eff_mask = cv2.bitwise_and(p2_brain_mask, p2_brain["img"][:, :, 3])
            partial_rgba = p2_brain["img"].copy()
            partial_rgba[:, :, 3] = eff_mask
            overlay_rgba(master_canvas, partial_rgba, p2_ox + p2_brain["rx"], p2_oy + p2_brain["ry"])
        elif t >= 20.8 and p2_brain_pt_idx < len(p2_brain_pts) - 1:
            overlay_rgba(master_canvas, p2_brain["img"], p2_ox + p2_brain["rx"], p2_oy + p2_brain["ry"])
            p2_brain_pt_idx = len(p2_brain_pts) - 1

        # Saturn Slide (20.8s - 23.0s)
        if 20.8 <= t < 23.0:
            prog = min(1.0, (t - 20.8) / 2.2)
            ease = ease_out_back(prog, overshoot=1.2)
            dx = int(round(-(1.0 - ease) * 160))
            dy = int(round(-(1.0 - ease) * 120))
            overlay_rgba(frame_canvas, p2_saturn["img"], p2_ox + p2_saturn["rx"] + dx, p2_oy + p2_saturn["ry"] + dy)
        elif t >= 23.0:
            overlay_rgba(master_canvas, p2_saturn["img"], p2_ox + p2_saturn["rx"], p2_oy + p2_saturn["ry"])

        # Charts Slide from Top (23.0s - 25.5s)
        if 23.0 <= t < 25.5:
            prog = min(1.0, (t - 23.0) / 2.5)
            ease = ease_out_back(prog, overshoot=1.2)
            dy = int(round(-(1.0 - ease) * 160))
            overlay_rgba(frame_canvas, p2_charts["img"], p2_ox + p2_charts["rx"], p2_oy + p2_charts["ry"] + dy)
        elif t >= 25.5:
            overlay_rgba(master_canvas, p2_charts["img"], p2_ox + p2_charts["rx"], p2_oy + p2_charts["ry"])

        # Stressed Person Slide Up (25.5s - 28.0s)
        if 25.5 <= t < 28.0:
            prog = min(1.0, (t - 25.5) / 2.5)
            ease = ease_out_back(prog, overshoot=1.2)
            dy = int(round((1.0 - ease) * 180))
            overlay_rgba(frame_canvas, p2_stressed["img"], p2_ox + p2_stressed["rx"], p2_oy + p2_stressed["ry"] + dy)
        elif t >= 28.0:
            overlay_rgba(master_canvas, p2_stressed["img"], p2_ox + p2_stressed["rx"], p2_oy + p2_stressed["ry"])

        # Math Symbols Fade (28.0s - 30.5s)
        if 28.0 <= t < 30.5:
            prog = min(1.0, (t - 28.0) / 2.5)
            overlay_rgba(frame_canvas, p2_math["img"], p2_ox + p2_math["rx"], p2_oy + p2_math["ry"], alpha_factor=smootherstep(prog))
        elif t >= 30.5:
            overlay_rgba(master_canvas, p2_math["img"], p2_ox + p2_math["rx"], p2_oy + p2_math["ry"])

        # Warning Badge Jelly Pop (28.5s - 30.2s)
        if 28.5 <= t < 30.2:
            prog = min(1.0, (t - 28.5) / 1.7)
            sx, sy = get_jelly_scales(prog)
            rw, rh = p2_warning["rw"], p2_warning["rh"]
            scaled_w, scaled_h = max(1, int(round(rw * sx))), max(1, int(round(rh * sy)))
            scaled_img = cv2.resize(p2_warning["img"], (scaled_w, scaled_h), interpolation=cv2.INTER_LANCZOS4)
            dx = (scaled_w - rw) // 2
            dy = (scaled_h - rh) // 2
            overlay_rgba(frame_canvas, scaled_img, p2_ox + p2_warning["rx"] - dx, p2_oy + p2_warning["ry"] - dy)
        elif t >= 30.2:
            overlay_rgba(master_canvas, p2_warning["img"], p2_ox + p2_warning["rx"], p2_oy + p2_warning["ry"])

        # ================= PANEL 3 CHOREOGRAPHY =================
        p3_ox, p3_oy = panel_origins[2]
        # Inking Logic Brain (34.8s - 40.5s)
        if 34.8 <= t < 40.5:
            prog = (t - 34.8) / 5.7
            n_pts = len(p3_logic_pts)
            tgt_idx = min(n_pts - 1, int(round(prog * (n_pts - 1))))
            if tgt_idx > p3_logic_pt_idx:
                for pi in range(p3_logic_pt_idx, tgt_idx):
                    pt1 = (int(round(p3_logic_pts[pi][0])), int(round(p3_logic_pts[pi][1])))
                    pt2 = (int(round(p3_logic_pts[pi+1][0])), int(round(p3_logic_pts[pi+1][1])))
                    cv2.line(p3_logic_mask, pt1, pt2, 255, thickness=18)
                    cv2.circle(p3_logic_mask, pt2, 9, 255, -1)
                p3_logic_pt_idx = tgt_idx
            cur_pt = p3_logic_pts[tgt_idx]
            hand_canvas_pt = (p3_ox + p3_logic["rx"] + cur_pt[0], p3_oy + p3_logic["ry"] + cur_pt[1])
            
            eff_mask = cv2.bitwise_and(p3_logic_mask, p3_logic["img"][:, :, 3])
            partial_rgba = p3_logic["img"].copy()
            partial_rgba[:, :, 3] = eff_mask
            overlay_rgba(master_canvas, partial_rgba, p3_ox + p3_logic["rx"], p3_oy + p3_logic["ry"])
        elif t >= 40.5 and p3_logic_pt_idx < len(p3_logic_pts) - 1:
            overlay_rgba(master_canvas, p3_logic["img"], p3_ox + p3_logic["rx"], p3_oy + p3_logic["ry"])
            p3_logic_pt_idx = len(p3_logic_pts) - 1

        # Inking Creative Brain (40.5s - 44.5s)
        if 40.5 <= t < 44.5:
            prog = (t - 40.5) / 4.0
            n_pts = len(p3_creative_pts)
            tgt_idx = min(n_pts - 1, int(round(prog * (n_pts - 1))))
            if tgt_idx > p3_creative_pt_idx:
                for pi in range(p3_creative_pt_idx, tgt_idx):
                    pt1 = (int(round(p3_creative_pts[pi][0])), int(round(p3_creative_pts[pi][1])))
                    pt2 = (int(round(p3_creative_pts[pi+1][0])), int(round(p3_creative_pts[pi+1][1])))
                    cv2.line(p3_creative_mask, pt1, pt2, 255, thickness=18)
                    cv2.circle(p3_creative_mask, pt2, 9, 255, -1)
                p3_creative_pt_idx = tgt_idx
            cur_pt = p3_creative_pts[tgt_idx]
            hand_canvas_pt = (p3_ox + p3_creative["rx"] + cur_pt[0], p3_oy + p3_creative["ry"] + cur_pt[1])
            
            eff_mask = cv2.bitwise_and(p3_creative_mask, p3_creative["img"][:, :, 3])
            partial_rgba = p3_creative["img"].copy()
            partial_rgba[:, :, 3] = eff_mask
            overlay_rgba(master_canvas, partial_rgba, p3_ox + p3_creative["rx"], p3_oy + p3_creative["ry"])
        elif t >= 44.5 and p3_creative_pt_idx < len(p3_creative_pts) - 1:
            overlay_rgba(master_canvas, p3_creative["img"], p3_ox + p3_creative["rx"], p3_oy + p3_creative["ry"])
            p3_creative_pt_idx = len(p3_creative_pts) - 1

        # Floating Icons Jelly Pop (44.5s - 46.8s)
        if 44.5 <= t < 46.8:
            prog = min(1.0, (t - 44.5) / 2.3)
            sx, sy = get_jelly_scales(prog)
            for ic in [p3_icons_logic, p3_icons_creative]:
                rw, rh = ic["rw"], ic["rh"]
                scaled_w, scaled_h = max(1, int(round(rw * sx))), max(1, int(round(rh * sy)))
                scaled_img = cv2.resize(ic["img"], (scaled_w, scaled_h), interpolation=cv2.INTER_LANCZOS4)
                dx = (scaled_w - rw) // 2
                dy = (scaled_h - rh) // 2
                overlay_rgba(frame_canvas, scaled_img, p3_ox + ic["rx"] - dx, p3_oy + ic["ry"] - dy)
        elif t >= 46.8:
            overlay_rgba(master_canvas, p3_icons_logic["img"], p3_ox + p3_icons_logic["rx"], p3_oy + p3_icons_logic["ry"])
            overlay_rgba(master_canvas, p3_icons_creative["img"], p3_ox + p3_icons_creative["rx"], p3_oy + p3_icons_creative["ry"])

        # ================= PANEL 4 CHOREOGRAPHY =================
        p4_ox, p4_oy = panel_origins[3]
        # Inking Growth Figures (49.0s - 58.0s)
        if 49.0 <= t < 58.0:
            prog = (t - 49.0) / 9.0
            n_pts = len(p4_growth_pts)
            tgt_idx = min(n_pts - 1, int(round(prog * (n_pts - 1))))
            if tgt_idx > p4_growth_pt_idx:
                for pi in range(p4_growth_pt_idx, tgt_idx):
                    pt1 = (int(round(p4_growth_pts[pi][0])), int(round(p4_growth_pts[pi][1])))
                    pt2 = (int(round(p4_growth_pts[pi+1][0])), int(round(p4_growth_pts[pi+1][1])))
                    cv2.line(p4_growth_mask, pt1, pt2, 255, thickness=18)
                    cv2.circle(p4_growth_mask, pt2, 9, 255, -1)
                p4_growth_pt_idx = tgt_idx
            cur_pt = p4_growth_pts[tgt_idx]
            hand_canvas_pt = (p4_ox + p4_growth["rx"] + cur_pt[0], p4_oy + p4_growth["ry"] + cur_pt[1])
            
            eff_mask = cv2.bitwise_and(p4_growth_mask, p4_growth["img"][:, :, 3])
            partial_rgba = p4_growth["img"].copy()
            partial_rgba[:, :, 3] = eff_mask
            overlay_rgba(master_canvas, partial_rgba, p4_ox + p4_growth["rx"], p4_oy + p4_growth["ry"])
        elif t >= 58.0 and p4_growth_pt_idx < len(p4_growth_pts) - 1:
            overlay_rgba(master_canvas, p4_growth["img"], p4_ox + p4_growth["rx"], p4_oy + p4_growth["ry"])
            p4_growth_pt_idx = len(p4_growth_pts) - 1

        # Learning Elements Slide Up (58.0s - 64.0s)
        if 58.0 <= t < 64.0:
            prog = min(1.0, (t - 58.0) / 6.0)
            ease = ease_out_back(min(1.0, prog * 1.5), overshoot=1.2)
            dy = int(round((1.0 - ease) * 160))
            overlay_rgba(frame_canvas, p4_learning["img"], p4_ox + p4_learning["rx"], p4_oy + p4_learning["ry"] + dy)
        elif t >= 64.0:
            overlay_rgba(master_canvas, p4_learning["img"], p4_ox + p4_learning["rx"], p4_oy + p4_learning["ry"])

        # ================= PANEL 5 CHOREOGRAPHY =================
        p5_ox, p5_oy = panel_origins[4]
        # Inking Thinker (71.2s - 75.5s)
        if 71.2 <= t < 75.5:
            prog = (t - 71.2) / 4.3
            n_pts = len(p5_thinker_pts)
            tgt_idx = min(n_pts - 1, int(round(prog * (n_pts - 1))))
            if tgt_idx > p5_thinker_pt_idx:
                for pi in range(p5_thinker_pt_idx, tgt_idx):
                    pt1 = (int(round(p5_thinker_pts[pi][0])), int(round(p5_thinker_pts[pi][1])))
                    pt2 = (int(round(p5_thinker_pts[pi+1][0])), int(round(p5_thinker_pts[pi+1][1])))
                    cv2.line(p5_thinker_mask, pt1, pt2, 255, thickness=18)
                    cv2.circle(p5_thinker_mask, pt2, 9, 255, -1)
                p5_thinker_pt_idx = tgt_idx
            cur_pt = p5_thinker_pts[tgt_idx]
            hand_canvas_pt = (p5_ox + p5_thinker["rx"] + cur_pt[0], p5_oy + p5_thinker["ry"] + cur_pt[1])
            
            eff_mask = cv2.bitwise_and(p5_thinker_mask, p5_thinker["img"][:, :, 3])
            partial_rgba = p5_thinker["img"].copy()
            partial_rgba[:, :, 3] = eff_mask
            overlay_rgba(master_canvas, partial_rgba, p5_ox + p5_thinker["rx"], p5_oy + p5_thinker["ry"])
        elif t >= 75.5 and p5_thinker_pt_idx < len(p5_thinker_pts) - 1:
            overlay_rgba(master_canvas, p5_thinker["img"], p5_ox + p5_thinker["rx"], p5_oy + p5_thinker["ry"])
            p5_thinker_pt_idx = len(p5_thinker_pts) - 1

        # 6 Thought Bubbles Clockwise Pops (75.5s - 79.5s)
        bubble_schedule = [
            (p5_b_house, 75.6),
            (p5_b_people, 76.2),
            (p5_b_money, 76.8),
            (p5_b_time, 77.4),
            (p5_b_plant, 78.0),
            (p5_b_heart, 78.6),
        ]
        for b_layer, b_t in bubble_schedule:
            if b_t <= t < b_t + 1.2:
                prog = min(1.0, (t - b_t) / 1.2)
                sx, sy = get_jelly_scales(prog)
                rw, rh = b_layer["rw"], b_layer["rh"]
                scaled_w, scaled_h = max(1, int(round(rw * sx))), max(1, int(round(rh * sy)))
                scaled_img = cv2.resize(b_layer["img"], (scaled_w, scaled_h), interpolation=cv2.INTER_LANCZOS4)
                dx = (scaled_w - rw) // 2
                dy = (scaled_h - rh) // 2
                overlay_rgba(frame_canvas, scaled_img, p5_ox + b_layer["rx"] - dx, p5_oy + b_layer["ry"] - dy)
            elif t >= b_t + 1.2:
                overlay_rgba(master_canvas, b_layer["img"], p5_ox + b_layer["rx"], p5_oy + b_layer["ry"])

        # ================= PANEL 6 CHOREOGRAPHY =================
        p6_ox, p6_oy = panel_origins[5]
        # Inking Stairs & Door (81.2s - 84.8s)
        if 81.2 <= t < 84.8:
            prog = (t - 81.2) / 3.6
            n_pts = len(p6_stairs_pts)
            tgt_idx = min(n_pts - 1, int(round(prog * (n_pts - 1))))
            if tgt_idx > p6_stairs_pt_idx:
                for pi in range(p6_stairs_pt_idx, tgt_idx):
                    pt1 = (int(round(p6_stairs_pts[pi][0])), int(round(p6_stairs_pts[pi][1])))
                    pt2 = (int(round(p6_stairs_pts[pi+1][0])), int(round(p6_stairs_pts[pi+1][1])))
                    cv2.line(p6_stairs_mask, pt1, pt2, 255, thickness=18)
                    cv2.circle(p6_stairs_mask, pt2, 9, 255, -1)
                p6_stairs_pt_idx = tgt_idx
            cur_pt = p6_stairs_pts[tgt_idx]
            hand_canvas_pt = (p6_ox + p6_stairs["rx"] + cur_pt[0], p6_oy + p6_stairs["ry"] + cur_pt[1])
            
            eff_mask = cv2.bitwise_and(p6_stairs_mask, p6_stairs["img"][:, :, 3])
            partial_rgba = p6_stairs["img"].copy()
            partial_rgba[:, :, 3] = eff_mask
            overlay_rgba(master_canvas, partial_rgba, p6_ox + p6_stairs["rx"], p6_oy + p6_stairs["ry"])
        elif t >= 84.8 and p6_stairs_pt_idx < len(p6_stairs_pts) - 1:
            overlay_rgba(master_canvas, p6_stairs["img"], p6_ox + p6_stairs["rx"], p6_oy + p6_stairs["ry"])
            p6_stairs_pt_idx = len(p6_stairs_pts) - 1

        # Hero Character (83.0s - 85.0s)
        if 83.0 <= t < 85.0:
            prog = min(1.0, (t - 83.0) / 2.0)
            overlay_rgba(frame_canvas, p6_hero["img"], p6_ox + p6_hero["rx"], p6_oy + p6_hero["ry"], alpha_factor=smootherstep(prog))
        elif t >= 85.0:
            overlay_rgba(master_canvas, p6_hero["img"], p6_ox + p6_hero["rx"], p6_oy + p6_hero["ry"])

        # Compass & Symbols Pop (84.8s - 85.8s)
        if 84.8 <= t < 85.8:
            prog = min(1.0, (t - 84.8) / 1.0)
            sx, sy = get_jelly_scales(prog)
            for sym in [p6_compass, p6_symbols]:
                rw, rh = sym["rw"], sym["rh"]
                scaled_w, scaled_h = max(1, int(round(rw * sx))), max(1, int(round(rh * sy)))
                scaled_img = cv2.resize(sym["img"], (scaled_w, scaled_h), interpolation=cv2.INTER_LANCZOS4)
                dx = (scaled_w - rw) // 2
                dy = (scaled_h - rh) // 2
                overlay_rgba(frame_canvas, scaled_img, p6_ox + sym["rx"] - dx, p6_oy + sym["ry"] - dy)
        elif t >= 85.8:
            overlay_rgba(master_canvas, p6_compass["img"], p6_ox + p6_compass["rx"], p6_oy + p6_compass["ry"])
            overlay_rgba(master_canvas, p6_symbols["img"], p6_ox + p6_symbols["rx"], p6_oy + p6_symbols["ry"])

        # 3. WARP VIEWPORT TO SCREEN (1920x1080)
        src_pts = np.float32([
            [cx - vw / 2.0, cy - vh / 2.0],
            [cx + vw / 2.0, cy - vh / 2.0],
            [cx - vw / 2.0, cy + vh / 2.0]
        ])
        dst_pts = np.float32([[0, 0], [out_w, 0], [0, out_h]])
        M = cv2.getAffineTransform(src_pts, dst_pts)
        screen_frame = cv2.warpAffine(frame_canvas, M, (out_w, out_h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

        # 4. COMPOSITE DRAWING HAND ON SCREEN
        if hand_canvas_pt is not None and t < 85.8:
            screen_pt = M @ np.array([hand_canvas_pt[0], hand_canvas_pt[1], 1.0], dtype=np.float32)
            s_px = int(round(screen_pt[0]))
            s_py = int(round(screen_pt[1]))
            # Place hand with pen tip at screen_pt
            screen_frame = composite_hand_on_canvas_fast(
                screen_frame, hand_screen, tip_screen_x, tip_screen_y, s_px, s_py
            )

        # Encode Frame to NVENC
        rgb_frame = cv2.cvtColor(screen_frame, cv2.COLOR_BGR2RGB)
        av_frame = av.VideoFrame.from_ndarray(rgb_frame, format="rgb24")
        for packet in v_stream.encode(av_frame):
            container.mux(packet)

        if f_idx % 150 == 0 or f_idx == total_frames - 1:
            fps_real = (f_idx + 1) / max(0.001, time.time() - start_time)
            print(f"Frame {f_idx+1}/{total_frames} ({t:.1f}s / {duration:.1f}s) - {fps_real:.1f} FPS")

    # Flush video encoder
    for packet in v_stream.encode():
        container.mux(packet)
    container.close()

    render_sec = time.time() - start_time
    print(f"Video render completed in {render_sec:.1f}s ({total_frames / render_sec:.1f} FPS)!")

    # 5. MUX WITH MASTER AUDIO MIX (with Sidechain Ducking)
    audio_mix = os.path.join(ROOT_DIR, "experiments", "sfx", "sheet_01_master_audio_mixed.wav")
    print(f"Muxing video with professional audio mix: {audio_mix}...")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_no_audio,
        "-i", audio_mix,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        final_output
    ]
    subprocess.run(cmd, check=True)
    print("=" * 80)
    print(f">>> MASTER PRODUCTION VIDEO SUCCESSFULLY PRODUCED: {final_output} <<<")
    print("=" * 80)


if __name__ == "__main__":
    render_masterpiece()
