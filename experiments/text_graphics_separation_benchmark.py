"""
EXPERIMENTAL COMPUTER VISION AUDIT — PHASE 3-7
File: experiments/text_graphics_separation_benchmark.py

GOAL: Head-to-head benchmark of 6 different methods for separating TEXT from GRAPHICS
across all 12 panels at 4 resolutions, with full metric tracking and failure analysis.

METHODS TESTED:
  A: Classical Adaptive Threshold + Connected Components (Area/Aspect/StrokeWidth)
  B: Contour Topology + Circularity + Solid Fill Ratio
  C: Multi-Channel Color Seed Subtraction (Color-First Character Isolation)
  D: Erosion-Based Stroke Width Transform (SWT-Lite)
  E: Distance Transform + Skeleton Medial Axis
  F: Hybrid Pipeline (Best of A+B+D combined)

READ-ONLY: Zero modifications to project source code.
All outputs go to: experiments/results/
"""
import os
import sys
import time
import json
import cv2
import numpy as np

# ======================== CONFIGURATION ========================
IMG_PATH = r"C:\Users\loper\.gemini\antigravity-ide\brain\6c66c18f-8997-4b3a-89b1-ec5216983d7f\.user_uploaded\media_1788292396282.png"
RESULTS_DIR = r"E:\image_to_animate\experiments\results"
DATASET_DIR = r"E:\image_to_animate\experiments\dataset"
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(DATASET_DIR, exist_ok=True)

img_master = cv2.imread(IMG_PATH)
if img_master is None:
    raise FileNotFoundError(f"Cannot load: {IMG_PATH}")
MH, MW = img_master.shape[:2]
print(f"[AUDIT] Master image loaded: {MW}x{MH}")

# ======================== PHASE 2: PANEL EXTRACTION ========================
# Dynamic border-based panel discovery (READ-ONLY re-implementation for isolation)
def discover_panels(img):
    ih, iw = img.shape[:2]
    color_diff = 255.0 - img.astype(np.float32)
    dist_from_white = np.max(color_diff, axis=2)
    ink_bin = (dist_from_white > 26.0).astype(np.uint8) * 255
    
    num_cc, cc_labels, cc_stats, _ = cv2.connectedComponentsWithStats(ink_bin)
    
    borders = []
    for i in range(1, num_cc):
        cw = cc_stats[i, cv2.CC_STAT_WIDTH]
        ch = cc_stats[i, cv2.CC_STAT_HEIGHT]
        cx = cc_stats[i, cv2.CC_STAT_LEFT]
        cy = cc_stats[i, cv2.CC_STAT_TOP]
        carea = cc_stats[i, cv2.CC_STAT_AREA]
        
        if (iw * 0.15 <= cw <= iw * 0.35) and (ih * 0.20 <= ch <= ih * 0.40):
            density = carea / float(cw * ch + 1e-5)
            if density < 0.15:
                borders.append({"comp_id": i, "bbox": (cx, cy, cw, ch),
                                "cx": cx + cw/2.0, "cy": cy + ch/2.0})
    
    borders.sort(key=lambda b: (int(b["cy"] / (ih / 3.0)), b["cx"]))
    
    panels = []
    for idx, b in enumerate(borders):
        bx, by, bw, bh = b["bbox"]
        inset = 4
        ix, iy = bx + inset, by + inset
        iw_p, ih_p = max(10, bw - 2*inset), max(10, bh - 2*inset)
        interior = img[iy:iy+ih_p, ix:ix+iw_p].copy()
        panels.append({"id": idx+1, "bbox": (bx, by, bw, bh),
                        "interior_bbox": (ix, iy, iw_p, ih_p), "crop": interior})
    return panels

panels = discover_panels(img_master)
print(f"[AUDIT] Discovered {len(panels)} panels.")

# Save individual panel crops to dataset/
for p in panels:
    cv2.imwrite(os.path.join(DATASET_DIR, f"panel_{p['id']:02d}_original.png"), p["crop"])

# ======================== METHOD IMPLEMENTATIONS ========================

