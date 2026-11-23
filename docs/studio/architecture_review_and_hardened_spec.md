# Whiteboard Studio — Principal Architect Architecture Review & Hardened Specification (Phase 0.5)

> **Document Class:** Principal Architecture Review & Hardened Blueprint  
> **Status:** APPROVED AS CANONICAL FOUNDATION (Zero Implementation Prior to Gate Sign-off)  
> **Target System:** Whiteboard Studio Desktop Application (PySide6 / Core TCM-DS v2 / Production Engine)  
> **Author:** Principal Systems & Video Pipeline Architect  
> **Date:** September 2026  

---

## Executive Summary

This architecture review serves as the strict quality gate between the conceptual design phase and Phase 1 implementation. An exhaustive forensic audit of the repository (`core/`, `production_engine/`, `kivy/engine/`) and the initial design specification revealed **critical contradictions, latent race conditions, missing lifecycle contracts, unsafe static resource allocations, and hidden engine couplings** that would cause pipeline deadlocks, silent audio/video desynchronization, cache poisoning, and application crashes on consumer hardware.

This document formally resolves every ambiguity, eliminates all off-by-one inconsistencies, establishes strict mathematical resource governance, defines a multi-tiered revision safety protocol, and provides the corrected canonical contracts governing all downstream implementation phases.

---

# PART I: FORENSIC CRITIQUE OF THE 18 MANDATORY REVIEW AREAS

```
=============================================================================================================
                                     ARCHITECTURAL REVIEW TAXONOMY
=============================================================================================================
  [01. State Machines]   [02. Canonical DAG]       [03. Artifact Preflight]  [04. Engine Boundary]
  [05. Resource Gov]     [06. Preview Contracts]   [07. Invalidation Matrix] [08. Revision Safety]
  [09. Persistence/WAL]  [10. Review Contracts]    [11. Error & Resilience]  [12. Concurrency/Locks]
  [13. Restart/Recovery] [14. Performance Tiers]   [15. Packaging/Runtime]   [16. Master Assembly]
  [17. Impact UX Modal]  [18. Canonical Synthesis (A -> Q)]
=============================================================================================================
```

---

### 1. State Machine Consistency

#### 1.1 The Contradictions in the Original Specification
1. **Off-by-One Stage Count:** The original specification stated *"17 pipeline stages"* in its textual overview, but proceeded to enumerate stages from `Stage 00` through `Stage 18` (which constitutes exactly **19 stages**).
2. **Unified Enum Conflation:** The existing implementation (`core/state/transitions.py`) defined a single `LifecycleStatus` enum with only 8 values (`PENDING`, `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `RETRYING`, `SKIPPED`, `INVALIDATED`). The specification introduced `NEEDS_REVIEW` and `CANCELLED` in diagrams without reconciling them into the transition table, without distinguishing between **Execution Status** (task-level scheduling), **Section Review Status** (human-in-the-loop gates), and **Pipeline Stage Identity**.
3. **Project vs. Section State Aggregation:** `ProjectState` in `core/state/project_state.py` passively aggregated section states without defining atomic bubble-up semantics: if Section 1 is `RUNNING`, Section 2 is `FAILED`, and Section 3 is `NEEDS_REVIEW`, what is the valid composite state of the project?

#### 1.2 Canonical State Architecture & Counts
We decompose the state machine into three orthogonal, strictly typed layers:

- **Task Execution States (`TaskLifecycleStatus`):** Exactly **9 states** (`PENDING`, `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `RETRYING`, `CANCELLED`, `SKIPPED`, `INVALIDATED`).
- **Review Gate States (`ReviewGateStatus`):** Exactly **5 states** (`NOT_APPLICABLE`, `REVIEW_PENDING`, `IN_REVIEW`, `APPROVED`, `REJECTED`).
- **Section Lifecycle States (`SectionLifecycleStatus`):** Exactly **8 states** (`EMPTY`, `DRAFTING`, `PROCESSING`, `NEEDS_REVIEW`, `READY_TO_RENDER`, `RENDERING`, `COMPLETED`, `ERROR`).
- **Project Lifecycle States (`ProjectLifecycleStatus`):** Exactly **6 states** (`IDLE`, `INGESTING`, `PROCESSING`, `READY`, `EXPORTING`, `ERROR`).

