"""Unit and Contract Tests for SemanticBeatBinder (Task 2).

Validates:
1. Valid manifest ingestion (object, dict, file path)
2. Arabic normalization (diacritics, alefs, taa marbuta)
3. Exact anchor matching
4. Normalized anchor matching
5. Token / fuzzy matching
6. Repeated phrase handling (distinct chronological anchors)
7. Duplicated Whisper ending handling (filters spurious duplicate tail)
8. Missing word timestamps fallback handling
9. Monotonic timestamp progression
10. Strict rule: NO invented asset IDs
11. Deterministic output reproducibility
12. NarrativeVisualMap Pydantic contract validation
"""

import copy
import json
from pathlib import Path
import pytest

from core.contracts.visual_manifest import (
    VisualManifest,
    VisualEntity,
    VisualType,
    ExtractionStatus,
    NormalizedDemandMetrics,
)
from core.contracts.narrative_map import NarrativeVisualMap, NarrativeRole
from core.narrative.semantic_beat_binder import SemanticBeatBinder, bind_semantic_beats, InvalidManifestInputError
from core.sync.arabic_matcher import ArabicMatcher
from core.sync.anchor_resolver import DeterministicAnchorResolver

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def sample_manifest() -> VisualManifest:
    """Creates a sample VisualManifest with 4 distinct assets."""
    entities = [
        VisualEntity(
            visual_id="asset_001",
            sheet_order=1,
            centroid=(100, 100),
            extraction_status=ExtractionStatus.VALID_REQUIRED_ASSET,
            visual_type=VisualType.ATOMIC_OBJECT,
            bbox=(50, 50, 100, 100),
            mask_crop_path="assets/asset_001.png",
            demand_metrics=NormalizedDemandMetrics(
                normalized_pixel_mass=0.5,
                normalized_contour_length=0.4,
                normalized_edge_complexity=0.3,
                stroke_count_estimate=5,
                aspect_ratio=1.0,
                raw_demand_score=0.4,
            ),
            visual_tags=["status:green", "thinking", "brain"],
            description="Thinking brain asset",
        ),
        VisualEntity(
            visual_id="asset_002",
            sheet_order=2,
            centroid=(300, 100),
            extraction_status=ExtractionStatus.VALID_REQUIRED_ASSET,
            visual_type=VisualType.ATOMIC_OBJECT,
            bbox=(250, 50, 100, 100),
            mask_crop_path="assets/asset_002.png",
            demand_metrics=NormalizedDemandMetrics(
                normalized_pixel_mass=0.6,
                normalized_contour_length=0.5,
                normalized_edge_complexity=0.4,
                stroke_count_estimate=6,
                aspect_ratio=1.0,
                raw_demand_score=0.5,
            ),
            visual_tags=["status:green", "pareidolia_vision", "faces"],
            description="Faces in clouds asset",
        ),
        VisualEntity(
            visual_id="asset_003",
            sheet_order=3,
            centroid=(500, 100),
            extraction_status=ExtractionStatus.VALID_REQUIRED_ASSET,
            visual_type=VisualType.ATOMIC_OBJECT,
            bbox=(450, 50, 100, 100),
            mask_crop_path="assets/asset_003.png",
            demand_metrics=NormalizedDemandMetrics(
                normalized_pixel_mass=0.5,
                normalized_contour_length=0.4,
                normalized_edge_complexity=0.3,
                stroke_count_estimate=4,
                aspect_ratio=0.8,
                raw_demand_score=0.4,
            ),
            visual_tags=["status:green", "phantom_vibration", "phone"],
            description="Phone vibrating asset",
        ),
        VisualEntity(
            visual_id="asset_004",
            sheet_order=4,
            centroid=(700, 100),
            extraction_status=ExtractionStatus.VALID_REQUIRED_ASSET,
            visual_type=VisualType.COMPOSITE_SCENE,
            bbox=(650, 50, 120, 120),
            mask_crop_path="assets/asset_004.png",
            demand_metrics=NormalizedDemandMetrics(
                normalized_pixel_mass=0.7,
                normalized_contour_length=0.6,
                normalized_edge_complexity=0.5,
                stroke_count_estimate=12,
                aspect_ratio=1.0,
                raw_demand_score=0.6,
            ),
            visual_tags=["status:green", "inattentional_blindness", "gorilla"],
            description="Gorilla basketball asset",
        ),
    ]

    return VisualManifest(
        contract_type="visual_manifest",
        version="2.0",
        storyboard_id="test_storyboard",
        storyboard_hash="a" * 64,
        canvas_dimensions={"width": 1920, "height": 1080},
        entities=entities,
    )


