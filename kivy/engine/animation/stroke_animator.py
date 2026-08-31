import cv2
import numpy as np
from typing import Callable, Optional
from ..core.stroke import Stroke
from .easing import get_easing


class StrokeAnimator:
    """
    V3.1 TrueColor Stroke Animator.
    Renders strokes by generating an anti-aliased spatial stroke mask,
    then pulling actual source artwork pixels from source_image.
    Zero synthetic/flat colors used during rendering.
    """

    @staticmethod
    def get_visible_path(
        stroke: Stroke,
        progress: float,
        easing_fn: Optional[Callable[[float], float]] = None
    ) -> np.ndarray:
        """
        Calculates the visible sub-path of a stroke at the given progress [0.0, 1.0].
        Applies easing before sub-path extraction.
        """
        if progress <= 0.0:
            return np.empty((0, 2), dtype=np.float64)
        if progress >= 1.0:
            return stroke.points.copy()

        if easing_fn is not None:
            eased_progress = easing_fn(progress)
        else:
            eased_progress = progress

        return stroke.sub_path(eased_progress)

    @staticmethod
    def render_stroke(
        canvas: np.ndarray,
        stroke: Stroke,
        progress: float,
        easing: str = "linear",
        source_image: Optional[np.ndarray] = None
    ):
        """
        Renders a stroke with progressive reveal:
        - When source_image is provided, pulls exact true artwork pixels under the stroke mask.
        - High-speed ROI-bounded rendering avoids allocating full canvas temporary buffers.
        """
        if progress <= 0.0:
            return

        pts = StrokeAnimator.get_visible_path(stroke, progress, get_easing(easing))
        if len(pts) < 2:
            return

        can_h, can_w = canvas.shape[:2]
        pts_int = pts.astype(np.int32)
        w = max(1, int(round(stroke.width)))
        is_closed = stroke.is_closed if progress >= 0.99 else False

        if source_image is not None:
            # Fast ROI bounding box computation for the stroke
            min_x = max(0, int(np.min(pts_int[:, 0])) - w - 2)
            max_x = min(can_w, int(np.max(pts_int[:, 0])) + w + 3)
            min_y = max(0, int(np.min(pts_int[:, 1])) - w - 2)
            max_y = min(can_h, int(np.max(pts_int[:, 1])) + w + 3)

            roi_w = max_x - min_x
            roi_h = max_y - min_y

            if roi_w <= 0 or roi_h <= 0:
                return

            # Draw stroke path inside localized ROI mask
            roi_mask = np.zeros((roi_h, roi_w), dtype=np.uint8)
            local_pts = pts_int - np.array([min_x, min_y], dtype=np.int32)
            cv2.polylines(roi_mask, [local_pts], is_closed, 255, w, cv2.LINE_AA)

            # Copy exact source pixels under the stroke mask onto the canvas
            src_roi = source_image[min_y:max_y, min_x:max_x]
            can_roi = canvas[min_y:max_y, min_x:max_x]
            mask_idx = roi_mask > 0
            can_roi[mask_idx] = src_roi[mask_idx]
        else:
            # Fallback when no source image is supplied
            cv2.polylines(canvas, [pts_int], is_closed, stroke.color, w, cv2.LINE_AA)
