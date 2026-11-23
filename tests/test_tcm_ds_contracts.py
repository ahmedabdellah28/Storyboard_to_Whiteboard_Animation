"""Comprehensive Unit & Regression Test Suite for Tri-Contract Manifest & Deterministic Scheduler (TCM-DS v2.0).

Verifies:
1. Pure Visual Manifest (Contract 1) contains no script/timing data.
2. Narrative Visual Map (Contract 2) acts as semantic bridge with weighted anchors.
3. Cryptographic Cache Invalidation (Zero Stale Artifacts).
4. Normalized CV Demand Estimator mathematically scales without magic constants.
5. Deterministic Anchor Resolver enforces monotonic progression with ZERO silent guessing.
6. Hero anchor failure strictly halts the pipeline (No fallback guessing).
7. Constraint Visual Scheduler generates valid FinalRenderPlan (Contract 3) respecting policy limits.
"""

from __future__ import annotations

import pytest
import numpy as np

from core.contracts import (
    VisualManifest,
    VisualEntity,
    VisualType,
    SpatialRelation,
    NormalizedDemandMetrics,
    NarrativeVisualMap,
    NarrativeConcept,
    NarrativeRole,
    AnchorCandidate,
    AnchorType,
    OverlapPolicy,
    NarrativeFlowRule,
    FinalRenderPlan,
    RenderPolicy,
)
from core.artifacts.cache_validator import CacheValidator
from core.vision.demand_estimator import DemandEstimator
from core.sync.anchor_resolver import DeterministicAnchorResolver, UnresolvedHeroAnchorError
from core.scheduling.constraint_scheduler import ConstraintVisualScheduler


def test_contract_1_visual_manifest_isolation():
    """Verify Contract 1 is pure visual truth with no narrative or timing leakage."""
    metrics = NormalizedDemandMetrics(
        normalized_pixel_mass=0.75,
        normalized_contour_length=0.60,
        normalized_edge_complexity=0.80,
        stroke_count_estimate=120,
        aspect_ratio=0.85,
        raw_demand_score=0.72,
    )
    entity = VisualEntity(
        visual_id="vis_hero_01",
        visual_type=VisualType.COMPOSITE_SCENE,
        bbox=(100, 100, 800, 1200),
        mask_crop_path="assets/crops/hero.png",
        demand_metrics=metrics,
        visual_tags=["warrior", "armor", "sword"],
    )
    manifest = VisualManifest(
        storyboard_id="test_storyboard",
        storyboard_hash="sha256_mock_sb_hash",
        entities=[entity],
    )

    d = manifest.model_dump()
    assert d["contract_type"] == "visual_manifest"
    assert "entities" in d
    # Strict isolation checks: NO script or audio timestamps allowed in Contract 1
    assert "transcript" not in d
    assert "anchor_phrase" not in d["entities"][0]
    assert "start_time" not in d["entities"][0]


def test_contract_2_narrative_visual_map():
    """Verify Contract 2 maps visual IDs to weighted semantic anchor candidates."""
    concept = NarrativeConcept(
        concept_id="cpt_warrior",
        visual_id="vis_hero_01",
        narrative_role=NarrativeRole.HERO,
        importance_weight=1.0,
        anchor_candidates=[
            AnchorCandidate(text="غوان يو", weight=1.0, type=AnchorType.IDENTITY),
            AnchorCandidate(text="أسطورته", weight=0.85, type=AnchorType.SEMANTIC),
        ],
    )
    flow_rule = NarrativeFlowRule(
        antecedent="cpt_warrior",
        consequent="cpt_weapon",
        overlap_policy=OverlapPolicy.INTENTIONAL_OVERLAP,
    )
    n_map = NarrativeVisualMap(
        map_id="map_01",
        storyboard_hash="sha256_mock_sb_hash",
        script_hash="sha256_mock_script_hash",
        concepts=[concept],
        narrative_flow_rules=[flow_rule],
    )

    assert len(n_map.concepts) == 1
    assert n_map.concepts[0].anchor_candidates[0].text == "غوان يو"
    assert n_map.narrative_flow_rules[0].overlap_policy == OverlapPolicy.INTENTIONAL_OVERLAP


def test_cache_invalidation_rules(tmp_path):
    """Verify multi-tier cache invalidation behavior."""
    sb_file = tmp_path / "storyboard.png"
    sb_file.write_bytes(b"image_v1_data")
    sc_file = tmp_path / "transcript.txt"
    sc_file.write_text("نص القصة الأصلي", encoding="utf-8")

    sb_hash = CacheValidator.compute_storyboard_hash(sb_file)
    sc_hash = CacheValidator.compute_script_hash(sc_file)

    manifest_json = tmp_path / "visual_manifest.json"
    manifest_json.write_text(f'{{"storyboard_hash": "{sb_hash}"}}', encoding="utf-8")

    # 1. Freshness checks pass
    assert CacheValidator.is_manifest_fresh(manifest_json, sb_hash) is True

    # 2. Modifying storyboard invalidates manifest
    sb_file.write_bytes(b"image_v2_data_modified")
    new_sb_hash = CacheValidator.compute_storyboard_hash(sb_file)
    assert CacheValidator.is_manifest_fresh(manifest_json, new_sb_hash) is False


