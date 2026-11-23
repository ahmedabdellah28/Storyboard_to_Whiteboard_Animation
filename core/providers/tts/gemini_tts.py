"""Unified Gemini Text-to-Speech implementation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from google.genai import types

from core.api.client_manager import GeminiClientManager, get_client_manager
from core.artifacts.artifact_identity import compute_artifact_hash
from core.artifacts.artifact_store import ArtifactStore, get_artifact_store
from core.audio.wav_utils import apply_speed, pcm_to_wav, stitch_wav_files
from core.config.settings import DEFAULT_TTS_MODEL, DEFAULT_VOICE_NAME
from core.providers.tts.base import BaseTTSProvider
from core.telemetry.counters import get_telemetry_counters
from core.telemetry.timer import TaskTimer

PathLike = Union[str, Path]


class UnifiedGeminiTTS(BaseTTSProvider):
    """High-reliability TTS provider leveraging centralized Gemini client manager."""

    def __init__(
        self,
        model: str = DEFAULT_TTS_MODEL,
        default_voice: str = DEFAULT_VOICE_NAME,
        client_manager: Optional[GeminiClientManager] = None,
        artifact_store: Optional[ArtifactStore] = None,
    ) -> None:
        self.model = model
        self.default_voice = default_voice
        self.client_manager = client_manager or get_client_manager()
        self.artifact_store = artifact_store or get_artifact_store()
        self.counters = get_telemetry_counters()

    def build_config(self, voice_name: str, temperature: float = 2.0) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            temperature=temperature,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        )

    def synthesize(
        self,
        text: str,
        voice_name: Optional[str] = None,
        speed_factor: float = 1.0,
        options: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        voice = voice_name or self.default_voice
        opts = options or {}
        temperature = opts.get("temperature", 2.0)
        system_directive = opts.get("directive", "")

        full_prompt = f"{system_directive}\n\n{text}".strip() if system_directive else text
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=full_prompt)])]
        cfg = self.build_config(voice_name=voice, temperature=temperature)

        raw_pcm = self.client_manager.execute_stream_with_retry(
            model=self.model,
            contents=contents,
            config=cfg,
        )
        wav_bytes = pcm_to_wav(raw_pcm, sample_rate=24000)
        return wav_bytes

    def synthesize_to_file(
        self,
        text: str,
        output_path: PathLike,
        voice_name: Optional[str] = None,
        speed_factor: float = 1.0,
        options: Optional[Dict[str, Any]] = None,
    ) -> Path:
        out_file = Path(output_path).resolve()
        voice = voice_name or self.default_voice

        # Check artifact cache
        art_hash = compute_artifact_hash(
            component="tts",
            inputs={"text": text},
            config={"model": self.model, "voice": voice, "speed": speed_factor},
        )
        if self.artifact_store.is_artifact_valid(art_hash, out_file):
            self.counters.record_cache_hit("tts")
            return out_file

        self.counters.record_cache_miss("tts")
        wav_bytes = self.synthesize(text=text, voice_name=voice, options=options)

        if abs(speed_factor - 1.0) > 0.001:
            temp_path = out_file.with_name(f"{out_file.stem}_raw{out_file.suffix}")
            self.artifact_store.atomic_write_bytes(temp_path, wav_bytes)
            apply_speed(temp_path, out_file, factor=speed_factor)
            if temp_path.exists():
                temp_path.unlink()
        else:
            self.artifact_store.atomic_write_bytes(out_file, wav_bytes)

        self.artifact_store.register_artifact(art_hash, out_file, component="tts")
        return out_file

    def synthesize_chunked(
        self,
        chunks: List[str],
        output_wav_path: PathLike,
        voice_name: Optional[str] = None,
        speed_factor: float = 1.0,
        directive: str = "",
        inter_chunk_pause_ms: int = 80,
    ) -> Path:
        """Synthesize multiple text chunks with caching and stitch into master audio."""
        out_path = Path(output_wav_path).resolve()
        chunks_dir = out_path.parent / f"{out_path.stem}_chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        voice = voice_name or self.default_voice

        chunk_files: List[Path] = []
        for i, ctext in enumerate(chunks, 1):
            chunk_file = chunks_dir / f"chunk_{i:02d}.wav"
            self.synthesize_to_file(
                text=ctext,
                output_path=chunk_file,
                voice_name=voice,
                speed_factor=1.0,
                options={"directive": directive},
            )
            chunk_files.append(chunk_file)

        stitched_temp = out_path.with_name(f"{out_path.name}.temp_stitched.wav")
        stitch_wav_files(chunk_files, stitched_temp, silence_ms=inter_chunk_pause_ms)

        if abs(speed_factor - 1.0) > 0.001:
            apply_speed(stitched_temp, out_path, factor=speed_factor)
            if stitched_temp.exists():
                stitched_temp.unlink()
        else:
            if out_path.exists():
                out_path.unlink()
            stitched_temp.replace(out_path)

        return out_path
