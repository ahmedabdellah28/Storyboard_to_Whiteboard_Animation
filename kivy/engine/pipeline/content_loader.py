"""
Dynamic Project Content Loader
Discovers, validates, and prepares images, SRT subtitles, and audio tracks from any project directory.
"""
import os
import re
import glob
import subprocess
from typing import List, Dict, Any, Tuple
import av


def parse_srt_timestamp(ts_str: str) -> float:
    ts_str = ts_str.strip().replace(',', '.')
    parts = ts_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600.0 + float(m) * 60.0 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60.0 + float(s)
    return float(ts_str)


def format_srt_timestamp(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.', ',')


class DynamicContentLoader:
    @staticmethod
    def parse_srt_file(srt_path: str) -> List[Dict[str, Any]]:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        blocks = re.split(r'\n\s*\n', content.strip())
        entries = []
        for block in blocks:
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if len(lines) >= 3 and '-->' in lines[1]:
                idx_str = lines[0]
                t_start_s, t_end_s = lines[1].split('-->')
                start_sec = parse_srt_timestamp(t_start_s)
                end_sec = parse_srt_timestamp(t_end_s)
                text = " ".join(lines[2:])
                entries.append({
                    "index": int(idx_str) if idx_str.isdigit() else len(entries) + 1,
                    "start": start_sec,
                    "end": end_sec,
                    "duration": max(0.05, end_sec - start_sec),
                    "text": text
                })
        return entries

    @classmethod
    def load_project(cls, project_dir: str = "project_content") -> Dict[str, Any]:
        """
        Dynamically scans project directory, discovers all images, subtitles,
        and assembles continuous audio with micro-exact word synchronization.
        """
        images_dir = os.path.join(project_dir, "images")
        audio_dir = os.path.join(project_dir, "audio")
        srt_dir = os.path.join(project_dir, "srt")

        # 1. Discover Images with Deterministic Story Ordering
        img_exts = ("*.png", "*.jpg", "*.jpeg", "*.webp")
        image_files = []
        for ext in img_exts:
            image_files.extend(glob.glob(os.path.join(images_dir, ext)))

        def story_sheet_sort_key(file_path: str) -> tuple:
            fname = os.path.basename(file_path).lower()
            # Explicit story ordering: Part 1 (المستوى التأسيسي) must precede Part 2 (ذكاء الشوارع)
            if any(k in fname for k in ('07_57_31', 'part1', 'sheet1', 'part_1', '1_')):
                return (1, fname)
            if any(k in fname for k in ('06_05_24', 'part2', 'sheet2', 'part_2', '2_')):
                return (2, fname)
            return (50, fname)

        image_files = sorted(image_files, key=story_sheet_sort_key)

        if not image_files:
            raise FileNotFoundError(f"No image files found in: {images_dir}")

        # 2. Discover SRT
        srt_files = glob.glob(os.path.join(srt_dir, "*.srt"))
        if not srt_files:
            raise FileNotFoundError(f"No SRT file found in: {srt_dir}")
        srt_path = srt_files[0]
        raw_srt_entries = cls.parse_srt_file(srt_path)

        # 3. Discover & Assemble Audio
        raw_audio_files = []
        for ext in ("*.wav", "*.m4a", "*.mp3", "*.aac"):
            raw_audio_files.extend(glob.glob(os.path.join(audio_dir, ext)))

        # Exclude previously generated master tracks
        source_audio_files = [f for f in raw_audio_files if "master" not in os.path.basename(f).lower()]
        source_audio_files = sorted(source_audio_files)

        if not source_audio_files:
            raise FileNotFoundError(f"No audio files found in: {audio_dir}")

        master_audio_path = os.path.join(audio_dir, "master_voiceover_concatenated.wav")

        if len(source_audio_files) == 1:
            master_audio_path = source_audio_files[0]
        else:
            # Concatenate all parts seamlessly using ffmpeg
            inputs = []
            filter_parts = []
            for i, af in enumerate(source_audio_files):
                inputs.extend(["-i", af])
                filter_parts.append(f"[{i}:a]")
            filter_str = f"{''.join(filter_parts)}concat=n={len(source_audio_files)}:v=0:a=1[aout]"
            cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_str, "-map", "[aout]", master_audio_path]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Measure audio duration
        with av.open(master_audio_path) as c:
            s = c.streams.audio[0]
            total_audio_sec = float(c.duration / 1_000_000.0) if c.duration else float(s.duration * s.time_base)
            sample_rate = s.rate
            channels = s.channels

        # 4. Synchronize SRT Timeline to Audio Duration
        raw_srt_dur = raw_srt_entries[-1]["end"] if raw_srt_entries else 1.0
        time_ratio = total_audio_sec / float(raw_srt_dur)

        scaled_srt_entries = []
        for entry in raw_srt_entries:
            st = round(entry["start"] * time_ratio, 3)
            en = round(entry["end"] * time_ratio, 3)
            scaled_srt_entries.append({
                "index": entry["index"],
                "start": st,
                "end": en,
                "duration": round(en - st, 3),
                "text": entry["text"]
            })

        return {
            "project_dir": project_dir,
            "images": image_files,
            "image_count": len(image_files),
            "master_audio_path": master_audio_path,
            "audio_duration": total_audio_sec,
            "audio_sample_rate": sample_rate,
            "audio_channels": channels,
            "srt_path": srt_path,
            "word_count": len(scaled_srt_entries),
            "srt_entries": scaled_srt_entries,
            "time_scale_ratio": time_ratio
        }
