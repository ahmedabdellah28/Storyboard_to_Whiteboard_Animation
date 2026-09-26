"""
Next-Gen 2026 Motion Graphics & Explainer Video Visual Engine:
Features:
1. INSIDE_OUT_DRAW: Concentric / Radial inside-out drawing from focal center outward.
   - Hand pen tip physically orbits and leads the expanding contour wavefront.
2. JELLY_POP_2026: Modern Non-Uniform Squash & Stretch Elastic Spring Pop.
   - Asymmetric (ScaleX != ScaleY) spring physics with organic bounce.
3. SLIDE_WITH_MOTION_BLUR: Directional slides with dynamic velocity motion blur.
4. LIGHT_SWEEP_SHIMMER: Sleek 45-degree cinematic sheen sweep across finished elements.
5. AMBIENT_BREATHE: Micro-floating organic levitation keeping the canvas alive.
6. Full Synchronized SFX Audio Mix.
"""
import os
import sys
import math
import cv2
import av
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter
import subprocess

ROOT_DIR = r"E:\image_to_animate"
if os.path.join(ROOT_DIR, 'kivy') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'kivy'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
from engine.render.concentric_engine import DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH, PEN_TIP_ANCHOR_X, PEN_TIP_ANCHOR_Y


def ease_out_back(t: float, overshoot: float = 1.70158) -> float:
    t = max(0.0, min(1.0, t)) - 1.0
    return t * t * ((overshoot + 1.0) * t + overshoot) + 1.0


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - math.pow(1.0 - t, 3)


def get_jelly_scales(t: float) -> tuple:
    """
    2026 Non-Uniform Squash & Stretch Jelly Spring:
    Returns (scale_x, scale_y) simulating organic vector elasticity.
    """
    t = max(0.0, min(1.0, t))
    if t >= 1.0:
        return 1.0, 1.0
    if t <= 0.0:
        return 0.0, 0.0
        
    # Spring physics: decay * cos(omega * t)
    omega = 18.0
    decay = math.exp(-t * 5.0)
    osc = decay * math.cos(omega * t)
    
    # Base expansion
    base = 1.0 - math.pow(1.0 - t, 4)
    
    # Asymmetric squash/stretch: when X squashes outward (+), Y stretches downward (-)
    scale_x = base + 0.35 * osc
    scale_y = base - 0.28 * osc
    return max(0.01, scale_x), max(0.01, scale_y)


def apply_directional_blur(image: np.ndarray, mask: np.ndarray, direction: str, amount: int) -> tuple:
    """Applies horizontal or vertical directional motion blur based on velocity."""
    ksize = max(1, int(round(amount)))
    if ksize % 2 == 0:
        ksize += 1
    if ksize <= 1:
        return image, mask
        
    if direction in ["LEFT", "RIGHT"]:
        kernel = np.zeros((1, ksize), dtype=np.float32)
        kernel[0, :] = 1.0 / ksize
    else:  # TOP, BOTTOM
        kernel = np.zeros((ksize, 1), dtype=np.float32)
        kernel[:, 0] = 1.0 / ksize
        
    blurred_img = cv2.filter2D(image, -1, kernel)
    blurred_mask = cv2.filter2D(mask, -1, kernel)
    return blurred_img, blurred_mask


def apply_light_sweep(canvas: np.ndarray, x: int, y: int, w: int, h: int, mask: np.ndarray, sweep_prog: float) -> None:
    """
    Sweeps a sleek 45-degree angled specular sheen across the element.
    sweep_prog: 0.0 -> 1.0
    """
    if sweep_prog < 0.0 or sweep_prog > 1.0:
        return
        
    diag = w + h
    cur_pos = -int(diag * 0.2) + int(sweep_prog * diag * 1.4)
    beam_width = int(max(20, w * 0.25))
    
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(canvas.shape[1], x + w)
    y2 = min(canvas.shape[0], y + h)
    
    roi = canvas[y1:y2, x1:x2].astype(np.float32)
    m_roi = (mask[y1-y:y2-y, x1-x:x2-x] > 20).astype(np.float32)
    
    # Coordinate grid for 45 deg line: (X - x) + (Y - y)
    yy, xx = np.indices((y2 - y1, x2 - x1))
    proj = xx + yy
    
    dist_to_beam = np.abs(proj - cur_pos)
    intensity = np.exp(- (dist_to_beam ** 2) / float(beam_width ** 2))
    sheen = (intensity * 75.0)[:, :, np.newaxis] * m_roi[:, :, np.newaxis]
    
    blended = np.clip(roi + sheen, 0, 255).astype(np.uint8)
    canvas[y1:y2, x1:x2] = blended


