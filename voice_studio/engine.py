"""
Voice Studio Core Engine
Direct integration with Google GenAI SDK (gemini-3.1-flash-tts-preview).
Optimized for Bendia-style fast-paced 20-asset YouTube scripts:
- Full-section synthesis (up to 180 words per section) to prevent mid-story tone resets
- Automatic leading/trailing silence trimming for tight, zero-dead-air transitions
- Stage-cue extraction so bracketed tags guide emotion without being read aloud
- Content-hash caching so script edits regenerate automatically
"""
import os
import sys
import core_engine.dns_patch
import time
import re
import hashlib
import struct
import wave
import subprocess
import mimetypes
from typing import Dict, Any, Optional, List
from .profiles import AudioProfile, DirectorNote, AUDIO_PROFILES, DIRECTOR_NOTES

# Safe UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def parse_audio_mime_type(mime_type: str) -> Dict[str, int]:
    """Parses bits per sample and rate from an audio MIME type string (e.g. 'audio/L16;rate=24000')."""
    bits_per_sample = 16
    rate = 24000
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}


def convert_raw_pcm_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Wraps raw linear PCM audio stream into a valid standard RIFF/WAVE header."""
    from core.audio.wav_utils import pcm_to_wav
    return pcm_to_wav(audio_data, mime_type=mime_type)


def trim_pcm_silence(
    pcm_bytes: bytes,
    sample_rate: int = 24000,
    bits_per_sample: int = 16,
    threshold: int = 180,
    pad_ms: int = 35
) -> bytes:
    """
    Trims excess dead silence that Gemini TTS pads at the start and end of generated audio chunks,
    preserving a tiny natural pad (35ms) so fast-paced sections flow seamlessly without robotic clipping
    or 1-second dead-air gaps.
    """
    if bits_per_sample != 16 or len(pcm_bytes) < 400:
        return pcm_bytes

    num_samples = len(pcm_bytes) // 2
    samples = struct.unpack(f"<{num_samples}h", pcm_bytes[:num_samples * 2])

    first_idx = 0
    for idx, val in enumerate(samples):
        if abs(val) > threshold:
            first_idx = idx
            break
    else:
        return pcm_bytes

    last_idx = num_samples - 1
    for idx in range(num_samples - 1, -1, -1):
        if abs(samples[idx]) > threshold:
            last_idx = idx
            break

    pad_samples = int((sample_rate * pad_ms) / 1000.0)
    start_sample = max(0, first_idx - pad_samples)
    end_sample = min(num_samples, last_idx + pad_samples + 1)

    if start_sample >= end_sample:
        return pcm_bytes

    return pcm_bytes[start_sample * 2:end_sample * 2]


def split_transcript_into_sections(transcript: str, max_words_per_chunk: int = 75) -> List[Dict[str, Any]]:
    """
    Splits a script into logical story sections based on [tag] annotations or SECTION headers.
    Default max_words_per_chunk is set to 75 so each chunk stays safely below Gemini TTS's
    ~32-second per-call audio token ceiling while sub-splitting cleanly at sentence boundaries.
    """
    # Support both [tag] cues (English/Arabic) and SECTION XX headers if present
    pattern = r'(\[[^\[\]\n]{1,70}\])'
    parts = re.split(pattern, transcript)

    initial_sections = []
    curr_tag = ""
    for p in parts:
        p_str = p.strip()
        if not p_str:
            continue
        if p_str.startswith('[') and p_str.endswith(']'):
            curr_tag = p_str
        else:
            full_chunk = f"{curr_tag}\n{p_str}" if curr_tag else p_str
            clean_words = re.sub(r'\[.*?\]', '', full_chunk).split()
            if clean_words:
                initial_sections.append({
                    "tag": curr_tag,
                    "text": full_chunk,
                    "words": len(clean_words)
                })

    if not initial_sections:
        clean_words = re.sub(r'\[.*?\]', '', transcript).split()
        initial_sections.append({
            "tag": "",
            "text": transcript,
            "words": len(clean_words)
        })

    # Sub-divide any section that exceeds max_words_per_chunk at real sentence terminators only
    final_sections = []
    for sec in initial_sections:
        if sec["words"] <= max_words_per_chunk:
            final_sections.append(sec)
        else:
            tag = sec["tag"]
            raw_text = re.sub(r'\[.*?\]', '', sec["text"]).strip()
            # Normalize single line wraps inside the same paragraph so sentences aren't chopped mid-phrase
            raw_text = re.sub(r'(?<![.!?؟:\n])\n(?!\n)', ' ', raw_text)
            sentence_parts = re.split(r'([.!?؟]+|\n\n+)', raw_text)
            buffer = []
            buf_words = 0
            for i in range(0, len(sentence_parts), 2):
                s = sentence_parts[i].strip()
                punct = sentence_parts[i + 1].strip() if i + 1 < len(sentence_parts) else ""
                full_sent = f"{s}{punct}".strip()
                if not full_sent:
                    continue
                w_count = len(full_sent.split())
                if buf_words + w_count > max_words_per_chunk and buffer:
                    chunk_text = " ".join(buffer)
                    if tag:
                        chunk_text = f"{tag}\n{chunk_text}"
                    final_sections.append({
                        "tag": tag,
                        "text": chunk_text,
                        "words": buf_words
                    })
                    buffer = [full_sent]
                    buf_words = w_count
                else:
                    buffer.append(full_sent)
                    buf_words += w_count
            if buffer:
                chunk_text = " ".join(buffer)
                if tag:
                    chunk_text = f"{tag}\n{chunk_text}"
                final_sections.append({
                    "tag": tag,
                    "text": chunk_text,
                    "words": buf_words
                })

    return final_sections


class VoiceStudioEngine:
    """
    Dedicated Voice Studio TTS Engine using Google GenAI SDK.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.1-flash-tts-preview"):
        from core.config.env_loader import get_gemini_api_keys

        self.api_keys: List[str] = []
        if api_key and api_key.strip() != "YOUR_GEMINI_API_KEY_HERE":
            self.api_keys.append(api_key.strip())

        # Load all valid keys from unified loader
        for k in get_gemini_api_keys():
            if k not in self.api_keys:
                self.api_keys.append(k)

        self.api_key = self.api_keys[0] if self.api_keys else None
        self.model = model

    def rotate_key(self) -> Optional[str]:
        """Rotates to the next available API key in the pool."""
        if len(self.api_keys) > 1:
            curr = self.api_keys.pop(0)
            self.api_keys.append(curr)
            self.api_key = self.api_keys[0]
            print(f"  🔄 Rotated to next API key (Prefix: {self.api_key[:10]}...)")
            return self.api_key
        return self.api_key

    @staticmethod
    def compute_chunk_hash(text: str, voice_name: str, profile_name: str) -> str:
        """Computes a short 8-char MD5 hash so cached chunks invalidate automatically when script or voice changes."""
        payload = f"{voice_name}|{profile_name}|{text.strip()}"
        return hashlib.md5(payload.encode("utf-8")).hexdigest()[:8]

    def build_prompt(
        self,
        transcript: str,
        profile: AudioProfile,
        director_note: DirectorNote
    ) -> str:
        """
        Combines the persona, scene notes, and transcript into the unified TTS prompt.
        Extracts any bracketed stage cues (e.g. [rapid fire, sarcastic], [بحماس]) into the
        directorial header so the model performs the emotion without ever reading the brackets aloud.
        """
        instruction = director_note.compile_instruction(profile)
        raw_text = transcript.strip()

        # Extract bracketed stage cues so they guide performance without polluting spoken Arabic text
        cues = [m.strip("[]").strip() for m in re.findall(r'\[[^\[\]\n]{1,70}\]', raw_text) if m.strip("[]").strip()]
        clean_text = re.sub(r'\[[^\[\]\n]{1,70}\]', '', raw_text).strip()
        clean_text = re.sub(r'[ \t]{2,}', ' ', clean_text)

        cue_note = ", ".join(cues) if cues else "rapid fire, punchy, expressive, crisp Arabic letter articulation"

        return (
            f"{instruction}\n\n"
            f"# Section Delivery Cue (Act out this delivery, DO NOT read the cue aloud)\n"
            f"Delivery Mode: [{cue_note}] — Start immediately with a punchy hook, maintain fast Bendia-style conversational momentum, "
            f"color shocking facts and ironic lines with genuine vocal attitude, and pronounce every Arabic letter clearly.\n\n"
            f"# Spoken Arabic Script (Read ONLY the Arabic text below)\n"
            f"{clean_text}"
        )

    def _synthesize_single_chunk(
        self,
        client: Any,
        types: Any,
        full_prompt: str,
        output_wav_path: str,
        voice_name: str,
        temperature: float = 0.75,
        trim_silence: bool = True,
        retries: int = 50
    ) -> Dict[str, Any]:
        """Synthesizes a single chunk with retry capability, silence trimming, and crisp articulation."""
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=full_prompt)],
            ),
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature=temperature,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        )

        last_err = None
        for attempt in range(1, retries + 1):
            try:
                audio_data = bytearray()
                mime_type = "audio/L16;rate=24000"

                for chunk in client.models.generate_content_stream(
                    model=self.model,
                    contents=contents,
                    config=generate_content_config,
                ):
                    if chunk.parts is None:
                        continue
                    for part in chunk.parts:
                        if part.inline_data and part.inline_data.data:
                            inline_data = part.inline_data
                            audio_data.extend(inline_data.data)
                            if inline_data.mime_type:
                                mime_type = inline_data.mime_type
                        elif part.text:
                            pass

                if not audio_data:
                    raise RuntimeError("No audio data was received from the Gemini TTS stream.")

                os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)
                raw_bytes = bytes(audio_data)
                params = parse_audio_mime_type(mime_type)
                sample_rate = params["rate"]
                bits_per_sample = params["bits_per_sample"]
                bytes_per_sample = bits_per_sample // 8

                ext = mimetypes.guess_extension(mime_type)
                if ext == ".wav" and raw_bytes.startswith(b"RIFF"):
                    final_buffer = raw_bytes
                    pcm_payload_len = max(0, len(raw_bytes) - 44)
                else:
                    if trim_silence:
                        raw_bytes = trim_pcm_silence(
                            raw_bytes,
                            sample_rate=sample_rate,
                            bits_per_sample=bits_per_sample
                        )
                    pcm_payload_len = len(raw_bytes)
                    final_buffer = convert_raw_pcm_to_wav(raw_bytes, mime_type)

                with open(output_wav_path, "wb") as f:
                    f.write(final_buffer)

                duration_sec = pcm_payload_len / float(sample_rate * bytes_per_sample)

                return {
                    "output_path": output_wav_path,
                    "duration": round(duration_sec, 2),
                    "sample_rate": sample_rate,
                    "file_size": len(final_buffer),
                    "client": client
                }
            except Exception as e:
                last_err = e
                print(f"    ⚠️ [ليميت / Limit] حدث خطأ أو ليميت في المفتاح الحالي ({e})")
                new_key = self.rotate_key()
                from google import genai
                client = genai.Client(api_key=new_key)
                print(f"    🔄 تم الانتقال إلى API Key آخر ({new_key[:10]}...) والمتابعة مع الموديل ({self.model})...")
                time.sleep(2)

        raise RuntimeError(f"Failed to synthesize chunk after {retries} attempts: {last_err}")

    def generate_segmented_speech(
        self,
        transcript: str,
        output_wav_path: str,
        voice_name: str = "Fenrir",
        profile_key: str = "SAUDI_YOUTH_CREATOR",
        director_note_key: str = "HIGH_ENERGY_YOUTUBE",
        custom_profile: Optional[AudioProfile] = None,
        custom_director_note: Optional[DirectorNote] = None,
        temperature: float = 0.75,
        speed: float = 1.0,
        pause_between_sections: float = 0.14,
        chunks_dir: Optional[str] = None,
        resume: bool = True
    ) -> Dict[str, Any]:
        """
        Synthesizes multi-section scripts by generating each story section as a continuous take,
        trimming dead air, concatenating with a tight 0.14s transition beat, and applying speed.
        """
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError("The 'google-genai' library is required. Please install it via: pip install google-genai")

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please set it in .env or via environment variable.")

        client = genai.Client(api_key=self.api_key)
        profile = custom_profile or AUDIO_PROFILES.get(profile_key, AUDIO_PROFILES["SAUDI_YOUTH_CREATOR"])
        director_note = custom_director_note or DIRECTOR_NOTES.get(director_note_key, DIRECTOR_NOTES["HIGH_ENERGY_YOUTUBE"])

        sections = split_transcript_into_sections(transcript)
        total_sections = len(sections)

        if not chunks_dir:
            chunks_dir = os.path.join(os.path.dirname(os.path.abspath(output_wav_path)), "chunks")
        os.makedirs(chunks_dir, exist_ok=True)

        print(f"\n[VoiceStudio] Starting Multi-Section Fast-Paced Generation (Bendia Mode):")
        print(f"  • Total Sections: {total_sections}")
        print(f"  • Temperature   : {temperature}")
        print(f"  • Target Speed  : {speed}x")
        print(f"  • Section Gap   : {pause_between_sections}s (Zero Dead-Air Trimmed)")
        print(f"  • Voice / Model : {voice_name} / {self.model}")
        print(f"  • Target Output : {output_wav_path}")
        print(f"  • Chunks Cache  : {chunks_dir}\n")

        chunk_files = []
        total_raw_duration = 0.0

        for i, sec in enumerate(sections, 1):
            tag_label = sec["tag"] if sec["tag"] else "[fast_story]"
            clean_tag = re.sub(r'[^a-zA-Z0-9_]', '_', tag_label.strip('[]')).strip('_') or "sec"
            chunk_hash = self.compute_chunk_hash(sec["text"], voice_name, profile.name)
            chunk_name = f"sec_{i:02d}_{clean_tag}_{chunk_hash}.wav"
            chunk_path = os.path.join(chunks_dir, chunk_name)
            chunk_files.append(chunk_path)

            first_snippet = " ".join(re.sub(r'\[.*?\]', '', sec["text"]).replace('\n', ' ').split()[:6])

            # Check content-verified cache
            if resume and os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 2000:
                try:
                    with wave.open(chunk_path, 'rb') as wf:
                        sec_dur = wf.getnframes() / float(wf.getframerate())
                        total_raw_duration += sec_dur
                        print(f"  [{i:02d}/{total_sections:02d}] ⚡ Cached: {tag_label} ({sec['words']} words) -> {sec_dur:.1f}s")
                        continue
                except Exception:
                    pass

            print(f"  [{i:02d}/{total_sections:02d}] 🎙️ Synthesizing: {tag_label} ({sec['words']} words) | \"{first_snippet}...\"")
            full_prompt = self.build_prompt(sec["text"], profile, director_note)
            res = self._synthesize_single_chunk(
                client=client,
                types=types,
                full_prompt=full_prompt,
                output_wav_path=chunk_path,
                voice_name=voice_name,
                temperature=temperature
            )
            client = res.get("client", client)
            sec_dur = res["duration"]
            total_raw_duration += sec_dur
            print(f"         ✅ Done in {sec_dur:.1f}s audio duration.")

        # Concatenate chunks into master audio
        print(f"\n[VoiceStudio] 🔗 Seamlessly concatenating {total_sections} sections with tight {pause_between_sections}s transitions...")
        os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)
        raw_concat_path = output_wav_path + ".raw.wav"

        sample_rate = 24000
        num_channels = 1
        sampwidth = 2
        if chunk_files and os.path.exists(chunk_files[0]):
            try:
                with wave.open(chunk_files[0], 'rb') as first_wf:
                    sample_rate = first_wf.getframerate()
                    num_channels = first_wf.getnchannels()
                    sampwidth = first_wf.getsampwidth()
            except Exception:
                pass

        silence_bytes = b'\x00' * int(sample_rate * num_channels * sampwidth * pause_between_sections)

        with wave.open(raw_concat_path, 'wb') as outfile:
            outfile.setnchannels(num_channels)
            outfile.setsampwidth(sampwidth)
            outfile.setframerate(sample_rate)

            for idx, c_path in enumerate(chunk_files):
                with wave.open(c_path, 'rb') as infile:
                    outfile.writeframes(infile.readframes(infile.getnframes()))
                if idx < len(chunk_files) - 1 and pause_between_sections > 0:
                    outfile.writeframes(silence_bytes)

        # Apply Speed Multiplier via FFmpeg
        final_target_path = output_wav_path
        if abs(speed - 1.0) > 0.01:
            print(f"[VoiceStudio] ⚡ Applying speed multiplier {speed}x via FFmpeg atempo...")
            cmd = ["ffmpeg", "-y", "-i", raw_concat_path, "-af", f"atempo={speed}", final_target_path]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if os.path.exists(raw_concat_path):
                    os.remove(raw_concat_path)
            except Exception as e:
                print(f"  ⚠️ Warning: Speed conversion failed ({e}), using raw concatenation.")
                os.replace(raw_concat_path, final_target_path)
        else:
            os.replace(raw_concat_path, final_target_path)

        # Inspect final master audio
        with wave.open(final_target_path, 'rb') as wf:
            final_frames = wf.getnframes()
            final_rate = wf.getframerate()
            final_duration = final_frames / float(final_rate)
        final_size = os.path.getsize(final_target_path)

        mins = int(final_duration // 60)
        secs = int(final_duration % 60)
        print("=" * 85)
        print("🎉 MASTER VOICEOVER GENERATED SUCCESSFULLY!")
        print(f"  • File Path   : {final_target_path}")
        print(f"  • Duration    : {final_duration:.2f}s (~{mins}m {secs}s)")
        print(f"  • Speed       : {speed}x")
        print(f"  • Sample Rate : {final_rate} Hz (RIFF 16-bit PCM)")
        print(f"  • File Size   : {final_size / (1024*1024):.2f} MB")
        print("=" * 85 + "\n")

        return {
            "status": "SUCCESS",
            "output_path": final_target_path,
            "duration": round(final_duration, 2),
            "sample_rate": final_rate,
            "file_size": final_size,
            "sections_count": total_sections
        }

    def generate_speech(
        self,
        transcript: str,
        output_wav_path: str,
        voice_name: str = "Fenrir",
        profile_key: str = "SAUDI_YOUTH_CREATOR",
        director_note_key: str = "HIGH_ENERGY_YOUTUBE",
        custom_profile: Optional[AudioProfile] = None,
        custom_director_note: Optional[DirectorNote] = None,
        temperature: float = 0.75,
        speed: float = 1.0,
        auto_chunk: bool = True
    ) -> Dict[str, Any]:
        """
        Generates expressive spoken audio from text and saves to a WAV file.
        Automatically uses segmented generation if the transcript contains multiple cues
        or exceeds 175 words.
        """
        sections = split_transcript_into_sections(transcript)
        words_count = len(re.sub(r'\[.*?\]', '', transcript).split())

        if auto_chunk and (len(sections) > 1 or words_count > 75):
            return self.generate_segmented_speech(
                transcript=transcript,
                output_wav_path=output_wav_path,
                voice_name=voice_name,
                profile_key=profile_key,
                director_note_key=director_note_key,
                custom_profile=custom_profile,
                custom_director_note=custom_director_note,
                temperature=temperature,
                speed=speed
            )

        # Single-shot synthesis for single sections (<= 175 words)
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError("The 'google-genai' library is required. Please install it via: pip install google-genai")

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please set it in .env or via environment variable.")

        client = genai.Client(api_key=self.api_key)
        profile = custom_profile or AUDIO_PROFILES.get(profile_key, AUDIO_PROFILES["SAUDI_YOUTH_CREATOR"])
        director_note = custom_director_note or DIRECTOR_NOTES.get(director_note_key, DIRECTOR_NOTES["HIGH_ENERGY_YOUTUBE"])
        full_prompt = self.build_prompt(transcript, profile, director_note)

        res = self._synthesize_single_chunk(
            client=client,
            types=types,
            full_prompt=full_prompt,
            output_wav_path=output_wav_path,
            voice_name=voice_name,
            temperature=temperature
        )

        duration_sec = res["duration"]
        if abs(speed - 1.0) > 0.01:
            temp_path = output_wav_path + ".orig.wav"
            try:
                os.replace(output_wav_path, temp_path)
                cmd = ["ffmpeg", "-y", "-i", temp_path, "-af", f"atempo={speed}", output_wav_path]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                duration_sec /= speed
            except Exception as e:
                print(f"  ⚠️ Warning: Speed adjustment failed ({e}), keeping original speed.")
                if os.path.exists(temp_path):
                    os.replace(temp_path, output_wav_path)

        final_size = os.path.getsize(output_wav_path)
        return {
            "status": "SUCCESS",
            "output_path": output_wav_path,
            "duration": round(duration_sec, 2),
            "sample_rate": res["sample_rate"],
            "file_size": final_size
        }
