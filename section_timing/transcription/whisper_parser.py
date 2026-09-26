from typing import List
from ..timeline.models import WhisperOutput, WordItem

class WhisperParser:
    """Parses Whisper transcript into standardized WordItem sequences."""
    @staticmethod
    def extract_word_items(whisper_data: WhisperOutput) -> List[WordItem]:
        words: List[WordItem] = []
        counter = 1
        for seg in whisper_data.segments:
            for w in seg.words:
                w_id = f"w{counter:04d}"
                dur = max(0.01, w.end - w.start)
                words.append(WordItem(
                    id=w_id,
                    text=w.word,
                    start=w.start,
                    end=w.end,
                    duration=round(dur, 3),
                    probability=w.probability,
                    sentence_id=f"s{seg.id:03d}",
                    needs_review=(w.probability < 0.40)
                ))
                counter += 1
        return words
