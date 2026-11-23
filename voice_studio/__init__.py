"""
Voice Studio Package
Professional AI Text-to-Speech & Voiceover Subsystem
"""
from .engine import VoiceStudioEngine, split_transcript_into_sections
from .profiles import AudioProfile, DirectorNote, AUDIO_PROFILES, DIRECTOR_NOTES
from .vyond_story import (
    BASE_DIRECTOR_PROMPT,
    DEFAULT_FEMALE_VOICE,
    DEFAULT_VYOND_MODEL,
    VyondStoryEngine,
    clean_pcm_audio,
    parse_story_script,
    split_into_safe_chunks,
)

__all__ = [
    "VoiceStudioEngine",
    "split_transcript_into_sections",
    "AudioProfile",
    "DirectorNote",
    "AUDIO_PROFILES",
    "DIRECTOR_NOTES",
    "VyondStoryEngine",
    "BASE_DIRECTOR_PROMPT",
    "DEFAULT_FEMALE_VOICE",
    "DEFAULT_VYOND_MODEL",
    "clean_pcm_audio",
    "parse_story_script",
    "split_into_safe_chunks",
]
