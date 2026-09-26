"""
TTS Base Interface
===================
Abstract interface for Text-to-Speech providers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class AudioResult:
    """Result from a TTS synthesis call."""
    audio_path: str
    duration: float  # seconds
    sample_rate: int


class TTSProvider(ABC):
    """Abstract base class for text-to-speech providers."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        language: str,
        voice: str,
        output_path: str,
    ) -> AudioResult:
        """
        Synthesize speech from text.

        Args:
            text: The text to speak.
            language: BCP-47 language code (e.g. "en").
            voice: Voice identifier (provider-specific).
            output_path: Path where the WAV file should be written.

        Returns:
            AudioResult with the path, duration, and sample rate.
        """
        ...