def test_demand_estimator_math():
    """Verify CV demand estimation produces bounded scores and maps to policy durations."""
    policy = RenderPolicy()
    estimator = DemandEstimator(policy)

    # Synthetic image: 200x200 canvas with drawn square in middle
    img = np.full((200, 200, 3), 255, dtype=np.uint8)
    img[50:150, 50:150] = 0  # Black box

    metrics = estimator.compute_metrics(img, canvas_dimensions=(1920, 1080))
    assert 0.0 <= metrics.raw_demand_score <= 1.0
    assert 0.0 <= metrics.normalized_pixel_mass <= 1.0

    t_min, t_est, t_max = estimator.calculate_duration(metrics, policy.speed_limits.hero)
    assert t_min <= t_est <= t_max
    assert t_min >= 0.6


def test_deterministic_anchor_resolver_and_zero_guessing():
    """Verify anchor resolver matches words monotonically and raises on Hero failure."""
    whisper_words = [
        {"word": "كان", "start": 1.0, "end": 1.4},
        {"word": "غوان", "start": 1.5, "end": 1.9},
        {"word": "يو", "start": 2.0, "end": 2.5},
        {"word": "فارسا", "start": 2.6, "end": 3.0},
        {"word": "شجاعا", "start": 3.1, "end": 3.8},
    ]

    hero_concept = NarrativeConcept(
        concept_id="cpt_hero",
        visual_id="vis_hero",
        narrative_role=NarrativeRole.HERO,
        anchor_candidates=[
            AnchorCandidate(text="غوان يو", weight=1.0, type=AnchorType.IDENTITY),
        ],
    )
    support_concept = NarrativeConcept(
        concept_id="cpt_support",
        visual_id="vis_support",
        narrative_role=NarrativeRole.SUPPORT,
        anchor_candidates=[
            AnchorCandidate(text="شجاعا", weight=1.0, type=AnchorType.SEMANTIC),
        ],
    )

    n_map = NarrativeVisualMap(
        map_id="map_test",
        storyboard_hash="sb_hash",
        script_hash="sc_hash",
        concepts=[hero_concept, support_concept],
    )

    resolver = DeterministicAnchorResolver(whisper_words, audio_duration=10.0)
    resolved = resolver.resolve_map(n_map)

    assert len(resolved) == 2
    hero_res = resolved[0][1]
    assert hero_res is not None
    assert hero_res.whisper_t_start == 1.5
    assert hero_res.confidence >= 0.90

    # Test ZERO SILENT GUESSING on Hero failure:
    missing_hero = NarrativeConcept(
        concept_id="cpt_missing_hero",
        visual_id="vis_ghost",
        narrative_role=NarrativeRole.HERO,
        anchor_candidates=[
            AnchorCandidate(text="كلمة مستحيلة غير موجودة إطلاقا", weight=1.0),
        ],
    )
    bad_map = NarrativeVisualMap(
        map_id="map_fail",
        storyboard_hash="sb_hash",
        script_hash="sc_hash",
        concepts=[missing_hero],
    )

    # Must raise UnresolvedHeroAnchorError rather than guessing timestamps!
    with pytest.raises(UnresolvedHeroAnchorError):
        resolver.resolve_map(bad_map)


def test_constraint_scheduler_execution_plan():
    """Verify ConstraintVisualScheduler builds complete FinalRenderPlan."""
    metrics = NormalizedDemandMetrics(
        normalized_pixel_mass=0.5,
        normalized_contour_length=0.5,
        normalized_edge_complexity=0.5,
        stroke_count_estimate=50,
        aspect_ratio=1.0,
        raw_demand_score=0.5,
    )
    entity = VisualEntity(
        visual_id="vis_01",
        visual_type=VisualType.ATOMIC_OBJECT,
        bbox=(200, 200, 400, 400),
        mask_crop_path="crops/crop_01.png",
        demand_metrics=metrics,
    )
    manifest = VisualManifest(
        storyboard_id="sb_01",
        storyboard_hash="sb_hash",
        entities=[entity],
    )

    concept = NarrativeConcept(
        concept_id="cpt_01",
        visual_id="vis_01",
        narrative_role=NarrativeRole.HERO,
        anchor_candidates=[AnchorCandidate(text="بطل", weight=1.0)],
    )
    n_map = NarrativeVisualMap(
        map_id="m_01",
        storyboard_hash="sb_hash",
        script_hash="sc_hash",
        concepts=[concept],
    )

    whisper_words = [{"word": "بطل", "start": 3.0, "end": 3.5}]
    resolver = DeterministicAnchorResolver(whisper_words, audio_duration=15.0)
    resolved_pairs = resolver.resolve_map(n_map)

    scheduler = ConstraintVisualScheduler(audio_duration=15.0)
    plan = scheduler.schedule(
        section_id="sec_test",
        manifest=manifest,
        narrative_map=n_map,
        resolved_pairs=resolved_pairs,
        hashes={
            "audio_hash": "a_hash",
            "narrative_map_hash": "m_hash",
            "manifest_hash": "sb_hash",
            "policy_hash": "p_hash",
        },
    )

    assert isinstance(plan, FinalRenderPlan)
    assert len(plan.execution_tracks.visual_beats) == 1
    beat = plan.execution_tracks.visual_beats[0]
    assert beat.timing.ink_start_s <= 3.0  # Lead-in applied
    assert beat.timing.ink_end_s > beat.timing.ink_start_s
    assert len(plan.execution_tracks.camera_path) >= 2  # Establishing + Beat focus
    assert len(plan.execution_tracks.sfx_cues) == 1
