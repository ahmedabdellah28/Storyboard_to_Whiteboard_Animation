"""Global settings and path configuration for the production platform."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _detect_project_root() -> Path:
    """Dynamically determine the project root directory.

    Order of priority:
    1. PRODUCTION_PROJECT_ROOT environment variable
    2. Traverse up from this file until .env or .git is found
    3. Fallback to 3 levels up from this file (core/config/settings.py -> root)
    """
    env_root = os.environ.get("PRODUCTION_PROJECT_ROOT")
    if env_root:
        candidate = Path(env_root).resolve()
        if candidate.exists():
            return candidate

    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists() or (parent / ".env").exists():
            return parent

    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT: Path = _detect_project_root()

# Standard project directory locations
OUTPUT_DIR: Path = PROJECT_ROOT / "output_animations"
PROJECT_CONTENT_DIR: Path = PROJECT_ROOT / "project_content"
SECTIONS_DIR: Path = PROJECT_ROOT / "sections"
AUDIO_CHUNKS_DIR: Path = PROJECT_ROOT / "audio_chunks"
VOICE_STUDIO_DIR: Path = PROJECT_ROOT / "voice_studio"
DUBBING_DIR: Path = PROJECT_ROOT / "dubbing"
PRE_RENDER_DIR: Path = PROJECT_ROOT / "pre_render_director"
LOGS_DIR: Path = PROJECT_ROOT / "logs"
CACHE_DIR: Path = PROJECT_ROOT / ".cache"

# Audio constants
DEFAULT_SAMPLE_RATE: int = 24000
DEFAULT_BITS_PER_SAMPLE: int = 16
DEFAULT_CHANNELS: int = 1
DEFAULT_SILENCE_PADDING_MS: int = 80

# Gemini model defaults
DEFAULT_TTS_MODEL: str = "gemini-3.1-flash-tts-preview"
FALLBACK_TTS_MODEL: str = "gemini-3.1-flash-tts-preview"
DEFAULT_CHAT_MODEL: str = "gemini-2.5-flash"
FALLBACK_CHAT_MODEL: str = "gemini-3.5-flash"
DEFAULT_VOICE_NAME: str = "Puck"

# Rate limit defaults
DEFAULT_API_RPM_LIMIT: int = 15  # requests per minute per key
DEFAULT_COOLDOWN_SECONDS: int = 50

# Shared Studio Typography Library & EffectCraft Integration
ASSETS_DIR: Path = PROJECT_ROOT / "assets"
CONFIG_DIR: Path = PROJECT_ROOT / "config"
TYPOGRAPHY_ROOT: Path = ASSETS_DIR / "typography"
TYPOGRAPHY_FONTS_DIR: Path = TYPOGRAPHY_ROOT / "fonts"
TYPOGRAPHY_REGISTRY_PATH: Path = TYPOGRAPHY_ROOT / "font_registry.json"
TYPOGRAPHY_DOWNLOAD_MANIFEST_PATH: Path = TYPOGRAPHY_ROOT / "font_registry_download.json"
TYPOGRAPHY_SETTINGS_PATH: Path = CONFIG_DIR / "typography_settings.json"


def get_effectcraft_font_dirs() -> str:
    """Return `;`/`:`-joined studio font directories for `EFFECTCRAFT_FONT_DIRS`."""
    import json

    dirs: list[Path] = []
    if TYPOGRAPHY_SETTINGS_PATH.is_file():
        try:
            cfg = json.loads(TYPOGRAPHY_SETTINGS_PATH.read_text(encoding="utf-8"))
            for rel in cfg.get("effectcraft_font_dirs", []):
                p = Path(rel)
                if not p.is_absolute():
                    p = PROJECT_ROOT / p
                if p.is_dir():
                    dirs.append(p.resolve())
        except Exception:
            pass
    if not dirs and TYPOGRAPHY_FONTS_DIR.is_dir():
        dirs.append(TYPOGRAPHY_FONTS_DIR.resolve())
    return os.pathsep.join(str(d) for d in dirs)


def get_effectcraft_subprocess_env(base_env: Optional[dict[str, str]] = None) -> dict[str, str]:
    """Return a subprocess environment dictionary with `EFFECTCRAFT_FONT_DIRS` bound."""
    env = dict(base_env) if base_env is not None else os.environ.copy()
    studio_dirs = get_effectcraft_font_dirs()
    if studio_dirs:
        existing = env.get("EFFECTCRAFT_FONT_DIRS", "").strip()
        if existing:
            parts = [p for p in existing.split(os.pathsep) if p]
            for d in studio_dirs.split(os.pathsep):
                if d and d not in parts:
                    parts.append(d)
            env["EFFECTCRAFT_FONT_DIRS"] = os.pathsep.join(parts)
        else:
            env["EFFECTCRAFT_FONT_DIRS"] = studio_dirs
    return env
