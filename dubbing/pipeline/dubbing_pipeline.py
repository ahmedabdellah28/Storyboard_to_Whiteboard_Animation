"""
AI Audio Dubbing Pipeline
=========================
Core orchestrator for the standalone AI Audio Dubbing Engine.

Pipeline stages:
  1. Audio validation & preprocessing (FFmpeg)
  2. Faster-Whisper ASR transcription & language detection
  3. Context-aware translation (preserving segment IDs & timings)
  4. Segment-level TTS generation (with per-segment error isolation)
  5. Multi-level duration matching (Level 1-4 strategies)
  6. Final audio mixing with exact pause & silence preservation
"""
from __future__ import annotations

import json
import math
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from ..models.dubbing_models import (
    DubbingResult,
    DubbingSegment,
    DubbingConfig,
    TranscriptionResult,
    TranslatedSegment,
    SourceSegment,
    SourceAudioInfo,
    TimingInfo,
)
from ..asr.base import ASRProvider
from ..translation.base import TranslationProvider
from ..tts.base import TTSProvider
from ..audio.processor import AudioProcessor
from ..audio.segmenter import Segmenter
from ..audio.mixer import Mixer
from ..timing.duration_matcher import DurationMatcher


class DubbingPipeline:
    """
    Modular, provider-based audio dubbing pipeline.
    Completely decoupled from visual/video engines.
    """

    def __init__(
        self,
        asr_provider: Optional[ASRProvider] = None,
        translation_provider: Optional[TranslationProvider] = None,
        tts_provider: Optional[TTSProvider] = None,
        config: Optional[DubbingConfig] = None,
    ):
        self.config = config or DubbingConfig()

        # Initialize providers lazily or use passed instances
        self.asr_provider = asr_provider
        self.translation_provider = translation_provider
        self.tts_provider = tts_provider

        # Audio processors
        self.audio_processor = AudioProcessor(
            sample_rate=self.config.output_sample_rate,
            channels=self.config.output_channels,
        )
        self.segmenter = Segmenter()
        self.mixer = Mixer(self.config)
        self.duration_matcher = DurationMatcher(self.config.duration_matching)

        # Global or per-run progress callback
        self.progress_callback: Optional[Callable[[str, float], None]] = self.config.progress_callback

    def _get_asr(self) -> ASRProvider:
        if self.asr_provider is None:
            from ..asr.faster_whisper import FasterWhisperProvider
            self.asr_provider = FasterWhisperProvider(
                model_size=self.config.asr_model_size,
                compute_type=self.config.asr_compute_type,
                device=self.config.asr_device,
            )
        return self.asr_provider

    def _get_translation(self, checkpoint_file: Optional[str] = None) -> TranslationProvider:
        if self.translation_provider is None:
            from ..translation.provider import GeminiTranslationProvider
            self.translation_provider = GeminiTranslationProvider(
                checkpoint_file=checkpoint_file,
            )
        elif checkpoint_file and hasattr(self.translation_provider, "checkpoint_file"):
            self.translation_provider.checkpoint_file = checkpoint_file
        return self.translation_provider

    def _get_tts(self) -> TTSProvider:
        if self.tts_provider is None:
            from ..tts.provider import GeminiTTSProvider
            self.tts_provider = GeminiTTSProvider(
                model=self.config.tts_model,
                profile=self.config.tts_profile,
                director_note=self.config.tts_director_note,
            )
        return self.tts_provider

    def _update_progress(
        self,
        step: str,
        progress: float,
        callback: Optional[Callable[[str, float], None]] = None,
    ) -> None:
        """Report progress to active callback."""
        active_cb = callback or self.progress_callback
        if active_cb:
            try:
                active_cb(step, progress)
            except Exception as e:
                print(f"[Progress Callback Warning] {e}")

    # ── Main Entry Point ───────────────────────────────────────────────────────

    def dub(
        self,
        audio_path: str,
        target_language: str = "en",
        voice: Optional[str] = None,
        project_name: Optional[str] = None,
        output_base_dir: str = "dubbing",
        progress_callback: Optional[Callable[[str, float], None]] = None,
        force_rebuild: bool = False,
    ) -> DubbingResult:
        """
        Execute the complete audio dubbing pipeline.

        Args:
            audio_path: Path to original audio file (.wav, .mp3, .m4a, .flac, .ogg).
            target_language: Target language code or name (e.g. "en", "English", "fr").
            voice: Voice name (defaults to config.tts_voice, e.g. "Kore").
            project_name: Optional custom project folder name.
            output_base_dir: Base directory for projects (default: "dubbing").
            progress_callback: Optional callback(status_message: str, fraction: float).
            force_rebuild: If True, ignores cached intermediate files.

        Returns:
            DubbingResult containing paths to final audio, transcript, translation, and metadata.
        """
        start_time = time.time()
        voice = voice or self.config.tts_voice
        cb = progress_callback or self.progress_callback

        # 0. Validate input file
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Source audio file not found: {audio_path}")

        # 1. Project Directory Structure
        project_id, project_dir = self._create_project_structure(
            audio_path=audio_path,
            project_name=project_name,
            output_base_dir=output_base_dir,
        )

        # 2. Stage 1: Load and probe audio
        self._update_progress("[1/6] Loading audio", 0.05, cb)
        source_info, processed_audio = self._preprocess_source_audio(
            audio_path=audio_path,
            project_dir=project_dir,
        )

        # 3. Stage 2: Transcribe with Faster-Whisper
        self._update_progress("[2/6] Transcribing", 0.15, cb)
        transcription = self._transcribe_step(
            audio_path=processed_audio,
            project_dir=project_dir,
            force=force_rebuild,
        )

        # 4. Stage 3: Translate segments
        self._update_progress("[3/6] Translating", 0.35, cb)
        translations = self._translate_step(
            transcription=transcription,
            target_language=target_language,
            project_dir=project_dir,
            force=force_rebuild,
        )

        # 5. Stage 4: Generate TTS for segments
        self._update_progress("[4/6] Generating TTS", 0.50, cb)
        tts_segments = self._generate_tts_step(
            translations=translations,
            voice=voice,
            target_language=target_language,
            project_dir=project_dir,
            callback=cb,
            force=force_rebuild,
        )

        # 6. Stage 5: Duration matching
        self._update_progress("[5/6] Matching durations", 0.75, cb)
        matched_segments = self._match_durations_step(
            tts_segments=tts_segments,
            project_dir=project_dir,
            callback=cb,
            force=force_rebuild,
        )

        # 7. Stage 6: Rendering final audio with exact pause preservation
        self._update_progress("[6/6] Rendering final audio", 0.90, cb)
        final_audio_path = self._render_final_audio(
            segments=matched_segments,
            target_language=target_language,
            total_duration=source_info.duration,
            project_dir=project_dir,
        )

        # 8. Create metadata & wrap result
        self._update_progress("[Finalizing] Creating metadata", 0.96, cb)
        metadata_path = self._write_metadata(
            project_id=project_id,
            source_language=transcription.detected_language,
            target_language=target_language,
            source_info=source_info,
            segments=matched_segments,
            output_audio_path=final_audio_path,
            project_dir=project_dir,
            start_time=start_time,
        )

        self._update_progress("[Complete] Dubbing finished successfully!", 1.0, cb)

        return DubbingResult(
            project_id=project_id,
            source_language=transcription.detected_language,
            target_language=target_language,
            source_audio=source_info,
            output_audio=final_audio_path,
            transcript_path=os.path.join(project_dir, "transcription", "transcript.json"),
            translation_path=os.path.join(project_dir, "translation", f"{target_language}.json"),
            metadata_path=metadata_path,
            segments=matched_segments,
        )

    # ── Pipeline Stages ────────────────────────────────────────────────────────

    def _create_project_structure(
        self,
        audio_path: str,
        project_name: Optional[str],
        output_base_dir: str,
    ) -> tuple[str, str]:
        """Create standard folder layout under dubbing/<project_name>."""
        stem = Path(audio_path).stem
        if project_name:
            folder_name = project_name
            project_id = project_name
        else:
            short_id = uuid.uuid4().hex[:8]
            folder_name = f"{stem}_{short_id}"
            project_id = folder_name

        project_dir = os.path.abspath(os.path.join(output_base_dir, folder_name))
        for subdir in ["source", "transcription", "translation", "segments", "output"]:
            os.makedirs(os.path.join(project_dir, subdir), exist_ok=True)

        return project_id, project_dir

    def _preprocess_source_audio(
        self,
        audio_path: str,
        project_dir: str,
    ) -> tuple[SourceAudioInfo, str]:
        """Probe original audio and produce standardized ASR input WAV."""
        info_dict = self.audio_processor.get_info(audio_path)
        source_info = SourceAudioInfo(
            path=info_dict["path"],
            duration=info_dict["duration"],
            sample_rate=info_dict["sample_rate"],
            channels=info_dict["channels"],
            format=info_dict["format"],
        )

        # Copy original into project_dir/source/
        ext = os.path.splitext(audio_path)[1]
        copied_source = os.path.join(project_dir, "source", f"original{ext}")
        if not os.path.exists(copied_source):
            shutil.copy2(audio_path, copied_source)

        # Preprocess into 16kHz mono WAV for Whisper
        preprocessed_wav = os.path.join(project_dir, "source", "preprocessed_asr.wav")
        if not os.path.exists(preprocessed_wav):
            self.audio_processor.prepare_for_asr(copied_source, preprocessed_wav)

        return source_info, preprocessed_wav

    def _transcribe_step(
        self,
        audio_path: str,
        project_dir: str,
        force: bool = False,
    ) -> TranscriptionResult:
        """Execute or load cached ASR transcription."""
        transcription_dir = os.path.join(project_dir, "transcription")
        transcript_json = os.path.join(transcription_dir, "transcript.json")

        if not force and os.path.isfile(transcript_json):
            try:
                with open(transcript_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                segments = [
                    SourceSegment(
                        id=s["id"],
                        start=s["start"],
                        end=s["end"],
                        text=s["text"],
                    )
                    for s in data["segments"]
                ]
                print(f"  [Cache] Loaded existing transcription ({len(segments)} segments)")
                return TranscriptionResult(
                    segments=segments,
                    detected_language=data["detected_language"],
                    language_probability=data.get("language_probability", 1.0),
                    full_text=data.get("full_text", " ".join(s.text for s in segments)),
                )
            except Exception as e:
                print(f"  [Cache Warning] Could not parse cached transcript.json: {e}")

        # Run ASR
        asr = self._get_asr()
        result = asr.transcribe(audio_path)

        # Save artifacts
        self.segmenter.save_transcription_artifacts(result, transcription_dir)
        return result

    def _translate_step(
        self,
        transcription: TranscriptionResult,
        target_language: str,
        project_dir: str,
        force: bool = False,
    ) -> List[TranslatedSegment]:
        """Execute or load cached segment translation."""
        translation_dir = os.path.join(project_dir, "translation")
        trans_file = os.path.join(translation_dir, f"{target_language}.json")

        if not force and os.path.isfile(trans_file):
            try:
                with open(trans_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                id_to_seg = {s.id: s for s in transcription.segments}
                results = []
                for item in data:
                    seg_id = item["id"]
                    source_seg = id_to_seg.get(seg_id) or SourceSegment(
                        id=seg_id,
                        start=item["source"]["start"],
                        end=item["source"]["end"],
                        text=item["source"]["text"],
                    )
                    results.append(
                        TranslatedSegment(
                            id=seg_id,
                            source=source_seg,
                            language=item["translation"]["language"],
                            text=item["translation"]["text"],
                        )
                    )
                min_required = max(1, int(len(transcription.segments) * 0.95))
                if len(results) >= min_required:
                    print(f"  [Cache] Loaded existing translation ({len(results)}/{len(transcription.segments)} segments)")
                    return results
            except Exception as e:
                print(f"  [Cache Warning] Could not parse cached translation: {e}")

        # Run Translation (with checkpoint file for resumability)
        checkpoint_path = os.path.join(translation_dir, f"{target_language}_checkpoint.json")
        translator = self._get_translation(checkpoint_file=checkpoint_path)
        translations = translator.translate_segments(
            segments=transcription.segments,
            source_language=transcription.detected_language,
            target_language=target_language,
        )

        # Save translation JSON
        os.makedirs(translation_dir, exist_ok=True)
        payload = [t.to_dict() for t in translations]
        with open(trans_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return translations

    def _generate_tts_step(
        self,
        translations: List[TranslatedSegment],
        voice: str,
        target_language: str,
        project_dir: str,
        callback: Optional[Callable[[str, float], None]] = None,
        force: bool = False,
    ) -> List[DubbingSegment]:
        """Generate TTS audio for each translated segment with failure isolation."""
        segments_dir = os.path.join(project_dir, "segments")
        os.makedirs(segments_dir, exist_ok=True)
        tts_provider = self._get_tts()

        dubbing_segments: List[DubbingSegment] = []
        total = len(translations)

        for i, trans in enumerate(translations):
            frac = 0.50 + 0.22 * ((i + 1) / max(1, total))
            self._update_progress(f"[4/6] Generating TTS ({i+1}/{total})", frac, callback)

            tts_path = os.path.join(segments_dir, f"segment_{trans.id:03d}_tts.wav")

            # Smart cache: reuse existing TTS audio if present
            if not force and os.path.isfile(tts_path) and os.path.getsize(tts_path) > 100:
                duration = self.audio_processor.get_duration(tts_path)
                dubbing_segments.append(
                    DubbingSegment(
                        id=trans.id,
                        source=trans.source,
                        translated_text=trans.text,
                        target_language=target_language,
                        tts_audio_path=tts_path,
                        tts_duration=duration,
                    )
                )
                continue

            # Synthesize speech
            try:
                res = tts_provider.synthesize(
                    text=trans.text,
                    language=target_language,
                    voice=voice,
                    output_path=tts_path,
                )
                tts_dur = res.duration
            except Exception as e:
                print(f"  [TTS Segment Warning] Segment {trans.id} failed: {e}. Generating silent fallback.")
                # Produce silent fallback audio matching source duration
                self._generate_silent_wav(tts_path, duration=trans.source.duration)
                tts_dur = trans.source.duration

            dubbing_segments.append(
                DubbingSegment(
                    id=trans.id,
                    source=trans.source,
                    translated_text=trans.text,
                    target_language=target_language,
                    tts_audio_path=tts_path,
                    tts_duration=tts_dur,
                )
            )

        return dubbing_segments

    def _match_durations_step(
        self,
        tts_segments: List[DubbingSegment],
        project_dir: str,
        callback: Optional[Callable[[str, float], None]] = None,
        force: bool = False,
    ) -> List[DubbingSegment]:
        """Apply duration matching strategies (passthrough, stretch, compress, overflow)."""
        segments_dir = os.path.join(project_dir, "segments")
        matched_segments: List[DubbingSegment] = []
        total = len(tts_segments)

        for i, seg in enumerate(tts_segments):
            frac = 0.75 + 0.14 * ((i + 1) / max(1, total))
            self._update_progress(f"[5/6] Matching durations ({i+1}/{total})", frac, callback)

            final_path = os.path.join(segments_dir, f"segment_{seg.id:03d}.wav")

            if not force and os.path.isfile(final_path) and os.path.getsize(final_path) > 100:
                final_dur = self.audio_processor.get_duration(final_path)
                timing = TimingInfo(
                    original_duration=seg.source.duration,
                    generated_duration=seg.tts_duration,
                    final_duration=final_dur,
                    adjustment_factor=final_dur / max(0.01, seg.tts_duration),
                    strategy="cached",
                )
            else:
                timing = self.duration_matcher.match(
                    audio_path=seg.tts_audio_path,
                    target_duration=seg.source.duration,
                    output_path=final_path,
                )

            seg.final_audio_path = final_path
            seg.final_duration = timing.final_duration
            seg.timing = timing
            matched_segments.append(seg)

        return matched_segments

    def _render_final_audio(
        self,
        segments: List[DubbingSegment],
        target_language: str,
        total_duration: float,
        project_dir: str,
    ) -> str:
        """Mix all segments into the final dubbed audio file, preserving pauses."""
        output_file = os.path.join(project_dir, "output", f"dubbed_{target_language}.wav")
        self.mixer.mix_segments(
            segments=segments,
            output_path=output_file,
            total_duration=total_duration,
        )
        return output_file

    def _write_metadata(
        self,
        project_id: str,
        source_language: str,
        target_language: str,
        source_info: SourceAudioInfo,
        segments: List[DubbingSegment],
        output_audio_path: str,
        project_dir: str,
        start_time: float,
    ) -> str:
        """Persist metadata.json with comprehensive timing and statistics."""
        out_info = self.audio_processor.get_info(output_audio_path)

        metadata = {
            "project_id": project_id,
            "source_language": source_language,
            "target_language": target_language,
            "source_audio": source_info.to_dict(),
            "dubbed_audio": out_info,
            "processing_time_seconds": round(time.time() - start_time, 2),
            "stats": {
                "total_segments": len(segments),
                "original_speech_duration": round(sum(s.source.duration for s in segments), 3),
                "generated_tts_duration": round(sum(s.tts_duration for s in segments), 3),
                "final_speech_duration": round(sum(s.final_duration for s in segments), 3),
            },
            "segments": [seg.to_dict() for seg in segments],
            "config": self.config.to_dict(),
        }

        meta_path = os.path.join(project_dir, "metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return meta_path

    @staticmethod
    def _generate_silent_wav(output_path: str, duration: float, sample_rate: int = 48000) -> None:
        """Helper to create a silent WAV file."""
        import numpy as np
        import soundfile as sf
        samples = int(math.ceil(max(0.1, duration) * sample_rate))
        silence = np.zeros(samples, dtype=np.float32)
        sf.write(output_path, silence, sample_rate, subtype="PCM_16")