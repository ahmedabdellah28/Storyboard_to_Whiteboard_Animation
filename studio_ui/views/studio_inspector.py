"""Contextual Inspector Panel for Whiteboard Studio.

Part of Unified Studio Editor & Live Video Preview:
- Displays and edits properties of the currently selected element, camera shot, or SFX cue.
- Exposes ownership status: AUTO / USER_OVERRIDE / LOCKED.
- Provides [Reset to Automatic] button to restore deterministic AI scheduling.
- Integrated with centralized responsive system (flexible width, scrollable form fallback, DPI-scaled metrics).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from studio_ui.qt import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    Qt,
    QVBoxLayout,
    QWidget,
    Signal,
)
from studio_ui.responsive import (
    control_height,
    font_size,
    inspector_panel_width,
    scaled_stylesheet_values,
    spacing,
)


class StudioInspectorPanel(QFrame):
    """Context-sensitive properties inspector for canvas, timeline, and SFX cues."""

    property_changed = Signal(str, str, object)      # (item_id, prop_name, value)
    remove_item_requested = Signal(str)              # item_id
    reset_to_auto_requested = Signal(str)            # item_id

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(0)
        self.setMaximumWidth(420)
        self._apply_responsive_styles()

        self.current_item_id: Optional[str] = None
        self.current_item_type: str = "none"
        self._block_signals = False

        self._init_ui()

    def _apply_responsive_styles(self) -> None:
        sv = scaled_stylesheet_values(widget=self)
        self.setStyleSheet(f"""
            StudioInspectorPanel {{
                background-color: #FFFFFF;
                border-left: 1px solid #FAFBFC;
            }}
            QLabel {{
                color: #475467;
                font-size: {sv['small_font']}px;
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: #FAFBFC;
                color: #101828;
                border: 1px solid #E4E7EC;
                border-radius: {sv['border_radius_sm']}px;
                padding: {sv['pad_sm']}px;
                font-size: {sv['small_font']}px;
                min-height: {sv['ctrl_h_sm']}px;
            }}
        """)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(spacing(10), spacing(10), spacing(10), spacing(10))
        layout.setSpacing(spacing(8))

        # Header Title
        self.header_title = QLabel("INSPECTOR")
        self.header_title.setStyleSheet(
            f"font-size: {font_size(12)}px; font-weight: bold; color: #4F46E5;"
        )
        layout.addWidget(self.header_title)

        # Ownership Row
        ownership_row = QHBoxLayout()
        ownership_row.setSpacing(spacing(6))
        ownership_row.addWidget(QLabel("Ownership:"))
        self.ownership_badge = QLabel("AUTO")
        self.ownership_badge.setStyleSheet(
            f"background-color: #DCFCE7; color: #15803D; font-weight: bold; "
            f"font-size: {font_size(10)}px; border-radius: {spacing(3)}px; "
            f"padding: {spacing(2)}px {spacing(6)}px;"
        )
        ownership_row.addWidget(self.ownership_badge)
        ownership_row.addStretch()

        self.reset_auto_btn = QPushButton("Reset to Auto")
        self.reset_auto_btn.setStyleSheet(
            f"background-color: #FAFBFC; color: #4F46E5; font-size: {font_size(10)}px; "
            f"padding: {spacing(2)}px {spacing(8)}px; border: 1px solid #4F46E5; "
            f"border-radius: {spacing(3)}px;"
        )
        self.reset_auto_btn.clicked.connect(self._on_reset_auto_clicked)
        ownership_row.addWidget(self.reset_auto_btn)
        layout.addLayout(ownership_row)

        # Scrollable container for dynamic properties (avoids clipping on compact displays)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.form_widget = QWidget()
        self.form_layout = QFormLayout(self.form_widget)
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(spacing(8))

        # Common Controls
        self.name_edit = QLineEdit()
        self.name_edit.setReadOnly(True)
        self.form_layout.addRow("ID:", self.name_edit)

        # Position X, Y
        pos_row = QHBoxLayout()
        pos_row.setSpacing(spacing(4))
        self.pos_x_spin = QSpinBox()
        self.pos_x_spin.setRange(-500, 2500)
        self.pos_x_spin.valueChanged.connect(lambda v: self._emit_prop("x", v))
        pos_row.addWidget(QLabel("X:"))
        pos_row.addWidget(self.pos_x_spin)

        self.pos_y_spin = QSpinBox()
        self.pos_y_spin.setRange(-500, 2000)
        self.pos_y_spin.valueChanged.connect(lambda v: self._emit_prop("y", v))
        pos_row.addWidget(QLabel("Y:"))
        pos_row.addWidget(self.pos_y_spin)
        self.form_layout.addRow("Position:", pos_row)

        # Scale Factor / Zoom
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.1, 5.0)
        self.scale_spin.setSingleStep(0.05)
        self.scale_spin.setValue(1.0)
        self.scale_spin.valueChanged.connect(lambda v: self._emit_prop("scale", v))
        self.form_layout.addRow("Scale / Zoom:", self.scale_spin)

        # Animation Style / SFX Type
        self.anim_combo = QComboBox()
        self.anim_combo.addItems([
            "Outside-In Pen",
            "Contour Stroke Draw",
            "Hand Slide from Left",
            "Hand Slide from Right",
            "Smooth Fade In",
            "Pop & Bounce",
        ])
        self.anim_combo.currentTextChanged.connect(lambda t: self._emit_prop("animation_style", t))
        self.form_layout.addRow("Animation:", self.anim_combo)

        # Timing: Start Time
        self.start_time_spin = QDoubleSpinBox()
        self.start_time_spin.setRange(0.0, 3600.0)
        self.start_time_spin.setSingleStep(0.1)
        self.start_time_spin.setSuffix(" s")
        self.start_time_spin.valueChanged.connect(lambda v: self._emit_prop("start_time", v))
        self.form_layout.addRow("Start Time:", self.start_time_spin)

        # Timing: Draw Duration
        self.draw_dur_spin = QDoubleSpinBox()
        self.draw_dur_spin.setRange(0.1, 30.0)
        self.draw_dur_spin.setSingleStep(0.1)
        self.draw_dur_spin.setValue(0.8)
        self.draw_dur_spin.setSuffix(" s")
        self.draw_dur_spin.valueChanged.connect(lambda v: self._emit_prop("draw_duration", v))
        self.form_layout.addRow("Draw Time:", self.draw_dur_spin)

        # Timing: Hold Duration
        self.hold_dur_spin = QDoubleSpinBox()
        self.hold_dur_spin.setRange(0.0, 60.0)
        self.hold_dur_spin.setSingleStep(0.2)
        self.hold_dur_spin.setValue(2.0)
        self.hold_dur_spin.setSuffix(" s")
        self.hold_dur_spin.valueChanged.connect(lambda v: self._emit_prop("hold_duration", v))
        self.form_layout.addRow("Hold Time:", self.hold_dur_spin)

        # Semantic Trigger Anchor
        self.trigger_edit = QLineEdit()
        self.trigger_edit.setPlaceholderText("Spoken Whisper keyword...")
        self.trigger_edit.textChanged.connect(lambda t: self._emit_prop("anchor_word", t))
        self.form_layout.addRow("Trigger Word:", self.trigger_edit)

        self.scroll_area.setWidget(self.form_widget)
        layout.addWidget(self.scroll_area, stretch=1)

        # Remove Item button
        self.delete_btn = QPushButton("🗑️ Remove Selected")
        self.delete_btn.setStyleSheet(
            f"background-color: #FEE2E2; color: #B91C1C; padding: {spacing(6)}px; "
            f"font-weight: bold; border-radius: {spacing(4)}px; font-size: {font_size(11)}px;"
        )
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self.delete_btn)

        # Initial Empty State
        self.show_empty()

    def show_empty(self) -> None:
        """Display placeholder when no element or camera is selected."""
        self.current_item_id = None
        self.current_item_type = "none"
        self.header_title.setText("INSPECTOR (No Selection)")
        self.form_widget.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.reset_auto_btn.setEnabled(False)
        self.name_edit.setText("None selected")
        self.ownership_badge.setText("—")
        self.ownership_badge.setStyleSheet(
            f"background-color: #FAFBFC; color: #667085; padding: {spacing(2)}px {spacing(6)}px;"
        )

    def _set_ownership_display(self, ownership: str) -> None:
        tag = ownership.upper()
        self.ownership_badge.setText(tag)
        sv = scaled_stylesheet_values()
        pad = f"padding: {spacing(2)}px {spacing(6)}px; border-radius: {spacing(3)}px; font-size: {font_size(10)}px; font-weight: bold;"
        if tag == "USER_OVERRIDE":
            self.ownership_badge.setStyleSheet(f"background-color: #FFEDD5; color: #FEF3C7; {pad}")
            self.reset_auto_btn.setEnabled(True)
        elif tag == "LOCKED":
            self.ownership_badge.setStyleSheet(f"background-color: #FEE2E2; color: #B91C1C; {pad}")
            self.reset_auto_btn.setEnabled(False)
        else:
            self.ownership_badge.setStyleSheet(f"background-color: #DCFCE7; color: #15803D; {pad}")
            self.reset_auto_btn.setEnabled(False)

    def inspect_element(self, element_id: str, data: Dict[str, Any]) -> None:
        """Populate inspector with visual element attributes."""
        self._block_signals = True
        self.current_item_id = element_id
        self.current_item_type = "element"
        self.header_title.setText(f"VISUAL ASSET: {element_id}")
        self.form_widget.setEnabled(True)
        self.delete_btn.setEnabled(True)

        self._set_ownership_display(data.get("ownership", "AUTO"))

        self.name_edit.setText(element_id)
        self.pos_x_spin.setValue(int(data.get("x", data.get("cx", 100))))
        self.pos_y_spin.setValue(int(data.get("y", data.get("cy", 100))))
        self.scale_spin.setValue(float(data.get("scale", 1.0)))

        anim = data.get("animation_style", "Outside-In Pen")
        idx = self.anim_combo.findText(anim)
        if idx >= 0:
            self.anim_combo.setCurrentIndex(idx)

        self.start_time_spin.setValue(float(data.get("start_time", 0.5)))
        self.draw_dur_spin.setValue(float(data.get("draw_duration", 0.8)))
        self.hold_dur_spin.setValue(float(data.get("hold_duration", 2.0)))
        self.trigger_edit.setText(data.get("anchor_word", data.get("aid", "")))

        self._block_signals = False

    def inspect_camera(self, camera_name: str, data: Dict[str, Any]) -> None:
        """Populate inspector with camera shot attributes."""
        self._block_signals = True
        self.current_item_id = camera_name
        self.current_item_type = "camera"
        self.header_title.setText(f"CAMERA SHOT: {camera_name}")
        self.form_widget.setEnabled(True)
        self.delete_btn.setEnabled(False)

        self._set_ownership_display(data.get("ownership", "AUTO"))

        self.name_edit.setText(camera_name)
        self.pos_x_spin.setValue(int(data.get("center_x", 960)))
        self.pos_y_spin.setValue(int(data.get("center_y", 540)))
        self.scale_spin.setValue(float(data.get("zoom", 1.0)))
        self.start_time_spin.setValue(float(data.get("start_time", 0.0)))
        self.draw_dur_spin.setValue(float(data.get("duration", 4.0)))
        self.trigger_edit.setText(data.get("speech_phrase", ""))

        self._block_signals = False

    def inspect_sfx(self, sfx_id: str, data: Dict[str, Any]) -> None:
        """Populate inspector with SFX cue attributes."""
        self._block_signals = True
        self.current_item_id = sfx_id
        self.current_item_type = "sfx"
        self.header_title.setText(f"SFX CUE: {sfx_id}")
        self.form_widget.setEnabled(True)
        self.delete_btn.setEnabled(True)

        self._set_ownership_display(data.get("ownership", "AUTO"))

        self.name_edit.setText(sfx_id)
        self.start_time_spin.setValue(float(data.get("timestamp", data.get("start_time", 0.0))))

        sfx_t = data.get("sfx_type", "pop")
        idx = self.anim_combo.findText(sfx_t)
        if idx >= 0:
            self.anim_combo.setCurrentIndex(idx)
        else:
            self.anim_combo.addItem(sfx_t)
            self.anim_combo.setCurrentText(sfx_t)

        self._block_signals = False

    def update_position(self, x: float, y: float, scale: float) -> None:
        """Update spinboxes silently when item is dragged on canvas."""
        self._block_signals = True
        self.pos_x_spin.setValue(int(x))
        self.pos_y_spin.setValue(int(y))
        self.scale_spin.setValue(float(scale))
        self._set_ownership_display("USER_OVERRIDE")
        self._block_signals = False

    def _emit_prop(self, prop_name: str, value: Any) -> None:
        if self._block_signals or not self.current_item_id:
            return
        self._set_ownership_display("USER_OVERRIDE")
        self.property_changed.emit(self.current_item_id, prop_name, value)

    def _on_reset_auto_clicked(self) -> None:
        if self.current_item_id:
            self.reset_to_auto_requested.emit(self.current_item_id)
            self._set_ownership_display("AUTO")

    def _on_delete_clicked(self) -> None:
        if self.current_item_id:
            self.remove_item_requested.emit(self.current_item_id)
            self.show_empty()
