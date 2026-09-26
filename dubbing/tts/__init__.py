"""TTS package."""
from .base import TTSProvider, AudioResult
from .provider import GeminiTTSProvider

__all__ = ["TTSProvider", "AudioResult", "GeminiTTSProvider"]
