"""
Concentric Gapless Orbital Whiteboard Rendering Engine (360° Synchronous Drawing).
100% Mathematical & Algorithm Preservation with Clean Architectural Boundaries.
"""
import os
import sys
import math
from typing import List, Dict, Any, Optional, Tuple, Callable
import cv2
import numpy as np

from ..core.image_io import read_image_unicode
from .hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
from .viewport_transform import render_camera_viewport
from ..video.encoder import VideoEncoder

# Default Hand Asset Paths & Anchors
if getattr(sys, 'frozen', False):
    _base_path = sys._MEIPASS
else:
    _base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_images_path = os.path.join(_base_path, 'data', 'images')
DEFAULT_HAND_PATH = os.path.join(_images_path, 'drawing-hand.png')
DEFAULT_HAND_MASK_PATH = os.path.join(_images_path, 'hand-mask.png')
PEN_TIP_ANCHOR_X = 62
PEN_TIP_ANCHOR_Y = 40


def merge_nearby_punctuation(boxes, h_thresh_factor=0.35, dist_thresh=35):
    """Merges standalone small punctuation/dot boxes into adjacent bounding boxes."""
    if not boxes:
        return []
    
    avg_h = np.median([b[3] for b in boxes])
    min_main_h = avg_h * h_thresh_factor
    
    main_boxes = []
    punct_boxes = []
    
    for b in boxes:
        x, y, w, h = b[:4]
        if h < min_main_h and w < min_main_h * 1.5:
            punct_boxes.append(b)
        else:
            main_boxes.append(b)
            
    if not main_boxes:
        return boxes
        
    merged_mains = [list(b) for b in main_boxes]
    
    for pb in punct_boxes:
        px, py, pw, ph = pb[:4]
        pcx, pcy = px + pw / 2.0, py + ph / 2.0
        
        best_dist = float('inf')
        best_idx = -1
        
        for i, mb in enumerate(merged_mains):
            mx, my, mw, mh = mb[:4]
            nearest_x = max(mx, min(pcx, mx + mw))
            nearest_y = max(my, min(pcy, my + mh))
            dist = math.hypot(pcx - nearest_x, pcy - nearest_y)
            
            if dist < best_dist:
                best_dist = dist
                best_idx = i
                
        if best_idx != -1 and best_dist <= dist_thresh:
            mx, my, mw, mh = merged_mains[best_idx][:4]
            nx = min(mx, px)
            ny = min(my, py)
            nw = max(mx + mw, px + pw) - nx
            nh = max(my + mh, py + ph) - ny
            merged_mains[best_idx] = (nx, ny, nw, nh)
        else:
            merged_mains.append(list(pb[:4]))
            
    return [tuple(b[:4]) for b in merged_mains]


