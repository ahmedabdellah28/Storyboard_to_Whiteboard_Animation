"""Phase 8 & 9 Test Suite: Interactive 1080p Studio Canvas & Timeline View.

Validates:
1. StudioCanvasScene 1920x1080 coordinate system and item interactions.
2. CanvasElementItem, CanvasTextItem, and CameraFrustumItem geometry manipulation.
3. Multi-track StudioTimelineView, playhead scrubbing, and track timing adjustments.
4. Contextual StudioInspectorPanel dynamic property editing.
5. Unified StudioEditorView end-to-end data loading, canvas-timeline sync, and selective layout persistence.
6. StudioMainWindow navigation into Page 3 (Studio Canvas Editor).
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest
from core.state.project_state import ProjectState, SectionState
from core.state.state_store import StateStore
from studio_ui.main_window import StudioMainWindow
from studio_ui.qt import QApplication, QPixmap, QRectF
from studio_ui.views.studio_canvas import (
    CameraFrustumItem,
    CanvasElementItem,
    CanvasTextItem,
    StudioCanvasScene,
    StudioCanvasView,
)
from studio_ui.views.studio_editor import StudioEditorView
from studio_ui.views.studio_inspector import StudioInspectorPanel
from studio_ui.views.studio_timeline import StudioTimelineView, TimelineTrackItem


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
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        base = Path(tmpdir)
        state_dir = base / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)

        proj_dir = base / "test_editor_project"
        sec_dir = proj_dir / "sections" / "01_section"
        (sec_dir / "assets").mkdir(parents=True, exist_ok=True)
        (sec_dir / "timing").mkdir(parents=True, exist_ok=True)

        # Mock asset image
        img_path = sec_dir / "assets" / "asset_character.png"
        pix = QPixmap(100, 100)
        pix.fill()
        pix.save(str(img_path))

        # Mock metadata
        meta = {
            "assets": {
                "asset_character": {
                    "id": "asset_character",
                    "file": "asset_character.png",
                    "bbox": [50, 50, 200, 300],
                    "label": "Character",
                }
            }
        }
        (sec_dir / "assets" / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")

        # Mock layout
        layout = {
            "placed_elements": [
                {
                    "id": "asset_character",
                    "x": 200,
                    "y": 150,
                    "scale": 1.2,
                    "animation_style": "Outside-In Pen",
                    "draw_duration": 1.0,
                    "hold_duration": 3.0,
                    "anchor_word": "الشخصية",
                }
            ],
            "cameras": [
                {"name": "Camera 01", "center_x": 960, "center_y": 540, "zoom": 1.0}
            ],
        }
        (sec_dir / "placed_elements_layout.json").write_text(json.dumps(layout), encoding="utf-8")

        yield base, proj_dir, sec_dir


def test_studio_canvas_scene_and_items(qapp):
    """Verify 1920x1080 scene coordinate space and item addition."""
    scene = StudioCanvasScene()
    assert scene.width() == 1920
    assert scene.height() == 1080

    # Add element item
    pix = QPixmap(100, 80)
    elem = CanvasElementItem("item_01", pix, initial_x=300, initial_y=200, scale_factor=1.5)
    scene.addItem(elem)

    assert elem.x() == 300
    assert elem.y() == 200
    assert elem.scale() == 1.5
    assert elem.element_id == "item_01"

    # Add camera frustum item
    cam = CameraFrustumItem(camera_name="Camera 01")
    scene.addItem(cam)
    assert cam.camera_name == "Camera 01"
    assert cam.zValue() == 100

    # Add text overlay item
    txt = CanvasTextItem("txt_01", "عنوان تجريبي", initial_x=400, initial_y=100)
    scene.addItem(txt)
    assert txt.toPlainText() == "عنوان تجريبي"

    # Verify painting of selected item with corner handles does not raise TypeError
    from studio_ui.qt import QImage, QPainter
    elem.setSelected(True)
    test_img = QImage(1920, 1080, QImage.Format.Format_ARGB32)
    painter = QPainter(test_img)
    scene.render(painter)
    painter.end()


def test_studio_canvas_view_zoom_and_fit(qapp):
    """Verify view zoom actions and 1080p fit functionality."""
    scene = StudioCanvasScene()
    view = StudioCanvasView(scene)

    view.fit_1080p()
    t_initial = view.transform()

    view.zoom_in()
    t_zoomed = view.transform()
    assert t_zoomed.m11() > t_initial.m11()

    view.zoom_out()
    view.reset_zoom()
    t_reset = view.transform()
    assert t_reset.isIdentity()


def test_studio_timeline_tracks_and_scrubbing(qapp):
    """Verify multi-track sequencer display, time scrubbing, and item duration handling."""
    timeline = StudioTimelineView()
    timeline.set_duration(45.0)

    tracks = [
        TimelineTrackItem("voice_main", "Voiceover Narration", start_time=0.0, duration=42.0, track_type="voice", color_hex="#22c55e"),
        TimelineTrackItem("asset_sword", "Sword Element", start_time=4.5, duration=3.0, track_type="element", color_hex="#38bdf8"),
    ]
    timeline.set_tracks(tracks)

    scrubbed_times = []
    timeline.time_scrubbed.connect(lambda t: scrubbed_times.append(t))

    # Scrub timeline to 12.5 seconds
    timeline.canvas_widget._scrub_to_x(12.5 * timeline.canvas_widget.PIXELS_PER_SECOND)

    assert len(scrubbed_times) == 1
    assert scrubbed_times[0] == pytest.approx(12.5, 0.1)
    assert "12.50" in timeline.timecode_label.text()


def test_studio_inspector_element_property_editing(qapp):
    """Verify inspector panel updates element properties and fires change signals."""
    inspector = StudioInspectorPanel()

    elem_data = {
        "x": 250,
        "y": 180,
        "scale": 1.25,
        "animation_style": "Contour Stroke Draw",
        "draw_duration": 1.2,
        "hold_duration": 4.0,
        "anchor_word": "سيف",
    }
    inspector.inspect_element("asset_sword", elem_data)

    assert inspector.name_edit.text() == "asset_sword"
    assert inspector.pos_x_spin.value() == 250
    assert inspector.pos_y_spin.value() == 180
    assert inspector.scale_spin.value() == pytest.approx(1.25, 0.01)

    changes = []
    inspector.property_changed.connect(lambda iid, prop, val: changes.append((iid, prop, val)))

    # Change scale
    inspector.scale_spin.setValue(1.50)
    assert ("asset_sword", "scale", 1.50) in changes

    # Change animation style
    inspector.anim_combo.setCurrentText("Outside-In Pen")
    assert ("asset_sword", "animation_style", "Outside-In Pen") in changes


def test_studio_editor_data_loading_and_saving(qapp, temp_workspace):
    """Verify StudioEditorView loads layout from disk and persists updates with revision bumps."""
    base, proj_dir, sec_dir = temp_workspace
    store = StateStore(base_dir=base / ".state")

    project = ProjectState(
        project_id="p_editor_test",
        title="Editor Test Project",
        metadata={"project_path": str(proj_dir)},
    )
    sec = project.get_or_create_section("01_section")
    store.save_state(project)

    editor = StudioEditorView(state_store=store)
    editor.load_section(project, "01_section")

    assert "asset_character" in editor.elements_data
    assert "asset_character" in editor.canvas_items
    assert "Camera 01" in editor.cameras_data

    # Modify item position on canvas
    item = editor.canvas_items["asset_character"]
    item.setPos(350, 220)
    editor._on_item_geometry_changed("asset_character", 350, 220, 1.2)

    assert editor.elements_data["asset_character"]["x"] == 350.0
    assert editor.elements_data["asset_character"]["y"] == 220.0

    # Save layout
    initial_rev = sec.revision_id
    editor.save_layout()

    # Verify disk persistence
    layout_file = sec_dir / "placed_elements_layout.json"
    assert layout_file.exists()
    with open(layout_file, "r", encoding="utf-8") as f:
        saved_layout = json.load(f)
    saved_elem = [e for e in saved_layout["placed_elements"] if e["id"] == "asset_character"][0]
    assert saved_elem["x"] == 350.0

    # Verify revision was incremented
    updated_state = store.load_state("p_editor_test")
    assert updated_state.sections["01_section"].revision_id == initial_rev + 1


def test_main_window_switching_to_studio_editor(qapp, temp_workspace):
    """Verify StudioMainWindow transitions seamlessly into Page 3 (Studio Canvas Editor)."""
    base, proj_dir, sec_dir = temp_workspace
    store = StateStore(base_dir=base / ".state")
    window = StudioMainWindow(state_store=store)

    project = ProjectState(
        project_id="p_nav_editor",
        title="Nav Editor Test",
        metadata={"project_path": str(proj_dir)},
    )
    project.get_or_create_section("01_section")
    store.save_state(project)

    window.load_project(project)
    assert window.stacked_widget.currentIndex() == 1  # Workspace

    # Open Studio Editor -> Page 3
    window._open_studio_editor("01_section")
    assert window.stacked_widget.currentIndex() == 3
    assert window.studio_editor.active_section_id == "01_section"

    # Switch back to workspace -> Page 1
    window.studio_editor.back_btn.click()
    assert window.stacked_widget.currentIndex() == 1
