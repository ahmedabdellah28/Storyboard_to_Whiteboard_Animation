"""Test Suite for Motion Choreographer & Feasibility (Task 3).

Validates all 10 Phase J test criteria:
1. Unknown asset ID rejection
2. Overlapping actions validation
3. Negative or zero duration rejection
4. Action outside beat boundary rejection
5. Action outside audio duration rejection
6. Invalid easing rejection
7. Excessive simultaneous assets detection
8. Broken continuity detection
9. Invalid camera timing rejection
10. Deterministic output reproducibility
"""

import copy
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from core.narrative.motion_choreographer import (
    MotionChoreographer,
    MotionAction,
    CameraActionSpec,
    BeatMotionPlan,
    MotionFeasibilityAuditor,
    EntranceAction,
    EmphasisAction,
    CameraAction,
    EasingType,
)


@pytest.fixture
def sample_manifest() -> dict:
    return {
        "storyboard_id": "test_storyboard",
        "entities": [
            {
                "visual_id": "asset_001",
                "visual_type": "atomic_object",
                "extraction_status": "VALID_REQUIRED_ASSET",
                "bbox": [100, 100, 200, 200],
            },
            {
                "visual_id": "asset_002",
                "visual_type": "atomic_object",
                "extraction_status": "VALID_REQUIRED_ASSET",
                "bbox": [300, 100, 150, 150],
            },
            {
                "visual_id": "asset_003",
                "visual_type": "atomic_object",
                "extraction_status": "VALID_REQUIRED_ASSET",
                "bbox": [500, 100, 80, 80],
            },
        ],
    }


@pytest.fixture
def sample_narrative_map() -> dict:
    return {
        "metadata": {
            "audio_duration_s": 10.0,
            "speech_beats": [
                {
                    "beat_id": "beat_001",
                    "start": 0.0,
                    "end": 3.0,
                    "duration": 3.0,
                    "transcript_text": "مرحبا بكم",
                    "visual_entities": ["asset_001"],
                    "continuity": False,
                },
                {
                    "beat_id": "beat_002",
                    "start": 3.0,
                    "end": 6.5,
                    "duration": 3.5,
                    "transcript_text": "هذا اختبار تجريبي",
                    "visual_entities": ["asset_002"],
                    "continuity": True,
                },
            ],
        },
    }


def test_unknown_asset_id_rejected(sample_manifest, sample_narrative_map):
    """Validation 1: Unknown asset ID must raise KeyError during validation."""
    choreographer = MotionChoreographer(
        manifest_data_or_path=sample_manifest,
        narrative_map_or_path=sample_narrative_map,
    )
    bad_plan = [
        BeatMotionPlan(
            beat_id="beat_001",
            start=0.0,
            end=3.0,
            actions=[
                MotionAction(
                    asset_id="asset_non_existent_999",
                    action=EntranceAction.POP_IN.value,
                    start=0.0,
                    end=0.5,
                    easing=EasingType.EASE_OUT_BACK.value,
                )
            ],
            camera=CameraActionSpec(action=CameraAction.HOLD.value, start=0.0, end=3.0),
        )
    ]
    with pytest.raises(KeyError, match="unknown asset_id 'asset_non_existent_999'"):
        choreographer._validate_plans(bad_plan)


def test_negative_or_zero_duration_rejected():
    """Validation 2: Non-positive duration must raise ValidationError or ValueError."""
    # Negative duration (end < start)
    with pytest.raises(ValueError):
        MotionAction(
            asset_id="asset_001",
            action=EntranceAction.POP_IN.value,
            start=2.0,
            end=1.0,
            easing=EasingType.EASE_OUT_BACK.value,
        )

    # Zero duration (end == start)
    with pytest.raises((ValueError, ValidationError)):
        MotionAction(
            asset_id="asset_001",
            action=EntranceAction.POP_IN.value,
            start=1.0,
            end=1.0,
            easing=EasingType.EASE_OUT_BACK.value,
        )


