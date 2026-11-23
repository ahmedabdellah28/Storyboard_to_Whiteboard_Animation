"""
========================================================================================================================
Deep Pipeline Render Engine — Universal 2026 Cinematic Storyboard Animator
========================================================================================================================
Combines:
1. 2026 Balanced Cinematic Camera Director:
   - Smootherstep quintic easing curves.
   - Rotational banking tilt (±1.4°) on camera moves.
   - Parallax pullback during inter-panel crane transit.
   - Intro Swoop & Grand Master Outro reveal.
2. RTL Arabic Typography Engine:
   - Morphological skeleton stroke extraction.
   - Line-by-line handwriting (Title, Underline, Body Text, Accents).
   - Natural Bézier arc air-flights.
3. Concentric Character & Graphics Inking Engine:
   - High-speed zero-loss concentric orbital paths.
   - Area-prioritized component inking.
4. Screen-Space Subpixel Pen Tip Compositing (100% ink-to-tip accuracy).
5. Super-sampling image enhancement with bilateral smoothing & unsharp mask.
========================================================================================================================
"""
import os
import sys
import math
import cv2
import numpy as np
from typing import Callable, Optional, List, Dict, Any, Union

from ..video.encoder import VideoEncoder
from .hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
from .concentric_engine import (
    DEFAULT_HAND_PATH,
    DEFAULT_HAND_MASK_PATH,
    PEN_TIP_ANCHOR_X,
    PEN_TIP_ANCHOR_Y,
    build_gapless_orbital_path
)
from ..processing.dynamic_decomposition import (
    detect_panels_dynamically,
    suppress_outer_frame_borders
)
from ..processing.dynamic_border_detector import DynamicBorderDetector
from ..processing.m1_panel_extractor import DynamicPanelExtractor
from ..processing.m2_layer_splitter import MethodALayerSplitter
from ..processing.m3_text_line_auditor import TextLineAuditor
from ..processing.whiteboard_processor import WhiteboardProcessor


def smootherstep(t: float) -> float:
    """Quintic smootherstep curve: 6t^5 - 15t^4 + 10t^3."""
    t = max(0.0, min(1.0, float(t)))
    return t * t * t * (t * (6.0 * t - 15.0) + 10.0)


def get_camera_affine_matrix(
    center_x: float,
    center_y: float,
    zoom_scale: float,
    tilt_deg: float = 0.0,
    out_w: int = 1920,
    out_h: int = 1080,
    ref_w: float = 1920.0
) -> np.ndarray:
    zoom_scale = max(0.2, float(zoom_scale))
    # Normalized canvas-space viewport so framing is 100% identical across all render resolutions
    vw = ref_w / zoom_scale
    vh = vw * (out_h / float(max(1, out_w)))

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


