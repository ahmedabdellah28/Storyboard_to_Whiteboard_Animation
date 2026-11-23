"""
V3.2 7-Angle 2D Turnaround SVG & Articulated Finger/Face Rig Builder
for Brand Mascot V1 — Updated to match the new 30-pose reference sheet (poses 01-06).
All 7 views are genuine layered 2D SVG (zero bitmaps, no naive horizontal flip
for asymmetrical hair/tie) sharing identical skeletal bone IDs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

_RIG_PARTS_PATH = Path(__file__).resolve().parent / "rig_parts_4k.json"
_RIG_PARTS_CACHE: Dict[str, dict] | None = None


def _get_rig_parts(view_id: str) -> dict:
    global _RIG_PARTS_CACHE
    if _RIG_PARTS_CACHE is None and _RIG_PARTS_PATH.exists():
        _RIG_PARTS_CACHE = json.loads(_RIG_PARTS_PATH.read_text(encoding="utf-8"))
    return (_RIG_PARTS_CACHE or {}).get(view_id, {})


VIEW_IDS = [
    "front",
    "front_34_left",
    "front_34_right",
    "profile_left",
    "profile_right",
    "back_34",
    "back",
]

EMOTIONS_12 = [
    "neutral",
    "smile",
    "happy",
    "open_talk",
    "surprise",
    "frown",
    "sad",
    "angry",
    "curious",
    "determined",
    "mischievous",
    "baffled",
]

VISEMES_9 = [
    "viseme_rest",
    "viseme_A",
    "viseme_E",
    "viseme_I",
    "viseme_O",
    "viseme_U",
    "viseme_MBP",
    "viseme_FV",
    "viseme_LTH",
]


def articulated_hand_svg(side: str) -> str:
    """Articulated 5-finger hand with proximal and distal segments per finger."""
    flip = "scale(-1, 1)" if side == "left" else ""
    prefix = f"hand_{side}_articulated"
    fingers = [
        ("thumb", 4, -14, -48, 16, 13, 8.5),
        ("index", 24, -15, -14, 22, 17, 7.2),
        ("middle", 28, -4, 0, 25, 19, 7.5),
        ("ring", 25, 7, 12, 22, 16, 7.0),
        ("pinky", 20, 16, 24, 17, 13, 6.2),
    ]
    f_xml = []
    for fname, bx, by, base_rot, l1, l2, w in fingers:
        r = w * 0.5
        f_xml.append(
            f'''        <g id="finger_{side}_{fname}_prox" transform="translate({bx}, {by}) rotate({base_rot})" data-base-x="{bx}" data-base-y="{by}" data-base-rot="{base_rot}">
          <rect x="0" y="{-r:.1f}" width="{l1}" height="{w:.1f}" rx="{r:.1f}" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4.2"/>
          <g id="finger_{side}_{fname}_dist" transform="translate({l1 - 2}, 0)" data-base-x="{l1 - 2}" data-base-y="0" data-base-rot="0">
            <rect x="0" y="{-r * 0.9:.1f}" width="{l2}" height="{w * 0.9:.1f}" rx="{r * 0.9:.1f}" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4.0"/>
          </g>
        </g>'''
        )
    return f'''      <g id="{prefix}" display="none" transform="{flip}">
        <path d="M -10,-14 C 2,-22 22,-20 28,-8 C 32,4 26,20 12,22 C -4,24 -14,12 -10,-14 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5.2" stroke-linejoin="round"/>
{chr(10).join(f_xml)}
      </g>'''


def extended_mouth_variants_svg() -> str:
    """Return 12 emotion mouths + 9 lip-sync viseme mouths inside mouth_group."""
    return '''<g id="mouth_group" transform="translate(278, 250)">
      <g id="mouth_smile" display="inline">
        <path d="M -28,-6 C -10,-2 10,-4 30,-10 C 28,13 13,25 -4,24 C -20,23 -30,11 -28,-6 Z" fill="#14151A" stroke="#0B0C10" stroke-width="4" stroke-linejoin="round"/>
        <path d="M -23,-4 C -8,0 8,-2 25,-7 C 23,1 16,4 2,5 C -12,5 -20,2 -23,-4 Z" fill="#FFFFFF"/>
        <path d="M -13,14 C -4,9 7,10 15,16 C 7,22 -5,22 -13,14 Z" fill="#EA6A6A"/>
      </g>
      <g id="mouth_happy" display="none">
        <path d="M -32,-10 C -12,-4 12,-6 34,-13 C 32,17 15,30 -2,29 C -20,28 -33,13 -32,-10 Z" fill="#14151A" stroke="#0B0C10" stroke-width="4" stroke-linejoin="round"/>
        <path d="M -26,-7 C -9,-2 9,-4 28,-9 C 26,2 16,5 2,6 C -15,6 -23,3 -26,-7 Z" fill="#FFFFFF"/>
        <path d="M -15,17 C -4,10 9,11 17,19 C 8,26 -6,26 -15,17 Z" fill="#EA6A6A"/>
      </g>
      <g id="mouth_neutral" display="none">
        <path d="M -18,4 C -5,7 7,6 20,2" fill="none" stroke="#0B0C10" stroke-width="4.5" stroke-linecap="round"/>
      </g>
      <g id="mouth_open_talk" display="none">
        <ellipse cx="0" cy="7" rx="20" ry="14" fill="#14151A" stroke="#0B0C10" stroke-width="4"/>
        <path d="M -14,-3 C -5,-5 7,-5 14,-3 C 12,3 -10,3 -14,-3 Z" fill="#FFFFFF"/>
        <path d="M -10,13 C -4,9 5,9 11,13 C 4,19 -4,19 -10,13 Z" fill="#EA6A6A"/>
      </g>
      <g id="mouth_surprise" display="none">
        <ellipse cx="0" cy="8" rx="13" ry="17" fill="#14151A" stroke="#0B0C10" stroke-width="4.2"/>
        <ellipse cx="0" cy="17" rx="7" ry="5" fill="#EA6A6A"/>
      </g>
      <g id="mouth_frown" display="none">
        <path d="M -20,14 C -7,2 9,2 22,13" fill="none" stroke="#0B0C10" stroke-width="4.5" stroke-linecap="round"/>
      </g>
      <g id="mouth_sad" display="none">
        <path d="M -22,16 C -9,0 11,0 24,15" fill="none" stroke="#0B0C10" stroke-width="4.8" stroke-linecap="round"/>
        <path d="M -9,12 C -2,8 4,8 9,12" fill="none" stroke="#0B0C10" stroke-width="2.6" stroke-linecap="round"/>
      </g>
      <g id="mouth_angry" display="none">
        <path d="M -24,12 C -11,-2 11,-2 24,10 C 18,18 -18,18 -24,12 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4"/>
        <line x1="-20" y1="9" x2="20" y2="8" stroke="#0B0C10" stroke-width="2.8"/>
      </g>
      <g id="mouth_curious" display="none">
        <path d="M -15,6 C -4,9 7,5 17,-1" fill="none" stroke="#0B0C10" stroke-width="4.2" stroke-linecap="round"/>
      </g>
      <g id="mouth_determined" display="none">
        <path d="M -22,2 C -5,5 11,3 24,-4 C 22,8 9,12 -4,12 C -15,12 -20,8 -22,2 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4"/>
      </g>
      <g id="mouth_mischievous" display="none">
        <path d="M -22,6 C -5,12 13,6 26,-10 C 24,6 9,16 -7,14 C -16,12 -20,10 -22,6 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4" stroke-linejoin="round"/>
      </g>
      <g id="mouth_baffled" display="none">
        <path d="M -18,8 C -9,2 -2,14 7,6 C 13,2 18,8 22,6" fill="none" stroke="#0B0C10" stroke-width="4.5" stroke-linecap="round"/>
      </g>
      <!-- Visemes -->
      <g id="mouth_viseme_rest" display="none">
        <path d="M -16,4 C -4,6 6,5 18,2" fill="none" stroke="#0B0C10" stroke-width="4.2" stroke-linecap="round"/>
      </g>
      <g id="mouth_viseme_A" display="none">
        <ellipse cx="0" cy="8" rx="18" ry="15" fill="#14151A" stroke="#0B0C10" stroke-width="4"/>
        <path d="M -13,-2 C -4,-4 5,-4 13,-2 C 10,3 -9,3 -13,-2 Z" fill="#FFFFFF"/>
        <path d="M -9,15 C -3,11 4,11 10,15 C 4,20 -4,20 -9,15 Z" fill="#EA6A6A"/>
      </g>
      <g id="mouth_viseme_E" display="none">
        <path d="M -22,0 C -7,3 7,2 22,-2 C 20,10 9,14 -2,14 C -13,14 -20,10 -22,0 Z" fill="#14151A" stroke="#0B0C10" stroke-width="4"/>
        <path d="M -18,1 C -5,3 5,2 18,-1 L 16,6 L -16,6 Z" fill="#FFFFFF"/>
      </g>
      <g id="mouth_viseme_I" display="none">
        <path d="M -20,2 C -5,4 7,3 20,0 C 18,9 7,12 -2,12 C -11,12 -18,9 -20,2 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8"/>
      </g>
      <g id="mouth_viseme_O" display="none">
        <ellipse cx="0" cy="8" rx="12" ry="14" fill="#14151A" stroke="#0B0C10" stroke-width="4"/>
        <ellipse cx="0" cy="16" rx="6" ry="4" fill="#EA6A6A"/>
      </g>
      <g id="mouth_viseme_U" display="none">
        <ellipse cx="0" cy="8" rx="8" ry="9" fill="#14151A" stroke="#0B0C10" stroke-width="4"/>
      </g>
      <g id="mouth_viseme_MBP" display="none">
        <path d="M -20,5 C -7,5 7,5 20,4" fill="none" stroke="#0B0C10" stroke-width="5.5" stroke-linecap="round"/>
      </g>
      <g id="mouth_viseme_FV" display="none">
        <path d="M -18,2 L 18,2 C 14,10 -14,10 -18,2 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8"/>
        <path d="M -16,9 C -5,12 5,12 16,9" fill="none" stroke="#0B0C10" stroke-width="3.2" stroke-linecap="round"/>
      </g>
      <g id="mouth_viseme_LTH" display="none">
        <path d="M -18,0 C -5,2 5,2 18,0 C 16,12 -16,12 -18,0 Z" fill="#14151A" stroke="#0B0C10" stroke-width="3.8"/>
        <path d="M -9,6 C -3,2 3,2 9,6 C 4,12 -4,12 -9,6 Z" fill="#EA6A6A"/>
      </g>
    </g>'''


def _legs_svg_for_view(view_id: str) -> str:
    """Clean straight legs & blue sneakers matching poses 01-06."""
    if view_id == "profile_left":
        return '''      <g id="leg_left_upper" transform="translate(-4, 6)" data-pivot="0,0">
        <path d="M -14,-4 L 18,0 L 14,116 L -14,116 Z" fill="#1B1D23" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
        <g id="leg_left_lower" transform="translate(0, 116)" data-pivot="0,0">
          <path d="M -13,-4 L 15,-4 L 12,110 L -13,110 Z" fill="#1B1D23" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
          <g id="foot_left" transform="translate(0, 108)" data-pivot="0,0">
            <path d="M -14,-4 C 8,-6 22,2 26,16 L 28,42 C -4,52 -50,52 -70,38 C -72,20 -46,6 -14,-4 Z" fill="#0072CE" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
            <path d="M -68,31 C -42,42 2,42 26,31 L 28,42 C -2,52 -48,52 -70,39 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
          </g>
        </g>
      </g>
      <g id="leg_right_upper" transform="translate(8, 6)" data-pivot="0,0" opacity="0.9">
        <path d="M -12,-4 L 14,0 L 12,116 L -12,116 Z" fill="#14161B" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
        <g id="leg_right_lower" transform="translate(0, 114)" data-pivot="0,0">
          <path d="M -12,-4 L 12,-4 L 10,110 L -12,110 Z" fill="#14161B" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
          <g id="foot_right" transform="translate(0, 108)" data-pivot="0,0">
            <path d="M -12,-4 C 6,-6 20,2 24,16 L 26,40 C -4,50 -44,50 -64,36 C -66,20 -40,6 -12,-4 Z" fill="#005BA6" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
          </g>
        </g>
      </g>'''
    if view_id == "profile_right":
        return '''      <g id="leg_left_upper" transform="translate(-8, 6)" data-pivot="0,0" opacity="0.9">
        <path d="M -14,0 L 12,-4 L 12,116 L -12,116 Z" fill="#14161B" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
        <g id="leg_left_lower" transform="translate(0, 114)" data-pivot="0,0">
          <path d="M -12,-4 L 12,-4 L 12,110 L -10,110 Z" fill="#14161B" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
          <g id="foot_left" transform="translate(0, 108)" data-pivot="0,0">
            <path d="M -24,16 C -20,2 -6,-6 12,-4 C 40,6 66,20 64,36 C 44,50 4,50 -26,40 Z" fill="#005BA6" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
          </g>
        </g>
      </g>
      <g id="leg_right_upper" transform="translate(4, 6)" data-pivot="0,0">
        <path d="M -18,0 L 14,-4 L 14,116 L -14,116 Z" fill="#1B1D23" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
        <g id="leg_right_lower" transform="translate(0, 116)" data-pivot="0,0">
          <path d="M -15,-4 L 13,-4 L 13,110 L -12,110 Z" fill="#1B1D23" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
          <g id="foot_right" transform="translate(0, 108)" data-pivot="0,0">
            <path d="M -26,16 C -22,2 -8,-6 14,-4 C 46,6 72,20 70,38 C 50,52 4,52 -28,42 Z" fill="#0072CE" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
            <path d="M -26,31 C -2,42 42,42 68,31 L 70,39 C 48,52 2,52 -28,42 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
          </g>
        </g>
      </g>'''
    if view_id in ("back", "back_34"):
        return '''      <g id="leg_left_upper" transform="translate(-24, 6)" data-pivot="0,0">
        <path d="M -16,-4 L 18,0 L 12,118 L -18,116 Z" fill="#1B1D23" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
        <g id="leg_left_lower" transform="translate(-4, 116)" data-pivot="0,0">
          <path d="M -15,-6 L 15,-4 L 12,112 L -16,110 Z" fill="#1B1D23" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
          <g id="foot_left" transform="translate(-2, 108)" data-pivot="0,0">
            <path d="M -22,2 C -10,-8 10,-8 22,2 L 26,42 C 10,50 -12,50 -28,42 Z" fill="#0072CE" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
            <path d="M -26,32 C -10,40 10,40 24,32 L 26,42 C 10,50 -12,50 -28,42 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
          </g>
        </g>
      </g>
      <g id="leg_right_upper" transform="translate(24, 6)" data-pivot="0,0">
        <path d="M -18,0 L 16,-4 L 18,116 L -12,118 Z" fill="#1B1D23" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
        <g id="leg_right_lower" transform="translate(4, 116)" data-pivot="0,0">
          <path d="M -15,-4 L 15,-6 L 16,110 L -12,112 Z" fill="#1B1D23" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
          <g id="foot_right" transform="translate(2, 108)" data-pivot="0,0">
            <path d="M -22,2 C -10,-8 10,-8 22,2 L 28,42 C 12,50 -10,50 -26,42 Z" fill="#0072CE" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
            <path d="M -24,32 C -10,40 10,40 26,32 L 28,42 C 12,50 -10,50 -26,42 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
          </g>
        </g>
      </g>'''
    # Front, front_34_left, front_34_right (pose 01 & 02)
    return '''      <g id="leg_left_upper" transform="translate(-24, 6)" data-pivot="0,0">
        <path d="M -16,-4 L 18,0 L 12,118 L -18,116 Z" fill="#1B1D23" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
        <g id="leg_left_lower" transform="translate(-4, 116)" data-pivot="0,0">
          <path d="M -15,-6 L 15,-4 L 12,112 L -16,110 Z" fill="#1B1D23" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
          <g id="foot_left" transform="translate(-4, 108)" data-pivot="0,0">
            <path d="M -14,-4 C 4,-8 20,-4 28,8 L 32,40 C 10,52 -32,54 -56,42 C -60,26 -44,10 -14,-4 Z" fill="#0072CE" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
            <path d="M -54,32 C -30,42 8,40 30,30 L 32,41 C 8,53 -34,55 -56,43 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
            <path d="M -28,11 C -20,5 -12,5 -6,11 M -20,3 C -12,-3 -4,-3 2,3" fill="none" stroke="#FFFFFF" stroke-width="6" stroke-linecap="round"/>
          </g>
        </g>
      </g>
      <g id="leg_right_upper" transform="translate(24, 6)" data-pivot="0,0">
        <path d="M -18,0 L 16,-4 L 18,116 L -12,118 Z" fill="#1B1D23" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
        <g id="leg_right_lower" transform="translate(4, 114)" data-pivot="0,0">
          <path d="M -15,-4 L 15,-6 L 16,110 L -12,112 Z" fill="#1B1D23" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
          <g id="foot_right" transform="translate(4, 108)" data-pivot="0,0">
            <path d="M -28,8 C -20,-4 -4,-8 14,-4 C 44,10 60,26 56,42 C 32,54 -10,52 -32,40 Z" fill="#0072CE" stroke="#0B0C10" stroke-width="6" stroke-linejoin="round"/>
            <path d="M -30,30 C -8,40 30,42 54,32 L 56,43 C 34,55 -8,53 -32,41 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
            <path d="M 6,11 C 12,5 20,5 28,11 M -2,3 C 4,-3 12,-3 20,3" fill="none" stroke="#FFFFFF" stroke-width="6" stroke-linecap="round"/>
          </g>
        </g>
      </g>'''


def _head_svg_for_view(view_id: str) -> str:
    """Exact 4K-traced head & hair silhouettes (poses 01-06) with live animatable eyes & mouth."""
    parts = _get_rig_parts(view_id)
    head_4k_xml = "\n".join(parts.get("head_paths", []))

    if view_id in ("back", "back_34"):
        return f'''      <g id="head_group" transform="translate(0, -155)" data-pivot="0,0">
        <g id="head_4k_vector">
          {head_4k_xml}
        </g>
        <g id="eyes_group" display="none"></g>
        <g id="mouth_group" display="none"></g>
      </g>'''

    if view_id == "profile_left":
        return f'''      <g id="head_group" transform="translate(0, -155)" data-pivot="0,0">
        <g id="head_4k_vector">
          {head_4k_xml}
        </g>
        <g id="eyes_group" transform="translate(-32, -88)">
          <g id="eye_left" transform="translate(0, 0)">
            <path d="M -18,-4 C -9,-20 11,-18 18,0 C 11,16 -9,16 -18,-4 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4.2"/>
            <g id="iris_group_left">
              <ellipse id="iris_left" cx="-3" cy="0" rx="9" ry="12" fill="#00A99D" stroke="#0B0C10" stroke-width="3"/>
              <ellipse id="pupil_left" cx="-5" cy="1" rx="4.8" ry="7" fill="#0B0C10"/>
              <circle cx="-1" cy="-4" r="2.8" fill="#FFFFFF"/>
            </g>
            <path id="eyelid_left" d="M -20,-6 C -9,-20 11,-18 18,0 L 18,2 L -20,2 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4" opacity="0"/>
          </g>
          <g id="eye_right" display="none"></g>
          <g id="brows_group">
            <path id="brow_left" d="M -22,-24 C -8,-35 10,-33 20,-22 C 8,-28 -8,-30 -22,-24 Z" fill="#0B0C10" stroke="#0B0C10" stroke-width="2.5"/>
            <g id="brow_right" display="none"></g>
          </g>
        </g>
        <g transform="translate(-192, -284) scale(0.56, 0.92)">
          {extended_mouth_variants_svg()}
        </g>
      </g>'''

    if view_id == "profile_right":
        return f'''      <g id="head_group" transform="translate(0, -155)" data-pivot="0,0">
        <g id="head_4k_vector">
          {head_4k_xml}
        </g>
        <g id="eyes_group" transform="translate(32, -88)">
          <g id="eye_left" display="none"></g>
          <g id="eye_right" transform="translate(0, 0)">
            <path d="M -18,0 C -11,-18 9,-20 18,-4 C 9,16 -11,16 -18,0 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4.2"/>
            <g id="iris_group_right">
              <ellipse id="iris_right" cx="3" cy="0" rx="9" ry="12" fill="#00A99D" stroke="#0B0C10" stroke-width="3"/>
              <ellipse id="pupil_right" cx="5" cy="1" rx="4.8" ry="7" fill="#0B0C10"/>
              <circle cx="1" cy="-4" r="2.8" fill="#FFFFFF"/>
            </g>
            <path id="eyelid_right" d="M -18,0 C -11,-18 9,-20 20,-6 L 20,2 L -18,2 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4" opacity="0"/>
          </g>
          <g id="brows_group">
            <g id="brow_left" display="none"></g>
            <path id="brow_right" d="M -20,-22 C -10,-33 8,-35 22,-24 C 8,-30 -8,-28 -20,-22 Z" fill="#0B0C10" stroke="#0B0C10" stroke-width="2.5"/>
          </g>
        </g>
        <g transform="translate(-124, -284) scale(0.56, 0.92)">
          {extended_mouth_variants_svg()}
        </g>
      </g>'''

    face_shift_x = 0 if view_id == "front" else (-14 if view_id == "front_34_left" else 14)
    nose_x = 5 + face_shift_x
    mouth_tx = -278 + face_shift_x

    return f'''      <g id="head_group" transform="translate(0, -155)" data-pivot="0,0">
        <g id="head_4k_vector">
          {head_4k_xml}
        </g>
        <g id="eyes_group" transform="translate({face_shift_x}, -86)">
          <g id="eye_left" transform="translate(-28, 0)">
            <path d="M -22,-5 C -10,-23 12,-19 21,-2 C 15,17 -10,17 -22,-5 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4.2" stroke-linejoin="round"/>
            <g clip-path="url(#clip_eye_left)">
              <g id="iris_group_left" transform="translate(0, 0)">
                <ellipse id="iris_left" cx="-1" cy="0" rx="11.5" ry="13.5" fill="#00A99D" stroke="#0B0C10" stroke-width="3.2"/>
                <ellipse id="pupil_left" cx="-1" cy="1" rx="6.5" ry="8.5" fill="#0B0C10"/>
                <circle cx="3.5" cy="-4.5" r="3.5" fill="#FFFFFF"/>
                <circle cx="-4" cy="5" r="1.6" fill="#FFFFFF"/>
              </g>
            </g>
            <path d="M -25,-7 C -12,-24 12,-21 22,-2" fill="none" stroke="#0B0C10" stroke-width="5.2" stroke-linecap="round"/>
            <path id="eyelid_left" d="M -24,-7 C -12,-23 12,-19 22,-2 L 22,2 L -24,2 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8" opacity="0"/>
          </g>
          <g id="eye_right" transform="translate(30, -1)">
            <path d="M -19,-2 C -10,-21 12,-21 21,-2 C 15,16 -8,17 -19,-2 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="4.2" stroke-linejoin="round"/>
            <g clip-path="url(#clip_eye_right)">
              <g id="iris_group_right" transform="translate(0, 0)">
                <ellipse id="iris_right" cx="1" cy="0" rx="11" ry="13" fill="#00A99D" stroke="#0B0C10" stroke-width="3.2"/>
                <ellipse id="pupil_right" cx="1" cy="1" rx="6.2" ry="8.2" fill="#0B0C10"/>
                <circle cx="4.5" cy="-4.5" r="3.4" fill="#FFFFFF"/>
                <circle cx="-2.5" cy="5" r="1.6" fill="#FFFFFF"/>
              </g>
            </g>
            <path d="M -21,-4 C -10,-23 12,-21 22,-4" fill="none" stroke="#0B0C10" stroke-width="5.2" stroke-linecap="round"/>
            <path id="eyelid_right" d="M -21,-4 C -10,-23 12,-21 22,-2 L 22,2 L -21,2 Z" fill="#FFFFFF" stroke="#0B0C10" stroke-width="3.8" opacity="0"/>
          </g>
          <g id="brows_group">
            <path id="brow_left" transform="translate(0, 0)" d="M -52,-26 C -37,-40 -18,-38 -8,-26 C -20,-31 -35,-31 -52,-26 Z" fill="#0B0C10" stroke="#0B0C10" stroke-width="2.5" stroke-linejoin="round"/>
            <path id="brow_right" transform="translate(0, 0)" d="M 10,-26 C 22,-38 41,-40 54,-26 C 37,-31 22,-31 10,-26 Z" fill="#0B0C10" stroke="#0B0C10" stroke-width="2.5" stroke-linejoin="round"/>
          </g>
        </g>
        <path id="nose" d="M {nose_x},-64 C {nose_x + 6},-62 {nose_x + 6},-55 {nose_x},-53" fill="none" stroke="#0B0C10" stroke-width="3.5" stroke-linecap="round"/>
        <g transform="translate({mouth_tx}, -282)">
          {extended_mouth_variants_svg()}
        </g>
      </g>'''


def build_view_svg(view_id: str, hand_variants_fn) -> str:
    """Build a complete layered 2D SVG for one of the 7 turnaround views."""
    parts = _get_rig_parts(view_id)
    shirt_4k_xml = "\n".join(parts.get("shirt_paths", []))
    tie_4k_xml = "\n".join(parts.get("tie_paths", []))
    tie_visible = 'display="none"' if view_id in ("back", "back_34") or not tie_4k_xml else ""

    if view_id in ("profile_left", "profile_right"):
        arms_svg = f'''        <g id="arm_left_upper" transform="translate(-8, -110)" data-pivot="0,0">
          <path d="M -8,-4 L 8,-4 L 9,52 L -8,52 Z" fill="#14161B" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
          <g id="arm_left_forearm" transform="translate(0, 50)" data-pivot="0,0">
            <path d="M -8,-4 L 8,-4 L 8,46 L -8,46 Z" fill="#14161B" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
            <g id="wrist_left" transform="translate(0, 48)" data-pivot="0,0">
              {hand_variants_fn("left")}
{articulated_hand_svg("left")}
            </g>
          </g>
        </g>
        <g id="arm_right_upper" transform="translate(8, -110)" data-pivot="0,0">
          <path d="M -8,-4 L 8,-4 L 8,52 L -9,52 Z" fill="#14161B" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
          <g id="arm_right_forearm" transform="translate(0, 50)" data-pivot="0,0">
            <path d="M -8,-4 L 8,-4 L 8,46 L -8,46 Z" fill="#14161B" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
            <g id="wrist_right" transform="translate(0, 48)" data-pivot="0,0">
              {hand_variants_fn("right")}
{articulated_hand_svg("right")}
            </g>
          </g>
        </g>'''
    else:
        arms_svg = f'''        <g id="arm_left_upper" transform="translate(-48, -110)" data-pivot="0,0">
          <path d="M -6,-4 L 10,-2 L -2,52 L -18,48 Z" fill="#14161B" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
          <g id="arm_left_forearm" transform="translate(-10, 48)" data-pivot="0,0">
            <path d="M -8,-2 L 8,-2 L 2,46 L -14,44 Z" fill="#14161B" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
            <g id="wrist_left" transform="translate(-6, 48)" data-pivot="0,0">
              {hand_variants_fn("left")}
{articulated_hand_svg("left")}
            </g>
          </g>
        </g>
        <g id="arm_right_upper" transform="translate(48, -110)" data-pivot="0,0">
          <path d="M -10,-2 L 6,-4 L 18,48 L 2,52 Z" fill="#14161B" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
          <g id="arm_right_forearm" transform="translate(10, 48)" data-pivot="0,0">
            <path d="M -8,-2 L 8,-2 L 14,44 L -2,46 Z" fill="#14161B" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
            <g id="wrist_right" transform="translate(6, 48)" data-pivot="0,0">
              {hand_variants_fn("right")}
{articulated_hand_svg("right")}
            </g>
          </g>
        </g>'''

    shirt_svg = f'''        <g id="shirt_group" transform="translate(0, 0)">
          {shirt_4k_xml}
        </g>'''

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" id="brand_mascot_v1_{view_id}" data-view-id="{view_id}" viewBox="0 0 600 800" width="600" height="800">
  <title>Creative Stickman Studio V3.2 — Brand Mascot V1 ({view_id})</title>
  <desc>Genuine layered, articulated 2D vector mascot view ({view_id}) traced from 4K reference poses 01-06.</desc>
  <defs>
    <clipPath id="clip_eye_left">
      <path d="M 248,200 C 260,182 282,186 291,203 C 285,222 260,222 248,200 Z"/>
    </clipPath>
    <clipPath id="clip_eye_right">
      <path d="M 311,202 C 320,183 342,183 351,202 C 345,220 322,221 311,202 Z"/>
    </clipPath>
  </defs>

  <g id="character_root" transform="translate(0, 0)" data-pivot="300,745">
    <g id="pelvis_group" transform="translate(300, 460)" data-pivot="0,0">

{_legs_svg_for_view(view_id)}

      <g id="torso_group" transform="translate(0, 0)" data-pivot="0,0">
{arms_svg}

        <g id="neck_group" transform="translate(0, -145)" data-pivot="0,0">
          <path d="M -14,-16 L 14,-16 L 13,14 L -13,14 Z" fill="#14161B" stroke="#0B0C10" stroke-width="5" stroke-linejoin="round"/>
        </g>

{shirt_svg}

        <g id="tie_group" transform="translate(0, 0)" data-pivot="0,-120" {tie_visible}>
          {tie_4k_xml}
        </g>
      </g>

{_head_svg_for_view(view_id)}
    </g>
  </g>
</svg>'''
