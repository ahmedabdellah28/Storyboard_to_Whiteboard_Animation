"""Stage 2: Unified Gemini TTS Voice Synthesis + Chunk Whisper QA Guard + Broadcast Mastering.

Dual-track language-specialized architecture:
  - Saudi Arabic (`ar`): Strictly authentic modern Saudi / White Riyadh YouTube creator style
    (`Fenrir`, `SAUDI_YOUTH_CREATOR`), Arabic-density chunking (48 words), stage-cue extraction,
    Saudi tashkeel/loanword lexicon, Arabic vocal DSP chain, and `_norm_ar` Whisper QA.
  - English / Foreign (`en`+): Dedicated foreign track using `system_instruction` so `Puck`
    executes full director notes & dynamic matched phonetic glossary without ever reading
    instructions aloud, English-density chunking (72 words), and US YouTube vocal DSP chain.

Both tracks share 48kHz end-to-end 2-pass linear `-14 LUFS` mastering, RMS silence trimming,
seamless micro-faded stitching, and content-hash chunk caching.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import threading
import time
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

import core_engine.dns_patch  # noqa: F401
from google import genai
from google.genai import types

from core.aion.audio_mastering import (
    MASTER_SAMPLE_RATE,
    master_voice_ffmpeg,
    stitch_wav_chunks_seamless,
    trim_pcm_silence_rms,
)
from core.api.key_pool import get_key_pool
from voice_studio.engine import convert_raw_pcm_to_wav
from voice_studio.profiles import AUDIO_PROFILES, DIRECTOR_NOTES

DEFAULT_TTS_MODEL = "gemini-3.1-flash-tts-preview"

# Dynamic phonetic glossary for English/Foreign scientific & loanword terms (only matched terms are injected)
EN_PRONUNCIATION_HINTS: List[Tuple[str, str]] = [
    ("Ganzfeld", 'Ganzfeld ("GANZ-felt", hard G)'),
    ("Metzger", 'Metzger ("METS-ger")'),
    ("Petter Johansson", 'Petter Johansson ("PEH-ter YO-han-son", Y sound)'),
    ("Lackner", 'Lackner ("LACK-ner")'),
    ("Capilano", 'Capilano ("kap-ih-LAH-no")'),
    ("Chronostasis", 'Chronostasis ("kroh-nuh-STAY-sis")'),
    ("Kielan Yarrow", 'Kielan Yarrow ("KEE-lan YAR-oh")'),
    ("Jamais", 'Jamais Vu ("zhah-may VOO", French pronunciation)'),
    ("deja vu", 'deja vu ("day-zhah VOO")'),
    ("Akira", 'Akira O\'Connor ("ah-KEE-rah oh-KON-ner")'),
    ("Ig Nobel", 'Ig Nobel ("IG noh-BEL", pronounce "Ig" as a word, not letters)'),
    ("Cryptomnesia", 'Cryptomnesia ("krip-tom-NEE-zhuh")'),
    ("Placebo", 'Placebo ("pluh-SEE-boh")'),
    ("Nocebo", 'Nocebo ("noh-SEE-boh")'),
    ("Dopamine", 'Dopamine ("DOH-puh-meen")'),
    ("Cortisol", 'Cortisol ("KOR-tih-zol")'),
    ("Amygdala", 'Amygdala ("uh-MIG-duh-luh")'),
]

# Saudi Arabic pronunciation & smart partial tashkeel hints for ambiguous terms / foreign brands
AR_SAUDI_PRONUNCIATION_LEXICON: Dict[str, str] = {
    "بلاسيبو": "بلاسِيبو",
    "نوسيبو": "نوسِيبو",
    "دوبامين": "دوبامِين",
    "كورتيزول": "كورتِيزول",
    "أدرينالين": "أدرينالِين",
    "سيروتونين": "سيروتونِين",
    "نايكي": "نايكِي",
    "بوينج": "بُوينج",
    "ديجافو": "ديجافُو",
    "جامي فو": "جامِي فُو",
    "كرونوستيسيس": "كرونوستِيسِيس",
    "كريبتومنيزيا": "كريبتومنِيزيا",
    "غانزفيلد": "غانزفِيلد",
}

# Egyptian Cairo Arabic pronunciation & smart partial tashkeel hints for ambiguous terms / foreign brands
AR_EGYPTIAN_PRONUNCIATION_LEXICON: Dict[str, str] = {
    "بلاسيبو": "بلاسِيبو",
    "نوسيبو": "نوسِيبو",
    "دوبامين": "دوبامِين",
    "كورتيزول": "كورتِيزول",
    "أدرينالين": "أدرينالِين",
    "سيروتونين": "سيروتونِين",
    "نايكي": "نايكِي",
    "بوينج": "بُوينج",
    "ديجافو": "ديجافُو",
    "جامي فو": "جامِي فُو",
    "كرونوستيسيس": "كرونوستِيسِيس",
    "كريبتومنيزيا": "كريبتومنِيزيا",
    "غانزفيلد": "جانزفِيلد",
}

_EGYPTIAN_DIALECT_ALIASES = {
    "egyptian", "egyptian_cairo", "egyptian_male", "egyptian_female",
    "ar_eg", "ar-eg", "eg", "masri", "cairo",
}
_FEMALE_VOICES = {"kore", "aoede", "leda", "zephyr", "autonoe", "callirrhoe", "despina", "erinome", "laomedeia", "pulcherrima", "sulafat", "vindemiatrix"}


def is_egyptian_dialect(dialect: str = "", profile_key: str = "", note_key: str = "") -> bool:
    """Return True when the requested Arabic track targets Cairo Egyptian Arabic."""
    d = str(dialect or "").strip().lower()
    p = str(profile_key or "").strip().upper()
    n = str(note_key or "").strip().upper()
    return (
        d in _EGYPTIAN_DIALECT_ALIASES
        or d.startswith("egypt")
        or p.startswith("EGYPTIAN_")
        or "EGYPTIAN" in n
        or n == "VYOND_DRAMATIC_STORY"
    )


def prepare_arabic_egyptian_tts_text(
    text: str,
    custom_lexicon: Optional[Dict[str, str]] = None,
) -> Tuple[str, List[str]]:
    """Prepares Arabic text for Egyptian Cairo TTS: extracts stage cues & applies targeted loanword lexicon."""
    clean, cues = extract_stage_cues(text)
    merged_lex = dict(AR_EGYPTIAN_PRONUNCIATION_LEXICON)
    if custom_lexicon:
        merged_lex.update(custom_lexicon)
    spoken = clean
    for src, dst in merged_lex.items():
        if src in spoken:
            spoken = spoken.replace(src, dst)
    return spoken, cues


_STAGE_CUE_RE = re.compile(r"\[[^\[\]\n]{1,70}\]")
_POOL_LOCK = threading.Lock()


def extract_stage_cues(text: str) -> Tuple[str, List[str]]:
    """Extracts bracketed performance cues (e.g. `[بصدمة]`, `[whisper]`) without leaving them in spoken text."""
    cues = [m.strip("[]").strip() for m in _STAGE_CUE_RE.findall(text) if m.strip("[]").strip()]
    clean = _STAGE_CUE_RE.sub("", text)
    clean = re.sub(r"[ \t]{2,}", " ", clean).strip()
    return clean, cues


def load_project_pronunciation_lexicon(project_dir: Optional[Path]) -> Dict[str, str]:
    """Loads optional per-project `inputs/pronunciation_lexicon.json` overrides."""
    if not project_dir:
        return {}
    lex_path = Path(project_dir) / "inputs" / "pronunciation_lexicon.json"
    if not lex_path.is_file():
        return {}
    try:
        data = json.loads(lex_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items() if k and v}
    except Exception:
        pass
    return {}


def prepare_arabic_saudi_tts_text(
    text: str,
    custom_lexicon: Optional[Dict[str, str]] = None,
) -> Tuple[str, List[str]]:
    """Prepares Arabic text for Saudi TTS: extracts stage cues & applies targeted tashkeel/loanword lexicon."""
    clean, cues = extract_stage_cues(text)
    merged_lex = dict(AR_SAUDI_PRONUNCIATION_LEXICON)
    if custom_lexicon:
        merged_lex.update(custom_lexicon)

    spoken = clean
    for src, dst in merged_lex.items():
        if src in spoken:
            spoken = spoken.replace(src, dst)
    return spoken, cues


def match_en_pronunciation_hints(
    text: str,
    custom_lexicon: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Returns only the English/Foreign phonetic hints that actually appear in `text`."""
    low = text.lower()
    matched: List[str] = []
    for term, hint in EN_PRONUNCIATION_HINTS:
        if term.lower() in low:
            matched.append(hint)
    if custom_lexicon:
        for term, hint in custom_lexicon.items():
            if term.lower() in low:
                matched.append(f'{term} ("{hint}")')
    # Add clean year-reading reminder only if a 4-digit year appears in the chunk
    if re.search(r"\b(1[0-9]{3}|20[0-2][0-9])\b", text):
        matched.append('Read 4-digit years naturally (e.g., 1974 -> "nineteen seventy-four", 2005 -> "two thousand five").')
    return matched


