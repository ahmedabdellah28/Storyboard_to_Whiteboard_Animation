# Motion Graphics & Whiteboard Video System: Comprehensive Project Audit

**Document:** `docs/MOTION_PROJECT_AUDIT.md`  
**Date:** October 2026  
**Auditor:** Antigravity Agent  
**Repository:** `image_to_animate`  
**Target Workflow:**  
`Storyboard → AI-generated Animation Asset Sheet → existing Python asset extraction → extracted transparent PNG assets → local script/audio timing analysis → semantic visual beats → motion planning → camera planning → deterministic rendering`

---

## 1. Executive Summary

The repository `image_to_animate` is a mature, production-proven engine designed to convert storyboards and character asset sheets into broadcast-quality 1080p 30 FPS animated whiteboard/motion videos.

Crucially, **the repository already contains two parallel, working pipelines and extensive supporting infrastructure**:
1. **The Production Engine (OSAS v3.1 / `DynamicSectionEngine`)**: A high-throughput, hardware-accelerated (NVIDIA NVENC) deterministic renderer that composites hand-inking paths, secondary kinetic animations (`slide_down`, `slide_up`, `jelly_pop`, `pulse_pop`, `organic_grow`), camera panning, and 48kHz audio mixing with ducked sound effects.
2. **The Tri-Contract Manifest & Deterministic Scheduler (TCM-DS v2.0)**: A formal three-contract architecture (`VisualManifest` → `NarrativeVisualMap` → `FinalRenderPlan`) that isolates visual truth from narrative concepts and scheduling, operating with zero runtime LLMs.
3. **Asset Sheet Extractor Output**: Already present at `asset_sheet_extractor_v2_output/` containing `assets/` (55 clean transparent PNGs), `assets.json`, `report.json`, `foreground_mask.png`, and `preview_diagnostics.png`.

**Core Audit Verdict**: There is **no need to rewrite or replace** the core engine. The transition to the new motion graphics workflow requires only a lightweight compatibility adapter, semantic beat binding, and motion parameter extensions.

---

## 2. Directory & Component Mapping

