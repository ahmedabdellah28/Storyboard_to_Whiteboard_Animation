# V3.2 2D Turnaround & Articulated Rig Guide

## 1. Strictly 2D Layered SVG Architecture
- Zero 3D meshes, zero Blender dependencies, zero embedded raster bitmaps (`embedded_bitmaps: 0`).
- All 7 views live in `creative_v3/characters/brand_mascot_v1/turnaround_svg/`:
  - `front.svg` (`FRONT`)
  - `front_34_left.svg` (`FRONT-3/4-LEFT`)
  - `front_34_right.svg` (`FRONT-3/4-RIGHT`)
  - `profile_left.svg` (`LEFT-PROFILE`)
  - `profile_right.svg` (`RIGHT-PROFILE`)
  - `back_34.svg` (`BACK-3/4`)
  - `back.svg` (`BACK`)
- Every view preserves asymmetrical hair/tie placement without naive horizontal mirroring and shares identical skeletal group IDs.

## 2. Rig Controls (`rig.json` v3.2.0)
- **18 Skeletal Bones** (`character_root`, `pelvis_group`, `torso_group`, `neck_group`, `head_group`, `tie_group`, left/right arms/forearms/wrists, left/right upper/lower legs/feet) with joint limits.
- **4 Two-Bone IK Chains** (`left_arm`, `right_arm`, `left_leg`, `right_leg`) with IK/FK blending.
- **20 Articulated Finger Joints** (5 fingers × 2 segments × 2 hands) + 8 stylized hand poses.
- **Independent Face Controls:** `iris_group_left/right` gaze (`[-1, 1]`), `eyelid_left/right` openness (`[0, 1]`), `brow_left/right` lift & tilt, **12 emotions**, and **9 lip-sync visemes**.

## 3. Character Readiness Gallery (C+4)
All 12 executable test clips in `character_readiness_gallery/` verify turnaround, walk, jump, IK reach, finger curl/spread, gaze/blink, 12 expressions, 9 visemes, tie follow-through, prop grip, squash/stretch, and combined acting.