def method_A_classical_threshold(panel_crop):
    """Classical Adaptive Threshold + Connected Components with Area/Aspect/Height filter."""
    t0 = time.time()
    ph, pw = panel_crop.shape[:2]
    
    diff = 255.0 - panel_crop.astype(np.float32)
    dist = np.max(diff, axis=2)
    ink = (dist > 26.0).astype(np.uint8) * 255
    
    num_cc, labels, stats, _ = cv2.connectedComponentsWithStats(ink)
    
    text_mask = np.zeros((ph, pw), dtype=np.uint8)
    graphics_mask = np.zeros((ph, pw), dtype=np.uint8)
    
    for i in range(1, num_cc):
        cw = stats[i, cv2.CC_STAT_WIDTH]
        ch = stats[i, cv2.CC_STAT_HEIGHT]
        carea = stats[i, cv2.CC_STAT_AREA]
        aspect = cw / float(ch + 1e-5)
        
        # Text: small height, moderate width, small area, or dots
        if (ch <= 28 and cw <= 85 and carea < 260) or carea <= 20 or (aspect > 4.5 and ch <= 7):
            text_mask[labels == i] = 255
        else:
            graphics_mask[labels == i] = 255
    
    elapsed = time.time() - t0
    return text_mask, graphics_mask, elapsed

