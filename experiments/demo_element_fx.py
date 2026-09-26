"""
Demo & Prototype Engine for Modern Motion FX in Whiteboard Explainer:
- POP_BUBBLE: Elastic scale bounce (0 -> 1.15x -> 1.0x)
- SLIDE_IN: Directional entry from Left, Right, Top, or Bottom
- FADE_DISSOLVE: Smooth alpha blend from transparency (0.0 -> 1.0)
- HAND_DRAW: Classic physical marker drawing
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

from engine.processing.whiteboard_processor import WhiteboardProcessor
from engine.processing.dynamic_border_detector import DynamicBorderDetector
from dev_separator.panel_pipeline import PanelPipeline
from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
from engine.render.concentric_engine import DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH, PEN_TIP_ANCHOR_X, PEN_TIP_ANCHOR_Y


def elastic_overshoot(t: float) -> float:
    """Elastic spring bounce for bubble pop (t: 0..1 -> scale: 0..1 with overshoot)."""
    t = max(0.0, min(1.0, t))
    if t == 0:
        return 0.0
    if t == 1:
        return 1.0
    # Ease out back / elastic
    c4 = 2.70158
    return 1.0 + (c4 + 1) * math.pow(t - 1, 3) + c4 * math.pow(t - 1, 2)


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - math.pow(1.0 - t, 3)


def render_fx_showcase(output_path: str = "output_animations/demo_element_fx_showcase.mp4"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img_path = os.path.join(ROOT_DIR, "project_content", "images", "sheet_01.png")
    img = cv2.imread(img_path)
    discovered = WhiteboardProcessor.discover_panels(img)
    
    # Take Panel 1
    px, py, pw, ph = discovered[0]["bbox"]
    raw_crop = img[py:py+ph, px:px+pw]
    border_res = DynamicBorderDetector.detect_and_trim_panel_border(raw_crop)
    clean_crop = border_res["clean_crop"]
    panel_res = PanelPipeline.process_panel(clean_crop, panel_id=1, ignore_badges=True)
    
    out_w, out_h = 1920, 1080
    fps = 30
    duration_sec = 6.0
    total_frames = int(duration_sec * fps)
    
    # Scale panel to center of 1080p canvas
    target_h = 820
    aspect = clean_crop.shape[1] / float(clean_crop.shape[0])
    target_w = int(round(target_h * aspect))
    scale_x = target_w / float(clean_crop.shape[1])
    scale_y = target_h / float(clean_crop.shape[0])
    
    gx = (out_w - target_w) // 2
    gy = (out_h - target_h) // 2
    
    # Hand
    hand_bgra = load_hand_asset_bgra(DEFAULT_HAND_PATH, DEFAULT_HAND_MASK_PATH)
    hand_h = int(out_h * 0.38)
    scale_h = hand_h / float(hand_bgra.shape[0])
    hand_w = max(1, int(hand_bgra.shape[1] * scale_h))
    hand_screen = cv2.resize(hand_bgra, (hand_w, hand_h), interpolation=cv2.INTER_AREA)
    tip_x = int(round(PEN_TIP_ANCHOR_X * scale_h))
    tip_y = int(round(PEN_TIP_ANCHOR_Y * scale_h))
    
    # Classify objects into different demonstration effects:
    # 1. Narrator Character -> HAND_DRAW (رسم باليد)
    # 2. IQ Thermometer Scale -> SLIDE_IN_BOTTOM (انزلاق من الأسفل)
    # 3. 2% Percentage Badge -> POP_BUBBLE (ظهور كفقاعة ارتدادية)
    # 4. Crowd -> FADE_DISSOLVE (ظهور ناعم من الاختفاء)
    objs = panel_res["objects"]
    fx_plan = []
    
    for idx, o in enumerate(objs):
        bx, by, bw, bh = o["bbox"]
        cx = float(bx + bw / 2.0) / float(clean_crop.shape[1])
        scaled_bx = gx + int(round(bx * scale_x))
        scaled_by = gy + int(round(by * scale_y))
        scaled_bw = int(round(bw * scale_x))
        scaled_bh = int(round(bh * scale_y))
        
        crop_art = o.get("crop")
        if crop_art is not None and scaled_bw > 0 and scaled_bh > 0:
            hd_crop = cv2.resize(crop_art, (scaled_bw, scaled_bh), interpolation=cv2.INTER_LANCZOS4)
            hd_mask = cv2.resize(o["mask"], (scaled_bw, scaled_bh), interpolation=cv2.INTER_NEAREST)
        else:
            hd_crop = None
            hd_mask = None
            
        if cx < 0.38:
            fx_mode = "HAND_DRAW"
            st_t, en_t = 0.5, 2.5
            desc = "Narrator Character (Hand Inking)"
        elif 0.38 <= cx <= 0.65:
            fx_mode = "SLIDE_IN_BOTTOM"
            st_t, en_t = 2.6, 3.4
            desc = "IQ Scale Thermometer (Slide-in from Bottom)"
        else:
            if by < clean_crop.shape[0] * 0.35:
                fx_mode = "POP_BUBBLE"
                st_t, en_t = 3.6, 4.3
                desc = "2% Badge (Pop-in Bubble Bounce)"
            else:
                fx_mode = "FADE_DISSOLVE"
                st_t, en_t = 4.4, 5.2
                desc = "Human Crowd (Smooth Fade-in Dissolve)"
                
        fx_plan.append({
            "idx": idx,
            "desc": desc,
            "fx_mode": fx_mode,
            "st": st_t,
            "en": en_t,
            "dur": en_t - st_t,
            "gx": scaled_bx,
            "gy": scaled_by,
            "gw": scaled_bw,
            "gh": scaled_bh,
            "crop": hd_crop,
            "mask": hd_mask,
            "strokes": [(scaled_bx + p[0]*scale_x, scaled_by + p[1]*scale_y) for p in o.get("strokes", [])] if fx_mode == "HAND_DRAW" else []
        })
    
    container = av.open(output_path, mode="w")
    v_stream = container.add_stream("h264_nvenc", rate=fps)
    v_stream.width = out_w
    v_stream.height = out_h
    v_stream.pix_fmt = "yuv420p"
    v_stream.options = {"preset": "p5", "cq": "19"}
    
    print(f"Rendering Showcase Video with Dynamic Visual FX ({total_frames} frames)...")
    current_pen = (out_w + 300, out_h + 300)
    
    for f_idx in range(total_frames):
        t = f_idx / float(fps)
        canvas = np.full((out_h, out_w, 3), 255, dtype=np.uint8)
        
        # Render panel border box
        cv2.rectangle(canvas, (gx, gy), (gx + target_w, gy + target_h), (20, 20, 20), 3)
        
        hand_target = None
        show_hand = False
        
        for item in fx_plan:
            st, en = item["st"], item["en"]
            mode = item["fx_mode"]
            crop = item["crop"]
            mask = item["mask"]
            if crop is None or mask is None:
                continue
                
            bx, by, bw, bh = item["gx"], item["gy"], item["gw"], item["gh"]
            
            if t < st:
                continue
                
            prog = min(1.0, (t - st) / max(0.01, item["dur"]))
            
            # EFFECT 1: POP BUBBLE BOUNCE (Elastic Scale around center)
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
                    
                    # Stamp onto canvas with boundary clipping
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
            
            # EFFECT 2: SLIDE IN FROM BOTTOM (Directional Ease-Out Slide)
            elif mode == "SLIDE_IN_BOTTOM":
                ease = ease_out_cubic(prog) if t < en else 1.0
                offset_y = int(round((1.0 - ease) * 180))  # slides up 180px
                ry = by + offset_y
                rx = bx
                
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
                    
            # EFFECT 3: SMOOTH FADE DISSOLVE (Alpha Transparency 0..1)
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
                    
            # EFFECT 4: CLASSIC HAND INKING (Drawing Hand Following Strokes)
            elif mode == "HAND_DRAW":
                x1 = max(0, bx)
                y1 = max(0, by)
                x2 = min(out_w, bx + bw)
                y2 = min(out_h, by + bh)
                
                if t >= en:
                    m3 = cv2.merge([mask] * 3)
                    canvas[y1:y2, x1:x2] = np.where(m3 > 0, crop, canvas[y1:y2, x1:x2])
                else:
                    # progressive draw with hand
                    show_hand = True
                    draw_pct = prog
                    draw_h = int(round(bh * draw_pct))
                    if draw_h > 0:
                        part_mask = mask[:draw_h, :]
                        part_crop = crop[:draw_h, :]
                        m3 = cv2.merge([part_mask] * 3)
                        canvas[by:by+draw_h, bx:bx+bw] = np.where(m3 > 0, part_crop, canvas[by:by+draw_h, bx:bx+bw])
                        hand_target = (bx + bw * 0.5, by + draw_h)
        
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
            # hand glides offscreen
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
            
        # Draw on-screen label explaining active effect
        active_label = "Waiting..."
        if 0.5 <= t < 2.5:
            active_label = "Effect 1: [HAND INKING] Physical Artist Hand & Marker"
        elif 2.6 <= t < 3.4:
            active_label = "Effect 2: [SLIDE-IN] Directional Slide from Bottom (Ease-Out)"
        elif 3.6 <= t < 4.3:
            active_label = "Effect 3: [POP BUBBLE] Elastic Spring Overshoot Bounce"
        elif 4.4 <= t < 5.5:
            active_label = "Effect 4: [FADE DISSOLVE] Smooth Alpha Transparency Blend"
        elif t >= 5.5:
            active_label = "Complete Composition: Hybrid Motion FX & Whiteboard"
            
        cv2.putText(canvas, active_label, (gx, gy - 25), cv2.FONT_HERSHEY_DUPLEX, 0.85, (30, 30, 30), 2, cv2.LINE_AA)
        
        frame = av.VideoFrame.from_ndarray(canvas, format="bgr24")
        frame.pts = f_idx
        for pkt in v_stream.encode(frame):
            container.mux(pkt)
            
    for pkt in v_stream.encode():
        container.mux(pkt)
    container.close()
    print(f"Showcase Video created: {output_path}")

if __name__ == "__main__":
    render_fx_showcase()
