"""
Phase 6 — Drawing Method Discovery Engine
File: experiments/drawing_methods/drawing_method_classifier.py

Determines HOW each individual entity should be drawn on the whiteboard:
1. METHOD_CHARACTER_OUTLINE_AND_HATCH:
   - Vector contour silhouette -> Facial/cloth detailing -> Progressive Zig-zag Hatching Fill (حركة متعرجة).
2. METHOD_CALLIGRAPHIC_HANDWRITING:
   - Natural fluid stroke trajectory following RTL (Arabic) or LTR (English/Math) direction.
3. METHOD_GEOMETRIC_CONSTRUCTION:
   - Linear coordinate axes, tick marks, geometric polygon paths (Triangle, Box).
4. METHOD_CLOSED_CONTOUR_LOOP:
   - Single-stroke continuous perimeter (Speech Bubbles, Cloud Frames).
5. METHOD_RADIAL_EMOJI_STAMP:
   - Outer circle loop -> Inner facial smile -> Radial color wash.
6. METHOD_GESTURAL_ACCENT:
   - Rapid gesture paths (Hearts, Stars, Lightbulb ideas, Rays).
"""
import math
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple


class DrawingMethodType:
    CHARACTER_HATCH = "CHARACTER_OUTLINE_AND_HATCH"
    HANDWRITING_RTL = "HANDWRITING_ARABIC_RTL"
    HANDWRITING_LTR = "HANDWRITING_ENGLISH_LTR"
    MATH_NOTATION = "MATHEMATICAL_CONSTRUCTION"
    GEOMETRIC_DIAGRAM = "GEOMETRIC_LINEWORK"
    CONTAINER_LOOP = "CLOSED_CONTOUR_LOOP"
    RADIAL_EMOJI = "RADIAL_EMOJI_REVEAL"
    GESTURAL_ACCENT = "GESTURAL_QUICK_ACCENT"


class DrawingMethodClassifier:
    """Classifies the optimal drawing technique and generates trajectory parameters for any entity."""

    @staticmethod
    def assign_drawing_method(entity: Dict[str, Any], panel_shape: tuple) -> Dict[str, Any]:
        cat = entity["category"]
        sub = entity["sub_type"]
        script = entity.get("script", "NONE")
        direction = entity.get("direction", "NONE")
        bbox = entity["bbox"]
        bx, by, bw, bh = bbox
        
        # 1. Typography & Handwriting
        if cat in ["title", "text_line"]:
            if script == "ARABIC" or direction == "RTL":
                method = DrawingMethodType.HANDWRITING_RTL
                pen_tool = "CHISEL_TIP_MARKER_DARK"
                stroke_style = "FLUID_ARABIC_CURSIVE"
                fill_mode = "NONE"
            else:
                method = DrawingMethodType.HANDWRITING_LTR
                pen_tool = "ROUND_TIP_MARKER_DARK"
                stroke_style = "DISCRETE_LATIN_STEMS"
                fill_mode = "NONE"
                
        elif cat == "math_formula":
            method = DrawingMethodType.MATH_NOTATION
            pen_tool = "FINE_TIP_MARKER_BLUE"
            stroke_style = "MATHEMATICAL_OPERATOR_FLOW"
            fill_mode = "NONE"
            
        # 2. Characters & Mascots
        elif cat == "character":
            method = DrawingMethodType.CHARACTER_HATCH
            pen_tool = "MEDIUM_OUTLINE_AND_BRUSH"
            stroke_style = "OUTER_SILHOUETTE_THEN_DETAILS"
            fill_mode = "ZIGZAG_HATCHING" # حركة متعرجة
            
        # 3. Containers & Speech Bubbles
        elif cat == "container":
            method = DrawingMethodType.CONTAINER_LOOP
            pen_tool = "CHISEL_TIP_MARKER_BLUE"
            stroke_style = "CONTINUOUS_CLOUD_LOOP"
            fill_mode = "TRANSPARENT_INTERIOR"
            
        # 4. Diagrams & Scientific Geometry
        elif cat == "diagram":
            method = DrawingMethodType.GEOMETRIC_DIAGRAM
            pen_tool = "RULER_AND_FINE_MARKER"
            stroke_style = "AXES_THEN_FUNCTION_CURVE"
            fill_mode = "SECTION_SHADING"
            
        # 5. Emojis
        elif cat == "emoji":
            method = DrawingMethodType.RADIAL_EMOJI
            pen_tool = "ROUND_MARKER_YELLOW_BLACK"
            stroke_style = "CIRCULAR_OUTLINE_THEN_FACE"
            fill_mode = "ZIGZAG_HATCHING"
            
        # 6. Accents & Symbols
        else:
            method = DrawingMethodType.GESTURAL_ACCENT
            pen_tool = "FINE_GESTURE_MARKER"
            stroke_style = "RAPID_STROKE"
            fill_mode = "SOLID_POP"

        # Trajectory Anchor Points
        # For RTL: Start Top-Right (bx + bw, by); For LTR: Start Top-Left (bx, by)
        if direction == "RTL":
            start_point = (bx + bw - 4, by + int(bh * 0.4))
            end_point = (bx + 4, by + int(bh * 0.7))
        else:
            start_point = (bx + 4, by + int(bh * 0.4))
            end_point = (bx + bw - 4, by + int(bh * 0.7))
            
        return {
            "entity_id": entity["entity_id"],
            "category": cat,
            "drawing_method": method,
            "pen_tool": pen_tool,
            "stroke_style": stroke_style,
            "fill_mode": fill_mode,
            "start_point": start_point,
            "end_point": end_point,
            "hatching_angle_deg": -35.0 if fill_mode == "ZIGZAG_HATCHING" else 0.0
        }
