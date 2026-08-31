"""
=============================================================================
محرك Whiteboard Animation المتزامن تماماً (Deterministic Sync Engine)
تمت إعادة هيكلة هذا الملف بالكامل للقضاء على مشاكل عدم التزامن (Desynchronization)
والكشف الشبكي العشوائي (Grid-based wipe) وضبط حركة اليد وسن القلم بدقة رياضية 1:1.
=============================================================================
"""

import os
import sys
import time
import math
import json
import datetime
from pathlib import Path
from typing import List, Tuple, Optional

import cv2
import numpy as np

try:
    from kivy.clock import Clock
except ImportError:
    class DummyClock:
        @staticmethod
        def schedule_once(callback, *args, **kwargs):
            try:
                callback(0)
            except Exception:
                pass
    Clock = DummyClock()

# =============================================================================
# إعدادات المسارات العامة ونقاط الارتكاز (Global Anchor & Asset Configuration)
# =============================================================================
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

images_path = os.path.join(base_path, 'data', 'images')
save_path = os.path.join(base_path, "save_videos")
platform = "linux"
progress_updater = None

# [مكان تعديل مسارات صور اليد]:
# يمكنك تغيير المسارات أدناه للإشارة إلى أي صورة يد أخرى ترغب بها
DEFAULT_HAND_PATH = os.path.join(images_path, 'drawing-hand.png')
DEFAULT_HAND_MASK_PATH = os.path.join(images_path, 'hand-mask.png')

# [تحديد نقطة ارتكاز سن القلم - Pen Tip Anchor Point]:
# الإحداثيات (X, Y) داخل صورة اليد الأصلية التي تمثل رأس القلم بالضبط.
# عدّل هذه القيم إذا قمت بتغيير صورة اليد لضمان ملامسة سن القلم لخط الرسم 100%.
PEN_TIP_ANCHOR_X = 62  # إحداثي X لسن القلم في الصورة الأصلية
PEN_TIP_ANCHOR_Y = 40  # إحداثي Y لسن القلم في الصورة الأصلية

# إعدادات الحركة والرسم الافتراضية
DEFAULT_DRAWING_SPEED_PX_SEC = 2800.0  # سرعة حركة القلم السريعة والنشطة (بكسل في الثانية)
DEFAULT_BRUSH_RADIUS = 5               # نصف قطر فرشاة الكشف (سُمك الخط المكشوف)
DEFAULT_HAND_SCALE_HEIGHT = 380        # الارتفاع المناسب لصورة اليد فوق لوحة الرسم


