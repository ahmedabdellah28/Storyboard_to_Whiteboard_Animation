# AION CLI — Existing System Capability Audit (`CLI_CAPABILITY_AUDIT.md`)

**Audit Date:** 2026-11-17  
**Inspected Entrypoint:** `e:\image_to_animate\pipeline_cli.py` (1,311 lines)  
**Golden Reference Protected:** `projects/mind_glitches_ar` (2,157 files, 97 dirs, 1.32 GB — checksum baseline captured at `tests/aion_cli/baselines/mind_glitches_ar.golden.json`)  

---

## 1. Existing CLI Structure & Entrypoint Discovery

### Primary CLI Entrypoint
- **Path:** `pipeline_cli.py`
- **Invocation:** `python pipeline_cli.py [--project <name>] <subcommand> [options]`
- **Active Project Persistence:** `.active_project` (currently `mind_glitches_ar`)
- **Project Isolation Root:** `projects/<project_name>/` (`project.json`, `inputs/`, `sections/`, `exports/`, `export/`)

### Extracted Subcommands & Options (Pre-Upgrade)

| Subcommand | Aliases | Options | Handler Function | Underlying Modules Called |
| :--- | :--- | :--- | :--- | :--- |
| `init` | `new` | `name`, `--sections`, `--desc`, `--lang {ar,en}`, `--dialect`, `--voice` | `cmd_init` | `slugify_project_name`, `.active_project`, writes `project.json` + templates |
| `use` | `switch` | `name` | `cmd_use` | `get_project_dirs`, `set_active_project_name`, `cmd_paths` |
| `projects` | `list` | _(none)_ | `cmd_list_projects` | Reads `projects/*/project.json` & `.active_project` |
| `paths` | `info` | `--project` | `cmd_paths` | `get_project_dirs` |
| `voice` | _(none)_ | `--section` (required), `--project` | `cmd_voice` | `voice_studio.engine.VoiceStudioEngine` |
| `timing` | _(none)_ | `--section` (required), `--project` | `cmd_timing` | `section_timing.transcription.faster_whisper_engine`, `whisper_parser`, `script_audio_aligner` |
| `extract` | _(none)_ | `--section` (required), `--project` | `cmd_extract` | Optional `<sec_dir>/extract_assets.py` or `core_engine.universal_craft_extractor.UniversalCraftExtractor` |
| `render` | _(none)_ | `--section` (required), `--engine {python,effectcraft}`, `--project` | `cmd_render` | `core_engine.effectcraft_director`, `core_engine.media_compositor` OR `core_engine.universal_staged_director_v2` |
| `effects` | _(none)_ | `--list`, `--demo`, `--all` | Inline in `main()` | `core_engine.effectcraft_motion_studio.EffectCraftMotionStudio` |
| `status` | _(none)_ | `--project` | `cmd_status` | Scans `sections/section_XX/` & legacy `exports/section_XX_master_v7.mp4` |
| `merge` | _(none)_ | `--project` | `cmd_merge` | Subprocess `ffmpeg concat` over `section_*_master_v7.mp4` |
| `enhance` | _(none)_ | `--section`, `--all`, `--project` | `cmd_enhance` | `core_engine.media_compositor.enhance_section` |
| `auto` | `loop`, `run-all` | `--project`, `--start`, `--end`, `--engine`, `--skip-voice`, `--skip-timing`, `--skip-extract`, `--skip-render`, `--skip-merge`, `--force` | `cmd_auto` | Calls `cmd_voice`, `cmd_timing`, `cmd_extract`, `synthesize_default_grounded_manifest`, `core_engine.director_qa_auditor`, `cmd_render`, `cmd_merge` |

### Related Non-Centralized / Orphaned Entrypoints Found in Repo
- `core/orchestration/orchestrator.py` (`ProductionOrchestrator`, `TaskDAGExecutor`, `StateStore`, `ArtifactStore`) — tested cleanly (`44 passed`), primarily imported by `studio_ui/*` and `production_engine/universal_section_pipeline.py`, **not yet wired into `pipeline_cli.py`**.
- `projects/mind_glitches_ar/` (`build_aion_section.py`, `build_all_sections.py`, `extract_all_storyboards.py`, `run_voice_and_timing.py`, `adapters/*`) — contains the **proven AION v2.0 `scene_graph.json` pipeline** that produced the golden documentary, isolated inside `mind_glitches_ar`.
- `scripts/generate_viral_en_voice_timing.py` & `scripts/extract_project_storyboards.py` — standalone scripts duplicating voice/timing/extraction patterns outside `pipeline_cli.py`.

