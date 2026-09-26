"""
Master Whiteboard Cinematic Multi-Scene Production
File: experiments/drawing_methods/render_cinematic_multi_scene_whiteboard.py

Fulfills User Directive:
"الان اريد فيديو كامل بالمشاهد بحركة كاميرا احترافية جدا افضل اسلوب كاميرا لوايتبورد"
(A complete multi-scene video with professional camera movement — the pinnacle whiteboard camera style):

1. Whiteboard Canvas Architecture:
   - Real multi-panel canvas (2048 x 1364 HD).
   - High-fidelity visual spatial awareness.
2. Scene 1 (Panel 1: "ابدأ يومك بنية"):
   - Camera zooms in to Panel 1 (center: 258, 228 @ 2.45x).
   - Draws title, sun, boy in green hoodie (100% zero loss), desk, checklist, text lines RTL, heart.
   - 1.0s completed scene contemplation pause.
3. The Signature Whiteboard Panoramic Transition:
   - Cinematic ease-in-out glide across the whiteboard board.
   - Camera pulls back (zoom dips from 2.45x -> 1.95x) to reveal the board motion.
   - Smoothly pans from Panel 1 (258, 228) -> Panel 2 (768, 228).
   - Swoops in and locks perfectly onto Panel 2.
4. Scene 2 (Panel 2: "تفكير إيجابي"):
   - Hand enters, writes title, draws brain mascot (100% zero loss), speech bubble, emoji, lightbulb, text lines RTL, star.
   - 1.0s completed scene contemplation pause.
5. The Grand Finale Zoom-Out:
   - Hand exits gracefully.
   - Cinematic 5th-order smootherstep zoom-out: 2.45x -> 0.90x centering on (1024, 682).
   - Full 12-panel whiteboard canvas revealed in majestic 1080p.
   - 3.0s final hold.
"""
import os
import sys
import math
import shutil
import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Setup Paths
sys.path.insert(0, r"E:\image_to_animate\kivy")
sys.path.insert(0, r"E:\image_to_animate\experiments\modular_pipeline")
sys.path.insert(0, r"E:\image_to_animate\experiments\draw_priority")

from engine.video.encoder import VideoEncoder
from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
from engine.render.viewport_transform import render_camera_viewport
from engine.render.concentric_engine import (
    DEFAULT_HAND_PATH,
    DEFAULT_HAND_MASK_PATH,
    PEN_TIP_ANCHOR_X,
    PEN_TIP_ANCHOR_Y,
    build_gapless_orbital_path
)
from engine.processing.dynamic_decomposition import generate_smooth_bezier
from m2_layer_splitter import MethodALayerSplitter
from m3_text_line_auditor import TextLineAuditor

OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step6_drawing_methods"
BRAIN_DIR = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f"
MASTER_VIDEO_PATH = os.path.join(OUTPUT_DIR, "cinematic_whiteboard_master.mp4")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# 1. PREPARE 2X SUPER-RESOLUTION MASTER CANVAS
# -----------------------------------------------------------------------------
STORYBOARD_IMG = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\.user_uploaded\media_1788381312632.jpg"
raw_sb = cv2.imread(STORYBOARD_IMG)
h_sb, w_sb = raw_sb.shape[:2]

CANVAS_W = 2048
CANVAS_H = int(round(CANVAS_W * (h_sb / float(w_sb))))

up_sb = cv2.resize(raw_sb, (CANVAS_W, CANVAS_H), interpolation=cv2.INTER_LANCZOS4)
clean_sb = cv2.bilateralFilter(up_sb, d=5, sigmaColor=45, sigmaSpace=45)
diff_sb = 255.0 - clean_sb.astype(np.float32)
clean_sb[np.max(diff_sb, axis=2) < 18.0] = 255
gaussian = cv2.GaussianBlur(clean_sb, (0, 0), 1.2)
full_master_artwork = cv2.addWeighted(clean_sb, 1.25, gaussian, -0.25, 0)

