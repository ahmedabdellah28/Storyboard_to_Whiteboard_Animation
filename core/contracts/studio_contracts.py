"""Canonical studio contracts, stage rosters, preflight input contracts, and revision tokens.

Part of Phase 1: Core Foundation & Governed Contracts.
"""

from __future__ import annotations

import enum
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================================
# CANONICAL 18 STAGE IDENTIFIERS
# ============================================================================

class StageIdentifier(str, enum.Enum):
    """Canonical 18-stage roster for the dynamic whiteboard production pipeline."""
    INGEST = "sec.ingest"                  # 00: Ingest & Preflight
    OCR = "sec.ocr"                        # 01: Storyboard OCR
    EXTRACTION = "sec.extraction"          # 02: Asset Extraction & Masks
    TTS = "sec.tts"                        # 03: Voiceover Synthesis
    WHISPER = "sec.whisper"                # 04: Word-Level Audio Alignment
    NARRATIVE = "sec.narrative"            # 05: Narrative Semantic Reasoning
    SEMANTIC = "sec.semantic"              # 06: Semantic Beat Binding
    SCENE_SPEC = "sec.scene_spec"          # 07: Scene Spec Compilation
    LAYOUT = "sec.layout"                  # 08: Micro-Zoning Spatial Layout
    CHOREOGRAPHY = "sec.choreography"      # 09: Visual Choreography & Timing
    CAMERA = "sec.camera"                  # 10: Camera Trajectory Pathing
    SFX = "sec.sfx"                        # 11: Dynamic SFX Placement
    AUDIO_MIX = "sec.audio_mix"            # 12: Master Audio & SFX Mix
    RENDER_PLAN = "sec.render_plan"        # 13: Render Plan Compilation
    RENDER = "sec.render"                  # 14: Visual Frame Rasterization (Silent)
    MUX = "sec.mux"                        # 15: Audio/Video Multiplexing
    QA = "sec.qa"                          # 16: Post-Render Automated QA
    EXPORT = "sec.export"                  # 17: Deliverable Export & Thumbnail


@dataclass(frozen=True)
class StageDefinition:
    """Immutable definition of a canonical production pipeline stage."""
    identifier: StageIdentifier
    index: int
    name: str
    description: str
    resource_type: str                     # DISK_IO, CPU_BOUND, VISION, NETWORK_API, DSP_AUDIO, GPU_RENDER
    upstream_dependencies: Set[StageIdentifier]
    produces_artifact: str
    can_need_review: bool = False


