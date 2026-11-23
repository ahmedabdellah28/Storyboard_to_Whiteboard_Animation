"""Unified Whiteboard Studio Editor & Live Video Preview.

CRITICAL UX REVISION:
- Eliminates separate "Preview screen" step. The Studio IS the unified editing and preview workspace.
- Integrated 1080p Live Canvas with real-time inking and element animation.
- Synchronized Multi-track Timeline:
  1. VOICE (Original narration waveform/words, locked by default for Whisper sync)
  2. VISUALS (Asset events with draw + hold durations, draggable & edge-resizable)
  3. SFX (Independent cue markers with diamond symbols, AUTO vs USER_OVERRIDE ownership)
  4. CAMERA (Shot boundaries and camera pan intervals)
- Live Playback Transport (Play, Pause, Stop, Scrub, Timecode).
- Preview Scopes: [ Shot ] [ Section ] [ Selection ] [ Project ].
- Immediate visual, timeline, and inspector synchronization with direct manipulation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.contracts.studio_contracts import StageIdentifier
from core.orchestration.core_bridge import CoreBridge, get_core_bridge
from core.state.project_state import ProjectState, SectionState
from core.state.state_store import StateStore, get_state_store
from studio_ui.qt import (
    QButtonGroup,
    QColor,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QMenu,
    QToolButton,
    QPixmap,
    QPushButton,
    QRectF,
    QScrollArea,
    QSplitter,
    QTimer,
    Qt,
    QVBoxLayout,
    QWidget,
    Signal,
)
from studio_ui.responsive import (
    Breakpoint,
    get_breakpoint,
    font_size,
    spacing,
    page_margin,
    control_height,
    icon_size,
    h_splitter_sizes,
    compact_h_splitter_sizes,
    v_splitter_sizes,
    is_panel_collapsible,
    shots_panel_width,
    inspector_panel_width,
    scaled_stylesheet_values,
)
from studio_ui.views.camera_render_view import MultiCameraRenderStrip
from studio_ui.views.element_extraction_panel import ElementExtractionPanel
from studio_ui.views.studio_canvas import (
    CameraFrustumItem,
    CanvasElementItem,
    CanvasTextItem,
    StudioCanvasScene,
    StudioCanvasView,
)
from studio_ui.views.studio_inspector import StudioInspectorPanel
from studio_ui.views.studio_timeline import StudioTimelineView, TimelineTrackItem
from studio_ui.qt import QTabWidget as _QTabWidget  # noqa: F401 — ensure QTabWidget is importable
QTabWidget = _QTabWidget


class StudioEditorView(QWidget):
    """Unified Studio Workspace combining Canvas, Live Video Playback, Multi-Track Timeline, and Inspector."""

    back_requested = Signal()
    projects_requested = Signal()
    render_section_requested = Signal(str)  # section_id

    def __init__(
        self,
        bridge: Optional[CoreBridge] = None,
        state_store: Optional[StateStore] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.bridge = bridge or get_core_bridge()
        self.state_store = state_store or get_state_store()

        self.current_project: Optional[ProjectState] = None
        self.active_section_id: Optional[str] = None
        self.section_path: Optional[Path] = None

        # Data stores
        self.elements_data: Dict[str, Dict[str, Any]] = {}
        self.cameras_data: Dict[str, Dict[str, Any]] = {}
        self.sfx_cues: Dict[str, Dict[str, Any]] = {}
        self.words_data: List[Tuple[str, float, float]] = []
        self.auto_defaults_backup: Dict[str, Dict[str, Any]] = {}

        self.canvas_items: Dict[str, CanvasElementItem] = {}
        self.camera_frustum: Optional[CameraFrustumItem] = None
        self.active_camera_name = "Camera 01"

        # Playback Engine
        self.is_playing = False
        self.playhead_time = 0.0
        self.section_duration = 30.0
        self.preview_scope = "Section"  # "Shot", "Section", "Selection", "Project"
        self.is_dirty = False

        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(33)  # ~30 FPS
        self.playback_timer.timeout.connect(self._on_playback_tick)

        self._init_ui()

    def _init_ui(self) -> None:
        sv = scaled_stylesheet_values()
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # =====================================================================
        # 1. TOP STUDIO TOOLBAR (Playback, Scope, Content Tools, Actions)
        # =====================================================================
        toolbar = QFrame()
        toolbar.setStyleSheet(f"background-color: #FFFFFF; border-bottom: 1px solid #FAFBFC; padding: {sv['pad_sm']}px;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(sv['pad_lg'], sv['pad_sm'], sv['pad_lg'], sv['pad_sm'])
        tb_layout.setSpacing(spacing(10))

        # Navigation: Back to Projects & Back to Sections
        self.back_to_projects_btn = QPushButton("📁 المشاريع (Projects)")
        self.back_to_projects_btn.setStyleSheet(f"background-color: #FAFBFC; color: #101828; font-weight: bold; padding: {sv['pad_xs']}px {sv['pad_md']}px; font-size: {sv['small_font']}px; border: 1px solid #E4E7EC; border-radius: 4px;")
        self.back_to_projects_btn.setToolTip("الرجوع إلى قائمة المشاريع الرئيسية (Projects Browser)")
        self.back_to_projects_btn.clicked.connect(self._on_projects_clicked)
        tb_layout.addWidget(self.back_to_projects_btn)

        self.back_btn = QPushButton("⬅ السيكشنات (Sections)")
        self.back_btn.setStyleSheet(f"background-color: #FAFBFC; color: #4F46E5; font-weight: bold; padding: {sv['pad_xs']}px {sv['pad_md']}px; font-size: {sv['small_font']}px; border: 1px solid #4F46E5; border-radius: 4px;")
        self.back_btn.setToolTip("الرجوع إلى جدول سيكشنات المشروع الحالي (Sections Roster)")
        self.back_btn.clicked.connect(self._on_back_clicked)
        tb_layout.addWidget(self.back_btn)

        # Compact layout controls are part of the toolbar (not orphan widgets).
        self.shots_toggle_btn = QToolButton()
        self.shots_toggle_btn.setText("Shots")
        self.shots_toggle_btn.setToolTip("Show / hide the Shots panel")
        self.shots_toggle_btn.setCheckable(True)
        self.shots_toggle_btn.setChecked(False)
        self.shots_toggle_btn.clicked.connect(self._toggle_shots_panel)
        self.shots_toggle_btn.setVisible(False)
        tb_layout.addWidget(self.shots_toggle_btn)

        self.inspector_toggle_btn = QToolButton()
        self.inspector_toggle_btn.setText("Inspector")
        self.inspector_toggle_btn.setToolTip("Show / hide the Inspector panel")
        self.inspector_toggle_btn.setCheckable(True)
        self.inspector_toggle_btn.setChecked(False)
        self.inspector_toggle_btn.clicked.connect(self._toggle_inspector_panel)
        self.inspector_toggle_btn.setVisible(False)
        tb_layout.addWidget(self.inspector_toggle_btn)

        # Section Info & Dirty Badge
        self.section_title_lbl = QLabel("<b>Section: None</b>")
        self.section_title_lbl.setStyleSheet(f"font-size: {sv['body_font']}px; color: #4F46E5;")
        tb_layout.addWidget(self.section_title_lbl)

        self.dirty_lbl = QLabel("● Unsaved")
        self.dirty_lbl.setStyleSheet(f"color: #D97706; font-size: {sv['small_font']}px; font-weight: bold;")
        self.dirty_lbl.setVisible(False)
        tb_layout.addWidget(self.dirty_lbl)

        tb_layout.addSpacing(spacing(12))

        # PLAYBACK TRANSPORT CONTROLS
        transport_h = control_height(26)
        self.jump_start_btn = QPushButton("⏮")
        self.jump_start_btn.setToolTip("Rewind to Beginning")
        self.jump_start_btn.setFixedSize(transport_h + spacing(4), transport_h)
        self.jump_start_btn.clicked.connect(self.stop_playback)
        tb_layout.addWidget(self.jump_start_btn)

        self.play_pause_btn = QPushButton("▶ Play")
        self.play_pause_btn.setToolTip("Play / Pause Live Preview")
        self.play_pause_btn.setStyleSheet(f"background-color: #16A34A; color: #FFFFFF; font-weight: bold; padding: {sv['pad_sm']}px {sv['pad_lg']}px; font-size: {sv['body_font']}px;")
        self.play_pause_btn.clicked.connect(self.toggle_playback)
        tb_layout.addWidget(self.play_pause_btn)

        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setToolTip("Stop Playback")
        self.stop_btn.setFixedSize(transport_h + spacing(4), transport_h)
        self.stop_btn.clicked.connect(self.stop_playback)
        tb_layout.addWidget(self.stop_btn)

        tb_layout.addSpacing(spacing(12))

        # PREVIEW SCOPE SELECTOR: [ Shot ] [ Section ] [ Selection ] [ Project ]
        self.scope_lbl = QLabel("Scope:")
        self.scope_lbl.setStyleSheet(f"font-size: {sv['small_font']}px;")
        tb_layout.addWidget(self.scope_lbl)
        self.scope_btn_group = QButtonGroup(self)
        self.scope_btn_group.setExclusive(True)
        self.scope_buttons = []

        for scope_name in ["Shot", "Section", "Selection", "Project"]:
            s_btn = QPushButton(scope_name)
            s_btn.setCheckable(True)
            s_btn.setStyleSheet(f"""
                QPushButton {{ background-color: #FAFBFC; color: #475467; padding: {sv['pad_sm']}px {sv['pad_md']}px; font-size: {sv['small_font']}px; }}
                QPushButton:checked {{ background-color: #4F46E5; color: #FFFFFF; font-weight: bold; }}
            """)
            if scope_name == "Section":
                s_btn.setChecked(True)
            s_btn.clicked.connect(lambda _, s=scope_name: self.set_preview_scope(s))
            self.scope_btn_group.addButton(s_btn)
            self.scope_buttons.append(s_btn)
            tb_layout.addWidget(s_btn)

        tb_layout.addSpacing(spacing(16))

        # Creative Content Tools
        self.add_text_btn = QPushButton("+ Text")
        self.add_text_btn.setToolTip("Add text overlay to current camera frame")
        self.add_text_btn.clicked.connect(self._add_text_overlay)
        tb_layout.addWidget(self.add_text_btn)

        self.add_sfx_btn = QPushButton("+ SFX Cue")
        self.add_sfx_btn.setToolTip("Add custom SFX trigger at playhead position")
        self.add_sfx_btn.clicked.connect(self._add_sfx_cue)
        tb_layout.addWidget(self.add_sfx_btn)

        # Viewport Fit & Zoom
        self.fit_btn = QPushButton("Fit 1080p")
        self.fit_btn.setToolTip("Fit the full 1920x1080 canvas into the viewport")
        self.fit_btn.clicked.connect(lambda: self.canvas_view.fit_1080p())
        tb_layout.addWidget(self.fit_btn)

        # Extraction panel toggle
        self.extraction_btn = QPushButton("✂️ Extraction")
        self.extraction_btn.setToolTip("Open Element Extraction panel to re-select and debug bounding boxes")
        self.extraction_btn.setStyleSheet(f"background-color: #FAFBFC; color: #16A34A; font-weight: bold; padding: {sv['pad_sm']}px {sv['pad_md']}px; font-size: {sv['small_font']}px; border: 1px solid #16A34A; border-radius: 4px;")
        self.extraction_btn.clicked.connect(self._switch_to_extraction_tab)
        tb_layout.addWidget(self.extraction_btn)

        # Camera views toggle
        self.cameras_view_btn = QPushButton("📷 Camera Views")
        self.cameras_view_btn.setToolTip("Show render-accurate white-canvas camera views (horizontal layout)")
        self.cameras_view_btn.setStyleSheet(f"background-color: #FAFBFC; color: #D97706; font-weight: bold; padding: {sv['pad_sm']}px {sv['pad_md']}px; font-size: {sv['small_font']}px; border: 1px solid #D97706; border-radius: 4px;")
        self.cameras_view_btn.clicked.connect(self._switch_to_cameras_tab)
        tb_layout.addWidget(self.cameras_view_btn)

        # Responsive toolbar overflow for medium/compact widths.
        self.more_btn = QToolButton()
        self.more_btn.setText("More ▾")
        self.more_btn.setToolTip("More Studio actions")
        self.more_menu = QMenu(self)
        self.more_btn.setMenu(self.more_menu)
        self.more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.more_btn.setVisible(False)
        tb_layout.addWidget(self.more_btn)

        self._toolbar_overflow_widgets = [
            self.add_text_btn, self.add_sfx_btn, self.fit_btn,
            self.extraction_btn, self.cameras_view_btn,
        ]
        self._toolbar_overflow_actions = []
        for widget, label in [
            (self.add_text_btn, "Add Text"),
            (self.add_sfx_btn, "Add SFX Cue"),
            (self.fit_btn, "Fit Canvas"),
            (self.extraction_btn, "Extraction"),
            (self.cameras_view_btn, "Camera Views"),
        ]:
            action = self.more_menu.addAction(label)
            action.triggered.connect(widget.click)
            self._toolbar_overflow_actions.append(action)

        tb_layout.addStretch()

        # Action Buttons: Save & Render Section
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setStyleSheet(f"background-color: #4F46E5; color: #FFFFFF; font-weight: bold; padding: {sv['pad_sm']}px {sv['pad_lg']}px; font-size: {sv['body_font']}px;")
        self.save_btn.setToolTip("Save layout to disk (Ctrl+S)")
        self.save_btn.clicked.connect(self.save_layout)
        tb_layout.addWidget(self.save_btn)

        self.render_btn = QPushButton("Render Section")
        self.render_btn.setStyleSheet(f"background-color: #4F46E5; color: #FFFFFF; font-weight: bold; padding: {sv['pad_sm']}px {sv['pad_lg']}px; font-size: {sv['body_font']}px;")
        self.render_btn.setToolTip("Submit section to the rendering pipeline")
        self.render_btn.clicked.connect(self._on_render_clicked)
        tb_layout.addWidget(self.render_btn)

        root_layout.addWidget(toolbar)

        # =====================================================================
        # 2. MAIN HORIZONTAL SPLITTER: Shots Strip (Left) + Canvas (Center) + Inspector (Right)
        # =====================================================================
        self.main_h_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Column: Shots Strip (collapsible at COMPACT)
        self.shots_panel = QFrame()
        self.shots_panel.setMinimumWidth(0)
        self.shots_panel.setMaximumWidth(260)
        self.shots_panel.setStyleSheet("background-color: #FFFFFF; border-right: 1px solid #FAFBFC;")
        shots_layout = QVBoxLayout(self.shots_panel)
        shots_layout.setContentsMargins(sv['pad_md'], sv['pad_md'], sv['pad_md'], sv['pad_md'])
        shots_layout.setSpacing(spacing(6))

        shots_hdr = QLabel("<b>SHOTS / CAMERAS</b>")
        shots_hdr.setStyleSheet(f"color: #D97706; font-size: {sv['small_font']}px;")
        shots_layout.addWidget(shots_hdr)

        # Scrollable shots container for many camera shots
        self.shots_scroll = QScrollArea()
        self.shots_scroll.setWidgetResizable(True)
        self.shots_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.shots_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.shots_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.shots_scroll_content = QWidget()
        self.shots_btn_container = QVBoxLayout(self.shots_scroll_content)
        self.shots_btn_container.setSpacing(spacing(4))
        self.shots_btn_container.setContentsMargins(0, 0, 0, 0)
        self.shots_btn_group = QButtonGroup(self)
        self.shots_btn_group.setExclusive(True)
        self.shots_btn_container.addStretch()
        self.shots_scroll.setWidget(self.shots_scroll_content)
        shots_layout.addWidget(self.shots_scroll)

        self.add_shot_btn = QPushButton("+ Add Shot")
        self.add_shot_btn.setStyleSheet(f"background-color: #FAFBFC; color: #D97706; font-size: {sv['small_font']}px; padding: {sv['pad_sm']}px;")
        self.add_shot_btn.setToolTip("Add a new camera shot")
        self.add_shot_btn.clicked.connect(self._add_camera_shot)
        shots_layout.addWidget(self.add_shot_btn)

        self.main_h_splitter.addWidget(self.shots_panel)

        # Center: Tab widget with 3 views:
        #   Tab 0: Classic 1080p canvas (dark background, overview)
        #   Tab 1: Multi-camera render strip (white canvas, render-accurate)
        #   Tab 2: Element Extraction editor
        self.center_tabs = QTabWidget()
        self.center_tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background-color: #F5F6F8; }
            QTabBar::tab { background-color: #FFFFFF; color: #475467; padding: 6px 16px; font-size: 12px; border: 1px solid #FAFBFC; border-bottom: none; }
            QTabBar::tab:selected { background-color: #F5F6F8; color: #101828; font-weight: bold; border-top: 2px solid #4F46E5; }
            QTabBar::tab:hover { background-color: #FAFBFC; color: #101828; }
        """)

        # Tab 0: Canvas
        self.canvas_scene = StudioCanvasScene(self)
        self.canvas_scene.element_selected.connect(self._on_item_selected_on_canvas)
        self.canvas_scene.element_geometry_changed.connect(self._on_item_geometry_changed)
        self.canvas_scene.selection_cleared.connect(self._on_selection_cleared)
        self.canvas_view = StudioCanvasView(self.canvas_scene, self)
        self.center_tabs.addTab(self.canvas_view, "Canvas (Overview)")

        # Tab 1: Multi-camera render strip
        self.camera_render_strip = MultiCameraRenderStrip()
        self.camera_render_strip.element_moved.connect(self._on_camera_element_moved)
        self.camera_render_strip.element_selected.connect(self._on_item_selected_from_timeline)
        self.camera_render_strip.camera_selected.connect(self._select_shot)
        self.center_tabs.addTab(self.camera_render_strip, "Camera Views (Render-Accurate)")

        # Tab 2: Extraction
        self.extraction_panel = ElementExtractionPanel()
        self.extraction_panel.extraction_completed.connect(self._on_extraction_completed)
        self.extraction_panel.element_selected.connect(self._on_item_selected_from_timeline)
        self.center_tabs.addTab(self.extraction_panel, "Element Extraction")
        self.center_tabs.currentChanged.connect(self._on_center_tab_changed)

        self.main_h_splitter.addWidget(self.center_tabs)

        # Right: Contextual Properties Inspector (collapsible at COMPACT)
        self.inspector = StudioInspectorPanel(self)
        self.inspector.property_changed.connect(self._on_inspector_prop_changed)
        self.inspector.remove_item_requested.connect(self._remove_element)
        self.inspector.reset_to_auto_requested.connect(self._reset_item_to_automatic)
        self.main_h_splitter.addWidget(self.inspector)

        self.main_h_splitter.setStretchFactor(0, 1)
        self.main_h_splitter.setStretchFactor(1, 6)
        self.main_h_splitter.setStretchFactor(2, 2)

        # =====================================================================
        # 3. VERTICAL SPLITTER: Top Workspace + Bottom Sequencer Timeline
        # =====================================================================
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.addWidget(self.main_h_splitter)

        # Timeline Sequencer View
        self.timeline_view = StudioTimelineView(self)
        self.timeline_view.time_scrubbed.connect(self.scrub_to_time)
        self.timeline_view.element_timing_changed.connect(self._on_element_timing_changed)
        self.timeline_view.sfx_timing_changed.connect(self._on_sfx_timing_changed)
        self.timeline_view.element_selected.connect(self._on_item_selected_from_timeline)
        self.timeline_view.word_clicked.connect(self._on_word_clicked)

        self.v_splitter.addWidget(self.timeline_view)
        self.v_splitter.setStretchFactor(0, 4)
        self.v_splitter.setStretchFactor(1, 2)

        # Set minimum timeline height so it stays usable
        self.timeline_view.setMinimumHeight(150)

        root_layout.addWidget(self.v_splitter)

        # Apply initial responsive layout
        self._apply_responsive_layout()

    # =========================================================================
    # DATA LOADING & SYNCHRONIZATION
    # =========================================================================

    def load_section(self, project: ProjectState, section_id: str) -> None:
        """Load section artifacts, elements layout, voice transcript, and cameras."""
        self.current_project = project
        self.active_section_id = section_id
        self.is_dirty = False
        self.dirty_lbl.setVisible(False)
        self.stop_playback()

        # Locate section directory
        if project.metadata and project.metadata.get("project_path"):
            cand = Path(project.metadata["project_path"]) / "sections" / section_id
            self.section_path = cand if cand.is_dir() else None

        if not self.section_path:
            from core.config.settings import SECTIONS_DIR, PROJECT_CONTENT_DIR
            cand1 = PROJECT_CONTENT_DIR / project.project_id / "sections" / section_id
            cand2 = SECTIONS_DIR / project.project_id / section_id
            cand3 = SECTIONS_DIR / section_id
            if cand1.is_dir():
                self.section_path = cand1
            elif cand2.is_dir():
                self.section_path = cand2
            elif cand3.is_dir():
                self.section_path = cand3

        sec_title = f"{section_id}"
        if section_id in project.sections:
            sec_title = f"{section_id} — {project.sections[section_id].title}"
        self.section_title_lbl.setText(f"<b>Section: {sec_title}</b>")

        self._load_data_from_disk()
        self._populate_canvas_and_timeline()

        # Load extraction panel with this section path
        if self.section_path:
            self.extraction_panel.load_section(self.section_path)


    def _load_data_from_disk(self) -> None:
        """Loads elements, camera zones, SFX cues, and Whisper word timestamps from disk."""
        if not self.section_path or not self.section_path.is_dir():
            return

        self.elements_data.clear()
        self.cameras_data.clear()
        self.sfx_cues.clear()
        self.words_data.clear()
        self.auto_defaults_backup.clear()

        # 1. Load placed elements layout if exists
        layout_file = self.section_path / "placed_elements_layout.json"
        if layout_file.exists():
            try:
                with open(layout_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    raw_elems = data.get("placed_elements", data.get("elements", []))
                    if isinstance(raw_elems, list):
                        for el in raw_elems:
                            if isinstance(el, dict):
                                eid = el.get("id", el.get("element_id", el.get("aid", "")))
                                if eid:
                                    el.setdefault("start_time", 0.5)
                                    el.setdefault("draw_duration", 0.8)
                                    el.setdefault("hold_duration", 2.0)
                                    el.setdefault("ownership", "AUTO")
                                    self.elements_data[eid] = el
                    elif isinstance(raw_elems, dict):
                        for k, v in raw_elems.items():
                            if isinstance(v, list):
                                for el in v:
                                    if isinstance(el, dict):
                                        eid = el.get("id", el.get("element_id", el.get("aid", "")))
                                        if eid:
                                            el.setdefault("start_time", 0.5)
                                            el.setdefault("draw_duration", 0.8)
                                            el.setdefault("hold_duration", 2.0)
                                            el.setdefault("ownership", "AUTO")
                                            self.elements_data[eid] = el
                            elif isinstance(v, dict):
                                eid = v.get("id", v.get("element_id", v.get("aid", k)))
                                if eid:
                                    v.setdefault("start_time", 0.5)
                                    v.setdefault("draw_duration", 0.8)
                                    v.setdefault("hold_duration", 2.0)
                                    v.setdefault("ownership", "AUTO")
                                    self.elements_data[eid] = v

                    # Load camera zones if present
                    zones = data.get("zones", {})
                    if isinstance(zones, dict) and zones:
                        cur_cam_start = 0.0
                        for zid, zdata in zones.items():
                            if isinstance(zdata, dict):
                                cam_pos = zdata.get("cam_pos", [960.0, 540.0])
                                cx = cam_pos[0] if len(cam_pos) > 0 else 960.0
                                cy = cam_pos[1] if len(cam_pos) > 1 else 540.0
                                zoom = float(zdata.get("zoom", 1.0))
                                dur = float(zdata.get("duration", 5.0))
                                self.cameras_data[zid] = {
                                    "name": zid,
                                    "center_x": cx,
                                    "center_y": cy,
                                    "zoom": zoom,
                                    "start_time": cur_cam_start,
                                    "duration": dur,
                                    "ownership": "AUTO",
                                }
                                cur_cam_start += dur
            except Exception as e:
                print(f"[StudioEditor] Error reading layout file: {e}")

        # 2. Fallback to assets/metadata.json if layout empty
        if not self.elements_data:
            meta_file = self.section_path / "assets" / "metadata.json"
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        mdata = json.load(f)
                        raw_assets = mdata.get("assets", mdata)
                        col_x, row_y = 120, 120
                        step_t = 0.5
                        for aid, adata in raw_assets.items():
                            if not isinstance(adata, dict):
                                continue
                            self.elements_data[aid] = {
                                "id": aid,
                                "file": adata.get("file", f"{aid}.png"),
                                "x": col_x,
                                "y": row_y,
                                "scale": 1.0,
                                "start_time": step_t,
                                "draw_duration": 0.8,
                                "hold_duration": 2.5,
                                "animation_style": "Outside-In Pen",
                                "anchor_word": adata.get("label", aid),
                                "ownership": "AUTO",
                            }
                            step_t += 2.0
                            col_x += 240
                            if col_x > 1400:
                                col_x, row_y = 120, row_y + 220
                except Exception as e:
                    print(f"[StudioEditor] Error reading metadata: {e}")

        # 3. Load Whisper word timestamps if available
        whisper_file = self.section_path / "whisper_words.json"
        if whisper_file.exists():
            try:
                with open(whisper_file, "r", encoding="utf-8") as f:
                    wdata = json.load(f)
                    for item in wdata.get("words", []):
                        w_text = item.get("word", "")
                        w_s = float(item.get("start", 0.0))
                        w_e = float(item.get("end", w_s + 0.3))
                        self.words_data.append((w_text, w_s, w_e))
            except Exception:
                pass

        # 4. Load or synthesize SFX cues
        sfx_file = self.section_path / "sfx_cues.json"
        if sfx_file.exists():
            try:
                with open(sfx_file, "r", encoding="utf-8") as f:
                    sdata = json.load(f)
                    for cue in sdata.get("cues", []):
                        cid = cue.get("id", f"sfx_{len(self.sfx_cues)+1}")
                        self.sfx_cues[cid] = {
                            "id": cid,
                            "timestamp": float(cue.get("timestamp", 0.0)),
                            "sfx_type": cue.get("type", "pop"),
                            "gain": float(cue.get("gain", 1.0)),
                            "ownership": cue.get("ownership", "AUTO"),
                        }
            except Exception:
                pass

        # Generate automatic SFX cues aligned with element draw starts if none existed
        if not self.sfx_cues and self.elements_data:
            idx = 1
            for eid, edata in self.elements_data.items():
                t = float(edata.get("start_time", 0.5))
                cid = f"sfx_cue_{idx:02d}"
                self.sfx_cues[cid] = {
                    "id": cid,
                    "timestamp": t,
                    "sfx_type": "pop" if idx % 2 == 1 else "whoosh",
                    "gain": 1.0,
                    "ownership": "AUTO",
                }
                idx += 1

        # 5. Setup Default Cameras if none found
        if not self.cameras_data:
            self.cameras_data = {
                "Camera 01": {"name": "Camera 01", "center_x": 960, "center_y": 540, "zoom": 1.0, "start_time": 0.0, "duration": 6.0, "ownership": "AUTO"},
                "Camera 02": {"name": "Camera 02", "center_x": 600, "center_y": 400, "zoom": 1.25, "start_time": 6.0, "duration": 8.0, "ownership": "AUTO"},
            }

        # Backup auto defaults for "Reset to Auto"
        for eid, ed in self.elements_data.items():
            self.auto_defaults_backup[eid] = dict(ed)

    def _populate_canvas_and_timeline(self) -> None:
        """Render all loaded assets on the 1080p canvas and populate the 4 sequencer tracks."""
        self.canvas_scene.clear()
        self.canvas_items.clear()
        self._pixmaps_cache: Dict[str, QPixmap] = {}

        # Calculate total section duration
        max_t = 15.0
        for edata in self.elements_data.values():
            end_t = float(edata.get("start_time", 0.0)) + float(edata.get("draw_duration", 0.8)) + float(edata.get("hold_duration", 2.0))
            max_t = max(max_t, end_t)
        for cdata in self.cameras_data.values():
            end_t = float(cdata.get("start_time", 0.0)) + float(cdata.get("duration", 4.0))
            max_t = max(max_t, end_t)
        if self.words_data:
            max_t = max(max_t, self.words_data[-1][2] + 1.0)

        self.section_duration = round(max_t + 1.5, 1)

        # 1. Rebuild Shots strip buttons
        self._rebuild_shots_ui()

        # 2. Add Camera Frustum Item to Canvas
        first_cam_name = next(iter(self.cameras_data.keys()), "Camera 01")
        self.active_camera_name = first_cam_name
        self.camera_frustum = CameraFrustumItem(
            camera_name=first_cam_name,
            rect=QRectF(0, 0, 1920, 1080),
        )
        self.canvas_scene.addItem(self.camera_frustum)

        # 3. Add Visual Elements to Canvas
        for eid, edata in self.elements_data.items():
            if not isinstance(edata, dict):
                continue
            img_file = edata.get("file", f"{edata.get('aid', eid)}.png")
            img_path = self.section_path / "assets" / img_file if self.section_path else Path(img_file)
            if not img_path.exists() and self.section_path:
                img_path = self.section_path / img_file

            pix = QPixmap(str(img_path)) if img_path.exists() else QPixmap()
            if pix.isNull():
                pix = QPixmap(200, 150)
                pix.fill(QColor("#4F46E5"))

            item = CanvasElementItem(
                element_id=eid,
                pixmap=pix,
                initial_x=float(edata.get("x", edata.get("cx", 100))),
                initial_y=float(edata.get("y", edata.get("cy", 100))),
                scale_factor=float(edata.get("scale", 1.0)),
            )
            item.start_time = float(edata.get("start_time", 0.5))
            item.draw_duration = float(edata.get("draw_duration", 0.8))
            item.hold_duration = float(edata.get("hold_duration", 2.0))
            item.animation_style = edata.get("animation_style", "Outside-In Pen")
            item.anchor_word = edata.get("anchor_word", edata.get("aid", ""))

            self.canvas_scene.addItem(item)
            self.canvas_items[eid] = item
            self._pixmaps_cache[eid] = pix

        # 4. Build Multi-track Timeline Items
        timeline_tracks: List[TimelineTrackItem] = []

        # (A) VOICE TRACK
        voice_item = TimelineTrackItem(
            item_id="voice_track",
            label="Original Voice Narration",
            start_time=0.0,
            duration=self.section_duration - 1.0,
            track_group="VOICE",
            color_hex="#4F46E5",
            is_locked=True,
        )
        timeline_tracks.append(voice_item)

        # (B) VISUAL ASSET TRACKS
        for eid, edata in self.elements_data.items():
            st = float(edata.get("start_time", 0.5))
            dd = float(edata.get("draw_duration", 0.8))
            hd = float(edata.get("hold_duration", 2.0))
            ownership = edata.get("ownership", "AUTO")

            t_item = TimelineTrackItem(
                item_id=eid,
                label=eid,
                start_time=st,
                duration=dd + hd,
                track_group="VISUALS",
                draw_duration=dd,
                hold_duration=hd,
                ownership=ownership,
                color_hex="#4F46E5",
                anchor_word=edata.get("anchor_word", ""),
            )
            timeline_tracks.append(t_item)

        # (C) SFX CUES
        for cid, cdata in self.sfx_cues.items():
            st = float(cdata.get("timestamp", 0.0))
            ownership = cdata.get("ownership", "AUTO")
            sfx_t = cdata.get("sfx_type", "pop")

            s_item = TimelineTrackItem(
                item_id=cid,
                label=cid,
                start_time=st,
                duration=0.5,
                track_group="SFX",
                ownership=ownership,
                sfx_type=sfx_t,
                color_hex="#16A34A",
            )
            timeline_tracks.append(s_item)

        # (D) CAMERA SHOTS
        for cid, cdata in self.cameras_data.items():
            st = float(cdata.get("start_time", 0.0))
            dur = float(cdata.get("duration", 4.0))

            c_item = TimelineTrackItem(
                item_id=cid,
                label=cid,
                start_time=st,
                duration=dur,
                track_group="CAMERA",
                color_hex="#D97706",
            )
            timeline_tracks.append(c_item)

        self.timeline_view.set_duration(self.section_duration)
        self.timeline_view.set_words(self.words_data)
        self.timeline_view.set_tracks(timeline_tracks)

        # 5. Rebuild multi-camera render strip (render-accurate white canvas views)
        self.camera_render_strip.rebuild_cameras(
            cameras_data=self.cameras_data,
            elements_data=self.elements_data,
            pixmaps=self._pixmaps_cache,
            playhead_time=self.playhead_time,
        )

        # Jump playhead to start
        self.scrub_to_time(0.0)

    def resizeEvent(self, event) -> None:
        """Adapt panel proportions when the window is resized."""
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        """Update panel visibility, toolbar density, and splitter proportions."""
        bp = get_breakpoint(self)
        total_w = self.main_h_splitter.width()

        if bp == Breakpoint.COMPACT:
            # Canvas stays primary. Secondary panels become toolbar drawers.
            shots_visible = self.shots_toggle_btn.isChecked()
            inspector_visible = self.inspector_toggle_btn.isChecked()
            self.shots_toggle_btn.setVisible(True)
            self.inspector_toggle_btn.setVisible(True)
            self.shots_panel.setVisible(shots_visible)
            self.inspector.setVisible(inspector_visible)
            self.more_btn.setVisible(True)
            for widget in self._toolbar_overflow_widgets:
                widget.setVisible(False)
            if total_w > 0:
                self.main_h_splitter.setSizes(
                    compact_h_splitter_sizes(
                        total_w,
                        shots_visible=shots_visible,
                        inspector_visible=inspector_visible,
                    )
                )
        elif bp == Breakpoint.MEDIUM:
            # Keep essential controls inline; move creative/expert tools into More.
            self.shots_toggle_btn.setVisible(False)
            self.inspector_toggle_btn.setVisible(False)
            self.shots_panel.setVisible(True)
            self.inspector.setVisible(True)
            self.more_btn.setVisible(True)
            for widget in self._toolbar_overflow_widgets:
                widget.setVisible(False)
        else:
            self.shots_toggle_btn.setVisible(False)
            self.inspector_toggle_btn.setVisible(False)
            self.shots_panel.setVisible(True)
            self.inspector.setVisible(True)
            self.more_btn.setVisible(False)
            for widget in self._toolbar_overflow_widgets:
                widget.setVisible(True)

        if total_w > 0 and bp != Breakpoint.COMPACT:
            self.main_h_splitter.setSizes(h_splitter_sizes(total_w, widget=self))
        if self.v_splitter.height() > 0:
            self.v_splitter.setSizes(v_splitter_sizes(self.v_splitter.height(), widget=self))

        # Keep the inspector's internal width aligned with the current profile.
        if bp != Breakpoint.COMPACT:
            self.inspector.setMinimumWidth(240)
            self.inspector.setMaximumWidth(inspector_panel_width(widget=self) + 40)
            self.shots_panel.setMaximumWidth(shots_panel_width(widget=self) + 20)

    def _toggle_shots_panel(self) -> None:
        """Show/hide the shots panel (drawer-based toggle at compact breakpoint)."""
        show = self.shots_toggle_btn.isChecked()
        self.shots_panel.setVisible(show)
        self.main_h_splitter.setSizes(
            compact_h_splitter_sizes(
                self.main_h_splitter.width(),
                shots_visible=show,
                inspector_visible=self.inspector_toggle_btn.isChecked(),
            )
        )

    def _toggle_inspector_panel(self) -> None:
        """Show/hide the inspector panel (drawer-based toggle at compact breakpoint)."""
        show = self.inspector_toggle_btn.isChecked()
        self.inspector.setVisible(show)
        self.main_h_splitter.setSizes(
            compact_h_splitter_sizes(
                self.main_h_splitter.width(),
                shots_visible=self.shots_toggle_btn.isChecked(),
                inspector_visible=show,
            )
        )

    def _rebuild_shots_ui(self) -> None:
        """Rebuilds the vertical list of shot/camera buttons in the left panel."""
        for b in self.shots_btn_group.buttons():
            self.shots_btn_group.removeButton(b)
            b.deleteLater()

        for cam_name in self.cameras_data.keys():
            btn = QPushButton(f"🎥 {cam_name}")
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton { background-color: #FAFBFC; color: #101828; text-align: left; padding: 6px 10px; font-size: 12px; border-radius: 4px; }
                QPushButton:checked { background-color: #D97706; color: #FFFFFF; font-weight: bold; }
            """)
            if cam_name == self.active_camera_name:
                btn.setChecked(True)
            btn.clicked.connect(lambda _, cn=cam_name: self._select_shot(cn))
            self.shots_btn_group.addButton(btn)
            self.shots_btn_container.addWidget(btn)

    # =========================================================================
    # LIVE PLAYBACK ENGINE & TRANSPORT
    # =========================================================================

    def toggle_playback(self) -> None:
        if self.is_playing:
            self.pause_playback()
        else:
            self.start_playback()

    def start_playback(self) -> None:
        sv = scaled_stylesheet_values()
        self.is_playing = True
        self.play_pause_btn.setText("⏸ Pause")
        self.play_pause_btn.setStyleSheet(f"background-color: #D97706; color: #FFFFFF; font-weight: bold; padding: {sv['pad_sm']}px {sv['pad_lg']}px; font-size: {sv['body_font']}px;")

        # If at end, loop back
        if self.playhead_time >= self.section_duration:
            self.playhead_time = 0.0

        self.playback_timer.start()

    def pause_playback(self) -> None:
        sv = scaled_stylesheet_values()
        self.is_playing = False
        self.playback_timer.stop()
        self.play_pause_btn.setText("▶ Play")
        self.play_pause_btn.setStyleSheet(f"background-color: #16A34A; color: #FFFFFF; font-weight: bold; padding: {sv['pad_sm']}px {sv['pad_lg']}px; font-size: {sv['body_font']}px;")

    def stop_playback(self) -> None:
        self.pause_playback()
        self.scrub_to_time(0.0)

    def _on_playback_tick(self) -> None:
        """30 FPS playback advance updating playhead and canvas visuals."""
        dt = 0.033
        new_time = self.playhead_time + dt

        # Scope-aware looping
        if self.preview_scope == "Shot":
            cam = self.cameras_data.get(self.active_camera_name, {})
            start = float(cam.get("start_time", 0.0))
            end = start + float(cam.get("duration", 4.0))
            if new_time >= end:
                new_time = start
        else:
            if new_time >= self.section_duration:
                new_time = 0.0  # Loop playback

        self.playhead_time = new_time
        self.timeline_view.set_playhead_time(new_time)
        self.canvas_scene.update_playhead(new_time, is_playing=True)
        self.camera_render_strip.update_playhead(new_time)

    def scrub_to_time(self, time_sec: float) -> None:
        """Scrub playhead and jump canvas to exact visual timing state without rendering."""
        self.playhead_time = time_sec
        self.timeline_view.set_playhead_time(time_sec)
        self.canvas_scene.update_playhead(time_sec, is_playing=self.is_playing)
        self.camera_render_strip.update_playhead(time_sec)

        # Update active camera frame if time crosses camera boundary
        for cam_name, cdata in self.cameras_data.items():
            cs = float(cdata.get("start_time", 0.0))
            cd = float(cdata.get("duration", 4.0))
            if cs <= time_sec <= cs + cd:
                if self.active_camera_name != cam_name:
                    self.active_camera_name = cam_name
                    self._highlight_shot_button(cam_name)
                    if self.camera_frustum:
                        self.camera_frustum.camera_name = cam_name
                break

    def set_preview_scope(self, scope: str) -> None:
        """Switches playback scope without leaving the Studio."""
        self.preview_scope = scope
        if scope == "Shot":
            cam = self.cameras_data.get(self.active_camera_name, {})
            self.scrub_to_time(float(cam.get("start_time", 0.0)))

    # =========================================================================
    # SELECTION & DIRECT MANIPULATION
    # =========================================================================

    def _select_shot(self, camera_name: str) -> None:
        """Select a camera shot: focuses frustum, jumps playhead, inspects camera."""
        self.active_camera_name = camera_name
        self._highlight_shot_button(camera_name)

        if camera_name in self.cameras_data:
            cdata = self.cameras_data[camera_name]
            st = float(cdata.get("start_time", 0.0))
            self.scrub_to_time(st)
            if self.camera_frustum:
                self.camera_frustum.camera_name = camera_name

            self.inspector.inspect_camera(camera_name, cdata)

    def _highlight_shot_button(self, camera_name: str) -> None:
        for b in self.shots_btn_group.buttons():
            if camera_name in b.text():
                b.setChecked(True)
                break

    def _on_item_selected_on_canvas(self, element_id: str) -> None:
        """User clicked element on canvas -> select in timeline & inspector."""
        if element_id in self.elements_data:
            self.inspector.inspect_element(element_id, self.elements_data[element_id])
            self.timeline_view.canvas_widget.selected_item_id = element_id
            self.timeline_view.canvas_widget.update()

    def _on_item_selected_from_timeline(self, item_id: str) -> None:
        """User clicked track in timeline -> select on canvas & inspector."""
        if item_id in self.elements_data:
            for eid, itm in self.canvas_items.items():
                itm.setSelected(eid == item_id)
            self.inspector.inspect_element(item_id, self.elements_data[item_id])
        elif item_id in self.sfx_cues:
            self.inspector.inspect_sfx(item_id, self.sfx_cues[item_id])
        elif item_id in self.cameras_data:
            self._select_shot(item_id)

    def _on_word_clicked(self, word: str, start_time: float) -> None:
        """User clicked spoken word in Voice track -> jump playhead & highlight linked asset."""
        self.scrub_to_time(start_time)
        # Check if any element is anchored to this word
        for eid, edata in self.elements_data.items():
            anchor = edata.get("anchor_word", "")
            if anchor and (anchor in word or word in anchor):
                self._on_item_selected_from_timeline(eid)
                break

    def _on_item_geometry_changed(self, element_id: str, x: float, y: float, scale: float) -> None:
        """Live direct manipulation on canvas updates state immediately."""
        if element_id in self.elements_data:
            self.elements_data[element_id]["x"] = round(x, 1)
            self.elements_data[element_id]["y"] = round(y, 1)
            self.elements_data[element_id]["scale"] = round(scale, 2)
            self.elements_data[element_id]["ownership"] = "USER_OVERRIDE"
            self.inspector.update_position(x, y, scale)
            self._mark_dirty()

    def _on_inspector_prop_changed(self, item_id: str, prop_name: str, value: Any) -> None:
        """Inspector change updates canvas & timeline immediately."""
        if item_id in self.elements_data:
            self.elements_data[item_id][prop_name] = value
            self.elements_data[item_id]["ownership"] = "USER_OVERRIDE"

            if item_id in self.canvas_items:
                item = self.canvas_items[item_id]
                if prop_name == "x":
                    item.setX(float(value))
                elif prop_name == "y":
                    item.setY(float(value))
                elif prop_name == "scale":
                    item.setScale(float(value))
                elif prop_name == "draw_duration":
                    item.draw_duration = float(value)
                elif prop_name == "hold_duration":
                    item.hold_duration = float(value)
                elif prop_name == "start_time":
                    item.start_time = float(value)

            self._mark_dirty()
            # Refresh timeline track
            self._refresh_timeline_tracks()

        elif item_id in self.sfx_cues:
            self.sfx_cues[item_id][prop_name] = value
            self.sfx_cues[item_id]["ownership"] = "USER_OVERRIDE"
            self._mark_dirty()
            self._refresh_timeline_tracks()

    def _on_element_timing_changed(self, item_id: str, start_time: float, duration: float) -> None:
        """Direct manipulation dragging/resizing in timeline."""
        if item_id in self.elements_data:
            self.elements_data[item_id]["start_time"] = start_time
            ratio = self.elements_data[item_id].get("draw_duration", 0.8) / max(0.1, duration)
            self.elements_data[item_id]["draw_duration"] = round(duration * ratio, 2)
            self.elements_data[item_id]["hold_duration"] = round(duration * (1.0 - ratio), 2)
            self.elements_data[item_id]["ownership"] = "USER_OVERRIDE"

            if item_id in self.canvas_items:
                self.canvas_items[item_id].start_time = start_time
                self.canvas_items[item_id].draw_duration = self.elements_data[item_id]["draw_duration"]
                self.canvas_items[item_id].hold_duration = self.elements_data[item_id]["hold_duration"]

            if self.inspector.current_item_id == item_id:
                self.inspector.inspect_element(item_id, self.elements_data[item_id])

            self._mark_dirty()

    def _on_sfx_timing_changed(self, cue_id: str, new_time: float) -> None:
        """Direct dragging of SFX cue along timeline."""
        if cue_id in self.sfx_cues:
            self.sfx_cues[cue_id]["timestamp"] = new_time
            self.sfx_cues[cue_id]["ownership"] = "USER_OVERRIDE"
            if self.inspector.current_item_id == cue_id:
                self.inspector.inspect_sfx(cue_id, self.sfx_cues[cue_id])
            self._mark_dirty()

    def _reset_item_to_automatic(self, item_id: str) -> None:
        """Restores AI/deterministic default scheduling for overridden items."""
        if item_id in self.auto_defaults_backup:
            self.elements_data[item_id] = dict(self.auto_defaults_backup[item_id])
            self.elements_data[item_id]["ownership"] = "AUTO"
            self.inspector.inspect_element(item_id, self.elements_data[item_id])
            self._populate_canvas_and_timeline()
            self._mark_dirty()

    def _mark_dirty(self) -> None:
        self.is_dirty = True
        self.dirty_lbl.setVisible(True)

    def _refresh_timeline_tracks(self) -> None:
        """Update timeline items without rebuilding the whole scene."""
        tracks = self.timeline_view.canvas_widget.tracks
        for t in tracks:
            if t.item_id in self.elements_data:
                ed = self.elements_data[t.item_id]
                t.start_time = float(ed.get("start_time", 0.5))
                t.draw_duration = float(ed.get("draw_duration", 0.8))
                t.hold_duration = float(ed.get("hold_duration", 2.0))
                t.duration = t.draw_duration + t.hold_duration
                t.ownership = ed.get("ownership", "AUTO")
            elif t.item_id in self.sfx_cues:
                sd = self.sfx_cues[t.item_id]
                t.start_time = float(sd.get("timestamp", 0.0))
                t.ownership = sd.get("ownership", "AUTO")
        self.timeline_view.canvas_widget.update()

    def _on_selection_cleared(self) -> None:
        self.inspector.show_empty()

    # =========================================================================
    # TAB NAVIGATION SHORTCUTS
    # =========================================================================

    def _switch_to_cameras_tab(self) -> None:
        """Switch to the render-accurate camera views tab and refresh it."""
        if not hasattr(self, "_pixmaps_cache"):
            self._pixmaps_cache = {}
        self.camera_render_strip.rebuild_cameras(
            cameras_data=self.cameras_data,
            elements_data=self.elements_data,
            pixmaps=self._pixmaps_cache,
            playhead_time=self.playhead_time,
        )
        self.center_tabs.setCurrentIndex(1)

    def _switch_to_extraction_tab(self) -> None:
        """Switch to the Element Extraction tab."""
        self.center_tabs.setCurrentIndex(2)
        if self.section_path and not self.extraction_panel.section_path:
            self.extraction_panel.load_section(self.section_path)

    # =========================================================================
    # CAMERA RENDER STRIP ELEMENT MOVE HANDLER
    # =========================================================================

    def _on_camera_element_moved(self, element_id: str, new_x: float, new_y: float) -> None:
        """Element dragged inside a camera view — sync position back to elements_data and canvas."""
        if element_id in self.elements_data:
            self.elements_data[element_id]["x"] = round(new_x, 1)
            self.elements_data[element_id]["y"] = round(new_y, 1)
            self.elements_data[element_id]["ownership"] = "USER_OVERRIDE"
            # Sync canvas item position
            if element_id in self.canvas_items:
                self.canvas_items[element_id].setX(new_x)
                self.canvas_items[element_id].setY(new_y)
            # Update inspector if this element is inspected
            self.inspector.update_position(new_x, new_y, float(self.elements_data[element_id].get("scale", 1.0)))
            # Update all other camera views
            self.camera_render_strip.update_elements(self.elements_data, self._pixmaps_cache)
            self._mark_dirty()

    # =========================================================================
    # EXTRACTION COMPLETED
    # =========================================================================

    def _on_extraction_completed(self) -> None:
        """Called after DynamicStoryboardExtractor finishes — reload everything."""
        if self.section_path:
            self._load_data_from_disk()
            self._populate_canvas_and_timeline()


    # =========================================================================
    # CONTENT CREATION & SAVING
    # =========================================================================

    def _add_text_overlay(self) -> None:

        text, ok = QInputDialog.getText(self, "Add Text to Canvas", "Enter text content (Arabic/English):")
        if ok and text.strip():
            tid = f"text_{len(self.elements_data) + 1:02d}"
            txt_item = CanvasTextItem(text_id=tid, text=text.strip(), initial_x=400, initial_y=300)
            self.canvas_scene.addItem(txt_item)
            self.elements_data[tid] = {
                "id": tid,
                "text": text.strip(),
                "x": 400,
                "y": 300,
                "scale": 1.0,
                "start_time": self.playhead_time,
                "draw_duration": 1.0,
                "hold_duration": 3.0,
                "ownership": "USER_OVERRIDE",
            }
            self._populate_canvas_and_timeline()
            self._mark_dirty()

    def _add_sfx_cue(self) -> None:
        types = ["pop", "whoosh", "pencil_write", "chime", "click"]
        sfx_t, ok = QInputDialog.getItem(self, "Add SFX Cue", "Select SFX type:", types, 0, False)
        if ok and sfx_t:
            cid = f"sfx_cue_{len(self.sfx_cues) + 1:02d}"
            self.sfx_cues[cid] = {
                "id": cid,
                "timestamp": self.playhead_time,
                "sfx_type": sfx_t,
                "gain": 1.0,
                "ownership": "USER_OVERRIDE",
            }
            self._populate_canvas_and_timeline()
            self._mark_dirty()

    def _add_camera_shot(self) -> None:
        cam_num = len(self.cameras_data) + 1
        cam_name = f"Camera {cam_num:02d}"
        last_cam = list(self.cameras_data.values())[-1] if self.cameras_data else {}
        st = float(last_cam.get("start_time", 0.0)) + float(last_cam.get("duration", 4.0))

        self.cameras_data[cam_name] = {
            "name": cam_name,
            "center_x": 960,
            "center_y": 540,
            "zoom": 1.0,
            "start_time": st,
            "duration": 4.0,
            "ownership": "USER_OVERRIDE",
        }
        self._populate_canvas_and_timeline()
        self._select_shot(cam_name)
        self._mark_dirty()

    def _remove_element(self, item_id: str) -> None:
        if item_id in self.elements_data:
            del self.elements_data[item_id]
            if item_id in self.canvas_items:
                self.canvas_scene.removeItem(self.canvas_items[item_id])
                del self.canvas_items[item_id]
        elif item_id in self.sfx_cues:
            del self.sfx_cues[item_id]

        self._populate_canvas_and_timeline()
        self._mark_dirty()

    def save_layout(self, show_dialog: bool = True) -> None:
        """Persists current visual composition and SFX cues to disk."""
        if not self.section_path:
            if show_dialog:
                QMessageBox.warning(self, "Save Error", "No active section directory resolved.")
            return

        layout_payload = {
            "section_id": self.active_section_id,
            "canvas_width": 1920,
            "canvas_height": 1080,
            "duration": self.section_duration,
            "placed_elements": list(self.elements_data.values()),
            "cameras": list(self.cameras_data.values()),
        }

        # 1. Save placed_elements_layout.json
        out_layout = self.section_path / "placed_elements_layout.json"
        try:
            with open(out_layout, "w", encoding="utf-8") as f:
                json.dump(layout_payload, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if show_dialog:
                QMessageBox.critical(self, "Save Failed", f"Failed saving layout: {e}")
            return

        # 2. Save sfx_cues.json (independent editable audio cues)
        sfx_payload = {
            "section_id": self.active_section_id,
            "cues": list(self.sfx_cues.values()),
        }
        out_sfx = self.section_path / "sfx_cues.json"
        try:
            with open(out_sfx, "w", encoding="utf-8") as f:
                json.dump(sfx_payload, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        # 3. Bump revision in project state store
        if self.current_project and self.active_section_id:
            sec = self.current_project.sections.get(self.active_section_id)
            if sec:
                sec.increment_revision()
                self.state_store.save_state(self.current_project)

        self.is_dirty = False
        self.dirty_lbl.setVisible(False)
        if show_dialog:
            QMessageBox.information(
                self,
                "Layout Saved",
                f"Successfully saved {len(self.elements_data)} elements and {len(self.sfx_cues)} SFX cues to:\n{out_layout.name}",
            )

    def _on_render_clicked(self) -> None:
        """Directly triggers render of the current section with immediate feedback."""
        if self.is_dirty:
            self.save_layout()

        if self.active_section_id:
            self.render_section_requested.emit(self.active_section_id)
            QMessageBox.information(
                self,
                "Render Initiated",
                f"Section '{self.active_section_id}' render pipeline initiated using active layout.",
            )

    def _on_back_clicked(self) -> None:
        """Handle returning to Sections Roster, prompting to save if dirty."""
        if self.is_dirty:
            reply = QMessageBox.question(
                self,
                "تعديلات غير محفوظة (Unsaved Changes)",
                "لديك تعديلات غير محفوظة في السيكشن الحالي.\nهل ترغب في حفظ التغييرات قبل الرجوع إلى جدول السيكشنات؟",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if reply == QMessageBox.StandardButton.Save:
                self.save_layout(show_dialog=False)
                self.back_requested.emit()
            elif reply == QMessageBox.StandardButton.Discard:
                self.is_dirty = False
                self.dirty_lbl.setVisible(False)
                self.back_requested.emit()
            else:
                return
        else:
            self.back_requested.emit()

    def _on_projects_clicked(self) -> None:
        """Handle returning to Projects Browser, prompting to save if dirty."""
        if self.is_dirty:
            reply = QMessageBox.question(
                self,
                "تعديلات غير محفوظة (Unsaved Changes)",
                "لديك تعديلات غير محفوظة في السيكشن الحالي.\nهل ترغب في حفظ التغييرات قبل الرجوع إلى قائمة المشاريع؟",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if reply == QMessageBox.StandardButton.Save:
                self.save_layout(show_dialog=False)
                self.projects_requested.emit()
            elif reply == QMessageBox.StandardButton.Discard:
                self.is_dirty = False
                self.dirty_lbl.setVisible(False)
                self.projects_requested.emit()
            else:
                return
        else:
            self.projects_requested.emit()

    def _switch_to_extraction_tab(self) -> None:
        """Switch central tabs to the Element Extraction panel."""
        self.center_tabs.setCurrentIndex(2)

    def _switch_to_cameras_tab(self) -> None:
        """Switch central tabs to the Multi-Camera Render Strip."""
        self.center_tabs.setCurrentIndex(1)

    def _on_center_tab_changed(self, index: int) -> None:
        """Contextual UI: show/hide toolbar buttons to prevent crowding based on active tab."""
        is_extraction = (index == 2)
        is_canvas = (index == 0)

        # In extraction tab, hide playback & canvas-specific controls to avoid overcrowding
        self.jump_start_btn.setVisible(not is_extraction)
        self.play_pause_btn.setVisible(not is_extraction)
        self.stop_btn.setVisible(not is_extraction)
        self.scope_lbl.setVisible(not is_extraction)
        for btn in getattr(self, "scope_buttons", []):
            btn.setVisible(not is_extraction)

        self.add_text_btn.setVisible(is_canvas)
        self.add_sfx_btn.setVisible(is_canvas)
        self.fit_btn.setVisible(is_canvas)

        if is_extraction:
            # Hide timeline when in extraction mode to maximize vertical workspace
            self.timeline_view.setVisible(False)
        else:
            self.timeline_view.setVisible(True)

    def _on_extraction_completed(self) -> None:
        """When extraction or bounding boxes are updated, reload data and refresh all views."""
        self._load_data_from_disk()
        self._populate_canvas_and_timeline()
        if hasattr(self, "camera_render_strip"):
            self.camera_render_strip.set_elements_data(self.elements_data)

    def _on_delete_current_section(self) -> None:
        """Confirm and delete the current section, then return to sections roster."""
        if not self.active_section_id:
            return

        reply = QMessageBox.question(
            self,
            "تأكيد حذف السيكشن (Delete Section)",
            f"هل أنت متأكد من حذف السيكشن الحالي بالكامل؟\n\nالمعرف: {self.active_section_id}\n\n⚠️ سيتم حذف جميع ملفات وتخطيطات هذا السيكشن نهائياً.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        sec_id = self.active_section_id

        # 1. Remove from current_project
        if self.current_project and sec_id in self.current_project.sections:
            del self.current_project.sections[sec_id]
            self.state_store.save_state(self.current_project)

        # 2. Delete section directory on disk
        import shutil
        if self.section_path and self.section_path.is_dir():
            try:
                shutil.rmtree(self.section_path, ignore_errors=True)
            except Exception:
                pass

        # 3. Clear local state and navigate back
        self.is_dirty = False
        self.dirty_lbl.setVisible(False)
        self.active_section_id = None
        self.section_path = None
        self.back_requested.emit()

