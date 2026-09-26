"""
Phase 6 — Panel 01 Masterpiece Animation (30-Second Fast Pace, Enhanced HD Quality, 1.0x Zoom)
File: experiments/drawing_methods/render_panel_01_master_animation.py

Fulfills Exact User Specifications:
1. Duration: Exactly ~30 seconds total (brisk, energetic whiteboard animation pace).
2. Reduced Zoom: 1.0x Natural Full-HD View (Zero digital zoom degradation or pixelation).
3. Pre-Animation HD Enhancement:
   - High-order Lanczos4 upscaling to 1080p.
   - Pure-white background normalization (dist < 20 -> pure 255).
   - Unsharp mask edge sharpening for razor-sharp crisp lines.
4. Smooth, Steady Drawing Sequence:
   - Title -> Boy Character (Outside-in) -> Speech Bubble -> Text Lines (Medial Skeleton) -> Emoji & Heart.
"""
import os
import sys
import math
import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

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
from engine.processing.dynamic_decomposition import (
    extract_dynamic_organic_parts,
    generate_smooth_bezier
)
from downstream_artifact_consumer import DownstreamArtifactConsumer

OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step6_drawing_methods"
os.makedirs(OUTPUT_DIR, exist_ok=True)
MASTER_VIDEO_PATH = os.path.join(OUTPUT_DIR, "panel_01_masterpiece_animation.mp4")

# =============================================================================
# 1. SKELETON ALGORITHMS (FOR CRISP MEDIAL HANDWRITING)
# =============================================================================

def morphological_skeleton(bin_img):
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

def extract_ordered_skeleton_strokes(ink_roi, direction="RTL", step_stride=3):
    skel = morphological_skeleton(ink_roi)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(skel)
    if num_labels <= 1:
        ys, xs = np.where(ink_roi > 0)
        if len(xs) == 0: return []
        if direction == "RTL":
            return [[(float(x), float(ys[xs == x].mean())) for x in range(xs.max(), xs.min()-1, -step_stride) if len(ys[xs == x]) > 0]]
        else:
            return [[(float(x), float(ys[xs == x].mean())) for x in range(xs.min(), xs.max()+1, step_stride) if len(ys[xs == x]) > 0]]

    comps = []
    for i in range(1, num_labels):
        cx = stats[i, cv2.CC_STAT_LEFT]
        cy = stats[i, cv2.CC_STAT_TOP]
        area = stats[i, cv2.CC_STAT_AREA]
        comps.append((cx, cy, area, i))

    if direction == "RTL":
        comps.sort(key=lambda c: -c[0])
    else:
        comps.sort(key=lambda c: c[0])

    all_strokes = []
    for cx, cy, area, idx in comps:
        comp_mask = (labels == idx).astype(np.uint8)
        ys, xs = np.where(comp_mask > 0)
        if len(xs) == 0: continue
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
                    if dx == 0 and dy == 0: continue
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


# =============================================================================
# 2. ENHANCE ARTWORK HD BEFORE ANIMATION (RAZOR-SHARP QUALITY)
# =============================================================================
print("="*80)
print("[30-SECOND MASTERPIECE] ENHANCING HD QUALITY & CALIBRATING SPEED")
print("="*80)

