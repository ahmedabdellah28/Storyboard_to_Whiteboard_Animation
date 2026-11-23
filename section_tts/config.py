import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent.parent

def load_env_file(env_path: Optional[Path] = None) -> Dict[str, str]:
    """Loads key=value pairs from .env via core.config.env_loader."""
    from core.config.env_loader import load_project_env
    return load_project_env()

# Auto load environment
load_env_file()

def get_gemini_api_keys() -> List[str]:
    """Retrieves all GEMINI_API_KEY entries via core.config.env_loader."""
    from core.config.env_loader import get_gemini_api_keys as _get_keys
    return _get_keys()

class TTSConfig(BaseModel):
    provider: str = "gemini"
    model: str = "gemini-3.1-flash-tts-preview"
    voice: str = "Fenrir"
    sample_rate: int = 24000
    temperature: float = 2.0

class VoiceProfileConfig(BaseModel):
    name: str = "Saudi Male Youth - Fast YouTube Explainer"
    voice_name: str = "Fenrir"
    gender: str = "male"
    dialect: str = "Saudi Arabic (Neutral / White)"
    target_wpm: float = 168.0
    system_directive: str = ""

class ChunkingConfig(BaseModel):
    max_words_per_chunk: int = 28
    min_words_per_chunk: int = 6
    respect_punctuation: bool = True
    respect_paragraphs: bool = True

class StitchingConfig(BaseModel):
    pause_between_chunks_ms: int = 80
    micro_crossfade_ms: int = 8

class LoudnessConfig(BaseModel):
    enabled: bool = True
    target_rms: float = 0.15
    max_peak: float = 0.95

class SpeedAdjustmentConfig(BaseModel):
    enabled: bool = False
    min: float = 0.98
    max: float = 1.08

class PostProcessingConfig(BaseModel):
    speed_adjustment: SpeedAdjustmentConfig = Field(default_factory=SpeedAdjustmentConfig)

class ValidationConfig(BaseModel):
    min_duration_per_chunk_sec: float = 0.8
    min_wpm: float = 110.0
    max_wpm: float = 230.0
    max_silence_ratio: float = 0.35
    max_peak_allowed: float = 1.0

class RetryConfig(BaseModel):
    max_retries: int = 3
    initial_delay_sec: float = 1.5
    backoff_multiplier: float = 2.0
    jitter: bool = True

class AppConfig(BaseModel):
    tts: TTSConfig = Field(default_factory=TTSConfig)
    voice_profile: VoiceProfileConfig = Field(default_factory=VoiceProfileConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    stitching: StitchingConfig = Field(default_factory=StitchingConfig)
    loudness: LoudnessConfig = Field(default_factory=LoudnessConfig)
    post_processing: PostProcessingConfig = Field(default_factory=PostProcessingConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)

def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Loads configuration from YAML file with fallback to defaults."""
    if config_path is None:
        config_path = Path(__file__).resolve().parent / "config.yaml"
    
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return AppConfig(**data)
    return AppConfig()
