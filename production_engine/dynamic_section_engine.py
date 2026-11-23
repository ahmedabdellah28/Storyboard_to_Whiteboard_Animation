import os
import sys
import json
import math
import wave
import time
import subprocess
import cv2
import numpy as np
from scipy.signal import resample

# Safe console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
try:
    from core.render_engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast
except ImportError:
    kivy_dir = os.path.join(ROOT_DIR, 'kivy')
    if kivy_dir not in sys.path:
        sys.path.insert(0, kivy_dir)
    # pyrefly: ignore [missing-import]
    from engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast


WIDTH, HEIGHT = 1920, 1080
FPS = 30
SR = 48000
CAM_ZOOM = 0.58
WORLD_HALF = (WIDTH / 2.0) / CAM_ZOOM  # ~1655.17 px

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    """Safely loads images from paths containing non-ASCII / Unicode characters on Windows."""
    try:
        data = np.fromfile(path, dtype=np.uint8)
        return cv2.imdecode(data, flags)
    except Exception as e:
        print(f"Error reading image {path}: {e}")
        return None

def imwrite_unicode(path, img):
    """Safely writes images to paths containing non-ASCII / Unicode characters on Windows."""
    try:
        ext = os.path.splitext(path)[1]
        ok, buf = cv2.imencode(ext, img)
        if ok:
            buf.tofile(path)
            return True
        return False
    except Exception as e:
        print(f"Error writing image {path}: {e}")
        return False

def smootherstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

