"""Element Extraction Panel -- Storyboard element inspection, right-click contextual management, and re-extraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from studio_ui.qt import (
    QAbstractItemView,
    QColor,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPixmap,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    Qt,
    Signal,
)
from studio_ui.views.storyboard_review_canvas import StoryboardReviewCanvas


class ExtractionLogView(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet(
            "QTextEdit { background-color: #F5F6F8; color: #667085; font-family: Consolas, monospace; "
            "font-size: 12px; border: 1px solid #D0D5DD; border-radius: 4px; }"
        )
        self.setMaximumHeight(90)

    def append_line(self, text: str, color: str = "#667085") -> None:
        self.append(f"<span style=color:{color}>{text}</span>")
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    def log_info(self, msg: str) -> None: self.append_line(f"[INFO]  {msg}", "#4F46E5")
    def log_ok(self, msg: str) -> None: self.append_line(f"[OK]    {msg}", "#16A34A")
    def log_warn(self, msg: str) -> None: self.append_line(f"[WARN]  {msg}", "#D97706")
    def log_err(self, msg: str) -> None: self.append_line(f"[ERR]   {msg}", "#DC2626")


class CoordinatesDialog(QDialog):
    """Sleek modal dialog for editing bounding box coordinates (X, Y, W, H) without sidebar clutter."""

    def __init__(self, aid: str, box: List[int], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"تعديل إحداثيات العنصر — {aid}")
        self.setFixedWidth(300)
        self.setStyleSheet("QDialog { background-color: #FFFFFF; color: #101828; }")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        hdr = QLabel(f"<b>تعديل أبعاد وموضع: <span style='color:#4F46E5;'>{aid}</span></b>")
        layout.addWidget(hdr)

        grid = QGridLayout()
        grid.setSpacing(8)

        spin_style = "QSpinBox { background-color: #FAFBFC; color: #101828; border: 1px solid #E4E7EC; border-radius: 4px; padding: 4px; }"

        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 9999)
        self.x_spin.setValue(int(box[0]) if len(box) > 0 else 0)
        self.x_spin.setStyleSheet(spin_style)

        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 9999)
        self.y_spin.setValue(int(box[1]) if len(box) > 1 else 0)
        self.y_spin.setStyleSheet(spin_style)

        self.w_spin = QSpinBox()
        self.w_spin.setRange(1, 9999)
        self.w_spin.setValue(int(box[2]) if len(box) > 2 else 100)
        self.w_spin.setStyleSheet(spin_style)

        self.h_spin = QSpinBox()
        self.h_spin.setRange(1, 9999)
        self.h_spin.setValue(int(box[3]) if len(box) > 3 else 100)
        self.h_spin.setStyleSheet(spin_style)

        grid.addWidget(QLabel("X (الموضع الأفقي):"), 0, 0)
        grid.addWidget(self.x_spin, 0, 1)
        grid.addWidget(QLabel("Y (الموضع الرأسي):"), 1, 0)
        grid.addWidget(self.y_spin, 1, 1)
        grid.addWidget(QLabel("W (العرض):"), 2, 0)
        grid.addWidget(self.w_spin, 2, 1)
        grid.addWidget(QLabel("H (الارتفاع):"), 3, 0)
        grid.addWidget(self.h_spin, 3, 1)

        layout.addLayout(grid)

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    def get_box(self) -> List[int]:
        return [self.x_spin.value(), self.y_spin.value(), self.w_spin.value(), self.h_spin.value()]


class ElementListPanel(QWidget):
    """Clean, uncluttered elements sidebar with drag & drop and full right-click context menu."""

    element_selected = Signal(str)
    element_deleted = Signal(str)
    redraw_requested = Signal(str)
    coords_changed = Signal(str, list)
    order_changed = Signal(list)
    reindex_requested = Signal()
    exclude_toggled = Signal(str)
    rename_requested = Signal(str)
    split_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setStyleSheet("background-color: #FFFFFF; border-right: 1px solid #FAFBFC;")

        self._current_aid: Optional[str] = None
        self._elements_data: Dict[str, Dict[str, Any]] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Header with Count and Quick Actions
        hdr_layout = QHBoxLayout()
        self.hdr_lbl = QLabel("ELEMENTS")
        self.hdr_lbl.setStyleSheet("color: #D97706; font-size: 12px; font-weight: bold;")
        hdr_layout.addWidget(self.hdr_lbl)
        hdr_layout.addStretch()

        self.reindex_btn = QPushButton("🔢 Re-Index")
        self.reindex_btn.setToolTip("إعادة ترقيم العناصر تسلسلياً (elem_01, elem_02...)")
        self.reindex_btn.setStyleSheet("QPushButton { background-color: #FAFBFC; color: #4F46E5; font-size: 12px; font-weight: bold; padding: 3px 8px; border-radius: 3px; border: 1px solid #4F46E5; } QPushButton:hover { background-color: #4F46E5; color: #FFFFFF; }")
        self.reindex_btn.clicked.connect(self.reindex_requested.emit)
        hdr_layout.addWidget(self.reindex_btn)
        layout.addLayout(hdr_layout)

        # Elements List (with drag & drop reorder and custom context menu)
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu)
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #FFFFFF; border: 1px solid #FAFBFC; color: #101828; font-size: 12px; border-radius: 4px; }"
            "QListWidget::item { padding: 5px 6px; border-bottom: 1px solid #202025; }"
            "QListWidget::item:selected { background-color: #4F46E5; color: #FFFFFF; font-weight: bold; }"
            "QListWidget::item:hover { background-color: #FAFBFC; }"
        )
        self.list_widget.currentItemChanged.connect(self._on_item_changed)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)
        layout.addWidget(self.list_widget, stretch=1)

        # Contextual Preview & Helper Info Strip
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #FAFBFC; border-radius: 4px; padding: 4px; }")
        p_layout = QVBoxLayout(self.preview_frame)
        p_layout.setContentsMargins(4, 4, 4, 4)
        p_layout.setSpacing(4)

        self.preview_lbl = QLabel("انقر كليك يمين على أي عنصر للخصائص")
        self.preview_lbl.setFixedHeight(75)
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_lbl.setStyleSheet("QLabel { background-color: #F5F6F8; border: 1px solid #D0D5DD; border-radius: 3px; color: #667085; font-size: 12px; }")
        p_layout.addWidget(self.preview_lbl)

        layout.addWidget(self.preview_frame)

    def set_elements(self, elements: Dict[str, Dict[str, Any]], order: Optional[List[str]] = None) -> None:
        self._elements_data = dict(elements)
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        keys = order if order and all(k in elements for k in order) else list(elements.keys())
        for idx, aid in enumerate(keys, 1):
            data = elements[aid]
            is_ex = data.get("excluded", False)
            icon = "🚫" if is_ex else "✓"
            item = QListWidgetItem(f"{idx:02d}. {icon} {aid}")
            item.setData(Qt.ItemDataRole.UserRole, aid)
            item.setForeground(QColor("#DC2626" if is_ex else "#101828"))
            self.list_widget.addItem(item)

        self.list_widget.blockSignals(False)

        if self._current_aid and self._current_aid in elements:
            self.select_element(self._current_aid)
        elif self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def select_element(self, aid: str) -> None:
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == aid:
                self.list_widget.setCurrentItem(item)
                break

    def update_selected_element_info(
        self,
        aid: str,
        data: Dict[str, Any],
        cropped_pixmap: Optional[QPixmap] = None,
    ) -> None:
        self._current_aid = aid
        if cropped_pixmap and not cropped_pixmap.isNull():
            scaled = cropped_pixmap.scaled(
                self.preview_lbl.width() - 8,
                self.preview_lbl.height() - 8,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.preview_lbl.setPixmap(scaled)
        else:
            self.preview_lbl.setText(f"{aid}\n(كليك يمين للخيارات)")

    def _on_item_changed(self, current, previous) -> None:
        if current:
            aid = current.data(Qt.ItemDataRole.UserRole)
            if aid:
                self.element_selected.emit(aid)

    def _on_rows_moved(self, parent, start, end, destination, row) -> None:
        order = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            aid = item.data(Qt.ItemDataRole.UserRole)
            if aid:
                order.append(aid)
        self.order_changed.emit(order)

    def _on_context_menu(self, pos) -> None:
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        aid = item.data(Qt.ItemDataRole.UserRole)
        if not aid:
            return

        self.show_element_context_menu(aid, self.list_widget.mapToGlobal(pos))

    def show_element_context_menu(self, aid: str, global_pos) -> None:
        """Pops up the rich, contextual right-click properties & action menu for an element."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #FAFBFC; color: #101828; border: 1px solid #E4E7EC; padding: 4px; border-radius: 6px; font-size: 12px; }
            QMenu::item { padding: 5px 20px 5px 10px; }
            QMenu::item:selected { background-color: #4F46E5; }
            QMenu::separator { height: 1px; background-color: #E4E7EC; margin: 4px 6px; }
        """)

        # 1. Redraw Action
        act_redraw = menu.addAction(f"🎯 إعادة تحديد يدوي بالماوس ({aid})")
        # 2. Coordinates Edit Dialog
        act_coords = menu.addAction("📐 تعديل الإحداثيات والأبعاد...")
        # 3. Rename
        act_rename = menu.addAction("🏷️ إعادة تسمية العنصر...")
        menu.addSeparator()

        # 4. Re-ordering
        act_up = menu.addAction("⬆️ تحريك للأعلى في الترتيب")
        act_down = menu.addAction("⬇️ تحريك للأسفل في الترتيب")
        menu.addSeparator()

        # 5. Split Submenu
        split_menu = menu.addMenu("✂️ تقسيم العنصر...")
        split_menu.setStyleSheet(menu.styleSheet())
        act_split_lr = split_menu.addAction("✂️ تقسيم أفقي (يسار / يمين)")
        act_split_tb = split_menu.addAction("✂️ تقسيم رأسي (أعلى / أسفل)")
        act_split_3 = split_menu.addAction("✂️ تقسيم إلى 3 أجزاء")

        # 6. Exclude Toggle
        is_ex = self._elements_data.get(aid, {}).get("excluded", False)
        act_exclude = menu.addAction("✅ تفعيل العنصر (Include)" if is_ex else "🚫 استبعاد العنصر (Exclude)")
        menu.addSeparator()

        # 7. Delete
        act_del = menu.addAction("🗑️ حذف هذا العنصر (Delete)")

        chosen = menu.exec(global_pos)
        if chosen == act_redraw:
            self.redraw_requested.emit(aid)
        elif chosen == act_coords:
            box = self._elements_data.get(aid, {}).get("orig_box") or [0, 0, 100, 100]
            dlg = CoordinatesDialog(aid, box, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.coords_changed.emit(aid, dlg.get_box())
        elif chosen == act_rename:
            self.rename_requested.emit(aid)
        elif chosen == act_up:
            self._move_aid(aid, -1)
        elif chosen == act_down:
            self._move_aid(aid, +1)
        elif chosen == act_split_lr:
            self.split_requested.emit(aid, "lr")
        elif chosen == act_split_tb:
            self.split_requested.emit(aid, "tb")
        elif chosen == act_split_3:
            self.split_requested.emit(aid, "3parts")
        elif chosen == act_exclude:
            self.exclude_toggled.emit(aid)
        elif chosen == act_del:
            self.element_deleted.emit(aid)

    def _move_aid(self, aid: str, offset: int) -> None:
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == aid:
                new_row = i + offset
                if 0 <= new_row < self.list_widget.count():
                    taken = self.list_widget.takeItem(i)
                    self.list_widget.insertItem(new_row, taken)
                    self.list_widget.setCurrentItem(taken)
                    # emit new order
                    order = [self.list_widget.item(j).data(Qt.ItemDataRole.UserRole) for j in range(self.list_widget.count())]
                    self.order_changed.emit(order)
                break


class ElementExtractionPanel(QWidget):
    """Storyboard bounding box editor, manual re-selector, and right-click management."""

    extraction_completed = Signal()
    element_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.section_path: Optional[Path] = None
        self.elements: Dict[str, Dict[str, Any]] = {}
        self._element_order: List[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sleek, minimal toolbar
        toolbar = QFrame()
        toolbar.setFixedHeight(42)
        toolbar.setStyleSheet("background-color: #FFFFFF; border-bottom: 1px solid #FAFBFC;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 4, 12, 4)
        tb_layout.setSpacing(8)

        lbl = QLabel("✂️ Storyboard Element Extraction & Box Editor")
        lbl.setStyleSheet("color: #4F46E5; font-weight: bold; font-size: 12px;")
        tb_layout.addWidget(lbl)
        tb_layout.addStretch()

        # Draw Mode Toggle
        self.manual_mode_btn = QPushButton("🎯 Draw Box Mode")
        self.manual_mode_btn.setCheckable(True)
        self.manual_mode_btn.setToolTip("عند التفعيل: انقر واسحب بالماوس فوق أي رسمة لتحديدها")
        self.manual_mode_btn.setStyleSheet(
            "QPushButton { background-color: #FAFBFC; color: #101828; padding: 4px 12px; font-size: 12px; border-radius: 4px; border: 1px solid #E4E7EC; }"
            "QPushButton:checked { background-color: #16A34A; color: #FFFFFF; font-weight: bold; border-color: #16A34A; }"
        )
        self.manual_mode_btn.clicked.connect(self._toggle_manual_draw_mode)
        tb_layout.addWidget(self.manual_mode_btn)

        tb_layout.addSpacing(10)

        self.re_extract_btn = QPushButton("⚡ Auto Re-Extract")
        self.re_extract_btn.setStyleSheet(
            "background-color: #4F46E5; color: #FFFFFF; padding: 5px 14px; font-size: 12px; font-weight: bold; border-radius: 4px; border: none;"
        )
        self.re_extract_btn.clicked.connect(self._on_re_extract_all)
        tb_layout.addWidget(self.re_extract_btn)

        self.save_boxes_btn = QPushButton("💾 Save & Apply")
        self.save_boxes_btn.setStyleSheet(
            "background-color: #4F46E5; color: #FFFFFF; padding: 5px 14px; font-size: 12px; font-weight: bold; border-radius: 4px; border: none;"
        )
        self.save_boxes_btn.clicked.connect(self._on_save_boxes)
        tb_layout.addWidget(self.save_boxes_btn)

        root.addWidget(toolbar)

        # Splitter: Minimal Sidebar (Left) & Canvas (Center)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.elem_list_panel = ElementListPanel()
        self.elem_list_panel.element_selected.connect(self._on_element_list_selected)
        self.elem_list_panel.element_deleted.connect(self._on_element_deleted)
        self.elem_list_panel.redraw_requested.connect(self._on_redraw_requested)
        self.elem_list_panel.coords_changed.connect(self._on_coords_changed)
        self.elem_list_panel.order_changed.connect(self._on_order_changed)
        self.elem_list_panel.reindex_requested.connect(self._on_reindex_requested)
        self.elem_list_panel.exclude_toggled.connect(self._on_exclude_toggle)
        self.elem_list_panel.rename_requested.connect(self._on_rename_requested)
        self.elem_list_panel.split_requested.connect(self._on_split_requested)
        splitter.addWidget(self.elem_list_panel)

        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(4)

        self.sb_canvas = StoryboardReviewCanvas()
        self.sb_canvas.asset_selected.connect(self._on_canvas_asset_selected)
        self.sb_canvas.box_modified.connect(self._on_box_modified)
        self.sb_canvas.new_box_created.connect(self._on_new_box_created)
        self.sb_canvas.delete_requested.connect(self._on_element_deleted)
        self.sb_canvas.split_requested.connect(self._on_split_requested)
        self.sb_canvas.exclude_toggle_requested.connect(self._on_exclude_toggle)
        center_layout.addWidget(self.sb_canvas, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #FAFBFC; border-radius: 3px; height: 6px; }"
            "QProgressBar::chunk { background-color: #16A34A; border-radius: 3px; }"
        )
        center_layout.addWidget(self.progress_bar)

        self.log_view = ExtractionLogView()
        center_layout.addWidget(self.log_view)

        splitter.addWidget(center_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, 1)

    def load_section(self, section_path: Path) -> None:
        self.section_path = section_path
        self.log_view.clear()
        self.log_view.log_info(f"Loading section: {section_path.name}")
        sb_img = section_path / "storyboard.png"
        if sb_img.exists():
            self.sb_canvas.set_storyboard_image(sb_img)
            self.log_view.log_ok(f"Storyboard loaded ({sb_img.stat().st_size // 1024} KB)")
        else:
            self.sb_canvas.set_storyboard_image("")
            self.log_view.log_warn("storyboard.png not found!")
        self._load_metadata()

    def _load_metadata(self) -> None:
        if not self.section_path:
            return
        self.elements.clear()
        self._element_order.clear()

        meta_file = self.section_path / "assets" / "metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file, encoding="utf-8") as f:
                    mdata = json.load(f)
                raw = mdata.get("assets", mdata)
                for aid, adata in raw.items():
                    if isinstance(adata, dict):
                        self.elements[aid] = adata
                        self._element_order.append(aid)
                self.log_view.log_ok(f"Loaded {len(self.elements)} elements from metadata.json")
            except Exception as e:
                self.log_view.log_err(f"Error reading metadata.json: {e}")

        if not self.elements:
            layout_file = self.section_path / "placed_elements_layout.json"
            if layout_file.exists():
                try:
                    with open(layout_file, encoding="utf-8") as f:
                        ldata = json.load(f)
                    raw_elems = ldata.get("placed_elements", ldata.get("elements", []))
                    if isinstance(raw_elems, list):
                        for el in raw_elems:
                            if isinstance(el, dict):
                                aid = el.get("id", el.get("aid", ""))
                                if aid:
                                    self.elements[aid] = el
                                    self._element_order.append(aid)
                    self.log_view.log_ok(f"Loaded {len(self.elements)} elements from layout json")
                except Exception as e:
                    self.log_view.log_err(f"Error reading layout: {e}")

        self._refresh_canvas_boxes()
        self.elem_list_panel.set_elements(self.elements, self._element_order)

    def _refresh_canvas_boxes(self) -> None:
        boxes = {}
        for aid in self._element_order:
            if aid in self.elements:
                adata = self.elements[aid]
                orig_box = (adata.get("orig_box") or adata.get("bbox") or adata.get("box"))
                if not orig_box:
                    orig_box = [int(adata.get("x", 0)), int(adata.get("y", 0)),
                                int(adata.get("w", adata.get("width", 200))),
                                int(adata.get("h", adata.get("height", 150)))]
                boxes[aid] = {"orig_box": list(orig_box), "excluded": adata.get("excluded", False)}
        self.sb_canvas.set_boxes(boxes)

    def _toggle_manual_draw_mode(self, checked: bool) -> None:
        self.sb_canvas.set_mode("manual_box" if checked else "select")

    def _on_element_list_selected(self, aid: str) -> None:
        self.sb_canvas.set_selected_asset(aid)
        if aid in self.elements:
            box = self.elements[aid].get("orig_box") or self.elements[aid].get("bbox") or [0, 0, 100, 100]
            pix = self.sb_canvas.get_cropped_pixmap(box)
            self.elem_list_panel.update_selected_element_info(aid, self.elements[aid], pix)
        self.element_selected.emit(aid)

    def _on_canvas_asset_selected(self, aid: str) -> None:
        self.elem_list_panel.select_element(aid)
        if aid in self.elements:
            box = self.elements[aid].get("orig_box") or self.elements[aid].get("bbox") or [0, 0, 100, 100]
            pix = self.sb_canvas.get_cropped_pixmap(box)
            self.elem_list_panel.update_selected_element_info(aid, self.elements[aid], pix)
        self.element_selected.emit(aid)

    def _on_redraw_requested(self, aid: str) -> None:
        self.manual_mode_btn.setChecked(True)
        self.sb_canvas.set_mode("manual_box")
        self.sb_canvas.set_selected_asset(aid)

    def _on_coords_changed(self, aid: str, new_box: list) -> None:
        if aid in self.elements:
            self.elements[aid]["orig_box"] = new_box
            self.elements[aid]["bbox"] = new_box
            self._refresh_canvas_boxes()
            pix = self.sb_canvas.get_cropped_pixmap(new_box)
            self.elem_list_panel.update_selected_element_info(aid, self.elements[aid], pix)

    def _on_order_changed(self, new_order: list) -> None:
        self._element_order = list(new_order)
        self._refresh_canvas_boxes()

    def _on_reindex_requested(self) -> None:
        """Renumber all elements sequentially (elem_01, elem_02, ...) based on current order."""
        if not self._element_order:
            return

        reply = QMessageBox.question(
            self,
            "تأكيد إعادة الترقيم (Re-Index)",
            "هل ترغب في إعادة ترقيم جميع العناصر بالتسلسل (elem_01, elem_02, ...) بناءً على الترتيب الحالي؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        new_elements = {}
        new_order = []
        for idx, old_aid in enumerate(self._element_order, 1):
            new_aid = f"elem_{idx:02d}"
            adata = dict(self.elements[old_aid])
            adata["id"] = new_aid
            adata["label"] = adata.get("label", old_aid)
            new_elements[new_aid] = adata
            new_order.append(new_aid)

        self.elements = new_elements
        self._element_order = new_order
        self._refresh_canvas_boxes()
        self.elem_list_panel.set_elements(self.elements, self._element_order)
        self.log_view.log_ok(f"✅ Re-indexed {len(new_order)} elements to sequential IDs.")

    def _on_box_modified(self, aid: str, new_box: list) -> None:
        if aid in self.elements:
            self.elements[aid]["orig_box"] = new_box
            self.elements[aid]["bbox"] = new_box
            pix = self.sb_canvas.get_cropped_pixmap(new_box)
            self.elem_list_panel.update_selected_element_info(aid, self.elements[aid], pix)
            self.log_view.log_info(f"Box updated: {aid} -> {new_box}")

    def _on_new_box_created(self, box: list) -> None:
        idx = 1
        while f"elem_{idx:02d}" in self.elements:
            idx += 1
        aid = f"elem_{idx:02d}"
        self.elements[aid] = {"id": aid, "orig_box": box, "bbox": box, "label": aid, "excluded": False}
        self._element_order.append(aid)
        self.log_view.log_ok(f"New element: {aid}  box={box}")
        self._refresh_canvas_boxes()
        self.elem_list_panel.set_elements(self.elements, self._element_order)
        self.elem_list_panel.select_element(aid)

    def _on_element_deleted(self, aid: str) -> None:
        if aid in self.elements:
            del self.elements[aid]
            if aid in self._element_order:
                self._element_order.remove(aid)
            self.log_view.log_warn(f"Deleted: {aid}")
            self._refresh_canvas_boxes()
            self.elem_list_panel.set_elements(self.elements, self._element_order)

    def _on_rename_requested(self, aid: str) -> None:
        new_name, ok = QInputDialog.getText(self, "إعادة تسمية العنصر", f"الاسم الجديد لـ {aid}:", text=aid)
        if ok and new_name and new_name != aid:
            adata = self.elements.pop(aid)
            adata["id"] = new_name
            adata["label"] = new_name
            self.elements[new_name] = adata
            if aid in self._element_order:
                idx = self._element_order.index(aid)
                self._element_order[idx] = new_name
            self._refresh_canvas_boxes()
            self.elem_list_panel.set_elements(self.elements, self._element_order)
            self.elem_list_panel.select_element(new_name)
            self.log_view.log_ok(f"Renamed {aid} -> {new_name}")

    def _on_split_requested(self, aid: str, split_type: str) -> None:
        if aid not in self.elements:
            return
        box = (self.elements[aid].get("orig_box") or self.elements[aid].get("bbox") or [0, 0, 200, 150])
        x, y, w, h = box
        del self.elements[aid]
        idx = self._element_order.index(aid) if aid in self._element_order else len(self._element_order)
        if aid in self._element_order:
            self._element_order.remove(aid)

        new_ids = []
        if split_type == "lr":
            hw = w // 2
            self.elements[f"{aid}_L"] = {"id": f"{aid}_L", "orig_box": [x, y, hw, h], "bbox": [x, y, hw, h]}
            self.elements[f"{aid}_R"] = {"id": f"{aid}_R", "orig_box": [x + hw, y, w - hw, h], "bbox": [x + hw, y, w - hw, h]}
            new_ids = [f"{aid}_L", f"{aid}_R"]
        elif split_type == "tb":
            hh = h // 2
            self.elements[f"{aid}_T"] = {"id": f"{aid}_T", "orig_box": [x, y, w, hh], "bbox": [x, y, w, hh]}
            self.elements[f"{aid}_B"] = {"id": f"{aid}_B", "orig_box": [x, y + hh, w, h - hh], "bbox": [x, y + hh, w, h - hh]}
            new_ids = [f"{aid}_T", f"{aid}_B"]
        elif split_type == "3parts":
            tw = w // 3
            self.elements[f"{aid}_1"] = {"id": f"{aid}_1", "orig_box": [x, y, tw, h], "bbox": [x, y, tw, h]}
            self.elements[f"{aid}_2"] = {"id": f"{aid}_2", "orig_box": [x + tw, y, tw, h], "bbox": [x + tw, y, tw, h]}
            self.elements[f"{aid}_3"] = {"id": f"{aid}_3", "orig_box": [x + 2 * tw, y, w - 2 * tw, h], "bbox": [x + 2 * tw, y, w - 2 * tw, h]}
            new_ids = [f"{aid}_1", f"{aid}_2", f"{aid}_3"]

        for offset, nid in enumerate(new_ids):
            self._element_order.insert(idx + offset, nid)

        self.log_view.log_ok(f"Split {aid} ({split_type})")
        self._refresh_canvas_boxes()
        self.elem_list_panel.set_elements(self.elements, self._element_order)

    def _on_exclude_toggle(self, aid: str) -> None:
        if aid in self.elements:
            current = self.elements[aid].get("excluded", False)
            self.elements[aid]["excluded"] = not current
            self.log_view.log_info(f"{aid}: {'excluded' if not current else 'included'}")
            self._refresh_canvas_boxes()
            self.elem_list_panel.set_elements(self.elements, self._element_order)
            box = self.elements[aid].get("orig_box") or self.elements[aid].get("bbox") or [0, 0, 100, 100]
            pix = self.sb_canvas.get_cropped_pixmap(box)
            self.elem_list_panel.update_selected_element_info(aid, self.elements[aid], pix)

    def _on_re_extract_all(self) -> None:
        if not self.section_path:
            QMessageBox.warning(self, "No Section", "No section is currently loaded.")
            return
        sb = self.section_path / "storyboard.png"
        if not sb.exists():
            QMessageBox.critical(self, "Missing Storyboard", f"storyboard.png not found in:\n{self.section_path}")
            return
        self.log_view.log_info("Starting auto re-extraction via DynamicStoryboardExtractor...")
        self.re_extract_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        try:
            from production_engine.dynamic_storyboard_extractor import DynamicStoryboardExtractor
            extractor = DynamicStoryboardExtractor(str(self.section_path))
            extractor.extract_assets()
            self.log_view.log_ok("Extraction complete! Reloading metadata...")
            self._load_metadata()
            self.extraction_completed.emit()
        except Exception as e:
            self.log_view.log_err(f"Extraction failed: {e}")
            import traceback
            self.log_view.log_err(traceback.format_exc()[:800])
        finally:
            self.re_extract_btn.setEnabled(True)
            self.progress_bar.setVisible(False)

    def _on_save_boxes(self) -> None:
        if not self.section_path:
            QMessageBox.warning(self, "No Section", "No section is loaded.")
            return

        for aid, box_data in self.sb_canvas.boxes.items():
            if aid in self.elements:
                box = box_data.get("orig_box") or box_data.get("bbox", [])
                if box:
                    self.elements[aid]["orig_box"] = box
                    self.elements[aid]["bbox"] = box
                self.elements[aid]["excluded"] = box_data.get("excluded", False)

        ordered_elements = {}
        for aid in self._element_order:
            if aid in self.elements:
                ordered_elements[aid] = self.elements[aid]
        for aid, el in self.elements.items():
            if aid not in ordered_elements:
                ordered_elements[aid] = el

        self.elements = ordered_elements

        meta_dir = self.section_path / "assets"
        meta_dir.mkdir(exist_ok=True)
        meta_file = meta_dir / "metadata.json"
        try:
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump({"assets": self.elements}, f, indent=2, ensure_ascii=False)
            self.log_view.log_ok(f"Saved {len(self.elements)} elements in order to metadata.json")
        except Exception as e:
            self.log_view.log_err(f"Save metadata failed: {e}")

        layout_file = self.section_path / "placed_elements_layout.json"
        try:
            layout_list = []
            for aid, el in self.elements.items():
                box = el.get("orig_box") or el.get("bbox") or [0, 0, 200, 150]
                layout_list.append({
                    "id": aid,
                    "x": int(box[0]),
                    "y": int(box[1]),
                    "width": int(box[2]),
                    "height": int(box[3]),
                    "orig_box": box,
                    "excluded": el.get("excluded", False),
                })
            with open(layout_file, "w", encoding="utf-8") as f:
                json.dump({"placed_elements": layout_list}, f, indent=2, ensure_ascii=False)
            self.log_view.log_ok("Updated placed_elements_layout.json")
        except Exception as e:
            self.log_view.log_warn(f"Could not update placed_elements_layout.json: {e}")

        QMessageBox.information(
            self,
            "تم الحفظ بنجاح (Saved)",
            f"تم حفظ {len(self.elements)} عنصراً مع الترتيب والتحديدات الجديدة بنجاح!\nسيتم تطبيقها فوراً في الكانفاس والريندر.",
        )
        self.extraction_completed.emit()
