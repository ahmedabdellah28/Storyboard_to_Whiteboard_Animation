"""Prompt builder for multimodal AI Visual Director."""

import json
from typing import Dict, Any, List, Optional

class DirectorPromptBuilder:
    """Builds structured director prompts for Gemini multimodal analysis."""

    SYSTEM_INSTRUCTION = """You are the Senior Whiteboard Animation Director, Visual Synchronization Director, and Timeline QA Engineer.
Your job is NOT to render video, draw pixels, or alter audio.
Your job is strictly to:
1. UNDERSTAND: Understand the Arabic narration speech intent and the visual meaning of candidate assets.
2. VALIDATE: Validate whether the proposed visual asset semantically and temporally matches what is being spoken at this exact moment.
3. DETECT CONTRADICTIONS: Catch any contradiction between narration and visual evidence (e.g. narration says sleeping on concrete ground, but asset depicts a bench).
4. SYNCHRONIZE: Ensure drawing inking starts early enough so that it COMPLETES on the semantic anchor word (or appropriate timing strategy).
5. CONTINUITY: Decide visual state transitions (what stays visible on canvas, what gets cleared, density limits).
6. PATCH: If there is an issue, propose a surgical, discrete timeline patch (ADD_EVENT, REMOVE_EVENT, UPDATE_EVENT, MOVE_EVENT, RESIZE_EVENT, CHANGE_ASSET, KEEP_EVENT, REJECT_EVENT).

CRITICAL CONSTRAINTS:
- Audio timestamps and Whisper transcriptions are immutable ground truth.
- Script text is immutable ground truth.
- Return ONLY valid JSON adhering to the specified schema.
- If confidence < 0.65, set needs_review=true.
"""

    @classmethod
    def build_event_analysis_prompt(
        cls,
        event_dict: Dict[str, Any],
        asset_info: Optional[Dict[str, Any]],
        speech_context: Dict[str, Any],
        look_behind_event: Optional[Dict[str, Any]] = None,
        look_ahead_event: Optional[Dict[str, Any]] = None,
        available_assets_summary: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        prompt_data = {
            "task": "EVALUATE_VISUAL_EVENT",
            "current_event": event_dict,
            "current_asset_metadata": asset_info,
            "speech_context": {
                "anchor_text": speech_context.get("anchor_text", ""),
                "sentence_text": speech_context.get("sentence_text", ""),
                "word_timestamps": speech_context.get("words", []),
                "pause_before_s": speech_context.get("pause_before_s", 0.0),
                "pause_after_s": speech_context.get("pause_after_s", 0.0),
                "audio_total_duration": speech_context.get("audio_total_duration", 0.0)
            },
            "look_behind_previous_event": look_behind_event,
            "look_ahead_next_event": look_ahead_event,
            "available_alternative_assets": available_assets_summary or []
        }

        prompt_str = f"""{cls.SYSTEM_INSTRUCTION}

Analyze the following visual event in context of the narration and the visual evidence provided in the accompanying image(s):

DATA:
```json
{json.dumps(prompt_data, ensure_ascii=False, indent=2)}
```

You must return a JSON object with EXACTLY this structure:
{{
  "semantic_match": "EXACT_MATCH" | "STRONG_MATCH" | "PARTIAL_MATCH" | "WEAK_MATCH" | "CONTRADICTORY" | "INVALID",
  "match_score": 0.0 to 1.0,
  "contradiction_detected": true | false,
  "contradiction_reason": "string or null",
  "temporal_strategy": "COMPLETE_ON_ANCHOR" | "START_ON_ANCHOR" | "CENTER_ON_ANCHOR" | "REVEAL_ON_ANCHOR" | "DURING_PAUSE",
  "drawing_feasible": true | false,
  "optimal_timing": {{
    "start_s": float,
    "end_s": float,
    "duration_s": float
  }},
  "visual_continuity": {{
    "keep_previous_visible": true | false,
    "highlight_current": true | false,
    "clear_screen": true | false
  }},
  "patch_recommendation": {{
    "operation": "KEEP_EVENT" | "UPDATE_EVENT" | "CHANGE_ASSET" | "REMOVE_EVENT" | "ADD_EVENT" | "RESIZE_EVENT",
    "target_asset_id": "string or null",
    "changes": {{}},
    "reason": "Detailed justification from director perspective",
    "confidence": float (0.0 to 1.0),
    "needs_review": true | false
  }}
}}
"""
        return prompt_str

    @classmethod
    def build_batch_overview_prompt(
        cls,
        script_text: str,
        events: List[Dict[str, Any]],
        catalog: Dict[str, Any]
    ) -> str:
        prompt_data = {
            "task": "OVERVIEW_VALIDATION",
            "script_text": script_text,
            "events_count": len(events),
            "events_sample": events[:15],
            "catalog_asset_ids": list(catalog.keys())
        }
        return f"""{cls.SYSTEM_INSTRUCTION}
Perform high-level director review of storyboard events against the script:
```json
{json.dumps(prompt_data, ensure_ascii=False, indent=2)}
```
Identify any glaring timeline anomalies, word-by-word literal animations to avoid, or missing assets.
Output a JSON list of high-level warnings and suggested patches.
"""
