"""Studio Video Player — High-Precision 1080p Video Playback Widget & Dialog.

Provides crash-free, platform-independent video playback and frame scrubbing
using OpenCV decoding and native Qt image rendering.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from studio_ui.qt import (
    QAction,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QIcon,
    QImage,
    QLabel,
    QPixmap,
    QPushButton,
    QSlider,
    QTimer,
    QVBoxLayout,
    QWidget,
    Qt,
    Signal,
)


class StudioVideoPlayerWidget(QWidget):
    """Integrated 1080p video player with scrubbing, frame stepping, and speed control."""

    playback_finished = Signal()
    position_changed = Signal(float)  # (current_seconds)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.video_path: Optional[str] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.total_frames: int = 0
        self.fps: float = 30.0
        self.duration: float = 0.0
        self.current_frame_idx: int = 0
        self.is_playing: bool = False
        self.speed: float = 1.0
        self.is_looping: bool = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 1. Video Display Frame
        self.display_frame = QFrame()
        self.display_frame.setStyleSheet("background-color: #F5F6F8; border: 1px solid #FAFBFC; border-radius: 6px;")
        disp_layout = QVBoxLayout(self.display_frame)
        disp_layout.setContentsMargins(4, 4, 4, 4)

        self.video_label = QLabel("No video loaded")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("color: #667085; font-size: 14px; font-weight: 500;")
        self.video_label.setMinimumSize(480, 270)
        disp_layout.addWidget(self.video_label)

        layout.addWidget(self.display_frame, stretch=1)

        # 2. Scrubbing Bar & Timecode
        scrub_layout = QHBoxLayout()
        scrub_layout.setSpacing(8)

        self.timecode_label = QLabel("00:00.00 / 00:00.00")
        self.timecode_label.setStyleSheet("color: #4F46E5; font-family: monospace; font-size: 12px; font-weight: bold;")
        scrub_layout.addWidget(self.timecode_label)

        self.scrub_slider = QSlider(Qt.Orientation.Horizontal)
        self.scrub_slider.setRange(0, 0)
        self.scrub_slider.sliderMoved.connect(self._on_slider_moved)
        self.scrub_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #FAFBFC;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #4F46E5;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #101828;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
        """)
        scrub_layout.addWidget(self.scrub_slider, stretch=1)

        self.meta_label = QLabel("1080p @ 30fps")
        self.meta_label.setStyleSheet("color: #475467; font-size: 12px;")
        scrub_layout.addWidget(self.meta_label)

        layout.addLayout(scrub_layout)

        # 3. Transport Controls
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(8)

        self.step_back_btn = QPushButton("⏮ -1s")
        self.step_back_btn.clicked.connect(lambda: self.seek_relative(-1.0))
        ctrl_layout.addWidget(self.step_back_btn)

        self.prev_frame_btn = QPushButton("◀ Step")
        self.prev_frame_btn.setToolTip("Step 1 frame backward")
        self.prev_frame_btn.clicked.connect(self.step_backward)
        ctrl_layout.addWidget(self.prev_frame_btn)

        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setObjectName("primaryButton")
        self.play_btn.setFixedWidth(90)
        self.play_btn.clicked.connect(self.toggle_play)
        ctrl_layout.addWidget(self.play_btn)

        self.next_frame_btn = QPushButton("Step ▶")
        self.next_frame_btn.setToolTip("Step 1 frame forward")
        self.next_frame_btn.clicked.connect(self.step_forward)
        ctrl_layout.addWidget(self.next_frame_btn)

        self.step_fwd_btn = QPushButton("+1s ⏭")
        self.step_fwd_btn.clicked.connect(lambda: self.seek_relative(1.0))
        ctrl_layout.addWidget(self.step_fwd_btn)

        ctrl_layout.addSpacing(16)

        # Speed Dropdown
        ctrl_layout.addWidget(QLabel("Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "1.0x", "1.5x", "2.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)
        ctrl_layout.addWidget(self.speed_combo)

        # Loop Toggle
        self.loop_chk = QCheckBox("Loop")
        self.loop_chk.toggled.connect(self._on_loop_toggled)
        ctrl_layout.addWidget(self.loop_chk)

        ctrl_layout.addStretch()

        layout.addLayout(ctrl_layout)

    def load_video(self, video_path: str | Path) -> bool:
        """Loads a video file and renders the initial frame."""
        self.stop()
        p = Path(video_path)
        if not p.exists():
            self.video_label.setText(f"File not found:\n{p.name}")
            return False

        if self.cap:
            self.cap.release()

        self.video_path = str(p)
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            self.video_label.setText(f"Could not decode:\n{p.name}")
            return False

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = float(self.cap.get(cv2.CAP_PROP_FPS)) or 30.0
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0.0
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.meta_label.setText(f"{width}x{height} @ {self.fps:.1f}fps")
        self.scrub_slider.setRange(0, max(0, self.total_frames - 1))
        self.current_frame_idx = 0

        self._show_frame(0)
        self._update_timecode_display()
        return True

    def play(self) -> None:
        """Starts video playback."""
        if not self.cap or not self.cap.isOpened():
            return
        if self.current_frame_idx >= self.total_frames - 1:
            self.seek_frame(0)

        self.is_playing = True
        self.play_btn.setText("⏸ Pause")
        interval_ms = int(1000.0 / (self.fps * self.speed))
        self._timer.start(max(5, interval_ms))

    def pause(self) -> None:
        """Pauses video playback."""
        self.is_playing = False
        self._timer.stop()
        self.play_btn.setText("▶ Play")

    def toggle_play(self) -> None:
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def stop(self) -> None:
        self.pause()
        self.seek_frame(0)

    def seek_frame(self, frame_idx: int) -> None:
        """Seek directly to specified frame number."""
        if not self.cap:
            return
        idx = max(0, min(frame_idx, self.total_frames - 1))
        self.current_frame_idx = idx
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        self._show_frame(idx)
        self.scrub_slider.blockSignals(True)
        self.scrub_slider.setValue(idx)
        self.scrub_slider.blockSignals(False)
        self._update_timecode_display()

        cur_sec = idx / self.fps if self.fps > 0 else 0.0
        self.position_changed.emit(cur_sec)

    def seek_relative(self, seconds: float) -> None:
        target_f = int(self.current_frame_idx + (seconds * self.fps))
        self.seek_frame(target_f)

    def step_forward(self) -> None:
        self.pause()
        self.seek_frame(self.current_frame_idx + 1)

    def step_backward(self) -> None:
        self.pause()
        self.seek_frame(self.current_frame_idx - 1)

    def _on_tick(self) -> None:
        if not self.cap or not self.is_playing:
            return

        ret, frame = self.cap.read()
        if not ret or self.current_frame_idx >= self.total_frames - 1:
            if self.is_looping:
                self.seek_frame(0)
            else:
                self.pause()
                self.playback_finished.emit()
            return

        self.current_frame_idx += 1
        self._render_opencv_frame(frame)
        self.scrub_slider.blockSignals(True)
        self.scrub_slider.setValue(self.current_frame_idx)
        self.scrub_slider.blockSignals(False)
        self._update_timecode_display()

        cur_sec = self.current_frame_idx / self.fps if self.fps > 0 else 0.0
        self.position_changed.emit(cur_sec)

    def _show_frame(self, frame_idx: int) -> None:
        if not self.cap:
            return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if ret:
            self._render_opencv_frame(frame)

    def _render_opencv_frame(self, frame: np.ndarray) -> None:
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(q_img)

        # Scale to label size preserving aspect ratio
        scaled = pix.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.video_label.setPixmap(scaled)

    def _on_slider_moved(self, val: int) -> None:
        self.seek_frame(val)

    def _on_speed_changed(self, text: str) -> None:
        try:
            self.speed = float(text.replace("x", ""))
        except ValueError:
            self.speed = 1.0
        if self.is_playing:
            self.pause()
            self.play()

    def _on_loop_toggled(self, checked: bool) -> None:
        self.is_looping = checked

    def _update_timecode_display(self) -> None:
        cur_sec = self.current_frame_idx / self.fps if self.fps > 0 else 0.0
        c_m = int(cur_sec // 60)
        c_s = cur_sec % 60
        t_m = int(self.duration // 60)
        t_s = self.duration % 60
        self.timecode_label.setText(f"{c_m:02d}:{c_s:05.2f} / {t_m:02d}:{t_s:05.2f}")

    def closeEvent(self, event) -> None:
        self.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        super().closeEvent(event)


class StudioPlayerDialog(QDialog):
    """Standalone video preview modal with QA inspection shortcut."""

    def __init__(
        self,
        video_path: str | Path,
        title: str = "Video Preview",
        section_id: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.video_path = str(video_path)
        self.section_id = section_id
        self.setWindowTitle(f"🎬 {title} — {Path(video_path).name}")
        from studio_ui.window_utils import fit_dialog_to_screen
        fit_dialog_to_screen(self, 800, 560, min_width=680, min_height=460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Top Info Bar
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel(f"<b>{title}</b> | <code>{Path(video_path).name}</code>"))
        top_bar.addStretch()

        self.qa_btn = QPushButton("✅ Run Post-Render QA")
        self.qa_btn.setStyleSheet("background-color: #16A34A; color: #FFFFFF; font-weight: bold; padding: 4px 12px;")
        self.qa_btn.clicked.connect(self._run_qa)
        top_bar.addWidget(self.qa_btn)

        layout.addLayout(top_bar)

        # Player Widget
        self.player = StudioVideoPlayerWidget(self)
        self.player.load_video(self.video_path)
        layout.addWidget(self.player, stretch=1)

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _run_qa(self) -> None:
        from studio_ui.dialogs.post_render_qa_dialog import PostRenderQADialog
        dlg = PostRenderQADialog(
            video_path=self.video_path,
            section_id=self.section_id,
            parent=self,
        )
        dlg.exec()

    def closeEvent(self, event) -> None:
        self.player.stop()
        super().closeEvent(event)
