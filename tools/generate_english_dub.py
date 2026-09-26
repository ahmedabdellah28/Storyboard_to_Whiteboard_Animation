"""
Professional English Dubbing Engine for Wealth Classes Documentary
Generates synchronized, broadcast-quality English narration for all 11 sections:
1. 00_Hook
2. 01_Homeless
3. 02_Extreme_Poverty
4. 03_Working_Poor
5. 04_Lower_Middle_Class
6. 05_Middle_Class
7. 06_Upper_Middle_Class
8. 07_Comfortable_Rich
9. 08_Ultra_Wealthy
10. 10_Islamic_Perspective
11. 11_Outro

Features:
- Eloquent, cinematic documentary English adaptation
- Precise per-chapter duration matching to the millisecond
- Gemini TTS (gemini-3.1-flash-tts-preview) with Fenrir documentary voice
- Audio ducking & mixing with whiteboard drawing SFX & ambiance
- Full master video compilation with English audio
"""
import os
import sys
import json
import time
import wave
import shutil
import subprocess
from typing import Dict, List, Tuple

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from voice_studio.engine import VoiceStudioEngine
from voice_studio.profiles import AudioProfile, DirectorNote

SECTIONS_DIR = os.path.join(ROOT_DIR, "output_animations", "wealth_classes_documentary", "deliverables", "sections")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output_animations", "wealth_classes_documentary", "deliverables")
CACHE_DIR = os.path.join(ROOT_DIR, "scratch", "english_dub_chunks")
os.makedirs(CACHE_DIR, exist_ok=True)

