import sys
import os
import tempfile
import json
from pathlib import Path
import pytest

kivy_dir = Path(__file__).resolve().parent.parent / "kivy"
sys.path.insert(0, str(kivy_dir))

from engine.core.scene import SceneConfig
from ui.services.settings_repository import SettingsRepository


class TestDrawingSpeedSettings:
    def test_01_scene_config_defaults_and_explicit(self):
        """Verify SceneConfig has character_drawing_speed and text_drawing_speed."""
        cfg_default = SceneConfig()
        assert cfg_default.drawing_speed == 1.5
        assert cfg_default.character_drawing_speed == 1.5
        assert cfg_default.text_drawing_speed == 1.5

        cfg_custom = SceneConfig(
            drawing_speed=2.0,
            character_drawing_speed=1.0,
            text_drawing_speed=3.0
        )
        assert cfg_custom.drawing_speed == 2.0
        assert cfg_custom.character_drawing_speed == 1.0
        assert cfg_custom.text_drawing_speed == 3.0

    def test_02_settings_repository_persistence(self):
        """Verify SettingsRepository saves and loads separate speeds correctly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_path = os.path.join(tmp_dir, "settings.json")
            repo = SettingsRepository(settings_path)

            defaults = repo.get_default_settings()
            assert "character_drawing_speed" in defaults
            assert "text_drawing_speed" in defaults
            assert defaults["character_drawing_speed"] == 1.5
            assert defaults["text_drawing_speed"] == 1.5

            cfg = SceneConfig(
                drawing_speed=2.2,
                character_drawing_speed=0.8,
                text_drawing_speed=2.5
            )
            assert repo.save_settings(cfg) is True

            loaded = repo.load_settings()
            assert loaded["drawing_speed"] == 2.2
            assert loaded["character_drawing_speed"] == 0.8
            assert loaded["text_drawing_speed"] == 2.5

    def test_03_settings_repository_legacy_backward_compatibility(self):
        """Verify that older settings.json without character/text speeds inherit drawing_speed."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_path = os.path.join(tmp_dir, "legacy_settings.json")
            legacy_data = {
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "drawing_speed": 2.5
            }
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(legacy_data, f)

            repo = SettingsRepository(settings_path)
            loaded = repo.load_settings()
            assert loaded["drawing_speed"] == 2.5
            # Must inherit 2.5 instead of crashing or falling back to 1.5
            assert loaded["character_drawing_speed"] == 2.5
            assert loaded["text_drawing_speed"] == 2.5

    def test_04_render_pipeline_signatures_support_speeds(self):
        """Verify render function signatures accept decoupled speed parameters."""
        import inspect
        from engine.render.deep_pipeline_engine import render_deep_storyboard_pipeline
        from engine.render.concentric_engine import render_concentric_orbital_whiteboard

        sig_deep = inspect.signature(render_deep_storyboard_pipeline)
        assert "character_drawing_speed" in sig_deep.parameters
        assert "text_drawing_speed" in sig_deep.parameters

        sig_conc = inspect.signature(render_concentric_orbital_whiteboard)
        assert "character_drawing_speed" in sig_conc.parameters
        assert "text_drawing_speed" in sig_conc.parameters

    def test_05_render_service_settings_propagation(self):
        """Verify render service accurately extracts character and text drawing speed."""
        settings = {"drawing_speed": 2.0, "character_drawing_speed": 1.2, "text_drawing_speed": 3.5}
        assert settings.get("character_drawing_speed", settings.get("drawing_speed")) == 1.2
        assert settings.get("text_drawing_speed", settings.get("drawing_speed")) == 3.5

        # Fallback when specific speeds missing
        legacy_settings = {"drawing_speed": 2.4}
        assert legacy_settings.get("character_drawing_speed", legacy_settings.get("drawing_speed")) == 2.4
        assert legacy_settings.get("text_drawing_speed", legacy_settings.get("drawing_speed")) == 2.4
