"""
Universal Multi-Scale Layer Splitter Test Pipeline
Processes all 3 test images in test_images/ and produces full 12-panel separation matrices.
"""
import os
import sys
import time
import cv2
import numpy as np

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_root, 'kivy'))
sys.path.insert(0, os.path.join(_root, 'experiments', 'modular_pipeline'))

from engine.processing.m1_panel_extractor import DynamicPanelExtractor
from engine.render.deep_pipeline_engine import enhance_panel_clarity_and_vibrance


class UniversalLayerSplitter:
    """
    Universal Scale-Invariant Layer Splitter:
    Automatically adapts all topological and geometric thresholds to any panel resolution.
    """
    @staticmethod
    def split(panel_crop: np.ndarray) -> dict:
        ph, pw = panel_crop.shape[:2]
        
        # Scale factor relative to baseline 170px panel height
        scale = ph / 170.0

        # Multi-channel ink distance (threshold > 26.0)
        diff = 255.0 - panel_crop.astype(np.float32)
        dist = np.max(diff, axis=2)
        ink_bin = (dist > 26.0).astype(np.uint8) * 255

        num_cc, labels, stats, _ = cv2.connectedComponentsWithStats(ink_bin)

        text_mask = np.zeros((ph, pw), dtype=np.uint8)
        graphics_mask = np.zeros((ph, pw), dtype=np.uint8)

        # Scaled thresholds matching Method A benchmark
        max_ch = int(round(28 * scale))
        max_cw = int(round(85 * scale))
        max_carea = int(round(260 * scale * scale))
        min_dot = int(round(20 * scale * scale))
        max_uh = int(round(7 * scale))

        for i in range(1, num_cc):
            cw = stats[i, cv2.CC_STAT_WIDTH]
            ch = stats[i, cv2.CC_STAT_HEIGHT]
            carea = stats[i, cv2.CC_STAT_AREA]
            aspect = cw / float(ch + 1e-5)

            if (ch <= max_ch and cw <= max_cw and carea < max_carea) or carea <= min_dot or (aspect > 4.5 and ch <= max_uh):
                text_mask[labels == i] = 255
            else:
                graphics_mask[labels == i] = 255

        # Render isolated layers onto pure white canvas
        graphics_image = np.full_like(panel_crop, 255)
        graphics_image[graphics_mask > 0] = panel_crop[graphics_mask > 0]

        text_image = np.full_like(panel_crop, 255)
        text_image[text_mask > 0] = panel_crop[text_mask > 0]

        return {
            "graphics_image": graphics_image,
            "text_image": text_image,
            "graphics_mask": graphics_mask,
            "text_mask": text_mask
        }


def build_full_matrix_card(image_label: str, split_results: list, output_path: str):
    row_h = 130
    col_w = 200
    matrix_h = len(split_results) * (row_h + 8) + 65
    matrix_w = 3 * (col_w + 10) + 15
    master_matrix = np.full((matrix_h, matrix_w, 3), 245, dtype=np.uint8)

    cv2.rectangle(master_matrix, (0, 0), (matrix_w, 50), (30, 30, 40), -1)
    title_text = f"UNIVERSAL SPLIT MATRIX — {image_label} ({len(split_results)} PANELS)"
    cv2.putText(master_matrix, title_text, (15, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 220, 255), 2, cv2.LINE_AA)

    for r_idx, res in enumerate(split_results):
        pid = res['id']
        gy = 58 + r_idx * (row_h + 8)
        items = [res['crop'], res['graphics'], res['typography']]
        headers = [f"P#{pid:02d} Original", f"P#{pid:02d} Graphics", f"P#{pid:02d} Text"]

        for c_idx in range(3):
            gx = 10 + c_idx * (col_w + 10)
            im = items[c_idx]
            sc_m = min((col_w - 6) / float(im.shape[1]), (row_h - 22) / float(im.shape[0]))
            iw_sc = int(im.shape[1] * sc_m)
            ih_sc = int(im.shape[0] * sc_m)
            img_sc = cv2.resize(im, (iw_sc, ih_sc), interpolation=cv2.INTER_AREA)

            cv2.rectangle(master_matrix, (gx, gy), (gx + col_w, gy + row_h), (255, 255, 255), -1)
            cv2.rectangle(master_matrix, (gx, gy), (gx + col_w, gy + row_h), (180, 180, 180), 1)

            ox = gx + (col_w - iw_sc) // 2
            oy = gy + 20 + (row_h - 22 - ih_sc) // 2
            master_matrix[oy : oy + ih_sc, ox : ox + iw_sc] = img_sc

            cv2.rectangle(master_matrix, (gx, gy), (gx + col_w, gy + 18), (45, 45, 55), -1)
            cv2.putText(master_matrix, headers[c_idx], (gx + 6, gy + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 255, 255), 1, cv2.LINE_AA)

    cv2.imwrite(output_path, master_matrix)
    print(f"  [OK] Saved Master Matrix: {output_path}")


def run_test():
    output_dir = os.path.join(_root, "experiments", "results", "universal_layer_split_test")
    os.makedirs(output_dir, exist_ok=True)

    test_images = [
        ("Image_1_Sep_1_09_30_00_PM", "ChatGPT Image Sep 1, 2026, 09_30_00 PM.png"),
        ("Image_2_Sep_1_09_30_02_PM", "ChatGPT Image Sep 1, 2026, 09_30_02 PM.png"),
        ("Image_3_Sep_2_11_35_01_PM", "ChatGPT Image Sep 2, 2026, 11_35_01 PM.png")
    ]

    print("=================================================================")
    print("UNIVERSAL MULTI-SCALE LAYER SPLITTER TEST")
    print("=================================================================")

    for label, img_name in test_images:
        img_path = os.path.join(_root, "test_images", img_name)
        if not os.path.exists(img_path):
            print(f"Skipping {img_name}: File not found")
            continue

        print(f"\nProcessing {label} ({img_name})...")
        t0 = time.time()
        img = cv2.imread(img_path)
        panels = DynamicPanelExtractor.extract_panels(img, border_inset=8)
        print(f"  • Extracted {len(panels)} panels.")

        split_results = []
        for p in panels:
            pid = p['id']
            crop = p['crop']
            
            # Apply Universal Splitter
            res = UniversalLayerSplitter.split(crop)
            split_results.append({
                'id': pid,
                'crop': crop,
                'graphics': res['graphics_image'],
                'typography': res['text_image']
            })

        out_matrix = os.path.join(output_dir, f"{label}_12_panels_matrix.png")
        build_full_matrix_card(label, split_results, out_matrix)
        t_elapsed = time.time() - t0
        print(f"  • Finished in {t_elapsed:.2f}s ({len(split_results)} panels processed).")

    print("\n=================================================================")
    print(f"ALL TESTS COMPLETE! Results saved to: {output_dir}")
    print("=================================================================")


if __name__ == "__main__":
    run_test()