---

## 2. Path, Configuration, State & Error-Handling Inspection

1. **Filesystem Side Effects on Read Operations:** `get_project_dirs()` unconditionally invokes `.mkdir(parents=True, exist_ok=True)` on `exports/`, `export/`, `inputs/`, and `input/` — even when called by read-only `status` or `paths`. `get_section_paths()` similarly creates `voice/`, `timing/`, and `assets/` on read-only checks.
2. **Script Parsing & Template Leak:** `get_section_text()` splits `master_script.txt` only by `SECTION 01` regex (fails on `[SECTION 01: ...]` bracket headers used by newer projects) and returns `cmd_init` placeholder text (`[اكتب هنا نص السكربت الصوتي ...]`) as valid narration text instead of rejecting unedited stubs.
3. **Silent Error Exit Codes:** `main()` discards `False` return values from `cmd_voice`, `cmd_timing`, `cmd_extract`, `cmd_render`, `cmd_merge`, exiting with `0` even on failure. (Note: `cmd_use` / missing inputs print errors cleanly; legacy compatibility must be preserved cleanly while offering strict/stage validation.)
4. **`effects --list` Hard Crash:** `core_engine/effectcraft_motion_studio.py:39` hardcodes `ROOT_DIR / "effectcraft" / "target" / "release" / "effectcraft-cli.exe"`, missing the actual binary at `craftApp/effectcraft/target/release/effectcraft-cli.exe` (`FileNotFoundError`, exit `1`).
5. **Run Output Overwriting & Resume Gaps:**
   - `cmd_render` and `cmd_merge` write fixed filenames (`section_XX_master_v7.mp4`, `<project>_full_movie_master.mp4`) directly into `exports/`, overwriting prior runs.
   - `cmd_auto` uses naive file-existence checks (`if paths["audio_wav"].exists()`) without reading `core/state/state_store.py`, hash invalidation (`core/artifacts/cache_validator.py`), checkpoint recovery (`core/validation/recovery.py`), or partial-stage resume (`--from-stage` / `--resume`).

---

## 3. Capability Classification Matrix

