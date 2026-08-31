"""
Image IO Utility — Supports unicode paths across Windows, Linux, and Android.
"""
from typing import Optional
import cv2
import numpy as np


def read_image_unicode(img_path) -> Optional[np.ndarray]:
    """Read image supporting unicode file paths."""
    if isinstance(img_path, np.ndarray):
        return img_path
    try:
        bytes_data = np.fromfile(str(img_path), dtype=np.uint8)
        return cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"[ImageIO Error]: {e}")
        return None
