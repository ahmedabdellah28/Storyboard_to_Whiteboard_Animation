# Whiteboard Studio — Forensic Repository Audit (Phase 0)

> **Date:** 2026-09-29  
> **Status:** AUDIT — No behavior changes  
> **Purpose:** Comprehensive inventory of the existing codebase to inform the Whiteboard Studio migration

---

## 1. Current Architecture Overview

### 1.1 Repository Layout

```
e:\image_to_animate\
├── core/                           # Production Core — REUSE
│   ├── api/                        # Gemini client management, key pooling, rate limiting
│   ├── artifacts/                  # ArtifactStore, ArtifactIdentity, CacheValidator, DependencyGraph
│   ├── audio/                      # WAV utilities
│   ├── config/                     # Settings, env_loader (PROJECT_ROOT, paths, defaults)
│   ├── contracts/                  # TCM-DS v2 contracts (VisualManifest, NarrativeMap, RenderPlan, etc.)
│   ├── narrative/                  # NarrativeDirector — AI semantic reasoning
│   ├── orchestration/              # ProductionOrchestrator, SectionWorker, TaskDAGExecutor, ResourcePools
│   ├── providers/                  # ASR (Whisper), TTS (Gemini), Translation
│   ├── scheduling/                 # VisualChoreographer, ConstraintScheduler, VisualBeatScheduler
│   ├── state/                      # ProjectState, SectionState, TaskState, StateStore, Transitions
│   ├── sync/                       # Cross-module sync utilities
│   ├── telemetry/                  # TaskTimer, counters, reporter
│   ├── validation/                 # Empty — __init__.py only (GAP)
│   └── vision/                     # AdaptiveCandidateExtractor, BackgroundRemover, DemandEstimator
│
├── production_engine/              # Production Pipeline Steps — REUSE
│   ├── universal_section_pipeline.py  # UniversalSectionPipeline (7 modular steps)
│   ├── dynamic_section_engine.py      # DynamicSectionEngine (camera, render, SFX, audio mix)
│   ├── dynamic_storyboard_extractor.py # Storyboard → assets extraction
│   ├── dynamic_speech_synchronizer.py  # Speech-asset synchronization
│   ├── dynamic_layout_planner.py       # Micro-zoning layout planner
│   ├── voiceover_engine.py             # Zero-truncation TTS generation
│   ├── audio_aligner.py               # Audio alignment
│   ├── mix_section_audio.py            # SFX mixing
│   ├── merge_master_sections.py        # Master documentary assembly
│   ├── merge_sections_dissolve.py      # Dissolve transitions between sections
│   ├── export_section_reels.py         # Reel export
│   ├── gemini_client_pool.py           # Gemini API client pool
│   └── sfx/                            # Sound effect assets
│
├── kivy/                           # Current UI — REPLACE
│   ├── main.py                     # SketchAnimationApp (KivyMD, 452 lines)
│   ├── main_layout.kv              # Kivy layout file
│   ├── engine/                     # Render engine (REUSE, NOT replace)
│   │   ├── render/                 # DeepPipelineEngine, ConcentricEngine, HandCompositor, Renderer
│   │   ├── camera/                 # Camera, CameraAnimator
│   │   ├── animation/              # DrawingOrder, StrokeAnimator, FillAnimator, Easing
│   │   ├── pipeline/               # DynamicWhiteboardRenderer, DynamicSRTChoreographer
│   │   ├── audio/                  # Audio processing
│   │   ├── beat/                   # Beat matching
│   │   ├── core/                   # Scene, Project models
│   │   ├── video/                  # Video processing
│   │   ├── planning/               # Planning utilities
│   │   ├── processing/             # Processing utilities
│   │   └── debug/                  # Debug utilities
│   ├── ui/                         # Current UI layer — REPLACE
│   │   ├── screens/                # HomeScreen, LoadingScreen, GridSetupScreen, SceneScreen
│   │   ├── canvas/                 # CanvasView, CoordinateTransform, VideoPlayer, tools/
│   │   ├── widgets/                # InspectorPanel, ObjectCard, ObjectList, SettingsDialog
│   │   ├── services/               # AnalysisService, DialogService, RenderService
│   │   ├── state/                  # ProjectState (UI), Commands
│   │   └── theme.py                # Kivy theme
│   └── licensing/                  # License guard
│
├── pre_render_director/            # AI Pre-Render Director — REUSE
├── tests/                          # 34 test files — EXTEND
├── docs/                           # 11 doc files — EXTEND
└── Various run_*.py files          # Legacy per-section runners
```

