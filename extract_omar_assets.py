#!/usr/bin/env python3
"""
Omar al-Mukhtar Storyboard Asset Extraction
Extracts 20 visual elements (4 rows × 5 columns) from the storyboard
with semantic naming and metadata.
"""
import os
import sys
import json
import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

SECTION_DIR = "sections/fiercest_warriors_documentary/06_omar_al_mukhtar"
STORYBOARD = os.path.join(SECTION_DIR, "storyboard.png")
ASSETS_DIR = os.path.join(SECTION_DIR, "assets")

# Semantic descriptions for all 20 elements (4 rows × 5 columns)
# Based on visual analysis of عمر المختار storyboard
ELEMENT_DESCRIPTIONS = {
    # Row 1: Early life and resistance beginnings
    "r1_01_omar_portrait": "رأس عمر المختار المقاوم الليبي",
    "r1_02_omar_with_rifle": "عمر المختار بق銃ه في الصحراء",
    "r1_03_group_fighters": "مجموعة مقاومين ليبيا مع عمر",
    "r1_04_italian_tank_planes": "الجيش الإيطالي بدبابات وطائرات",
    "r1_05_mounted_resistance": "عمر على حصان يقود المقاومة",
    
    # Row 2: Guerrilla warfare
    "r2_01_ambush_rock": "كمانة وراء صخرة مع مقاومين",
    "r2_02_campfire_night": "ليل حول الشعلة مع المقاومين",
    "r2_03_desert_travel": "عمر في الصحراء على خيل",
    "r2_04_battle_fallen_horse": "حصان أسقط في المعركة، جنود بالزحف",
    "r2_05_capture_prison": "عمر الأسر بين الجيش الإيطالي",
    
    # Row 3: Capture and trial
    "r3_01_trial_interrogation": "المحاكمة مع الجنرال الإيطالي",
    "r3_02_finger_defiance": "عمر يرفع اصبعه بتحدي في المحاكمة",
    "r3_03_prison_cell": "عمر في السجن بين الحراس",
    "r3_04_git_ahead_execution": "منصة الإعدام مع الحبل",
    "r3_05_profile_resolute": "بروفايل عمر قبل الإعدام ثابت",
    
    # Row 4: Execution and legacy
    "r4_01_execution_platform": "عمر على منصة الإعدام مع الجماهير",
    "r4_02_execution_closeup": "لقطة مقربة للإعدام - العمر على الحبل",
    "r4_03_execution_italian_flag": "إعدام علني مع العلم الإيطالي",
    "r4_04_officer_observing": "ضابط إيطالي يشاهد الإعدام",
    "r4_05_legacy_silhouette": "عمر يسير وحيد في الصحراء عند الغسق",
}

# Mapping: (row, col) -> semantic ID
# 4 rows × 5 columns = 20 elements
ROW_COL_TO_ID = {}
idx = 0
for row in range(1, 5):
    for col in range(1, 6):
        # Generate key in order: r1_01, r1_02, ..., r1_05, r2_01, ...
        keys = list(ELEMENT_DESCRIPTIONS.keys())
        key = keys[idx]
        ROW_COL_TO_ID[(row, col)] = key
        idx += 1

def detect_columns_robust(row_crop, target_cols=5):
    """
    Detect columns in a row crop. If automatic detection fails to find
    target_cols, falls back to fixed grid partitioning.
    """
    rh, rw = row_crop.shape[:2]
    gray = cv2.cvtColor(row_crop, cv2.COLOR_BGR2GRAY)
    drawing_mask = (gray < 235).astype(np.uint8)
    col_density = np.sum(drawing_mask, axis=0) / float(rh)
    
    # Try multiple thresholds to find exact column count
    for threshold in [0.015, 0.012, 0.01, 0.008, 0.006, 0.004]:
        is_valley = col_density < threshold
        intervals = []
        in_content = False
        start_x = 0
        
        for x in range(rw):
            if not is_valley[x] and not in_content:
                in_content = True
                start_x = x
            elif is_valley[x] and in_content:
                in_content = False
                if x - start_x > 15:
                    intervals.append((start_x, x))
        
        if in_content and rw - start_x > 15:
            intervals.append((start_x, rw))
        
        # Merge only very close intervals (gap < 8px)
        merged = []
        for iv in intervals:
            if not merged:
                merged.append(iv)
            else:
                prev_st, prev_en = merged[-1]
                gap = iv[0] - prev_en
                if gap < 8:
                    merged[-1] = (prev_st, iv[1])
                else:
                    merged.append(iv)
        
        if len(merged) == target_cols:
            return merged
    
    # Fallback: fixed grid
    print(f"    ⚠️  Automatic detection failed, using fixed {target_cols}-column grid")
    step = rw / target_cols
    fixed_cols = [(int(i * step), int((i + 1) * step)) for i in range(target_cols)]
    return fixed_cols

