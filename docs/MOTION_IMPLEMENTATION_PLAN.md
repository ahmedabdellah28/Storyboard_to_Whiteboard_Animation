# Motion Graphics & Whiteboard System: Minimum-Change Implementation Plan

**Document:** `docs/MOTION_IMPLEMENTATION_PLAN.md`  
**Date:** October 2026  
**Auditor & Architect:** Antigravity Agent  
**Repository:** `image_to_animate`  
**Target Pipeline:**  
`Storyboard → AI-generated Animation Asset Sheet → existing Python asset extraction → extracted transparent PNG assets → local script/audio timing analysis → semantic visual beats → motion planning → camera planning → deterministic rendering`

---

## 1. Principles & Non-Negotiable Constraints

1. **Zero External AI Image Analysis**: No external vision APIs, no sending images to multimodal LLMs. All image metrics (edges, contours, bounding boxes, background separation) are computed purely locally via OpenCV and NumPy.
2. **Zero Engine Rewrites**: The existing, production-proven `DynamicSectionEngine`, `concentric_engine`, `hand_compositor`, and Faster-Whisper modules remain untouched in their core algorithms.
3. **Compatibility Adapters Over Modifications**: The existing Asset Sheet Extractor output format (`asset_sheet_extractor_v2_output`) will be ingested via a dedicated adapter without changing the extractor's internal logic.
4. **Deterministic Physical Truth**: Scheduling, timing windows, lead-in offsets, motion easing, and camera trajectories must execute 100% deterministically from contract specifications.
5. **Single Source of Truth**: All data exchanges flow through the established TCM-DS contract models (`VisualManifest`, `NarrativeVisualMap`, `FinalRenderPlan`).

---

## 2. Target Workflow & Minimal-Change Bridge

```
┌────────────────────────────────────────────────────────────────────────┐
│                   TARGET MOTION GRAPHICS WORKFLOW                      │
└────────────────────────────────────────────────────────────────────────┘

 [1] Storyboard / AI Animation Asset Sheet
                     │
                     ▼
 [2] Existing Python Asset Extractor  (No Changes)
                     │
                     ▼
     Extracted Transparent PNG Assets
     + `assets.json` & `report.json`
                     │
                     ▼
 [3] Asset Sheet Adapter ──────────────► Contract 1: visual_manifest.json
                                                    │
 [4] Local Script & Audio Timing                    │
     • Faster-Whisper (whisper.json)                │
     • Local Token/Anchor Resolver ─────────────────┤
                     │                              │
                     ▼                              ▼
 [5] Semantic Visual Beats ────────────► Contract 2: narrative_visual_map.json
                     │                              │
                     ▼                              │
 [6] Motion Planning & Choreography                 │
     (Inking vs Kinetic Presets)                    │
                     │                              │
                     ▼                              │
 [7] Camera Planning & Viewports                    │
     (2D Framings + JIT Pans)                       │
                     │                              │
                     ▼                              ▼
 [8] Constraint Scheduler ─────────────► Contract 3: final_render_plan.json
                                                    │
                                                    ▼
 [9] Deterministic Rendering via DynamicSectionEngine
     • NVENC 1080p 30 FPS Render
     • Synchronized SFX Ducked Audio Master
```

---

## 3. Implementation Phases

### Phase 1: Asset Sheet Ingestion & Adapter Layer (`AssetSheetAdapter`)
* **Objective**: Ingest the existing Asset Sheet Extractor output directory (`asset_sheet_extractor_v2_output/` or per-section asset directories) and convert it into the canonical `VisualManifest` (Contract 1).
* **New Module Required**: `core/vision/asset_sheet_adapter.py`
* **Input**:
  - `assets/` (transparent PNGs)
  - `assets.json` (containing `asset_id`, `bbox`, `crop_size`, `diagnostics`)
  - `report.json` (containing background parameters and metadata)
* **Output**:
  - `visual_manifest.json` conforming to `core/contracts/visual_manifest.py`
