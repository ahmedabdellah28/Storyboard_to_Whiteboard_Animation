"""Reusable Channel CTA Audio Asset & 9:16 Visual End-Screen Choreography (AION Shorts).

Implements Rule 10 of AION Shorts Director:
  - Synthesizes the canonical Arabic channel CTA voiceover ONCE into a shared,
    reusable asset (`assets/audio/cta/cta_channel_ar_fenrir.wav` + aligned timing JSON)
    and never regenerates it per short.
  - Produces bespoke animated 9:16 CTA graphics (Like button bounce, Subscribe confirmation,
    general downward indicator toward the YouTube Related Video / channel link area —
    zero fake URLs inside the video frame, cleanly spaced inside mobile safe margins).
"""
from __future__ import annotations

import json
import os
import subprocess
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.aion.procedural_graphics import ProceduralGraphicsEngine
from core.config.settings import ASSETS_DIR, PROJECT_ROOT

CANONICAL_CTA_TEXT_AR = (
    "اعمل لايك، واشترك في القناة، وكمل الفيديو كامل من الفيديو المرتبط تحت اسم القناة!"
)
CANONICAL_CTA_TEXT_AR_EG = (
    "اعمل لايك، واشترك في القناة، وكمّل الفيديو كامل من الفيديو المرتبط تحت اسم القناة!"
)
CANONICAL_CTA_TEXT_EN = (
    "Hit like, subscribe to the channel, and watch the full video from the related link right below!"
)
CTA_DIR = ASSETS_DIR / "audio" / "cta"
CTA_WAV_PATH = CTA_DIR / "cta_channel_ar_fenrir.wav"
CTA_TIMING_PATH = CTA_DIR / "cta_channel_ar_fenrir_timing.json"
CTA_WAV_PATH_AR_EG = CTA_DIR / "cta_channel_ar_eg_fenrir.wav"
CTA_TIMING_PATH_AR_EG = CTA_DIR / "cta_channel_ar_eg_fenrir_timing.json"
CTA_WAV_PATH_AR_EG_FEMALE = CTA_DIR / "cta_channel_ar_eg_kore.wav"
CTA_TIMING_PATH_AR_EG_FEMALE = CTA_DIR / "cta_channel_ar_eg_kore_timing.json"
CTA_WAV_PATH_EN = CTA_DIR / "cta_channel_en_puck.wav"
CTA_TIMING_PATH_EN = CTA_DIR / "cta_channel_en_puck_timing.json"

# Clean bespoke flat-vector SVG marks for the visual CTA card (48x48 normalized coords)
LIKE_THUMB_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<circle cx="32" cy="32" r="29" fill="#0F172A" stroke="#38BDF8" stroke-width="3"/>'
    '<path d="M22 30 L28 17 C29 14 33 14 34 18 L34 26 L45 26 C48 26 50 29 49 32 L46 44 '
    'C45 47 42 48 39 48 L22 48 Z" fill="#38BDF8"/>'
    '<rect x="14" y="29" width="7" height="19" rx="2" fill="#FFD400"/>'
    '</svg>'
)

SUBSCRIBE_BELL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<circle cx="32" cy="32" r="29" fill="#0F172A" stroke="#F43F5E" stroke-width="3"/>'
    '<path d="M32 14 C23 14 19 21 19 29 L17 39 L47 39 L45 29 C45 21 41 14 32 14 Z" fill="#F43F5E"/>'
    '<path d="M26 42 C27 46 37 46 38 42 Z" fill="#FFD400"/>'
    '<circle cx="46" cy="20" r="6" fill="#22C55E" stroke="#FFFFFF" stroke-width="2"/>'
    '</svg>'
)

RELATED_VIDEO_BADGE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect x="6" y="14" width="52" height="36" rx="8" fill="#1E293B" stroke="#FFD400" stroke-width="3"/>'
    '<polygon points="27,23 44,32 27,41" fill="#FFD400"/>'
    '</svg>'
)


def _wav_duration(wav_path: Path) -> float:
    with wave.open(str(wav_path), "rb") as wf:
        return round(wf.getnframes() / float(wf.getframerate()), 3)


