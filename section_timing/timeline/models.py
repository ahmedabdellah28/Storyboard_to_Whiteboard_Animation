from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# --- Raw Whisper Layer Models ---
class WhisperWord(BaseModel):
    word: str
    start: float
    end: float
    probability: float

class WhisperSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    words: List[WhisperWord] = Field(default_factory=list)

class WhisperOutput(BaseModel):
    audio_path: str
    duration: float
    language: str
    segments: List[WhisperSegment] = Field(default_factory=list)

# --- Speech Layer Models ---
class WordItem(BaseModel):
    id: str
    text: str
    start: float
    end: float
    duration: float
    probability: float = 1.0
    sentence_id: Optional[str] = None
    semantic_span_id: Optional[str] = None
    needs_review: bool = False

class SentenceItem(BaseModel):
    id: str
    text: str
    start: float
    end: float
    duration: float
    word_ids: List[str] = Field(default_factory=list)
    confidence: float = 1.0

class PauseItem(BaseModel):
    id: str
    start: float
    end: float
    duration: float
    type: str  # micro_pause, short_pause, medium_pause, long_pause

class SpeechBeatItem(BaseModel):
    id: str
    start: float
    end: float
    type: str  # hook, main_fact, pause, new_idea, important_fact, outro
    importance: float = 0.5
    sentence_id: Optional[str] = None

# --- Semantic & Visual Layer Models ---
class SemanticBeatItem(BaseModel):
    id: str
    sentence_id: Optional[str] = None
    subject: Optional[str] = None
    action: Optional[str] = None
    relation: Optional[str] = None
    objects: List[str] = Field(default_factory=list)
    anchor_text: str = ""
    importance: float = 0.8

class SpeechAnchor(BaseModel):
    text: str
    start: float
    end: float

class VisualBeatItem(BaseModel):
    id: str
    asset_id: str
    semantic_role: str = "subject"  # subject, object, location, detail, connector
    speech_anchor: SpeechAnchor
    importance: float = 0.8
    action: str = "draw"

# --- Solved Drawing Timeline Models ---
class DrawingItem(BaseModel):
    id: str
    type: str = "draw"  # draw, reveal, write, connect, transform, highlight, erase, move, zoom
    asset_id: str
    start_s: float
    end_s: float
    duration_s: float
    trigger: str = "semantic"  # semantic, dependency, pause, lead_in
    anchor_text: str = ""
    confidence: float = 0.95
    layer_order: int = 0

class SFXItem(BaseModel):
    id: str
    type: str = "marker_draw"  # marker_draw, pop, whoosh, ding, click
    start_s: float
    end_s: float
    duration_s: float
    anchor_asset_id: Optional[str] = None

class CameraItem(BaseModel):
    id: str
    type: str = "pan"  # pan, zoom, focus, reveal
    start_s: float
    end_s: float
    duration_s: float
    target_asset_id: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)

# --- Master Timeline Model ---
class MasterTimeline(BaseModel):
    section_id: str
    duration: float
    audio_file: str
    script_file: str
    hashes: Dict[str, str] = Field(default_factory=dict)
    whisper_model: str = "small"
    
    words: List[WordItem] = Field(default_factory=list)
    sentences: List[SentenceItem] = Field(default_factory=list)
    pauses: List[PauseItem] = Field(default_factory=list)
    speech_beats: List[SpeechBeatItem] = Field(default_factory=list)
    semantic_beats: List[SemanticBeatItem] = Field(default_factory=list)
    visual_beats: List[VisualBeatItem] = Field(default_factory=list)
    drawings: List[DrawingItem] = Field(default_factory=list)
    sfx: List[SFXItem] = Field(default_factory=list)
    camera: List[CameraItem] = Field(default_factory=list)
