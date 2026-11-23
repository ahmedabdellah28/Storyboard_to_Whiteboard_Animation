"""
Isolated FastAPI Character + Motion & Action Studio UI for Creative Stickman Studio V3.
Run via: python -m creative_v3.studio.ui.server
Does NOT modify or replace legacy studio_ui/.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel

from creative_v3.engine.actions.catalog_100 import build_100_actions, get_action_map
from creative_v3.engine.actions.runner import CHAR_DIR, V3_ROOT, render_action_deliverables
from creative_v3.engine.renderers.svg_renderer import apply_pose_to_svg, load_view_svg_bytes
from creative_v3.engine.rigging.rig_model import load_rig

app = FastAPI(title="Creative Stickman Studio V3.2", version="3.2.0")


class PosePreviewRequest(BaseModel):
    pose: Dict[str, dict] = {}
    view_id: str = "front"
    expression: str = "smile"
    viseme: Optional[str] = None
    gaze_x: float = 0.0
    gaze_y: float = 0.0
    left_hand: str = "fist"
    right_hand: str = "open_palm"
    finger_curls: Optional[Dict[str, Dict[str, float]]] = None


class RenderActionRequest(BaseModel):
    action_id: str
    width: int = 640
    height: int = 480
    params: Optional[dict] = None


@app.get("/", response_class=HTMLResponse)
def studio_home() -> str:
    rig = load_rig(CHAR_DIR / "rig.json")
    actions = [
        {"number": s.number, "action_id": s.action_id, "category": s.category, "title": s.title, "duration_frames": s.duration_frames}
        for s in build_100_actions()
    ]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Creative Stickman Studio V3</title>
<style>
body{{margin:0;font-family:system-ui,sans-serif;background:#0b1120;color:#e2e8f0;display:grid;grid-template-columns:340px 1fr;height:100vh}}
aside{{background:#111827;border-right:1px solid #1f2937;padding:16px;overflow:auto}}
main{{display:flex;flex-direction:column;padding:16px;overflow:auto;gap:16px}}
label{{display:block;font-size:12px;color:#94a3b8;margin-top:8px}}
select,input,button{{width:100%;padding:8px;margin-top:4px;border-radius:6px;border:1px solid #334155;background:#1e293b;color:#fff}}
button{{background:#0284c7;border:none;font-weight:600;cursor:pointer;margin-top:12px}}
.stage{{background:#0f172a;border:1px solid #334155;border-radius:12px;padding:12px;display:flex;justify-content:center;align-items:center;min-height:420px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}}
.card{{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px;cursor:pointer}}
.card:hover{{border-color:#38bdf8}}
</style></head><body>
<aside>
  <h2>Character & Pose Studio</h2>
  <label>Expression</label>
  <select id="expr" onchange="updatePreview()">{"".join(f'<option>{e}</option>' for e in rig['expressions'])}</select>
  <label>Right Hand</label>
  <select id="rh" onchange="updatePreview()">{"".join(f'<option>{h}</option>' for h in rig['hand_poses'])}</select>
  <label>Left Hand</label>
  <select id="lh" onchange="updatePreview()">{"".join(f'<option {"selected" if h=="fist" else ""}>{h}</option>' for h in rig['hand_poses'])}</select>
  <label>Head Tilt (<span id="hv">0</span>°)</label>
  <input type="range" id="head_rot" min="-40" max="40" value="0" oninput="hv.innerText=this.value;updatePreview()">
  <label>Torso Lean (<span id="tv">0</span>°)</label>
  <input type="range" id="torso_rot" min="-35" max="35" value="0" oninput="tv.innerText=this.value;updatePreview()">
  <label>Right Arm (<span id="rav">0</span>°)</label>
  <input type="range" id="rarm_rot" min="-140" max="90" value="0" oninput="rav.innerText=this.value;updatePreview()">
  <button onclick="renderSelected()">Render Selected Action Frames</button>
  <pre id="status" style="font-size:11px;color:#4ade80;white-space:pre-wrap"></pre>
</aside>
<main>
  <div class="stage" id="stage">Loading SVG Rig...</div>
  <h3>100 Creative Action Library</h3>
  <input id="q" placeholder="Filter 100 actions..." oninput="renderGrid()">
  <div class="grid" id="grid"></div>
</main>
<script>
const ACTIONS = {json.dumps(actions)};
let selectedAction = "signature_idle_breath";
async function updatePreview(){{
  const body = {{
    expression: expr.value, right_hand: rh.value, left_hand: lh.value,
    pose: {{
      head_group: {{rot: +head_rot.value}},
      torso_group: {{rot: +torso_rot.value}},
      arm_right_upper: {{rot: +rarm_rot.value}}
    }}
  }};
  const res = await fetch('/api/preview-svg', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify(body)}});
  stage.innerHTML = await res.text();
}}
function renderGrid(){{
  const f = q.value.toLowerCase();
  grid.innerHTML = ACTIONS.filter(a=>!f||a.action_id.includes(f)||a.title.toLowerCase().includes(f))
    .map(a=>`<div class="card" onclick="selectedAction='${{a.action_id}}';status.innerText='Selected: ${{a.action_id}}'">
      <b>#${{String(a.number).padStart(3,'0')}}</b> ${{a.title}}<br><small style="color:#fbbf24">${{a.action_id}}</small>
    </div>`).join('');
}}
async function renderSelected(){{
  status.innerText = 'Rendering ' + selectedAction + '...';
  const res = await fetch('/api/render-action', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{action_id: selectedAction}})}});
  status.innerText = JSON.stringify(await res.json(), null, 2);
}}
updatePreview(); renderGrid();
</script></body></html>"""


@app.post("/api/preview-svg")
def preview_svg(req: PosePreviewRequest) -> Response:
    master = load_view_svg_bytes(req.view_id)
    svg_bytes = apply_pose_to_svg(
        master,
        req.pose,
        expression=req.expression,
        left_hand=req.left_hand,
        right_hand=req.right_hand,
        canvas_viewbox=(0, 0, 600, 800),
        char_offset_xy=(0.0, 0.0),
        viseme=req.viseme,
        gaze_xy=(req.gaze_x, req.gaze_y),
        finger_curls=req.finger_curls,
    )
    return Response(content=svg_bytes, media_type="image/svg+xml")


@app.get("/api/assets")
def list_assets() -> dict:
    manifest_path = V3_ROOT / "asset_factory" / "asset_manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Asset manifest not generated")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


@app.get("/api/readiness")
def get_readiness() -> dict:
    qa_path = CHAR_DIR / "character_readiness_gallery" / "readiness_qa.json"
    if not qa_path.exists():
        raise HTTPException(status_code=404, detail="Readiness gallery not generated")
    return json.loads(qa_path.read_text(encoding="utf-8"))


@app.get("/api/actions")
def list_actions() -> dict:
    specs = build_100_actions()
    return {"count": len(specs), "actions": [s.to_dict() for s in specs]}


@app.post("/api/render-action")
def api_render_action(req: RenderActionRequest) -> dict:
    amap = get_action_map()
    if req.action_id not in amap:
        raise HTTPException(status_code=404, detail="Action not found")
    return render_action_deliverables(
        amap[req.action_id],
        width=req.width,
        height=req.height,
        frame_step=2,
        export_webm=True,
        param_overrides=req.params,
    )


@app.get("/gallery", response_class=FileResponse)
def gallery_page() -> Path:
    gal = V3_ROOT / "index" / "action_gallery.html"
    if not gal.exists():
        raise HTTPException(status_code=404, detail="Gallery not generated yet")
    return gal


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
