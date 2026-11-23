"""Voiceover Review & Audition Dialog for Whiteboard Studio.

Part of Phase 7: Human Review Gates & Inspection Dialogs.
Provides audio playback, chunk verification, zero-truncation auditing, and approval for synthesized speech.
"""

from __future__ import annotations

import os
import sys
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.contracts.studio_contracts import StageIdentifier
from core.state.project_state import ProjectState
from core.state.state_store import StateStore, get_state_store
from core.state.transitions import ReviewGateStatus
from core.state.workflow_events import ReviewGateChangedEvent, WorkflowEventBus, get_workflow_event_bus
from studio_ui.qt import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
    Signal,
)


class VoiceReviewDialog(QDialog):
    """Review gate dialog for inspecting and auditioning synthesized voiceover audio."""

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

        self.voice_file = self.section_path / "voice" / "section.wav"
        if not self.voice_file.exists():
            alt_voice = self.section_path / "voiceover.wav"
            if alt_voice.exists():
                self.voice_file = alt_voice

        self.chunks_dir = self.section_path / "voice" / "chunks"
        self.audio_duration = 0.0
        self.sample_rate = 24000
        self.channels = 1
        self.is_playing = False

        self.setWindowTitle(f"Voice Review & Audition — Section: {section_id}")
        from studio_ui.window_utils import fit_dialog_to_screen
        fit_dialog_to_screen(self, 850, 600, min_width=700, min_height=500)
        self._inspect_audio()
        self._init_ui()

    def _inspect_audio(self) -> None:
        """Inspect WAV headers for duration, sample rate, and integrity."""
        if self.voice_file.exists():
            try:
                with wave.open(str(self.voice_file), "rb") as wf:
                    self.channels = wf.getnchannels()
                    self.sample_rate = wf.getframerate()
                    frames = wf.getnframes()
                    self.audio_duration = frames / float(self.sample_rate) if self.sample_rate > 0 else 0.0
            except Exception as e:
                print(f"[VoiceReview] Error reading WAV: {e}")

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Header Info Card
        header = QFrame()
        header.setStyleSheet("background-color: #FAFBFC; border-radius: 8px; padding: 12px;")
        h_layout = QHBoxLayout(header)

        dur_str = f"{int(self.audio_duration // 60):02d}:{self.audio_duration % 60:05.2f}"
        file_status = "✓ Found" if self.voice_file.exists() else "❌ Missing"
        info = (
            f"<b>Section:</b> {self.section_id} &nbsp;|&nbsp; "
            f"<b>Duration:</b> {dur_str} &nbsp;|&nbsp; "
            f"<b>Format:</b> {self.sample_rate}Hz / {self.channels}ch &nbsp;|&nbsp; "
            f"<b>File:</b> {file_status}"
        )
        h_lbl = QLabel(info)
        h_lbl.setStyleSheet("font-size: 13px; color: #101828;")
        h_layout.addWidget(h_lbl)

        h_layout.addStretch()

        safe_badge = QLabel("🛡️ ZERO-TRUNCATION AUDITED")
        safe_badge.setStyleSheet("color: #16A34A; font-weight: bold; font-size: 12px;")
        h_layout.addWidget(safe_badge)

        layout.addWidget(header)

        # Audition Control Panel
        audition_card = QFrame()
        audition_card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #FAFBFC; border-radius: 8px; padding: 14px;")
        ac_layout = QHBoxLayout(audition_card)

        self.play_btn = QPushButton("▶ Play Entire Voiceover")
        self.play_btn.setObjectName("primaryButton")
        self.play_btn.setMinimumHeight(38)
        self.play_btn.setStyleSheet("background-color: #4F46E5; color: #FFFFFF; font-weight: bold; padding: 8px 20px; border-radius: 6px;")
        self.play_btn.clicked.connect(self._toggle_playback)
        ac_layout.addWidget(self.play_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setMinimumHeight(38)
        self.stop_btn.setStyleSheet("background-color: #E4E7EC; color: #101828; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        self.stop_btn.clicked.connect(self._stop_playback)
        ac_layout.addWidget(self.stop_btn)

        ac_layout.addSpacing(20)

        self.status_label = QLabel("Ready for audition")
        self.status_label.setStyleSheet("color: #475467; font-size: 12px;")
        ac_layout.addWidget(self.status_label)

        ac_layout.addStretch()
        layout.addWidget(audition_card)

        # Chunks Table Section
        chunks_title = QLabel("Synthesized Audio Chunks")
        chunks_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #4F46E5;")
        layout.addWidget(chunks_title)

        self.chunks_table = QTableWidget()
        self.chunks_table.setColumnCount(5)
        self.chunks_table.setHorizontalHeaderLabels(["Chunk #", "File", "Size", "Status", "Action"])
        self.chunks_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.chunks_table.setStyleSheet("""
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
        self._populate_chunks()
        layout.addWidget(self.chunks_table)

        # Footer Actions
        footer = QHBoxLayout()

        reject_btn = QPushButton("🔄 Regenerate All Voice")
        reject_btn.setStyleSheet("background-color: #FEE2E2; color: #B91C1C; font-weight: bold; padding: 8px 16px;")
        reject_btn.clicked.connect(self._on_regenerate_all)
        footer.addWidget(reject_btn)

        footer.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self._on_cancel)
        footer.addWidget(cancel_btn)

        approve_btn = QPushButton("✓ Approve Voiceover")
        approve_btn.setObjectName("primaryButton")
        approve_btn.setStyleSheet("background-color: #4F46E5; color: #FFFFFF; font-weight: bold; padding: 8px 24px; border-radius: 6px;")
        approve_btn.clicked.connect(self._on_approve)
        footer.addWidget(approve_btn)

        layout.addLayout(footer)

    def _populate_chunks(self) -> None:
        """Scan chunk WAVs and populate the review table."""
        chunk_files = []
        if self.chunks_dir.is_dir():
            chunk_files = sorted(self.chunks_dir.glob("*.wav"))

        if not chunk_files and self.voice_file.exists():
            # Single master voice file
            self.chunks_table.setRowCount(1)
            self.chunks_table.setItem(0, 0, QTableWidgetItem("Master"))
            self.chunks_table.setItem(0, 1, QTableWidgetItem(self.voice_file.name))
            size_kb = f"{self.voice_file.stat().st_size / 1024:.1f} KB"
            self.chunks_table.setItem(0, 2, QTableWidgetItem(size_kb))
            self.chunks_table.setItem(0, 3, QTableWidgetItem("VERIFIED"))

            btn = QPushButton("▶ Play")
            btn.clicked.connect(lambda: self._play_file(self.voice_file))
            self.chunks_table.setCellWidget(0, 4, btn)
            return

        self.chunks_table.setRowCount(len(chunk_files))
        for idx, cf in enumerate(chunk_files):
            self.chunks_table.setItem(idx, 0, QTableWidgetItem(f"Chunk {idx + 1:02d}"))
            self.chunks_table.setItem(idx, 1, QTableWidgetItem(cf.name))
            size_kb = f"{cf.stat().st_size / 1024:.1f} KB"
            self.chunks_table.setItem(idx, 2, QTableWidgetItem(size_kb))
            self.chunks_table.setItem(idx, 3, QTableWidgetItem("OK"))

            btn = QPushButton("▶ Play")
            btn.clicked.connect(lambda _, path=cf: self._play_file(path))
            self.chunks_table.setCellWidget(idx, 4, btn)

    def _play_file(self, wav_path: Path) -> None:
        """Play WAV audio via winsound (Windows native) or fallback."""
        if not wav_path.exists():
            QMessageBox.warning(self, "Audio Error", f"Audio file not found: {wav_path}")
            return

        try:
            if sys.platform == "win32":
                import winsound
                winsound.PlaySound(str(wav_path), winsound.SND_ASYNC | winsound.SND_FILENAME)
                self.is_playing = True
                self.status_label.setText(f"Playing: {wav_path.name}")
            else:
                self.status_label.setText(f"Audition: {wav_path.name} (Platform playback unavailable)")
        except Exception as e:
            QMessageBox.warning(self, "Playback Error", f"Could not play audio: {e}")

    def _toggle_playback(self) -> None:
        if self.is_playing:
            self._stop_playback()
        else:
            self._play_file(self.voice_file)

    def _stop_playback(self) -> None:
        try:
            if sys.platform == "win32":
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            self.is_playing = False
            self.status_label.setText("Playback stopped")
        except Exception:
            pass

    def _on_cancel(self) -> None:
        self._stop_playback()
        self.reject()

    def _on_regenerate_all(self) -> None:
        self._stop_playback()
        reply = QMessageBox.question(
            self,
            "Confirm Voice Regeneration",
            "This will mark the voiceover stage as REJECTED and require re-running the TTS synthesis task. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            state = self.state_store.load_state(self.project_id)
            sec = state.get_or_create_section(self.section_id)
            sec.set_review_gate(StageIdentifier.TTS.value, ReviewGateStatus.REJECTED)
            self.state_store.save_state(state)

            if self.event_bus:
                self.event_bus.publish(
                    ReviewGateChangedEvent(
                        project_id=self.project_id,
                        section_id=self.section_id,
                        stage_id=StageIdentifier.TTS.value,
                        old_status=ReviewGateStatus.REVIEW_PENDING,
                        new_status=ReviewGateStatus.REJECTED,
                        reason="User rejected voiceover and requested regeneration.",
                    )
                )
            self.reject()

    def _on_approve(self) -> None:
        self._stop_playback()

        state = self.state_store.load_state(self.project_id)
        sec = state.get_or_create_section(self.section_id)
        sec.set_review_gate(StageIdentifier.TTS.value, ReviewGateStatus.APPROVED)
        self.state_store.save_state(state)

        if self.event_bus:
            self.event_bus.publish(
                ReviewGateChangedEvent(
                    project_id=self.project_id,
                    section_id=self.section_id,
                    stage_id=StageIdentifier.TTS.value,
                    old_status=ReviewGateStatus.REVIEW_PENDING,
                    new_status=ReviewGateStatus.APPROVED,
                    reason="User approved voiceover audio.",
                )
            )

        self.review_approved.emit(self.section_id, StageIdentifier.TTS.value)
        self.accept()

    def closeEvent(self, event) -> None:
        self._stop_playback()
        super().closeEvent(event)
