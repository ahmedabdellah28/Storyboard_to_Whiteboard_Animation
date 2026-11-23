"""Whiteboard Studio Modern Workstation Desktop Application Package."""

from studio_ui.qt import QT_BINDING
from studio_ui.theme import DARK_THEME_QSS, apply_dark_theme

__all__ = [
    "QT_BINDING",
    "DARK_THEME_QSS",
    "apply_dark_theme",
    "create_application",
    "StudioMainWindow",
    "ProjectBrowser",
    "ProcessingMonitorView",
    "StudioEditorView",
    "NewProjectDialog",
    "NewSectionDialog",
    "ExtractionReviewDialog",
    "VoiceReviewDialog",
    "SemanticReviewDialog",
]


def __getattr__(name: str):
    """Lazy imports to break circular dependency with core.orchestration."""
    if name == "create_application":
        from studio_ui.app import create_application
        return create_application
    if name == "StudioMainWindow":
        from studio_ui.main_window import StudioMainWindow
        return StudioMainWindow
    if name == "ProjectBrowser":
        from studio_ui.views.project_browser import ProjectBrowser
        return ProjectBrowser
    if name == "ProcessingMonitorView":
        from studio_ui.views.processing_monitor import ProcessingMonitorView
        return ProcessingMonitorView
    if name == "StudioEditorView":
        from studio_ui.views.studio_editor import StudioEditorView
        return StudioEditorView
    if name == "NewProjectDialog":
        from studio_ui.dialogs.new_project_dialog import NewProjectDialog
        return NewProjectDialog
    if name == "NewSectionDialog":
        from studio_ui.dialogs.new_section_dialog import NewSectionDialog
        return NewSectionDialog
    if name == "ExtractionReviewDialog":
        from studio_ui.dialogs.extraction_review_dialog import ExtractionReviewDialog
        return ExtractionReviewDialog
    if name == "VoiceReviewDialog":
        from studio_ui.dialogs.voice_review_dialog import VoiceReviewDialog
        return VoiceReviewDialog
    if name == "SemanticReviewDialog":
        from studio_ui.dialogs.semantic_review_dialog import SemanticReviewDialog
        return SemanticReviewDialog
    raise AttributeError(f"module 'studio_ui' has no attribute {name!r}")
