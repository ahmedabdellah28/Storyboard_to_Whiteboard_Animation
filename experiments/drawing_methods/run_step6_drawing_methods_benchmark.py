"""
Phase 6 — Drawing Method Discovery Benchmark Runner
File: experiments/drawing_methods/run_step6_drawing_methods_benchmark.py

Executes Step 6:
1. Takes the validated drawing order from Step 5.
2. Assigns physical drawing methods to every entity (Character Hatching, RTL Arabic, LTR English, Math Geometry).
3. Produces:
   - Visual Drawing Methods Atlas for all 12 panels.
   - Vector Trajectory & Zig-Zag Hatching (حركة متعرجة) close-up inspection sheet.
   - Structured JSON plan (drawing_methods_plan.json).
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
sys.path.insert(0, r"E:\image_to_animate\experiments\drawing_methods")

from downstream_artifact_consumer import DownstreamArtifactConsumer
from drawing_method_classifier import DrawingMethodClassifier, DrawingMethodType

INPUT_JSON_PATH = r"E:\image_to_animate\experiments\results\step5_draw_priority\validated_draw_order.json"
OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step6_drawing_methods"
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(INPUT_JSON_PATH, "r", encoding="utf-8") as f:
    step5_data = json.load(f)

print("="*80)
print("[PHASE 6] DRAWING METHOD DISCOVERY BENCHMARK ON ALL 12 PANELS")
print("="*80)

all_classified_panels = []
plan_output = {"phase": "PHASE 6 — DRAWING METHOD DISCOVERY", "panels": []}

METHOD_BADGE_COLORS = {
    DrawingMethodType.CHARACTER_HATCH: (220, 60, 20),     # Blue/Cyan
    DrawingMethodType.HANDWRITING_RTL: (40, 180, 40),     # Green
    DrawingMethodType.HANDWRITING_LTR: (220, 100, 40),    # Blue
    DrawingMethodType.MATH_NOTATION: (0, 140, 255),       # Orange
    DrawingMethodType.GEOMETRIC_DIAGRAM: (180, 120, 20),  # Dark Blue
    DrawingMethodType.CONTAINER_LOOP: (0, 165, 255),      # Amber/Orange
    DrawingMethodType.RADIAL_EMOJI: (0, 215, 255),        # Yellow/Gold
    DrawingMethodType.GESTURAL_ACCENT: (180, 40, 200)     # Magenta
}

METHOD_ABBR = {
    DrawingMethodType.CHARACTER_HATCH: "HATCH (حركة متعرجة)",
    DrawingMethodType.HANDWRITING_RTL: "RTL ⬅ (خط عربي)",
    DrawingMethodType.HANDWRITING_LTR: "LTR ➡ (English)",
    DrawingMethodType.MATH_NOTATION: "MATH ➡ (معادلات)",
    DrawingMethodType.GEOMETRIC_DIAGRAM: "GEOM (هندسي)",
    DrawingMethodType.CONTAINER_LOOP: "LOOP (إطار مغلق)",
    DrawingMethodType.RADIAL_EMOJI: "EMOJI (تعبيري)",
    DrawingMethodType.GESTURAL_ACCENT: "ACCENT (زخرفي)"
}

for p_rec in step5_data["panels"]:
    pid = int(p_rec["panel_id"].split("_")[1])
    panel_data = DownstreamArtifactConsumer.load_panel_artifacts(pid)
    ordered_plan = p_rec["draw_order_validated"]
    
    panel_methods = []
    for item in ordered_plan:
        method_meta = DrawingMethodClassifier.assign_drawing_method(item, panel_data["shape"])
        method_meta["priority"] = item["priority"]
        panel_methods.append(method_meta)
        
    all_classified_panels.append({
        "panel_id": pid,
        "panel_data": panel_data,
        "methods": panel_methods
    })
    
    plan_output["panels"].append({
        "panel_id": f"panel_{pid:02d}",
        "entities_count": len(panel_methods),
        "drawing_plan": panel_methods
    })
    print(f"  [Panel #{pid:02d}] Classified {len(panel_methods)} entities into physical drawing methods.")

# Save Plan JSON
PLAN_JSON_PATH = os.path.join(OUTPUT_DIR, "drawing_methods_plan.json")
with open(PLAN_JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(plan_output, f, indent=2, ensure_ascii=False)
print(f"\n[SUCCESS] Saved Drawing Methods Plan: {PLAN_JSON_PATH}")

# ----------------- 1. GENERATE VISUAL DRAWING METHODS ATLAS -----------------
card_w, card_h = 360, 240
cols, rows = 4, 3
atlas_w = cols * (card_w + 15) + 15
atlas_h = rows * (card_h + 40) + 75
atlas = np.full((atlas_h, atlas_w, 3), 245, dtype=np.uint8)

cv2.rectangle(atlas, (0, 0), (atlas_w, 60), (35, 30, 20), -1) # Dark Bronze
cv2.putText(atlas, "PHASE 6 — DRAWING METHOD DISCOVERY ATLAS (HOW EACH ENTITY IS DRAWN)", 
            (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 220, 255), 2, cv2.LINE_AA)

for idx, p_info in enumerate(all_classified_panels):
    pid = p_info["panel_id"]
    composite_c = p_info["panel_data"]["composite_canvas"]
    ph, pw = p_info["panel_data"]["shape"]
    methods = p_info["methods"]
    
    r = idx // cols
    c = idx % cols
    gx = 15 + c * (card_w + 15)
    gy = 70 + r * (card_h + 40)
    
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + card_h), (255, 255, 255), -1)
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + card_h), (180, 160, 120), 2)
    
    sc = min((card_w - 10) / float(pw), (card_h - 26) / float(ph))
    cw_sc = int(pw * sc)
    ch_sc = int(ph * sc)
    crop_sc = cv2.resize(composite_c, (cw_sc, ch_sc), interpolation=cv2.INTER_AREA)
    
    ox = gx + (card_w - cw_sc) // 2
    oy = gy + 22 + (card_h - 26 - ch_sc) // 2
    atlas[oy:oy+ch_sc, ox:ox+cw_sc] = crop_sc
    
    # Overlay Method Markers and Trajectory Vectors
    for m in methods:
        p_num = m["priority"]
        m_type = m["drawing_method"]
        sp = m["start_point"]
        ep = m["end_point"]
        
        # Calculate badge on scaled image
        bcx = ox + int(sp[0] * sc)
        bcy = oy + int(sp[1] * sc)
        
        c_color = METHOD_BADGE_COLORS.get(m_type, (120, 120, 120))
        cv2.circle(atlas, (bcx, bcy), 11, (20, 20, 20), -1)
        cv2.circle(atlas, (bcx, bcy), 9, c_color, -1)
        
        p_str = str(p_num)
        txt_offset_x = 4 if len(p_str) == 1 else 7
        cv2.putText(atlas, p_str, (bcx - txt_offset_x, bcy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1, cv2.LINE_AA)
        
    cv2.rectangle(atlas, (gx, gy), (gx + card_w, gy + 20), (45, 40, 30), -1)
    cv2.putText(atlas, f"Panel #{pid:02d} [{len(methods)} Drawing Techniques]", (gx + 6, gy + 14), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 220, 255), 1, cv2.LINE_AA)

ATLAS_OUT = os.path.join(OUTPUT_DIR, "step6_drawing_methods_classification_atlas.png")
cv2.imwrite(ATLAS_OUT, atlas)
print(f"[SUCCESS] Saved Drawing Methods Atlas: {ATLAS_OUT}")

# ----------------- 2. CLOSE-UP VECTOR TRAJECTORY & ZIG-ZAG HATCHING INSPECTION -----------------
# Inspect Panel 1 (Character Hatching + RTL Cursive) & Panel 3 (Geometric Axes + Math)
p1_info = all_classified_panels[0]
p1_c = p1_info["panel_data"]["composite_canvas"].copy()
ph1, pw1 = p1_c.shape[:2]

# Draw simulated zig-zag hatching on boy's hoodie (حركة متعرجة)
boy_ent = next(m for m in p1_info["methods"] if m["category"] == "character")
bx, by, bw, bh = (18, 60, 78, 103) # approximate bounding for boy
hatch_vis = p1_c.copy()

# Render visual zig-zag lines across hoodie area
y_start, y_end = by + 40, by + bh
step_y = 6
for y_line in range(y_start, y_end, step_y):
    x_left = bx + 10 + int((y_line - y_start) * 0.15)
    x_right = bx + bw - 15
    # Zig-zag pattern
    cv2.line(hatch_vis, (x_left, y_line), (x_right, y_line + 3), (255, 120, 0), 1, cv2.LINE_AA)
    cv2.line(hatch_vis, (x_right, y_line + 3), (x_left, y_line + 6), (255, 120, 0), 1, cv2.LINE_AA)

# Overlay pen flow trajectory arrows for Arabic text lines
text_methods = [m for m in p1_info["methods"] if "HANDWRITING_RTL" in m["drawing_method"]]
for tm in text_methods:
    sp = tm["start_point"]
    ep = tm["end_point"]
    cv2.arrowedLine(hatch_vis, sp, ep, (40, 180, 40), 1, tipLength=0.25)

# High-res preview comparison
target_w = 640
target_h = int(target_w * (ph1 / float(pw1)))
c_orig = cv2.resize(p1_c, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
c_hatch = cv2.resize(hatch_vis, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

inspection_sheet = np.full((target_h + 80, target_w * 2 + 30, 3), 245, dtype=np.uint8)
cv2.rectangle(inspection_sheet, (0, 0), (inspection_sheet.shape[1], 45), (35, 30, 20), -1)
cv2.putText(inspection_sheet, "PHASE 6: DRAWING TECHNIQUE SIMULATION (ZIG-ZAG HATCHING [حركة متعرجة] & RTL FLUID PEN FLOW)", 
            (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 220, 255), 2, cv2.LINE_AA)

cards = [
    (c_orig, "1. Target Clean Composite Panel"),
    (c_hatch, "2. Drawing Technique: Blue Zig-Zag Shading (حركة متعرجة) + Green RTL Pen Trajectory (⬅)")
]

for idx, (img_item, title_t) in enumerate(cards):
    gx = 15 + idx * (target_w + 10)
    gy = 55
    inspection_sheet[gy:gy+target_h, gx:gx+target_w] = img_item
    cv2.rectangle(inspection_sheet, (gx, gy), (gx+target_w, gy+target_h), (160, 150, 130), 2)
    cv2.rectangle(inspection_sheet, (gx, gy), (gx+target_w, gy+24), (45, 40, 30), -1)
    cv2.putText(inspection_sheet, title_t, (gx+8, gy+17), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 220, 255), 1, cv2.LINE_AA)

INSPECTION_OUT = os.path.join(OUTPUT_DIR, "step6_vector_trajectory_inspection.png")
cv2.imwrite(INSPECTION_OUT, inspection_sheet)
print(f"[SUCCESS] Saved Drawing Technique Inspection: {INSPECTION_OUT}")
print("="*80 + "\n")
