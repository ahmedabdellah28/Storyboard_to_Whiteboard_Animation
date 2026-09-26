"""
Gemini GenAI Text-to-Speech (TTS) Engine
Generates expressive, natural Arabic voiceovers synchronized for whiteboard animation using Google GenAI SDK.
"""
import os
import sys
import re
import struct
import mimetypes
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Safe UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


@dataclass
class AudioProfile:
    name: str
    description: str


@dataclass
class DirectorNote:
    style: str
    scene: str
    sample_context: str


# Preconfigured Voice Personas
AUDIO_PROFILES = {
    "SAUDI_YOUTH_CREATOR": AudioProfile(
        name="Young Saudi YouTube Creator",
        description=(
            "Young Saudi male YouTube creator, around 25–30 years old. "
            "Natural modern Saudi Arabic accent, clearly Saudi but easy to understand across the Arab world. "
            "Medium male pitch, youthful, energetic, confident and expressive. "
            "Conversational and charismatic, with a natural vocal smile. "
            "He sounds spontaneous and authentic, never like a news anchor, documentary narrator, "
            "audiobook reader, or commercial announcer."
        )
    ),
    "PROFESSIONAL_EXPLAINER": AudioProfile(
        name="Professional Arabic Explainer",
        description=(
            "Professional, clear, modern Arabic male speaker, around 30–35 years old. "
            "Warm, articulate, educational tone with clear pronunciation and natural pacing. "
            "Engaging and authoritative without sounding dry or bureaucratic."
        )
    ),
    "NARRATIVE_STORYTELLER": AudioProfile(
        name="Dramatic Storyteller",
        description=(
            "Deep, immersive Arabic storyteller. Expressive vocal shifts between suspense, "
            "insight, and humor. Perfect for cinematic case studies and historical retrospectives."
        )
    )
}

DIRECTOR_NOTES = {
    "HIGH_ENERGY_YOUTUBE": DirectorNote(
        style="High energy, punchy consonants, elongated vowels on excitement words.",
        scene=(
            "A fast-paced animated YouTube explainer for a young Arabic-speaking audience. "
            "Rapid visuals, frequent visual changes, quick jokes, surprising facts and constant forward motion. "
            "The narrator is speaking directly to the viewer in an energetic, natural and conversational way, "
            "as if explaining something fascinating to a friend. "
            "The scene is youthful, clever, entertaining and highly engaging. "
            "The narration should feel tightly synchronized with fast animation and should almost never stop."
        ),
        sample_context=(
            "This is a fast Saudi YouTube explainer, not a documentary. "
            "The speaker talks continuously at a very fast conversational pace with a natural bouncing cadence. "
            "Words and phrases flow smoothly into each other. Use extremely short micro-pauses only for natural breathing or brief emphasis. "
            "Keep the speech moving forward at all times. No dead air. No long pauses. No dramatic silence. "
            "The energy comes from rhythm, pitch variation, emphasis and conversational excitement rather than shouting. "
            "The Saudi accent should sound natural, modern and authentic, not exaggerated. "
            "The speaker sounds like he is spontaneously telling the viewer something fascinating and cannot wait to get to the next point."
        )
    ),
    "CALM_EDUCATIONAL": DirectorNote(
        style="Clear, measured, pedagogical with precise diction.",
        scene="An intuitive educational whiteboard explainer. Step-by-step clarity with smooth vocal cadence.",
        sample_context="Balanced pacing allowing concepts to settle while maintaining strong viewer engagement."
    )
}


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
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
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
    return header + audio_data


class GeminiTTSEngine:
    """
    Production Text-to-Speech Engine using Google GenAI SDK and Gemini TTS Preview models.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.1-flash-tts-preview"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key or self.api_key.strip() == "YOUR_GEMINI_API_KEY_HERE":
            # Check local .env in workspace root
            root_candidates = [
                os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"),
                os.path.join(os.getcwd(), ".env")
            ]
            for env_path in root_candidates:
                if os.path.exists(env_path):
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            clean_line = line.strip()
                            if clean_line.startswith("GEMINI_API_KEY="):
                                val = clean_line.split("=", 1)[1].strip('"\' ')
                                if val and val != "YOUR_GEMINI_API_KEY_HERE":
                                    self.api_key = val
                                    break
                if self.api_key:
                    break

        if self.api_key == "YOUR_GEMINI_API_KEY_HERE":
            self.api_key = None

        self.model = model

    def build_prompt(
        self,
        transcript: str,
        profile: AudioProfile,
        director_note: DirectorNote
    ) -> str:
        """Constructs the prompt embedding the persona, scene notes, and transcript."""
        return f"""Read the following transcript based on the audio profile and director's note.

# Audio Profile
{profile.description}

# Director's note
Style: {director_note.style}

## Scene:
{director_note.scene}

## Sample Context:
{director_note.sample_context}

## Transcript:
[emphasis]

{transcript.strip()}"""

    def generate_speech(
        self,
        transcript: str,
        output_wav_path: str,
        voice_name: str = "Fenrir",
        profile_key: str = "SAUDI_YOUTH_CREATOR",
        director_note_key: str = "HIGH_ENERGY_YOUTUBE",
        custom_profile: Optional[AudioProfile] = None,
        custom_director_note: Optional[DirectorNote] = None,
        temperature: float = 1.0
    ) -> Dict[str, Any]:
        """
        Generates expressive spoken audio from text and saves to a WAV file.
        """
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError(
                "The 'google-genai' library is required. Please install it via: pip install google-genai"
            )

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please set the environment variable GEMINI_API_KEY."
            )

        client = genai.Client(api_key=self.api_key)

        profile = custom_profile or AUDIO_PROFILES.get(profile_key, AUDIO_PROFILES["SAUDI_YOUTH_CREATOR"])
        director_note = custom_director_note or DIRECTOR_NOTES.get(director_note_key, DIRECTOR_NOTES["HIGH_ENERGY_YOUTUBE"])

        full_prompt = self.build_prompt(transcript, profile, director_note)

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

        print(f"\n[GeminiTTSEngine] Initiating streaming TTS generation...")
        print(f"  • Model      : {self.model}")
        print(f"  • Voice Name : {voice_name}")
        print(f"  • Persona    : {profile.name}")
        print(f"  • Output Path: {output_wav_path}")

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
                    print(f"  [TTS Model Log] {part.text}")

        if not audio_data:
            raise RuntimeError("No audio data was received from the Gemini TTS stream.")

        # Convert to standard WAV
        os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)
        raw_bytes = bytes(audio_data)

        ext = mimetypes.guess_extension(mime_type)
        if ext == ".wav" and raw_bytes.startswith(b"RIFF"):
            final_buffer = raw_bytes
        else:
            final_buffer = convert_raw_pcm_to_wav(raw_bytes, mime_type)

        with open(output_wav_path, "wb") as f:
            f.write(final_buffer)

        # Inspect resulting audio parameters
        params = parse_audio_mime_type(mime_type)
        sample_rate = params["rate"]
        bytes_per_sample = params["bits_per_sample"] // 8
        duration_sec = len(audio_data) / float(sample_rate * bytes_per_sample)

        print(f"✅ Voiceover successfully saved to: {output_wav_path}")
        print(f"  • Duration    : {duration_sec:.2f}s")
        print(f"  • Sample Rate : {sample_rate} Hz")
        print(f"  • Total Bytes : {len(final_buffer):,} bytes\n")

        return {
            "status": "SUCCESS",
            "output_path": output_wav_path,
            "duration": round(duration_sec, 2),
            "sample_rate": sample_rate,
            "file_size": len(final_buffer)
        }
