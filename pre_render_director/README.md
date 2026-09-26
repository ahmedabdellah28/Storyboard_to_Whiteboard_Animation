# AI Pre-Render Visual Director

The **AI Pre-Render Visual Director** is the final intelligent synchronization and QA layer in the Whiteboard Animation pipeline, situated immediately before the **Video Renderer**.

```text
SCRIPT
   ↓
SECTION
   ↓
PROFESSIONAL TTS
   ↓
SECTION AUDIO (Immutable Ground Truth)
   ↓
FASTER-WHISPER (Immutable Ground Truth)
   ↓
WORD / SENTENCE TIMING
   ↓
SEMANTIC ANALYSIS
   ↓
ASSET EXTRACTION & CATALOG
   ↓
INITIAL VISUAL TIMELINE
   ↓
────────────────────────────────
AI PRE-RENDER VISUAL DIRECTOR
────────────────────────────────
   ↓
FINAL RENDER PLAN (final_render_plan.json)
   ↓
VIDEO RENDERER
   ↓
SECTION VIDEO
```

---

## 1. Strict Boundary & Non-Negotiable Principles

- **AI is NOT a Renderer**: AI never generates video frames, alters image pixels, runs FFmpeg, or directly draws strokes.
- **Audio is Immutable Temporal Ground Truth**: `section.wav` and Whisper word/segment timestamps are strictly read-only and never modified.
- **Script is Immutable Semantic Ground Truth**: Narration text is fixed; words cannot be deleted, added, or rewritten.
- **AI Responsibilities**: `UNDERSTAND`, `VALIDATE`, `COMPARE`, `CORRECT`, `OPTIMIZE`, `PLAN`.
- **Renderer Contract**: Downstream video renderers receive a self-contained JSON (`final_render_plan.json`) requiring zero semantic or language comprehension.

---

## 2. Multimodal Visual Evidence Inspection

The Director combines **Semantic Metadata** with **Real Visual Evidence**:
- Inspects asset images directly via Gemini Vision API (`image_path` + PIL / base64).
- Evaluates asset visual features (e.g., character pose, surface type, props).
- Detects contradictions between spoken text and visual depiction (e.g., sleeping on concrete ground vs. sitting on a park bench).

---

## 3. The 12 Pre-Render Validation Checks

Before any plan is released to the Renderer, it must pass 12 deterministic checks:

| Check ID | Description | Severity | Gate Impact |
| :--- | :--- | :--- | :--- |
| **CHECK 01** | Every visual event references a valid asset ID | ERROR | Blocks Render |
| **CHECK 02** | Every referenced asset exists on disk | ERROR | Blocks Render |
| **CHECK 03** | Every asset semantically matches its speech anchor | WARNING | Review Flag |
| **CHECK 04** | No contradictory visual asset is displayed | ERROR | Blocks Render |
| **CHECK 05** | Asset visual dependencies are satisfied chronologically | ERROR | Blocks Render |
| **CHECK 06** | Drawing duration meets feasible drawing speed threshold | WARNING | Auto-Pitched |
| **CHECK 07** | No impossible timing (start < 0, end > duration, start >= end) | ERROR | Blocks Render |
| **CHECK 08** | No invalid overlaps (drawing collision without parallel flag) | WARNING | Auto-Pitched |
| **CHECK 09** | SFX markers have valid anchors and sane intervals | WARNING | Auto-Aligned |
| **CHECK 10** | Camera target exists and is visible on canvas | WARNING | Safe Fallback |
| **CHECK 11** | Visual state transitions are chronological and continuous | ERROR | Blocks Render |
| **CHECK 12** | Canvas density stays within maximum capacity threshold | WARNING | Fade Oldest |

### Final Gate Status:
- `PASS`: 100% compliant, ready for immediate rendering.
- `PASS_WITH_WARNINGS`: Non-critical warnings present; render proceeds safely.
- `BLOCK_RENDER`: Critical errors detected; output flagged for human review in `review_report.json`.

---

## 4. Discrete Timeline Patches

The Director avoids destructive rewrites. Corrections are applied via atomic, surgical patches:

- `ADD_EVENT`: Insert new visual/SFX/camera event.
- `REMOVE_EVENT`: Drop unsuited or cluttering event.
- `UPDATE_EVENT`: Adjust timing boundaries or visual attributes.
- `CHANGE_ASSET`: Replace contradictory asset with an accurate catalog match.
- `MOVE_EVENT` / `RESIZE_EVENT`: Re-anchor drawing timing.
- `KEEP_EVENT`: Confirm existing timing.

---

## 5. Usage & CLI

```bash
# Run on a section directory
python -m pre_render_director.main --section sections/01_homeless

# Run with deterministic offline mock AI (zero API quota usage)
python -m pre_render_director.main --section sections/01_homeless --mock-ai

# Specify custom output locations
python -m pre_render_director.main --section sections/01_homeless \
    --output sections/01_homeless/timing/final_render_plan.json \
    --report sections/01_homeless/timing/review_report.json
```
