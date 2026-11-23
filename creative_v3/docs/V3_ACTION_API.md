# V3.2 Headless Character & Action API

## 1. Python Rig Control API (`creative_v3/api/commands.py`)
- `create_rig_state() -> RigState`
- `set_joint_angle(state, joint_id, angle_deg)`
- `set_joint_position(state, joint_id, tx, ty)`
- `set_ik_target(state, chain_id, target_xy, weight=1.0, bend_dir=1)`
- `set_finger_curl(state, side, finger, curl, spread=None)`
- `set_gaze_target(state, gx, gy)`
- `set_expression(state, expression)` (12 emotions)
- `set_viseme(state, viseme)` (9 visemes)
- `set_view_id(state, view_id)` (7 turnaround views)
- `set_view_blend(state, blend)`
- `play_clip(clip_id, state_sequence, out_dir, width=640, height=480, fps=30)`
- `render_frames(state_sequence, out_dir, width=640, height=480)`
- `export_svg(state, out_svg_path)`

## 2. Headless CLI (`creative_v3/api/cli.py`)
- `python -m creative_v3.api.cli list [--category A_performance]`
- `python -m creative_v3.api.cli validate`
- `python -m creative_v3.api.cli render-action <action_id> [--width 640] [--height 480] [--step 1]`
- `python -m creative_v3.api.cli render-batch [--start 1] [--end 100] [--width 480] [--height 360] [--step 1]`

## 3. Studio FastAPI Server (`creative_v3/studio/ui/server.py`)
- `GET /` — Interactive Character & Pose Studio + 100 Action Library
- `POST /api/preview-svg` — Live SVG DOM preview (pose, view_id, expression, viseme, gaze, finger_curls)
- `GET /api/actions` — Full 100-action catalog JSON
- `POST /api/render-action` — Render action deliverables
- `GET /api/assets` — Asset Factory manifest (40 icons, 20 props, 24 FX)
- `GET /api/readiness` — 12 Character Readiness clips QA JSON
- `GET /gallery` — Action Gallery HTML
