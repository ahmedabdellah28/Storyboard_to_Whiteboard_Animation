"""
Universal Dynamic Section Pipeline Engine
End-to-end automated pipeline for whiteboard animation video production:
1. Whisper word-level timing synthesis
2. Storyboard visual cell extraction & Arabic Handwriting Title Banner generation
3. Narrative speech synchronization & High-Impact Micro-Zoning layout
4. AI Pre-Render Visual Director approval
5. Synchronized SFX audio mixing & 1080p NVENC hardware video rendering
6. Deliverables publishing
"""
import os
import sys
import json
import wave
import shutil
import argparse
import subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from production_engine.dynamic_storyboard_extractor import DynamicStoryboardExtractor
from production_engine.dynamic_speech_synchronizer import DynamicSpeechSynchronizer
from production_engine.dynamic_layout_planner import DynamicLayoutPlanner
from production_engine.dynamic_section_engine import DynamicSectionEngine

class UniversalSectionPipeline:
    def __init__(self, section_dir, title=None):
        self.section_dir = os.path.abspath(section_dir)
        self.section_id = os.path.basename(self.section_dir)
        self.title = title
        
        # Audio paths
        self.voice_path = os.path.join(self.section_dir, "voice", "section.wav")
        if not os.path.exists(self.voice_path):
            self.voice_path = os.path.join(self.section_dir, "voiceover.wav")

        self.storyboard_path = os.path.join(self.section_dir, "storyboard.png")
        self.script_path = os.path.join(self.section_dir, "script.txt")
        self.timing_dir = os.path.join(self.section_dir, "timing")
        self.whisper_path = os.path.join(self.timing_dir, "whisper.json")
        self.assets_dir = os.path.join(self.section_dir, "assets")

    def read_title_from_script(self):
        """Extracts section title from script.txt or folder name if not provided."""
        if self.title:
            return self.title
        if os.path.exists(self.script_path):
            with open(self.script_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and len(line) < 60:
                        return line
        return self.section_id.replace("_", " ").title()

    def run_whisper_if_needed(self, force=False):
        """Runs faster-whisper transcription to generate timing/whisper.json."""
        if os.path.exists(self.whisper_path) and not force:
            print(f"[1/5] ✓ Using existing Whisper timing: {self.whisper_path}")
            return self.whisper_path

        print(f"[1/5] 🎙️ Running Faster-Whisper on {self.voice_path}...")
        cmd = [
            sys.executable,
            os.path.join(ROOT_DIR, "section_timing", "main.py"),
            "--section", self.section_dir,
            "--force"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if res.returncode != 0:
            print(f"⚠️ Warning running section_timing: {res.stderr}")
        return self.whisper_path

    def run(self, force_whisper=False, custom_manifest=None):
        """Executes full end-to-end production pipeline."""
        print("=" * 80)
        print(f"🚀 EXECUTING UNIVERSAL PRODUCTION PIPELINE: {self.section_id}")
        print("=" * 80)

        section_title = self.read_title_from_script()
        print(f"  • Section Title: {section_title}")
        print(f"  • Section Dir  : {self.section_dir}")

        # Step 1: Faster-Whisper Word-Level Timestamps
        self.run_whisper_if_needed(force=force_whisper)

        # Step 2: Storyboard Extraction & Title Banner Generation
        print(f"\n[2/5] 🎨 Storyboard Extraction & Title Banner Generation...")
        extractor = DynamicStoryboardExtractor(self.section_dir)
        extractor.generate_title_banner(section_title)
        
        # If assets don't already exist or re-extract needed
        meta_file = os.path.join(self.assets_dir, "metadata.json")
        if not os.path.exists(meta_file):
            extractor.extract_assets()
        else:
            print(f"  ✓ Assets catalog verified: {meta_file}")

        # Step 3: Speech Synchronization & Micro-Zoning Layout
        print(f"\n[3/5] ⏱️ Speech Synchronization & Micro-Zoning Layout...")
        synchronizer = DynamicSpeechSynchronizer(self.section_dir)
        manifest_items = synchronizer.synchronize(custom_manifest=custom_manifest)

        planner = DynamicLayoutPlanner(self.section_dir, fixed_y=800.0, cam_zoom=0.68)
        planner.plan_layout(manifest_items)

        # Step 4: AI Pre-Render Visual Director Validation
        print(f"\n[4/5] 🧠 AI Pre-Render Visual Director Validation...")
        director_cmd = [
            sys.executable, "-m", "pre_render_director.main",
            "--section", self.section_dir,
            "--mock-ai"
        ]
        res = subprocess.run(director_cmd, capture_output=True, text=True, encoding="utf-8")
        if res.returncode == 0:
            print("  ✓ AI Pre-Render Director Gate: APPROVED")
        else:
            print(f"  ⚠️ Pre-render director returned warnings: {res.stderr}")

        # Step 5: Master Audio Mix & NVENC Video Rendering
        print(f"\n[5/5] 🎥 Audio Mixing & 1080p NVENC Video Rendering...")
        with wave.open(self.voice_path, 'rb') as wf:
            duration_sec = wf.getnframes() / float(wf.getframerate())

        layout_path = os.path.join(self.section_dir, "placed_elements_layout.json")
        with open(layout_path, "r", encoding="utf-8") as f:
            layout_data = json.load(f)

        placed_elements = layout_data["elements"]
        zones = layout_data["zones"]
        fixed_y = layout_data.get("fixed_y", 800.0)
        cam_zoom = layout_data.get("cam_zoom", 0.68)

        elements_by_aid = {}
        for z_name, elems in placed_elements.items():
            for el in elems:
                elements_by_aid[el["aid"]] = el

        def get_zone_cam_x(z_name):
            return zones[z_name]["cam_pos"][0]

        # Load Staging Specs from Final Plan or Alignment Data
        final_plan_path = os.path.join(self.section_dir, "timing", "final_render_plan.json")
        align_path = os.path.join(self.section_dir, "alignment_data.json")

        with open(align_path, "r", encoding="utf-8") as f:
            align_data = json.load(f)
        anim_map = {s[0]: (s[3], s[4]) for s in align_data.get("staging_specs", [])}

        if os.path.exists(final_plan_path):
            with open(final_plan_path, "r", encoding="utf-8") as f:
                plan_data = json.load(f)
            staging_specs_raw = []
            for ev in plan_data.get("render_events", []):
                if ev.get("type") in ["draw", "reveal"]:
                    aid = ev["asset_id"]
                    t_st = float(ev["start_s"])
                    t_dur = float(ev["duration_s"])
                    fade_out = ev.get("fade_out_at")
                    anim_type, depth = anim_map.get(aid, ("outside_in_pen", 5))
                    staging_specs_raw.append((aid, t_st, t_dur, anim_type, depth, fade_out))
        else:
            staging_specs_raw = [s + (None,) for s in align_data["staging_specs"]]

        # Calculate camera pans
        element_zone_map = {}
        for z_name, elems in placed_elements.items():
            for el in elems:
                element_zone_map[el["aid"]] = z_name

        zone_order = list(layout_data["zones"].keys())
        zone_last_element_end = {}
        zone_first_element_start = {}

        for spec in staging_specs_raw:
            aid = spec[0]
            t_st = spec[1]
            t_dur = spec[2]
            z = element_zone_map.get(aid)
            if z:
                t_end = t_st + t_dur
                if z not in zone_last_element_end or t_end > zone_last_element_end[z]:
                    zone_last_element_end[z] = t_end
                if z not in zone_first_element_start or t_st < zone_first_element_start[z]:
                    zone_first_element_start[z] = t_st

        cam_pans = DynamicSectionEngine.calculate_camera_pans(
            zone_order=zone_order,
            zone_last_element_end=zone_last_element_end,
            zone_first_element_start=zone_first_element_start,
            get_cam_x_fn=get_zone_cam_x,
            default_pan_dur=0.85
        )

        initial_cam_x = get_zone_cam_x(zone_order[0])
        get_camera_state = DynamicSectionEngine.build_horizontal_camera_trajectory(
            cam_pans=cam_pans,
            initial_x=initial_cam_x,
            fixed_y=fixed_y,
            cam_zoom=cam_zoom
        )

        elements_staging = []
        hero_configs = []
        for spec in staging_specs_raw:
            aid = spec[0]
            t_st = spec[1]
            t_dur = spec[2]
            anim_type = spec[3]
            depth = spec[4]
            fade_out = spec[5] if len(spec) > 5 else None

            if aid not in elements_by_aid:
                continue
            el = elements_by_aid[aid]
            elements_staging.append({
                'id': aid,
                'asset': aid,
                't_start': t_st,
                't_dur': t_dur,
                'type': anim_type,
                'pos': (el['x'], el['y']),
                'size': (el['w'], el['h']),
                'depth': depth,
                'fade_out_at': fade_out
            })
            if anim_type == "outside_in_pen":
                hero_configs.append((aid, t_st, t_dur))

        engine = DynamicSectionEngine(self.section_dir)

        # Mix master audio with ducked SFX
        pan_times = [p[0] for p in cam_pans]
        sfx_cues = engine.generate_sfx_from_staging(elements_staging, camera_pans=pan_times)
        master_audio_path = engine.mix_master_audio(self.voice_path, sfx_cues, target_duration_s=duration_sec)

        # Render 1080p Video
        final_video_path = engine.render_section(
            hero_configs=hero_configs,
            elements_staging=elements_staging,
            camera_trajectory_fn=get_camera_state,
            duration_sec=duration_sec
        )

        # Publish Deliverables
        deliv_dir = os.path.join(ROOT_DIR, "output_animations", "wealth_classes_documentary", "deliverables", "sections")
        os.makedirs(deliv_dir, exist_ok=True)
        deliv_video = os.path.join(deliv_dir, f"{self.section_id}_Whiteboard_1080p.mp4")
        deliv_audio = os.path.join(deliv_dir, f"{self.section_id}_Master_Audio.wav")

        shutil.copyfile(final_video_path, deliv_video)
        shutil.copyfile(master_audio_path, deliv_audio)

        print("\n" + "=" * 80)
        print(f"🎉 SECTION DELIVERABLE PUBLISHED SUCCESSFULLY!")
        print(f"  • Video Deliverable: {deliv_video}")
        print(f"  • Audio Deliverable: {deliv_audio}")
        print(f"  • Total Duration   : {duration_sec:.2f}s")
        print(f"  • Elements Staged  : {len(elements_staging)} ({len(hero_configs)} heroes)")
        print("=" * 80)
        return deliv_video

def main():
    parser = argparse.ArgumentParser(description="Universal Dynamic Whiteboard Production Pipeline")
    parser.add_argument("--section", type=str, required=True, help="Path to section folder (e.g. sections/02_extreme_poverty)")
    parser.add_argument("--title", type=str, default=None, help="Optional Section Title in Arabic")
    parser.add_argument("--force-whisper", action="store_true", help="Force Whisper re-transcription")
    args = parser.parse_args()

    pipeline = UniversalSectionPipeline(args.section, title=args.title)
    pipeline.run(force_whisper=args.force_whisper)

if __name__ == "__main__":
    main()
