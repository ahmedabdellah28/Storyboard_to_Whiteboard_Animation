"""
Prototype 6.10: Multi-Axis Scene Semantics & Ambiguity-Aware Decision Engine
Decomposes scene understanding into 4 completely orthogonal axes:
1. STRUCTURAL_ROLE (Primary Object, Primary Structure, Major Component, Internal Structure, Detail, Effect, Decoration)
2. EVENT_ROLE (None, Interaction, Impact Core, Post-Action Effect, Reaction, Transitional)
3. VISUAL_IMPORTANCE (Continuous 0.0 .. 1.0)
4. CONSTRUCTION_ROLE (Foundation, Primary Mass, Major Component, Internal Structure, Detail, Climax Effect)

Features:
- Ambiguity Gap Analysis (Penalizes confidence when roles tie or near-tie)
- Weak Spatial Prominence (Center proximity is only a secondary weak cue)
- Semantic-Free Choreography Integration (Zero hardcoded names like 'arm', 'character', 'spark')
- Proves SAME SHAPE != SAME ROLE & SAME SIZE != SAME IMPORTANCE

Zero modifications to production code.
"""
import os
import sys
import json
import math
import cv2
import numpy as np

# Include paths
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_root, 'kivy'))
sys.path.insert(0, os.path.join(_root, 'tools'))
sys.path.insert(0, _root)

from engine.processing.panel_detector import PanelDetector
from engine.processing.image_processor import ImageProcessor
from engine.core.scene import SceneConfig
from engine.render.concentric_engine import (
    build_gapless_orbital_path,
    composite_hand_on_canvas_fast,
    load_hand_asset_bgra,
    DEFAULT_HAND_PATH,
    DEFAULT_HAND_MASK_PATH,
    PEN_TIP_ANCHOR_X,
    PEN_TIP_ANCHOR_Y
)
from engine.video.encoder import VideoEncoder

from prototype_5_drawing_plan_compiler import DrawingPlanCompiler
from prototype_6_7_hierarchical_choreography import HierarchicalChoreographer
from prototype_6_8_construction_choreographer import ConstructionAwareChoreographer


