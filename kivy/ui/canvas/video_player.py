"""
Canvas Video Player — Manages In-App Video Playback Texture Stream via OpenCV.
"""
import os
import cv2
import numpy as np
from typing import Callable, Optional
from kivy.clock import Clock
# pyrefly: ignore [missing-import]
from kivy.graphics.texture import Texture


class CanvasVideoPlayer:
    def __init__(self, on_frame_update_cb: Callable[[Texture], None]):
        self._on_frame_update_cb = on_frame_update_cb
        self._cap = None
        self._video_path = None
        self._video_clock = None
        self._is_playing = False
        self._total_frames = 0
        self._current_frame_idx = 0
        self._fps = 30.0
        self._persistent_texture: Optional[Texture] = None
        self.on_progress_cb: Optional[Callable[[float, int, int], None]] = None

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def has_video(self) -> bool:
        return self._cap is not None

    @property
    def fps(self) -> float:
        return self._fps

    def play_video(self, video_path: str):
        if not os.path.exists(video_path):
            return
        self.stop_video()
        self._video_path = video_path
        self._cap = cv2.VideoCapture(video_path)
        if not self._cap.isOpened():
            return

        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._fps = float(self._cap.get(cv2.CAP_PROP_FPS)) or 30.0
        self._current_frame_idx = 0
        self._is_playing = True
        self._persistent_texture = None

        self._video_clock = Clock.schedule_interval(self._tick_video_frame, 1.0 / self._fps)

    def _tick_video_frame(self, dt):
        if not self._cap or not self._is_playing:
            return

        ret, frame = self._cap.read()
        if not ret:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self._cap.read()
            if not ret:
                return

        self._current_frame_idx += 1
        h, w = frame.shape[:2]

        if self._persistent_texture is None or self._persistent_texture.size != (w, h):
            self._persistent_texture = Texture.create(size=(w, h), colorfmt='rgba')

        frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        buf = np.ascontiguousarray(cv2.flip(frame_rgba, 0)).tobytes()
        self._persistent_texture.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')

        if self._on_frame_update_cb:
            self._on_frame_update_cb(self._persistent_texture)

        if self.on_progress_cb:
            pct = (self._current_frame_idx / float(max(1, self._total_frames)))
            self.on_progress_cb(pct, self._current_frame_idx, self._total_frames)

    def toggle_play_pause(self):
        self._is_playing = not self._is_playing

    def replay_video(self):
        if self._cap:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self._current_frame_idx = 0
            self._is_playing = True

    def stop_video(self):
        if self._video_clock:
            self._video_clock.cancel()
            self._video_clock = None
        if self._cap:
            self._cap.release()
            self._cap = None
        self._is_playing = False
        self._persistent_texture = None
