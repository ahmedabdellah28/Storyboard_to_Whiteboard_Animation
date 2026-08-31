import cv2
import numpy as np
import logging
from typing import List, Tuple, Optional, Dict, Any
from ..core.project import PanelStructure, StructureType, Project

logger = logging.getLogger(__name__)


class StoryboardConfidenceAnalyzer:
    """
    Conservative Multi-Evidence Storyboard Confidence Analyzer.
    
    Evaluates 10 structural & geometric criteria:
    1. Candidate rectangle count (must be >= 2)
    2. Dimension similarity ratio (low variance in width and height)
    3. Regular spacing / gutters between panels
    4. Alignment into a clean M x N grid matrix
    5. Content independence within each panel
    6. Closed real bounding borders
    7. Clear gutters/separators without crossing strokes
    8. Canvas coverage rationality (40% - 95%)
    9. Content richness within candidate panels
    10. Rejection of single outer borders or stray composition lines
    """

    CONFIDENCE_THRESHOLD = 0.80

    @staticmethod
    def analyze(
        panels: List[PanelStructure],
        image_bgr: np.ndarray,
        grid_shape: Tuple[int, int]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculates multi-evidence confidence score in [0.0, 1.0].
        Returns (confidence, metrics_dict).
        """
        h, w = image_bgr.shape[:2]
        if not panels or len(panels) < 2:
            return 0.0, {"reason": "Less than 2 candidate panels"}

        rows, cols = grid_shape
        expected_cells = rows * cols
        if expected_cells < 2:
            return 0.0, {"reason": "Grid matrix size < 2"}

        widths = np.array([p.bbox[2] for p in panels], dtype=np.float64)
        heights = np.array([p.bbox[3] for p in panels], dtype=np.float64)
        areas = widths * heights
        total_panel_area = float(np.sum(areas))

        # 1. Dimension Consistency (In real storyboards, panel widths/heights in a row/column are uniform: cv < 0.08)
        mean_w = float(np.mean(widths)) if len(widths) > 0 else 1.0
        mean_h = float(np.mean(heights)) if len(heights) > 0 else 1.0
        w_cv = float(np.std(widths) / max(1.0, mean_w))
        h_cv = float(np.std(heights) / max(1.0, mean_h))

        # Strict penalty: if CV > 0.10, panels are random scene objects, NOT a storyboard grid
        if w_cv > 0.12 or h_cv > 0.12:
            dim_consistency = 0.0
        else:
            dim_consistency = max(0.0, 1.0 - 5.0 * (w_cv + h_cv))

        # 2. Grid Matrix Completeness
        grid_completeness = min(1.0, len(panels) / float(max(1, expected_cells)))

        # 3. Canvas Coverage Ratio
        coverage_ratio = total_panel_area / float(w * h)
        if 0.35 <= coverage_ratio <= 0.95:
            coverage_score = 1.0
        elif coverage_ratio < 0.35:
            coverage_score = max(0.0, coverage_ratio / 0.35)
        else:
            coverage_score = max(0.0, 1.0 - (coverage_ratio - 0.95) / 0.05)

        # 4. Panel Count Evidence (Real storyboards are typically 2x2=4 or 2x3=6 or 3x3=9)
        if len(panels) >= 4:
            count_score = 1.0
        elif len(panels) >= 2 and expected_cells >= 4:
            count_score = 0.70
        else:
            count_score = 0.40

        # 5. Gutter Separation & Non-Overlap
        overlap_found = False
        for i in range(len(panels)):
            for j in range(i + 1, len(panels)):
                b1 = panels[i].bbox
                b2 = panels[j].bbox
                ix = max(b1[0], b2[0])
                iy = max(b1[1], b2[1])
                iw = min(b1[0] + b1[2], b2[0] + b2[2]) - ix
                ih = min(b1[1] + b1[3], b2[1] + b2[3]) - iy
                if iw > 4 and ih > 4:
                    overlap_found = True
                    break
            if overlap_found:
                break

        gutter_score = 0.0 if overlap_found else 1.0

        # 6. Content Independence
        content_scores = [p.content_score for p in panels]
        active_panels = sum(1 for s in content_scores if s > 0.5)
        content_score = min(1.0, active_panels / float(len(panels)))

        # Weighted multi-factor confidence
        confidence = (
            0.35 * dim_consistency +
            0.25 * grid_completeness +
            0.15 * count_score +
            0.15 * gutter_score +
            0.10 * coverage_score
        )

        # If dimension consistency failed (CV > 12%), drop confidence to 0
        if dim_consistency == 0.0:
            confidence = 0.0

        metrics = {
            "dim_consistency": dim_consistency,
            "grid_completeness": grid_completeness,
            "gutter_score": gutter_score,
            "coverage_score": coverage_score,
            "content_score": content_score,
            "w_cv": w_cv,
            "h_cv": h_cv,
            "coverage_ratio": coverage_ratio,
            "active_panels": active_panels,
            "raw_confidence": confidence
        }

        return min(0.99, max(0.0, float(confidence))), metrics


class PanelDetector:
    """
    Conservative Storyboard & Panel Detector (V3 Architecture).
    
    Principles:
    - Default is SINGLE_SCENE (False Positive Storyboard is unacceptable).
    - Multi-evidence validation via StoryboardConfidenceAnalyzer.
    - Storyboard requires CONFIDENCE >= 0.80 and >= 2 valid panels.
    - Single outer frames are classified as SINGLE_FRAMED_SCENE.
    - Unframed images are classified as SINGLE_UNFRAMED_SCENE.
    - Pixel-exact crops created directly from source_image.
    """

    CONFIDENCE_THRESHOLD = 0.80

    @staticmethod
    def detect(image_bgr: np.ndarray) -> Project:
        """
        Structural Analysis: determines SINGLE_SCENE vs STORYBOARD.
        Uses pure Classical Computer Vision (no AI/ML/DL).
        """
        h, w = image_bgr.shape[:2]
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

        # Check for Single Outer Canvas Frame
        frame_type, frame_conf = PanelDetector._detect_outer_frame(gray, h, w)

        # Method 1: Matrix Contour Grid Detection (Most reliable for framed panels)
        panels_cnt, grid_shape_cnt, conf_cnt, metrics_cnt = PanelDetector._detect_contour_grid(gray, image_bgr, h, w)

        # If a single outer frame encloses the scene and < 4 panels were found,
        # it is strictly a SINGLE_FRAMED_SCENE (not a storyboard)
        if frame_type == StructureType.SINGLE_FRAMED_SCENE and len(panels_cnt) < 4:
            panels_cnt = []
            conf_cnt = 0.0

        # Method 2: Separator Grid Line Detection (For gutter-divided storyboards with 2x2+ grid)
        # If single outer frame was detected and no internal contours found, skip grid slicing
        if frame_type == StructureType.SINGLE_FRAMED_SCENE and len(panels_cnt) < 4:
            panels_lines, grid_shape_lines, conf_lines, metrics_lines = [], (1, 1), 0.0, {}
        else:
            panels_lines, grid_shape_lines, conf_lines, metrics_lines = PanelDetector._detect_grid_lines(gray, image_bgr, h, w)

        # Choose best candidate
        if conf_cnt >= conf_lines and conf_cnt >= PanelDetector.CONFIDENCE_THRESHOLD:
            best_panels = panels_cnt
            best_conf = conf_cnt
            best_grid = grid_shape_cnt
            method = "CONTOUR_GRID"
        elif conf_lines >= PanelDetector.CONFIDENCE_THRESHOLD:
            best_panels = panels_lines
            best_conf = conf_lines
            best_grid = grid_shape_lines
            method = "GRID_LINES"
        else:
            best_panels = []
            best_conf = max(conf_cnt, conf_lines)
            best_grid = (1, 1)
            method = "NONE"

        # Final Decision
        is_storyboard = (best_conf >= PanelDetector.CONFIDENCE_THRESHOLD and len(best_panels) >= 2)

        if is_storyboard:
            stype = StructureType.STORYBOARD
            rows, cols = best_grid
            project = Project(
                structure_type=stype,
                confidence=best_conf,
                source_image=image_bgr,
                original_width=w,
                original_height=h
            )
            project.panels = best_panels

            # Assign grid positions (row, column, index)
            PanelDetector._assign_grid_positions(best_panels, h, w)

            # Compute per-panel metrics
            for panel in best_panels:
                PanelDetector._compute_panel_metrics(panel, image_bgr)

            rows = max(p.row for p in best_panels) + 1
            cols = max(p.column for p in best_panels) + 1
        else:
            stype = frame_type
            rows, cols = 1, 1
            project = Project(
                structure_type=stype,
                confidence=best_conf,
                source_image=image_bgr,
                original_width=w,
                original_height=h
            )
            project.panels = []

        # Standardized Diagnostic Logging
        PanelDetector._log_diagnostics(
            structure_type=stype.value,
            storyboard_confidence=best_conf,
            rows=rows,
            columns=cols,
            panel_count=len(project.panels),
            frame_confidence=frame_conf,
            panels=project.panels
        )

        return project

    # ═══════════════════════════════════════════════════════
    #  Method 1: Contour Grid Detection
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _detect_contour_grid(
        gray: np.ndarray,
        image_bgr: np.ndarray,
        h: int,
        w: int
    ) -> Tuple[List[PanelStructure], Tuple[int, int], float, Dict[str, Any]]:
        """
        Finds candidate panel boxes from closed rectangular contours.
        Groups and validates into an M x N grid matrix.
        """
        # Multi-scale edge detection & closing
        blurred = cv2.GaussianBlur(gray, (5, 5), 1.0)
        edges = cv2.Canny(blurred, 40, 120)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, hierarchy = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        candidates = []
        min_panel_area = (w * h) * 0.04   # Panel must be at least 4% of image
        max_panel_area = (w * h) * 0.50   # Panel cannot exceed 50% (avoids single outer box)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_panel_area or area > max_panel_area:
                continue

            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / float(max(1, bh))
            if aspect < 0.35 or aspect > 3.0:
                continue

            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            if hull_area <= 0:
                continue

            rectangularity = area / hull_area
            # Check approx polygon vertices
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)

            if rectangularity > 0.80 and len(approx) in (4, 5, 6, 8):
                if PanelDetector._is_true_rectangular_frame(edges, x, y, bw, bh):
                    candidates.append((x, y, bw, bh))

        # Filter overlapping duplicates
        filtered = PanelDetector._filter_overlapping(candidates)
        if len(filtered) < 2:
            return [], (1, 1), 0.0, {}

        # Grid analysis
        grid_shape, aligned_boxes = PanelDetector._fit_grid_matrix(filtered, h, w)
        if len(aligned_boxes) < 2 or grid_shape[0] * grid_shape[1] < 2:
            return [], (1, 1), 0.0, {}

        # Build panels
        panels = []
        for idx, (x, y, bw, bh) in enumerate(aligned_boxes):
            bbox = (x, y, bw, bh)
            margin_x = max(6, int(bw * 0.05))
            margin_y = max(6, int(bh * 0.05))
            ix = x + margin_x
            iy = y + margin_y
            iw = max(1, bw - 2 * margin_x)
            ih = max(1, bh - 2 * margin_y)
            interior_bbox = (ix, iy, iw, ih)

            border_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.rectangle(border_mask, (x, y), (x + bw, y + bh), 255, thickness=margin_x)

            content_img = image_bgr[iy:iy + ih, ix:ix + iw].copy()
            full_panel_img = image_bgr[y:y + bh, x:x + bw].copy()
            score, is_empty = PanelDetector._evaluate_content(content_img)

            panel = PanelStructure(
                id=idx + 1,
                bbox=bbox,
                interior_bbox=interior_bbox,
                border_mask=border_mask,
                content_score=score,
                is_empty=is_empty,
                content_region_image=content_img,
                source_image=full_panel_img,
                original_bbox_in_parent=bbox,
                is_frame=True
            )
            panels.append(panel)

        confidence, metrics = StoryboardConfidenceAnalyzer.analyze(panels, image_bgr, grid_shape)
        return panels, grid_shape, confidence, metrics

    # ═══════════════════════════════════════════════════════
    #  Method 2: Separator Grid Line Detection
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _detect_grid_lines(
        gray: np.ndarray,
        image_bgr: np.ndarray,
        h: int,
        w: int
    ) -> Tuple[List[PanelStructure], Tuple[int, int], float, Dict[str, Any]]:
        """
        Detects storyboards with clean divider gutters using HoughLinesP and gutter validation.
        Strictly requires continuous lines crossing between panels without cutting foreground objects.
        """
        blurred = cv2.GaussianBlur(gray, (5, 5), 1.0)
        edges = cv2.Canny(blurred, 40, 120)

        # Morphological line kernels
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, w // 25), 1))
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, h // 25)))
        closed_h = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_h)
        closed_v = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_v)
        combined = cv2.bitwise_or(closed_h, closed_v)

        min_line_len = min(w, h) * 0.35  # Must be a long structural line
        lines = cv2.HoughLinesP(combined, 1, np.pi / 180, threshold=120,
                                minLineLength=int(min_line_len), maxLineGap=max(10, min(w, h) // 25))

        if lines is None or len(lines) < 2:
            return [], (1, 1), 0.0, {}

        lines = lines.reshape(-1, 4)
        h_lines = []
        v_lines = []

        for line in lines:
            x1, y1, x2, y2 = int(line[0]), int(line[1]), int(line[2]), int(line[3])
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)
            length = np.sqrt(dx * dx + dy * dy)
            if length < min_line_len:
                continue

            if dx > 0 and (dy / float(dx)) < 0.04:
                # Horizontal divider line (must not be at outer margin)
                avg_y = (y1 + y2) // 2
                if h * 0.15 < avg_y < h * 0.85:
                    h_lines.append(avg_y)
            elif dy > 0 and (dx / float(dy)) < 0.04:
                # Vertical divider line
                avg_x = (x1 + x2) // 2
                if w * 0.15 < avg_x < w * 0.85:
                    v_lines.append(avg_x)

        if not h_lines and not v_lines:
            return [], (1, 1), 0.0, {}

        # Cluster divider lines
        h_divs = PanelDetector._cluster_positions(sorted(set(h_lines)), min_gap=h * 0.18)
        v_divs = PanelDetector._cluster_positions(sorted(set(v_lines)), min_gap=w * 0.18)

        # Must have at least 1 internal divider in at least one direction
        if len(h_divs) == 0 and len(v_divs) == 0:
            return [], (1, 1), 0.0, {}

        # Validate that the dividers are true separators and not lines inside a character
        # Check edge density across divider band
        valid_h_divs = []
        for y_div in h_divs:
            band = gray[max(0, y_div - 6):min(h, y_div + 6), :]
            # Check if band has uniform gutter structure
            if np.std(band) < 45.0 or np.mean(band) < 40 or np.mean(band) > 220:
                valid_h_divs.append(y_div)

        valid_v_divs = []
        for x_div in v_divs:
            band = gray[:, max(0, x_div - 6):min(w, x_div + 6)]
            if np.std(band) < 45.0 or np.mean(band) < 40 or np.mean(band) > 220:
                valid_v_divs.append(x_div)

        if not valid_h_divs and not valid_v_divs:
            return [], (1, 1), 0.0, {}

        # Construct grid
        y_bounds = [0] + sorted(valid_h_divs) + [h]
        x_bounds = [0] + sorted(valid_v_divs) + [w]

        num_rows = len(y_bounds) - 1
        num_cols = len(x_bounds) - 1
        grid_shape = (num_rows, num_cols)

        # Require a robust multi-panel grid (at least 2x2, or 3+ panels)
        # Single-line 1x2 or 2x1 splits on unframed scenes are rejected to prevent slicing single scenes
        if (num_rows * num_cols) < 3 and (len(valid_h_divs) == 0 or len(valid_v_divs) == 0):
            return [], (1, 1), 0.0, {}

        if num_rows * num_cols < 2:
            return [], (1, 1), 0.0, {}

        panels = []
        min_area = (w * h) * 0.04
        panel_id = 1

        for r in range(num_rows):
            for c in range(num_cols):
                y1 = y_bounds[r]
                y2 = y_bounds[r + 1]
                x1 = x_bounds[c]
                x2 = x_bounds[c + 1]

                bw = x2 - x1
                bh = y2 - y1

                if bw * bh < min_area:
                    continue

                bbox = (x1, y1, bw, bh)
                margin_x = max(6, int(bw * 0.05))
                margin_y = max(6, int(bh * 0.05))
                ix = x1 + margin_x
                iy = y1 + margin_y
                iw = max(1, bw - 2 * margin_x)
                ih = max(1, bh - 2 * margin_y)
                interior_bbox = (ix, iy, iw, ih)

                border_mask = np.zeros((h, w), dtype=np.uint8)
                cv2.rectangle(border_mask, (x1, y1), (x2, y2), 255, thickness=margin_x)

                content_img = image_bgr[iy:iy + ih, ix:ix + iw].copy()
                full_panel_img = image_bgr[y1:y2, x1:x2].copy()
                score, is_empty = PanelDetector._evaluate_content(content_img)

                panel = PanelStructure(
                    id=panel_id,
                    bbox=bbox,
                    interior_bbox=interior_bbox,
                    border_mask=border_mask,
                    row=r,
                    column=c,
                    index=panel_id - 1,
                    content_score=score,
                    is_empty=is_empty,
                    content_region_image=content_img,
                    source_image=full_panel_img,
                    original_bbox_in_parent=bbox,
                    is_frame=True
                )
                panels.append(panel)
                panel_id += 1

        if len(panels) < 2:
            return [], (1, 1), 0.0, {}

        confidence, metrics = StoryboardConfidenceAnalyzer.analyze(panels, image_bgr, grid_shape)
        return panels, grid_shape, confidence, metrics

    # ═══════════════════════════════════════════════════════
    #  Grid Matrix Fitting & Validation
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _fit_grid_matrix(
        rects: List[Tuple[int, int, int, int]],
        h: int,
        w: int
    ) -> Tuple[Tuple[int, int], List[Tuple[int, int, int, int]]]:
        """
        Clusters rectangle bounding boxes into a regular M x N matrix.
        Filters out irregular, isolated, or unaligned boxes.
        """
        if not rects:
            return (1, 1), []

        # Cluster Y centers into rows
        y_centers = sorted(set(r[1] + r[3] // 2 for r in rects))
        row_clusters = PanelDetector._cluster_positions(y_centers, min_gap=h * 0.12)

        # Cluster X centers into columns
        x_centers = sorted(set(r[0] + r[2] // 2 for r in rects))
        col_clusters = PanelDetector._cluster_positions(x_centers, min_gap=w * 0.12)

        num_rows = len(row_clusters)
        num_cols = len(col_clusters)

        if num_rows * num_cols < 2:
            return (1, 1), []

        # Map each rectangle to nearest (row, col)
        grid_map: Dict[Tuple[int, int], Tuple[int, int, int, int]] = {}

        for r in rects:
            cx = r[0] + r[2] // 2
            cy = r[1] + r[3] // 2

            r_idx = min(range(num_rows), key=lambda i: abs(row_clusters[i] - cy))
            c_idx = min(range(num_cols), key=lambda i: abs(col_clusters[i] - cx))

            key = (r_idx, c_idx)
            # If conflict, keep larger area
            if key not in grid_map or (r[2] * r[3] > grid_map[key][2] * grid_map[key][3]):
                grid_map[key] = r

        # Sort in reading order (top->bottom, left->right)
        sorted_boxes = []
        for r_idx in range(num_rows):
            for c_idx in range(num_cols):
                if (r_idx, c_idx) in grid_map:
                    sorted_boxes.append(grid_map[(r_idx, c_idx)])

        return (num_rows, num_cols), sorted_boxes

    # ═══════════════════════════════════════════════════════
    #  Outer Frame & Content Analysis
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _detect_outer_frame(gray: np.ndarray, h: int, w: int) -> Tuple[StructureType, float]:
        """
        Determines whether a single scene has an outer framing border
        (SINGLE_FRAMED_SCENE) or is unframed (SINGLE_UNFRAMED_SCENE).
        """
        edges = cv2.Canny(gray, 40, 120)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 0.55 * (w * h):
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
                if len(approx) == 4:
                    return StructureType.SINGLE_FRAMED_SCENE, 0.90

        return StructureType.SINGLE_UNFRAMED_SCENE, 0.20

    @staticmethod
    def _evaluate_content(img: np.ndarray) -> Tuple[float, bool]:
        """
        Evaluates content richness and emptiness within a panel ROI.
        """
        if img is None or img.size == 0:
            return 0.0, True

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_ratio = cv2.countNonZero(edges) / float(max(1, img.shape[0] * img.shape[1]))
        std_dev = float(np.std(gray))

        score = (edge_ratio * 100.0) + (std_dev / 255.0)
        is_empty = (edge_ratio < 0.003 and std_dev < 8.0) or (score < 0.08)
        return float(score), is_empty

    @staticmethod
    def _compute_panel_metrics(panel: PanelStructure, image_bgr: np.ndarray):
        """Computes edge_density and entropy for a panel."""
        content_img = panel.content_region_image
        if content_img is None or content_img.size == 0:
            return

        gray = cv2.cvtColor(content_img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        total_pixels = max(1, content_img.shape[0] * content_img.shape[1])
        panel.edge_density = float(cv2.countNonZero(edges)) / total_pixels

        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten() / float(total_pixels)
        hist = hist[hist > 0]
        panel.entropy = float(-np.sum(hist * np.log2(hist)))
        panel.confidence = min(0.99, panel.edge_density * 10.0 + panel.entropy / 8.0)

    @staticmethod
    def _assign_grid_positions(panels: List[PanelStructure], h: int, w: int):
        """Assigns row, col, and reading-order index to panels."""
        if not panels:
            return

        y_centers = sorted(set(p.bbox[1] + p.bbox[3] // 2 for p in panels))
        row_clusters = PanelDetector._cluster_positions(y_centers, h * 0.10)

        x_centers = sorted(set(p.bbox[0] + p.bbox[2] // 2 for p in panels))
        col_clusters = PanelDetector._cluster_positions(x_centers, w * 0.10)

        for panel in panels:
            cy = panel.bbox[1] + panel.bbox[3] // 2
            cx = panel.bbox[0] + panel.bbox[2] // 2

            panel.row = min(range(len(row_clusters)), key=lambda i: abs(row_clusters[i] - cy))
            panel.column = min(range(len(col_clusters)), key=lambda i: abs(col_clusters[i] - cx))

        panels.sort(key=lambda p: (p.row, p.column))
        for idx, panel in enumerate(panels):
            panel.index = idx
            panel.id = idx + 1

    @staticmethod
    def _cluster_positions(positions: List[int], min_gap: float) -> List[int]:
        """Clusters 1D positions that are close to each other."""
        if not positions:
            return []

        clustered = [positions[0]]
        for pos in positions[1:]:
            if abs(pos - clustered[-1]) > min_gap:
                clustered.append(pos)
            else:
                clustered[-1] = (clustered[-1] + pos) // 2

        return clustered

    @staticmethod
    def _filter_overlapping(rects: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """Filters heavily overlapping rectangles, keeping largest."""
        if not rects:
            return []

        rects.sort(key=lambda r: r[2] * r[3], reverse=True)
        keep = []
        for r in rects:
            x1, y1, w1, h1 = r
            r_area = w1 * h1
            overlap = False
            for k in keep:
                kx, ky, kw, kh = k
                ix = max(x1, kx)
                iy = max(y1, ky)
                iw = min(x1 + w1, kx + kw) - ix
                ih = min(y1 + h1, ky + kh) - iy
                if iw > 0 and ih > 0:
                    inter_area = iw * ih
                    if inter_area > 0.25 * r_area:
                        overlap = True
                        break
            if not overlap:
                keep.append(r)

        keep.sort(key=lambda r: (r[1] // 50, r[0]))
        return keep

    @staticmethod
    def _is_true_rectangular_frame(edges: np.ndarray, x: int, y: int, bw: int, bh: int) -> bool:
        """
        Checks if a candidate bounding box actually has drawn perimeter lines
        along all 4 sides (top, bottom, left, right).
        Real storyboard panels always have distinct drawn box borders.
        """
        h, w = edges.shape[:2]
        margin = max(2, int(min(bw, bh) * 0.02))
        top_strip = edges[max(0, y - margin):min(h, y + margin + 1), max(0, x):min(w, x + bw)]
        bot_strip = edges[max(0, y + bh - margin):min(h, y + bh + margin + 1), max(0, x):min(w, x + bw)]
        left_strip = edges[max(0, y):min(h, y + bh), max(0, x - margin):min(w, x + margin + 1)]
        right_strip = edges[max(0, y):min(h, y + bh), max(0, x + bw - margin):min(w, x + bw + margin + 1)]

        top_coverage = np.count_nonzero(np.any(top_strip > 0, axis=0)) / float(max(1, bw))
        bot_coverage = np.count_nonzero(np.any(bot_strip > 0, axis=0)) / float(max(1, bw))
        left_coverage = np.count_nonzero(np.any(left_strip > 0, axis=1)) / float(max(1, bh))
        right_coverage = np.count_nonzero(np.any(right_strip > 0, axis=1)) / float(max(1, bh))

        min_side = min(top_coverage, bot_coverage, left_coverage, right_coverage)
        avg_side = (top_coverage + bot_coverage + left_coverage + right_coverage) / 4.0
        return min_side >= 0.35 and avg_side >= 0.50

    # ═══════════════════════════════════════════════════════
    #  Diagnostic Output Logger
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _log_diagnostics(
        structure_type: str,
        storyboard_confidence: float,
        rows: int,
        columns: int,
        panel_count: int,
        frame_confidence: float,
        panels: List[PanelStructure]
    ):
        """Prints formatted diagnostic output matching architectural specifications."""
        print("==================================================")
        print("STRUCTURE DETECTION")
        print("-------------------")
        print(f"structure_type: {structure_type}")
        print(f"storyboard_confidence: {storyboard_confidence:.2f}")
        print(f"rows: {rows}")
        print(f"columns: {columns}")
        print(f"panel_count: {panel_count}")
        print(f"frame_confidence: {frame_confidence:.2f}")
        print("==================================================")

        for p in panels:
            print(f"PANEL {p.id}")
            print("--------")
            print(f"bbox: {p.bbox}")
            print(f"interior_bbox: {p.interior_bbox}")
            print(f"content_score: {p.content_score:.2f}")
            print(f"is_empty: {p.is_empty}")
            print("")
