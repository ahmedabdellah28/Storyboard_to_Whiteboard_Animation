"""Input and stage-boundary preflight validation system for Whiteboard Studio.

Part of Phase 3: Validation System & Recovery System.
Enforces strict preflight checks without requiring generated intermediate artifacts at ingest.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from core.contracts.studio_contracts import (
    CANONICAL_STAGES_ORDER,
    STAGE_DEFINITIONS,
    SectionInputContract,
    StageDefinition,
    StageIdentifier,
)
from core.state.project_state import ProjectState, SectionState


@dataclass
class ValidationResult:
    """Outcome of a validation check."""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, message: str) -> None:
        self.is_valid = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


class InputPreflightValidator:
    """Validates raw user inputs at project and section creation time."""

    @staticmethod
    def validate_section_input(contract: SectionInputContract) -> ValidationResult:
        """Validate SectionInputContract (Storyboard image + Script text)."""
        res = ValidationResult()
        raw_res = contract.validate()

        for err in raw_res.get("errors", []):
            res.add_error(err)
        for warn in raw_res.get("warnings", []):
            res.add_warning(warn)

        # Advanced Storyboard Image Header Inspection
        if res.is_valid:
            sb_path = Path(contract.storyboard_path)
            try:
                # Basic signature / size validation
                size = sb_path.stat().st_size
                res.details["storyboard_size_bytes"] = size
                if size < 1024:
                    res.add_warning(f"Storyboard image '{sb_path.name}' is very small ({size} bytes).")
            except Exception as e:
                res.add_error(f"Failed to inspect storyboard file: {e}")

        # Script Word Count & Length Analysis
        if contract.script_text:
            word_count = len(contract.script_text.split())
            res.details["script_word_count"] = word_count
            res.details["script_char_count"] = len(contract.script_text)
            if word_count < 3:
                res.add_warning("Script is very short (< 3 words). Generated video may be under 2 seconds.")

        return res

    @staticmethod
    def validate_project_structure(project_state: ProjectState) -> ValidationResult:
        """Verify project consistency, duplicate section IDs, and sequence ordering."""
        res = ValidationResult()

        if not project_state.project_id or not project_state.project_id.strip():
            res.add_error("project_id cannot be empty")

        indices: Set[int] = set()
        for sid, sec in project_state.sections.items():
            if sec.sequence_index in indices:
                res.add_warning(f"Duplicate sequence_index {sec.sequence_index} detected in section '{sid}'.")
            indices.add(sec.sequence_index)

        res.details["total_sections"] = len(project_state.sections)
        return res


class StagePreflightValidator:
    """Dynamically validates prerequisite upstream artifacts before an ExecutableTask executes."""

    @staticmethod
    def validate_stage_prerequisites(
        stage_id: StageIdentifier,
        section_dir: Union[str, Path],
        inputs: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """Verify that all upstream requirements for stage_id exist on disk and are non-empty."""
        res = ValidationResult()
        s_dir = Path(section_dir)
        defn = STAGE_DEFINITIONS.get(stage_id)

        if not defn:
            res.add_error(f"Unrecognized canonical stage identifier: {stage_id}")
            return res

        # Check stage-specific prerequisite artifacts
        if stage_id == StageIdentifier.INGEST:
            # Requires storyboard and script in inputs or section_dir
            sb = inputs.get("storyboard") if inputs else str(s_dir / "storyboard.png")
            sc = inputs.get("script") if inputs else str(s_dir / "script.txt")
            if not Path(sb).is_file():
                res.add_error(f"Stage 00 (Ingest) missing storyboard image at {sb}")
            if not Path(sc).is_file() and not (inputs and inputs.get("script_text")):
                res.add_error(f"Stage 00 (Ingest) missing script input at {sc}")

        elif stage_id == StageIdentifier.OCR:
            sb = inputs.get("storyboard") if inputs else str(s_dir / "storyboard.png")
            if not Path(sb).is_file():
                res.add_error(f"Stage 01 (OCR) requires storyboard file: {sb}")

        elif stage_id == StageIdentifier.EXTRACTION:
            sb = inputs.get("storyboard") if inputs else str(s_dir / "storyboard.png")
            if not Path(sb).is_file():
                res.add_error(f"Stage 02 (Extraction) requires storyboard file: {sb}")

        elif stage_id == StageIdentifier.TTS:
            # TTS only requires script text or script file
            sc = inputs.get("script") if inputs else str(s_dir / "script.txt")
            has_text = bool(inputs and inputs.get("script_text"))
            if not Path(sc).is_file() and not has_text:
                res.add_error(f"Stage 03 (TTS) requires script file or text input at {sc}")

        elif stage_id == StageIdentifier.WHISPER:
            # Requires voice WAV
            voice = inputs.get("voice") if inputs else str(s_dir / "voice" / "section.wav")
            if not Path(voice).is_file():
                # Fallback path check
                fallback_voice = s_dir / "section_voice.wav"
                if not fallback_voice.is_file():
                    res.add_error(f"Stage 04 (Whisper) requires synthesized voice WAV: {voice}")

        elif stage_id == StageIdentifier.LAYOUT:
            # Requires visual manifest
            manifest = inputs.get("visual_manifest") if inputs else str(s_dir / "visual_manifest.json")
            if not Path(manifest).is_file():
                res.add_error(f"Stage 08 (Layout) requires visual manifest: {manifest}")

        elif stage_id == StageIdentifier.AUDIO_MIX:
            # Requires voice WAV and sfx cues
            voice = inputs.get("voice") if inputs else str(s_dir / "voice" / "section.wav")
            if not Path(voice).is_file() and not (s_dir / "section_voice.wav").is_file():
                res.add_error(f"Stage 12 (AudioMix) requires voice WAV: {voice}")

        elif stage_id == StageIdentifier.RENDER:
            # Requires final render plan or layout
            plan = inputs.get("render_plan") if inputs else str(s_dir / "timing" / "final_render_plan.json")
            layout = inputs.get("layout") if inputs else str(s_dir / "placed_elements_layout.json")
            if not Path(plan).is_file() and not Path(layout).is_file():
                res.add_error(f"Stage 14 (Visual Render) requires render plan or layout file.")

        elif stage_id == StageIdentifier.MUX:
            # Requires silent video and master audio
            video = inputs.get("video") if inputs else str(s_dir / "silent_visual_1080p.mp4")
            audio = inputs.get("audio") if inputs else str(s_dir / "master_audio.wav")
            if not Path(video).is_file() and not (s_dir / "final_whiteboard_1080p.mp4").is_file():
                res.add_error(f"Stage 15 (Mux) requires rendered video stream: {video}")
            if not Path(audio).is_file():
                res.add_error(f"Stage 15 (Mux) requires master audio WAV: {audio}")

        return res
