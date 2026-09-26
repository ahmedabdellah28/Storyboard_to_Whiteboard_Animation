import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from faster_whisper import WhisperModel
from ..timeline.models import WhisperOutput, WhisperSegment, WhisperWord

def compute_file_sha256(filepath: Path) -> str:
    """Computes SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

class FasterWhisperEngine:
    """Production Faster-Whisper wrapper with auto hardware detection and SHA256 caching."""
    def __init__(
        self,
        model_size: str = "small",
        language: str = "ar",
        device: str = "auto",
        compute_type: str = "auto",
        vad_filter: bool = True
    ):
        self.model_size = model_size
        self.language = language
        self.vad_filter = vad_filter
        self.device, self.compute_type = self._resolve_device(device, compute_type)
        self._model: Optional[WhisperModel] = None

    def _resolve_device(self, device: str, compute_type: str) -> Tuple[str, str]:
        """Resolves optimal device and compute_type with safe CPU fallback."""
        if device == "cpu":
            c_type = "int8" if compute_type in ("auto", "int8") else compute_type
            return "cpu", c_type
        
        # Test CUDA availability
        try:
            import ctranslate2
            cuda_supported = "cuda" in ctranslate2.get_supported_compute_types("cuda")
        except Exception:
            cuda_supported = False

        if cuda_supported and device in ("auto", "cuda"):
            c_type = "float16" if compute_type == "auto" else compute_type
            return "cuda", c_type
        else:
            c_type = "int8" if compute_type == "auto" else compute_type
            return "cpu", c_type

    def get_model(self) -> WhisperModel:
        """Lazily initializes the WhisperModel."""
        if self._model is None:
            try:
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
            except Exception as e:
                # If CUDA failed (e.g. cublas missing on Windows), gracefully fallback to CPU
                if self.device == "cuda":
                    print(f"⚠️ CUDA initialization failed ({e}), falling back to CPU with int8.")
                    self.device = "cpu"
                    self.compute_type = "int8"
                    self._model = WhisperModel(
                        self.model_size,
                        device="cpu",
                        compute_type="int8"
                    )
                else:
                    raise e
        return self._model

    def transcribe(
        self,
        audio_path: Path | str,
        cache_file: Optional[Path] = None,
        force: bool = False
    ) -> WhisperOutput:
        """
        Transcribes audio with word-level timestamps.
        Reuses cached whisper.json if available and audio hash matches.
        """
        audio_path = Path(audio_path).resolve()
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Check Cache
        if not force and cache_file and cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return WhisperOutput.model_validate(data)
            except Exception:
                pass  # Recompute if cache is corrupted

        model = self.get_model()
        segments_gen, info = model.transcribe(
            str(audio_path),
            language=self.language,
            word_timestamps=True,
            vad_filter=self.vad_filter
        )

        segments_list: List[WhisperSegment] = []
        for s_idx, seg in enumerate(segments_gen):
            words_list: List[WhisperWord] = []
            if seg.words:
                for w in seg.words:
                    clean_w = w.word.strip()
                    if clean_w:
                        words_list.append(WhisperWord(
                            word=clean_w,
                            start=round(float(w.start), 3),
                            end=round(float(w.end), 3),
                            probability=round(float(w.probability), 3)
                        ))

            segments_list.append(WhisperSegment(
                id=s_idx,
                start=round(float(seg.start), 3),
                end=round(float(seg.end), 3),
                text=seg.text.strip(),
                words=words_list
            ))

        output = WhisperOutput(
            audio_path=str(audio_path),
            duration=round(float(info.duration), 3) if info else 0.0,
            language=self.language,
            segments=segments_list
        )

        # Save Raw Audio Evidence
        if cache_file:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(output.model_dump_json(indent=2))

        return output