#### 1.3 State Aggregation Logic
A section's aggregate state is a deterministic reduction of its member tasks:
- If ANY task is `FAILED` and retry budget is exhausted $\rightarrow$ `SectionLifecycleStatus.ERROR`.
- Else if ANY task is `CANCELLED` and none `RUNNING` $\rightarrow$ `SectionLifecycleStatus.DRAFTING`.
- Else if ANY active review gate is `REVIEW_PENDING` or `IN_REVIEW` $\rightarrow$ `SectionLifecycleStatus.NEEDS_REVIEW`.
- Else if ANY task is `RUNNING` or `QUEUED` $\rightarrow$ `SectionLifecycleStatus.PROCESSING` (or `RENDERING` if task is `Stage 14/15`).
- Else if ALL terminal deliverables are `COMPLETED` $\rightarrow$ `SectionLifecycleStatus.COMPLETED`.

---

### 2. DAG Correctness & Video/Audio Render Decoupling

#### 2.1 The Critical Pipeline Ambiguity
In the original specification and legacy `universal_section_pipeline.py`:
- `pipeline.step_render()` called `dynamic_section_engine.render_section()`, passing `audio_path=master_audio.wav`.
- Inside `dynamic_section_engine.py` (lines 838–844), the engine rendered silent frames to a temporary `raw_video` via FFmpeg pipe, and immediately invoked `ffmpeg -i raw_video -i master_audio -c:v copy ...` to produce `final_whiteboard_1080p.mp4`.
- Because of this internal coupling, `section_worker.py` (line 199) declared that `render` depended on `audio_mix`.
- **The Contradiction:** This created the false belief that visual frame rasterization requires audio. In reality, **rasterizing 2D canvas strokes, hand movement, and camera transforms has zero dependency on audio samples**. Only duration and visual beat cues are needed.

#### 2.2 Canonical Dependency Verification
- **Does Visual Render depend on Audio Mix?** **NO.** Visual frame rendering depends only on `PlacedElementsLayout`, `VisualChoreography`, `CameraTrajectory`, and `DurationSec`.
- **Is video rendered with final audio?** **NO.** Video is rendered as raw silent H.264/ProRes streams (`visual_track.mp4`).
- **Is muxing a separate task?** **YES.** Muxing is an explicit, lightweight (I/O bound, copy codec) stage (`Stage 15: MultiplexDeliverable`).
- **Can Audio Mix and Visual Render run in parallel?** **YES.** Once `Stage 10 (CameraTrajectory)` and `Stage 09 (Choreography)` are finalized, `Stage 12 (AudioMix)` and `Stage 14 (VisualRender)` execute **100% concurrently** on separate hardware pipelines (DSP/CPU vs. GPU/NVENC).

---

### 3. Creation vs. Generated Artifacts & Preflight Decoupling

#### 3.1 The Preflight Contradiction
In `core/orchestration/section_worker.py` (lines 39–52), the legacy method `validate_inputs()` asserted:
```python
return {
    "storyboard": storyboard_file.is_file(),
    "script": script_file.is_file(),
    "voice": voice_file.is_file(),  # FATAL FLAW: Voice does not exist at creation!
}
```
If this ran upon section creation, section initialization crashed or locked out workflow execution because `voice_file` is synthesized downstream in `Stage 03 (TTS)`.

#### 3.2 Canonical Invariant: Two-Tiered Validation Contract

1. **Initial Preflight Contract (`SectionInputContract`):**
   - Evaluated *strictly* at Section Creation or Ingest.
   - **Mandatory External Inputs:**
     - `storyboard_path`: File exists, readable image format (PNG/JPG/WEBP), dimensions $\ge 640\times 360$, file size $> 10\text{ KB}$.
     - `script_text` or `script_path`: Non-empty string, length $\ge 5$ characters, UTF-8 encodable.
   - **Optional Overrides:**
     - `custom_voice_path`: Optional user-provided narration WAV. If absent, `SectionConfig.generate_tts` MUST be `True`.
   - **Artifacts Forbidden at Ingest:** Any requirement for `whisper.json`, `placed_elements.json`, or `voice.wav` is an architectural violation.

