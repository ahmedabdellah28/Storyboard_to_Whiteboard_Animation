"""Packaging, Environment Health & Hardware Acceleration Diagnostics.

Provides diagnostic health checks, FFmpeg detection, hardware encoder ladder
evaluation (NVENC -> QSV -> AMF -> libx264 -> h264), and standalone deployment
verification for Whiteboard Studio.

Part of Phase 14 & 15: Migration Cleanup, Packaging & Diagnostics.
"""

from __future__ import annotations

import os
import shutil
import sys
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.config.settings import PROJECT_ROOT, CACHE_DIR, OUTPUT_DIR, SECTIONS_DIR


ENCODER_LADDER_DEFINITIONS = [
    ("h264_nvenc", "NVIDIA NVENC Hardware Encoder (Fastest / Low CPU)"),
    ("h264_qsv", "Intel QuickSync Video Hardware Encoder"),
    ("h264_amf", "AMD Advanced Media Framework Hardware Encoder"),
    ("libx264", "Standard x264 High-Quality Software Encoder"),
    ("h264", "Default PyAV/FFmpeg H.264 Encoder"),
]


@dataclass
class HardwareEncoderInfo:
    codec_name: str
    available: bool
    description: str
    error: Optional[str] = None


@dataclass
class EnvironmentHealthReport:
    python_version: str
    is_64bit: bool
    platform_name: str
    ffmpeg_available: bool
    ffmpeg_path: Optional[str]
    ffmpeg_version: Optional[str]
    dependencies: Dict[str, bool] = field(default_factory=dict)
    encoders: List[HardwareEncoderInfo] = field(default_factory=list)
    best_encoder: str = "h264"
    directories_ok: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        """Returns True if there are zero blocking errors and core dependencies are met."""
        return len(self.errors) == 0 and self.dependencies.get("numpy", False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "python_version": self.python_version,
            "is_64bit": self.is_64bit,
            "platform": self.platform_name,
            "ffmpeg": {
                "available": self.ffmpeg_available,
                "path": self.ffmpeg_path,
                "version": self.ffmpeg_version,
            },
            "dependencies": self.dependencies,
            "hardware_encoders": [
                {
                    "codec": e.codec_name,
                    "available": e.available,
                    "description": e.description,
                    "error": e.error,
                }
                for e in self.encoders
            ],
            "best_encoder": self.best_encoder,
            "directories_ok": self.directories_ok,
            "healthy": self.is_healthy,
            "warnings": self.warnings,
            "errors": self.errors,
        }

    def format_cli(self) -> str:
        lines = [
            "=" * 70,
            " WHITEBOARD STUDIO — ENVIRONMENT HEALTH & PACKAGING DIAGNOSTICS",
            "=" * 70,
            f"Python:       {self.python_version} ({'64-bit' if self.is_64bit else '32-bit'})",
            f"Platform:     {self.platform_name}",
            f"Status:       {'[OK] HEALTHY' if self.is_healthy else '[FAIL] ATTENTION NEEDED'}",
            "-" * 70,
            "FFmpeg Diagnostics:",
            f"  Available:  {'YES' if self.ffmpeg_available else 'NO (Falling back to PyAV / OpenCV)'}",
            f"  Binary:     {self.ffmpeg_path or 'Not in PATH or bin/'}",
            "-" * 70,
            "Hardware Encoder Ladder (NVENC -> QSV -> AMF -> libx264 -> h264):",
        ]
        for e in self.encoders:
            status = "[ACTIVE]" if e.codec_name == self.best_encoder and e.available else (
                "[SUPPORTED]" if e.available else "[NOT FOUND]"
            )
            lines.append(f"  {status:13} {e.codec_name:12} : {e.description}")
        lines.append(f"Selected Primary Codec: {self.best_encoder}")
        lines.append("-" * 70)
        lines.append("Dependency Matrix:")
        for dep, ok in self.dependencies.items():
            lines.append(f"  {dep:15} : {'INSTALLED' if ok else 'MISSING'}")
        lines.append("-" * 70)
        if self.warnings:
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  ! {w}")
        if self.errors:
            lines.append("Errors:")
            for err in self.errors:
                lines.append(f"  X {err}")
        lines.append("=" * 70)
        return "\n".join(lines)