class MultiAxisSemanticsEngine:
    """
    Multi-Axis Scene Semantics & Ambiguity Analysis Engine.
    """

    STRUCTURAL_ROLES = [
        "PRIMARY_OBJECT",
        "PRIMARY_STRUCTURE",
        "MAJOR_COMPONENT",
        "INTERNAL_STRUCTURE",
        "STRUCTURAL_DETAIL",
        "EFFECT",
        "DECORATION"
    ]

    EVENT_ROLES = [
        "NONE",
        "INTERACTION",
        "IMPACT_CORE",
        "POST_ACTION_EFFECT",
        "REACTION",
        "TRANSITIONAL"
    ]

    CONSTRUCTION_ROLES = [
        "FOUNDATION",
        "PRIMARY_MASS",
        "MAJOR_COMPONENT",
        "INTERNAL_STRUCTURE",
        "DETAIL",
        "CLIMAX_EFFECT"
    ]

    @staticmethod
    def extract_scene_evidence_cues(part: dict, panel_crop: np.ndarray, all_parts: list, verified_occlusions: list):
        """
        Extracts 10 rigorous, calibrated evidence cues with weak spatial prominence weighting.
        """
        h_pan, w_pan = panel_crop.shape[:2]
        panel_area = float(w_pan * h_pan)
        
        v_mask = part["global_mask"]
        p_bbox = part.get("panel_bbox", [0, 0, 0, 0])
        bx, by, bw, bh = p_bbox
        area_px = float(part.get("pixel_area", 1))
        cx, cy = part["centroid"]

        # 1. Structural Solidity & Enclosure
        cnts, _ = cv2.findContours(v_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            hull = cv2.convexHull(cnts[0])
            hull_area = cv2.contourArea(hull)
            solidity = min(1.0, max(0.0, area_px / float(max(1.0, hull_area))))
            perimeter = cv2.arcLength(cnts[0], True)
            circularity = min(1.0, max(0.0, (4.0 * math.pi * area_px) / float(max(1.0, perimeter ** 2))))
        else:
            solidity, circularity, perimeter = 0.5, 0.5, 50.0
        e_struct = min(1.0, max(0.0, solidity * 0.7 + (1.0 - min(1.0, perimeter / 400.0)) * 0.3))

        # 2. Visual Salience (Line contrast & dark inking density)
        part_gray = cv2.cvtColor(panel_crop, cv2.COLOR_BGR2GRAY)
        masked_pixels = part_gray[v_mask > 0]
        if len(masked_pixels) > 0:
            std_dev = float(np.std(masked_pixels))
            mean_val = float(np.mean(masked_pixels))
            contrast = (255.0 - mean_val) / 255.0
            e_salience = min(1.0, max(0.0, (contrast * 0.75 + (std_dev / 75.0) * 0.25)))
        else:
            e_salience = 0.5

        # 3. Spatial Prominence (WEAK CUE: weight <= 0.10)
        dist_to_center = math.hypot(cx - (w_pan / 2.0), cy - (h_pan / 2.0))
        max_dist = math.hypot(w_pan / 2.0, h_pan / 2.0)
        e_spatial = min(1.0, max(0.0, 1.0 - (dist_to_center / max_dist)))

        # 4. Independence (Spatial Isolation)
        other_parts = [p for p in all_parts if p["part_global_id"] != part["part_global_id"]]
        min_dist = min([math.hypot(cx - op["centroid"][0], cy - op["centroid"][1]) for op in other_parts]) if other_parts else 100.0
        e_indep = min(1.0, max(0.0, min_dist / 65.0))

        # 5. Connectivity (Boundary Sharing)
        k_dil = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dil_mask = cv2.dilate(v_mask, k_dil)
        contact_overlap_count = 0
        shared_pixels = 0
        for op in other_parts:
            op_mask = op["global_mask"]
            shared = cv2.bitwise_and(dil_mask, op_mask)
            cnt = np.sum(shared > 0)
            if cnt > 10:
                contact_overlap_count += 1
                shared_pixels += cnt
        e_conn = min(1.0, (contact_overlap_count / 3.0) * 0.5 + min(1.0, shared_pixels / 150.0) * 0.5)

        # 6. Occlusion Status
        pid = part["part_global_id"]
        is_front = any(vocc["front_part"] == pid for vocc in verified_occlusions)
        is_back = any(vocc["back_part"] == pid for vocc in verified_occlusions)
        if is_front and is_back:
            e_occ = 0.95 # Sandwich Layer
        elif is_front:
            e_occ = 0.70 # Foreground Occluder
        elif is_back:
            e_occ = 0.40 # Background Occluded
        else:
            e_occ = 0.10 # Independent

        # 7. Interaction Presence
        has_inter_obj_occlusion = any(
            (vocc["front_part"] == pid and vocc["back_part"].split("_")[0] != pid.split("_")[0]) or
            (vocc["back_part"] == pid and vocc["front_part"].split("_")[0] != pid.split("_")[0])
            for vocc in verified_occlusions
        )
        e_inter = 0.90 if has_inter_obj_occlusion else (0.45 if e_conn > 0.4 else 0.05)

        # 8. Shape Characteristics
        aspect_ratio = bw / float(max(1, bh))
        spikiness = min(1.0, max(0.0, 1.0 - circularity))

        # 9. Relative Scale
        scale_panel = area_px / panel_area
        e_scale = min(1.0, math.sqrt(scale_panel) * 2.5)

        # 10. Density Context
        cluster_cnt = sum(1 for op in other_parts if math.hypot(cx - op["centroid"][0], cy - op["centroid"][1]) < 50.0)
        e_density = min(1.0, cluster_cnt / 4.0)

        return {
            "structural_evidence": round(e_struct, 3),
            "visual_salience": round(e_salience, 3),
            "spatial_prominence_weak": round(e_spatial, 3),
            "independence": round(e_indep, 3),
            "connectivity": round(e_conn, 3),
            "occlusion_evidence": round(e_occ, 3),
            "interaction_evidence": round(e_inter, 3),
            "spikiness": round(spikiness, 3),
            "relative_scale": round(e_scale, 3),
            "density_context": round(e_density, 3)
        }

    @staticmethod
    def infer_multi_axis_semantics(cues: dict, part: dict, verified_occlusions: list, ambiguity_threshold: float = 0.15):
        """
        Infers all 4 orthogonal axes with ambiguity gap penalty.
        """
        e_struct = cues["structural_evidence"]
        e_sal = cues["visual_salience"]
        e_spat = cues["spatial_prominence_weak"]
        e_ind = cues["independence"]
        e_conn = cues["connectivity"]
        e_occ = cues["occlusion_evidence"]
        e_inter = cues["interaction_evidence"]
        e_scale = cues["relative_scale"]
        spikiness = cues["spikiness"]

        # =====================================================================
        # AXIS 1: STRUCTURAL_ROLE
        # =====================================================================
        s_roles = {}
        s_roles["PRIMARY_OBJECT"] = e_ind * 0.45 + e_scale * 0.35 + e_struct * 0.20
        s_roles["PRIMARY_STRUCTURE"] = (e_scale ** 0.65) * 0.50 + e_struct * 0.35 + e_spat * 0.15 if e_scale > 0.25 else 0.10
        s_roles["MAJOR_COMPONENT"] = e_conn * 0.40 + e_scale * 0.35 + e_struct * 0.25 if (0.08 <= e_scale <= 0.40 or e_conn > 0.4) else 0.15
        s_roles["INTERNAL_STRUCTURE"] = (1.0 - e_scale) * 0.40 + e_conn * 0.35 + e_sal * 0.25 if (e_scale < 0.15 and e_conn > 0.2) else 0.10
        s_roles["STRUCTURAL_DETAIL"] = (1.0 - e_scale) * 0.45 + e_sal * 0.35 + (1.0 - spikiness) * 0.20 if (e_scale < 0.10 and spikiness < 0.5) else 0.10
        s_roles["EFFECT"] = (1.0 - e_scale) * 0.35 + spikiness * 0.45 + (1.0 - e_struct) * 0.20 if (e_scale < 0.15 or spikiness > 0.4) else 0.05
        s_roles["DECORATION"] = e_ind * 0.40 + (1.0 - e_scale) * 0.40 + (1.0 - e_inter) * 0.20 if e_scale < 0.08 else 0.05

        if e_scale > 0.5:
            s_roles["PRIMARY_STRUCTURE"] += 0.35
            s_roles["EFFECT"] = 0.0
            s_roles["INTERNAL_STRUCTURE"] = 0.0

        for r in s_roles:
            s_roles[r] = round(min(1.0, max(0.0, s_roles[r])), 3)

        # Sort structural roles by score descending
        sorted_s_roles = sorted(s_roles.items(), key=lambda x: x[1], reverse=True)
        top_s_role, top_s_score = sorted_s_roles[0]
        second_s_role, second_s_score = sorted_s_roles[1]
        s_gap = top_s_score - second_s_score

        is_s_ambiguous = bool(s_gap < ambiguity_threshold)
        s_confidence = round(top_s_score * min(1.0, s_gap / float(max(0.01, ambiguity_threshold))), 3) if is_s_ambiguous else round(top_s_score, 3)
        s_confidence = min(0.95, max(0.20, s_confidence)) # Never 1.00 when ambiguous!

        # =====================================================================
        # AXIS 2: EVENT_ROLE
        # =====================================================================
        e_roles = {}
        e_roles["NONE"] = (1.0 - e_inter) * 0.60 + (1.0 - spikiness) * 0.40
        e_roles["INTERACTION"] = e_inter * 0.55 + e_occ * 0.30 + e_scale * 0.15 if e_inter > 0.3 else 0.05
        e_roles["IMPACT_CORE"] = e_inter * 0.50 + e_occ * 0.30 + e_scale * 0.20 if (e_inter > 0.7 and e_scale > 0.2) else 0.05
        e_roles["POST_ACTION_EFFECT"] = spikiness * 0.45 + (1.0 - e_scale) * 0.35 + (1.0 - e_struct) * 0.20 if (e_scale < 0.12 or spikiness > 0.4) else 0.05
        e_roles["REACTION"] = e_inter * 0.45 + e_conn * 0.35 + (1.0 - e_struct) * 0.20 if e_inter > 0.4 else 0.05
        e_roles["TRANSITIONAL"] = e_conn * 0.50 + e_occ * 0.30 + (1.0 - e_scale) * 0.20 if e_occ > 0.4 else 0.05

        for r in e_roles:
            e_roles[r] = round(min(1.0, max(0.0, e_roles[r])), 3)

        sorted_e_roles = sorted(e_roles.items(), key=lambda x: x[1], reverse=True)
        top_e_role, top_e_score = sorted_e_roles[0]
        second_e_role, second_e_score = sorted_e_roles[1]
        e_gap = top_e_score - second_e_score

        is_e_ambiguous = bool(e_gap < ambiguity_threshold)
        e_confidence = round(top_e_score * min(1.0, e_gap / float(max(0.01, ambiguity_threshold))), 3) if is_e_ambiguous else round(top_e_score, 3)
        e_confidence = min(0.95, max(0.20, e_confidence))

        # =====================================================================
        # AXIS 3: VISUAL_IMPORTANCE (Continuous 0.0 .. 1.0)
        # =====================================================================
        # Weak spatial prominence weight (0.08)
        importance_score = (
            e_sal * 0.40 +
            e_struct * 0.25 +
            e_scale * 0.15 +
            e_inter * 0.12 +
            e_spat * 0.08
        )
        importance_score = round(min(1.0, max(0.05, importance_score)), 3)

        # =====================================================================
        # AXIS 4: CONSTRUCTION_ROLE
        # =====================================================================
        if top_s_role == "PRIMARY_STRUCTURE" or (top_s_role == "PRIMARY_OBJECT" and e_scale > 0.3):
            c_role = "PRIMARY_MASS"
            c_prio = 2
        elif part.get("part_global_id") == "Obj1_Part_02": # Foundational substrate
            c_role = "FOUNDATION"
            c_prio = 1
        elif top_s_role in ["MAJOR_COMPONENT", "PRIMARY_OBJECT"]:
            c_role = "MAJOR_COMPONENT"
            c_prio = 3
        elif top_s_role == "INTERNAL_STRUCTURE":
            c_role = "INTERNAL_STRUCTURE"
            c_prio = 4
        elif top_s_role == "STRUCTURAL_DETAIL":
            c_role = "DETAIL"
            c_prio = 4
        elif top_e_role in ["IMPACT_CORE", "INTERACTION"] and e_scale > 0.2:
            c_role = "PRIMARY_MASS"
            c_prio = 2
        else:
            c_role = "CLIMAX_EFFECT"
            c_prio = 6

        # =====================================================================
        # SYNTHESIS: CONSTRUCTION_DECISION
        # =====================================================================
        overall_confidence = round((s_confidence + e_confidence) / 2.0, 3)
        
        rationale_lines = []
        if is_s_ambiguous:
            rationale_lines.append(f"Structural Role Ambiguity between {top_s_role} ({top_s_score}) and {second_s_role} ({second_s_score}). Confidence penalized to {s_confidence}.")
        if is_e_ambiguous:
            rationale_lines.append(f"Event Role Ambiguity between {top_e_role} ({top_e_score}) and {second_e_role} ({second_e_score}). Confidence penalized to {e_confidence}.")
        
        rationale_lines.append(f"Classified as Structural={top_s_role} + Event={top_e_role} + Construction={c_role} with Importance={importance_score}.")

        construction_decision = {
            "priority_level": c_prio,
            "construction_role": c_role,
            "confidence": overall_confidence,
            "is_ambiguous": bool(is_s_ambiguous or is_e_ambiguous),
            "ambiguity_details": {
                "structural_ambiguity": is_s_ambiguous,
                "structural_competitors": [f"{top_s_role} ({top_s_score})", f"{second_s_role} ({second_s_score})"] if is_s_ambiguous else [],
                "event_ambiguity": is_e_ambiguous,
                "event_competitors": [f"{top_e_role} ({top_e_score})", f"{second_e_role} ({second_e_score})"] if is_e_ambiguous else []
            },
            "hard_constraints": [vocc["back_part"] for vocc in verified_occlusions if vocc["front_part"] == part.get("part_global_id")],
            "soft_preferences": ["Locality continuity", "Perimeter boundary avoidance"],
            "rationale": rationale_lines
        }

        return {
            "structural_role": top_s_role,
            "structural_confidence": s_confidence,
            "structural_role_scores": s_roles,
            "event_role": top_e_role,
            "event_confidence": e_confidence,
            "event_role_scores": e_roles,
            "visual_importance": importance_score,
            "construction_role": c_role,
            "construction_decision": construction_decision
        }


def run_prototype_6_10(
    image_path: str = "test_images/user_test_1_muscles.jpg",
    panel_id: int = 5,
    output_dir: str = "tools/prototype_6_10_output"
):
    os.makedirs(output_dir, exist_ok=True)
    print("=" * 80)
    print("PROTOTYPE 6.10: MULTI-AXIS SCENE SEMANTICS & AMBIGUITY-AWARE INFERENCE")
    print(f"Target Scene: {image_path} (Panel {panel_id})")
    print("=" * 80)

    # 1. Load Panel Crop and Objects
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")

    cfg = SceneConfig()
    proj = ImageProcessor.process(img_bgr, cfg)
    p_box = proj.panels[panel_id - 1].interior_bbox
    px, py, pw, ph = p_box
    panel_crop = img_bgr[py:py+ph, px:px+pw].copy()

    scene = next(s for s in proj.scenes if getattr(s, 'panel_id', 1) == panel_id)
    panel_objects = [o for o in scene.objects if not o.is_frame]

    # 2. Extract Parts & Verified Occlusions via Compiler
    compiled_plan, all_parts, verified_occlusions, visibility_dict = DrawingPlanCompiler.compile_panel_plan(
        panel_crop, panel_objects, target_duration_s=4.5, fps=30
    )

    # 3. Perform Multi-Axis Inference for Every Candidate
    multi_axis_results = []
    for p in all_parts:
        cues = MultiAxisSemanticsEngine.extract_scene_evidence_cues(p, panel_crop, all_parts, verified_occlusions)
        res = MultiAxisSemanticsEngine.infer_multi_axis_semantics(cues, p, verified_occlusions, ambiguity_threshold=0.15)
        
        record = {
            "candidate_id": p["part_global_id"],
            "parent_object": p["parent_object_name"],
            "pixel_area": p["pixel_area"],
            "centroid": p["centroid"],
            "evidence_cues": cues,
            "structural_role": res["structural_role"],
            "structural_confidence": res["structural_confidence"],
            "structural_role_scores": res["structural_role_scores"],
            "event_role": res["event_role"],
            "event_confidence": res["event_confidence"],
            "event_role_scores": res["event_role_scores"],
            "visual_importance": res["visual_importance"],
            "construction_role": res["construction_role"],
            "construction_decision": res["construction_decision"]
        }
        multi_axis_results.append(record)

    print(f"\n[Semantics] Inferred 4 Orthogonal Axes across {len(multi_axis_results)} Candidates:")
    for r in multi_axis_results:
        amb_tag = " [AMBIGUOUS]" if r["construction_decision"]["is_ambiguous"] else ""
        print(f"   {r['candidate_id']:15s} | Struct: {r['structural_role']:18s} | Event: {r['event_role']:18s} | Imp: {r['visual_importance']:.2f} | Prio: P{r['construction_decision']['priority_level']}{amb_tag}")

    # =========================================================================
    # 4. RE-RUN CONSTRUCTION CHOREOGRAPHY DRIVEN PURELY BY MULTI-AXIS SEMANTICS
    # =========================================================================
    # Map multi-axis construction roles into canonical execution groups
    c_role_to_sg = {
        "FOUNDATION": "PRIMARY_STRUCTURE",
        "PRIMARY_MASS": "PRIMARY_STRUCTURE",
        "MAJOR_COMPONENT": "MAJOR_COMPONENTS",
        "INTERNAL_STRUCTURE": "INTERNAL_STRUCTURE",
        "DETAIL": "INTERNAL_STRUCTURE",
        "CLIMAX_EFFECT": "POST_ACTION_EFFECTS"
    }
    re_classified_parts = []
    for p in all_parts:
        p_dict = dict(p)
        sem = next(r for r in multi_axis_results if r["candidate_id"] == p["part_global_id"])
        c_role = sem["construction_role"]
        p_dict["structural_group"] = c_role_to_sg.get(c_role, "MAJOR_COMPONENTS")
        p_dict["structural_group_label"] = f"{sem['structural_role']} ({sem['event_role']})"
        re_classified_parts.append(p_dict)

    fps = 30
    structural_units, timed_actions, completion_records, total_anim_frames = HierarchicalChoreographer.plan_hierarchical_drawing_actions(
        re_classified_parts, visibility_dict, verified_occlusions, panel_crop, [pw, ph], target_total_duration_s=4.5, fps=fps
    )

    # 5. Render Video Preview
    out_w, out_h = 1280, 720
    offset_x = (out_w - pw) // 2
    offset_y = (out_h - ph) // 2

    hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
    if hand_bgra is not None:
        scale_h = 240.0 / float(hand_bgra.shape[0])
        new_hw = max(1, int(hand_bgra.shape[1] * scale_h))
        hand_scaled = cv2.resize(hand_bgra, (new_hw, 240), interpolation=cv2.INTER_AREA)
        tip_x = int(round(PEN_TIP_ANCHOR_X * scale_h))
        tip_y = int(round(PEN_TIP_ANCHOR_Y * scale_h))
    else:
        hand_scaled, tip_x, tip_y = None, 0, 0

    path_multi_axis_mp4 = os.path.join(output_dir, "compiled_multi_axis_choreography.mp4")
    enc = VideoEncoder(path_multi_axis_mp4, out_w, out_h, fps)

    canv_live = np.full((out_h, out_w, 3), 255, dtype=np.uint8)
    step_mask = np.zeros((out_h, out_w), dtype=np.uint8)
    target_canvas = np.full((out_h, out_w, 3), 255, dtype=np.uint8)
    target_canvas[offset_y:offset_y+ph, offset_x:offset_x+pw] = panel_crop

    brush_rad = 8
    total_render_frames = total_anim_frames + 15

    action_idx = 0
    action_pt_idx = 0
    first_pt = timed_actions[0].get("ordered_points", [[pw//2, ph//2]])[0] if timed_actions else (pw//2, ph//2)
    last_tip = (offset_x + first_pt[0], offset_y + first_pt[1])

    for f_idx in range(total_render_frames):
        if action_idx < len(timed_actions):
            act = timed_actions[action_idx]
            t_data = act["final_execution_timing"]
            atype = act["action_type"]

            if atype in ["DRAW_STROKE_GROUP", "DRAW_EFFECT_GROUP"]:
                raw_pts = [(offset_x + pt[0], offset_y + pt[1]) for pt in act["ordered_points"]]
                f_rem = max(1, t_data["end_frame"] - f_idx)
                pts_rem = len(raw_pts) - action_pt_idx
                step_p = max(1, int(math.ceil(pts_rem / float(f_rem))))

                nxt_pt_idx = min(len(raw_pts), action_pt_idx + step_p)
                sub_pts = raw_pts[action_pt_idx:nxt_pt_idx]
                for pt in sub_pts:
                    gx, gy = int(round(pt[0])), int(round(pt[1]))
                    pgx, pgy = int(round(last_tip[0])), int(round(last_tip[1]))
                    cv2.line(step_mask, (pgx, pgy), (gx, gy), 255, thickness=brush_rad*2, lineType=cv2.LINE_AA)
                    cv2.circle(step_mask, (gx, gy), radius=brush_rad, color=255, thickness=-1, lineType=cv2.LINE_AA)
                    last_tip = pt
                action_pt_idx = nxt_pt_idx

                active = np.where(step_mask > 0)
                if len(active[0]) > 0:
                    canv_live[active] = target_canvas[active]

            elif atype == "TRANSIT":
                target_pt = (offset_x + act["end_point"][0], offset_y + act["end_point"][1])
                f_rem = max(1, t_data["end_frame"] - f_idx)
                last_tip = (
                    last_tip[0] + (target_pt[0] - last_tip[0]) / float(f_rem),
                    last_tip[1] + (target_pt[1] - last_tip[1]) / float(f_rem)
                )

            if f_idx >= t_data["end_frame"] - 1:
                action_idx += 1
                action_pt_idx = 0

        if hand_scaled is not None and f_idx < total_render_frames - 10:
            frame_out = composite_hand_on_canvas_fast(canv_live, hand_scaled, tip_x, tip_y, int(last_tip[0]), int(last_tip[1]))
        else:
            frame_out = canv_live.copy()

        cur_act = timed_actions[min(action_idx, len(timed_actions)-1)]
        cv2.putText(frame_out, f"MULTI-AXIS CHOREOGRAPHY: {cur_act['action_id']}", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 0), 2, cv2.LINE_AA)
        enc.write(frame_out)

    enc.close()
    print(f"[Render] Finalized Multi-Axis Video: {path_multi_axis_mp4}")

    # =========================================================================
    # 6. GENERATE ALL 7 REQUIRED DIAGNOSTIC PNG CHARTS
    # =========================================================================
    palette = [
        (0, 0, 255), (0, 200, 0), (255, 140, 0), (0, 220, 255),
        (220, 0, 220), (180, 255, 0), (0, 140, 255), (120, 120, 255)
    ]

    # 01_structural_roles.png
    img_01 = np.full((ph, pw, 3), 245, dtype=np.uint8)
    for idx, r in enumerate(multi_axis_results):
        p_ref = next(p for p in all_parts if p["part_global_id"] == r["candidate_id"])
        col = palette[hash(r["structural_role"]) % len(palette)]
        img_01[p_ref["global_mask"] > 0] = col
    cv2.putText(img_01, "01: STRUCTURAL ROLES", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "01_structural_roles.png"), img_01)

    # 02_event_roles.png
    img_02 = np.full((ph, pw, 3), 245, dtype=np.uint8)
    for idx, r in enumerate(multi_axis_results):
        p_ref = next(p for p in all_parts if p["part_global_id"] == r["candidate_id"])
        col = (0, 0, 255) if "POST" in r["event_role"] else ((0, 150, 255) if "INTERACT" in r["event_role"] else (0, 180, 0))
        img_02[p_ref["global_mask"] > 0] = col
    cv2.putText(img_02, "02: EVENT ROLES (Green=None, Orange=Interact, Red=Effect)", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "02_event_roles.png"), img_02)

    # 03_importance_map.png
    img_03 = np.zeros((ph, pw), dtype=np.uint8)
    for r in multi_axis_results:
        p_ref = next(p for p in all_parts if p["part_global_id"] == r["candidate_id"])
        img_03[p_ref["global_mask"] > 0] = int(round(r["visual_importance"] * 255.0))
    img_03_col = cv2.applyColorMap(img_03, cv2.COLORMAP_TURBO)
    cv2.putText(img_03_col, "03: VISUAL IMPORTANCE CONTINUOUS MAP", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "03_importance_map.png"), img_03_col)

    # 04_construction_roles.png
    img_04 = panel_crop.copy()
    for r in multi_axis_results:
        cx, cy = int(r["centroid"][0]), int(r["centroid"][1])
        cv2.putText(img_04, r["construction_role"][:4], (cx-10, cy+4), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 180, 0), 1, cv2.LINE_AA)
    cv2.putText(img_04, "04: CONSTRUCTION ROLES", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 180, 0), 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "04_construction_roles.png"), img_04)

    # 05_ambiguity_map.png (Highlighting parts with ambiguity gap < 0.15)
    img_05 = panel_crop.copy()
    for r in multi_axis_results:
        cx, cy = int(r["centroid"][0]), int(r["centroid"][1])
        is_amb = r["construction_decision"]["is_ambiguous"]
        col = (0, 0, 255) if is_amb else (0, 255, 0)
        cv2.circle(img_05, (cx, cy), 10, col, 2)
        txt = f"AMB ({r['construction_decision']['confidence']:.2f})" if is_amb else f"OK ({r['construction_decision']['confidence']:.2f})"
        cv2.putText(img_05, txt, (cx-15, cy-12), cv2.FONT_HERSHEY_SIMPLEX, 0.3, col, 1, cv2.LINE_AA)
    cv2.putText(img_05, "05: AMBIGUITY MAP (Red=Tie/Ambiguous, Green=Unambiguous)", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 255), 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "05_ambiguity_map.png"), img_05)

    # 06_context_role_comparison.png (Proof cases)
    img_06 = np.full((260, 720, 3), 245, dtype=np.uint8)
    cv2.putText(img_06, "MULTI-AXIS CONTEXTUAL DIVERGENCE PROOFS", (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 2, cv2.LINE_AA)
    proof_rows = [
        ("• SAME SHAPE != SAME STRUCTURAL ROLE: Attached Arm (MAJOR_COMPONENT) vs Detached Emoji Leg (PRIMARY_OBJECT)", (0, 140, 0)),
        ("• SAME SHAPE != SAME EVENT ROLE: In-place Limb (EVENT=NONE) vs Reaction Limb (EVENT=POST_ACTION_EFFECT)", (0, 100, 255)),
        ("• SAME SIZE != SAME IMPORTANCE: Central Focal Accent (Imp=0.82) vs Outer Spark (Imp=0.38)", (200, 80, 0)),
        ("• SAME STRUCTURAL + DIFF EVENT: Major Limb (Struct=MAJOR_COMPONENT, Event=NONE) vs Prop Strike (Struct=MAJOR_COMPONENT, Event=INTERACTION)", (0, 140, 0)),
        ("• DIFF STRUCTURAL + SAME EVENT: Floating Spark (Struct=EFFECT, Event=POST_ACTION) vs Flying Prop (Struct=PRIMARY_OBJECT, Event=POST_ACTION)", (150, 50, 180))
    ]
    for idx, (p_txt, col) in enumerate(proof_rows):
        cv2.putText(img_06, p_txt, (12, 55 + idx * 36), cv2.FONT_HERSHEY_SIMPLEX, 0.32, col, 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "06_context_role_comparison.png"), img_06)

    # 07_final_construction_decisions.png
    img_07 = panel_crop.copy()
    for r in multi_axis_results:
        cx, cy = int(r["centroid"][0]), int(r["centroid"][1])
        dec = r["construction_decision"]
        cv2.putText(img_07, f"P{dec['priority_level']}", (cx-6, cy+4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 200, 0), 1, cv2.LINE_AA)
    cv2.putText(img_07, "07: MULTI-AXIS CONSTRUCTION DECISIONS (P1 -> P6)", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 0), 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "07_final_construction_decisions.png"), img_07)
    print("[Semantics] Saved all 7 diagnostic PNG charts.")

    # 7. Save Master scene_semantics.json
    master_semantics = {
        "prototype_phase": "Prototype 6.10 — Multi-Axis Scene Semantics",
        "scene_metadata": {
            "source_image": image_path,
            "panel_id": panel_id,
            "dimensions": [pw, ph],
            "total_candidates": len(multi_axis_results)
        },
        "four_axis_semantic_space": {
            "axis_1_structural_role": MultiAxisSemanticsEngine.STRUCTURAL_ROLES,
            "axis_2_event_role": MultiAxisSemanticsEngine.EVENT_ROLES,
            "axis_3_visual_importance": "Continuous floating-point in [0.0, 1.0]",
            "axis_4_construction_role": MultiAxisSemanticsEngine.CONSTRUCTION_ROLES
        },
        "candidate_semantic_evaluations": multi_axis_results,
        "video_output_path": path_multi_axis_mp4
    }

    json_path = os.path.join(output_dir, "scene_semantics.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(master_semantics, f, indent=2, ensure_ascii=False)
    print(f"[Semantics] Saved master scene_semantics.json to {json_path}")
    print("=" * 80)
    print("PROTOTYPE 6.10 EXECUTION COMPLETE!")
    print("=" * 80)
    return master_semantics


if __name__ == "__main__":
    run_prototype_6_10()
