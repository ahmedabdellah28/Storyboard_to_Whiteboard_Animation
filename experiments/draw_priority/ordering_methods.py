"""
Phase 5 — Candidate Draw Priority Methods (A, B, C, D, E)
File: experiments/draw_priority/ordering_methods.py

Implements 5 candidate draw-priority discovery algorithms:
- Method A: Spatial Ordering (Y-band + RTL/LTR reading flow)
- Method B: Containment Hierarchy (Parent container -> Contained children)
- Method C: Visual Dependency Graph (Directed edges + Topological sort with Cycle Detection)
- Method D: Semantic Category Ordering (Title -> Diagram/Character -> Container -> Text -> Accent)
- Method E: Hybrid Multi-Factor Constraint Satisfaction (DAG + Containment + Semantics + Spatial Flow)
"""
import math
from typing import List, Dict, Any, Tuple
import numpy as np
from entity_aggregator import UnifiedEntity


# =============================================================================
# METHOD A: SPATIAL ORDERING
# =============================================================================
class MethodASpatial:
    @staticmethod
    def compute_draw_order(entities: List[UnifiedEntity]) -> List[Dict[str, Any]]:
        """Sorts strictly by spatial coordinates (Top-to-Bottom Y bands, with RTL/LTR flow)."""
        # Band height = 30px
        def sort_key(e: UnifiedEntity):
            y_band = int(e.cy / 35.0)
            # If Arabic RTL, flow Right-to-Left (-cx); if English/Math, flow Left-to-Right (+cx)
            x_factor = -e.cx if e.direction == "RTL" else e.cx
            return (y_band, x_factor)
            
        sorted_ents = sorted(entities, key=sort_key)
        
        result = []
        for p_idx, e in enumerate(sorted_ents):
            result.append({
                "priority": p_idx + 1,
                "entity_id": e.entity_id,
                "category": e.category,
                "sub_type": e.sub_type,
                "bbox": e.bbox,
                "confidence": 0.65,
                "reasons": [f"spatial_y_band_{int(e.cy/35.0)}", f"x_coord_{round(e.cx,1)}"]
            })
        return result


# =============================================================================
# METHOD B: CONTAINMENT HIERARCHY
# =============================================================================
class MethodBContainment:
    @staticmethod
    def compute_draw_order(entities: List[UnifiedEntity]) -> List[Dict[str, Any]]:
        """Sorts based on Container -> Child containment relationships."""
        # Detect containment
        containers = [e for e in entities if e.category in ["container", "title"]]
        non_containers = [e for e in entities if e not in containers]
        
        containment_map: Dict[str, List[UnifiedEntity]] = {c.entity_id: [] for c in containers}
        uncontained = []
        
        for e in non_containers:
            parent = None
            ex, ey, ew, eh = e.bbox
            for c in containers:
                cx, cy, cw, ch = c.bbox
                if cx <= ex and cy <= ey and (cx + cw) >= (ex + ew) and (cy + ch) >= (ey + eh):
                    parent = c
                    break
            if parent:
                containment_map[parent.entity_id].append(e)
            else:
                uncontained.append(e)
                
        # Sequence: Containers first, then their enclosed children, then uncontained
        ordered_list = []
        reasons_map = {}
        
        for c in containers:
            ordered_list.append(c)
            reasons_map[c.entity_id] = ["container_parent_priority"]
            # Add enclosed children sorted by Y
            children = sorted(containment_map[c.entity_id], key=lambda x: x.cy)
            for ch in children:
                ordered_list.append(ch)
                reasons_map[ch.entity_id] = [f"enclosed_by_{c.entity_id}"]
                
        for u in sorted(uncontained, key=lambda x: (x.cy, x.cx)):
            ordered_list.append(u)
            reasons_map[u.entity_id] = ["uncontained_spatial_order"]
            
        result = []
        for p_idx, e in enumerate(ordered_list):
            result.append({
                "priority": p_idx + 1,
                "entity_id": e.entity_id,
                "category": e.category,
                "sub_type": e.sub_type,
                "bbox": e.bbox,
                "confidence": 0.75 if "enclosed_by" in reasons_map[e.entity_id][0] else 0.60,
                "reasons": reasons_map[e.entity_id]
            })
        return result


