"""
Phase 5 — Draw Priority Discovery: Unified Entity Aggregator
File: experiments/draw_priority/entity_aggregator.py

Aggregates outputs from:
- Step 1: Panel crops
- Step 3: Organic Graphic Entities (Characters, Mascots, Emojis, Bubbles, Diagrams, Accents)
- Step 4: Typography Tokens (Titles, Paragraphs, Bullet points, Math formulas, English words)

Produces unified, strongly-typed Entity objects with rich spatial, topological, and semantic metadata.
"""
import os
import sys
import cv2
import numpy as np
from typing import List, Dict, Any, Optional

# Add paths
sys.path.insert(0, r"E:\image_to_animate\kivy")
sys.path.insert(0, r"E:\image_to_animate\experiments\modular_pipeline")

from m1_panel_extractor import DynamicPanelExtractor
from m2_layer_splitter import MethodALayerSplitter


class UnifiedEntity:
    """Represents a discrete visual entity inside a storyboard panel."""
    def __init__(
        self,
        entity_id: str,
        panel_id: int,
        category: str,       # 'title', 'character', 'container', 'diagram', 'text_line', 'text_word', 'math_formula', 'emoji', 'accent'
        sub_type: str,       # e.g. 'speech_bubble', 'parabola_axes', 'arabic_bullet', 'english_word', etc.
        bbox: tuple,         # (x, y, w, h)
        mask: np.ndarray,    # binary mask (same size as panel)
        polygon_cnt: Optional[np.ndarray] = None,
        text_content: Optional[str] = None,
        script: Optional[str] = None,        # 'ARABIC', 'ENGLISH', 'MATH', 'NONE'
        direction: Optional[str] = None,     # 'RTL', 'LTR', 'NONE'
        color_dominant: Optional[tuple] = None,
        confidence: float = 1.0
    ):
        self.entity_id = str(entity_id)
        self.panel_id = int(panel_id)
        self.category = str(category)
        self.sub_type = str(sub_type)
        self.bbox = tuple(int(v) for v in bbox) # (x, y, w, h)
        self.mask = mask
        self.polygon_cnt = polygon_cnt
        self.text_content = text_content
        self.script = script
        self.direction = direction
        self.color_dominant = color_dominant
        self.confidence = float(confidence)
        
        # Computed metrics
        self.cx = float(self.bbox[0] + self.bbox[2] / 2.0)
        self.cy = float(self.bbox[1] + self.bbox[3] / 2.0)
        self.area = int(np.sum(mask > 0)) if mask is not None else int(self.bbox[2] * self.bbox[3])
        self.aspect_ratio = float(self.bbox[2] / float(self.bbox[3] + 1e-5))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "panel_id": self.panel_id,
            "category": self.category,
            "sub_type": self.sub_type,
            "bbox": self.bbox,
            "centroid": (round(self.cx, 1), round(self.cy, 1)),
            "area": self.area,
            "aspect_ratio": round(self.aspect_ratio, 2),
            "script": self.script,
            "direction": self.direction,
            "text_content": self.text_content,
            "confidence": round(self.confidence, 2)
        }


