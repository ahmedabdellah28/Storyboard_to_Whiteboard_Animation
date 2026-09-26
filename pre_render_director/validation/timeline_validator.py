"""Comprehensive Timeline Validator executing all 12 Pre-Render Checks."""

from typing import List, Dict, Any, Tuple, Optional
from ..models.input import AssetCatalog, SectionInput
from ..models.output import (
    ValidationCheckResult,
    ValidationReport,
    ValidationStatus
)
from .asset_validator import validate_asset_references, validate_semantic_matches
from .dependency_validator import validate_asset_dependencies

class TimelineValidator:
    """Executes the 12 Pre-Render Validation Checks and computes overall status."""

    def __init__(
        self,
        audio_duration: float,
        catalog: AssetCatalog,
        max_density: int = 6,
        min_draw_duration: float = 0.5
    ):
        self.audio_duration = audio_duration
        self.catalog = catalog
        self.max_density = max_density
        self.min_draw_duration = min_draw_duration

    def validate_all(
        self,
        events: List[Dict[str, Any]],
        evaluation_results: Optional[List[Dict[str, Any]]] = None,
        sfx_events: Optional[List[Dict[str, Any]]] = None,
        camera_events: Optional[List[Dict[str, Any]]] = None,
        visual_states: Optional[List[Any]] = None
    ) -> ValidationReport:
        checks: List[ValidationCheckResult] = []
        evaluation_results = evaluation_results or []
        sfx_events = sfx_events or []
        camera_events = camera_events or []

        # CHECK 01 & 02: Asset references and disk existence
        c1, c2 = validate_asset_references(events, self.catalog)
        checks.extend([c1, c2])

        # CHECK 03 & 04: Semantic match & contradiction detection
        c3, c4 = validate_semantic_matches(evaluation_results)
        checks.extend([c3, c4])

        # CHECK 05: Dependencies
        c5 = validate_asset_dependencies(events, self.catalog)
        checks.append(c5)

        # CHECK 06: Drawing duration is feasible
        c6_details = []
        for ev in events:
            eid = ev.get("event_id") or ev.get("id", "UNKNOWN")
            dur = float(ev.get("duration_s", 0.0))
            atype = ev.get("type", "draw")
            if atype == "draw" and dur < self.min_draw_duration:
                c6_details.append(f"Event {eid} duration {dur:.2f}s is below minimum feasible threshold {self.min_draw_duration}s.")
        checks.append(ValidationCheckResult(
            check_id="CHECK_06",
            name="Drawing duration is feasible",
            passed=(len(c6_details) == 0),
            severity="WARNING",
            details=c6_details
        ))

        # CHECK 07: No impossible timing
        c7_details = []
        for ev in events:
            eid = ev.get("event_id") or ev.get("id", "UNKNOWN")
            st = float(ev.get("start_s", 0.0))
            en = float(ev.get("end_s", 0.0))
            if st < 0.0:
                c7_details.append(f"Event {eid} has negative start time ({st}s).")
            if en <= st:
                c7_details.append(f"Event {eid} has invalid interval: start={st}s, end={en}s.")
            if self.audio_duration > 0 and en > self.audio_duration + 0.5:
                c7_details.append(f"Event {eid} ends at {en}s, exceeding audio duration {self.audio_duration}s.")
        checks.append(ValidationCheckResult(
            check_id="CHECK_07",
            name="No impossible timing",
            passed=(len(c7_details) == 0),
            severity="ERROR",
            details=c7_details
        ))

        # CHECK 08: No invalid overlaps
        # Checks whether drawings overlap inappropriately without being parallel
        c8_details = []
        sorted_draws = sorted(
            [e for e in events if e.get("type", "draw") == "draw"],
            key=lambda x: float(x.get("start_s", 0.0))
        )
        for i in range(len(sorted_draws) - 1):
            curr = sorted_draws[i]
            nxt = sorted_draws[i + 1]
            c_end = float(curr.get("end_s", 0.0))
            n_start = float(nxt.get("start_s", 0.0))
            # If next starts before current finishes by more than 0.8s and neither allows parallel
            if (c_end - n_start) > 0.8:
                c_id = curr.get("event_id") or curr.get("id")
                n_id = nxt.get("event_id") or nxt.get("id")
                c8_details.append(f"Excessive drawing collision between {c_id} (ends {c_end:.2f}s) and {n_id} (starts {n_start:.2f}s).")
        checks.append(ValidationCheckResult(
            check_id="CHECK_08",
            name="No invalid overlaps",
            passed=(len(c8_details) == 0),
            severity="WARNING",
            details=c8_details
        ))

        # CHECK 09: SFX has valid anchor
        c9_details = []
        draw_ids = {e.get("event_id") or e.get("id") for e in events}
        draw_assets = {e.get("asset_id") for e in events if e.get("asset_id")}
        for sfx in sfx_events:
            sid = sfx.get("event_id") or sfx.get("id", "SFX")
            aid = sfx.get("anchor_asset_id") or sfx.get("asset_id")
            eid_anchor = sfx.get("anchor_event_id")
            if aid and (aid not in draw_assets):
                c9_details.append(f"SFX {sid} references asset '{aid}' not present in drawing timeline.")
            if eid_anchor and (eid_anchor not in draw_ids):
                c9_details.append(f"SFX {sid} references event '{eid_anchor}' which does not exist.")
        checks.append(ValidationCheckResult(
            check_id="CHECK_09",
            name="SFX has valid anchor",
            passed=(len(c9_details) == 0),
            severity="WARNING",
            details=c9_details
        ))

        # CHECK 10: Camera target exists
        c10_details = []
        for cam in camera_events:
            cid = cam.get("event_id") or cam.get("id", "CAM")
            target = cam.get("target_asset_id")
            if target and not self.catalog.contains(target):
                c10_details.append(f"Camera event {cid} targets unknown asset '{target}'.")
        checks.append(ValidationCheckResult(
            check_id="CHECK_10",
            name="Camera target exists",
            passed=(len(c10_details) == 0),
            severity="WARNING",
            details=c10_details
        ))

        # CHECK 11: Visual state transitions are valid
        c11_details = []
        if visual_states:
            for i in range(len(visual_states) - 1):
                s1 = visual_states[i]
                s2 = visual_states[i+1]
                t1 = getattr(s1, "time_s", 0.0)
                t2 = getattr(s2, "time_s", 0.0)
                if t2 < t1:
                    c11_details.append(f"Visual state timestamps out of chronological order: {t1}s -> {t2}s.")
        checks.append(ValidationCheckResult(
            check_id="CHECK_11",
            name="Visual state transitions are valid",
            passed=(len(c11_details) == 0),
            severity="ERROR",
            details=c11_details
        ))

        # CHECK 12: No excessive visual density
        c12_details = []
        if visual_states:
            for s in visual_states:
                d = getattr(s, "density", 0)
                t = getattr(s, "time_s", 0.0)
                if d > self.max_density:
                    c12_details.append(f"Canvas density {d} exceeds max allowed {self.max_density} at t={t:.2f}s.")
        checks.append(ValidationCheckResult(
            check_id="CHECK_12",
            name="No excessive visual density",
            passed=(len(c12_details) == 0),
            severity="WARNING",
            details=c12_details
        ))

        # Compile overall status and issues
        unresolved: List[str] = []
        has_error = False
        has_warning = False

        for c in checks:
            if not c.passed:
                unresolved.extend(c.details)
                if c.severity == "ERROR":
                    has_error = True
                elif c.severity == "WARNING":
                    has_warning = True

        if has_error:
            status = ValidationStatus.BLOCK_RENDER
        elif has_warning:
            status = ValidationStatus.PASS_WITH_WARNINGS
        else:
            status = ValidationStatus.PASS

        score = max(0.0, 1.0 - (len(unresolved) * 0.08))

        return ValidationReport(
            status=status,
            overall_score=round(score, 2),
            checks=checks,
            unresolved_issues=unresolved,
            review_required=(status == ValidationStatus.BLOCK_RENDER or score < 0.75)
        )

def run_all_pre_render_checks(
    section_input: SectionInput,
    events: List[Dict[str, Any]],
    evaluation_results: Optional[List[Dict[str, Any]]] = None,
    sfx_events: Optional[List[Dict[str, Any]]] = None,
    camera_events: Optional[List[Dict[str, Any]]] = None,
    visual_states: Optional[List[Any]] = None
) -> ValidationReport:
    """Convenience helper to run all 12 checks."""
    catalog = AssetCatalog(assets=section_input.assets)
    validator = TimelineValidator(
        audio_duration=section_input.audio_duration,
        catalog=catalog
    )
    return validator.validate_all(
        events=events,
        evaluation_results=evaluation_results,
        sfx_events=sfx_events,
        camera_events=camera_events,
        visual_states=visual_states
    )
