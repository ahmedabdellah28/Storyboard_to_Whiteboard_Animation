"""Test runner for UniversalStagedDirectorV2.
Tests advanced motion features:
1. Camera Push & Pan
2. Inking Connector Path between elements
3. Directional Flow entrance with subtle motion blur
4. Style 1 Grounded word card with no badge
"""

import sys
import os
import json
import cv2
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core_engine.universal_staged_director_v2 import UniversalStagedDirectorV2

def test_v2():
    manifest_path = ROOT_DIR / "sections" / "section_08" / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        base_manifest = json.load(f)

    # Two-Scene Continuous Sequence: Beat 1 -> Transition -> Beat 2 (The Next Animation)
    v2_manifest = dict(base_manifest)
    v2_manifest["total_duration"] = 11.0
    
    # Motion Transition #1: Morph Transition from Asset A -> Asset B (Seamless in-place transformation on grounded stage)
    morph_01 = {
        "from_asset": "r1_04_solution_cloning_dna",
        "to_asset": "r1_07_utah_pando_forest_map",
        "start": 5.0,
        "end": 5.65,
        "pos": [480, 600],
        "target_size": 480,
        "is_elevated": False
    }
    v2_manifest["morph_transitions"] = [morph_01]
    
    scene_01 = {
        "id": "v2_scene_01_cloning",
        "start": 0.0,
        "end": 5.3,
        "camera": {
            "duration": 0.9,
            "zoom_start": 1.0,
            "zoom_end": 1.08,
            "center_start": [960, 540],
            "center_end": [1080, 540]
        },
        "elements": [
            {
                "asset_key": "r1_04_solution_cloning_dna",
                "start": 0.0,
                "end": 5.0,
                "pos": [480, 600],
                "ground_y": 840,
                "target_size": 480,
                "is_elevated": False,
                "anim_type": "directional_flow"
            }
        ],
        "words": [
            {
                "start": 1.5,
                "end": 4.8,
                "word": "الحل هو الاستنساخ!",
                "theme": "teal",
                "pos": [1140, 540]
            }
        ]
    }
    
    scene_02 = {
        "id": "v2_scene_02_pando_forest",
        "start": 5.3,
        "end": 11.0,
        "camera": {
            "duration": 1.0,
            "zoom_start": 1.08,
            "zoom_end": 1.15,
            "center_start": [1080, 540],
            "center_end": [880, 540]
        },
        "elements": [
            {
                "asset_key": "r1_07_utah_pando_forest_map",
                "start": 5.65,
                "end": 11.0,
                "pos": [480, 600],
                "ground_y": 840,
                "target_size": 480,
                "is_elevated": False,
                "anim_type": "none",
                "scale_punches": [
                    {"time": 7.5, "duration": 0.22}
                ]
            }
        ],
        "words": [
            {
                "start": 6.6,
                "end": 10.5,
                "word": "غابة باندو (Pando)",
                "theme": "forest",
                "pos": [1180, 540]
            }
        ]
    }
    
    v2_manifest["scenes"] = [scene_01, scene_02]
    
    test_manifest_path = ROOT_DIR / "sections" / "section_08" / "manifest_v2_test.json"
    with open(test_manifest_path, "w", encoding="utf-8") as f:
        json.dump(v2_manifest, f, ensure_ascii=False, indent=2)

    print("🚀 Initializing UniversalStagedDirectorV2 for full sequence with Morph Transition...")
    director = UniversalStagedDirectorV2(test_manifest_path)
    
    # Capture key inspection frames across the morph timeline:
    print("📸 Rendering key inspection frames...")
    
    # 1. Grounded Beat 1 (t=3.2s): Tumbleweed firmly planted with floor shadow + card
    f1 = director.render_frame(3.2)
    cv2.imwrite(str(ROOT_DIR / "sections" / "test_v2_grounded_beat1.png"), f1)
    
    # 2. Morph Phase 1 - Inward Squash (t=5.16s): Tumbleweed squashes inward toward its base
    f_squash = director.render_frame(5.16)
    cv2.imwrite(str(ROOT_DIR / "sections" / "test_v2_morph_1_squash.png"), f_squash)
    
    # 3. Morph Midpoint - Energy Flash (t=5.32s): Incandescent spark & glowing ring at core
    f_spark = director.render_frame(5.32)
    cv2.imwrite(str(ROOT_DIR / "sections" / "test_v2_morph_2_spark.png"), f_spark)
    
    # 4. Morph Phase 2 - Elastic Bloom (t=5.50s): Utah Pando Forest blooms elastically in place
    f_bloom = director.render_frame(5.50)
    cv2.imwrite(str(ROOT_DIR / "sections" / "test_v2_morph_3_bloom.png"), f_bloom)
    
    # 5. Scene 2 Traveling Dot Mid-Flight (t=6.74s): Calibrated 0.28s trackable dot flying to card
    f_dot = director.render_frame(6.74)
    cv2.imwrite(str(ROOT_DIR / "sections" / "test_v2_card_dot_flying.png"), f_dot)
    
    # 6. Scene 2 Rapid Arabic Handwriting (t=7.08s): Glowing pen nib writing headline
    f_write = director.render_frame(7.08)
    cv2.imwrite(str(ROOT_DIR / "sections" / "test_v2_card_rapid_write.png"), f_write)
    
    # 7. Beat 2 Grounded Complete (t=8.2s): Grounded Forest map + complete Cairo headline card
    f_done = director.render_frame(8.2)
    cv2.imwrite(str(ROOT_DIR / "sections" / "test_v2_grounded_complete.png"), f_done)
    
    # Export full 11-second demo video
    print("🎬 Exporting 11-second V2 demo video...")
    out_video = ROOT_DIR / "exports" / "v2_test_motion_demo.mp4"
    audio_path = ROOT_DIR / "sections" / "section_08" / "voice" / "section_08.wav"
    director.export_video(str(out_video), str(audio_path))
    print(f"🎉 V2 Demo video ready at: {out_video}")

if __name__ == "__main__":
    test_v2()
