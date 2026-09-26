import os
import sys
import wave
import subprocess
import shutil
import re

# Safe UTF-8 console output
sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import convert_raw_pcm_to_wav
from google import genai
from google.genai import types

SEC_DIR = os.path.join(ROOT_DIR, "sections", "01_homeless")
SCRIPT_PATH = os.path.join(SEC_DIR, "script.txt")
CHUNKS_DIR = os.path.join(SEC_DIR, "audio_chunks")
FINAL_WAV = os.path.join(SEC_DIR, "voiceover.wav")
DELIV_DIR = os.path.join(ROOT_DIR, "output_animations", "wealth_classes_documentary", "deliverables", "sections")
os.makedirs(CHUNKS_DIR, exist_ok=True)
os.makedirs(DELIV_DIR, exist_ok=True)

with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
    raw_script = f.read()

# Clean all punctuation and format into continuous rapid stream
clean_text = re.sub(r'[.,?!؟،()\[\]\n\r\t]', ' ', raw_script)
clean_text = re.sub(r'\s+', ' ', clean_text).strip()
words = clean_text.split()
total_words = len(words)

# Break into 6 balanced chunks of ~51 words
num_chunks = 6
chunk_size = (total_words + num_chunks - 1) // num_chunks
chunks = []
for i in range(0, total_words, chunk_size):
    ch = ' '.join(words[i:min(total_words, i+chunk_size)])
    chunks.append(ch)

print("=" * 75)
print(f"🎙️ GENERATING SECTION 01 VOICEOVER: {total_words} WORDS IN {len(chunks)} SAFE CHUNKS")
print("=" * 75)

# Load Gemini Client
with open(os.path.join(ROOT_DIR, ".env")) as f:
    for l in f:
        if l.startswith("GEMINI_API_KEY="):
            api_key = l.strip().split("=", 1)[1]
            break

client = genai.Client(api_key=api_key)

prompt_directive = """AUDIO SCRIPT — GEMINI TTS
النبرة المطلوبة: سريعة، شبابية، سعودية، متصلة، بدون وقفات درامية طويلة نهائياً. إلقاء يوتيوب سريع ومتدفق وخاطف."""

chunk_files = []
for idx, ctext in enumerate(chunks, 1):
    c_path = os.path.join(CHUNKS_DIR, f"chunk_{idx:02d}.wav")
    chunk_files.append(c_path)

    # Check if cached
    if os.path.exists(c_path) and os.path.getsize(c_path) > 5000:
        with wave.open(c_path, 'rb') as wf:
            dur = wf.getnframes() / float(wf.getframerate())
        print(f"  [{idx}/{len(chunks)}] ⚡ Cached chunk_{idx:02d}.wav: {dur:.2f}s ({len(ctext.split())} words)")
        continue

    print(f"  [{idx}/{len(chunks)}] 🎙️ Synthesizing chunk_{idx:02d} ({len(ctext.split())} words)...")
    full_prompt = f"{prompt_directive}\n\n{ctext}"
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=full_prompt)]
        )
    ]
    cfg = types.GenerateContentConfig(
        temperature=1.0,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Fenrir")
            )
        )
    )

    audio_data = bytearray()
    for chunk in client.models.generate_content_stream(model="gemini-3.1-flash-tts-preview", contents=contents, config=cfg):
        if chunk.parts:
            for p in chunk.parts:
                if p.inline_data and p.inline_data.data:
                    audio_data.extend(p.inline_data.data)

    wav_bytes = convert_raw_pcm_to_wav(bytes(audio_data), "audio/L16;rate=24000")
    with open(c_path, "wb") as f:
        f.write(wav_bytes)

    with wave.open(c_path, 'rb') as wf:
        dur = wf.getnframes() / float(wf.getframerate())
    print(f"    ✅ Done: {dur:.2f}s audio duration.")

# Seamless concatenation with 0.08s natural micro-pause
print("\n🔗 Seamlessly stitching chunks with 0.08s pauses...")
raw_concat = os.path.join(SEC_DIR, "raw_concat.wav")
sample_rate = 24000
silence_bytes = b'\x00' * int(sample_rate * 1 * 2 * 0.08)

with wave.open(raw_concat, 'wb') as outfile:
    outfile.setnchannels(1)
    outfile.setsampwidth(2)
    outfile.setframerate(sample_rate)
    for idx, cp in enumerate(chunk_files):
        with wave.open(cp, 'rb') as infile:
            outfile.writeframes(infile.readframes(infile.getnframes()))
        if idx < len(chunk_files) - 1:
            outfile.writeframes(silence_bytes)

# Apply 1.1x speed multiplier via FFmpeg
print("⚡ Applying speed multiplier 1.1x...")
cmd = ["ffmpeg", "-y", "-i", raw_concat, "-af", "atempo=1.1", FINAL_WAV]
subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
if os.path.exists(raw_concat):
    os.remove(raw_concat)

# Copy to deliverables
deliv_wav = os.path.join(DELIV_DIR, "01_Homeless_Voiceover.wav")
shutil.copyfile(FINAL_WAV, deliv_wav)

with wave.open(FINAL_WAV, 'rb') as wf:
    final_dur = wf.getnframes() / float(wf.getframerate())

print("=" * 75)
print(f"🎉 SECTION 01 VOICEOVER COMPLETE!")
print(f"  • File Path   : {FINAL_WAV}")
print(f"  • Deliverable : {deliv_wav}")
print(f"  • Duration    : {final_dur:.2f}s ({final_dur/60:.2f} mins)")
print("=" * 75)
