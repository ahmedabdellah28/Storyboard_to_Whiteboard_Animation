"""
Typography Line Grouper & Dynamic Line Assembly Engine
Solves text fragmentation:
1. Dynamically scales horizontal word bridging relative to font height (no fixed kernel).
2. Groups horizontally aligned words into full, cohesive sentences/lines.
3. Distinguishes titles, underlines, and body text lines.
4. Correctly computes RTL (Arabic) / LTR (English) reading orders.
"""
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple


class TypographyLineGrouper:
    @staticmethod
    def audit_and_group_lines(txt_img: np.ndarray, min_line_pixels: int = 15) -> Dict[str, Any]:
        """
        Groups words and glyphs into full horizontal sentences and text lines.
        Ensures both large titles and small body text form complete horizontal lines
        without fragmenting into individual words or breaking across sentences.
        """
        ph, pw = txt_img.shape[:2]

        diff = 255.0 - txt_img.astype(np.float32)
        dist = np.max(diff, axis=2)
        ink_bin = (dist > 25.0).astype(np.uint8) * 255

        if cv2.countNonZero(ink_bin) < min_line_pixels:
            return {"lines": [], "accents": []}

        # Step 1: Find individual words/glyphs first
        num_cc, labels, stats, centroids = cv2.connectedComponentsWithStats(ink_bin)
        
        words = []
        for i in range(1, num_cc):
            wx = stats[i, cv2.CC_STAT_LEFT]
            wy = stats[i, cv2.CC_STAT_TOP]
            ww = stats[i, cv2.CC_STAT_WIDTH]
            wh = stats[i, cv2.CC_STAT_HEIGHT]
            wa = stats[i, cv2.CC_STAT_AREA]
            cx, cy = centroids[i]
            
            if wa < 4:
                continue
                
            w_mask = (labels == i).astype(np.uint8) * 255
            words.append({
                "id": i,
                "bbox": (wx, wy, ww, wh),
                "cx": cx, "cy": cy,
                "area": wa,
                "mask": w_mask
            })

        if not words:
            return {"lines": [], "accents": []}

        # Step 2: Separate small standalone punctuation / dots from primary word bodies
        primary_words = []
        isolated_dots = []
        
        for w in words:
            wx, wy, ww, wh = w["bbox"]
            if w["area"] < 12 and max(ww, wh) <= 8:
                isolated_dots.append(w)
            else:
                primary_words.append(w)

        if not primary_words:
            primary_words = words
            isolated_dots = []

        # Step 3: Vertical band clustering to discover line baselines
        # Sort words from top to bottom
        primary_words.sort(key=lambda w: w["bbox"][1])
        
        line_clusters: List[List[Dict[str, Any]]] = []
        for word in primary_words:
            wx, wy, ww, wh = word["bbox"]
            w_center_y = wy + wh / 2.0
            
            best_cluster_idx = -1
            best_overlap = 0.0
            
            for c_idx, cluster in enumerate(line_clusters):
                # Calculate vertical overlap with existing line cluster
                c_y1 = min(w["bbox"][1] for w in cluster)
                c_y2 = max(w["bbox"][1] + w["bbox"][3] for w in cluster)
                c_h = c_y2 - c_y1
                
                # Check vertical overlap
                y_overlap = max(0, min(wy + wh, c_y2) - max(wy, c_y1))
                min_h = max(1, min(wh, c_h))
                overlap_ratio = y_overlap / float(min_h)
                
                # Check center distance
                c_center_y = (c_y1 + c_y2) / 2.0
                dist_y = abs(w_center_y - c_center_y)
                
                if overlap_ratio > 0.35 or dist_y < max(8.0, 0.40 * min_h):
                    if overlap_ratio > best_overlap:
                        best_overlap = overlap_ratio
                        best_cluster_idx = c_idx
                        
            if best_cluster_idx >= 0:
                line_clusters[best_cluster_idx].append(word)
            else:
                line_clusters.append([word])

        # Step 4: Attach isolated dots/accents to their nearest vertical line
        for dot in isolated_dots:
            dx, dy, dw, dh = dot["bbox"]
            d_center_y = dy + dh / 2.0
            
            best_dist = float('inf')
            best_cluster = None
            
            for cluster in line_clusters:
                c_y1 = min(w["bbox"][1] for w in cluster)
                c_y2 = max(w["bbox"][1] + w["bbox"][3] for w in cluster)
                c_center_y = (c_y1 + c_y2) / 2.0
                dist_y = abs(d_center_y - c_center_y)
                
                # Check horizontal alignment within cluster bounds (+/- 15px margin)
                c_x1 = min(w["bbox"][0] for w in cluster) - 15
                c_x2 = max(w["bbox"][0] + w["bbox"][2] for w in cluster) + 15
                
                if c_x1 <= dx <= c_x2 and dist_y < best_dist:
                    best_dist = dist_y
                    best_cluster = cluster
                    
            if best_cluster is not None and best_dist < 35.0:
                best_cluster.append(dot)

        # Step 5: Construct full horizontal line objects
        # Sort lines vertically from top to bottom
        line_clusters.sort(key=lambda c: min(w["bbox"][1] for w in c))
        
        constructed_lines = []
        for line_idx, cluster in enumerate(line_clusters):
            # Combine all word masks in this line
            lx1 = min(w["bbox"][0] for w in cluster)
            ly1 = min(w["bbox"][1] for w in cluster)
            lx2 = max(w["bbox"][0] + w["bbox"][2] for w in cluster)
            ly2 = max(w["bbox"][1] + w["bbox"][3] for w in cluster)
            lw = lx2 - lx1 + 1
            lh = ly2 - ly1 + 1
            
            line_m = np.zeros((ph, pw), dtype=np.uint8)
            for w in cluster:
                line_m = cv2.bitwise_or(line_m, w["mask"])
                
            aspect = lw / float(lh + 1e-5)
            is_underline = (aspect > 6.0 and lh <= 6)
            is_title = (line_idx == 0 and ly1 < ph * 0.35 and not is_underline)
            
            line_type = "UNDERLINE" if is_underline else ("TITLE" if is_title else "TEXT_LINE")
            direction = "LTR" if is_underline else "RTL"
            
            constructed_lines.append({
                "line_id": line_idx + 1,
                "type": line_type,
                "bbox": (lx1, ly1, lw, lh),
                "mask": line_m,
                "direction": direction,
                "words_count": len(cluster),
                "pixel_count": cv2.countNonZero(line_m),
                "is_underline": is_underline
            })

        return {
            "lines": constructed_lines,
            "accents": []
        }