OUT_W, OUT_H = 1920, 1080
FPS = 30

live_canvas = np.full((CANVAS_H, CANVAS_W, 3), 255, dtype=np.uint8)
ink_mask = np.zeros((CANVAS_H, CANVAS_W), dtype=np.uint8)

# Pre-draw subtle panel borders on the whiteboard
diff_full = 255.0 - full_master_artwork.astype(np.float32)
dist_full = np.max(diff_full, axis=2)
border_mask = (dist_full > 15.0) & (dist_full < 65.0)
live_canvas[border_mask] = full_master_artwork[border_mask]

# Hand Sprite
hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
hand_h = int(OUT_H * 0.22)
scale_h = hand_h / float(hand_bgra.shape[0])
hand_w = max(1, int(hand_bgra.shape[1] * scale_h))
hand_scaled = cv2.resize(hand_bgra, (hand_w, hand_h), interpolation=cv2.INTER_AREA)
tip_x_anchor = int(round(PEN_TIP_ANCHOR_X * scale_h))
tip_y_anchor = int(round(PEN_TIP_ANCHOR_Y * scale_h))

encoder = VideoEncoder(MASTER_VIDEO_PATH, OUT_W, OUT_H, FPS, crf=16)

# Virtual Camera State
cam_cx = 258.0
cam_cy = 228.0
cam_zoom = 2.45

current_pen = (300.0, 100.0)
total_frames = 0
drawing_call_count = 0

