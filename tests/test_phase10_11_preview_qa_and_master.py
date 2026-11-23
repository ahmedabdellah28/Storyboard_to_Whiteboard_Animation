"""Phase 10 & 11 Test Suite: Video Preview Player, Post-Render QA, and Master Assembly.

Validates:
1. PostRenderQAEngine forensic inspection (resolution, drift, black frames, audio clipping).
2. MasterConcatenator multi-section discovery, sequencing, and manifest generation.
3. StudioVideoPlayerWidget frame decoding, playback controls, stepping, and speed.
4. PostRenderQADialog UI loading and metric card population.
5. MasterAssemblyDialog section roster and assembly trigger.
6. StudioMainWindow master film button integration.
"""

import json
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any, Dict

import cv2
import numpy as np
import pytest

from core.contracts.qa_reports import PostRenderQAReport, QAGateStatus
from core.orchestration.master_concatenator import MasterConcatenator
from core.state.project_state import ProjectState, SectionState
from core.state.state_store import StateStore
from core.validation.post_render_qa import PostRenderQAEngine
from studio_ui.dialogs.master_assembly_dialog import MasterAssemblyDialog
from studio_ui.dialogs.post_render_qa_dialog import PostRenderQADialog
from studio_ui.main_window import StudioMainWindow
from studio_ui.qt import QApplication, QMessageBox
from studio_ui.views.studio_player import StudioPlayerDialog, StudioVideoPlayerWidget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    return app


@pytest.fixture(autouse=True)
def mock_dialogs(monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)


def _generate_synthetic_video(file_path: Path, width=1920, height=1080, fps=30.0, num_frames=30) -> None:
    """Helper to generate a lightweight valid MP4 video using OpenCV."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(file_path), fourcc, fps, (width, height))
    for i in range(num_frames):
        # White background with drawing line to avoid black frame trigger
        frame = np.full((height, width, 3), 240, dtype=np.uint8)
        cv2.line(frame, (100, 100), (100 + i * 10, 100 + i * 5), (20, 20, 20), 4)
        out.write(frame)
    out.release()


def _generate_synthetic_audio(file_path: Path, duration_sec=1.0, sample_rate=44100) -> None:
    """Helper to generate a lightweight valid WAV audio file."""
    num_samples = int(duration_sec * sample_rate)
    # Generate 440 Hz sine tone at 0.5 amplitude
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    audio_data = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)

    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())


@pytest.fixture
def qa_test_env():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        base = Path(tmpdir)
        vid_path = base / "test_1080p.mp4"
        aud_path = base / "test_audio.wav"

        _generate_synthetic_video(vid_path, width=1920, height=1080, fps=30.0, num_frames=30)
        _generate_synthetic_audio(aud_path, duration_sec=1.0)

        yield base, vid_path, aud_path


# ----------------------------------------------------------------------------
# 1. Post-Render QA Tests
# ----------------------------------------------------------------------------

def test_post_render_qa_valid_pass(qa_test_env):
    """Verify PostRenderQAEngine passes a valid 1080p video with synced audio."""
    base, vid_path, aud_path = qa_test_env
    engine = PostRenderQAEngine()
    rep_file = base / "qa_report.json"

    report = engine.inspect(
        video_path=vid_path,
        audio_path=aud_path,
        section_id="sec_01",
        output_report_path=rep_file,
    )

    assert report.overall_status == QAGateStatus.PASS
    assert report.resolution == "1920x1080"
    assert report.fps == 30.0
    assert report.duration_drift < 0.1
    assert report.black_frames_count == 0
    assert not report.audio_clipping_detected
    assert rep_file.exists()


def test_post_render_qa_missing_file():
    """Verify PostRenderQAEngine handles nonexistent video file gracefully."""
    engine = PostRenderQAEngine()
    report = engine.inspect(video_path="/nonexistent/missing.mp4", section_id="sec_err")

    assert report.overall_status == QAGateStatus.FAIL
    assert len(report.checks) == 1
    assert report.checks[0].check_id == "file_existence"


# ----------------------------------------------------------------------------
# 2. Master Concatenation Tests
# ----------------------------------------------------------------------------

def test_master_concatenator_discovery_and_manifest(monkeypatch):
    """Verify MasterConcatenator orders sections and writes master_manifest.json."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        base = Path(tmpdir)
        state_dir = base / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)
        store = StateStore(base_dir=state_dir)

        proj_dir = base / "proj_master"
        proj_dir.mkdir(parents=True, exist_ok=True)

        project = ProjectState(
            project_id="master_proj_test",
            title="Master Film Test",
            metadata={"project_path": str(proj_dir)},
        )

        # Create two sections
        s1 = project.get_or_create_section("01_intro", title="Introduction", sequence_index=0)
        s2 = project.get_or_create_section("02_body", title="Body Content", sequence_index=1)
        store.save_state(project)

        # Create synthetic videos
        s1_dir = proj_dir / "sections" / "01_intro"
        s1_dir.mkdir(parents=True, exist_ok=True)
        _generate_synthetic_video(s1_dir / "final_whiteboard_1080p.mp4", num_frames=30)

        s2_dir = proj_dir / "sections" / "02_body"
        s2_dir.mkdir(parents=True, exist_ok=True)
        _generate_synthetic_video(s2_dir / "final_whiteboard_1080p.mp4", num_frames=60)

        out_dir = base / "deliverables"

        # Mock FFmpeg call to create dummy file rather than requiring external ffmpeg binary in tests
        def mock_subprocess_run(cmd, *args, **kwargs):
            out_file = Path(cmd[-1])
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.touch()
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        concat = MasterConcatenator(
            project_id="master_proj_test",
            state_store=store,
            output_dir=out_dir,
        )

        progress_log = []
        manifest = concat.assemble(progress_cb=lambda msg, p: progress_log.append((msg, p)))

        assert manifest["sections_count"] == 2
        assert len(manifest["chapters"]) == 2
        assert manifest["chapters"][0]["section_id"] == "01_intro"
        assert manifest["chapters"][1]["section_id"] == "02_body"
        assert manifest["chapters"][0]["start_time"] == 0.0
        assert manifest["chapters"][1]["start_time"] == pytest.approx(1.0, 0.05)

        manifest_file = out_dir / "master_manifest.json"
        assert manifest_file.exists()
        assert len(progress_log) >= 3


