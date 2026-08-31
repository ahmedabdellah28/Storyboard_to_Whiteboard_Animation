import os
import sys
import json
import cv2
import numpy as np
from pathlib import Path

# Add kivy directory to path
kivy_dir = Path(__file__).resolve().parent.parent / "kivy"
sys.path.insert(0, str(kivy_dir))

# pyrefly: ignore [missing-import]
from engine.core.scene import SceneConfig   
# pyrefly: ignore [missing-import]
from engine.core.project import Project, StructureType
# pyrefly: ignore [missing-import]
from engine.processing.image_processor import ImageProcessor
# pyrefly: ignore [missing-import]
from engine.processing.panel_detector import PanelDetector
# pyrefly: ignore [missing-import]
from sketchApi import render_concentric_orbital_whiteboard

test_images_dir = Path(__file__).resolve().parent.parent / "test_images"

def capture_baseline():
    baseline_data = {}
    
    # 1. Structural & Entity Extraction on test images
    images = sorted(list(test_images_dir.glob("*.jpg")) + list(test_images_dir.glob("*.png")))
    print(f"Found {len(images)} test images in {test_images_dir}")
    
    for img_path in images:
        name = img_path.name
        print(f"\n--- Processing Image: {name} ---")
        bytes_data = np.fromfile(str(img_path), dtype=np.uint8)
        img_bgr = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)
        if img_bgr is None:
            print(f"Error loading {img_path}")
            continue
            
        h, w = img_bgr.shape[:2]
        
        # Panel Detection
        detected_project = PanelDetector.detect(img_bgr)
        panels_info = []
        for p in detected_project.panels:
            panels_info.append({
                "id": p.id,
                "bbox": list(p.bbox),
                "interior_bbox": list(p.interior_bbox),
                "row": p.row,
                "col": p.column,
                "is_empty": p.is_empty,
                "content_score": round(float(p.content_score), 4)
            })
            
        # Full Image Processing
        cfg = SceneConfig(width=1280, height=720, fps=30, drawing_speed=1.5)
        project = ImageProcessor.process(img_bgr, cfg)
        
        objects_info = []
        for sc in project.scenes:
            for obj in sc.objects:
                if not obj.is_frame:
                    objects_info.append({
                        "name": obj.name,
                        "panel_id": getattr(obj, "panel_id", 1),
                        "bbox": list(obj.bbox),
                        "global_bbox": list(obj.global_bbox) if obj.global_bbox else list(obj.bbox),
                        "width": int(obj.width),
                        "height": int(obj.height),
                        "area": int(obj.area)
                    })
                    
        baseline_data[name] = {
            "image_dimensions": [w, h],
            "detected_structure_type": detected_project.structure_type.value,
            "detected_confidence": round(float(detected_project.confidence), 4),
            "panel_count": len(detected_project.panels),
            "panels": panels_info,
            "processed_scenes_count": len(project.scenes),
            "total_objects_count": len(objects_info),
            "objects": objects_info
        }
        print(f"  Structure: {detected_project.structure_type.value} | Panels: {len(detected_project.panels)} | Objects: {len(objects_info)}")

    # 2. Concentric 360 Video Render Baseline
    out_video_path = test_images_dir.parent / "tests" / "baseline_render_output.mp4"
    if out_video_path.exists():
        out_video_path.unlink()
        
    print(f"\n--- Generating Baseline 360 Video Render Output ---")
    sample_img_path = test_images_dir / "user_test_1_muscles.jpg"
    sample_img = cv2.imdecode(np.fromfile(str(sample_img_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    
    # Process sample project for custom objects
    cfg = SceneConfig(width=1280, height=720, fps=30, drawing_speed=2.0)
    sample_project = ImageProcessor.process(sample_img, cfg)
    all_sample_objs = []
    for sc in sample_project.scenes:
        for o in sc.objects:
            if not o.is_frame:
                all_sample_objs.append(o)
                
    render_concentric_orbital_whiteboard(
        image_input=sample_img,
        output_path=str(out_video_path),
        fps=30,
        drawing_speed=2.5,
        camera_zoom_scale=1.5,
        element_spacing=24,
        drawing_direction="OUTSIDE_IN",
        ring_step=5,
        brush_radius=8,
        sample_interval=3.0,
        show_hand=True,
        hand_scale=0.75,
        end_hold_seconds=1.0,
        custom_objects=all_sample_objs
    )
    
    # Inspect rendered video
    cap = cv2.VideoCapture(str(out_video_path))
    v_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    v_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    v_fps = float(cap.get(cv2.CAP_PROP_FPS))
    v_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    v_duration = v_frame_count / max(1.0, v_fps)
    
    # Sample checkpoints
    frame_indices = [0, v_frame_count // 4, v_frame_count // 2, (3 * v_frame_count) // 4, max(0, v_frame_count - 1)]
    checkpoints = {}
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            mean_bgr = [round(float(m), 2) for m in np.mean(frame, axis=(0, 1))]
            std_bgr = [round(float(s), 2) for s in np.std(frame, axis=(0, 1))]
            checkpoints[str(idx)] = {
                "mean_bgr": mean_bgr,
                "std_bgr": std_bgr
            }
    cap.release()
    
    video_baseline = {
        "output_resolution": [v_width, v_height],
        "fps": v_fps,
        "total_frames": v_frame_count,
        "duration_seconds": round(v_duration, 2),
        "file_size_bytes": os.path.getsize(str(out_video_path)),
        "checkpoints": checkpoints
    }
    
    baseline_data["_video_render_baseline"] = video_baseline
    print(f"  Render Result: {v_width}x{v_height} @ {v_fps}fps | Frames: {v_frame_count} | Duration: {round(v_duration, 2)}s")
    
    # Save baseline to JSON
    json_path = test_images_dir.parent / "tests" / "golden_baseline_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(baseline_data, f, indent=2)
    print(f"\n[SUCCESS] Golden Baseline saved to: {json_path}")
    return baseline_data

if __name__ == "__main__":
    capture_baseline()
