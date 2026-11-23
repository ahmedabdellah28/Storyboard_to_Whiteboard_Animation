"""Motion Graphics Feasibility & Choreography Engine (Task 3).

Converts upstream narrative visual maps and visual manifests into deterministic,
audio-synchronized kinetic motion graphics plans.

Adheres strictly to the 10 Kinetic Motion Graphics Design Rules:
1. New concept causes visible change.
2. No simultaneous asset dump; use staggering.
3. Staggered entrances for support elements.
4. Hero asset receives primary emphasis (highest intensity and top layer).
5. Support assets reinforce without competing.
6. Visible assets persist across neighboring beats.
7. Avoid unnecessary remove/re-add churn.
8. Continuity = true prefers continuous motion/state change over re-entry.
9. Camera movement follows: HOLD -> VISUAL CHANGE -> CAMERA RESPONSE -> HOLD.
10. Every motion has a semantic or compositional purpose.

Zero external AI. Zero LLM. Zero image analysis. 100% deterministic execution.
"""

from __future__ import annotations

import json
import math
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# MOTION VOCABULARY & PRIMITIVES (Phase C)
# ============================================================================

class EntranceAction(str, Enum):
    FADE_IN = "fade_in"
    SCALE_IN = "scale_in"
    POP_IN = "pop_in"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    RISE_IN = "rise_in"
    STAGGER_IN = "stagger_in"


class EmphasisAction(str, Enum):
    PULSE = "pulse"
    SOFT_BOUNCE = "soft_bounce"
    MICRO_SHAKE = "micro_shake"
    GLOW_PULSE = "glow_pulse"
    SCALE_PUNCH = "scale_punch"
    SETTLE = "settle"


class TransformAction(str, Enum):
    MOVE = "move"
    SCALE = "scale"
    ROTATE = "rotate"
    FOLLOW = "follow"
    DRIFT = "drift"


class ExitAction(str, Enum):
    FADE_OUT = "fade_out"
    SCALE_OUT = "scale_out"
    SLIDE_OUT = "slide_out"


class CameraAction(str, Enum):
    HOLD = "hold"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    PAN = "pan"
    FOLLOW = "follow"
    REFRAME = "reframe"
    PUNCH = "punch"
    PULL_BACK = "pull_back"


class EasingType(str, Enum):
    LINEAR = "linear"
    SMOOTHERSTEP = "smootherstep"
    EASE_IN_OUT = "ease_in_out"
    EASE_OUT_BACK = "ease_out_back"
    EASE_OUT_CUBIC = "ease_out_cubic"
    EASE_OUT_ELASTIC = "ease_out_elastic"
    EASE_OUT_QUAD = "ease_out_quad"


VALID_ACTION_NAMES: Set[str] = {
    e.value for e in EntranceAction
} | {
    e.value for e in EmphasisAction
} | {
    e.value for e in TransformAction
} | {
    e.value for e in ExitAction
}

VALID_CAMERA_ACTIONS: Set[str] = {e.value for e in CameraAction}
VALID_EASINGS: Set[str] = {e.value for e in EasingType}


# ============================================================================
# MOTION PLAN CONTRACT MODELS (Phase I)
# ============================================================================

class MotionAction(BaseModel):
    """Represents a discrete kinetic motion action on a visual asset."""
    asset_id: str = Field(..., description="Foreign key mapping to VisualEntity.visual_id in visual_manifest")
    action: str = Field(..., description="Action primitive name (entrance, emphasis, transform, exit)")
    start: float = Field(..., ge=0.0, description="Action start timestamp in seconds")
    end: float = Field(..., ge=0.0, description="Action end timestamp in seconds")
    easing: str = Field(default="ease_out_back", description="Interpolation easing function")
    intensity: float = Field(default=1.0, ge=0.0, le=1.0, description="Motion amplitude / intensity multiplier")
    z_index: int = Field(default=0, ge=0, description="Compositing layer depth")
    reason: str = Field(default="", description="Semantic or compositional explanation")
    continuity: bool = Field(default=False, description="Whether this is a continuing state of an already visible asset")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in VALID_ACTION_NAMES:
            raise ValueError(f"Unknown action '{v}'. Must be one of {sorted(VALID_ACTION_NAMES)}")
        return v

    @field_validator("easing")
    @classmethod
    def validate_easing(cls, v: str) -> str:
        if v not in VALID_EASINGS:
            raise ValueError(f"Unknown easing '{v}'. Must be one of {sorted(VALID_EASINGS)}")
        return v

    @model_validator(mode="after")
    def check_duration_positive(self) -> MotionAction:
        if self.end <= self.start:
            raise ValueError(f"Action end timestamp ({self.end}) must be strictly greater than start ({self.start})")
        return self


