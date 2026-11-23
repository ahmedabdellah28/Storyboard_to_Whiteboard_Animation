"""TTS providers package."""

from core.providers.tts.base import BaseTTSProvider
from core.providers.tts.gemini_tts import UnifiedGeminiTTS
from core.providers.tts.profiles import (
    AUDIO_PROFILES,
    DIRECTOR_NOTES,
    AudioProfile,
    DirectorNote,
)

__all__ = [
    "BaseTTSProvider",
    "UnifiedGeminiTTS",
    "AudioProfile",
    "DirectorNote",
    "AUDIO_PROFILES",
    "DIRECTOR_NOTES",
]
