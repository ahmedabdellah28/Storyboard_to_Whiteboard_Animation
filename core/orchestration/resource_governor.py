"""Dynamic hardware-profiled resource governor and GPU device mutex.

Part of Phase 4: ResourceGovernor, WorkerManager & Cancellation.
Replaces static constants with mathematical capacity budgeting across consumer and workstation PCs.
"""

from __future__ import annotations

import enum
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

from core.validation.environment_doctor import EnvironmentDoctor


class ResourceProfile(str, enum.Enum):
    LOW = "LOW"                   # Low-power / 8GB RAM laptops
    BALANCED = "BALANCED"         # Standard 16GB RAM desktop/laptop
    PERFORMANCE = "PERFORMANCE"   # 32GB+ RAM / Multi-core workstation
    AUTO = "AUTO"                 # Dynamic calculation based on host telemetry


@dataclass(frozen=True)
class ResourceBudget:
    """Calculated hardware resource budget allocations."""
    profile: ResourceProfile
    max_concurrent_tasks: int
    cpu_heavy_slots: int
    network_api_slots: int
    gpu_render_slots: int
    disk_io_slots: int
    os_reserve_gb: float
    preview_cache_mb: int
    render_encoder: str           # h264_nvenc, h264_qsv, libx264
    has_gpu_acceleration: bool


class GpuDeviceLock:
    """Global mutual exclusion lock regulating hardware video encoding and GPU memory."""
    _instance: Optional[GpuDeviceLock] = None
    _lock = threading.Lock()

    def __new__(cls) -> GpuDeviceLock:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._mutex = threading.Lock()
            return cls._instance

    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        return self._mutex.acquire(blocking=blocking, timeout=timeout)

    def release(self) -> None:
        self._mutex.release()

    def __enter__(self) -> bool:
        return self._mutex.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._mutex.release()


class ResourceGovernor:
    """Calculates safe hardware budgets and dynamically provisions concurrency pools."""

    def __init__(self, profile: ResourceProfile = ResourceProfile.AUTO) -> None:
        self.profile = profile
        self.gpu_lock = GpuDeviceLock()
        self._budget = self.calculate_budget(self.profile)

    @property
    def budget(self) -> ResourceBudget:
        return self._budget

    @classmethod
    def get_hardware_telemetry(cls) -> Dict[str, Any]:
        """Probe host CPU, RAM, and GPU telemetry."""
        logical_cores = os.cpu_count() or 4
        physical_cores = logical_cores // 2 if logical_cores > 1 else 1
        total_ram_gb = 16.0
        avail_ram_gb = 8.0

        if _HAS_PSUTIL:
            try:
                logical_cores = psutil.cpu_count(logical=True) or logical_cores
                physical_cores = psutil.cpu_count(logical=False) or physical_cores
                vm = psutil.virtual_memory()
                total_ram_gb = round(vm.total / (1024 ** 3), 2)
                avail_ram_gb = round(vm.available / (1024 ** 3), 2)
            except Exception:
                pass

        enc_info = EnvironmentDoctor.probe_hardware_encoders()

        return {
            "logical_cores": logical_cores,
            "physical_cores": physical_cores,
            "total_ram_gb": total_ram_gb,
            "avail_ram_gb": avail_ram_gb,
            "primary_encoder": enc_info.get("primary_encoder", "libx264"),
            "has_gpu_acceleration": enc_info.get("has_gpu_acceleration", False),
        }

    @classmethod
    def calculate_budget(cls, profile: ResourceProfile) -> ResourceBudget:
        """Compute mathematical resource allocations."""
        hw = cls.get_hardware_telemetry()
        total_ram = hw["total_ram_gb"]
        avail_ram = hw["avail_ram_gb"]
        phys_cores = hw["physical_cores"]
        primary_enc = hw["primary_encoder"]
        has_gpu = hw["has_gpu_acceleration"]

        if profile == ResourceProfile.LOW:
            return ResourceBudget(
                profile=ResourceProfile.LOW,
                max_concurrent_tasks=1,
                cpu_heavy_slots=1,
                network_api_slots=2,
                gpu_render_slots=1,
                disk_io_slots=1,
                os_reserve_gb=2.5,
                preview_cache_mb=512,
                render_encoder="libx264",
                has_gpu_acceleration=False,
            )

        if profile == ResourceProfile.BALANCED:
            return ResourceBudget(
                profile=ResourceProfile.BALANCED,
                max_concurrent_tasks=2,
                cpu_heavy_slots=max(1, min(2, phys_cores - 1)),
                network_api_slots=4,
                gpu_render_slots=1,
                disk_io_slots=2,
                os_reserve_gb=3.5,
                preview_cache_mb=1536,
                render_encoder=primary_enc,
                has_gpu_acceleration=has_gpu,
            )

        if profile == ResourceProfile.PERFORMANCE:
            return ResourceBudget(
                profile=ResourceProfile.PERFORMANCE,
                max_concurrent_tasks=max(2, min(8, phys_cores - 1)),
                cpu_heavy_slots=max(2, min(4, phys_cores - 2)),
                network_api_slots=6,
                gpu_render_slots=2 if total_ram >= 32.0 and has_gpu else 1,
                disk_io_slots=4,
                os_reserve_gb=5.0,
                preview_cache_mb=4096,
                render_encoder=primary_enc,
                has_gpu_acceleration=has_gpu,
            )

        # AUTO Formula:
        # max_tasks = max(1, min(4, floor((avail_ram - 3GB) / 2.5GB)))
        safe_ram_tasks = max(1, min(4, int(max(0, avail_ram - 3.0) / 2.5)))
        safe_cpu_tasks = max(1, min(4, phys_cores - 1))
        auto_tasks = min(safe_ram_tasks, safe_cpu_tasks)

        cpu_slots = max(1, min(2, auto_tasks))
        preview_cache = min(4096, max(512, int(avail_ram * 1024 * 0.10)))
        os_reserve = max(2.5, round(total_ram * 0.20, 1))

        return ResourceBudget(
            profile=ResourceProfile.AUTO,
            max_concurrent_tasks=auto_tasks,
            cpu_heavy_slots=cpu_slots,
            network_api_slots=4,
            gpu_render_slots=1,
            disk_io_slots=2,
            os_reserve_gb=os_reserve,
            preview_cache_mb=preview_cache,
            render_encoder=primary_enc if has_gpu and avail_ram >= 2.5 else "libx264",
            has_gpu_acceleration=has_gpu and avail_ram >= 2.5,
        )

    def apply_to_resource_pool(self, pool_manager: Any) -> None:
        """Configure concurrency semaphores in ResourcePoolManager to match budget."""
        b = self._budget
        with pool_manager._lock:
            pool_manager._pools["NETWORK_API"] = threading.BoundedSemaphore(b.network_api_slots)
            pool_manager._pools["CPU_HEAVY"] = threading.BoundedSemaphore(b.cpu_heavy_slots)
            pool_manager._pools["GPU_RENDER"] = threading.BoundedSemaphore(b.gpu_render_slots)
            pool_manager._pools["DISK_IO"] = threading.BoundedSemaphore(b.disk_io_slots)


_GLOBAL_GOVERNOR: Optional[ResourceGovernor] = None
_GOV_LOCK = threading.Lock()


def get_resource_governor() -> ResourceGovernor:
    global _GLOBAL_GOVERNOR
    with _GOV_LOCK:
        if _GLOBAL_GOVERNOR is None:
            _GLOBAL_GOVERNOR = ResourceGovernor()
        return _GLOBAL_GOVERNOR