| Required Component | Existing Workspace Location | Status |
|---|---|---|
| **1. Existing Asset Extraction Code** | • `core/vision/adaptive_candidate_extractor.py`<br>• `production_engine/dynamic_storyboard_extractor.py`<br>• `dev_separator/adaptive_layer_splitter.py`<br>• `extract_guan_yu_assets.py`, `extract_al_baraa_assets.py` | Active, fully functional |
| **2. Existing Extracted Asset Outputs** | • `asset_sheet_extractor_v2_output/assets/` (55 assets `asset_001.png` to `asset_055.png`)<br>• `sections/brain_illusions_documentary/01..07/assets/`<br>• `sections/fiercest_warriors_documentary/07_guan_yu/assets/` | Populated with transparent RGBA PNGs & metadata |
| **3. Asset Extractor Equivalents** | • `asset_sheet_extractor_v2_output/assets.json`<br>• `asset_sheet_extractor_v2_output/report.json`<br>• `asset_sheet_extractor_v2_output/preview_diagnostics.png`<br>• `asset_sheet_extractor_v2_output/foreground_mask.png` | Complete match to requested specifications |
| **4. Script Source** | • `sections/<project>/<section>/script.txt`<br>• `project_content/transcript_to_speech.txt` | Clean Arabic / multi-lingual scripts |
| **5. Master Audio** | • `sections/<project>/<section>/master_audio.wav`<br>• `sections/<project>/<section>/voice/section.wav`<br>• `output_animations/<project>/deliverables/sections/*.wav` | 48kHz stereo masters with ducked SFX |
| **6. Whisper Timing JSON** | • `sections/<project>/<section>/timing/whisper.json`<br>• `section_timing/transcription/faster_whisper_engine.py` | Word-level timestamps, probabilities, durations |
| **7. Beat / Timeline Modules** | • `section_timing/visual/beat_solver.py`<br>• `section_timing/visual/semantic_beat_mapper.py`<br>• `section_timing/speech/speech_beat_detector.py`<br>• `core/scheduling/constraint_scheduler.py`<br>• `core/sync/anchor_resolver.py` | Deterministic anchor & beat scheduling |
| **8. Whiteboard Renderer** | • `core/render_engine/render/concentric_engine.py` (outside-in inking)<br>• `core/render_engine/render/hand_compositor.py` (hand sprite)<br>• `kivy/engine/render/renderer.py` | High-precision contour tracing & hand compositing |
| **9. Dynamic Renderer** | • `production_engine/dynamic_section_engine.py` (NVENC / OpenCV)<br>• `core/render_engine/render/deep_pipeline_engine.py`<br>• `scripts/render_guan_yu_tcm_v2.py` | 1080p @ 30 FPS multi-element kinetic rendering |
| **10. Camera / Timeline Code** | • `core/render_engine/camera/camera.py`<br>• `production_engine/dynamic_section_engine.py` (`smootherstep`, JIT pans)<br>• `CAMERA_EDITOR_V3.md` | Smooth Hermite / smootherstep viewport interpolator |
| **11. Preview / Studio Code** | • `studio_ui/main_window.py`<br>• `studio_ui/views/` (`camera_render_view.py`, `studio_timeline.py`, `studio_canvas.py`)<br>• `kivy/studio/` | Full desktop GUI for canvas inspection and playback |
| **12. Existing Tests** | • `tests/test_tcm_ds_contracts.py`<br>• `tests/test_visual_beat_solver_v2.py`<br>• `tests/test_production_dag_execution.py`<br>• `tests/test_golden_baseline.py` (49 test files) | Comprehensive regression & contract test suite |
| **13. Data Structures** | • `core/contracts/visual_manifest.py`<br>• `core/contracts/narrative_map.py`<br>• `core/contracts/render_plan.py`<br>• `core/contracts/studio_contracts.py` | Fully typed Pydantic models with cryptographic hashes |

---

## 3. Current Architecture & Pipeline Flow

### 3.1 The TCM-DS v2 Three-Contract Model
```
[ Storyboard / Asset Sheet ]
            │
            ▼
[ AdaptiveCandidateExtractor ]
            │ (crops, bboxes, masks)
            ▼
[ VisualReviewerEngine ] ───► Contract 1: visual_manifest.json (Pure Visual Truth)
                                       │
[ script.txt ] ────────────────────────┼───► Contract 2: narrative_visual_map.json (Semantic Bridge)
                                       │
[ FasterWhisperEngine ] ───────────────┼───► DeterministicAnchorResolver
 (whisper.json)                        │
                                       ▼
                         [ ConstraintVisualScheduler ] ───► Contract 3: final_render_plan.json (Physical Plan)
                                                                       │
                                                                       ▼
                                                          [ DynamicSectionEngine ]
                                                          (NVENC 1080p MP4 + Master WAV)
```

1. **Contract 1: Visual Manifest (`visual_manifest.json`)**: Contains solely visual entities, bounding boxes, normalized demand scores (pixel mass, contour perimeter, edge complexity), aspect ratios, and spatial relationships. It is strictly isolated from narration text.
2. **Contract 2: Narrative Visual Map (`narrative_visual_map.json`)**: Connects visual entities to narrative concepts, assigning priority weights, semantic roles (`hero`, `support`, `context`, `decorative`), anchor search phrases, and continuity rules.
3. **Contract 3: Final Render Plan (`final_render_plan.json`)**: Contains concrete physics, timestamps, lead-in times, draw durations, screen coordinates, camera keyframes, and SFX cues. Computed 100% deterministically.

