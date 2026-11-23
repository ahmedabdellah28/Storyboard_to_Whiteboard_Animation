---
name: aion-pre-render-montage-guard
description: >-
  Mandatory pre-render thinking protocol and error-prevention checklist for AION Studio V8 (Master Cinema + Adaptive Director v4).
  Activate BEFORE generating TTS voiceover, authoring scene_graph.v2.json, or running studio compile / studio merge / EffectCraft GPU rendering.
---

# AION Pre-Render Thinking & Montage Guard (بروتوكول التفكير ومنع الأخطاء قبل الرندر)

Follow this checklist **before** running any TTS synthesis, scene-graph generation, or GPU render inside `e:\image_to_animate`.

---

## Gate 0: Mandatory Pre-Render Protocol (إلزامي قبل كتابة أي `scene_graph` أو تشغيل `render`)

1. **Zero Pre-Render Image Reads:** Never open raw storyboard PNGs (`inputs/storyboards/*.png`) or extracted entity PNGs (`entity_*.png`) during planning or directing. Read strictly JSON metadata (`inputs/storyboard_catalog/*.json`, `sections/section_XX/timing/section_XX_timing_master.json`, `semantic_manifest.json`, or `studio shorts --action inspect`).
2. **Query Real Resources First (`<1.5ms` SQLite FTS5):** Use `python pipeline_cli.py studio resources --query "<intent>" [--kind icon|sfx|effect|background|font|asset]` (`2,838` verified resources, `p50=0.53ms`, `p95=1.46ms`). Never invent effect, icon, or SFX names.
3. **100% Asset Coverage & Spoken Sync:** Account for all extracted assets in chronological order aligned to Faster-Whisper timestamps. For live-typing HUDs (especially 9:16 Reels), never display a phrase before its spoken timestamp in `timing_master.json`.
4. **Canary 1-Section Render First (`720p` Default):** Always compile `--section 01` first at default **`720p`** (`--resolution 1080p` only when explicitly requested), inspect `qa/creative_contact_sheet.png` visually + `qa/creative_quality_report.json`, then compile `--all`.

---

## Gate 1: Critical Pipeline, Dialect & Rendering Guardrails

### 1. Default V8 Routing (`720p` + `Master Edu` + `Director v4` ON by Default)
- `studio compile` and `studio preview` automatically default to:
  - **`--resolution 720p`** (`1280×720` / `720×1280`)
  - **`--format educational`** (`Master Edu`)
  - **`--director-v4` ON** (builds & validates `asset_manifest.v2.json`, `cinematic_plan.v2.json`, `motion_plan.v3.json`, collision-free `chrono_items` choreography, dynamic icon placement, diverse inter-element connectors, emotion-driven motion & VFX, whisper-soft particles `opacity <= 12%`, real Pillow WCAG contrast metrics). Pass `--no-director-v4` only to opt out.
- **Custom `scene_graph.v2.json`:** Loaded directly when `canvas.aspect_ratio == aspect` and it contains V7 `cinema_stage`/`hud_sequence` (or when `--format legacy` is passed with `story_genre == "auto"`, `style_mode == "auto"`).
- **Never** pass explicit non-`auto` `--style-mode` (e.g. `cinematic_2_5d`) when you want a full multi-asset documentary montage.
- **Zero Editorial Notes on Screen:** Bracketed directives (`[آية قرآنية صامتة: ...]`, `[excited]`, `[pause]`) are auto-scrubbed from HUD/typography and must NEVER render on screen. Keep `quran_cards` verbatim with zero SFX during silent verse windows.

### 2. GPU-Speed & Visual Restraint Guardrails
- **GPU-Killer Ban:** **NEVER** apply `ec.generate.cclightrays` (`>420s` CPU timeout) or `Gaussian Blur >= 80px` on full-frame `>1500px` shapes (`325s`).
- **Whisper-Soft Particles:** Keep ambient `particles` subtle (`birth_rate <= 1.5`, `opacity <= 12%`, layer opacity `<= 16%`) so they never clutter foreground artwork.
- **Zero Same-Slot Overlaps:** Always sort scene assets chronologically before setting exit times (`prev_out <= next_in - 0.04s`) and preserve column parity so two active assets never stack on top of each other.
- **SFX Gain-Staging:** Pre-ducking CC0 SFX (`380` verified files) calibrated at `-1.8` to `-3.5 dB` via `resolve_pro_sfx` alongside `-14 LUFS` voiceover and `-12 dB` RMS ducking (Zero-BGM policy).

