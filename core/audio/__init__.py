"""Audio utilities package."""

from core.audio.wav_utils import (
    apply_speed,
    generate_silence_wav,
    get_wav_duration,
    pcm_to_wav,
    stitch_wav_files,
)

__all__ = [
    "pcm_to_wav",
    "get_wav_duration",
    "stitch_wav_files",
    "generate_silence_wav",
    "apply_speed",
]
