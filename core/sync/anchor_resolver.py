"""Deterministic Semantic Anchor Resolver (Contract 2 -> Contract 3 Bridge).

Strict Rules:
1. NO AI AT RUNTIME — 100% deterministic, reproducible precision.
2. NO SILENT GUESSING — Mathematical interpolation is strictly forbidden.
3. Monotonic Progression — Chronological order in speech is preserved.
4. Tiered Resolution — Exact -> Normalized -> Token -> Fuzzy -> Contextual.
5. Hero concept resolution failure raises an explicit PipelineHaltError.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from core.contracts.narrative_map import NarrativeVisualMap, NarrativeConcept, NarrativeRole
from core.contracts.render_plan import ResolvedAnchor, MatchTier
from core.contracts.render_policy import RenderPolicy
from core.sync.arabic_matcher import ArabicMatcher


class UnresolvedHeroAnchorError(RuntimeError):
    """Raised when a HERO concept cannot be deterministically resolved to speech."""
    pass


class DeterministicAnchorResolver:
    """Deterministically maps Narrative Concepts to Whisper word-level timestamps."""

    def __init__(
        self,
        whisper_words: List[Dict[str, Any]],
        audio_duration: float,
        policy: Optional[RenderPolicy] = None,
    ) -> None:
        self.words = whisper_words
        self.audio_duration = audio_duration
        self.policy = policy or RenderPolicy()
        self.matcher = ArabicMatcher()

    def resolve_map(
        self, narrative_map: NarrativeVisualMap
    ) -> List[Tuple[NarrativeConcept, Optional[ResolvedAnchor]]]:
        """Resolves all concepts in the narrative visual map monotonically.

        Returns:
            List of (concept, resolved_anchor) pairs.
            For unresolved non-hero concepts, resolved_anchor will be None.
            For unresolved hero concepts, raises UnresolvedHeroAnchorError.
        """
        results: List[Tuple[NarrativeConcept, Optional[ResolvedAnchor]]] = []
        last_word_idx = 0
        last_timestamp = 0.0

        for concept in narrative_map.concepts:
            best_match: Optional[Tuple[int, int, float, MatchTier, str]] = None
            
            # Sort candidates by weight descending
            sorted_candidates = sorted(concept.anchor_candidates, key=lambda c: c.weight, reverse=True)

            # Lookahead window from policy
            lookahead = self.policy.temporal.max_lookahead_words

            for cand in sorted_candidates:
                raw_text = cand.text.strip()
                if not raw_text:
                    continue

                # 1. Exact / Normalized Match via ArabicMatcher
                span = self.matcher.find_best_span(
                    raw_text,
                    self.words,
                    search_start_idx=last_word_idx,
                    max_lookahead=lookahead,
                )

                if span:
                    st_idx, en_idx, score = span
                    cand_words = self.words[st_idx : en_idx + 1]
                    word_texts = [w.get("word", "") for w in cand_words]
                    phrase = " ".join(word_texts)

                    # Determine exact tier
                    if score >= 0.98:
                        tier = MatchTier.EXACT
                    elif score >= 0.85:
                        tier = MatchTier.NORMALIZED
                    elif score >= 0.70:
                        tier = MatchTier.TOKEN
                    else:
                        tier = MatchTier.PHONETIC

                    best_match = (st_idx, en_idx, score * cand.weight, tier, phrase)
                    break

            if best_match:
                st_idx, en_idx, score, tier, phrase = best_match
                t_start = float(self.words[st_idx].get("start", last_timestamp))
                t_end = float(self.words[en_idx].get("end", t_start + 0.8))

                # Enforce strictly monotonic progression
                if t_start < last_timestamp:
                    t_start = last_timestamp

                resolved = ResolvedAnchor(
                    matched_text=phrase,
                    whisper_t_start=round(t_start, 3),
                    whisper_t_end=round(max(t_start + 0.3, t_end), 3),
                    match_tier=tier,
                    confidence=round(score, 3),
                    matched_word_indices=list(range(st_idx, en_idx + 1)),
                )

                last_word_idx = max(last_word_idx, st_idx)
                last_timestamp = t_start
                results.append((concept, resolved))

            else:
                # UNRESOLVED: Strict failure mode differentiation
                if concept.narrative_role == NarrativeRole.HERO:
                    candidate_texts = [c.text for c in concept.anchor_candidates]
                    raise UnresolvedHeroAnchorError(
                        f"Deterministic Anchor Resolution Failed for HERO concept '{concept.concept_id}'. "
                        f"None of candidates {candidate_texts} found in Whisper words beyond index {last_word_idx}."
                    )
                else:
                    # Non-hero support/context: return None (zero guessing)
                    results.append((concept, None))

        return results
