"""
Production Pipeline: End-to-End Storyboard-to-Videos Dynamic Engine
File: experiments/end_to_end_storyboard_to_videos.py

Fulfills User Directive:
"اريد ديناميك الكود ياخذ الصورة ويمر بكل المراحل ثم يخرج لي فيديو لكل بانل"
(The code dynamically takes the storyboard image, runs through all stages, and outputs a video for each panel)

Stages Executed Automatically:
1. Dynamic Panel Discovery & Clean Interior Extraction (Grid / Contour Analysis).
2. Method A Layer Splitting (Graphics vs Typography on pure white).
3. In-Depth Text Line & Accent Auditing (m3_text_line_auditor: line bounds, RTL/LTR ordering).
4. Morphological Entity Classification (Characters, Containers, Text Lines, Accents).
5. 1080p Master Whiteboard Animation Video Generation:
   - 100% Zero-Loss Outside-In Concentric Character Drawing.
   - Strict Line-by-Line RTL Handwriting.
   - Bilateral Edge-Preserving Super-Resolution (Zero Pixelation).
   - Proportional Hand Compositing & Still Outro.
   - Contact Sheet Generation.
"""
import os
import sys
import math
import argparse
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
from m1_panel_extractor import DynamicPanelExtractor
from m2_layer_splitter import MethodALayerSplitter
from m3_text_line_auditor import TextLineAuditor

DEFAULT_STORYBOARD_IMG = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\.user_uploaded\media_1788381312632.jpg"
BASE_OUTPUT_DIR = r"E:\image_to_animate\experiments\results\end_to_end_production"
BRAIN_DIR = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f"
os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)


# =============================================================================
# STAGE 1: DYNAMIC STORYBOARD PANEL EXTRACTION
# =============================================================================

def extract_storyboard_panels(img_path: str) -> list:
    """
    Dynamically extracts all panels from any storyboard image.
    Uses contour discovery or intelligent grid detection with clean border trimming.
    """
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load storyboard image from: {img_path}")
    
    h, w = img.shape[:2]
    print(f"[STAGE 1] Loading Storyboard: {w}x{h} px from {os.path.basename(img_path)}")

    # Try general DynamicPanelExtractor first
    raw_panels = DynamicPanelExtractor.extract_panels(img, border_inset=6)
    
    # If standard contour detection misses corner panels in a 4x3 or 3x2 grid, use grid projection
    if len(raw_panels) not in [4, 6, 8, 9, 12]:
        print(f"  Standard contours found {len(raw_panels)} panels. Applying robust grid projection...")
        # Check aspect ratio to determine grid (4x3 is standard for 12 panels: 1024x682 ~ 1.5)
        if 1.4 <= w / float(h) <= 1.6:
            cols, rows = 4, 3
        elif 1.9 <= w / float(h) <= 2.1:
            cols, rows = 4, 2
        elif 0.9 <= w / float(h) <= 1.1:
            cols, rows = 2, 2
        else:
            cols, rows = 4, 3
            
        cell_w = w / float(cols)
        cell_h = h / float(rows)
        
        panels = []
        for r in range(rows):
            for c in range(cols):
                x1 = int(round(c * cell_w)) + 8
                x2 = int(round((c + 1) * cell_w)) - 8
                y1 = int(round(r * cell_h)) + 7
                y2 = int(round((r + 1) * cell_h)) - 7
                
                # Inset to completely eliminate outer border lines
                crop = img[y1+6:y2-6, x1+6:x2-6]
                p_id = r * cols + c + 1
                panels.append({
                    "panel_id": p_id,
                    "row": r + 1,
                    "col": c + 1,
                    "crop": crop
                })
        print(f"  [STAGE 1 SUCCESS] Extracted all {len(panels)} panels via grid projection.")
        return panels
    else:
        panels = []
        for idx, p in enumerate(raw_panels):
            panels.append({
                "panel_id": idx + 1,
                "crop": p["crop"]
            })
        print(f"  [STAGE 1 SUCCESS] Discovered {len(panels)} panels via contour geometry.")
        return panels


# =============================================================================
# SKELETON ALGORITHMS FOR HANDWRITING
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


# =============================================================================
# STAGE 2 TO 5: MASTER PANEL ANIMATOR
# =============================================================================

