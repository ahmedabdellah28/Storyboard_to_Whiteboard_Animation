import json
from pathlib import Path
from typing import Dict, Any
from .models import (
    MasterTimeline,
    WhisperOutput,
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

class TimelineExporter:
    """Exports all 11 individual timeline and evidence JSON files into the timing directory."""
    @staticmethod
    def export_all(
        timing_dir: Path | str,
        master: MasterTimeline,
        whisper_output: WhisperOutput
    ) -> Dict[str, Path]:
        t_dir = Path(timing_dir).resolve()
        t_dir.mkdir(parents=True, exist_ok=True)
        paths = {}

        def _write_json(filename: str, data: Any):
            p = t_dir / filename
            with open(p, "w", encoding="utf-8") as f:
                if hasattr(data, "model_dump_json"):
                    f.write(data.model_dump_json(indent=2))
                else:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            paths[filename] = p

        # 1. whisper.json
        _write_json("whisper.json", whisper_output)

        # 2. words.json
        _write_json("words.json", {"words": [w.model_dump() for w in master.words]})

        # 3. sentences.json
        _write_json("sentences.json", {"sentences": [s.model_dump() for s in master.sentences]})

        # 4. pauses.json
        _write_json("pauses.json", {"pauses": [p.model_dump() for p in master.pauses]})

        # 5. speech_beats.json
        _write_json("speech_beats.json", {"speech_beats": [sb.model_dump() for sb in master.speech_beats]})

        # 6. semantic_beats.json
        _write_json("semantic_beats.json", {"semantic_beats": [sm.model_dump() for sm in master.semantic_beats]})

        # 7. visual_beats.json
        _write_json("visual_beats.json", {"visual_beats": [vb.model_dump() for vb in master.visual_beats]})

        # 8. drawing_timeline.json
        _write_json("drawing_timeline.json", {
            "section_id": master.section_id,
            "duration": master.duration,
            "events": [d.model_dump() for d in master.drawings]
        })

        # 9. sfx_timeline.json
        _write_json("sfx_timeline.json", {"sfx": [sx.model_dump() for sx in master.sfx]})

        # 10. camera_timeline.json
        _write_json("camera_timeline.json", {"camera": [c.model_dump() for c in master.camera]})

        # 11. master_timeline.json
        _write_json("master_timeline.json", master)

        return paths