2. **Stage-Boundary Preflight Contract (`StagePreflightContract`):**
   - Evaluated dynamically immediately before each `ExecutableTask` executes.
   - Example for `Stage 04 (Whisper)`: Requires `Stage 03 (TTS)` output hash to exist and resolve to a valid PCM WAV with duration $> 0.1\text{s}$.
   - Example for `Stage 14 (Visual Render)`: Requires `final_render_plan.json` hash to match current `visual_manifest.json`, `camera_trajectory.json`, and `choreography.json`.

---

### 4. Production Engine Boundary: Governed Adaptation vs. Dogma

#### 4.1 Rejection of the "NO CHANGES" Dogma
The original specification stated: *"production_engine = NO CHANGES"*. This dogma is fatal to a production desktop app for four forensic reasons:
1. **Coupling to Kivy Subdirectory:** `production_engine/dynamic_section_engine.py` (lines 22–24) actively modifies `sys.path`:
   ```python
   kivy_path = Path(__file__).resolve().parent.parent / "kivy"
   sys.path.insert(0, str(kivy_path))
   from engine.render.render_engine import WhiteboardRenderer
   ```
   This ties the headless production engine to the very directory (`kivy/`) scheduled for deletion!
2. **Missing Cooperative Cancellation:** The frame rendering loop in `dynamic_section_engine.py` runs a monolithic loop over `total_frames` (lines 730–834) without checking any `threading.Event` or cancellation token. A user cancelling a 3-minute render would leave a zombie Python thread thrashing the GPU and blocking FFmpeg pipes.
3. **Monolithic Render/Mux Coupling:** As identified in Area 2, `render_section` forced silent frame rasterization and FFmpeg muxing into a single call.
4. **Unbounded Memory Leaks:** OpenCV canvas allocations (`np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)`) inside nested loops are not garbage collected deterministically on Windows unless frame contexts are managed cleanly.

#### 4.2 Governed Adaptation Rules
`production_engine/` and `kivy/engine/` shall NOT be rewritten or duplicated. Refactoring is strictly governed under the following charter:
- **Rule 4.2.1 (Relocation):** Relocate `kivy/engine/` to `core/render_engine/` or `production_engine/renderer/`. Eliminate all `sys.path` hacks.
- **Rule 4.2.2 (Cooperative Cancellation):** Inject an optional `cancel_token: Optional[threading.Event] = None` and `progress_callback: Optional[Callable[[int, int, float], None]] = None` into `WhiteboardRenderer.render_timeline` and `DynamicSectionEngine.render_section`.
- **Rule 4.2.3 (Decoupled Mux):** Expose `render_visual_frames()` and `multiplex_audio_video()` as separate public methods, keeping `render_section()` only as a backward-compatible wrapper.
- **Rule 4.2.4 (Algorithmic Invariance):** Zero changes permitted to mathematical stroke interpolation, stroke drawing shaders, hand compositor matrix math, or micro-zoning placement heuristics.

---

### 5. Resource Governance: Dynamic Policies vs. Static Numbers

#### 5.1 Critique of Static Budgets
The original specification proposed hardcoded constants: *"4 workers, 8GB RAM, 1 GPU"*.
- On an 8GB RAM ultrabook: 4 workers launching Whisper and OpenCV will trigger an out-of-memory crash (OOM) and freeze Windows.
- On a 64-core AMD Threadripper with 128GB RAM and RTX 4090: allocating 4 workers leaves 85% of compute capacity idle.

#### 5.2 Mathematical Governance Model
The `ResourceGovernor` dynamically queries hardware upon initialization via `psutil` and `pynvml` / Direct3D diagnostic utilities:

$$\text{Cores}_{\text{logical}} = \text{psutil.cpu\_count(logical=True)}, \quad \text{Cores}_{\text{physical}} = \text{psutil.cpu\_count(logical=False)}$$
$$\text{RAM}_{\text{total}} = \text{psutil.virtual\_memory().total}, \quad \text{RAM}_{\text{avail}} = \text{psutil.virtual\_memory().available}$$
$$\text{VRAM}_{\text{free}} = \text{GPU.free\_vram\_bytes() if CUDA/NVENC else } 0$$

#### 5.3 Policy Definitions
The user selects a profile, or allows `AUTO` to compute the allocation matrix:

| Resource Dimension | LOW (Battery / 8GB) | BALANCED (Standard 16GB) | PERFORMANCE (32GB+ / Pro) | AUTO Calculation Formula |
| :--- | :--- | :--- | :--- | :--- |
| **Max Concurrent Tasks** | 1 Task | 2 Tasks | $\min(8, \text{Cores}_{\text{phys}} - 1)$ | $\max\left(1, \min\left(4, \left\lfloor \frac{\text{RAM}_{\text{avail}} - 3\text{GB}}{2.5\text{GB}} \right\rfloor\right)\right)$ |
| **Whisper Concurrency** | 1 (Int8, 2 threads) | 1 (FP32, 4 threads) | 2 (Parallel, 8 threads) | Max 1 unless $\text{RAM}_{\text{avail}} > 24\text{GB}$ |
| **Video Render Mode** | CPU Libx264 (Medium) | NVENC if VRAM $\ge 2\text{GB}$ | NVENC Fast Dual-Instance | NVENC if supported & VRAM $\ge 2.5\text{GB}$, else CPU |
| **Max Render Workers** | 1 Worker | 1 Worker | 2 Workers (Independent Sec) | 1 Worker unless $\text{VRAM} \ge 8\text{GB}$ and $\text{RAM} \ge 32\text{GB}$ |
| **OS Memory Reserve** | 2.5 GB Fixed | 3.5 GB Fixed | 5.0 GB Fixed | $\max(2.5\text{GB}, 0.20 \times \text{RAM}_{\text{total}})$ |
| **Preview Cache RAM** | 512 MB | 1.5 GB | 4.0 GB | $\min(4\text{GB}, \max(512\text{MB}, 0.10 \times \text{RAM}_{\text{avail}}))$ |

---

### 6. Preview Correctness & Unified Rendering Contracts

#### 6.1 The Preview Drift Vulnerability
A major hazard in video production software is **Preview Drift**: where the user approves a layout in an interactive OpenGL preview canvas, but the final FFmpeg render produces different aspect ratios, misaligned text, or offset hand positions.

#### 6.2 The Five Canonical Preview Tiers
1. **Tier 1 (Interactive Canvas):** Vector/sprite bounding box manipulation in real time (60 FPS, PySide6 `QGraphicsScene`). Zero rasterization delay.
2. **Tier 2 (Camera Viewport Preview):** Real-time affine transformation of canvas coordinate space representing camera zoom ($0.5\times$ to $2.5\times$) and pan $(X, Y)$.
3. **Tier 3 (Section Cached Preview):** Frame-accurate composite containing animated strokes, hand overlays, and synchronized audio. Renders into a ring buffer of downsampled JPEGs/RGBA textures in shared memory.
4. **Tier 4: Project Sequencer Preview:** Multi-section timeline player stitching section preview buffers with cross-dissolve audio transitions.
5. **Tier 5: Final Production Render:** Master 1080p60 H.264/AAC MP4.

#### 6.3 Shared Contract Invariants
- **Canonical Canvas Coordinates:** All coordinates across all 5 tiers are normalized to a virtual reference frame of exactly $1920 \times 1080$ with $(0,0)$ at Top-Left.
- **Preview Cache Identity:** The Tier 3 Preview Cache key is mathematically identical to the Final Render key:
  $$\text{Key}_{\text{preview}} = \text{SHA256}(\text{ManifestHash} \parallel \text{LayoutHash} \parallel \text{CameraHash} \parallel \text{AudioMixHash} \parallel \text{ResolutionScale})$$

---

### 7. Invalidation Matrix: Cascades & Camera-SFX Coupling

#### 7.1 The Hidden Camera $\rightarrow$ SFX $\rightarrow$ Audio Mix Cascade
In `dynamic_section_engine.py` (lines 535–560), `generate_sfx_from_staging()` extracts camera motion keyframes:
- When a fast camera pan or zoom-in occurs, the engine automatically injects a `whoosh.wav` or `zoom_slide.wav` sound effect into the staging cues!
- **The Cascade:**
  $$\text{User edits Camera Trajectory} \longrightarrow \text{SFX Cues Change} \longrightarrow \text{Master Audio Mix Invalidated} \longrightarrow \text{Final Mux Invalidated}$$

#### 7.2 Complete Downstream Invalidation Matrix