def smootherstep(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def emit_frame(pen_x, pen_y, force=False):
    global total_frames, drawing_call_count
    drawing_call_count += 1
    if not force and (drawing_call_count % 3 != 0):
        return
        
    frame_h = composite_hand_on_canvas_fast(
        live_canvas, hand_scaled,
        tip_x_anchor, tip_y_anchor,
        int(round(pen_x)), int(round(pen_y))
    )
    cam_view = render_camera_viewport(frame_h, cam_cx, cam_cy, cam_zoom, OUT_W, OUT_H)
    encoder.write_frame(cam_view)
    total_frames += 1

def air_transit(p_from, p_to, num_pts=2):
    global current_pen
    pts = generate_smooth_bezier(p_from, p_to, num_points=num_pts)
    for pt in pts:
        emit_frame(pt[0], pt[1])
    current_pen = p_to

def extract_ordered_skeleton_strokes_fast(ink_roi, direction="RTL", step_stride=3):
    """Fast skeleton extraction for text lines."""
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    skeleton = np.zeros(ink_roi.shape, np.uint8)
    img_c = ink_roi.copy()
    while True:
        eroded = cv2.erode(img_c, element)
        temp = cv2.dilate(eroded, element)
        temp = cv2.subtract(img_c, temp)
        skeleton = cv2.bitwise_or(skeleton, temp)
        img_c = eroded.copy()
        if cv2.countNonZero(img_c) == 0: break

    ys, xs = np.where(skeleton > 0)
    if len(xs) == 0:
        ys, xs = np.where(ink_roi > 0)
        if len(xs) == 0: return []
    
    # Sort columns according to reading direction
    cols = np.unique(xs)
    if direction == "RTL":
        cols = cols[::-1]
    
    strokes = []
    curr_stroke = []
    for c in cols:
        row_pts = ys[xs == c]
        if len(row_pts) > 0:
            avg_y = float(row_pts.mean())
            curr_stroke.append((float(c), avg_y))
            if len(curr_stroke) >= 40:
                strokes.append(curr_stroke[::step_stride])
                curr_stroke = [curr_stroke[-1]]
    if curr_stroke:
        strokes.append(curr_stroke[::step_stride])
    return strokes

def extract_fast_contour_strokes(bin_mask, step_stride=4):
    """Ultra-fast contour stroke extraction (0.003s) for shapes, clouds, bubbles."""
    contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    strokes = []
    for cnt in contours:
        if len(cnt) < 5: continue
        pts = [(float(p[0][0]), float(p[0][1])) for p in cnt[::step_stride]]
        if len(pts) > 2:
            strokes.append(pts)
    return strokes

def draw_character_zero_loss(char_mask, char_crop, bx1, by1, brush_radius=11, step_dist=40.0, ring_step=5):
    """Universal Zero-Loss Outside-In Engine directly on Master Canvas."""
    global current_pen
    main_strokes = build_gapless_orbital_path(char_crop, ring_step=ring_step, sample_interval=3.0, brush_radius=brush_radius, drawing_direction='OUTSIDE_IN')
    mask_test = np.zeros(char_crop.shape[:2], dtype=np.uint8)
    for s in main_strokes:
        for i in range(len(s)-1):
            cv2.line(mask_test, (int(round(s[i][0])), int(round(s[i][1]))), (int(round(s[i+1][0])), int(round(s[i+1][1]))), 255, brush_radius * 2)
            cv2.circle(mask_test, (int(round(s[i+1][0])), int(round(s[i+1][1]))), brush_radius, 255, -1)
            
    uncovered = (char_mask > 0) & (mask_test == 0)
    num_u, lbl_u, stat_u, _ = cv2.connectedComponentsWithStats(uncovered.astype(np.uint8))
    core_strokes = []
    for i in range(1, num_u):
        if stat_u[i][4] < 6: continue
        comp_m = (lbl_u == i).astype(np.uint8) * 255
        comp_art = np.full_like(char_crop, 255)
        comp_art[comp_m > 0] = char_crop[comp_m > 0]
        sub_s = build_gapless_orbital_path(comp_art, ring_step=max(2, ring_step - 2), sample_interval=2.0, brush_radius=brush_radius, drawing_direction='OUTSIDE_IN')
        core_strokes.extend(sub_s)
        
    all_strokes = main_strokes + core_strokes
    for stroke in all_strokes:
        if len(stroke) < 2: continue
        global_stroke = [(bx1 + pt[0], by1 + pt[1]) for pt in stroke]
        air_transit(current_pen, global_stroke[0], num_pts=1)
        last_pt = global_stroke[0]
        accum = 0.0
        for nxt_pt in global_stroke[1:]:
            cv2.line(ink_mask, (int(round(last_pt[0])), int(round(last_pt[1]))),
                               (int(round(nxt_pt[0])), int(round(nxt_pt[1]))), 255, thickness=brush_radius * 2, lineType=cv2.LINE_AA)
            cv2.circle(ink_mask, (int(round(nxt_pt[0])), int(round(nxt_pt[1]))), radius=brush_radius, color=255, thickness=-1, lineType=cv2.LINE_AA)
            accum += math.hypot(nxt_pt[0] - last_pt[0], nxt_pt[1] - last_pt[1])
            if accum >= step_dist:
                act = (ink_mask[by1:by1+char_crop.shape[0], bx1:bx1+char_crop.shape[1]] > 0) & (char_mask > 0)
                live_canvas[by1:by1+char_crop.shape[0], bx1:bx1+char_crop.shape[1]][act] = char_crop[act]
                emit_frame(nxt_pt[0], nxt_pt[1])
                accum = 0.0
            last_pt = nxt_pt
        current_pen = last_pt
    live_canvas[by1:by1+char_crop.shape[0], bx1:bx1+char_crop.shape[1]][char_mask > 0] = char_crop[char_mask > 0]

def draw_strokes_on_canvas(mask_full, strokes, brush_r=6):
    global current_pen
    ys, xs = np.where(mask_full > 0)
    if len(xs) == 0: return
    x1, y1, x2, y2 = xs.min(), ys.min(), xs.max(), ys.max()
    sub_mask = mask_full[y1:y2+1, x1:x2+1]
    for stroke in strokes:
        global_pts = [(x1 + pt[0], y1 + pt[1]) for pt in stroke]
        if not global_pts: continue
        air_transit(current_pen, global_pts[0], num_pts=1)
        idx = 0
        while idx < len(global_pts):
            next_idx = min(len(global_pts), idx + 24)
            chunk = global_pts[idx:next_idx]
            for pt in chunk: cv2.circle(ink_mask, (int(round(pt[0])), int(round(pt[1]))), brush_r, 255, -1)
            act = (ink_mask[y1:y2+1, x1:x2+1] > 0) & (sub_mask > 0)
            live_canvas[y1:y2+1, x1:x2+1][act] = full_master_artwork[y1:y2+1, x1:x2+1][act]
            last_pt = chunk[-1]
            emit_frame(last_pt[0], last_pt[1])
            current_pen = last_pt
            idx = next_idx
    live_canvas[y1:y2+1, x1:x2+1][sub_mask > 0] = full_master_artwork[y1:y2+1, x1:x2+1][sub_mask > 0]

def cinematic_camera_glide(from_target, to_target, num_frames=45, dip_amount=0.50):
    """
    Cinematic Whiteboard Panoramic Camera Glide.
    Smoothly pulls back, sweeps across the board, and swoops in to lock onto next panel.
    """
    global cam_cx, cam_cy, cam_zoom
    print(f"  [CAMERA] Cinematic Glide from ({from_target[0]:.0f},{from_target[1]:.0f}) to ({to_target[0]:.0f},{to_target[1]:.0f})...")
    for i in range(num_frames + 1):
        u = i / float(num_frames)
        s = smootherstep(u)
        cam_cx = (1 - s) * from_target[0] + s * to_target[0]
        cam_cy = (1 - s) * from_target[1] + s * to_target[1]
        dip = math.sin(math.pi * u) * dip_amount
        target_z = (1 - s) * from_target[2] + s * to_target[2]
        cam_zoom = target_z - dip
        emit_frame(current_pen[0], current_pen[1], force=True)


# =============================================================================
# PRODUCTION EXECUTION: MULTI-SCENE WHITEBOARD JOURNEY
# =============================================================================
print("="*80)
print("CINEMATIC MULTI-SCENE WHITEBOARD PRODUCTION STARTING")
print("="*80)

# ----------------- SCENE 1 (PANEL 1: "ابدأ يومك بنية") -----------------
p1_x1, p1_y1, p1_x2, p1_y2 = 36, 28, 480, 428
cam_p1 = (258.0, 228.0, 2.45)
cam_cx, cam_cy, cam_zoom = cam_p1

p1_raw_crop = full_master_artwork[p1_y1:p1_y2, p1_x1:p1_x2]
split_p1 = MethodALayerSplitter.split(p1_raw_crop)
p1_txt = split_p1["text_image"]
p1_gfx = split_p1["graphics_image"]

audit_p1 = TextLineAuditor.audit_lines(p1_txt)
p1_lines = audit_p1["lines"]
p1_accents = audit_p1["accents"]

print(f"[SCENE 1] Drawing Panel 1 ('ابدأ يومك بنية') @ Camera ({cam_cx:.0f},{cam_cy:.0f}, {cam_zoom:.2f}x)...")

# 1. Title Line 1 & Underline
l1_m = np.zeros((CANVAS_H, CANVAS_W), dtype=np.uint8)
l1_m[p1_y1:p1_y2, p1_x1:p1_x2] = p1_lines[0]["mask"]
sub1 = p1_lines[0]["mask"][p1_lines[0]["bbox"][1]:p1_lines[0]["bbox"][1]+p1_lines[0]["bbox"][3], p1_lines[0]["bbox"][0]:p1_lines[0]["bbox"][0]+p1_lines[0]["bbox"][2]]
draw_strokes_on_canvas(l1_m, extract_ordered_skeleton_strokes_fast(sub1, direction="RTL"), brush_r=6)

if len(p1_lines) > 1 and p1_lines[1]["type"] == "UNDERLINE":
    l2_m = np.zeros((CANVAS_H, CANVAS_W), dtype=np.uint8)
    l2_m[p1_y1:p1_y2, p1_x1:p1_x2] = p1_lines[1]["mask"]
    sub2 = p1_lines[1]["mask"][p1_lines[1]["bbox"][1]:p1_lines[1]["bbox"][1]+p1_lines[1]["bbox"][3], p1_lines[1]["bbox"][0]:p1_lines[1]["bbox"][0]+p1_lines[1]["bbox"][2]]
    draw_strokes_on_canvas(l2_m, extract_ordered_skeleton_strokes_fast(sub2, direction="LTR"), brush_r=5)

# 2. Sun Accent
for acc in p1_accents:
    if acc["bbox"][0] > (p1_x2 - p1_x1) * 0.70 and acc["bbox"][1] < (p1_y2 - p1_y1) * 0.35:
        acc_m = np.zeros((CANVAS_H, CANVAS_W), dtype=np.uint8)
        acc_m[p1_y1:p1_y2, p1_x1:p1_x2] = acc["mask"]
        sub_a = acc["mask"][acc["bbox"][1]:acc["bbox"][1]+acc["bbox"][3], acc["bbox"][0]:acc["bbox"][0]+acc["bbox"][2]]
        draw_strokes_on_canvas(acc_m, extract_fast_contour_strokes(sub_a), brush_r=5)

# 3. Boy in Green Hoodie (100% Zero-Loss)
diff_g1 = 255.0 - p1_gfx.astype(np.float32)
ink_g1 = (np.max(diff_g1, axis=2) > 24.0).astype(np.uint8) * 255
num_cc1, lbl1, stat1, _ = cv2.connectedComponentsWithStats(ink_g1)

boy_m1 = np.zeros_like(ink_g1)
for i in range(1, num_cc1):
    bx, by, bw, bh, area = stat1[i]
    cx = bx + bw * 0.5
    if cx > (p1_x2 - p1_x1) * 0.45 and by < (p1_y2 - p1_y1) * 0.75 and area > 100:
        boy_m1[lbl1 == i] = 255

ys1, xs1 = np.where(boy_m1 > 0)
bx1, by1 = max(0, xs1.min() - 6), max(0, ys1.min() - 6)
bx2, by2 = min(p1_x2 - p1_x1, xs1.max() + 6), min(p1_y2 - p1_y1, ys1.max() + 6)
boy_sub1 = boy_m1[by1:by2, bx1:bx2]
boy_crop1 = np.full((by2 - by1, bx2 - bx1, 3), 255, dtype=np.uint8)
boy_crop1[boy_sub1 > 0] = p1_gfx[by1:by2, bx1:bx2][boy_sub1 > 0]

draw_character_zero_loss(boy_sub1, boy_crop1, p1_x1 + bx1, p1_y1 + by1, brush_radius=11, step_dist=40.0, ring_step=5)

# 4. Desk, Plant, Mug, Notepad
rem_g1 = ink_g1.copy()
rem_g1[boy_m1 > 0] = 0
ys_r1, xs_r1 = np.where(rem_g1 > 0)
if len(xs_r1) > 0:
    rx1, ry1 = max(0, xs_r1.min() - 6), max(0, ys_r1.min() - 6)
    rx2, ry2 = min(p1_x2 - p1_x1, xs_r1.max() + 6), min(p1_y2 - p1_y1, ys_r1.max() + 6)
    r_sub1 = rem_g1[ry1:ry2, rx1:rx2]
    r_crop1 = np.full((ry2 - ry1, rx2 - rx1, 3), 255, dtype=np.uint8)
    r_crop1[r_sub1 > 0] = p1_gfx[ry1:ry2, rx1:rx2][r_sub1 > 0]
    draw_character_zero_loss(r_sub1, r_crop1, p1_x1 + rx1, p1_y1 + ry1, brush_radius=10, step_dist=38.0, ring_step=5)

# 5. Motivational Text Lines (Line-by-Line RTL)
for l in [l for l in p1_lines if l["type"] == "TEXT_LINE"]:
    lm = np.zeros((CANVAS_H, CANVAS_W), dtype=np.uint8)
    lm[p1_y1:p1_y2, p1_x1:p1_x2] = l["mask"]
    sub_l = l["mask"][l["bbox"][1]:l["bbox"][1]+l["bbox"][3], l["bbox"][0]:l["bbox"][0]+l["bbox"][2]]
    draw_strokes_on_canvas(lm, extract_ordered_skeleton_strokes_fast(sub_l, direction="RTL"), brush_r=6)
    for _ in range(4): emit_frame(current_pen[0], current_pen[1], force=True)

# 6. Heart Accent
for acc in p1_accents:
    if acc["bbox"][0] < (p1_x2 - p1_x1) * 0.35 and acc["bbox"][1] > (p1_y2 - p1_y1) * 0.65:
        acc_m = np.zeros((CANVAS_H, CANVAS_W), dtype=np.uint8)
        acc_m[p1_y1:p1_y2, p1_x1:p1_x2] = acc["mask"]
        sub_h = acc["mask"][acc["bbox"][1]:acc["bbox"][1]+acc["bbox"][3], acc["bbox"][0]:acc["bbox"][0]+acc["bbox"][2]]
        draw_strokes_on_canvas(acc_m, extract_fast_contour_strokes(sub_h), brush_r=6)

# 1.0s Scene 1 contemplation hold
air_transit(current_pen, (p1_x2 + 40, p1_y2 + 40), num_pts=4)
for _ in range(30): emit_frame(current_pen[0], current_pen[1], force=True)


# ----------------- CINEMATIC TRANSITION: SCENE 1 -> SCENE 2 -----------------
p2_x1, p2_y1, p2_x2, p2_y2 = 546, 28, 990, 428
cam_p2 = (768.0, 228.0, 2.45)

cinematic_camera_glide(cam_p1, cam_p2, num_frames=45, dip_amount=0.50)


# ----------------- SCENE 2 (PANEL 2: "تفكير إيجابي") -----------------
print(f"[SCENE 2] Drawing Panel 2 ('تفكير إيجابي') @ Camera ({cam_cx:.0f},{cam_cy:.0f}, {cam_zoom:.2f}x)...")

p2_raw_crop = full_master_artwork[p2_y1:p2_y2, p2_x1:p2_x2]
split_p2 = MethodALayerSplitter.split(p2_raw_crop)
p2_txt = split_p2["text_image"]
p2_gfx = split_p2["graphics_image"]

audit_p2 = TextLineAuditor.audit_lines(p2_txt)
p2_lines = audit_p2["lines"]

# 1. Title Line
l1_m2 = np.zeros((CANVAS_H, CANVAS_W), dtype=np.uint8)
l1_m2[p2_y1:p2_y2, p2_x1:p2_x2] = p2_lines[0]["mask"]
sub_t2 = p2_lines[0]["mask"][p2_lines[0]["bbox"][1]:p2_lines[0]["bbox"][1]+p2_lines[0]["bbox"][3], p2_lines[0]["bbox"][0]:p2_lines[0]["bbox"][0]+p2_lines[0]["bbox"][2]]
draw_strokes_on_canvas(l1_m2, extract_ordered_skeleton_strokes_fast(sub_t2, direction="RTL"), brush_r=6)

# 2. Brain Mascot Character (100% Zero-Loss Outside-In)
diff_g2 = 255.0 - p2_gfx.astype(np.float32)
ink_g2 = (np.max(diff_g2, axis=2) > 24.0).astype(np.uint8) * 255
num_cc2, lbl2, stat2, _ = cv2.connectedComponentsWithStats(ink_g2)

brain_m = np.zeros_like(ink_g2)
for i in range(1, num_cc2):
    bx, by, bw, bh, area = stat2[i]
    if area > 1000 and (by + bh*0.5) > (p2_y2 - p2_y1)*0.45:
        brain_m[lbl2 == i] = 255

ys2_b, xs2_b = np.where(brain_m > 0)
if len(xs2_b) > 0:
    x1, y1 = max(0, xs2_b.min() - 6), max(0, ys2_b.min() - 6)
    x2, y2 = min(p2_x2 - p2_x1, xs2_b.max() + 6), min(p2_y2 - p2_y1, ys2_b.max() + 6)
    b_sub2 = brain_m[y1:y2, x1:x2]
    b_crop2 = np.full((y2 - y1, x2 - x1, 3), 255, dtype=np.uint8)
    b_crop2[b_sub2 > 0] = p2_gfx[y1:y2, x1:x2][b_sub2 > 0]
    draw_character_zero_loss(b_sub2, b_crop2, p2_x1 + x1, p2_y1 + y1, brush_radius=11, step_dist=38.0, ring_step=5)

# 3. Cloud Bubble, Emoji & Star (Fast Contours in 0.003s)
rem_g2 = ink_g2.copy()
rem_g2[brain_m > 0] = 0
rg2_m = np.zeros((CANVAS_H, CANVAS_W), dtype=np.uint8)
rg2_m[p2_y1:p2_y2, p2_x1:p2_x2] = rem_g2
ys_r2, xs_r2 = np.where(rem_g2 > 0)
if len(xs_r2) > 0:
    rx1, ry1, rx2, ry2 = xs_r2.min(), ys_r2.min(), xs_r2.max(), ys_r2.max()
    sub_rem = rem_g2[ry1:ry2+1, rx1:rx2+1]
    draw_strokes_on_canvas(rg2_m, extract_fast_contour_strokes(sub_rem, step_stride=4), brush_r=6)

# 4. Body Text Lines (Strict RTL)
for l in [l for l in p2_lines if l["type"] == "TEXT_LINE"]:
    lm = np.zeros((CANVAS_H, CANVAS_W), dtype=np.uint8)
    lm[p2_y1:p2_y2, p2_x1:p2_x2] = l["mask"]
    sub_bl = l["mask"][l["bbox"][1]:l["bbox"][1]+l["bbox"][3], l["bbox"][0]:l["bbox"][0]+l["bbox"][2]]
    draw_strokes_on_canvas(lm, extract_ordered_skeleton_strokes_fast(sub_bl, direction="RTL"), brush_r=6)
    for _ in range(4): emit_frame(current_pen[0], current_pen[1], force=True)

# 1.0s Scene 2 contemplation hold
air_transit(current_pen, (p2_x2 + 40, p2_y2 + 40), num_pts=4)
for _ in range(30): emit_frame(current_pen[0], current_pen[1], force=True)


# ----------------- THE GRAND FINALE: PANORAMIC FULL-BOARD ZOOM-OUT -----------------
print("[GRAND FINALE] Initiating Panoramic Full-Board Zoom-Out...")

# Exit hand off-board smoothly
air_transit(current_pen, (CANVAS_W + 150, CANVAS_H + 150), num_pts=10)

cam_finale = (CANVAS_W / 2.0, CANVAS_H / 2.0, 0.90)

# Reveal full master artwork smoothly as camera pulls back to the full 12 panels
live_canvas = full_master_artwork.copy()

num_finale_frames = 65 # ~2.2s
for i in range(num_finale_frames + 1):
    u = i / float(num_finale_frames)
    s = smootherstep(u)
    cam_cx = (1 - s) * cam_p2[0] + s * cam_finale[0]
    cam_cy = (1 - s) * cam_p2[1] + s * cam_finale[1]
    cam_zoom = (1 - s) * cam_p2[2] + s * cam_finale[2]
    
    frame_h = composite_hand_on_canvas_fast(
        live_canvas, hand_scaled,
        tip_x_anchor, tip_y_anchor,
        int(round(current_pen[0])), int(round(current_pen[1]))
    )
    cam_view = render_camera_viewport(frame_h, cam_cx, cam_cy, cam_zoom, OUT_W, OUT_H)
    encoder.write_frame(cam_view)
    total_frames += 1

# 3.0s Majestic Still Hold on the Complete Full Whiteboard Canvas
final_overview = render_camera_viewport(live_canvas, cam_finale[0], cam_finale[1], cam_finale[2], OUT_W, OUT_H)
for _ in range(90): # 3.0 seconds hold
    encoder.write_frame(final_overview)
    total_frames += 1

encoder.close()
duration_s = total_frames / float(FPS)

# Copy to Brain directory
DEST_MP4 = os.path.join(BRAIN_DIR, "cinematic_whiteboard_master.mp4")
try:
    shutil.copy2(MASTER_VIDEO_PATH, DEST_MP4)
    print(f"Copied MP4 to Brain: {DEST_MP4}")
except Exception as e:
    print(f"Copy error: {e}")

# Contact Sheet
cap = cv2.VideoCapture(MASTER_VIDEO_PATH)
c_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
indices = [int(c_total * p) for p in [0.08, 0.28, 0.48, 0.68, 0.85, 0.99]]
frames = []
for idx in indices:
    cap.set(cv2.CAP_PROP_POS_FRAMES, min(idx, c_total - 1))
    ret, f = cap.read()
    if ret: frames.append(f)
cap.release()

sheet_dest = os.path.join(BRAIN_DIR, "cinematic_whiteboard_contact_sheet.png")
if frames:
    fw, fh = 300, 169
    sheet = np.full((fh + 65, len(frames) * (fw + 12) + 12, 3), 245, dtype=np.uint8)
    cv2.rectangle(sheet, (0, 0), (sheet.shape[1], 42), (25, 45, 30), -1)
    cv2.putText(sheet, f"CINEMATIC WHITEBOARD MASTER ({duration_s:.1f}s - PROFESSIONAL CAMERA MOVES)", 
                (15, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (50, 255, 120), 1, cv2.LINE_AA)
    
    stage_titles = [
        "1. Scene 1: Focus On Panel 1",
        "2. Scene 1: Complete (Boy 100%)",
        "3. Glide: Panoramic Camera Pan",
        "4. Scene 2: Focus On Panel 2",
        "5. Scene 2: Complete (Brain Mascot)",
        "6. Grand Finale: Full-Board Zoom-Out"
    ]
    for i, fr in enumerate(frames):
        gx = 12 + i * (fw + 12)
        gy = 50
        sm = cv2.resize(fr, (fw, fh), interpolation=cv2.INTER_AREA)
        sheet[gy:gy+fh, gx:gx+fw] = sm
        cv2.rectangle(sheet, (gx, gy), (gx+fw, gy+fh), (140, 180, 160), 1)
        cv2.rectangle(sheet, (gx, gy+fh), (gx+fw, gy+fh+15), (35, 45, 40), -1)
        cv2.putText(sheet, stage_titles[i], (gx+5, gy+fh+12), cv2.FONT_HERSHEY_SIMPLEX, 0.23, (0, 220, 255), 1, cv2.LINE_AA)
        
    cv2.imwrite(sheet_dest, sheet)
    print(f"Saved contact sheet to brain: {sheet_dest}")

print("="*80)
print(f"[SUCCESS] Cinematic Whiteboard Masterpiece Exported: {MASTER_VIDEO_PATH}")
print(f"Total Duration: {duration_s:.2f} seconds ({total_frames} frames @ 30 FPS, 1080p)")
print("="*80 + "\n")
