import cv2
import numpy as np

# Load key extracted assets from experiments/exact_contour_assets/
keys = [
    ("01_giant_red_apple", "1. Giant Apple"),
    ("08_roman_soldier", "8. Roman Soldier"),
    ("09_horse_cart_apples", "9. Horse & Cart"),
    ("11_farmer_planting", "11. Farmer Planting"),
    ("18_sliced_apples_juice", "18. Sliced Apple & Juice"),
    ("26_refrigerator_modern_apples", "26. Modern Fridge"),
]

card_w, card_h = 360, 360
cards = []

for name, title in keys:
    path = f"experiments/exact_contour_assets/{name}.png"
    rgba = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    ch, cw = rgba.shape[:2]
    
    # Scale to fit nicely in 300x300 while preserving aspect ratio
    scale = min(280.0 / cw, 280.0 / ch, 1.0)
    nw, nh = int(cw * scale), int(ch * scale)
    resized = cv2.resize(rgba, (nw, nh), interpolation=cv2.INTER_AREA)
    
    card = np.full((card_h, card_w, 3), 255, dtype=np.uint8)
    ox = (card_w - nw) // 2
    oy = (card_h - nh) // 2
    
    # Extract contour of resized asset
    mask = (resized[:, :, 3] > 10).astype(np.uint8)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    # Overlay asset
    alpha = resized[:, :, 3].astype(np.float32) / 255.0
    alpha3 = np.repeat(alpha[:, :, np.newaxis], 3, axis=2)
    bgr = resized[:, :, :3].astype(np.float32)
    roi = card[oy:oy+nh, ox:ox+nw].astype(np.float32)
    card[oy:oy+nh, ox:ox+nw] = np.clip(bgr * alpha3 + roi * (1.0 - alpha3), 0, 255).astype(np.uint8)
    
    # Draw vibrant organic contour outline (ZERO RECTANGLES)
    offset_cnts = [c + np.array([[[ox, oy]]]) for c in cnts]
    cv2.drawContours(card, offset_cnts, -1, (220, 140, 20), 2, cv2.LINE_AA)
    
    # Title badge
    cv2.rectangle(card, (10, 10), (card_w - 10, 42), (245, 245, 245), -1)
    cv2.putText(card, title, (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1, cv2.LINE_AA)
    
    cards.append(card)

row1 = np.hstack(cards[:3])
row2 = np.hstack(cards[3:])
grid = np.vstack([row1, row2])

# Add header
header = np.full((60, grid.shape[1], 3), 245, dtype=np.uint8)
cv2.putText(header, "Exact Organic Silhouette Contours (Zero Rectangles / 100% Pure Contour Isolation)", (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 0.70, (20, 20, 20), 2, cv2.LINE_AA)

final_img = np.vstack([header, grid])
cv2.imwrite("experiments/inspect_key_contours.jpg", final_img)
print("Saved experiments/inspect_key_contours.jpg")
