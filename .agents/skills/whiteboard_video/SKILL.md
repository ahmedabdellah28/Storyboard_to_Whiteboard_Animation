---
name: whiteboard-video
description: >
  Complete, self-contained guide for producing cinematic whiteboard-style animation videos from storyboard images.
  Covers both the legacy pipeline (UniversalSectionPipeline) and the TCM-DS v2 three-contract pipeline
  (Visual Manifest → Narrative Map → Final Render Plan). Full pipeline: storyboard verification → adaptive
  candidate extraction → cinematic layout → zero-truncation voiceover → audio mixing → video rendering →
  multi-section merging. Produces 1080p professional whiteboard videos with hand-drawn inking effects,
  cinematic camera pans, and synchronized audio with ducked SFX.
---

# 🎬 Cinematic Whiteboard Video — Production Skill

> **Autonomous End-to-End Pipeline**: Transforms a hand-drawn storyboard sheet into a polished,
> narrator-synced whiteboard animation video at 1080p / 30 FPS.
>
> ⚠️ **CRITICAL DIRECTIVE FOR AI AGENTS**:
> You do **NOT** need to read the entire repository files to produce a section.
> Everything you need — architecture, rules, algorithms, parameters, tool APIs, and executable templates —
> is fully codified in this skill document.

---

## Table of Contents

