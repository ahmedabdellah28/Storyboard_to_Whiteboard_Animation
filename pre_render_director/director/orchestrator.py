"""Director Orchestrator managing the multi-iteration validation and patch loop."""

import copy
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from ..models.input import SectionInput, AssetCatalog, AssetMetadata
from ..models.event import RenderEvent, ActionType, TimingStrategy, SFXEvent, CameraEvent
from ..models.patch import TimelinePatch, PatchOperation, PatchBatch
from ..models.output import (
    FinalRenderPlan,
    ValidationReport,
    ValidationStatus,
    VisualStateSnapshot
)
from ..ai.provider import AIProvider, get_ai_provider
from .semantic_validator import SemanticValidator
from .temporal_validator import TemporalValidator
from .visual_state_analyzer import VisualStateAnalyzer
from .density_controller import DensityController
from .patch_generator import PatchGenerator, apply_patch_batch
from ..validation.timeline_validator import TimelineValidator

logger = logging.getLogger("VisualDirector")

class DirectorOrchestrator:
    """Senior Visual Director Orchestrator executing the iterative refinement loop."""

    def __init__(
        self,
        ai_provider: Optional[AIProvider] = None,
        max_iterations: int = 3,
        confidence_threshold: float = 0.65,
        max_density: int = 12
    ):
        self.ai_provider = ai_provider or get_ai_provider()
        self.max_iterations = max_iterations
        self.confidence_threshold = confidence_threshold
        self.max_density = max_density

    def execute(self, section_input: SectionInput) -> Tuple[FinalRenderPlan, Dict[str, Any]]:
        """Executes the complete Pre-Render Visual Director loop."""
        catalog = AssetCatalog(assets=section_input.assets)
        duration = section_input.audio_duration
        semantic_val = SemanticValidator(ai_provider=self.ai_provider)
        temporal_val = TemporalValidator(audio_duration=duration)
        state_analyzer = VisualStateAnalyzer(audio_duration=duration)
        density_ctrl = DensityController(max_concurrent=self.max_density)
        timeline_val = TimelineValidator(audio_duration=duration, catalog=catalog, max_density=self.max_density)

        # 1. Normalize Initial Events
        current_events: List[Dict[str, Any]] = []
        for d in section_input.initial_drawings:
            ev = copy.deepcopy(d)
            if "id" in ev and "event_id" not in ev:
                ev["event_id"] = ev["id"]
            if "start_s" not in ev and "start" in ev:
                ev["start_s"] = float(ev["start"])
            if "end_s" not in ev and "end" in ev:
                ev["end_s"] = float(ev["end"])
            if "duration_s" not in ev:
                ev["duration_s"] = round(float(ev.get("end_s", 0.0)) - float(ev.get("start_s", 0.0)), 3)
            current_events.append(ev)

        # Map words by anchor text or time
        words_list = section_input.words
        all_applied_patches: List[TimelinePatch] = []
        review_items: List[Dict[str, Any]] = []
        missing_assets: List[Dict[str, str]] = []

        # 2. Main Iterative Loop (max_iterations)
        final_validation: Optional[ValidationReport] = None
        visual_states: List[VisualStateSnapshot] = []

        for iteration in range(1, self.max_iterations + 1):
            patches_this_iter: List[TimelinePatch] = []
            evaluation_results: List[Dict[str, Any]] = []
            print(f"\n[Iteration {iteration}/{self.max_iterations}] Analyzing {len(current_events)} visual events...", flush=True)

            # A. Evaluate Each Event
            for i, ev in enumerate(current_events):
                eid = ev.get("event_id") or ev.get("id")
                aid = ev.get("asset_id")
                asset = catalog.get(aid) if aid else None
                anchor_text = ev.get("anchor_text", "")
                print(f"   -> Event {i+1:02d}/{len(current_events):02d} [{eid}]: '{anchor_text[:28]}...' (asset: {aid})", flush=True)

                # Context look-behind & look-ahead
                prev_ev = current_events[i - 1] if i > 0 else None
                next_ev = current_events[i + 1] if i < len(current_events) - 1 else None

                ev_st = float(ev.get("start_s", 0.0))
                ev_en = float(ev.get("end_s", ev_st + 2.0))

                ARABIC_STOPWORDS = {"من", "في", "على", "إلى", "عن", "مع", "أو", "و", "ثم", "إن", "أن", "ما", "هو", "هي", "هل", "قد", "لو", "كان", "كل"}

                # Find matching words for anchor within tight temporal vicinity (+- 1.5s)
                local_words = [
                    w for w in words_list
                    if (ev_st - 1.5 <= w.start <= ev_en + 1.5)
                ]
                matched_words = [
                    w.model_dump() for w in local_words
                    if (w.text.strip("،.؟!-") in anchor_text) or (w.text in anchor_text)
                ]
                # Prioritize content words to avoid trailing stopwords
                content_words = [
                    w for w in matched_words
                    if w["text"].strip("،.؟!-") not in ARABIC_STOPWORDS and len(w["text"].strip("،.؟!-")) > 1
                ]
                active_words = content_words if content_words else matched_words

                anchor_start = float(active_words[0]["start"]) if active_words else ev_st
                anchor_end = float(active_words[-1]["end"]) if active_words else ev_en

                speech_ctx = {
                    "anchor_text": anchor_text,
                    "words": matched_words,
                    "audio_total_duration": duration
                }

                # Semantic & Contradiction Evaluation
                sem_res = semantic_val.validate(
                    event_id=eid,
                    asset=asset,
                    anchor_text=anchor_text,
                    speech_context=speech_ctx,
                    look_behind=prev_ev,
                    look_ahead=next_ev
                )
                evaluation_results.append({
                    "event_id": eid,
                    "asset_id": aid,
                    "semantic_match": sem_res.status.value,
                    "contradiction_detected": sem_res.is_contradictory,
                    "contradiction_reason": sem_res.contradiction_reason,
                    "confidence": sem_res.confidence
                })

                # Check if review is required
                if sem_res.confidence < self.confidence_threshold:
                    review_items.append({
                        "event_id": eid,
                        "type": "SEMANTIC_UNCERTAINTY",
                        "confidence": sem_res.confidence,
                        "reason": sem_res.reason
                    })

                # If Contradiction Detected: Propose Patch
                if sem_res.is_contradictory:
                    # Look for replacement asset in catalog
                    from .asset_match_validator import AssetMatchValidator
                    match_val = AssetMatchValidator(catalog)
                    best_cand, score, _ = match_val.find_best_asset(anchor_text, [anchor_text])
                    if best_cand and best_cand.asset_id != aid:
                        patch = PatchGenerator.create_change_asset_patch(
                            event_id=eid,
                            from_asset=aid,
                            to_asset=best_cand.asset_id,
                            reason=f"Resolved contradiction: {sem_res.contradiction_reason}. Replaced with {best_cand.asset_id}."
                        )
                        patches_this_iter.append(patch)
                    else:
                        missing_assets.append({
                            "anchor_text": anchor_text,
                            "semantic_concept": anchor_text,
                            "event_id": eid
                        })

                # B. Temporal Validation & Inking Completion Synchronization
                drawing_demand = asset.drawing_demand if asset else float(ev.get("duration_s", 1.8))
                prev_end = float(prev_ev.get("end_s", 0.0)) if prev_ev else 0.0
                opt_start, opt_end, opt_dur = temporal_val.compute_optimal_timing(
                    anchor_start=anchor_start,
                    anchor_end=anchor_end,
                    drawing_demand=drawing_demand,
                    strategy=TimingStrategy.START_ON_ANCHOR,
                    prev_event_end=prev_end
                )

                curr_start = float(ev.get("start_s", 0.0))
                curr_end = float(ev.get("end_s", 0.0))

                # If current timing is uncalibrated or significantly offset
                if ev.get("confidence", 0.0) < 0.95 and (abs(curr_start - opt_start) > 0.35 or abs(curr_end - opt_end) > 0.35):
                    p = PatchGenerator.create_timing_update_patch(
                        event_id=eid,
                        start_s=opt_start,
                        end_s=opt_end,
                        reason="Adjusted timing so drawing inking begins on the spoken semantic anchor."
                    )
                    patches_this_iter.append(p)

            # C. Visual State & Density Check
            visual_states = state_analyzer.compute_visual_states(current_events)
            density_patches = density_ctrl.check_and_relieve_density(current_events, visual_states)
            patches_this_iter.extend(density_patches)

            # D. Validation Check
            val_report = timeline_val.validate_all(
                events=current_events,
                evaluation_results=evaluation_results,
                sfx_events=section_input.initial_sfx,
                camera_events=section_input.initial_camera,
                visual_states=visual_states
            )
            final_validation = val_report

            # If no patches needed or valid PASS reached, exit loop
            if not patches_this_iter:
                break

            # E. Apply Patches
            current_events, batch = apply_patch_batch(current_events, patches_this_iter)
            all_applied_patches.extend(patches_this_iter)

        # 3. Build Synchronized SFX & Camera Events
        final_render_events: List[Dict[str, Any]] = []

        # Add all visual drawing/action events
        for ev in current_events:
            rev = RenderEvent(
                event_id=ev.get("event_id") or ev.get("id"),
                type=ActionType(ev.get("type", "draw")),
                asset_id=ev.get("asset_id"),
                start_s=float(ev.get("start_s", 0.0)),
                end_s=float(ev.get("end_s", 0.0)),
                duration_s=float(ev.get("duration_s", 0.0)),
                action=ev.get("action", "draw"),
                anchor_text=ev.get("anchor_text", ""),
                layer_order=int(ev.get("layer_order", 0)),
                keep_visible=ev.get("keep_visible", True),
                fade_out_at=ev.get("fade_out_at"),
                confidence=float(ev.get("confidence", 1.0)),
                params=ev.get("params", {})
            )
            final_render_events.append(rev.to_renderer_dict())

        # Auto-align SFX with drawing start
        sfx_counter = 1
        for ev in current_events:
            if ev.get("type", "draw") == "draw":
                eid = ev.get("event_id") or ev.get("id")
                aid = ev.get("asset_id")
                st = float(ev.get("start_s", 0.0))
                sfx_item = SFXEvent(
                    event_id=f"SFX_{sfx_counter:03d}",
                    sfx_type="marker_draw",
                    start_s=st,
                    end_s=round(st + 1.2, 3),
                    duration_s=1.2,
                    anchor_asset_id=aid,
                    anchor_event_id=eid,
                    volume=0.65
                )
                final_render_events.append(sfx_item.to_render_event().to_renderer_dict())
                sfx_counter += 1

        # Camera events
        cam_counter = 1
        for ev in current_events:
            aid = ev.get("asset_id")
            if aid:
                st = float(ev.get("start_s", 0.0))
                en = float(ev.get("end_s", 0.0))
                cam = CameraEvent(
                    event_id=f"CAM_{cam_counter:03d}",
                    camera_type="focus",
                    start_s=st,
                    end_s=en,
                    duration_s=round(en - st, 3),
                    target_asset_id=aid,
                    zoom=1.12
                )
                final_render_events.append(cam.to_render_event().to_renderer_dict())
                cam_counter += 1

        # Sort all final renderer events by start_s
        final_render_events.sort(key=lambda x: float(x.get("start_s", 0.0)))

        # Final visual states and validation
        visual_states = state_analyzer.compute_visual_states(current_events)
        final_validation = timeline_val.validate_all(
            events=current_events,
            evaluation_results=evaluation_results,
            sfx_events=[e for e in final_render_events if e["type"] == "sfx"],
            camera_events=[e for e in final_render_events if e["type"] == "camera"],
            visual_states=visual_states
        )
        final_validation.missing_assets = missing_assets
        final_validation.review_items = review_items

        # Build Final Render Plan
        plan = FinalRenderPlan(
            contract_version="1.0.0",
            section_id=section_input.section_id,
            audio_file=section_input.audio_path,
            audio_duration=round(duration, 3),
            fps=30,
            resolution={"width": 1920, "height": 1080},
            validation=final_validation,
            applied_patches=all_applied_patches,
            render_events=final_render_events,
            visual_states=visual_states,
            review_required=final_validation.review_required or len(review_items) > 0
        )

        review_report = {
            "section_id": section_input.section_id,
            "status": final_validation.status.value,
            "overall_score": final_validation.overall_score,
            "patches_count": len(all_applied_patches),
            "applied_patches": [p.model_dump() for p in all_applied_patches],
            "missing_assets": missing_assets,
            "review_required": plan.review_required,
            "review_items": review_items,
            "unresolved_issues": final_validation.unresolved_issues
        }

        return plan, review_report