### 1.2 Canonical Runtime Path

```
ProductionOrchestrator (core/orchestration/orchestrator.py)
  └── run_section() / run_project()
       └── SectionWorker (core/orchestration/section_worker.py)
            ├── validate_inputs()     → {script, storyboard, voice} presence
            ├── build_section_dag()   → construct ExecutableTask DAG (8 tasks)
            └── TaskDAGExecutor (core/orchestration/task_dag.py)
                 ├── Topological sort for execution order
                 ├── Parallel dispatch via ThreadPoolExecutor
                 ├── Resource gating via ResourcePoolManager semaphores
                 ├── Artifact cache (ArtifactStore) hit/miss evaluation
                 ├── State persistence (StateStore) per task
                 ├── Retry policy (configurable per task)
                 └── Telemetry timing
```

### 1.3 Section Production DAG (8 Tasks)

```
TTS ──────────────────────────┐
  │                           │
  └→ Whisper ────────────┐    │
                         │    │
Extraction ──────────────┤    │
                         │    │
                    Layout & Sync
                         │
                    Pre-Render Director
                         │
                 ┌───────┴───────┐
                 │               │
            Audio Mix        Render
                 │               │
                 └───────┬───────┘
                         │
                    Deliverable
```

---

## 2. Current Runtime Path Detail

| Step | Task ID Pattern | Component | Resource | Module |
|------|----------------|-----------|----------|--------|
| 0 | `{sec}.tts` | tts | NETWORK_API | `voiceover_engine.generate_voiceover_zero_truncation` |
| 1 | `{sec}.whisper` | whisper | CPU_HEAVY | `section_timing/main.py` (subprocess) |
| 2 | `{sec}.extraction` | extraction | CPU_HEAVY | `DynamicStoryboardExtractor.extract_assets()` |
| 3 | `{sec}.layout_and_sync` | layout | CPU_HEAVY | `DynamicSpeechSynchronizer + DynamicLayoutPlanner` |
| 4 | `{sec}.pre_render_director` | validation | NETWORK_API | `pre_render_director.main` (subprocess) |
| 5 | `{sec}.audio_mix` | audio_mix | DISK_IO | `DynamicSectionEngine.mix_master_audio()` |
| 6 | `{sec}.render` | render | GPU_RENDER | `DynamicSectionEngine.render_section()` |
| 7 | `{sec}.deliverable` | deliverable | DISK_IO | `shutil.copyfile` to deliverables/ |

---

## 3. Existing Reusable Modules

### REUSE — Do Not Rewrite

