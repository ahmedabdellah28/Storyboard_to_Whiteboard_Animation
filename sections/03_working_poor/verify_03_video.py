import os
import cv2

video_path = r"E:\image_to_animate\output_animations\wealth_classes_documentary\deliverables\sections\03_working_poor_Whiteboard_1080p.mp4"
out_dir = r"E:\image_to_animate\sections\03_working_poor\scratch"
os.makedirs(out_dir, exist_ok=True)

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
dur = total_frames / float(fps)
print(f"Video: {video_path}")
print(f"Resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
print(f"FPS: {fps}, Total Frames: {total_frames}, Duration: {dur:.2f}s")

check_times = [
    (2.0, "t02_title_banner"),
    (7.0, "t07_alarm_wake"),
    (13.0, "t13_apartment"),
    (18.0, "t18_bank_app"),
    (26.5, "t26_bus_and_car"),
    (32.5, "t32_four_jobs"),
    (38.0, "t38_shift_checklist"),
    (48.5, "t48_doctor_visit"),
    (62.0, "t62_discount_shopping"),
    (69.5, "t69_savings_jar"),
    (86.5, "t86_watch_series"),
    (89.0, "t89_online_course"),
    (92.0, "t92_sleep_finale")
]

for t, name in check_times:
    f_idx = min(total_frames - 1, int(t * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
    ret, frame = cap.read()
    if ret:
        out_f = os.path.join(out_dir, f"{name}.jpg")
        cv2.imwrite(out_f, frame)
        print(f"Saved snapshot {name} at {t:.1f}s (frame {f_idx})")

cap.release()
print("Snapshots verification complete!")
