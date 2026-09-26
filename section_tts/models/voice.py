from dataclasses import dataclass, field
from typing import Optional

@dataclass
class VoiceProfile:
    """Central voice identity profile. Configurable and immutable across chunks."""
    name: str = "Saudi Male Youth - Fast YouTube Explainer"
    voice_name: str = "Fenrir"
    gender: str = "male"
    dialect: str = "Saudi Arabic (Neutral / White)"
    target_wpm: float = 168.0
    system_directive: str = (
        "VOICE PERFORMANCE PROFILE:\n"
        "Young Saudi male narrator speaking in neutral, widely understandable Saudi Arabic.\n"
        "Fast-paced, energetic and highly engaging YouTube documentary/explainer delivery.\n"
        "Maintain high but controlled energy throughout the entire section.\n"
        "Speak quickly while keeping every word clearly understandable.\n"
        "Use natural pitch variation and subtle emphasis on important facts, discoveries, contrasts and surprising information.\n"
        "Maintain a continuous forward-moving rhythm.\n"
        "Use short natural pauses between ideas.\n"
        "Use slightly longer pauses only when a major idea changes or emphasis is naturally required.\n"
        "Avoid slow dramatic narration.\n"
        "Avoid theatrical acting.\n"
        "Avoid exaggerated emotions.\n"
        "Avoid sleepy or relaxed delivery.\n"
        "Do not rush pronunciation.\n"
        "Do not sacrifice clarity for speed.\n"
        "Maintain the same voice identity, dialect, energy, pacing philosophy and vocal character across every TTS chunk belonging to the same section."
    )

@dataclass
class PerformanceCue:
    """Dynamic performance cue assigned to a specific chunk by PerformancePlanner."""
    segment_type: str = "FACT"  # HOOK, FACT, SURPRISE, TRANSITION, CLIMAX, OUTRO
    energy: str = "high"        # high, medium_high, peak
    pace: str = "fast"          # fast, continuous, slightly_paced
    curiosity: str = "normal"   # high, normal
    emphasis: str = "subtle"    # subtle, strong
    pause_before_ms: int = 0
    pause_after_ms: int = 80
    instruction: str = ""
