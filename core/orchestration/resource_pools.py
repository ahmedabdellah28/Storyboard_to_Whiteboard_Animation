"""Semaphore-based resource pools for concurrency and hardware protection."""

from __future__ import annotations

import contextlib
import threading
from typing import Dict, Iterator, Optional


class ResourcePoolManager:
    """Manages bounded concurrency semaphores across disparate hardware resources.

    - NETWORK_API: Free Gemini API calls (capped to key count to avoid 429 floods)
    - CPU_HEAVY: Whisper ASR, OpenCV cell segmentation (caps CPU core saturation)
    - GPU_RENDER: Hardware NVENC encoder (locks single hardware render slot to avoid NVENC crashes)
    - DISK_IO: FFmpeg muxing and file I/O operations
    """

    def __init__(
        self,
        network_api_slots: int = 4,
        cpu_heavy_slots: int = 2,
        gpu_render_slots: int = 1,
        disk_io_slots: int = 3,
    ) -> None:
        self._pools: Dict[str, threading.BoundedSemaphore] = {
            "NETWORK_API": threading.BoundedSemaphore(max(1, network_api_slots)),
            "CPU_HEAVY": threading.BoundedSemaphore(max(1, cpu_heavy_slots)),
            "GPU_RENDER": threading.BoundedSemaphore(max(1, gpu_render_slots)),
            "DISK_IO": threading.BoundedSemaphore(max(1, disk_io_slots)),
            "DEFAULT": threading.BoundedSemaphore(4),
        }
        self._lock = threading.Lock()

    def get_semaphore(self, resource_type: str) -> threading.BoundedSemaphore:
        with self._lock:
            if resource_type not in self._pools:
                self._pools[resource_type] = threading.BoundedSemaphore(2)
            return self._pools[resource_type]

    @contextlib.contextmanager
    def acquire(self, resource_type: str, timeout: Optional[float] = None) -> Iterator[bool]:
        """Acquire a slot in the specified resource pool contextually."""
        sem = self.get_semaphore(resource_type)
        if timeout is not None:
            acquired = sem.acquire(timeout=timeout)
        else:
            acquired = sem.acquire(blocking=True)
        if not acquired:
            raise TimeoutError(f"Timed out acquiring resource {resource_type}")
        try:
            yield acquired
        finally:
            sem.release()


_GLOBAL_RESOURCE_MANAGER: Optional[ResourcePoolManager] = None
_RES_LOCK = threading.Lock()


def get_resource_manager() -> ResourcePoolManager:
    global _GLOBAL_RESOURCE_MANAGER
    with _RES_LOCK:
        if _GLOBAL_RESOURCE_MANAGER is None:
            _GLOBAL_RESOURCE_MANAGER = ResourcePoolManager()
        return _GLOBAL_RESOURCE_MANAGER
