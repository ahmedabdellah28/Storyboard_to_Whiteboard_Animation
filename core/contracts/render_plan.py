"""Contract 3: Final Render Plan (final_render_plan.json)

Strict Rule: This contract represents the 'PHYSICAL EXECUTION TRUTH'.
It contains concrete timestamps (seconds), viewport geometry, camera trajectories,
and audio SFX cues computed 100% deterministically without any runtime LLM call.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class MatchTier(str, Enum):
    EXACT = "Exact"
    NORMALIZED = "Normalized"
    TOKEN = "Token"
    PHONETIC = "Phonetic"
    CONTEXTUAL = "Contextual"
    AMBIGUOUS = "Ambiguous"
    UNRESOLVED = "Unresolved"


class CollisionClassification(str, Enum):
    NONE = "NONE"
    INTENTIONAL_OVERLAP = "INTENTIONAL_OVERLAP"
    SAFE_COMPOSITION = "SAFE_COMPOSITION"
    RESOLVED_BY_CAMERA = "RESOLVED_BY_CAMERA"
    RESOLVED_BY_WIPE = "RESOLVED_BY_WIPE"


class ResolvedAnchor(BaseModel):
    matched_text: str
    whisper_t_start: float = Field(..., ge=0.0)
    whisper_t_end: float = Field(..., ge=0.0)
    match_tier: MatchTier
    confidence: float = Field(..., ge=0.0, le=1.0)
    matched_word_indices: List[int] = Field(default_factory=list)


class TimingSpec(BaseModel):
    lead_in_s: float = Field(..., ge=0.0, description="Lead-in time before speech anchor")
    ink_start_s: float = Field(..., ge=0.0, description="Timestamp when inking animation starts")
    ink_end_s: float = Field(..., ge=0.0, description="Timestamp when inking animation completes")
    draw_duration_s: float = Field(..., gt=0.0, description="Active drawing/inking duration")
    speed_multiplier: float = Field(default=1.0, ge=0.5, le=3.0, description="Speed scaling factor applied to inking")
    hold_until_s: float = Field(..., ge=0.0, description="Timestamp until which the asset remains visible on canvas")


class ViewportPlacement(BaseModel):
    target_center: Tuple[int, int] = Field(..., description="[center_x, center_y] in canvas coordinates")
    scale: float = Field(default=1.0, gt=0.0)
    render_layer: int = Field(default=0, ge=0)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)


class VisualBeat(BaseModel):
    beat_id: str = Field(..., description="Unique beat ID (e.g. beat_001)")
    concept_id: str
    visual_id: str
    resolved_anchor: ResolvedAnchor
    timing: TimingSpec
    viewport: ViewportPlacement
    collision_classification: CollisionClassification = CollisionClassification.NONE


class CameraKeyframe(BaseModel):
    t: float = Field(..., ge=0.0, description="Time in seconds")
    viewport_rect: Tuple[int, int, int, int] = Field(
        ..., description="[x, y, width, height] viewport rectangle"
    )
    focus_beat_id: Optional[str] = None
    interpolation: str = Field(default="cubic_hermite", description="Easing / interpolation type")


class SFXCue(BaseModel):
    t_start: float = Field(..., ge=0.0)
    t_end: float = Field(..., ge=0.0)
    sfx_profile: str = Field(default="whiteboard_ink_dense")
    duck_speech_db: float = Field(default=-3.0, description="Amount to duck background audio during drawing")


class ExecutionTracks(BaseModel):
    visual_beats: List[VisualBeat] = Field(default_factory=list)
    camera_path: List[CameraKeyframe] = Field(default_factory=list)
    sfx_cues: List[SFXCue] = Field(default_factory=list)


class FinalRenderPlan(BaseModel):
    """Contract 3: Concrete Deterministic Execution Plan."""
    contract_type: str = Field(default="final_render_plan", frozen=True)
    version: str = Field(default="2.0")
    section_id: str
    total_duration_s: float = Field(..., gt=0.0)
    render_policy_id: str = "default_policy"
    
    # Cryptographic integrity hashes
    source_audio_hash: str
    narrative_map_hash: str
    manifest_hash: str
    policy_hash: str

    execution_tracks: ExecutionTracks = Field(default_factory=ExecutionTracks)
    metadata: Dict[str, Any] = Field(default_factory=dict)
