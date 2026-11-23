"""Storyboard Shot Mapper (Task 8C / Storyboard Reconstruction Architecture).

Transforms the original storyboard panels into faithful, reconstructible Shot Blueprints
using independent clean layer assets extracted from the separated asset sheet.

Core Model:
Original Storyboard
→ Storyboard Shot Blueprint
→ Map storyboard entities to extracted assets
→ Reconstruct each storyboard shot using independent assets
→ Animate those assets
→ Camera serves the reconstructed shot

Rules:
- The storyboard defines WHAT the viewer should see.
- The extracted assets define HOW the scene is built as independent layers.
- Preserves hero, support, accents, spatial relationships, scale, and hierarchy.
- No arbitrary assets, no invented compositions, no runtime AI.
"""

from typing import Tuple
# pyrefly: ignore [invalid-syntax]
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parents[2]


class StoryboardPanelMapping(BaseModel):
    """Mapping of a single storyboard panel to clean layer assets."""
    panel_id: str
    panel_index: int
    storyboard_reference: str
    orig_box: List[int]
    hero_entities: List[str]
    support_entities: List[str]
    accent_entities: List[str]
    persistent_entities: List[str] = Field(default_factory=list)
    allowed_assets: List[str]
    description: str


class StoryboardShot(BaseModel):
    """Reconstructed editorial shot faithful to the storyboard panel."""
    shot_id: str
    panel_index: int
    storyboard_reference: str
    start: float
    end: float
    beat_ids: List[str]
    hero_entities: List[str]
    support_entities: List[str]
    accent_entities: List[str]
    persistent_entities: List[str] = Field(default_factory=list)
    allowed_assets: List[str]
    composition_type: str
    normalized_positions: Dict[str, List[float]]
    relative_scales: Dict[str, float]
    z_order: Dict[str, int]
    depth_layers: Dict[str, float]
    focal_point: List[float]
    camera_intent: Dict[str, Any]


