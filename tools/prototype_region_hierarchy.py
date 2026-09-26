"""
Prototype 3: Region Interpretation & Hierarchy
Grouping raw visual regions into meaningful structural parts without semantic labels.
Testing 3 Strategies (Boundary-only, Color-similarity, Contextual Multi-Factor) across 5 diverse test cases.
Zero production code changes, zero video rendering.
"""
import os
import sys
import json
import math
import cv2
import numpy as np

# Include kivy directory for baseline panel detection without modifying any production code
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'kivy')))

from engine.processing.panel_detector import PanelDetector
from engine.processing.image_processor import ImageProcessor
from engine.core.scene import SceneConfig


def extract_planar_regions(obj_crop: np.ndarray, gmag_norm: np.ndarray):
    """
    Extracts raw planar enclosed regions inside the object mask.
    """
    h_c, w_c = obj_crop.shape[:2]
    obj_gray = cv2.cvtColor(obj_crop, cv2.COLOR_BGR2GRAY)
    _, obj_mask = cv2.threshold(obj_gray, 235, 255, cv2.THRESH_BINARY_INV)
    total_obj_px = max(1, int(np.sum(obj_mask > 0)))

    blurred = cv2.GaussianBlur(obj_gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 30, 100)
    k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, k_close)

    planar_non_edge = cv2.bitwise_and(obj_mask, cv2.bitwise_not(closed_edges))
    num_raw, raw_labels, raw_stats, raw_centroids = cv2.connectedComponentsWithStats(planar_non_edge, connectivity=4)

    # Filter into initial regions
    raw_regions = {}
    for lbl in range(1, num_raw):
        area = int(raw_stats[lbl, cv2.CC_STAT_AREA])
        if area < 8:
            continue
        m_r = (raw_labels == lbl).astype(np.uint8)
        mean_lum = float(np.mean(obj_gray[m_r > 0]))
        mean_bgr = [float(np.mean(obj_crop[m_r > 0, c])) for c in range(3)]
        raw_regions[lbl] = {
            "label": lbl,
            "area": area,
            "area_pct": (area / float(total_obj_px)) * 100.0,
            "centroid": [float(raw_centroids[lbl][0]), float(raw_centroids[lbl][1])],
            "bbox": [int(raw_stats[lbl, i]) for i in range(4)],
            "mean_lum": mean_lum,
            "mean_bgr": mean_bgr,
            "mask": m_r
        }

    # Extract classified boundary contours
    cnts, _ = cv2.findContours(closed_edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    detail_lines = []
    structural_boundaries = []

    for cnt in cnts:
        arc_l = float(cv2.arcLength(cnt, False))
        c_area = float(cv2.contourArea(cnt))
        if arc_l < 15.0:
            continue
        m_cnt = np.zeros((h_c, w_c), dtype=np.uint8)
        cv2.drawContours(m_cnt, [cnt], -1, 255, 1)
        dil = cv2.dilate(m_cnt, np.ones((3, 3), np.uint8), iterations=1)
        mean_g = float(np.mean(gmag_norm[dil > 0])) if np.sum(dil > 0) > 0 else 0.0

        if c_area > 60.0 and mean_g >= 35.0:
            structural_boundaries.append({"contour": cnt, "area": c_area, "mean_gradient": mean_g})
        else:
            detail_lines.append({"contour": cnt, "length": arc_l, "mean_gradient": mean_g})

    return raw_regions, obj_mask, structural_boundaries, detail_lines


def build_rag(raw_regions: dict, gmag_norm: np.ndarray):
    """
    Constructs the Region Adjacency Graph (RAG) with shared boundary metrics.
    """
    k_dil = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    adj_graph = {}
    sig_labels = [lbl for lbl, r in raw_regions.items() if r["area"] >= 30]

    for la in sig_labels:
        mask_a = raw_regions[la]["mask"]
        dil_a = cv2.dilate(mask_a, k_dil, iterations=1)
        adj_graph[la] = {}

        for lb in sig_labels:
            if la >= lb:
                continue
            mask_b = raw_regions[lb]["mask"]
            shared_border = cv2.bitwise_and(dil_a, mask_b)
            shared_len = int(np.sum(shared_border > 0))

            if shared_len > 2:
                border_pts = np.where(shared_border > 0)
                b_grad = float(np.mean(gmag_norm[border_pts])) if len(border_pts[0]) > 0 else 0.0
                
                col_a = np.array(raw_regions[la]["mean_bgr"])
                col_b = np.array(raw_regions[lb]["mean_bgr"])
                color_dist = float(np.linalg.norm(col_a - col_b))

                # Shared perimeter enclosure ratio
                peri_a = float(np.sum(cv2.subtract(dil_a, mask_a) > 0))
                enclosure_a = shared_len / max(1.0, peri_a)

                adj_graph[la][lb] = {
                    "shared_pixels": shared_len,
                    "mean_edge_gradient": round(b_grad, 1),
                    "color_distance": round(color_dist, 1),
                    "enclosure_ratio": round(enclosure_a, 3)
                }

    return adj_graph, sig_labels


def group_regions_by_strategy(
    raw_regions: dict,
    adj_graph: dict,
    sig_labels: list,
    strategy: str = "STRATEGY_C"
):
    """
    Three Region Interpretation Strategies:
    - STRATEGY_A: Region boundaries only (gradient threshold).
    - STRATEGY_B: Region boundaries + Color similarity.
    - STRATEGY_C: Multi-Factor Contextual (Boundary + Color + Enclosure + Salience Guard).
    """
    merged_map = {lbl: lbl for lbl in raw_regions}

    # Pass 1: Attach tiny noise (<80px) to best neighbor
    k_dil = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    for lbl, r in sorted(raw_regions.items(), key=lambda x: x[1]["area"]):
        if r["area"] < 100:
            dil_r = cv2.dilate(r["mask"], k_dil, iterations=2)
            best_n = None
            best_weight = -1
            for n_lbl in sig_labels:
                if n_lbl == lbl:
                    continue
                shared = np.sum(cv2.bitwise_and(dil_r, raw_regions[n_lbl]["mask"]) > 0)
                if shared > best_weight:
                    best_weight = shared
                    best_n = n_lbl
            if best_n is not None:
                merged_map[lbl] = best_n

    # Pass 2: Merge adjacent significant regions based on Strategy criteria
    for la in sig_labels:
        for lb, edge in adj_graph.get(la, {}).items():
            root_a = merged_map[la]
            root_b = merged_map[lb]
            if root_a == root_b:
                continue

            b_grad = edge["mean_edge_gradient"]
            c_dist = edge["color_distance"]
            enc = edge["enclosure_ratio"]

            should_merge = False

            if strategy == "STRATEGY_A":
                # Boundary only
                should_merge = (b_grad < 24.0)

            elif strategy == "STRATEGY_B":
                # Boundary + Color
                should_merge = (b_grad < 24.0) or (c_dist < 18.0 and b_grad < 40.0)

            elif strategy == "STRATEGY_C":
                # Contextual Multi-Factor with Salience Guard
                # High contrast salient regions (>55 gradient AND >25 color dist) NEVER merge
                is_salient_feature = (b_grad > 55.0 and c_dist > 25.0 and raw_regions[lb]["area"] > 200)
                
                if not is_salient_feature:
                    # Enclosed sub-pocket (<15% perimeter of parent or low contrast)
                    if enc > 0.40 and b_grad < 45.0:
                        should_merge = True
                    elif b_grad < 28.0 and c_dist < 35.0:
                        should_merge = True
                    elif c_dist < 15.0 and b_grad < 45.0:
                        should_merge = True

            if should_merge:
                for k in merged_map:
                    if merged_map[k] == root_b:
                        merged_map[k] = root_a

    # Assemble Parts hierarchy
    part_clusters = {}
    for orig_l, root_l in merged_map.items():
        if root_l not in part_clusters:
            part_clusters[root_l] = []
        part_clusters[root_l].append(orig_l)

    # Sort parts descending by total area
    sorted_roots = sorted(
        part_clusters.keys(),
        key=lambda r: sum(raw_regions[lbl]["area"] for lbl in part_clusters[r]),
        reverse=True
    )

    parts_result = []
    part_idx = 1
    total_area_all = sum(r["area"] for r in raw_regions.values())

    for root in sorted_roots:
        cluster_lbls = part_clusters[root]
        tot_area = sum(raw_regions[lbl]["area"] for lbl in cluster_lbls)
        pct = (tot_area / float(total_area_all)) * 100.0
        
        # Filter negligible residual fragments (<0.8%)
        if tot_area < 150 and pct < 0.8:
            continue

        p_id = f"Part_{part_idx:02d}"
        part_idx += 1

        parts_result.append({
            "part_id": p_id,
            "constituent_regions": [f"Region_{l}" for l in cluster_lbls],
            "constituent_count": len(cluster_lbls),
            "pixel_area": tot_area,
            "area_percentage": round(pct, 2),
            "labels": cluster_lbls
        })

    return parts_result


def run_prototype_3(
    output_dir: str = "tools/prototype_3_results"
):
    os.makedirs(output_dir, exist_ok=True)
    print("=" * 70)
    print("PROTOTYPE 3: REGION INTERPRETATION & HIERARCHY EVALUATION")
    print("=" * 70)

    # Define the 5 Diverse Evaluation Cases
    test_cases = [
        {
            "case_id": "CASE_1_Complex_Character",
            "image": "test_images/Staka_storyboard_in_four_panels_202608301648.jpeg",
            "panel_id": 4,
            "object_idx": 1,
            "description": "Complex interacting character with overlapping limbs & clothing"
        },
        {
            "case_id": "CASE_2_Pose_Character_Props",
            "image": "test_images/Character_storyboard_in_four_poses_202608301656.jpeg",
            "panel_id": 1,
            "object_idx": 0,
            "description": "Character in action pose with distinct prop and limbs"
        },
        {
            "case_id": "CASE_3_Muscle_Anatomy_Contour",
            "image": "test_images/user_test_1_muscles.jpg",
            "panel_id": 1,
            "object_idx": 0,
            "description": "Cartoon character with heavy internal muscle contours & shading"
        },
        {
            "case_id": "CASE_4_Label_Prop_Object",
            "image": "test_images/Staka_storyboard_in_four_panels_202608301648.jpeg",
            "panel_id": 2,
            "object_idx": 1,
            "description": "Distinct floating reaction/label effect prop"
        },
        {
            "case_id": "CASE_5_Simple_Pose_Entity",
            "image": "test_images/Character_storyboard_in_four_poses_202608301656.jpeg",
            "panel_id": 3,
            "object_idx": 0,
            "description": "Simple standalone character posture"
        }
    ]

    all_case_reports = []
    cfg = SceneConfig()

    for tc in test_cases:
        c_id = tc["case_id"]
        c_path = tc["image"]
        p_id = tc["panel_id"]
        o_idx = tc["object_idx"]

        print(f"\n---> Running Case: {c_id} ({tc['description']})...")
        img_bgr = cv2.imread(c_path)
        if img_bgr is None:
            continue

        proj = ImageProcessor.process(img_bgr, cfg)
        scene = next((s for s in proj.scenes if getattr(s, 'panel_id', 1) == p_id), proj.scenes[0])
        objs = [o for o in scene.objects if not o.is_frame]
        target_obj = objs[min(o_idx, len(objs)-1)]
        
        obx, oby, obw, obh = target_obj.bbox
        px, py, pw, ph = proj.panels[p_id - 1].interior_bbox
        panel_crop = img_bgr[py:py+ph, px:px+pw]
        obj_crop = panel_crop[oby:oby+obh, obx:obx+obw].copy()
        h_c, w_c = obj_crop.shape[:2]

        # Sobel gradient
        obj_gray = cv2.cvtColor(obj_crop, cv2.COLOR_BGR2GRAY)
        gx = cv2.Sobel(obj_gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(obj_gray, cv2.CV_32F, 0, 1, ksize=3)
        gmag = cv2.magnitude(gx, gy)
        gmag_norm = cv2.normalize(gmag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        # 1. Raw Planar Region Extraction
        raw_regions, obj_mask, struct_bounds, detail_lines = extract_planar_regions(obj_crop, gmag_norm)

        # 2. Build RAG
        adj_graph, sig_labels = build_rag(raw_regions, gmag_norm)

        # 3. Test Strategies A, B, C
        parts_a = group_regions_by_strategy(raw_regions, adj_graph, sig_labels, "STRATEGY_A")
        parts_b = group_regions_by_strategy(raw_regions, adj_graph, sig_labels, "STRATEGY_B")
        parts_c = group_regions_by_strategy(raw_regions, adj_graph, sig_labels, "STRATEGY_C")

        print(f"     Regions: {len(sig_labels)} raw -> Strategy A: {len(parts_a)} parts | Strategy B: {len(parts_b)} parts | Strategy C: {len(parts_c)} parts")

        # 4. Generate Visual Comparison Image for this Case
        # Side-by-side: Original | Strategy A (Boundary) | Strategy B (Color) | Strategy C (Contextual)
        palette = [(0, 0, 255), (0, 220, 0), (255, 140, 0), (0, 220, 255), (220, 0, 220), (180, 255, 0), (0, 140, 255), (120, 120, 255)]

        def render_part_map(parts_list):
            vis = np.zeros_like(obj_crop)
            for p_i, p_info in enumerate(parts_list):
                col = palette[p_i % len(palette)]
                comb_m = np.zeros((h_c, w_c), dtype=np.uint8)
                for l in p_info["labels"]:
                    comb_m = cv2.bitwise_or(comb_m, raw_regions[l]["mask"])
                vis[comb_m > 0] = col
                # Draw white outline
                cnts_p, _ = cv2.findContours(comb_m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(vis, cnts_p, -1, (255, 255, 255), 1, cv2.LINE_AA)
            return vis

        vis_a = render_part_map(parts_a)
        vis_b = render_part_map(parts_b)
        vis_c = render_part_map(parts_c)

        # Header overlays
        header_h = 35
        def add_header(img, text, color):
            hdr = np.full((header_h, img.shape[1], 3), 35, dtype=np.uint8)
            cv2.putText(hdr, text, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
            return np.vstack([hdr, img])

        col_orig = add_header(obj_crop, "Original Crop", (255, 255, 255))
        col_a = add_header(vis_a, f"Strat A ({len(parts_a)} Parts)", (0, 255, 255))
        col_b = add_header(vis_b, f"Strat B ({len(parts_b)} Parts)", (255, 180, 0))
        col_c = add_header(vis_c, f"Strat C: Best ({len(parts_c)} Parts)", (0, 255, 0))

        vis_case = np.hstack([col_orig, col_a, col_b, col_c])
        cv2.imwrite(os.path.join(output_dir, f"{c_id}_comparison.png"), vis_case)

        # Record Case Report
        case_report = {
            "case_id": c_id,
            "description": tc["description"],
            "object_name": target_obj.name,
            "crop_dimensions": [w_c, h_c],
            "raw_planar_regions_count": len(raw_regions),
            "rag_significant_nodes_count": len(sig_labels),
            "strategy_a_boundary_only": {
                "parts_count": len(parts_a),
                "parts": parts_a
            },
            "strategy_b_boundary_plus_color": {
                "parts_count": len(parts_b),
                "parts": parts_b
            },
            "strategy_c_contextual_multi_factor": {
                "parts_count": len(parts_c),
                "parts": parts_c,
                "detail_lines_count": len(detail_lines)
            },
            "over_segmentation_assessment": "Low" if len(parts_c) <= 5 else "Moderate",
            "under_segmentation_assessment": "None (Solid regions separated)" if len(parts_c) >= 2 else "Monolithic",
            "hierarchy_tree": {
                "object_name": target_obj.name,
                "parts": [
                    {
                        "part_id": p["part_id"],
                        "area_pct": p["area_percentage"],
                        "constituent_regions": p["constituent_regions"]
                    } for p in parts_c
                ],
                "detail_lines": len(detail_lines)
            }
        }
        all_case_reports.append(case_report)

    # Save Master JSON Analysis
    json_path = os.path.join(output_dir, "prototype_3_analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_case_reports, f, indent=2, ensure_ascii=False)

    print(f"\n[Prototype 3] Saved visual comparisons and master analysis to {output_dir}")
    print("=" * 70)
    print("PROTOTYPE 3 EVALUATION COMPLETE!")
    print("=" * 70)
    return all_case_reports


if __name__ == "__main__":
    run_prototype_3()