| Module | Path | Purpose |
|--------|------|---------|
| ProductionOrchestrator | `core/orchestration/orchestrator.py` | Central section lifecycle manager |
| SectionWorker | `core/orchestration/section_worker.py` | DAG builder for section production |
| TaskDAGExecutor | `core/orchestration/task_dag.py` | Parallel task dispatch with caching |
| ResourcePoolManager | `core/orchestration/resource_pools.py` | Semaphore-based concurrency control |
| ProjectState / SectionState / TaskState | `core/state/project_state.py` | State models with lifecycle |
| StateStore | `core/state/state_store.py` | JSON persistence with atomic writes |
| LifecycleStatus + Transitions | `core/state/transitions.py` | 8-state machine with validated transitions |
| ArtifactStore | `core/artifacts/artifact_store.py` | Thread-safe artifact catalog + cache |
| ArtifactIdentity | `core/artifacts/artifact_identity.py` | Content-addressable hashing |
| CacheValidator | `core/artifacts/cache_validator.py` | Artifact freshness validation |
| DependencyGraph | `core/artifacts/dependency_graph.py` | DAG + transitive invalidation |
| TCM-DS v2 Contracts | `core/contracts/*.py` | VisualManifest, NarrativeMap, RenderPlan, etc. |
| NarrativeDirector | `core/narrative/narrative_director.py` | AI semantic mapping |
| VisualChoreographer | `core/scheduling/visual_choreographer.py` | Deterministic timing scheduler |
| ConstraintScheduler | `core/scheduling/constraint_scheduler.py` | Constraint-aware scheduling |
| AdaptiveCandidateExtractor | `core/vision/adaptive_candidate_extractor.py` | Storyboard asset extraction |
| VisualReviewerEngine | `core/vision/visual_reviewer_engine.py` | AI extraction review |
| DemandEstimator | `core/vision/demand_estimator.py` | Drawing complexity estimation |
| UniversalSectionPipeline | `production_engine/universal_section_pipeline.py` | 7-step modular pipeline |
| DynamicSectionEngine | `production_engine/dynamic_section_engine.py` | Camera + render + SFX |
| VoiceoverEngine | `production_engine/voiceover_engine.py` | Zero-truncation TTS |
| DeepPipelineEngine | `kivy/engine/render/deep_pipeline_engine.py` | Production renderer |
| HandCompositor | `kivy/engine/render/hand_compositor.py` | Hand drawing overlay |
| Camera/CameraAnimator | `kivy/engine/camera/*.py` | Camera system |
| Animation modules | `kivy/engine/animation/*.py` | Stroke/fill/drawing animation |
| DynamicWhiteboardRenderer | `kivy/engine/pipeline/dynamic_whiteboard_renderer.py` | Whiteboard render pipeline |
| Client/Key Management | `core/api/*.py` | Gemini API management |
| Providers (ASR/TTS) | `core/providers/*.py` | Whisper + TTS providers |
| Config/Settings | `core/config/*.py` | Project paths + defaults |
| Telemetry | `core/telemetry/*.py` | Performance timing + counters |

### REPLACE — Current UI Only

| Module | Path | Purpose |
|--------|------|---------|
| SketchAnimationApp | `kivy/main.py` | KivyMD app shell |
| HomeScreen | `kivy/ui/screens/home_screen.py` | Project start screen |
| GridSetupScreen | `kivy/ui/screens/grid_setup_screen.py` | Grid configuration |
| SceneScreen | `kivy/ui/screens/scene_screen.py` | Scene editing |
| LoadingScreen | `kivy/ui/screens/loading_screen.py` | Loading indicator |
| CanvasView | `kivy/ui/canvas/canvas_view.py` | Canvas rendering |
| Inspector/Widgets | `kivy/ui/widgets/*.py` | Property panels |
| UI State | `kivy/ui/state/*.py` | UI-specific state |
| UI Services | `kivy/ui/services/*.py` | UI workflow services |
| Theme | `kivy/ui/theme.py` | Kivy theme |

---

## 4. Existing Duplicated / Redundant Modules

| Issue | Details |
|-------|---------|
| **Dual ProjectState** | `core/state/project_state.py` (production) vs `kivy/ui/state/project_state.py` (UI). Independent implementations with different fields |
| **Dual DependencyGraph** | `core/artifacts/dependency_graph.py` has `build_default_section_dag()` which duplicates the DAG shape in `SectionWorker.build_section_dag()`. Shapes differ slightly |
| **Legacy run scripts** | 10+ per-section runner scripts bypassing the orchestrator |
| **Pipeline.run() delegate** | `UniversalSectionPipeline.run()` delegates to `SectionWorker.run()` — circular dependency adapter |
| **Gemini client pool** | `production_engine/gemini_client_pool.py` exists alongside `core/api/client_manager.py` |

---

## 5. Current State Behavior

### 5.1 LifecycleStatus Enum (8 states)

```
PENDING → QUEUED → RUNNING → COMPLETED
                           → FAILED → RETRYING → RUNNING
                                    → PENDING (reset)
         COMPLETED → INVALIDATED → PENDING
         PENDING → SKIPPED
```

### 5.2 State Store

- **Storage:** JSON files in `.state/` directory, one file per project
- **Atomic writes:** Uses `.tmp` + `os.replace()`
- **Thread safety:** `threading.Lock()` around all operations
- **In-memory cache:** `Dict[str, ProjectState]`
- **Granularity:** Project → Section → Task (3 levels)

### 5.3 Gaps

