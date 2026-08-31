import os
import sys
import cv2
import numpy as np
import json

# Add kivy to path
sys.path.insert(0, os.path.abspath("kivy"))

from engine.core.scene import SceneConfig, Scene
from engine.core.timeline import CameraShot
from engine.processing.image_processor import ImageProcessor
from engine.processing.color_processor import ColorProcessor
from engine.processing.edge_extractor import EdgeExtractor
from engine.processing.stroke_classifier import StrokeClassifier
from engine.processing.region_extractor import RegionExtractor
from engine.planning.object_grouping import MajorObjectGrouper
from engine.planning.sequence_planner import SequencePlanner
from engine.planning.shot_planner import ShotPlanner
from engine.camera.camera import Camera
from engine.camera.camera_animator import CameraAnimator
from engine.render.renderer import Renderer

def run_forensic_analysis(image_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    
    # 00. Source Image (Immutable Source of Truth)
    try:
        bytes_data = np.fromfile(str(image_path), dtype=np.uint8)
        img_bgr = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)
    except Exception:
        img_bgr = None
        
    if img_bgr is None:
        print(f"Failed to load image: {image_path}")
        return
        
    src_h, src_w, src_c = img_bgr.shape
    cv2.imwrite(os.path.join(output_dir, "00_original.png"), img_bgr)
    
    config = SceneConfig(width=1280, height=720, fps=30, detail_level="MEDIUM", color_palette_size=16)
    
    # 01. Resized & Padded (Analysis Plane)
    norm_bgr = ImageProcessor.resize_and_pad(img_bgr, config.width, config.height)
    cv2.imwrite(os.path.join(output_dir, "01_resized_padded.png"), norm_bgr)
    norm_h, norm_w = norm_bgr.shape[:2]
    
    # 02. Color Quantization Stage
    quantized_bgr, palette, bg_color = ColorProcessor.quantize(norm_bgr, config)
    cv2.imwrite(os.path.join(output_dir, "02_quantized.png"), quantized_bgr)
    
    # Calculate color quantization loss
    quant_delta = np.abs(norm_bgr.astype(np.float32) - quantized_bgr.astype(np.float32))
    quant_mae = float(np.mean(quant_delta))
    quant_max = float(np.max(quant_delta))
    unique_src_colors = len(np.unique(norm_bgr.reshape(-1, 3), axis=0))
    unique_quant_colors = len(np.unique(quantized_bgr.reshape(-1, 3), axis=0))
    
    # 03. Edge Extraction Stage
    raw_strokes = EdgeExtractor.extract(norm_bgr, config)
    raw_edge_mask = np.zeros((norm_h, norm_w), dtype=np.uint8)
    for s in raw_strokes:
        pts = s.points.astype(np.int32)
        cv2.polylines(raw_edge_mask, [pts], s.is_closed, 255, 1)
    cv2.imwrite(os.path.join(output_dir, "03_raw_edges.png"), raw_edge_mask)
    
    # 04. Stroke Classification Stage
    classified_strokes = StrokeClassifier.classify(raw_strokes, norm_bgr, quantized_bgr, config)
    classified_edge_mask = np.zeros((norm_h, norm_w), dtype=np.uint8)
    for s in classified_strokes:
        pts = s.points.astype(np.int32)
        cv2.polylines(classified_edge_mask, [pts], s.is_closed, 255, max(1, int(round(s.width))))
    cv2.imwrite(os.path.join(output_dir, "04_classified_edges.png"), classified_edge_mask)
    
    dropped_strokes_count = len(raw_strokes) - len(classified_strokes)
    
    # 05. Region Extraction Stage
    regions = RegionExtractor.extract(quantized_bgr, palette, bg_color, config)
    regions_mask = np.zeros((norm_h, norm_w), dtype=np.uint8)
    for r in regions:
        if r.mask is not None:
            regions_mask = cv2.bitwise_or(regions_mask, r.mask)
    cv2.imwrite(os.path.join(output_dir, "05_regions_union_mask.png"), regions_mask)
    
    # 06. Object Grouping Stage
    major_objects = MajorObjectGrouper.group_into_major_objects(
        classified_strokes, regions, norm_w, norm_h, config
    )
    
    grouped_occupancy = np.zeros((norm_h, norm_w), dtype=np.uint8)
    for obj in major_objects:
        if not obj.is_frame:
            for s in obj.strokes + obj.details:
                pts = s.points.astype(np.int32)
                cv2.polylines(grouped_occupancy, [pts], s.is_closed, 255, 2)
            for f in obj.fills:
                if f.mask is not None:
                    grouped_occupancy = cv2.bitwise_or(grouped_occupancy, f.mask)
    cv2.imwrite(os.path.join(output_dir, "06_grouped_occupancy.png"), grouped_occupancy)
    
    # 07. Full Pipeline Rendered Final Frame using actual Engine Renderer
    scene = Scene(
        config=config,
        objects=major_objects,
        background_color=bg_color,
        source_image=norm_bgr,
        canvas_width=norm_w,
        canvas_height=norm_h
    )
    ordered_objects, timeline = SequencePlanner.plan_sequence_and_timeline(scene, major_objects, config)
    camera = Camera(norm_w, norm_h, norm_w, norm_h)
    animator = CameraAnimator()
    shots = [CameraShot(shot_name="STATIC", target_center=np.array([norm_w/2, norm_h/2]), zoom=1.0, start_time=0.0, end_time=timeline.duration)]
    
    renderer = Renderer(scene, timeline, camera, shots, animator)
    rendered_frame = renderer.render_frame_at_time(timeline.duration + 0.1)
    cv2.imwrite(os.path.join(output_dir, "07_final_rendered_frame.png"), rendered_frame)
    
    # 08. Residual Analysis (Uncovered Source Pixels)
    # Total Union of all drawn pixels
    total_drawn_mask = np.zeros((norm_h, norm_w), dtype=np.uint8)
    total_drawn_mask[regions_mask > 0] = 255
    total_drawn_mask[classified_edge_mask > 0] = 255
    
    uncovered_mask = cv2.bitwise_not(total_drawn_mask)
    
    # Residual Image: Exact source pixels that were NOT covered by any stroke or region
    residual_image = np.full_like(norm_bgr, 255)
    residual_image[uncovered_mask > 0] = norm_bgr[uncovered_mask > 0]
    cv2.imwrite(os.path.join(output_dir, "08_residual_pixels.png"), residual_image)
    cv2.imwrite(os.path.join(output_dir, "08_residual_mask.png"), uncovered_mask)
    
    # Pixel Error Metrics between Resized Source and Final Rendered Frame
    pixel_diff = np.abs(norm_bgr.astype(np.float32) - rendered_frame.astype(np.float32))
    render_mae = float(np.mean(pixel_diff))
    render_mse = float(np.mean(pixel_diff ** 2))
    differing_pixels = int(np.count_nonzero(np.any(pixel_diff > 5.0, axis=2)))
    total_pixels = norm_h * norm_w
    diff_pixel_ratio = (differing_pixels / float(total_pixels)) * 100.0
    coverage_ratio = (cv2.countNonZero(total_drawn_mask) / float(total_pixels)) * 100.0
    
    report = {
        "image_name": os.path.basename(image_path),
        "source_resolution": f"{src_w}x{src_h}",
        "analysis_resolution": f"{norm_w}x{norm_h}",
        "unique_source_colors": unique_src_colors,
        "unique_quantized_colors": unique_quant_colors,
        "quantization_mae": quant_mae,
        "quantization_max_delta": quant_max,
        "detected_bg_color": list(bg_color),
        "raw_strokes_count": len(raw_strokes),
        "classified_strokes_count": len(classified_strokes),
        "dropped_micro_strokes": dropped_strokes_count,
        "extracted_regions_count": len(regions),
        "major_objects_count": len(major_objects),
        "object_names": [o.name for o in major_objects],
        "mask_coverage_percentage": coverage_ratio,
        "uncovered_residual_percentage": 100.0 - coverage_ratio,
        "final_frame_mae": render_mae,
        "final_frame_mse": render_mse,
        "differing_pixels_count": differing_pixels,
        "differing_pixels_percentage": diff_pixel_ratio
    }
    
    with open(os.path.join(output_dir, "metrics_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
        
    print(f"\n========================================================")
    print(f"FORENSIC REPORT: {os.path.basename(image_path)}")
    print(f"========================================================")
    print(f"Unique Colors: Source={unique_src_colors} -> Quantized={unique_quant_colors}")
    print(f"Strokes: Raw={len(raw_strokes)} -> Classified={len(classified_strokes)} (Dropped={dropped_strokes_count})")
    print(f"Regions: {len(regions)}")
    print(f"Major Objects detected: {len(major_objects)} ({[o.name for o in major_objects[:5]]}...)")
    print(f"Mask Coverage: {coverage_ratio:.2f}% | Uncovered Residual: {100.0 - coverage_ratio:.2f}%")
    print(f"Final Frame Pixel MAE: {render_mae:.2f} | MSE: {render_mse:.2f}")
    print(f"Differing Pixels: {differing_pixels} / {total_pixels} ({diff_pixel_ratio:.2f}%)")
    print(f"========================================================\n")

if __name__ == "__main__":
    import glob
    images = glob.glob("*.jpeg") + glob.glob("*.jpg") + glob.glob("*.png")
    for img in sorted(images):
        if "mock" in img or "debug" in img:
            continue
        out_name = os.path.splitext(os.path.basename(img))[0]
        out_dir = os.path.join("debug", "forensic", out_name)
        run_forensic_analysis(img, out_dir)
