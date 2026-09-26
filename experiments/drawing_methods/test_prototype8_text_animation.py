"""
Phase 6 — Prototype 8 Medial Skeleton Text Handwriting Engine
File: experiments/drawing_methods/test_prototype8_text_animation.py

Implements the EXACT text handwriting animation method from:
E:\\image_to_animate\\tools\\prototype_8\\auto_animate_whiteboard.py (auto_master_video.mp4)

Features:
1. 1-Pixel Medial Axis Skeleton Extraction (morphological thinning).
2. Natural cursive stroke path tracing (RTL for Arabic, starting top-right of each stroke).
3. Synchronous ink reveal via circular pen-tip stamping directly uncovering genuine artwork ink.
4. Smooth Bezier air transits between disconnected strokes and dots.
5. Cinematic 2.1x closeup camera tracking with smooth zoom-out outro.
"""
import os
import sys
import math
import cv2
import numpy as np

# Include kivy engine paths
sys.path.insert(0, r"E:\image_to_animate\kivy")
sys.path.insert(0, r"E:\image_to_animate\experiments\draw_priority")

from engine.video.encoder import VideoEncoder
from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
from engine.render.viewport_transform import render_camera_viewport
from engine.render.concentric_engine import (
    DEFAULT_HAND_PATH,
    DEFAULT_HAND_MASK_PATH,
    PEN_TIP_ANCHOR_X,
    PEN_TIP_ANCHOR_Y
)
from downstream_artifact_consumer import DownstreamArtifactConsumer

OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step6_drawing_methods"
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_MP4 = os.path.join(OUTPUT_DIR, "prototype8_authentic_text_animation.mp4")

# -----------------------------------------------------------------------------
# 1. CORE SKELETON ALGORITHMS (EXACT FROM PROTOTYPE 8)
# -----------------------------------------------------------------------------

def morphological_skeleton(bin_img):
    """Extracts 1-pixel thin medial axis skeleton via morphological thinning."""
    skeleton = np.zeros(bin_img.shape, np.uint8)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    img = bin_img.copy()
    while True:
        eroded = cv2.erode(img, element)
        temp = cv2.dilate(eroded, element)
        temp = cv2.subtract(img, temp)
        skeleton = cv2.bitwise_or(skeleton, temp)
        img = eroded.copy()
        if cv2.countNonZero(img) == 0:
            break
    return skeleton

def generate_smooth_bezier(p_start, p_end, num_points=2):
    """Generates natural Bezier arc for hand air transits."""
    p0 = np.array(p_start, dtype=np.float32)
    p3 = np.array(p_end, dtype=np.float32)
    dist = np.linalg.norm(p3 - p0)
    normal = np.array([-(p3[1] - p0[1]), (p3[0] - p0[0])])
    if np.linalg.norm(normal) > 1e-5:
        normal = normal / np.linalg.norm(normal)
    else:
        normal = np.array([0, -1])
    arc_height = min(12.0, dist * 0.08)
    p1 = p0 + (p3 - p0) * 0.33 + normal * arc_height
    p2 = p0 + (p3 - p0) * 0.66 + normal * arc_height
    pts = []
    for t in np.linspace(0, 1, num_points):
        pt = (1-t)**3 * p0 + 3*(1-t)**2 * t * p1 + 3*(1-t) * t**2 * p2 + t**3 * p3
        pts.append((float(pt[0]), float(pt[1])))
    return pts

