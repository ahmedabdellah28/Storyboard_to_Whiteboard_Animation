"""
Duration Matcher
=================
Multi-level strategy to match dubbed audio duration to original segment timing.

Strategy priority:
  Level 1: Accept if already within tolerance (passthrough).
  Level 2: Safe time-stretch within configured bounds [min_speed, max_speed].
  Level 3: Controlled stretch clamped to bounds.
  Level 4: Overflow: If required speed exceeds max safe bounds, cap speed at max_speed
           and allow slight overflow rather than producing distorted or unintelligible speech.
"""
from __future__ import annotations

import os
import subprocess
import wave
from typing import Optional

from .audio_stretcher import AudioStretcher
from ..models.dubbing_models import DurationMatchingConfig, TimingInfo


class DurationMatcher:
    """
    Adjusts a TTS-generated audio segment to match the original duration
    using configurable speed bounds and stretch strategies.
    """

    def __init__(self, config: Optional[DurationMatchingConfig] = None):
        self.config = config or DurationMatchingConfig()
        self.stretcher = AudioStretcher()

    def get_duration(self, path: str) -> float:
        """Get WAV audio duration in seconds."""
        try:
            with wave.open(path, "rb") as wf:
                return wf.getnframes() / float(wf.getframerate())
        except Exception:
            return self.stretcher.get_duration(path)

    def match(
        self,
        audio_path: str,
        target_duration: float,
        output_path: str,
    ) -> TimingInfo:
        """
        Adjust *audio_path* so its duration approximates *target_duration*.

        Returns TimingInfo with the strategy applied.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        gen_dur = self.get_duration(audio_path)

        if not self.config.enabled:
            # Just copy as-is
            if os.path.normcase(os.path.abspath(audio_path)) != os.path.normcase(os.path.abspath(output_path)):
                self._copy_audio(audio_path, output_path)
            return TimingInfo(
                original_duration=target_duration,
                generated_duration=gen_dur,
                final_duration=gen_dur,
                adjustment_factor=1.0,
                strategy="disabled",
            )

        error = abs(gen_dur - target_duration)

        # Level 1: Already within tolerance
        if error <= self.config.max_duration_error:
            if os.path.normcase(os.path.abspath(audio_path)) != os.path.normcase(os.path.abspath(output_path)):
                self._copy_audio(audio_path, output_path)
            final_dur = self.get_duration(output_path)
            return TimingInfo(
                original_duration=target_duration,
                generated_duration=gen_dur,
                final_duration=final_dur,
                adjustment_factor=1.0,
                strategy="passthrough",
            )

        # Compute required speed factor
        # speed > 1 = faster (compress duration), speed < 1 = slower (stretch duration)
        if target_duration <= 0.05:
            # Guard against zero or near-zero target duration
            speed = 1.0
        else:
            speed = gen_dur / target_duration

        # Level 2 & 3: Within safe speed bounds -> apply atempo
        if self.config.min_speed <= speed <= self.config.max_speed:
            final_dur = AudioStretcher.stretch(
                input_path=audio_path,
                output_path=output_path,
                speed_factor=speed,
            )
            return TimingInfo(
                original_duration=target_duration,
                generated_duration=gen_dur,
                final_duration=final_dur,
                adjustment_factor=round(speed, 4),
                strategy="stretch" if speed < 1.0 else "compress",
            )

        # Level 4: Speed outside safe bounds.
        # Clamp speed to boundary to avoid robotic distortion, and allow controlled overflow.
        clamped_speed = max(
            self.config.min_speed, min(speed, self.config.max_speed)
        )
        final_dur = AudioStretcher.stretch(
            input_path=audio_path,
            output_path=output_path,
            speed_factor=clamped_speed,
        )

        return TimingInfo(
            original_duration=target_duration,
            generated_duration=gen_dur,
            final_duration=final_dur,
            adjustment_factor=round(clamped_speed, 4),
            strategy="overflow",
        )

    @staticmethod
    def _copy_audio(src: str, dst: str):
        """Normalise and copy audio to output path."""
        cmd = [
            "ffmpeg", "-y", "-i", src,
            "-ar", "48000", "-ac", "1",
            "-c:a", "pcm_s16le",
            dst,
        ]
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
