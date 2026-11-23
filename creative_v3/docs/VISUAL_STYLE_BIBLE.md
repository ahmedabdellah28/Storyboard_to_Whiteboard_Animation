# Creative Stickman Studio V3.2 — Visual Style Bible

## 1. Brand Identity & Design Tokens
| Token | Value | Usage |
|---|---|---|
| `face_and_hands` | `#FFFFFF` | Head, neck, hands, teeth, eye sclera, shoe trim |
| `hair_primary` | `#1A1C22` | Swept top crest + left-side spiky tufts |
| `hair_highlight` | `#2D313C` | Crest & nape line highlights |
| `outline_ink` | `#0B0C10` | Master stroke (`5.5px–6.5px` round join/cap) |
| `eyes_teal` | `#00A99D` | Signature teal irises + portal/energy accents |
| `outfit_blue` | `#0072CE` | Short-sleeve polo shirt + sneakers |
| `tie_yellow` | `#FFD400` | Signature yellow necktie + spark/star accents |
| `tongue_coral` | `#EA6A6A` | Interior mouth tongue accent |

## 2. Line-Art & Proportion Rules
- Head silhouette is a rounded-square with tapered chin (`6.5px` `#0B0C10` contour).
- Asymmetrical hair crest sweeps toward character's right; spiky tufts anchor on character's left.
- Never swap into a generic black-circle stickman mid-action.
- Planted feet maintain `ground_contact` at `y=740` (character local) unless airborne.

## 3. Motion Craft & 30/60 FPS Discipline
- Standard frame rate: **30 FPS** (`--step 1`, continuous interpolation via `easing.py`), with **60 FPS** supported on demand.
- Anticipation before launch, clear action arcs, eye-lead before head/torso, and secondary follow-through on `tie_group`.
- Performance tones: `playful`, `curious`, `dramatic`, `triumphant`, `mischievous`, `baffled`, `focused`.