def split_section_paragraphs(text: str, max_words: Optional[int] = None, language: str = "ar") -> List[str]:
    """Splits script into optimal TTS chunks tuned per language density (48 words AR / 72 words EN).

    Coalesces consecutive short one-liner lines (e.g. punchy ad/shorts scripts) into natural
    multi-sentence chunks up to `limit` so Gemini TTS preserves comedic/narrative pacing,
    avoids excessive API calls, and gives Faster-Whisper enough context for reliable QA.
    """
    is_en = str(language or "ar").lower().startswith("en")
    limit = max_words if max_words is not None else (72 if is_en else 48)
    min_merge_words = 22 if is_en else 18

    paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
    raw_chunks: List[str] = []
    for p in paragraphs:
        words = p.split()
        if len(words) <= limit:
            raw_chunks.append(p)
        else:
            sents = re.split(r"([.!?؟]+)", p)
            buf: List[str] = []
            buf_w = 0
            for i in range(0, len(sents), 2):
                s = sents[i].strip()
                punct = sents[i + 1].strip() if i + 1 < len(sents) else ""
                full_s = f"{s}{punct}".strip()
                if not full_s:
                    continue
                wc = len(full_s.split())
                if buf and buf_w + wc > limit:
                    raw_chunks.append(" ".join(buf))
                    buf = [full_s]
                    buf_w = wc
                else:
                    buf.append(full_s)
                    buf_w += wc
            if buf:
                raw_chunks.append(" ".join(buf))

    # Coalesce consecutive short chunks so 2-4 word punchlines never become fragile standalone TTS calls
    chunks: List[str] = []
    for rc in raw_chunks:
        rc_w = len(rc.split())
        if chunks:
            prev_w = len(chunks[-1].split())
            if (prev_w < min_merge_words or rc_w < min_merge_words) and (prev_w + rc_w <= limit):
                chunks[-1] = f"{chunks[-1]} {rc}"
                continue
        chunks.append(rc)
    return chunks


