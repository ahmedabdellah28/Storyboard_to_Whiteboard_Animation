"""Processing Monitor View for Whiteboard Studio.

Part of Phase 6: Core Bridge, Processing Monitor & Section Lifecycle.
Renders canonical 18-stage production progress cards, execution controls,
and real-time diagnostic log stream.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from core.contracts.studio_contracts import STAGE_DEFINITIONS, StageDefinition, StageIdentifier
from core.orchestration.core_bridge import CoreBridge, get_core_bridge
from core.state.project_state import ProjectState, SectionState
from studio_ui.qt import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    Qt,
    QVBoxLayout,
    QWidget,
    Signal,
    Slot,
)
from studio_ui.responsive import (
    Breakpoint,
    control_height,
    font_size,
    get_breakpoint,
    page_margin,
    spacing,
)


# Canonical task-to-stage mapping supporting both canonical and legacy DAG names
TASK_TO_STAGE_MAP: Dict[str, StageIdentifier] = {
    "ingest": StageIdentifier.INGEST,
    "ocr": StageIdentifier.OCR,
    "extraction": StageIdentifier.EXTRACTION,
    "tts": StageIdentifier.TTS,
    "whisper": StageIdentifier.WHISPER,
    "narrative": StageIdentifier.NARRATIVE,
    "semantic": StageIdentifier.SEMANTIC,
    "scene_spec": StageIdentifier.SCENE_SPEC,
    "intent": StageIdentifier.SCENE_SPEC,
    "layout": StageIdentifier.LAYOUT,
    "layout_and_sync": StageIdentifier.LAYOUT,
    "choreography": StageIdentifier.CHOREOGRAPHY,
    "camera": StageIdentifier.CAMERA,
    "sfx": StageIdentifier.SFX,
    "audio_mix": StageIdentifier.AUDIO_MIX,
    "render_plan": StageIdentifier.RENDER_PLAN,
    "pre_render_director": StageIdentifier.RENDER_PLAN,
    "render": StageIdentifier.RENDER,
    "mux": StageIdentifier.MUX,
    "qa": StageIdentifier.QA,
    "post_render_qa": StageIdentifier.QA,
    "export": StageIdentifier.EXPORT,
    "deliverable": StageIdentifier.EXPORT,
}


def _map_task_to_stage(task_id: str) -> Optional[StageIdentifier]:
    """Resolve a DAG task ID (e.g. '01.tts', 'sec.ocr') to its canonical StageIdentifier."""
    clean = task_id.lower()
    if clean.startswith("sec."):
        clean = clean[4:]
    elif "." in clean:
        clean = clean.split(".", 1)[1]

    return TASK_TO_STAGE_MAP.get(clean)


class StageCardWidget(QFrame):
    """Visual card representing an individual production stage's lifecycle and telemetry."""

    review_clicked = Signal(str)  # stage_id

    def __init__(self, stage_def: StageDefinition, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.stage_def = stage_def
        self.stage_id = stage_def.identifier
        self.current_status: str = "PENDING"

        self.setObjectName("card")
        self.setStyleSheet("""
            QFrame#card {
                background-color: #F0F2F5;
                border: 1px solid #E4E7EC;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame#card:hover {
                border-color: #3b82f6;
            }
        """)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header: Index + Name + Status Badge
        top_row = QHBoxLayout()

        idx_label = QLabel(f"<b>[{self.stage_def.index:02d}]</b>")
        idx_label.setStyleSheet("color: #4F46E5; font-weight: bold; font-size: 13px;")
        top_row.addWidget(idx_label)

        self.title_label = QLabel(self.stage_def.name)
        self.title_label.setStyleSheet("color: #101828; font-weight: 600; font-size: 13px;")
        top_row.addWidget(self.title_label)

        top_row.addStretch()

        self.res_badge = QLabel(f"[{self.stage_def.resource_type[:4]}]")
        self.res_badge.setStyleSheet("color: #667085; font-size: 12px;")
        top_row.addWidget(self.res_badge)

        self.status_badge = QLabel("PENDING")
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setMinimumWidth(80)
        self._set_badge_style("PENDING")
        top_row.addWidget(self.status_badge)

        layout.addLayout(top_row)

        # Description
        desc_label = QLabel(self.stage_def.description)
        desc_label.setStyleSheet("color: #475467; font-size: 12px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #FAFBFC;
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #4F46E5;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Meta & Actions Row
        meta_row = QHBoxLayout()

        self.elapsed_label = QLabel("⏱ --")
        self.elapsed_label.setStyleSheet("color: #667085; font-size: 12px;")
        meta_row.addWidget(self.elapsed_label)

        self.cache_label = QLabel("")
        self.cache_label.setStyleSheet("color: #16A34A; font-size: 12px; font-weight: bold;")
        meta_row.addWidget(self.cache_label)

        meta_row.addStretch()

        self.review_btn = QPushButton("Review")
        self.review_btn.setFixedHeight(22)
        self.review_btn.setStyleSheet("""
            QPushButton {
                background-color: #D97706;
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                padding: 2px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #D97706;
            }
        """)
        self.review_btn.clicked.connect(lambda: self.review_clicked.emit(self.stage_id.value))
        self.review_btn.setVisible(False)
        meta_row.addWidget(self.review_btn)

        layout.addLayout(meta_row)

        # Error / Detail Label (Hidden by default)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #DC2626; font-size: 12px;")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

    def _set_badge_style(self, status: str) -> None:
        self.current_status = status
        self.status_badge.setText(status)

        colors = {
            "PENDING": ("#667085", "#FAFBFC"),
            "QUEUED": ("#4F46E5", "#EEF2FF"),
            "RUNNING": ("#22d3ee", "#DBEAFE"),
            "COMPLETED": ("#15803D", "#DCFCE7"),
            "SKIPPED": ("#4F46E5", "#344054"),
            "NEEDS_REVIEW": ("#D97706", "#FFEDD5"),
            "FAILED": ("#f87171", "#FEE2E2"),
            "CANCELLED": ("#F97316", "#FFF1E8"),
        }
        fg, bg = colors.get(status, ("#475467", "#FAFBFC"))
        self.status_badge.setStyleSheet(f"""
            QLabel {{
                color: {fg};
                background-color: {bg};
                font-weight: bold;
                font-size: 12px;
                padding: 3px 8px;
                border-radius: 4px;
            }}
        """)

    def update_status(self, status: str, duration: float = 0.0, error: str = "") -> None:
        self._set_badge_style(status)

        if duration > 0.0:
            self.elapsed_label.setText(f"⏱ {duration:.2f}s")

        if status == "COMPLETED":
            self.progress_bar.setValue(100)
            self.error_label.setVisible(False)
            self.review_btn.setVisible(False)
        elif status == "RUNNING":
            if self.progress_bar.value() == 0:
                self.progress_bar.setValue(30)
            self.error_label.setVisible(False)
        elif status == "NEEDS_REVIEW":
            self.review_btn.setVisible(True)
            self.error_label.setVisible(False)
        elif status == "FAILED":
            self.error_label.setText(f"Error: {error}")
            self.error_label.setVisible(True)
            self.review_btn.setVisible(False)
        elif status == "CANCELLED":
            self.error_label.setText("Cancelled by user")
            self.error_label.setVisible(True)
            self.review_btn.setVisible(False)

    def update_progress(self, progress: float, message: str = "") -> None:
        val = int(max(0.0, min(1.0, progress)) * 100)
        self.progress_bar.setValue(val)
        if message:
            self.elapsed_label.setText(f"⏱ {message}")

    def reset(self) -> None:
        self._set_badge_style("PENDING")
        self.progress_bar.setValue(0)
        self.elapsed_label.setText("⏱ --")
        self.cache_label.setText("")
        self.error_label.setVisible(False)
        self.review_btn.setVisible(False)


class ProcessingMonitorView(QWidget):
    """Workstation Processing Monitor displaying 18 stage cards and real-time logs."""

    back_clicked = Signal()
    review_requested = Signal(str, str)  # (section_id, stage_id)
    open_canvas_requested = Signal(str)  # (section_id)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        bridge: Optional[CoreBridge] = None,
    ) -> None:
        super().__init__(parent)
        self.bridge = bridge or get_core_bridge()
        self.current_project: Optional[ProjectState] = None
        self.active_section_id: str = ""
        self.cards: Dict[StageIdentifier, StageCardWidget] = {}
        self.sorted_stages: List[StageDefinition] = []
        self._current_cols = 3

        self._init_ui()
        self._connect_bridge()

    def _init_ui(self) -> None:
        self.root_layout = QVBoxLayout(self)
        pad = page_margin(widget=self)
        self.root_layout.setContentsMargins(pad, pad, pad, pad)
        self.root_layout.setSpacing(spacing(12))

        # 1. Top Control & Section Navigation Bar
        top_bar = QFrame()
        top_bar.setObjectName("card")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 10, 12, 10)
        top_layout.setSpacing(12)

        self.back_btn = QPushButton("← Back to Timeline")
        self.back_btn.clicked.connect(self.back_clicked.emit)
        top_layout.addWidget(self.back_btn)

        top_layout.addWidget(QLabel("<b>Section:</b>"))
        self.section_combo = QComboBox()
        self.section_combo.setMinimumWidth(220)
        self.section_combo.currentIndexChanged.connect(self._on_section_selected)
        top_layout.addWidget(self.section_combo)

        self.overall_status_badge = QLabel("IDLE")
        self.overall_status_badge.setStyleSheet("""
            QLabel {
                color: #4F46E5;
                background-color: #EEF2FF;
                font-weight: bold;
                font-size: 12px;
                padding: 4px 10px;
                border-radius: 4px;
            }
        """)
        top_layout.addWidget(self.overall_status_badge)

        self.stop_at_review_chk = QCheckBox("Stop at Review")
        self.stop_at_review_chk.setChecked(True)
        self.stop_at_review_chk.setToolTip("Pause pipeline after Extraction, Voice, and Whisper for human review")
        top_layout.addWidget(self.stop_at_review_chk)

        self.force_all_chk = QCheckBox("Force All")
        top_layout.addWidget(self.force_all_chk)

        self.force_render_chk = QCheckBox("Force Render")
        top_layout.addWidget(self.force_render_chk)

        top_layout.addStretch()

        self.run_btn = QPushButton("▶ Process Section")
        self.run_btn.setObjectName("primaryButton")
        self.run_btn.clicked.connect(self._on_run_clicked)
        top_layout.addWidget(self.run_btn)

        self.resume_btn = QPushButton("🚀 Resume Post-Review")
        self.resume_btn.setStyleSheet("background-color: #16A34A; color: #FFFFFF; font-weight: bold;")
        self.resume_btn.setToolTip("Continue pipeline to Spatial Layout, SFX, and Final Render")
        self.resume_btn.clicked.connect(self._on_resume_clicked)
        top_layout.addWidget(self.resume_btn)

        self.open_canvas_btn = QPushButton("🎨 Studio Canvas")
        self.open_canvas_btn.setStyleSheet("background-color: #4F46E5; color: #FFFFFF; font-weight: bold;")
        self.open_canvas_btn.setToolTip("Open interactive 1080p Studio Canvas & Timeline editor")
        self.open_canvas_btn.clicked.connect(lambda: self.open_canvas_requested.emit(self.active_section_id))
        top_layout.addWidget(self.open_canvas_btn)

        self.cancel_btn = QPushButton("🛑 Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("background-color: #B91C1C; color: #FFFFFF;")
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        top_layout.addWidget(self.cancel_btn)

        self.root_layout.addWidget(top_bar)

        # 2. Overall Progress Bar
        prog_row = QHBoxLayout()
        self.overall_prog_label = QLabel("Pipeline Progress: 0 / 18 Stages Completed (0%)")
        self.overall_prog_label.setStyleSheet(
            f"color: #475467; font-weight: 500; font-size: {font_size(12)}px;"
        )
        prog_row.addWidget(self.overall_prog_label)
        self.root_layout.addLayout(prog_row)

        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setRange(0, 18)
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setFixedHeight(spacing(8))
        self.overall_progress_bar.setTextVisible(False)
        self.overall_progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #FAFBFC;
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #16A34A;
                border-radius: 4px;
            }
        """)
        self.root_layout.addWidget(self.overall_progress_bar)

        # 3. Main Splitter: Stage Cards Grid (Top) + Diagnostics Log Stream (Bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Scroll Area for Stage Cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        cards_container = QWidget()
        self.grid_layout = QGridLayout(cards_container)
        self.grid_layout.setSpacing(spacing(10))
        self.grid_layout.setContentsMargins(spacing(4), spacing(4), spacing(4), spacing(4))

        # Populate the 18 Canonical Stage Cards
        self.sorted_stages = sorted(STAGE_DEFINITIONS.values(), key=lambda s: s.index)
        self._current_cols = 3
        for i, sdef in enumerate(self.sorted_stages):
            card = StageCardWidget(sdef, parent=cards_container)
            card.review_clicked.connect(self._on_card_review_clicked)
            self.cards[sdef.identifier] = card
            row, col = divmod(i, self._current_cols)
            self.grid_layout.addWidget(card, row, col)

        scroll_area.setWidget(cards_container)
        splitter.addWidget(scroll_area)

        # Log Stream Console
        log_panel = QFrame()
        log_panel.setObjectName("card")
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(12, 8, 12, 8)
        log_layout.setSpacing(6)

        log_header = QHBoxLayout()
        log_title = QLabel("<b>Diagnostics & Real-Time Pipeline Log Stream</b>")
        log_title.setStyleSheet("color: #101828; font-size: 12px;")
        log_header.addWidget(log_title)

        log_header.addStretch()

        self.log_level_filter = QComboBox()
        self.log_level_filter.addItems(["ALL", "INFO", "WARNING", "ERROR"])
        self.log_level_filter.currentTextChanged.connect(self._filter_logs)
        log_header.addWidget(self.log_level_filter)

        self.log_search_input = QLineEdit()
        self.log_search_input.setPlaceholderText("Filter logs...")
        self.log_search_input.setFixedWidth(160)
        self.log_search_input.textChanged.connect(self._filter_logs)
        log_header.addWidget(self.log_search_input)

        self.autoscroll_chk = QCheckBox("Auto-scroll")
        self.autoscroll_chk.setChecked(True)
        log_header.addWidget(self.autoscroll_chk)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(22)
        clear_btn.clicked.connect(self._clear_logs)
        log_header.addWidget(clear_btn)

        log_layout.addLayout(log_header)

        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #F5F6F8;
                color: #475467;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid #FAFBFC;
                border-radius: 4px;
            }
        """)
        log_layout.addWidget(self.log_console)

        splitter.addWidget(log_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.root_layout.addWidget(splitter, stretch=1)
        self._raw_log_lines: List[tuple[str, str, str, str, str]] = []

    def resizeEvent(self, event) -> None:
        """Dynamically adapt padding and grid columns on resize."""
        super().resizeEvent(event)
        pad = page_margin(widget=self)
        self.root_layout.setContentsMargins(pad, pad, pad, pad)

        w = self.width()
        if w < 850:
            target_cols = 1
        elif w < 1250:
            target_cols = 2
        elif w < 1700:
            target_cols = 3
        else:
            target_cols = 4

        self._reflow_cards(target_cols)

    def _reflow_cards(self, cols: int) -> None:
        if cols == self._current_cols or not self.sorted_stages:
            return
        self._current_cols = cols
        for i, sdef in enumerate(self.sorted_stages):
            card = self.cards.get(sdef.identifier)
            if card:
                self.grid_layout.removeWidget(card)
                row, col = divmod(i, cols)
                self.grid_layout.addWidget(card, row, col)

    def _connect_bridge(self) -> None:
        self.bridge.task_status_changed.connect(self._on_task_status_changed)
        self.bridge.task_progress_updated.connect(self._on_task_progress_updated)
        self.bridge.section_status_changed.connect(self._on_section_status_changed)
        self.bridge.pipeline_log_received.connect(self._on_log_received)
        self.bridge.section_started.connect(self._on_section_started)
        self.bridge.section_finished.connect(self._on_section_finished)

    # ------------------------------------------------------------------------
    # Public State Loading
    # ------------------------------------------------------------------------

    def set_project(self, project: ProjectState, initial_section_id: Optional[str] = None) -> None:
        """Bind project and populate section selector."""
        self.current_project = project
        self.section_combo.blockSignals(True)
        self.section_combo.clear()

        secs = sorted(project.sections.values(), key=lambda s: s.sequence_index)
        for s in secs:
            title_text = f"[{s.sequence_index}] {s.title or s.section_id}"
            self.section_combo.addItem(title_text, s.section_id)

        self.section_combo.blockSignals(False)

        if initial_section_id:
            idx = self.section_combo.findData(initial_section_id)
            if idx >= 0:
                self.section_combo.setCurrentIndex(idx)
        elif secs:
            self.section_combo.setCurrentIndex(0)

        self._refresh_active_section()

    def set_active_section(self, section_id: str) -> None:
        idx = self.section_combo.findData(section_id)
        if idx >= 0:
            self.section_combo.setCurrentIndex(idx)

    # ------------------------------------------------------------------------
    # Internal Handlers & Refresh Logic
    # ------------------------------------------------------------------------

    def _on_section_selected(self, index: int) -> None:
        self._refresh_active_section()

    def _refresh_active_section(self) -> None:
        sec_id = self.section_combo.currentData()
        if not sec_id or not self.current_project or sec_id not in self.current_project.sections:
            return

        self.active_section_id = sec_id
        sec_state = self.current_project.sections[sec_id]

        # Reset all cards
        for card in self.cards.values():
            card.reset()

        # Populate cards from stored tasks
        completed_count = 0
        for task_id, tstate in sec_state.tasks.items():
            stage_id = _map_task_to_stage(task_id)
            if stage_id and stage_id in self.cards:
                status_str = tstate.status.value
                self.cards[stage_id].update_status(
                    status_str,
                    duration=tstate.duration_seconds,
                    error=tstate.error or "",
                )
                if status_str == "COMPLETED":
                    completed_count += 1

        # Check review gates
        for stage_key, gate_status in sec_state.review_gates.items():
            stg = _map_task_to_stage(stage_key)
            if stg and stg in self.cards and gate_status.value == "NEEDS_REVIEW":
                self.cards[stg].update_status("NEEDS_REVIEW")

        self.overall_status_badge.setText(sec_state.lifecycle_status.value)
        self._update_overall_progress(completed_count)

        is_running = self.bridge.is_section_running(sec_id)
        self.run_btn.setEnabled(not is_running)
        self.cancel_btn.setEnabled(is_running)

    def _update_overall_progress(self, completed_count: int) -> None:
        total = len(STAGE_DEFINITIONS)
        self.overall_progress_bar.setValue(completed_count)
        pct = int((completed_count / total) * 100) if total > 0 else 0
        self.overall_prog_label.setText(
            f"Pipeline Progress: {completed_count} / {total} Stages Completed ({pct}%)"
        )

    # ------------------------------------------------------------------------
    # Bridge Signal Listeners
    # ------------------------------------------------------------------------

    def _on_task_status_changed(
        self,
        project_id: str,
        section_id: str,
        task_id: str,
        status_val: str,
        duration: float,
        error: str,
    ) -> None:
        if section_id != self.active_section_id:
            return

        stage_id = _map_task_to_stage(task_id)
        if stage_id and stage_id in self.cards:
            self.cards[stage_id].update_status(status_val, duration=duration, error=error)

            completed = sum(1 for c in self.cards.values() if c.current_status == "COMPLETED")
            self._update_overall_progress(completed)

    def _on_task_progress_updated(
        self,
        project_id: str,
        section_id: str,
        task_id: str,
        progress: float,
        message: str,
    ) -> None:
        if section_id != self.active_section_id:
            return

        stage_id = _map_task_to_stage(task_id)
        if stage_id and stage_id in self.cards:
            self.cards[stage_id].update_progress(progress, message=message)

    def _on_section_status_changed(
        self,
        project_id: str,
        section_id: str,
        status_val: str,
        revision_id: int,
    ) -> None:
        if section_id == self.active_section_id:
            self.overall_status_badge.setText(status_val)

    def _on_section_started(self, project_id: str, section_id: str) -> None:
        if section_id == self.active_section_id:
            self.run_btn.setEnabled(False)
            self.cancel_btn.setEnabled(True)
            self.overall_status_badge.setText("PROCESSING")

    def _on_section_finished(
        self,
        project_id: str,
        section_id: str,
        success: bool,
        msg: str,
    ) -> None:
        if section_id == self.active_section_id:
            self.run_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.overall_status_badge.setText("COMPLETED" if success else "FAILED")

    def _on_card_review_clicked(self, stage_id_str: str) -> None:
        self.review_requested.emit(self.active_section_id, stage_id_str)

    # ------------------------------------------------------------------------
    # Execution Actions
    # ------------------------------------------------------------------------

    def _on_run_clicked(self) -> None:
        if not self.current_project or not self.active_section_id:
            return

        sec_path = None
        if self.current_project.metadata and self.current_project.metadata.get("project_path"):
            cand = Path(self.current_project.metadata["project_path"]) / "sections" / self.active_section_id
            if cand.is_dir():
                sec_path = cand

        mode = "to_review" if self.stop_at_review_chk.isChecked() else "full"
        self.bridge.start_section_pipeline(
            project_id=self.current_project.project_id,
            section_id=self.active_section_id,
            section_path=sec_path,
            force_all=self.force_all_chk.isChecked(),
            force_render=self.force_render_chk.isChecked(),
            target_mode=mode,
        )

    def _on_resume_clicked(self) -> None:
        if not self.current_project or not self.active_section_id:
            return

        sec_path = None
        if self.current_project.metadata and self.current_project.metadata.get("project_path"):
            cand = Path(self.current_project.metadata["project_path"]) / "sections" / self.active_section_id
            if cand.is_dir():
                sec_path = cand

        self.bridge.start_section_pipeline(
            project_id=self.current_project.project_id,
            section_id=self.active_section_id,
            section_path=sec_path,
            force_all=self.force_all_chk.isChecked(),
            force_render=self.force_render_chk.isChecked(),
            target_mode="post_review",
        )

    def _on_cancel_clicked(self) -> None:
        if self.active_section_id:
            self.bridge.cancel_section(self.active_section_id)

    # ------------------------------------------------------------------------
    # Log Stream Handling
    # ------------------------------------------------------------------------

    def _on_log_received(
        self,
        timestamp: str,
        level: str,
        section_id: str,
        stage_id: str,
        message: str,
    ) -> None:
        entry = (timestamp, level, section_id, stage_id, message)
        self._raw_log_lines.append(entry)
        self._append_log_entry(entry)

    def _append_log_entry(self, entry: tuple[str, str, str, str, str]) -> None:
        ts, lvl, sec, stg, msg = entry
        lvl_filter = self.log_level_filter.currentText()
        if lvl_filter != "ALL" and lvl != lvl_filter:
            return

        srch = self.log_search_input.text().strip().lower()
        if srch and srch not in msg.lower() and srch not in sec.lower() and srch not in stg.lower():
            return

        # Format line with color
        color = "#475467"
        if lvl == "ERROR":
            color = "#f87171"
        elif lvl == "WARNING":
            color = "#D97706"
        elif lvl == "INFO":
            color = "#4F46E5"

        line = f"<span style='color:#667085;'>[{ts}]</span> <span style='color:{color}; font-weight:bold;'>[{lvl:5s}]</span> <span style='color:#4F46E5;'>[{sec or 'proj'}]</span> <span style='color:#344054;'>{msg}</span>"
        self.log_console.appendHtml(line)

        if self.autoscroll_chk.isChecked():
            sb = self.log_console.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _filter_logs(self) -> None:
        self.log_console.clear()
        for entry in self._raw_log_lines:
            self._append_log_entry(entry)

    def _clear_logs(self) -> None:
        self._raw_log_lines.clear()
        self.log_console.clear()
