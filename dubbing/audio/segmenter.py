"""
Audio Segmenter
===============
Sentence-level segmentation, timestamp tracking, and subtitle (SRT) generation.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import List, Optional, Dict, Any

from ..models.dubbing_models import SourceSegment, TranscriptionResult


class Segmenter:
    """Handles audio segmentation, timestamping, and SRT subtitle formatting."""

    def __init__(self, min_silence_duration: float = 0.3):
        self.min_silence_duration = min_silence_duration

    def save_transcription_artifacts(
        self,
        transcription_result: TranscriptionResult,
        transcription_dir: str,
    ) -> Dict[str, str]:
        """
        Save both transcript.json and transcript.srt into the specified directory.

        Returns dictionary with paths to transcript.json and transcript.srt.
        """
        os.makedirs(transcription_dir, exist_ok=True)

        json_path = os.path.join(transcription_dir, "transcript.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(transcription_result.to_dict(), f, ensure_ascii=False, indent=2)

        srt_path = os.path.join(transcription_dir, "transcript.srt")
        self.save_as_srt(transcription_result.segments, srt_path)

        return {"json": json_path, "srt": srt_path}

    def save_as_srt(self, segments: List[SourceSegment], output_path: str) -> str:
        """Save segments in standard SRT (SubRip) format."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments):
                start_str = self.format_srt_timestamp(segment.start)
                end_str = self.format_srt_timestamp(segment.end)
                f.write(f"{i + 1}\n")
                f.write(f"{start_str} --> {end_str}\n")
                f.write(f"{segment.text.strip()}\n\n")
        return output_path

    @staticmethod
    def format_srt_timestamp(seconds: float) -> str:
        """Convert float seconds to SRT time format: HH:MM:SS,mmm."""
        if seconds < 0:
            seconds = 0.0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        if millis >= 1000:
            millis = 999
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def extract_audio_segment(
        self,
        source_audio_path: str,
        start_time: float,
        end_time: float,
        output_path: str,
    ) -> str:
        """Extract a slice from the source audio file using FFmpeg."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        duration = max(0.01, end_time - start_time)
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", source_audio_path,
            "-t", str(duration),
            "-ar", "48000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            output_path,
        ]
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return output_path