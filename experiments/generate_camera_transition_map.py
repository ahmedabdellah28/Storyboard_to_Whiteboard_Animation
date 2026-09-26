"""
Generates high-definition visual diagnostic and infographic image:
'Camera Transition & Cinematic Choreography Map'
Shows:
1. All 6 panels on the master sheet
2. The smooth Bézier / Smootherstep camera center trajectory
3. Camera viewport rectangles (Panel close-up vs Grand Zoom-out)
4. Keyframe milestones with timing labels
"""
import os
import cv2
import numpy as np

img_path = r"project_content/images/ChatGPT Image Sep 18, 2026, 04_51_53 PM.png"
img = cv2.imread(img_path)
ih, iw = img.shape[:2]

# Create high-res canvas (1920x1080) with clean layout
canvas_w, canvas_h = 1920, 1080
canvas = np.full((canvas_h, canvas_w, 3), 248, dtype=np.uint8)

# Place master sheet image centered
target_h = 800
scale = target_h / float(ih)
target_w = int(round(iw * scale))
off_x = (canvas_w - target_w) // 2
off_y = 170

resized_sheet = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
canvas[off_y:off_y+target_h, off_x:off_x+target_w] = resized_sheet

# Panel Bounding Boxes on the original sheet (scaled)
# Panels:
# 1: (9, 10, 499, 493)
# 2: (524, 10, 493, 493)
# 3: (1032, 10, 499, 493)
# 4: (9, 521, 499, 492)
# 5: (524, 521, 493, 492)
# 6: (1032, 521, 499, 492)

raw_panels = [
    (9, 10, 499, 493, "Panel 1 (0.0s - 15.0s)", "المقدمة ونسبة الـ 2%"),
    (524, 10, 493, 493, "Panel 2 (15.0s - 34.5s)", "المخ والتفكير والضغوط"),
    (1032, 10, 499, 493, "Panel 3 (34.5s - 48.1s)", "نصفي الدماغ (منطق وإبداع)"),
    (9, 521, 499, 492, "Panel 4 (48.1s - 71.0s)", "مراحل العمر والتعلم"),
    (524, 521, 493, 492, "Panel 5 (71.0s - 81.0s)", "العقل المفكر وسحب الأفكار"),
    (1032, 521, 499, 492, "Panel 6 (81.0s - 89.9s)", "طريق الأهداف وتجاوز العقبات")
]

