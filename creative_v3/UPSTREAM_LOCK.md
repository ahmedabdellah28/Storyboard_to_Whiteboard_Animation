# Creative Stickman Studio V3 — Upstream Dependency Lock (M1)

All upstream repositories are isolated under `third_party/` (never inside legacy `core/`, `production_engine/`, or `studio_ui/`).

| Repository | Remote URL | Pinned Commit SHA | Version | License | Role in V3 | Status |
|---|---|---|---|---|---|---|
| `anicraft` | `https://github.com/storytold/anicraft.git` | `d439e3e10e38eda630aa413871b76f721a2a0719` | `0.3.0` | `MIT OR Apache-2.0` | SVG import, vector animation, keyframes, tweening, headless CLI (`anicraft-cli`) | Cloned & Inspecting |
| `vectorcraft` | `https://github.com/storytold/vectorcraft.git` | `5bd8acfce98e784a37618e8c6c082fc13e2e0165` | `0.24.1` | `MIT OR Apache-2.0` | SVG/vector path & shape editing/export (`vectorcraft-cli`) | Cloned & Inspecting |
| `effectcraft` | `https://github.com/storytold/effectcraft.git` | `d6c9ad664342c19e1ed473b4356292647117be62` | `0.24.1` | `MIT OR Apache-2.0` | Layered motion/compositing, keyframes, particles, headless CLI (`effectcraft-cli`) | Cloned & Inspecting |
| `filmcraft` | `https://github.com/storytold/filmcraft.git` | `1ec744c2ecbd15e31484caf62510f4bd9e570c21` | `0.20.1` | `MIT OR Apache-2.0` | Video montage/assembly (`filmcraft-frame`, `filmcraft-time`, `filmcraft-audio-dsp`, `filmcraft-isobmff`, `filmcraft-matroska`) | **Pinned & Deferred (Per Phase Scope)** |

## Notes
- Upstream license files (`LICENSE-MIT`, `LICENSE-APACHE`) are preserved intact inside each `third_party/<repo>/` directory.
- No local modifications have been made to any `third_party/<repo>/` source tree.
- `filmcraft` APIs are documented and version-pinned only; story montage / full video editing is intentionally deferred from this phase.