# Master Section Specifications: (id, english_title, target_duration_sec, original_video_file, original_master_audio)
SECTIONS_CONFIG = [
    {
        "id": "00_Hook",
        "title": "The Hook: How Wealth Shapes Reality",
        "target_dur": 36.333,
        "vid_file": "00_Hook_Whiteboard_1080p.mp4",
        "aud_file": "00_Hook_Master_Audio.wav",
        "script": """Imagine waking up before dawn—not for work, not for a flight, nor the gym.
You wake up because the street is stirring, and you must find safe ground before the morning rush.
Now imagine that same morning in a small room... a tidy apartment... a comfortable house... an upscale villa... and an estate managed by a private staff.
Same day. Same twenty-four hours.
Yet every financial tier completely reshapes your time, your health, and the burdens you bear alone.
Today, we walk through an entire day—from having no roof over your head, to commanding billions.
The question isn't who has more money.
It's: How does human life itself transform when your wealth class changes?"""
    },
    {
        "id": "01_Homeless",
        "title": "Tier 1: Homelessness (Living Hour by Hour)",
        "target_dur": 130.800,
        "vid_file": "01_Homeless_Whiteboard_1080p.mp4",
        "aud_file": "01_Homeless_Master_Audio.wav",
        "script": """Tier One: Homelessness.
You wake up on a cold sidewalk or an alleyway bench.
No alarm clock—you're jolted awake by street sweepers, freezing concrete, or police asking you to move.
Your body aches from shivering.
Before anything else, you check your belongings: your backpack, your shoes. On the street, if you lose your bag, you lose your entire life.
Basic hygiene is an ordeal. You search for a public restroom, wash your face with cold sink water, and try to look presentable so you aren't kicked out.
Breakfast isn't about choice; it's about whatever is available. A cup of coffee from a volunteer, a food bank voucher, or counting a few loose coins.
Your day isn't scheduled around goals or careers. It's scheduled around survival.
Where can you charge your phone? Where can you sit without being chased away?
Constant hyper-vigilance wears you down. You can never truly relax, because vulnerability is dangerous.
Healthcare is non-existent until a condition becomes life-threatening and requires an emergency room.
As evening approaches, the real anxiety begins: Where will you sleep tonight?
Waiting in line for an overcrowded shelter, or hunting for a sheltered doorway hidden from the wind.
You lie down exhausted, your mind replaying the same loop.
Here, life isn't measured in years or months. It is survived hour by hour."""
    },
    {
        "id": "02_Extreme_Poverty",
        "title": "Tier 2: Extreme Poverty (The Suffocating Scarcity)",
        "target_dur": 106.600,
        "vid_file": "02_Extreme_Poverty_Whiteboard_1080p.mp4",
        "aud_file": "02_Extreme_Poverty_Master_Audio.wav",
        "script": """Tier Two: Extreme Poverty.
You have a roof, but stability remains an illusion.
You wake up in a cramped, damp room. A thin mattress on the floor, peeling paint, and cold drafts through cracked windows.
Your first thought isn't what to eat—it's whether the power is still on.
Every single day is a calculation of trade-offs: pay the electricity bill, or buy groceries for the kids?
Breakfast is minimal: bread, cheap tea, or leftovers stretched to the limit.
Getting to work is an exhausting mission. Long waits for unreliable public transit, walking miles in worn-out shoes to save bus fare.
Work is precarious, underpaid, and physically taxing, with zero benefits or job security.
A single sudden expense—a broken heater, a child's fever—triggers an instant crisis.
You borrow from neighbors, visit loan sharks, or juggle debts just to make it to next week.
Chronic financial scarcity consumes your mental bandwidth. Studies show poverty acts like cognitive tunnel vision; you have no space left to plan ahead.
At night, you turn off the lights to save power and fall asleep anxious.
Tomorrow offers no relief—only another day of pure endurance."""
    },
    {
        "id": "03_Working_Poor",
        "title": "Tier 3: The Working Poor (The Endless Grind)",
        "target_dur": 93.533,
        "vid_file": "03_Working_Poor_Whiteboard_1080p.mp4",
        "aud_file": "03_Working_Poor_Master_Audio.wav",
        "script": """Tier Three: The Working Poor.
You work relentlessly, yet you never seem to get ahead.
Multiple alarms wake you after five hours of sleep. You rush to catch early morning buses or drive a beat-up car that makes ominous engine noises.
You juggle two jobs or endless overtime: cleaning offices, cashier shifts, food delivery in the heat.
On paper, you have an income. In reality, the paycheck vanishes the moment it hits your account.
Rent takes half. Groceries, utilities, and transport consume the rest. Zero savings remain.
You dread unexpected emergencies. A flat tire or a broken tooth feels like a financial catastrophe.
Healthcare is delayed; you take over-the-counter painkillers and hope the problem goes away.
You return home late, physically drained, with barely enough energy to heat frozen food or spend ten minutes with your family.
You lie in bed knowing you must repeat the entire grind tomorrow.
You aren't destitute, but you are trapped on a treadmill running at full speed just to stay in the exact same place."""
    },
    {
        "id": "04_Lower_Middle_Class",
        "title": "Tier 4: Lower Middle Class (Fragile Stability)",
        "target_dur": 83.633,
        "vid_file": "04_Lower_Middle_Class_Whiteboard_1080p.mp4",
        "aud_file": "04_Lower_Middle_Class_Master_Audio.wav",
        "script": """Tier Four: The Lower Middle Class.
Here, daily life starts feeling noticeably calmer.
You wake up in a modest two-bedroom apartment. The space is clean, simple, and organized.
On the refrigerator, a pinned calendar tracks bill deadlines and grocery budgets.
You drive an older, reliable used car. You keep up with oil changes, but major repairs are planned months in advance.
Your job provides a steady salary and basic health insurance.
You shop with discount apps, hunt for supermarket deals, and pack home-cooked lunches for work.
A weekend family outing to a park or a casual pizza night is affordable and enjoyed.
Yet, financial margin remains narrow. You have a modest emergency fund of a thousand dollars, but high credit card debt or a sudden layoff could wipe it out in weeks.
You sleep with a sense of accomplishment, knowing you've built a real home, while constantly watching the horizon to protect it."""
    },
    {
        "id": "05_Middle_Class",
        "title": "Tier 5: The Middle Class (The Foundation of Stability)",
        "target_dur": 96.800,
        "vid_file": "05_Middle_Class_Whiteboard_1080p.mp4",
        "aud_file": "05_Middle_Class_Master_Audio.wav",
        "script": """Tier Five: The Middle Class.
Life enters genuine stability.
You wake up in a comfortable three-bedroom home in a safe neighborhood.
A modern kitchen, a coffee machine brewing, and children getting ready for school.
You drive a dependable mid-sized sedan with manageable monthly payments.
You work a corporate or professional career with regular hours, paid vacation, and health insurance.
Groceries are bought without agonizing over price tags, and you dine out on weekends without guilt.
Your children participate in sports, music lessons, and summer camps.
You have three to six months of emergency savings tucked away in a high-yield account, and your retirement portfolio grows quietly in the background.
Yet, the golden handcuffs are real. Your entire lifestyle depends on keeping your current salary.
You balance a mortgage, car loans, and college funds.
You enjoy real comfort and security, but walking away from the corporate ladder isn't an option."""
    },
    {
        "id": "06_Upper_Middle_Class",
        "title": "Tier 6: Upper Middle Class (Affluence & Outsourcing)",
        "target_dur": 79.233,
        "vid_file": "06_Upper_Middle_Class_Whiteboard_1080p.mp4",
        "aud_file": "06_Upper_Middle_Class_Master_Audio.wav",
        "script": """Tier Six: The Upper Middle Class.
You wake up in a spacious custom home in a prime neighborhood.
Smart thermostats adjust during the night, and a robot vacuum glides through the hallway.
You work a senior executive role, a specialized medical career, or run a thriving consulting practice.
You have substantial control over your schedule and work from home whenever you choose.
Time becomes your most valuable currency.
You hire a weekly cleaning service and a professional landscaper—not as a luxury, but because your working hours are worth far more.
All routine bills are on autopay, with substantial monthly transfers flowing directly into index funds and retirement accounts.
Healthcare is top-tier: preventative screenings, specialist visits, and private clinics.
Vacations are booked months ahead: comfortable flights, boutique hotels, and zero budget panic.
You go to sleep feeling deeply secure, knowing the future is well-guarded."""
    },
    {
        "id": "07_Comfortable_Rich",
        "title": "Tier 7: Comfortable Rich (The Quiet Millionaire)",
        "target_dur": 94.100,
        "vid_file": "07_Comfortable_Rich_Whiteboard_1080p.mp4",
        "aud_file": "07_Comfortable_Rich_Master_Audio.wav",
        "script": """Tier Seven: The Comfortable Rich.
A multimillionaire, yet your life isn't about flashy display.
You wake up in a peaceful home you fully own in a premier neighborhood, with the mortgage virtually paid off.
You have a dedicated home office, guest suites, and automated smart-security systems.
Housekeeping and landscaping teams manage all domestic maintenance. You aren't buying status—you're buying back your time.
Your wealth is diversified across paid real estate, retirement funds, stock portfolios, and private business equity.
A major financial emergency fund and an experienced CPA handle tax strategy and wealth preservation.
Your luxury SUV is paid in full. If a phone breaks, you replace it that afternoon without checking your bank balance.
At work, you lead companies or direct clinics with near-total autonomy over your calendar.
Healthcare is proactive, private, and world-class.
You travel in premium class, support community causes, and fund elite private education.
At night, you review investment yields, approve reports, and sip coffee on the terrace at sunset.
You have the ultimate luxury: the headspace to design your future in total peace."""
    },
    {
        "id": "08_Ultra_Wealthy",
        "title": "Tier 8: Ultra Wealthy (Empires & Private Systems)",
        "target_dur": 99.533,
        "vid_file": "08_Ultra_Wealthy_Whiteboard_1080p.mp4",
        "aud_file": "08_Ultra_Wealthy_Master_Audio.wav",
        "script": """Tier Eight: The Ultra Wealthy.
You wake up in an estate or luxury penthouse where a private staff has been operating for hours.
Automated blinds rise silently. Your morning briefing arrives: market movements, board summaries, private flight manifests, and philanthropic updates.
A personal trainer meets you in your private gym, and a personal chef prepares breakfast.
Your wealth isn't held in bank accounts; it's an ecosystem of holding companies, commercial towers, private equity, and family offices.
You don't manage daily operations. You make high-leverage strategic decisions: acquisitions, venture funding, and major liquidations.
Private aviation removes all friction from travel. You fly across continents for a dinner meeting and return home the same night.
Philanthropy is conducted at institutional scale: funding hospital wings, university research centers, and global foundations.
Your estate runs seamlessly in your absence under a dedicated estate manager.
At this level, money ceases to be a constraint.
Your entire ecosystem exists to protect and leverage your single rarest asset: your focused time and vision."""
    },
    {
        "id": "10_Islamic_Perspective",
        "title": "A Moment of Reflection: True Wealth of the Soul",
        "target_dur": 49.900,
        "vid_file": "10_Islamic_Perspective_Whiteboard_1080p.mp4",
        "aud_file": "10_Islamic_Perspective_Master_Audio.wav",
        "script": """Here, we must pause for a deeper truth.
If we measure human life solely through financial net worth, we miss the heart of our existence.
In divine wisdom, sustenance is distributed with purpose beyond our comprehension.
Wealth is not a proof of divine honor, and poverty is not a sign of disgrace. Both are profound tests.
The wealthy are tested with gratitude, humility, and justice: how was it earned, and where was it spent?
The poor are tested with patience and dignity, promised great honor for their perseverance.
As the Prophet Muhammad, peace be upon him, taught:
True wealth is not an abundance of worldly goods; true wealth is the richness of the soul.
You can possess billions and harbor an anxious, impoverished heart.
Or live simply with a heart overflowing with peace, sleeping with tranquility no fortune can ever purchase."""
    },
    {
        "id": "11_Outro",
        "title": "Outro: The Shroud Has No Pockets",
        "target_dur": 34.400,
        "vid_file": "11_Outro_Whiteboard_1080p.mp4",
        "aud_file": "11_Outro_Master_Audio.wav",
        "script": """In the end, whether you slept on a cold sidewalk or a silk mattress, the reality remains unchanged.
The shroud has no pockets.
We leave this world exactly as we entered it, and everything we accumulate is fleeting.
May we be blessed with contentment, pure provision, and hearts anchored beyond material wealth.
Tell us in the comments below:
Which tier felt closest to genuine peace of mind and true balance?
Thank you for watching, and see you in the next documentary."""
    }
]