class StoryboardShotMapper:
    """Deterministic mapper reconstructing storyboard panels into layered shot compositions."""

    def __init__(
        self,
        storyboard_meta_path: Optional[str] = None,
        whisper_path: Optional[str] = None,
    ) -> None:
        self.sec_dir = ROOT_DIR / "sections" / "brain_illusions_documentary" / "06_spotlight_effect"
        self.storyboard_meta_path = (
            Path(storyboard_meta_path)
            if storyboard_meta_path
            else self.sec_dir / "assets" / "metadata.json"
        )
        self.whisper_path = (
            Path(whisper_path)
            if whisper_path
            else self.sec_dir / "timing" / "whisper.json"
        )

        with open(self.storyboard_meta_path, "r", encoding="utf-8") as f:
            self.storyboard_meta = json.load(f)

        with open(self.whisper_path, "r", encoding="utf-8") as f:
            self.whisper_data = json.load(f)

        self.audio_duration = float(self.whisper_data.get("duration", 45.486))

        # Build mappings and shot blueprint
        self.asset_map = self._build_storyboard_asset_map()
        self.shots = self._build_storyboard_shots()

    def _build_storyboard_asset_map(self) -> Dict[str, Any]:
        """Maps each of the 10 storyboard panels to its extracted replacement assets."""
        mappings = [
            StoryboardPanelMapping(
                panel_id="01_man_coffee_spill",
                panel_index=1,
                storyboard_reference="panel_01_coffee_spill",
                orig_box=[0, 0, 353, 348],
                hero_entities=["asset_001"],
                support_entities=["asset_036"],
                accent_entities=["asset_038"],
                allowed_assets=["asset_001", "asset_036", "asset_038"],
                description="Protagonist standing in suit holding spilled coffee cup with flying droplet",
            ),
            StoryboardPanelMapping(
                panel_id="02_man_hiding_stain",
                panel_index=2,
                storyboard_reference="panel_02_hiding_stain",
                orig_box=[353, 0, 660, 348],
                hero_entities=["asset_001"],
                support_entities=[],
                accent_entities=["asset_037"],
                allowed_assets=["asset_001", "asset_037"],
                description="Protagonist clutching jacket trying to cover and hide coffee stain",
            ),
            StoryboardPanelMapping(
                panel_id="03_man_eyes_watching",
                panel_index=3,
                storyboard_reference="panel_03_eyes_watching",
                orig_box=[660, 0, 1029, 348],
                hero_entities=["asset_002"],
                support_entities=["asset_027"],
                accent_entities=["asset_029", "asset_030", "asset_032"],
                allowed_assets=["asset_002", "asset_027", "asset_029", "asset_030", "asset_032"],
                description="Protagonist head clutching in panic, judging crowd silhouette and staring eyes pointing at stain",
            ),
            StoryboardPanelMapping(
                panel_id="06_brain_spotlight_hero",
                panel_index=4,
                storyboard_reference="panel_06_brain_spotlight_hero",
                orig_box=[460, 337, 967, 696],
                hero_entities=["asset_013"],
                support_entities=["asset_003"],
                accent_entities=["asset_018"],
                allowed_assets=["asset_013", "asset_003", "asset_018"],
                description="Glowing profile of brain with internal spotlight shining on protagonist ego self-concept",
            ),
            StoryboardPanelMapping(
                panel_id="05_man_stressed_thought_bubble",
                panel_index=5,
                storyboard_reference="panel_05_ego_thought_bubble",
                orig_box=[0, 337, 460, 696],
                hero_entities=["asset_003"],
                support_entities=["asset_018"],
                accent_entities=["asset_008"],
                allowed_assets=["asset_003", "asset_018", "asset_008"],
                description="Protagonist looking up anxiously with thought bubble convincing him he is the hero of the story",
            ),
            StoryboardPanelMapping(
                panel_id="04_spotlight_silhouettes",
                panel_index=6,
                storyboard_reference="panel_04_theatrical_spotlight",
                orig_box=[1029, 0, 1536, 348],
                hero_entities=["asset_001"],
                support_entities=["asset_015", "asset_027"],
                accent_entities=["asset_031"],
                allowed_assets=["asset_001", "asset_015", "asset_027", "asset_031"],
                description="Theatrical spotlight cone shining directly on protagonist on stage with crowd and all eyes watching",
            ),
            StoryboardPanelMapping(
                panel_id="08_man_stain_crowd_distracted",
                panel_index=7,
                storyboard_reference="panel_08_crowd_oblivious",
                orig_box=[0, 686, 537, 1024],
                hero_entities=["asset_010"],
                support_entities=["asset_024", "asset_025", "asset_026"],
                accent_entities=[],
                allowed_assets=["asset_010", "asset_024", "asset_025", "asset_026"],
                description="Protagonist standing small with stain, pedestrians walking away completely absorbed and oblivious",
            ),
            StoryboardPanelMapping(
                panel_id="07_three_distracted_people",
                panel_index=8,
                storyboard_reference="panel_07_three_distracted_people",
                orig_box=[967, 337, 1536, 696],
                hero_entities=["asset_006"],
                support_entities=["asset_004", "asset_007"],
                accent_entities=["asset_035"],
                allowed_assets=["asset_006", "asset_004", "asset_007", "asset_035"],
                description="Three people side-by-side: man checking hair, woman absorbed in phone, man worried about mistake",
            ),
            StoryboardPanelMapping(
                panel_id="09_brain_social_warning",
                panel_index=9,
                storyboard_reference="panel_09_brain_social_warning",
                orig_box=[537, 686, 967, 1024],
                hero_entities=["asset_017"],
                support_entities=["asset_013"],
                accent_entities=[],
                allowed_assets=["asset_017", "asset_013"],
                description="Brain social monitoring and vigilance surveillance mechanism explaining evolutionary purpose",
            ),
            StoryboardPanelMapping(
                panel_id="10_man_worried_others_busy",
                panel_index=10,
                storyboard_reference="panel_10_liberating_takeaway",
                orig_box=[967, 686, 1536, 1024],
                hero_entities=["asset_017"],
                support_entities=["asset_010"],
                accent_entities=["asset_018"],
                allowed_assets=["asset_017", "asset_010", "asset_018"],
                description="Final liberating perspective: protagonist peaceful with empty thought bubble (nobody noticed)",
            ),
        ]

        return {
            "section": "06_spotlight_effect",
            "storyboard_image": "sections/brain_illusions_documentary/06_spotlight_effect/storyboard.png",
            "canvas_dimensions": {"width": 1536, "height": 1024},
            "total_storyboard_panels": 10,
            "panel_mappings": [m.model_dump() for m in mappings],
        }

    def _build_storyboard_shots(self) -> List[StoryboardShot]:
        """Constructs 10 chronological storyboard shots with spatial reconstruction and timing."""
        raw_shots = [
            # Shot 1: Panel 01 - Coffee spill
            {
                "shot_id": "shot_001",
                "panel_index": 1,
                "storyboard_reference": "panel_01_coffee_spill",
                "start": 0.00,
                "end": 3.42,
                "beat_ids": ["beat_001"],
                "hero_entities": ["asset_001"],
                "support_entities": ["asset_036"],
                "accent_entities": ["asset_038"],
                "allowed_assets": ["asset_001", "asset_036", "asset_038"],
                "composition_type": "hero_center_support_left",
                "normalized_positions": {
                    "asset_001": [0.50, 0.52],
                    "asset_036": [0.26, 0.52],
                    "asset_038": [0.32, 0.28],
                },
                "relative_scales": {
                    "asset_001": 1.05,
                    "asset_036": 0.85,
                    "asset_038": 0.65,
                },
                "z_order": {"asset_001": 10, "asset_036": 5, "asset_038": 15},
                "depth_layers": {"asset_001": 0.5, "asset_036": 0.7, "asset_038": 1.0},
                "focal_point": [0.50, 0.52],
                "camera_intent": {"action": "hold", "focal_point": [0.50, 0.50], "zoom": 1.0, "reason": "Establish coffee spill accident"},
            },
            # Shot 2: Panel 02 - Hiding stain
            {
                "shot_id": "shot_002",
                "panel_index": 2,
                "storyboard_reference": "panel_02_hiding_stain",
                "start": 3.42,
                "end": 5.84,
                "beat_ids": ["beat_002"],
                "hero_entities": ["asset_001"],
                "support_entities": [],
                "accent_entities": ["asset_037"],
                "allowed_assets": ["asset_001", "asset_037"],
                "composition_type": "hero_center_closeup",
                "normalized_positions": {
                    "asset_001": [0.50, 0.52],
                    "asset_037": [0.50, 0.58],
                },
                "relative_scales": {
                    "asset_001": 1.10,
                    "asset_037": 0.70,
                },
                "z_order": {"asset_001": 10, "asset_037": 15},
                "depth_layers": {"asset_001": 0.5, "asset_037": 0.8},
                "focal_point": [0.50, 0.52],
                "camera_intent": {"action": "subtle_push", "focal_point": [0.50, 0.52], "zoom": 1.08, "reason": "Tighten focus on stain concealment"},
            },
            # Shot 3: Panel 03 - Eyes watching & panic
            {
                "shot_id": "shot_003",
                "panel_index": 3,
                "storyboard_reference": "panel_03_eyes_watching",
                "start": 5.84,
                "end": 10.46,
                "beat_ids": ["beat_003", "beat_004", "beat_005"],
                "hero_entities": ["asset_002"],
                "support_entities": ["asset_027"],
                "accent_entities": ["asset_029", "asset_030", "asset_032"],
                "allowed_assets": ["asset_002", "asset_027", "asset_029", "asset_030", "asset_032"],
                "composition_type": "hero_center_surrounded",
                "normalized_positions": {
                    "asset_002": [0.50, 0.52],
                    "asset_027": [0.22, 0.65],
                    "asset_029": [0.26, 0.28],
                    "asset_030": [0.74, 0.28],
                    "asset_032": [0.38, 0.46],
                },
                "relative_scales": {
                    "asset_002": 1.15,
                    "asset_027": 0.85,
                    "asset_029": 0.75,
                    "asset_030": 0.75,
                    "asset_032": 0.55,
                },
                "z_order": {"asset_002": 20, "asset_027": 5, "asset_029": 15, "asset_030": 15, "asset_032": 18},
                "depth_layers": {"asset_002": 0.5, "asset_027": 0.2, "asset_029": 0.8, "asset_030": 0.8, "asset_032": 0.9},
                "focal_point": [0.50, 0.52],
                "camera_intent": {"action": "subtle_push", "focal_point": [0.50, 0.50], "zoom": 1.12, "reason": "Intensify perceived audience scrutiny"},
            },
            # Shot 4: Panel 06 - Brain spotlight illusion
            {
                "shot_id": "shot_004",
                "panel_index": 4,
                "storyboard_reference": "panel_06_brain_spotlight_hero",
                "start": 10.46,
                "end": 16.70,
                "beat_ids": ["beat_006", "beat_007"],
                "hero_entities": ["asset_013"],
                "support_entities": ["asset_003"],
                "accent_entities": ["asset_018"],
                "allowed_assets": ["asset_013", "asset_003", "asset_018"],
                "composition_type": "hero_left_support_right",
                "normalized_positions": {
                    "asset_013": [0.34, 0.50],
                    "asset_003": [0.68, 0.52],
                    "asset_018": [0.72, 0.32],
                },
                "relative_scales": {
                    "asset_013": 1.10,
                    "asset_003": 0.90,
                    "asset_018": 0.65,
                },
                "z_order": {"asset_013": 10, "asset_003": 8, "asset_018": 15},
                "depth_layers": {"asset_013": 0.5, "asset_003": 0.6, "asset_018": 0.9},
                "focal_point": [0.46, 0.50],
                "camera_intent": {"action": "lateral_reframe", "focal_point": [0.46, 0.50], "zoom": 1.06, "reason": "Frame illuminated brain model and ego self-concept"},
            },
            # Shot 5: Panel 05 - Ego thought bubble
            {
                "shot_id": "shot_005",
                "panel_index": 5,
                "storyboard_reference": "panel_05_ego_thought_bubble",
                "start": 16.70,
                "end": 19.50,
                "beat_ids": ["beat_008"],
                "hero_entities": ["asset_003"],
                "support_entities": ["asset_018"],
                "accent_entities": ["asset_008"],
                "allowed_assets": ["asset_003", "asset_018", "asset_008"],
                "composition_type": "hero_left_support_right",
                "normalized_positions": {
                    "asset_003": [0.35, 0.55],
                    "asset_018": [0.68, 0.38],
                    "asset_008": [0.35, 0.58],
                },
                "relative_scales": {
                    "asset_003": 1.05,
                    "asset_018": 0.95,
                    "asset_008": 0.95,
                },
                "z_order": {"asset_003": 10, "asset_018": 5, "asset_008": 12},
                "depth_layers": {"asset_003": 0.5, "asset_018": 0.7, "asset_008": 0.5},
                "focal_point": [0.50, 0.48],
                "camera_intent": {"action": "hold", "focal_point": [0.50, 0.48], "zoom": 1.05, "reason": "Hold on ego thought bubble projection"},
            },
            # Shot 6: Panel 04 - Theatrical spotlight on stage
            {
                "shot_id": "shot_006",
                "panel_index": 6,
                "storyboard_reference": "panel_04_theatrical_spotlight",
                "start": 19.50,
                "end": 21.72,
                "beat_ids": ["beat_009"],
                "hero_entities": ["asset_001"],
                "support_entities": ["asset_015", "asset_027"],
                "accent_entities": ["asset_031"],
                "allowed_assets": ["asset_001", "asset_015", "asset_027", "asset_031"],
                "composition_type": "radial_theatrical_focus",
                "normalized_positions": {
                    "asset_001": [0.50, 0.54],
                    "asset_015": [0.50, 0.42],
                    "asset_027": [0.50, 0.78],
                    "asset_031": [0.50, 0.22],
                },
                "relative_scales": {
                    "asset_001": 1.05,
                    "asset_015": 1.25,
                    "asset_027": 0.85,
                    "asset_031": 0.75,
                },
                "z_order": {"asset_015": 2, "asset_027": 5, "asset_001": 10, "asset_031": 15},
                "depth_layers": {"asset_015": 0.2, "asset_027": 0.3, "asset_001": 0.5, "asset_031": 0.9},
                "focal_point": [0.50, 0.52],
                "camera_intent": {"action": "punch_in", "focal_point": [0.50, 0.52], "zoom": 1.22, "reason": "Dramatic punch into theatrical spotlight beam"},
            },
            # Shot 7: Panel 08 - Oblivious crowd walking away
            {
                "shot_id": "shot_007",
                "panel_index": 7,
                "storyboard_reference": "panel_08_crowd_oblivious",
                "start": 21.72,
                "end": 24.94,
                "beat_ids": ["beat_010", "beat_011"],
                "hero_entities": ["asset_010"],
                "support_entities": ["asset_024", "asset_025", "asset_026"],
                "accent_entities": [],
                "allowed_assets": ["asset_010", "asset_024", "asset_025", "asset_026"],
                "composition_type": "split_contrast_wide",
                "normalized_positions": {
                    "asset_010": [0.30, 0.55],
                    "asset_024": [0.58, 0.55],
                    "asset_025": [0.76, 0.55],
                    "asset_026": [0.88, 0.55],
                },
                "relative_scales": {
                    "asset_010": 0.90,
                    "asset_024": 0.95,
                    "asset_025": 0.95,
                    "asset_026": 0.85,
                },
                "z_order": {"asset_010": 10, "asset_024": 8, "asset_025": 6, "asset_026": 4},
                "depth_layers": {"asset_010": 0.5, "asset_024": 0.6, "asset_025": 0.7, "asset_026": 0.8},
                "focal_point": [0.50, 0.52],
                "camera_intent": {"action": "pull_back", "focal_point": [0.50, 0.52], "zoom": 0.95, "reason": "Pull back to reveal public completely oblivious to protagonist"},
            },
            # Shot 8: Panel 07 - Three distracted people
            {
                "shot_id": "shot_008",
                "panel_index": 8,
                "storyboard_reference": "panel_07_three_distracted_people",
                "start": 24.94,
                "end": 33.88,
                "beat_ids": ["beat_012", "beat_013", "beat_014", "beat_015"],
                "hero_entities": ["asset_006"],
                "support_entities": ["asset_004", "asset_007"],
                "accent_entities": ["asset_035"],
                "allowed_assets": ["asset_006", "asset_004", "asset_007", "asset_035"],
                "composition_type": "triptych_horizontal",
                "normalized_positions": {
                    "asset_006": [0.26, 0.52],
                    "asset_004": [0.50, 0.52],
                    "asset_007": [0.74, 0.52],
                    "asset_035": [0.26, 0.40],
                },
                "relative_scales": {
                    "asset_006": 1.05,
                    "asset_004": 1.00,
                    "asset_007": 1.00,
                    "asset_035": 0.65,
                },
                "z_order": {"asset_006": 10, "asset_004": 8, "asset_007": 8, "asset_035": 4},
                "depth_layers": {"asset_006": 0.5, "asset_004": 0.5, "asset_007": 0.5, "asset_035": 0.2},
                "focal_point": [0.50, 0.50],
                "camera_intent": {"action": "hold", "focal_point": [0.50, 0.50], "zoom": 1.00, "reason": "Stable horizontal triptych of distracted individuals"},
            },
            # Shot 9: Panel 09 - Brain social warning mechanism
            {
                "shot_id": "shot_009",
                "panel_index": 9,
                "storyboard_reference": "panel_09_brain_social_warning",
                "start": 33.88,
                "end": 38.64,
                "beat_ids": ["beat_016"],
                "hero_entities": ["asset_017"],
                "support_entities": ["asset_013"],
                "accent_entities": [],
                "allowed_assets": ["asset_017", "asset_013"],
                "composition_type": "hero_center_analytical",
                "normalized_positions": {
                    "asset_017": [0.50, 0.50],
                    "asset_013": [0.50, 0.50],
                },
                "relative_scales": {
                    "asset_017": 1.15,
                    "asset_013": 0.85,
                },
                "z_order": {"asset_017": 15, "asset_013": 5},
                "depth_layers": {"asset_017": 0.5, "asset_013": 0.3},
                "focal_point": [0.50, 0.50],
                "camera_intent": {"action": "subtle_push", "focal_point": [0.50, 0.50], "zoom": 1.08, "reason": "Focus on cognitive social vigilance mechanism"},
            },
            # Shot 10: Panel 10 - Liberating takeaway (nobody is thinking about you)
            {
                "shot_id": "shot_010",
                "panel_index": 10,
                "storyboard_reference": "panel_10_liberating_takeaway",
                "start": 38.64,
                "end": self.audio_duration,
                "beat_ids": ["beat_017"],
                "hero_entities": ["asset_017"],
                "support_entities": ["asset_010"],
                "accent_entities": ["asset_018"],
                "allowed_assets": ["asset_017", "asset_010", "asset_018"],
                "composition_type": "split_liberation",
                "normalized_positions": {
                    "asset_017": [0.50, 0.50],
                    "asset_010": [0.28, 0.62],
                    "asset_018": [0.68, 0.40],
                },
                "relative_scales": {
                    "asset_017": 1.10,
                    "asset_010": 0.95,
                    "asset_018": 1.05,
                },
                "z_order": {"asset_017": 15, "asset_010": 10, "asset_018": 5},
                "depth_layers": {"asset_017": 0.5, "asset_010": 0.6, "asset_018": 0.8},
                "focal_point": [0.50, 0.50],
                "camera_intent": {"action": "subtle_push", "focal_point": [0.50, 0.50], "zoom": 1.15, "reason": "Gentle final push holding peace of mind through tail"},
            },
        ]

        return [StoryboardShot(**s) for s in raw_shots]

    def export_plans(
        self,
        output_shot_plan_path: Optional[str] = None,
        output_asset_map_path: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Exports storyboard_shot_plan.json and storyboard_asset_map.json."""
        out_shot = Path(output_shot_plan_path) if output_shot_plan_path else ROOT_DIR / "data" / "storyboard_shot_plan.json"
        out_map = Path(output_asset_map_path) if output_asset_map_path else ROOT_DIR / "data" / "storyboard_asset_map.json"

        out_shot.parent.mkdir(parents=True, exist_ok=True)
        out_map.parent.mkdir(parents=True, exist_ok=True)

        shot_plan_data = {
            "section": "06_spotlight_effect",
            "audio_duration": self.audio_duration,
            "total_shots": len(self.shots),
            "storyboard_reference": "sections/brain_illusions_documentary/06_spotlight_effect/storyboard.png",
            "shots": [s.model_dump() for s in self.shots],
        }

        with open(out_shot, "w", encoding="utf-8") as f:
            json.dump(shot_plan_data, f, indent=2, ensure_ascii=False)

        with open(out_map, "w", encoding="utf-8") as f:
            json.dump(self.asset_map, f, indent=2, ensure_ascii=False)

        # Mirror to section motion directory as well
        sec_motion = self.sec_dir / "motion"
        sec_motion.mkdir(parents=True, exist_ok=True)
        with open(sec_motion / "storyboard_shot_plan.json", "w", encoding="utf-8") as f:
            json.dump(shot_plan_data, f, indent=2, ensure_ascii=False)
        with open(sec_motion / "storyboard_asset_map.json", "w", encoding="utf-8") as f:
            json.dump(self.asset_map, f, indent=2, ensure_ascii=False)

        return str(out_shot), str(out_map)
