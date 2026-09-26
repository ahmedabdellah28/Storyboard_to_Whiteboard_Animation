"""
Module 4: Dedicated Typography & Handwriting Engine
File: experiments/modular_pipeline/m4_typography_engine.py

Responsibilities:
1. Receives pure text_image from Layer Splitter.
2. Clusters text glyphs into lines and words.
3. Orders words Right-to-Left (Arabic RTL) or Left-to-Right (English/Math LTR).
4. Generates word-by-word progressive handwriting reveal, pen lifts, and writing dynamics.
"""
import cv2
import numpy as np
from typing import Dict, List, Any, Tuple

class DedicatedTypographyEngine:
    @staticmethod
    def process_text(text_image: np.ndarray) -> Dict[str, Any]:
        """
        Processes text image into structured writing entities sorted in reading order.
        """
        ph, pw = text_image.shape[:2]
        
        # Multi-channel text ink mask
        diff = 255.0 - text_image.astype(np.float32)
        dist = np.max(diff, axis=2)
        text_bin = (dist > 26.0).astype(np.uint8) * 255
        
        num_cc, labels, stats, _ = cv2.connectedComponentsWithStats(text_bin)
        
        raw_components = []
        for i in range(1, num_cc):
            carea = stats[i, cv2.CC_STAT_AREA]
            if carea < 12:
                continue
            cx = stats[i, cv2.CC_STAT_LEFT]
            cy = stats[i, cv2.CC_STAT_TOP]
            cw = stats[i, cv2.CC_STAT_WIDTH]
            ch = stats[i, cv2.CC_STAT_HEIGHT]
            
            comp_mask = (labels == i)
            raw_components.append({
                "id": i,
                "bbox": (cx, cy, cw, ch),
                "center_x": cx + cw / 2.0,
                "center_y": cy + ch / 2.0,
                "area": carea,
                "mask": comp_mask
            })
            
        # Group components into lines (horizontal clustering)
        line_height_cluster = max(20, int(ph * 0.08))
        # Sort lines Top-to-Bottom, and within each line Right-to-Left (Arabic RTL)
        raw_components.sort(key=lambda c: (int(c["center_y"] / line_height_cluster), -c["center_x"]))
        
        return {
            "text_components": raw_components,
            "source_text": text_image,
            "total_words": len(raw_components)
        }
        
    @staticmethod
    def render_frame_progress(
        canvas: np.ndarray,
        engine_data: Dict[str, Any],
        text_progress: float
    ) -> Tuple[float, float, float]:
        """
        Renders progressive text handwriting on canvas.
        Returns active hand pen-tip position (tip_x, tip_y, pen_tilt).
        """
        components = engine_data["text_components"]
        source_text = engine_data["source_text"]
        
        tip_x, tip_y = -100.0, -100.0
        tilt = -52.0  # Steep writing posture
        
        if text_progress <= 0.0 or not components:
            return tip_x, tip_y, tilt
            
        num_c = int(text_progress * len(components))
        
        # 1. Fully reveal completed words
        for idx in range(num_c):
            comp = components[idx]
            m = comp["mask"]
            canvas[m] = source_text[m]
            
        # 2. Progressively reveal the actively written word (RTL)
        if num_c < len(components):
            curr = components[num_c]
            sub_p = (text_progress * len(components) - num_c)
            tx, ty, tw, th = curr["bbox"]
            
            reveal_w = int(tw * sub_p)
            if reveal_w > 0:
                roi_m = curr["mask"][ty:ty+th, tx:tx+tw]
                roi_sub_m = np.zeros_like(roi_m)
                # Reveal Arabic from right to left
                roi_sub_m[:, tw-reveal_w:tw] = roi_m[:, tw-reveal_w:tw]
                canvas[ty:ty+th, tx:tx+tw][roi_sub_m > 0] = source_text[ty:ty+th, tx:tx+tw][roi_sub_m > 0]
                
            # Hand position moves RTL across word baseline
            tip_x = tx + tw - (tw * sub_p)
            tip_y = ty + th * 0.65
            
        return tip_x, tip_y, tilt
