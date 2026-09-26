"""
Voice Studio Profiles & Director Notes
Customizable voice personas and directorial scene notes for Gemini GenAI TTS.
"""
from dataclasses import dataclass


@dataclass
class AudioProfile:
    name: str
    description: str


@dataclass
class DirectorNote:
    style: str
    scene: str
    sample_context: str

    def compile_instruction(self, profile: AudioProfile) -> str:
        """Combines voice persona and director notes into a unified system instruction."""
        return (
            f"Role & Persona: {profile.name}. {profile.description}\n\n"
            f"Performance Style: {self.style}\n"
            f"Scene Context: {self.scene}\n"
            f"Delivery Directives: {self.sample_context}\n\n"
            "Acoustic Environment & Microphone Technique:\n"
            "- Recorded in a professional acoustically treated voiceover booth using a broadcast condenser microphone with pop shield at a standard studio distance (20 cm).\n"
            "- Balanced broadcast mastering: crisp, clear presence without heavy bass proximity effect or muffled closeness.\n"
            "- ZERO AUDIBLE BREATHING: Inhalations and breathing must be completely silent and inaudible. Absolutely NO gasping, heavy breath intakes, mouth clicks, or breath puffs hitting the microphone.\n"
            "- Clear vocal projection: Project voice with natural studio confidence, avoiding ASMR intimacy or close-mic whisper.\n\n"
            "Dialect & Acting Rules:\n"
            "1. Maintain authentic modern spoken Saudi Arabic (Urban conversational style).\n"
            "2. Pronounce all unvocalized words using contemporary everyday Saudi dialect, avoiding classical Arabic inflections (I'rab) entirely.\n"
            "3. Enact performance cues in square brackets (e.g. [emphasis], [laugh], [sigh], [ضحكة خفيفة]) purely as vocal expressions and acting inflections. NEVER pronounce or read the bracketed text itself out loud."
        )


# Preconfigured Voice Personas
AUDIO_PROFILES = {
    "SAUDI_YOUTH_CREATOR": AudioProfile(
        name="Young Saudi YouTube Creator",
        description=(
            "Young Saudi male YouTube creator, around 25–30 years old. "
            "Natural modern Saudi Arabic accent, clearly Saudi but easy to understand across the Arab world. "
            "Medium male pitch, youthful, energetic, confident and expressive with clean vocal projection. "
            "Conversational and charismatic, with a natural vocal smile. "
            "He records in a clean studio setting with proper mic technique, never sounding breathy, muffled, or like a news anchor."
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
        style="Very fast-paced, rapid-fire delivery, punchy consonants, energetic and brisk tempo with clean vocal projection.",
        scene=(
            "A fast-paced animated YouTube explainer for a young Arabic-speaking audience. "
            "Rapid visuals, frequent visual changes, and non-stop forward motion. "
            "The narrator is delivering the lines rapidly and energetically with tight rhythm and high enthusiasm, "
            "keeping the viewer hooked every millisecond without any slow delivery."
        ),
        sample_context=(
            "This is a fast-paced Saudi YouTube explainer. The speaker delivers at a rapid-fire, brisk conversational pace "
            "(around 1.25x fast tempo) with tight, snappy transitions between sentences. "
            "Eliminate pauses between lines; transition immediately to the next phrase. "
            "Words flow smoothly and swiftly into each other without dragging or lingering on syllables. "
            "The speech moves forward rapidly with non-stop drive and momentum. "
            "The microphone distance is comfortable and clean, with zero audible breaths."
        )
    ),
    "CALM_EDUCATIONAL": DirectorNote(
        style="Clear, measured, pedagogical with precise diction.",
        scene="An intuitive educational whiteboard explainer. Step-by-step clarity with smooth vocal cadence.",
        sample_context="Balanced pacing allowing concepts to settle while maintaining strong viewer engagement."
    ),
    "WHITEBOARD_PACED": DirectorNote(
        style="Relaxed, deliberate, educational pacing with crisp clarity and warm conversational presence.",
        scene=(
            "An engaging whiteboard animation video where every spoken sentence accompanies hand-drawn visual elements. "
            "The narrator speaks with measured, calm pacing, leaving distinct natural breath pauses (around 1.2 to 1.5 seconds) "
            "between major thoughts and paragraphs so the visual illustrations have time to be drawn on screen."
        ),
        sample_context=(
            "Deliver the script with clear, comfortable pacing (around 95–100 words per minute). "
            "Do NOT rush or speak rapidly. Pronounce each word warmly and clearly in natural conversational Saudi Arabic. "
            "Pause distinctly after each comma and full sentence, letting each visual concept settle before continuing."
        )
    ),
    "DYNAMIC_WHITEBOARD_SWEETSPOT": DirectorNote(
        style="Energetic, charismatic, natural Saudi conversational explainer with crisp rhythm and zero sluggishness.",
        scene=(
            "A polished YouTube whiteboard animation video. The speaker is confident, youthful, and engaging. "
            "Pacing is lively and brisk without being an overwhelming rush or breathless race, giving each concept "
            "its punchy musical rhythm."
        ),
        sample_context=(
            "Speak at a natural, engaging YouTube explainer tempo (around 125 words per minute). "
            "Flow smoothly and dynamically between sentences with brief natural speech punctuation, avoiding unnatural dead air. "
            "Clean vocal projection, confident charisma, modern conversational Saudi accent with zero audible gasps."
        )
    )
}