def build_tts_request(
    text: str,
    language: str,
    profile_key: str,
    note_key: str,
    custom_lexicon: Optional[Dict[str, str]] = None,
    dialect: str = "saudi_white",
) -> Tuple[str, str]:
    """Builds `(system_instruction, spoken_text)` separately per language & Arabic dialect track.

    - Saudi Arabic (`ar` + `saudi_white`): Strictly locks modern Saudi / White Riyadh creator dialect.
    - Egyptian Arabic (`ar` + `egyptian` / `egyptian_female` / `EGYPTIAN_*`): Strictly locks authentic
      modern Cairo Egyptian Arabic (hard Egyptian Jeem, natural Cairo cadence, zero Gulf/MSA drift).
    - English / Foreign (`en`+): Passes full `AudioProfile` + `DirectorNote` + dynamic matched
      phonetic hints via `system_instruction` without ever reading instructions aloud.
    """
    is_en = str(language or "ar").lower().startswith("en")

    if is_en:
        profile = AUDIO_PROFILES.get(profile_key, AUDIO_PROFILES["US_CASUAL_STORYTELLER"])
        note = DIRECTOR_NOTES.get(note_key, DIRECTOR_NOTES["HIGH_ENERGY_ENGLISH_YT"])
        compiled = note.compile_instruction(profile)
        spoken_text, cues = extract_stage_cues(text)
        hints = match_en_pronunciation_hints(spoken_text, custom_lexicon=custom_lexicon)

        sys_parts = [
            "You are a professional voice actor. NEVER read these instructions or stage cues aloud. "
            "Speak ONLY the user's exact script verbatim once—no preamble, no repetition, no skipped endings.",
            compiled,
            "Studio Hygiene: Close-mic studio clarity, crisp consonant articulation, zero audible gasps, zero dead air.",
        ]
        if cues:
            sys_parts.append(f"Chunk Performance Cues (act out, do NOT speak): {', '.join(cues)}")
        if hints:
            sys_parts.append("Pronunciation Guide (apply naturally):\n- " + "\n- ".join(hints))
        return "\n\n".join(sys_parts), spoken_text

    if is_egyptian_dialect(dialect, profile_key=profile_key, note_key=note_key):
        is_fem = ("female" in str(dialect or "").lower()) or ("FEMALE" in str(profile_key or "").upper()) or ("VYOND" in str(profile_key or "").upper())
        default_prof = "EGYPTIAN_FEMALE_CREATOR" if is_fem else "EGYPTIAN_YOUTH_CREATOR"
        profile = AUDIO_PROFILES.get(profile_key, AUDIO_PROFILES[default_prof])
        note = DIRECTOR_NOTES.get(note_key, DIRECTOR_NOTES["HIGH_ENERGY_EGYPTIAN_YT"])
        compiled = note.compile_instruction(profile)
        spoken_text, cues = prepare_arabic_egyptian_tts_text(text, custom_lexicon=custom_lexicon)
        gender_desc = "Egyptian female" if is_fem else "young Egyptian male"

        sys_parts = [
            f"STRICT DIALECT LOCK — EGYPTIAN ARABIC (CAIRO) ONLY: Speak aloud ONLY the Arabic text provided by the user "
            f"in a charismatic, witty, fast-paced {gender_desc} YouTube creator voice "
            f"(authentic everyday Cairo Egyptian Arabic — لهجة مصرية قاهرية طبيعية وأصلية بجيم مصرية واضحة). "
            f"NEVER drift into Saudi/Gulf, Levantine, or stiff formal news-anchor MSA tone.",
            "ARTICULATION & STUDIO HYGIENE: Close-mic studio clarity, crisp Egyptian pronunciation with hard Cairo Jeem (ج), "
            "natural Cairo rhythm on numbers and everyday phrasing, ZERO breathing/gasps, ZERO dead air.",
            compiled,
            "STRICT VERBATIM RULE: Read the exact Arabic words ONCE verbatim; NEVER repeat sentences, "
            "NEVER read instructions or bracketed cues aloud, and NEVER skip the ending.",
        ]
        if cues:
            sys_parts.append(f"Delivery Emotion Cues for this chunk (act out, NEVER speak): {', '.join(cues)}")
        return "\n\n".join(sys_parts), spoken_text

    # Strict Saudi Arabic Track (committed to modern Saudi / White Riyadh YouTube creator dialect)
    profile = AUDIO_PROFILES.get(profile_key, AUDIO_PROFILES["SAUDI_YOUTH_CREATOR"])
    note = DIRECTOR_NOTES.get(note_key, DIRECTOR_NOTES["HIGH_ENERGY_YOUTUBE"])
    compiled = note.compile_instruction(profile)
    spoken_text, cues = prepare_arabic_saudi_tts_text(text, custom_lexicon=custom_lexicon)

    sys_parts = [
        "STRICT DIALECT LOCK — SAUDI ARABIC ONLY: Speak aloud ONLY the Arabic text provided by the user "
        "in a charismatic, fast-paced, energetic young Saudi male YouTube creator voice "
        "(authentic modern Riyadh / White Saudi dialect — لهجة سعودية شبابية بيضاء أصلية وواضحة). "
        "NEVER drift into Egyptian, Levantine, or stiff news-anchor MSA tone.",
        "ARTICULATION & STUDIO HYGIENE: Close-mic studio clarity, razor-sharp Arabic consonants and shadda (شدّة), "
        "natural Saudi rhythm on numbers and dates, ZERO breathing/gasps, ZERO dead air.",
        compiled,
        "STRICT VERBATIM RULE: Read the exact Arabic words ONCE verbatim; NEVER repeat sentences, "
        "NEVER read instructions or bracketed cues aloud, and NEVER skip the ending.",
    ]
    if cues:
        sys_parts.append(f"Delivery Emotion Cues for this chunk (act out, NEVER speak): {', '.join(cues)}")

    return "\n\n".join(sys_parts), spoken_text


