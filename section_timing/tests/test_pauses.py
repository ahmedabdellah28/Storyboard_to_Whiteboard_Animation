from section_timing.speech.pause_detector import PauseDetector
from section_timing.timeline.models import WordItem

def test_pause_detector():
    detector = PauseDetector(min_pause_s=0.15)
    words = [
        WordItem(id="w1", text="الكيوي", start=0.0, end=0.5, duration=0.5),
        # Gap: 0.5 to 0.7 -> 0.20s (micro_pause)
        WordItem(id="w2", text="أصله", start=0.7, end=1.1, duration=0.4),
        # Gap: 1.1 to 1.7 -> 0.60s (medium_pause)
        WordItem(id="w3", text="الصين", start=1.7, end=2.3, duration=0.6),
    ]

    pauses = detector.detect_pauses(words)
    assert len(pauses) == 2
    assert pauses[0].type == "micro_pause"
    assert pauses[0].duration == 0.20
    assert pauses[1].type == "medium_pause"
    assert pauses[1].duration == 0.60
