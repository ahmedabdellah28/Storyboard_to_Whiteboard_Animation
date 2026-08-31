import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import Tuple, Optional


class StrokeType(Enum):
    OUTER_OUTLINE = "outer_outline"       # Main bounding outline of shapes/objects
    INTERNAL_DETAIL = "internal_detail"   # Internal features (eyes, mouth, muscle cuts, clothing folds)
    COLOR_BOUNDARY = "color_boundary"     # Edges delineating distinct color regions
    MICRO_DETAIL = "micro_detail"         # Fine textures, shading, hatching
    FRAME_STROKE = "frame_stroke"         # Panel borders & structural frames (excluded from animation)


@dataclass
class Stroke:
    points: np.ndarray                              # shape (N, 2), float64 or int32 coordinates [x, y]
    stroke_type: StrokeType = StrokeType.INTERNAL_DETAIL
    color: Tuple[int, int, int] = (20, 20, 20)      # BGR format (dark sketch line default)
    width: float = 2.0                              # Stroke width in pixels
    length: float = 0.0                             # Cumulative arc length in pixels
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)  # (x, y, w, h)
    center: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=np.float64))  # (cx, cy)
    is_closed: bool = False
    is_frame: bool = False
    layer_id: int = 0
    priority: int = 0

    def __post_init__(self):
        if self.points is not None and len(self.points) > 0:
            if not isinstance(self.points, np.ndarray):
                self.points = np.array(self.points, dtype=np.float64)
            else:
                self.points = self.points.astype(np.float64)
            if self.length <= 0.0:
                self.compute_length()
            if self.bbox == (0, 0, 0, 0):
                self.compute_bbox()
            if np.all(self.center == 0):
                self.compute_center()

    def compute_length(self) -> float:
        if len(self.points) < 2:
            self.length = 0.0
            return 0.0
        diffs = np.diff(self.points, axis=0)
        dists = np.sqrt(np.sum(diffs ** 2, axis=1))
        self.length = float(np.sum(dists))
        if self.is_closed and len(self.points) > 2:
            close_dist = float(np.linalg.norm(self.points[-1] - self.points[0]))
            self.length += close_dist
        return self.length

    def compute_bbox(self) -> Tuple[int, int, int, int]:
        if len(self.points) == 0:
            self.bbox = (0, 0, 0, 0)
            return self.bbox
        min_x = int(np.min(self.points[:, 0]))
        min_y = int(np.min(self.points[:, 1]))
        max_x = int(np.max(self.points[:, 0]))
        max_y = int(np.max(self.points[:, 1]))
        self.bbox = (min_x, min_y, max(1, max_x - min_x), max(1, max_y - min_y))
        return self.bbox

    def compute_center(self) -> np.ndarray:
        if len(self.points) == 0:
            self.center = np.zeros(2, dtype=np.float64)
        else:
            self.center = np.mean(self.points, axis=0)
        return self.center

    def sub_path(self, progress: float) -> np.ndarray:
        """
        Returns the visible points up to the given progress [0.0, 1.0].
        Interpolates smoothly at the exact head point.
        """
        if progress <= 0.0 or len(self.points) == 0:
            return np.empty((0, 2), dtype=np.float64)
        if progress >= 1.0 or len(self.points) < 2:
            return self.points.copy()

        target_len = self.length * progress
        current_len = 0.0
        result_pts = [self.points[0]]

        pts_to_iterate = self.points
        if self.is_closed:
            pts_to_iterate = np.vstack([self.points, self.points[0:1]])

        for i in range(len(pts_to_iterate) - 1):
            p1 = pts_to_iterate[i]
            p2 = pts_to_iterate[i + 1]
            seg_len = float(np.linalg.norm(p2 - p1))
            if seg_len < 1e-6:
                continue

            if current_len + seg_len < target_len:
                current_len += seg_len
                result_pts.append(p2)
            else:
                # Interpolate head point
                remain = target_len - current_len
                t = remain / seg_len
                p_head = p1 + t * (p2 - p1)
                result_pts.append(p_head)
                break

        return np.array(result_pts, dtype=np.float64)
