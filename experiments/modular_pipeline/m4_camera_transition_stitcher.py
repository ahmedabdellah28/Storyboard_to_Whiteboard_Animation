"""
Camera Transition & Stitching Engine
File: experiments/modular_pipeline/m4_camera_transition_stitcher.py

Fulfills User Directive:
"ثم نجرب خطوات الكاميرا والدمج واحدة واحدة مع بعض"
(Then test the camera steps and merging one-by-one together)

Uses PyAV VideoEncoder for rock-solid 1080p encoding.
"""
import os
import sys
import cv2
import numpy as np

sys.path.insert(0, r"E:\image_to_animate\kivy")
from engine.video.encoder import VideoEncoder

def smootherstep(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def stitch_panels_with_camera_glide(
    video_1_path: str,
    video_2_path: str,
    merged_output_path: str,
    glide_duration_frames: int = 36,
    fps: int = 30
):
    """
    Stitches Video 1 + Smooth Panoramic Camera Glide + Video 2 into one unified continuous master video.
    """
    cap1 = cv2.VideoCapture(video_1_path)
    w = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
    h = int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
    
    encoder = VideoEncoder(merged_output_path, w, h, fps, crf=16)
    
    # 1. Stream all frames from Video 1
    print(f"[STITCH] Streaming Scene 1 from {os.path.basename(video_1_path)}...")
    last_frame_1 = None
    while True:
        ret, frame = cap1.read()
        if not ret: break
        encoder.write_frame(frame)
        last_frame_1 = frame.copy()
    cap1.release()
    
    # 2. Read first frame of Video 2
    cap2 = cv2.VideoCapture(video_2_path)
    ret, first_frame_2 = cap2.read()
    if not ret or last_frame_1 is None:
        cap2.release()
        encoder.close()
        raise RuntimeError("Failed to read video frames for transition stitching.")
        
    # 3. Generate the Panoramic Camera Glide
    print(f"[STITCH] Generating Cinematic Panoramic Camera Glide ({glide_duration_frames} frames)...")
    GAP = 140
    dual_canvas = np.full((h, w * 2 + GAP, 3), 255, dtype=np.uint8)
    dual_canvas[:, :w] = last_frame_1
    sep_x = w + GAP // 2
    cv2.line(dual_canvas, (sep_x, int(h * 0.12)), (sep_x, int(h * 0.88)), (220, 226, 224), 2)
    dual_canvas[:, w + GAP:] = first_frame_2
    
    for i in range(glide_duration_frames):
        u = i / float(glide_duration_frames - 1)
        s = smootherstep(u)
        curr_x = int(round(s * (w + GAP)))
        view = np.ascontiguousarray(dual_canvas[:, curr_x:curr_x + w])
        encoder.write_frame(view)
        
    # 4. Stream all frames from Video 2
    print(f"[STITCH] Streaming Scene 2 from {os.path.basename(video_2_path)}...")
    encoder.write_frame(first_frame_2)
    while True:
        ret, frame = cap2.read()
        if not ret: break
        encoder.write_frame(frame)
    cap2.release()
    
    encoder.close()
    print(f"[STITCH SUCCESS] Created Merged Video: {merged_output_path}")
    return merged_output_path

if __name__ == "__main__":
    v1 = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\dynamic_panel_01.mp4"
    v2 = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\dynamic_panel_02.mp4"
    out_merged = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\merged_scene_01_and_02.mp4"
    
    stitch_panels_with_camera_glide(v1, v2, out_merged, glide_duration_frames=36)