# ----------------------------------------------------------------------------
# 3. Studio Video Player Tests
# ----------------------------------------------------------------------------

def test_studio_video_player_widget(qapp, qa_test_env):
    """Verify StudioVideoPlayerWidget frame stepping, scrubbing, and speed changes."""
    base, vid_path, aud_path = qa_test_env
    player = StudioVideoPlayerWidget()

    ok = player.load_video(vid_path)
    assert ok is True
    assert player.total_frames == 30
    assert player.fps == 30.0
    assert player.duration == pytest.approx(1.0, 0.05)

    # Frame stepping
    player.step_forward()
    assert player.current_frame_idx == 1

    player.step_forward()
    assert player.current_frame_idx == 2

    player.step_backward()
    assert player.current_frame_idx == 1

    # Seek frame
    player.seek_frame(15)
    assert player.current_frame_idx == 15

    # Speed control
    player.speed_combo.setCurrentText("2.0x")
    assert player.speed == 2.0

    # Play/Pause toggle
    player.play()
    assert player.is_playing is True
    player.pause()
    assert player.is_playing is False


# ----------------------------------------------------------------------------
# 4. Dialog & Integration Tests
# ----------------------------------------------------------------------------

def test_post_render_qa_dialog(qapp, qa_test_env):
    """Verify PostRenderQADialog initializes and populates metrics from inspection."""
    base, vid_path, aud_path = qa_test_env
    dlg = PostRenderQADialog(video_path=vid_path, section_id="test_sec")

    assert dlg.report is not None
    assert dlg.report.overall_status == QAGateStatus.PASS
    assert dlg.status_badge.text() == "PASSED"
    assert dlg.checks_table.rowCount() == len(dlg.report.checks)


def test_master_assembly_dialog_roster(qapp):
    """Verify MasterAssemblyDialog correctly displays section sequence and status."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        base = Path(tmpdir)
        store = StateStore(base_dir=base / ".state")

        project = ProjectState(project_id="dialog_test_proj", title="Test Title")
        project.get_or_create_section("01_intro", title="Intro Section", sequence_index=0)
        project.get_or_create_section("02_outro", title="Outro Section", sequence_index=1)
        store.save_state(project)

        dlg = MasterAssemblyDialog(project=project, state_store=store)
        assert dlg.sections_table.rowCount() == 2
        assert "Intro Section" in dlg.sections_table.item(0, 1).text()
        assert "Outro Section" in dlg.sections_table.item(1, 1).text()


def test_main_window_master_film_button(qapp, monkeypatch):
    """Verify StudioMainWindow has Assemble Master Film button and handler."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        base = Path(tmpdir)
        store = StateStore(base_dir=base / ".state")
        window = StudioMainWindow(state_store=store)

        project = ProjectState(project_id="btn_test_proj", title="Main Window Test")
        store.save_state(project)
        window.load_project(project)

        assert hasattr(window, "master_btn")
        assert window.master_btn.isEnabled()

        dialog_opened = []
        from studio_ui.dialogs.master_assembly_dialog import MasterAssemblyDialog
        monkeypatch.setattr(MasterAssemblyDialog, "exec", lambda self: dialog_opened.append(True))

        window.master_btn.click()
        assert len(dialog_opened) == 1
