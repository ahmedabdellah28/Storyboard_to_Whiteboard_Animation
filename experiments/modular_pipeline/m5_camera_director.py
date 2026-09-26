"""
Module 5: Camera & Progressive Whiteboard Director
File: experiments/modular_pipeline/m5_camera_director.py

Responsibilities:
1. Manages a Pristine Blank Whiteboard Canvas (starts 100% white; no future panels visible).
2. Directs the Cinematic Camera:
   - Initial Wide Shot -> Smooth Ease-In Zoom to Center Stage.
   - Synchronizes Character Drawing Phase followed by Typography Writing Phase.
   - Smooth Ease-Out Zoom while the completed panel slides into its designated slot.
   - Preserves completed panels progressively while keeping un-drawn panels 100% blank.
3. Renders high-resolution Hand Overlay with adaptive tilt.
"""
import os
import math
import cv2
import numpy as np
from typing import Dict, List, Any, Tuple

class CameraWhiteboardDirector:
    def __init__(self, hd_w: int = 1920, hd_h: int = 1080, hand_sprite_path: str = None):
        self.hd_w = hd_w
        self.hd_h = hd_h
        self.board_canvas = np.full((hd_h, hd_w, 3), 255, dtype=np.uint8)
        self.hand_bgr, self.hand_alpha, self.tip_anchor = self._load_hand_sprite(hand_sprite_path)
        
    def _load_hand_sprite(self, path: str):
        if path and os.path.exists(path):
            img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if img is not None:
                h, w = img.shape[:2]
                target_w = 420
                target_h = int(h * (target_w / float(w)))
                resized = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
                bgr = resized[:, :, :3]
                alpha = resized[:, :, 3].astype(np.float32) / 255.0
                tip_anchor = (int(target_w * 0.08), int(target_h * 0.05))
                return bgr, alpha, tip_anchor
        # Fallback
        target_w, target_h = 300, 300
        bgr = np.full((target_h, target_w, 3), (200, 160, 120), dtype=np.uint8)
        alpha = np.ones((target_h, target_w), dtype=np.float32)
        return bgr, alpha, (10, 10)
        
    def draw_hand(self, canvas: np.ndarray, tip_x: float, tip_y: float, tilt_deg: float = -30.0, opacity: float = 1.0):
        if opacity <= 0.01:
            return
        can_h, can_w = canvas.shape[:2]
        sh, sw = self.hand_bgr.shape[:2]
        tip_x_anchor, tip_y_anchor = self.tip_anchor
        
        M = cv2.getRotationMatrix2D((tip_x_anchor, tip_y_anchor), tilt_deg, 1.0)
        rot_bgr = cv2.warpAffine(self.hand_bgr, M, (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0))
        rot_alpha = cv2.warpAffine(self.hand_alpha, M, (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0) * opacity
        
        x1 = int(tip_x - tip_x_anchor)
        y1 = int(tip_y - tip_y_anchor)
        x2 = x1 + sw
        y2 = y1 + sh
        
        cx1 = max(0, x1)
        cy1 = max(0, y1)
        cx2 = min(can_w, x2)
        cy2 = min(can_h, y2)
        if cx2 <= cx1 or cy2 <= cy1:
            return
            
        sx1 = cx1 - x1
        sy1 = cy1 - y1
        sx2 = sx1 + (cx2 - cx1)
        sy2 = sy1 + (cy2 - cy1)
        
        sub_alpha = rot_alpha[sy1:sy2, sx1:sx2, np.newaxis]
        sub_bgr = rot_bgr[sy1:sy2, sx1:sx2]
        can_roi = canvas[cy1:cy2, cx1:cx2]
        canvas[cy1:cy2, cx1:cx2] = (can_roi * (1.0 - sub_alpha) + sub_bgr * sub_alpha).astype(np.uint8)

    def render_panel_transition(
        self,
        panel_active_canvas: np.ndarray,
        center_rect: Tuple[int, int, int, int],
        slot_rect: Tuple[int, int, int, int],
        progress: float,
        is_zoom_in: bool = False
    ) -> np.ndarray:
        """
        Renders smooth camera transition between center stage and whiteboard slot.
        The rest of the whiteboard remains strictly blank/accumulated.
        """
        cx_c, cy_c, cw_c, ch_c = center_rect
        sx_s, sy_s, sw_s, sh_s = slot_rect
        
        # Cubic easing
        t_eased = progress * progress * (3.0 - 2.0 * progress)
        
        frame = self.board_canvas.copy()
        
        if is_zoom_in:
            # Zoom In: From Slot (or slightly scaled) to Center
            cur_x = int(sx_s + t_eased * (cx_c - sx_s))
            cur_y = int(sy_s + t_eased * (cy_c - sy_s))
            cur_w = max(10, int(sw_s + t_eased * (cw_c - sw_s)))
            cur_h = max(10, int(sh_s + t_eased * (ch_c - sh_s)))
        else:
            # Zoom Out: From Center to Slot on the Whiteboard
            cur_x = int(cx_c + t_eased * (sx_s - cx_c))
            cur_y = int(cy_c + t_eased * (sy_s - cy_c))
            cur_w = max(10, int(cw_c + t_eased * (sw_s - cw_c)))
            cur_h = max(10, int(ch_c + t_eased * (sh_s - ch_c)))
            
        scaled_panel = cv2.resize(panel_active_canvas, (cur_w, cur_h), 
                                  interpolation=cv2.INTER_AREA if cur_w < cw_c * 0.7 else cv2.INTER_LANCZOS4)
        
        # Place onto canvas cleanly
        y2 = min(self.hd_h, cur_y + cur_h)
        x2 = min(self.hd_w, cur_x + cur_w)
        frame[cur_y:y2, cur_x:x2] = scaled_panel[:y2-cur_y, :x2-cur_x]
        return frame

    def commit_panel_to_board(self, panel_completed_img: np.ndarray, slot_rect: Tuple[int, int, int, int]):
        """
        Permanently embeds a completed panel into the cumulative whiteboard canvas.
        All other un-drawn areas remain 100% blank white.
        """
        sx, sy, sw, sh = slot_rect
        scaled = cv2.resize(panel_completed_img, (sw, sh), interpolation=cv2.INTER_AREA)
        y2 = min(self.hd_h, sy + sh)
        x2 = min(self.hd_w, sx + sw)
        self.board_canvas[sy:y2, sx:x2] = scaled[:y2-sy, :x2-sx]
