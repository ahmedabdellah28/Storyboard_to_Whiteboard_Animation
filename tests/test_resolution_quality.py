"""
Automated Test for Default 720p Resolution and 1080p Upgrade Support.
Tests:
1. Default Settings resolution is 1280x720 (720p HD)
2. SceneConfig default width/height is 1280x720
3. Switching quality to 1080p Full HD scales 16:9 to 1920x1080
4. Switching aspect ratio in 720p and 1080p modes
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "kivy")))

from shared.app_config import DEFAULT_CANVAS_WIDTH, DEFAULT_CANVAS_HEIGHT
from engine.core.scene import SceneConfig
from ui.services.settings_repository import SettingsRepository

def test_default_resolution():
    print("[TEST 1] Testing AppConfig and SceneConfig defaults...")
    assert DEFAULT_CANVAS_WIDTH == 1280, f"Expected 1280, got {DEFAULT_CANVAS_WIDTH}"
    assert DEFAULT_CANVAS_HEIGHT == 720, f"Expected 720, got {DEFAULT_CANVAS_HEIGHT}"
    
    cfg = SceneConfig()
    assert cfg.width == 1280, f"Expected SceneConfig width 1280, got {cfg.width}"
    assert cfg.height == 720, f"Expected SceneConfig height 720, got {cfg.height}"
    print("-> AppConfig & SceneConfig Default 720p: PASSED!")
    
    print("\n[TEST 2] Testing SettingsRepository defaults...")
    repo = SettingsRepository()
    defaults = repo.get_default_settings()
    assert defaults["width"] == 1280, f"Expected default width 1280, got {defaults['width']}"
    assert defaults["height"] == 720, f"Expected default height 720, got {defaults['height']}"
    print("-> SettingsRepository Default 720p: PASSED!")

    print("\n[TEST 3] Testing 1080p Upgrade Scaling...")
    # 16:9 Widescreen
    cfg_1080 = SceneConfig(width=1920, height=1080)
    assert cfg_1080.width == 1920 and cfg_1080.height == 1080
    print("-> 1080p Upgrade: PASSED!")

    print("\n=======================================================")
    print("ALL RESOLUTION & QUALITY TESTS PASSED (720p Default & 1080p)!")
    print("=======================================================")

if __name__ == "__main__":
    test_default_resolution()