def render_2026_modern_showcase(
    video_out: str = "output_animations/demo_2026_modern_fx.mp4",
    final_with_sfx: str = "output_animations/demo_2026_modern_fx_with_sfx.mp4"
):
    os.makedirs(os.path.dirname(video_out), exist_ok=True)
    
    clean_p5 = cv2.imread(r"experiments/panel_inspections/panel_5_clean.png")
    ph, pw = clean_p5.shape[:2]
    
    out_w, out_h = 1920, 1080
    fps = 30
    duration_sec = 10.0
    total_frames = int(duration_sec * fps)
    
    target_h = 860
    aspect = pw / float(ph)
    target_w = int(round(target_h * aspect))
    scale_x = target_w / float(pw)
    scale_y = target_h / float(ph)
    
    gx = (out_w - target_w) // 2
    gy = (out_h - target_h) // 2
    
    # Hand
    hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
    hand_h = int(out_h * 0.40)
    scale_h = hand_h / float(hand_bgra.shape[0])
    hand_w = max(1, int(hand_bgra.shape[1] * scale_h))
    hand_screen = cv2.resize(hand_bgra, (hand_w, hand_h), interpolation=cv2.INTER_AREA)
    tip_x = int(round(PEN_TIP_ANCHOR_X * scale_h))
    tip_y = int(round(PEN_TIP_ANCHOR_Y * scale_h))
    
    # Elements Definition
    elements_meta = [
        {
            "id": "character",
            "file": "experiments/panel5_groups/character.png",
            "bbox": (82, 138, 290, 291),
            "fx_mode": "INSIDE_OUT_DRAW",
            "st": 0.5,
            "en": 3.0,
            "focal_center": (133, 93),  # Face focal center (eyes/nose)
            "title": "Effect 1: [INSIDE-OUT DRAW] 2026 Concentric Radial Inking",
            "desc": "الرسم من الداخل للخارج: يبدأ من ملامح الوجه ويتسع بحلقات متحدة المركز"
        },
        {
            "id": "cloud_house",
            "file": "experiments/panel5_groups/cloud_house.png",
            "bbox": (47, 40, 118, 128),
            "fx_mode": "SLIDE_BLUR_LEFT",
            "st": 3.1,
            "en": 3.9,
            "dir": "LEFT",
            "title": "Effect 2: [VELOCITY SLIDE + BLUR: LEFT] House Cloud",
            "desc": "انزلاق بسرعة عالية مع تعتيم حركي واقعي (Motion Blur) وتباطؤ مرن"
        },
        {
            "id": "cloud_family",
            "file": "experiments/panel5_groups/cloud_family.png",
            "bbox": (182, 11, 123, 123),
            "fx_mode": "SLIDE_BLUR_TOP",
            "st": 4.0,
            "en": 4.8,
            "dir": "TOP",
            "title": "Effect 3: [VELOCITY SLIDE + BLUR: TOP] Family Cloud",
            "desc": "هبوط انسيابي من الأعلى مع تدرج حدة بصري متكامل"
        },
        {
            "id": "cloud_money",
            "file": "experiments/panel5_groups/cloud_money.png",
            "bbox": (304, 35, 153, 137),
            "fx_mode": "SLIDE_BLUR_RIGHT",
            "st": 4.9,
            "en": 5.7,
            "dir": "RIGHT",
            "title": "Effect 4: [VELOCITY SLIDE + BLUR: RIGHT] Money Cloud",
            "desc": "دخول جانبي من اليمين مع استقرار وتلاشي التعتيم الحركي"
        },
        {
            "id": "cloud_plant",
            "file": "experiments/panel5_groups/cloud_plant.png",
            "bbox": (363, 271, 107, 89),
            "fx_mode": "SLIDE_BLUR_BOTTOM",
            "st": 5.8,
            "en": 6.6,
            "dir": "BOTTOM",
            "title": "Effect 5: [VELOCITY SLIDE + BLUR: BOTTOM] Plant Cloud",
            "desc": "صعود ديناميكي من الأسفل بانسيابية حركية متقنة"
        },
        {
            "id": "cloud_heart",
            "file": "experiments/panel5_groups/cloud_heart.png",
            "bbox": (6, 150, 127, 102),
            "fx_mode": "JELLY_POP_2026",
            "st": 6.7,
            "en": 7.6,
            "title": "Effect 6: [2026 JELLY POP] Organic Squash & Stretch",
            "desc": "ظهور جيلي مطاطي ثلاثي الأبعاد (Squash & Stretch) بفيزياء نابضة"
        },
        {
            "id": "cloud_clock",
            "file": "experiments/panel5_groups/cloud_clock.png",
            "bbox": (321, 162, 157, 102),
            "fx_mode": "FADE_BLOOM_SHIMMER",
            "st": 7.7,
            "en": 8.6,
            "title": "Effect 7: [FADE DISSOLVE + LIGHT SWEEP] Clock Cloud",
            "desc": "ظهور ناعم متبوع بمسحة ضوء سينمائية براقة (Specular Light Sweep)"
        }
    ]
    
    # Pre-scale assets and pre-calculate radial distance map for inside-out draw
    prepared_items = []
    for idx, m in enumerate(elements_meta):
        rgba = cv2.imread(m["file"], cv2.IMREAD_UNCHANGED)
        b, g, r, a = cv2.split(rgba)
        bgr = cv2.merge([b, g, r])
        
        bx, by, bw, bh = m["bbox"]
        scaled_bx = gx + int(round(bx * scale_x))
        scaled_by = gy + int(round(by * scale_y))
        scaled_bw = int(round(bw * scale_x))
        scaled_bh = int(round(bh * scale_y))
        
        hd_crop = cv2.resize(bgr, (scaled_bw, scaled_bh), interpolation=cv2.INTER_LANCZOS4)
        hd_mask = cv2.resize(a, (scaled_bw, scaled_bh), interpolation=cv2.INTER_NEAREST)
        
        item = dict(m)
        item.update({
            "idx": idx,
            "gx": scaled_bx,
            "gy": scaled_by,
            "gw": scaled_bw,
            "gh": scaled_bh,
            "crop": hd_crop,
            "mask": hd_mask,
            "dur": m["en"] - m["st"],
            "phase": idx * 1.05  # for ambient breathing
        })
        
        if m["fx_mode"] == "INSIDE_OUT_DRAW":
            fx_orig, fy_orig = m["focal_center"]
            scaled_fx = int(round(fx_orig * scale_x))
            scaled_fy = int(round(fy_orig * scale_y))
            
            # Distance matrix from focal center
            yy, xx = np.indices((scaled_bh, scaled_bw))
            dist_map = np.sqrt((xx - scaled_fx)**2 + (yy - scaled_fy)**2)
            valid_dists = dist_map[hd_mask > 20]
            max_dist = float(np.max(valid_dists)) if len(valid_dists) > 0 else 100.0
            
            item["scaled_focal"] = (scaled_fx, scaled_fy)
            item["dist_map"] = dist_map
            item["max_dist"] = max_dist
            
        prepared_items.append(item)
        
    container = av.open(video_out, mode="w")
    v_stream = container.add_stream("h264_nvenc", rate=fps)
    v_stream.width = out_w
    v_stream.height = out_h
    v_stream.pix_fmt = "yuv420p"
    v_stream.options = {"preset": "p5", "cq": "17"}
    
    print(f"Rendering 2026 Modern FX Showcase ({total_frames} frames)...")
    current_pen = (out_w + 300, out_h + 300)
    
    for f_idx in range(total_frames):
        t = f_idx / float(fps)
        canvas = np.full((out_h, out_w, 3), 255, dtype=np.uint8)
        
        # Sleek modern border frame with subtle corner accent
        cv2.rectangle(canvas, (gx, gy), (gx + target_w, gy + target_h), (30, 30, 30), 3)
        cv2.circle(canvas, (gx, gy), 4, (30, 30, 30), -1)
        cv2.circle(canvas, (gx + target_w, gy), 4, (30, 30, 30), -1)
        cv2.circle(canvas, (gx, gy + target_h), 4, (30, 30, 30), -1)
        cv2.circle(canvas, (gx + target_w, gy + target_h), 4, (30, 30, 30), -1)
        
        show_hand = False
        hand_target = None
        
        active_title = "2026 Next-Gen Motion Graphics Showcase"
        active_desc = "Whiteboard Animation Reimagined with Modern Aesthetics"
        
        for item in prepared_items:
            st, en = item["st"], item["en"]
            dur = item["dur"]
            mode = item["fx_mode"]
            crop = item["crop"]
            mask = item["mask"]
            bx, by, bw, bh = item["gx"], item["gy"], item["gw"], item["gh"]
            
            if t < st:
                continue
                
            if st <= t < en:
                active_title = item["title"]
                active_desc = item["desc"]
                
            prog = min(1.0, (t - st) / max(0.01, dur))
            
            # --- 1. INSIDE-OUT CONCENTRIC DRAWING ---
            if mode == "INSIDE_OUT_DRAW":
                if t >= en:
                    m3 = cv2.merge([mask] * 3)
                    canvas[by:by+bh, bx:bx+bw] = np.where(m3 > 0, crop, canvas[by:by+bh, bx:bx+bw])
                else:
                    show_hand = True
                    # Ease progress for organic growth
                    r_prog = ease_out_cubic(prog)
                    cur_radius = item["max_dist"] * r_prog
                    
                    # Reveal mask: pixels within current radius
                    active_reveal = ((item["dist_map"] <= cur_radius) & (mask > 20)).astype(np.uint8) * 255
                    
                    # Render revealed portion
                    m3 = cv2.merge([active_reveal] * 3)
                    canvas[by:by+bh, bx:bx+bw] = np.where(m3 > 0, crop, canvas[by:by+bh, bx:bx+bw])
                    
                    # Hand pen tip physically orbits the expanding circular boundary!
                    # 6 full orbital revolutions during the reveal
                    orbit_angle = (prog * 6.0) * (2.0 * math.pi)
                    sfx, sfy = item["scaled_focal"]
                    pen_rel_x = sfx + cur_radius * math.cos(orbit_angle)
                    pen_rel_y = sfy + cur_radius * math.sin(orbit_angle) * 0.85
                    hand_target = (bx + pen_rel_x, by + pen_rel_y)
                    
            # --- 2. 2026 JELLY POP (Squash & Stretch) ---
            elif mode == "JELLY_POP_2026":
                sx, sy = get_jelly_scales(prog)
                cur_w = max(1, int(round(bw * sx)))
                cur_h = max(1, int(round(bh * sy)))
                
                scaled_crop = cv2.resize(crop, (cur_w, cur_h), interpolation=cv2.INTER_LINEAR)
                scaled_mask = cv2.resize(mask, (cur_w, cur_h), interpolation=cv2.INTER_NEAREST)
                
                # Ambient breathing floating after settling
                float_y = 0
                if t >= en:
                    float_y = int(round(math.sin((t - en) * 4.0 + item["phase"]) * 2.5))
                    
                cx = bx + bw // 2
                cy = by + bh // 2 + float_y
                rx = cx - cur_w // 2
                ry = cy - cur_h // 2
                
                x1 = max(0, rx)
                y1 = max(0, ry)
                x2 = min(out_w, rx + cur_w)
                y2 = min(out_h, ry + cur_h)
                
                src_x1 = x1 - rx
                src_y1 = y1 - ry
                src_x2 = src_x1 + (x2 - x1)
                src_y2 = src_y1 + (y2 - y1)
                
                if x2 > x1 and y2 > y1:
                    c_roi = canvas[y1:y2, x1:x2]
                    s_c = scaled_crop[src_y1:src_y2, src_x1:src_x2]
                    s_m = scaled_mask[src_y1:src_y2, src_x1:src_x2]
                    m3 = cv2.merge([s_m] * 3)
                    canvas[y1:y2, x1:x2] = np.where(m3 > 0, s_c, c_roi)
                    
            # --- 3. DIRECTIONAL SLIDE WITH MOTION BLUR ---
            elif mode.startswith("SLIDE_BLUR"):
                d_dir = item["dir"]
                dist = 240
                
                # Ease out with subtle overshoot
                ease = ease_out_back(prog, overshoot=1.2) if t < en else 1.0
                offset = (1.0 - ease) * dist
                
                offset_x, offset_y = 0, 0
                if d_dir == "LEFT":
                    offset_x = -int(round(offset))
                elif d_dir == "RIGHT":
                    offset_x = +int(round(offset))
                elif d_dir == "TOP":
                    offset_y = -int(round(offset))
                elif d_dir == "BOTTOM":
                    offset_y = +int(round(offset))
                    
                # Calculate velocity for motion blur
                velocity = abs(offset)
                blur_amount = min(25, int(round(velocity * 0.12))) if t < en else 0
                
                active_crop = crop
                active_mask = mask
                if blur_amount > 2:
                    active_crop, active_mask = apply_directional_blur(crop, mask, d_dir, blur_amount)
                    
                # Ambient float after landing
                float_y = 0
                if t >= en:
                    float_y = int(round(math.sin((t - en) * 3.5 + item["phase"]) * 2.5))
                    
                rx = bx + offset_x
                ry = by + offset_y + float_y
                
                x1 = max(0, rx)
                y1 = max(0, ry)
                x2 = min(out_w, rx + bw)
                y2 = min(out_h, ry + bh)
                
                src_x1 = x1 - rx
                src_y1 = y1 - ry
                src_x2 = src_x1 + (x2 - x1)
                src_y2 = src_y1 + (y2 - y1)
                
                if x2 > x1 and y2 > y1:
                    c_roi = canvas[y1:y2, x1:x2]
                    s_c = active_crop[src_y1:src_y2, src_x1:src_x2]
                    s_m = active_mask[src_y1:src_y2, src_x1:src_x2]
                    m3 = cv2.merge([s_m] * 3)
                    canvas[y1:y2, x1:x2] = np.where(m3 > 0, s_c, c_roi)
                    
            # --- 4. FADE DISSOLVE + SPECULAR LIGHT SWEEP ---
            elif mode == "FADE_BLOOM_SHIMMER":
                alpha = min(1.0, prog) if t < en else 1.0
                
                float_y = 0
                if t >= en:
                    float_y = int(round(math.sin((t - en) * 3.2 + item["phase"]) * 2.5))
                    
                rx = bx
                ry = by + float_y
                
                x1 = max(0, rx)
                y1 = max(0, ry)
                x2 = min(out_w, rx + bw)
                y2 = min(out_h, ry + bh)
                
                if x2 > x1 and y2 > y1:
                    c_roi = canvas[y1:y2, x1:x2].astype(np.float32)
                    s_crop = crop[:y2-y1, :x2-x1].astype(np.float32)
                    s_mask = (mask[:y2-y1, :x2-x1] > 20).astype(np.float32)
                    m3 = np.repeat(s_mask[:, :, np.newaxis], 3, axis=2)
                    blended = (1.0 - alpha * m3) * c_roi + (alpha * m3) * s_crop
                    canvas[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)
                    
                # Light sweep immediately following complete fade (from t = 8.6 to 9.2)
                if 8.5 <= t <= 9.3:
                    sweep_prog = (t - 8.5) / 0.8
                    apply_light_sweep(canvas, rx, ry, bw, bh, mask, sweep_prog)
                    active_title = "Effect 7+: [SPECULAR LIGHT SWEEP] 45-Degree Sheen Beam"
                    active_desc = "مسحة ضوء سينمائية بزاوية 45 درجة تعطي لمعاناً فائق الفخامة"

        # Composite Hand
        if show_hand and hand_target is not None:
            current_pen = (
                current_pen[0] + (hand_target[0] - current_pen[0]) * 0.45,
                current_pen[1] + (hand_target[1] - current_pen[1]) * 0.45
            )
            canvas = composite_hand_on_canvas_fast(
                canvas,
                hand_screen,
                tip_x,
                tip_y,
                int(round(current_pen[0])),
                int(round(current_pen[1]))
            )
        else:
            off_x, off_y = out_w + 300, out_h + 300
            current_pen = (
                current_pen[0] + (off_x - current_pen[0]) * 0.15,
                current_pen[1] + (off_y - current_pen[1]) * 0.15
            )
            if current_pen[0] < out_w + 100 and current_pen[1] < out_h + 100:
                canvas = composite_hand_on_canvas_fast(
                    canvas,
                    hand_screen,
                    tip_x,
                    tip_y,
                    int(round(current_pen[0])),
                    int(round(current_pen[1]))
                )
                
        if t >= 9.3:
            active_title = "Mastery: 2026 Next-Gen Explainer Animation Suite"
            active_desc = "Inside-Out Inking | Jelly Squash & Stretch | Motion Blur | Light Sweep | Micro-Levitation"
            
        # Draw Sleek 2026 UI Overlay Badge
        cv2.putText(canvas, active_title, (gx, gy - 36), cv2.FONT_HERSHEY_DUPLEX, 0.82, (20, 20, 20), 2, cv2.LINE_AA)
        cv2.putText(canvas, active_desc, (gx, gy - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (80, 80, 80), 1, cv2.LINE_AA)
        
        frame = av.VideoFrame.from_ndarray(canvas, format="bgr24")
        frame.pts = f_idx
        for pkt in v_stream.encode(frame):
            container.mux(pkt)
            
    for pkt in v_stream.encode():
        container.mux(pkt)
    container.close()
    print(f"2026 Video Rendered: {video_out}")
    
    # MIX AUDIO TRACK
    print("Synthesizing and Mixing 2026 Audio Track...")
    sr = 44100
    total_samples = int(duration_sec * sr)
    master_audio = np.zeros(total_samples, dtype=np.float32)
    
    def mix_track(fpath, st_s, vol=1.0):
        if not os.path.exists(fpath):
            return
        _, data = wavfile.read(fpath)
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        st_samp = int(st_s * sr)
        en_samp = min(total_samples, st_samp + len(data))
        master_audio[st_samp:en_samp] += data[:en_samp-st_samp] * vol
        
    mix_track("experiments/sfx/marker_draw.wav", 0.5, vol=0.50)
    mix_track("experiments/sfx/whoosh.wav", 3.1, vol=0.45)
    mix_track("experiments/sfx/whoosh.wav", 4.0, vol=0.45)
    mix_track("experiments/sfx/whoosh.wav", 4.9, vol=0.45)
    mix_track("experiments/sfx/whoosh.wav", 5.8, vol=0.45)
    mix_track("experiments/sfx/pop_bubble.wav", 6.7, vol=0.75)
    mix_track("experiments/sfx/chime_sparkle.wav", 7.7, vol=0.55)
    mix_track("experiments/sfx/chime_sparkle.wav", 8.5, vol=0.40)  # light sweep shimmer
    
    # Normalize
    peak = np.max(np.abs(master_audio))
    if peak > 0.95:
        master_audio = master_audio / peak * 0.95
        
    wav_path = "experiments/sfx/master_2026_sfx.wav"
    wavfile.write(wav_path, sr, (master_audio * 32767).astype(np.int16))
    
    # Mux into final output
    cmd = [
        'ffmpeg', '-y',
        '-i', video_out,
        '-i', wav_path,
        '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '192k',
        final_with_sfx
    ]
    subprocess.run(cmd, check=True)
    print(f"Final 2026 Masterpiece with SFX: {final_with_sfx}")


if __name__ == "__main__":
    render_2026_modern_showcase()
