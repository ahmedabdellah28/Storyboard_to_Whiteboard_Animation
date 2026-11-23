"""Cinematic Production Renderer for Guan Yu (07_guan_yu) using TCM-DS Deterministic Plan & Micro-Zoning Layout.

Integrates:
1. Clean organic crops extracted via TCM-DS (cand_001, cand_019, cand_020, etc.).
2. High-impact micro-zoning (6 zones, prominent scaling 2.35x-3.2x, CAM_ZOOM=0.68, FIXED_Y=800.0).
3. Arabic handwriting title banner ("غوان يو").
4. Authentic solid outside-in inking + synchronized SFX (marker, pops, whooshes).
5. Cinematic horizontal camera pans matching the exact presentation style of production sections.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
import cv2

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from production_engine.universal_section_pipeline import UniversalSectionPipeline


def run_cinematic_production():
    sec_dir = REPO_ROOT / "sections" / "fiercest_warriors_documentary" / "07_guan_yu"
    assets_dir = sec_dir / "assets"
    crops_dir = sec_dir / "scratch" / "tcm_v2_run" / "crops"
    meta_path = assets_dir / "metadata.json"

    print("=" * 70)
    print("PREPARING CINEMATIC PRODUCTION FOR GUAN YU (07_guan_yu)")
    print("=" * 70)

    # 1. Copy verified clean crops to assets directory and measure dimensions
    used_cands = [
        ("cand_001", "غوان يو محارب صيني عملاق", "hero"),
        ("cand_019", "سلاحه الهلالي الثقيل", "supporting"),
        ("cand_020", "اندفع بحصانه وسط جيش العدو", "supporting"),
        ("cand_004", "قائد بارز وقتله أمام جنوده", "hero"),
        ("cand_005", "حليفه ليو بي", "supporting"),
        ("cand_007", "ثقته الزائدة وسقوطه", "supporting"),
        ("cand_010", "قطع إمداداته وقواعده", "supporting"),
        ("cand_011", "جيشه انهار", "supporting"),
        ("cand_012", "أسر هو وولده", "hero"),
        ("cand_013", "ثم أعدما بالسيف", "hero"),
        ("cand_015", "الرأس أرسل إلى تساو تساو", "hero"),
        ("cand_017", "معبد إله الحرب ورمز الوفاء", "hero"),
    ]

    # Load or initialize metadata
    metadata = {}
    if (assets_dir / "r0_00_title_banner.png").exists():
        banner_img = cv2.imread(str(assets_dir / "r0_00_title_banner.png"))
        bh, bw = banner_img.shape[:2]
        metadata["r0_00_title_banner"] = {
            "file": "r0_00_title_banner.png",
            "desc": "غوان يو",
            "orig_size": [bw, bh],
            "role": "hero",
        }

    for cid, desc, role in used_cands:
        src = crops_dir / f"{cid}.png"
        dst = assets_dir / f"{cid}.png"
        if src.exists():
            shutil.copyfile(src, dst)
            img = cv2.imread(str(src))
            ih, iw = img.shape[:2]
            metadata[cid] = {
                "file": f"{cid}.png",
                "desc": desc,
                "orig_size": [iw, ih],
                "role": role,
            }
            print(f"  ✓ Prepared asset: {cid}.png ({iw}x{ih})")

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Saved updated assets metadata to: {meta_path}")

    # 2. Build high-impact micro-zoned custom manifest from TCM-DS plan
    custom_manifest = [
        # Zone 01: Introduction - Title Banner + Guan Yu + Crescent Blade + Warhorse
        ("r0_00_title_banner", 0.00, 2.20, "غوان يو", "zone_01", "outside_in_pen", 5),
        ("cand_001", 0.15, 3.24, "غوان يو محارب صيني عملاق", "zone_01", "outside_in_pen", 5),
        ("cand_019", 3.94, 1.80, "سلاحه الهلالي الثقيل", "zone_01", "outside_in_pen", 5),
        ("cand_020", 6.66, 1.94, "اندفع بحصانه", "zone_01", "outside_in_pen", 5),

        # Zone 02: Battles - Single Combat + Sworn Brothers
        ("cand_004", 8.75, 3.36, "قائد بارز وقتله أمام جنوده", "zone_02", "outside_in_pen", 5),
        ("cand_005", 13.58, 1.40, "حليفه ليو بي", "zone_02", "outside_in_pen", 5),

        # Zone 03: Fall & Collapse - Overconfidence + Cut Supplies + Army Collapse
        ("cand_007", 18.54, 1.41, "ثقته الزائدة", "zone_03", "outside_in_pen", 5),
        ("cand_010", 23.92, 1.37, "قطع إمداداته من الخلف", "zone_03", "outside_in_pen", 5),
        ("cand_011", 25.44, 1.26, "جيشه انهار", "zone_03", "outside_in_pen", 5),

        # Zone 04: Capture & Execution - Kneeling With Son + Execution Scene
        ("cand_012", 26.85, 2.47, "وأُسر هو وولده", "zone_04", "outside_in_pen", 5),
        ("cand_013", 29.47, 2.53, "ثم أُعدما", "zone_04", "outside_in_pen", 5),

        # Zone 05: The Head & Cao Cao - Cao Cao Mourning
        ("cand_015", 32.15, 3.15, "الرأس أُرسل إلى تساو تساو", "zone_05", "outside_in_pen", 5),

        # Zone 06: Legacy - Temple Deification / God of War
        ("cand_017", 37.14, 3.44, "رمز للقوة والوفاء كإله للحرب", "zone_06", "outside_in_pen", 5),
    ]

    print("\n--- 3. Running UniversalSectionPipeline with Micro-Zoning Layout ---")
    pipeline = UniversalSectionPipeline(
        str(sec_dir),
        title="غوان يو",
        project_id="fiercest_warriors_documentary",
    )

    # Step 3: Layout & Sync with DynamicLayoutPlanner
    layout_file = pipeline.step_layout_and_sync(custom_manifest=custom_manifest)
    print(f"Layout created: {layout_file}")

    # Step 5: Audio Mix
    audio_file = pipeline.step_audio_mix()
    print(f"Master Audio Mixed: {audio_file}")

    # Step 6: Video Render with NVENC
    video_file = pipeline.step_render()
    print(f"Rendered Video: {video_file}")

    # Step 7: Publish to Deliverables
    deliv_file = pipeline.step_publish()
    print(f"Published to Deliverables: {deliv_file}")

    print("\nSUCCESS: Guan Yu cinematic whiteboard animation completed!")


if __name__ == "__main__":
    run_cinematic_production()
