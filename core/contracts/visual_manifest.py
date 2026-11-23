"""Contract 1: Visual Manifest (visual_manifest.json)

Strict Rule: This contract describes ONLY 'WHAT IS IN THE STORYBOARD'.
It contains purely visual and spatial truth:
- Bounding boxes, crops, masks
- Composite Scene vs Atomic Object classification
- Normalized visual demand metrics (pixel mass, contour, edge complexity)
- Intrinsic visual tags and structural spatial relationships
It NEVER contains script text, narrative anchors, or runtime timestamps.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class VisualType(str, Enum):
    ATOMIC_OBJECT = "atomic_object"
    COMPOSITE_SCENE = "composite_scene"
    CHARACTER = "character"
    BACKGROUND = "background"
    PROP = "prop"
    DECORATIVE = "decorative"
    UNKNOWN = "unknown"


class SpatialRelationType(str, Enum):
    SUBPART_OF = "subpart_of"
    FOREGROUND_OF = "foreground_of"
    ADJACENT_TO = "adjacent_to"
    SUBPART_OVERLAP = "subpart_overlap"


class ExtractionStatus(str, Enum):
    VALID_REQUIRED_ASSET = "VALID_REQUIRED_ASSET"
    FRAGMENT = "FRAGMENT"
    DUPLICATE = "DUPLICATE"
    DECORATIVE = "DECORATIVE"
    INVALID_CROP = "INVALID_CROP"


class NormalizedDemandMetrics(BaseModel):
    normalized_pixel_mass: float = Field(
        ..., ge=0.0, le=1.0, description="Foreground non-zero pixels relative to entity bbox area"
    )
    normalized_contour_length: float = Field(
        ..., ge=0.0, le=1.0, description="Total contour perimeter normalized to theoretical maximum"
    )
    normalized_edge_complexity: float = Field(
        ..., ge=0.0, le=1.0, description="Canny/Sobel high-frequency edge density in foreground"
    )
    stroke_count_estimate: int = Field(
        ..., ge=1, description="Estimated hand stroke count from skeleton/contour topology"
    )
    aspect_ratio: float = Field(
        ..., gt=0.0, description="Width / Height aspect ratio"
    )
    raw_demand_score: float = Field(
        ..., ge=0.0, le=1.0, description="Weighted composite demand score [0.0, 1.0]"
    )
    demand_range_s: Dict[str, float] = Field(
        default_factory=lambda: {"min_s": 1.2, "target_s": 2.0, "max_s": 3.5},
        description="Dynamic demand range (min, target, max duration) based on visual complexity",
    )


class VisualEntity(BaseModel):
    visual_id: str = Field(..., description="Unique immutable identifier within the storyboard")
    sheet_order: int = Field(default=1, ge=1, description="Immutable spatial order within the storyboard sheet (1..N)")
    centroid: Tuple[int, int] = Field(default=(0, 0), description="[cx, cy] center of the detected asset in canvas space")
    extraction_status: ExtractionStatus = Field(default=ExtractionStatus.VALID_REQUIRED_ASSET)
    visual_type: VisualType = Field(default=VisualType.ATOMIC_OBJECT)
    bbox: Tuple[int, int, int, int] = Field(
        ..., description="[x, y, width, height] in original canvas coordinates"
    )
    mask_crop_path: str = Field(
        ..., description="Relative path to transparent PNG crop with alpha mask"
    )
    sub_components: List[str] = Field(
        default_factory=list, description="IDs of sub-entities if this is a composite scene"
    )
    demand_metrics: NormalizedDemandMetrics
    visual_tags: List[str] = Field(
        default_factory=list, description="Purely visual descriptors (e.g. warrior, beard, horse, spear)"
    )
    description: str = Field(
        default="", description="Visual summary of the asset appearance"
    )


class SpatialRelation(BaseModel):
    source: str = Field(..., description="visual_id of the source entity")
    target: str = Field(..., description="visual_id of the target entity")
    type: SpatialRelationType = Field(default=SpatialRelationType.ADJACENT_TO)
    allowed_overlap_ratio: float = Field(
        default=0.25, ge=0.0, le=1.0, description="Permissible overlap ratio without triggering collision"
    )


class VisualManifest(BaseModel):
    """Contract 1: Pure Storyboard Visual Truth."""
    contract_type: str = Field(default="visual_manifest", frozen=True)
    version: str = Field(default="2.0")
    storyboard_id: str
    storyboard_hash: str = Field(..., description="SHA-256 hash of the source storyboard image")
    canvas_dimensions: Dict[str, int] = Field(
        default_factory=lambda: {"width": 1920, "height": 1080}
    )
    entities: List[VisualEntity] = Field(default_factory=list)
    structural_spatial_relations: List[SpatialRelation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_entity(self, visual_id: str) -> Optional[VisualEntity]:
        for e in self.entities:
            if e.visual_id == visual_id:
                return e
        return None