### 3.2 The Runtime Rendering Engine (`DynamicSectionEngine`)
The engine in `production_engine/dynamic_section_engine.py` operates on a continuous world canvas:
- **Canvas Dimensions**: Native 1920×1080 viewports projected across a multi-thousand-pixel horizontal world (`cam_y = 800.0`, `cam_zoom = 0.58–0.68`).
- **Inking Cache Generator (`build_solid_inking_cache`)**: Traces outer subject contours using concentric boundary peeling (`concentric_engine`), rendering progressive reveal masks.
- **Hand Compositor (`hand_compositor`)**: Computes real-time pen tip coordinates and alpha-blends the artist hand sprite on top of the drawing frame.
- **Secondary Animation Subsystem**:
  - `slide_down`: Vertical drop with smootherstep deceleration and landing pop.
  - `slide_up`: Ascending entrance with opacity blend.
  - `jelly_pop`: Damped sinusoidal elastic scale bounce.
  - `pulse_pop`: Single harmonic scale pulse.
  - `organic_grow`: Radial expansion from element centroid with shimmer.
- **Encoder Pipeline**: Pipes raw BGR24 frames directly to FFmpeg with NVIDIA NVENC (`h264_nvenc`, preset `p7`, `cq 18`) at ~60 FPS, with seamless fallback to `libx264 ultrafast`.

---

## 4. Current Timeline & Audio Synchronization Pipeline

1. **Audio Ingestion**:
   - Voiceover generated via Fenrir TTS (`voice/section.wav`) or ingested from studio recording.
   - Ground truth transcription generated via `FasterWhisperEngine` (`timing/whisper.json`), capturing exact word start/end timestamps and confidence scores.
2. **Anchor Resolution (`DeterministicAnchorResolver`)**:
   - Evaluates multi-tier text matching (Exact → Normalized → Token → Phonetic → Contextual) between script concepts and spoken words.
   - Applies a deterministic lead-in offset (`t_start = word_t - 0.20s`) so drawing initiates 200ms before the word is vocalized.
3. **Duration & Demand Allocation**:
   - Draw duration is governed by visual complexity metrics (`pixel_mass`, `contour_length`, `edge_complexity`) rather than arbitrary static numbers.
   - Enforces a minimum explanation hold time: elements and camera remain visible and stationary for the entire sentence duration.
4. **Audio Ducking & SFX Alignment (`mix_section_audio.py`)**:
   - Generates synchronized SFX cues for marker inking, completion pops, whooshes on slides, and camera transitions.
   - Dynamically ducks voiceover/SFX to preserve pristine narration clarity at 48kHz stereo.

---

## 5. Current Camera System

1. **Geometry & Projection**:
   - Camera center $(C_x, C_y)$ and zoom factor $Z$.
   - Screen transformation:
     $$\text{scr}_x = (W_x - C_x) \cdot Z + \frac{\text{WIDTH}}{2}$$
     $$\text{scr}_y = (W_y - C_y) \cdot Z + \frac{\text{HEIGHT}}{2}$$
2. **Just-In-Time (JIT) Camera Panning**:
   - Camera stays locked on the active scene during narration hold.
   - Pan initiates only at:
     $$\text{pan\_end} = \text{next\_start} - 0.05\text{s}$$
     $$\text{pan\_start} = \max(\text{prev\_end} + 0.05\text{s}, \text{pan\_end} - 0.40\text{s})$$
   - Prevents blank white canvases between narrative points.
3. **Interpolation**:
   - Uses `smootherstep(p) = p^3 * (p * (p * 6 - 15) + 10)` for zero jerk and zero acceleration discontinuities.

---

## 6. Existing Strengths & Reusable Modules