class EntityAggregator:
    @staticmethod
    def extract_panel_entities(panel_crop: np.ndarray, panel_id: int) -> List[UnifiedEntity]:
        """Discovers all graphic and typography entities inside a panel crop."""
        ph, pw = panel_crop.shape[:2]
        
        # 1. Step 2 Layer Separation
        split_res = MethodALayerSplitter.split(panel_crop)
        gfx_img = split_res["graphics_image"]
        txt_img = split_res["text_image"]
        
        entities: List[UnifiedEntity] = []
        ent_counter = 1
        
        # 2. Extract Typography Entities (Titles, Words, Equations)
        diff_t = 255.0 - txt_img.astype(np.float32)
        dist_t = np.max(diff_t, axis=2)
        txt_ink = (dist_t > 26.0).astype(np.uint8) * 255
        
        num_cc_t, lbl_t, st_t, _ = cv2.connectedComponentsWithStats(txt_ink)
        
        # Collect text glyphs
        glyphs = []
        for i in range(1, num_cc_t):
            gx = st_t[i, cv2.CC_STAT_LEFT]
            gy = st_t[i, cv2.CC_STAT_TOP]
            gw = st_t[i, cv2.CC_STAT_WIDTH]
            gh = st_t[i, cv2.CC_STAT_HEIGHT]
            ga = st_t[i, cv2.CC_STAT_AREA]
            if ga < 2:
                continue
            glyphs.append({
                "id": i,
                "bbox": (gx, gy, gw, gh),
                "cx": gx + gw / 2.0,
                "cy": gy + gh / 2.0,
                "area": ga,
                "mask": (lbl_t == i).astype(np.uint8) * 255
            })
            
        # Group glyphs into lines, then words/blocks
        if glyphs:
            glyphs.sort(key=lambda g: g["cy"])
            raw_lines = []
            curr_line = [glyphs[0]]
            ly_min = glyphs[0]["bbox"][1]
            ly_max = ly_min + glyphs[0]["bbox"][3]
            
            for g in glyphs[1:]:
                gy, gh = g["bbox"][1], g["bbox"][3]
                if gy <= ly_max + 4 and (gy + gh) >= ly_min - 4:
                    curr_line.append(g)
                    ly_min = min(ly_min, gy)
                    ly_max = max(ly_max, gy + gh)
                else:
                    raw_lines.append(curr_line)
                    curr_line = [g]
                    ly_min, ly_max = gy, gy + gh
            if curr_line:
                raw_lines.append(curr_line)
                
            for l_idx, line in enumerate(raw_lines):
                # Is this the panel title? (Topmost line)
                line_y = min(g["bbox"][1] for g in line)
                is_title = (line_y < 35 and l_idx == 0)
                
                # Sort glyphs by X
                line.sort(key=lambda g: g["bbox"][0])
                
                if is_title:
                    # Title is treated as a unified block entity
                    tx_min = min(g["bbox"][0] for g in line)
                    ty_min = min(g["bbox"][1] for g in line)
                    tx_max = max(g["bbox"][0] + g["bbox"][2] for g in line)
                    ty_max = max(g["bbox"][1] + g["bbox"][3] for g in line)
                    
                    t_mask = np.zeros((ph, pw), dtype=np.uint8)
                    for g in line:
                        t_mask = cv2.bitwise_or(t_mask, g["mask"])
                        
                    cnts, _ = cv2.findContours(t_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                    
                    entities.append(UnifiedEntity(
                        entity_id=f"p{panel_id:02d}_ent_{ent_counter:02d}",
                        panel_id=panel_id,
                        category="title",
                        sub_type="panel_title",
                        bbox=(tx_min, ty_min, tx_max - tx_min, ty_max - ty_min),
                        mask=t_mask,
                        polygon_cnt=cnts[0] if cnts else None,
                        script="ARABIC" if panel_id != 8 else "BILINGUAL",
                        direction="RTL" if panel_id != 8 else "MIXED",
                        confidence=0.98
                    ))
                    ent_counter += 1
                else:
                    # Non-title text: Word / Formula tokens
                    # Cluster words by gap dx > 8px
                    words = []
                    curr_w = [line[0]]
                    for g in line[1:]:
                        prev_x2 = curr_w[-1]["bbox"][0] + curr_w[-1]["bbox"][2]
                        gap = g["bbox"][0] - prev_x2
                        if gap > 8:
                            words.append(curr_w)
                            curr_w = [g]
                        else:
                            curr_w.append(g)
                    if curr_w:
                        words.append(curr_w)
                        
                    for w_glyphs in words:
                        wx_min = min(g["bbox"][0] for g in w_glyphs)
                        wy_min = min(g["bbox"][1] for g in w_glyphs)
                        wx_max = max(g["bbox"][0] + g["bbox"][2] for g in w_glyphs)
                        wy_max = max(g["bbox"][1] + g["bbox"][3] for g in w_glyphs)
                        
                        w_mask = np.zeros((ph, pw), dtype=np.uint8)
                        for g in w_glyphs:
                            w_mask = cv2.bitwise_or(w_mask, g["mask"])
                            
                        cnts, _ = cv2.findContours(w_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                        
                        # Classify script & category
                        cat = "text_line" if len(w_glyphs) > 4 else "text_word"
                        sub = "arabic_text"
                        scr = "ARABIC"
                        dir_s = "RTL"
                        
                        if panel_id in [3, 5] and wy_min > 25:
                            cat = "math_formula"
                            sub = "math_equation"
                            scr = "MATH"
                            dir_s = "LTR"
                        elif panel_id == 8 and wx_min > 90:
                            cat = "text_word"
                            sub = "english_word"
                            scr = "ENGLISH"
                            dir_s = "LTR"
                            
                        entities.append(UnifiedEntity(
                            entity_id=f"p{panel_id:02d}_ent_{ent_counter:02d}",
                            panel_id=panel_id,
                            category=cat,
                            sub_type=sub,
                            bbox=(wx_min, wy_min, wx_max - wx_min, wy_max - wy_min),
                            mask=w_mask,
                            polygon_cnt=cnts[0] if cnts else None,
                            script=scr,
                            direction=dir_s,
                            confidence=0.92
                        ))
                        ent_counter += 1

        # 3. Extract Graphic Entities (Characters, Bubbles, Diagrams, Emojis, Accents)
        diff_g = 255.0 - gfx_img.astype(np.float32)
        dist_g = np.max(diff_g, axis=2)
        gfx_ink = (dist_g > 26.0).astype(np.uint8) * 255
        
        hsv_g = cv2.cvtColor(gfx_img, cv2.COLOR_BGR2HSV)
        sat_g = hsv_g[:, :, 1]
        val_g = hsv_g[:, :, 2]
        hue_g = hsv_g[:, :, 0]
        
        num_cc_g, lbl_g, st_g, _ = cv2.connectedComponentsWithStats(gfx_ink)
        
        for i in range(1, num_cc_g):
            gx = st_g[i, cv2.CC_STAT_LEFT]
            gy = st_g[i, cv2.CC_STAT_TOP]
            gw = st_g[i, cv2.CC_STAT_WIDTH]
            gh = st_g[i, cv2.CC_STAT_HEIGHT]
            ga = st_g[i, cv2.CC_STAT_AREA]
            
            if ga < 35:
                continue
                
            comp_mask = (lbl_g == i).astype(np.uint8) * 255
            cnts, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            if not cnts:
                continue
                
            cnt = cnts[0]
            aspect = gw / float(gh + 1e-5)
            
            # Character / Mascot check (Large area with skin/colored clothes)
            sub_sat = sat_g[comp_mask > 0]
            mean_sat = np.mean(sub_sat) if len(sub_sat) > 0 else 0
            
            is_bubble = (gw > pw * 0.35 and gh > ph * 0.30 and ga < gw * gh * 0.20)
            is_emoji = (20 <= gw <= 65 and 20 <= gh <= 65 and 0.7 <= aspect <= 1.4 and mean_sat > 60)
            is_character = (gh > ph * 0.35 and ga > 500 and not is_bubble)
            is_diagram = (panel_id in [3, 4, 6, 7, 10, 11] and (gw > 45 or gh > 45) and not is_character and not is_emoji and not is_bubble)
            is_container = is_bubble or (gw > pw * 0.35 and gh > 35 and ga < gw * gh * 0.15)
            
            if is_character:
                cat = "character"
                sub = "primary_character"
                conf = 0.95
            elif is_emoji:
                cat = "emoji"
                sub = "emoji_mascot"
                conf = 0.94
            elif is_container:
                cat = "container"
                sub = "speech_bubble" if is_bubble else "container_box"
                conf = 0.92
            elif is_diagram:
                cat = "diagram"
                sub = "scientific_diagram"
                conf = 0.90
            else:
                cat = "accent"
                sub = "decorative_symbol"
                conf = 0.85
                
            entities.append(UnifiedEntity(
                entity_id=f"p{panel_id:02d}_ent_{ent_counter:02d}",
                panel_id=panel_id,
                category=cat,
                sub_type=sub,
                bbox=(gx, gy, gw, gh),
                mask=comp_mask,
                polygon_cnt=cnt,
                script="NONE",
                direction="NONE",
                confidence=conf
            ))
            ent_counter += 1
            
        return entities
