"""
Whiteboard Processor — Universal Dual-Engine Whiteboard, Character & Typography Processor.
Integrates:
1. Dynamic Panel Discovery & Adaptive Border Suppression via DynamicBorderDetector.
2. Layer Splitting (MethodALayerSplitter): Pure Artwork/Graphics vs Typography.
3. Typography & Line Auditing (TextLineAuditor): Title, Underline, RTL Body Lines, Accents.
4. Character & Graphic Elements Auditing (audit_character_elements): Distinct components separated.
5. Color-Coded Execution Priority:
   - Priority 1: Title & Header Text (Gold / Cyan)
   - Priority 2: Underline (if present)
   - Priority 3: Character & Graphics Elements (Emerald / Green)
   - Priority 4: Body Text Lines in natural reading order (Blue / Indigo)
   - Priority 5: Accents & Decorative Icons (Purple / Coral)
"""
import logging
from typing import List, Tuple, Optional, Callable, Dict, Any
import cv2
import numpy as np

from ..core.scene import Scene, SceneObject, SceneConfig
from ..core.project import Project, StructureType, PanelStructure
from .dynamic_border_detector import DynamicBorderDetector
from .m2_layer_splitter import MethodALayerSplitter
from .m3_text_line_auditor import TextLineAuditor

logger = logging.getLogger(__name__)


