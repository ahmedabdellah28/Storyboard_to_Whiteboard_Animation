"""
Phase 6 — Master Dynamic Whiteboard Animator for All Panels (01 to 12)
File: experiments/drawing_methods/render_dynamic_panel_master.py

Fully dynamic production engine capable of animating ANY panel (Panel 2, Panel 3, etc.):
1. Universal Zero-Loss Character Engine (Outside-In, zero missing pixels, 100% complete).
2. Fast RTL Typography & Math Handwriting Engine (medial skeleton, fluid cursive flow).
3. Container & Cloud Loop Engine for Speech Bubbles / Boxes.
4. Crystal-Clear Super-Resolution Framing (Zero Pixelation, natural margins).
5. Dynamic entity execution based on validated draw order from Step 5.
"""
import os
import sys
import math
import argparse
import json
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
from downstream_artifact_consumer import DownstreamArtifactConsumer

OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step6_drawing_methods"
BRAIN_DIR = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f"
ORDER_JSON_PATH = r"E:\image_to_animate\experiments\results\step5_draw_priority\fully_dynamic_draw_order.json"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =============================================================================
# SKELETON ALGORITHMS FOR TYPOGRAPHY
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
# MASTER DYNAMIC ANIMATOR FUNCTION
# =============================================================================

def render_dynamic_panel(panel_id: int):
    print("="*80)
    print(f"[DYNAMIC MASTER ANIMATOR] Rendering Panel #{panel_id:02d}...")
    print("="*80)

    # 1. Load Artifacts
    p_data = DownstreamArtifactConsumer.load_panel_artifacts(panel_id)
    gfx_raw = p_data["graphics_image"]
    txt_raw = p_data["typography_image"]
    ph_raw, pw_raw = gfx_raw.shape[:2]

    OUT_W, OUT_H = 1920, 1080
    FPS = 30

    # Natural crystal-clear scale (Zero Pixelation)
    PANEL_W = 980
    PANEL_H = int(round(PANEL_W * (ph_raw / float(pw_raw))))
    POS_X = (OUT_W - PANEL_W) // 2
    POS_Y = (OUT_H - PANEL_H) // 2

    # 2. Super-Resolution Bilateral Anti-Aliasing
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

    # Master Artwork
    master_artwork = np.full((PANEL_H, PANEL_W, 3), 255, dtype=np.uint8)
    master_artwork[dist_g >= 18.0] = gfx_hd[dist_g >= 18.0]
    master_artwork[np.max(diff_t, axis=2) >= 22.0] = txt_hd[np.max(diff_t, axis=2) >= 22.0]

    gfx_ink = (np.max(255.0 - gfx_hd.astype(np.float32), axis=2) > 24.0).astype(np.uint8) * 255
    txt_ink = (np.max(255.0 - txt_hd.astype(np.float32), axis=2) > 22.0).astype(np.uint8) * 255

    # 3. Setup Hand Sprite
    hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
    hand_h = int(OUT_H * 0.22)
    scale_h = hand_h / float(hand_bgra.shape[0])
    hand_w = max(1, int(hand_bgra.shape[1] * scale_h))
    hand_scaled = cv2.resize(hand_bgra, (hand_w, hand_h), interpolation=cv2.INTER_AREA)
    tip_x_anchor = int(round(PEN_TIP_ANCHOR_X * scale_h))
    tip_y_anchor = int(round(PEN_TIP_ANCHOR_Y * scale_h))

    live_canvas = np.full((OUT_H, OUT_W, 3), 255, dtype=np.uint8)
    ink_mask = np.zeros((OUT_H, OUT_W), dtype=np.uint8)

    video_path = os.path.join(OUTPUT_DIR, f"panel_{panel_id:02d}_masterpiece.mp4")
    encoder = VideoEncoder(video_path, OUT_W, OUT_H, FPS, crf=16)

    CAM_CX = OUT_W / 2.0
    CAM_CY = OUT_H / 2.0
    CAM_ZOOM = 1.0

    current_pen = (POS_X + PANEL_W * 0.75, POS_Y + 40)
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

    def draw_character_zero_loss(char_mask, char_crop, bx1, by1, brush_radius=12, step_dist=42.0, ring_step=5):
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

    # 4. Load Step 5 Entity Plan
    order_data = {}
    if os.path.exists(ORDER_JSON_PATH):
        with open(ORDER_JSON_PATH, 'r', encoding='utf-8') as f:
            full_data = json.load(f)
            for p in full_data.get("panels", []):
                if p.get("panel_id") == f"panel_{panel_id:02d}":
                    order_data = p
                    break

    entities = order_data.get("draw_order_dynamic", [])
    print(f"Loaded {len(entities)} dynamic entities for Panel #{panel_id:02d}.")

    # Track rendered pixels
    drawn_gfx_mask = np.zeros_like(gfx_ink)
    drawn_txt_mask = np.zeros_like(txt_ink)

    # 5. Execute Entities in Calibrated Priority Order
    scale_x = PANEL_W / float(pw_raw)
    scale_y = PANEL_H / float(ph_raw)

    for ent in entities:
        cat = ent.get("category", "")
        sub_type = ent.get("sub_type", "")
        bx_raw, by_raw, bw_raw, bh_raw = ent.get("bbox", [0, 0, 0, 0])

        gx1 = max(0, int(round(bx_raw * scale_x)) - 6)
        gy1 = max(0, int(round(by_raw * scale_y)) - 6)
        gx2 = min(PANEL_W, int(round((bx_raw + bw_raw) * scale_x)) + 6)
        gy2 = min(PANEL_H, int(round((by_raw + bh_raw) * scale_y)) + 6)

        print(f"  -> Drawing Entity P{ent.get('priority')}: {ent.get('entity_id')} [{cat} - {sub_type}]")

        # CASE A: Character / Mascot / Emoji (Zero-Loss Outside-In Engine)
        if cat in ["character", "emoji", "mascot"] or "character" in sub_type or "emoji" in sub_type:
            ent_mask = gfx_ink[gy1:gy2, gx1:gx2].copy()
            if cv2.countNonZero(ent_mask) < 10:
                continue
            ent_crop = np.full((gy2 - gy1, gx2 - gx1, 3), 255, dtype=np.uint8)
            ent_crop[ent_mask > 0] = gfx_hd[gy1:gy2, gx1:gx2][ent_mask > 0]
            
            draw_character_zero_loss(ent_mask, ent_crop, gx1, gy1, brush_radius=12, step_dist=40.0, ring_step=5)
            drawn_gfx_mask[gy1:gy2, gx1:gx2] = cv2.bitwise_or(drawn_gfx_mask[gy1:gy2, gx1:gx2], ent_mask)
            
            # Brief 0.2s pause confirming character completion
            for _ in range(6): emit_frame(current_pen[0], current_pen[1], force=True)

        # CASE B: Container (Speech Bubble, Box, Frame)
        elif cat in ["container", "diagram"] or "bubble" in sub_type or "box" in sub_type:
            ent_mask = gfx_ink[gy1:gy2, gx1:gx2].copy()
            if cv2.countNonZero(ent_mask) < 10:
                continue
            c_strokes = extract_ordered_skeleton_strokes(ent_mask, direction="LTR", step_stride=4)
            for stroke in c_strokes:
                global_pts = [(POS_X + gx1 + pt[0], POS_Y + gy1 + pt[1]) for pt in stroke]
                if not global_pts: continue
                air_transit(current_pen, global_pts[0], num_pts=2)
                idx = 0
                while idx < len(global_pts):
                    next_idx = min(len(global_pts), idx + 28)
                    chunk = global_pts[idx:next_idx]
                    for pt in chunk:
                        cv2.circle(ink_mask, (int(round(pt[0])), int(round(pt[1]))), 8, 255, -1)
                    act = (ink_mask[POS_Y+gy1:POS_Y+gy2, POS_X+gx1:POS_X+gx2] > 0) & (ent_mask > 0)
                    live_canvas[POS_Y+gy1:POS_Y+gy2, POS_X+gx1:POS_X+gx2][act] = master_artwork[gy1:gy2, gx1:gx2][act]
                    last_pt = chunk[-1]
                    emit_frame(last_pt[0], last_pt[1])
                    current_pen = last_pt
                    idx = next_idx
            live_canvas[POS_Y+gy1:POS_Y+gy2, POS_X+gx1:POS_X+gx2][ent_mask > 0] = master_artwork[gy1:gy2, gx1:gx2][ent_mask > 0]
            drawn_gfx_mask[gy1:gy2, gx1:gx2] = cv2.bitwise_or(drawn_gfx_mask[gy1:gy2, gx1:gx2], ent_mask)

        # CASE C: Typography / Title / Text Line / Math Formula
        else:
            # Check typography mask in this bbox
            ent_mask = txt_ink[gy1:gy2, gx1:gx2].copy()
            if cv2.countNonZero(ent_mask) < 5:
                # Check graphics mask (some symbols/accents might be classified as text)
                ent_mask = gfx_ink[gy1:gy2, gx1:gx2].copy()
                is_gfx = True
            else:
                is_gfx = False

            if cv2.countNonZero(ent_mask) < 5:
                continue

            dir_mode = "RTL" if ent.get("direction", "RTL") == "RTL" else "LTR"
            t_strokes = extract_ordered_skeleton_strokes(ent_mask, direction=dir_mode, step_stride=3)
            for stroke in t_strokes:
                global_pts = [(POS_X + gx1 + pt[0], POS_Y + gy1 + pt[1]) for pt in stroke]
                if not global_pts: continue
                air_transit(current_pen, global_pts[0], num_pts=1)
                idx = 0
                while idx < len(global_pts):
                    next_idx = min(len(global_pts), idx + 24)
                    chunk = global_pts[idx:next_idx]
                    for pt in chunk:
                        cv2.circle(ink_mask, (int(round(pt[0])), int(round(pt[1]))), 7, 255, -1)
                    act = (ink_mask[POS_Y+gy1:POS_Y+gy2, POS_X+gx1:POS_X+gx2] > 0) & (ent_mask > 0)
                    live_canvas[POS_Y+gy1:POS_Y+gy2, POS_X+gx1:POS_X+gx2][act] = master_artwork[gy1:gy2, gx1:gx2][act]
                    last_pt = chunk[-1]
                    emit_frame(last_pt[0], last_pt[1])
                    current_pen = last_pt
                    idx = next_idx
            live_canvas[POS_Y+gy1:POS_Y+gy2, POS_X+gx1:POS_X+gx2][ent_mask > 0] = master_artwork[gy1:gy2, gx1:gx2][ent_mask > 0]
            if is_gfx:
                drawn_gfx_mask[gy1:gy2, gx1:gx2] = cv2.bitwise_or(drawn_gfx_mask[gy1:gy2, gx1:gx2], ent_mask)
            else:
                drawn_txt_mask[gy1:gy2, gx1:gx2] = cv2.bitwise_or(drawn_txt_mask[gy1:gy2, gx1:gx2], ent_mask)

    # 6. Any Remaining Uncovered Ink (Accents, Rays, Punctuation)
    rem_ink = (gfx_ink > 0) & (drawn_gfx_mask == 0)
    rem_txt = (txt_ink > 0) & (drawn_txt_mask == 0)
    total_rem = cv2.bitwise_or(rem_ink.astype(np.uint8)*255, rem_txt.astype(np.uint8)*255)

    if cv2.countNonZero(total_rem) > 20:
        print("  -> Drawing Finishing Accents & Remaining Symbols...")
        fin_strokes = extract_ordered_skeleton_strokes(total_rem, direction="LTR", step_stride=4)
        for stroke in fin_strokes:
            global_pts = [(POS_X + pt[0], POS_Y + pt[1]) for pt in stroke]
            if not global_pts: continue
            air_transit(current_pen, global_pts[0], num_pts=1)
            idx = 0
            while idx < len(global_pts):
                next_idx = min(len(global_pts), idx + 26)
                chunk = global_pts[idx:next_idx]
                for pt in chunk:
                    cv2.circle(ink_mask, (int(round(pt[0])), int(round(pt[1]))), 8, 255, -1)
                act = (ink_mask[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W] > 0) & (total_rem > 0)
                live_canvas[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W][act] = master_artwork[act]
                last_pt = chunk[-1]
                emit_frame(last_pt[0], last_pt[1])
                current_pen = last_pt
                idx = next_idx

    # Ensure 100% pristine canvas
    live_canvas[POS_Y:POS_Y+PANEL_H, POS_X:POS_X+PANEL_W] = master_artwork

    # 7. Outro: Hand Exit & 2.5s Still Hold
    print("Outro: Hand exit & 2.5s still hold...")
    air_transit(current_pen, (OUT_W + 120, OUT_H + 120), num_pts=12)

    final_view = render_camera_viewport(live_canvas, CAM_CX, CAM_CY, CAM_ZOOM, OUT_W, OUT_H)
    for _ in range(75):
        encoder.write_frame(final_view)
        total_frames += 1

    encoder.close()
    duration_s = total_frames / float(FPS)

    # Copy directly to Brain directory
    dest_mp4 = os.path.join(BRAIN_DIR, f"panel_{panel_id:02d}_dynamic_animation.mp4")
    try:
        shutil.copy2(video_path, dest_mp4)
        print(f"Copied MP4 to Brain: {dest_mp4}")
    except Exception as e:
        print(f"Copy error: {e}")

    # Extract Contact Sheet
    cap = cv2.VideoCapture(video_path)
    c_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    indices = [int(c_total * p) for p in [0.06, 0.22, 0.42, 0.65, 0.85, 0.99]]
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(idx, c_total - 1))
        ret, f = cap.read()
        if ret: frames.append(f)
    cap.release()

    sheet_dest = os.path.join(BRAIN_DIR, f"panel_{panel_id:02d}_dynamic_contact_sheet.png")
    if frames:
        fw, fh = 300, 169
        sheet = np.full((fh + 65, len(frames) * (fw + 12) + 12, 3), 245, dtype=np.uint8)
        cv2.rectangle(sheet, (0, 0), (sheet.shape[1], 42), (25, 45, 30), -1)
        cv2.putText(sheet, f"PANEL #{panel_id:02d} FULLY DYNAMIC WHITEBOARD ANIMATION ({duration_s:.1f}s - 1080p)", 
                    (15, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (50, 255, 120), 1, cv2.LINE_AA)
        for i, fr in enumerate(frames):
            gx = 12 + i * (fw + 12)
            gy = 50
            sm = cv2.resize(fr, (fw, fh), interpolation=cv2.INTER_AREA)
            sheet[gy:gy+fh, gx:gx+fw] = sm
            cv2.rectangle(sheet, (gx, gy), (gx+fw, gy+fh), (140, 180, 160), 1)
        cv2.imwrite(sheet_dest, sheet)
        print(f"Saved contact sheet to brain: {sheet_dest}")

    print("="*80)
    print(f"[SUCCESS] Panel #{panel_id:02d} Video Exported: {video_path}")
    print(f"Total Duration: {duration_s:.2f} seconds ({total_frames} frames @ 30 FPS, 1080p)")
    print("="*80 + "\n")
    return video_path, dest_mp4, sheet_dest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render Dynamic Whiteboard Animation for any panel (1 to 12).")
    parser.add_argument("--panel", type=int, default=None, help="Specific Panel ID to render (1-12).")
    parser.add_argument("--all", action="store_true", help="Render all 12 panels sequentially.")
    parser.add_argument("--start", type=int, default=1, help="Start panel ID for range.")
    parser.add_argument("--end", type=int, default=12, help="End panel ID for range.")
    args = parser.parse_args()

    if args.all:
        print(">>> BATCH RENDERING ALL 12 PANELS SEQUENTIALLY <<<")
        for p_id in range(1, 13):
            render_dynamic_panel(p_id)
    elif args.panel is not None:
        render_dynamic_panel(args.panel)
    else:
        for p_id in range(args.start, args.end + 1):
            render_dynamic_panel(p_id)
