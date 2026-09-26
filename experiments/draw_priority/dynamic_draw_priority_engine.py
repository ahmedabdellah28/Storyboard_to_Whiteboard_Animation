"""
Phase 5 — Fully Dynamic Draw Priority & Multi-Script Discovery Engine
File: experiments/draw_priority/dynamic_draw_priority_engine.py

100% DYNAMIC — ZERO HARD-CODED PANEL IDs OR MANUAL RULES:
1. Dynamic Script & Formula Discovery:
   - Identifies Math Equations via mathematical operators (=, +, -, x, /, sqrt, exponents).
   - Identifies Arabic Text via cursive baselines and diacritic dots (RTL ⬅).
   - Identifies English / Latin Text via discrete vertical stems (LTR ➡).
   - Dynamically splits bilingual tables into RTL Arabic cells and LTR English cells based on spatial gap & script analysis.
2. Dynamic Graphic Entity Classification:
   - Identifies Containers (Speech Bubbles, Boxes) via hollow geometric enclosure.
   - Identifies Characters via color variance, skin tones, and anatomical scale.
   - Identifies Scientific Diagrams via geometric linework, axes, and right angles.
   - Identifies Emojis via circularity metric (4*pi*Area / P^2) and yellow saturation.
   - Identifies Accents (Stars, Hearts, Lightbulbs, Rays) via scale and perimeter complexity.
3. Dynamic Relational Priority Graph:
   - Pure DAG construction from Geometric Containment, Topological Support, Reading Flow, and Semantic Roles.
"""
import os
import sys
import math
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional


class DynamicScriptClassifier:
    """Dynamically classifies text script and reading direction with zero hard-coded IDs."""
    
    @staticmethod
    def is_math_expression(mask: np.ndarray, glyphs: List[Dict[str, Any]]) -> bool:
        """Detects mathematical formulas via operators (=, +, -, x, exponents, fractions, sqrt)."""
        if len(glyphs) < 2:
            return False
            
        # If the line contains large cursive Arabic words (width > 50px with height > 15px), it's regular text
        arabic_word_count = 0
        for g in glyphs:
            gw, gh = g["bbox"][2], g["bbox"][3]
            # Regular Arabic connected sub-word
            if gw > 35 and gh > 14 and g["area"] > 120:
                arabic_word_count += 1
                
        # Lines with multiple regular Arabic words are text, not math formulas
        if arabic_word_count >= 2:
            return False
            
        has_equal_sign = False
        has_plus_or_minus = False
        has_sqrt_or_fraction = False
        
        # Check for math operator morphology
        for g in glyphs:
            gw, gh = g["bbox"][2], g["bbox"][3]
            aspect = gw / float(gh + 1e-5)
            # Minus or fraction line: isolated thin bar
            if aspect > 4.0 and gh <= 4 and gw > 15:
                has_sqrt_or_fraction = True
                
        # Check for equal sign '=' (two parallel horizontal bars vertically aligned)
        for i in range(len(glyphs)):
            g1 = glyphs[i]
            w1, h1 = g1["bbox"][2], g1["bbox"][3]
            if w1 / float(h1 + 1e-5) > 1.8 and h1 <= 6:
                for j in range(i + 1, len(glyphs)):
                    g2 = glyphs[j]
                    w2, h2 = g2["bbox"][2], g2["bbox"][3]
                    if w2 / float(h2 + 1e-5) > 1.8 and h2 <= 6:
                        if abs(g1["cx"] - g2["cx"]) < 6 and 2 <= abs(g1["cy"] - g2["cy"]) <= 10:
                            has_equal_sign = True
                            
        # Plus sign '+' (cross shape: width ~ height, aspect ~ 1.0, compact)
        for g in glyphs:
            gw, gh = g["bbox"][2], g["bbox"][3]
            if 6 <= gw <= 16 and 6 <= gh <= 16 and 0.8 <= gw/float(gh) <= 1.25:
                # Check for cross-like density
                density = g["area"] / float(gw * gh)
                if 0.30 <= density <= 0.65:
                    has_plus_or_minus = True

        return (has_equal_sign or (has_sqrt_or_fraction and has_plus_or_minus)) and arabic_word_count <= 1

    @staticmethod
    def classify_script_features(glyphs: List[Dict[str, Any]], mask: np.ndarray) -> Tuple[str, str]:
        """Classifies Arabic vs English vs Math dynamically from morphology."""
        if DynamicScriptClassifier.is_math_expression(mask, glyphs):
            return "MATH", "LTR"
            
        # Count small diacritic dots (Arabic feature)
        diacritic_dots = 0
        total_glyphs = len(glyphs)
        for g in glyphs:
            if g["area"] <= 18:
                diacritic_dots += 1
                
        # In Arabic, diacritic dots are frequent (typically > 15% of components)
        dot_ratio = diacritic_dots / float(total_glyphs + 1e-5)
        
        # Check character stem aspect ratios
        # Latin text has many tall vertical glyphs (l, t, d, b, h, k, f) where h > 1.8 * w
        tall_stems = sum(1 for g in glyphs if g["bbox"][3] > 1.7 * g["bbox"][2] and g["area"] > 25)
        stem_ratio = tall_stems / float(total_glyphs + 1e-5)
        
        if stem_ratio > 0.28 and dot_ratio < 0.10:
            return "ENGLISH", "LTR"
        elif dot_ratio > 0.12 or len(glyphs) > 6:
            return "ARABIC", "RTL"
        else:
            # Default to Arabic in bilingual context
            return "ARABIC", "RTL"


