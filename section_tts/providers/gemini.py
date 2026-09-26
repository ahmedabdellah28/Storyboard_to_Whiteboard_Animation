import io
import os
import re
import time
import struct
import wave
from typing import Optional, List
from google import genai
from google.genai import types

from .base import TTSProvider, AudioResult
from ..models.voice import VoiceProfile, PerformanceCue
from ..models.chunk import ChunkContext
from ..config import get_gemini_api_keys
from ..utils.logging import log
from ..utils.retry import RetryManager

def pcm_to_wav_bytes(pcm_data: bytes, sample_rate: int = 24000, bits_per_sample: int = 16) -> bytes:
    """Wraps raw linear PCM audio bytes into a valid standard RIFF/WAVE container."""
    num_channels = 1
    data_size = len(pcm_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size
    )
    return header + pcm_data

class GeminiTTSProvider(TTSProvider):
    """Production Gemini TTS Provider supporting model configuration and multi-key rotation."""
    def __init__(
        self,
        model: str = "gemini-2.5-flash-preview-tts",
        voice_name: str = "Fenrir",
        sample_rate: int = 24000,
        api_keys: Optional[List[str]] = None,
        max_retries: int = 8
    ):
        self.model = model
        self.voice_name = voice_name
        self.sample_rate = sample_rate
        self.keys = api_keys or get_gemini_api_keys()
        
        if not self.keys:
            raise ValueError("No GEMINI_API_KEY found in environment or .env file.")
        
        self.clients = [genai.Client(api_key=k) for k in self.keys]
        self.current_key_idx = 0
        self.retry_manager = RetryManager(max_retries=max_retries, initial_delay_sec=1.0)

    def _get_client(self) -> genai.Client:
        return self.clients[self.current_key_idx]

    def _rotate_key(self):
        prev = self.current_key_idx
        self.current_key_idx = (self.current_key_idx + 1) % len(self.clients)
        log.tts(f"Rotating API Key: #{prev + 1} -> #{self.current_key_idx + 1}")

    def build_prompt(
        self,
        text: str,
        voice_profile: VoiceProfile,
        performance: PerformanceCue,
        context: Optional[ChunkContext] = None
    ) -> str:
        """Constructs a prompt strictly instructing the TTS engine on delivery without reciting metadata."""
        prompt_parts = [
            f"AUDIO SCRIPT — GEMINI TTS DELIVERY DIRECTIVE\n",
            voice_profile.system_directive.strip(),
            f"\nSEGMENT DYNAMICS:",
            f"- Segment Type: {performance.segment_type}",
            f"- Delivery Energy: {performance.energy}",
            f"- Pacing: {performance.pace}",
            f"- Emphasis: {performance.emphasis}"
        ]

        if performance.instruction:
            prompt_parts.append(f"- Note: {performance.instruction}")

        if context:
            if context.previous_text:
                prompt_parts.append(f"\n[Acoustic Context - Previous phrase: \"{context.previous_text}\"]")
            if context.next_text:
                prompt_parts.append(f"[Acoustic Context - Next upcoming phrase: \"{context.next_text}\"]")

        prompt_parts.append(
            "\nCRITICAL DIRECTIVE:\n"
            "You are a voice actor. You must voice ONLY the exact Arabic text below.\n"
            "DO NOT read any instructions, bracketed context, or cues.\n"
            "DO NOT add greetings, intros, outros, or omit any words.\n\n"
            "TEXT TO SPEAK EXACTLY:\n"
            f"{text.strip()}"
        )
        return "\n".join(prompt_parts)

    def generate(
        self,
        text: str,
        voice_profile: VoiceProfile,
        performance: PerformanceCue,
        context: Optional[ChunkContext] = None
    ) -> AudioResult:
        """Synthesizes text using Gemini TTS with automatic retry and key rotation."""
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Cannot synthesize empty text.")

        voice_to_use = voice_profile.voice_name or self.voice_name
        full_prompt = self.build_prompt(clean_text, voice_profile, performance, context)

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
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_to_use)
                )
            )
        )

        def _do_generate() -> AudioResult:
            client = self._get_client()
            pcm_buffer = bytearray()
            try:
                stream = client.models.generate_content_stream(
                    model=self.model,
                    contents=contents,
                    config=cfg
                )
                for chunk in stream:
                    if chunk.candidates:
                        for cand in chunk.candidates:
                            if cand.content and cand.content.parts:
                                for part in cand.content.parts:
                                    inline = getattr(part, "inline_data", None)
                                    if inline and inline.data:
                                        pcm_buffer.extend(inline.data)
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    delay_match = re.search(r'retryDelay[\'"]?:\s*[\'"]?([0-9]+)s', err_msg)
                    cooldown = int(delay_match.group(1)) + 2 if delay_match else 20
                    self._rotate_key()
                    log.tts(f"Quota throttle (429): cooling down {cooldown}s before retrying...")
                    time.sleep(cooldown)
                raise e

            if not pcm_buffer:
                raise RuntimeError("Gemini TTS returned empty audio stream.")

            raw_bytes = bytes(pcm_buffer)
            # If the response is already a WAV container, use as-is; otherwise wrap PCM into WAV
            if raw_bytes.startswith(b"RIFF"):
                wav_bytes = raw_bytes
            else:
                wav_bytes = pcm_to_wav_bytes(raw_bytes, sample_rate=self.sample_rate)

            # Compute duration from WAV header
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                dur = wf.getnframes() / float(wf.getframerate())

            return AudioResult(
                audio_bytes=wav_bytes,
                sample_rate=self.sample_rate,
                duration=round(dur, 3),
                format="wav"
            )

        return self.retry_manager.execute(_do_generate, operation_name=f"Gemini TTS ({len(clean_text.split())} words)")
