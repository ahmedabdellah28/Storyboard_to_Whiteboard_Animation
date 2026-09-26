"""
Audio Stretcher
===============
Time-stretch audio without pitch shifting using FFmpeg atempo filters.
Supports arbitrary stretch factors by chaining atempo filters (each 0.5 - 2.0).
"""
from __future__ import annotations

import os
import subprocess
import wave
from typing import Optional


class AudioStretcher:
    """Stretches or compresses audio duration without altering pitch."""

    @staticmethod
    def get_duration(audio_path: str) -> float:
        """Get WAV audio duration in seconds."""
        with wave.open(audio_path, "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())

    @classmethod
    def stretch(
        cls,
        input_path: str,
        output_path: str,
        speed_factor: float,
        sample_rate: int = 48000,
        channels: int = 1,
    ) -> float:
        """
        Change audio playback speed by *speed_factor* without altering pitch.
        
        Args:
            input_path: Source audio file path.
            output_path: Destination audio file path.
            speed_factor: Target speed factor (>1.0 speeds up / shortens, <1.0 slows down / elongates).
            sample_rate: Target audio sample rate.
            channels: Target audio channel count.
            
        Returns:
            The duration in seconds of the newly generated audio.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Build atempo filter chain (each filter limited to 0.5–2.0)
        filters = []
        remaining = speed_factor
        while remaining > 2.0:
            filters.append("atempo=2.0")
            remaining /= 2.0
        while remaining < 0.5:
            filters.append("atempo=0.5")
            remaining /= 0.5
        filters.append(f"atempo={remaining:.6f}")

        filter_str = ",".join(filters)

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-filter:a", filter_str,
            "-ar", str(sample_rate),
            "-ac", str(channels),
            "-c:a", "pcm_s16le",
            output_path,
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg stretch failed: {result.stderr}")

        return cls.get_duration(output_path)
