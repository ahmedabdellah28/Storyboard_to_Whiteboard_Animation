# AION Pipeline Contracts (`PIPELINE_CONTRACTS.md`)

All project inputs, intermediate stage artifacts, isolated runs, and final deliverables live strictly inside `projects/<project_name>/`.

---

## Stage-by-Stage Artifact Contracts

| # | Stage | CLI Command | Required Inputs | Produced Outputs | Verification / Contract Rules |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 0 | Project Init | `init <name>` | CLI args (`--lang`, `--sections`, `--voice`) | `project.json`, scaffolded folders, `.active_project` | Isolated root; sets `language`, `text_direction`, `tts_voice`, `tts_profile`, `director_note` |
| 1 | `script` | `script` | `inputs/script/master_script.txt` or `sections/section_XX.txt` | `inputs/script/sections/section_XX.txt` | Supports `SECTION XX`, `[SECTION XX: ...]`, `## N.` headers; rejects unedited template stubs |
| 2 | `voice` | `voice` | Validated `section_XX.txt` + `project.json` | `sections/section_XX/voice/chunks_38/*.wav`, `sections/section_XX/voice/section_XX.wav` | 48kHz 16-bit mono PCM, `-15 LUFS`, Faster-Whisper duplicate/truncation guard, tail-spike trim |
| 3 | `timing` | `timing` | `section_XX.wav` + `section_XX.txt` | `sections/section_XX/timing/whisper.json`, `section_XX_timing_master.json`, `section_XX_word_by_word.srt`, optional `all_sections_timing_index.json` | Schema includes `duration`, `words_count`, `sentences[]`, `words[]`, `whisper_tail_sample` |
| 4 | `extract` | `extract` | `inputs/storyboards/section_XX.(png\|jpg\|webp)` | `sections/section_XX/assets/entity_01..20.png` (or `*_composite.png`), `metadata.json`, `contact_sheet.png` | Transparent exterior BG; `<60px` dots & neighbor edge slivers removed; 3x PhotoCraft HD |
| 5 | `semantic-map` | `semantic-map` | `assets/metadata.json` + `section_XX_timing_master.json` | `director/section_XX/semantic_map.json` (`aion.semantic_map.v1`) | Maps 100% assets to timing intervals + bottom-crop framing flags (`needs_framing`) |
| 6 | `brief` | `brief` | `project.json` + `semantic_map.json` | `director/section_XX/creative_brief.json` (`aion.creative_brief.v1`) | Palette moods, `text_direction` (`rtl`/`ltr`), font, `use_character: false`, Glow contrast rules |
| 7 | `direct` | `direct` | `semantic_map.json` + `creative_brief.json` + `timing_master.json` | `director/section_XX/scene_graph.json` (`aion.scene_graph.v2`) | Validated by `audit_scene_graph`: non-empty scenes, contrast-matched cards, solo centering keyframes |
| 8 | `motion` | `motion` | `director/section_XX/scene_graph.json` + `assets/*.png` | `exports/runs/<run_id>/work/section_XX/derived_assets/*.png`, `motion_plan.json` | Exhibit card (`warm`/`dark_crimson`/`arctic`) & soft-bottom alpha fade derivatives |
| 9 | `sfx` | `sfx` | `scene_graph.json` (`sfx_cues`) + `section_XX.wav` | `exports/runs/<run_id>/work/section_XX/section_XX_aion_mix.wav` | 44.1kHz stereo WAV; zero voice truncation; RMS envelope ducking around speech |
| 10-11 | `render` | `render --pipeline aion` | `scene_graph.json` + derived assets + `section_XX_aion_mix.wav` | `exports/runs/<run_id>/sections/section_XX/section_XX_aion_editable.ecproj`, `section_XX_aion_master.mp4` | 1920x1080 @ 30fps H.264 + AAC; isolated per-run folder; rollback on failure |
| 12 | `qa` | `qa` | Rendered `.mp4` + `section_XX_aion_mix.wav` + `scene_graph.json` | `exports/runs/<run_id>/qa/section_XX/qa_report.json`, `qa_contact_sheet.png`, `qa_00..09_*.png` | Checks 1080p aspect, black frames, A/V drift `<0.35s`, audio clipping, 10-frame visual sheet |
| 13 | `merge` | `merge --pipeline aion` | All rendered `section_*_aion_master.mp4` in run folder | `exports/runs/<run_id>/<project>_<run_id>_master_1080p.mp4`, `concat_list.txt` | Full sequential documentary master; preserves prior runs untouched |

---

## Run State & Checkpoint Contracts
- **Per-Run Ledger:** `projects/<project>/exports/runs/<run_id>/run_manifest.json`
- **Latest Run Pointer:** `projects/<project>/exports/runs/latest_run.json`
- **Core Lifecycle StateStore:** `projects/<project>/state/<project>_state.json`
- **Legacy Compatibility Mode:** When `director/section_XX/scene_graph.json` is absent or `--pipeline legacy` is passed, `manifest.json -> section_XX_master_v7.mp4` remains intact.
- **Creative Studio V5 Mode (`aion.scene_graph.v2`):**
  - Compiled via 10-stage ECGC (`core/aion/ecgc_compiler.py`) through `studio compile` / `studio preview` or `render` when V2 schema is detected.
  - Required top-level V2 keys: `narrative_intent`, `asset_references`, `visual_metaphor`, `composition`, `procedural_graphics`, `motion_paths`, `camera`, `lighting`, `vfx`, `typography`, `sfx`, `timing_anchors`, `tool_requirements`, `fallbacks`, `quality_constraints`.
  - Outputs isolated under `projects/<project>/exports/runs/<run_id>/sections/section_XX/` (`scene_graph.v2.json`, `section_XX_studio.ecproj`, `section_XX_studio.mp4`, `work/compile_report.json`, `qa/creative_quality_report.json`, `qa/creative_contact_sheet.png`).
  - Golden reference `projects/mind_glitches_ar` is write-protected by `studio_cli` (`PermissionError` on compile/preview; read-only QA writes under `cache/qa_readonly/`).
