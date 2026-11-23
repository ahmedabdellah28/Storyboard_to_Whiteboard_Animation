"""Approved Light 2026 design-system theme for Whiteboard Studio."""
from __future__ import annotations

from studio_ui.responsive import scaled_stylesheet_values


def _build_light_theme_qss() -> str:
    v = scaled_stylesheet_values()
    return f"""
QWidget {{
    background-color: #F5F6F8;
    color: #101828;
    font-family: "Segoe UI", "Segoe UI Variable", Arial, sans-serif;
    font-size: {v['body_font']}px;
    selection-background-color: #EEF2FF;
    selection-color: #101828;
}}

QMainWindow {{ background: #F5F6F8; }}

QFrame#card {{
    background: #FFFFFF;
    border: 1px solid #E4E7EC;
    border-radius: {v['border_radius']}px;
}}

QFrame#card:hover {{ border-color: #D0D5DD; }}

QMenuBar {{
    background: #FFFFFF;
    border-bottom: 1px solid #E4E7EC;
    padding: {v['pad_xs']}px {v['pad_sm']}px;
    color: #344054;
}}
QMenuBar::item {{ padding: {v['pad_sm']}px {v['pad_md']}px; border-radius: {v['border_radius_sm']}px; }}
QMenuBar::item:selected {{ background: #F0F2F5; color: #4F46E5; }}
QMenu {{ background: #FFFFFF; border: 1px solid #D0D5DD; border-radius: {v['border_radius']}px; padding: {v['pad_sm']}px; }}
QMenu::item {{ padding: {v['pad_sm']}px {v['pad_xxl']}px {v['pad_sm']}px {v['pad_lg']}px; border-radius: {v['border_radius_sm']}px; }}
QMenu::item:selected {{ background: #EEF2FF; color: #4F46E5; }}
QMenu::separator {{ height: 1px; background: #E4E7EC; margin: {v['pad_sm']}px {v['pad_md']}px; }}

QToolBar {{ background: #FFFFFF; border-bottom: 1px solid #E4E7EC; padding: {v['pad_sm']}px; spacing: {v['pad_sm']}px; }}

QPushButton, QToolButton {{
    background: #FFFFFF;
    color: #344054;
    border: 1px solid #D0D5DD;
    border-radius: {v['border_radius_sm']}px;
    padding: {v['pad_sm']}px {v['pad_lg']}px;
    font-weight: 500;
    min-height: {v['ctrl_h_sm']}px;
}}
QPushButton:hover, QToolButton:hover {{ background: #F7F8FA; border-color: #98A2B3; }}
QPushButton:pressed, QToolButton:pressed {{ background: #F0F2F5; }}
QPushButton:disabled, QToolButton:disabled {{ background: #F5F6F8; color: #98A2B3; border-color: #E4E7EC; }}
QPushButton:focus, QToolButton:focus {{ border: 1px solid #4F46E5; }}
QPushButton#primaryButton {{ background: #4F46E5; color: #FFFFFF; border-color: #4F46E5; }}
QPushButton#primaryButton:hover {{ background: #4338CA; border-color: #4338CA; }}
QPushButton#dangerButton {{ background: #DC2626; color: #FFFFFF; border-color: #DC2626; }}
QPushButton#dangerButton:hover {{ background: #B91C1C; border-color: #B91C1C; }}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: #FFFFFF;
    color: #101828;
    border: 1px solid #D0D5DD;
    border-radius: {v['border_radius_sm']}px;
    padding: {v['pad_sm']}px {v['pad_md']}px;
    min-height: {v['ctrl_h_sm']}px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: #4F46E5; }}
QComboBox::drop-down {{ border: none; padding-right: {v['pad_md']}px; }}

QListWidget, QTableWidget, QTreeWidget {{
    background: #FFFFFF;
    color: #101828;
    border: 1px solid #E4E7EC;
    border-radius: {v['border_radius']}px;
    alternate-background-color: #FAFBFC;
}}
QListWidget::item {{ padding: {v['pad_md']}px {v['pad_lg']}px; border-radius: {v['border_radius_sm']}px; margin: 2px 4px; }}
QListWidget::item:hover {{ background: #F7F8FA; }}
QListWidget::item:selected {{ background: #EEF2FF; color: #101828; }}
QHeaderView::section {{ background: #FAFBFC; color: #475467; padding: {v['pad_sm']}px {v['pad_md']}px; border: none; border-bottom: 1px solid #E4E7EC; font-weight: 600; }}

QStatusBar {{ background: #FFFFFF; border-top: 1px solid #E4E7EC; color: #475467; }}
QStatusBar QLabel {{ color: #475467; padding: {v['pad_xs']}px {v['pad_md']}px; }}

QProgressBar {{ background: #F0F2F5; border: 1px solid #E4E7EC; border-radius: {v['border_radius_sm']}px; text-align: center; color: #344054; min-height: {v['ctrl_h_sm']}px; }}
QProgressBar::chunk {{ background: #4F46E5; border-radius: 5px; }}

QTabWidget::pane {{ border: 1px solid #E4E7EC; background: #FFFFFF; }}
QTabBar::tab {{ background: #FAFBFC; color: #667085; padding: {v['pad_md']}px {v['pad_xl']}px; border: 1px solid #E4E7EC; border-bottom: none; margin-right: 2px; }}
QTabBar::tab:selected {{ background: #FFFFFF; color: #4F46E5; font-weight: 600; border-top: 2px solid #4F46E5; }}
QTabBar::tab:hover:!selected {{ background: #F7F8FA; color: #344054; }}

QScrollBar:vertical {{ border: none; background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #C4C9D2; min-height: 36px; border-radius: 5px; }}
QScrollBar::handle:vertical:hover {{ background: #98A2B3; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ border: none; background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #C4C9D2; min-width: 36px; border-radius: 5px; }}
QScrollBar::handle:horizontal:hover {{ background: #98A2B3; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

QScrollArea {{ border: none; background: transparent; }}
QToolTip {{ background: #101828; color: #FFFFFF; border: 1px solid #344054; border-radius: 6px; padding: 6px 8px; }}

/* Keyboard focus: keep a visible indication; do not remove focus outlines globally. */
*:focus {{ outline: none; }}

QSplitter::handle {{ background: #E4E7EC; }}
QSplitter::handle:horizontal {{ width: 4px; }}
QSplitter::handle:vertical {{ height: 4px; }}
QSplitter::handle:hover {{ background: #C4C9D2; }}

QGroupBox {{ border: 1px solid #E4E7EC; border-radius: {v['border_radius']}px; margin-top: {v['pad_lg']}px; padding-top: {v['pad_lg']}px; font-weight: 600; color: #475467; }}
QGroupBox::title {{ subcontrol-origin: margin; padding: 0 {v['pad_md']}px; color: #4F46E5; }}
"""


def apply_light_theme(app) -> None:
    app.setStyleSheet(_build_light_theme_qss())
    try:
        app.setFont(app.font())
        f = app.font()
        f.setFamily("Segoe UI")
        app.setFont(f)
    except Exception:
        pass


# Backward compatibility for existing imports.
apply_dark_theme = apply_light_theme
DARK_THEME_QSS = _build_light_theme_qss()
LIGHT_THEME_QSS = DARK_THEME_QSS
