"""
Beat Timing Solver (ASATE Level 3: Constrained Optimization Engine V2)
Content-Aware Visual Timing Engine with Calibrated Physical Modeling,
Decoupled Drawing Demand, Speed Feasibility Analysis, and Timing Conflict Handling.
"""
import math
from typing import List, Dict, Any, Optional, Tuple
from .visual_beat import (
    VisualBeat,
    ElementTier,
    OverlapPolicy,
    TransitionPolicy,
    TimingDecision,
    EmphasisPoint,
    SemanticAnchor,
    AnchorType,
    AnchorSourceType,
    DrawingDemand,
    TimingAllocation,
    SpeedFeasibility,
    ConflictType,
    ConflictSeverity,
    TimingConflict,
    BeatTransition
)


class BeatTimingSolver:
    """
    Constrained Global & Local Solver for Visual Beat element scheduling.
    Content-Aware physical simulation replaces hardcoded preset durations.
    """

    # Calibrated physical drawing parameters (fully configurable)
    calibrated_pen_velocity: float = 650.0   # Baseline physical drawing speed in pixels per second
    MIN_ELEMENT_DURATION: float = 0.35       # Minimum physical drawing threshold (seconds)
    MAX_ELEMENT_DURATION: float = 8.00       # Maximum continuous drawing duration (seconds)
    MIN_HOLD_DURATION: float = 0.20          # Minimum visibility retention after drawing completes
    SPEED_SAFE_LIMIT: float = 1400.0         # Absolute upper physical limit for human/robotic whiteboard hand
    MAX_SPEED_MULTIPLIER: float = 2.20       # Maximum acceptable acceleration
    MIN_SPEED_MULTIPLIER: float = 0.50       # Maximum acceptable deceleration

    @classmethod
    def calculate_drawing_demand(cls, elem: Dict[str, Any]) -> DrawingDemand:
        """
        Extracts purely physical drawing workload from element geometry.
        DrawingDemand != DrawingDuration.
        """
        stroke_pts = elem.get("stroke_pts", [])
        bbox = elem.get("bbox", (0, 0, 100, 100))
        w = max(10.0, float(bbox[2]))
        h = max(10.0, float(bbox[3]))
        cat = elem.get("category", "").upper()
        name = elem.get("name", "").lower()

        arc_len = 0.0
        n_pts = 0
        n_strokes = 1

        if stroke_pts:
            # Handle list of points [(x,y), ...] or list of strokes [[(x,y), ...], ...]
            if isinstance(stroke_pts[0], (list, tuple)) and stroke_pts and isinstance(stroke_pts[0][0], (list, tuple)):
                n_strokes = len(stroke_pts)
                for stroke in stroke_pts:
                    n_pts += len(stroke)
                    for i in range(1, len(stroke)):
                        p1, p2 = stroke[i - 1], stroke[i]
                        arc_len += math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            else:
                n_pts = len(stroke_pts)
                for i in range(1, len(stroke_pts)):
                    p1, p2 = stroke_pts[i - 1], stroke_pts[i]
                    arc_len += math.hypot(p2[0] - p1[0], p2[1] - p1[1])

        # If points are absent or sparse, derive physical arc length from geometry & category density
        if arc_len < 10.0:
            perimeter = 2.0 * (w + h)
            if cat in ("TITLE", "TEXT_LINE", "TEXT") or "title" in name or "text" in name or "%" in name or name.isdigit():
                # Text strokes: directly proportional to character count
                text_len = max(2, len(elem.get("text", name)))
                arc_len = text_len * 55.0
                n_strokes = max(2, text_len)
                n_pts = text_len * 15
            elif cat in ("CHARACTER", "PORTRAIT", "FIGURE") or "character" in name or "person" in name:
                # Rich linework: contour + anatomy + clothing details
                density_factor = 3.2
                n_strokes = max(8, int(perimeter / 60.0))
                n_pts = int(perimeter * 2.5)
                arc_len = perimeter * density_factor
            elif cat in ("CONTAINER_CARD", "BOX", "PANEL_BADGE"):
                # Clean outline + header line
                density_factor = 1.3
                n_strokes = 4
                n_pts = 80
                arc_len = perimeter * density_factor
            elif cat in ("EMOJI", "ICON_GRAPHIC"):
                # Icon outline + internal features
                density_factor = 2.1
                n_strokes = 5
                n_pts = 120
                arc_len = perimeter * density_factor
            else:
                density_factor = 1.8
                n_strokes = 3
                n_pts = 90
                arc_len = perimeter * density_factor

        # Geometric complexity: curvature and linework concentration relative to dimension
        characteristic_dim = math.sqrt(w * h)
        geom_complexity = max(0.5, round(arc_len / max(40.0, characteristic_dim), 2))
        spatial_density = max(0.5, round(arc_len / max(50.0, 2.0 * (w + h)), 2))
        
        # Physical effort combining length and complexity
        effort = arc_len * (1.0 + 0.10 * min(5.0, geom_complexity))

        return DrawingDemand(
            arc_length_px=round(arc_len, 1),
            stroke_count=max(1, n_strokes),
            point_count=max(10, n_pts),
            geometric_complexity=geom_complexity,
            spatial_density=spatial_density,
            estimated_physical_effort=round(effort, 1)
        )

    @classmethod
    def calculate_nominal_draw_time(cls, demand: DrawingDemand) -> float:
        """
        Calibrated Physical Model: computes nominal drawing time from physical effort
        and calibrated pen velocity. Replaces fixed duration presets.
        """
        nominal_time = demand.estimated_physical_effort / max(100.0, cls.calibrated_pen_velocity)
        return max(cls.MIN_ELEMENT_DURATION, min(cls.MAX_ELEMENT_DURATION, round(nominal_time, 3)))

    @classmethod
    def evaluate_speed_feasibility(
        cls,
        demand: DrawingDemand,
        allocated_duration: float
    ) -> Tuple[SpeedFeasibility, float, float]:
        """
        Evaluates whether allocated duration requires physically natural drawing speed.
        Returns (feasibility_status, effective_speed_px_s, speed_multiplier).
        """
        dur = max(0.05, allocated_duration)
        nominal_time = cls.calculate_nominal_draw_time(demand)
        effective_speed = demand.arc_length_px / dur
        speed_mult = round(nominal_time / dur, 2)

        if speed_mult <= 1.25 and effective_speed <= cls.calibrated_pen_velocity * 1.25:
            status = SpeedFeasibility.NORMAL
        elif speed_mult <= 1.75 and effective_speed <= cls.SPEED_SAFE_LIMIT * 0.85:
            status = SpeedFeasibility.FAST
        elif speed_mult <= cls.MAX_SPEED_MULTIPLIER and effective_speed <= cls.SPEED_SAFE_LIMIT:
            status = SpeedFeasibility.LIMITED
        else:
            status = SpeedFeasibility.INFEASIBLE

        return status, effective_speed, speed_mult

    @classmethod
    def solve_beat(
        cls,
        beat: VisualBeat,
        speech_density: float = 12.0,
        available_pause: float = 0.0,
        available_pre_speech: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Solves Content-Aware Timing for all elements inside a single Visual Beat.
        Implements Calibrated Physical Model, Speed Feasibility Analysis,
        6-step Resolution Search, and Timing Conflict Handling.
        """
        elements = beat.elements
        if not elements:
            beat.timing_decisions = []
            beat.timing_conflicts = []
            return []

        beat_start = beat.start
        beat_end = beat.end
        speech_dur = max(0.1, beat_end - beat_start)

        # Build Drawing Demand for all elements
        demands: Dict[str, DrawingDemand] = {}
        for idx, elem in enumerate(elements):
            e_id = elem.get("id", f"elem_{idx+1}")
            demands[e_id] = cls.calculate_drawing_demand(elem)
        beat.drawing_demands = demands

        # Categorize into Tiers (Tiers govern semantic protection & hold, NOT drawing duration directly)
        categorized_elems: List[Tuple[Dict[str, Any], ElementTier, DrawingDemand, float]] = []
        for idx, elem in enumerate(elements):
            e_id = elem.get("id", f"elem_{idx+1}")
            tier = beat.get_element_tier(elem)
            demand = demands[e_id]
            nominal_t = cls.calculate_nominal_draw_time(demand)
            categorized_elems.append((elem, tier, demand, nominal_t))

        # Build Semantic Anchor Lookup (rich model)
        anchors_by_elem: Dict[str, SemanticAnchor] = {}
        # 1. From explicit semantic_anchors
        for sa in beat.semantic_anchors:
            if sa.target_element:
                anchors_by_elem[sa.target_element.lower()] = sa
            if sa.source_token:
                anchors_by_elem[sa.source_token.lower()] = sa
        # 2. From backwards-compatible emphasis_points
        for ep in beat.emphasis_points:
            ep_text = ep.text.lower()
            if ep.element_id:
                anchors_by_elem[ep.element_id.lower()] = SemanticAnchor(
                    source="speech_landmark",
                    source_text=ep.text,
                    source_token=ep.text,
                    source_type=AnchorSourceType.NUMBER if ("%" in ep.text or ep.text.isdigit()) else AnchorSourceType.OBJECT,
                    target_element=ep.element_id,
                    target_time=ep.target_time if ep.target_time is not None else beat_start,
                    anchor_type=AnchorType.EMPHASIS,
                    confidence=0.90,
                    tolerance=0.18
                )
            elif ep_text:
                anchors_by_elem[ep_text] = SemanticAnchor(
                    source="speech_landmark",
                    source_text=ep.text,
                    source_token=ep.text,
                    source_type=AnchorSourceType.NUMBER if ("%" in ep.text or ep.text.isdigit()) else AnchorSourceType.OBJECT,
                    target_element="",
                    target_time=ep.target_time if ep.target_time is not None else beat_start,
                    anchor_type=AnchorType.EMPHASIS,
                    confidence=0.85,
                    tolerance=0.20
                )

        # Dynamic Temporal Budgeting: absorb trailing pause safely
        absorbable_pause = min(available_pause, 1.20)
        effective_end = beat_end + absorbable_pause
        total_time_budget = speech_dur + absorbable_pause

        # Compute dynamic hold duration based on focal primary element demand
        has_primary = any(t == ElementTier.PRIMARY for _, t, _, _ in categorized_elems)
        base_hold = beat.hold_duration if has_primary else max(cls.MIN_HOLD_DURATION, beat.hold_duration * 0.6)
        available_draw_budget = max(0.25, total_time_budget - base_hold)

        # Calculate sum of nominal times
        total_nominal_time = sum(nom_t for _, _, _, nom_t in categorized_elems)

        # Dynamic overlap score calculation between successive elements
        def compute_dynamic_overlap(idx: int, prev_tier: ElementTier, curr_tier: ElementTier) -> float:
            if beat.overlap_policy == OverlapPolicy.NONE:
                return 0.0
            # Container-child or dependent relationship
            if prev_tier == ElementTier.PRIMARY and curr_tier == ElementTier.SECONDARY:
                score = 0.35 if beat.overlap_policy == OverlapPolicy.NATURAL else 0.20
            elif prev_tier == curr_tier:
                score = 0.25 if beat.overlap_policy == OverlapPolicy.NATURAL else 0.15
            else:
                score = 0.15 if beat.overlap_policy == OverlapPolicy.NATURAL else 0.08
            return score

        # Multi-pass schedule resolution
        scheduled_elements: List[Dict[str, Any]] = []
        decisions: List[TimingDecision] = []
        conflicts: List[TimingConflict] = []

        curr_time = beat_start
        min_drawing_start = beat_start
        max_drawing_end = beat_start

        for idx, (elem, tier, demand, nominal_dur) in enumerate(categorized_elems):
            e_copy = dict(elem)
            e_id = e_copy.get("id", f"elem_{idx+1}")
            e_name = e_copy.get("name", e_id)

            # Check for bound Semantic Anchor
            anchor = anchors_by_elem.get(e_id.lower()) or anchors_by_elem.get(e_name.lower())
            if not anchor:
                # Fuzzy token match
                for token_key, cand_anchor in anchors_by_elem.items():
                    if token_key in e_name.lower() or (token_key.isdigit() and token_key in e_name):
                        anchor = cand_anchor
                        break

            # Initial duration target based on physical demand & tier protection
            if speech_density > 16.0:
                pace_multiplier = 0.75
                max_budget_scale = 1.0
            elif speech_density < 8.0:
                pace_multiplier = 1.50
                max_budget_scale = 2.4
            else:
                pace_multiplier = 1.0
                max_budget_scale = 1.30

            budget_ratio = available_draw_budget / max(0.1, total_nominal_time)
            if budget_ratio >= 1.0:
                if tier == ElementTier.PRIMARY:
                    scale = min(max_budget_scale, budget_ratio)
                elif tier == ElementTier.SECONDARY:
                    scale = min(max_budget_scale * 0.95, budget_ratio * 0.90)
                else:
                    scale = min(max_budget_scale * 0.85, budget_ratio * 0.70)
            else:
                # Tight budget: scale proportionally with tier weighting so sum of all durations fits in budget
                if tier == ElementTier.PRIMARY:
                    scale = max(0.15, budget_ratio * 1.25)
                elif tier == ElementTier.SECONDARY:
                    scale = max(0.12, budget_ratio * 0.95)
                else:
                    scale = max(0.08, budget_ratio * 0.70)

            allocated_dur = max(cls.MIN_ELEMENT_DURATION, round(nominal_dur * pace_multiplier * scale, 2))

            # Bound allocated duration so no single element starves remaining elements in dense panels
            avg_slot = available_draw_budget / float(max(1, len(categorized_elems)))
            slot_mult = 1.35 if len(categorized_elems) > 8 else 2.6
            max_elem_share = max(cls.MIN_ELEMENT_DURATION, avg_slot * slot_mult)
            allocated_dur = min(max_elem_share, allocated_dur)
            allocated_dur = max(cls.MIN_ELEMENT_DURATION, round(allocated_dur, 2))

            # Feasibility Check & Resolution Search
            feasibility, eff_speed, speed_mult = cls.evaluate_speed_feasibility(demand, allocated_dur)
            anticipation = 0.0
            resolution_log = "Direct physical allocation"

            if feasibility == SpeedFeasibility.INFEASIBLE:
                # --- Step 1: Extend drawing window into available pause ---
                if absorbable_pause > 0.1:
                    extra_time = min(absorbable_pause, allocated_dur * 0.4)
                    allocated_dur += extra_time
                    feasibility, eff_speed, speed_mult = cls.evaluate_speed_feasibility(demand, allocated_dur)
                    resolution_log = f"Extended into pause (+{extra_time:.2f}s)"

                # --- Step 2: Use anticipation / lead-in before speech start ---
                if feasibility == SpeedFeasibility.INFEASIBLE and available_pre_speech > 0.1 and idx == 0:
                    lead_in = min(available_pre_speech, allocated_dur * 0.5)
                    anticipation = lead_in
                    allocated_dur += lead_in
                    feasibility, eff_speed, speed_mult = cls.evaluate_speed_feasibility(demand, allocated_dur)
                    resolution_log += f" | Applied lead-in anticipation ({lead_in:.2f}s)"

                # --- Step 3: Increase dynamic overlap with adjacent elements ---
                if feasibility == SpeedFeasibility.INFEASIBLE and idx > 0:
                    allocated_dur = max(allocated_dur, nominal_dur * 0.75)
                    feasibility, eff_speed, speed_mult = cls.evaluate_speed_feasibility(demand, allocated_dur)
                    resolution_log += " | Increased dynamic overlap"

                # --- Step 4: Level-Of-Detail (LOD) subsampling ---
                if feasibility == SpeedFeasibility.INFEASIBLE:
                    # Simplify detail rendering load by 25%
                    reduced_demand = DrawingDemand(
                        arc_length_px=demand.arc_length_px * 0.75,
                        stroke_count=demand.stroke_count,
                        point_count=int(demand.point_count * 0.70),
                        geometric_complexity=demand.geometric_complexity * 0.85,
                        spatial_density=demand.spatial_density * 0.85,
                        estimated_physical_effort=demand.estimated_physical_effort * 0.75
                    )
                    feasibility, eff_speed, speed_mult = cls.evaluate_speed_feasibility(reduced_demand, allocated_dur)
                    resolution_log += " | Applied Level-Of-Detail reduction (25%)"

                # --- Step 5: Mark Timing Conflict if still exceeding physical limits ---
                if feasibility == SpeedFeasibility.INFEASIBLE:
                    # Cap speed at safe ceiling and record conflict
                    allocated_dur = max(cls.MIN_ELEMENT_DURATION, demand.arc_length_px / cls.SPEED_SAFE_LIMIT)
                    feasibility = SpeedFeasibility.LIMITED
                    speed_mult = min(cls.MAX_SPEED_MULTIPLIER, cls.SPEED_SAFE_LIMIT / cls.calibrated_pen_velocity)
                    
                    conflict = TimingConflict(
                        conflict_type=ConflictType.SPEED_CONFLICT,
                        severity=ConflictSeverity.HIGH if tier == ElementTier.PRIMARY else ConflictSeverity.MEDIUM,
                        affected_elements=[e_id],
                        description=f"Element '{e_name}' physical demand ({demand.arc_length_px:.0f}px) requires speed exceeding physical ceiling ({cls.SPEED_SAFE_LIMIT:.0f}px/s).",
                        resolution_attempted=resolution_log + " -> Capped at physical speed limit."
                    )
                    conflicts.append(conflict)

            # Strict guard for dense panels: never allow one element to consume more than its bounded share
            allocated_dur = min(max_elem_share, allocated_dur)
            allocated_dur = max(cls.MIN_ELEMENT_DURATION, round(allocated_dur, 2))

            # Anchor Alignment & Window Scheduling
            if anchor and anchor.target_time > 0.0:
                target_t = float(anchor.target_time)
                tol = anchor.tolerance

                if anchor.anchor_type == AnchorType.EMPHASIS:
                    # Drawing must finish precisely at keyword instant
                    # Compute lead-in budget dynamically
                    lead_in_budget = min(
                        available_pre_speech + (target_t - beat_start),
                        allocated_dur * (0.35 + 0.30 * anchor.confidence)
                    )
                    en = target_t
                    st = max(beat_start - lead_in_budget, en - allocated_dur)
                    allocated_dur = max(cls.MIN_ELEMENT_DURATION, en - st)
                    
                    # Check if anchor is physically unachievable (Anchor Conflict)
                    if st < (beat_start - available_pre_speech - 0.05):
                        conflict = TimingConflict(
                            conflict_type=ConflictType.ANCHOR_CONFLICT,
                            severity=ConflictSeverity.HIGH,
                            affected_elements=[e_id],
                            description=f"Anchor for '{anchor.source_token}' at {target_t:.2f}s requires drawing to start at {st:.2f}s, exceeding pre-speech budget.",
                            resolution_attempted=f"Shifted start to {beat_start - available_pre_speech:.2f}s; reveal completed with delta."
                        )
                        conflicts.append(conflict)
                        st = beat_start - available_pre_speech
                        en = st + allocated_dur

                    anticipation = max(0.0, beat_start - st)
                    reason = f"Semantic emphasis (Anchor EMPHASIS '{anchor.source_token}') @ {target_t:.2f}s ({resolution_log})"

                elif anchor.anchor_type == AnchorType.LEAD_IN:
                    # Drawing leads ahead of speech
                    lead_in = min(available_pre_speech, allocated_dur * 0.60)
                    st = max(beat_start - lead_in, beat_start - available_pre_speech)
                    en = st + allocated_dur
                    anticipation = beat_start - st
                    reason = f"Semantic Anchor LEAD_IN '{anchor.source_token}' ({resolution_log})"

                else: # DURING or TRAILING
                    st = max(beat_start, curr_time)
                    en = st + allocated_dur
                    reason = f"Semantic Anchor {anchor.anchor_type.value} '{anchor.source_token}' ({resolution_log})"

                curr_time = en
            else:
                # Sequential / Overlapped Scheduling without explicit anchor
                if curr_time >= effective_end - cls.MIN_ELEMENT_DURATION:
                    # Drawing budget exhausted -> register DRAWING_BUDGET_CONFLICT
                    remaining_count = max(1, len(categorized_elems) - idx)
                    slot_dur = max(0.08, cls.MIN_ELEMENT_DURATION / float(remaining_count))
                    st = min(effective_end - 0.08, curr_time)
                    en = min(effective_end, st + slot_dur)
                    allocated_dur = max(0.08, en - st)
                    curr_time = en
                    conflict = TimingConflict(
                        conflict_type=ConflictType.DRAWING_BUDGET_CONFLICT,
                        severity=ConflictSeverity.HIGH if tier == ElementTier.PRIMARY else ConflictSeverity.MEDIUM,
                        affected_elements=[e_id],
                        description=f"Drawing budget exhausted in beat '{beat.id}' for element '{e_name}' ({demand.arc_length_px:.0f}px linework).",
                        resolution_attempted="Distributed sequentially into compressed remaining slots of beat window."
                    )
                    conflicts.append(conflict)
                    reason = f"Budget compressed schedule ({tier.value}, DRAWING_BUDGET_CONFLICT)"
                else:
                    st = max(beat_start, curr_time)
                    en = min(effective_end, st + allocated_dur)
                    allocated_dur = max(cls.MIN_ELEMENT_DURATION, en - st)

                    # Compute dynamic overlap for next element
                    if idx < len(categorized_elems) - 1:
                        next_tier = categorized_elems[idx + 1][1]
                        ov_score = compute_dynamic_overlap(idx, tier, next_tier)
                        curr_time = min(effective_end - cls.MIN_ELEMENT_DURATION, max(beat_start, st + allocated_dur * (1.0 - ov_score)))
                    else:
                        curr_time = en

                    reason = f"Physical demand schedule ({tier.value}, effort: {demand.estimated_physical_effort:.0f})"

            # Re-evaluate final speed and feasibility for the actual final allocated duration
            final_feasibility, final_eff_speed, final_speed_mult = cls.evaluate_speed_feasibility(demand, allocated_dur)
            final_speed_mult = max(cls.MIN_SPEED_MULTIPLIER, min(cls.MAX_SPEED_MULTIPLIER, final_speed_mult))

            min_drawing_start = min(min_drawing_start, st)
            max_drawing_end = max(max_drawing_end, en)

            # Hold duration assignment (Primary gets prominent focus)
            elem_hold = base_hold if tier == ElementTier.PRIMARY else base_hold * 0.50
            elem_hold = round(max(cls.MIN_HOLD_DURATION, elem_hold), 2)

            speed_mult_rounded = round(final_speed_mult, 2)
            st_rounded = round(st, 2)
            en_rounded = round(en, 2)
            dur_rounded = round(allocated_dur, 2)

            e_copy["sync_start"] = st_rounded
            e_copy["sync_end"] = en_rounded
            e_copy["sync_duration"] = dur_rounded
            e_copy["hold_duration"] = elem_hold
            e_copy["speed_multiplier"] = speed_mult_rounded
            e_copy["tier"] = tier.value
            e_copy["visual_beat_id"] = beat.id

            decision = TimingDecision(
                element_id=e_id,
                element_name=e_name,
                tier=tier.value,
                start=st_rounded,
                end=en_rounded,
                duration=dur_rounded,
                hold_duration=elem_hold,
                reason=reason,
                anticipation=round(anticipation, 2),
                speed_multiplier=speed_mult_rounded,
                demand=demand,
                feasibility=feasibility
            )
            decisions.append(decision)
            scheduled_elements.append(e_copy)

        # Update VisualBeat internal windows
        beat.speech_window = (round(beat_start, 2), round(beat_end, 2))
        beat.drawing_window = (round(min_drawing_start, 2), round(max_drawing_end, 2))
        hold_end = max(beat_end, max_drawing_end + base_hold)
        beat.hold_window = (round(max_drawing_end, 2), round(hold_end, 2))
        beat.timing_decisions = decisions
        beat.timing_conflicts = conflicts

        return scheduled_elements

    @classmethod
    def solve_storyboard(
        cls,
        visual_beats: List[VisualBeat],
        total_audio_duration: float,
        return_transitions: bool = False
    ) -> Any:
        """
        Global multi-beat solver.
        Solves Content-Aware timing for each beat and computes explicit BeatTransition
        relationships connecting successive beats without temporal collision.
        If return_transitions is True, returns (visual_beats, transitions).
        Otherwise returns visual_beats for backward compatibility.
        """
        if not visual_beats:
            return ([], []) if return_transitions else []

        # 1. Adjust beat boundaries to cover audio track smoothly without gaps
        num_beats = len(visual_beats)
        for i in range(num_beats - 1):
            curr_b = visual_beats[i]
            next_b = visual_beats[i + 1]
            if curr_b.transition_policy == TransitionPolicy.OVERLAP:
                trans_window = min(0.40, curr_b.duration * 0.15)
                next_b.start = max(curr_b.start + 0.2, curr_b.end - trans_window)
            elif next_b.start < curr_b.end:
                curr_b.end = next_b.start

        # Clamp final beat to audio duration
        if visual_beats:
            visual_beats[-1].end = max(visual_beats[-1].start + 0.5, total_audio_duration)

        # 2. Solve each beat individually with pre-speech and pause awareness
        for i, beat in enumerate(visual_beats):
            pre_speech = 0.0
            if i > 0:
                gap_prev = beat.start - visual_beats[i - 1].end
                if gap_prev > 0:
                    pre_speech = min(gap_prev * 0.6, 0.60)
            elif beat.start > 0:
                pre_speech = min(beat.start, 0.50)

            pause_after = 0.0
            if i < num_beats - 1:
                gap_next = visual_beats[i + 1].start - beat.end
                if gap_next > 0:
                    pause_after = gap_next

            beat.elements = cls.solve_beat(
                beat,
                speech_density=12.0,
                available_pause=pause_after,
                available_pre_speech=pre_speech
            )

        # 3. Compute explicit inter-beat BeatTransition objects
        transitions: List[BeatTransition] = []
        for i in range(num_beats - 1):
            curr_b = visual_beats[i]
            next_b = visual_beats[i + 1]

            t_start = curr_b.hold_window[0] if curr_b.hold_window[0] > 0 else curr_b.drawing_window[1]
            t_end = next_b.drawing_window[0]

            # Determine transition type & strategy
            if curr_b.transition_policy == TransitionPolicy.OVERLAP:
                trans_type = TransitionPolicy.OVERLAP
                strategy = f"Anticipatory overlap: {next_b.id} drawing begins during {curr_b.id} hold"
            elif curr_b.transition_policy == TransitionPolicy.REPLACE:
                trans_type = TransitionPolicy.REPLACE
                strategy = f"Clear previous canvas before {next_b.id} begins"
            else:
                trans_type = TransitionPolicy.KEEP
                strategy = f"Additive hold: canvas retained as {next_b.id} commences"

            trans = BeatTransition(
                from_beat_id=curr_b.id,
                to_beat_id=next_b.id,
                start=round(t_start, 2),
                end=round(max(t_start, t_end), 2),
                transition_type=trans_type,
                strategy=strategy
            )
            transitions.append(trans)

        if return_transitions:
            return visual_beats, transitions
        return visual_beats
