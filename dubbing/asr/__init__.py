"""ASR package."""
from .base import ASRProvider
from .faster_whisper import FasterWhisperProvider

__all__ = ["ASRProvider", "FasterWhisperProvider"]
