"""
Container & Card Detector + Weak Bridge Splitter
Handles:
1. Weak bridge / valley decomposition (isolates touching characters from adjacent cards/boxes).
2. Detection of colored text cards and container boxes.
3. Extraction of internal text layers inside colored containers.
"""
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional


class ContainerDetector:
    @staticmethod
    def split_weak_bridges(comp_mask: np.ndarray, min_sub_area: int = 500) -> List[np.ndarray]:
        """
        Detects if a large component contains multiple distinct entities connected by
        a weak bridge (e.g. character touching an adjacent text box/card at the bottom).
        Splits at the minimum neck cut and returns individual entity masks.
        """
        ys, xs = np.where(comp_mask > 0)
        if len(xs) == 0:
            return [comp_mask]
            
        x1, x2 = int(xs.min()), int(xs.max())
        y1, y2 = int(ys.min()), int(ys.max())
        cw = x2 - x1 + 1
        ch = y2 - y1 + 1
        
        # Only inspect components that are wide enough to contain multiple distinct entities
        if cw < 60 or ch < 40:
            return [comp_mask]
            
        sub_crop = comp_mask[y1:y2+1, x1:x2+1]
        col_counts = np.sum(sub_crop > 0, axis=0) # length cw
        
        # We search inside a margin to ensure each half is substantial
        min_margin = int(cw * 0.20)
        search_range = range(min_margin, cw - min_margin)
        
        best_cut_x = -1
        min_cut_val = float('inf')
        
        for cx in search_range:
            w_val = np.mean(col_counts[max(0, cx-2):min(cw, cx+3)])
            left_max = np.max(col_counts[:cx])
            right_max = np.max(col_counts[cx:])
            
            # A bridge exists when the neck has low thickness compared to both left and right bodies
            if left_max > 0.40 * ch and right_max > 0.40 * ch:
                ratio = w_val / float(min(left_max, right_max))
                # Check for an actual open valley above or below
                # In panel 1, col_counts at bridge is ~10 while ch is ~126 (ratio < 0.25)
                if ratio < 0.25 and w_val < min_cut_val:
                    min_cut_val = w_val
                    best_cut_x = cx
                    
        if best_cut_x > 0:
            global_cut_x = x1 + best_cut_x
            mask_left = comp_mask.copy()
            mask_left[:, global_cut_x:] = 0
            
            mask_right = comp_mask.copy()
            mask_right[:, :global_cut_x] = 0
            
            area_l = cv2.countNonZero(mask_left)
            area_r = cv2.countNonZero(mask_right)
            
            if area_l >= min_sub_area and area_r >= min_sub_area:
                # Recursively inspect both halves
                return (ContainerDetector.split_weak_bridges(mask_left, min_sub_area) +
                        ContainerDetector.split_weak_bridges(mask_right, min_sub_area))
                
        return [comp_mask]

    @staticmethod
    def inspect_container_card(crop_bgr: np.ndarray, mask: np.ndarray) -> Dict[str, Any]:
        """
        Analyzes a candidate graphic entity to determine if it is a Text Box / Info Card.
        Features checked:
        - Rectangular / rounded-rectangular geometry
        - Uniform background color fill (e.g. light blue, gray, cream)
        - Internal high-contrast text or numbers (e.g. 'أقل من', '70', 'في اختبار الذكاء')
        """
        ys, xs = np.where(mask > 0)
        if len(xs) == 0:
            return {"is_card": False}
            
        x1, x2 = int(xs.min()), int(xs.max())
        y1, y2 = int(ys.min()), int(ys.max())
        w = x2 - x1 + 1
        h = y2 - y1 + 1
        area = cv2.countNonZero(mask)
        
        # Minimum card dimensions
        if w < 40 or h < 35:
            return {"is_card": False}
            
        # Rectangular extent / solidity: A card fills > 70% of its bounding box
        bbox_area = w * h
        solidity = area / float(bbox_area)
        aspect = w / float(h + 1e-5)
        
        if solidity < 0.65 or aspect < 0.45 or aspect > 2.5:
            return {"is_card": False}
            
        card_crop = crop_bgr[y1:y2+1, x1:x2+1]
        card_mask = mask[y1:y2+1, x1:x2+1]
        
        # Background color analysis
        gray_card = cv2.cvtColor(card_crop, cv2.COLOR_BGR2GRAY)
        valid_pixels = gray_card[card_mask > 0]
        if len(valid_pixels) == 0:
            return {"is_card": False}
            
        median_gray = np.median(valid_pixels)
        
        # Contrast with background: find internal text/markings
        # Any pixel inside the card differing by > 25 gray levels or strong color contrast
        gray_diff = np.abs(gray_card.astype(float) - median_gray)
        internal_ink = ((gray_diff > 25) & (card_mask > 0)).astype(np.uint8) * 255
        
        # Also check for colored text like red numbers (R high, B & G low)
        b = card_crop[:, :, 0].astype(float)
        g = card_crop[:, :, 1].astype(float)
        r = card_crop[:, :, 2].astype(float)
        colored_text = ((r - b > 40) & (r - g > 40) & (card_mask > 0)).astype(np.uint8) * 255
        internal_ink = cv2.bitwise_or(internal_ink, colored_text)
        
        num_cc, labels, stats, centroids = cv2.connectedComponentsWithStats(internal_ink)
        
        # Count text-like sub-components (words, numbers, letters)
        text_components = []
        for i in range(1, num_cc):
            ca = stats[i, cv2.CC_STAT_AREA]
            cw_comp = stats[i, cv2.CC_STAT_WIDTH]
            ch_comp = stats[i, cv2.CC_STAT_HEIGHT]
            # Text glyphs are between 4px and 70px height
            if ca >= 6 and 4 <= ch_comp <= int(h * 0.85) and cw_comp <= int(w * 0.90):
                text_components.append({
                    "bbox": (stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], cw_comp, ch_comp),
                    "area": ca,
                    "centroid": centroids[i],
                    "mask": (labels == i).astype(np.uint8) * 255
                })
                
        # If the container contains multiple text-like glyphs or numbers (at least 2 distinct text components)
        is_card = (len(text_components) >= 2 and solidity >= 0.70)
        
        return {
            "is_card": is_card,
            "bbox": (x1, y1, w, h),
            "solidity": solidity,
            "bg_median_gray": median_gray,
            "card_crop": card_crop,
            "card_mask": card_mask,
            "internal_text_mask": internal_ink,
            "text_components": text_components
        }
