"""Canonical Visual Unit Models and Manifest Schemas for Whiteboard Production.

Strict Rule: Visual manifests contain semantic concepts, anchors, and roles.
They NEVER contain final runtime timestamps.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VisualUnitType(str, Enum):
    ATOMIC_OBJECT = "ATOMIC_OBJECT"
    CHARACTER = "CHARACTER"
    CHARACTER_GROUP = "CHARACTER_GROUP"
    COMPOSITE_SCENE = "COMPOSITE_SCENE"
    ENVIRONMENT = "ENVIRONMENT"
    SYMBOLIC_VISUAL = "SYMBOLIC_VISUAL"
    BACKGROUND = "BACKGROUND"
    SUPPORT_ELEMENT = "SUPPORT_ELEMENT"
    DECORATIVE_ELEMENT = "DECORATIVE_ELEMENT"
    UNKNOWN = "UNKNOWN"


class ImportanceRole(str, Enum):
    HERO = "HERO"
    SUPPORT = "SUPPORT"
    CONTEXT = "CONTEXT"
    DECORATIVE = "DECORATIVE"


class ReuseMode(str, Enum):
    DRAW_ONCE_AND_HOLD = "DRAW_ONCE_AND_HOLD"
    DRAW_ONCE_AND_REUSE = "DRAW_ONCE_AND_REUSE"
    DRAW_AGAIN = "DRAW_AGAIN"
    BACKGROUND_PERSISTENCE = "BACKGROUND_PERSISTENCE"
    TEMPORARY_SUPPORT = "TEMPORARY_SUPPORT"
    INSTANT_REVEAL = "INSTANT_REVEAL"


class ReviewDecision(str, Enum):
    KEEP_ATOMIC = "KEEP_ATOMIC"
    KEEP_COMPOSITE = "KEEP_COMPOSITE"
    SPLIT = "SPLIT"
    MERGE = "MERGE"
    DISCARD = "DISCARD"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class ResolutionStatus(str, Enum):
    EXACT = "EXACT"
    STRONG_SEMANTIC = "STRONG_SEMANTIC"
    CONTEXTUAL = "CONTEXTUAL"
    WEAK = "WEAK"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


class DrawDemand(BaseModel):
    estimated: float = Field(..., description="Estimated drawing duration in seconds")
    min: float = Field(..., description="Minimum duration required for visual legibility")
    max: float = Field(..., description="Maximum duration before viewer disengagement")


class VisualConcept(BaseModel):
    concept_id: str
    asset_ids: List[str]
    primary_anchor: str
    fallback_anchors: List[str] = Field(default_factory=list)
    semantic_keywords: List[str] = Field(default_factory=list)
    synonyms: List[str] = Field(default_factory=list)
    concept_group: str = "main"
    narrative_role: str = "subject"
    importance: ImportanceRole = ImportanceRole.HERO
    reuse_mode: ReuseMode = ReuseMode.DRAW_ONCE_AND_HOLD
    visual_unit_type: VisualUnitType = VisualUnitType.CHARACTER
    draw_demand: DrawDemand
    anim_type: str = "outside_in_pen"
    depth: int = 5
    description: str = ""


class NarrativeMapping(BaseModel):
    concept_id: str
    script_span: str
    primary_anchor: str
    confidence: float = 1.0
    resolution_status: ResolutionStatus = ResolutionStatus.STRONG_SEMANTIC
    reason: str = ""


class AssetReview(BaseModel):
    candidate_id: str
    decision: ReviewDecision
    type: VisualUnitType
    semantic_label: str
    reason: str
    confidence: float = 1.0
    errors_detected: List[str] = Field(default_factory=list)


class VisualReviewReport(BaseModel):
    storyboard_id: str
    review_summary: Dict[str, int] = Field(default_factory=dict)
    asset_reviews: List[AssetReview] = Field(default_factory=list)
    semantic_concepts: List[VisualConcept] = Field(default_factory=list)
    narrative_mapping: List[NarrativeMapping] = Field(default_factory=list)
    missing_visuals: List[Dict[str, Any]] = Field(default_factory=list)
    unused_visuals: List[str] = Field(default_factory=list)
    ambiguities: List[Dict[str, Any]] = Field(default_factory=list)


class VisualManifest(BaseModel):
    storyboard_id: str
    version: str = "2.0"
    concepts: List[VisualConcept]
    assets: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_legacy_metadata(self) -> Dict[str, Any]:
        """Convert manifest concepts to legacy metadata.json dictionary for backward compatibility."""
        out = {}
        for c in self.concepts:
            for aid in c.asset_ids:
                asset_info = self.assets.get(aid, {})
                out[aid] = {
                    "file": asset_info.get("file", f"{aid}.png"),
                    "desc": c.description or c.primary_anchor,
                    "role": "hero" if c.importance == ImportanceRole.HERO else "supporting",
                    "anim_type": c.anim_type,
                    "orig_size": asset_info.get("orig_size", [300, 300]),
                    "drawing_demand": c.draw_demand.estimated,
                    "area": asset_info.get("area", 90000),
                }
        return out
