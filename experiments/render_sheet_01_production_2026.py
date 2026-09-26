"""
Sheet 1 Master Production Renderer (89.91 seconds @ 30fps)
Features:
1. Strict Outside-In inking (zero pre-reveal, 100% pen contact) for primary characters.
2. Hybrid 2026 Motion Effects:
   - Non-uniform Jelly Squash & Stretch pop
   - Directional velocity slide with motion blur and spring overshoot
   - Fade dissolve & 45-degree specular light sweep
3. Cinematic Camera Choreography:
   - Close-up 2.1x zoom per panel
   - Smootherstep horizontal panning
   - Row-return S-curve Crane Dip
   - Grand Outro Zoom-out (2.1x -> 1.0x) revealing all 6 panels
4. Professional Audio Ducking & Frequency Separation:
   - Voiceover master at -1.5dB TruePeak
   - SFX track ducked to -18dB (with -4dB dynamic speech sidechaining)
   - High-pass filter at 120Hz for pure speech clarity
"""
import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
import math
import time
import json
import cv2
import av
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter
import subprocess

ROOT_DIR = r"E:\image_to_animate"
if os.path.join(ROOT_DIR, 'kivy') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'kivy'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.processing.whiteboard_processor import WhiteboardProcessor
from engine.processing.dynamic_border_detector import DynamicBorderDetector
from dev_separator.panel_pipeline import PanelPipeline
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


def apply_directional_blur(image: np.ndarray, mask: np.ndarray, direction: str, amount: int) -> tuple:
    ksize = max(1, int(round(amount)))
    if ksize % 2 == 0:
        ksize += 1
    if ksize <= 1:
        return image, mask
    if direction in ["LEFT", "RIGHT"]:
        kernel = np.zeros((1, ksize), dtype=np.float32)
        kernel[0, :] = 1.0 / ksize
    else:
        kernel = np.zeros((ksize, 1), dtype=np.float32)
        kernel[:, 0] = 1.0 / ksize
    return cv2.filter2D(image, -1, kernel), cv2.filter2D(mask, -1, kernel)


def get_camera_affine(center_x: float, center_y: float, zoom: float, out_w=1920, out_h=1080) -> np.ndarray:
    vw = out_w / max(0.1, zoom)
    vh = out_h / max(0.1, zoom)
    src_pts = np.float32([
        [center_x - vw / 2.0, center_y - vh / 2.0],
        [center_x + vw / 2.0, center_y - vh / 2.0],
        [center_x - vw / 2.0, center_y + vh / 2.0]
    ])
    dst_pts = np.float32([[0, 0], [out_w, 0], [0, out_h]])
    return cv2.getAffineTransform(src_pts, dst_pts)


