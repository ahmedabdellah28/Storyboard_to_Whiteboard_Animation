"""
Audio Processor
===============
Audio file operations, format conversions, probe info, and preprocessing
for the AI Audio Dubbing Engine.
"""
from __future__ import annotations

import json
import os
import subprocess
import wave
from typing import Dict, Any, Optional

import soundfile as sf


class AudioProcessor:
    """Handles audio conversions, metadata probing, and ASR preprocessing."""

    SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".wma"}

    def __init__(self, sample_rate: int = 48000, channels: int = 2):
        self.sample_rate = sample_rate
        self.channels = channels

    def get_info(self, audio_path: str) -> Dict[str, Any]:
        """
        Extract duration, sample_rate, channels, and format from any supported audio file.
        Uses ffprobe with fallback to soundfile or wave.
        """
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Try ffprobe first for universal format support
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                audio_path,
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            probe = json.loads(res.stdout)

            # Find first audio stream
            audio_stream = None
            for stream in probe.get("streams", []):
                if stream.get("codec_type") == "audio":
                    audio_stream = stream
                    break

            fmt_info = probe.get("format", {})
            duration = float(fmt_info.get("duration", 0.0))
            if duration <= 0.0 and audio_stream and "duration" in audio_stream:
                duration = float(audio_stream["duration"])

            sample_rate = int(audio_stream.get("sample_rate", 48000)) if audio_stream else 48000
            channels = int(audio_stream.get("channels", 2)) if audio_stream else 2
            format_name = fmt_info.get("format_name", os.path.splitext(audio_path)[1].lstrip("."))

            return {
                "path": os.path.abspath(audio_path),
                "duration": round(duration, 4),
                "sample_rate": sample_rate,
                "channels": channels,
                "format": format_name,
            }
        except Exception:
            pass

        # Fallback to soundfile
        try:
            info = sf.info(audio_path)
            return {
                "path": os.path.abspath(audio_path),
                "duration": round(info.duration, 4),
                "sample_rate": info.samplerate,
                "channels": info.channels,
                "format": info.format.lower(),
            }
        except Exception:
            pass

        # Fallback to wave
        try:
            with wave.open(audio_path, "rb") as wf:
                dur = wf.getnframes() / float(wf.getframerate())
                return {
                    "path": os.path.abspath(audio_path),
                    "duration": round(dur, 4),
                    "sample_rate": wf.getframerate(),
                    "channels": wf.getnchannels(),
                    "format": "wav",
                }
        except Exception as e:
            raise RuntimeError(f"Could not probe audio file {audio_path}: {e}")

    def get_duration(self, audio_path: str) -> float:
        """Get duration in seconds of any audio file."""
        return self.get_info(audio_path)["duration"]

    def convert_to_wav(
        self,
        input_path: str,
        output_path: str,
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
    ) -> str:
        """
        Convert any audio file (.mp3, .m4a, .ogg, etc.) to 16-bit PCM WAV.
        """
        sr = sample_rate or self.sample_rate
        ch = channels or self.channels
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-ar", str(sr),
            "-ac", str(ch),
            "-c:a", "pcm_s16le",
            output_path,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg conversion failed: {res.stderr}")

        return output_path

    def prepare_for_asr(self, input_path: str, output_path: str) -> str:
        """
        Preprocess audio file specifically for Faster-Whisper:
        Converts to 16kHz mono 16-bit PCM WAV with volume normalization.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-ar", "16000",
            "-ac", "1",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:a", "pcm_s16le",
            output_path,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            # Fallback without loudnorm filter if loudnorm fails
            cmd_fallback = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                output_path,
            ]
            res2 = subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res2.returncode != 0:
                raise RuntimeError(f"FFmpeg ASR preprocessing failed: {res2.stderr}")

        return output_path