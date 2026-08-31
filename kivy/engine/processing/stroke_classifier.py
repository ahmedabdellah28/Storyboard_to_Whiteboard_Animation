import cv2
import numpy as np
from typing import List, Tuple, Optional
from ..core.stroke import Stroke, StrokeType
from ..core.scene import SceneConfig


class StrokeClassifier:
    @staticmethod
    def classify(
        strokes: List[Stroke],
        image_bgr: np.ndarray,
        quantized_bgr: Optional[np.ndarray],
        config: SceneConfig
    ) -> List[Stroke]:
        """
        Classifies raw strokes into 4 distinct geometric categories:
        - OUTER_OUTLINE
        - INTERNAL_DETAIL
        - COLOR_BOUNDARY
        - MICRO_DETAIL
        Filters strokes according to detail_level.
        """
        if not strokes:
            return []

        h, w = image_bgr.shape[:2]
        total_scene_diag = float(np.sqrt(h**2 + w**2))

        # Compute stroke statistics
        lengths = np.array([s.length for s in strokes], dtype=np.float64)
        median_len = float(np.median(lengths)) if len(lengths) > 0 else 20.0
        max_len = float(np.max(lengths)) if len(lengths) > 0 else 100.0

        # Local edge density map for micro-texture detection
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        density_map = cv2.boxFilter(edges.astype(np.float32) / 255.0, -1, (25, 25))

        classified: List[Stroke] = []

        for s in strokes:
            pts = s.points
            if len(pts) < 2:
                continue

            # Feature 1: Geometric size & enclosed area
            bbox_w, bbox_h = s.bbox[2], s.bbox[3]
            bbox_area = bbox_w * bbox_h
            is_large_loop = s.is_closed and (s.length > 0.15 * total_scene_diag or bbox_area > 0.04 * (w * h))
            is_long_contour = s.length > max(median_len * 2.5, 0.20 * total_scene_diag)

            # Feature 2: Color boundary check
            is_color_boundary = False
            if quantized_bgr is not None and len(pts) >= 3:
                is_color_boundary = StrokeClassifier._is_color_boundary(pts, quantized_bgr, h, w)

            # Feature 3: Local texture / micro detail check
            cx = int(np.clip(s.center[0], 0, w - 1))
            cy = int(np.clip(s.center[1], 0, h - 1))
            local_density = float(density_map[cy, cx])
            is_short = s.length < max(12.0, median_len * 0.45)

            # Feature 0: Frame Stroke check (outer canvas/panel borders)
            is_frame = StrokeClassifier._is_frame_stroke(s, w, h)

            # Classification rules
            if is_frame:
                s.stroke_type = StrokeType.FRAME_STROKE
                s.is_frame = True
                s.width = 2.0
                s.priority = 0
            elif is_large_loop or is_long_contour:
                s.stroke_type = StrokeType.OUTER_OUTLINE
                s.width = 2.4
                s.priority = 10
            elif is_color_boundary:
                s.stroke_type = StrokeType.COLOR_BOUNDARY
                s.width = 1.6
                s.priority = 6
            elif is_short and local_density > 0.35:
                s.stroke_type = StrokeType.MICRO_DETAIL
                s.width = 1.2
                s.priority = 2
            else:
                s.stroke_type = StrokeType.INTERNAL_DETAIL
                s.width = 1.8
                s.priority = 8

            # Zero Detail Loss: Preserve all strokes across all detail levels
            if config.detail_level == "LOW":
                if s.stroke_type == StrokeType.MICRO_DETAIL:
                    s.width = 1.0
                    s.priority = 1
            classified.append(s)

        return classified

    @staticmethod
    def _is_color_boundary(points: np.ndarray, quantized_bgr: np.ndarray, h: int, w: int) -> bool:
        """
        Samples color on both sides of normal vectors along the stroke.
        Returns True if more than 50% of sampled normals cross distinct color clusters.
        """
        sample_indices = np.linspace(0, len(points) - 2, min(8, len(points) - 1), dtype=int)
        boundary_crossings = 0
        valid_samples = 0

        for idx in sample_indices:
            p1 = points[idx]
            p2 = points[idx + 1]
            vec = p2 - p1
            norm = np.linalg.norm(vec)
            if norm < 1e-5:
                continue

            # Perpendicular unit normal vector
            normal = np.array([-vec[1], vec[0]]) / norm
            offset = 3.0  # 3 pixels perpendicular offset

            left_pt = p1 + normal * offset
            right_pt = p1 - normal * offset

            lx, ly = int(np.clip(left_pt[0], 0, w - 1)), int(np.clip(left_pt[1], 0, h - 1))
            rx, ry = int(np.clip(right_pt[0], 0, w - 1)), int(np.clip(right_pt[1], 0, h - 1))

            c_left = quantized_bgr[ly, lx].astype(np.float32)
            c_right = quantized_bgr[ry, rx].astype(np.float32)

            color_diff = float(np.linalg.norm(c_left - c_right))
            if color_diff > 25.0:  # Distinct color difference
                boundary_crossings += 1
            valid_samples += 1

        if valid_samples == 0:
            return False
        return (boundary_crossings / valid_samples) >= 0.50

    @staticmethod
    def _is_frame_stroke(s: Stroke, w: int, h: int) -> bool:
        """
        Determines if a stroke represents an outer structural frame/border.
        Structural frame lines are excluded from character drawing animations.
        """
        bx, by, bw, bh = s.bbox
        # Full enclosing border rectangle
        if bw >= 0.85 * w and bh >= 0.85 * h:
            return True
        # Top or bottom border strip
        if bw >= 0.80 * w and bh <= 20 and (by <= 24 or by + bh >= h - 24):
            return True
        # Left or right border strip
        if bh >= 0.80 * h and bw <= 20 and (bx <= 24 or bx + bw >= w - 24):
            return True
        return False
