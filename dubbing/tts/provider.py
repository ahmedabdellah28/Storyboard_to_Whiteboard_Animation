"""
Gemini TTS Provider
===================
Concrete TTS implementation using Google Gemini (gemini-3.1-flash-tts-preview).
Incorporates Voice Studio character personas, directorial styles, and studio acoustics.
"""
from __future__ import annotations

import os
import struct
import time
import wave
from typing import Optional, Dict

from .base import TTSProvider, AudioResult


# Persona and Director Styles matching voice_studio
VOICE_STUDIO_PROFILES: Dict[str, str] = {
    "YOUTH_CREATOR": (
        "Role & Persona: Young YouTube Creator & Documentary Explainer, around 25–30 years old. "
        "Medium male pitch, youthful, energetic, confident and expressive with clean vocal projection. "
        "Conversational and charismatic, with a natural vocal smile. "
        "Records in a clean studio setting with proper mic technique, never sounding breathy, muffled, or like a robotic news anchor."
    ),
    "PROFESSIONAL_EXPLAINER": (
        "Role & Persona: Professional Documentary Explainer, around 30–35 years old. "
        "Warm, articulate, educational tone with clear pronunciation and natural pacing. "
        "Engaging and authoritative without sounding dry or bureaucratic."
    ),
    "NARRATIVE_STORYTELLER": (
        "Role & Persona: Dramatic Storyteller. Deep, immersive narration. "
        "Expressive vocal shifts between suspense, insight, and nuance. Perfect for cinematic documentaries."
    ),
}

VOICE_STUDIO_DIRECTOR_NOTES: Dict[str, str] = {
    "HIGH_ENERGY_YOUTUBE": (
        "Performance Style: Very fast-paced, rapid-fire delivery, punchy consonants, energetic and brisk tempo with clean vocal projection.\n"
        "Scene Context: A high-energy animated YouTube explainer with rapid visuals and non-stop forward motion.\n"
        "Delivery Directives: Speak at a brisk conversational tempo with tight, snappy phrasing. Words flow smoothly and swiftly with drive and momentum."
    ),
    "DYNAMIC_WHITEBOARD_SWEETSPOT": (
        "Performance Style: Energetic, charismatic, natural conversational explainer with crisp rhythm and zero sluggishness.\n"
        "Scene Context: A polished whiteboard documentary animation. Confident, youthful, and engaging.\n"
        "Delivery Directives: Speak at a natural, engaging YouTube explainer tempo (around 125 words per minute). Flow smoothly and dynamically between thoughts."
    ),
    "CALM_EDUCATIONAL": (
        "Performance Style: Clear, measured, pedagogical with precise diction.\n"
        "Scene Context: An educational whiteboard explainer. Step-by-step clarity with smooth vocal cadence."
    ),
}

ACOUSTIC_STUDIO_DIRECTIVES = (
    "Acoustic Environment & Microphone Technique:\n"
    "- Recorded in a professional acoustically treated voiceover booth using a broadcast condenser microphone with pop shield.\n"
    "- Balanced broadcast mastering: crisp, clear presence without heavy bass proximity effect or muffled closeness.\n"
    "- ZERO AUDIBLE BREATHING: Inhalations and breathing must be completely silent and inaudible. Absolutely NO gasping, heavy breath intakes, mouth clicks, or breath puffs.\n"
    "- Clear vocal projection: Project voice with natural studio confidence, avoiding ASMR intimacy or close-mic whisper."
)


