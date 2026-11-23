"""AI Narrative Director & Semantic Mapper (TCM-DS Contract 2 Generator).

Bridges the purely visual manifest (visual_manifest.json) to the narrative script:
- Maps visual IDs to semantic concept IDs with narrative roles (HERO, SUPPORT, CONTEXT)
- Constructs tiered, weighted anchor candidates (identity, semantic, support) for robust speech matching
- Formulates narrative flow rules and intentional overlap policies
- Outputs narrative_visual_map.json (Contract 2)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from core.contracts.visual_manifest import VisualManifest
from core.contracts.narrative_map import (
    NarrativeVisualMap,
    NarrativeConcept,
    NarrativeRole,
    AnchorCandidate,
    AnchorType,
    OverlapPolicy,
    OrderConstraint,
    NarrativeFlowRule,
    VisualContinuity,
    ScriptReferenceSegment,
)
from core.artifacts.artifact_identity import hash_file


class NarrativeDirector:
    """Constructs Contract 2 (narrative_visual_map.json) linking visuals to narrative text."""

    @staticmethod
    def build_narrative_map_for_guan_yu(
        manifest: VisualManifest,
        script_path: Path,
        output_map_path: Optional[Path] = None,
    ) -> NarrativeVisualMap:
        """Constructs canonical narrative mapping for Guan Yu section."""
        script_hash = hash_file(script_path)
        with open(script_path, "r", encoding="utf-8") as f:
            script_text = f.read()

        # Map candidate visual IDs to narrative concepts based on storyboard layout
        # (cand_001..021 extracted organically via white valley slicing)
        concepts = [
            NarrativeConcept(
                concept_id="cpt_guan_yu_hero",
                visual_id="cand_001",
                narrative_role=NarrativeRole.HERO,
                importance_weight=1.0,
                anchor_candidates=[
                    AnchorCandidate(text="غوان يو", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="جوانيو", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="محرب صيني عملاق", weight=0.90, type=AnchorType.SEMANTIC),
                ],
                script_reference_segment=ScriptReferenceSegment(
                    paragraph_index=0, full_sentence="غوان يو. محارب صيني عملاق عاش في فترة الممالك الثلاث"
                ),
                visual_continuity=VisualContinuity(persist_after_draw=True, min_hold_after_finish_s=3.0),
            ),
            NarrativeConcept(
                concept_id="cpt_crescent_blade",
                visual_id="cand_019",
                narrative_role=NarrativeRole.SUPPORT,
                importance_weight=0.85,
                anchor_candidates=[
                    AnchorCandidate(text="سلاحه الهلالي الثقيل", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="سلاحه الهلالي", weight=0.95, type=AnchorType.SEMANTIC),
                    AnchorCandidate(text="بقوته ومهارته", weight=0.75, type=AnchorType.SUPPORT),
                ],
                script_reference_segment=ScriptReferenceSegment(
                    paragraph_index=1, full_sentence="واشتهر بقوته ومهارته باستخدام سلاحه الهلالي الثقيل."
                ),
                visual_continuity=VisualContinuity(persist_after_draw=True, min_hold_after_finish_s=2.5),
            ),
            NarrativeConcept(
                concept_id="cpt_warhorse_charge",
                visual_id="cand_020",
                narrative_role=NarrativeRole.SUPPORT,
                importance_weight=0.90,
                anchor_candidates=[
                    AnchorCandidate(text="اندفع بحصانه", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="بحصانه وسط جيش العدو", weight=0.95, type=AnchorType.SEMANTIC),
                    AnchorCandidate(text="في معركة", weight=0.70, type=AnchorType.SUPPORT),
                ],
                script_reference_segment=ScriptReferenceSegment(
                    paragraph_index=2, full_sentence="ومن أشهر قصصه إنه في معركة، اندفع بحصانه وسط جيش العدو"
                ),
                visual_continuity=VisualContinuity(persist_after_draw=True, min_hold_after_finish_s=2.5),
            ),
            NarrativeConcept(
                concept_id="cpt_single_combat",
                visual_id="cand_004",
                narrative_role=NarrativeRole.HERO,
                importance_weight=0.95,
                anchor_candidates=[
                    AnchorCandidate(text="قاعد بارز", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="قائد بارز", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="قتل امام جنوده", weight=0.90, type=AnchorType.SEMANTIC),
                    AnchorCandidate(text="امام جنوده", weight=0.85, type=AnchorType.SUPPORT),
                ],
                script_reference_segment=ScriptReferenceSegment(
                    paragraph_index=2, full_sentence="واتجه مباشرة إلى قائد بارز، وتمكن من قتله أمام جنوده."
                ),
                visual_continuity=VisualContinuity(persist_after_draw=True, min_hold_after_finish_s=2.0),
            ),
            NarrativeConcept(
                concept_id="cpt_sworn_brothers",
                visual_id="cand_005",
                narrative_role=NarrativeRole.CONTEXT,
                importance_weight=0.80,
                anchor_candidates=[
                    AnchorCandidate(text="حليفه ليوبي", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="حليفه ليو بي", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="سنوات طويلة", weight=0.70, type=AnchorType.SUPPORT),
                ],
                script_reference_segment=ScriptReferenceSegment(
                    paragraph_index=3, full_sentence="سنوات طويلة، قاتل إلى جانب حليفه ليو بي، وصار واحداً من أشهر المحاربين"
                ),
                visual_continuity=VisualContinuity(persist_after_draw=True, min_hold_after_finish_s=2.0),
            ),
            NarrativeConcept(
                concept_id="cpt_campaign_fall",
                visual_id="cand_007",
                narrative_role=NarrativeRole.CONTEXT,
                importance_weight=0.75,
                anchor_candidates=[
                    AnchorCandidate(text="ثقة الزائدة", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="ثقته الزائدة", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="سقوطة كان", weight=0.85, type=AnchorType.SUPPORT),
                ],
                script_reference_segment=ScriptReferenceSegment(
                    paragraph_index=4, full_sentence="لكن سقوطه كان بسبب ثقته الزائدة."
                ),
                visual_continuity=VisualContinuity(persist_after_draw=True, min_hold_after_finish_s=1.5),
            ),
            NarrativeConcept(
                concept_id="cpt_cut_supplies",
                visual_id="cand_010",
                narrative_role=NarrativeRole.CONTEXT,
                importance_weight=0.75,
                anchor_candidates=[
                    AnchorCandidate(text="وقطع امداداته من الخلف", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="قطع امداداته", weight=0.90, type=AnchorType.SEMANTIC),
                    AnchorCandidate(text="قواعده", weight=0.70, type=AnchorType.SUPPORT),
                ],
                script_reference_segment=ScriptReferenceSegment(
                    paragraph_index=5, full_sentence="تقدم عميقاً داخل أراضي العدو، بينما تمكن خصومه من احتلال قواعده وقطع إمداداته من الخلف."
                ),
                visual_continuity=VisualContinuity(persist_after_draw=True, min_hold_after_finish_s=1.5),
            ),
            NarrativeConcept(
                concept_id="cpt_army_collapse",
                visual_id="cand_011",
                narrative_role=NarrativeRole.SUPPORT,
                importance_weight=0.85,
                anchor_candidates=[
                    AnchorCandidate(text="جيشانهار", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="جيشه انهار", weight=1.0, type=AnchorType.IDENTITY),
                ],
                script_reference_segment=ScriptReferenceSegment(
                    paragraph_index=6, full_sentence="جيشه انهار."
                ),
                visual_continuity=VisualContinuity(persist_after_draw=True, min_hold_after_finish_s=1.5),
            ),
            NarrativeConcept(
                concept_id="cpt_captured_kneeling",
                visual_id="cand_012",
                narrative_role=NarrativeRole.HERO,
                importance_weight=0.95,
                anchor_candidates=[
                    AnchorCandidate(text="واسر هو ولده", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="واسر هو وولده", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="ولده", weight=0.75, type=AnchorType.SUPPORT),
                ],
                script_reference_segment=ScriptReferenceSegment(
                    paragraph_index=7, full_sentence="وأُسر هو وولده."
                ),
                visual_continuity=VisualContinuity(persist_after_draw=True, min_hold_after_finish_s=2.0),
            ),
            NarrativeConcept(
                concept_id="cpt_execution",
                visual_id="cand_013",
                narrative_role=NarrativeRole.HERO,
                importance_weight=1.0,
                anchor_candidates=[
                    AnchorCandidate(text="ثم اعدمه", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="ثم اعدما", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="اعدمه", weight=0.90, type=AnchorType.SEMANTIC),
                ],
                script_reference_segment=ScriptReferenceSegment(
                    paragraph_index=8, full_sentence="ثم أُعدما."
                ),
                visual_continuity=VisualContinuity(persist_after_draw=True, min_hold_after_finish_s=2.5),
            ),
            NarrativeConcept(
                concept_id="cpt_head_sent_cao_cao",
                visual_id="cand_015",
                narrative_role=NarrativeRole.HERO,
                importance_weight=0.95,
                anchor_candidates=[
                    AnchorCandidate(text="تساو تساو", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="الراس ارسل لاحقا", weight=0.95, type=AnchorType.SEMANTIC),
                    AnchorCandidate(text="الراس ارسل", weight=0.90, type=AnchorType.SEMANTIC),
                ],
                script_reference_segment=ScriptReferenceSegment(
                    paragraph_index=9, full_sentence="والأغرب إن الرأس أُرسل لاحقاً إلى تساو تساو، لأن خصومه كانوا يخشون من تبعات قتل رجل بهذه الشهرة."
                ),
                visual_continuity=VisualContinuity(persist_after_draw=True, min_hold_after_finish_s=3.0),
            ),
            NarrativeConcept(
                concept_id="cpt_temple_deification",
                visual_id="cand_017",
                narrative_role=NarrativeRole.HERO,
                importance_weight=1.0,
                anchor_candidates=[
                    AnchorCandidate(text="للقوة والوفاء", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="رمز للقوة والوفاء", weight=1.0, type=AnchorType.IDENTITY),
                    AnchorCandidate(text="كاله للحرب", weight=0.95, type=AnchorType.SEMANTIC),
                ],
                script_reference_segment=ScriptReferenceSegment(
                    paragraph_index=10, full_sentence="ومع مرور القرون، تحول غوان يو في الثقافة الصينية إلى رمز للقوة والوفاء، وصار يُبجل في بعض التقاليد كإله للحرب."
                ),
                visual_continuity=VisualContinuity(persist_after_draw=True, min_hold_after_finish_s=4.0),
            ),
        ]

        flow_rules = [
            NarrativeFlowRule(
                antecedent="cpt_crescent_blade",
                consequent="cpt_guan_yu_hero",
                order_constraint=OrderConstraint.ANTECEDENT_BEFORE_CONSEQUENT,
                overlap_policy=OverlapPolicy.SAFE_COMPOSITION,
            ),
            NarrativeFlowRule(
                antecedent="cpt_captured_kneeling",
                consequent="cpt_execution",
                order_constraint=OrderConstraint.ANTECEDENT_BEFORE_CONSEQUENT,
                overlap_policy=OverlapPolicy.SAFE_COMPOSITION,
            ),
        ]

        n_map = NarrativeVisualMap(
            map_id="map_07_guan_yu",
            storyboard_hash=manifest.storyboard_hash,
            script_hash=script_hash,
            concepts=concepts,
            narrative_flow_rules=flow_rules,
        )

        if output_map_path:
            output_map_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_map_path, "w", encoding="utf-8") as f:
                json.dump(n_map.model_dump(), f, indent=2, ensure_ascii=False)

        return n_map
