"""Centralized responsive metrics for the Whiteboard Studio Qt Widgets UI.

The UI uses Qt logical pixels. Qt 6/Windows High-DPI is responsible for mapping
logical pixels to physical pixels. This module therefore intentionally does
NOT multiply normal layout dimensions by devicePixelRatio; doing so would
cause double scaling at 125%/150%/200% Windows display scaling.
"""
from __future__ import annotations

import enum
from typing import Optional

from studio_ui.qt import QApplication, QWidget


class Breakpoint(enum.Enum):
    COMPACT = "compact"       # < 1100 logical px
    MEDIUM = "medium"         # 1100–1599 logical px
    LARGE = "large"            # >= 1600 logical px


COMPACT_MAX_WIDTH = 1100
MEDIUM_MAX_WIDTH = 1600
MIN_WINDOW_WIDTH = 960
MIN_WINDOW_HEIGHT = 640

# Approved design-system sizing in Qt logical pixels.
_MIN_BODY_FONT_PX = 12
_MAX_BODY_FONT_PX = 16
_MIN_HEADING_FONT_PX = 16
_MAX_HEADING_FONT_PX = 28


def screen_for(widget: Optional[QWidget] = None):
    """Return the screen associated with *widget/window* when possible."""
    app = QApplication.instance()
    if app is None:
        return None

    try:
        if widget is not None:
            window = widget.window()
            if window is not None:
                handle = window.windowHandle()
                if handle is not None and handle.screen() is not None:
                    return handle.screen()
                center = window.frameGeometry().center()
                screen = app.screenAt(center)
                if screen is not None:
                    return screen

        active = app.activeWindow()
        if active is not None:
            handle = active.windowHandle()
            if handle is not None and handle.screen() is not None:
                return handle.screen()

        return app.primaryScreen()
    except Exception:
        return None


def get_device_pixel_ratio(widget: Optional[QWidget] = None) -> float:
    """Return DPR of the relevant screen for diagnostics only.

    Layout sizes must NOT be multiplied by this value; Qt already performs
    logical-to-physical scaling.
    """
    screen = screen_for(widget)
    if screen is None:
        return 1.0
    try:
        return float(screen.devicePixelRatio())
    except Exception:
        return 1.0


def _get_logical_width(widget: Optional[QWidget] = None) -> int:
    if widget is not None:
        try:
            window = widget.window()
            if window is not None and window.width() > 0:
                return int(window.width())
        except Exception:
            pass

    app = QApplication.instance()
    if app is not None:
        try:
            screen = screen_for(widget)
            if screen is not None:
                return int(screen.availableGeometry().width())
        except Exception:
            pass
    return 1280


def _get_logical_height(widget: Optional[QWidget] = None) -> int:
    if widget is not None:
        try:
            window = widget.window()
            if window is not None and window.height() > 0:
                return int(window.height())
        except Exception:
            pass

    screen = screen_for(widget)
    if screen is not None:
        try:
            return int(screen.availableGeometry().height())
        except Exception:
            pass
    return 800


def get_breakpoint(widget: Optional[QWidget] = None) -> Breakpoint:
    width = _get_logical_width(widget)
    if width < COMPACT_MAX_WIDTH:
        return Breakpoint.COMPACT
    if width < MEDIUM_MAX_WIDTH:
        return Breakpoint.MEDIUM
    return Breakpoint.LARGE


def get_ui_scale(widget: Optional[QWidget] = None) -> float:
    """Return a restrained *layout/font tier* scale based on logical width.

    This is intentionally independent from display DPR. It only makes the
    visual hierarchy slightly tighter/looser across compact/medium/large
    windows while preserving readable minimum sizes.
    """
    bp = get_breakpoint(widget)
    return {
        Breakpoint.COMPACT: 0.92,
        Breakpoint.MEDIUM: 1.00,
        Breakpoint.LARGE: 1.08,
    }[bp]


def font_size(base_px: int, *, widget: Optional[QWidget] = None) -> int:
    scale = get_ui_scale(widget)
    raw = round(base_px * scale)
    if base_px <= 14:
        return max(_MIN_BODY_FONT_PX, min(_MAX_BODY_FONT_PX, raw))
    return max(_MIN_HEADING_FONT_PX, min(_MAX_HEADING_FONT_PX, raw))