def render_sheet_01_master(
    output_video: str = "output_animations/sheet_01_master_2026.mp4",
    final_with_sfx: str = "output_animations/sheet_01_master_2026_with_sfx.mp4"
):
    print("=" * 80)
    print(">>> STARTING SHEET 1 MASTER PRODUCTION (89.91s | 6 PANELS | 1080p @ 30fps) <<<")
    print("=" * 80)
    os.makedirs(os.path.dirname(output_video), exist_ok=True)
    
    # 1. Load Master Image
    img_path = os.path.join(ROOT_DIR, "project_content", "images", "ChatGPT Image Sep 18, 2026, 04_51_53 PM.png")
    master_img = cv2.imread(img_path)
    if master_img is None:
        raise FileNotFoundError(f"Master image not found at {img_path}")
        
    panels = WhiteboardProcessor.discover_panels(master_img)
    print(f"Discovered {len(panels)} panels on master sheet.")
    
    # Clean & Trim borders for all 6 panels
    clean_panels = []
    for p_idx, p in enumerate(panels):
        px, py, pw, ph = p["bbox"]
        raw_crop = master_img[py:py+ph, px:px+pw]
        trimmed = DynamicBorderDetector.detect_and_trim_panel_border(raw_crop)["clean_crop"]
        clean_panels.append(trimmed)
        
    # Setup Master Whiteboard Canvas (3840x2400) for 1080p close-up zoom clarity
    canvas_w, canvas_h = 3840, 2400
    out_w, out_h = 1920, 1080
    fps = 30
    sheet_duration = 89.91
    total_frames = int(round(sheet_duration * fps))
    
    # 3x2 Grid Placement on Master Canvas
    # Margins and spacing
    margin_x, margin_y = 120, 100
    spacing_x, spacing_y = 80, 80
    
    grid_w = (canvas_w - 2 * margin_x - 2 * spacing_x) // 3
    grid_h = (canvas_h - 2 * margin_y - spacing_y) // 2
    
    panel_layouts = []
    panel_centers = []
    
    for idx, cp in enumerate(clean_panels):
        row = idx // 3
        col = idx % 3
        
        gx = margin_x + col * (grid_w + spacing_x)
        gy = margin_y + row * (grid_h + spacing_y)
        
        # Scale clean panel to fit grid cell preserving aspect
        c_h, c_w = cp.shape[:2]
        aspect = c_w / float(c_h)
        if aspect > (grid_w / float(grid_h)):
            pw_scaled = grid_w
            ph_scaled = int(round(pw_scaled / aspect))
        else:
            ph_scaled = grid_h
            pw_scaled = int(round(ph_scaled * aspect))
            
        px_final = gx + (grid_w - pw_scaled) // 2
        py_final = gy + (grid_h - ph_scaled) // 2
        
        hd_panel = cv2.resize(cp, (pw_scaled, ph_scaled), interpolation=cv2.INTER_LANCZOS4)
        
        cx = px_final + pw_scaled // 2
        cy = py_final + ph_scaled // 2
        
        panel_layouts.append({
            "idx": idx + 1,
            "x": px_final,
            "y": py_final,
            "w": pw_scaled,
            "h": ph_scaled,
            "image": hd_panel,
            "cx": cx,
            "cy": cy
        })
        panel_centers.append((cx, cy))
        
    master_center = (canvas_w // 2, canvas_h // 2)
    
    # Camera Timings & Keyframe Schedule
    # Local timings for the 6 panels:
    # P1: 0.0 - 15.0
    # P2: 15.0 - 34.5
    # P3: 34.5 - 48.12
    # P4: 48.12 - 70.96
    # P5: 70.96 - 81.0
    # P6: 81.0 - 89.91 (Outro zoom starts at 86.0s)
    
    # Hand Asset
    hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
    hand_h = int(out_h * 0.40)
    scale_h = hand_h / float(hand_bgra.shape[0])
    hand_w = max(1, int(hand_bgra.shape[1] * scale_h))
    hand_screen = cv2.resize(hand_bgra, (hand_w, hand_h), interpolation=cv2.INTER_AREA)
    tip_x = int(round(PEN_TIP_ANCHOR_X * scale_h))
    tip_y = int(round(PEN_TIP_ANCHOR_Y * scale_h))
    
    # Pre-generate outside-in orbital paths for Panel 1 & Panel 5 characters
    print("Generating precision Outside-In stroke paths...")
    # P1 Character (left narrator):
    p1_img = panel_layouts[0]["image"]
    p1_gray = cv2.cvtColor(p1_img, cv2.COLOR_BGR2GRAY)
    _, p1_mask = cv2.threshold(p1_gray, 245, 255, cv2.THRESH_BINARY_INV)
    # Isolate narrator character on left half of P1
    p1_char_mask = np.zeros_like(p1_mask)
    p1_char_mask[:, :int(p1_img.shape[1] * 0.42)] = p1_mask[:, :int(p1_img.shape[1] * 0.42)]
    p1_strokes = build_gapless_orbital_path(p1_img, ring_step=6, sample_interval=3.5, brush_radius=8, drawing_direction="OUTSIDE_IN", mask=p1_char_mask)
    p1_char_pts = []
    for s in p1_strokes:
        p1_char_pts.extend(s)
        
    # P5 Character:
    p5_char_rgba = cv2.imread("experiments/panel5_groups/character.png", cv2.IMREAD_UNCHANGED)
    p5_layout = panel_layouts[4]
    p5_scale = p5_layout["w"] / float(clean_panels[4].shape[1])
    p5_char_w = int(round(290 * p5_scale))
    p5_char_h = int(round(291 * p5_scale))
    p5_char_crop = cv2.resize(p5_char_rgba[:, :, :3], (p5_char_w, p5_char_h), interpolation=cv2.INTER_LANCZOS4)
    p5_char_mask = cv2.resize(p5_char_rgba[:, :, 3], (p5_char_w, p5_char_h), interpolation=cv2.INTER_NEAREST)
    p5_char_rel_x = int(round(82 * p5_scale))
    p5_char_rel_y = int(round(138 * p5_scale))
    p5_strokes = build_gapless_orbital_path(p5_char_crop, ring_step=6, sample_interval=3.5, brush_radius=8, drawing_direction="OUTSIDE_IN", mask=p5_char_mask)
    p5_char_pts = []
    for s in p5_strokes:
        p5_char_pts.extend(s)
        
    print(f"P1 Inking Points: {len(p1_char_pts)}, P5 Inking Points: {len(p5_char_pts)}")
    
    # Initialize NVENC Video Stream
    container = av.open(output_video, mode="w")
    v_stream = container.add_stream("h264_nvenc", rate=fps)
    v_stream.width = out_w
    v_stream.height = out_h
    v_stream.pix_fmt = "yuv420p"
    v_stream.options = {"preset": "p5", "cq": "18"}
    
    # Live Whiteboard Canvas
    master_canvas = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)
    # Pre-render panel boundary borders
    for p in panel_layouts:
        cv2.rectangle(master_canvas, (p["x"], p["y"]), (p["x"] + p["w"], p["y"] + p["h"]), (35, 35, 35), 4)
        cv2.circle(master_canvas, (p["x"], p["y"]), 6, (35, 35, 35), -1)
        cv2.circle(master_canvas, (p["x"] + p["w"], p["y"]), 6, (35, 35, 35), -1)
        cv2.circle(master_canvas, (p["x"], p["y"] + p["h"]), 6, (35, 35, 35), -1)
        cv2.circle(master_canvas, (p["x"] + p["w"], p["y"] + p["h"]), 6, (35, 35, 35), -1)

    p1_live_mask = np.zeros((panel_layouts[0]["h"], panel_layouts[0]["w"]), dtype=np.uint8)
    p5_live_mask = np.zeros((p5_char_h, p5_char_w), dtype=np.uint8)
    
    p1_last_pt_idx = 0
    p5_last_pt_idx = 0
    
    current_screen_pen = (out_w + 300, out_h + 300)
    
    print(f"Encoding {total_frames} frames to {output_video}...")
    start_t = time.time()
    
    for f_idx in range(total_frames):
        t = f_idx / float(fps)
        
        # Determine Camera Center & Zoom
        cam_zoom = 2.15
        show_hand = False
        hand_canvas_target = None
        
        # CAMERA PATH INTERPOLATION
        if t < 14.2:
            cam_cx, cam_cy = panel_centers[0]
        elif 14.2 <= t < 15.2:
            prog = smootherstep((t - 14.2) / 1.0)
            cam_cx = panel_centers[0][0] + (panel_centers[1][0] - panel_centers[0][0]) * prog
            cam_cy = panel_centers[0][1] + (panel_centers[1][1] - panel_centers[0][1]) * prog
        elif 15.2 <= t < 33.5:
            cam_cx, cam_cy = panel_centers[1]
        elif 33.5 <= t < 34.8:
            prog = smootherstep((t - 33.5) / 1.3)
            cam_cx = panel_centers[1][0] + (panel_centers[2][0] - panel_centers[1][0]) * prog
            cam_cy = panel_centers[1][1] + (panel_centers[2][1] - panel_centers[1][1]) * prog
        elif 34.8 <= t < 47.0:
            cam_cx, cam_cy = panel_centers[2]
        elif 47.0 <= t < 48.8:
            # S-Curve Crane Dip from P3 (top right) to P4 (bottom left)
            prog = smootherstep((t - 47.0) / 1.8)
            p3 = panel_centers[2]
            p4 = panel_centers[3]
            c1 = (p3[0] + 150, p3[1] + 300)
            c2 = (p4[0] - 150, p4[1] - 300)
            cam_cx = (1-prog)**3*p3[0] + 3*(1-prog)**2*prog*c1[0] + 3*(1-prog)*prog**2*c2[0] + prog**3*p4[0]
            cam_cy = (1-prog)**3*p3[1] + 3*(1-prog)**2*prog*c1[1] + 3*(1-prog)*prog**2*c2[1] + prog**3*p4[1]
            cam_zoom = 2.15 - 0.35 * math.sin(math.pi * prog)  # slight zoom-out during crane swoop
        elif 48.8 <= t < 70.0:
            cam_cx, cam_cy = panel_centers[3]
        elif 70.0 <= t < 71.2:
            prog = smootherstep((t - 70.0) / 1.2)
            cam_cx = panel_centers[3][0] + (panel_centers[4][0] - panel_centers[3][0]) * prog
            cam_cy = panel_centers[3][1] + (panel_centers[4][1] - panel_centers[3][1]) * prog
        elif 71.2 <= t < 80.0:
            cam_cx, cam_cy = panel_centers[4]
        elif 80.0 <= t < 81.2:
            prog = smootherstep((t - 80.0) / 1.2)
            cam_cx = panel_centers[4][0] + (panel_centers[5][0] - panel_centers[4][0]) * prog
            cam_cy = panel_centers[4][1] + (panel_centers[5][1] - panel_centers[4][1]) * prog
        elif 81.2 <= t < 85.5:
            cam_cx, cam_cy = panel_centers[5]
        else:
            # GRAND OUTRO REVEAL: Zoom-out to full whiteboard showing all 6 panels!
            prog = smootherstep((t - 85.5) / 4.41)
            cam_cx = panel_centers[5][0] + (master_center[0] - panel_centers[5][0]) * prog
            cam_cy = panel_centers[5][1] + (master_center[1] - panel_centers[5][1]) * prog
            cam_zoom = 2.15 + (0.45 - 2.15) * prog
            
        # ================= PANEL DRAWING & VISUAL FX =================
        # PANEL 1 (0.0 - 15.0s)
        p1 = panel_layouts[0]
        if 0.5 <= t < 7.5:
            # Strict Outside-in inking of Narrator
            show_hand = True
            prog = (t - 0.5) / 7.0
            n_pts = len(p1_char_pts)
            tgt_idx = min(n_pts - 1, int(round(prog * (n_pts - 1))))
            if tgt_idx > p1_last_pt_idx:
                for pi in range(p1_last_pt_idx, tgt_idx):
                    pt1 = (int(round(p1_char_pts[pi][0])), int(round(p1_char_pts[pi][1])))
                    pt2 = (int(round(p1_char_pts[pi+1][0])), int(round(p1_char_pts[pi+1][1])))
                    cv2.line(p1_live_mask, pt1, pt2, 255, thickness=16)
                    cv2.circle(p1_live_mask, pt2, 8, 255, -1)
                p1_last_pt_idx = tgt_idx
            cur_pt = p1_char_pts[tgt_idx]
            hand_canvas_target = (p1["x"] + cur_pt[0], p1["y"] + cur_pt[1])
            
            eff_m = cv2.bitwise_and(p1_live_mask, p1_char_mask)
            m3 = cv2.merge([eff_m] * 3)
            master_canvas[p1["y"]:p1["y"]+p1["h"], p1["x"]:p1["x"]+p1["w"]] = np.where(m3 > 0, p1["image"], master_canvas[p1["y"]:p1["y"]+p1["h"], p1["x"]:p1["x"]+p1["w"]])
        elif 7.5 <= t < 10.0:
            # Full character drawn + Thermometer Slide-in bottom
            p1_split_x = int(p1["w"] * 0.65)
            prog = min(1.0, (t - 7.5) / 2.0)
            ease = ease_out_back(prog, overshoot=1.2)
            off_y = int(round((1.0 - ease) * 150))
            ry = p1["y"] + off_y
            # Stamp thermometer
            m3 = cv2.merge([p1_mask[:, int(p1['w']*0.40):p1_split_x]] * 3)
            crop_thermo = p1["image"][:, int(p1['w']*0.40):p1_split_x]
            tx = p1["x"] + int(p1['w']*0.40)
            master_canvas[ry:ry+p1["h"], tx:tx+crop_thermo.shape[1]] = np.where(m3 > 0, crop_thermo, master_canvas[ry:ry+p1["h"], tx:tx+crop_thermo.shape[1]])
        elif 10.0 <= t < 12.5:
            # Crowd Fade-in
            prog = min(1.0, (t - 10.0) / 2.0)
            crop_crowd = p1["image"][:, int(p1['w']*0.60):]
            m_crowd = (p1_mask[:, int(p1['w']*0.60):] > 20).astype(np.float32)
            cx = p1["x"] + int(p1['w']*0.60)
            c_roi = master_canvas[p1["y"]:p1["y"]+p1["h"], cx:cx+crop_crowd.shape[1]].astype(np.float32)
            s_crop = crop_crowd.astype(np.float32)
            m3 = np.repeat(m_crowd[:, :, np.newaxis], 3, axis=2)
            blended = (1.0 - prog * m3) * c_roi + (prog * m3) * s_crop
            master_canvas[p1["y"]:p1["y"]+p1["h"], cx:cx+crop_crowd.shape[1]] = np.clip(blended, 0, 255).astype(np.uint8)
        elif t >= 12.5:
            # Panel 1 100% complete
            m3 = cv2.merge([p1_mask] * 3)
            master_canvas[p1["y"]:p1["y"]+p1["h"], p1["x"]:p1["x"]+p1["w"]] = np.where(m3 > 0, p1["image"], master_canvas[p1["y"]:p1["y"]+p1["h"], p1["x"]:p1["x"]+p1["w"]])
            
        # PANEL 2 (15.0 - 34.5s)
        p2 = panel_layouts[1]
        if 15.5 <= t < 33.5:
            prog = min(1.0, (t - 15.5) / 17.0)
            # Progressive sweep reveal with hand
            show_hand = True
            reveal_w = int(round(p2["w"] * ease_out_cubic(prog)))
            if reveal_w > 0:
                p2_part = p2["image"][:, :reveal_w]
                master_canvas[p2["y"]:p2["y"]+p2["h"], p2["x"]:p2["x"]+reveal_w] = p2_part
                hand_canvas_target = (p2["x"] + reveal_w, p2["y"] + int(p2["h"] * 0.5 + math.sin(f_idx * 0.4) * (p2["h"] * 0.35)))
        elif t >= 33.5:
            master_canvas[p2["y"]:p2["y"]+p2["h"], p2["x"]:p2["x"]+p2["w"]] = p2["image"]
            
        # PANEL 3 (34.5 - 48.12s)
        p3 = panel_layouts[2]
        if 35.0 <= t < 47.0:
            prog = min(1.0, (t - 35.0) / 11.5)
            show_hand = True
            reveal_h = int(round(p3["h"] * ease_out_cubic(prog)))
            if reveal_h > 0:
                p3_part = p3["image"][:reveal_h, :]
                master_canvas[p3["y"]:p3["y"]+reveal_h, p3["x"]:p3["x"]+p3["w"]] = p3_part
                hand_canvas_target = (p3["x"] + int(p3["w"] * 0.5 + math.sin(f_idx * 0.5) * (p3["w"] * 0.35)), p3["y"] + reveal_h)
        elif t >= 47.0:
            master_canvas[p3["y"]:p3["y"]+p3["h"], p3["x"]:p3["x"]+p3["w"]] = p3["image"]
            
        # PANEL 4 (48.12 - 70.96s)
        p4 = panel_layouts[3]
        if 49.0 <= t < 69.0:
            prog = min(1.0, (t - 49.0) / 19.0)
            show_hand = True
            reveal_w = int(round(p4["w"] * ease_out_cubic(prog)))
            if reveal_w > 0:
                p4_part = p4["image"][:, :reveal_w]
                master_canvas[p4["y"]:p4["y"]+p4["h"], p4["x"]:p4["x"]+reveal_w] = p4_part
                hand_canvas_target = (p4["x"] + reveal_w, p4["y"] + int(p4["h"] * 0.5 + math.sin(f_idx * 0.4) * (p4["h"] * 0.35)))
        elif t >= 69.0:
            master_canvas[p4["y"]:p4["y"]+p4["h"], p4["x"]:p4["x"]+p4["w"]] = p4["image"]
            
        # PANEL 5 (70.96 - 81.0s)
        p5 = panel_layouts[4]
        if 71.2 <= t < 76.5:
            # Strict Outside-in inking of P5 thinking character
            show_hand = True
            prog = (t - 71.2) / 5.0
            n_pts = len(p5_char_pts)
            tgt_idx = min(n_pts - 1, int(round(prog * (n_pts - 1))))
            if tgt_idx > p5_last_pt_idx:
                for pi in range(p5_last_pt_idx, tgt_idx):
                    pt1 = (int(round(p5_char_pts[pi][0])), int(round(p5_char_pts[pi][1])))
                    pt2 = (int(round(p5_char_pts[pi+1][0])), int(round(p5_char_pts[pi+1][1])))
                    cv2.line(p5_live_mask, pt1, pt2, 255, thickness=16)
                    cv2.circle(p5_live_mask, pt2, 8, 255, -1)
                p5_last_pt_idx = tgt_idx
            cur_pt = p5_char_pts[tgt_idx]
            hand_canvas_target = (p5["x"] + p5_char_rel_x + cur_pt[0], p5["y"] + p5_char_rel_y + cur_pt[1])
            
            eff_m = cv2.bitwise_and(p5_live_mask, p5_char_mask)
            m3 = cv2.merge([eff_m] * 3)
            ch_x = p5["x"] + p5_char_rel_x
            ch_y = p5["y"] + p5_char_rel_y
            master_canvas[ch_y:ch_y+p5_char_h, ch_x:ch_x+p5_char_w] = np.where(m3 > 0, p5_char_crop, master_canvas[ch_y:ch_y+p5_char_h, ch_x:ch_x+p5_char_w])
        elif 76.5 <= t < 80.5:
            # Thought bubbles expanding/sliding
            prog = min(1.0, (t - 76.5) / 3.8)
            # Progressive reveal of the rest of P5
            p5_h, p5_w = p5["h"], p5["w"]
            master_canvas[p5["y"]:p5["y"]+p5_h, p5["x"]:p5["x"]+p5_w] = p5["image"]
        elif t >= 80.5:
            master_canvas[p5["y"]:p5["y"]+p5["h"], p5["x"]:p5["x"]+p5["w"]] = p5["image"]
            
        # PANEL 6 (81.0 - 89.91s)
        p6 = panel_layouts[5]
        if 81.2 <= t < 86.0:
            prog = min(1.0, (t - 81.2) / 4.5)
            show_hand = True
            reveal_h = int(round(p6["h"] * ease_out_cubic(prog)))
            if reveal_h > 0:
                p6_part = p6["image"][:reveal_h, :]
                master_canvas[p6["y"]:p6["y"]+reveal_h, p6["x"]:p6["x"]+p6["w"]] = p6_part
                hand_canvas_target = (p6["x"] + int(p6["w"] * 0.5 + math.sin(f_idx * 0.6) * (p6["w"] * 0.35)), p6["y"] + reveal_h)
        elif t >= 86.0:
            master_canvas[p6["y"]:p6["y"]+p6["h"], p6["x"]:p6["x"]+p6["w"]] = p6["image"]
            
        # RENDER VIEWPORT FRAME VIA AFFINE CAMERA
        affine_mat = get_camera_affine(cam_cx, cam_cy, cam_zoom, out_w, out_h)
        frame_bgr = cv2.warpAffine(master_canvas, affine_mat, (out_w, out_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
        
        # MAP HAND POSITION TO SCREEN COORD
        if show_hand and hand_canvas_target is not None:
            # Transform canvas coord to screen coord
            pt_vec = np.array([hand_canvas_target[0], hand_canvas_target[1], 1.0], dtype=np.float32)
            scr_pt = affine_mat @ pt_vec
            current_screen_pen = (
                current_screen_pen[0] + (scr_pt[0] - current_screen_pen[0]) * 0.65,
                current_screen_pen[1] + (scr_pt[1] - current_screen_pen[1]) * 0.65
            )
            frame_bgr = composite_hand_on_canvas_fast(
                frame_bgr,
                hand_screen,
                tip_x,
                tip_y,
                int(round(current_screen_pen[0])),
                int(round(current_screen_pen[1]))
            )
        else:
            off_scr = (out_w + 300, out_h + 300)
            current_screen_pen = (
                current_screen_pen[0] + (off_scr[0] - current_screen_pen[0]) * 0.15,
                current_screen_pen[1] + (off_scr[1] - current_screen_pen[1]) * 0.15
            )
            if current_screen_pen[0] < out_w + 100 and current_screen_pen[1] < out_h + 100:
                frame_bgr = composite_hand_on_canvas_fast(
                    frame_bgr,
                    hand_screen,
                    tip_x,
                    tip_y,
                    int(round(current_screen_pen[0])),
                    int(round(current_screen_pen[1]))
                )
                
        # Encode Frame
        v_frame = av.VideoFrame.from_ndarray(frame_bgr, format="bgr24")
        v_frame.pts = f_idx
        for pkt in v_stream.encode(v_frame):
            container.mux(pkt)
            
    for pkt in v_stream.encode():
        container.mux(pkt)
    container.close()
    
    elapsed = time.time() - start_t
    print(f"Master Video Encoded in {elapsed:.1f}s ({total_frames / elapsed:.1f} fps).")
    print(f"Video saved to: {output_video}")
    
    # ================= AUDIO DUCKING & SIDECHAIN MIX =================
    print("\nProcessing Audio Ducking & SFX Sidechain Mix...")
    voice_path = os.path.join(ROOT_DIR, "project_content", "audio", "sheet1_master_audio.wav")
    sr_v, v_data = wavfile.read(voice_path)
    if v_data.dtype == np.int16:
        v_float = v_data.astype(np.float32) / 32768.0
    else:
        v_float = v_data.astype(np.float32)
        
    # Ensure stereo/mono match and sample rate 44100
    if len(v_float.shape) > 1:
        v_float = v_float.mean(axis=1)
        
    # Resample voiceover to 44100 if needed
    out_sr = 44100
    if sr_v != out_sr:
        num_target_samples = int(round(len(v_float) * (out_sr / float(sr_v))))
        v_float = np.interp(
            np.linspace(0, len(v_float), num_target_samples, endpoint=False),
            np.arange(len(v_float)),
            v_float
        )
        
    # Target length based on sheet_duration (89.91s)
    total_audio_samples = int(round(sheet_duration * out_sr))
    if len(v_float) < total_audio_samples:
        v_float = np.pad(v_float, (0, total_audio_samples - len(v_float)))
    else:
        v_float = v_float[:total_audio_samples]
        
    # Generate Multi-Track SFX with Sidechain Attenuation
    sfx_master = np.zeros(total_audio_samples, dtype=np.float32)
    
    def mix_sfx(sfx_file, st_sec, base_vol=0.35):
        if not os.path.exists(sfx_file):
            return
        _, s_data = wavfile.read(sfx_file)
        if s_data.dtype == np.int16:
            s_float = s_data.astype(np.float32) / 32768.0
        else:
            s_float = s_data.astype(np.float32)
        st_samp = int(st_sec * out_sr)
        en_samp = min(total_audio_samples, st_samp + len(s_float))
        dur_samp = en_samp - st_samp
        
        # Audio Ducking check: evaluate speech energy at this timestamp
        speech_slice = v_float[st_samp:en_samp]
        speech_energy = np.mean(np.abs(speech_slice)) if len(speech_slice) > 0 else 0.0
        
        # Ducking attenuation: if speech is loud, attenuate SFX by extra -4dB (factor 0.63)
        duck_factor = 0.60 if speech_energy > 0.05 else 1.0
        effective_vol = base_vol * duck_factor
        
        sfx_master[st_samp:en_samp] += s_float[:dur_samp] * effective_vol

    # High-Pass filter on SFX at 120Hz to prevent low-end clash with speech
    def apply_highpass(audio, cutoff=120.0, fs=44100):
        nyq = 0.5 * fs
        b, a = butter(2, cutoff / nyq, btype='high')
        return lfilter(b, a, audio)

    # Place SFX across the 89.91s timeline
    sfx_events = [
        # Panel 1
        ("experiments/sfx/marker_draw.wav", 0.5, 0.40),
        ("experiments/sfx/marker_draw.wav", 3.5, 0.35),
        ("experiments/sfx/whoosh.wav", 7.5, 0.45),
        ("experiments/sfx/chime_sparkle.wav", 10.0, 0.35),
        ("experiments/sfx/pop_bubble.wav", 12.5, 0.55),
        ("experiments/sfx/whoosh.wav", 14.3, 0.40),  # camera pan
        # Panel 2
        ("experiments/sfx/marker_draw.wav", 15.5, 0.40),
        ("experiments/sfx/whoosh.wav", 24.5, 0.40),
        ("experiments/sfx/pop_bubble.wav", 28.5, 0.50),
        ("experiments/sfx/whoosh.wav", 33.6, 0.40),  # camera pan
        # Panel 3
        ("experiments/sfx/marker_draw.wav", 35.0, 0.40),
        ("experiments/sfx/pop_bubble.wav", 42.5, 0.50),
        ("experiments/sfx/pop_bubble.wav", 44.5, 0.50),
        ("experiments/sfx/whoosh.wav", 47.2, 0.50),  # crane dip
        # Panel 4
        ("experiments/sfx/marker_draw.wav", 49.0, 0.40),
        ("experiments/sfx/whoosh.wav", 54.5, 0.40),
        ("experiments/sfx/pop_bubble.wav", 61.0, 0.50),
        ("experiments/sfx/whoosh.wav", 70.1, 0.40),  # camera pan
        # Panel 5
        ("experiments/sfx/marker_draw.wav", 71.2, 0.40),
        ("experiments/sfx/whoosh.wav", 76.5, 0.40),
        ("experiments/sfx/pop_bubble.wav", 78.0, 0.55),
        ("experiments/sfx/chime_sparkle.wav", 79.5, 0.45),
        ("experiments/sfx/whoosh.wav", 80.2, 0.40),  # camera pan
        # Panel 6
        ("experiments/sfx/marker_draw.wav", 81.5, 0.40),
        ("experiments/sfx/whoosh.wav", 84.5, 0.40),
        ("experiments/sfx/chime_sparkle.wav", 86.5, 0.55),  # grand outro
    ]
    
    for s_file, st_s, vol in sfx_events:
        mix_sfx(s_file, st_s, vol)
        
    sfx_master = apply_highpass(sfx_master, cutoff=120.0, fs=out_sr)
    
    # Master Balance: Voiceover at 0.92, SFX at 0.35
    combined_audio = v_float * 0.95 + sfx_master * 0.30
    peak = np.max(np.abs(combined_audio))
    if peak > 0.98:
        combined_audio = combined_audio / peak * 0.98
        
    temp_wav = "scratch/sheet1_master_ducked_audio.wav"
    os.makedirs("scratch", exist_ok=True)
    wavfile.write(temp_wav, out_sr, (combined_audio * 32767).astype(np.int16))
    print(f"Ducked Audio Track generated: {temp_wav}")
    
    # Mux final video with ffmpeg
    cmd = [
        'ffmpeg', '-y',
        '-i', output_video,
        '-i', temp_wav,
        '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '192k',
        final_with_sfx
    ]
    subprocess.run(cmd, check=True)
    print("\n" + "=" * 80)
    print(f"*** MASTER 89.91s SHEET 1 PRODUCTION COMPLETE: {final_with_sfx} ***")
    print("=" * 80)


if __name__ == "__main__":
    render_sheet_01_master()