0. [Autonomous Executive Blueprint (Standards 0–4)](#-0-autonomous-executive-blueprint)
1. [Project Tool API Map](#-1-project-tool-api-map--module-reference)
2. [Project Organization & Directory Standards](#-2-project-organization--directory-standards)
3. [Step 1 — Script, Voiceover & Word-Sync Alignment](#-3-step-1--script-voiceover--word-sync-alignment)
4. [Step 2 — Asset Extraction (Natural White-Gap)](#-4-step-2--asset-extraction-natural-white-gap-pipeline)
5. [Step 3 — Cinematic Layout & Micro-Zoning](#-5-step-3--cinematic-layout--micro-zoning)
6. [Step 3.5 — AI Pre-Render Visual Director Gate](#-6-step-35--ai-pre-render-visual-director-gate)
7. [Step 4 — Audio Mixing (SFX + Ducking)](#-7-step-4--audio-mixing-sfx--ducking)
8. [Step 5 — Video Rendering](#-8-step-5--video-rendering)
9. [Step 6 — Multi-Section Merging](#-9-step-6--multi-section-merging)
10. [Step 7 — Vertical Reels / Shorts Export (9:16)](#-10-step-7--vertical-reels--shorts-export-916)
11. [Animation Types Reference](#-11-animation-types-reference)
12. [Camera System Reference](#-12-camera-system-reference)
13. [Audio Engineering Reference](#-13-audio-engineering-reference)
14. [Troubleshooting & Quality Lessons](#-14-troubleshooting--quality-lessons)
15. [TCM-DS v2 Three-Contract Pipeline](#-15-tcm-ds-v2-three-contract-pipeline)
16. [Production Checklist](#-16-production-checklist)
17. [Micro-Retention Transparent GIFs & Strict Zero-BGM Policy](#-17-micro-retention-transparent-gifs--strict-zero-bgm-policy)
18. [Zero-Regression Constitution: Anti-Freeze, Boundary Precision & Layout Perfection](#-18-zero-regression-constitution-anti-freeze-boundary-precision--layout-perfection)

---

## ⚡ 0. Autonomous Executive Blueprint (دليل الإنتاج الذاتي السريع والشامل)

This executive section is the **single source of truth** for producing any whiteboard section. Follow these 5 mandatory standards strictly:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                   AUTONOMOUS PRODUCTION BLUEPRINT (OSAS v3.1)                │
├──────────────────────────────────────────────────────────────────────────────┤
│ [Stage 0] Storyboard Check    → Verify storyboard.png; alert if missing     │
│ [Stage 1] Natural Extraction  → White-gap projection; zero box cutting      │
│ [Stage 2] Voiceover Engine    → Fenrir TTS, <28 words, tail-verified        │
│ [Stage 3] Whisper Alignment   → Ground truth word timestamps                │
│ [Stage 4] Choreography & QA   → Semantic anchors, single-ink mutex, 10 gates│
│ [Stage 5] Scene Composition   → 2-4 elements per scene, varied animations   │
│ [Stage 6] Video & Audio Mix   → NVENC 1080p, 6 calm camera pans, ducked SFX │
├──────────────────────────────────────────────────────────────────────────────┤
│ ⚠️ CRITICAL: Each scene has 2-4 elements. Only Hero elements use pen inking. │
│    Secondary elements use slide_down/up, jelly_pop, pulse_pop, organic_grow. │
│    Camera stays STEADY on each scene. Only 5-7 total pans per 50s section.   │
│    Reference: scripts/run_08_lu_bu_osas_pipeline.py                          │
│               scripts/run_09_al_baraa_osas_pipeline.py                      │
│               scripts/run_15_outro_osas_pipeline.py                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 🛑 Standard 0: Storyboard Existence Verification & Mandatory Alert (إلزامية فحص الاستوري بورد)

> [!CAUTION]
> **STRICT BAN ON FAKE PLACEHOLDERS**:
> Never generate fake shapes, mock rectangles, or artificial canvases when a storyboard is missing.
> If the storyboard image cannot be found, you MUST **HALT IMMEDIATELY** and alert the user.

#### Verification Protocol:
1. Check primary location: `sections/<documentary_slug>/<NN_section>/storyboard.png`
2. Check secondary repository cache: `project_content/images/<section_name_or_keyword>.*`
3. If neither exists:
   - **Do NOT proceed with rendering.**
   - **Do NOT draw placeholder boxes.**
   - **Immediately output this alert to the user:**
     > ⚠️ **تنبيه حاسم**: لم يتم العثور على صورة الستوري بورد (`storyboard.png`) للقسم المطلوب.
     > وفقاً للبروتوكول الصارم، توقف النظام فوراً لمنع توليد رسومات وهمية أو أشكال مؤقتة.
     > يرجى تزويدي بصورة الستوري بورد أو حفظها في المسار المخصص قبل المتابعة.

```python
import os, glob, shutil

def verify_storyboard_or_halt(sec_dir, project_images_dir, keywords):
    """Checks if a valid storyboard image exists. If missing, raises an error to halt execution."""
    primary_sb = os.path.join(sec_dir, "storyboard.png")
    if os.path.exists(primary_sb) and os.path.getsize(primary_sb) > 10000:
        return primary_sb
    if os.path.exists(project_images_dir):
        for kw in keywords:
            matches = glob.glob(os.path.join(project_images_dir, f"*{kw}*.*"))
            for m in matches:
                if m.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and os.path.getsize(m) > 10000:
                    os.makedirs(sec_dir, exist_ok=True)
                    shutil.copy2(m, primary_sb)
                    return primary_sb
    raise FileNotFoundError(
        f"CRITICAL: No storyboard found at '{sec_dir}' or '{project_images_dir}'! HALTED."
    )
```

---

### ✂️ Standard 1: Natural White-Gap Asset Extraction (دقة الفصل الطبيعي الكامل)

> [!IMPORTANT]
> **NEVER USE MECHANICAL GRID SLICING**:
> Storyboard sheets (e.g. 1536×1024) do **not** use uniform rectangular boxes. Mechanical slicing
> (dividing width into 5 equal 307px columns) cuts off spears, heads, shields, and splits panoramic scenes!
> You MUST use **Natural White-Gap Projection Analysis**.

#### Natural Projection & Organic Segmentation Algorithm:
1. **Find Row Gaps**: Project foreground pixels horizontally. Gaps where density ≈ 0 define true row boundaries.
2. **Find Column Gaps Per Row**: Within each row, project vertically. Gaps define natural illustration boundaries.
3. **Corner Flood-Fill Background Removal**: 4-corner flood-fill with `BG_TOL = 20`.
4. **Connected-Component Noise Filter**: Keep components ≥ 3% of largest area.
5. **Gaussian Alpha Feathering**: `cv2.GaussianBlur` (kernel 3×3, sigma 0.8).
6. **Tight Bounding Crop**: Crop to actual alpha boundaries.

```python
def extract_natural_asset(img_full, x1, x2, y1, y2):
    """Extracts asset along organic silhouette. Zero box borders, zero cutoff, feathered edges."""
    crop = img_full[y1:y2, x1:x2].copy()
    ch, cw = crop.shape[:2]
    padded = cv2.copyMakeBorder(crop, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    ph, pw = padded.shape[:2]
    flood_mask = np.zeros((ph + 2, pw + 2), dtype=np.uint8)
    BG_TOL = 20
    for cy, cx in [(0, 0), (0, pw - 1), (ph - 1, 0), (ph - 1, pw - 1)]:
        if flood_mask[cy + 1, cx + 1] == 0:
            cv2.floodFill(padded, flood_mask, (cx, cy), [0,0,0],
                          (BG_TOL,)*3, (BG_TOL,)*3, cv2.FLOODFILL_FIXED_RANGE)
    exterior = flood_mask[1:ph+1, 1:pw+1][4:4+ch, 4:4+cw]
    fg_rough = ((exterior == 0).astype(np.uint8)) * 255
    k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    fg_clean = cv2.morphologyEx(fg_rough, cv2.MORPH_CLOSE, k_close, iterations=2)
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(fg_clean, connectivity=8)
    if n_labels > 1:
        areas = sorted([(stats[i, cv2.CC_STAT_AREA], i) for i in range(1, n_labels)], reverse=True)
        keep = [idx for area, idx in areas if area >= areas[0][0] * 0.03]
        fg_clean2 = np.isin(labels, keep).astype(np.uint8) * 255
    else:
        fg_clean2 = fg_rough
    alpha = cv2.GaussianBlur(fg_clean2.astype(np.float32), (3, 3), 0.8)
    alpha = np.clip(alpha, 0, 255).astype(np.uint8)
    ys, xs = np.where(alpha > 10)
    if len(xs) > 0:
        tx1, tx2, ty1, ty2 = int(np.min(xs)), int(np.max(xs)), int(np.min(ys)), int(np.max(ys))
        bgra = np.dstack([crop[ty1:ty2+1, tx1:tx2+1], alpha[ty1:ty2+1, tx1:tx2+1]])
    else:
        bgra = np.dstack([crop, alpha])
    return bgra
```

---

### 🎙️ Standard 2: Professional Voiceover & Zero-Truncation Standard (احترافية الصوت)

> [!CAUTION]
> **GEMINI TTS BUFFER CEILING (20-25 Seconds / 35 Words)**:
> Gemini TTS silently drops audio beyond ~25s per call without error!
> All scripts MUST be chunked into semantic clauses strictly **under 28 words**.

1. **Model & Voice**: `gemini-3.1-flash-tts-preview`, Voice: `Fenrir`, `speed_factor=1.05–1.10`.
2. **Punctuation Stripping**: Remove internal `,` `.` `؟` from TTS payload to prevent 0.5s dead-air pauses.
3. **Mandatory Tail-Verification Loop**: Transcribe last 15s via `gemini-3.6-flash` STT → compare with final 6-8 words → auto-repair if missing.
4. **Audio Master Mix**: 48kHz 16-bit Stereo, voiceover at -0.5 dB, SFX at 50% with dynamic ducking.

---

### ⏱️ Standard 3: Millisecond Word-Level Inking Sync & Camera Panning (تزامن الرسم والكاميرا)

1. **Ground Truth via Faster-Whisper** → `timing/whisper.json`. Never guess timestamps!
2. **0.20s Lead Inking**: `t_start = max(0.0, word_t - 0.20)` — pen touches canvas 200ms before word is spoken.
3. **Explanation Hold**: Camera + element REMAIN VISIBLE & STATIONARY for entire narration sentence. Elements NEVER fade out (`fade_out_at = None`).
4. **Just-In-Time Camera Pan**: `pan_end = next_zone_start - 0.05`, `pan_start = pan_end - 0.85s`. Guarantees **zero blank white screen**.

---

### 📐 Standard 4: Viewport-Safe Camera & Multi-Element Scene Layout (أبعاد الكاميرا وتكوين المشاهد)

> [!IMPORTANT]
> **MULTI-ELEMENT SCENE COMPOSITION (OSAS v3.1)**:
> Every scene/zone contains **2 to 4 thematically related elements**.
> Only the **Hero element** is drawn with inking hand (`outside_in_pen`).
> Secondary elements use varied animations (`slide_down`, `jelly_pop`, `pulse_pop`, `organic_grow`, `slide_up`).
> Camera stays **completely stationary** on each scene. Total pans per section: **5 to 7**.

| Parameter | Standard Value | Rationale |
|---|---|---|
| `CAM_ZOOM` | **0.65** | Balanced zoom for multi-element scenes (2-4 elements visible simultaneously) |
| `FIXED_Y` | **800.0 px** | Constant vertical center. Camera pans 100% horizontally (dY = 0) |
| `Scenes per Section` | **5 to 8** | Each scene has 2–4 elements. ~20 elements = ~7 scenes |
| `Elements per Scene` | **2 to 4** | Thematically grouped. NEVER 1 element per zone |
| `Scene Spacing` | **3200 px** | Complete visual isolation between scenes |
| `Element Gap (within scene)` | **70 – 100 px** | Aesthetic breathing room between adjacent elements |
| `Animation per scene` | **1 Hero pen + N varied** | Only 1 `outside_in_pen`; rest are `slide/pop/grow` |
| `Camera pans` | **5 to 7 total** | Calm, cinematic. NEVER 1 pan per element |

---

## 🗺️ 1. Project Tool API Map & Module Reference

> [!IMPORTANT]
> The AI agent acts as **supervisor/orchestrator** over these existing project tools.
> It does NOT need to rewrite them — it calls them via the APIs documented below.

### Core Production Tools

| Module | Path | Class / Function | Purpose |
|---|---|---|---|
| **Universal Pipeline** | `production_engine/universal_section_pipeline.py` | `UniversalSectionPipeline` | Full section pipeline with modular stages |
| **Storyboard Extractor** | `production_engine/dynamic_storyboard_extractor.py` | `DynamicStoryboardExtractor` | Discovers rows/cells, extracts BGRA assets, generates title banner |
| **Layout Planner** | `production_engine/dynamic_layout_planner.py` | `DynamicLayoutPlanner` | High-impact micro-zone layout with adaptive scaling |
| **Speech Synchronizer** | `production_engine/dynamic_speech_synchronizer.py` | `DynamicSpeechSynchronizer` | Maps narration timestamps to visual elements |
| **Voiceover Engine** | `production_engine/voiceover_engine.py` | `generate_voiceover_zero_truncation()` | Fenrir TTS with chunking + tail-verification |
| **Audio Aligner** | `production_engine/audio_aligner.py` | `align_anchor_phrases()` | Gemini STT anchor phrase timestamp extraction |
| **Render Engine** | `production_engine/dynamic_section_engine.py` | `DynamicSectionEngine` | 1080p NVENC rendering with inking + hand compositor |
| **Audio Mixer** | `production_engine/mix_section_audio.py` | `mix_section_audio()` | 48kHz stereo mix with SFX ducking |
| **Section Merger** | `production_engine/merge_master_sections.py` | Dissolve merger | Multi-section master video with dissolve-through-white |
| **Reels Exporter** | `production_engine/export_section_reels.py` | Vertical 9:16 export | Instagram/TikTok/Shorts vertical reformat |
| **Inking Engine** | `kivy/engine/render/concentric_engine.py` | `build_gapless_orbital_path()` | Outside-in contour-following stroke generation |
| **Hand Compositor** | `kivy/engine/render/hand_compositor.py` | `composite_hand_on_canvas_fast()` | Alpha-blends drawing hand sprite onto frames |

### Core Orchestration System

| Module | Path | Class | Purpose |
|---|---|---|---|
| **Production Orchestrator** | `core/orchestration/orchestrator.py` | `ProductionOrchestrator` | Canonical project/section entry point |
| **Section Worker** | `core/orchestration/section_worker.py` | `SectionWorker` | Per-section DAG lifecycle manager |
| **Task DAG Executor** | `core/orchestration/task_dag.py` | `TaskDAGExecutor` | Dependency-aware parallel task execution |
| **Resource Scheduler** | `core/orchestration/resource_pools.py` | `ResourcePoolManager` | NETWORK_API / CPU_HEAVY / GPU_RENDER / DISK_IO |
| **State & Artifacts** | `core/state/` + `core/artifacts/` | StateStore, ArtifactStore | Resume, cache, invalidation, atomic completion |

### TCM-DS v2 Pipeline Modules (Three-Contract Model)

| Module | Path | Class | Purpose |
|---|---|---|---|
| **Adaptive Candidate Extractor** | `core/vision/adaptive_candidate_extractor.py` | `AdaptiveCandidateExtractor` | Recursive XY-cut organic element segmentation (replaces fixed grid) |
| **Visual Reviewer Engine** | `core/vision/visual_reviewer_engine.py` | — | Generates Contract 1: visual_manifest.json |
| **Demand Estimator** | `core/vision/demand_estimator.py` | `DemandEstimator` | Estimates draw duration from visual complexity (pixel mass, contour, edge density) |
| **Narrative Director** | `core/narrative/narrative_director.py` | — | Generates Contract 2: narrative_visual_map.json |
| **Constraint Scheduler** | `core/scheduling/constraint_scheduler.py` | `ConstraintVisualScheduler` | Generates Contract 3: final_render_plan.json (deterministic, zero LLM) |
| **Contract Schemas** | `core/contracts/` | Pydantic models | `VisualManifest`, `NarrativeVisualMap`, `FinalRenderPlan` with cryptographic hashes |
| **TCM v2 Render Script** | `scripts/render_guan_yu_tcm_v2.py` | `render_guan_yu()` | Reference implementation: Contract 3 → DynamicSectionEngine rendering |

### How to Execute Production

**Single section (canonical command):**
```bash
python -m core.orchestration.orchestrator --section 04_spartacus
```

**Full project with parallel sections + master assembly:**
```bash
python -m core.orchestration.orchestrator --project fiercest_warriors_documentary --parallel 2 --assemble
```

**Alternative: Direct pipeline invocation (for custom manifest or debugging):**
```python
from production_engine.universal_section_pipeline import UniversalSectionPipeline
pipeline = UniversalSectionPipeline("sections/fiercest_warriors_documentary/04_spartacus")
pipeline.step_tts()                           # Stage 0: Fenrir TTS
pipeline.step_whisper()                       # Stage 1: Faster-Whisper
pipeline.step_extraction()                    # Stage 2: Storyboard extraction
pipeline.step_layout_and_sync(custom_manifest)# Stage 3: Layout + sync
pipeline.step_pre_render_director()           # Stage 4: AI Director gate
pipeline.step_audio_mix()                     # Stage 5: Audio mixing
pipeline.step_render()                        # Stage 6: 1080p render
pipeline.step_publish()                       # Stage 7: Publish deliverable
```

### Canonical Section DAG Order

```
1. TTS Audio Generation         (NETWORK_API) → voice/section.wav
2. Faster-Whisper Ground Truth  (CPU_HEAVY)   → timing/whisper.json
3. Storyboard Extraction        (CPU_HEAVY)   → assets/ + metadata.json
4. Layout + Speech Sync         (CPU_HEAVY)   → placed_elements_layout.json
5. AI Pre-Render Director Gate  (NETWORK_API) → timing/final_render_plan.json
6. Audio Mixing + SFX           (DISK_IO)     → master_audio.wav
7. NVENC Production Rendering   (GPU_RENDER)  → final_whiteboard_1080p.mp4
8. Deliverable Publishing       (DISK_IO)     → deliverables/sections/
```

Independent tasks are scheduled concurrently. Valid artifacts are CACHE_HIT (not regenerated). Failed tasks are isolated and resumable.

### Canonical Execution Rules

| Rule | Requirement |
|---|---|
| **Single Source of Truth** | `core.orchestration.orchestrator` is the canonical entry point |
| **DAG Ownership** | Task ordering, retries, cache belong to Core DAG |
| **Resume First** | Re-running resumes from valid completed tasks |
| **No Direct Stage Launching** | Do not launch Whisper/Director/TTS separately for production |
| **Legacy Compatibility** | `run_<topic>_production.py` must delegate to Core; never duplicate logic |

---

## 📁 2. Project Organization & Directory Standards

```
image_to_animate/
├── project_content/                         # Raw materials
│   ├── images/                              # Storyboard PNG sheets from artists
│   └── transcript_to_speech.txt             # Full documentary script
│
├── sections/                                # Production workspaces per section
│   └── <documentary_slug>/
│       └── NN_topic/                        # e.g., 04_spartacus, 05_tlahuicole
│           ├── storyboard.png               # Source sheet (MANDATORY)
│           ├── script.txt                   # Narration script
│           ├── assets/                      # Extracted RGBA PNGs + metadata.json
│           ├── timing/                      # whisper.json, drawing_timeline.json, final_render_plan.json
│           ├── voice/                       # section.wav (Fenrir TTS)
│           ├── placed_elements_layout.json  # World canvas layout & camera zones
│           ├── master_audio.wav             # 48kHz voiceover + ducked SFX
│           ├── final_whiteboard_1080p.mp4   # 1080p section video deliverable
│           └── scratch/                     # Temporary scripts & test frames
│
├── output_animations/                       # Master outputs
│   └── <project_slug>/
│       ├── deliverables/
│       │   ├── <Topic>_Whiteboard_Master_1080p.mp4
│       │   ├── <Topic>_Master_Audio.wav
│       │   ├── project_manifest.json
│       │   ├── sections/                    # Standalone clean section videos
│       │   └── reels/                       # Vertical 9:16 exports
│       └── scratch/                         # Temporary render buffers
│
├── production_engine/                       # Core engine modules & SFX bank
│   ├── dynamic_section_engine.py            # Render engine
│   ├── dynamic_storyboard_extractor.py      # Asset extraction
│   ├── dynamic_layout_planner.py            # Layout planning
│   ├── dynamic_speech_synchronizer.py       # Speech sync
│   ├── universal_section_pipeline.py        # Unified pipeline
│   ├── voiceover_engine.py                  # TTS engine
│   ├── audio_aligner.py                     # STT alignment
│   ├── mix_section_audio.py                 # Audio ducking mixer
│   ├── merge_master_sections.py             # Multi-section dissolve merger
│   ├── export_section_reels.py              # Vertical reels exporter
│   └── sfx/                                 # 18 specialized 48kHz WAV sounds
│
├── core/                                    # Core orchestration + TCM-DS v2 pipeline
│   ├── orchestration/                       # DAG, resource pools, orchestrator
│   ├── state/                               # Durable state & resume
│   ├── artifacts/                           # Cache identity & artifact store
│   ├── contracts/                           # Pydantic schemas: VisualManifest, NarrativeMap, RenderPlan
│   ├── vision/                              # Adaptive extraction, demand estimation, visual review
│   │   ├── adaptive_candidate_extractor.py  # Recursive XY-cut (replaces fixed grid)
│   │   ├── demand_estimator.py              # Drawing complexity → duration estimation
│   │   └── visual_reviewer_engine.py        # Contract 1 generator
│   ├── narrative/                           # Narrative director (Contract 2)
│   └── scheduling/                          # Constraint scheduler (Contract 3, deterministic)
│
├── scripts/                                 # TCM v2 render scripts & test harnesses
│   ├── render_guan_yu_tcm_v2.py             # Reference: Contract 3 → whiteboard video
│   └── test_guan_yu_full_tcm_pipeline.py    # Full pipeline integration test
│
└── kivy/engine/render/                      # Inking & hand compositor
    ├── concentric_engine.py                 # Outside-in orbital stroke path
    └── hand_compositor.py                   # Drawing hand alpha blending
```

### Semantic Content Naming Rules (Mandatory)

| Item | ❌ Forbidden | ✔️ Required |
|---|---|---|
| Master Video | `final_video.mp4` | `<Topic>_Whiteboard_Master_1080p.mp4` |
| Master Audio | `merged_audio.wav` | `<Topic>_Master_Audio.wav` |
| Section Video | `output.mp4` | `<NN>_<Topic>_Whiteboard_1080p.mp4` |
| Section Folder | `sec1/` | `sections/<NN>_<topic>/` |

---

## 🎙️ 3. Step 1 — Script, Voiceover & Word-Sync Alignment

### 1.1 Script Preparation

The narration script is processed for TTS:
- `script.txt` — Full Arabic text with natural phrasing.
- Strip internal commas (`,`), periods (`.`), question marks (`؟`) for TTS payload to prevent 0.4–0.8s acoustic pauses.

### 1.2 Zero-Truncation Safe Chunking (< 28 Words)

```python
from production_engine.voiceover_engine import generate_voiceover_zero_truncation

voiceover_wav, dur = generate_voiceover_zero_truncation(
    script_path="script.txt",
    output_wav_path="voice/section.wav",
    chunks_dir="voice/chunks",
    voice_name="Fenrir",
    speed_factor=1.1,
    max_words_per_chunk=28
)
```

### 1.3 Semantic Speech-to-Visual Alignment

```python
from production_engine.audio_aligner import align_anchor_phrases

# Define anchor phrases mapping each visual element to 2-4 words in script.txt
anchor_dict = {
    "r1_01_hero_portrait": "البطل الشرس",
    "r1_02_battle_scene":  "المعركة الكبرى",
    # ... all elements mapped
}

# Returns exact timestamps: {"r1_01_hero_portrait": 1.05, "r1_02_battle_scene": 4.28, ...}
timestamps = align_anchor_phrases("voice/section.wav", anchor_dict)
```

**The 0.20s Lead Inking Formula:**
```python
t_start = max(0.0, word_t - 0.20)  # Pen starts 200ms before word is spoken
```

**Just-In-Time Camera Pan Rule:**
```python
pan_end = next_start - 0.05          # Camera arrives 50ms before next zone inks
pan_start = pan_end - pan_dur        # pan_dur typically 0.85s
min_pan_start = last_end + 0.20      # Hold at least 200ms after last drawing
if pan_start < min_pan_start:
    pan_start = min_pan_start
    pan_dur = max(0.40, pan_end - pan_start)
```

---

## ✂️ 4. Step 2 — Asset Extraction (Natural White-Gap Pipeline)

### Purpose

Extract each visual element along its natural organic contour as a standalone RGBA PNG, eliminating white background and preventing neighbor bleed.

### Professional Connected-Components Algorithm

```
Storyboard Sheet (BGR)
       │
       ▼
1. Natural White-Gap Projection: Find real row/column boundaries (NOT fixed grid!)
       │
       ▼
2. Corner Flood-Fill: BG_TOL=20, isolate external white canvas
       │
       ▼
3. Morphological Close: cv2.morphologyEx(fg_mask, MORPH_CLOSE, ellipse(3x3))
       │
       ▼
4. Connected Components: Keep foreground ≥ 3% of max component area
       │
       ▼
5. Gaussian Alpha Feathering: Soft edges (kernel 3x3, sigma 0.8)
       │
       ▼
6. Tight Contour Crop & RGBA Export: Save PNG + record orig_box & pixel area
```

### Tool API:
```python
from production_engine.dynamic_storyboard_extractor import DynamicStoryboardExtractor

extractor = DynamicStoryboardExtractor(section_dir)
extractor.generate_title_banner("عنوان القسم")  # Arabic handwriting banner
extractor.extract_assets()                        # Extracts all cells → assets/
```

### Key Principles

| Principle | Why It Matters |
|---|---|
| **Zero Rectangles** | Assets masked to organic silhouette, zero box artifacts |
| **Label Isolation** | Neighbor pixels set to `alpha = 0` via different component IDs |
| **100% Coverage** | Every storyboard drawing maps to a script sentence. Never drop trailing elements |
| **Strict L-to-R Order** | Assets named `r{ROW}_{COL:02d}_{name}.png` |

---

## 📐 5. Step 3 — Cinematic Layout & Micro-Zoning

### Tool API:
```python
from production_engine.dynamic_layout_planner import DynamicLayoutPlanner

planner = DynamicLayoutPlanner(section_dir, fixed_y=800.0, cam_zoom=0.74)
planner.plan_layout(manifest_items)  # Outputs placed_elements_layout.json
```

### Adaptive Element Scaling

> [!CAUTION]
> **CRITICAL: Crops from the extractor are ~250-350px (raw storyboard resolution).**
> They MUST be scaled UP before rendering. Using raw crop sizes with any CAM_ZOOM
> results in tiny ~200px elements on a 1920×1080 canvas — effectively invisible!

**Legacy Pipeline (DynamicLayoutPlanner):**

| Elements per Zone | Scale | Screen Height |
|---|---|---|
| 1 (Hero) | 3.2 | ~45% of 1080p |
| 2 | 2.6 | ~40% |
| 3 | 2.35 | ~35% |
| 4+ | 2.0 | ~30% |

**OSAS v3.1 Pipeline (Multi-Element Scene Composition — CANONICAL):**

| Parameter | Value | Rationale |
|---|---|---|
| `RENDER_CAM_ZOOM` | **0.65** | Balanced for 2-4 elements visible per scene |
| `cam_y` | **800.0** | Fixed vertical center |
| `zone_spacing` | **3200.0 px** | Clean separation between scenes |
| `GAP` | **70.0 px** | Spacing between elements within a scene |
| `base_scale` | **2.3** (2-3 elems) / **1.9** (4 elems) | Adaptive: more elements → slightly smaller |

### Placement Logic (OSAS v3.1 — Multi-Element Scenes)
```python
# Define scenes: 2-4 elements grouped by narrative theme
SCENES = [
    {"scene_id": "zone_1", "base_scale": 2.3, "elements": [
        ("cand_001", "outside_in_pen", 2.0),   # Hero: pen inking
        ("cand_002", "slide_down", 1.2),        # Support: slide animation
    ]},
    {"scene_id": "zone_2", "base_scale": 2.3, "elements": [
        ("cand_003", "outside_in_pen", 2.0),   # Hero
        ("cand_004", "jelly_pop", 1.0),         # Support: bounce
        ("cand_005", "slide_up", 1.2),          # Support: slide up
    ]},
    # ... more scenes with 2-4 elements each
]

RENDER_CAM_ZOOM = 0.65
cam_y = 800.0
zone_spacing = 3200.0
GAP = 70.0

for s_idx, scene in enumerate(SCENES):
    cam_x = 1600.0 + s_idx * zone_spacing
    b_scale = scene["base_scale"]
    
    # Compute total width of all elements in this scene
    elem_widths = [int(crop_w * b_scale) for each element]
    total_w = sum(elem_widths) + GAP * (len(elems) - 1)
    cur_x = cam_x - total_w / 2.0  # Center horizontally
    
    for aid, anim_type, dur in scene["elements"]:
        sw, sh = int(cw * b_scale), int(ch * b_scale)
        elements_staging.append({
            "type": anim_type,  # NOT always outside_in_pen!
            "pos": (int(cur_x), int(cam_y - sh // 2)),
            "size": (sw, sh),
        })
        # Only append to hero_configs if anim_type == "outside_in_pen"
        if anim_type == "outside_in_pen":
            hero_configs.append((aid, t_start, dur))
        cur_x += sw + GAP
```

> [!CAUTION]
> **DEPRECATED — DO NOT USE**: The old `single-element-per-zone` pattern (1 element = 1 zone = 1 camera pan)
> produces nervous, rapid camera pans and monotonous all-inking animations.
> Always use multi-element scenes with varied animations as shown above.

---

## 🧠 6. Step 3.5 — AI Pre-Render Visual Director Gate

### Tool API:
```python
# Invoked automatically by the DAG. For manual testing:
pipeline.step_pre_render_director()  # Produces timing/final_render_plan.json
```

### Core Rules
1. **Zero Blank Screen**: Elements stay visible; they slide off-screen naturally via camera panning.
2. **START_ON_ANCHOR Strategy**: Drawing begins immediately when keyword is spoken (NOT at sentence end).
3. **Ground Truth Immutability**: Audio timestamps are unalterable; visuals align to audio.
4. **No premature fade-out**: `fade_out_at = None` for all elements in horizontal panning documentaries.
5. **Visual Semantic Mapping Contract (SMC — Anti-Sequential Numbering)**:
   - OpenCV contour detection orders entities geometrically or by area (`entity_01`, `entity_02`), NOT narratively!
   - NEVER map entities sequentially by index to scenes.
   - You MUST inspect the visual content of the asset (using contact sheets) and match it with 100% semantic accuracy to the sentence and Whisper timestamp where that concept is spoken.
6. **Bottom-Ink Grounding Law ($Y=840$)**:
   - In 2D graphic engines, layer anchor points default to center (`[width/2, height/2]`). Placing `[X, 840]` without setting anchor point will submerge the character's legs below the ground line by `height/2`.
   - The engine automatically computes `[center_x, bottom_ink_y]` via OpenCV alpha channel analysis. Ensure all standing characters and grounded props use bottom-ink anchors resting on $Y=840$.
7. **Semantic Motion VFX Matrix (Physically-Informed Animation)**:
   - *Microscopic organisms/viruses*: `zoom_in` + `radio_waves`/subtle pulse, floating at $Y \approx 480-540$.
   - *Predator strikes/attacks*: `whip_motion`/`speed_blur` + `scale_punch` (1.25x impact shake) + `border_flash`.
   - *Grounded characters/animals*: `squash_drop` or `pop_bounce` anchored at feet on $Y=840$ with soft `light_sweep`.
   - *Laboratory/instruments*: `slide_in` + metallic `light_sweep` across glassware/metal.
   - *Catastrophes/Impacts*: `elastic_pop` + `border_flash` + `camera_shake`.
   - *Abstract thoughts/scales/compass*: `rotation_spin` or `card_bloom` floating at $Y \approx 360-480$.
8. **Mandatory Keyframe Vision QA Sampling Gate**:
   - Before completing any section, sample 3-4 keyframe snapshots from the rendered video.
   - Inspect with `view_file` to confirm that feet touch the stage line and assets match the text card.

---

## 🔊 7. Step 4 — Audio Mixing (SFX + Ducking)

### SFX Auto-Generation (MANDATORY)
SFX cues are generated automatically from element staging — **never** defined manually:

```python
# Called internally by the pipeline:
sfx_cues = DynamicSectionEngine.generate_sfx_from_staging(elements_staging, camera_pans=pan_times)
```

**SFX Mapping by Animation Type:**

| Animation | SFX | Timing |
|---|---|---|
| `outside_in_pen` | `marker` (0.38 gain) + completion `pop` (0.22) | Marker during 90% of draw duration |
| `jelly_pop` | `pop` (0.35) | At t_start |
| `slide_down/up` | `whoosh` (0.40) + landing `pop` (0.25) | Whoosh at start, pop at 70% |
| `organic_grow` | `pop` (0.30) + `chime` (0.25) if dur > 1s | Pop at start, chime at 55% |
| `pulse_pop` | `chime` (0.35) + `pop` (0.25) | Chime at start, pop +0.15s |
| Camera Pan | `whoosh` (0.45) | At pan_start |

### The 18 Specialized SFX Sounds (`production_engine/sfx/*.wav`):

| Category | Sound IDs |
|---|---|
| ✏️ Drawing | `pencil_write`, `marker_scribble`, `pencil_stroke`, `marker_stroke` |
| 💨 Motion | `soft_whoosh`, `light_whoosh`, `reveal_whoosh`, `zoom_whoosh` |
| 👆 Appearance | `soft_pop`, `pluck_pop` |
| 🔔 Information | `soft_ding`, `bright_ping` |
| 💥 Impact | `soft_impact`, `light_hit` |
| ⚡ Surprise | `short_stinger` |
| ❌/✅ Result | `soft_error_beep`, `success_ding` |
| ✨ Highlight | `magic_sparkle` |

### Ducking Algorithm
```python
SFX_VOLUME_SCALE = 0.50                                    # All SFX at 50%
vo_envelope = convolve(abs(vo_audio), 120ms_RMS_window)    # Voiceover envelope
duck_gain = clip(1.0 - vo_envelope * 0.45, 0.55, 1.0)     # Duck floor: 55%
sfx_ducked = sfx_track * duck_gain
# Stereo: L = vo*0.95 + sfx*0.90, R = vo*0.95 + sfx*1.10
# Peak normalize to -0.4 dB → master_audio.wav (48kHz, 16-bit, Stereo)
```

---

## 🎥 8. Step 5 — Video Rendering

### Render Constants

| Constant | Value |
|---|---|
| `WIDTH, HEIGHT` | 1920 × 1080 |
| `FPS` | 30 |
| `CAM_ZOOM` | 0.74 (overrides code default of 0.58) |
| `TARGET_HAND_H` | 480 px |

### Tool API:
```python
engine = DynamicSectionEngine(section_dir)
final_video = engine.render_section(
    hero_configs=hero_configs,         # [(asset_name, t_start, t_dur), ...]
    elements_staging=elements_staging, # Full staging list
    camera_trajectory_fn=get_camera_state,
    duration_sec=duration_sec,
)
```

### Hero Inking Pre-Cache (Outside-In Contour-Following)

> [!CAUTION]
> **NEVER** use distance-transform ring-popping for inking.
> The hand's pen tip MUST trace the outer silhouette contour first, then spiral inward.

```python
from production_engine.dynamic_section_engine import build_solid_inking_cache

cache = build_solid_inking_cache(
    img_bgra=asset_rgba,
    duration_sec=t_dur,
    fps=30,
    ring_step=5,       # Erosion step between contour layers
    brush_radius=12    # Production standard brush width
)
# Returns: list of (frame_bgra, pen_tip_xy, rotation) per frame
```

**Inking Algorithm Steps:**
1. Generate contour-following strokes via `build_gapless_orbital_path()` (outer silhouette first)
2. Fill uncovered interior gaps with supplemental core strokes
3. Frame-by-frame ink reveal via `cv2.line()` + `cv2.circle()` under pen tip
4. Last 8% of frames = completion hold (100% revealed, no hand)

### World-to-Screen Projection
```python
scr_x = int(WIDTH / 2.0 + (world_x - cam_x) * cam_zoom)
scr_y = int(HEIGHT / 2.0 + (world_y - cam_y) * cam_zoom)
scr_w = int(world_w * cam_zoom)
scr_h = int(world_h * cam_zoom)
```

### Drawing Hand Composite
```python
from kivy.engine.render.hand_compositor import load_hand_asset_bgra, composite_hand_on_canvas_fast

if anim_type == 'outside_in_pen' and progress < 1.0:
    tip_wx = elem_x + (tip_ax / asset_w) * world_w
    tip_wy = elem_y + (tip_ay / asset_h) * world_h
    hand_sx = int(WIDTH/2 + (tip_wx - cam_x) * cam_zoom)
    hand_sy = int(HEIGHT/2 + (tip_wy - cam_y) * cam_zoom)
    frame = composite_hand_on_canvas_fast(frame, hand_bgra, HAND_TIP_X, HAND_TIP_Y, hand_sx, hand_sy)
```

### FFmpeg Encoding Pipeline
```python
# Raw frames → libx264 (or h264_nvenc)
ffmpeg -y -f rawvideo -vcodec rawvideo -s 1920x1080 -pix_fmt bgr24 -r 30 -i - \
       -c:v libx264 -preset ultrafast -crf 17 -pix_fmt yuv420p raw_video.mp4

# Multiplex video + audio
ffmpeg -y -i raw_video.mp4 -i master_audio.wav \
       -c:v copy -c:a aac -ac 2 -b:a 256k -shortest final_whiteboard_1080p.mp4
```

### Encoder Priority
1. **NVIDIA NVENC** (`h264_nvenc`, preset `p7`, CQ 18) — hardware accelerated
2. **libx264** (`ultrafast`, CRF 18) — CPU fallback

---

## 🔗 9. Step 6 — Multi-Section Merging

### Transition Style: Dissolve Through White
```
Section 1 → [Fade to White] → [Hold White 0.2s] → [Fade from White] → Section 2
               15 frames          6 frames            15 frames
               (0.5s)             (0.2s)               (0.5s)
```

### Tool API:
```bash
# Full project merge via Core Orchestrator:
python -m core.orchestration.orchestrator --project <project_slug> --assemble

# Or direct merge engine:
# production_engine/merge_master_sections.py
```

### Audio Stitching
- 0.2s silent pause between sections
- Whoosh sound (8% volume) at 0.35s before each transition
- Peak normalization to -0.2 dB

### Post-Merge Processing
1. Mux master audio + video → `deliverables/<TITLE>.mp4`
2. Copy section MP4s → `deliverables/sections/`
3. Write `project_manifest.json` indexing sections, durations, sizes
4. Purge temporary buffers from `scratch/`

---

## 📱 10. Step 7 — Vertical Reels / Shorts Export (9:16)

### Tool API:
```bash
python production_engine/export_section_reels.py --sections 04_spartacus 05_tlahuicole
python production_engine/export_section_reels.py --all
python production_engine/export_section_reels.py --all --gpu
```

### Layout (1080 × 1920):
- 16:9 video placed at y=620 (1080×608)
- Arabic category badge + title at top
- Engagement question card at y=1288
- Animated progress bar at y=1912
- Output: `deliverables/reels/<NN>_<Topic>_Reels_1080x1920.mp4`

---

## 🎨 11. Animation Types Reference & Multi-Element Scene Composition

### Animation Types

| Animation | Duration | SFX | Visual Behavior | Primary Role |
|---|---|---|---|---|
| `outside_in_pen` | 1.4–2.5s | `marker` | Hand traces outer silhouette first, spirals inward. Ink under pen tip only. 8% hold frames. | **Lead / Hero Assets Only** |
| `jelly_pop` | 0.8–1.2s | `pop` | Pops from zero with elastic overshoot: `ease_out_back(progress, s=1.8)` | Secondary accents / weapons / rapid reveals |
| `slide_down` | 1.0–1.4s | `whoosh`+`pop` | Slides down 80px: `y_offset = -80 + 80 * ease_out_cubic(progress)` | Supporting characters / explanatory figures |
| `slide_up` | 1.0–1.4s | `whoosh`+`pop` | Same as slide_down but from +80px below | Ground actions / warnings / tactical movements |
| `organic_grow` | 1.2–1.8s | `pop`+`chime` | Width before height: `scale_x = 0.4 + 0.6 * ease_out_cubic(p)` | Environments / thematic concepts / aftermath |
| `pulse_pop` | 1.0–1.3s | `chime`+`pop` | Pulsating: `1.0 + 0.12 * sin(p * π * 3) * (1.0 - p)` | Dramatic turning points / psychological moments |

### 🎬 Mandatory Scene Composition Rules (قواعد تكوين المشاهد متعددة العناصر)

> [!IMPORTANT]
> **MULTI-ELEMENT MICRO-ZONING (NO 1:1 CAMERA RUSH)**:
> - **2 to 4 Elements per Scene**: Every camera zone/scene MUST contain **2, 3, or 4 complementary elements** grouped by narrative context. Never isolate every single element into its own separate zone with a nervous camera pan after every single element.
> - **Varied Animation Distribution**: In each scene, typically **only 1 key Hero element** is drawn with the hand pen (`outside_in_pen`). The remaining supporting elements in the scene enter sequentially with varied transitions (`slide_down`, `slide_up`, `jelly_pop`, `pulse_pop`, `organic_grow`).
> - **Calm Camera Operation**: The camera remains completely stationary on the scene while all its elements appear sequentially in Storyboard Order. Across a 50s section with ~20 elements, there should only be **5 to 7 smooth camera pans** total.
> - **Symmetric Horizontal Layout**: Elements within a scene are dynamically centered around `cam_x` with consistent spacing (`GAP = 70–100px`), ensuring balanced composition and zero clipping.

---

## 📷 12. Camera System Reference

### Easing Functions

| Function | Formula | Use Case |
|---|---|---|
| `smootherstep(t)` | `t³(t(6t-15)+10)` | Camera pans (ultra-smooth S-curve) |
| `ease_out_cubic(t)` | `1-(1-t)³` | Element slide deceleration |
| `ease_out_back(t, s)` | Overshooting cubic | Jelly pop bounce |

### 100% Pure Horizontal Camera Trajectory (MANDATORY)

> [!IMPORTANT]
> Camera Y is **permanently locked** at `Y = 800.0`. All panning is horizontal only (dY = 0).

```python
FIXED_Y = 800.0
CAM_ZOOM = 0.74  # Production calibrated standard

def get_camera_state(t):
    """100% PURE HORIZONTAL CAMERA: Y strictly constant."""
    if t < CAM_PANS[0][0]:
        return (CAM_PANS[0][2], FIXED_Y, CAM_ZOOM)
    for (t_start, t_end, x_from, x_to) in CAM_PANS:
        if t < t_start:
            return (x_from, FIXED_Y, CAM_ZOOM)
        elif t < t_end:
            p = smootherstep((t - t_start) / (t_end - t_start))
            cx = x_from + (x_to - x_from) * p
            return (cx, FIXED_Y, CAM_ZOOM)
    return (CAM_PANS[-1][3], FIXED_Y, CAM_ZOOM)
```

### Camera Pan Rules
- **Dynamic Zone Traversal**: Always use `zone_order = list(layout_data["zones"].keys())`. Never hardcode.
- **Pans in Speech Pauses Only**: 0.4–0.85s, concluding 0.05s before next zone starts.
- **Explanation Hold**: Camera holds steady on completed elements during narration.
- **Zero Blank Screen**: Elements stay visible; slide off naturally via camera panning.
- **No Zoom-Out at End**: Camera holds steady on final zone until video completion.

---

## 🔊 13. Audio Engineering Reference

### Signal Flow
```
voiceover.wav → Peak Normalize (-0.5 dB)
                     ↓
               ┌─────┴──────┐
               │  Envelope   │ (120ms RMS window)
               └─────┬──────┘
                     ↓
SFX tracks → Duck Gain = clip(1 - env*0.45, 0.55, 1.0) → Ducked SFX
                                                              ↓
                                                    ┌─────────┴──────────┐
                                                    │  Stereo Pan Mix    │
                                                    │  L: vo*0.95+sfx*0.90│
                                                    │  R: vo*0.95+sfx*1.10│
                                                    └─────────┬──────────┘
                                                              ↓
                                                    Peak Normalize (-0.4 dB)
                                                              ↓
                                                       master_audio.wav
                                                    (48kHz, 16-bit, Stereo)
```

### Gain Cookbook

| Element | Gain Range |
|---|---|
| Voiceover peak normalize | 0.94 (-0.5 dB) |
| Marker SFX base volume | 0.25 (25%) |
| Other SFX base volume | 0.50 (50%) |
| Duck floor (min SFX during speech) | 0.55 (55%) |
| Master peak limit | 0.96 (-0.4 dB) |

---

## 🔧 14. Troubleshooting & Quality Lessons

### Audio Truncated / Missing Words at End (انقطاع خاتمة الصوت)
**Cause:** Chunks > 35 words. Gemini TTS silently stops at ~20-25s.
**Fix:** Safe semantic chunks under 28 words + automated tail-verification loop with `gemini-3.6-flash`.

### Audio-Visual Desync (عدم تطابق الصوت مع الرسومات)
**Cause:** Manual guesswork timestamps instead of extracted ones.
**Fix:** Define anchor phrases → `align_anchor_phrases()` → 0.20s lead formula.

### Elements Too Small / Invisible (صغر حجم العناصر أو اختفائها)
**Cause:** Using raw crop pixel sizes (~300×250px) without scaling. With `CAM_ZOOM=0.58`,
crop renders at ~200×150px on a 1920×1080 canvas (~2% coverage = effectively invisible).
**Fix:** Scale crops UP by 2.0-3.2x before world-space placement. Use `BASE_SCALE=3.0` for TCM v2
single-element zones. Use `RENDER_CAM_ZOOM=0.68` and `cam_y=800.0`. Final screen coverage should be 10-15%+.
**Verification:** Extract a frame and check `np.sum(np.any(frame < 240, axis=2)) / total_pixels > 0.05`.

### Elements Completely Missing / Blank Canvas in TCM v2 (اختفاء العناصر كلياً في رندر TCM v2)
**Cause 1:** `engine.assets_dir` defaults to `sections/<name>/assets/` while TCM-DS v2 crops reside in `scratch/tcm_v2_run/crops/` with `cand_001.png` names. The engine fails to load the image silently, rendering blank frames!
**Fix:** Explicitly override `engine.assets_dir = str(crops_dir)` before calling `render_section()`.
**Cause 2:** Asset ID mismatch in `elements_staging` (e.g. referencing `cand_001` when file is `cand_1.png`). Always ensure filenames match `beat.visual_id`.

### Blank White Screen During Narration (شاشة بيضاء فارغة)
**Cause:** Premature `fade_out_at` forcing elements to vanish during explanation.
**Fix:** Set `fade_out_at = None`. Elements remain visible; exit screen via camera panning.

### Elements Appearing Late (ظهور العناصر متأخرة)
**Cause:** Using `COMPLETE_ON_ANCHOR` pegged to end of long sentence.
**Fix:** Switch to `START_ON_ANCHOR` with 0.15–0.20s lead formula.

### Missing Storyboard Concepts (إسقاط عناصر جوهرية)
**Cause:** Truncating asset extraction at arbitrary column count.
**Fix:** Count all connected components per row, cross-reference with script, map 100%.

### Elements Clipped at Screen Edges (تآكل العناصر في الحواف)
**Cause:** Zone isolation gap too small or cam_zoom too tight without margin checks.
**Fix:** Enforce `cam_zoom = 0.74` with safe margins ≥ 140px. Check screen bounds: X ∈ [140..1780].

### Hand Sprite Not Showing
**Cause:** `hand_bgra` is `None` or off-screen.
**Fix:** Verify `kivy/data/images/drawing-hand.png` and `hand-mask.png` exist.

### Black Frames in Output
**Cause:** FFmpeg pipe error.
**Fix:** Ensure `pix_fmt bgr24` matches OpenCV channel order. Check `ffmpeg_render.log`.

---

## 🔗 15. TCM-DS v2 Three-Contract Pipeline

> [!IMPORTANT]
> The TCM-DS v2 (Three-Contract Model — Deterministic Scheduling) separates **semantic understanding**
> (AI/LLM) from **physical scheduling** (deterministic, zero LLM). The AI understands the storyboard
> and story; the runtime computes timing from Whisper and visual constraints without any LLM call.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TCM-DS v2 Pipeline                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Contract 1: visual_manifest.json (AI/Vision)                              │
│  ├── AdaptiveCandidateExtractor: Recursive XY-cut → organic crops          │
│  ├── DemandEstimator: pixel_mass + contour + edge_density → draw_demand    │
│  └── Output: candidates with bounding boxes, complexity scores, roles      │
│                                                                             │
│  Contract 2: narrative_visual_map.json (AI/LLM)                            │
│  ├── NarrativeDirector: Maps script concepts to visual candidates          │
│  ├── Whisper word-level timestamps → trigger anchors                       │
│  └── Output: concept → candidate bindings + trigger_anchor phrases         │
│                                                                             │
│  Contract 3: final_render_plan.json (Deterministic, Zero LLM)              │
│  ├── ConstraintVisualScheduler: Whisper anchors → ink_start/ink_end        │
│  ├── DemandEstimator: complexity → draw_duration_s                         │
│  ├── Collision detection + viewport placement                             │
│  └── Output: VisualBeat[] with exact timestamps, verified by crypto hashes │
│                                                                             │
│  Render: render_guan_yu_tcm_v2.py (Reference Implementation)              │
│  ├── Reads Contract 3 + crop PNGs                                         │
│  ├── Scales elements UP (BASE_SCALE=3.0, RENDER_CAM_ZOOM=0.68)            │
│  ├── Builds smootherstep camera trajectory from zone_centers               │
│  └── Feeds hero_configs + elements_staging → DynamicSectionEngine          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Contract 3 Schema (FinalRenderPlan)
```python
from core.contracts.render_plan import FinalRenderPlan, VisualBeat, TimingSpec

# Each VisualBeat contains:
# - beat_id: "beat_001"
# - visual_id: "cand_001" (matches crop filename)
# - resolved_anchor: {matched_text, whisper_t_start, whisper_t_end, match_tier, confidence}
# - timing: {lead_in_s, ink_start_s, ink_end_s, draw_duration_s, speed_multiplier, hold_until_s}
# - viewport: {target_center, scale, render_layer, opacity}
# - collision_classification: SAFE_COMPOSITION | INTENTIONAL_OVERLAP | ...
```

### End-to-End Pipeline Execution (Contract 1 → Contract 2 → Contract 3 → Video)

```python
from core.contracts import RenderPolicy
from core.vision.adaptive_candidate_extractor import AdaptiveCandidateExtractor
from core.vision.visual_reviewer_engine import VisualReviewerEngine
from core.narrative.narrative_director import NarrativeDirector
from core.scheduling.constraint_scheduler import ConstraintVisualScheduler
from production_engine.dynamic_section_engine import DynamicSectionEngine, smootherstep

# --- STAGE 1: Adaptive Candidate Extraction (Zero Fixed Grid) ---
extractor = AdaptiveCandidateExtractor()
candidates, contact_sheet = extractor.extract_candidates(storyboard_path, output_crops_dir=crops_dir)

# --- STAGE 2: Contract 1 - Pure Visual Manifest (Pure Visual Truth) ---
# CRITICAL: Must NEVER contain transcript or Whisper audio timestamps!
reviewer = VisualReviewerEngine()
manifest = reviewer.review_and_build_manifest(
    storyboard_path=storyboard_path,
    candidates=candidates,
    storyboard_id=sec_id,
    canvas_dimensions=(1920, 1080),
    output_manifest_path=manifest_path,
)

# --- STAGE 3: Contract 2 - Narrative Visual Map (Semantic Bridge) ---
# Maps narration concepts to candidate visual IDs with trigger anchors
narrative_map = NarrativeDirector.build_narrative_map_for_section(
    manifest=manifest,
    script_path=script_path,
    output_map_path=map_path,
)

# --- STAGE 4: Contract 3 - Deterministic Final Render Plan (Zero LLM) ---
# Compiles physical execution plan from Whisper words + visual demand
scheduler = ConstraintVisualScheduler(policy=RenderPolicy.default_whiteboard())
plan = scheduler.compile_render_plan(
    manifest=manifest,
    narrative_map=narrative_map,
    whisper_words=all_words,
    audio_duration_s=audio_dur,
    output_plan_path=plan_path,
)

# --- STAGE 5: Multi-Element Scene Composition & Rendering (OSAS v3.1) ---
# CRITICAL: Group elements into 2-4 element scenes. Only Hero = outside_in_pen.
# Reference implementation: scripts/run_08_lu_bu_osas_pipeline.py

beats_map = {b.visual_id: b for b in plan.execution_tracks.visual_beats}

# Define multi-element scenes (2-4 elements per scene, grouped by narrative theme)
SCENES = [
    {"scene_id": "zone_1", "base_scale": 2.3, "elements": [
        ("cand_001", "outside_in_pen", 2.0),  # Hero: pen inking
        ("cand_002", "slide_down", 1.2),       # Support: varied animation
    ]},
    # ... define all scenes with 2-4 elements each
]

RENDER_CAM_ZOOM = 0.65
cam_y = 800.0
zone_spacing = 3200.0
GAP = 70.0
elements_staging = []
hero_configs = []
scene_cam_x_list = []
scene_timings = []

for s_idx, scene in enumerate(SCENES):
    cam_x = 1600.0 + s_idx * zone_spacing
    scene_cam_x_list.append(cam_x)
    b_scale = scene["base_scale"]
    scene_elems = []
    for aid, anim_type, dur in scene["elements"]:
        crop = cv2.imread(f"{crops_dir}/{aid}.png", cv2.IMREAD_UNCHANGED)
        ch, cw = crop.shape[:2]
        sw, sh = int(cw * b_scale), int(ch * b_scale)
        beat = beats_map[aid]
        scene_elems.append({"aid": aid, "anim_type": anim_type, "w": sw, "h": sh,
                            "t_start": beat.timing.ink_start_s, "t_dur": dur})
    total_w = sum(e["w"] for e in scene_elems) + GAP * (len(scene_elems) - 1)
    cur_x = cam_x - total_w / 2.0
    for e in scene_elems:
        elements_staging.append({
            "id": f"{e['aid']}_{s_idx}", "asset": e["aid"],
            "t_start": e["t_start"], "t_dur": e["t_dur"],
            "type": e["anim_type"],  # NOT always outside_in_pen!
            "pos": (int(cur_x), int(cam_y - e["h"] // 2)),
            "size": (e["w"], e["h"]), "depth": 5, "fade_out_at": None,
        })
        if e["anim_type"] == "outside_in_pen":  # Only hero elements get inking cache
            hero_configs.append((e["aid"], e["t_start"], e["t_dur"]))
        cur_x += e["w"] + GAP

# Build 5-7 calm camera pans between scenes (NOT 1 pan per element!)
camera_pans = build_scene_camera_pans(scene_timings, scene_cam_x_list)
camera_trajectory_fn = build_horizontal_camera_trajectory(camera_pans, scene_cam_x_list[0])

# Auto-generate enriched SFX & mix master audio
sfx_cues = DynamicSectionEngine.generate_sfx_from_staging(elements_staging, camera_pans=[p[0] for p in camera_pans])
engine = DynamicSectionEngine(str(sec_dir))
engine.assets_dir = str(crops_dir)
engine.mix_master_audio(str(voice_path), sfx_cues, audio_dur)
engine.render_section(hero_configs, elements_staging, camera_trajectory_fn, audio_dur)
```

### Output Artifacts

| File | Location | Purpose |
|---|---|---|
| `visual_manifest.json` | `scratch/tcm_v2_run/` | Contract 1: visual candidates + complexity |
| `narrative_visual_map.json` | `scratch/tcm_v2_run/` | Contract 2: concept ↔ candidate bindings |
| `final_render_plan.json` | `scratch/tcm_v2_run/` | Contract 3: physical execution plan |
| `crops/cand_XXX.png` | `scratch/tcm_v2_run/crops/` | Organic BGRA crop PNGs |
| `contact_sheet.png` | `scratch/tcm_v2_run/crops/` | Visual overview of all candidates |
| `final_whiteboard_tcm_v2_1080p.mp4` | Section root | Rendered video output |

---

## 🚀 16. Production Checklist (قائمة التحقق الإلزامية — OSAS v3.1)

```
[ ]  1. Check storyboard.png exists → If missing, search project_content/images/ or HALT & alert user.
[ ]  2. Extract assets via adaptive candidate extractor (zero fixed grid, organic silhouettes).
[ ]  3. Generate Fenrir TTS voiceover with safe chunking (< 28 words) + STT tail-verification.
[ ]  4. Extract Faster-Whisper millisecond timestamps → timing/whisper.json.
[ ]  5. Build semantic anchor map: map each asset to its trigger word in the narration.
[ ]  6. Compile visual choreography with single-ink mutex + 10 QA gates (100% coverage).
[ ]  7. ⚠️ DEFINE MULTI-ELEMENT SCENES: Group assets into 5-8 scenes of 2-4 elements each.
[ ]  8. ⚠️ ASSIGN VARIED ANIMATIONS: Only 1 Hero element per scene uses outside_in_pen.
         Secondary elements MUST use slide_down, slide_up, jelly_pop, pulse_pop, or organic_grow.
[ ]  9. Layout: Symmetric horizontal centering within each scene (GAP=70px, scale=1.8-2.3).
[ ] 10. Camera: Only 5-7 total calm pans. Camera STEADY on each scene during element reveals.
[ ] 11. Build inking cache ONLY for hero elements (outside_in_pen) via build_solid_inking_cache().
[ ] 12. Auto-generate SFX cues from staging → mix 48kHz master audio with ducked SFX.
[ ] 13. Render 1080p/30fps video using NVENC p7 hardware acceleration.
[ ] 14. Mux video + audio → final_whiteboard_1080p.mp4.
[ ] 15. Copy deliverable to output_animations/<project>/deliverables/sections/.
[ ] 16. VERIFY: Extract sample frames → multi-element composition visible, zero blank screens.
[ ] 17. (Optional) Merge all sections → master video via Core Orchestrator --assemble.
[ ] 18. (Optional) Export vertical Reels (9:16) → export_section_reels.py --all.
[ ] 19. Micro-Retention GIFs: Max 2-3 transparent overlays (scale_w: 160-200px) in upper negative space.
[ ] 20. Strict Zero-BGM Mandate: Background music (BGM) is strictly prohibited. Pure voice narration only.
[ ] 21. Anti-Freeze Guarantee: ffmpeg clamp -t exact_audio_dur with eof_action=pass (NO shortest=1).
[ ] 22. Clean Exit Sweep: All scene elements must reach opacity 0% at least 0.35s before section cut.

⚠️ CANONICAL REFERENCE: scripts/run_08_lu_bu_osas_pipeline.py
```

---

## 🎨 17. Micro-Retention Transparent GIFs & Strict Zero-BGM Policy

> [!CAUTION]
> **STRICT ZERO-BGM MANDATE (حظر الموسيقى التصويرية):**
> * Background music (BGM) is **strictly forbidden** in whiteboard explainer productions.
> * Whiteboard animations depend entirely on the cognitive clarity of **uncluttered, pristine voiceover narration** accompanied only by natural drawing sound effects (SFX).
> * Never inject, mix, or duck musical background tracks into whiteboard sections.

### 1. Curated Transparent GIFs (`assets/gifs/`):
* 26 clean, alpha-channel GIF overlays: `thumbs_up_like.gif`, `subscribe_bell.gif`, `dna_sequence.gif`, `heart_monitor.gif`, `biohazard_symbol.gif`, `optical_vision.gif`, `research_magnifier.gif`, `question_mark_pulse.gif`.

### 2. Micro-Retention GIF Overlay Rules:
1. **Subtle Scale (`scale_w: 160-200px`):** Accent icons that break monotony without competing with hero whiteboard inking.
2. **Constrained Duration (`4.0s - 8.0s`):** Appears during key thematic moments only; never left looping indefinitely across multiple thoughts.
3. **Upper Negative Space Placement ($Y \approx 310-360$):** Positioned away from text cards and at least 80px above grounded characters.
4. **Pre-Cut Sweep:** Fade out at least 0.35s before the section cut.

---

## 🛡️ 18. Zero-Regression Constitution: Anti-Freeze, Boundary Precision & Layout Perfection

Based on production audits from large multi-section documentary projects, the AI agent must strictly follow these hard rules to prevent all regression errors:

### 1. The Zero Boundary Freeze Law (FFmpeg Infinite Loop Fix):
* **The Root Bug:** Passing `-ignore_loop 0` with GIFs creates an infinite video stream. Using `-shortest` or `overlay=...:shortest=1` causes FFmpeg to either terminate prematurely on the first GIF loop or stall at the end, repeating the last video frame for 1.5s to 10s of dead silence!
* **The Mandatory Solution:**
  1. Measure exact audio duration via `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1`.
  2. Overlay filter MUST use `eof_action=pass` and **NEVER** `shortest=1`:
     `overlay=X:Y:eof_action=pass:enable='between(t,st,en)'`
  3. Clamp the final output duration explicitly: `-t {exact_audio_dur:.3f}`.
  4. Result: 100.00% audio-video sync with 0.000s frozen boundary pause between sections.

### 2. Stage Grounding & 2-Beat Visual Hierarchy:
* **Characters Grounded at $Y=840$:** Humans, scientists, and animals must sit firmly on the stage floor ($Y=840$, anchor at lowest ink pixel). Never float characters at $Y=500-520$.
* **2-Beat Phased Storytelling:** Never crowd 3-4 simultaneous elements. Split complex scenes into Beat A (left character + right card) fading out before Beat B (right character + left card) enters.
* **Preserve Small Assets:** Never artificially stretch microscopic entities (parasites/viruses < 150px) to 500px. Keep them small as accents or pair them with composite hero assets.
* **Pre-Cut Exit Sweep:** All visual elements and text cards in the section's final scene must fade to 0 opacity at least **0.35s before the section cut**, ensuring zero visual ghosting or half-disappeared elements at transition boundaries.