class EnvironmentHealthChecker:
    """Performs deep environmental and hardware preflight verification."""

    @classmethod
    def check_ffmpeg(cls, search_dirs: Optional[List[Path]] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """Checks for FFmpeg binary in system PATH or local application directories."""
        # 1. System PATH
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            return True, str(Path(sys_ffmpeg).resolve()), "System PATH"

        # 2. Local search directories
        candidates = search_dirs or [
            PROJECT_ROOT / "bin" / "ffmpeg.exe",
            PROJECT_ROOT / "bin" / "ffmpeg",
            PROJECT_ROOT / "tools" / "ffmpeg.exe",
            PROJECT_ROOT / "tools" / "ffmpeg",
        ]
        for p in candidates:
            if p.exists() and os.access(str(p), os.X_OK | os.R_OK):
                return True, str(p.resolve()), "Local Bundle"

        return False, None, None

    @classmethod
    def check_encoder_ladder(cls, fps: int = 30) -> Tuple[List[HardwareEncoderInfo], str]:
        """Tests each codec in the canonical hardware ladder and selects the optimal one."""
        results: List[HardwareEncoderInfo] = []
        best_codec = "h264"
        found_best = False

        try:
            import av
            has_pyav = True
        except ImportError:
            has_pyav = False

        for codec_name, desc in ENCODER_LADDER_DEFINITIONS:
            if not has_pyav:
                # Without PyAV, fallback to standard cv2/openh264
                results.append(HardwareEncoderInfo(
                    codec_name=codec_name,
                    available=False,
                    description=desc,
                    error="PyAV not installed",
                ))
                continue

            try:
                test_c = av.open(os.devnull, mode="w", format="mp4")
                test_s = test_c.add_stream(codec_name, rate=fps)
                test_c.close()
                results.append(HardwareEncoderInfo(
                    codec_name=codec_name,
                    available=True,
                    description=desc,
                ))
                if not found_best:
                    best_codec = codec_name
                    found_best = True
            except Exception as e:
                results.append(HardwareEncoderInfo(
                    codec_name=codec_name,
                    available=False,
                    description=desc,
                    error=str(e),
                ))

        if not found_best and has_pyav:
            best_codec = "h264"
        elif not has_pyav:
            best_codec = "mp4v"

        return results, best_codec

    @classmethod
    def check_dependencies(cls) -> Dict[str, bool]:
        """Validates existence of core and UI workstation dependencies."""
        deps = [
            "numpy",
            "cv2",
            "scipy",
            "soundfile",
            "av",
            "PySide6",
            "pydantic",
            "pytest",
        ]
        res = {}
        for dep in deps:
            try:
                __import__(dep)
                res[dep] = True
            except ImportError:
                res[dep] = False
        return res

    @classmethod
    def check_directories(cls) -> Tuple[bool, List[str]]:
        """Ensures all essential storage and cache roots exist and are writable."""
        dirs = [OUTPUT_DIR, CACHE_DIR, SECTIONS_DIR]
        errors = []
        for d in dirs:
            try:
                d.mkdir(parents=True, exist_ok=True)
                test_file = d / ".write_test"
                test_file.write_text("ok", encoding="utf-8")
                test_file.unlink(missing_ok=True)
            except Exception as e:
                errors.append(f"Directory {d} is not writable: {e}")
        return len(errors) == 0, errors

    @classmethod
    def run_full_diagnostics(cls) -> EnvironmentHealthReport:
        """Executes full diagnostic suite and returns comprehensive health report."""
        ffmpeg_ok, ffmpeg_path, ffmpeg_src = cls.check_ffmpeg()
        encoders, best_codec = cls.check_encoder_ladder()
        deps = cls.check_dependencies()
        dirs_ok, dir_errors = cls.check_directories()

        warnings: List[str] = []
        errors: List[str] = []

        if not ffmpeg_ok:
            warnings.append("FFmpeg binary not detected in PATH or bin/. Video muxing will use internal PyAV stream writer.")

        if not deps.get("PySide6", False):
            warnings.append("PySide6 not installed; desktop UI is running in mock/shim mode.")

        if not deps.get("av", False):
            warnings.append("PyAV not installed; video encoding falls back to OpenCV VideoWriter.")

        if not dirs_ok:
            errors.extend(dir_errors)

        return EnvironmentHealthReport(
            python_version=platform.python_version(),
            is_64bit=sys.maxsize > 2**32,
            platform_name=f"{platform.system()} {platform.release()} ({platform.machine()})",
            ffmpeg_available=ffmpeg_ok,
            ffmpeg_path=ffmpeg_path,
            ffmpeg_version=ffmpeg_src,
            dependencies=deps,
            encoders=encoders,
            best_encoder=best_codec,
            directories_ok=dirs_ok,
            warnings=warnings,
            errors=errors,
        )

    @classmethod
    def ensure_render_engine_assets(cls) -> Path:
        """Ensures drawing-hand and hand-mask assets are copied into core/render_engine/data/images."""
        target_dir = PROJECT_ROOT / "core" / "render_engine" / "data" / "images"
        target_dir.mkdir(parents=True, exist_ok=True)

        hand_file = target_dir / "drawing-hand.png"
        mask_file = target_dir / "hand-mask.png"

        legacy_hand = PROJECT_ROOT / "kivy" / "data" / "images" / "drawing-hand.png"
        legacy_mask = PROJECT_ROOT / "kivy" / "data" / "images" / "hand-mask.png"

        if not hand_file.exists() and legacy_hand.exists():
            shutil.copy2(str(legacy_hand), str(hand_file))
        if not mask_file.exists() and legacy_mask.exists():
            shutil.copy2(str(legacy_mask), str(mask_file))

        return target_dir

