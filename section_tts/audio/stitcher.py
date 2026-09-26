import wave
from pathlib import Path
from typing import List, Tuple, Dict
import numpy as np
from .analyzer import AudioAnalyzer
from ..utils.logging import log

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False

class AudioStitcher:
    """Seamlessly stitches audio chunks into a unified section audio file."""
    def __init__(
        self,
        pause_between_chunks_ms: int = 80,
        micro_crossfade_ms: int = 8,
        expected_sample_rate: int = 24000
    ):
        self.pause_ms = pause_between_chunks_ms
        self.crossfade_ms = micro_crossfade_ms
        self.expected_sample_rate = expected_sample_rate
        self.analyzer = AudioAnalyzer()

    def stitch_chunks(
        self,
        chunk_files: List[Path],
        output_path: Path
    ) -> Tuple[float, List[Dict[str, float]]]:
        """
        Stitches a list of chunk WAV files into a single continuous section.wav.
        Returns:
            total_duration: float in seconds
            timings: List of dicts with {"global_start": float, "global_end": float, "duration": float}
        """
        if not chunk_files:
            raise ValueError("No chunk files provided for stitching.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        loaded_chunks = []
        sample_rate = self.expected_sample_rate

        for cf in chunk_files:
            data, sr = self.analyzer.load_audio_array(cf)
            if sr != sample_rate:
                log.warn(f"Chunk {cf.name} sample rate {sr} differs from expected {sample_rate}.")
            if data.ndim > 1:
                data = np.mean(data, axis=1)  # Mono projection
            loaded_chunks.append(data.astype(np.float32))
            sample_rate = sr

        # Micro-pause and micro-crossfade sample counts
        pause_samples = int(sample_rate * (self.pause_ms / 1000.0))
        crossfade_samples = int(sample_rate * (self.crossfade_ms / 1000.0))

        stitched_signal: List[np.ndarray] = []
        timings: List[Dict[str, float]] = []
        current_sample_idx = 0

        for idx, chunk_data in enumerate(loaded_chunks):
            chunk_len = len(chunk_data)
            chunk_dur = chunk_len / float(sample_rate)

            # Apply micro-fade in/out on the chunk boundaries to prevent clicks
            cf_len = min(crossfade_samples, chunk_len // 4)
            processed_chunk = chunk_data.copy()
            if cf_len > 0:
                fade_in = np.linspace(0.0, 1.0, cf_len, dtype=np.float32)
                fade_out = np.linspace(1.0, 0.0, cf_len, dtype=np.float32)
                processed_chunk[:cf_len] *= fade_in
                processed_chunk[-cf_len:] *= fade_out

            start_sec = current_sample_idx / float(sample_rate)
            end_sec = (current_sample_idx + chunk_len) / float(sample_rate)
            timings.append({
                "global_start": round(start_sec, 3),
                "global_end": round(end_sec, 3),
                "duration": round(chunk_dur, 3)
            })

            stitched_signal.append(processed_chunk)
            current_sample_idx += chunk_len

            # Insert micro-pause between chunks (not after the final chunk)
            if idx < len(loaded_chunks) - 1 and pause_samples > 0:
                silence = np.zeros(pause_samples, dtype=np.float32)
                stitched_signal.append(silence)
                current_sample_idx += pause_samples

        final_signal = np.concatenate(stitched_signal)
        total_duration = len(final_signal) / float(sample_rate)

        # Write output file
        if HAS_SOUNDFILE:
            sf.write(str(output_path), final_signal, sample_rate, subtype="PCM_16")
        else:
            int16_data = (np.clip(final_signal, -1.0, 1.0) * 32767.0).astype(np.int16)
            with wave.open(str(output_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(int16_data.tobytes())

        return round(total_duration, 3), timings
