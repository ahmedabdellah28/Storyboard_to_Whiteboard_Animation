import os
import cv2
import numpy as np
import logging
from typing import Optional, Tuple, Dict, Any
from ..core.timeline import Timeline, StrokeEvent, FillEvent
from ..core.region import ColorRegion, FillMode
from ..animation.stroke_animator import StrokeAnimator
from ..animation.easing import get_easing

logger = logging.getLogger(__name__)


class HandOverlay:
    """
    V3.1 High-Fidelity Drawing Hand & Pencil Overlay System.
    
    Responsibilities:
    - Provides a purely visual drawing explanation (Hand + Marker/Pencil).
    - Accurately tracks stroke/fill drawing paths in real-time.
    - Smoothly tilts/rotates the pen according to movement trajectory.
    - Applies smooth fade-in/fade-out during transitions and final holds.
    - Supports Storyboard panel clipping so the hand never bleeds outside active panels.
    - ZERO impact on source pixels: on the final frame (or when disabled), the canvas is 100% pure source artwork.
    """

    _cached_hand_bgr: Optional[np.ndarray] = None
    _cached_hand_alpha: Optional[np.ndarray] = None
    _cached_tip_anchor: Tuple[int, int] = (35, 14)

    def __init__(self, scale: float = 0.75, opacity: float = 1.0, tilt_enabled: bool = True):
        self.scale = scale
        self.opacity = opacity
        self.tilt_enabled = tilt_enabled

        # Smoothing state
        self._last_pos: Optional[np.ndarray] = None
        self._last_angle: float = -28.0  # Natural default rest angle in degrees
        self._last_time: float = -1.0

        self._load_assets()

    @classmethod
    def _load_assets(cls):
        """Loads and pre-processes drawing-hand and hand-mask sprites."""
        if cls._cached_hand_bgr is not None and cls._cached_hand_alpha is not None:
            return

        # Locate asset paths
        possible_roots = [
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "images"),
            os.path.join(os.path.dirname(__file__), "..", "data", "images"),
            os.path.abspath("kivy/data/images"),
            os.path.abspath("data/images"),
        ]

        hand_path = None
        mask_path = None

        for root in possible_roots:
            h_p = os.path.join(root, "drawing-hand.png")
            m_p = os.path.join(root, "hand-mask.png")
            if os.path.exists(h_p) and os.path.exists(m_p):
                hand_path = h_p
                mask_path = m_p
                break

        if hand_path is None or not os.path.exists(hand_path):
            logger.warning("[HAND] drawing-hand.png asset not found. Synthesizing fallback cursor.")
            cls._create_synthetic_fallback()
            return

        try:
            bytes_hand = np.fromfile(hand_path, dtype=np.uint8)
            hand_img = cv2.imdecode(bytes_hand, cv2.IMREAD_UNCHANGED)

            if hand_img is None:
                raise ValueError("Could not decode hand image")

            # Extract BGR and Alpha
            if hand_img.ndim == 3 and hand_img.shape[2] == 4:
                bgr = hand_img[:, :, :3]
                alpha = hand_img[:, :, 3].astype(np.float32) / 255.0
            else:
                bgr = hand_img if hand_img.ndim == 3 else cv2.cvtColor(hand_img, cv2.COLOR_GRAY2BGR)
                alpha = np.ones((bgr.shape[0], bgr.shape[1]), dtype=np.float32)

            # If external mask exists, safely match spatial shape and combine
            if mask_path is not None and os.path.exists(mask_path):
                bytes_mask = np.fromfile(mask_path, dtype=np.uint8)
                mask_img = cv2.imdecode(bytes_mask, cv2.IMREAD_GRAYSCALE)
                if mask_img is not None:
                    if mask_img.shape[:2] != bgr.shape[:2]:
                        mask_img = cv2.resize(mask_img, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_LINEAR)
                    mask_a = mask_img.astype(np.float32) / 255.0
                    alpha = np.maximum(alpha, mask_a)

            # Solidify body: ensure full crisp 100% opacity inside silhouette
            alpha = np.where(alpha > 0.12, 1.0, alpha / 0.12).astype(np.float32)

            # Find extreme coordinates of non-zero mask for tight bounding box
            y_indices, x_indices = np.where(alpha > 0.05)
            if len(x_indices) > 0:
                min_x, max_x = int(np.min(x_indices)), int(np.max(x_indices))
                min_y, max_y = int(np.min(y_indices)), int(np.max(y_indices))

                # Crop tightly
                bgr = bgr[min_y:max_y+1, min_x:max_x+1]
                alpha = alpha[min_y:max_y+1, min_x:max_x+1]

                # Precise pen tip anchor at top of pen nib
                top_y = 0
                top_x_arr = np.where(alpha[top_y, :] > 0.1)[0]
                if len(top_x_arr) > 0:
                    tip_x = int(np.mean(top_x_arr))
                    tip_y = 0
                else:
                    tip_x, tip_y = 14, 0
            else:
                tip_x, tip_y = 14, 0

            cls._cached_hand_bgr = bgr
            cls._cached_hand_alpha = alpha
            cls._cached_tip_anchor = (tip_x, tip_y)
            logger.info(f"[HAND] Asset loaded successfully: size={bgr.shape[:2]}, tip={cls._cached_tip_anchor}")

        except Exception as e:
            logger.error(f"[HAND] Error loading hand asset: {e}")
            cls._create_synthetic_fallback()

    @classmethod
    def _create_synthetic_fallback(cls):
        """Creates a clean synthetic pen/stylus sprite if image asset is missing."""
        w, h = 180, 260
        bgr = np.zeros((h, w, 3), dtype=np.uint8)
        alpha = np.zeros((h, w), dtype=np.float32)

        # Pen body
        pen_pts = np.array([[20, 10], [45, 15], [160, 240], [135, 255]], dtype=np.int32)
        cv2.fillPoly(bgr, [pen_pts], (220, 220, 220))
        cv2.fillPoly(alpha, [pen_pts], 1.0)

        # Pen nib
        nib_pts = np.array([[20, 10], [12, 0], [25, 4]], dtype=np.int32)
        cv2.fillPoly(bgr, [nib_pts], (40, 40, 40))
        cv2.fillPoly(alpha, [nib_pts], 1.0)

        cls._cached_hand_bgr = bgr
        cls._cached_hand_alpha = alpha
        cls._cached_tip_anchor = (12, 0)

    def reset(self):
        """Resets smoothing trajectory state for a new animation pass."""
        self._last_pos = None
        self._last_angle = -28.0
        self._last_time = -1.0

    def get_drawing_state_at_time(
        self,
        timeline: Timeline,
        current_time: float,
        canvas_w: int,
        canvas_h: int
    ) -> Tuple[Optional[np.ndarray], float, float, Optional[Tuple[int, int, int, int]]]:
        """
        Determines the pen tip coordinate (x, y), tilt angle (degrees), opacity [0.0, 1.0],
        and current active panel clipping bbox at timestamp current_time.
        """
        total_duration = timeline.duration
        if current_time >= total_duration - 0.15:
            # Hide hand on final hold frames so raw artwork is completely clean
            return None, 0.0, 0.0, None

        # 1. Search for active stroke event
        for se in timeline.stroke_events:
            if se.start_time <= current_time <= se.end_time:
                duration = max(1e-4, se.end_time - se.start_time)
                prog = (current_time - se.start_time) / duration
                pts = StrokeAnimator.get_visible_path(se.stroke, prog, get_easing(se.easing))
                
                if len(pts) > 0:
                    curr_pt = pts[-1].copy()
                    # Calculate trajectory angle
                    if len(pts) >= 3:
                        prev_pt = pts[-3]
                        dx = curr_pt[0] - prev_pt[0]
                        dy = curr_pt[1] - prev_pt[1]
                        angle_rad = np.arctan2(dy, dx)
                        angle_deg = float(np.degrees(angle_rad))
                    else:
                        angle_deg = -28.0

                    # 100% Solid Opacity during drawing
                    opacity = self.opacity
                    return curr_pt, angle_deg, opacity, getattr(se.stroke, 'panel_bbox', None)

        # 2. Search for active fill event
        for fe in timeline.fill_events:
            if fe.start_time <= current_time <= fe.end_time:
                duration = max(1e-4, fe.end_time - fe.start_time)
                prog = (current_time - fe.start_time) / duration
                r = fe.region
                bx, by, bw, bh = r.bbox

                # Move pen along the fill region reveal direction
                if r.fill_mode == FillMode.TOP_TO_BOTTOM:
                    fy = by + bh * prog
                    fx = bx + bw * (0.5 + 0.3 * np.sin(prog * 8 * np.pi))
                elif r.fill_mode == FillMode.LEFT_TO_RIGHT:
                    fx = bx + bw * prog
                    fy = by + bh * (0.5 + 0.3 * np.sin(prog * 8 * np.pi))
                elif r.fill_mode == FillMode.CENTER_OUT:
                    angle = prog * 6 * np.pi
                    radius = min(bw, bh) * 0.4 * prog
                    fx = r.center[0] + radius * np.cos(angle)
                    fy = r.center[1] + radius * np.sin(angle)
                else:  # FOLLOW_OUTLINE
                    fx = r.center[0] + (bw * 0.2) * np.sin(prog * 4 * np.pi)
                    fy = r.center[1] + (bh * 0.2) * np.cos(prog * 4 * np.pi)

                curr_pt = np.array([fx, fy], dtype=np.float64)
                angle_deg = -28.0 + 8.0 * np.sin(prog * 6 * np.pi)
                opacity = self.opacity
                return curr_pt, angle_deg, opacity, None

        # 3. Inter-event transit interpolation (moving pen to next drawing element)
        prev_event = None
        next_event = None

        all_events = []
        for se in timeline.stroke_events:
            all_events.append(('stroke', se.start_time, se.end_time, se))
        for fe in timeline.fill_events:
            all_events.append(('fill', fe.start_time, fe.end_time, fe))

        all_events.sort(key=lambda ev: ev[1])

        for ev in all_events:
            if ev[2] < current_time:
                prev_event = ev
            elif ev[1] > current_time:
                next_event = ev
                break

        if prev_event is not None and next_event is not None:
            # Transit between prev and next
            t_gap_start = prev_event[2]
            t_gap_end = next_event[1]
            gap_dur = max(1e-4, t_gap_end - t_gap_start)
            transit_prog = (current_time - t_gap_start) / gap_dur
            transit_prog = max(0.0, min(1.0, transit_prog))

            # Ease transit
            eased_prog = float(get_easing("ease_in_out")(transit_prog))

            # Determine start position
            if prev_event[0] == 'stroke':
                s_pts = prev_event[3].stroke.points
                p_start = s_pts[-1] if len(s_pts) > 0 else np.array([canvas_w / 2.0, canvas_h / 2.0])
            else:
                p_start = prev_event[3].region.center

            # Determine end position
            if next_event[0] == 'stroke':
                s_pts = next_event[3].stroke.points
                p_end = s_pts[0] if len(s_pts) > 0 else np.array([canvas_w / 2.0, canvas_h / 2.0])
            else:
                p_end = next_event[3].region.center

            # Slight arc during pen lift
            curr_pt = (1.0 - eased_prog) * p_start + eased_prog * p_end
            arc_offset = np.sin(eased_prog * np.pi) * -15.0
            curr_pt[1] += arc_offset

            angle_deg = -28.0
            opacity = self.opacity
            return curr_pt, angle_deg, opacity, None

        elif prev_event is None and next_event is not None:
            # Entry Transition: hand smoothly glides in from bottom-right to the first stroke
            t_entry_end = next_event[1]
            t_entry_start = max(0.0, t_entry_end - 0.7)
            if current_time >= t_entry_start:
                entry_prog = (current_time - t_entry_start) / max(0.01, t_entry_end - t_entry_start)
                entry_prog = max(0.0, min(1.0, entry_prog))
                eased_p = float(get_easing("ease_out")(entry_prog))

                # Determine first target position
                if next_event[0] == 'stroke':
                    s_pts = next_event[3].stroke.points
                    p_end = s_pts[0] if len(s_pts) > 0 else np.array([canvas_w / 2.0, canvas_h / 2.0])
                else:
                    p_end = next_event[3].region.center

                p_start = np.array([canvas_w * 0.85, canvas_h + 120.0], dtype=np.float64)
                curr_pt = (1.0 - eased_p) * p_start + eased_p * p_end
                curr_pt[1] += np.sin(eased_p * np.pi) * -20.0
                opacity = self.opacity
                return curr_pt, -28.0, opacity, None

        elif prev_event is not None and next_event is None:
            # After last event: smooth fade out / exit towards bottom-right
            t_after = current_time - prev_event[2]
            fade_out = max(0.0, 1.0 - (t_after / 0.5))
            if fade_out > 0.0:
                if prev_event[0] == 'stroke':
                    s_pts = prev_event[3].stroke.points
                    p_base = s_pts[-1] if len(s_pts) > 0 else np.array([canvas_w / 2.0, canvas_h / 2.0])
                else:
                    p_base = prev_event[3].region.center
                curr_pt = p_base + np.array([t_after * 180.0, t_after * 180.0])
                return curr_pt, -28.0, self.opacity * fade_out, None

        return None, 0.0, 0.0, None

    def render_hand_on_canvas(
        self,
        canvas: np.ndarray,
        target_pos: np.ndarray,
        target_angle_deg: float,
        opacity: float,
        clip_bbox: Optional[Tuple[int, int, int, int]] = None
    ):
        """
        Renders the hand sprite rotated and positioned at target_pos with alpha blending.
        """
        if opacity <= 0.01 or target_pos is None:
            return

        bgr_sprite = self._cached_hand_bgr
        alpha_sprite = self._cached_hand_alpha
        tip_anchor = self._cached_tip_anchor

        if bgr_sprite is None or alpha_sprite is None:
            return

        can_h, can_w = canvas.shape[:2]

        # Temporal angle smoothing (Exponential Moving Average)
        # Clamped to natural hand holding range (-45 deg to +10 deg)
        clamped_angle = max(-48.0, min(12.0, target_angle_deg))
        if self._last_angle is not None and self.tilt_enabled:
            smooth_angle = self._last_angle * 0.80 + clamped_angle * 0.20
        else:
            smooth_angle = clamped_angle
        self._last_angle = smooth_angle

        # Position smoothing: Damped human arm physical inertia
        if self._last_pos is not None:
            smooth_pos = self._last_pos * 0.65 + target_pos * 0.35
        else:
            smooth_pos = target_pos
        self._last_pos = smooth_pos.copy()

        # Dynamic scale relative to canvas height
        effective_scale = self.scale * (can_h / 1080.0) * 0.90
        effective_scale = max(0.20, min(1.50, effective_scale))

        # 2D Affine Transformation:
        # 1. Translate tip anchor to (0, 0)
        # 2. Scale by effective_scale
        # 3. Rotate by smooth_angle (relative to sprite default -32 deg orientation)
        rel_rotation = smooth_angle - (-32.0)
        rad = np.radians(rel_rotation)
        cos_a = np.cos(rad) * effective_scale
        sin_a = np.sin(rad) * effective_scale

        ax, ay = tip_anchor
        # Transformed tip anchor
        tx = float(smooth_pos[0])
        ty = float(smooth_pos[1])

        # Affine matrix: maps sprite (x, y) -> canvas (x', y')
        # [x']   [ cos_a  -sin_a ] [ x - ax ] + [ tx ]
        # [y'] = [ sin_a   cos_a ] [ y - ay ]   [ ty ]
        m00 = cos_a
        m01 = -sin_a
        m02 = tx - (cos_a * ax - sin_a * ay)

        m10 = sin_a
        m11 = cos_a
        m12 = ty - (sin_a * ax + cos_a * ay)

        M = np.array([[m00, m01, m02], [m10, m11, m12]], dtype=np.float32)

        # Warp hand sprite and alpha mask
        warped_hand = cv2.warpAffine(
            bgr_sprite, M, (can_w, can_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0)
        )

        warped_alpha = cv2.warpAffine(
            alpha_sprite, M, (can_w, can_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0.0
        )

        # Apply global opacity
        final_alpha = warped_alpha * float(opacity)

        # Storyboard Panel Clipping: keep hand inside panel interior
        if clip_bbox is not None:
            cx, cy, cw, ch = clip_bbox
            cx1 = max(0, cx)
            cy1 = max(0, cy)
            cx2 = min(can_w, cx + cw)
            cy2 = min(can_h, cy + ch)

            # Mask out alpha outside clip_bbox
            clip_mask = np.zeros((can_h, can_w), dtype=np.float32)
            clip_mask[cy1:cy2, cx1:cx2] = 1.0
            final_alpha *= clip_mask

        # Fast alpha compositing
        alpha_mask = final_alpha > 0.005
        if np.any(alpha_mask):
            a3 = final_alpha[alpha_mask, None]
            can_pixels = canvas[alpha_mask].astype(np.float32)
            hand_pixels = warped_hand[alpha_mask].astype(np.float32)
            blended = can_pixels * (1.0 - a3) + hand_pixels * a3
            canvas[alpha_mask] = np.clip(blended, 0, 255).astype(np.uint8)

    def overlay(
        self,
        canvas: np.ndarray,
        timeline: Timeline,
        current_time: float,
        clip_bbox: Optional[Tuple[int, int, int, int]] = None
    ):
        """Convenience single-call method to evaluate timeline and render hand overlay."""
        can_h, can_w = canvas.shape[:2]
        pos, angle, opacity, active_clip = self.get_drawing_state_at_time(
            timeline, current_time, can_w, can_h
        )
        if pos is not None and opacity > 0.01:
            eff_clip = clip_bbox if clip_bbox is not None else active_clip
            self.render_hand_on_canvas(canvas, pos, angle, opacity, eff_clip)