def build_solid_inking_cache(img_bgra, duration_sec, fps=FPS, ring_step=5, brush_radius=12):
    """
    Authentic Outside-In Contour-Following Inking Cache.
    Uses build_gapless_orbital_path to trace the outer subject silhouette first,
    then progressively spirals into the interior (Outside-In Boundary Layer Infill).
    Ink appears ONLY under the pen tip — never in bulk ring pops.
    """
    try:
        from core.render_engine.render.concentric_engine import build_gapless_orbital_path
    except ImportError:
        # pyrefly: ignore [missing-import]
        from engine.render.concentric_engine import build_gapless_orbital_path


    h, w = img_bgra.shape[:2]
    total_f = max(1, int(round(duration_sec * fps)))
    alpha = img_bgra[:, :, 3]
    char_mask = (alpha > 20).astype(np.uint8) * 255

    # Step 1: Generate contour-following strokes (outer silhouette first)
    main_strokes = build_gapless_orbital_path(
        img_bgra[:, :, :3],
        ring_step=ring_step,
        sample_interval=3.0,
        brush_radius=brush_radius,
        drawing_direction='OUTSIDE_IN',
        mask=char_mask
    )

    # Step 2: Fill uncovered interior gaps with supplemental core strokes
    mask_test = np.zeros((h, w), dtype=np.uint8)
    for s in main_strokes:
        for i in range(len(s) - 1):
            p1 = (int(round(s[i][0])), int(round(s[i][1])))
            p2 = (int(round(s[i+1][0])), int(round(s[i+1][1])))
            cv2.line(mask_test, p1, p2, 255, brush_radius * 2)
            cv2.circle(mask_test, p2, brush_radius, 255, -1)

    uncovered = (char_mask > 0) & (mask_test == 0)
    num_u, lbl_u, stat_u, _ = cv2.connectedComponentsWithStats(uncovered.astype(np.uint8))
    core_strokes = []
    for i in range(1, num_u):
        if stat_u[i][4] < 3:
            continue
        comp_m = (lbl_u == i).astype(np.uint8) * 255
        comp_art = np.full_like(img_bgra[:, :, :3], 255)
        comp_art[comp_m > 0] = img_bgra[:, :, :3][comp_m > 0]
        sub_s = build_gapless_orbital_path(
            comp_art, ring_step=max(2, ring_step - 2),
            sample_interval=2.0, brush_radius=brush_radius,
            drawing_direction='OUTSIDE_IN'
        )
        core_strokes.extend(sub_s)

    all_strokes = [s for s in (main_strokes + core_strokes) if len(s) >= 2]

    # Step 3: Calculate total stroke distance for frame pacing
    total_dist = 0.0
    for stroke in all_strokes:
        for i in range(len(stroke) - 1):
            total_dist += math.hypot(stroke[i+1][0] - stroke[i][0], stroke[i+1][1] - stroke[i][1])

    # Reserve last 8% for 100% completion hold
    drawing_frames = max(1, int(round(total_f * 0.92)))
    hold_frames = total_f - drawing_frames
    step_dist = max(0.5, total_dist / float(drawing_frames))

    ink_mask = np.zeros((h, w), dtype=np.uint8)
    frames = []

    current_pen = (all_strokes[0][0][0], all_strokes[0][0][1]) if all_strokes else (w // 2, h // 2)
    accum = 0.0

    # Step 4: Frame-by-frame pen-tip synchronized ink reveal
    for stroke in all_strokes:
        last_pt = stroke[0]
        current_pen = last_pt

        for nxt_pt in stroke[1:]:
            p1 = (int(round(last_pt[0])), int(round(last_pt[1])))
            p2 = (int(round(nxt_pt[0])), int(round(nxt_pt[1])))
            cv2.line(ink_mask, p1, p2, 255, thickness=brush_radius * 2, lineType=cv2.LINE_AA)
            cv2.circle(ink_mask, p2, radius=brush_radius, color=255, thickness=-1, lineType=cv2.LINE_AA)

            d = math.hypot(nxt_pt[0] - last_pt[0], nxt_pt[1] - last_pt[1])
            accum += d

            while accum >= step_dist and len(frames) < drawing_frames:
                frame_alpha = np.minimum(alpha, ink_mask)
                f_bgra = img_bgra.copy()
                f_bgra[:, :, 3] = frame_alpha
                frames.append((f_bgra, (nxt_pt[0], nxt_pt[1]), 0.0))
                accum -= step_dist

            last_pt = nxt_pt
        current_pen = last_pt

    # Fill any remaining drawing frames
    while len(frames) < drawing_frames:
        frame_alpha = np.minimum(alpha, ink_mask)
        f_bgra = img_bgra.copy()
        f_bgra[:, :, 3] = frame_alpha
        frames.append((f_bgra, (current_pen[0], current_pen[1]), 0.0))

    # Step 5: Completion hold frames (100% revealed, no hand needed)
    final_bgra = img_bgra.copy()
    final_bgra[:, :, 3] = alpha
    for _ in range(hold_frames):
        frames.append((final_bgra, (current_pen[0], current_pen[1]), 0.0))

    return frames

def build_arabic_handwriting_cache(img_bgra, duration_sec, fps=FPS):
    """
    Authentic Arabic Right-to-Left Handwriting Inking Cache.
    Traces words sequentially from right to left (RTL progression).
    If an underline is present, lifts the pen and sweeps the underline from right to left.
    Never uses outer contour inking on text.
    """
    h, w = img_bgra.shape[:2]
    total_f = max(1, int(round(duration_sec * fps)))
    alpha = img_bgra[:, :, 3]

    row_sums = np.sum(alpha > 20, axis=1)
    nonzero_rows = np.where(row_sums > 0)[0]
    if len(nonzero_rows) == 0:
        return [(img_bgra.copy(), (w // 2, h // 2), 0.0)] * total_f

    y_top, y_bottom = nonzero_rows[0], nonzero_rows[-1]
    active_h = y_bottom - y_top

    line_rows = np.where(row_sums > 0.35 * w)[0]
    if len(line_rows) > 0 and line_rows[0] > y_top + active_h * 0.5:
        split_y = line_rows[0] - 2
        line_y = float(np.mean(line_rows))
        has_line = True
    else:
        split_y = y_bottom
        line_y = float(y_bottom)
        has_line = False

    text_mask = np.zeros_like(alpha)
    text_mask[:split_y, :] = alpha[:split_y, :]

    line_mask = np.zeros_like(alpha)
    line_mask[split_y:, :] = alpha[split_y:, :]

    t_cols = np.where(np.sum(text_mask > 20, axis=0) > 0)[0]
    l_cols = np.where(np.sum(line_mask > 20, axis=0) > 0)[0]

    tx_start, tx_end = (t_cols[-1], t_cols[0]) if len(t_cols) > 0 else (w - 10, 10)
    lx_start, lx_end = (l_cols[-1], l_cols[0]) if len(l_cols) > 0 else (w - 10, 10)

    y_centers = {}
    default_ty = float((y_top + split_y) // 2)
    last_ty = default_ty
    for x in range(w):
        ys = np.where(text_mask[:, x] > 20)[0]
        if len(ys) > 0:
            last_ty = float(np.mean(ys))
        y_centers[x] = last_ty

    has_line = len(l_cols) > 10
    if has_line:
        f_text = max(1, int(round(total_f * 0.68)))
        f_fly = max(1, int(round(total_f * 0.06)))
        f_line = max(1, int(round(total_f * 0.16)))
        f_hold = total_f - f_text - f_fly - f_line
    else:
        f_text = max(1, int(round(total_f * 0.85)))
        f_fly = 0
        f_line = 0
        f_hold = total_f - f_text

    frames = []

    # Phase 1: Text handwriting (Right to Left)
    for i in range(f_text):
        p = i / float(max(1, f_text - 1))
        cur_x = int(round(tx_start - p * (tx_start - tx_end)))
        base_y = y_centers.get(cur_x, default_ty)
        oscillation = math.sin(p * math.pi * 14.0) * 3.5
        cur_y = base_y + oscillation

        rev_alpha = np.zeros_like(alpha)
        rev_alpha[:split_y, cur_x:] = text_mask[:split_y, cur_x:]

        f_bgra = img_bgra.copy()
        f_bgra[:, :, 3] = rev_alpha
        frames.append((f_bgra, (float(cur_x), float(cur_y)), 0.0))

    if has_line:
        # Phase 2: Lift and fly to underline start
        p_start_fly = (float(tx_end), float(y_centers.get(tx_end, default_ty)))
        p_end_fly = (float(lx_start), float(line_y))
        for i in range(f_fly):
            p = (i + 1) / float(f_fly)
            fx = p_start_fly[0] + p * (p_end_fly[0] - p_start_fly[0])
            fy = p_start_fly[1] + p * (p_end_fly[1] - p_start_fly[1]) - math.sin(p * math.pi) * 15.0

            f_bgra = img_bgra.copy()
            f_bgra[:, :, 3] = text_mask
            frames.append((f_bgra, (fx, fy), 0.0))

        # Phase 3: Underline stroke (Right to Left)
        for i in range(f_line):
            p = i / float(max(1, f_line - 1))
            cur_lx = int(round(lx_start - p * (lx_start - lx_end)))

            rev_alpha = text_mask.copy()
            rev_alpha[split_y:, cur_lx:] = line_mask[split_y:, cur_lx:]

            f_bgra = img_bgra.copy()
            f_bgra[:, :, 3] = rev_alpha
            frames.append((f_bgra, (float(cur_lx), float(line_y)), 0.0))

    # Phase 4: Hold 100% revealed
    final_bgra = img_bgra.copy()
    final_bgra[:, :, 3] = alpha
    for _ in range(f_hold):
        frames.append((final_bgra, (float(lx_end if has_line else tx_end), float(line_y if has_line else default_ty)), 0.0))

    return frames

def blend_sprite_screen(frame, sprite_bgra, scr_x, scr_y, scr_w, scr_h, alpha_mult=1.0):
    if sprite_bgra is None or sprite_bgra.size == 0 or frame is None:
        return
    sp_h, sp_w = sprite_bgra.shape[:2]
    if sp_h <= 0 or sp_w <= 0 or scr_w <= 2 or scr_h <= 2:
        return

    fh, fw = frame.shape[:2] if hasattr(frame, "shape") else (HEIGHT, WIDTH)
    x1, y1 = scr_x, scr_y
    x2, y2 = scr_x + scr_w, scr_y + scr_h
    if x2 <= 0 or x1 >= fw or y2 <= 0 or y1 >= fh:
        return

    clip_x1, clip_y1 = max(0, x1), max(0, y1)
    clip_x2, clip_y2 = min(fw, x2), min(fh, y2)
    dst_w, dst_h = clip_x2 - clip_x1, clip_y2 - clip_y1
    if dst_w <= 0 or dst_h <= 0:
        return

    src_x1 = int(round((clip_x1 - x1) * sp_w / float(scr_w)))
    src_y1 = int(round((clip_y1 - y1) * sp_h / float(scr_h)))
    src_x2 = int(round((clip_x2 - x1) * sp_w / float(scr_w)))
    src_y2 = int(round((clip_y2 - y1) * sp_h / float(scr_h)))

    src_x1 = max(0, min(sp_w - 1, src_x1))
    src_y1 = max(0, min(sp_h - 1, src_y1))
    src_x2 = max(src_x1 + 1, min(sp_w, max(src_x1 + 1, src_x2)))
    src_y2 = max(src_y1 + 1, min(sp_h, max(src_y1 + 1, src_y2)))

    cropped_src = sprite_bgra[src_y1:src_y2, src_x1:src_x2]
    if cropped_src is None or cropped_src.size == 0 or cropped_src.shape[0] <= 0 or cropped_src.shape[1] <= 0:
        return

    resized_patch = cv2.resize(cropped_src, (dst_w, dst_h), interpolation=cv2.INTER_LINEAR)
    alpha = (resized_patch[:, :, 3].astype(np.float32) / 255.0) * alpha_mult
    alpha_3d = alpha[:, :, np.newaxis]

    roi = frame[clip_y1:clip_y2, clip_x1:clip_x2].astype(np.float32)
    fg = resized_patch[:, :, :3].astype(np.float32)

    blended = fg * alpha_3d + roi * (1.0 - alpha_3d)
    frame[clip_y1:clip_y2, clip_x1:clip_x2] = blended.astype(np.uint8)


class DynamicSectionEngine:
    """Unified dynamic pipeline for producing cinematic whiteboard video sections."""

    def __init__(self, section_dir):
        self.section_dir = section_dir
        self.assets_dir = os.path.join(section_dir, "assets")
        self.scratch_dir = os.path.join(section_dir, "scratch")
        os.makedirs(self.assets_dir, exist_ok=True)
        os.makedirs(self.scratch_dir, exist_ok=True)

        # Hand Sprite — multi-root discovery prioritizing core.render_engine
        candidate_hand_roots = [
            os.path.join(ROOT_DIR, "core", "render_engine", "data", "images"),
            os.path.join(ROOT_DIR, "data", "images"),
            os.path.join(ROOT_DIR, "kivy", "data", "images"),
        ]
        hand_path, hand_mask_path = None, None
        for root in candidate_hand_roots:
            hp = os.path.join(root, "drawing-hand.png")
            mp = os.path.join(root, "hand-mask.png")
            if os.path.exists(hp) and os.path.exists(mp):
                hand_path, hand_mask_path = hp, mp
                break

        raw_hand = load_hand_asset_bgra(hand_path, hand_mask_path) if hand_path else None

        if raw_hand is not None:
            hh, hw = raw_hand.shape[:2]
            target_h = 480
            target_w = int(hw * (target_h / hh))
            self.hand_bgra = cv2.resize(raw_hand, (target_w, target_h), interpolation=cv2.INTER_AREA)
            self.hand_tip_x = int(round(62 * (target_h / hh)))
            self.hand_tip_y = int(round(40 * (target_h / hh)))
        else:
            self.hand_bgra = None
            self.hand_tip_x, self.hand_tip_y = 0, 0

    def extract_assets(self, storyboard_path, asset_manifest, severing_cuts=None, bg_thresh=238):
        """Zero-box connected-components organic silhouette extraction."""
        print(f"\n[Extraction] Processing storyboard: {storyboard_path}")
        img = imread_unicode(storyboard_path)
        if img is None:
            raise FileNotFoundError(f"Storyboard not found: {storyboard_path}")

        H, W = img.shape[:2]
        is_bg = (img[:, :, 0] > bg_thresh) & (img[:, :, 1] > bg_thresh) & (img[:, :, 2] > bg_thresh)
        fg = (~is_bg).astype(np.uint8) * 255

        if severing_cuts:
            for y1, y2, x1, x2 in severing_cuts:
                fg[y1:y2, x1:x2] = 0

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fg_closed = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_closed, connectivity=8)

        metadata = {}
        extracted = []

        for item in asset_manifest:
            aid, (x1, y1, x2, y2), desc = item[0], item[1], item[2]
            matched = []
            for cid in range(1, num_labels):
                cx, cy = centroids[cid]
                area = stats[cid, cv2.CC_STAT_AREA]
                if x1 <= cx <= x2 and y1 <= cy <= y2 and area > 100:
                    matched.append(cid)

            mask = np.isin(labels, matched).astype(np.uint8) * 255
            bg_in = (img[:, :, 0] > 242) & (img[:, :, 1] > 242) & (img[:, :, 2] > 242)
            mask[bg_in] = 0

            mask_blur = cv2.GaussianBlur(mask, (3, 3), 0.5)
            alpha = np.clip(mask_blur.astype(np.float32) / 255.0 * 255.0, 0, 255).astype(np.uint8)

            coords = cv2.findNonZero(alpha)
            if coords is None:
                print(f"⚠️ Warning: No pixels found for {aid}!")
                continue

            bx, by, bw, bh = cv2.boundingRect(coords)
            crop_bgr = img[by:by+bh, bx:bx+bw]
            crop_alpha = alpha[by:by+bh, bx:bx+bw]

            rgba = cv2.merge([crop_bgr[:, :, 0], crop_bgr[:, :, 1], crop_bgr[:, :, 2], crop_alpha])
            out_file = os.path.join(self.assets_dir, f"{aid}.png")
            imwrite_unicode(out_file, rgba)

            row_num = int(aid[1]) if (len(aid) > 2 and aid[1].isdigit()) else 1
            meta = {
                "aid": aid,
                "desc": desc,
                "row": row_num,
                "storyboard_box": [int(bx), int(by), int(bw), int(bh)],
                "width": int(bw),
                "height": int(bh),
                "cids": matched,
                "file": f"{aid}.png"
            }
            metadata[aid] = meta
            extracted.append((aid, rgba, meta))
            print(f"  Extracted: {aid:38s} | Size: {bw:4d}x{bh:4d} | BBox: ({bx:4d}, {by:4d}, {bw:4d}, {bh:4d})")

        meta_path = os.path.join(self.assets_dir, "metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Visual Catalog Grid
        cat_cols = 4
        cat_rows = (len(extracted) + cat_cols - 1) // cat_cols
        cell_w, cell_h = 420, 320
        catalog = np.full((cat_rows * cell_h, cat_cols * cell_w, 3), 250, dtype=np.uint8)

        for idx, (aid, asset_rgba, meta) in enumerate(extracted):
            r, c = idx // cat_cols, idx % cat_cols
            cx0, cy0 = c * cell_w, r * cell_h
            cv2.rectangle(catalog, (cx0, cy0), (cx0 + cell_w - 1, cy0 + cell_h - 1), (220, 220, 220), 1)

            ah, aw = asset_rgba.shape[:2]
            scale = min((cell_w - 40) / float(aw), (cell_h - 60) / float(ah))
            nw, nh = int(aw * scale), int(ah * scale)
            scaled = cv2.resize(asset_rgba, (nw, nh), interpolation=cv2.INTER_AREA)

            off_x = cx0 + (cell_w - nw) // 2
            off_y = cy0 + 10 + (cell_h - 60 - nh) // 2
            alpha_s = scaled[:, :, 3].astype(float) / 255.0
            for ch in range(3):
                catalog[off_y:off_y+nh, off_x:off_x+nw, ch] = (
                    scaled[:, :, ch] * alpha_s + catalog[off_y:off_y+nh, off_x:off_x+nw, ch] * (1.0 - alpha_s)
                ).astype(np.uint8)

            lbl = f"{aid} ({aw}x{ah})"
            cv2.putText(catalog, lbl, (cx0 + 15, cy0 + cell_h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (40, 40, 40), 1, cv2.LINE_AA)

        cat_path = os.path.join(self.scratch_dir, "clean_assets_catalog.png")
        imwrite_unicode(cat_path, catalog)
        print(f"[Extraction] Catalog saved: {cat_path} (Total: {len(metadata)} assets)\n")
        return metadata

    def calculate_layout(self, layout_spec, base_scale=2.7, scale_overrides=None, row_gap_y=2000.0, base_y=800.0):
        """Calculates 4-row / 8-zone cinematic layout with guaranteed >750px offscreen clearance."""
        print("[Layout] Computing 8-zone world-space layout...")
        meta_path = os.path.join(self.assets_dir, "metadata.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        scale_overrides = scale_overrides or {}
        placed_elements = {}
        row_zones = {}

        for r_idx, row_data in layout_spec.items():
            row_y = base_y + (r_idx - 1) * row_gap_y
            row_placed = []

            # Zone A
            cur_x = row_data['zone_A']['x_start']
            za_start_x = cur_x
            for aid, gap in row_data['zone_A']['elements']:
                info = meta[aid]
                elem_scale = scale_overrides.get(aid, base_scale)
                w = int(info['width'] * elem_scale)
                h = int(info['height'] * elem_scale)
                y = row_y - (h / 2.0)
                row_placed.append({
                    'aid': aid, 'file': info['file'],
                    'x': cur_x, 'y': y, 'w': w, 'h': h,
                    'cx': cur_x + w / 2.0, 'cy': y + h / 2.0, 'zone': 'A'
                })
                cur_x += w + gap
            za_end_x = cur_x - (gap if 'gap' in locals() else 0)
            za_cam_x = (za_start_x + za_end_x) / 2.0

            # Zone B
            cur_x = row_data['zone_B']['x_start']
            zb_start_x = cur_x
            for aid, gap in row_data['zone_B']['elements']:
                info = meta[aid]
                elem_scale = scale_overrides.get(aid, base_scale)
                w = int(info['width'] * elem_scale)
                h = int(info['height'] * elem_scale)
                y = row_y - (h / 2.0)
                row_placed.append({
                    'aid': aid, 'file': info['file'],
                    'x': cur_x, 'y': y, 'w': w, 'h': h,
                    'cx': cur_x + w / 2.0, 'cy': y + h / 2.0, 'zone': 'B'
                })
                cur_x += w + gap
            zb_end_x = cur_x - (gap if 'gap' in locals() else 0)
            zb_cam_x = (zb_start_x + zb_end_x) / 2.0

            placed_elements[str(r_idx)] = row_placed
            row_zones[str(r_idx)] = {
                'row_y': row_y,
                'zone_A': [za_cam_x, row_y],
                'zone_B': [zb_cam_x, row_y],
                'za_span': [za_start_x, za_end_x],
                'zb_span': [zb_start_x, zb_end_x]
            }

            clearance_A_to_B = zb_start_x - (za_cam_x + WORLD_HALF)
            clearance_B_to_A = (zb_cam_x - WORLD_HALF) - za_end_x
            print(f"  Row {r_idx} (Y={row_y:.0f}): Zone A CamX={za_cam_x:.1f}, Zone B CamX={zb_cam_x:.1f} | Clearance: A→B={clearance_A_to_B:.0f}px, B→A={clearance_B_to_A:.0f}px")

        layout_json = os.path.join(self.section_dir, "placed_elements_layout.json")
        with open(layout_json, "w", encoding="utf-8") as f:
            json.dump({
                'scale': base_scale, 'zoom': CAM_ZOOM, 'world_half': WORLD_HALF,
                'elements': placed_elements, 'zones': row_zones
            }, f, indent=2, ensure_ascii=False)

        print(f"[Layout] Saved to {layout_json}\n")
        return layout_json

    @staticmethod
    def generate_sfx_from_staging(elements_staging, camera_pans=None):
        """
        Auto-generate enriched, synchronized SFX cues from element staging.
        Generates full-coverage, subtle sound design:
        - Inking pen drawing + sustained drawing strokes for long heroes + completion accents
        - Pop-ins with elastic bounce
        - Slides with swooshes and gentle settlement accents
        - Organic growth with blossom shimmers
        - Golden / pulse highlights with sparkles
        - Camera navigation whooshes
        """
        sfx_cues = []

        for elem in elements_staging:
            t = elem['t_start']
            dur = elem.get('t_dur', 1.5)
            anim = elem.get('type', 'slide_down')

            if anim == 'outside_in_pen':
                # Active inking completes at ~90% of dur when pen lifts
                draw_dur = round(dur * 0.90, 2)
                # Drawing sound duration precisely matched to active inking time (no overflow!)
                sfx_cues.append((t, 'marker', 0.38, draw_dur))
                # Gentle completion pop right as inking finishes
                sfx_cues.append((t + draw_dur, 'pop', 0.22))


            elif anim == 'jelly_pop':
                sfx_cues.append((t, 'pop', 0.35))

            elif anim in ('slide_down', 'slide_up'):
                sfx_cues.append((t, 'whoosh', 0.40))
                # Landing settlement accent
                sfx_cues.append((t + dur * 0.70, 'pop', 0.25))

            elif anim == 'organic_grow':
                sfx_cues.append((t, 'pop', 0.30))
                # Blossom / growth shimmer
                if dur > 1.0:
                    sfx_cues.append((t + dur * 0.55, 'chime', 0.25))

            elif anim in ('pulse_pop', 'golden_burst'):
                sfx_cues.append((t, 'chime', 0.35))
                sfx_cues.append((t + 0.15, 'pop', 0.25))

            elif anim == 'bounce_drop':
                sfx_cues.append((t, 'whoosh', 0.30))
                sfx_cues.append((t + dur * 0.45, 'bright_ping', 0.28))

            elif anim == 'slam_down':
                sfx_cues.append((t, 'whoosh', 0.35))
                sfx_cues.append((t + dur * 0.70, 'soft_impact', 0.45))

            elif anim == 'float_drift':
                sfx_cues.append((t, 'pop', 0.25))

        # Add whoosh sounds for camera pans (zone/row transitions)
        if camera_pans:
            for pan_time in camera_pans:
                sfx_cues.append((pan_time, 'whoosh', 0.45))

        sfx_cues.sort(key=lambda x: x[0])
        return sfx_cues

    @staticmethod
    def calculate_camera_pans(zone_order, zone_last_element_end, zone_first_element_start, get_cam_x_fn, default_pan_dur=0.85):
        """
        Calculates cinematic camera pan intervals between consecutive zones.
        
        CRITICAL WHITEBOARD RULE (Zero Blank Screen / Narration Hold):
        The camera MUST HOLD on the current zone during the narration / explanation ("الشرح")
        of the completed elements. It must NEVER pan away early to an empty zone leaving
        a blank white screen.
        
        The pan to z_to must occur just in time, concluding right as the first element of z_to
        is about to be drawn (pan_end = next_start - 0.05s).
        """
        cam_pans = []
        for i in range(len(zone_order) - 1):
            z_from = zone_order[i]
            z_to = zone_order[i + 1]
            
            if z_from not in zone_last_element_end or z_to not in zone_first_element_start:
                continue
                
            last_end = zone_last_element_end[z_from]
            next_start = zone_first_element_start[z_to]
            gap = next_start - last_end
            
            pan_dur = default_pan_dur
            pan_end = next_start - 0.05
            pan_start = pan_end - pan_dur
            
            min_hold = 0.20
            earliest_pan_start = last_end + min_hold
            
            if pan_start < earliest_pan_start:
                if gap > 0.5:
                    pan_start = earliest_pan_start
                    pan_dur = max(0.4, pan_end - pan_start)
                    pan_end = pan_start + pan_dur
                else:
                    pan_start = last_end
                    pan_end = max(next_start, pan_start + 0.4)
                    
            x_from = get_cam_x_fn(z_from)
            x_to = get_cam_x_fn(z_to)
            
            hold_time = pan_start - last_end
            cam_pans.append((pan_start, pan_end, x_from, x_to))
            print(f"  📷 Camera Pan: {z_from} -> {z_to} | [{pan_start:.2f}s .. {pan_end:.2f}s] (dur={pan_end-pan_start:.2f}s) | Explanation Hold: {hold_time:.2f}s")
            
        return cam_pans

    @staticmethod
    def build_horizontal_camera_trajectory(cam_pans, initial_x, fixed_y=800.0, cam_zoom=0.58):
        """Builds a pure horizontal camera trajectory function (Y fixed) using smootherstep easing."""
        def get_camera_state(t):
            if not cam_pans:
                return (initial_x, fixed_y, cam_zoom)
            if t < cam_pans[0][0]:
                return (cam_pans[0][2], fixed_y, cam_zoom)
            for pan_start, pan_end, x_from, x_to in cam_pans:
                if t < pan_start:
                    return (x_from, fixed_y, cam_zoom)
                elif t < pan_end:
                    p = smootherstep((t - pan_start) / (pan_end - pan_start))
                    cx = x_from + (x_to - x_from) * p
                    return (cx, fixed_y, cam_zoom)
            final_x = cam_pans[-1][3]
            return (final_x, fixed_y, cam_zoom)
        return get_camera_state


    def mix_master_audio(self, voiceover_path, sfx_cues, target_duration_s):
        """Mixes 48kHz stereo master audio with envelope ducking and SFX alignment."""
        out_audio = os.path.join(self.section_dir, "master_audio.wav")
        from production_engine.mix_section_audio import mix_section_audio
        mix_section_audio(voiceover_path, sfx_cues, out_audio, target_duration_s=target_duration_s)
        return out_audio

    def render_section(self, hero_configs, elements_staging, camera_trajectory_fn, duration_sec):
        """Renders 1080p 30fps whiteboard video with inking hand, smooth camera pans, and NVENC."""
        total_frames = int(round(duration_sec * FPS))
        print(f"\n[Render] Starting video render: {duration_sec:.2f}s ({total_frames} frames)...")

        # 1. Load assets
        assets = {}
        for f in os.listdir(self.assets_dir):
            if f.endswith(".png"):
                aid = os.path.splitext(f)[0]
                assets[aid] = imread_unicode(os.path.join(self.assets_dir, f), cv2.IMREAD_UNCHANGED)

        # 2. Pre-cache hero inking
        hero_cache = {}
        for h_name, t_start, t_dur in hero_configs:
            if h_name in assets:
                asset = assets[h_name]
                ah, aw = asset.shape[:2]
                if "title" in h_name.lower() or "text" in h_name.lower() or "banner" in h_name.lower():
                    cf = build_arabic_handwriting_cache(asset, t_dur, FPS)
                    hero_cache[h_name] = {'frames': cf, 'orig_size': (aw, ah)}
                    print(f"  ✍️ Pre-cached Arabic Handwriting: {h_name:30s} ({len(cf)} frames, {t_dur:.2f}s)")
                else:
                    cf = build_solid_inking_cache(asset, t_dur, FPS, ring_step=5)
                    hero_cache[h_name] = {'frames': cf, 'orig_size': (aw, ah)}
                    print(f"  Pre-cached Inking: {h_name:38s} ({len(cf)} frames, {t_dur:.2f}s)")

        # 3. Setup FFmpeg video pipe
        raw_video = os.path.join(self.section_dir, "raw_cinematic_panned.mp4")
        final_video = os.path.join(self.section_dir, "final_whiteboard_1080p.mp4")
        master_audio = os.path.join(self.section_dir, "master_audio.wav")

        nvenc_cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "bgr24", "-r", str(FPS),
            "-i", "-", "-c:v", "h264_nvenc", "-preset", "p7", "-cq", "18",
            "-g", "60", "-keyint_min", "30",
            "-bf", "2", "-pix_fmt", "yuv420p", raw_video
        ]
        libx264_cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "bgr24", "-r", str(FPS),
            "-i", "-", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
            "-g", "60", "-keyint_min", "30",
            "-pix_fmt", "yuv420p", raw_video
        ]

        log_path = os.path.join(self.section_dir, "ffmpeg_render.log")
        ffmpeg_log = open(log_path, "w", encoding="utf-8")
        try:
            pipe = subprocess.Popen(nvenc_cmd, stdin=subprocess.PIPE, stderr=ffmpeg_log)
            print("  Encoder: Hardware-accelerated NVIDIA NVENC (p7)")
        except Exception:
            pipe = subprocess.Popen(libx264_cmd, stdin=subprocess.PIPE, stderr=ffmpeg_log)
            print("  Encoder: CPU libx264 (ultrafast)")

        t0 = time.time()
        elements_staging.sort(key=lambda e: e.get('depth', 4))

        for f_idx in range(total_frames):
            time_s = f_idx / float(FPS)
            cam_x, cam_y, cam_zoom = camera_trajectory_fn(time_s)

            frame = np.full((HEIGHT, WIDTH, 3), 255, dtype=np.uint8)
            active_hand = None

            for elem in elements_staging:
                t_st = elem['t_start']
                t_du = elem['t_dur']
                aid = elem['asset']
                if time_s < t_st or aid not in assets:
                    continue

                fade_out_at = elem.get('fade_out_at')
                current_alpha = 1.0
                if fade_out_at is not None:
                    if time_s >= fade_out_at + 0.8:
                        continue
                    elif time_s >= fade_out_at:
                        fade_p = (time_s - fade_out_at) / 0.8
                        current_alpha = max(0.0, 1.0 - smootherstep(fade_p))

                wx, wy = elem['pos']
                ww, wh = elem['size']
                anim_type = elem.get('type', 'slide_down')

                rel_t = time_s - t_st
                prog = min(1.0, rel_t / max(0.001, t_du))

                scr_x = int(round((wx - cam_x) * cam_zoom + (WIDTH / 2.0)))
                scr_y = int(round((wy - cam_y) * cam_zoom + (HEIGHT / 2.0)))
                scr_w = int(round(ww * cam_zoom))
                scr_h = int(round(wh * cam_zoom))

                base_asset = assets[aid]

                if anim_type == 'outside_in_pen':
                    if prog < 1.0 and aid in hero_cache:
                        cf = hero_cache[aid]['frames']
                        sub_f = min(len(cf) - 1, int(round(prog * (len(cf) - 1))))
                        cur_spr, tip_pt, p_ang = cf[sub_f]
                        blend_sprite_screen(frame, cur_spr, scr_x, scr_y, scr_w, scr_h, alpha_mult=current_alpha)

                        orig_w, orig_h = hero_cache[aid]['orig_size']
                        tip_sx = scr_x + int(round(tip_pt[0] * (scr_w / float(orig_w))))
                        tip_sy = scr_y + int(round(tip_pt[1] * (scr_h / float(orig_h))))
                        active_hand = (tip_sx, tip_sy, p_ang)
                    else:
                        blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h, alpha_mult=current_alpha)

                elif anim_type == 'slide_down':
                    if prog < 1.0:
                        p = smootherstep(prog)
                        cur_y = scr_y - int(round(60 * (1.0 - p) * cam_zoom))
                        blend_sprite_screen(frame, base_asset, scr_x, cur_y, scr_w, scr_h, alpha_mult=p * current_alpha)
                    else:
                        blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h, alpha_mult=current_alpha)

                elif anim_type == 'slide_up':
                    if prog < 1.0:
                        p = smootherstep(prog)
                        cur_y = scr_y + int(round(60 * (1.0 - p) * cam_zoom))
                        blend_sprite_screen(frame, base_asset, scr_x, cur_y, scr_w, scr_h, alpha_mult=p)
                    else:
                        blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h)

                elif anim_type == 'jelly_pop':
                    if prog < 1.0:
                        osc = math.sin(prog * math.pi * 3.0) * math.exp(-prog * 4.0)
                        scale = (1.0 + 0.18 * osc) * prog
                        cur_w = int(round(scr_w * scale))
                        cur_h = int(round(scr_h * scale))
                        cur_x = scr_x + (scr_w - cur_w) // 2
                        cur_y = scr_y + (scr_h - cur_h) // 2
                        blend_sprite_screen(frame, base_asset, cur_x, cur_y, cur_w, cur_h, alpha_mult=min(1.0, prog * 1.5))
                    else:
                        blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h)

                elif anim_type == 'pulse_pop':
                    if prog < 1.0:
                        pulse = 1.0 + 0.15 * math.sin(prog * math.pi * 2.0)
                        cur_w = int(round(scr_w * pulse))
                        cur_h = int(round(scr_h * pulse))
                        cur_x = scr_x + (scr_w - cur_w) // 2
                        cur_y = scr_y + (scr_h - cur_h) // 2
                        blend_sprite_screen(frame, base_asset, cur_x, cur_y, cur_w, cur_h)
                    else:
                        blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h)

                elif anim_type == 'organic_grow':
                    if prog < 1.0:
                        scale_y = smootherstep(prog)
                        scale_x = 0.5 + 0.5 * smootherstep(prog)
                        cur_w = int(round(scr_w * scale_x))
                        cur_h = int(round(scr_h * scale_y))
                        cur_x = scr_x + (scr_w - cur_w) // 2
                        cur_y = scr_y + (scr_h - cur_h)
                        blend_sprite_screen(frame, base_asset, cur_x, cur_y, cur_w, cur_h, alpha_mult=min(1.0, prog * 1.8))
                    else:
                        blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h)

                elif anim_type == 'bounce_drop':
                    if prog < 1.0:
                        bounce = abs(math.cos(prog * math.pi * 2.2)) * math.exp(-prog * 3.5)
                        drop_offset = int(round(-120 * bounce * cam_zoom))
                        cur_y = scr_y + drop_offset
                        blend_sprite_screen(frame, base_asset, scr_x, cur_y, scr_w, scr_h, alpha_mult=min(1.0, prog * 2.5))
                    else:
                        blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h)

                elif anim_type == 'slam_down':
                    if prog < 1.0:
                        p = prog * prog * prog
                        cur_y = scr_y - int(round(140 * (1.0 - p) * cam_zoom))
                        squash = 1.0 + (0.20 * (1.0 - abs(prog - 0.85) / 0.15) if prog > 0.7 else 0.0)
                        cur_w = int(round(scr_w * squash))
                        cur_h = int(round(scr_h / squash))
                        cur_x = scr_x + (scr_w - cur_w) // 2
                        blend_sprite_screen(frame, base_asset, cur_x, cur_y, cur_w, cur_h, alpha_mult=min(1.0, prog * 3.0))
                    else:
                        blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h)

                elif anim_type == 'float_drift':
                    float_y = int(round(10 * math.sin((time_s - t_st) * 2.5) * cam_zoom))
                    if prog < 1.0:
                        p = smootherstep(prog)
                        blend_sprite_screen(frame, base_asset, scr_x, scr_y + float_y, scr_w, scr_h, alpha_mult=p)
                    else:
                        blend_sprite_screen(frame, base_asset, scr_x, scr_y + float_y, scr_w, scr_h)

                else:
                    blend_sprite_screen(frame, base_asset, scr_x, scr_y, scr_w, scr_h)

            if active_hand is not None and self.hand_bgra is not None:
                tx, ty, rot = active_hand
                if -100 <= tx <= WIDTH + 100 and -100 <= ty <= HEIGHT + 100:
                    frame = composite_hand_on_canvas_fast(frame, self.hand_bgra, self.hand_tip_x, self.hand_tip_y, tx, ty)

            pipe.stdin.write(frame.tobytes())

            if (f_idx + 1) % 300 == 0 or (f_idx + 1) == total_frames:
                el = time.time() - t0
                speed = (f_idx + 1) / max(0.001, el)
                pct = (f_idx + 1) / float(total_frames) * 100.0
                print(f"  Render progress: {f_idx + 1}/{total_frames} frames ({pct:.1f}%) [Speed: {speed:.1f} FPS, Time: {time_s:.2f}s]")

        pipe.stdin.close()
        pipe.wait()
        ffmpeg_log.close()

        # 4. Final Audio + Video Multiplexing
        mux_cmd = [
            "ffmpeg", "-y", "-i", raw_video, "-i", master_audio,
            "-c:v", "copy", "-c:a", "aac", "-ac", "2", "-b:a", "256k",
            "-movflags", "+faststart",
            "-shortest", final_video
        ]
        subprocess.run(mux_cmd, check=True, capture_output=True)
        print(f"🎉 Section video complete: {final_video} ({duration_sec:.2f}s)")
        return final_video

    def render_motion_plan(
        self,
        motion_plan_path: str,
        manifest_path: str,
        assets_dir: str,
        audio_path: str,
        output_path: str,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
    ):
        """Declaratively renders motion plan using DeclarativeMotionGraphicsEngine."""
        from production_engine.motion_graphics_engine import DeclarativeMotionGraphicsEngine
        engine = DeclarativeMotionGraphicsEngine(
            motion_plan_path=motion_plan_path,
            manifest_path=manifest_path,
            assets_dir=assets_dir,
            audio_path=audio_path,
            output_path=output_path,
            width=width,
            height=height,
            fps=fps,
        )
        return engine.render_preview_video()