def enhance_panel_clarity_and_vibrance(clean_crop: np.ndarray, target_w: int, target_h: int) -> tuple:
    # Color Vibrance Boost
    hsv = cv2.cvtColor(clean_crop, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.25, 0, 255)
    boosted = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # Lanczos Super-Sampling
    hd = cv2.resize(boosted, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

    # Edge-Preserving Bilateral Smoothing
    clean = cv2.bilateralFilter(hd, d=7, sigmaColor=45, sigmaSpace=45)

    # Unsharp Masking
    gaussian = cv2.GaussianBlur(clean, (0, 0), 1.3)
    sharp = cv2.addWeighted(clean, 1.40, gaussian, -0.40, 0)

    # Pure White Background Thresholding
    gray = cv2.cvtColor(sharp, cv2.COLOR_BGR2GRAY)
    sharp[gray > 245] = [255, 255, 255]

    return sharp, clean_crop


def morphological_skeleton(bin_img: np.ndarray) -> np.ndarray:
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


def extract_ordered_skeleton_strokes(ink_roi: np.ndarray, direction: str = "RTL", step_stride: int = 3) -> List[List[tuple]]:
    skel = morphological_skeleton(ink_roi)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(skel)
    if num_labels <= 1:
        ys, xs = np.where(ink_roi > 0)
        if len(xs) == 0:
            return []
        if direction == "RTL":
            return [[(float(x), float(ys[xs == x].mean())) for x in range(xs.max(), xs.min() - 1, -step_stride) if len(ys[xs == x]) > 0]]
        else:
            return [[(float(x), float(ys[xs == x].mean())) for x in range(xs.min(), xs.max() + 1, step_stride) if len(ys[xs == x]) > 0]]

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
            neighbors = [(cx_pt + dx, cy_pt + dy) for dx in [-1, 0, 1] for dy in [-1, 0, 1] if (dx != 0 or dy != 0) and (cx_pt + dx, cy_pt + dy) in pts_set]
            if neighbors:
                next_pt = min(neighbors, key=lambda p: (p[0], p[1])) if direction == "RTL" else max(neighbors, key=lambda p: (p[0], -p[1]))
            else:
                next_pt = min(pts_set, key=lambda p: (p[0] - cx_pt)**2 + (p[1] - cy_pt)**2)
            path.append(next_pt)
            pts_set.remove(next_pt)
            curr = next_pt
        sampled_path = path[::step_stride]
        if len(sampled_path) > 0:
            all_strokes.append(sampled_path)
    return all_strokes


def generate_natural_bezier_flight(p_start: tuple, p_end: tuple, num_points: int = 10, arch_factor: float = 0.20) -> List[tuple]:
    p0 = np.array(p_start, dtype=np.float32)
    p3 = np.array(p_end, dtype=np.float32)
    dist = np.linalg.norm(p3 - p0)

    lift = -min(180.0, max(30.0, dist * arch_factor))
    p1 = p0 + (p3 - p0) * 0.25 + np.array([0, lift * 0.8], dtype=np.float32)
    p2 = p0 + (p3 - p0) * 0.75 + np.array([0, lift * 0.9], dtype=np.float32)

    pts = []
    for t in np.linspace(0, 1, num_points):
        pt = (1 - t)**3 * p0 + 3 * (1 - t)**2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3
        pts.append((float(pt[0]), float(pt[1])))
    return pts


def get_object_hd_mask(obj: Any, target_w: int, target_h: int, orig_w: int, orig_h: int) -> np.ndarray:
    """Extracts and precisely rescales a SceneObject's mask into full HD panel coordinates."""
    bbox = getattr(obj, "bbox", (0, 0, orig_w, orig_h))
    bx, by, bw, bh = (0, 0, orig_w, orig_h)
    if bbox and len(bbox) == 4:
        bx, by, bw, bh = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

    full_w = max(orig_w, bx + bw, 1)
    full_h = max(orig_h, by + bh, 1)
    full_m = np.zeros((full_h, full_w), dtype=np.uint8)

    m = getattr(obj, "mask", None)
    if m is not None and isinstance(m, np.ndarray) and m.size > 0:
        if m.shape[:2] == (bh, bw):
            full_m[by : by + bh, bx : bx + bw] = (m > 0).astype(np.uint8) * 255
        elif m.shape[:2] == (full_h, full_w) or m.shape[:2] == (orig_h, orig_w):
            mh, mw = m.shape[:2]
            full_m[:mh, :mw] = (m > 0).astype(np.uint8) * 255
        else:
            resized_m = cv2.resize((m > 0).astype(np.uint8) * 255, (max(1, bw), max(1, bh)), interpolation=cv2.INTER_NEAREST)
            clip_h = min(full_h - by, bh)
            clip_w = min(full_w - bx, bw)
            if clip_h > 0 and clip_w > 0:
                full_m[by : by + clip_h, bx : bx + clip_w] = resized_m[:clip_h, :clip_w]
    else:
        crop = getattr(obj, "crop", None)
        if crop is not None and isinstance(crop, np.ndarray) and crop.size > 0:
            diff = 255.0 - crop.astype(np.float32)
            dist = np.max(diff, axis=2)
            crop_mask = (dist > 20.0).astype(np.uint8) * 255
            clip_h = min(full_h - by, crop_mask.shape[0])
            clip_w = min(full_w - bx, crop_mask.shape[1])
            if clip_h > 0 and clip_w > 0:
                full_m[by : by + clip_h, bx : bx + clip_w] = crop_mask[:clip_h, :clip_w]

    bounded_m = full_m[:orig_h, :orig_w] if (orig_h <= full_h and orig_w <= full_w) else full_m
    return cv2.resize(bounded_m, (target_w, target_h), interpolation=cv2.INTER_NEAREST)


def render_deep_storyboard_pipeline(
    image_input: Union[str, np.ndarray],
    output_path: str,
    fps: int = 30,
    drawing_speed: float = 1.5,
    camera_zoom_scale: float = 2.05,
    show_hand: bool = True,
    hand_scale: float = 0.95,
    end_hold_seconds: float = 1.5,
    custom_objects: Optional[List[Any]] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    min_parts: int = 4,
    max_parts: int = 6,
    canvas_width: int = 1920,
    canvas_height: int = 1080,
    custom_panels: Optional[List[Any]] = None,
    character_drawing_speed: Optional[float] = None,
    text_drawing_speed: Optional[float] = None
) -> str:
    """
    Executes the 2026 Universal Cinematic Storyboard Whiteboard Animator.
    Renders with Cinematic Camera Director, RTL Skeleton Typography, and Concentric Inking.
    """
    if progress_callback:
        progress_callback(5.0, "Analyzing composition & extracting clean storyboard panels...")

    if isinstance(image_input, str):
        img = cv2.imread(image_input)
    else:
        img = image_input.copy()

    if img is None:
        raise ValueError("Invalid image input for deep storyboard pipeline.")

    out_w = max(320, int(canvas_width))
    out_h = max(240, int(canvas_height))
    h, w = img.shape[:2]

    # 1. Dynamic panel extraction (from project panels if provided, else via WhiteboardProcessor)
    if custom_panels and len(custom_panels) > 0:
        raw_panels = []
        for idx, p in enumerate(custom_panels):
            if hasattr(p, "bbox"):
                bbox = p.bbox
                pid = getattr(p, "id", idx + 1)
            elif isinstance(p, dict):
                bbox = p.get("bbox", (0, 0, w, h))
                pid = p.get("id", p.get("panel_id", idx + 1))
            else:
                continue
            raw_panels.append({"id": pid, "bbox": bbox})
    else:
        raw_panels = WhiteboardProcessor.discover_panels(img)

    if not raw_panels:
        raw_panels = [{"id": 1, "bbox": (0, 0, w, h)}]

    # Compute grid shape (rows x cols) dynamically from Y and X centers
    y_centers = sorted(set(int(round(p["bbox"][1] + p["bbox"][3] / 2.0)) for p in raw_panels))
    x_centers = sorted(set(int(round(p["bbox"][0] + p["bbox"][2] / 2.0)) for p in raw_panels))

    def cluster_1d(centers, tol):
        res = [centers[0]]
        for c_val in centers[1:]:
            if c_val - res[-1] > tol:
                res.append(c_val)
        return res

    row_clusters = cluster_1d(y_centers, max(12, int(h * 0.08)))
    col_clusters = cluster_1d(x_centers, max(12, int(w * 0.08)))
    grid_rows = len(row_clusters)
    grid_cols = len(col_clusters)

    for p in raw_panels:
        cy = p["bbox"][1] + p["bbox"][3] / 2.0
        cx = p["bbox"][0] + p["bbox"][2] / 2.0
        p["row"] = min(range(grid_rows), key=lambda i: abs(row_clusters[i] - cy))
        p["col"] = min(range(grid_cols), key=lambda i: abs(col_clusters[i] - cx))

    raw_panels.sort(key=lambda p: (p["row"], p["col"]))
    for idx, p in enumerate(raw_panels):
        p["id"] = idx + 1

    panels_data = []
    for p in raw_panels:
        px, py, pw, ph = p["bbox"]
        px = max(0, min(w - 1, int(px)))
        py = max(0, min(h - 1, int(py)))
        pw = max(2, min(w - px, int(pw)))
        ph = max(2, min(h - py, int(ph)))

        raw_crop = img[py:py+ph, px:px+pw].copy()
        border_res = DynamicBorderDetector.detect_and_trim_panel_border(raw_crop)
        clean_crop = border_res["clean_crop"]
        panels_data.append({
            "panel_id": p["id"],
            "row": p["row"],
            "col": p["col"],
            "crop": clean_crop,
            "bbox": (px, py, pw, ph)
        })

    # Extract all panels from full storyboard composition
    all_panels_data = list(panels_data)
    num_p = len(all_panels_data)
    if progress_callback:
        progress_callback(12.0, f"Discovered {num_p} panel(s). Laying out 4K Master Whiteboard Canvas...")

    # 2. 4K UHD Master Canvas Layout (3840x2160)
    canvas_w, canvas_h = 3840, 2160

    is_vertical = (out_h > out_w * 1.15)
    is_square = (0.85 <= out_w / float(out_h) <= 1.15)

    if is_vertical:
        layout_cols = 1
        layout_rows = num_p
        target_p_h = max(300, int((canvas_h * 0.90) / float(num_p)))
        gap_x = 0
        gap_y = max(30, int(canvas_h * 0.02))
    elif is_square:
        layout_cols = 2 if num_p <= 4 else 3
        layout_rows = int(np.ceil(num_p / float(layout_cols)))
        target_p_h = max(350, int((canvas_h * 0.85) / float(layout_rows)))
        gap_x = 60
        gap_y = 50
    else:
        # Standard Landscape - respect the detected dynamic grid
        layout_cols = grid_cols
        layout_rows = grid_rows
        gap_x = 70
        gap_y = 50
        target_p_h = min(580, max(280, int((canvas_h * 0.88 - (layout_rows - 1) * gap_y) / float(max(1, layout_rows)))))

    first_crop = all_panels_data[0]["crop"]
    aspect = first_crop.shape[1] / float(max(1, first_crop.shape[0]))
    p_w_scaled = int(round(target_p_h * aspect))

    total_grid_w = layout_cols * p_w_scaled + (layout_cols - 1) * gap_x
    total_grid_h = layout_rows * target_p_h + (layout_rows - 1) * gap_y
    start_x = max(40, (canvas_w - total_grid_w) // 2)
    start_y = max(40, (canvas_h - total_grid_h) // 2)

    live_canvas = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)
    ink_mask = np.zeros((canvas_h, canvas_w), dtype=np.uint8)

    # Balanced cinematic zoom: panel occupies ~58% of viewport height leaving generous breathing room
    optimal_cinematic_zoom = round(0.58 * 1080.0 / float(target_p_h), 2)
    user_zoom = float(camera_zoom_scale) if camera_zoom_scale else optimal_cinematic_zoom
    target_panel_zoom = min(user_zoom, optimal_cinematic_zoom) if user_zoom > optimal_cinematic_zoom + 0.3 else user_zoom

    # 3. Process Panel Layers with Super-Resolution & Typography Decomposition
    if progress_callback:
        progress_callback(20.0, "Auditing typography, lines, and character graphics...")

    panel_layouts = []
    for idx, p_info in enumerate(panels_data):
        p_id = p_info["panel_id"]
        row_i = p_info["row"]
        col_i = p_info["col"]
        crop = p_info["crop"]

        px = start_x + col_i * (p_w_scaled + gap_x)
        py = start_y + row_i * (target_p_h + gap_y)

        artwork_hd, clean_crop = enhance_panel_clarity_and_vibrance(crop, p_w_scaled, target_p_h)

        # Method A Layer Splitting (Graphics vs Text)
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
            "clean_w": clean_crop.shape[1],
            "clean_h": clean_crop.shape[0],
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

    # Filter and order panels to animate strictly based on user's custom_objects list order
    active_custom_objs = None
    if custom_objects and len(custom_objects) > 0:
        visible_objs = [o for o in custom_objects if getattr(o, "visibility", True)]
        # Always retain all visible objects - NEVER drop unassigned objects!
        active_custom_objs = visible_objs if visible_objs else list(custom_objects)

        ordered_pids = []
        for o in active_custom_objs:
            pid = getattr(o, "panel_id", 1)
            if pid not in ordered_pids:
                ordered_pids.append(pid)

        panel_by_id = {p["panel_id"]: p for p in panel_layouts}
        panels_to_animate = [panel_by_id[pid] for pid in ordered_pids if pid in panel_by_id]
        if not panels_to_animate:
            panels_to_animate = panel_layouts
    else:
        panels_to_animate = panel_layouts

    # 4. Load Hand Sprite for Native Screen Space
    hand_bgra_master = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
    hand_screen_h = int(out_h * 0.44 * max(0.4, min(2.5, hand_scale)))
    scale_h_scr = hand_screen_h / float(hand_bgra_master.shape[0])
    hand_screen_w = max(1, int(hand_bgra_master.shape[1] * scale_h_scr))
    hand_screen = cv2.resize(hand_bgra_master, (hand_screen_w, hand_screen_h), interpolation=cv2.INTER_AREA)
    tip_x_screen = int(round(PEN_TIP_ANCHOR_X * scale_h_scr))
    tip_y_screen = int(round(PEN_TIP_ANCHOR_Y * scale_h_scr))

    # 5. Initialize Video Encoder
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    encoder = VideoEncoder(output_path, out_w, out_h, fps, crf=16)

    total_frames = 0
    full_board_center = (canvas_w / 2.0, canvas_h / 2.0)
    full_board_zoom = 1920.0 / float(canvas_w) # Exactly 0.50x overview on 4K master canvas

    cur_cam_pos = full_board_center
    cur_zoom = full_board_zoom
    cur_tilt = 0.0

    # INTRO SWOOP: Full Board Overview -> Panel 1 of target animation set
    p1 = panels_to_animate[0]
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

    def emit_frame_exact(pen_canvas_x: float, pen_canvas_y: float, cam_x: float, cam_y: float, zoom_z: float, tilt_deg: float, force: bool = False):
        nonlocal total_frames, drawing_call_count
        drawing_call_count += 1

        M = get_camera_affine_matrix(cam_x, cam_y, zoom_z, tilt_deg, out_w, out_h)
        viewport_view = render_camera_viewport_with_matrix(live_canvas, M, out_w, out_h)

        if show_hand:
            scr_x, scr_y = canvas_to_screen_pt(M, (pen_canvas_x, pen_canvas_y))
            final_frame = composite_hand_on_canvas_fast(
                viewport_view, hand_screen,
                tip_x_screen, tip_y_screen,
                int(round(scr_x)), int(round(scr_y))
            )
        else:
            final_frame = viewport_view

        encoder.write_frame(final_frame)
        total_frames += 1

    def air_flight(p_from: tuple, p_to: tuple, num_pts: int = 2, arch_factor: float = 0.15):
        nonlocal current_pen
        pts = generate_natural_bezier_flight(p_from, p_to, num_points=num_pts, arch_factor=arch_factor)
        for pt in pts:
            emit_frame_exact(pt[0], pt[1], cur_cam_pos[0], cur_cam_pos[1], cur_zoom, cur_tilt, force=True)
        current_pen = p_to

    # Dedicated and decoupled Character and Text drawing speed factors
    char_speed = float(character_drawing_speed if character_drawing_speed is not None else drawing_speed)
    text_speed = float(text_drawing_speed if text_drawing_speed is not None else drawing_speed)

    # Base steps calibrated for visible, natural whiteboard inking:
    # Text: 14px/frame at 1.0x (~1.0s per line), faster or slower linearly with text_speed
    # Graphics: 28px/frame at 1.0x (~4.0s per character), faster or slower linearly with char_speed
    text_step_dist = max(2.0, 14.0 * text_speed)
    gfx_step_dist = max(4.0, 28.0 * char_speed)
    print(f"  • [Calibrated Speeds] Text Speed: {text_speed:.2f}x (step={text_step_dist:.1f}px) | Character Speed: {char_speed:.2f}x (step={gfx_step_dist:.1f}px)", flush=True)

    def draw_text_line_exact(line_mask_hd: np.ndarray, pos_x: int, pos_y: int, artwork_hd: np.ndarray, direction: str = "RTL", brush_r: int = 10, step_dist: float = 24.0):
        nonlocal current_pen
        l_strokes = extract_ordered_skeleton_strokes(line_mask_hd, direction=direction, step_stride=3)

        accum = 0.0
        for s_idx, stroke in enumerate(l_strokes):
            global_pts = [(pos_x + pt[0], pos_y + pt[1]) for pt in stroke]
            if len(global_pts) < 1:
                continue

            hop_dist = math.hypot(global_pts[0][0] - current_pen[0], global_pts[0][1] - current_pen[1])
            if s_idx == 0:
                flight_pts = max(1, int(round(3.0 / max(0.5, text_speed)))) if hop_dist > 80.0 else 1
                air_flight(current_pen, global_pts[0], num_pts=flight_pts, arch_factor=0.10)
            elif hop_dist > 45.0:
                flight_pts = max(1, int(round(2.0 / max(0.5, text_speed)))) if hop_dist > 120.0 else 1
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

        # Emit at least one frame if ink was drawn but not yet emitted
        if accum > 0:
            act = (ink_mask[pos_y : pos_y + artwork_hd.shape[0], pos_x : pos_x + artwork_hd.shape[1]] > 0) & (line_mask_hd > 0)
            live_canvas[pos_y : pos_y + artwork_hd.shape[0], pos_x : pos_x + artwork_hd.shape[1]][act] = artwork_hd[act]
            emit_frame_exact(current_pen[0], current_pen[1], cur_cam_pos[0], cur_cam_pos[1], cur_zoom, cur_tilt)
            accum = 0.0

        act = (ink_mask[pos_y : pos_y + artwork_hd.shape[0], pos_x : pos_x + artwork_hd.shape[1]] > 0) & (line_mask_hd > 0)
        live_canvas[pos_y : pos_y + artwork_hd.shape[0], pos_x : pos_x + artwork_hd.shape[1]][act] = artwork_hd[act]
        live_canvas[pos_y : pos_y + artwork_hd.shape[0], pos_x : pos_x + artwork_hd.shape[1]][line_mask_hd > 0] = artwork_hd[line_mask_hd > 0]

    def draw_graphics_concentric_exact(gfx_ink: np.ndarray, gfx_hd: np.ndarray, pos_x: int, pos_y: int, brush_r: int = 18, step_dist: float = 40.0):
        nonlocal current_pen
        num_cc, lbls_g, stats_g, _ = cv2.connectedComponentsWithStats(gfx_ink)
        if num_cc <= 1:
            return

        comps = sorted(range(1, num_cc), key=lambda i: stats_g[i][4], reverse=True)
        drawn_gfx = np.zeros_like(gfx_ink)

        accum = 0.0
        for c_idx in comps:
            area = stats_g[c_idx][4]
            if area < 15:
                continue
            c_mask = (lbls_g == c_idx).astype(np.uint8) * 255
            ys, xs = np.where(c_mask > 0)
            x1, y1 = max(0, xs.min() - 4), max(0, ys.min() - 4)
            x2, y2 = min(gfx_hd.shape[1], xs.max() + 4), min(gfx_hd.shape[0], ys.max() + 4)

            c_crop = np.full((y2 - y1, x2 - x1, 3), 255, dtype=np.uint8)
            sub_m = c_mask[y1:y2, x1:x2]
            c_crop[sub_m > 0] = gfx_hd[y1:y2, x1:x2][sub_m > 0]

            main_strokes = build_gapless_orbital_path(c_crop, ring_step=6, sample_interval=3.0, brush_radius=brush_r, drawing_direction='OUTSIDE_IN')

            for s_i, stroke in enumerate(main_strokes):
                if len(stroke) < 2:
                    continue
                global_stroke = [(pos_x + x1 + pt[0], pos_y + y1 + pt[1]) for pt in stroke]
                hop_d = math.hypot(global_stroke[0][0] - current_pen[0], global_stroke[0][1] - current_pen[1])
                if s_i == 0 or hop_d > 60.0:
                    air_flight(current_pen, global_stroke[0], num_pts=1, arch_factor=0.10)
                else:
                    current_pen = global_stroke[0]

                last_pt = global_stroke[0]

                # Paint initial brush circle immediately at start point
                cv2.circle(ink_mask, (int(round(last_pt[0])), int(round(last_pt[1]))), radius=brush_r, color=255, thickness=-1, lineType=cv2.LINE_AA)
                act = (ink_mask[pos_y + y1 : pos_y + y2, pos_x + x1 : pos_x + x2] > 0) & (sub_m > 0)
                live_canvas[pos_y + y1 : pos_y + y2, pos_x + x1 : pos_x + x2][act] = c_crop[act]

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

    # 6. Draw Target Panels with Balanced Crane Transitions
    total_panels_count = len(panels_to_animate)

    for p_idx, p_info in enumerate(panels_to_animate):
        p_name = p_info["name"]
        target_c = (p_info["center_x"], p_info["center_y"])
        pos_x, pos_y = p_info["x1"], p_info["y1"]
        artwork_hd = p_info["artwork_hd"]

        if progress_callback:
            pct = 25.0 + 65.0 * (p_idx / float(max(1, total_panels_count)))
            progress_callback(pct, f"Cinematic Inking {p_name} ({p_idx+1}/{total_panels_count})...")

        # Inter-panel transition
        if p_idx > 0:
            is_new_row = (p_info["row"] != panels_to_animate[p_idx - 1]["row"])
            trans_frames = 14 if not is_new_row else 18

            p_prev_center = cur_cam_pos
            dx = target_c[0] - p_prev_center[0]
            dy = target_c[1] - p_prev_center[1]

            target_pen_start = (pos_x + p_info["w"] * 0.75, pos_y + 55.0)
            hand_flight_pts = generate_natural_bezier_flight(current_pen, target_pen_start, num_points=trans_frames, arch_factor=0.30 if is_new_row else 0.18)

            pullback_max = -0.35 if not is_new_row else -0.50

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

        hd_lines = p_info["hd_lines"]
        hd_accents = p_info["hd_accents"]
        p_id = p_info["panel_id"]

        # Check if user passed custom objects for this panel
        p_custom_objs = [o for o in active_custom_objs if getattr(o, "panel_id", 1) == p_id] if active_custom_objs else []

        if p_custom_objs:
            # Sort strictly by priority_order (assigned first in numerical order, then unassigned)
            p_custom_objs = sorted(
                p_custom_objs,
                key=lambda o: (0 if getattr(o, "priority_order", None) not in (None, 0) else 1, getattr(o, "priority_order", 99999))
            )

            orig_cw = p_info.get("clean_w", p_w_scaled)
            orig_ch = p_info.get("clean_h", target_p_h)
            sc_x = p_w_scaled / float(max(1, orig_cw))
            sc_y = target_p_h / float(max(1, orig_ch))

            title_line = next((l for l in hd_lines if l["type"] == "TITLE"), (hd_lines[0] if hd_lines else None))
            und_line = next((l for l in hd_lines if l["type"] == "UNDERLINE"), None)
            non_title_lines = [l for l in hd_lines if l is not title_line and l is not und_line]
            if not non_title_lines and hd_lines:
                non_title_lines = hd_lines

            # Render each object directly via its exact HD mask in strict user order
            for obj in p_custom_objs:
                elem_type = str(getattr(obj, "element_type", "")).upper()
                obj_name = str(getattr(obj, "name", "")).lower()
                direction = getattr(obj, "direction", "RTL")
                obj_hd_mask = get_object_hd_mask(obj, p_w_scaled, target_p_h, orig_cw, orig_ch)
                obj_spd_mult = float(getattr(obj, "speed_multiplier", 1.0) or 1.0)
                cur_gfx_step = max(4.0, gfx_step_dist * obj_spd_mult)
                cur_txt_step = max(2.0, text_step_dist * obj_spd_mult)

                # 1. CHARACTER / ART / GRAPHICS
                if elem_type in ("CHARACTER", "GRAPHICS", "ART", "IMAGE") or ("character" in obj_name) or ("art" in obj_name):
                    ys_c, xs_c = np.where(obj_hd_mask > 0)
                    if len(xs_c) > 0:
                        x1 = max(0, int(xs_c.min()) - 4)
                        y1 = max(0, int(ys_c.min()) - 4)
                        x2 = min(artwork_hd.shape[1], int(xs_c.max()) + 4)
                        y2 = min(artwork_hd.shape[0], int(ys_c.max()) + 4)

                        c_crop = np.full((y2 - y1, x2 - x1, 3), 255, dtype=np.uint8)
                        sub_m = obj_hd_mask[y1:y2, x1:x2]
                        c_crop[sub_m > 0] = artwork_hd[y1:y2, x1:x2][sub_m > 0]

                        main_strokes = build_gapless_orbital_path(c_crop, ring_step=6, sample_interval=3.0, brush_radius=18, drawing_direction='OUTSIDE_IN')

                        accum = 0.0
                        for s_i, stroke in enumerate(main_strokes):
                            if len(stroke) < 2:
                                continue
                            global_stroke = [(pos_x + x1 + pt[0], pos_y + y1 + pt[1]) for pt in stroke]
                            hop_d = math.hypot(global_stroke[0][0] - current_pen[0], global_stroke[0][1] - current_pen[1])
                            if s_i == 0 or hop_d > 60.0:
                                air_flight(current_pen, global_stroke[0], num_pts=1, arch_factor=0.10)
                            else:
                                current_pen = global_stroke[0]

                            last_pt = global_stroke[0]

                            cv2.circle(ink_mask, (int(round(last_pt[0])), int(round(last_pt[1]))), radius=18, color=255, thickness=-1, lineType=cv2.LINE_AA)
                            act = (ink_mask[pos_y + y1 : pos_y + y2, pos_x + x1 : pos_x + x2] > 0) & (sub_m > 0)
                            live_canvas[pos_y + y1 : pos_y + y2, pos_x + x1 : pos_x + x2][act] = c_crop[act]

                            for next_pt in global_stroke[1:]:
                                cv2.line(ink_mask, (int(round(last_pt[0])), int(round(last_pt[1]))),
                                                   (int(round(next_pt[0])), int(round(next_pt[1]))), 255, thickness=36, lineType=cv2.LINE_AA)
                                cv2.circle(ink_mask, (int(round(next_pt[0])), int(round(next_pt[1]))), radius=18, color=255, thickness=-1, lineType=cv2.LINE_AA)

                                accum += math.hypot(next_pt[0] - last_pt[0], next_pt[1] - last_pt[1])

                                if accum >= cur_gfx_step:
                                    act = (ink_mask[pos_y + y1 : pos_y + y2, pos_x + x1 : pos_x + x2] > 0) & (sub_m > 0)
                                    live_canvas[pos_y + y1 : pos_y + y2, pos_x + x1 : pos_x + x2][act] = c_crop[act]
                                    emit_frame_exact(next_pt[0], next_pt[1], cur_cam_pos[0], cur_cam_pos[1], cur_zoom, cur_tilt)
                                    accum = 0.0

                                last_pt = next_pt

                            current_pen = last_pt

                        if accum > 0:
                            act = (ink_mask[pos_y + y1 : pos_y + y2, pos_x + x1 : pos_x + x2] > 0) & (sub_m > 0)
                            live_canvas[pos_y + y1 : pos_y + y2, pos_x + x1 : pos_x + x2][act] = c_crop[act]
                            emit_frame_exact(current_pen[0], current_pen[1], cur_cam_pos[0], cur_cam_pos[1], cur_zoom, cur_tilt)
                            accum = 0.0

                        live_canvas[pos_y + y1 : pos_y + y2, pos_x + x1 : pos_x + x2][sub_m > 0] = c_crop[sub_m > 0]
                        live_canvas[pos_y : pos_y + target_p_h, pos_x : pos_x + p_w_scaled][obj_hd_mask > 0] = artwork_hd[obj_hd_mask > 0]
                    else:
                        draw_graphics_concentric_exact(p_info["gfx_ink"], p_info["gfx_hd"], pos_x, pos_y, brush_r=18, step_dist=cur_gfx_step)

                # 2. UNDERLINE
                elif elem_type == "UNDERLINE" or ("underline" in obj_name):
                    if cv2.countNonZero(obj_hd_mask) > 10:
                        draw_text_line_exact(obj_hd_mask, pos_x, pos_y, artwork_hd, direction="LTR", brush_r=8, step_dist=cur_txt_step * 1.15)
                        live_canvas[pos_y : pos_y + target_p_h, pos_x : pos_x + p_w_scaled][obj_hd_mask > 0] = artwork_hd[obj_hd_mask > 0]
                    elif und_line is not None:
                        draw_text_line_exact(und_line["mask_hd"], pos_x, pos_y, artwork_hd, direction="LTR", brush_r=8, step_dist=cur_txt_step * 1.15)
                    elif hd_lines:
                        u_cands = [l for l in hd_lines if l["type"] == "UNDERLINE"]
                        if u_cands:
                            draw_text_line_exact(u_cands[0]["mask_hd"], pos_x, pos_y, artwork_hd, direction="LTR", brush_r=8, step_dist=cur_txt_step * 1.15)

                # 3. TITLE
                elif ("title" in obj_name) or (elem_type in ("TITLE", "TEXT") and "title" in obj_name):
                    if cv2.countNonZero(obj_hd_mask) > 10:
                        draw_text_line_exact(obj_hd_mask, pos_x, pos_y, artwork_hd, direction=direction, brush_r=10, step_dist=cur_txt_step)
                        live_canvas[pos_y : pos_y + target_p_h, pos_x : pos_x + p_w_scaled][obj_hd_mask > 0] = artwork_hd[obj_hd_mask > 0]
                    elif title_line is not None:
                        draw_text_line_exact(title_line["mask_hd"], pos_x, pos_y, artwork_hd, direction=title_line.get("direction", direction), brush_r=10, step_dist=cur_txt_step)
                    elif hd_lines:
                        draw_text_line_exact(hd_lines[0]["mask_hd"], pos_x, pos_y, artwork_hd, direction=hd_lines[0].get("direction", direction), brush_r=10, step_dist=cur_txt_step)

                # 4. ACCENTS & ICONS
                elif ("accent" in obj_name) or (elem_type in ("ACCENT", "ICON")):
                    if cv2.countNonZero(obj_hd_mask) > 5:
                        draw_text_line_exact(obj_hd_mask, pos_x, pos_y, artwork_hd, direction="LTR", brush_r=8, step_dist=cur_txt_step * 1.1)
                        live_canvas[pos_y : pos_y + target_p_h, pos_x : pos_x + p_w_scaled][obj_hd_mask > 0] = artwork_hd[obj_hd_mask > 0]
                    elif hd_accents:
                        draw_text_line_exact(hd_accents[0], pos_x, pos_y, artwork_hd, direction="LTR", brush_r=8, step_dist=cur_txt_step * 1.1)

                # 5. BODY TEXT LINES (Direct Mask Drawing)
                else:
                    if cv2.countNonZero(obj_hd_mask) > 10:
                        draw_text_line_exact(obj_hd_mask, pos_x, pos_y, artwork_hd, direction=direction, brush_r=9, step_dist=cur_txt_step)
                        live_canvas[pos_y : pos_y + target_p_h, pos_x : pos_x + p_w_scaled][obj_hd_mask > 0] = artwork_hd[obj_hd_mask > 0]
                    else:
                        matched_line = None
                        if hasattr(obj, "bbox") and obj.bbox and len(obj.bbox) == 4 and non_title_lines:
                            bx, by, bw, bh = obj.bbox
                            ocx = (bx + bw / 2.0) * sc_x
                            ocy = (by + bh / 2.0) * sc_y

                            best_d = float('inf')
                            for cand_line in non_title_lines:
                                ys_l, xs_l = np.where(cand_line["mask_hd"] > 0)
                                if len(xs_l) > 0:
                                    lcx, lcy = float(xs_l.mean()), float(ys_l.mean())
                                    d = math.hypot(ocx - lcx, ocy - lcy)
                                    if d < best_d:
                                        best_d = d
                                        matched_line = cand_line

                        if matched_line is None and non_title_lines:
                            matched_line = non_title_lines[0]
                        elif matched_line is None and hd_lines:
                            matched_line = hd_lines[-1]

                        if matched_line is not None:
                            draw_text_line_exact(matched_line["mask_hd"], pos_x, pos_y, artwork_hd, direction=matched_line.get("direction", direction), brush_r=9, step_dist=cur_txt_step)

        else:
            # Default All-Elements Drawing Sequence
            # 1. DRAW TITLE & UNDERLINE (High-Speed Writing)
            if hd_lines:
                draw_text_line_exact(hd_lines[0]["mask_hd"], pos_x, pos_y, artwork_hd, direction=hd_lines[0]["direction"], brush_r=10, step_dist=text_step_dist)
                if len(hd_lines) > 1 and hd_lines[1]["type"] == "UNDERLINE":
                    draw_text_line_exact(hd_lines[1]["mask_hd"], pos_x, pos_y, artwork_hd, direction=hd_lines[1]["direction"], brush_r=8, step_dist=text_step_dist * 1.15)

            # 2. DRAW GRAPHICS & CHARACTERS CONCENTRICALLY (High-Speed Zero-Loss)
            draw_graphics_concentric_exact(p_info["gfx_ink"], p_info["gfx_hd"], pos_x, pos_y, brush_r=18, step_dist=gfx_step_dist)

            # 3. DRAW BODY TEXT LINES (High-Speed RTL Writing)
            body_lines = [l for l in hd_lines if l["type"] == "TEXT_LINE"]
            for l in body_lines:
                draw_text_line_exact(l["mask_hd"], pos_x, pos_y, artwork_hd, direction=l["direction"], brush_r=9, step_dist=text_step_dist)

            # 4. DRAW ACCENTS & ICONS
            for acc_m in p_info["hd_accents"]:
                draw_text_line_exact(acc_m, pos_x, pos_y, artwork_hd, direction="LTR", brush_r=8, step_dist=text_step_dist * 1.1)

        # Always guarantee 100% full reveal for all panel artwork and details
        live_canvas[pos_y : pos_y + target_p_h, pos_x : pos_x + p_w_scaled] = artwork_hd

    # 7. MASTER OUTRO REVEAL
    if progress_callback:
        progress_callback(92.0, "Executing Grand Master Outro Reveal...")

    # Hand exits off screen
    hand_exit_target = (canvas_w + 500.0, canvas_h + 500.0)
    exit_pts = generate_natural_bezier_flight(current_pen, hand_exit_target, num_points=12, arch_factor=0.25)
    for pt in exit_pts:
        emit_frame_exact(pt[0], pt[1], cur_cam_pos[0], cur_cam_pos[1], cur_zoom, cur_tilt, force=True)

    # Grand Master Outro Pull-out: Panel N -> Full Master Board
    outro_frames = 28
    p_last_center = cur_cam_pos
    for i in range(outro_frames):
        t_norm = (i + 1) / float(outro_frames)
        t_ease = smootherstep(t_norm)

        cam_x = p_last_center[0] + (full_board_center[0] - p_last_center[0]) * t_ease
        cam_y = p_last_center[1] + (full_board_center[1] - p_last_center[1]) * t_ease
        cam_zoom = target_panel_zoom + (full_board_zoom - target_panel_zoom) * t_ease
        tilt = -math.sin(t_ease * math.pi) * 0.8

        M = get_camera_affine_matrix(cam_x, cam_y, cam_zoom, tilt, out_w, out_h)
        frame = render_camera_viewport_with_matrix(live_canvas, M, out_w, out_h)
        encoder.write_frame(frame)
        total_frames += 1

    # Final Hold Showcase
    hold_frames = max(15, int(end_hold_seconds * fps))
    M_final = get_camera_affine_matrix(full_board_center[0], full_board_center[1], full_board_zoom, 0.0, out_w, out_h)
    frame_final = render_camera_viewport_with_matrix(live_canvas, M_final, out_w, out_h)
    for _ in range(hold_frames):
        encoder.write_frame(frame_final)
        total_frames += 1

    encoder.close()
    if progress_callback:
        progress_callback(100.0, "Cinematic Master video rendered successfully!")

    return output_path
