"""Unified WAV audio utilities.

Consolidates duplicate PCM-to-WAV conversions and WAV stitching across
voice_studio, dubbing, section_tts, and production_engine.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import wave
from pathlib import Path
from typing import List, Sequence, Union

PathLike = Union[str, Path]


def pcm_to_wav(
    pcm_data: bytes,
    sample_rate: int = 24000,
    bits_per_sample: int = 16,
    num_channels: int = 1,
    mime_type: str = "",
) -> bytes:
    """Convert raw PCM audio bytes to a valid WAV container with a 44-byte RIFF header.

    If the input is already a valid WAV (starts with 'RIFF'), it is returned unmodified.
    Extracts sample rate from mime_type (e.g. 'audio/L16;rate=24000') if specified.
    """
    if not pcm_data:
        return b""

    # If already a WAV file, return as-is
    if len(pcm_data) >= 12 and pcm_data[:4] == b"RIFF" and pcm_data[8:12] == b"WAVE":
        return pcm_data

    # Handle legacy callers that pass mime_type as the second argument
    if isinstance(sample_rate, str):
        if not mime_type:
            mime_type = sample_rate
        sample_rate = 24000

    # Parse sample rate from mime_type if available
    if mime_type and "rate=" in mime_type:
        match = re.search(r"rate=(\d+)", mime_type)
        if match:
            sample_rate = int(match.group(1))

    data_size = len(pcm_data)
    chunk_size = 36 + data_size
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8

    header = bytearray()
    header.extend(b"RIFF")
    header.extend(chunk_size.to_bytes(4, "little"))
    header.extend(b"WAVE")
    header.extend(b"fmt ")
    header.extend((16).to_bytes(4, "little"))  # Subchunk1Size for PCM
    header.extend((1).to_bytes(2, "little"))   # AudioFormat 1 = PCM
    header.extend(num_channels.to_bytes(2, "little"))
    header.extend(sample_rate.to_bytes(4, "little"))
    header.extend(byte_rate.to_bytes(4, "little"))
    header.extend(block_align.to_bytes(2, "little"))
    header.extend(bits_per_sample.to_bytes(2, "little"))
    header.extend(b"data")
    header.extend(data_size.to_bytes(4, "little"))

    return bytes(header) + pcm_data


def get_wav_duration(file_path: PathLike) -> float:
    """Return the duration of a WAV file in seconds."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"WAV file not found: {file_path}")

    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        if rate == 0:
            return 0.0
        return frames / float(rate)


def stitch_wav_files(
    file_list: Sequence[PathLike],
    output_path: PathLike,
    silence_ms: int = 80,
) -> Path:
    """Stitch multiple WAV files into a single WAV file with micro-pause silence.

    Writes to a temporary file first, then atomically renames to ensure atomic completion.
    """
    valid_files = [Path(p) for p in file_list if Path(p).is_file() and Path(p).stat().st_size > 44]
    if not valid_files:
        raise ValueError("No valid WAV files provided to stitch.")

    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = out_file.with_name(f"{out_file.name}.tmp")

    # Read audio specs from first file
    with wave.open(str(valid_files[0]), "rb") as first_wf:
        channels = first_wf.getnchannels()
        sampwidth = first_wf.getsampwidth()
        framerate = first_wf.getframerate()

    silence_frames = int(framerate * (silence_ms / 1000.0))
    silence_bytes = b"\x00" * (silence_frames * channels * sampwidth)

    try:
        with wave.open(str(temp_file), "wb") as outfile:
            outfile.setnchannels(channels)
            outfile.setsampwidth(sampwidth)
            outfile.setframerate(framerate)

            for i, chunk_path in enumerate(valid_files):
                with wave.open(str(chunk_path), "rb") as infile:
                    n_frames = infile.getnframes()
                    if n_frames > 0:
                        outfile.writeframes(infile.readframes(n_frames))

                if i < len(valid_files) - 1 and silence_bytes:
                    outfile.writeframes(silence_bytes)

        # Atomic replacement
        if out_file.exists():
            out_file.unlink()
        temp_file.replace(out_file)
        return out_file
    except Exception as e:
        if temp_file.exists():
            temp_file.unlink()
        raise RuntimeError(f"Failed to stitch WAV files: {e}") from e


def generate_silence_wav(
    output_path: PathLike,
    duration_seconds: float,
    sample_rate: int = 24000,
    channels: int = 1,
    bits_per_sample: int = 16,
) -> Path:
    """Generate a valid WAV file containing silence."""
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    bytes_per_sample = bits_per_sample // 8
    total_frames = int(sample_rate * duration_seconds)
    silence_bytes = b"\x00" * (total_frames * channels * bytes_per_sample)

    wav_content = pcm_to_wav(
        silence_bytes,
        sample_rate=sample_rate,
        bits_per_sample=bits_per_sample,
        num_channels=channels,
    )

    with open(out_file, "wb") as f:
        f.write(wav_content)

    return out_file


def apply_speed(
    input_path: PathLike,
    output_path: PathLike,
    factor: float = 1.0,
) -> Path:
    """Adjust audio playback speed using ffmpeg if available.

    If factor == 1.0, copies the file.
    """
    in_file = Path(input_path).resolve()
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if abs(factor - 1.0) < 0.001:
        shutil.copy2(in_file, out_file)
        return out_file

    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", str(in_file),
            "-filter:a", f"atempo={factor}",
            str(out_file),
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg speed adjustment failed: {result.stderr}")
        return out_file
    else:
        # Fallback: copy without speed change if ffmpeg is missing
        print(f"⚠️ [apply_speed] ffmpeg not found, copying audio as-is without speed {factor}x")
        shutil.copy2(in_file, out_file)
        return out_file