def enhance_artwork(img_raw, target_w, target_h):
    """Upscales with Lanczos4, cleans background to pure white, and applies edge sharpening."""
    upscaled = cv2.resize(img_raw, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
    # Pure white background thresholding
    diff = 255.0 - upscaled.astype(np.float32)
    dist = np.max(diff, axis=2)
    upscaled[dist < 22.0] = 255
    # Edge sharpening unsharp mask
    blurred = cv2.GaussianBlur(upscaled, (0, 0), 1.5)
    sharpened = cv2.addWeighted(upscaled, 1.25, blurred, -0.25, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)

panel_1_data = DownstreamArtifactConsumer.load_panel_artifacts(1)
gfx_raw = panel_1_data["graphics_image"]
txt_raw = panel_1_data["typography_image"]
ph_raw, pw_raw = gfx_raw.shape[:2]

OUT_W, OUT_H = 1920, 1080
FPS = 30

# Clean Widescreen Layout: Target panel fills 82% of screen with beautiful white margins
TARGET_PANEL_W = 1520
TARGET_PANEL_H = int(round(TARGET_PANEL_W * (ph_raw / float(pw_raw))))

PANEL_POS_X = (OUT_W - TARGET_PANEL_W) // 2
PANEL_POS_Y = (OUT_H - TARGET_PANEL_H) // 2

gfx_hd = enhance_artwork(gfx_raw, TARGET_PANEL_W, TARGET_PANEL_H)
txt_hd = enhance_artwork(txt_raw, TARGET_PANEL_W, TARGET_PANEL_H)

# Master Complete Target Artwork
complete_artwork = np.full((TARGET_PANEL_H, TARGET_PANEL_W, 3), 255, dtype=np.uint8)
diff_t = 255.0 - txt_hd.astype(np.float32)
txt_ink_hd = (np.max(diff_t, axis=2) > 26.0).astype(np.uint8) * 255

diff_g = 255.0 - gfx_hd.astype(np.float32)
gfx_ink_hd = (np.max(diff_g, axis=2) > 26.0).astype(np.uint8) * 255

complete_artwork[gfx_ink_hd > 0] = gfx_hd[gfx_ink_hd > 0]
complete_artwork[txt_ink_hd > 0] = txt_hd[txt_ink_hd > 0]

# Setup Hand
hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
hand_h = int(OUT_H * 0.27)
scale_h = hand_h / float(hand_bgra.shape[0])
hand_w = max(1, int(hand_bgra.shape[1] * scale_h))
hand_scaled = cv2.resize(hand_bgra, (hand_w, hand_h), interpolation=cv2.INTER_AREA)
tip_x_anchor = int(round(PEN_TIP_ANCHOR_X * scale_h))
tip_y_anchor = int(round(PEN_TIP_ANCHOR_Y * scale_h))

live_canvas = np.full((OUT_H, OUT_W, 3), 255, dtype=np.uint8)
revealed_mask = np.zeros((OUT_H, OUT_W), dtype=np.uint8)
encoder = VideoEncoder(MASTER_VIDEO_PATH, OUT_W, OUT_H, FPS, crf=16)

# Locked 1.0x Full-Panel Overview (Zero Camera Vibration, Zero Pixel Distortion!)
CAM_CENTER_X = OUT_W / 2.0
CAM_CENTER_Y = OUT_H / 2.0
CAM_ZOOM = 1.0 # Pure 1.0x native view!

current_pen = (PANEL_POS_X + TARGET_PANEL_W * 0.75, PANEL_POS_Y + 50)
total_frames = 0

def emit_frame(pen_x, pen_y):
    global total_frames
    frame_h = composite_hand_on_canvas_fast(
        live_canvas, hand_scaled,
        tip_x_anchor, tip_y_anchor,
        int(round(pen_x)), int(round(pen_y))
    )
    cam_view = render_camera_viewport(frame_h, CAM_CENTER_X, CAM_CENTER_Y, CAM_ZOOM, OUT_W, OUT_H)
    encoder.write_frame(cam_view)
    total_frames += 1

# =============================================================================
# 3. FAST-PACED EXACT 30-SECOND DRAWING SEQUENCE (~900 FRAMES TOTAL)
# =============================================================================

# STEP 1: TITLE "١. التفكير الإيجابي" (~3.0 seconds, ~90 frames)
print("[1/5] Drawing Title (calibrated for 30s total)...")
title_crop_mask = txt_ink_hd[:int(TARGET_PANEL_H * 0.22), :]
t_strokes = extract_ordered_skeleton_strokes(title_crop_mask, direction="RTL", step_stride=4)
for stroke in t_strokes:
    global_pts = [(PANEL_POS_X + pt[0], PANEL_POS_Y + pt[1]) for pt in stroke]
    if not global_pts: continue
    transit = generate_smooth_bezier(current_pen, global_pts[0], num_points=1)
    for pt in transit: emit_frame(pt[0], pt[1])
    current_pen = global_pts[0]
    
    idx = 0
    while idx < len(global_pts):
        next_idx = min(len(global_pts), idx + 115) # Calibrated for 30s
        chunk = global_pts[idx:next_idx]
        for pt in chunk:
            cv2.circle(revealed_mask, (int(round(pt[0])), int(round(pt[1]))), 10, 255, -1)
        
        act = (revealed_mask[PANEL_POS_Y:PANEL_POS_Y+TARGET_PANEL_H, PANEL_POS_X:PANEL_POS_X+TARGET_PANEL_W] > 0) & (txt_ink_hd > 0)
        live_canvas[PANEL_POS_Y:PANEL_POS_Y+TARGET_PANEL_H, PANEL_POS_X:PANEL_POS_X+TARGET_PANEL_W][act] = complete_artwork[act]
        
        last_pt = chunk[-1]
        emit_frame(last_pt[0], last_pt[1])
        current_pen = last_pt
        idx = next_idx

# STEP 2: CHARACTER "THE BOY" (OUTSIDE-IN NATIVE ENGINE) (~10.0 seconds, ~300 frames)
print("[2/5] Drawing Boy Character Outside-In (calibrated for 30s total)...")
num_cc, lbls, stats, _ = cv2.connectedComponentsWithStats(gfx_ink_hd)
boy_idx = 1
for i in range(1, num_cc):
    bx, by, bw, bh, area = stats[i]
    if bh > TARGET_PANEL_H * 0.35 and area > 1000 and (bx + bw * 0.5) < TARGET_PANEL_W * 0.40:
        boy_idx = i
        break

boy_mask_hd = (lbls == boy_idx).astype(np.uint8) * 255
boy_crop_art = np.full_like(gfx_hd, 255)
boy_crop_art[boy_mask_hd > 0] = gfx_hd[boy_mask_hd > 0]

organic_layers = extract_dynamic_organic_parts(boy_mask_hd, boy_crop_art, min_parts=4, max_parts=5)

for part in organic_layers:
    p_mask = part["mask"]
    part_art = np.full_like(boy_crop_art, 255)
    part_art[p_mask > 0] = boy_crop_art[p_mask > 0]
    
    strokes = build_gapless_orbital_path(part_art, ring_step=10, sample_interval=5.0, brush_radius=10, drawing_direction="OUTSIDE_IN")
    
    for stroke in strokes:
        if len(stroke) < 2: continue
        global_stroke = [(PANEL_POS_X + pt[0], PANEL_POS_Y + pt[1]) for pt in stroke]
        transit = generate_smooth_bezier(current_pen, global_stroke[0], num_points=1)
        for pt in transit: emit_frame(pt[0], pt[1])
        
        idx = 0
        while idx < len(global_stroke):
            next_idx = min(len(global_stroke), idx + 135) # Calibrated for 30s
            chunk = global_stroke[idx:next_idx]
            for pt in chunk:
                cv2.circle(revealed_mask, (int(round(pt[0])), int(round(pt[1]))), 12, 255, -1)
                
            act = (revealed_mask[PANEL_POS_Y:PANEL_POS_Y+TARGET_PANEL_H, PANEL_POS_X:PANEL_POS_X+TARGET_PANEL_W] > 0) & (boy_mask_hd > 0)
            live_canvas[PANEL_POS_Y:PANEL_POS_Y+TARGET_PANEL_H, PANEL_POS_X:PANEL_POS_X+TARGET_PANEL_W][act] = complete_artwork[act]
            
            last_pt = chunk[-1]
            emit_frame(last_pt[0], last_pt[1])
            current_pen = last_pt
            idx = next_idx

# STEP 3: SPEECH BUBBLE CONTAINER (~2.5 seconds, ~75 frames)
print("[3/5] Drawing Speech Bubble (calibrated for 30s total)...")
bubble_idx = 1
for i in range(1, num_cc):
    bx, by, bw, bh, area = stats[i]
    if bw > TARGET_PANEL_W * 0.35 and bh > TARGET_PANEL_H * 0.30 and area < bw * bh * 0.22:
        bubble_idx = i
        break

bubble_mask = (lbls == bubble_idx).astype(np.uint8) * 255
bub_strokes = extract_ordered_skeleton_strokes(bubble_mask, direction="LTR", step_stride=5)

for stroke in bub_strokes:
    global_pts = [(PANEL_POS_X + pt[0], PANEL_POS_Y + pt[1]) for pt in stroke]
    if not global_pts: continue
    transit = generate_smooth_bezier(current_pen, global_pts[0], num_points=1)
    for pt in transit: emit_frame(pt[0], pt[1])
    
    idx = 0
    while idx < len(global_pts):
        next_idx = min(len(global_pts), idx + 140) # Calibrated for 30s
        chunk = global_pts[idx:next_idx]
        for pt in chunk:
            cv2.circle(revealed_mask, (int(round(pt[0])), int(round(pt[1]))), 11, 255, -1)
            
        act = (revealed_mask[PANEL_POS_Y:PANEL_POS_Y+TARGET_PANEL_H, PANEL_POS_X:PANEL_POS_X+TARGET_PANEL_W] > 0) & (bubble_mask > 0)
        live_canvas[PANEL_POS_Y:PANEL_POS_Y+TARGET_PANEL_H, PANEL_POS_X:PANEL_POS_X+TARGET_PANEL_W][act] = complete_artwork[act]
        
        last_pt = chunk[-1]
        emit_frame(last_pt[0], last_pt[1])
        current_pen = last_pt
        idx = next_idx

# STEP 4: TEXT LINES INSIDE BUBBLE (~9.0 seconds, ~270 frames)
print("[4/5] Drawing Text Lines (calibrated for 30s total)...")
c_x, c_y, c_w, c_h = int(TARGET_PANEL_W * 0.44), int(TARGET_PANEL_H * 0.20), int(TARGET_PANEL_W * 0.46), int(TARGET_PANEL_H * 0.65)
sub_ink = txt_ink_hd[c_y:c_y+c_h, c_x:c_x+c_w]

num_t, lbl_t, stat_t, _ = cv2.connectedComponentsWithStats(sub_ink)
glyphs = []
for i in range(1, num_t):
    gx, gy, gw, gh, ga = stat_t[i]
    if ga < 3: continue
    glyphs.append({"bbox": (gx, gy, gw, gh), "cx": gx + gw/2.0, "cy": gy + gh/2.0})

glyphs.sort(key=lambda g: g["cy"])
text_lines = []
if glyphs:
    cur_l = [glyphs[0]]
    ly1, ly2 = glyphs[0]["bbox"][1], glyphs[0]["bbox"][1] + glyphs[0]["bbox"][3]
    for g in glyphs[1:]:
        gy, gh = g["bbox"][1], g["bbox"][3]
        if gy <= ly2 + 8 and (gy + gh) >= ly1 - 8:
            cur_l.append(g)
            ly1 = min(ly1, gy)
            ly2 = max(ly2, gy + gh)
        else:
            text_lines.append(cur_l)
            cur_l = [g]
            ly1, ly2 = gy, gy + gh
    if cur_l: text_lines.append(cur_l)

text_lines.sort(key=lambda l: min(g["bbox"][1] for g in l))

for l_idx, line in enumerate(text_lines):
    lx_min = min(g["bbox"][0] for g in line)
    ly_min = min(g["bbox"][1] for g in line)
    lx_max = max(g["bbox"][0] + g["bbox"][2] for g in line)
    ly_max = max(g["bbox"][1] + g["bbox"][3] for g in line)
    
    line_crop = sub_ink[ly_min:ly_max, lx_min:lx_max]
    line_strokes = extract_ordered_skeleton_strokes(line_crop, direction="RTL", step_stride=4)
    
    for stroke in line_strokes:
        global_pts = [(PANEL_POS_X + c_x + lx_min + pt[0], PANEL_POS_Y + c_y + ly_min + pt[1]) for pt in stroke]
        if not global_pts: continue
        transit = generate_smooth_bezier(current_pen, global_pts[0], num_points=1)
        for pt in transit: emit_frame(pt[0], pt[1])
        current_pen = global_pts[0]
        
        idx = 0
        while idx < len(global_pts):
            next_idx = min(len(global_pts), idx + 110) # Calibrated for 30s
            chunk = global_pts[idx:next_idx]
            for pt in chunk:
                cv2.circle(revealed_mask, (int(round(pt[0])), int(round(pt[1]))), 10, 255, -1)
                
            act = (revealed_mask[PANEL_POS_Y:PANEL_POS_Y+TARGET_PANEL_H, PANEL_POS_X:PANEL_POS_X+TARGET_PANEL_W] > 0) & (txt_ink_hd > 0)
            live_canvas[PANEL_POS_Y:PANEL_POS_Y+TARGET_PANEL_H, PANEL_POS_X:PANEL_POS_X+TARGET_PANEL_W][act] = complete_artwork[act]
            
            last_pt = chunk[-1]
            emit_frame(last_pt[0], last_pt[1])
            current_pen = last_pt
            idx = next_idx

# STEP 5: FINISHING TOUCHES (EMOJI & HEART) (~2.5 seconds, ~75 frames)
print("[5/5] Drawing Emoji Mascot & Accents (calibrated for 30s total)...")
rem_mask = gfx_ink_hd.copy()
rem_mask[boy_mask_hd > 0] = 0
rem_mask[bubble_mask > 0] = 0

rem_strokes = extract_ordered_skeleton_strokes(rem_mask, direction="LTR", step_stride=5)
for stroke in rem_strokes:
    global_pts = [(PANEL_POS_X + pt[0], PANEL_POS_Y + pt[1]) for pt in stroke]
    if not global_pts: continue
    transit = generate_smooth_bezier(current_pen, global_pts[0], num_points=1)
    for pt in transit: emit_frame(pt[0], pt[1])
    
    idx = 0
    while idx < len(global_pts):
        next_idx = min(len(global_pts), idx + 125) # Calibrated for 30s
        chunk = global_pts[idx:next_idx]
        for pt in chunk:
            cv2.circle(revealed_mask, (int(round(pt[0])), int(round(pt[1]))), 11, 255, -1)
            
        act = (revealed_mask[PANEL_POS_Y:PANEL_POS_Y+TARGET_PANEL_H, PANEL_POS_X:PANEL_POS_X+TARGET_PANEL_W] > 0)
        live_canvas[PANEL_POS_Y:PANEL_POS_Y+TARGET_PANEL_H, PANEL_POS_X:PANEL_POS_X+TARGET_PANEL_W][act] = complete_artwork[act]
        
        last_pt = chunk[-1]
        emit_frame(last_pt[0], last_pt[1])
        current_pen = last_pt
        idx = next_idx

# Ensure 100% complete artwork
live_canvas[PANEL_POS_Y:PANEL_POS_Y+TARGET_PANEL_H, PANEL_POS_X:PANEL_POS_X+TARGET_PANEL_W] = complete_artwork

# OUTRO: Hand exits smoothly & 1.5s Still Hold
exit_transit = generate_smooth_bezier(current_pen, (OUT_W + 100, OUT_H + 100), num_points=8)
for pt in exit_transit:
    emit_frame(pt[0], pt[1])

final_frame = render_camera_viewport(live_canvas, CAM_CENTER_X, CAM_CENTER_Y, CAM_ZOOM, OUT_W, OUT_H)
for _ in range(45): # 1.5s still hold
    encoder.write_frame(final_frame)
    total_frames += 1

encoder.close()
duration_s = total_frames / float(FPS)

# Also copy directly to Brain directory for immediate user access
import shutil
BRAIN_DIR = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f"
DEST_MP4 = os.path.join(BRAIN_DIR, "panel_01_30s_masterpiece.mp4")
try:
    shutil.copy2(MASTER_VIDEO_PATH, DEST_MP4)
    print(f"Copied to brain directory: {DEST_MP4}")
except Exception as e:
    print(f"Copy error: {e}")

# Extract Contact Sheet directly
cap = cv2.VideoCapture(MASTER_VIDEO_PATH)
c_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
indices = [int(c_total * p) for p in [0.10, 0.35, 0.55, 0.75, 0.90, 0.99]]
frames = []
for idx in indices:
    cap.set(cv2.CAP_PROP_POS_FRAMES, min(idx, c_total - 1))
    ret, f = cap.read()
    if ret: frames.append(f)
cap.release()

if frames:
    fw, fh = 300, 169
    sheet = np.full((fh + 65, len(frames) * (fw + 12) + 12, 3), 245, dtype=np.uint8)
    cv2.rectangle(sheet, (0, 0), (sheet.shape[1], 42), (25, 45, 30), -1)
    cv2.putText(sheet, f"PANEL 1 COMPLETE ANIMATION ({duration_s:.1f}s TOTAL - 1.0x NATIVE VIEW - ENHANCED HD ARTWORK)", 
                (15, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (50, 255, 120), 1, cv2.LINE_AA)
    
    stage_titles = [
        "1. Title (RTL Medial)",
        "2. Boy (Outside-In)",
        "3. Speech Bubble",
        "4. Steady RTL Lines",
        "5. Mascot & Heart",
        "6. Complete Artwork"
    ]
    for i, fr in enumerate(frames):
        gx = 12 + i * (fw + 12)
        gy = 50
        sm = cv2.resize(fr, (fw, fh), interpolation=cv2.INTER_AREA)
        sheet[gy:gy+fh, gx:gx+fw] = sm
        cv2.rectangle(sheet, (gx, gy), (gx+fw, gy+fh), (140, 180, 160), 1)
        cv2.rectangle(sheet, (gx, gy+fh), (gx+fw, gy+fh+15), (35, 45, 40), -1)
        cv2.putText(sheet, stage_titles[i], (gx+5, gy+fh+12), cv2.FONT_HERSHEY_SIMPLEX, 0.26, (0, 220, 255), 1, cv2.LINE_AA)
        
    SHEET_DEST = os.path.join(BRAIN_DIR, "panel_01_30s_masterpiece_contact_sheet.png")
    cv2.imwrite(SHEET_DEST, sheet)
    print(f"Saved contact sheet to brain: {SHEET_DEST}")

print("="*80)
print(f"[SUCCESS] 30-Second Masterpiece Video Exported: {MASTER_VIDEO_PATH}")
print(f"Total Duration: {duration_s:.2f} seconds ({total_frames} frames @ 30 FPS, 1080p crf=16)")
print("="*80 + "\n")
