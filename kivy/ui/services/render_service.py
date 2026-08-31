"""
Render Workflow Service — Orchestrates Background Animation Video Rendering & Job Lifecycle.
"""
import os
import datetime
import traceback
from threading import Thread
from typing import Callable, Optional, List, Dict, Any
import numpy as np

from engine.core.scene import SceneObject
from sketchApi import render_concentric_orbital_whiteboard


class RenderWorkflowService:
    def __init__(self, output_directory: str):
        self.output_directory = output_directory
        os.makedirs(self.output_directory, exist_ok=True)
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start_render_job(
        self,
        source_image: np.ndarray,
        settings: Dict[str, Any],
        objects_to_render: List[SceneObject],
        progress_callback: Callable[[float, str], None],
        on_complete_callback: Callable[[str], None],
        on_error_callback: Callable[[str], None],
        job_prefix: str = "sketch"
    ):
        """Starts asynchronous video rendering in a background daemon thread."""
        if self._is_running:
            print("[RenderWorkflowService] Render job already in progress, skipping duplicate launch.")
            return

        def _worker():
            self._is_running = True
            try:
                now = datetime.datetime.now()
                filename = f"{job_prefix}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
                out_path = os.path.join(self.output_directory, filename)

                drawing_speed = float(settings.get("drawing_speed", 1.5))
                camera_zoom_scale = float(settings.get("camera_zoom_scale", 2.0))
                fps = int(settings.get("fps", 30))
                element_spacing = int(settings.get("element_spacing", 24))
                drawing_direction = str(settings.get("drawing_direction", "OUTSIDE_IN"))
                ring_step = int(settings.get("ring_step", 5))
                brush_radius = int(settings.get("brush_radius", 8))
                sample_interval = float(settings.get("sample_interval", 3.0))
                show_hand = bool(settings.get("show_hand", True))
                hand_scale = float(settings.get("hand_scale", 0.75))
                end_hold_seconds = float(settings.get("end_hold_seconds", 1.5))

                render_concentric_orbital_whiteboard(
                    image_input=source_image,
                    output_path=out_path,
                    fps=fps,
                    drawing_speed=drawing_speed,
                    camera_zoom_scale=camera_zoom_scale,
                    element_spacing=element_spacing,
                    drawing_direction=drawing_direction,
                    ring_step=ring_step,
                    brush_radius=brush_radius,
                    sample_interval=sample_interval,
                    show_hand=show_hand,
                    hand_scale=hand_scale,
                    end_hold_seconds=end_hold_seconds,
                    custom_objects=objects_to_render,
                    progress_callback=progress_callback
                )

                on_complete_callback(out_path)

            except Exception as e:
                err_msg = str(e)
                print(f"[Render Error]: {err_msg}")
                traceback.print_exc()
                on_error_callback(err_msg)
            finally:
                self._is_running = False

        Thread(target=_worker, daemon=True).start()
