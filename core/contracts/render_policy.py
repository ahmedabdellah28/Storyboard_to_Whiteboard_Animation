"""Render Policy Configuration Model.

Defines all tunable directorial and engineering constraints as policies,
eliminating magic numbers and hardcoded truths from the runtime engine.
"""

from __future__ import annotations

from typing import Dict
from pydantic import BaseModel, Field


class RoleSpeedLimit(BaseModel):
    max_speedup_factor: float = Field(..., ge=1.0, le=4.0)
    max_lead_in_s: float = Field(..., ge=0.0, le=3.0)
    min_duration_s: float = Field(..., ge=0.4, le=10.0)
    max_duration_s: float = Field(..., ge=1.0, le=20.0)


class SpeedLimitsPolicy(BaseModel):
    hero: RoleSpeedLimit = Field(
        default_factory=lambda: RoleSpeedLimit(
            max_speedup_factor=1.35,
            max_lead_in_s=1.50,
            min_duration_s=2.0,
            max_duration_s=4.8,
        )
    )
    support: RoleSpeedLimit = Field(
        default_factory=lambda: RoleSpeedLimit(
            max_speedup_factor=1.70,
            max_lead_in_s=0.80,
            min_duration_s=1.2,
            max_duration_s=3.0,
        )
    )
    context: RoleSpeedLimit = Field(
        default_factory=lambda: RoleSpeedLimit(
            max_speedup_factor=2.00,
            max_lead_in_s=0.40,
            min_duration_s=0.8,
            max_duration_s=2.2,
        )
    )
    decorative: RoleSpeedLimit = Field(
        default_factory=lambda: RoleSpeedLimit(
            max_speedup_factor=2.20,
            max_lead_in_s=0.00,
            min_duration_s=0.6,
            max_duration_s=1.8,
        )
    )


class OverlapPolicyConfig(BaseModel):
    max_accidental_overlap_ratio: float = Field(default=0.20, ge=0.0, le=1.0)
    collision_action: str = Field(default="CAMERA_PAN_TO_CLEAR_ZONE")
    fallback_wipe_action: str = Field(default="SOFT_WIPE_PREVIOUS")


class TemporalPolicyConfig(BaseModel):
    allow_parallel_drawing: bool = Field(default=False)
    ink_resource_id: str = Field(default="INK_RESOURCE_01")
    ink_switch_margin_s: float = Field(
        default=0.05, ge=0.0, le=0.50, description="Configurable minimum idle buffer between sequential inking operations"
    )
    max_unexplained_blank_s: float = Field(
        default=0.25, ge=0.0, le=1.00, description="Maximum permissible unexplained blank opening duration"
    )
    min_gap_between_beats_s: float = Field(default=0.15, ge=0.0)
    max_lookahead_words: int = Field(default=75, ge=5)


class DemandWeightsConfig(BaseModel):
    pixel_mass_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    contour_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    edge_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    stroke_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    area_weight: float = Field(default=0.10, ge=0.0, le=1.0)


class RenderPolicy(BaseModel):
    policy_id: str = "documentary_balanced_v2"
    version: str = "2.0"
    speed_limits: SpeedLimitsPolicy = Field(default_factory=SpeedLimitsPolicy)
    overlap: OverlapPolicyConfig = Field(default_factory=OverlapPolicyConfig)
    temporal: TemporalPolicyConfig = Field(default_factory=TemporalPolicyConfig)
    demand_weights: DemandWeightsConfig = Field(default_factory=DemandWeightsConfig)
