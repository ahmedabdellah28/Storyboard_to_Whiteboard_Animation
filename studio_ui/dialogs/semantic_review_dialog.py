"""Semantic Mapping & Keyword Binding Review Dialog for Whiteboard Studio.

Part of Phase 7: Human Review Gates & Inspection Dialogs.
Allows interactive mapping of Whisper spoken words to extracted visual assets,
trigger timestamp validation, and human approval before spatial choreography.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.contracts.studio_contracts import StageIdentifier
from core.state.project_state import ProjectState
from core.state.state_store import StateStore, get_state_store
from core.state.transitions import ReviewGateStatus
from core.state.workflow_events import ReviewGateChangedEvent, WorkflowEventBus, get_workflow_event_bus
from studio_ui.qt import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
    Signal,
)


class SemanticReviewDialog(QDialog):
    """Review gate dialog for inspecting and adjusting semantic word-to-asset bindings."""

    review_approved = Signal(str, str)  # (section_id, stage_id)

    def __init__(
        self,
        project_id: str,
        section_id: str,
        section_path: Path,
        state_store: Optional[StateStore] = None,
        event_bus: Optional[WorkflowEventBus] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.project_id = project_id
        self.section_id = section_id
        self.section_path = Path(section_path).resolve()
        self.state_store = state_store or get_state_store()
        self.event_bus = event_bus or get_workflow_event_bus()

        self.whisper_words: List[Dict[str, Any]] = []
        self.assets_data: Dict[str, Any] = {}
        self.bindings: Dict[str, Dict[str, Any]] = {}

        self.setWindowTitle(f"Semantic Review & Audio-Visual Alignment — Section: {section_id}")
        from studio_ui.window_utils import fit_dialog_to_screen
        fit_dialog_to_screen(self, 920, 640, min_width=720, min_height=500)
        self._load_data()
        self._init_ui()

    def _load_data(self) -> None:
        """Load Whisper word timings and asset metadata."""
        # 1. Load Whisper JSON
        whisper_file = self.section_path / "timing" / "whisper.json"
        if whisper_file.exists():
            try:
                with open(whisper_file, "r", encoding="utf-8") as f:
                    wdata = json.load(f)
                    # Extract words from segments
                    segments = wdata.get("segments", [])
                    for seg in segments:
                        for word_info in seg.get("words", []):
                            self.whisper_words.append(word_info)
                    if not self.whisper_words and "words" in wdata:
                        self.whisper_words = wdata["words"]
            except Exception as e:
                print(f"[SemanticReview] Error reading whisper.json: {e}")

        # 2. Load Assets metadata
        meta_file = self.section_path / "assets" / "metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.assets_data = data.get("assets", data) if isinstance(data, dict) else {}
            except Exception as e:
                print(f"[SemanticReview] Error reading metadata.json: {e}")

        # Fallback assets if empty
        if not self.assets_data:
            assets_dir = self.section_path / "assets"
            if assets_dir.is_dir():
                for p in sorted(assets_dir.glob("*.png")):
                    if p.name != "storyboard.png":
                        self.assets_data[p.stem] = {"label": p.stem, "file": p.name}

        # 3. Load or generate default bindings
        semantic_file = self.section_path / "timing" / "semantic_mapping.json"
        if semantic_file.exists():
            try:
                with open(semantic_file, "r", encoding="utf-8") as f:
                    self.bindings = json.load(f)
            except Exception:
                pass

        if not self.bindings:
            # Generate heuristic initial mapping
            total_assets = len(self.assets_data)
            total_words = len(self.whisper_words)
            for i, aid in enumerate(self.assets_data.keys()):
                # Distribute triggers across transcript words
                w_idx = int((i / max(1, total_assets)) * total_words) if total_words > 0 else 0
                word_item = self.whisper_words[w_idx] if w_idx < len(self.whisper_words) else {}
                self.bindings[aid] = {
                    "trigger_word": word_item.get("word", "").strip(),
                    "timestamp": word_item.get("start", 0.0),
                    "is_decorative": False,
                }

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Info Banner
        header = QFrame()
        header.setStyleSheet("background-color: #FAFBFC; border-radius: 8px; padding: 12px;")
        h_layout = QHBoxLayout(header)

        words_count = len(self.whisper_words)
        info = (
            f"<b>Section:</b> {self.section_id} &nbsp;|&nbsp; "
            f"<b>Whisper Words:</b> {words_count} &nbsp;|&nbsp; "
            f"<b>Assets to Bind:</b> {len(self.assets_data)}"
        )
        lbl = QLabel(info)
        lbl.setStyleSheet("font-size: 13px; color: #101828;")
        h_layout.addWidget(lbl)

        h_layout.addStretch()

        help_lbl = QLabel("🎯 Bind each visual element to its exact spoken trigger phrase.")
        help_lbl.setStyleSheet("color: #475467; font-size: 12px;")
        h_layout.addWidget(help_lbl)

        layout.addWidget(header)

        # Mapping Table
        table_title = QLabel("Asset Trigger Bindings")
        table_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #4F46E5;")
        layout.addWidget(table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Asset ID", "Trigger Word / Phrase", "Spoken At", "Role", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #FAFBFC;
                border-radius: 6px;
                color: #101828;
            }
            QHeaderView::section {
                background-color: #FAFBFC;
                color: #475467;
                padding: 6px;
                font-weight: bold;
                border: none;
            }
        """)

        self._populate_table()
        layout.addWidget(self.table)

        # Footer Actions
        footer = QHBoxLayout()

        reset_btn = QPushButton("Reset to Auto Defaults")
        reset_btn.setStyleSheet("background-color: #E4E7EC; color: #101828; padding: 8px 16px; border-radius: 6px;")
        reset_btn.clicked.connect(self._reset_defaults)
        footer.addWidget(reset_btn)

        footer.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)

        approve_btn = QPushButton("✓ Approve Semantic Mapping")
        approve_btn.setObjectName("primaryButton")
        approve_btn.setStyleSheet("background-color: #4F46E5; color: #FFFFFF; font-weight: bold; padding: 8px 24px; border-radius: 6px;")
        approve_btn.clicked.connect(self._on_approve)
        footer.addWidget(approve_btn)

        layout.addLayout(footer)

    def _populate_table(self) -> None:
        """Populate mapping table with current bindings."""
        self.table.setRowCount(len(self.assets_data))
        self.trigger_edits: Dict[str, QLineEdit] = {}
        self.role_combos: Dict[str, QComboBox] = {}

        for row, aid in enumerate(self.assets_data.keys()):
            b = self.bindings.get(aid, {})

            # 0. Asset ID
            self.table.setItem(row, 0, QTableWidgetItem(aid))

            # 1. Trigger Edit
            edit = QLineEdit(b.get("trigger_word", ""))
            edit.setStyleSheet("background-color: #FAFBFC; color: #101828; border: 1px solid #E4E7EC; border-radius: 4px; padding: 4px;")
            self.trigger_edits[aid] = edit
            self.table.setCellWidget(row, 1, edit)

            # 2. Timestamp
            t_sec = float(b.get("timestamp", 0.0))
            ts_str = f"{int(t_sec // 60):02d}:{t_sec % 60:05.2f}"
            self.table.setItem(row, 2, QTableWidgetItem(ts_str))

            # 3. Role Combo
            combo = QComboBox()
            combo.addItems(["Key Semantic Anchor", "Supporting Visual", "Decorative (Auto-time)"])
            if b.get("is_decorative"):
                combo.setCurrentIndex(2)
            self.role_combos[aid] = combo
            self.table.setCellWidget(row, 3, combo)

            # 4. Action
            pick_btn = QPushButton("Find in Audio")
            pick_btn.clicked.connect(lambda _, a=aid: self._pick_word_for_asset(a))
            self.table.setCellWidget(row, 4, pick_btn)

    def _pick_word_for_asset(self, asset_id: str) -> None:
        """Helper to find closest word in whisper words."""
        edit = self.trigger_edits.get(asset_id)
        if not edit:
            return
        query = edit.text().strip()
        matched = False
        for w in self.whisper_words:
            if query and query in w.get("word", ""):
                edit.setText(w.get("word", ""))
                matched = True
                break
        if not matched and self.whisper_words:
            edit.setText(self.whisper_words[0].get("word", ""))

    def _reset_defaults(self) -> None:
        self.bindings.clear()
        self._load_data()
        self._populate_table()

    def _save_bindings(self) -> None:
        """Persist mapping bindings to timing/semantic_mapping.json."""
        out: Dict[str, Any] = {}
        for aid, edit in self.trigger_edits.items():
            combo = self.role_combos.get(aid)
            out[aid] = {
                "trigger_word": edit.text().strip(),
                "is_decorative": (combo.currentIndex() == 2) if combo else False,
            }

        out_file = self.section_path / "timing" / "semantic_mapping.json"
        try:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[SemanticReview] Warning saving bindings: {e}")

    def _on_approve(self) -> None:
        self._save_bindings()

        state = self.state_store.load_state(self.project_id)
        sec = state.get_or_create_section(self.section_id)
        sec.set_review_gate(StageIdentifier.SEMANTIC.value, ReviewGateStatus.APPROVED)
        self.state_store.save_state(state)

        if self.event_bus:
            self.event_bus.publish(
                ReviewGateChangedEvent(
                    project_id=self.project_id,
                    section_id=self.section_id,
                    stage_id=StageIdentifier.SEMANTIC.value,
                    old_status=ReviewGateStatus.REVIEW_PENDING,
                    new_status=ReviewGateStatus.APPROVED,
                    reason="User approved semantic keyword mapping.",
                )
            )

        self.review_approved.emit(self.section_id, StageIdentifier.SEMANTIC.value)
        self.accept()