@pytest.fixture
def sample_whisper() -> dict:
    """Sample Whisper data with word-level timestamps."""
    return {
        "duration": 15.0,
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 2.5,
                "text": "مخك عضو جبار",
                "words": [
                    {"word": "مخك", "start": 0.0, "end": 0.8, "probability": 0.95},
                    {"word": "عضو", "start": 0.8, "end": 1.5, "probability": 0.96},
                    {"word": "جبار", "start": 1.5, "end": 2.5, "probability": 0.98},
                ],
            },
            {
                "id": 1,
                "start": 2.5,
                "end": 6.0,
                "text": "يشوف لك وجوه في الفيش",
                "words": [
                    {"word": "يشوف", "start": 2.5, "end": 3.2, "probability": 0.92},
                    {"word": "لك", "start": 3.2, "end": 3.8, "probability": 0.88},
                    {"word": "وجوه", "start": 3.8, "end": 4.6, "probability": 0.97},
                    {"word": "في", "start": 4.6, "end": 5.0, "probability": 0.91},
                    {"word": "الفيش", "start": 5.0, "end": 6.0, "probability": 0.99},
                ],
            },
            {
                "id": 2,
                "start": 6.0,
                "end": 9.5,
                "text": "يخليك تحس بجوال يهتز",
                "words": [
                    {"word": "يخليك", "start": 6.0, "end": 6.8, "probability": 0.95},
                    {"word": "تحس", "start": 6.8, "end": 7.5, "probability": 0.96},
                    {"word": "بجوال", "start": 7.5, "end": 8.4, "probability": 0.94},
                    {"word": "يهتز", "start": 8.4, "end": 9.5, "probability": 0.99},
                ],
            },
            {
                "id": 3,
                "start": 9.5,
                "end": 13.0,
                "text": "يحذف قوريلا من قدام عينك",
                "words": [
                    {"word": "يحذف", "start": 9.5, "end": 10.2, "probability": 0.95},
                    {"word": "قوريلا", "start": 10.2, "end": 11.2, "probability": 0.85},
                    {"word": "من", "start": 11.2, "end": 11.6, "probability": 0.96},
                    {"word": "قدام", "start": 11.6, "end": 12.2, "probability": 0.92},
                    {"word": "عينك", "start": 12.2, "end": 13.0, "probability": 0.98},
                ],
            },
        ],
    }


# ============================================================================
# 1. VALID MANIFEST INGESTION
# ============================================================================

def test_valid_manifest_ingestion(sample_manifest, sample_whisper, tmp_path: Path):
    """Test binding directly with a VisualManifest object, dict, and json path."""
    binder = SemanticBeatBinder()
    script = "مخك عضو جبار.\nيشوف لك وجوه في الفيش.\nيخليك تحس بجوال يهتز.\nيحذف غوريلا من قدام عينك."

    # Ingestion via object
    map1 = binder.bind(sample_manifest, script, sample_whisper)
    assert isinstance(map1, NarrativeVisualMap)
    assert len(map1.concepts) == 4

    # Ingestion via dict
    manifest_dict = sample_manifest.model_dump()
    map2 = binder.bind(manifest_dict, script, sample_whisper)
    assert len(map2.concepts) == 4

    # Ingestion via file path
    manifest_file = tmp_path / "vm.json"
    manifest_file.write_text(json.dumps(manifest_dict), encoding="utf-8")
    map3 = binder.bind(manifest_file, script, sample_whisper)
    assert len(map3.concepts) == 4


# ============================================================================
# 2. ARABIC NORMALIZATION
# ============================================================================

def test_arabic_normalization():
    """Verify invariant normalization across tashkeel, alefs, and punctuation."""
    matcher = ArabicMatcher()
    t1 = "مُخُّكَ عُضْوٌ جَبَّارٌ!"
    t2 = "مخك عضو جبار"
    assert matcher.normalize(t1) == matcher.normalize(t2)

    # Alef variants
    assert matcher.normalize("أحمد") == matcher.normalize("احمد")
    assert matcher.normalize("إدراك") == matcher.normalize("ادراك")
    assert matcher.normalize("آثار") == matcher.normalize("اثار")

    # Taa marbuta and Haa
    assert matcher.normalize("غريبة") == matcher.normalize("غريبه")