### 3. Gemini TTS Multi-Dialect Tracks & Word-Match QA
- Default model: **`gemini-3.1-flash-tts-preview`** (fallback `gemini-2.5-flash-preview-tts`; never send English instructions to `gemini-3.8-flash-tts`).
- **Isolated Dialect Tracks (Zero Cross-Leak + Separate Cache Hash):**
  - **Saudi White Arabic (`ar` default):** `--dialect saudi_white` (`Fenrir` / `SAUDI_YOUTH_CREATOR` / `HIGH_ENERGY_YOUTUBE` / `cta_channel_ar_fenrir.wav`).
  - **Egyptian Cairo Arabic (`ar`):** `--dialect egyptian` (Male `Fenrir` or energetic comedic `Puck` / `EGYPTIAN_YOUTH_CREATOR`) or `--dialect egyptian_female` (Female `Kore` / `EGYPTIAN_FEMALE_CREATOR`) + `HIGH_ENERGY_EGYPTIAN_YT` + `cta_channel_ar_eg_*.wav`. Overridable per run via `voice --dialect egyptian [--voice Puck|Kore]`.
  - **US Casual English (`en`):** `--lang en --dialect us_casual` (`Puck` / `US_CASUAL_STORYTELLER` / `cta_channel_en_puck.wav`).
- **Short-Line Coalescing:** [`split_section_paragraphs`](file:///e:/image_to_animate/core/aion/voice_stage.py#L202-L249) automatically merges consecutive short punchy lines into natural chunks (preventing 429 quota spikes and 2–3 word Whisper QA false rejects).
- **Never** feed placeholder text (`[اكتب هنا نص السكربت الصوتي ...]`) to TTS, and never truncate narration.

### 4. Arabic/English Live Typing (`neon_live_typing`) & Contrast Pitfalls
- EffectCraft `prop.addKey` on `text/sourceText` preserves 100% native `HarfBuzz` Arabic cursive shaping while animating letter-by-letter with dynamic cursor tracking (`_measure_text_width_px`).
- Verify `with_backdrop: True`, bright ink (`#F8FAFC`) over dark frosted glass, and `neon_intensity <= 0.90` (`glow < 1.0` over bright cards).

---

## Gate 2: Standard Execution Order (التسلسل المعتمد للإنتاج)

1. `python pipeline_cli.py status --detailed --project <name>`
2. `script --all` -> `voice --all` -> `timing --all`
3. `extract --all --from-zip "<zip>"` -> `semantic-map --all`
4. Optional resource lookup: `python pipeline_cli.py studio resources --project <name> --section 01 --query "<intent>"`
5. Canary compile (`720p` + `Master Edu` + `Director v4` default): `python pipeline_cli.py studio compile --project <name> --section 01 --run-id <run_id>` -> inspect `qa/creative_contact_sheet.png` + `qa/creative_quality_report.json`.
6. Check free space on `E:` (`> 2 GB`) -> `studio compile --all --run-id <run_id>` -> `studio merge --run-id <run_id>`.

---

## Gate 3: Post-Render Visual QA, Protection & Regression Checks

- **Never trust numeric `PASS` alone:** Open `qa/creative_contact_sheet.png` visually to verify zero same-slot overlaps, clean icon placement, readable Arabic shaping, subtle particles, and clean Quran cards.
- **Golden Reference Immutability:** Never modify any file inside `projects/mind_glitches_ar/` or leave `.active_project` pointing to a temporary test project.
- **After Any Pipeline/Code Edit:** Regenerate `CLI_REFERENCE.md` (`python pipeline_cli.py cli-spec --write-docs`) if CLI flags changed, and run `python -m pytest tests/aion_cli/ -v`.
