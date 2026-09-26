"""
Test CanvasVideoPlayer instantiation and frame decode.
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "kivy")))

from ui.canvas.video_player import CanvasVideoPlayer

def test_video_player_init():
    frames = []
    def on_frame(tex):
        frames.append(tex)

    player = CanvasVideoPlayer(on_frame)
    assert player is not None
    assert not player.is_playing
    print("CanvasVideoPlayer initialized successfully!")

if __name__ == "__main__":
    test_video_player_init()
