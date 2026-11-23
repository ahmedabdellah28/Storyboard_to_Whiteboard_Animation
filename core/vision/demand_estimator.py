"""Normalized Computer Vision Drawing Demand Estimator.

Computes mathematically normalized metrics across all visual assets:
- Pixel Mass: ratio of colored stroke pixels to bounding box area.
- Contour Complexity: normalized perimeter relative to theoretical bounds.
- Edge Density: high-frequency interior detail using Canny/Sobel filters.
- Stroke Topology: count of connected strokes and components.
- Canvas Scale: relative footprint on the target canvas.

Produces NormalizedDemandMetrics and maps to policy-driven durations without magic numbers.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple
import cv2
import numpy as np

from core.contracts.visual_manifest import NormalizedDemandMetrics
from core.contracts.render_policy import RenderPolicy, RoleSpeedLimit


class DemandEstimator:
    """Computes normalized CV metrics and maps them to policy duration windows."""

    def __init__(self, policy: Optional[RenderPolicy] = None) -> None:
        self.policy = policy or RenderPolicy()

    def compute_metrics(
        self,
        crop_bgr: np.ndarray,
        mask: Optional[np.ndarray] = None,
        canvas_dimensions: Tuple[int, int] = (1920, 1080),
    ) -> NormalizedDemandMetrics:
        """Calculates normalized visual demand metrics for an asset crop.

        Args:
            crop_bgr: BGR image crop of the asset.
            mask: Optional binary mask (0-255). If None, extracted from alpha or non-white pixels.
            canvas_dimensions: (width, height) of the canvas for scale normalization.

        Returns:
            NormalizedDemandMetrics instance with scores in [0.0, 1.0].
        """
        h, w = crop_bgr.shape[:2]
        if h == 0 or w == 0:
            return NormalizedDemandMetrics(
                normalized_pixel_mass=0.1,
                normalized_contour_length=0.1,
                normalized_edge_complexity=0.1,
                stroke_count_estimate=1,
                aspect_ratio=1.0,
                raw_demand_score=0.1,
            )

        bbox_area = float(w * h)
        canvas_w, canvas_h = canvas_dimensions
        canvas_area = float(canvas_w * canvas_h)

        # 1. Mask extraction if not provided
        if mask is None:
            if crop_bgr.shape[2] == 4:
                mask = crop_bgr[:, :, 3]
            else:
                gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
                # Treat non-pure white (>245) as foreground
                _, mask = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)

        fg_pixels = int(np.count_nonzero(mask))
        if fg_pixels == 0:
            return NormalizedDemandMetrics(
                normalized_pixel_mass=0.05,
                normalized_contour_length=0.05,
                normalized_edge_complexity=0.05,
                stroke_count_estimate=1,
                aspect_ratio=float(w) / float(max(1, h)),
                raw_demand_score=0.05,
            )

        # A. Normalized Pixel Mass M_norm in [0, 1]
        m_norm = min(1.0, fg_pixels / max(1.0, bbox_area))

        # B. Edge Detection in Foreground (E_norm in [0, 1])
        gray_crop = cv2.cvtColor(crop_bgr[:, :, :3], cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_crop, 50, 150)
        edges_in_fg = cv2.bitwise_and(edges, edges, mask=mask)
        edge_pixel_count = int(np.count_nonzero(edges_in_fg))
        e_norm = min(1.0, edge_pixel_count / max(1.0, float(fg_pixels)))

        # C. Contour Analysis (C_norm in [0, 1])
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        total_contour_len = sum(cv2.arcLength(c, True) for c in contours)
        contour_count = max(1, len(contours))
        
        # Max theoretical perimeter: outer perimeter plus inner stroke complexity
        max_perimeter_ref = 2.0 * (w + h) * math.sqrt(contour_count)
        c_norm = min(1.0, total_contour_len / max(1.0, max_perimeter_ref))

        # D. Stroke Count Estimate (S_norm in [0, 1])
        # Whiteboard drawings typically have 5 to 60 distinct stroke clusters
        s_norm = min(1.0, contour_count / 40.0)

        # E. Asset Area Footprint relative to standard focal zone (A_norm in [0, 1])
        # Focal zone ~ 25% of canvas area
        a_norm = min(1.0, bbox_area / (canvas_area * 0.25))

        # F. Weighted Raw Demand Score using policy weights
        pw = self.policy.demand_weights
        raw_score = (
            pw.pixel_mass_weight * m_norm +
            pw.contour_weight * c_norm +
            pw.edge_weight * e_norm +
            pw.stroke_weight * s_norm +
            pw.area_weight * a_norm
        )
        clamped_raw_score = round(max(0.05, min(1.0, float(raw_score))), 3)

        return NormalizedDemandMetrics(
            normalized_pixel_mass=round(m_norm, 3),
            normalized_contour_length=round(c_norm, 3),
            normalized_edge_complexity=round(e_norm, 3),
            stroke_count_estimate=contour_count,
            aspect_ratio=round(float(w) / float(max(1, h)), 3),
            raw_demand_score=clamped_raw_score,
        )

    def calculate_duration(
        self,
        metrics: NormalizedDemandMetrics,
        role_limit: RoleSpeedLimit,
    ) -> Tuple[float, float, float]:
        """Calculates (t_min, t_est, t_max) in seconds for an asset given role limits.

        Returns:
            Tuple of (min_duration_s, estimated_duration_s, max_duration_s)
        """
        score = metrics.raw_demand_score
        t_base = role_limit.min_duration_s
        t_ceiling = role_limit.max_duration_s

        # Linear mapping between min_duration and max_duration via demand score
        t_est = round(t_base + score * (t_ceiling - t_base), 2)
        t_min = round(max(0.6, t_est / role_limit.max_speedup_factor), 2)
        t_max = round(min(t_ceiling * 1.2, t_est * 1.3), 2)

        return t_min, t_est, t_max
