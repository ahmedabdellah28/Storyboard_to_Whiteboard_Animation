from section_timing.visual.beat_solver import BeatSolver
from section_timing.timeline.models import VisualBeatItem, SpeechAnchor, PauseItem

def test_beat_solver_lead_in_and_constraints():
    solver = BeatSolver(max_lead_in_s=0.5, allow_overlap=True)
    
    # Asset A01 has anchor from 1.0 to 1.5 (span = 0.5s), but drawing takes ~1.2s
    # Solver must start drawing before 1.0 (lead-in)
    beats = [
        VisualBeatItem(
            id="vb1",
            asset_id="A01_character",
            speech_anchor=SpeechAnchor(text="تصحى", start=1.0, end=1.5),
            action="draw"
        ),
        VisualBeatItem(
            id="vb2",
            asset_id="A02_arrow",
            speech_anchor=SpeechAnchor(text="الشارع", start=2.5, end=3.0),
            action="connect"
        )
    ]
    assets = [
        {"aid": "A01_character", "drawing_demand": 0.75},
        {"aid": "A02_arrow", "drawing_demand": 0.20, "depends_on": ["A01_character"]}
    ]
    pauses = [
        PauseItem(id="p1", start=0.6, end=1.0, duration=0.4, type="short_pause")
    ]

    drawings = solver.solve(beats, assets, pauses, section_duration=5.0)
    assert len(drawings) == 2

    # A01 drawing starts before speech anchor (lead-in into pause)
    d1 = drawings[0]
    assert d1.start_s < 1.0
    assert d1.start_s >= 0.0

    # A02 depends on A01, so A02 start must be >= A01 end
    d2 = drawings[1]
    assert d2.start_s >= d1.end_s - 0.05
    assert d2.end_s <= 5.0
