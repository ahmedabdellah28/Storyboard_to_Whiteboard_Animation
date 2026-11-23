"""Motion Templates System (20 Standard Transitions).
Reference: motion_types.md (2026 Motion Graphics & Explainer Trends)

All 20 transition templates:
1. Morph Transition
2. Match Cut Transition
3. Camera Push / Pull
4. Directional Flow
5. Mask Reveal / Wipe
6. Object Push Transition
7. Whip Motion
8. Scale Punch
9. Orbit / Arc Motion
10. Parallax Depth
11. Kinetic Typography Transition
12. Shape Transform
13. Line Path Transition
14. Liquid / Organic Flow
15. Card Stack Transition
16. Split Screen Transition
17. Blur Speed Transition
18. Trail / Echo Transition
19. Rotation / Spin Reveal
20. Elastic / Overshoot Transition

Every template preserves:
- Physical stage baseline grounding (Y = 840) with zero float.
- Proper alpha compositing & easing curves.
- Snappy, responsive execution in isolation.
"""

import math
import numpy as np
import cv2
from typing import Tuple, Dict, Any, Optional

def ease(p: float, curve: str = "linear") -> float:
    p = max(0.0, min(1.0, float(p)))
    if curve == "linear":
        return p
    elif curve == "in_quad":
        return p * p
    elif curve == "out_quad":
        return p * (2.0 - p)
    elif curve == "in_out_quad":
        return 2.0 * p * p if p < 0.5 else -1.0 + (4.0 - 2.0 * p) * p
    elif curve == "in_cubic":
        return p * p * p
    elif curve == "out_cubic":
        return (p - 1.0) * (p - 1.0) * (p - 1.0) + 1.0
    elif curve == "out_expo":
        return 1.0 if p == 1.0 else 1.0 - math.pow(2.0, -10.0 * p)
    elif curve == "out_back":
        c1 = 1.70158
        c3 = c1 + 1.0
        return 1.0 + c3 * math.pow(p - 1.0, 3.0) + c1 * math.pow(p - 1.0, 2.0)
    elif curve == "out_elastic":
        if p == 0: return 0.0
        if p == 1: return 1.0
        return math.pow(2.0, -10.0 * p) * math.sin((p * 10.0 - 0.75) * (2.0 * math.pi / 3.0)) + 1.0
    return p

def blend_patch(dest: np.ndarray, patch: np.ndarray, x: int, y: int):
    ph, pw = patch.shape[:2]
    dh, dw = dest.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(dw, x + pw), min(dh, y + ph)
    if x1 >= x2 or y1 >= y2:
        return
    px1, py1 = x1 - x, y1 - y
    px2, py2 = px1 + (x2 - x1), py1 + (y2 - y1)
    src = patch[py1:py2, px1:px2]
    if src.shape[2] == 4:
        alpha = (src[:, :, 3].astype(float) / 255.0)[:, :, np.newaxis]
        dest[y1:y2, x1:x2, :3] = (alpha * src[:, :, :3].astype(float) + (1.0 - alpha) * dest[y1:y2, x1:x2, :3].astype(float)).astype(np.uint8)
        if dest.shape[2] == 4:
            dest[y1:y2, x1:x2, 3] = np.maximum(dest[y1:y2, x1:x2, 3], src[:, :, 3])
    else:
        dest[y1:y2, x1:x2, :3] = src[:, :, :3]

def create_ground_shadow(width: int, alpha: float = 1.0) -> np.ndarray:
    """Disabled: user requested removal of the two-toned puddle shadow spot."""
    return np.zeros((1, 1, 4), dtype=np.uint8)

