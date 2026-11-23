"""Contract 3 & 4: Visual Choreography and Execution Models - OSAS v3.1

Defines the physical execution events, single-ink resource constraints,
hold durations, and camera alignment.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from core.contracts.semantic_anchor_map import ResolutionTier


class ChoreographyEvent(BaseModel):
    sequence: int = Field(..., ge=1, description="Execution sequence index (1..N)")
    sheet_order: int = Field(..., ge=1, description="Storyboard spatial order (must match sequence monotonically)")
    asset_id: str = Field(..., description="Unique visual ID")
    resolution_tier: ResolutionTier = Field(default=ResolutionTier.EXACT)
    resolved_text: str = Field(..., description="The exact matched text in spoken audio")
    anchor_time_s: float = Field(..., ge=0.0, description="Ground truth Whisper timestamp of spoken anchor")
    draw_start_s: float = Field(..., ge=0.0, description="Pen inking start timestamp")
    draw_end_s: float = Field(..., ge=0.0, description="Pen inking completion timestamp")
    hold_end_s: float = Field(..., ge=0.0, description="Hold duration end timestamp (explanation completion)")
    ink_resource_id: str = Field(default="INK_RESOURCE_01", description="Exclusive physical inking resource ID")
    target_screen_zone: int = Field(default=1, ge=1, description="Spatial camera zone index")
    viewport_scale: float = Field(default=3.0, gt=0.0, description="World space scale factor")


class VisualChoreography(BaseModel):
    """Contract: Physical Choreography Timeline."""
    contract_type: str = Field(default="visual_choreography", frozen=True)
    version: str = Field(default="3.1")
    section_id: str
    audio_duration_s: float
    total_events: int
    events: List[ChoreographyEvent] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