def method_B_contour_topology(panel_crop):
    """Contour Topology + Circularity + Solid Fill Ratio."""
    t0 = time.time()
    ph, pw = panel_crop.shape[:2]
    
    diff = 255.0 - panel_crop.astype(np.float32)
    dist = np.max(diff, axis=2)
    ink = (dist > 26.0).astype(np.uint8) * 255
    
    hsv = cv2.cvtColor(panel_crop, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    color_mask = (sat > 25).astype(np.uint8) * 255
    
    num_cc, labels, stats, _ = cv2.connectedComponentsWithStats(ink)
    kernel_erode = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    
    text_mask = np.zeros((ph, pw), dtype=np.uint8)
    graphics_mask = np.zeros((ph, pw), dtype=np.uint8)
    
    for i in range(1, num_cc):
        cx = stats[i, cv2.CC_STAT_LEFT]
        cy = stats[i, cv2.CC_STAT_TOP]
        cw = stats[i, cv2.CC_STAT_WIDTH]
        ch = stats[i, cv2.CC_STAT_HEIGHT]
        carea = stats[i, cv2.CC_STAT_AREA]
        
        comp = (labels[cy:cy+ch, cx:cx+cw] == i).astype(np.uint8) * 255
        
        # Solid fill ratio (erosion survival)
        eroded = cv2.erode(comp, kernel_erode)
        solid_ratio = np.sum(eroded > 0) / float(carea + 1e-5)
        
        # Color ratio
        sub_col = color_mask[cy:cy+ch, cx:cx+cw][comp > 0]
        col_ratio = np.sum(sub_col > 0) / float(carea + 1e-5)
        
        # Circularity
        cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        circ = 0.0
        if cnts:
            perim = cv2.arcLength(cnts[0], True)
            circ = (4.0 * np.pi * carea) / float(perim**2 + 1e-5)
        
        # Decision: Text has thin strokes (solid_ratio < 0.20, low color)
        # Graphics have dense bodies (solid_ratio > 0.22 or high color)
        is_graphics = (solid_ratio >= 0.22 and col_ratio > 0.35) or \
                      (carea > 300) or \
                      (14 <= cw <= 38 and 14 <= ch <= 38 and circ >= 0.55 and col_ratio > 0.30)
        
        if is_graphics:
            graphics_mask[labels == i] = 255
        else:
            text_mask[labels == i] = 255
    
    elapsed = time.time() - t0
    return text_mask, graphics_mask, elapsed

def method_C_color_seed_subtraction(panel_crop):
    """Multi-Channel Color Seed Subtraction (Character body isolation first)."""
    t0 = time.time()
    ph, pw = panel_crop.shape[:2]
    
    diff = 255.0 - panel_crop.astype(np.float32)
    dist = np.max(diff, axis=2)
    ink = (dist > 26.0).astype(np.uint8) * 255
    
    hsv = cv2.cvtColor(panel_crop, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    color_seed = ((sat > 25) & (val > 35) & (val < 250)).astype(np.uint8) * 255
    
    # Close color seeds to merge body parts
    fuse_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    closed = cv2.morphologyEx(color_seed, cv2.MORPH_CLOSE, fuse_kernel)
    
    # Annex touching linework
    dilated = cv2.dilate(closed, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    graphics_mask = ((dilated > 0) & (ink > 0)).astype(np.uint8) * 255
    graphics_mask = graphics_mask | closed
    
    # Everything else in ink is text
    text_mask = ink.copy()
    text_mask[graphics_mask > 0] = 0
    
    elapsed = time.time() - t0
    return text_mask, graphics_mask, elapsed

def method_D_stroke_width_transform(panel_crop):
    """Erosion-Based Stroke Width Transform (SWT-Lite)."""
    t0 = time.time()
    ph, pw = panel_crop.shape[:2]
    
    diff = 255.0 - panel_crop.astype(np.float32)
    dist = np.max(diff, axis=2)
    ink = (dist > 26.0).astype(np.uint8) * 255
    
    # Distance transform on ink
    dt = cv2.distanceTransform(ink, cv2.DIST_L2, 5)
    
    num_cc, labels, stats, _ = cv2.connectedComponentsWithStats(ink)
    
    text_mask = np.zeros((ph, pw), dtype=np.uint8)
    graphics_mask = np.zeros((ph, pw), dtype=np.uint8)
    
    for i in range(1, num_cc):
        cx = stats[i, cv2.CC_STAT_LEFT]
        cy = stats[i, cv2.CC_STAT_TOP]
        cw = stats[i, cv2.CC_STAT_WIDTH]
        ch = stats[i, cv2.CC_STAT_HEIGHT]
        carea = stats[i, cv2.CC_STAT_AREA]
        
        comp_pixels = (labels == i)
        
        # Mean stroke width from distance transform
        mean_sw = np.mean(dt[comp_pixels]) if carea > 0 else 0.0
        max_sw = np.max(dt[comp_pixels]) if carea > 0 else 0.0
        
        # Text has uniform thin strokes: mean_sw <= 1.8, max_sw <= 3.5
        # Graphics have wider/variable strokes or solid fills: mean_sw > 2.0 or max_sw > 4.0
        is_text = (mean_sw <= 1.8 and max_sw <= 3.5 and ch <= 30 and cw <= 90) or carea <= 20
        
        if is_text:
            text_mask[comp_pixels] = 255
        else:
            graphics_mask[comp_pixels] = 255
    
    elapsed = time.time() - t0
    return text_mask, graphics_mask, elapsed

def method_E_skeleton_medial_axis(panel_crop):
    """Distance Transform + Skeleton Medial Axis classification."""
    t0 = time.time()
    ph, pw = panel_crop.shape[:2]
    
    diff = 255.0 - panel_crop.astype(np.float32)
    dist = np.max(diff, axis=2)
    ink = (dist > 26.0).astype(np.uint8) * 255
    
    # Morphological skeleton
    skel = np.zeros_like(ink)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    temp = ink.copy()
    while True:
        eroded = cv2.erode(temp, element)
        opened = cv2.dilate(eroded, element)
        diff_img = cv2.subtract(temp, opened)
        skel = cv2.bitwise_or(skel, diff_img)
        temp = eroded.copy()
        if cv2.countNonZero(temp) == 0:
            break
    
    num_cc, labels, stats, _ = cv2.connectedComponentsWithStats(ink)
    
    text_mask = np.zeros((ph, pw), dtype=np.uint8)
    graphics_mask = np.zeros((ph, pw), dtype=np.uint8)
    
    for i in range(1, num_cc):
        cx = stats[i, cv2.CC_STAT_LEFT]
        cy = stats[i, cv2.CC_STAT_TOP]
        cw = stats[i, cv2.CC_STAT_WIDTH]
        ch = stats[i, cv2.CC_STAT_HEIGHT]
        carea = stats[i, cv2.CC_STAT_AREA]
        
        comp_pixels = (labels == i)
        skel_area = np.sum(skel[comp_pixels] > 0)
        
        # Skeleton ratio: text strokes are mostly skeleton (ratio > 0.35)
        # Solid graphics have low skeleton ratio (ratio < 0.20)
        skel_ratio = skel_area / float(carea + 1e-5)
        
        is_text = (skel_ratio > 0.30 and ch <= 30 and cw <= 90) or carea <= 20
        
        if is_text:
            text_mask[comp_pixels] = 255
        else:
            graphics_mask[comp_pixels] = 255
    
    elapsed = time.time() - t0
    return text_mask, graphics_mask, elapsed

def method_F_hybrid(panel_crop):
    """Hybrid: Color seed for characters + SWT for text vs remaining ink."""
    t0 = time.time()
    ph, pw = panel_crop.shape[:2]
    
    diff = 255.0 - panel_crop.astype(np.float32)
    dist = np.max(diff, axis=2)
    ink = (dist > 26.0).astype(np.uint8) * 255
    
    hsv = cv2.cvtColor(panel_crop, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    color_seed = ((sat > 25) & (val > 35) & (val < 250)).astype(np.uint8) * 255
    
    # Step 1: Isolate colored character bodies (color seed + touching linework)
    fuse_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    closed = cv2.morphologyEx(color_seed, cv2.MORPH_CLOSE, fuse_kernel)
    dilated = cv2.dilate(closed, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    char_body = ((dilated > 0) & (ink > 0)).astype(np.uint8) * 255
    char_body = char_body | closed
    
    # Step 2: Remaining ink (not character body) → classify with SWT
    remaining_ink = ink.copy()
    remaining_ink[char_body > 0] = 0
    
    dt = cv2.distanceTransform(remaining_ink, cv2.DIST_L2, 5)
    num_cc, labels, stats, _ = cv2.connectedComponentsWithStats(remaining_ink)
    
    text_mask = np.zeros((ph, pw), dtype=np.uint8)
    graphics_mask = char_body.copy()  # Characters are already graphics
    
    kernel_erode = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    
    for i in range(1, num_cc):
        cx = stats[i, cv2.CC_STAT_LEFT]
        cy = stats[i, cv2.CC_STAT_TOP]
        cw = stats[i, cv2.CC_STAT_WIDTH]
        ch = stats[i, cv2.CC_STAT_HEIGHT]
        carea = stats[i, cv2.CC_STAT_AREA]
        
        comp_pixels = (labels == i)
        mean_sw = np.mean(dt[comp_pixels]) if carea > 0 else 0.0
        
        comp_mask_local = (labels[cy:cy+ch, cx:cx+cw] == i).astype(np.uint8) * 255
        eroded = cv2.erode(comp_mask_local, kernel_erode)
        solid_ratio = np.sum(eroded > 0) / float(carea + 1e-5)
        
        # Text: thin strokes, small glyph height, low solid ratio
        is_text = (mean_sw <= 1.8 and ch <= 30 and cw <= 90 and solid_ratio < 0.25) or carea <= 20
        
        if is_text:
            text_mask[comp_pixels] = 255
        else:
            graphics_mask[comp_pixels] = 255
    
    elapsed = time.time() - t0
    return text_mask, graphics_mask, elapsed

# ======================== METRIC CALCULATION ========================
def calc_metrics(text_mask, graphics_mask, ink_mask, panel_crop):
    """Calculate separation quality metrics."""
    total_ink = np.sum(ink_mask > 0)
    text_px = np.sum(text_mask > 0)
    gfx_px = np.sum(graphics_mask > 0)
    
    # Coverage: how much of ink is accounted for
    accounted = np.sum((text_mask > 0) | (graphics_mask > 0))
    coverage = accounted / float(total_ink + 1e-5)
    
    # Overlap: pixels classified as both
    overlap = np.sum((text_mask > 0) & (graphics_mask > 0))
    overlap_ratio = overlap / float(total_ink + 1e-5)
    
    # Color contamination in text layer (colored pixels wrongly in text)
    hsv = cv2.cvtColor(panel_crop, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    colored_in_text = np.sum((text_mask > 0) & (sat > 40))
    color_contam = colored_in_text / float(text_px + 1e-5)
    
    return {
        "total_ink_px": int(total_ink),
        "text_px": int(text_px),
        "graphics_px": int(gfx_px),
        "coverage": round(coverage, 4),
        "overlap_ratio": round(overlap_ratio, 4),
        "color_contamination_in_text": round(color_contam, 4),
        "text_ratio": round(text_px / float(total_ink + 1e-5), 4),
        "gfx_ratio": round(gfx_px / float(total_ink + 1e-5), 4)
    }

# ======================== RESOLUTION TESTING ========================
resolutions = {
    "original": 1.0,
    "1.5x": 1.5,
    "0.75x": 0.75,
    "0.50x": 0.50
}

methods = {
    "A_ClassicalThreshold": method_A_classical_threshold,
    "B_ContourTopology": method_B_contour_topology,
    "C_ColorSeedSubtract": method_C_color_seed_subtraction,
    "D_StrokeWidthTransform": method_D_stroke_width_transform,
    "E_SkeletonMedialAxis": method_E_skeleton_medial_axis,
    "F_Hybrid": method_F_hybrid
}

# ======================== RUN BENCHMARK ========================
all_results = {}

# Run at original resolution first (primary benchmark)
res_name = "original"
res_scale = 1.0
print(f"\n{'='*80}")
print(f"BENCHMARK AT RESOLUTION: {res_name} (scale={res_scale})")
print(f"{'='*80}")

for p in panels:
    pid = p["id"]
    crop = p["crop"]
    ph, pw = crop.shape[:2]
    
    # Ink mask for metrics
    diff = 255.0 - crop.astype(np.float32)
    dist = np.max(diff, axis=2)
    ink_mask = (dist > 26.0).astype(np.uint8) * 255
    
    panel_key = f"panel_{pid:02d}"
    all_results[panel_key] = {}
    
    for method_name, method_fn in methods.items():
        text_mask, gfx_mask, elapsed = method_fn(crop)
        metrics = calc_metrics(text_mask, gfx_mask, ink_mask, crop)
        metrics["time_ms"] = round(elapsed * 1000, 1)
        
        all_results[panel_key][method_name] = metrics
        
        # Save individual results
        method_dir = os.path.join(RESULTS_DIR, method_name)
        os.makedirs(method_dir, exist_ok=True)
        
        # Text layer on white
        text_vis = np.full((ph, pw, 3), 255, dtype=np.uint8)
        text_vis[text_mask > 0] = crop[text_mask > 0]
        cv2.imwrite(os.path.join(method_dir, f"panel_{pid:02d}_text.png"), text_vis)
        
        # Graphics layer on white
        gfx_vis = np.full((ph, pw, 3), 255, dtype=np.uint8)
        gfx_vis[gfx_mask > 0] = crop[gfx_mask > 0]
        cv2.imwrite(os.path.join(method_dir, f"panel_{pid:02d}_graphics.png"), gfx_vis)
        
        print(f"  Panel {pid:02d} | {method_name:25s} | Text: {metrics['text_px']:5d}px ({metrics['text_ratio']:.2%}) | Gfx: {metrics['graphics_px']:5d}px ({metrics['gfx_ratio']:.2%}) | ColorContam: {metrics['color_contamination_in_text']:.2%} | {metrics['time_ms']:.0f}ms")

# ======================== BUILD COMPARISON VISUALIZATIONS ========================
# Select 6 representative panels for visual comparison
vis_panels = [1, 2, 4, 8, 9, 12]

card_w, card_h = 200, 150
num_methods = len(methods)
comp_cols = num_methods + 1  # Original + each method
comp_rows = len(vis_panels)

comp_w = comp_cols * (card_w + 8) + 20
comp_h = comp_rows * (card_h + 8) + 65

# TEXT LAYER comparison
text_comp = np.full((comp_h, comp_w, 3), 240, dtype=np.uint8)
cv2.rectangle(text_comp, (0, 0), (comp_w, 50), (25, 25, 35), -1)
cv2.putText(text_comp, "TEXT LAYER COMPARISON: ORIGINAL | METHOD A | B | C | D | E | F (HYBRID)", (15, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 220, 255), 2, cv2.LINE_AA)

for row_idx, pid in enumerate(vis_panels):
    gy = 58 + row_idx * (card_h + 8)
    p_crop = panels[pid-1]["crop"]
    
    # Column 0: Original
    gx0 = 10
    cv2.rectangle(text_comp, (gx0, gy), (gx0+card_w, gy+card_h), (255,255,255), -1)
    cv2.rectangle(text_comp, (gx0, gy), (gx0+card_w, gy+card_h), (80,80,80), 1)
    cv2.rectangle(text_comp, (gx0, gy), (gx0+card_w, gy+18), (35,35,45), -1)
    cv2.putText(text_comp, f"P{pid:02d} ORIGINAL", (gx0+4, gy+13), cv2.FONT_HERSHEY_SIMPLEX, 0.30, (255,255,255), 1)
    sc = min((card_w-8)/float(p_crop.shape[1]), (card_h-25)/float(p_crop.shape[0]))
    res_orig = cv2.resize(p_crop, (int(p_crop.shape[1]*sc), int(p_crop.shape[0]*sc)))
    ox = gx0 + (card_w - res_orig.shape[1])//2
    oy = gy + 20 + (card_h-25 - res_orig.shape[0])//2
    text_comp[oy:oy+res_orig.shape[0], ox:ox+res_orig.shape[1]] = res_orig
    
    # Columns 1-6: Methods
    for col_idx, (m_name, _) in enumerate(methods.items()):
        gx = 10 + (col_idx + 1) * (card_w + 8)
        m_dir = os.path.join(RESULTS_DIR, m_name)
        text_img = cv2.imread(os.path.join(m_dir, f"panel_{pid:02d}_text.png"))
        if text_img is None:
            continue
        
        cv2.rectangle(text_comp, (gx, gy), (gx+card_w, gy+card_h), (255,255,255), -1)
        cv2.rectangle(text_comp, (gx, gy), (gx+card_w, gy+card_h), (0,200,0), 1)
        cv2.rectangle(text_comp, (gx, gy), (gx+card_w, gy+18), (35,35,45), -1)
        short_name = m_name.split("_")[0]
        cv2.putText(text_comp, f"P{pid:02d} {short_name}", (gx+4, gy+13), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0,220,255), 1)
        
        res_m = cv2.resize(text_img, (int(text_img.shape[1]*sc), int(text_img.shape[0]*sc)))
        mx = gx + (card_w - res_m.shape[1])//2
        my = gy + 20 + (card_h-25 - res_m.shape[0])//2
        text_comp[my:my+res_m.shape[0], mx:mx+res_m.shape[1]] = res_m

os.makedirs(os.path.join(RESULTS_DIR, "comparison"), exist_ok=True)
cv2.imwrite(os.path.join(RESULTS_DIR, "comparison", "text_layer_comparison_all_methods.png"), text_comp)

# GRAPHICS LAYER comparison
gfx_comp = np.full((comp_h, comp_w, 3), 240, dtype=np.uint8)
cv2.rectangle(gfx_comp, (0, 0), (comp_w, 50), (25, 25, 35), -1)
cv2.putText(gfx_comp, "GRAPHICS LAYER COMPARISON: ORIGINAL | METHOD A | B | C | D | E | F (HYBRID)", (15, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 200, 255), 2, cv2.LINE_AA)

for row_idx, pid in enumerate(vis_panels):
    gy = 58 + row_idx * (card_h + 8)
    p_crop = panels[pid-1]["crop"]
    
    # Column 0: Original
    gx0 = 10
    cv2.rectangle(gfx_comp, (gx0, gy), (gx0+card_w, gy+card_h), (255,255,255), -1)
    cv2.rectangle(gfx_comp, (gx0, gy), (gx0+card_w, gy+card_h), (80,80,80), 1)
    cv2.rectangle(gfx_comp, (gx0, gy), (gx0+card_w, gy+18), (35,35,45), -1)
    cv2.putText(gfx_comp, f"P{pid:02d} ORIGINAL", (gx0+4, gy+13), cv2.FONT_HERSHEY_SIMPLEX, 0.30, (255,255,255), 1)
    sc = min((card_w-8)/float(p_crop.shape[1]), (card_h-25)/float(p_crop.shape[0]))
    res_orig = cv2.resize(p_crop, (int(p_crop.shape[1]*sc), int(p_crop.shape[0]*sc)))
    ox = gx0 + (card_w - res_orig.shape[1])//2
    oy = gy + 20 + (card_h-25 - res_orig.shape[0])//2
    gfx_comp[oy:oy+res_orig.shape[0], ox:ox+res_orig.shape[1]] = res_orig
    
    for col_idx, (m_name, _) in enumerate(methods.items()):
        gx = 10 + (col_idx + 1) * (card_w + 8)
        m_dir = os.path.join(RESULTS_DIR, m_name)
        gfx_img = cv2.imread(os.path.join(m_dir, f"panel_{pid:02d}_graphics.png"))
        if gfx_img is None:
            continue
        
        cv2.rectangle(gfx_comp, (gx, gy), (gx+card_w, gy+card_h), (255,255,255), -1)
        cv2.rectangle(gfx_comp, (gx, gy), (gx+card_w, gy+card_h), (0,200,255), 1)
        cv2.rectangle(gfx_comp, (gx, gy), (gx+card_w, gy+18), (35,35,45), -1)
        short_name = m_name.split("_")[0]
        cv2.putText(gfx_comp, f"P{pid:02d} {short_name}", (gx+4, gy+13), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0,200,255), 1)
        
        res_m = cv2.resize(gfx_img, (int(gfx_img.shape[1]*sc), int(gfx_img.shape[0]*sc)))
        mx = gx + (card_w - res_m.shape[1])//2
        my = gy + 20 + (card_h-25 - res_m.shape[0])//2
        gfx_comp[my:my+res_m.shape[0], mx:mx+res_m.shape[1]] = res_m

cv2.imwrite(os.path.join(RESULTS_DIR, "comparison", "graphics_layer_comparison_all_methods.png"), gfx_comp)

# ======================== SAVE METRICS JSON ========================
metrics_path = os.path.join(RESULTS_DIR, "metrics", "benchmark_results.json")
os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
with open(metrics_path, "w", encoding="utf-8") as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)
print(f"\nSaved metrics to: {metrics_path}")

# ======================== RESOLUTION ROBUSTNESS TEST ========================
print(f"\n{'='*80}")
print("RESOLUTION ROBUSTNESS TEST")
print(f"{'='*80}")

res_results = {}
for res_name, scale in resolutions.items():
    if scale == 1.0:
        continue  # Already tested
    
    print(f"\n--- Resolution: {res_name} (scale={scale}) ---")
    res_results[res_name] = {}
    
    for p in panels[:4]:  # Test on first 4 panels for speed
        pid = p["id"]
        crop = p["crop"]
        
        # Resize
        new_w = max(32, int(crop.shape[1] * scale))
        new_h = max(32, int(crop.shape[0] * scale))
        resized_crop = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4 if scale > 1 else cv2.INTER_AREA)
        
        diff = 255.0 - resized_crop.astype(np.float32)
        dist = np.max(diff, axis=2)
        ink_mask = (dist > 26.0).astype(np.uint8) * 255
        
        for m_name, m_fn in [("A_ClassicalThreshold", method_A_classical_threshold), 
                              ("F_Hybrid", method_F_hybrid)]:
            text_mask, gfx_mask, elapsed = m_fn(resized_crop)
            metrics = calc_metrics(text_mask, gfx_mask, ink_mask, resized_crop)
            key = f"P{pid:02d}_{m_name}"
            res_results[res_name][key] = metrics
            print(f"  Panel {pid:02d} | {m_name:25s} | Text: {metrics['text_ratio']:.2%} | Gfx: {metrics['gfx_ratio']:.2%} | ColContam: {metrics['color_contamination_in_text']:.2%}")

res_metrics_path = os.path.join(RESULTS_DIR, "metrics", "resolution_robustness.json")
with open(res_metrics_path, "w", encoding="utf-8") as f:
    json.dump(res_results, f, indent=2, ensure_ascii=False)

print(f"\n{'='*80}")
print("EXPERIMENTAL BENCHMARK COMPLETE!")
print(f"Results saved to: {RESULTS_DIR}")
print(f"{'='*80}")
