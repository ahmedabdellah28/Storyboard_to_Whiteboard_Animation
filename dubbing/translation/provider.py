"""
Gemini Translation Provider
===========================
Uses Google Gemini for context-aware, natural dubbing translation.
Features:
  - Multi-API key rotation across GEMINI_API_KEY, GEMINI_API_KEY2, GEMINI_API_KEY3
  - Automatic fallback between gemini-3.8-flash and gemini-1.5-flash on 503/429
  - Small-batch translation (5 segments/batch) to stay within quota
  - Per-batch checkpoint caching: resume from last saved batch on restart
  - Per-request timeout to prevent silent hangs
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import List, Optional

from .base import TranslationProvider
from ..models.dubbing_models import SourceSegment, TranslatedSegment

_LANG_NAMES = {
    "ar": "Arabic",
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "tr": "Turkish",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "pt": "Portuguese",
    "ru": "Russian",
    "it": "Italian",
    "hi": "Hindi",
}


def _lang_name(code: str) -> str:
    return _LANG_NAMES.get(code, code)


class GeminiTranslationProvider(TranslationProvider):
    """Translates text using Google Gemini with key rotation, backoff, and model fallback."""

    FALLBACK_MODELS = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-2.5-flash",
        "gemini-flash-latest",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3.8-flash",
        batch_size: int = 3,
        request_timeout: float = 60.0,
        inter_batch_sleep: float = 6.0,
        checkpoint_file: Optional[str] = None,
    ):
        self.model = model
        self.batch_size = batch_size
        self.request_timeout = request_timeout
        self.inter_batch_sleep = inter_batch_sleep
        self.checkpoint_file = checkpoint_file
        self._current_model_idx = 0
        from core.config.env_loader import get_gemini_api_keys

        self._api_keys: list[str] = []
        if api_key:
            self._api_keys.append(api_key.strip())

        for k in get_gemini_api_keys():
            if k not in self._api_keys:
                self._api_keys.append(k)

        self._key_idx = 0
        self._client = None

        if self._api_keys:
            print(f"  [Translation] Loaded {len(self._api_keys)} API key(s)")
        else:
            print("  [Translation] WARNING: No API keys found!", file=sys.stderr)

    @property
    def _current_key(self) -> str:
        if not self._api_keys:
            raise RuntimeError("No Gemini API keys configured.")
        return self._api_keys[self._key_idx % len(self._api_keys)]

    def _rotate_key(self) -> str:
        prev_idx = self._key_idx
        self._key_idx = (self._key_idx + 1) % len(self._api_keys)
        self._client = None
        if self._key_idx == 0 and len(self._api_keys) > 1:
            # Wrapped around — all keys exhausted, try next model too
            self._current_model_idx = (self._current_model_idx + 1) % len(self.FALLBACK_MODELS)
            self.model = self.FALLBACK_MODELS[self._current_model_idx]
            print(f"  [Translation] All keys cycled — switched model to {self.model}, restarting with key 1")
        else:
            print(f"  [Translation] Rotated to key {self._key_idx + 1}/{len(self._api_keys)} (model: {self.model})")
        return self._current_key

    def _switch_model(self):
        self._current_model_idx = (self._current_model_idx + 1) % len(self.FALLBACK_MODELS)
        self.model = self.FALLBACK_MODELS[self._current_model_idx]
        self._client = None
        print(f"  [Translation] Switched model to {self.model}")

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self._current_key)
        return self._client

    def _load_checkpoint(self) -> dict:
        """Load cached translations keyed by segment ID string."""
        if self.checkpoint_file and os.path.isfile(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                print(f"  [Translation] Checkpoint loaded: {len(data)} segments already translated")
                return data
            except Exception as e:
                print(f"  [Translation] Checkpoint parse warning: {e}")
        return {}

    def _save_checkpoint(self, cache: dict) -> None:
        """Persist incremental translation progress."""
        if self.checkpoint_file:
            try:
                parent = os.path.dirname(os.path.abspath(self.checkpoint_file))
                os.makedirs(parent, exist_ok=True)
                with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(cache, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"  [Translation] Checkpoint save warning: {e}")

    def _call_api(self, prompt: str) -> str:
        """Call Gemini API with a wall-clock timeout to prevent silent hangs."""
        def _do_call():
            client = self._get_client()
            resp = client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            return resp.text.strip()

        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_do_call)
            try:
                return fut.result(timeout=self.request_timeout)
            except FuturesTimeoutError:
                raise TimeoutError(
                    f"Gemini API call timed out after {self.request_timeout}s"
                )

    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """Translate a single line with key rotation on rate limits."""
        prompt = (
            f"Translate the following {_lang_name(source_language)} text "
            f"into natural, spoken {_lang_name(target_language)} for dubbing.\n"
            f"Return ONLY the translated text, nothing else.\n\n"
            f"Text:\n{text}"
        )
        max_retries = max(6, len(self._api_keys) * 2)
        for attempt in range(max_retries):
            try:
                return self._call_api(prompt)
            except TimeoutError:
                print(f"  [Translation] Single request timed out (attempt {attempt + 1})")
                self._rotate_key()
                time.sleep(3.0)
                continue
            except Exception as e:
                err_str = str(e).lower()
                if "quota" in err_str or "429" in err_str or "rate" in err_str:
                    self._rotate_key()
                    time.sleep(2.0)
                    continue
                if ("503" in err_str or "unavailable" in err_str
                            or "404" in err_str or "not_found" in err_str or "no longer" in err_str):
                    self._switch_model()
                    time.sleep(3.0)
                    continue
                if attempt < max_retries - 1:
                    time.sleep(1.5)
                    continue
                raise
        return text

    def translate_segments(
        self,
        segments: List[SourceSegment],
        source_language: str,
        target_language: str,
    ) -> List[TranslatedSegment]:
        """
        Translate all segments in small batches with checkpoint-based resumption.
        Progress is saved after every batch.
        """
        if not segments:
            return []

        cache = self._load_checkpoint()
        pending = [s for s in segments if str(s.id) not in cache]
        already_done = len(segments) - len(pending)
        total_batches = (len(pending) + self.batch_size - 1) // self.batch_size

        if already_done:
            print(
                f"  [Translation] Resuming: {already_done}/{len(segments)} cached, "
                f"{len(pending)} remaining in {total_batches} batches"
            )
        else:
            print(
                f"  [Translation] Translating {len(segments)} segments in "
                f"{total_batches} batches of {self.batch_size}"
            )

        batch_num = 0
        for batch_start in range(0, len(pending), self.batch_size):
            batch_num += 1
            batch = pending[batch_start: batch_start + self.batch_size]
            pct = int(100 * batch_start / max(1, len(pending)))
            print(
                f"  [Translation] Batch {batch_num}/{total_batches} "
                f"({len(batch)} segs | {pct}% done) ...",
                flush=True,
            )

            translated_batch = self._translate_batch(batch, source_language, target_language)

            for seg, trans in zip(batch, translated_batch):
                cache[str(seg.id)] = trans.text

            self._save_checkpoint(cache)
            print(f"  [Translation] Batch {batch_num} done - checkpoint saved", flush=True)

            if batch_start + self.batch_size < len(pending):
                time.sleep(self.inter_batch_sleep)

        id_to_source = {s.id: s for s in segments}
        results = []
        for seg in segments:
            text = cache.get(str(seg.id), seg.text)
            results.append(
                TranslatedSegment(
                    id=seg.id,
                    source=id_to_source[seg.id],
                    language=target_language,
                    text=text.strip(),
                )
            )

        print(f"  [Translation] All {len(results)} segments translated", flush=True)
        return results

    def _translate_batch(
        self,
        segments: List[SourceSegment],
        source_language: str,
        target_language: str,
    ) -> List[TranslatedSegment]:
        """Translate a batch using JSON mapping with retries, key rotation, and timeout."""
        lines = [f'{seg.id}: "{seg.text}"' for seg in segments]
        numbered_text = "\n".join(lines)

        prompt = (
            f"You are a professional dubbing translator.\n"
            f"Translate each numbered line from {_lang_name(source_language)} "
            f"to natural, spoken, conversational {_lang_name(target_language)}.\n"
            f"The translations are for voice dubbing: keep them natural, concise, and spoken.\n\n"
            f"Return ONLY a JSON object mapping each ID to its translated text.\n"
            f'Example: {{"0": "translated text", "1": "another"}}\n\n'
            f"Segments:\n{numbered_text}"
        )

        max_retries = max(10, len(self._api_keys) * 3)
        for attempt in range(max_retries):
            try:
                raw = self._call_api(prompt)
                if raw.startswith("```"):
                    raw = re.sub(r"^```[a-z]*\n?", "", raw)
                    raw = re.sub(r"\n?```$", "", raw)
                    raw = raw.strip()

                mapping = json.loads(raw)
                results = []
                for seg in segments:
                    key = str(seg.id)
                    translated_text = mapping.get(key) or mapping.get(seg.id) or ""
                    if not translated_text:
                        print(f"  [Translation] Segment {seg.id} missing, translating individually...")
                        translated_text = self.translate(seg.text, source_language, target_language)
                    results.append(
                        TranslatedSegment(
                            id=seg.id,
                            source=seg,
                            language=target_language,
                            text=translated_text.strip(),
                        )
                    )
                return results

            except TimeoutError:
                wait = min(30.0, 5.0 * (attempt + 1))
                print(f"  [Translation] Request timed out (attempt {attempt + 1}), waiting {wait:.0f}s...")
                self._rotate_key()
                time.sleep(wait)
                continue

            except json.JSONDecodeError as e:
                print(f"  [Translation] JSON parse error (attempt {attempt + 1}): {e}")
                return self._fallback_per_segment(segments, source_language, target_language)

            except Exception as e:
                err_str = str(e).lower()
                if "quota" in err_str or "429" in err_str or "rate" in err_str:
                    self._rotate_key()
                    wait = min(60.0, 5.0 * (attempt + 1))
                    print(f"  [Translation] Rate limited (attempt {attempt + 1}), waiting {wait:.0f}s...")
                    time.sleep(wait)
                    continue
                if ("503" in err_str or "unavailable" in err_str or "high demand" in err_str
                            or "404" in err_str or "not_found" in err_str or "no longer available" in err_str):
                    print(f"  [Translation] Model {self.model} unavailable (attempt {attempt + 1}), switching...")
                    self._switch_model()
                    time.sleep(3.0)
                    continue
                if attempt < max_retries - 1:
                    print(f"  [Translation] Batch error (attempt {attempt + 1}): {e}")
                    time.sleep(3.0)
                    continue
                print("  [Translation] All retries exhausted, falling back to per-segment.")
                return self._fallback_per_segment(segments, source_language, target_language)

        return self._fallback_per_segment(segments, source_language, target_language)

    def _fallback_per_segment(
        self,
        segments: List[SourceSegment],
        source_language: str,
        target_language: str,
    ) -> List[TranslatedSegment]:
        results = []
        for seg in segments:
            try:
                text = self.translate(seg.text, source_language, target_language)
            except Exception as e:
                print(f"  [Translation] Segment {seg.id} fallback warning: {e}")
                text = seg.text
            results.append(
                TranslatedSegment(
                    id=seg.id,
                    source=seg,
                    language=target_language,
                    text=text.strip(),
                )
            )
            time.sleep(1.0)
        return results