def extract_assets():
    if not os.path.exists(STORYBOARD):
        print(f"❌ Storyboard not found at: {STORYBOARD}")
        return
    
    img = cv2.imread(STORYBOARD)
    h, w = img.shape[:2]
    print(f"📸 Storyboard: {w}x{h} pixels")
    
    # Manual row detection: 4 rows evenly distributed
    # But first try to detect actual row boundaries
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    drawing_mask = (gray < 240).astype(np.uint8)
    row_density = np.sum(drawing_mask, axis=1) / float(w)
    
    # Find valleys (horizontal gaps between rows)
    is_valley = row_density < 0.02
    valleys = []
    for y in range(1, h-1):
        if is_valley[y] and not is_valley[y-1]:
            # Find end of valley
            end = y
            while end < h and is_valley[end]:
                end += 1
            mid = (y + end) // 2
            if end - y > 5:  # minimum valley width
                valleys.append(mid)
    
    print(f"🔍 Detected {len(valleys)} horizontal valleys")
    
    # If we found valleys, use them. Otherwise use 4 equal bands.
    if len(valleys) >= 3:
        # Sort valleys and use middle 3 to create 4 rows
        valleys_sorted = sorted(valleys)
        # Take the 3 most prominent valleys (middle ones)
        row_boundaries = []
        for v in valleys_sorted:
            if 50 < v < h - 50:
                row_boundaries.append(v)
        row_boundaries = sorted(row_boundaries)[:3]  # Take up to 3 boundaries
        
        if len(row_boundaries) >= 3:
            rows = [
                (10, row_boundaries[0]),
                (row_boundaries[0], row_boundaries[1]),
                (row_boundaries[1], row_boundaries[2]),
                (row_boundaries[2], h - 10)
            ]
            print(f"✅ Using detected row boundaries: {[f'{y1}-{y2}' for y1,y2 in rows]}")
        else:
            # Fallback
            step = h / 4.0
            rows = [(int(i * step), int((i + 1) * step)) for i in range(4)]
            print(f"⚠️ Falling back to 4 equal rows")
    else:
        step = h / 4.0
        rows = [(int(i * step), int((i + 1) * step)) for i in range(4)]
        print(f"⚠️ Using 4 equal rows (no clear valleys)")
    
    os.makedirs(ASSETS_DIR, exist_ok=True)
    
    # Clear old assets
    for f in os.listdir(ASSETS_DIR):
        if f.endswith('.png') and f != 'metadata.json':
            os.remove(os.path.join(ASSETS_DIR, f))
    
    metadata = {}
    asset_counter = 0
    
    for r_idx, (y1, y2) in enumerate(rows, 1):
        row_crop = img[y1:y2, 0:w]
        
        cols = detect_columns_robust(row_crop, target_cols=5)
        print(f"  Row {r_idx}: {len(cols)} cells detected")
        
        for c_idx, (x1, x2) in enumerate(cols, 1):
            if c_idx > 5:
                break
                
            asset_id = ROW_COL_TO_ID.get((r_idx, c_idx), f"r{r_idx}_{c_idx:02d}_unknown")
            desc = ELEMENT_DESCRIPTIONS.get(asset_id, f"Row {r_idx} Element {c_idx}")
            
            pad = 4
            px1 = max(0, x1 - pad)
            py1 = max(0, y1 - pad)
            px2 = min(w, x2 + pad)
            py2 = min(h, y2 + pad)
            
            crop = img[py1:py2, px1:px2]
            gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            is_fg = gray_crop < 240
            
            mask = is_fg.astype(np.uint8) * 255
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
            
            ys, xs = np.where(mask > 0)
            if len(xs) == 0 or len(ys) == 0:
                print(f"    ⚠️  {asset_id}: No foreground pixels found, skipping")
                continue
            
            tx1, tx2 = np.min(xs), np.max(xs)
            ty1, ty2 = np.min(ys), np.max(ys)
            
            tight_crop = crop[ty1:ty2+1, tx1:tx2+1]
            tight_mask = mask[ty1:ty2+1, tx1:tx2+1]
            
            bgra = np.dstack([tight_crop, tight_mask])
            out_name = f"{asset_id}.png"
            cv2.imwrite(os.path.join(ASSETS_DIR, out_name), bgra)
            
            actual_w = tx2 - tx1 + 1
            actual_h = ty2 - ty1 + 1
            area = int(np.count_nonzero(tight_mask))
            
            metadata[asset_id] = {
                "file": out_name,
                "row": r_idx,
                "col": c_idx,
                "desc": desc,
                "orig_box": [int(px1 + tx1), int(py1 + ty1), int(actual_w), int(actual_h)],
                "orig_size": [int(actual_w), int(actual_h)],
                "area": area
            }
            asset_counter += 1
            print(f"    ✅ {asset_id}: {actual_w}x{actual_h}px, area={area}")
    
    # Save metadata
    meta_path = os.path.join(ASSETS_DIR, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Extracted {len(metadata)} assets to: {ASSETS_DIR}")
    print(f"📄 Metadata saved to: {meta_path}")
    
    # Print summary
    print("\n📋 Asset Summary:")
    for aid, info in sorted(metadata.items()):
        print(f"  {aid}: row={info['row']}, col={info['col']}, {info['orig_size'][0]}x{info['orig_size'][1]}px")

if __name__ == "__main__":
    extract_assets()