* **Adapter Logic**:
  - Maps `assets.json` entries to `VisualEntity` objects.
  - Maps `diagnostics.fill_ratio`, `aspect_ratio`, `contour_complexity` directly to `NormalizedDemandMetrics`.
  - Assigns visual entity ordering from `bbox` coordinates (top-to-bottom, right-to-left for Arabic or left-to-right).
  - Flags composite scenes vs atomic props based on `reasons` (e.g. `possible_touching_assets`).

### Phase 2: Local Script & Audio Timing Analysis
* **Objective**: Generate ground-truth word and sentence timestamps locally without any external LLM call.
* **Modules Reused**:
  - `section_timing/transcription/faster_whisper_engine.py` (Local Faster-Whisper with word timestamps)
  - `section_timing/speech/speech_beat_detector.py` (Pause and clause detection)
  - `core/sync/arabic_matcher.py` (Arabic token normalization)
* **Execution**:
  - Run `FasterWhisperEngine.transcribe()` to produce `timing/whisper.json`.
  - Extract sentence boundary clauses and pauses (`pause_detector.py`).
  - Calculate total speech duration and pause budget.

### Phase 3: Semantic Visual Beats & Concept Binding
* **Objective**: Bind visual entities from `VisualManifest` to script segments, creating `NarrativeVisualMap` (Contract 2).
* **Modules Reused**:
  - `core/sync/anchor_resolver.py` (`DeterministicAnchorResolver`)
  - `core/contracts/narrative_map.py` (`NarrativeVisualMap`, `NarrativeConcept`)
* **New Module Required**: `core/narrative/semantic_beat_binder.py`
* **Binding Logic**:
  - Uses local rule-based entity naming or declarative mapping table to assign narrative roles (`hero`, `support`, `context`, `decorative`).
  - Associates each concept with 2–4 anchor search keywords.
  - Executes `DeterministicAnchorResolver.resolve_map()` against Whisper words to lock in exact timestamps.
  - Generates `narrative_visual_map.json`.

### Phase 4: Motion Planning & Animation Choreography
* **Objective**: Assign appropriate motion styles (outside-in inking vs kinetic motion graphics) to each visual beat.
* **Modules Reused**:
  - `core/scheduling/constraint_scheduler.py`
  - `production_engine/dynamic_section_engine.py` (existing animation engines)
* **Extensions to Existing Files**:
  - Extend `production_engine/dynamic_section_engine.py` to register additional motion graphics presets:
    - `pop_zoom`: Fast scale pop with slight overshoot.
    - `stagger_fade`: Alpha ramp with horizontal slide for multi-part items.
    - `spin_settle`: Subtle rotation ease (5–10 degrees) into place.
* **Choreography Rules**:
  - Maximum **1 Hero inking element** (`outside_in_pen`) per scene.
  - Secondary elements assigned kinetic motion graphics presets.
  - Lead-in offset fixed at **200ms before spoken anchor** (`t_start = word_t - 0.20s`).
  - Explanation hold: Elements stay visible on screen until scene transition.

### Phase 5: Camera Planning & Dynamic Viewport Framing
* **Objective**: Calculate collision-free world canvas placements and camera trajectories.
* **Modules Reused**:
  - `DynamicSectionEngine.calculate_camera_pans()`
  - `DynamicSectionEngine.build_horizontal_camera_trajectory()`
  - `core/contracts/render_plan.py` (`CameraKeyframe`, `ViewportPlacement`)
* **New / Enhanced Logic**:
  - **Scene Clustering**: Groups 2 to 4 related visual beats into a spatial scene zone.
  - **Zoning Geometry**: Centers each zone horizontally at intervals of 3200 px (`cam_y = 800.0`, `cam_zoom = 0.65`).
  - **Just-In-Time (JIT) Pan Calculation**:
    - Pan concludes at: `pan_end = next_scene_start - 0.05s`.
    - Pan duration: `0.30s – 0.50s`.
    - Camera holds stationary on the scene throughout all spoken narration.
  - Compiles full `ExecutionTracks` into `final_render_plan.json` (Contract 3).

### Phase 6: Deterministic Rendering & Deliverables
* **Objective**: Execute hardware-accelerated video rendering and audio mixing.
* **Modules Reused**:
  - `DynamicSectionEngine.render_section()` (FFmpeg NVENC 1080p @ 30 FPS)
  - `DynamicSectionEngine.mix_master_audio()` / `production_engine/mix_section_audio.py`