# The authoritative 18-stage definition table
STAGE_DEFINITIONS: Dict[StageIdentifier, StageDefinition] = {
    StageIdentifier.INGEST: StageDefinition(
        identifier=StageIdentifier.INGEST,
        index=0,
        name="Section Ingest & Preflight",
        description="Validates raw storyboard image and script text inputs.",
        resource_type="DISK_IO",
        upstream_dependencies=set(),
        produces_artifact="input_manifest.json",
        can_need_review=False,
    ),
    StageIdentifier.OCR: StageDefinition(
        identifier=StageIdentifier.OCR,
        index=1,
        name="Storyboard OCR",
        description="Extracts embedded text labels from storyboard image.",
        resource_type="CPU_BOUND",
        upstream_dependencies={StageIdentifier.INGEST},
        produces_artifact="ocr_results.json",
        can_need_review=False,
    ),
    StageIdentifier.EXTRACTION: StageDefinition(
        identifier=StageIdentifier.EXTRACTION,
        index=2,
        name="Asset Extraction & Masks",
        description="Segments visual characters, icons, and titles into transparent RGBA assets.",
        resource_type="VISION",
        upstream_dependencies={StageIdentifier.INGEST, StageIdentifier.OCR},
        produces_artifact="visual_manifest.json",
        can_need_review=True,
    ),
    StageIdentifier.TTS: StageDefinition(
        identifier=StageIdentifier.TTS,
        index=3,
        name="Voiceover Synthesis",
        description="Generates zero-truncation narration audio from script via Gemini/Edge-TTS.",
        resource_type="NETWORK_API",
        upstream_dependencies={StageIdentifier.INGEST},
        produces_artifact="section_voice.wav",
        can_need_review=True,
    ),
    StageIdentifier.WHISPER: StageDefinition(
        identifier=StageIdentifier.WHISPER,
        index=4,
        name="Whisper Word-Level Alignment",
        description="Extracts high-precision word timestamps and duration boundaries.",
        resource_type="CPU_BOUND",
        upstream_dependencies={StageIdentifier.TTS},
        produces_artifact="whisper_words.json",
        can_need_review=False,
    ),
    StageIdentifier.NARRATIVE: StageDefinition(
        identifier=StageIdentifier.NARRATIVE,
        index=5,
        name="Narrative Semantic Reasoning",
        description="Derives narrative concepts, anchor candidates, and visual flow rules.",
        resource_type="NETWORK_API",
        upstream_dependencies={StageIdentifier.INGEST, StageIdentifier.WHISPER},
        produces_artifact="narrative_map.json",
        can_need_review=False,
    ),
    StageIdentifier.SEMANTIC: StageDefinition(
        identifier=StageIdentifier.SEMANTIC,
        index=6,
        name="Semantic Beat Binding",
        description="Binds extracted visual entities to spoken word concepts and phrases.",
        resource_type="CPU_BOUND",
        upstream_dependencies={StageIdentifier.EXTRACTION, StageIdentifier.NARRATIVE},
        produces_artifact="semantic_bindings.json",
        can_need_review=True,
    ),
    StageIdentifier.SCENE_SPEC: StageDefinition(
        identifier=StageIdentifier.SCENE_SPEC,
        index=7,
        name="Scene Spec Compilation",
        description="Compiles target timeline duration, resolution, and pacing constraints.",
        resource_type="CPU_BOUND",
        upstream_dependencies={StageIdentifier.SEMANTIC},
        produces_artifact="scene_spec.json",
        can_need_review=False,
    ),
    StageIdentifier.LAYOUT: StageDefinition(
        identifier=StageIdentifier.LAYOUT,
        index=8,
        name="Micro-Zoning Spatial Layout",
        description="Places visual entities on 1920x1080 canvas preventing collisions.",
        resource_type="CPU_BOUND",
        upstream_dependencies={StageIdentifier.EXTRACTION, StageIdentifier.SCENE_SPEC},
        produces_artifact="placed_elements_layout.json",
        can_need_review=True,
    ),
    StageIdentifier.CHOREOGRAPHY: StageDefinition(
        identifier=StageIdentifier.CHOREOGRAPHY,
        index=9,
        name="Visual Choreography & Timing",
        description="Calculates stroke inking order, hand reveal paths, and duration curves.",
        resource_type="CPU_BOUND",
        upstream_dependencies={StageIdentifier.LAYOUT, StageIdentifier.WHISPER},
        produces_artifact="timeline_manifest.json",
        can_need_review=False,
    ),
    StageIdentifier.CAMERA: StageDefinition(
        identifier=StageIdentifier.CAMERA,
        index=10,
        name="Camera Trajectory Pathing",
        description="Calculates viewport pans and zooms centered on actively drawn elements.",
        resource_type="CPU_BOUND",
        upstream_dependencies={StageIdentifier.LAYOUT, StageIdentifier.CHOREOGRAPHY},
        produces_artifact="camera_trajectory.json",
        can_need_review=True,
    ),
    StageIdentifier.SFX: StageDefinition(
        identifier=StageIdentifier.SFX,
        index=11,
        name="Dynamic SFX Placement",
        description="Places whoosh, click, and inking sound cues based on camera pans and reveals.",
        resource_type="DISK_IO",
        upstream_dependencies={StageIdentifier.CHOREOGRAPHY, StageIdentifier.CAMERA},
        produces_artifact="sfx_cues.json",
        can_need_review=False,
    ),
    StageIdentifier.AUDIO_MIX: StageDefinition(
        identifier=StageIdentifier.AUDIO_MIX,
        index=12,
        name="Master Audio & SFX Mix",
        description="Mixes voice narration with ducked sound effects into master WAV.",
        resource_type="DSP_AUDIO",
        upstream_dependencies={StageIdentifier.TTS, StageIdentifier.SFX},
        produces_artifact="master_audio.wav",
        can_need_review=False,
    ),
    StageIdentifier.RENDER_PLAN: StageDefinition(
        identifier=StageIdentifier.RENDER_PLAN,
        index=13,
        name="Render Plan Compilation",
        description="Compiles final unified render plan merging choreography, camera, and assets.",
        resource_type="CPU_BOUND",
        upstream_dependencies={StageIdentifier.CHOREOGRAPHY, StageIdentifier.CAMERA, StageIdentifier.EXTRACTION},
        produces_artifact="final_render_plan.json",
        can_need_review=False,
    ),
    StageIdentifier.RENDER: StageDefinition(
        identifier=StageIdentifier.RENDER,
        index=14,
        name="Visual Frame Rasterization",
        description="Renders silent 1080p60 frames with whiteboard inking and hand compositor.",
        resource_type="GPU_RENDER",
        upstream_dependencies={StageIdentifier.RENDER_PLAN},
        produces_artifact="silent_visual_1080p.mp4",
        can_need_review=False,
    ),
    StageIdentifier.MUX: StageDefinition(
        identifier=StageIdentifier.MUX,
        index=15,
        name="Audio/Video Multiplexing",
        description="Multiplexes silent video with master audio via FFmpeg faststart.",
        resource_type="DISK_IO",
        upstream_dependencies={StageIdentifier.RENDER, StageIdentifier.AUDIO_MIX},
        produces_artifact="section_delivery.mp4",
        can_need_review=False,
    ),
    StageIdentifier.QA: StageDefinition(
        identifier=StageIdentifier.QA,
        index=16,
        name="Post-Render Automated QA",
        description="Inspects delivered MP4 for black frames, audio clipping, and sync drift.",
        resource_type="CPU_BOUND",
        upstream_dependencies={StageIdentifier.MUX},
        produces_artifact="qa_report.json",
        can_need_review=True,
    ),
    StageIdentifier.EXPORT: StageDefinition(
        identifier=StageIdentifier.EXPORT,
        index=17,
        name="Deliverable Export & Thumbnail",
        description="Generates poster thumbnail and copies final package to deliverables directory.",
        resource_type="DISK_IO",
        upstream_dependencies={StageIdentifier.QA},
        produces_artifact="deliverable_manifest.json",
        can_need_review=False,
    ),
}