def sort_panel_entities(entities, panel_w, panel_h):
    """Sorts entities inside a panel according to standard natural reading order."""
    if len(entities) <= 1:
        return entities
        
    row_height = panel_h / 2.5
    
    def get_sort_key(ent):
        cx, cy = ent["center_x"], ent["center_y"]
        row_idx = int(cy // row_height)
        is_large = ent["area"] > (panel_w * panel_h * 0.15)
        type_priority = 0 if is_large else 1
        return (row_idx, type_priority, cx)
        
    sorted_ents = sorted(entities, key=get_sort_key)
    for i, ent in enumerate(sorted_ents):
        ent["label"] = i + 1
    return sorted_ents


def extract_storyboard_panels_and_entities(img_bgr: np.ndarray) -> List[Dict[str, Any]]:
    """Extracts panels and inner entities if no custom objects list is provided."""
    h_img, w_img = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 4)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    panel_bboxes = []
    min_panel_area = (w_img * h_img) * 0.04

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area >= min_panel_area:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < w_img * 0.98 or h < h_img * 0.98:
                panel_bboxes.append((x, y, w, h))

    if not panel_bboxes:
        panel_bboxes = [(0, 0, w_img, h_img)]
    else:
        panel_bboxes = sorted(panel_bboxes, key=lambda b: (b[1] // (h_img / 3), b[0]))

    panels_data = []
    for p_idx, (px, py, pw, ph) in enumerate(panel_bboxes):
        pad_x, pad_y = int(pw * 0.03), int(ph * 0.03)
        ix, iy = max(0, px + pad_x), max(0, py + pad_y)
        iw, ih = min(w_img - ix, max(10, pw - 2 * pad_x)), min(h_img - iy, max(10, ph - 2 * pad_y))

        panel_crop = img_bgr[iy:iy+ih, ix:ix+iw].copy()
        p_gray = gray[iy:iy+ih, ix:ix+iw]
        p_thresh = cv2.adaptiveThreshold(p_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 3)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(p_thresh, kernel, iterations=2)
        inner_cnts, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        raw_boxes = []
        for c in inner_cnts:
            ca = cv2.contourArea(c)
            if ca >= 120:
                raw_boxes.append(cv2.boundingRect(c))

        merged_boxes = merge_nearby_punctuation(raw_boxes, dist_thresh=int(iw * 0.05))

        entities = []
        for e_idx, (bx, by, bw, bh) in enumerate(merged_boxes):
            c_crop = panel_crop[by:by+bh, bx:bx+bw]
            c_mask = p_thresh[by:by+bh, bx:bx+bw]
            entities.append({
                "label": e_idx + 1,
                "name": f"Entity {e_idx + 1}",
                "rel_x": bx, "rel_y": by,
                "w": bw, "h": bh,
                "center_x": bx + bw / 2.0,
                "center_y": by + bh / 2.0,
                "area": bw * bh,
                "crop": c_crop,
                "mask": c_mask
            })

        entities = sort_panel_entities(entities, iw, ih)
        panels_data.append({
            "panel_name": f"Panel {p_idx + 1}",
            "entities": entities,
            "panel_crop": panel_crop,
            "offset_x": 0,
            "offset_y": 0
        })

    return panels_data


def build_gapless_orbital_path(
    img_crop: np.ndarray,
    ring_step: int = 5,
    sample_interval: float = 3.0,
    brush_radius: int = 8,
    drawing_direction: str = "OUTSIDE_IN",
    mask: np.ndarray = None
) -> List[List[Tuple[float, float]]]:
    """
    Generates contour-following drawing paths tracing the actual subject silhouette
    from the outer boundaries to the interior (Outside-In Boundary Layer Infill).
    """
    h, w = img_crop.shape[:2]
    if h <= 2 or w <= 2:
        return []

    if mask is None:
        gray = cv2.cvtColor(img_crop, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        if cv2.countNonZero(mask) < 20:
            mask = np.full((h, w), 255, dtype=np.uint8)

    step = max(2, int(ring_step))
    sample_interval = max(1.0, float(sample_interval))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (step * 2 + 1, step * 2 + 1))

    layer_masks = []
    curr = mask.copy()
    max_layers = max(10, min(150, max(h, w) // step))

    while cv2.countNonZero(curr) > 0 and len(layer_masks) < max_layers:
        layer_masks.append(curr.copy())
        eroded = cv2.erode(curr, kernel)
        if cv2.countNonZero(eroded) == cv2.countNonZero(curr):
            break
        curr = eroded

    if drawing_direction != "OUTSIDE_IN":
        layer_masks.reverse()

    all_strokes = []
    for m in layer_masks:
        contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        for c in contours:
            if len(c) < 4:
                continue
            pts = [tuple(p[0]) for p in c]
            sampled = []
            last_p = pts[0]
            sampled.append((float(last_p[0]), float(last_p[1])))
            accum = 0.0
            for p in pts[1:]:
                d = math.hypot(p[0] - last_p[0], p[1] - last_p[1])
                accum += d
                if accum >= sample_interval:
                    sampled.append((float(p[0]), float(p[1])))
                    accum = 0.0
                last_p = p
            sampled.append(sampled[0])
            all_strokes.append(sampled)

    if not all_strokes:
        # Fallback to bounding ellipse if no contours
        c_x, c_y = w / 2.0, h / 2.0
        max_radius = math.hypot(c_x, c_y)
        r_starts = np.arange(max_radius, 2.0, -step) if drawing_direction == "OUTSIDE_IN" else np.arange(2.0, max_radius, step)
        for r in r_starts:
            num_samples = max(12, int(round((2 * math.pi * r) / sample_interval)))
            angles = np.linspace(0, 2 * math.pi, num_samples, endpoint=False)
            ring_points = [(float(c_x + r * math.cos(a)), float(c_y + r * math.sin(a))) for a in angles]
            ring_points.append(ring_points[0])
            all_strokes.append(ring_points)

    return all_strokes


def render_concentric_orbital_whiteboard(
    image_input,
    output_path: str,
    fps: int = 30,
    drawing_speed: float = 1.5,
    camera_zoom_scale: float = 2.0,
    element_spacing: int = 24,
    drawing_direction: str = "OUTSIDE_IN",
    ring_step: int = 5,
    brush_radius: int = 8,
    sample_interval: float = 3.0,
    show_hand: bool = True,
    hand_scale: float = 0.95,
    end_hold_seconds: float = 1.5,
    custom_objects: list = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    character_drawing_speed: Optional[float] = None,
    text_drawing_speed: Optional[float] = None
) -> str:
    """
    Main 360° Concentric Gapless Orbital Whiteboard Rendering Engine.
    Generates professional 16:9 Widescreen MP4 animation video.
    """
    if isinstance(image_input, str):
        img = read_image_unicode(image_input)
    else:
        img = image_input

    if img is None:
        raise ValueError("Cannot load input image for rendering.")

    h_img, w_img = img.shape[:2]

    # Process custom objects or detect fallback panels
    if custom_objects and len(custom_objects) > 0:
        visible_objs = [o for o in custom_objects if getattr(o, "visibility", True)]
        if not visible_objs:
            visible_objs = list(custom_objects)

        active_objs = sorted(
            visible_objs,
            key=lambda x: (
                0 if getattr(x, "priority_order", None) not in (None, 0) else 1,
                int(getattr(x, "priority_order", 99999)) if getattr(x, "priority_order", None) not in (None, 0) else 99999
            )
        )

        panels_order = []
        panels_map = {}
        for idx, obj in enumerate(active_objs):
            pid = getattr(obj, "panel_id", idx + 1)
            if pid not in panels_map:
                panels_map[pid] = []
                panels_order.append(pid)
            panels_map[pid].append(obj)

        panel_data = []
        for p_idx, pid in enumerate(panels_order):
            p_objs = sorted(panels_map[pid], key=lambda o: getattr(o, "priority_order", 1))
            all_bboxes = [getattr(o, "global_bbox", None) or getattr(o, "bbox", (0, 0, 0, 0)) for o in p_objs]
            min_gx = max(0, min(b[0] for b in all_bboxes))
            min_gy = max(0, min(b[1] for b in all_bboxes))
            max_gx = min(w_img, max(b[0] + b[2] for b in all_bboxes))
            max_gy = min(h_img, max(b[1] + b[3] for b in all_bboxes))
            pw_actual = max(4, max_gx - min_gx)
            ph_actual = max(4, max_gy - min_gy)

            p_crop_combined = img[min_gy:max_gy, min_gx:max_gx].copy()

            p_entities = []
            for e_idx, obj in enumerate(p_objs):
                gbx, gby, gbw, gbh = getattr(obj, "global_bbox", None) or getattr(obj, "bbox", (0, 0, 0, 0))
                rel_x = max(0, gbx - min_gx)
                rel_y = max(0, gby - min_gy)
                cw = max(2, min(gbw, pw_actual - rel_x))
                ch = max(2, min(gbh, ph_actual - rel_y))

                c = getattr(obj, "crop", None)
                if c is None or getattr(c, "size", 0) == 0:
                    c = p_crop_combined[rel_y:rel_y+ch, rel_x:rel_x+cw].copy()

                if c.size == 0:
                    c = np.full((ch, cw, 3), 255, dtype=np.uint8)

                p_entities.append({
                    "label": e_idx + 1,
                    "name": obj.name,
                    "rel_x": rel_x,
                    "rel_y": rel_y,
                    "w": cw,
                    "h": ch,
                    "center_x": rel_x + cw / 2.0,
                    "center_y": rel_y + ch / 2.0,
                    "area": cw * ch,
                    "direction": getattr(obj, "direction", "RTL"),
                    "crop": c,
                    "mask": (cv2.cvtColor(c, cv2.COLOR_BGR2GRAY) < 235).astype(np.uint8) * 255
                })

            panel_data.append({
                "panel_name": f"Panel {p_idx+1}",
                "entities": p_entities,
                "panel_crop": p_crop_combined,
                "offset_x": 0,
                "offset_y": 0
            })
    else:
        panel_data = extract_storyboard_panels_and_entities(img)

    num_panels = len(panel_data)
    out_w, out_h = 1920, 1080
    user_gap = max(0, min(120, int(element_spacing)))
    available_w = max(400, out_w - (num_panels + 1) * user_gap)

    aspect_sum = sum(p["panel_crop"].shape[1] / max(1.0, float(p["panel_crop"].shape[0])) for p in panel_data)
    target_panel_h = min(560, max(140, int(available_w / max(0.1, aspect_sum))))

    scaled_panels = []
    for p in panel_data:
        p_crop = p["panel_crop"]
        ph, pw = p_crop.shape[:2]
        sc = target_panel_h / float(max(1, ph))
        nw = max(1, int(round(pw * sc)))
        resized_panel = cv2.resize(p_crop, (nw, target_panel_h), interpolation=cv2.INTER_AREA)
        scaled_panels.append({
            "panel_name": p["panel_name"],
            "entities": p["entities"],
            "raw_crop": p_crop,
            "scaled_crop": resized_panel,
            "scale": sc,
            "offset_x": p["offset_x"],
            "offset_y": p["offset_y"],
            "w": nw, "h": target_panel_h
        })

    total_panels_w = sum(p["w"] for p in scaled_panels)
    actual_gap = user_gap if (total_panels_w + (num_panels + 1) * user_gap <= out_w) else max(4, (out_w - total_panels_w) // (num_panels + 1))
    curr_x = actual_gap
    margin_y = (out_h - target_panel_h) // 2

    target_complete_canvas = np.full((out_h, out_w, 3), 255, dtype=np.uint8)
    entity_render_list = []

    for p_idx, p in enumerate(scaled_panels):
        pw, ph = p["w"], p["h"]
        px1 = curr_x
        py1 = margin_y

        x2 = min(out_w, px1 + pw)
        y2 = min(out_h, py1 + ph)
        dw = x2 - px1
        dh = y2 - py1
        if dw > 0 and dh > 0:
            target_complete_canvas[py1:y2, px1:x2] = p["scaled_crop"][:dh, :dw]

        sc = p["scale"]
        pox = p["offset_x"]
        poy = p["offset_y"]

        for e_idx, ent in enumerate(p["entities"]):
            ew_scaled = max(1, int(round(ent["w"] * sc)))
            eh_scaled = max(1, int(round(ent["h"] * sc)))
            ex_scaled = px1 + int(round((ent["rel_x"] - pox) * sc))
            ey_scaled = py1 + int(round((ent["rel_y"] - poy) * sc))
            ent_crop_scaled = cv2.resize(ent["crop"], (ew_scaled, eh_scaled), interpolation=cv2.INTER_AREA)

            entity_render_list.append({
                "panel_index": p_idx + 1,
                "panel_name": p["panel_name"],
                "entity_index": e_idx + 1,
                "total_in_panel": len(p["entities"]),
                "x1": ex_scaled, "y1": ey_scaled,
                "w": ew_scaled, "h": eh_scaled,
                "center_x": ex_scaled + ew_scaled / 2.0,
                "center_y": ey_scaled + eh_scaled / 2.0,
                "crop": ent_crop_scaled
            })

        curr_x += pw + actual_gap

    live_canvas = np.full((out_h, out_w, 3), 255, dtype=np.uint8)
    step_mask = np.zeros((out_h, out_w), dtype=np.uint8)

    hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH) if show_hand else None
    if hand_bgra is not None:
        hand_target_h = max(60, int(round(300 * max(0.2, float(hand_scale)))))
        scale_h = hand_target_h / float(hand_bgra.shape[0])
        new_hw = max(1, int(hand_bgra.shape[1] * scale_h))
        hand_bgra_scaled = cv2.resize(hand_bgra, (new_hw, hand_target_h), interpolation=cv2.INTER_AREA)
        scaled_tip_x = int(round(PEN_TIP_ANCHOR_X * scale_h))
        scaled_tip_y = int(round(PEN_TIP_ANCHOR_Y * scale_h))
    else:
        hand_bgra_scaled = None
        scaled_tip_x, scaled_tip_y = 0, 0

    writer = VideoEncoder(output_path, out_w, out_h, fps)

    full_cam_center = (out_w / 2.0, out_h / 2.0)
    full_cam_scale = 1.0
    brush_radius = max(2, int(brush_radius))

    current_cam_pos = full_cam_center
    current_cam_scale = full_cam_scale

    total_entities = len(entity_render_list)
    char_speed = float(character_drawing_speed if character_drawing_speed is not None else drawing_speed)
    text_speed = float(text_drawing_speed if text_drawing_speed is not None else drawing_speed)

    for i_ent, ent_info in enumerate(entity_render_list):
        is_text = any(t in str(ent_info.get("type", "")).upper() for t in ("TEXT", "TITLE", "UNDERLINE"))
        current_speed = text_speed if is_text else char_speed
        pts_per_frame = max(4, int(round(20 * (current_speed / 1.0))))

        p_name = ent_info["panel_name"]
        e_idx = ent_info["entity_index"]
        total_e = ent_info["total_in_panel"]
        c_x, c_y = ent_info["center_x"], ent_info["center_y"]
        ex1, ey1 = ent_info["x1"], ent_info["y1"]
        crop = ent_info["crop"]
        ew, eh = ent_info["w"], ent_info["h"]

        if camera_zoom_scale <= 1.05:
            target_zoom = 1.0
        else:
            base_fit = 800.0 / max(ew, eh)
            target_zoom = min(3.8, max(1.1, base_fit * (camera_zoom_scale / 2.0)))

        if progress_callback:
            pct = (i_ent / float(total_entities)) * 88.0
            progress_callback(pct, f"Drawing {p_name} — Entity {e_idx}/{total_e}...")

        # 1. Smooth camera transition
        if abs(target_zoom - current_cam_scale) > 0.05 or abs(c_x - current_cam_pos[0]) > 10:
            trans_frames = 8
            for tf in range(1, trans_frames + 1):
                t = tf / float(trans_frames)
                ease_t = t * t * (3.0 - 2.0 * t)
                cur_cx = current_cam_pos[0] + (c_x - current_cam_pos[0]) * ease_t
                cur_cy = current_cam_pos[1] + (c_y - current_cam_pos[1]) * ease_t
                cur_scale = current_cam_scale + (target_zoom - current_cam_scale) * ease_t

                cam_frame = render_camera_viewport(live_canvas, cur_cx, cur_cy, cur_scale, out_w, out_h)
                writer.write(cam_frame)

        current_cam_pos = (c_x, c_y)
        current_cam_scale = target_zoom

        # 2. Orbital paths
        char_strokes = build_gapless_orbital_path(
            crop,
            ring_step=max(1, int(ring_step)),
            sample_interval=max(1.0, float(sample_interval)),
            brush_radius=brush_radius,
            drawing_direction=drawing_direction
        )

        all_path_points = []
        for s in char_strokes:
            for p in s:
                all_path_points.append((ex1 + p[0], ey1 + p[1]))

        if not all_path_points:
            cx, cy = ex1 + ew / 2.0, ey1 + eh / 2.0
            r_w, r_h = max(6.0, ew / 2.0), max(6.0, eh / 2.0)
            angles = np.linspace(0, 2 * np.pi, 24)
            all_path_points = [(cx + r_w * np.cos(a), cy + r_h * np.sin(a)) for a in angles]
            all_path_points.append(all_path_points[0])
            live_canvas[ey1:min(out_h, ey1+eh), ex1:min(out_w, ex1+ew)] = target_complete_canvas[ey1:min(out_h, ey1+eh), ex1:min(out_w, ex1+ew)]

        last_pt = all_path_points[0]

        # 3. Drawing loop
        pt_idx = 0
        total_pts = len(all_path_points)
        while pt_idx < total_pts:
            next_idx = min(total_pts, pt_idx + pts_per_frame)
            sub_pts = all_path_points[pt_idx:next_idx]

            for pt in sub_pts:
                gx = int(round(pt[0]))
                gy = int(round(pt[1]))
                prev_gx = int(round(last_pt[0]))
                prev_gy = int(round(last_pt[1]))

                bx1 = max(0, min(prev_gx, gx) - brush_radius - 2)
                bx2 = min(out_w, max(prev_gx, gx) + brush_radius + 3)
                by1 = max(0, min(prev_gy, gy) - brush_radius - 2)
                by2 = min(out_h, max(prev_gy, gy) + brush_radius + 3)

                if bx1 < bx2 and by1 < by2:
                    sub_mask = step_mask[by1:by2, bx1:bx2]
                    sub_mask.fill(0)
                    p1_rel = (prev_gx - bx1, prev_gy - by1)
                    p2_rel = (gx - bx1, gy - by1)
                    cv2.line(sub_mask, p1_rel, p2_rel, 255, thickness=brush_radius * 2, lineType=cv2.LINE_AA)
                    cv2.circle(sub_mask, p2_rel, radius=brush_radius, color=255, thickness=-1, lineType=cv2.LINE_AA)
                    active = np.where(sub_mask > 0)
                    if len(active[0]) > 0:
                        live_canvas[by1:by2, bx1:bx2][active] = target_complete_canvas[by1:by2, bx1:bx2][active]

                last_pt = pt

            curr_tip_x = int(round(last_pt[0]))
            curr_tip_y = int(round(last_pt[1]))

            if hand_bgra_scaled is not None:
                canvas_with_hand = composite_hand_on_canvas_fast(live_canvas, hand_bgra_scaled, scaled_tip_x, scaled_tip_y, curr_tip_x, curr_tip_y)
                cam_view = render_camera_viewport(canvas_with_hand, c_x, c_y, target_zoom, out_w, out_h)
            else:
                cam_view = render_camera_viewport(live_canvas, c_x, c_y, target_zoom, out_w, out_h)

            writer.write(cam_view)
            pt_idx = next_idx

        # 4. Hand exit
        if last_pt and hand_bgra_scaled is not None:
            exit_f = 3
            for ef in range(1, exit_f + 1):
                t = ef / float(exit_f)
                hx = last_pt[0] + (c_x + 250 - last_pt[0]) * (t * t)
                hy = last_pt[1] + (c_y + 250 - last_pt[1]) * (t * t)
                c_exit = composite_hand_on_canvas_fast(live_canvas, hand_bgra_scaled, scaled_tip_x, scaled_tip_y, int(hx), int(hy))
                cam_view = render_camera_viewport(c_exit, c_x, c_y, target_zoom, out_w, out_h)
                writer.write(cam_view)

        # 5. Zoom out on panel end
        if e_idx == total_e and target_zoom > 1.05:
            zoom_out_frames = 8
            for zf in range(1, zoom_out_frames + 1):
                t = zf / float(zoom_out_frames)
                ease_t = t * t * (3.0 - 2.0 * t)
                cur_cx = c_x + (full_cam_center[0] - c_x) * ease_t
                cur_cy = c_y + (full_cam_center[1] - c_y) * ease_t
                cur_scale = target_zoom + (full_cam_scale - target_zoom) * ease_t

                cam_frame = render_camera_viewport(live_canvas, cur_cx, cur_cy, cur_scale, out_w, out_h)
                writer.write(cam_frame)

            current_cam_pos = full_cam_center
            current_cam_scale = full_cam_scale

            full_overview = render_camera_viewport(live_canvas, full_cam_center[0], full_cam_center[1], full_cam_scale, out_w, out_h)
            for _ in range(3):
                writer.write(full_overview)

    # 6. Final holding frames
    if progress_callback:
        progress_callback(96.0, "Finalizing Master Storyboard...")

    final_full_view = live_canvas.copy()
    final_hold_frames = max(1, int(round(fps * float(end_hold_seconds))))
    for _ in range(final_hold_frames):
        writer.write(final_full_view)

    writer.release()
    if progress_callback:
        progress_callback(100.0, "Complete!")

    return output_path
