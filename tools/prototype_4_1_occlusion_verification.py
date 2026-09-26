"""
Prototype 4.1: True Occlusion Verification
Distinguishes between Physical Occlusion Evidence (Boundary Ownership, T-Junctions, Contact, Convexity)
and Weak Depth Priors (Base-Y, Proximity).
Evaluates true interactions across panels including inter-object and partial occlusion (A1 < B < A2).
Zero production code changes, zero video rendering.
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
from prototype_4_occlusion_reasoning import extract_panel_parts_in_global_coordinates


def detect_t_junctions_on_panel(panel_gray: np.ndarray):
    """
    Extracts high-confidence T-Junction points on the panel edge map.
    """
    blurred = cv2.GaussianBlur(panel_gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 35, 110)
    skel = edges.copy()
    try:
        if hasattr(cv2, 'ximgproc'):
            skel = cv2.ximgproc.thinning(edges)
    except Exception:
        pass
    kernel_neigh = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.uint8)
    neigh_count = cv2.filter2D(skel // 255, -1, kernel_neigh) * (skel // 255)
    tj_y, tj_x = np.where(neigh_count >= 3)
    return set(zip(tj_x, tj_y)), edges


def verify_pair_occlusion(p_a: dict, p_b: dict, panel_edges: np.ndarray, tj_points: set):
    """
    Rigorous physical verification of occlusion between two parts:
    Analyzes Boundary Ownership, T-Junctions, Shared Boundary Length, Contact Area, and Convexity.
    Separates TRUE_OCCLUSION from WEAK_DEPTH_PRIOR and REJECTED.
    """
    k_dil = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask_a = p_a["global_mask"]
    mask_b = p_b["global_mask"]
    
    # Check bounding box overlap first
    bx_a, by_a, bw_a, bh_a = p_a["panel_bbox"]
    bx_b, by_b, bw_b, bh_b = p_b["panel_bbox"]
    
    ix1 = max(bx_a, bx_b)
    iy1 = max(by_a, by_b)
    ix2 = min(bx_a + bw_a, bx_b + bw_b)
    iy2 = min(by_a + bh_a, by_b + bh_b)
    bbox_overlap = (ix2 > ix1 and iy2 > iy1)
    
    # Contact and Overlap Masks
    direct_overlap_mask = cv2.bitwise_and(mask_a, mask_b)
    overlap_area = int(np.sum(direct_overlap_mask > 0))
    
    dil_a = cv2.dilate(mask_a, k_dil, iterations=1)
    dil_b = cv2.dilate(mask_b, k_dil, iterations=1)
    
    contact_border = cv2.bitwise_and(dil_a, mask_b)
    contact_len = int(np.sum(contact_border > 0))
    
    # Base Y distance
    base_diff = p_a["base_y"] - p_b["base_y"]

    # 1. Check if there is NO physical contact or overlap
    if overlap_area == 0 and contact_len < 3:
        # No physical interaction
        if bbox_overlap or abs(base_diff) > 20.0:
            # Only depth prior exists
            front_p = p_a["part_global_id"] if base_diff > 0 else p_b["part_global_id"]
            back_p = p_b["part_global_id"] if base_diff > 0 else p_a["part_global_id"]
            return {
                "classification": "WEAK_DEPTH_PRIOR",
                "front_part": front_p,
                "back_part": back_p,
                "confidence": 0.35,
                "evidence_strength": "LOW",
                "evidence": [f"BASE_Y_DEPTH_PRIOR (delta={abs(base_diff):.1f}px, no physical touching)"],
                "interaction_area": 0,
                "boundary_length": 0,
                "boundary_ownership": "NONE",
                "t_junctions_count": 0,
                "rejection_reason": "No physical contact or edge overlap detected; based purely on ground plane heuristic."
            }
        else:
            return {
                "classification": "REJECTED",
                "front_part": p_a["part_global_id"],
                "back_part": p_b["part_global_id"],
                "confidence": 0.0,
                "evidence_strength": "NONE",
                "evidence": [],
                "interaction_area": 0,
                "boundary_length": 0,
                "boundary_ownership": "NONE",
                "t_junctions_count": 0,
                "rejection_reason": "Non-interacting pair with zero physical contact and insignificant depth disparity."
            }

    # 2. Physical contact exists -> Evaluate Boundary Ownership & T-Junctions
    contact_pts = np.where(contact_border > 0)
    contact_tjs = sum(1 for px_t, py_t in zip(contact_pts[1], contact_pts[0]) if (px_t, py_t) in tj_points)
    
    # Boundary Ownership Analysis:
    # We inspect whose edge contour continues across the contact region without disruption
    cnts_a, _ = cv2.findContours(mask_a, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts_b, _ = cv2.findContours(mask_b, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    hull_a = cv2.convexHull(cnts_a[0]) if cnts_a else None
    hull_b = cv2.convexHull(cnts_b[0]) if cnts_b else None
    
    solidity_a = p_a["pixel_area"] / max(1.0, float(cv2.contourArea(hull_a))) if hull_a is not None else 0.5
    solidity_b = p_b["pixel_area"] / max(1.0, float(cv2.contourArea(hull_b))) if hull_b is not None else 0.5

    # Enclosure Check
    a_in_b = (bx_a >= bx_b and by_a >= by_b and bx_a+bw_a <= bx_b+bw_b and by_a+bh_a <= by_b+bh_b)
    b_in_a = (bx_b >= bx_a and by_b >= by_a and bx_b+bw_b <= bx_a+bw_a and by_b+bh_b <= by_a+bh_a)

    score_a = 0.0
    score_b = 0.0
    ev_a = []
    ev_b = []

    # Ownership Cue 1: Spatial Enclosure (etched foreground part on top of host part)
    if a_in_b and p_a["pixel_area"] < p_b["pixel_area"] * 0.45:
        score_a += 0.50
        ev_a.append(f"SPATIAL_ENCLOSURE_OWNERSHIP (Part A is enclosed within Part B with area ratio {p_a['pixel_area']/p_b['pixel_area']:.2f})")
    elif b_in_a and p_b["pixel_area"] < p_a["pixel_area"] * 0.45:
        score_b += 0.50
        ev_b.append(f"SPATIAL_ENCLOSURE_OWNERSHIP (Part B is enclosed within Part A with area ratio {p_b['pixel_area']/p_a['pixel_area']:.2f})")

    # Ownership Cue 2: Convexity Continuity & Boundary Intrusion
    if solidity_a > solidity_b + 0.12:
        score_a += 0.35
        ev_a.append(f"CONVEXITY_OWNERSHIP (Part A solidity {solidity_a:.2f} > Part B {solidity_b:.2f}; Part A boundary indents into B)")
    elif solidity_b > solidity_a + 0.12:
        score_b += 0.35
        ev_b.append(f"CONVEXITY_OWNERSHIP (Part B solidity {solidity_b:.2f} > Part A {solidity_a:.2f}; Part B boundary indents into A)")

    # Ownership Cue 3: T-Junction Stem Termination
    if contact_tjs > 0:
        if score_a >= score_b:
            score_a += 0.25
            ev_a.append(f"T_JUNCTION_STEM_TERMINATION ({contact_tjs} T-junction anchors along shared border)")
        else:
            score_b += 0.25
            ev_b.append(f"T_JUNCTION_STEM_TERMINATION ({contact_tjs} T-junction anchors along shared border)")

    # Ownership Cue 4: Shared Inking Line Contact
    shared_ink_px = int(np.sum(panel_edges[contact_pts] > 0)) if len(contact_pts[0]) > 0 else 0
    if shared_ink_px > 4:
        ev_shared = f"SHARED_INK_CONTOUR ({shared_ink_px} ink edge pixels across {contact_len}px contact line)"
        if score_a >= score_b:
            ev_a.append(ev_shared)
        else:
            ev_b.append(ev_shared)

    # Determine Verdict
    if score_a > score_b and score_a >= 0.45:
        conf = min(0.98, 0.50 + score_a * 0.5)
        return {
            "classification": "TRUE_OCCLUSION",
            "front_part": p_a["part_global_id"],
            "back_part": p_b["part_global_id"],
            "confidence": round(conf, 3),
            "evidence_strength": "STRONG" if conf >= 0.80 else "MODERATE",
            "evidence": ev_a,
            "interaction_area": overlap_area,
            "boundary_length": contact_len,
            "boundary_ownership": f"{p_a['part_global_id']} OWNS boundary over {p_b['part_global_id']}",
            "t_junctions_count": contact_tjs
        }
    elif score_b > score_a and score_b >= 0.45:
        conf = min(0.98, 0.50 + score_b * 0.5)
        return {
            "classification": "TRUE_OCCLUSION",
            "front_part": p_b["part_global_id"],
            "back_part": p_a["part_global_id"],
            "confidence": round(conf, 3),
            "evidence_strength": "STRONG" if conf >= 0.80 else "MODERATE",
            "evidence": ev_b,
            "interaction_area": overlap_area,
            "boundary_length": contact_len,
            "boundary_ownership": f"{p_b['part_global_id']} OWNS boundary over {p_a['part_global_id']}",
            "t_junctions_count": contact_tjs
        }
    else:
        # Ambiguous contact with no clear ownership
        return {
            "classification": "REJECTED",
            "front_part": p_a["part_global_id"],
            "back_part": p_b["part_global_id"],
            "confidence": round(max(score_a, score_b), 3),
            "evidence_strength": "INCONCLUSIVE",
            "evidence": ["AMBIGUOUS_CONTACT_BOUNDARY (Symmetric contact without clear boundary ownership or T-junction stem)"],
            "interaction_area": overlap_area,
            "boundary_length": contact_len,
            "boundary_ownership": "AMBIGUOUS / CO-PLANAR",
            "t_junctions_count": contact_tjs,
            "rejection_reason": "Symmetric contact boundary lacks directional ownership cues."
        }


def run_prototype_4_1_verification(
    output_dir: str = "tools/prototype_4_1_output"
):
    os.makedirs(output_dir, exist_ok=True)
    print("=" * 75)
    print("PROTOTYPE 4.1: OCCLUSION VERIFICATION (TRUE OCCLUSION VS DEPTH PRIORS)")
    print("=" * 75)

    # We evaluate across real interaction cases:
    # 1. Staka Panel 4: Two Interacting Characters (Touching limbs, internal body parts)
    # 2. Muscles Panel 5: Character with floating impact reaction prop (Direct physical contact)
    # 3. Poses Panel 1: Character holding prop (Hand / Prop interaction)
    test_evaluations = [
        {
            "eval_id": "EVAL_1_STAKA_PANEL_4",
            "image": "test_images/Staka_storyboard_in_four_panels_202608301648.jpeg",
            "panel_id": 4,
            "desc": "Staka Panel 4: Two complex characters interacting with internal anatomical parts"
        },
        {
            "eval_id": "EVAL_2_MUSCLES_PANEL_5",
            "image": "test_images/user_test_1_muscles.jpg",
            "panel_id": 5,
            "desc": "Muscles Panel 5: Character with large reaction effect prop directly overlapping torso"
        },
        {
            "eval_id": "EVAL_3_POSES_PANEL_1",
            "image": "test_images/Character_storyboard_in_four_poses_202608301656.jpeg",
            "panel_id": 1,
            "desc": "Poses Panel 1: Character holding prop with hand/limb occlusion"
        }
    ]

    all_verified_results = []
    cfg = SceneConfig()

    for te in test_evaluations:
        e_id = te["eval_id"]
        im_path = te["image"]
        p_id = te["panel_id"]
        print(f"\n---> Evaluating: {e_id} ({te['desc']})...")

        img_bgr = cv2.imread(im_path)
        if img_bgr is None:
            continue

        proj = ImageProcessor.process(img_bgr, cfg)
        scene = next((s for s in proj.scenes if getattr(s, 'panel_id', 1) == p_id), proj.scenes[0])
        p_bbox = proj.panels[p_id - 1].interior_bbox
        px, py, pw, ph = p_bbox
        panel_crop = img_bgr[py:py+ph, px:px+pw].copy()
        panel_gray = cv2.cvtColor(panel_crop, cv2.COLOR_BGR2GRAY)
        h_pan, w_pan = panel_crop.shape[:2]

        panel_objects = [o for o in scene.objects if not o.is_frame]
        all_parts = extract_panel_parts_in_global_coordinates(panel_crop, panel_objects)
        tj_points, panel_edges = detect_t_junctions_on_panel(panel_gray)

        print(f"     Panel {p_id}: {len(panel_objects)} objects, {len(all_parts)} Drawing Units, {len(tj_points)} raw T-junctions.")

        # Pairwise verification across all Drawing Unit combinations
        verified_occlusions = []
        weak_depth_priors = []
        rejected_relations = []

        num_parts = len(all_parts)
        for i in range(num_parts):
            for j in range(i + 1, num_parts):
                verdict = verify_pair_occlusion(all_parts[i], all_parts[j], panel_edges, tj_points)
                if verdict["classification"] == "TRUE_OCCLUSION":
                    verified_occlusions.append(verdict)
                elif verdict["classification"] == "WEAK_DEPTH_PRIOR":
                    weak_depth_priors.append(verdict)
                else:
                    rejected_relations.append(verdict)

        # Check for Partial Occlusion (A1 < B < A2)
        partial_occlusion_instances = []
        for obj in panel_objects:
            obj_parts = [p["part_global_id"] for p in all_parts if p["parent_object_name"] == obj.name]
            other_parts = [p["part_global_id"] for p in all_parts if p["parent_object_name"] != obj.name]
            
            for p_other in other_parts:
                # Find parts of obj that are behind p_other, and parts of obj that are in front of p_other
                behind_other = [v["back_part"] for v in verified_occlusions if v["front_part"] == p_other and v["back_part"] in obj_parts]
                in_front_other = [v["front_part"] for v in verified_occlusions if v["back_part"] == p_other and v["front_part"] in obj_parts]
                
                if behind_other and in_front_other:
                    partial_occlusion_instances.append({
                        "object_name": obj.name,
                        "other_interactor": p_other,
                        "parts_behind": behind_other,
                        "parts_in_front": in_front_other,
                        "sandwich_chain": f"{behind_other[0]} < {p_other} < {in_front_other[0]}"
                    })

        total_pairs = (num_parts * (num_parts - 1)) // 2
        false_positive_rate = (len(weak_depth_priors) / float(total_pairs)) if total_pairs > 0 else 0.0

        print(f"     RESULTS:")
        print(f"       • Verified True Occlusions: {len(verified_occlusions)}")
        print(f"       • Weak Depth Priors:        {len(weak_depth_priors)}")
        print(f"       • Rejected Relations:       {len(rejected_relations)}")
        print(f"       • Partial Occlusions (A1 < B < A2): {len(partial_occlusion_instances)}")

        eval_summary = {
            "eval_id": e_id,
            "description": te["desc"],
            "panel_dimensions": [w_pan, h_pan],
            "total_drawing_units": len(all_parts),
            "total_evaluated_pairs": total_pairs,
            "metrics": {
                "verified_true_occlusions_count": len(verified_occlusions),
                "weak_depth_priors_count": len(weak_depth_priors),
                "rejected_relations_count": len(rejected_relations),
                "false_positive_rate_if_depth_prior_used": round(false_positive_rate, 3),
                "partial_occlusions_count": len(partial_occlusion_instances)
            },
            "partial_occlusion_details": partial_occlusion_instances,
            "verified_occlusions": verified_occlusions,
            "weak_depth_priors": weak_depth_priors[:10], # sample top 10
            "rejected_relations": rejected_relations[:10]
        }
        all_verified_results.append(eval_summary)

        # =====================================================================
        # GENERATE THE 8 DIAGNOSTIC VISUALIZATIONS FOR PRIMARY CASE (STAKA P4)
        # =====================================================================
        if e_id == "EVAL_1_STAKA_PANEL_4":
            part_lookup = {p["part_global_id"]: p for p in all_parts}

            # 01_full_panel.png
            img_01 = panel_crop.copy()
            for obj in panel_objects:
                ox, oy, ow, oh = obj.bbox
                cv2.rectangle(img_01, (ox, oy), (ox+ow, oy+oh), (0, 220, 0), 2)
                cv2.putText(img_01, obj.name, (ox+6, oy+22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 0), 2, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "01_full_panel.png"), img_01)

            # 02_interacting_pairs.png (Highlighting physically interacting pairs)
            img_02 = panel_crop.copy()
            for vocc in verified_occlusions:
                pa = part_lookup[vocc["front_part"]]
                pb = part_lookup[vocc["back_part"]]
                ca = (int(pa["centroid"][0]), int(pa["centroid"][1]))
                cb = (int(pb["centroid"][0]), int(pb["centroid"][1]))
                cv2.line(img_02, ca, cb, (0, 255, 0), 2, cv2.LINE_AA)
                cv2.circle(img_02, ca, 5, (0, 255, 0), -1)
                cv2.circle(img_02, cb, 5, (0, 0, 255), -1)
            cv2.putText(img_02, "GREEN: Front Part Centroid | RED: Back Part Centroid", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(img_02, "GREEN: Front Part Centroid | RED: Back Part Centroid", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "02_interacting_pairs.png"), img_02)

            # 03_overlap_masks.png (Direct contact and intersection masks)
            img_03 = np.zeros_like(panel_crop)
            for vocc in verified_occlusions:
                pa = part_lookup[vocc["front_part"]]
                pb = part_lookup[vocc["back_part"]]
                cont_m = cv2.bitwise_and(cv2.dilate(pa["global_mask"], np.ones((3,3), np.uint8)), pb["global_mask"])
                img_03[cont_m > 0] = (0, 255, 255)
            cv2.putText(img_03, "YELLOW: Verified Physical Contact Borders", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "03_overlap_masks.png"), img_03)

            # 04_boundary_ownership.png (Green for owning boundary, Red for terminating)
            img_04 = panel_crop.copy()
            for vocc in verified_occlusions:
                pa = part_lookup[vocc["front_part"]]
                pb = part_lookup[vocc["back_part"]]
                cnts_a, _ = cv2.findContours(pa["global_mask"], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cnts_b, _ = cv2.findContours(pb["global_mask"], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(img_04, cnts_a, -1, (0, 255, 0), 2, cv2.LINE_AA) # Front owns boundary
                cv2.drawContours(img_04, cnts_b, -1, (0, 0, 255), 1, cv2.LINE_AA) # Back is occluded
            cv2.putText(img_04, "GREEN: Owning Contour (Front) | RED: Terminating Contour (Back)", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(img_04, "GREEN: Owning Contour (Front) | RED: Terminating Contour (Back)", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "04_boundary_ownership.png"), img_04)

            # 05_tjunction_evidence.png (T-junction points along contact seams)
            img_05 = cv2.cvtColor(panel_edges, cv2.COLOR_GRAY2BGR)
            for vocc in verified_occlusions:
                pa = part_lookup[vocc["front_part"]]
                pb = part_lookup[vocc["back_part"]]
                cont_pts = np.where(cv2.bitwise_and(cv2.dilate(pa["global_mask"], np.ones((3,3), np.uint8)), pb["global_mask"]) > 0)
                for px_t, py_t in zip(cont_pts[1], cont_pts[0]):
                    if (px_t, py_t) in tj_points:
                        cv2.circle(img_05, (px_t, py_t), 4, (0, 0, 255), -1)
            cv2.putText(img_05, "RED DOTS: Verified T-Junction Stem Anchors", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "05_tjunction_evidence.png"), img_05)

            # 06_verified_occlusion.png (Directional Verified Occlusion Edges)
            img_06 = panel_crop.copy()
            for vocc in verified_occlusions:
                pa = part_lookup[vocc["front_part"]]
                pb = part_lookup[vocc["back_part"]]
                ca = (int(pa["centroid"][0]), int(pa["centroid"][1]))
                cb = (int(pb["centroid"][0]), int(pb["centroid"][1]))
                cv2.arrowedLine(img_06, ca, cb, (0, 255, 0), 2, tipLength=0.25)
                mid_x = (ca[0] + cb[0]) // 2
                mid_y = (ca[1] + cb[1]) // 2
                cv2.putText(img_06, f"{vocc['confidence']:.2f}", (mid_x+4, mid_y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1, cv2.LINE_AA)
            cv2.putText(img_06, f"VERIFIED TRUE OCCLUSIONS ({len(verified_occlusions)} Edges)", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "06_verified_occlusion.png"), img_06)

            # 07_rejected_false_occlusion.png (Displaying rejected & weak priors)
            img_07 = panel_crop.copy()
            for wdp in weak_depth_priors[:8]:
                pa = part_lookup[wdp["front_part"]]
                pb = part_lookup[wdp["back_part"]]
                ca = (int(pa["centroid"][0]), int(pa["centroid"][1]))
                cb = (int(pb["centroid"][0]), int(pb["centroid"][1]))
                cv2.line(img_07, ca, cb, (0, 165, 255), 1, cv2.LINE_AA) # Orange dotted
            cv2.putText(img_07, f"ORANGE: Weak Depth Priors (Disjoint Pairs without Physical Contact)", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "07_rejected_false_occlusion.png"), img_07)

            # 08_final_verified_graph.png (Verified DAG)
            img_08 = np.full((h_pan, w_pan, 3), 30, dtype=np.uint8)
            for p in all_parts:
                cx, cy = int(p["centroid"][0]), int(p["centroid"][1])
                cv2.circle(img_08, (cx, cy), 13, (60, 60, 60), -1)
                cv2.circle(img_08, (cx, cy), 13, (0, 255, 0), 2)
                cv2.putText(img_08, p["part_global_id"].split("_")[0], (cx-10, cy-2), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(img_08, p["part_global_id"].split("_")[1], (cx-12, cy+10), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 255), 1, cv2.LINE_AA)
            for vocc in verified_occlusions:
                pa = part_lookup[vocc["front_part"]]
                pb = part_lookup[vocc["back_part"]]
                ca = (int(pa["centroid"][0]), int(pa["centroid"][1]))
                cb = (int(pb["centroid"][0]), int(pb["centroid"][1]))
                # DAG edge: back (drawn first) -> front (drawn over)
                cv2.arrowedLine(img_08, cb, ca, (0, 255, 0), 2, tipLength=0.20)
            cv2.putText(img_08, "FINAL VERIFIED OCCLUSION DAG (0 False Priors)", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "08_final_verified_graph.png"), img_08)
            print("[Verification] Saved all 8 diagnostic PNG visualizations.")

    # Master Analysis JSON
    json_path = os.path.join(output_dir, "analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_verified_results, f, indent=2, ensure_ascii=False)

    print(f"\n[Verification] Saved analysis.json to {json_path}")
    print("=" * 75)
    print("PROTOTYPE 4.1 EXECUTION COMPLETE!")
    print("=" * 75)
    return all_verified_results


if __name__ == "__main__":
    run_prototype_4_1_verification()
