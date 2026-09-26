"""
Speech Beat Model (Level 1: Speech Rhythm)
Represents a coherent thought or spoken unit from audio/subtitles with density and rhythm metrics.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import re


@dataclass
class SpeechBeat:
    id: str
    start: float
    end: float
    text: str
    audio_chunk_id: Optional[str] = None
    pause_after: float = 0.0
    speech_density: float = 0.0          # Characters per second (CPS)
    words_per_sec: float = 0.0           # Words per second (WPS)
    landmarks: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        self.start = float(round(self.start, 3))
        self.end = float(round(max(self.start + 0.05, self.end), 3))
        self.text = self.text.strip()
        dur = self.duration
        words = re.findall(r'[\w%]+', self.text)
        num_words = max(1, len(words))
        num_chars = max(1, len(self.text.replace(" ", "")))
        
        if self.speech_density <= 0.0:
            self.speech_density = round(num_chars / max(0.1, dur), 2)
        if self.words_per_sec <= 0.0:
            self.words_per_sec = round(num_words / max(0.1, dur), 2)

    @property
    def duration(self) -> float:
        return max(0.05, round(self.end - self.start, 3))

    @property
    def word_count(self) -> int:
        return len(re.findall(r'[\w%]+', self.text))

    def is_rapid_speech(self, threshold_cps: float = 18.0) -> bool:
        """Returns True if speech pace is unusually fast, demanding streamlined visual detail."""
        return self.speech_density >= threshold_cps

    def is_slow_speech(self, threshold_cps: float = 10.0) -> bool:
        """Returns True if speech pace is slow and relaxed, allowing elaborate drawing flourishes."""
        return self.speech_density <= threshold_cps

    def is_suspiciously_short(
        self,
        min_normal_duration: float = 0.60,
        max_cps: float = 20.0
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Detects if a subtitle/speech segment is unrealistically short for its content,
        which would otherwise cause extreme speed distortion in visual animation.
        Returns (is_suspicious, diagnostic_info).
        """
        dur = self.duration
        is_suspicious = (dur < min_normal_duration and self.word_count >= 3) or (self.speech_density > max_cps)
        recommended_dur = round(max(0.60, self.word_count * 0.28), 2)
        info = {
            "duration": dur,
            "word_count": self.word_count,
            "speech_density": self.speech_density,
            "is_suspicious": is_suspicious,
            "recommended_min_duration": recommended_dur,
            "reason": "Duration too compressed for word count (potential SRT alignment anomaly)" if is_suspicious else "Normal"
        }
        return is_suspicious, info
