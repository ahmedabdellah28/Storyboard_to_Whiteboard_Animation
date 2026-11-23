"""Computer Vision-Driven Drawing Demand and Stroke Complexity Calculator.

Computes contour complexity, edge density, and visual weight to return
estimated_demand, minimum_demand, and maximum_demand for the deterministic scheduler.
"""

from __future__ import annotations

import cv2
import numpy as np
from typing import Dict, Any
from core.vision.visual_manifest import DrawDemand, ImportanceRole


class DrawingComplexityEstimator:
    """Estimates realistic hand-drawn rendering demands using contour topology and edge analysis."""

    @staticmethod
    def estimate_demand(
        crop_bgr: np.ndarray,
        mask: np.ndarray,
        importance: ImportanceRole = ImportanceRole.HERO,
        anim_type: str = "outside_in_pen"
    ) -> DrawDemand:
        """Calculates CV-driven drawing demand range.

        Args:
            crop_bgr: BGR visual image crop.
            mask: Alpha or foreground binary mask (0-255).
            importance: Semantic importance role.
            anim_type: Animation mode (e.g., outside_in_pen, slide_down).

        Returns:
            DrawDemand object with estimated, min, and max durations in seconds.
        """
        if crop_bgr.size == 0 or np.count_nonzero(mask) == 0:
            return DrawDemand(estimated=1.0, min=0.8, max=1.4)

        # 1. Edge & Contour Analysis
        gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 60, 180)
        edges_in_fg = cv2.bitwise_and(edges, edges, mask=mask)
        edge_pixel_count = int(np.count_nonzero(edges_in_fg))

        # Find external and internal contours
        contours, hierarchy = cv2.findContours(
            mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        total_contour_len = sum(cv2.arcLength(c, True) for c in contours)
        contour_count = len(contours)

        fg_area = int(np.count_nonzero(mask))
        edge_density = edge_pixel_count / float(max(1, fg_area))

        # 2. Base duration from animation type
        if anim_type in ["slide_down", "slide_up", "instant_reveal", "jelly_pop"]:
            # Entrance animations need less demand time
            base = 1.0 + min(0.6, edge_density * 2.0)
            d_min = max(0.6, round(base * 0.7, 2))
            d_est = max(0.8, round(base, 2))
            d_max = max(1.0, round(base * 1.3, 2))
            return DrawDemand(estimated=d_est, min=d_min, max=d_max)

        # 3. For pen-drawn (outside_in_pen):
        # Base scale calibrated around typical whiteboard drawing speed (1.4s to 2.8s)
        # Scaled by contour complexity and edge density
        complexity_score = (
            (total_contour_len / 1200.0) * 0.4 +
            (edge_pixel_count / 3000.0) * 0.4 +
            (contour_count / 15.0) * 0.2
        )

        if importance == ImportanceRole.HERO:
            target_est = 1.6 + min(1.2, complexity_score * 0.7)
            d_min = max(1.2, round(target_est * 0.75, 2))
            d_est = round(min(3.0, target_est), 2)
            d_max = round(min(3.6, target_est * 1.35), 2)
        elif importance == ImportanceRole.SUPPORT:
            target_est = 1.3 + min(0.9, complexity_score * 0.5)
            d_min = max(0.9, round(target_est * 0.75, 2))
            d_est = round(min(2.4, target_est), 2)
            d_max = round(min(2.8, target_est * 1.3), 2)
        else:
            target_est = 1.0 + min(0.6, complexity_score * 0.3)
            d_min = max(0.7, round(target_est * 0.75, 2))
            d_est = round(min(1.8, target_est), 2)
            d_max = round(min(2.2, target_est * 1.3), 2)

        return DrawDemand(estimated=d_est, min=d_min, max=d_max)
