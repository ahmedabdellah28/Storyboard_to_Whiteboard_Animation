"""
Hand Compositor — Fast Alpha Blending of Drawing Hand Sprite onto Live Canvas.
"""
import os
import cv2
import numpy as np
from typing import Optional, Tuple


def load_hand_asset_bgra(hand_path: str, mask_path: str) -> Optional[np.ndarray]:
    """Loads drawing hand image and attaches its alpha mask."""
    if not os.path.exists(hand_path):
        return None
    try:
        hand_bytes = np.fromfile(str(hand_path), dtype=np.uint8)
        hand_img = cv2.imdecode(hand_bytes, cv2.IMREAD_COLOR)
        if hand_img is None:
            return None

        hh, hw = hand_img.shape[:2]

        if os.path.exists(mask_path):
            mask_bytes = np.fromfile(str(mask_path), dtype=np.uint8)
            mask_img = cv2.imdecode(mask_bytes, cv2.IMREAD_GRAYSCALE)
            if mask_img is not None:
                if mask_img.shape[:2] != (hh, hw):
                    mask_img = cv2.resize(mask_img, (hw, hh), interpolation=cv2.INTER_LINEAR)
                b, g, r = cv2.split(hand_img)
                return cv2.merge([b, g, r, mask_img])

        # Default fallback alpha channel
        gray = cv2.cvtColor(hand_img, cv2.COLOR_BGR2GRAY)
        _, alpha = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)
        b, g, r = cv2.split(hand_img)
        return cv2.merge([b, g, r, alpha])
    except Exception as e:
        print(f"[HandCompositor] Error loading hand asset: {e}")
        return None


def composite_hand_on_canvas_fast(
    canvas: np.ndarray,
    hand_bgra: np.ndarray,
    tip_x_anchor: int,
    tip_y_anchor: int,
    target_x: int,
    target_y: int
) -> np.ndarray:
    """Fast alpha blend of hand sprite onto canvas frame."""
    frame = canvas.copy()
    hh, hw = hand_bgra.shape[:2]
    cw, ch = canvas.shape[1], canvas.shape[0]

    hx = int(target_x - tip_x_anchor)
    hy = int(target_y - tip_y_anchor)

    x1_src = max(0, -hx)
    y1_src = max(0, -hy)
    x2_src = min(hw, cw - hx)
    y2_src = min(hh, ch - hy)

    x1_dst = max(0, hx)
    y1_dst = max(0, hy)
    x2_dst = min(cw, hx + hw)
    y2_dst = min(ch, hy + hh)

    if x1_src >= x2_src or y1_src >= y2_src or x1_dst >= x2_dst or y1_dst >= y2_dst:
        return frame

    hand_crop = hand_bgra[y1_src:y2_src, x1_src:x2_src]
    alpha = (hand_crop[:, :, 3].astype(np.float32) / 255.0)[:, :, np.newaxis]
    hand_bgr = hand_crop[:, :, :3].astype(np.float32)
    target_roi = frame[y1_dst:y2_dst, x1_dst:x2_dst].astype(np.float32)

    blended = (hand_bgr * alpha + target_roi * (1.0 - alpha)).astype(np.uint8)
    frame[y1_dst:y2_dst, x1_dst:x2_dst] = blended
    return frame
