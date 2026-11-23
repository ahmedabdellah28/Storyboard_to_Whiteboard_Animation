import json
from pathlib import Path
from typing import Dict, Any
from ..timeline.models import MasterTimeline

class TimingDebugger:
    """Produces detailed diagnostic reports and standalone HTML timeline visualizations."""
    
    @staticmethod
    def generate_debug_report(timing_dir: Path | str, master: MasterTimeline) -> Path:
        timing_dir = Path(timing_dir)
        report_file = timing_dir / "debug_report.json"

        # Correlate sentences with drawing and sfx events
        sentence_diagnostics = []
        for s in master.sentences:
            s_drawings = [
                d.model_dump() for d in master.drawings
                if (d.start_s >= s.start - 0.5 and d.start_s <= s.end + 0.5)
            ]
            s_pauses = [
                p.model_dump() for p in master.pauses
                if (p.start >= s.start and p.end <= s.end + 0.5)
            ]
            s_sfx = [
                sx.model_dump() for sx in master.sfx
                if (sx.start_s >= s.start - 0.5 and sx.start_s <= s.end + 0.5)
            ]

            sentence_diagnostics.append({
                "sentence_id": s.id,
                "text": s.text,
                "start": s.start,
                "end": s.end,
                "duration": s.duration,
                "words_count": len(s.word_ids),
                "pauses_count": len(s_pauses),
                "drawings": s_drawings,
                "sfx": s_sfx
            })

        summary = {
            "section_id": master.section_id,
            "duration": master.duration,
            "words_total": len(master.words),
            "sentences_total": len(master.sentences),
            "pauses_total": len(master.pauses),
            "drawings_total": len(master.drawings),
            "sfx_total": len(master.sfx),
            "camera_total": len(master.camera),
            "sentences": sentence_diagnostics
        }

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        # Generate HTML visualization
        html_file = timing_dir / "timeline_debug.html"
        TimingDebugger.generate_html_timeline(html_file, master)

        return report_file

    @staticmethod
    def generate_html_timeline(html_path: Path, master: MasterTimeline) -> None:
        """Generates a responsive visual track viewer for browser inspection."""
        dur = max(1.0, master.duration)
        
        def pct(s: float) -> str:
            return f"{(s / dur) * 100:.2f}%"

        def width_pct(s: float, e: float) -> str:
            return f"{max(0.2, ((e - s) / dur) * 100):.2f}%"

        html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"/>
<title>Timeline Debug — Section {master.section_id}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; margin: 0; }}
  h1 {{ font-size: 20px; color: #38bdf8; margin-bottom: 8px; }}
  .meta {{ color: #94a3b8; font-size: 13px; margin-bottom: 24px; }}
  .timeline-container {{ background: #1e293b; border-radius: 8px; padding: 16px; border: 1px solid #334155; position: relative; }}
  .track {{ position: relative; height: 36px; margin-bottom: 12px; background: #0f172a; border-radius: 6px; }}
  .track-label {{ position: absolute; left: 12px; top: 8px; font-size: 11px; font-weight: bold; color: #64748b; z-index: 10; text-transform: uppercase; }}
  .block {{ position: absolute; height: 100%; border-radius: 4px; font-size: 10px; display: flex; align-items: center; justify-content: center; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; padding: 0 4px; box-sizing: border-box; cursor: pointer; transition: transform 0.1s; }}
  .block:hover {{ transform: scaleY(1.15); z-index: 20; }}
  .sentence {{ background: #2563eb; color: #fff; }}
  .word {{ background: #38bdf8; color: #0f172a; opacity: 0.85; border: 1px solid #0284c7; }}
  .pause {{ background: #f59e0b; color: #0f172a; font-weight: bold; }}
  .drawing {{ background: #10b981; color: #0f172a; font-weight: bold; border: 1px solid #059669; }}
  .sfx {{ background: #ec4899; color: #fff; font-weight: bold; }}
  .camera {{ background: #8b5cf6; color: #fff; }}
</style>
</head>
<body>
  <h1>🎬 Timeline Inspector — Section {master.section_id}</h1>
  <div class="meta">Duration: {master.duration:.2f}s | Words: {len(master.words)} | Drawings: {len(master.drawings)} | SFX: {len(master.sfx)}</div>
  
  <div class="timeline-container">
    <!-- Sentences -->
    <div class="track">
      <span class="track-label">Sentences</span>
      {"".join([f'<div class="block sentence" style="left:{pct(s.start)};width:{width_pct(s.start, s.end)}" title="{s.text} ({s.start}s - {s.end}s)">{s.text[:20]}</div>' for s in master.sentences])}
    </div>

    <!-- Words -->
    <div class="track">
      <span class="track-label">Words</span>
      {"".join([f'<div class="block word" style="left:{pct(w.start)};width:{width_pct(w.start, w.end)}" title="{w.text} ({w.start}s - {w.end}s)">{w.text}</div>' for w in master.words])}
    </div>

    <!-- Pauses -->
    <div class="track">
      <span class="track-label">Pauses</span>
      {"".join([f'<div class="block pause" style="left:{pct(p.start)};width:{width_pct(p.start, p.end)}" title="{p.type} ({p.duration}s)">{p.duration}s</div>' for p in master.pauses])}
    </div>

    <!-- Drawings -->
    <div class="track">
      <span class="track-label">Drawings</span>
      {"".join([f'<div class="block drawing" style="left:{pct(d.start_s)};width:{width_pct(d.start_s, d.end_s)}" title="{d.asset_id} [{d.type}] ({d.start_s}s - {d.end_s}s)">{d.asset_id}</div>' for d in master.drawings])}
    </div>

    <!-- SFX -->
    <div class="track">
      <span class="track-label">SFX</span>
      {"".join([f'<div class="block sfx" style="left:{pct(sx.start_s)};width:{width_pct(sx.start_s, sx.end_s)}" title="{sx.type} ({sx.start_s}s)">{sx.type}</div>' for sx in master.sfx])}
    </div>

    <!-- Camera -->
    <div class="track">
      <span class="track-label">Camera</span>
      {"".join([f'<div class="block camera" style="left:{pct(c.start_s)};width:{width_pct(c.start_s, c.end_s)}" title="{c.type} ({c.start_s}s - {c.end_s}s)">{c.type}</div>' for c in master.camera])}
    </div>
  </div>
</body>
</html>
"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