class GeminiTTSProvider(TTSProvider):
    """
    Text-to-speech using Google Gemini TTS API with Voice Studio persona styles.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3.1-flash-tts-preview",
        profile: str = "YOUTH_CREATOR",
        director_note: str = "DYNAMIC_WHITEBOARD_SWEETSPOT",
    ):
        self.model = model
        self.profile = profile
        self.director_note = director_note
        self._api_keys: list[str] = []

        if api_key:
            self._api_keys.append(api_key.strip())

        for env_var in ["GEMINI_API_KEY", "GEMINI_API_KEY2", "GEMINI_API_KEY3"]:
            val = os.environ.get(env_var)
            if val and val.strip() not in self._api_keys:
                self._api_keys.append(val.strip())

        # Workspace .env
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        if os.path.isfile(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY") and "=" in line:
                        val = line.split("=", 1)[1].strip("\"' ")
                        if val and val not in self._api_keys:
                            self._api_keys.append(val)

        self._key_idx = 0
        self._client = None

    @property
    def _current_key(self) -> str:
        if not self._api_keys:
            raise RuntimeError("No Gemini API keys configured.")
        return self._api_keys[self._key_idx % len(self._api_keys)]

    def _rotate_key(self) -> str:
        if len(self._api_keys) > 1:
            self._key_idx = (self._key_idx + 1) % len(self._api_keys)
            self._client = None
            print(f"  [TTS] Rotated to next API key ({self._key_idx + 1}/{len(self._api_keys)})")
        return self._current_key

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self._current_key)
        return self._client

    @staticmethod
    def _raw_pcm_to_wav(audio_data: bytes, sample_rate: int = 24000) -> bytes:
        """Wrap raw linear PCM into a valid WAV container."""
        bits = 16
        channels = 1
        block_align = channels * (bits // 8)
        byte_rate = sample_rate * block_align
        data_size = len(audio_data)
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE",
            b"fmt ", 16, 1, channels,
            sample_rate, byte_rate, block_align, bits,
            b"data", data_size,
        )
        return header + audio_data

    def synthesize(
        self,
        text: str,
        language: str,
        voice: str,
        output_path: str,
    ) -> AudioResult:
        """Synthesize speech for a segment using Voice Studio persona and style."""
        from google.genai import types

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        persona_desc = VOICE_STUDIO_PROFILES.get(
            self.profile, VOICE_STUDIO_PROFILES["YOUTH_CREATOR"]
        )
        director_desc = VOICE_STUDIO_DIRECTOR_NOTES.get(
            self.director_note, VOICE_STUDIO_DIRECTOR_NOTES["DYNAMIC_WHITEBOARD_SWEETSPOT"]
        )

        prompt = (
            f"{persona_desc}\n\n"
            f"{director_desc}\n\n"
            f"{ACOUSTIC_STUDIO_DIRECTIVES}\n\n"
            f"Deliver the following {language} line naturally, expressively, and in character with non-stop forward drive:\n\n"
            f"{text}"
        )

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            )
        ]
        config = types.GenerateContentConfig(
            temperature=1.0,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice,
                    )
                )
            ),
        )

        max_retries = max(6, len(self._api_keys) * 2)
        for attempt in range(max_retries):
            try:
                client = self._get_client()
                response = client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )

                # Extract audio data
                audio_data = None
                sample_rate = 24000
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                        audio_data = part.inline_data.data
                        mime = part.inline_data.mime_type
                        if "rate=" in mime:
                            try:
                                sample_rate = int(
                                    mime.split("rate=")[1].split(";")[0]
                                )
                            except (ValueError, IndexError):
                                pass
                        break

                if audio_data is None:
                    raise RuntimeError("Gemini TTS returned no audio data.")

                wav_bytes = self._raw_pcm_to_wav(audio_data, sample_rate)
                with open(output_path, "wb") as f:
                    f.write(wav_bytes)

                with wave.open(output_path, "rb") as wf:
                    duration = wf.getnframes() / float(wf.getframerate())

                return AudioResult(
                    audio_path=output_path,
                    duration=duration,
                    sample_rate=sample_rate,
                )

            except Exception as e:
                err_str = str(e).lower()
                if "quota" in err_str or "429" in err_str or "rate" in err_str:
                    self._rotate_key()
                    wait = 2.0 * (attempt + 1)
                    print(f"  [TTS] Rate limited, rotating key and waiting {wait:.1f}s...")
                    time.sleep(wait)
                    continue

                if attempt < max_retries - 1:
                    print(f"  [TTS] Retry {attempt + 1}: {e}")
                    time.sleep(1.5)
                    continue

                raise
