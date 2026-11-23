"""Unified Gemini API key pool management.

Provides thread-safe key rotation, cooldown tracking, least-loaded selection,
and quota failure handling across all subsystems.
"""

from __future__ import annotations

import enum
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from core.config.env_loader import get_gemini_api_keys
from core.telemetry.counters import get_telemetry_counters


class KeyStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    RATE_LIMITED = "RATE_LIMITED"
    DAILY_EXHAUSTED = "DAILY_EXHAUSTED"


@dataclass
class ManagedKey:
    key: str
    index: int
    status: KeyStatus = KeyStatus.ACTIVE
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rate_limit_hits: int = 0
    cooldown_until: float = 0.0
    exhausted_models: Set[str] = field(default_factory=set)
    last_used_at: float = 0.0

    def is_available(self, model: Optional[str] = None) -> bool:
        now = time.time()
        if self.status == KeyStatus.DAILY_EXHAUSTED:
            return False
        if model and model in self.exhausted_models:
            return False
        if self.status == KeyStatus.RATE_LIMITED:
            if now >= self.cooldown_until:
                self.status = KeyStatus.ACTIVE
                return True
            return False
        return True

    def mark_success(self) -> None:
        self.successful_calls += 1
        self.status = KeyStatus.ACTIVE

    def mark_rate_limited(self, cooldown_seconds: float) -> None:
        self.rate_limit_hits += 1
        self.status = KeyStatus.RATE_LIMITED
        self.cooldown_until = time.time() + cooldown_seconds

    def mark_model_exhausted(self, model: str) -> None:
        self.exhausted_models.add(model)

    @property
    def masked_key(self) -> str:
        if len(self.key) <= 10:
            return "***"
        return f"{self.key[:6]}...{self.key[-4:]}"


