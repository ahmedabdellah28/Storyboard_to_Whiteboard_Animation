"""Tests for Composition-First Motion Graphics Renderer (Task 9).

Validates:
- composition state resolution
- hero/support visibility
- normalized layout
- camera targeting composition
- asset lifetime
- continuity
- maximum simultaneous assets and zero violations
"""

import json
from pathlib import Path
import pytest
import numpy as np

from production_engine.motion_graphics_engine import (
    DeclarativeMotionGraphicsEngine,
    CompositionCameraTrajectory,
)

ROOT_DIR = Path(r"E:\image_to_animate")


@pytest.fixture
def section6_paths():
    base = ROOT_DIR / "sections" / "brain_illusions_documentary" / "06_spotlight_effect"
    return {
        "motion_plan": str(ROOT_DIR / "data" / "motion_plan.json"),
        "shot_plan": str(ROOT_DIR / "data" / "shot_plan.json"),
        "camera_plan": str(ROOT_DIR / "data" / "camera_plan.json"),
        "manifest": str(ROOT_DIR / "data" / "visual_manifest.json"),
        "assets_dir": str(ROOT_DIR / "asset_sheet_extractor_v2_output" / "assets"),
        "audio": str(base / "master_audio.wav"),
        "output": str(base / "motion" / "preview_composition_v3.mp4"),
    }


@pytest.fixture
def renderer_engine(section6_paths):
    return DeclarativeMotionGraphicsEngine(
        motion_plan_path=section6_paths["motion_plan"],
        manifest_path=section6_paths["manifest"],
        assets_dir=section6_paths["assets_dir"],
        audio_path=section6_paths["audio"],
        output_path=section6_paths["output"],
        shot_plan_path=section6_paths["shot_plan"],
        camera_plan_path=section6_paths["camera_plan"],
        width=1280,
        height=720,
        fps=30,
    )


def test_composition_state_resolution(renderer_engine):
    """Verifies that engine resolves the correct Shot and CompositionState at any narrative timestamp."""
    test_cases = [
        (1.0, "shot_001", "asset_001"),
        (7.0, "shot_002", "asset_002"),
        (13.0, "shot_003", "asset_013"),
        (20.5, "shot_004", "asset_001"),
        (23.0, "shot_005", "asset_010"),
        (28.0, "shot_006", "asset_006"),
        (42.0, "shot_007", "asset_017"),
    ]
    for t, expected_shot_id, expected_hero in test_cases:
        shot = renderer_engine.resolve_shot(t)
        assert shot is not None, f"Expected active shot at t={t}"
        assert shot["shot_id"] == expected_shot_id, f"Expected {expected_shot_id} at t={t}, got {shot['shot_id']}"
        comp = shot.get("composition_state", shot)
        hero = comp.get("hero") or (shot.get("hero_assets", [None])[0])
        assert hero == expected_hero, f"Expected hero {expected_hero} in {expected_shot_id}, got {hero}"


def test_hero_and_support_visibility(renderer_engine):
    """Verifies hero and support elements are visible strictly according to their scheduled timeline."""
    # Before shot 1 hero appears at 0.56s
    _, m0 = renderer_engine.render_frame(0.20)
    assert m0["visible_assets"] == 0, "No assets should be visible before 0.56s"

    # Shot 1 hero after pop-in
    _, m1 = renderer_engine.render_frame(1.00)
    assert m1["visible_assets"] == 1, "Only hero asset_001 should be visible at t=1.0s"

    # Shot 1 support appears around 2.20s
    _, m2 = renderer_engine.render_frame(3.00)
    assert m2["visible_assets"] == 3, "Hero, support, and accent should all be visible at t=3.0s"


def test_normalized_layout_coordinates(renderer_engine):
    """Verifies all rendered assets use normalized coordinates in [0.0, 1.0], never asset-sheet bboxes."""
    for s in renderer_engine.shot_plan:
        comp = s.get("composition_state", s)
        norm_positions = comp.get("normalized_positions", {})
        for aid, (nx, ny) in norm_positions.items():
            assert 0.0 <= nx <= 1.0, f"Asset {aid} X={nx} not in [0.0, 1.0] in {s['shot_id']}"
            assert 0.0 <= ny <= 1.0, f"Asset {aid} Y={ny} not in [0.0, 1.0] in {s['shot_id']}"


def test_camera_targeting_composition_not_isolated_assets(renderer_engine):
    """Verifies camera targets composition focal points and zooms, never isolated sequential assets."""
    for c in renderer_engine.camera.camera_specs:
        fp = c.get("focal_point")
        assert fp is not None, "Camera must define composition focal point"
        assert len(fp) == 2
        assert 0.0 <= fp[0] <= 1.0, f"Focal point X={fp[0]} not in [0.0, 1.0]"
        assert 0.0 <= fp[1] <= 1.0, f"Focal point Y={fp[1]} not in [0.0, 1.0]"
        # No asset ID target allowed
        assert "target" not in c or c["target"] is None or not str(c["target"]).startswith("asset_")

    # Sample camera states along timeline
    for t in np.linspace(0.0, 45.486, 100):
        cx, cy, cz = renderer_engine.camera.get_state(float(t))
        assert 0.40 <= cx <= 0.60, f"Camera focal X={cx} off composition center at t={t}"
        assert 0.40 <= cy <= 0.60, f"Camera focal Y={cy} off composition center at t={t}"
        assert 0.90 <= cz <= 1.30, f"Camera zoom={cz} out of cinematic range at t={t}"


def test_asset_lifetime_and_continuity(renderer_engine):
    """Verifies non-persistent assets do not linger beyond their shot boundary."""
    # Shot 1 ends at 5.84s (with hero asset_001). In Shot 2 (5.84-10.46s), hero is asset_002.
    frame_s1, m_s1 = renderer_engine.render_frame(5.0)
    assert m_s1["visible_assets"] == 3

    # Shot 2 active at 7.0s
    frame_s2, m_s2 = renderer_engine.render_frame(7.0)
    # asset_001 must not be visible in Shot 2
    cur_shot_2 = renderer_engine.resolve_shot(7.0)
    assert cur_shot_2["shot_id"] == "shot_002"
    assert "asset_001" not in cur_shot_2["hero_assets"]
    assert "asset_001" not in cur_shot_2["support_assets"]
    assert "asset_001" not in cur_shot_2["accent_assets"]


def test_maximum_simultaneous_assets_and_zero_violations(renderer_engine):
    """Verifies across all frames that simultaneous assets <= 5, violations == 0, and offscreen == 0."""
    max_simul = 0
    total_violations = 0
    total_offscreen = 0
    blank_frames_after_speech_start = 0

    for f in range(renderer_engine.total_frames):
        t = f / float(renderer_engine.fps)
        _, metrics = renderer_engine.render_frame(t)

        max_simul = max(max_simul, metrics["visible_assets"])
        total_violations += metrics.get("composition_violations", 0)
        total_offscreen += metrics["offscreen_assets"]

        if metrics["is_blank"] and t >= 0.56:
            blank_frames_after_speech_start += 1

    assert max_simul <= 5, f"Maximum simultaneous assets was {max_simul}, expected <= 5"
    assert total_violations == 0, f"Expected 0 composition violations, got {total_violations}"
    assert total_offscreen == 0, f"Expected 0 offscreen assets, got {total_offscreen}"
    assert blank_frames_after_speech_start == 0, f"Expected 0 blank frames after speech start, got {blank_frames_after_speech_start}"
