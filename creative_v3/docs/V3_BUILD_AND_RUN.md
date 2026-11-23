# Creative Stickman Studio V3.2 — Build & Run Guide

## Prerequisites
- Python 3.11+ with `PySide6`, `lxml`, `Pillow`, `fastapi`, `uvicorn`, `pytest`
- `ffmpeg` on PATH (`libvpx-vp9` for `yuva420p` transparent WebM)

## Commands
```powershell
# 1. Build mascot master SVG, 7 turnaround views, rig.json, manifest
python -m creative_v3.characters.brand_mascot_v1.build_mascot

# 2. Build Asset Factory (40 icons, 20 props, 24 FX primitives)
python -m creative_v3.asset_factory.factory

# 3. Render & verify all 12 Character Readiness Gallery clips
python -m creative_v3.characters.brand_mascot_v1.build_readiness_gallery

# 4. Validate all 100 actions & render full 30fps sequences
python -m creative_v3.api.cli validate
python -m creative_v3.api.cli render-batch --start 1 --end 100 --width 480 --height 360 --step 1

# 5. Launch isolated V3.2 Studio UI (port 8765)
python -m creative_v3.studio.ui.server

# 6. Run V3.2 tests + legacy regression tests
python -m pytest creative_v3/tests/test_creative_v3.py -v
python -m pytest tests/test_core_foundation.py tests/test_tcm_ds_contracts.py tests/test_vyond_story.py -q
```
