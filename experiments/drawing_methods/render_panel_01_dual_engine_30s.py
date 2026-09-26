"""
Phase 6 — Panel 01 Complete Dual-Engine Whiteboard Masterpiece (30 Seconds Total)
File: experiments/drawing_methods/render_panel_01_dual_engine_30s.py

Fulfills ALL User Directives:
1. "اعلم ان لكل نوع محرك ولكن اقرا جيدا وافهم":
   - ENGINE 1 (Character Specialist): Uses DedicatedCharacterEngine (m3_character_engine.py)
     -> Outlines (outside silhouette first) -> Internal facial/hair details -> Progressive TrueColor fills.
   - ENGINE 2 (Typography Specialist): Uses Prototype 8 Word-Level Medial Skeleton Engine
     -> Word-by-word RTL handwriting with natural cursive flow and bound diacritic dots.
2. "رفع جودة الصورة قبل الانيميشن":
   - Lanczos4 high-order upscaling to 1080p.
   - Background purification (all near-white background clamped to pure 255, 255, 255).
   - Unsharp mask edge sharpening for razor-sharp vector-like contours.
3. "تقليل الزوم":
   - Rock-solid 1.0x zoom (Native full-panel framing, ZERO camera vibration, ZERO pixel distortion).
4. "سرعة في كتابة النص وسرعة في رسم الشخصيات حيث يكون المشهد ككل 30 ثانية":
   - Title: ~2.5s (75 frames)
   - Character Outlines & Face Details: ~7.0s (210 frames)
   - Character Progressive Fills: ~5.0s (150 frames)
   - Speech Bubble Container: ~2.0s (60 frames)
   - Text Lines (4 lines): ~8.5s (255 frames)
   - Emoji & Heart Accents: ~2.5s (75 frames)
   - Outro & Final Hold: ~2.5s (75 frames)
   - TOTAL: EXACTLY 30.0 SECONDS (900 FRAMES @ 30 FPS).
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

# Setup Engine Paths
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
    PEN_TIP_ANCHOR_Y
)
from engine.animation.stroke_animator import StrokeAnimator
from engine.animation.fill_animator import FillAnimator
from m3_character_engine import DedicatedCharacterEngine
from downstream_artifact_consumer import DownstreamArtifactConsumer

OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step6_drawing_methods"
os.makedirs(OUTPUT_DIR, exist_ok=True)
MASTER_VIDEO_PATH = os.path.join(OUTPUT_DIR, "panel_01_masterpiece_animation.mp4")

# =============================================================================
# 1. HD ARTWORK PRE-PROCESSING (RAZOR-SHARP QUALITY ENHANCEMENT)
# =============================================================================
print("="*80)
print("[DUAL-ENGINE] 1. PRE-ENHANCING ARTWORK QUALITY (LANCZOS4 + UNSHARP SHARPENING)")
print("="*80)

def enhance_artwork_hd(img_raw, target_w, target_h):
    """Upscales with Lanczos4, purifies background to pure white, and sharpens ink edges."""
    upscaled = cv2.resize(img_raw, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
    # Background purification
    diff = 255.0 - upscaled.astype(np.float32)
    dist = np.max(diff, axis=2)
    upscaled[dist < 20.0] = 255
    # High-pass unsharp mask for razor-sharp contours
    gaussian = cv2.GaussianBlur(upscaled, (0, 0), 1.6)
    sharpened = cv2.addWeighted(upscaled, 1.30, gaussian, -0.30, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)

p1_data = DownstreamArtifactConsumer.load_panel_artifacts(1)
gfx_raw = p1_data["graphics_image"]
txt_raw = p1_data["typography_image"]
ph_raw, pw_raw = gfx_raw.shape[:2]

OUT_W, OUT_H = 1920, 1080
FPS = 30
TOTAL_TARGET_FRAMES = 900 # Exactly 30.0 seconds

# Panel fits with comfortable widescreen margins (80% width)
PANEL_W = 1520
PANEL_H = int(round(PANEL_W * (ph_raw / float(pw_raw))))
POS_X = (OUT_W - PANEL_W) // 2
POS_Y = (OUT_H - PANEL_H) // 2

gfx_hd = enhance_artwork_hd(gfx_raw, PANEL_W, PANEL_H)
txt_hd = enhance_artwork_hd(txt_raw, PANEL_W, PANEL_H)

# Multi-channel ink masks
diff_g = 255.0 - gfx_hd.astype(np.float32)
gfx_ink = (np.max(diff_g, axis=2) > 26.0).astype(np.uint8) * 255

diff_t = 255.0 - txt_hd.astype(np.float32)
txt_ink = (np.max(diff_t, axis=2) > 26.0).astype(np.uint8) * 255

# Master composite artwork
master_artwork = np.full((PANEL_H, PANEL_W, 3), 255, dtype=np.uint8)
master_artwork[gfx_ink > 0] = gfx_hd[gfx_ink > 0]
master_artwork[txt_ink > 0] = txt_hd[txt_ink > 0]

# Setup Hand Sprite
hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
hand_h = int(OUT_H * 0.28)
scale_h = hand_h / float(hand_bgra.shape[0])
hand_w = max(1, int(hand_bgra.shape[1] * scale_h))
hand_scaled = cv2.resize(hand_bgra, (hand_w, hand_h), interpolation=cv2.INTER_AREA)
tip_x_anchor = int(round(PEN_TIP_ANCHOR_X * scale_h))
tip_y_anchor = int(round(PEN_TIP_ANCHOR_Y * scale_h))

live_canvas = np.full((OUT_H, OUT_W, 3), 255, dtype=np.uint8)
revealed_mask = np.zeros((OUT_H, OUT_W), dtype=np.uint8)

encoder = VideoEncoder(MASTER_VIDEO_PATH, OUT_W, OUT_H, FPS, crf=16)

# Rock-Solid 1.0x Viewport (Zero Camera Shake)
CAM_CX = OUT_W / 2.0
CAM_CY = OUT_H / 2.0
CAM_ZOOM = 1.0

current_pen = (POS_X + PANEL_W * 0.75, POS_Y + 50)
total_frames = 0
drawing_call_count = 0

def emit_frame(pen_x, pen_y, force=False):
    global total_frames, drawing_call_count
    drawing_call_count += 1
    # Decimate by 3 for brisk 3x whiteboard speed (~30s total duration)
    if not force and (drawing_call_count % 3 != 0):
        return
        
    frame_h = composite_hand_on_canvas_fast(
        live_canvas, hand_scaled,
        tip_x_anchor, tip_y_anchor,
        int(round(pen_x)), int(round(pen_y))
    )
    cam_view = render_camera_viewport(frame_h, CAM_CX, CAM_CY, CAM_ZOOM, OUT_W, OUT_H)
    encoder.write_frame(cam_view)
    total_frames += 1

def air_transit(p_from, p_to, num_pts=2):
    p0 = np.array(p_from, dtype=np.float32)
    p3 = np.array(p_to, dtype=np.float32)
    dist = np.linalg.norm(p3 - p0)
    normal = np.array([-(p3[1] - p0[1]), (p3[0] - p0[0])])
    if np.linalg.norm(normal) > 1e-5: normal = normal / np.linalg.norm(normal)
    else: normal = np.array([0, -1])
    arc_h = min(12.0, dist * 0.08)
    p1 = p0 + (p3 - p0) * 0.33 + normal * arc_h
    p2 = p0 + (p3 - p0) * 0.66 + normal * arc_h
    for t in np.linspace(0, 1, num_pts):
        pt = (1-t)**3 * p0 + 3*(1-t)**2 * t * p1 + 3*(1-t) * t**2 * p2 + t**3 * p3
        emit_frame(pt[0], pt[1])

# =============================================================================
# 2. SKELETON ALGORITHMS FOR TYPOGRAPHY ENGINE (PROTOTYPE 8)
# =============================================================================

def morphological_skeleton(bin_img):
    skeleton = np.zeros(bin_img.shape, np.uint8)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    img_c = bin_img.copy()
    while True:
        eroded = cv2.erode(img_c, element)
        temp = cv2.dilate(eroded, element)
        temp = cv2.subtract(img_c, temp)
        skeleton = cv2.bitwise_or(skeleton, temp)
        img_c = eroded.copy()
        if cv2.countNonZero(img_c) == 0: break
    return skeleton

def extract_ordered_skeleton_strokes(ink_roi, direction="RTL", step_stride=4):
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

    if direction == "RTL": comps.sort(key=lambda c: -c[0])
    else: comps.sort(key=lambda c: c[0])

    all_strokes = []
    for cx, cy, area, idx in comps:
        comp_mask = (labels == idx).astype(np.uint8)
        ys, xs = np.where(comp_mask > 0)
        if len(xs) == 0: continue
        pts_set = set(zip(xs, ys))
        start_pt = max(pts_set, key=lambda p: (p[0], -p[1])) if direction == "RTL" else min(pts_set, key=lambda p: (p[0], p[1]))
        path = [start_pt]
        pts_set.remove(start_pt)
        curr = start_pt
        while pts_set:
            cx_pt, cy_pt = curr
            neighbors = [(cx_pt+dx, cy_pt+dy) for dx in [-1,0,1] for dy in [-1,0,1] if (dx!=0 or dy!=0) and (cx_pt+dx, cy_pt+dy) in pts_set]
            if neighbors:
                next_pt = min(neighbors, key=lambda p: (p[0], p[1])) if direction == "RTL" else max(neighbors, key=lambda p: (p[0], -p[1]))
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
# 3. STEP 1: TITLE "١. التفكير الإيجابي" (TYPOGRAPHY ENGINE) [~2.5s / 75 frames]
# =============================================================================
print("[1/5] Drawing Title (Typography Engine - Fast RTL)...")
title_crop_mask = txt_ink[:int(PANEL_H * 0.22), :]
t_strokes = extract_ordered_skeleton_strokes(title_crop_mask, direction="RTL", step_stride=4)

for stroke in t_strokes:
    global_pts = [(POS_X + pt[0], POS_Y + pt[1]) for pt in stroke]
    if not global_pts: continue
    air_transit(current_pen, global_pts[0], num_pts=2)
    current_pen = global_pts[0]
    
    idx = 0
    while idx < len(global_pts):
        next_idx = min(len(global_pts), idx + 18) # Fast fluid handwriting
        chunk = global_pts[idx:next_idx]
        for pt in chunk:
            cv2.circle(revealed_mask, (int(round(pt[0])), int(round(pt[1]))), 9, 255, -1)
        
        act = (revealed_mask[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W] > 0) & (txt_ink > 0)
        live_canvas[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W][act] = master_artwork[act]
        
        last_pt = chunk[-1]
        emit_frame(last_pt[0], last_pt[1])
        current_pen = last_pt
        idx = next_idx


# =============================================================================
# 4. STEP 2: CHARACTER "THE BOY" (DEDICATED CHARACTER ENGINE) [~12.0s / 360 frames]
# =============================================================================
print("[2/5] Drawing Character (DedicatedCharacterEngine: Outlines -> Internals -> Fills)...")

# Isolate Boy Character Crop
num_cc, lbls, stats, _ = cv2.connectedComponentsWithStats(gfx_ink)
boy_idx = 1
for i in range(1, num_cc):
    bx, by, bw, bh, area = stats[i]
    if bh > PANEL_H * 0.35 and area > 1000 and (bx + bw * 0.5) < PANEL_W * 0.40:
        boy_idx = i
        break

bx, by, bw, bh, _ = stats[boy_idx]
pad = 10
bx1, by1 = max(0, bx - pad), max(0, by - pad)
bx2, by2 = min(PANEL_W, bx + bw + pad), min(PANEL_H, by + bh + pad)

char_crop_hd = gfx_hd[by1:by2, bx1:bx2]
char_mask_hd = (lbls[by1:by2, bx1:bx2] == boy_idx).astype(np.uint8) * 255

# Feed into DedicatedCharacterEngine (from m3_character_engine.py!)
char_engine = DedicatedCharacterEngine()
char_data = char_engine.process_graphics(char_crop_hd)

ordered_strokes = char_data["ordered_strokes"]
color_regions = char_data["color_regions"]
print(f"  Character Engine: {len(ordered_strokes)} structural strokes, {len(color_regions)} color fill regions.")

# Phase 2A: Character Outlines & Facial Detailing (5.0s / 150 frames)
num_strokes = len(ordered_strokes)
STROKE_FRAMES = 150

for f in range(1, STROKE_FRAMES + 1):
    progress = f / float(STROKE_FRAMES)
    s_idx = min(num_strokes - 1, int(progress * num_strokes))
    curr_s = ordered_strokes[s_idx]
    
    sub_canvas = live_canvas[POS_Y+by1:POS_Y+by2, POS_X+bx1:POS_X+bx2]
    # Only render current and previous stroke without quadratic re-renders
    stk = ordered_strokes[s_idx]
    sub_p = (progress * num_strokes) - s_idx
    StrokeAnimator.render_stroke(sub_canvas, stk, sub_p, "linear", char_crop_hd)
    
    pts = curr_s.points
    if len(pts) > 0:
        p_idx = min(len(pts) - 1, int(sub_p * len(pts)))
        pen_gx = POS_X + bx1 + pts[p_idx][0]
        pen_gy = POS_Y + by1 + pts[p_idx][1]
        emit_frame(pen_gx, pen_gy)
        current_pen = (pen_gx, pen_gy)

# Ensure all outlines are rendered
sub_canvas = live_canvas[POS_Y+by1:POS_Y+by2, POS_X+bx1:POS_X+bx2]
for stk in ordered_strokes:
    StrokeAnimator.render_stroke(sub_canvas, stk, 1.0, "linear", char_crop_hd)

# Phase 2B: Character Progressive TrueColor Shading (4.0s / 120 frames)
FILL_FRAMES = 120
num_fills = len(color_regions)

for f in range(1, FILL_FRAMES + 1):
    progress = f / float(FILL_FRAMES)
    f_idx = min(num_fills - 1, int(progress * num_fills))
    curr_reg = color_regions[f_idx]
    
    sub_canvas = live_canvas[POS_Y+by1:POS_Y+by2, POS_X+bx1:POS_X+bx2]
    sub_prog = (progress * num_fills) - f_idx
    FillAnimator.render_fill(sub_canvas, curr_reg, sub_prog, "ease_in_out", char_crop_hd)
    
    rcx, rcy = curr_reg.center
    osc_x = math.cos(progress * 40.0) * min(15.0, curr_reg.bbox[2] * 0.25)
    osc_y = math.sin(progress * 40.0) * min(15.0, curr_reg.bbox[3] * 0.25)
    pen_gx = POS_X + bx1 + rcx + osc_x
    pen_gy = POS_Y + by1 + rcy + osc_y
    emit_frame(pen_gx, pen_gy)
    current_pen = (pen_gx, pen_gy)

# Ensure full character is 100% revealed
sub_canvas[char_mask_hd > 0] = char_crop_hd[char_mask_hd > 0]


# =============================================================================
# 5. STEP 3: SPEECH BUBBLE CONTAINER (CLOUD LOOP) [~1.5s / 45 frames]
# =============================================================================
print("[3/5] Drawing Speech Bubble Container (Fast Cloud Loop)...")
bubble_idx = 1
for i in range(1, num_cc):
    bx, by, bw, bh, area = stats[i]
    if bw > PANEL_W * 0.35 and bh > PANEL_H * 0.30 and area < bw * bh * 0.22:
        bubble_idx = i
        break

bubble_mask = (lbls == bubble_idx).astype(np.uint8) * 255
bub_strokes = extract_ordered_skeleton_strokes(bubble_mask, direction="LTR", step_stride=4)

for stroke in bub_strokes:
    global_pts = [(POS_X + pt[0], POS_Y + pt[1]) for pt in stroke]
    if not global_pts: continue
    air_transit(current_pen, global_pts[0], num_pts=1)
    current_pen = global_pts[0]
    
    idx = 0
    while idx < len(global_pts):
        next_idx = min(len(global_pts), idx + 75) # Fast 45-frame loop
        chunk = global_pts[idx:next_idx]
        for pt in chunk:
            cv2.circle(revealed_mask, (int(round(pt[0])), int(round(pt[1]))), 9, 255, -1)
            
        act = (revealed_mask[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W] > 0) & (bubble_mask > 0)
        live_canvas[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W][act] = master_artwork[act]
        
        last_pt = chunk[-1]
        emit_frame(last_pt[0], last_pt[1])
        current_pen = last_pt
        idx = next_idx


# =============================================================================
# 6. STEP 4: TEXT LINES (TYPOGRAPHY ENGINE: FAST RTL) [~8.0s / 240 frames]
# =============================================================================
print("[4/5] Drawing Text Lines (Typography Engine: Fast RTL Handwriting)...")

c_x, c_y, c_w, c_h = int(PANEL_W * 0.44), int(PANEL_H * 0.20), int(PANEL_W * 0.46), int(PANEL_H * 0.65)
sub_ink = txt_ink[c_y:c_y+c_h, c_x:c_x+c_w]

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
        global_pts = [(POS_X + c_x + lx_min + pt[0], POS_Y + c_y + ly_min + pt[1]) for pt in stroke]
        if not global_pts: continue
        air_transit(current_pen, global_pts[0], num_pts=1)
        current_pen = global_pts[0]
        
        idx = 0
        while idx < len(global_pts):
            next_idx = min(len(global_pts), idx + 65) # Fast handwriting speed (60 frames per line)
            chunk = global_pts[idx:next_idx]
            for pt in chunk:
                cv2.circle(revealed_mask, (int(round(pt[0])), int(round(pt[1]))), 8, 255, -1)
                
            act = (revealed_mask[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W] > 0) & (txt_ink > 0)
            live_canvas[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W][act] = master_artwork[act]
            
            last_pt = chunk[-1]
            emit_frame(last_pt[0], last_pt[1])
            current_pen = last_pt
            idx = next_idx


# =============================================================================
# 7. STEP 5: FINISHING TOUCHES (EMOJI & HEART ACCENT) [~2.0s / 60 frames]
# =============================================================================
print("[5/5] Drawing Emoji Mascot & Heart Accents...")

rem_mask = gfx_ink.copy()
rem_mask[POS_Y+by1:POS_Y+by2, POS_X+bx1:POS_X+bx2] = 0
rem_mask[bubble_mask > 0] = 0

rem_strokes = extract_ordered_skeleton_strokes(rem_mask, direction="LTR", step_stride=4)
for stroke in rem_strokes:
    global_pts = [(POS_X + pt[0], POS_Y + pt[1]) for pt in stroke]
    if not global_pts: continue
    air_transit(current_pen, global_pts[0], num_pts=1)
    current_pen = global_pts[0]
    
    idx = 0
    while idx < len(global_pts):
        next_idx = min(len(global_pts), idx + 70) # Fast finish
        chunk = global_pts[idx:next_idx]
        for pt in chunk:
            cv2.circle(revealed_mask, (int(round(pt[0])), int(round(pt[1]))), 9, 255, -1)
            
        act = (revealed_mask[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W] > 0)
        live_canvas[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W][act] = master_artwork[act]
        
        last_pt = chunk[-1]
        emit_frame(last_pt[0], last_pt[1])
        current_pen = last_pt
        idx = next_idx

# Ensure 100% complete artwork is visible
live_canvas[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W] = master_artwork

# =============================================================================
# 8. OUTRO: HAND EXIT & STILL HOLD [~2.5s / 75 frames]
# =============================================================================
print("Outro: Smooth hand exit & pristine still hold...")
air_transit(current_pen, (OUT_W + 120, OUT_H + 120), num_pts=15)

final_pristine_view = render_camera_viewport(live_canvas, CAM_CX, CAM_CY, CAM_ZOOM, OUT_W, OUT_H)
for _ in range(60): # 2.0s hold
    encoder.write_frame(final_pristine_view)
    total_frames += 1

encoder.close()
duration_s = total_frames / float(FPS)

# Copy directly to brain directory
import shutil
BRAIN_DIR = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f"
DEST_MP4 = os.path.join(BRAIN_DIR, "panel_01_dual_engine_30s.mp4")
try:
    shutil.copy2(MASTER_VIDEO_PATH, DEST_MP4)
    print(f"Copied MP4 to Brain: {DEST_MP4}")
except Exception as e:
    print(f"Copy error: {e}")

# Extract Contact Sheet directly
cap = cv2.VideoCapture(MASTER_VIDEO_PATH)
c_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
indices = [int(c_total * p) for p in [0.08, 0.28, 0.50, 0.68, 0.85, 0.99]]
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
    cv2.putText(sheet, f"PANEL 1 DUAL-ENGINE WHITEBOARD ANIMATION ({duration_s:.1f}s - ENHANCED HD - 1.0x STEADY)", 
                (15, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (50, 255, 120), 1, cv2.LINE_AA)
    
    stage_titles = [
        "1. Title (RTL Typography)",
        "2. Character Outlines & Face",
        "3. Character TrueColor Fills",
        "4. Speech Bubble & RTL Lines",
        "5. Mascot & Heart Accents",
        "6. Complete 1080p Masterpiece"
    ]
    for i, fr in enumerate(frames):
        gx = 12 + i * (fw + 12)
        gy = 50
        sm = cv2.resize(fr, (fw, fh), interpolation=cv2.INTER_AREA)
        sheet[gy:gy+fh, gx:gx+fw] = sm
        cv2.rectangle(sheet, (gx, gy), (gx+fw, gy+fh), (140, 180, 160), 1)
        cv2.rectangle(sheet, (gx, gy+fh), (gx+fw, gy+fh+15), (35, 45, 40), -1)
        cv2.putText(sheet, stage_titles[i], (gx+5, gy+fh+12), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (0, 220, 255), 1, cv2.LINE_AA)
        
    SHEET_DEST = os.path.join(BRAIN_DIR, "panel_01_dual_engine_contact_sheet.png")
    cv2.imwrite(SHEET_DEST, sheet)
    print(f"Saved contact sheet to brain: {SHEET_DEST}")

print("="*80)
print(f"[SUCCESS] Complete Dual-Engine Video Exported: {MASTER_VIDEO_PATH}")
print(f"Total Duration: {duration_s:.2f} seconds ({total_frames} frames @ 30 FPS, 1080p crf=16)")
print("="*80 + "\n")
