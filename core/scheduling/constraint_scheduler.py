"""Constraint-Based Visual Scheduler & Execution Planner.

Implements Phase 3 of the Tri-Contract Architecture:
Takes VisualManifest (Contract 1), NarrativeVisualMap (Contract 2),
and ResolvedAnchors to produce FinalRenderPlan (Contract 3).

Enforces:
- Normalized demand-driven drawing durations
- Policy-governed speedup limits and lead-in times
- Strictly non-decreasing chronology
- Explicit overlap typology (INTENTIONAL_OVERLAP, SAFE_COMPOSITION, RESOLVED_BY_CAMERA)
- Integrated dynamic camera path and SFX tracks
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from core.contracts.visual_manifest import VisualManifest, VisualEntity
from core.contracts.narrative_map import NarrativeVisualMap, NarrativeConcept, NarrativeRole, OverlapPolicy
from core.contracts.render_plan import (
    FinalRenderPlan,
    VisualBeat,
    ResolvedAnchor,
    TimingSpec,
    ViewportPlacement,
    CameraKeyframe,
    SFXCue,
    ExecutionTracks,
    CollisionClassification,
)
from core.contracts.render_policy import RenderPolicy, RoleSpeedLimit
from core.vision.demand_estimator import DemandEstimator


class ConstraintVisualScheduler:
    """Calculates deterministic execution timeline, camera path, and audio cues."""

    def __init__(
        self,
        audio_duration: float,
        policy: Optional[RenderPolicy] = None,
        canvas_dimensions: Tuple[int, int] = (1920, 1080),
    ) -> None:
        self.audio_duration = audio_duration
        self.policy = policy or RenderPolicy()
        self.canvas_dimensions = canvas_dimensions
        self.demand_estimator = DemandEstimator(self.policy)

    def _get_role_limit(self, role: NarrativeRole) -> RoleSpeedLimit:
        sp = self.policy.speed_limits
        if role == NarrativeRole.HERO:
            return sp.hero
        elif role == NarrativeRole.SUPPORT:
            return sp.support
        elif role == NarrativeRole.CONTEXT:
            return sp.context
        return sp.decorative

    def _compute_overlap_ratio(
        self, bbox_a: Tuple[int, int, int, int], bbox_b: Tuple[int, int, int, int]
    ) -> float:
        """Compute intersection over minimum area between two bounding boxes."""
        ax, ay, aw, ah = bbox_a
        bx, by, bw, bh = bbox_b
        
        inter_x1 = max(ax, bx)
        inter_y1 = max(ay, by)
        inter_x2 = min(ax + aw, bx + bw)
        inter_y2 = min(ay + ah, by + bh)

        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0

        inter_area = float((inter_x2 - inter_x1) * (inter_y2 - inter_y1))
        area_a = float(aw * ah)
        area_b = float(bw * bh)
        min_area = max(1.0, min(area_a, area_b))
        return inter_area / min_area

    def schedule(
        self,
        section_id: str,
        manifest: VisualManifest,
        narrative_map: NarrativeVisualMap,
        resolved_pairs: List[Tuple[NarrativeConcept, Optional[ResolvedAnchor]]],
        hashes: Dict[str, str],
    ) -> FinalRenderPlan:
        """Builds a deterministic FinalRenderPlan from verified upstream contracts."""
        valid_pairs = [(c, a) for c, a in resolved_pairs if a is not None]
        # Sort strictly by anchor start timestamp
        sorted_pairs = sorted(valid_pairs, key=lambda p: p[1].whisper_t_start)

        visual_beats: List[VisualBeat] = []
        camera_keyframes: List[CameraKeyframe] = []
        sfx_cues: List[SFXCue] = []

        current_cursor = 0.0
        active_entities_on_screen: List[Tuple[str, Tuple[int, int, int, int], float]] = []

        # Initial camera establishing shot
        cw, ch = self.canvas_dimensions
        camera_keyframes.append(
            CameraKeyframe(t=0.0, viewport_rect=(0, 0, cw, ch), interpolation="cubic_hermite")
        )

        for i, (concept, anchor) in enumerate(sorted_pairs, 1):
            entity = manifest.get_entity(concept.visual_id)
            if not entity:
                continue

            role_limit = self._get_role_limit(concept.narrative_role)
            t_min, t_est, t_max = self.demand_estimator.calculate_duration(
                entity.demand_metrics, role_limit
            )

            # 1. Lead-in calculation bounded by policy
            desired_lead_in = min(role_limit.max_lead_in_s, anchor.whisper_t_start * 0.5)
            ideal_ink_start = max(0.0, anchor.whisper_t_start - desired_lead_in)

            # Enforce non-overlapping start with previous cursor if concurrency is disabled
            if not self.policy.temporal.allow_parallel_drawing:
                ink_start = max(ideal_ink_start, current_cursor + self.policy.temporal.min_gap_between_beats_s)
            else:
                ink_start = ideal_ink_start

            effective_lead_in = round(max(0.0, anchor.whisper_t_start - ink_start), 3)

            # 2. Window sizing and speedup factor calculation
            if i < len(sorted_pairs):
                next_anchor = sorted_pairs[i][1]
                available_window = max(0.5, next_anchor.whisper_t_start - ink_start)
            else:
                available_window = max(0.5, self.audio_duration - ink_start)

            if available_window < t_est:
                # Need speedup within policy limits
                required_speed = t_est / max(t_min, available_window)
                speed_factor = round(min(role_limit.max_speedup_factor, max(1.0, required_speed)), 2)
                draw_duration = round(max(t_min, t_est / speed_factor), 2)
            else:
                speed_factor = 1.0
                draw_duration = round(min(t_max, t_est), 2)

            ink_end = round(ink_start + draw_duration, 2)
            current_cursor = ink_end

            # 3. Hold time
            hold_min = concept.visual_continuity.min_hold_after_finish_s
            if i < len(sorted_pairs):
                next_t = sorted_pairs[i][1].whisper_t_start
                hold_until = round(max(ink_end + hold_min, next_t + 1.0), 2)
            else:
                hold_until = round(max(ink_end + hold_min, self.audio_duration), 2)

            # 4. Viewport placement & Overlap Typology
            bx, by, bw, bh = entity.bbox
            center_x = bx + bw // 2
            center_y = by + bh // 2

            # Check overlap against currently active entities on screen
            collision_type = CollisionClassification.NONE
            # Check flow rules first
            is_intentional = False
            for rule in narrative_map.narrative_flow_rules:
                if (rule.antecedent == concept.concept_id or rule.consequent == concept.concept_id) and \
                   rule.overlap_policy == OverlapPolicy.INTENTIONAL_OVERLAP:
                    is_intentional = True
                    break

            if is_intentional:
                collision_type = CollisionClassification.INTENTIONAL_OVERLAP
            else:
                # Check spatial overlap
                for prev_id, prev_bbox, prev_hold in active_entities_on_screen:
                    if prev_hold > ink_start:
                        ratio = self._compute_overlap_ratio(entity.bbox, prev_bbox)
                        if ratio > self.policy.overlap.max_accidental_overlap_ratio:
                            collision_type = CollisionClassification.RESOLVED_BY_CAMERA
                            break
                if collision_type == CollisionClassification.NONE:
                    collision_type = CollisionClassification.SAFE_COMPOSITION

            active_entities_on_screen.append((concept.concept_id, entity.bbox, hold_until))

            # 5. Build Visual Beat
            beat_id = f"beat_{i:03d}"
            beat = VisualBeat(
                beat_id=beat_id,
                concept_id=concept.concept_id,
                visual_id=entity.visual_id,
                resolved_anchor=anchor,
                timing=TimingSpec(
                    lead_in_s=effective_lead_in,
                    ink_start_s=round(ink_start, 2),
                    ink_end_s=ink_end,
                    draw_duration_s=draw_duration,
                    speed_multiplier=speed_factor,
                    hold_until_s=hold_until,
                ),
                viewport=ViewportPlacement(
                    target_center=(center_x, center_y),
                    scale=1.0,
                    render_layer=i,
                ),
                collision_classification=collision_type,
            )
            visual_beats.append(beat)

            # 6. Camera keyframe focused on active beat
            pad_w = int(bw * 1.4)
            pad_h = int(bh * 1.4)
            cam_x = max(0, min(cw - pad_w, center_x - pad_w // 2))
            cam_y = max(0, min(ch - pad_h, center_y - pad_h // 2))
            camera_keyframes.append(
                CameraKeyframe(
                    t=round(max(0.0, ink_start - 0.2), 2),
                    viewport_rect=(cam_x, cam_y, pad_w, pad_h),
                    focus_beat_id=beat_id,
                    interpolation="cubic_hermite",
                )
            )

            # 7. SFX cue for drawing duration
            sfx_cues.append(
                SFXCue(
                    t_start=round(ink_start, 2),
                    t_end=ink_end,
                    sfx_profile="whiteboard_ink_dense" if entity.visual_type == "composite_scene" else "whiteboard_ink_clean",
                    duck_speech_db=-2.5,
                )
            )

        tracks = ExecutionTracks(
            visual_beats=visual_beats,
            camera_path=camera_keyframes,
            sfx_cues=sfx_cues,
        )

        return FinalRenderPlan(
            section_id=section_id,
            total_duration_s=round(self.audio_duration, 2),
            render_policy_id=self.policy.policy_id,
            source_audio_hash=hashes.get("audio_hash", ""),
            narrative_map_hash=hashes.get("narrative_map_hash", ""),
            manifest_hash=hashes.get("manifest_hash", ""),
            policy_hash=hashes.get("policy_hash", ""),
            execution_tracks=tracks,
        )
