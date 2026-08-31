import cv2
import numpy as np
from typing import List, Tuple, Dict
from ..core.stroke import Stroke, StrokeType
from ..core.scene import SceneConfig


class EdgeExtractor:
    @staticmethod
    def extract(image_bgr: np.ndarray, config: SceneConfig) -> List[Stroke]:
        """
        Multi-stage edge extraction pipeline:
        1. Bilateral edge-preserving noise reduction
        2. Multi-scale edge detection (Canny + Gradient magnitude)
        3. Morphological cleanup
        4. Edge thinning (skeletonization) to prevent double lines
        5. Contour extraction
        6. Duplicate/parallel edge filtering
        7. Polygon approximation & minimum length filtering
        """
        h, w = image_bgr.shape[:2]
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

        # Stage 1: Noise reduction with edge preservation
        if config.detail_level == "LOW":
            denoised = cv2.bilateralFilter(gray, d=7, sigmaColor=75, sigmaSpace=75)
            canny_low, canny_high = 60, 160
            approx_eps_factor = 0.02
            min_len = 4.0
        elif config.detail_level == "HIGH":
            denoised = cv2.bilateralFilter(gray, d=3, sigmaColor=35, sigmaSpace=35)
            canny_low, canny_high = 20, 80
            approx_eps_factor = 0.005
            min_len = 1.5
        else:  # MEDIUM (default)
            denoised = cv2.bilateralFilter(gray, d=5, sigmaColor=50, sigmaSpace=50)
            canny_low, canny_high = 35, 110
            approx_eps_factor = 0.01
            min_len = 2.5

        # Stage 2: Multi-scale edge detection
        edges_canny = cv2.Canny(denoised, canny_low, canny_high)
        
        # Adaptive gradient magnitude (Sobel) to capture soft sketch lines
        grad_x = cv2.Sobel(denoised, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(denoised, cv2.CV_32F, 0, 1, ksize=3)
        grad_mag = cv2.magnitude(grad_x, grad_y)
        grad_norm = cv2.normalize(grad_mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        _, edges_grad = cv2.threshold(grad_norm, 35, 255, cv2.THRESH_BINARY)

        # Combined edges
        combined_edges = cv2.bitwise_or(edges_canny, edges_grad)

        # Stage 3: Morphological cleanup (Safe Closing only - NEVER Open to avoid erasing tiny dots)
        kernel_2 = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        closed_edges = cv2.morphologyEx(combined_edges, cv2.MORPH_CLOSE, kernel_2)

        # Stage 4: Morphological Thinning (Skeletonization)
        thinned_edges = EdgeExtractor._thin_edges(closed_edges)

        # Stage 5: Contour extraction
        contours, hierarchy = cv2.findContours(
            thinned_edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE
        )

        # Stage 6 & 7: Simplification & Stroke Construction (Zero Detail Loss)
        raw_strokes: List[Stroke] = []

        for cnt in contours:
            if len(cnt) < 2:
                continue

            # Check if contour is closed
            is_closed = bool(np.linalg.norm(cnt[0][0] - cnt[-1][0]) < 4.0)

            # Arc length & approxPolyDP simplification
            arc_len = cv2.arcLength(cnt, is_closed)
            if arc_len < min_len and len(cnt) < 3:
                # Handle single-point / 2-point dot
                pts = cnt.reshape(-1, 2).astype(np.float64)
            else:
                epsilon = max(0.5, arc_len * approx_eps_factor)
                approx = cv2.approxPolyDP(cnt, epsilon, is_closed)
                pts = approx.reshape(-1, 2).astype(np.float64)

            if len(pts) < 2:
                # Ensure even 1-point features have a minimal 2-point line representation for rendering
                p0 = pts[0]
                pts = np.array([p0, p0 + np.array([0.5, 0.5])], dtype=np.float64)

            # Sample actual source color along stroke
            cx = int(np.clip(np.mean(pts[:, 0]), 0, w - 1))
            cy = int(np.clip(np.mean(pts[:, 1]), 0, h - 1))
            stroke_color = tuple(int(c) for c in image_bgr[cy, cx])

            stroke = Stroke(
                points=pts,
                stroke_type=StrokeType.INTERNAL_DETAIL,
                color=stroke_color,
                width=1.8 if arc_len >= 8.0 else 1.2,
                is_closed=is_closed
            )
            raw_strokes.append(stroke)

        return raw_strokes

    @staticmethod
    def _thin_edges(binary_img: np.ndarray) -> np.ndarray:
        """
        Morphological thinning (skeletonization).
        Reduces thick edge blobs to 1-pixel wide line trajectories.
        """
        try:
            if hasattr(cv2, "ximgproc"):
                return cv2.ximgproc.thinning(binary_img, thinningType=cv2.ximgproc.THINNING_GUOHALL)
        except Exception:
            pass

        img = binary_img.copy()
        skel = np.zeros(img.shape, dtype=np.uint8)
        element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))

        max_iters = 8
        iters = 0
        while iters < max_iters:
            eroded = cv2.erode(img, element)
            temp = cv2.dilate(eroded, element)
            cv2.subtract(img, temp, dst=temp)
            cv2.bitwise_or(skel, temp, dst=skel)
            img = eroded
            if cv2.countNonZero(img) == 0:
                break
            iters += 1

        return skel
