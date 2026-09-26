"""
Layer Splitter (Graphics vs Typography)
Separates panel crop into pure Graphics and Typography image layers.
"""
import cv2
import numpy as np
from typing import Dict, Any


class MethodALayerSplitter:
    @staticmethod
    def split(panel_crop: np.ndarray) -> Dict[str, Any]:
        ph, pw = panel_crop.shape[:2]

        # Multi-scale normalization relative to baseline 170px panel height
        scale = max(0.4, ph / 170.0)

        diff = 255.0 - panel_crop.astype(np.float32)
        dist = np.max(diff, axis=2)
        ink_bin = (dist > 26.0).astype(np.uint8) * 255

        num_cc, labels, stats, _ = cv2.connectedComponentsWithStats(ink_bin)

        text_mask = np.zeros((ph, pw), dtype=np.uint8)
        graphics_mask = np.zeros((ph, pw), dtype=np.uint8)

        # Scaled thresholds matching Method A benchmark
        max_ch = int(round(28 * scale))
        max_cw = int(round(85 * scale))
        max_carea = int(round(260 * scale * scale))
        min_dot = int(round(20 * scale * scale))
        max_uh = int(round(7 * scale))

        for i in range(1, num_cc):
            cw = stats[i, cv2.CC_STAT_WIDTH]
            ch = stats[i, cv2.CC_STAT_HEIGHT]
            carea = stats[i, cv2.CC_STAT_AREA]
            aspect = cw / float(ch + 1e-5)

            if (ch <= max_ch and cw <= max_cw and carea < max_carea) or carea <= min_dot or (aspect > 4.5 and ch <= max_uh):
                text_mask[labels == i] = 255
            else:
                graphics_mask[labels == i] = 255

        graphics_image = np.full_like(panel_crop, 255)
        graphics_image[graphics_mask > 0] = panel_crop[graphics_mask > 0]

        text_image = np.full_like(panel_crop, 255)
        text_image[text_mask > 0] = panel_crop[text_mask > 0]

        return {
            "graphics_image": graphics_image,
            "text_image": text_image,
            "graphics_mask": graphics_mask,
            "text_mask": text_mask
        }
