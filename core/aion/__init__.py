"""Unified AION Production Pipeline Package (`core.aion`).

Consolidates the 12-stage workflow behind `pipeline_cli.py`:
Script -> Voice -> Timing -> Extract -> Semantic Mapping -> Creative Brief ->
AI Director -> Motion Graphics -> SFX -> EffectCraft -> Render -> QA -> Merge.
"""
from __future__ import annotations

from core.aion.contracts import PIPELINE_STAGES, SECTION_STAGES

__all__ = ["PIPELINE_STAGES", "SECTION_STAGES"]
