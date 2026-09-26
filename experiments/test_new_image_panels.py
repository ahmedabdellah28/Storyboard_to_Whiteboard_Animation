import os
import sys
import cv2

sys.path.insert(0, 'kivy')
sys.path.insert(0, r'E:\image_to_animate')
from engine.processing.whiteboard_processor import WhiteboardProcessor
from engine.processing.dynamic_border_detector import DynamicBorderDetector
from dev_separator.panel_pipeline import PanelPipeline

img_path = r'project_content/images/ChatGPT Image Sep 18, 2026, 04_51_53 PM.png'
img = cv2.imread(img_path)
panels = WhiteboardProcessor.discover_panels(img)

os.makedirs('experiments/panel_inspections', exist_ok=True)

for p_num in range(1, 7):
    px, py, pw, ph = panels[p_num - 1]['bbox']
    crop = img[py:py+ph, px:px+pw]
    border_res = DynamicBorderDetector.detect_and_trim_panel_border(crop)
    clean = border_res['clean_crop']
    cv2.imwrite(f'experiments/panel_inspections/panel_{p_num}_clean.png', clean)
    p_res = PanelPipeline.process_panel(clean, panel_id=p_num, ignore_badges=True)
    print(f"=== Panel {p_num} ===")
    for i, o in enumerate(p_res['objects']):
        bx, by, bw, bh = o['bbox']
        print(f"  Obj {i}: bbox=({bx}, {by}, {bw}, {bh}), strokes={len(o.get('strokes', []))}")
        # Save individual object crop
        if o.get('crop') is not None:
            cv2.imwrite(f'experiments/panel_inspections/p{p_num}_obj_{i}.png', o['crop'])