def audit_character_elements(gfx_bgr: np.ndarray, min_area: int = 40) -> List[Dict[str, Any]]:
    """Audits pure graphics layer and isolates distinct character and icon components."""
    h, w = gfx_bgr.shape[:2]
    gray = cv2.cvtColor(gfx_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(gfx_bgr, cv2.COLOR_BGR2HSV)
    is_ink = ((gray < 230) | (hsv[:, :, 1] > 20)).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    closed_ink = cv2.morphologyEx(is_ink, cv2.MORPH_CLOSE, k, iterations=1)
    num_cc, labels, stats, centroids = cv2.connectedComponentsWithStats(closed_ink)
    elements = []
    for i in range(1, num_cc):
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_area:
            bx = int(stats[i, cv2.CC_STAT_LEFT])
            by = int(stats[i, cv2.CC_STAT_TOP])
            bw = int(stats[i, cv2.CC_STAT_WIDTH])
            bh = int(stats[i, cv2.CC_STAT_HEIGHT])
            cx, cy = centroids[i]
            elem_mask = (labels == i).astype(np.uint8) * 255
            elements.append({
                'id': len(elements) + 1,
                'bbox': (bx, by, bw, bh),
                'centroid': (cx, cy),
                'area': area,
                'mask': elem_mask
            })
    elements = sorted(elements, key=lambda e: (round(e['centroid'][1] / max(1.0, h * 0.40)), e['centroid'][0]))
    for idx, e in enumerate(elements):
        e['id'] = idx + 1
    return elements


class WhiteboardProcessor:
    @staticmethod
    def discover_panels(image_bgr: np.ndarray) -> List[Dict[str, Any]]:
        """Discovers panels dynamically (1..N) using frame contour analysis & gutter projection."""
        ih, iw = image_bgr.shape[:2]
        gray_img = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_img, 30, 110)

        # Method A: Structural frame contours with NMS suppression
        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if (iw * 0.12 <= w <= iw * 0.60) and (ih * 0.12 <= h <= ih * 0.60):
                aspect = w / float(h)
                if 0.55 <= aspect <= 2.5:
                    candidates.append((x, y, w, h))

        candidates = sorted(candidates, key=lambda b: b[2] * b[3], reverse=True)
        outer_boxes = []
        for b in candidates:
            x1, y1, w1, h1 = b
            is_nested = False
            for ox, oy, ow, oh in outer_boxes:
                ix = max(x1, ox)
                iy = max(y1, oy)
                iw_box = min(x1 + w1, ox + ow) - ix
                ih_box = min(y1 + h1, oy + oh) - iy
                if iw_box > 0 and ih_box > 0:
                    overlap = (iw_box * ih_box) / float(w1 * h1)
                    if overlap > 0.45:
                        is_nested = True
                        break
            if not is_nested:
                outer_boxes.append(b)

        discovered_panels = []
        if len(outer_boxes) in [4, 6, 8, 9, 12, 16, 20]:
            widths = [b[2] for b in outer_boxes]
            heights = [b[3] for b in outer_boxes]
            w_cv = np.std(widths) / float(max(1.0, np.mean(widths)))
            h_cv = np.std(heights) / float(max(1.0, np.mean(heights)))
            if w_cv < 0.15 and h_cv < 0.15:
                mean_h = np.mean(heights)
                outer_boxes.sort(key=lambda b: (round(b[1] / (mean_h * 0.7)), b[0]))
                for idx, (px, py, pw, ph) in enumerate(outer_boxes):
                    discovered_panels.append({
                        "id": idx + 1,
                        "bbox": (int(px), int(py), int(pw), int(ph)),
                        "center": (px + pw / 2.0, py + ph / 2.0)
                    })

        # Method B: Dynamic Gutter Valley Projection if contours are irregular
        if not discovered_panels:
            ink_density = (gray_img < 220).astype(np.float32)
            h_proj = ink_density.mean(axis=1)
            v_proj = ink_density.mean(axis=0)

            candidate_grids = [(4, 4), (3, 4), (4, 3), (2, 4), (4, 2), (3, 3), (2, 3), (3, 2), (2, 2), (5, 4), (1, 1)]
            best_grid = (1, 1)
            best_score = float('inf')
            best_splits = ([], [])

            for rows, cols in candidate_grids:
                if rows == 1 and cols == 1:
                    continue
                cell_aspect = (iw / float(cols)) / (ih / float(rows))
                if cell_aspect < 0.65 or cell_aspect > 2.2:
                    continue
                expected_y = [int(r * ih / float(rows)) for r in range(1, rows)]
                expected_x = [int(c * iw / float(cols)) for c in range(1, cols)]

                def score_splits(proj, splits):
                    s_list, p_list = [], []
                    for sp in splits:
                        rad = max(4, int(len(proj) * 0.04))
                        st = max(0, sp - rad)
                        en = min(len(proj), sp + rad)
                        s_list.append(np.min(proj[st:en]))
                        p_list.append(st + int(np.argmin(proj[st:en])))
                    return (np.mean(s_list) if s_list else 1.0), p_list

                ys, ypos = score_splits(h_proj, expected_y)
                xs, xpos = score_splits(v_proj, expected_x)
                complexity_penalty = (rows * cols) * 0.0005
                total = ys + xs + complexity_penalty
                if total < best_score:
                    best_score = total
                    best_grid = (rows, cols)
                    best_splits = (ypos, xpos)

            if best_grid != (1, 1) and best_score < 0.40:
                rows, cols = best_grid
                y_bounds = [0] + best_splits[0] + [ih]
                x_bounds = [0] + best_splits[1] + [iw]
                p_id = 1
                for r in range(rows):
                    for c in range(cols):
                        px = x_bounds[c]
                        py = y_bounds[r]
                        pw = x_bounds[c + 1] - px
                        ph = y_bounds[r + 1] - py
                        discovered_panels.append({
                            "id": p_id,
                            "bbox": (int(px), int(py), int(pw), int(ph)),
                            "center": (px + pw / 2.0, py + ph / 2.0)
                        })
                        p_id += 1
            else:
                discovered_panels.append({
                    "id": 1,
                    "bbox": (0, 0, iw, ih),
                    "center": (iw / 2.0, ih / 2.0)
                })

        return discovered_panels

    @staticmethod
    def process(image_bgr: np.ndarray, config: SceneConfig,
                progress_cb: Optional[Callable[[float, str], None]] = None) -> Project:
        """Standard entry point that discovers panels and performs deep decomposition."""
        discovered_panels = WhiteboardProcessor.discover_panels(image_bgr)
        return WhiteboardProcessor.process_with_panels(image_bgr, discovered_panels, config, progress_cb)

    @staticmethod
    def process_with_panels(image_bgr: np.ndarray, panels_data: List[Dict[str, Any]], config: SceneConfig,
                            progress_cb: Optional[Callable[[float, str], None]] = None) -> Project:
        """
        Deep extraction pipeline for specified panel bounding boxes:
        1. Dynamic Border Trimming
        2. Layer Splitting (Artwork vs Typography)
        3. Typography Line Auditing (Full text lines & RTL direction)
        4. Graphics Elements Auditing (Isolated characters & icons)
        """
        def _report(pct, msg):
            if progress_cb:
                progress_cb(pct, msg)

        ih, iw = image_bgr.shape[:2]
        _report(15.0, f"Extracting {len(panels_data)} panels with dynamic border & layer suppression...")

        panel_structs = []
        scenes = []
        is_storyboard = len(panels_data) >= 2

        for p_idx, p_data in enumerate(panels_data):
            p_id = p_data.get("id", p_idx + 1)
            pct = 20.0 + (p_idx / float(max(1, len(panels_data)))) * 75.0
            _report(pct, f"Extracting layers for Panel {p_id:02d}...")

            px, py, pw, ph = p_data["bbox"]
            px = max(0, min(iw - 1, int(round(px))))
            py = max(0, min(ih - 1, int(round(py))))
            pw = max(2, min(iw - px, int(round(pw))))
            ph = max(2, min(ih - py, int(round(ph))))

            raw_crop = image_bgr[py:py+ph, px:px+pw].copy()

            # Dynamic Border Detection & Adaptive Stripping
            border_res = DynamicBorderDetector.detect_and_trim_panel_border(raw_crop)
            clean_crop = border_res["clean_crop"]
            t_top, t_bottom, t_left, t_right = border_res["insets"]

            interior_x = px + t_left
            interior_y = py + t_top
            interior_w = max(1, pw - t_left - t_right)
            interior_h = max(1, ph - t_top - t_bottom)
            interior_bbox = (interior_x, interior_y, interior_w, interior_h)

            # Layer Separation on clean interior crop
            split_res = MethodALayerSplitter.split(clean_crop)
            gfx_raw = split_res["graphics_image"]
            txt_raw = split_res["text_image"]
            gfx_mask = split_res["graphics_mask"]
            txt_mask = split_res["text_mask"]

            # Deep Typography Line Auditing
            audit_res = TextLineAuditor.audit_lines(txt_raw)
            lines = audit_res["lines"]
            accents = audit_res["accents"]

            panel_scene_objs = []
            priority_counter = 1

            # Priority 1: Title & Header Text
            if lines and lines[0]["type"] in ("TITLE", "TEXT_LINE"):
                first_line = lines[0]
                lx, ly, lw, lh = first_line["bbox"]
                gx = interior_x + lx
                gy = interior_y + ly
                crop = clean_crop[ly:ly+lh, lx:lx+lw].copy() if ly+lh <= clean_crop.shape[0] and lx+lw <= clean_crop.shape[1] else None
                obj = SceneObject(
                    name=f"Panel {p_id:02d} - Title",
                    bbox=(lx, ly, lw, lh),
                    global_bbox=(gx, gy, lw, lh),
                    panel_id=p_id,
                    width=lw,
                    height=lh,
                    area=lw * lh,
                    crop=crop,
                    direction=first_line.get("direction", "RTL"),
                    element_type="TEXT",
                    priority_order=priority_counter
                )
                obj.mask = first_line["mask"][ly:ly+lh, lx:lx+lw]
                obj.scene_source_image = image_bgr
                panel_scene_objs.append(obj)
                priority_counter += 1

            # Priority 2: Underline Bar (if present)
            if len(lines) > 1 and lines[1]["type"] == "UNDERLINE":
                und_line = lines[1]
                lx, ly, lw, lh = und_line["bbox"]
                gx = interior_x + lx
                gy = interior_y + ly
                crop = clean_crop[ly:ly+lh, lx:lx+lw].copy() if ly+lh <= clean_crop.shape[0] and lx+lw <= clean_crop.shape[1] else None
                obj = SceneObject(
                    name=f"Panel {p_id:02d} - Underline",
                    bbox=(lx, ly, lw, lh),
                    global_bbox=(gx, gy, lw, lh),
                    panel_id=p_id,
                    width=lw,
                    height=lh,
                    area=lw * lh,
                    crop=crop,
                    direction="LTR",
                    element_type="UNDERLINE",
                    priority_order=priority_counter
                )
                obj.mask = und_line["mask"][ly:ly+lh, lx:lx+lw]
                obj.scene_source_image = image_bgr
                panel_scene_objs.append(obj)
                priority_counter += 1

            # Priority 3: Character & Graphics Elements (Fine-grained separation)
            gfx_elements = audit_character_elements(gfx_raw)
            if gfx_elements:
                for g_elem in gfx_elements:
                    bx, by, bw, bh = g_elem["bbox"]
                    gx = interior_x + bx
                    gy = interior_y + by
                    g_crop = clean_crop[by:by+bh, bx:bx+bw].copy() if by+bh <= clean_crop.shape[0] and bx+bw <= clean_crop.shape[1] else None
                    elem_m = g_elem["mask"][by:by+bh, bx:bx+bw]
                    elem_title = f"Panel {p_id:02d} - Graphic {g_elem['id']}" if len(gfx_elements) > 1 else f"Panel {p_id:02d} - Character / Art"
                    
                    obj = SceneObject(
                        name=elem_title,
                        bbox=(bx, by, bw, bh),
                        global_bbox=(gx, gy, bw, bh),
                        panel_id=p_id,
                        width=bw,
                        height=bh,
                        area=int(g_elem["area"]),
                        crop=g_crop,
                        direction="CIRCUIT",
                        element_type="CHARACTER",
                        priority_order=priority_counter
                    )
                    obj.mask = elem_m
                    obj.scene_source_image = image_bgr
                    panel_scene_objs.append(obj)
                    priority_counter += 1
            elif cv2.countNonZero(gfx_mask) > 30:
                ys_g, xs_g = np.where(gfx_mask > 0)
                gx1, gy1 = int(xs_g.min()), int(ys_g.min())
                gx2, gy2 = int(xs_g.max()), int(ys_g.max())
                gw = gx2 - gx1 + 1
                gh = gy2 - gy1 + 1
                g_crop = clean_crop[gy1:gy2+1, gx1:gx2+1].copy()
                g_mask = gfx_mask[gy1:gy2+1, gx1:gx2+1]

                obj = SceneObject(
                    name=f"Panel {p_id:02d} - Character / Art",
                    bbox=(gx1, gy1, gw, gh),
                    global_bbox=(interior_x + gx1, interior_y + gy1, gw, gh),
                    panel_id=p_id,
                    width=gw,
                    height=gh,
                    area=gw * gh,
                    crop=g_crop,
                    direction="CIRCUIT",
                    element_type="CHARACTER",
                    priority_order=priority_counter
                )
                obj.mask = g_mask
                obj.scene_source_image = image_bgr
                panel_scene_objs.append(obj)
                priority_counter += 1

            # Priority 4: Body Text Lines
            body_start_idx = 2 if (len(lines) > 1 and lines[1]["type"] == "UNDERLINE") else 1
            for l_idx, l in enumerate(lines[body_start_idx:]):
                lx, ly, lw, lh = l["bbox"]
                gx = interior_x + lx
                gy = interior_y + ly
                crop = clean_crop[ly:ly+lh, lx:lx+lw].copy() if ly+lh <= clean_crop.shape[0] and lx+lw <= clean_crop.shape[1] else None
                obj = SceneObject(
                    name=f"Panel {p_id:02d} - Text Line {l_idx + 1}",
                    bbox=(lx, ly, lw, lh),
                    global_bbox=(gx, gy, lw, lh),
                    panel_id=p_id,
                    width=lw,
                    height=lh,
                    area=lw * lh,
                    crop=crop,
                    direction=l.get("direction", "RTL"),
                    element_type="TEXT",
                    priority_order=priority_counter
                )
                obj.mask = l["mask"][ly:ly+lh, lx:lx+lw]
                obj.scene_source_image = image_bgr
                panel_scene_objs.append(obj)
                priority_counter += 1

            # Priority 5: Accents & Decorative Icons
            for a_idx, acc in enumerate(accents):
                ax, ay, aw, ah = acc["bbox"]
                gx = interior_x + ax
                gy = interior_y + ay
                crop = clean_crop[ay:ay+ah, ax:ax+aw].copy() if ay+ah <= clean_crop.shape[0] and ax+aw <= clean_crop.shape[1] else None
                obj = SceneObject(
                    name=f"Panel {p_id:02d} - Accent {a_idx + 1}",
                    bbox=(ax, ay, aw, ah),
                    global_bbox=(gx, gy, aw, ah),
                    panel_id=p_id,
                    width=aw,
                    height=ah,
                    area=aw * ah,
                    crop=crop,
                    direction="LTR",
                    element_type="ICON",
                    priority_order=priority_counter
                )
                obj.mask = acc["mask"][ay:ay+ah, ax:ax+aw]
                obj.scene_source_image = image_bgr
                panel_scene_objs.append(obj)
                priority_counter += 1

            # Fallback if no sub-objects were found
            if not panel_scene_objs:
                obj = SceneObject(
                    name=f"Panel {p_id:02d} - Artwork",
                    bbox=(0, 0, interior_w, interior_h),
                    global_bbox=interior_bbox,
                    panel_id=p_id,
                    width=interior_w,
                    height=interior_h,
                    area=interior_w * interior_h,
                    crop=clean_crop,
                    direction="CIRCUIT",
                    element_type="CHARACTER",
                    priority_order=1
                )
                obj.scene_source_image = image_bgr
                panel_scene_objs.append(obj)

            ps = PanelStructure(
                id=p_id,
                bbox=(px, py, pw, ph),
                interior_bbox=interior_bbox,
                border_mask=np.zeros((ph, pw), dtype=np.uint8),
                source_image=clean_crop,
                content_region_image=clean_crop
            )
            ps.raw_crop = raw_crop
            ps.clean_crop = clean_crop
            panel_structs.append(ps)

            sc = Scene(
                config=config,
                objects=panel_scene_objs,
                source_image=clean_crop,
                canvas_width=interior_w,
                canvas_height=interior_h,
                panel_id=p_id,
                panel_bbox=(px, py, pw, ph),
                interior_bbox=interior_bbox
            )
            scenes.append(sc)

        project = Project(
            structure_type=StructureType.STORYBOARD if is_storyboard else StructureType.SINGLE_SCENE,
            panels=panel_structs,
            scenes=scenes,
            source_image=image_bgr,
            original_width=iw,
            original_height=ih
        )

        _report(100.0, "Composition Analysis & Layer Extraction Complete!")
        return project
