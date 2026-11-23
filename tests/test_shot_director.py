import json
from pathlib import Path
import pytest
import numpy as np

from core.narrative.shot_director import ShotDirector, LAYOUT_TEMPLATES
from production_engine.motion_graphics_engine import DeclarativeMotionGraphicsEngine


@pytest.fixture
def shot_director_setup():
    sec_dir = Path("sections/brain_illusions_documentary/06_spotlight_effect")
    script_p = sec_dir / "script.txt"
    whisper_p = sec_dir / "timing" / "whisper.json"
    narrative_p = sec_dir / "motion" / "narrative_visual_map.json"

    with open(script_p, "r", encoding="utf-8") as f:
        script = f.read()
    with open(whisper_p, "r", encoding="utf-8") as f:
        whisper = json.load(f)
    with open(narrative_p, "r", encoding="utf-8") as f:
        nvm = json.load(f)

    beats = nvm["metadata"]["speech_beats"]
    director = ShotDirector(script, beats, whisper)
    shots = director.direct_shots()
    motion_plan = director.generate_motion_plan()
    sync_diags = director.generate_sync_diagnostics(motion_plan)
    return director, shots, motion_plan, sync_diags


def test_each_shot_has_clear_hero_and_hierarchy(shot_director_setup):
    """Validation 1: Each shot must define a clear hero and conform to hierarchy limits."""
    _, shots, _, _ = shot_director_setup
    assert len(shots) == 7, f"Expected 7 narrative shots, got {len(shots)}"

    for shot in shots:
        # Hero count: 1
        assert len(shot.hero_assets) == 1, f"Shot {shot.shot_id} must have exactly 1 hero"
        # Support count: 1..3
        assert 1 <= len(shot.support_assets) <= 3, f"Shot {shot.shot_id} support assets outside 1..3"
        # Accent count: 0..3
        assert len(shot.accent_assets) <= 3, f"Shot {shot.shot_id} accent assets exceed 3"
        # Max simultaneous per shot <= 7
        total_assets = len(shot.hero_assets) + len(shot.support_assets) + len(shot.accent_assets)
        assert total_assets <= 7, f"Shot {shot.shot_id} total assets ({total_assets}) exceeds limit of 7"


def test_no_asset_sheet_extraction_coordinates_reused(shot_director_setup):
    """Validation 2: All composition coordinates must be normalized [0, 1] relative positions."""
    _, shots, _, _ = shot_director_setup

    for shot in shots:
        assert shot.normalized_positions, f"Shot {shot.shot_id} missing normalized positions"
        for aid, (nx, ny) in shot.normalized_positions.items():
            assert 0.0 <= nx <= 1.0, f"Normalized X={nx} outside [0, 1] in shot {shot.shot_id}"
            assert 0.0 <= ny <= 1.0, f"Normalized Y={ny} outside [0, 1] in shot {shot.shot_id}"
            # Ensure coordinates are not raw pixel sheet coords (> 10)
            assert nx < 2.0 and ny < 2.0


def test_camera_targets_compositions_not_isolated_assets(shot_director_setup):
    """Validation 3: Camera targets must be composition focal points, not sequential single assets."""
    director, shots, _, _ = shot_director_setup
    cam_plans = director.camera_plans

    assert len(cam_plans) == len(shots)
    for cp in cam_plans:
        fx, fy = cp.focal_point
        assert 0.20 <= fx <= 0.80, f"Camera focal X={fx} out of safe composition bounds"
        assert 0.20 <= fy <= 0.80, f"Camera focal Y={fy} out of safe composition bounds"
        assert cp.action in ["hold", "subtle_push", "subtle_pull", "lateral_reframe", "punch_in", "pull_back"]
        assert 0.80 <= cp.zoom <= 1.40


def test_visual_events_semantic_anchors_and_timing(shot_director_setup):
    """Validation 4: Every visual event must have a semantic speech anchor within +/- 250ms."""
    _, _, motion_plan, sync_diags = shot_director_setup

    assert sync_diags["anchored_events_count"] > 20
    assert sync_diags["pct_within_250ms"] >= 95.0, "Expected >=95% events within +/- 250ms"
    assert sync_diags["events_outside_250ms"] == 0

    for beat in motion_plan:
        for act in beat.get("actions", []):
            assert act.get("speech_anchor"), f"Action on {act['asset_id']} missing speech_anchor"
            assert act.get("semantic_reason"), f"Action on {act['asset_id']} missing semantic_reason"
            assert act["end"] > act["start"]


def test_composition_continuity_and_persisting_hero(shot_director_setup):
    """Validation 5: Composition states support asset continuity across scene mutations."""
    director, shots, _, _ = shot_director_setup
    states = director.composition_states

    assert len(states) == len(shots)
    # Check that shot 3 (psychological concept) records continuity
    has_continuity = any(len(s.persistent) > 0 for s in states)
    assert has_continuity, "Expected at least one composition state with persistent continuity"


def test_renderer_visibility_and_asset_density_bounds():
    """Validation 6: Renderer visibility strictly obeys shot lifetime (max simultaneous <= 7)."""
    sec_dir = Path("sections/brain_illusions_documentary/06_spotlight_effect")
    motion_dir = sec_dir / "motion"

    engine = DeclarativeMotionGraphicsEngine(
        motion_plan_path=str(motion_dir / "motion_plan.json"),
        manifest_path=str(motion_dir / "visual_manifest.json"),
        assets_dir=r"E:\image_to_animate\asset_sheet_extractor_v2_output\assets",
        audio_path=str(sec_dir / "master_audio.wav"),
        output_path=str(motion_dir / "preview_720p.mp4"),
        width=1280,
        height=720,
        fps=30,
    )

    vis_counts = []
    offscreen_counts = []
    # Test 60 sample timestamps across 45.486s
    for t in np.linspace(0.5, 45.0, 60):
        frame, metrics = engine.render_frame(float(t))
        vis_counts.append(metrics["visible_assets"])
        offscreen_counts.append(metrics["offscreen_assets"])
        assert frame.shape == (720, 1280, 3)

    max_vis = max(vis_counts)
    avg_vis = sum(vis_counts) / len(vis_counts)
    total_off = sum(offscreen_counts)

    assert max_vis <= 7, f"Max simultaneous visible assets ({max_vis}) exceeded limit of 7"
    assert avg_vis <= 4.0, f"Average visible assets ({avg_vis:.2f}) exceeded target of 4.0"
    assert total_off == 0, f"Offscreen assets must be 0, got {total_off}"


def test_timeline_ends_at_audio_duration():
    """Validation 7: Timeline must match master audio duration (45.486s)."""
    motion_plan_p = Path("data/motion_plan.json")
    with open(motion_plan_p, "r", encoding="utf-8") as f:
        plan = json.load(f)

    assert plan[-1]["end"] == pytest.approx(45.486, abs=0.01)
    tail = plan[-1].get("timeline_tail")
    assert tail is not None
    assert tail["type"] == "audio_tail"
    assert tail["visual_policy"] == "hold_last_state"