| Module / System | File Path | Reuse Strategy |
|---|---|---|
| **Contour Inking Engine** | `core/render_engine/render/concentric_engine.py` | Direct reuse (Zero changes) |
| **Hand Compositor** | `core/render_engine/render/hand_compositor.py` | Direct reuse (Zero changes) |
| **Dynamic Video Renderer** | `production_engine/dynamic_section_engine.py` | Direct reuse as core rendering target |
| **Whisper Transcription Engine** | `section_timing/transcription/faster_whisper_engine.py` | Direct reuse for local word alignment |
| **Audio SFX Ducking Mixer** | `production_engine/mix_section_audio.py` | Direct reuse for master audio mastering |
| **Contract Data Models** | `core/contracts/` (`visual_manifest.py`, etc.) | Direct reuse as canonical data schemas |
| **Deterministic Scheduler** | `core/scheduling/constraint_scheduler.py` | Direct reuse for conflict-free beat timing |
| **Anchor Resolver** | `core/sync/anchor_resolver.py` | Direct reuse for script-to-audio matching |
| **Studio UI & Canvas** | `studio_ui/views/` | Direct reuse for visual preview & inspection |

---

## 7. Existing Limitations & Architectural Gaps

1. **Asset Sheet Adapter Absence**:
   - `asset_sheet_extractor_v2_output` produces a specific schema (`assets.json`, `report.json`, with fields like `asset_id`, `bbox`, `reasons`, `diagnostics`).
   - The TCM-DS v2 pipeline consumes `visual_manifest.json` (`VisualEntity`, `NormalizedDemandMetrics`).
   - *Gap*: Need a direct, zero-loss adapter converting `assets.json` + `report.json` into `visual_manifest.json`.
2. **Hardcoded Production Scripts**:
   - Several sections rely on per-topic python scripts (`run_01_pareidolia_osas_pipeline.py` ... `run_07_conclusion_osas_pipeline.py`) where staging coordinates and timing lists were hand-curated.
   - *Gap*: The workflow needs to be driven declaratively from the extracted assets and timing analysis, without manual per-section script duplication.
3. **Motion Graphics Vocabulary**:
   - Secondary animation in `DynamicSectionEngine` currently supports 5 kinetic types (`slide_down`, `slide_up`, `jelly_pop`, `pulse_pop`, `organic_grow`).
   - *Gap*: Can be extended with rotation/spin, zoom-in punch, fade-blur, and multi-asset stagger reveals.
4. **Camera Paths**:
   - Camera motion in OSAS v3.1 scripts is predominantly horizontal ($dY = 0$).
   - *Gap*: Motion graphics benefits from 2D camera framing (pan-and-zoom to group bounding boxes).

---

## 8. File Classification

### A. Files That MUST NOT Be Rewritten (Protected Core)
- `core/render_engine/render/concentric_engine.py` (Proprietary orbital inking algorithm)
- `core/render_engine/render/hand_compositor.py` (Optimized alpha hand overlay)
- `production_engine/mix_section_audio.py` (Calibrated audio ducking & SFX balance)
- `section_timing/transcription/faster_whisper_engine.py` (Local Faster-Whisper pipeline)
- `core/contracts/visual_manifest.py` (Canonical visual contract schema)
- `core/contracts/narrative_map.py` (Canonical narrative contract schema)
- `core/contracts/render_plan.py` (Canonical execution contract schema)
- `asset_sheet_extractor_v2_output/*` (Existing validated asset extraction artifacts)

### B. Files That Can Be Extended / Adapted
- `production_engine/dynamic_section_engine.py` (Add new motion animation presets and 2D camera interpolation)
- `core/contracts/render_plan.py` (Support motion graphics transform keyframes)
- `core/scheduling/constraint_scheduler.py` (Support multi-element motion beat grouping)
- `studio_ui/views/studio_timeline.py` (Display new motion beat tracks)

---

## 9. Conclusion of Audit

The repository architecture is exceptionally solid and ready for the new motion graphics workflow. The foundations—audio synchronization, asset extraction, deterministic scheduling, and hardware-accelerated rendering—are already fully implemented and verified across 7 complete documentary sections. Proceeding to implementation will only require surgical integration adapters.
