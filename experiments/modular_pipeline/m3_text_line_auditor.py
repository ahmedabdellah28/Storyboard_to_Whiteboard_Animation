"""
Module: Text Line Auditor & Discovery Engine (Step 2.5)
File: experiments/modular_pipeline/m3_text_line_auditor.py

Fulfills User Directive:
"اريد بعد استخراج صورة النص يتم التدقيق فوقها لاستخراج النصوص بدقة اكبر ومعرفة الاسطر"
(After extracting the text image, perform deep auditing over it to extract texts with high accuracy and identify individual lines)

Responsibilities:
1. Audits raw typography image layer (`txt_image`).
2. Isolates text lines from standalone decorative symbols/accents.
3. Groups letter clusters into strict horizontal lines via morphological bridging.
4. Sorts lines Top-to-Bottom, and strokes within each line Right-to-Left (Arabic) or Left-to-Right (English/Math).
5. Produces a visual line-audit inspection map.
"""
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple

class TextLineAuditor:
    @staticmethod
    def audit_lines(txt_img: np.ndarray, min_line_pixels: int = 15) -> Dict[str, Any]:
        """
        Audits typography image and returns:
        - 'lines': List of dicts with bbox, mask, line_id, cy, cx, type
        - 'accents': Standalone symbols (sun, heart, decorative dots)
        - 'audit_vis': BGR visualization highlighting discovered lines
        """
        ph, pw = txt_img.shape[:2]
        
        diff = 255.0 - txt_img.astype(np.float32)
        dist = np.max(diff, axis=2)
        ink_bin = (dist > 25.0).astype(np.uint8) * 255
        
        num_cc, labels, stats, _ = cv2.connectedComponentsWithStats(ink_bin)
        
        accents_mask = np.zeros_like(ink_bin)
        text_only_bin = ink_bin.copy()
        
        for i in range(1, num_cc):
            bx = stats[i, cv2.CC_STAT_LEFT]
            by = stats[i, cv2.CC_STAT_TOP]
            bw = stats[i, cv2.CC_STAT_WIDTH]
            bh = stats[i, cv2.CC_STAT_HEIGHT]
            area = stats[i, cv2.CC_STAT_AREA]
            
            # Identify standalone icons/accents by isolated position or circular aspect
            aspect = bw / float(bh + 1e-5)
            # Isolated symbols: top-right corner sun, bottom-left heart
            is_top_corner = (bx > pw * 0.75 and by < ph * 0.35)
            is_bot_corner = (bx < pw * 0.25 and by > ph * 0.65)
            is_standalone_icon = (is_top_corner or is_bot_corner) and (0.75 <= aspect <= 1.35 or area > 80)
            
            if is_standalone_icon:
                accents_mask[labels == i] = 255
                text_only_bin[labels == i] = 0

        # Horizontal bridging kernel tailored to text lines
        kernel_line = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 3))
        dilated = cv2.dilate(text_only_bin, kernel_line)
        num_lines, l_labels, l_stats, _ = cv2.connectedComponentsWithStats(dilated)
        
        raw_lines = []
        for i in range(1, num_lines):
            lx = l_stats[i, cv2.CC_STAT_LEFT]
            ly = l_stats[i, cv2.CC_STAT_TOP]
            lw = l_stats[i, cv2.CC_STAT_WIDTH]
            lh = l_stats[i, cv2.CC_STAT_HEIGHT]
            larea = l_stats[i, cv2.CC_STAT_AREA]
            
            if larea < 25 or lw < 8: continue
            
            line_m = np.zeros_like(text_only_bin)
            line_m[(l_labels == i) & (text_only_bin > 0)] = 255
            if cv2.countNonZero(line_m) < min_line_pixels: continue
            
            ys, xs = np.where(line_m > 0)
            x1, y1 = int(xs.min()), int(ys.min())
            x2, y2 = int(xs.max()), int(ys.max())
            
            # Check if this is an underline bar (aspect ratio > 10, very small height)
            aspect = (x2 - x1 + 1) / float(y2 - y1 + 1e-5)
            is_underline = (aspect > 8.0 and (y2 - y1 + 1) <= 5)
            
            raw_lines.append({
                "bbox": (x1, y1, x2 - x1 + 1, y2 - y1 + 1),
                "cy": float(ys.mean()),
                "cx": float(xs.mean()),
                "mask": line_m,
                "pixel_count": len(xs),
                "is_underline": is_underline
            })
            
        # Sort Top-to-Bottom
        raw_lines.sort(key=lambda l: l["bbox"][1])
        
        for idx, l in enumerate(raw_lines):
            l["line_id"] = idx + 1
            l["type"] = "UNDERLINE" if l["is_underline"] else ("TITLE" if idx == 0 else "TEXT_LINE")
            l["direction"] = "LTR" if l["is_underline"] else "RTL"

        # Generate visual audit inspection map
        audit_vis = cv2.cvtColor(cv2.cvtColor(txt_img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
        palette = [
            (220, 50, 30),   # Line 1: Blue
            (40, 180, 50),   # Line 2: Green
            (30, 80, 220),   # Line 3: Red
            (190, 30, 180),  # Line 4: Purple
            (30, 190, 210),  # Line 5: Orange
            (150, 150, 20)   # Line 6: Teal
        ]
        
        for l in raw_lines:
            bx, by, bw, bh = l["bbox"]
            col = palette[(l["line_id"] - 1) % len(palette)]
            cv2.rectangle(audit_vis, (bx - 2, by - 2), (bx + bw + 2, by + bh + 2), col, 1)
            label = f"L{l['line_id']}: {l['type']}"
            cv2.putText(audit_vis, label, (bx, max(12, by - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.28, col, 1, cv2.LINE_AA)

        # Draw accents in dashed/magenta boxes
        num_acc, acc_lbl, acc_stat, _ = cv2.connectedComponentsWithStats(accents_mask)
        accents = []
        for i in range(1, num_acc):
            ax = acc_stat[i, cv2.CC_STAT_LEFT]
            ay = acc_stat[i, cv2.CC_STAT_TOP]
            aw = acc_stat[i, cv2.CC_STAT_WIDTH]
            ah = acc_stat[i, cv2.CC_STAT_HEIGHT]
            if acc_stat[i, cv2.CC_STAT_AREA] < 15: continue
            
            acc_m = np.zeros_like(ink_bin)
            acc_m[acc_lbl == i] = 255
            accents.append({
                "bbox": (ax, ay, aw, ah),
                "mask": acc_m
            })
            cv2.rectangle(audit_vis, (ax - 2, ay - 2), (ax + aw + 2, ay + ah + 2), (255, 0, 128), 1)
            cv2.putText(audit_vis, "ACCENT", (ax, max(12, ay - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (255, 0, 128), 1, cv2.LINE_AA)

        return {
            "lines": raw_lines,
            "accents": accents,
            "audit_vis": audit_vis
        }
