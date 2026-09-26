"""
Render Whiteboard Animation for Panel 1 of the New Storyboard with In-Depth Text Line Auditing
File: experiments/drawing_methods/render_new_storyboard_panel_01.py

Fulfills User Directive:
"اريد بعد استخراج صورة النص يتم التدقيق فوقها لاستخراج النصوص بدقة اكبر ومعرفة الاسطر"
(After extracting the text image, perform deep auditing over it to extract texts with high accuracy and identify individual lines)
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
    PEN_TIP_ANCHOR_Y,
    build_gapless_orbital_path
)
from engine.processing.dynamic_decomposition import generate_smooth_bezier
from m3_text_line_auditor import TextLineAuditor

OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step6_drawing_methods"
BRAIN_DIR = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f"
MASTER_VIDEO_PATH = os.path.join(OUTPUT_DIR, "new_storyboard_panel_01.mp4")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Load Split Layers from Scratch
crop_interior = cv2.imread(r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\scratch\new_p01_clean_interior.png")
gfx_raw = cv2.imread(r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\scratch\new_p01_graphics.png")
txt_raw = cv2.imread(r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\scratch\new_p01_typography.png")

# =============================================================================
# 2. IN-DEPTH AUDIT & LINE DISCOVERY (STEP 2.5)
# =============================================================================
print("="*80)
print("[TEXT AUDIT] PERFORMING DEEP AUDITING & LINE DISCOVERY ON TYPOGRAPHY LAYER")
print("="*80)

audit_result = TextLineAuditor.audit_lines(txt_raw)
audited_lines = audit_result["lines"]
audited_accents = audit_result["accents"]
audit_vis = audit_result["audit_vis"]

print(f"Audited {len(audited_lines)} distinct text lines + {len(audited_accents)} standalone accents:")
for l in audited_lines:
    bx, by, bw, bh = l["bbox"]
    print(f"  Line #{l['line_id']}: [{l['type']} - {l['direction']}] bbox=({bx},{by},{bw},{bh}), px={l['pixel_count']}")

# Save Audit Visualization Artifact to Brain
AUDIT_VIS_DEST = os.path.join(BRAIN_DIR, "new_p01_text_lines_audit_vis.png")
cv2.imwrite(AUDIT_VIS_DEST, audit_vis)
print(f"Saved Text Lines Audit Visualization to: {AUDIT_VIS_DEST}")

# =============================================================================
# 3. HIGH-DEFINITION RESOLUTION & ANTI-ALIASED PRE-PROCESSING
# =============================================================================
ph_raw, pw_raw = crop_interior.shape[:2]

OUT_W, OUT_H = 1920, 1080
FPS = 30

PANEL_H = 750
PANEL_W = int(round(PANEL_H * (pw_raw / float(ph_raw))))
POS_X = (OUT_W - PANEL_W) // 2
POS_Y = (OUT_H - PANEL_H) // 2

# Super-Resolution Bilateral Smoothing
gfx_up = cv2.resize(gfx_raw, (PANEL_W, PANEL_H), interpolation=cv2.INTER_LANCZOS4)
gfx_clean = cv2.bilateralFilter(gfx_up, d=5, sigmaColor=45, sigmaSpace=45)
diff_g = 255.0 - gfx_clean.astype(np.float32)
dist_g = np.max(diff_g, axis=2)
gfx_clean[dist_g < 18.0] = 255
gaussian = cv2.GaussianBlur(gfx_clean, (0, 0), 1.2)
gfx_hd = cv2.addWeighted(gfx_clean, 1.25, gaussian, -0.25, 0)

txt_up = cv2.resize(txt_raw, (PANEL_W, PANEL_H), interpolation=cv2.INTER_LANCZOS4)
diff_t = 255.0 - txt_up.astype(np.float32)
txt_up[np.max(diff_t, axis=2) < 22.0] = 255
txt_hd = txt_up

master_artwork = np.full((PANEL_H, PANEL_W, 3), 255, dtype=np.uint8)
master_artwork[dist_g >= 18.0] = gfx_hd[dist_g >= 18.0]
master_artwork[np.max(diff_t, axis=2) >= 22.0] = txt_hd[np.max(diff_t, axis=2) >= 22.0]

gfx_ink = (np.max(255.0 - gfx_hd.astype(np.float32), axis=2) > 24.0).astype(np.uint8) * 255
txt_ink = (np.max(255.0 - txt_hd.astype(np.float32), axis=2) > 22.0).astype(np.uint8) * 255

# Setup Hand Sprite
hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
hand_h = int(OUT_H * 0.22)
scale_h = hand_h / float(hand_bgra.shape[0])
hand_w = max(1, int(hand_bgra.shape[1] * scale_h))
hand_scaled = cv2.resize(hand_bgra, (hand_w, hand_h), interpolation=cv2.INTER_AREA)
tip_x_anchor = int(round(PEN_TIP_ANCHOR_X * scale_h))
tip_y_anchor = int(round(PEN_TIP_ANCHOR_Y * scale_h))

live_canvas = np.full((OUT_H, OUT_W, 3), 255, dtype=np.uint8)
ink_mask = np.zeros((OUT_H, OUT_W), dtype=np.uint8)

encoder = VideoEncoder(MASTER_VIDEO_PATH, OUT_W, OUT_H, FPS, crf=16)

CAM_CX = OUT_W / 2.0
CAM_CY = OUT_H / 2.0
CAM_ZOOM = 1.0

current_pen = (POS_X + PANEL_W * 0.70, POS_Y + 40)
total_frames = 0
drawing_call_count = 0

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
    cam_view = render_camera_viewport(frame_h, CAM_CX, CAM_CY, CAM_ZOOM, OUT_W, OUT_H)
    encoder.write_frame(cam_view)
    total_frames += 1

def air_transit(p_from, p_to, num_pts=2):
    global current_pen
    pts = generate_smooth_bezier(p_from, p_to, num_points=num_pts)
    for pt in pts:
        emit_frame(pt[0], pt[1])
    current_pen = p_to

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

def draw_character_zero_loss(char_mask, char_crop, bx1, by1, brush_radius=14, step_dist=42.0, ring_step=6):
    """Universal 100% Zero-Loss Character Engine (Outside-In)."""
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
        if stat_u[i][4] < 3: continue
        comp_m = (lbl_u == i).astype(np.uint8) * 255
        comp_art = np.full_like(char_crop, 255)
        comp_art[comp_m > 0] = char_crop[comp_m > 0]
        sub_s = build_gapless_orbital_path(comp_art, ring_step=max(2, ring_step - 2), sample_interval=2.0, brush_radius=brush_radius, drawing_direction='OUTSIDE_IN')
        core_strokes.extend(sub_s)
        
    all_strokes = main_strokes + core_strokes
    for stroke in all_strokes:
        if len(stroke) < 2: continue
        global_stroke = [(POS_X + bx1 + pt[0], POS_Y + by1 + pt[1]) for pt in stroke]
        air_transit(current_pen, global_stroke[0], num_pts=1)
        last_pt = global_stroke[0]
        accum = 0.0
        for nxt_pt in global_stroke[1:]:
            cv2.line(ink_mask, (int(round(last_pt[0])), int(round(last_pt[1]))),
                               (int(round(nxt_pt[0])), int(round(nxt_pt[1]))), 255, thickness=brush_radius * 2, lineType=cv2.LINE_AA)
            cv2.circle(ink_mask, (int(round(nxt_pt[0])), int(round(nxt_pt[1]))), radius=brush_radius, color=255, thickness=-1, lineType=cv2.LINE_AA)
            accum += math.hypot(nxt_pt[0] - last_pt[0], nxt_pt[1] - last_pt[1])
            if accum >= step_dist:
                act = (ink_mask[POS_Y+by1:POS_Y+by1+char_crop.shape[0], POS_X+bx1:POS_X+bx1+char_crop.shape[1]] > 0) & (char_mask > 0)
                live_canvas[POS_Y+by1:POS_Y+by1+char_crop.shape[0], POS_X+bx1:POS_X+bx1+char_crop.shape[1]][act] = char_crop[act]
                emit_frame(nxt_pt[0], nxt_pt[1])
                accum = 0.0
            last_pt = nxt_pt
        current_pen = last_pt
    live_canvas[POS_Y+by1:POS_Y+by1+char_crop.shape[0], POS_X+bx1:POS_X+bx1+char_crop.shape[1]][char_mask > 0] = char_crop[char_mask > 0]

def draw_single_text_line(line_mask_hd, direction="RTL"):
    """Renders a single audited text line strictly in designated direction."""
    global current_pen
    l_strokes = extract_ordered_skeleton_strokes(line_mask_hd, direction=direction, step_stride=3)
    for stroke in l_strokes:
        global_pts = [(POS_X + pt[0], POS_Y + pt[1]) for pt in stroke]
        if not global_pts: continue
        air_transit(current_pen, global_pts[0], num_pts=1)
        idx = 0
        while idx < len(global_pts):
            next_idx = min(len(global_pts), idx + 24)
            chunk = global_pts[idx:next_idx]
            for pt in chunk: cv2.circle(ink_mask, (int(round(pt[0])), int(round(pt[1]))), 7, 255, -1)
            act = (ink_mask[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W] > 0) & (line_mask_hd > 0)
            live_canvas[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W][act] = master_artwork[act]
            last_pt = chunk[-1]
            emit_frame(last_pt[0], last_pt[1])
            current_pen = last_pt
            idx = next_idx
    live_canvas[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W][line_mask_hd > 0] = master_artwork[line_mask_hd > 0]


# Scale line masks to HD
scale_x = PANEL_W / float(pw_raw)
scale_y = PANEL_H / float(ph_raw)

hd_lines = []
for l in audited_lines:
    m_up = cv2.resize(l["mask"], (PANEL_W, PANEL_H), interpolation=cv2.INTER_NEAREST)
    hd_lines.append({
        "line_id": l["line_id"],
        "type": l["type"],
        "direction": l["direction"],
        "mask_hd": m_up
    })

# =============================================================================
# 4. DRAWING CHOREOGRAPHY WITH AUDITED LINES
# =============================================================================

# STEP 1: Title Line (Line 1)
print(f"[1/7] Writing Audited Title Line #1 ({hd_lines[0]['direction']})...")
draw_single_text_line(hd_lines[0]["mask_hd"], direction=hd_lines[0]["direction"])

# STEP 2: Underline (Line 2)
if len(hd_lines) > 1 and hd_lines[1]["type"] == "UNDERLINE":
    print(f"[2/7] Drawing Title Underline #2 ({hd_lines[1]['direction']})...")
    draw_single_text_line(hd_lines[1]["mask_hd"], direction=hd_lines[1]["direction"])

# STEP 3: Sun Icon (Top-Right Accent)
print("[3/7] Drawing Sun Icon Accent (Top-Right)...")
sun_mask_raw = np.zeros((ph_raw, pw_raw), dtype=np.uint8)
for acc in audited_accents:
    ax, ay = acc["bbox"][0], acc["bbox"][1]
    if ax > pw_raw * 0.70 and ay < ph_raw * 0.35:
        sun_mask_raw = cv2.bitwise_or(sun_mask_raw, acc["mask"])

if cv2.countNonZero(sun_mask_raw) > 0:
    sun_hd = cv2.resize(sun_mask_raw, (PANEL_W, PANEL_H), interpolation=cv2.INTER_NEAREST)
    draw_single_text_line(sun_hd, direction="LTR")

# STEP 4: Character (Boy in Green Hoodie - 100% Zero-Loss)
print("[4/7] Drawing Character (Boy in Green Hoodie): 100% Zero-Loss Outside-In...")
num_cc, lbls, stats, _ = cv2.connectedComponentsWithStats(gfx_ink)
boy_mask = np.zeros_like(gfx_ink)
for i in range(1, num_cc):
    bx, by, bw, bh, area = stats[i]
    cx = bx + bw * 0.5
    if cx > PANEL_W * 0.45 and by < PANEL_H * 0.75 and area > 100:
        boy_mask[lbls == i] = 255

ys, xs = np.where(boy_mask > 0)
bx1, by1 = max(0, xs.min() - 8), max(0, ys.min() - 8)
bx2, by2 = min(PANEL_W, xs.max() + 8), min(PANEL_H, ys.max() + 8)
boy_crop = np.full((by2 - by1, bx2 - bx1, 3), 255, dtype=np.uint8)
b_sub = boy_mask[by1:by2, bx1:bx2]
boy_crop[b_sub > 0] = gfx_hd[by1:by2, bx1:bx2][b_sub > 0]

draw_character_zero_loss(b_sub, boy_crop, bx1, by1, brush_radius=14, step_dist=42.0, ring_step=6)
for _ in range(8): emit_frame(current_pen[0], current_pen[1], force=True)

# STEP 5: Desk Elements & Notepad Checklist
print("[5/7] Drawing Desk, Potted Plant, Coffee Mug & Notepad...")
rem_gfx = gfx_ink.copy()
rem_gfx[boy_mask > 0] = 0

ys_r, xs_r = np.where(rem_gfx > 0)
if len(xs_r) > 0:
    rx1, ry1 = max(0, xs_r.min() - 6), max(0, ys_r.min() - 6)
    rx2, ry2 = min(PANEL_W, xs_r.max() + 6), min(PANEL_H, ys_r.max() + 6)
    r_sub = rem_gfx[ry1:ry2, rx1:rx2]
    r_crop = np.full((ry2 - ry1, rx2 - rx1, 3), 255, dtype=np.uint8)
    r_crop[r_sub > 0] = gfx_hd[ry1:ry2, rx1:rx2][r_sub > 0]
    draw_character_zero_loss(r_sub, r_crop, rx1, ry1, brush_radius=12, step_dist=36.0, ring_step=5)

# STEP 6: Audited Motivational Text Lines (Line 3, Line 4, Line 5)
print("[6/7] Writing Audited Motivational Text Lines (Strict RTL Line-by-Line)...")
text_lines_to_draw = [l for l in hd_lines if l["type"] == "TEXT_LINE"]
for l in text_lines_to_draw:
    print(f"  -> Writing Audited Line #{l['line_id']} (RTL)...")
    draw_single_text_line(l["mask_hd"], direction="RTL")
    # Brief 0.15s pause between lines
    for _ in range(5): emit_frame(current_pen[0], current_pen[1], force=True)

# STEP 7: Heart Accent (Bottom-Left)
print("[7/7] Drawing Heart Accent (Bottom-Left)...")
heart_mask_raw = np.zeros((ph_raw, pw_raw), dtype=np.uint8)
for acc in audited_accents:
    ax, ay = acc["bbox"][0], acc["bbox"][1]
    if ax < pw_raw * 0.35 and ay > ph_raw * 0.65:
        heart_mask_raw = cv2.bitwise_or(heart_mask_raw, acc["mask"])

if cv2.countNonZero(heart_mask_raw) > 0:
    heart_hd = cv2.resize(heart_mask_raw, (PANEL_W, PANEL_H), interpolation=cv2.INTER_NEAREST)
    draw_single_text_line(heart_hd, direction="LTR")

# 100% Canvas Guarantee
live_canvas[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W] = master_artwork

# Outro: Hand Exit & 2.5s Still Hold
print("Outro: Hand exit & 2.5s still hold...")
air_transit(current_pen, (OUT_W + 120, OUT_H + 120), num_pts=12)

final_view = render_camera_viewport(live_canvas, CAM_CX, CAM_CY, CAM_ZOOM, OUT_W, OUT_H)
for _ in range(75):
    encoder.write_frame(final_view)
    total_frames += 1

encoder.close()
duration_s = total_frames / float(FPS)

# Copy to Brain
DEST_MP4 = os.path.join(BRAIN_DIR, "new_storyboard_panel_01.mp4")
try:
    shutil.copy2(MASTER_VIDEO_PATH, DEST_MP4)
    print(f"Copied MP4 to Brain: {DEST_MP4}")
except Exception as e:
    print(f"Copy error: {e}")

# Contact Sheet
cap = cv2.VideoCapture(MASTER_VIDEO_PATH)
c_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
indices = [int(c_total * p) for p in [0.06, 0.22, 0.42, 0.65, 0.85, 0.99]]
frames = []
for idx in indices:
    cap.set(cv2.CAP_PROP_POS_FRAMES, min(idx, c_total - 1))
    ret, f = cap.read()
    if ret: frames.append(f)
cap.release()

sheet_dest = os.path.join(BRAIN_DIR, "new_storyboard_panel_01_contact_sheet.png")
if frames:
    fw, fh = 300, 169
    sheet = np.full((fh + 65, len(frames) * (fw + 12) + 12, 3), 245, dtype=np.uint8)
    cv2.rectangle(sheet, (0, 0), (sheet.shape[1], 42), (25, 45, 30), -1)
    cv2.putText(sheet, f"AUDITED TEXT LINES - PANEL 01 ('EBDAA YAWMAK') ({duration_s:.1f}s - 1080p)", 
                (15, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (50, 255, 120), 1, cv2.LINE_AA)
    
    stage_titles = [
        "1. Audited Title L1 & Sun",
        "2. Character (100% Zero-Loss)",
        "3. Desk, Plant & Notepad",
        "4. Audited Text Line #3 (RTL)",
        "5. Audited Lines #4 & #5 (RTL)",
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
        
    cv2.imwrite(sheet_dest, sheet)
    print(f"Saved contact sheet to brain: {sheet_dest}")

print("="*80)
print(f"[SUCCESS] Audited Panel 1 Exported: {MASTER_VIDEO_PATH}")
print(f"Total Duration: {duration_s:.2f} seconds ({total_frames} frames @ 30 FPS, 1080p)")
print("="*80 + "\n")
