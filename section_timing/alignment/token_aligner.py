import difflib
from typing import List, Dict, Any, Tuple, Optional
from .arabic_normalizer import ArabicTextNormalizer
from ..timeline.models import WordItem

class TokenAligner:
    """Aligns script tokens to Whisper acoustic tokens using sequence matching and interpolation."""
    def __init__(self, normalizer: Optional[ArabicTextNormalizer] = None):
        self.normalizer = normalizer or ArabicTextNormalizer()

    def align_tokens(
        self,
        script_words: List[str],
        whisper_words: List[WordItem]
    ) -> List[WordItem]:
        """
        Aligns raw script words to Whisper timestamps.
        Produces a 1-to-1 WordItem list for the script, interpolating missing timings.
        """
        if not script_words:
            return []

        if not whisper_words:
            # Fallback if whisper returned 0 words (unlikely)
            return [
                WordItem(
                    id=f"w{i+1:04d}",
                    text=sw,
                    start=round(i * 0.4, 3),
                    end=round((i + 1) * 0.4, 3),
                    duration=0.4,
                    probability=0.5,
                    needs_review=True
                )
                for i, sw in enumerate(script_words)
            ]

        # Normalized representations for matching
        norm_script = [self.normalizer.normalize(w) for w in script_words]
        norm_whisper = [self.normalizer.normalize(w.text) for w in whisper_words]

        matcher = difflib.SequenceMatcher(None, norm_script, norm_whisper)
        matching_blocks = matcher.get_matching_blocks()

        aligned: List[Optional[WordItem]] = [None] * len(script_words)

        for block in matching_blocks:
            for i in range(block.size):
                s_idx = block.a + i
                w_idx = block.b + i
                w_item = whisper_words[w_idx]
                aligned[s_idx] = WordItem(
                    id=f"w{s_idx+1:04d}",
                    text=script_words[s_idx],
                    start=w_item.start,
                    end=w_item.end,
                    duration=w_item.duration,
                    probability=w_item.probability,
                    needs_review=w_item.needs_review
                )

        # Interpolate timings for unaligned script tokens
        last_end = 0.0
        for i in range(len(aligned)):
            if aligned[i] is None:
                # Find next known timestamp
                next_start = None
                for j in range(i + 1, len(aligned)):
                    if aligned[j] is not None:
                        next_start = aligned[j].start
                        break

                if next_start is not None and next_start > last_end:
                    gap = next_start - last_end
                    span_len = 1
                    for k in range(i + 1, len(aligned)):
                        if aligned[k] is None:
                            span_len += 1
                        else:
                            break
                    slot = gap / float(span_len)
                    start_t = round(last_end, 3)
                    end_t = round(last_end + slot, 3)
                else:
                    start_t = round(last_end, 3)
                    end_t = round(last_end + 0.35, 3)

                aligned[i] = WordItem(
                    id=f"w{i+1:04d}",
                    text=script_words[i],
                    start=start_t,
                    end=end_t,
                    duration=round(end_t - start_t, 3),
                    probability=0.60,
                    needs_review=True
                )
                last_end = end_t
            else:
                last_end = aligned[i].end

        return [item for item in aligned if item is not None]