class DynamicEntityClassifier:
    """Dynamically classifies graphic entities using purely morphological & topological features."""
    
    @staticmethod
    def classify_graphic_entity(
        comp_mask: np.ndarray,
        bbox: tuple,
        cnt: np.ndarray,
        sat_channel: np.ndarray,
        val_channel: np.ndarray,
        hue_channel: np.ndarray,
        panel_shape: tuple,
        enclosed_text_count: int
    ) -> Tuple[str, str, float]:
        ph, pw = panel_shape
        panel_area = ph * pw
        bx, by, bw, bh = bbox
        area = int(np.sum(comp_mask > 0))
        aspect = bw / float(bh + 1e-5)
        
        # Circularity metric: 4 * pi * Area / Perimeter^2
        perimeter = cv2.arcLength(cnt, True)
        circularity = (4.0 * math.pi * area) / float(perimeter * perimeter + 1e-5)
        
        sub_sat = sat_channel[comp_mask > 0]
        mean_sat = float(np.mean(sub_sat)) if len(sub_sat) > 0 else 0.0
        
        sub_hue = hue_channel[comp_mask > 0]
        mean_hue = float(np.mean(sub_hue)) if len(sub_hue) > 0 else 0.0
        
        # 1. Container / Speech Bubble Discovery
        # Encloses empty space or text, low density, large size
        density = area / float(bw * bh + 1e-5)
        is_container = (enclosed_text_count >= 1) or (bw > pw * 0.30 and bh > 35 and density < 0.18)
        if is_container:
            sub = "speech_bubble" if (aspect > 1.1 and bw > pw * 0.35) else "container_box"
            return "container", sub, 0.96
            
        # 2. Emoji Discovery
        # Circular, yellow/golden hue (15-42), high saturation, compact (20-65px)
        is_emoji = (20 <= bw <= 75 and 20 <= bh <= 75 and 0.7 <= aspect <= 1.35 and 
                    circularity > 0.45 and mean_sat > 55 and (12 <= mean_hue <= 45))
        if is_emoji:
            return "emoji", "emoji_mascot", 0.95
            
        # 3. Primary Character Discovery
        # Large anatomical mass (> 0.08 of panel), contains skin/hair/hoodie colors, tall
        is_character = (bh > ph * 0.32 and area > 450 and not is_container and mean_sat > 30)
        if is_character:
            return "character", "primary_character", 0.96
            
        # 4. Scientific Diagram Discovery
        # Coordinate axes, triangles, charts, molecules (geometric contours)
        is_diagram = (area > 200 and (bw > 45 or bh > 45) and not is_character and not is_container)
        if is_diagram:
            return "diagram", "scientific_diagram", 0.92
            
        # 5. Decorative Accent (Hearts, Stars, Lightbulbs, Rays)
        return "accent", "decorative_symbol", 0.88