def process_and_render_panel(panel_id: int, panel_crop: np.ndarray, out_dir: str, hand_scale_ratio: float = 0.45):
    """
    Executes Stages 2, 3, 4, 5 for a single panel.
    """
    print("="*80)
    print(f"[PIPELINE] PROCESSING PANEL #{panel_id:02d} (Hand Scale: {hand_scale_ratio:.2f})...")
    print("="*80)

    panel_dir = os.path.join(out_dir, f"panel_{panel_id:02d}")
    os.makedirs(panel_dir, exist_ok=True)
    
    cv2.imwrite(os.path.join(panel_dir, "clean_crop.png"), panel_crop)

    # ---------------- STAGE 2: METHOD A LAYER SPLITTING ----------------
    print(f"  [STAGE 2] Splitting Graphics & Typography Layers...")
    split_res = MethodALayerSplitter.split(panel_crop)
    gfx_raw = split_res["graphics_image"]
    txt_raw = split_res["text_image"]
    cv2.imwrite(os.path.join(panel_dir, "graphics.png"), gfx_raw)
    cv2.imwrite(os.path.join(panel_dir, "typography.png"), txt_raw)

    # ---------------- STAGE 3: TEXT LINE & ACCENT AUDITING -------------
    print(f"  [STAGE 3] Performing In-Depth Text Line Auditing...")
    audit_res = TextLineAuditor.audit_lines(txt_raw)
    audited_lines = audit_res["lines"]
    audited_accents = audit_res["accents"]
    cv2.imwrite(os.path.join(panel_dir, "text_lines_audit.png"), audit_res["audit_vis"])
    print(f"    Discovered {len(audited_lines)} text lines + {len(audited_accents)} accents.")

    # ---------------- STAGE 4: FRAMING & SUPER-RESOLUTION --------------
    ph_raw, pw_raw = panel_crop.shape[:2]
    OUT_W, OUT_H = 1920, 1080
    FPS = 30

    PANEL_H = 750
    PANEL_W = int(round(PANEL_H * (pw_raw / float(ph_raw))))
    if PANEL_W > 1100:
        PANEL_W = 1100
        PANEL_H = int(round(PANEL_W * (ph_raw / float(pw_raw))))

    POS_X = (OUT_W - PANEL_W) // 2
    POS_Y = (OUT_H - PANEL_H) // 2

    # Bilateral smoothing (Zero Pixelation)
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

    # ---------------- STAGE 5: VIDEO GENERATION ------------------------
    print(f"  [STAGE 5] Rendering 1080p Whiteboard Animation Video...")
    hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
    hand_h = int(OUT_H * hand_scale_ratio)
    scale_h = hand_h / float(hand_bgra.shape[0])
    hand_w = max(1, int(hand_bgra.shape[1] * scale_h))
    hand_scaled = cv2.resize(hand_bgra, (hand_w, hand_h), interpolation=cv2.INTER_AREA)
    tip_x_anchor = int(round(PEN_TIP_ANCHOR_X * scale_h))
    tip_y_anchor = int(round(PEN_TIP_ANCHOR_Y * scale_h))

    live_canvas = np.full((OUT_H, OUT_W, 3), 255, dtype=np.uint8)
    ink_mask = np.zeros((OUT_H, OUT_W), dtype=np.uint8)

    video_path = os.path.join(panel_dir, f"panel_{panel_id:02d}.mp4")
    encoder = VideoEncoder(video_path, OUT_W, OUT_H, FPS, crf=16)

    CAM_CX = OUT_W / 2.0
    CAM_CY = OUT_H / 2.0
    CAM_ZOOM = 1.0

    current_pen = (POS_X + PANEL_W * 0.70, POS_Y + 40)
    total_frames = 0
    drawing_call_count = 0

    def emit_frame(pen_x, pen_y, force=False):
        nonlocal total_frames, drawing_call_count
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
        nonlocal current_pen
        pts = generate_smooth_bezier(p_from, p_to, num_points=num_pts)
        for pt in pts:
            emit_frame(pt[0], pt[1])
        current_pen = p_to

    def draw_character_zero_loss(char_mask, char_crop, bx1, by1, brush_radius=14, step_dist=42.0, ring_step=6):
        nonlocal current_pen
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
        nonlocal current_pen
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

    # Map audited lines to HD scale
    hd_lines = []
    for l in audited_lines:
        m_up = cv2.resize(l["mask"], (PANEL_W, PANEL_H), interpolation=cv2.INTER_NEAREST)
        hd_lines.append({
            "line_id": l["line_id"],
            "type": l["type"],
            "direction": l["direction"],
            "mask_hd": m_up
        })

    # 1. DRAW TITLE & UNDERLINE (LINES 1 & 2)
    if hd_lines:
        print(f"    -> Drawing Title: Line #1 ({hd_lines[0]['direction']})...")
        draw_single_text_line(hd_lines[0]["mask_hd"], direction=hd_lines[0]["direction"])
        if len(hd_lines) > 1 and hd_lines[1]["type"] == "UNDERLINE":
            draw_single_text_line(hd_lines[1]["mask_hd"], direction=hd_lines[1]["direction"])

    # 2. DRAW GRAPHICS & CHARACTERS (100% ZERO-LOSS)
    num_cc_g, lbls_g, stats_g, _ = cv2.connectedComponentsWithStats(gfx_ink)
    if num_cc_g > 1:
        # Decompose into primary character and supporting items
        # Largest components
        comps = sorted(range(1, num_cc_g), key=lambda i: stats_g[i][4], reverse=True)
        drawn_gfx = np.zeros_like(gfx_ink)
        
        for c_idx in comps:
            area = stats_g[c_idx][4]
            if area < 15: continue
            c_mask = (lbls_g == c_idx).astype(np.uint8) * 255
            ys, xs = np.where(c_mask > 0)
            x1, y1 = max(0, xs.min() - 6), max(0, ys.min() - 6)
            x2, y2 = min(PANEL_W, xs.max() + 6), min(PANEL_H, ys.max() + 6)
            
            c_crop = np.full((y2 - y1, x2 - x1, 3), 255, dtype=np.uint8)
            sub_m = c_mask[y1:y2, x1:x2]
            c_crop[sub_m > 0] = gfx_hd[y1:y2, x1:x2][sub_m > 0]
            
            # Character / large drawing
            print(f"    -> Drawing Graphic Element (Area: {area} px) via Zero-Loss...")
            draw_character_zero_loss(sub_m, c_crop, x1, y1, brush_radius=12, step_dist=38.0, ring_step=5)
            drawn_gfx = cv2.bitwise_or(drawn_gfx, c_mask)
            
        # Any residual graphic linework
        rem_g = (gfx_ink > 0) & (drawn_gfx == 0)
        if cv2.countNonZero(rem_g) > 20:
            live_canvas[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W][rem_g > 0] = master_artwork[rem_g > 0]

    # 3. DRAW BODY TEXT LINES STRICTLY LINE-BY-LINE (RTL)
    body_lines = [l for l in hd_lines if l["type"] == "TEXT_LINE"]
    for l in body_lines:
        print(f"    -> Writing Audited Line #{l['line_id']} ({l['direction']})...")
        draw_single_text_line(l["mask_hd"], direction=l["direction"])
        for _ in range(5): emit_frame(current_pen[0], current_pen[1], force=True)

    # 4. DRAW ACCENTS & SYMBOLS
    for acc in audited_accents:
        acc_hd = cv2.resize(acc["mask"], (PANEL_W, PANEL_H), interpolation=cv2.INTER_NEAREST)
        draw_single_text_line(acc_hd, direction="LTR")

    # 5. OUTRO HOLD & FINALIZE
    live_canvas[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W] = master_artwork
    air_transit(current_pen, (OUT_W + 120, OUT_H + 120), num_pts=12)

    final_view = render_camera_viewport(live_canvas, CAM_CX, CAM_CY, CAM_ZOOM, OUT_W, OUT_H)
    for _ in range(75):
        encoder.write_frame(final_view)
        total_frames += 1

    encoder.close()
    duration_s = total_frames / float(FPS)

    # Copy MP4 to Brain directory
    brain_mp4 = os.path.join(BRAIN_DIR, f"dynamic_panel_{panel_id:02d}.mp4")
    try:
        shutil.copy2(video_path, brain_mp4)
        print(f"  Copied MP4 to Brain: {brain_mp4}")
    except Exception as e:
        print(f"  Copy error: {e}")

    # Generate Contact Sheet
    cap = cv2.VideoCapture(video_path)
    c_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    indices = [int(c_total * p) for p in [0.06, 0.22, 0.42, 0.65, 0.85, 0.99]]
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(idx, c_total - 1))
        ret, f = cap.read()
        if ret: frames.append(f)
    cap.release()

    sheet_path = os.path.join(panel_dir, "contact_sheet.png")
    brain_sheet = os.path.join(BRAIN_DIR, f"dynamic_panel_{panel_id:02d}_contact_sheet.png")
    if frames:
        fw, fh = 300, 169
        sheet = np.full((fh + 65, len(frames) * (fw + 12) + 12, 3), 245, dtype=np.uint8)
        cv2.rectangle(sheet, (0, 0), (sheet.shape[1], 42), (25, 45, 30), -1)
        cv2.putText(sheet, f"PANEL #{panel_id:02d} DYNAMIC PIPELINE VIDEO ({duration_s:.1f}s - 1080p)", 
                    (15, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (50, 255, 120), 1, cv2.LINE_AA)
        for i, fr in enumerate(frames):
            gx = 12 + i * (fw + 12)
            gy = 50
            sm = cv2.resize(fr, (fw, fh), interpolation=cv2.INTER_AREA)
            sheet[gy:gy+fh, gx:gx+fw] = sm
            cv2.rectangle(sheet, (gx, gy), (gx+fw, gy+fh), (140, 180, 160), 1)
        cv2.imwrite(sheet_path, sheet)
        cv2.imwrite(brain_sheet, sheet)
        print(f"  Saved Contact Sheet: {brain_sheet}")

    print(f"[SUCCESS] Panel #{panel_id:02d} Completed: {video_path} ({duration_s:.1f}s)")
    return video_path, brain_mp4, brain_sheet


# =============================================================================
# CLI ENTRYPOINT
# =============================================================================

def run_pipeline(image_path: str, target_panel: int = None, run_all: bool = False, start_p: int = 1, end_p: int = 12, hand_scale: float = 0.45):
    print("*"*80)
    print("STARTING END-TO-END STORYBOARD-TO-VIDEOS PIPELINE")
    print(f"Input Image: {image_path} (Hand Scale: {hand_scale:.2f})")
    print("*"*80)

    panels = extract_storyboard_panels(image_path)
    total_panels = len(panels)
    print(f"Discovered {total_panels} panels in storyboard.")

    if target_panel is not None:
        target_list = [p for p in panels if p["panel_id"] == target_panel]
        if not target_list:
            print(f"Error: Panel {target_panel} not found in {total_panels} discovered panels.")
            return
        p = target_list[0]
        process_and_render_panel(p["panel_id"], p["crop"], BASE_OUTPUT_DIR, hand_scale_ratio=hand_scale)
    elif run_all:
        for p in panels:
            process_and_render_panel(p["panel_id"], p["crop"], BASE_OUTPUT_DIR, hand_scale_ratio=hand_scale)
    else:
        for p in panels:
            if start_p <= p["panel_id"] <= end_p:
                process_and_render_panel(p["panel_id"], p["crop"], BASE_OUTPUT_DIR, hand_scale_ratio=hand_scale)

    print("*"*80)
    print("[PIPELINE COMPLETE] All requested panel videos have been successfully generated!")
    print("*"*80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-End Dynamic Storyboard-to-Videos Pipeline.")
    parser.add_argument("--image", type=str, default=DEFAULT_STORYBOARD_IMG, help="Path to input storyboard image.")
    parser.add_argument("--panel", type=int, default=None, help="Specific panel ID to render (1-based).")
    parser.add_argument("--all", action="store_true", help="Render all discovered panels.")
    parser.add_argument("--start", type=int, default=1, help="Start panel ID.")
    parser.add_argument("--end", type=int, default=2, help="End panel ID.")
    parser.add_argument("--hand-scale", type=float, default=0.45, help="Hand scale ratio relative to canvas height (default: 0.45).")
    args = parser.parse_args()

    run_pipeline(
        image_path=args.image,
        target_panel=args.panel,
        run_all=args.all,
        start_p=args.start,
        end_p=args.end,
        hand_scale=args.hand_scale
    )