class CameraActionSpec(BaseModel):
    """Specifies camera motion accompanying the beat."""
    action: str = Field(default="hold", description="Camera motion primitive")
    start: float = Field(..., ge=0.0, description="Camera move start time in seconds")
    end: float = Field(..., ge=0.0, description="Camera move end time in seconds")
    target: Optional[Any] = Field(default=None, description="Optional target visual entity ID or focus coordinate")

    @field_validator("action")
    @classmethod
    def validate_camera_action(cls, v: str) -> str:
        if v not in VALID_CAMERA_ACTIONS:
            raise ValueError(f"Unknown camera action '{v}'. Must be one of {sorted(VALID_CAMERA_ACTIONS)}")
        return v


class BeatMotionPlan(BaseModel):
    """Motion plan for a single narrative beat."""
    beat_id: str = Field(..., description="Unique beat identifier")
    start: float = Field(..., ge=0.0, description="Beat start timestamp")
    end: float = Field(..., ge=0.0, description="Beat end timestamp")
    actions: List[MotionAction] = Field(default_factory=list, description="Ordered motion actions")
    camera: CameraActionSpec = Field(default_factory=lambda: CameraActionSpec(action="hold", start=0.0, end=1.0))
    timeline_tail: Optional[Dict[str, Any]] = Field(default=None, description="Audio tail preservation specification")


# ============================================================================
# AUDIT & FEASIBILITY REPORT MODELS (Phase A)
# ============================================================================

class FeasibilityBeatReport(BaseModel):
    """Feasibility audit report item for each narrative beat."""
    beat_id: str
    visual_density: str
    hero_assets: List[str]
    support_assets: List[str]
    continuity_assets: List[str]
    recommended_motion_strategy: str
    issues: List[str] = Field(default_factory=list)


class MotionDiagnostics(BaseModel):
    """Comprehensive diagnostics summary for the generated motion plan."""
    total_beats: int
    total_actions: int
    average_actions_per_beat: float
    max_simultaneous_assets: int
    camera_movement_duration: float
    continuity_reuse_count: int
    beats_with_no_visual_action: List[str] = Field(default_factory=list)
    beats_with_excessive_density: List[str] = Field(default_factory=list)
    render_duration: Optional[float] = None
    audio_duration: Optional[float] = None
    timeline_tail: Optional[Dict[str, Any]] = None


# ============================================================================
# MOTION FEASIBILITY AUDITOR (Phase A)
# ============================================================================