def ensure_reusable_cta_audio(
    *,
    language: str = "ar",
    dialect: str = "saudi_white",
    force: bool = False,
    voice_name: Optional[str] = None,
    profile_key: Optional[str] = None,
    note_key: Optional[str] = None,
) -> Tuple[Path, Dict[str, Any]]:
    """Return existing approved CTA audio + timing JSON, synthesizing once only if absent."""
    from core.aion.voice_stage import _FEMALE_VOICES, is_egyptian_dialect

    is_en = str(language or "ar").lower().startswith("en")
    is_eg = (not is_en) and is_egyptian_dialect(dialect, profile_key or "", note_key or "")
    is_eg_fem = is_eg and (
        ("female" in str(dialect or "").lower())
        or (str(voice_name or "").lower() in _FEMALE_VOICES)
        or ("FEMALE" in str(profile_key or "").upper())
    )

    if is_en:
        wav_path = CTA_WAV_PATH_EN
        timing_path = CTA_TIMING_PATH_EN
        cta_text = CANONICAL_CTA_TEXT_EN
        v_name = voice_name or "Puck"
        p_key = profile_key or "US_CASUAL_STORYTELLER"
        n_key = note_key or "VIRAL_PSYCHOLOGY_ENGLISH_YT"
        cta_id = "cta_channel_en_puck"
        sec_tag = "cta_channel_en"
        raw_name = "cta_en_raw_chunk.wav"
    elif is_eg:
        wav_path = CTA_WAV_PATH_AR_EG_FEMALE if is_eg_fem else CTA_WAV_PATH_AR_EG
        timing_path = CTA_TIMING_PATH_AR_EG_FEMALE if is_eg_fem else CTA_TIMING_PATH_AR_EG
        cta_text = CANONICAL_CTA_TEXT_AR_EG
        v_name = voice_name or ("Kore" if is_eg_fem else "Fenrir")
        p_key = profile_key or ("EGYPTIAN_FEMALE_CREATOR" if is_eg_fem else "EGYPTIAN_YOUTH_CREATOR")
        n_key = note_key or "HIGH_ENERGY_EGYPTIAN_YT"
        cta_id = "cta_channel_ar_eg_kore" if is_eg_fem else "cta_channel_ar_eg_fenrir"
        sec_tag = "cta_channel_ar_eg_fem" if is_eg_fem else "cta_channel_ar_eg"
        raw_name = "cta_ar_eg_fem_raw_chunk.wav" if is_eg_fem else "cta_ar_eg_raw_chunk.wav"
    else:
        wav_path = CTA_WAV_PATH
        timing_path = CTA_TIMING_PATH
        cta_text = CANONICAL_CTA_TEXT_AR
        v_name = voice_name or "Fenrir"
        p_key = profile_key or "SAUDI_YOUTH_CREATOR"
        n_key = note_key or "HIGH_ENERGY_YOUTUBE"
        cta_id = "cta_channel_ar_fenrir"
        sec_tag = "cta_channel_ar"
        raw_name = "cta_raw_chunk.wav"

    if wav_path.is_file() and timing_path.is_file() and not force:
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        if 2.0 <= float(timing.get("duration", 0.0)) <= 10.0:
            return wav_path, timing

    from google import genai
    from google.genai import types
    from core.api.key_pool import get_key_pool
    from core.aion.timing_stage import run_timing_alignment
    from core.aion.voice_stage import DEFAULT_TTS_MODEL, concat_and_master_section, trim_isolated_tail_glitch, verify_chunk_audio
    from section_timing.transcription.faster_whisper_engine import FasterWhisperEngine
    from voice_studio.engine import convert_raw_pcm_to_wav, trim_pcm_silence

    CTA_DIR.mkdir(parents=True, exist_ok=True)
    raw_chunk = CTA_DIR / raw_name
    if is_en:
        prompt = cta_text
    elif is_eg:
        persona = "Egyptian Cairo female YouTube creator voice (Kore tone)" if is_eg_fem else "Egyptian Cairo male YouTube creator voice (Fenrir tone)"
        prompt = (
            "Read ONLY the exact Arabic sentence below once, cleanly and enthusiastically, "
            f"in a fast-paced {persona} with authentic Cairo pronunciation (hard Egyptian 'g' for ج, natural Cairo rhythm), "
            "with zero preamble, zero explanation, and zero extra words:\n"
            f"{cta_text}"
        )
    else:
        prompt = (
            "Read ONLY the exact Arabic sentence below once, cleanly and enthusiastically, "
            "in a fast-paced Saudi Gulf Arabic YouTube creator voice (Fenrir tone), "
            "with zero preamble, zero explanation, and zero extra words:\n"
            f"{cta_text}"
        )
    key_pool = get_key_pool()
    whisper_eng = FasterWhisperEngine(model_size="small", language="en" if is_en else "ar")

    info = ""
    for attempt in range(1, 6):
        mkey = key_pool.get_best_key(model=DEFAULT_TTS_MODEL)
        client = genai.Client(api_key=mkey.key, http_options=types.HttpOptions(timeout=45000))
        cfg = types.GenerateContentConfig(
            temperature=0.35 if attempt <= 2 else 0.25,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=v_name)
                )
            ),
        )
        audio = bytearray()
        mime_type = "audio/L16;rate=24000"
        for chunk in client.models.generate_content_stream(model=DEFAULT_TTS_MODEL, contents=prompt, config=cfg):
            if chunk.parts:
                for pt in chunk.parts:
                    if pt.inline_data and pt.inline_data.data:
                        audio.extend(pt.inline_data.data)
                        if pt.inline_data.mime_type:
                            mime_type = pt.inline_data.mime_type
        if not audio:
            continue
        mkey.mark_success()
        trimmed = trim_pcm_silence(bytes(audio), sample_rate=24000, bits_per_sample=16, pad_ms=35)
        wav_bytes = trim_isolated_tail_glitch(convert_raw_pcm_to_wav(trimmed, mime_type))
        raw_chunk.write_bytes(wav_bytes)
        ok_qa, info = verify_chunk_audio(raw_chunk, cta_text, whisper_eng, language="en" if is_en else "ar")
        dur_chk = _wav_duration(raw_chunk)
        if ok_qa and dur_chk <= 9.5:
            break
        raw_chunk.unlink(missing_ok=True)
    else:
        raise RuntimeError(f"Failed clean concise CTA TTS synthesis after retries (last={info})")

    concat_and_master_section([raw_chunk], wav_path, language="en" if is_en else "ar", speed_factor=1.04)
    raw_chunk.unlink(missing_ok=True)
    timing_raw = run_timing_alignment(
        sec_id=sec_tag,
        wav_path=wav_path,
        script_text=cta_text,
        timing_dir=CTA_DIR,
        language="en" if is_en else "ar",
        voice_name=v_name,
        force=True,
        whisper_eng=whisper_eng,
    )
    timing = {
        "cta_id": cta_id,
        "dialect": "us_casual" if is_en else ("egyptian_female" if is_eg_fem else ("egyptian" if is_eg else "saudi_white")),
        "text": cta_text,
        "voice": v_name,
        "profile": p_key,
        "note": n_key,
        "wav_path": str(wav_path),
        "duration": _wav_duration(wav_path),
        "words": timing_raw.get("words", []),
        "sentences": timing_raw.get("sentences", []),
    }
    timing_path.write_text(json.dumps(timing, indent=2, ensure_ascii=False), encoding="utf-8")
    return wav_path, timing


