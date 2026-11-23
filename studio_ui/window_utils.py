"""Window sizing helpers for responsive dialogs."""
from __future__ import annotations

from studio_ui.qt import QDialog, QWidget


def fit_dialog_to_screen(dialog: QDialog, width: int, height: int, *, min_width: int = 640, min_height: int = 420) -> None:
    """Set a sensible initial dialog size without allowing off-screen geometry."""
    width = max(min_width, int(width))
    height = max(min_height, int(height))
    try:
        screen = dialog.windowHandle().screen() if dialog.windowHandle() else None
        if screen is None:
            screen = dialog.screen()
        if screen is not None:
            geo = screen.availableGeometry()
            width = min(width, max(min_width, geo.width() - 48))
            height = min(height, max(min_height, geo.height() - 64))
    except Exception:
        pass
    dialog.resize(width, height)