scaled_centers = []
for idx, (px, py, pw, ph, en_title, ar_title) in enumerate(raw_panels):
    sx = off_x + int(round(px * scale))
    sy = off_y + int(round(py * scale))
    sw = int(round(pw * scale))
    sh = int(round(ph * scale))
    
    cx = sx + sw // 2
    cy = sy + sh // 2
    scaled_centers.append((cx, cy))
    
    # Draw glowing subtle panel border
    cv2.rectangle(canvas, (sx, sy), (sx + sw, sy + sh), (0, 120, 255), 2)
    
    # Draw badge for panel number
    cv2.circle(canvas, (sx + 35, sy + 35), 22, (20, 20, 20), -1)
    cv2.circle(canvas, (sx + 35, sy + 35), 22, (0, 160, 255), 2)
    cv2.putText(canvas, str(idx + 1), (sx + 26, sy + 43), cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    
    # Small label
    cv2.putText(canvas, en_title, (sx + 65, sy + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (20, 20, 20), 1, cv2.LINE_AA)

# Draw the cinematic camera trajectory spline
# P1 -> P2 -> P3 -> Crane Dip curve down to P4 -> P5 -> P6
curve_points = []

# P1 to P2
for t in np.linspace(0, 1, 30):
    x = int(scaled_centers[0][0] + (scaled_centers[1][0] - scaled_centers[0][0]) * t)
    y = int(scaled_centers[0][1] + (scaled_centers[1][1] - scaled_centers[0][1]) * t)
    curve_points.append((x, y))

# P2 to P3
for t in np.linspace(0, 1, 30):
    x = int(scaled_centers[1][0] + (scaled_centers[2][0] - scaled_centers[1][0]) * t)
    y = int(scaled_centers[1][1] + (scaled_centers[2][1] - scaled_centers[1][1]) * t)
    curve_points.append((x, y))

# Crane Dip: P3 to P4 (S-curve dipping across the sheet)
p3 = scaled_centers[2]
p4 = scaled_centers[3]
# Control points for beautiful swoop
ctrl1 = (p3[0] + 120, p3[1] + 180)
ctrl2 = (p4[0] - 120, p4[1] - 180)
for t in np.linspace(0, 1, 60):
    # Cubic Bezier
    bx = (1-t)**3 * p3[0] + 3*(1-t)**2*t*ctrl1[0] + 3*(1-t)*t**2*ctrl2[0] + t**3 * p4[0]
    by = (1-t)**3 * p3[1] + 3*(1-t)**2*t*ctrl1[1] + 3*(1-t)*t**2*ctrl2[1] + t**3 * p4[1]
    curve_points.append((int(bx), int(by)))

# P4 to P5
for t in np.linspace(0, 1, 30):
    x = int(scaled_centers[3][0] + (scaled_centers[4][0] - scaled_centers[3][0]) * t)
    y = int(scaled_centers[3][1] + (scaled_centers[4][1] - scaled_centers[3][1]) * t)
    curve_points.append((x, y))

# P5 to P6
for t in np.linspace(0, 1, 30):
    x = int(scaled_centers[4][0] + (scaled_centers[5][0] - scaled_centers[4][0]) * t)
    y = int(scaled_centers[4][1] + (scaled_centers[5][1] - scaled_centers[4][1]) * t)
    curve_points.append((x, y))

# Draw the path on canvas with glowing effect
for i in range(len(curve_points) - 1):
    pt1 = curve_points[i]
    pt2 = curve_points[i+1]
    # Outer glow
    cv2.line(canvas, pt1, pt2, (255, 200, 100), 7, cv2.LINE_AA)
    # Core line
    cv2.line(canvas, pt1, pt2, (230, 80, 0), 3, cv2.LINE_AA)

# Draw directional arrowheads along the path
for arrow_idx in [15, 45, 90, 135, 165]:
    pt1 = curve_points[arrow_idx]
    pt2 = curve_points[arrow_idx + 1]
    cv2.arrowedLine(canvas, pt1, pt2, (0, 50, 200), 3, tipLength=0.45)

# Illustrate Camera Viewport Frame at Panel 1 (Closeup Zoom: 2.2x)
p1_cx, p1_cy = scaled_centers[0]
vw = int(target_w * 0.48)
vh = int(target_h * 0.48)
vx1, vy1 = p1_cx - vw // 2, p1_cy - vh // 2
vx2, vy2 = vx1 + vw, vy1 + vh

# Dashed or glowing camera rectangle
cv2.rectangle(canvas, (vx1, vy1), (vx2, vy2), (0, 0, 220), 3)
cv2.putText(canvas, "CAMERA VIEWPORT (Zoom 2.2x Close-up)", (vx1 + 10, vy1 - 10), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 0, 220), 1, cv2.LINE_AA)

# Title Header & Infographic Bar
cv2.rectangle(canvas, (0, 0), (canvas_w, 130), (24, 24, 28), -1)
cv2.putText(canvas, "CINEMATIC CAMERA CHOREOGRAPHY & VIEWPORT TRAJECTORY", (off_x, 48), cv2.FONT_HERSHEY_DUPLEX, 1.05, (255, 255, 255), 2, cv2.LINE_AA)
cv2.putText(canvas, "Sheet 1: 6 Panels | Seamless Smootherstep Easing | Row Crane Dip | Final Grand Outro Zoom", (off_x, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 210, 255), 1, cv2.LINE_AA)
cv2.putText(canvas, "Audio Ducking: -16dB SFX Sidechaining preserves 100% Voiceover Clarity", (off_x, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (180, 255, 180), 1, cv2.LINE_AA)

# Bottom legend bar
cv2.rectangle(canvas, (0, canvas_h - 70), (canvas_w, canvas_h), (24, 24, 28), -1)
legend_text = "Legend: [Orange Path] Smooth Bezier Camera Motion  |  [Red Frame] Active Focus Viewport (Zoom 2.2x)  |  [Blue Badges] Sequential Panels 1 to 6"
cv2.putText(canvas, legend_text, (off_x, canvas_h - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (230, 230, 230), 1, cv2.LINE_AA)

art_dir = r"C:\Users\loper\.gemini\antigravity-ide\brain\158728a5-a939-4410-9555-755847fa7279"
out_img_path = os.path.join(art_dir, "camera_transition_choreography_map.jpg")
cv2.imwrite(out_img_path, canvas)
print(f"Camera Transition Map generated: {out_img_path}")
