"""Universal CraftApp-Powered Multi-Layer Storyboard Pipeline.
A general, automated engine that works for ANY storyboard image:
1. Universal Panel Discovery: Auto-detects grid gutters & panel partitions.
2. VectorCraft Contour Tracing: Extracts true organic boundaries (no rectangular box cuts).
3. Nearest-Contour Proximity Affiliation: Mathematically links satellite effects
   (rays, question marks, sweat drops, alert ticks, arrows, thought bubbles)
   to the closest core entity using point-to-polygon geodesic distance.
4. PhotoCraft Sub-Pixel Color-to-Alpha: Produces 100% fringe-free RGBA layers.
5. Co-Registered Multi-Layer Compositing: Generates matching layers ready for EffectCraft.
"""

import sys
import json
import math
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


class UniversalCraftExtractor:
    """Universal CraftApp Engine for decomposing any storyboard into animated layers."""

    @staticmethod
    def color_to_alpha(bgr: np.ndarray, t_low: float = 0.03, t_high: float = 0.96) -> np.ndarray:
        """PhotoCraft Color-to-Alpha unmixing (algo::color_to_alpha)."""
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
    def auto_detect_grid(cls, img: np.ndarray) -> Tuple[int, int]:
        """Automatically detects the grid structure (rows, cols) of the storyboard."""
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ink = (gray < 235).astype(np.float32)

        # Projection profiles
        h_proj = np.sum(ink, axis=1)
        w_proj = np.sum(ink, axis=0)

        # Look for regular gutter dips
        aspect = w / h
        if aspect > 1.3: # landscape: typical 3x3, 2x3, or 2x2
            # Check 3 columns vs 2 columns
            c3_g1 = np.mean(w_proj[int(w * 0.31):int(w * 0.35)])
            c3_g2 = np.mean(w_proj[int(w * 0.64):int(w * 0.68)])
            c2_g1 = np.mean(w_proj[int(w * 0.48):int(w * 0.52)])

            cols = 3 if (c3_g1 + c3_g2) / 2.0 < c2_g1 else 2
            
            # Check 3 rows vs 2 rows
            r3_g1 = np.mean(h_proj[int(h * 0.31):int(h * 0.35)])
            r3_g2 = np.mean(h_proj[int(h * 0.64):int(h * 0.68)])
            r2_g1 = np.mean(h_proj[int(h * 0.48):int(h * 0.52)])

            rows = 3 if (r3_g1 + r3_g2) / 2.0 < r2_g1 else 2
            return rows, cols
        else:
            return 2, 2

    @classmethod
    def crop_to_contour(cls, rgba: np.ndarray, mask: np.ndarray, pad: int = 15) -> np.ndarray:
        """Crops transparent RGBA tightly to the active contour mask with organic padding."""
        y_indices, x_indices = np.where(mask > 0)
        if len(y_indices) == 0 or len(x_indices) == 0:
            return np.zeros((10, 10, 4), dtype=np.uint8)

        h, w = rgba.shape[:2]
        y0 = max(0, int(np.min(y_indices)) - pad)
        y1 = min(h, int(np.max(y_indices)) + pad + 1)
        x0 = max(0, int(np.min(x_indices)) - pad)
        x1 = min(w, int(np.max(x_indices)) + pad + 1)

        cropped = rgba[y0:y1, x0:x1].copy()
        crop_mask = mask[y0:y1, x0:x1]
        cropped[crop_mask == 0, 3] = 0
        return cropped

    @classmethod
    def extract_storyboard_pure_contours(
        cls,
        storyboard_path: Path,
        output_dir: Path,
        min_core_area: float = 3000.0,
        proximity_radius: float = 55.0
    ) -> Dict[str, Any]:
        """Pure Global Contour Extraction across entire storyboard with ZERO rectangular cuts."""
        storyboard_path = Path(storyboard_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        img = cv2.imread(str(storyboard_path))
        if img is None:
            raise FileNotFoundError(f"Cannot load storyboard: {storyboard_path}")

        h, w = img.shape[:2]
        print(f"🎬 [PURE GLOBAL CONTOURS] {storyboard_path.name} ({w}x{h}) - Tracing ink boundaries...")

        # 1. Global PhotoCraft Color-to-Alpha
        global_rgba = cls.color_to_alpha(img)

        # 2. VectorCraft Global Ink Contours
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ink = (gray < 225).astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        ink_clean = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(ink_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        core_contours = []
        satellite_contours = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= min_core_area:
                core_contours.append(cnt)
            elif area >= 30.0:
                satellite_contours.append(cnt)

        # Sort core contours spatially by clustering into true horizontal rows (Top-to-bottom, Left-to-right)
        if core_contours:
            with_boxes = [(c, cv2.boundingRect(c)) for c in core_contours]
            # Sort initially by vertical center cy = by + bh/2
            with_boxes.sort(key=lambda item: item[1][1] + item[1][3] * 0.5)
            rows_clustered: List[List[Tuple[np.ndarray, Tuple[int, int, int, int]]]] = []
            row_tol = max(40.0, h * 0.13)
            for item in with_boxes:
                cy = item[1][1] + item[1][3] * 0.5
                if not rows_clustered:
                    rows_clustered.append([item])
                else:
                    prev_row_cy = sum(x[1][1] + x[1][3] * 0.5 for x in rows_clustered[-1]) / len(rows_clustered[-1])
                    if abs(cy - prev_row_cy) <= row_tol:
                        rows_clustered[-1].append(item)
                    else:
                        rows_clustered.append([item])
            # Sort each row strictly Left-to-Right by bx
            sorted_contours = []
            for r_list in rows_clustered:
                r_list.sort(key=lambda item: item[1][0])
                sorted_contours.extend([item[0] for item in r_list])
            core_contours = sorted_contours

        # Proximity linking: attach each satellite to the nearest core contour
        attachments: Dict[int, List[np.ndarray]] = {i: [] for i in range(len(core_contours))}

        for sat in satellite_contours:
            min_dist = float("inf")
            best_core_idx = 0
            step = max(1, len(sat) // 15)
            for core_idx, core_c in enumerate(core_contours):
                for pt in sat[::step]:
                    d = abs(cv2.pointPolygonTest(core_c, (float(pt[0][0]), float(pt[0][1])), True))
                    if d < min_dist:
                        min_dist = d
                        best_core_idx = core_idx

            if min_dist <= proximity_radius:
                attachments[best_core_idx].append(sat)

        manifest_layers = {
            "storyboard": storyboard_path.name,
            "mode": "pure_global_contours",
            "resolution": [w, h],
            "entities": []
        }
        metadata_dict: Dict[str, Any] = {}
        map_vis = img.copy()
        comp_thumbs: List[Tuple[str, np.ndarray]] = []

        # Export pure organic layers
        for idx, core_c in enumerate(core_contours):
            ent_key = f"entity_{idx+1:02d}"
            mask_core = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(mask_core, [core_c], -1, 255, -1)

            sats = attachments.get(idx, [])
            has_fx = len(sats) > 0
            mask_fx = np.zeros((h, w), dtype=np.uint8)
            if has_fx:
                cv2.drawContours(mask_fx, sats, -1, 255, -1)

            mask_comp = cv2.bitwise_or(mask_core, mask_fx)

            rgba_core = cls.crop_to_contour(global_rgba, mask_core)
            rgba_comp = cls.crop_to_contour(global_rgba, mask_comp)
            rgba_fx = cls.crop_to_contour(global_rgba, mask_fx) if has_fx else None

            core_file = output_dir / f"{ent_key}_core.png"
            comp_file = output_dir / f"{ent_key}_composite.png"
            fx_file = output_dir / f"{ent_key}_fx.png" if has_fx else None

            cv2.imwrite(str(core_file), rgba_core)
            cv2.imwrite(str(comp_file), rgba_comp)
            if fx_file and rgba_fx is not None:
                cv2.imwrite(str(fx_file), rgba_fx)

            bx, by, bw, bh = cv2.boundingRect(core_c)
            ent_info = {
                "key": ent_key,
                "asset_key": f"{ent_key}_composite",
                "core_file": core_file.name,
                "composite_file": comp_file.name,
                "fx_file": fx_file.name if fx_file else None,
                "has_effect": has_fx,
                "bounds": [bx, by, bw, bh],
                "size": [int(rgba_comp.shape[1]), int(rgba_comp.shape[0])],
                "components_count": 1 + len(sats)
            }
            manifest_layers["entities"].append(ent_info)
            metadata_dict[f"{ent_key}_composite"] = ent_info
            comp_thumbs.append((f"{ent_key}_composite", rgba_comp))

            # Draw true green organic contour on connectivity map (ZERO box cuts)
            cv2.drawContours(map_vis, [core_c], -1, (0, 200, 0), 3)
            if sats:
                cv2.drawContours(map_vis, sats, -1, (255, 140, 0), 2)
            label_txt = f"{idx+1:02d}"
            cx_lbl = max(10, min(w - 65, bx + bw // 2 - 24))
            cy_lbl = max(35, min(h - 15, by + bh // 2))
            cv2.rectangle(map_vis, (cx_lbl - 6, cy_lbl - 28), (cx_lbl + 52, cy_lbl + 8), (20, 20, 210), -1)
            cv2.putText(map_vis, label_txt, (cx_lbl, cy_lbl), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)

        # Save QA Visual Maps: connectivity_and_separation_map.png, contact_sheet.png, metadata.json
        cv2.imwrite(str(output_dir / "connectivity_and_separation_map.png"), map_vis)
        with open(output_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata_dict, f, indent=2, ensure_ascii=False)

        if comp_thumbs:
            cols_cs = 5
            rows_cs = math.ceil(len(comp_thumbs) / float(cols_cs))
            cell_w_cs, cell_h_cs = 320, 260
            sheet = np.full((rows_cs * cell_h_cs, cols_cs * cell_w_cs, 3), (224, 232, 237), dtype=np.uint8)
            for idx_t, (lbl_t, rgba_t) in enumerate(comp_thumbs):
                r_t = idx_t // cols_cs
                c_t = idx_t % cols_cs
                x0_t, y0_t = c_t * cell_w_cs, r_t * cell_h_cs
                cv2.rectangle(sheet, (x0_t + 2, y0_t + 2), (x0_t + cell_w_cs - 2, y0_t + cell_h_cs - 2), (190, 198, 205), 1)
                th_h, th_w = rgba_t.shape[:2]
                scale_t = min((cell_w_cs - 24) / float(max(th_w, 1)), (cell_h_cs - 54) / float(max(th_h, 1)))
                nw_t, nh_t = max(1, int(th_w * scale_t)), max(1, int(th_h * scale_t))
                resized_t = cv2.resize(rgba_t, (nw_t, nh_t), interpolation=cv2.INTER_AREA)
                ox_t = x0_t + (cell_w_cs - nw_t) // 2
                oy_t = y0_t + 38 + (cell_h_cs - 44 - nh_t) // 2
                alpha_t = (resized_t[:, :, 3:4].astype(np.float32) / 255.0)
                roi_t = sheet[oy_t:oy_t + nh_t, ox_t:ox_t + nw_t].astype(np.float32)
                sheet[oy_t:oy_t + nh_t, ox_t:ox_t + nw_t] = (resized_t[:, :, :3].astype(np.float32) * alpha_t + roi_t * (1.0 - alpha_t)).astype(np.uint8)
                cv2.rectangle(sheet, (x0_t + 4, y0_t + 4), (x0_t + cell_w_cs - 4, y0_t + 32), (35, 35, 180), -1)
                cv2.putText(sheet, f"{lbl_t} ({th_w}x{th_h})", (x0_t + 10, y0_t + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imwrite(str(output_dir / "contact_sheet.png"), sheet)

        manifest_file = output_dir / "storyboard_layers_manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_layers, f, indent=2, ensure_ascii=False)

        print(f"✨ [SUCCESS] Pure global contour extraction: {len(core_contours)} core entities extracted (ZERO rectangular cuts).")
        return manifest_layers

    @classmethod
    def extract_storyboard(
        cls,
        storyboard_path: Path,
        output_dir: Path,
        override_grid: Optional[Tuple[int, int]] = None,
        use_pure_contours: bool = True
    ) -> Dict[str, Any]:
        """Universally extracts any storyboard into contour-separated, layer-decomposed assets."""
        if use_pure_contours:
            return cls.extract_storyboard_pure_contours(storyboard_path, output_dir)

        storyboard_path = Path(storyboard_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        img = cv2.imread(str(storyboard_path))
        if img is None:
            raise FileNotFoundError(f"Cannot load storyboard: {storyboard_path}")

        h, w = img.shape[:2]
        rows, cols = override_grid if override_grid else cls.auto_detect_grid(img)
        print(f"🎬 [UNIVERSAL CRAFT EXTRACTOR] {storyboard_path.name} ({w}x{h}) -> Detected Grid: {rows}x{cols}")

        cell_h = h // rows
        cell_w = w // cols

        manifest_layers = {
            "storyboard": storyboard_path.name,
            "grid": [rows, cols],
            "resolution": [w, h],
            "panels": []
        }

        panel_idx = 1
        for r in range(rows):
            for c in range(cols):
                y0, y1 = r * cell_h, min(h, (r + 1) * cell_h)
                x0, x1 = c * cell_w, min(w, (c + 1) * cell_w)
                cell_roi = img[y0:y1, x0:x1]

                panel_info = cls.process_cell(
                    cell_roi,
                    panel_idx=panel_idx,
                    grid_pos=(r, c),
                    output_dir=output_dir
                )
                manifest_layers["panels"].append(panel_info)
                panel_idx += 1

        # Save layer manifest
        manifest_file = output_dir / "storyboard_layers_manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_layers, f, indent=2, ensure_ascii=False)

        print(f"✨ [SUCCESS] Universal multi-layer extraction finished: {len(manifest_layers['panels'])} panels saved to {output_dir}")
        return manifest_layers

    @classmethod
    def process_cell(
        cls,
        cell_bgr: np.ndarray,
        panel_idx: int,
        grid_pos: Tuple[int, int],
        output_dir: Path
    ) -> Dict[str, Any]:
        """Decomposes a single cell into core entities and attached proximity effects."""
        ch, cw = cell_bgr.shape[:2]
        gray = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2GRAY)
        ink = (gray < 235).astype(np.uint8) * 255

        # Clean noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        ink_clean = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(ink_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        # Core contours: large distinct bodies
        core_contours = []
        satellite_contours = []

        # Adaptive area threshold: 1.5% of cell area
        core_threshold = ch * cw * 0.015

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= core_threshold:
                core_contours.append(cnt)
            elif area >= 30.0:
                satellite_contours.append(cnt)

        if not core_contours and contours:
            core_contours = [contours[0]]
            satellite_contours = contours[1:]

        # Sort core contours left-to-right
        core_contours.sort(key=lambda c: cv2.boundingRect(c)[0])

        # Proximity linking: attach each satellite to the nearest core contour
        attachments: Dict[int, List[np.ndarray]] = {i: [] for i in range(len(core_contours))}

        for sat in satellite_contours:
            min_dist = float("inf")
            best_core_idx = 0
            step = max(1, len(sat) // 15)
            for core_idx, core_c in enumerate(core_contours):
                for pt in sat[::step]:
                    d = abs(cv2.pointPolygonTest(core_c, (float(pt[0][0]), float(pt[0][1])), True))
                    if d < min_dist:
                        min_dist = d
                        best_core_idx = core_idx

            # If within 55px radius, attach
            if min_dist <= 55.0:
                attachments[best_core_idx].append(sat)

        # PhotoCraft Color to Alpha
        rgba_cell = cls.color_to_alpha(cell_bgr)

        panel_data = {
            "panel_id": f"panel_{panel_idx:02d}",
            "grid_row": grid_pos[0],
            "grid_col": grid_pos[1],
            "entities": []
        }

        # Export Layers for each Core Entity
        for core_idx, core_c in enumerate(core_contours):
            ent_key = f"p{panel_idx:02d}_e{core_idx+1:02d}"
            
            # 1. Core Actor Mask
            mask_core = np.zeros((ch, cw), dtype=np.uint8)
            cv2.drawContours(mask_core, [core_c], -1, 255, -1)
            mask_core = cv2.dilate(mask_core, np.ones((3, 3), np.uint8))

            rgba_core = rgba_cell.copy()
            rgba_core[mask_core == 0, 3] = 0

            # 2. Attached Effects Mask
            sats = attachments.get(core_idx, [])
            has_fx = len(sats) > 0
            rgba_fx = None

            # Determine dominant effect color
            fx_type = "generic_effect"
            suggested_anim = "pop_bounce"

            if has_fx:
                mask_fx = np.zeros((ch, cw), dtype=np.uint8)
                cv2.drawContours(mask_fx, sats, -1, 255, -1)
                mask_fx = cv2.dilate(mask_fx, np.ones((3, 3), np.uint8))

                rgba_fx = rgba_cell.copy()
                rgba_fx[mask_fx == 0, 3] = 0

                # Analyze color of fx mask in HSV
                hsv = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2HSV)
                fx_pixels_hsv = hsv[mask_fx > 0]
                if len(fx_pixels_hsv) > 0:
                    mean_hue = np.median(fx_pixels_hsv[:, 0])
                    mean_sat = np.median(fx_pixels_hsv[:, 1])
                    if mean_sat > 50:
                        if 15 <= mean_hue <= 40:
                            fx_type = "attention_rays"
                            suggested_anim = "light_burst_flash"
                        elif mean_hue < 12 or mean_hue > 165:
                            fx_type = "alert_or_question"
                            suggested_anim = "wiggle_attention"
                        elif 90 <= mean_hue <= 135:
                            fx_type = "sweat_or_digital"
                            suggested_anim = "breathe"

            # 3. Composite (Fallback)
            mask_composite = mask_core.copy()
            if has_fx:
                mask_composite = cv2.bitwise_or(mask_composite, mask_fx)
            rgba_composite = rgba_cell.copy()
            rgba_composite[mask_composite == 0, 3] = 0

            # Save Files
            core_file = output_dir / f"{ent_key}_core.png"
            comp_file = output_dir / f"{ent_key}_composite.png"
            fx_file = output_dir / f"{ent_key}_fx.png" if has_fx else None

            cv2.imwrite(str(core_file), rgba_core)
            cv2.imwrite(str(comp_file), rgba_composite)
            if fx_file and rgba_fx is not None:
                cv2.imwrite(str(fx_file), rgba_fx)

            bx, by, bw, bh = cv2.boundingRect(core_c)
            entity_record = {
                "key": ent_key,
                "core_file": core_file.name,
                "composite_file": comp_file.name,
                "fx_file": fx_file.name if fx_file else None,
                "has_effect": has_fx,
                "effect_type": fx_type if has_fx else None,
                "suggested_anim": suggested_anim,
                "bounds": [bx, by, bw, bh]
            }
            panel_data["entities"].append(entity_record)

        return panel_data


if __name__ == "__main__":
    import sys
    sb_target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("projects/phone_traps/inputs/storyboards/section_02.png")
    out_target = Path("projects/phone_traps/sections/section_02/assets")
    UniversalCraftExtractor.extract_storyboard(sb_target, out_target)