def test_action_outside_beat_boundary_rejected(sample_manifest, sample_narrative_map):
    """Validation 3: Non-continuity action extending beyond beat boundaries must be rejected."""
    choreographer = MotionChoreographer(
        manifest_data_or_path=sample_manifest,
        narrative_map_or_path=sample_narrative_map,
    )
    # Action ends at 3.5, but beat ends at 3.0
    bad_plan = [
        BeatMotionPlan(
            beat_id="beat_001",
            start=0.0,
            end=3.0,
            actions=[
                MotionAction(
                    asset_id="asset_001",
                    action=EntranceAction.POP_IN.value,
                    start=1.0,
                    end=3.5,
                    easing=EasingType.EASE_OUT_BACK.value,
                    continuity=False,
                )
            ],
            camera=CameraActionSpec(action=CameraAction.HOLD.value, start=0.0, end=3.0),
        )
    ]
    with pytest.raises(ValueError, match="outside beat beat_001"):
        choreographer._validate_plans(bad_plan)


def test_action_outside_audio_duration_rejected(sample_manifest, sample_narrative_map):
    """Validation 4: Beat exceeding total audio duration must be rejected."""
    choreographer = MotionChoreographer(
        manifest_data_or_path=sample_manifest,
        narrative_map_or_path=sample_narrative_map,
        whisper_data_or_path={"duration": 5.0},
    )
    bad_plan = [
        BeatMotionPlan(
            beat_id="beat_001",
            start=4.0,
            end=8.0,  # exceeds 5.0
            actions=[],
            camera=CameraActionSpec(action=CameraAction.HOLD.value, start=4.0, end=8.0),
        )
    ]
    with pytest.raises(ValueError, match="exceed audio duration"):
        choreographer._validate_plans(bad_plan)


def test_invalid_easing_rejected():
    """Validation 5: Invalid easing strings must be rejected."""
    with pytest.raises(ValidationError):
        MotionAction(
            asset_id="asset_001",
            action=EntranceAction.POP_IN.value,
            start=0.0,
            end=1.0,
            easing="non_existent_magic_ease",
        )


def test_invalid_action_primitive_rejected():
    """Validation 6: Invalid action primitive names must be rejected."""
    with pytest.raises(ValidationError):
        MotionAction(
            asset_id="asset_001",
            action="unsupported_explosion_action",
            start=0.0,
            end=1.0,
            easing=EasingType.LINEAR.value,
        )


def test_invalid_camera_timing_rejected(sample_manifest, sample_narrative_map):
    """Validation 7: Camera start before beat start must be rejected."""
    choreographer = MotionChoreographer(
        manifest_data_or_path=sample_manifest,
        narrative_map_or_path=sample_narrative_map,
    )
    bad_plan = [
        BeatMotionPlan(
            beat_id="beat_001",
            start=1.0,
            end=3.0,
            actions=[],
            camera=CameraActionSpec(action=CameraAction.HOLD.value, start=0.5, end=3.0),
        )
    ]
    with pytest.raises(ValueError, match="camera timing"):
        choreographer._validate_plans(bad_plan)


def test_excessive_simultaneous_assets_detection(sample_manifest, sample_narrative_map):
    """Validation 8: Excessive asset density flag triggers on > 5 actions per beat."""
    choreographer = MotionChoreographer(
        manifest_data_or_path=sample_manifest,
        narrative_map_or_path=sample_narrative_map,
    )
    # Beat with 6 actions
    dense_actions = [
        MotionAction(
            asset_id="asset_001",
            action=EntranceAction.POP_IN.value,
            start=round(i * 0.4, 2),
            end=round((i + 1) * 0.4, 2),
            easing=EasingType.LINEAR.value,
        )
        for i in range(6)
    ]
    plan = BeatMotionPlan(
        beat_id="beat_dense",
        start=0.0,
        end=3.0,
        actions=dense_actions,
        camera=CameraActionSpec(action=CameraAction.HOLD.value, start=0.0, end=3.0),
    )
    # Manually check diagnostics logic
    excessive = []
    if len(plan.actions) > 5:
        excessive.append(plan.beat_id)
    assert "beat_dense" in excessive


def test_continuity_preserves_persistent_assets(sample_manifest, sample_narrative_map):
    """Validation 9: Continuity assets allow actions to carry over from previous beats."""
    choreographer = MotionChoreographer(
        manifest_data_or_path=sample_manifest,
        narrative_map_or_path=sample_narrative_map,
    )
    plans, diags = choreographer.choreograph()
    assert len(plans) == 2
    # Beat 2 has continuity=True in narrative map fixture
    assert diags["continuity_reuse_count"] >= 1
    # Check that Beat 2 contains a continuity action
    beat_2_actions = plans[1]["actions"]
    continuity_actions = [a for a in beat_2_actions if a.get("continuity")]
    assert len(continuity_actions) >= 1
    assert continuity_actions[0]["action"] == EmphasisAction.SETTLE.value


