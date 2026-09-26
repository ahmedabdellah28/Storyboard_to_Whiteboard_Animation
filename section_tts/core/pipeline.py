import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..config import AppConfig, load_config
from ..models.section import SectionScript
from ..models.voice import VoiceProfile, PerformanceCue
from ..models.chunk import ChunkContext, ChunkMetadata
from ..models.metadata import SectionMetadata
from ..providers.base import TTSProvider
from ..providers.gemini import GeminiTTSProvider
from ..audio.analyzer import AudioAnalyzer
from ..audio.normalizer import LoudnessNormalizer
from ..audio.stitcher import AudioStitcher
from ..audio.validator import AudioValidator
from .semantic_chunker import SemanticChunker
from .performance_planner import PerformancePlanner
from .consistency_manager import ConsistencyManager
from .cache_manager import CacheManager
from ..utils.hashing import compute_section_hash, compute_chunk_hash
from ..utils.logging import log

class SectionTTSPipeline:
    """Master production pipeline transforming section script into validated section.wav & metadata."""
    def __init__(
        self,
        config: Optional[AppConfig] = None,
        provider: Optional[TTSProvider] = None,
        force_regenerate: bool = False,
        debug_mode: bool = False
    ):
        self.config = config or load_config()
        self.force_regenerate = force_regenerate
        self.debug_mode = debug_mode

        # Initialize voice profile from config
        self.voice_profile = VoiceProfile(
            name=self.config.voice_profile.name,
            voice_name=self.config.tts.voice,
            gender=self.config.voice_profile.gender,
            dialect=self.config.voice_profile.dialect,
            target_wpm=self.config.voice_profile.target_wpm,
            system_directive=self.config.voice_profile.system_directive
        )

        # Initialize components
        self.provider = provider or GeminiTTSProvider(
            model=self.config.tts.model,
            voice_name=self.config.tts.voice,
            sample_rate=self.config.tts.sample_rate,
            max_retries=self.config.retry.max_retries
        )

        self.chunker = SemanticChunker(self.config.chunking)
        self.planner = PerformancePlanner()
        self.analyzer = AudioAnalyzer()
        self.normalizer = LoudnessNormalizer(
            target_rms=self.config.loudness.target_rms,
            max_peak=self.config.loudness.max_peak
        )
        self.stitcher = AudioStitcher(
            pause_between_chunks_ms=self.config.stitching.pause_between_chunks_ms,
            micro_crossfade_ms=self.config.stitching.micro_crossfade_ms,
            expected_sample_rate=self.config.tts.sample_rate
        )
        self.validator = AudioValidator(self.config.validation)
        self.consistency = ConsistencyManager()
        self.cache_mgr = CacheManager(force_regenerate=force_regenerate)

    def process_section(
        self,
        script_path: Path | str,
        output_dir: Path | str,
        section_id: Optional[str] = None
    ) -> SectionMetadata:
        """Processes an independent script section into production section.wav + metadata.json."""
        script_path = Path(script_path).resolve()
        output_dir = Path(output_dir).resolve()
        chunks_dir = output_dir / "chunks"
        output_dir.mkdir(parents=True, exist_ok=True)
        chunks_dir.mkdir(parents=True, exist_ok=True)

        # 1. Load section script
        script = SectionScript.from_file(script_path, section_id=section_id or "")
        log.section(f"Loading section {script.section_id} ({script_path.name})")
        log.script(f"{script.word_count} words")

        # 2. Compute Section Hash & Check Cache
        settings_dict = {
            "max_words": self.config.chunking.max_words_per_chunk,
            "sample_rate": self.config.tts.sample_rate,
            "pause_ms": self.config.stitching.pause_between_chunks_ms
        }
        sec_hash = compute_section_hash(
            section_text=script.raw_text,
            voice_profile_dict=self.voice_profile.__dict__,
            model=self.config.tts.model,
            voice=self.config.tts.voice,
            settings=settings_dict
        )

        cached_meta = self.cache_mgr.is_section_cached(output_dir, sec_hash)
        if cached_meta:
            log.output(f"Cached audio retained: {output_dir / 'section.wav'}")
            return cached_meta

        # 3. Semantic Chunking
        raw_chunks = self.chunker.split_script(script.raw_text)
        log.chunker(f"Created {len(raw_chunks)} semantic chunks")

        # 4. Performance Planning
        performance_cues = self.planner.plan(raw_chunks)

        # 5. Synthesize / Validate Chunks
        chunk_files: List[Path] = []
        chunk_records: List[ChunkMetadata] = []
        debug_chunks: List[Dict[str, Any]] = []

        for idx, chunk_text in enumerate(raw_chunks):
            chunk_file = chunks_dir / f"{idx:03d}.wav"
            cue = performance_cues[idx]
            
            # Context for intonation continuity
            prev_text = raw_chunks[idx - 1] if idx > 0 else None
            next_text = raw_chunks[idx + 1] if idx < len(raw_chunks) - 1 else None
            ctx = ChunkContext(previous_text=prev_text, current_text=chunk_text, next_text=next_text)

            chunk_hash = compute_chunk_hash(
                chunk_text=chunk_text,
                model=self.config.tts.model,
                voice=self.config.tts.voice,
                performance_dict=cue.__dict__
            )

            # Check chunk-level cache
            is_chunk_cached = self.cache_mgr.is_chunk_cached(chunk_file, chunk_hash)
            metrics = None

            if is_chunk_cached:
                metrics = self.analyzer.analyze(chunk_file, text=chunk_text)
                log.cache(f"Chunk {idx + 1}/{len(raw_chunks)} cached: {metrics.duration:.2f}s")
            else:
                log.tts(f"Generating chunk {idx + 1}/{len(raw_chunks)} ({len(chunk_text.split())} words, {cue.segment_type})")
                
                # Retry generation loop with chunk validation
                success = False
                attempts = 0
                max_attempts = self.config.retry.max_retries

                while not success and attempts < max_attempts:
                    attempts += 1
                    try:
                        audio_res = self.provider.generate(
                            text=chunk_text,
                            voice_profile=self.voice_profile,
                            performance=cue,
                            context=ctx
                        )
                        # Save temporary chunk audio
                        with open(chunk_file, "wb") as f:
                            f.write(audio_res.audio_bytes)

                        # Analyze and validate
                        metrics = self.analyzer.analyze(chunk_file, text=chunk_text)
                        is_valid, validation_errors, metrics = self.validator.validate_chunk(
                            chunk_file, text=chunk_text, metrics=metrics
                        )

                        if is_valid:
                            success = True
                            log.tts(f"Chunk {idx + 1} completed: {metrics.duration:.2f}s")
                            log.analyzer(f"Chunk {idx + 1} WPM: {metrics.estimated_wpm:.1f} (RMS: {metrics.rms:.3f})")
                            log.validator(f"Chunk {idx + 1}: PASS")
                            time.sleep(1.0)
                        else:
                            log.warn(f"Chunk {idx + 1} validation issues on attempt {attempts}: {validation_errors}")
                            if attempts >= max_attempts:
                                # Accept with warning if retry limit reached
                                log.warn(f"Proceeding with chunk {idx + 1} despite validation warnings after {attempts} attempts.")
                                success = True
                    except Exception as e:
                        log.error(f"Error synthesizing chunk {idx + 1}: {str(e)}")
                        if attempts >= max_attempts:
                            raise e
                        time.sleep(1.0)

            # Loudness normalization on chunk
            if self.config.loudness.enabled and chunk_file.exists():
                self.normalizer.normalize_file(chunk_file, chunk_file)
                # Re-analyze normalized chunk
                metrics = self.analyzer.analyze(chunk_file, text=chunk_text)

            chunk_files.append(chunk_file)
            
            chunk_rec = ChunkMetadata(
                id=idx,
                text=chunk_text,
                file=f"chunks/{chunk_file.name}",
                duration=metrics.duration,
                sample_rate=metrics.sample_rate,
                estimated_wpm=metrics.estimated_wpm,
                rms=metrics.rms,
                peak=metrics.peak,
                silence_ratio=metrics.silence_ratio,
                global_start=0.0,  # Will be populated by stitcher
                global_end=metrics.duration,
                performance_type=cue.segment_type,
                generation_hash=chunk_hash
            )
            chunk_records.append(chunk_rec)

            if self.debug_mode:
                debug_chunks.append({
                    "id": idx,
                    "text": chunk_text,
                    "cue": cue.__dict__,
                    "metrics": metrics.__dict__
                })

        # 6. Audio Stitching
        log.stitch(f"Combining {len(chunk_files)} chunks into section.wav")
        section_wav = output_dir / "section.wav"
        total_duration, timings = self.stitcher.stitch_chunks(chunk_files, section_wav)

        # Update global start / end timings
        for i, t in enumerate(timings):
            chunk_records[i].global_start = t["global_start"]
            chunk_records[i].global_end = t["global_end"]

        # 7. Final Section Validation
        is_sec_valid, sec_errors, sec_metrics = self.validator.validate_section(
            section_wav,
            expected_chunks=chunk_records,
            expected_sample_rate=self.config.tts.sample_rate
        )
        if not is_sec_valid:
            log.warn(f"Section validation warnings: {sec_errors}")
        else:
            log.validator("Final section: PASS")

        # 8. Consistency Evaluation
        is_consistent, consistency_issues, consistency_summary = self.consistency.evaluate_consistency(chunk_records)

        # 9. Compute Overall Statistics
        total_words = script.word_count
        avg_wpm = (total_words / (total_duration / 60.0)) if total_duration > 0 else 0.0

        metadata = SectionMetadata(
            section_id=script.section_id,
            script_file=script_path.name,
            text=script.clean_text,
            model=self.config.tts.model,
            voice=self.config.tts.voice,
            duration=round(total_duration, 2),
            sample_rate=self.config.tts.sample_rate,
            total_words=total_words,
            average_wpm=round(avg_wpm, 1),
            audio_file="section.wav",
            generation_hash=sec_hash,
            chunks=chunk_records
        )

        # Save metadata.json
        metadata.save(output_dir / "metadata.json")
        log.output(f"section.wav ({total_duration:.2f}s, {avg_wpm:.1f} WPM)")

        # 10. Write Debug Reports if requested
        if self.debug_mode:
            debug_dir = output_dir / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            with open(debug_dir / "chunks.json", "w", encoding="utf-8") as f:
                json.dump(debug_chunks, f, indent=2, ensure_ascii=False)
            with open(debug_dir / "performance.json", "w", encoding="utf-8") as f:
                json.dump([c.__dict__ for c in performance_cues], f, indent=2, ensure_ascii=False)
            with open(debug_dir / "metrics.json", "w", encoding="utf-8") as f:
                json.dump(sec_metrics.__dict__, f, indent=2)
            with open(debug_dir / "validation.json", "w", encoding="utf-8") as f:
                json.dump({
                    "section_valid": is_sec_valid,
                    "section_errors": sec_errors,
                    "consistency": consistency_summary
                }, f, indent=2)
            with open(debug_dir / "generation_report.json", "w", encoding="utf-8") as f:
                json.dump({
                    "section_id": script.section_id,
                    "duration": total_duration,
                    "words": total_words,
                    "average_wpm": avg_wpm,
                    "chunks_count": len(chunk_records),
                    "hash": sec_hash
                }, f, indent=2)
            log.debug(f"Debug reports saved to {debug_dir}")

        return metadata
