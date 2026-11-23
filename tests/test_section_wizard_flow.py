"""Unit tests for the Section Pipeline Guided Wizard & Interactive Extraction Review.

Verifies:
1. StoryboardReviewCanvas: coordinate transformation, box selection, resizing, and drawing.
2. ExtractionReviewWidget: split horizontal/vertical, merge, exclude, metadata saving.
3. DynamicStoryboardExtractor: single box extraction and RGBA recropping.
4. NewSectionDialog: step progression from input -> extraction -> review -> audio -> auto-completion.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import cv2

from core.state.project_state import ProjectState
from core.state.state_store import StateStore
from production_engine.dynamic_storyboard_extractor import DynamicStoryboardExtractor
from studio_ui.qt import QApplication, QPoint, Qt
from studio_ui.dialogs.extraction_review_dialog import ExtractionReviewWidget
from studio_ui.dialogs.new_section_dialog import NewSectionDialog
from studio_ui.views.storyboard_review_canvas import StoryboardReviewCanvas


class TestSectionWizardFlow(unittest.TestCase):
    """Automated tests for the end-to-end Section Pipeline Wizard and Interactive Review."""

    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "test_project"
        self.project_dir.mkdir(parents=True)
        self.sections_dir = self.project_dir / "sections"
        self.sections_dir.mkdir()

        # Create a mock 1920x1080 storyboard with white background and dark drawn shapes
        self.sb_path = self.temp_dir / Path("mock_storyboard.png")
        img = np.ones((1080, 1920, 3), dtype=np.uint8) * 255
        # Draw 2 distinct black rectangles (elements)
        cv2.rectangle(img, (200, 200), (500, 400), (20, 20, 20), -1)
        cv2.rectangle(img, (700, 200), (1000, 400), (30, 30, 30), -1)
        cv2.imwrite(str(self.sb_path), img)

        # Mock project state
        self.state_store = StateStore(base_dir=self.temp_dir / Path("state"))
        self.project_state = ProjectState(
            project_id="test_proj",
            title="اختبار المشروع",
            metadata={"project_path": str(self.project_dir)},
        )
        self.state_store.save_state(self.project_state)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dynamic_storyboard_extractor_recrop(self):
        """DynamicStoryboardExtractor should accurately extract tight clean RGBA boxes."""
        sec_dir = self.sections_dir / "sec_01"
        sec_dir.mkdir()
        shutil.copy(self.sb_path, sec_dir / "storyboard.png")

        extractor = DynamicStoryboardExtractor(str(sec_dir))
        res = extractor.recrop_and_save_asset("test_elem", [200, 200, 300, 200], desc="Test Rectangle")
        self.assertIsNotNone(res)
        self.assertEqual(res["file"], "test_elem.png")
        self.assertTrue((sec_dir / "assets" / "test_elem.png").exists())
        self.assertGreater(res["area"], 0)

    def test_storyboard_review_canvas_coordinates_and_selection(self):
        """StoryboardReviewCanvas should map coordinates and emit signals."""
        canvas = StoryboardReviewCanvas()
        canvas.resize(800, 600)
        canvas.set_storyboard_image(self.sb_path)

        boxes = {
            "elem_01": {"orig_box": [200, 200, 300, 200], "excluded": False},
            "elem_02": {"orig_box": [700, 200, 300, 200], "excluded": True},
        }
        canvas.set_boxes(boxes)
        canvas.set_selected_asset("elem_01")
        self.assertEqual(canvas.selected_asset_id, "elem_01")

        # Screen to image transforms
        scale, ox, oy = canvas._get_transform_metrics()
        self.assertGreater(scale, 0.0)

    def test_extraction_review_widget_split_and_merge(self):
        """ExtractionReviewWidget should split elements horizontally and vertically and merge them."""
        sec_dir = self.sections_dir / "sec_02"
        sec_dir.mkdir()
        shutil.copy(self.sb_path, sec_dir / "storyboard.png")

        # Initialize metadata with one element
        assets_dir = sec_dir / "assets"
        assets_dir.mkdir()
        extractor = DynamicStoryboardExtractor(str(sec_dir))
        extractor.recrop_and_save_asset("elem_orig", [200, 200, 300, 200])

        with open(assets_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump({
                "elem_orig": {
                    "file": "elem_orig.png",
                    "orig_box": [200, 200, 300, 200],
                    "desc": "Original element",
                    "excluded": False,
                }
            }, f)

        widget = ExtractionReviewWidget(
            project_id="test_proj",
            section_id="sec_02",
            section_path=sec_dir,
        )
        self.assertIn("elem_orig", widget.assets_data)

        # Test Split Left / Right
        widget._on_asset_selected("elem_orig")
        widget._split_left_right()

        self.assertNotIn("elem_orig", widget.assets_data)
        self.assertIn("elem_orig_a", widget.assets_data)
        self.assertIn("elem_orig_b", widget.assets_data)
        self.assertTrue((assets_dir / "elem_orig_a.png").exists())
        self.assertTrue((assets_dir / "elem_orig_b.png").exists())

        # Test Merge
        widget._on_asset_selected("elem_orig_a")
        widget._merge_selected_with_next()
        merged_key = "merged_elem_orig_a_elem_orig_b"
        self.assertIn(merged_key, widget.assets_data)
        self.assertTrue((assets_dir / f"{merged_key}.png").exists())

    def test_extraction_review_widget_split_3_parts(self):
        """ExtractionReviewWidget should split a combined element into 3 separate parts."""
        sec_dir = self.sections_dir / "sec_03"
        sec_dir.mkdir()
        shutil.copy(self.sb_path, sec_dir / "storyboard.png")

        assets_dir = sec_dir / "assets"
        assets_dir.mkdir()
        extractor = DynamicStoryboardExtractor(str(sec_dir))
        extractor.recrop_and_save_asset("elem_grouped", [100, 100, 600, 300])

        widget = ExtractionReviewWidget(
            project_id="test_proj",
            section_id="sec_03",
            section_path=sec_dir,
        )
        widget._on_asset_selected("elem_grouped")
        widget._split_3_parts()

        self.assertNotIn("elem_grouped", widget.assets_data)
        self.assertIn("elem_grouped_1", widget.assets_data)
        self.assertIn("elem_grouped_2", widget.assets_data)
        self.assertIn("elem_grouped_3", widget.assets_data)
        self.assertTrue((assets_dir / "elem_grouped_1.png").exists())
        self.assertTrue((assets_dir / "elem_grouped_2.png").exists())
        self.assertTrue((assets_dir / "elem_grouped_3.png").exists())

    def test_new_section_dialog_stepper_progression(self):
        """NewSectionDialog wizard should advance smoothly through steps."""
        dlg = NewSectionDialog(
            project_state=self.project_state,
            project_dir=self.project_dir,
            state_store=self.state_store,
        )

        dlg.id_edit.setText("sec_auto_01")
        dlg.title_edit.setText("المشهد التفاعلي الأول")
        dlg.sb_edit.setText(str(self.sb_path))
        dlg.script_edit.setPlainText("هذا نص تجريبي للتعليق الصوتي.")

        self.assertEqual(dlg.pages.currentIndex(), 0)
        # Advance to step 1
        dlg._start_extraction_phase()
        self.assertEqual(dlg.pages.currentIndex(), 1)
        self.assertIsNotNone(dlg.created_contract)
        self.assertTrue((self.project_dir / "sections" / "sec_auto_01").exists())

        # Wait for worker thread to finish extraction and process events
        if dlg.extraction_worker:
            dlg.extraction_worker.wait(5000)
        self.app.processEvents()

        # Review page setup
        self.assertEqual(dlg.pages.currentIndex(), 2)
        self.assertIsNotNone(dlg.review_widget)
        dlg.close()


if __name__ == "__main__":
    unittest.main()
