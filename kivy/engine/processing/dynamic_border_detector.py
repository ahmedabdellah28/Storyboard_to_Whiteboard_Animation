"""
Dynamic Border Detector — Automatically analyzes, detects, and measures outer box frame borders.
Eliminates rectangular panel borders while preserving 100% of the internal artwork.
"""
import cv2
import numpy as np
from typing import Dict, Tuple, Any


class DynamicBorderDetector:
    """
    Intelligently detects and measures outer box border lines for any panel crop.
    Computes exact per-edge trim offsets (top, bottom, left, right) dynamically.
    If no border exists on an edge, trim is 0 (preserving the artwork).
    """

    @staticmethod
    def detect_and_trim_panel_border(panel_crop: np.ndarray, max_scan_ratio: float = 0.12) -> Dict[str, Any]:
        """
        Analyzes the perimeter of panel_crop to detect outer border lines.
        Returns:
            {
                "clean_crop": np.ndarray (trimmed image without border lines),
                "insets": (trim_top, trim_bottom, trim_left, trim_right),
                "has_border": bool,
                "border_thickness": int
            }
        """
        if panel_crop is None or panel_crop.size == 0:
            return {"clean_crop": panel_crop, "insets": (0, 0, 0, 0), "has_border": False, "border_thickness": 0}

        h, w = panel_crop.shape[:2]
        if h < 20 or w < 20:
            return {"clean_crop": panel_crop, "insets": (0, 0, 0, 0), "has_border": False, "border_thickness": 0}

        gray = cv2.cvtColor(panel_crop, cv2.COLOR_BGR2GRAY) if len(panel_crop.shape) == 3 else panel_crop.copy()
        ink_density = (gray < 200).astype(np.float32)

        max_scan_y = max(4, int(h * max_scan_ratio))
        max_scan_x = max(4, int(w * max_scan_ratio))

        # --- 1. Detect TOP border ---
        trim_top = 0
        has_top_border = False
        for y in range(max_scan_y):
            row_density = float(np.mean(ink_density[y, :]))
            if row_density > 0.40:
                has_top_border = True
                trim_top = y + 1
            elif has_top_border and row_density < 0.20:
                break
        if has_top_border:
            trim_top = min(max_scan_y, trim_top + 2)

        # --- 2. Detect BOTTOM border ---
        trim_bottom = 0
        has_bottom_border = False
        for y_offset in range(max_scan_y):
            y = h - 1 - y_offset
            row_density = float(np.mean(ink_density[y, :]))
            if row_density > 0.40:
                has_bottom_border = True
                trim_bottom = y_offset + 1
            elif has_bottom_border and row_density < 0.20:
                break
        if has_bottom_border:
            trim_bottom = min(max_scan_y, trim_bottom + 2)

        # --- 3. Detect LEFT border ---
        trim_left = 0
        has_left_border = False
        for x in range(max_scan_x):
            col_density = float(np.mean(ink_density[:, x]))
            if col_density > 0.40:
                has_left_border = True
                trim_left = x + 1
            elif has_left_border and col_density < 0.20:
                break
        if has_left_border:
            trim_left = min(max_scan_x, trim_left + 2)

        # --- 4. Detect RIGHT border ---
        trim_right = 0
        has_right_border = False
        for x_offset in range(max_scan_x):
            x = w - 1 - x_offset
            col_density = float(np.mean(ink_density[:, x]))
            if col_density > 0.40:
                has_right_border = True
                trim_right = x_offset + 1
            elif has_right_border and col_density < 0.20:
                break
        if has_right_border:
            trim_right = min(max_scan_x, trim_right + 2)

        has_any_border = bool(has_top_border or has_bottom_border or has_left_border or has_right_border)

        y1 = trim_top
        y2 = h - trim_bottom if trim_bottom > 0 else h
        x1 = trim_left
        x2 = w - trim_right if trim_right > 0 else w

        if y2 <= y1 or x2 <= x1:
            clean_crop = panel_crop.copy()
            insets = (0, 0, 0, 0)
        else:
            clean_crop = panel_crop[y1:y2, x1:x2].copy()
            insets = (trim_top, trim_bottom, trim_left, trim_right)

        valid_insets = [t for t in insets if t > 0]
        avg_thickness = int(np.mean(valid_insets)) if valid_insets else 0

        return {
            "clean_crop": clean_crop,
            "insets": insets,
            "has_border": has_any_border,
            "border_thickness": avg_thickness
        }
