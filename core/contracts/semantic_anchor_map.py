"""Contract 2: Semantic Anchor Map (semantic_anchor_map.json) - OSAS v3.1

Strict Rule: This contract maps author-ordered assets (sheet_order 1..N)
to semantic concepts and search anchor specifications from the script.
It NEVER changes the storyboard sheet_order, and NEVER creates runtime timestamps.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NarrativeRole(str, Enum):
    HERO = "HERO"
    SUPPORT = "SUPPORT"
    CONTEXT = "CONTEXT"
    DECORATIVE = "DECORATIVE"


class AnchorClassification(str, Enum):
    DIRECT_ANCHOR = "DIRECT_ANCHOR"
    CONTEXTUAL_ANCHOR = "CONTEXTUAL_ANCHOR"
    NARRATIVE_SUPPORT = "NARRATIVE_SUPPORT"
    DECORATIVE = "DECORATIVE"


class ResolutionTier(str, Enum):
    EXACT = "EXACT"
    NORMALIZED = "NORMALIZED"
    PREFIX_SUFFIX = "PREFIX_SUFFIX"
    TOKEN_PHRASE = "TOKEN_PHRASE"
    FUZZY_PHRASE = "FUZZY_PHRASE"
    MONOTONIC_CONTEXTUAL = "MONOTONIC_CONTEXTUAL"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


class ContextSearchWindow(BaseModel):
    sentence_index: int = Field(default=0, ge=0, description="Semantic sentence index used as bounded search window")
    bounding_phrase: str = Field(default="", description="Guiding sentence text for contextual bound")


class AnchorSpec(BaseModel):
    primary_anchor: str = Field(..., min_length=1, description="Primary Arabic anchor keyword or phrase")
    fallback_anchors: List[str] = Field(default_factory=list, description="Fallback Arabic keywords in preference order")
    context_search_window: ContextSearchWindow = Field(default_factory=ContextSearchWindow)


class SemanticMapping(BaseModel):
    sheet_order: int = Field(..., ge=1, description="Immutable storyboard spatial order (1..N)")
    visual_id: str = Field(..., description="Foreign key matching VisualEntity.visual_id in visual_manifest")
    narrative_role: NarrativeRole = Field(default=NarrativeRole.HERO)
    anchor_classification: AnchorClassification = Field(default=AnchorClassification.DIRECT_ANCHOR)
    is_required: bool = Field(default=True, description="Whether this asset MUST appear in the final video")
    semantic_concept: str = Field(..., description="Semantic meaning of this asset in the story")
    anchor_spec: AnchorSpec
    notes: str = Field(default="")


class SemanticAnchorMap(BaseModel):
    """Contract 2: Semantic Bridges Bound to Immutable Storyboard Order."""
    contract_type: str = Field(default="semantic_anchor_map", frozen=True)
    version: str = Field(default="3.1")
    section_id: str
    script_hash: str = Field(..., description="SHA-256 hash of source script.txt")
    manifest_hash: str = Field(..., description="SHA-256 hash of source visual_manifest.json")
    mappings: List[SemanticMapping] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_mapping_by_order(self, sheet_order: int) -> Optional[SemanticMapping]:
        for m in self.mappings:
            if m.sheet_order == sheet_order:
                return m
        return None

    def get_mapping_by_visual_id(self, visual_id: str) -> Optional[SemanticMapping]:
        for m in self.mappings:
            if m.visual_id == visual_id:
                return m
        return None
