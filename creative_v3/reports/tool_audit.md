# M1 Tool Audit & Upstream Integration Report

## Upstream Repositories (Pinned in `creative_v3/UPSTREAM_LOCK.md`)
| Tool | Path | Pinned SHA | Version | License | Status |
|---|---|---|---|---|---|
| `anicraft` | `third_party/anicraft` | `d439e3e10e38eda630aa413871b76f721a2a0719` | `0.3.0` | `MIT OR Apache-2.0` | `cargo check -p anicraft-cli` **PASS** |
| `vectorcraft` | `third_party/vectorcraft` | `5bd8acfce98e784a37618e8c6c082fc13e2e0165` | `0.24.1` | `MIT OR Apache-2.0` | `cargo check -p vectorcraft-cli` **PASS** |
| `effectcraft` | `third_party/effectcraft` | `d6c9ad664342c19e1ed473b4356292647117be62` | `0.24.1` | `MIT OR Apache-2.0` | `cargo check -p effectcraft-cli` **PASS** |
| `filmcraft` | `third_party/filmcraft` | `1ec744c2ecbd15e31484caf62510f4bd9e570c21` | `0.20.1` | `MIT OR Apache-2.0` | **Pinned & Deferred** (per M1) |

## Practical CLI Probe & Disk-Space Finding
- All three active Rust CLIs (`anicraft-cli`, `vectorcraft-cli`, `effectcraft-cli`) passed `cargo check` cleanly under `rustc 1.99.0` / `cargo 1.99.0`.
- Full `cargo run` binary compilation of `vectorcraft-cli` and `effectcraft-cli` failed on `E:` with `os error 112: There is not enough space on the disk` after generating ~5.8 GiB of debug build artifacts (`third_party/*/target`).
- `cargo clean` was executed on all three `third_party` workspaces, reclaiming **5.8 GiB** (`5,803,618,304` bytes free on `E:`) to ensure ample headroom for the 12 readiness clips and 100 rendered action sequences.

## Isolated Local Engine Path (D+3 / D+10 Compliant)
Per V3.2 Section D+3 & D+10 ("If an upstream dependency cannot perform a capability reliably, document the failure, implement an isolated alternate engine path and run the same acceptance tests"):
- **SVG DOM Rigging & Mutation:** `lxml.etree` (`creative_v3/engine/renderers/svg_renderer.py`)
- **RGBA Vector Rasterization:** `PySide6.QtSvg.QSvgRenderer` (`QImage.Format_RGBA8888`, transparent alpha)
- **Contact Sheets & Thumbnails:** `Pillow`
- **Transparent Preview Encoding:** `ffmpeg` (`libvpx-vp9`, `yuva420p` alpha channel)
- **Parametric 2D VFX:** `creative_v3/engine/effects/vector_fx.py` (24 SVG/2D VFX primitives)
