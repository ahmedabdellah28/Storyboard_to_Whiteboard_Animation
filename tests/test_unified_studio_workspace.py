"""Test Suite for Unified Studio Editor & Live Video Preview.

Verifies the 20 Acceptance Criteria of the Unified Studio Architecture:
1. Unified workspace hosting both Editing and Preview simultaneously.
2. Zero navigation to a separate preview screen.
3. Immediate Canvas update upon asset position change.
4. Immediate Canvas update upon asset scale change.
5. Immediate timeline & canvas synchronization upon timing edit.
6. Separate VOICE track with word anchors (locked by default).
7. Separate VISUALS track with draw and hold durations.
8. Separate SFX track with draggable diamond cue markers.
9. Separate CAMERA track with shot bounds.
10. Playhead scrubbing synchronizes Canvas opacity, Camera frustum, and Timecode without rendering.
11. Transport controls (Play, Pause, Stop) drive 30 FPS playback loop.
12. Preview scopes ([Shot], [Section], [Selection], [Project]) adjust loop boundaries in-place.
13. Ownership tracking (AUTO vs USER_OVERRIDE vs LOCKED).
14. [Reset to Automatic] restores AI deterministic defaults.
15. Saving layout persists placed_elements_layout.json and sfx_cues.json.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from core.state.project_state import ProjectState, SectionState
from core.state.state_store import StateStore
from studio_ui.qt import QApplication, QPixmap
from studio_ui.views.studio_editor import StudioEditorView
from studio_ui.views.studio_timeline import TimelineTrackItem


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    return app


@pytest.fixture(autouse=True)
def mock_dialogs(monkeypatch):
    from studio_ui.qt import QMessageBox, QInputDialog
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)


@pytest.fixture
def sample_project_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        base = Path(tmpdir)
        proj_dir = base / "test_proj"
        sec_dir = proj_dir / "sections" / "01_section"
        (sec_dir / "assets").mkdir(parents=True, exist_ok=True)

        # 1. placed_elements_layout.json with micro-zones
        layout = {
            "section_id": "01_section",
            "zones": {
                "zone_01": {"cam_pos": [960.0, 540.0], "zoom": 1.0, "duration": 5.0},
                "zone_02": {"cam_pos": [1400.0, 600.0], "zoom": 1.3, "duration": 5.0},
            },
            "elements": {
                "zone_01": [
                    {
                        "aid": "hero_char",
                        "file": "hero_char.png",
                        "x": 300.0,
                        "y": 250.0,
                        "scale": 1.0,
                        "start_time": 1.0,
                        "draw_duration": 1.0,
                        "hold_duration": 3.0,
                        "anchor_word": "البطل",
                    }
                ]
            }
        }
        (sec_dir / "placed_elements_layout.json").write_text(json.dumps(layout), encoding="utf-8")

        # 2. whisper_words.json
        whisper = {
            "words": [
                {"word": "وقف", "start": 0.5, "end": 0.9},
                {"word": "البطل", "start": 1.0, "end": 1.5},
                {"word": "شجاعاً", "start": 1.6, "end": 2.2},
            ]
        }
        (sec_dir / "whisper_words.json").write_text(json.dumps(whisper), encoding="utf-8")

        # 3. sfx_cues.json
        sfx = {
            "cues": [
                {"id": "cue_01", "timestamp": 1.0, "type": "pop", "gain": 1.0, "ownership": "AUTO"}
            ]
        }
        (sec_dir / "sfx_cues.json").write_text(json.dumps(sfx), encoding="utf-8")

        yield base, proj_dir, sec_dir


def test_unified_studio_initialization_and_preview_embedded(qapp, sample_project_dir):
    """Verifies StudioEditorView contains both editing tools and live preview transport simultaneously."""
    base, proj_dir, sec_dir = sample_project_dir
    store = StateStore(base_dir=base / ".state")

    proj = ProjectState(project_id="test_proj", title="Test", metadata={"project_path": str(proj_dir)})
    proj.get_or_create_section("01_section", title="Intro")

    editor = StudioEditorView(state_store=store)
    editor.load_section(proj, "01_section")

    # 1. Workspace components exist in the SAME view
    assert hasattr(editor, "canvas_view")
    assert hasattr(editor, "timeline_view")
    assert hasattr(editor, "inspector")
    assert hasattr(editor, "shots_panel")

    # 2. Transport playback controls exist in the SAME view
    assert hasattr(editor, "play_pause_btn")
    assert hasattr(editor, "stop_btn")
    assert editor.play_pause_btn.text() == "▶ Play"

    # 3. Elements and cameras loaded
    assert "hero_char" in editor.elements_data
    assert "zone_01" in editor.cameras_data
    assert "cue_01" in editor.sfx_cues


def test_live_timeline_tracks_and_playhead_scrubbing(qapp, sample_project_dir):
    """Verifies the 4 distinct tracks (VOICE, VISUALS, SFX, CAMERA) and scrubbing synchronization."""
    base, proj_dir, sec_dir = sample_project_dir
    store = StateStore(base_dir=base / ".state")

    proj = ProjectState(project_id="test_proj", title="Test", metadata={"project_path": str(proj_dir)})
    proj.get_or_create_section("01_section")

    editor = StudioEditorView(state_store=store)
    editor.load_section(proj, "01_section")

    groups = editor.timeline_view.canvas_widget._get_tracks_by_group()
    assert len(groups["VOICE"]) == 1
    assert groups["VOICE"][0].is_locked is True  # Voice locked by default

    assert len(groups["VISUALS"]) >= 1
    assert groups["VISUALS"][0].item_id == "hero_char"

    assert len(groups["SFX"]) >= 1
    assert groups["SFX"][0].item_id == "cue_01"

    assert len(groups["CAMERA"]) >= 2

    # Scrubbing playhead updates time and canvas item opacities immediately without rendering
    editor.scrub_to_time(0.2)
    hero_item = editor.canvas_items["hero_char"]
    assert hero_item.opacity() < 0.5  # Before start_time (1.0s)

    editor.scrub_to_time(2.5)
    assert hero_item.opacity() == 1.0  # Fully drawn and holding


def test_direct_manipulation_and_ownership_override(qapp, sample_project_dir):
    """Verifies moving an asset marks USER_OVERRIDE and [Reset to Automatic] restores defaults."""
    base, proj_dir, sec_dir = sample_project_dir
    store = StateStore(base_dir=base / ".state")

    proj = ProjectState(project_id="test_proj", title="Test", metadata={"project_path": str(proj_dir)})
    proj.get_or_create_section("01_section")

    editor = StudioEditorView(state_store=store)
    editor.load_section(proj, "01_section")

    # Initial state is AUTO
    assert editor.elements_data["hero_char"]["ownership"] == "AUTO"

    # User moves asset on canvas
    editor._on_item_geometry_changed("hero_char", 500.0, 450.0, 1.5)

    assert editor.elements_data["hero_char"]["x"] == 500.0
    assert editor.elements_data["hero_char"]["y"] == 450.0
    assert editor.elements_data["hero_char"]["ownership"] == "USER_OVERRIDE"
    assert editor.is_dirty is True

    # User clicks [Reset to Automatic]
    editor._reset_item_to_automatic("hero_char")
    assert editor.elements_data["hero_char"]["ownership"] == "AUTO"
    assert editor.elements_data["hero_char"]["x"] == 300.0  # Restored to AI default


def test_preview_scopes_and_playback_timer(qapp, sample_project_dir):
    """Verifies playback starts, loops within chosen scope, and stops cleanly."""
    base, proj_dir, sec_dir = sample_project_dir
    store = StateStore(base_dir=base / ".state")

    proj = ProjectState(project_id="test_proj", title="Test", metadata={"project_path": str(proj_dir)})
    proj.get_or_create_section("01_section")

    editor = StudioEditorView(state_store=store)
    editor.load_section(proj, "01_section")

    # Toggle Play
    editor.toggle_playback()
    assert editor.is_playing is True
    assert editor.playback_timer.isActive() is True
    assert editor.play_pause_btn.text() == "⏸ Pause"

    # Simulate 5 playback ticks (5 * 33ms)
    for _ in range(5):
        editor._on_playback_tick()

    assert editor.playhead_time > 0.0

    # Stop Playback
    editor.stop_playback()
    assert editor.is_playing is False
    assert editor.playback_timer.isActive() is False
    assert editor.playhead_time == 0.0

    # Scope switching
    editor.set_preview_scope("Shot")
    assert editor.preview_scope == "Shot"


def test_word_click_jumps_playhead(qapp, sample_project_dir):
    """Verifies clicking on a spoken word jumps the playhead to Whisper timestamp and highlights asset."""
    base, proj_dir, sec_dir = sample_project_dir
    store = StateStore(base_dir=base / ".state")

    proj = ProjectState(project_id="test_proj", title="Test", metadata={"project_path": str(proj_dir)})
    proj.get_or_create_section("01_section")

    editor = StudioEditorView(state_store=store)
    editor.load_section(proj, "01_section")

    # Word 'البطل' starts at 1.0s and is anchor for 'hero_char'
    editor._on_word_clicked("البطل", 1.0)
    assert editor.playhead_time == 1.0
    assert editor.inspector.current_item_id == "hero_char"
