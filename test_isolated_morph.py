"""Isolated Test for Motion Graphic #1: Morph Transition (تحول العنصر A إلى B بصرياً).

Purity & Coherence Criteria:
1. Zero simultaneous clutter: Camera is 100% static, no directional flows or scale punches.
2. Contextual & Semantic Harmony:
   - Element A: r1_05_genetic_clone_100_percent (Single curious sprout/sapling)
   - Element B: r2_03_counter_40k_trees_one_organism (Massive forest of interconnected trees)
   - Narrative text matches visual evolution: "نبتة منفردة؟" -> Morph -> "غابة كاملة ككائن واحد!"
3. Temporal Rhythm:
   - Beat 1 (0.0s - 2.0s): Element A + Text A
   - Beat 2 (2.2s - 3.0s): Pure Morph Transition (squash -> spark -> elastic bloom)
   - Beat 3 (3.2s - 6.0s): Element B settles grounded + Text B writes with glowing nib
"""

import sys
import json
import cv2
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core_engine.universal_staged_director_v2 import UniversalStagedDirectorV2

def run_isolated_morph_test():
    manifest = {
        "title": "تجربة معزولة: Morph Transition (نبتة إلى غابة)",
        "total_duration": 6.5,
        "fps": 30,
        "resolution": [1920, 1080],
        # Completely static camera so user can inspect the transformation in 100% focus
        "camera": {
            "duration": 6.5,
            "zoom_start": 1.0,
            "zoom_end": 1.0,
            "center_start": [960, 540],
            "center_end": [960, 540]
        },
        # Motion Transition #1: Morph Transition (Element A -> Element B)
        "morph_transitions": [
            {
                "from_asset": "r1_05_genetic_clone_100_percent",
                "to_asset": "r2_03_counter_40k_trees_one_organism",
                "start": 2.2,
                "end": 2.95,
                "pos": [500, 600],
                "target_size": 500,
                "is_elevated": False
            }
        ],
        "scenes": [
            {
                "id": "scene_isolated_morph",
                "start": 0.0,
                "end": 6.5,
                "elements": [
                    {
                        "asset_key": "r1_05_genetic_clone_100_percent",
                        "start": 0.0,
                        "end": 2.2,
                        "pos": [500, 600],
                        "ground_y": 840,
                        "target_size": 480,
                        "is_elevated": False,
                        "anim_type": "none",
                        "exit_type": "none"
                    },
                    {
                        "asset_key": "r2_03_counter_40k_trees_one_organism",
                        "start": 2.95,
                        "end": 6.5,
                        "pos": [500, 600],
                        "ground_y": 840,
                        "target_size": 520,
                        "is_elevated": False,
                        "anim_type": "none",
                        "exit_type": "none"
                    }
                ],
                "words": [
                    # Beat 1 Text: Question about single sprout
                    {
                        "start": 0.4,
                        "end": 2.0,
                        "word": "نبتة منفردة؟",
                        "theme": "teal",
                        "pos": [1220, 540]
                    },
                    # Beat 3 Text: Answer after morph finishes
                    {
                        "start": 3.2,
                        "end": 6.2,
                        "word": "غابة كاملة ككائن واحد!",
                        "theme": "forest",
                        "pos": [1220, 540]
                    }
                ]
            }
        ]
    }

    manifest_path = ROOT_DIR / "sections" / "section_08" / "manifest_isolated_morph.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("🚀 Initializing UniversalStagedDirectorV2 for Isolated Morph Test...")
    director = UniversalStagedDirectorV2(manifest_path)

    # Render key inspection frames:
    print("📸 Rendering inspection frames...")
    # 1. Element A sitting grounded before morph (t = 1.6s)
    f_before = director.render_frame(1.6)
    cv2.imwrite(str(ROOT_DIR / "sections" / "isolated_morph_1_before.png"), f_before)

    # 2. Inward anticipation squash (t = 2.40s)
    f_squash = director.render_frame(2.40)
    cv2.imwrite(str(ROOT_DIR / "sections" / "isolated_morph_2_squash.png"), f_squash)

    # 3. Incandescent spark at midpoint (t = 2.58s)
    f_spark = director.render_frame(2.58)
    cv2.imwrite(str(ROOT_DIR / "sections" / "isolated_morph_3_spark.png"), f_spark)

    # 4. Elastic bloom emergence of Element B (t = 2.80s)
    f_bloom = director.render_frame(2.80)
    cv2.imwrite(str(ROOT_DIR / "sections" / "isolated_morph_4_bloom.png"), f_bloom)

    # 5. Beat 3: Forest grounded + handwriting card (t = 4.2s)
    f_after = director.render_frame(4.2)
    cv2.imwrite(str(ROOT_DIR / "sections" / "isolated_morph_5_complete.png"), f_after)

    # Export isolated video
    print("🎬 Exporting isolated 6.5s morph demo video...")
    out_video = ROOT_DIR / "exports" / "isolated_morph_demo.mp4"
    audio_path = ROOT_DIR / "sections" / "section_08" / "voice" / "section_08.wav"
    director.export_video(str(out_video), str(audio_path))
    print(f"🎉 Isolated Morph Video ready at: {out_video}")

if __name__ == "__main__":
    run_isolated_morph_test()