class APIKeyPool:
    """Thread-safe API key pool manager."""

    def __init__(self, keys: Optional[List[str]] = None) -> None:
        self._lock = threading.Lock()
        raw_keys = keys if keys is not None else get_gemini_api_keys()
        if not raw_keys:
            raise ValueError("No Gemini API keys found! Please configure GEMINI_API_KEY in .env.")

        self.keys: List[ManagedKey] = [
            ManagedKey(key=k, index=idx) for idx, k in enumerate(raw_keys)
        ]
        self.current_idx: int = 0
        self._consecutive_429: int = 0
        self.counters = get_telemetry_counters()
        print(f"[APIKeyPool] Initialized with {len(self.keys)} managed API keys.", flush=True)

    def __len__(self) -> int:
        return len(self.keys)

    def get_current_key(self) -> ManagedKey:
        with self._lock:
            return self.keys[self.current_idx]

    def get_best_key(self, model: Optional[str] = None) -> ManagedKey:
        """Select the available key with the lowest total call count (least-loaded)."""
        with self._lock:
            available = [k for k in self.keys if k.is_available(model)]
            if available:
                best = min(available, key=lambda k: k.total_calls)
                self.current_idx = best.index
                best.total_calls += 1
                best.last_used_at = time.time()
                return best

            # If none available, pick the one closest to cooldown expiration
            rate_limited = [k for k in self.keys if k.status == KeyStatus.RATE_LIMITED]
            if rate_limited:
                soonest = min(rate_limited, key=lambda k: k.cooldown_until)
                self.current_idx = soonest.index
                soonest.total_calls += 1
                soonest.last_used_at = time.time()
                return soonest

            # Fallback to current key
            curr = self.keys[self.current_idx]
            curr.total_calls += 1
            curr.last_used_at = time.time()
            return curr

    def rotate_key(self) -> ManagedKey:
        """Rotate to the next key index."""
        with self._lock:
            prev = self.current_idx
            self.current_idx = (self.current_idx + 1) % len(self.keys)
            next_key = self.keys[self.current_idx]
            print(
                f"  [APIKeyPool] Rotating API Key: #{prev + 1} ({self.keys[prev].masked_key}) "
                f"-> #{self.current_idx + 1} ({next_key.masked_key})",
                flush=True,
            )
            return next_key

    def handle_429(self, key: ManagedKey, err_str: str, default_cooldown: int = 50) -> float:
        """Handle 429 rate limit error: mark key, calculate cooldown, and manage global cooldown if all exhausted."""
        with self._lock:
            self._consecutive_429 += 1
            self.counters.inc_rate_limit(provider="gemini", key_id=f"key_{key.index + 1}")

            # Parse retryDelay from error message
            delay_match = re.search(r'retryDelay[\'"]?:\s*[\'"]?([0-9]+)s', err_str)
            delay = int(delay_match.group(1)) + 5 if delay_match else default_cooldown
            delay = max(delay, default_cooldown)

            key.mark_rate_limited(delay)
            print(
                f"  [APIKeyPool] WARNING: Key #{key.index + 1} ({key.masked_key}) hit rate limit (429). Cooldown: {delay}s",
                flush=True,
            )

            all_exhausted = all(not k.is_available() for k in self.keys)
            if self._consecutive_429 >= len(self.keys) or all_exhausted:
                print(
                    f"  [APIKeyPool] ALERT: All {len(self.keys)} keys exhausted! Sleeping {delay}s to reset RPM quota...",
                    flush=True,
                )
                time.sleep(delay)
                self._consecutive_429 = 0
                for k in self.keys:
                    k.status = KeyStatus.ACTIVE

            self.current_idx = (self.current_idx + 1) % len(self.keys)
            time.sleep(2.0)
            return float(delay)

    def handle_daily_limit(self, key: ManagedKey, model: str) -> None:
        """Mark a specific model exhausted for a key when daily quota is reached."""
        with self._lock:
            key.mark_model_exhausted(model)
            print(
                f"  [APIKeyPool] WARNING: Key #{key.index + 1} ({key.masked_key}) exhausted daily quota for model {model}.",
                flush=True,
            )

    def probe_keys(self, model: str = "gemini-3.8-flash-tts", timeout_ms: int = 20000) -> Dict[str, Any]:
        """Pre-flight Key Limit Check across all configured keys for a target Gemini model."""
        from google import genai
        from google.genai import types

        results: List[Dict[str, Any]] = []
        active_count = 0
        for mk in self.keys:
            t0 = time.time()
            entry: Dict[str, Any] = {
                "index": mk.index + 1,
                "masked_key": mk.masked_key,
                "status": "UNKNOWN",
                "latency_sec": 0.0,
                "detail": "",
            }
            try:
                client = genai.Client(api_key=mk.key, http_options=types.HttpOptions(timeout=timeout_ms))
                if "tts" in model.lower():
                    cfg = types.GenerateContentConfig(
                        temperature=0.3,
                        response_modalities=["audio"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Fenrir")
                            )
                        ),
                    )
                    got = 0
                    for ch in client.models.generate_content_stream(model=model, contents="مرحبا", config=cfg):
                        if ch.parts:
                            for pt in ch.parts:
                                if pt.inline_data and pt.inline_data.data:
                                    got += len(pt.inline_data.data)
                    if got <= 0:
                        raise RuntimeError("Empty audio buffer")
                    entry["detail"] = f"audio_bytes={got}"
                else:
                    client.models.generate_content(model=model, contents="ping")
                    entry["detail"] = "ok"
                mk.status = KeyStatus.ACTIVE
                mk.exhausted_models.discard(model)
                entry["status"] = "ACTIVE"
                active_count += 1
            except Exception as exc:
                msg = str(exc).replace("\n", " ")
                if "PerDay" in msg or "GenerateRequestsPerDay" in msg or "403" in msg or "PERMISSION_DENIED" in msg:
                    mk.mark_model_exhausted(model)
                    entry["status"] = "EXHAUSTED_OR_DENIED"
                elif "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    mk.mark_rate_limited(60.0)
                    entry["status"] = "RATE_LIMITED_429"
                else:
                    entry["status"] = "ERROR"
                entry["detail"] = msg[:160]
            entry["latency_sec"] = round(time.time() - t0, 2)
            results.append(entry)
        return {
            "model": model,
            "total_keys": len(self.keys),
            "active_keys": active_count,
            "keys": results,
        }


_GLOBAL_KEY_POOL: Optional[APIKeyPool] = None
_POOL_LOCK = threading.Lock()


def get_key_pool(force_reload: bool = False) -> APIKeyPool:
    global _GLOBAL_KEY_POOL
    with _POOL_LOCK:
        if _GLOBAL_KEY_POOL is None or force_reload:
            _GLOBAL_KEY_POOL = APIKeyPool()
        return _GLOBAL_KEY_POOL
