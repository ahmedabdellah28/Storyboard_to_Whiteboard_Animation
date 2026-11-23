# Creative Stickman Studio V3 — Baseline Report (M0)

- **Timestamp:** 2026-11-15T19:08:15+02:00
- **Original Branch:** `main`
- **Base Commit:** `b20a094` (`feat: production architecture update with standalone AI audio dubbing engine, dynamic section engine, and quality gates`)
- **Backup Tag:** `backup/pre-creative-v3` -> `b20a094`
- **Working Branch:** `feature/creative-stickman-v3`
- **Existing Tags:** `v0.8.0-beta`, `backup/pre-creative-v3`
- **Dirty Working Tree:** Pre-existing modified/deleted/untracked files on `main` were preserved untouched when branching to `feature/creative-stickman-v3`.

## Environment & Tool Versions
- **OS:** Windows
- **Python:** `3.13.13`
- **Git:** `2.44.0.windows.1`
- **FFmpeg:** `9.0.1-essentials_build-www.gyan.dev`
- **Node.js / npm:** Not installed in system `PATH`
- **Key Python Packages:**
  - `playwright 1.49.1`
  - `PySide6 6.11.2`, `PyQt6 6.11.0`
  - `fastapi 0.162.2`, `uvicorn 0.54.0`
  - `opencv-python 5.0.0.93`, `pillow 10.4.0`, `numpy 2.4.4`, `scipy 1.17.1`, `lxml 6.0.4`
  - `pytest 9.1.1`

## Legacy Protected Paths (Untouched)
- `core/orchestration/orchestrator.py`
- `production_engine/`
- `core/contracts/`
- `studio_ui/` legacy screens and entrypoints

## Baseline Test Suite Result
- **Core + TCM-DS + Voice Studio Smoke (`python -m pytest tests/test_core_foundation.py tests/test_tcm_ds_contracts.py tests/test_vyond_story.py -q`):**
  - **Outcome:** **PASS** (`21 passed in 6.77s`)
- **Core, State, Orchestration, DAG & Phase 1–4 Baseline (`python -m pytest tests/test_core_foundation.py tests/test_core_orchestration_and_providers.py tests/test_core_state_and_artifacts.py tests/test_tcm_ds_contracts.py tests/test_vyond_story.py tests/test_production_dag_execution.py tests/test_phase1_contracts_and_state.py tests/test_phase2_invalidation_and_revisions.py tests/test_phase3_validation_and_recovery.py tests/test_phase4_governance_and_cancellation.py -v`):**
  - **Outcome:** `82 passed, 2 failed in 26.32s`
  - **Pre-existing failures on `main` (unrelated to V3):**
    1. `tests/test_production_dag_execution.py::test_real_section_dag_construction` (`audio_mix.dependencies` on `main` includes `pre_render_director`)
    2. `tests/test_production_dag_execution.py::test_canary_section_03_dag_run` (`sections/03_working_poor` script file missing in pre-existing working tree)
  - Note: Full `python -m pytest -q` (including UI/Qt/render tests) was cancelled after >8m without completion; targeted non-GUI regression suites above form the reproducible automated baseline.
