"""Motion Design Grammar Engine (Phase 3 of AION Creative Studio V5).

Maps narrative intent, semantic meaning, and pacing cues into concrete visual
motion-graphics treatments instead of mechanical time-interval rules.
Supports all 15 narrative intents across Arabic & English storyboards/scripts
and enforces visual diversity across consecutive narrative beats.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SEMANTIC_RULES_PATH = ROOT_DIR / "config" / "semantic_visual_rules.json"

NARRATIVE_INTENTS: Tuple[str, ...] = (
    "introduction",
    "concept_reveal",
    "cause_and_effect",
    "comparison",
    "timeline",
    "process_flow",
    "problem_and_solution",
    "psychological_illusion",
    "historical_event",
    "dramatic_climax",
    "emotional_shift",
    "hierarchy",
    "abstract_idea",
    "data_or_statistic",
    "conclusion",
)

# Color moods tuned against AGENTS.md & Visual QA dark/warm contrast rules.
PALETTES: Dict[str, Dict[str, Any]] = {
    "deep_studio_slate": {
        "name": "deep_studio_slate",
        "bg": "#0F172A",
        "surface": "#1E293B",
        "primary": "#38BDF8",
        "accent": "#FFD400",
        "secondary": "#00D4C0",
        "danger": "#F43F5E",
        "text": "#F8FAFC",
        "text_muted": "#94A3B8",
        "is_light_bg": False,
    },
    "warm_editorial_paper": {
        "name": "warm_editorial_paper",
        "bg": "#EDE8E0",
        "surface": "#E2DBD0",
        "primary": "#0F172A",
        "accent": "#0072CE",
        "secondary": "#00A99D",
        "danger": "#DC2626",
        "text": "#0B0C10",
        "text_muted": "#475569",
        "is_light_bg": True,
    },
    "scientific_obsidian": {
        "name": "scientific_obsidian",
        "bg": "#0B1120",
        "surface": "#162033",
        "primary": "#00D4C0",
        "accent": "#F59E0B",
        "secondary": "#60A5FA",
        "danger": "#EF4444",
        "text": "#F1F5F9",
        "text_muted": "#94A3B8",
        "is_light_bg": False,
    },
    "cinematic_amber_noir": {
        "name": "cinematic_amber_noir",
        "bg": "#141118",
        "surface": "#241E2B",
        "primary": "#F59E0B",
        "accent": "#FB7185",
        "secondary": "#38BDF8",
        "danger": "#EF4444",
        "text": "#FAF5FF",
        "text_muted": "#C4B5FD",
        "is_light_bg": False,
    },
}

_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "introduction": ["مرحبا", "تخيل", "هل تعلم", "اليوم", "مقدمة", "تساؤل", "imagine", "welcome", "have you ever", "today"],
    "concept_reveal": ["الفكرة", "المفهوم", "يعني", "السر", "الحقيقة", "ببساطة", "تسمى", "concept", "means", "secret", "reveal"],
    "cause_and_effect": ["لذلك", "نتيجة", "بسبب", "يؤدي", "تأثير", "ينتج", "يسبب", "because", "therefore", "leads to", "causes", "effect"],
    "comparison": ["مقارنة", "بينما", "عكس", "بدلا", "مقابل", "الفرق", "أكثر من", "vs", "versus", "whereas", "unlike", "compare"],
    "timeline": ["تاريخ", "عام", "سنة", "مرور الوقت", "قرن", "أولا", "ثم", "بعدها", "timeline", "year", "century", "over time", "era"],
    "process_flow": ["خطوة", "مرحلة", "يمر", "آلية", "كيف يعمل", "سير", "تسلسل", "شبكة", "إشارة", "step", "process", "flow", "pipeline", "signal"],
    "problem_and_solution": ["مشكلة", "خلل", "الحل", "علاج", "تحدي", "تصحيح", "فخ", "problem", "glitch", "solution", "fix", "challenge"],
    "psychological_illusion": ["وهم", "خداع", "دماغ", "عقل", "إدراك", "تفسير", "باريدوليا", "ماكغورك", "illusion", "perception", "brain", "trick", "bias"],
    "historical_event": ["قديما", "تاريخيا", "معركة", "قصة", "اكتشاف", "حضارة", "مخطوطة", "ancient", "history", "historical", "discovery"],
    "dramatic_climax": ["صدمة", "فجأة", "انفجار", "كارثة", "خطير", "لحظة الحسم", "تحول", "shock", "suddenly", "climax", "critical", "twist"],
    "emotional_shift": ["خوف", "أمل", "راحة", "قلق", "شعور", "هدوء", "حزن", "fear", "hope", "relief", "calm", "emotion", "anxiety"],
    "hierarchy": ["هرم", "مستوى", "أولوية", "ترتيب", "طبقة", "أعلى", "أساس", "hierarchy", "layer", "tier", "pyramid", "priority"],
    "abstract_idea": ["معنى", "فلسفة", "رمز", "وعي", "زمن", "حرية", "عدالة", "abstract", "meaning", "symbol", "consciousness"],
    "data_or_statistic": ["بالمئة", "%", "مليون", "ألف", "دراسة", "إحصائية", "نسبة", "رقم", "percent", "million", "data", "stat", "ratio"],
    "conclusion": ["أخيرا", "الخلاصة", "تذكر", "في النهاية", "النتيجة", "باختصار", "summary", "finally", "remember", "conclusion", "takeaway"],
}

_CONCEPT_TO_INTENT: Dict[str, str] = {
    "pareidolia_vision": "psychological_illusion",
    "phantom_vibration": "psychological_illusion",
    "memory_reconstruction": "process_flow",
    "inattentional_blindness": "dramatic_climax",
    "sensory_agreement": "comparison",
    "spotlight_effect": "psychological_illusion",
    "reality_interpretation": "concept_reveal",
    "camera_analogy": "comparison",
    "realization": "dramatic_climax",
    "distraction": "problem_and_solution",
    "thinking": "process_flow",
    "confusion": "emotional_shift",
}

_TREATMENT_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "introduction": [
        {
            "treatment_id": "editorial_hook_reveal",
            "grammar_family": "kinetic_statement",
            "visual_metaphor": "mask_aperture_open_with_hero_focal",
            "graphic_elements": ["mask_wipe", "hero_asset_or_icon", "kinetic_title"],
            "capabilities": ["masks", "arabic_rtl_text", "camera_motion"],
            "camera_profile": "slow_push_in",
            "lighting_profile": "soft_editorial_sweep",
            "palette": "deep_studio_slate",
            "pacing": "curious_open",
            "sfx_cue": "whoosh",
        },
        {
            "treatment_id": "depth_stage_establishing",
            "grammar_family": "cinematic_parallax_reveal",
            "visual_metaphor": "layered_2_5d_backdrop_with_focal_emblem",
            "graphic_elements": ["depth_plane", "hero_asset_or_icon", "subtitle_badge"],
            "capabilities": ["layer_2_5d", "camera_motion", "lights_and_shadows"],
            "camera_profile": "establishing_orbit",
            "lighting_profile": "dramatic_key_spot",
            "palette": "cinematic_amber_noir",
            "pacing": "cinematic_breathe",
            "sfx_cue": "glint",
        },
    ],
    "concept_reveal": [
        {
            "treatment_id": "callout_anatomy",
            "grammar_family": "explanatory_diagram",
            "visual_metaphor": "bezier_callout_line_to_annotated_concept",
            "graphic_elements": ["hero_asset_or_icon", "bezier_connector", "arrow_path", "keyword_badge"],
            "capabilities": ["bezier_path", "trim_paths", "arrow_path", "arabic_rtl_text"],
            "camera_profile": "focus_center_drift",
            "lighting_profile": "clean_rim_sweep",
            "palette": "scientific_obsidian",
            "pacing": "clear_reveal",
            "sfx_cue": "pop",
        },
        {
            "treatment_id": "luma_mask_unveil",
            "grammar_family": "track_matte_unveil",
            "visual_metaphor": "geometric_wipe_revealing_core_idea",
            "graphic_elements": ["track_matte", "hero_asset_or_icon", "kinetic_title"],
            "capabilities": ["track_mattes", "shape_layer", "arabic_rtl_text"],
            "camera_profile": "subtle_zoom_settle",
            "lighting_profile": "soft_editorial_sweep",
            "palette": "warm_editorial_paper",
            "pacing": "crisp_reveal",
            "sfx_cue": "card_snap",
        },
    ],
    "cause_and_effect": [
        {
            "treatment_id": "causal_arrow_bridge",
            "grammar_family": "causal_chain",
            "visual_metaphor": "source_node_triggers_curved_arrow_to_effect_node",
            "graphic_elements": ["flowchart_node_a", "arrow_path", "flowchart_node_b", "ripple_pulse"],
            "capabilities": ["bezier_path", "trim_paths", "arrow_path", "glow"],
            "camera_profile": "follow_vector_pan",
            "lighting_profile": "target_spotlight_shift",
            "palette": "deep_studio_slate",
            "pacing": "impulse_reaction",
            "sfx_cue": "whoosh",
        },
    ],
    "comparison": [
        {
            "treatment_id": "dual_polarity_columns",
            "grammar_family": "split_polarity",
            "visual_metaphor": "vertical_divider_contrasting_left_vs_right",
            "graphic_elements": ["comparison_panel", "divider_trim_line", "dual_badges"],
            "capabilities": ["shape_layer", "trim_paths", "masks", "arabic_rtl_text"],
            "camera_profile": "balanced_static_tilt",
            "lighting_profile": "dual_accent_rim",
            "palette": "warm_editorial_paper",
            "pacing": "alternating_beats",
            "sfx_cue": "card_snap",
        },
        {
            "treatment_id": "wipe_before_after",
            "grammar_family": "split_polarity",
            "visual_metaphor": "animated_mask_sweeping_between_states",
            "graphic_elements": ["mask_wipe", "comparison_panel", "arrow_path"],
            "capabilities": ["masks", "shape_layer", "arabic_rtl_text"],
            "camera_profile": "subtle_zoom_settle",
            "lighting_profile": "soft_editorial_sweep",
            "palette": "deep_studio_slate",
            "pacing": "alternating_beats",
            "sfx_cue": "whoosh",
        },
    ],
    "timeline": [
        {
            "treatment_id": "chronological_spine",
            "grammar_family": "chronological_rail",
            "visual_metaphor": "horizontal_trim_rail_with_milestone_nodes",
            "graphic_elements": ["timeline_track", "milestone_pins", "date_callouts"],
            "capabilities": ["trim_paths", "shape_layer", "camera_motion", "arabic_rtl_text"],
            "camera_profile": "lateral_pan_track",
            "lighting_profile": "soft_editorial_sweep",
            "palette": "warm_editorial_paper",
            "pacing": "steady_cadence",
            "sfx_cue": "pop",
        },
    ],
    "process_flow": [
        {
            "treatment_id": "network_signal_diagram",
            "grammar_family": "explanatory_diagram",
            "visual_metaphor": "connected_network_nodes_with_animated_signal_pulse",
            "graphic_elements": ["network_nodes", "bezier_connector", "arrow_path", "signal_dot"],
            "capabilities": ["bezier_path", "trim_paths", "arrow_path", "glow", "animated_svg"],
            "camera_profile": "slow_push_in",
            "lighting_profile": "target_spotlight_shift",
            "palette": "scientific_obsidian",
            "pacing": "sequential_cascade",
            "sfx_cue": "glint",
        },
        {
            "treatment_id": "step_by_step_pipeline",
            "grammar_family": "step_pipeline",
            "visual_metaphor": "numbered_stages_linking_left_to_right_or_rtl",
            "graphic_elements": ["flowchart_diagram", "arrow_path", "keyword_badge"],
            "capabilities": ["shape_layer", "trim_paths", "arrow_path", "arabic_rtl_text"],
            "camera_profile": "follow_vector_pan",
            "lighting_profile": "soft_editorial_sweep",
            "palette": "deep_studio_slate",
            "pacing": "sequential_cascade",
            "sfx_cue": "card_snap",
        },
    ],
    "problem_and_solution": [
        {
            "treatment_id": "glitch_tension_to_clarity",
            "grammar_family": "polarity_resolution",
            "visual_metaphor": "distorted_warning_state_clears_into_structured_solution",
            "graphic_elements": ["distortion_pulse", "comparison_panel", "arrow_path"],
            "capabilities": ["distortion", "blur", "trim_paths", "arabic_rtl_text"],
            "camera_profile": "tension_tighten_release",
            "lighting_profile": "dramatic_key_spot",
            "palette": "deep_studio_slate",
            "pacing": "tension_release",
            "sfx_cue": "suspense_riser",
        },
    ],
    "psychological_illusion": [
        {
            "treatment_id": "perception_lens_shift",
            "grammar_family": "radar_illusion",
            "visual_metaphor": "spotlight_or_concentric_wave_revealing_hidden_pattern",
            "graphic_elements": ["hero_asset_or_icon", "concentric_repeater", "focus_spotlight", "bezier_connector"],
            "capabilities": ["repeaters", "lights_and_shadows", "layer_2_5d", "masks"],
            "camera_profile": "rack_focus_push",
            "lighting_profile": "dramatic_key_spot",
            "palette": "cinematic_amber_noir",
            "pacing": "uncanny_reveal",
            "sfx_cue": "heartbeat",
        },
    ],
    "historical_event": [
        {
            "treatment_id": "archival_parallax_diorama",
            "grammar_family": "cinematic_parallax_reveal",
            "visual_metaphor": "depth_separated_plates_with_date_banner_and_vignette",
            "graphic_elements": ["depth_plane", "mask_frame", "timeline_badge"],
            "capabilities": ["layer_2_5d", "camera_motion", "lights_and_shadows", "masks"],
            "camera_profile": "slow_cinematic_drift",
            "lighting_profile": "warm_archival_spot",
            "palette": "cinematic_amber_noir",
            "pacing": "narrative_gravity",
            "sfx_cue": "thud",
        },
    ],
    "dramatic_climax": [
        {
            "treatment_id": "impact_convergence",
            "grammar_family": "climax_convergence",
            "visual_metaphor": "radial_vectors_and_particles_converge_on_hero_headline",
            "graphic_elements": ["radial_burst", "particles", "kinetic_title", "light_sweep"],
            "capabilities": ["camera_motion", "particles", "glow", "arabic_rtl_text"],
            "camera_profile": "dramatic_push_in",
            "lighting_profile": "high_contrast_spot",
            "palette": "cinematic_amber_noir",
            "pacing": "explosive_peak",
            "sfx_cue": "thud",
        },
    ],
    "emotional_shift": [
        {
            "treatment_id": "chromatic_focus_transition",
            "grammar_family": "atmospheric_shift",
            "visual_metaphor": "soft_blur_defocus_transitions_to_clear_horizon",
            "graphic_elements": ["blur_transition", "minimal_icon", "floating_particles"],
            "capabilities": ["blur", "particles", "camera_motion", "arabic_rtl_text"],
            "camera_profile": "slow_cinematic_drift",
            "lighting_profile": "warm_archival_spot",
            "palette": "deep_studio_slate",
            "pacing": "emotional_swell",
            "sfx_cue": "glint",
        },
    ],
    "hierarchy": [
        {
            "treatment_id": "stepped_tier_stack",
            "grammar_family": "tiered_pyramid",
            "visual_metaphor": "3_to_4_stacked_tiers_ascending_with_connector_lines",
            "graphic_elements": ["hierarchy_tiers", "trim_borders", "keyword_badge"],
            "capabilities": ["shape_layer", "trim_paths", "layer_2_5d", "arabic_rtl_text"],
            "camera_profile": "vertical_reveal_tilt",
            "lighting_profile": "soft_editorial_sweep",
            "palette": "scientific_obsidian",
            "pacing": "ordered_build",
            "sfx_cue": "pop",
        },
    ],
    "abstract_idea": [
        {
            "treatment_id": "generative_geometry_morph",
            "grammar_family": "symbolic_geometry",
            "visual_metaphor": "rotating_repeater_geometry_framing_central_symbol",
            "graphic_elements": ["concentric_repeater", "svg_symbol", "kinetic_title"],
            "capabilities": ["repeaters", "expressions", "animated_svg", "arabic_rtl_text"],
            "camera_profile": "orbital_drift",
            "lighting_profile": "soft_editorial_sweep",
            "palette": "scientific_obsidian",
            "pacing": "hypnotic_flow",
            "sfx_cue": "glint",
        },
    ],
    "data_or_statistic": [
        {
            "treatment_id": "animated_infographic_chart",
            "grammar_family": "data_infographic",
            "visual_metaphor": "growing_bars_and_tick_marks_with_numeric_callout",
            "graphic_elements": ["bar_chart", "numeric_counter", "grid_axes"],
            "capabilities": ["shape_layer", "trim_paths", "text_animators", "arabic_rtl_text"],
            "camera_profile": "crisp_orthographic_push",
            "lighting_profile": "clean_rim_sweep",
            "palette": "deep_studio_slate",
            "pacing": "precision_snap",
            "sfx_cue": "pop",
        },
    ],
    "conclusion": [
        {
            "treatment_id": "synthesized_takeaway_frame",
            "grammar_family": "summary_lockup",
            "visual_metaphor": "nested_emblem_settles_with_clean_editorial_lockup",
            "graphic_elements": ["nested_emblem", "kinetic_title", "subtle_sweep"],
            "capabilities": ["nested_compositions", "arabic_rtl_text", "masks"],
            "camera_profile": "pull_back_resolve",
            "lighting_profile": "soft_editorial_sweep",
            "palette": "warm_editorial_paper",
            "pacing": "graceful_resolve",
            "sfx_cue": "glint",
        },
    ],
}


@dataclass
class IntentClassification:
    """Result of classifying a narration chunk into a V5 narrative intent."""

    intent: str
    confidence: float
    matched_keywords: List[str] = field(default_factory=list)
    semantic_concept: Optional[str] = None
    alternative_intents: List[str] = field(default_factory=list)


class MotionDesignGrammarEngine:
    """Translates narrative intent + constraints into concrete motion-design treatments."""

    def __init__(self, semantic_rules_path: Path = SEMANTIC_RULES_PATH):
        self.semantic_rules = self._load_semantic_rules(semantic_rules_path)

    @staticmethod
    def _load_semantic_rules(path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("rules", []) if isinstance(data, dict) else []
        except Exception:
            return []

    @staticmethod
    def list_intents() -> List[str]:
        return list(NARRATIVE_INTENTS)

    def classify_intent(
        self,
        text: str,
        *,
        section_index: int = 0,
        total_sections: int = 1,
        hints: Optional[List[str]] = None,
        explicit_intent: Optional[str] = None,
    ) -> IntentClassification:
        """Classify Arabic or English narrative text into one of the 15 intents."""
        if explicit_intent and explicit_intent in NARRATIVE_INTENTS:
            return IntentClassification(
                intent=explicit_intent,
                confidence=1.0,
                matched_keywords=[explicit_intent],
                alternative_intents=[],
            )

        norm = (text or "").lower()
        scores: Dict[str, float] = {k: 0.0 for k in NARRATIVE_INTENTS}
        hits: Dict[str, List[str]] = {k: [] for k in NARRATIVE_INTENTS}
        matched_concept: Optional[str] = None

        # 1. Existing semantic_visual_rules.json bridge
        for rule in self.semantic_rules:
            kw = str(rule.get("keyword", "")).lower()
            aliases = [str(a).lower() for a in rule.get("aliases", [])]
            negatives = [str(n).lower() for n in rule.get("negative_keywords", [])]
            if any(neg and neg in norm for neg in negatives):
                continue
            rule_hits = [w for w in ([kw] + aliases) if w and w in norm]
            if rule_hits:
                concept = rule.get("concept", "")
                mapped = _CONCEPT_TO_INTENT.get(concept)
                if mapped:
                    matched_concept = concept
                    scores[mapped] += float(rule.get("priority", 0.9)) * len(rule_hits)
                    hits[mapped].extend(rule_hits)

        # 2. Direct multilingual narrative intent keywords
        for intent, kws in _INTENT_KEYWORDS.items():
            for kw in kws:
                if kw in norm:
                    scores[intent] += 1.0
                    hits[intent].append(kw)

        # 3. Numeric / percentage signal boost for data_or_statistic
        if re.search(r"\b\d+(?:\.\d+)?\s*%|\b\d{4}\b", norm):
            if re.search(r"\b(?:19|20)\d{2}\b", norm) and scores["timeline"] >= 0:
                scores["timeline"] += 0.9
            else:
                scores["data_or_statistic"] += 0.85

        # 4. Structural position hints (start / end / caller hints)
        if hints:
            for h in hints:
                hl = str(h).lower()
                for intent in NARRATIVE_INTENTS:
                    if intent in hl:
                        scores[intent] += 1.4
        if total_sections > 1:
            if section_index == 0:
                scores["introduction"] += 0.35
            elif section_index == total_sections - 1:
                scores["conclusion"] += 0.35

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        best_intent, best_score = ranked[0]
        if best_score <= 0.0:
            best_intent = "concept_reveal"
            conf = 0.45
        else:
            conf = min(0.99, round(0.55 + 0.15 * best_score, 2))
        alts = [k for k, v in ranked[1:4] if v > 0]
        return IntentClassification(
            intent=best_intent,
            confidence=conf,
            matched_keywords=sorted(set(hits.get(best_intent, []))),
            semantic_concept=matched_concept,
            alternative_intents=alts,
        )

    def design_treatment(
        self,
        intent: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        avoid_treatment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Select a tailored visual treatment for `intent` considering visual variety & constraints."""
        ctx = context or {}
        if intent not in _TREATMENT_CATALOG:
            intent = "concept_reveal"
        candidates = _TREATMENT_CATALOG[intent]
        chosen = candidates[0]
        if avoid_treatment_id and len(candidates) > 1 and chosen["treatment_id"] == avoid_treatment_id:
            chosen = candidates[1]

        palette_key = ctx.get("palette_override") or chosen["palette"]
        palette = dict(PALETTES.get(palette_key, PALETTES["deep_studio_slate"]))
        dur = float(ctx.get("duration", 4.0))

        # Safety guard from AGENTS.md: bright light surfaces avoid intense additive Glow >= 1.0
        vfx_policy = {
            "prefer_light_sweep": bool(palette.get("is_light_bg")),
            "max_glow_intensity": 0.65 if palette.get("is_light_bg") else 1.5,
        }

        return {
            "intent": intent,
            "treatment_id": chosen["treatment_id"],
            "grammar_family": chosen["grammar_family"],
            "visual_metaphor": chosen["visual_metaphor"],
            "graphic_elements": list(chosen["graphic_elements"]),
            "recommended_capabilities": list(chosen["capabilities"]),
            "camera_profile": chosen["camera_profile"],
            "lighting_profile": chosen["lighting_profile"],
            "palette": palette,
            "pacing": chosen["pacing"],
            "suggested_sfx": chosen["sfx_cue"],
            "vfx_policy": vfx_policy,
            "timing_proportions": self._build_timing_proportions(dur, chosen["pacing"]),
        }

    @staticmethod
    def _build_timing_proportions(duration: float, pacing: str) -> Dict[str, float]:
        """Derive anticipation/reveal/hold/resolve ratios organically from beat duration & pacing."""
        d = max(0.8, duration)
        if pacing in ("explosive_peak", "precision_snap", "impulse_reaction"):
            ant = min(0.18, d * 0.08)
            rev = min(0.55, d * 0.25)
        elif pacing in ("cinematic_breathe", "narrative_gravity", "emotional_swell"):
            ant = min(0.30, d * 0.12)
            rev = min(1.10, d * 0.35)
        else:
            ant = min(0.22, d * 0.10)
            rev = min(0.75, d * 0.28)
        res = min(0.45, d * 0.15)
        return {
            "anticipation_sec": round(ant, 3),
            "reveal_sec": round(rev, 3),
            "hold_sec": round(max(0.2, d - ant - rev - res), 3),
            "resolve_sec": round(res, 3),
        }

    def plan_section_grammar(
        self,
        beats: List[Dict[str, Any]],
        *,
        palette_override: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Assign varied narrative intents & treatments across a sequence of beats."""
        planned: List[Dict[str, Any]] = []
        last_tid: Optional[str] = None
        total = max(1, len(beats))
        for idx, beat in enumerate(beats):
            text = str(beat.get("text", ""))
            cls = self.classify_intent(
                text,
                section_index=idx,
                total_sections=total,
                hints=beat.get("hints"),
                explicit_intent=beat.get("intent"),
            )
            dur = max(0.8, float(beat.get("end", 4.0)) - float(beat.get("start", 0.0)))
            treatment = self.design_treatment(
                cls.intent,
                context={"duration": dur, "palette_override": palette_override},
                avoid_treatment_id=last_tid,
            )
            last_tid = treatment["treatment_id"]
            planned.append({
                "beat_id": beat.get("id", f"beat_{idx + 1:02d}"),
                "start": float(beat.get("start", 0.0)),
                "end": float(beat.get("end", dur)),
                "text": text,
                "classification": {
                    "intent": cls.intent,
                    "confidence": cls.confidence,
                    "matched_keywords": cls.matched_keywords,
                    "semantic_concept": cls.semantic_concept,
                },
                "treatment": treatment,
            })
        return planned