def extract_ordered_skeleton_strokes(ink_roi, direction="RTL", step_stride=2):
    """Extracts ordered 1D stroke paths from the skeleton graph (Exact Prototype 8)."""
    skel = morphological_skeleton(ink_roi)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(skel)
    
    if num_labels <= 1:
        ys, xs = np.where(ink_roi > 0)
        if len(xs) == 0:
            return []
        if direction == "RTL":
            return [ [(float(x), float(ys[xs == x].mean())) for x in range(xs.max(), xs.min()-1, -step_stride) if len(ys[xs == x]) > 0] ]
        else:
            return [ [(float(x), float(ys[xs == x].mean())) for x in range(xs.min(), xs.max()+1, step_stride) if len(ys[xs == x]) > 0] ]

    comps = []
    for i in range(1, num_labels):
        cx = stats[i, cv2.CC_STAT_LEFT]
        cy = stats[i, cv2.CC_STAT_TOP]
        area = stats[i, cv2.CC_STAT_AREA]
        comps.append((cx, cy, area, i))
        
    if direction == "RTL":
        comps.sort(key=lambda c: -c[0]) # Right to Left
    else:
        comps.sort(key=lambda c: c[0])  # Left to Right
        
    all_strokes = []
    for cx, cy, area, idx in comps:
        comp_mask = (labels == idx).astype(np.uint8)
        ys, xs = np.where(comp_mask > 0)
        if len(xs) == 0:
            continue
            
        pts_set = set(zip(xs, ys))
        if direction == "RTL":
            start_pt = max(pts_set, key=lambda p: (p[0], -p[1]))
        else:
            start_pt = min(pts_set, key=lambda p: (p[0], p[1]))
            
        path = [start_pt]
        pts_set.remove(start_pt)
        curr = start_pt
        
        while pts_set:
            cx_pt, cy_pt = curr
            neighbors = []
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    np_pt = (cx_pt + dx, cy_pt + dy)
                    if np_pt in pts_set:
                        neighbors.append(np_pt)
            if neighbors:
                if direction == "RTL":
                    next_pt = min(neighbors, key=lambda p: (p[0], p[1]))
                else:
                    next_pt = max(neighbors, key=lambda p: (p[0], -p[1]))
                path.append(next_pt)
                pts_set.remove(next_pt)
                curr = next_pt
            else:
                next_pt = min(pts_set, key=lambda p: (p[0]-cx_pt)**2 + (p[1]-cy_pt)**2)
                path.append(next_pt)
                pts_set.remove(next_pt)
                curr = next_pt
                
        sampled_path = path[::step_stride]
        if len(sampled_path) > 0:
            all_strokes.append(sampled_path)
            
    return all_strokes


# -----------------------------------------------------------------------------
# 2. RUN ANIMATION ON PANEL 1 TEXT USING PROTOTYPE 8 PIPELINE
# -----------------------------------------------------------------------------

print("="*80)
print("[PROTOTYPE 8 ENGINE] RUNNING EXACT MEDIAL SKELETON TEXT HANDWRITING ANIMATION")
print("="*80)

p1_data = DownstreamArtifactConsumer.load_panel_artifacts(1)
txt_p1 = p1_data["typography_image"]
h_p, w_p = txt_p1.shape[:2]

diff_t = 255.0 - txt_p1.astype(np.float32)
ink_bin = (np.max(diff_t, axis=2) > 26.0).astype(np.uint8) * 255

# Speech Bubble Text Area:
# Line 1: ✓ ثق بنفسك
# Line 2: ✓ لا تستسلم.
# Line 3: ✓ ركز على هدفك
# Line 4: ✓ كل يوم خطوة للأمام
tx_min, ty_min, tw, th = int(w_p * 0.44), int(h_p * 0.20), int(w_p * 0.46), int(h_p * 0.65)
roi_img = txt_p1[ty_min:ty_min+th, tx_min:tx_min+tw]
roi_ink = ink_bin[ty_min:ty_min+th, tx_min:tx_min+tw]

# Identify individual lines within ROI
num_t, lbl_t, stat_t, _ = cv2.connectedComponentsWithStats(roi_ink)
glyphs = []
for i in range(1, num_t):
    gx, gy, gw, gh, ga = stat_t[i]
    if ga < 3: continue
    glyphs.append({"bbox": (gx, gy, gw, gh), "cx": gx + gw/2.0, "cy": gy + gh/2.0, "mask": (lbl_t == i)})

