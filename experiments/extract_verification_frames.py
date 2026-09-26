import os
import cv2

video_path = "output_animations/sheet_01_masterpiece_2026.mp4"
out_dir = "experiments/verification_frames_masterpiece"
os.makedirs(out_dir, exist_ok=True)

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
total_f = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"Video opened: fps={fps}, total_frames={total_f}")

timestamps = [
    (3.0, "p1_narrator_outside_in"),
    (6.0, "p1_thermometer_slide"),
    (10.0, "p1_red_figures_2pct_badge"),
    (14.8, "camera_pan_p1_to_p2"),
    (18.0, "p2_brain_outside_in"),
    (29.5, "p2_complete_error_saturn"),
    (42.0, "p3_logic_creative_brain"),
    (47.9, "camera_crane_dip_p3_to_p4"),
    (54.0, "p4_growth_figures"),
    (73.5, "p5_thinker_outside_in"),
    (78.5, "p5_thought_bubbles_complete"),
    (83.5, "p6_stairs_hero_drawing"),
    (88.5, "grand_outro_all_6_panels")
]

for sec, label in timestamps:
    f_num = int(round(sec * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, f_num)
    ret, frame = cap.read()
    if ret:
        out_name = f"{f_num:04d}_{sec:.1f}s_{label}.jpg"
        p = os.path.join(out_dir, out_name)
        cv2.imwrite(p, frame)
        print(f"Saved: {out_name} (frame {f_num})")

cap.release()
print("All diagnostic frames successfully extracted!")
