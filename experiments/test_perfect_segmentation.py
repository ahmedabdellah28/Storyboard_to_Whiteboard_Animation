import cv2
import numpy as np

p2 = cv2.imread("experiments/choreographed_layers/panel_02/clean_panel.png")
h, w = p2.shape[:2]

# Character region mask in Panel 2:
# Saturn is top: y < 290 and x < 480
# Warning is bottom-center: y > 750 and 420 < x < 620
# Stressed person is bottom-right: x > 550 and y > 600
# Math symbols is mid-right: x > 550 and 360 < y < 650
# Charts is top-right: x > 520 and y < 360

# Let's create an exact spatial mask for the Profile Character
char_mask = np.zeros((h, w), dtype=np.uint8)
# Character boundary: roughly x from 100 to 570, y from 220 to 860
# Exclude saturn (y < 280), exclude warning (x > 450 and y > 760)
for y in range(220, 860):
    for x in range(100, 570):
        # Exclude saturn
        if y < 290 and x < 350:
            continue
        # Exclude warning triangle
        if y > 760 and x > 440:
            continue
        # If pixel is not pure background white
        # Clean white paper in this image is RGB > 248
        b, g, r = p2[y, x]
        if min(b, g, r) < 245 or max(b, g, r) - min(b, g, r) > 8:
            char_mask[y, x] = 255

# Fill small interior holes (e.g. highlights or light skin)
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
char_mask_closed = cv2.morphologyEx(char_mask, cv2.MORPH_CLOSE, kernel)

# Find convex hull or fill contours to ensure face interior is 100% solid
contours, _ = cv2.findContours(char_mask_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
solid_char_mask = np.zeros((h, w), dtype=np.uint8)
for cnt in contours:
    if cv2.contourArea(cnt) > 2000:
        cv2.drawContours(solid_char_mask, [cnt], -1, 255, -1)

# Inside this solid mask, the alpha should be 255
b, g, r = cv2.split(p2)
char_rgba = cv2.merge([b, g, r, solid_char_mask])

# Save and inspect
cv2.imwrite("experiments/test_p2_char_solid.png", char_rgba)
print("Saved experiments/test_p2_char_solid.png")
