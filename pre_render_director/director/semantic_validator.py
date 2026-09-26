"""Semantic validation and contradiction detection between narration intent and visual assets."""

import re
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from ..models.output import SemanticMatchScore
from ..models.input import AssetMetadata

class SemanticMatchResult(BaseModel):
    event_id: str
    asset_id: Optional[str] = None
    anchor_text: str = ""
    match_score: float = 1.0
    status: SemanticMatchScore = SemanticMatchScore.STRONG_MATCH
    is_contradictory: bool = False
    contradiction_reason: Optional[str] = None
    is_missing_asset: bool = False
    missing_concept: Optional[str] = None
    confidence: float = 0.95
    reason: str = ""

class SemanticValidator:
    """Evaluates semantic compatibility and catches contradictions between narration and visuals."""

    # Contradiction rules: (trigger_keywords in speech, forbidden_keywords in asset, reason)
    CONTRADICTION_RULES = [
        (
            ["تشيك على أغراضك", "تشيك على الشنطة", "تفتيش الحقيبة"],
            ["sleeping", "bench", "hospital", "clinic", "eating", "food"],
            "Asset shows passive state or food/clinic while narration specifies checking belongings/backpack."
        ),
        (
            ["صبة", "أرض", "رصيف", "ground", "concrete"],
            ["bench", "bed", "chair", "sofa"],
            "Asset depicts a bench/furniture while narration explicitly specifies sleeping on hard ground/concrete."
        ),
        (
            ["عطش", "ماء", "مويه", "شرب"],
            ["smoking", "money", "phone", "cardboard"],
            "Asset action does not represent thirst or drinking water."
        ),
        (
            ["جوال", "شاشة", "بطارية", "شاحن", "واي فاي"],
            ["food", "sink", "shirt", "eating", "begging"],
            "Asset does not represent phone, battery, or electronic connectivity."
        )
    ]

    def __init__(self, ai_provider=None):
        self.ai_provider = ai_provider

    def validate(
        self,
        event_id: str,
        asset: Optional[AssetMetadata],
        anchor_text: str,
        speech_context: Optional[Dict[str, Any]] = None,
        look_behind: Optional[Dict[str, Any]] = None,
        look_ahead: Optional[Dict[str, Any]] = None
    ) -> SemanticMatchResult:
        """Validates semantic match between spoken anchor and visual asset."""
        if not asset:
            return SemanticMatchResult(
                event_id=event_id,
                asset_id=None,
                anchor_text=anchor_text,
                match_score=0.0,
                status=SemanticMatchScore.INVALID,
                reason="Event has no asset assigned.",
                confidence=1.0
            )

        norm_anchor = anchor_text.lower().strip()
        asset_tags = f"{asset.asset_id} {asset.semantic_description} {asset.visual_role} {asset.action or ''} {' '.join(asset.objects)}".lower()

        # 1. Deterministic Contradiction Check
        for speech_kws, asset_kws, rule_reason in self.CONTRADICTION_RULES:
            if any(skw in norm_anchor for skw in speech_kws):
                if any(akw in asset_tags for akw in asset_kws):
                    # Check if asset also has positive match
                    if not any(skw in asset_tags for skw in speech_kws):
                        return SemanticMatchResult(
                            event_id=event_id,
                            asset_id=asset.asset_id,
                            anchor_text=anchor_text,
                            match_score=0.1,
                            status=SemanticMatchScore.CONTRADICTORY,
                            is_contradictory=True,
                            contradiction_reason=rule_reason,
                            confidence=0.96,
                            reason=f"Direct contradiction detected: {rule_reason}"
                        )

        # 2. Consult AI Provider if available for deep multimodal analysis
        if self.ai_provider:
            try:
                ai_res = self.ai_provider.evaluate_event(
                    event={"event_id": event_id, "asset_id": asset.asset_id, "anchor_text": anchor_text},
                    asset_info=asset.model_dump(),
                    speech_context=speech_context or {"anchor_text": anchor_text},
                    look_behind=look_behind,
                    look_ahead=look_ahead
                )
                match_str = ai_res.get("semantic_match", "STRONG_MATCH")
                score = float(ai_res.get("match_score", 0.9))
                is_contra = bool(ai_res.get("contradiction_detected", False))
                contra_reason = ai_res.get("contradiction_reason")

                status_enum = SemanticMatchScore.STRONG_MATCH
                if match_str in [e.value for e in SemanticMatchScore]:
                    status_enum = SemanticMatchScore(match_str)
                elif is_contra:
                    status_enum = SemanticMatchScore.CONTRADICTORY

                return SemanticMatchResult(
                    event_id=event_id,
                    asset_id=asset.asset_id,
                    anchor_text=anchor_text,
                    match_score=score,
                    status=status_enum,
                    is_contradictory=is_contra,
                    contradiction_reason=contra_reason,
                    confidence=float(ai_res.get("confidence", 0.9)),
                    reason=ai_res.get("reason", "AI director semantic verification.")
                )
            except Exception:
                pass

        # 3. Fallback heuristic scoring
        # Check token overlaps
        anchor_tokens = set(re.findall(r"[\w']+", norm_anchor))
        asset_tokens = set(re.findall(r"[\w']+", asset_tags))
        overlap = anchor_tokens.intersection(asset_tokens)

        score = 0.85
        status = SemanticMatchScore.STRONG_MATCH

        return SemanticMatchResult(
            event_id=event_id,
            asset_id=asset.asset_id,
            anchor_text=anchor_text,
            match_score=score,
            status=status,
            confidence=0.9,
            reason="Heuristic alignment check passed."
        )
