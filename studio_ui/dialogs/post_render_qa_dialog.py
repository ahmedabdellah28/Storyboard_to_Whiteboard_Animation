"""Post-Render QA Inspection Dialog.

Provides an interactive audit interface for verifying post-render quality gates:
1080p resolution, audio/video duration sync, black frame bursts, and audio integrity.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from core.contracts.qa_reports import PostRenderQAReport, QAGateStatus
from core.validation.post_render_qa import PostRenderQAEngine
from studio_ui.qt import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    Qt,
)


class PostRenderQADialog(QDialog):
    """Forensic Post-Render QA inspection dialog."""

    def __init__(
        self,
        video_path: str | Path,
        section_id: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.video_path = Path(video_path)
        self.section_id = section_id or self.video_path.stem
        self.engine = PostRenderQAEngine()
        self.report: Optional[PostRenderQAReport] = None

        self.setWindowTitle(f"Post-Render QA Inspection — {self.section_id}")
        from studio_ui.window_utils import fit_dialog_to_screen
        fit_dialog_to_screen(self, 750, 520, min_width=650, min_height=440)

        self._init_ui()
        self._execute_inspection()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # 1. Header Card
        header_card = QFrame()
        header_card.setObjectName("card")
        header_layout = QHBoxLayout(header_card)

        info_layout = QVBoxLayout()
        self.title_label = QLabel(f"<b>Post-Render QA: {self.section_id}</b>")
        self.title_label.setStyleSheet("font-size: 16px; color: #101828;")
        self.file_label = QLabel(f"Target: {self.video_path.name}")
        self.file_label.setStyleSheet("color: #475467; font-size: 12px;")
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.file_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()

        self.status_badge = QLabel("ANALYZING...")
        self.status_badge.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 13px;
                padding: 6px 14px;
                border-radius: 6px;
                color: #D97706;
                background-color: #FFEDD5;
            }
        """)
        header_layout.addWidget(self.status_badge)
        layout.addWidget(header_card)

        # 2. Key Metrics Row
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(10)

        self.metric_res = self._create_metric_card("Resolution", "--")
        self.metric_drift = self._create_metric_card("A/V Drift", "--")
        self.metric_black = self._create_metric_card("Black Frames", "--")
        self.metric_audio = self._create_metric_card("Audio Clip", "--")

        metrics_row.addWidget(self.metric_res)
        metrics_row.addWidget(self.metric_drift)
        metrics_row.addWidget(self.metric_black)
        metrics_row.addWidget(self.metric_audio)
        layout.addLayout(metrics_row)

        # 3. Detailed Checks Table
        layout.addWidget(QLabel("<b>Inspection Checks Detail:</b>"))
        self.checks_table = QTableWidget()
        self.checks_table.setColumnCount(3)
        self.checks_table.setHorizontalHeaderLabels(["Check Name", "Status", "Inspection Details"])
        self.checks_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.checks_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.checks_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.checks_table, stretch=1)

        # 4. Action Buttons
        btn_layout = QHBoxLayout()

        self.rerun_btn = QPushButton("🔄 Re-run Inspection")
        self.rerun_btn.clicked.connect(self._execute_inspection)
        btn_layout.addWidget(self.rerun_btn)

        self.export_btn = QPushButton("💾 Export Report JSON")
        self.export_btn.clicked.connect(self._export_report)
        btn_layout.addWidget(self.export_btn)

        btn_layout.addStretch()

        self.accept_btn = QPushButton("Accept Deliverable")
        self.accept_btn.setObjectName("primaryButton")
        self.accept_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.accept_btn)

        layout.addLayout(btn_layout)

    def _create_metric_card(self, title: str, val: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #FAFBFC; border-radius: 6px; padding: 8px;")
        ly = QVBoxLayout(card)
        ly.setContentsMargins(6, 4, 6, 4)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #475467; font-size: 12px;")
        v_lbl = QLabel(val)
        v_lbl.setObjectName("metric_val")
        v_lbl.setStyleSheet("color: #101828; font-size: 14px; font-weight: bold;")
        ly.addWidget(t_lbl)
        ly.addWidget(v_lbl)
        return card

    def _update_metric_card(self, card: QFrame, val: str) -> None:
        v_lbl = card.findChild(QLabel, "metric_val")
        if v_lbl:
            v_lbl.setText(val)

    def _execute_inspection(self) -> None:
        """Run QA inspection engine and populate table."""
        report_file = self.video_path.parent / "qa_report.json"
        self.report = self.engine.inspect(
            video_path=self.video_path,
            section_id=self.section_id,
            output_report_path=report_file,
        )

        is_pass = self.report.overall_status == QAGateStatus.PASS
        if is_pass:
            self.status_badge.setText("PASSED")
            self.status_badge.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 13px;
                    padding: 6px 14px;
                    border-radius: 6px;
                    color: #15803D;
                    background-color: #DCFCE7;
                }
            """)
        else:
            self.status_badge.setText("FAILED")
            self.status_badge.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 13px;
                    padding: 6px 14px;
                    border-radius: 6px;
                    color: #f87171;
                    background-color: #FEE2E2;
                }
            """)

        # Update metrics
        self._update_metric_card(self.metric_res, self.report.resolution)
        self._update_metric_card(self.metric_drift, f"{self.report.duration_drift:.2f}s")
        self._update_metric_card(self.metric_black, f"{self.report.black_frames_count} frames")
        self._update_metric_card(self.metric_audio, "DETECTED" if self.report.audio_clipping_detected else "CLEAN")

        # Populate table
        self.checks_table.setRowCount(len(self.report.checks))
        for row, chk in enumerate(self.report.checks):
            self.checks_table.setItem(row, 0, QTableWidgetItem(chk.name))

            stat_item = QTableWidgetItem(chk.status.value)
            if chk.status == QAGateStatus.PASS:
                stat_item.setForeground(Qt.GlobalColor.green)
            else:
                stat_item.setForeground(Qt.GlobalColor.red)
            self.checks_table.setItem(row, 1, stat_item)

            self.checks_table.setItem(row, 2, QTableWidgetItem(chk.details))

    def _export_report(self) -> None:
        if not self.report:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export QA Report",
            f"qa_report_{self.section_id}.json",
            "JSON Files (*.json)",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.report.model_dump_json(indent=2))
            QMessageBox.information(self, "Exported", f"QA report saved to:\n{path}")
