"""Main workstation window and shell for Whiteboard Studio.

Part of Phase 5: PySide6 Application Shell & Project Browser.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.contracts.studio_contracts import StageIdentifier
from core.orchestration.core_bridge import CoreBridge, get_core_bridge
from core.orchestration.resource_governor import ResourceGovernor, get_resource_governor
from core.orchestration.worker_manager import WorkerManager, get_worker_manager
from core.state.project_state import ProjectState, SectionState
from core.state.state_store import StateStore, get_state_store
from core.state.workflow_events import (
    ProjectStatusChangedEvent,
    RevisionIncrementedEvent,
    SectionStatusChangedEvent,
    TaskStatusChangedEvent,
    WorkflowEventBus,
    get_workflow_event_bus,
)
from core.validation.environment_doctor import EnvironmentDoctor
from studio_ui.dialogs.new_project_dialog import NewProjectDialog
from studio_ui.dialogs.new_section_dialog import NewSectionDialog
from studio_ui.qt import (
    QAction,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QKeySequence,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    Qt,
)
from studio_ui.responsive import (
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    font_size,
    spacing,
    page_margin,
    control_height,
    scaled_stylesheet_values,
)
from studio_ui.views.processing_monitor import ProcessingMonitorView
from studio_ui.views.project_browser import ProjectBrowser


class StudioMainWindow(QMainWindow):
    """Primary workstation window shell for Whiteboard Studio."""

    def __init__(
        self,
        state_store: Optional[StateStore] = None,
        event_bus: Optional[WorkflowEventBus] = None,
        resource_governor: Optional[ResourceGovernor] = None,
        worker_manager: Optional[WorkerManager] = None,
        core_bridge: Optional[CoreBridge] = None,
    ) -> None:
        super().__init__()
        self.state_store = state_store or get_state_store()
        self.event_bus = event_bus or get_workflow_event_bus()
        self.governor = resource_governor or get_resource_governor()
        self.worker_manager = worker_manager or get_worker_manager()
        self.core_bridge = core_bridge or get_core_bridge()

        self.current_project: Optional[ProjectState] = None

        self.setWindowTitle("Whiteboard Studio")
        self.resize(1440, 900)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        self._init_ui()
        self._init_menu_bar()
        self._init_status_bar()
        self._subscribe_events()

    def _init_ui(self) -> None:
        self.stacked_widget = QStackedWidget(self)
        self.setCentralWidget(self.stacked_widget)

        # Page 0: Project Browser
        self.project_browser = ProjectBrowser(self, state_store=self.state_store)
        self.project_browser.project_opened.connect(self.load_project)
        self.stacked_widget.addWidget(self.project_browser)

        # Page 1: Active Workspace
        self.workspace_widget = QWidget(self)
        self._init_workspace_ui()
        self.stacked_widget.addWidget(self.workspace_widget)

        # Page 2: Processing Monitor
        self.processing_monitor = ProcessingMonitorView(self, bridge=self.core_bridge)
        self.processing_monitor.back_clicked.connect(self._switch_to_workspace)
        self.processing_monitor.review_requested.connect(self._on_review_requested)
        self.processing_monitor.open_canvas_requested.connect(self._open_studio_editor)
        self.stacked_widget.addWidget(self.processing_monitor)

        # Page 3: Studio Editor (Phase 8 & 9)
        from studio_ui.views.studio_editor import StudioEditorView
        self.studio_editor = StudioEditorView(bridge=self.core_bridge, state_store=self.state_store, parent=self)
        self.studio_editor.back_requested.connect(self._switch_to_workspace)
        self.studio_editor.projects_requested.connect(self.close_project)
        self.studio_editor.render_section_requested.connect(self._on_render_section_requested)
        self.stacked_widget.addWidget(self.studio_editor)

        self.stacked_widget.setCurrentIndex(0)

    @property
    def current_page(self) -> int:
        """Returns the current active page index in the stacked widget."""
        return self.stacked_widget.currentIndex()

    def _init_workspace_ui(self) -> None:
        ws_layout = QVBoxLayout(self.workspace_widget)
        m = page_margin(widget=self)
        ws_layout.setContentsMargins(m, m, m, m)
        ws_layout.setSpacing(spacing(16))

        # 1. Project Header Card
        header_card = QFrame()
        header_card.setObjectName("card")
        header_layout = QHBoxLayout(header_card)

        info_layout = QVBoxLayout()
        sv = scaled_stylesheet_values(widget=self)
        self.proj_title_label = QLabel("<b>Project Name</b>")
        self.proj_title_label.setStyleSheet(f"font-size: {sv['heading_font']}px; color: #101828;")
        self.proj_sub_label = QLabel("Project ID | Schema v2 | Status: IDLE")
        self.proj_sub_label.setStyleSheet(f"color: #475467; font-size: {sv['label_font']}px;")
        info_layout.addWidget(self.proj_title_label)
        info_layout.addWidget(self.proj_sub_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()

        # Action Buttons
        self.add_section_btn = QPushButton("+ Add Section...")
        self.add_section_btn.setObjectName("primaryButton")
        self.add_section_btn.clicked.connect(self._on_add_section)
        header_layout.addWidget(self.add_section_btn)

        self.monitor_btn = QPushButton("📊 Processing Monitor")
        self.monitor_btn.clicked.connect(lambda: self._open_monitor_view())
        header_layout.addWidget(self.monitor_btn)

        self.editor_btn = QPushButton("🎨 Studio Canvas")
        self.editor_btn.setStyleSheet(f"background-color: #4F46E5; color: #FFFFFF; font-weight: bold; font-size: {sv['body_font']}px;")
        self.editor_btn.clicked.connect(lambda: self._open_studio_editor())
        header_layout.addWidget(self.editor_btn)

        self.master_btn = QPushButton("🎞️ Assemble Master Film")
        self.master_btn.setStyleSheet(f"background-color: #4F46E5; color: #FFFFFF; font-weight: bold; font-size: {sv['body_font']}px;")
        self.master_btn.clicked.connect(self._open_master_assembly)
        header_layout.addWidget(self.master_btn)

        self.close_proj_btn = QPushButton("📁 المشاريع (Projects)")
        self.close_proj_btn.setToolTip("الرجوع إلى قائمة المشاريع الرئيسية (Return to Projects Browser)")
        self.close_proj_btn.setStyleSheet(f"background-color: #FAFBFC; color: #101828; font-weight: bold; font-size: {sv['body_font']}px; border: 1px solid #E4E7EC;")
        self.close_proj_btn.clicked.connect(self.close_project)
        header_layout.addWidget(self.close_proj_btn)

        ws_layout.addWidget(header_card)

        # 2. Sections Table
        table_header = QLabel("<h3>Sections Timeline Roster — مرتبة حسب آخر تحديث 🕒</h3>")
        table_header.setTextFormat(Qt.TextFormat.RichText)
        ws_layout.addWidget(table_header)

        self.sections_table = QTableWidget(0, 8)
        self.sections_table.setHorizontalHeaderLabels([
            "Seq", "Section ID", "Title", "Status", "Revision", "Tasks Progress", "آخر تحديث (Updated)", "Studio Action"
        ])
        self.sections_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.sections_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.sections_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.sections_table.cellDoubleClicked.connect(self._on_section_double_clicked)
        ws_layout.addWidget(self.sections_table)

    def _init_menu_bar(self) -> None:
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        new_proj_action = QAction("&New Project...", self)
        new_proj_action.setShortcut(QKeySequence("Ctrl+N"))
        new_proj_action.triggered.connect(self._on_new_project_menu)
        file_menu.addAction(new_proj_action)

        open_proj_action = QAction("&Open Project...", self)
        open_proj_action.setShortcut(QKeySequence("Ctrl+O"))
        open_proj_action.triggered.connect(self.project_browser._on_open_project)
        file_menu.addAction(open_proj_action)

        self.save_proj_action = QAction("&Save Project", self)
        self.save_proj_action.setShortcut(QKeySequence("Ctrl+S"))
        self.save_proj_action.setEnabled(False)
        self.save_proj_action.triggered.connect(self._on_save_project)
        file_menu.addAction(self.save_proj_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View Menu
        view_menu = menubar.addMenu("&View")
        self.view_workspace_action = QAction("&Timeline Roster", self)
        self.view_workspace_action.setShortcut(QKeySequence("Ctrl+T"))
        self.view_workspace_action.triggered.connect(self._switch_to_workspace)
        view_menu.addAction(self.view_workspace_action)

        self.view_monitor_action = QAction("&Processing Monitor", self)
        self.view_monitor_action.setShortcut(QKeySequence("Ctrl+M"))
        self.view_monitor_action.triggered.connect(lambda: self._open_monitor_view())
        view_menu.addAction(self.view_monitor_action)

        # Section Menu
        self.section_menu = menubar.addMenu("&Section")
        self.add_sec_action = QAction("&Add New Section...", self)
        self.add_sec_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        self.add_sec_action.setEnabled(False)
        self.add_sec_action.triggered.connect(self._on_add_section)
        self.section_menu.addAction(self.add_sec_action)

        # Tools Menu
        tools_menu = menubar.addMenu("&Tools")
        doctor_action = QAction("&Environment Diagnostics Doctor...", self)
        doctor_action.triggered.connect(self._on_run_doctor)
        tools_menu.addAction(doctor_action)

        # Help Menu
        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About Whiteboard Studio", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _init_status_bar(self) -> None:
        status_bar = self.statusBar()

        # Hardware Profile Badge
        budget = self.governor.budget
        self.profile_badge = QLabel(f"[Profile: {budget.profile.value}]")
        self.profile_badge.setStyleSheet("color: #4F46E5; font-weight: bold;")
        status_bar.addPermanentWidget(self.profile_badge)

        # Hardware Encoder Badge
        enc_text = f"[Encoder: {budget.render_encoder}]"
        self.encoder_badge = QLabel(enc_text)
        self.encoder_badge.setStyleSheet("color: #16A34A;")
        status_bar.addPermanentWidget(self.encoder_badge)

        # Active Workers
        self.workers_badge = QLabel("[Workers: 0 Active]")
        self.workers_badge.setStyleSheet("color: #475467;")
        status_bar.addPermanentWidget(self.workers_badge)

        status_bar.showMessage("Ready. Select or create a project to begin.")

    def _subscribe_events(self) -> None:
        self.event_bus.subscribe(SectionStatusChangedEvent, self._on_section_status_event)
        self.event_bus.subscribe(RevisionIncrementedEvent, self._on_revision_event)
        self.core_bridge.section_started.connect(self._on_bridge_section_started)
        self.core_bridge.section_finished.connect(self._on_bridge_section_finished)

    def load_project(self, project_state: ProjectState) -> None:
        """Load an active project into the workspace."""
        self.current_project = project_state
        self.setWindowTitle(f"Whiteboard Studio — {project_state.title or project_state.project_id}")

        self.proj_title_label.setText(f"<b>{project_state.title or project_state.project_id}</b>")
        self.proj_sub_label.setText(
            f"Project ID: {project_state.project_id}  |  Schema: v{project_state.schema_version}  |  Status: {project_state.lifecycle_status.value}"
        )

        self.save_proj_action.setEnabled(True)
        self.add_sec_action.setEnabled(True)

        self._refresh_sections_table()
        self.processing_monitor.set_project(project_state)
        self.stacked_widget.setCurrentIndex(1)
        self.statusBar().showMessage(f"Project '{project_state.project_id}' loaded successfully.")

    def close_project(self) -> None:
        """Unload active project and return to ProjectBrowser."""
        self.current_project = None
        self.setWindowTitle("Whiteboard Studio")
        self.save_proj_action.setEnabled(False)
        self.add_sec_action.setEnabled(False)
        self.stacked_widget.setCurrentIndex(0)
        self.project_browser._load_recents()
        self.statusBar().showMessage("Ready. Select or create a project to begin.")

    def _refresh_sections_table(self) -> None:
        if not self.current_project:
            return

        import datetime
        secs = list(self.current_project.sections.values())
        # Sort by updated_at descending (latest updated section first)
        secs.sort(key=lambda s: (s.updated_at or s.created_at or ""), reverse=True)

        self.sections_table.setRowCount(len(secs))
        for row, sec in enumerate(secs):
            # Seq
            self.sections_table.setItem(row, 0, QTableWidgetItem(str(sec.sequence_index)))
            # ID
            self.sections_table.setItem(row, 1, QTableWidgetItem(sec.section_id))
            # Title
            self.sections_table.setItem(row, 2, QTableWidgetItem(sec.title or sec.section_id))
            # Status
            status_item = QTableWidgetItem(sec.lifecycle_status.value)
            # Colorize status
            if sec.lifecycle_status.value == "COMPLETED":
                status_item.setForeground(Qt.GlobalColor.green)
            elif sec.lifecycle_status.value == "ERROR":
                status_item.setForeground(Qt.GlobalColor.red)
            elif "REVIEW" in sec.lifecycle_status.value:
                status_item.setForeground(Qt.GlobalColor.yellow)
            self.sections_table.setItem(row, 3, status_item)
            # Revision
            self.sections_table.setItem(row, 4, QTableWidgetItem(f"r{sec.revision_id}"))
            # Tasks progress
            completed_tasks = sum(1 for t in sec.tasks.values() if t.status.value == "COMPLETED")
            total_tasks = len(sec.tasks)
            self.sections_table.setItem(row, 5, QTableWidgetItem(f"{completed_tasks}/{total_tasks} Tasks"))
            # Last Updated (Column 6)
            up_text = ""
            if sec.updated_at:
                try:
                    dt = datetime.datetime.fromisoformat(sec.updated_at)
                    up_text = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    up_text = sec.updated_at[:16]
            self.sections_table.setItem(row, 6, QTableWidgetItem(up_text or "—"))
            # Action Button (Column 7)
            sv = scaled_stylesheet_values(widget=self)
            btn = QPushButton("🎨 Edit on Canvas")
            btn.setStyleSheet(f"font-size: {sv['small_font']}px; padding: {sv['pad_xs']}px {sv['pad_md']}px; background-color: #4F46E5; color: #FFFFFF;")
            btn.clicked.connect(lambda _, s=sec.section_id: self._open_studio_editor(s))
            self.sections_table.setCellWidget(row, 7, btn)

    def _open_studio_editor(self, section_id: Optional[str] = None) -> None:
        """Open the interactive 1080p Studio Canvas & Timeline Editor."""
        if not self.current_project:
            return
        if not section_id and self.current_project.sections:
            section_id = next(iter(self.current_project.sections.keys()))
        if section_id:
            self.studio_editor.load_section(self.current_project, section_id)
            self.stacked_widget.setCurrentIndex(3)

    def _on_render_section_requested(self, section_id: str) -> None:
        """Trigger section production pipeline directly from Studio."""
        if self.current_project and self.core_bridge:
            self.core_bridge.start_production_pipeline(self.current_project.project_id, section_id)
            self.statusBar().showMessage(f"Rendering pipeline initiated for section '{section_id}'.")


    def _open_master_assembly(self) -> None:
        """Open the multi-section Master Film Assembly dialog."""
        if not self.current_project:
            return
        from studio_ui.dialogs.master_assembly_dialog import MasterAssemblyDialog
        dlg = MasterAssemblyDialog(self.current_project, state_store=self.state_store, parent=self)
        dlg.exec()

    def _on_add_section(self) -> None:
        if not self.current_project:
            return
        dlg = NewSectionDialog(self.current_project, parent=self, state_store=self.state_store)
        if dlg.exec():
            self._refresh_sections_table()
            sec_id = dlg.created_contract.section_id if dlg.created_contract else None
            self.statusBar().showMessage(f"Section '{sec_id}' ready. Opening Studio Canvas...")
            if sec_id:
                self._open_studio_editor(sec_id)

    def _on_new_project_menu(self) -> None:
        dlg = NewProjectDialog(self, state_store=self.state_store)
        if dlg.exec():
            if dlg.created_project_state:
                self.load_project(dlg.created_project_state)

    def _on_save_project(self) -> None:
        if self.current_project:
            self.state_store.save_state(self.current_project)
            self.statusBar().showMessage("Project state saved to disk.")

    def _on_run_doctor(self) -> None:
        rep = EnvironmentDoctor.run_full_diagnosis()
        msg = (
            f"<b>System Environment Diagnostic Report</b><br><br>"
            f"• <b>Status:</b> {'Healthy (Ready)' if rep.is_healthy else 'Attention Required'}<br>"
            f"• <b>FFmpeg:</b> {rep.ffmpeg_version}<br>"
            f"• <b>Video Encoder:</b> {rep.hardware_encoder} (GPU: {rep.details.get('gpu_accelerated')})<br>"
            f"• <b>Free Disk:</b> {rep.free_disk_gb} GB<br>"
            f"• <b>Python:</b> {rep.python_version}<br>"
        )
        if rep.issues:
            msg += "<br><b>Issues Detected:</b><br>" + "<br>".join(f"- {i}" for i in rep.issues)
        if rep.recommendations:
            msg += "<br><br><b>Recommendations:</b><br>" + "<br>".join(f"- {r}" for r in rep.recommendations)

        QMessageBox.information(self, "Environment Doctor", msg)

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About Whiteboard Studio",
            "<h3>Whiteboard Studio v2.0</h3>"
            "<p>Autonomous Production Pipeline & High-Performance Animation Workstation.</p>"
            "<p>Architected for deterministic zero-drift rendering and multi-tier revision safety.</p>",
        )

    def _on_section_status_event(self, ev: SectionStatusChangedEvent) -> None:
        if self.current_project and ev.project_id == self.current_project.project_id:
            self._refresh_sections_table()

    def _on_revision_event(self, ev: RevisionIncrementedEvent) -> None:
        if self.current_project and ev.project_id == self.current_project.project_id:
            self._refresh_sections_table()

    def _switch_to_workspace(self) -> None:
        self.stacked_widget.setCurrentIndex(1)
        self._refresh_sections_table()

    def _open_monitor_view(self, section_id: Optional[str] = None) -> None:
        if not self.current_project:
            return
        self.processing_monitor.set_project(self.current_project, initial_section_id=section_id)
        if section_id:
            self.processing_monitor.set_active_section(section_id)
        self.stacked_widget.setCurrentIndex(2)

    def _on_section_double_clicked(self, row: int, col: int) -> None:
        item = self.sections_table.item(row, 1)
        if item:
            sec_id = item.text()
            self._open_monitor_view(section_id=sec_id)

    def _on_review_requested(self, section_id: str, stage_id: str) -> None:
        """Launch the appropriate human review gate inspection dialog."""
        if not self.current_project:
            return

        # Resolve section directory
        sec_dir = None
        if self.current_project.metadata and self.current_project.metadata.get("project_path"):
            cand = Path(self.current_project.metadata["project_path"]) / "sections" / section_id
            if cand.is_dir():
                sec_dir = cand

        if sec_dir is None:
            from core.config.settings import SECTIONS_DIR
            cand = SECTIONS_DIR / self.current_project.project_id / section_id
            sec_dir = cand if cand.is_dir() else SECTIONS_DIR / section_id

        # Dispatch based on canonical stage category
        if stage_id in (StageIdentifier.EXTRACTION.value, "sec.extraction", "sec.ocr"):
            from studio_ui.dialogs.extraction_review_dialog import ExtractionReviewDialog
            dlg = ExtractionReviewDialog(
                project_id=self.current_project.project_id,
                section_id=section_id,
                section_path=sec_dir,
                state_store=self.state_store,
                event_bus=self.event_bus,
                parent=self,
            )
            dlg.review_approved.connect(self._on_review_approved)
            dlg.exec()

        elif stage_id in (StageIdentifier.TTS.value, "sec.tts", "sec.whisper"):
            from studio_ui.dialogs.voice_review_dialog import VoiceReviewDialog
            dlg = VoiceReviewDialog(
                project_id=self.current_project.project_id,
                section_id=section_id,
                section_path=sec_dir,
                state_store=self.state_store,
                event_bus=self.event_bus,
                parent=self,
            )
            dlg.review_approved.connect(self._on_review_approved)
            dlg.exec()

        elif stage_id in (StageIdentifier.SEMANTIC.value, "sec.semantic", "sec.narrative"):
            from studio_ui.dialogs.semantic_review_dialog import SemanticReviewDialog
            dlg = SemanticReviewDialog(
                project_id=self.current_project.project_id,
                section_id=section_id,
                section_path=sec_dir,
                state_store=self.state_store,
                event_bus=self.event_bus,
                parent=self,
            )
            dlg.review_approved.connect(self._on_review_approved)
            dlg.exec()

        else:
            QMessageBox.information(
                self,
                "Review Gate Active",
                f"Review gate for '{stage_id}' in section '{section_id}' is active.",
            )

    def _on_review_approved(self, section_id: str, stage_id: str) -> None:
        """Handle review approval from any review gate dialog."""
        if self.current_project:
            self.current_project = self.state_store.load_state(self.current_project.project_id)
            self._refresh_sections_table()
            self.processing_monitor.set_project(self.current_project, initial_section_id=section_id)

    def _on_bridge_section_started(self, project_id: str, section_id: str) -> None:
        active_count = len([t for t in self.core_bridge._active_tokens.values() if not t.is_cancelled])
        self.workers_badge.setText(f"[Workers: {active_count} Active]")
        self.workers_badge.setStyleSheet("color: #4F46E5; font-weight: bold;")
        self._refresh_sections_table()

    def _on_bridge_section_finished(self, project_id: str, section_id: str, success: bool, msg: str) -> None:
        active_count = len([t for t in self.core_bridge._active_tokens.values() if not t.is_cancelled])
        self.workers_badge.setText(f"[Workers: {active_count} Active]")
        if active_count == 0:
            self.workers_badge.setStyleSheet("color: #475467;")
        self._refresh_sections_table()

        self._refresh_sections_table()

