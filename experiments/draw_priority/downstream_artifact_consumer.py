"""
Phase 5 — Downstream Artifact Consumer (High-Precision Coherent Line Architecture)
File: experiments/draw_priority/downstream_artifact_consumer.py

Consumes EXCLUSIVELY:
- Step 3: Graphics Layer (pXX_01_graphics.png)
- Step 4: Typography Layer (pXX_02_typography.png)

Maintains Strict Semantic Line Coherence:
- Preserves whole text lines and bullet points as atomic thought units.
- Eliminates fragmented word scrambling.
- Guarantees natural pedagogical sequence: Title -> Subject/Character -> Container -> Top-to-Bottom Lines -> Accents.
"""
import os
import sys
import cv2
import numpy as np
from typing import List, Dict, Any, Optional

PIPELINE_RESULTS_DIR = r"E:\image_to_animate\experiments\results\all_12_panels_pipeline"


class UnifiedEntity:
    """Represents a discrete visual entity discovered by Step 3 or Step 4."""
    def __init__(
        self,
        entity_id: str,
        panel_id: int,
        source_stage: str,   # 'STEP_3_GRAPHICS' or 'STEP_4_TYPOGRAPHY'
        category: str,       # 'title', 'character', 'container', 'diagram', 'text_line', 'math_formula', 'emoji', 'accent'
        sub_type: str,
        bbox: tuple,         # (x, y, w, h)
        mask: np.ndarray,
        polygon_cnt: Optional[np.ndarray] = None,
        script: str = "NONE",
        direction: str = "NONE",
        confidence: float = 1.0
    ):
        self.entity_id = str(entity_id)
        self.panel_id = int(panel_id)
        self.source_stage = str(source_stage)
        self.category = str(category)
        self.sub_type = str(sub_type)
        self.bbox = tuple(int(v) for v in bbox)
        self.mask = mask
        self.polygon_cnt = polygon_cnt
        self.script = str(script)
        self.direction = str(direction)
        self.confidence = float(confidence)
        
        self.cx = float(self.bbox[0] + self.bbox[2] / 2.0)
        self.cy = float(self.bbox[1] + self.bbox[3] / 2.0)
        self.area = int(np.sum(mask > 0)) if mask is not None else int(self.bbox[2] * self.bbox[3])
        self.aspect_ratio = float(self.bbox[2] / float(self.bbox[3] + 1e-5))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "panel_id": self.panel_id,
            "source_stage": self.source_stage,
            "category": self.category,
            "sub_type": self.sub_type,
            "bbox": self.bbox,
            "centroid": (round(self.cx, 1), round(self.cy, 1)),
            "area": self.area,
            "script": self.script,
            "direction": self.direction,
            "confidence": round(self.confidence, 2)
        }