class MotionTemplates:
    """Library of all 20 Standard Motion Transitions."""

    @staticmethod
    def render_01_morph(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """1. Morph Transition: A squashes down, incandescent spark at midpoint, B elastically blooms."""
        cw, ch = int(size * 1.5) + 120, int(size * 1.5) + 120
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        ha, wa = raw_a.shape[:2]
        hb, wb = raw_b.shape[:2]
        scale_a = size / max(ha, wa)
        scale_b = size / max(hb, wb)

        # Asset A
        if p < 0.55:
            pa = p / 0.55
            sx = 1.0 + 0.16 * math.sin(pa * math.pi)
            sy = max(0.1, 1.0 - 0.70 * ease(pa, "in_quad"))
            alpha_a = max(0.0, 1.0 - ease(max(0.0, (pa - 0.35) / 0.65), "in_quad"))
            nwa, nha = max(4, int(wa * scale_a * sx)), max(4, int(ha * scale_a * sy))
            res_a = cv2.resize(raw_a, (nwa, nha))
            if alpha_a < 1.0:
                res_a[:, :, 3] = (res_a[:, :, 3].astype(float) * alpha_a).astype(np.uint8)
            blend_patch(canvas, res_a, cx - nwa // 2, floor_y - nha)

        # Asset B
        if p >= 0.45:
            pb = (p - 0.45) / 0.55
            sb = 0.30 + 0.70 * ease(pb, "out_back")
            sx = sb * (1.0 + 0.14 * math.sin((1.0 - pb) * math.pi))
            alpha_b = min(1.0, pb / 0.35)
            nwb, nhb = max(4, int(wb * scale_b * sx)), max(4, int(hb * scale_b * sb))
            res_b = cv2.resize(raw_b, (nwb, nhb))
            if alpha_b < 1.0:
                res_b[:, :, 3] = (res_b[:, :, 3].astype(float) * alpha_b).astype(np.uint8)
            blend_patch(canvas, res_b, cx - nwb // 2, floor_y - nhb)

        # Spark
        if 0.32 <= p <= 0.68:
            pc = (p - 0.32) / 0.36
            inten = math.sin(pc * math.pi)
            core_r = int(14 + 65 * pc)
            spark = np.zeros_like(canvas)
            core_y = floor_y - int(size * 0.28)
            cv2.circle(spark, (cx, core_y), core_r, (45, 212, 191, int(190 * inten)), -1, cv2.LINE_AA)
            cv2.circle(spark, (cx, core_y), max(4, int(core_r * 0.40)), (255, 255, 255, int(250 * inten)), -1, cv2.LINE_AA)
            spark = cv2.GaussianBlur(spark, (27, 27), 0)
            blend_patch(canvas, spark, 0, 0)

        # Ground Shadow
        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_02_match_cut(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """2. Match Cut: A rotates 0->90 deg around vertical axis, B emerges seamlessly continuing 90->0 deg."""
        cw, ch = int(size * 1.5) + 120, int(size * 1.5) + 120
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        if p < 0.5:
            # A collapses horizontally (spinning out)
            pa = p / 0.5
            rot_scale = math.cos(pa * (math.pi / 2.0))
            ha, wa = raw_a.shape[:2]
            scale = size / max(ha, wa)
            nw = max(4, int(wa * scale * rot_scale))
            nh = max(4, int(ha * scale))
            res = cv2.resize(raw_a, (nw, nh))
            blend_patch(canvas, res, cx - nw // 2, floor_y - nh)
            cur_w = nw
        else:
            # B continues expansion horizontally (spinning in)
            pb = (p - 0.5) / 0.5
            rot_scale = math.sin(pb * (math.pi / 2.0))
            hb, wb = raw_b.shape[:2]
            scale = size / max(hb, wb)
            nw = max(4, int(wb * scale * rot_scale))
            nh = max(4, int(hb * scale))
            res = cv2.resize(raw_b, (nw, nh))
            blend_patch(canvas, res, cx - nw // 2, floor_y - nh)
            cur_w = nw

        sh_patch = create_ground_shadow(max(size // 3, cur_w), alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_03_camera_push_pull(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """3. Camera Push / Pull: Dramatic optical punch in on A, then pull back uncovering B."""
        cw, ch = int(size * 1.5) + 120, int(size * 1.5) + 120
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        if p < 0.5:
            pa = p / 0.5
            zoom = 1.0 + 0.65 * ease(pa, "in_cubic")
            alpha = max(0.0, 1.0 - pa * 1.5)
            ha, wa = raw_a.shape[:2]
            nw = int(wa * (size / max(ha, wa)) * zoom)
            nh = int(ha * (size / max(ha, wa)) * zoom)
            res = cv2.resize(raw_a, (nw, nh))
            res[:, :, 3] = (res[:, :, 3].astype(float) * alpha).astype(np.uint8)
            blend_patch(canvas, res, cx - nw // 2, floor_y - nh)
        else:
            pb = (p - 0.5) / 0.5
            zoom = 1.7 - 0.70 * ease(pb, "out_cubic")
            alpha = min(1.0, pb * 2.0)
            hb, wb = raw_b.shape[:2]
            nw = int(wb * (size / max(hb, wb)) * zoom)
            nh = int(hb * (size / max(hb, wb)) * zoom)
            res = cv2.resize(raw_b, (nw, nh))
            res[:, :, 3] = (res[:, :, 3].astype(float) * alpha).astype(np.uint8)
            blend_patch(canvas, res, cx - nw // 2, floor_y - nh)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_04_directional_flow(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """4. Directional Flow: Continuous momentum vector: A flows left, B enters from right."""
        cw, ch = int(size * 2.0), int(size * 1.5) + 120
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        # Flow distance
        dist = int(size * 1.1)
        # Element A
        ha, wa = raw_a.shape[:2]
        nwa = int(wa * size / max(ha, wa))
        nha = int(ha * size / max(ha, wa))
        ax = int(cx - nwa // 2 - dist * ease(p, "in_out_quad"))
        res_a = cv2.resize(raw_a, (nwa, nha))
        alpha_a = max(0.0, 1.0 - p * 1.8)
        res_a[:, :, 3] = (res_a[:, :, 3].astype(float) * alpha_a).astype(np.uint8)
        blend_patch(canvas, res_a, ax, floor_y - nha)

        # Element B
        hb, wb = raw_b.shape[:2]
        nwb = int(wb * size / max(hb, wb))
        nhb = int(hb * size / max(hb, wb))
        bx = int(cx - nwb // 2 + dist * (1.0 - ease(p, "out_cubic")))
        res_b = cv2.resize(raw_b, (nwb, nhb))
        alpha_b = min(1.0, p * 2.0)
        res_b[:, :, 3] = (res_b[:, :, 3].astype(float) * alpha_b).astype(np.uint8)
        blend_patch(canvas, res_b, bx, floor_y - nhb)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_05_mask_reveal_wipe(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """5. Mask Reveal / Wipe: Smooth horizontal geometric wipe reveals B over A."""
        cw, ch = int(size * 1.5), int(size * 1.5)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        # Render A full
        ha, wa = raw_a.shape[:2]
        nwa = int(wa * size / max(ha, wa))
        nha = int(ha * size / max(ha, wa))
        res_a = cv2.resize(raw_a, (nwa, nha))
        blend_patch(canvas, res_a, cx - nwa // 2, floor_y - nha)

        # Render B with horizontal wipe mask
        hb, wb = raw_b.shape[:2]
        nwb = int(wb * size / max(hb, wb))
        nhb = int(hb * size / max(hb, wb))
        res_b = cv2.resize(raw_b, (nwb, nhb)).copy()
        wipe_x = int(nwb * ease(p, "in_out_quad"))
        if wipe_x < nwb:
            res_b[:, wipe_x:, 3] = 0
        blend_patch(canvas, res_b, cx - nwb // 2, floor_y - nhb)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_06_object_push(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """6. Object Push: B enters with inertia from right, bumps into A, shoving A left off screen."""
        cw, ch = int(size * 2.2), int(size * 1.5)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        ha, wa = raw_a.shape[:2]
        nwa, nha = int(wa * size / max(ha, wa)), int(ha * size / max(ha, wa))
        hb, wb = raw_b.shape[:2]
        nwb, nhb = int(wb * size / max(hb, wb)), int(hb * size / max(hb, wb))

        # Collision happens around p = 0.35
        if p < 0.35:
            # B moves towards A, A remains stationary
            pp = p / 0.35
            bx = int(cw - (cw - cx) * ease(pp, "in_quad"))
            ax = cx - nwa // 2
        else:
            # Impact: A is shoved left, B settles in center
            pp = (p - 0.35) / 0.65
            ax = int(cx - nwa // 2 - size * 1.2 * ease(pp, "out_expo"))
            bx = int(cx - nwb // 2 + (size * 0.25) * (1.0 - ease(pp, "out_back")))

        res_a = cv2.resize(raw_a, (nwa, nha))
        blend_patch(canvas, res_a, ax, floor_y - nha)

        res_b = cv2.resize(raw_b, (nwb, nhb))
        blend_patch(canvas, res_b, bx, floor_y - nhb)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_07_whip_motion(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """7. Whip Motion: Fast camera whip with extreme directional motion blur."""
        cw, ch = int(size * 1.8), int(size * 1.5)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        # Intense blur in the middle (0.2 < p < 0.8)
        blur_len = int(45 * math.sin(p * math.pi))
        if blur_len % 2 == 0: blur_len += 1

        if p < 0.5:
            pa = p / 0.5
            ha, wa = raw_a.shape[:2]
            nw, nh = int(wa * size / max(ha, wa)), int(ha * size / max(ha, wa))
            res = cv2.resize(raw_a, (nw, nh))
            dx = int(-350 * ease(pa, "in_expo"))
            blend_patch(canvas, res, cx - nw // 2 + dx, floor_y - nh)
        else:
            pb = (p - 0.5) / 0.5
            hb, wb = raw_b.shape[:2]
            nw, nh = int(wb * size / max(hb, wb)), int(hb * size / max(hb, wb))
            res = cv2.resize(raw_b, (nw, nh))
            dx = int(350 * (1.0 - ease(pb, "out_expo")))
            blend_patch(canvas, res, cx - nw // 2 + dx, floor_y - nh)

        if blur_len > 3:
            kernel = np.zeros((blur_len, blur_len), dtype=np.float32)
            kernel[blur_len // 2, :] = 1.0 / blur_len
            canvas = cv2.filter2D(canvas, -1, kernel)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_08_scale_punch(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """8. Scale Punch: A punches up in scale on emphasis beat, then B emerges with reverse punch."""
        cw, ch = int(size * 1.8), int(size * 1.5)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        if p < 0.5:
            pa = p / 0.5
            # Punch up to 1.35x
            scale_mod = 1.0 + 0.35 * math.sin(pa * math.pi)
            ha, wa = raw_a.shape[:2]
            nw = max(4, int(wa * (size / max(ha, wa)) * scale_mod))
            nh = max(4, int(ha * (size / max(ha, wa)) * scale_mod))
            res = cv2.resize(raw_a, (nw, nh))
            blend_patch(canvas, res, cx - nw // 2, floor_y - nh)
        else:
            pb = (p - 0.5) / 0.5
            # Punch down from 1.35x to 1.0x with overshoot
            scale_mod = 1.0 + 0.35 * (1.0 - ease(pb, "out_back"))
            hb, wb = raw_b.shape[:2]
            nw = max(4, int(wb * (size / max(hb, wb)) * scale_mod))
            nh = max(4, int(hb * (size / max(hb, wb)) * scale_mod))
            res = cv2.resize(raw_b, (nw, nh))
            blend_patch(canvas, res, cx - nw // 2, floor_y - nh)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_09_orbit_arc(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """9. Orbit / Arc Motion: B travels along an elegant curved arched trajectory into place."""
        cw, ch = int(size * 1.8), int(size * 1.6)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        # A fades down smoothly
        alpha_a = max(0.0, 1.0 - p * 2.0)
        if alpha_a > 0.01:
            ha, wa = raw_a.shape[:2]
            nwa, nha = int(wa * size / max(ha, wa)), int(ha * size / max(ha, wa))
            res_a = cv2.resize(raw_a, (nwa, nha))
            res_a[:, :, 3] = (res_a[:, :, 3].astype(float) * alpha_a).astype(np.uint8)
            blend_patch(canvas, res_a, cx - nwa // 2, floor_y - nha)

        # B travels on arched quadratic path
        p_arc = ease(p, "out_cubic")
        hb, wb = raw_b.shape[:2]
        nwb, nhb = int(wb * size / max(hb, wb)), int(hb * size / max(hb, wb))
        # Start top right, arch upwards, settle at center
        bx = int((cx + 360) * (1.0 - p_arc) + cx * p_arc)
        by = int((floor_y - 280) * (1.0 - p_arc) + floor_y * p_arc - 120 * math.sin(p * math.pi))
        res_b = cv2.resize(raw_b, (nwb, nhb))
        alpha_b = min(1.0, p * 2.5)
        res_b[:, :, 3] = (res_b[:, :, 3].astype(float) * alpha_b).astype(np.uint8)
        blend_patch(canvas, res_b, bx - nwb // 2, by - nhb)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_10_parallax_depth(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """10. Parallax Depth: Multilayer speed separation (background moves 0.3x, hero moves 1.0x)."""
        cw, ch = int(size * 1.8), int(size * 1.5)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        # Background subtle shift (0.35x velocity)
        ha, wa = raw_a.shape[:2]
        scale_bg = (size * 0.70) / max(ha, wa)
        nwa, nha = int(wa * scale_bg), int(ha * scale_bg)
        bg_dx = int(-140 * ease(p, "in_out_quad"))
        res_a = cv2.resize(raw_a, (nwa, nha))
        res_a[:, :, 3] = (res_a[:, :, 3].astype(float) * 0.45).astype(np.uint8)  # Receded in depth
        blend_patch(canvas, res_a, cx - nwa // 2 + bg_dx, floor_y - nha)

        # Foreground hero B (1.0x velocity)
        hb, wb = raw_b.shape[:2]
        scale_fg = size / max(hb, wb)
        nwb, nhb = int(wb * scale_fg), int(hb * scale_fg)
        fg_dx = int(320 * (1.0 - ease(p, "out_cubic")))
        res_b = cv2.resize(raw_b, (nwb, nhb))
        blend_patch(canvas, res_b, cx - nwb // 2 + fg_dx, floor_y - nhb)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_11_kinetic_typography(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """11. Kinetic Typography Transition: Kinetic Arabic word scales up into visual element B."""
        cw, ch = int(size * 1.8), int(size * 1.5)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        if p < 0.45:
            # Word scales dynamically
            pa = p / 0.45
            scale_word = 0.5 + 1.2 * ease(pa, "in_quad")
            alpha = max(0.0, 1.0 - pa * 1.4)
            ha, wa = raw_a.shape[:2]
            nwa, nha = max(4, int(wa * (size / max(ha, wa)) * scale_word)), max(4, int(ha * (size / max(ha, wa)) * scale_word))
            res = cv2.resize(raw_a, (nwa, nha))
            res[:, :, 3] = (res[:, :, 3].astype(float) * alpha).astype(np.uint8)
            blend_patch(canvas, res, cx - nwa // 2, floor_y - nha)
        else:
            # Visual object blooms from word epicenter
            pb = (p - 0.45) / 0.55
            scale_b = 0.25 + 0.75 * ease(pb, "out_back")
            hb, wb = raw_b.shape[:2]
            nwb, nhb = max(4, int(wb * (size / max(hb, wb)) * scale_b)), max(4, int(hb * (size / max(hb, wb)) * scale_b))
            res = cv2.resize(raw_b, (nwb, nhb))
            blend_patch(canvas, res, cx - nwb // 2, floor_y - nhb)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_12_shape_transform(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """12. Shape Transform: Procedural geometry (circle -> rounded rect) transforms into asset B."""
        cw, ch = int(size * 1.6), int(size * 1.5)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        if p < 0.5:
            # Geometric circle / rounded rect expanding with energetic accent
            pa = p / 0.5
            rad = int(size * 0.35 * ease(pa, "out_cubic"))
            cv2.circle(canvas, (cx, floor_y - rad), rad, (45, 212, 191, 230), 6, cv2.LINE_AA)
            cv2.circle(canvas, (cx, floor_y - rad), max(4, int(rad * 0.6)), (13, 148, 136, 180), -1, cv2.LINE_AA)
        else:
            # Asset B expands out from shape
            pb = (p - 0.5) / 0.5
            hb, wb = raw_b.shape[:2]
            scale_b = 0.40 + 0.60 * ease(pb, "out_back")
            nwb, nhb = max(4, int(wb * (size / max(hb, wb)) * scale_b)), max(4, int(hb * (size / max(hb, wb)) * scale_b))
            res = cv2.resize(raw_b, (nwb, nhb))
            blend_patch(canvas, res, cx - nwb // 2, floor_y - nhb)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_13_line_path(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """13. Line Path Transition: Inked hand-drawn guide path draws from A, revealing B at its tip."""
        cw, ch = int(size * 2.0), int(size * 1.5)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        # Element A on left
        ha, wa = raw_a.shape[:2]
        nwa, nha = int(wa * (size * 0.75) / max(ha, wa)), int(ha * (size * 0.75) / max(ha, wa))
        ax = cx - int(size * 0.65)
        res_a = cv2.resize(raw_a, (nwa, nha))
        blend_patch(canvas, res_a, ax - nwa // 2, floor_y - nha)

        # Hand-inked curve from A to B
        p1 = (ax + nwa // 2, floor_y - nha // 2)
        p2 = (cx + int(size * 0.45), floor_y - int(size * 0.35))
        num_pts = max(3, int(40 * p))
        for i in range(num_pts):
            t1 = (i / float(num_pts)) * p
            t2 = ((i + 1) / float(num_pts)) * p
            x1 = int((1 - t1)**2 * p1[0] + 2 * (1 - t1) * t1 * ((p1[0] + p2[0]) // 2) + t1**2 * p2[0])
            y1 = int((1 - t1)**2 * p1[1] + 2 * (1 - t1) * t1 * (min(p1[1], p2[1]) - 80) + t1**2 * p2[1])
            x2 = int((1 - t2)**2 * p1[0] + 2 * (1 - t2) * t2 * ((p1[0] + p2[0]) // 2) + t2**2 * p2[0])
            y2 = int((1 - t2)**2 * p1[1] + 2 * (1 - t2) * t2 * (min(p1[1], p2[1]) - 80) + t2**2 * p2[1])
            cv2.line(canvas, (x1, y1), (x2, y2), (45, 212, 191, 230), 4, cv2.LINE_AA)

        # Element B reveals at tip
        if p > 0.4:
            pb = (p - 0.4) / 0.6
            hb, wb = raw_b.shape[:2]
            scale_b = (size * 0.85) / max(hb, wb) * ease(pb, "out_back")
            nwb, nhb = max(4, int(wb * scale_b)), max(4, int(hb * scale_b))
            res_b = cv2.resize(raw_b, (nwb, nhb))
            blend_patch(canvas, res_b, p2[0] - nwb // 2, floor_y - nhb)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_14_liquid_organic(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """14. Liquid / Organic Flow: Viscous blob morph expanding with sine wave deformation."""
        cw, ch = int(size * 1.6), int(size * 1.5)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        # Organic pulse
        if p < 0.5:
            pa = p / 0.5
            blob_r = int(size * 0.40 * ease(pa, "in_quad"))
            cv2.circle(canvas, (cx, floor_y - blob_r), blob_r, (16, 185, 129, 210), -1, cv2.LINE_AA)
            cv2.circle(canvas, (cx, floor_y - blob_r), int(blob_r * 0.8), (5, 150, 105, 240), -1, cv2.LINE_AA)
            canvas = cv2.GaussianBlur(canvas, (21, 21), 0)
        else:
            pb = (p - 0.5) / 0.5
            hb, wb = raw_b.shape[:2]
            scale_b = (size / max(hb, wb)) * ease(pb, "out_elastic")
            nwb, nhb = max(4, int(wb * scale_b)), max(4, int(hb * scale_b))
            res = cv2.resize(raw_b, (nwb, nhb))
            blend_patch(canvas, res, cx - nwb // 2, floor_y - nhb)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_15_card_stack(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """15. Card Stack Transition: Top card A peels/slides off upwards, uncovering card B underneath."""
        cw, ch = int(size * 1.6), int(size * 1.6)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        # Card B underneath (rises slightly as top card slides away)
        hb, wb = raw_b.shape[:2]
        nwb, nhb = int(wb * size / max(hb, wb)), int(hb * size / max(hb, wb))
        res_b = cv2.resize(raw_b, (nwb, nhb))
        blend_patch(canvas, res_b, cx - nwb // 2, floor_y - nhb)

        # Card A slides up and rotates slightly
        if p < 0.95:
            ha, wa = raw_a.shape[:2]
            nwa, nha = int(wa * size / max(ha, wa)), int(ha * size / max(ha, wa))
            dy = int(-400 * ease(p, "in_expo"))
            rot = 8.0 * ease(p, "in_quad")
            res_a = cv2.resize(raw_a, (nwa, nha))
            alpha_a = max(0.0, 1.0 - p * 1.2)
            res_a[:, :, 3] = (res_a[:, :, 3].astype(float) * alpha_a).astype(np.uint8)
            M = cv2.getRotationMatrix2D((nwa / 2.0, nha / 2.0), rot, 1.0)
            res_a = cv2.warpAffine(res_a, M, (nwa, nha), borderMode=cv2.BORDER_CONSTANT)
            blend_patch(canvas, res_a, cx - nwa // 2, floor_y - nha + dy)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_16_split_screen(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """16. Split Screen Transition: Vertical division line sweeps across, transitioning from A to B."""
        cw, ch = int(size * 1.8), int(size * 1.5)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        ha, wa = raw_a.shape[:2]
        hb, wb = raw_b.shape[:2]
        nwa, nha = int(wa * size / max(ha, wa)), int(ha * size / max(ha, wa))
        nwb, nhb = int(wb * size / max(hb, wb)), int(hb * size / max(hb, wb))

        res_a = cv2.resize(raw_a, (nwa, nha))
        res_b = cv2.resize(raw_b, (nwb, nhb))

        split_x = int(cw * ease(p, "in_out_quad"))
        canvas_a = np.zeros_like(canvas)
        canvas_b = np.zeros_like(canvas)
        blend_patch(canvas_a, res_a, cx - nwa // 2, floor_y - nha)
        blend_patch(canvas_b, res_b, cx - nwb // 2, floor_y - nhb)

        # Combine across split
        canvas[:, :split_x] = canvas_b[:, :split_x]
        canvas[:, split_x:] = canvas_a[:, split_x:]
        # Divider line
        cv2.line(canvas, (split_x, floor_y - size), (split_x, floor_y), (13, 148, 136, 255), 4, cv2.LINE_AA)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_17_blur_speed(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """17. Blur Speed Transition: Fast horizontal blur-out followed by snapping into sharp focus."""
        cw, ch = int(size * 1.8), int(size * 1.5)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        blur_val = max(1, int(35 * math.sin(p * math.pi)))
        if blur_val % 2 == 0: blur_val += 1

        if p < 0.5:
            ha, wa = raw_a.shape[:2]
            nw, nh = int(wa * size / max(ha, wa)), int(ha * size / max(ha, wa))
            res = cv2.resize(raw_a, (nw, nh))
            blend_patch(canvas, res, cx - nw // 2, floor_y - nh)
        else:
            hb, wb = raw_b.shape[:2]
            nw, nh = int(wb * size / max(hb, wb)), int(hb * size / max(hb, wb))
            res = cv2.resize(raw_b, (nw, nh))
            blend_patch(canvas, res, cx - nw // 2, floor_y - nh)

        if blur_val > 1:
            canvas = cv2.GaussianBlur(canvas, (blur_val, 1), 0)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_18_trail_echo(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """18. Trail / Echo Transition: Ghost trails replicate along movement path and converge into B."""
        cw, ch = int(size * 2.0), int(size * 1.5)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        hb, wb = raw_b.shape[:2]
        nwb, nhb = int(wb * size / max(hb, wb)), int(hb * size / max(hb, wb))
        res_b = cv2.resize(raw_b, (nwb, nhb))

        # 4 trailing echo ghosts
        num_echoes = 4
        for i in range(num_echoes):
            echo_p = max(0.0, p - i * 0.08)
            echo_x = int(cx + 300 * (1.0 - ease(echo_p, "out_cubic")))
            echo_alpha = (0.22 / (i + 1)) * min(1.0, echo_p * 2.0)
            echo_patch = res_b.copy()
            echo_patch[:, :, 3] = (echo_patch[:, :, 3].astype(float) * echo_alpha).astype(np.uint8)
            blend_patch(canvas, echo_patch, echo_x - nwb // 2, floor_y - nhb)

        # Main hero instance
        hero_x = int(cx + 300 * (1.0 - ease(p, "out_cubic")))
        blend_patch(canvas, res_b, hero_x - nwb // 2, floor_y - nhb)

        sh_patch = create_ground_shadow(size, alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_19_rotation_spin(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """19. Rotation / Spin Reveal: 3D axial coin flip cleanly reveals B on the reverse face."""
        cw, ch = int(size * 1.5), int(size * 1.5)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        angle = p * 180.0
        if angle < 90.0:
            scale_x = math.cos(math.radians(angle))
            ha, wa = raw_a.shape[:2]
            nw = max(4, int(wa * (size / max(ha, wa)) * scale_x))
            nh = max(4, int(ha * (size / max(ha, wa))))
            res = cv2.resize(raw_a, (nw, nh))
            blend_patch(canvas, res, cx - nw // 2, floor_y - nh)
            cur_w = nw
        else:
            scale_x = math.sin(math.radians(angle - 90.0))
            hb, wb = raw_b.shape[:2]
            nw = max(4, int(wb * (size / max(hb, wb)) * scale_x))
            nh = max(4, int(hb * (size / max(hb, wb))))
            res = cv2.resize(raw_b, (nw, nh))
            blend_patch(canvas, res, cx - nw // 2, floor_y - nh)
            cur_w = nw

        sh_patch = create_ground_shadow(max(size // 3, cur_w), alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas

    @staticmethod
    def render_20_elastic_overshoot(raw_a: np.ndarray, raw_b: np.ndarray, p: float, size: int = 480) -> np.ndarray:
        """20. Elastic / Overshoot Transition: Physical harmonic overshoot bounce and settling."""
        cw, ch = int(size * 1.6), int(size * 1.6)
        canvas = np.zeros((ch, cw, 4), dtype=np.uint8)
        cx, cy = cw // 2, ch // 2
        floor_y = cy + int(size * 0.44)

        # A fades smoothly
        if p < 0.35:
            alpha_a = max(0.0, 1.0 - p / 0.35)
            ha, wa = raw_a.shape[:2]
            nwa, nha = int(wa * size / max(ha, wa)), int(ha * size / max(ha, wa))
            res_a = cv2.resize(raw_a, (nwa, nha))
            res_a[:, :, 3] = (res_a[:, :, 3].astype(float) * alpha_a).astype(np.uint8)
            blend_patch(canvas, res_a, cx - nwa // 2, floor_y - nha)

        # B lands with harmonic damped oscillation
        pb = max(0.0, (p - 0.20) / 0.80)
        # Overshoot spring factor: decays from 1.25 -> 0.95 -> 1.0
        overshoot = 1.0 - math.exp(-6.0 * pb) * math.cos(12.0 * pb)
        hb, wb = raw_b.shape[:2]
        scale_b = (size / max(hb, wb)) * overshoot
        nwb, nhb = max(4, int(wb * scale_b)), max(4, int(hb * scale_b))
        res_b = cv2.resize(raw_b, (nwb, nhb))
        blend_patch(canvas, res_b, cx - nwb // 2, floor_y - nhb)

        sh_patch = create_ground_shadow(int(size * overshoot), alpha=1.0)
        final_canvas = np.zeros_like(canvas)
        blend_patch(final_canvas, sh_patch, cx - sh_patch.shape[1] // 2, floor_y - sh_patch.shape[0] // 2)
        blend_patch(final_canvas, canvas, 0, 0)
        return final_canvas
