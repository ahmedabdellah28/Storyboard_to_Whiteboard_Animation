"""
AI Audio Dubbing Engine
=======================
Standalone, modular, provider-based audio dubbing pipeline.

Pipeline:
    Audio Input → Faster-Whisper ASR → Segmentation → Translation → TTS → Duration Matching → Final Dubbed Audio

This module is fully independent from the visual/video pipeline.
"""
from .pipeline.dubbing_pipeline import DubbingPipeline
from .models.dubbing_models import (
    DubbingResult,
    DubbingSegment,
    DubbingConfig,
    DurationMatchingConfig,
    SourceSegment,
    TranslatedSegment,
    TranscriptionResult,
)
from .asr.base import ASRProvider
from .translation.base import TranslationProvider
from .tts.base import TTSProvider
from .timing.duration_matcher import DurationMatcher
from .audio.processor import AudioProcessor
from .audio.mixer import Mixer
from .audio.segmenter import Segmenter

__all__ = [
    "DubbingPipeline",
    "DubbingResult",
    "DubbingSegment",
    "DubbingConfig",
    "DurationMatchingConfig",
    "SourceSegment",
    "TranslatedSegment",
    "TranscriptionResult",
    "ASRProvider",
    "TranslationProvider",
    "TTSProvider",
    "DurationMatcher",
    "AudioProcessor",
    "Mixer",
    "Segmenter",
]

