"""Tests for Phase 3, 4, 5: Orchestration, Resource Pools, and Unified Providers."""

import os
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.orchestration.resource_pools import ResourcePoolManager
from core.orchestration.task_dag import ExecutableTask, TaskDAGExecutor
from core.orchestration.orchestrator import ProductionOrchestrator
from core.providers.tts.base import BaseTTSProvider
from core.providers.tts.gemini_tts import UnifiedGeminiTTS
from core.providers.tts.profiles import AUDIO_PROFILES
from core.providers.translation.gemini_translation import UnifiedGeminiTranslator
from core.artifacts.artifact_store import ArtifactStore
from core.state.state_store import StateStore


def test_resource_pool_manager():
    mgr = ResourcePoolManager(network_api_slots=2, gpu_render_slots=1)

    # Acquire and release
    with mgr.acquire("NETWORK_API") as slot1:
        assert slot1 is True
        # Second acquire in same thread or separate
        with mgr.acquire("NETWORK_API") as slot2:
            assert slot2 is True


def test_task_dag_executor_with_caching():
    with tempfile.TemporaryDirectory() as td:
        art_store = ArtifactStore(store_dir=Path(td) / "artifacts")
        state_store = StateStore(base_dir=Path(td) / "state")

        executor = TaskDAGExecutor(
            project_id="test_proj",
            section_id="sec_01",
            artifact_store=art_store,
            state_store=state_store,
        )

        dummy_out = Path(td) / "output.txt"
        call_count = {"count": 0}

        def action():
            call_count["count"] += 1
            dummy_out.write_text("done", encoding="utf-8")
            return str(dummy_out)

        task = ExecutableTask(
            task_id="t1",
            name="Dummy Task",
            component="test",
            action=action,
            expected_output_path=str(dummy_out),
            inputs={"val": 1},
        )
        executor.add_task(task)

        # First run: executes
        res1 = executor.execute()
        assert call_count["count"] == 1
        assert dummy_out.exists()

        # Second run: should be cached and NOT call action() again!
        res2 = executor.execute()
        assert call_count["count"] == 1


def test_orchestrator_discovery_and_resolution():
    orch = ProductionOrchestrator(project_id="wealth_classes_documentary")
    sections = orch.discover_sections()
    assert len(sections) > 0

    p3 = orch.resolve_section_path("03_working_poor")
    assert p3.is_dir()
    assert "03_working_poor" in p3.name

    p3_short = orch.resolve_section_path("03")
    assert p3_short.is_dir()
    assert "03_working_poor" in p3_short.name


def test_tts_profiles_available():
    assert "SAUDI_YOUTH_CREATOR" in AUDIO_PROFILES
    profile = AUDIO_PROFILES["SAUDI_YOUTH_CREATOR"]
    assert "Saudi" in profile.name or "Saudi" in profile.description


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tests = [
        test_resource_pool_manager,
        test_task_dag_executor_with_caching,
        test_orchestrator_discovery_and_resolution,
        test_tts_profiles_available,
    ]
    print(f"Running {len(tests)} Orchestration & Providers tests...")
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nResult: {passed}/{len(tests)} tests passed.")
    if passed == len(tests):
        print("ALL ORCHESTRATION & PROVIDERS TESTS PASSED SUCCESSFULLY!")
    else:
        sys.exit(1)
