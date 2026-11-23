"""Adaptive Storyboard Candidate Extractor with Recursive XY-Cut White Valley Slicing (TCM-DS Phase 3).

Strict Rules:
- NO fixed row or column assumptions.
- NO fixed element count assumptions.
- Recursive XY-Cut: detects continuous horizontal and vertical white valleys to segment compound panels.
- Natural white-gap analysis, connected components, and multi-scale contour clustering.
- Generates transparent PNG crops and a numbered Contact Sheet for AI Review.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np


class ExtractedCandidate:
    """Represents a raw candidate extracted from the storyboard."""

    def __init__(
        self,
        candidate_id: str,
        bbox: Tuple[int, int, int, int],  # (x, y, w, h)
        crop_bgr: np.ndarray,
        mask: np.ndarray,
        area: int,
        sheet_order: int = 1,
        centroid: Tuple[int, int] = (0, 0),
    ) -> None:
        self.candidate_id = candidate_id
        self.bbox = bbox
        self.crop_bgr = crop_bgr
        self.mask = mask
        self.area = area
        self.sheet_order = sheet_order
        self.centroid = centroid


class AdaptiveCandidateExtractor:
    """Extracts organic visual units using adaptive thresholding, recursive XY-cut, and contour clustering."""

    def __init__(
        self,
        min_area_ratio: float = 0.004,  # Min 0.4% of canvas area to filter specks
        max_area_ratio: float = 0.90,   # Max 90% of canvas area to filter entire canvas
        white_threshold: int = 242,
        min_valley_span: int = 5,
    ) -> None:
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.white_threshold = white_threshold
        self.min_valley_span = min_valley_span

    def extract_candidates(
        self,
        storyboard_path: Path,
        output_crops_dir: Optional[Path] = None,
    ) -> Tuple[List[ExtractedCandidate], np.ndarray]:
        """Extracts candidate visual regions without any grid assumptions.

        Returns:
            Tuple of (list_of_candidates, contact_sheet_image)
        """
        img = cv2.imread(str(storyboard_path))
        if img is None:
            raise FileNotFoundError(f"Could not load storyboard at {storyboard_path}")

        h, w = img.shape[:2]
        canvas_area = float(w * h)
        min_area = int(canvas_area * self.min_area_ratio)
        max_area = int(canvas_area * self.max_area_ratio)

        # 1. Convert to grayscale and identify foreground drawing strokes
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Adaptive inverse threshold: drawing marks (dark) become white (255) on black background
        _, binary = cv2.threshold(gray, self.white_threshold, 255, cv2.THRESH_BINARY_INV)

        # 2. Moderate morphological closing (5x5) to keep elements intact without bridging separate panels
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # 3. Find connected components / contours
        contours, _ = cv2.findContours(
            closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        initial_boxes: List[Tuple[int, int, int, int]] = []
        for cnt in contours:
            bx, by, bw, bh = cv2.boundingRect(cnt)
            area = bw * bh
            if min_area <= area <= max_area:
                initial_boxes.append((bx, by, bw, bh))

        # 4. Apply Recursive XY-Cut to split any merged panels separated by clear white valleys
        refined_boxes: List[Tuple[int, int, int, int]] = []
        for bx, by, bw, bh in initial_boxes:
            crop = img[by : by + bh, bx : bx + bw]
            splits = self._recursive_xy_cut(crop, bbox_offset=(bx, by))
            for _, sub_bbox in splits:
                sub_area = sub_bbox[2] * sub_bbox[3]
                if sub_area >= min_area:
                    refined_boxes.append(sub_bbox)

        # 5. Clean / trim white borders for each box to tightly wrap drawing strokes
        tight_boxes = [self._tighten_bbox(img, b, binary) for b in refined_boxes]
        tight_boxes = [b for b in tight_boxes if (b[2] * b[3]) >= min_area]

        # 6. Sort boxes spatially using dynamic centroid clustering (top-to-bottom, left-to-right)
        tight_boxes = self._cluster_and_sort_spatially(tight_boxes)

        candidates: List[ExtractedCandidate] = []
        contact_sheet = img.copy()

        if output_crops_dir:
            output_crops_dir.mkdir(parents=True, exist_ok=True)

        for idx, (bx, by, bw, bh) in enumerate(tight_boxes, 1):
            cand_id = f"cand_{idx:03d}"
            crop_bgr = img[by : by + bh, bx : bx + bw].copy()
            crop_mask = binary[by : by + bh, bx : bx + bw].copy()
            cx = int(bx + bw / 2.0)
            cy = int(by + bh / 2.0)

            cand = ExtractedCandidate(
                candidate_id=cand_id,
                bbox=(bx, by, bw, bh),
                crop_bgr=crop_bgr,
                mask=crop_mask,
                area=bw * bh,
                sheet_order=idx,
                centroid=(cx, cy),
            )
            candidates.append(cand)

            # Save transparent PNG if output directory specified
            if output_crops_dir:
                rgba = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2BGRA)
                rgba[:, :, 3] = crop_mask
                crop_file = output_crops_dir / f"{cand_id}.png"
                cv2.imwrite(str(crop_file), rgba)

            # Draw visual indicator on Contact Sheet for AI Review
            cv2.rectangle(contact_sheet, (bx, by), (bx + bw, by + bh), (0, 0, 220), 2)
            cv2.putText(
                contact_sheet,
                f"#{idx}",
                (bx + 4, by + 22),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 220),
                2,
                cv2.LINE_AA,
            )

        if output_crops_dir:
            contact_path = output_crops_dir / "contact_sheet.png"
            cv2.imwrite(str(contact_path), contact_sheet)

        return candidates, contact_sheet

    def _recursive_xy_cut(
        self,
        crop_bgr: np.ndarray,
        bbox_offset: Tuple[int, int],
        min_dim: int = 40,
    ) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """Recursively splits a candidate region along horizontal and vertical white valleys."""
        bx0, by0 = bbox_offset
        h, w = crop_bgr.shape[:2]
        if h < min_dim or w < min_dim:
            return [(crop_bgr, (bx0, by0, w, h))]

        gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)

        # 1. Search for vertical white valleys (split X)
        col_mean = np.mean(gray, axis=0)
        white_cols = np.where(col_mean >= self.white_threshold)[0]
        valleys_x = self._find_contiguous_runs(white_cols, self.min_valley_span)
        # Exclude edge valleys
        valleys_x = [v for v in valleys_x if v[0] > 12 and v[1] < w - 12]

        if valleys_x:
            splits: List[Tuple[np.ndarray, Tuple[int, int, int, int]]] = []
            curr_x = 0
            for v_start, v_end in valleys_x:
                split_x = (v_start + v_end) // 2
                if split_x - curr_x >= min_dim:
                    sub_crop = crop_bgr[:, curr_x:split_x]
                    splits.extend(
                        self._recursive_xy_cut(sub_crop, (bx0 + curr_x, by0), min_dim)
                    )
                curr_x = split_x
            if w - curr_x >= min_dim:
                sub_crop = crop_bgr[:, curr_x:w]
                splits.extend(
                    self._recursive_xy_cut(sub_crop, (bx0 + curr_x, by0), min_dim)
                )
            return splits

        # 2. Search for horizontal white valleys (split Y)
        row_mean = np.mean(gray, axis=1)
        white_rows = np.where(row_mean >= self.white_threshold)[0]
        valleys_y = self._find_contiguous_runs(white_rows, self.min_valley_span)
        valleys_y = [v for v in valleys_y if v[0] > 12 and v[1] < h - 12]

        if valleys_y:
            splits: List[Tuple[np.ndarray, Tuple[int, int, int, int]]] = []
            curr_y = 0
            for v_start, v_end in valleys_y:
                split_y = (v_start + v_end) // 2
                if split_y - curr_y >= min_dim:
                    sub_crop = crop_bgr[curr_y:split_y, :]
                    splits.extend(
                        self._recursive_xy_cut(sub_crop, (bx0, by0 + curr_y), min_dim)
                    )
                curr_y = split_y
            if h - curr_y >= min_dim:
                sub_crop = crop_bgr[curr_y:h, :]
                splits.extend(
                    self._recursive_xy_cut(sub_crop, (bx0, by0 + curr_y), min_dim)
                )
            return splits

        return [(crop_bgr, (bx0, by0, w, h))]

    @staticmethod
    def _find_contiguous_runs(indices: np.ndarray, min_len: int) -> List[Tuple[int, int]]:
        runs: List[Tuple[int, int]] = []
        if len(indices) == 0:
            return runs
        start = int(indices[0])
        prev = int(indices[0])
        length = 1
        for idx in indices[1:]:
            idx_int = int(idx)
            if idx_int == prev + 1:
                length += 1
                prev = idx_int
            else:
                if length >= min_len:
                    runs.append((start, prev))
                start = idx_int
                prev = idx_int
                length = 1
        if length >= min_len:
            runs.append((start, prev))
        return runs

    @staticmethod
    def _tighten_bbox(
        img: np.ndarray, bbox: Tuple[int, int, int, int], binary_fg: np.ndarray
    ) -> Tuple[int, int, int, int]:
        bx, by, bw, bh = bbox
        sub_fg = binary_fg[by : by + bh, bx : bx + bw]
        pts = cv2.findNonZero(sub_fg)
        if pts is None:
            return bbox
        tx, ty, tw, th = cv2.boundingRect(pts)
        pad = 4
        new_x = max(0, bx + tx - pad)
        new_y = max(0, by + ty - pad)
        new_w = min(img.shape[1] - new_x, tw + pad * 2)
        new_h = min(img.shape[0] - new_y, th + pad * 2)
        return (int(new_x), int(new_y), int(new_w), int(new_h))

    @staticmethod
    def _cluster_and_sort_spatially(
        boxes: List[Tuple[int, int, int, int]]
    ) -> List[Tuple[int, int, int, int]]:
        """Sorts bounding boxes into natural spatial reading order without grid hardcoding.
        
        Calculates centroids, clusters boxes by Y-band (rows) based on adaptive vertical distance,
        and sorts each row left-to-right by X-centroid.
        """
        if not boxes:
            return []

        heights = [b[3] for b in boxes]
        med_h = float(np.median(heights)) if heights else 150.0
        row_threshold = med_h * 0.45

        # Sort primarily by vertical center
        sorted_by_y = sorted(boxes, key=lambda b: b[1] + b[3] / 2.0)

        rows: List[List[Tuple[int, int, int, int]]] = []
        current_row: List[Tuple[int, int, int, int]] = []
        current_row_cy = 0.0

        for b in sorted_by_y:
            cy = b[1] + b[3] / 2.0
            if not current_row:
                current_row = [b]
                current_row_cy = cy
            else:
                if abs(cy - current_row_cy) <= row_threshold:
                    current_row.append(b)
                    current_row_cy = sum(bx[1] + bx[3] / 2.0 for bx in current_row) / len(current_row)
                else:
                    rows.append(current_row)
                    current_row = [b]
                    current_row_cy = cy
        if current_row:
            rows.append(current_row)

        ordered_boxes: List[Tuple[int, int, int, int]] = []
        for r in rows:
            r.sort(key=lambda b: b[0] + b[2] / 2.0)
            ordered_boxes.extend(r)

        return ordered_boxes