glyphs.sort(key=lambda g: g["cy"])
text_lines = []
if glyphs:
    cur_l = [glyphs[0]]
    ly1, ly2 = glyphs[0]["bbox"][1], glyphs[0]["bbox"][1] + glyphs[0]["bbox"][3]
    for g in glyphs[1:]:
        gy, gh = g["bbox"][1], g["bbox"][3]
        if gy <= ly2 + 5 and (gy + gh) >= ly1 - 5:
            cur_l.append(g)
            ly1 = min(ly1, gy)
            ly2 = max(ly2, gy + gh)
        else:
            text_lines.append(cur_l)
            cur_l = [g]
            ly1, ly2 = gy, gy + gh
    if cur_l: text_lines.append(cur_l)

text_lines.sort(key=lambda l: min(g["bbox"][1] for g in l))
print(f"Identified {len(text_lines)} coherent text lines inside ROI.")

# Setup Prototype 8 Canvas & Hand
out_w, out_h = 1920, 1080
fps = 30

hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
hand_h_native = 260
scale_native = hand_h_native / float(hand_bgra.shape[0])
hand_w_native = max(1, int(hand_bgra.shape[1] * scale_native))
hand_native = cv2.resize(hand_bgra, (hand_w_native, hand_h_native), interpolation=cv2.INTER_AREA)
tip_x_native = int(round(PEN_TIP_ANCHOR_X * scale_native))
tip_y_native = int(round(PEN_TIP_ANCHOR_Y * scale_native))

# Scale text region nicely in center of HD canvas
t_scale = (out_h * 0.68) / float(th)
scaled_tw = int(round(tw * t_scale))
scaled_th = int(round(th * t_scale))
canvas_img = cv2.resize(roi_img, (scaled_tw, scaled_th), interpolation=cv2.INTER_LANCZOS4)
canvas_ink = cv2.resize(roi_ink, (scaled_tw, scaled_th), interpolation=cv2.INTER_NEAREST)

pos_x = (out_w - scaled_tw) // 2
pos_y = (out_h - scaled_th) // 2

target_complete_canvas = np.full((out_h, out_w, 3), 255, dtype=np.uint8)
target_complete_canvas[pos_y:pos_y+scaled_th, pos_x:pos_x+scaled_tw] = canvas_img

live_canvas = np.full((out_h, out_w, 3), 255, dtype=np.uint8)
revealed_mask = np.zeros((out_h, out_w), dtype=np.uint8)

encoder = VideoEncoder(OUTPUT_MP4, out_w, out_h, fps, crf=18)

# Prototype 8 Camera Tracking
cam_cx = pos_x + scaled_tw * 0.70
cam_cy = pos_y + scaled_th * 0.25
cam_zoom = 2.1 # Close-up 2.1x as in Prototype 8!
current_pen = (cam_cx, max(0, cam_cy - 80))
total_frames = 0
PTS_PER_FRAME = 12 # Fast energetic handwriting pace

def emit_frame(pen_x, pen_y, target_cam_cx, target_cam_cy, target_zoom):
    global cam_cx, cam_cy, cam_zoom, total_frames
    
    # Smooth easing towards target camera
    cam_cx += (target_cam_cx - cam_cx) * 0.28
    cam_cy += (target_cam_cy - cam_cy) * 0.28
    cam_zoom += (target_zoom - cam_zoom) * 0.28
        
    frame_native = composite_hand_on_canvas_fast(
        live_canvas, hand_native,
        tip_x_native, tip_y_native,
        int(round(pen_x)), int(round(pen_y))
    )
    
    viewport_1080p = render_camera_viewport(
        frame_native,
        center_x=cam_cx,
        center_y=cam_cy,
        zoom_scale=cam_zoom,
        out_w=out_w,
        out_h=out_h
    )
    encoder.write_frame(viewport_1080p)
    total_frames += 1