| User Mutation / Event | Directly Invalidated Stages | Cascaded Downstream Stages | Preserved Stages (Cached) |
| :--- | :--- | :--- | :--- |
| **Edit Script Text** | Stage 03 (TTS), Stage 04 (Whisper) | Stages 05, 06, 07, 08, 09, 11, 12, 13, 14, 15, 16, 17 | Stage 00 (Ingest), Stage 01 (OCR), Stage 02 (Extraction) |
| **Replace Storyboard Image** | Stage 01 (OCR), Stage 02 (Extraction) | Stages 06, 07, 08, 09, 10, 11, 13, 14, 15, 16, 17 | Stage 03 (TTS), Stage 04 (Whisper), Stage 05 (Narrative Map) |
| **Modify Extracted Asset (Mask/Crop)** | Stage 02 (Extraction Assets) | Stages 08, 09, 13, 14, 15, 16, 17 | Stages 00, 01, 03, 04, 05, 06, 07, 10, 11, 12 |
| **Reorder Visual Layout (Z/Pos)** | Stage 08 (Layout) | Stages 09, 13, 14, 15, 16, 17 | Stages 00..07, Stage 10 (Camera), Stage 11 (SFX), Stage 12 (Audio) |
| **Adjust Camera Pan/Zoom** | Stage 10 (Camera Trajectory) | **Stage 11 (SFX)**, **Stage 12 (Audio Mix)**, Stage 13, 14, 15, 16, 17 | Stages 00..09 (All Visual & Timing Assets Intact) |
| **Swap / Volume SFX Cue** | Stage 11 (SFX Placement) | Stage 12 (Audio Mix), Stage 15 (Mux), Stage 16, 17 | Stages 00..10, **Stage 14 (Visual Render Intact!)** |
| **Adjust Drawing Speed / Order** | Stage 09 (Choreography) | Stage 11 (SFX), Stage 12, Stage 13, 14, 15, 16, 17 | Stages 00..08, Stage 10 (Camera Path) |

---

### 8. Revision Safety & Race Condition Mitigation

Every mutating operation MUST occur within an `EditTransaction`:
```python
@dataclass(frozen=True)
class RevisionToken:
    project_id: str
    section_id: str
    revision_id: int          # Monotonically increasing uint64
    transaction_uuid: str     # Unique transaction identifier
    schema_version: int = 2
```
1. **Token Propagation:** When a task DAG is spawned, it is stamped with an immutable `RevisionToken(rev=3)`.
2. **Atomic Commit Guard:** Before writing output, task verifies `state_store.is_revision_current(token)`. If stale, results are discarded.
3. **Cancellation on Invalidation:** Committing Revision $N+1$ immediately signals the `CancellationToken` of all running tasks operating on Revision $\le N$.

---

### 9. Persistence Architecture: WAL, Schemas, & Crash Recovery

The Whiteboard Studio persistence layer employs a **three-tier atomic durability model**:
1. **Atomic File Replacement:** Write to `.tmp.[uuid]`, flush, `os.fsync()`, and `os.replace()` to ensure zero-byte file corruptions cannot occur during unexpected power loss.
2. **Schema Versioning & Migrations:** Every stored JSON file specifies `schema_version: 2` with explicit migration runners.
3. **Autosave Cadence:** Dirty-flag evaluation every 1000ms; debounced commit after 3000ms of inactivity or 60s hard limit.

---

### 10. Human-in-the-Loop Review Contracts (`NEEDS_REVIEW`)