| Gap | Impact |
|-----|--------|
| No `NEEDS_REVIEW` state | Plan requires it for extraction/semantic review gates |
| No `CANCELLED` state | Plan requires real cancellation |
| No revision tracking | State has no revision/version field on sections or tasks |
| No stage-level sub-states | Processing states are flat (no per-stage PENDING/RUNNING/READY) |
| Section has no sub-stage states | Only overall section status, not per-pipeline-stage |
| No user-edit tracking | No command history, no undo/redo metadata |

---

## 6. Current Cache Behavior

### 6.1 ArtifactStore

- **Location:** `.artifacts_cache/artifacts_manifest.json`
- **Identity:** Content-addressable via `compute_artifact_hash(component, inputs, config)`
- **Validation:** File exists + non-empty + size matches registered size
- **Registration:** Task executor registers after successful action
- **Lookup:** DAG executor checks before dispatching task

### 6.2 Gaps

| Gap | Impact |
|-----|--------|
| No schema validation | "file exists + size matches" is insufficient per plan Section 16 |
| No dependency chain validation | Artifact validity doesn't verify upstream dependencies |
| No revision awareness | Cache doesn't track which input revision produced the artifact |
| No expiry/eviction | No LRU or budget-based cache cleanup |
| No thumbnail/preview cache | Only production artifacts are cached |

---

## 7. Current Resource Management

### 7.1 ResourcePoolManager

```
NETWORK_API  → 4 slots (Gemini API)
CPU_HEAVY    → 2 slots (Whisper, OpenCV)
GPU_RENDER   → 1 slot  (NVENC encoder)
DISK_IO      → 3 slots (FFmpeg, file I/O)
DEFAULT      → 4 slots (fallback)
```

### 7.2 Gaps

| Gap | Impact |
|-----|--------|
| No hardware detection | Hardcoded slot counts, no AUTO mode |
| No RAM budget | No memory pressure tracking |
| No GPU detection | No check for NVENC availability |
| No priority system | All tasks get equal resource priority |
| No background throttling | No interactive vs background priority differentiation |
| No cancellation propagation | Semaphores don't support cooperative cancellation |

---

## 8. Existing Failure Points

| Component | Failure Mode | Current Handling | Plan Required |
|-----------|-------------|-----------------|---------------|
| TTS (Gemini API) | Rate limit, timeout, auth | Retry via `retry_policy` in DAG | Granular chunk retry + clear user messaging |
| Whisper (subprocess) | Process crash, OOM | stderr check | Isolated process + real retry |
| Extraction (OpenCV) | Merged elements, bad segmentation | None — no review gate | USER_REVIEW_REQUIRED + review UI |
| Pre-Render Director | subprocess + mock-ai | stderr warning only | Real validation with actionable feedback |
| Render (NVENC) | GPU crash, encoder failure | Task failure → section failure | Process isolation + crash recovery |
| FFmpeg (subprocess) | Process crash, corrupt output | Exit code check only | Post-render QA (duration, frames, streams) |
| Master Assembly | Missing sections | FileNotFoundError | Graceful section-level status |
| State File | Corruption | Try/except with warning | Backup + recovery |

---

## 9. Existing Rendering Path

```
DynamicSectionEngine.render_section()
  │
  ├── prepare_staging_and_camera()    → camera trajectory + element staging
  ├── generate_sfx_from_staging()     → SFX cue list
  ├── mix_master_audio()              → voice + SFX → master_audio.wav
  │
  └── render_section()
       │
       ├── DeepPipelineEngine         → Frame-by-frame whiteboard rendering
       │     ├── StrokeAnimator       → Inking effect
       │     ├── FillAnimator         → Color fill
       │     ├── HandCompositor       → Hand overlay
       │     ├── CameraAnimator       → Camera pan/zoom
       │     └── DrawingOrder         → Element sequencing
       │
       └── FFmpeg / NVENC             → Video encoding (1080p H.264)
```

**Key principle:** This rendering path MUST NOT be duplicated. The new UI will consume the same render contracts for both preview and final render, varying only in resolution/quality/encoding.

---

