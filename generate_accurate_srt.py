"""
Deterministic Acoustic SRT Generator & Subtitle Aligner (Zero AI / Pure Signal Processing)
مولد ومحاذي ملفات SRT الصوتي الدقيق بدون أي ذكاء اصطناعي (معالجة إشارات صوتية نقية)

Features:
1. Pure acoustic voice activity detection (VAD) via FFmpeg silencedetect / RMS energy.
2. Zero AI / No LLM / No cloud API: 100% deterministic, local, and reproducible.
3. Dynamic Programming (Viterbi) alignment of subtitle text phrases to natural vocal bursts.
4. Preserves natural speech rhythm, punctuation pauses (commas, periods, questions), and avoids subtitle drift.
5. Directly updates project_content/srt/combined_subtitles.srt to sync 1:1 with audio.
"""

import os
import sys
import re
import wave
import argparse
import subprocess
from typing import List, Dict, Any, Tuple
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))


def clean_phrase_text(p: str) -> str:
    """Removes punctuation and whitespace to compute phonetic character length."""
    return re.sub(r'[\s\.\،\?؟!,:\"\'-]', '', p)


def clean_len(p: str) -> int:
    return max(1, len(clean_phrase_text(p)))


def has_strong_punct(p: str) -> bool:
    return any(c in p for c in ['.', '!', '؟', '?'])


def has_any_punct(p: str) -> bool:
    return any(c in p for c in ['.', '!', '؟', '?', '،', ',', ':', '؛', '-'])


