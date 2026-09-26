"""
Module 1: Dynamic Panel Extractor & Border Stripper
File: experiments/modular_pipeline/m1_panel_extractor.py

Responsibilities:
1. Discovers all panels dynamically from the master image.
2. Sorts panels into standard reading order.
3. Strips the outer border frames to yield pristine interior crops.
"""
import cv2
import numpy as np
from typing import List, Dict, Any

class DynamicPanelExtractor:
    @staticmethod
    def extract_panels(image_bgr: np.ndarray, border_inset: int = 4) -> List[Dict[str, Any]]:
        """
        Dynamically detects panel boxes and extracts border-free interior crops.
        """
        ih, iw = image_bgr.shape[:2]
        
        # Multi-channel ink distance from white
        diff = 255.0 - image_bgr.astype(np.float32)
        dist_from_white = np.max(diff, axis=2)
        ink_bin = (dist_from_white > 26.0).astype(np.uint8) * 255
        
        num_cc, cc_labels, cc_stats, _ = cv2.connectedComponentsWithStats(ink_bin)
        
        raw_borders = []
        for i in range(1, num_cc):
            cw = cc_stats[i, cv2.CC_STAT_WIDTH]
            ch = cc_stats[i, cv2.CC_STAT_HEIGHT]
            cx = cc_stats[i, cv2.CC_STAT_LEFT]
            cy = cc_stats[i, cv2.CC_STAT_TOP]
            carea = cc_stats[i, cv2.CC_STAT_AREA]
            
            # Panel outer border criterion: wide & tall outer rounded rectangle
            if (iw * 0.18 <= cw <= iw * 0.35) and (ih * 0.22 <= ch <= ih * 0.40):
                density = carea / float(cw * ch + 1e-5)
                if density < 0.15:
                    raw_borders.append({
                        "comp_id": i,
                        "bbox": (cx, cy, cw, ch),
                        "cx": cx + cw / 2.0,
                        "cy": cy + ch / 2.0,
                        "area": cw * ch
                    })
        
        # Eliminate nested inner boxes: if box A is completely inside box B, drop box A
        borders = []
        for a in raw_borders:
            ax, ay, aw, ah = a["bbox"]
            is_nested = False
            for b in raw_borders:
                if a == b:
                    continue
                bx, by, bw, bh = b["bbox"]
                if bx <= ax and by <= ay and (bx + bw) >= (ax + aw) and (by + bh) >= (ay + ah):
                    # Box A is inside Box B!
                    is_nested = True
                    break
            if not is_nested:
                borders.append(a)
        
        # Sort panels cleanly into 3 rows (Top, Middle, Bottom) and 4 columns (Left-to-Right)
        if borders:
            row_height = ih / 3.0
            borders.sort(key=lambda b: (int(b["cy"] / row_height), b["cx"]))
        else:
            borders = [{"comp_id": 0, "bbox": (0, 0, iw, ih), "cx": iw/2.0, "cy": ih/2.0}]
        
        panels = []
        for idx, b in enumerate(borders):
            p_id = idx + 1
            bx, by, bw, bh = b["bbox"]
            
            # Safe interior coordinates with border stripped
            ix = max(0, bx + border_inset)
            iy = max(0, by + border_inset)
            iw_p = max(10, min(iw - ix, bw - 2 * border_inset))
            ih_p = max(10, min(ih - iy, bh - 2 * border_inset))
            
            interior_crop = image_bgr[iy:iy+ih_p, ix:ix+iw_p].copy()
            
            panels.append({
                "id": p_id,
                "outer_bbox": (bx, by, bw, bh),
                "interior_bbox": (ix, iy, iw_p, ih_p),
                "crop": interior_crop,
                "center": (bx + bw / 2.0, by + bh / 2.0),
                "width": iw_p,
                "height": ih_p
            })
            
        return panels
