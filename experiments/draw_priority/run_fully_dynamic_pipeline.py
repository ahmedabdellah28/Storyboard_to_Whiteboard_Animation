"""
Phase 5 — Run Fully Dynamic Draw Priority Pipeline
File: experiments/draw_priority/run_fully_dynamic_pipeline.py

100% DYNAMIC EXECUTION:
- Zero hard-coded panel IDs (no 'if pid == 8', no 'if pid in [3, 5]').
- Consumes exclusively the outputs of Step 3 (Graphics) and Step 4 (Typography).
- Discovers scripts, formulas, entities, and drawing order dynamically.
"""
import os
import sys
import json
import cv2
import numpy as np

# Set stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, r"E:\image_to_animate\experiments\draw_priority")
from dynamic_draw_priority_engine import (
    DynamicScriptClassifier,
    DynamicEntityClassifier,
    DynamicPriorityGraph
)

PIPELINE_RESULTS_DIR = r"E:\image_to_animate\experiments\results\all_12_panels_pipeline"
OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step5_draw_priority"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class DynamicUnifiedEntity:
    def __init__(self, entity_id, panel_id, source_stage, category, sub_type, bbox, mask, polygon_cnt=None, script="NONE", direction="NONE", confidence=1.0):
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

    def to_dict(self):
        return {
            "entity_id": self.entity_id,
            "category": self.category,
            "sub_type": self.sub_type,
            "bbox": self.bbox,
            "centroid": (round(self.cx, 1), round(self.cy, 1)),
            "area": self.area,
            "script": self.script,
            "direction": self.direction,
            "confidence": round(self.confidence, 2)
        }

