"""Project browser, launcher view, and recent projects catalog for Whiteboard Studio.

Part of Phase 5: PySide6 Application Shell & Project Browser.
Integrated with centralized responsive system.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from core.config.settings import PROJECT_ROOT
from core.state.project_state import ProjectState
from core.state.state_store import StateStore, get_state_store
from studio_ui.dialogs.new_project_dialog import NewProjectDialog
from studio_ui.qt import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSize,
    QVBoxLayout,
    QWidget,
    Qt,
    Signal,
)
from studio_ui.responsive import (
    Breakpoint,
    control_height,
    font_size,
    get_breakpoint,
    page_margin,
    spacing,
)


class ProjectBrowser(QWidget):
    """Start screen presenting project creation, open file dialog, and recent projects list."""

    project_opened = Signal(object)  # Emits ProjectState when a project is selected

    def __init__(self, parent=None, state_store: Optional[StateStore] = None) -> None:
        super().__init__(parent)
        self.state_store = state_store or get_state_store()
        self.recents_file = PROJECT_ROOT / ".state" / "recent_projects.json"
        self._init_ui()
        self._load_recents()

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Scroll area container for responsive scrolling on small screens
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.content_widget = QWidget()
        self.main_layout = QVBoxLayout(self.content_widget)
        pad = page_margin(widget=self)
        self.main_layout.setContentsMargins(pad, pad, pad, pad)
        self.main_layout.setSpacing(spacing(20))

        # 1. Branding Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(spacing(6))

        self.title_lbl = QLabel("Whiteboard Studio")
        self.title_lbl.setStyleSheet(
            f"color: #4F46E5; font-size: {font_size(26)}px; font-weight: bold; margin: 0px;"
        )

        self.subtitle_lbl = QLabel("Autonomous High-Performance Whiteboard Animation Workstation")
        self.subtitle_lbl.setStyleSheet(
            f"color: #475467; font-size: {font_size(14)}px;"
        )

        header_layout.addWidget(self.title_lbl)
        header_layout.addWidget(self.subtitle_lbl)
        self.main_layout.addLayout(header_layout)

        # 2. Quick Action Cards Container
        self.actions_container = QWidget()
        self.actions_layout = QHBoxLayout(self.actions_container)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(spacing(16))

        # Card: New Project
        self.new_card = QFrame()
        self.new_card.setObjectName("card")
        new_card_layout = QVBoxLayout(self.new_card)
        new_card_layout.setContentsMargins(spacing(16), spacing(16), spacing(16), spacing(16))
        new_card_layout.setSpacing(spacing(10))

        new_lbl = QLabel("<b>Create New Project</b>")
        new_lbl.setStyleSheet(f"font-size: {font_size(15)}px; color: #101828;")
        new_desc = QLabel("Initialize a new multi-section documentary or lesson pipeline.")
        new_desc.setStyleSheet(f"color: #475467; font-size: {font_size(12)}px;")
        new_desc.setWordWrap(True)

        new_btn = QPushButton("New Project...")
        new_btn.setObjectName("primaryButton")
        new_btn.setMinimumHeight(control_height(30))
        new_btn.clicked.connect(self._on_new_project)

        new_card_layout.addWidget(new_lbl)
        new_card_layout.addWidget(new_desc)
        new_card_layout.addStretch()
        new_card_layout.addWidget(new_btn)
        self.actions_layout.addWidget(self.new_card)

        # Card: Open Existing Project
        self.open_card = QFrame()
        self.open_card.setObjectName("card")
        open_card_layout = QVBoxLayout(self.open_card)
        open_card_layout.setContentsMargins(spacing(16), spacing(16), spacing(16), spacing(16))
        open_card_layout.setSpacing(spacing(10))

        open_lbl = QLabel("<b>Open Project</b>")
        open_lbl.setStyleSheet(f"font-size: {font_size(15)}px; color: #101828;")
        open_desc = QLabel("Open an existing project folder or state JSON file from disk.")
        open_desc.setStyleSheet(f"color: #475467; font-size: {font_size(12)}px;")
        open_desc.setWordWrap(True)

        open_btn = QPushButton("Open From Disk...")
        open_btn.setMinimumHeight(control_height(30))
        open_btn.clicked.connect(self._on_open_project)

        open_card_layout.addWidget(open_lbl)
        open_card_layout.addWidget(open_desc)
        open_card_layout.addStretch()
        open_card_layout.addWidget(open_btn)
        self.actions_layout.addWidget(self.open_card)

        self.main_layout.addWidget(self.actions_container)

        # 3. Recent Projects Section
        recents_header = QLabel("<h3>المشاريع الأخيرة (Recent Projects) — مرتبة حسب آخر تحديث 🕒</h3>")
        recents_header.setTextFormat(Qt.TextFormat.RichText)
        recents_header.setStyleSheet(f"color: #344054; margin-top: {spacing(8)}px; font-size: {font_size(16)}px;")
        self.main_layout.addWidget(recents_header)

        self.recents_list = QListWidget()
        self.recents_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.recents_list.itemDoubleClicked.connect(self._on_recent_double_clicked)
        self.recents_list.setMinimumHeight(spacing(160))
        self.main_layout.addWidget(self.recents_list, stretch=1)

        # Footer Actions
        footer_layout = QHBoxLayout()
        self.open_selected_btn = QPushButton("Open Selected Project")
        self.open_selected_btn.setObjectName("primaryButton")
        self.open_selected_btn.setMinimumHeight(control_height(30))
        self.open_selected_btn.setEnabled(False)
        self.open_selected_btn.clicked.connect(self._on_open_selected_recent)

        self.recents_list.itemSelectionChanged.connect(
            lambda: self.open_selected_btn.setEnabled(len(self.recents_list.selectedItems()) > 0)
        )

        footer_layout.addStretch()
        footer_layout.addWidget(self.open_selected_btn)
        self.main_layout.addLayout(footer_layout)

        scroll.setWidget(self.content_widget)
        outer_layout.addWidget(scroll)

    def resizeEvent(self, event) -> None:
        """Dynamically adapt layout padding and orientation on window resize."""
        super().resizeEvent(event)
        pad = page_margin(widget=self)
        self.main_layout.setContentsMargins(pad, pad, pad, pad)

        bp = get_breakpoint(self)
        # Adapt action cards direction: stack vertically on compact screens
        if bp == Breakpoint.COMPACT:
            self.actions_layout.setDirection(QHBoxLayout.Direction.TopToBottom)
        else:
            self.actions_layout.setDirection(QHBoxLayout.Direction.LeftToRight)

    def _on_new_project(self) -> None:
        dlg = NewProjectDialog(self, state_store=self.state_store)
        if dlg.exec():
            state = dlg.created_project_state
            if state:
                self._record_recent(state.project_id, state.title, str(dlg.project_path))
                self.project_opened.emit(state)

    def _on_open_project(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project State",
            str(PROJECT_ROOT / ".state"),
            "Project Files (*_state.json *.wbp *.json)",
        )
        if chosen:
            path = Path(chosen)
            name = path.name
            proj_id = name.replace("_state.json", "").replace(".wbp", "")
            state = self.state_store.load_state(proj_id)
            self._record_recent(state.project_id, state.title, str(path.parent))
            self.project_opened.emit(state)

    def _load_recents(self) -> None:
        import datetime
        self.recents_list.clear()

        # Gather all projects from state store (scans .state directory)
        projects_list = self.state_store.list_all_projects()
        seen_ids = {p["project_id"] for p in projects_list}

        # Also merge with recent_projects.json if there are custom paths not yet discovered
        if self.recents_file.is_file():
            try:
                with open(self.recents_file, "r", encoding="utf-8") as f:
                    recents: List[dict] = json.load(f)
                for item in recents:
                    pid = item.get("project_id")
                    if pid and pid not in seen_ids:
                        projects_list.append(item)
                        seen_ids.add(pid)
            except Exception:
                pass

        # Sort all projects by updated_at descending (newest updated first)
        projects_list.sort(key=lambda x: (x.get("updated_at") or "", x.get("mtime") or 0.0), reverse=True)

        for item in projects_list:
            proj_id = item.get("project_id", "")
            title = item.get("title", proj_id) or proj_id
            sections_count = item.get("sections_count", 0)
            updated_at = item.get("updated_at", "")

            # Format timestamp nicely
            time_display = ""
            if updated_at:
                try:
                    dt = datetime.datetime.fromisoformat(updated_at)
                    time_display = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    time_display = updated_at[:16]

            time_str = f"   •   🕒 آخر تحديث: {time_display}" if time_display else ""
            list_item = QListWidgetItem()
            list_item.setText(f"📁  {title} ({proj_id})   —   {sections_count} سيكشن{time_str}")
            list_item.setData(Qt.ItemDataRole.UserRole, proj_id)
            list_item.setToolTip(f"المشروع: {title}\nالمعرف: {proj_id}\nعدد السيكشنات: {sections_count}\nآخر تحديث: {time_display}")
            self.recents_list.addItem(list_item)

    def _record_recent(self, project_id: str, title: str, path_str: str) -> None:
        import datetime
        self.recents_file.parent.mkdir(parents=True, exist_ok=True)
        recents = []

        if self.recents_file.is_file():
            try:
                with open(self.recents_file, "r", encoding="utf-8") as f:
                    recents = json.load(f)
            except Exception:
                recents = []

        recents = [r for r in recents if r.get("project_id") != project_id]
        recents.insert(0, {
            "project_id": project_id,
            "title": title or project_id,
            "path": path_str,
            "sections_count": len(self.state_store.load_state(project_id).sections),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })

        recents = recents[:20]

        try:
            with open(self.recents_file, "w", encoding="utf-8") as f:
                json.dump(recents, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        self._load_recents()

    def _on_recent_double_clicked(self, item: QListWidgetItem) -> None:
        proj_id = item.data(Qt.ItemDataRole.UserRole)
        if proj_id:
            state = self.state_store.load_state(proj_id)
            self.project_opened.emit(state)

    def _on_open_selected_recent(self) -> None:
        selected = self.recents_list.selectedItems()
        if selected:
            self._on_recent_double_clicked(selected[0])
