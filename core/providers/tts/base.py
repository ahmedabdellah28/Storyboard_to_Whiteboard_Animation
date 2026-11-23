"""Abstract base interface for Text-to-Speech providers."""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Any, Dict, Optional, Union

PathLike = Union[str, Path]


class BaseTTSProvider(abc.ABC):
    """Abstract interface defining required TTS operations."""

    @abc.abstractmethod
    def synthesize(
        self,
        text: str,
        voice_name: Optional[str] = None,
        speed_factor: float = 1.0,
        options: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Synthesize text and return valid WAV bytes."""
        raise NotImplementedError

    @abc.abstractmethod
    def synthesize_to_file(
        self,
        text: str,
        output_path: PathLike,
        voice_name: Optional[str] = None,
        speed_factor: float = 1.0,
        options: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Synthesize text and save directly to a WAV file."""
        raise NotImplementedError
