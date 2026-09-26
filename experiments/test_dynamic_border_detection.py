"""
Test Dynamic Panel Border Detection & Adaptive Suppression
Tests automatic detection of border lines (thickness, position, or absence of border)
across multiple diverse storyboard images.
"""
import os
import sys
import cv2
import numpy as np

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_root, 'kivy'))
sys.path.insert(0, os.path.join(_root, 'experiments', 'modular_pipeline'))

from m1_panel_extractor import DynamicPanelExtractor


class DynamicBorderDetector:
    """
    Intelligently detects and measures outer box border lines for any panel crop.
    Computes exact per-edge trim offsets (top, bottom, left, right) dynamically.
    If no border exists, trim is 0 (preserves art).
    """

    @staticmethod
    def detect_and_trim_panel_border(panel_crop: np.ndarray, max_scan_ratio: float = 0.12) -> dict:
        """
        Analyzes the perimeter of panel_crop to detect outer border lines.
        Returns:
            {
                "clean_crop": trimmed image without border lines,
                "insets": (trim_top, trim_bottom, trim_left, trim_right),
                "has_border": True/False,
                "border_thickness": approximate detected thickness
            }
        """
        h, w = panel_crop.shape[:2]
        if h < 20 or w < 20:
            return {"clean_crop": panel_crop, "insets": (0, 0, 0, 0), "has_border": False, "border_thickness": 0}

        gray = cv2.cvtColor(panel_crop, cv2.COLOR_BGR2GRAY) if len(panel_crop.shape) == 3 else panel_crop.copy()
        
        # Calculate ink intensity (distance from white background)
        # Background is typically > 220 in grayscale
        ink_density = (gray < 200).astype(np.float32)

        max_scan_y = max(4, int(h * max_scan_ratio))
        max_scan_x = max(4, int(w * max_scan_ratio))

        # --- 1. Detect TOP border ---
        trim_top = 0
        has_top_border = False
        for y in range(max_scan_y):
            row_density = np.mean(ink_density[y, :])
            # A border line spans a large portion of the row (> 40% dense ink)
            if row_density > 0.40:
                has_top_border = True
                trim_top = y + 1
            elif has_top_border and row_density < 0.20:
                # Border line has ended
                break
        if has_top_border:
            trim_top = min(max_scan_y, trim_top + 2) # 2px safety buffer beyond the line

        # --- 2. Detect BOTTOM border ---
        trim_bottom = 0
        has_bottom_border = False
        for y_offset in range(max_scan_y):
            y = h - 1 - y_offset
            row_density = np.mean(ink_density[y, :])
            if row_density > 0.40:
                has_bottom_border = True
                trim_bottom = y_offset + 1
            elif has_bottom_border and row_density < 0.20:
                break
        if has_bottom_border:
            trim_bottom = min(max_scan_y, trim_bottom + 2)

        # --- 3. Detect LEFT border ---
        trim_left = 0
        has_left_border = False
        for x in range(max_scan_x):
            col_density = np.mean(ink_density[:, x])
            if col_density > 0.40:
                has_left_border = True
                trim_left = x + 1
            elif has_left_border and col_density < 0.20:
                break
        if has_left_border:
            trim_left = min(max_scan_x, trim_left + 2)

        # --- 4. Detect RIGHT border ---
        trim_right = 0
        has_right_border = False
        for x_offset in range(max_scan_x):
            x = w - 1 - x_offset
            col_density = np.mean(ink_density[:, x])
            if col_density > 0.40:
                has_right_border = True
                trim_right = x_offset + 1
            elif has_right_border and col_density < 0.20:
                break
        if has_right_border:
            trim_right = min(max_scan_x, trim_right + 2)

        has_any_border = has_top_border or has_bottom_border or has_left_border or has_right_border
        
        # Apply trims safely
        y1 = trim_top
        y2 = h - trim_bottom if trim_bottom > 0 else h
        x1 = trim_left
        x2 = w - trim_right if trim_right > 0 else w

        if y2 <= y1 or x2 <= x1:
            clean_crop = panel_crop.copy()
            insets = (0, 0, 0, 0)
        else:
            clean_crop = panel_crop[y1:y2, x1:x2].copy()
            insets = (trim_top, trim_bottom, trim_left, trim_right)

        avg_thickness = int(np.mean([t for t in insets if t > 0])) if any(insets) else 0

        return {
            "clean_crop": clean_crop,
            "insets": insets,
            "has_border": has_any_border,
            "border_thickness": avg_thickness
        }


def test_on_all_images():
    test_dir = os.path.join(_root, 'test_images')
    out_debug_dir = os.path.join(_root, 'experiments', 'results', 'debug_dynamic_border')
    os.makedirs(out_debug_dir, exist_ok=True)

    images = [f for f in os.listdir(test_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"Testing Dynamic Border Detection on {len(images)} images...")

    for img_name in images:
        img_path = os.path.join(test_dir, img_name)
        img = cv2.imread(img_path)
        if img is None:
            continue

        base_name = os.path.splitext(img_name)[0]
        print(f"\n=======================================================")
        print(f"Image: {img_name} ({img.shape[1]}x{img.shape[0]})")
        
        raw_panels = DynamicPanelExtractor.extract_panels(img, border_inset=0)
        print(f"  • Extracted {len(raw_panels)} raw candidate panels.")

        for p_idx, p in enumerate(raw_panels):
            crop = p["crop"]
            res = DynamicBorderDetector.detect_and_trim_panel_border(crop)
            insets = res["insets"]
            has_b = res["has_border"]
            th = res["border_thickness"]
            clean_crop = res["clean_crop"]
            
            print(f"    - Panel {p_idx+1:02d}: size={crop.shape[1]}x{crop.shape[0]} | Has Border: {has_b} | Insets (T,B,L,R) = {insets} | Clean Size: {clean_crop.shape[1]}x{clean_crop.shape[0]}")
            
            orig_h, orig_w = crop.shape[:2]
            cl_h, cl_w = clean_crop.shape[:2]
            
            comp_h = max(orig_h, cl_h)
            canvas_comp = np.full((comp_h, orig_w + cl_w + 30, 3), 240, dtype=np.uint8)
            canvas_comp[:orig_h, :orig_w] = crop
            canvas_comp[:cl_h, orig_w + 30 : orig_w + 30 + cl_w] = clean_crop
            
            cv2.putText(canvas_comp, f"RAW (Border Detected: {has_b})", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.putText(canvas_comp, f"CLEAN (Insets: {insets})", (orig_w + 40, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 150, 0), 2)
            
            out_fn = os.path.join(out_debug_dir, f"{base_name}_panel_{p_idx+1:02d}_border_diff.png")
            cv2.imwrite(out_fn, canvas_comp)

    print(f"\n[Done] All visual comparison files saved to: {out_debug_dir}")

if __name__ == "__main__":
    test_on_all_images()