* **Execution**:
  - Generates synchronized SFX cues (marker drawing, pops, whooshes, chimes).
  - Mixes master audio with automatic voiceover ducking (-3 dB).
  - Pre-caches solid inking orbital paths for Hero elements.
  - Renders final 1080p MP4 deliverable.

---

## 4. Minimum-Change Component Matrix

| Pipeline Step | Change Type | File to Touch / Add | Rationale |
|---|---|---|---|
| **Asset Sheet Adapter** | **NEW** (Minimal) | `core/vision/asset_sheet_adapter.py` | Bridges `asset_sheet_extractor_v2_output` to `VisualManifest` without modifying extractor |
| **Semantic Beat Binder** | **NEW** (Minimal) | `core/narrative/semantic_beat_binder.py` | Binds script sentences to visual entities deterministically |
| **Motion Presets** | **EXTEND** | `production_engine/dynamic_section_engine.py` | Adds motion graphics entrance presets to existing blend loop |
| **Pipeline Runner** | **NEW** | `scripts/run_motion_graphics_pipeline.py` | Unified end-to-end command runner for the workflow |
| **Inking Engine** | **KEEP AS-IS** | `core/render_engine/render/concentric_engine.py` | Proven hand-inking algorithms must not be touched |
| **Hand Compositor** | **KEEP AS-IS** | `core/render_engine/render/hand_compositor.py` | Proven hand compositing must not be touched |
| **Audio Ducking** | **KEEP AS-IS** | `production_engine/mix_section_audio.py` | Calibrated SFX & voiceover mixing must not be touched |
| **Whisper Engine** | **KEEP AS-IS** | `section_timing/transcription/faster_whisper_engine.py` | Ground truth transcription must not be touched |

---

## 5. Architectural Risk Analysis & Mitigations

| Risk | Impact | Mitigation Strategy |
|---|---|---|
| **Touching/Clustered Assets in Asset Sheet** | Extractor might group adjacent icons into a single crop | `asset_sheet_extractor_v2_output/report.json` already flags `possible_touching_assets` and `possible_composites`. The adapter reads these diagnostics and handles them as composite scenes or prompts review. |
| **Arabic Text Misalignment in Speech Anchors** | Inking triggers at incorrect time if Whisper transcription has dialectal variations | Use `core/sync/arabic_matcher.py` with multi-tier fuzzy matching (Exact → Normalized → Token → Phonetic). Falls back gracefully to sentence-level timing if token confidence is low. |
| **Camera Jerk or Blank Canvas** | Camera pans too early leaving blank white space | Strictly enforce the **Just-In-Time (JIT) Pan Rule**: Camera never moves until 0.40s before the next element starts drawing. Minimum explanation hold of 1.5s on all finished elements. |
| **Drawing Sound Overflow** | SFX marker sound continues after drawing stops | The duration of the marker SFX is explicitly clamped to the active drawing duration (`draw_dur = round(dur * 0.90, 2)`), followed immediately by a settlement pop. |
| **NVENC Hardware Encoder Unavailable** | Render failure on environments without NVIDIA GPU | `DynamicSectionEngine` has an automated fallback to CPU `libx264 ultrafast` if NVENC process fails to initialize. |

---

## 6. Verification & Test Plan

1. **Contract Ingestion Test**:
   - Verify `AssetSheetAdapter` ingests `asset_sheet_extractor_v2_output/assets.json` and outputs valid `visual_manifest.json` with matching hash.
2. **Deterministic Alignment Test**:
   - Verify all narrative anchors resolve against `whisper.json` with 100% monotonic progression (no backwards time jumps).
3. **Collision & Viewport Safe Test**:
   - Validate that elements within a scene maintain the required 50–100 px buffer and never exceed the 2950 px visible world viewport at zoom 0.65.
4. **End-to-End Golden Baseline Test**:
   - Run complete pipeline from asset sheet to 1080p MP4. Validate frame count matches audio duration, audio sync is within ±50ms, and render output size is valid.