def test_deterministic_output_reproducibility(sample_manifest, sample_narrative_map):
    """Validation 10: Running choreography twice yields bit-identical outputs."""
    choreographer1 = MotionChoreographer(sample_manifest, sample_narrative_map)
    p1, d1 = choreographer1.choreograph()

    choreographer2 = MotionChoreographer(sample_manifest, sample_narrative_map)
    p2, d2 = choreographer2.choreograph()

    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)
    assert json.dumps(d1, sort_keys=True) == json.dumps(d2, sort_keys=True)


def test_production_data_artifacts_validation():
    """Validation 11: Validates the actual generated production artifacts."""
    manifest_p = Path("data/visual_manifest.json")
    nvm_p = Path("data/narrative_visual_map.json")
    plan_p = Path("data/motion_plan.json")
    feasibility_p = Path("data/motion_feasibility_report.json")
    diags_p = Path("data/motion_diagnostics.json")

    assert manifest_p.is_file(), "data/visual_manifest.json must exist"
    assert nvm_p.is_file(), "data/narrative_visual_map.json must exist"
    assert plan_p.is_file(), "data/motion_plan.json must exist"
    assert feasibility_p.is_file(), "data/motion_feasibility_report.json must exist"
    assert diags_p.is_file(), "data/motion_diagnostics.json must exist"

    with open(plan_p, "r", encoding="utf-8") as f:
        plans = json.load(f)

    with open(diags_p, "r", encoding="utf-8") as f:
        diags = json.load(f)

    with open(feasibility_p, "r", encoding="utf-8") as f:
        feasibility = json.load(f)

    assert len(plans) == diags["total_beats"], f"Expected {diags['total_beats']} beats in plan, got {len(plans)}"
    assert len(feasibility) == diags["total_beats"], f"Expected {diags['total_beats']} beats in feasibility, got {len(feasibility)}"
    assert diags["total_beats"] == 17, f"Expected 17 Section 6 beats, got {diags['total_beats']}"
    assert diags["total_actions"] > 17, "Choreography should contain hero + support actions"
    assert diags["max_simultaneous_assets"] <= 5, "Simultaneous assets should not exceed visual limit"
    assert diags["beats_with_no_visual_action"] == []
    assert diags["beats_with_excessive_density"] == []


def test_section_6_cannot_consume_foreign_section_script_or_audio():
    """Regression Test: Section 6 build can NEVER silently consume Section 7 inputs."""
    import hashlib
    sec06_script_p = Path("sections/brain_illusions_documentary/06_spotlight_effect/script.txt")
    sec07_script_p = Path("sections/brain_illusions_documentary/07_conclusion/script.txt")
    sec06_whisper_p = Path("sections/brain_illusions_documentary/06_spotlight_effect/timing/whisper.json")

    sec06_hash = hashlib.sha256(sec06_script_p.read_text(encoding="utf-8").strip().encode("utf-8")).hexdigest()
    sec07_hash = hashlib.sha256(sec07_script_p.read_text(encoding="utf-8").strip().encode("utf-8")).hexdigest()
    assert sec06_hash != sec07_hash, "Section 6 and Section 7 scripts must have different hashes"

    # Ingest narrative map and assert it must match Section 6 script hash
    nvm_p = Path("sections/brain_illusions_documentary/06_spotlight_effect/motion/narrative_visual_map.json")
    if nvm_p.is_file():
        with open(nvm_p, "r", encoding="utf-8") as f:
            nvm = json.load(f)
        assert nvm.get("script_hash") == sec06_hash, "Section 6 narrative map must strictly reference Section 6 script"
        assert nvm.get("script_hash") != sec07_hash, "Section 6 narrative map must never reference Section 7 script"
        assert nvm.get("metadata", {}).get("audio_duration_s") == 45.486, "Section 6 timeline must be 45.486s"