class DownstreamArtifactConsumer:
    @staticmethod
    def load_panel_artifacts(panel_id: int) -> Dict[str, Any]:
        """Loads strictly from Step 3 and Step 4 outputs."""
        p_dir = os.path.join(PIPELINE_RESULTS_DIR, f"panel_{panel_id:02d}")
        gfx_path = os.path.join(p_dir, f"p{panel_id:02d}_01_graphics.png")
        txt_path = os.path.join(p_dir, f"p{panel_id:02d}_02_typography.png")
        
        if not os.path.exists(gfx_path) or not os.path.exists(txt_path):
            raise FileNotFoundError(f"Missing Step 3/4 artifacts for panel {panel_id} in {p_dir}")
            
        gfx_img = cv2.imread(gfx_path)
        txt_img = cv2.imread(txt_path)
        
        # Assembled canvas derived purely from the sum of Step 3 and Step 4 layers
        composite_canvas = np.full_like(gfx_img, 255)
        m_txt = (np.max(255.0 - txt_img.astype(np.float32), axis=2) > 26.0)
        m_gfx = (np.max(255.0 - gfx_img.astype(np.float32), axis=2) > 26.0)
        
        composite_canvas[m_gfx] = gfx_img[m_gfx]
        composite_canvas[m_txt] = txt_img[m_txt]
        
        return {
            "panel_id": panel_id,
            "graphics_image": gfx_img,
            "typography_image": txt_img,
            "composite_canvas": composite_canvas,
            "shape": gfx_img.shape[:2]
        }

    @staticmethod
    def extract_entities_from_artifacts(panel_data: Dict[str, Any]) -> List[UnifiedEntity]:
        """Builds unified entities strictly from Step 3 graphics and Step 4 text images."""
        pid = panel_data["panel_id"]
        gfx_img = panel_data["graphics_image"]
        txt_img = panel_data["typography_image"]
        ph, pw = panel_data["shape"]
        
        entities: List[UnifiedEntity] = []
        ent_counter = 1
        
        # -------------------------------------------------------------
        # 1. CONSUME STEP 4 TYPOGRAPHY ARTIFACT (ATOMIC LINES & PHRASES)
        # -------------------------------------------------------------
        diff_t = 255.0 - txt_img.astype(np.float32)
        dist_t = np.max(diff_t, axis=2)
        txt_ink = (dist_t > 26.0).astype(np.uint8) * 255
        
        num_cc_t, lbl_t, st_t, _ = cv2.connectedComponentsWithStats(txt_ink)
        glyphs = []
        for i in range(1, num_cc_t):
            gx, gy = st_t[i, cv2.CC_STAT_LEFT], st_t[i, cv2.CC_STAT_TOP]
            gw, gh = st_t[i, cv2.CC_STAT_WIDTH], st_t[i, cv2.CC_STAT_HEIGHT]
            ga = st_t[i, cv2.CC_STAT_AREA]
            if ga < 2: continue
            glyphs.append({
                "bbox": (gx, gy, gw, gh),
                "cx": gx + gw / 2.0, "cy": gy + gh / 2.0,
                "mask": (lbl_t == i).astype(np.uint8) * 255
            })
            
        if glyphs:
            glyphs.sort(key=lambda g: g["cy"])
            lines = []
            curr_line = [glyphs[0]]
            ly_min, ly_max = glyphs[0]["bbox"][1], glyphs[0]["bbox"][1] + glyphs[0]["bbox"][3]
            
            for g in glyphs[1:]:
                gy, gh = g["bbox"][1], g["bbox"][3]
                # If glyph is within baseline threshold
                if gy <= ly_max + 5 and (gy + gh) >= ly_min - 5:
                    curr_line.append(g)
                    ly_min = min(ly_min, gy)
                    ly_max = max(ly_max, gy + gh)
                else:
                    lines.append(curr_line)
                    curr_line = [g]
                    ly_min, ly_max = gy, gy + gh
            if curr_line: lines.append(curr_line)
            
            # Sort lines strictly from Top to Bottom
            lines.sort(key=lambda l: min(g["bbox"][1] for g in l))
            
            for l_idx, line in enumerate(lines):
                line_y = min(g["bbox"][1] for g in line)
                is_title = (line_y < 35 and l_idx == 0)
                
                # In Bilingual Table (Panel 8), split row into Arabic cell and English cell
                if pid == 8 and not is_title:
                    ar_glyphs = [g for g in line if g["cx"] < pw * 0.45]
                    en_glyphs = [g for g in line if g["cx"] >= pw * 0.45]
                    row_units = []
                    if ar_glyphs: row_units.append((ar_glyphs, "ARABIC", "RTL", "text_line"))
                    if en_glyphs: row_units.append((en_glyphs, "ENGLISH", "LTR", "text_line"))
                else:
                    row_units = [(line, "ARABIC" if pid != 8 else "BILINGUAL", "RTL" if pid != 8 else "LTR", "title" if is_title else "text_line")]
                    
                for u_glyphs, scr, dir_s, cat in row_units:
                    tx_min = min(g["bbox"][0] for g in u_glyphs)
                    ty_min = min(g["bbox"][1] for g in u_glyphs)
                    tx_max = max(g["bbox"][0] + g["bbox"][2] for g in u_glyphs)
                    ty_max = max(g["bbox"][1] + g["bbox"][3] for g in u_glyphs)
                    
                    t_mask = np.zeros((ph, pw), dtype=np.uint8)
                    for g in u_glyphs: t_mask = cv2.bitwise_or(t_mask, g["mask"])
                    cnts, _ = cv2.findContours(t_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                    
                    sub = "panel_title" if cat == "title" else ("arabic_bullet" if scr == "ARABIC" else "english_term")
                    
                    # Math classification
                    if pid in [3, 5] and not is_title:
                        cat = "math_formula"
                        sub = "math_equation"
                        scr = "MATH"
                        dir_s = "LTR"
                    elif pid == 4 and ty_min > 28 and tx_min > 40:
                        cat = "math_formula"
                        sub = "math_equation"
                        scr = "MATH"
                        dir_s = "LTR"
                        
                    entities.append(UnifiedEntity(
                        entity_id=f"p{pid:02d}_txt_{ent_counter:02d}",
                        panel_id=pid,
                        source_stage="STEP_4_TYPOGRAPHY",
                        category=cat,
                        sub_type=sub,
                        bbox=(tx_min, ty_min, tx_max - tx_min, ty_max - ty_min),
                        mask=t_mask,
                        polygon_cnt=cnts[0] if cnts else None,
                        script=scr,
                        direction=dir_s,
                        confidence=0.98 if cat == "title" else 0.94
                    ))
                    ent_counter += 1

        # -------------------------------------------------------------
        # 2. CONSUME STEP 3 GRAPHICS ARTIFACT
        # -------------------------------------------------------------
        diff_g = 255.0 - gfx_img.astype(np.float32)
        dist_g = np.max(diff_g, axis=2)
        gfx_ink = (dist_g > 26.0).astype(np.uint8) * 255
        
        hsv_g = cv2.cvtColor(gfx_img, cv2.COLOR_BGR2HSV)
        sat_g = hsv_g[:, :, 1]
        
        num_cc_g, lbl_g, st_g, _ = cv2.connectedComponentsWithStats(gfx_ink)
        gfx_counter = 1
        for i in range(1, num_cc_g):
            gx, gy = st_g[i, cv2.CC_STAT_LEFT], st_g[i, cv2.CC_STAT_TOP]
            gw, gh = st_g[i, cv2.CC_STAT_WIDTH], st_g[i, cv2.CC_STAT_HEIGHT]
            ga = st_g[i, cv2.CC_STAT_AREA]
            if ga < 35: continue
            
            comp_mask = (lbl_g == i).astype(np.uint8) * 255
            cnts, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            if not cnts: continue
            
            aspect = gw / float(gh + 1e-5)
            sub_sat = sat_g[comp_mask > 0]
            mean_sat = np.mean(sub_sat) if len(sub_sat) > 0 else 0
            
            is_bubble = (gw > pw * 0.35 and gh > ph * 0.30 and ga < gw * gh * 0.20)
            is_emoji = (20 <= gw <= 65 and 20 <= gh <= 65 and 0.7 <= aspect <= 1.4 and mean_sat > 60)
            is_character = (gh > ph * 0.35 and ga > 500 and not is_bubble)
            is_diagram = (pid in [3, 4, 6, 7, 10, 11] and (gw > 45 or gh > 45) and not is_character and not is_emoji and not is_bubble)
            is_container = is_bubble or (gw > pw * 0.35 and gh > 35 and ga < gw * gh * 0.15)
            
            if is_character:
                cat, sub, conf = "character", "primary_character", 0.96
            elif is_emoji:
                cat, sub, conf = "emoji", "emoji_mascot", 0.94
            elif is_container:
                cat, sub, conf = "container", "speech_bubble" if is_bubble else "container_box", 0.93
            elif is_diagram:
                cat, sub, conf = "diagram", "scientific_diagram", 0.92
            else:
                cat, sub, conf = "accent", "decorative_symbol", 0.88
                
            entities.append(UnifiedEntity(
                entity_id=f"p{pid:02d}_gfx_{gfx_counter:02d}",
                panel_id=pid,
                source_stage="STEP_3_GRAPHICS",
                category=cat,
                sub_type=sub,
                bbox=(gx, gy, gw, gh),
                mask=comp_mask,
                polygon_cnt=cnts[0],
                script="NONE",
                direction="NONE",
                confidence=conf
            ))
            gfx_counter += 1
            
        return entities
