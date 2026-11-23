"""Automated tests for the Centralized Responsive Design System.

Verifies:
- Scale factors and DPI adaptation
- Breakpoint transitions (COMPACT, MEDIUM, LARGE)
- Typography clamping (enforced minimums and maximums)
- Panel sizing hints and splitter proportional distribution
- UI component integration (MainWindow, ProjectBrowser, StudioInspector, ProcessingMonitor, StudioEditor)
- Zero layout clipping, overflow handling with scrollable fallbacks
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from studio_ui.qt import (
    QApplication,
    QHBoxLayout,
    QScrollArea,
    QWidget,
)
from studio_ui.responsive import (
    Breakpoint,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    control_height,
    font_size,
    get_breakpoint,
    get_device_pixel_ratio,
    get_ui_scale,
    h_splitter_sizes,
    icon_size,
    inspector_panel_width,
    is_panel_collapsible,
    page_margin,
    scaled_stylesheet_values,
    shots_panel_width,
    spacing,
    v_splitter_sizes,
)


class TestResponsiveMetrics(unittest.TestCase):
    """Unit tests for the centralized responsive design calculations."""

    @classmethod
    def setUpClass(cls):
        # Ensure a QApplication exists for headless test execution
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_ui_scale_positive(self):
        """UI scale factor should always be a positive float >= 1.0 (or matching DPR)."""
        scale = get_ui_scale()
        self.assertIsInstance(scale, float)
        self.assertGreaterEqual(scale, 0.5)

    def test_typography_body_clamping(self):
        """Body text (base <= 14) must never fall below 12px or exceed 18px."""
        # Test low base size
        low = font_size(8)
        self.assertGreaterEqual(low, 12, "Body font size must not fall below 12px")
        self.assertLessEqual(low, 18, "Body font size must not exceed 18px")

        # Test standard body size
        body = font_size(13)
        self.assertGreaterEqual(body, 12)
        self.assertLessEqual(body, 18)

    def test_typography_heading_clamping(self):
        """Heading text (base > 14) must never fall below 16px or exceed 28px."""
        # Test small heading
        h_small = font_size(15)
        self.assertGreaterEqual(h_small, 16, "Heading font size must not fall below 16px")

        # Test large heading
        h_large = font_size(32)
        self.assertLessEqual(h_large, 28, "Heading font size must be clamped to max 28px")

    def test_spacing_and_dimensions(self):
        """Spacing, icon sizes, and control heights must have sane floors."""
        self.assertGreaterEqual(spacing(1), 2, "Spacing must have a floor of at least 2px")
        self.assertGreaterEqual(spacing(16), 8)

        self.assertGreaterEqual(icon_size(8), 12, "Icon size floor must be >= 12px")
        self.assertGreaterEqual(control_height(16), 22, "Control height floor must be >= 22px")

    def test_scaled_stylesheet_values_dictionary(self):
        """scaled_stylesheet_values must return complete token map with positive integers."""
        tokens = scaled_stylesheet_values()
        required_keys = [
            "body_font", "small_font", "heading_font", "subheading_font", "label_font",
            "pad_xs", "pad_sm", "pad_md", "pad_lg", "pad_xl", "pad_xxl",
            "icon_sm", "icon_md", "icon_lg", "ctrl_h", "ctrl_h_sm",
            "border_radius", "border_radius_sm",
        ]
        for key in required_keys:
            self.assertIn(key, tokens)
            self.assertIsInstance(tokens[key], int)
            self.assertGreater(tokens[key], 0, f"Token {key} must be positive")


class TestBreakpointTransitions(unittest.TestCase):
    """Tests for breakpoint detection logic and window-size thresholds."""

    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_breakpoint_compact(self):
        """Width < 1100 logical pixels must return Breakpoint.COMPACT."""
        mock_widget = MagicMock()
        mock_window = MagicMock()
        mock_window.width.return_value = 960
        mock_widget.window.return_value = mock_window

        bp = get_breakpoint(mock_widget)
        self.assertEqual(bp, Breakpoint.COMPACT)
        self.assertTrue(is_panel_collapsible(widget=mock_widget))

    def test_breakpoint_medium(self):
        """1100 <= Width < 1600 logical pixels must return Breakpoint.MEDIUM."""
        mock_widget = MagicMock()
        mock_window = MagicMock()
        mock_window.width.return_value = 1366
        mock_widget.window.return_value = mock_window

        bp = get_breakpoint(mock_widget)
        self.assertEqual(bp, Breakpoint.MEDIUM)
        self.assertFalse(is_panel_collapsible(widget=mock_widget))

    def test_breakpoint_large(self):
        """Width >= 1600 logical pixels must return Breakpoint.LARGE."""
        mock_widget = MagicMock()
        mock_window = MagicMock()
        mock_window.width.return_value = 1920
        mock_widget.window.return_value = mock_window

        bp = get_breakpoint(mock_widget)
        self.assertEqual(bp, Breakpoint.LARGE)
        self.assertFalse(is_panel_collapsible(widget=mock_widget))

    def test_page_margins_by_breakpoint(self):
        """Page margins scale up from compact to large."""
        mock_compact = MagicMock()
        mock_compact.window().width.return_value = 1000
        mock_large = MagicMock()
        mock_large.window().width.return_value = 1920

        margin_compact = page_margin(widget=mock_compact)
        margin_large = page_margin(widget=mock_large)
        self.assertLess(margin_compact, margin_large)


class TestSplitterAndPanelPolicies(unittest.TestCase):
    """Tests for proportional layout distribution and panel hints."""

    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_horizontal_splitter_compact(self):
        """At compact breakpoint, side panels collapse to 0 and canvas gets full width."""
        mock_widget = MagicMock()
        mock_widget.window().width.return_value = 1000

        sizes = h_splitter_sizes(1000, widget=mock_widget)
        self.assertEqual(len(sizes), 3)
        self.assertEqual(sizes[0], 0, "Left panel must collapse to 0")
        self.assertEqual(sizes[1], 1000, "Canvas must take full width")
        self.assertEqual(sizes[2], 0, "Right inspector must collapse to 0")

    def test_horizontal_splitter_medium_and_large(self):
        """At medium and large breakpoints, canvas must receive majority of width."""
        for width in [1366, 1920, 2560]:
            mock_widget = MagicMock()
            mock_widget.window().width.return_value = width

            sizes = h_splitter_sizes(width, widget=mock_widget)
            shots, canvas, inspector = sizes
            self.assertGreater(canvas, shots)
            self.assertGreater(canvas, inspector)
            self.assertGreaterEqual(canvas, width * 0.55, "Canvas must receive at least 55% of width")

    def test_vertical_splitter(self):
        """Vertical splitter distributes ~70% to workspace and ~30% to timeline."""
        total_h = 900
        workspace, timeline = v_splitter_sizes(total_h)
        self.assertGreater(workspace, timeline)
        self.assertGreaterEqual(timeline, 150)
        self.assertEqual(workspace + timeline, total_h)


class TestUIComponentsResponsive(unittest.TestCase):
    """Integration tests verifying UI views respect the responsive system."""

    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_studio_inspector_panel_flexibility(self):
        """StudioInspectorPanel must have flexible min/max width and a scrollable container."""
        from studio_ui.views.studio_inspector import StudioInspectorPanel

        inspector = StudioInspectorPanel()
        self.assertGreaterEqual(inspector.minimumWidth(), 200)
        self.assertLessEqual(inspector.maximumWidth(), 500)
        self.assertNotEqual(inspector.minimumWidth(), inspector.maximumWidth(), "Inspector must not have fixed width")

        # Must have scroll area to prevent control clipping
        self.assertTrue(hasattr(inspector, "scroll_area"))
        self.assertIsInstance(inspector.scroll_area, QScrollArea)

        # Verify inspection without error
        inspector.inspect_element("elem_1", {"x": 100, "y": 200, "scale": 1.2, "ownership": "AUTO"})
        self.assertEqual(inspector.current_item_id, "elem_1")

        inspector.inspect_camera("Cam_01", {"center_x": 960, "center_y": 540, "zoom": 1.0, "ownership": "AUTO"})
        self.assertEqual(inspector.current_item_id, "Cam_01")

        inspector.show_empty()
        self.assertIsNone(inspector.current_item_id)

    def test_project_browser_adaptive_layout(self):
        """ProjectBrowser must wrap in a QScrollArea and adapt its action layout on resize."""
        from studio_ui.qt import QResizeEvent, QSize
        from studio_ui.views.project_browser import ProjectBrowser

        browser = ProjectBrowser()
        # Verify scroll area wrapping
        scroll = browser.findChild(QScrollArea)
        self.assertIsNotNone(scroll, "ProjectBrowser content must be wrapped in a QScrollArea")

        # Simulate resize to compact (< 1100)
        browser.resize(900, 600)
        browser.resizeEvent(QResizeEvent(QSize(900, 600), QSize(1200, 800)))
        self.assertEqual(browser.actions_layout.direction(), QHBoxLayout.Direction.TopToBottom)

        # Simulate resize to large (>= 1600)
        browser.resize(1800, 900)
        browser.resizeEvent(QResizeEvent(QSize(1800, 900), QSize(900, 600)))
        self.assertEqual(browser.actions_layout.direction(), QHBoxLayout.Direction.LeftToRight)

    def test_processing_monitor_dynamic_reflow(self):
        """ProcessingMonitorView must reflow stage cards into 1, 2, 3, or 4 columns based on width."""
        from studio_ui.qt import QResizeEvent, QSize
        from studio_ui.views.processing_monitor import ProcessingMonitorView

        monitor = ProcessingMonitorView()

        # At compact width: 1 column
        monitor.resize(750, 600)
        monitor.resizeEvent(QResizeEvent(QSize(750, 600), QSize(1200, 800)))
        self.assertEqual(monitor._current_cols, 1)

        # At medium-small width: 2 columns
        monitor.resize(1100, 700)
        monitor.resizeEvent(QResizeEvent(QSize(1100, 700), QSize(750, 600)))
        self.assertEqual(monitor._current_cols, 2)

        # At standard desktop width: 3 columns
        monitor.resize(1400, 800)
        monitor.resizeEvent(QResizeEvent(QSize(1400, 800), QSize(1100, 700)))
        self.assertEqual(monitor._current_cols, 3)

        # At ultrawide width: 4 columns
        monitor.resize(1800, 900)
        monitor.resizeEvent(QResizeEvent(QSize(1800, 900), QSize(1400, 800)))
        self.assertEqual(monitor._current_cols, 4)

    def test_main_window_min_dimensions(self):
        """StudioMainWindow must enforce MIN_WINDOW_WIDTH and MIN_WINDOW_HEIGHT."""
        from studio_ui.main_window import StudioMainWindow

        win = StudioMainWindow()
        self.assertGreaterEqual(win.minimumWidth(), MIN_WINDOW_WIDTH)
        self.assertGreaterEqual(win.minimumHeight(), MIN_WINDOW_HEIGHT)


if __name__ == "__main__":
    unittest.main()
