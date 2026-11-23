"""Professional Background Remover with Internal White Preservation.

Unlike naive luminance thresholding (gray < 240) which destroys white clothing,
turbans, weapons, eyes, teeth, and highlights, this module uses edge-connected
exterior flood-fill and contour topology to remove ONLY the exterior background.
"""

from __future__ import annotations

import cv2
import numpy as np
from typing import Tuple, Dict, Any


class BackgroundRemover:
    """Removes exterior storyboard backgrounds while preserving internal white regions."""

    @staticmethod
    def extract_clean_rgba(
        crop_bgr: np.ndarray,
        bg_color_tol: int = 18,
        feather_radius: int = 1,
        pad: int = 4
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Extracts clean RGBA with internal white preservation.

        Args:
            crop_bgr: Input BGR image crop.
            bg_color_tol: Color distance tolerance from pure white background (0-255).
            feather_radius: Radius for edge alpha smoothing.
            pad: Outer border padding added before flood-fill to ensure edge connectivity.

        Returns:
            Tuple of (bgra_image, stats_dict)
        """
        h, w = crop_bgr.shape[:2]
        if h == 0 or w == 0:
            return np.zeros((0, 0, 4), dtype=np.uint8), {"status": "empty"}

        # 1. Add white border so background connects completely around all 4 edges
        padded = cv2.copyMakeBorder(
            crop_bgr, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255, 255, 255]
        )
        p_h, p_w = padded.shape[:2]

        # 2. Flood-fill exterior background starting from the border (0, 0)
        # FloodFill mask must be (h+2, w+2)
        flood_mask = np.zeros((p_h + 2, p_w + 2), dtype=np.uint8)
        
        # We fill from all four corners to guarantee complete exterior capture
        corners = [(0, 0), (0, p_w - 1), (p_h - 1, 0), (p_h - 1, p_w - 1)]
        for cy, cx in corners:
            if flood_mask[cy + 1, cx + 1] == 0:
                cv2.floodFill(
                    padded,
                    flood_mask,
                    (cx, cy),
                    newVal=[0, 0, 0],
                    loDiff=(bg_color_tol, bg_color_tol, bg_color_tol),
                    upDiff=(bg_color_tol, bg_color_tol, bg_color_tol),
                    flags=cv2.FLOODFILL_FIXED_RANGE
                )

        # 3. Extract the foreground mask: flood_mask == 1 is the exterior background
        exterior_bg_mask = flood_mask[1:p_h + 1, 1:p_w + 1]
        raw_fg_mask = (exterior_bg_mask == 0).astype(np.uint8)[pad:pad + h, pad:pad + w] * 255

        # 4. Fill any accidental pinhole noise inside the foreground
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        clean_fg_mask = cv2.morphologyEx(raw_fg_mask, cv2.MORPH_CLOSE, kernel)

        # 5. Calculate internal white pixels preserved vs naive thresholding
        gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        naive_mask = (gray < 240).astype(np.uint8) * 255
        naive_count = int(np.count_nonzero(naive_mask))
        smart_count = int(np.count_nonzero(clean_fg_mask))
        preserved_whites = max(0, smart_count - naive_count)

        # 6. Subtle edge feathering for smooth antialiasing
        if feather_radius > 0:
            smoothed_alpha = cv2.GaussianBlur(
                clean_fg_mask.astype(np.float32), (feather_radius * 2 + 1, feather_radius * 2 + 1), 0.5
            )
            alpha_channel = np.clip(smoothed_alpha, 0, 255).astype(np.uint8)
        else:
            alpha_channel = clean_fg_mask

        # 7. Stack into BGRA
        bgra = np.dstack([crop_bgr, alpha_channel])

        stats = {
            "width": w,
            "height": h,
            "foreground_pixels": smart_count,
            "preserved_internal_whites": preserved_whites,
            "naive_foreground_pixels": naive_count,
            "coverage_ratio": round(smart_count / float(max(1, w * h)), 4)
        }

        return bgra, stats
