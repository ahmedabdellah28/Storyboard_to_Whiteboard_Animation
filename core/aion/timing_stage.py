"""Stage 3: Faster-Whisper Word & Sentence Timing Alignment (RTL & LTR)."""
from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional

from section_timing.alignment.script_audio_aligner import ScriptAudioAligner
from section_timing.transcription.faster_whisper_engine import FasterWhisperEngine
from section_timing.transcription.whisper_parser import WhisperParser


def _format_srt_time(sec: float) -> str:
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms >= 1000:
        s += 1
        ms -= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def run_timing_alignment(
    sec_id: str,
    wav_path: Path,
    script_text: str,
    timing_dir: Path,
    language: str = "ar",
    model_name: str = "gemini-3.8-flash-tts",
    voice_name: str = "Fenrir",
    force: bool = False,
    whisper_eng: Optional[FasterWhisperEngine] = None,
) -> Dict[str, Any]:
    """Runs Faster-Whisper alignment emitting master JSON (with sentences + words) & SRT."""
    timing_dir.mkdir(parents=True, exist_ok=True)
    lang_code = "en" if language.lower().startswith("en") else "ar"
    if whisper_eng is None:
        whisper_eng = FasterWhisperEngine(model_size="small", language=lang_code)

    whisper_cache = timing_dir / "whisper.json"
    w_out = whisper_eng.transcribe(audio_path=wav_path, cache_file=whisper_cache, force=force)

    raw_words = WhisperParser.extract_word_items(w_out)
    aligner = ScriptAudioAligner(language=lang_code)
    aligned = aligner.align(script_text, raw_words)

    clean_words = [
        {"word": item.text, "start": round(item.start, 3), "end": round(item.end, 3), "duration": round(item.duration, 3)}
        for item in aligned
    ]

    word_srt = timing_dir / f"{sec_id}_word_by_word.srt"
    with open(word_srt, "w", encoding="utf-8") as f:
        for idx, w in enumerate(clean_words, 1):
            f.write(f"{idx}\n{_format_srt_time(w['start'])} --> {_format_srt_time(w['end'])}\n{w['word']}\n\n")

    sentences: List[Dict[str, Any]] = []
    buf: List[Dict[str, Any]] = []
    for w in clean_words:
        buf.append(w)
        if w["word"].endswith((".", "?", "!", "؟")) or w is clean_words[-1]:
            sentences.append({
                "text": " ".join(x["word"] for x in buf),
                "start": buf[0]["start"],
                "end": buf[-1]["end"],
                "word_count": len(buf),
            })
            buf = []

    whisper_text = " ".join(s.text for s in w_out.segments).strip()
    master_json = timing_dir / f"{sec_id}_timing_master.json"
    payload = {
        "section_id": sec_id,
        "language": lang_code,
        "model": model_name,
        "voice": voice_name,
        "audio_path": str(wav_path),
        "duration": round(w_out.duration, 3),
        "words_count": len(clean_words),
        "whisper_tail_sample": " ".join(whisper_text.split()[-12:]),
        "sentences": sentences,
        "words": clean_words,
    }
    master_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def write_all_sections_timing_index(proj_dir: Path, meta: Dict[str, Any]) -> Optional[Path]:
    """Builds `sections/all_sections_timing_index.json` across all completed timing masters."""
    sections_dir = proj_dir / "sections"
    entries = []
    offset = 0.0
    for sdir in sorted(sections_dir.glob("section_*")):
        sid = sdir.name
        tm_path = sdir / "timing" / f"{sid}_timing_master.json"
        wav_path = sdir / "voice" / f"{sid}.wav"
        if not tm_path.is_file():
            continue
        tm = json.loads(tm_path.read_text(encoding="utf-8"))
        dur = float(tm.get("duration", 0.0))
        if dur <= 0 and wav_path.is_file():
            with wave.open(str(wav_path), "rb") as wf:
                dur = round(wf.getnframes() / float(wf.getframerate()), 3)
        entries.append({
            "section_id": sid,
            "start_global": round(offset, 3),
            "end_global": round(offset + dur, 3),
            "duration": dur,
            "words_count": tm.get("words_count", len(tm.get("words", []))),
            "whisper_tail": tm.get("whisper_tail_sample", ""),
            "wav": str(wav_path.relative_to(proj_dir)) if wav_path.is_file() else None,
            "timing_json": str(tm_path.relative_to(proj_dir)),
        })
        offset += dur + 0.35

    if not entries:
        return None
    out = sections_dir / "all_sections_timing_index.json"
    out.write_text(
        json.dumps(
            {
                "project": proj_dir.name,
                "language": meta.get("language", "ar"),
                "model": meta.get("tts_model", "gemini-3.8-flash-tts"),
                "voice": meta.get("tts_voice", "Fenrir"),
                "total_duration_sec": round(max(0.0, offset - 0.35), 2),
                "sections": entries,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return out
