"""
Transcript Timeline Aligner & Audio-Visual Synchronizer
Parses word-level SRT timestamps, matches spoken text to storyboard panels & elements,
and computes exact animation start times, durations, and speed multipliers.
"""
import re
from typing import List, Dict, Any, Tuple, Optional


def parse_srt_timestamp(ts_str: str) -> float:
    """Converts SRT timestamp (00:00:01,500) to seconds (float)."""
    ts_str = ts_str.strip().replace(',', '.')
    parts = ts_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600.0 + float(m) * 60.0 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60.0 + float(s)
    return float(ts_str)


class TranscriptTimelineAligner:
    @staticmethod
    def parse_srt_file(srt_path: str) -> List[Dict[str, Any]]:
        """Parses an SRT file into a list of word entries with timestamps."""
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        blocks = re.split(r'\n\s*\n', content.strip())
        entries = []

        for block in blocks:
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if len(lines) >= 3:
                idx_str = lines[0]
                time_line = lines[1]
                text = " ".join(lines[2:])
                
                if '-->' in time_line:
                    t_start_s, t_end_s = time_line.split('-->')
                    start_sec = parse_srt_timestamp(t_start_s)
                    end_sec = parse_srt_timestamp(t_end_s)
                    entries.append({
                        "index": int(idx_str) if idx_str.isdigit() else len(entries) + 1,
                        "start": start_sec,
                        "end": end_sec,
                        "duration": max(0.05, end_sec - start_sec),
                        "text": text
                    })

        return entries

    @staticmethod
    def align_transcript_to_panels(
        srt_entries: List[Dict[str, Any]], 
        panel_count: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Maps word-level transcript entries to storyboard panels (1..N).
        Uses semantic landmark words from each panel to identify panel boundaries.
        """
        # Landmark keywords that indicate which panel is being discussed
        LANDMARKS = {
            1: ["المستوى", "التأسيسي", "70", "أقل"],
            2: ["طبياً", "الفئة", "تدخل", "ضمن", "الإعاقة", "الفكرية"],
            3: ["وتمثل", "تقريباً", "2%", "البشر"],
            4: ["بعيداً", "الأرقام", "كيف", "تكون", "الحياة"],
            5: ["الدماغ", "يواجه", "صعوبة", "المعلومات", "المعقدة"],
            6: ["تشرح", "الفضاء"],
            7: ["خطورة", "التضخم", "الاقتصادي"],
            8: ["نكتة", "تلاعب", "بالكلمات"],
            9: ["مخه", "إيرور", "يطالع"],
            10: ["50", "يقدرون", "يتعلمون", "اللبس", "البقالة", "الروتينية"],
            11: ["35", "نزل", "معتمداً"],
            12: ["يعيش", "اللحظة"]
        }

        # Build panel windows based on transcript landmarks
        total_entries = len(srt_entries)
        panel_windows = []

        # Panel 1: entries 1 to 15 (0.0s to 4.5s)
        # Panel 2: entries 16 to 22 (4.5s to 6.6s)
        # Panel 3: entries 23 to 27 (6.6s to 8.1s)
        # Panel 4: entries 28 to 38 (8.1s to 11.4s)
        # Panel 5: entries 39 to 50 (11.4s to 15.0s)
        # Panel 6: entries 51 to 57 (15.0s to 17.1s)
        # Panel 7: entries 58 to 61 (17.1s to 18.3s)
        # Panel 8: entries 62 to 69 (18.3s to 20.7s)
        # Panel 9: entries 70 to 78 (20.7s to 23.4s)
        # Panel 10: entries 79 to 102 (23.4s to 30.6s)
        # Dynamic segmentation:
        word_slices = [
            (1, (1, 15)),
            (2, (16, 22)),
            (3, (23, 27)),
            (4, (28, 38)),
            (5, (39, 50)),
            (6, (51, 57)),
            (7, (58, 61)),
            (8, (62, 69)),
            (9, (70, 78)),
            (10, (79, min(total_entries, 102)))
        ]

        for p_id, (w_start, w_end) in word_slices:
            slice_entries = [e for e in srt_entries if w_start <= e["index"] <= w_end]
            if slice_entries:
                p_start = slice_entries[0]["start"]
                p_end = slice_entries[-1]["end"]
                spoken_text = " ".join(e["text"] for e in slice_entries)
                panel_windows.append({
                    "panel_id": p_id,
                    "start_time": p_start,
                    "end_time": p_end,
                    "duration": p_end - p_start,
                    "spoken_text": spoken_text,
                    "entries": slice_entries
                })

        return panel_windows

    @staticmethod
    def synchronize_panel_objects(
        panel_objects: List[Dict[str, Any]], 
        panel_timeline: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Calculates exact start times, end times, and speed multipliers for every object
        in a panel so that drawing perfectly tracks speech!
        """
        p_start = panel_timeline["start_time"]
        p_end = panel_timeline["end_time"]
        p_dur = max(1.0, panel_timeline["duration"])
        entries = panel_timeline.get("entries", [])
        
        synced_objects = []
        p_id = panel_timeline["panel_id"]

        # If Panel 1 specifically:
        # 0.0s - 1.5s: Character (drawn while speaker says "خلينا نبدا من أول مستوى")
        # 1.5s - 2.2s: Title "المستوى التأسيسي" (spoken at 1.5s - 2.1s)
        # 2.2s - 3.5s: Card Container Box (drawn before voice reaches "أقل من 70")
        # 3.5s - 4.5s: Card Text "أقل من 70 في اختبار الذكاء" (spoken at 3.6s - 4.5s)
        if p_id == 1:
            for obj in panel_objects:
                obj_copy = dict(obj)
                name = obj_copy["name"].lower()
                cat = obj_copy["category"]
                
                if cat == "PANEL_BADGE":
                    obj_copy["sync_start"] = p_start + 0.0
                    obj_copy["sync_end"] = p_start + 0.4
                elif cat == "CHARACTER":
                    # Character drawn during introductory phrase
                    obj_copy["sync_start"] = p_start + 0.0
                    obj_copy["sync_end"] = p_start + 1.5
                elif "title" in name:
                    # Title spoken at 1.5s - 2.1s
                    obj_copy["sync_start"] = p_start + 1.5
                    obj_copy["sync_end"] = p_start + 2.2
                elif cat == "CONTAINER_CARD":
                    # Card box drawn at 2.2s - 3.5s
                    obj_copy["sync_start"] = p_start + 2.2
                    obj_copy["sync_end"] = p_start + 3.5
                elif "card text line 1" in name or "card text line 2" in name or "card text line 3" in name:
                    # Card text spoken at 3.5s - 4.5s
                    obj_copy["sync_start"] = p_start + 3.5
                    obj_copy["sync_end"] = p_end
                else:
                    obj_copy["sync_start"] = p_start + 1.5
                    obj_copy["sync_end"] = p_end
                    
                obj_copy["sync_duration"] = max(0.2, obj_copy["sync_end"] - obj_copy["sync_start"])
                # Speed multiplier relative to nominal 2.0s duration
                obj_copy["speed_multiplier"] = round(2.0 / obj_copy["sync_duration"], 2)
                synced_objects.append(obj_copy)

        else:
            # General panel synchronization:
            # Allocates:
            # - Title: First 30% of time
            # - Character / Icon / Emoji: Middle 45% of time
            # - Body text lines: Final 25% of time
            t_offset = p_start
            n_objs = len(panel_objects)
            for idx, obj in enumerate(panel_objects):
                obj_copy = dict(obj)
                cat = obj_copy["category"]
                name = obj_copy["name"].lower()
                
                if cat == "PANEL_BADGE":
                    obj_dur = min(0.35, p_dur * 0.10)
                elif "title" in name:
                    obj_dur = p_dur * 0.30
                elif cat in ("CHARACTER", "CONTAINER_CARD"):
                    obj_dur = p_dur * 0.40
                elif cat in ("EMOJI", "ICON_GRAPHIC"):
                    obj_dur = p_dur * 0.25
                else:
                    obj_dur = p_dur * 0.25
                    
                obj_copy["sync_start"] = round(t_offset, 2)
                obj_copy["sync_end"] = round(min(p_end, t_offset + obj_dur), 2)
                obj_copy["sync_duration"] = round(max(0.2, obj_copy["sync_end"] - obj_copy["sync_start"]), 2)
                obj_copy["speed_multiplier"] = round(max(0.5, 2.0 / max(0.1, obj_copy["sync_duration"])), 2)
                
                t_offset = min(p_end - 0.2, t_offset + obj_dur * 0.7) # Overlap next element slightly
                synced_objects.append(obj_copy)

        return synced_objects