## 10. UI Replacement Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                    REPLACE (New PySide6/QML UI)             │
│                                                              │
│  kivy/main.py, main_layout.kv                                │
│  kivy/ui/screens/*.py                                        │
│  kivy/ui/canvas/*.py                                         │
│  kivy/ui/widgets/*.py                                        │
│  kivy/ui/services/*.py                                       │
│  kivy/ui/state/*.py                                          │
│  kivy/ui/theme.py                                            │
│  kivy/screens/*.py                                           │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                    KEEP (Render Engine)                       │
│                                                              │
│  kivy/engine/**/*.py                                         │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                    KEEP (Core + Production)                   │
│                                                              │
│  core/**/*.py                                                │
│  production_engine/*.py                                      │
│  pre_render_director/                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | Engine modules (`kivy/engine/`) may have Kivy import dependencies | HIGH | Audit imports; extract engine to standalone package if needed |
| R2 | Replacing Kivy removes the only functional UI during transition | HIGH | Keep Kivy app runnable; new UI canonical only after feature parity |
| R3 | PySide6 + QML learning curve | MEDIUM | Start with component library + simple screens |
| R4 | State model changes could break existing `.state` JSON files | MEDIUM | Migration function for existing state files |
| R5 | DependencyGraph vs SectionWorker DAG divergence | LOW | Unify into single canonical DAG definition |
| R6 | Subprocess-based steps prevent fine-grained progress reporting | MEDIUM | Add progress callback protocol or IPC |
| R7 | Gemini client pool duplication | LOW | Remove production_engine duplicate |
| R8 | No post-render QA — corrupt outputs silently published | HIGH | Implement post-render validation before publish |
| R9 | No real cancellation support | HIGH | Add cooperative cancellation tokens |
| R10 | UI thread safety with PySide6 | HIGH | Use signals/slots pattern strictly |

---

## 12. Migration Strategy

### Phase Approach

```
Phase 0:  Audit + Architecture Specification          ← CURRENT
Phase 1:  Core extensions (state, validation, revision, NEEDS_REVIEW/CANCELLED)
Phase 2:  Invalidation graph + revision system
Phase 3:  Validation + Recovery system
Phase 4:  ResourceGovernor + WorkerManager + cancellation
Phase 5:  PySide6 app shell + Project Browser
Phase 6:  Core Bridge + Processing Monitor
Phase 7:  Extraction Review UI
Phase 8:  Voice Review UI
Phase 9:  Semantic Review UI
Phase 10: Studio Editor (Canvas, Shots, Assets, Inspector, Text)
Phase 11: Preview System
Phase 12: Render Integration + Post-Render QA
Phase 13: Master Studio
Phase 14: Performance Hardening
Phase 15: Migration Cleanup (remove Kivy UI)
```

### Migration Rules

1. **Kivy app stays runnable** until Phase 15
2. **No production pipeline changes** in Phases 0-4
3. **Engine modules** (`kivy/engine/`) extracted to shared location for both UIs
4. **State store format** upgraded with backward-compatible migration
5. **Feature parity verified** before old UI removal
6. **Tests run at every phase boundary**

---

## Summary of Key Findings

| Area | Current State | Target State | Gap Severity |
|------|--------------|-------------|-------------|
| **State Machine** | 8 states, no NEEDS_REVIEW/CANCELLED | Plan requires NEEDS_REVIEW, CANCELLED, per-stage substates | HIGH |
| **Validation** | Empty module | 13+ validators required | HIGH |
| **Recovery** | Basic retry in DAG executor | Full recovery system with error classification | HIGH |
| **Editing** | No undo/redo, no command system | Command-based editing with revision tracking | HIGH |
| **Preview** | No preview system | 4-level preview (Interactive, Camera, Section, Project) | HIGH |
| **UI Technology** | Kivy/KivyMD | PySide6 + QML | COMPLETE REPLACEMENT |
| **Resource Management** | Hardcoded semaphores | Hardware-aware ResourceGovernor with priority | MEDIUM |
| **Post-Render QA** | None | Full video/audio validation | HIGH |
| **Cancellation** | None | Cooperative cancellation with resource cleanup | HIGH |
| **Artifact Validation** | File exists + size | Schema + hash + dependency chain + revision | MEDIUM |
| **Cache** | No eviction, no thumbnails | LRU + memory budget + preview cache | MEDIUM |
| **Tests** | 34 test files (mixed coverage) | Unit + Integration + Race + Resource + UI tests | EXTEND |
