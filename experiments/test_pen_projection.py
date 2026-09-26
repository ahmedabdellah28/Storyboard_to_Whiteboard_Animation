import numpy as np
import cv2

# Canvas size: 4800 x 2700, Screen: 1920 x 1080
out_w, out_h = 1920, 1080
cx, cy = 900, 750
vw, vh = 2000, 1125

src_pts = np.float32([
    [cx - vw / 2.0, cy - vh / 2.0],
    [cx + vw / 2.0, cy - vh / 2.0],
    [cx - vw / 2.0, cy + vh / 2.0]
])
dst_pts = np.float32([[0, 0], [out_w, 0], [0, out_h]])
M = cv2.getAffineTransform(src_pts, dst_pts)

# Test center of Panel 1: (900, 750)
center_screen = M @ np.array([cx, cy, 1.0], dtype=np.float32)
print("Canvas Center (900, 750) -> Screen:", center_screen[:2])
assert abs(center_screen[0] - 960) < 1.0 and abs(center_screen[1] - 540) < 1.0, "Center projection mismatch!"

# Test top-left of Panel 1: (450, 300)
tl_screen = M @ np.array([450, 300, 1.0], dtype=np.float32)
print("Panel 1 Top-Left (450, 300) -> Screen:", tl_screen[:2])

# Test bottom-right of Panel 1: (1350, 1200)
br_screen = M @ np.array([1350, 1200, 1.0], dtype=np.float32)
print("Panel 1 Bottom-Right (1350, 1200) -> Screen:", br_screen[:2])

panel_w_screen = br_screen[0] - tl_screen[0]
panel_h_screen = br_screen[1] - tl_screen[1]
print(f"Panel size on 1080p screen: {panel_w_screen:.1f} x {panel_h_screen:.1f}")
print(f"Left margin: {tl_screen[0]:.1f}px, Right margin: {out_w - br_screen[0]:.1f}px")
print(f"Top margin: {tl_screen[1]:.1f}px, Bottom margin: {out_h - br_screen[1]:.1f}px")
print("PROJECTION VALIDATION PERFECT!")
