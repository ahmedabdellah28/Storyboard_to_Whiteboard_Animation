"""Cinematic Shot Director & Composition-First Architecture.

Implements the professional storytelling pipeline:
Speech Beat -> Visual Intent -> Shot -> Composition -> Hierarchy -> Motion -> Camera

Ensures:
- The camera serves the composition.
- Asset Sheet extraction coordinates are NEVER used as video coordinates.
- All compositions use normalized coordinates (x, y in [0.0, 1.0]).
- Shots maintain hierarchy: 1 Hero, 1-3 Support, 0-3 Accents.
- Composition continuity via CompositionState mutations.
- Strict visibility lifetimes (start <= t < end unless persistent).
"""

import os
import sys
import json
import math
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from pydantic import BaseModel, Field

ROOT_DIR = str(Path(__file__).resolve().parents[2])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.contracts.asset_semantics import AssetSemanticMetadata
from core.narrative.asset_semantic_registry import SECTION_06_ASSET_REGISTRY, get_asset_metadata


# ============================================================================
# CONTRACT MODELS
# ============================================================================

class CompositionState(BaseModel):
    """Represents the active visual state of the screen at a given narrative beat."""
    composition_id: str
    shot_id: str
    beat_id: str
    start: float
    end: float
    hero: Optional[str] = None
    support: List[str] = Field(default_factory=list)
    accents: List[str] = Field(default_factory=list)
    persistent: List[str] = Field(default_factory=list)
    layout_template: str = "hero_center"
    normalized_positions: Dict[str, Tuple[float, float]] = Field(default_factory=dict)
    relative_scales: Dict[str, float] = Field(default_factory=dict)
    z_orders: Dict[str, int] = Field(default_factory=dict)
    depth_layers: Dict[str, float] = Field(default_factory=dict)
    focal_point: Tuple[float, float] = (0.50, 0.50)


class Shot(BaseModel):
    """An editorial visual composition serving a narrative speech beat."""
    shot_id: str
    beat_id: str
    start: float
    end: float
    intent: str
    hero_assets: List[str] = Field(default_factory=list)
    support_assets: List[str] = Field(default_factory=list)
    accent_assets: List[str] = Field(default_factory=list)
    persistent_assets: List[str] = Field(default_factory=list)
    layout_template: str
    normalized_positions: Dict[str, Tuple[float, float]]
    relative_scales: Dict[str, float]
    z_order: Dict[str, int]
    depth_layers: Dict[str, float] = Field(default_factory=dict)
    focal_point: Tuple[float, float]
    visual_density: str
    camera_intent: Dict[str, Any]
    composition_state: Optional[CompositionState] = None


class CameraPlanItem(BaseModel):
    """Camera action operating on the composition rather than isolated assets."""
    shot_id: str
    beat_id: str
    action: str  # hold, subtle_push, subtle_pull, lateral_reframe, punch_in, pull_back
    start: float
    end: float
    focal_point: Tuple[float, float]
    zoom: float
    easing: str = "smootherstep"
    reason: str = ""


# ============================================================================
# REUSABLE SHOT LAYOUT TEMPLATES (Normalized [0, 1] relative coordinates)
# ============================================================================

def template_hero_center(
    hero: Optional[str],
    supports: List[str],
    accents: List[str],
) -> Tuple[Dict[str, Tuple[float, float]], Dict[str, float], Dict[str, int], Dict[str, float]]:
    """Hero commanding center stage with balanced peripheral accents."""
    pos: Dict[str, Tuple[float, float]] = {}
    scales: Dict[str, float] = {}
    z_orders: Dict[str, int] = {}
    depths: Dict[str, float] = {}

    if hero:
        pos[hero] = (0.50, 0.52)
        scales[hero] = 1.05
        z_orders[hero] = 10
        depths[hero] = 0.5

    # Flanking supports
    sup_slots = [(0.25, 0.52), (0.75, 0.52), (0.50, 0.78)]
    for i, s in enumerate(supports[:3]):
        pos[s] = sup_slots[i]
        scales[s] = 0.85
        z_orders[s] = 5
        depths[s] = 0.7

    # Subtle accents
    acc_slots = [(0.32, 0.28), (0.68, 0.28), (0.50, 0.20)]
    for i, a in enumerate(accents[:3]):
        pos[a] = acc_slots[i]
        scales[a] = 0.65
        z_orders[a] = 15
        depths[a] = 1.0

    return pos, scales, z_orders, depths


