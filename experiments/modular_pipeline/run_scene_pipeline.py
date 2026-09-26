"""
Orchestrator: Modular Pipeline Runner for Scene 1
File: experiments/modular_pipeline/run_scene_pipeline.py

Executes the 5 Decoupled Modules:
1. Module 1: Dynamic Panel Extractor
2. Module 2: Method A Layer Splitter (Graphics vs Text)
3. Module 3: Dedicated Character Engine (Outlines + TrueColor Fills)
4. Module 4: Dedicated Typography Engine (Arabic RTL Handwriting + Pen Lifts)
5. Module 5: Camera & Progressive Whiteboard Director (Blank Canvas -> Zoom In -> Draw/Write -> Zoom Out to Slot)
"""
import os
import sys
import av
import cv2
import numpy as np

# Ensure modular_pipeline and kivy are accessible
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, r"E:\image_to_animate\kivy")

from m1_panel_extractor import DynamicPanelExtractor
from m2_layer_splitter import MethodALayerSplitter
from m3_character_engine import DedicatedCharacterEngine
from m4_typography_engine import DedicatedTypographyEngine
from m5_camera_director import CameraWhiteboardDirector

# Configuration
MASTER_IMAGE_PATH = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\.user_uploaded\media_1788292396282.png"
HAND_PATH = r"E:\image_to_animate\kivy\data\images\drawing-hand.png"
OUTPUT_DIR = r"E:\image_to_animate\experiments\results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def run_scene_1():
    print("\n" + "="*80)
    print("[PIPELINE] RUNNING MODULAR 5-STAGE PIPELINE FOR SCENE 1")
    print("="*80)
    
    # ----------------- 1. LOAD MASTER & DISCOVER PANELS -----------------
    master_bgr = cv2.imread(MASTER_IMAGE_PATH)
    if master_bgr is None:
        raise FileNotFoundError(f"Cannot load master image: {MASTER_IMAGE_PATH}")
    MH, MW = master_bgr.shape[:2]
    
    print("[Stage 1/5] Module 1: Discovering panels and extracting interior...")
    panels = DynamicPanelExtractor.extract_panels(master_bgr)
    print(f"  -> Discovered {len(panels)} panels dynamically.")
    
    # Focus on Panel 1 (Scene 1)
    p1 = panels[0]
    p1_crop = p1["crop"]
    ph_orig, pw_orig = p1_crop.shape[:2]
    
    # Canvas parameters
    HD_W, HD_H = 1920, 1080
    PANEL_HD_W = 1400
    PANEL_HD_H = int(PANEL_HD_W * (ph_orig / float(pw_orig)))
    
    # Super-Resolve Panel 1 to Native Full HD
    p1_hd = cv2.resize(p1_crop, (PANEL_HD_W, PANEL_HD_H), interpolation=cv2.INTER_LANCZOS4)
    p1_blur = cv2.GaussianBlur(p1_hd, (0, 0), 1.2)
    p1_hd = cv2.addWeighted(p1_hd, 1.25, p1_blur, -0.25, 0)
    
    # Coordinates for Center Focus and Whiteboard Slot
    CENTER_X = (HD_W - PANEL_HD_W) // 2
    CENTER_Y = (HD_H - PANEL_HD_H) // 2
    CENTER_RECT = (CENTER_X, CENTER_Y, PANEL_HD_W, PANEL_HD_H)
    
    BOARD_SCALE = min(1700.0 / MW, 950.0 / MH)
    BOARD_W = int(MW * BOARD_SCALE)
    BOARD_H = int(MH * BOARD_SCALE)
    BOARD_OFF_X = (HD_W - BOARD_W) // 2
    BOARD_OFF_Y = (HD_H - BOARD_H) // 2
    
    SLOT_X = BOARD_OFF_X + int(p1["outer_bbox"][0] * BOARD_SCALE)
    SLOT_Y = BOARD_OFF_Y + int(p1["outer_bbox"][1] * BOARD_SCALE)
    SLOT_W = int(p1["outer_bbox"][2] * BOARD_SCALE)
    SLOT_H = int(p1["outer_bbox"][3] * BOARD_SCALE)
    SLOT_RECT = (SLOT_X, SLOT_Y, SLOT_W, SLOT_H)
    
    # ----------------- 2. LAYER SPLITTER (METHOD A) -----------------
    print("[Stage 2/5] Module 2: Method A Layer Splitter (Graphics vs Typography)...")
    split_result = MethodALayerSplitter.split(p1_hd)
    graphics_img = split_result["graphics_image"]
    text_img = split_result["text_image"]
    
    # Save layer split artifacts for verification
    cv2.imwrite(os.path.join(OUTPUT_DIR, "m2_scene_01_graphics_layer.png"), graphics_img)
    cv2.imwrite(os.path.join(OUTPUT_DIR, "m2_scene_01_text_layer.png"), text_img)
    print("  -> Saved graphics and typography isolated image layers.")
    
    # ----------------- 3. CHARACTER ENGINE -----------------
    print("[Stage 3/5] Module 3: Dedicated Character Engine (Outlines + Progressive Fills)...")
    char_engine = DedicatedCharacterEngine()
    char_data = char_engine.process_graphics(graphics_img)
    print(f"  -> Extracted {char_data['total_strokes']} character strokes and {char_data['total_fills']} color regions.")
    
    # ----------------- 4. TYPOGRAPHY ENGINE -----------------
    print("[Stage 4/5] Module 4: Dedicated Typography Engine (Arabic RTL Handwriting)...")
    text_engine = DedicatedTypographyEngine()
    text_data = text_engine.process_text(text_img)
    print(f"  -> Extracted {text_data['total_words']} text words/glyphs with RTL reading order.")
    
    # ----------------- 5. CAMERA & WHITEBOARD DIRECTOR -----------------
    print("[Stage 5/5] Module 5: Camera & Progressive Whiteboard Director (Blank Canvas -> Zoom In -> Draw/Write -> Zoom Out)...")
    director = CameraWhiteboardDirector(HD_W, HD_H, HAND_PATH)
    
    FPS = 30
    TOTAL_DURATION = 14.0  # seconds
    TOTAL_FRAMES = int(TOTAL_DURATION * FPS)
    
    VIDEO_PATH = os.path.join(OUTPUT_DIR, "scene_01_modular_pipeline_demo.mp4")
    container = av.open(VIDEO_PATH, mode="w")
    stream = container.add_stream("h264", rate=FPS)
    stream.width = HD_W
    stream.height = HD_H
    stream.pix_fmt = "yuv420p"
    stream.options = {"crf": "20", "preset": "fast"}
    
    # Timeline Milestones (Seconds)
    T_START_HOLD        = 0.5   # 0.0s - 0.5s: 100% Pristine Blank White Canvas
    T_ZOOM_IN_START     = 0.5   # 0.5s - 1.8s: Camera smooth zoom to center
    T_ZOOM_IN_END       = 1.8
    T_CHAR_STROKES_START = 1.8   # 1.8s - 4.5s: Character Outlines & Linework Drawing
    T_CHAR_STROKES_END   = 4.5
    T_CHAR_FILLS_START   = 4.5   # 4.5s - 6.8s: Character Color Fills (TrueColor Progressive Reveal)
    T_CHAR_FILLS_END     = 6.8
    T_TRANSIT_START     = 6.8   # 6.8s - 7.3s: Hand transit to title
    T_TRANSIT_END       = 7.3
    T_TEXT_START        = 7.3   # 7.3s - 10.8s: Arabic Typography Handwriting (RTL)
    T_TEXT_END          = 10.8
    T_HAND_EXIT_START   = 10.8  # 10.8s - 11.4s: Hand exits frame gracefully
    T_HAND_EXIT_END     = 11.4
    T_ZOOM_OUT_START    = 11.4  # 11.4s - 13.0s: Zoom out, Panel 1 moves to its slot on blank board
    T_ZOOM_OUT_END      = 13.0
    T_FINAL_HOLD        = 14.0  # 13.0s - 14.0s: Final hold of Panel 1 on blank board
    
    # Local Panel Buffer
    panel_canvas = np.full((PANEL_HD_H, PANEL_HD_W, 3), 255, dtype=np.uint8)
    
    snapshot_times = [0.3, 1.2, 3.2, 5.8, 9.2, 12.2, 13.8]
    snapshot_frames = []
    
    for frame_idx in range(TOTAL_FRAMES):
        t = frame_idx / float(FPS)
        
        # 1. Compute Progress Values
        p_char_strokes = 0.0
        if t >= T_CHAR_STROKES_START:
            p_char_strokes = min(1.0, (t - T_CHAR_STROKES_START) / (T_CHAR_STROKES_END - T_CHAR_STROKES_START))
            
        p_char_fills = 0.0
        if t >= T_CHAR_FILLS_START:
            p_char_fills = min(1.0, (t - T_CHAR_FILLS_START) / (T_CHAR_FILLS_END - T_CHAR_FILLS_START))
            
        p_text = 0.0
        if t >= T_TEXT_START:
            p_text = min(1.0, (t - T_TEXT_START) / (T_TEXT_END - T_TEXT_START))
            
        # 2. Render Panel Canvas Progress via Specialized Engines
        # Step A: Character Engine
        tip_x_c, tip_y_c, tilt_c = DedicatedCharacterEngine.render_frame_progress(
            panel_canvas, char_data, p_char_strokes, p_char_fills
        )
        
        # Step B: Typography Engine
        tip_x_t, tip_y_t, tilt_t = DedicatedTypographyEngine.render_frame_progress(
            panel_canvas, text_data, p_text
        )
        
        # 3. Determine Hand Position & Dynamics
        hand_tip_x, hand_tip_y = -100.0, -100.0
        hand_tilt = -30.0
        hand_opacity = 0.0
        
        if T_CHAR_STROKES_START <= t < T_CHAR_FILLS_END:
            hand_opacity = 1.0
            hand_tip_x = CENTER_X + tip_x_c
            hand_tip_y = CENTER_Y + tip_y_c
            hand_tilt = tilt_c
        elif T_TRANSIT_START <= t < T_TRANSIT_END:
            # Transit arc
            hand_opacity = 1.0
            hand_tilt = -45.0
            p_tr = (t - T_TRANSIT_START) / (T_TRANSIT_END - T_TRANSIT_START)
            s_pt = [CENTER_X + 250, CENTER_Y + 350]
            e_pt = [CENTER_X + PANEL_HD_W - 180, CENTER_Y + 70]
            m_pt = [(s_pt[0] + e_pt[0])/2.0, min(s_pt[1], e_pt[1]) - 120]
            hand_tip_x = (1-p_tr)**2 * s_pt[0] + 2*(1-p_tr)*p_tr*m_pt[0] + p_tr**2 * e_pt[0]
            hand_tip_y = (1-p_tr)**2 * s_pt[1] + 2*(1-p_tr)*p_tr*m_pt[1] + p_tr**2 * e_pt[1]
        elif T_TEXT_START <= t < T_TEXT_END:
            hand_opacity = 1.0
            hand_tip_x = CENTER_X + tip_x_t
            hand_tip_y = CENTER_Y + tip_y_t
            hand_tilt = tilt_t
        elif T_HAND_EXIT_START <= t < T_HAND_EXIT_END:
            p_ex = (t - T_HAND_EXIT_START) / (T_HAND_EXIT_END - T_HAND_EXIT_START)
            hand_tip_x = CENTER_X + PANEL_HD_W * 0.7 + (p_ex**2) * 700
            hand_tip_y = CENTER_Y + PANEL_HD_H * 0.7 + (p_ex**2) * 600
            hand_opacity = max(0.0, 1.0 - p_ex**2)
            
        # 4. Camera Compositing onto Progressive Whiteboard
        if t < T_ZOOM_IN_START:
            # Stage 0: 100% Blank White Canvas
            final_frame = director.board_canvas.copy()
            
        elif t < T_ZOOM_IN_END:
            # Stage 1: Zoom In to Center Stage
            p_z = (t - T_ZOOM_IN_START) / (T_ZOOM_IN_END - T_ZOOM_IN_START)
            final_frame = director.render_panel_transition(panel_canvas, CENTER_RECT, (CENTER_X, CENTER_Y, int(PANEL_HD_W*0.4), int(PANEL_HD_H*0.4)), p_z, is_zoom_in=True)
            
        elif t < T_ZOOM_OUT_START:
            # Stage 2-4: Full-HD Center Focus Stage
            final_frame = director.board_canvas.copy()
            final_frame[CENTER_Y:CENTER_Y+PANEL_HD_H, CENTER_X:CENTER_X+PANEL_HD_W] = panel_canvas
            if hand_opacity > 0.01:
                director.draw_hand(final_frame, hand_tip_x, hand_tip_y, hand_tilt, hand_opacity)
                
        elif t < T_ZOOM_OUT_END:
            # Stage 5: Zoom Out & Slide to Designated Slot
            p_zo = (t - T_ZOOM_OUT_START) / (T_ZOOM_OUT_END - T_ZOOM_OUT_START)
            final_frame = director.render_panel_transition(panel_canvas, CENTER_RECT, SLOT_RECT, p_zo, is_zoom_in=False)
            
        else:
            # Stage 6: Commit and Hold (ONLY Panel 1 on Blank Board)
            director.commit_panel_to_board(p1_hd, SLOT_RECT)
            final_frame = director.board_canvas.copy()
            
        # Write Frame
        v_frame = av.VideoFrame.from_ndarray(final_frame, format="bgr24")
        for packet in stream.encode(v_frame):
            container.mux(packet)
            
        # Snapshots
        for s_t in snapshot_times:
            if abs(t - s_t) < (0.5 / FPS):
                snapshot_frames.append({
                    "time": s_t,
                    "label": f"t={s_t:.1f}s",
                    "frame": final_frame.copy()
                })
                
    for packet in stream.encode():
        container.mux(packet)
    container.close()
    print(f"\n[SUCCESS] Modular Pipeline Video exported successfully: {VIDEO_PATH}")
    
    # ----------------- 6. CONTACT SHEET -----------------
    cw, ch = 600, 338
    grid_cols = 3
    grid_rows = 2
    cs_img = np.full((grid_rows * (ch + 40) + 70, grid_cols * (cw + 15) + 20, 3), 35, dtype=np.uint8)
    
    cv2.putText(cs_img, "MODULAR PIPELINE SCENE 1: DECOUPLED MODULES (A-SPLIT -> CHAR -> TEXT -> CAMERA)", 
                (25, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (0, 220, 255), 2, cv2.LINE_AA)
    
    stage_labels = [
        "M5: 100% Pristine Blank White Canvas",
        "M5: Camera Zooms In to Center Stage",
        "M3: Character Outlines & Linework Drawing",
        "M3: Character TrueColor Progressive Fills",
        "M4: Arabic Typography Handwriting (RTL)",
        "M5: Zoom-Out Transition to Slot (Board Blank)"
    ]
    
    for idx, sn in enumerate(snapshot_frames[:6]):
        r = idx // grid_cols
        c = idx % grid_cols
        gx = 20 + c * (cw + 15)
        gy = 70 + r * (ch + 40)
        
        small_f = cv2.resize(sn["frame"], (cw, ch), interpolation=cv2.INTER_AREA)
        cs_img[gy:gy+ch, gx:gx+cw] = small_f
        cv2.rectangle(cs_img, (gx, gy), (gx+cw, gy+ch), (80, 80, 80), 2)
        
        lbl = stage_labels[idx] if idx < len(stage_labels) else sn["label"]
        cv2.putText(cs_img, f"[{sn['label']}] {lbl}", (gx + 5, gy + ch + 24), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)
    
    CONTACT_SHEET_PATH = os.path.join(OUTPUT_DIR, "scene_01_modular_contact_sheet.png")
    cv2.imwrite(CONTACT_SHEET_PATH, cs_img)
    print(f"[SUCCESS] Contact sheet saved: {CONTACT_SHEET_PATH}")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_scene_1()
