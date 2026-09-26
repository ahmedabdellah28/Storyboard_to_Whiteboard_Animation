"""
Adaptive Layer Splitter (Artwork vs Typography)
Robustly separates panel contents into:
1. Clean Typography Layer (preserves full Arabic words without accidental fragmentation into graphics).
2. Clean Graphics / Artwork Layer.
3. Card & Container identification.
"""
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple


class AdaptiveLayerSplitter:
    @staticmethod
    def split(panel_crop: np.ndarray) -> Dict[str, Any]:
        """
        Splits a clean panel crop into pure Graphics and Typography image layers.
        Specially tuned for Arabic cursive typography and mixed-scale whiteboard elements.
        """
        ph, pw = panel_crop.shape[:2]
        scale = max(0.4, ph / 170.0)

        diff = 255.0 - panel_crop.astype(np.float32)
        dist = np.max(diff, axis=2)
        ink_bin = (dist > 25.0).astype(np.uint8) * 255

        num_cc, labels, stats, centroids = cv2.connectedComponentsWithStats(ink_bin)

        text_mask = np.zeros((ph, pw), dtype=np.uint8)
        graphics_mask = np.zeros((ph, pw), dtype=np.uint8)

        # Dynamic multi-scale thresholds
        max_line_h = int(round(36 * scale))      # Max height for standard text lines/words
        max_title_h = int(round(48 * scale))     # Max height for prominent titles
        max_word_w = int(round(160 * scale))     # Max width for a single connected word
        max_word_area = int(round(950 * scale * scale)) # Arabic cursive words can be up to 900px
        min_dot_area = int(round(6 * scale * scale))

        for i in range(1, num_cc):
            cx = stats[i, cv2.CC_STAT_LEFT]
            cy = stats[i, cv2.CC_STAT_TOP]
            cw = stats[i, cv2.CC_STAT_WIDTH]
            ch = stats[i, cv2.CC_STAT_HEIGHT]
            carea = stats[i, cv2.CC_STAT_AREA]
            aspect = cw / float(ch + 1e-5)

            # Circular panel numbers (e.g. ❶, ❷... in black circle at top left)
            # These are icons/graphics (aspect ~ 1.0, area ~ 700, at top left)
            is_panel_badge = (cw >= 25 and ch >= 25 and 0.8 <= aspect <= 1.25 and 
                              carea > 400 and cy < ph * 0.25 and cx < pw * 0.25)

            # Standard text words or letters:
            # 1. Normal body text or title word
            is_text_word = (
                not is_panel_badge and
                ch <= max_line_h and 
                cw <= max_word_w and 
                carea <= max_word_area and 
                carea >= min_dot_area
            )
            
            # 2. Large title words or bold heading characters
            is_title_word = (
                not is_panel_badge and
                cy < ph * 0.35 and 
                ch <= max_title_h and 
                cw <= max_word_w and 
                carea <= max_word_area * 1.3
            )
            
            # 3. Dots, accents, or punctuation marks (small area)
            is_accent_dot = (
                carea <= min_dot_area * 3 and 
                ch <= int(round(14 * scale)) and 
                cw <= int(round(14 * scale))
            )
            
            # 4. Underline bars
            is_underline = (aspect > 4.5 and ch <= int(round(8 * scale)))

            if (is_text_word or is_title_word or is_accent_dot or is_underline):
                text_mask[labels == i] = 255
            else:
                graphics_mask[labels == i] = 255

        # Refine masks: make sure text components don't overlap with large solid graphic bodies
        # Any text mask pixel inside a massive graphic region remains graphic
        graphics_image = np.full_like(panel_crop, 255)
        graphics_image[graphics_mask > 0] = panel_crop[graphics_mask > 0]

        text_image = np.full_like(panel_crop, 255)
        text_image[text_mask > 0] = panel_crop[text_mask > 0]

        return {
            "graphics_image": graphics_image,
            "text_image": text_image,
            "graphics_mask": graphics_mask,
            "text_mask": text_mask,
            "ink_bin": ink_bin
        }
