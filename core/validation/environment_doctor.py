"""System environment diagnostics, hardware encoder probe, and runtime health doctor.

Part of Phase 3: Validation System & Recovery System.
Ensures zero-crash desktop deployment across heterogeneous consumer PCs.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config.settings import PROJECT_ROOT


@dataclass
class SystemDiagnosticReport:
    """Consolidated diagnostic report of host environment health."""
    is_healthy: bool = True
    ffmpeg_available: bool = False
    ffmpeg_version: str = "Unknown"
    hardware_encoder: str = "libx264"
    available_encoders: List[str] = field(default_factory=list)
    free_disk_gb: float = 0.0
    python_version: str = field(default_factory=lambda: sys.version.split()[0])
    dependencies_intact: bool = True
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class EnvironmentDoctor:
    """Probes system binaries, hardware acceleration, and disk health."""

    @staticmethod
    def find_ffmpeg_binary() -> Optional[str]:
        """Locate FFmpeg in project bin/ or system PATH."""
        # 1. Project local bundled bin directory
        local_bin = PROJECT_ROOT / "bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if local_bin.is_file():
            return str(local_bin)

        # 2. System PATH
        system_bin = shutil.which("ffmpeg")
        if system_bin:
            return system_bin

        return None

    @classmethod
    def check_ffmpeg(cls) -> Dict[str, Any]:
        """Verify FFmpeg execution and fetch version."""
        ffmpeg_bin = cls.find_ffmpeg_binary()
        if not ffmpeg_bin:
            return {
                "available": False,
                "version": "Not Found",
                "path": None,
                "error": "FFmpeg executable not found in PATH or project bin/",
            }

        try:
            res = subprocess.run([ffmpeg_bin, "-version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                first_line = res.stdout.splitlines()[0] if res.stdout else "ffmpeg version unknown"
                return {
                    "available": True,
                    "version": first_line,
                    "path": ffmpeg_bin,
                    "error": None,
                }
            return {
                "available": False,
                "version": "Error",
                "path": ffmpeg_bin,
                "error": f"FFmpeg returned exit code {res.returncode}",
            }
        except Exception as e:
            return {
                "available": False,
                "version": "Execution Failed",
                "path": ffmpeg_bin,
                "error": str(e),
            }

    @classmethod
    def probe_hardware_encoders(cls) -> Dict[str, Any]:
        """Detect GPU hardware video encoders (NVENC, QSV, AMF) with CPU fallback."""
        ffmpeg_bin = cls.find_ffmpeg_binary()
        if not ffmpeg_bin:
            return {
                "primary_encoder": "libx264",
                "available_encoders": ["libx264"],
                "has_gpu_acceleration": False,
            }

        available = []
        try:
            res = subprocess.run([ffmpeg_bin, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=5)
            stdout = res.stdout or ""

            if "h264_nvenc" in stdout:
                available.append("h264_nvenc")
            if "h264_qsv" in stdout:
                available.append("h264_qsv")
            if "h264_amf" in stdout:
                available.append("h264_amf")
            if "libx264" in stdout:
                available.append("libx264")
        except Exception:
            available = ["libx264"]

        if not available:
            available = ["libx264"]

        # Selection priority
        primary = "libx264"
        if "h264_nvenc" in available:
            primary = "h264_nvenc"
        elif "h264_qsv" in available:
            primary = "h264_qsv"
        elif "h264_amf" in available:
            primary = "h264_amf"

        return {
            "primary_encoder": primary,
            "available_encoders": available,
            "has_gpu_acceleration": primary != "libx264",
        }

    @staticmethod
    def check_storage_space(target_path: Optional[Path] = None) -> float:
        """Return free space in Gigabytes for the specified path."""
        p = Path(target_path or PROJECT_ROOT)
        try:
            usage = shutil.disk_usage(p)
            return round(usage.free / (1024 ** 3), 2)
        except Exception:
            return 0.0

    @classmethod
    def run_full_diagnosis(cls) -> SystemDiagnosticReport:
        """Run complete environment diagnostic scan."""
        report = SystemDiagnosticReport()

        # 1. FFmpeg
        ff_info = cls.check_ffmpeg()
        report.ffmpeg_available = ff_info["available"]
        report.ffmpeg_version = ff_info["version"]
        if not report.ffmpeg_available:
            report.is_healthy = False
            report.issues.append("FFmpeg is missing or not executable.")
            report.recommendations.append("Install FFmpeg or place ffmpeg.exe in the project bin/ folder.")

        # 2. Hardware Encoders
        enc_info = cls.probe_hardware_encoders()
        report.hardware_encoder = enc_info["primary_encoder"]
        report.available_encoders = enc_info["available_encoders"]
        report.details["gpu_accelerated"] = enc_info["has_gpu_acceleration"]

        if not enc_info["has_gpu_acceleration"]:
            report.recommendations.append(
                "GPU hardware encoder not detected. Production will use CPU libx264 fallback (Balanced/Low profile)."
            )

        # 3. Storage
        free_gb = cls.check_storage_space()
        report.free_disk_gb = free_gb
        if free_gb < 2.0:
            report.issues.append(f"Low disk space: {free_gb} GB remaining.")
            report.recommendations.append("Free at least 5 GB for video rendering and artifact caching.")
            if free_gb < 0.5:
                report.is_healthy = False

        # 4. Critical Python Libraries
        missing_libs = []
        for mod in ("numpy", "PIL", "cv2"):
            try:
                __import__(mod)
            except ImportError:
                missing_libs.append(mod)

        if missing_libs:
            report.is_healthy = False
            report.dependencies_intact = False
            report.issues.append(f"Missing core Python modules: {', '.join(missing_libs)}")
            report.recommendations.append(f"Run 'pip install {' '.join(missing_libs)}' in your environment.")

        return report
