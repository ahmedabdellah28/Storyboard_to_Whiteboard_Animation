"""
Animation Engine V3 Architecture Verification Suite.

Validates all 10 architectural acceptance criteria:
TEST 01: Single image without frame -> SINGLE_SCENE (0 panels)
TEST 02: Single image with one outer frame -> SINGLE_SCENE / SINGLE_FRAMED_SCENE (0 panels, NOT 4 panels)
TEST 03: Single image with internal drawn lines (floor/horizon) -> SINGLE_SCENE (0 panels)
TEST 04: Single image with 4 visual composition elements -> SINGLE_SCENE (0 panels)
TEST 05: Real 2x2 Storyboard -> STORYBOARD (4 panels)
TEST 06: Real 2x3 Storyboard -> STORYBOARD (6 panels)
TEST 07: Storyboard with an empty panel -> STORYBOARD with empty panel preserved
TEST 08: Dark background artwork -> Background preserved, no artificial white/black holes
TEST 09: Pixel-Exact Preservation (TrueColor, Gradients, Shading, Highlights, Micro-details) -> MAE=0, MSE=0, Coverage=100%
TEST 10: Hand & Pen Animation Layer + Zero Early Reveal (Canvas blank at t=0, no pixel before its draw event)
TEST 11: Real Workspace Images Regression -> Real Storyboards vs Single Scenes
"""
import os
import sys
import glob
import cv2
import numpy as np
import unittest

sys.path.insert(0, os.path.abspath("kivy"))

from engine.core.scene import SceneConfig, Scene, SceneObject
from engine.core.stroke import Stroke, StrokeType
from engine.core.region import ColorRegion, FillMode
from engine.core.timeline import Timeline, StrokeEvent, FillEvent, CameraShot
from engine.core.project import Project, StructureType
from engine.processing.image_processor import ImageProcessor
from engine.processing.color_processor import ColorProcessor
from engine.processing.edge_extractor import EdgeExtractor
from engine.processing.stroke_classifier import StrokeClassifier
from engine.processing.region_extractor import RegionExtractor
from engine.processing.panel_detector import PanelDetector, StoryboardConfidenceAnalyzer
from engine.planning.object_grouping import MajorObjectGrouper
from engine.planning.sequence_planner import SequencePlanner
from engine.planning.shot_planner import ShotPlanner
from engine.planning.storyboard_planner import StoryboardPlanner
from engine.camera.camera import Camera
from engine.camera.camera_animator import CameraAnimator
from engine.render.renderer import Renderer
from engine.render.hand_overlay import HandOverlay


