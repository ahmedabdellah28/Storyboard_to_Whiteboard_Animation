"""Unit and integration test suite for Phase 5: PySide6 Application Shell & Project Browser.

Verifies:
1. Qt binding initialization and offscreen headless support.
2. NewProjectDialog configuration, directory bootstrap, and StateStore persistence.
3. NewSectionDialog input preflight, storyboard copy, and section registration.
4. ProjectBrowser launcher view, recent project recording, and double-click signals.
5. StudioMainWindow workspace switching (ProjectBrowser <-> Workspace Shell) and status bar badges.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
import pytest

# Ensure headless offscreen platform for automated test runs
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from core.contracts.studio_contracts import SectionInputContract
from core.state.project_state import ProjectState
from core.state.state_store import StateStore
from studio_ui.dialogs.new_project_dialog import NewProjectDialog
from studio_ui.dialogs.new_section_dialog import NewSectionDialog
from studio_ui.main_window import StudioMainWindow
from studio_ui.qt import QApplication, QT_BINDING
from studio_ui.views.project_browser import ProjectBrowser


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single global QApplication instance exists for offscreen tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ============================================================================
# 1. QT BINDING & ENVIRONMENT
# ============================================================================

def test_qt_binding_available(qapp):
    assert QT_BINDING in ("PySide6", "PyQt6")
    assert qapp is not None


# ============================================================================
# 2. NEW PROJECT DIALOG
# ============================================================================

def test_new_project_dialog_creation(qapp):
    with tempfile.TemporaryDirectory() as td:
        s_store = StateStore(base_dir=Path(td) / "state")

        dlg = NewProjectDialog(state_store=s_store)
        dlg.id_edit.setText("test_documentary_01")
        dlg.title_edit.setText("وثائقي اختبار 01")
        dlg.dir_edit.setText(td)

        dlg._on_accept()

        assert dlg.created_project_state is not None
        assert dlg.created_project_state.project_id == "test_documentary_01"
        assert dlg.created_project_state.title == "وثائقي اختبار 01"
        assert dlg.created_project_state.schema_version == 2

        # Check directories created on disk
        p_dir = Path(td) / "test_documentary_01"
        assert (p_dir / "sections").is_dir()
        assert (p_dir / "deliverables").is_dir()


# ============================================================================
# 3. NEW SECTION DIALOG
# ============================================================================

def test_new_section_dialog_creation_and_preflight(qapp):
    with tempfile.TemporaryDirectory() as td:
        s_store = StateStore(base_dir=Path(td) / "state")
        proj_dir = Path(td) / "my_project"
        proj_dir.mkdir(parents=True, exist_ok=True)

        proj_state = ProjectState(
            project_id="my_project",
            title="My Test Project",
            metadata={"project_path": str(proj_dir)},
        )
        s_store.save_state(proj_state)

        # Create dummy storyboard PNG
        sb_file = Path(td) / "sample_storyboard.png"
        sb_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 2048)

        dlg = NewSectionDialog(
            project_state=proj_state,
            project_dir=proj_dir,
            state_store=s_store,
        )

        dlg.id_edit.setText("01_intro")
        dlg.title_edit.setText("مقدمة الفيديو")
        dlg.sb_edit.setText(str(sb_file))
        dlg.script_edit.setPlainText("هذا نص توضيحي للسكريبت من أجل اختبار إضافة السكشن.")

        dlg._on_accept()

        assert dlg.created_contract is not None
        assert dlg.created_contract.section_id == "01_intro"
        assert dlg.created_section_state is not None

        # Verify section files were deployed to disk
        sec_dir = proj_dir / "sections" / "01_intro"
        assert sec_dir.is_dir()
        assert (sec_dir / "storyboard.png").is_file()
        assert (sec_dir / "script.txt").is_file()
        assert (sec_dir / "script.txt").read_text(encoding="utf-8").startswith("هذا نص")


# ============================================================================
# 4. PROJECT BROWSER
# ============================================================================

def test_project_browser_recent_loading_and_signal(qapp):
    with tempfile.TemporaryDirectory() as td:
        s_store = StateStore(base_dir=Path(td) / "state")
        browser = ProjectBrowser(state_store=s_store)

        # Record a project in recents
        p_state = s_store.load_state("proj_recent_01")
        p_state.title = "Recent Project 01"
        s_store.save_state(p_state)

        browser._record_recent("proj_recent_01", "Recent Project 01", td)

        # Check recents list item
        assert browser.recents_list.count() >= 1

        opened_projects = []
        browser.project_opened.connect(lambda p: opened_projects.append(p))

        # Select and open
        first_item = browser.recents_list.item(0)
        browser._on_recent_double_clicked(first_item)

        assert len(opened_projects) == 1
        assert opened_projects[0].project_id == "proj_recent_01"


# ============================================================================
# 5. STUDIO MAIN WINDOW SHELL
# ============================================================================

def test_studio_main_window_lifecycle_and_switching(qapp):
    with tempfile.TemporaryDirectory() as td:
        s_store = StateStore(base_dir=Path(td) / "state")
        win = StudioMainWindow(state_store=s_store)

        # Initial view is ProjectBrowser (index 0)
        assert win.stacked_widget.currentIndex() == 0
        assert win.current_project is None
        assert win.save_proj_action.isEnabled() is False

        # Load project
        proj = ProjectState(project_id="studio_proj_01", title="Studio Test Project")
        proj.get_or_create_section("01_sec", title="Section 1", sequence_index=0)
        s_store.save_state(proj)

        win.load_project(proj)

        # Switched to Workspace (index 1)
        assert win.stacked_widget.currentIndex() == 1
        assert win.current_project is not None
        assert win.save_proj_action.isEnabled() is True
        assert win.sections_table.rowCount() == 1
        assert "Studio Test Project" in win.windowTitle()

        # Status bar badges
        assert "[Profile:" in win.profile_badge.text()
        assert "[Encoder:" in win.encoder_badge.text()

        # Close project
        win.close_project()
        assert win.stacked_widget.currentIndex() == 0
        assert win.current_project is None