# =============================================================================
# فئة كاتب الفيديو المباشر عالي الجودة (Direct Single-Pass Video Writer)
# =============================================================================
class DirectVideoWriter:
    """
    كاتب فيديو مباشر يتعامل مع PyAV / H.264 بدون الحاجة لإنشاء ملفات وسيطة معطوبة.
    """
    def __init__(self, output_path: str, width: int, height: int, fps: int = 30):
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.use_pyav = True
        self.container = None
        self.stream = None
        self.cv2_writer = None

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        try:
            import av
            self.container = av.open(str(output_path), mode="w")
            codec_name = "h264_nvenc"
            try:
                test_c = av.open(os.devnull, mode="w", format="mp4")
                test_s = test_c.add_stream("h264_nvenc", rate=fps)
                test_c.close()
            except Exception:
                codec_name = "libx264" if platform == "android" else "h264"

            self.stream = self.container.add_stream(codec_name, rate=fps)
            self.stream.width = width
            self.stream.height = height
            self.stream.pix_fmt = "yuv420p"
            self.stream.options = {"crf": "20"}
        except Exception as e:
            print(f"[DirectVideoWriter] PyAV fallback to OpenCV: {e}")
            self.use_pyav = False
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.cv2_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    def write(self, frame_bgr: np.ndarray):
        if self.use_pyav and self.stream and self.container:
            import av
            if frame_bgr.shape[1] != self.width or frame_bgr.shape[0] != self.height:
                frame_bgr = cv2.resize(frame_bgr, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
            video_frame = av.VideoFrame.from_ndarray(frame_bgr, format="bgr24")
            for packet in self.stream.encode(video_frame):
                self.container.mux(packet)
        elif self.cv2_writer:
            if frame_bgr.shape[1] != self.width or frame_bgr.shape[0] != self.height:
                frame_bgr = cv2.resize(frame_bgr, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
            self.cv2_writer.write(frame_bgr)

    def release(self):
        if self.use_pyav and self.stream and self.container:
            try:
                for packet in self.stream.encode():
                    self.container.mux(packet)
                self.container.close()
            except Exception as e:
                print(f"[DirectVideoWriter] Error closing PyAV: {e}")
        elif self.cv2_writer:
            self.cv2_writer.release()


# =============================================================================
# فئة تمثيل نقاط المسار البارامتري (Stroke Point Data Structure)
# =============================================================================
class StrokePoint:
    """تمثل نقطة واحدة على مسار حركة القلم مع حالتها (رسم أم رفع في الهواء)."""
    def __init__(self, x: float, y: float, is_drawing: bool = True):
        self.x = float(x)
        self.y = float(y)
        self.is_drawing = is_drawing


# =============================================================================
# محرك الرندر المتزامن حتمياً (Deterministic Sync Engine)
# =============================================================================
class DeterministicSyncEngine:
    """
    محرك رسم Whiteboard متزامن تماماً (Frame-by-Frame Deterministic Engine).
    
    القاعدة الصارمة:
    "لا يتم كشف أي بكسل في الكانفاس إلا عندما يمر عليه سن القلم في نفس الإطار الزمني بالتمام والكمال."
    """
    def __init__(
        self,
        source_image: np.ndarray,
        hand_image_bgra: np.ndarray,
        pen_tip_anchor: Tuple[int, int] = (PEN_TIP_ANCHOR_X, PEN_TIP_ANCHOR_Y),
        output_fps: int = 30,
        drawing_speed_px_per_sec: float = DEFAULT_DRAWING_SPEED_PX_SEC,
        brush_radius: int = DEFAULT_BRUSH_RADIUS,
        hand_scale_height: int = DEFAULT_HAND_SCALE_HEIGHT
    ):
        self.source_img = source_image.copy()
        self.height, self.width = source_image.shape[:2]
        self.fps = max(1, int(output_fps))
        self.speed = float(drawing_speed_px_per_sec)
        self.brush_radius = max(1, int(brush_radius))
        
        # تجهيز أصل اليد ونقطة الارتكاز المحسوبة بعد التحجيم
        self.hand_bgra, self.tip_x, self.tip_y = self._prepare_hand_asset(
            hand_image_bgra, pen_tip_anchor, hand_scale_height
        )
        self.hand_h, self.hand_w = self.hand_bgra.shape[:2]
        
        # مسبقاً: فصل قنوات اللون والشفافية لحسابات Alpha Blending فائقة السرعة
        self.hand_alpha = (self.hand_bgra[:, :, 3].astype(np.float32) / 255.0)[:, :, np.newaxis]
        self.hand_bgr = self.hand_bgra[:, :, :3].astype(np.float32)
        
        # لوحة الرسم الحالية ومصفوفة الكشف الموضعي
        self.current_canvas = np.full((self.height, self.width, 3), 255, dtype=np.uint8)
        self.step_mask = np.zeros((self.height, self.width), dtype=np.uint8)

    def _prepare_hand_asset(self, raw_hand: np.ndarray, anchor: Tuple[int, int], target_h: int) -> Tuple[np.ndarray, int, int]:
        """قص الحواف الشفافة لليد وتعديل نقطة الارتكاز مع التحجيم المناسب."""
        if raw_hand.shape[2] == 4:
            alpha = raw_hand[:, :, 3]
            coords = np.argwhere(alpha > 10)
            if len(coords) > 0:
                y0, x0 = coords.min(axis=0)
                y1, x1 = coords.max(axis=0) + 1
                cropped = raw_hand[y0:y1, x0:x1]
                raw_anchor_x = max(0, anchor[0] - x0)
                raw_anchor_y = max(0, anchor[1] - y0)
            else:
                cropped = raw_hand
                raw_anchor_x, raw_anchor_y = anchor
        else:
            cropped = cv2.cvtColor(raw_hand, cv2.COLOR_BGR2BGRA)
            raw_anchor_x, raw_anchor_y = anchor

        h_orig, w_orig = cropped.shape[:2]
        scale = target_h / float(h_orig)
        new_w = max(1, int(w_orig * scale))
        new_h = target_h
        resized_hand = cv2.resize(cropped, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        scaled_anchor_x = int(round(raw_anchor_x * scale))
        scaled_anchor_y = int(round(raw_anchor_y * scale))
        
        return resized_hand, scaled_anchor_x, scaled_anchor_y

    def composite_hand(self, background: np.ndarray, tip_target_x: int, tip_target_y: int) -> np.ndarray:
        """دمج اليد (Alpha Blending) مع معالجة آمنة تماماً لحواف الشاشة (Boundary Clipping)."""
        frame = background.copy()
        hx = int(tip_target_x - self.tip_x)
        hy = int(tip_target_y - self.tip_y)
        
        x1_src = max(0, -hx)
        y1_src = max(0, -hy)
        x2_src = min(self.hand_w, self.width - hx)
        y2_src = min(self.hand_h, self.height - hy)
        
        x1_dst = max(0, hx)
        y1_dst = max(0, hy)
        x2_dst = min(self.width, hx + self.hand_w)
        y2_dst = min(self.height, hy + self.hand_h)
        
        if x1_src >= x2_src or y1_src >= y2_src or x1_dst >= x2_dst or y1_dst >= y2_dst:
            return frame
        
        alpha = self.hand_alpha[y1_src:y2_src, x1_src:x2_src]
        hand_bgr = self.hand_bgr[y1_src:y2_src, x1_src:x2_src]
        
        target_roi = frame[y1_dst:y2_dst, x1_dst:x2_dst].astype(np.float32)
        blended = (hand_bgr * alpha + target_roi * (1.0 - alpha)).astype(np.uint8)
        frame[y1_dst:y2_dst, x1_dst:x2_dst] = blended
        return frame

    def interpolate_strokes(self, strokes: List[List[Tuple[float, float]]]) -> List[StrokePoint]:
        """إعادة أخذ العينات للمسارات لتكون متساوية زمنياً مع الـ FPS والسرعة الفيزيائية."""
        timed_points = []
        step_dist = max(1.0, self.speed / self.fps)
        
        for stroke in strokes:
            if len(stroke) == 0:
                continue
            if len(stroke) == 1:
                timed_points.append(StrokePoint(stroke[0][0], stroke[0][1], is_drawing=True))
                continue
            
            timed_points.append(StrokePoint(stroke[0][0], stroke[0][1], is_drawing=True))
            for i in range(1, len(stroke)):
                p0 = np.array(stroke[i - 1], dtype=np.float32)
                p1 = np.array(stroke[i], dtype=np.float32)
                dist = np.linalg.norm(p1 - p0)
                if dist <= 0:
                    continue
                num_substeps = max(1, int(np.ceil(dist / step_dist)))
                for s in range(1, num_substeps + 1):
                    t = min(1.0, (s * step_dist) / dist)
                    interp_p = p0 + t * (p1 - p0)
                    timed_points.append(StrokePoint(interp_p[0], interp_p[1], is_drawing=True))
                    if t >= 1.0:
                        break
        return timed_points

    def _reveal_segment(self, p1: Tuple[int, int], p2: Tuple[int, int]):
        """كشف بكسلات الشريحة المحددة فقط بين النقطتين مع نقل ألوان الصورة الأصلية للكانفاس."""
        x_min = max(0, min(p1[0], p2[0]) - self.brush_radius - 2)
        x_max = min(self.width, max(p1[0], p2[0]) + self.brush_radius + 3)
        y_min = max(0, min(p1[1], p2[1]) - self.brush_radius - 2)
        y_max = min(self.height, max(p1[1], p2[1]) + self.brush_radius + 3)
        
        if x_min >= x_max or y_min >= y_max:
            return
            
        roi_mask = self.step_mask[y_min:y_max, x_min:x_max]
        roi_mask.fill(0)
        
        p1_rel = (p1[0] - x_min, p1[1] - y_min)
        p2_rel = (p2[0] - x_min, p2[1] - y_min)
        
        cv2.line(roi_mask, p1_rel, p2_rel, 255, thickness=self.brush_radius * 2, lineType=cv2.LINE_AA)
        cv2.circle(roi_mask, p2_rel, radius=self.brush_radius, color=255, thickness=-1, lineType=cv2.LINE_AA)
        
        active_idx = np.where(roi_mask > 0)
        if len(active_idx[0]) > 0:
            target_slice = self.current_canvas[y_min:y_max, x_min:x_max]
            source_slice = self.source_img[y_min:y_max, x_min:x_max]
            target_slice[active_idx] = source_slice[active_idx]

    def render_all(
        self,
        strokes: List[List[Tuple[float, float]]],
        video_writer,
        draw_hand: bool = True,
        end_hold_sec: float = 2.0,
        progress_callback = None
    ):
        """الحلقة الرئيسية لإنتاج الفيديو: كتابة إطار متزامن 1:1 لكل نقطة في المسار الزمني."""
        timed_points = self.interpolate_strokes(strokes)
        total_pts = len(timed_points)
        if total_pts == 0:
            for _ in range(int(round(end_hold_sec * self.fps))):
                video_writer.write(self.source_img)
            return

        last_pt = timed_points[0]
        p0 = (int(round(last_pt.x)), int(round(last_pt.y)))
        self._reveal_segment(p0, p0)

        # 1. حلقة الرسم المتزامنة خطوة بخطوة
        for idx, pt in enumerate(timed_points):
            p1 = (int(round(last_pt.x)), int(round(last_pt.y)))
            p2 = (int(round(pt.x)), int(round(pt.y)))
            
            if pt.is_drawing:
                self._reveal_segment(p1, p2)
            
            if draw_hand:
                frame_out = self.composite_hand(self.current_canvas, p2[0], p2[1])
            else:
                frame_out = self.current_canvas.copy()

            video_writer.write(frame_out)
            last_pt = pt
            
            if progress_callback and idx % 30 == 0:
                progress_pct = (idx / float(total_pts)) * 85.0
                try:
                    Clock.schedule_once(lambda dt, p=progress_pct: progress_callback(p))
                except Exception:
                    progress_callback(progress_pct)

        # 2. انزلاق وخروج اليد بسلاسة خارج الشاشة بعد انتهاء الرسم (Smooth Hand Exit)
        if draw_hand and total_pts > 0:
            exit_frames = max(1, int(0.4 * self.fps))
            start_x, start_y = last_pt.x, last_pt.y
            end_x = self.width + self.tip_x + 50
            end_y = self.height + self.tip_y + 50
            
            for ef in range(1, exit_frames + 1):
                t = ef / float(exit_frames)
                ease_t = t * t
                curr_x = start_x + (end_x - start_x) * ease_t
                curr_y = start_y + (end_y - start_y) * ease_t
                frame_exit = self.composite_hand(self.current_canvas, int(round(curr_x)), int(round(curr_y)))
                video_writer.write(frame_exit)

        # 3. انسياب وظهور الألوان بتلاشٍ ناعم (Watercolor Bloom Fade)
        render_color_alpha_fade(
            canvas_with_lines=self.current_canvas,
            source_color_img=self.source_img,
            video_writer=video_writer,
            fps=self.fps,
            fade_duration_sec=0.6
        )

        # 4. تثبيت الصورة النهائية الكاملة بدون يد للمدة المحددة (End Hold)
        hold_frames = int(round(end_hold_sec * self.fps))
        for _ in range(hold_frames):
            video_writer.write(self.source_img)

        if progress_callback:
            try:
                Clock.schedule_once(lambda dt: progress_callback(100.0))
            except Exception:
                progress_callback(100.0)


def is_outer_frame_contour(cnt, img_w: int, img_h: int, margin_ratio: float = 0.15, coverage_ratio: float = 0.70) -> bool:
    """
    يكتشف ما إذا كان الكونتور هو الإطار الخارجي المستطيل للمشهد لتجنب رسمه.
    """
    x, y, w, h = cv2.boundingRect(cnt)
    covers_box = (w > coverage_ratio * img_w) and (h > coverage_ratio * img_h)
    near_edge = (x < margin_ratio * img_w) and (y < margin_ratio * img_h)
    return covers_box or (covers_box and near_edge)


def extract_strokes_from_image(
    img_bgr: np.ndarray,
    detail_threshold: int = 50,
    min_stroke_len: float = 14.0,
    filter_outer_frame: bool = True
) -> List[List[Tuple[float, float]]]:
    """
    استخراج الحواف والخطوط من الصورة وتنعيمها وترتيبها هندسياً لتقليل قفزات اليد العشوائية،
    مع استبعاد الإطار الخارجي المحيط بالشخصية تلقائياً.
    """
    img_h, img_w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.bilateralFilter(gray, 7, 50, 50)
    edges = cv2.Canny(blurred, detail_threshold, detail_threshold * 3)
    
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_KCOS)
    
    raw_strokes = []
    for cnt in contours:
        if cv2.arcLength(cnt, False) < min_stroke_len:
            continue
        # استبعاد الإطار الخارجي المحيط باللوحة
        if filter_outer_frame and is_outer_frame_contour(cnt, img_w, img_h):
            continue
        pts = cnt.reshape(-1, 2).tolist()
        raw_strokes.append(pts)
        
    if not raw_strokes:
        return generate_mock_demo_path(img_bgr.shape[1], img_bgr.shape[0])
        
    # ترتيب المسارات باستخدام Nearest Neighbor Chaining
    sorted_strokes = [raw_strokes.pop(0)]
    while raw_strokes:
        last_pt = np.array(sorted_strokes[-1][-1])
        closest_idx = 0
        min_dist = 1e9
        for i, s in enumerate(raw_strokes):
            d = np.linalg.norm(np.array(s[0]) - last_pt)
            if d < min_dist:
                min_dist = d
                closest_idx = i
        sorted_strokes.append(raw_strokes.pop(closest_idx))
        
    # تنعيم كافة المسارات بـ B-Splines لإزالة أي تعرجات أو تكسرات بكسلية
    smoothed_strokes = smooth_all_strokes(sorted_strokes)
    return smoothed_strokes


def render_color_alpha_fade(
    canvas_with_lines: np.ndarray,
    source_color_img: np.ndarray,
    video_writer,
    fps: int = 30,
    fade_duration_sec: float = 0.6
):
    """
    تطبيق تأثير انسياب الألوان (Watercolor Bloom Fade) تدريجياً داخل الورقة.
    """
    total_frames = max(1, int(fade_duration_sec * fps))
    lines_float = canvas_with_lines.astype(np.float32)
    color_float = source_color_img.astype(np.float32)

    for frame_idx in range(1, total_frames + 1):
        t = frame_idx / float(total_frames)
        alpha = t * t * (3.0 - 2.0 * t)
        blended_frame = (lines_float * (1.0 - alpha) + color_float * alpha).astype(np.uint8)
        video_writer.write(blended_frame)


def smooth_stroke_bspline(
    raw_points: List[Tuple[float, float]],
    smoothing_factor: float = 2.5,
    approx_epsilon: float = 1.2
) -> List[Tuple[float, float]]:
    """
    تنعيم مسار خطي منفرد باستخدام تقريب المضلعات ثم منحنيات B-Splines البارامترية.
    """
    if len(raw_points) < 4:
        return raw_points

    pts_arr = np.array(raw_points, dtype=np.float32)

    # 1. إزالة النقاط المكررة المتتالية
    valid_mask = np.ones(len(pts_arr), dtype=bool)
    valid_mask[1:] = np.any(pts_arr[1:] != pts_arr[:-1], axis=1)
    pts_arr = pts_arr[valid_mask]

    if len(pts_arr) < 4:
        return raw_points

    # 2. تنظيف تكسرات البكسلات عبر approxPolyDP
    pts_contour = pts_arr.reshape(-1, 1, 2).astype(np.float32)
    simplified = cv2.approxPolyDP(pts_contour, approx_epsilon, closed=False).reshape(-1, 2)

    if len(simplified) < 4:
        simplified = pts_arr

    x = simplified[:, 0]
    y = simplified[:, 1]

    # 3. ملاءمة منحنى B-Spline من الدرجة الثالثة (Cubic Spline k=3)
    k_degree = min(3, len(simplified) - 1)
    try:
        from scipy.interpolate import splprep, splev
        chord_length = np.sum(np.linalg.norm(simplified[1:] - simplified[:-1], axis=1))
        num_samples = max(len(simplified), int(chord_length / 2.0))

        tck, u = splprep([x, y], s=smoothing_factor * len(simplified), k=k_degree)
        u_fine = np.linspace(0.0, 1.0, num_samples)
        x_smooth, y_smooth = splev(u_fine, tck)

        return list(zip(x_smooth, y_smooth))
    except Exception:
        return simplified.tolist()


def smooth_all_strokes(strokes: List[List[Tuple[float, float]]]) -> List[List[Tuple[float, float]]]:
    """تطبيق التنعيم على كافة مسارات الصورة."""
    smoothed_list = []
    for stroke in strokes:
        if len(stroke) >= 4:
            smoothed_list.append(smooth_stroke_bspline(stroke))
        else:
            smoothed_list.append(stroke)
    return smoothed_list


def generate_mock_demo_path(width: int, height: int) -> List[List[Tuple[float, float]]]:
    """مسار تجريبي بارامتري (Mock Path) لاختبار تزامن المحرك بشكل مستقل."""
    cx, cy = width / 2.0, height / 2.0
    spiral_points = []
    for theta in np.linspace(0, 10 * np.pi, 300):
        r = (theta / (10 * np.pi)) * min(cx, cy) * 0.7
        x = cx + r * np.cos(theta)
        y = cy + r * np.sin(theta)
        spiral_points.append((float(x), float(y)))
    return [spiral_points]


# =============================================================================
# دوال التوافق والمساعدات (Compatibility Layer & Helper Functions)
# =============================================================================
def read_image_unicode(img_path) -> Optional[np.ndarray]:
    """قراءة الصور بأمان حتى لو كانت المسارات تحتوي على أحرف عربية أو مسافات."""
    if isinstance(img_path, np.ndarray):
        return img_path
    if not os.path.exists(str(img_path)):
        return None
    bytes_data = np.fromfile(str(img_path), dtype=np.uint8)
    return cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)


def load_hand_asset_bgra(hand_path: str, hand_mask_path: Optional[str] = None) -> np.ndarray:
    """تحميل أصل اليد مع دعم قنوات Alpha أو القناع المنفصل."""
    hand_bgra = cv2.imread(hand_path, cv2.IMREAD_UNCHANGED)
    
    if hand_bgra is None:
        print(f"Warning: Hand image not found at {hand_path}. Creating fallback hand.")
        h_fb = np.zeros((400, 300, 4), dtype=np.uint8)
        h_fb[:, :, :3] = (40, 40, 40)
        h_fb[:, :, 3] = 255
        return h_fb

    if hand_bgra.shape[2] == 3 and hand_mask_path and os.path.exists(hand_mask_path):
        mask = cv2.imread(hand_mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is not None:
            if mask.shape[:2] != hand_bgra.shape[:2]:
                mask = cv2.resize(mask, (hand_bgra.shape[1], hand_bgra.shape[0]))
            b, g, r = cv2.split(hand_bgra)
            hand_bgra = cv2.merge([b, g, r, mask])
    elif hand_bgra.shape[2] == 3:
        hand_bgra = cv2.cvtColor(hand_bgra, cv2.COLOR_BGR2BGRA)

    return hand_bgra


def resize_with_padding(img: np.ndarray, target_width: int, target_height: int, color=(255, 255, 255)) -> np.ndarray:
    h, w = img.shape[:2]
    scale = min(target_width / float(w), target_height / float(h))
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    pad_w = target_width - new_w
    pad_h = target_height - new_h
    top = pad_h // 2
    bottom = pad_h - top
    left = pad_w // 2
    right = pad_w - left
    
    return cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)


def find_nearest_res(given: int) -> int:
    arr = np.array([640, 360, 480, 1280, 720, 1920, 1080, 2560, 1440, 3840, 2160])
    idx = (np.abs(arr - given)).argmin()
    return int(arr[idx])


def common_divisors(num1: int, num2: int) -> List[int]:
    divs = [i for i in range(1, min(num1, num2) + 1) if num1 % i == 0 and num2 % i == 0]
    return sorted(divs)


def get_split_lens(image_path: str, max_1080p: bool = True):
    final_return = {"image_res": [1280, 720], "split_lens": [10, 15, 20]}
    try:
        img = read_image_unicode(image_path)
        if img is None:
            return final_return
        h, w = img.shape[:2]
        if max_1080p and (h > 1920 or w > 1920):
            if w > h:
                w, h = 1920, 1080
            else:
                w, h = 1080, 1920
        else:
            aspect = w / float(h)
            h = find_nearest_res(h)
            w = find_nearest_res(int(h * aspect))
        final_return["image_res"] = [w, h]
        final_return["split_lens"] = common_divisors(h, w)
    except Exception as e:
        print(f"Error in get_split_lens: {e}")
    return final_return


class AllVariables:
    """فئة نقل المتغيرات القديمة (محفوظة بالكامل لتوافق الواجهة)."""
    def __init__(
        self,
        frame_rate=30,
        resize_wd=1280,
        resize_ht=720,
        split_len=10,
        object_skip_rate=5,
        bg_object_skip_rate=10,
        end_gray_img_duration_in_sec=2,
        draw_hand=True,
    ):
        self.frame_rate = frame_rate
        self.resize_wd = resize_wd
        self.resize_ht = resize_ht
        self.split_len = split_len
        self.object_skip_rate = object_skip_rate
        self.bg_object_skip_rate = bg_object_skip_rate
        self.end_gray_img_duration_in_sec = end_gray_img_duration_in_sec
        self.draw_hand = draw_hand
        self.video_object = None


def ffmpeg_convert(source_vid: str, dest_vid: str, platform: str = "linux") -> bool:
    """دالة تحويل خارجية في حال تم استدعاؤها من سكربتات قديمة."""
    try:
        import av
        src_path = Path(source_vid)
        input_container = av.open(str(src_path), mode="r")
        output_container = av.open(str(dest_vid), mode="w")
        
        in_stream = input_container.streams.video[0]
        fps = in_stream.average_rate
        codec_name = "libx264" if platform == "android" else "h264"
        
        out_stream = output_container.add_stream(codec_name, rate=fps)
        out_stream.width = in_stream.codec_context.width
        out_stream.height = in_stream.codec_context.height
        out_stream.pix_fmt = "yuv420p"
        out_stream.options = {"crf": "20"}
        
        for frame in input_container.decode(video=0):
            for packet in out_stream.encode(frame):
                output_container.mux(packet)
        for packet in out_stream.encode(None):
            output_container.mux(packet)
            
        output_container.close()
        input_container.close()
        return True
    except Exception as e:
        print(f"FFmpeg conversion fallback/error: {e}")
        return False


# =============================================================================
# دوال التنفيذ الرئيسية (Main Execution Pipelines)
# =============================================================================
def draw_whiteboard_animations(
    img: np.ndarray,
    mask_path: Optional[str],
    hand_path: str,
    hand_mask_path: Optional[str],
    save_video_path: str,
    variables: AllVariables,
    end_color: bool = True,
    progress_callback = None
):
    """
    [تم التحديث بالكامل]: استبدال الخوارزمية الشبكية القديمة بمحرك التزامن البارامتري.
    """
    hand_bgra = load_hand_asset_bgra(hand_path, hand_mask_path)
    strokes = extract_strokes_from_image(img)
    
    writer = DirectVideoWriter(
        output_path=save_video_path,
        width=int(variables.resize_wd),
        height=int(variables.resize_ht),
        fps=int(variables.frame_rate)
    )
    
    engine = DeterministicSyncEngine(
        source_image=img,
        hand_image_bgra=hand_bgra,
        pen_tip_anchor=(PEN_TIP_ANCHOR_X, PEN_TIP_ANCHOR_Y),
        output_fps=variables.frame_rate,
        drawing_speed_px_per_sec=DEFAULT_DRAWING_SPEED_PX_SEC,
        brush_radius=DEFAULT_BRUSH_RADIUS,
        hand_scale_height=DEFAULT_HAND_SCALE_HEIGHT
    )
    
    engine.render_all(
        strokes=strokes,
        video_writer=writer,
        draw_hand=variables.draw_hand,
        end_hold_sec=float(variables.end_gray_img_duration_in_sec),
        progress_callback=progress_callback
    )
    
    writer.release()


def initiate_sketch(
    image_path: str,
    split_len: int,
    frame_rate: int,
    object_skip_rate: int,
    bg_object_skip_rate: int,
    main_img_duration: float,
    callback,
    save_path: str = save_path,
    which_platform: str = "linux",
    end_color: bool = True,
    draw_hand: bool = True,
    max_1080p: bool = True,
    progress_callback = None
):
    """
    نقطة الدخول الرئيسية المتوافقة مع واجهة المستخدم (Kivy UI) وخيوط المعالجة في الخلفية.
    """
    global platform
    platform = which_platform
    final_result = {"status": False, "message": "Initial load"}
    
    try:
        image_bgr = read_image_unicode(image_path)
        if image_bgr is None:
            raise FileNotFoundError(f"Cannot read image at: {image_path}")

        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        final_mp4_path = os.path.join(save_path, f"sketch_{timestamp}.mp4")
        os.makedirs(save_path, exist_ok=True)

        img_ht, img_wd = image_bgr.shape[:2]
        if max_1080p and (img_ht > 1920 or img_wd > 1920):
            if img_wd > img_ht:
                target_w, target_h = 1920, 1080
            else:
                target_w, target_h = 1080, 1920
            image_bgr = resize_with_padding(image_bgr, target_w, target_h)
        else:
            aspect = img_wd / float(img_ht)
            target_h = find_nearest_res(img_ht)
            target_w = find_nearest_res(int(target_h * aspect))
            image_bgr = cv2.resize(image_bgr, (target_w, target_h), interpolation=cv2.INTER_AREA)

        variables = AllVariables(
            frame_rate=frame_rate,
            resize_wd=image_bgr.shape[1],
            resize_ht=image_bgr.shape[0],
            split_len=split_len,
            object_skip_rate=object_skip_rate,
            bg_object_skip_rate=bg_object_skip_rate,
            end_gray_img_duration_in_sec=main_img_duration,
            draw_hand=draw_hand
        )

        draw_whiteboard_animations(
            img=image_bgr,
            mask_path=None,
            hand_path=DEFAULT_HAND_PATH,
            hand_mask_path=DEFAULT_HAND_MASK_PATH,
            save_video_path=final_mp4_path,
            variables=variables,
            end_color=end_color,
            progress_callback=progress_callback
        )

        final_result = {"status": True, "message": final_mp4_path}

    except Exception as e:
        print(f"Error in initiate_sketch: {e}")
        final_result = {"status": False, "message": f"Error: {e}"}

    try:
        Clock.schedule_once(lambda dt: callback(final_result))
    except Exception:
        callback(final_result)


def merge_nearby_punctuation(entities: List[dict], q_img: Optional[np.ndarray] = None, max_gap: int = 14) -> List[dict]:
    """دمج علامات الترقيم والنقاط التابعة لنفس علامة التعجب أو الحرف وتحديث أبعاد الـ Crop والـ Mask."""
    if len(entities) <= 1:
        return entities

    merged = []
    used = set()

    for i in range(len(entities)):
        if i in used:
            continue
        cur = dict(entities[i])
        bx1, by1 = cur["rel_x"], cur["rel_y"]
        bx2, by2 = bx1 + cur["w"], by1 + cur["h"]
        has_merged = False

        for j in range(i + 1, len(entities)):
            if j in used:
                continue
            other = entities[j]
            ox1, oy1 = other["rel_x"], other["rel_y"]
            ox2, oy2 = ox1 + other["w"], oy1 + other["h"]

            x_dist = max(0, max(bx1, ox1) - min(bx2, ox2))
            y_dist = max(0, max(by1, oy1) - min(by2, oy2))

            # دمج النقطة بالخط التابع لها مباشرة (فارق أفقي <= 2px وفارق رأسي <= 14px)
            if x_dist <= 2 and y_dist <= max_gap and cur["area"] < 1500 and other["area"] < 1500:
                used.add(j)
                has_merged = True
                nbx1 = min(bx1, ox1)
                nby1 = min(by1, oy1)
                nbx2 = max(bx2, ox2)
                nby2 = max(by2, oy2)
                nbw = nbx2 - nbx1
                nbh = nby2 - nby1

                bx1, by1, bx2, by2 = nbx1, nby1, nbx2, nby2
                cur["rel_x"] = nbx1
                cur["rel_y"] = nby1
                cur["w"] = nbw
                cur["h"] = nbh
                cur["center_x"] = nbx1 + nbw / 2.0
                cur["center_y"] = nby1 + nbh / 2.0
                cur["area"] += other["area"]

        if has_merged and q_img is not None:
            cur_crop = q_img[cur["rel_y"]:cur["rel_y"]+cur["h"], cur["rel_x"]:cur["rel_x"]+cur["w"]].copy()
            cur_mask = (cv2.cvtColor(cur_crop, cv2.COLOR_BGR2GRAY) < 235).astype(np.uint8) * 255
            cur["crop"] = cur_crop
            cur["mask"] = cur_mask

        merged.append(cur)
    return merged


def sort_panel_entities(entities: List[dict], q_img: Optional[np.ndarray] = None) -> List[dict]:
    """
    ترتيب العناصر داخل المربع/اللوحة بذكاء:
    1. إذا كانت هناك شخصية رئيسية وعلامات رد فعل/تعجب فوقها -> ترسم الشخصية أولاً، ثم علامات التعجب من اليسار لليمين بالتسلسل!
    2. إذا كانت العناصر أفقية جنباً إلى جنب -> من اليسار إلى اليمين دائماً (Left-to-Right).
    3. إذا كانت هناك شخصية/عنصر فوق أخرى (عمودية) -> من الأعلى إلى الأسفل (Top-to-Bottom).
    """
    if len(entities) <= 1:
        return entities

    entities = merge_nearby_punctuation(entities, q_img=q_img)

    # التحقق من وجود شخصية رئيسية وعلامات تعجب/رد فعل علوية
    max_area = max(e["area"] for e in entities)
    if max_area >= 2000:
        main_chars = [e for e in entities if e["area"] >= max(1200, max_area * 0.20)]
        reaction_marks = [e for e in entities if e not in main_chars]

        if reaction_marks:
            sorted_chars = sorted(main_chars, key=lambda e: (e["rel_x"]))
            sorted_reactions = sorted(reaction_marks, key=lambda e: e["rel_x"])
            return sorted_chars + sorted_reactions

    import functools

    def compare_entities(a, b):
        ax, ay, aw, ah = a["rel_x"], a["rel_y"], a["w"], a["h"]
        bx, by, bw, bh = b["rel_x"], b["rel_y"], b["w"], b["h"]

        # تداخل المحور الأفقي X
        x_overlap = max(0, min(ax + aw, bx + bw) - max(ax, bx))
        min_w = max(1, min(aw, bw))
        x_overlap_ratio = x_overlap / float(min_w)

        # تداخل المحور الرأسي Y
        y_overlap = max(0, min(ay + ah, by + bh) - max(ay, by))
        min_h = max(1, min(ah, bh))
        y_overlap_ratio = y_overlap / float(min_h)

        # الحالة 1: العناصر مكدسة عمودياً فوق بعضها (تداخل أفقي كبير وتفارق رأسي)
        if x_overlap_ratio > 0.30 and y_overlap_ratio < 0.40:
            return -1 if ay < by else 1

        # الحالة 2: العناصر متجاورة أفقياً (تداخل رأسي وتفارق أفقي) -> اليسار أولاً
        if y_overlap_ratio > 0.30 and x_overlap_ratio < 0.40:
            return -1 if ax < bx else 1

        # الحالة 3: ترتيب شبكي عام: الصف العلوي يسبق السفلي إذا كان الفارق واضحاً، وإلا اليسار يسبق اليمين
        if (ay + ah * 0.5) + (min_h * 0.5) < (by + bh * 0.5):
            return -1
        elif (by + bh * 0.5) + (min_h * 0.5) < (ay + ah * 0.5):
            return 1
        else:
            return -1 if ax < bx else 1

    return sorted(entities, key=functools.cmp_to_key(compare_entities))


# =============================================================================
# محرك الرندر البيضاوي المتراكز 360 درجة للشاشات العريضة (16:9 Pro Whiteboard Engine)
# =============================================================================
def extract_storyboard_panels_and_entities(source_img: np.ndarray, min_entity_area: int = 50) -> List[dict]:
    """
    تقسيم الستوري بورد ديناميكياً (1، 2، 4، 6+ لوحات) واستخراج كافة الشخصيات والكيانات النقية بدون استثناء.
    """
    h, w = source_img.shape[:2]
    
    try:
        from engine.processing.panel_detector import PanelDetector
        project = PanelDetector.detect(source_img)
        if project.structure_type.is_storyboard and len(project.panels) >= 2:
            panels_list = [p for p in project.panels if not p.is_empty]
            if not panels_list:
                panels_list = project.panels
            panels_list.sort(key=lambda p: (p.bbox[1] // 50, p.bbox[0]))
            panel_rois = []
            for idx, p in enumerate(panels_list):
                px, py, pw, ph = p.interior_bbox
                panel_rois.append((f"Panel {idx+1}", px, py, pw, ph))
        else:
            panel_rois = [("Scene 1", 0, 0, w, h)]
    except Exception:
        mid_y, mid_x = h // 2, w // 2
        panel_rois = [
            ("Panel 1", 0, 0, mid_x, mid_y),
            ("Panel 2", mid_x, 0, w - mid_x, mid_y),
            ("Panel 3", 0, mid_y, mid_x, h - mid_y),
            ("Panel 4", mid_x, mid_y, w - mid_x, h - mid_y)
        ]

    panel_data = []

    for p_name, px, py, pw, ph in panel_rois:
        px = max(0, min(w - 1, px))
        py = max(0, min(h - 1, py))
        pw = max(4, min(w - px, pw))
        ph = max(4, min(h - py, ph))

        q_img = source_img[py:py+ph, px:px+pw]
        qh, qw = q_img.shape[:2]
        gray = cv2.cvtColor(q_img, cv2.COLOR_BGR2GRAY)
        non_white = (gray < 235).astype(np.uint8)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(non_white)

        raw_entities = []
        for label in range(1, num_labels):
            bx = stats[label, cv2.CC_STAT_LEFT]
            by = stats[label, cv2.CC_STAT_TOP]
            bw = stats[label, cv2.CC_STAT_WIDTH]
            bh = stats[label, cv2.CC_STAT_HEIGHT]
            area = stats[label, cv2.CC_STAT_AREA]

            # استبعاد شرائح الحواف المتبقية فقط
            is_edge_sliver = (bw < 6 and (bx == 0 or bx + bw >= qw)) or (bh < 6 and (by == 0 or by + bh >= qh))
            if is_edge_sliver:
                continue

            if area < min_entity_area:
                continue

            ent_mask = (labels == label).astype(np.uint8) * 255
            ent_crop = np.full((bh, bw, 3), 255, dtype=np.uint8)
            ent_crop_mask = ent_mask[by:by+bh, bx:bx+bw]
            ent_crop[ent_crop_mask > 0] = q_img[by:by+bh, bx:bx+bw][ent_crop_mask > 0]

            raw_entities.append({
                "label": label,
                "rel_x": bx, "rel_y": by,
                "w": bw, "h": bh,
                "center_x": bx + bw / 2.0,
                "center_y": by + bh / 2.0,
                "area": area,
                "crop": ent_crop,
                "mask": ent_crop_mask
            })

        raw_entities = sort_panel_entities(raw_entities, q_img=q_img)

        # إنشاء لوحة نقية تحتوي كافة الكيانات فقط بدون إطار المربع
        clean_panel_canvas = np.full((qh, qw, 3), 255, dtype=np.uint8)
        for e in raw_entities:
            ebx, eby = e["rel_x"], e["rel_y"]
            ebw, ebh = e["w"], e["h"]
            mask = e["mask"]
            clean_panel_canvas[eby:eby+ebh, ebx:ebx+ebw][mask > 0] = e["crop"][mask > 0]

        all_active_y, all_active_x = np.where(cv2.cvtColor(clean_panel_canvas, cv2.COLOR_BGR2GRAY) < 235)
        if len(all_active_x) > 0 and len(all_active_y) > 0:
            min_px, max_px = int(all_active_x.min()), int(all_active_x.max())
            min_py, max_py = int(all_active_y.min()), int(all_active_y.max())
            panel_crop_tight = clean_panel_canvas[min_py:max_py+1, min_px:max_px+1]
            panel_offset_x = min_px
            panel_offset_y = min_py
        else:
            panel_crop_tight = clean_panel_canvas
            panel_offset_x = 0
            panel_offset_y = 0

        panel_data.append({
            "panel_name": p_name,
            "entities": raw_entities,
            "panel_crop": panel_crop_tight,
            "offset_x": panel_offset_x,
            "offset_y": panel_offset_y
        })

    return panel_data


def build_gapless_orbital_path(
    pure_entity_bgr: np.ndarray,
    ring_step: int = 5,
    sample_interval: float = 3.0,
    brush_radius: int = 8,
    drawing_direction: str = "OUTSIDE_IN"
) -> list:
    """
    بناء مسار دوران متراكز 360 درجة بدون فراغات وتوقف فوري عند 100%.
    - OUTSIDE_IN (من الخارج للداخل): يبدأ من المحيط الخارجي ويلتف نحو المركز الداخلي.
    - INSIDE_OUT (من الداخل للخارج): يبدأ من أعمق نقطة بالمركز ويتسع تدريجياً للخارج.
    """
    if pure_entity_bgr is None or pure_entity_bgr.size == 0:
        return []
    h, w = pure_entity_bgr.shape[:2]
    if h <= 2 or w <= 2:
        return []

    gray = cv2.cvtColor(pure_entity_bgr, cv2.COLOR_BGR2GRAY)
    body_mask = (gray < 240).astype(np.uint8) * 255
    if np.count_nonzero(body_mask) < 5:
        return []

    dist = cv2.distanceTransform(body_mask, cv2.DIST_L2, 5)
    max_d = float(np.max(dist))
    if max_d <= 1.0 or np.isnan(max_d) or np.isinf(max_d) or max_d > 5000.0:
        return []

    step = max(1.0, float(ring_step))
    d_levels = np.arange(1.0, max_d + 1.0, step)
    sim_drawn = np.zeros_like(body_mask)
    dense_laps = []

    for d in d_levels:
        level_mask = (dist >= d).astype(np.uint8) * 255
        cnts, _ = cv2.findContours(level_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        for cnt in cnts:
            if len(cnt) < 2:
                continue
            pts = cnt.reshape(-1, 2)
            diffs = pts[1:] - pts[:-1]
            seg_lens = np.linalg.norm(diffs, axis=1)
            cum_lens = np.zeros(len(pts))
            cum_lens[1:] = np.cumsum(seg_lens)
            total_l = cum_lens[-1]
            if total_l <= 0:
                continue

            num_s = max(2, int(total_l / sample_interval))
            sample_dists = np.linspace(0, total_l, num_s)
            new_x = np.interp(sample_dists, cum_lens, pts[:, 0])
            new_y = np.interp(sample_dists, cum_lens, pts[:, 1])
            resampled = np.column_stack([new_x, new_y]).tolist()
            if resampled[0] != resampled[-1]:
                resampled.append(resampled[0])
            dense_laps.append((d, resampled))

            for p in resampled:
                cv2.circle(sim_drawn, (int(round(p[0])), int(round(p[1]))), radius=brush_radius, color=255, thickness=-1)

        unvisited = (body_mask > 0) & (sim_drawn == 0)
        if np.sum(unvisited) == 0:
            break

    # فرز الحلقات بناءً على الاتجاه المختار (من الداخل للخارج أو من الخارج للداخل)
    is_inside_out = str(drawing_direction).upper() in ("INSIDE_OUT", "INSIDEOUT", "INSIDE_TO_OUT")
    if is_inside_out:
        dense_laps.sort(key=lambda item: -item[0])
    else:
        dense_laps.sort(key=lambda item: item[0])

    master_sequence = []
    last_pt = None

    for d, lap in dense_laps:
        if last_pt is not None:
            pts_arr = np.array(lap[:-1])
            dists = np.linalg.norm(pts_arr - np.array(last_pt), axis=1)
            best_idx = int(np.argmin(dists))
            full_360_lap = lap[best_idx:-1] + lap[:best_idx] + [lap[best_idx]]
            master_sequence.append(full_360_lap)
            last_pt = full_360_lap[-1]
        else:
            master_sequence.append(lap)
            last_pt = lap[-1]

    return master_sequence


def render_camera_viewport(canvas: np.ndarray, center_x: float, center_y: float, zoom_scale: float, out_w: int = 1920, out_h: int = 1080) -> np.ndarray:
    """تحويل الكاميرا الافتراضية بدقة بالغة."""
    vw = out_w / zoom_scale
    vh = out_h / zoom_scale

    x1 = center_x - vw / 2.0
    y1 = center_y - vh / 2.0
    x2 = center_x + vw / 2.0
    y2 = center_y + vh / 2.0

    src_pts = np.float32([[x1, y1], [x2, y1], [x1, y2]])
    dst_pts = np.float32([[0, 0], [out_w, 0], [0, out_h]])
    matrix = cv2.getAffineTransform(src_pts, dst_pts)
    return cv2.warpAffine(canvas, matrix, (out_w, out_h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))


def composite_hand_on_canvas_fast(canvas: np.ndarray, hand_bgra: np.ndarray, tip_x_anchor: int, tip_y_anchor: int, target_x: int, target_y: int) -> np.ndarray:
    """دمج اليد فوق الكانفاس بأمان وسرعة."""
    frame = canvas.copy()
    hh, hw = hand_bgra.shape[:2]
    cw, ch = canvas.shape[1], canvas.shape[0]

    hx = int(target_x - tip_x_anchor)
    hy = int(target_y - tip_y_anchor)

    x1_src = max(0, -hx)
    y1_src = max(0, -hy)
    x2_src = min(hw, cw - hx)
    y2_src = min(hh, ch - hy)

    x1_dst = max(0, hx)
    y1_dst = max(0, hy)
    x2_dst = min(cw, hx + hw)
    y2_dst = min(ch, hy + hh)

    if x1_src >= x2_src or y1_src >= y2_src or x1_dst >= x2_dst or y1_dst >= y2_dst:
        return frame

    hand_crop = hand_bgra[y1_src:y2_src, x1_src:x2_src]
    alpha = (hand_crop[:, :, 3].astype(np.float32) / 255.0)[:, :, np.newaxis]
    hand_bgr = hand_crop[:, :, :3].astype(np.float32)
    target_roi = frame[y1_dst:y2_dst, x1_dst:x2_dst].astype(np.float32)

    blended = (hand_bgr * alpha + target_roi * (1.0 - alpha)).astype(np.uint8)
    frame[y1_dst:y2_dst, x1_dst:x2_dst] = blended
    return frame


def render_concentric_orbital_whiteboard(
    image_input,
    output_path: str,
    fps: int = 30,
    drawing_speed: float = 1.5,
    camera_zoom_scale: float = 2.0,
    element_spacing: int = 24,
    drawing_direction: str = "OUTSIDE_IN",
    ring_step: int = 5,
    brush_radius: int = 8,
    sample_interval: float = 3.0,
    show_hand: bool = True,
    hand_scale: float = 0.75,
    end_hold_seconds: float = 1.5,
    custom_objects: list = None,
    progress_callback = None
):
    """
    الدالة الرئيسية للرندر الاحترافي بدقة 16:9 Widescreen مع الاستخراج الذكي للكيانات المتعددة والدوران 360°.
    تتيح التحكم الكامل في سرعة الرسم ومستوى تقريب الكاميرا والمسافات وترتيب العناصر.
    """
    if isinstance(image_input, str):
        img = read_image_unicode(image_input)
    else:
        img = image_input

    if img is None:
        raise ValueError("Cannot load input image.")

    h_img, w_img = img.shape[:2]

    # إذا مرر المستخدم قائمة عناصر مرتبة أو معدلة يدوياً
    if custom_objects and len(custom_objects) > 0:
        active_objs = [o for o in custom_objects if getattr(o, "visibility", True)]
        if not active_objs:
            active_objs = custom_objects

        panels_order = []
        panels_map = {}
        for idx, obj in enumerate(active_objs):
            pid = getattr(obj, "panel_id", idx + 1)
            if pid not in panels_map:
                panels_map[pid] = []
                panels_order.append(pid)
            panels_map[pid].append(obj)

        panel_data = []
        for p_idx, pid in enumerate(panels_order):
            p_objs = panels_map[pid]
            all_bboxes = [getattr(o, "global_bbox", None) or getattr(o, "bbox", (0, 0, 0, 0)) for o in p_objs]
            min_gx = max(0, min(b[0] for b in all_bboxes))
            min_gy = max(0, min(b[1] for b in all_bboxes))
            max_gx = min(w_img, max(b[0] + b[2] for b in all_bboxes))
            max_gy = min(h_img, max(b[1] + b[3] for b in all_bboxes))
            pw_actual = max(4, max_gx - min_gx)
            ph_actual = max(4, max_gy - min_gy)

            p_crop_combined = img[min_gy:max_gy, min_gx:max_gx].copy()

            p_entities = []
            for e_idx, obj in enumerate(p_objs):
                gbx, gby, gbw, gbh = getattr(obj, "global_bbox", None) or getattr(obj, "bbox", (0, 0, 0, 0))
                rel_x = max(0, gbx - min_gx)
                rel_y = max(0, gby - min_gy)
                cw = max(2, min(gbw, pw_actual - rel_x))
                ch = max(2, min(gbh, ph_actual - rel_y))

                c = getattr(obj, "crop", None)
                if c is None or getattr(c, "size", 0) == 0:
                    c = p_crop_combined[rel_y:rel_y+ch, rel_x:rel_x+cw].copy()

                if c.size == 0:
                    c = np.full((ch, cw, 3), 255, dtype=np.uint8)

                p_entities.append({
                    "label": e_idx + 1,
                    "name": obj.name,
                    "rel_x": rel_x,
                    "rel_y": rel_y,
                    "w": cw,
                    "h": ch,
                    "center_x": rel_x + cw / 2.0,
                    "center_y": rel_y + ch / 2.0,
                    "area": cw * ch,
                    "crop": c,
                    "mask": (cv2.cvtColor(c, cv2.COLOR_BGR2GRAY) < 235).astype(np.uint8) * 255
                })

            panel_data.append({
                "panel_name": f"Panel {p_idx+1}",
                "entities": p_entities,
                "panel_crop": p_crop_combined,
                "offset_x": 0,
                "offset_y": 0
            })
    else:
        panel_data = extract_storyboard_panels_and_entities(img)

    num_panels = len(panel_data)
    out_w, out_h = 1920, 1080
    user_gap = max(0, min(120, int(element_spacing)))
    available_w = max(400, out_w - (num_panels + 1) * user_gap)

    # حساب النسبة وتوحيد الارتفاع بحيث ترص اللوحات أفقياً دائماً في شريط عريض متناسق
    aspect_sum = sum(p["panel_crop"].shape[1] / max(1.0, float(p["panel_crop"].shape[0])) for p in panel_data)
    target_panel_h = min(560, max(140, int(available_w / max(0.1, aspect_sum))))

    scaled_panels = []
    for p in panel_data:
        p_crop = p["panel_crop"]
        ph, pw = p_crop.shape[:2]
        sc = target_panel_h / float(max(1, ph))
        nw = max(1, int(round(pw * sc)))
        resized_panel = cv2.resize(p_crop, (nw, target_panel_h), interpolation=cv2.INTER_AREA)
        scaled_panels.append({
            "panel_name": p["panel_name"],
            "entities": p["entities"],
            "raw_crop": p_crop,
            "scaled_crop": resized_panel,
            "scale": sc,
            "offset_x": p["offset_x"],
            "offset_y": p["offset_y"],
            "w": nw, "h": target_panel_h
        })

    total_panels_w = sum(p["w"] for p in scaled_panels)
    actual_gap = user_gap if (total_panels_w + (num_panels + 1) * user_gap <= out_w) else max(4, (out_w - total_panels_w) // (num_panels + 1))
    curr_x = actual_gap
    margin_y = (out_h - target_panel_h) // 2

    target_complete_canvas = np.full((out_h, out_w, 3), 255, dtype=np.uint8)
    entity_render_list = []

    for p_idx, p in enumerate(scaled_panels):
        pw, ph = p["w"], p["h"]
        px1 = curr_x
        py1 = margin_y

        x2 = min(out_w, px1 + pw)
        y2 = min(out_h, py1 + ph)
        dw = x2 - px1
        dh = y2 - py1
        if dw > 0 and dh > 0:
            target_complete_canvas[py1:y2, px1:x2] = p["scaled_crop"][:dh, :dw]

        sc = p["scale"]
        pox = p["offset_x"]
        poy = p["offset_y"]

        for e_idx, ent in enumerate(p["entities"]):
            ew_scaled = max(1, int(round(ent["w"] * sc)))
            eh_scaled = max(1, int(round(ent["h"] * sc)))
            ex_scaled = px1 + int(round((ent["rel_x"] - pox) * sc))
            ey_scaled = py1 + int(round((ent["rel_y"] - poy) * sc))
            ent_crop_scaled = cv2.resize(ent["crop"], (ew_scaled, eh_scaled), interpolation=cv2.INTER_AREA)

            entity_render_list.append({
                "panel_index": p_idx + 1,
                "panel_name": p["panel_name"],
                "entity_index": e_idx + 1,
                "total_in_panel": len(p["entities"]),
                "x1": ex_scaled, "y1": ey_scaled,
                "w": ew_scaled, "h": eh_scaled,
                "center_x": ex_scaled + ew_scaled / 2.0,
                "center_y": ey_scaled + eh_scaled / 2.0,
                "crop": ent_crop_scaled
            })

        curr_x += pw + actual_gap

    live_canvas = np.full((out_h, out_w, 3), 255, dtype=np.uint8)
    step_mask = np.zeros((out_h, out_w), dtype=np.uint8)

    hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH) if show_hand else None
    if hand_bgra is not None:
        hand_target_h = max(60, int(round(300 * max(0.2, float(hand_scale)))))
        scale_h = hand_target_h / float(hand_bgra.shape[0])
        new_hw = max(1, int(hand_bgra.shape[1] * scale_h))
        hand_bgra_scaled = cv2.resize(hand_bgra, (new_hw, hand_target_h), interpolation=cv2.INTER_AREA)
        scaled_tip_x = int(round(PEN_TIP_ANCHOR_X * scale_h))
        scaled_tip_y = int(round(PEN_TIP_ANCHOR_Y * scale_h))
    else:
        hand_bgra_scaled = None
        scaled_tip_x, scaled_tip_y = 0, 0

    writer = DirectVideoWriter(output_path, out_w, out_h, fps)

    full_cam_center = (out_w / 2.0, out_h / 2.0)
    full_cam_scale = 1.0
    brush_radius = max(2, int(brush_radius))

    current_cam_pos = full_cam_center
    current_cam_scale = full_cam_scale

    total_entities = len(entity_render_list)

    # حساب سرعة الرسم بالنقاط لكل إطار
    pts_per_frame = max(4, int(round(20 * (drawing_speed / 1.0))))

    for i_ent, ent_info in enumerate(entity_render_list):
        p_name = ent_info["panel_name"]
        e_idx = ent_info["entity_index"]
        total_e = ent_info["total_in_panel"]
        c_x, c_y = ent_info["center_x"], ent_info["center_y"]
        ex1, ey1 = ent_info["x1"], ent_info["y1"]
        crop = ent_info["crop"]
        ew, eh = ent_info["w"], ent_info["h"]

        # حساب نسبة التقريب بناء على إعدادات زوم الكاميرا المحددة من قبل المستخدم
        if camera_zoom_scale <= 1.05:
            target_zoom = 1.0  # بدون زوم (عرض كامل ثابت)
        else:
            base_fit = 800.0 / max(ew, eh)
            target_zoom = min(3.8, max(1.1, base_fit * (camera_zoom_scale / 2.0)))

        if progress_callback:
            pct = (i_ent / float(total_entities)) * 88.0
            progress_callback(pct, f"Drawing {p_name} — Entity {e_idx}/{total_e}...")

        # 1. تحريك الكاميرا بسلاسة نحو الكيان (إذا كان الزوم مفعلاً)
        if abs(target_zoom - current_cam_scale) > 0.05 or abs(c_x - current_cam_pos[0]) > 10:
            trans_frames = 8
            for tf in range(1, trans_frames + 1):
                t = tf / float(trans_frames)
                ease_t = t * t * (3.0 - 2.0 * t)
                cur_cx = current_cam_pos[0] + (c_x - current_cam_pos[0]) * ease_t
                cur_cy = current_cam_pos[1] + (c_y - current_cam_pos[1]) * ease_t
                cur_scale = current_cam_scale + (target_zoom - current_cam_scale) * ease_t

                cam_frame = render_camera_viewport(live_canvas, cur_cx, cur_cy, cur_scale, out_w, out_h)
                writer.write(cam_frame)

        current_cam_pos = (c_x, c_y)
        current_cam_scale = target_zoom

        # 2. بناء مسار الدوران المتراكز 360 درجة للكيان
        char_strokes = build_gapless_orbital_path(
            crop,
            ring_step=max(1, int(ring_step)),
            sample_interval=max(1.0, float(sample_interval)),
            brush_radius=brush_radius,
            drawing_direction=drawing_direction
        )

        all_path_points = []
        for s in char_strokes:
            for p in s:
                all_path_points.append((ex1 + p[0], ey1 + p[1]))

        if not all_path_points:
            cx, cy = ex1 + ew / 2.0, ey1 + eh / 2.0
            r_w, r_h = max(6.0, ew / 2.0), max(6.0, eh / 2.0)
            angles = np.linspace(0, 2 * np.pi, 24)
            all_path_points = [(cx + r_w * np.cos(a), cy + r_h * np.sin(a)) for a in angles]
            all_path_points.append(all_path_points[0])
            live_canvas[ey1:min(out_h, ey1+eh), ex1:min(out_w, ex1+ew)] = target_complete_canvas[ey1:min(out_h, ey1+eh), ex1:min(out_w, ex1+ew)]

        last_pt = all_path_points[0]

        # 3. حلقة رسم الكيان باليد
        pt_idx = 0
        total_pts = len(all_path_points)
        while pt_idx < total_pts:
            next_idx = min(total_pts, pt_idx + pts_per_frame)
            sub_pts = all_path_points[pt_idx:next_idx]

            for pt in sub_pts:
                gx = int(round(pt[0]))
                gy = int(round(pt[1]))
                prev_gx = int(round(last_pt[0]))
                prev_gy = int(round(last_pt[1]))

                bx1 = max(0, min(prev_gx, gx) - brush_radius - 2)
                bx2 = min(out_w, max(prev_gx, gx) + brush_radius + 3)
                by1 = max(0, min(prev_gy, gy) - brush_radius - 2)
                by2 = min(out_h, max(prev_gy, gy) + brush_radius + 3)

                if bx1 < bx2 and by1 < by2:
                    sub_mask = step_mask[by1:by2, bx1:bx2]
                    sub_mask.fill(0)
                    p1_rel = (prev_gx - bx1, prev_gy - by1)
                    p2_rel = (gx - bx1, gy - by1)
                    cv2.line(sub_mask, p1_rel, p2_rel, 255, thickness=brush_radius * 2, lineType=cv2.LINE_AA)
                    cv2.circle(sub_mask, p2_rel, radius=brush_radius, color=255, thickness=-1, lineType=cv2.LINE_AA)
                    active = np.where(sub_mask > 0)
                    if len(active[0]) > 0:
                        live_canvas[by1:by2, bx1:bx2][active] = target_complete_canvas[by1:by2, bx1:bx2][active]

                last_pt = pt

            curr_tip_x = int(round(last_pt[0]))
            curr_tip_y = int(round(last_pt[1]))

            if hand_bgra_scaled is not None:
                canvas_with_hand = composite_hand_on_canvas_fast(live_canvas, hand_bgra_scaled, scaled_tip_x, scaled_tip_y, curr_tip_x, curr_tip_y)
                cam_view = render_camera_viewport(canvas_with_hand, c_x, c_y, target_zoom, out_w, out_h)
            else:
                cam_view = render_camera_viewport(live_canvas, c_x, c_y, target_zoom, out_w, out_h)

            writer.write(cam_view)
            pt_idx = next_idx

        # 4. خروج اليد المباشر فور الاكتمال
        if last_pt and hand_bgra_scaled is not None:
            exit_f = 3
            for ef in range(1, exit_f + 1):
                t = ef / float(exit_f)
                hx = last_pt[0] + (c_x + 250 - last_pt[0]) * (t * t)
                hy = last_pt[1] + (c_y + 250 - last_pt[1]) * (t * t)
                c_exit = composite_hand_on_canvas_fast(live_canvas, hand_bgra_scaled, scaled_tip_x, scaled_tip_y, int(hx), int(hy))
                cam_view = render_camera_viewport(c_exit, c_x, c_y, target_zoom, out_w, out_h)
                writer.write(cam_view)

        # 5. إذا كان هذا آخر كيان في اللوحة، ابتعاد الكاميرا
        if e_idx == total_e and target_zoom > 1.05:
            zoom_out_frames = 8
            for zf in range(1, zoom_out_frames + 1):
                t = zf / float(zoom_out_frames)
                ease_t = t * t * (3.0 - 2.0 * t)
                cur_cx = c_x + (full_cam_center[0] - c_x) * ease_t
                cur_cy = c_y + (full_cam_center[1] - c_y) * ease_t
                cur_scale = target_zoom + (full_cam_scale - target_zoom) * ease_t

                cam_frame = render_camera_viewport(live_canvas, cur_cx, cur_cy, cur_scale, out_w, out_h)
                writer.write(cam_frame)

            current_cam_pos = full_cam_center
            current_cam_scale = full_cam_scale

            full_overview = render_camera_viewport(live_canvas, full_cam_center[0], full_cam_center[1], full_cam_scale, out_w, out_h)
            for _ in range(3):
                writer.write(full_overview)

    # -------------------------------------------------------------
    # الخاتمة: عرض اللوحة الكاملة 16:9
    # -------------------------------------------------------------
    if progress_callback:
        progress_callback(96.0, "Finalizing Master Storyboard...")

    final_full_view = live_canvas.copy()
    final_hold_frames = max(1, int(round(fps * float(end_hold_seconds))))
    for _ in range(final_hold_frames):
        writer.write(final_full_view)

    writer.release()
    if progress_callback:
        progress_callback(100.0, "Complete!")

    return output_path