def build_tts_prompt(
    text: str,
    language: str,
    profile_key: str,
    note_key: str,
    custom_lexicon: Optional[Dict[str, str]] = None,
    dialect: str = "saudi_white",
) -> str:
    """Backward-compatible helper returning the spoken payload (instructions now live in `system_instruction`)."""
    _sys_inst, spoken = build_tts_request(
        text, language, profile_key, note_key, custom_lexicon=custom_lexicon, dialect=dialect
    )
    return spoken


def compute_chunk_cache_key(
    *,
    text: str,
    voice_name: str,
    profile_key: str,
    note_key: str,
    language: str,
    model_name: str,
    dialect: str = "saudi_white",
) -> str:
    """Computes an 8-char SHA-256 content hash so edited paragraphs or dialect changes automatically invalidate stale chunks."""
    eff_dialect = str(dialect or "saudi_white").strip().lower()
    # Keep legacy hash identical for default `saudi_white` & `us_casual`, while isolating `egyptian` / custom dialects cleanly
    if eff_dialect in ("", "saudi_white", "us_casual"):
        payload = f"{model_name}|{language}|{voice_name}|{profile_key}|{note_key}|{text.strip()}"
    else:
        payload = f"{model_name}|{language}|{eff_dialect}|{voice_name}|{profile_key}|{note_key}|{text.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


