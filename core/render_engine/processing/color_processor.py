import cv2
import numpy as np
from typing import Tuple, List, Dict
from ..core.scene import SceneConfig


class ColorProcessor:
    @staticmethod
    def quantize(
        image_bgr: np.ndarray,
        config: SceneConfig
    ) -> Tuple[np.ndarray, List[Tuple[int, int, int]], Tuple[int, int, int]]:
        """
        Quantizes the image to a compact palette using k-means in LAB color space.
        Returns:
        - quantized_bgr: np.ndarray of shape (H, W, 3)
        - palette: list of (B, G, R) color tuples
        - background_color: detected background (B, G, R)
        """
        h, w = image_bgr.shape[:2]
        
        # Subsample if image is large for ultra-fast k-means clustering
        scale = 1.0
        if max(h, w) > 720:
            scale = 720.0 / max(h, w)
            small_bgr = cv2.resize(image_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        else:
            small_bgr = image_bgr

        # Convert to LAB space for perceptually uniform clustering
        lab_small = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2LAB)
        pixel_data = lab_small.reshape((-1, 3)).astype(np.float32)

        K = max(4, min(32, config.color_palette_size))
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 12, 1.0)
        flags = cv2.KMEANS_PP_CENTERS

        _, labels, centers = cv2.kmeans(
            pixel_data, K, None, criteria, 8, flags
        )

        centers_lab = np.uint8(centers).reshape((1, K, 3))
        centers_bgr = cv2.cvtColor(centers_lab, cv2.COLOR_LAB2BGR).reshape((K, 3))

        # Reconstruct quantized full image
        lab_full = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
        # Find nearest center for each pixel in full image
        # Using 1D LUT / nearest neighbor mapping
        
        # Ultra-fast nearest cluster assignment using BLAS matrix multiplication
        # Mathematically equivalent to Euclidean distance, but runs in multi-threaded C
        flat_lab = lab_full.reshape((-1, 3))
        
        a_sq = np.sum(flat_lab ** 2, axis=1, keepdims=True)
        b_sq = np.sum(centers ** 2, axis=1)
        dot_ab = np.dot(flat_lab, centers.T)
        
        dists = a_sq + b_sq - 2 * dot_ab
        best_cluster_idx = np.argmin(dists, axis=1).astype(np.int32)
        
        quantized_flat = centers_bgr[best_cluster_idx]
        quantized_bgr = quantized_flat.reshape((h, w, 3)).astype(np.uint8)

        # Build palette tuples (B, G, R)
        palette = [tuple(int(c) for c in color) for color in centers_bgr]

        # Detect dominant background color from actual source image perimeter spatial sampling
        border_top = image_bgr[0, :]
        border_bottom = image_bgr[-1, :]
        border_left = image_bgr[:, 0]
        border_right = image_bgr[:, -1]
        border_pixels = np.concatenate([border_top, border_bottom, border_left, border_right], axis=0)
        
        median_bg = np.median(border_pixels, axis=0).astype(np.uint8)
        background_color = (int(median_bg[0]), int(median_bg[1]), int(median_bg[2]))

        return quantized_bgr, palette, background_color
