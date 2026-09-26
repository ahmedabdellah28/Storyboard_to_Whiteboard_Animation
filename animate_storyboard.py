"""
========================================================================================================================
UNIVERSAL 2026 CINEMATIC STORYBOARD WHITEBOARD ANIMATOR (MASTER PRODUCTION ENGINE)
========================================================================================================================
1. Dynamic Panel Discovery & Perimeter Border Suppression via DynamicBorderDetector.
2. 4K UHD Master Whiteboard Canvas (3840x2160) on 100% Pure White (255, 255, 255).
3. 2026 Balanced Cinematic Camera Director:
   - Default balanced focus zoom (1.40x) with comfortable margins.
   - Parallax Crane Pullback (1.10x) during smooth inter-panel travel.
   - Natural Rotational Banking Tilt (±1.4°).
   - Grand Master Outro Reveal (Whole canvas showcase).
4. Subpixel Screen-Space Pen Tip Tracking: 100% micro-exact ink-to-tip alignment.
5. High-Speed Arabic Typography Engine: Line-by-line handwriting via skeleton strokes.
6. Zero-Loss Concentric Character & Graphic Inking.

Usage:
  python animate_storyboard.py --image path/to/image.jpg [--output output.mp4] [--zoom 1.40] [--fps 30]
========================================================================================================================
"""
import os
import sys
import argparse
import math
import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(_root, 'kivy'))
sys.path.insert(0, os.path.join(_root, 'experiments', 'modular_pipeline'))

from engine.video.encoder import VideoEncoder
from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
from engine.render.concentric_engine import (
    DEFAULT_HAND_PATH,
    DEFAULT_HAND_MASK_PATH,
    PEN_TIP_ANCHOR_X,
    PEN_TIP_ANCHOR_Y,
    build_gapless_orbital_path
)
from engine.processing.dynamic_border_detector import DynamicBorderDetector
from m1_panel_extractor import DynamicPanelExtractor
from m2_layer_splitter import MethodALayerSplitter
from m3_text_line_auditor import TextLineAuditor


def smootherstep(t: float) -> float:
    """Quintic smootherstep curve: 6t^5 - 15t^4 + 10t^3."""
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (6.0 * t - 15.0) + 10.0)


