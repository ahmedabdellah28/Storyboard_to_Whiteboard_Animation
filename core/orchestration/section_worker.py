"""Self-contained section production worker unit driven by Core DAG and Resource Gating."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.artifacts.artifact_store import ArtifactStore, get_artifact_store
from core.config.settings import PROJECT_ROOT, SECTIONS_DIR
from core.orchestration.resource_pools import ResourcePoolManager, get_resource_manager
from core.orchestration.task_dag import ExecutableTask, TaskDAGExecutor
from core.state.project_state import ProjectState
from core.state.state_store import StateStore, get_state_store
from core.state.transitions import LifecycleStatus
from core.state.workflow_events import (
    PipelineLogEvent,
    WorkflowEventBus,
    get_workflow_event_bus,
)
from production_engine.universal_section_pipeline import UniversalSectionPipeline


class SectionWorker:
    """Manages full lifecycle execution for an individual section through the Core DAG."""

    def __init__(
        self,
        section_path: str | Path,
        project_id: str = "wealth_classes_documentary",
        title: Optional[str] = None,
        state_store: Optional[StateStore] = None,
        resource_manager: Optional[ResourcePoolManager] = None,
        artifact_store: Optional[ArtifactStore] = None,
        cancel_token: Optional[Any] = None,
        event_bus: Optional[WorkflowEventBus] = None,
    ) -> None:
        self.section_path = Path(section_path).resolve()
        self.section_id = self.section_path.name
        self.project_id = project_id
        self.title = title
        self.state_store = state_store or get_state_store()
        self.resource_manager = resource_manager or get_resource_manager()
        self.artifact_store = artifact_store or get_artifact_store()
        self.cancel_token = cancel_token
        self.event_bus = event_bus or get_workflow_event_bus()

    def validate_inputs(self) -> Dict[str, bool]:
        """Check availability of primary section input assets."""
        script_file = self.section_path / "script.txt"
        storyboard_file = self.section_path / "storyboard.png"
        voice_file = self.section_path / "voice" / "section.wav"
        if not voice_file.exists():
            voice_file = self.section_path / "voiceover.wav"

        return {
            "script": script_file.is_file(),
            "storyboard": storyboard_file.is_file(),
            "voice": voice_file.is_file(),
        }

    def build_section_dag(
        self,
        pipeline: UniversalSectionPipeline,
        force_whisper: bool = False,
        custom_manifest: Optional[List[Any]] = None,
        force_tts: bool = False,
        tts_provider: Optional[Any] = None,
    ) -> TaskDAGExecutor:
        """Constructs the explicit DAG for all section production stages."""
        executor = TaskDAGExecutor(
            project_id=self.project_id,
            section_id=self.section_id,
            resource_manager=self.resource_manager,
            artifact_store=self.artifact_store,
            state_store=self.state_store,
            cancel_token=self.cancel_token,
            event_bus=self.event_bus,
        )

        sec_id = self.section_id
        voice_target = (
            pipeline.voice_path
            if (pipeline.voice_path and Path(pipeline.voice_path).exists())
            else str(self.section_path / "voice" / "section.wav")
        )
        meta_file = str(Path(pipeline.assets_dir) / "metadata.json")
        layout_file = str(self.section_path / "placed_elements_layout.json")
        final_plan_file = str(self.section_path / "timing" / "final_render_plan.json")
        master_audio_file = str(self.section_path / "master_audio.wav")
        final_video_file = str(self.section_path / "final_whiteboard_1080p.mp4")
        deliv_dir = PROJECT_ROOT / "output_animations" / self.project_id / "deliverables" / "sections"
        deliv_video_file = str(deliv_dir / f"{self.section_id}_Whiteboard_1080p.mp4")

        # 0. Text-to-Speech Synthesis (Audio Branch Root)
        executor.add_task(
            ExecutableTask(
                task_id=f"{sec_id}.tts",
                name=f"TTS Audio Generation ({sec_id})",
                component="tts",
                resource_type="NETWORK_API",
                action=lambda: pipeline.step_tts(force=force_tts, provider=tts_provider),
                expected_output_path=voice_target,
                inputs={"script": str(pipeline.script_path)},
                config={"force": force_tts},
                dependencies=set(),
                section_id=sec_id,
            )
        )

        # 1. Whisper Word-Level Timing (Depends on TTS!)
        executor.add_task(
            ExecutableTask(
                task_id=f"{sec_id}.whisper",
                name=f"Whisper Timing ({sec_id})",
                component="whisper",
                resource_type="CPU_HEAVY",
                action=lambda: pipeline.step_whisper(force=force_whisper),
                expected_output_path=pipeline.whisper_path,
                inputs={"voice": voice_target},
                config={"force": force_whisper},
                dependencies={f"{sec_id}.tts"},
                section_id=sec_id,
            )
        )

        # 2. Storyboard Asset Extraction & Title Banner (Visual Branch Root)
        executor.add_task(
            ExecutableTask(
                task_id=f"{sec_id}.extraction",
                name=f"Storyboard Extraction ({sec_id})",
                component="extraction",
                resource_type="CPU_HEAVY",
                action=lambda: pipeline.step_extraction(),
                expected_output_path=meta_file,
                inputs={
                    "storyboard": str(pipeline.storyboard_path),
                    "title": pipeline.read_title_from_script(),
                },
                dependencies=set(),
                section_id=sec_id,
            )
        )

        # 3. Speech Synchronization & Micro-Zoning Layout (Convergence)
        executor.add_task(
            ExecutableTask(
                task_id=f"{sec_id}.layout_and_sync",
                name=f"Layout & Sync ({sec_id})",
                component="layout",
                resource_type="CPU_HEAVY",
                action=lambda: pipeline.step_layout_and_sync(custom_manifest=custom_manifest),
                expected_output_path=layout_file,
                inputs={
                    "whisper": pipeline.whisper_path,
                    "metadata": meta_file,
                    "manifest_items_count": len(custom_manifest) if custom_manifest else 0,
                },
                dependencies={f"{sec_id}.whisper", f"{sec_id}.extraction"},
                section_id=sec_id,
            )
        )

        # 4. AI Pre-Render Visual Director Approval Gate
        executor.add_task(
            ExecutableTask(
                task_id=f"{sec_id}.pre_render_director",
                name=f"AI Director Gate ({sec_id})",
                component="validation",
                resource_type="NETWORK_API",
                action=lambda: pipeline.step_pre_render_director(),
                expected_output_path=final_plan_file,
                inputs={"layout": layout_file},
                dependencies={f"{sec_id}.layout_and_sync"},
                section_id=sec_id,
            )
        )

        # 5. Master Audio Mixing & SFX Alignment
        executor.add_task(
            ExecutableTask(
                task_id=f"{sec_id}.audio_mix",
                name=f"Audio Mixing & SFX ({sec_id})",
                component="audio_mix",
                resource_type="DISK_IO",
                action=lambda: pipeline.step_audio_mix(),
                expected_output_path=master_audio_file,
                inputs={
                    "voice": str(pipeline.voice_path),
                    "layout": layout_file,
                },
                dependencies={f"{sec_id}.layout_and_sync", f"{sec_id}.pre_render_director"},
                section_id=sec_id,
            )
        )

        # 6. 1080p Video Rendering (Waits for Audio Mix & Director Gate)
        executor.add_task(
            ExecutableTask(
                task_id=f"{sec_id}.render",
                name=f"1080p Video Render ({sec_id})",
                component="render",
                resource_type="GPU_RENDER",
                action=lambda: pipeline.step_render(),
                expected_output_path=final_video_file,
                inputs={
                    "layout": layout_file,
                    "audio": master_audio_file,
                },
                dependencies={f"{sec_id}.audio_mix", f"{sec_id}.pre_render_director"},
                section_id=sec_id,
            )
        )

        # 7. Deliverables Publishing
        executor.add_task(
            ExecutableTask(
                task_id=f"{sec_id}.deliverable",
                name=f"Publish Deliverables ({sec_id})",
                component="deliverable",
                resource_type="DISK_IO",
                action=lambda: pipeline.step_publish(),
                expected_output_path=deliv_video_file,
                inputs={
                    "video": final_video_file,
                    "audio": master_audio_file,
                },
                dependencies={f"{sec_id}.render"},
                section_id=sec_id,
            )
        )

        return executor

    def run(
        self,
        force_whisper: bool = False,
        custom_manifest: Optional[List[Any]] = None,
        force_all: bool = False,
        force_tts: bool = False,
        tts_provider: Optional[Any] = None,
        cancel_token: Optional[Any] = None,
        target_mode: str = "full",
    ) -> str:
        """Execute section production pipeline via Core Task DAG with state persistence."""
        if cancel_token is not None:
            self.cancel_token = cancel_token

        if self.event_bus:
            self.event_bus.publish(
                PipelineLogEvent(
                    project_id=self.project_id,
                    section_id=self.section_id,
                    stage_id="sec.ingest",
                    level="INFO",
                    message=f"Starting production pipeline for section {self.section_id} (mode={target_mode})",
                )
            )

        state = self.state_store.load_state(self.project_id)
        sec_state = state.get_or_create_section(self.section_id)
        sec_state.transition_to(LifecycleStatus.RUNNING)
        self.state_store.save_state(state)

        try:
            pipeline = UniversalSectionPipeline(
                str(self.section_path),
                title=self.title,
                project_id=self.project_id,
            )
            executor = self.build_section_dag(
                pipeline=pipeline,
                force_whisper=force_whisper,
                custom_manifest=custom_manifest,
                force_tts=force_tts,
                tts_provider=tts_provider,
            )

            if target_mode == "to_review":
                review_targets = {
                    f"{self.section_id}.tts",
                    f"{self.section_id}.whisper",
                    f"{self.section_id}.extraction",
                }
                results = executor.execute(force_all=force_all, target_tasks=review_targets)

                # Set review gates and halt execution
                from core.contracts.studio_contracts import StageIdentifier
                from core.state.transitions import ReviewGateStatus, SectionLifecycleStatus
                from core.state.workflow_events import ReviewGateChangedEvent

                sec_state.set_review_gate(StageIdentifier.EXTRACTION.value, ReviewGateStatus.REVIEW_PENDING)
                sec_state.set_review_gate(StageIdentifier.TTS.value, ReviewGateStatus.REVIEW_PENDING)
                sec_state.set_review_gate(StageIdentifier.SEMANTIC.value, ReviewGateStatus.REVIEW_PENDING)
                sec_state.recompute_lifecycle()
                state.recompute_lifecycle()
                self.state_store.save_state(state)

                if self.event_bus:
                    for gid in (StageIdentifier.EXTRACTION.value, StageIdentifier.TTS.value, StageIdentifier.SEMANTIC.value):
                        self.event_bus.publish(
                            ReviewGateChangedEvent(
                                project_id=self.project_id,
                                section_id=self.section_id,
                                stage_id=gid,
                                old_status=ReviewGateStatus.NOT_APPLICABLE,
                                new_status=ReviewGateStatus.REVIEW_PENDING,
                                reason="Automatic processing completed. Awaiting user review.",
                            )
                        )
                    self.event_bus.publish(
                        PipelineLogEvent(
                            project_id=self.project_id,
                            section_id=self.section_id,
                            stage_id="sec.extraction",
                            level="INFO",
                            message=f"Section {self.section_id} completed initial processing and entered REVIEW GATE.",
                        )
                    )

                return "NEEDS_REVIEW"

            elif target_mode == "post_review":
                post_targets = {
                    f"{self.section_id}.layout_and_sync",
                    f"{self.section_id}.pre_render_director",
                    f"{self.section_id}.audio_mix",
                    f"{self.section_id}.render",
                    f"{self.section_id}.deliverable",
                }
                results = executor.execute(force_all=force_all, target_tasks=post_targets)
            else:
                results = executor.execute(force_all=force_all)

            deliverable_video = results.get(f"{self.section_id}.deliverable")
            if not deliverable_video or not Path(deliverable_video).exists():
                deliv_dir = PROJECT_ROOT / "output_animations" / self.project_id / "deliverables" / "sections"
                deliverable_video = str(deliv_dir / f"{self.section_id}_Whiteboard_1080p.mp4")

            sec_state.output_video_path = deliverable_video
            sec_state.transition_to(LifecycleStatus.COMPLETED)
            self.state_store.save_state(state)

            if self.event_bus:
                self.event_bus.publish(
                    PipelineLogEvent(
                        project_id=self.project_id,
                        section_id=self.section_id,
                        stage_id="sec.export",
                        level="INFO",
                        message=f"Section {self.section_id} finished successfully: {deliverable_video}",
                    )
                )

            return deliverable_video

        except Exception as e:
            sec_state.transition_to(LifecycleStatus.FAILED)
            self.state_store.save_state(state)

            if self.event_bus:
                self.event_bus.publish(
                    PipelineLogEvent(
                        project_id=self.project_id,
                        section_id=self.section_id,
                        stage_id="sec.error",
                        level="ERROR",
                        message=f"Section {self.section_id} production failed: {e}",
                    )
                )

            raise RuntimeError(f"Section {self.section_id} production failed: {e}") from e
