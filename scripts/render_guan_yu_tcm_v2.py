"""Deterministic Whiteboard Video Renderer for Guan Yu (07_guan_yu) using TCM-DS v2.0 Execution Plan.

Executes:
1. Ingestion of Contract 3 (final_render_plan.json) and verified visual crops.
2. World space staging layout (zero collisions, clean focal zones).
3. Hermite/Smootherstep camera trajectory synchronized with speech anchors.
4. Active hand-inking cache generation for characters and scenes.
5. SFX alignment (marker drawing, completion pops, camera whooshes) and audio mixing.
6. Hardware-accelerated 1080p 30fps video rendering via DynamicSectionEngine.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
import wave
from pathlib import Path
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
    FPS,
    CAM_ZOOM,
)
from core.contracts.render_plan import FinalRenderPlan


def render_guan_yu():
    sec_dir = REPO_ROOT / "sections" / "fiercest_warriors_documentary" / "07_guan_yu"
    crops_dir = sec_dir / "scratch" / "tcm_v2_run" / "crops"
    plan_path = sec_dir / "scratch" / "tcm_v2_run" / "final_render_plan.json"
    voice_path = sec_dir / "voice" / "section.wav"
    output_video_path = sec_dir / "final_whiteboard_tcm_v2_1080p.mp4"

    print("=" * 70)
    print("STARTING DETERMINISTIC WHITEBOARD RENDERING: GUAN YU (07_guan_yu)")
    print("=" * 70)

    # 1. Load Execution Plan (Contract 3)
    with open(plan_path, "r", encoding="utf-8") as f:
        plan_dict = json.load(f)
    plan = FinalRenderPlan.model_validate(plan_dict)

    beats = plan.execution_tracks.visual_beats
    print(f"Loaded Contract 3: {len(beats)} visual beats.")

    # 2. Get audio duration
    with wave.open(str(voice_path), "rb") as wf:
        audio_dur = wf.getnframes() / float(wf.getframerate())
    print(f"Audio file duration: {audio_dur:.2f}s")

    # 3. Build Staging Geometry in World Coordinates
    # Uses the proven DynamicLayoutPlanner approach: scale crops 2x-3.2x so they
    # fill 35%-45% of the visible canvas height, with cam_zoom=0.68 and fixed_y=800.
    elements_staging = []
    hero_configs = []
    zone_centers = []

    RENDER_CAM_ZOOM = 0.68  # Match proven production zoom
    cam_y = 800.0           # Match proven fixed_y for consistent horizontal panning
    visible_w = WIDTH / RENDER_CAM_ZOOM    # ~2823.5 px visible in world space
    zone_spacing = visible_w + 400.0       # Clean separation: full viewport + 400px gap

    # Adaptive scale: 3.2x for solo element, 2.6x for pairs, 2.0x for dense zones
    # Single-element-per-zone in the TCM v2 pipeline, so use 3.0x base
    BASE_SCALE = 3.0
    MAX_WORLD_H = 900.0     # Max height in world-space to prevent overflow

    for i, b in enumerate(beats):
        aid = b.visual_id
        crop_path = crops_dir / f"{aid}.png"
        if not crop_path.exists():
            print(f"Warning: Crop {crop_path} does not exist!")
            continue

        crop_img = cv2.imread(str(crop_path), cv2.IMREAD_UNCHANGED)
        ch, cw = crop_img.shape[:2]

        # Calculate world position centered in its zone
        zone_cam_x = 1200.0 + i * zone_spacing
        zone_centers.append((b.timing.ink_start_s, b.timing.ink_end_s, b.timing.hold_until_s, zone_cam_x))

        # Scale UP to fill the viewport (matching DynamicLayoutPlanner approach)
        elem_scale = BASE_SCALE
        scaled_w = int(cw * elem_scale)
        scaled_h = int(ch * elem_scale)

        # Clamp: if world-space height exceeds maximum, scale down proportionally
        if scaled_h > MAX_WORLD_H:
            ratio = MAX_WORLD_H / float(scaled_h)
            scaled_w = int(scaled_w * ratio)
            scaled_h = int(scaled_h * ratio)

        world_x = zone_cam_x - scaled_w // 2
        world_y = cam_y - scaled_h // 2

        # Inking animation duration and start from Contract 3
        t_start = b.timing.ink_start_s
        t_dur = b.timing.draw_duration_s

        elements_staging.append({
            "id": f"{aid}_{i}",
            "asset": aid,
            "t_start": t_start,
            "t_dur": t_dur,
            "type": "outside_in_pen",
            "pos": (world_x, world_y),
            "size": (scaled_w, scaled_h),
            "depth": 5,
            "fade_out_at": None,
        })
        hero_configs.append((aid, t_start, t_dur))
        print(f"  Element {i}: {aid} raw=({cw}x{ch}) -> world=({scaled_w}x{scaled_h}) @ ({world_x:.0f},{world_y:.0f})")

    # 4. Construct Hermite / Smootherstep Camera Trajectory Function
    camera_pans = []
    for i in range(len(zone_centers) - 1):
        curr_ink_end = zone_centers[i][1]
        next_ink_start = zone_centers[i + 1][0]
        # Pan starts after current ink ends, completes before next ink starts
        pan_dur = min(1.2, max(0.6, next_ink_start - curr_ink_end - 0.1))
        pan_start = max(curr_ink_end, next_ink_start - pan_dur)
        pan_end = pan_start + pan_dur
        from_x = zone_centers[i][3]
        to_x = zone_centers[i + 1][3]
        camera_pans.append((pan_start, pan_end, from_x, to_x))

    def camera_trajectory_fn(time_s: float):
        if not zone_centers:
            return (1200.0, cam_y, RENDER_CAM_ZOOM)

        # Before first pan
        if time_s <= camera_pans[0][0]:
            return (zone_centers[0][3], cam_y, RENDER_CAM_ZOOM)

        # Check in pans
        for p_start, p_end, x1, x2 in camera_pans:
            if p_start <= time_s <= p_end:
                prog = (time_s - p_start) / max(0.001, (p_end - p_start))
                eased = smootherstep(prog)
                cur_x = x1 + eased * (x2 - x1)
                return (cur_x, cam_y, RENDER_CAM_ZOOM)
            elif time_s < p_start:
                return (x1, cam_y, RENDER_CAM_ZOOM)

        # After last pan
        return (zone_centers[-1][3], cam_y, RENDER_CAM_ZOOM)

    # 5. Audio SFX Alignment & Mixing
    print("\n[Audio Mix] Generating synchronized SFX cues & mixing master audio...")
    engine = DynamicSectionEngine(str(sec_dir))
    # Point engine assets_dir directly to our clean crops
    engine.assets_dir = str(crops_dir)

    pan_times = [p[0] for p in camera_pans]
    sfx_cues = engine.generate_sfx_from_staging(elements_staging, camera_pans=pan_times)
    master_audio = engine.mix_master_audio(str(voice_path), sfx_cues, target_duration_s=audio_dur)
    print(f"Master audio generated: {master_audio}")

    # 6. Render Section Video
    print(f"\n[Rendering] Rendering 1080p whiteboard video ({audio_dur:.2f}s)...")
    rendered_raw = engine.render_section(
        hero_configs=hero_configs,
        elements_staging=elements_staging,
        camera_trajectory_fn=camera_trajectory_fn,
        duration_sec=audio_dur,
    )

    # Copy to designated final output
    shutil.copyfile(rendered_raw, str(output_video_path))
    print(f"\nSUCCESS! Rendered final video to: {output_video_path}")
    print(f"File size: {output_video_path.stat().st_size / (1024*1024):.2f} MB")


if __name__ == "__main__":
    render_guan_yu()