def synthesize_section_english(engine: VoiceStudioEngine, cfg: dict) -> Tuple[str, float]:
    """Synthesizes raw voiceover for a single section."""
    sec_id = cfg["id"]
    script = cfg["script"].strip()
    target_dur = cfg["target_dur"]
    
    out_wav = os.path.join(CACHE_DIR, f"{sec_id}_voice_raw.wav")
    chunks_sub = os.path.join(CACHE_DIR, f"chunks_{sec_id}")
    os.makedirs(chunks_sub, exist_ok=True)
    
    profile = AudioProfile(
        name="English Documentary Narrator",
        description="Authoritative, captivating, and measured English documentary narrator."
    )
    note = DirectorNote(
        style="Cinematic, articulate, engaging documentary delivery.",
        scene=f"Narrating {cfg['title']}.",
        sample_context="Deliver each phrase with natural documentary cadence and confident resonance."
    )
    
    print(f"\n🎙️ Synthesizing English Voiceover: {sec_id} ({cfg['title']})...")
    res = engine.generate_segmented_speech(
        transcript=script,
        output_wav_path=out_wav,
        voice_name="Fenrir",
        custom_profile=profile,
        custom_director_note=note,
        chunks_dir=chunks_sub,
        resume=True
    )
    
    raw_dur = res["duration"]
    print(f"  • Raw Generated Duration: {raw_dur:.2f}s | Target: {target_dur:.2f}s")
    return out_wav, raw_dur

