"""
Faster-Whisper ASR Provider
============================
Concrete implementation using faster-whisper for speech-to-text
with automatic language detection and precise timestamp segmentation.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

from .base import ASRProvider
from ..models.dubbing_models import TranscriptionResult, SourceSegment


class FasterWhisperProvider(ASRProvider):
    """
    Speech-to-text using faster-whisper (CTranslate2 backend).

    Supports CPU and CUDA, configurable model sizes.
    """

    def __init__(
        self,
        model_size: str = "small",
        compute_type: str = "int8",
        device: str = "auto",
    ):
        """
        Args:
            model_size: One of "tiny", "base", "small", "medium", "large-v3".
            compute_type: Quantization type — "int8", "float16", "float32".
            device: "auto" (detects GPU availability), "cpu", or "cuda".
        """
        self.model_size = model_size
        self.compute_type = compute_type
        self.device = self._resolve_device(device)
        self._model = None  # lazy loaded

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device in ("cpu", "cuda"):
            return device
        return "cpu"

    def _get_model(self):
        """Lazy-load the whisper model to avoid heavy startup cost."""
        if self._model is None:
            from faster_whisper import WhisperModel

            print(
                f"  [ASR] Loading faster-whisper model "
                f"'{self.model_size}' on {self.device} ({self.compute_type})…"
            )
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    # ── public API ────────────────────────────────────────────────────────────

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe an audio file and return structured segments.

        Auto-detects the source language if *language* is not given.
        """
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        model = self._get_model()

        # Run transcription
        segments_gen, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            word_timestamps=False,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=300,
                speech_pad_ms=200,
            ),
        )

        detected_lang = info.language
        lang_prob = info.language_probability

        print(
            f"  [ASR] Detected language: {detected_lang} "
            f"(confidence: {lang_prob:.2%})"
        )

        # Materialise generator into list of SourceSegments
        source_segments = []
        full_texts = []
        for idx, seg in enumerate(segments_gen):
            text = seg.text.strip()
            if not text:
                continue
            source_segments.append(
                SourceSegment(
                    id=idx,
                    start=round(seg.start, 4),
                    end=round(seg.end, 4),
                    text=text,
                )
            )
            full_texts.append(text)

        if not source_segments:
            raise RuntimeError(
                "Transcription produced zero non-empty segments. "
                "Check the audio file quality and content."
            )

        # Re-number IDs contiguously (VAD may skip)
        for i, seg in enumerate(source_segments):
            seg.id = i

        print(f"  [ASR] Transcribed {len(source_segments)} segments.")

        return TranscriptionResult(
            segments=source_segments,
            detected_language=detected_lang,
            language_probability=lang_prob,
            full_text=" ".join(full_texts),
        )
