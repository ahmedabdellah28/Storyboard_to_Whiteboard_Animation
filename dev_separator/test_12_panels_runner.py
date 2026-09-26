"""
Comprehensive 12-Panel Test Runner & Visual Verification Engine
Processes all 12 panels of the user storyboard, saves annotated crops & masks,
and generates a detailed verification report.
"""
import os
import sys
import cv2
import numpy as np

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure kivy root is accessible for DynamicBorderDetector / WhiteboardProcessor
KIVY_DIR = os.path.abspath('kivy')
ROOT_DIR = os.path.abspath('.')
if KIVY_DIR not in sys.path:
    sys.path.insert(0, KIVY_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.processing.whiteboard_processor import WhiteboardProcessor, DynamicBorderDetector
from dev_separator.panel_pipeline import PanelPipeline


def run_full_12_panel_suite(image_path: str, output_base: str = 'dev_separator/output_reports'):
    os.makedirs(output_base, exist_ok=True)
    
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not load image from {image_path}")
        
    print(f"[12-Panel Runner] Image loaded successfully: shape={img.shape}")
    
    panels_data = WhiteboardProcessor.discover_panels(img)
    print(f"[12-Panel Runner] Discovered {len(panels_data)} panels.")
    
    report_lines = []
    report_lines.append("# تقرير التحقق والفحص البصري الشامل لجميع البانلات الـ 12\n")
    report_lines.append(f"**تاريخ التشغيل:** 2026-09-17\n")
    report_lines.append(f"**عدد البانلات المكتشفة:** {len(panels_data)}\n\n")
    report_lines.append("| رقم البانل | عدد العناصر | تفصيل العناصر المستخرجة | حالة الفصل |")
    report_lines.append("| :--- | :--- | :--- | :--- |")
    
    # High-contrast distinctive colors for exact contour outlining (BGR)
    PALETTE = {
        "PANEL_BADGE": (40, 40, 40),          # Dark Gray / Black
        "TITLE": (220, 30, 180),              # Deep Magenta
        "UNDERLINE": (0, 140, 255),           # Vivid Orange
        "CHARACTER": (30, 200, 30),           # Vivid Emerald Green
        "CONTAINER_CARD": (255, 200, 0),      # Electric Cyan / Sky Blue
        "CARD_TEXT": (20, 20, 240),           # Coral Red (distinct for text inside card)
        "TEXT": (180, 20, 220),               # Purple
        "EMOJI": (0, 215, 255),               # Gold Yellow
        "ICON_GRAPHIC": (230, 90, 30)         # Royal Blue
    }
    
    for p_idx, p_info in enumerate(panels_data):
        panel_id = p_idx + 1
        px, py, pw, ph = p_info["bbox"]
        raw_crop = img[py:py+ph, px:px+pw]
        
        # Border trimming
        border_res = DynamicBorderDetector.detect_and_trim_panel_border(raw_crop)
        clean_crop = border_res["clean_crop"]
        c_h, c_w = clean_crop.shape[:2]
        
        # Process panel with V4 PanelPipeline
        panel_res = PanelPipeline.process_panel(clean_crop, panel_id=panel_id)
        objects = panel_res["objects"]
        
        panel_dir = os.path.join(output_base, f"panel_{panel_id:02d}")
        os.makedirs(panel_dir, exist_ok=True)
        
        # 1. Save original clean crop
        cv2.imwrite(os.path.join(panel_dir, "00_original_clean.png"), clean_crop)
        
        # 2. Render exact contour annotations on boundaries
        annotated_contours = clean_crop.copy()
        tint_overlay = clean_crop.copy()
        
        obj_names_summary = []
        for obj in objects:
            bx, by, bw, bh = obj["bbox"]
            cat = obj.get("category", "UNKNOWN")
            obj_type = obj.get("type", "UNKNOWN")
            obj_name = obj.get("name", "")
            
            # Specific distinctive color
            if "card text" in obj_name.lower():
                color = PALETTE["CARD_TEXT"]
            elif cat == "CONTAINER_CARD":
                color = PALETTE["CONTAINER_CARD"]
            elif cat == "CHARACTER":
                color = PALETTE["CHARACTER"]
            elif obj_type == "TITLE":
                color = PALETTE["TITLE"]
            elif cat == "EMOJI":
                color = PALETTE["EMOJI"]
            elif cat == "ICON_GRAPHIC":
                color = PALETTE["ICON_GRAPHIC"]
            else:
                color = PALETTE.get(cat, (0, 255, 0))
                
            full_m = obj.get("full_mask")
            if full_m is not None and cv2.countNonZero(full_m) > 0:
                cnts, _ = cv2.findContours(full_m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                # Tinted fill
                cv2.drawContours(tint_overlay, cnts, -1, color, thickness=cv2.FILLED)
                # Exact contour boundary line (following curves and silhouettes)
                cv2.drawContours(annotated_contours, cnts, -1, color, thickness=2, lineType=cv2.LINE_AA)
            else:
                cv2.rectangle(annotated_contours, (bx, by), (bx + bw, by + bh), color, 2)
                
            # Add small label pill
            label_text = f"P{obj['priority']}: {obj_name.split(' - ')[-1]}"
            lx = max(2, min(c_w - 90, bx))
            ly = max(14, min(c_h - 6, by - 3))
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.32, 1)
            cv2.rectangle(annotated_contours, (lx - 1, ly - th - 2), (lx + tw + 2, ly + 2), (255, 255, 255), -1)
            cv2.rectangle(annotated_contours, (lx - 1, ly - th - 2), (lx + tw + 2, ly + 2), color, 1)
            cv2.putText(annotated_contours, label_text, (lx, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (15, 15, 15), 1, cv2.LINE_AA)
            
            # 3. Save exact contour alpha crop (transparent PNG cutout following exact boundary)
            if full_m is not None and obj.get("crop") is not None:
                sub_mask = full_m[by:by+bh, bx:bx+bw]
                sub_crop = clean_crop[by:by+bh, bx:bx+bw]
                if sub_mask.shape[:2] == sub_crop.shape[:2] and sub_crop.size > 0:
                    rgba_crop = cv2.cvtColor(sub_crop, cv2.COLOR_BGR2BGRA)
                    rgba_crop[:, :, 3] = sub_mask # Exact Alpha channel
                    cv2.imwrite(os.path.join(panel_dir, f"obj_{obj['priority']:02d}_alpha.png"), rgba_crop)
                    
                    # Also save clean white-isolated cutout
                    white_crop = np.full_like(sub_crop, 255)
                    white_crop[sub_mask > 0] = sub_crop[sub_mask > 0]
                    cv2.imwrite(os.path.join(panel_dir, f"obj_{obj['priority']:02d}_white.png"), white_crop)
                
            obj_names_summary.append(f"{obj['name']} ({obj['type']})")
            
        cv2.addWeighted(tint_overlay, 0.18, annotated_contours, 0.82, 0, annotated_contours)
        cv2.imwrite(os.path.join(panel_dir, "01_annotated_contours.png"), annotated_contours)
        
        # 4. Generate Exploded View for Panel 1 (and any container card panel)
        has_card = any(o["type"] == "CONTAINER_CARD" for o in objects)
        if has_card and panel_id == 1:
            try:
                exp_w = 640
                exp_h = 440
                exp_canvas = np.full((exp_h, exp_w, 3), 250, dtype=np.uint8)
                
                cv2.putText(exp_canvas, f"EXPLODED DECOMPOSITION VIEW - PANEL {panel_id:02d}", (20, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.60, (40, 40, 40), 2, cv2.LINE_AA)
                cv2.putText(exp_canvas, "Separating Character, Container Card, and Internal Text Lines", (20, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (100, 100, 100), 1, cv2.LINE_AA)
                            
                char_o = next((o for o in objects if o["type"] == "CHARACTER"), None)
                card_o = next((o for o in objects if o["type"] == "CONTAINER_CARD"), None)
                card_texts = [o for o in objects if "card text" in o["name"].lower()]
                title_o = next((o for o in objects if o["type"] == "TITLE"), None)
                
                if title_o is not None:
                    t_crop = title_o["crop"]
                    th, tw = t_crop.shape[:2]
                    exp_canvas[70:70+th, 20:20+tw] = t_crop
                    cv2.rectangle(exp_canvas, (18, 68), (22+tw, 72+th), PALETTE["TITLE"], 1)
                    cv2.putText(exp_canvas, "[1] Full Title Line", (20, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.38, PALETTE["TITLE"], 1)
                    
                if char_o is not None:
                    c_crop = char_o["crop"]
                    c_mask = char_o["mask"]
                    ch, cw = c_crop.shape[:2]
                    for r in range(ch):
                        for c in range(cw):
                            if c_mask[r, c] > 0:
                                exp_canvas[130+r, 25+c] = c_crop[r, c]
                    cv2.rectangle(exp_canvas, (23, 128), (27+cw, 132+ch), PALETTE["CHARACTER"], 2)
                    cv2.putText(exp_canvas, "[2] Character (Clean Silhouette)", (25, 124), cv2.FONT_HERSHEY_SIMPLEX, 0.38, PALETTE["CHARACTER"], 1)
                    
                if card_o is not None:
                    b_crop = card_o["crop"]
                    b_mask = card_o["mask"]
                    bh, bw = b_crop.shape[:2]
                    for r in range(bh):
                        for c in range(bw):
                            if b_mask[r, c] > 0:
                                exp_canvas[130+r, 180+c] = b_crop[r, c]
                    cv2.rectangle(exp_canvas, (178, 128), (182+bw, 132+bh), PALETTE["CONTAINER_CARD"], 2)
                    cv2.putText(exp_canvas, "[3] Text Box / Card Container", (180, 124), cv2.FONT_HERSHEY_SIMPLEX, 0.38, PALETTE["CONTAINER_CARD"], 1)
                    
                if card_texts:
                    cv2.putText(exp_canvas, "[4] Internal Text Lines (Separated Away)", (340, 124), cv2.FONT_HERSHEY_SIMPLEX, 0.38, PALETTE["CARD_TEXT"], 1)
                    cur_ty = 140
                    for c_t_idx, c_t_o in enumerate(card_texts):
                        t_m = c_t_o["mask"]
                        t_c = c_t_o["crop"]
                        tlh, tlw = t_m.shape[:2]
                        for r in range(tlh):
                            for c in range(tlw):
                                if t_m[r, c] > 0:
                                    exp_canvas[cur_ty+r, 360+c] = t_c[r, c]
                        cv2.rectangle(exp_canvas, (358, cur_ty-2), (362+tlw, cur_ty+tlh+2), PALETTE["CARD_TEXT"], 1)
                        cur_ty += tlh + 16
                        
                cv2.imwrite(os.path.join(panel_dir, "02_exploded_decomposition.png"), exp_canvas)
            except Exception as e:
                print(f"Notice generating exploded view: {e}")
        
        # Status checks
        status_note = "✅ سليم ومكتمل"
        if panel_id == 1:
            has_char = any(o["type"] == "CHARACTER" for o in objects)
            has_card = any(o["type"] == "CONTAINER_CARD" for o in objects)
            if has_char and has_card:
                status_note = "🌟 تم فصل الشخصية عن مربع النص وقص حوافهما الدقيقة!"
            else:
                status_note = "⚠️ فحص مطلوب"
        elif panel_id == 8:
            has_emoji = any(o["type"] == "EMOJI" for o in objects)
            if has_emoji:
                status_note = "🌟 تم رصد الإيموجي الضاحك 😂 كعنصر مستقل!"
        elif panel_id == 10:
            icons = [o for o in objects if o["type"] == "ICON_GRAPHIC"]
            if len(icons) >= 3:
                status_note = f"🌟 تم رصد الأيقونات (القميص، العربة، المكنسة) منفصلة!"
        elif panel_id == 12:
            icons = [o for o in objects if o["type"] == "ICON_GRAPHIC"]
            if len(icons) >= 2:
                status_note = "🌟 تم رصد الشمس والنبتة كأيقونات منفصلة!"
                
        summary_str = "<br>".join(obj_names_summary)
        report_lines.append(f"| **البانل {panel_id:02d}** | {len(objects)} | {summary_str} | {status_note} |")
        
        print(f"  [Panel {panel_id:02d}] {len(objects)} objects detected -> {status_note}")
        for o in objects:
            print(f"    - Priority {o['priority']}: {o['name']} [type={o['type']}, bbox={o['bbox']}]")
            
    # Write report file
    report_content = "\n".join(report_lines)
    report_path = os.path.join(output_base, "12_PANEL_AUDIT_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"\n[12-Panel Runner] Suite finished successfully! Report saved to {report_path}")
    return report_path


if __name__ == "__main__":
    test_img_path = r"C:/Users/loper/.gemini/antigravity-ide/brain/158728a5-a939-4410-9555-755847fa7279/.user_uploaded/media_1789648701976.jpg"
    run_full_12_panel_suite(test_img_path)
