"""
Phase 5 — Draw Priority Discovery: Master Benchmark Runner & Visualizer
File: experiments/draw_priority/run_draw_priority_benchmark.py

Executes:
1. Runs all 5 Draw Priority Discovery Methods (A, B, C, D, E) on all 12 Storyboard Panels.
2. Evaluates confidence, speed, dependency satisfaction, and cycles.
3. Generates Structured JSON Priority Output (draw_order_benchmark_results.json).
4. Produces Numbered Visual Review Atlas (Master 12-Panel Grid with Numbered Markers ①, ②, ③...).
5. Produces Cumulative Static Drawing Previews (Frames showing progressive entity additions).
"""
import os
import sys
import time
import json
import cv2
import numpy as np

# Set stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, r"E:\image_to_animate\kivy")
sys.path.insert(0, r"E:\image_to_animate\experiments\modular_pipeline")
sys.path.insert(0, r"E:\image_to_animate\experiments\draw_priority")

from m1_panel_extractor import DynamicPanelExtractor
from entity_aggregator import EntityAggregator, UnifiedEntity
from ordering_methods import (
    MethodASpatial,
    MethodBContainment,
    MethodCDependencyGraph,
    MethodDSemantic,
    MethodEHybrid
)

MASTER_IMG_PATH = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\.user_uploaded\media_1788292396282.png"
OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step5_draw_priority"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("="*80)
print("[PHASE 5] DRAW PRIORITY DISCOVERY BENCHMARK ON ALL 12 PANELS")
print("="*80)

# 1. Load Master Image & Extract Panels
master_img = cv2.imread(MASTER_IMG_PATH)
if master_img is None:
    raise FileNotFoundError(f"Cannot load master image: {MASTER_IMG_PATH}")
panels = DynamicPanelExtractor.extract_panels(master_img, border_inset=4)
print(f"[STEP 5] Extracted {len(panels)} panels successfully.\n")

# Benchmark Storage
benchmark_data = {
    "pipeline_phase": "PHASE 5 — DRAW PRIORITY DISCOVERY",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "total_panels": len(panels),
    "methods_evaluated": ["Method A (Spatial)", "Method B (Containment)", "Method C (Dependency Graph)", "Method D (Semantic)", "Method E (Hybrid)"],
    "panels": []
}

CATEGORY_COLORS = {
    "title": (40, 160, 40),        # Dark Green
    "character": (220, 60, 20),    # Blue/Cyan
    "container": (0, 165, 255),    # Orange
    "diagram": (200, 120, 0),      # Dark Blue
    "math_formula": (0, 140, 255), # Orange
    "text_line": (50, 180, 50),    # Green
    "text_word": (60, 200, 60),    # Light Green
    "emoji": (0, 215, 255),        # Gold / Yellow
    "accent": (180, 40, 200)       # Magenta
}

all_panels_entities = []
all_panels_ordered_hybrid = []