# Steady Camera Target: Locked on the text panel center (Zero Camera Vibration!)
panel_center_x = pos_x + scaled_tw * 0.5
panel_center_y = pos_y + scaled_th * 0.5
cam_cx = panel_center_x
cam_cy = panel_center_y
cam_zoom = 1.95 # Crisp, steady close-up

# Render Line by Line using Prototype 8 Medial Skeleton Algorithm
for l_idx, line in enumerate(text_lines):
    lx_min = min(g["bbox"][0] for g in line)
    ly_min = min(g["bbox"][1] for g in line)
    lx_max = max(g["bbox"][0] + g["bbox"][2] for g in line)
    ly_max = max(g["bbox"][1] + g["bbox"][3] for g in line)
    
    slx = pos_x + int(round(lx_min * t_scale))
    sly = pos_y + int(round(ly_min * t_scale))
    slw = int(round((lx_max - lx_min) * t_scale))
    slh = int(round((ly_max - ly_min) * t_scale))
    
    # Line mask on canvas
    line_ink_crop = canvas_ink[sly - pos_y : sly - pos_y + slh, slx - pos_x : slx - pos_x + slw]
    
    # Extract 1-Pixel Medial Axis Skeleton Strokes
    strokes = extract_ordered_skeleton_strokes(line_ink_crop, direction="RTL", step_stride=2)
    
    for stroke in strokes:
        global_pts = [(slx + pt[0], sly + pt[1]) for pt in stroke]
        if not global_pts:
            continue
            
        # 2-frame Bezier air transit to stroke start
        transit = generate_smooth_bezier(current_pen, global_pts[0], num_points=2)
        for pt in transit:
            emit_frame(pt[0], pt[1], panel_center_x, panel_center_y, 1.95)
        current_pen = global_pts[0]
        
        idx = 0
        while idx < len(global_pts):
            next_idx = min(len(global_pts), idx + PTS_PER_FRAME)
            chunk = global_pts[idx:next_idx]
            
            # Stamping circle along skeleton uncovers the genuine artwork ink
            for pt in chunk:
                gx, gy = int(round(pt[0])), int(round(pt[1]))
                cv2.circle(revealed_mask, (gx, gy), 8, 255, -1)
                
            new_rev = (revealed_mask[pos_y:pos_y+scaled_th, pos_x:pos_x+scaled_tw] > 0) & (canvas_ink > 0)
            live_canvas[pos_y:pos_y+scaled_th, pos_x:pos_x+scaled_tw][new_rev] = canvas_img[new_rev]
            
            last_pt = chunk[-1]
            # Emit frame with ROCK-SOLID camera target on panel center!
            emit_frame(last_pt[0], last_pt[1], panel_center_x, panel_center_y, 1.95)
            current_pen = last_pt
            idx = next_idx

# Finale: Smooth Zoom-Out to Full 1080p Overview (1.0x) exactly like Prototype 8
print("Finale: Smooth Zoom-Out to Full 1080p Overview...")
exit_transit = generate_smooth_bezier(current_pen, (out_w + 100, out_h + 100), num_points=12)
for pt in exit_transit:
    emit_frame(pt[0], pt[1], out_w / 2.0, out_h / 2.0, 1.0)
    
for _ in range(15):
    emit_frame(out_w + 120, out_h + 120, out_w / 2.0, out_h / 2.0, 1.0)
    
final_full = render_camera_viewport(live_canvas, out_w / 2.0, out_h / 2.0, 1.0, out_w, out_h)
for _ in range(35):
    encoder.write_frame(final_full)
    total_frames += 1
    
encoder.close()
duration_s = total_frames / 30.0
print("="*80)
print(f"[SUCCESS] Prototype 8 Text Animation Video Exported: {OUTPUT_MP4}")
print(f"Total Frames: {total_frames} ({duration_s:.2f} seconds @ 30 FPS, 1080p)")
print("="*80 + "\n")
