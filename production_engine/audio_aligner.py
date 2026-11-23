import os
import sys
import wave
import json
import re
import numpy as np
from google.genai import types

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.gemini_client_pool import get_client_pool

def align_anchor_phrases(voiceover_path, anchor_dict):
    """
    Pass the voiceover audio to gemini-3.6-flash and extract exact start timestamps (seconds)
    for each anchor phrase in anchor_dict.
    
    anchor_dict: { aid: "Arabic anchor phrase", ... }
    returns: { aid: timestamp_seconds, ... }
    """
    pool = get_client_pool()

    import subprocess
    temp_mp3 = voiceover_path.replace(".wav", "_align_temp.mp3")
    subprocess.run(["ffmpeg", "-y", "-i", voiceover_path, "-ar", "16000", "-ac", "1", "-b:a", "64k", temp_mp3], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    with open(temp_mp3, "rb") as f:
        audio_bytes = f.read()
    if os.path.exists(temp_mp3):
        os.remove(temp_mp3)

    # Split into batches of up to 12 anchors to ensure highest precision
    items = list(anchor_dict.items())
    batch_size = 12
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

    all_timestamps = {}

    print(f"🎯 Running Semantic Speech Alignment on {len(items)} anchors in {len(batches)} batches...")

    for b_idx, batch in enumerate(batches, 1):
        batch_dict = dict(batch)
        prompt = f"""You are an expert audio-visual synchronization sound engineer.
Listen attentively to this Arabic voiceover audio.
For each element in the following JSON, find the EXACT timestamp in seconds (as a float, e.g. 14.35) when the narrator begins pronouncing that specific anchor phrase in the audio.

ANCHOR PHRASES TO LOCATE:
{json.dumps(batch_dict, ensure_ascii=False, indent=2)}

INSTRUCTIONS:
1. Return ONLY a single valid JSON object mapping each element ID (aid) to its start timestamp in seconds as a float.
2. Ensure timestamps are strictly chronological and accurate to within 0.1 seconds.
3. Do not include markdown code fences (no ```json or ```).
"""
        resp = pool.execute_content_with_retry(
            model="gemini-3.5-flash-lite",
            contents=[
                prompt,
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/mp3")
            ]
        )

        raw_resp = resp.text.strip()
        raw_resp = re.sub(r'^```(?:json)?\s*', '', raw_resp)
        raw_resp = re.sub(r'\s*```$', '', raw_resp)

        try:
            parsed = json.loads(raw_resp)
            for k, v in parsed.items():
                all_timestamps[k] = float(v)
            print(f"  Batch {b_idx}/{len(batches)} aligned successfully ({len(parsed)} items).")
        except Exception as e:
            print(f"  ⚠️ Error parsing batch {b_idx} JSON: {e}\nRaw output: {raw_resp}")
            matches = re.findall(r'\"([^\"]+)\"\s*:\s*([0-9]+(?:\.[0-9]+)?)', raw_resp)
            for k, v in matches:
                all_timestamps[k] = float(v)

    return all_timestamps

def calculate_synced_staging(anchor_timestamps, element_types, durations=None, lead_sec=0.20):
    """
    Given exact anchor timestamps, calculate production staging specs:
    - t_start = max(0.0, word_t - lead_sec) (begins drawing 0.20s before speech)
    - t_dur = duration according to element type and speech window
    """
    if durations is None:
        durations = {
            "outside_in_pen": 2.0,
            "slide_down": 1.4,
            "slide_up": 1.4,
            "jelly_pop": 1.4,
            "pulse_pop": 1.5,
            "organic_grow": 1.8
        }

    sorted_anchors = sorted(anchor_timestamps.items(), key=lambda x: x[1])
    staging_specs = []

    for i, (aid, word_t) in enumerate(sorted_anchors):
        anim_type = element_types.get(aid, "slide_down")
        depth = 5 if anim_type == "outside_in_pen" else 4
        
        t_st = max(0.0, word_t - lead_sec)
        
        default_dur = durations.get(anim_type, 1.5)
        if i < len(sorted_anchors) - 1:
            next_t = sorted_anchors[i+1][1] - lead_sec
            available_gap = next_t - t_st
            t_dur = min(default_dur, max(1.0, available_gap * 0.90))
        else:
            t_dur = default_dur

        staging_specs.append((aid, round(t_st, 2), round(t_dur, 2), anim_type, depth))

    return staging_specs
