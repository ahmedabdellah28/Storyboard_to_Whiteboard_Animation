"""
ASR Base Interface
==================
Abstract interface for Automatic Speech Recognition providers.
"""
from abc import ABC, abstractmethod
from typing import Optional

from ..models.dubbing_models import TranscriptionResult


class ASRProvider(ABC):
    """Abstract base class for speech-to-text providers."""

    @abstractmethod
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe an audio file into text segments with timestamps.

        Args:
            audio_path: Path to a WAV audio file (16-bit PCM, mono recommended).
            language: Optional BCP-47 language hint (e.g. "ar", "en").
                      If None, the provider should auto-detect.

        Returns:
            TranscriptionResult with segments, detected language, and full text.
        """
        ...