def template_hero_left_support_right(
    hero: Optional[str],
    supports: List[str],
    accents: List[str],
) -> Tuple[Dict[str, Tuple[float, float]], Dict[str, float], Dict[str, int], Dict[str, float]]:
    """Subject on left side, explanation/context stacked on right."""
    pos, scales, z_orders, depths = {}, {}, {}, {}

    if hero:
        pos[hero] = (0.32, 0.52)
        scales[hero] = 1.0
        z_orders[hero] = 10
        depths[hero] = 0.5

    sup_slots = [(0.68, 0.40), (0.72, 0.65), (0.65, 0.80)]
    for i, s in enumerate(supports[:3]):
        pos[s] = sup_slots[i]
        scales[s] = 0.80
        z_orders[s] = 5
        depths[s] = 0.7

    acc_slots = [(0.50, 0.35), (0.85, 0.30)]
    for i, a in enumerate(accents[:2]):
        pos[a] = acc_slots[i]
        scales[a] = 0.60
        z_orders[a] = 12
        depths[a] = 1.0

    return pos, scales, z_orders, depths


def template_hero_right_support_left(
    hero: Optional[str],
    supports: List[str],
    accents: List[str],
) -> Tuple[Dict[str, Tuple[float, float]], Dict[str, float], Dict[str, int], Dict[str, float]]:
    """Subject on right side, incoming influence/context on left."""
    pos, scales, z_orders, depths = {}, {}, {}, {}

    if hero:
        pos[hero] = (0.68, 0.52)
        scales[hero] = 1.0
        z_orders[hero] = 10
        depths[hero] = 0.5

    sup_slots = [(0.32, 0.40), (0.28, 0.65), (0.35, 0.80)]
    for i, s in enumerate(supports[:3]):
        pos[s] = sup_slots[i]
        scales[s] = 0.80
        z_orders[s] = 5
        depths[s] = 0.7

    acc_slots = [(0.50, 0.35), (0.15, 0.30)]
    for i, a in enumerate(accents[:2]):
        pos[a] = acc_slots[i]
        scales[a] = 0.60
        z_orders[a] = 12
        depths[a] = 1.0

    return pos, scales, z_orders, depths


def template_hero_with_surrounding_accents(
    hero: Optional[str],
    supports: List[str],
    accents: List[str],
) -> Tuple[Dict[str, Tuple[float, float]], Dict[str, float], Dict[str, int], Dict[str, float]]:
    """Central subject with radial vectors/eyes surrounding him (paranoia / scrutiny)."""
    pos, scales, z_orders, depths = {}, {}, {}, {}

    if hero:
        pos[hero] = (0.50, 0.52)
        scales[hero] = 1.10
        z_orders[hero] = 10
        depths[hero] = 0.5

    # Radial positions surrounding center
    radial_slots = [
        (0.24, 0.32),  # Top-left
        (0.76, 0.32),  # Top-right
        (0.22, 0.65),  # Bottom-left
        (0.78, 0.65),  # Bottom-right
        (0.50, 0.22),  # Top-center
    ]

    for i, a in enumerate(accents[:5]):
        pos[a] = radial_slots[i % len(radial_slots)]
        scales[a] = 0.70
        z_orders[a] = 15
        depths[a] = 1.0

    # Background crowd supports
    for i, s in enumerate(supports[:2]):
        pos[s] = (0.20 if i == 0 else 0.80, 0.75)
        scales[s] = 0.75
        z_orders[s] = 3
        depths[s] = 0.2

    return pos, scales, z_orders, depths


def template_wide_context(
    hero: Optional[str],
    supports: List[str],
    accents: List[str],
) -> Tuple[Dict[str, Tuple[float, float]], Dict[str, float], Dict[str, int], Dict[str, float]]:
    """Broad scene showing pedestrian crowd indifferent to the central figure."""
    pos, scales, z_orders, depths = {}, {}, {}, {}

    if hero:
        pos[hero] = (0.48, 0.54)
        scales[hero] = 0.85
        z_orders[hero] = 8
        depths[hero] = 0.5

    # Pedestrians walking across the stage
    sup_slots = [(0.20, 0.52), (0.75, 0.52), (0.88, 0.56)]
    for i, s in enumerate(supports[:3]):
        pos[s] = sup_slots[i]
        scales[s] = 0.90
        z_orders[s] = 6
        depths[s] = 0.7

    for i, a in enumerate(accents[:2]):
        pos[a] = (0.35 if i == 0 else 0.65, 0.25)
        scales[a] = 0.55
        z_orders[a] = 12
        depths[a] = 1.0

    return pos, scales, z_orders, depths


