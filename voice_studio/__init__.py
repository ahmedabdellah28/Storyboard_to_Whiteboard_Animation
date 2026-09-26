"""
Voice Studio Package
Professional AI Text-to-Speech & Voiceover Subsystem
"""
from .engine import VoiceStudioEngine
from .profiles import AudioProfile, DirectorNote, AUDIO_PROFILES, DIRECTOR_NOTES

__all__ = [
    "VoiceStudioEngine",
    "AudioProfile",
    "DirectorNote",
    "AUDIO_PROFILES",
    "DIRECTOR_NOTES"
]
