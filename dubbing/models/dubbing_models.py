"""
Dubbing Data Models
===================
Dataclass definitions for the entire dubbing pipeline.
All intermediate and final results are represented here.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class SourceSegment:
    """A single segment from ASR transcription."""
    id: int
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "duration": self.duration,
        }


@dataclass
class TranslatedSegment:
    """A segment with both source and translated text."""
    id: int
    source: SourceSegment
    language: str
    text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source.to_dict(),
            "translation": {
                "language": self.language,
                "text": self.text,
            },
        }


@dataclass
class TimingInfo:
    """Duration-matching timing metadata for a segment."""
    original_duration: float
    generated_duration: float
    final_duration: float
    adjustment_factor: float
    strategy: str  # e.g. "passthrough", "stretch", "compress", "overflow"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_duration": self.original_duration,
            "generated_duration": self.generated_duration,
            "final_duration": self.final_duration,
            "adjustment_factor": round(self.adjustment_factor, 4),
            "strategy": self.strategy,
        }


@dataclass
class DubbingSegment:
    """Full per-segment result combining source, translation, TTS, and timing."""
    id: int
    source: SourceSegment
    translated_text: str
    target_language: str
    tts_audio_path: Optional[str] = None
    tts_duration: float = 0.0
    final_duration: float = 0.0
    final_audio_path: Optional[str] = None
    timing: Optional[TimingInfo] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "source": self.source.to_dict(),
            "target": {
                "language": self.target_language,
                "text": self.translated_text,
                "tts_duration": round(self.tts_duration, 4),
                "final_duration": round(self.final_duration, 4),
            },
        }
        if self.timing:
            d["timing"] = self.timing.to_dict()
        return d


@dataclass
class TranscriptionResult:
    """Full transcription result from ASR."""
    segments: List[SourceSegment]
    detected_language: str
    language_probability: float
    full_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected_language": self.detected_language,
            "language_probability": round(self.language_probability, 4),
            "full_text": self.full_text,
            "segments": [s.to_dict() for s in self.segments],
        }


@dataclass
class SourceAudioInfo:
    """Metadata about the source audio file."""
    path: str
    duration: float
    sample_rate: int
    channels: int
    format: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "duration": round(self.duration, 4),
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "format": self.format,
        }


@dataclass
class DubbingResult:
    """Final result returned by the dubbing pipeline."""
    project_id: str
    source_language: str
    target_language: str
    source_audio: SourceAudioInfo
    output_audio: str
    transcript_path: str
    translation_path: str
    metadata_path: str
    segments: List[DubbingSegment] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "source_audio": self.source_audio.to_dict(),
            "output_audio": self.output_audio,
            "transcript_path": self.transcript_path,
            "translation_path": self.translation_path,
            "metadata_path": self.metadata_path,
            "segments": [s.to_dict() for s in self.segments],
        }


@dataclass
class DurationMatchingConfig:
    """Configurable thresholds for duration matching."""
    enabled: bool = True
    max_speed: float = 1.15
    min_speed: float = 0.90
    max_duration_error: float = 0.20  # seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "max_speed": self.max_speed,
            "min_speed": self.min_speed,
            "max_duration_error": self.max_duration_error,
        }


@dataclass
class DubbingConfig:
    """Master configuration for the dubbing pipeline."""
    # ASR
    asr_model_size: str = "small"
    asr_compute_type: str = "int8"
    asr_device: str = "auto"  # "auto", "cpu", "cuda"

    # Translation
    translation_provider: str = "gemini"

    # TTS
    tts_provider: str = "gemini"
    tts_voice: str = "Fenrir"
    tts_profile: str = "YOUTH_CREATOR"
    tts_director_note: str = "DYNAMIC_WHITEBOARD_SWEETSPOT"
    tts_model: str = "gemini-3.1-flash-tts-preview"

    # Duration matching
    duration_matching: DurationMatchingConfig = field(default_factory=DurationMatchingConfig)

    # Audio output
    output_sample_rate: int = 48000
    output_channels: int = 2

    # Progress
    progress_callback: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asr": {
                "model_size": self.asr_model_size,
                "compute_type": self.asr_compute_type,
                "device": self.asr_device,
            },
            "translation": {
                "provider": self.translation_provider,
            },
            "tts": {
                "provider": self.tts_provider,
                "voice": self.tts_voice,
                "profile": self.tts_profile,
                "director_note": self.tts_director_note,
                "model": self.tts_model,
            },
            "duration_matching": self.duration_matching.to_dict(),
            "output": {
                "sample_rate": self.output_sample_rate,
                "channels": self.output_channels,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DubbingConfig:
        """Create DubbingConfig from nested or flat dictionary."""
        cfg = cls()
        if "asr" in data:
            asr = data["asr"]
            cfg.asr_model_size = asr.get("model_size", cfg.asr_model_size)
            cfg.asr_compute_type = asr.get("compute_type", cfg.asr_compute_type)
            cfg.asr_device = asr.get("device", cfg.asr_device)

        if "translation" in data:
            trans = data["translation"]
            cfg.translation_provider = trans.get("provider", cfg.translation_provider)

        if "tts" in data:
            tts = data["tts"]
            cfg.tts_provider = tts.get("provider", cfg.tts_provider)
            cfg.tts_voice = tts.get("voice", cfg.tts_voice)
            cfg.tts_profile = tts.get("profile", cfg.tts_profile)
            cfg.tts_director_note = tts.get("director_note", cfg.tts_director_note)
            cfg.tts_model = tts.get("model", cfg.tts_model)

        if "duration_matching" in data:
            dm = data["duration_matching"]
            cfg.duration_matching = DurationMatchingConfig(
                enabled=dm.get("enabled", True),
                max_speed=float(dm.get("max_speed", 1.15)),
                min_speed=float(dm.get("min_speed", 0.90)),
                max_duration_error=float(dm.get("max_duration_error", 0.20)),
            )

        if "output" in data or "audio" in data:
            out = data.get("output") or data.get("audio", {})
            cfg.output_sample_rate = int(out.get("sample_rate", cfg.output_sample_rate))
            cfg.output_channels = int(out.get("channels", cfg.output_channels))

        return cfg

    @classmethod
    def from_yaml(cls, path: str) -> DubbingConfig:
        """Load configuration from a YAML file."""
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)

