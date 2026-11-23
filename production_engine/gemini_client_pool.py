"""Gemini Client Pool adapter backed by unified core.api foundation.

Maintains 100% backward compatibility with legacy calls while leveraging
centralized key pooling, telemetry, least-loaded rotation, and rate limiting.
"""

from __future__ import annotations

import os
from typing import Any, List, Optional

from core.api.client_manager import GeminiClientManager, get_client_manager
from core.api.key_pool import get_key_pool
from core.config.env_loader import get_gemini_api_keys
from core.config.settings import PROJECT_ROOT

ROOT_DIR = str(PROJECT_ROOT)


def load_all_api_keys() -> List[str]:
    """Retrieve all valid Gemini API keys using the unified core env loader."""
    keys = get_gemini_api_keys()
    if not keys and os.environ.get("GEMINI_API_KEY"):
        keys.append(os.environ["GEMINI_API_KEY"])
    return keys


class GeminiClientPool:
    """Adapter wrapping GeminiClientManager for legacy calls."""

    def __init__(self, manager: Optional[GeminiClientManager] = None) -> None:
        self._manager = manager or get_client_manager()
        self.keys = [k.key for k in self._manager.key_pool.keys]
        self.clients = [self._manager._get_client_for_key(k) for k in self.keys]
        print(f"[GeminiClientPool] Initialized with {len(self.keys)} API keys via core.api.", flush=True)

    @property
    def current_idx(self) -> int:
        return self._manager.key_pool.current_idx

    @current_idx.setter
    def current_idx(self, val: int) -> None:
        self._manager.key_pool.current_idx = val

    @property
    def _consecutive_429(self) -> int:
        return self._manager.key_pool._consecutive_429

    @_consecutive_429.setter
    def _consecutive_429(self, val: int) -> None:
        self._manager.key_pool._consecutive_429 = val

    def get_current_client(self) -> Any:
        return self._manager.get_current_client()

    def rotate_key(self) -> None:
        self._manager.rotate_key()

    def _handle_429(self, err_str: str) -> None:
        current_key = self._manager.key_pool.get_current_key()
        self._manager.key_pool.handle_429(current_key, err_str)

    def execute_stream_with_retry(
        self,
        model: str,
        contents: Any,
        config: Any,
        max_retries: int = 100,
    ) -> bytes:
        return self._manager.execute_stream_with_retry(
            model=model,
            contents=contents,
            config=config,
            max_retries=max_retries,
        )

    def execute_content_with_retry(
        self,
        model: str,
        contents: Any,
        config: Any = None,
        max_retries: int = 60,
    ) -> Any:
        return self._manager.execute_content_with_retry(
            model=model,
            contents=contents,
            config=config,
            max_retries=max_retries,
        )


_global_pool: Optional[GeminiClientPool] = None


def get_client_pool() -> GeminiClientPool:
    global _global_pool
    if _global_pool is None:
        _global_pool = GeminiClientPool()
    return _global_pool
