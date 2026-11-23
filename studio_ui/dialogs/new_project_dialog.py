"""New Project creation dialog for Whiteboard Studio.

Part of Phase 5: PySide6 Application Shell & Project Browser.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from core.config.settings import PROJECT_ROOT
from core.state.project_state import ProjectState
from core.state.state_store import StateStore, get_state_store
from studio_ui.qt import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    Qt,
)


class NewProjectDialog(QDialog):
    """Dialog allowing the user to configure and initialize a new Whiteboard Studio project."""

    def __init__(self, parent=None, state_store: Optional[StateStore] = None) -> None:
        super().__init__(parent)
        self.state_store = state_store or get_state_store()
        self.created_project_state: Optional[ProjectState] = None
        self.project_path: Optional[Path] = None

        self.setWindowTitle("Create New Whiteboard Studio Project")
        self.setMinimumWidth(520)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header description
        header = QLabel("<h3>New Whiteboard Project</h3><p style='color: #475467;'>Configure your project name and directory location to begin video production.</p>")
        header.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(header)

        # Form layout
        form = QFormLayout()
        form.setSpacing(12)

        # 1. Project ID
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("e.g. world_history_ep01")
        form.addRow("Project ID (Folder):", self.id_edit)

        # 2. Project Title
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. وثائقي: تاريخ العالم القديم")
        form.addRow("Display Title:", self.title_edit)

        # 3. Project Directory
        dir_layout = QHBoxLayout()
        default_dir = str(PROJECT_ROOT / "project_content")
        self.dir_edit = QLineEdit(default_dir)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_dir)
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(browse_btn)
        form.addRow("Location:", dir_layout)

        layout.addLayout(form)

        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Create Project")
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primaryButton")
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _browse_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self,
            "Select Project Storage Directory",
            self.dir_edit.text() or str(PROJECT_ROOT),
        )
        if chosen:
            self.dir_edit.setText(chosen)

    def _on_accept(self) -> None:
        proj_id = self.id_edit.text().strip()
        title = self.title_edit.text().strip() or proj_id
        base_dir = self.dir_edit.text().strip()

        # Validation
        if not proj_id:
            QMessageBox.warning(self, "Invalid Input", "Project ID cannot be empty.")
            return

        # Sanitize project ID
        invalid_chars = set('<>:"/\\|?*')
        if any(c in invalid_chars for c in proj_id):
            QMessageBox.warning(self, "Invalid Input", "Project ID contains invalid characters.")
            return

        target_dir = Path(base_dir) / proj_id
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "sections").mkdir(exist_ok=True)
            (target_dir / "deliverables").mkdir(exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "File System Error", f"Could not create project directory: {e}")
            return

        # Initialize ProjectState
        state = ProjectState(
            project_id=proj_id,
            title=title,
            schema_version=2,
            metadata={"project_path": str(target_dir)},
        )
        self.state_store.save_state(state)

        self.created_project_state = state
        self.project_path = target_dir
        self.accept()
