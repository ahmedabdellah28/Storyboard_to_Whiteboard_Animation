#!/usr/bin/env python3
import sys
import core_engine.dns_patch
from produce_shorts_pipeline import prepare_short_folders, generate_short_voice, generate_short_timing, SHORTS_CONFIG

def main():
    print("=== Generating Voice and Whisper Timing for 3 YouTube Shorts ===")
    for short_id in ["short_01", "short_02", "short_03"]:
        print(f"\n--- Processing {short_id} ---")
        paths = prepare_short_folders(short_id)
        dur = generate_short_voice(short_id, paths)
        print(f"[{short_id}] Audio Duration: {dur:.2f}s")
        words = generate_short_timing(short_id, paths)
        print(f"[{short_id}] Aligned {len(words)} words.")

if __name__ == "__main__":
    main()
