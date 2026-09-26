"""
Text Line Auditor & Discovery Engine
Audits typography image and separates lines, accents, underlines, and detects writing directions.
Includes dynamic multi-line horizontal valley decomposition for stacked paragraphs.
"""
import cv2
import numpy as np
from typing import Dict, Any, List


class TextLineAuditor:
    @staticmethod
    def _split_lines_by_valleys(line_m: np.ndarray, min_line_pixels: int = 15) -> List[np.ndarray]:
        """Splits vertically stacked multi-line paragraphs at horizontal projection valleys."""
        ys, xs = np.where(line_m > 0)
        if len(ys) == 0:
            return []
        y_min, y_max = int(ys.min()), int(ys.max())
        block_h = y_max - y_min + 1
        if block_h < 22:
            return [line_m]

        sub_m = line_m[y_min:y_max+1, :]
        h_proj = (sub_m > 0).astype(np.float32).mean(axis=1)
        kernel = np.ones(5) / 5.0
        smoothed = np.convolve(h_proj, kernel, mode='same')

        max_p = np.max(smoothed)
        if max_p < 0.05:
            return [line_m]

        # Major peaks
        major_peaks = []
        for y in range(2, block_h - 2):
            if smoothed[y] >= smoothed[y-1] and smoothed[y] >= smoothed[y+1]:
                if smoothed[y] >= 0.06 and smoothed[y] >= 0.20 * max_p:
                    major_peaks.append((y, smoothed[y]))

        if len(major_peaks) < 2:
            return [line_m]

        # Merge peaks that are too close (< 8px apart)
        merged_peaks = []
        for p in major_peaks:
            if not merged_peaks:
                merged_peaks.append(p)
            else:
                prev_y, prev_v = merged_peaks[-1]
                if p[0] - prev_y < 8:
                    if p[1] > prev_v:
                        merged_peaks[-1] = p
                else:
                    merged_peaks.append(p)

        if len(merged_peaks) < 2:
            return [line_m]

        split_ys = []
        for i in range(len(merged_peaks) - 1):
            y1, p1 = merged_peaks[i]
            y2, p2 = merged_peaks[i+1]
            v_rel = y1 + np.argmin(smoothed[y1:y2+1])
            v_val = smoothed[v_rel]
            min_p = min(p1, p2)
            if v_val <= 0.50 * min_p or v_val <= 0.05:
                split_ys.append(y_min + v_rel)

        if not split_ys:
            return [line_m]

        sub_masks = []
        cur_y = y_min
        for sy in split_ys + [y_max + 1]:
            m_part = np.zeros_like(line_m)
            m_part[cur_y:sy, :] = line_m[cur_y:sy, :]
            if cv2.countNonZero(m_part) >= min_line_pixels:
                sub_masks.append(m_part)
            cur_y = sy

        return sub_masks if len(sub_masks) > 1 else [line_m]

    @staticmethod
    def audit_lines(txt_img: np.ndarray, min_line_pixels: int = 15) -> Dict[str, Any]:
        ph, pw = txt_img.shape[:2]

        diff = 255.0 - txt_img.astype(np.float32)
        dist = np.max(diff, axis=2)
        ink_bin = (dist > 25.0).astype(np.uint8) * 255

        # Purely horizontal kernel (width=18, height=1) to connect words without merging vertical lines
        kernel_line = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 1))
        dilated = cv2.dilate(ink_bin, kernel_line)
        num_lines, l_labels, l_stats, _ = cv2.connectedComponentsWithStats(dilated)

        candidate_masks = []
        for i in range(1, num_lines):
            larea = l_stats[i, cv2.CC_STAT_AREA]
            lw = l_stats[i, cv2.CC_STAT_WIDTH]

            if larea < 15 or lw < 6:
                continue

            line_m = np.zeros_like(ink_bin)
            line_m[(l_labels == i) & (ink_bin > 0)] = 255
            if cv2.countNonZero(line_m) < min_line_pixels:
                continue

            # Split stacked multi-line blocks dynamically by valley analysis
            sub_splits = TextLineAuditor._split_lines_by_valleys(line_m, min_line_pixels=min_line_pixels)
            candidate_masks.extend(sub_splits)

        raw_lines = []
        for line_m in candidate_masks:
            ys, xs = np.where(line_m > 0)
            if len(xs) < min_line_pixels:
                continue

            x1, y1 = int(xs.min()), int(ys.min())
            x2, y2 = int(xs.max()), int(ys.max())

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

        raw_lines.sort(key=lambda l: l["bbox"][1])

        for idx, l in enumerate(raw_lines):
            l["line_id"] = idx + 1
            l["type"] = "UNDERLINE" if l["is_underline"] else ("TITLE" if idx == 0 else "TEXT_LINE")
            l["direction"] = "LTR" if l["is_underline"] else "RTL"

        # Accents / Stars / Bullets mask (ink pixels not belonging to primary text lines, or standalone marks)
        all_lines_mask = np.zeros_like(ink_bin)
        for l in raw_lines:
            all_lines_mask[l["mask"] > 0] = 255

        accents_mask = np.zeros_like(ink_bin)
        accents_mask[(ink_bin > 0) & (all_lines_mask == 0)] = 255

        num_acc, acc_lbl, acc_stat, _ = cv2.connectedComponentsWithStats(accents_mask)
        accents = []
        for i in range(1, num_acc):
            ax = acc_stat[i, cv2.CC_STAT_LEFT]
            ay = acc_stat[i, cv2.CC_STAT_TOP]
            aw = acc_stat[i, cv2.CC_STAT_WIDTH]
            ah = acc_stat[i, cv2.CC_STAT_HEIGHT]
            if acc_stat[i, cv2.CC_STAT_AREA] < 8:
                continue

            acc_m = np.zeros_like(ink_bin)
            acc_m[acc_lbl == i] = 255
            accents.append({
                "bbox": (ax, ay, aw, ah),
                "mask": acc_m
            })

        return {
            "lines": raw_lines,
            "accents": accents
        }