def adjust_tempo_and_sync(raw_wav: str, target_dur: float, sec_id: str) -> str:
    """
    Adjusts speech tempo slightly if needed and pads with exact silence
    so that the output duration matches target_dur to within 10ms.
    """
    with wave.open(raw_wav, 'rb') as wf:
        raw_dur = wf.getnframes() / float(wf.getframerate())
    
    # We want speech to end comfortably with ~1.5s to 2.0s tail before the section transitions
    ideal_speech_dur = target_dur - 1.8
    
    tempo = 1.0
    if raw_dur > ideal_speech_dur:
        tempo = min(1.35, raw_dur / ideal_speech_dur)
    elif raw_dur < (ideal_speech_dur * 0.70):
        # Slightly stretch if speech was too fast
        tempo = max(0.90, raw_dur / ideal_speech_dur)
    
    tempo_wav = os.path.join(CACHE_DIR, f"{sec_id}_tempo.wav")
    if abs(tempo - 1.0) > 0.02:
        print(f"  ⚡ Applying natural cadence adjustment (atempo={tempo:.3f})...")
        cmd_tempo = [
            'ffmpeg', '-y', '-i', raw_wav,
            '-filter:a', f'atempo={tempo:.3f}',
            '-ar', '48000', '-ac', '2',
            tempo_wav
        ]
        subprocess.run(cmd_tempo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    else:
        # Just convert to 48kHz stereo
        cmd_conv = [
            'ffmpeg', '-y', '-i', raw_wav,
            '-ar', '48000', '-ac', '2',
            tempo_wav
        ]
        subprocess.run(cmd_conv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    with wave.open(tempo_wav, 'rb') as wf:
        current_dur = wf.getnframes() / float(wf.getframerate())
    
    # Pad with initial small lead-in (0.3s) and trailing silence to reach EXACT target_dur
    lead_in_s = 0.35 if sec_id != "00_Hook" else 0.15
    tail_s = max(0.05, target_dur - (current_dur + lead_in_s))
    
    synced_wav = os.path.join(CACHE_DIR, f"{sec_id}_synced.wav")
    cmd_pad = [
        'ffmpeg', '-y',
        '-f', 'lavfi', '-t', str(lead_in_s), '-i', 'anullsrc=r=48000:cl=stereo',
        '-i', tempo_wav,
        '-f', 'lavfi', '-t', str(tail_s), '-i', 'anullsrc=r=48000:cl=stereo',
        '-filter_complex', '[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]',
        '-map', '[a]',
        '-t', str(target_dur),
        synced_wav
    ]
    subprocess.run(cmd_pad, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    with wave.open(synced_wav, 'rb') as wf:
        final_dur = wf.getnframes() / float(wf.getframerate())
    print(f"  ✓ Synchronized to exact section duration: {final_dur:.2f}s (target: {target_dur:.2f}s)")
    return synced_wav

def mix_with_drawing_sfx(synced_voice_wav: str, orig_master_audio: str, sec_id: str) -> str:
    """
    Extracts the subtle ambient & drawing sound effects from the original master audio,
    ducks it under the new English voiceover, and mixes into a pristine Master English Track.
    """
    master_en_wav = os.path.join(CACHE_DIR, f"{sec_id}_master_en.wav")
    
    if not os.path.exists(orig_master_audio):
        print(f"  Notice: Original master audio not found, using clean voiceover.")
        shutil.copyfile(synced_voice_wav, master_en_wav)
        return master_en_wav
    
    # Mix original background SFX at 0.35 volume with English voiceover at 1.0 volume
    # using sidechain ducking or balanced blend:
    cmd_mix = [
        'ffmpeg', '-y',
        '-i', synced_voice_wav,
        '-i', orig_master_audio,
        '-filter_complex',
        '[1:a]volume=0.30,lowpass=f=3500[sfx];[0:a]volume=1.05[vox];[vox][sfx]amix=inputs=2:duration=first:dropout_transition=2[out]',
        '-map', '[out]',
        '-ar', '48000', '-ac', '2',
        master_en_wav
    ]
    subprocess.run(cmd_mix, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return master_en_wav

def main():
    print("=" * 80)
    print("🎬 LAUNCHING FULL DOCUMENTARY ENGLISH DUBBING PIPELINE")
    print("=" * 80)
    
    engine = VoiceStudioEngine()
    
    synced_voice_files = []
    master_en_files = []
    
    cumulative_time = 0.0
    chapters_en = []
    
    for idx, cfg in enumerate(SECTIONS_CONFIG, 1):
        sec_id = cfg["id"]
        target_dur = cfg["target_dur"]
        orig_aud = os.path.join(SECTIONS_DIR, cfg["aud_file"])
        
        print(f"\n[{idx:02d}/11] Processing: {sec_id} ({cfg['title']})")
        
        # 1. Synthesize English narration
        raw_wav, raw_dur = synthesize_section_english(engine, cfg)
        
        # 2. Timing sync & padding
        synced_wav = adjust_tempo_and_sync(raw_wav, target_dur, sec_id)
        synced_voice_files.append(synced_wav)
        
        # 3. Sound design & SFX mix
        master_en = mix_with_drawing_sfx(synced_wav, orig_aud, sec_id)
        master_en_files.append(master_en)
        
        # Record English chapter
        m = int(cumulative_time // 60)
        s = int(cumulative_time % 60)
        chapters_en.append({
            "tag": sec_id,
            "title": cfg["title"],
            "timestamp": f"{m:02d}:{s:02d}",
            "start_s": cumulative_time,
            "dur": target_dur
        })
        cumulative_time += target_dur
    
    # 4. Concatenate All Synchronized English Voiceover
    print("\n" + "=" * 80)
    print("🔗 STITCHING FULL FEATURE ENGLISH SOUNDTRACKS")
    print("=" * 80)
    
    # Pristine English Voiceover Concat
    list_voice = os.path.join(CACHE_DIR, "concat_voice_en_list.txt")
    with open(list_voice, "w", encoding="utf-8") as f:
        for p in synced_voice_files:
            f.write(f"file '{p.replace(chr(92), '/')}'\n")
    
    full_voice_en = os.path.join(OUTPUT_DIR, "Full_Wealth_Classes_Documentary_English_Dub.wav")
    cmd_concat_v = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_voice, '-c', 'pcm_s16le', full_voice_en]
    subprocess.run(cmd_concat_v, check=True)
    print(f"  ✓ Full English Dub Audio: {full_voice_en}")
    
    # Master Stereo Mixed Soundtrack Concat
    list_master = os.path.join(CACHE_DIR, "concat_master_en_list.txt")
    with open(list_master, "w", encoding="utf-8") as f:
        for p in master_en_files:
            f.write(f"file '{p.replace(chr(92), '/')}'\n")
    
    full_master_en = os.path.join(OUTPUT_DIR, "Full_Wealth_Classes_Documentary_English_Master.wav")
    cmd_concat_m = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_master, '-c', 'pcm_s16le', full_master_en]
    subprocess.run(cmd_concat_m, check=True)
    print(f"  ✓ Full English Master Audio: {full_master_en}")
    
    # 5. Multiplex Final 1080p Video with English Audio
    print("\n🎥 Multiplexing 1080p Video with English Audio Track...")
    orig_full_video = os.path.join(OUTPUT_DIR, "Full_Wealth_Classes_Documentary_1080p.mp4")
    full_video_en = os.path.join(OUTPUT_DIR, "Full_Wealth_Classes_Documentary_English_1080p.mp4")
    
    cmd_mux = [
        'ffmpeg', '-y',
        '-i', orig_full_video,
        '-i', full_master_en,
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '256k',
        full_video_en
    ]
    subprocess.run(cmd_mux, check=True)
    print(f"  ✓ Full English 1080p Video: {full_video_en}")
    
    # 6. Save English Chapters
    chapters_file = os.path.join(OUTPUT_DIR, "documentary_chapters_english.txt")
    with open(chapters_file, "w", encoding="utf-8") as f:
        f.write("# Wealth Classes: From Homeless to Billionaire (English Documentary Edition)\n")
        f.write(f"# Total Runtime: {int(cumulative_time//60):02d}:{int(cumulative_time%60):02d} ({cumulative_time:.2f}s)\n\n")
        f.write("## YouTube Chapters (English):\n")
        for ch in chapters_en:
            f.write(f"{ch['timestamp']} {ch['title']}\n")
    print(f"  ✓ English Chapters: {chapters_file}")
    
    # Print summary
    file_size_mb = os.path.getsize(full_video_en) / (1024 * 1024)
    print("\n" + "=" * 80)
    print("🏆 ENGLISH DUBBING PRODUCTION 100% COMPLETE!")
    print(f"  • English Video 1080p : {full_video_en} ({file_size_mb:.1f} MB)")
    print(f"  • English Master Audio: {full_master_en}")
    print(f"  • English Voice Dub   : {full_voice_en}")
    print(f"  • English Chapters    : {chapters_file}")
    print(f"  • Total Runtime       : {int(cumulative_time//60):02d}:{int(cumulative_time%60):02d} ({cumulative_time:.2f}s)")
    print("=" * 80)

if __name__ == "__main__":
    main()