# =============================================================================
# METHOD C: VISUAL DEPENDENCY GRAPH (DAG + TOPOLOGICAL SORT + CYCLE DETECTION)
# =============================================================================
class MethodCDependencyGraph:
    @staticmethod
    def compute_draw_order(entities: List[UnifiedEntity]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Builds directed dependency graph and solves via Topological Sort with Cycle Detection."""
        # Nodes = entity_ids
        adj: Dict[str, List[str]] = {e.entity_id: [] for e in entities}
        in_degree: Dict[str, int] = {e.entity_id: 0 for e in entities}
        reasons_edge: Dict[Tuple[str, str], str] = {}
        ent_by_id = {e.entity_id: e for e in entities}
        
        # Rule 1: Title introduces panel (Title -> all other entities)
        titles = [e for e in entities if e.category == "title"]
        for t in titles:
            for other in entities:
                if other != t:
                    adj[t.entity_id].append(other.entity_id)
                    in_degree[other.entity_id] += 1
                    reasons_edge[(t.entity_id, other.entity_id)] = "title_introduces_content"
                    
        # Rule 2: Container -> Contained Text
        containers = [e for e in entities if e.category == "container"]
        for c in containers:
            cx, cy, cw, ch = c.bbox
            for other in entities:
                if other != c and other.category in ["text_word", "text_line", "math_formula"]:
                    ox, oy, ow, oh = other.bbox
                    if (cx - 10 <= ox and cy - 10 <= oy and (cx + cw + 10) >= (ox + ow) and (cy + ch + 10) >= (oy + oh)):
                        if other.entity_id not in adj[c.entity_id]:
                            adj[c.entity_id].append(other.entity_id)
                            in_degree[other.entity_id] += 1
                            reasons_edge[(c.entity_id, other.entity_id)] = "container_precedes_content"

        # Rule 3: Main Character -> Speech Bubble
        characters = [e for e in entities if e.category == "character"]
        for ch in characters:
            for bub in containers:
                if "bubble" in bub.sub_type and bub.entity_id not in adj[ch.entity_id]:
                    adj[ch.entity_id].append(bub.entity_id)
                    in_degree[bub.entity_id] += 1
                    reasons_edge[(ch.entity_id, bub.entity_id)] = "character_speaks_bubble"

        # Rule 4: Diagram / Axes -> Math Formulas / Annotations
        diagrams = [e for e in entities if e.category == "diagram"]
        for d in diagrams:
            for m in entities:
                if m.category in ["math_formula", "text_word"] and m.cy > d.cy:
                    if m.entity_id not in adj[d.entity_id]:
                        adj[d.entity_id].append(m.entity_id)
                        in_degree[m.entity_id] += 1
                        reasons_edge[(d.entity_id, m.entity_id)] = "diagram_establishes_formula"

        # Rule 5: Main Content -> Emojis & Decorative Accents
        accents = [e for e in entities if e.category in ["emoji", "accent"]]
        for a in accents:
            for main_e in entities:
                if main_e.category in ["character", "diagram", "title"]:
                    if a.entity_id not in adj[main_e.entity_id]:
                        adj[main_e.entity_id].append(a.entity_id)
                        in_degree[a.entity_id] += 1
                        reasons_edge[(main_e.entity_id, a.entity_id)] = "content_precedes_accent"

        # Cycle Detection & Kahn's Topological Sort
        cycles_reported = []
        queue = [e_id for e_id, deg in in_degree.items() if deg == 0]
        # Secondary sort by Y-coord to break ties deterministically
        queue.sort(key=lambda eid: (ent_by_id[eid].cy, ent_by_id[eid].cx))
        
        ordered_ids = []
        while queue:
            curr = queue.pop(0)
            ordered_ids.append(curr)
            
            # Sort neighbors by spatial position before pushing
            neighbors = sorted(adj[curr], key=lambda nid: (ent_by_id[nid].cy, ent_by_id[nid].cx))
            for nxt in neighbors:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)
                    queue.sort(key=lambda eid: (ent_by_id[eid].cy, ent_by_id[eid].cx))
                    
        # Check for remaining cycle nodes
        if len(ordered_ids) < len(entities):
            cycle_nodes = [e_id for e_id in adj if e_id not in ordered_ids]
            cycles_reported.append(f"Cycle detected among nodes: {cycle_nodes}")
            # Break cycle using spatial fallback
            remaining = sorted([ent_by_id[nid] for nid in cycle_nodes], key=lambda x: (x.cy, x.cx))
            for rem in remaining:
                ordered_ids.append(rem.entity_id)

        result = []
        for p_idx, eid in enumerate(ordered_ids):
            e = ent_by_id[eid]
            incoming_reasons = [reason for (src, dst), reason in reasons_edge.items() if dst == eid]
            result.append({
                "priority": p_idx + 1,
                "entity_id": e.entity_id,
                "category": e.category,
                "sub_type": e.sub_type,
                "bbox": e.bbox,
                "confidence": 0.88 if incoming_reasons else 0.70,
                "reasons": incoming_reasons if incoming_reasons else ["topological_root_or_tiebreak"]
            })
        return result, cycles_reported


# =============================================================================
# METHOD D: SEMANTIC CATEGORY ORDERING
# =============================================================================
class MethodDSemantic:
    CATEGORY_TIERS = {
        "title": 1,
        "diagram": 2,
        "character": 3,
        "container": 4,
        "math_formula": 5,
        "text_line": 6,
        "text_word": 7,
        "emoji": 8,
        "accent": 9
    }
    
    @staticmethod
    def compute_draw_order(entities: List[UnifiedEntity]) -> List[Dict[str, Any]]:
        """Sorts primarily by semantic category role hierarchy, then by spatial reading order."""
        def semantic_key(e: UnifiedEntity):
            tier = MethodDSemantic.CATEGORY_TIERS.get(e.category, 10)
            x_factor = -e.cx if e.direction == "RTL" else e.cx
            return (tier, e.cy, x_factor)
            
        sorted_ents = sorted(entities, key=semantic_key)
        
        result = []
        for p_idx, e in enumerate(sorted_ents):
            tier = MethodDSemantic.CATEGORY_TIERS.get(e.category, 10)
            result.append({
                "priority": p_idx + 1,
                "entity_id": e.entity_id,
                "category": e.category,
                "sub_type": e.sub_type,
                "bbox": e.bbox,
                "confidence": 0.82,
                "reasons": [f"semantic_tier_{tier}_{e.category}", f"spatial_y_{round(e.cy,1)}"]
            })
        return result


# =============================================================================
# METHOD E: HYBRID MULTI-FACTOR CONSTRAINT SATISFACTION (RECOMMENDED)
# =============================================================================
class MethodEHybrid:
    @staticmethod
    def compute_draw_order(entities: List[UnifiedEntity]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Combines Topological Dependency Graph + Containment Constraints + 
        Semantic Hierarchy + Reading Direction Flow (RTL/LTR) + Tiebreak Stability.
        """
        ent_by_id = {e.entity_id: e for e in entities}
        
        # 1. Dependency Edges (u -> v: u must be drawn before v)
        adj: Dict[str, List[str]] = {e.entity_id: [] for e in entities}
        in_degree: Dict[str, int] = {e.entity_id: 0 for e in entities}
        edge_reasons: Dict[Tuple[str, str], str] = {}
        edge_confidence: Dict[Tuple[str, str], float] = {}
        
        def add_edge(u_id: str, v_id: str, reason: str, conf: float):
            if v_id not in adj[u_id]:
                adj[u_id].append(v_id)
                in_degree[v_id] += 1
                edge_reasons[(u_id, v_id)] = reason
                edge_confidence[(u_id, v_id)] = conf

        # Factor A: Title introduces entire panel
        titles = [e for e in entities if e.category == "title"]
        for t in titles:
            for o in entities:
                if o != t:
                    add_edge(t.entity_id, o.entity_id, "title_introduces_panel", 0.98)

        # Factor B: Character & Main Diagram Priority
        characters = [e for e in entities if e.category == "character"]
        diagrams = [e for e in entities if e.category == "diagram"]
        containers = [e for e in entities if e.category == "container"]
        
        # Character -> Speech Bubble
        for ch in characters:
            for bub in containers:
                add_edge(ch.entity_id, bub.entity_id, "character_precedes_speech_bubble", 0.95)
                
        # Factor C: Container -> Enclosed First Text Line
        # And Factor D: LINE-TO-LINE STRICT TOP-TO-BOTTOM SEQUENTIAL ORDER!
        text_lines = [e for e in entities if e.category in ["text_line", "math_formula"]]
        text_lines.sort(key=lambda x: x.cy)
        
        # Connect text lines sequentially: Line 1 -> Line 2 -> Line 3 -> Line 4
        for i in range(len(text_lines) - 1):
            curr_l = text_lines[i]
            next_l = text_lines[i+1]
            add_edge(curr_l.entity_id, next_l.entity_id, "sequential_reading_order_top_to_bottom", 0.96)
            
        # Container precedes its enclosed lines
        for c in containers:
            cx, cy, cw, ch = c.bbox
            for tl in text_lines:
                if (cx <= tl.cx <= cx + cw) and (cy <= tl.cy <= cy + ch):
                    add_edge(c.entity_id, tl.entity_id, "container_precedes_enclosed_text", 0.94)

        # Factor E: Main Diagram -> Mathematical Formulas & Text Annotations
        for d in diagrams:
            for tl in text_lines:
                if tl.cy > d.cy:
                    add_edge(d.entity_id, tl.entity_id, "diagram_precedes_math_derivation", 0.92)

        # Factor F: Accents & Emojis are drawn at the very end of the panel
        accents = [e for e in entities if e.category in ["emoji", "accent"]]
        for a in accents:
            for main in entities:
                if main.category in ["character", "container", "text_line", "math_formula", "diagram"]:
                    add_edge(main.entity_id, a.entity_id, "content_precedes_decorative_accent", 0.90)

        # 2. Topological Sort with Multi-Objective Priority Queue
        # Tiebreak score: (Semantic Tier, Y position, RTL/LTR X position)
        def tiebreak_key(eid: str):
            e = ent_by_id[eid]
            tier_weights = {
                "title": 1,
                "diagram": 2,
                "character": 3,
                "container": 4,
                "math_formula": 5,
                "text_line": 6,
                "text_word": 7,
                "emoji": 8,
                "accent": 9
            }
            tier = tier_weights.get(e.category, 10)
            x_val = -e.cx if e.direction == "RTL" else e.cx
            return (tier, e.cy, x_val)

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
            cycles.append(f"Cycle resolved for nodes: {cycle_nodes}")
            rem = sorted([ent_by_id[nid] for nid in cycle_nodes], key=tiebreak_key)
            for r in rem:
                ordered_ids.append(r.entity_id)

        result = []
        for p_idx, eid in enumerate(ordered_ids):
            e = ent_by_id[eid]
            in_edges = [(src, reason) for (src, dst), reason in edge_reasons.items() if dst == eid]
            reasons_list = [f"{reason}_(from_{src})" for src, reason in in_edges]
            
            # Confidence score calculation
            if in_edges:
                conf = max([edge_confidence.get((src, eid), 0.85) for src, _ in in_edges])
            else:
                conf = 0.95 if e.category == "title" else 0.80
                reasons_list = [f"topological_root_{e.category}"]
                
            result.append({
                "priority": p_idx + 1,
                "entity_id": e.entity_id,
                "category": e.category,
                "sub_type": e.sub_type,
                "bbox": e.bbox,
                "confidence": round(conf, 2),
                "reasons": reasons_list
            })
            
        return result, cycles
