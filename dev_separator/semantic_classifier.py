"""
Semantic Classifier (Character vs Text Box vs Emoji vs Icon vs Typography)
Accurately categorizes every extracted panel element without cross-type confusion.
"""
import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional


class SemanticClassifier:
    @staticmethod
    def classify_element(crop_bgr: np.ndarray, mask: np.ndarray, panel_dim: Tuple[int, int]) -> Dict[str, Any]:
        """
        Classifies an isolated graphic entity into its semantic role:
        - CHARACTER: Human figures, large organic drawings.
        - CONTAINER_CARD: Rectangular cards / text boxes containing text.
        - EMOJI: Multi-colored facial expressions (e.g. laughing emoji 😂).
        - ICON_GRAPHIC: Standalone symbolic illustrations (e.g. ☀️ sun, 🛒 cart, 👕 shirt, 🧹 broom, 🪐 planet, ❓ question marks).
        - PANEL_BADGE: Circular numbered panel markers (e.g. ❶, ❷).
        """
        ph, pw = panel_dim
        ys, xs = np.where(mask > 0)
        if len(xs) == 0:
            return {"category": "UNKNOWN", "confidence": 0.0}
            
        x1, x2 = int(xs.min()), int(xs.max())
        y1, y2 = int(ys.min()), int(ys.max())
        w = x2 - x1 + 1
        h = y2 - y1 + 1
        area = cv2.countNonZero(mask)
        aspect = w / float(h + 1e-5)
        bbox_area = w * h
        solidity = area / float(bbox_area)
        
        elem_crop = crop_bgr[y1:y2+1, x1:x2+1]
        elem_mask = mask[y1:y2+1, x1:x2+1]
        
        # Color space analysis
        hsv = cv2.cvtColor(elem_crop, cv2.COLOR_BGR2HSV)
        sat_vals = hsv[:, :, 1][elem_mask > 0]
        hue_vals = hsv[:, :, 0][elem_mask > 0]
        val_vals = hsv[:, :, 2][elem_mask > 0]
        
        mean_sat = float(np.mean(sat_vals)) if len(sat_vals) > 0 else 0.0
        mean_val = float(np.mean(val_vals)) if len(val_vals) > 0 else 0.0
        std_hue = float(np.std(hue_vals)) if len(hue_vals) > 0 else 0.0
        
        # 1. Check if it is a Circular Panel Badge (e.g. ❶, ❷... at top left)
        if (x1 < pw * 0.20 and y1 < ph * 0.25 and 
            24 <= w <= 40 and 24 <= h <= 40 and 
            0.80 <= aspect <= 1.25 and mean_val < 80):
            return {
                "category": "PANEL_BADGE",
                "label": "Panel Number Badge",
                "confidence": 0.98,
                "bbox": (x1, y1, w, h)
            }
            
        # 2. Check if it is a Text Box / Container Card
        from .container_detector import ContainerDetector
        card_res = ContainerDetector.inspect_container_card(crop_bgr, mask)
        if card_res.get("is_card", False):
            return {
                "category": "CONTAINER_CARD",
                "label": "Text Box / Card",
                "confidence": 0.95,
                "bbox": (x1, y1, w, h),
                "card_details": card_res
            }
            
        # 3. Check for Emoji (e.g. Laughing Emoji 😂)
        # Emojis have: compact size (25..75px), aspect ~ 1.0, high saturation, distinct yellow/colorful face
        is_emoji = (
            25 <= w <= 80 and 25 <= h <= 80 and
            0.75 <= aspect <= 1.30 and
            solidity >= 0.55 and
            mean_sat > 55.0 and
            std_hue > 15.0 # multiple colors (yellow face + blue tears or red mouth)
        )
        if is_emoji:
            return {
                "category": "EMOJI",
                "label": "Emoji / Expression",
                "confidence": 0.96,
                "bbox": (x1, y1, w, h)
            }
            
        # 4. Check for Question Marks ❓ or standalone punctuation icons
        # Red or dark question marks have height 25..55, width 15..45, aspect 0.4..0.8
        is_question_mark = (
            12 <= w <= 45 and 20 <= h <= 60 and
            0.35 <= aspect <= 0.85 and
            solidity < 0.65 and
            (mean_sat > 40.0 or mean_val < 90)
        )
        if is_question_mark:
            return {
                "category": "ICON_GRAPHIC",
                "label": "Question Mark / Symbol",
                "confidence": 0.92,
                "bbox": (x1, y1, w, h)
            }
            
        # 5. Check for Character (Large human figures / drawings)
        # Characters typically have height > 35% of panel, area > 1200
        is_character = (
            (h >= ph * 0.35 or w >= pw * 0.35) and
            area >= 1200 and
            not card_res.get("is_card", False)
        )
        if is_character:
            return {
                "category": "CHARACTER",
                "label": "Character / Person",
                "confidence": 0.96,
                "bbox": (x1, y1, w, h)
            }
            
        # 6. Default to Icon / Graphic (e.g. sun ☀️, shirt 👕, cart 🛒, broom 🧹, planet 🪐, diagram)
        return {
            "category": "ICON_GRAPHIC",
            "label": "Icon / Graphic",
            "confidence": 0.88,
            "bbox": (x1, y1, w, h)
        }