def process_panel_dynamically(pid: int):
    """Processes a panel purely from its Step 3 & Step 4 images with ZERO hardcoded rules."""
    p_dir = os.path.join(PIPELINE_RESULTS_DIR, f"panel_{pid:02d}")
    gfx_path = os.path.join(p_dir, f"p{pid:02d}_01_graphics.png")
    txt_path = os.path.join(p_dir, f"p{pid:02d}_02_typography.png")
    
    gfx_img = cv2.imread(gfx_path)
    txt_img = cv2.imread(txt_path)
    ph, pw = gfx_img.shape[:2]
    
    # 1. Extract Text Entities from Step 4
    diff_t = 255.0 - txt_img.astype(np.float32)
    txt_ink = (np.max(diff_t, axis=2) > 26.0).astype(np.uint8) * 255
    num_cc_t, lbl_t, st_t, _ = cv2.connectedComponentsWithStats(txt_ink)
    
    glyphs = []
    for i in range(1, num_cc_t):
        gx, gy, gw, gh = st_t[i, cv2.CC_STAT_LEFT], st_t[i, cv2.CC_STAT_TOP], st_t[i, cv2.CC_STAT_WIDTH], st_t[i, cv2.CC_STAT_HEIGHT]
        ga = st_t[i, cv2.CC_STAT_AREA]
        if ga < 2: continue
        glyphs.append({
            "bbox": (gx, gy, gw, gh),
            "cx": gx + gw / 2.0, "cy": gy + gh / 2.0,
            "area": ga, "mask": (lbl_t == i).astype(np.uint8) * 255
        })
        
    text_entities = []
    ent_counter = 1
    
    if glyphs:
        glyphs.sort(key=lambda g: g["cy"])
        lines = []
        curr_line = [glyphs[0]]
        ly_min, ly_max = glyphs[0]["bbox"][1], glyphs[0]["bbox"][1] + glyphs[0]["bbox"][3]
        for g in glyphs[1:]:
            gy, gh = g["bbox"][1], g["bbox"][3]
            if gy <= ly_max + 5 and (gy + gh) >= ly_min - 5:
                curr_line.append(g)
                ly_min = min(ly_min, gy)
                ly_max = max(ly_max, gy + gh)
            else:
                lines.append(curr_line)
                curr_line = [g]
                ly_min, ly_max = gy, gy + gh
        if curr_line: lines.append(curr_line)
        lines.sort(key=lambda l: min(g["bbox"][1] for g in l))
        
        for l_idx, line in enumerate(lines):
            line_y = min(g["bbox"][1] for g in line)
            is_title = (line_y < 35 and l_idx == 0)
            
            # Dynamic Column / Table Detection (checks for large horizontal gap dx > 20px)
            line.sort(key=lambda g: g["bbox"][0])
            gap_split_idx = -1
            for g_i in range(len(line) - 1):
                gap = line[g_i+1]["bbox"][0] - (line[g_i]["bbox"][0] + line[g_i]["bbox"][2])
                if gap > 20:
                    gap_split_idx = g_i + 1
                    break
                    
            if gap_split_idx > 0 and not is_title:
                part1 = line[:gap_split_idx]
                part2 = line[gap_split_idx:]
                parts = [part1, part2]
            else:
                parts = [line]
                
            for p_glyphs in parts:
                tx_min = min(g["bbox"][0] for g in p_glyphs)
                ty_min = min(g["bbox"][1] for g in p_glyphs)
                tx_max = max(g["bbox"][0] + g["bbox"][2] for g in p_glyphs)
                ty_max = max(g["bbox"][1] + g["bbox"][3] for g in p_glyphs)
                
                t_mask = np.zeros((ph, pw), dtype=np.uint8)
                for g in p_glyphs: t_mask = cv2.bitwise_or(t_mask, g["mask"])
                cnts, _ = cv2.findContours(t_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                
                # Dynamic Script Classification
                script, direction = DynamicScriptClassifier.classify_script_features(p_glyphs, t_mask)
                
                cat = "title" if is_title else ("math_formula" if script == "MATH" else "text_line")
                sub = "panel_title" if is_title else ("math_expression" if script == "MATH" else f"{script.lower()}_text")
                
                text_entities.append(DynamicUnifiedEntity(
                    entity_id=f"p{pid:02d}_txt_{ent_counter:02d}",
                    panel_id=pid,
                    source_stage="STEP_4_TYPOGRAPHY",
                    category=cat,
                    sub_type=sub,
                    bbox=(tx_min, ty_min, tx_max - tx_min, ty_max - ty_min),
                    mask=t_mask,
                    polygon_cnt=cnts[0] if cnts else None,
                    script=script,
                    direction=direction,
                    confidence=0.98 if is_title else 0.94
                ))
                ent_counter += 1

    # 2. Extract Graphic Entities from Step 3
    diff_g = 255.0 - gfx_img.astype(np.float32)
    gfx_ink = (np.max(diff_g, axis=2) > 26.0).astype(np.uint8) * 255
    
    hsv_g = cv2.cvtColor(gfx_img, cv2.COLOR_BGR2HSV)
    sat_g = hsv_g[:, :, 1]
    val_g = hsv_g[:, :, 2]
    hue_g = hsv_g[:, :, 0]
    
    num_cc_g, lbl_g, st_g, _ = cv2.connectedComponentsWithStats(gfx_ink)
    graphic_entities = []
    gfx_counter = 1
    
    for i in range(1, num_cc_g):
        gx, gy, gw, gh = st_g[i, cv2.CC_STAT_LEFT], st_g[i, cv2.CC_STAT_TOP], st_g[i, cv2.CC_STAT_WIDTH], st_g[i, cv2.CC_STAT_HEIGHT]
        ga = st_g[i, cv2.CC_STAT_AREA]
        if ga < 35: continue
        
        comp_mask = (lbl_g == i).astype(np.uint8) * 255
        cnts, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not cnts: continue
        
        # Count how many text entities are geometrically enclosed inside this graphic component
        enclosed_cnt = 0
        for te in text_entities:
            if gx <= te.cx <= gx + gw and gy <= te.cy <= gy + gh:
                enclosed_cnt += 1
                
        # 100% Dynamic Classification
        cat, sub, conf = DynamicEntityClassifier.classify_graphic_entity(
            comp_mask=comp_mask,
            bbox=(gx, gy, gw, gh),
            cnt=cnts[0],
            sat_channel=sat_g,
            val_channel=val_g,
            hue_channel=hue_g,
            panel_shape=(ph, pw),
            enclosed_text_count=enclosed_cnt
        )
        
        graphic_entities.append(DynamicUnifiedEntity(
            entity_id=f"p{pid:02d}_gfx_{gfx_counter:02d}",
            panel_id=pid,
            source_stage="STEP_3_GRAPHICS",
            category=cat,
            sub_type=sub,
            bbox=(gx, gy, gw, gh),
            mask=comp_mask,
            polygon_cnt=cnts[0],
            confidence=conf
        ))
        gfx_counter += 1
        
    all_entities = text_entities + graphic_entities
    
    # 3. Dynamic Priority Graph & Topological Ordering
    ordered_plan, cycles = DynamicPriorityGraph.compute_draw_order(all_entities)
    
    # Composite Canvas for visualization
    composite_canvas = np.full_like(gfx_img, 255)
    composite_canvas[gfx_ink > 0] = gfx_img[gfx_ink > 0]
    composite_canvas[txt_ink > 0] = txt_img[txt_ink > 0]
    
    return {
        "panel_id": pid,
        "composite_canvas": composite_canvas,
        "shape": (ph, pw),
        "entities": all_entities,
        "ordered_plan": ordered_plan,
        "cycles": cycles
    }

# Run dynamically on all 12 panels
print("="*80)
print("[FULLY DYNAMIC] PROCESSING ALL 12 PANELS (ZERO HARDCODED IDs)")
print("="*80)

all_panels_dynamic_results = []
json_records = []

for pid in range(1, 13):
    res = process_panel_dynamically(pid)
    all_panels_dynamic_results.append(res)
    
    json_records.append({
        "panel_id": f"panel_{pid:02d}",
        "entities_count": len(res["entities"]),
        "draw_order_dynamic": res["ordered_plan"],
        "cycles_resolved": res["cycles"]
    })
    
    # Print dynamic stats
    types_str = ", ".join([f"{item['priority']}:{item['category']}" for item in res["ordered_plan"][:6]])
    print(f"  [Panel #{pid:02d}] {len(res['entities'])} Entities | Sequence: {types_str} ... | Cycles: {len(res['cycles'])}")

# Save JSON
class DynamicEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

JSON_OUT = os.path.join(OUTPUT_DIR, "fully_dynamic_draw_order.json")
with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump({"execution_mode": "100%_DYNAMIC_ZERO_HARDCODING", "panels": json_records}, f, indent=2, cls=DynamicEncoder)
print(f"\n[SUCCESS] Saved 100% Dynamic JSON: {JSON_OUT}")

# ----------------- BUILD 100% DYNAMIC NUMBERED ATLAS -----------------
card_w, card_h = 360, 240
cols, rows = 4, 3
atlas_w = cols * (card_w + 15) + 15
atlas_h = rows * (card_h + 40) + 75
atlas = np.full((atlas_h, atlas_w, 3), 245, dtype=np.uint8)

cv2.rectangle(atlas, (0, 0), (atlas_w, 60), (20, 35, 45), -1) # Sleek Dark Teal
cv2.putText(atlas, "PHASE 5 — 100% DYNAMIC DRAW PRIORITY ATLAS (ZERO HARDCODED IDs)", 
            (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 220, 255), 2, cv2.LINE_AA)

CATEGORY_COLORS = {
    "title": (40, 160, 40),
    "character": (220, 60, 20),
    "container": (0, 165, 255),
    "diagram": (200, 120, 0),
    "math_formula": (0, 140, 255),
    "text_line": (50, 180, 50),
    "emoji": (0, 215, 255),
    "accent": (180, 40, 200)
}

for idx, p_res in enumerate(all_panels_dynamic_results):
    pid = p_res["panel_id"]
    composite_c = p_res["composite_canvas"]
    ph, pw = p_res["shape"]
    entities = p_res["entities"]
    ordered_plan = p_res["ordered_plan"]
    
    r = idx // cols
    c = idx % cols
    gx = 15 + c * (card_w + 15)
    gy = 70 + r * (card_h + 40)
    
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + card_h), (255, 255, 255), -1)
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + card_h), (0, 180, 220), 2)
    
    sc = min((card_w - 10) / float(pw), (card_h - 26) / float(ph))
    cw_sc = int(pw * sc)
    ch_sc = int(ph * sc)
    crop_sc = cv2.resize(composite_c, (cw_sc, ch_sc), interpolation=cv2.INTER_AREA)
    
    ox = gx + (card_w - cw_sc) // 2
    oy = gy + 22 + (card_h - 26 - ch_sc) // 2
    atlas[oy:oy+ch_sc, ox:ox+cw_sc] = crop_sc
    
    ent_map = {e.entity_id: e for e in entities}
    
    for item in ordered_plan:
        priority = item["priority"]
        eid = item["entity_id"]
        cat = item["category"]
        e = ent_map[eid]
        
        bx, by, bw, bh = e.bbox
        bcx = ox + int((bx + bw * 0.5) * sc)
        bcy = oy + int((by + bh * 0.5) * sc)
        
        c_color = CATEGORY_COLORS.get(cat, (100, 100, 100))
        cv2.circle(atlas, (bcx, bcy), 11, (20, 20, 20), -1)
        cv2.circle(atlas, (bcx, bcy), 9, c_color, -1)
        
        p_str = str(priority)
        txt_offset_x = 4 if len(p_str) == 1 else 7
        cv2.putText(atlas, p_str, (bcx - txt_offset_x, bcy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1, cv2.LINE_AA)
        
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + 20), (30, 45, 50), -1)
    cv2.putText(atlas, f"Panel #{pid:02d} [100% DYNAMIC: {len(entities)} Ent]", (gx + 6, gy + 14), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 220, 255), 1, cv2.LINE_AA)

ATLAS_OUT = os.path.join(OUTPUT_DIR, "step5_fully_dynamic_draw_order_atlas.png")
cv2.imwrite(ATLAS_OUT, atlas)
print(f"[SUCCESS] Saved Fully Dynamic Atlas: {ATLAS_OUT}")
print("="*80 + "\n")
