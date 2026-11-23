"""Unified Faster-Whisper ASR provider with caching and timestamp normalization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.artifacts.artifact_identity import compute_artifact_hash, hash_file
from core.artifacts.artifact_store import ArtifactStore, get_artifact_store
from core.telemetry.counters import get_telemetry_counters
from core.telemetry.timer import TaskTimer

PathLike = Union[str, Path]


class UnifiedWhisperASR:
    """Wrapper for Faster-Whisper with artifact caching and timestamp output."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "default",
        artifact_store: Optional[ArtifactStore] = None,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.artifact_store = artifact_store or get_artifact_store()
        self.counters = get_telemetry_counters()
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe(
        self,
        audio_path: PathLike,
        output_json_path: Optional[PathLike] = None,
        language: Optional[str] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        path = Path(audio_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Audio file not found for ASR: {path}")

        out_path = Path(output_json_path).resolve() if output_json_path else path.with_suffix(".whisper.json")

        # Check cache
        audio_h = hash_file(path)
        art_hash = compute_artifact_hash(
            component="whisper",
            inputs={"audio_hash": audio_h},
            config={"model_size": self.model_size, "language": language},
        )

        if not force and self.artifact_store.is_artifact_valid(art_hash, out_path):
            self.counters.record_cache_hit("whisper")
            with open(out_path, "r", encoding="utf-8") as f:
                return json.load(f)

        self.counters.record_cache_miss("whisper")
        with TaskTimer(f"whisper_{path.stem}", category="asr"):
            model = self._get_model()
            segments, info = model.transcribe(
                str(path),
                language=language,
                word_timestamps=True,
            )

            word_list: List[Dict[str, Any]] = []
            segment_list: List[Dict[str, Any]] = []

            for seg in segments:
                segment_list.append({
                    "id": seg.id,
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": seg.text.strip(),
                })
                if seg.words:
                    for w in seg.words:
                        word_list.append({
                            "word": w.word.strip(),
                            "start": round(w.start, 2),
                            "end": round(w.end, 2),
                            "probability": round(w.probability, 3),
                        })

            result_data = {
                "detected_language": info.language,
                "duration": round(info.duration, 2),
                "words": word_list,
                "segments": segment_list,
            }

            self.artifact_store.atomic_write_text(
                out_path, json.dumps(result_data, indent=2, ensure_ascii=False)
            )
            self.artifact_store.register_artifact(art_hash, out_path, component="whisper")
            return result_data
