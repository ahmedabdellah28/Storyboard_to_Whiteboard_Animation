import os
import cv2
import numpy as np
import logging
from typing import Optional
from ..core.scene import Scene, SceneConfig
from ..core.stroke import StrokeType
from ..core.project import Project, StructureType
from ..processing.image_processor import ImageProcessor
from ..processing.edge_extractor import EdgeExtractor
from ..processing.stroke_classifier import StrokeClassifier
from ..processing.color_processor import ColorProcessor
from ..processing.region_extractor import RegionExtractor
from ..planning.object_grouping import MajorObjectGrouper
from ..planning.sequence_planner import SequencePlanner
from ..planning.shot_planner import ShotPlanner

logger = logging.getLogger(__name__)


class DebugPreview:
    """
    V3 Debug Visualization.
    Generates debug images showing every stage of the pipeline
    including storyboard/panel detection overlay.
    """

    # Debug colors
    COLOR_PANEL_BBOX = (255, 165, 0)       # Orange — panel bounding box
    COLOR_PANEL_INTERIOR = (0, 255, 128)   # Green — interior content area
    COLOR_OBJECT_BBOX = (0, 165, 255)      # Light blue — object bounding box
    COLOR_GRID_LINE = (255, 0, 255)        # Magenta — detected grid lines
    COLOR_RESIDUAL = (0, 0, 255)           # Red — residual mask

    @staticmethod
    def save_pipeline_stages(image_path: str, config: SceneConfig, output_dir: str = "debug_output") -> Scene:
        """
        Executes the entire pipeline and saves visual debug snapshots for each stage:
        - 01_original
        - 02_resized_padded
        - 03_storyboard_detection
        - 04_panel_bboxes
        - 05_color_quantized (analysis reference only)
        - 06_edges_raw
        - 07_strokes_classified
        - 08_color_regions
        - 09_major_objects_detected
        - 10_camera_shots_storyboard
        - 11_residual_mask
        - 12_full_composition_preview
        """
        os.makedirs(output_dir, exist_ok=True)
        if isinstance(image_path, np.ndarray):
            img_bgr = image_path
        else:
            bytes_data = np.fromfile(str(image_path), dtype=np.uint8)
            img_bgr = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)

        if img_bgr is None:
            raise FileNotFoundError(f"Cannot load image at {image_path}")

        # 01. Original
        cv2.imwrite(os.path.join(output_dir, "01_original.png"), img_bgr)

        # 02. Resized & padded
        resized_bgr = ImageProcessor.resize_and_pad(img_bgr, config.width, config.height)
        cv2.imwrite(os.path.join(output_dir, "02_resized_padded.png"), resized_bgr)

        # 03. Storyboard Detection Debug
        project = ImageProcessor.process(img_bgr, config)
        storyboard_debug = resized_bgr.copy()

        if project.structure_type == StructureType.STORYBOARD:
            # Draw panel bounding boxes and interior regions
            for panel in project.panels:
                px, py, pw, ph = panel.bbox
                ix, iy, iw, ih = panel.interior_bbox

                # Panel outer bbox (orange)
                cv2.rectangle(storyboard_debug, (px, py), (px + pw, py + ph),
                              DebugPreview.COLOR_PANEL_BBOX, 3)

                # Interior bbox (green dashed-effect)
                cv2.rectangle(storyboard_debug, (ix, iy), (ix + iw, iy + ih),
                              DebugPreview.COLOR_PANEL_INTERIOR, 2)

                # Panel label
                label = f"P{panel.id} R{panel.row}C{panel.column}"
                if panel.is_empty:
                    label += " [EMPTY]"
                cv2.putText(storyboard_debug, label, (px + 8, py + 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, DebugPreview.COLOR_PANEL_BBOX, 2)

                # Metrics
                metrics = f"ED:{panel.edge_density:.3f} E:{panel.entropy:.1f}"
                cv2.putText(storyboard_debug, metrics, (px + 8, py + 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            # Structure info
            rows = max(p.row for p in project.panels) + 1 if project.panels else 0
            cols = max(p.column for p in project.panels) + 1 if project.panels else 0
            info = f"STORYBOARD: {len(project.panels)} panels ({rows}x{cols}) conf={project.confidence:.2f}"
            cv2.putText(storyboard_debug, info, (10, resized_bgr.shape[0] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(storyboard_debug, "SINGLE_SCENE", (10, resized_bgr.shape[0] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)

        cv2.imwrite(os.path.join(output_dir, "03_storyboard_detection.png"), storyboard_debug)

        # 04. Per-panel object detection debug
        if project.structure_type == StructureType.STORYBOARD:
            panel_debug = resized_bgr.copy()
            box_colors = [
                (0, 165, 255), (0, 220, 50), (255, 100, 50),
                (200, 0, 200), (0, 215, 255), (128, 128, 255)
            ]
            for scene in project.scenes:
                if scene.is_empty:
                    continue
                for obj_idx, obj in enumerate(scene.objects):
                    if obj.is_frame:
                        continue
                    if obj.global_bbox:
                        gx, gy, gw, gh = obj.global_bbox
                    else:
                        gx, gy, gw, gh = obj.bbox
                    color = box_colors[obj_idx % len(box_colors)]
                    cv2.rectangle(panel_debug, (gx, gy), (gx + gw, gy + gh), color, 2)
                    cv2.putText(panel_debug, obj.name, (gx + 4, max(15, gy - 5)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
            cv2.imwrite(os.path.join(output_dir, "04_panel_objects.png"), panel_debug)

        # Use first scene for single-scene debug stages
        if project.scenes:
            first_scene = project.scenes[0]
            scene_img = first_scene.source_image
            if scene_img is None:
                scene_img = resized_bgr
        else:
            scene_img = resized_bgr
            first_scene = None

        h_s, w_s = scene_img.shape[:2]

        # 05. Color quantized (analysis reference)
        quantized_bgr, palette, bg_color = ColorProcessor.quantize(scene_img, config)
        cv2.imwrite(os.path.join(output_dir, "05_color_quantized_analysis.png"), quantized_bgr)

        # 06. Raw Edges
        raw_strokes = EdgeExtractor.extract(scene_img, config)
        edge_canvas = np.full_like(scene_img, 255)
        for s in raw_strokes:
            pts = s.points.astype(np.int32)
            cv2.polylines(edge_canvas, [pts], s.is_closed, (30, 30, 30), 1, cv2.LINE_AA)
        cv2.imwrite(os.path.join(output_dir, "06_edges_raw.png"), edge_canvas)

        # 07. Strokes Classified
        classified_strokes = StrokeClassifier.classify(raw_strokes, scene_img, quantized_bgr, config)
        classified_canvas = np.full_like(scene_img, 255)
        type_colors = {
            StrokeType.OUTER_OUTLINE: (0, 0, 220),       # Red
            StrokeType.INTERNAL_DETAIL: (200, 50, 20),   # Blue/Navy
            StrokeType.COLOR_BOUNDARY: (30, 180, 40),    # Green
            StrokeType.MICRO_DETAIL: (140, 140, 140),    # Gray
        }
        for s in classified_strokes:
            c = type_colors.get(s.stroke_type, (0, 0, 0))
            pts = s.points.astype(np.int32)
            w = max(1, int(round(s.width)))
            cv2.polylines(classified_canvas, [pts], s.is_closed, c, w, cv2.LINE_AA)
        cv2.imwrite(os.path.join(output_dir, "07_strokes_classified.png"), classified_canvas)

        # 08. Color Regions
        regions = RegionExtractor.extract(quantized_bgr, palette, bg_color, config)
        regions_canvas = np.full_like(scene_img, 255)
        for r in regions:
            regions_canvas[r.mask > 0] = r.color
        cv2.imwrite(os.path.join(output_dir, "08_color_regions.png"), regions_canvas)

        # 09. Major Objects Detected
        if first_scene and first_scene.objects:
            objects_canvas = scene_img.copy()
            box_colors = [
                (0, 165, 255), (0, 220, 50), (255, 100, 50),
                (200, 0, 200), (0, 215, 255)
            ]
            for idx, obj in enumerate([o for o in first_scene.objects if not o.is_frame]):
                bx, by, bw, bh = obj.bbox
                color = box_colors[idx % len(box_colors)]
                cv2.rectangle(objects_canvas, (bx, by), (bx + bw, by + bh), color, 3)
                label = f"#{idx+1}: {obj.name}"
                cv2.putText(objects_canvas, label, (bx + 8, max(30, by - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
            cv2.imwrite(os.path.join(output_dir, "09_major_objects_detected.png"), objects_canvas)

        # 10. Residual mask visualization
        residual_canvas = scene_img.copy()
        # Show what the residual fallback would cover
        covered = np.zeros((h_s, w_s), dtype=np.uint8)
        for r in regions:
            if r.cropped_mask is not None:
                bx, by, bw, bh = r.bbox
                x2 = min(w_s, bx + bw)
                y2 = min(h_s, by + bh)
                if x2 > bx and y2 > by:
                    cm = r.cropped_mask[:(y2 - by), :(x2 - bx)]
                    covered[by:y2, bx:x2][cm > 0] = 255
        for s in classified_strokes:
            if len(s.points) >= 2:
                pts = s.points.astype(np.int32)
                sw = max(1, int(round(s.width)))
                cv2.polylines(covered, [pts], s.is_closed, 255, sw)
        residual = cv2.bitwise_not(covered)

        # Overlay residual in red tint
        residual_overlay = residual_canvas.copy()
        residual_overlay[residual > 0] = (0, 0, 200)
        residual_canvas = cv2.addWeighted(residual_canvas, 0.6, residual_overlay, 0.4, 0)
        residual_pct = float(cv2.countNonZero(residual)) / max(1, h_s * w_s) * 100
        cv2.putText(residual_canvas, f"Residual: {residual_pct:.1f}% of pixels",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imwrite(os.path.join(output_dir, "10_residual_mask.png"), residual_canvas)

        # 11. Full Composition (source-based, not quantized)
        comp_canvas = scene_img.copy()
        cv2.imwrite(os.path.join(output_dir, "11_full_composition_source.png"), comp_canvas)

        logger.info(f"[DEBUG] Saved {11 if project.structure_type != StructureType.STORYBOARD else 12} debug images to {output_dir}")
        return first_scene