def get_camera_affine_matrix(
    center_x: float,
    center_y: float,
    zoom_scale: float,
    tilt_deg: float = 0.0,
    out_w: int = 1920,
    out_h: int = 1080
) -> np.ndarray:
    zoom_scale = max(0.2, zoom_scale)
    vw = out_w / zoom_scale
    vh = out_h / zoom_scale

    angle_rad = math.radians(tilt_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    half_w = vw / 2.0
    half_h = vh / 2.0

    p0 = (-half_w, -half_h)
    p1 = (half_w, -half_h)
    p2 = (-half_w, half_h)

    src_pts = np.float32([
        [center_x + p0[0] * cos_a - p0[1] * sin_a, center_y + p0[0] * sin_a + p0[1] * cos_a],
        [center_x + p1[0] * cos_a - p1[1] * sin_a, center_y + p1[0] * sin_a + p1[1] * cos_a],
        [center_x + p2[0] * cos_a - p2[1] * sin_a, center_y + p2[0] * sin_a + p2[1] * cos_a]
    ])

    dst_pts = np.float32([[0, 0], [out_w, 0], [0, out_h]])
    return cv2.getAffineTransform(src_pts, dst_pts)


def render_camera_viewport_with_matrix(
    canvas: np.ndarray,
    matrix: np.ndarray,
    out_w: int = 1920,
    out_h: int = 1080
) -> np.ndarray:
    return cv2.warpAffine(
        canvas,
        matrix,
        (out_w, out_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255)
    )


def canvas_to_screen_pt(matrix: np.ndarray, pt: tuple) -> tuple:
    p = np.array([pt[0], pt[1], 1.0], dtype=np.float32)
    scr = matrix @ p
    return (float(scr[0]), float(scr[1]))


def enhance_panel_clarity_and_vibrance(crop: np.ndarray, target_w: int, target_h: int) -> tuple:
    # 1. Dynamic Border Detection and Stripping
    border_res = DynamicBorderDetector.detect_and_trim_panel_border(crop)
    clean_crop = border_res["clean_crop"]

    # 2. Color Vibrance Boost (+25% Saturation)
    hsv = cv2.cvtColor(clean_crop, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.25, 0, 255)
    boosted = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # 3. Lanczos Super-Sampling
    hd = cv2.resize(boosted, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

    # 4. Edge-Preserving Bilateral Smoothing
    clean = cv2.bilateralFilter(hd, d=7, sigmaColor=45, sigmaSpace=45)

    # 5. Unsharp Masking
    gaussian = cv2.GaussianBlur(clean, (0, 0), 1.3)
    sharp = cv2.addWeighted(clean, 1.40, gaussian, -0.40, 0)

    # 6. Pure White Background Thresholding
    gray = cv2.cvtColor(sharp, cv2.COLOR_BGR2GRAY)
    sharp[gray > 235] = [255, 255, 255]

    return sharp, clean_crop


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
        if cv2.countNonZero(img_c) == 0:
            break
    return skeleton


def extract_ordered_skeleton_strokes(ink_roi, direction="RTL", step_stride=3):
    skel = morphological_skeleton(ink_roi)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(skel)
    if num_labels <= 1:
        ys, xs = np.where(ink_roi > 0)
        if len(xs) == 0:
            return []
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
        if len(xs) == 0:
            continue
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


def generate_natural_bezier_flight(p_start, p_end, num_points=10, arch_factor=0.20):
    p0 = np.array(p_start, dtype=np.float32)
    p3 = np.array(p_end, dtype=np.float32)
    dist = np.linalg.norm(p3 - p0)

    lift = -min(180.0, max(30.0, dist * arch_factor))
    p1 = p0 + (p3 - p0) * 0.25 + np.array([0, lift * 0.8], dtype=np.float32)
    p2 = p0 + (p3 - p0) * 0.75 + np.array([0, lift * 0.9], dtype=np.float32)

    pts = []
    for t in np.linspace(0, 1, num_points):
        pt = (1-t)**3 * p0 + 3*(1-t)**2 * t * p1 + 3*(1-t) * t**2 * p2 + t**3 * p3
        pts.append((float(pt[0]), float(pt[1])))
    return pts


def extract_storyboard_panels_dynamically(img_path: str):
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load storyboard image from: {img_path}")

    h, w = img.shape[:2]
    raw_panels = DynamicPanelExtractor.extract_panels(img, border_inset=0)

    if len(raw_panels) not in [4, 6, 8, 9, 12]:
        if 1.35 <= w / float(h) <= 1.65:
            cols, rows = 4, 3
        elif 1.85 <= w / float(h) <= 2.15:
            cols, rows = 4, 2
        elif 0.85 <= w / float(h) <= 1.15:
            cols, rows = 2, 2
        else:
            cols, rows = 4, 3

        cell_w = w / float(cols)
        cell_h = h / float(rows)

        panels = []
        for r in range(rows):
            for c in range(cols):
                x1 = int(round(c * cell_w))
                x2 = int(round((c + 1) * cell_w))
                y1 = int(round(r * cell_h))
                y2 = int(round((r + 1) * cell_h))

                crop = img[y1:y2, x1:x2].copy()
                p_id = r * cols + c + 1
                panels.append({
                    "panel_id": p_id,
                    "row": r,
                    "col": c,
                    "crop": crop
                })
        return panels, cols, rows
    else:
        panels = []
        cols = 4 if len(raw_panels) >= 8 else (2 if len(raw_panels) <= 4 else 3)
        rows = int(np.ceil(len(raw_panels) / float(cols)))
        for idx, p in enumerate(raw_panels):
            r = idx // cols
            c = idx % cols
            panels.append({
                "panel_id": idx + 1,
                "row": r,
                "col": c,
                "crop": p["crop"]
            })
        return panels, cols, rows


def run_cinematic_storyboard_2026(image_path, output_video_path=None, zoom_level=1.40, fps=30, progress_cb=None, drawing_speed=1.5, char_speed=None, text_speed=None):
    """
    Main universal 2026 production rendering entry point.
    """
    print("=================================================================")
    print("UNIVERSAL 2026 CINEMATIC STORYBOARD WHITEBOARD ANIMATOR")
    print(f"Input Image: {image_path}")
    print(f"Calibrated Focus Zoom: {zoom_level:.2f}x | 100% Pure White & Dynamic Border-Free")
    print("=================================================================")

    if not os.path.exists(image_path):
        print(f"Error: Image not found: {image_path}")
        return False

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    out_dir = os.path.join(_root, 'output_animations')
    os.makedirs(out_dir, exist_ok=True)

    if output_video_path is None:
        output_video_path = os.path.join(out_dir, f"{base_name}_2026_cinematic.mp4")

    # 1. Discover Panels
    print("\n[Step 1] Extracting Storyboard Panels (Border-Free)...")
    if progress_cb: progress_cb(5.0, "Extracting panels...")
    panels_data, grid_cols, grid_rows = extract_storyboard_panels_dynamically(image_path)
    num_p = len(panels_data)
    print(f"  • Extracted {num_p} clean interior panels ({grid_cols} cols x {grid_rows} rows).")

    # 2. Master Canvas Layout on 4K UHD Master Canvas (3840x2160)
    canvas_w, canvas_h = 3840, 2160
    out_w, out_h = 1920, 1080

    if num_p <= 4:
        target_p_h = 780
        gap_x = 90
        gap_y = 0
    elif num_p <= 6:
        target_p_h = 660
        gap_x = 100
        gap_y = 80
    elif num_p <= 9:
        target_p_h = 490
        gap_x = 80
        gap_y = 60
    else:
        target_p_h = 480
        gap_x = 64
        gap_y = 52

    first_crop = panels_data[0]["crop"]
    aspect = first_crop.shape[1] / float(first_crop.shape[0])
    p_w_scaled = int(round(target_p_h * aspect))

    total_grid_w = grid_cols * p_w_scaled + (grid_cols - 1) * gap_x
    total_grid_h = grid_rows * target_p_h + (grid_rows - 1) * gap_y
    start_x = max(40, (canvas_w - total_grid_w) // 2)
    start_y = max(40, (canvas_h - total_grid_h) // 2)

    # Pure White Canvas
    live_canvas = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)
    ink_mask = np.zeros((canvas_h, canvas_w), dtype=np.uint8)

    target_panel_zoom = float(zoom_level) if zoom_level is not None else 1.40
    print(f"  • 4K Master Canvas: Pure White ({canvas_w}x{canvas_h}), Center Focus Zoom: {target_panel_zoom:.2f}x")

    # 3. Process Panel Layers with Super-Resolution & Typography
    print("\n[Step 2] Processing Super-Resolution & Typography per Panel...")
    if progress_cb: progress_cb(15.0, "Auditing typography & graphics...")
    panel_layouts = []

    for p_info in panels_data:
        p_id = p_info["panel_id"]
        row_i = p_info["row"]
        col_i = p_info["col"]
        crop = p_info["crop"]

        px = start_x + col_i * (p_w_scaled + gap_x)
        py = start_y + row_i * (target_p_h + gap_y)

        artwork_hd, clean_crop = enhance_panel_clarity_and_vibrance(crop, p_w_scaled, target_p_h)

        # Method A Layer Splitting
        split_res = MethodALayerSplitter.split(clean_crop)
        gfx_raw = split_res["graphics_image"]
        txt_raw = split_res["text_image"]

        # Typography Line Auditing
        audit_res = TextLineAuditor.audit_lines(txt_raw)
        audited_lines = audit_res["lines"]
        audited_accents = audit_res["accents"]

        gfx_up = cv2.resize(gfx_raw, (p_w_scaled, target_p_h), interpolation=cv2.INTER_LANCZOS4)
        gfx_clean = cv2.bilateralFilter(gfx_up, d=5, sigmaColor=45, sigmaSpace=45)
        diff_g = 255.0 - gfx_clean.astype(np.float32)
        dist_g = np.max(diff_g, axis=2)
        gfx_clean[dist_g < 18.0] = 255
        gaussian = cv2.GaussianBlur(gfx_clean, (0, 0), 1.2)
        gfx_hd = cv2.addWeighted(gfx_clean, 1.35, gaussian, -0.35, 0)

        gfx_ink = (np.max(255.0 - gfx_hd.astype(np.float32), axis=2) > 22.0).astype(np.uint8) * 255

        hd_lines = []
        for l in audited_lines:
            m_up = cv2.resize(l["mask"], (p_w_scaled, target_p_h), interpolation=cv2.INTER_NEAREST)
            hd_lines.append({
                "line_id": l["line_id"],
                "type": l["type"],
                "direction": l["direction"],
                "mask_hd": m_up
            })

        hd_accents = []
        for acc in audited_accents:
            acc_hd = cv2.resize(acc["mask"], (p_w_scaled, target_p_h), interpolation=cv2.INTER_NEAREST)
            hd_accents.append(acc_hd)

        panel_layouts.append({
            "panel_id": p_id,
            "name": f"panel_{p_id:02d}",
            "x1": px, "y1": py,
            "w": p_w_scaled, "h": target_p_h,
            "center_x": px + p_w_scaled / 2.0,
            "center_y": py + target_p_h / 2.0,
            "row": row_i,
            "col": col_i,
            "artwork_hd": artwork_hd,
            "gfx_hd": gfx_hd,
            "gfx_ink": gfx_ink,
            "hd_lines": hd_lines,
            "hd_accents": hd_accents
        })

    # 4. Load Hand Sprite for Native 1080p Screen Space
    hand_bgra_master = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
    hand_screen_h = int(out_h * 0.38) # Standard 38% screen height (~410px)
    scale_h_scr = hand_screen_h / float(hand_bgra_master.shape[0])
    hand_screen_w = max(1, int(hand_bgra_master.shape[1] * scale_h_scr))
    hand_screen = cv2.resize(hand_bgra_master, (hand_screen_w, hand_screen_h), interpolation=cv2.INTER_AREA)
    tip_x_screen = int(round(PEN_TIP_ANCHOR_X * scale_h_scr))
    tip_y_screen = int(round(PEN_TIP_ANCHOR_Y * scale_h_scr))

    # 5. Render Master Video
    print(f"\n[Step 3] Rendering 2026 Master Video: {output_video_path}...")
    if progress_cb: progress_cb(25.0, "Rendering cinematic animation...")
    encoder = VideoEncoder(output_video_path, out_w, out_h, fps, crf=16)

    total_frames = 0
    full_board_center = (canvas_w / 2.0, canvas_h / 2.0)
    full_board_zoom = out_w / float(canvas_w) # 0.5x

    cur_cam_pos = full_board_center
    cur_zoom = full_board_zoom
    cur_tilt = 0.0

    # INTRO SWOOP: Full Board -> Panel 1
    p1 = panel_layouts[0]
    p1_center = (p1["center_x"], p1["center_y"])
    intro_frames = 18
    for i in range(intro_frames):
        t_norm = (i + 1) / float(intro_frames)
        t_ease = smootherstep(t_norm)

        cam_x = full_board_center[0] + (p1_center[0] - full_board_center[0]) * t_ease
        cam_y = full_board_center[1] + (p1_center[1] - full_board_center[1]) * t_ease
        cam_zoom = full_board_zoom + (target_panel_zoom - full_board_zoom) * t_ease
        tilt = math.sin(t_ease * math.pi) * 0.7

        M = get_camera_affine_matrix(cam_x, cam_y, cam_zoom, tilt, out_w, out_h)
        frame = render_camera_viewport_with_matrix(live_canvas, M, out_w, out_h)
        encoder.write_frame(frame)
        total_frames += 1

    cur_cam_pos = p1_center
    cur_zoom = target_panel_zoom
    cur_tilt = 0.0
    current_pen = (p1["x1"] + p1["w"] * 0.75, p1["y1"] + 65.0)

    # Subpixel Screen-Space frame emitter
    drawing_call_count = 0

    def emit_frame_exact(pen_canvas_x, pen_canvas_y, cam_x, cam_y, zoom_z, tilt_deg, force=False):
        nonlocal total_frames, drawing_call_count
        drawing_call_count += 1

        M = get_camera_affine_matrix(cam_x, cam_y, zoom_z, tilt_deg, out_w, out_h)
        viewport_view = render_camera_viewport_with_matrix(live_canvas, M, out_w, out_h)

        scr_x, scr_y = canvas_to_screen_pt(M, (pen_canvas_x, pen_canvas_y))

        final_frame = composite_hand_on_canvas_fast(
            viewport_view, hand_screen,
            tip_x_screen, tip_y_screen,
            int(round(scr_x)), int(round(scr_y))
        )
        encoder.write_frame(final_frame)
        total_frames += 1

    def air_flight(p_from, p_to, num_pts=2, arch_factor=0.15):
        nonlocal current_pen
        pts = generate_natural_bezier_flight(p_from, p_to, num_points=num_pts, arch_factor=arch_factor)
        for pt in pts:
            emit_frame_exact(pt[0], pt[1], cur_cam_pos[0], cur_cam_pos[1], cur_zoom, cur_tilt, force=True)
        current_pen = p_to

    # EXACT HANDWRITING ENGINE (~20-25s per panel)
    def draw_text_line_exact(line_mask_hd, pos_x, pos_y, artwork_hd, direction="RTL", brush_r=10, step_dist=14.0):
        nonlocal current_pen
        l_strokes = extract_ordered_skeleton_strokes(line_mask_hd, direction=direction, step_stride=3)

        accum = 0.0
        for s_idx, stroke in enumerate(l_strokes):
            global_pts = [(pos_x + pt[0], pos_y + pt[1]) for pt in stroke]
            if len(global_pts) < 1:
                continue

            hop_dist = math.hypot(global_pts[0][0] - current_pen[0], global_pts[0][1] - current_pen[1])
            if s_idx == 0:
                flight_pts = max(1, int(round(3.0 / max(0.5, text_s)))) if hop_dist > 80.0 else 1
                air_flight(current_pen, global_pts[0], num_pts=flight_pts, arch_factor=0.10)
            elif hop_dist > 45.0:
                flight_pts = max(1, int(round(2.0 / max(0.5, text_s)))) if hop_dist > 120.0 else 1
                air_flight(current_pen, global_pts[0], num_pts=flight_pts, arch_factor=0.08)
            else:
                current_pen = global_pts[0]

            last_pt = global_pts[0]

            cv2.circle(ink_mask, (int(round(last_pt[0])), int(round(last_pt[1]))), brush_r, 255, -1)
            act = (ink_mask[pos_y : pos_y + artwork_hd.shape[0], pos_x : pos_x + artwork_hd.shape[1]] > 0) & (line_mask_hd > 0)
            live_canvas[pos_y : pos_y + artwork_hd.shape[0], pos_x : pos_x + artwork_hd.shape[1]][act] = artwork_hd[act]

            for next_pt in global_pts[1:]:
                cv2.line(ink_mask, (int(round(last_pt[0])), int(round(last_pt[1]))),
                                   (int(round(next_pt[0])), int(round(next_pt[1]))), 255, thickness=brush_r * 2, lineType=cv2.LINE_AA)
                cv2.circle(ink_mask, (int(round(next_pt[0])), int(round(next_pt[1]))), radius=brush_r, color=255, thickness=-1, lineType=cv2.LINE_AA)

                accum += math.hypot(next_pt[0] - last_pt[0], next_pt[1] - last_pt[1])

                if accum >= step_dist:
                    act = (ink_mask[pos_y : pos_y + artwork_hd.shape[0], pos_x : pos_x + artwork_hd.shape[1]] > 0) & (line_mask_hd > 0)
                    live_canvas[pos_y : pos_y + artwork_hd.shape[0], pos_x : pos_x + artwork_hd.shape[1]][act] = artwork_hd[act]
                    emit_frame_exact(next_pt[0], next_pt[1], cur_cam_pos[0], cur_cam_pos[1], cur_zoom, cur_tilt)
                    accum = 0.0

                last_pt = next_pt

            current_pen = last_pt

        if accum > 0:
            act = (ink_mask[pos_y : pos_y + artwork_hd.shape[0], pos_x : pos_x + artwork_hd.shape[1]] > 0) & (line_mask_hd > 0)
            live_canvas[pos_y : pos_y + artwork_hd.shape[0], pos_x : pos_x + artwork_hd.shape[1]][act] = artwork_hd[act]
            emit_frame_exact(current_pen[0], current_pen[1], cur_cam_pos[0], cur_cam_pos[1], cur_zoom, cur_tilt)
            accum = 0.0

        act = (ink_mask[pos_y : pos_y + artwork_hd.shape[0], pos_x : pos_x + artwork_hd.shape[1]] > 0) & (line_mask_hd > 0)
        live_canvas[pos_y : pos_y + artwork_hd.shape[0], pos_x : pos_x + artwork_hd.shape[1]][act] = artwork_hd[act]
        live_canvas[pos_y : pos_y + artwork_hd.shape[0], pos_x : pos_x + artwork_hd.shape[1]][line_mask_hd > 0] = artwork_hd[line_mask_hd > 0]

    # HIGH SPEED ZERO-LOSS CONCENTRIC CHARACTER & GRAPHIC INKING
    def draw_graphics_concentric_exact(gfx_ink, gfx_hd, pos_x, pos_y, brush_r=15, step_dist=28.0):
        nonlocal current_pen
        num_cc, lbls_g, stats_g, _ = cv2.connectedComponentsWithStats(gfx_ink)
        if num_cc <= 1:
            return

        comps = sorted(range(1, num_cc), key=lambda i: stats_g[i][4], reverse=True)
        drawn_gfx = np.zeros_like(gfx_ink)

        accum = 0.0
        for c_idx in comps:
            area = stats_g[c_idx][4]
            if area < 25:
                continue
            c_mask = (lbls_g == c_idx).astype(np.uint8) * 255
            ys, xs = np.where(c_mask > 0)
            x1, y1 = max(0, xs.min() - 4), max(0, ys.min() - 4)
            x2, y2 = min(gfx_hd.shape[1], xs.max() + 4), min(gfx_hd.shape[0], ys.max() + 4)

            c_crop = np.full((y2 - y1, x2 - x1, 3), 255, dtype=np.uint8)
            sub_m = c_mask[y1:y2, x1:x2]
            c_crop[sub_m > 0] = gfx_hd[y1:y2, x1:x2][sub_m > 0]

            main_strokes = build_gapless_orbital_path(c_crop, ring_step=8, sample_interval=4.0, brush_radius=brush_r, drawing_direction='OUTSIDE_IN')

            for stroke in main_strokes:
                if len(stroke) < 2:
                    continue
                global_stroke = [(pos_x + x1 + pt[0], pos_y + y1 + pt[1]) for pt in stroke]
                air_flight(current_pen, global_stroke[0], num_pts=1, arch_factor=0.10)

                last_pt = global_stroke[0]

                for next_pt in global_stroke[1:]:
                    cv2.line(ink_mask, (int(round(last_pt[0])), int(round(last_pt[1]))),
                                       (int(round(next_pt[0])), int(round(next_pt[1]))), 255, thickness=brush_r * 2, lineType=cv2.LINE_AA)
                    cv2.circle(ink_mask, (int(round(next_pt[0])), int(round(next_pt[1]))), radius=brush_r, color=255, thickness=-1, lineType=cv2.LINE_AA)

                    accum += math.hypot(next_pt[0] - last_pt[0], next_pt[1] - last_pt[1])

                    if accum >= step_dist:
                        act = (ink_mask[pos_y + y1 : pos_y + y2, pos_x + x1 : pos_x + x2] > 0) & (sub_m > 0)
                        live_canvas[pos_y + y1 : pos_y + y2, pos_x + x1 : pos_x + x2][act] = c_crop[act]
                        emit_frame_exact(next_pt[0], next_pt[1], cur_cam_pos[0], cur_cam_pos[1], cur_zoom, cur_tilt)
                        accum = 0.0

                    last_pt = next_pt

                current_pen = last_pt

            drawn_gfx = cv2.bitwise_or(drawn_gfx, c_mask)
            live_canvas[pos_y + y1 : pos_y + y2, pos_x + x1 : pos_x + x2][sub_m > 0] = c_crop[sub_m > 0]

        if accum > 0:
            emit_frame_exact(current_pen[0], current_pen[1], cur_cam_pos[0], cur_cam_pos[1], cur_zoom, cur_tilt)
            accum = 0.0

    char_s = float(char_speed if char_speed is not None else drawing_speed)
    text_s = float(text_speed if text_speed is not None else drawing_speed)
    text_step = max(2.0, 14.0 * text_s)
    gfx_step = max(4.0, 28.0 * char_s)

    # DRAW ALL PANELS
    for p_idx, p_info in enumerate(panel_layouts):
        p_name = p_info["name"]
        target_c = (p_info["center_x"], p_info["center_y"])
        pos_x, pos_y = p_info["x1"], p_info["y1"]
        artwork_hd = p_info["artwork_hd"]

        if p_idx > 0:
            is_new_row = (p_info["row"] != panel_layouts[p_idx-1]["row"])
            trans_frames = 14 if not is_new_row else 18

            p_prev_center = cur_cam_pos
            dx = target_c[0] - p_prev_center[0]
            dy = target_c[1] - p_prev_center[1]

            target_pen_start = (pos_x + p_info["w"] * 0.75, pos_y + 55.0)
            hand_flight_pts = generate_natural_bezier_flight(current_pen, target_pen_start, num_points=trans_frames, arch_factor=0.30 if is_new_row else 0.18)

            pullback_max = -0.30 if not is_new_row else -0.45

            for tf in range(trans_frames):
                t_norm = (tf + 1) / float(trans_frames)
                t_ease = smootherstep(t_norm)

                cx = p_prev_center[0] + dx * t_ease
                cy = p_prev_center[1] + dy * t_ease

                z = target_panel_zoom + pullback_max * math.sin(t_ease * math.pi)

                direction_sign = 1.0 if dx >= 0 else -1.0
                tilt = direction_sign * (1.0 if not is_new_row else 1.4) * math.sin(t_ease * math.pi)

                pen_pt = hand_flight_pts[tf]
                emit_frame_exact(pen_pt[0], pen_pt[1], cx, cy, z, tilt, force=True)

            cur_cam_pos = target_c
            cur_zoom = target_panel_zoom
            cur_tilt = 0.0
            current_pen = target_pen_start

        pct = 25.0 + (p_idx / float(num_p)) * 65.0
        if progress_cb: progress_cb(pct, f"Rendering panel {p_idx+1}/{num_p}...")
        print(f"  • Rendering {p_name} on Whiteboard...")

        # 1. DRAW TITLE & UNDERLINE
        hd_lines = p_info["hd_lines"]
        if hd_lines:
            draw_text_line_exact(hd_lines[0]["mask_hd"], pos_x, pos_y, artwork_hd, direction=hd_lines[0]["direction"], brush_r=10, step_dist=text_step)
            if len(hd_lines) > 1 and hd_lines[1]["type"] == "UNDERLINE":
                draw_text_line_exact(hd_lines[1]["mask_hd"], pos_x, pos_y, artwork_hd, direction=hd_lines[1]["direction"], brush_r=8, step_dist=text_step * 1.15)

        # 2. DRAW GRAPHICS & CHARACTERS CONCENTRICALLY
        draw_graphics_concentric_exact(p_info["gfx_ink"], p_info["gfx_hd"], pos_x, pos_y, brush_r=15, step_dist=gfx_step)

        # 3. DRAW BODY TEXT LINES
        body_lines = [l for l in hd_lines if l["type"] == "TEXT_LINE"]
        for l in body_lines:
            draw_text_line_exact(l["mask_hd"], pos_x, pos_y, artwork_hd, direction=l["direction"], brush_r=9, step_dist=text_step)
            emit_frame_exact(current_pen[0], current_pen[1], cur_cam_pos[0], cur_cam_pos[1], cur_zoom, cur_tilt, force=True)

        # 4. DRAW ACCENTS & ICONS
        for acc_m in p_info["hd_accents"]:
            draw_text_line_exact(acc_m, pos_x, pos_y, artwork_hd, direction="LTR", brush_r=8, step_dist=text_step * 1.1)

        live_canvas[pos_y : pos_y + target_p_h, pos_x : pos_x + p_w_scaled] = artwork_hd

    # MASTER OUTRO REVEAL
    print("  • Camera Director: Executing Master Outro Pull-out...")
    if progress_cb: progress_cb(92.0, "Showcasing full storyboard...")

    exit_pts = generate_natural_bezier_flight(current_pen, (canvas_w + 350, canvas_h + 350), num_points=10, arch_factor=0.2)
    for pt in exit_pts:
        emit_frame_exact(pt[0], pt[1], cur_cam_pos[0], cur_cam_pos[1], cur_zoom, cur_tilt, force=True)

    outro_frames = 28
    for tf in range(outro_frames):
        t_norm = (tf + 1) / float(outro_frames)
        t_ease = smootherstep(t_norm)

        z = cur_zoom + (full_board_zoom - cur_zoom) * t_ease
        cx = cur_cam_pos[0] + (full_board_center[0] - cur_cam_pos[0]) * t_ease
        cy = cur_cam_pos[1] + (full_board_center[1] - cur_cam_pos[1]) * t_ease
        tilt = math.sin(t_ease * math.pi) * 0.4

        M = get_camera_affine_matrix(cx, cy, z, tilt, out_w, out_h)
        frame = render_camera_viewport_with_matrix(live_canvas, M, out_w, out_h)
        encoder.write_frame(frame)
        total_frames += 1

    M_final = get_camera_affine_matrix(full_board_center[0], full_board_center[1], full_board_zoom, 0.0, out_w, out_h)
    final_full_frame = render_camera_viewport_with_matrix(live_canvas, M_final, out_w, out_h)
    for _ in range(75):
        encoder.write_frame(final_full_frame)
        total_frames += 1

    encoder.close()
    dur_s = total_frames / float(fps)
    print("\n=================================================================")
    print("CINEMATIC ANIMATION COMPLETE!")
    print(f"  • Master Video: {output_video_path}")
    print(f"  • Duration: {dur_s:.2f}s ({total_frames} frames @ {fps}fps)")
    print("=================================================================")
    if progress_cb: progress_cb(100.0, "Render complete!")
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Universal 2026 Cinematic Storyboard Whiteboard Animator")
    parser.add_argument("--image", default=os.path.join(_root, 'test_images', 'arabic_12_panel_storyboard.jpg'), help="Input storyboard image")
    parser.add_argument("--output", default=None, help="Output MP4 path")
    parser.add_argument("--zoom", type=float, default=1.40, help="Center focus zoom level (default: 1.40)")
    parser.add_argument("--fps", type=int, default=30, help="Framerate (default: 30)")
    parser.add_argument("--speed", type=float, default=1.5, help="General drawing speed multiplier (default: 1.5)")
    parser.add_argument("--char-speed", type=float, default=None, help="Character & artwork drawing speed multiplier")
    parser.add_argument("--text-speed", type=float, default=None, help="Text & typography handwriting speed multiplier")
    args = parser.parse_args()

    run_cinematic_storyboard_2026(
        args.image,
        args.output,
        zoom_level=args.zoom,
        fps=args.fps,
        drawing_speed=args.speed,
        char_speed=args.char_speed,
        text_speed=args.text_speed
    )
