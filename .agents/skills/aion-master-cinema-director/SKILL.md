---
name: aion-master-cinema-director
description: >-
  Complete AION Studio V8 (V7 Master Cinema + Adaptive Director v4 Default) directing & production skill for Educational
  Explainer (`--format educational`, DEFAULT) and Cinematic Storytelling (`--format narrative`) videos on ANY script and
  ANY extracted assets. Covers default 720p GPU rendering, sub-millisecond SQLite FTS5 resource search (2,410 icons,
  380 CC0 SFX, GPU VFX/connectors, palettes, fonts), dynamic icon placement, semantic spatial choreography, diverse
  inter-element connectors, whisper-soft particles, single persistent top neon-glass live-typing HUD, and multi-dialect TTS.
---

# AION Studio V8 — Master Cinema & Adaptive Director v4 (Default Pipeline)

Activate this skill whenever planning, directing, compiling, or refining any video (16:9 documentary/explainer or 9:16 Shorts/Reels) inside `e:\image_to_animate`. Everything is **100% general-purpose** across any language, genre, script, and extracted asset set.

---

## 1. Automatic Defaults (الإعدادات التلقائية المعتمدة)

Running a single `studio compile` command now automatically activates the complete upgraded stack:
- **Resolution:** **`720p` DEFAULT** (`1280×720` for 16:9, `720×1280` for 9:16) across `studio compile`, `render`, and `shorts` (`~45–60s` GPU render per 60s section). Pass `--resolution 1080p` only when Full HD is explicitly requested.
- **Visual Format:** **`--format educational` DEFAULT** (`Master Edu` — pass `--format narrative` or `--format auto` when desired).
- **Adaptive Director v4 (`v2 + v3 + v4`):** **`ON` BY DEFAULT** (`--director-v4` is enabled automatically; pass `--no-director-v4` only to opt out). Automatically executes:
  1. `asset_manifest.v2.json` (multi-pattern catalog loader `01_section.json` / `section_01.json` + real Pillow PNG bounds/alpha/dominant-color inspection).
  2. `cinematic_plan.v2.json` (semantic beats, human emotions, `focal_target` verified inside scene, `eye_trace`, `cut_reason`).
  3. `motion_plan.v3.json` (normalized `0..1` keyframe tracks, `settle_hold_sec`, `easing_to_next`, capability checks).
  4. **Collision-free Semantic Spatial Choreography** (chronological `chrono_items` zero-overlap guard + dynamic layouts: `causal_left_to_right`, `asymmetric_right_hero`, `restrained_negative_space`, `tight_comparison`, `centered_focus`).
  5. **Dynamic Icon Placement + Diverse Inter-Element Visual Connectors** (NOT just repeated arrows or top-right icons!).
  6. **Auto-scrubbing** of `[...]` editorial notes from HUD/typography, **silent `quran_cards`** (SFX suppressed inside verse intervals), and real **WCAG Pillow `contrast_metrics`**.

---

## 2. Sub-Millisecond Resource Search for Any AI Model (`SQLite FTS5`)

