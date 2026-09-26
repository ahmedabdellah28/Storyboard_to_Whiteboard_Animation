from section_timing.visual.drawing_demand import DrawingDemandCalculator
from section_timing.visual.drawing_duration import DrawingDurationEstimator
from section_timing.visual.semantic_beat_mapper import SemanticBeatMapper
from section_timing.timeline.models import SentenceItem, WordItem

def test_drawing_demand_calculation():
    calc = DrawingDemandCalculator()
    # Simple arrow should have low demand
    arrow_demand = calc.compute_demand({"aid": "r1_arrow_connection", "w": 200, "h": 100})
    assert arrow_demand < 0.40

    # Complex scene/character should have high demand
    char_demand = calc.compute_demand({"aid": "r1_character_homeless", "w": 800, "h": 900})
    assert char_demand > 0.60

def test_drawing_duration_estimation():
    est = DrawingDurationEstimator(min_duration_s=0.35, max_duration_s=3.0)
    # Low demand -> fast duration
    assert est.estimate(0.15) < 1.0
    # High demand -> longer duration
    assert est.estimate(0.85) > 2.0

def test_semantic_beat_mapper():
    mapper = SemanticBeatMapper()
    assets = [
        {"aid": "A01_kiwi", "role": "subject"},
        {"aid": "A02_china", "role": "location"}
    ]
    sentences = [
        SentenceItem(id="s001", text="الكيوي أصله من الصين", start=0.0, end=2.5, duration=2.5)
    ]
    words = [
        WordItem(id="w1", text="الكيوي", start=0.0, end=0.6, duration=0.6),
        WordItem(id="w2", text="أصله", start=0.7, end=1.2, duration=0.5),
        WordItem(id="w3", text="الصين", start=1.8, end=2.5, duration=0.7)
    ]

    sem_beats, vis_beats = mapper.map_visual_beats(assets, sentences, words, total_duration=2.5)
    assert len(vis_beats) == 2
    assert vis_beats[0].asset_id == "A01_kiwi"
    assert vis_beats[1].asset_id == "A02_china"
