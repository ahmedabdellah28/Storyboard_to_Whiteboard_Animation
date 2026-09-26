import cv2
import json
import os
import numpy as np

img = cv2.imread("project_content/images/ChatGPT Image Sep 18, 2026, 06_50_39 PM.png", cv2.IMREAD_UNCHANGED)
h, w = img.shape[:2]

with open("experiments/transparent_assets_manifest.json") as f:
    manifest = json.load(f)

# Composite on white background with labels
b, g, r, a = cv2.split(img)
white_bg = np.full((h, w, 3), 255, dtype=np.uint8)
a_norm = a.astype(np.float32) / 255.0
a_3 = np.repeat(a_norm[:, :, np.newaxis], 3, axis=2)
labeled = (cv2.merge([b, g, r]).astype(np.float32) * a_3 + white_bg.astype(np.float32) * (1.0 - a_3)).astype(np.uint8)

for item in manifest:
    x, y, bw, bh = item["bbox"]
    aid = item["id"]
    cv2.rectangle(labeled, (x, y), (x + bw, y + bh), (0, 0, 255), 2)
    cv2.putText(labeled, f"#{aid}", (x + 5, y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 0, 0), 2)

cv2.imwrite("experiments/labeled_assets_contact_sheet.jpg", labeled)
print("Labeled contact sheet generated at experiments/labeled_assets_contact_sheet.jpg")
