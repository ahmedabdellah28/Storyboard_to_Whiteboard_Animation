"""
Comprehensive Visual FX Showcase on the User's New Image (Panel 5: The Contemplating Mind)
Demonstrates:
1. HAND_DRAW: Physical artist hand inking the main character
2. SLIDE_IN_LEFT: Directional slide from Left (House Cloud)
3. SLIDE_IN_TOP: Directional slide from Top (Family Cloud)
4. SLIDE_IN_RIGHT: Directional slide from Right (Money Cloud)
5. SLIDE_IN_BOTTOM: Directional slide from Bottom (Plant Cloud)
6. POP_BUBBLE: Elastic spring bounce overshoot (Heart Cloud)
7. FADE_DISSOLVE: Smooth alpha transparency blend (Clock Cloud)
"""
import os
import sys
import math
import cv2
import av
import numpy as np

ROOT_DIR = r"E:\image_to_animate"
if os.path.join(ROOT_DIR, 'kivy') not in sys.path:
    sys.path.insert(0, os.path.join(ROOT_DIR, 'kivy'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
from engine.render.concentric_engine import DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH, PEN_TIP_ANCHOR_X, PEN_TIP_ANCHOR_Y


def elastic_overshoot(t: float) -> float:
    """Elastic bounce overshoot for bubble pop."""
    t = max(0.0, min(1.0, t))
    if t == 0:
        return 0.0
    if t == 1:
        return 1.0
    c4 = 2.70158
    return 1.0 + (c4 + 1) * math.pow(t - 1, 3) + c4 * math.pow(t - 1, 2)


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - math.pow(1.0 - t, 3)


def render_new_image_fx_showcase(output_path: str = "output_animations/demo_new_image_fx_showcase.mp4"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Load Panel 5 clean crop and elements
    clean_p5 = cv2.imread(r"experiments/panel_inspections/panel_5_clean.png")
    ph, pw = clean_p5.shape[:2]
    
    out_w, out_h = 1920, 1080
    fps = 30
    duration_sec = 9.5
    total_frames = int(duration_sec * fps)
    
    # Panel target size on 1080p canvas (centered with generous padding)
    target_h = 860
    aspect = pw / float(ph)
    target_w = int(round(target_h * aspect))
    scale_x = target_w / float(pw)
    scale_y = target_h / float(ph)
    
    gx = (out_w - target_w) // 2
    gy = (out_h - target_h) // 2
    
    # Load Hand asset
    hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
    hand_h = int(out_h * 0.40)
    scale_h = hand_h / float(hand_bgra.shape[0])
    hand_w = max(1, int(hand_bgra.shape[1] * scale_h))
    hand_screen = cv2.resize(hand_bgra, (hand_w, hand_h), interpolation=cv2.INTER_AREA)
    tip_x = int(round(PEN_TIP_ANCHOR_X * scale_h))
    tip_y = int(round(PEN_TIP_ANCHOR_Y * scale_h))
    
    # Load each segmented RGBA group
    # Format: (filename, native_bbox=(x, y, w, h), fx_mode, st_time, en_time, description_ar, description_en)
    elements_meta = [
        {
            "id": "character",
            "file": "experiments/panel5_groups/character.png",
            "bbox": (82, 138, 290, 291),
            "fx_mode": "HAND_DRAW",
            "st": 0.5,
            "en": 2.5,
            "title": "Effect 1: [HAND INKING] Marker Drawing Character",
            "desc": "رسم الشخصية بالقلم ويد الرسام الحقيقية"
        },
        {
            "id": "cloud_house",
            "file": "experiments/panel5_groups/cloud_house.png",
            "bbox": (47, 40, 118, 128),
            "fx_mode": "SLIDE_IN_LEFT",
            "st": 2.6,
            "en": 3.4,
            "title": "Effect 2: [SLIDE-IN: LEFT] House Thought Cloud",
            "desc": "انزلاق ناعم من اليسار مع تباطؤ تدريجي (Ease-Out)"
        },
        {
            "id": "cloud_family",
            "file": "experiments/panel5_groups/cloud_family.png",
            "bbox": (182, 11, 123, 123),
            "fx_mode": "SLIDE_IN_TOP",
            "st": 3.5,
            "en": 4.3,
            "title": "Effect 3: [SLIDE-IN: TOP] Family Thought Cloud",
            "desc": "انزلاق هابط من الأعلى بانسيابية تامة"
        },
        {
            "id": "cloud_money",
            "file": "experiments/panel5_groups/cloud_money.png",
            "bbox": (304, 35, 153, 137),
            "fx_mode": "SLIDE_IN_RIGHT",
            "st": 4.4,
            "en": 5.2,
            "title": "Effect 4: [SLIDE-IN: RIGHT] Wealth & Money Cloud",
            "desc": "انزلاق ناعم من اليمين إلى موضع الفكرة"
        },
        {
            "id": "cloud_plant",
            "file": "experiments/panel5_groups/cloud_plant.png",
            "bbox": (363, 271, 107, 89),
            "fx_mode": "SLIDE_IN_BOTTOM",
            "st": 5.3,
            "en": 6.1,
            "title": "Effect 5: [SLIDE-IN: BOTTOM] Growth Plant Cloud",
            "desc": "صعود انسيابي من الأسفل نحو الأعلى"
        },
        {
            "id": "cloud_heart",
            "file": "experiments/panel5_groups/cloud_heart.png",
            "bbox": (6, 150, 127, 102),
            "fx_mode": "POP_BUBBLE",
            "st": 6.2,
            "en": 7.1,
            "title": "Effect 6: [POP BUBBLE] Heart Pulse Elastic Bounce",
            "desc": "ظهور كفقاعة ارتدادية نابضة (Elastic Spring Overshoot)"
        },
        {
            "id": "cloud_clock",
            "file": "experiments/panel5_groups/cloud_clock.png",
            "bbox": (321, 162, 157, 102),
            "fx_mode": "FADE_DISSOLVE",
            "st": 7.2,
            "en": 8.1,
            "title": "Effect 7: [FADE DISSOLVE] Time Clock Smooth Blend",
            "desc": "ظهور تدريجي ناعم من الاختفاء الكامل (Alpha Blend)"
        }
    ]
    
    # Prepare scaled assets
    prepared_items = []
    for m in elements_meta:
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
            "gx": scaled_bx,
            "gy": scaled_by,
            "gw": scaled_bw,
            "gh": scaled_bh,
            "crop": hd_crop,
            "mask": hd_mask,
            "dur": m["en"] - m["st"]
        })
        prepared_items.append(item)
        
    container = av.open(output_path, mode="w")
    v_stream = container.add_stream("h264_nvenc", rate=fps)
    v_stream.width = out_w
    v_stream.height = out_h
    v_stream.pix_fmt = "yuv420p"
    v_stream.options = {"preset": "p5", "cq": "18"}
    
    print(f"Rendering Showcase on User's New Image ({total_frames} frames)...")
    current_pen = (out_w + 300, out_h + 300)
    
    for f_idx in range(total_frames):
        t = f_idx / float(fps)
        # Pristine white background
        canvas = np.full((out_h, out_w, 3), 255, dtype=np.uint8)
        
        # Draw sleek panel container box
        cv2.rectangle(canvas, (gx, gy), (gx + target_w, gy + target_h), (35, 35, 35), 3)
        
        show_hand = False
        hand_target = None
        
        active_title = "Showcase: Professional Motion Effects"
        active_desc = "Testing on New Image - Panel 5"
        
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
            
            # --- EFFECT 1: POP_BUBBLE (Elastic Spring Overshoot) ---
            if mode == "POP_BUBBLE":
                scale = elastic_overshoot(prog) if t < en else 1.0
                if scale > 0.01:
                    cur_w = max(1, int(round(bw * scale)))
                    cur_h = max(1, int(round(bh * scale)))
                    scaled_crop = cv2.resize(crop, (cur_w, cur_h), interpolation=cv2.INTER_LINEAR)
                    scaled_mask = cv2.resize(mask, (cur_w, cur_h), interpolation=cv2.INTER_NEAREST)
                    
                    cx = bx + bw // 2
                    cy = by + bh // 2
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
                        s_crop = scaled_crop[src_y1:src_y2, src_x1:src_x2]
                        s_mask = scaled_mask[src_y1:src_y2, src_x1:src_x2]
                        m3 = cv2.merge([s_mask] * 3)
                        canvas[y1:y2, x1:x2] = np.where(m3 > 0, s_crop, c_roi)
            
            # --- EFFECT 2, 3, 4, 5: DIRECTIONAL SLIDE-IN (4 DIRECTIONS) ---
            elif mode.startswith("SLIDE_IN"):
                ease = ease_out_cubic(prog) if t < en else 1.0
                dist = 220
                offset_x, offset_y = 0, 0
                
                if mode == "SLIDE_IN_LEFT":
                    offset_x = -int(round((1.0 - ease) * dist))
                elif mode == "SLIDE_IN_RIGHT":
                    offset_x = +int(round((1.0 - ease) * dist))
                elif mode == "SLIDE_IN_TOP":
                    offset_y = -int(round((1.0 - ease) * dist))
                elif mode == "SLIDE_IN_BOTTOM":
                    offset_y = +int(round((1.0 - ease) * dist))
                    
                rx = bx + offset_x
                ry = by + offset_y
                
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
                    s_crop = crop[src_y1:src_y2, src_x1:src_x2]
                    s_mask = mask[src_y1:src_y2, src_x1:src_x2]
                    m3 = cv2.merge([s_mask] * 3)
                    canvas[y1:y2, x1:x2] = np.where(m3 > 0, s_crop, c_roi)
                    
            # --- EFFECT 6: FADE_DISSOLVE (Alpha Transparency 0..1) ---
            elif mode == "FADE_DISSOLVE":
                alpha = min(1.0, prog) if t < en else 1.0
                x1 = max(0, bx)
                y1 = max(0, by)
                x2 = min(out_w, bx + bw)
                y2 = min(out_h, by + bh)
                
                if x2 > x1 and y2 > y1:
                    c_roi = canvas[y1:y2, x1:x2].astype(np.float32)
                    s_crop = crop[:y2-y1, :x2-x1].astype(np.float32)
                    s_mask = (mask[:y2-y1, :x2-x1] > 0).astype(np.float32)
                    m3 = np.repeat(s_mask[:, :, np.newaxis], 3, axis=2)
                    blended = (1.0 - alpha * m3) * c_roi + (alpha * m3) * s_crop
                    canvas[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)
                    
            # --- EFFECT 7: HAND_DRAW (Physical Artist Hand Inking) ---
            elif mode == "HAND_DRAW":
                x1 = max(0, bx)
                y1 = max(0, by)
                x2 = min(out_w, bx + bw)
                y2 = min(out_h, by + bh)
                
                if t >= en:
                    m3 = cv2.merge([mask] * 3)
                    canvas[y1:y2, x1:x2] = np.where(m3 > 0, crop, canvas[y1:y2, x1:x2])
                else:
                    show_hand = True
                    draw_pct = prog
                    draw_h = int(round(bh * draw_pct))
                    if draw_h > 0:
                        part_mask = mask[:draw_h, :]
                        part_crop = crop[:draw_h, :]
                        m3 = cv2.merge([part_mask] * 3)
                        canvas[by:by+draw_h, bx:bx+bw] = np.where(m3 > 0, part_crop, canvas[by:by+draw_h, bx:bx+bw])
                        
                        # Hand pen tracks along the active horizontal wave
                        wave_x = math.sin(f_idx * 0.4) * (bw * 0.35)
                        hand_target = (bx + bw * 0.5 + wave_x, by + draw_h)
        
        # Composite Artist Hand
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
                
        if t >= 8.2:
            active_title = "Final Result: Complete Harmonized Whiteboard & Motion FX"
            active_desc = "All 7 Elements Integrated with Precision"
            
        # Draw sleek on-screen HUD
        cv2.putText(canvas, active_title, (gx, gy - 35), cv2.FONT_HERSHEY_DUPLEX, 0.85, (25, 25, 25), 2, cv2.LINE_AA)
        cv2.putText(canvas, active_desc, (gx, gy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (90, 90, 90), 1, cv2.LINE_AA)
        
        frame = av.VideoFrame.from_ndarray(canvas, format="bgr24")
        frame.pts = f_idx
        for pkt in v_stream.encode(frame):
            container.mux(pkt)
            
    for pkt in v_stream.encode():
        container.mux(pkt)
    container.close()
    print(f"Showcase created successfully: {output_path}")


if __name__ == "__main__":
    render_new_image_fx_showcase()
