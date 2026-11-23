"""Unified environment variable and .env loader.

Replaces divergent .env loading implementations across the codebase.
Thread-safe, lazy singleton, filters placeholders, and discovers arbitrary key variations.
"""

from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional

from core.config.settings import PROJECT_ROOT

_PLACEHOLDER_VALUES = {
    "your_gemini_api_key_here",
    "your_api_key_here",
    "your_key_here",
    "none",
    "null",
    "placeholder",
    "",
}


class EnvLoader:
    """Singleton loader for .env configuration and API keys."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded = False
        self._env_vars: Dict[str, str] = {}
        self._gemini_keys: List[str] = []

    def _locate_env_file(self) -> Optional[Path]:
        custom_env = os.environ.get("ENV_FILE")
        if custom_env:
            custom_path = Path(custom_env).resolve()
            if custom_path.is_file():
                return custom_path

        candidates = [
            PROJECT_ROOT / ".env",
            Path.cwd() / ".env",
            Path(__file__).resolve().parent.parent.parent / ".env",
        ]

        for cand in candidates:
            if cand.is_file():
                return cand.resolve()

        return None

    def load(self, force_reload: bool = False) -> Dict[str, str]:
        with self._lock:
            if self._loaded and not force_reload:
                return dict(self._env_vars)

            env_path = self._locate_env_file()
            self._env_vars.clear()

            if env_path and env_path.is_file():
                try:
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#"):
                                continue
                            if "=" in line:
                                key, val = line.split("=", 1)
                                key = key.strip()
                                val = val.strip()
                                if (val.startswith('"') and val.endswith('"')) or (
                                    val.startswith("'") and val.endswith("'")
                                ):
                                    val = val[1:-1].strip()
                                self._env_vars[key] = val
                                # Populate os.environ if not present
                                if key not in os.environ:
                                    os.environ[key] = val
                except Exception as e:
                    print(f"⚠️ [EnvLoader] Error reading .env from {env_path}: {e}")

            # Collect Gemini keys from both parsed .env and os.environ
            discovered_keys: Dict[str, str] = {}  # key_name -> key_value

            all_vars = {**self._env_vars, **os.environ}
            for k, v in all_vars.items():
                if k.startswith("GEMINI_API_KEY"):
                    clean_val = v.strip() if v else ""
                    if clean_val and clean_val.lower() not in _PLACEHOLDER_VALUES:
                        discovered_keys[k] = clean_val

            # Sort keys: GEMINI_API_KEY first, then GEMINI_API_KEY2, 3, 4, ...
            def key_sort_order(name: str) -> int:
                if name == "GEMINI_API_KEY":
                    return 1
                match = re.search(r"(\d+)$", name)
                if match:
                    return int(match.group(1))
                return 999

            sorted_names = sorted(discovered_keys.keys(), key=key_sort_order)
            seen_values = set()
            self._gemini_keys = []
            for name in sorted_names:
                val = discovered_keys[name]
                if val not in seen_values:
                    seen_values.add(val)
                    self._gemini_keys.append(val)

            self._loaded = True
            return dict(self._env_vars)

    def get_gemini_api_keys(self) -> List[str]:
        if not self._loaded:
            self.load()
        return list(self._gemini_keys)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if not self._loaded:
            self.load()
        return os.environ.get(key, self._env_vars.get(key, default))


_GLOBAL_ENV_LOADER = EnvLoader()


def load_project_env(force_reload: bool = False) -> Dict[str, str]:
    return _GLOBAL_ENV_LOADER.load(force_reload=force_reload)


def get_gemini_api_keys() -> List[str]:
    return _GLOBAL_ENV_LOADER.get_gemini_api_keys()


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    return _GLOBAL_ENV_LOADER.get(key, default)
