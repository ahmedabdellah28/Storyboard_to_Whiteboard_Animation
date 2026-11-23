import cv2
import numpy as np
from dataclasses import dataclass, field


@dataclass
class CameraState:
    x: float = 960.0                     # Viewport focus center X on scene canvas
    y: float = 540.0                     # Viewport focus center Y on scene canvas
    zoom: float = 1.0                    # Zoom level (1.0 = full canvas view, >1.0 = zoomed in)
    rotation: float = 0.0                # Rotation angle in degrees


class Camera:
    def __init__(
        self,
        scene_width: int = 1920,
        scene_height: int = 1080,
        output_width: int = 1920,
        output_height: int = 1080
    ):
        self.scene_width = scene_width
        self.scene_height = scene_height
        self.output_width = output_width
        self.output_height = output_height

    def apply(self, scene_canvas: np.ndarray, state: CameraState) -> np.ndarray:
        return self.apply_to_frame(scene_canvas, state)

    def apply_to_frame(self, scene_canvas: np.ndarray, state: CameraState) -> np.ndarray:
        """
        Extracts and transforms the camera viewport from the scene canvas
        to produce the final frame matching output_width x output_height.
        """
        # If zoom is 1.0, no rotation, and center is at scene center -> return direct resized canvas
        default_cx = self.scene_width / 2.0
        default_cy = self.scene_height / 2.0
        is_default = (
            abs(state.zoom - 1.0) < 1e-4 and
            abs(state.rotation) < 1e-4 and
            abs(state.x - default_cx) < 1.0 and
            abs(state.y - default_cy) < 1.0
        )
        if is_default:
            if scene_canvas.shape[1] == self.output_width and scene_canvas.shape[0] == self.output_height:
                return scene_canvas.copy()
            return cv2.resize(scene_canvas, (self.output_width, self.output_height), interpolation=cv2.INTER_LANCZOS4)

        # Clamped zoom
        zoom = max(1.0, min(3.5, float(state.zoom)))

        # Viewport dimensions on scene canvas
        vp_w = self.scene_width / zoom
        vp_h = self.scene_height / zoom

        # Clamped center to stay inside scene bounds
        min_x = vp_w / 2.0
        max_x = self.scene_width - vp_w / 2.0
        min_y = vp_h / 2.0
        max_y = self.scene_height - vp_h / 2.0

        cx = max(min_x, min(max_x, float(state.x))) if max_x >= min_x else default_cx
        cy = max(min_y, min(max_y, float(state.y))) if max_y >= min_y else default_cy

        # Affine transform mapping 3 viewport points to output corners
        src_pts = np.float32([
            [cx - vp_w / 2.0, cy - vp_h / 2.0],  # Top-left
            [cx + vp_w / 2.0, cy - vp_h / 2.0],  # Top-right
            [cx - vp_w / 2.0, cy + vp_h / 2.0],  # Bottom-left
        ])

        dst_pts = np.float32([
            [0, 0],
            [self.output_width - 1, 0],
            [0, self.output_height - 1]
        ])

        M = cv2.getAffineTransform(src_pts, dst_pts)
        out_frame = cv2.warpAffine(
            scene_canvas, M, (self.output_width, self.output_height),
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0)  # V3: Canvas already has correct bg color
        )
        return out_frame
