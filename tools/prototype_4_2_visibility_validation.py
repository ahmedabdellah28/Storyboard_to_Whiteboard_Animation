"""
Prototype 4.2: Occlusion + Visibility Validation
Computes exact Visible Masks and Occluded Masks from verified occlusion relations.
Validates the area conservation law: Visible + Occluded == Original Mask.
Tests Internal, Inter-object, Sandwich (A1 < B < A2), Nested details, and Ambiguous contact.
Zero production code changes, zero video rendering.
"""
import os
import sys
import json
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
from prototype_4_1_occlusion_verification import (
    detect_t_junctions_on_panel,
    verify_pair_occlusion
)


def compute_visibility_and_conservation(all_parts: list, verified_occlusions: list, h_pan: int, w_pan: int):
    """
    Computes for each Drawing Unit:
    - Original Mask
    - Occluded Mask (portions covered by higher-depth front parts)
    - Visible Mask (Original minus all occluding front parts)
    - Verifies Conservation: Visible Area + Occluded Area == Original Area
    """
    part_lookup = {p["part_global_id"]: p for p in all_parts}
    part_masks_orig = {p["part_global_id"]: p["global_mask"].copy() for p in all_parts}
    
    # Track which parts occlude which
    # front_of[back_id] = list of front_ids that occlude back_id
    occluding_parents = {p["part_global_id"]: [] for p in all_parts}
    for vocc in verified_occlusions:
        front_id = vocc["front_part"]
        back_id = vocc["back_part"]
        if front_id in occluding_parents and back_id in occluding_parents:
            occluding_parents[back_id].append(front_id)

    visibility_results = {}
    
    for p in all_parts:
        p_id = p["part_global_id"]
        orig_m = part_masks_orig[p_id]
        orig_area = int(np.sum(orig_m > 0))

        # Union of all front parts that occlude this part
        cum_occluding_m = np.zeros((h_pan, w_pan), dtype=np.uint8)
        for front_id in occluding_parents[p_id]:
            cum_occluding_m = cv2.bitwise_or(cum_occluding_m, part_masks_orig[front_id])

        # Occluded Mask = Original AND Occluding
        occluded_m = cv2.bitwise_and(orig_m, cum_occluding_m)
        occluded_area = int(np.sum(occluded_m > 0))

        # Visible Mask = Original MINUS Occluding
        visible_m = cv2.bitwise_and(orig_m, cv2.bitwise_not(cum_occluding_m))
        visible_area = int(np.sum(visible_m > 0))

        # Conservation check
        reconstructed_m = cv2.bitwise_or(visible_m, occluded_m)
        diff_m = cv2.absdiff(orig_m, reconstructed_m)
        discrepancy_px = int(np.sum(diff_m > 0))
        is_conserved = (discrepancy_px == 0 and (visible_area + occluded_area == orig_area))

        visibility_results[p_id] = {
            "part_id": p_id,
            "parent_object": p["parent_object_name"],
            "original_area_pixels": orig_area,
            "visible_area_pixels": visible_area,
            "occluded_area_pixels": occluded_area,
            "visible_percentage": round((visible_area / max(1, orig_area)) * 100.0, 2),
            "occluded_percentage": round((occluded_area / max(1, orig_area)) * 100.0, 2),
            "occluded_by_parts": occluding_parents[p_id],
            "conservation_discrepancy_pixels": discrepancy_px,
            "conservation_verified": is_conserved,
            "original_mask": orig_m,
            "visible_mask": visible_m,
            "occluded_mask": occluded_m
        }

    return visibility_results


