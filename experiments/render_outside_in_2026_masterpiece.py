"""
2026 Masterpiece Engine:
1. Strict Outside-In Inking (الرسم من الخارج للداخل بدون أي ظهور مسبق إطلاقاً قبل سن القلم).
   - Pen-leading revelation: Ink flows strictly from the pen tip as it traces outer silhouette inward.
2. 2026 Modern Motion Effects:
   - Jelly Elastic Squash & Stretch Pop (سحابة القلب)
   - Directional Velocity Slides with Motion Blur & Overshoot (سحب المنزل، العائلة، المال، النبتة)
   - Specular 45° Light Sweep Sheen (مسحة الضوء السينمائية)
   - Ambient Micro-Floating Levitation (تنفس وحيوية العناصر)
   - Full Multi-Track SFX Audio Sync.
"""
import os
import sys
import math
import cv2
import av
import numpy as np
from scipy.io import wavfile
import subprocess

ROOT_DIR = r"E:\image_to_animate"
if os.path.join(ROOT_DIR, 'kivy') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'kivy'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
from engine.render.concentric_engine import (
    DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH,
    PEN_TIP_ANCHOR_X, PEN_TIP_ANCHOR_Y,
    build_gapless_orbital_path
)


def ease_out_back(t: float, overshoot: float = 1.3) -> float:
    t = max(0.0, min(1.0, t)) - 1.0
    return t * t * ((overshoot + 1.0) * t + overshoot) + 1.0


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - math.pow(1.0 - t, 3)


def get_jelly_scales(t: float) -> tuple:
    """Non-uniform squash & stretch 2026 spring elasticity."""
    t = max(0.0, min(1.0, t))
    if t >= 1.0:
        return 1.0, 1.0
    if t <= 0.0:
        return 0.0, 0.0
    omega = 18.0
    decay = math.exp(-t * 5.2)
    osc = decay * math.cos(omega * t)
    base = 1.0 - math.pow(1.0 - t, 4)
    scale_x = base + 0.38 * osc
    scale_y = base - 0.30 * osc
    return max(0.01, scale_x), max(0.01, scale_y)


def apply_directional_blur(image: np.ndarray, mask: np.ndarray, direction: str, amount: int) -> tuple:
    ksize = max(1, int(round(amount)))
    if ksize % 2 == 0:
        ksize += 1
    if ksize <= 1:
        return image, mask
        
    if direction in ["LEFT", "RIGHT"]:
        kernel = np.zeros((1, ksize), dtype=np.float32)
        kernel[0, :] = 1.0 / ksize
    else:
        kernel = np.zeros((ksize, 1), dtype=np.float32)
        kernel[:, 0] = 1.0 / ksize
        
    blurred_img = cv2.filter2D(image, -1, kernel)
    blurred_mask = cv2.filter2D(mask, -1, kernel)
    return blurred_img, blurred_mask


def apply_light_sweep(canvas: np.ndarray, x: int, y: int, w: int, h: int, mask: np.ndarray, sweep_prog: float) -> None:
    if sweep_prog < 0.0 or sweep_prog > 1.0:
        return
    diag = w + h
    cur_pos = -int(diag * 0.2) + int(sweep_prog * diag * 1.4)
    beam_width = int(max(25, w * 0.30))
    
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(canvas.shape[1], x + w)
    y2 = min(canvas.shape[0], y + h)
    
    roi = canvas[y1:y2, x1:x2].astype(np.float32)
    m_roi = (mask[y1-y:y2-y, x1-x:x2-x] > 20).astype(np.float32)
    
    yy, xx = np.indices((y2 - y1, x2 - x1))
    proj = xx + yy
    dist_to_beam = np.abs(proj - cur_pos)
    intensity = np.exp(- (dist_to_beam ** 2) / float(beam_width ** 2))
    sheen = (intensity * 85.0)[:, :, np.newaxis] * m_roi[:, :, np.newaxis]
    
    blended = np.clip(roi + sheen, 0, 255).astype(np.uint8)
    canvas[y1:y2, x1:x2] = blended


