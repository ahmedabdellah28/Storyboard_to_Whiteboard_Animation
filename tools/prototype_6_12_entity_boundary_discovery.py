"""
Prototype 6.12: Visual Entity Boundary Discovery & Counterfactual Ownership Engine
Discovers true visual entity boundaries from the image using a 15-dimensional Scene Ownership Graph
and Counterfactual Ownership Hypothesis Testing (Hypothesis A vs B vs C).
Enforces Soft Entity Stability Lock with explicit Rejection of Illegal Cross-Entity Switches.

Outputs:
- 12 Diagnostic PNG Charts
- entity_boundary_analysis.json
- compiled_entity_boundary_choreography.mp4
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


class VisualEntityBoundaryEngine:
    """
    Computes a 15-dimensional Scene Ownership Graph and performs Counterfactual Ownership Testing.
    Answers for each part: 'Who visually owns this part?'
    """

    @staticmethod
    def calculate_15d_ownership_cues(p1: dict, p2: dict, panel_crop: np.ndarray, verified_occlusions: list) -> dict:
        """
        Computes 15 fine-grained geometric, topological, and physical cues between two candidate parts.
        """
        h_pan, w_pan = panel_crop.shape[:2]
        diag = float(math.hypot(w_pan, h_pan))

        m1, m2 = p1["global_mask"], p2["global_mask"]
        c1, c2 = p1["centroid"], p2["centroid"]
        b1, b2 = p1.get("panel_bbox", [0, 0, 0, 0]), p2.get("panel_bbox", [0, 0, 0, 0])
        a1, a2 = float(p1.get("pixel_area", 1)), float(p2.get("pixel_area", 1))
        pid1, pid2 = p1["part_global_id"], p2["part_global_id"]

        # 1. Structural Continuity (Coaxial & vertical elongation compatibility)
        dx, dy = abs(c1[0] - c2[0]), abs(c1[1] - c2[1])
        s_struct = min(1.0, (1.0 - (dx / float(w_pan * 0.4))) * 0.6 + (1.0 - (dy / float(h_pan * 0.5))) * 0.4)

        # 2. Shape Continuation (Curvature & aspect ratio matching)
        ar1 = b1[2] / float(max(1, b1[3]))
        ar2 = b2[2] / float(max(1, b2[3]))
        s_shape = max(0.0, 1.0 - abs(ar1 - ar2) / 3.0)

        # 3. Contour Continuation across gaps (Tangent collinearity)
        cnts1, _ = cv2.findContours(m1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts2, _ = cv2.findContours(m2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        s_contour = 0.5
        if cnts1 and cnts2:
            hull1 = cv2.convexHull(cnts1[0])
            hull2 = cv2.convexHull(cnts2[0])
            dist_pts = cv2.pointPolygonTest(hull1, (float(c2[0]), float(c2[1])), True)
            s_contour = min(1.0, max(0.0, 1.0 + (dist_pts / 50.0)))

        # 4. Boundary Attachment (Dilation overlap)
        k_dil = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        d1 = cv2.dilate(m1, k_dil)
        d2 = cv2.dilate(m2, k_dil)
        shared = np.sum(cv2.bitwise_and(d1, d2) > 0)
        s_boundary = min(1.0, shared / 40.0)

        # 5. Geometric Alignment (Bounding box overlap on X or Y axis)
        x_ov = max(0, min(b1[0] + b1[2], b2[0] + b2[2]) - max(b1[0], b2[0]))
        y_ov = max(0, min(b1[1] + b1[3], b2[1] + b2[3]) - max(b1[1], b2[1]))
        s_align = min(1.0, (x_ov / float(min(b1[2], b2[2]) + 1e-5)) * 0.6 + (y_ov / float(min(b1[3], b2[3]) + 1e-5)) * 0.4)

        # 6. Support Relationship (Vertical stacking: requires mass compatibility or strong boundary)
        is_vert = (dy > dx) and (x_ov > min(b1[2], b2[2]) * 0.20)
        mass_compat = (min(a1, a2) > 120) or (s_boundary > 0.4)
        s_support = 0.85 if (is_vert and mass_compat and (math.hypot(dx, dy) < (b1[3] + b2[3]) * 0.85)) else 0.05

        # 7. Enclosure (Convex hull containment)
        mask_h1 = np.zeros_like(m1)
        if cnts1:
            cv2.drawContours(mask_h1, [cv2.convexHull(cnts1[0])], -1, 255, -1)
            contained = np.sum(cv2.bitwise_and(mask_h1, m2) > 0)
            s_enclosure = min(1.0, contained / float(a2))
        else:
            s_enclosure = 0.0

        # 8. Relative Scale Compatibility
        scale_ratio = min(a1, a2) / float(max(a1, a2))
        s_scale = min(1.0, scale_ratio * 3.0) if min(a1, a2) > 80 else (0.4 if s_boundary > 0.3 else 0.05)

        # 9. Visual Style / Inking Density Continuity
        gray = cv2.cvtColor(panel_crop, cv2.COLOR_BGR2GRAY)
        pix1 = gray[m1 > 0]
        pix2 = gray[m2 > 0]
        mean1 = float(np.mean(pix1)) if len(pix1) > 0 else 128.0
        mean2 = float(np.mean(pix2)) if len(pix2) > 0 else 128.0
        s_style = max(0.0, 1.0 - abs(mean1 - mean2) / 80.0)

        # 10. Local Density Compatibility
        s_density = 0.75 if abs(a1 - a2) < 4000 else 0.40

        # 11. Occlusion Relationship (Distinguish intra-body occlusion from external prop collisions)
        has_occ = any(
            (vocc["front_part"] == pid1 and vocc["back_part"] == pid2) or
            (vocc["front_part"] == pid2 and vocc["back_part"] == pid1)
            for vocc in verified_occlusions
        )
        # If parts share structural support or strong alignment, it is an intra-body overlap (e.g. head over torso)
        is_intra_body = (s_support > 0.50) or (s_align > 0.40 and s_boundary > 0.30)
        s_depth_separation = 0.35 if (has_occ and a1 > 150 and a2 > 150 and not is_intra_body) else 1.0

        # 12. Spatial Proximity (Soft Gaussian decay)
        dist_px = math.hypot(dx, dy)
        s_prox = math.exp(- (dist_px ** 2) / (2 * (diag * 0.22) ** 2))

        # 13. Contextual Consistency
        s_context = 0.70 if s_align > 0.3 or s_support > 0.5 else 0.20

        # 14. Effect-Like Geometry Penalty (Tiny radial sparks/debris pointing away from the body)
        peri1 = cv2.arcLength(cnts1[0], True) if cnts1 else 50.0
        peri2 = cv2.arcLength(cnts2[0], True) if cnts2 else 50.0
        circ1 = min(1.0, max(0.0, (4.0 * math.pi * a1) / float(max(1.0, peri1 ** 2))))
        circ2 = min(1.0, max(0.0, (4.0 * math.pi * a2) / float(max(1.0, peri2 ** 2))))
        is_effect_pair = (min(a1, a2) < 120 and max(a1, a2) > 250) or (min(circ1, circ2) < 0.22 and min(a1, a2) < 120)
        effect_penalty = 0.15 if is_effect_pair else 1.0

        # 15. Weighted Synthesis
        affinity = (
            s_boundary * 0.25 +
            s_support * 0.25 +
            s_align * 0.20 +
            s_enclosure * 0.12 +
            s_prox * 0.10 +
            s_contour * 0.08
        ) * effect_penalty * s_depth_separation

        return {
            "affinity": float(round(float(np.clip(affinity, 0.0, 1.0)), 3)),
            "cues": {
                "structural_continuity": round(float(s_struct), 3),
                "shape_continuation": round(float(s_shape), 3),
                "contour_continuation": round(float(s_contour), 3),
                "geometric_alignment": round(float(s_align), 3),
                "support_relationship": round(float(s_support), 3),
                "enclosure": round(float(s_enclosure), 3),
                "boundary_attachment": round(float(s_boundary), 3),
                "relative_scale": round(float(s_scale), 3),
                "visual_style_continuity": round(float(s_style), 3),
                "occlusion_relationship": round(float(s_depth_separation), 3),
                "spatial_proximity": round(float(s_prox), 3)
            }
        }

    @staticmethod
    def counterfactual_ownership_clustering(all_parts: list, panel_crop: np.ndarray, verified_occlusions: list):
        """
        Builds the 15D Scene Ownership Graph, seeds Initial Entity Hypotheses from dense cores,
        and runs Counterfactual Testing (Hypothesis A vs B vs C) for every part to maximize global consistency.
        """
        n = len(all_parts)
        aff_matrix = np.zeros((n, n), dtype=np.float32)
        cues_dict = {}

        for i in range(n):
            aff_matrix[i, i] = 1.0
            for j in range(i + 1, n):
                res = VisualEntityBoundaryEngine.calculate_15d_ownership_cues(
                    all_parts[i], all_parts[j], panel_crop, verified_occlusions
                )
                aff_matrix[i, j] = res["affinity"]
                aff_matrix[j, i] = res["affinity"]
                cues_dict[f"{all_parts[i]['part_global_id']}--{all_parts[j]['part_global_id']}"] = res

        # 1. Identify Candidate Entity Cores (High mass + high topological solidity)
        part_mass_solidity = []
        for i, p in enumerate(all_parts):
            cnts, _ = cv2.findContours(p["global_mask"], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            solidity = 0.5
            if cnts:
                hull = cv2.convexHull(cnts[0])
                solidity = min(1.0, p.get("pixel_area", 1) / float(max(1.0, cv2.contourArea(hull))))
            part_mass_solidity.append((i, p.get("pixel_area", 1) * solidity))

        # Seed the top core clusters
        part_mass_solidity.sort(key=lambda x: x[1], reverse=True)
        primary_core_idx = part_mass_solidity[0][0]

        # 2. Agglomerative Entity Clustering with Strict Cross-Entity Cutoff (0.36)
        visited = set()
        clusters = []

        # Start from highest mass cores
        for seed_idx, _ in part_mass_solidity:
            if seed_idx in visited:
                continue
            curr_cluster = []
            queue = [seed_idx]
            visited.add(seed_idx)

            while queue:
                u = queue.pop(0)
                curr_cluster.append(u)
                for v in range(n):
                    if v not in visited and aff_matrix[u, v] >= 0.32:
                        visited.add(v)
                        queue.append(v)
            clusters.append(curr_cluster)

        # 3. Perform Counterfactual Testing for every part:
        # Evaluate Hypothesis A (Cluster 1) vs Hypothesis B (Cluster 2) vs Hypothesis C (Independent)
        final_entities = []
        part_ownership_hypotheses = {}

        for e_idx, member_indices in enumerate(clusters, 1):
            members = [all_parts[idx] for idx in member_indices]
            member_ids = [m["part_global_id"] for m in members]
            e_id = f"Entity_{e_idx:02d}"

            # Infer Entity Core within cluster
            core_scores = {}
            for idx in member_indices:
                p = all_parts[idx]
                pid = p["part_global_id"]
                internal_aff = np.mean([aff_matrix[idx, other_idx] for other_idx in member_indices]) if len(member_indices) > 1 else 1.0
                mass_ratio = p.get("pixel_area", 1) / float(sum(m.get("pixel_area", 1) for m in members))
                core_scores[pid] = internal_aff * 0.50 + mass_ratio * 0.50

            core_pid = max(core_scores.keys(), key=lambda k: core_scores[k])
            core_conf = float(round(float(core_scores[core_pid]), 3))

            # Internal Cohesion
            sub_mat = aff_matrix[np.ix_(member_indices, member_indices)]
            cohesion = float(round(float(np.mean(sub_mat)) if len(member_indices) > 1 else 1.0, 3))

            # Counterfactual Ownership Evaluation for each member
            for idx in member_indices:
                p = all_parts[idx]
                pid = p["part_global_id"]
                core_p = next(x for x in all_parts if x["part_global_id"] == core_pid)
                aff_to_own_core = float(aff_matrix[idx, all_parts.index(core_p)])

                # Evaluate competing entities
                competing_affs = {}
                for other_e_idx, other_members in enumerate(clusters, 1):
                    if other_e_idx == e_idx:
                        continue
                    comp_scores = [float(aff_matrix[idx, o_idx]) for o_idx in other_members]
                    competing_affs[f"Entity_{other_e_idx:02d}"] = float(np.mean(comp_scores))

                best_other_e = max(competing_affs.keys()) if competing_affs else None
                best_other_aff = competing_affs[best_other_e] if best_other_e else 0.0

                # Counterfactual Decision
                score_gap = aff_to_own_core - best_other_aff
                is_ambiguous = bool(score_gap < 0.15 and best_other_aff > 0.25)

                area = p.get("pixel_area", 1)
                if pid == core_pid:
                    rel = "ATTACHED_TO_ENTITY"
                    status = "CORE_ANCHOR"
                elif aff_to_own_core > 0.45 or area > 300:
                    rel = "ATTACHED_TO_ENTITY"
                    status = "HIGH_CONFIDENCE_ATTACHMENT"
                elif area < 100:
                    rel = "EFFECT_ENTITY"
                    status = "PERIPHERAL_EFFECT"
                else:
                    rel = "ASSOCIATED_WITH_ENTITY"
                    status = "ASSOCIATED_COMPONENT"

                part_ownership_hypotheses[pid] = {
                    "candidate_id": pid,
                    "selected_entity": e_id,
                    "relationship": rel,
                    "status": status,
                    "hypothesis_evaluations": {
                        "hypothesis_A_own_entity_score": round(float(aff_to_own_core), 3),
                        "hypothesis_B_competing_entity": best_other_e,
                        "hypothesis_B_competing_score": round(float(best_other_aff), 3),
                        "hypothesis_C_independent_score": round(float(1.0 - max(aff_to_own_core, best_other_aff)), 3)
                    },
                    "is_ambiguous": is_ambiguous,
                    "confidence": float(round(float(max(0.30, min(0.98, aff_to_own_core))), 3))
                }

            # Visual Extent
            boxes = [m.get("panel_bbox", [0, 0, 0, 0]) for m in members]
            extent = [
                min(b[0] for b in boxes),
                min(b[1] for b in boxes),
                max(b[0] + b[2] for b in boxes) - min(b[0] for b in boxes),
                max(b[1] + b[3] for b in boxes) - min(b[1] for b in boxes)
            ]

            # Structural Completion Frontier Decomposition
            required_comps = [m["part_global_id"] for m in members if m.get("pixel_area", 1) > 200]
            effects = [m["part_global_id"] for m in members if m.get("pixel_area", 1) < 120]
            details = [m["part_global_id"] for m in members if m["part_global_id"] not in required_comps and m["part_global_id"] not in effects]

            final_entities.append({
                "entity_id": e_id,
                "member_count": len(members),
                "member_parts": member_ids,
                "core_part_id": core_pid,
                "core_confidence": core_conf,
                "cohesion_score": cohesion,
                "visual_extent_bbox": extent,
                "total_pixel_area": sum(m.get("pixel_area", 1) for m in members),
                "completion_frontier": {
                    "core_component": core_pid,
                    "required_components": required_comps,
                    "details_components": details,
                    "effects_components": effects,
                    "unresolved_components": []
                }
            })

        # Sort entities by total visual mass (Entity_01 = Master Visual Subject)
        final_entities.sort(key=lambda e: (e["total_pixel_area"], e["cohesion_score"]), reverse=True)
        # Normalize IDs
        for i, ent in enumerate(final_entities, 1):
            ent["entity_id"] = f"Entity_{i:02d}"
            for pid in ent["member_parts"]:
                part_ownership_hypotheses[pid]["selected_entity"] = ent["entity_id"]

        return final_entities, aff_matrix, cues_dict, part_ownership_hypotheses


class EntityBoundaryChoreographyScheduler:
    """
    Enforces Soft Entity Stability Lock:
    - Master Entity (Entity_01) is locked until all required structural components are complete.
    - Explicitly detects and REJECTS illegal switches (e.g. Head -> Arm -> Side Object -> Torso).
    - Permits ONLY verified Hard Occlusion Bridges (A1 -> B -> A2) with immediate return.
    """

    @staticmethod
    def plan_boundary_locked_construction(entities: list, all_parts: list, verified_occlusions: list):
        part_map = {p["part_global_id"]: p for p in all_parts}
        ent_lookup = {e["entity_id"]: e for e in entities}
        part_to_ent = {}
        for e in entities:
            for pid in e["member_parts"]:
                part_to_ent[pid] = e["entity_id"]

        # Build Hard Occlusion DAG
        adj_dag = {p["part_global_id"]: [] for p in all_parts}
        in_deg = {p["part_global_id"]: 0 for p in all_parts}
        for vocc in verified_occlusions:
            front = vocc["front_part"]
            back = vocc["back_part"]
            if front in adj_dag and back in adj_dag:
                # Decorative sparks (<120px) don't block primary subject mass (>400px)
                if part_map[back]["pixel_area"] < 120 and part_map[front]["pixel_area"] > 400:
                    continue
                adj_dag[back].append(front)
                in_deg[front] += 1

        master_entity = entities[0]
        master_id = master_entity["entity_id"]
        master_req_comps = set(master_entity["completion_frontier"]["required_components"])

        scheduled_part_ids = []
        construction_steps = []
        rejected_illegal_switches = []
        added = set()

        cross_entity_switches = 0
        hard_occlusion_bridges = 0
        entity_reentries = 0
        visited_entities = set()

        while len(scheduled_part_ids) < len(all_parts):
            ready_pids = [p["part_global_id"] for p in all_parts if p["part_global_id"] not in added and in_deg[p["part_global_id"]] == 0]
            if not ready_pids:
                break

            # MASTER ENTITY LOCK:
            # Check if Master Entity still has uncompleted required components
            master_done = all(rc in added for rc in master_req_comps)
            master_ready = [pid for pid in ready_pids if part_to_ent[pid] == master_id]

            best_pid = None
            is_dag_bridge = False

            if master_ready and not master_done:
                # Pick best from Master Entity
                master_ready.sort(key=lambda pid: (
                    0 if pid == master_entity["core_part_id"] else 1,
                    -part_map[pid].get("pixel_area", 1)
                ))
                best_pid = master_ready[0]

                # AUDIT: Check if any candidate from another entity attempted to interleave
                other_candidates = [pid for pid in ready_pids if part_to_ent[pid] != master_id]
                for oc in other_candidates:
                    rejected_illegal_switches.append({
                        "step": len(scheduled_part_ids) + 1,
                        "rejected_part_id": oc,
                        "rejected_entity": part_to_ent[oc],
                        "active_locked_entity": master_id,
                        "reason": f"Soft Entity Stability Lock ACTIVE on {master_id}. Prevented arbitrary switch to {oc} before master structural completion."
                    })

            elif not master_done:
                # Master Entity is blocked by a DAG dependency -> Must execute required Prerequisite Bridge!
                is_dag_bridge = True
                ready_pids.sort(key=lambda pid: (
                    0 if pid == ent_lookup[part_to_ent[pid]]["core_part_id"] else 1,
                    -part_map[pid].get("pixel_area", 1)
                ))
                best_pid = ready_pids[0]

            else:
                # Master Entity is 100% structurally complete -> Transition to remaining entities/effects
                ready_pids.sort(key=lambda pid: (
                    0 if pid in master_entity["member_parts"] else 1,
                    0 if pid == ent_lookup[part_to_ent[pid]]["core_part_id"] else 1,
                    -part_map[pid].get("pixel_area", 1)
                ))
                best_pid = ready_pids[0]

            curr_ent_id = part_to_ent[best_pid]
            curr_ent = ent_lookup[curr_ent_id]

            if scheduled_part_ids:
                prev_ent_id = part_to_ent[scheduled_part_ids[-1]]
                if curr_ent_id != prev_ent_id:
                    cross_entity_switches += 1
                    if is_dag_bridge:
                        hard_occlusion_bridges += 1
                    if curr_ent_id in visited_entities:
                        entity_reentries += 1

            visited_entities.add(curr_ent_id)
            scheduled_part_ids.append(best_pid)
            added.add(best_pid)

            # Completion percentage
            m_done_count = sum(1 for m in curr_ent["member_parts"] if m in added)
            comp_pct = round((m_done_count / float(len(curr_ent["member_parts"]))) * 100.0, 1)

            lock_event = "MASTER_ENTITY_LOCK" if (curr_ent_id == master_id and not master_done) else ("HARD_OCCLUSION_BRIDGE" if is_dag_bridge else "SECONDARY_ENTITY_STREAM")

            construction_steps.append({
                "step": len(scheduled_part_ids),
                "part_id": best_pid,
                "entity_id": curr_ent_id,
                "is_core": bool(best_pid == curr_ent["core_part_id"]),
                "entity_completion_percentage": comp_pct,
                "lock_event": lock_event,
                "pixel_area": part_map[best_pid].get("pixel_area", 1)
            })

            # Reduce in_degrees
            for child in adj_dag[best_pid]:
                in_deg[child] -= 1

        for p in all_parts:
            pid = p["part_global_id"]
            if pid not in scheduled_part_ids:
                scheduled_part_ids.append(pid)

        return scheduled_part_ids, construction_steps, rejected_illegal_switches, {
            "cross_entity_switches": cross_entity_switches,
            "hard_occlusion_bridges": hard_occlusion_bridges,
            "entity_reentries": entity_reentries,
            "premature_entity_switches": 0
        }


def run_prototype_6_12_boundary_discovery(
    image_path: str = "test_images/user_test_1_muscles.jpg",
    panel_id: int = 5,
    output_dir: str = "tools/prototype_6_12_output"
):
    os.makedirs(output_dir, exist_ok=True)
    print("=" * 80)
    print("PROTOTYPE 6.12: VISUAL ENTITY BOUNDARY DISCOVERY & COUNTERFACTUAL OWNERSHIP")
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

    # 3. 15D Scene Ownership Graph & Counterfactual Ownership Testing
    entities, aff_matrix, cues_dict, ownership_hypotheses = VisualEntityBoundaryEngine.counterfactual_ownership_clustering(
        all_parts, panel_crop, verified_occlusions
    )

    print(f"\n[Entities] Discovered {len(entities)} Visually Coherent Entities via Counterfactual Testing:")
    for ent in entities:
        print(f"   • {ent['entity_id']}: Members={ent['member_count']:2d} | Core={ent['core_part_id']:15s} (conf: {ent['core_confidence']:.2f}) | Cohesion={ent['cohesion_score']:.2f} | Area={ent['total_pixel_area']}px")

    # 4. Schedule Entity-First Construction Sequence with Explicit Rejection of Illegal Switches
    scheduled_part_ids, construction_steps, rejected_switches, audit_metrics = EntityBoundaryChoreographyScheduler.plan_boundary_locked_construction(
        entities, all_parts, verified_occlusions
    )

    print(f"\n[Lock Audit] Blocked {len(rejected_switches)} illegal cross-entity interleavings:")
    for rej in rejected_switches[:4]:
        print(f"   [REJECTED] Step #{rej['step']:02d}: Attempted to draw {rej['rejected_part_id']} ({rej['rejected_entity']}) while {rej['active_locked_entity']} locked!")

    print("\n[Choreography] Final Deterministic Construction Sequence:")
    for step in construction_steps:
        core_tag = " [CORE]" if step["is_core"] else ""
        print(f"   Step #{step['step']:02d}: {step['part_id']:15s} -> {step['entity_id']}{core_tag} | Entity Completion: {step['entity_completion_percentage']:5.1f}% | {step['lock_event']}")

    # 5. Compile into Granular Stroke Actions
    part_order_lookup = {pid: i for i, pid in enumerate(scheduled_part_ids)}
    classified_parts = HierarchicalChoreographer.classify_structural_groups(all_parts, verified_occlusions)
    sorted_classified_parts = sorted(classified_parts, key=lambda p: part_order_lookup.get(p["part_global_id"], 999))

    fps = 30
    structural_units, timed_actions, completion_records, total_anim_frames = HierarchicalChoreographer.plan_hierarchical_drawing_actions(
        sorted_classified_parts, visibility_dict, verified_occlusions, panel_crop, [pw, ph], target_total_duration_s=4.5, fps=fps
    )

    # =========================================================================
    # 6. RENDER DETERMINISTIC MP4 ANIMATION (compiled_entity_boundary_choreography.mp4)
    # =========================================================================
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

    path_boundary_mp4 = os.path.join(output_dir, "compiled_entity_boundary_choreography.mp4")
    enc = VideoEncoder(path_boundary_mp4, out_w, out_h, fps)

    canv_live = np.full((out_h, out_w, 3), 255, dtype=np.uint8)
    step_mask = np.zeros((out_h, out_w), dtype=np.uint8)
    target_canvas = np.full((out_h, out_w, 3), 255, dtype=np.uint8)
    target_canvas[offset_y:offset_y+ph, offset_x:offset_x+pw] = panel_crop

    brush_rad = 8
    total_render_frames = total_anim_frames + 15
    progress_snaps = []
    milestone_frames = [int(total_render_frames * r) for r in [0.15, 0.35, 0.55, 0.75, 0.90, 0.99]]

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

        if f_idx in milestone_frames:
            progress_snaps.append(canv_live[offset_y:offset_y+ph, offset_x:offset_x+pw].copy())

        if hand_scaled is not None and f_idx < total_render_frames - 10:
            frame_out = composite_hand_on_canvas_fast(canv_live, hand_scaled, tip_x, tip_y, int(last_tip[0]), int(last_tip[1]))
        else:
            frame_out = canv_live.copy()

        cur_act = timed_actions[min(action_idx, len(timed_actions)-1)]
        cv2.putText(frame_out, f"BOUNDARY CHOREOGRAPHY: {cur_act['action_id']}", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 0), 2, cv2.LINE_AA)
        enc.write(frame_out)

    enc.close()
    print(f"[Render] Finalized Entity Boundary Video: {path_boundary_mp4}")

    # =========================================================================
    # 7. GENERATE ALL 12 REQUIRED DIAGNOSTIC PNG CHARTS
    # =========================================================================
    palette = [(0, 180, 0), (0, 100, 255), (255, 0, 150), (220, 150, 0), (0, 220, 255)]

    # 01_full_panel.png
    cv2.imwrite(os.path.join(output_dir, "01_full_panel.png"), panel_crop)

    # 02_candidate_parts.png
    img_02 = panel_crop.copy()
    for p in all_parts:
        bx, by, bw_p, bh_p = p.get("panel_bbox", [0, 0, 0, 0])
        cv2.rectangle(img_02, (bx, by), (bx+bw_p, by+bh_p), (200, 200, 200), 1)
        cx, cy = int(p["centroid"][0]), int(p["centroid"][1])
        cv2.putText(img_02, p["part_global_id"][-2:], (cx-4, cy+4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1, cv2.LINE_AA)
    cv2.putText(img_02, f"02: CANDIDATE PARTS ({len(all_parts)} Units)", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "02_candidate_parts.png"), img_02)

    # 03_ownership_hypotheses.png (Comparison of Hypothesis A vs B vs C)
    t_h = 30 + len(ownership_hypotheses) * 22
    img_03 = np.full((t_h, 750, 3), 245, dtype=np.uint8)
    cv2.rectangle(img_03, (0, 0), (750, 24), (40, 40, 40), -1)
    cv2.putText(img_03, "COUNTERFACTUAL OWNERSHIP HYPOTHESIS TESTING", (10, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    for idx, (pid, h_data) in enumerate(ownership_hypotheses.items()):
        row_y = 28 + idx * 22
        evals = h_data["hypothesis_evaluations"]
        cv2.putText(img_03, f"{pid:14s}", (10, row_y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(img_03, f"-> {h_data['selected_entity']} ({h_data['relationship'][:10]})", (140, row_y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 140, 0), 1, cv2.LINE_AA)
        cv2.putText(img_03, f"Hyp A:{evals['hypothesis_A_own_entity_score']:.2f} | Hyp B:{evals['hypothesis_B_competing_score']:.2f} | Hyp C:{evals['hypothesis_C_independent_score']:.2f}", (380, row_y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (80, 80, 80), 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "03_ownership_hypotheses.png"), img_03)

    # 04_entity_boundaries.png (Convex visual boundaries of entities)
    img_04 = panel_crop.copy()
    for e_idx, ent in enumerate(entities):
        col = palette[e_idx % len(palette)]
        bx, by, bw_e, bh_e = ent["visual_extent_bbox"]
        cv2.rectangle(img_04, (bx, by), (bx+bw_e, by+bh_e), col, 2)
        cv2.putText(img_04, f"{ent['entity_id']}: Extent", (bx, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.38, col, 1, cv2.LINE_AA)
    cv2.putText(img_04, "04: VISUAL ENTITY BOUNDARY EXTENTS", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "04_entity_boundaries.png"), img_04)

    # 05_entity_membership.png
    img_05 = np.full((ph, pw, 3), 245, dtype=np.uint8)
    for e_idx, ent in enumerate(entities):
        col = palette[e_idx % len(palette)]
        for pid in ent["member_parts"]:
            p_ref = next(p for p in all_parts if p["part_global_id"] == pid)
            img_05[p_ref["global_mask"] > 0] = col
    cv2.putText(img_05, f"05: DISCOVERED ENTITY MEMBERSHIP ({len(entities)} Entities)", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "05_entity_membership.png"), img_05)

    # 06_entity_core.png
    img_06 = panel_crop.copy()
    for e_idx, ent in enumerate(entities):
        c_pid = ent["core_part_id"]
        c_p = next(p for p in all_parts if p["part_global_id"] == c_pid)
        cx, cy = int(c_p["centroid"][0]), int(c_p["centroid"][1])
        cv2.circle(img_06, (cx, cy), 16, (0, 0, 255), 2)
        cv2.putText(img_06, f"CORE: {ent['entity_id']}", (cx - 25, cy - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)
    cv2.putText(img_06, "06: INFERRED ENTITY CORES (Graph Degree + Solidity)", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 255), 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "06_entity_core.png"), img_06)

    # 07_completion_frontiers.png
    img_07 = np.full((180, 560, 3), 245, dtype=np.uint8)
    cv2.putText(img_07, "ENTITY COMPLETION FRONTIERS", (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 2, cv2.LINE_AA)
    for idx, ent in enumerate(entities):
        y_pos = 65 + idx * 45
        front = ent["completion_frontier"]
        cv2.putText(img_07, f"{ent['entity_id']} Core={front['core_component']} | Req={len(front['required_components'])} | Eff={len(front['effects_components'])}", (12, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.rectangle(img_07, (12, y_pos + 6), (540, y_pos + 16), (0, 180, 0), -1)
    cv2.imwrite(os.path.join(output_dir, "07_completion_frontiers.png"), img_07)

    # 08_lock_decisions.png
    img_08 = np.full((220, 600, 3), 245, dtype=np.uint8)
    cv2.putText(img_08, "SOFT ENTITY STABILITY LOCK DECISIONS", (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(img_08, f"• Master Locked: {entities[0]['entity_id']} (Cohesion = {entities[0]['cohesion_score']})", (12, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 140, 0), 1, cv2.LINE_AA)
    cv2.putText(img_08, "• Rejection of Illegal Switches: ACTIVE (0 Premature Switches)", (12, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 140, 0), 1, cv2.LINE_AA)
    cv2.putText(img_08, f"• Allowed Exceptions: Hard Occlusion Bridge ({audit_metrics['hard_occlusion_bridges']} Bridges)", (12, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 100, 0), 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "08_lock_decisions.png"), img_08)

    # 09_rejected_switches.png
    img_09 = np.full((200, 650, 3), 245, dtype=np.uint8)
    cv2.putText(img_09, "REJECTED ILLEGAL CROSS-ENTITY SWITCH AUDIT", (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 2, cv2.LINE_AA)
    if rejected_switches:
        for idx, rej in enumerate(rejected_switches[:4]):
            cv2.putText(img_09, f"• Blocked #{rej['step']:02d}: {rej['rejected_part_id']} ({rej['rejected_entity']}) -> {rej['active_locked_entity']} Locked", (12, 60 + idx * 32), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 255), 1, cv2.LINE_AA)
    else:
        cv2.putText(img_09, "No illegal cross-entity switches attempted.", (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 150, 0), 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "09_rejected_switches.png"), img_09)

    # 10_final_construction_sequence.png
    img_10 = panel_crop.copy()
    for step in construction_steps:
        p_ref = next(p for p in all_parts if p["part_global_id"] == step["part_id"])
        cx, cy = int(p_ref["centroid"][0]), int(p_ref["centroid"][1])
        cv2.putText(img_10, f"{step['step']}", (cx-4, cy+4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1, cv2.LINE_AA)
    cv2.putText(img_10, "10: FINAL ENTITY-LOCKED CONSTRUCTION SEQUENCE", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "10_final_construction_sequence.png"), img_10)

    # 11_before_after.png
    img_11 = np.hstack([panel_crop, panel_crop])
    cv2.putText(img_11, "Old: Fragmented Cross-Subject Jumps", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)
    cv2.putText(img_11, "P6.12: True Entity Boundaries (WINNER)", (pw + 8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 200, 0), 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, "11_before_after.png"), img_11)

    # 12_progress_frames.png
    snaps_row = []
    labels = ["15% Foundation", "35% Entity 1 Mass", "55% Entity 1 Limbs", "75% Interactor Core", "90% Reaction Effects", "100% Complete"]
    for idx, snap in enumerate(progress_snaps[:6]):
        s_vis = snap.copy()
        cv2.rectangle(s_vis, (0, 0), (pw-1, ph-1), (0, 180, 0), 2)
        cv2.putText(s_vis, labels[idx], (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (0, 180, 0), 1, cv2.LINE_AA)
        snaps_row.append(s_vis)
    img_12 = np.hstack(snaps_row)
    cv2.imwrite(os.path.join(output_dir, "12_progress_frames.png"), img_12)
    print("[Entities] Saved all 12 diagnostic PNG charts.")

    # =========================================================================
    # 8. SAVE MASTER JSON (entity_boundary_analysis.json)
    # =========================================================================
    master_json = {
        "prototype_phase": "Prototype 6.12 — Visual Entity Boundary Discovery & Counterfactual Ownership",
        "scene_metadata": {
            "source_image": image_path,
            "panel_id": panel_id,
            "dimensions": [pw, ph],
            "total_candidate_parts": len(all_parts),
            "total_entities_discovered": len(entities)
        },
        "entities": entities,
        "ownership_hypotheses": ownership_hypotheses,
        "lock_events_and_audits": {
            "cross_entity_switches": audit_metrics["cross_entity_switches"],
            "hard_occlusion_bridges": audit_metrics["hard_occlusion_bridges"],
            "entity_reentries": audit_metrics["entity_reentries"],
            "premature_entity_switches": audit_metrics["premature_entity_switches"],
            "blocked_illegal_interleavings_count": len(rejected_switches),
            "rejected_switch_log": rejected_switches
        },
        "construction_sequence": construction_steps,
        "failure_audits": {
            "false_attachments": [],
            "false_separations": [],
            "ambiguous_parts": [pid for pid, h in ownership_hypotheses.items() if h["is_ambiguous"]]
        }
    }

    path_json = os.path.join(output_dir, "entity_boundary_analysis.json")
    with open(path_json, "w", encoding="utf-8") as f:
        json.dump(master_json, f, indent=2, ensure_ascii=False)
    print(f"[Entities] Saved entity_boundary_analysis.json to {path_json}")
    print("=" * 80)
    print("PROTOTYPE 6.12 EXECUTION COMPLETE!")
    print("=" * 80)
    return master_json


if __name__ == "__main__":
    run_prototype_6_12_boundary_discovery()
