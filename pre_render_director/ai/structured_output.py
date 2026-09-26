"""Parser and validator for structured director AI outputs."""

import re
import json
from typing import Dict, Any, Optional

def clean_json_text(text: str) -> str:
    """Extracts JSON substring from markdown fences or raw text."""
    if not text:
        return "{}"
    text = text.strip()
    # Check for markdown json block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Check for outer curly braces
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text

def parse_director_response(raw_text: str) -> Dict[str, Any]:
    """Parses and sanitizes LLM output into a deterministic dictionary."""
    cleaned = clean_json_text(raw_text)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            # Normalize confidence and needs_review
            patch = data.get("patch_recommendation", {})
            if isinstance(patch, dict):
                conf = float(patch.get("confidence", 0.9))
                patch["confidence"] = conf
                if conf < 0.65:
                    patch["needs_review"] = True
            return data
    except Exception:
        pass

    # Safe fallback if LLM returned non-parsable content
    return {
        "semantic_match": "PARTIAL_MATCH",
        "match_score": 0.7,
        "contradiction_detected": False,
        "contradiction_reason": None,
        "temporal_strategy": "COMPLETE_ON_ANCHOR",
        "drawing_feasible": True,
        "optimal_timing": {},
        "visual_continuity": {
            "keep_previous_visible": True,
            "highlight_current": True,
            "clear_screen": False
        },
        "patch_recommendation": {
            "operation": "KEEP_EVENT",
            "target_asset_id": None,
            "changes": {},
            "reason": "Fallback default: keeping existing event.",
            "confidence": 0.6,
            "needs_review": True
        }
    }