def render_outside_in_masterpiece(
    video_out: str = "output_animations/demo_outside_in_2026_masterpiece.mp4",
    final_with_sfx: str = "output_animations/demo_outside_in_2026_with_sfx.mp4"
):
    os.makedirs(os.path.dirname(video_out), exist_ok=True)
    
    clean_p5 = cv2.imread(r"experiments/panel_inspections/panel_5_clean.png")
    ph, pw = clean_p5.shape[:2]
    
    out_w, out_h = 1920, 1080
    fps = 30
    duration_sec = 11.0
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
    
    elements_meta = [
        {
            "id": "character",
            "file": "experiments/panel5_groups/character.png",
            "bbox": (82, 138, 290, 291),
            "fx_mode": "STRICT_OUTSIDE_IN_INK",
            "st": 0.5,
            "en": 4.0,  # 3.5 seconds of realistic outside-in inking
            "title": "Effect 1: [STRICT OUTSIDE-IN DRAWING] Pen-Leading Silhouette to Core",
            "desc": "رسم من الخارج للداخل بدقة 100%: لا يظهر أي بكسل إلا عند مرور سن القلم فوقه"
        },
        {
            "id": "cloud_house",
            "file": "experiments/panel5_groups/cloud_house.png",
            "bbox": (47, 40, 118, 128),
            "fx_mode": "SLIDE_BLUR_LEFT",
            "st": 4.1,
            "en": 4.9,
            "dir": "LEFT",
            "title": "Effect 2: [MOTION BLUR SLIDE: LEFT] House Thought Cloud",
            "desc": "انزلاق بسرعة عالية مع تعتيم حركي واقعي واستقرار نابض"
        },
        {
            "id": "cloud_family",
            "file": "experiments/panel5_groups/cloud_family.png",
            "bbox": (182, 11, 123, 123),
            "fx_mode": "SLIDE_BLUR_TOP",
            "st": 5.0,
            "en": 5.8,
            "dir": "TOP",
            "title": "Effect 3: [MOTION BLUR SLIDE: TOP] Family Thought Cloud",
            "desc": "هبوط ديناميكي من الأعلى مع تدرج حدة بصرية متكامل"
        },
        {
            "id": "cloud_money",
            "file": "experiments/panel5_groups/cloud_money.png",
            "bbox": (304, 35, 153, 137),
            "fx_mode": "SLIDE_BLUR_RIGHT",
            "st": 5.9,
            "en": 6.7,
            "dir": "RIGHT",
            "title": "Effect 4: [MOTION BLUR SLIDE: RIGHT] Wealth Cloud",
            "desc": "دخول جانبي من اليمين مع استقرار مرن"
        },
        {
            "id": "cloud_plant",
            "file": "experiments/panel5_groups/cloud_plant.png",
            "bbox": (363, 271, 107, 89),
            "fx_mode": "SLIDE_BLUR_BOTTOM",
            "st": 6.8,
            "en": 7.6,
            "dir": "BOTTOM",
            "title": "Effect 5: [MOTION BLUR SLIDE: BOTTOM] Plant Cloud",
            "desc": "صعود انسيابي من الأسفل نحو الأعلى"
        },
        {
            "id": "cloud_heart",
            "file": "experiments/panel5_groups/cloud_heart.png",
            "bbox": (6, 150, 127, 102),
            "fx_mode": "JELLY_POP_2026",
            "st": 7.7,
            "en": 8.6,
            "title": "Effect 6: [2026 JELLY POP] Non-Uniform Squash & Stretch",
            "desc": "ظهور جيلي مطاطي ثلاثي الأبعاد بفيزياء نابضة"
        },
        {
            "id": "cloud_clock",
            "file": "experiments/panel5_groups/cloud_clock.png",
            "bbox": (321, 162, 157, 102),
            "fx_mode": "FADE_BLOOM_SHIMMER",
            "st": 8.7,
            "en": 9.6,
            "title": "Effect 7: [FADE DISSOLVE + 45° LIGHT SWEEP] Clock Cloud",
            "desc": "ظهور ناعم متبوع بمسحة ضوء سينمائية براقة"
        }
    ]
    
    prepared_items = []
    char_live_mask = None
    char_points = []
    
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
            "phase": idx * 1.15
        })
        
        # Build STRICT OUTSIDE-IN STROKES for Character
        if m["fx_mode"] == "STRICT_OUTSIDE_IN_INK":
            char_live_mask = np.zeros((scaled_bh, scaled_bw), dtype=np.uint8)
            strokes = build_gapless_orbital_path(
                hd_crop,
                ring_step=5,
                sample_interval=3.0,
                brush_radius=7,
                drawing_direction="OUTSIDE_IN",
                mask=hd_mask
            )
            pts_accum = []
            for s in strokes:
                pts_accum.extend(s)
            char_points = pts_accum
            item["char_points"] = pts_accum
            print(f"Character Outside-In Path: {len(strokes)} rings, {len(pts_accum)} sequential points.")
            
        prepared_items.append(item)
        
    container = av.open(video_out, mode="w")
    v_stream = container.add_stream("h264_nvenc", rate=fps)
    v_stream.width = out_w
    v_stream.height = out_h
    v_stream.pix_fmt = "yuv420p"
    v_stream.options = {"preset": "p5", "cq": "17"}
    
    print(f"Rendering Outside-In Masterpiece ({total_frames} frames)...")
    current_pen = (out_w + 300, out_h + 300)
    
    last_pt_drawn_idx = 0
    brush_radius = 7
    
    for f_idx in range(total_frames):
        t = f_idx / float(fps)
        canvas = np.full((out_h, out_w, 3), 255, dtype=np.uint8)
        
        # Panel frame
        cv2.rectangle(canvas, (gx, gy), (gx + target_w, gy + target_h), (30, 30, 30), 3)
        cv2.circle(canvas, (gx, gy), 4, (30, 30, 30), -1)
        cv2.circle(canvas, (gx + target_w, gy), 4, (30, 30, 30), -1)
        cv2.circle(canvas, (gx, gy + target_h), 4, (30, 30, 30), -1)
        cv2.circle(canvas, (gx + target_w, gy + target_h), 4, (30, 30, 30), -1)
        
        show_hand = False
        hand_target = None
        
        active_title = "2026 Whiteboard Masterpiece Showcase"
        active_desc = "Strict Outside-In Inking | Zero Pre-Reveal | Modern Motion Suite"
        
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
            
            # --- 1. STRICT OUTSIDE-IN DRAWING: NOTHING APPEARS BEFORE THE PEN! ---
            if mode == "STRICT_OUTSIDE_IN_INK":
                if t >= en:
                    # Drawing 100% finished
                    m3 = cv2.merge([mask] * 3)
                    canvas[by:by+bh, bx:bx+bw] = np.where(m3 > 0, crop, canvas[by:by+bh, bx:bx+bw])
                else:
                    show_hand = True
                    # Target points index based on time progress
                    total_pts = len(char_points)
                    target_idx = int(round(prog * (total_pts - 1)))
                    target_idx = max(0, min(total_pts - 1, target_idx))
                    
                    # Ink strictly from last point to target point!
                    # Only newly passed pixels are turned to 255 on char_live_mask
                    if target_idx > last_pt_drawn_idx:
                        for p_i in range(last_pt_drawn_idx, target_idx):
                            p1 = (int(round(char_points[p_i][0])), int(round(char_points[p_i][1])))
                            p2 = (int(round(char_points[p_i+1][0])), int(round(char_points[p_i+1][1])))
                            cv2.line(char_live_mask, p1, p2, 255, thickness=brush_radius * 2)
                            cv2.circle(char_live_mask, p2, brush_radius, 255, -1)
                        last_pt_drawn_idx = target_idx
                    elif target_idx == 0 and len(char_points) > 0:
                        p0 = (int(round(char_points[0][0])), int(round(char_points[0][1])))
                        cv2.circle(char_live_mask, p0, brush_radius, 255, -1)
                        
                    # Strict mask combination: revealed_mask AND alpha_mask
                    # Absolute guarantee: ZERO pixels appear ahead of the pen!
                    effective_reveal = cv2.bitwise_and(char_live_mask, mask)
                    m3 = cv2.merge([effective_reveal] * 3)
                    canvas[by:by+bh, bx:bx+bw] = np.where(m3 > 0, crop, canvas[by:by+bh, bx:bx+bw])
                    
                    # Pen tip is pinned EXACTLY to the current active stroke point!
                    cur_pt = char_points[target_idx]
                    hand_target = (bx + cur_pt[0], by + cur_pt[1])
                    
            # --- 2. 2026 JELLY POP (Non-Uniform Squash & Stretch) ---
            elif mode == "JELLY_POP_2026":
                sx, sy = get_jelly_scales(prog)
                cur_w = max(1, int(round(bw * sx)))
                cur_h = max(1, int(round(bh * sy)))
                
                scaled_crop = cv2.resize(crop, (cur_w, cur_h), interpolation=cv2.INTER_LINEAR)
                scaled_mask = cv2.resize(mask, (cur_w, cur_h), interpolation=cv2.INTER_NEAREST)
                
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
                    
            # --- 3. DIRECTIONAL SLIDE WITH DYNAMIC MOTION BLUR ---
            elif mode.startswith("SLIDE_BLUR"):
                d_dir = item["dir"]
                dist = 240
                ease = ease_out_back(prog, overshoot=1.25) if t < en else 1.0
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
                    
                velocity = abs(offset)
                blur_amount = min(22, int(round(velocity * 0.11))) if t < en else 0
                
                active_crop = crop
                active_mask = mask
                if blur_amount > 2:
                    active_crop, active_mask = apply_directional_blur(crop, mask, d_dir, blur_amount)
                    
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
                    
                if 9.5 <= t <= 10.3:
                    sweep_prog = (t - 9.5) / 0.8
                    apply_light_sweep(canvas, rx, ry, bw, bh, mask, sweep_prog)
                    active_title = "Effect 7+: [SPECULAR LIGHT SWEEP] 45-Degree Sheen Beam"
                    active_desc = "مسحة ضوء سينمائية بزاوية 45 درجة تعطي لمعاناً فائق الفخامة"

        # Composite Hand
        if show_hand and hand_target is not None:
            current_pen = (
                current_pen[0] + (hand_target[0] - current_pen[0]) * 0.70,
                current_pen[1] + (hand_target[1] - current_pen[1]) * 0.70
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
                
        if t >= 10.3:
            active_title = "Final Result: Strict Outside-In Inking + 2026 Motion Suite"
            active_desc = "No Pre-reveal | 100% Pen Contact | Modern Velocity Blur & Squash/Stretch"
            
        cv2.putText(canvas, active_title, (gx, gy - 36), cv2.FONT_HERSHEY_DUPLEX, 0.82, (20, 20, 20), 2, cv2.LINE_AA)
        cv2.putText(canvas, active_desc, (gx, gy - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (80, 80, 80), 1, cv2.LINE_AA)
        
        frame = av.VideoFrame.from_ndarray(canvas, format="bgr24")
        frame.pts = f_idx
        for pkt in v_stream.encode(frame):
            container.mux(pkt)
            
    for pkt in v_stream.encode():
        container.mux(pkt)
    container.close()
    print(f"Master Video Rendered: {video_out}")
    
    # MIX AUDIO
    print("Synthesizing SFX Audio Track...")
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
        
    # Multiple marker friction bursts during inking
    mix_track("experiments/sfx/marker_draw.wav", 0.5, vol=0.50)
    mix_track("experiments/sfx/marker_draw.wav", 2.2, vol=0.45)
    mix_track("experiments/sfx/whoosh.wav", 4.1, vol=0.45)
    mix_track("experiments/sfx/whoosh.wav", 5.0, vol=0.45)
    mix_track("experiments/sfx/whoosh.wav", 5.9, vol=0.45)
    mix_track("experiments/sfx/whoosh.wav", 6.8, vol=0.45)
    mix_track("experiments/sfx/pop_bubble.wav", 7.7, vol=0.75)
    mix_track("experiments/sfx/chime_sparkle.wav", 8.7, vol=0.55)
    mix_track("experiments/sfx/chime_sparkle.wav", 9.5, vol=0.40)
    
    peak = np.max(np.abs(master_audio))
    if peak > 0.95:
        master_audio = master_audio / peak * 0.95
        
    wav_path = "experiments/sfx/master_outside_in_sfx.wav"
    wavfile.write(wav_path, sr, (master_audio * 32767).astype(np.int16))
    
    cmd = [
        'ffmpeg', '-y',
        '-i', video_out,
        '-i', wav_path,
        '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '192k',
        final_with_sfx
    ]
    subprocess.run(cmd, check=True)
    print(f"Master Video with Synced SFX Ready: {final_with_sfx}")


if __name__ == "__main__":
    render_outside_in_masterpiece()
