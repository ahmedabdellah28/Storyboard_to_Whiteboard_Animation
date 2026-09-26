from pathlib import Path
from section_timing.timeline.models import (
    MasterTimeline,
    WhisperOutput,
    WhisperSegment,
    WhisperWord,
    WordItem,
    SentenceItem,
    PauseItem,
    DrawingItem,
    SFXItem,
    CameraItem,
)
from section_timing.timeline.builder import MasterTimelineBuilder
from section_timing.timeline.exporter import TimelineExporter
from section_timing.debug.debugger import TimingDebugger

def test_master_timeline_assembly_and_export(tmp_path: Path):
    timing_dir = tmp_path / "timing"

    words = [
        WordItem(id="w1", text="الكيوي", start=0.0, end=0.5, duration=0.5),
        WordItem(id="w2", text="لذيذ", start=0.6, end=1.0, duration=0.4)
    ]
    sentences = [
        SentenceItem(id="s1", text="الكيوي لذيذ", start=0.0, end=1.0, duration=1.0, word_ids=["w1", "w2"])
    ]
    pauses = [
        PauseItem(id="p1", start=0.5, end=0.6, duration=0.1, type="micro_pause")
    ]
    drawings = [
        DrawingItem(id="D1", asset_id="A1", start_s=0.0, end_s=0.8, duration_s=0.8)
    ]
    sfx = [
        SFXItem(id="sx1", type="marker_draw", start_s=0.0, end_s=0.6, duration_s=0.6)
    ]
    camera = [
        CameraItem(id="c1", type="pan", start_s=0.0, end_s=0.8, duration_s=0.8)
    ]

    master = MasterTimelineBuilder.build(
        section_id="003",
        duration=1.0,
        audio_file="section.wav",
        script_file="script.txt",
        hashes={"audio": "123"},
        whisper_model="small",
        words=words,
        sentences=sentences,
        pauses=pauses,
        speech_beats=[],
        semantic_beats=[],
        visual_beats=[],
        drawings=drawings,
        sfx=sfx,
        camera=camera
    )

    whisper_output = WhisperOutput(
        audio_path="section.wav",
        duration=1.0,
        language="ar",
        segments=[
            WhisperSegment(id=0, start=0.0, end=1.0, text="الكيوي لذيذ", words=[
                WhisperWord(word="الكيوي", start=0.0, end=0.5, probability=0.99),
                WhisperWord(word="لذيذ", start=0.6, end=1.0, probability=0.98)
            ])
        ]
    )

    paths = TimelineExporter.export_all(timing_dir, master, whisper_output)

    # Check all 11 required files are exported
    expected_files = [
        "whisper.json",
        "words.json",
        "sentences.json",
        "pauses.json",
        "speech_beats.json",
        "semantic_beats.json",
        "visual_beats.json",
        "drawing_timeline.json",
        "sfx_timeline.json",
        "camera_timeline.json",
        "master_timeline.json"
    ]
    for ef in expected_files:
        assert (timing_dir / ef).exists(), f"File {ef} was not exported!"

    # Test Debug report & HTML visualizer
    report_path = TimingDebugger.generate_debug_report(timing_dir, master)
    assert report_path.exists()
    assert (timing_dir / "timeline_debug.html").exists()