Never guess effect/icon/SFX names and **never** load thousands of filenames into your prompt context. Use the local code-backed [`ResourceRegistry`](file:///e:/image_to_animate/core/aion/resource_registry.py) (**2,838 verified installed resources**, benchmarked offline on this machine at **`p50 = 0.53 ms` | `p95 = 1.46 ms`** across 120 bilingual Arabic/English queries):

| Kind (`--kind`) | Verified Count | Source in Repo | Notes |
| :--- | :---: | :--- | :--- |
| `icon` | **2,410** | `assets/icons_lucide/*.svg` | Trim-Paths + 3-layer animated GPU rigs |
| `sfx` | **380** | `assets/sfx_pro/`, `assets/sfx/`, `assets/audio/` | CC0 WAV/MP3 mixed via `-12 dB` RMS ducking |
| `effect` | **13** | `core/aion/ecgc_compiler.py` | GPU-fast VFX & connectors; `cclightrays` / `blur>=80px` **auto-banned** |
| `background` | **10** | `LIVING_GRADIENT_PALETTES` | Dark & light 4-Color Gradient moods |
| `font` | **5** | `typography_director.py` | HarfBuzz-verified Arabic (`IBM Plex Sans Arabic`, `Cairo`, `Amiri`) & English |
| `asset` | Per-section | `inputs/storyboard_catalog/*.json` | Project PNGs with real Pillow dimensions & luma |

### Two-Stage Retrieval (CLI & Python)
```powershell
# Stage 1 — Fast Top-K Bilingual Search (<1.5ms) by Arabic/English meaning:
python pipeline_cli.py studio resources --query "توهج" --kind effect --limit 6
python pipeline_cli.py studio resources --query "قفل" --kind icon --limit 6
python pipeline_cli.py studio resources --query "whoosh impact" --kind sfx --limit 8
python pipeline_cli.py studio resources --project <name> --section 01 --query "سفينة" --kind asset

# Rebuild SQLite FTS5 catalog after adding new icons/SFX:
python pipeline_cli.py studio resources --rebuild --json
```
In Python: call `reg.search_resources(query, kinds=[...], only_supported=True, limit=12)` first, then `reg.get_resource_details(selected_ids)` ONLY for the chosen IDs to inspect exact parameter bounds (`min`/`max`/`default`) and fallbacks.

---

## 3. End-to-End Model Workflow (سير العمل القياسي الكامل لأي موديل)

Execute strictly through `pipeline_cli.py` inside isolated runs (`exports/runs/<run_id>/`). **Never read raw storyboard or entity PNGs before rendering** (JSON + timing only).

```powershell
# 1. Inspect project state (or scaffold a new project with dialect)
python pipeline_cli.py status --detailed --project <name>
# New project examples:
#   Saudi Arabic (default):   python pipeline_cli.py new <name> --lang ar --dialect saudi_white --sections 10
#   Egyptian Male (Fenrir):   python pipeline_cli.py new <name> --lang ar --dialect egyptian --sections 10
#   Egyptian Female (Kore):   python pipeline_cli.py new <name> --lang ar --dialect egyptian_female --sections 10
#   US English (Puck):        python pipeline_cli.py new <name> --lang en --dialect us_casual --sections 10

# 2. Prepare script, 48kHz -14 LUFS voiceover, and Faster-Whisper timing
python pipeline_cli.py script --all --project <name>
python pipeline_cli.py voice  --all --project <name>   # optional: --dialect egyptian --voice Puck
python pipeline_cli.py timing --all --project <name>

# 3. Import pre-extracted assets ZIP & semantic map
python pipeline_cli.py extract --all --project <name> --from-zip "<path_to_zip>"
python pipeline_cli.py semantic-map --all --project <name>

# 4. Canary 1-section render (DEFAULT = 720p + Master Edu + Adaptive Director v4!)
python pipeline_cli.py studio compile --project <name> --section 01 --run-id <run_id>

# 5. Post-render visual QA (REQUIRED before --all):
#    Open exports/runs/<run_id>/sections/section_01/qa/creative_contact_sheet.png
#    Inspect qa/creative_quality_report.json (verify PASS, 0 overlaps, crisp RTL, clean HUD)

# 6. Render all sections (720p default) -> check E: disk (>2GB) -> merge master MP4
python pipeline_cli.py studio compile --project <name> --all --run-id <run_id>
python pipeline_cli.py studio merge   --project <name> --run-id <run_id>

# 7. Produce vertical 9:16 Shorts (reuses mastered audio + dialect-matched reusable CTA)
python pipeline_cli.py studio shorts --action plan   --project <name>
python pipeline_cli.py studio shorts --action render --project <name> --all --run-id shorts_<id>
```

---

## 4. Visual Choreography, Connectors & Motion Vocabulary (V8 Standard)

1. **Dynamic Icon Placement (Never Frozen Top-Right):**
   - `causal_left_to_right` -> centered above visual bridge (`50% W, 29% H`)
   - `asymmetric_right_hero` -> upper-left anchor (`28% W, 29% H`)
   - `restrained_negative_space` -> upper-right breathing space (`70% W, 28% H`)
   - `tight_comparison` -> centered on clash axis (`50% W, 30% H`)
   - `centered_focus` -> upper-left flank or centered solo halo, cycling entrances (`slide_down`, `soft_fade`, `slide_left`, `pop_settle`, `slide_right`, `zoom_drift`).
2. **Diverse Inter-Element Visual Connectors (Not Just Arrows!):**
   - Re-anchored glowing curved Bezier arrows + `light_sweep` gleam.
   - Vertical glowing clash divider + central nexus orb (`shape_node`) + `blur` rack-focus (`22 -> 0`).
   - Expanding concentric radar/target rings (`repeater_rings`) + dotted strategic route.
   - Concentric tension shockwave hub (`repeater_rings` + `shape_node`) + fast `distortion` ripple (`0.45s`).
   - Climax energy bridge + **whisper-soft ambient particles** (`birth_rate <= 1.5`, `opacity <= 12%`, layer opacity `<= 16%`).
   - Solo resolution halo (`repeater_rings`) behind centered hero.
3. **Emotion-Driven Motion (`ecgc_compiler.py`):**
   - Entrances: `zoom_drift`, `rise_up`, `slide_down`, `mask_reveal`, `soft_fade`, `slide_left`, `slide_right`, `pop_settle`.
   - Purposeful mid-hold keyframes: `pos`, `scale_mult`, `opacity`, and subtle `rotation` tilt settle (`±1.5–2.2° -> 0°`).
4. **Supportive Live-Shifting Gradients & Single Top HUD:**
   - `bg_opacity = 64%` over `#060A12`, zero grids, zero floor lines, `live_color_cycle = True`, auto-dimmed caustics on light beats (`sandstone_dawn`, `clean_ivory`).
   - Single persistent top neon-glass live-typing HUD (`hud_sequence` or spoken-synced `neon_live_typing` blocks on 9:16 Reels — **zero text before spoken timestamp**, **zero `[...]` production notes**).
5. **GPU-Killer Ban (Keep 720p Renders at `~45–60s`):**
   - **NEVER** use `ec.generate.cclightrays` (`>420s` CPU raymarch timeout) or `Gaussian Blur >= 80px` on full-frame layers (`325s`).
   - Keep `glow <= 0.90` (avoid white blowout) and `particles` ultra-subtle (`opacity <= 12%`).