def concat_narrative_with_cta(
    *,
    narrative_wav: Path,
    narrative_words: List[Dict[str, Any]],
    narrative_sentences: List[Dict[str, Any]],
    out_wav: Path,
    language: str = "ar",
    dialect: str = "saudi_white",
    gap_sec: float = 0.24,
    trim_narrative_start: float = 0.0,
    trim_narrative_end: Optional[float] = None,
) -> Dict[str, Any]:
    """Concatenate sliced/existing narrative WAV cleanly with reusable CTA WAV and emit unified timing."""
    cta_wav, cta_timing = ensure_reusable_cta_audio(language=language, dialect=dialect)
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    raw_narr_dur = _wav_duration(Path(narrative_wav))
    t_start = max(0.0, float(trim_narrative_start))
    t_end = min(raw_narr_dur, float(trim_narrative_end)) if trim_narrative_end else raw_narr_dur
    used_narr_dur = max(0.5, t_end - t_start)
    cta_dur = float(cta_timing.get("duration") or _wav_duration(cta_wav))

    tmp_narr = out_wav.with_name(f"{out_wav.stem}_narr_48k.wav")
    tmp_cta = out_wav.with_name(f"{out_wav.stem}_cta_48k.wav")
    tmp_gap = out_wav.with_name(f"{out_wav.stem}_gap_48k.wav")

    trim_args: List[str] = []
    if t_start > 0.005:
        trim_args.extend(["-ss", f"{t_start:.3f}"])
    if trim_narrative_end or t_start > 0.005:
        trim_args.extend(["-t", f"{used_narr_dur:.3f}"])
    fade_out_st = max(0.0, used_narr_dur - 0.030)
    narr_af = f"afade=t=in:st=0:d=0.025,afade=t=out:st={fade_out_st:.3f}:d=0.030"
    subprocess.run(
        ["ffmpeg", "-y", *trim_args, "-i", str(narrative_wav), "-af", narr_af, "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(tmp_narr)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(cta_wav), "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(tmp_cta)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", f"{gap_sec:.3f}", "-c:a", "pcm_s16le", str(tmp_gap)],
        check=True, capture_output=True,
    )
    concat_txt = out_wav.with_name(f"{out_wav.stem}_cat.txt")
    concat_txt.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in (tmp_narr, tmp_gap, tmp_cta)),
        encoding="utf-8",
    )
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(out_wav)],
        check=True, capture_output=True,
    )
    narr_clip_dur = _wav_duration(tmp_narr)
    for p in (tmp_narr, tmp_cta, tmp_gap, concat_txt):
        p.unlink(missing_ok=True)

    cta_offset = round(narr_clip_dur + gap_sec, 3)
    total_dur = _wav_duration(Path(out_wav))

    # Build shifted unified words & sentences aligned cleanly to sliced clip
    merged_words: List[Dict[str, Any]] = []
    for w in narrative_words:
        ws = float(w.get("start", 0.0))
        we = float(w.get("end", 0.0))
        if we <= t_start + 0.02 or ws >= t_end - 0.02:
            continue
        ns = round(max(0.0, ws - t_start), 3)
        ne = round(min(narr_clip_dur, max(ns + 0.04, we - t_start)), 3)
        merged_words.append({
            "word": w["word"],
            "start": ns,
            "end": ne,
            "duration": round(ne - ns, 3),
        })
    for cw in cta_timing.get("words", []):
        merged_words.append({
            "word": cw["word"],
            "start": round(cta_offset + float(cw["start"]), 3),
            "end": round(min(total_dur, cta_offset + float(cw["end"])), 3),
            "duration": float(cw.get("duration", 0.2)),
            "is_cta": True,
        })

    merged_sents: List[Dict[str, Any]] = []
    for s in narrative_sentences:
        ss = float(s.get("start", 0.0))
        se = float(s.get("end", 0.0))
        if se <= t_start + 0.15 or ss >= t_end - 0.15:
            continue
        ns = round(max(0.0, ss - t_start), 3)
        ne = round(min(narr_clip_dur, max(ns + 0.25, se - t_start)), 3)
        merged_sents.append({"text": s["text"], "start": ns, "end": ne})
    merged_sents.append({
        "text": cta_timing.get("text", CANONICAL_CTA_TEXT_AR),
        "start": cta_offset,
        "end": round(total_dur, 3),
        "is_cta": True,
    })

    return {
        "master_wav": str(out_wav),
        "trim_source_window": [round(t_start, 3), round(t_end, 3)],
        "narrative_duration": round(narr_clip_dur, 3),
        "cta_start": cta_offset,
        "cta_duration": round(cta_dur, 3),
        "total_duration": round(total_dur, 3),
        "cta_reused_from": str(cta_wav),
        "cta_text": cta_timing.get("text", CANONICAL_CTA_TEXT_AR),
        "words": merged_words,
        "sentences": merged_sents,
    }