class MotionFeasibilityAuditor:
    """Deterministically inspects narrative visual maps and manifests to identify

    visual density, continuity opportunities, and recommended motion strategies.
    """

    def __init__(
        self,
        narrative_map: Dict[str, Any],
        manifest: Dict[str, Any],
    ) -> None:
        self.narrative_map = narrative_map
        self.manifest = manifest
        self.entities_dict = {
            e["visual_id"]: e for e in manifest.get("entities", [])
        }
        self.beats = narrative_map.get("metadata", {}).get("speech_beats", [])

    def audit(self) -> List[FeasibilityBeatReport]:
        reports: List[FeasibilityBeatReport] = []
        active_on_screen: Set[str] = set()

        # Identify candidate atomic support assets from manifest not used as hero
        hero_ids = {
            b["visual_entities"][0]
            for b in self.beats
            if b.get("visual_entities")
        }
        available_support_pool = [
            e["visual_id"]
            for e in self.manifest.get("entities", [])
            if e["visual_id"] not in hero_ids
            and e.get("visual_type") == "atomic_object"
            and e.get("extraction_status") in ("VALID_REQUIRED_ASSET", "valid")
        ]

        support_idx = 0

        for i, beat in enumerate(self.beats):
            beat_id = beat.get("beat_id", f"beat_{i+1:03d}")
            duration = float(beat.get("duration", 0.0))
            heroes = beat.get("visual_entities", [])
            issues: List[str] = []

            # 1. Density classification
            if duration <= 1.2:
                density = "sparse"
            elif duration <= 2.5:
                density = "medium"
            else:
                density = "high"

            # 2. Check single visual asset & support allocation
            support_assets: List[str] = []
            if len(heroes) <= 1:
                issues.append("single_visual_asset_assigned_in_narrative_map")

            if duration < 1.0:
                issues.append("short_beat_duration_under_1s")
            elif duration > 3.0:
                issues.append("extended_duration_needs_secondary_motion")

            # Determine support assets if duration permits
            if duration > 2.5 and support_idx + 1 < len(available_support_pool):
                support_assets = [available_support_pool[support_idx], available_support_pool[support_idx + 1]]
                support_idx += 2
            elif duration > 1.4 and support_idx < len(available_support_pool):
                support_assets = [available_support_pool[support_idx]]
                support_idx += 1

            # 3. Continuity assets
            continuity_assets: List[str] = []
            if beat.get("continuity", False) and active_on_screen:
                continuity_assets = sorted(list(active_on_screen))
            elif i >= 14 and active_on_screen:  # Outro CTA sequence
                continuity_assets = [list(active_on_screen)[-1]]

            # 4. Recommended strategy
            if duration < 1.1:
                strategy = "hero_pop_in_with_subtle_hold"
            elif continuity_assets and duration > 2.5:
                strategy = "continuity_hold_with_staggered_support_and_pull_back"
            elif support_assets and duration > 2.5:
                strategy = "kinetic_stagger_with_camera_push"
            elif support_assets:
                strategy = "sequential_reveal_hero_then_support"
            else:
                strategy = "hero_entrance_with_soft_bounce"

            # Update active on screen tracking
            for h in heroes:
                active_on_screen.add(h)
            for s in support_assets:
                active_on_screen.add(s)

            reports.append(
                FeasibilityBeatReport(
                    beat_id=beat_id,
                    visual_density=density,
                    hero_assets=heroes,
                    support_assets=support_assets,
                    continuity_assets=continuity_assets,
                    recommended_motion_strategy=strategy,
                    issues=issues,
                )
            )

        return reports


# ============================================================================
# MOTION CHOREOGRAPHER IMPLEMENTATION (Phases D through H)
# ============================================================================

