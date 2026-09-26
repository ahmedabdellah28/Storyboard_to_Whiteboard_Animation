"""
Generate Coherent Cumulative Static Previews for Panel 1, 2, and 9
File: experiments/draw_priority/generate_coherent_cumulative_previews.py
"""
import os
import sys
import json
import cv2
import numpy as np

sys.path.insert(0, r"E:\image_to_animate\experiments\draw_priority")
from downstream_artifact_consumer import DownstreamArtifactConsumer

JSON_PATH = r"E:\image_to_animate\experiments\results\step5_draw_priority\validated_draw_order.json"
OUTPUT_DIR = r"E:\image_to_animate\experiments\results\step5_draw_priority"

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

panels_to_preview = [1, 2, 9]

for pid in panels_to_preview:
    p_rec = next(p for p in data["panels"] if p["panel_id"] == f"panel_{pid:02d}")
    panel_data = DownstreamArtifactConsumer.load_panel_artifacts(pid)
    entities = DownstreamArtifactConsumer.extract_entities_from_artifacts(panel_data)
    ent_map = {e.entity_id: e for e in entities}
    
    plan = p_rec["draw_order_validated"]
    ph, pw = panel_data["shape"]
    
    # Generate 6 key steps
    num_steps = min(6, len(plan))
    step_indices = np.linspace(1, len(plan), num_steps, dtype=int)
    
    col_w = 320
    col_h = int(col_w * (ph / float(pw)))
    
    sheet = np.full((col_h + 80, num_steps * (col_w + 12) + 12, 3), 245, dtype=np.uint8)
    cv2.rectangle(sheet, (0, 0), (sheet.shape[1], 45), (25, 45, 30), -1)
    cv2.putText(sheet, f"PANEL #{pid:02d} COHERENT DRAW SEQUENCE (TITLE -> CHARACTER -> CONTAINER -> LINES)", 
                (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (50, 255, 130), 2, cv2.LINE_AA)
                
    for s_idx, k in enumerate(step_indices):
        gx = 12 + s_idx * (col_w + 12)
        gy = 55
        
        canvas = np.full((ph, pw, 3), 255, dtype=np.uint8)
        sub_plan = plan[:k]
        
        for item in sub_plan:
            e = ent_map[item["entity_id"]]
            if e.mask is not None:
                canvas[e.mask > 0] = panel_data["composite_canvas"][e.mask > 0]
            else:
                bx, by, bw, bh = e.bbox
                canvas[by:by+bh, bx:bx+bw] = panel_data["composite_canvas"][by:by+bh, bx:bx+bw]
                
        sc_prev = cv2.resize(canvas, (col_w, col_h), interpolation=cv2.INTER_AREA)
        sheet[gy:gy+col_h, gx:gx+col_w] = sc_prev
        cv2.rectangle(sheet, (gx, gy), (gx + col_w, gy + col_h), (180, 180, 180), 1)
        
        last_e = sub_plan[-1]
        cv2.rectangle(sheet, (gx, gy + col_h), (gx + col_w, gy + col_h + 22), (40, 50, 45), -1)
        cv2.putText(sheet, f"Step {s_idx+1}: +{last_e['category']} (#{last_e['priority']})", 
                    (gx + 6, gy + col_h + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (50, 255, 120), 1, cv2.LINE_AA)
                    
    OUT_PATH = os.path.join(OUTPUT_DIR, f"step5_panel_{pid:02d}_coherent_preview.png")
    cv2.imwrite(OUT_PATH, sheet)
    print(f"Saved: {OUT_PATH}")
