"""Unified Gemini translation provider with batch chunking and caching."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.api.client_manager import GeminiClientManager, get_client_manager
from core.artifacts.artifact_identity import compute_artifact_hash
from core.artifacts.artifact_store import ArtifactStore, get_artifact_store
from core.config.settings import DEFAULT_CHAT_MODEL
from core.telemetry.counters import get_telemetry_counters
from core.telemetry.timer import TaskTimer

PathLike = Union[str, Path]


class UnifiedGeminiTranslator:
    """High-reliability translation provider using centralized Gemini client manager."""

    def __init__(
        self,
        model: str = DEFAULT_CHAT_MODEL,
        client_manager: Optional[GeminiClientManager] = None,
        artifact_store: Optional[ArtifactStore] = None,
    ) -> None:
        self.model = model
        self.client_manager = client_manager or get_client_manager()
        self.artifact_store = artifact_store or get_artifact_store()
        self.counters = get_telemetry_counters()

    def translate_text(
        self,
        text: str,
        target_language: str = "en",
        source_language: Optional[str] = "ar",
        context: str = "",
    ) -> str:
        art_hash = compute_artifact_hash(
            component="translation",
            inputs={"text": text},
            config={"target_lang": target_language, "source_lang": source_language, "model": self.model},
        )

        prompt = (
            f"You are a professional audiovisual translator.\n"
            f"Translate the following spoken narration from {source_language or 'auto'} to {target_language}.\n"
            f"Context: {context or 'Documentary narration'}\n"
            f"Rules:\n"
            f"1. Produce natural, conversational language suitable for voiceover.\n"
            f"2. Return ONLY the translated text, no comments or markdown quotes.\n\n"
            f"{text}"
        )

        with TaskTimer("gemini_translate", category="translation"):
            response = self.client_manager.execute_content_with_retry(
                model=self.model,
                contents=prompt,
            )
            return response.text.strip() if hasattr(response, "text") else str(response).strip()

    def translate_segments(
        self,
        segments: List[Dict[str, Any]],
        target_language: str = "en",
        output_file: Optional[PathLike] = None,
        force: bool = False,
    ) -> List[Dict[str, Any]]:
        """Translate a list of transcript segments while preserving timestamps and IDs."""
        if output_file:
            out_path = Path(output_file).resolve()
            art_hash = compute_artifact_hash(
                component="translation_segments",
                inputs={"segment_count": len(segments), "first_seg": segments[0] if segments else {}},
                config={"target_lang": target_language, "model": self.model},
            )
            if not force and self.artifact_store.is_artifact_valid(art_hash, out_path):
                self.counters.record_cache_hit("translation")
                with open(out_path, "r", encoding="utf-8") as f:
                    return json.load(f)

        self.counters.record_cache_miss("translation")
        translated_segments: List[Dict[str, Any]] = []

        for seg in segments:
            orig_text = seg.get("text", "")
            trans_text = self.translate_text(orig_text, target_language=target_language)
            translated_segments.append({
                "id": seg.get("id"),
                "start": seg.get("start"),
                "end": seg.get("end"),
                "source_text": orig_text,
                "translated_text": trans_text,
            })

        if output_file:
            out_path = Path(output_file).resolve()
            self.artifact_store.atomic_write_text(
                out_path, json.dumps(translated_segments, indent=2, ensure_ascii=False)
            )
            self.artifact_store.register_artifact(art_hash, out_path, component="translation_segments")

        return translated_segments
