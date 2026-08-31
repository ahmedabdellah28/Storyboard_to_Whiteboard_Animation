import cv2
import numpy as np
from typing import Callable, Optional
from ..core.region import ColorRegion, FillMode
from .easing import get_easing


class FillAnimator:
    """
    V3.1 TrueColor Fill Animator.
    Renders progressive fills by pulling 100% genuine pixels from source_image.
    Uses geometry-aware reveal dynamics (Follow Outline, Center-Out, Top-to-Bottom, Left-to-Right)
    with memoized distance transforms and ROI-bounded slicing for maximum performance.
    """

    @staticmethod
    def render_fill(
        canvas: np.ndarray,
        region: ColorRegion,
        progress: float,
        easing: str = "linear",
        source_image: Optional[np.ndarray] = None
    ):
        """
        Renders a color fill with progressive reveal directly within region ROI Bounding Box:
        - 100% TrueColor fidelity from source_image (exact artwork pixels)
        - High-speed slice-based rendering without allocating full-canvas temporary masks.
        """
        if progress <= 0.0 or region.cropped_mask is None:
            return

        bx, by, bw, bh = region.bbox
        can_h, can_w = canvas.shape[:2]

        # Clamp ROI to canvas bounds
        x1 = max(0, min(can_w, bx))
        y1 = max(0, min(can_h, by))
        x2 = max(0, min(can_w, bx + bw))
        y2 = max(0, min(can_h, by + bh))

        if x2 <= x1 or y2 <= y1:
            return

        cropped_m = region.cropped_mask[:(y2 - y1), :(x2 - x1)]

        if progress >= 1.0:
            if source_image is not None:
                src_roi = source_image[y1:y2, x1:x2]
                can_roi = canvas[y1:y2, x1:x2]
                can_roi[cropped_m > 0] = src_roi[cropped_m > 0]
            else:
                can_roi = canvas[y1:y2, x1:x2]
                can_roi[cropped_m > 0] = region.color
            return

        partial_roi_mask = FillAnimator.get_visible_roi_mask(region, progress, get_easing(easing))
        if partial_roi_mask is not None:
            partial_roi_mask = partial_roi_mask[:(y2 - y1), :(x2 - x1)]
            if source_image is not None:
                src_roi = source_image[y1:y2, x1:x2]
                can_roi = canvas[y1:y2, x1:x2]
                can_roi[partial_roi_mask > 0] = src_roi[partial_roi_mask > 0]
            else:
                can_roi = canvas[y1:y2, x1:x2]
                can_roi[partial_roi_mask > 0] = region.color

    @staticmethod
    def get_visible_roi_mask(
        region: ColorRegion,
        progress: float,
        easing_fn: Optional[Callable[[float], float]] = None
    ) -> np.ndarray:
        """
        Generates a partial binary mask of the region at the given progress [0.0, 1.0]
        strictly inside the region bounding box (ROI).
        """
        cmask = region.cropped_mask
        if progress <= 0.0 or cmask is None:
            return np.zeros_like(cmask) if cmask is not None else np.zeros((1, 1), dtype=np.uint8)
        if progress >= 1.0:
            return cmask.copy()

        if easing_fn is not None:
            eased_prog = float(easing_fn(progress))
        else:
            eased_prog = float(progress)

        eased_prog = max(0.0, min(1.0, eased_prog))
        bh, bw = cmask.shape[:2]
        mode = region.fill_mode

        if mode == FillMode.TOP_TO_BOTTOM:
            reveal_y = int(round(bh * eased_prog))
            partial = np.zeros_like(cmask)
            if reveal_y > 0:
                partial[:reveal_y, :] = cmask[:reveal_y, :]
            return partial

        elif mode == FillMode.LEFT_TO_RIGHT:
            reveal_x = int(round(bw * eased_prog))
            partial = np.zeros_like(cmask)
            if reveal_x > 0:
                partial[:, :reveal_x] = cmask[:, :reveal_x]
            return partial

        elif mode == FillMode.CENTER_OUT:
            bx, by = region.bbox[0], region.bbox[1]
            local_cx = int(region.center[0] - bx)
            local_cy = int(region.center[1] - by)
            corners = np.array([[0, 0], [bw, 0], [0, bh], [bw, bh]])
            max_dist = float(np.max(np.linalg.norm(corners - np.array([local_cx, local_cy]), axis=1)))
            curr_radius = int(round(max_dist * eased_prog))

            circle_mask = np.zeros_like(cmask)
            if curr_radius > 0:
                cv2.circle(circle_mask, (local_cx, local_cy), curr_radius, 255, -1)
            return cv2.bitwise_and(cmask, circle_mask)

        else:  # FOLLOW_OUTLINE
            if region.dist_transform is None:
                # Memoize distance transform on ROI mask
                region.dist_transform = cv2.distanceTransform(cmask, cv2.DIST_L2, 5)
                region.max_dist = float(np.max(region.dist_transform)) if np.any(region.dist_transform) else 1.0

            if region.max_dist <= 0:
                return cmask.copy()

            threshold = region.max_dist * (1.0 - eased_prog)
            _, revealed = cv2.threshold(
                region.dist_transform, threshold, 255, cv2.THRESH_BINARY
            )
            return revealed.astype(np.uint8)
