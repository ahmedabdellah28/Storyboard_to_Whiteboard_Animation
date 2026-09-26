import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent.parent

def load_env_file(env_path: Optional[Path] = None) -> Dict[str, str]:
    """Loads key=value pairs from .env into os.environ if not already present."""
    if env_path is None:
        env_path = ROOT_DIR / ".env"
    env_vars = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                k = key.strip()
                v = val.strip().strip("'\"")
                env_vars[k] = v
                if k not in os.environ:
                    os.environ[k] = v
    return env_vars

# Auto load environment
load_env_file()

def get_gemini_api_keys() -> List[str]:
    """Retrieves all GEMINI_API_KEY entries from environment."""
    keys = []
    # Primary key
    primary = os.environ.get("GEMINI_API_KEY", "").strip()
    if primary:
        keys.append(primary)
    # Check secondary keys GEMINI_API_KEY2, GEMINI_API_KEY3, etc.
    for i in range(2, 20):
        k = os.environ.get(f"GEMINI_API_KEY{i}", "").strip()
        if k and k not in keys:
            keys.append(k)
    return keys

class TTSConfig(BaseModel):
    provider: str = "gemini"
    model: str = "gemini-2.5-flash-preview-tts"
    voice: str = "Fenrir"
    sample_rate: int = 24000
    temperature: float = 1.0

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
