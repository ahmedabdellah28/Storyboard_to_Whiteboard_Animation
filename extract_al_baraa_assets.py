#!/usr/bin/env python3
"""
Al-Bara ibn Malik Storyboard Asset Extraction
Extracts all elements (4 rows: 5+5+5+4 = 19 elements) with semantic naming.
"""
import os
import sys
import json
import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

SECTION_DIR = "sections/fiercest_warriors_documentary/09_al_baraa_ibn_malik"
STORYBOARD = os.path.join(SECTION_DIR, "storyboard.png")
ASSETS_DIR = os.path.join(SECTION_DIR, "assets")

# Semantic descriptions - update based on actual storyboard analysis
# Row 1: 5 elements (intro, battle, leadership, etc.)
# Row 2: 5 elements (campaigns, achievements, etc.)  
# Row 3: 5 elements (death, legacy, etc.)
# Row 4: 4 elements (memorials, symbols, etc.)
ELEMENT_DESCRIPTIONS = {
    # Row 1 (5 elements)
    "r1_01_al_baraa_portrait": "البراء بن مالك --portrait",
    "r1_02_battle_scene": "مشهد معركة",
    "r1_03_camel_charge": "شرفة الجاموس/ال违法行为",
    "r1_04_leadership": "ق护*#فاع",
    "r1_05_flag_standard": "رايات/أعلام",
    
    # Row 2 (5 elements) - these were merged in extraction
    "r2_01_campaign_map": "خريطة حملة",
    "r2_02_army_march": "جيش ي marche",
    "r2_03_shield_wall": "جدار الدرع",
    "r2_04_arrow_shower": "مطر الرؤوس/سهام",
    "r2_05_victory": "النصر/الفوز",
    
    # Row 3 (5 elements)
    "r3_01_wounded_soldier": "مجريح",
    "r3_02_medical_tent": "خيمة طبية",
    "r3_03_eulogy": "خطابة/وداع",
    "r3_04_grave_marker": " شاهد قبر",
    "r3_05_legacy_symbol": "رمز الإرث",
    
    # Row 4 (4 elements - actual count)
    "r4_01_memorial_statue": "تمثال تذكاري",
    "r4_02_historical_book": "كتاب تاريخي",
    "r4_03_arabesque_design": "تصميم زخرفي",
    "r4_04_final_legacy": "الإرث النهائي",
}

# Map (row, col) -> element_id based on description order
ROW_COL_TO_ID = {}
idx = 0
for row in range(1, 5):
    num_cols = 5 if row < 4 else 4
    for col in range(1, num_cols + 1):
        keys = list(ELEMENT_DESCRIPTIONS.keys())
        key = keys[idx]
        ROW_COL_TO_ID[(row, col)] = key
        idx += 1

def detect_columns_robust(row_crop, target_cols=5):
    """Detect columns with fallback to fixed grid."""
    rh, rw = row_crop.shape[:2]
    gray = cv2.cvtColor(row_crop, cv2.COLOR_BGR2GRAY)
    drawing_mask = (gray < 235).astype(np.uint8)
    col_density = np.sum(drawing_mask, axis=0) / float(rh)
    
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
    
    print(f"    ⚠️  Using fixed {target_cols}-column grid fallback")
    step = rw / target_cols
    return [(int(i * step), int((i + 1) * step)) for i in range(target_cols)]

def extract_assets():
    if not os.path.exists(STORYBOARD):
        print(f"❌ Storyboard not found at: {STORYBOARD}")
        return
    
    img = cv2.imread(STORYBOARD)
    h, w = img.shape[:2]
    print(f"📸 Storyboard: {w}x{h} pixels")
    
    # Row detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    drawing_mask = (gray < 240).astype(np.uint8)
    row_density = np.sum(drawing_mask, axis=1) / float(w)
    
    is_valley = row_density < 0.02
    valleys = []
    for y in range(1, h-1):
        if is_valley[y] and not is_valley[y-1]:
            end = y
            while end < h and is_valley[end]:
                end += 1
            mid = (y + end) // 2
            if end - y > 5:
                valleys.append(mid)
    
    print(f"🔍 Detected {len(valleys)} horizontal valleys")
    
    if len(valleys) >= 3:
        valleys_sorted = sorted(valleys)
        row_boundaries = [v for v in valleys_sorted if 50 < v < h - 50][:3]
        
        if len(row_boundaries) >= 3:
            rows = [
                (10, row_boundaries[0]),
                (row_boundaries[0], row_boundaries[1]),
                (row_boundaries[1], row_boundaries[2]),
                (row_boundaries[2], h - 10)
            ]
            print(f"✅ Using detected row boundaries")
        else:
            step = h / 4.0
            rows = [(int(i * step), int((i + 1) * step)) for i in range(4)]
    else:
        step = h / 4.0
        rows = [(int(i * step), int((i + 1) * step)) for i in range(4)]
        print(f"⚠️ Using 4 equal rows")
    
    os.makedirs(ASSETS_DIR, exist_ok=True)
    
    # Clear old assets
    for f in os.listdir(ASSETS_DIR):
        if f.endswith('.png'):
            fp = os.path.join(ASSETS_DIR, f)
            if os.path.isfile(fp):
                os.remove(fp)
    
    metadata = {}
    
    for r_idx, (y1, y2) in enumerate(rows, 1):
        row_crop = img[y1:y2, 0:w]
        num_cols = 5 if r_idx < 4 else 4
        cols = detect_columns_robust(row_crop, target_cols=num_cols)
        print(f"  Row {r_idx} ({num_cols} cells): {len(cols)} detected")
        
        for c_idx, (x1, x2) in enumerate(cols, 1):
            if c_idx > num_cols:
                break
                
            asset_id = ROW_COL_TO_ID.get((r_idx, c_idx), f"r{r_idx}_{c_idx:02d}_unknown")
            desc = ELEMENT_DESCRIPTIONS.get(asset_id, f"Row {r_idx} Element {c_idx}")
            
            pad = 6
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
                print(f"    ⚠️  {asset_id}: No foreground, skipping")
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
            print(f"    ✅ {asset_id}: {actual_w}x{actual_h}px, area={area}")
    
    # Save metadata
    meta_path = os.path.join(ASSETS_DIR, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Extracted {len(metadata)} assets")
    print("\n📋 Asset Summary:")
    for aid, info in sorted(metadata.items()):
        print(f"  {aid}: row={info['row']}, col={info['col']}, {info['orig_size'][0]}x{info['orig_size'][1]}px")

if __name__ == "__main__":
    extract_assets()
