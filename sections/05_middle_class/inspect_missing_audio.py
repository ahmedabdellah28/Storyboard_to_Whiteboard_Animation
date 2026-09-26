import os
from faster_whisper import WhisperModel
import wave
import numpy as np

audio_path = r"E:\image_to_animate\sections\05_middle_class\voice\section.wav"

# Read audio between 74.0s and 83.0s
with wave.open(audio_path, 'rb') as wf:
    sr = wf.getframerate()
    ch = wf.getnchannels()
    n_frames = wf.getnframes()
    
    wf.setpos(int(74.0 * sr))
    data = wf.readframes(int(9.0 * sr))
    samples = np.frombuffer(data, dtype=np.int16)
    if ch == 2:
        samples = samples[::2]
    audio_float = samples.astype(np.float32) / 32768.0

print(f"Max amp: {np.max(np.abs(audio_float)):.3f}, Mean amp: {np.mean(np.abs(audio_float)):.3f}")

model = WhisperModel("small", device="auto")
segments, info = model.transcribe(audio_float, language="ar", word_timestamps=True)
for seg in segments:
    print(f"[{74.0 + seg.start:.2f} .. {74.0 + seg.end:.2f}] {seg.text}")
    for w in seg.words:
        print(f"   {74.0 + w.start:.2f} .. {74.0 + w.end:.2f}: {w.word}")
