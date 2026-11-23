"""Multi-track Sequencer Timeline View for Whiteboard Studio.

Part of Unified Studio Editor & Live Video Preview:
- Exposes 4 distinct source tracks:
  1. VOICE (Original narration waveform/words, locked by default for Whisper sync)
  2. VISUALS (Asset events with draw + hold durations, draggable & edge-resizable)
  3. SFX (Independent cue markers with diamond symbols, AUTO vs USER_OVERRIDE ownership)
  4. CAMERA (Shot boundaries and camera pan intervals)
- Live playhead scrubbing that synchronizes visual canvas, camera, voice, and SFX
- Direct manipulation of timing, zoom in/out/fit, and word anchor jumps.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from studio_ui.qt import (
    QBrush,
    QColor,
    QFont,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPainter,
    QPainterPath,
    QPen,
    QPoint,
    QRect,
    QRectF,
    QScrollArea,
    QPushButton,
    Qt,
    QVBoxLayout,
    QWidget,
    Signal,
)
from studio_ui.responsive import (
    control_height,
    font_size,
    scaled_stylesheet_values,
    spacing,
)


class TimelineTrackItem:
    """Model data for an individual event item on the sequencer timeline."""

    def __init__(
        self,
        item_id: str,
        label: str,
        start_time: float,
        duration: float,
        track_group: str = "VISUALS",  # "VOICE", "VISUALS", "SFX", "CAMERA"
        draw_duration: float = 0.8,
        hold_duration: float = 2.0,
        ownership: str = "AUTO",       # "AUTO", "USER_OVERRIDE", "LOCKED"
        color_hex: str = "#4F46E5",
        sfx_type: str = "pop",
        anchor_word: str = "",
        is_locked: bool = False,
        track_type: Optional[str] = None,
    ) -> None:
        if track_type is not None:
            if track_type == "voice":
                track_group = "VOICE"
            elif track_type == "camera":
                track_group = "CAMERA"
            elif track_type == "sfx":
                track_group = "SFX"
            else:
                track_group = "VISUALS"

        self.item_id = item_id
        self.label = label
        self.start_time = max(0.0, start_time)
        self.duration = max(0.2, duration)
        self.track_group = track_group
        self.track_type = track_type or track_group.lower()
        self.draw_duration = draw_duration
        self.hold_duration = hold_duration
        self.ownership = ownership
        self.color_hex = color_hex
        self.sfx_type = sfx_type
        self.anchor_word = anchor_word
        self.is_locked = is_locked or (track_group == "VOICE")
        self.is_selected = False


class TimelineCanvasWidget(QWidget):
    """Canvas rendering the 4 timeline track groups, blocks, cues, ruler, and playhead."""

    time_scrubbed = Signal(float)  # timestamp in seconds
    item_timing_changed = Signal(str, float, float)  # (item_id, start_time, duration)
    sfx_timing_changed = Signal(str, float)          # (cue_id, timestamp)
    item_selected = Signal(str)                      # item_id
    word_clicked = Signal(str, float)                # (word, timestamp)

    BASE_PIXELS_PER_SECOND = float(spacing(90))
    PIXELS_PER_SECOND = float(spacing(90))
    RULER_HEIGHT = spacing(28)
    GROUP_HEADER_HEIGHT = spacing(22)
    TRACK_HEIGHT = spacing(26)
    TRACK_GAP = spacing(4)
    EDGE_RESIZE_THRESHOLD = spacing(8)  # pixels

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.tracks: List[TimelineTrackItem] = []
        self.words_data: List[Tuple[str, float, float]] = []  # (word, start, end)
        self.total_duration: float = 30.0
        self.current_time: float = 0.0
        self.selected_item_id: Optional[str] = None
        self.zoom_factor: float = 1.0

        self._dragging_playhead = False
        self._dragging_item: Optional[TimelineTrackItem] = None
        self._resizing_item_edge: Optional[TimelineTrackItem] = None
        self._dragging_sfx: Optional[TimelineTrackItem] = None
        self._drag_offset_x = 0.0

        self.setMouseTracking(True)
        self._update_geometry()

    @property
    def pps(self) -> float:
        """Effective pixels per second according to current zoom factor."""
        return self.BASE_PIXELS_PER_SECOND * self.zoom_factor

    def set_duration(self, duration_seconds: float) -> None:
        self.total_duration = max(3.0, duration_seconds)
        self._update_geometry()
        self.update()

    def set_tracks(self, tracks: List[TimelineTrackItem]) -> None:
        self.tracks = tracks
        self._update_geometry()
        self.update()

    def set_words(self, words: List[Tuple[str, float, float]]) -> None:
        """Sets Whisper synchronized words for the VOICE track."""
        self.words_data = words
        self.update()

    def set_playhead_time(self, seconds: float) -> None:
        self.current_time = max(0.0, min(self.total_duration, seconds))
        self.update()

    def zoom_in(self) -> None:
        self.zoom_factor = min(3.0, self.zoom_factor * 1.25)
        self._update_geometry()
        self.update()

    def zoom_out(self) -> None:
        self.zoom_factor = max(0.35, self.zoom_factor / 1.25)
        self._update_geometry()
        self.update()

    def zoom_fit(self, available_width: int) -> None:
        if self.total_duration > 0 and available_width > 200:
            target_pps = (available_width - 160) / self.total_duration
            self.zoom_factor = max(0.35, min(3.0, target_pps / self.BASE_PIXELS_PER_SECOND))
            self._update_geometry()
            self.update()

    def _get_tracks_by_group(self) -> Dict[str, List[TimelineTrackItem]]:
        groups: Dict[str, List[TimelineTrackItem]] = {
            "VOICE": [],
            "VISUALS": [],
            "SFX": [],
            "CAMERA": [],
        }
        for t in self.tracks:
            grp = t.track_group.upper()
            if grp in groups:
                groups[grp].append(t)
            else:
                groups["VISUALS"].append(t)
        return groups

    def _update_geometry(self) -> None:
        width = int(self.total_duration * self.pps) + 300
        groups = self._get_tracks_by_group()

        total_track_rows = 1  # 1 for voice
        total_track_rows += max(1, len(groups["VISUALS"]))
        total_track_rows += 1  # 1 row for SFX cues
        total_track_rows += 1  # 1 row for camera shots

        height = self.RULER_HEIGHT + (4 * self.GROUP_HEADER_HEIGHT) + (total_track_rows * (self.TRACK_HEIGHT + self.TRACK_GAP)) + 80
        self.setMinimumSize(width, height)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pps = self.pps

        # 1. Background
        painter.fillRect(0, 0, w, h, QColor("#F5F6F8"))

        # 2. Time Ruler
        ruler_rect = QRect(0, 0, w, self.RULER_HEIGHT)
        painter.fillRect(ruler_rect, QColor("#F0F2F5"))

        ruler_pen = QPen(QColor("#667085"), 1)
        font_ruler = QFont("Segoe UI", font_size(12))
        painter.setFont(font_ruler)
        painter.setPen(ruler_pen)

        step_sec = 1 if pps > 60 else (2 if pps > 30 else 5)
        total_secs = int(self.total_duration) + 2

        for s in range(0, total_secs, step_sec):
            x = int(s * pps)
            painter.drawLine(x, 14, x, self.RULER_HEIGHT)
            mins = s // 60
            secs = s % 60
            painter.drawText(x + 3, 18, f"{mins:02d}:{secs:02d}")

            # Half-second tick
            if step_sec == 1 and pps > 60:
                mid_x = int((s + 0.5) * pps)
                painter.drawLine(mid_x, 20, mid_x, self.RULER_HEIGHT)

        # Subtle vertical grid lines
        grid_pen = QPen(QColor("#F0F2F5"), 1, Qt.PenStyle.DotLine)
        painter.setPen(grid_pen)
        for s in range(0, total_secs, step_sec):
            x = int(s * pps)
            painter.drawLine(x, self.RULER_HEIGHT, x, h)

        # 3. Draw Track Groups
        y_offset = self.RULER_HEIGHT + 2
        groups = self._get_tracks_by_group()

        # GROUP 1: VOICE
        y_offset = self._draw_group_header(painter, "VOICE (Narration & Word Timing) 🔒", y_offset, "#4F46E5", w)
        y_offset = self._draw_voice_track(painter, groups["VOICE"], y_offset, w)

        # GROUP 2: VISUALS
        y_offset = self._draw_group_header(painter, f"VISUALS ({len(groups['VISUALS'])} Assets)", y_offset, "#4F46E5", w)
        y_offset = self._draw_visual_tracks(painter, groups["VISUALS"], y_offset, w)

        # GROUP 3: SFX
        y_offset = self._draw_group_header(painter, f"SFX CUES ({len(groups['SFX'])} Effects)", y_offset, "#16A34A", w)
        y_offset = self._draw_sfx_track(painter, groups["SFX"], y_offset, w)

        # GROUP 4: CAMERA
        y_offset = self._draw_group_header(painter, "CAMERA & SHOT EVENTS", y_offset, "#D97706", w)
        y_offset = self._draw_camera_track(painter, groups["CAMERA"], y_offset, w)

        # 4. Draw Playhead (Top to bottom)
        ph_x = int(self.current_time * pps)
        painter.setPen(QPen(QColor("#DC2626"), 2))
        painter.drawLine(ph_x, 0, ph_x, h)

        # Playhead triangle cap
        painter.setBrush(QBrush(QColor("#DC2626")))
        painter.setPen(Qt.PenStyle.NoPen)
        handle_poly = [
            QPoint(ph_x - 6, 0),
            QPoint(ph_x + 6, 0),
            QPoint(ph_x + 6, 12),
            QPoint(ph_x, 18),
            QPoint(ph_x - 6, 12),
        ]
        painter.drawPolygon(handle_poly)

    def _draw_group_header(self, painter: QPainter, title: str, y: int, accent_hex: str, width: int) -> int:
        header_rect = QRect(0, y, width, self.GROUP_HEADER_HEIGHT)
        painter.fillRect(header_rect, QColor("#FFFFFF"))

        # Accent left bar
        painter.fillRect(QRect(0, y, 4, self.GROUP_HEADER_HEIGHT), QColor(accent_hex))

        painter.setPen(QColor(accent_hex))
        font = QFont("Segoe UI", font_size(12), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(header_rect.adjusted(12, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, title)

        return y + self.GROUP_HEADER_HEIGHT + 2

    def _draw_voice_track(self, painter: QPainter, voice_items: List[TimelineTrackItem], y: int, width: int) -> int:
        track_rect = QRect(0, y, width, self.TRACK_HEIGHT + 4)
        painter.fillRect(track_rect, QColor("#FFFFFF"))  # Deep navy slate

        # Draw simulated audio waveform pulses
        pps = self.pps
        painter.setPen(QPen(QColor("#4F46E5"), 1))
        mid_y = y + (self.TRACK_HEIGHT + 4) // 2

        # Draw Word Segments if present
        if self.words_data:
            for word, start, end in self.words_data:
                wx = int(start * pps)
                ww = max(18, int((end - start) * pps))
                wrect = QRect(wx, y + 2, ww, self.TRACK_HEIGHT)
                painter.setBrush(QBrush(QColor(56, 189, 248, 35)))
                painter.setPen(QPen(QColor("#4F46E5"), 1))
                painter.drawRoundedRect(wrect, 2, 2)

                painter.setPen(QColor("#EEF2FF"))
                font = QFont("Segoe UI", font_size(12))
                painter.setFont(font)
                elided = painter.fontMetrics().elidedText(word, Qt.TextElideMode.ElideRight, ww - 4)
                painter.drawText(wrect, Qt.AlignmentFlag.AlignCenter, elided)
        else:
            # Fallback voice bar
            tot_dur = voice_items[0].duration if voice_items else self.total_duration
            bw = int(tot_dur * pps)
            vrect = QRect(0, y + 3, bw, self.TRACK_HEIGHT - 2)
            painter.setBrush(QBrush(QColor(56, 189, 248, 40)))
            painter.setPen(QPen(QColor("#4F46E5"), 1))
            painter.drawRoundedRect(vrect, 4, 4)

            painter.setPen(QColor("#4F46E5"))
            font = QFont("Segoe UI", font_size(12), QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(vrect.adjusted(8, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, "🎙 Voice Narration (Whisper Synced — Locked)")

        return y + self.TRACK_HEIGHT + 4 + self.TRACK_GAP

    def _draw_visual_tracks(self, painter: QPainter, items: List[TimelineTrackItem], y: int, width: int) -> int:
        pps = self.pps
        if not items:
            empty_rect = QRect(0, y, width, self.TRACK_HEIGHT)
            painter.fillRect(empty_rect, QColor("#FFFFFF"))
            painter.setPen(QColor("#667085"))
            painter.setFont(QFont("Segoe UI", font_size(12)))
            painter.drawText(empty_rect.adjusted(12, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, "No visual elements loaded")
            return y + self.TRACK_HEIGHT + self.TRACK_GAP

        for track in items:
            track_bg = QRect(0, y, width, self.TRACK_HEIGHT)
            painter.fillRect(track_bg, QColor("#FFFFFF"))

            bx = int(track.start_time * pps)
            draw_w = max(10, int(track.draw_duration * pps))
            hold_w = max(10, int(track.hold_duration * pps))
            total_w = draw_w + hold_w

            full_block_rect = QRect(bx, y + 2, total_w, self.TRACK_HEIGHT - 4)
            draw_rect = QRect(bx, y + 2, draw_w, self.TRACK_HEIGHT - 4)
            hold_rect = QRect(bx + draw_w, y + 2, hold_w, self.TRACK_HEIGHT - 4)

            # Selected highlight
            if track.item_id == self.selected_item_id:
                painter.setPen(QPen(QColor("#ffffff"), 2))
            else:
                painter.setPen(QPen(QColor("#EEF2FF"), 1))

            # Draw phase (vibrant purple/blue)
            painter.setBrush(QBrush(QColor("#4F46E5")))
            painter.drawRoundedRect(draw_rect, 3, 3)

            # Hold phase (deeper secondary tone)
            painter.setBrush(QBrush(QColor("#4338CA")))
            painter.drawRoundedRect(hold_rect, 3, 3)

            # Edge resize handles on right edge
            painter.setPen(QColor("#ffffff"))
            painter.drawLine(bx + total_w - 2, y + 6, bx + total_w - 2, y + self.TRACK_HEIGHT - 8)

            # Label text
            painter.setPen(QColor("#ffffff"))
            font = QFont("Segoe UI", font_size(12), QFont.Weight.Bold)
            painter.setFont(font)
            label_text = f"{track.label} [draw:{track.draw_duration:.1f}s | hold:{track.hold_duration:.1f}s]"
            elided = painter.fontMetrics().elidedText(label_text, Qt.TextElideMode.ElideRight, total_w - 8)
            painter.drawText(full_block_rect.adjusted(6, 0, -4, 0), Qt.AlignmentFlag.AlignVCenter, elided)

            y += self.TRACK_HEIGHT + self.TRACK_GAP

        return y

    def _draw_sfx_track(self, painter: QPainter, sfx_items: List[TimelineTrackItem], y: int, width: int) -> int:
        pps = self.pps
        track_bg = QRect(0, y, width, self.TRACK_HEIGHT)
        painter.fillRect(track_bg, QColor("#DCFCE7"))  # Deep emerald slate

        if not sfx_items:
            painter.setPen(QColor("#16A34A"))
            painter.setFont(QFont("Segoe UI", font_size(12)))
            painter.drawText(track_bg.adjusted(12, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, "Automatic SFX cues placed with drawing beats")
            return y + self.TRACK_HEIGHT + self.TRACK_GAP

        for sfx in sfx_items:
            sx = int(sfx.start_time * pps)
            # Draw diamond symbol ◆
            cue_color = QColor("#16A34A") if sfx.ownership == "AUTO" else QColor("#D97706")
            painter.setBrush(QBrush(cue_color))
            painter.setPen(QPen(QColor("#ffffff") if sfx.item_id == self.selected_item_id else cue_color.darker(130), 1))

            diamond = [
                QPoint(sx, y + 4),
                QPoint(sx + 7, y + self.TRACK_HEIGHT // 2),
                QPoint(sx, y + self.TRACK_HEIGHT - 4),
                QPoint(sx - 7, y + self.TRACK_HEIGHT // 2),
            ]
            painter.drawPolygon(diamond)

            # Cue label badge
            badge_rect = QRect(sx + 9, y + 4, 60, self.TRACK_HEIGHT - 8)
            painter.setPen(QColor("#DCFCE7"))
            painter.setFont(QFont("Segoe UI", font_size(12)))
            tag = "AUTO" if sfx.ownership == "AUTO" else "USER"
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignVCenter, f"{sfx.sfx_type} ({tag})")

        return y + self.TRACK_HEIGHT + self.TRACK_GAP

    def _draw_camera_track(self, painter: QPainter, cam_items: List[TimelineTrackItem], y: int, width: int) -> int:
        pps = self.pps
        track_bg = QRect(0, y, width, self.TRACK_HEIGHT)
        painter.fillRect(track_bg, QColor("#FFFBEB"))  # Deep amber slate

        if not cam_items:
            # Default single camera shot
            full_w = int(self.total_duration * pps)
            shot_rect = QRect(0, y + 2, full_w, self.TRACK_HEIGHT - 4)
            painter.setBrush(QBrush(QColor(245, 158, 11, 40)))
            painter.setPen(QPen(QColor("#D97706"), 1))
            painter.drawRoundedRect(shot_rect, 4, 4)
            painter.setPen(QColor("#FEF3C7"))
            painter.setFont(QFont("Segoe UI", font_size(12), QFont.Weight.Bold))
            painter.drawText(shot_rect.adjusted(8, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, "🎥 Camera 01 (Static Framing)")
            return y + self.TRACK_HEIGHT + self.TRACK_GAP

        for cam in cam_items:
            cx = int(cam.start_time * pps)
            cw = max(24, int(cam.duration * pps))
            cam_rect = QRect(cx, y + 2, cw, self.TRACK_HEIGHT - 4)

            painter.setBrush(QBrush(QColor(245, 158, 11, 50)))
            painter.setPen(QPen(QColor("#D97706"), 1))
            painter.drawRoundedRect(cam_rect, 4, 4)

            painter.setPen(QColor("#FEF3C7"))
            font = QFont("Segoe UI", font_size(12), QFont.Weight.Bold)
            painter.setFont(font)
            elided = painter.fontMetrics().elidedText(f"🎥 {cam.label}", Qt.TextElideMode.ElideRight, cw - 8)
            painter.drawText(cam_rect.adjusted(6, 0, -4, 0), Qt.AlignmentFlag.AlignVCenter, elided)

        return y + self.TRACK_HEIGHT + self.TRACK_GAP

    def mousePressEvent(self, event) -> None:
        x = event.position().x()
        y = event.position().y()
        pps = self.pps

        # 1. Ruler Click -> Scrub Playhead
        if y <= self.RULER_HEIGHT or event.modifiers() == Qt.KeyboardModifier.AltModifier:
            self._dragging_playhead = True
            self._scrub_to_x(x)
            return

        # 2. Check Word Clicks on Voice Track
        voice_y_start = self.RULER_HEIGHT + self.GROUP_HEADER_HEIGHT + 2
        voice_y_end = voice_y_start + self.TRACK_HEIGHT + 4
        if voice_y_start <= y <= voice_y_end:
            for word, start, end in self.words_data:
                wx = int(start * pps)
                ww = max(18, int((end - start) * pps))
                if wx <= x <= wx + ww:
                    self.set_playhead_time(start)
                    self.word_clicked.emit(word, start)
                    self.time_scrubbed.emit(start)
                    return

        # 3. Check SFX Cues Clicks/Dragging
        groups = self._get_tracks_by_group()
        visual_count = max(1, len(groups["VISUALS"]))
        sfx_y_start = (
            self.RULER_HEIGHT
            + 2
            + (2 * self.GROUP_HEADER_HEIGHT)
            + (self.TRACK_HEIGHT + 4 + self.TRACK_GAP)
            + (visual_count * (self.TRACK_HEIGHT + self.TRACK_GAP))
            + self.GROUP_HEADER_HEIGHT
        )
        sfx_y_end = sfx_y_start + self.TRACK_HEIGHT

        if sfx_y_start <= y <= sfx_y_end:
            for sfx in groups["SFX"]:
                sx = int(sfx.start_time * pps)
                if abs(x - sx) <= 12:
                    self.selected_item_id = sfx.item_id
                    self._dragging_sfx = sfx
                    self.item_selected.emit(sfx.item_id)
                    self.update()
                    return

        # 4. Check Visual Element Blocks (Move vs Edge Resize)
        y_curr = (
            self.RULER_HEIGHT
            + 2
            + self.GROUP_HEADER_HEIGHT
            + (self.TRACK_HEIGHT + 4 + self.TRACK_GAP)
            + self.GROUP_HEADER_HEIGHT
        )
        for track in groups["VISUALS"]:
            bx = int(track.start_time * pps)
            total_w = max(20, int((track.draw_duration + track.hold_duration) * pps))
            block_rect = QRect(bx, y_curr + 2, total_w, self.TRACK_HEIGHT - 4)

            if block_rect.contains(int(x), int(y)):
                self.selected_item_id = track.item_id
                self.item_selected.emit(track.item_id)

                # Check if clicking on right edge for duration resizing
                if abs(x - (bx + total_w)) <= self.EDGE_RESIZE_THRESHOLD:
                    self._resizing_item_edge = track
                else:
                    self._dragging_item = track
                    self._drag_offset_x = x - bx

                self.update()
                return

            y_curr += self.TRACK_HEIGHT + self.TRACK_GAP

        # 5. Empty space -> Move Playhead
        self._dragging_playhead = True
        self._scrub_to_x(x)

    def mouseMoveEvent(self, event) -> None:
        x = event.position().x()
        pps = self.pps

        if self._dragging_playhead:
            self._scrub_to_x(x)
        elif self._dragging_item:
            new_bx = max(0.0, x - self._drag_offset_x)
            new_start = round(new_bx / pps, 2)
            self._dragging_item.start_time = new_start
            self._dragging_item.ownership = "USER_OVERRIDE"
            self.item_timing_changed.emit(
                self._dragging_item.item_id,
                self._dragging_item.start_time,
                self._dragging_item.duration,
            )
            self.update()
        elif self._resizing_item_edge:
            bx = int(self._resizing_item_edge.start_time * pps)
            new_w = max(20, x - bx)
            new_dur = round(new_w / pps, 2)
            # Allocate proportionately to draw and hold
            ratio = self._resizing_item_edge.draw_duration / max(0.1, self._resizing_item_edge.duration)
            self._resizing_item_edge.draw_duration = max(0.2, round(new_dur * ratio, 2))
            self._resizing_item_edge.hold_duration = max(0.2, round(new_dur * (1.0 - ratio), 2))
            self._resizing_item_edge.duration = new_dur
            self._resizing_item_edge.ownership = "USER_OVERRIDE"
            self.item_timing_changed.emit(
                self._resizing_item_edge.item_id,
                self._resizing_item_edge.start_time,
                self._resizing_item_edge.duration,
            )
            self.update()
        elif self._dragging_sfx:
            new_time = max(0.0, min(self.total_duration, round(x / pps, 2)))
            self._dragging_sfx.start_time = new_time
            self._dragging_sfx.ownership = "USER_OVERRIDE"
            self.sfx_timing_changed.emit(self._dragging_sfx.item_id, new_time)
            self.update()
        else:
            # Update cursor shape when hovering block edge
            cursor_changed = False
            groups = self._get_tracks_by_group()
            y_curr = (
                self.RULER_HEIGHT
                + 2
                + self.GROUP_HEADER_HEIGHT
                + (self.TRACK_HEIGHT + 4 + self.TRACK_GAP)
                + self.GROUP_HEADER_HEIGHT
            )
            for track in groups["VISUALS"]:
                bx = int(track.start_time * pps)
                total_w = max(20, int((track.draw_duration + track.hold_duration) * pps))
                if (
                    y_curr <= event.position().y() <= y_curr + self.TRACK_HEIGHT
                    and abs(x - (bx + total_w)) <= self.EDGE_RESIZE_THRESHOLD
                ):
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                    cursor_changed = True
                    break
                y_curr += self.TRACK_HEIGHT + self.TRACK_GAP

            if not cursor_changed:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event) -> None:
        self._dragging_playhead = False
        self._dragging_item = None
        self._resizing_item_edge = None
        self._dragging_sfx = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _scrub_to_x(self, x: float) -> None:
        sec = max(0.0, min(self.total_duration, x / self.pps))
        self.current_time = sec
        self.time_scrubbed.emit(sec)
        self.update()


class StudioTimelineView(QFrame):
    """Integrated Timeline panel with track labels, transport scrubbing, and zoom controls."""

    time_scrubbed = Signal(float)
    element_timing_changed = Signal(str, float, float)
    sfx_timing_changed = Signal(str, float)
    element_selected = Signal(str)
    word_clicked = Signal(str, float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("background-color: #F5F6F8; border-top: 1px solid #FAFBFC;")
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(spacing(8), spacing(6), spacing(8), spacing(6))
        layout.setSpacing(spacing(6))

        # Timeline Header Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(spacing(10))

        lbl = QLabel("<b>TIMELINE SEQUENCER</b>")
        lbl.setStyleSheet(f"font-size: {font_size(12)}px; color: #4F46E5; font-weight: bold;")
        top_bar.addWidget(lbl)

        self.timecode_label = QLabel("00:00.00 / 00:00.00")
        self.timecode_label.setStyleSheet(
            f"color: #101828; font-family: monospace; font-size: {font_size(12)}px; font-weight: bold;"
        )
        top_bar.addWidget(self.timecode_label)

        top_bar.addSpacing(spacing(16))

        # Timeline Zoom Controls
        btn_h = control_height(22)
        btn_w = control_height(28)

        self.zoom_in_btn = QPushButton("🔍+")
        self.zoom_in_btn.setFixedSize(btn_w, btn_h)
        self.zoom_in_btn.clicked.connect(self._on_zoom_in)
        top_bar.addWidget(self.zoom_in_btn)

        self.zoom_out_btn = QPushButton("🔍-")
        self.zoom_out_btn.setFixedSize(btn_w, btn_h)
        self.zoom_out_btn.clicked.connect(self._on_zoom_out)
        top_bar.addWidget(self.zoom_out_btn)

        self.zoom_fit_btn = QPushButton("Fit Timeline")
        self.zoom_fit_btn.setFixedHeight(btn_h)
        self.zoom_fit_btn.clicked.connect(self._on_zoom_fit)
        top_bar.addWidget(self.zoom_fit_btn)

        top_bar.addStretch()

        help_txt = QLabel("Tracks: VOICE (Locked) | VISUALS (Drag/Resize) | SFX (◆ Cues) | CAMERA")
        help_txt.setStyleSheet(f"color: #667085; font-size: {font_size(10)}px;")
        top_bar.addWidget(help_txt)

        layout.addLayout(top_bar)

        # Scrollable Canvas
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #FAFBFC; border-radius: 4px; }")

        self.canvas_widget = TimelineCanvasWidget()
        self.canvas_widget.time_scrubbed.connect(self._on_scrubbed)
        self.canvas_widget.item_timing_changed.connect(self.element_timing_changed)
        self.canvas_widget.sfx_timing_changed.connect(self.sfx_timing_changed)
        self.canvas_widget.item_selected.connect(self.element_selected)
        self.canvas_widget.word_clicked.connect(self.word_clicked)

        self.scroll_area.setWidget(self.canvas_widget)
        layout.addWidget(self.scroll_area)

    def set_duration(self, duration_seconds: float) -> None:
        self.canvas_widget.set_duration(duration_seconds)
        self._update_timecode_display()

    def set_tracks(self, tracks: List[TimelineTrackItem]) -> None:
        self.canvas_widget.set_tracks(tracks)

    def set_words(self, words: List[Tuple[str, float, float]]) -> None:
        self.canvas_widget.set_words(words)

    def set_playhead_time(self, seconds: float) -> None:
        self.canvas_widget.set_playhead_time(seconds)
        self._update_timecode_display()

    def _on_zoom_in(self) -> None:
        self.canvas_widget.zoom_in()

    def _on_zoom_out(self) -> None:
        self.canvas_widget.zoom_out()

    def _on_zoom_fit(self) -> None:
        self.canvas_widget.zoom_fit(self.scroll_area.viewport().width())

    def _on_scrubbed(self, seconds: float) -> None:
        self._update_timecode_display()
        self.time_scrubbed.emit(seconds)

    def _update_timecode_display(self) -> None:
        cur = self.canvas_widget.current_time
        tot = self.canvas_widget.total_duration
        c_m, c_s = int(cur // 60), cur % 60
        t_m, t_s = int(tot // 60), tot % 60
        self.timecode_label.setText(f"{c_m:02d}:{c_s:05.2f} / {t_m:02d}:{t_s:05.2f}")
