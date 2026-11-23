"""Unified Gemini client manager with retry, telemetry, and quota handling."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Optional

from google import genai
from google.genai.errors import ClientError

from core.api.key_pool import APIKeyPool, ManagedKey, get_key_pool
from core.telemetry.counters import get_telemetry_counters
from core.telemetry.timer import TaskTimer

logger = logging.getLogger(__name__)


class GeminiClientManager:
    """Manages cached Gemini client instances, automatic key rotation, and resilient retries."""

    def __init__(self, key_pool: Optional[APIKeyPool] = None) -> None:
        self.key_pool = key_pool or get_key_pool()
        self._clients: Dict[str, genai.Client] = {}
        self._lock = threading.Lock()
        self.counters = get_telemetry_counters()
        self._last_switched_key_idx: Optional[int] = None

    def _get_client_for_key(self, api_key: str) -> genai.Client:
        with self._lock:
            if api_key not in self._clients:
                self._clients[api_key] = genai.Client(api_key=api_key)
            return self._clients[api_key]

    def get_current_client(self) -> genai.Client:
        current_key = self.key_pool.get_current_key()
        return self._get_client_for_key(current_key.key)

    def rotate_key(self) -> ManagedKey:
        return self.key_pool.rotate_key()

    def execute_stream_with_retry(
        self,
        model: str,
        contents: Any,
        config: Any,
        max_retries: int = 100,
    ) -> bytes:
        """Stream audio or content generation with automatic key rotation and model fallback."""
        attempts = 0
        cur_model = model

        while attempts < max_retries:
            attempts += 1
            managed_key = self.key_pool.get_best_key(model=cur_model)
            client = self._get_client_for_key(managed_key.key)

            self.counters.inc_api_call(provider="gemini", model=cur_model)

            with TaskTimer(f"stream_{cur_model}", category="api_stream") as timer:
                try:
                    audio_data = bytearray()
                    stream = client.models.generate_content_stream(
                        model=cur_model,
                        contents=contents,
                        config=config,
                    )
                    for chunk in stream:
                        if chunk.parts:
                            for p in chunk.parts:
                                if p.inline_data and p.inline_data.data:
                                    audio_data.extend(p.inline_data.data)

                    # Success: mark key and telemetry
                    managed_key.mark_success()
                    self.key_pool._consecutive_429 = 0
                    self.counters.inc_bytes_generated("audio_pcm", len(audio_data))
                    timer.set_metadata("bytes", len(audio_data))
                    return bytes(audio_data)

                except ClientError as e:
                    err_str = str(e)
                    self.counters.inc_api_failure(provider="gemini", error_type="ClientError")

                    if "limit: 10" in err_str or "GenerateRequestsPerDay" in err_str:
                        self.counters.inc_retry(provider="gemini", reason="daily_limit")
                        print(
                            f"  ⚠️ [ليميت / Limit] تم بلوغ الحد اليومي للمفتاح #{managed_key.index + 1} ({managed_key.masked_key}) على الموديل {cur_model}. التدوير إلى API Key آخر مع البقاء على الموديل الأفضل دون تغييره...",
                            flush=True,
                        )
                        self.key_pool.handle_daily_limit(managed_key, cur_model)
                        self.key_pool.rotate_key()
                        time.sleep(1.0)
                        continue

                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        self.counters.inc_retry(provider="gemini", reason="429")
                        print(
                            f"  ⚠️ [ليميت / Limit] خطأ استنفاد كوتا 429 للمفتاح #{managed_key.index + 1} ({managed_key.masked_key}). التدوير إلى API Key آخر...",
                            flush=True,
                        )
                        self.key_pool.handle_429(managed_key, err_str)
                        continue

                    if "401" in err_str or "UNAUTHENTICATED" in err_str or "invalid authentication" in err_str.lower():
                        self.counters.inc_retry(provider="gemini", reason="unauthenticated")
                        self.key_pool.handle_daily_limit(managed_key, cur_model)
                        print(
                            f"  ⚠️ [ليميت / Limit] خطأ مصادقة على المفتاح #{managed_key.index + 1} للموديل {cur_model}; التدوير لمفتاح آخر...",
                            flush=True,
                        )
                        self.key_pool.rotate_key()
                        continue
                    else:
                        print(
                            f"  ⚠️ [ليميت / Limit] خطأ ClientError: {err_str[:120]}; التدوير لمفتاح آخر...",
                            flush=True,
                        )
                        self.key_pool.rotate_key()
                        time.sleep(2.0)
                        continue

                except Exception as e:
                    self.counters.inc_api_failure(provider="gemini", error_type=type(e).__name__)
                    self.counters.inc_retry(provider="gemini", reason="network_or_system")
                    print(
                        f"  ⚠️ [ليميت / Limit] خطأ في الاتصال أو الخادم ({e}); التدوير إلى API Key آخر والمتابعة فوراً...",
                        flush=True,
                    )
                    self.key_pool.rotate_key()
                    time.sleep(3.0)

        raise RuntimeError(
            f"Failed to execute stream on model {cur_model} after {max_retries} attempts."
        )

    def execute_content_with_retry(
        self,
        model: str,
        contents: Any,
        config: Any = None,
        max_retries: int = 60,
    ) -> Any:
        """Generate content with automatic key rotation, 429 cooldowns, and 503 fallback."""
        attempts = 0
        cur_model = model

        while attempts < max_retries:
            attempts += 1
            managed_key = self.key_pool.get_best_key(model=cur_model)
            client = self._get_client_for_key(managed_key.key)

            self.counters.inc_api_call(provider="gemini", model=cur_model)

            with TaskTimer(f"content_{cur_model}", category="api_content") as timer:
                try:
                    resp = client.models.generate_content(
                        model=cur_model,
                        contents=contents,
                        config=config,
                    )
                    managed_key.mark_success()
                    self.key_pool._consecutive_429 = 0
                    return resp

                except ClientError as e:
                    err_str = str(e)
                    self.counters.inc_api_failure(provider="gemini", error_type="ClientError")
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        self.counters.inc_retry(provider="gemini", reason="429")
                        self.key_pool.handle_429(managed_key, err_str)
                        continue
                    if "401" in err_str or "UNAUTHENTICATED" in err_str or "invalid authentication" in err_str.lower():
                        self.counters.inc_retry(provider="gemini", reason="unauthenticated")
                        self.key_pool.handle_daily_limit(managed_key, cur_model)
                        print(
                            f"  [ClientManager] WARNING: Key #{managed_key.index + 1} rejected by Gemini for {cur_model}; trying another key...",
                            flush=True,
                        )
                        continue
                    else:
                        raise e

                except Exception as e:
                    err_s = str(e)
                    self.counters.inc_api_failure(provider="gemini", error_type=type(e).__name__)
                    if ("503" in err_s or "UNAVAILABLE" in err_s) and cur_model != "gemini-3.5-flash":
                        self.counters.inc_retry(provider="gemini", reason="503_fallback")
                        print(f"  [ClientManager] 503 spike on {cur_model}. Switching to gemini-3.5-flash...", flush=True)
                        cur_model = "gemini-3.5-flash"
                        time.sleep(2)
                        continue
                    print(f"  [ClientManager] WARNING: Non-client error: {e}, retrying in 5s...", flush=True)
                    time.sleep(5)

        raise RuntimeError(
            f"Failed to execute content on model {cur_model} after {max_retries} attempts."
        )


_GLOBAL_CLIENT_MANAGER: Optional[GeminiClientManager] = None
_MANAGER_LOCK = threading.Lock()


def get_client_manager() -> GeminiClientManager:
    global _GLOBAL_CLIENT_MANAGER
    with _MANAGER_LOCK:
        if _GLOBAL_CLIENT_MANAGER is None:
            _GLOBAL_CLIENT_MANAGER = GeminiClientManager()
        return _GLOBAL_CLIENT_MANAGER
