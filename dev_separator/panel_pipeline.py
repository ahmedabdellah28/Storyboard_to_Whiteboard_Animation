"""
Panel Processing Pipeline (V4 Advanced Separator)
Integrates:
- Dynamic Border Detection
- Adaptive Layer Splitting
- Typography Line Grouping (Full horizontal lines)
- Container & Weak Bridge Separation
- Semantic Entity Classification
"""
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple

from .container_detector import ContainerDetector
from .adaptive_layer_splitter import AdaptiveLayerSplitter
from .typography_line_grouper import TypographyLineGrouper
from .semantic_classifier import SemanticClassifier


class PanelPipeline:
    @staticmethod
    def process_panel(panel_crop: np.ndarray, panel_id: int = 1, ignore_badges: bool = True) -> Dict[str, Any]:
        """
        Processes a single panel crop with high-precision layer separation:
        1. Separates typography from graphics.
        2. Groups words into full coherent horizontal sentences.
        3. Isolates characters, cards/text-boxes, emojis, icons, and badges.
        4. Extracts text inside colored cards/containers.
        """
        ph, pw = panel_crop.shape[:2]

        # 1. Layer Separation
        split_res = AdaptiveLayerSplitter.split(panel_crop)
        gfx_raw = split_res["graphics_image"]
        txt_raw = split_res["text_image"]
        gfx_mask = split_res["graphics_mask"]
        txt_mask = split_res["text_mask"]

        # 2. Typography Line Grouping
        type_res = TypographyLineGrouper.audit_and_group_lines(txt_raw)
        text_lines = type_res["lines"]

        # 3. Graphics Entity Extraction
        gray_gfx = cv2.cvtColor(gfx_raw, cv2.COLOR_BGR2GRAY)
        hsv_gfx = cv2.cvtColor(gfx_raw, cv2.COLOR_BGR2HSV)
        is_ink = ((gray_gfx < 230) | (hsv_gfx[:, :, 1] > 20)).astype(np.uint8) * 255
        
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        closed_ink = cv2.morphologyEx(is_ink, cv2.MORPH_CLOSE, k, iterations=1)
        num_cc, labels, stats, centroids = cv2.connectedComponentsWithStats(closed_ink)

        raw_masks = []
        for i in range(1, num_cc):
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= 30:
                comp_m = (labels == i).astype(np.uint8) * 255
                # Apply weak bridge / valley splitter to decompose merged entities
                sub_parts = ContainerDetector.split_weak_bridges(comp_m)
                raw_masks.extend(sub_parts)

        # 4. Classify and package graphic elements
        classified_objects = []
        
        # Add text lines first (Title, Underline, Body Text)
        for t_line in text_lines:
            lx, ly, lw, lh = t_line["bbox"]
            l_crop = panel_crop[ly:ly+lh, lx:lx+lw].copy()
            l_mask = t_line["mask"][ly:ly+lh, lx:lx+lw]
            
            classified_objects.append({
                "type": t_line["type"],
                "name": f"Panel {panel_id:02d} - {t_line['type'].capitalize()}",
                "bbox": (lx, ly, lw, lh),
                "mask": l_mask,
                "full_mask": t_line["mask"],
                "crop": l_crop,
                "direction": t_line["direction"],
                "category": "TEXT"
            })

        # Process graphic masks
        for g_mask in raw_masks:
            ys, xs = np.where(g_mask > 0)
            if len(xs) == 0:
                continue
            gx1, gx2 = int(xs.min()), int(xs.max())
            gy1, gy2 = int(ys.min()), int(ys.max())
            gw = gx2 - gx1 + 1
            gh = gy2 - gy1 + 1
            
            cls_info = SemanticClassifier.classify_element(panel_crop, g_mask, (ph, pw))
            category = cls_info["category"]
            label = cls_info["label"]
            
            # Ignore and suppress circular panel badges (e.g. ❶, ❷...) if requested
            if ignore_badges and category == "PANEL_BADGE":
                # Erase badge pixels to clean white canvas background
                panel_crop[g_mask > 0] = 255
                continue
                
            g_crop = panel_crop[gy1:gy2+1, gx1:gx2+1].copy()
            g_crop_mask = g_mask[gy1:gy2+1, gx1:gx2+1]
            
            obj_data = {
                "type": category,
                "name": f"Panel {panel_id:02d} - {label}",
                "bbox": (gx1, gy1, gw, gh),
                "mask": g_crop_mask,
                "full_mask": g_mask,
                "crop": g_crop,
                "direction": "CIRCUIT",
                "category": category,
                "confidence": cls_info.get("confidence", 0.90)
            }
            
            # If it's a container card, inspect and extract its internal text lines
            if category == "CONTAINER_CARD":
                card_details = cls_info.get("card_details", {})
                obj_data["bg_median_gray"] = card_details.get("bg_median_gray")
                obj_data["text_components_count"] = len(card_details.get("text_components", []))
                
                # Extract cohesive lines inside the colored card
                int_mask = card_details.get("internal_text_mask")
                if int_mask is not None and cv2.countNonZero(int_mask) > 15:
                    txt_card_synth = np.full_like(g_crop, 255)
                    txt_card_synth[int_mask > 0] = g_crop[int_mask > 0]
                    card_lines_res = TypographyLineGrouper.audit_and_group_lines(txt_card_synth)
                    
                    for c_l_idx, c_line in enumerate(card_lines_res.get("lines", [])):
                        clx, cly, clw, clh = c_line["bbox"]
                        glx = gx1 + clx
                        gly = gy1 + cly
                        
                        sub_m = c_line["mask"][cly:cly+clh, clx:clx+clw]
                        sh_h, sh_w = sub_m.shape[:2]
                        
                        # Clip safely within panel dimensions
                        end_y = min(ph, gly + sh_h)
                        end_x = min(pw, glx + sh_w)
                        fit_h = end_y - gly
                        fit_w = end_x - glx
                        
                        full_line_m = np.zeros((ph, pw), dtype=np.uint8)
                        if fit_h > 0 and fit_w > 0:
                            full_line_m[gly:end_y, glx:end_x] = sub_m[:fit_h, :fit_w]
                        
                        crop_slice = panel_crop[gly:end_y, glx:end_x].copy()
                        
                        classified_objects.append({
                            "type": "TEXT_LINE",
                            "name": f"Panel {panel_id:02d} - Card Text Line {c_l_idx + 1}",
                            "bbox": (glx, gly, fit_w, fit_h),
                            "mask": sub_m[:fit_h, :fit_w],
                            "full_mask": full_line_m,
                            "crop": crop_slice,
                            "direction": "RTL",
                            "category": "TEXT"
                        })
                
            classified_objects.append(obj_data)

        # 5. Semantic Priority Ordering
        # Order: 1. Badge -> 2. Title -> 3. Underline -> 4. Character -> 5. Container/Card -> 6. Emoji/Icon -> 7. Text Line
        def get_priority(obj):
            cat = obj["category"]
            if cat == "PANEL_BADGE":
                return 1
            if cat == "TEXT" and "title" in obj["name"].lower():
                return 2
            if cat == "TEXT" and "underline" in obj["name"].lower():
                return 3
            if cat == "CHARACTER":
                return 4
            if cat == "CONTAINER_CARD":
                return 5
            if cat in ("EMOJI", "ICON_GRAPHIC"):
                return 6
            return 7 # Standard text lines
            
        classified_objects.sort(key=get_priority)
        
        for idx, obj in enumerate(classified_objects):
            obj["priority"] = idx + 1

        return {
            "panel_id": panel_id,
            "width": pw,
            "height": ph,
            "clean_crop": panel_crop,
            "objects": classified_objects,
            "text_lines_count": len(text_lines),
            "graphics_count": len(raw_masks)
        }
