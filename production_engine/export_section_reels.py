#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║           REELS / SHORTS EXPORT ENGINE  (9:16 · 1080×1920)          ║
║                                                                      ║
║  Converts 16:9 whiteboard section videos into viral-ready vertical   ║
║  Reels with professional cinematic framing & Arabic overlays.        ║
║                                                                      ║
║  Features:                                                           ║
║  ─────────────────────────────────────────────────────────────────── ║
║  • 1080×1920 vertical canvas (9:16 Instagram/TikTok/YouTube Shorts)  ║
║  • Pixel-perfect Arabic typography (reshaped & bi-directional)       ║
║  • Section-tailored curiosity hooks and viral engagement cards       ║
║  • Clean whiteboard paper background (#FAF8F5) with colored accents  ║
║  • Smooth animated bottom progress bar                               ║
║  • Hardware-accelerated encoding (h264_nvenc with libx264 fallback)  ║
║                                                                      ║
║  Usage:                                                              ║
║    python export_section_reels.py --sections 04_pineapple 11_jabuticaba ║
║    python export_section_reels.py --all                              ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile

# Safe console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ─── Constants ────────────────────────────────────────────────────────────────
ROOT_DIR = r"E:\image_to_animate"
SECTIONS_DIR = os.path.join(ROOT_DIR, "sections")
OUTPUT_BASE = os.path.join(ROOT_DIR, "output_animations", "12_strangest_fruits_documentary", "deliverables", "reels")

# Reels dimensions
REEL_W, REEL_H = 1080, 1920
# Original video dimensions
SRC_W, SRC_H = 1920, 1080
SCALED_W = 1080
SCALED_H = 608
VIDEO_Y = 620
FPS = 30

# ─── Section Metadata (Titles, Hooks, Accent Colors, Engagement Questions) ────
SECTION_META = {
    "01_apple": {
        "title_ar": "لغز فاكهة التفاح",
        "subtitle_ar": "هل تعلم كم نوعاً مختلفاً يوجد حول العالم؟",
        "hook_question": "ما هو نوع التفاح المفضل لديك؟",
        "accent_color": "#E74C3C",
        "display_name": "Apple"
    },
    "02_kiwi": {
        "title_ar": "أسرار فاكهة الكيوي",
        "subtitle_ar": "الفاكهة الصغيرة ذات القوة الخارقة للمناعة!",
        "hook_question": "هل تأكل الكيوي بقشره أم تقشره أولاً؟",
        "accent_color": "#27AE60",
        "display_name": "Kiwi"
    },
    "03_lemon": {
        "title_ar": "عجائب فاكهة الليمون",
        "subtitle_ar": "سر الحموضة الصاعقة والفوائد التي لا تحصى!",
        "hook_question": "هل تبدأ يومك بكوب ماء دافئ مع ليمون؟",
        "accent_color": "#F1C40F",
        "display_name": "Lemon"
    },
    "04_pineapple": {
        "title_ar": "سر فاكهة الأناناس",
        "subtitle_ar": "لماذا تلدغ لسانك عندما تأكلها؟",
        "hook_question": "هل جربت نقع الأناناس في الماء المالح قبل أكله؟",
        "accent_color": "#E67E22",
        "display_name": "Pineapple"
    },
    "05_pomegranate": {
        "title_ar": "ياقوت الطبيعة: الرمان",
        "subtitle_ar": "فاكهة الملوك ومصدر مضادات الأكسدة الأقوى!",
        "hook_question": "ما هي أسهل طريقة لتقشير الرمان برأيك؟",
        "accent_color": "#C0392B",
        "display_name": "Pomegranate"
    },
    "06_mango": {
        "title_ar": "ملك الفواكه: المانجو",
        "subtitle_ar": "أسرار الحلاوة الاستوائية ومئات الأصناف الفريدة!",
        "hook_question": "ما هو نوع المانجو الألذ في بلدك؟",
        "accent_color": "#F39C12",
        "display_name": "Mango"
    },
    "07_dates": {
        "title_ar": "ذهب الصحراء: التمر",
        "subtitle_ar": "غذاء متكامل ومصدر الطاقة الطبيعية الأقدم بالتاريخ!",
        "hook_question": "كم حبة تمر تتناول يومياً مع القهوة؟",
        "accent_color": "#8B4513",
        "display_name": "Dates"
    },
    "08_miracle_fruit": {
        "title_ar": "الفاكهة المعجزة الساحرة",
        "subtitle_ar": "حبة سحرية تحول طعم الليمون الحامض إلى سكر خالص!",
        "hook_question": "لو توفرت لديك.. ما أول طعام حامض ستجربه معها؟",
        "accent_color": "#E91E63",
        "display_name": "Miracle_Fruit"
    },
    "09_dragon_fruit": {
        "title_ar": "فاكهة التنين الأسطورية",
        "subtitle_ar": "زهرة صبار نادرة لا تتفتح إلا في جنح الظلام!",
        "hook_question": "هل تفضل النوع الأبيض أم الأحمر من الداخل؟",
        "accent_color": "#D81B60",
        "display_name": "Dragon_Fruit"
    },
    "10_fig": {
        "title_ar": "عجائب فاكهة التين",
        "subtitle_ar": "أعجب سر بيولوجي بين شجرة التين وحشرة الدبور!",
        "hook_question": "هل كنت تعرف قصة التين مع الدبور من قبل؟",
        "accent_color": "#6D4C41",
        "display_name": "Fig"
    },
    "11_jabuticaba": {
        "title_ar": "شجرة الجابوتيكابا العجيبة",
        "subtitle_ar": "شجرة برازيلية نادرة تنبت ثمارها مباشرة على الجذع!",
        "hook_question": "هل شاهدت شجرة تثمر بهذه الطريقة من قبل في حياتك؟",
        "accent_color": "#4A148C",
        "display_name": "Jabuticaba"
    },
    "12_outro": {
        "title_ar": "أغرب فواكه كوكب الأرض",
        "subtitle_ar": "رحلة استكشافية في عجائب الطبيعة المدهشة!",
        "hook_question": "أي فاكهة أثارت دهشتك أكثر من غيرها؟",
        "accent_color": "#1B4F72",
        "display_name": "Outro"
    },
}


def hex_to_rgb(hex_color):
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def prepare_arabic_text(text):
    """Reshape and reorder Arabic text for proper RTL display."""
    if not text:
        return ""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def get_arabic_font(size, bold=True):
    """Load high-quality Windows Arabic font with fallback."""
    from PIL import ImageFont
    bold_candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\tahomabd.ttf",
    ]
    reg_candidates = [
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
    ]
    candidates = bold_candidates if bold else reg_candidates
    for p in candidates:
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def check_nvenc_available():
    """Check if NVIDIA h264_nvenc encoder is available."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=10
        )
        return "h264_nvenc" in result.stdout
    except Exception:
        return False


def create_reel_template_image(section_id, output_dir):
    """
    Create complete 1080x1920 static template PNG using Pillow.
    Pre-renders:
      - Clean whiteboard background (#FAF8F5)
      - Category pill badge ("أغرب فواكه العالم")
      - Main section title (large bold Arabic)
      - Catchy curiosity subtitle
      - Framing accent borders around video slot
      - Engagement question card with CTA button
      - Background track for bottom progress bar
    Returns path to generated template PNG.
    """
    from PIL import Image, ImageDraw

    meta = SECTION_META.get(section_id, {
        "title_ar": section_id,
        "subtitle_ar": "",
        "hook_question": "شاركنا رأيك في التعليقات!",
        "accent_color": "#E67E22",
        "display_name": section_id
    })

    accent_rgb = hex_to_rgb(meta["accent_color"])
    overlay_dir = os.path.join(output_dir, "overlays")
    os.makedirs(overlay_dir, exist_ok=True)

    # 1. Base Canvas (Clean warm whiteboard tone)
    canvas = Image.new("RGBA", (REEL_W, REEL_H), (250, 248, 245, 255))
    draw = ImageDraw.Draw(canvas)

    # Fonts
    font_badge = get_arabic_font(24, bold=True)
    font_title = get_arabic_font(56, bold=True)
    font_sub = get_arabic_font(30, bold=False)
    font_card = get_arabic_font(28, bold=True)
    font_body = get_arabic_font(26, bold=False)

    # 2. Framing borders around 16:9 video slot
    draw.line([(0, VIDEO_Y - 2), (REEL_W, VIDEO_Y - 2)], fill=accent_rgb, width=4)
    draw.line([(0, VIDEO_Y + SCALED_H + 2), (REEL_W, VIDEO_Y + SCALED_H + 2)], fill=accent_rgb, width=4)

    # 3. Top Header: Series Pill Badge
    badge_text = prepare_arabic_text("أغرب فواكه العالم")
    bb = draw.textbbox((0, 0), badge_text, font=font_badge)
    bw = bb[2] - bb[0]
    bx = (REEL_W - bw) // 2
    draw.rounded_rectangle(
        [bx - 24, 220, bx + bw + 24, 266],
        radius=16,
        fill=(*accent_rgb, 235)
    )
    draw.text((bx, 228), badge_text, fill=(255, 255, 255, 255), font=font_badge)

    # 4. Main Title
    title_text = prepare_arabic_text(meta["title_ar"])
    tb = draw.textbbox((0, 0), title_text, font=font_title)
    tw = tb[2] - tb[0]
    draw.text(((REEL_W - tw) // 2, 320), title_text, fill=(35, 35, 35, 255), font=font_title)

    # 5. Curiosity Subtitle Hook
    sub_text = prepare_arabic_text(meta["subtitle_ar"])
    if sub_text:
        sb = draw.textbbox((0, 0), sub_text, font=font_sub)
        sw = sb[2] - sb[0]
        draw.text(((REEL_W - sw) // 2, 415), sub_text, fill=(110, 110, 110, 255), font=font_sub)

    # 6. Bottom Engagement Card
    card_w, card_h = 960, 220
    cx = (REEL_W - card_w) // 2
    cy = VIDEO_Y + SCALED_H + 60

    # Card background with subtle accent outline
    draw.rounded_rectangle(
        [cx, cy, cx + card_w, cy + card_h],
        radius=24,
        fill=(255, 255, 255, 220),
        outline=(*accent_rgb, 120),
        width=2
    )

    # Card Question Text
    q_text = prepare_arabic_text(meta["hook_question"])
    qb = draw.textbbox((0, 0), q_text, font=font_card)
    qw = qb[2] - qb[0]
    draw.text(((REEL_W - qw) // 2, cy + 35), q_text, fill=(40, 40, 40, 255), font=font_card)

    # Comment prompt
    cmt_text = prepare_arabic_text("شاركنا رأيك في التعليقات!")
    cb = draw.textbbox((0, 0), cmt_text, font=font_body)
    cw = cb[2] - cb[0]
    draw.text(((REEL_W - cw) // 2, cy + 95), cmt_text, fill=(100, 100, 100, 255), font=font_body)

    # Subscribe / Follow CTA button badge
    btn_text = prepare_arabic_text("تابعنا للمزيد من الأسرار الغريبة")
    bb2 = draw.textbbox((0, 0), btn_text, font=font_badge)
    bw2 = bb2[2] - bb2[0]
    bx2 = (REEL_W - bw2) // 2
    draw.rounded_rectangle(
        [bx2 - 20, cy + 148, bx2 + bw2 + 20, cy + 192],
        radius=14,
        fill=(*accent_rgb, 220)
    )
    draw.text((bx2, cy + 154), btn_text, fill=(255, 255, 255, 255), font=font_badge)

    # 7. Progress bar track (gray background line at bottom)
    draw.rectangle([0, 1912, REEL_W, 1920], fill=(220, 220, 220, 255))

    template_path = os.path.join(overlay_dir, f"{section_id}_reel_template.png")
    canvas.save(template_path)
    return template_path


def build_reels_ffmpeg_command(
    input_video,
    output_path,
    template_image_path,
    duration_s,
    accent_rgb,
    use_nvenc=False
):
    """
    Build rock-solid FFmpeg command combining:
      Input 0: 1080x1920 pre-rendered static template (looped at 30 fps)
      Input 1: 16:9 whiteboard video
      Animated Progress bar: dynamically overlays across width [0..1080]
    """
    r, g, b = accent_rgb

    filter_complex = (
        f"[1:v]scale={SCALED_W}:{SCALED_H}:flags=lanczos[scaled];"
        f"[0:v][scaled]overlay=0:{VIDEO_Y}:shortest=1[comp];"
        f"color=c=0x{r:02X}{g:02X}{b:02X}:s={REEL_W}x8:d={duration_s}:r={FPS}[pbar];"
        f"[comp][pbar]overlay=x='-w+w*t/{duration_s:.2f}':y=1912:shortest=1[final]"
    )

    if use_nvenc:
        encoder_args = [
            "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-rc", "vbr",
            "-cq", "20",
            "-b:v", "8M",
            "-maxrate", "12M",
            "-bufsize", "16M",
        ]
    else:
        encoder_args = [
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-maxrate", "8M",
            "-bufsize", "12M",
        ]

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(FPS), "-t", f"{duration_s:.2f}",
        "-i", template_image_path,   # Input 0: Static canvas & typography template
        "-i", input_video,           # Input 1: Source 16:9 whiteboard video
        "-filter_complex", filter_complex,
        "-map", "[final]",
        "-map", "1:a?",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        *encoder_args,
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path
    ]

    return cmd


def export_section_reel(section_id, use_nvenc=False):
    """Export a single section as a vertical 9:16 Reel."""
    section_dir = os.path.join(SECTIONS_DIR, section_id)
    input_video = os.path.join(section_dir, "final_whiteboard_1080p.mp4")

    if not os.path.isfile(input_video):
        print(f"[ERROR] Video not found: {input_video}")
        return None

    meta = SECTION_META.get(section_id, {
        "display_name": section_id,
        "title_ar": section_id,
        "accent_color": "#E67E22"
    })

    os.makedirs(OUTPUT_BASE, exist_ok=True)

    section_num = section_id.split("_")[0]
    output_name = f"{section_num}_{meta['display_name']}_Reels_1080x1920.mp4"
    output_path = os.path.join(OUTPUT_BASE, output_name)

    duration = get_video_duration(input_video)
    accent_rgb = hex_to_rgb(meta["accent_color"])

    print(f"\n{'='*70}")
    print(f"  REELS EXPORT: {meta['title_ar']} ({meta['display_name']})")
    print(f"  Source:   {input_video}")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Output:   {output_path}")
    print(f"  Format:   {REEL_W}x{REEL_H} (9:16 Vertical)")
    print(f"  Encoder:  {'h264_nvenc (GPU)' if use_nvenc else 'libx264 (CPU)'}")
    print(f"{'='*70}\n")

    # Step 1: Generate high-resolution static template with Arabic typography
    print(f"[STEP 1] Generating high-res Arabic template graphic...")
    template_path = create_reel_template_image(section_id, OUTPUT_BASE)
    print(f"  Template: {template_path}")

    # Step 2: Build and execute FFmpeg command
    print(f"\n[STEP 2] Rendering vertical Reel video...")
    cmd = build_reels_ffmpeg_command(
        input_video, output_path, template_path, duration, accent_rgb, use_nvenc
    )

    log_path = os.path.join(OUTPUT_BASE, f"{section_num}_{meta['display_name']}_reels_render.log")

    with open(log_path, "w", encoding="utf-8") as log_file:
        log_file.write(f"Command:\n{' '.join(cmd)}\n\n")
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        log_file.write(process.stdout)

    if process.returncode != 0:
        print(f"[ERROR] FFmpeg failed with code {process.returncode}")
        print(f"[ERROR] Check log: {log_path}")
        lines = process.stdout.strip().split('\n')
        for line in lines[-15:]:
            print(f"  {line}")
        return None

    # Verify output
    if os.path.isfile(output_path):
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        out_duration = get_video_duration(output_path)
        print(f"\n[SUCCESS] Reel exported successfully!")
        print(f"  File:       {output_path}")
        print(f"  Size:       {file_size_mb:.1f} MB")
        print(f"  Duration:   {out_duration:.1f}s")
        print(f"  Resolution: {REEL_W}x{REEL_H}")
        return output_path
    else:
        print(f"[ERROR] Output file not created: {output_path}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Export whiteboard sections as vertical Reels (9:16, 1080x1920)"
    )
    parser.add_argument(
        "--sections", nargs="+",
        help="Section IDs to export (e.g., 04_pineapple 11_jabuticaba)"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Export all available sections"
    )
    parser.add_argument(
        "--gpu", action="store_true",
        help="Force GPU encoding (h264_nvenc)"
    )
    parser.add_argument(
        "--cpu", action="store_true",
        help="Force CPU encoding (libx264)"
    )

    args = parser.parse_args()

    # Determine encoder
    if args.gpu:
        use_nvenc = True
    elif args.cpu:
        use_nvenc = False
    else:
        use_nvenc = check_nvenc_available()

    print(f"\n{'='*70}")
    print(f"  REELS / SHORTS EXPORT ENGINE")
    print(f"  9:16  |  1080x1920  |  Professional Vertical Format")
    print(f"{'='*70}")
    print(f"\n  Encoder: {'h264_nvenc (GPU Accelerated)' if use_nvenc else 'libx264 (CPU)'}")
    print(f"  Output:  {OUTPUT_BASE}\n")

    # Determine which sections to export
    if args.all:
        sections = sorted([
            d for d in os.listdir(SECTIONS_DIR)
            if os.path.isdir(os.path.join(SECTIONS_DIR, d))
            and os.path.isfile(os.path.join(SECTIONS_DIR, d, "final_whiteboard_1080p.mp4"))
        ])
    elif args.sections:
        sections = args.sections
    else:
        print("[ERROR] Specify --sections or --all")
        sys.exit(1)

    print(f"  Sections to export: {len(sections)}")
    for s in sections:
        meta = SECTION_META.get(s, {"title_ar": s})
        print(f"    - {s}  ({meta['title_ar']})")
    print()

    # Export each section
    results = []
    for i, section_id in enumerate(sections, 1):
        print(f"\n{'─'*70}")
        print(f"  [{i}/{len(sections)}] Processing: {section_id}")
        print(f"{'─'*70}")

        result = export_section_reel(section_id, use_nvenc)
        results.append((section_id, result))

    # Summary
    print(f"\n\n{'='*70}")
    print(f"  EXPORT SUMMARY")
    print(f"{'='*70}\n")

    success_count = 0
    for section_id, result in results:
        meta = SECTION_META.get(section_id, {"title_ar": section_id})
        if result:
            size_mb = os.path.getsize(result) / (1024 * 1024)
            print(f"  [OK]   {meta['title_ar']:24s}  ->  {os.path.basename(result)} ({size_mb:.1f} MB)")
            success_count += 1
        else:
            print(f"  [FAIL] {meta['title_ar']:24s}  ->  FAILED")

    print(f"\n  Total: {success_count}/{len(results)} exported successfully")
    print(f"  Output: {OUTPUT_BASE}\n")

    return success_count == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