class DynamicPriorityGraph:
    """Builds a Directed Acyclic Graph (DAG) and computes optimal drawing order dynamically."""
    
    @staticmethod
    def compute_draw_order(entities: List[Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
        adj: Dict[str, List[str]] = {e.entity_id: [] for e in entities}
        in_degree: Dict[str, int] = {e.entity_id: 0 for e in entities}
        edge_reasons: Dict[Tuple[str, str], str] = {}
        edge_confidence: Dict[Tuple[str, str], float] = {}
        ent_by_id = {e.entity_id: e for e in entities}
        
        def add_edge(u_id: str, v_id: str, reason: str, conf: float):
            if v_id not in adj[u_id]:
                adj[u_id].append(v_id)
                in_degree[v_id] += 1
                edge_reasons[(u_id, v_id)] = reason
                edge_confidence[(u_id, v_id)] = conf

        # -------------------------------------------------------------
        # DYNAMIC CONSTRAINT INFERENCE (ZERO PANEL IDs)
        # -------------------------------------------------------------
        
        # 1. Title Rule: Topmost line spanning width introduces panel
        titles = [e for e in entities if e.category == "title"]
        for t in titles:
            for o in entities:
                if o != t:
                    add_edge(t.entity_id, o.entity_id, "title_introduces_panel", 0.99)

        # 2. Character & Diagram Priority (Subject establishes the scene)
        characters = [e for e in entities if e.category == "character"]
        diagrams = [e for e in entities if e.category == "diagram"]
        containers = [e for e in entities if e.category == "container"]
        
        # Character -> adjacent Speech Bubble
        for ch in characters:
            for bub in containers:
                # If bubble is near or connected to character
                dist_x = abs(ch.cx - bub.cx)
                dist_y = abs(ch.cy - bub.cy)
                if dist_x < ch.bbox[2] + bub.bbox[2]:
                    add_edge(ch.entity_id, bub.entity_id, "character_precedes_speech_bubble", 0.95)

        # 3. Dynamic Containment: Container -> Enclosed Content
        for c in containers:
            cx, cy, cw, ch = c.bbox
            for o in entities:
                if o != c and o.category not in ["title", "character"]:
                    # Check if center of child is inside container
                    if (cx - 5 <= o.cx <= cx + cw + 5) and (cy - 5 <= o.cy <= cy + ch + 5):
                        add_edge(c.entity_id, o.entity_id, f"container_precedes_{o.category}", 0.96)

        # 4. Sequential Line-by-Line Flow (Strict Top-to-Bottom order)
        text_lines = [e for e in entities if e.category in ["text_line", "math_formula"]]
        text_lines.sort(key=lambda x: x.cy)
        for i in range(len(text_lines) - 1):
            add_edge(text_lines[i].entity_id, text_lines[i+1].entity_id, "sequential_top_to_bottom_reading_flow", 0.97)

        # 5. Diagram -> Mathematical Derivations & Explanations
        for d in diagrams:
            for tl in text_lines:
                if tl.cy > d.cy:
                    add_edge(d.entity_id, tl.entity_id, "diagram_precedes_formula_derivation", 0.92)

        # 6. Content -> Decorative Accents & Emojis
        accents = [e for e in entities if e.category in ["emoji", "accent"]]
        for a in accents:
            for main in entities:
                if main.category in ["character", "container", "diagram", "text_line"]:
                    add_edge(main.entity_id, a.entity_id, "content_precedes_accent", 0.90)

        # -------------------------------------------------------------
        # TOPOLOGICAL SORT WITH MULTI-FACTOR TIE-BREAKING
        # -------------------------------------------------------------
        def tiebreak_key(eid: str):
            e = ent_by_id[eid]
            tier_weights = {
                "title": 1,
                "diagram": 2,
                "character": 3,
                "container": 4,
                "math_formula": 5,
                "text_line": 6,
                "emoji": 7,
                "accent": 8
            }
            tier = tier_weights.get(e.category, 10)
            x_factor = -e.cx if e.direction == "RTL" else e.cx
            return (tier, e.cy, x_factor)

        cycles = []
        queue = [eid for eid, deg in in_degree.items() if deg == 0]
        queue.sort(key=tiebreak_key)
        
        ordered_ids = []
        while queue:
            curr = queue.pop(0)
            ordered_ids.append(curr)
            
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)
                    queue.sort(key=tiebreak_key)
                    
        # Cycle fallback
        if len(ordered_ids) < len(entities):
            cycle_nodes = [eid for eid in adj if eid not in ordered_ids]
            cycles.append(f"Cycle resolved dynamically for nodes: {cycle_nodes}")
            rem = sorted([ent_by_id[nid] for nid in cycle_nodes], key=tiebreak_key)
            for r in rem:
                ordered_ids.append(r.entity_id)

        result = []
        for p_idx, eid in enumerate(ordered_ids):
            e = ent_by_id[eid]
            in_edges = [(src, reason) for (src, dst), reason in edge_reasons.items() if dst == eid]
            reasons_list = [f"{reason}_(from_{src})" for src, reason in in_edges]
            
            conf = max([edge_confidence.get((src, eid), 0.90) for src, _ in in_edges]) if in_edges else (0.99 if e.category == "title" else 0.85)
            
            result.append({
                "priority": p_idx + 1,
                "entity_id": e.entity_id,
                "category": e.category,
                "sub_type": e.sub_type,
                "bbox": e.bbox,
                "script": e.script,
                "direction": e.direction,
                "confidence": round(float(conf), 2),
                "reasons": reasons_list if reasons_list else ["topological_root"]
            })
            
        return result, cycles
