"""
Module 3: Dedicated Character & Graphics Drawing Engine
File: experiments/modular_pipeline/m3_character_engine.py

Responsibilities:
1. Receives pure graphics_image from Layer Splitter.
2. Extracts strokes via EdgeExtractor and classifies them via StrokeClassifier
   (Outer Outlines -> Internal Details -> Color Boundaries).
3. Extracts color regions via RegionExtractor & ColorProcessor for Progressive TrueColor Fills.
4. Generates precise drawing timeline and pen-tip coordinates for Art Sketching Mode.
"""
import sys
import math
import cv2
import numpy as np
from typing import Dict, List, Any, Tuple

# Ensure kivy directory is in path
sys.path.insert(0, r"E:\image_to_animate\kivy")

from engine.core.scene import SceneConfig
from engine.core.stroke import Stroke, StrokeType
from engine.core.region import ColorRegion
from engine.processing.edge_extractor import EdgeExtractor
from engine.processing.stroke_classifier import StrokeClassifier
from engine.processing.region_extractor import RegionExtractor
from engine.processing.color_processor import ColorProcessor
from engine.animation.stroke_animator import StrokeAnimator
from engine.animation.fill_animator import FillAnimator

class DedicatedCharacterEngine:
    def __init__(self, config: SceneConfig = None):
        self.config = config or SceneConfig(
            detail_level="HIGH",
            color_palette_size=16,
            show_hand=True,
            drawing_speed=1.0
        )
        
    def process_graphics(self, graphics_image: np.ndarray) -> Dict[str, Any]:
        """
        Processes graphics image using the project's native character drawing pipeline.
        Returns ordered strokes, fill regions, and drawing dynamics.
        """
        # 1. Color Quantization & Region Extraction
        quantized_bgr, palette, bg_color = ColorProcessor.quantize(graphics_image, self.config)
        raw_regions = RegionExtractor.extract(quantized_bgr, palette, bg_color, self.config)
        
        # Filter out pure white background fills
        color_regions = [r for r in raw_regions if r.color != (255, 255, 255) and r.area > 50]
        # Sort fills: largest to smallest (Base clothes -> skin -> hair -> emoji/accent)
        color_regions.sort(key=lambda r: r.area, reverse=True)
        
        # 2. Multi-scale Edge Extraction & Classification
        raw_strokes = EdgeExtractor.extract(graphics_image, self.config)
        classified_strokes = StrokeClassifier.classify(raw_strokes, graphics_image, quantized_bgr, self.config)
        
        outlines = [s for s in classified_strokes if s.stroke_type == StrokeType.OUTER_OUTLINE]
        internals = [s for s in classified_strokes if s.stroke_type == StrokeType.INTERNAL_DETAIL]
        color_bounds = [s for s in classified_strokes if s.stroke_type == StrokeType.COLOR_BOUNDARY]
        
        outlines.sort(key=lambda s: s.length, reverse=True)
        internals.sort(key=lambda s: s.center[1])
        color_bounds.sort(key=lambda s: s.length, reverse=True)
        
        ordered_strokes = outlines + internals + color_bounds
        
        return {
            "ordered_strokes": ordered_strokes,
            "color_regions": color_regions,
            "source_graphics": graphics_image,
            "total_strokes": len(ordered_strokes),
            "total_fills": len(color_regions)
        }
        
    @staticmethod
    def render_frame_progress(
        canvas: np.ndarray,
        engine_data: Dict[str, Any],
        stroke_progress: float,
        fill_progress: float
    ) -> Tuple[float, float, float]:
        """
        Renders progressive character drawing on canvas.
        Returns active hand pen-tip position (tip_x, tip_y, pen_tilt).
        """
        ordered_strokes = engine_data["ordered_strokes"]
        color_regions = engine_data["color_regions"]
        source_graphics = engine_data["source_graphics"]
        
        tip_x, tip_y = -100.0, -100.0
        tilt = -35.0
        
        # 1. Render Strokes
        if stroke_progress > 0.0 and ordered_strokes:
            num_s = int(stroke_progress * len(ordered_strokes))
            for idx in range(num_s):
                stk = ordered_strokes[idx]
                StrokeAnimator.render_stroke(canvas, stk, 1.0, "linear", source_graphics)
            
            if num_s < len(ordered_strokes):
                curr_s = ordered_strokes[num_s]
                sub_p = (stroke_progress * len(ordered_strokes) - num_s)
                StrokeAnimator.render_stroke(canvas, curr_s, sub_p, "linear", source_graphics)
                
                # Active hand position along stroke
                pts = curr_s.points
                pt_idx = min(len(pts) - 1, int(sub_p * len(pts)))
                tip_x, tip_y = pts[pt_idx][0], pts[pt_idx][1]
                tilt = -38.0
        
        # 2. Render Color Fills
        if fill_progress > 0.0 and color_regions:
            num_f = int(fill_progress * len(color_regions))
            for idx in range(num_f):
                reg = color_regions[idx]
                FillAnimator.render_fill(canvas, reg, 1.0, "ease_in_out", source_graphics)
                
            if num_f < len(color_regions):
                curr_reg = color_regions[num_f]
                sub_f = (fill_progress * len(color_regions) - num_f)
                FillAnimator.render_fill(canvas, curr_reg, sub_f, "ease_in_out", source_graphics)
                
                # Active hand shading oscillation
                cx, cy = curr_reg.center
                osc_x = math.cos(fill_progress * 40.0) * min(20.0, curr_reg.bbox[2] * 0.25)
                osc_y = math.sin(fill_progress * 40.0) * min(20.0, curr_reg.bbox[3] * 0.25)
                tip_x = cx + osc_x
                tip_y = cy + osc_y
                tilt = -30.0
                
        return tip_x, tip_y, tilt