# ============================================================================
# 3. EXACT ANCHOR MATCHING
# ============================================================================

def test_exact_anchor_matching(sample_whisper):
    """Verify that exact words match with 1.0 confidence."""
    words = [w for s in sample_whisper["segments"] for w in s["words"]]
    matcher = ArabicMatcher()

    span = matcher.find_best_span("مخك", words, 0)
    assert span is not None
    st, en, conf = span
    assert st == 0 and en == 0 and conf == 1.0

    span_phrase = matcher.find_best_span("عضو جبار", words, 0)
    assert span_phrase is not None
    st, en, conf = span_phrase
    assert st == 1 and en == 2 and conf == 1.0


# ============================================================================
# 4. NORMALIZED ANCHOR MATCHING
# ============================================================================

def test_normalized_anchor_matching(sample_whisper):
    """Verify matching across diacritics and alef forms."""
    words = [w for s in sample_whisper["segments"] for w in s["words"]]
    matcher = ArabicMatcher()

    # With diacritics
    span = matcher.find_best_span("عُضْوٌ", words, 0)
    assert span is not None
    assert span[0] == 1 and span[2] >= 0.98


# ============================================================================
# 5. TOKEN MATCHING (PHONETIC & DIALECTAL VARIANCE)
# ============================================================================

def test_token_fuzzy_matching(sample_whisper):
    """Verify that 'غوريلا' in script matches 'قوريلا' in Whisper via token/phonetic similarity."""
    words = [w for s in sample_whisper["segments"] for w in s["words"]]
    matcher = ArabicMatcher()

    span = matcher.find_best_span("غوريلا", words, 5)
    assert span is not None
    st, en, conf = span
    assert words[st]["word"] == "قوريلا"
    assert conf >= 0.70  # Valid token tier match


# ============================================================================
# 6. REPEATED PHRASE HANDLING
# ============================================================================

def test_repeated_phrase_chronological_advancement():
    """Verify that repeated words/phrases resolve to distinct forward timestamps."""
    whisper_data = {
        "duration": 10.0,
        "segments": [
            {
                "id": 0, "start": 0.0, "end": 3.0, "text": "مخك يفكر",
                "words": [
                    {"word": "مخك", "start": 0.0, "end": 1.2},
                    {"word": "يفكر", "start": 1.2, "end": 2.8},
                ],
            },
            {
                "id": 1, "start": 4.0, "end": 8.0, "text": "ومخك يقرر",
                "words": [
                    {"word": "ومخك", "start": 4.0, "end": 5.2},
                    {"word": "يقرر", "start": 5.2, "end": 7.5},
                ],
            },
        ],
    }
    words = [w for s in whisper_data["segments"] for w in s["words"]]
    matcher = ArabicMatcher()

    span1 = matcher.find_best_span("مخك", words, search_start_idx=0)
    assert span1 is not None and span1[0] == 0

    # Next search starts beyond span1
    span2 = matcher.find_best_span("مخك", words, search_start_idx=span1[1] + 1)
    assert span2 is not None and span2[0] == 2  # Matches second 'ومخك' at word index 2


# ============================================================================
# 7. DUPLICATED WHISPER ENDING HANDLING
# ============================================================================

def test_duplicated_whisper_ending_filtering(sample_manifest):
    """Verify spurious hallucinated duplicate whisper segment is filtered if script only has it once."""
    script = "في أمان الله."
    duplicated_whisper = {
        "duration": 6.0,
        "segments": [
            {
                "id": 0, "start": 0.0, "end": 2.5, "text": "في أمان الله",
                "words": [
                    {"word": "في", "start": 0.0, "end": 0.5},
                    {"word": "أمان", "start": 0.5, "end": 1.5},
                    {"word": "الله", "start": 1.5, "end": 2.5},
                ],
            },
            {
                "id": 1, "start": 2.8, "end": 5.5, "text": "في أمان الله",  # Spurious duplicated ending
                "words": [
                    {"word": "في", "start": 2.8, "end": 3.2},
                    {"word": "أمان", "start": 3.2, "end": 4.2},
                    {"word": "الله", "start": 4.2, "end": 5.2},
                ],
            },
        ],
    }

    binder = SemanticBeatBinder()
    n_map = binder.bind(sample_manifest, script, duplicated_whisper)

    # Canonical script has only one sentence, so exactly one speech beat must be created
    assert len(n_map.concepts) == 1
    assert n_map.metadata["total_speech_beats"] == 1


