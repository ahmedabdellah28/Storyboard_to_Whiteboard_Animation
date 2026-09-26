import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml

from .transcription.faster_whisper_engine import FasterWhisperEngine, compute_file_sha256
from .transcription.whisper_parser import WhisperParser
from .alignment.script_audio_aligner import ScriptAudioAligner
from .speech.sentence_segmenter import SentenceSegmenter
from .speech.pause_detector import PauseDetector
from .speech.speech_beat_detector import SpeechBeatDetector
from .visual.semantic_beat_mapper import SemanticBeatMapper
from .visual.beat_solver import BeatSolver
from .effects.sfx_mapper import SFXMapper
from .effects.camera_mapper import CameraMapper
from .timeline.models import MasterTimeline
from .timeline.builder import MasterTimelineBuilder
from .timeline.exporter import TimelineExporter
from .debug.debugger import TimingDebugger

class TimingPipeline:
    """Master pipeline orchestrating the entire audio-to-visual timing synthesis."""
    def __init__(
        self,
        config_path: Optional[Path | str] = None,
        whisper_engine: Optional[FasterWhisperEngine] = None
    ):
        if config_path is None:
            config_path = Path(__file__).resolve().parent / "config.yaml"
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}

        w_cfg = self.config.get("whisper", {})
        self.whisper_model_name = w_cfg.get("model", "small")
        self.whisper_engine = whisper_engine or FasterWhisperEngine(
            model_size=self.whisper_model_name,
            language=w_cfg.get("language", "ar"),
            device=w_cfg.get("device", "auto"),
            compute_type=w_cfg.get("compute_type", "auto"),
            vad_filter=w_cfg.get("vad_filter", True)
        )

        p_cfg = self.config.get("pauses", {})
        self.pause_detector = PauseDetector(min_pause_s=float(p_cfg.get("min_pause_s", 0.12)))

        s_cfg = self.config.get("solver", {})
        self.solver = BeatSolver(
            max_lead_in_s=float(s_cfg.get("max_lead_in_s", 0.45)),
            max_lag_s=float(s_cfg.get("max_lag_s", 0.30)),
            pause_utilization=float(s_cfg.get("pause_utilization", 0.85)),
            allow_overlap=bool(s_cfg.get("allow_overlap", True)),
            max_overlap_s=float(s_cfg.get("max_overlap_s", 0.25))
        )

        self.aligner = ScriptAudioAligner()
        self.sentence_segmenter = SentenceSegmenter()
        self.speech_beat_detector = SpeechBeatDetector()
        self.semantic_mapper = SemanticBeatMapper()
        self.sfx_mapper = SFXMapper()
        self.camera_mapper = CameraMapper()

    def load_asset_plan(self, section_dir: Path) -> List[Dict[str, Any]]:
        """Finds and parses asset_plan.json or placed_elements_layout.json from the section."""
        # 1. Search for asset_plan.json
        cand_plans = [
            section_dir / "assets" / "asset_plan.json",
            section_dir / "asset_plan.json",
            section_dir / "placed_elements_layout.json"
        ]
        for p in cand_plans:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            return data
                        if isinstance(data, dict):
                            if "assets" in data and isinstance(data["assets"], list):
                                return data["assets"]
                            if "elements" in data and isinstance(data["elements"], dict):
                                # Flatten zones from placed_elements_layout.json
                                flattened = []
                                for zone_name, items in data["elements"].items():
                                    if isinstance(items, list):
                                        for it in items:
                                            it["zone"] = zone_name
                                            flattened.append(it)
                                return flattened
                except Exception:
                    pass
        return []

    def process_section(
        self,
        section_dir: Path | str,
        script_file: Optional[Path | str] = None,
        audio_file: Optional[Path | str] = None,
        output_dir: Optional[Path | str] = None,
        force_whisper: bool = False
    ) -> MasterTimeline:
        """Executes the full timing synthesis pipeline for a section."""
        sec_dir = Path(section_dir).resolve()
        section_id = sec_dir.name

        # Resolve inputs
        script_path = Path(script_file).resolve() if script_file else sec_dir / "script.txt"
        audio_path = Path(audio_file).resolve() if audio_file else sec_dir / "voice" / "section.wav"
        if not audio_path.exists() and (sec_dir / "voiceover.wav").exists():
            audio_path = sec_dir / "voiceover.wav"
        if not audio_path.exists() and (sec_dir / "master_audio.wav").exists():
            audio_path = sec_dir / "master_audio.wav"

        if not script_path.exists():
            raise FileNotFoundError(f"Script file not found: {script_path}")
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        timing_dir = Path(output_dir).resolve() if output_dir else sec_dir / "timing"
        timing_dir.mkdir(parents=True, exist_ok=True)

        with open(script_path, "r", encoding="utf-8") as f:
            script_text = f.read()

        # Compute file hashes for reproducible provenance
        audio_hash = compute_file_sha256(audio_path)
        script_hash = compute_file_sha256(script_path)
        config_hash = compute_file_sha256(self.config_path) if self.config_path.exists() else ""

        print(f"[TIMING] Processing Section: {section_id}")
        print(f"[AUDIO]  {audio_path.name} (SHA256: {audio_hash[:8]}...)")
        print(f"[SCRIPT] {len(script_text.split())} words")

        # 1. Faster-Whisper Transcription
        whisper_cache = timing_dir / "whisper.json"
        print(f"[WHISPER] Running {self.whisper_model_name}...")
        whisper_output = self.whisper_engine.transcribe(
            audio_path=audio_path,
            cache_file=whisper_cache,
            force=force_whisper
        )
        total_duration = whisper_output.duration
        print(f"[WHISPER] Extracted {len(whisper_output.segments)} segments, duration: {total_duration:.2f}s")

        # 2. Extract Raw Words & Script Alignment
        raw_words = WhisperParser.extract_word_items(whisper_output)
        aligned_words = self.aligner.align(script_text, raw_words)
        print(f"[ALIGNMENT] Aligned {len(aligned_words)} words to audio timeline")

        # 3. Sentence Segmentation
        sentences = self.sentence_segmenter.segment(script_text, aligned_words)
        print(f"[SENTENCES] Identified {len(sentences)} rhythmic sentences")

        # 4. Pause Detection
        pauses = self.pause_detector.detect_pauses(aligned_words)
        print(f"[PAUSES] Detected {len(pauses)} inter-word pauses")

        # 5. Speech Beats
        speech_beats = self.speech_beat_detector.detect_beats(sentences, pauses)

        # 6. Load Asset Plan & Map Visual Beats
        assets = self.load_asset_plan(sec_dir)
        print(f"[ASSETS] Found {len(assets)} visual assets in plan")
        semantic_beats, visual_beats = self.semantic_mapper.map_visual_beats(
            assets=assets,
            sentences=sentences,
            words=aligned_words,
            total_duration=total_duration
        )

        # 7. Beat Solver (Actual Drawing Timeline)
        print(f"[SOLVER] Solving temporal constraints for {len(visual_beats)} visual beats...")
        drawings = self.solver.solve(
            visual_beats=visual_beats,
            assets=assets,
            pauses=pauses,
            section_duration=total_duration
        )
        print(f"[SOLVER] Generated {len(drawings)} drawing events")

        # 8. SFX & Camera Mapping
        sfx_events = self.sfx_mapper.map_sfx(drawings, assets)
        camera_events = self.camera_mapper.map_camera(drawings, assets, total_duration)
        print(f"[EFFECTS] Generated {len(sfx_events)} SFX cues and {len(camera_events)} camera actions")

        # 9. Assemble Master Timeline
        master = MasterTimelineBuilder.build(
            section_id=section_id,
            duration=total_duration,
            audio_file=audio_path.name,
            script_file=script_path.name,
            hashes={
                "audio_sha256": audio_hash,
                "script_sha256": script_hash,
                "config_sha256": config_hash
            },
            whisper_model=self.whisper_model_name,
            words=aligned_words,
            sentences=sentences,
            pauses=pauses,
            speech_beats=speech_beats,
            semantic_beats=semantic_beats,
            visual_beats=visual_beats,
            drawings=drawings,
            sfx=sfx_events,
            camera=camera_events
        )

        # 10. Export all 11 JSON documents
        TimelineExporter.export_all(timing_dir, master, whisper_output)

        # 11. Debug Reports and Visual Inspector
        TimingDebugger.generate_debug_report(timing_dir, master)
        print(f"[OUTPUT] Master timeline saved -> {timing_dir / 'master_timeline.json'}")

        return master
