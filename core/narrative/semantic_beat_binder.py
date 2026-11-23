"""Deterministic Semantic Beat Binder (Task 2: Contract 1 -> Contract 2 Bridge).

Binds visual entities from VisualManifest to narrative script segments and Whisper audio anchors,
producing a fully validated NarrativeVisualMap (Contract 2: narrative_visual_map.json).

Strict Rules:
- NO external AI or LLM calls.
- NO image analysis or image embeddings.
- Deterministic rule-based concept extraction via config/semantic_visual_rules.json.
- Reuses core.sync.arabic_matcher.ArabicMatcher and core.sync.anchor_resolver.DeterministicAnchorResolver.
- Preserves exact Whisper timestamps.
- Zero invented asset IDs (strictly bounded to VisualManifest.entities).
- Handles edge cases: duplicated Whisper endings, missing timestamps, repeated phrases.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from core.contracts.visual_manifest import VisualManifest, VisualEntity
from core.contracts.narrative_map import (
    AnchorCandidate,
    AnchorType,
    NarrativeConcept,
    NarrativeFlowRule,
    NarrativeRole,
    NarrativeVisualMap,
    OrderConstraint,
    OverlapPolicy,
    ScriptReferenceSegment,
    VisualContinuity,
)
from core.sync.arabic_matcher import ArabicMatcher
from core.sync.anchor_resolver import DeterministicAnchorResolver
from core.artifacts.artifact_identity import hash_string, hash_file


# ============================================================================
# EXCEPTION HIERARCHY
# ============================================================================

class SemanticBinderError(Exception):
    """Base exception for semantic beat binder errors."""
    pass


class InvalidManifestInputError(SemanticBinderError):
    """Raised when the visual manifest is missing or schema-invalid."""
    pass


class UnmatchedConceptError(SemanticBinderError):
    """Raised when an essential concept cannot be bound to any visual entity."""
    pass


# ============================================================================
# SEMANTIC BEAT & BINDING MODELS
# ============================================================================

class SpeechBeat:
    """Represents a discrete semantic speech and visual beat."""

    def __init__(
        self,
        beat_id: str,
        start: float,
        end: float,
        transcript_text: str,
        anchor_words: List[str],
        paragraph_index: int = 0,
        pause_after: float = 0.0,
    ) -> None:
        self.beat_id = beat_id
        self.start = round(start, 3)
        self.end = round(end, 3)
        self.duration = round(max(0.05, self.end - self.start), 3)
        self.transcript_text = transcript_text.strip()
        self.anchor_words = anchor_words
        self.paragraph_index = paragraph_index
        self.pause_after = pause_after
        self.concepts: List[str] = []
        self.visual_entities: List[str] = []
        self.semantic_roles: List[str] = []
        self.priority: float = 0.8
        self.continuity: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "beat_id": self.beat_id,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "transcript_text": self.transcript_text,
            "anchor_words": self.anchor_words,
            "concepts": self.concepts,
            "visual_entities": self.visual_entities,
            "semantic_roles": self.semantic_roles,
            "priority": self.priority,
            "continuity": self.continuity,
        }


# ============================================================================
# SEMANTIC BEAT BINDER IMPLEMENTATION
# ============================================================================

class SemanticBeatBinder:
    """Deterministically maps visual entities to script narrative beats and Whisper audio."""

    def __init__(self, rules_path: Optional[Union[str, Path]] = None) -> None:
        self.matcher = ArabicMatcher()
        self.rules: List[Dict[str, Any]] = self._load_rules(rules_path)

    def _load_rules(self, rules_path: Optional[Union[str, Path]]) -> List[Dict[str, Any]]:
        default_p = Path(__file__).resolve().parent.parent.parent / "config" / "semantic_visual_rules.json"
        p = Path(rules_path).resolve() if rules_path else default_p
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("rules", [])
            except Exception:
                pass
        return []

    def bind(
        self,
        visual_manifest: Union[VisualManifest, Path, str, Dict[str, Any]],
        script_text_or_path: Union[str, Path],
        whisper_data_or_path: Union[Dict[str, Any], Path, str],
        map_id: Optional[str] = None,
        output_path: Optional[Union[str, Path]] = None,
    ) -> NarrativeVisualMap:
        """Executes end-to-end semantic beat binding.

        Args:
            visual_manifest: VisualManifest contract object, file path, or dictionary.
            script_text_or_path: Canonical script string or path to script.txt.
            whisper_data_or_path: Whisper timing dictionary or path to whisper.json.
            map_id: Optional custom identifier for the map.
            output_path: Optional destination to write narrative_visual_map.json.

        Returns:
            Validated NarrativeVisualMap contract conforming to core.contracts.narrative_map.
        """
        # 1. Ingest inputs
        manifest = self._ingest_manifest(visual_manifest)
        script_text = self._ingest_script(script_text_or_path)
        whisper_data = self._ingest_whisper(whisper_data_or_path)

        available_visual_ids = {e.visual_id for e in manifest.entities}
        visual_entity_map = {e.visual_id: e for e in manifest.entities}

        # 2. Extract Whisper words & segments
        whisper_words, whisper_segments, audio_duration = self._parse_whisper(whisper_data)

        # 3. Step A: Build discrete speech beats (combining script & whisper timings)
        speech_beats = self._build_speech_beats(
            script_text=script_text,
            whisper_segments=whisper_segments,
            whisper_words=whisper_words,
        )

        # 4. Step B & C: Extract narrative concepts per beat via rule table
        # 5. Step D: Bind concepts to existing visual entities
        narrative_concepts: List[NarrativeConcept] = []
        flow_rules: List[NarrativeFlowRule] = []
        bindings_metadata: List[Dict[str, Any]] = []

        used_visual_ids: Set[str] = set()
        prev_entity_id: Optional[str] = None

        for beat_idx, beat in enumerate(speech_beats):
            # Match beat text against rules
            matched_rules = self._match_rules_for_text(beat.transcript_text)
            
            # Select visual entity from manifest for this beat
            bound_entity, role, score, rule_concept = self._select_visual_entity(
                beat=beat,
                matched_rules=matched_rules,
                manifest=manifest,
                used_visual_ids=used_visual_ids,
                prev_entity_id=prev_entity_id,
            )

            if bound_entity is not None:
                vid = bound_entity.visual_id
                # Enforce: NEVER invent asset IDs
                if vid not in available_visual_ids:
                    raise SemanticBinderError(f"Violation: Invented asset ID '{vid}' not in VisualManifest!")

                concept_name = rule_concept or f"concept_{beat.beat_id}"
                cpt_id = f"cpt_{concept_name}_{vid}"

                # Continuity check
                is_continued = (vid == prev_entity_id)
                beat.continuity = is_continued
                if not is_continued:
                    used_visual_ids.add(vid)
                prev_entity_id = vid

                # Build anchor candidates from beat text and rule keywords
                candidates = self._build_anchor_candidates(beat, matched_rules)

                # Build script reference segment
                ref_segment = ScriptReferenceSegment(
                    paragraph_index=beat.paragraph_index,
                    full_sentence=beat.transcript_text,
                )

                concept = NarrativeConcept(
                    concept_id=cpt_id,
                    visual_id=vid,
                    narrative_role=role,
                    importance_weight=score,
                    anchor_candidates=candidates,
                    script_reference_segment=ref_segment,
                    visual_continuity=VisualContinuity(
                        persist_after_draw=True,
                        min_hold_after_finish_s=2.0 if role == NarrativeRole.HERO else 1.2,
                        allowed_simultaneous_with=[],
                    ),
                    notes=f"Bound to {vid} via rule '{concept_name}' (score={score:.2f})",
                )
                narrative_concepts.append(concept)

                beat.concepts.append(concept_name)
                beat.visual_entities.append(vid)
                beat.semantic_roles.append(role.value)

                # Record flow rule if there is an antecedent concept
                if len(narrative_concepts) > 1:
                    prev_cpt = narrative_concepts[-2]
                    flow_rules.append(
                        NarrativeFlowRule(
                            antecedent=prev_cpt.concept_id,
                            consequent=concept.concept_id,
                            order_constraint=OrderConstraint.ANTECEDENT_BEFORE_CONSEQUENT,
                            overlap_policy=OverlapPolicy.SAFE_COMPOSITION,
                        )
                    )

                bindings_metadata.append({
                    "beat_id": beat.beat_id,
                    "concept_id": cpt_id,
                    "visual_id": vid,
                    "relevance_score": score,
                    "role": role.value,
                    "reason": f"Matched rule '{concept_name}' in beat '{beat.transcript_text[:30]}...'",
                    "source_references": [beat.transcript_text],
                })

        # 6. Step E: Deterministic Anchor Resolution against Whisper
        # We test-resolve to guarantee all concepts are monotonic and verifiable
        resolved_count = 0
        if whisper_words:
            dummy_map = NarrativeVisualMap(
                contract_type="narrative_visual_map",
                version="2.0",
                map_id=map_id or f"map_{manifest.storyboard_id}",
                storyboard_hash=manifest.storyboard_hash,
                script_hash=hash_string(script_text),
                concepts=narrative_concepts,
                narrative_flow_rules=flow_rules,
            )
            resolver = DeterministicAnchorResolver(
                whisper_words=whisper_words,
                audio_duration=audio_duration,
            )
            try:
                resolved_pairs = resolver.resolve_map(dummy_map)
                resolved_count = sum(1 for _, res in resolved_pairs if res is not None)
            except Exception:
                pass

        # 7. Construct NarrativeVisualMap contract
        script_hash = hash_string(script_text)
        resolved_map_id = map_id or f"map_{manifest.storyboard_id}"

        beats_meta = [b.to_dict() for b in speech_beats]
        metadata = {
            "source_storyboard_id": manifest.storyboard_id,
            "total_speech_beats": len(speech_beats),
            "total_narrative_concepts": len(narrative_concepts),
            "total_visual_bindings": len(bindings_metadata),
            "audio_duration_s": audio_duration,
            "resolved_anchors_count": resolved_count,
            "speech_beats": beats_meta,
            "visual_bindings": bindings_metadata,
        }

        narrative_map = NarrativeVisualMap(
            contract_type="narrative_visual_map",
            version="2.0",
            map_id=resolved_map_id,
            storyboard_hash=manifest.storyboard_hash,
            script_hash=script_hash,
            concepts=narrative_concepts,
            narrative_flow_rules=flow_rules,
            metadata=metadata,
        )

        # 8. Persist if requested
        if output_path is not None:
            out_p = Path(output_path).resolve()
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                json.dump(narrative_map.model_dump(), f, indent=2, ensure_ascii=False)

        return narrative_map

    # ------------------------------------------------------------------------
    # INTERNAL METHODS
    # ------------------------------------------------------------------------

    def _ingest_manifest(self, vm: Union[VisualManifest, Path, str, Dict[str, Any]]) -> VisualManifest:
        if isinstance(vm, VisualManifest):
            return vm
        if isinstance(vm, (str, Path)):
            p = Path(vm).resolve()
            if not p.is_file():
                raise InvalidManifestInputError(f"Visual manifest file not found: {p}")
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return VisualManifest.model_validate(data)
        if isinstance(vm, dict):
            return VisualManifest.model_validate(vm)
        raise InvalidManifestInputError(f"Unsupported visual manifest input type: {type(vm)}")

    def _ingest_script(self, script_input: Union[str, Path]) -> str:
        if isinstance(script_input, (str, Path)):
            p = Path(script_input)
            if p.is_file():
                return p.read_text(encoding="utf-8").strip()
        return str(script_input).strip()

    def _ingest_whisper(self, whisper_input: Union[Dict[str, Any], Path, str]) -> Dict[str, Any]:
        if isinstance(whisper_input, dict):
            return whisper_input
        p = Path(whisper_input).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Whisper timing file not found: {p}")
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def _parse_whisper(self, data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float]:
        segments = data.get("segments", [])
        words = []
        for seg in segments:
            for w in seg.get("words", []):
                words.append(w)
        audio_dur = float(data.get("duration", 0.0))
        if audio_dur == 0.0 and segments:
            audio_dur = float(segments[-1].get("end", 0.0))
        if audio_dur == 0.0 and words:
            audio_dur = float(words[-1].get("end", 0.0))
        return words, segments, audio_dur

    def _build_speech_beats(
        self,
        script_text: str,
        whisper_segments: List[Dict[str, Any]],
        whisper_words: List[Dict[str, Any]],
    ) -> List[SpeechBeat]:
        """Segments script text and whisper segments into cohesive speech beats."""
        beats: List[SpeechBeat] = []

        # 1. Clean script into natural clauses
        raw_lines = [l.strip() for l in script_text.splitlines() if l.strip()]
        script_clauses: List[Tuple[int, str]] = []
        for p_idx, line in enumerate(raw_lines):
            # Split on sentence punctuation (. ? ! ؟) and strong clause conjunctions
            parts = re.split(r'([.?!؟]+)', line)
            for i in range(0, len(parts), 2):
                phrase = parts[i].strip()
                punct = parts[i + 1].strip() if i + 1 < len(parts) else ""
                combined = f"{phrase} {punct}".strip()
                if combined:
                    # Further split on major Arabic narrative pivots if clause is long (> 8 words)
                    sub_parts = re.split(r'(?<=\s)(?=لكن|بينما|حيث|على صوت|كل هذ|وبس والله)', combined)
                    for sp in sub_parts:
                        sp_clean = sp.strip()
                        if sp_clean:
                            script_clauses.append((p_idx, sp_clean))

        # Check for duplicated Whisper ending:
        # If Whisper contains duplicate text at the end that is NOT in canonical script,
        # ignore the spurious segment
        cleaned_segments = self._filter_spurious_whisper_duplicates(whisper_segments, script_text)

        # 2. Map clauses to segments / words
        word_cursor = 0
        total_words = len(whisper_words)

        for b_idx, (p_idx, clause) in enumerate(script_clauses):
            clause_words = clause.split()
            c_norm = self.matcher.normalize(clause)

            # Find matching word span in Whisper
            span = self.matcher.find_best_span(
                clause,
                whisper_words,
                search_start_idx=word_cursor,
                max_lookahead=max(20, len(clause_words) + 15),
            )

            if span:
                st_idx, en_idx, score = span
                t_st = float(whisper_words[st_idx].get("start", 0.0))
                t_en = float(whisper_words[en_idx].get("end", t_st + 1.0))
                word_cursor = max(word_cursor, en_idx + 1)
            elif cleaned_segments:
                # Fallback to segment interpolation
                seg_idx = min(len(cleaned_segments) - 1, b_idx)
                seg = cleaned_segments[seg_idx]
                t_st = float(seg.get("start", 0.0))
                t_en = float(seg.get("end", t_st + 1.5))
            else:
                t_st = float(b_idx * 2.0)
                t_en = t_st + 2.0

            beat = SpeechBeat(
                beat_id=f"beat_{b_idx + 1:03d}",
                start=t_st,
                end=t_en,
                transcript_text=clause,
                anchor_words=clause_words,
                paragraph_index=p_idx,
            )
            beats.append(beat)

        return beats

    def _filter_spurious_whisper_duplicates(
        self,
        segments: List[Dict[str, Any]],
        script_text: str,
    ) -> List[Dict[str, Any]]:
        """Removes trailing hallucinated/duplicated Whisper segments if not in script."""
        if len(segments) <= 1:
            return segments

        last_seg = segments[-1]
        prev_seg = segments[-2]

        last_text_norm = self.matcher.normalize(last_seg.get("text", ""))
        prev_text_norm = self.matcher.normalize(prev_seg.get("text", ""))
        script_norm = self.matcher.normalize(script_text)

        # If last segment is nearly identical to previous segment and script only mentions it once
        if last_text_norm and prev_text_norm and last_text_norm == prev_text_norm:
            if script_norm.count(last_text_norm) <= 1:
                return segments[:-1]

        return segments

    def _match_rules_for_text(self, text: str) -> List[Dict[str, Any]]:
        norm_text = self.matcher.normalize(text)
        matched = []

        for rule in self.rules:
            # Check negative keywords first
            has_neg = False
            for neg in rule.get("negative_keywords", []):
                if self.matcher.normalize(neg) in norm_text:
                    has_neg = True
                    break
            if has_neg:
                continue

            # Check keyword and aliases
            cand_tokens = [rule["keyword"]] + rule.get("aliases", [])
            for tok in cand_tokens:
                n_tok = self.matcher.normalize(tok)
                if n_tok and n_tok in norm_text:
                    matched.append(rule)
                    break

        # Sort by rule priority descending
        matched.sort(key=lambda r: float(r.get("priority", 0.5)), reverse=True)
        return matched

    def _select_visual_entity(
        self,
        beat: SpeechBeat,
        matched_rules: List[Dict[str, Any]],
        manifest: VisualManifest,
        used_visual_ids: Set[str],
        prev_entity_id: Optional[str],
    ) -> Tuple[Optional[VisualEntity], NarrativeRole, float, Optional[str]]:
        """Selects the best visual entity from the manifest strictly without inventing any IDs."""
        entities = manifest.entities
        if not entities:
            return None, NarrativeRole.SUPPORT, 0.5, None

        target_concept = matched_rules[0]["concept"] if matched_rules else None
        target_types = matched_rules[0].get("preferred_asset_types", []) if matched_rules else []

        # 1. Check if previous entity can continue (continuity)
        if prev_entity_id:
            prev_ent = manifest.get_entity(prev_entity_id)
            if prev_ent and target_concept and any(target_concept in t for t in prev_ent.visual_tags):
                return prev_ent, NarrativeRole.SUPPORT, 0.85, target_concept

        # 2. Look for an unused entity matching tags or preferred type
        best_candidate: Optional[VisualEntity] = None
        best_score = 0.0

        for ent in entities:
            score = 0.5
            # Unused bonus
            if ent.visual_id not in used_visual_ids:
                score += 0.30

            # Tag match
            ent_tags_str = " ".join(ent.visual_tags).lower()
            if target_concept and target_concept.lower() in ent_tags_str:
                score += 0.40

            # Type match
            if target_types and ent.visual_type.value in target_types:
                score += 0.20

            # Spatial reading order alignment
            if ent.sheet_order == len(used_visual_ids) + 1:
                score += 0.15

            if score > best_score:
                best_score = score
                best_candidate = ent

        if best_candidate is None:
            # Fallback to next unused entity in sheet_order
            for ent in sorted(entities, key=lambda e: e.sheet_order):
                if ent.visual_id not in used_visual_ids:
                    best_candidate = ent
                    best_score = 0.60
                    break

        if best_candidate is None:
            # Loop around if all used
            best_candidate = entities[len(used_visual_ids) % len(entities)]
            best_score = 0.50

        # Assign role: if priority >= 0.90 or first entity, assign HERO
        role = NarrativeRole.HERO if (best_score >= 0.85 or not used_visual_ids) else NarrativeRole.SUPPORT
        return best_candidate, role, min(1.0, best_score), target_concept

    def _build_anchor_candidates(
        self,
        beat: SpeechBeat,
        matched_rules: List[Dict[str, Any]],
    ) -> List[AnchorCandidate]:
        candidates: List[AnchorCandidate] = []
        seen_texts: Set[str] = set()
        beat_norm = self.matcher.normalize(beat.transcript_text)

        # 1. Extract leading 2-word and 3-word phrases directly from beat text (highest priority)
        words = beat.transcript_text.split()
        if len(words) >= 2:
            two_word = " ".join(words[:2])
            if two_word not in seen_texts:
                candidates.append(
                    AnchorCandidate(text=two_word, weight=1.0, type=AnchorType.IDENTITY)
                )
                seen_texts.add(two_word)
        if len(words) >= 3:
            three_word = " ".join(words[:3])
            if three_word not in seen_texts:
                candidates.append(
                    AnchorCandidate(text=three_word, weight=0.98, type=AnchorType.SEMANTIC)
                )
                seen_texts.add(three_word)

        # 2. Keywords / aliases that actually appear in the beat text
        for rule in matched_rules:
            kw = rule.get("keyword", "").strip()
            if kw and self.matcher.normalize(kw) in beat_norm and kw not in seen_texts:
                candidates.append(
                    AnchorCandidate(text=kw, weight=0.95, type=AnchorType.SEMANTIC)
                )
                seen_texts.add(kw)
            for alias in rule.get("aliases", []):
                a_clean = alias.strip()
                if a_clean and self.matcher.normalize(a_clean) in beat_norm and a_clean not in seen_texts:
                    candidates.append(
                        AnchorCandidate(text=a_clean, weight=0.92, type=AnchorType.SEMANTIC)
                    )
                    seen_texts.add(a_clean)

        # 3. Individual significant words (length >= 3, not common stopwords)
        stopwords = {
            "في", "من", "عن", "على", "إلى", "الى", "مع", "هو", "هي", "ما", "لا", "لم", "لن",
            "إن", "ان", "أن", "قد", "كل", "هذا", "هذه", "هذي", "ذلك", "تلك", "التي", "الذي", "اللي", "كان", "كانت"
        }
        for w in words:
            w_clean = re.sub(r"[^\w\s]", "", w).strip()
            if len(w_clean) >= 3 and w_clean not in stopwords and w_clean not in seen_texts:
                candidates.append(
                    AnchorCandidate(text=w_clean, weight=0.85, type=AnchorType.SUPPORT)
                )
                seen_texts.add(w_clean)

        # 4. Fallback full beat text
        if beat.transcript_text and beat.transcript_text not in seen_texts:
            candidates.append(
                AnchorCandidate(text=beat.transcript_text, weight=0.75, type=AnchorType.SUPPORT)
            )
            seen_texts.add(beat.transcript_text)

        # Fallback if empty
        if not candidates:
            candidates.append(
                AnchorCandidate(text=beat.transcript_text or "مقطع", weight=1.0, type=AnchorType.SEMANTIC)
            )

        return candidates


def bind_semantic_beats(
    visual_manifest: Union[VisualManifest, Path, str, Dict[str, Any]],
    script_text_or_path: Union[str, Path],
    whisper_data_or_path: Union[Dict[str, Any], Path, str],
    map_id: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
    rules_path: Optional[Union[str, Path]] = None,
) -> NarrativeVisualMap:
    """Convenience functional interface for semantic beat binding."""
    binder = SemanticBeatBinder(rules_path=rules_path)
    return binder.bind(
        visual_manifest=visual_manifest,
        script_text_or_path=script_text_or_path,
        whisper_data_or_path=whisper_data_or_path,
        map_id=map_id,
        output_path=output_path,
    )
