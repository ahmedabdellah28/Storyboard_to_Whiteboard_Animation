"""
Dynamic Decomposition & Organic Image Processing Module
Modular mathematical algorithms for the Deep Storyboard Engine:
1. Dynamic Panel & Grid Detection.
2. Dynamic Outer Frame Border Suppression.
3. Medial Axis Pinch-Point & Marker-Controlled Gradient Watershed Decomposition.
4. Smooth Bezier Air Transits and Orbital Waypoint Generation.
"""
import cv2
import numpy as np
from typing import List, Tuple, Dict, Any

def detect_panels_dynamically(img: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """
    Dynamically detects and sorts all panels in standard reading order
    (Top-to-Bottom rows, Left-to-Right columns).
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
    
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 5)
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    panels = []
    min_area = (h * w) * 0.03
    max_area = (h * w) * 0.95
    for c in cnts:
        x, y, bw, bh = cv2.boundingRect(c)
        area = bw * bh
        if min_area <= area <= max_area and bw > 0.12 * w and bh > 0.12 * h:
            panels.append((x, y, bw, bh))
            
    if not panels:
        panels = [(0, 0, w, h)]
    else:
        filtered = []
        for p in panels:
            x, y, bw, bh = p
            keep = True
            for f in filtered:
                fx, fy, fbw, fbh = f
                if abs(x - fx) < 20 and abs(y - fy) < 20:
                    keep = False
                    break
            if keep:
                filtered.append(p)
        panels = filtered
        
        avg_h = np.mean([p[3] for p in panels])
        row_threshold = avg_h * 0.5
        panels = sorted(panels, key=lambda p: (int(p[1] / row_threshold), p[0]))
        
    return panels

def suppress_outer_frame_borders(p_crop: np.ndarray, fg_raw: np.ndarray = None) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Detects and clears outer rectangular panel border frames so only artwork/characters are animated.
    Returns cleaned foreground mask and isolated subjects.
    """
    h_p, w_p = p_crop.shape[:2]
    if fg_raw is None:
        gray_p = cv2.cvtColor(p_crop, cv2.COLOR_BGR2GRAY) if len(p_crop.shape) == 3 else p_crop
        hsv_p = cv2.cvtColor(p_crop, cv2.COLOR_BGR2HSV) if len(p_crop.shape) == 3 else gray_p
        fg_raw = ((gray_p < 225) | (hsv_p[:, :, 1] > 18)).astype(np.uint8) * 255 if len(p_crop.shape) == 3 else (gray_p < 225).astype(np.uint8) * 255
        
    # Clear perimeter border ring
    b_margin = max(4, int(min(w_p, h_p) * 0.015))
    fg_work = fg_raw.copy()
    fg_work[:b_margin, :] = 0
    fg_work[-b_margin:, :] = 0
    fg_work[:, :b_margin] = 0
    fg_work[:, -b_margin:] = 0
    
    num_c, labels_c, stats_c, _ = cv2.connectedComponentsWithStats(fg_work)
    fg_clean = np.zeros_like(fg_work)
    subjects = []
    
    for c_i in range(1, num_c):
        bx, by, cbw, cbh, area = stats_c[c_i]
        is_outer_border = (cbw > 0.82 * w_p and cbh > 0.82 * h_p)
        if not is_outer_border and area > 40:
            fg_clean[labels_c == c_i] = 255
            subjects.append({
                "id": c_i,
                "mask": (labels_c == c_i).astype(np.uint8) * 255,
                "area": area,
                "centroid_x": bx + cbw / 2.0,
                "centroid_y": by + cbh / 2.0
            })
            
    subjects = sorted(subjects, key=lambda s: s["centroid_x"])
    return fg_clean, subjects

def extract_dynamic_organic_parts(fg_mask: np.ndarray, source_img: np.ndarray, min_parts: int = 3, max_parts: int = 6) -> List[Dict[str, Any]]:
    """
    Dynamically decomposes any foreground character/object into organic anatomical parts
    following natural gradient contours and anatomical pinch points with ZERO straight lines.
    """
    gray = cv2.cvtColor(source_img, cv2.COLOR_BGR2GRAY) if len(source_img.shape) == 3 else source_img
    h, w = fg_mask.shape[:2]
    
    y_idxs, x_idxs = np.where(fg_mask > 0)
    if len(y_idxs) < 100:
        return [{"part_index": 1, "mask": fg_mask.copy(), "is_exit": True}]
        
    min_y, max_y = y_idxs.min(), y_idxs.max()
    span_h = max_y - min_y
    
    if span_h < 40:
        return [{"part_index": 1, "mask": fg_mask.copy(), "is_exit": True}]
        
    # 1. Edge Gradient Dam
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = cv2.magnitude(grad_x, grad_y)
    grad_mag = cv2.normalize(grad_mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    # 2. Distance Transform
    dist = cv2.distanceTransform(fg_mask, cv2.DIST_L2, 5)
    
    # 3. Dynamic 1D Width Profile & Curvature (Anatomical Pinch Points)
    widths = []
    y_range = range(min_y, max_y + 1)
    for y in y_range:
        xs = x_idxs[y_idxs == y]
        widths.append(len(xs))
        
    widths = np.array(widths, dtype=np.float32)
    k_size = max(5, int(span_h * 0.04) | 1)
    kernel_1d = cv2.getGaussianKernel(k_size, k_size / 3.0)
    widths_smooth = cv2.filter2D(widths.reshape(-1, 1), -1, kernel_1d).flatten()
    
    minima_y = []
    window = max(4, int(span_h * 0.05))
    for i in range(window, len(widths_smooth) - window):
        sub = widths_smooth[i - window : i + window + 1]
        if widths_smooth[i] == sub.min() and widths_smooth[i] < np.percentile(widths_smooth, 75):
            minima_y.append(min_y + i)
            
    filtered_minima = []
    min_dist = max(20, int(span_h / float(max_parts + 1)))
    for my in minima_y:
        if not filtered_minima or (my - filtered_minima[-1] >= min_dist):
            filtered_minima.append(my)
            
    if len(filtered_minima) < min_parts - 1:
        num_divs = min_parts
        step = span_h / float(num_divs)
        filtered_minima = [int(min_y + (i + 1) * step) for i in range(num_divs - 1)]
        
    if len(filtered_minima) > max_parts - 1:
        filtered_minima = filtered_minima[:max_parts - 1]
        
    # 4. Dynamic Medial Centroid Seeds
    seed_points = []
    all_bounds = [min_y] + filtered_minima + [max_y]
    for i in range(len(all_bounds) - 1):
        mid_y = int((all_bounds[i] + all_bounds[i+1]) / 2.0)
        xs_at_y = x_idxs[y_idxs == mid_y]
        if len(xs_at_y) > 0:
            seed_x = int(np.median(xs_at_y))
            seed_points.append((seed_x, mid_y))
        else:
            sub_dist = dist[all_bounds[i]:all_bounds[i+1], :]
            if sub_dist.max() > 0:
                ly, lx = np.where(sub_dist == sub_dist.max())
                seed_points.append((int(lx[0]), int(all_bounds[i] + ly[0])))
                
    # 5. Marker-Controlled Watershed on Edge Gradient Dam
    markers = np.zeros((h, w), dtype=np.int32)
    for idx, (sx, sy) in enumerate(seed_points):
        cv2.circle(markers, (sx, sy), 4, idx + 1, -1)
        
    cost_map = (grad_mag * 0.75 + (255 - cv2.normalize(dist, None, 0, 255, cv2.NORM_MINMAX)) * 0.25).astype(np.uint8)
    cost_bgr = cv2.cvtColor(cost_map, cv2.COLOR_GRAY2BGR)
    cv2.watershed(cost_bgr, markers)
    
    parts = []
    num_seeds = len(seed_points)
    for idx in range(num_seeds):
        m = ((markers == idx + 1) & (fg_mask > 0)).astype(np.uint8) * 255
        if cv2.countNonZero(m) > 20:
            parts.append({
                "part_index": idx + 1,
                "mask": m,
                "is_exit": (idx == num_seeds - 1)
            })
            
    return parts

def build_orbital_waypoints(mask: np.ndarray, brush_radius: int = 7, step_stride: int = 3) -> List[Tuple[int, int]]:
    remaining = mask.copy()
    pts = []
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (brush_radius, brush_radius))
    
    while cv2.countNonZero(remaining) > 8:
        cnts, _ = cv2.findContours(remaining, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not cnts:
            break
        cnts = sorted(cnts, key=lambda c: cv2.arcLength(c, True), reverse=True)
        for c in cnts:
            if len(c) < 3:
                continue
            sampled = c[::step_stride]
            for pt in sampled:
                pts.append((int(pt[0][0]), int(pt[0][1])))
        remaining = cv2.erode(remaining, kernel)
        
    if not pts:
        ys, xs = np.where(mask > 0)
        if len(xs) > 0:
            pts = [(int(xs.mean()), int(ys.mean()))]
    return pts

def generate_smooth_bezier(p_start: Tuple[int, int], p_end: Tuple[int, int], num_points: int = 8) -> List[Tuple[int, int]]:
    p0 = np.array(p_start, dtype=np.float32)
    p3 = np.array(p_end, dtype=np.float32)
    dist = np.linalg.norm(p3 - p0)
    normal = np.array([-(p3[1] - p0[1]), (p3[0] - p0[0])])
    if np.linalg.norm(normal) > 1e-5:
        normal = normal / np.linalg.norm(normal)
    else:
        normal = np.array([0, -1])
        
    arc_height = min(20.0, dist * 0.20)
    p1 = p0 + (p3 - p0) * 0.33 + normal * arc_height
    p2 = p0 + (p3 - p0) * 0.66 + normal * arc_height
    
    pts = []
    for t in np.linspace(0, 1, num_points):
        pt = (1-t)**3 * p0 + 3*(1-t)**2 * t * p1 + 3*(1-t) * t**2 * p2 + t**3 * p3
        pts.append((int(pt[0]), int(pt[1])))
    return pts
