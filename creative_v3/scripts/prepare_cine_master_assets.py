"""
Step 1 of 24s Cinematic Master Production:
1. Concatenate the 6 master stereo stems (4.00s each = 24.00s @ 44.1kHz) from
   creative_v3/studio_pro_sfx_and_audio_stems_v3/07_FULL_SECTION_MASTER_STEMS/
   into a single seamless master_audio_24s.wav.
2. Export the exact curated character motion clips from
   creative_v3/Character_Motion_Project_v4/Character_Motion_Final.anicraft
   at 2x resolution (1280x1280 RGBA) using anicraft-cli render-seq,
   assemble a contiguous 600-frame sequence (25 fps = 24.00s) matching every beat,
   and run PhotoCraft (defringe + smartSharpen) on all 600 frames for razor-sharp
   compositing on dark cinematic backdrops.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[2]
ANI_FILE = ROOT / "creative_v3" / "Character_Motion_Project_v4" / "Character_Motion_Final.anicraft"
ANI_CLI = ROOT / "craftApp" / "anicraft" / "target" / "release" / "anicraft-cli.exe"
PC_CLI = ROOT / "craftApp" / "photocraft" / "target" / "release" / "photocraft-cli.exe"
STEMS_DIR = ROOT / "creative_v3" / "studio_pro_sfx_and_audio_stems_v3" / "07_FULL_SECTION_MASTER_STEMS"

WORK_DIR = ROOT / "creative_v3" / "renders" / "cine_master_24s"
RAW_EXPORT_DIR = WORK_DIR / "_ani_raw"
SEQ_RAW_DIR = WORK_DIR / "_seq_raw"
SEQ_HD_DIR = WORK_DIR / "char_seq_hd"

# Exact global frame slices in Character_Motion_Final.anicraft (total = 600 frames = 24.00s @ 25fps)
# Each section (4.00s) = 100 frames, ending cleanly on neutral frames for zero-pop transitions!
CLIP_PLAN: List[Tuple[str, int, int, List[int] | None]] = [
    # SEC 01: HOOK (0.00s - 4.00s, frames 0..99)
    ("01_hook_shock_emo07", 685, 720, None),                       # 36f (1.44s)
    ("01_hook_point02", 37, 72, None),                             # 36f (1.44s)
    ("01_hook_shrug04", 145, 180, list(range(145, 169)) + list(range(177, 181))),  # 28f (1.12s) -> 100f

    # SEC 02: IMMERSION Evidence Board (4.00s - 8.00s, frames 100..199)
    ("02_ev_think05", 109, 144, None),                             # 36f
    ("02_ev_explain00", 73, 108, None),                            # 36f
    ("02_ev_confident_emo03", 541, 576, list(range(541, 565)) + list(range(573, 577))),  # 28f -> 100f

    # SEC 03: MECHANISM Neuro X-Ray (8.00s - 12.00s, frames 200..299)
    ("03_neuro_turnaround", 1297, 1360, None),                     # 64f (2.56s full 360 turnaround)
    ("03_neuro_inspired_emo20", 1153, 1188, None),                 # 36f (1.44s) -> 100f

    # SEC 04: ESCALATION Dark Tension (12.00s - 16.00s, frames 300..399)
    ("04_tens_worried_emo09", 757, 792, None),                     # 36f
    ("04_tens_angry_emo11", 829, 864, None),                       # 36f
    ("04_tens_panic_emo23", 1261, 1296, list(range(1261, 1285)) + list(range(1293, 1297))),  # 28f -> 100f

    # SEC 05: CLIMAX Paradigm Shift (16.00s - 20.00s, frames 400..499)
    ("05_climax_jump01", 325, 360, None),                          # 36f
    ("05_climax_celebrate07", 361, 396, None),                     # 36f
    ("05_climax_excited_emo01", 469, 504, list(range(469, 493)) + list(range(501, 505))),  # 28f -> 100f

    # SEC 06: RESOLUTION Seamless Loop (20.00s - 24.00s, frames 500..599)
    ("06_res_yes00", 181, 216, None),                              # 36f
    ("06_res_explain00", 73, 108, None),                           # 36f
    ("06_res_wave00", 1, 36, list(range(1, 25)) + list(range(33, 37))),  # 28f -> 100f
]


def build_master_audio() -> Path:
    stems = [
        STEMS_DIR / "MASTER_STEM_01_HOOK_Cold_Open.wav",
        STEMS_DIR / "MASTER_STEM_02_IMMERSION_Evidence_Board.wav",
        STEMS_DIR / "MASTER_STEM_03_MECHANISM_Neuro_XRay.wav",
        STEMS_DIR / "MASTER_STEM_04_ESCALATION_Dark_Thriller.wav",
        STEMS_DIR / "MASTER_STEM_05_CLIMAX_Paradigm_Shatter.wav",
        STEMS_DIR / "MASTER_STEM_06_RESOLUTION_Seamless_Loop.wav",
    ]
    for s in stems:
        if not s.exists():
            raise FileNotFoundError(f"Missing audio stem: {s}")

    out_wav = WORK_DIR / "master_audio_24s.wav"
    cmd_args = ["ffmpeg", "-y"]
    for s in stems:
        cmd_args += ["-i", str(s)]
    filter_str = "".join(f"[{i}:0]" for i in range(len(stems))) + f"concat=n={len(stems)}:v=0:a=1[outa]"
    cmd_args += ["-filter_complex", filter_str, "-map", "[outa]", "-ar", "44100", "-ac", "2", str(out_wav)]
    subprocess.run(cmd_args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Merged 6 master stems -> {out_wav}")
    return out_wav


def export_and_assemble_sequence() -> int:
    for d in (RAW_EXPORT_DIR, SEQ_RAW_DIR, SEQ_HD_DIR):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    # Deduplicate overlapping export ranges (e.g. 03 explain 00 used twice)
    exported_ranges: dict[Tuple[int, int], Path] = {}
    out_idx = 1

    for clip_name, f_start, f_end, pick_list in CLIP_PLAN:
        key = (f_start, f_end)
        if key not in exported_ranges:
            clip_dir = RAW_EXPORT_DIR / clip_name
            clip_dir.mkdir(parents=True, exist_ok=True)
            res = subprocess.run(
                [
                    str(ANI_CLI), "render-seq", str(ANI_FILE),
                    "--out-dir", str(clip_dir),
                    "--from", str(f_start), "--to", str(f_end), "--scale", "2",
                ],
                capture_output=True, text=True, check=True,
            )
            exported_ranges[key] = clip_dir
            print(f"Exported {clip_name:26s} ({f_start}..{f_end}) -> {clip_dir.name}")
        else:
            clip_dir = exported_ranges[key]

        frames_to_copy = pick_list if pick_list is not None else list(range(f_start, f_end + 1))
        for fnum in frames_to_copy:
            src_frame = clip_dir / f"frame_{fnum:05d}.png"
            if not src_frame.exists():
                raise FileNotFoundError(f"Expected exported frame missing: {src_frame}")
            dst_frame = SEQ_RAW_DIR / f"frame_{out_idx:05d}.png"
            shutil.copy2(src_frame, dst_frame)
            out_idx += 1

    total = out_idx - 1
    print(f"Assembled contiguous sequence: {total} frames ({total / 25.0:.2f}s @ 25fps)")

    # Run PhotoCraft batch clean-edge & sharpen across all 600 frames
    actions_path = WORK_DIR / "_pc_seq_actions.json"
    actions = [
        {"command": "layer.matting.defringe", "params": {"width": 1}},
        {"command": "filter.sharpen.smartSharpen", "params": {"amount": 65, "radius": 0.7, "reduceNoise": 10}},
    ]
    actions_path.write_text(json.dumps(actions, indent=2), encoding="utf-8")
    subprocess.run(
        [str(PC_CLI), "batch", "--actions", str(actions_path), "--in", str(SEQ_RAW_DIR), "--out", str(SEQ_HD_DIR), "--format", "png"],
        check=True,
    )
    actions_path.unlink(missing_ok=True)
    # Clean up temporary raw exports once HD sequence is ready
    shutil.rmtree(RAW_EXPORT_DIR, ignore_errors=True)
    shutil.rmtree(SEQ_RAW_DIR, ignore_errors=True)
    # Remove any leftover test folders from earlier check
    for old_name in ("_test_export", "_test_cmds.json", "_test_seq.ecproj", "_test_seq.mp4"):
        p = WORK_DIR / old_name
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()

    print(f"PhotoCraft HD sequence ready -> {SEQ_HD_DIR}")
    return total


def main() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    build_master_audio()
    total = export_and_assemble_sequence()
    assert total == 600, f"Expected 600 frames, got {total}"


if __name__ == "__main__":
    main()
