"""
Dynamic Multi-Sheet Storyboard Panel Engine
Extracts, cleans, and segments all panels across multiple storyboard sheets.
Suppresses all panel badges (❶..⓬), severs weak character-card bridges, and groups Arabic typography.
"""
import os
import cv2
import numpy as np
from typing import List, Dict, Any

try:
    from core.render_engine.processing.whiteboard_processor import WhiteboardProcessor
    from core.render_engine.processing.dynamic_border_detector import DynamicBorderDetector
except ImportError:
    from engine.processing.whiteboard_processor import WhiteboardProcessor
    from engine.processing.dynamic_border_detector import DynamicBorderDetector
from dev_separator.panel_pipeline import PanelPipeline


class DynamicMultiSheetEngine:
    @classmethod
    def process_sheets(
        cls, 
        image_paths: List[str], 
        ignore_badges: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Discovers and processes all storyboard panels across multiple image sheets.
        Returns a globally indexed list of panels (1..N).
        """
        all_panels = []
        global_panel_id = 1

        for sheet_idx, img_path in enumerate(image_paths):
            sheet_name = os.path.basename(img_path)
            img = cv2.imread(img_path)
            if img is None:
                raise FileNotFoundError(f"Could not load image: {img_path}")

            # Discover panels in sheet
            discovered = WhiteboardProcessor.discover_panels(img)
            print(f"[MultiSheetEngine] Sheet {sheet_idx + 1} ({sheet_name}): {len(discovered)} panels discovered.")

            for local_idx, p_info in enumerate(discovered):
                px, py, pw, ph = p_info["bbox"]
                raw_crop = img[py:py+ph, px:px+pw]

                # Border suppression & trimming
                border_res = DynamicBorderDetector.detect_and_trim_panel_border(raw_crop)
                clean_crop = border_res["clean_crop"]

                # High-precision entity separation with badge suppression
                panel_res = PanelPipeline.process_panel(
                    clean_crop,
                    panel_id=global_panel_id,
                    ignore_badges=ignore_badges
                )

                all_panels.append({
                    "global_id": global_panel_id,
                    "sheet_index": sheet_idx + 1,
                    "local_id": local_idx + 1,
                    "sheet_path": img_path,
                    "sheet_name": sheet_name,
                    "bbox_in_sheet": (px, py, pw, ph),
                    "clean_crop": panel_res["clean_crop"],
                    "raw_w": clean_crop.shape[1],
                    "raw_h": clean_crop.shape[0],
                    "objects": panel_res["objects"],
                    "text_lines_count": panel_res.get("text_lines_count", 0),
                    "graphics_count": panel_res.get("graphics_count", 0)
                })

                global_panel_id += 1

        print(f"[MultiSheetEngine] Successfully processed {len(all_panels)} total panels across {len(image_paths)} sheets.")
        return all_panels