# ============================================================================
# 8. MISSING WORD TIMESTAMPS FALLBACK
# ============================================================================

def test_missing_word_timestamps_graceful_fallback(sample_manifest):
    """Verify graceful handling when Whisper segments lack word-level lists."""
    script = "مخك عضو جبار.\nيشوف لك وجوه."
    whisper_no_words = {
        "duration": 6.0,
        "segments": [
            {"id": 0, "start": 0.0, "end": 2.8, "text": "مخك عضو جبار"},
            {"id": 1, "start": 3.0, "end": 5.8, "text": "يشوف لك وجوه"},
        ],
    }

    binder = SemanticBeatBinder()
    n_map = binder.bind(sample_manifest, script, whisper_no_words)

    assert len(n_map.concepts) == 2
    beats = n_map.metadata["speech_beats"]
    assert beats[0]["start"] == 0.0
    assert beats[1]["start"] == 3.0


# ============================================================================
# 9. MONOTONIC TIMESTAMPS
# ============================================================================

def test_monotonic_timestamps(sample_manifest, sample_whisper):
    """Verify that speech beats and resolved anchors advance monotonically forward in time."""
    script = "مخك عضو جبار.\nيشوف لك وجوه في الفيش.\nيخليك تحس بجوال يهتز.\nيحذف غوريلا من قدام عينك."
    binder = SemanticBeatBinder()
    n_map = binder.bind(sample_manifest, script, sample_whisper)

    beats = n_map.metadata["speech_beats"]
    for i in range(len(beats) - 1):
        assert beats[i]["start"] <= beats[i + 1]["start"], (
            f"Non-monotonic beats: {beats[i]['start']} > {beats[i+1]['start']}"
        )

    # Test anchor resolver monotonic guarantee
    words = [w for s in sample_whisper["segments"] for w in s["words"]]
    resolver = DeterministicAnchorResolver(words, sample_whisper["duration"])
    resolved_pairs = resolver.resolve_map(n_map)

    last_t = 0.0
    for _, anchor in resolved_pairs:
        if anchor:
            assert anchor.whisper_t_start >= last_t
            last_t = anchor.whisper_t_start


# ============================================================================
# 10. NO ASSET IDS INVENTED (STRICT BOUNDING)
# ============================================================================

def test_no_asset_ids_invented(sample_manifest, sample_whisper):
    """Verify that every concept.visual_id strictly belongs to VisualManifest.entities."""
    script = "مخك عضو جبار.\nيشوف لك وجوه في الفيش.\nيخليك تحس بجوال يهتز.\nيحذف غوريلا من قدام عينك."
    binder = SemanticBeatBinder()
    n_map = binder.bind(sample_manifest, script, sample_whisper)

    valid_visual_ids = {e.visual_id for e in sample_manifest.entities}
    for concept in n_map.concepts:
        assert concept.visual_id in valid_visual_ids, (
            f"Invented visual ID '{concept.visual_id}' not found in manifest!"
        )


# ============================================================================
# 11. DETERMINISTIC OUTPUT REPRODUCIBILITY
# ============================================================================

def test_deterministic_output_reproducibility(sample_manifest, sample_whisper):
    """Verify that running the binder twice produces identical JSON output."""
    script = "مخك عضو جبار.\nيشوف لك وجوه في الفيش."
    binder = SemanticBeatBinder()

    map1 = binder.bind(sample_manifest, script, sample_whisper)
    map2 = binder.bind(sample_manifest, script, sample_whisper)

    assert map1.model_dump_json(indent=2) == map2.model_dump_json(indent=2)


# ============================================================================
# 12. CONTRACT VALIDATION
# ============================================================================

def test_pydantic_contract_validation(sample_manifest, sample_whisper):
    """Verify that the generated map validates against NarrativeVisualMap schema."""
    script = "مخك عضو جبار.\nيشوف لك وجوه في الفيش."
    binder = SemanticBeatBinder()
    n_map = binder.bind(sample_manifest, script, sample_whisper)

    raw_dict = n_map.model_dump()
    reloaded = NarrativeVisualMap.model_validate(raw_dict)

    assert reloaded.contract_type == "narrative_visual_map"
    assert reloaded.version == "2.0"
    assert len(reloaded.concepts) == len(n_map.concepts)
    assert len(reloaded.narrative_flow_rules) == len(n_map.narrative_flow_rules)
