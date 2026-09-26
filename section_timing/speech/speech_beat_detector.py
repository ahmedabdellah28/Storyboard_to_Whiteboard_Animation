import re
from typing import List
from ..timeline.models import SentenceItem, PauseItem, SpeechBeatItem

class SpeechBeatDetector:
    """Converts acoustic flow and sentence landmarks into discrete speech beats."""
    def detect_beats(
        self,
        sentences: List[SentenceItem],
        pauses: List[PauseItem]
    ) -> List[SpeechBeatItem]:
        beats: List[SpeechBeatItem] = []
        counter = 1
        total_s = len(sentences)

        for idx, s in enumerate(sentences):
            # Categorize sentence beat type
            has_question = bool(re.search(r'[؟?]', s.text))
            has_numbers = bool(re.search(r'\d+', s.text))
            has_surprise = bool(re.search(r'(لكن|المفاجأة|الصدمة|الغريب|تخيل|أغرب|الحقيقة|في الواقع)', s.text))

            if idx == 0:
                b_type = "hook"
                imp = 1.0
            elif idx == total_s - 1:
                b_type = "outro"
                imp = 0.9
            elif has_surprise:
                b_type = "important_fact"
                imp = 0.95
            elif has_numbers or has_question:
                b_type = "main_fact"
                imp = 0.85
            else:
                b_type = "new_idea"
                imp = 0.70

            beats.append(SpeechBeatItem(
                id=f"sb{counter:03d}",
                start=s.start,
                end=s.end,
                type=b_type,
                importance=imp,
                sentence_id=s.id
            ))
            counter += 1

            # Check if there is a medium or long pause after this sentence
            for p in pauses:
                if abs(p.start - s.end) < 0.2 and p.type in ("medium_pause", "long_pause"):
                    beats.append(SpeechBeatItem(
                        id=f"sb{counter:03d}",
                        start=p.start,
                        end=p.end,
                        type="pause",
                        importance=0.40,
                        sentence_id=s.id
                    ))
                    counter += 1
                    break

        return sorted(beats, key=lambda b: b.start)