def format_srt_timestamp(sec: float) -> str:
    """Converts seconds into standard SRT timestamp HH:MM:SS,mmm"""
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms >= 1000:
        s += 1
        ms -= 1000
    if s >= 60:
        m += 1
        s -= 60
    if m >= 60:
        h += 1
        m -= 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def extract_silence_segments(
    audio_path: str,
    noise_db: float = -28.0,
    min_silence_sec: float = 0.18
) -> Tuple[List[Tuple[float, float, float]], List[Tuple[float, float, float]], float]:
    """
    Acoustic Voice Activity Detection (VAD) via FFmpeg silencedetect.
    Returns:
      silences: [(start, end, duration), ...]
      speech:   [(start, end, duration), ...]
      total_duration: float
    """
    cmd = [
        "ffmpeg", "-i", audio_path,
        "-af", f"silencedetect=noise={noise_db}dB:d={min_silence_sec}",
        "-f", "null", "-"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    stderr = proc.stderr

    silences = []
    curr_sil_start = None

    for line in stderr.split('\n'):
        if "silence_start:" in line:
            m = re.search(r'silence_start:\s*([\d\.]+)', line)
            if m:
                curr_sil_start = float(m.group(1))
        elif "silence_end:" in line:
            m = re.search(r'silence_end:\s*([\d\.]+)', line)
            d_m = re.search(r'silence_duration:\s*([\d\.]+)', line)
            if m and curr_sil_start is not None:
                sil_end = float(m.group(1))
                dur = float(d_m.group(1)) if d_m else sil_end - curr_sil_start
                silences.append((curr_sil_start, sil_end, dur))
                curr_sil_start = None

    with wave.open(audio_path, 'rb') as wf:
        total_audio_dur = wf.getnframes() / float(wf.getframerate())

    # Build speech intervals as complementary intervals to silences
    speech = []
    curr_t = 0.0
    for s_st, s_en, _ in silences:
        if s_st > curr_t + 0.04:
            speech.append((curr_t, s_st, s_st - curr_t))
        curr_t = s_en

    if curr_t + 0.04 < total_audio_dur:
        speech.append((curr_t, total_audio_dur, total_audio_dur - curr_t))

    if not speech:
        # Fallback if no silences detected (continuous speech)
        speech.append((0.0, total_audio_dur, total_audio_dur))

    return silences, speech, total_audio_dur


def align_section_phrases_dp(
    phrases: List[str],
    speech: List[Tuple[float, float, float]],
    silences: List[Tuple[float, float, float]],
    target_rate: float = None
) -> List[Dict[str, Any]]:
    """
    Dynamic Programming (Viterbi) monotonic sequence alignment.
    Matches phrases to speech intervals while minimizing tempo deviation
    and snapping punctuation to silence pauses.
    """
    M = len(phrases)
    N = len(speech)
    if M == 0 or N == 0:
        return []

    phrase_lens = [clean_len(p) for p in phrases]
    total_chars = sum(phrase_lens)
    total_speech_dur = sum(s[2] for s in speech)

    if target_rate is None or target_rate <= 0:
        target_rate = total_chars / total_speech_dur if total_speech_dur > 0 else 13.0

    # dp[i][j] = min cost to align first i phrases to first j speech intervals
    # parent[(i, j)] = (prev_i, prev_j)
    dp = np.full((M + 1, N + 1), np.inf)
    parent = {}
    dp[0][0] = 0.0

    for j in range(1, N + 1):
        for i in range(1, M + 1):
            # 1. Match multiple phrases (i_prev..i) to one speech interval j
            for i_prev in range(max(0, i - 6), i):
                if dp[i_prev][j - 1] == np.inf:
                    continue

                L = sum(phrase_lens[i_prev:i])
                D = speech[j - 1][2]
                r = L / D

                # Cost: tempo difference from expected speaking rate
                cost = ((r - target_rate) / target_rate) ** 2 * 10.0

                # Punctuation bonus: ending an interval with punctuation is highly favorable
                last_phrase = phrases[i - 1]
                if has_strong_punct(last_phrase):
                    cost -= 2.0
                elif has_any_punct(last_phrase):
                    cost -= 1.0
                else:
                    if j < N:
                        pause_after = speech[j][0] - speech[j - 1][1]
                        if pause_after > 0.35:
                            cost += 1.5

                # Intermediate phrases with strong punctuation inside interval are penalized
                for k in range(i_prev, i - 1):
                    if has_strong_punct(phrases[k]):
                        cost += 3.0

                total_c = dp[i_prev][j - 1] + cost
                if total_c < dp[i][j]:
                    dp[i][j] = total_c
                    parent[(i, j)] = (i_prev, j - 1)

            # 2. Match 1 phrase spanning across 2 or 3 tiny speech intervals (micro-pauses)
            if i > 0:
                i_prev = i - 1
                for j_prev in range(max(0, j - 3), j - 1):
                    if dp[i_prev][j_prev] == np.inf:
                        continue
                    L = phrase_lens[i - 1]
                    D = sum(speech[k][2] for k in range(j_prev, j))
                    r = L / D
                    cost = ((r - target_rate) / target_rate) ** 2 * 12.0 + 1.0
                    total_c = dp[i_prev][j_prev] + cost
                    if total_c < dp[i][j]:
                        dp[i][j] = total_c
                        parent[(i, j)] = (i_prev, j_prev)

    # Backtrack
    if dp[M][N] == np.inf:
        best_j = min(range(1, N + 1), key=lambda jj: dp[M][jj])
        curr = (M, best_j)
    else:
        curr = (M, N)

    blocks = []
    while curr != (0, 0):
        if curr not in parent:
            break
        prev = parent[curr]
        blocks.append((prev[0], curr[0], prev[1], curr[1]))
        curr = prev
    blocks.reverse()

    # Assign exact millisecond timestamps to each individual phrase
    aligned = []
    for i_start, i_end, j_start, j_end in blocks:
        sub_phrases = phrases[i_start:i_end]
        sub_lens = phrase_lens[i_start:i_end]
        total_sub_len = sum(sub_lens)

        t_start = speech[j_start][0]
        t_end = speech[j_end - 1][1]

        curr_t = t_start
        for k_idx, (p_text, p_l) in enumerate(zip(sub_phrases, sub_lens)):
            fraction = p_l / total_sub_len if total_sub_len > 0 else 1.0 / len(sub_phrases)
            p_dur = (t_end - t_start) * fraction
            p_end = curr_t + p_dur
            if k_idx == len(sub_phrases) - 1:
                p_end = t_end  # Snap last phrase to exact vocal offset

            aligned.append({
                "text": p_text,
                "start": round(curr_t, 3),
                "end": round(p_end, 3),
                "duration": round(p_end - curr_t, 3)
            })
            curr_t = p_end

    return aligned


def parse_existing_srt_phrases(srt_path: str) -> List[str]:
    """Extracts raw text phrases from an existing SRT file."""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = re.split(r'\n\s*\n', content.strip())
    phrases = []
    for b in blocks:
        lines = [x.strip() for x in b.split('\n') if x.strip()]
        if len(lines) >= 3 and '-->' in lines[1]:
            phrases.append(" ".join(lines[2:]))
    return phrases


def parse_transcript_sections(transcript_path: str) -> List[Dict[str, Any]]:
    """Splits transcript_to_speech.txt into sections based on [tag]."""
    with open(transcript_path, 'r', encoding='utf-8') as f:
        text = f.read()

    pattern = r'(\[[a-zA-Z0-9_,\s\-]+\])'
    parts = re.split(pattern, text)

    sections = []
    curr_tag = ""
    for p in parts:
        p_str = p.strip()
        if not p_str:
            continue
        if p_str.startswith('[') and p_str.endswith(']'):
            curr_tag = p_str
        else:
            clean_text = re.sub(r'\[.*?\]', '', p_str).strip()
            sections.append({
                "tag": curr_tag,
                "text": clean_text
            })
    return sections


def map_phrases_to_sections(phrases: List[str], sections: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
    """Maps sequential phrases to their corresponding section indices."""
    def norm(t):
        t = re.sub(r'[،,\.\?!؟:\"\']', '', t)
        t = re.sub(r'[إأآا]', 'ا', t)
        t = re.sub(r'[ىي]', 'ي', t)
        t = re.sub(r'ة', 'ه', t)
        return ''.join(t.split()).lower()

    curr_idx = 0
    ranges = []

    for s_idx, sec in enumerate(sections):
        sec_norm = norm(sec['text'])
        start_idx = curr_idx
        acc_text = ""
        while curr_idx < len(phrases):
            line_norm = norm(phrases[curr_idx])
            if line_norm in sec_norm:
                acc_text += line_norm
                curr_idx += 1
            else:
                if s_idx + 1 < len(sections) and line_norm in norm(sections[s_idx + 1]['text']):
                    break
                acc_text += line_norm
                curr_idx += 1
                if len(acc_text) >= len(sec_norm) * 0.95:
                    break
        ranges.append((start_idx, curr_idx))

    return ranges


def build_accurate_srt(
    audio_dir: str = "project_content/audio",
    transcript_path: str = "project_content/transcript_to_speech.txt",
    existing_srt_path: str = "project_content/srt/combined_subtitles.srt",
    output_srt_path: str = "project_content/srt/combined_subtitles.srt",
    pause_between_sections: float = 0.0,
    save_individual_sections: bool = True
):
    """
    Main entry point: Accurately aligns all audio sections with subtitles
    and writes the final synchronized combined_subtitles.srt.
    """
    print("=" * 85)
    print("      🎙️ DETERMINISTIC ACOUSTIC SRT GENERATOR (ZERO AI) 🎙️")
    print("=" * 85)

    if not os.path.isabs(audio_dir):
        audio_dir = os.path.join(ROOT_DIR, audio_dir)
    if not os.path.isabs(transcript_path):
        transcript_path = os.path.join(ROOT_DIR, transcript_path)
    if not os.path.isabs(existing_srt_path):
        existing_srt_path = os.path.join(ROOT_DIR, existing_srt_path)
    if not os.path.isabs(output_srt_path):
        output_srt_path = os.path.join(ROOT_DIR, output_srt_path)

    sections = parse_transcript_sections(transcript_path)
    phrases = parse_existing_srt_phrases(existing_srt_path)
    section_ranges = map_phrases_to_sections(phrases, sections)

    print(f"Loaded Transcript : {len(sections)} sections ({transcript_path})")
    print(f"Loaded Phrases    : {len(phrases)} subtitle lines ({existing_srt_path})")
    print(f"Audio Directory   : {audio_dir}")
    print(f"Section Pause     : {pause_between_sections:.2f}s")
    print(f"Output Target     : {output_srt_path}\n")

    master_srt_entries = []
    global_time_offset = 0.0
    total_audio_time = 0.0

    for sec_idx in range(len(sections)):
        sec_num = sec_idx + 1
        wav_file = os.path.join(audio_dir, f"section_{sec_num:02d}_speed_1.0x.wav")
        if not os.path.exists(wav_file):
            raise FileNotFoundError(f"Section audio file missing: {wav_file}")

        silences, speech, dur = extract_silence_segments(wav_file, noise_db=-28.0, min_silence_sec=0.18)
        st_i, en_i = section_ranges[sec_idx]
        sec_phrases = phrases[st_i:en_i]

        aligned = align_section_phrases_dp(sec_phrases, speech, silences)

        print(f"[{sec_num:02d}/{len(sections):02d}] ⚡ Sec {sec_num:02d} ({sections[sec_idx]['tag']}): "
              f"{len(aligned):2d} phrases aligned | Audio: {dur:5.2f}s | Offset: {global_time_offset:6.2f}s")

        for entry in aligned:
            global_st = entry["start"] + global_time_offset
            global_en = entry["end"] + global_time_offset
            master_srt_entries.append({
                "index": len(master_srt_entries) + 1,
                "start": global_st,
                "end": global_en,
                "text": entry["text"]
            })

        global_time_offset += dur + pause_between_sections
        total_audio_time += dur

    # Write Master SRT file
    os.makedirs(os.path.dirname(output_srt_path), exist_ok=True)
    with open(output_srt_path, "w", encoding="utf-8") as f:
        for entry in master_srt_entries:
            st_str = format_srt_timestamp(entry["start"])
            en_str = format_srt_timestamp(entry["end"])
            f.write(f"{entry['index']}\n")
            f.write(f"{st_str} --> {en_str}\n")
            f.write(f"{entry['text']}\n\n")

    # Optionally write individual section SRTs
    if save_individual_sections:
        sections_srt_dir = os.path.join(os.path.dirname(output_srt_path), "sections")
        os.makedirs(sections_srt_dir, exist_ok=True)
        for sec_idx in range(len(sections)):
            sec_num = sec_idx + 1
            sec_file = os.path.join(sections_srt_dir, f"section_{sec_num:02d}.srt")
            # Filter entries belonging to this section and re-index from 1 relative to section audio
            st_i, en_i = section_ranges[sec_idx]
            sec_entries = master_srt_entries[st_i:en_i]
            if not sec_entries:
                continue
            # Section local start time is the offset
            sec_offset = sum(extract_silence_segments(os.path.join(audio_dir, f"section_{k:02d}_speed_1.0x.wav"))[2] + pause_between_sections for k in range(1, sec_num))
            with open(sec_file, "w", encoding="utf-8") as sf:
                for idx, entry in enumerate(sec_entries, 1):
                    loc_st = max(0.0, entry["start"] - sec_offset)
                    loc_en = max(0.0, entry["end"] - sec_offset)
                    sf.write(f"{idx}\n")
                    sf.write(f"{format_srt_timestamp(loc_st)} --> {format_srt_timestamp(loc_en)}\n")
                    sf.write(f"{entry['text']}\n\n")

    print("\n" + "=" * 85)
    print("🎉 ACCURATE SRT GENERATION COMPLETE!")
    print(f"  • Total Subtitle Entries : {len(master_srt_entries)}")
    print(f"  • Total Audio Duration   : {total_audio_time:.2f}s (~{int(total_audio_time//60)}m {int(total_audio_time%60)}s)")
    print(f"  • Timeline Start -> End  : {format_srt_timestamp(master_srt_entries[0]['start'])} --> {format_srt_timestamp(master_srt_entries[-1]['end'])}")
    print(f"  • File Written To        : {output_srt_path}")
    if save_individual_sections:
        print(f"  • Individual Sections    : {sections_srt_dir}")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deterministic Acoustic SRT Generator")
    parser.add_argument("--audio_dir", default="project_content/audio")
    parser.add_argument("--transcript", default="project_content/transcript_to_speech.txt")
    parser.add_argument("--existing_srt", default="project_content/srt/combined_subtitles.srt")
    parser.add_argument("--output_srt", default="project_content/srt/combined_subtitles.srt")
    parser.add_argument("--pause", type=float, default=0.0, help="Pause between sections in seconds (0.0 for seamless concat)")
    parser.add_argument("--save_individual", action="store_true", default=True, help="Also save individual section SRTs in srt/sections/")
    args = parser.parse_args()

    build_accurate_srt(
        audio_dir=args.audio_dir,
        transcript_path=args.transcript,
        existing_srt_path=args.existing_srt,
        output_srt_path=args.output_srt,
        pause_between_sections=args.pause,
        save_individual_sections=args.save_individual
    )
