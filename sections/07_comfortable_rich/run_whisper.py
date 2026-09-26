import os
import sys
import json
from faster_whisper import WhisperModel

sys.stdout.reconfigure(encoding='utf-8')

audio_path = r"E:\image_to_animate\sections\07_comfortable_rich\voiceover.wav"
out_dir = r"E:\image_to_animate\sections\07_comfortable_rich\timing"
os.makedirs(out_dir, exist_ok=True)
out_json = os.path.join(out_dir, "whisper.json")

print("Transcribing with Faster-Whisper (cpu/int8)...", flush=True)
model = WhisperModel("base", device="cpu", compute_type="int8")
segments, _ = model.transcribe(audio_path, language="ar", word_timestamps=True)

res = []
for s in segments:
    words = [{'word': w.word, 'start': round(w.start, 2), 'end': round(w.end, 2)} for w in s.words] if s.words else []
    res.append({'start': round(s.start, 2), 'end': round(s.end, 2), 'text': s.text.strip(), 'words': words})

with open(out_json, "w", encoding="utf-8") as f:
    json.dump({'segments': res}, f, indent=2, ensure_ascii=False)

print(f"Transcribed {len(res)} segments to {out_json}")
for s in res:
    print(f"[{s['start']:5.2f} - {s['end']:5.2f}] {s['text']}")
