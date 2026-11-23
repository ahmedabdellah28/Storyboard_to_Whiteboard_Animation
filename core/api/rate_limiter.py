"""Token-bucket rate limiter for API calls."""

from __future__ import annotations

import threading
import time
from typing import Optional


class TokenBucketRateLimiter:
    """Thread-safe token bucket rate limiter.

    Args:
        rpm: Permitted requests per minute.
        burst_capacity: Maximum number of tokens that can accumulate.
    """

    def __init__(self, rpm: int = 15, burst_capacity: Optional[int] = None) -> None:
        self.rpm = max(1, rpm)
        self.capacity = burst_capacity if burst_capacity is not None else self.rpm
        self.tokens = float(self.capacity)
        self.refill_rate = self.rpm / 60.0  # tokens per second
        self.last_refill = time.perf_counter()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.perf_counter()
        elapsed = now - self.last_refill
        if elapsed > 0:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

    def acquire(self, tokens: int = 1, timeout: float = 60.0) -> bool:
        """Attempt to acquire tokens, waiting if necessary until available or timeout."""
        start = time.perf_counter()
        while True:
            with self._lock:
                self._refill()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

                needed = tokens - self.tokens
                wait_time = needed / self.refill_rate

            remaining_timeout = timeout - (time.perf_counter() - start)
            if remaining_timeout <= 0:
                return False

            sleep_time = min(wait_time, remaining_timeout, 1.0)
            if sleep_time > 0:
                time.sleep(sleep_time)
