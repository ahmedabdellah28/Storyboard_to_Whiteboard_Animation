import re
from typing import List
from ..timeline.models import WordItem, SentenceItem

class SentenceSegmenter:
    """Segments section text into authentic sentences based on script punctuation and audio word timings."""
    
    PUNCT_SPLIT = re.compile(r'([.?!؟]+|\n+)')

    def segment(self, script_text: str, aligned_words: List[WordItem]) -> List[SentenceItem]:
        """Groups aligned words into complete sentences based on script boundaries."""
        if not aligned_words:
            return []

        # Split script into natural sentence phrases
        raw_lines = [l.strip() for l in script_text.splitlines() if l.strip()]
        sentence_phrases: List[str] = []
        for line in raw_lines:
            parts = re.split(r'([.?!؟]+)', line)
            for i in range(0, len(parts), 2):
                phrase = parts[i].strip()
                punct = parts[i + 1].strip() if i + 1 < len(parts) else ""
                combined = f"{phrase} {punct}".strip()
                if combined:
                    sentence_phrases.append(combined)

        sentences: List[SentenceItem] = []
        word_cursor = 0
        total_words = len(aligned_words)

        for s_idx, phrase in enumerate(sentence_phrases):
            phrase_word_count = len(phrase.split())
            if phrase_word_count == 0:
                continue

            end_cursor = min(total_words, word_cursor + phrase_word_count)
            # If this is the last sentence phrase, sweep up any trailing words
            if s_idx == len(sentence_phrases) - 1:
                end_cursor = total_words

            sentence_words = aligned_words[word_cursor:end_cursor]
            if not sentence_words:
                continue

            s_id = f"s{s_idx+1:03d}"
            # Tag words with sentence_id
            for w in sentence_words:
                w.sentence_id = s_id

            s_start = sentence_words[0].start
            s_end = sentence_words[-1].end
            dur = max(0.01, s_end - s_start)

            sentences.append(SentenceItem(
                id=s_id,
                text=phrase,
                start=round(s_start, 3),
                end=round(s_end, 3),
                duration=round(dur, 3),
                word_ids=[w.id for w in sentence_words],
                confidence=round(sum(w.probability for w in sentence_words) / len(sentence_words), 2)
            ))

            word_cursor = end_cursor

        return sentences