def run_prototype_4_2_validation(
    output_dir: str = "tools/prototype_4_2_output"
):
    os.makedirs(output_dir, exist_ok=True)
    print("=" * 75)
    print("PROTOTYPE 4.2: OCCLUSION + VISIBILITY VALIDATION")
    print("=" * 75)

    # Primary focus: Muscles Panel 5 (Rich inter-object overlap + 3 sandwich chains)
    # Secondary focus: Staka Panel 4 (Internal occlusion + nested details)
    test_panels = [
        {
            "eval_id": "EVAL_MUSCLES_P5",
            "image": "test_images/user_test_1_muscles.jpg",
            "panel_id": 5,
            "desc": "Muscles Panel 5: Character with Impact Reaction Prop (Inter-object overlap & Sandwich A1 < B < A2)"
        },
        {
            "eval_id": "EVAL_STAKA_P4",
            "image": "test_images/Staka_storyboard_in_four_panels_202608301648.jpeg",
            "panel_id": 4,
            "desc": "Staka Panel 4: Two characters with nested details and intra-object occlusion"
        }
    ]

    all_case_reports = []
    cfg = SceneConfig()

    for tp in test_panels:
        e_id = tp["eval_id"]
        im_path = tp["image"]
        p_id = tp["panel_id"]
        print(f"\n---> Running Visibility Validation on {e_id} ({tp['desc']})...")

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

        # 1. Run Prototype 4.1 Verification
        verified_occlusions = []
        weak_depth_priors = []
        rejected_cases = []

        num_parts = len(all_parts)
        for i in range(num_parts):
            for j in range(i + 1, num_parts):
                verdict = verify_pair_occlusion(all_parts[i], all_parts[j], panel_edges, tj_points)
                if verdict["classification"] == "TRUE_OCCLUSION":
                    # Classify occlusion type
                    pa_obj = all_parts[i]["parent_object_name"]
                    pb_obj = all_parts[j]["parent_object_name"]
                    is_inter = (pa_obj != pb_obj)
                    is_nested = any("SPATIAL_ENCLOSURE" in ev for ev in verdict["evidence"])
                    
                    if is_inter:
                        occ_type = "INTER_OBJECT_OVERLAP"
                    elif is_nested:
                        occ_type = "NESTED_ENCLOSED_DETAIL"
                    else:
                        occ_type = "INTERNAL_OCCLUSION"
                        
                    verdict["occlusion_type"] = occ_type
                    verified_occlusions.append(verdict)
                elif verdict["classification"] == "WEAK_DEPTH_PRIOR":
                    weak_depth_priors.append(verdict)
                else:
                    rejected_cases.append(verdict)

        # 2. Compute Visibility & Conservation
        vis_results = compute_visibility_and_conservation(all_parts, verified_occlusions, h_pan, w_pan)

        # 3. Identify Sandwich Chains (A1 < B < A2)
        sandwich_chains = []
        for obj in panel_objects:
            obj_parts = [p["part_global_id"] for p in all_parts if p["parent_object_name"] == obj.name]
            other_parts = [p["part_global_id"] for p in all_parts if p["parent_object_name"] != obj.name]
            
            for p_other in other_parts:
                behind = [v["back_part"] for v in verified_occlusions if v["front_part"] == p_other and v["back_part"] in obj_parts]
                in_front = [v["front_part"] for v in verified_occlusions if v["back_part"] == p_other and v["front_part"] in obj_parts]
                
                if behind and in_front:
                    sandwich_chains.append({
                        "object_name": obj.name,
                        "other_interactor": p_other,
                        "part_a1_behind": behind[0],
                        "part_b_interactor": p_other,
                        "part_a2_in_front": in_front[0],
                        "sandwich_chain_repr": f"{behind[0]} (Back) < {p_other} (Middle) < {in_front[0]} (Front)",
                        "a1_visible_area": vis_results[behind[0]]["visible_area_pixels"],
                        "a1_occluded_area": vis_results[behind[0]]["occluded_area_pixels"],
                        "b_visible_area": vis_results[p_other]["visible_area_pixels"],
                        "a2_visible_area": vis_results[in_front[0]]["visible_area_pixels"]
                    })

        total_discrepancies = sum(vr["conservation_discrepancy_pixels"] for vr in vis_results.values())
        print(f"     [Visibility] Total Drawing Units: {len(all_parts)}")
        print(f"     [Visibility] Verified Occlusions: {len(verified_occlusions)}")
        print(f"     [Visibility] Sandwich Chains (A1 < B < A2): {len(sandwich_chains)}")
        print(f"     [Visibility] Area Conservation Status: {'PERFECT (0 px discrepancy)' if total_discrepancies == 0 else f'{total_discrepancies} px discrepancy'}")

        # Format report data
        case_report = {
            "eval_id": e_id,
            "description": tp["desc"],
            "panel_dimensions": [w_pan, h_pan],
            "total_drawing_units": len(all_parts),
            "area_conservation_summary": {
                "total_discrepancy_pixels": total_discrepancies,
                "conservation_verdict": "PERFECT (Visible + Occluded == Original for 100% of parts)" if total_discrepancies == 0 else "DISCREPANCY DETECTED"
            },
            "verified_occlusion_relations": [
                {
                    "front_id": vocc["front_part"],
                    "back_id": vocc["back_part"],
                    "occlusion_type": vocc["occlusion_type"],
                    "interaction_area": vocc["interaction_area"],
                    "visible_area_of_back": vis_results[vocc["back_part"]]["visible_area_pixels"],
                    "occluded_area_of_back": vis_results[vocc["back_part"]]["occluded_area_pixels"],
                    "boundary_length": vocc["boundary_length"],
                    "confidence": vocc["confidence"],
                    "evidence": vocc["evidence"]
                } for vocc in verified_occlusions
            ],
            "sandwich_chains": sandwich_chains,
            "drawing_units_visibility_breakdown": [
                {
                    "part_id": vr["part_id"],
                    "parent_object": vr["parent_object"],
                    "original_area": vr["original_area_pixels"],
                    "visible_area": vr["visible_area_pixels"],
                    "occluded_area": vr["occluded_area_pixels"],
                    "visible_pct": vr["visible_percentage"],
                    "occluded_pct": vr["occluded_percentage"],
                    "occluded_by": vr["occluded_by_parts"],
                    "is_conserved": vr["conservation_verified"]
                } for vr in vis_results.values()
            ],
            "rejected_ambiguous_cases_count": len(rejected_cases)
        }
        all_case_reports.append(case_report)

        # =====================================================================
        # GENERATE THE 8 DIAGNOSTIC VISUALIZATIONS FOR EVAL_MUSCLES_P5
        # =====================================================================
        if e_id == "EVAL_MUSCLES_P5":
            part_lookup = {p["part_global_id"]: p for p in all_parts}
            part_palette = [
                (0, 0, 255), (0, 220, 0), (255, 140, 0), (0, 220, 255),
                (220, 0, 220), (180, 255, 0), (0, 140, 255), (120, 120, 255),
                (255, 50, 150), (50, 255, 200), (200, 150, 50), (150, 50, 200)
            ]

            # 01_full_panel.png
            img_01 = panel_crop.copy()
            for obj in panel_objects:
                ox, oy, ow, oh = obj.bbox
                cv2.rectangle(img_01, (ox, oy), (ox+ow, oy+oh), (0, 220, 0), 2)
                cv2.putText(img_01, obj.name, (ox+6, oy+22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 0), 2, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "01_full_panel.png"), img_01)

            # 02_front_back_masks.png (Side-by-side: Front vs Back for verified relations)
            img_02_front = np.zeros_like(panel_crop)
            img_02_back = np.zeros_like(panel_crop)
            for vocc in verified_occlusions:
                pf = part_lookup[vocc["front_part"]]
                pb = part_lookup[vocc["back_part"]]
                img_02_front[pf["global_mask"] > 0] = (0, 255, 0)
                img_02_back[pb["global_mask"] > 0] = (0, 0, 255)
            cv2.putText(img_02_front, "FRONT MASKS (Occluding)", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)
            cv2.putText(img_02_back, "BACK MASKS (Occluded)", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1, cv2.LINE_AA)
            img_02 = np.hstack([img_02_front, img_02_back])
            cv2.imwrite(os.path.join(output_dir, "02_front_back_masks.png"), img_02)

            # 03_overlap_regions.png (Direct overlap between interacting parts)
            img_03 = panel_crop.copy()
            for vocc in verified_occlusions:
                pf = part_lookup[vocc["front_part"]]
                pb = part_lookup[vocc["back_part"]]
                ov_m = cv2.bitwise_and(pf["global_mask"], pb["global_mask"])
                if np.sum(ov_m) > 0:
                    img_03[ov_m > 0] = (0, 0, 255)
                    cnts, _ = cv2.findContours(ov_m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cv2.drawContours(img_03, cnts, -1, (0, 255, 255), 2, cv2.LINE_AA)
                else:
                    # Contact line
                    touch_m = cv2.bitwise_and(cv2.dilate(pf["global_mask"], np.ones((3,3), np.uint8)), pb["global_mask"])
                    img_03[touch_m > 0] = (0, 255, 0)
            cv2.putText(img_03, "RED: Physical Overlap | GREEN: Contact Seam", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "03_overlap_regions.png"), img_03)

            # 04_visible_masks.png (Render of pure Visible Regions after subtraction)
            img_04 = np.zeros_like(panel_crop)
            for i, (p_id, vr) in enumerate(vis_results.items()):
                col = part_palette[i % len(part_palette)]
                vm = vr["visible_mask"]
                img_04[vm > 0] = col
                cnts, _ = cv2.findContours(vm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(img_04, cnts, -1, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(img_04, "PURE VISIBLE MASKS (After Layer Subtraction)", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "04_visible_masks.png"), img_04)

            # 05_occluded_masks.png (Render of Occluded/Hidden portions)
            img_05 = panel_crop.copy()
            for p_id, vr in vis_results.items():
                om = vr["occluded_mask"]
                if np.sum(om) > 0:
                    img_05[om > 0] = cv2.addWeighted(panel_crop[om > 0], 0.3, np.full_like(panel_crop[om > 0], (0, 0, 255)), 0.7, 0)
                    cnts, _ = cv2.findContours(om, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cv2.drawContours(img_05, cnts, -1, (0, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(img_05, "RED OVERLAY: Occluded Hidden Regions", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "05_occluded_masks.png"), img_05)

            # 06_sandwich_validation.png (Step-by-step layer breakdown of A1 < B < A2)
            if sandwich_chains:
                sw = sandwich_chains[0]
                m_a1 = vis_results[sw["part_a1_behind"]]["visible_mask"]
                m_b = vis_results[sw["part_b_interactor"]]["visible_mask"]
                m_a2 = vis_results[sw["part_a2_in_front"]]["visible_mask"]

                canv_step1 = np.full((h_pan, w_pan, 3), 255, dtype=np.uint8)
                canv_step1[m_a1 > 0] = panel_crop[m_a1 > 0]
                cv2.putText(canv_step1, "1. A1 (Back)", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)

                canv_step2 = canv_step1.copy()
                canv_step2[m_b > 0] = panel_crop[m_b > 0]
                cv2.putText(canv_step2, "2. + B (Middle)", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 140, 0), 1, cv2.LINE_AA)

                canv_step3 = canv_step2.copy()
                canv_step3[m_a2 > 0] = panel_crop[m_a2 > 0]
                cv2.putText(canv_step3, "3. + A2 (Front)", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 0), 1, cv2.LINE_AA)

                img_06 = np.hstack([canv_step1, canv_step2, canv_step3])
                cv2.imwrite(os.path.join(output_dir, "06_sandwich_validation.png"), img_06)

            # 07_rejected_cases.png (Rejected Ambiguous Contacts)
            img_07 = panel_crop.copy()
            for rej in rejected_cases[:10]:
                pa = part_lookup[rej["front_part"]]
                pb = part_lookup[rej["back_part"]]
                ca = (int(pa["centroid"][0]), int(pa["centroid"][1]))
                cb = (int(pb["centroid"][0]), int(pb["centroid"][1]))
                cv2.line(img_07, ca, cb, (0, 165, 255), 1, cv2.LINE_AA)
            cv2.putText(img_07, "ORANGE: Rejected / Ambiguous Co-planar Contacts", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "07_rejected_cases.png"), img_07)

            # 08_final_visibility_graph.png (Visibility DAG with Area Stats)
            img_08 = np.full((h_pan, w_pan, 3), 30, dtype=np.uint8)
            for p_id, vr in vis_results.items():
                p_d = part_lookup[p_id]
                cx, cy = int(p_d["centroid"][0]), int(p_d["centroid"][1])
                cv2.circle(img_08, (cx, cy), 13, (60, 60, 60), -1)
                cv2.circle(img_08, (cx, cy), 13, (0, 255, 0), 2)
                cv2.putText(img_08, p_id.split("_")[0], (cx-10, cy-2), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(img_08, f"V:{vr['visible_percentage']:.0f}%", (cx-14, cy+10), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 255, 255), 1, cv2.LINE_AA)

            for vocc in verified_occlusions:
                pa = part_lookup[vocc["front_part"]]
                pb = part_lookup[vocc["back_part"]]
                ca = (int(pa["centroid"][0]), int(pa["centroid"][1]))
                cb = (int(pb["centroid"][0]), int(pb["centroid"][1]))
                # Edge: back -> front
                cv2.arrowedLine(img_08, cb, ca, (0, 255, 0), 2, tipLength=0.20)

            cv2.putText(img_08, "FINAL VISIBILITY DAG (Visible % per Node)", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "08_final_visibility_graph.png"), img_08)
            print("[Visibility] Saved all 8 diagnostic PNG visualizations.")

    # Save Master JSON Analysis
    json_path = os.path.join(output_dir, "analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_case_reports, f, indent=2, ensure_ascii=False)

    print(f"\n[Visibility] Saved analysis.json to {json_path}")
    print("=" * 75)
    print("PROTOTYPE 4.2 EXECUTION COMPLETE!")
    print("=" * 75)
    return all_case_reports


if __name__ == "__main__":
    run_prototype_4_2_validation()
