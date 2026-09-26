"""
Analysis Workflow Service — Orchestrates Background Image Processing & Composition Analysis.
"""
import time
import traceback
from threading import Thread
from typing import Callable, Optional, List, Dict, Any
import cv2
import numpy as np

from engine.core.scene import SceneConfig
from engine.processing.image_processor import ImageProcessor
from engine.core.project import Project


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


class AnalysisWorkflowService:
    def __init__(self):
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start_analysis_job(
        self,
        image_path: str,
        config: SceneConfig,
        progress_callback: Callable[[float, str], None],
        on_success_callback: Callable[[str, np.ndarray, Project], None],
        on_error_callback: Callable[[str], None],
        custom_panels: Optional[List[Dict[str, Any]]] = None
    ):
        """Starts asynchronous composition analysis in a background daemon thread."""
        if self._is_running:
            print("[AnalysisWorkflowService] Job already in progress, skipping duplicate launch.")
            return

        self._is_running = True
        def _worker():
            try:
                img = read_image_unicode(image_path)
                if img is None:
                    raise ValueError(f"Could not read image file at: {image_path}")

                last_report = [0.0]

                def _throttled_progress(pct, stage):
                    now = time.perf_counter()
                    if now - last_report[0] > 0.05 or pct >= 99.0:
                        last_report[0] = now
                        progress_callback(pct, stage)

                project = ImageProcessor.process(img, config, progress_cb=_throttled_progress, custom_panels=custom_panels)
                on_success_callback(image_path, img, project)

            except Exception as e:
                err_msg = str(e)
                print(f"[Analysis Error]: {err_msg}")
                traceback.print_exc()
                on_error_callback(err_msg)
            finally:
                self._is_running = False

        Thread(target=_worker, daemon=True).start()