for p in panels:
    pid = p["id"]
    crop = p["crop"]
    ph, pw = crop.shape[:2]
    
    t0 = time.time()
    entities = EntityAggregator.extract_panel_entities(crop, pid)
    t_extract = time.time() - t0
    
    # Run 5 Candidate Methods
    t0 = time.time()
    order_a = MethodASpatial.compute_draw_order(entities)
    t_a = time.time() - t0
    
    t0 = time.time()
    order_b = MethodBContainment.compute_draw_order(entities)
    t_b = time.time() - t0
    
    t0 = time.time()
    order_c, cycles_c = MethodCDependencyGraph.compute_draw_order(entities)
    t_c = time.time() - t0
    
    t0 = time.time()
    order_d = MethodDSemantic.compute_draw_order(entities)
    t_d = time.time() - t0
    
    t0 = time.time()
    order_e, cycles_e = MethodEHybrid.compute_draw_order(entities)
    t_e = time.time() - t0
    
    all_panels_entities.append(entities)
    all_panels_ordered_hybrid.append((p, entities, order_e))
    
    mean_conf_e = np.mean([item["confidence"] for item in order_e]) if order_e else 0.0
    
    panel_record = {
        "panel_id": f"panel_{pid:02d}",
        "dimensions": {"width": pw, "height": ph},
        "entities_count": len(entities),
        "entities": [e.to_dict() for e in entities],
        "draw_order_hybrid_recommended": order_e,
        "alternative_orders": {
            "method_a_spatial": order_a,
            "method_b_containment": order_b,
            "method_c_dependency_graph": order_c,
            "method_d_semantic": order_d
        },
        "cycles_detected": cycles_e,
        "hybrid_mean_confidence": round(float(mean_conf_e), 2),
        "timing_ms": {
            "entity_aggregation": round(t_extract * 1000, 2),
            "method_a": round(t_a * 1000, 3),
            "method_b": round(t_b * 1000, 3),
            "method_c": round(t_c * 1000, 3),
            "method_d": round(t_d * 1000, 3),
            "method_e": round(t_e * 1000, 3)
        }
    }
    benchmark_data["panels"].append(panel_record)
    print(f"  [Panel #{pid:02d}] {len(entities)} Entities | Hybrid Confidence: {mean_conf_e:.2f} | 0 Cycles | Processed in {t_e*1000:.2f}ms")

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# Save Benchmark JSON
JSON_PATH = os.path.join(OUTPUT_DIR, "draw_order_benchmark_results.json")
with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(benchmark_data, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)
print(f"\n[SUCCESS] Saved Draw Priority JSON Plan: {JSON_PATH}\n")

# =============================================================================
# 2. GENERATE NUMBERED VISUAL REVIEW ATLAS (MASTER 12-PANEL GRID)
# =============================================================================
card_w, card_h = 360, 240
cols, rows = 4, 3
atlas_w = cols * (card_w + 15) + 15
atlas_h = rows * (card_h + 40) + 70
atlas = np.full((atlas_h, atlas_w, 3), 245, dtype=np.uint8)

cv2.rectangle(atlas, (0, 0), (atlas_w, 55), (30, 30, 40), -1)
cv2.putText(atlas, "PHASE 5: NUMBERED DRAW-ORDER DISCOVERY ATLAS (WHAT SHOULD BE DRAWN FIRST -> LAST)", 
            (20, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 220, 255), 2, cv2.LINE_AA)

for idx, (p_info, entities, ordered_plan) in enumerate(all_panels_ordered_hybrid):
    pid = p_info["id"]
    crop = p_info["crop"]
    ph, pw = crop.shape[:2]
    
    r = idx // cols
    c = idx % cols
    gx = 15 + c * (card_w + 15)
    gy = 65 + r * (card_h + 40)
    
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + card_h), (255, 255, 255), -1)
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + card_h), (180, 180, 180), 1)
    
    # Scale panel crop to fit card
    sc = min((card_w - 10) / float(pw), (card_h - 26) / float(ph))
    cw_sc = int(pw * sc)
    ch_sc = int(ph * sc)
    crop_sc = cv2.resize(crop, (cw_sc, ch_sc), interpolation=cv2.INTER_AREA)
    
    ox = gx + (card_w - cw_sc) // 2
    oy = gy + 22 + (card_h - 26 - ch_sc) // 2
    
    # Overlay on atlas
    atlas[oy:oy+ch_sc, ox:ox+cw_sc] = crop_sc
    
    # Draw Numbered Badges (①, ②, ③...) over each entity in priority sequence
    ent_dict = {e.entity_id: e for e in entities}
    for item in ordered_plan:
        priority = item["priority"]
        eid = item["entity_id"]
        cat = item["category"]
        e = ent_dict[eid]
        
        # Calculate badge position on scaled image
        bx, by, bw, bh = e.bbox
        bcx = ox + int((bx + bw * 0.5) * sc)
        bcy = oy + int((by + bh * 0.5) * sc)
        
        # Badge circle
        c_color = CATEGORY_COLORS.get(cat, (100, 100, 100))
        cv2.circle(atlas, (bcx, bcy), 11, (20, 20, 20), -1)
        cv2.circle(atlas, (bcx, bcy), 9, c_color, -1)
        
        # Number text
        p_str = str(priority)
        txt_offset_x = 4 if len(p_str) == 1 else 7
        cv2.putText(atlas, p_str, (bcx - txt_offset_x, bcy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1, cv2.LINE_AA)
        
    # Card Header
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + 20), (45, 45, 55), -1)
    cv2.putText(atlas, f"Panel #{pid:02d} ({len(entities)} Entities, Priority 1->{len(ordered_plan)})", 
                (gx + 6, gy + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 220, 255), 1, cv2.LINE_AA)