class MotionChoreographer:
    """Transforms narrative beats into audio-synchronized, physics-eased motion plans."""

    def __init__(
        self,
        manifest_data_or_path: Union[Dict[str, Any], Path, str],
        narrative_map_or_path: Union[Dict[str, Any], Path, str],
        whisper_data_or_path: Optional[Union[Dict[str, Any], Path, str]] = None,
    ) -> None:
        self.manifest = self._load_json(manifest_data_or_path)
        self.narrative_map = self._load_json(narrative_map_or_path)
        self.whisper_data = self._load_json(whisper_data_or_path) if whisper_data_or_path else {}
        self.entities = {e["visual_id"]: e for e in self.manifest.get("entities", [])}
        # Determine audio duration: check whisper_data, then narrative_map metadata, then speech beat end
        dur = None
        if self.whisper_data and "duration" in self.whisper_data:
            dur = float(self.whisper_data["duration"])
        elif "metadata" in self.narrative_map and "audio_duration_s" in self.narrative_map["metadata"]:
            dur = float(self.narrative_map["metadata"]["audio_duration_s"])
        elif "audio_duration" in self.narrative_map:
            dur = float(self.narrative_map["audio_duration"])

        if dur is None or dur <= 0.0:
            beats = self.narrative_map.get("metadata", {}).get("speech_beats", [])
            dur = float(beats[-1]["end"]) if beats else 0.0

        self.audio_duration = dur

    def _load_json(self, src: Union[Dict[str, Any], Path, str]) -> Dict[str, Any]:
        if isinstance(src, dict):
            return src
        p = Path(src).resolve()
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate_feasibility_report(
        self, output_path: Optional[Union[str, Path]] = None
    ) -> List[Dict[str, Any]]:
        """Executes Phase A feasibility audit and optionally persists to JSON."""
        auditor = MotionFeasibilityAuditor(self.narrative_map, self.manifest)
        reports = auditor.audit()
        dict_reports = [r.model_dump() for r in reports]

        if output_path:
            out_p = Path(output_path).resolve()
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                json.dump(dict_reports, f, indent=2, ensure_ascii=False)

        return dict_reports

    def choreograph(
        self,
        output_plan_path: Optional[Union[str, Path]] = None,
        output_diagnostics_path: Optional[Union[str, Path]] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Main choreography entrypoint.

        Generates motion_plan.json and motion_diagnostics.json.
        """
        feasibility_reports = self.generate_feasibility_report()
        feasibility_by_beat = {r["beat_id"]: r for r in feasibility_reports}

        beats = self.narrative_map.get("metadata", {}).get("speech_beats", [])
        plans: List[BeatMotionPlan] = []

        total_actions_count = 0
        total_camera_duration = 0.0
        continuity_reuse_count = 0
        max_simultaneous = 0
        beats_no_action: List[str] = []
        beats_excessive_density: List[str] = []

        active_persistent_assets: Dict[str, float] = {}

        for i, beat in enumerate(beats):
            beat_id = beat["beat_id"]
            b_start = round(float(beat["start"]), 3)
            b_end = round(float(beat["end"]), 3)
            b_dur = round(b_end - b_start, 3)

            report = feasibility_by_beat.get(beat_id, {})
            heroes = report.get("hero_assets", beat.get("visual_entities", []))
            supports = report.get("support_assets", [])
            continuity_assets = report.get("continuity_assets", [])

            actions: List[MotionAction] = []
            current_beat_assets: Set[str] = set()

            # ----------------------------------------------------------------
            # 1. CONTINUITY ACTIONS (Rule 6, 7, 8)
            # ----------------------------------------------------------------
            if continuity_assets:
                for c_id in continuity_assets:
                    if c_id in self.entities and c_id not in current_beat_assets:
                        c_start = b_start
                        c_end = min(b_end, round(b_start + min(0.8, b_dur * 0.4), 3))
                        if c_end > c_start:
                            actions.append(
                                MotionAction(
                                    asset_id=c_id,
                                    action=EmphasisAction.SETTLE.value,
                                    start=c_start,
                                    end=c_end,
                                    easing=EasingType.SMOOTHERSTEP.value,
                                    intensity=0.5,
                                    z_index=3,
                                    reason=f"Continuity settle from previous beat",
                                    continuity=True,
                                )
                            )
                            current_beat_assets.add(c_id)
                            continuity_reuse_count += 1

            # ----------------------------------------------------------------
            # 2. HERO ENTRANCE & EMPHASIS (Rule 1, 4, 10)
            # ----------------------------------------------------------------
            for h_idx, hero_id in enumerate(heroes):
                if hero_id not in self.entities:
                    continue

                # Audio synchronized lead-in (200 ms lead-in, bounded by beat.start)
                lead_in = 0.20
                h_start = max(b_start, round(b_start - (lead_in if b_start > 0.2 else 0.0), 3))

                # Primary entrance duration
                # Use dynamic demand: longer for composite, crisp for atomic
                is_composite = self.entities[hero_id].get("visual_type") == "composite_scene"
                h_dur = min(0.65 if is_composite else 0.45, max(0.25, b_dur * 0.5))
                h_end = round(min(b_end, h_start + h_dur), 3)

                # Select entrance primitive based on concept / beat index
                if i % 3 == 0:
                    ent_primitive = EntranceAction.POP_IN.value
                    easing = EasingType.EASE_OUT_BACK.value
                elif i % 3 == 1:
                    ent_primitive = EntranceAction.SLIDE_UP.value
                    easing = EasingType.SMOOTHERSTEP.value
                else:
                    ent_primitive = EntranceAction.SCALE_IN.value
                    easing = EasingType.EASE_OUT_BACK.value

                actions.append(
                    MotionAction(
                        asset_id=hero_id,
                        action=ent_primitive,
                        start=h_start,
                        end=h_end,
                        easing=easing,
                        intensity=1.0,
                        z_index=10 + h_idx,
                        reason="Primary hero entrance synchronized with speech anchor",
                        continuity=False,
                    )
                )
                current_beat_assets.add(hero_id)

                # Hero emphasis action if beat duration permits hold and accent
                if b_dur > 2.0 and (b_end - h_end) >= 0.5:
                    emp_start = round(h_end + 0.15, 3)
                    emp_dur = min(0.55, round((b_end - emp_start) * 0.6, 3))
                    emp_end = round(min(b_end, emp_start + emp_dur), 3)
                    if emp_end > emp_start:
                        actions.append(
                            MotionAction(
                                asset_id=hero_id,
                                action=EmphasisAction.PULSE.value if i % 2 == 0 else EmphasisAction.SCALE_PUNCH.value,
                                start=emp_start,
                                end=emp_end,
                                easing=EasingType.EASE_OUT_CUBIC.value,
                                intensity=0.7,
                                z_index=10 + h_idx,
                                reason="Hero visual emphasis reinforcing narrative pivot",
                                continuity=False,
                            )
                        )

            # ----------------------------------------------------------------
            # 3. SUPPORT ACTIONS (Rule 2, 3, 5: Staggered, Non-competing)
            # ----------------------------------------------------------------
            stagger_offset = 0.35
            for s_idx, sup_id in enumerate(supports):
                if sup_id not in self.entities or sup_id in current_beat_assets:
                    continue

                sup_start = round(min(b_end - 0.25, b_start + 0.45 + (s_idx * stagger_offset)), 3)
                sup_dur = min(0.40, max(0.20, (b_end - sup_start) * 0.6))
                sup_end = round(min(b_end, sup_start + sup_dur), 3)

                if sup_end > sup_start:
                    actions.append(
                        MotionAction(
                            asset_id=sup_id,
                            action=EntranceAction.STAGGER_IN.value if s_idx > 0 else EntranceAction.POP_IN.value,
                            start=sup_start,
                            end=sup_end,
                            easing=EasingType.EASE_OUT_CUBIC.value,
                            intensity=0.75,
                            z_index=5 + s_idx,
                            reason=f"Staggered support element {s_idx + 1} reinforcing concept",
                            continuity=False,
                        )
                    )
                    current_beat_assets.add(sup_id)

            # ----------------------------------------------------------------
            # 4. CAMERA CHOREOGRAPHY (Phase G: HOLD -> CHANGE -> MOVE -> HOLD)
            # ----------------------------------------------------------------
            # Camera action begins slightly after initial visual change
            target_hero = heroes[0] if heroes else None
            cam_action = CameraAction.HOLD.value
            cam_start = b_start
            cam_end = b_end

            if b_dur > 2.8:
                # Long beat: subtle push or reframe
                cam_action = CameraAction.ZOOM_IN.value if i % 2 == 0 else CameraAction.REFRAME.value
                cam_start = round(b_start + 0.25, 3)
                cam_end = round(min(b_end - 0.2, cam_start + 1.2), 3)
                total_camera_duration += (cam_end - cam_start)
            elif b_dur > 1.6 and i % 3 == 0:
                cam_action = CameraAction.PUNCH.value
                cam_start = round(b_start + 0.15, 3)
                cam_end = round(min(b_end, cam_start + 0.65), 3)
                total_camera_duration += (cam_end - cam_start)
            elif i >= 15:  # Outro
                cam_action = CameraAction.PULL_BACK.value
                cam_start = round(b_start + 0.2, 3)
                cam_end = round(min(b_end - 0.2, cam_start + 1.5), 3)
                total_camera_duration += (cam_end - cam_start)

            cam_spec = CameraActionSpec(
                action=cam_action,
                start=cam_start,
                end=cam_end,
                target=target_hero,
            )

            # ----------------------------------------------------------------
            # 5. ASSEMBLE BEAT MOTION PLAN (with Audio Tail Resolution)
            # ----------------------------------------------------------------
            actions.sort(key=lambda a: (a.start, a.z_index))

            timeline_tail = None
            if i == len(beats) - 1 and self.audio_duration > b_end:
                tail_start = b_end
                tail_end = round(self.audio_duration, 3)
                timeline_tail = {
                    "type": "audio_tail",
                    "start": tail_start,
                    "end": tail_end,
                    "visual_policy": "hold_last_state",
                }
                b_end = tail_end
                cam_spec.end = tail_end

            plan = BeatMotionPlan(
                beat_id=beat_id,
                start=b_start,
                end=b_end,
                actions=actions,
                camera=cam_spec,
                timeline_tail=timeline_tail,
            )
            plans.append(plan)

            # Diagnostics metrics tracking
            total_actions_count += len(actions)
            simultaneous_count = len(current_beat_assets)
            if simultaneous_count > max_simultaneous:
                max_simultaneous = simultaneous_count

            if not actions:
                beats_no_action.append(beat_id)
            if len(actions) > 5:
                beats_excessive_density.append(beat_id)

        # --------------------------------------------------------------------
        # 6. VALIDATE CHOREOGRAPHY
        # --------------------------------------------------------------------
        self._validate_plans(plans)

        # --------------------------------------------------------------------
        # 7. GENERATE DIAGNOSTICS
        # --------------------------------------------------------------------
        avg_actions = round(total_actions_count / max(1, len(plans)), 2)
        render_dur = max(p.end for p in plans) if plans else 0.0
        final_tail = plans[-1].timeline_tail if (plans and plans[-1].timeline_tail) else None
        diagnostics = MotionDiagnostics(
            total_beats=len(plans),
            total_actions=total_actions_count,
            average_actions_per_beat=avg_actions,
            max_simultaneous_assets=max_simultaneous,
            camera_movement_duration=round(total_camera_duration, 3),
            continuity_reuse_count=continuity_reuse_count,
            beats_with_no_visual_action=beats_no_action,
            beats_with_excessive_density=beats_excessive_density,
            render_duration=round(render_dur, 3),
            audio_duration=round(self.audio_duration, 3),
            timeline_tail=final_tail,
        )

        plan_dicts = [p.model_dump() for p in plans]
        diag_dict = diagnostics.model_dump()

        # --------------------------------------------------------------------
        # 8. PERSIST OUTPUT CONTRACTS
        # --------------------------------------------------------------------
        if output_plan_path:
            out_p = Path(output_plan_path).resolve()
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                json.dump(plan_dicts, f, indent=2, ensure_ascii=False)

        if output_diagnostics_path:
            out_d = Path(output_diagnostics_path).resolve()
            out_d.parent.mkdir(parents=True, exist_ok=True)
            with open(out_d, "w", encoding="utf-8") as f:
                json.dump(diag_dict, f, indent=2, ensure_ascii=False)

        return plan_dicts, diag_dict

    def _validate_plans(self, plans: List[BeatMotionPlan]) -> None:
        """Runs strict contract validations on the generated plans."""
        for p in plans:
            # Check timestamps inside audio duration
            if p.start < 0.0 or p.end > self.audio_duration + 0.1:
                raise ValueError(
                    f"Beat {p.beat_id} bounds [{p.start}, {p.end}] exceed audio duration {self.audio_duration}"
                )

            # Check camera timing
            if p.camera.start < p.start or p.camera.end > p.end + 0.05:
                raise ValueError(
                    f"Beat {p.beat_id} camera timing [{p.camera.start}, {p.camera.end}] outside beat [{p.start}, {p.end}]"
                )

            # Check individual actions
            for act in p.actions:
                # 1. Unknown asset ID check
                if act.asset_id not in self.entities:
                    raise KeyError(
                        f"Action refers to unknown asset_id '{act.asset_id}' not found in visual_manifest.json"
                    )

                # 2. Duration check
                if act.end <= act.start:
                    raise ValueError(
                        f"Action {act.action} on {act.asset_id} has non-positive duration [{act.start}, {act.end}]"
                    )

                # 3. Beat boundary check (unless continuity=True)
                if act.start < p.start - 0.05 or act.end > p.end + 0.05:
                    if not act.continuity:
                        raise ValueError(
                            f"Action on {act.asset_id} [{act.start}, {act.end}] lies outside beat {p.beat_id} [{p.start}, {p.end}]"
                        )


# ============================================================================
# CONVENIENCE HIGH-LEVEL RUNNER
# ============================================================================

def run_motion_choreography(
    manifest_path: Union[str, Path] = "data/visual_manifest.json",
    narrative_map_path: Union[str, Path] = "data/narrative_visual_map.json",
    whisper_path: Optional[Union[str, Path]] = None,
    output_feasibility_path: Union[str, Path] = "data/motion_feasibility_report.json",
    output_plan_path: Union[str, Path] = "data/motion_plan.json",
    output_diagnostics_path: Union[str, Path] = "data/motion_diagnostics.json",
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Runs the complete Task 3 motion graphics choreography and writes all 3 artifacts."""
    choreographer = MotionChoreographer(
        manifest_data_or_path=manifest_path,
        narrative_map_or_path=narrative_map_path,
        whisper_data_or_path=whisper_path,
    )
    choreographer.generate_feasibility_report(output_path=output_feasibility_path)
    return choreographer.choreograph(
        output_plan_path=output_plan_path,
        output_diagnostics_path=output_diagnostics_path,
    )


if __name__ == "__main__":
    plans, diags = run_motion_choreography()
    print(f"Motion Choreography completed successfully.")
    print(f"Total Beats: {diags['total_beats']}")
    print(f"Total Actions: {diags['total_actions']} (avg {diags['average_actions_per_beat']} / beat)")
    print(f"Max Simultaneous Assets: {diags['max_simultaneous_assets']}")
    print(f"Continuity Reuses: {diags['continuity_reuse_count']}")
    print(f"Camera Movement Duration: {diags['camera_movement_duration']}s")
