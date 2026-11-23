"""
Voice Studio Profiles & Director Notes
Customizable voice personas and directorial scene notes for Gemini GenAI TTS.
Tuned specifically for Bendia-style fast-paced Saudi YouTube explainers:
Rapid momentum (~150-165 WPM), zero dead air for 20-asset storyboards,
witty/expressive micro-inflections, and razor-sharp Arabic letter articulation.
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
    tone: str = "Fast-paced, charismatic, expressive Saudi YouTube creator with dynamic micro-inflections (witty, shocked, curious, punchy)"
    accent: str = "Natural modern Saudi / White Gulf Arabic (لهجة سعودية شبابية بيضاء سريعة وواضحة جداً)"
    pace: str = "High-Velocity Conversational Flow (~155 WPM) — Zero Dead Air, Tight Asset Synchronization"
    articulation_rule: str = "High speed MUST NEVER cause slurred or swallowed letters. Attack every Arabic consonant, shadda (شدّة), and word ending with studio-grade crispness (مخارج حروف حادة وواضحة جداً رغم السرعة)."

    def compile_instruction(self, profile: AudioProfile) -> str:
        """
        Combines voice persona and director notes into the unified Gemini TTS prompt
        engineered for fast-paced storytelling with 100% crisp diction and expressive attitude.
        """
        return (
            "AUDIO SCRIPT — GEMINI TTS (DO NOT READ THESE INSTRUCTIONS ALOUD)\n"
            f"STYLE: {self.style.strip()}\n"
            f"TONE: {self.tone.strip()}\n"
            f"ACCENT: {self.accent.strip()}\n"
            f"PACE: {self.pace.strip()}\n"
            f"ARTICULATION RULE: {self.articulation_rule.strip()}\n\n"
            f"# Audio Profile\n"
            f"{profile.description.strip()}\n\n"
            f"# Scene\n"
            f"{self.scene.strip()}\n\n"
            f"# Sample Context & Delivery Rules\n"
            f"{self.sample_context.strip()}"
        )


# Preconfigured Voice Personas
AUDIO_PROFILES = {
    "SAUDI_YOUTH_CREATOR": AudioProfile(
        name="Young Saudi YouTube Creator (Bendia Style)",
        description=(
            "Young Saudi male YouTube creator, around 25–28 years old (in the exact vocal style of viral channel 'Bendia'). "
            "Natural modern Saudi Arabic accent, fast, sharp, and effortless to understand across the Arab world. "
            "Medium male pitch, youthful, energetic, confident, and highly expressive. "
            "He combines rapid-fire storytelling momentum with genuine human emotion: a witty, knowing vocal smile on ironic twists, "
            "sharp vocal weight on shocking numbers and crimes, and intrigued intensity on mysteries. "
            "Every single Arabic letter and syllable is articulated cleanly and crisply without mumbling or swallowing word endings. "
            "He sounds spontaneous and authentic—never like a stiff news anchor, slow documentary narrator, or robotic reader."
        )
    ),
    "PROFESSIONAL_EXPLAINER": AudioProfile(
        name="Professional Arabic Explainer",
        description=(
            "Professional, clear, modern Arabic male speaker, around 30–35 years old. "
            "Warm, articulate, fast-moving educational tone with razor-sharp pronunciation and punchy pacing. "
            "Engaging and authoritative without sounding dry or bureaucratic."
        )
    ),
    "NARRATIVE_STORYTELLER": AudioProfile(
        name="Dramatic Fast Storyteller",
        description=(
            "Immersive, high-tension Arabic storyteller with crisp diction and rapid narrative drive. "
            "Expressive vocal shifts between dark suspense, shocking pivots, witty irony, and dramatic payoff—engineered for high-retention multi-story videos."
        )
    ),
    "US_CASUAL_STORYTELLER": AudioProfile(
        name="Colloquial American YouTube Storyteller",
        description=(
            "Young American male YouTube storyteller, around 24–29 years old, speaking in natural, everyday colloquial American English. "
            "Casual, punchy, charismatic, and effortless—using natural contractions (gonna, wanna, didn't, couldn't, here's the crazy part). "
            "He sounds like a sharp, witty friend telling a wild true story over coffee—never like a stiff news anchor, corporate narrator, or robotic textbook reader. "
            "Crisp consonant clarity at high speed, zero mumbling, with genuine emotional micro-inflections on shocking twists and punchlines."
        )
    ),
    "EGYPTIAN_YOUTH_CREATOR": AudioProfile(
        name="Young Egyptian Male YouTube Creator (Cairo Explainer Style)",
        description=(
            "Young Egyptian male YouTube creator from Cairo, around 25–30 years old. "
            "Natural modern Cairo Egyptian Arabic (العامية المصرية القاهرية الذكية والواضحة جداً) with authentic hard Egyptian Jeem (ج مصرية قاهرية طبيعية). "
            "Energetic, witty, sharp, and confident—combining fast-paced explainer momentum with genuine human warmth, "
            "clever sarcastic inflection on plot twists, and crisp weight on shocking numbers and facts. "
            "Every syllable and scientific/historical term is pronounced cleanly without slurring or robotic news-anchor stiffness."
        )
    ),
    "EGYPTIAN_FEMALE_CREATOR": AudioProfile(
        name="Young Egyptian Female YouTube Creator (Cairo Explainer Style)",
        description=(
            "Young Egyptian female YouTube creator from Cairo, around 24–30 years old. "
            "Natural modern Cairo Egyptian Arabic (العامية المصرية القاهرية الطبيعية والواضحة جداً) with authentic Cairo cadence. "
            "Bright, articulate, engaging, and expressive—fast storytelling flow with clear consonant diction, "
            "warm curiosity on hooks, and punchy emphasis on key reveals—never robotic or sluggish."
        )
    ),
    "EGYPTIAN_VYOND_STORYTELLER": AudioProfile(
        name="Egyptian Female Dramatic Storyteller (Vyond Style)",
        description=(
            "Professional Egyptian female storyteller (حكاءة مصرية محترفة) narrating true dramatic stories "
            "in natural everyday Cairo Egyptian Arabic (العامية المصرية القاهرية الطبيعية جداً). "
            "Single consistent female voice (Kore / Aoede) narrating all events and performing every character's dialogue "
            "by shifting emotion and vocal intensity naturally to match each dramatic beat without robotic pauses."
        )
    )
}

DIRECTOR_NOTES = {
    "HIGH_ENERGY_YOUTUBE": DirectorNote(
        style="Bendia-style rapid, punchy, expressive Saudi YouTube explainer with razor-sharp Arabic letter clarity.",
        scene=(
            "A fast-paced, high-retention animated YouTube explainer (like Bendia) where 20 visual cutout assets pop onto the screen "
            "every 3 seconds in rapid sequence, accompanied by quick visual gags, shocking historical/corporate secrets, and constant forward momentum.\n\n"
            "The narrator speaks directly to the viewer in a fast, captivating, conversational way—like a sharp, witty friend exposing a mind-blowing story.\n\n"
            "The delivery is tightly locked to fast motion graphics: zero sluggishness, zero dead air, yet rich with vocal personality and attitude."
        ),
        sample_context=(
            "This is a fast-paced Saudi YouTube explainer (around 150–165 words per minute), NOT a slow documentary.\n\n"
            "1. SPEED WITH 100% LETTER CLARITY: Speak at a brisk, rapid conversational tempo where sentences flow tightly into one another, "
            "but pronounce EVERY Arabic letter, shadda, and vowel with crisp, staccato precision. Speed comes from eliminating dead air between clauses, NEVER from slurring or eating letters.\n\n"
            "2. EXPRESSIVE MICRO-INFLECTIONS (NOT MONOTONE): Keep the fast pace alive with real human emotion:\n"
            "   - Hit the opening character/company name at the start of a section with a sharp, punchy hook (e.g., 'نايكي!', 'بوينج!', 'بيدرو الأول!').\n"
            "   - Punch shocking numbers, dates, and absurd contrasts with clear vocal emphasis.\n"
            "   - Use a subtle witty, sarcastic undertone on ironic punchlines.\n"
            "   - On rhetorical questions ('هل وقفوا هنا؟ لا!'), raise pitch quickly on the question and drop it sharply on the answer.\n\n"
            "3. BREATH & RHYTHM: Use ultra-tight, natural micro-pauses (0.1s–0.15s) only at commas and pivots to give the 20 visual beats their punchy rhythm without ever stopping the forward momentum."
        )
    ),
    "CALM_EDUCATIONAL": DirectorNote(
        style="Clear, brisk pedagogical delivery with precise diction.",
        scene="An intuitive educational explainer. Step-by-step clarity with smooth, engaging vocal cadence.",
        sample_context="Balanced, active pacing allowing concepts to land clearly while maintaining strong viewer retention."
    ),
    "WHITEBOARD_PACED": DirectorNote(
        style="Measured, articulate explainer pacing with crisp clarity and warm conversational presence.",
        scene=(
            "An engaging whiteboard animation video where spoken clauses accompany hand-drawn visual elements. "
            "The narrator speaks with clear, purposeful rhythm and natural pauses between major thoughts."
        ),
        sample_context=(
            "Deliver the script with clear, comfortable pacing (around 115–125 words per minute). "
            "Pronounce each word warmly and clearly in natural conversational Saudi Arabic."
        )
    ),
    "DYNAMIC_WHITEBOARD_SWEETSPOT": DirectorNote(
        style="Energetic, charismatic, fast Saudi conversational explainer with crisp rhythm and zero sluggishness.",
        scene=(
            "A polished YouTube motion-graphics explainer video. The speaker is confident, youthful, witty, and engaging. "
            "Pacing is fast, lively, and punchy—giving every 6-to-8-word visual beat its own distinct energy."
        ),
        sample_context=(
            "Speak at an energetic YouTube explainer tempo (around 145–155 words per minute). "
            "Flow smoothly and dynamically between sentences with tight speech punctuation, crisp Arabic consonant articulation, "
            "expressive vocal attitude, and zero audible gasps or dead air."
        )
    ),
    "HIGH_ENERGY_ENGLISH_YT": DirectorNote(
        style="Fast-paced, colloquial American YouTube explainer with punchy storytelling rhythm and crystal-clear diction.",
        tone="Fast-paced, charismatic, witty American YouTube creator with dynamic micro-inflections (shocked, ironic, intrigued, punchy)",
        accent="Natural colloquial American English (everyday casual storytelling tone, natural contractions, zero stiff formality)",
        pace="High-Velocity Conversational Flow (~155–170 WPM) — Zero Dead Air, Tight Visual Beat Synchronization",
        articulation_rule="Fast conversational speed MUST NEVER cause slurred or swallowed words. Enunciate consonants cleanly while keeping contractions and casual phrasing 100% natural.",
        scene=(
            "A high-retention animated whiteboard YouTube explainer where 20 cutout illustrations pop onto the screen "
            "every few seconds in rapid sequence, paired with wild true-story twists and constant forward momentum."
        ),
        sample_context=(
            "Deliver this in natural, everyday colloquial American English at ~155–170 WPM.\n"
            "1. HOOK HARD: Hit the opening name or hook with punchy, immediate energy.\n"
            "2. KEEP IT REAL & CASUAL: Sound like an engaging creator talking straight to the audience—lean into natural contractions and rhythmic emphasis on wild numbers or plot twists.\n"
            "3. ZERO DEAD AIR: Use ultra-tight micro-pauses (0.1s–0.15s) only at commas and pivots so every visual asset lands right on the beat."
        )
    ),
    "VIRAL_PSYCHOLOGY_ENGLISH_YT": DirectorNote(
        style="Close-mic, charismatic, mind-blown American YouTube psychology explainer (Zack D. Films / Veritasium crisp retention rhythm).",
        tone="Curious, intimate, sharpest friend revealing shocking mind glitches—warm on interactive hooks, crisp awe on lab twists, decisive drop on punchlines",
        accent="Natural colloquial American English with crystal-clear pronunciation of scientific & foreign terms",
        pace="Tight High-Retention Flow (~152–162 WPM) — Micro-pauses (0.2s) only before plot twists, zero sluggish dead air",
        articulation_rule="NEVER slur scientific terms or foreign names. Enunciate consonants cleanly without harsh sibilance. Read the exact script ONCE; NEVER repeat or add filler sounds.",
        scene=(
            "A viral animated psychology explainer where interactive mental tests ('Imagine...', 'Look up right now...') "
            "pivot quickly into shocking lab proof and punchy takeaways synced to rapid visual cards."
        ),
        sample_context=(
            "Deliver this in natural, everyday American English at ~152–162 WPM:\n"
            "1. INTERACTIVE HOOK: Pull the listener straight into the scenario with warm, intrigued proximity.\n"
            "2. TWIST & STATS: Land a clean 0.18s beat before pivot words ('Here's the catch.', 'Wrong.', 'Even crazier...') and punch numbers & years cleanly.\n"
            "3. MIC-DROP ENDING: Hold steady confident weight on the final 4–5 takeaway words of each section."
        )
    ),
    "HIGH_ENERGY_EGYPTIAN_YT": DirectorNote(
        style="Fast-paced, witty, charismatic Cairo Egyptian Arabic YouTube explainer with razor-sharp clarity.",
        tone="Energetic, clever, conversational Cairo Egyptian creator with natural emotional micro-inflections (curious, shocked, witty, punchy)",
        accent="Authentic modern Cairo Egyptian Arabic (لهجة مصرية قاهرية طبيعية وواضحة جداً بجيم مصرية أصلية، بدون أي انحراف للخليجي أو الشامي أو الفصحى الخبرية الجافة)",
        pace="High-Velocity Conversational Flow (~150–160 WPM) — Zero Dead Air, Tight Visual Beat Synchronization",
        articulation_rule="Fast Egyptian flow MUST NEVER cause slurred or swallowed syllables. Keep Cairo colloquial endings natural while pronouncing historical names, numbers, and scientific terms crisply.",
        scene=(
            "A high-retention animated YouTube explainer in natural Cairo Egyptian Arabic where visual cutouts, "
            "glowing arrows, and animated icons pop onto screen every few seconds in sync with the narration."
        ),
        sample_context=(
            "Deliver this in authentic, natural everyday Cairo Egyptian Arabic (~150–160 WPM):\n"
            "1. AUTHENTIC CAIRO VOICE: Use natural Egyptian Cairo rhythm and hard Egyptian Jeem (ج) throughout; "
            "NEVER drift into Gulf/Saudi, Levantine, or stiff formal broadcast Arabic.\n"
            "2. PUNCHY HOOKS & TWISTS: Hit opening hooks, shocking numbers, and ironic twists with lively human energy.\n"
            "3. ZERO DEAD AIR: Use tight micro-pauses (0.1s–0.15s) only at punctuation and pivots; NEVER read instructions or bracketed cues aloud."
        )
    ),
    "VYOND_DRAMATIC_STORY": DirectorNote(
        style="Fast, flowing, emotionally gripping Egyptian Cairo Arabic dramatic storytelling (Vyond style).",
        tone="Expressive, suspenseful, intimate Egyptian female storyteller shifting seamlessly between characters and emotions",
        accent="Natural everyday Cairo Egyptian Arabic (لهجة عامية مصرية قاهرية طبيعية جداً)",
        pace="Fast, flowing, suspenseful rhythm with zero robotic pauses or stretching",
        articulation_rule="Never read emotion or stage cues aloud; speak ONLY the requested dialogue/narration with crisp Egyptian Arabic clarity.",
        scene=(
            "A dramatic Vyond-style animated story video narrated by a single Egyptian female voice who carries both the narration "
            "and all character voices through emotional inflection."
        ),
        sample_context=(
            "أنتِ راوية قصص مصرية محترفة (حكاءة) تحكين قصة حقيقية باللهجة العامية المصرية القاهرية الطبيعية جداً. "
            "أنتِ تروين الأحداث وتؤدين كلام كل الشخصيات بصوتكِ النسائي الطبيعي مع تغيير نبرة المشاعر والانفعال فقط حسب الموقف. "
            "إيقاع القراءة يجب أن يكون سريعاً، متدفقاً، ومشوقاً بدون أي وقفات آلية أو تمطيط. "
            "إياكِ أن تنطقي التوجيهات الشعورية، انطقي النص المطلوب فقط."
        )
    )
}