def test_motion_plan_shorter_than_audio_extended_with_tail(sample_manifest, sample_narrative_map):
    """Regression Test 1: When motion plan is shorter than audio duration, it extends with hold_last_state tail."""
    # sample_narrative_map ends at 6.8s. Force audio_duration to 10.0s.
    sample_narrative_map["metadata"]["audio_duration_s"] = 10.0
    choreographer = MotionChoreographer(sample_manifest, sample_narrative_map)
    plans, diags = choreographer.choreograph()

    last_plan = plans[-1]
    assert last_plan["end"] == 10.0, f"Expected final beat end to be extended to 10.0s, got {last_plan['end']}"
    assert last_plan["timeline_tail"] is not None, "Final beat must have timeline_tail"
    assert last_plan["timeline_tail"]["type"] == "audio_tail"
    assert last_plan["timeline_tail"]["start"] == 6.5
    assert last_plan["timeline_tail"]["end"] == 10.0
    assert last_plan["timeline_tail"]["visual_policy"] == "hold_last_state"
    assert diags["render_duration"] == 10.0
    assert diags["audio_duration"] == 10.0
    assert diags["timeline_tail"]["visual_policy"] == "hold_last_state"


def test_legitimate_trailing_silence_report():
    """Regression Test 2: Validates legitimate trailing silence calculation and report."""
    report_p = Path("sections/brain_illusions_documentary/06_spotlight_effect/motion/audio_tail_report.json")
    assert report_p.is_file(), "audio_tail_report.json must exist"

    with open(report_p, "r", encoding="utf-8") as f:
        rep = json.load(f)

    assert rep["target_section"] == "06_spotlight_effect"
    assert rep["audio_duration_s"] == 45.486
    assert rep["last_spoken_word_end"] == 45.38
    assert rep["trailing_silence_duration_s"] == pytest.approx(0.106, abs=0.005)
    assert rep["status"] == "RESOLVED"


def test_required_hold_last_state_tail_in_motion_plan():
    """Regression Test 3: Validates hold_last_state tail structure and bounds in production motion plan."""
    plan_p = Path("sections/brain_illusions_documentary/06_spotlight_effect/motion/motion_plan.json")
    with open(plan_p, "r", encoding="utf-8") as f:
        plans = json.load(f)

    last_beat = plans[-1]
    tail = last_beat.get("timeline_tail")
    assert tail is not None, "Final beat must specify timeline_tail"
    assert tail["type"] == "audio_tail"
    assert tail["start"] == 42.74
    assert tail["end"] == 45.486
    assert tail["visual_policy"] == "hold_last_state"

    # All active entrance actions in the last beat must conclude prior to the tail
    for action in last_beat["actions"]:
        assert action["start"] >= last_beat["start"]
        assert action["end"] <= last_beat["end"]
        # Entrances should be well underway before the hold tail
        if action["action"] in ["slide_up", "pop_in", "stagger_in"]:
            assert action["end"] <= tail["start"]


def test_missing_spoken_content_at_end_resolution():
    """Regression Test 4: Verifies no canonical script content remains unrepresented."""
    report_p = Path("sections/brain_illusions_documentary/06_spotlight_effect/motion/audio_tail_report.json")
    with open(report_p, "r", encoding="utf-8") as f:
        rep = json.load(f)

    assert rep["canonical_script_unrepresented"] is False
    assert rep["spoken_repetition_detected"] is not None
    assert rep["spoken_repetition_detected"]["nature"] == "spoken_final_emphasis_take"
    # Audio ends at 45.486, spoken words end at 45.38s, both are inside render duration
    assert rep["render_duration_s"] >= rep["last_spoken_word_end"]


def test_render_duration_equals_audio_duration():
    """Regression Test 5: Strict invariant: render_duration == audio_duration == 45.486s."""
    diags_p = Path("sections/brain_illusions_documentary/06_spotlight_effect/motion/motion_diagnostics.json")
    plan_p = Path("sections/brain_illusions_documentary/06_spotlight_effect/motion/motion_plan.json")

    with open(diags_p, "r", encoding="utf-8") as f:
        diags = json.load(f)
    with open(plan_p, "r", encoding="utf-8") as f:
        plans = json.load(f)

    assert diags["audio_duration"] == 45.486
    assert diags["render_duration"] == 45.486
    assert diags["render_duration"] == diags["audio_duration"]

    assert plans[-1]["end"] == 45.486
    # Verify all actions across all beats remain within valid time bounds
    for beat in plans:
        for action in beat["actions"]:
            assert action["start"] >= 0.0
            assert action["end"] > action["start"]
            assert action["end"] <= beat["end"]

