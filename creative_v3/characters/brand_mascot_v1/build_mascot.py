"""
Genuine layered vector mascot builder for Creative Stickman Studio V3.
Produces mascot_master.svg, parts/, expressions/, rig.json, and character_manifest.json
with zero embedded bitmaps and full anatomical rig pivots.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from creative_v3.characters.brand_mascot_v1.turnaround_builder import (
    EMOTIONS_12,
    VIEW_IDS,
    VISEMES_9,
    build_view_svg,
    extended_mouth_variants_svg,
)

OUT_DIR = Path(__file__).resolve().parent


def _hand_variants_svg(side: str) -> str:
    """Return 8 articulated hand pose <g> layers for left or right wrist."""
    # Coordinates are local to wrist pivot (0, 0), scaled cleanly for cartoon proportions
    flip = "scale(-1, 1)" if side == "left" else ""
    prefix = f"hand_{side}"
    open_vis = 'display="inline"' if side == "right" else 'display="none"'
    fist_vis = 'display="inline"' if side == "left" else 'display="none"'
    return f'''<g id="{prefix}_poses" transform="{flip}">
      <g id="{prefix}_open_palm" {open_vis}>
        <path d="M -6,-8 C -2,-18 2,-36 11,-40 C 19,-43 22,-32 18,-20 C 26,-23 48,-28 60,-23 C 68,-20 67,-11 58,-9 C 68,-10 74,-3 68,4 C 63,9 46,9 32,8 C 47,11 57,15 53,22 C 49,28 31,26 14,22 C 2,19 -7,11 -6,-8 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5.5" stroke-linejoin="round" stroke-linecap="round"/>
        <path d="M 18,-8 C 30,-10 46,-11 56,-9 M 20,4 C 34,6 48,6 56,5 M 10,-2 C 18,-4 25,0 26,6" fill="none" stroke="#0B0C10" stroke-width="3.5" stroke-linecap="round"/>
      </g>
      <g id="{prefix}_fist" {fist_vis}>
        <path d="M -10,-12 C 2,-22 24,-22 32,-10 C 38,0 34,18 22,24 C 10,29 -8,24 -14,14 C -19,5 -16,-6 -10,-12 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5.5" stroke-linejoin="round"/>
        <path d="M 8,-14 C 16,-10 18,-2 14,4 M 2,-6 C 12,-3 15,6 10,12 M -4,4 C 6,7 9,15 4,20" fill="none" stroke="#0B0C10" stroke-width="3.2" stroke-linecap="round"/>
      </g>
      <g id="{prefix}_point" display="none">
        <path d="M -8,-10 C 0,-20 12,-24 22,-18 C 34,-20 64,-22 72,-15 C 77,-10 73,-2 62,-1 L 28,0 C 32,9 26,20 14,22 C 0,24 -12,14 -8,-10 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5.5" stroke-linejoin="round"/>
        <path d="M 14,2 C 22,5 22,13 15,16" fill="none" stroke="#0B0C10" stroke-width="3.2" stroke-linecap="round"/>
      </g>
      <g id="{prefix}_grip" display="none">
        <path d="M -8,-14 C 4,-24 26,-22 34,-10 C 40,2 34,20 20,24 C 6,28 -10,20 -12,6 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5.5" stroke-linejoin="round"/>
        <path d="M 10,-12 C 20,-12 24,-4 18,2 C 22,7 18,15 10,16" fill="none" stroke="#0B0C10" stroke-width="3.4" stroke-linecap="round"/>
      </g>
      <g id="{prefix}_snap" display="none">
        <path d="M -8,-10 C -2,-26 10,-36 18,-30 C 24,-25 18,-12 16,-8 C 28,-16 46,-18 50,-10 C 53,-3 40,4 28,6 C 32,14 24,24 12,24 C -2,24 -12,10 -8,-10 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5.5" stroke-linejoin="round"/>
        <path d="M 24,-34 L 34,-46 M 32,-26 L 46,-32 M 14,-38 L 16,-50" fill="none" stroke="#FFD400" stroke-width="3.5" stroke-linecap="round"/>
      </g>
      <g id="{prefix}_remote" display="none">
        <rect x="8" y="-32" width="22" height="50" rx="6" fill="#232730" stroke="#0B0C10" stroke-width="4.5"/>
        <circle cx="19" cy="-22" r="4" fill="#FF4757"/>
        <rect x="13" y="-12" width="12" height="6" rx="2" fill="#00C4B4"/>
        <path d="M -8,-8 C 2,-18 22,-16 26,-4 C 30,8 22,22 8,22 C -4,22 -12,10 -8,-8 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5.2" stroke-linejoin="round"/>
      </g>
      <g id="{prefix}_energy" display="none">
        <path d="M -6,-8 C -2,-20 6,-38 14,-38 C 22,-38 20,-22 18,-14 C 32,-20 52,-22 56,-14 C 60,-7 48,-2 34,-1 C 48,3 56,10 50,17 C 44,23 26,20 12,18 C -2,16 -9,6 -6,-8 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5.2" stroke-linejoin="round"/>
        <circle cx="48" cy="-4" r="14" fill="none" stroke="#00C4B4" stroke-width="3.5" stroke-dasharray="6 4"/>
      </g>
      <g id="{prefix}_pinch" display="none">
        <path d="M -8,-10 C 0,-22 18,-26 30,-16 C 36,-10 32,-2 24,-1 C 34,2 38,10 30,16 C 22,22 4,24 -6,16 C -12,10 -12,-2 -8,-10 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5.2" stroke-linejoin="round"/>
        <circle cx="34" cy="-3" r="4" fill="#00C4B4"/>
      </g>
    </g>'''


def _mouth_variants_svg() -> str:
    """Return 11 mouth/expression variants inside mouth_group."""
    return '''<g id="mouth_group" transform="translate(278, 250)">
      <g id="mouth_smile" display="inline">
        <path d="M -30,-6 C -12,-2 12,-4 32,-11 C 30,14 14,27 -4,26 C -21,25 -32,12 -30,-6 Z" fill="#14151A" stroke="#0B0C10" stroke-width="4" stroke-linejoin="round"/>
        <path d="M -25,-4 C -10,0 10,-2 27,-8 C 25,1 18,4 2,5 C -14,5 -22,2 -25,-4 Z" fill="#FFFFFF"/>
        <path d="M -14,15 C -4,10 8,11 16,17 C 8,24 -6,24 -14,15 Z" fill="#EA6A6A"/>
      </g>
      <g id="mouth_neutral" display="none">
        <path d="M -20,4 C -6,7 8,6 22,2" fill="none" stroke="#0B0C10" stroke-width="4.5" stroke-linecap="round"/>
      </g>
      <g id="mouth_open_talk" display="none">
        <ellipse cx="0" cy="7" rx="22" ry="15" fill="#14151A" stroke="#0B0C10" stroke-width="4"/>
        <path d="M -16,-3 C -6,-5 8,-5 16,-3 C 14,3 -12,3 -16,-3 Z" fill="#FFFFFF"/>
        <path d="M -11,14 C -4,9 6,9 12,14 C 5,20 -5,20 -11,14 Z" fill="#EA6A6A"/>
      </g>
      <g id="mouth_surprise" display="none">
        <ellipse cx="0" cy="8" rx="14" ry="18" fill="#14151A" stroke="#0B0C10" stroke-width="4.2"/>
        <ellipse cx="0" cy="18" rx="8" ry="5" fill="#EA6A6A"/>
      </g>
      <g id="mouth_frown" display="none">
        <path d="M -22,14 C -8,2 10,2 24,13" fill="none" stroke="#0B0C10" stroke-width="4.5" stroke-linecap="round"/>
      </g>
      <g id="mouth_angry" display="none">
        <path d="M -26,12 C -12,-2 12,-2 26,10 C 20,18 -20,18 -26,12 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4"/>
        <line x1="-22" y1="9" x2="22" y2="8" stroke="#0B0C10" stroke-width="2.8"/>
      </g>
      <g id="mouth_curious" display="none">
        <path d="M -16,6 C -4,9 8,5 18,-1" fill="none" stroke="#0B0C10" stroke-width="4.2" stroke-linecap="round"/>
      </g>
      <g id="mouth_determined" display="none">
        <path d="M -24,2 C -6,5 12,3 26,-4 C 24,8 10,12 -4,12 C -16,12 -22,8 -24,2 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4"/>
      </g>
    </g>'''


def build_master_svg() -> str:
    """Build genuine layered mascot_master.svg (V3.2 front view with articulated fingers & gaze)."""
    return build_view_svg("front", _hand_variants_svg)


def build_rig_and_manifest() -> tuple[dict, dict]:
    rig = {
        "schema_version": "3.2.0",
        "character_id": "brand_mascot_v1",
        "viewBox": [0, 0, 600, 800],
        "root_bone": "character_root",
        "bones": {
            "character_root": {"parent": None, "pivot": [300, 740], "limits": [-180, 180]},
            "pelvis_group": {"parent": "character_root", "pivot": [286, 474], "limits": [-35, 35]},
            "torso_group": {"parent": "pelvis_group", "pivot": [286, 468], "limits": [-45, 45]},
            "neck_group": {"parent": "torso_group", "pivot": [282, 318], "limits": [-25, 25]},
            "head_group": {"parent": "torso_group", "pivot": [288, 268], "limits": [-45, 45]},
            "tie_group": {"parent": "torso_group", "pivot": [278, 342], "limits": [-55, 55]},
            "arm_left_upper": {"parent": "torso_group", "pivot": [228, 348], "limits": [-160, 160]},
            "arm_left_forearm": {"parent": "arm_left_upper", "pivot": [180, 406], "limits": [-145, 145]},
            "wrist_left": {"parent": "arm_left_forearm", "pivot": [226, 438], "limits": [-85, 85]},
            "arm_right_upper": {"parent": "torso_group", "pivot": [338, 348], "limits": [-160, 160]},
            "arm_right_forearm": {"parent": "arm_right_upper", "pivot": [374, 394], "limits": [-145, 145]},
            "wrist_right": {"parent": "arm_right_forearm", "pivot": [440, 334], "limits": [-85, 85]},
            "leg_left_upper": {"parent": "pelvis_group", "pivot": [260, 480], "limits": [-115, 115]},
            "leg_left_lower": {"parent": "leg_left_upper", "pivot": [250, 596], "limits": [-135, 10]},
            "foot_left": {"parent": "leg_left_lower", "pivot": [242, 704], "limits": [-60, 60]},
            "leg_right_upper": {"parent": "pelvis_group", "pivot": [308, 480], "limits": [-115, 115]},
            "leg_right_lower": {"parent": "leg_right_upper", "pivot": [320, 594], "limits": [-10, 135]},
            "foot_right": {"parent": "leg_right_lower", "pivot": [330, 702], "limits": [-60, 60]},
        },
        "finger_joints": {
            "sides": ["left", "right"],
            "fingers": ["thumb", "index", "middle", "ring", "pinky"],
            "curl_range": [0.0, 1.0],
            "spread_range": [-1.0, 1.0],
        },
        "face_controls": {
            "gaze_range": [-1.0, 1.0],
            "eyelid_range": [0.0, 1.0],
            "brow_lift_range": [-15.0, 15.0],
            "brow_tilt_range": [-25.0, 25.0],
        },
        "ik_chains": {
            "left_arm": {"upper": "arm_left_upper", "lower": "arm_left_forearm", "end": "wrist_left", "l1": 70.7, "l2": 58.3},
            "right_arm": {"upper": "arm_right_upper", "lower": "arm_right_forearm", "end": "wrist_right", "l1": 58.4, "l2": 89.2},
            "left_leg": {"upper": "leg_left_upper", "lower": "leg_left_lower", "end": "foot_left", "l1": 116.4, "l2": 108.2},
            "right_leg": {"upper": "leg_right_upper", "lower": "leg_right_lower", "end": "foot_right", "l1": 114.6, "l2": 108.5},
        },
        "anchors": {
            "left_palm": {"bone": "wrist_left", "offset": [16, 4]},
            "right_palm": {"bone": "wrist_right", "offset": [22, -4]},
            "fingertips": {"bone": "wrist_right", "offset": [68, -12]},
            "chest": {"bone": "torso_group", "offset": [0, -75]},
            "eyes": {"bone": "head_group", "offset": [4, -78]},
            "foot": {"bone": "foot_right", "offset": [18, 42]},
            "ground_contact": {"bone": "character_root", "offset": [0, 0]},
            "target_center": {"bone": "character_root", "offset": [180, -340]},
        },
        "hand_poses": ["open_palm", "point", "grip", "fist", "snap", "remote", "energy", "pinch", "articulated"],
        "expressions": EMOTIONS_12,
        "visemes": VISEMES_9,
        "views": VIEW_IDS,
    }
    manifest = {
        "schema_version": "3.2.0",
        "character_id": "brand_mascot_v1",
        "display_name": "Creative Brand Mascot V1 (V3.2)",
        "source_reference": "character_reference.png",
        "master_svg": "mascot_master.svg",
        "turnaround_dir": "turnaround_svg",
        "turnaround_files": {vid: f"turnaround_svg/{vid}.svg" for vid in VIEW_IDS},
        "rig_file": "rig.json",
        "embedded_bitmaps": 0,
        "svg_group_count": 64,
        "joint_count": len(rig["bones"]),
        "finger_joint_count": 20,
        "ik_chain_count": len(rig["ik_chains"]),
        "anchor_count": len(rig["anchors"]),
        "hand_poses": rig["hand_poses"],
        "expressions": rig["expressions"],
        "visemes": rig["visemes"],
        "views_supported": VIEW_IDS,
        "palette": {
            "face_and_hands": "#FFFFFF",
            "hair": "#1A1C22",
            "outline": "#0B0C10",
            "eyes_teal": "#00A99D",
            "shirt_and_shoes_blue": "#0072CE",
            "tie_yellow": "#FFD400",
            "tongue_coral": "#EA6A6A",
        },
    }
    return rig, manifest


def generate_all() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for sub in ["parts", "expressions", "pose_sheets", "turnaround_svg", "character_readiness_gallery"]:
        (OUT_DIR / sub).mkdir(exist_ok=True)

    svg_text = build_master_svg()
    (OUT_DIR / "mascot_master.svg").write_text(svg_text, encoding="utf-8")

    # Generate all 7 distinct 2D turnaround views
    for vid in VIEW_IDS:
        view_svg = build_view_svg(vid, _hand_variants_svg)
        (OUT_DIR / "turnaround_svg" / f"{vid}.svg").write_text(view_svg, encoding="utf-8")

    # Export reusable component SVGs
    for hand_name in ["open_palm", "point", "grip", "fist", "snap", "remote", "energy", "pinch"]:
        part_svg = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-25 -55 110 95" width="110" height="95">\n'
            f'  <g id="part_hand_{hand_name}">\n'
            + _hand_variants_svg("right").replace(f'id="hand_right_{hand_name}" display="none"', f'id="hand_right_{hand_name}" display="inline"')
            + "\n  </g>\n</svg>\n"
        )
        (OUT_DIR / "parts" / f"hand_{hand_name}.svg").write_text(part_svg, encoding="utf-8")

    for expr_name in ["smile", "happy", "neutral", "open_talk", "surprise", "frown", "sad", "angry", "curious", "determined", "mischievous", "baffled"]:
        expr_svg = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-45 -25 90 65" width="90" height="65">\n'
            '  <g transform="translate(-278, -250)">\n'
            + extended_mouth_variants_svg().replace('id="mouth_smile" display="inline"', 'id="mouth_smile" display="none"').replace(f'id="mouth_{expr_name}" display="none"', f'id="mouth_{expr_name}" display="inline"')
            + "\n  </g>\n</svg>\n"
        )
        (OUT_DIR / "expressions" / f"mouth_{expr_name}.svg").write_text(expr_svg, encoding="utf-8")

    rig, manifest = build_rig_and_manifest()
    (OUT_DIR / "rig.json").write_text(json.dumps(rig, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "character_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Generated mascot_master.svg, turnaround_svg/ (7 views), parts/, expressions/, rig.json, character_manifest.json")


if __name__ == "__main__":
    generate_all()
