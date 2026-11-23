"""Worker orchestration, priority scheduling, and cooperative task cancellation.

Part of Phase 4: ResourceGovernor, WorkerManager & Cancellation.
Guarantees clean process management and instant cancellation without leaving zombie background threads.
"""

from __future__ import annotations

import concurrent.futures
import enum
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


class OperationCancelledException(Exception):
    """Raised when an operation is aborted via a CancellationToken."""
    pass


class CancellationToken:
    """Thread-safe cooperative cancellation token."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self.reason: Optional[str] = None

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self, reason: str = "User cancelled execution") -> None:
        self.reason = reason
        self._event.set()

    def throw_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise OperationCancelledException(self.reason or "Operation was cancelled.")

    @property
    def event(self) -> threading.Event:
        return self._event


class WorkerPriority(enum.IntEnum):
    """Execution priority levels for background tasks."""
    CRITICAL_UI = 1      # Immediate user scrub and viewport drag (<16ms)
    PREVIEW = 2          # Audio / video playback buffer streaming
    BACKGROUND = 3       # Pre-render tasks 00..13 (Whisper, Layout, Choreography)
    BATCH_RENDER = 4     # Heavy video frame rendering (Stage 14/15, GPU mutex)


class WorkerManager:
    """Manages thread pools, section task submissions, and selective cancellations."""

    def __init__(self, max_workers: int = 4) -> None:
        self.max_workers = max_workers
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="WhiteboardWorker",
        )
        self._active_tokens: Dict[str, CancellationToken] = {}
        self._active_futures: Dict[str, concurrent.futures.Future] = {}
        self._lock = threading.RLock()

    def submit_section(
        self,
        section_id: str,
        task_fn: Callable[[CancellationToken], Any],
    ) -> concurrent.futures.Future:
        """Submit a section execution job with an attached cancellation token."""
        with self._lock:
            # If section is already running, cancel previous execution
            if section_id in self._active_tokens:
                self.cancel_section(section_id, reason="Superseded by new submission")

            token = CancellationToken()
            self._active_tokens[section_id] = token

            def _wrapped():
                try:
                    return task_fn(token)
                finally:
                    with self._lock:
                        self._active_tokens.pop(section_id, None)
                        self._active_futures.pop(section_id, None)

            future = self._executor.submit(_wrapped)
            self._active_futures[section_id] = future
            return future

    def cancel_section(self, section_id: str, reason: str = "User cancelled section") -> bool:
        """Signal cancellation for a specific section worker."""
        with self._lock:
            token = self._active_tokens.get(section_id)
            if token:
                token.cancel(reason=reason)
                fut = self._active_futures.get(section_id)
                if fut and not fut.running():
                    fut.cancel()
                return True
            return False

    def cancel_all(self, reason: str = "User cancelled all operations") -> None:
        """Cancel all active section workers."""
        with self._lock:
            for sid, token in list(self._active_tokens.items()):
                token.cancel(reason=reason)
            for sid, fut in list(self._active_futures.items()):
                if not fut.running():
                    fut.cancel()

    def is_section_running(self, section_id: str) -> bool:
        """Check if a section has an active worker executing."""
        with self._lock:
            return section_id in self._active_tokens

    def get_token(self, section_id: str) -> Optional[CancellationToken]:
        """Fetch active token for a section."""
        with self._lock:
            return self._active_tokens.get(section_id)

    def shutdown(self, wait: bool = False) -> None:
        """Shutdown thread pool cleanly."""
        self.cancel_all(reason="Application shutting down")
        self._executor.shutdown(wait=wait, cancel_futures=True)


_GLOBAL_WORKER_MANAGER: Optional[WorkerManager] = None
_WORKER_LOCK = threading.Lock()


def get_worker_manager() -> WorkerManager:
    global _GLOBAL_WORKER_MANAGER
    with _WORKER_LOCK:
        if _GLOBAL_WORKER_MANAGER is None:
            _GLOBAL_WORKER_MANAGER = WorkerManager()
        return _GLOBAL_WORKER_MANAGER