def spacing(base_px: int, *, widget: Optional[QWidget] = None) -> int:
    return max(2, round(base_px * get_ui_scale(widget)))


def icon_size(base_px: int = 16, *, widget: Optional[QWidget] = None) -> int:
    return max(12, round(base_px * get_ui_scale(widget)))


def control_height(base_px: int = 32, *, widget: Optional[QWidget] = None) -> int:
    return max(28, round(base_px * get_ui_scale(widget)))


def page_margin(*, widget: Optional[QWidget] = None) -> int:
    return {
        Breakpoint.COMPACT: 12,
        Breakpoint.MEDIUM: 20,
        Breakpoint.LARGE: 28,
    }[get_breakpoint(widget)]


def shots_panel_width(*, widget: Optional[QWidget] = None) -> int:
    return {
        Breakpoint.COMPACT: 0,
        Breakpoint.MEDIUM: 190,
        Breakpoint.LARGE: 230,
    }[get_breakpoint(widget)]


def inspector_panel_width(*, widget: Optional[QWidget] = None) -> int:
    return {
        Breakpoint.COMPACT: 0,
        Breakpoint.MEDIUM: 300,
        Breakpoint.LARGE: 340,
    }[get_breakpoint(widget)]


def is_panel_collapsible(*, widget: Optional[QWidget] = None) -> bool:
    return get_breakpoint(widget) == Breakpoint.COMPACT


def h_splitter_sizes(total_width: int, *, widget: Optional[QWidget] = None) -> list[int]:
    total_width = max(1, int(total_width))
    bp = get_breakpoint(widget)
    if bp == Breakpoint.COMPACT:
        return [0, total_width, 0]

    if bp == Breakpoint.MEDIUM:
        shots = min(190, max(150, round(total_width * 0.15)))
        inspector = min(300, max(260, round(total_width * 0.22)))
    else:
        shots = min(230, max(190, round(total_width * 0.14)))
        inspector = min(360, max(320, round(total_width * 0.20)))

    canvas = max(320, total_width - shots - inspector)
    return [shots, canvas, inspector]


def v_splitter_sizes(total_height: int, *, widget: Optional[QWidget] = None) -> list[int]:
    total_height = max(200, int(total_height))
    bp = get_breakpoint(widget)
    if bp == Breakpoint.COMPACT:
        timeline = max(150, min(190, round(total_height * 0.30)))
    elif bp == Breakpoint.MEDIUM:
        timeline = max(170, min(240, round(total_height * 0.28)))
    else:
        timeline = max(190, min(280, round(total_height * 0.27)))
    return [max(180, total_height - timeline), timeline]


def scaled_stylesheet_values(*, widget: Optional[QWidget] = None) -> dict[str, int]:
    return {
        "body_font": font_size(13, widget=widget),
        "small_font": font_size(12, widget=widget),
        "heading_font": font_size(18, widget=widget),
        "subheading_font": font_size(15, widget=widget),
        "label_font": font_size(12, widget=widget),
        "pad_xs": spacing(4, widget=widget),
        "pad_sm": spacing(6, widget=widget),
        "pad_md": spacing(10, widget=widget),
        "pad_lg": spacing(14, widget=widget),
        "pad_xl": spacing(18, widget=widget),
        "pad_xxl": spacing(24, widget=widget),
        "icon_sm": icon_size(14, widget=widget),
        "icon_md": icon_size(18, widget=widget),
        "icon_lg": icon_size(22, widget=widget),
        "ctrl_h": control_height(32, widget=widget),
        "ctrl_h_sm": control_height(28, widget=widget),
        "border_radius": spacing(8, widget=widget),
        "border_radius_sm": spacing(6, widget=widget),
    }


def compact_h_splitter_sizes(total_width: int, *, shots_visible: bool, inspector_visible: bool) -> list[int]:
    """Return compact-mode splitter sizes while keeping Canvas usable."""
    total_width = max(1, int(total_width))
    shots = 230 if shots_visible else 0
    inspector = 300 if inspector_visible else 0

    # Never let side panels consume the entire compact viewport.
    max_side = max(0, total_width - 360)
    side_total = shots + inspector
    if side_total > max_side and side_total > 0:
        ratio = max_side / side_total
        shots = round(shots * ratio) if shots else 0
        inspector = round(inspector * ratio) if inspector else 0

    canvas = max(280, total_width - shots - inspector)
    return [shots, canvas, inspector]