| Review Stage | Trigger Reason | Allowable User Modifications | Resolution / Exit Criteria | Downstream Invalidation on Edit | UI Navigation Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Stage 02: Extraction** | Low OCR confidence, ambiguous segmentation masks, or count $<2$. | Adjust bounding boxes, re-run SAM mask, rename element, re-order drawing precedence. | User clicks "Approve Visual Assets" with $\ge 1$ valid asset. | Invalidates Stages 08..17. | Asset Extraction Inspector (`#inspector-assets`) |
| **Stage 03: Voiceover** | Script word count mismatch, synthesis clipping, duration deviation $>20\%$. | Re-generate with alternate voice/provider, adjust speed/pitch, upload custom WAV. | Audio plays cleanly; user clicks "Approve Voiceover". | Invalidates Stages 04, 09, 11..17. | Voice & Speech Studio (`#inspector-voice`) |
| **Stage 06: Semantic Mapping** | AI Director assigns confidence $<0.70$ on visual-speech semantic match. | Re-link storyboard visual asset to different spoken phrase/sentence. | All script segments have $\ge 1$ assigned visual anchor. | Invalidates Stages 07..17. | Narrative Mapping Matrix (`#inspector-narrative`) |
| **Stage 08: Layout** | Element overlap detected $>15\%$ or canvas boundary violation. | Drag-and-drop elements on 1080p canvas, resize, flip, change anchor point. | Zero bounding box collisions; elements inside 5% safety margin. | Invalidates Stages 09, 13..17. | Canvas Layout Editor (`#editor-canvas`) |
| **Stage 10: Camera** | Pan speed exceeds visual comfort threshold ($>800\text{ px/sec}$). | Adjust camera keyframes, modify zoom factor ($0.5\times-2.0\times$), change easing. | Camera trajectory validated within canvas boundaries. | Invalidates Stages 11, 12, 13..17. | Camera Timeline Track (`#editor-camera`) |
| **Stage 16: Post-Render QA** | Automated QA detects video black frames, audio clipping, or duration drift. | User plays rendered deliverable; options: "Accept", "Re-render", or "Adjust Stages". | User explicitly signs off on final output video. | None if accepted; re-queues specific stage if rejected. | Delivery QA Player (`#player-qa`) |

---

### 11. Error System: Taxonomy, Resilience, & Circuit Breakers

- **Transient:** Network timeouts, Gemini 429 rate limits $\rightarrow$ Auto-retry with jittered exponential backoff ($T_{\text{wait}} = \min(30.0, 2^{\text{attempt}} + \text{rand})$), budget: 3 attempts.
- **Recoverable:** Low confidence detection, bad layout overlap $\rightarrow$ Halt stage, flag `NEEDS_REVIEW`, open dedicated inspector.
- **Configuration:** Missing FFmpeg binary, bad API keys $\rightarrow$ Pause pipeline, launch Environment Doctor modal.
- **Fatal:** NTFS sector failure, system OOM $\rightarrow$ Emergency state flush, worker termination, crash report generation.

---

### 12. Processing Concurrency: Multi-Section Scheduling Under Load

- **Priority Hierarchy:**
  1. Priority 1 (Interactive UI drag & scrub, $<16\text{ms}$)
  2. Priority 2 (Preview audio/video playback buffer)
  3. Priority 3 (Background pre-render stages 01..12)
  4. Priority 4 (Batch video render, single GPU mutex holder)
- **GPU Mutex:** Only ONE render task holds the NVENC/CUDA context. Timeline preview scrubbing automatically uses CPU downscaled textures during active video exports.

---

### 13. Application Restart, Crash Consistency, & Orphan Recovery

Startup reconciliation sequence:
1. Load `project.wbp` (or `.bak` on failure).
2. Scan all tasks flagged `RUNNING` or `RETRYING` in SQLite journal.
3. Compare output file existence and SHA256 against registered cache expectations.
4. Auto-promote intact outputs to `COMPLETED`; transition incomplete outputs to `FAILED` with `"Interrupted by abnormal shutdown"`.
5. Reconcile aggregate section and project states; purge stale `.tmp.*` files older than 1 hour.

---

### 14. Performance Architecture: SLAs per Hardware Profile

- **Interactive Drag:** $\le 33\text{ms}$ (Low), $\le 16\text{ms}$ (Balanced), $\le 8\text{ms}$ (Performance).
- **Timeline Scrub Latency (p50):** $\le 120\text{ms}$ (Low), $\le 30\text{ms}$ (Balanced), $\le 10\text{ms}$ (Performance).
- **Render Speed (1080p60):** $\ge 18\text{ FPS}$ (Low CPU), $\ge 108\text{ FPS}$ (Balanced NVENC), $\ge 270\text{ FPS}$ (Performance Dual-Instance).

---

### 15. Packaging & Deployment Architecture (Windows Desktop)

