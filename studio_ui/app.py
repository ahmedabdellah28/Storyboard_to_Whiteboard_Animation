"""Application launcher and lifecycle bootstrapper for Whiteboard Studio.

Part of Phase 5, Phase 14 & 15: PySide6 Application Shell, Diagnostics & Packaging.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, List

from core.config.settings import PROJECT_ROOT
from core.state.state_store import get_state_store
from core.telemetry.packaging import EnvironmentHealthChecker
from studio_ui.main_window import StudioMainWindow
from studio_ui.qt import QApplication
from studio_ui.theme import apply_light_theme


def create_application(argv: Optional[List[str]] = None) -> tuple[QApplication, StudioMainWindow]:
    """Factory creating and configuring the QApplication and StudioMainWindow instances."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv or sys.argv)
    app.setApplicationName("Whiteboard Studio")
    app.setOrganizationName("WhiteboardStudio")
    app.setApplicationVersion("2.0.0")

    # Apply approved Light 2026 design system
    apply_light_theme(app)

    main_win = StudioMainWindow()
    return app, main_win


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Whiteboard Studio Desktop Workstation")
    parser.add_argument("--project", type=str, default=None, help="Optional Project ID or path to open on startup")
    parser.add_argument("--diagnostics", "--check-env", dest="diagnostics", action="store_true",
                        help="Run full system, FFmpeg, and hardware encoder diagnostics")
    parser.add_argument("--headless-check", action="store_true",
                        help="Perform headless initialization sanity check and exit cleanly")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.diagnostics:
        report = EnvironmentHealthChecker.run_full_diagnostics()
        print(report.format_cli())
        return 0 if report.is_healthy else 1

    app, window = create_application(sys.argv)

    if args.project:
        store = get_state_store()
        proj_state = store.load_state(args.project)
        window.load_project(proj_state)

    if args.headless_check:
        page = window.current_page
        window.close()
        print(f"[StudioUI] Headless initialization sanity check passed. Active page: {page}")
        return 0

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