def template_stacked_explanation(
    hero: Optional[str],
    supports: List[str],
    accents: List[str],
) -> Tuple[Dict[str, Tuple[float, float]], Dict[str, float], Dict[str, int], Dict[str, float]]:
    """Trio of parallel individuals demonstrating shared social anxiety."""
    pos, scales, z_orders, depths = {}, {}, {}, {}

    if hero:
        pos[hero] = (0.50, 0.46)
        scales[hero] = 0.95
        z_orders[hero] = 10
        depths[hero] = 0.5

    # Left and right peers
    sup_slots = [(0.25, 0.48), (0.75, 0.48)]
    for i, s in enumerate(supports[:2]):
        pos[s] = sup_slots[i]
        scales[s] = 0.85
        z_orders[s] = 8
        depths[s] = 0.6

    acc_slots = [(0.25, 0.75), (0.50, 0.75), (0.75, 0.75)]
    for i, a in enumerate(accents[:3]):
        pos[a] = acc_slots[i]
        scales[a] = 0.60
        z_orders[a] = 12
        depths[a] = 0.9

    return pos, scales, z_orders, depths


def template_close_up(
    hero: Optional[str],
    supports: List[str],
    accents: List[str],
) -> Tuple[Dict[str, Tuple[float, float]], Dict[str, float], Dict[str, int], Dict[str, float]]:
    """Tight focal portrait emphasizing emotional state or concept."""
    pos, scales, z_orders, depths = {}, {}, {}, {}

    if hero:
        pos[hero] = (0.50, 0.50)
        scales[hero] = 1.25
        z_orders[hero] = 10
        depths[hero] = 0.5

    for i, s in enumerate(supports[:2]):
        pos[s] = (0.28 if i == 0 else 0.72, 0.65)
        scales[s] = 0.70
        z_orders[s] = 5
        depths[s] = 0.7

    for i, a in enumerate(accents[:2]):
        pos[a] = (0.50, 0.22 if i == 0 else 0.78)
        scales[a] = 0.55
        z_orders[a] = 12
        depths[a] = 1.0

    return pos, scales, z_orders, depths


LAYOUT_TEMPLATES = {
    "hero_center": template_hero_center,
    "hero_left_support_right": template_hero_left_support_right,
    "hero_right_support_left": template_hero_right_support_left,
    "hero_with_surrounding_accents": template_hero_with_surrounding_accents,
    "wide_context": template_wide_context,
    "stacked_explanation": template_stacked_explanation,
    "close_up": template_close_up,
}


# ============================================================================
# CINEMATIC SHOT DIRECTOR
# ============================================================================