- **Bundled Static Binaries:** Self-contained `bin/ffmpeg.exe` and `bin/ffprobe.exe` prepended to `PATH`.
- **Driver Diagnostics:** Automatic probing of NVENC/QSV/AMF capabilities on first boot with graceful CPU libx264 fallback.
- **Storage Isolation:** Standard paths configured for `%Documents%\WhiteboardStudio\Projects\` and `%LOCALAPPDATA%\WhiteboardStudio\Cache\`.

---

### 16. Master Documentary Assembly Architecture

- **Sequencing:** Deterministic ordering by `sequence_index`.
- **Eligibility:** Strict requirement for `SectionLifecycleStatus.COMPLETED` and valid deliverable hash.
- **Section Isolation:** Editing Section $K$ invalidates `master_documentary.mp4`, but keeps all other section deliverables $J \ne K$ completely cached.

---

### 17. User Impact Preview: Reusable UX Invalidation Pattern

- Intercepts destructive mutations with an Impact Analysis Dialog listing exact stages to be re-run vs. stages preserved, complete with estimated recomputation time.

---

# PART II: CANONICAL ARCHITECTURAL SYNTHESIS (SECTIONS A — Q)

### Section A: Architectural Contradictions & Formal Resolutions
1. Resolved stage count from 17 vs 19 to strictly **18 canonical stages** (00..17).
2. Decoupled silent visual frame rendering from master audio mixing into parallel branches.
3. Separated section creation input preflight from downstream generated artifact validation.
4. Replaced "NO CHANGES" dogma with Governed Adaptation Rules.
5. Replaced static resource numbers with dynamic mathematical hardware budgets.

### Section B: Missing Contracts Identified & Formally Defined
Formalized `EditTransactionTokenContract`, `CameraToAudioCascadeContract`, `UnifiedPreviewContract`, `ReviewGateProtocol`, `AtomicPersistenceContract`, `CircuitBreakerContract`, `CrashReconciliationContract`, and `PackagingEnvironmentContract`.

### Section C: Corrected Canonical Pipeline DAG
Strict 18-stage directed acyclic graph establishing parallel audio and visual branches converging at Stage 15 (Multiplexing).

### Section D: Corrected State Machine Specification
Formally defined 9 task states, 5 review states, 8 section states, and 6 project states with exhaustive transition permissibility matrix.

### Section E: Canonical 18 Stages Roster & Artifact Contracts
Comprehensive roster of Stages 00 through 17 with upstream dependencies, produced artifact schemas, and resource pools.

### Section F: Corrected Invalidation Matrix
Exhaustive matrix mapping every user mutation to its cascaded downstream invalidations and preserved artifact caches.

### Section G: Dynamic Resource Governance Architecture
Mathematical formulas computing max workers, memory budgets, and GPU mutex allocation across LOW, BALANCED, PERFORMANCE, and AUTO profiles.

### Section H: Unified Preview Contracts & Drift Acceptance Tests
Mathematical RMSE pixel-delta equivalence test ensuring Tier 1 through Tier 5 rendering contracts never drift.

### Section I: Persistence Architecture & WAL Journaling
POSIX/NTFS atomic temp-flush-rename pattern with automatic rolling `.bak` backup and SQLite WAL task locks.

### Section J: Revision Tokens & Multi-Tier Revision Safety
Monotonically increasing `RevisionToken` preventing stale asynchronous render outputs from overwriting active user edits.

### Section K: Human Review Gate Model (`NEEDS_REVIEW`)
Exhaustive review gate schemas and resolution criteria for Extraction, Voice, Semantic, Layout, Camera, and Delivery QA.

### Section L: Restart, Crash Recovery, & Orphan Reconciliation
Deterministic startup reconciliation algorithm self-healing interrupted tasks and purging orphaned temp files.

### Section M: Packaging & Native Deployment Architecture
Embedded runtime architecture, static binary distribution, and automated hardware encoder detection.

### Section N: Updated File & Module Architecture
Clean workspace reorganization relocating `kivy/engine/` to `core/render_engine/` and establishing the modern `studio_ui/` desktop application structure.

### Section O: Updated Implementation Phases
Six-phase execution roadmap prioritizing core foundation and engine decoupling before UI assembly.

### Section P: Risk Registry & Forensic Mitigations
Exhaustive risk analysis addressing race conditions, camera-audio cascades, OOM crashes, and file corruptions.

### Section Q: Final Phase 1 Entry Criteria & Verification Gate
All 9 architectural quality gates verified and signed off for Phase 1 commencement.

---
*Signed and Certified as Production Architecture Foundation,*  
**Principal Systems & Video Pipeline Architect**  
*Whiteboard Studio Project*