CANONICAL_STAGES_ORDER: List[StageIdentifier] = [
    StageIdentifier.INGEST,
    StageIdentifier.OCR,
    StageIdentifier.EXTRACTION,
    StageIdentifier.TTS,
    StageIdentifier.WHISPER,
    StageIdentifier.NARRATIVE,
    StageIdentifier.SEMANTIC,
    StageIdentifier.SCENE_SPEC,
    StageIdentifier.LAYOUT,
    StageIdentifier.CHOREOGRAPHY,
    StageIdentifier.CAMERA,
    StageIdentifier.SFX,
    StageIdentifier.AUDIO_MIX,
    StageIdentifier.RENDER_PLAN,
    StageIdentifier.RENDER,
    StageIdentifier.MUX,
    StageIdentifier.QA,
    StageIdentifier.EXPORT,
]


# ============================================================================
# SECTION INITIAL INPUT CONTRACT (Decoupled Preflight)
# ============================================================================

@dataclass
class SectionInputContract:
    """Preflight contract for section creation.
    
    Guarantees that section creation ONLY requires Storyboard + Script.
    Explicitly forbids requiring pre-existing voice, whisper, or layout files.
    """
    section_id: str
    storyboard_path: str
    script_text: str
    title: Optional[str] = None
    sequence_index: int = 0
    custom_voice_path: Optional[str] = None
    generate_tts: bool = True

    def validate(self) -> Dict[str, Any]:
        """Validate input constraints.
        
        Returns a dictionary: {'is_valid': bool, 'errors': List[str], 'warnings': List[str]}
        """
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Section ID check
        if not self.section_id or not self.section_id.strip():
            errors.append("section_id cannot be empty")

        # 2. Storyboard validation
        sb_path = Path(self.storyboard_path)
        if not sb_path.is_file():
            errors.append(f"Storyboard file does not exist: {self.storyboard_path}")
        else:
            valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
            if sb_path.suffix.lower() not in valid_exts:
                errors.append(f"Unsupported storyboard image format '{sb_path.suffix}'. Expected: {valid_exts}")
            try:
                size_bytes = sb_path.stat().st_size
                if size_bytes < 512:
                    errors.append(f"Storyboard file is suspiciously small ({size_bytes} bytes).")
            except Exception as e:
                errors.append(f"Cannot access storyboard file metadata: {e}")

        # 3. Script validation
        cleaned_script = (self.script_text or "").strip()
        if len(cleaned_script) < 5:
            errors.append("Script text must contain at least 5 characters.")

        # 4. Voice validation (only if custom voice provided)
        if self.custom_voice_path:
            voice_path = Path(self.custom_voice_path)
            if not voice_path.is_file():
                errors.append(f"Specified custom_voice_path does not exist: {self.custom_voice_path}")
            elif voice_path.suffix.lower() not in {".wav", ".mp3", ".m4a", ".aac"}:
                warnings.append(f"Custom voice file '{voice_path.name}' is not a standard WAV/MP3 format.")
        elif not self.generate_tts:
            errors.append("Either custom_voice_path must be supplied or generate_tts must be True.")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }


# ============================================================================
# REVISION TOKENS & EDIT TRANSACTIONS (Race-Condition Safety)
# ============================================================================

@dataclass(frozen=True)
class RevisionToken:
    """Immutable stamp assigned to background tasks to prevent stale results from overwriting user edits."""
    project_id: str
    section_id: str
    revision_id: int                    # Monotonically increasing revision counter
    transaction_uuid: str               # Unique UUID of the editing transaction
    created_at: str = field(default_factory=_now_iso)
    schema_version: int = 2

    def is_stale_compared_to(self, current_revision_id: int) -> bool:
        """Check if this token represents an obsolete revision."""
        return self.revision_id < current_revision_id


@dataclass
class EditTransaction:
    """Encapsulates a user mutation and calculates exact downstream stage invalidations."""
    transaction_uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    section_id: str = ""
    mutated_fields: List[str] = field(default_factory=list)
    description: str = ""
    target_revision_id: int = 1
    invalidated_stages: Set[StageIdentifier] = field(default_factory=set)
    created_at: str = field(default_factory=_now_iso)

    @staticmethod
    def compute_invalidations(mutated_field: str) -> Set[StageIdentifier]:
        """Determine downstream stages to invalidate based on mutated field."""
        field_lower = mutated_field.lower()

        if "script" in field_lower:
            return {
                StageIdentifier.TTS,
                StageIdentifier.WHISPER,
                StageIdentifier.NARRATIVE,
                StageIdentifier.SEMANTIC,
                StageIdentifier.SCENE_SPEC,
                StageIdentifier.CHOREOGRAPHY,
                StageIdentifier.SFX,
                StageIdentifier.AUDIO_MIX,
                StageIdentifier.RENDER_PLAN,
                StageIdentifier.RENDER,
                StageIdentifier.MUX,
                StageIdentifier.QA,
                StageIdentifier.EXPORT,
            }
        elif "storyboard" in field_lower:
            return {
                StageIdentifier.OCR,
                StageIdentifier.EXTRACTION,
                StageIdentifier.SEMANTIC,
                StageIdentifier.SCENE_SPEC,
                StageIdentifier.LAYOUT,
                StageIdentifier.CHOREOGRAPHY,
                StageIdentifier.CAMERA,
                StageIdentifier.SFX,
                StageIdentifier.RENDER_PLAN,
                StageIdentifier.RENDER,
                StageIdentifier.MUX,
                StageIdentifier.QA,
                StageIdentifier.EXPORT,
            }
        elif "layout" in field_lower or "element" in field_lower:
            return {
                StageIdentifier.CHOREOGRAPHY,
                StageIdentifier.CAMERA,
                StageIdentifier.SFX,
                StageIdentifier.AUDIO_MIX,
                StageIdentifier.RENDER_PLAN,
                StageIdentifier.RENDER,
                StageIdentifier.MUX,
                StageIdentifier.QA,
                StageIdentifier.EXPORT,
            }
        elif "camera" in field_lower:
            # Fast camera pans change SFX -> Audio Mix -> Mux! (Stage 14 Visual Render is re-compiled via RenderPlan)
            return {
                StageIdentifier.SFX,
                StageIdentifier.AUDIO_MIX,
                StageIdentifier.RENDER_PLAN,
                StageIdentifier.RENDER,
                StageIdentifier.MUX,
                StageIdentifier.QA,
                StageIdentifier.EXPORT,
            }
        elif "sfx" in field_lower or "audio" in field_lower:
            # Crucial: Visual frame render (Stage 14) is 100% PRESERVED!
            return {
                StageIdentifier.AUDIO_MIX,
                StageIdentifier.MUX,
                StageIdentifier.QA,
                StageIdentifier.EXPORT,
            }
        return set()