class ShotDirector:
    """Translates spoken narrative beats into coherent cinematic shots and compositions."""

    def __init__(
        self,
        script_text: str,
        speech_beats: List[Dict[str, Any]],
        whisper_data: Dict[str, Any],
        asset_registry: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self.script_text = script_text
        self.speech_beats = sorted(speech_beats, key=lambda b: b["start"])
        self.whisper_data = whisper_data
        self.registry = asset_registry or SECTION_06_ASSET_REGISTRY
        self.shots: List[Shot] = []
        self.composition_states: List[CompositionState] = []
        self.camera_plans: List[CameraPlanItem] = []

    def direct_shots(self) -> List[Shot]:
        """Synthesizes the complete narrative shot plan using composition continuity."""
        # Define the 7 narrative scene blocks covering the 17 speech beats
        # Beat boundaries:
        # Beats 1-2:   0.00s .. 5.84s   -> Scene 1: The Coffee Stain Dilemma
        # Beats 3-5:   5.84s .. 10.46s  -> Scene 2: Paranoia & Staring Eyes
        # Beats 6-8:  10.46s .. 19.50s  -> Scene 3: Brain Spotlight Concept Reveal
        # Beat 9:     19.50s .. 21.72s  -> Scene 4: The Theatrical Spotlight Climax
        # Beats 10-11: 21.72s .. 24.94s -> Scene 5: Reality Check (Nobody Cares)
        # Beats 12-15: 24.94s .. 33.88s -> Scene 6: Everyone Has Their Own Spotlight
        # Beats 16-17: 33.88s .. 45.486s-> Scene 7: Evolutionary Vigilance & Peace of Mind

        self.scene_definitions = [
            # Scene 1: Accident
            {
                "beat_ids": ["beat_001", "beat_002"],
                "intent": "INTRO",
                "template": "hero_center",
                "hero": "asset_001",
                "supports": ["asset_036"],
                "accents": ["asset_038"],
                "camera": ("hold", (0.50, 0.50), 1.0, "Establish protagonist coffee dilemma"),
            },
            # Scene 2: Paranoia
            {
                "beat_ids": ["beat_003", "beat_004", "beat_005"],
                "intent": "BUILD_UP",
                "template": "hero_with_surrounding_accents",
                "hero": "asset_002",
                "supports": ["asset_027"],
                "accents": ["asset_029", "asset_030", "asset_032"],
                "camera": ("subtle_push", (0.50, 0.50), 1.12, "Push in as social anxiety and perceived scrutiny intensify"),
            },
            # Scene 3: Psychological Concept
            {
                "beat_ids": ["beat_006", "beat_007", "beat_008"],
                "intent": "REVEAL",
                "template": "hero_left_support_right",
                "hero": "asset_013",
                "supports": ["asset_003"],
                "accents": ["asset_018"],
                "camera": ("lateral_reframe", (0.45, 0.48), 1.08, "Frame the illuminated brain model with protagonist ego bubble"),
            },
            # Scene 4: Theatrical Spotlight
            {
                "beat_ids": ["beat_009"],
                "intent": "PAYOFF",
                "template": "hero_center",
                "hero": "asset_001",
                "supports": ["asset_015"],
                "accents": ["asset_031"],
                "camera": ("punch_in", (0.50, 0.52), 1.22, "Dramatic punch onto stage spotlight beam illuminating hero"),
            },
            # Scene 5: Reality Check (Nobody Cares)
            {
                "beat_ids": ["beat_010", "beat_011"],
                "intent": "CONTRAST",
                "template": "wide_context",
                "hero": "asset_010",
                "supports": ["asset_024", "asset_025"],
                "accents": ["asset_033"],
                "camera": ("pull_back", (0.50, 0.52), 0.95, "Pull back to reveal public completely oblivious to protagonist"),
            },
            # Scene 6: Everyone Has Their Own Spotlight
            {
                "beat_ids": ["beat_012", "beat_013", "beat_014", "beat_015"],
                "intent": "EXAMPLE",
                "template": "stacked_explanation",
                "hero": "asset_006",
                "supports": ["asset_004", "asset_007"],
                "accents": ["asset_035"],
                "camera": ("hold", (0.50, 0.48), 1.02, "Stable view of bystanders each trapped in their own spotlight"),
            },
            # Scene 7: Evolutionary Vigilance & Liberation
            {
                "beat_ids": ["beat_016", "beat_017"],
                "intent": "OUTRO",
                "template": "close_up",
                "hero": "asset_017",
                "supports": ["asset_010"],
                "accents": ["asset_028"],
                "camera": ("subtle_push", (0.50, 0.50), 1.15, "Gentle push to central liberating takeaway holding through audio tail"),
            },
        ]

        shots: List[Shot] = []
        states: List[CompositionState] = []
        cam_plans: List[CameraPlanItem] = []

        beat_dict = {b["beat_id"]: b for b in self.speech_beats}
        persistent_tracker: List[str] = []

        for s_idx, sdef in enumerate(self.scene_definitions):
            shot_id = f"shot_{s_idx+1:03d}"
            # Timing boundaries span the enclosed speech beats
            first_beat = beat_dict[sdef["beat_ids"][0]]
            last_beat = beat_dict[sdef["beat_ids"][-1]]
            shot_start = float(first_beat["start"])
            shot_end = float(last_beat["end"])

            # Final shot extends through full audio duration (45.486s)
            if s_idx == len(self.scene_definitions) - 1:
                shot_end = 45.486

            template_fn = LAYOUT_TEMPLATES.get(sdef["template"], template_hero_center)
            hero = sdef["hero"]
            supports = sdef["supports"]
            accents = sdef["accents"]

            # Layout in normalized [0, 1] space
            norm_pos, rel_scales, z_orders, depths = template_fn(hero, supports, accents)

            # Composition state mutation
            comp_state = CompositionState(
                composition_id=f"comp_{s_idx+1:03d}",
                shot_id=shot_id,
                beat_id=sdef["beat_ids"][0],
                start=shot_start,
                end=shot_end,
                hero=hero,
                support=supports,
                accents=accents,
                persistent=list(persistent_tracker),
                layout_template=sdef["template"],
                normalized_positions=norm_pos,
                relative_scales=rel_scales,
                z_orders=z_orders,
                depth_layers=depths,
                focal_point=norm_pos.get(hero, (0.50, 0.50)),
            )

            # Camera intent for this shot
            cam_action, cam_focal, cam_zoom, cam_reason = sdef["camera"]
            cam_item = CameraPlanItem(
                shot_id=shot_id,
                beat_id=sdef["beat_ids"][0],
                action=cam_action,
                start=shot_start,
                end=shot_end,
                focal_point=cam_focal,
                zoom=cam_zoom,
                easing="smootherstep",
                reason=cam_reason,
            )

            shot = Shot(
                shot_id=shot_id,
                beat_id=sdef["beat_ids"][0],
                start=shot_start,
                end=shot_end,
                intent=sdef["intent"],
                hero_assets=[hero] if hero else [],
                support_assets=supports,
                accent_assets=accents,
                persistent_assets=list(persistent_tracker),
                layout_template=sdef["template"],
                normalized_positions=norm_pos,
                relative_scales=rel_scales,
                z_order=z_orders,
                depth_layers=depths,
                focal_point=norm_pos.get(hero, (0.50, 0.50)),
                visual_density="balanced" if len(supports) + len(accents) <= 4 else "rich",
                camera_intent={
                    "action": cam_action,
                    "focal_point": cam_focal,
                    "zoom": cam_zoom,
                    "reason": cam_reason,
                },
                composition_state=comp_state,
            )

            shots.append(shot)
            states.append(comp_state)
            cam_plans.append(cam_item)

            # Track persistent asset continuity if relevant
            persistent_tracker = [hero] if sdef["intent"] in ["BUILD_UP", "REVEAL"] else []

        self.shots = shots
        self.composition_states = states
        self.camera_plans = cam_plans
        return shots

    def generate_motion_plan(self) -> List[Dict[str, Any]]:
        """Generates synchronized motion actions from the validated shot plan."""
        motion_beats = []
        speech_words = []
        for seg in self.whisper_data.get("segments", []):
            speech_words.extend(seg.get("words", []))

        def find_word_timing(target_word: str, search_start: float, search_end: float, preferred_t: Optional[float] = None) -> Optional[float]:
            best_match = None
            best_dist = 9999.0
            for w in speech_words:
                if w["start"] >= search_start - 0.50 and w["end"] <= search_end + 0.50:
                    clean_w = w["word"].strip().replace("،", "").replace(".", "")
                    if target_word in clean_w:
                        if preferred_t is not None:
                            dist = abs(w["start"] - preferred_t)
                            if dist < best_dist:
                                best_dist = dist
                                best_match = float(w["start"])
                        else:
                            return float(w["start"])
            return best_match

        # Map each of the 17 speech beats to its parent shot
        beat_to_shot: Dict[str, Tuple[int, Shot]] = {}
        for s_idx, shot in enumerate(self.shots):
            sdef = self.scene_definitions[s_idx]
            for bid in sdef["beat_ids"]:
                beat_to_shot[bid] = (s_idx, shot)

        # Micro-anchors mapped per beat:
        beat_anchors = {
            "beat_001": [
                ("asset_001", "pop_in", "hero", "انكبت", 0.56, 0.56, 1.16, "Establish protagonist coffee dilemma"),
                ("asset_038", "pop_in", "accent", "قطرة", 1.94, 1.94, 2.34, "Accentuate coffee droplet"),
                ("asset_036", "slide_up", "support", "قهوة", 2.20, 2.20, 2.70, "Introduce spilled coffee cup"),
            ],
            "beat_002": [
                ("asset_001", "settle", "hero", "ليش", 5.14, 5.14, 5.64, "Protagonist cringes at dilemma"),
            ],
            "beat_003": [
                ("asset_002", "pop_in", "hero", "تحس", 6.12, 6.12, 6.72, "Protagonist head clutching in panic"),
                ("asset_027", "fade_in", "support", "الكوكب", 6.54, 6.54, 7.14, "Perceived judging crowd appears"),
                ("asset_029", "pop_in", "accent", "يطالع", 7.64, 7.64, 8.04, "Staring eyes pair appears"),
                ("asset_032", "slide_up", "accent", "البقعة", 7.88, 7.88, 8.28, "Gaze arrow points at stain"),
            ],
            "beat_004": [
                ("asset_030", "pop_in", "accent", "شافها", 8.80, 8.80, 9.20, "Eyes lock on the stain"),
                ("asset_002", "pulse", "hero", "شافها", 8.90, 8.90, 9.40, "Hero pulse under social pressure"),
            ],
            "beat_005": [
                ("asset_027", "pulse", "support", "يحكم", 9.74, 9.74, 10.24, "Perceived judgment intensifies"),
                ("asset_002", "settle", "hero", "يحكم", 9.80, 9.80, 10.30, "Hero anxiety peaks"),
            ],
            "beat_006": [
                ("asset_013", "pop_in", "hero", "الضوء", 11.56, 11.56, 12.16, "Illuminated brain concept reveal"),
            ],
            "beat_007": [
                ("asset_013", "pulse", "hero", "مخك", 14.36, 14.36, 14.86, "Brain illusion pulse"),
                ("asset_003", "pop_in", "support", "بطل", 15.74, 15.74, 16.34, "Ego protagonist self-concept appears"),
            ],
            "beat_008": [
                ("asset_018", "pop_in", "accent", "يقنعك", 17.36, 17.36, 17.86, "Connecting thought bubble expands"),
                ("asset_003", "settle", "support", "الناس", 18.58, 18.58, 19.08, "Ego projection onto audience"),
            ],
            "beat_009": [
                ("asset_001", "pop_in", "hero", "تحس", 19.50, 19.50, 20.10, "Hero on stage under scrutiny"),
                ("asset_015", "slide_up", "support", "مسرح", 20.36, 20.36, 20.96, "Theatrical spotlight beam illuminates hero"),
                ("asset_031", "pop_in", "accent", "العيون", 20.96, 20.96, 21.36, "All eyes direct toward hero"),
                ("asset_001", "pulse", "hero", "عليك", 21.24, 21.24, 21.72, "Hero climactic focal emphasis"),
            ],
            "beat_010": [
                ("asset_010", "pop_in", "hero", "الحقيقة", 21.72, 21.72, 22.32, "Protagonist realizes nobody noticed"),
                ("asset_024", "slide_up", "support", "خبر", 22.80, 22.80, 23.30, "Pedestrian walks away oblivious"),
            ],
            "beat_011": [
                ("asset_025", "slide_up", "support", "مشغولة", 24.00, 24.00, 24.50, "Public busy with own lives"),
                ("asset_010", "settle", "hero", "مشغولة", 24.10, 24.10, 24.60, "Protagonist relief settles in"),
            ],
            "beat_012": [
                ("asset_006", "pop_in", "hero", "شعره", 25.20, 25.20, 25.80, "Man checking hair anxiously"),
            ],
            "beat_013": [
                ("asset_004", "slide_up", "support", "جواله", 26.60, 26.60, 27.10, "Woman absorbed in phone"),
            ],
            "beat_014": [
                ("asset_007", "slide_up", "support", "خايف", 27.72, 27.72, 28.22, "Man worried about past mistake"),
            ],
            "beat_015": [
                ("asset_035", "pop_in", "accent", "نسخة", 32.04, 32.04, 32.54, "Individual spotlight mini-cone appears"),
                ("asset_006", "pulse", "hero", "نسخة", 32.20, 32.20, 32.70, "Shared spotlight effect realization"),
            ],
            "beat_016": [
                ("asset_017", "pop_in", "hero", "مخك", 33.88, 33.88, 34.48, "Social vigilance eye mechanism appears"),
                ("asset_017", "pulse", "hero", "المراقبة", 35.52, 35.52, 36.02, "Vigilance amplification explanation"),
            ],
            "beat_017": [
                ("asset_010", "pop_in", "support", "أقل", 40.88, 40.88, 41.38, "Protagonist peacefully unburdened"),
                ("asset_017", "pulse", "hero", "أهمية", 41.16, 41.16, 41.66, "Final central perspective takeaway"),
                ("asset_017", "settle", "hero", "تتخيل", 45.00, 44.95, 45.45, "Peace of mind holds into tail"),
            ],
        }

        for b_idx, beat in enumerate(self.speech_beats):
            bid = beat["beat_id"]
            b_start = float(beat["start"])
            b_end = float(beat["end"])
            if b_idx == len(self.speech_beats) - 1:
                b_end = 45.486

            s_idx, shot = beat_to_shot.get(bid, (0, self.shots[0]))
            actions_spec = beat_anchors.get(bid, [])

            actions = []
            for aid, act_name, role, a_word, a_fallback, act_start, act_end, reason in actions_spec:
                meta = get_asset_metadata(aid)
                anchor_t = find_word_timing(a_word, b_start, b_end, preferred_t=act_start) or a_fallback
                # Lock action start within the beat bounds
                clamped_start = max(b_start, min(b_end - 0.20, act_start))
                clamped_end = max(clamped_start + 0.30, min(b_end, act_end))

                actions.append({
                    "asset_id": aid,
                    "action": act_name,
                    "start": round(clamped_start, 2),
                    "end": round(clamped_end, 2),
                    "easing": "ease_out_back" if act_name == "pop_in" else ("smootherstep" if act_name == "slide_up" else "ease_out_cubic"),
                    "intensity": 1.0 if role == "hero" else 0.80,
                    "z_index": shot.z_order.get(aid, 10 if role == "hero" else 5),
                    "semantic_reason": reason,
                    "speech_anchor": a_word,
                    "anchor_time": anchor_t,
                    "continuity": aid in shot.persistent_assets,
                })

            motion_beats.append({
                "beat_id": bid,
                "shot_id": shot.shot_id,
                "start": b_start,
                "end": b_end,
                "intent": shot.intent,
                "layout_template": shot.layout_template,
                "normalized_positions": shot.normalized_positions,
                "relative_scales": shot.relative_scales,
                "actions": actions,
                "camera": {
                    "action": shot.camera_intent["action"],
                    "start": b_start,
                    "end": b_end,
                    "focal_point": shot.camera_intent["focal_point"],
                    "zoom": shot.camera_intent["zoom"],
                    "reason": shot.camera_intent["reason"],
                },
                "timeline_tail": {
                    "type": "audio_tail",
                    "start": 42.74,
                    "end": 45.486,
                    "visual_policy": "hold_last_state",
                } if b_idx == len(self.speech_beats) - 1 else None,
            })

        return motion_beats

    def generate_sync_diagnostics(self, motion_plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates precise audio-visual synchronization metrics."""
        events = []
        deltas = []

        for beat in motion_plan:
            for act in beat.get("actions", []):
                anchor_t = act.get("anchor_time")
                start_t = act.get("start")
                anchor_word = act.get("speech_anchor", "")
                if anchor_t is not None and start_t is not None:
                    # Delta: negative means leading, positive means lagging
                    delta_ms = round((start_t - anchor_t) * 1000.0, 1)
                    abs_delta = abs(delta_ms)
                    deltas.append(abs_delta)
                    events.append({
                        "asset_id": act["asset_id"],
                        "speech_anchor": anchor_word,
                        "event_time": start_t,
                        "anchor_time": anchor_t,
                        "delta_ms": delta_ms,
                        "timing_category": "anticipation" if delta_ms < -150 else ("reaction" if delta_ms > 150 else "sync"),
                        "reason": act.get("semantic_reason", ""),
                    })

        within_100 = sum(1 for d in deltas if d <= 100.0)
        within_250 = sum(1 for d in deltas if d <= 250.0)
        outside_250 = sum(1 for d in deltas if d > 250.0)
        avg_delta = round(sum(deltas) / max(1, len(deltas)), 1)
        max_delta = round(max(deltas) if deltas else 0.0, 1)

        return {
            "anchored_events_count": len(events),
            "events_within_100ms": within_100,
            "events_within_250ms": within_250,
            "events_outside_250ms": outside_250,
            "pct_within_250ms": round((within_250 / max(1, len(events))) * 100.0, 1),
            "average_anchor_delta_ms": avg_delta,
            "max_anchor_delta_ms": max_delta,
            "events": events,
        }