def build_cta_visual_sequence(
    *,
    cta_start: float,
    total_dur: float,
    font_primary: str,
    font_display: str,
    palette: Dict[str, Any],
    language: str = "ar",
    width: int = 1080,
    height: int = 1920,
    prefix: str = "cta",
) -> Dict[str, List[Dict[str, Any]]]:
    """Create synchronized 9:16 visual CTA sequence (Like + Subscribe + Related Video Pointer)."""
    st = round(float(cta_start), 3)
    en = round(float(total_dur), 3)
    dur = max(2.0, en - st)
    cx = width * 0.5
    card_fill = str(palette.get("surface", "#0F172A"))
    accent = str(palette.get("accent", "#FFD400"))
    primary = str(palette.get("primary", "#38BDF8"))
    txt_col = str(palette.get("text", "#F8FAFC"))

    # Anchor action beats nicely across CTA words ("لايك" ~0.3s, "اشترك" ~1.4s, "الفيديو المرتبط" ~2.6s)
    t_like = st
    t_sub = round(min(en - 1.2, st + min(1.05, dur * 0.25)), 3)
    t_rel = round(min(en - 0.8, st + min(2.15, dur * 0.50)), 3)

    assets: List[Dict[str, Any]] = [
        {
            "id": f"{prefix}_like_svg",
            "svg": LIKE_THUMB_SVG,
            "in": t_like,
            "out": en,
            "position": [round(cx + 185.0, 1), 650.0],
            "scale": 195.0,
            "entrance": "pop_settle",
            "entrance_dur": 0.30,
            "three_d": False,
        },
        {
            "id": f"{prefix}_sub_svg",
            "svg": SUBSCRIBE_BELL_SVG,
            "in": t_sub,
            "out": en,
            "position": [round(cx - 185.0, 1), 650.0],
            "scale": 195.0,
            "entrance": "pop_settle",
            "entrance_dur": 0.30,
            "three_d": False,
        },
        {
            "id": f"{prefix}_vid_svg",
            "svg": RELATED_VIDEO_BADGE_SVG,
            "in": t_rel,
            "out": en,
            "position": [cx, 1140.0],
            "scale": 240.0,
            "entrance": "slide_down",
            "entrance_dur": 0.34,
            "three_d": False,
        },
    ]

    is_en = str(language or "ar").lower().startswith("en")
    graphics: List[Dict[str, Any]] = [
        {
            "kind": "badge_card",
            "id": f"{prefix}_like_pill",
            "title": "Like" if is_en else "اعمل لايك",
            "subtitle": "Support Experiment" if is_en else "لدعم التجربة",
            "position": [round(cx + 185.0, 1), 815.0],
            "size": [355.0, 128.0],
            "fill": card_fill,
            "stroke": primary,
            "text_color": txt_col,
            "font": font_primary,
            "start": round(t_like, 3),
            "end": en,
        },
        {
            "kind": "badge_card",
            "id": f"{prefix}_sub_pill",
            "title": "Subscribe" if is_en else "اشترك بالقناة",
            "subtitle": "Subscribed ✓" if is_en else "تم التفعيل ✓",
            "position": [round(cx - 185.0, 1), 815.0],
            "size": [355.0, 128.0],
            "fill": card_fill,
            "stroke": "#F43F5E",
            "text_color": txt_col,
            "font": font_primary,
            "start": round(t_sub + 0.05, 3),
            "end": en,
        },
        ProceduralGraphicsEngine(width, height).build_bezier_connector(
            f"{prefix}_rel_arrow",
            (cx, 1240.0),
            (cx, 1455.0),
            curvature=0.0,
            stroke_color=accent,
            stroke_width=9.0,
            start_time=t_rel,
            draw_duration=0.45,
            end_time=en,
            with_arrow=True,
            layer_3d=False,
        ),
    ]

    typography: List[Dict[str, Any]] = [
        {
            "kind": "kinetic_typography",
            "id": f"{prefix}_headline",
            "role": "impact_title",
            "text": "Watch Full Video From Related Link" if is_en else "كمل الفيديو الكامل من الفيديو المرتبط",
            "direction": "ltr" if is_en else "rtl",
            "font": font_display,
            "font_style": "Bold",
            "size": 44 if is_en else 46,
            "position": [cx, 355.0],
            "box": [110.0, 270.0, 860.0, 160.0],
            "leading": 62,
            "color": txt_col,
            "with_backdrop": True,
            "backdrop_fill": card_fill,
            "backdrop_stroke": accent,
            "animation_mode": "impact_title",
            "animator_based_on": 0 if is_en else 2,
            "start": st,
            "end": en,
        }
    ]

    sfx: List[Dict[str, Any]] = [
        {"time": t_like, "cue": "pop", "gain": 0.24},
        {"time": t_sub, "cue": "pop", "gain": 0.24},
        {"time": t_rel, "cue": "glint", "gain": 0.26},
    ]

    return {"assets": assets, "graphics": graphics, "typography": typography, "sfx": sfx}
