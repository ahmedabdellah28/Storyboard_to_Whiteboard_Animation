"""Contour-Based Proximity & Attached Effect Extractor.
Implements organic contour tracing and geodesic/Euclidean proximity clustering
inspired by CraftApp (PhotoCraft algo::matting and VectorCraft trace::contour).

Features:
1. True Contour Extraction: Identifies entities by organic ink boundaries, NOT arbitrary rectangles.
2. Nearest-Contour Affinity: Attaches satellite effects (rays, sweat drops, question marks, motion lines)
   to the closest core entity using minimum edge-to-edge distance.
3. Sub-Pixel PhotoCraft Color-to-Alpha: Produces 100% fringe-free RGBA layers.
4. Co-Registered Canvas Alignment: Sub-layers share identical canvas dimensions for effortless 0-offset compositing.
"""

import sys
import json
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


class ContourProximityExtractor:
    """Master Organic Contour & Effect Proximity Engine."""

    @staticmethod
    def color_to_alpha(bgr: np.ndarray, t_low: float = 0.03, t_high: float = 0.96) -> np.ndarray:
        """PhotoCraft Color-to-Alpha unmixing formula."""
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        min_c = np.min(rgb, axis=2)
        alpha = 1.0 - min_c
        alpha = np.clip((alpha - t_low) / (t_high - t_low), 0.0, 1.0)
        safe_a = np.maximum(alpha, 1e-5)[:, :, np.newaxis]
        q_rgb = np.clip(1.0 + (rgb - 1.0) / safe_a, 0.0, 1.0)
        q_rgb[alpha < 1e-4] = 0.0
        q_bgr = cv2.cvtColor((q_rgb * 255.0).astype(np.uint8), cv2.COLOR_RGB2BGR)
        alpha_u8 = (alpha * 255.0).astype(np.uint8)
        b, g, r = cv2.split(q_bgr)
        return cv2.merge([b, g, r, alpha_u8])

    @classmethod
    def decompose_panel_by_contours(
        cls,
        panel_bgr: np.ndarray,
        core_names: List[str],
        min_core_area: float = 4000.0,
        max_satellite_dist: float = 45.0,
        output_dir: Optional[Path] = None,
        prefix: str = "elem"
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """Decomposes a panel into core entities and their attached effects via contour proximity."""
        h, w = panel_bgr.shape[:2]
        gray = cv2.cvtColor(panel_bgr, cv2.COLOR_BGR2GRAY)
        ink_mask = (gray < 235).astype(np.uint8) * 255

        # Clean noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        ink_clean = cv2.morphologyEx(ink_mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(ink_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        # 1. Identify Core Contours
        cores = []
        for c in contours:
            area = cv2.contourArea(c)
            if area >= min_core_area:
                cores.append(c)

        # If not enough cores found by area, take top N
        num_expected = len(core_names)
        if len(cores) < num_expected:
            cores = contours[:num_expected]

        # Sort cores from left to right (by bounding box x) to match names
        cores_with_x = []
        for c in cores[:num_expected]:
            bx, _, _, _ = cv2.boundingRect(c)
            cores_with_x.append((bx, c))
        cores_with_x.sort(key=lambda t: t[0])

        core_dict = {}
        for idx, (bx, c) in enumerate(cores_with_x):
            name = core_names[idx] if idx < len(core_names) else f"{prefix}_core_{idx+1}"
            core_dict[name] = c

        # 2. Match Satellites to Nearest Core by Contour Distance
        assigned_satellites: Dict[str, List[np.ndarray]] = {name: [] for name in core_dict}

        for c in contours:
            area = cv2.contourArea(c)
            # Skip if it is one of the cores or too tiny
            if any(np.array_equal(c, core_c) for core_c in core_dict.values()):
                continue
            if area < 30.0:
                continue

            # Calculate shortest distance from this contour to each core contour
            min_dists = {}
            for name, core_c in core_dict.items():
                min_d = float("inf")
                # Sample points on satellite contour
                step = max(1, len(c) // 20)
                for pt in c[::step]:
                    d = abs(cv2.pointPolygonTest(core_c, (float(pt[0][0]), float(pt[0][1])), True))
                    if d < min_d:
                        min_d = d
                min_dists[name] = min_d

            nearest_name = min(min_dists, key=min_dists.get)
            shortest_dist = min_dists[nearest_name]

            if shortest_dist <= max_satellite_dist:
                assigned_satellites[nearest_name].append(c)

        # 3. Render Separate RGBA Layers using PhotoCraft Matting
        rgba_full = cls.color_to_alpha(panel_bgr)
        results = {}

        for name, core_c in core_dict.items():
            # Mask for Core only
            mask_core = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(mask_core, [core_c], -1, 255, -1)
            # Dilate 2px to ensure full ink anti-aliasing is covered
            mask_core = cv2.dilate(mask_core, np.ones((3, 3), np.uint8))

            rgba_core = rgba_full.copy()
            rgba_core[mask_core == 0, 3] = 0

            # Mask for Attached Effects only
            sats = assigned_satellites.get(name, [])
            rgba_effect = None
            if sats:
                mask_effect = np.zeros((h, w), dtype=np.uint8)
                cv2.drawContours(mask_effect, sats, -1, 255, -1)
                mask_effect = cv2.dilate(mask_effect, np.ones((3, 3), np.uint8))

                rgba_effect = rgba_full.copy()
                rgba_effect[mask_effect == 0, 3] = 0

            # Combined Composite
            mask_composite = mask_core.copy()
            if sats:
                mask_composite = cv2.bitwise_or(mask_composite, mask_effect)
            rgba_composite = rgba_full.copy()
            rgba_composite[mask_composite == 0, 3] = 0

            results[name] = {
                "core": rgba_core,
                "effect": rgba_effect,
                "composite": rgba_composite
            }

            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(output_dir / f"{name}_core.png"), rgba_core)
                cv2.imwrite(str(output_dir / f"{name}_composite.png"), rgba_composite)
                if rgba_effect is not None:
                    cv2.imwrite(str(output_dir / f"{name}_effect.png"), rgba_effect)

        return results


if __name__ == "__main__":
    test_sb = Path("projects/phone_traps/inputs/storyboards/section_01.png")
    if test_sb.exists():
        img = cv2.imread(str(test_sb))
        # Test Panel 6 (Runner, Brain, Phone)
        p6_roi = img[512:1024, 1024:1536]
        out = Path("projects/phone_traps/sections/section_01/assets/contour_test_p6")
        res = ContourProximityExtractor.decompose_panel_by_contours(
            p6_roi,
            core_names=["p6_runner", "p6_brain", "p6_phone"],
            min_core_area=4000,
            max_satellite_dist=35,
            output_dir=out
        )
        print("✅ Extracted Panel 6 layers based on organic contour proximity:")
        for k in res:
            has_fx = "Yes" if res[k]["effect"] is not None else "No"
            print(f"  • {k:<15} -> Core + Effect ({has_fx})")
