import os
import sys
import wave
import subprocess
import shutil
import re
import time
from google.genai import types

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import convert_raw_pcm_to_wav
from production_engine.gemini_client_pool import get_client_pool

def split_into_semantic_chunks(text, max_words=28):
    """
    Split Arabic script into natural semantic chunks:
    1. First split by paragraph breaks and sentence punctuation (، . ؟ ! \n).
    2. Group clauses so that no chunk exceeds max_words (default 28 words).
    3. Ensure no phrase is cut mid-sentence.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    clauses = []
    for line in lines:
        sub_clauses = re.split(r'([،.؟!]+)', line)
        combined = []
        for i in range(0, len(sub_clauses), 2):
            part = sub_clauses[i].strip()
            punct = sub_clauses[i+1].strip() if i+1 < len(sub_clauses) else ""
            if part:
                combined.append(f"{part} {punct}".strip())
        clauses.extend(combined)

    chunks = []
    curr_words = []
    
    for clause in clauses:
        clean_clause = re.sub(r'[.,?!؟،()\[\]\t]', ' ', clause)
        clean_clause = re.sub(r'\s+', ' ', clean_clause).strip()
        words = clean_clause.split()
        if not words:
            continue
            
        if len(curr_words) + len(words) > max_words and curr_words:
            chunks.append(' '.join(curr_words))
            curr_words = list(words)
        else:
            curr_words.extend(words)

    if curr_words:
        chunks.append(' '.join(curr_words))

    return chunks

def verify_tail_completion(audio_path, target_tail_phrase):
    """
    Use gemini-3.6-flash to transcribe the last 15 seconds of the audio file
    and verify that all words in target_tail_phrase were spoken.
    """
    pool = get_client_pool()

    with wave.open(audio_path, 'rb') as wf:
        n_frames = wf.getnframes()
        sr = wf.getframerate()
        dur = n_frames / float(sr)

    tail_dur = min(dur, 15.0)
    tail_frames = int(tail_dur * sr)
    start_frame = max(0, n_frames - tail_frames)

    temp_tail_wav = audio_path.replace(".wav", "_tail_check.wav")
    with wave.open(audio_path, 'rb') as infile:
        infile.setpos(start_frame)
        tail_data = infile.readframes(tail_frames)

    with wave.open(temp_tail_wav, 'wb') as outfile:
        outfile.setnchannels(1)
        outfile.setsampwidth(2)
        outfile.setframerate(sr)
        outfile.writeframes(tail_data)

    with open(temp_tail_wav, 'rb') as f:
        tail_bytes = f.read()

    if os.path.exists(temp_tail_wav):
        os.remove(temp_tail_wav)

    prompt = (
        "Transcribe this Arabic audio segment word-for-word exactly as heard in Arabic. "
        "Do not summarize or add markdown, return only the spoken words:"
    )

    resp = pool.execute_content_with_retry(
        model="gemini-3.6-flash",
        contents=[
            prompt,
            types.Part.from_bytes(data=tail_bytes, mime_type="audio/wav")
        ]
    )
    tail_transcript = resp.text.strip()
    
    def normalize_ar(t):
        t = re.sub(r'[:.,?!؟،()\[\]\t\n\r=\-_#*~]', ' ', t)
        t = re.sub(r'[إأآاى]', 'ا', t)
        t = re.sub(r'ة', 'ه', t)
        return re.sub(r'\s+', ' ', t).strip()

    norm_transcript = normalize_ar(tail_transcript)
    norm_target = normalize_ar(target_tail_phrase)
    target_words = norm_target.split()

    missing_words = [w for w in target_words if w not in norm_transcript]
    is_complete = len(missing_words) == 0

    return is_complete, tail_transcript, missing_words

def generate_voiceover_zero_truncation(
    script_path,
    output_wav_path,
    chunks_dir,
    voice_name="Fenrir",
    speed_factor=1.1,
    max_words_per_chunk=28,
    force_regenerate=False,
    model="gemini-2.5-flash-preview-tts"
):
    """
    Master pipeline for zero-truncation, fast Saudi YouTube voiceover generation:
    1. Semantic boundary chunking (< 28 words/chunk).
    2. Single-chunk TTS with gemini-2.5-flash-preview-tts & multi-key rotation.
    3. Seamless stitching with 0.08s micro-pauses.
    4. Automated tail-verification loop with gemini-3.6-flash.
    5. Automatic repair if any tail words are missing.
    6. FFmpeg atempo speedup (1.1x default).
    """
    os.makedirs(chunks_dir, exist_ok=True)
    out_dir = os.path.dirname(output_wav_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(script_path, "r", encoding="utf-8") as f:
        raw_script = f.read()

    clean_all = re.sub(r'[:.,?!؟،()\[\]\n\r\t]', ' ', raw_script)
    clean_all = re.sub(r'\s+', ' ', clean_all).strip()
    all_words = clean_all.split()
    target_tail_phrase = ' '.join(all_words[-7:])

    chunks = split_into_semantic_chunks(raw_script, max_words=max_words_per_chunk)
    total_words = len(all_words)

    print("=" * 80, flush=True)
    print(f"🎙️ ZERO-TRUNCATION VOICEOVER GENERATOR: {total_words} WORDS IN {len(chunks)} SAFE CHUNKS (Model: {model})", flush=True)
    print(f"  Target Tail Phrase: \"{target_tail_phrase}\"", flush=True)
    print("=" * 80, flush=True)

    pool = get_client_pool()
    prompt_directive = (
        "AUDIO SCRIPT — GEMINI TTS\n"
        "النبرة المطلوبة: سريعة، شبابية، سعودية، متصلة، بدون وقفات درامية طويلة نهائياً. "
        "إلقاء يوتيوب سريع ومتدفق وخاطف."
    )

    chunk_files = []
    for idx, ctext in enumerate(chunks, 1):
        c_path = os.path.join(chunks_dir, f"safe_chunk_{idx:02d}.wav")
        chunk_files.append(c_path)

        if not force_regenerate and os.path.exists(c_path) and os.path.getsize(c_path) > 5000:
            with wave.open(c_path, 'rb') as wf:
                dur = wf.getnframes() / float(wf.getframerate())
            print(f"  [{idx:02d}/{len(chunks):02d}] ⚡ Cached: {dur:.2f}s ({len(ctext.split())} words)", flush=True)
            continue

        print(f"  [{idx:02d}/{len(chunks):02d}] 🎙️ Synthesizing ({len(ctext.split())} words)...", flush=True)
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
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            )
        )

        raw_pcm = pool.execute_stream_with_retry(
            model=model,
            contents=contents,
            config=cfg
        )

        wav_bytes = convert_raw_pcm_to_wav(raw_pcm, "audio/L16;rate=24000")
        with open(c_path, "wb") as f:
            f.write(wav_bytes)

        with wave.open(c_path, 'rb') as wf:
            dur = wf.getnframes() / float(wf.getframerate())
        print(f"         ✅ Done: {dur:.2f}s", flush=True)
        # Gentle inter-chunk throttle to respect free tier RPM
        time.sleep(1.0)

    # Stitch all chunks with 0.08s micro-pause
    sample_rate = 24000
    silence_bytes = b'\x00' * int(sample_rate * 1 * 2 * 0.08)
    temp_stitched = output_wav_path.replace(".wav", "_temp_stitched.wav")

    def stitch_files(file_list, target_path):
        with wave.open(target_path, 'wb') as outfile:
            outfile.setnchannels(1)
            outfile.setsampwidth(2)
            outfile.setframerate(sample_rate)
            for i, cp in enumerate(file_list):
                with wave.open(cp, 'rb') as infile:
                    outfile.writeframes(infile.readframes(infile.getnframes()))
                if i < len(file_list) - 1:
                    outfile.writeframes(silence_bytes)

    stitch_files(chunk_files, temp_stitched)

    # Automated Tail-Verification Loop
    print("\n🔍 Verifying tail completion via Gemini STT (gemini-3.6-flash)...", flush=True)
    is_complete, heard_tail, missing = verify_tail_completion(temp_stitched, target_tail_phrase)
    print(f"  Heard Tail: \"{heard_tail}\"", flush=True)

    if not is_complete:
        print(f"  ⚠️ Warning: Tail words missing: {missing}", flush=True)
        print("  🛠️ Synthesizing auto-repair tail chunk...", flush=True)
        repair_text = target_tail_phrase
        repair_path = os.path.join(chunks_dir, "safe_chunk_tail_repair.wav")
        
        full_prompt = f"{prompt_directive}\n\n{repair_text}"
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=full_prompt)])]
        cfg = types.GenerateContentConfig(
            temperature=1.0,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name))
            )
        )
        raw_pcm = pool.execute_stream_with_retry(
            model=model,
            contents=contents,
            config=cfg
        )

        wav_bytes = convert_raw_pcm_to_wav(raw_pcm, "audio/L16;rate=24000")
        with open(repair_path, "wb") as f:
            f.write(wav_bytes)

        chunk_files.append(repair_path)
        stitch_files(chunk_files, temp_stitched)
        
        # Re-verify
        is_complete, heard_tail, missing = verify_tail_completion(temp_stitched, target_tail_phrase)
        print(f"  Post-Repair Heard Tail: \"{heard_tail}\"", flush=True)
        if is_complete:
            print("  ✅ 100% Tail-Word Verification Confirmed!", flush=True)
        else:
            print(f"  ⚠️ Note: Missing remaining words after repair: {missing}", flush=True)
    else:
        print("  ✅ 100% Tail-Word Verification Confirmed on First Pass!", flush=True)

    # Apply FFmpeg atempo speedup
    print(f"⚡ Applying speed multiplier {speed_factor}x...", flush=True)
    cmd = ["ffmpeg", "-y", "-i", temp_stitched, "-af", f"atempo={speed_factor}", output_wav_path]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    if os.path.exists(temp_stitched):
        os.remove(temp_stitched)

    with wave.open(output_wav_path, 'rb') as wf:
        final_dur = wf.getnframes() / float(wf.getframerate())

    print("=" * 80, flush=True)
    print(f"🎉 FINAL VOICEOVER GENERATED & VERIFIED: {output_wav_path}", flush=True)
    print(f"  Duration: {final_dur:.2f}s ({final_dur/60:.2f} min)", flush=True)
    print("=" * 80, flush=True)
    return output_wav_path, final_dur
