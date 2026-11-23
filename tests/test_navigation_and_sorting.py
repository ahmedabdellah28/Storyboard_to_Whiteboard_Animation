"""Tests for navigation between Studio Editor, Sections Roster, and Projects Browser,
as well as latest-updated-first sorting for both Projects and Sections.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from core.state.project_state import ProjectState, SectionState
from core.state.state_store import StateStore
from studio_ui.qt import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestNavigationAndSorting:
    def test_state_store_list_all_projects_sorting(self, tmp_path):
        """Verifies that projects are sorted by updated_at descending (newest first)."""
        store = StateStore(base_dir=tmp_path)

        p1 = ProjectState(project_id="proj_old", title="Old Project")
        p1.updated_at = "2026-09-01T10:00:00+00:00"
        store.save_state(p1)
        # Manually overwrite updated_at to ensure older date for testing
        p1_file = store.get_state_file_path("proj_old")
        import json
        with open(p1_file, "r", encoding="utf-8") as f:
            d = json.load(f)
        d["updated_at"] = "2026-09-01T10:00:00+00:00"
        with open(p1_file, "w", encoding="utf-8") as f:
            json.dump(d, f)

        p2 = ProjectState(project_id="proj_new", title="New Project")
        p2.updated_at = "2026-09-30T22:00:00+00:00"
        store.save_state(p2)
        p2_file = store.get_state_file_path("proj_new")
        with open(p2_file, "r", encoding="utf-8") as f:
            d2 = json.load(f)
        d2["updated_at"] = "2026-09-30T22:00:00+00:00"
        with open(p2_file, "w", encoding="utf-8") as f:
            json.dump(d2, f)

        projects = store.list_all_projects()
        assert len(projects) == 2
        # Latest updated project should be first
        assert projects[0]["project_id"] == "proj_new"
        assert projects[1]["project_id"] == "proj_old"

    def test_sections_table_sorting_by_latest_update(self, qapp, tmp_path):
        """Verifies that sections in StudioMainWindow are sorted by updated_at descending."""
        from studio_ui.main_window import StudioMainWindow

        store = StateStore(base_dir=tmp_path)
        win = StudioMainWindow(state_store=store)

        proj = ProjectState(project_id="test_sort_proj", title="Test Sort Project")
        s1 = SectionState(section_id="sec_01", title="First Created Section", sequence_index=0)
        s1.updated_at = "2026-09-10T12:00:00+00:00"

        s2 = SectionState(section_id="sec_02", title="Recently Updated Section", sequence_index=1)
        s2.updated_at = "2026-09-30T23:00:00+00:00"

        s3 = SectionState(section_id="sec_03", title="Middle Section", sequence_index=2)
        s3.updated_at = "2026-09-20T15:00:00+00:00"

        proj.sections = {"sec_01": s1, "sec_02": s2, "sec_03": s3}
        win.load_project(proj)

        # Roster should have 3 rows
        assert win.sections_table.rowCount() == 3
        # Row 0 should be sec_02 (newest)
        assert win.sections_table.item(0, 1).text() == "sec_02"
        # Row 1 should be sec_03 (middle)
        assert win.sections_table.item(1, 1).text() == "sec_03"
        # Row 2 should be sec_01 (oldest)
        assert win.sections_table.item(2, 1).text() == "sec_01"

        win.close()

    def test_studio_editor_navigation_buttons(self, qapp, tmp_path):
        """Verifies navigation signals and return functionality from Studio Editor."""
        from studio_ui.main_window import StudioMainWindow

        store = StateStore(base_dir=tmp_path)
        win = StudioMainWindow(state_store=store)

        proj = ProjectState(project_id="nav_proj", title="Nav Project")
        s1 = SectionState(section_id="sec_nav", title="Nav Section")
        proj.sections = {"sec_nav": s1}
        win.load_project(proj)

        # Open Studio Editor (Page 3)
        win._open_studio_editor("sec_nav")
        assert win.stacked_widget.currentIndex() == 3

        # Click Back to Sections
        win.studio_editor.back_btn.click()
        assert win.stacked_widget.currentIndex() == 1  # Workspace

        # Open Studio Editor again
        win._open_studio_editor("sec_nav")
        assert win.stacked_widget.currentIndex() == 3

        # Click Back to Projects
        win.studio_editor.back_to_projects_btn.click()
        assert win.stacked_widget.currentIndex() == 0  # Project Browser
        assert win.current_project is None

        win.close()
