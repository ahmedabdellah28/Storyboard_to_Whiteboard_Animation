"""Master Assembly Dialog.

Provides an interface for building the complete master documentary film from all
sequenced project sections, with live progress reporting and instant playback.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from core.orchestration.master_concatenator import MasterConcatenator
from core.state.project_state import ProjectState
from core.state.state_store import StateStore, get_state_store
from studio_ui.qt import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    Qt,
)


class MasterAssemblyDialog(QDialog):
    """Multi-section master concatenation dialog."""

    def __init__(
        self,
        project: ProjectState,
        state_store: Optional[StateStore] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.state_store = state_store or get_state_store()
        self.concatenator = MasterConcatenator(
            project_id=project.project_id,
            state_store=self.state_store,
        )
        self.master_video_path: Optional[str] = None

        self.setWindowTitle(f"Master Assembly — {project.title or project.project_id}")
        from studio_ui.window_utils import fit_dialog_to_screen
        fit_dialog_to_screen(self, 780, 520, min_width=680, min_height=460)

        self._init_ui()
        self._load_sections()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # 1. Header Card
        header_card = QFrame()
        header_card.setObjectName("card")
        header_layout = QHBoxLayout(header_card)

        info_layout = QVBoxLayout()
        self.title_label = QLabel(f"<b>Master Film Assembly: {self.project.title or self.project.project_id}</b>")
        self.title_label.setStyleSheet("font-size: 16px; color: #101828;")
        self.desc_label = QLabel("Concatenate all sequenced 1080p sections into a unified whiteboard documentary film.")
        self.desc_label.setStyleSheet("color: #475467; font-size: 12px;")
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.desc_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()

        self.sections_count_label = QLabel(f"{len(self.project.sections)} Sections")
        self.sections_count_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 12px;
                padding: 4px 10px;
                border-radius: 4px;
                color: #4F46E5;
                background-color: #EEF2FF;
            }
        """)
        header_layout.addWidget(self.sections_count_label)
        layout.addWidget(header_card)

        # 2. Sections Table
        layout.addWidget(QLabel("<b>Project Sections Sequence:</b>"))
        self.sections_table = QTableWidget()
        self.sections_table.setColumnCount(4)
        self.sections_table.setHorizontalHeaderLabels(["Seq #", "Section ID", "Status", "Deliverable Video"])
        self.sections_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.sections_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.sections_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.sections_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.sections_table, stretch=1)

        # 3. Progress Bar & Status
        self.progress_label = QLabel("Ready to assemble.")
        self.progress_label.setStyleSheet("color: #475467; font-size: 12px;")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # 4. Action Buttons
        btn_layout = QHBoxLayout()

        self.watch_btn = QPushButton("🎬 Watch Master Film")
        self.watch_btn.setEnabled(False)
        self.watch_btn.setStyleSheet("background-color: #4F46E5; color: #FFFFFF; font-weight: bold;")
        self.watch_btn.clicked.connect(self._watch_master)
        btn_layout.addWidget(self.watch_btn)

        self.open_folder_btn = QPushButton("📁 Open Folder")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self._open_folder)
        btn_layout.addWidget(self.open_folder_btn)

        btn_layout.addStretch()

        self.assemble_btn = QPushButton("🚀 Assemble Master Film")
        self.assemble_btn.setObjectName("primaryButton")
        self.assemble_btn.clicked.connect(self._start_assembly)
        btn_layout.addWidget(self.assemble_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def _load_sections(self) -> None:
        """Load sections into table ordered by sequence index."""
        sorted_secs = sorted(self.project.sections.values(), key=lambda s: s.sequence_index)
        self.sections_table.setRowCount(len(sorted_secs))

        for row, sec in enumerate(sorted_secs):
            self.sections_table.setItem(row, 0, QTableWidgetItem(f"#{sec.sequence_index:02d}"))
            self.sections_table.setItem(row, 1, QTableWidgetItem(sec.title or sec.section_id))
            self.sections_table.setItem(row, 2, QTableWidgetItem(sec.status.value))

            v_file = self.concatenator._find_section_video(self.project, sec)
            if v_file:
                item = QTableWidgetItem(f"✓ {v_file.name}")
                item.setForeground(Qt.GlobalColor.green)
            else:
                item = QTableWidgetItem("Missing (Not rendered)")
                item.setForeground(Qt.GlobalColor.red)
            self.sections_table.setItem(row, 3, item)

    def _start_assembly(self) -> None:
        """Trigger master concatenation."""
        self.assemble_btn.setEnabled(False)
        self.progress_bar.setValue(10)
        self.progress_label.setText("Starting assembly...")

        def on_prog(msg: str, frac: float):
            self.progress_label.setText(msg)
            self.progress_bar.setValue(int(frac * 100))

        try:
            manifest = self.concatenator.assemble(progress_cb=on_prog)
            self.master_video_path = manifest["master_video_path"]
            self.progress_label.setText(f"Done! Assembled in {manifest['total_duration']:.1f}s.")
            self.progress_bar.setValue(100)
            self.watch_btn.setEnabled(True)
            self.open_folder_btn.setEnabled(True)
            QMessageBox.information(
                self,
                "Master Assembly Completed",
                f"Master film created successfully!\n\nLocation: {self.master_video_path}\n"
                f"Total Duration: {manifest['total_duration']:.1f}s\nSections: {manifest['sections_count']}",
            )
        except Exception as e:
            self.progress_label.setText(f"Assembly failed: {e}")
            self.progress_bar.setValue(0)
            QMessageBox.critical(self, "Assembly Error", f"Master concatenation failed:\n{e}")
        finally:
            self.assemble_btn.setEnabled(True)

    def _watch_master(self) -> None:
        if not self.master_video_path or not Path(self.master_video_path).exists():
            return
        from studio_ui.views.studio_player import StudioPlayerDialog
        dlg = StudioPlayerDialog(
            video_path=self.master_video_path,
            title="Master Film Preview",
            section_id="master",
            parent=self,
        )
        dlg.exec()

    def _open_folder(self) -> None:
        if self.master_video_path:
            p = Path(self.master_video_path).parent
            if p.exists():
                os.startfile(str(p))
