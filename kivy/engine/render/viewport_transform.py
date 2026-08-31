"""
Viewport Transform — Virtual Camera Affine Transform and Zoom Positioning.
"""
import cv2
import numpy as np


def render_camera_viewport(
    canvas: np.ndarray,
    center_x: float,
    center_y: float,
    zoom_scale: float,
    out_w: int = 1920,
    out_h: int = 1080
) -> np.ndarray:
    """Transforms virtual camera viewport with subpixel precision."""
    vw = out_w / zoom_scale
    vh = out_h / zoom_scale

    x1 = center_x - vw / 2.0
    y1 = center_y - vh / 2.0
    x2 = center_x + vw / 2.0
    y2 = center_y + vh / 2.0

    src_pts = np.float32([[x1, y1], [x2, y1], [x1, y2]])
    dst_pts = np.float32([[0, 0], [out_w, 0], [0, out_h]])
    matrix = cv2.getAffineTransform(src_pts, dst_pts)
    return cv2.warpAffine(
        canvas,
        matrix,
        (out_w, out_h),
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255)
    )
