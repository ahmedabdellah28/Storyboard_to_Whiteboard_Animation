import cv2
import numpy as np

# Load the pure extracted assets from exact_contour_assets
apple_rgba = cv2.imread("experiments/exact_contour_assets/01_giant_red_apple.png", cv2.IMREAD_UNCHANGED)
soldier_rgba = cv2.imread("experiments/exact_contour_assets/07_roman_soldier.png", cv2.IMREAD_UNCHANGED)

card_w = 420
card_h = 420

def create_box_card(rgba, title_text):
    h_c, w_c = rgba.shape[:2]
    card = np.full((card_h, card_w, 3), 255, dtype=np.uint8)
    ox = (card_w - w_c) // 2
    oy = (card_h - h_c) // 2
    
    alpha = rgba[:, :, 3].astype(np.float32) / 255.0
    alpha3 = np.repeat(alpha[:, :, np.newaxis], 3, axis=2)
    bgr = rgba[:, :, :3].astype(np.float32)
    roi = card[oy:oy+h_c, ox:ox+w_c].astype(np.float32)
    card[oy:oy+h_c, ox:ox+w_c] = np.clip(bgr * alpha3 + roi * (1.0 - alpha3), 0, 255).astype(np.uint8)
    
    # Draw RED RECTANGULAR BOX (Rejected by User)
    cv2.rectangle(card, (ox - 6, oy - 6), (ox + w_c + 6, oy + h_c + 6), (50, 50, 220), 3)
    
    # Header tag
    cv2.rectangle(card, (15, 15), (card_w - 15, 55), (240, 240, 245), -1)
    cv2.rectangle(card, (15, 15), (card_w - 15, 55), (50, 50, 220), 1)
    cv2.putText(card, "REJECTED: Box / Rectangle", (25, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (40, 40, 220), 2, cv2.LINE_AA)
    return card

def create_contour_card(rgba, title_text):
    h_c, w_c = rgba.shape[:2]
    card = np.full((card_h, card_w, 3), 255, dtype=np.uint8)
    ox = (card_w - w_c) // 2
    oy = (card_h - h_c) // 2
    
    alpha_mask = (rgba[:, :, 3] > 10).astype(np.uint8)
    contours, _ = cv2.findContours(alpha_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    alpha = rgba[:, :, 3].astype(np.float32) / 255.0
    alpha3 = np.repeat(alpha[:, :, np.newaxis], 3, axis=2)
    bgr = rgba[:, :, :3].astype(np.float32)
    roi = card[oy:oy+h_c, ox:ox+w_c].astype(np.float32)
    card[oy:oy+h_c, ox:ox+w_c] = np.clip(bgr * alpha3 + roi * (1.0 - alpha3), 0, 255).astype(np.uint8)
    
    # Draw CYAN/BLUE EXACT ORGANIC CONTOUR (Approved by User)
    offset_contours = [c + np.array([[[ox, oy]]]) for c in contours]
    cv2.drawContours(card, offset_contours, -1, (225, 140, 0), 3, cv2.LINE_AA)
    
    # Header tag
    cv2.rectangle(card, (15, 15), (card_w - 15, 55), (240, 255, 240), -1)
    cv2.rectangle(card, (15, 15), (card_w - 15, 55), (30, 160, 30), 1)
    cv2.putText(card, "APPROVED: Exact Organic Contour", (25, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 140, 20), 2, cv2.LINE_AA)
    return card

card_apple_box = create_box_card(apple_rgba, "Giant Apple")
card_apple_cnt = create_contour_card(apple_rgba, "Giant Apple")

card_soldier_box = create_box_card(soldier_rgba, "Roman Soldier")
card_soldier_cnt = create_contour_card(soldier_rgba, "Roman Soldier")

row1 = np.hstack([card_apple_box, card_apple_cnt])
row2 = np.hstack([card_soldier_box, card_soldier_cnt])
comparison = np.vstack([row1, row2])

# Add top banner
banner = np.full((70, comparison.shape[1], 3), 245, dtype=np.uint8)
cv2.putText(banner, "Exact Organic Contour Extraction (Zero Rectangles / Zero Boxes)", (30, 45),
            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (20, 20, 20), 2, cv2.LINE_AA)

final_comp = np.vstack([banner, comparison])
cv2.imwrite("experiments/contour_vs_box_comparison.jpg", final_comp)
print("Saved flawless comparison image: experiments/contour_vs_box_comparison.jpg")
