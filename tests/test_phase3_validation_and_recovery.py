"""Unit and integration test suite for Phase 3: Validation System & Recovery System.

Verifies:
1. InputPreflightValidator section and project level validation.
2. StagePreflightValidator dynamic prerequisite checking for canonical stages.
3. EnvironmentDoctor system diagnostics, FFmpeg probe, and encoder detection.
4. CrashReconciliationEngine self-healing of interrupted tasks and orphan cleanup.
5. Rolling backup (.bak) restoration upon corrupted primary state.
6. CircuitBreaker failure threshold, cooldown, and recovery state machine.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
import pytest

from core.contracts.studio_contracts import SectionInputContract, StageIdentifier
from core.state.project_state import ProjectState, SectionState, TaskState
from core.state.transitions import (
    ProjectLifecycleStatus,
    SectionLifecycleStatus,
    TaskLifecycleStatus,
)
from core.validation.environment_doctor import EnvironmentDoctor, SystemDiagnosticReport
from core.validation.preflight import (
    InputPreflightValidator,
    StagePreflightValidator,
    ValidationResult,
)
from core.validation.recovery import (
    CircuitBreaker,
    CircuitBreakerState,
    CrashReconciliationEngine,
    ReconciliationReport,
)


# ============================================================================
# 1. INPUT PREFLIGHT VALIDATION
# ============================================================================

def test_input_preflight_valid_inputs():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        tf.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 2048)
        sb_path = tf.name

    try:
        contract = SectionInputContract(
            section_id="sec_01",
            storyboard_path=sb_path,
            script_text="Hello world, this is a valid narration script.",
        )
        res = InputPreflightValidator.validate_section_input(contract)
        assert res.is_valid is True
        assert len(res.errors) == 0
        assert res.details.get("script_word_count") == 8
        assert res.details.get("storyboard_size_bytes") > 2000
    finally:
        Path(sb_path).unlink(missing_ok=True)


def test_input_preflight_duplicate_sequence_index():
    proj = ProjectState(project_id="proj_dup")
    proj.get_or_create_section("sec_01", sequence_index=0)
    proj.get_or_create_section("sec_02", sequence_index=0)  # Duplicate!

    res = InputPreflightValidator.validate_project_structure(proj)
    assert res.is_valid is True  # Warning, not hard failure
    assert any("Duplicate sequence_index 0" in w for w in res.warnings)


# ============================================================================
# 2. STAGE PREFLIGHT PREREQUISITE VALIDATION
# ============================================================================

def test_stage_preflight_whisper_requires_voice():
    with tempfile.TemporaryDirectory() as td:
        s_dir = Path(td)
        # Voice does not exist
        res = StagePreflightValidator.validate_stage_prerequisites(
            StageIdentifier.WHISPER,
            section_dir=s_dir,
            inputs={"voice": str(s_dir / "missing_voice.wav")},
        )
        assert res.is_valid is False
        assert any("requires synthesized voice WAV" in e for e in res.errors)

        # Create voice file -> should pass
        v_file = s_dir / "missing_voice.wav"
        v_file.write_bytes(b"RIFF" + b"\x00" * 100)
        res_ok = StagePreflightValidator.validate_stage_prerequisites(
            StageIdentifier.WHISPER,
            section_dir=s_dir,
            inputs={"voice": str(v_file)},
        )
        assert res_ok.is_valid is True


def test_stage_preflight_mux_requires_video_and_audio():
    with tempfile.TemporaryDirectory() as td:
        s_dir = Path(td)
        v_file = s_dir / "silent_visual_1080p.mp4"
        a_file = s_dir / "master_audio.wav"

        # Neither exists
        res = StagePreflightValidator.validate_stage_prerequisites(
            StageIdentifier.MUX,
            section_dir=s_dir,
            inputs={"video": str(v_file), "audio": str(a_file)},
        )
        assert res.is_valid is False

        # Create both files
        v_file.write_bytes(b"\x00" * 500)
        a_file.write_bytes(b"\x00" * 500)
        res_ok = StagePreflightValidator.validate_stage_prerequisites(
            StageIdentifier.MUX,
            section_dir=s_dir,
            inputs={"video": str(v_file), "audio": str(a_file)},
        )
        assert res_ok.is_valid is True


# ============================================================================
# 3. ENVIRONMENT DOCTOR
# ============================================================================

def test_environment_doctor_ffmpeg_and_hardware_encoders():
    ff_info = EnvironmentDoctor.check_ffmpeg()
    assert "available" in ff_info
    assert "version" in ff_info

    enc_info = EnvironmentDoctor.probe_hardware_encoders()
    assert "primary_encoder" in enc_info
    assert len(enc_info["available_encoders"]) >= 1
    assert "libx264" in enc_info["available_encoders"]

    free_gb = EnvironmentDoctor.check_storage_space()
    assert free_gb >= 0.0

    report = EnvironmentDoctor.run_full_diagnosis()
    assert isinstance(report, SystemDiagnosticReport)
    assert report.python_version.startswith("3.")


# ============================================================================
# 4. CRASH RECONCILIATION ENGINE
# ============================================================================

def test_crash_reconciliation_heals_completed_artifact():
    with tempfile.TemporaryDirectory() as td:
        proj_dir = Path(td)
        sec_dir = proj_dir / "sections" / "sec_01"
        sec_dir.mkdir(parents=True, exist_ok=True)

        # Create physical output artifact for Whisper
        whisper_output = sec_dir / "whisper_words.json"
        whisper_output.write_text('{"words": []}', encoding="utf-8")

        # Create project state where task was left in RUNNING
        proj = ProjectState(project_id="p_crash")
        sec = proj.get_or_create_section("sec_01")
        task_whisper = sec.get_or_create_task("sec.whisper")
        task_whisper.status = TaskLifecycleStatus.RUNNING
        task_render = sec.get_or_create_task("sec.render")
        task_render.status = TaskLifecycleStatus.RUNNING  # Output missing

        # Run reconciliation
        rep = CrashReconciliationEngine.reconcile_on_startup(proj, base_project_dir=proj_dir)

        assert rep.reconciled_tasks_count == 2
        # Whisper had output -> healed to COMPLETED
        assert "sec_01:sec.whisper" in rep.healed_to_completed
        assert task_whisper.status == TaskLifecycleStatus.COMPLETED

        # Render output was missing -> marked FAILED
        assert "sec_01:sec.render" in rep.marked_as_failed
        assert task_render.status == TaskLifecycleStatus.FAILED
        assert "abnormal application shutdown" in task_render.error


def test_crash_reconciliation_backup_recovery():
    with tempfile.TemporaryDirectory() as td:
        proj_file = Path(td) / "project_corrupt.json"
        bak_file = Path(td) / "project_corrupt.json.bak"

        # Corrupt primary file
        proj_file.write_text("{CORRUPT JSON NOT VALID}", encoding="utf-8")

        # Valid backup file
        valid_state = ProjectState(project_id="recovered_proj", title="Recovered Project")
        bak_file.write_text(json.dumps(valid_state.to_dict()), encoding="utf-8")

        recovered = CrashReconciliationEngine.recover_from_backup(proj_file)
        assert recovered is not None
        assert recovered.project_id == "recovered_proj"
        assert recovered.title == "Recovered Project"


def test_orphan_temp_files_cleanup():
    with tempfile.TemporaryDirectory() as td:
        p_dir = Path(td)
        old_tmp = p_dir / "render.tmp"
        old_tmp.write_bytes(b"\x00" * 100)

        # Artificially set modification time to 2 hours ago
        past_time = time.time() - 7200
        os.utime(old_tmp, (past_time, past_time))

        new_tmp = p_dir / "active.tmp"
        new_tmp.write_bytes(b"\x00" * 100)

        cleaned = CrashReconciliationEngine.cleanup_orphan_temp_files(p_dir, max_age_seconds=3600)
        assert cleaned == 1
        assert not old_tmp.exists()
        assert new_tmp.exists()


# ============================================================================
# 5. CIRCUIT BREAKER
# ============================================================================

def test_circuit_breaker_lifecycle():
    cb = CircuitBreaker(name="tts_circuit", failure_threshold=2, cooldown_seconds=0.2)
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True

    # 1st failure
    cb.record_failure()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True

    # 2nd failure -> Trips circuit to OPEN
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.can_execute() is False
    assert cb.get_remaining_cooldown() > 0.0

    # Wait for cooldown
    time.sleep(0.25)
    assert cb.can_execute() is True
    assert cb.state == CircuitBreakerState.HALF_OPEN

    # Success resets circuit
    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 0
