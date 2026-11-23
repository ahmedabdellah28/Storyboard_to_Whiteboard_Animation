"""Voice profiles and director notes for unified TTS narration."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from voice_studio.profiles import (
        AUDIO_PROFILES,
        DIRECTOR_NOTES,
        AudioProfile,
        DirectorNote,
    )
except ImportError:
    from dataclasses import dataclass

    @dataclass
    class AudioProfile:
        name: str
        description: str

    @dataclass
    class DirectorNote:
        style: str
        scene: str
        sample_context: str

        def compile_instruction(self, profile: AudioProfile) -> str:
            return f"Role: {profile.name}. Style: {self.style}\n{self.sample_context}"

    AUDIO_PROFILES = {
        "SAUDI_YOUTH_CREATOR": AudioProfile(
            name="Young Saudi YouTube Creator",
            description="Young Saudi male YouTube creator, around 25-30 years old.",
        )
    }
    DIRECTOR_NOTES = {}

__all__ = [
    "AudioProfile",
    "DirectorNote",
    "AUDIO_PROFILES",
    "DIRECTOR_NOTES",
]
