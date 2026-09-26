from typing import List, Dict, Any, Optional
from .models import (
    MasterTimeline,
    WordItem,
    SentenceItem,
    PauseItem,
    SpeechBeatItem,
    SemanticBeatItem,
    VisualBeatItem,
    DrawingItem,
    SFXItem,
    CameraItem,
)

class MasterTimelineBuilder:
    """Assembles all acoustic, semantic, drawing, and effect layers into the MasterTimeline."""
    @staticmethod
    def build(
        section_id: str,
        duration: float,
        audio_file: str,
        script_file: str,
        hashes: Dict[str, str],
        whisper_model: str,
        words: List[WordItem],
        sentences: List[SentenceItem],
        pauses: List[PauseItem],
        speech_beats: List[SpeechBeatItem],
        semantic_beats: List[SemanticBeatItem],
        visual_beats: List[VisualBeatItem],
        drawings: List[DrawingItem],
        sfx: List[SFXItem],
        camera: List[CameraItem]
    ) -> MasterTimeline:
        return MasterTimeline(
            section_id=section_id,
            duration=round(duration, 3),
            audio_file=audio_file,
            script_file=script_file,
            hashes=hashes,
            whisper_model=whisper_model,
            words=words,
            sentences=sentences,
            pauses=pauses,
            speech_beats=speech_beats,
            semantic_beats=semantic_beats,
            visual_beats=visual_beats,
            drawings=drawings,
            sfx=sfx,
            camera=camera
        )