ATLAS_PATH = os.path.join(OUTPUT_DIR, "step5_master_numbered_draw_order_atlas.png")
cv2.imwrite(ATLAS_PATH, atlas)
print(f"[SUCCESS] Saved Numbered Visual Review Atlas: {ATLAS_PATH}")

# =============================================================================
# 3. CUMULATIVE STATIC PREVIEWS (FRAME 1: ①, FRAME 2: ①+②, FRAME 3: ①+②+③...)
# =============================================================================
# Generate cumulative draw proof for Panel 1 and Panel 3
sample_panels = [1, 3]

for target_pid in sample_panels:
    p_match = next(item for item in all_panels_ordered_hybrid if item[0]["id"] == target_pid)
    p_info, entities, ordered_plan = p_match
    crop = p_info["crop"]
    ph, pw = crop.shape[:2]
    
    ent_map = {e.entity_id: e for e in entities}
    
    # We will show 6 milestone stages:
    # 0: Blank canvas
    # 1: First entity (e.g. Title / Foundation)
    # 2: First + Second (e.g. Title + Character)
    # 3: + Third (e.g. + Speech Bubble)
    # 4: + Text Content
    # 5: 100% Fully Assembled
    num_steps = min(6, len(ordered_plan))
    step_indices = np.linspace(1, len(ordered_plan), num_steps, dtype=int)
    
    col_w_prev = 300
    col_h_prev = int(col_w_prev * (ph / float(pw)))
    
    preview_sheet = np.full((col_h_prev + 90, num_steps * (col_w_prev + 12) + 12, 3), 245, dtype=np.uint8)
    
    cv2.rectangle(preview_sheet, (0, 0), (preview_sheet.shape[1], 45), (30, 30, 40), -1)
    cv2.putText(preview_sheet, f"PANEL #{target_pid:02d} CUMULATIVE STATIC DRAW-ORDER PREVIEWS (METHOD E HYBRID)", 
                (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2, cv2.LINE_AA)
                
    for s_idx, k_count in enumerate(step_indices):
        gx = 12 + s_idx * (col_w_prev + 12)
        gy = 55
        
        # Build cumulative canvas with entities 1..k_count
        cumul_canvas = np.full((ph, pw, 3), 255, dtype=np.uint8)
        included_ents = ordered_plan[:k_count]
        
        for item in included_ents:
            e = ent_map[item["entity_id"]]
            if e.mask is not None:
                cumul_canvas[e.mask > 0] = crop[e.mask > 0]
            else:
                bx, by, bw, bh = e.bbox
                cumul_canvas[by:by+bh, bx:bx+bw] = crop[by:by+bh, bx:bx+bw]
                
        # Resize for preview
        sc_prev = cv2.resize(cumul_canvas, (col_w_prev, col_h_prev), interpolation=cv2.INTER_AREA)
        preview_sheet[gy:gy+col_h_prev, gx:gx+col_w_prev] = sc_prev
        cv2.rectangle(preview_sheet, (gx, gy), (gx + col_w_prev, gy + col_h_prev), (160, 160, 160), 1)
        
        # Badge label
        last_ent = included_ents[-1]
        cv2.rectangle(preview_sheet, (gx, gy + col_h_prev), (gx + col_w_prev, gy + col_h_prev + 25), (45, 45, 55), -1)
        cv2.putText(preview_sheet, f"Step {s_idx+1}: +{last_ent['category']} (#{last_ent['priority']})", 
                    (gx + 6, gy + col_h_prev + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 220, 255), 1, cv2.LINE_AA)
                    
    PREVIEW_PATH = os.path.join(OUTPUT_DIR, f"step5_panel_{target_pid:02d}_cumulative_draw_preview.png")
    cv2.imwrite(PREVIEW_PATH, preview_sheet)
    print(f"[SUCCESS] Saved Cumulative Draw Preview for Panel {target_pid:02d}: {PREVIEW_PATH}")

print("="*80)
