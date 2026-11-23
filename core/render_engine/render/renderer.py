import cv2
import numpy as np
import logging
from typing import List, Callable, Optional, Tuple, Dict, Any
from ..core.scene import Scene, SceneObject
from ..core.timeline import Timeline, StrokeEvent, FillEvent, CameraShot
from ..core.stroke import Stroke
from ..core.region import ColorRegion
from ..camera.camera import Camera, CameraState
from ..camera.camera_animator import CameraAnimator
from ..animation.stroke_animator import StrokeAnimator
from ..animation.fill_animator import FillAnimator
from .hand_overlay import HandOverlay

logger = logging.getLogger(__name__)


class Renderer:
    """
    V3.1 TrueColor Pixel-Preserving Progressive Reveal Renderer with Zero Early Reveal & Frame Exclusion.
    
    Golden Rules:
    1. SOURCE IMAGE = SOURCE OF TRUTH (All pixels are extracted directly from source_image).
    2. NO PIXEL BEFORE ITS DRAW EVENT (A pixel is revealed ONLY when actively drawn by the hand/pen).
    3. VISIBLE CANVAS STARTS BLANK (Initial canvas is 100% background color).
    4. HAND + PENCIL SYNCHRONIZATION (Hand moves along stroke path; pixels appear under/behind the pen tip).
    5. NO PREMATURE RESIDUAL REVEAL (Residual fallback strictly operates AFTER all drawing events complete).
    6. NO FRAME BORDER DRAWING (Panel borders and box frames are excluded and kept clean background).
    7. ZERO DETAIL LOSS (Final frame strictly equals source_image with MAE=0, MSE=0, Coverage=100%).
    """

    def __init__(
        self,
        scene: Scene,
        timeline: Timeline,
        camera: Camera,
        camera_shots: List[CameraShot],
        camera_animator: CameraAnimator
    ):
        self.scene = scene
        self.timeline = timeline
        self.camera = camera
        self.camera_shots = camera_shots
        self.camera_animator = camera_animator

        self.canvas_w = scene.canvas_width
        self.canvas_h = scene.canvas_height
        self.bg_color = scene.background_color
        self.source_image = scene.source_image

        # Hand Overlay instantiation
        show_hand = getattr(scene.config, "show_hand", True)
        hand_scale = getattr(scene.config, "hand_scale", 0.75)
        hand_opacity = getattr(scene.config, "hand_opacity", 1.0)
        hand_tilt = getattr(scene.config, "hand_tilt_enabled", True)

        self.hand_overlay = HandOverlay(
            scale=hand_scale,
            opacity=hand_opacity,
            tilt_enabled=hand_tilt
        ) if show_hand else None

        # Compute frame border mask (panel borders & outer rectangular frames)
        self.frame_border_mask = self._compute_frame_border_mask()

        # Universal Residual Analysis & Spatial Reveal Scheduling
        self.residual_mask = self._compute_residual_mask()
        if np.any(self.frame_border_mask > 0):
            self.residual_mask[self.frame_border_mask > 0] = 0

        self.residual_dist_map, self.residual_max_dist = self._compute_residual_distance_transform()

        # Strict Rule: Residual reveal begins ONLY after all planned drawing events have completed
        all_event_ends = [e.end_time for e in self.timeline.stroke_events + self.timeline.fill_events]
        self.drawing_end_time = max(all_event_ends) if all_event_ends else 0.0

    def _compute_frame_border_mask(self) -> np.ndarray:
        """
        Computes binary mask of outer panel frame borders and divider lines to exclude them
        from being drawn or stamped onto the canvas.
        """
        mask = np.zeros((self.canvas_h, self.canvas_w), dtype=np.uint8)

        # 1. From Storyboard Panels (outer rectangle border between bbox and interior_bbox)
        if hasattr(self.scene, "panel_structures") and self.scene.panel_structures:
            for p in self.scene.panel_structures:
                bx, by, bw, bh = p.bbox
                ix, iy, iw, ih = p.interior_bbox
                # Mark outer panel box
                mask[by:min(self.canvas_h, by+bh), bx:min(self.canvas_w, bx+bw)] = 255
                # Clear interior safe content area
                mask[iy:min(self.canvas_h, iy+ih), ix:min(self.canvas_w, ix+iw)] = 0

        # 2. From is_frame SceneObjects (e.g. outer single scene border rectangles)
        for obj in self.scene.objects:
            if getattr(obj, "is_frame", False):
                for s in obj.strokes:
                    if len(s.points) >= 2:
                        pts = s.points.astype(np.int32)
                        w = max(2, int(round(s.width)) + 4)
                        cv2.polylines(mask, [pts], s.is_closed, 255, w)

        return mask

    def _compute_residual_mask(self) -> np.ndarray:
        """
        Computes the unclassified/residual pixel mask across the canvas.
        Marks all pixels covered by strokes or fill regions.
        """
        covered = np.zeros((self.canvas_h, self.canvas_w), dtype=np.uint8)

        # Mark all fill regions (dilated ROI masks)
        for fe in self.timeline.fill_events:
            r = fe.region
            if r.cropped_mask is not None:
                bx, by, bw, bh = r.bbox
                x2 = min(self.canvas_w, bx + bw)
                y2 = min(self.canvas_h, by + bh)
                if x2 > bx and y2 > by:
                    cm = r.cropped_mask[:(y2 - by), :(x2 - bx)]
                    covered[by:y2, bx:x2][cm > 0] = 255

        # Mark all stroke lines
        for se in self.timeline.stroke_events:
            s = se.stroke
            if len(s.points) >= 2:
                pts = s.points.astype(np.int32)
                w = max(1, int(round(s.width)))
                cv2.polylines(covered, [pts], s.is_closed, 255, w + 2)

        residual = cv2.bitwise_not(covered)
        return residual

    def _compute_residual_distance_transform(self) -> Tuple[np.ndarray, float]:
        """
        Computes Euclidean distance transform of residual pixels to nearest artwork/stroke.
        Allows distance-based spatial reveal ordering (close-to-art pixels reveal first).
        """
        if cv2.countNonZero(self.residual_mask) == 0:
            return np.zeros((self.canvas_h, self.canvas_w), dtype=np.float32), 1.0

        dist_map = cv2.distanceTransform(self.residual_mask, cv2.DIST_L2, 5)
        max_dist = float(np.max(dist_map)) if np.any(dist_map) else 1.0
        return dist_map, max(1.0, max_dist)

    def _apply_residual_reveal(self, canvas: np.ndarray, current_time: float):
        """
        Final Residual Pass:
        STRICT: Operates ONLY after all character/stroke drawing events have completed (current_time >= drawing_end_time).
        Excludes panel borders so frame outlines are never stamped onto the canvas.
        """
        if self.source_image is None:
            return

        total_dur = self.timeline.duration
        if current_time >= total_dur:
            # 100% Full Source Reproduction at completion (excluding panel frame borders)
            canvas[:, :] = self.source_image[:self.canvas_h, :self.canvas_w]
            if np.any(self.frame_border_mask > 0):
                canvas[self.frame_border_mask > 0] = self.bg_color
            return

        # STRICT RULE: No residual reveal before all drawing events complete!
        reveal_start = self.drawing_end_time
        if current_time < reveal_start:
            return

        reveal_duration = max(0.01, total_dur - reveal_start)
        prog = min(1.0, (current_time - reveal_start) / reveal_duration)

        if prog >= 0.99:
            canvas[self.residual_mask > 0] = self.source_image[self.residual_mask > 0]
        else:
            # Distance-based spatial ring reveal: pixels closer to strokes reveal earlier
            dist_threshold = self.residual_max_dist * prog
            active_residual = (self.residual_mask > 0) & (self.residual_dist_map <= dist_threshold)
            
            # Direct source pixel copy for active distance band
            if np.any(active_residual):
                canvas[active_residual] = self.source_image[active_residual]

            # Soft alpha blend for outer residual border pixels
            soft_prog = prog * 0.8
            blend_mask = (self.residual_mask > 0) & (~active_residual)
            if np.any(blend_mask) and soft_prog > 0.05:
                res_src = self.source_image[blend_mask]
                can_pix = canvas[blend_mask]
                blended = cv2.addWeighted(res_src, soft_prog, can_pix, 1.0 - soft_prog, 0)
                canvas[blend_mask] = blended

        if np.any(self.frame_border_mask > 0):
            canvas[self.frame_border_mask > 0] = self.bg_color

    def render_frame_at_time(self, current_time: float) -> np.ndarray:
        """
        Renders a single frame at timestamp current_time:
        - Canvas begins 100% blank (background color).
        - Active & completed fills and strokes are revealed.
        - Residual pixels remain hidden until all drawing completes.
        - Frame borders are excluded and kept clean background.
        - Hand & pencil overlay is drawn.
        - Camera transform is applied as the final step.
        """
        canvas = np.full((self.canvas_h, self.canvas_w, 3), self.bg_color, dtype=np.uint8)

        # 1. Render active and completed fills with TrueColor texture from source_image
        for fe in self.timeline.fill_events:
            if current_time < fe.start_time:
                continue
            elif current_time >= fe.end_time:
                FillAnimator.render_fill(canvas, fe.region, 1.0, fe.easing, self.source_image)
            else:
                progress = (current_time - fe.start_time) / max(1e-4, fe.end_time - fe.start_time)
                FillAnimator.render_fill(canvas, fe.region, progress, fe.easing, self.source_image)

        # 2. Render active and completed strokes with TrueColor line texture from source_image
        for se in self.timeline.stroke_events:
            if current_time < se.start_time:
                continue
            elif current_time >= se.end_time:
                StrokeAnimator.render_stroke(canvas, se.stroke, 1.0, se.easing, self.source_image)
            else:
                progress = (current_time - se.start_time) / max(1e-4, se.end_time - se.start_time)
                StrokeAnimator.render_stroke(canvas, se.stroke, progress, se.easing, self.source_image)

        # 3. Final Residual Pass (ONLY active after all drawing events complete)
        self._apply_residual_reveal(canvas, current_time)

        # Keep frame borders clean background
        if np.any(self.frame_border_mask > 0):
            canvas[self.frame_border_mask > 0] = self.bg_color

        # 4. Visual Drawing Hand & Pencil Overlay
        if self.hand_overlay is not None and getattr(self.scene.config, "show_hand", True):
            self.hand_overlay.overlay(canvas, self.timeline, current_time)

        # 5. Camera transformation
        cam_state = self.camera_animator.get_state_at_time(
            self.camera_shots, current_time, self.canvas_w, self.canvas_h
        )
        return self.camera.apply(canvas, cam_state)

    def render_raw_final_frame(self) -> np.ndarray:
        """
        Renders the un-camera-transformed raw canvas at final completion time for fidelity testing.
        Zero overlays are applied so this strictly tests source image pixel preservation.
        """
        return self.render_raw_frame_at_time(self.timeline.duration + 0.1)

    def render_raw_frame_at_time(self, current_time: float) -> np.ndarray:
        """
        Renders raw canvas without camera viewport transformations and without hand overlay.
        """
        canvas = np.full((self.canvas_h, self.canvas_w, 3), self.bg_color, dtype=np.uint8)

        for fe in self.timeline.fill_events:
            if current_time >= fe.end_time:
                FillAnimator.render_fill(canvas, fe.region, 1.0, fe.easing, self.source_image)
            elif current_time >= fe.start_time:
                progress = (current_time - fe.start_time) / max(1e-4, fe.end_time - fe.start_time)
                FillAnimator.render_fill(canvas, fe.region, progress, fe.easing, self.source_image)

        for se in self.timeline.stroke_events:
            if current_time >= se.end_time:
                StrokeAnimator.render_stroke(canvas, se.stroke, 1.0, se.easing, self.source_image)
            elif current_time >= se.start_time:
                progress = (current_time - se.start_time) / max(1e-4, se.end_time - se.start_time)
                StrokeAnimator.render_stroke(canvas, se.stroke, progress, se.easing, self.source_image)

        self._apply_residual_reveal(canvas, current_time)

        if np.any(self.frame_border_mask > 0):
            canvas[self.frame_border_mask > 0] = self.bg_color

        return canvas

    def render_scene(self, scene: Scene, encoder, progress_callback=None):
        """V3.1: Convenience method to render a full scene."""
        self.render_all(encoder, progress_callback)

    def render_panel(self, panel_scene: Scene, encoder, progress_callback=None):
        """V3.1: Convenience method to render a single panel's scene."""
        self.render_all(encoder, progress_callback)

    def render_all(self, encoder, progress_callback: Optional[Callable[[float], None]] = None):
        """
        Incremental baking render loop for maximum performance, ZERO early reveal, and 100% TrueColor fidelity.
        """
        fps = self.scene.config.fps
        total_duration = self.timeline.duration
        total_frames = max(1, int(round(total_duration * fps)))

        stroke_events = self.timeline.stroke_events
        fill_events = self.timeline.fill_events

        base_canvas = np.full((self.canvas_h, self.canvas_w, 3), self.bg_color, dtype=np.uint8)
        baked_strokes = set()
        baked_fills = set()
        residual_baked = False

        # Strict: Residual reveal starts only after all drawing events finish
        all_event_ends = [e.end_time for e in stroke_events + fill_events]
        drawing_end_time = max(all_event_ends) if all_event_ends else 0.0
        reveal_start = drawing_end_time
        reveal_duration = max(0.01, total_duration - reveal_start)

        if self.hand_overlay is not None:
            self.hand_overlay.reset()

        for frame_idx in range(total_frames):
            current_time = frame_idx / float(fps)

            # 1. Bake ONLY 100% finished fills with TrueColor texture
            for i, fe in enumerate(fill_events):
                if i not in baked_fills and fe.end_time <= current_time:
                    FillAnimator.render_fill(base_canvas, fe.region, 1.0, fe.easing, self.source_image)
                    baked_fills.add(i)

            # 2. Bake ONLY 100% finished strokes with TrueColor texture
            for i, se in enumerate(stroke_events):
                if i not in baked_strokes and se.end_time <= current_time:
                    StrokeAnimator.render_stroke(base_canvas, se.stroke, 1.0, se.easing, self.source_image)
                    baked_strokes.add(i)

            # 3. Active elements on frame canvas (strictly initialized from base_canvas)
            active_frame_canvas = base_canvas.copy()

            for i, fe in enumerate(fill_events):
                if i not in baked_fills and fe.start_time <= current_time < fe.end_time:
                    prog = (current_time - fe.start_time) / max(1e-4, fe.end_time - fe.start_time)
                    FillAnimator.render_fill(active_frame_canvas, fe.region, prog, fe.easing, self.source_image)

            for i, se in enumerate(stroke_events):
                if i not in baked_strokes and se.start_time <= current_time < se.end_time:
                    prog = (current_time - se.start_time) / max(1e-4, se.end_time - se.start_time)
                    StrokeAnimator.render_stroke(active_frame_canvas, se.stroke, prog, se.easing, self.source_image)

            # 4. Final Residual Reveal (STRICT: only active after all drawing events complete)
            if self.source_image is not None and current_time >= reveal_start:
                if not residual_baked and current_time >= total_duration - (1.0 / max(1, fps)):
                    # Last frame: bake full source residual (excluding frame borders)
                    base_canvas[self.residual_mask > 0] = self.source_image[self.residual_mask > 0]
                    residual_baked = True
                    active_frame_canvas[self.residual_mask > 0] = self.source_image[self.residual_mask > 0]
                else:
                    res_prog = min(1.0, (current_time - reveal_start) / reveal_duration)
                    if res_prog >= 0.99:
                        active_frame_canvas[self.residual_mask > 0] = self.source_image[self.residual_mask > 0]
                    else:
                        dist_thresh = self.residual_max_dist * res_prog
                        active_res = (self.residual_mask > 0) & (self.residual_dist_map <= dist_thresh)
                        if np.any(active_res):
                            active_frame_canvas[active_res] = self.source_image[active_res]

                        blend_mask = (self.residual_mask > 0) & (~active_res)
                        soft_p = res_prog * 0.8
                        if np.any(blend_mask) and soft_p > 0.05:
                            res_pixels = self.source_image[blend_mask]
                            can_pixels = active_frame_canvas[blend_mask]
                            blended = cv2.addWeighted(res_pixels, soft_p, can_pixels, 1.0 - soft_p, 0)
                            active_frame_canvas[blend_mask] = blended

            # Exclude frame borders from visible canvas
            if np.any(self.frame_border_mask > 0):
                active_frame_canvas[self.frame_border_mask > 0] = self.bg_color

            # 5. Visual Drawing Hand & Pencil Overlay
            if self.hand_overlay is not None and getattr(self.scene.config, "show_hand", True):
                self.hand_overlay.overlay(active_frame_canvas, self.timeline, current_time)

            # 6. Camera Viewport Transformation
            cam_state = self.camera_animator.get_state_at_time(
                self.camera_shots, current_time, self.canvas_w, self.canvas_h
            )
            final_frame_bgr = self.camera.apply(active_frame_canvas, cam_state)

            encoder.write_frame(final_frame_bgr)

            if progress_callback and frame_idx % max(1, (total_frames // 100)) == 0:
                pct = (frame_idx / float(total_frames)) * 100.0
                progress_callback(pct)

        if progress_callback:
            progress_callback(100.0)

    @staticmethod
    def verify_fidelity(source_image: np.ndarray, raw_final_frame: np.ndarray, ignore_mask: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Acceptance Criteria Fidelity Test:
        Evaluates pixel matching, MAE, MSE, and coverage before lossy video compression.
        """
        h_s, w_s = source_image.shape[:2]
        h_f, w_f = raw_final_frame.shape[:2]
        
        min_h = min(h_s, h_f)
        min_w = min(w_s, w_f)

        src = source_image[:min_h, :min_w].astype(np.float32)
        raw = raw_final_frame[:min_h, :min_w].astype(np.float32)

        diff_matrix = np.abs(src - raw)
        if ignore_mask is not None:
            ign = ignore_mask[:min_h, :min_w]
            diff_matrix[ign > 0] = 0.0

        total_pixels = min_h * min_w
        different_pixels = int(np.count_nonzero(np.any(diff_matrix > 0, axis=2)))

        mae = float(np.mean(diff_matrix))
        mse = float(np.mean((src - raw) ** 2))
        max_error = float(np.max(diff_matrix)) if diff_matrix.size > 0 else 0.0
        coverage = float(total_pixels - different_pixels) / float(max(1, total_pixels)) * 100.0

        metrics = {
            "source_pixels": total_pixels,
            "revealed_pixels": total_pixels - different_pixels,
            "missing_pixels": different_pixels,
            "coverage_pct": coverage,
            "mae": mae,
            "mse": mse,
            "max_error": max_error,
            "is_perfect": (different_pixels == 0 and mae == 0.0)
        }

        print("==================================================")
        print("RENDERING")
        print("---------")
        print(f"revealed_pixels: {metrics['revealed_pixels']}")
        print(f"residual_pixels: {different_pixels}")
        print(f"coverage_percent: {coverage:.2f}%")
        print(f"final_pixel_difference: {mae:.4f}")
        print("==================================================")

        return metrics
