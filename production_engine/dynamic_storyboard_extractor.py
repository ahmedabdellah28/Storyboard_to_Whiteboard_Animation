"""
Dynamic Storyboard Extractor Engine
Automatically discovers rows and cells in storyboard images, merges fragmented cuts,
extracts clean feathered BGRA assets, and generates the Arabic Handwriting Title Banner.
"""
import os
import sys
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    """Safely loads images from paths containing non-ASCII / Unicode characters on Windows."""
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
        return cv2.imdecode(data, flags)
    except Exception as e:
        print(f"Error reading image {path}: {e}")
        return None

def imwrite_unicode(path, img):
    """Safely writes images to paths containing non-ASCII / Unicode characters on Windows."""
    try:
        ext = os.path.splitext(str(path))[1]
        ok, buf = cv2.imencode(ext, img)
        if ok:
            buf.tofile(str(path))
            return True
        return False
    except Exception as e:
        print(f"Error writing image {path}: {e}")
        return False

class DynamicStoryboardExtractor:
    def __init__(self, section_dir):
        self.section_dir = section_dir
        self.storyboard_path = os.path.join(section_dir, "storyboard.png")
        self.assets_dir = os.path.join(section_dir, "assets")
        os.makedirs(self.assets_dir, exist_ok=True)

    def generate_title_banner(self, title_text, output_path=None):
        """Generates an authentic Arabic Handwriting Title Banner with underline."""
        if output_path is None:
            output_path = os.path.join(self.assets_dir, "r0_00_title_banner.png")

        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            reshaped = arabic_reshaper.reshape(title_text)
            bidi_t = get_display(reshaped)
        except Exception:
            bidi_t = title_text

        w, h = 1000, 220
        img = Image.new('RGBA', (w, h), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        font_paths = [
            'C:/Windows/Fonts/arialbd.ttf',
            'C:/Windows/Fonts/tahomabd.ttf',
            'C:/Windows/Fonts/seguiemj.ttf'
        ]
        font = None
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, 60)
                    break
                except Exception:
                    pass
        if font is None:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), bidi_t, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (w - tw) // 2
        ty = (h - th) // 2 - 14

        draw.text((tx, ty), bidi_t, font=font, fill=(25, 25, 30, 255))
        line_y = ty + th + 16
        draw.line([(tx - 25, line_y), (tx + tw + 25, line_y)], fill=(35, 35, 40, 255), width=6)

        img.save(output_path)
        return output_path

    def detect_rows(self, img_bgr):
        """Detects horizontal rows by finding horizontal dividing lines/valleys."""
        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # Invert: drawing/lines are dark (< 240)
        drawing_mask = (gray < 240).astype(np.uint8)
        
        # Horizontal projection
        row_density = np.sum(drawing_mask, axis=1) / float(w)
        
        # Find horizontal valleys where density drops significantly
        is_valley = row_density < 0.04
        
        # Group contiguous valley rows
        transitions = np.diff(is_valley.astype(int))
        split_points = np.where(transitions != 0)[0]
        
        # If valleys are detected, use them. Otherwise, default to 5 equal horizontal bands.
        valleys = []
        for i in range(len(split_points) - 1):
            if is_valley[split_points[i] + 1]:
                valleys.append((split_points[i] + split_points[i+1]) // 2)
        
        rows = []
        prev_y = 10
        for vy in valleys:
            if vy - prev_y > 100:
                rows.append((prev_y, vy))
                prev_y = vy
        if h - prev_y > 100:
            rows.append((prev_y, h - 10))
            
        if len(rows) < 3: # Fallback to standard 5-row storyboard grid
            step = h / 5.0
            rows = [(int(i * step), int((i + 1) * step)) for i in range(5)]
            
        return rows

    def detect_columns_in_row(self, row_crop):
        """Detects vertical column boundaries inside a single row crop."""
        rh, rw = row_crop.shape[:2]
        gray = cv2.cvtColor(row_crop, cv2.COLOR_BGR2GRAY)
        drawing_mask = (gray < 235).astype(np.uint8)
        
        # Vertical projection across row
        col_density = np.sum(drawing_mask, axis=0) / float(rh)
        
        # Find valleys (blank vertical margins or divider lines)
        is_valley = col_density < 0.015
        
        intervals = []
        in_content = False
        start_x = 0
        
        for x in range(rw):
            if not is_valley[x] and not in_content:
                in_content = True
                start_x = x
            elif is_valley[x] and in_content:
                in_content = False
                if x - start_x > 25: # minimum element width
                    intervals.append((start_x, x))
                    
        if in_content and rw - start_x > 25:
            intervals.append((start_x, rw))
            
        # Merge fragmented cuts: if distance between intervals is very small (< 15px)
        # or if an interval is extremely narrow (< 60px) adjacent to a character, merge them
        merged = []
        for iv in intervals:
            if not merged:
                merged.append(iv)
            else:
                prev_st, prev_en = merged[-1]
                gap = iv[0] - prev_en
                width = iv[1] - iv[0]
                prev_width = prev_en - prev_st
                
                # Merge if gap is small or one piece is too thin to be a standalone cell
                if gap < 20 or (width < 65 and gap < 40) or (prev_width < 65 and gap < 40):
                    merged[-1] = (prev_st, iv[1])
                else:
                    merged.append(iv)
                    
        return merged

    def extract_assets(self, cell_descriptions=None):
        """Extracts all clean BGRA assets from storyboard and writes metadata.json."""
        if not os.path.exists(self.storyboard_path):
            raise FileNotFoundError(f"Storyboard not found at: {self.storyboard_path}")

        img = imread_unicode(self.storyboard_path)
        if img is None:
            raise ValueError(f"Could not load/decode storyboard image from: {self.storyboard_path}")
        h, w = img.shape[:2]

        rows = self.detect_rows(img)
        print(f"[EXTRACTOR] Detected {len(rows)} storyboard rows.")

        extracted = {}
        counter = 1

        for r_idx, (y1, y2) in enumerate(rows, 1):
            row_crop = img[y1:y2, 0:w]
            cols = self.detect_columns_in_row(row_crop)
            print(f"  Row {r_idx}: {len(cols)} cells detected.")

            for c_idx, (x1, x2) in enumerate(cols, 1):
                pad = 4
                px1 = max(0, x1 - pad)
                py1 = max(0, y1 - pad)
                px2 = min(w, x2 + pad)
                py2 = min(h, y2 + pad)

                crop = img[py1:py2, px1:px2]
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                is_fg = gray < 240

                mask = is_fg.astype(np.uint8) * 255
                k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

                ys, xs = np.where(mask > 0)
                if len(xs) > 0 and len(ys) > 0:
                    tx1, tx2 = np.min(xs), np.max(xs)
                    ty1, ty2 = np.min(ys), np.max(ys)

                    tight_crop = crop[ty1:ty2+1, tx1:tx2+1]
                    tight_mask = mask[ty1:ty2+1, tx1:tx2+1]

                    bgra = np.dstack([tight_crop, tight_mask])
                    aid = f"r{r_idx}_{c_idx:02d}_elem"
                    
                    # If description provided in list
                    desc = f"Row {r_idx} Element {c_idx}"
                    if cell_descriptions and counter - 1 < len(cell_descriptions):
                        custom_aid, desc = cell_descriptions[counter - 1][:2]
                        aid = custom_aid

                    out_name = f"{aid}.png"
                    imwrite_unicode(os.path.join(self.assets_dir, out_name), bgra)

                    actual_w = tx2 - tx1 + 1
                    actual_h = ty2 - ty1 + 1
                    area = int(np.count_nonzero(tight_mask))

                    extracted[aid] = {
                        "file": out_name,
                        "row": r_idx,
                        "col": c_idx,
                        "desc": desc,
                        "orig_box": [int(px1 + tx1), int(py1 + ty1), int(actual_w), int(actual_h)],
                        "orig_size": [int(actual_w), int(actual_h)],
                        "area": area
                    }
                    counter += 1

        # Save metadata
        meta_path = os.path.join(self.assets_dir, "metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(extracted, f, indent=2, ensure_ascii=False)

        print(f"✅ Extracted {len(extracted)} assets saved to: {self.assets_dir}")
        return extracted

    def extract_single_box(self, img_bgr, box, pad=4):
        """Extracts a tight clean RGBA asset from a bounding box [x, y, w, h]."""
        h, w = img_bgr.shape[:2]
        bx, by, bw, bh = [int(v) for v in box]
        px1 = max(0, bx - pad)
        py1 = max(0, by - pad)
        px2 = min(w, bx + bw + pad)
        py2 = min(h, by + bh + pad)

        if px2 <= px1 or py2 <= py1:
            return None, [bx, by, bw, bh], 0

        crop = img_bgr[py1:py2, px1:px2]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        is_fg = gray < 240

        mask = is_fg.astype(np.uint8) * 255
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

        ys, xs = np.where(mask > 0)
        if len(xs) > 0 and len(ys) > 0:
            tx1, tx2 = int(np.min(xs)), int(np.max(xs))
            ty1, ty2 = int(np.min(ys)), int(np.max(ys))
            tight_crop = crop[ty1:ty2+1, tx1:tx2+1]
            tight_mask = mask[ty1:ty2+1, tx1:tx2+1]
            bgra = np.dstack([tight_crop, tight_mask])
            actual_w = tx2 - tx1 + 1
            actual_h = ty2 - ty1 + 1
            area = int(np.count_nonzero(tight_mask))
            actual_box = [int(px1 + tx1), int(py1 + ty1), int(actual_w), int(actual_h)]
            return bgra, actual_box, area
        else:
            # Fallback to direct crop if no distinct foreground lines found
            bgra = cv2.cvtColor(crop, cv2.COLOR_BGR2BGRA)
            actual_box = [px1, py1, px2 - px1, py2 - py1]
            return bgra, actual_box, actual_box[2] * actual_box[3]

    def recrop_and_save_asset(self, aid, box, desc="Custom Element"):
        """Re-crops an asset from storyboard.png given box [x, y, w, h] and writes PNG & returns metadata."""
        if not os.path.exists(self.storyboard_path):
            raise FileNotFoundError(f"Storyboard not found: {self.storyboard_path}")
        img = imread_unicode(self.storyboard_path)
        if img is None:
            raise ValueError(f"Could not load/decode storyboard image from: {self.storyboard_path}")
        bgra, actual_box, area = self.extract_single_box(img, box)
        if bgra is None:
            return None

        out_name = f"{aid}.png"
        out_path = os.path.join(self.assets_dir, out_name)
        imwrite_unicode(out_path, bgra)

        return {
            "file": out_name,
            "orig_box": actual_box,
            "bbox": actual_box,
            "orig_size": [actual_box[2], actual_box[3]],
            "area": area,
            "desc": desc,
            "excluded": False,
        }
