from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional
import numpy as np

from .scene import Scene

class StructureType(Enum):
    STORYBOARD = "STORYBOARD"
    MULTI_PANEL_STORYBOARD = "STORYBOARD"
    SINGLE_SCENE = "SINGLE_SCENE"
    SINGLE_FRAMED_SCENE = "SINGLE_FRAMED_SCENE"
    SINGLE_UNFRAMED_SCENE = "SINGLE_UNFRAMED_SCENE"
    UNKNOWN = "UNKNOWN"

    @property
    def is_storyboard(self) -> bool:
        return self in (StructureType.STORYBOARD, StructureType.MULTI_PANEL_STORYBOARD)

    @property
    def is_single_scene(self) -> bool:
        return self in (StructureType.SINGLE_SCENE, StructureType.SINGLE_FRAMED_SCENE, StructureType.SINGLE_UNFRAMED_SCENE)


@dataclass
class PanelStructure:
    id: int
    bbox: Tuple[int, int, int, int]              # (x, y, w, h) of the entire panel including border
    interior_bbox: Tuple[int, int, int, int]     # (x, y, w, h) of the safe content area
    border_mask: np.ndarray                      # binary mask of the border
    number: Optional[int] = None                 # Panel number (metadata)
    row: int = 0                                 # Grid row index (0-based)
    column: int = 0                              # Grid column index (0-based)
    index: int = 0                               # Sequential reading-order index (0-based)
    content_score: float = 0.0                   # Density of content
    edge_density: float = 0.0                    # Edge pixel ratio within interior
    entropy: float = 0.0                         # Grayscale entropy of interior
    confidence: float = 0.0                      # Detection confidence for this panel
    is_empty: bool = False                       # True if content_score is below threshold
    is_frame: bool = True                        # Borders are structural frames
    content_region_image: Optional[np.ndarray] = None # Cropped interior image for pipeline
    source_image: Optional[np.ndarray] = None    # Full panel source image (incl. border) for rendering
    original_bbox_in_parent: Tuple[int, int, int, int] = (0, 0, 0, 0) # Used to trace back


@dataclass
class Project:
    structure_type: StructureType = StructureType.UNKNOWN
    confidence: float = 0.0
    panels: List[PanelStructure] = field(default_factory=list)
    scenes: List[Scene] = field(default_factory=list)
    source_image: Optional[np.ndarray] = None
    original_width: int = 0
    original_height: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def is_storyboard(self) -> bool:
        return self.structure_type.is_storyboard

    @property
    def is_single_scene(self) -> bool:
        return self.structure_type.is_single_scene

    def to_metadata_dict(self) -> dict:
        return {
            "structure_type": self.structure_type.value,
            "confidence": round(float(self.confidence), 4),
            "panel_count": len(self.panels),
            "detected_panels": [
                {
                    "id": p.id,
                    "bbox": p.bbox,
                    "interior_bbox": p.interior_bbox,
                    "row": p.row,
                    "col": p.column,
                    "content_score": round(float(p.content_score), 2),
                    "is_empty": p.is_empty
                }
                for p in self.panels
            ]
        }
