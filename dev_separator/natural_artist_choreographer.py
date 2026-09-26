"""
Natural Artist Choreographer (Hierarchical Character Drawing Engine)
Replaces random / circular concentric strokes with a 3-stage realistic drawing choreography:
Stage 1: Major Line Art & Outlines (هيكل الشخصية والخطوط الخارجية)
Stage 2: Facial Features & Detailed Line Work (ملامح الوجه والتفاصيل)
Stage 3: Natural Directional Color Hatching (التلوين والتظليل من الأعلى للأسفل)
"""
import cv2
import numpy as np
import math
from typing import List, Tuple, Dict, Any


class NaturalArtistChoreographer:
    @staticmethod
    def generate_character_drawing_plan(
        character_crop: np.ndarray, 
        character_mask: np.ndarray,
        step_dist: float = 4.0
    ) -> Dict[str, Any]:
        """
        Builds a natural human-like drawing sequence for a character:
        1. Outer Silhouette & Major Linework (Outlines)
        2. Facial Features & Line Details
        3. Smooth Directional Color Filling (Top-to-Bottom)
        """
        ch, cw = character_crop.shape[:2]
        gray = cv2.cvtColor(character_crop, cv2.COLOR_BGR2GRAY)
        
        # 1. Edge Extraction (Linework)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        edges = cv2.Canny(blurred, 40, 120)
        edges[character_mask == 0] = 0
        
        # Skeletonize linework into thin strokes
        kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        dilated_edges = cv2.dilate(edges, kernel)
        
        # Stage 1: Line Art Strokes (Ordered from top of head to bottom of body)
        contours, _ = cv2.findContours(dilated_edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        
        linework_strokes = []
        for cnt in contours:
            if len(cnt) >= 6:
                pts = cnt.reshape(-1, 2)
                # Subsample points
                sampled = [pts[0]]
                accum = 0.0
                for pt in pts[1:]:
                    d = math.hypot(pt[0] - sampled[-1][0], pt[1] - sampled[-1][1])
                    if d >= step_dist:
                        sampled.append(pt)
                if len(sampled) >= 3:
                    linework_strokes.append(sampled)
                    
        # Sort linework from top to bottom (head first, then facial features, then torso/arms)
        linework_strokes.sort(key=lambda s: np.mean([pt[1] for pt in s]))
        
        # Stage 2: Color Shading / Filling Paths (Top-to-bottom directional passes)
        # We generate smooth horizontal passes to fill color like a marker pen
        hatching_strokes = []
        y_step = 6 # Distance between coloring passes
        
        for y in range(4, ch - 4, y_step):
            row_xs = np.where(character_mask[y, :] > 0)[0]
            if len(row_xs) > 6:
                # Group contiguous horizontal spans
                spans = []
                s_start = row_xs[0]
                prev_x = row_xs[0]
                for x in row_xs[1:]:
                    if x == prev_x + 1:
                        prev_x = x
                    else:
                        if prev_x - s_start >= 6:
                            spans.append((s_start, prev_x))
                        s_start = x
                        prev_x = x
                if prev_x - s_start >= 6:
                    spans.append((s_start, prev_x))
                    
                for x_st, x_en in spans:
                    # Zigzag stroke across the row
                    stroke = [(x, y) for x in range(x_st, x_en + 1, int(step_dist))]
                    if len(stroke) >= 2:
                        hatching_strokes.append(stroke)

        return {
            "total_linework_strokes": len(linework_strokes),
            "total_shading_strokes": len(hatching_strokes),
            "linework_strokes": linework_strokes,
            "shading_strokes": hatching_strokes,
            "stages": [
                {
                    "stage_id": 1,
                    "name": "Phase 1: Line Art & Outlines (هيكل الشخصية)",
                    "description": "رسم الخطوط الخارجية وملامح الوجه بالقلم بدقة متناهية من الأعلى للأسفل",
                    "strokes_count": len(linework_strokes)
                },
                {
                    "stage_id": 2,
                    "name": "Phase 2: Natural Shading & Fills (التلوين والتظليل)",
                    "description": "تلوين مساحات البشرة والشعر والملابس بتمريرات مريحة تحاكي قلم التلوين",
                    "strokes_count": len(hatching_strokes)
                }
            ]
        }
