"""Main entry point for Whiteboard Studio desktop workstation.

Direct execution entry point:
    python -m studio_ui.main
    python -m studio_ui.main --diagnostics
    python -m studio_ui.main --headless-check
    python -m studio_ui.main --project my_project_id
"""

from __future__ import annotations

import sys
from studio_ui.app import main

if __name__ == "__main__":
    sys.exit(main())
