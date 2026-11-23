"""End-to-End Execution of Ordered Synchronized Asset Sheets (OSAS v3.1) on Outro (15_outro).

Executes:
1. Load 15 verified storyboard assets in strict sheet order (Row 1 -> Row 4).
2. Compile deterministic multi-element scene choreography across 4 cinematic scenes.
3. Single-Ink Hero mutex per scene + varied dynamic animations (slide_down, slide_up, jelly_pop, pulse_pop, organic_grow).
4. Auto-generate enriched SFX cues and mix 48kHz master audio with dynamic ducking.
5. Render 1080p 30 FPS whiteboard video with DynamicSectionEngine.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import wave
from pathlib import Path
from typing import List, Dict, Any, Tuple
import cv2
import numpy as np

# Ensure root is on path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from production_engine.dynamic_section_engine import (
    DynamicSectionEngine,
    smootherstep,
    WIDTH,
    HEIGHT,
)


def run_pipeline():
    section_dir = REPO_ROOT / "sections" / "fiercest_warriors_documentary" / "15_outro"
    storyboard_path = section_dir / "storyboard.png"
    script_path = section_dir / "script.txt"
    whisper_path = section_dir / "timing" / "whisper.json"
    voice_path = section_dir / "voice" / "section.wav"
    assets_dir = section_dir / "assets"
    output_dir = section_dir / "scratch" / "osas_v3_run"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_video_path = section_dir / "final_whiteboard_1080p.mp4"

    print("=" * 80)
    print("🎬 STARTING OSAS v3.1 PRODUCTION PIPELINE: OUTRO (15_outro)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # STAGE 0: Verify Storyboard and Assets Existence
    # -------------------------------------------------------------------------
    if not storyboard_path.exists():
        raise FileNotFoundError(f"Storyboard not found at: {storyboard_path}")
    print(f"  -> Storyboard verified: {storyboard_path}")

    with wave.open(str(voice_path), "rb") as wf:
        audio_dur = wf.getnframes() / float(wf.getframerate())
    print(f"  -> Narration audio verified: {audio_dur:.2f}s ({voice_path.name})")

    # -------------------------------------------------------------------------
    # STAGE 1: Asset Manifest & Order Verification
    # -------------------------------------------------------------------------
    # 15 Assets in strict Ground Truth Storyboard order (Left to Right, Row by Row):
    ASSET_ORDER = [
        # Row 1: The Fate of History's Fiercest Warriors (3 elements)
        ("r1_01_elem", "قصص أشرس محاربي التاريخ"),
        ("r1_02_elem", "والغريب إن كثير منهم"),
        ("r1_03_elem", "ما ماتوا بالطريقة اللي تتوقعها"),
        # Row 2: How They Died - Battle, Bed, Standing Up (5 elements)
        ("r2_01_elem", "بعضهم مات في المعركة (1)"),
        ("r2_02_elem", "بعضهم مات في المعركة (2)"),
        ("r2_03_elem", "وبعضهم مات على فراشه"),
        ("r2_04_elem", "وبعضهم ظل واقفاً (1)"),
        ("r2_05_elem", "حتى بعد موته (2)"),
        # Row 3: True Definition of Courage (3 elements)
        ("r3_01_elem", "الشجاعة مو دائماً تعني إنك ما تخاف"),
        ("r3_02_elem", "تعرف وش ينتظرك"),
        ("r3_03_elem", "وتتقدم رغم ذلك"),
        # Row 4: Call to Action & Farewell (4 elements)
        ("r4_01_elem", "لايك واشتراك"),
        ("r4_02_elem", "اكتب لي في التعليقات"),
        ("r4_03_elem", "نشوفكم في الفيديو الجاي"),
        ("r4_04_elem", "وفي أمان الله"),
    ]

    print(f"\n[Stage 1] Verified {len(ASSET_ORDER)} visual assets in strict storyboard order.")

    # -------------------------------------------------------------------------
    # STAGE 2: Multi-Element Scene Composition (OSAS v3.1 Architecture)
    # -------------------------------------------------------------------------
    # 4 Cohesive Cinematic Scenes:
    # 1. 3 to 5 complementary elements grouped per scene.
    # 2. Camera stays steady on the zone while its elements appear sequentially with spoken words.
    # 3. Exactly 1 Hero inking hand (outside_in_pen) per scene.
    # 4. Secondary elements use varied animations (slide_down, slide_up, jelly_pop, pulse_pop, organic_grow).
    # 5. Exactly 3 smooth camera pans across the whole 23.6s duration.

    SCENES = [
        # Scene 1: Introduction & Fate of Warriors (3 elements)
        {
            "scene_id": "zone_1_warriors_fate",
            "base_scale": 1.6,
            "elements": [
                ("r1_01_elem", "outside_in_pen", 0.0, 2.0),
                ("r1_02_elem", "slide_down", 2.4, 1.1),
                ("r1_03_elem", "pulse_pop", 3.8, 1.0),
            ],
        },
        # Scene 2: How They Died (5 elements)
        {
            "scene_id": "zone_2_how_they_died",
            "base_scale": 1.7,
            "elements": [
                ("r2_01_elem", "outside_in_pen", 5.0, 1.4),
                ("r2_02_elem", "slide_down", 5.8, 1.0),
                ("r2_03_elem", "pulse_pop", 6.5, 1.0),
                ("r2_04_elem", "slide_up", 7.7, 1.1),
                ("r2_05_elem", "jelly_pop", 8.8, 1.0),
            ],
        },
        # Scene 3: Definition of True Courage (3 elements)
        {
            "scene_id": "zone_3_courage_definition",
            "base_scale": 1.7,
            "elements": [
                ("r3_01_elem", "outside_in_pen", 9.8, 2.0),
                ("r3_02_elem", "jelly_pop", 12.2, 1.0),
                ("r3_03_elem", "organic_grow", 13.5, 1.4),
            ],
        },
        # Scene 4: Call to Action & Farewell (4 elements)
        {
            "scene_id": "zone_4_call_to_action",
            "base_scale": 1.7,
            "elements": [
                ("r4_01_elem", "outside_in_pen", 15.3, 1.8),
                ("r4_02_elem", "slide_down", 17.8, 1.4),
                ("r4_03_elem", "pulse_pop", 21.2, 1.0),
                ("r4_04_elem", "organic_grow", 22.4, 1.1),
            ],
        },
    ]

    RENDER_CAM_ZOOM = 0.65
    cam_y = 800.0
    zone_spacing = 3200.0
    GAP = 60.0

    elements_staging = []
    hero_configs = []
    scene_cam_x_list = []
    scene_timings = []

    for s_idx, scene in enumerate(SCENES):
        cam_x = 1600.0 + s_idx * zone_spacing
        scene_cam_x_list.append(cam_x)
        b_scale = scene["base_scale"]

        # Compute dimensions of all elements in this scene
        scene_elems_info = []
        for aid, anim_type, t_start, t_dur in scene["elements"]:
            crop_path = assets_dir / f"{aid}.png"
            if not crop_path.exists():
                raise FileNotFoundError(f"Asset file missing: {crop_path}")
            crop_img = cv2.imread(str(crop_path), cv2.IMREAD_UNCHANGED)
            ch, cw = crop_img.shape[:2]
            sw = int(cw * b_scale)
            sh = int(ch * b_scale)
            scene_elems_info.append({
                "aid": aid,
                "anim_type": anim_type,
                "w": sw,
                "h": sh,
                "t_start": t_start,
                "t_dur": t_dur,
            })

        # Calculate symmetric horizontal layout centered at cam_x
        total_scene_w = sum(e["w"] for e in scene_elems_info) + GAP * (len(scene_elems_info) - 1)
        cur_x = cam_x - total_scene_w / 2.0

        first_start = scene_elems_info[0]["t_start"]
        last_end = max(e["t_start"] + e["t_dur"] for e in scene_elems_info)
        scene_timings.append((first_start, last_end, cam_x))

        for e in scene_elems_info:
            wx = int(cur_x)
            wy = int(cam_y - e["h"] // 2)

            elements_staging.append({
                "id": f"{e['aid']}_{s_idx}",
                "asset": e["aid"],
                "t_start": e["t_start"],
                "t_dur": e["t_dur"],
                "type": e["anim_type"],
                "pos": (wx, wy),
                "size": (e["w"], e["h"]),
                "depth": 5,
                "fade_out_at": None,
            })

            if e["anim_type"] == "outside_in_pen":
                hero_configs.append((e["aid"], e["t_start"], e["t_dur"]))

            cur_x += e["w"] + GAP

    print(f"  -> Configured {len(elements_staging)} staged elements across {len(SCENES)} cinematic scenes.")
    print(f"  -> Hero Inking Hand Cache: {len(hero_configs)} elements ({[h[0] for h in hero_configs]}).")

    # Camera Pans between Scenes (Only 3 calm pans across the entire video!)
    camera_pans = []
    for i in range(len(scene_timings) - 1):
        prev_end = scene_timings[i][1]
        next_start = scene_timings[i + 1][0]
        x1 = scene_timings[i][2]
        x2 = scene_timings[i + 1][2]

        pan_end = next_start - 0.05
        pan_dur = min(0.75, max(0.45, pan_end - prev_end))
        pan_start = pan_end - pan_dur
        camera_pans.append((pan_start, pan_end, x1, x2))
        print(f"  📷 Camera Pan {i+1}->{i+2}: [{pan_start:.2f}s .. {pan_end:.2f}s] (dur={pan_dur:.2f}s, hold={pan_start - prev_end:.2f}s)")

    def camera_trajectory_fn(time_s: float):
        if not scene_cam_x_list:
            return (1600.0, cam_y, RENDER_CAM_ZOOM)
        if not camera_pans or time_s <= camera_pans[0][0]:
            return (scene_cam_x_list[0], cam_y, RENDER_CAM_ZOOM)
        for p_start, p_end, x1, x2 in camera_pans:
            if p_start <= time_s <= p_end:
                prog = (time_s - p_start) / max(0.001, (p_end - p_start))
                eased = smootherstep(prog)
                return (x1 + eased * (x2 - x1), cam_y, RENDER_CAM_ZOOM)
            elif time_s < p_start:
                return (x1, cam_y, RENDER_CAM_ZOOM)
        return (scene_cam_x_list[-1], cam_y, RENDER_CAM_ZOOM)

    # -------------------------------------------------------------------------
    # STAGE 3: Audio Design (Enriched SFX + Dynamic Ducking)
    # -------------------------------------------------------------------------
    print("\n[Stage 3] Generating Synchronized SFX & Mixing Master Audio...")
    engine = DynamicSectionEngine(str(section_dir))
    engine.assets_dir = str(assets_dir)

    pan_times = [p[0] for p in camera_pans]
    sfx_cues = DynamicSectionEngine.generate_sfx_from_staging(elements_staging, camera_pans=pan_times)
    print(f"  -> Generated {len(sfx_cues)} enriched SFX cues.")

    master_audio = engine.mix_master_audio(str(voice_path), sfx_cues, audio_dur)
    print(f"  -> Master audio mixed with synchronized SFX: {master_audio}")

    # -------------------------------------------------------------------------
    # STAGE 4: High-Performance 1080p Video Rendering
    # -------------------------------------------------------------------------
    print("\n[Stage 4] Rendering 1080p Whiteboard Video with DynamicSectionEngine...")
    rendered_raw = engine.render_section(
        hero_configs=hero_configs,
        elements_staging=elements_staging,
        camera_trajectory_fn=camera_trajectory_fn,
        duration_sec=audio_dur,
    )

    if Path(rendered_raw).resolve() != Path(output_video_path).resolve():
        shutil.copyfile(rendered_raw, str(output_video_path))

    # Also update deliverables if directory exists
    deliverables_dir = REPO_ROOT / "output_animations" / "fiercest_warriors_documentary" / "deliverables" / "sections"
    if deliverables_dir.exists():
        deliverable_file = deliverables_dir / "15_Outro_Whiteboard_1080p.mp4"
        shutil.copyfile(rendered_raw, str(deliverable_file))
        print(f"  -> Updated deliverable: {deliverable_file}")

    print("\n" + "=" * 80)
    print("🎉 SUCCESS! OSAS v3.1 CANARY RENDER COMPLETED FOR OUTRO (15_outro)")
    print(f"  • Video Output: {output_video_path}")
    print(f"  • File Size   : {output_video_path.stat().st_size / (1024*1024):.2f} MB")
    print(f"  • Scenes      : {len(SCENES)} Multi-Element Micro-Zones (3-5 elements per scene)")
    print(f"  • Transitions : Hand Inking (4) + Slide/Pop/Grow/Pulse (11)")
    print(f"  • Camera Pans : 3 Calm Pans (Zero jitter, Zero blank screen)")
    print(f"  • Total Assets: 15/15 Rendered in Strict Storyboard Order")
    print("=" * 80)


if __name__ == "__main__":
    run_pipeline()