def trim_isolated_tail_glitch(wav_bytes: bytes, min_gap_ms: int = 240, max_tail_ms: int = 420) -> bytes:
    """Drops an isolated short artifact island at chunk tail preceded by silence."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        sw = w.getsampwidth()
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).copy()

    if len(raw) < sr * 1.2:
        return wav_bytes
    win = int(sr * 0.02)
    n_win = len(raw) // win
    rms = np.sqrt(np.mean(raw[:n_win * win].reshape(n_win, win).astype(np.float64) ** 2, axis=1))
    active = rms > 220
    if not np.any(active):
        return wav_bytes
    last_active = int(np.where(active)[0][-1])
    i = last_active
    while i >= 0 and active[i]:
        i -= 1
    island_len_ms = (last_active - i) * 20
    j = i
    while j >= 0 and not active[j]:
        j -= 1
    gap_ms = (i - j) * 20
    if island_len_ms <= max_tail_ms and gap_ms >= min_gap_ms and j > 15:
        keep_samples = int((j + 2) * win)
        out_io = io.BytesIO()
        with wave.open(out_io, "wb") as ow:
            ow.setnchannels(nch)
            ow.setsampwidth(sw)
            ow.setframerate(sr)
            ow.writeframes(raw[:keep_samples].tobytes())
        return out_io.getvalue()
    return wav_bytes


def _norm_ar(word: str) -> str:
    w = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", word)
    w = re.sub(r"[أإآٱ]", "ا", w).replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"[^\w]", "", w)


def _has_repeated_ngram(words: List[str], language: str, n: int = 4) -> Optional[str]:
    if len(words) < n * 2:
        return None
    if language.lower().startswith("en"):
        norm = [re.sub(r"[^a-z0-9]", "", w.lower()) for w in words]
    else:
        # Normalize Arabic diacritics, alef forms, taa marbouta & yaa so duplicate phrases are always caught
        norm = [_norm_ar(w) for w in words]
    norm = [w for w in norm if w]
    seen: Dict[Tuple[str, ...], int] = {}
    for i in range(len(norm) - n + 1):
        ng = tuple(norm[i:i + n])
        if ng in seen and i - seen[ng] >= n:
            return " ".join(ng)
        seen.setdefault(ng, i)
    return None


def verify_chunk_audio(
    chunk_wav: Path,
    expected_text: str,
    whisper_eng: Any,
    language: str,
) -> Tuple[bool, str]:
    tmp_cache = chunk_wav.with_suffix(".verify.json")
    w_out = whisper_eng.transcribe(audio_path=chunk_wav, cache_file=tmp_cache, force=True)
    tmp_cache.unlink(missing_ok=True)
    spoken_text = " ".join(s.text for s in w_out.segments).strip()
    spoken_words = spoken_text.split()
    clean_expected, _cues = extract_stage_cues(expected_text)
    exp_words = clean_expected.split()

    ratio = len(spoken_words) / max(1, len(exp_words))
    rep = _has_repeated_ngram(spoken_words, language=language, n=4)
    if rep:
        return False, f"repeated 4-gram '{rep}'"
    if ratio > 1.22:
        return False, f"word overflow ratio={ratio:.2f} ({len(spoken_words)} vs {len(exp_words)})"
    if ratio < 0.78:
        return False, f"truncation ratio={ratio:.2f} ({len(spoken_words)} vs {len(exp_words)})"

    # Guard against fluent hallucinated speech with matching length but unrelated content
    if language.lower().startswith("ar"):
        def _norm_toks(ws: List[str]) -> set:
            out = set()
            for w in ws:
                nw = _norm_ar(w)
                if len(nw) >= 2:
                    out.add(nw)
            return out
    else:
        def _norm_toks(ws: List[str]) -> set:
            return {re.sub(r"[^\w]", "", w.lower()) for w in ws if len(re.sub(r"[^\w]", "", w)) >= 2}

    exp_set = _norm_toks(exp_words)
    spk_set = _norm_toks(spoken_words)
    if exp_set:
        recall = len(exp_set & spk_set) / len(exp_set)
        if recall < 0.35:
            return False, f"content mismatch overlap={recall:.2f} ({len(spoken_words)} vs {len(exp_words)})"
    return True, f"ok ratio={ratio:.2f} words={len(spoken_words)}/{len(exp_words)}"


def build_inline_style_prefix(
    spoken_text: str,
    *,
    language: str,
    voice_name: str = "Fenrir",
    profile_key: str = "SAUDI_YOUTH_CREATOR",
    note_key: str = "HIGH_ENERGY_YOUTUBE",
    dialect: str = "saudi_white",
    cues: Optional[List[str]] = None,
    custom_lexicon: Optional[Dict[str, str]] = None,
) -> str:
    """Builds the compact inline style prefix for Gemini 3.1/2.5 TTS models per language & dialect."""
    cue_clause = f", with {', '.join(cues)} emotion" if cues else ""
    if str(language or "ar").lower().startswith("en"):
        hints = match_en_pronunciation_hints(spoken_text, custom_lexicon=custom_lexicon)
        hint_clause = f" (Pronounce: {'; '.join(hints[:4])})" if hints else ""
        return (
            f"Say in a fast, charismatic, colloquial American YouTube explainer voice, "
            f"crisp consonants, natural contractions, zero dead air{cue_clause}{hint_clause}: {spoken_text}"
        )
    if is_egyptian_dialect(dialect, profile_key=profile_key, note_key=note_key):
        is_fem = (
            str(voice_name or "").strip().lower() in _FEMALE_VOICES
            or "female" in str(dialect or "").lower()
            or "FEMALE" in str(profile_key or "").upper()
            or "VYOND" in str(profile_key or "").upper()
        )
        persona = "warm, witty Egyptian Cairo female YouTube creator" if is_fem else "warm, witty young Egyptian Cairo male YouTube creator"
        return (
            f"Say enthusiastically in a lively, {persona} voice "
            f"(authentic everyday Cairo Masri Egyptian Arabic, hard Egyptian 'g' for ج, natural Cairo colloquial glottal-stop for ق, "
            f"expressive comedic storytelling rhythm, zero dead air, zero gasps{cue_clause}): {spoken_text}"
        )
    return (
        f"Say enthusiastically in a fast, charismatic young Saudi Riyadh male YouTube creator voice "
        f"(authentic modern White Saudi dialect, crisp Arabic consonants, zero dead air, zero gasps{cue_clause}): {spoken_text}"
    )


def synth_chunk_gemini(
    text: str,
    out_wav: Path,
    voice_name: str,
    profile_key: str,
    note_key: str,
    language: str,
    model_name: str = DEFAULT_TTS_MODEL,
    force: bool = False,
    temperature: float = 0.52,
    retries: int = 30,
    custom_lexicon: Optional[Dict[str, str]] = None,
    dialect: str = "saudi_white",
) -> Path:
    if out_wav.exists() and out_wav.stat().st_size > 4000 and not force:
        try:
            with wave.open(str(out_wav), "rb") as wf:
                if wf.getnframes() > 2400:
                    return out_wav
        except Exception:
            pass

    key_pool = get_key_pool()
    _sys_inst, spoken_text = build_tts_request(
        text=text,
        language=language,
        profile_key=profile_key,
        note_key=note_key,
        custom_lexicon=custom_lexicon,
        dialect=dialect,
    )
    _clean_txt, cues = extract_stage_cues(text)

    # Official compact Gemini TTS style prefix for models that understand inline direction
    # (`gemini-3.1-flash-tts-preview`, `gemini-2.5-flash-preview-tts`).
    # Pure-text models (`gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`) speak literally and
    # MUST receive ONLY `spoken_text` with zero instruction prefix.
    styled_contents = build_inline_style_prefix(
        spoken_text,
        language=language,
        voice_name=voice_name,
        profile_key=profile_key,
        note_key=note_key,
        dialect=dialect,
        cues=cues,
        custom_lexicon=custom_lexicon,
    )

    def _contents_for_model(mdl: str) -> str:
        return spoken_text if "3.8-" in mdl else styled_contents

    cfg = types.GenerateContentConfig(
        temperature=temperature,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        ),
    )

    last_err: Optional[Exception] = None
    fallback_chain = [model_name]
    for cand in ("gemini-2.5-flash-preview-tts", "gemini-3.8-flash-tts"):
        if cand not in fallback_chain:
            fallback_chain.append(cand)
    chain_idx = 0
    active_model = fallback_chain[chain_idx]
    consecutive_429 = 0

    for attempt in range(1, retries + 1):
        mkey = key_pool.get_best_key(model=active_model)
        client = genai.Client(api_key=mkey.key, http_options=types.HttpOptions(timeout=65000))
        try:
            audio = bytearray()
            mime_type = "audio/L16;rate=24000"
            for chunk in client.models.generate_content_stream(
                model=active_model,
                contents=_contents_for_model(active_model),
                config=cfg,
            ):
                if not chunk.parts:
                    continue
                for pt in chunk.parts:
                    if pt.inline_data and pt.inline_data.data:
                        audio.extend(pt.inline_data.data)
                        if pt.inline_data.mime_type:
                            mime_type = pt.inline_data.mime_type
            if not audio:
                raise RuntimeError(f"Empty audio buffer from {active_model}")

            mkey.mark_success()
            trimmed = trim_pcm_silence_rms(bytes(audio), sample_rate=24000, bits_per_sample=16, pad_ms=40, fade_ms=8)
            wav_bytes = trim_isolated_tail_glitch(convert_raw_pcm_to_wav(trimmed, mime_type))
            out_wav.parent.mkdir(parents=True, exist_ok=True)
            tmp_out = out_wav.with_name(f"{out_wav.name}.tmp")
            tmp_out.write_bytes(wav_bytes)
            tmp_out.replace(out_wav)
            return out_wav
        except Exception as e:
            last_err = e
            msg = str(e)
            if "PerDay" in msg or "GenerateRequestsPerDay" in msg or "403" in msg or "PERMISSION_DENIED" in msg:
                key_pool.handle_daily_limit(mkey, active_model)
                consecutive_429 += 1
            elif "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                key_pool.handle_429(mkey, msg, default_cooldown=30)
                consecutive_429 += 1
            print(f"    Retry {attempt}/{retries} ({out_wav.name} | {active_model} | {mkey.masked_key}): {msg[:100]}", flush=True)
            if chain_idx + 1 < len(fallback_chain) and consecutive_429 >= 6:
                chain_idx += 1
                next_mdl = fallback_chain[chain_idx]
                print(f"    ↪️ Switching TTS model {active_model} -> {next_mdl} (quota fallback)", flush=True)
                active_model = next_mdl
                consecutive_429 = 0
            time.sleep(0.4)

    raise RuntimeError(f"TTS chunk failed after {retries} retries: {last_err}")


def concat_and_master_section(
    chunk_wavs: List[Path],
    final_wav: Path,
    language: str = "ar",
    speed_factor: Optional[float] = None,
    gap_sec: Optional[float] = None,
) -> float:
    """Stitches paragraph WAVs seamlessly and masters with language-tuned DSP + 2-pass -14 LUFS at 48kHz."""
    is_en = str(language or "ar").lower().startswith("en")
    eff_speed = speed_factor if speed_factor is not None else (1.00 if is_en else 1.02)
    eff_gap = gap_sec if gap_sec is not None else (0.14 if is_en else 0.15)

    final_wav.parent.mkdir(parents=True, exist_ok=True)
    raw_cat = final_wav.with_suffix(".cat.wav")
    stitch_wav_chunks_seamless(chunk_wavs, raw_cat, gap_sec=eff_gap, fade_ms=10.0, room_tone_dbfs=-68.0)
    try:
        dur, _meta = master_voice_ffmpeg(
            raw_cat,
            final_wav,
            language=language,
            speed_factor=eff_speed,
            sample_rate=MASTER_SAMPLE_RATE,
        )
    finally:
        raw_cat.unlink(missing_ok=True)
    return dur


def synthesize_section_voice(
    script_text: str,
    final_wav: Path,
    language: str,
    voice_name: str,
    profile_key: str,
    note_key: str,
    model_name: str = DEFAULT_TTS_MODEL,
    speed_factor: Optional[float] = None,
    force: bool = False,
    verify_with_whisper: bool = True,
    whisper_eng: Any = None,
    max_workers: int = 4,
    project_dir: Optional[Path] = None,
    dialect: str = "saudi_white",
) -> Dict[str, Any]:
    """Synthesizes content-hashed paragraph chunks -> Faster-Whisper QA -> 48kHz broadcast master."""
    is_en = str(language or "ar").lower().startswith("en")
    is_eg = (not is_en) and is_egyptian_dialect(dialect, profile_key=profile_key, note_key=note_key)
    eff_speed = speed_factor if speed_factor is not None else (1.00 if is_en else 1.02)
    custom_lexicon = load_project_pronunciation_lexicon(project_dir)

    chunks_dir = final_wav.parent / "chunks_38"
    chunks = split_section_paragraphs(script_text, language=language)
    chunk_pairs: List[Tuple[Path, str]] = []
    for idx, c_txt in enumerate(chunks, 1):
        chash = compute_chunk_cache_key(
            text=c_txt,
            voice_name=voice_name,
            profile_key=profile_key,
            note_key=note_key,
            language=language,
            model_name=model_name,
            dialect=dialect,
        )
        chunk_pairs.append((chunks_dir / f"{final_wav.stem}_p{idx:02d}_{chash}.wav", c_txt))

    workers = max(1, min(max_workers, len(chunk_pairs)))
    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [
                ex.submit(
                    synth_chunk_gemini,
                    c_txt,
                    cp,
                    voice_name,
                    profile_key,
                    note_key,
                    language,
                    model_name,
                    force,
                    0.52,
                    30,
                    custom_lexicon,
                    dialect,
                )
                for cp, c_txt in chunk_pairs
            ]
            for f in as_completed(futs):
                f.result()
    else:
        for cp, c_txt in chunk_pairs:
            synth_chunk_gemini(
                c_txt,
                cp,
                voice_name,
                profile_key,
                note_key,
                language,
                model_name,
                force,
                custom_lexicon=custom_lexicon,
                dialect=dialect,
            )

    qa_notes: List[str] = []
    if verify_with_whisper:
        if whisper_eng is None:
            from section_timing.transcription.faster_whisper_engine import FasterWhisperEngine
            whisper_eng = FasterWhisperEngine(model_size="small", language="en" if is_en else "ar")
        for idx, (cp, c_txt) in enumerate(chunk_pairs, 1):
            verified_ok = False
            last_info = ""
            for heal_try in range(1, 5):
                ok, info = verify_chunk_audio(cp, c_txt, whisper_eng, language=language)
                last_info = info
                if ok:
                    qa_notes.append(f"p{idx:02d}:{info}")
                    verified_ok = True
                    break
                print(f"    Chunk {idx} QA REJECT [{heal_try}/4]: {info} -> Regenerating...", flush=True)
                synth_chunk_gemini(
                    c_txt,
                    cp,
                    voice_name,
                    profile_key,
                    note_key,
                    language,
                    model_name,
                    force=True,
                    temperature=0.42,
                    custom_lexicon=custom_lexicon,
                    dialect=dialect,
                )
            if not verified_ok:
                ok, last_info = verify_chunk_audio(cp, c_txt, whisper_eng, language=language)
                if not ok:
                    raise RuntimeError(f"Chunk {idx} failed Whisper QA after 4 attempts: {last_info}")
                qa_notes.append(f"p{idx:02d}:{last_info}")

    dur = concat_and_master_section(
        [cp for cp, _ in chunk_pairs],
        final_wav,
        language=language,
        speed_factor=eff_speed,
    )
    return {
        "audio_wav": str(final_wav),
        "duration": dur,
        "sample_rate": MASTER_SAMPLE_RATE,
        "chunks": len(chunk_pairs),
        "model": model_name,
        "voice": voice_name,
        "dialect": dialect,
        "language_track": "en" if is_en else ("ar_egyptian" if is_eg else "ar_saudi"),
        "speed_factor": eff_speed,
        "qa": qa_notes,
    }
