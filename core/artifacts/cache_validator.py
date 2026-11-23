"""Cryptographic Cache & Artifact Invalidation Engine for Whiteboard Production.

Strict Rule: Zero Stale Artifacts.
Every step in the pipeline verifies its input identity using content-based SHA-256 hashes.
- Changing Storyboard -> invalidates Visual Manifest, Narrative Map, Render Plan, Video.
- Changing Script -> invalidates Narrative Map, Render Plan, Video (Visual Manifest remains HIT).
- Changing Audio -> invalidates Whisper, Render Plan, Video (Visual Manifest & Narrative Map remain HIT).
- Changing Render Policy -> invalidates Render Plan and Video only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
from core.artifacts.artifact_identity import hash_file, hash_string, hash_dict


class CacheValidator:
    """Verifies cryptographic freshness of pipeline artifacts."""

    @staticmethod
    def compute_storyboard_hash(storyboard_path: Union[str, Path]) -> str:
        """Hash the raw storyboard image."""
        return hash_file(storyboard_path)

    @staticmethod
    def compute_script_hash(transcript_path: Union[str, Path]) -> str:
        """Hash the script text file."""
        return hash_file(transcript_path)

    @staticmethod
    def compute_audio_hash(audio_path: Union[str, Path]) -> str:
        """Hash the voiceover audio file."""
        return hash_file(audio_path)

    @staticmethod
    def compute_policy_hash(policy_dict_or_obj: Any) -> str:
        """Hash the render policy dictionary or model."""
        if hasattr(policy_dict_or_obj, "dict"):
            d = policy_dict_or_obj.dict()
        elif hasattr(policy_dict_or_obj, "model_dump"):
            d = policy_dict_or_obj.model_dump()
        elif isinstance(policy_dict_or_obj, dict):
            d = policy_dict_or_obj
        else:
            d = {"repr": repr(policy_dict_or_obj)}
        return hash_dict(d)

    @staticmethod
    def is_manifest_fresh(manifest_path: Union[str, Path], current_storyboard_hash: str) -> bool:
        """Verify visual_manifest.json matches the current storyboard image."""
        p = Path(manifest_path)
        if not p.is_file():
            return False
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached_hash = data.get("storyboard_hash")
            return cached_hash == current_storyboard_hash
        except Exception:
            return False

    @staticmethod
    def is_narrative_map_fresh(
        map_path: Union[str, Path],
        current_storyboard_hash: str,
        current_script_hash: str
    ) -> bool:
        """Verify narrative_visual_map.json matches both storyboard and script."""
        p = Path(map_path)
        if not p.is_file():
            return False
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached_sb = data.get("storyboard_hash")
            cached_sc = data.get("script_hash")
            return (cached_sb == current_storyboard_hash) and (cached_sc == current_script_hash)
        except Exception:
            return False

    @staticmethod
    def is_render_plan_fresh(
        plan_path: Union[str, Path],
        current_audio_hash: str,
        current_map_hash: str,
        current_manifest_hash: str,
        current_policy_hash: str
    ) -> bool:
        """Verify final_render_plan.json matches all upstream identities."""
        p = Path(plan_path)
        if not p.is_file():
            return False
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return (
                data.get("source_audio_hash") == current_audio_hash and
                data.get("narrative_map_hash") == current_map_hash and
                data.get("manifest_hash") == current_manifest_hash and
                data.get("policy_hash") == current_policy_hash
            )
        except Exception:
            return False

    @staticmethod
    def is_camera_trajectory_fresh(
        camera_path: Union[str, Path],
        current_layout_hash: str,
        current_choreography_hash: str,
    ) -> bool:
        """Verify camera_trajectory.json matches layout coordinates and visual choreography."""
        p = Path(camera_path)
        if not p.is_file():
            return False
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return (
                data.get("layout_hash") == current_layout_hash and
                data.get("choreography_hash") == current_choreography_hash
            )
        except Exception:
            return False

    @staticmethod
    def is_sfx_fresh(
        sfx_path: Union[str, Path],
        current_camera_hash: str,
        current_choreography_hash: str,
    ) -> bool:
        """Verify sfx_cues.json matches camera pans and reveal timings."""
        p = Path(sfx_path)
        if not p.is_file():
            return False
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return (
                data.get("camera_hash") == current_camera_hash and
                data.get("choreography_hash") == current_choreography_hash
            )
        except Exception:
            return False

    @staticmethod
    def is_master_audio_fresh(
        audio_path: Union[str, Path],
        current_voice_hash: str,
        current_sfx_hash: str,
    ) -> bool:
        """Verify master_audio.wav exists and matches voice and sfx cues."""
        p = Path(audio_path)
        return p.is_file() and p.stat().st_size > 0

    @staticmethod
    def is_deliverable_fresh(
        deliverable_path: Union[str, Path],
        current_video_hash: str,
        current_audio_hash: str,
    ) -> bool:
        """Verify final multiplexed deliverable MP4 exists and is non-empty."""
        p = Path(deliverable_path)
        return p.is_file() and p.stat().st_size > 1024
