import os
import cv2
import numpy as np
from pathlib import Path
from typing import Optional


class VideoEncoder:
    def __init__(
        self,
        output_path: str,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        crf: int = 20
    ):
        """
        Direct Single-Pass H.264 Encoder via PyAV.
        Streams frames from memory directly into MP4 container.
        """
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.crf = crf
        self.use_pyav = True
        self.container = None
        self.stream = None
        self.cv2_writer = None

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        try:
            import av
            self.container = av.open(str(output_path), mode="w")
            codec_name = self._detect_best_codec(fps)
            self.stream = self.container.add_stream(codec_name, rate=fps)
            self.stream.width = width
            self.stream.height = height
            self.stream.pix_fmt = "yuv420p"
            self.stream.options = {"crf": str(crf)}
            print(f"[VideoEncoder] Initialized PyAV H.264 stream with codec: {codec_name}")
        except Exception as e:
            print(f"[VideoEncoder] PyAV init fallback to OpenCV VideoWriter: {e}")
            self.use_pyav = False
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.cv2_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    def _detect_best_codec(self, fps: int) -> str:
        """
        Tests if hardware accelerated NVENC is available, otherwise uses h264/libx264.
        """
        import av
        # Try NVENC
        try:
            test_c = av.open(os.devnull, mode="w", format="mp4")
            test_s = test_c.add_stream("h264_nvenc", rate=fps)
            test_c.close()
            return "h264_nvenc"
        except Exception:
            pass

        # Fallback to standard CPU H.264
        return "h264"

    def write_frame(self, frame_bgr: np.ndarray):
        """
        Encodes a single BGR frame.
        """
        if self.use_pyav and self.stream and self.container:
            import av
            # Ensure correct resolution
            if frame_bgr.shape[1] != self.width or frame_bgr.shape[0] != self.height:
                frame_bgr = cv2.resize(frame_bgr, (self.width, self.height), interpolation=cv2.INTER_LINEAR)

            video_frame = av.VideoFrame.from_ndarray(frame_bgr, format="bgr24")
            for packet in self.stream.encode(video_frame):
                self.container.mux(packet)
        elif self.cv2_writer:
            if frame_bgr.shape[1] != self.width or frame_bgr.shape[0] != self.height:
                frame_bgr = cv2.resize(frame_bgr, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
            self.cv2_writer.write(frame_bgr)

    def close(self):
        """
        Flushes and finalizes the MP4 video container.
        """
        if self.use_pyav and self.stream and self.container:
            try:
                for packet in self.stream.encode():
                    self.container.mux(packet)
                self.container.close()
                print(f"[VideoEncoder] Successfully finalized MP4: {self.output_path}")
            except Exception as e:
                print(f"[VideoEncoder] Error finalizing PyAV container: {e}")
        elif self.cv2_writer:
            self.cv2_writer.release()
            print(f"[VideoEncoder] Finalized OpenCV video: {self.output_path}")
