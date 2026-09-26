import wave
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from .analyzer import AudioAnalyzer, AudioMetrics
from ..models.chunk import ChunkMetadata
from ..config import ValidationConfig

class AudioValidator:
    """Validates acoustic integrity of individual chunks and stitched section audio."""
    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig()
        self.analyzer = AudioAnalyzer()

    def validate_chunk(
        self,
        audio_source: Path | bytes,
        text: str,
        metrics: Optional[AudioMetrics] = None
    ) -> Tuple[bool, List[str], AudioMetrics]:
        """
        Validates an individual synthesized chunk.
        Returns: (is_valid, list_of_errors_or_warnings, metrics)
        """
        errors = []
        if metrics is None:
            metrics = self.analyzer.analyze(audio_source, text=text)

        # 1. Non-zero duration
        if metrics.duration <= 0:
            errors.append(f"Duration is non-positive: {metrics.duration}s")
        elif metrics.duration < self.config.min_duration_per_chunk_sec:
            errors.append(f"Duration {metrics.duration:.2f}s is below minimum {self.config.min_duration_per_chunk_sec}s")

        # 2. Clipping check
        if metrics.peak > self.config.max_peak_allowed:
            errors.append(f"Peak amplitude {metrics.peak:.3f} exceeds clipping threshold {self.config.max_peak_allowed}")

        # 3. Silence ratio check
        if metrics.silence_ratio > self.config.max_silence_ratio:
            errors.append(f"Excessive silence ratio {metrics.silence_ratio:.2f} > {self.config.max_silence_ratio}")

        # 4. Pacing / WPM bounds
        word_count = len([w for w in text.split() if w])
        if word_count > 3 and metrics.duration > 0:
            if metrics.estimated_wpm < self.config.min_wpm:
                errors.append(f"Pacing too slow: {metrics.estimated_wpm:.1f} WPM < min {self.config.min_wpm}")
            elif metrics.estimated_wpm > self.config.max_wpm:
                errors.append(f"Pacing too fast: {metrics.estimated_wpm:.1f} WPM > max {self.config.max_wpm}")

        is_valid = len(errors) == 0
        return is_valid, errors, metrics

    def validate_section(
        self,
        section_path: Path,
        expected_chunks: List[ChunkMetadata],
        expected_sample_rate: int = 24000
    ) -> Tuple[bool, List[str], AudioMetrics]:
        """
        Comprehensive validation of the final section.wav.
        Checks file existence, valid WAV format, duration, clipping, chunk continuity,
        and audio integrity.
        """
        errors = []
        section_path = Path(section_path)

        # 1. File existence
        if not section_path.exists():
            return False, [f"Section audio file does not exist: {section_path}"], AudioMetrics(0, 0, 0, 0, 0, 1, 0, 0)
        
        # 2. File size
        if section_path.stat().st_size < 1000:
            return False, ["Section audio file is abnormally small / corrupted"], AudioMetrics(0, 0, 0, 0, 0, 1, 0, 0)

        # 3. Load & analyze
        try:
            metrics = self.analyzer.analyze(section_path)
        except Exception as e:
            return False, [f"Failed to read WAV audio: {str(e)}"], AudioMetrics(0, 0, 0, 0, 0, 1, 0, 0)

        # 4. Sample rate & channels
        if metrics.sample_rate != expected_sample_rate:
            errors.append(f"Sample rate mismatch: {metrics.sample_rate} vs expected {expected_sample_rate}")
        if metrics.channels != 1:
            # We enforce mono for explainer voiceover
            errors.append(f"Channels mismatch: {metrics.channels} channels (expected mono 1)")

        # 5. Non-zero duration
        if metrics.duration <= 0:
            errors.append("Section duration is 0.0s")

        # 6. Clipping
        if metrics.peak > self.config.max_peak_allowed:
            errors.append(f"Section peak amplitude {metrics.peak:.3f} indicates clipping")

        # 7. Silence ratio
        if metrics.silence_ratio > 0.45:
            errors.append(f"Section has high silence ratio: {metrics.silence_ratio:.2f}")

        # 8. All chunks accounted for and ordered
        if expected_chunks:
            sum_chunk_dur = sum(c.duration for c in expected_chunks)
            if metrics.duration < sum_chunk_dur * 0.9:
                errors.append(f"Section duration ({metrics.duration:.2f}s) is significantly shorter than sum of chunks ({sum_chunk_dur:.2f}s)")
            
            # Check sequential ordering
            for i in range(len(expected_chunks) - 1):
                c_curr = expected_chunks[i]
                c_next = expected_chunks[i+1]
                if c_next.global_start < c_curr.global_end - 0.05:
                    errors.append(f"Chunk order / timing overlap between chunk {c_curr.id} and {c_next.id}")

        is_valid = len(errors) == 0
        return is_valid, errors, metrics
