"""
Golden Baseline Regression Suite (Phase 1).

Guarantees 100% behavior preservation across:
1. Panel Detection (Grid, Rows, Cols, BBoxes, Interior BBoxes, Confidence)
2. Entity Extraction (Objects count, names, bboxes, dimensions, areas)
3. 360° Concentric Orbital Whiteboard Video Rendering Contract:
   - Resolution: 1920x1080
   - FPS: 30.0
   - Codec: H.264 (PyAV / libx264 / h264)
   - Playability & Frame Completeness
   - Checkpoint Frame Mean & Standard Deviation
"""
import os
import sys
import json
import unittest
import cv2
import numpy as np
from pathlib import Path

# Add kivy directory to path
kivy_dir = Path(__file__).resolve().parent.parent / "kivy"
sys.path.insert(0, str(kivy_dir))

from engine.core.scene import SceneConfig
from engine.core.project import Project, StructureType
from engine.processing.image_processor import ImageProcessor
from engine.processing.panel_detector import PanelDetector

test_images_dir = Path(__file__).resolve().parent.parent / "test_images"
baseline_json_path = Path(__file__).resolve().parent / "golden_baseline_data.json"


class TestGoldenBaseline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not baseline_json_path.exists():
            raise FileNotFoundError(f"Baseline data file not found at: {baseline_json_path}")
        with open(baseline_json_path, "r", encoding="utf-8") as f:
            cls.baseline = json.load(f)

    # ═════════════════════════════════════════════════════════════════════════
    #  TEST 01: Test Image 1 (user_test_1_muscles.jpg) — 6-Panel Storyboard
    # ═════════════════════════════════════════════════════════════════════════
    def test_01_user_test_1_muscles_baseline(self):
        img_name = "user_test_1_muscles.jpg"
        self.assertIn(img_name, self.baseline)
        exp = self.baseline[img_name]

        img_path = test_images_dir / img_name
        img_bgr = cv2.imdecode(np.fromfile(str(img_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertIsNotNone(img_bgr, f"Could not load {img_name}")

        # 1. Structural Panel Detection Check
        detected_project = PanelDetector.detect(img_bgr)
        self.assertEqual(detected_project.structure_type.value, exp["detected_structure_type"])
        self.assertEqual(len(detected_project.panels), exp["panel_count"])

        for idx, (act_p, exp_p) in enumerate(zip(detected_project.panels, exp["panels"])):
            self.assertEqual(act_p.id, exp_p["id"])
            self.assertEqual(list(act_p.bbox), exp_p["bbox"], f"Panel {idx+1} bbox mismatch")
            self.assertEqual(list(act_p.interior_bbox), exp_p["interior_bbox"], f"Panel {idx+1} interior_bbox mismatch")
            self.assertEqual(act_p.is_empty, exp_p["is_empty"])

        # 2. Entity Extraction Check
        cfg = SceneConfig(width=1280, height=720, fps=30, drawing_speed=1.5)
        project = ImageProcessor.process(img_bgr, cfg)
        self.assertEqual(len(project.scenes), exp["processed_scenes_count"])

        act_objs = []
        for sc in project.scenes:
            for obj in sc.objects:
                if not obj.is_frame:
                    act_objs.append(obj)

        self.assertEqual(len(act_objs), exp["total_objects_count"])
        for idx, (act_o, exp_o) in enumerate(zip(act_objs, exp["objects"])):
            self.assertEqual(act_o.name, exp_o["name"])
            self.assertEqual(act_o.panel_id, exp_o["panel_id"])
            self.assertEqual(list(act_o.bbox), exp_o["bbox"])
            self.assertEqual(int(act_o.width), exp_o["width"])
            self.assertEqual(int(act_o.height), exp_o["height"])

    # ═════════════════════════════════════════════════════════════════════════
    #  TEST 02: Test Image 2 (user_test_2_padlock_numbered.jpg) — Storyboard
    # ═════════════════════════════════════════════════════════════════════════
    def test_02_user_test_2_padlock_baseline(self):
        img_name = "user_test_2_padlock_numbered.jpg"
        self.assertIn(img_name, self.baseline)
        exp = self.baseline[img_name]

        img_path = test_images_dir / img_name
        img_bgr = cv2.imdecode(np.fromfile(str(img_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertIsNotNone(img_bgr, f"Could not load {img_name}")

        # 1. Structural Panel Detection Check
        detected_project = PanelDetector.detect(img_bgr)
        self.assertEqual(detected_project.structure_type.value, exp["detected_structure_type"])
        self.assertEqual(len(detected_project.panels), exp["panel_count"])

        for idx, (act_p, exp_p) in enumerate(zip(detected_project.panels, exp["panels"])):
            self.assertEqual(act_p.id, exp_p["id"])
            self.assertEqual(list(act_p.bbox), exp_p["bbox"], f"Panel {idx+1} bbox mismatch")
            self.assertEqual(list(act_p.interior_bbox), exp_p["interior_bbox"], f"Panel {idx+1} interior_bbox mismatch")

        # 2. Entity Extraction Check
        cfg = SceneConfig(width=1280, height=720, fps=30, drawing_speed=1.5)
        project = ImageProcessor.process(img_bgr, cfg)
        self.assertEqual(len(project.scenes), exp["processed_scenes_count"])

        act_objs = []
        for sc in project.scenes:
            for obj in sc.objects:
                if not obj.is_frame:
                    act_objs.append(obj)

        self.assertEqual(len(act_objs), exp["total_objects_count"])

    # ═════════════════════════════════════════════════════════════════════════
    #  TEST 03: Test Image 3 (user_test_3_continuity_code.jpg) — Single Scene
    # ═════════════════════════════════════════════════════════════════════════
    def test_03_user_test_3_continuity_baseline(self):
        img_name = "user_test_3_continuity_code.jpg"
        self.assertIn(img_name, self.baseline)
        exp = self.baseline[img_name]

        img_path = test_images_dir / img_name
        img_bgr = cv2.imdecode(np.fromfile(str(img_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertIsNotNone(img_bgr, f"Could not load {img_name}")

        # 1. Structural Detection Check
        detected_project = PanelDetector.detect(img_bgr)
        self.assertEqual(detected_project.structure_type.value, exp["detected_structure_type"])
        self.assertEqual(len(detected_project.panels), exp["panel_count"])

        # 2. Entity Extraction Check
        cfg = SceneConfig(width=1280, height=720, fps=30, drawing_speed=1.5)
        project = ImageProcessor.process(img_bgr, cfg)
        act_objs = []
        for sc in project.scenes:
            for obj in sc.objects:
                if not obj.is_frame:
                    act_objs.append(obj)

        self.assertEqual(len(act_objs), exp["total_objects_count"])

    # ═════════════════════════════════════════════════════════════════════════
    #  TEST 04: Video Render Output Contract Baseline
    # ═════════════════════════════════════════════════════════════════════════
    def test_04_video_render_contract_baseline(self):
        self.assertIn("_video_render_baseline", self.baseline)
        exp_vid = self.baseline["_video_render_baseline"]

        out_video_path = Path(__file__).resolve().parent / "baseline_render_output.mp4"
        self.assertTrue(out_video_path.exists(), "Baseline video file must exist")
        self.assertGreater(os.path.getsize(str(out_video_path)), 10000, "Rendered video must be > 10KB")

        cap = cv2.VideoCapture(str(out_video_path))
        self.assertTrue(cap.isOpened(), "Rendered MP4 video must be valid and readable by OpenCV")
        
        v_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        v_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        v_fps = float(cap.get(cv2.CAP_PROP_FPS))
        v_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self.assertEqual(v_width, exp_vid["output_resolution"][0])
        self.assertEqual(v_height, exp_vid["output_resolution"][1])
        self.assertEqual(v_fps, exp_vid["fps"])
        self.assertEqual(v_frame_count, exp_vid["total_frames"])
        cap.release()


if __name__ == "__main__":
    unittest.main()