class TestAnimationEngineV3Architecture(unittest.TestCase):
    def setUp(self):
        self.config = SceneConfig(width=640, height=360, fps=15, color_palette_size=16, show_hand=True)

    def _render_and_get_fidelity(self, img_bgr: np.ndarray, config: SceneConfig):
        """Helper to render raw final frame and compute fidelity metrics."""
        h, w = img_bgr.shape[:2]
        quantized_bgr, palette, bg_color = ColorProcessor.quantize(img_bgr, config)
        raw_strokes = EdgeExtractor.extract(img_bgr, config)
        classified_strokes = StrokeClassifier.classify(raw_strokes, img_bgr, quantized_bgr, config)
        regions = RegionExtractor.extract(quantized_bgr, palette, bg_color, config)
        major_objects = MajorObjectGrouper.group_into_major_objects(classified_strokes, regions, w, h, config)

        scene = Scene(
            config=config,
            objects=major_objects,
            background_color=bg_color,
            source_image=img_bgr,
            canvas_width=w,
            canvas_height=h
        )

        ordered_objects, timeline = SequencePlanner.plan_sequence_and_timeline(scene, major_objects, config)
        camera = Camera(w, h, w, h)
        animator = CameraAnimator()
        shots = [CameraShot(shot_name="STATIC", target_center=np.array([w/2, h/2]), zoom=1.0, start_time=0.0, end_time=timeline.duration)]

        renderer = Renderer(scene, timeline, camera, shots, animator)
        raw_final = renderer.render_raw_final_frame()
        metrics = Renderer.verify_fidelity(img_bgr, raw_final)
        return metrics, renderer, timeline

    # ═══════════════════════════════════════════
    #  TEST 01: Single Unframed Image
    # ═══════════════════════════════════════════
    def test_01_single_unframed_image(self):
        """Single image with no outer border must be classified as SINGLE_SCENE (0 panels)."""
        img = np.full((360, 640, 3), 245, dtype=np.uint8)
        # Character
        cv2.circle(img, (240, 180), 50, (40, 110, 210), -1)
        cv2.circle(img, (240, 180), 50, (20, 20, 20), 2)
        # Floating Object
        cv2.rectangle(img, (440, 140), (520, 220), (50, 180, 80), -1)

        project = PanelDetector.detect(img)
        self.assertTrue(project.is_single_scene, f"Expected SINGLE_SCENE, got {project.structure_type}")
        self.assertEqual(len(project.panels), 0, "Single scene must have 0 panels")

    # ═══════════════════════════════════════════
    #  TEST 02: Single Framed Image (1 Outer Box)
    # ═══════════════════════════════════════════
    def test_02_single_framed_image(self):
        """Single image inside 1 large bounding frame must NOT be split into 4 panels."""
        img = np.full((720, 1280, 3), 245, dtype=np.uint8)
        # Large outer bounding box
        cv2.rectangle(img, (40, 40), (1240, 680), (20, 20, 20), 4)
        # Inner character and padlock
        cv2.circle(img, (400, 360), 100, (40, 110, 210), -1)
        cv2.circle(img, (880, 360), 60, (220, 180, 40), -1)

        project = PanelDetector.detect(img)
        self.assertTrue(project.is_single_scene, f"Single framed image must be SINGLE_SCENE, got {project.structure_type}")
        self.assertEqual(len(project.panels), 0, "Single framed image must have 0 panels")

    # ═══════════════════════════════════════════
    #  TEST 03: Single Image with Internal Lines
    # ═══════════════════════════════════════════
    def test_03_single_image_with_internal_lines(self):
        """Internal drawing lines (table/floor/horizon) must not trigger storyboard detection."""
        img = np.full((360, 640, 3), 250, dtype=np.uint8)
        # Horizontal floor line
        cv2.line(img, (20, 260), (620, 260), (30, 30, 30), 3)
        # Character standing on floor
        cv2.circle(img, (320, 180), 60, (50, 100, 220), -1)

        project = PanelDetector.detect(img)
        self.assertTrue(project.is_single_scene)
        self.assertEqual(len(project.panels), 0)

    # ═══════════════════════════════════════════
    #  TEST 04: Single Image with 4 Composition Areas
    # ═══════════════════════════════════════════
    def test_04_single_image_with_4_composition_areas(self):
        """4 distinct elements in corners of one scene must remain ONE single scene."""
        img = np.full((720, 1280, 3), 255, dtype=np.uint8)
        # Top-left element
        cv2.circle(img, (300, 200), 50, (200, 80, 40), -1)
        # Top-right element
        cv2.circle(img, (980, 200), 50, (40, 200, 80), -1)
        # Bottom-left element
        cv2.circle(img, (300, 520), 50, (40, 80, 200), -1)
        # Bottom-right element
        cv2.circle(img, (980, 520), 50, (200, 200, 40), -1)
        # Central connecting banner/drawing
        cv2.line(img, (300, 200), (980, 520), (20, 20, 20), 3)

        project = PanelDetector.detect(img)
        self.assertTrue(project.is_single_scene)
        self.assertEqual(len(project.panels), 0)

    # ═══════════════════════════════════════════
    #  TEST 05: Real 2x2 Storyboard
    # ═══════════════════════════════════════════
    def test_05_real_storyboard_2x2(self):
        """Real 2x2 Storyboard with 4 distinct panels must be detected as STORYBOARD (4 panels)."""
        img = np.full((720, 1280, 3), 255, dtype=np.uint8)
        for r in range(2):
            for c in range(2):
                px = 60 + c * 580
                py = 50 + r * 320
                cv2.rectangle(img, (px, py), (px + 540, py + 280), (20, 20, 20), 4)
                cv2.circle(img, (px + 270, py + 140), 40, (50 + c * 80, 80 + r * 80, 200), -1)

        project = PanelDetector.detect(img)
        self.assertTrue(project.is_storyboard, f"Expected STORYBOARD, got {project.structure_type}")
        self.assertEqual(len(project.panels), 4, f"Expected 4 panels, got {len(project.panels)}")

    # ═══════════════════════════════════════════
    #  TEST 06: Real 2x3 Storyboard
    # ═══════════════════════════════════════════
    def test_06_real_storyboard_2x3(self):
        """Real 2x3 Storyboard with 6 distinct panels must be detected as STORYBOARD (6 panels)."""
        img = np.full((720, 1280, 3), 255, dtype=np.uint8)
        for r in range(2):
            for c in range(3):
                px = 40 + c * 400
                py = 40 + r * 330
                cv2.rectangle(img, (px, py), (px + 370, py + 290), (20, 20, 20), 4)
                cv2.circle(img, (px + 185, py + 145), 35, (40 + c * 40, 60 + r * 60, 180), -1)

        project = PanelDetector.detect(img)
        self.assertTrue(project.is_storyboard, f"Expected STORYBOARD, got {project.structure_type}")
        self.assertEqual(len(project.panels), 6, f"Expected 6 panels, got {len(project.panels)}")

    # ═══════════════════════════════════════════
    #  TEST 07: Storyboard with an Empty Panel
    # ═══════════════════════════════════════════
    def test_07_storyboard_with_empty_panel(self):
        """Storyboard where 1 panel is empty must preserve all panels and flag is_empty."""
        img = np.full((720, 1280, 3), 255, dtype=np.uint8)
        for r in range(2):
            for c in range(2):
                px = 60 + c * 580
                py = 50 + r * 320
                cv2.rectangle(img, (px, py), (px + 540, py + 280), (20, 20, 20), 4)
                # Leave bottom-right panel empty
                if not (r == 1 and c == 1):
                    cv2.circle(img, (px + 270, py + 140), 40, (50 + c * 80, 80 + r * 80, 200), -1)

        project = PanelDetector.detect(img)
        self.assertTrue(project.is_storyboard)
        self.assertEqual(len(project.panels), 4)
        empty_panels = [p for p in project.panels if p.is_empty]
        self.assertGreaterEqual(len(empty_panels), 1, "Expected at least 1 empty panel detected")

    # ═══════════════════════════════════════════
    #  TEST 08: Dark Background Artwork Preservation
    # ═══════════════════════════════════════════
    def test_08_dark_background_preservation(self):
        """Dark theme artwork background is preserved, not forced to white or altered."""
        img = np.full((360, 640, 3), (25, 20, 20), dtype=np.uint8)
        cv2.circle(img, (320, 180), 45, (220, 200, 80), -1)

        metrics, _, _ = self._render_and_get_fidelity(img, self.config)
        self.assertEqual(metrics["missing_pixels"], 0)
        self.assertEqual(metrics["mae"], 0.0)

    # ═══════════════════════════════════════════
    #  TEST 09: Pixel-Exact Preservation (Zero Loss)
    # ═══════════════════════════════════════════
    def test_09_pixel_exact_fidelity_and_zero_loss(self):
        """Final RAW frame MUST equal source image exactly with MAE=0, MSE=0, Coverage=100%."""
        img = np.zeros((360, 640, 3), dtype=np.uint8)
        # Radial gradient
        cx, cy = 320, 180
        for y in range(360):
            for x in range(640):
                d = np.sqrt((x - cx)**2 + (y - cy)**2)
                if d < 120:
                    glow = max(0.0, 1.0 - d / 120.0)
                    img[y, x] = (int(50 * glow), int(220 * glow), int(255 * glow))

        # Anti-aliased circle and micro-text
        cv2.circle(img, (cx, cy), 35, (200, 255, 100), -1, cv2.LINE_AA)
        cv2.putText(img, "TRUECOLOR", (220, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2, cv2.LINE_AA)

        metrics, _, _ = self._render_and_get_fidelity(img, self.config)
        self.assertEqual(metrics["missing_pixels"], 0)
        self.assertEqual(metrics["mae"], 0.0)
        self.assertEqual(metrics["mse"], 0.0)
        self.assertEqual(metrics["coverage_pct"], 100.0)

    # ═══════════════════════════════════════════
    #  TEST 10: Hand & Pen Animation + Zero Early Reveal
    # ═══════════════════════════════════════════
    def test_10_hand_overlay_and_no_early_reveal(self):
        """At t=0, canvas must be 100% blank; strokes reveal only when drawn by hand."""
        img = np.full((360, 640, 3), 255, dtype=np.uint8)
        cv2.circle(img, (160, 180), 40, (20, 80, 220), -1)
        cv2.circle(img, (480, 180), 40, (220, 80, 20), -1)

        _, renderer, timeline = self._render_and_get_fidelity(img, self.config)
        
        # Frame at t=0
        raw_t0 = renderer.render_raw_frame_at_time(0.0)
        bg = renderer.bg_color
        self.assertTrue(np.all(raw_t0 == bg), "Initial canvas at t=0 must be 100% blank background")

        # Future stroke check
        if len(timeline.stroke_events) >= 2:
            second_event = timeline.stroke_events[-1]
            t_before_second = max(0.0, second_event.start_time - 0.05)
            raw_mid = renderer.render_raw_frame_at_time(t_before_second)
            s2_pts = second_event.stroke.points.astype(np.int32)
            mid_pt = s2_pts[len(s2_pts)//2]
            pixel_at_s2 = raw_mid[mid_pt[1], mid_pt[0]]
            self.assertTrue(np.array_equal(pixel_at_s2, bg), "Stroke must not be revealed before its start time")

    # ═══════════════════════════════════════════
    #  TEST 11: Real Workspace Images Regression
    # ═══════════════════════════════════════════
    def test_11_real_workspace_images_regression(self):
        """Verifies real workspace images match their exact expected classifications."""
        image_expectations = {
            "Man_interacting_with_magical": "SINGLE_SCENE",
            "Man_looking_at_floating_padlock": "SINGLE_SCENE",
            "Man_unlocking_glowing_padlock": "STORYBOARD",
            "Storyboard_showing_Zaid": "STORYBOARD"
        }

        found_tested = 0
        for pattern, expected_type in image_expectations.items():
            matches = glob.glob(f"*{pattern}*.jpeg") + glob.glob(f"*{pattern}*.jpg")
            if not matches:
                continue

            img_path = matches[0]
            bytes_data = np.fromfile(img_path, dtype=np.uint8)
            img = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)
            if img is None:
                continue

            norm = ImageProcessor.resize_and_pad(img, 1280, 720)
            project = PanelDetector.detect(norm)

            if expected_type == "SINGLE_SCENE":
                self.assertTrue(project.is_single_scene, f"Image {os.path.basename(img_path)} must be SINGLE_SCENE, got {project.structure_type}")
                self.assertEqual(len(project.panels), 0, f"Image {os.path.basename(img_path)} must have 0 panels")
            else:
                self.assertTrue(project.is_storyboard, f"Image {os.path.basename(img_path)} must be STORYBOARD, got {project.structure_type}")
                self.assertGreaterEqual(len(project.panels), 4, f"Image {os.path.basename(img_path)} must have >= 4 panels")

            found_tested += 1

        self.assertGreaterEqual(found_tested, 2, "Must have tested at least 2 real project images")


if __name__ == "__main__":
    unittest.main()
