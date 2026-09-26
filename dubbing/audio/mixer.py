"""
Audio Mixer
===========
Mixes TTS-generated segments into a unified, continuous audio track.
Critically preserves original silence pauses between segments and accurate start timestamps.
"""
from __future__ import annotations

import math
import os
import subprocess
import wave
from typing import List, Dict, Any, Optional

import numpy as np
import soundfile as sf

from ..models.dubbing_models import DubbingSegment, DubbingConfig


class Mixer:
    """Combines dubbed segments into a final audio file while preserving exact timing and pauses."""

    def __init__(self, config: Optional[DubbingConfig] = None):
        self.config = config or DubbingConfig()
        self.sample_rate = self.config.output_sample_rate
        self.channels = self.config.output_channels

    def mix_segments(
        self,
        segments: List[DubbingSegment],
        output_path: str,
        total_duration: Optional[float] = None,
    ) -> str:
        """
        Combine all segment audio files into a single continuous audio file.
        Preserves original pauses, silences, and start times.

        Args:
            segments: List of DubbingSegment objects with valid final_audio_path.
            output_path: Destination path for the final mixed WAV file.
            total_duration: Optional total duration for padding silence at the end.

        Returns:
            Absolute path to the final mixed audio file.
        """
        if not segments:
            raise ValueError("No segments provided to mix.")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Calculate required total length in seconds
        max_end_time = 0.0
        for seg in segments:
            seg_start = seg.source.start
            seg_dur = seg.final_duration if seg.final_duration > 0 else seg.source.duration
            seg_end = max(seg.source.end, seg_start + seg_dur)
            if seg_end > max_end_time:
                max_end_time = seg_end

        if total_duration and total_duration > max_end_time:
            target_duration = total_duration
        else:
            target_duration = max_end_time

        total_samples = int(math.ceil(target_duration * self.sample_rate))
        if total_samples <= 0:
            total_samples = self.sample_rate  # At least 1 second

        # Create blank silent canvas (channels x samples or samples x channels)
        if self.channels > 1:
            master_buffer = np.zeros((total_samples, self.channels), dtype=np.float32)
        else:
            master_buffer = np.zeros(total_samples, dtype=np.float32)

        for seg in segments:
            audio_file = seg.final_audio_path or seg.tts_audio_path
            if not audio_file or not os.path.isfile(audio_file):
                # Missing segment: keep as silence
                continue

            try:
                data, sr = sf.read(audio_file, dtype="float32")
            except Exception:
                # If soundfile fails, try reading via ffmpeg into wav
                tmp_conv = audio_file + ".norm.wav"
                self._convert_to_target_pcm(audio_file, tmp_conv)
                data, sr = sf.read(tmp_conv, dtype="float32")
                try:
                    os.remove(tmp_conv)
                except OSError:
                    pass

            # Resample if sample rate doesn't match
            if sr != self.sample_rate:
                # Convert using ffmpeg temporary file
                tmp_resampled = audio_file + f".{self.sample_rate}.wav"
                self._convert_to_target_pcm(audio_file, tmp_resampled)
                data, sr = sf.read(tmp_resampled, dtype="float32")
                try:
                    os.remove(tmp_resampled)
                except OSError:
                    pass

            # Ensure channel matching
            if self.channels == 2:
                if data.ndim == 1:
                    # Convert mono to stereo
                    data = np.column_stack((data, data))
                elif data.ndim == 2 and data.shape[1] > 2:
                    data = data[:, :2]
            elif self.channels == 1:
                if data.ndim == 2:
                    # Downmix stereo to mono
                    data = np.mean(data, axis=1)

            # Compute sample positions
            start_sample = int(round(seg.source.start * self.sample_rate))
            if start_sample < 0:
                start_sample = 0

            seg_samples = len(data)
            end_sample = start_sample + seg_samples

            # Extend master buffer if segment slightly overflows
            if end_sample > len(master_buffer):
                overflow = end_sample - len(master_buffer)
                if self.channels > 1:
                    master_buffer = np.pad(master_buffer, ((0, overflow), (0, 0)), mode="constant")
                else:
                    master_buffer = np.pad(master_buffer, (0, overflow), mode="constant")

            # Place segment audio (sum with slight crossfade / clip protection)
            master_buffer[start_sample:end_sample] += data

        # Apply soft clipping to prevent distortion from overlapping peaks
        np.clip(master_buffer, -1.0, 1.0, out=master_buffer)

        # Write final WAV file
        sf.write(output_path, master_buffer, self.sample_rate, subtype="PCM_16")

        return os.path.abspath(output_path)

    def _convert_to_target_pcm(self, src: str, dst: str) -> None:
        """Helper to convert audio to the mixer target format via FFmpeg."""
        cmd = [
            "ffmpeg", "-y",
            "-i", src,
            "-ar", str(self.sample_rate),
            "-ac", str(self.channels),
            "-c:a", "pcm_s16le",
            dst,
        ]
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

    def validate_output(self, audio_path: str) -> Dict[str, Any]:
        """Validate properties of the mixed audio file."""
        info = sf.info(audio_path)
        return {
            "path": os.path.abspath(audio_path),
            "duration": round(info.duration, 4),
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "format": info.format,
            "subtype": info.subtype,
        }