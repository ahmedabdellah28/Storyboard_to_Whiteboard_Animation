import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import Tuple, Optional


class FillMode(Enum):
    TOP_TO_BOTTOM = "top_to_bottom"
    LEFT_TO_RIGHT = "left_to_right"
    CENTER_OUT = "center_out"
    FOLLOW_OUTLINE = "follow_outline"


@dataclass
class ColorRegion:
    color: Tuple[int, int, int]                         # (B, G, R) quantized fill color
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)      # (x, y, w, h)
    center: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=np.float64)) # (cx, cy)
    fill_mode: FillMode = FillMode.FOLLOW_OUTLINE
    dist_transform: Optional[np.ndarray] = None
    area: int = 0
    contour: Optional[np.ndarray] = None
    layer_id: int = 0
    priority: int = 0
    
    _cropped_mask: np.ndarray = None
    _full_shape: Tuple[int, int] = None

    def __init__(self, color, mask, bbox, area, center, fill_mode):
        self.color = color
        self.bbox = bbox
        self.area = area
        self.center = center
        self.fill_mode = fill_mode
        self.dist_transform = None
        self.layer_id = 0
        self.priority = 0
        self.contour = None
        
        # Memory Optimization: Store only the cropped bounding box of the mask
        bx, by, bw, bh = bbox
        self._cropped_mask = mask[by:by+bh, bx:bx+bw].copy()
        self._full_shape = mask.shape[:2]

    @property
    def cropped_mask(self) -> np.ndarray:
        return self._cropped_mask

    @property
    def mask(self) -> np.ndarray:
        """Dynamically reconstruct the full-size mask to save memory when full mask is requested."""
        if self._cropped_mask is None:
            return None
        full = np.zeros(self._full_shape, dtype=np.uint8)
        bx, by, bw, bh = self.bbox
        full[by:by+bh, bx:bx+bw] = self._cropped_mask
        return full

    def compute_bbox_and_center(self):
        y_indices, x_indices = np.where(self.mask > 0)
        if len(x_indices) > 0:
            min_x, max_x = int(np.min(x_indices)), int(np.max(x_indices))
            min_y, max_y = int(np.min(y_indices)), int(np.max(y_indices))
            self.bbox = (min_x, min_y, max(1, max_x - min_x + 1), max(1, max_y - min_y + 1))
            self.center = np.array([np.mean(x_indices), np.mean(y_indices)], dtype=np.float64)
