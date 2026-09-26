"""
Visual Beat Layer Package (ASATE)
Provides speech-visual rhythm mapping, semantic emphasis, controlled overlap,
and constrained timing solving for whiteboard animation.
"""
from .speech_beat import SpeechBeat
from .visual_beat import (
    VisualBeat,
    TransitionPolicy,
    OverlapPolicy,
    ElementTier,
    EmphasisPoint,
    TimingDecision
)
from .beat_solver import BeatTimingSolver
from .beat_mapper import BeatMapper
from .beat_debugger import BeatTimelineVisualizer

__all__ = [
    "SpeechBeat",
    "VisualBeat",
    "TransitionPolicy",
    "OverlapPolicy",
    "ElementTier",
    "EmphasisPoint",
    "TimingDecision",
    "BeatTimingSolver",
    "BeatMapper",
    "BeatTimelineVisualizer"
]
