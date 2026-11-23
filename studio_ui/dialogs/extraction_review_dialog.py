"""Extraction Review & Human Inspection Dialog for Whiteboard Studio.

Part of Phase 7: Human Review Gates & Inspection Dialogs.
Allows interactive visual verification, split/merge/recrop, and approval of extracted assets.
Supports direct bounding box drawing, 3-way splitting, horizontal/vertical splitting,
instant deletion of faulty selections, and RGBA re-cropping.
Designed with Fluent 2-inspired Light 2026 Theme and centralized responsive metrics (zero clipping).
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
from production_engine.dynamic_storyboard_extractor import DynamicStoryboardExtractor
from studio_ui.qt import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPixmap,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    Qt,
    QVBoxLayout,
    QWidget,
    Signal,
)
from studio_ui.responsive import (
    control_height,
    font_size,
    page_margin,
    scaled_stylesheet_values,
    spacing,
)
from studio_ui.views.storyboard_review_canvas import StoryboardReviewCanvas


class AssetCardWidget(QFrame):
    """Card widget representing an individual extracted visual asset."""

    clicked = Signal(str)  # asset_id

    def __init__(
        self,
        asset_id: str,
        asset_data: Dict[str, Any],
        section_path: Path,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.asset_id = asset_id
        self.asset_data = asset_data
        self.section_path = section_path
        self.is_selected = False
        self.is_excluded = asset_data.get("excluded", False)

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._init_ui()
        self._update_style()

    def _init_ui(self) -> None:
        sv = scaled_stylesheet_values()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(spacing(8), spacing(8), spacing(8), spacing(8))
        layout.setSpacing(spacing(6))

        # Asset Thumbnail
        self.thumb_label = QLabel()
        self.thumb_label.setMinimumSize(spacing(120), spacing(90))
        self.thumb_label.setMaximumSize(spacing(160), spacing(110))
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet("background-color: #FFFFFF; border-radius: 4px;")

        self.reload_thumbnail()
        layout.addWidget(self.thumb_label)

        # Asset ID & Class
        self.id_label = QLabel(self.asset_id)
        self.id_label.setStyleSheet(f"font-weight: bold; font-size: {sv['small_font']}px; color: #101828;")
        layout.addWidget(self.id_label)

        bbox = self.asset_data.get("orig_box") or self.asset_data.get("bbox") or [0, 0, 0, 0]
        self.meta_label = QLabel(f"Box: {bbox[0]},{bbox[1]} ({bbox[2]}x{bbox[3]})")
        self.meta_label.setStyleSheet(f"font-size: {max(9, sv['small_font'] - 1)}px; color: #475467;")
        layout.addWidget(self.meta_label)

        # Status badge
        self.status_label = QLabel("EXCLUDED" if self.is_excluded else "ACTIVE")
        self.status_label.setStyleSheet(
            f"font-size: {max(9, sv['small_font'] - 2)}px; font-weight: bold; color: #DC2626;"
            if self.is_excluded
            else f"font-size: {max(9, sv['small_font'] - 2)}px; font-weight: bold; color: #16A34A;"
        )
        layout.addWidget(self.status_label)

    def reload_thumbnail(self) -> None:
        img_name = self.asset_data.get("file", f"{self.asset_id}.png")
        img_path = self.section_path / "assets" / img_name
        if not img_path.exists():
            img_path = self.section_path / img_name

        if img_path.exists():
            pix = QPixmap(str(img_path))
            if not pix.isNull():
                self.thumb_label.setPixmap(
                    pix.scaled(
                        spacing(130),
                        spacing(95),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self.thumb_label.setText("No Image")
        else:
            self.thumb_label.setText("Missing PNG")

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.asset_id)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        self._update_style()

    def set_excluded(self, excluded: bool) -> None:
        self.is_excluded = excluded
        self.asset_data["excluded"] = excluded
        self.status_label.setText("EXCLUDED" if excluded else "ACTIVE")
        self.status_label.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #DC2626;"
            if excluded
            else "font-size: 12px; font-weight: bold; color: #16A34A;"
        )
        self._update_style()

    def _update_style(self) -> None:
        if self.is_selected:
            self.setStyleSheet(
                "AssetCardWidget { background-color: #FAFBFC; border: 2px solid #4F46E5; border-radius: 6px; }"
            )
        elif self.is_excluded:
            self.setStyleSheet(
                "AssetCardWidget { background-color: #FFFFFF; border: 1px dashed #DC2626; border-radius: 6px; opacity: 0.5; }"
            )
        else:
            self.setStyleSheet(
                "AssetCardWidget { background-color: #FAFBFC; border: 1px solid #E4E7EC; border-radius: 6px; }"
            )


class ExtractionReviewWidget(QWidget):
    """Reusable interactive widget for reviewing, correcting, and editing extracted elements."""

    assets_changed = Signal()

    def __init__(
        self,
        project_id: str,
        section_id: str,
        section_path: Path,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.project_id = project_id
        self.section_id = section_id
        self.section_path = Path(section_path).resolve()
        self.extractor = DynamicStoryboardExtractor(str(self.section_path))

        self.assets_data: Dict[str, Any] = {}
        self.card_widgets: Dict[str, AssetCardWidget] = {}
        self.selected_asset_id: Optional[str] = None

        self._load_extraction_data()
        self._init_ui()

    def _load_extraction_data(self) -> None:
        """Load asset metadata from assets/metadata.json or fallback files."""
        meta_file = self.section_path / "assets" / "metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.assets_data = data.get("assets", data)
                    elif isinstance(data, list):
                        self.assets_data = {item.get("id", f"asset_{i:02d}"): item for i, item in enumerate(data)}
            except Exception as e:
                print(f"[ExtractionReview] Warning reading metadata.json: {e}")

        # Fallback: scan asset PNGs if metadata empty
        if not self.assets_data:
            assets_dir = self.section_path / "assets"
            if assets_dir.is_dir():
                for p in sorted(assets_dir.glob("*.png")):
                    if p.name != "storyboard.png":
                        aid = p.stem
                        self.assets_data[aid] = {
                            "id": aid,
                            "file": p.name,
                            "orig_box": [0, 0, 100, 100],
                            "label": aid,
                            "excluded": False,
                        }

    def _init_ui(self) -> None:
        sv = scaled_stylesheet_values()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(spacing(8), spacing(8), spacing(8), spacing(8))
        main_layout.setSpacing(spacing(8))

        # Header Info Banner
        header = QFrame()
        header.setStyleSheet("background-color: #FAFBFC; border-radius: 8px; padding: 6px;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(spacing(10), spacing(6), spacing(10), spacing(6))

        self.info_lbl = QLabel(
            f"<b>القسم:</b> {self.section_id} &nbsp;|&nbsp; <b>العناصر المكتشفة:</b> {len(self.assets_data)}"
        )
        self.info_lbl.setStyleSheet(f"font-size: {sv['body_font']}px; color: #101828;")
        h_layout.addWidget(self.info_lbl)

        h_layout.addStretch()

        help_lbl = QLabel("💡 يمكنك رسم صندوق جديد بالماوس، أو حذف التحديد الخاطئ، أو تقسيم العناصر المدمجة.")
        help_lbl.setStyleSheet(f"color: #475467; font-size: {sv['small_font']}px;")
        h_layout.addWidget(help_lbl)

        main_layout.addWidget(header)

        # Splitter: Left Canvas/Grid Tabs, Right Scrollable Inspector
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Tabs (Canvas View & Cards Gallery)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #E4E7EC; background-color: #FFFFFF; border-radius: 6px; }
            QTabBar::tab { background: #FAFBFC; color: #475467; padding: 6px 14px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }
            QTabBar::tab:selected { background: #4F46E5; color: #FFFFFF; font-weight: bold; }
        """)

        # Tab 1: Storyboard Canvas
        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(spacing(4), spacing(4), spacing(4), spacing(4))
        canvas_layout.setSpacing(spacing(6))

        # Canvas toolbar
        tool_bar = QHBoxLayout()
        tool_bar.setSpacing(spacing(6))

        self.tool_select_btn = QPushButton("🔍 وضع التحديد والتحريك")
        self.tool_select_btn.setCheckable(True)
        self.tool_select_btn.setChecked(True)
        self.tool_select_btn.setFixedHeight(control_height(26))
        self.tool_select_btn.clicked.connect(lambda: self._set_canvas_mode("select"))

        self.tool_draw_btn = QPushButton("✏️ وضع التحديد اليدوي (رسم بالماوس)")
        self.tool_draw_btn.setCheckable(True)
        self.tool_draw_btn.setFixedHeight(control_height(26))
        self.tool_draw_btn.setStyleSheet("font-weight: bold; color: #4F46E5;")
        self.tool_draw_btn.clicked.connect(lambda: self._set_canvas_mode("draw"))

        self.continuous_cb = QCheckBox("✏️ استمرار وضع الرسم")
        self.continuous_cb.setStyleSheet(f"color: #344054; font-size: {sv['small_font']}px;")
        self.continuous_cb.toggled.connect(self._toggle_continuous_draw)

        self.quick_del_btn = QPushButton("🗑️ حذف التحديد")
        self.quick_del_btn.setFixedHeight(control_height(26))
        self.quick_del_btn.setStyleSheet("background-color: #FEE2E2; color: #B91C1C; padding: 2px 10px; border-radius: 4px;")
        self.quick_del_btn.clicked.connect(lambda: self._delete_selected_no_confirm())

        tool_bar.addWidget(self.tool_select_btn)
        tool_bar.addWidget(self.tool_draw_btn)
        tool_bar.addWidget(self.continuous_cb)
        tool_bar.addStretch()
        tool_bar.addWidget(self.quick_del_btn)
        canvas_layout.addLayout(tool_bar)

        self.canvas = StoryboardReviewCanvas()
        sb_path = self.section_path / "storyboard.png"
        self.canvas.set_storyboard_image(sb_path)
        self.canvas.set_boxes(self.assets_data)
        self.canvas.asset_selected.connect(self._on_asset_selected)
        self.canvas.new_box_created.connect(self._on_new_box_drawn)
        self.canvas.box_modified.connect(self._on_box_modified)
        self.canvas.delete_requested.connect(self._delete_selected_no_confirm)
        self.canvas.split_requested.connect(self._handle_split_requested)
        self.canvas.exclude_toggle_requested.connect(self._toggle_exclude_selected)

        canvas_layout.addWidget(self.canvas)
        self.tabs.addTab(canvas_container, "🖼️ لوحة القصة وصناديق التحديد (Canvas)")

        # Tab 2: Asset Cards Gallery
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #FFFFFF; border: none;")

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(spacing(10), spacing(10), spacing(10), spacing(10))
        self.grid_layout.setSpacing(spacing(10))
        self._populate_grid_cards()

        self.scroll_area.setWidget(self.grid_container)
        self.tabs.addTab(self.scroll_area, "🗂️ معرض العناصر المفرغة (Cards)")

        self.splitter.addWidget(self.tabs)

        # Right: Detail & Tool Panel (Wrapped inside a ScrollArea for 100% responsive safety)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        right_panel = QFrame()
        right_panel.setMinimumWidth(spacing(240))
        right_panel.setStyleSheet("background-color: #FAFBFC; border-radius: 8px;")
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(spacing(10), spacing(10), spacing(10), spacing(10))
        rp_layout.setSpacing(spacing(8))

        rp_title = QLabel("خصائص وتعديل العنصر")
        rp_title.setStyleSheet(f"font-size: {sv['body_font']}px; font-weight: bold; color: #4F46E5;")
        rp_layout.addWidget(rp_title)

        # ── Card 1: Element Preview ──
        prev_card = QFrame()
        prev_card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E4E7EC; border-radius: 6px; padding: 6px;")
        pc_layout = QVBoxLayout(prev_card)
        pc_layout.setContentsMargins(spacing(6), spacing(6), spacing(6), spacing(6))
        pc_layout.setSpacing(spacing(4))

        self.detail_image = QLabel()
        self.detail_image.setMinimumHeight(spacing(100))
        self.detail_image.setMaximumHeight(spacing(150))
        self.detail_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_image.setStyleSheet("background-color: #F5F6F8; border-radius: 4px;")
        pc_layout.addWidget(self.detail_image)

        self.detail_id = QLabel("اختر عنصراً لتعديله")
        self.detail_id.setStyleSheet(f"font-weight: bold; font-size: {sv['small_font']}px; color: #101828;")
        pc_layout.addWidget(self.detail_id)

        self.detail_meta = QLabel("")
        self.detail_meta.setStyleSheet(f"font-size: {max(9, sv['small_font'] - 1)}px; color: #475467;")
        self.detail_meta.setWordWrap(True)
        pc_layout.addWidget(self.detail_meta)
        rp_layout.addWidget(prev_card)

        # ── Card 2: Split Tools ──
        split_card = QFrame()
        split_card.setStyleSheet("background-color: #F0F2F5; border: 1px solid #E4E7EC; border-radius: 6px; padding: 6px;")
        sc_layout = QVBoxLayout(split_card)
        sc_layout.setContentsMargins(spacing(8), spacing(8), spacing(8), spacing(8))
        sc_layout.setSpacing(spacing(6))

        sc_title = QLabel("أدوات تقسيم العناصر المدمجة")
        sc_title.setStyleSheet(f"font-weight: bold; font-size: {sv['small_font']}px; color: #4F46E5;")
        sc_layout.addWidget(sc_title)

        btn_h = control_height(26)
        btn_style = f"QPushButton {{ background-color: #E4E7EC; color: #101828; padding: 4px 8px; border-radius: 4px; font-size: {sv['small_font']}px; font-weight: bold; }} QPushButton:hover {{ background-color: #D0D5DD; }}"
        accent_btn_style = f"QPushButton {{ background-color: #4F46E5; color: #FFFFFF; padding: 4px 8px; border-radius: 4px; font-size: {sv['small_font']}px; font-weight: bold; }} QPushButton:hover {{ background-color: #4338CA; }}"

        # 3-way Split
        self.split_3_btn = QPushButton("✂️ تقسيم إلى 3 عناصر (يسار/وسط/يمين)")
        self.split_3_btn.setFixedHeight(btn_h)
        self.split_3_btn.setStyleSheet(accent_btn_style)
        self.split_3_btn.clicked.connect(self._split_3_parts)
        sc_layout.addWidget(self.split_3_btn)

        # 2-way Split L/R
        self.split_lr_btn = QPushButton("✂️ تقسيم أفقي لنصفين (يسار / يمين)")
        self.split_lr_btn.setFixedHeight(btn_h)
        self.split_lr_btn.setStyleSheet(btn_style)
        self.split_lr_btn.clicked.connect(self._split_left_right)
        sc_layout.addWidget(self.split_lr_btn)

        # 2-way Split T/B
        self.split_tb_btn = QPushButton("✂️ تقسيم رأسي لنصفين (أعلى / أسفل)")
        self.split_tb_btn.setFixedHeight(btn_h)
        self.split_tb_btn.setStyleSheet(btn_style)
        self.split_tb_btn.clicked.connect(self._split_top_bottom)
        sc_layout.addWidget(self.split_tb_btn)

        self.merge_btn = QPushButton("🔗 دمج مع العنصر التالي")
        self.merge_btn.setFixedHeight(btn_h)
        self.merge_btn.setStyleSheet(btn_style)
        self.merge_btn.clicked.connect(self._merge_selected_with_next)
        sc_layout.addWidget(self.merge_btn)

        rp_layout.addWidget(split_card)

        # ── Card 3: Actions & Delete ──
        act_card = QFrame()
        act_card.setStyleSheet("background-color: #F0F2F5; border: 1px solid #E4E7EC; border-radius: 6px; padding: 6px;")
        ac_layout = QVBoxLayout(act_card)
        ac_layout.setContentsMargins(spacing(8), spacing(8), spacing(8), spacing(8))
        ac_layout.setSpacing(spacing(6))

        self.tighten_btn = QPushButton("🔄 إعادة قص وتفريغ تلقائي")
        self.tighten_btn.setFixedHeight(btn_h)
        self.tighten_btn.setStyleSheet(btn_style)
        self.tighten_btn.clicked.connect(self._tighten_crop_selected)
        ac_layout.addWidget(self.tighten_btn)

        self.exclude_btn = QPushButton("🚫 استبعاد / تفعيل العنصر")
        self.exclude_btn.setFixedHeight(btn_h)
        self.exclude_btn.setStyleSheet(btn_style)
        self.exclude_btn.clicked.connect(self._toggle_exclude_selected)
        ac_layout.addWidget(self.exclude_btn)

        self.delete_btn = QPushButton("🗑️ حذف هذا التحديد الخاطئ")
        self.delete_btn.setFixedHeight(btn_h)
        self.delete_btn.setStyleSheet(f"QPushButton {{ background-color: #FEE2E2; color: #B91C1C; padding: 4px 8px; border-radius: 4px; font-size: {sv['small_font']}px; font-weight: bold; }} QPushButton:hover {{ background-color: #DC2626; }}")
        self.delete_btn.clicked.connect(lambda: self._delete_selected_no_confirm())
        ac_layout.addWidget(self.delete_btn)

        rp_layout.addWidget(act_card)
        rp_layout.addStretch()

        right_scroll.setWidget(right_panel)
        self.splitter.addWidget(right_scroll)

        # Balanced splitter sizes: 70% canvas, 30% tools
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)

        main_layout.addWidget(self.splitter)

        if self.assets_data:
            first_id = next(iter(self.assets_data.keys()))
            self._on_asset_selected(first_id)

    def _set_canvas_mode(self, mode: str) -> None:
        self.tool_select_btn.setChecked(mode == "select")
        self.tool_draw_btn.setChecked(mode == "draw")
        self.canvas.set_mode(mode)

    def _toggle_continuous_draw(self, enabled: bool) -> None:
        self.canvas.set_continuous_draw(enabled)
        if enabled:
            self._set_canvas_mode("draw")

    def _populate_grid_cards(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.card_widgets.clear()

        col = 0
        row = 0
        for aid, adata in self.assets_data.items():
            card = AssetCardWidget(aid, adata, self.section_path)
            card.clicked.connect(self._on_asset_selected)
            self.card_widgets[aid] = card
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

    def _on_asset_selected(self, asset_id: str) -> None:
        self.selected_asset_id = asset_id
        self.canvas.set_selected_asset(asset_id)

        for aid, card in self.card_widgets.items():
            card.set_selected(aid == asset_id)

        data = self.assets_data.get(asset_id, {})
        self.detail_id.setText(f"العنصر: {asset_id}")

        bbox = data.get("orig_box") or data.get("bbox") or [0, 0, 0, 0]
        status = "مستبعد (Excluded)" if data.get("excluded") else "نشط (Active)"
        self.detail_meta.setText(
            f"الصندوق: [X={bbox[0]}, Y={bbox[1]}, W={bbox[2]}, H={bbox[3]}]\n"
            f"المساحة: {data.get('area', bbox[2]*bbox[3])} px\n"
            f"الحالة: {status}"
        )

        img_name = data.get("file", f"{asset_id}.png")
        img_path = self.section_path / "assets" / img_name
        if img_path.exists():
            pix = QPixmap(str(img_path))
            if not pix.isNull():
                self.detail_image.setPixmap(
                    pix.scaled(
                        spacing(220),
                        spacing(140),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self.detail_image.setText("Invalid Image")
        else:
            self.detail_image.setText("Image Not Found")

    def _on_new_box_drawn(self, box: List[int]) -> None:
        """Called when user drags on canvas to create a new manual element."""
        new_id = f"manual_{len(self.assets_data) + 1:02d}"
        res = self.extractor.recrop_and_save_asset(new_id, box, desc=f"Manual Drawn Element {new_id}")
        if res:
            self.assets_data[new_id] = res
            self.canvas.set_boxes(self.assets_data)
            self._populate_grid_cards()
            self._on_asset_selected(new_id)
            self._save_metadata()
            self.info_lbl.setText(
                f"<b>القسم:</b> {self.section_id} &nbsp;|&nbsp; <b>العناصر المكتشفة:</b> {len(self.assets_data)}"
            )
            self.assets_changed.emit()

    def _on_box_modified(self, asset_id: str, new_box: List[int]) -> None:
        """Called when user drags/resizes a box on the canvas."""
        res = self.extractor.recrop_and_save_asset(asset_id, new_box)
        if res:
            self.assets_data[asset_id].update(res)
            self._save_metadata()
            card = self.card_widgets.get(asset_id)
            if card:
                card.asset_data = self.assets_data[asset_id]
                card.reload_thumbnail()
            self._on_asset_selected(asset_id)
            self.assets_changed.emit()

    def _handle_split_requested(self, aid: str, mode: str) -> None:
        self.selected_asset_id = aid
        if mode == "3parts":
            self._split_3_parts()
        elif mode == "lr":
            self._split_left_right()
        elif mode == "tb":
            self._split_top_bottom()

    def _split_3_parts(self) -> None:
        """Splits selected element horizontally into 3 equal sub-elements (left, center, right)."""
        if not self.selected_asset_id or self.selected_asset_id not in self.assets_data:
            return
        box = self.assets_data[self.selected_asset_id].get("orig_box") or self.assets_data[self.selected_asset_id].get("bbox", [0, 0, 150, 100])
        x, y, w, h = box
        w_part = max(20, w // 3)

        box_1 = [x, y, w_part, h]
        box_2 = [x + w_part, y, w_part, h]
        box_3 = [x + 2 * w_part, y, w - 2 * w_part, h]

        id_1 = f"{self.selected_asset_id}_1"
        id_2 = f"{self.selected_asset_id}_2"
        id_3 = f"{self.selected_asset_id}_3"

        res_1 = self.extractor.recrop_and_save_asset(id_1, box_1, desc=f"{self.selected_asset_id} (Part 1)")
        res_2 = self.extractor.recrop_and_save_asset(id_2, box_2, desc=f"{self.selected_asset_id} (Part 2)")
        res_3 = self.extractor.recrop_and_save_asset(id_3, box_3, desc=f"{self.selected_asset_id} (Part 3)")

        if res_1 and res_2 and res_3:
            del self.assets_data[self.selected_asset_id]
            self.assets_data[id_1] = res_1
            self.assets_data[id_2] = res_2
            self.assets_data[id_3] = res_3
            self._refresh_all(select_id=id_1)

    def _split_left_right(self) -> None:
        """Splits selected element horizontally into left and right sub-elements."""
        if not self.selected_asset_id or self.selected_asset_id not in self.assets_data:
            return
        box = self.assets_data[self.selected_asset_id].get("orig_box") or self.assets_data[self.selected_asset_id].get("bbox", [0, 0, 100, 100])
        x, y, w, h = box
        half_w = max(20, w // 2)

        box_left = [x, y, half_w, h]
        box_right = [x + half_w, y, w - half_w, h]

        id_a = f"{self.selected_asset_id}_a"
        id_b = f"{self.selected_asset_id}_b"

        res_a = self.extractor.recrop_and_save_asset(id_a, box_left, desc=f"{self.selected_asset_id} (Part 1)")
        res_b = self.extractor.recrop_and_save_asset(id_b, box_right, desc=f"{self.selected_asset_id} (Part 2)")

        if res_a and res_b:
            del self.assets_data[self.selected_asset_id]
            self.assets_data[id_a] = res_a
            self.assets_data[id_b] = res_b
            self._refresh_all(select_id=id_a)

    def _split_top_bottom(self) -> None:
        """Splits selected element vertically into top and bottom sub-elements."""
        if not self.selected_asset_id or self.selected_asset_id not in self.assets_data:
            return
        box = self.assets_data[self.selected_asset_id].get("orig_box") or self.assets_data[self.selected_asset_id].get("bbox", [0, 0, 100, 100])
        x, y, w, h = box
        half_h = max(20, h // 2)

        box_top = [x, y, w, half_h]
        box_bot = [x, y + half_h, w, h - half_h]

        id_a = f"{self.selected_asset_id}_top"
        id_b = f"{self.selected_asset_id}_bot"

        res_a = self.extractor.recrop_and_save_asset(id_a, box_top, desc=f"{self.selected_asset_id} (Top)")
        res_b = self.extractor.recrop_and_save_asset(id_b, box_bot, desc=f"{self.selected_asset_id} (Bottom)")

        if res_a and res_b:
            del self.assets_data[self.selected_asset_id]
            self.assets_data[id_a] = res_a
            self.assets_data[id_b] = res_b
            self._refresh_all(select_id=id_a)

    def _merge_selected_with_next(self) -> None:
        """Merges selected element with the next chronological element."""
        if not self.selected_asset_id:
            return
        keys = list(self.assets_data.keys())
        if self.selected_asset_id not in keys:
            return
        idx = keys.index(self.selected_asset_id)
        if idx >= len(keys) - 1:
            QMessageBox.information(self, "دمج العناصر", "لا يوجد عنصر تالٍ لدمجه مع العنصر المحدد.")
            return

        next_id = keys[idx + 1]
        box1 = self.assets_data[self.selected_asset_id].get("orig_box", [0, 0, 10, 10])
        box2 = self.assets_data[next_id].get("orig_box", [0, 0, 10, 10])

        x1 = min(box1[0], box2[0])
        y1 = min(box1[1], box2[1])
        x2 = max(box1[0] + box1[2], box2[0] + box2[2])
        y2 = max(box1[1] + box1[3], box2[1] + box2[3])
        union_box = [x1, y1, x2 - x1, y2 - y1]

        merged_id = f"merged_{self.selected_asset_id}_{next_id}"
        res = self.extractor.recrop_and_save_asset(merged_id, union_box, desc="Merged Element")
        if res:
            del self.assets_data[self.selected_asset_id]
            del self.assets_data[next_id]
            self.assets_data[merged_id] = res
            self._refresh_all(select_id=merged_id)

    def _tighten_crop_selected(self) -> None:
        if not self.selected_asset_id or self.selected_asset_id not in self.assets_data:
            return
        box = self.assets_data[self.selected_asset_id].get("orig_box", [0, 0, 100, 100])
        res = self.extractor.recrop_and_save_asset(self.selected_asset_id, box)
        if res:
            self.assets_data[self.selected_asset_id].update(res)
            self._refresh_all(select_id=self.selected_asset_id)

    def _toggle_exclude_selected(self, asset_id: Optional[str] = None) -> None:
        aid = asset_id or self.selected_asset_id
        if not aid or aid not in self.assets_data:
            return
        card = self.card_widgets.get(aid)
        new_ex = not self.assets_data[aid].get("excluded", False)
        if card:
            card.set_excluded(new_ex)
        self.assets_data[aid]["excluded"] = new_ex
        self.canvas.set_boxes(self.assets_data)
        self._on_asset_selected(aid)
        self._save_metadata()
        self.assets_changed.emit()

    def _delete_selected_no_confirm(self, asset_id: Optional[str] = None) -> None:
        aid = asset_id or self.selected_asset_id
        if not aid or aid not in self.assets_data:
            return
        del self.assets_data[aid]
        next_id = next(iter(self.assets_data.keys()), None)
        self._refresh_all(select_id=next_id)

    def _refresh_all(self, select_id: Optional[str] = None) -> None:
        self._save_metadata()
        self.canvas.set_boxes(self.assets_data)
        self._populate_grid_cards()
        self.info_lbl.setText(
            f"<b>القسم:</b> {self.section_id} &nbsp;|&nbsp; <b>العناصر المكتشفة:</b> {len(self.assets_data)}"
        )
        if select_id and select_id in self.assets_data:
            self._on_asset_selected(select_id)
        elif self.assets_data:
            self._on_asset_selected(next(iter(self.assets_data.keys())))
        self.assets_changed.emit()

    def _save_metadata(self) -> None:
        """Persist review changes back to assets/metadata.json."""
        meta_file = self.section_path / "assets" / "metadata.json"
        try:
            meta_file.parent.mkdir(parents=True, exist_ok=True)
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(self.assets_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ExtractionReview] Warning saving metadata: {e}")


class ExtractionReviewDialog(QDialog):
    """Review gate inspection dialog for extracted storyboard visual elements."""

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

        self.setWindowTitle(f"مراجعة وتعديل العناصر — المشهد: {section_id}")
        self._init_adaptive_size()
        self._init_ui()

    def _init_adaptive_size(self) -> None:
        app = QApplication.instance()
        screen = self.screen() if app else None
        if screen:
            avail = screen.availableGeometry()
            target_w = max(spacing(900), min(spacing(1200), int(avail.width() * 0.85)))
            target_h = max(spacing(600), min(spacing(800), int(avail.height() * 0.85)))
            self.resize(target_w, target_h)
        else:
            self.resize(1000, 680)
        self.setMinimumSize(spacing(840), spacing(540))

    def _init_ui(self) -> None:
        sv = scaled_stylesheet_values()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(spacing(10), spacing(10), spacing(10), spacing(10))
        layout.setSpacing(spacing(8))

        self.review_widget = ExtractionReviewWidget(
            project_id=self.project_id,
            section_id=self.section_id,
            section_path=self.section_path,
            parent=self,
        )
        layout.addWidget(self.review_widget)

        footer = QHBoxLayout()
        btn_h = control_height(28)

        reject_btn = QPushButton("إعادة الاستخراج من البداية")
        reject_btn.setFixedHeight(btn_h)
        reject_btn.setStyleSheet("background-color: #FEE2E2; color: #B91C1C; font-weight: bold; padding: 4px 16px; border-radius: 4px;")
        reject_btn.clicked.connect(self._on_reject)
        footer.addWidget(reject_btn)

        footer.addStretch()

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setFixedHeight(btn_h)
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)

        approve_btn = QPushButton("✓ اعتماد العناصر ومتابعة ➔")
        approve_btn.setFixedHeight(btn_h)
        approve_btn.setObjectName("primaryButton")
        approve_btn.setStyleSheet("background-color: #4F46E5; color: #FFFFFF; font-weight: bold; padding: 4px 24px; border-radius: 6px;")
        approve_btn.clicked.connect(self._on_approve)
        footer.addWidget(approve_btn)

        layout.addLayout(footer)

    def _on_reject(self) -> None:
        reply = QMessageBox.question(
            self,
            "تأكيد إعادة الاستخراج",
            "هل ترغب بإلغاء العناصر الحالية وإعادة تشغيل الاستخراج التلقائي؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            state = self.state_store.load_state(self.project_id)
            sec = state.get_or_create_section(self.section_id)
            sec.set_review_gate(StageIdentifier.EXTRACTION.value, ReviewGateStatus.REJECTED)
            self.state_store.save_state(state)

            if self.event_bus:
                self.event_bus.publish(
                    ReviewGateChangedEvent(
                        project_id=self.project_id,
                        section_id=self.section_id,
                        stage_id=StageIdentifier.EXTRACTION.value,
                        old_status=ReviewGateStatus.REVIEW_PENDING,
                        new_status=ReviewGateStatus.REJECTED,
                        reason="User rejected extraction assets.",
                    )
                )
            self.reject()

    def _on_approve(self) -> None:
        self.review_widget._save_metadata()

        state = self.state_store.load_state(self.project_id)
        sec = state.get_or_create_section(self.section_id)
        sec.set_review_gate(StageIdentifier.EXTRACTION.value, ReviewGateStatus.APPROVED)
        self.state_store.save_state(state)

        if self.event_bus:
            self.event_bus.publish(
                ReviewGateChangedEvent(
                    project_id=self.project_id,
                    section_id=self.section_id,
                    stage_id=StageIdentifier.EXTRACTION.value,
                    old_status=ReviewGateStatus.REVIEW_PENDING,
                    new_status=ReviewGateStatus.APPROVED,
                    reason="User approved extraction assets.",
                )
            )

        self.review_approved.emit(self.section_id, StageIdentifier.EXTRACTION.value)
        self.accept()
