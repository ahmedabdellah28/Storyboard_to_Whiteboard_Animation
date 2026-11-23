import subprocess
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


ROOT_DIR = Path(r"E:\image_to_animate")
EXPORTS_DIR = ROOT_DIR / "projects" / "ottoman_sultans" / "exports"
FRAMES_DIR = ROOT_DIR / "projects" / "ottoman_sultans" / "exports" / "shorts_preview_frames"
FRAMES_DIR.mkdir(parents=True, exist_ok=True)

shorts = ["short_01", "short_02", "short_03"]

for s in shorts:
    mp4_path = EXPORTS_DIR / f"{s}_master.mp4"
    print(f"\n=================== PROBING {s.upper()} ===================")
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=width,height,r_frame_rate,duration,codec_name",
        "-of", "json",
        str(mp4_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    probe = json.loads(res.stdout)
    for st in probe.get("streams", []):
        print(f"Stream ({st.get('codec_name')}): {st.get('width', 'N/A')}x{st.get('height', 'N/A')} | FPS: {st.get('r_frame_rate', 'N/A')} | Duration: {st.get('duration', 'N/A')}s")
        
    # Extract 3 sample frames per short
    timestamps = [5.0, 18.0, 29.0] if s != "short_03" else [6.0, 20.0, 38.0, 48.0]
    for t in timestamps:
        frame_out = FRAMES_DIR / f"{s}_frame_{int(t)}s.png"
        f_cmd = [
            "ffmpeg", "-y", "-ss", str(t), "-i", str(mp4_path),
            "-vframes", "1", "-q:v", "2", str(frame_out)
        ]
        subprocess.run(f_cmd, capture_output=True)
        if frame_out.exists():
            print(f"  📸 Extracted frame at {t}s -> {frame_out.name} ({frame_out.stat().st_size / 1024:.1f} KB)")
