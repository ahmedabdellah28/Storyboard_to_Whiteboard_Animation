import json
from pathlib import Path
import pytest
import numpy as np

from production_engine.motion_graphics_engine import (
    DeclarativeMotionGraphicsEngine,
    DeclarativeCameraTrajectory,
    apply_easing,
)


@pytest.fixture
def motion_paths():
    base = Path("sections/brain_illusions_documentary/06_spotlight_effect")
    return {
        "motion_plan": str(base / "motion" / "motion_plan.json"),
        "manifest": str(base / "motion" / "visual_manifest.json"),
        "assets_dir": r"E:\image_to_animate\asset_sheet_extractor_v2_output\assets",
        "audio": str(base / "master_audio.wav"),
        "output": str(base / "motion" / "preview_720p.mp4"),
        "metadata": base / "motion" / "preview_metadata.json",
        "diagnostics": base / "motion" / "motion_render_diagnostics.json",
        "contact_sheet": base / "motion" / "preview_contact_sheet.png",
    }


def test_declarative_motion_renderer_initialization(motion_paths):
    """Verifies that DeclarativeMotionGraphicsEngine parses motion plan and manifest without errors."""
    engine = DeclarativeMotionGraphicsEngine(
        motion_plan_path=motion_paths["motion_plan"],
        manifest_path=motion_paths["manifest"],
        assets_dir=motion_paths["assets_dir"],
        audio_path=motion_paths["audio"],
        output_path=motion_paths["output"],
        width=1280,
        height=720,
        fps=30,
    )
    assert engine.duration_sec == pytest.approx(45.486, abs=0.01)
    assert engine.total_frames == 1365
    assert len(engine.missing_assets) == 0, f"Expected 0 missing assets, got {engine.missing_assets}"
    assert len(engine.actions) == 35
    assert len(engine.camera.camera_specs) == 17


def test_camera_trajectory_continuity_and_finite_bounds(motion_paths):
    """Verifies camera path contains no NaNs or Infs and stays within valid coordinate ranges."""
    with open(motion_paths["manifest"], "r", encoding="utf-8") as f:
        manifest = json.load(f)
    with open(motion_paths["motion_plan"], "r", encoding="utf-8") as f:
        motion_plan = json.load(f)

    entities = {e["visual_id"]: e for e in manifest.get("entities", [])}
    camera_specs = [b["camera"] for b in motion_plan if b.get("camera")]

    cam = DeclarativeCameraTrajectory(
        camera_specs=camera_specs,
        manifest_entities=entities,
        canvas_dims=(1536, 1024),
        preview_dims=(1280, 720),
        base_zoom=720.0 / 1024.0,
    )

    # Sample timestamps across the entire 45.486s timeline
    for t in np.linspace(0.0, 45.486, 200):
        cx, cy, cz = cam.get_state(float(t))
        assert not np.isnan(cx) and not np.isinf(cx)
        assert not np.isnan(cy) and not np.isinf(cy)
        assert not np.isnan(cz) and not np.isinf(cz)
        assert 0.0 < cx < 2000.0, f"Camera X={cx} out of bounds at t={t}"
        assert 0.0 < cy < 1500.0, f"Camera Y={cy} out of bounds at t={t}"
        assert 0.4 <= cz <= 2.0, f"Camera Zoom={cz} out of bounds at t={t}"


def test_frame_rendering_bounds_and_no_nan(motion_paths):
    """Verifies that rendered frames produce valid uint8 image buffers with content."""
    engine = DeclarativeMotionGraphicsEngine(
        motion_plan_path=motion_paths["motion_plan"],
        manifest_path=motion_paths["manifest"],
        assets_dir=motion_paths["assets_dir"],
        audio_path=motion_paths["audio"],
        output_path=motion_paths["output"],
        width=1280,
        height=720,
        fps=30,
    )

    # Test key frames
    for t in [1.0, 10.0, 22.0, 35.0, 45.486]:
        frame, metrics = engine.render_frame(t)
        assert frame.shape == (720, 1280, 3)
        assert frame.dtype == np.uint8
        assert not metrics["is_blank"], f"Frame at t={t} should contain visible rendered assets"
        assert metrics["visible_assets"] > 0


def test_preview_render_artifacts_and_diagnostics(motion_paths):
    """Verifies all required Task 6 preview artifacts exist and meet objective quality metrics."""
    assert Path(motion_paths["output"]).is_file(), "preview_720p.mp4 must exist"
    assert motion_paths["metadata"].is_file(), "preview_metadata.json must exist"
    assert motion_paths["diagnostics"].is_file(), "motion_render_diagnostics.json must exist"
    assert motion_paths["contact_sheet"].is_file(), "preview_contact_sheet.png must exist"

    with open(motion_paths["metadata"], "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["resolution"] == "1280x720"
    assert meta["fps"] == 30
    assert meta["duration"] == pytest.approx(45.486, abs=0.01)
    assert meta["frame_count"] == 1365
    assert meta["audio_duration"] == pytest.approx(45.486, abs=0.01)

    with open(motion_paths["diagnostics"], "r", encoding="utf-8") as f:
        diags = json.load(f)
    assert diags["blank_frame_count"] == 0, "No blank frames permitted"
    assert diags["missing_asset_count"] == 0, "All 38 referenced assets must be present"
    assert diags["dropped_frame_count"] == 0
    assert diags["action_count"] == 50
    assert diags["camera_movement_count"] == 17
    assert diags["render_duration"] == pytest.approx(45.486, abs=0.01)
