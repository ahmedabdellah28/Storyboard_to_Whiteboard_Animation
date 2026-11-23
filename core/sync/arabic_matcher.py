"""Robust Arabic Text Normalizer and Multi-Tier Semantic Matcher for Audio-Visual Alignment.

Handles ASR (Whisper) phonetic and orthographic variances:
- Diacritics (tashkeel), tatweel, punctuation removal
- Hamza unification (أ, إ, آ, ٱ, ء, ئ, ؤ -> ا / normalized forms)
- Taa marbuta and Haa normalization (ة -> ه)
- Alif maksura and Yaa normalization (ى -> ي)
- Strict substring isolation: prevents short prepositions/particles (e.g. 'إن', 'في', 'من') from false-matching inside longer words.
- Multi-token phrase alignment and token-level Levenshtein similarity.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import List, Tuple, Optional


class ArabicMatcher:
    """Normalizes Arabic text and computes tiered matches against Whisper transcripts."""

    @staticmethod
    def normalize(text: str) -> str:
        """Thoroughly normalizes Arabic text for invariant speech-to-visual matching."""
        if not text:
            return ""

        # Unicode NFKC
        text = unicodedata.normalize("NFKC", text)

        # Remove tashkeel (diacritics)
        tashkeel = re.compile(r"[\u0617-\u061A\u064B-\u0652\u0670]")
        text = re.sub(tashkeel, "", text)

        # Normalize alefs (أ, إ, آ, ٱ -> ا)
        text = re.sub(r"[أإآٱ]", "ا", text)

        # Normalize yaa / alef maksura (ى -> ي)
        text = re.sub(r"ى", "ي", text)

        # Normalize taa marbuta (ة -> ه)
        text = re.sub(r"ة", "ه", text)

        # Normalize standalone/on-line hamzas for fuzzy matching
        text = re.sub(r"[ءئؤ]", "ء", text)

        # Remove tatweel (ـ)
        text = re.sub(r"ـ", "", text)

        # Remove punctuation
        text = re.sub(r"[،.؟!:;\(\)\"\'\[\]\{\}/\\«»\-–—]", " ", text)

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @classmethod
    def token_similarity(cls, str1: str, str2: str) -> float:
        """Returns normalized character-level SequenceMatcher ratio."""
        n1 = cls.normalize(str1)
        n2 = cls.normalize(str2)
        if not n1 or not n2:
            return 0.0
        return SequenceMatcher(None, n1, n2).ratio()

    @classmethod
    def are_tokens_fuzzy_match(cls, t1: str, t2: str, threshold: float = 0.72) -> bool:
        """Determines if two tokens match allowing for single-letter ASR phonetic variance."""
        if t1 == t2:
            return True
        # Check affix attached (e.g. و / ف prefix)
        if len(t1) >= 4 and len(t2) >= 4:
            if t1 in t2 and (len(t2) - len(t1) <= 2):
                return True
            if t2 in t1 and (len(t1) - len(t2) <= 2):
                return True
        if len(t1) >= 3 and len(t2) >= 3:
            return SequenceMatcher(None, t1, t2).ratio() >= threshold
        return False

    @classmethod
    def find_best_span(
        cls,
        anchor: str,
        whisper_words: List[dict],
        search_start_idx: int = 0,
        max_lookahead: int = 80,
    ) -> Optional[Tuple[int, int, float]]:
        """Finds the best matching word span [start_idx, end_idx] for an anchor phrase.

        Args:
            anchor: Target phrase or anchor keywords.
            whisper_words: List of Whisper word dicts [{"word": ..., "start": ..., "end": ...}].
            search_start_idx: Starting index in whisper_words (enforces monotonic progress).
            max_lookahead: Maximum number of words to look ahead.

        Returns:
            Tuple of (start_idx, end_idx, confidence) or None.
        """
        norm_anchor = cls.normalize(anchor)
        anchor_tokens = norm_anchor.split()
        if not anchor_tokens or search_start_idx >= len(whisper_words):
            return None

        m = len(anchor_tokens)
        max_search = min(len(whisper_words), search_start_idx + max_lookahead)
        best_score = 0.0
        best_span: Optional[Tuple[int, int, float]] = None

        # Restrict window size around token count
        min_win = max(1, m - 1) if m > 1 else 1
        max_win = m + 2 if m > 1 else 2

        for window_size in range(min_win, max_win + 1):
            for i in range(search_start_idx, max_search - window_size + 1):
                cand_tokens = [
                    cls.normalize(w.get("word", "")) for w in whisper_words[i : i + window_size]
                ]
                cand_str = " ".join(cand_tokens)

                # 1. Exact normalized match
                if cand_str == norm_anchor:
                    return (i, i + window_size - 1, 1.0)

                # 2. Strict affix match: anchor exists inside cand_str as a distinct token/prefix
                if m == 1:
                    # Single word anchor: check exact match or close fuzzy match
                    sim = cls.token_similarity(cand_tokens[0], anchor_tokens[0])
                    if sim >= 0.85:
                        return (i, i + window_size - 1, round(sim, 3))
                    if sim > best_score and sim >= 0.82:
                        best_score = sim
                        best_span = (i, i + window_size - 1, round(sim, 3))
                else:
                    # Multi-token anchor
                    # Full phrase contained in candidate string
                    if norm_anchor in cand_str and len(cand_str) <= len(norm_anchor) + 4:
                        return (i, i + window_size - 1, 0.98)

                    # Token overlap with fuzzy comparison
                    shared = 0
                    for at in anchor_tokens:
                        if any(cls.are_tokens_fuzzy_match(at, ct) for ct in cand_tokens):
                            shared += 1

                    overlap_ratio = shared / float(len(anchor_tokens))
                    if overlap_ratio >= 0.60:
                        sim = cls.token_similarity(cand_str, norm_anchor)
                        composite = overlap_ratio * 0.70 + sim * 0.30
                        if composite > best_score and composite >= 0.65:
                            best_score = composite
                            best_span = (i, i + window_size - 1, round(composite, 3))

        return best_span
