"""Contract 2: Narrative Visual Map (narrative_visual_map.json)

Strict Rule: This contract describes 'HOW DOES THIS STORYBOARD SERVE THIS SCRIPT?'.
It links Visual Entities (from visual_manifest.json) to Narrative Concepts:
- Concept IDs, roles, and importance weights
- Weighted anchor candidates (identity, semantic, support) for deterministic resolution
- Semantic script references
- Visual continuity and flow rules (e.g. intentional overlap, antecedent ordering)
It NEVER contains concrete runtime timestamps (no seconds, no start/end times).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NarrativeRole(str, Enum):
    HERO = "hero"
    SUPPORT = "support"
    CONTEXT = "context"
    DECORATIVE = "decorative"


class AnchorType(str, Enum):
    IDENTITY = "identity"  # e.g., "غوان يو", "عمر المختار"
    SEMANTIC = "semantic"  # e.g., "أسطورته", "قائدهم"
    SUPPORT = "support"    # e.g., "الشجاعة والفروسية"


class OverlapPolicy(str, Enum):
    INTENTIONAL_OVERLAP = "INTENTIONAL_OVERLAP"
    SAFE_COMPOSITION = "SAFE_COMPOSITION"
    UNSAFE_OCCLUSION = "UNSAFE_OCCLUSION"
    DISALLOWED_COLLISION = "DISALLOWED_COLLISION"


class OrderConstraint(str, Enum):
    ANTECEDENT_BEFORE_CONSEQUENT = "antecedent_before_consequent"
    SIMULTANEOUS_REVEAL = "simultaneous_reveal"
    INDEPENDENT = "independent"


class AnchorCandidate(BaseModel):
    text: str = Field(..., min_length=1, description="Candidate search phrase or keyword in Arabic")
    weight: float = Field(..., ge=0.0, le=1.0, description="Priority weight (1.0 = highest)")
    type: AnchorType = Field(default=AnchorType.SEMANTIC)


class ScriptReferenceSegment(BaseModel):
    paragraph_index: int = Field(default=0, ge=0)
    full_sentence: str = Field(default="", description="The complete narrative sentence containing the anchor")


class VisualContinuity(BaseModel):
    persist_after_draw: bool = Field(default=True, description="Whether to keep the asset rendered after inking finishes")
    min_hold_after_finish_s: float = Field(default=2.0, ge=0.0, description="Minimum duration to hold on screen before camera pans away")
    allowed_simultaneous_with: List[str] = Field(default_factory=list, description="List of concept_ids allowed to co-exist in frame")


class NarrativeConcept(BaseModel):
    concept_id: str = Field(..., description="Unique semantic identifier (e.g. cpt_guan_yu_hero)")
    visual_id: str = Field(..., description="Foreign key mapping to VisualEntity.visual_id in visual_manifest")
    narrative_role: NarrativeRole = Field(default=NarrativeRole.HERO)
    importance_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    anchor_candidates: List[AnchorCandidate] = Field(
        ..., min_length=1, description="Ordered candidate phrases for matching against Whisper words"
    )
    script_reference_segment: Optional[ScriptReferenceSegment] = None
    visual_continuity: VisualContinuity = Field(default_factory=VisualContinuity)
    notes: str = Field(default="", description="Director context or explanation")


class NarrativeFlowRule(BaseModel):
    antecedent: str = Field(..., description="concept_id that must precede or trigger first")
    consequent: str = Field(..., description="concept_id that follows")
    order_constraint: OrderConstraint = Field(default=OrderConstraint.ANTECEDENT_BEFORE_CONSEQUENT)
    overlap_policy: OverlapPolicy = Field(default=OverlapPolicy.SAFE_COMPOSITION)


class NarrativeVisualMap(BaseModel):
    """Contract 2: Semantic Bridge between Visuals and Script."""
    contract_type: str = Field(default="narrative_visual_map", frozen=True)
    version: str = Field(default="2.0")
    map_id: str
    storyboard_hash: str = Field(..., description="SHA-256 hash of the visual manifest storyboard")
    script_hash: str = Field(..., description="SHA-256 hash of the transcript text")
    concepts: List[NarrativeConcept] = Field(default_factory=list)
    narrative_flow_rules: List[NarrativeFlowRule] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_concept(self, concept_id: str) -> Optional[NarrativeConcept]:
        for c in self.concepts:
            if c.concept_id == concept_id:
                return c
        return None

    def get_concepts_for_visual(self, visual_id: str) -> List[NarrativeConcept]:
        return [c for c in self.concepts if c.visual_id == visual_id]
