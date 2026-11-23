"""
Vyond-Style Dramatic Story Narration Section for Voice Studio
-------------------------------------------------------------
Produces dramatic, fast-flowing Cairo Egyptian Arabic stories using a single
consistent female narrator voice (e.g. 'Kore' or 'Aoede') with per-chunk
emotional direction, automatic safe sentence chunking, -42 dBFS silence
trimming, -2 dBFS peak normalization, micro/scene pauses, chunk caching,
and MP3 (192k) or WAV master export.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import wave
from typing import Any, Dict, List, Optional

import core_engine.dns_patch  # noqa: F401 - ensures DNS patch is active when run standalone

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.audio.wav_utils import pcm_to_wav

# Safe UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_VYOND_MODEL = "gemini-3.8-flash-tts"
DEFAULT_FEMALE_VOICE = "Kore"  # Fallback / standard voice
SUPPORTED_FEMALE_VOICES = ("Kore", "Aoede")

BASE_DIRECTOR_PROMPT = (
    "Audio Profile: Native Egyptian female storyteller from Cairo (30 years old) with a warm, sweet, captivating, and deeply expressive voice (صوت عذب ودافئ ومليان حرارة). "
    "Accent Rules: Strictly speak in 100% natural everyday Cairo Egyptian Arabic (Ammiya). "
    "Pronounce all 'Qaf' (ق) in colloquial words as a soft glottal stop (Hamza 'أ'), "
    "pronounce 'Jeem' (ج) as a hard 'G' (like in 'good'), and use natural Egyptian vowel elongation. "
    "Never use Modern Standard Arabic (Fusha) grammar or pronunciation. "
    "Delivery & Emotion: Speak with genuine human warmth, heartfelt passion, and vivid melodic vocal expression—like an Egyptian woman telling a gripping true story to close friends with real fire, empathy, heartbreak, and excitement in her voice. "
    "Pacing: Fast, fluid, continuous conversational flow (~160 WPM) with NO unintended pauses. "
    "Studio Hygiene: Clean, close-mic studio clarity with ZERO audible breathing, ZERO mic inhales, ZERO gasps, and ZERO airy whispers. "
    "STRICT VERBATIM RULE: Read the exact written Arabic words verbatim word-for-word; NEVER add, skip, or substitute any word. "
    "اقرئي النص المكتوب حرفياً كلمة بكلمة بحرارة ودفء وعذوبة، ولا تنطقي التوجيهات الشعورية أبداً، انطقي النص المطلوب فقط:"
)


def split_into_safe_chunks(text: str, max_chars: int = 500) -> List[str]:
    """Split text on sentence boundaries so each chunk stays within max_chars."""
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    sentences = re.split(r"(?<=[.!؟…])\s+", normalized)
    chunks: List[str] = []
    current_chunk = ""
    for sentence in sentences:
        if not sentence:
            continue
        candidate = f"{current_chunk} {sentence}" if current_chunk else sentence
        if len(candidate) <= max_chars:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks


def normalize_pcm(pcm_bytes: bytes, headroom_db: float = 2.0) -> bytes:
    """Peak-normalize 16-bit signed little-endian PCM to -headroom_db dBFS."""
    num_samples = len(pcm_bytes) // 2
    if num_samples == 0:
        return pcm_bytes

    samples = struct.unpack(f"<{num_samples}h", pcm_bytes[: num_samples * 2])
    peak = max((abs(s) for s in samples), default=0)
    if peak == 0:
        return pcm_bytes[: num_samples * 2]

    target_peak = 32767.0 * (10.0 ** (-headroom_db / 20.0))
    gain = target_peak / float(peak)
    if abs(gain - 1.0) < 1e-3:
        return pcm_bytes[: num_samples * 2]

    scaled = [max(-32768, min(32767, int(round(s * gain)))) for s in samples]
    return struct.pack(f"<{num_samples}h", *scaled)


def clean_pcm_audio(
    pcm_bytes: bytes,
    sample_rate: int = 24000,
    silence_thresh_db: float = -38.0,
    headroom_db: float = 2.0,
) -> bytes:
    """Trim leading/trailing silence below silence_thresh_db and peak-normalize."""
    num_samples = len(pcm_bytes) // 2
    if num_samples == 0:
        return pcm_bytes

    samples = struct.unpack(f"<{num_samples}h", pcm_bytes[: num_samples * 2])
    threshold = int(round(32767.0 * (10.0 ** (silence_thresh_db / 20.0))))

    first_idx = 0
    for idx, val in enumerate(samples):
        if abs(val) > threshold:
            first_idx = idx
            break
    else:
        return b""

    last_idx = num_samples - 1
    for idx in range(num_samples - 1, -1, -1):
        if abs(samples[idx]) > threshold:
            last_idx = idx
            break

    trimmed = pcm_bytes[first_idx * 2 : (last_idx + 1) * 2]
    return normalize_pcm(trimmed, headroom_db=headroom_db)


def _extract_pcm_from_audio_bytes(raw_bytes: bytes) -> tuple[bytes, int]:
    """Return (pcm_16bit_bytes, sample_rate) from raw PCM or RIFF WAV bytes."""
    if len(raw_bytes) >= 44 and raw_bytes[:4] == b"RIFF" and raw_bytes[8:12] == b"WAVE":
        import io

        with wave.open(io.BytesIO(raw_bytes), "rb") as wf:
            return wf.readframes(wf.getnframes()), wf.getframerate()
    return raw_bytes, 24000


def parse_story_script(raw_text: str) -> List[Dict[str, Any]]:
    """
    Parse a dramatic story script from either:
    1) JSON list of blocks: [{"emotion": "...", "text": "...", "scene_break": false}]
    2) Tagged text blocks separated by '---' or blank lines, with optional
       [المشاعر: ...] / [emotion: ...] and [scene_break] markers.
    """
    stripped = raw_text.strip()
    if not stripped:
        return []

    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict) and "story_chunks" in data:
                data = data["story_chunks"]
            if isinstance(data, list):
                blocks: List[Dict[str, Any]] = []
                for item in data:
                    if isinstance(item, dict) and str(item.get("text", "")).strip():
                        blocks.append(
                            {
                                "emotion": str(item.get("emotion", "أداء درامي طبيعي متدفق")).strip(),
                                "text": str(item["text"]).strip(),
                                "scene_break": bool(item.get("scene_break", False)),
                            }
                        )
                if blocks:
                    return blocks
        except json.JSONDecodeError:
            pass

    emotion_pattern = re.compile(r"^\[(?:المشاعر|emotion)\s*:\s*(.+?)\]$", re.IGNORECASE)
    generic_tag_pattern = re.compile(r"^\[([^\[\]\n]{2,120})\]$")

    # If the script uses [emotion] tags, group paragraphs under each [emotion] tag
    # instead of splitting on every blank line (which fragments narration and dialogue).
    has_emotion_tags = any(
        (emotion_pattern.match(ln.strip()) or generic_tag_pattern.match(ln.strip()))
        and not re.fullmatch(r"\[scene_break\]", ln.strip(), re.IGNORECASE)
        for ln in stripped.splitlines()
    )

    if has_emotion_tags and not re.search(r"\n\s*---+\s*\n", stripped):
        parsed: List[Dict[str, Any]] = []
        current_emotion = "أداء درامي مصري سريع ومشحون بالعاطفة"
        current_lines: List[str] = []
        current_scene_break = False

        for raw_ln in stripped.splitlines():
            ln = raw_ln.strip()
            if not ln:
                continue
            if re.fullmatch(r"\[scene_break\]", ln, re.IGNORECASE):
                current_scene_break = True
                continue
            m = emotion_pattern.match(ln) or generic_tag_pattern.match(ln)
            if m:
                if current_lines:
                    spoken = " ".join(current_lines).strip()
                    if spoken:
                        parsed.append(
                            {
                                "emotion": current_emotion,
                                "text": spoken,
                                "scene_break": current_scene_break,
                            }
                        )
                    current_lines = []
                    current_scene_break = False
                tag_body = m.group(1).strip()
                if "| scene_break" in tag_body.lower():
                    current_scene_break = True
                    tag_body = re.sub(r"\|\s*scene_break", "", tag_body, flags=re.IGNORECASE).strip()
                if tag_body:
                    current_emotion = tag_body
                continue
            if "[scene_break]" in ln.lower():
                current_scene_break = True
                ln = re.sub(r"\[scene_break\]", "", ln, flags=re.IGNORECASE).strip()
            ln = re.sub(r"^[—\-–]\s*", "", ln).strip()
            if ln:
                current_lines.append(ln)

        if current_lines:
            spoken = " ".join(current_lines).strip()
            if spoken:
                parsed.append(
                    {
                        "emotion": current_emotion,
                        "text": spoken,
                        "scene_break": current_scene_break,
                    }
                )
        return parsed

    raw_blocks = re.split(r"\n\s*---+\s*\n|\n\s*\n+", stripped)
    parsed = []
    current_emotion = "أداء درامي مصري سريع ومشحون بالعاطفة"

    for block in raw_blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        emotion = current_emotion
        scene_break = False
        text_lines: List[str] = []

        for ln in lines:
            if re.fullmatch(r"\[scene_break\]", ln, re.IGNORECASE):
                scene_break = True
                continue
            m = emotion_pattern.match(ln) or generic_tag_pattern.match(ln)
            if m:
                tag_body = m.group(1).strip()
                if "| scene_break" in tag_body.lower():
                    scene_break = True
                    tag_body = re.sub(r"\|\s*scene_break", "", tag_body, flags=re.IGNORECASE).strip()
                if tag_body:
                    emotion = tag_body
                    current_emotion = tag_body
                continue
            if "[scene_break]" in ln.lower():
                scene_break = True
                ln = re.sub(r"\[scene_break\]", "", ln, flags=re.IGNORECASE).strip()
            if ln:
                text_lines.append(ln)

        spoken = " ".join(text_lines).strip()
        if spoken:
            parsed.append(
                {
                    "emotion": emotion,
                    "text": spoken,
                    "scene_break": scene_break,
                }
            )

    return parsed


class VyondStoryEngine:
    """
    Vyond-style single-female-narrator dramatic story TTS engine.
    Integrates with VoiceStudioEngine's multi-key pool and rotation.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_VYOND_MODEL,
        voice_name: str = DEFAULT_FEMALE_VOICE,
        director_prompt: str = BASE_DIRECTOR_PROMPT,
        temperature: float = 0.85,
    ):
        from core.config.env_loader import get_gemini_api_keys

        self.api_keys: List[str] = []
        if api_key and api_key.strip() not in ("", "YOUR_GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE"):
            self.api_keys.append(api_key.strip())

        for key in get_gemini_api_keys():
            if key not in self.api_keys:
                self.api_keys.append(key)

        self.api_key: Optional[str] = self.api_keys[0] if self.api_keys else None
        self.model = model
        self.voice_name = voice_name
        self.director_prompt = director_prompt
        self.temperature = temperature
        self._designed_voice_id: Optional[str] = None

    def get_or_create_egyptian_narrator_voice(
        self,
        client: Any = None,
        voice_id_cache: Optional[str] = None,
    ) -> str:
        """
        Return a cached/created Voice Design ID for Cairo Egyptian Arabic (ar-EG)
        if supported by the installed google-genai SDK; otherwise fall back to
        the configured prebuilt voice (default: 'Kore').
        """
        if self._designed_voice_id:
            return self._designed_voice_id

        cache_file = voice_id_cache or os.path.join(
            ROOT_DIR, "project_content", "audio", "egyptian_narrator_voice_id.txt"
        )
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_id = f.read().strip()
                if cached_id:
                    self._designed_voice_id = cached_id
                    return cached_id

        voices_api = getattr(client, "voices", None) if client is not None else None
        if voices_api is not None and hasattr(voices_api, "create"):
            try:
                designed_voice = voices_api.create(
                    voice_type="VOICE_TYPE_PROMPTED",
                    description=(
                        "A 30-year-old native Egyptian woman from Cairo, warm, expressive, "
                        "authentic Cairene Egyptian Arabic (ar-EG) storyteller. Natural colloquial pronunciation "
                        "with soft glottal stop for Qaf and hard Egyptian G for Jeem. Fast, engaging conversational flow."
                    ),
                    sample_text="أهلاً بيكم يا جماعة، النهاردة هحكيلكم حكاية حقيقية حصلت قدام عيني ومش هتصدقوا اللي حصل فيها!",
                    store=True,
                )
                os.makedirs(os.path.dirname(os.path.abspath(cache_file)), exist_ok=True)
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(designed_voice.id)
                self._designed_voice_id = designed_voice.id
                return designed_voice.id
            except Exception as err:
                print(f"[ملاحظة] تعذر استخدام Voice Design ({err})، سيتم استخدام {self.voice_name} مع توجيه ar-EG.")

        self._designed_voice_id = self.voice_name
        return self.voice_name

    def rotate_key(self) -> Optional[str]:
        """Rotate to the next available Gemini API key in the pool."""
        if len(self.api_keys) > 1:
            curr = self.api_keys.pop(0)
            self.api_keys.append(curr)
            self.api_key = self.api_keys[0]
        return self.api_key

    def build_chunk_prompt(self, emotion: str, spoken_text: str) -> str:
        """Build the exact Vyond-style Egyptian storyteller prompt for a chunk."""
        clean_emotion = emotion
        # Prevent Gemini TTS from producing breathy mic inhales when "whisper" or "holding breath" appears
        clean_emotion = re.sub(r"بهمس|همس", "بصوت دافئ عذب ومتأثر بدون نفس", clean_emotion)
        clean_emotion = re.sub(r"وحبس أنفاس|حبس أنفاس", "وترقب مشحون بالعاطفة", clean_emotion)
        # Convert mid-sentence ellipses (.. / ...) into commas so TTS doesn't insert long unintended pauses
        fluent_text = re.sub(r"\s*\.{2,}\s*", "، ", spoken_text).strip()
        fluent_text = re.sub(r"\s*…\s*", "، ", fluent_text).strip()
        return (
            f"Style: 30yo Cairo Egyptian woman (100% natural ar-EG Ammiya, soft glottal Qaf, hard Egyptian G), "
            f"warm, passionate, fast fluent storytelling (~160 WPM), clean studio mic with zero breathing; "
            f"emotion: {clean_emotion}.\n"
            f"Transcript:\n{fluent_text}"
        )

    def _compute_chunk_hash(self, emotion: str, spoken_text: str) -> str:
        payload = (
            f"{self.model}|{self.voice_name}|{self.temperature}|"
            f"{self.director_prompt}|{emotion.strip()}|{spoken_text.strip()}"
        )
        return hashlib.md5(payload.encode("utf-8")).hexdigest()[:10]

    def generate_narrator_chunk(
        self,
        emotion: str,
        spoken_text: str,
        retries: int = 4,
        client: Any = None,
    ) -> tuple[bytes, int]:
        """Synthesize and clean a single dramatic chunk, returning (pcm_bytes, sample_rate)."""
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ImportError(
                "The 'google-genai' library is required. Install via: pip install google-genai"
            ) from exc

        if not self.api_key and client is None:
            raise ValueError("GEMINI_API_KEY is not set. Please set it in .env or via --api-key.")

        active_client = client or genai.Client(api_key=self.api_key)
        voice_id = self.get_or_create_egyptian_narrator_voice(active_client)
        speech_metadata_cls = getattr(types, "SpeechMetadata", None)
        use_speech_metadata = (
            speech_metadata_cls is not None
            and "voice" in getattr(types.VoiceConfig, "model_fields", {})
        )

        if use_speech_metadata and speech_metadata_cls is not None:
            clean_emotion = re.sub(r"بهمس|همس", "بصوت دافئ عذب ومتأثر بدون نفس", emotion)
            clean_emotion = re.sub(r"وحبس أنفاس|حبس أنفاس", "وترقب مشحون بالعاطفة", clean_emotion)
            fluent_text = re.sub(r"\s*\.{2,}\s*", "، ", spoken_text).strip()
            fluent_text = re.sub(r"\s*…\s*", "، ", fluent_text).strip()
            style_directive = (
                f"Native Cairo Egyptian Arabic (ar-EG) accent, fast-paced conversational storytelling, "
                f"warm emotional acting tone: {clean_emotion}"
            )
            part_kwargs: dict[str, Any] = {
                "text": fluent_text,
                "speech_metadata": speech_metadata_cls(style=style_directive),
            }
            voice_cfg_kwargs: dict[str, Any] = {"voice": voice_id}
            contents: Any = [
                types.Content(
                    role="user",
                    parts=[types.Part(**part_kwargs)],
                )
            ]
            speech_cfg = types.SpeechConfig(voice_config=types.VoiceConfig(**voice_cfg_kwargs))
        else:
            fluent_text = re.sub(r"\s*\.{2,}\s*", "، ", spoken_text).strip()
            fluent_text = re.sub(r"\s*…\s*", "، ", fluent_text).strip()
            contents = self.build_chunk_prompt(emotion, spoken_text)
            speech_cfg = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice_name
                    )
                )
            )

        last_err: Optional[Exception] = None

        for attempt in range(retries):
            try:
                response = active_client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=self.temperature,
                        response_modalities=["AUDIO"],
                        speech_config=speech_cfg,
                    ),
                )
                raw_audio = response.candidates[0].content.parts[0].inline_data.data
                pcm_bytes, sample_rate = _extract_pcm_from_audio_bytes(raw_audio)
                cleaned_pcm = clean_pcm_audio(pcm_bytes, sample_rate=sample_rate)
                dur_sec = len(cleaned_pcm) / float(sample_rate * 2)
                chars_per_sec = len(fluent_text) / max(dur_sec, 0.1)
                if len(fluent_text) >= 60 and chars_per_sec < 7.5:
                    raise RuntimeError(
                        f"Abnormal TTS duration ({dur_sec:.1f}s for {len(fluent_text)} chars, "
                        f"{chars_per_sec:.1f} ch/s) indicating prompt leak or repetition"
                    )
                return cleaned_pcm, sample_rate
            except Exception as err:
                last_err = err
                wait_time = (2 ** attempt) + 2
                print(f"خطأ في المحاولة {attempt + 1}: {err} - انتظار {wait_time} ث...")
                if len(self.api_keys) > 1:
                    new_key = self.rotate_key()
                    active_client = genai.Client(api_key=new_key)
                if attempt < retries - 1:
                    time.sleep(wait_time)

        raise RuntimeError(f"فشل توليد المقطع الصوتي: {last_err}")

    def render_full_story(
        self,
        story_chunks: List[Dict[str, Any]],
        output_file: str = "full_story_kore.mp3",
        max_chars: int = 900,
        micro_pause_ms: int = 0,
        scene_pause_ms: int = 280,
        delay_between_chunks: float = 1.2,
        speed: float = 1.12,
        clean_mic: bool = True,
        bitrate: str = "192k",
        chunks_dir: Optional[str] = None,
        resume: bool = True,
        client: Any = None,
    ) -> Dict[str, Any]:
        """
        Render a full Vyond-style dramatic story from structured chunks and export
        to MP3 (via ffmpeg) or WAV.
        """
        if not story_chunks:
            raise ValueError("story_chunks cannot be empty.")

        abs_output = os.path.abspath(output_file)
        os.makedirs(os.path.dirname(abs_output), exist_ok=True)
        cache_dir = chunks_dir or os.path.join(os.path.dirname(abs_output), "vyond_chunks")
        if resume:
            os.makedirs(cache_dir, exist_ok=True)

        master_pcm = bytearray()
        sample_rate = 24000
        total_sub_chunks = 0

        for idx, block in enumerate(story_chunks, 1):
            emotion = str(block.get("emotion", "أداء درامي طبيعي متدفق")).strip()
            text = str(block.get("text", "")).strip()
            if not text:
                continue

            sub_texts = split_into_safe_chunks(text, max_chars=max_chars)
            for sub_idx, sub_t in enumerate(sub_texts, 1):
                total_sub_chunks += 1
                chunk_hash = self._compute_chunk_hash(emotion, sub_t)
                cache_path = os.path.join(cache_dir, f"vyond_{idx:03d}_{sub_idx:02d}_{chunk_hash}.wav")

                if resume and os.path.exists(cache_path) and os.path.getsize(cache_path) > 44:
                    with wave.open(cache_path, "rb") as wf:
                        sample_rate = wf.getframerate()
                        chunk_pcm = wf.readframes(wf.getnframes())
                    print(f"⚡ [مخزن مؤقت] الجزء {idx}.{sub_idx} | المشاعر: {emotion}")
                else:
                    print(f"جاري توليد الجزء {idx}.{sub_idx} | المشاعر: {emotion}...")
                    chunk_pcm, sample_rate = self.generate_narrator_chunk(
                        emotion=emotion,
                        spoken_text=sub_t,
                        client=client,
                    )
                    if resume and chunk_pcm:
                        with open(cache_path, "wb") as cf:
                            cf.write(pcm_to_wav(chunk_pcm, sample_rate=sample_rate))
                    if delay_between_chunks > 0:
                        time.sleep(delay_between_chunks)

                master_pcm.extend(chunk_pcm)
                if micro_pause_ms > 0:
                    micro_silence = b"\x00" * (int(sample_rate * (micro_pause_ms / 1000.0)) * 2)
                    master_pcm.extend(micro_silence)

            if block.get("scene_break", False) and scene_pause_ms > 0:
                scene_silence = b"\x00" * (int(sample_rate * (scene_pause_ms / 1000.0)) * 2)
                master_pcm.extend(scene_silence)

        wav_bytes = pcm_to_wav(bytes(master_pcm), sample_rate=sample_rate)
        duration_sec = len(master_pcm) / float(sample_rate * 2)

        af_filters: List[str] = []
        if clean_mic:
            af_filters.append("highpass=f=85")
        if abs(speed - 1.0) > 0.01:
            af_filters.append(f"atempo={speed}")
            duration_sec /= speed

        is_wav = abs_output.lower().endswith(".wav")
        if is_wav and not af_filters:
            with open(abs_output, "wb") as f:
                f.write(wav_bytes)
        else:
            temp_wav = abs_output + ".tmp.wav"
            with open(temp_wav, "wb") as f:
                f.write(wav_bytes)
            ffmpeg_bin = shutil.which("ffmpeg")
            if not ffmpeg_bin:
                if is_wav:
                    os.replace(temp_wav, abs_output)
                else:
                    raise RuntimeError("ffmpeg is required to export MP3 files, but was not found on PATH.")
            else:
                try:
                    cmd = [ffmpeg_bin, "-y", "-i", temp_wav]
                    if af_filters:
                        cmd.extend(["-af", ",".join(af_filters)])
                    if not is_wav:
                        cmd.extend(["-codec:a", "libmp3lame", "-b:a", bitrate])
                    cmd.append(abs_output)
                    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if proc.returncode != 0:
                        raise RuntimeError(f"FFmpeg audio export failed: {proc.stderr}")
                finally:
                    if os.path.exists(temp_wav):
                        os.remove(temp_wav)

        print(f"تم إخراج القصة بصوت الراوية بنجاح: {abs_output}")
        return {
            "status": "SUCCESS",
            "output_path": abs_output,
            "duration": round(duration_sec, 2),
            "sample_rate": sample_rate,
            "blocks_count": len(story_chunks),
            "chunks_count": total_sub_chunks,
            "voice": self.voice_name,
            "model": self.model,
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Voice Studio — Vyond-Style Dramatic Story Narrator (Egyptian Arabic)"
    )
    parser.add_argument("--story-file", type=str, required=True, help="Path to .json or .txt story script")
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join(ROOT_DIR, "project_content", "audio", "full_story_kore.mp3"),
        help="Output audio file (.mp3 or .wav)",
    )
    parser.add_argument("--voice", type=str, default=DEFAULT_FEMALE_VOICE, help="Single female voice (e.g. Kore, Aoede)")
    parser.add_argument("--model", type=str, default=DEFAULT_VYOND_MODEL, help="Gemini TTS model")
    parser.add_argument("--max-chars", type=int, default=900, help="Max characters per TTS chunk (default: 900)")
    parser.add_argument("--micro-pause", type=int, default=0, help="Pause between chunks in ms (default: 0)")
    parser.add_argument("--scene-pause", type=int, default=280, help="Extra pause on scene_break in ms (default: 280)")
    parser.add_argument("--delay", type=float, default=1.2, help="Delay between API calls in seconds")
    parser.add_argument("--speed", type=float, default=1.12, help="Playback speed multiplier (default: 1.12)")
    parser.add_argument("--temperature", type=float, default=0.85, help="Sampling temperature (default: 0.85)")
    parser.add_argument("--bitrate", type=str, default="192k", help="MP3 export bitrate (default: 192k)")
    parser.add_argument("--no-clean-mic", action="store_true", help="Disable highpass + breath gate filtering")
    parser.add_argument("--no-resume", action="store_true", help="Disable chunk caching/resume")
    parser.add_argument("--api-key", type=str, default=None, help="Optional Gemini API Key")

    args = parser.parse_args()

    if not os.path.exists(args.story_file):
        print(f"❌ ملف القصة غير موجود: {args.story_file}")
        sys.exit(1)

    with open(args.story_file, "r", encoding="utf-8") as f:
        raw_story = f.read()

    story_chunks = parse_story_script(raw_story)
    if not story_chunks:
        print("❌ لم يتم العثور على مقاطع صالحة في ملف القصة.")
        sys.exit(1)

    engine = VyondStoryEngine(
        api_key=args.api_key,
        model=args.model,
        voice_name=args.voice,
        temperature=args.temperature,
    )
    if not engine.api_key:
        print("⚠️ لم يتم العثور على مفتاح GEMINI_API_KEY في البيئة أو ملف .env")
        sys.exit(1)

    res = engine.render_full_story(
        story_chunks=story_chunks,
        output_file=args.output,
        max_chars=args.max_chars,
        micro_pause_ms=args.micro_pause,
        scene_pause_ms=args.scene_pause,
        delay_between_chunks=args.delay,
        speed=args.speed,
        clean_mic=not args.no_clean_mic,
        bitrate=args.bitrate,
        resume=not args.no_resume,
    )
    print(f"⏱️ المدة الإجمالية: {res['duration']} ثانية | المقاطع: {res['chunks_count']}")


if __name__ == "__main__":
    main()