| Capability / Stage | Current Module(s) | Classification | Notes & Action Plan |
| :--- | :--- | :--- | :--- |
| Multi-project scaffolding (`init`, `use`, `projects`) | `pipeline_cli.py` | `EXISTING_WORKING` | Keep exact flags/behavior; clean up `get_project_dirs(create=...)` side effect for read commands. |
| Project status & paths (`paths`, `status`) | `pipeline_cli.py` | `EXISTING_NEEDS_EXTENSION` | Keep existing 7-column compatibility table; extend status to display AION stages (`Brief`, `Direct`, `QA`, active `run_id`, resume checkpoint) cleanly. |
| **Stage 1: Script** ingestion, split & validation | `pipeline_cli.py:get_section_text`, `cmd_init` | `EXISTING_NEEDS_FIX` | Fix `[SECTION XX]` header regex & placeholder-stub detection; add explicit `script` command (`--split`, `--validate`). |
| **Stage 2: Voice** (`gemini-3.8-flash-tts`, key pool, chunk QA) | `pipeline_cli.py:cmd_voice`, `voice_studio/*`, `core/api/key_pool.py` | `EXISTING_NEEDS_EXTENSION` | Default model in `VoiceStudioEngine` is older `gemini-3.1-flash-tts-preview`; no automatic `Faster-Whisper` duplicate/truncation guard, no `-15 LUFS` mastering, no `--all` batch flag, no `APIKeyPool` daily-quota skip. Extend `cmd_voice` + reuse `APIKeyPool`. |
| **Stage 3: Timing** (`Faster-Whisper` word/sentence sync + SRT) | `pipeline_cli.py:cmd_timing`, `section_timing/*` | `EXISTING_WORKING` (Needs Minor Extension) | Reuse `FasterWhisperEngine` + `ScriptAudioAligner`; extend JSON output to always include `sentences`, `whisper_tail_sample`, `language`, `--all`, and `all_sections_timing_index.json`. |
| **Stage 4: Assets** (Storyboard extraction + PhotoCraft 3x HD) | `pipeline_cli.py:cmd_extract`, `core_engine/universal_craft_extractor.py`, `scripts/extract_project_storyboards.py` | `EXISTING_NEEDS_EXTENSION` | Consolidate valley-projection + flood-fill + PhotoCraft 3x HD + `<60px`/edge sliver stripper alongside `UniversalCraftExtractor` (`--mode grid|contour`, `--all`). |
| **Stage 5: Semantic Mapping** (`semantic_map.json`) | `core/narrative/narrative_director.py`, `core/contracts/narrative_map.py` | `EXISTING_NEEDS_EXTENSION` | Existing implementations are hardcoded to Guan Yu / `spotlight_effect`; add generic `semantic-map` stage mapping `metadata.json` entities + `timing_master.json` phrases. |
| **Stage 6: Creative Brief** (`creative_brief.json`) | `AION_CREATIVE_DIRECTOR_CONSTITUTION_AR_V2.md`, `projects/mind_glitches_ar/DIRECTING_PLAYBOOK_AR.md` | `MISSING` | Add structured `brief` stage producing/validating `director/section_XX/creative_brief.json` (palette, RTL/LTR, framing rules, `use_character`, pacing). |
| **Stage 7: AI Director** (`scene_graph.json`) | `pipeline_cli.py:synthesize_default_grounded_manifest` (legacy `manifest.json` only) | `EXISTING_NEEDS_EXTENSION` | Keep `manifest.json` compat; add `direct` stage synthesizing/validating AION `director/section_XX/scene_graph.json` with Glow/contrast guards & never clobbering human/AI-authored graphs without `--force`. |
| **Stage 8: Motion Graphics & Derivatives** (`exhibit_card`, `soft_bottom`, effects) | `core_engine/effectcraft_motion_studio.py`, `projects/mind_glitches_ar/adapters/image_tools_adapter.py` | `EXISTING_NEEDS_FIX` | Fix `CLI_PATH` in `effectcraft_motion_studio.py` (`effects --list`); centralize image derivative builders + `motion` stage into `core/aion/`. |
| **Stage 9: SFX & Ducking Mix** | `core_engine/sfx_director.py`, `projects/mind_glitches_ar/adapters/audio_tools_adapter.py` | `EXISTING_NEEDS_EXTENSION` | Promote RMS-ducking studio SFX mixer cleanly into shared `sfx` CLI stage (never truncating voiceover) while preserving `sfx_director` compat. |
| **Stage 10: EffectCraft Compiler** (`.ecproj` GPU pipeline) | `core_engine/effectcraft_director.py`, `projects/mind_glitches_ar/adapters/effectcraft_adapter.py` | `EXISTING_NEEDS_EXTENSION` | Promote verified `EffectCraftAdapter` into `core/aion/`, parameterizing `language` / `text_direction` (`rtl` Cairo & `ltr` Latin typography) and root paths. |
| **Stage 11: Render & Merge** (with Isolated Runs & Rollback) | `cmd_render`, `cmd_enhance`, `cmd_merge`, `core/validation/recovery.py` | `EXISTING_NEEDS_EXTENSION` | Support both AION (`scene_graph.json`) and legacy (`manifest.json`); isolate new run outputs in `exports/runs/<run_id>/`; add pre-run snapshots & rollback on failure. |
| **Stage 12: QA & Environment Doctor** | `core_engine/director_qa_auditor.py`, `core/validation/{environment_doctor,post_render_qa,preflight}.py` | `EXISTING_NEEDS_EXTENSION` | Modules exist & pass tests, but were NOT exposed via CLI. Wire `doctor` and `qa` (10-frame `qa_contact_sheet.png` + `PostRenderQAEngine` + Glow/contrast check) into `pipeline_cli.py`. |
| **Unified Resumable Runner** (`run` / `auto`) | `cmd_auto`, `core/state/state_store.py`, `core/artifacts/cache_validator.py` | `EXISTING_NEEDS_EXTENSION` | Connect `StateStore` + `CrashReconciliationEngine` + `--from-stage`/`--to-stage`/`--resume`/`--run-id` into `pipeline_cli.py`. |
| **Agent Documentation Suite** | `.agents/skills/*`, `.agents/rules/*` | `MISSING` | Create/sync `SKILL.md`, `AGENTS.md`, `CLI_REFERENCE.md`, `PIPELINE_CONTRACTS.md`, `TOOL_CAPABILITIES.md`. |
