"""Input models representing the data coming from previous pipeline stages."""

import os
import json
import wave
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

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
    type: str = "short_pause"

class SemanticBeatItem(BaseModel):
    id: str
    sentence_id: Optional[str] = None
    subject: Optional[str] = None
    action: Optional[str] = None
    relation: Optional[str] = None
    objects: List[str] = Field(default_factory=list)
    anchor_text: str = ""
    importance: float = 0.8

class AssetMetadata(BaseModel):
    asset_id: str
    file: str
    image_path: Optional[str] = None
    semantic_description: str = ""
    visual_role: str = "subject"  # subject, object, environment, action, symbol, banner
    action: Optional[str] = None
    objects: List[str] = Field(default_factory=list)
    state: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    drawing_demand: float = 1.8
    orig_box: Optional[List[int]] = None
    orig_size: Optional[List[int]] = None
    area: Optional[int] = None
    row: Optional[int] = None
    col: Optional[int] = None

class AssetCatalog(BaseModel):
    assets: Dict[str, AssetMetadata] = Field(default_factory=dict)

    def get(self, asset_id: str) -> Optional[AssetMetadata]:
        return self.assets.get(asset_id)

    def contains(self, asset_id: str) -> bool:
        return asset_id in self.assets

class SectionInput(BaseModel):
    section_id: str
    script_text: str
    audio_path: str
    audio_duration: float
    words: List[WordItem] = Field(default_factory=list)
    sentences: List[SentenceItem] = Field(default_factory=list)
    pauses: List[PauseItem] = Field(default_factory=list)
    semantic_beats: List[SemanticBeatItem] = Field(default_factory=list)
    initial_drawings: List[Dict[str, Any]] = Field(default_factory=list)
    initial_sfx: List[Dict[str, Any]] = Field(default_factory=list)
    initial_camera: List[Dict[str, Any]] = Field(default_factory=list)
    assets: Dict[str, AssetMetadata] = Field(default_factory=dict)

    @classmethod
    def from_directory(cls, section_dir: str | Path) -> "SectionInput":
        """Loads a SectionInput bundle from a section folder structure."""
        section_path = Path(section_dir)
        section_id = section_path.name

        # 1. Script
        script_file = section_path / "script.txt"
        script_text = script_file.read_text(encoding="utf-8") if script_file.exists() else ""

        # 2. Audio file & duration
        audio_candidates = [
            section_path / "voice" / "section.wav",
            section_path / "master_audio.wav",
            section_path / "voiceover.wav"
        ]
        audio_path = ""
        audio_duration = 0.0
        for cand in audio_candidates:
            if cand.exists():
                audio_path = str(cand)
                try:
                    with wave.open(str(cand), "rb") as wf:
                        audio_duration = round(wf.getnframes() / float(wf.getframerate()), 3)
                except Exception:
                    pass
                break

        # 3. Timing JSON files
        timing_dir = section_path / "timing"
        words: List[WordItem] = []
        sentences: List[SentenceItem] = []
        pauses: List[PauseItem] = []
        semantic_beats: List[SemanticBeatItem] = []
        initial_drawings: List[Dict[str, Any]] = []
        initial_sfx: List[Dict[str, Any]] = []
        initial_camera: List[Dict[str, Any]] = []

        if timing_dir.exists():
            words_file = timing_dir / "words.json"
            if words_file.exists():
                try:
                    wdata = json.loads(words_file.read_text(encoding="utf-8"))
                    items = wdata.get("words", []) if isinstance(wdata, dict) else wdata
                    words = [WordItem(**w) for w in items]
                except Exception:
                    pass

            sentences_file = timing_dir / "sentences.json"
            if sentences_file.exists():
                try:
                    sdata = json.loads(sentences_file.read_text(encoding="utf-8"))
                    items = sdata.get("sentences", []) if isinstance(sdata, dict) else sdata
                    sentences = [SentenceItem(**s) for s in items]
                except Exception:
                    pass

            pauses_file = timing_dir / "pauses.json"
            if pauses_file.exists():
                try:
                    pdata = json.loads(pauses_file.read_text(encoding="utf-8"))
                    items = pdata.get("pauses", []) if isinstance(pdata, dict) else pdata
                    pauses = [PauseItem(**p) for p in items]
                except Exception:
                    pass

            semantic_beats_file = timing_dir / "semantic_beats.json"
            if semantic_beats_file.exists():
                try:
                    sbdata = json.loads(semantic_beats_file.read_text(encoding="utf-8"))
                    items = sbdata.get("beats", []) if isinstance(sbdata, dict) else sbdata
                    semantic_beats = [SemanticBeatItem(**sb) for sb in items]
                except Exception:
                    pass

            # Drawings: try initial_timeline.json first, then drawing_timeline.json
            drawings_file = timing_dir / "initial_timeline.json"
            if not drawings_file.exists():
                drawings_file = timing_dir / "drawing_timeline.json"
            if drawings_file.exists():
                try:
                    ddata = json.loads(drawings_file.read_text(encoding="utf-8"))
                    if isinstance(ddata, dict):
                        initial_drawings = ddata.get("events", ddata.get("drawings", []))
                        if audio_duration <= 0.0 and "duration" in ddata:
                            audio_duration = float(ddata["duration"])
                    elif isinstance(ddata, list):
                        initial_drawings = ddata
                except Exception:
                    pass

            sfx_file = timing_dir / "sfx_timeline.json"
            if sfx_file.exists():
                try:
                    sfx_data = json.loads(sfx_file.read_text(encoding="utf-8"))
                    initial_sfx = sfx_data.get("events", sfx_data.get("sfx", [])) if isinstance(sfx_data, dict) else sfx_data
                except Exception:
                    pass

            camera_file = timing_dir / "camera_timeline.json"
            if camera_file.exists():
                try:
                    cam_data = json.loads(camera_file.read_text(encoding="utf-8"))
                    initial_camera = cam_data.get("events", cam_data.get("camera", [])) if isinstance(cam_data, dict) else cam_data
                except Exception:
                    pass

        # 4. Assets catalog / metadata
        assets_dir = section_path / "assets"
        assets: Dict[str, AssetMetadata] = {}
        meta_file = assets_dir / "asset_catalog.json"
        if not meta_file.exists():
            meta_file = assets_dir / "metadata.json"

        if meta_file.exists():
            try:
                mdata = json.loads(meta_file.read_text(encoding="utf-8"))
                # could be dict of id -> obj, or {"assets": [...]}
                if isinstance(mdata, dict):
                    entries = mdata.get("assets", mdata)
                    for k, v in entries.items():
                        if isinstance(v, dict):
                            aid = v.get("asset_id", k)
                            img_name = v.get("file", f"{k}.png")
                            full_img_path = str(assets_dir / img_name)
                            if not os.path.exists(full_img_path) and os.path.exists(str(assets_dir / "assets" / img_name)):
                                full_img_path = str(assets_dir / "assets" / img_name)

                            # Default semantic description from name if empty
                            desc = v.get("semantic_description") or k.replace("_", " ")

                            meta = AssetMetadata(
                                asset_id=aid,
                                file=img_name,
                                image_path=full_img_path if os.path.exists(full_img_path) else None,
                                semantic_description=desc,
                                visual_role=v.get("visual_role", "subject"),
                                action=v.get("action"),
                                objects=v.get("objects", []),
                                state=v.get("state"),
                                dependencies=v.get("dependencies", []),
                                drawing_demand=float(v.get("drawing_demand", 1.8)),
                                orig_box=v.get("orig_box"),
                                orig_size=v.get("orig_size"),
                                area=v.get("area"),
                                row=v.get("row"),
                                col=v.get("col")
                            )
            except Exception:
                pass

        # Also auto-discover any image files on disk not explicitly in metadata.json (e.g. title banner)
        if assets_dir.exists():
            for p in assets_dir.glob("*.png"):
                aid = p.stem
                if aid not in assets:
                    role = "banner" if "banner" in aid or "title" in aid else "subject"
                    assets[aid] = AssetMetadata(
                        asset_id=aid,
                        file=p.name,
                        image_path=str(p),
                        semantic_description=aid.replace("_", " "),
                        visual_role=role,
                        drawing_demand=1.5
                    )

        return cls(
            section_id=section_id,
            script_text=script_text,
            audio_path=audio_path,
            audio_duration=audio_duration,
            words=words,
            sentences=sentences,
            pauses=pauses,
            semantic_beats=semantic_beats,
            initial_drawings=initial_drawings,
            initial_sfx=initial_sfx,
            initial_camera=initial_camera,
            assets=assets
        )
