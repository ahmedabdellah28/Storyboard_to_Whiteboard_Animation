#!/usr/bin/env python3
"""Unified Multi-Project CLI Orchestrator for Whiteboard Motion Graphics Pipeline (V6).

Features:
- Full Multi-Project Isolation: Keeps separate projects, storyboards, voiceovers,
  scripts, and rendered exports organized under projects/<project_name>/ without collision.
- Automated Scaffolding: 'init' / 'new' command initializes project folders,
  formats master voiceover script templates, storyboard guides, and metadata.
- Context Switching: 'use' switches active project, 'projects' lists all available projects.
- Clear Visual Path Guides: 'paths' displays exact input/output directories in Arabic.
- Native EffectCraft GPU Render: 1080p hardware-accelerated motion graphics engine.

Commands:
    python pipeline_cli.py init <project_name> [--sections 10]
    python pipeline_cli.py projects
    python pipeline_cli.py use <project_name>
    python pipeline_cli.py paths [--project <name>]
    python pipeline_cli.py voice   --section 01 [--project <name>]
    python pipeline_cli.py timing  --section 01 [--project <name>]
    python pipeline_cli.py extract --section 01 [--project <name>]
    python pipeline_cli.py render  --section 01 [--engine effectcraft] [--project <name>]
    python pipeline_cli.py status  [--project <name>]
    python pipeline_cli.py merge   [--project <name>]
"""

import os
import sys
import core_engine.dns_patch
import argparse
import re
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Safe UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

ACTIVE_PROJECT_FILE = ROOT_DIR / ".active_project"
PROJECTS_DIR = ROOT_DIR / "projects"
GLOBAL_EXPORTS_DIR = ROOT_DIR / "exports"


def get_active_project_name() -> Optional[str]:
    """Retrieves the currently active project name from .active_project file."""
    if ACTIVE_PROJECT_FILE.exists():
        try:
            val = ACTIVE_PROJECT_FILE.read_text(encoding="utf-8").strip()
            if val and (PROJECTS_DIR / val).is_dir():
                return val
        except Exception:
            pass
    return None


def set_active_project_name(project_name: str) -> None:
    """Sets the currently active project name."""
    try:
        ACTIVE_PROJECT_FILE.write_text(project_name.strip(), encoding="utf-8")
    except Exception as e:
        print(f"[!] Warning: Could not persist active project: {e}")


def slugify_project_name(name: str) -> str:
    """Produces a clean filesystem slug, supporting both Latin and Arabic titles."""
    if not name:
        return "project"
    clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', name.strip()).strip('_').lower()
    clean = re.sub(r'_+', '_', clean)
    if clean:
        return clean
    arabic_map = {
        'ا': 'a', 'أ': 'a', 'إ': 'i', 'آ': 'a', 'ب': 'b', 'ت': 't', 'ث': 'th',
        'ج': 'j', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'dh', 'ر': 'r', 'ز': 'z',
        'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'd', 'ط': 't', 'ظ': 'z', 'ع': 'a',
        'غ': 'gh', 'ف': 'f', 'ق': 'q', 'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n',
        'ه': 'h', 'و': 'w', 'ي': 'y', 'ى': 'a', 'ئ': 'e', 'ء': 'a', 'ؤ': 'o',
        'ة': 'a'
    }
    trans = "".join(arabic_map.get(ch, ch if ch.isalnum() else "_") for ch in name)
    clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', trans).strip('_').lower()
    clean = re.sub(r'_+', '_', clean)
    return clean if clean else "project"


def get_project_dirs(project_name: Optional[str] = None, create: bool = True) -> Dict[str, Any]:
    """Resolves all root, input, section, and export paths for a given or active project.
    Falls back gracefully to legacy root paths if no project is active or specified.
    """
    if not project_name:
        project_name = get_active_project_name()

    if project_name and project_name != "default":
        clean_name = slugify_project_name(project_name)
        proj_dir = PROJECTS_DIR / clean_name
        if not proj_dir.is_dir():
            # Check by raw project_name
            if (PROJECTS_DIR / project_name).is_dir():
                proj_dir = PROJECTS_DIR / project_name
                clean_name = project_name
            elif PROJECTS_DIR.exists():
                # Search by title in project.json across all projects
                for p in PROJECTS_DIR.iterdir():
                    if p.is_dir() and (p / "project.json").exists():
                        try:
                            meta = json.loads((p / "project.json").read_text(encoding="utf-8"))
                            if meta.get("title") == project_name or meta.get("project_name") == project_name:
                                proj_dir = p
                                clean_name = p.name
                                break
                        except Exception:
                            pass
        if proj_dir.is_dir():
            # Internal project exports directory: projects/<project_name>/exports/
            proj_exports_dir = proj_dir / "exports"
            if create:
                proj_exports_dir.mkdir(parents=True, exist_ok=True)
                (proj_dir / "export").mkdir(parents=True, exist_ok=True)

            inputs_dir = proj_dir / "inputs"
            if not inputs_dir.exists() and (proj_dir / "input").exists():
                inputs_dir = proj_dir / "input"
            if create:
                inputs_dir.mkdir(parents=True, exist_ok=True)
                (proj_dir / "input").mkdir(parents=True, exist_ok=True)

            script_dir = inputs_dir / "script"
            storyboards_dir = inputs_dir / "storyboards"
            sections_dir = proj_dir / "sections"

            # Master script: check inputs/script/master_script.txt, then inputs/master_script.txt
            master_script = script_dir / "master_script.txt"
            if not master_script.exists() and (inputs_dir / "master_script.txt").exists():
                master_script = inputs_dir / "master_script.txt"

            return {
                "name": clean_name,
                "is_project": True,
                "proj_dir": proj_dir,
                "inputs_dir": inputs_dir,
                "script_dir": script_dir,
                "sections_script_dir": script_dir / "sections",
                "storyboards_dir": storyboards_dir,
                "sections_dir": sections_dir,
                "exports_dir": proj_exports_dir,
                "internal_exports_dir": proj_exports_dir,
                "master_script": master_script,
            }

    # Fallback to legacy default structure
    return {
        "name": "default",
        "is_project": False,
        "proj_dir": ROOT_DIR,
        "inputs_dir": ROOT_DIR / "inputs",
        "script_dir": ROOT_DIR / "inputs" / "scripts",
        "sections_script_dir": ROOT_DIR / "inputs" / "scripts",
        "storyboards_dir": ROOT_DIR / "inputs" / "storyboards",
        "sections_dir": ROOT_DIR / "sections",
        "exports_dir": GLOBAL_EXPORTS_DIR,
        "internal_exports_dir": GLOBAL_EXPORTS_DIR,
        "master_script": ROOT_DIR / "inputs" / "master_script.txt",
    }


def get_section_paths(sec_num: str, project: Optional[str] = None, create: bool = True) -> Dict[str, Any]:
    """Returns resolved paths for an individual section within the selected project."""
    proj = get_project_dirs(project, create=create)
    sec_id = f"section_{int(sec_num):02d}"
    sec_dir = proj["sections_dir"] / sec_id
    voice_dir = sec_dir / "voice"
    timing_dir = sec_dir / "timing"
    assets_dir = sec_dir / "assets"

    if create:
        sec_dir.mkdir(parents=True, exist_ok=True)
        voice_dir.mkdir(parents=True, exist_ok=True)
        timing_dir.mkdir(parents=True, exist_ok=True)
        assets_dir.mkdir(parents=True, exist_ok=True)

    # 1. Storyboard search
    sb_path = proj["storyboards_dir"] / f"{sec_id}.png"
    if not sb_path.exists():
        for ext in [".jpg", ".jpeg", ".webp", ".PNG", ".JPG", ".JPEG"]:
            cand = proj["storyboards_dir"] / f"{sec_id}{ext}"
            if cand.exists():
                sb_path = cand
                break

    # Fallback to legacy storyboards only if in default project
    if not sb_path.exists() and proj["name"] == "default":
        cand_legacy = ROOT_DIR / "inputs" / "storyboards" / f"{sec_id}.png"
        if cand_legacy.exists():
            sb_path = cand_legacy

    # 2. Section script search
    sec_script = proj["sections_script_dir"] / f"{sec_id}.txt"
    if not sec_script.exists():
        cand2 = proj["inputs_dir"] / "scripts" / f"{sec_id}.txt"
        if cand2.exists():
            sec_script = cand2

    # 3. Export video path (v7 only — no v6 kept in exports)
    export_dir = proj["exports_dir"]
    export_mp4 = export_dir / f"{sec_id}_master_v7.mp4"

    return {
        "project": proj["name"],
        "proj_dir": proj["proj_dir"],
        "is_project": proj["is_project"],
        "sec_id": sec_id,
        "sec_dir": sec_dir,
        "voice_dir": voice_dir,
        "timing_dir": timing_dir,
        "assets_dir": assets_dir,
        "audio_wav": voice_dir / f"{sec_id}.wav",
        "storyboard_png": sb_path,
        "master_script": proj["master_script"],
        "section_script": sec_script,
        "export_dir": export_dir,
        "export_mp4": export_mp4,
        "manifest_json": sec_dir / "manifest.json"
    }


def get_section_text(paths: dict, sec_num: str) -> str:
    """Extracts validated text for a section supporting SECTION XX, [SECTION XX: ...], and ## N. headers."""
    from core.aion.script_stage import resolve_section_script
    proj_dir = paths["sec_dir"].parents[1] if "sec_dir" in paths else ROOT_DIR
    return resolve_section_script(
        sec_num=int(sec_num),
        sections_script_dir=paths["section_script"].parent,
        legacy_scripts_dir=proj_dir / "inputs" / "scripts",
        master_script=paths.get("master_script"),
    )


# ==============================================================================
# CLI COMMANDS: PROJECT SCAFFOLDING & MANAGEMENT
# ==============================================================================

def get_project_config(project: Optional[str] = None) -> dict:
    """Loads per-project language/TTS/typography config with safe Arabic/Egyptian/English defaults."""
    defaults = {
        "language": "ar",
        "dialect": "saudi_white",
        "tts_model": "gemini-3.1-flash-tts-preview",
        "tts_voice": "Fenrir",
        "tts_profile": "SAUDI_YOUTH_CREATOR",
        "director_note": "HIGH_ENERGY_YOUTUBE",
        "text_direction": "rtl",
        "fps": 30,
    }
    try:
        from core.aion.voice_stage import _FEMALE_VOICES, is_egyptian_dialect
        proj = get_project_dirs(project, create=False)
        proj_json = proj["proj_dir"] / "project.json"
        if proj_json.exists():
            meta = json.loads(proj_json.read_text(encoding="utf-8"))
            lang = (meta.get("language") or "ar").lower()
            if lang.startswith("en"):
                defaults.update({
                    "language": "en",
                    "dialect": "us_casual",
                    "tts_voice": "Puck",
                    "tts_profile": "US_CASUAL_STORYTELLER",
                    "director_note": "VIRAL_PSYCHOLOGY_ENGLISH_YT",
                    "text_direction": "ltr",
                })
            elif is_egyptian_dialect(
                meta.get("dialect", ""),
                meta.get("tts_profile", ""),
                meta.get("director_note", ""),
            ):
                d_low = str(meta.get("dialect") or "").lower()
                v_low = str(meta.get("tts_voice") or "").lower()
                p_up = str(meta.get("tts_profile") or "").upper()
                is_fem = ("female" in d_low) or (v_low in _FEMALE_VOICES) or ("FEMALE" in p_up)
                defaults.update({
                    "language": "ar",
                    "dialect": meta.get("dialect") or ("egyptian_female" if is_fem else "egyptian"),
                    "tts_voice": "Kore" if is_fem else "Fenrir",
                    "tts_profile": "EGYPTIAN_FEMALE_CREATOR" if is_fem else "EGYPTIAN_YOUTH_CREATOR",
                    "director_note": "HIGH_ENERGY_EGYPTIAN_YT",
                    "text_direction": "rtl",
                })
            for k in defaults:
                if meta.get(k):
                    defaults[k] = meta[k]
    except Exception:
        pass
    return defaults


def cmd_init(
    project_name: str,
    num_sections: int = 10,
    description: str = "",
    lang: str = "ar",
    dialect: str = "",
    voice: str = "",
):
    """Creates an isolated, complete folder architecture for a new video project."""
    clean_name = slugify_project_name(project_name)
    display_title = description or project_name
    proj_dir = PROJECTS_DIR / clean_name

    inputs_dir = proj_dir / "inputs"
    script_dir = inputs_dir / "script"
    sections_script_dir = script_dir / "sections"
    storyboards_dir = inputs_dir / "storyboards"
    sections_dir = proj_dir / "sections"
    exports_dir = proj_dir / "exports"

    # Self-contained directories inside projects/<project_name>/
    for d in [
        inputs_dir, proj_dir / "input",
        script_dir, sections_script_dir, storyboards_dir,
        sections_dir,
        exports_dir, proj_dir / "export"
    ]:
        d.mkdir(parents=True, exist_ok=True)

    # Pre-create section subfolders
    for i in range(1, num_sections + 1):
        s_dir = sections_dir / f"section_{i:02d}"
        (s_dir / "voice").mkdir(parents=True, exist_ok=True)
        (s_dir / "timing").mkdir(parents=True, exist_ok=True)
        (s_dir / "assets").mkdir(parents=True, exist_ok=True)

    # 1. Master Script Template
    master_script_path = script_dir / "master_script.txt"
    if not master_script_path.exists():
        sec_blocks = []
        for i in range(1, num_sections + 1):
            sec_blocks.append(
                f"SECTION {i:02d} - [عنوان المشهد {i}]\n"
                f"[اكتب هنا نص السكربت الصوتي للسكشن {i} - سيتم تحويله تلقائياً لصوت احترافي عبر Gemini TTS]\n"
            )
        script_body = (
            f"# ==============================================================================\n"
            f"# 📜 الاسكربت الصوتي الكامل لمشروع: {display_title}\n"
            f"# المعرف البرمجي: {clean_name}\n"
            f"# الوصف: {description or display_title}\n"
            f"# تاريخ الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"# ==============================================================================\n"
            f"# التعليمات:\n"
            f"# 1. املأ نصوص كل سكشن أدناه تحت عنوان 'SECTION 01', 'SECTION 02' إلخ.\n"
            f"# 2. أو يمكنك وضع ملف منفصل لكل سكشن داخل: inputs/script/sections/section_01.txt\n"
            f"# ==============================================================================\n\n"
            + "\n".join(sec_blocks)
        )
        master_script_path.write_text(script_body, encoding="utf-8")

    # 2. Storyboard Guide README
    sb_guide = storyboards_dir / "README.md"
    sb_guide.write_text(
        f"# 🎨 مجلد صور الاستوري بورد لمشروع: {display_title} ({clean_name})\n\n"
        f"ضع هنا صور الستوري بورد لكل سكشن وفق التسمية الآتية:\n"
        + "\n".join([f"- `section_{i:02d}.png` (أو .jpg / .webp)" for i in range(1, min(num_sections + 1, 11))]) +
        f"\n\n### ⚙️ المواصفات الموصى بها:\n"
        f"- **الدقة:** 1920x1080 (1080p Full HD) أو أعلى.\n"
        f"- **الخلفية:** بيضاء نقية (#FFFFFF) لاستخراج العناصر دون شوائب.\n"
        f"- **الصيغة:** PNG أو JPG.\n",
        encoding="utf-8"
    )

    # 3. Project Metadata JSON
    from core.aion.voice_stage import _FEMALE_VOICES, is_egyptian_dialect
    norm_lang = (lang or "ar").lower()
    is_en = norm_lang.startswith("en")
    eff_dialect = dialect or ("us_casual" if is_en else "saudi_white")
    is_eg = (not is_en) and is_egyptian_dialect(eff_dialect)
    is_eg_fem = is_eg and (("female" in eff_dialect.lower()) or (str(voice or "").lower() in _FEMALE_VOICES))
    if is_en:
        default_voice = "Puck"
        default_profile = "US_CASUAL_STORYTELLER"
        default_note = "HIGH_ENERGY_ENGLISH_YT"
    elif is_eg:
        default_voice = "Kore" if is_eg_fem else "Fenrir"
        default_profile = "EGYPTIAN_FEMALE_CREATOR" if is_eg_fem else "EGYPTIAN_YOUTH_CREATOR"
        default_note = "HIGH_ENERGY_EGYPTIAN_YT"
    else:
        default_voice = "Fenrir"
        default_profile = "SAUDI_YOUTH_CREATOR"
        default_note = "HIGH_ENERGY_YOUTUBE"

    project_meta = {
        "project_name": clean_name,
        "title": display_title,
        "created_at": datetime.now().isoformat(),
        "description": description or display_title,
        "num_sections": num_sections,
        "language": "en" if is_en else "ar",
        "dialect": eff_dialect,
        "tts_voice": voice or default_voice,
        "tts_profile": default_profile,
        "director_note": default_note,
        "text_direction": "ltr" if is_en else "rtl",
        "default_engine": "effectcraft",
        "fps": 30,
        "resolution": [1920, 1080],
        "paths": {
            "root": str(proj_dir.resolve()),
            "master_script": str(master_script_path.resolve()),
            "storyboards": str(storyboards_dir.resolve()),
            "sections": str(sections_dir.resolve()),
            "exports": str(exports_dir.resolve()),
            "export": str((proj_dir / "export").resolve())
        }
    }
    (proj_dir / "project.json").write_text(json.dumps(project_meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # 4. Project README
    proj_readme = proj_dir / "README.md"
    proj_readme.write_text(
        f"# 🎬 مشروع موشن جرافيك: {clean_name}\n\n"
        f"تم عزل مجلدات المشروع بالكامل لعدم التداخل مع أي مشاريع أخرى.\n\n"
        f"## 📂 أماكن الملفات:\n"
        f"1. **الاسكربت الصوتي:** `inputs/script/master_script.txt`\n"
        f"2. **الاستوري بورد:** `inputs/storyboards/section_01.png` إلخ\n"
        f"3. **بيانات السكاشن:** `sections/`\n"
        f"4. **مخرجات الفيديو:** `exports/` (أو `export/`)\n\n"
        f"## 🚀 خطوات العمل:\n"
        f"```bash\n"
        f"python pipeline_cli.py voice   --section 01\n"
        f"python pipeline_cli.py timing  --section 01\n"
        f"python pipeline_cli.py extract --section 01\n"
        f"python pipeline_cli.py render  --section 01 --engine effectcraft\n"
        f"```\n",
        encoding="utf-8"
    )

    # Set as active project
    set_active_project_name(clean_name)

    # Print comprehensive Arabic guide
    print("=" * 76)
    print(f"🎉 تم إنشاء وتهيئة مشروع الفيديو الجديد بنجاح: [{clean_name.upper()}]")
    print("=" * 76)
    print(f"📂 المجلد الرئيسي للمشروع:")
    print(f"   {proj_dir.resolve()}\n")

    print(f"📥 1. أين تضع الاسكربت الصوتي (Voiceover Script):")
    print(f"   • ملف النص الكامل:")
    print(f"     👉 {master_script_path.resolve()}")
    print(f"   • أو نصوص السكاشن منفصلة:")
    print(f"     👉 {sections_script_dir.resolve()}\\section_01.txt\n")

    print(f"🎨 2. أين تضع صور الاستوري بورد (Storyboard Images):")
    print(f"   • مجلد الصور:")
    print(f"     👉 {storyboards_dir.resolve()}")
    print(f"   • التسمية المطلوبة: section_01.png, section_02.png ... (PNG/JPG/WEBP)\n")

    print(f"📤 3. مجلد المخرجات النهائي (Exports Folder):")
    print(f"   • مجلد مخرجات هذا المشروع تحديداً (داخل المشروع ذاته):")
    print(f"     👉 {exports_dir.resolve()}")
    print(f"   • الفيديوهات المصدرة ستكون مثل: section_01_master_v6.mp4\n")

    print(f"✨ تم ضبط المشروع [{clean_name}] كمشروع نشط حالياً (Active Project).")
    print(f"🚀 خطوات الإنتاج التالية (جاهزة للتشغيل مباشرة):")
    print(f"   1) توليد الصوت:       python pipeline_cli.py voice   --section 01")
    print(f"   2) مزامنة التوقيت:     python pipeline_cli.py timing  --section 01")
    print(f"   3) استخراج العناصر:    python pipeline_cli.py extract --section 01")
    print(f"   4) رندر الفيديو 1080p: python pipeline_cli.py render  --section 01 --engine effectcraft")
    print(f"   5) متابعة الحالة:     python pipeline_cli.py status")
    print("=" * 76)


def cmd_use(project_name: str):
    """Switches the active project context."""
    p_info = get_project_dirs(project_name)
    if p_info["is_project"]:
        clean_name = p_info["name"]
        set_active_project_name(clean_name)
        print(f"✅ تم تفعيل المشروع النشط: [{clean_name.upper()}]")
        cmd_paths(clean_name)
        return True

    print(f"❌ المشروع '{project_name}' غير موجود في: {PROJECTS_DIR.resolve()}")
    print(f"👉 يمكنك إنشاؤه عبر: python pipeline_cli.py init {slugify_project_name(project_name)}")
    return False


def cmd_list_projects():
    """Lists all configured projects and marks the active one."""
    print("=" * 76)
    print("📋 قائمة مشاريع الموشن جرافيك المتوفرة")
    print("=" * 76)
    if not PROJECTS_DIR.exists():
        print("لا توجد مشاريع منشأة بعد. استخدم: python pipeline_cli.py init <اسم_المشروع>")
        return

    active = get_active_project_name()
    projs = [d for d in PROJECTS_DIR.iterdir() if d.is_dir()]
    if not projs:
        print("لا توجد مشاريع منشأة بعد. استخدم: python pipeline_cli.py init <اسم_المشروع>")
        return

    print(f"{'اسم المشروع':<25} | {'الحالة':<12} | {'عدد السكاشن':<14} | {'تاريخ الإنشاء'}")
    print("-" * 76)
    for p in sorted(projs, key=lambda x: x.name):
        meta_file = p / "project.json"
        num_sec = len(list((p / "sections").glob("section_*"))) if (p / "sections").exists() else 0
        created = "—"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                created = meta.get("created_at", "")[:16].replace("T", " ")
                num_sec = meta.get("num_sections", num_sec)
            except Exception:
                pass
        is_act = "⭐ [ACTIVE]" if p.name == active else ""
        print(f"{p.name:<25} | {is_act:<12} | {num_sec:<14} | {created}")
    print("=" * 76)
    print(f"👉 للتبديل بين المشاريع: python pipeline_cli.py use <اسم_المشروع>")


def cmd_paths(project: Optional[str] = None):
    """Displays detailed input/output directories and checklist for a project."""
    proj = get_project_dirs(project, create=False)
    print("=" * 76)
    print(f"🔍 تفاصيل ومسارات مشروع: [{proj['name'].upper()}]")
    print("=" * 76)

    # Check script
    ms_exists = "✅ موجود" if proj["master_script"].exists() else "❌ غير موجود بعد"
    print(f"📝 1. الاسكربت الصوتي (Voice Script):")
    print(f"   • المسار: {proj['master_script'].resolve()}")
    print(f"   • الحالة: {ms_exists}\n")

    # Check storyboards
    sb_dir = proj["storyboards_dir"]
    sbs = list(sb_dir.glob("section_*.*")) if sb_dir.exists() else []
    print(f"🎨 2. مجلد الاستوري بورد (Storyboards):")
    print(f"   • المسار: {sb_dir.resolve()}")
    print(f"   • عدد الصور المتوفرة: {len(sbs)} صور")
    for s in sbs[:5]:
        print(f"     - {s.name}")
    if len(sbs) > 5:
        print(f"     ... و {len(sbs) - 5} صور أخرى")
    print("")

    # Check exports
    exp_dir = proj["exports_dir"]
    vids = list(exp_dir.glob("*.mp4")) if exp_dir.exists() else []
    print(f"📤 3. مجلد المخرجات (Exports):")
    print(f"   • المسار: {exp_dir.resolve()}")
    print(f"   • الفيديوهات المصدرة: {len(vids)} فيديو")
    for v in vids:
        size_mb = v.stat().st_size / (1024 * 1024)
        print(f"     - {v.name} ({size_mb:.1f} MB)")
    print("=" * 76)


# ==============================================================================
# PIPELINE EXECUTION COMMANDS
# ==============================================================================

def _resolve_target_sections(project: Optional[str], sec_num: Optional[str] = None, all_sections: bool = False) -> List[str]:
    if sec_num is not None and not all_sections:
        return [f"{int(sec_num):02d}"]
    proj = get_project_dirs(project, create=False)
    total = 8
    pjson = proj["proj_dir"] / "project.json"
    if pjson.is_file():
        try:
            total = int(json.loads(pjson.read_text(encoding="utf-8")).get("num_sections", total))
        except Exception:
            pass
    return [f"{i:02d}" for i in range(1, total + 1)]


def cmd_voice(
    sec_num: Optional[str] = None,
    project: Optional[str] = None,
    all_sections: bool = False,
    model_name: Optional[str] = None,
    force: bool = False,
    verify: bool = True,
    pipeline: str = "aion",
    dialect: Optional[str] = None,
    voice_name: Optional[str] = None,
):
    targets = _resolve_target_sections(project, sec_num=sec_num, all_sections=all_sections)
    all_ok = True
    for s in targets:
        paths = get_section_paths(s, project=project)
        print("=" * 70)
        print(f"🎙️ GENERATING VOICEOVER FOR {paths['sec_id'].upper()} (Project: {paths['project']})")
        print("=" * 70)

        text = get_section_text(paths, s)
        if not text:
            print(f"❌ Could not find script for Section {s} in:")
            print(f"   1) {paths['section_script']}")
            print(f"   2) {paths['master_script']}")
            all_ok = False
            continue
        print(f"• Words Count: {len(text.split())}")
        print(f"• Snippet    : {text[:80]}...\n")

        cfg = dict(get_project_config(project))
        from core.aion.voice_stage import _FEMALE_VOICES, is_egyptian_dialect
        if dialect:
            cfg["dialect"] = dialect
            if not str(cfg.get("language", "ar")).lower().startswith("en"):
                if is_egyptian_dialect(dialect):
                    is_fem = ("female" in dialect.lower()) or (str(voice_name or "").lower() in _FEMALE_VOICES)
                    if cfg.get("tts_profile") in ("SAUDI_YOUTH_CREATOR", "EGYPTIAN_YOUTH_CREATOR", "EGYPTIAN_FEMALE_CREATOR"):
                        cfg["tts_profile"] = "EGYPTIAN_FEMALE_CREATOR" if is_fem else "EGYPTIAN_YOUTH_CREATOR"
                    if cfg.get("director_note") in ("HIGH_ENERGY_YOUTUBE", "HIGH_ENERGY_EGYPTIAN_YT"):
                        cfg["director_note"] = "HIGH_ENERGY_EGYPTIAN_YT"
                    if is_fem and not voice_name and str(cfg.get("tts_voice", "")).lower() not in _FEMALE_VOICES:
                        cfg["tts_voice"] = "Kore"
                elif dialect.lower() in ("saudi_white", "saudi", "gulf"):
                    if str(cfg.get("tts_profile", "")).startswith("EGYPTIAN_"):
                        cfg["tts_profile"] = "SAUDI_YOUTH_CREATOR"
                    if cfg.get("director_note") == "HIGH_ENERGY_EGYPTIAN_YT":
                        cfg["director_note"] = "HIGH_ENERGY_YOUTUBE"
        if voice_name:
            cfg["tts_voice"] = voice_name
            if is_egyptian_dialect(cfg.get("dialect", ""), cfg.get("tts_profile", ""), cfg.get("director_note", "")):
                if voice_name.lower() in _FEMALE_VOICES and cfg.get("tts_profile") == "EGYPTIAN_YOUTH_CREATOR":
                    cfg["tts_profile"] = "EGYPTIAN_FEMALE_CREATOR"
                elif voice_name.lower() not in _FEMALE_VOICES and cfg.get("tts_profile") == "EGYPTIAN_FEMALE_CREATOR":
                    cfg["tts_profile"] = "EGYPTIAN_YOUTH_CREATOR"

        if pipeline == "legacy":
            from voice_studio.engine import VoiceStudioEngine
            engine = VoiceStudioEngine()
            print(f"• Model       : {engine.model}")
            print(f"• Language    : {cfg['language']} ({cfg['dialect']})")
            print(f"• Voice/Prof  : {cfg['tts_voice']} / {cfg['tts_profile']}")
            print(f"• Output Path : {paths['audio_wav']}")
            res = engine.generate_speech(
                transcript=text,
                output_wav_path=str(paths["audio_wav"]),
                voice_name=cfg["tts_voice"],
                profile_key=cfg["tts_profile"],
                director_note_key=cfg["director_note"],
                temperature=0.75,
                speed=1.0,
            )
            print(f"✅ Voice generated: {res['duration']:.2f}s ({res['sample_rate']} Hz)")
        else:
            from core.aion.voice_stage import synthesize_section_voice
            mdl = model_name or cfg.get("tts_model", "gemini-3.1-flash-tts-preview")
            print(f"• Model       : {mdl}")
            print(f"• Language    : {cfg['language']} ({cfg['dialect']})")
            print(f"• Voice/Prof  : {cfg['tts_voice']} / {cfg['tts_profile']} [{cfg['director_note']}]")
            print(f"• Output Path : {paths['audio_wav']}")
            res = synthesize_section_voice(
                script_text=text,
                final_wav=paths["audio_wav"],
                language=cfg["language"],
                dialect=cfg["dialect"],
                voice_name=cfg["tts_voice"],
                profile_key=cfg["tts_profile"],
                note_key=cfg["director_note"],
                model_name=mdl,
                force=force,
                verify_with_whisper=verify,
                project_dir=paths["proj_dir"],
            )
            print(f"✅ Voice generated: {res['duration']:.2f}s ({res['sample_rate']} Hz, chunks={res['chunks']})")
    return all_ok


def cmd_timing(
    sec_num: Optional[str] = None,
    project: Optional[str] = None,
    all_sections: bool = False,
    force: bool = False,
):
    targets = _resolve_target_sections(project, sec_num=sec_num, all_sections=all_sections)
    all_ok = True
    cfg = get_project_config(project)
    for s in targets:
        paths = get_section_paths(s, project=project)
        print("=" * 70)
        print(f"⏱️ GENERATING TIMING & SRT ALIGNMENT FOR {paths['sec_id'].upper()} (Project: {paths['project']})")
        print("=" * 70)

        if not paths["audio_wav"].exists():
            print(f"❌ Audio file not found: {paths['audio_wav']}. Run 'voice' first.")
            all_ok = False
            continue

        script_text = get_section_text(paths, s)
        if not script_text:
            print(f"❌ Valid script missing for Section {s}. Run 'script' first.")
            all_ok = False
            continue

        from core.aion.timing_stage import run_timing_alignment
        print(f"• Transcribing audio with Faster-Whisper (language={cfg['language']})...")
        payload = run_timing_alignment(
            sec_id=paths["sec_id"],
            wav_path=paths["audio_wav"],
            script_text=script_text,
            timing_dir=paths["timing_dir"],
            language=cfg["language"],
            model_name=cfg.get("tts_model", "gemini-3.1-flash-tts-preview"),
            voice_name=cfg.get("tts_voice", "Fenrir"),
            force=force,
        )
        word_srt = paths["timing_dir"] / f"{paths['sec_id']}_word_by_word.srt"
        master_json = paths["timing_dir"] / f"{paths['sec_id']}_timing_master.json"
        print(f"✅ Timing synthesis complete: {payload['duration']:.2f}s, {payload['words_count']} words aligned.")
        print(f"• Word SRT   : {word_srt}")
        print(f"• Master JSON: {master_json}")

    if all_sections:
        from core.aion.timing_stage import write_all_sections_timing_index
        proj = get_project_dirs(project, create=False)
        idx = write_all_sections_timing_index(proj["proj_dir"], cfg)
        if idx:
            print(f"📑 Updated Timing Index: {idx}")
    return all_ok


def cmd_extract(
    sec_num: Optional[str] = None,
    project: Optional[str] = None,
    all_sections: bool = False,
    mode: str = "grid",
    rows: int = 4,
    cols: int = 5,
    from_zip: Optional[str] = None,
):
    if from_zip:
        proj = get_project_dirs(project)
        from core.aion.extract_stage import import_extracted_assets_zip
        print(f"📦 Importing pre-extracted assets from ZIP: {from_zip} -> {proj['proj_dir']}...")
        res = import_extracted_assets_zip(proj["proj_dir"], Path(from_zip))
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return bool(res.get("ok"))

    targets = _resolve_target_sections(project, sec_num=sec_num, all_sections=all_sections)
    all_ok = True
    for s in targets:
        paths = get_section_paths(s, project=project)
        print("=" * 70)
        print(f"✂️ TOPOLOGICAL CONNECTIVITY & CONTOUR EXTRACTOR FOR {paths['sec_id'].upper()}")
        print("=" * 70)

        if not paths["storyboard_png"].exists():
            print(f"❌ Storyboard image not found: {paths['storyboard_png']}")
            print(f"👉 Please place the storyboard image at:")
            print(f"   {paths['storyboard_png']}")
            all_ok = False
            continue

        from core.aion.extract_stage import run_extract_stage
        print(f"🎨 Extracting ({mode}) from {paths['storyboard_png'].name}...")
        res = run_extract_stage(paths["sec_dir"], paths["storyboard_png"], mode=mode, rows=rows, cols=cols)
        if isinstance(res, dict) and "assets_count" in res:
            print(f"✅ Extracted {res['assets_count']} HD assets -> {paths['assets_dir']}")
    return all_ok


def _use_aion_for_section(proj_dir: Path, sec_id: str, pipeline: str) -> bool:
    if pipeline == "legacy":
        return False
    if pipeline == "aion":
        return True
    return (proj_dir / "director" / sec_id / "scene_graph.json").is_file()


def _detect_mp4_res_tag(mp4_path: Path) -> str:
    """Return '720p' or '1080p' matching the actual rendered MP4 dimensions."""
    try:
        pr = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(mp4_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if pr.returncode == 0:
            st = (json.loads(pr.stdout).get("streams") or [{}])[0]
            if max(int(st.get("width", 1280)), int(st.get("height", 720))) > 1280:
                return "1080p"
    except Exception:
        pass
    return "720p"


def _downscale_mp4_to_720p_inplace(mp4_path: Path) -> None:
    """Ensure legacy-rendered MP4 outputs are 720p when `--resolution 720p` (default) is active."""
    if not mp4_path.is_file() or _detect_mp4_res_tag(mp4_path) == "720p":
        return
    tmp_720 = mp4_path.with_suffix(".720p.tmp.mp4")
    pr = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(mp4_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    st = (json.loads(pr.stdout).get("streams") or [{}])[0] if pr.returncode == 0 else {}
    sw, sh = int(st.get("width", 1920)), int(st.get("height", 1080))
    tw, th = (720, 1280) if sh > sw else (1280, 720)
    res = subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(mp4_path),
            "-vf", f"scale={tw}:{th}:flags=lanczos",
            "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-c:a", "copy", str(tmp_720),
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if res.returncode == 0 and tmp_720.is_file():
        tmp_720.replace(mp4_path)


def cmd_render(
    sec_num: Optional[str] = None,
    engine: str = "effectcraft",
    project: Optional[str] = None,
    all_sections: bool = False,
    pipeline: str = "auto",
    run_id: Optional[str] = None,
    use_gpu: bool = True,
    rollback_on_fail: bool = True,
    resolution: str = "720p",
):
    targets = _resolve_target_sections(project, sec_num=sec_num, all_sections=all_sections)
    proj = get_project_dirs(project)
    all_ok = True

    from core.aion.run_manager import IsolatedRunManager
    rm = IsolatedRunManager(proj["proj_dir"], proj["name"])
    rid: Optional[str] = None

    for s in targets:
        paths = get_section_paths(s, project=project)
        sec_id = paths["sec_id"]
        if _use_aion_for_section(proj["proj_dir"], sec_id, pipeline):
            if rid is None:
                rid = rm.allocate_run_id(requested=run_id)
                rm.init_or_load_run(rid, config={"pipeline": "aion", "engine": engine, "gpu": use_gpu})
            sg_path = proj["proj_dir"] / "director" / sec_id / "scene_graph.json"
            if not sg_path.is_file():
                print(f"❌ Scene graph not found: {sg_path}. Run 'direct --section {s}' first.")
                all_ok = False
                continue

            out_dir = rm.section_out_dir(rid, sec_id)
            work_dir = rm.section_work_dir(rid, sec_id)
            out_ecproj = out_dir / f"{sec_id}_aion_editable.ecproj"
            out_mp4 = out_dir / f"{sec_id}_aion_master.mp4"
            mix_wav = work_dir / f"{sec_id}_aion_mix.wav"
            print("=" * 70)
            print(f"🎬 AION GPU RENDER {sec_id.upper()} (Project: {paths['project']}, Run: {rid})")
            print(f"• Target MP4 : {out_mp4}")
            print("=" * 70)

            sg = json.loads(sg_path.read_text(encoding="utf-8"))
            from core.aion.motion_and_audio import mix_scene_graph_audio
            from core.aion.effectcraft_compiler import EffectCraftSceneCompiler

            with rm.stage_transaction(rid, sec_id, "render", watch_paths=[out_ecproj, out_mp4], rollback_on_fail=rollback_on_fail):
                narr_wav = proj["proj_dir"] / (sg.get("source_timeline", {}).get("audio_file") or f"sections/{sec_id}/voice/{sec_id}.wav")
                if not mix_wav.is_file():
                    if not narr_wav.is_file():
                        raise FileNotFoundError(f"Audio not found: {narr_wav}")
                    mix_scene_graph_audio(narr_wav, sg.get("sfx_cues", []), mix_wav)
                compiler = EffectCraftSceneCompiler(section_dir=paths["sec_dir"], work_dir=work_dir)
                ec_res = compiler.build_and_render(sg, None, mix_wav, out_ecproj, out_mp4, use_gpu=use_gpu, resolution=resolution)
                if not ec_res.get("ok"):
                    raise RuntimeError(f"EffectCraft render failed: {ec_res}")
                rm.mark_stage(rid, sec_id, "render", "COMPLETED", outputs=[str(out_mp4), str(out_ecproj)], metrics=ec_res)
                print(f"✅ AION Render finished ({resolution}, {ec_res.get('render_sec')}s): {out_mp4}")
            continue

        # Legacy manifest.json path preserved identically for full backward compatibility
        print("=" * 70)
        print(f"🎬 RENDERING {resolution.upper()} MASTER V7 FOR {paths['sec_id'].upper()} (Engine: {engine.upper()})")
        print(f"• Project    : {paths['project']}")
        print(f"• Target MP4 : {paths['export_mp4']}")
        print("=" * 70)

        if not paths["manifest_json"].exists():
            print(f"❌ Manifest not found: {paths['manifest_json']}")
            all_ok = False
            continue
        if not paths["audio_wav"].exists():
            print(f"❌ Audio not found: {paths['audio_wav']}")
            all_ok = False
            continue

        if engine == "effectcraft":
            from core_engine.effectcraft_director import EffectCraftMotionEngine
            from core_engine.media_compositor import enhance_section
            raw_render_mp4 = paths["sec_dir"] / f"{paths['sec_id']}_raw_render.mp4"
            ec_engine = EffectCraftMotionEngine(section_dir=paths["sec_dir"], output_dir=paths["export_dir"])
            ec_engine.render(out_mp4=raw_render_mp4)
            out_v7 = enhance_section(proj["proj_dir"], paths["sec_id"])
            if out_v7 and out_v7.exists():
                if str(resolution).lower() == "720p":
                    _downscale_mp4_to_720p_inplace(out_v7)
                print(f"✅ Render & V7 Enhancement finished successfully: {out_v7}")
            else:
                all_ok = False
        else:
            from core_engine.universal_staged_director_v2 import UniversalStagedDirectorV2
            director = UniversalStagedDirectorV2(manifest_path=str(paths["manifest_json"]))
            director.export_video(output_mp4=str(paths["export_mp4"]), audio_wav=str(paths["audio_wav"]))
            if str(resolution).lower() == "720p" and paths["export_mp4"].exists():
                _downscale_mp4_to_720p_inplace(paths["export_mp4"])
            print(f"✅ Render finished successfully: {paths['export_mp4']}")

    return all_ok


def cmd_status(project: Optional[str] = None, detailed: bool = False):
    proj = get_project_dirs(project, create=False)
    total_sections = 10
    if proj["is_project"]:
        proj_json = proj["proj_dir"] / "project.json"
        if proj_json.exists():
            try:
                with open(proj_json, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    total_sections = meta.get("num_sections", 10)
            except Exception:
                pass

    print("=" * 86)
    print(f"📊 WHITEBOARD PIPELINE STATUS — PROJECT: [{proj['name'].upper()}]")
    print("=" * 86)
    print(f"{'Section':<12} | {'Script':<8} | {'Storyboard':<12} | {'Voice (WAV)':<12} | {'Timing (SRT)':<14} | {'Assets':<8} | {'Export (MP4)':<14}")
    print("-" * 86)

    for i in range(1, total_sections + 1):
        paths = get_section_paths(str(i), project=proj["name"] if proj["is_project"] else None, create=False)
        sec_label = paths["sec_id"]

        has_script = "✅" if (paths["section_script"].exists() or paths["master_script"].exists()) else "❌"
        has_sb = "✅" if paths["storyboard_png"].exists() else "⏳"
        has_voice = "✅" if paths["audio_wav"].exists() else "⏳"
        has_timing = "✅" if (paths["timing_dir"] / f"{paths['sec_id']}_word_by_word.srt").exists() else "⏳"
        has_assets = "✅" if (paths["assets_dir"] / "metadata.json").exists() else "⏳"
        aion_sg = (proj["proj_dir"] / "director" / sec_label / "scene_graph.json").exists()
        aion_mp4 = (proj["exports_dir"] / sec_label / f"{sec_label}_aion_master.mp4").exists()
        has_export = "✅" if (paths["export_mp4"].exists() or aion_mp4) else ("📐" if aion_sg else "⏳")

        print(f"{sec_label:<12} | {has_script:<8} | {has_sb:<12} | {has_voice:<12} | {has_timing:<14} | {has_assets:<8} | {has_export:<14}")
    print("=" * 86)

    from core.aion.run_manager import IsolatedRunManager
    rm = IsolatedRunManager(proj["proj_dir"], proj["name"])
    runs = rm.list_runs()
    if runs or detailed:
        latest = rm.get_latest_run_id()
        print(f"\n📦 AION ISOLATED RUNS ({len(runs)}): latest={latest or 'none'}")
        if latest:
            print(f"   Run Manifest: {rm.manifest_path(latest)}")
            for i in range(1, total_sections + 1):
                sid = f"section_{i:02d}"
                done = rm.completed_stages(latest, sid)
                nxt = rm.resolve_resume_stage(latest, sid)
                print(f"   • {sid}: completed={len(done)} [{','.join(done) if done else '-'}] -> next={nxt}")


def cmd_merge(
    project: Optional[str] = None,
    run_id: Optional[str] = None,
    pipeline: str = "auto",
    out_file: Optional[str] = None,
):
    proj = get_project_dirs(project, create=False)
    print("=" * 80)
    print(f"🎬 CONCATENATING FULL DOCUMENTARY MASTER FOR: [{proj['name'].upper()}]")
    print("=" * 80)

    exp_dir = proj["exports_dir"]
    from core.aion.run_manager import IsolatedRunManager
    rm = IsolatedRunManager(proj["proj_dir"], proj["name"])
    target_rid = run_id or rm.get_latest_run_id()

    sec_files: List[Path] = []
    target_mp4 = Path(out_file) if out_file else (exp_dir / f"{proj['name']}_full_movie_master.mp4")
    concat_list = exp_dir / "concat_list.txt"

    if pipeline != "legacy" and target_rid:
        r_sec_root = rm.run_dir(target_rid) / "sections"
        cand_files = sorted(r_sec_root.glob("section_*/section_*_aion_master.mp4"))
        if cand_files:
            sec_files = cand_files
            if not out_file:
                res_tag = _detect_mp4_res_tag(sec_files[0])
                target_mp4 = rm.run_dir(target_rid) / f"{proj['name']}_{target_rid}_master_{res_tag}.mp4"
            concat_list = rm.run_dir(target_rid) / "concat_list.txt"

    if not sec_files and pipeline != "legacy":
        aion_root_files = sorted(exp_dir.glob("section_*/section_*_aion_master.mp4"))
        if aion_root_files:
            sec_files = aion_root_files
            if not out_file:
                rid = rm.allocate_run_id()
                rm.run_dir(rid).mkdir(parents=True, exist_ok=True)
                res_tag = _detect_mp4_res_tag(sec_files[0])
                target_mp4 = rm.run_dir(rid) / f"{proj['name']}_full_master_{res_tag}.mp4"
                concat_list = rm.run_dir(rid) / "concat_list.txt"

    if not sec_files:
        sec_files = sorted(list(exp_dir.glob("section_*_master_v7.mp4")))
    if not sec_files:
        sec_files = sorted(list(exp_dir.glob("section_*_master_v6.mp4")))
    if not sec_files:
        sec_files = sorted(list(exp_dir.glob("section_*.mp4")))

    if not sec_files:
        print(f"❌ No rendered section videos found in: {exp_dir}")
        return False

    print(f"• Found {len(sec_files)} rendered sections:")
    for sf in sec_files:
        print(f"  - {sf.name} ({sf.stat().st_size / (1024*1024):.1f} MB)")

    concat_list.parent.mkdir(parents=True, exist_ok=True)
    with open(concat_list, "w", encoding="utf-8") as f:
        for sf in sec_files:
            clean_p = str(sf.resolve()).replace("\\", "/")
            f.write(f"file '{clean_p}'\n")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(target_mp4)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        re_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            str(target_mp4),
        ]
        res = subprocess.run(re_cmd, capture_output=True, text=True)

    if res.returncode == 0:
        if target_rid:
            rm.mark_stage(target_rid, None, "merge", "COMPLETED", outputs=[str(target_mp4)])
        print(f"\n🎉 FULL MOVIE CONCATENATION COMPLETE: {target_mp4}")
        print(f"• Size: {target_mp4.stat().st_size / (1024*1024):.1f} MB")
        return True
    else:
        print(f"❌ Concat failed: {res.stderr}")
        return False


def cmd_enhance(sec_num: Optional[str] = None, all_sections: bool = False, project: Optional[str] = None):
    """Enhances rendered section(s) with micro-retention GIF overlays and pure voice narration (ZERO-BGM POLICY)."""
    proj = get_project_dirs(project)
    clean_name = proj["name"]
    from core_engine.media_compositor import enhance_section

    if all_sections or not sec_num:
        sec_dirs = sorted((proj["proj_dir"] / "sections").glob("section_*"))
        if not sec_dirs:
            print(f"[-] No section folders found in {proj['proj_dir'] / 'sections'}")
            return False
        for s_path in sec_dirs:
            s_id = s_path.name
            print(f"\n✨ Enhancing {s_id} (Micro-Retention Overlays + Pure Voiceover, ZERO BGM)...")
            enhance_section(proj["proj_dir"], s_id)
        return True
    else:
        sec_id = f"section_{int(sec_num):02d}"
        print(f"\n✨ Enhancing {sec_id} (Micro-Retention Overlays + Pure Voiceover, ZERO BGM)...")
        out_v7 = enhance_section(proj["proj_dir"], sec_id)
        return bool(out_v7 and out_v7.exists())


def synthesize_default_grounded_manifest(paths: Dict[str, Any], sec_num: str) -> bool:
    """Synthesizes a high-aesthetic, grounded EffectCraft manifest adhering to all choreography rules:
    - Eye-comfort paper background (#EDE8E0)
    - Ground line Y=840 for characters
    - Phased staging to eliminate collisions
    - Clean 0.35s exit sweep before scene end
    - Text cards synced to Whisper timing

    """
    timing_file = paths["timing_dir"] / f"{paths['sec_id']}_timing_master.json"
    audio_wav = paths["audio_wav"]
    assets_dir = paths["assets_dir"]
    manifest_path = paths["manifest_json"]

    total_duration = 20.0
    words_data = []

    if timing_file.exists():
        try:
            with open(timing_file, "r", encoding="utf-8") as f:
                t_data = json.load(f)
                total_duration = float(t_data.get("duration", 20.0))
                words_data = t_data.get("words", [])
        except Exception:
            pass
    elif audio_wav.exists():
        try:
            import wave
            with wave.open(str(audio_wav), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                total_duration = round(frames / float(rate), 2)
        except Exception:
            pass

    # Gather extracted assets (prioritize composite entities)
    asset_files = []
    if assets_dir.exists():
        comps = sorted(assets_dir.glob("*_composite.png"))
        if comps:
            asset_files = [p.stem for p in comps]
        else:
            for p in sorted(assets_dir.glob("*.png")):
                if any(x in p.name.lower() for x in ["test_", "preview", "contact_sheet", "map", "frame_", "_fx", "_core"]):
                    continue
                asset_files.append(p.stem)

    # Determine scenes so ALL extracted assets are used in 2-beat phased storytelling
    num_assets = len(asset_files)
    if num_assets >= 6:
        # 2 assets per scene beat (~3.2s - 4.0s per asset)
        num_scenes = max(4, min(10, int(round(num_assets / 2.0))))
    else:
        ideal_scene_dur = 8.0
        num_scenes = max(1, int(round(total_duration / ideal_scene_dur)))
    scene_dur = total_duration / num_scenes

    scenes = []
    theme_cycle = ["crimson", "royal", "amber", "emerald"]
    entrances_cycle = ["whip_motion", "pop_bounce", "slide_in", "elastic_overshoot", "squash_drop", "card_stack"]

    for s_idx in range(num_scenes):
        s_start = round(s_idx * scene_dur, 2)
        s_end = round(min(total_duration, (s_idx + 1) * scene_dur), 2)
        sc_id = f"scene_{s_idx+1:02d}"

        # Distribute all assets evenly across scenes
        idx_a = int(round(s_idx * num_assets / float(num_scenes))) if num_assets else 0
        idx_b = int(round((s_idx + 1) * num_assets / float(num_scenes))) if num_assets else 0
        sc_assets = asset_files[idx_a:idx_b]
        if not sc_assets and asset_files:
            sc_assets = [asset_files[s_idx % num_assets]]

        elements = []
        n_sc_assets = len(sc_assets)
        # If 3+ assets fall into this scene, split into Phase A (first half) and Phase B (second half)
        s_mid = round((s_start + s_end) / 2.0, 2)
        for a_idx, a_key in enumerate(sc_assets[:4]):
            pos_x = 560 if (a_idx % 2 == 0) else 1380
            pos_y = 840 if (a_idx % 2 == 0) else 520
            is_grounded = (pos_y == 840)
            target_size = 540 if (a_idx % 2 == 0) else 460

            if n_sc_assets <= 2:
                elem_start = round(s_start + (a_idx * 1.4), 2)
                elem_end = round(s_end - 0.35, 2) if (s_idx == num_scenes - 1) else s_end
            else:
                if a_idx < 2:
                    elem_start = round(s_start + (a_idx * 0.8), 2)
                    elem_end = round(s_mid - 0.15, 2)
                else:
                    elem_start = round(s_mid + ((a_idx - 2) * 0.8), 2)
                    elem_end = round(s_end - 0.35, 2) if (s_idx == num_scenes - 1) else s_end

            anim = entrances_cycle[(s_idx + a_idx) % len(entrances_cycle)]
            punch_t = round(elem_start + (elem_end - elem_start) * 0.38, 2)
            sweep_t = round(elem_start + (elem_end - elem_start) * 0.65, 2)

            elem_entry = {
                "asset_key": a_key,
                "start": elem_start,
                "end": elem_end,
                "pos": [pos_x, pos_y],
                "grounded": is_grounded,
                "target_size": target_size,
                "entrance": anim,
                "exit": "shrink_out",
                "scale_punches": [{"time": punch_t}] if (punch_t < elem_end - 0.45) else [],
                "effects": [
                    {"type": "light_sweep", "time": sweep_t, "duration": 0.45, "intensity": 20.0, "width": 22, "color": "gold"}
                ] if (sweep_t < elem_end - 0.45) else []
            }
            elements.append(elem_entry)

        # Build 3-to-4 word Arabic headline phrases from words_data in this scene window
        sc_words = []
        win_words = [w for w in words_data if s_start <= float(w.get("start", 0)) < (s_end - 0.8)]
        if win_words:
            # Card 1 in first half of scene
            chunk1 = win_words[:4]
            phrase1 = " ".join(re.sub(r'[:،.؟!""]', '', w.get("word", "")).strip() for w in chunk1).strip()
            if len(phrase1) >= 6:
                w1_st = round(float(chunk1[0].get("start", s_start + 0.3)), 2)
                w1_en = round(min(s_mid - 0.1 if len(win_words) >= 8 else s_end - 0.35, w1_st + 3.2), 2)
                if w1_en > w1_st + 1.0:
                    sc_words.append({
                        "word": phrase1,
                        "theme": theme_cycle[s_idx % len(theme_cycle)],
                        "start": w1_st,
                        "end": w1_en,
                        "pos": [1340, 220]
                    })
            # Card 2 in second half of scene if enough words
            if len(win_words) >= 8:
                mid_idx = len(win_words) // 2
                chunk2 = win_words[mid_idx:mid_idx + 4]
                phrase2 = " ".join(re.sub(r'[:،.؟!""]', '', w.get("word", "")).strip() for w in chunk2).strip()
                if len(phrase2) >= 6:
                    w2_st = round(float(chunk2[0].get("start", s_mid + 0.2)), 2)
                    w2_en = round(min(s_end - 0.35, w2_st + 3.2), 2)
                    if w2_en > w2_st + 1.0:
                        sc_words.append({
                            "word": phrase2,
                            "theme": theme_cycle[(s_idx + 1) % len(theme_cycle)],
                            "start": w2_st,
                            "end": w2_en,
                            "pos": [580, 220]
                        })

        scene_obj = {
            "id": sc_id,
            "start": s_start,
            "end": s_end,
            "camera": {
                "zoom_start": 1.0,
                "zoom_end": 1.08 if s_idx == 0 else 1.05,
                "duration": round(s_end - s_start, 2)
            },
            "description": f"Scene {s_idx+1}",
            "elements": elements,
            "words": sc_words
        }
        if s_idx == 0:
            scene_obj["camera_effects"] = [
                {"type": "border_flash", "time": round(s_start + 1.1, 2), "color": "red", "opacity": 42.0, "pulses": 2}
            ]
        scenes.append(scene_obj)

    manifest = {
        "section_id": paths["sec_id"],
        "project": paths["project"],
        "title": f"{paths['project']} — {paths['sec_id']}",
        "total_duration": total_duration,
        "fps": 30,
        "resolution": [1920, 1080],
        "theme": {
            "name": "eye_comfort_paper"
        },
        "enable_sfx": True,
        "scenes": scenes
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"✨ Synthesized grounded cinematic manifest for {paths['sec_id']}: {len(scenes)} scenes, {sum(len(s['elements']) for s in scenes)} elements.")
    return True


def cmd_script(sec_num: Optional[str] = None, project: Optional[str] = None, all_sections: bool = False, split: bool = True):
    proj = get_project_dirs(project, create=False)
    from core.aion.script_stage import run_script_stage
    target_num = None if (all_sections or sec_num is None) else int(sec_num)
    rep = run_script_stage(proj["proj_dir"], sec_num=target_num, split=split)
    print(f"📝 SCRIPT STAGE [{proj['name']}] -> ok={rep['ok']} | split={rep['split_written']}")
    for sid, info in sorted(rep["sections"].items()):
        flag = "✅" if info["valid"] else "❌"
        print(f"  {flag} {sid}: {info['words']} words" + (f" ({info['warning']})" if info["warning"] else ""))
    return rep["ok"]


def cmd_semantic_map(sec_num: Optional[str] = None, project: Optional[str] = None, all_sections: bool = False, force: bool = False):
    proj = get_project_dirs(project)
    from core.aion.director_stages import run_semantic_map_stage
    all_ok = True
    for s in _resolve_target_sections(project, sec_num=sec_num, all_sections=all_sections):
        sid = f"section_{int(s):02d}"
        try:
            mp = run_semantic_map_stage(proj["proj_dir"], sid, force=force)
            print(f"🧭 SEMANTIC MAP [{sid}]: {mp['assets_count']} assets -> {mp['sentences_count']} sentences")
        except Exception as exc:
            print(f"❌ SEMANTIC MAP [{sid}]: {exc}")
            all_ok = False
    return all_ok


def cmd_brief(sec_num: Optional[str] = None, project: Optional[str] = None, all_sections: bool = False, force: bool = False):
    proj = get_project_dirs(project)
    cfg = get_project_config(project)
    from core.aion.director_stages import run_brief_stage
    for s in _resolve_target_sections(project, sec_num=sec_num, all_sections=all_sections):
        sid = f"section_{int(s):02d}"
        br = run_brief_stage(proj["proj_dir"], sid, cfg, force=force)
        print(f"🎨 CREATIVE BRIEF [{sid}]: lang={br['language']} dir={br['text_direction']} font={br['typography_font']}")
    return True


def cmd_direct(sec_num: Optional[str] = None, project: Optional[str] = None, all_sections: bool = False, force: bool = False):
    proj = get_project_dirs(project)
    cfg = get_project_config(project)
    from core.aion.director_stages import run_direct_stage
    all_ok = True
    for s in _resolve_target_sections(project, sec_num=sec_num, all_sections=all_sections):
        sid = f"section_{int(s):02d}"
        try:
            sg = run_direct_stage(proj["proj_dir"], sid, cfg, force=force)
            print(f"🎬 DIRECTOR SCENE GRAPH [{sid}]: {len(sg.get('scenes', []))} scenes, dur={sg['source_timeline']['duration_sec']}s")
        except Exception as exc:
            print(f"❌ DIRECTOR [{sid}]: {exc}")
            all_ok = False
    return all_ok


def cmd_motion(sec_num: Optional[str] = None, project: Optional[str] = None, all_sections: bool = False, run_id: Optional[str] = None):
    proj = get_project_dirs(project)
    from core.aion.motion_and_audio import run_motion_stage
    from core.aion.run_manager import IsolatedRunManager
    rm = IsolatedRunManager(proj["proj_dir"], proj["name"])
    rid = run_id or rm.get_latest_run_id()
    all_ok = True
    for s in _resolve_target_sections(project, sec_num=sec_num, all_sections=all_sections):
        sid = f"section_{int(s):02d}"
        wdir = rm.section_work_dir(rid, sid) if rid else (proj["proj_dir"] / "work" / sid)
        try:
            res = run_motion_stage(proj["proj_dir"], sid, work_dir=wdir)
            print(f"🎞️ MOTION PREP [{sid}]: {res['assets_prepared']} assets -> {res['motion_plan']}")
        except Exception as exc:
            print(f"❌ MOTION PREP [{sid}]: {exc}")
            all_ok = False
    return all_ok


def cmd_sfx(sec_num: Optional[str] = None, project: Optional[str] = None, all_sections: bool = False, run_id: Optional[str] = None):
    proj = get_project_dirs(project)
    from core.aion.motion_and_audio import run_sfx_stage
    from core.aion.run_manager import IsolatedRunManager
    rm = IsolatedRunManager(proj["proj_dir"], proj["name"])
    rid = run_id or rm.get_latest_run_id()
    all_ok = True
    for s in _resolve_target_sections(project, sec_num=sec_num, all_sections=all_sections):
        sid = f"section_{int(s):02d}"
        wdir = rm.section_work_dir(rid, sid) if rid else (proj["proj_dir"] / "work" / sid)
        try:
            rep = run_sfx_stage(proj["proj_dir"], sid, work_dir=wdir)
            print(f"🔊 SFX MIX [{sid}]: placed={rep['placed_cues_count']} missing={rep['missing_cues']} -> {rep['out_wav']}")
        except Exception as exc:
            print(f"❌ SFX MIX [{sid}]: {exc}")
            all_ok = False
    return all_ok


def cmd_qa(sec_num: Optional[str] = None, project: Optional[str] = None, all_sections: bool = False, run_id: Optional[str] = None):
    proj = get_project_dirs(project, create=False)
    from core.aion.qa_and_doctor import run_qa_stage
    from core.aion.run_manager import IsolatedRunManager
    rm = IsolatedRunManager(proj["proj_dir"], proj["name"])
    rid = run_id or rm.get_latest_run_id()
    all_ok = True
    for s in _resolve_target_sections(project, sec_num=sec_num, all_sections=all_sections):
        sid = f"section_{int(s):02d}"
        if rid and (rm.section_out_dir(rid, sid) / f"{sid}_aion_master.mp4").is_file():
            mp4 = rm.section_out_dir(rid, sid) / f"{sid}_aion_master.mp4"
            aud = rm.section_work_dir(rid, sid) / f"{sid}_aion_mix.wav"
            qdir = rm.section_qa_dir(rid, sid)
        elif (proj["exports_dir"] / sid / f"{sid}_aion_master.mp4").is_file():
            mp4 = proj["exports_dir"] / sid / f"{sid}_aion_master.mp4"
            aud = proj["proj_dir"] / "work" / sid / f"{sid}_aion_mix.wav"
            qdir = proj["proj_dir"] / "qa" / sid
        else:
            mp4 = proj["exports_dir"] / f"{sid}_master_v7.mp4"
            aud = proj["sections_dir"] / sid / "voice" / f"{sid}.wav"
            qdir = proj["proj_dir"] / "qa" / sid
        rep = run_qa_stage(proj["proj_dir"], sid, mp4, aud, qdir)
        print(f"🧪 QA [{sid}]: status={rep['overall_status']} sheet={rep['contact_sheet']}")
        if not rep["ok"]:
            all_ok = False
    return all_ok


def cmd_doctor(as_json: bool = False):
    from core.aion.qa_and_doctor import run_doctor_check
    rep = run_doctor_check()
    if as_json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print("=" * 72)
        print(f"🩺 AION ENVIRONMENT DOCTOR — Healthy: {rep['is_healthy']}")
        print("=" * 72)
        print(f"• Python      : {rep['python_version']}")
        print(f"• Disk Free   : {rep['free_disk_gb']} GB")
        print(f"• FFmpeg      : {rep['ffmpeg']['available']} ({rep['ffmpeg']['hardware_encoder']})")
        print(f"• EffectCraft : {rep['craftapp']['effectcraft_cli']['exists']}")
        print(f"• PhotoCraft  : {rep['craftapp']['photocraft_cli']['exists']}")
        print(f"• AniCraft    : {rep['craftapp']['anicraft_cli']['exists']}")
        print(f"• Gemini Keys : {rep['gemini_api_keys_loaded']}")
        for iss in rep["issues"]:
            print(f"  ⚠️ {iss}")
    return rep["is_healthy"]


def cmd_cli_spec(as_json: bool = True, write_docs: bool = False):
    from core.aion.docgen import extract_parser_spec, render_cli_reference_md
    spec = extract_parser_spec(build_parser())
    if write_docs:
        out_md = ROOT_DIR / "CLI_REFERENCE.md"
        out_md.write_text(render_cli_reference_md(spec), encoding="utf-8")
        print(f"📄 Generated CLI_REFERENCE.md from live parser -> {out_md}")
    if as_json:
        print(json.dumps(spec, indent=2, ensure_ascii=False))
    return True


def cmd_auto(
    project: Optional[str] = None,
    start_sec: int = 1,
    end_sec: Optional[int] = None,
    engine: str = "effectcraft",
    skip_voice: bool = False,
    skip_timing: bool = False,
    skip_extract: bool = False,
    skip_render: bool = False,
    skip_merge: bool = False,
    force: bool = False,
    from_stage: Optional[str] = None,
    to_stage: Optional[str] = None,
    resume: bool = False,
    run_id: Optional[str] = None,
    pipeline: str = "auto",
    mode: str = "grid",
    use_gpu: bool = True,
    rollback_on_fail: bool = True,
    resolution: str = "720p",
):
    """Executes the unified 12-stage production pipeline with resume & isolated runs."""
    proj = get_project_dirs(project)
    clean_name = proj["name"]

    if pipeline == "aion" or resume or from_stage or to_stage or run_id:
        return cmd_run_aion(
            project=clean_name,
            start_sec=start_sec,
            end_sec=end_sec,
            from_stage=from_stage,
            to_stage=to_stage,
            resume=resume,
            run_id=run_id,
            mode=mode,
            use_gpu=use_gpu,
            force=force,
            rollback_on_fail=rollback_on_fail,
            skip_merge=skip_merge,
            resolution=resolution,
        )

    print("=" * 80)
    print(f"🚀 INITIATING AUTONOMOUS WHITEBOARD PRODUCTION LOOP FOR: [{clean_name.upper()}]")
    print("=" * 80)

    # Detect number of sections
    proj_json = proj["proj_dir"] / "project.json"
    total_sections = 10
    if proj_json.exists():
        try:
            with open(proj_json, "r", encoding="utf-8") as f:
                meta = json.load(f)
                total_sections = meta.get("num_sections", 10)
        except Exception:
            pass

    # Or count available storyboard images if greater
    sb_dir = proj["storyboards_dir"]
    if sb_dir.exists():
        sb_files = list(sb_dir.glob("section_*.*"))
        if sb_files:
            max_sb = 0
            for f in sb_files:
                m = re.search(r'section_(\d+)', f.name)
                if m:
                    max_sb = max(max_sb, int(m.group(1)))
            total_sections = max(total_sections, max_sb)

    start = max(1, start_sec)
    end = end_sec if end_sec is not None else total_sections

    print(f"• Active Project : {clean_name}")
    print(f"• Section Range  : {start:02d} -> {end:02d} (Total: {end - start + 1})")
    print(f"• Render Engine  : {engine.upper()}")
    print("-" * 80)

    results = []

    for i in range(start, end + 1):
        sec_num = f"{i:02d}"
        paths = get_section_paths(sec_num, project=clean_name)
        sec_label = paths["sec_id"]
        print(f"\n{'='*30} [LOOP: SECTION {sec_num} / {end:02d}] {'='*30}")

        # 1. Voice
        if not skip_voice:
            if paths["audio_wav"].exists() and not force:
                print(f"⏩ [VOICE] Section {sec_num} WAV already exists. Skipping regeneration.")
            else:
                print(f"🎙️ [VOICE] Generating speech for Section {sec_num}...")
                ok = cmd_voice(sec_num, project=clean_name)
                if not ok:
                    print(f"⚠️ [VOICE] Could not generate audio for {sec_label}. Skipping to next step...")

        # 2. Timing
        if not skip_timing:
            timing_master = paths["timing_dir"] / f"{sec_label}_timing_master.json"
            if timing_master.exists() and not force:
                print(f"⏩ [TIMING] Section {sec_num} timing already exists. Skipping.")
            else:
                if paths["audio_wav"].exists():
                    print(f"⏱️ [TIMING] Aligning Faster-Whisper timing for Section {sec_num}...")
                    cmd_timing(sec_num, project=clean_name)
                else:
                    print(f"⚠️ [TIMING] Audio missing. Skipping timing for {sec_label}.")

        # 3. Storyboard check
        if not paths["storyboard_png"].exists():
            print(f"⚠️ [STORYBOARD] Storyboard image not found for Section {sec_num} in {paths['storyboard_png']}.")
            print(f"⏭️ Skipping extraction and rendering for Section {sec_num} and continuing loop...")
            results.append({"section": sec_label, "status": "SKIPPED_NO_STORYBOARD"})
            continue

        # 4. Extract
        if not skip_extract:
            has_assets = (paths["assets_dir"] / "metadata.json").exists() or len(list(paths["assets_dir"].glob("*.png"))) >= 2
            if has_assets and not force:
                print(f"⏩ [EXTRACT] Assets already extracted for Section {sec_num}. Skipping.")
            else:
                print(f"✂️ [EXTRACT] Extracting organic contours for Section {sec_num}...")
                cmd_extract(sec_num, project=clean_name)

        # 5. Manifest Validation & QA Audit
        if not paths["manifest_json"].exists():
            print(f"📝 [MANIFEST] No manifest found for Section {sec_num}. Auto-synthesizing grounded manifest...")
            synthesize_default_grounded_manifest(paths, sec_num)

        if paths["manifest_json"].exists():
            try:
                from core_engine.director_qa_auditor import DirectorQAAuditor
                is_valid, audit_log = DirectorQAAuditor.audit_and_optimize_manifest(paths["manifest_json"], auto_fix=True)
                for msg in audit_log:
                    print(f"  {msg}")
            except Exception as e:
                print(f"  [!] QA Audit notice: {e}")

        # 6. Render
        if not skip_render:
            if paths["export_mp4"].exists() and not force:
                print(f"⏩ [RENDER] Master video already exists: {paths['export_mp4'].name}. Skipping.")
                results.append({"section": sec_label, "status": "EXISTS"})
            else:
                print(f"🎬 [RENDER] Rendering {resolution.upper()} Master for Section {sec_num}...")
                render_ok = cmd_render(sec_num, engine=engine, project=clean_name, resolution=resolution)
                if render_ok and paths["export_mp4"].exists():
                    size_mb = paths["export_mp4"].stat().st_size / (1024 * 1024)
                    print(f"✅ [RENDER SUCCESS] Section {sec_num} complete ({size_mb:.1f} MB)")
                    results.append({"section": sec_label, "status": "RENDERED", "size_mb": size_mb})
                else:
                    print(f"❌ [RENDER FAILED] Section {sec_num} failed to render.")
                    results.append({"section": sec_label, "status": "FAILED"})

        print(f"🏁 Finished processing Section {sec_num}.")

    # PHASE 3: Merge
    if not skip_merge:
        print("\n" + "=" * 80)
        print(f"🎞️ PHASE 3: CONCATENATING FULL MOVIE MASTER FOR [{clean_name.upper()}]")
        print("=" * 80)
        cmd_merge(project=clean_name)

    # Status Dashboard
    print("\n" + "=" * 80)
    print("📊 FINAL PIPELINE SUMMARY REPORT")
    print("=" * 80)
    cmd_status(project=clean_name)
    print("\n🎉 ALL AUTONOMOUS PRODUCTION OPERATIONS COMPLETED!")
    return True


def cmd_run_aion(
    project: Optional[str] = None,
    start_sec: int = 1,
    end_sec: Optional[int] = None,
    from_stage: Optional[str] = None,
    to_stage: Optional[str] = None,
    resume: bool = False,
    run_id: Optional[str] = None,
    mode: str = "grid",
    use_gpu: bool = True,
    force: bool = False,
    rollback_on_fail: bool = True,
    skip_merge: bool = False,
    resolution: str = "720p",
) -> bool:
    """Unified 12-stage AION pipeline runner with isolated runs, resume & rollback."""
    from core.aion.contracts import PIPELINE_STAGES, SECTION_STAGES
    from core.aion.run_manager import IsolatedRunManager

    proj = get_project_dirs(project)
    clean_name = proj["name"]
    rm = IsolatedRunManager(proj["proj_dir"], clean_name)
    rid = rm.allocate_run_id(requested=run_id, resume=resume)
    rm.init_or_load_run(rid, config={"pipeline": "aion", "mode": mode, "gpu": use_gpu})

    total_sections = 8
    proj_json = proj["proj_dir"] / "project.json"
    if proj_json.is_file():
        try:
            total_sections = int(json.loads(proj_json.read_text(encoding="utf-8")).get("num_sections", total_sections))
        except Exception:
            pass
    start = max(1, start_sec)
    end = end_sec if end_sec is not None else total_sections

    from_idx = PIPELINE_STAGES.index(from_stage) if from_stage else 0
    to_idx = PIPELINE_STAGES.index(to_stage) if to_stage else len(PIPELINE_STAGES) - 1
    if to_idx < from_idx:
        raise ValueError(f"--to-stage ({to_stage}) precedes --from-stage ({from_stage})")

    print("=" * 80)
    print(f"🚀 AION UNIFIED PIPELINE | Project: {clean_name} | Run: {rid} | Resume: {resume}")
    print(f"   Stages: {PIPELINE_STAGES[from_idx]} -> {PIPELINE_STAGES[to_idx]} | Sections: {start:02d}..{end:02d}")
    print("=" * 80)

    overall_ok = True
    for i in range(start, end + 1):
        sec_num = f"{i:02d}"
        sec_id = f"section_{sec_num}"
        paths = get_section_paths(sec_num, project=clean_name)

        eff_from_idx = from_idx
        if resume and not from_stage:
            res_stage = rm.resolve_resume_stage(rid, sec_id)
            eff_from_idx = PIPELINE_STAGES.index(res_stage) if res_stage in PIPELINE_STAGES else 0

        for st in SECTION_STAGES:
            st_idx = PIPELINE_STAGES.index(st)
            if st_idx < eff_from_idx or st_idx > to_idx:
                continue
            if resume and not force and rm.get_stage_status(rid, sec_id, st) == "COMPLETED":
                print(f"⏩ [{sec_id}] Stage '{st}' already COMPLETED in {rid}. Skipping.")
                continue

            watch: List[Path] = []
            if st == "script":
                watch = [paths["section_script"]]
            elif st == "voice":
                watch = [paths["audio_wav"]]
            elif st == "timing":
                watch = [paths["timing_dir"] / f"{sec_id}_timing_master.json", paths["timing_dir"] / f"{sec_id}_word_by_word.srt"]
            elif st == "extract":
                watch = [paths["assets_dir"] / "metadata.json", paths["assets_dir"] / "contact_sheet.png"]
            elif st == "semantic-map":
                watch = [proj["proj_dir"] / "director" / sec_id / "semantic_map.json"]
            elif st == "brief":
                watch = [proj["proj_dir"] / "director" / sec_id / "creative_brief.json"]
            elif st == "direct":
                watch = [proj["proj_dir"] / "director" / sec_id / "scene_graph.json"]
            elif st == "motion":
                watch = [rm.section_work_dir(rid, sec_id) / "motion_plan.json", rm.section_work_dir(rid, sec_id) / "derived_assets"]
            elif st == "sfx":
                watch = [rm.section_work_dir(rid, sec_id) / f"{sec_id}_aion_mix.wav"]
            elif st == "render":
                watch = [rm.section_out_dir(rid, sec_id) / f"{sec_id}_aion_editable.ecproj", rm.section_out_dir(rid, sec_id) / f"{sec_id}_aion_master.mp4"]
            elif st == "qa":
                watch = [rm.section_qa_dir(rid, sec_id)]

            try:
                with rm.stage_transaction(rid, sec_id, st, watch_paths=watch, rollback_on_fail=rollback_on_fail):
                    if st == "script":
                        ok = cmd_script(sec_num, project=clean_name, split=True)
                    elif st == "voice":
                        if paths["audio_wav"].is_file() and not force:
                            ok = True
                            print(f"⏩ [{sec_id}] Voice WAV already present -> {paths['audio_wav'].name}")
                        else:
                            ok = cmd_voice(sec_num, project=clean_name, force=force)
                    elif st == "timing":
                        tm = paths["timing_dir"] / f"{sec_id}_timing_master.json"
                        if tm.is_file() and not force:
                            ok = True
                            print(f"⏩ [{sec_id}] Timing already present -> {tm.name}")
                        else:
                            ok = cmd_timing(sec_num, project=clean_name, force=force)
                    elif st == "extract":
                        meta = paths["assets_dir"] / "metadata.json"
                        if meta.is_file() and not force:
                            ok = True
                            print(f"⏩ [{sec_id}] Extracted assets already present.")
                        else:
                            ok = cmd_extract(sec_num, project=clean_name, mode=mode)
                    elif st == "semantic-map":
                        ok = cmd_semantic_map(sec_num, project=clean_name, force=force)
                    elif st == "brief":
                        ok = cmd_brief(sec_num, project=clean_name, force=force)
                    elif st == "direct":
                        ok = cmd_direct(sec_num, project=clean_name, force=force)
                    elif st == "motion":
                        ok = cmd_motion(sec_num, project=clean_name, run_id=rid)
                    elif st == "sfx":
                        ok = cmd_sfx(sec_num, project=clean_name, run_id=rid)
                    elif st == "render":
                        ok = cmd_render(sec_num, project=clean_name, pipeline="aion", run_id=rid, use_gpu=use_gpu, rollback_on_fail=False, resolution=resolution)
                    elif st == "qa":
                        ok = cmd_qa(sec_num, project=clean_name, run_id=rid)
                    else:
                        ok = False

                    if not ok:
                        raise RuntimeError(f"Stage '{st}' returned False for {sec_id}")
                    rm.mark_stage(rid, sec_id, st, "COMPLETED", outputs=[str(p) for p in watch if p.exists()])
            except Exception as exc:
                print(f"❌ [{sec_id}] Stage '{st}' FAILED (rollback={rollback_on_fail}): {exc}")
                overall_ok = False
                break

    if overall_ok and not skip_merge and to_idx >= PIPELINE_STAGES.index("merge"):
        ok_m = cmd_merge(project=clean_name, run_id=rid, pipeline="aion")
        overall_ok = overall_ok and ok_m

    cmd_status(project=clean_name, detailed=True)
    return overall_ok


# ==============================================================================
# MAIN CLI ENTRYPOINT & SPEC BUILDER
# ==============================================================================

def _add_project_flag(subp: argparse.ArgumentParser) -> None:
    """Adds --project without clobbering a global --project passed before subcommand."""
    subp.add_argument("--project", default=argparse.SUPPRESS, help="Project name (overrides active project)")


def build_parser() -> argparse.ArgumentParser:
    from core.aion.contracts import PIPELINE_STAGES

    parser = argparse.ArgumentParser(
        prog="pipeline_cli.py",
        description="Unified Whiteboard Motion Graphics Multi-Project Pipeline (AION CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project", help="Specify project name (overrides active project)")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any stage fails or reports errors")
    subparsers = parser.add_subparsers(dest="command")

    # Project management subcommands
    init_p = subparsers.add_parser("init", aliases=["new"], help="Initialize a new isolated video project")
    init_p.add_argument("name", help="Project name (e.g. quantum_physics, alexander_the_great)")
    init_p.add_argument("--sections", type=int, default=10, help="Number of sections to scaffold (default: 10)")
    init_p.add_argument("--desc", default="", help="Short description of the video")
    init_p.add_argument("--lang", choices=["ar", "en"], default="ar", help="Project language (ar or en; default: ar)")
    init_p.add_argument("--dialect", default="", help="Accent/dialect tag (e.g. us_casual, saudi_white)")
    init_p.add_argument("--voice", default="", help="Override TTS voice name (e.g. Puck, Fenrir)")

    use_p = subparsers.add_parser("use", aliases=["switch"], help="Switch active working project")
    use_p.add_argument("name", help="Name of project to activate")

    subparsers.add_parser("projects", aliases=["list"], help="List all video projects")
    paths_p = subparsers.add_parser("paths", aliases=["info"], help="Show exact input/output paths for project")
    _add_project_flag(paths_p)

    # Stage 1: Script
    script_p = subparsers.add_parser("script", help="Split and validate section scripts from master_script")
    script_p.add_argument("--section", help="Section number (e.g. 01)")
    script_p.add_argument("--all", action="store_true", help="Process all sections")
    script_p.add_argument("--no-split", action="store_true", help="Validate without splitting master_script")
    _add_project_flag(script_p)

    # Stage 2: Voice
    voice_p = subparsers.add_parser("voice", help="Generate Voiceover")
    voice_p.add_argument("--section", help="Section number (e.g. 01, 02, 03)")
    voice_p.add_argument("--all", action="store_true", help="Generate all sections")
    voice_p.add_argument("--model", default=None, help="TTS model override (default: gemini-3.1-flash-tts-preview)")
    voice_p.add_argument("--dialect", default=None, help="Optional dialect override (e.g. saudi_white, egyptian, egyptian_female, us_casual)")
    voice_p.add_argument("--voice", default=None, help="Optional Gemini prebuilt voice override (e.g. Fenrir, Kore, Puck)")
    voice_p.add_argument("--force", action="store_true", help="Regenerate cached TTS chunks")
    voice_p.add_argument("--no-verify", action="store_true", help="Skip per-chunk Faster-Whisper QA verification")
    voice_p.add_argument("--pipeline", choices=["aion", "legacy"], default="aion", help="Voice backend (default: aion)")
    _add_project_flag(voice_p)

    # Stage 3: Timing
    timing_p = subparsers.add_parser("timing", help="Generate Timing & SRT")
    timing_p.add_argument("--section", help="Section number (e.g. 01, 02, 03)")
    timing_p.add_argument("--all", action="store_true", help="Align all sections and build timing index")
    timing_p.add_argument("--force", action="store_true", help="Force Whisper re-transcription")
    _add_project_flag(timing_p)

    # Stage 4: Extract Assets
    extract_p = subparsers.add_parser("extract", help="Topological Asset Extractor")
    extract_p.add_argument("--section", help="Section number (e.g. 01, 02, 03)")
    extract_p.add_argument("--all", action="store_true", help="Extract all sections")
    extract_p.add_argument("--mode", choices=["grid", "contour"], default="grid", help="Extraction mode (default: grid)")
    extract_p.add_argument("--rows", type=int, default=4, help="Grid rows for grid mode (default: 4)")
    extract_p.add_argument("--cols", type=int, default=5, help="Grid cols for grid mode (default: 5)")
    extract_p.add_argument("--from-zip", default=None, help="Import pre-extracted section assets & manifest.json from a ZIP archive")
    _add_project_flag(extract_p)

    # Stage 5: Semantic Mapping
    sem_p = subparsers.add_parser("semantic-map", aliases=["map"], help="Map storyboard assets to timing sentences")
    sem_p.add_argument("--section", help="Section number (e.g. 01)")
    sem_p.add_argument("--all", action="store_true", help="Map all sections")
    sem_p.add_argument("--force", action="store_true", help="Overwrite existing semantic_map.json")
    _add_project_flag(sem_p)

    # Stage 6: Creative Brief
    brief_p = subparsers.add_parser("brief", help="Generate/validate AION Creative Brief")
    brief_p.add_argument("--section", help="Section number (e.g. 01)")
    brief_p.add_argument("--all", action="store_true", help="Generate briefs for all sections")
    brief_p.add_argument("--force", action="store_true", help="Overwrite existing creative_brief.json")
    _add_project_flag(brief_p)

    # Stage 7: AI Director (Scene Graph)
    dir_p = subparsers.add_parser("direct", help="Generate or validate AION scene_graph.json")
    dir_p.add_argument("--section", help="Section number (e.g. 01)")
    dir_p.add_argument("--all", action="store_true", help="Direct all sections")
    dir_p.add_argument("--force", action="store_true", help="Regenerate existing scene_graph.json")
    _add_project_flag(dir_p)

    # Stage 8: Motion Graphics Derivatives
    mot_p = subparsers.add_parser("motion", help="Prepare exhibit cards / soft-bottom asset derivatives")
    mot_p.add_argument("--section", help="Section number (e.g. 01)")
    mot_p.add_argument("--all", action="store_true", help="Prepare all sections")
    mot_p.add_argument("--run-id", default=None, help="Isolated run ID")
    _add_project_flag(mot_p)

    # Stage 9: SFX & Ducking Audio Mix
    sfx_p = subparsers.add_parser("sfx", help="Mix narration WAV with RMS-ducked studio SFX")
    sfx_p.add_argument("--section", help="Section number (e.g. 01)")
    sfx_p.add_argument("--all", action="store_true", help="Mix all sections")
    sfx_p.add_argument("--run-id", default=None, help="Isolated run ID")
    _add_project_flag(sfx_p)

    # Stage 10-11: Render Master Video (720p default; --resolution 1080p for Full HD)
    render_p = subparsers.add_parser("render", help="Render Master Video (720p default, or --resolution 1080p)")
    render_p.add_argument("--section", help="Section number (e.g. 01, 02, 03)")
    render_p.add_argument("--all", action="store_true", help="Render all sections")
    render_p.add_argument("--engine", choices=["python", "effectcraft"], default="effectcraft", help="Render engine (default: effectcraft)")
    render_p.add_argument("--pipeline", choices=["auto", "aion", "legacy"], default="auto", help="Pipeline mode (default: auto)")
    render_p.add_argument("--resolution", choices=["720p", "1080p", "full", "half", "third", "quarter"], default="720p", help="Output resolution (default: 720p; pass 1080p or full for 1920x1080)")
    render_p.add_argument("--run-id", default=None, help="Isolated run ID (prevents overwriting previous runs)")
    render_p.add_argument("--no-gpu", action="store_true", help="Disable GPU rendering flag")
    render_p.add_argument("--no-rollback", action="store_true", help="Keep partial outputs on render failure")
    _add_project_flag(render_p)

    # Stage 12: QA
    qa_p = subparsers.add_parser("qa", help="Run PostRender QA + 10-frame Contact Sheet + Scene Graph Audit")
    qa_p.add_argument("--section", help="Section number (e.g. 01)")
    qa_p.add_argument("--all", action="store_true", help="QA all sections")
    qa_p.add_argument("--run-id", default=None, help="Isolated run ID to inspect")
    _add_project_flag(qa_p)

    # Utilities: Effects, Status, Merge, Enhance, Doctor, Spec
    effects_p = subparsers.add_parser("effects", help="EffectCraft Motion Effects Studio")
    effects_p.add_argument("--list", action="store_true", help="List all 15 available effects")
    effects_p.add_argument("--demo", help="Render specific effect demo")
    effects_p.add_argument("--all", action="store_true", help="Render all 15 effect demos")

    status_p = subparsers.add_parser("status", help="Show pipeline status matrix")
    status_p.add_argument("--detailed", action="store_true", help="Show isolated run & resume stage state")
    _add_project_flag(status_p)

    merge_p = subparsers.add_parser("merge", help="Merge rendered sections into master documentary")
    merge_p.add_argument("--run-id", default=None, help="Isolated run ID to merge")
    merge_p.add_argument("--pipeline", choices=["auto", "aion", "legacy"], default="auto", help="Merge mode (default: auto)")
    merge_p.add_argument("--out", default=None, help="Optional explicit output MP4 path")
    _add_project_flag(merge_p)

    enhance_p = subparsers.add_parser("enhance", help="Apply Micro-Retention GIF Overlays with Pure Voiceover (Zero-BGM Policy)")
    enhance_p.add_argument("--section", help="Section number (e.g. 01, 02)")
    enhance_p.add_argument("--all", action="store_true", help="Enhance all sections in project")
    _add_project_flag(enhance_p)

    doc_p = subparsers.add_parser("doctor", help="Check FFmpeg, CraftApp binaries, GPU, storage & Gemini keys")
    doc_p.add_argument("--json", action="store_true", help="Print JSON diagnostic output")

    keys_p = subparsers.add_parser("keys-check", help="Probe Gemini API key limits/quotas for TTS or Gemini models")
    keys_p.add_argument("--model", default="gemini-3.1-flash-tts-preview", help="Target Gemini model (default: gemini-3.1-flash-tts-preview)")
    keys_p.add_argument("--json", action="store_true", help="Print JSON key health report")

    spec_p = subparsers.add_parser("cli-spec", help="Print live CLI schema JSON and optionally generate CLI_REFERENCE.md")
    spec_p.add_argument("--write-docs", action="store_true", help="Regenerate root CLI_REFERENCE.md from live parser")

    # Creative Studio V5 (`studio <subcommand>`)
    studio_p = subparsers.add_parser("studio", help="AION Creative Studio V5 (ECGC compiler, capabilities & visual QA)")
    studio_sub = studio_p.add_subparsers(dest="studio_command")

    st_doc = studio_sub.add_parser("doctor", help="Check Studio V5 readiness, capabilities registry & golden integrity (read-only)")
    st_doc.add_argument("--json", action="store_true", help="Print JSON diagnostic payload")

    st_cap = studio_sub.add_parser("capabilities", help="Inspect or empirically probe EffectCraft capabilities")
    st_cap.add_argument("--probe", action="store_true", help="Run live EffectCraft probes & refresh config/effectcraft_capabilities.json")
    st_cap.add_argument("--only", default=None, help="Comma-separated subset of capability IDs to probe")
    st_cap.add_argument("--gpu", action="store_true", help="Request GPU backend during live probe")
    st_cap.add_argument("--json", action="store_true", help="Output capabilities JSON")

    st_fnt = studio_sub.add_parser("fonts", help="Inspect/verify licensed studio fonts, SHA-256 & EffectCraft render status")
    st_fnt.add_argument("--probe", action="store_true", help="Run live EffectCraft RTL/Tashkeel/mobile font & kinetic render probe")
    st_fnt.add_argument("--verify-sha", action="store_true", help="Verify downloaded font & license SHA-256 checksums on disk")
    st_fnt.add_argument("--json", action="store_true", help="Output font registry JSON")

    st_gt = studio_sub.add_parser("graphics-test", help="Verify Motion Grammar, Procedural Vectors & Scene Graph V2")
    st_gt.add_argument("--mode", choices=["all", "scientific_explanation", "cinematic_2_5d", "editorial_motion_graphics"], default="all", help="Graphic test blueprint mode")
    st_gt.add_argument("--out-dir", default=None, help="Optional scratch directory for test specs & previews")
    st_gt.add_argument("--render-preview", action="store_true", help="Render live EffectCraft preview PNGs during test")

    st_cmp = studio_sub.add_parser("compile", help="Direct Scene Graph V2 + ECGC compile + MP4 render inside isolated run dir")
    _add_project_flag(st_cmp)
    st_cmp.add_argument("--section", default=None, help="Section number or ID (e.g. 01 or section_01)")
    st_cmp.add_argument("--all", action="store_true", help="Compile all sections sequentially inside shared isolated run")
    st_cmp.add_argument("--style-mode", choices=["auto", "scientific_explanation", "cinematic_2_5d", "editorial_motion_graphics"], default="auto", help="Visual treatment style mode")
    st_cmp.add_argument("--format", dest="video_format", choices=["educational", "narrative", "workflow_montage", "auto", "legacy"], default="educational", help="Video montage format (default: educational / Mehmed V8 Master Edu; also narrative, workflow_montage for ANKARA_PRODUCTION staged scenes, auto, or legacy)")
    st_cmp.add_argument("--aspect", choices=["16:9", "9:16"], default="16:9", help="Composition aspect ratio (default: 16:9)")
    st_cmp.add_argument("--story-genre", choices=["auto", "psychological_cinematic", "historical_documentary", "shorts_viral_9x16", "scientific_explanation", "english_editorial"], default="auto", help="Typography & kinetic pacing story genre")
    st_cmp.add_argument("--run-id", default=None, help="Isolated run ID under exports/runs/")
    st_cmp.add_argument("--duration", type=float, default=None, help="Optional duration override in seconds")
    st_cmp.add_argument("--resolution", choices=["720p", "1080p", "full", "half", "third", "quarter"], default="720p", help="Output resolution (default: 720p -> 1280x720 / 720x1280; pass 1080p or full for Full HD)")
    st_cmp.add_argument("--no-gpu", action="store_true", help="Disable GPU rendering flag")
    st_cmp.add_argument("--director-v4", dest="director_v4", action="store_true", default=True, help="Enable AION v2+v3+v4 Adaptive Director, Motion Plan V3 & FTS5 Resource Registry (DEFAULT: ON)")
    st_cmp.add_argument("--no-director-v4", dest="director_v4", action="store_false", help="Disable AION Director v4 layer (revert to raw V7 scene graph)")
    st_cmp.add_argument("--force", action="store_true", help="Overwrite explicit --run-id if already populated")

    st_prv = studio_sub.add_parser("preview", help="Fast multi-frame ECGC preview & QA check inside isolated run dir")
    _add_project_flag(st_prv)
    st_prv.add_argument("--section", default=None, help="Section number or ID")
    st_prv.add_argument("--all", action="store_true", help="Preview all sections")
    st_prv.add_argument("--style-mode", choices=["auto", "scientific_explanation", "cinematic_2_5d", "editorial_motion_graphics"], default="auto", help="Visual treatment style mode")
    st_prv.add_argument("--format", dest="video_format", choices=["educational", "narrative", "workflow_montage", "auto", "legacy"], default="educational", help="Video montage format (default: educational / Mehmed V8 Master Edu; also narrative, workflow_montage for ANKARA_PRODUCTION staged scenes, auto, or legacy)")
    st_prv.add_argument("--aspect", choices=["16:9", "9:16"], default="16:9", help="Composition aspect ratio (default: 16:9)")
    st_prv.add_argument("--story-genre", choices=["auto", "psychological_cinematic", "historical_documentary", "shorts_viral_9x16", "scientific_explanation", "english_editorial"], default="auto", help="Typography & kinetic pacing story genre")
    st_prv.add_argument("--run-id", default=None, help="Isolated run ID")
    st_prv.add_argument("--duration", type=float, default=None, help="Optional duration override in seconds")
    st_prv.add_argument("--director-v4", dest="director_v4", action="store_true", default=True, help="Enable AION v2+v3+v4 Adaptive Director & Motion Plan V3 (DEFAULT: ON)")
    st_prv.add_argument("--no-director-v4", dest="director_v4", action="store_false", help="Disable AION Director v4 layer")
    st_prv.add_argument("--force", action="store_true", help="Overwrite explicit --run-id")

    st_res = studio_sub.add_parser("resources", help="Search & inspect real AION v4 Resource Registry (SQLite FTS5)")
    _add_project_flag(st_res)
    st_res.add_argument("--query", default="", help="Arabic/English semantic query (e.g. 'سفينة', 'glow', 'قفل')")
    st_res.add_argument("--kind", choices=["icon", "background", "sfx", "effect", "font", "asset"], default=None, help="Filter by resource kind")
    st_res.add_argument("--section", default=None, help="Optional section ID to include project assets")
    st_res.add_argument("--rebuild", action="store_true", help="Rebuild FTS5 index from scratch")
    st_res.add_argument("--limit", type=int, default=12, help="Max top-k candidates (default: 12)")
    st_res.add_argument("--json", action="store_true", help="Output JSON")

    st_qa = studio_sub.add_parser("qa", help="Run Visual Intelligence QA & build creative_contact_sheet.png")
    _add_project_flag(st_qa)
    st_qa.add_argument("--section", required=True, help="Section number or ID")
    st_qa.add_argument("--run-id", default=None, help="Specific run ID to inspect")
    st_qa.add_argument("--out-dir", default=None, help="Optional QA output directory")

    st_mrg = studio_sub.add_parser("merge", help="Merge rendered Studio V5 section MP4s inside isolated run into final master")
    _add_project_flag(st_mrg)
    st_mrg.add_argument("--run-id", default=None, help="Run ID to merge (defaults to latest run)")
    st_mrg.add_argument("--out", default=None, help="Optional output master MP4 path")

    st_sh = studio_sub.add_parser("shorts", help="Autonomous 9:16 Shorts Director (inspect, plan, compile, package)")
    _add_project_flag(st_sh)
    st_sh.add_argument("--action", choices=["inspect", "plan", "compile", "package"], default="plan", help="Shorts Director workflow action")
    st_sh.add_argument("--short", default=None, help="Target Short ID (e.g. short_01)")
    st_sh.add_argument("--all", action="store_true", help="Compile all planned Shorts cleanly into isolated run")
    st_sh.add_argument("--run-id", default="shorts_v6", help="Isolated run ID under exports/runs/")
    st_sh.add_argument("--preview-only", action="store_true", help="Render half-res preview.mp4 + QA only without final.mp4")
    st_sh.add_argument("--resolution", choices=["720p", "1080p", "full", "half", "third", "quarter"], default="720p", help="Final render resolution (default: 720p -> 720x1280; pass 1080p or full for 1080x1920)")
    st_sh.add_argument("--no-gpu", action="store_true", help="Disable GPU acceleration flag")
    st_sh.add_argument("--force", action="store_true", help="Overwrite explicit --run-id if already populated")

    st_720 = studio_sub.add_parser("export-720p", help="Downscale rendered 1080p landscape/portrait MP4s cleanly to 720p")
    st_720.add_argument("--input", nargs="+", required=True, help="One or more MP4 files, globs, or folders")
    st_720.add_argument("--out-dir", default=None, help="Output folder (default: <input_parent>/720p/)")
    st_720.add_argument("--crf", type=int, default=18, help="x264 visual quality CRF (default: 18)")
    st_720.add_argument("--force", action="store_true", help="Overwrite existing 720p output files")

    # Unified Autonomous Production Loop (`auto` + `run`)
    auto_p = subparsers.add_parser("auto", aliases=["loop", "run-all", "run"], help="Autonomous production loop across stages 1..12")
    _add_project_flag(auto_p)
    auto_p.add_argument("--start", type=int, default=1, help="Starting section number (default: 1)")
    auto_p.add_argument("--end", type=int, default=None, help="Ending section number (default: auto-detect)")
    auto_p.add_argument("--engine", choices=["python", "effectcraft"], default="effectcraft", help="Render engine (default: effectcraft)")
    auto_p.add_argument("--pipeline", choices=["auto", "aion", "legacy"], default="auto", help="Pipeline architecture (default: auto)")
    auto_p.add_argument("--from-stage", choices=PIPELINE_STAGES, default=None, help="Start execution at this stage")
    auto_p.add_argument("--to-stage", choices=PIPELINE_STAGES, default=None, help="Stop execution after this stage")
    auto_p.add_argument("--resume", action="store_true", help="Resume isolated run from last successful stage")
    auto_p.add_argument("--run-id", default=None, help="Explicit isolated run ID")
    auto_p.add_argument("--mode", choices=["grid", "contour"], default="grid", help="Extraction mode (default: grid)")
    auto_p.add_argument("--resolution", choices=["720p", "1080p", "full", "half", "third", "quarter"], default="720p", help="Output resolution (default: 720p -> 1280x720; pass 1080p or full for 1920x1080)")
    auto_p.add_argument("--no-gpu", action="store_true", help="Disable GPU rendering flag")
    auto_p.add_argument("--no-rollback", action="store_true", help="Disable rollback on failure")
    auto_p.add_argument("--skip-voice", action="store_true", help="Skip voice generation")
    auto_p.add_argument("--skip-timing", action="store_true", help="Skip timing alignment")
    auto_p.add_argument("--skip-extract", action="store_true", help="Skip extraction")
    auto_p.add_argument("--skip-render", action="store_true", help="Skip rendering")
    auto_p.add_argument("--skip-merge", action="store_true", help="Skip final merge")
    auto_p.add_argument("--force", action="store_true", help="Force regeneration of all stages")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    proj_override = getattr(args, "project", None)
    ok = True

    if args.command in ["init", "new"]:
        cmd_init(
            args.name,
            num_sections=args.sections,
            description=args.desc,
            lang=args.lang,
            dialect=args.dialect,
            voice=args.voice,
        )
    elif args.command in ["use", "switch"]:
        ok = cmd_use(args.name)
    elif args.command in ["projects", "list"]:
        cmd_list_projects()
    elif args.command in ["paths", "info"]:
        cmd_paths(project=proj_override)
    elif args.command == "script":
        ok = cmd_script(sec_num=args.section, project=proj_override, all_sections=args.all, split=not args.no_split)
    elif args.command == "voice":
        if not args.section and not args.all:
            parser.error("voice requires --section or --all")
        ok = cmd_voice(
            sec_num=args.section,
            project=proj_override,
            all_sections=args.all,
            model_name=args.model,
            force=args.force,
            verify=not args.no_verify,
            pipeline=args.pipeline,
            dialect=args.dialect,
            voice_name=args.voice,
        )
    elif args.command == "timing":
        if not args.section and not args.all:
            parser.error("timing requires --section or --all")
        ok = cmd_timing(sec_num=args.section, project=proj_override, all_sections=args.all, force=args.force)
    elif args.command == "extract":
        if not args.section and not args.all and not args.from_zip:
            parser.error("extract requires --section, --all, or --from-zip")
        ok = cmd_extract(
            sec_num=args.section,
            project=proj_override,
            all_sections=args.all,
            mode=args.mode,
            rows=args.rows,
            cols=args.cols,
            from_zip=args.from_zip,
        )
    elif args.command in ["semantic-map", "map"]:
        ok = cmd_semantic_map(sec_num=args.section, project=proj_override, all_sections=args.all or not args.section, force=args.force)
    elif args.command == "brief":
        ok = cmd_brief(sec_num=args.section, project=proj_override, all_sections=args.all or not args.section, force=args.force)
    elif args.command == "direct":
        ok = cmd_direct(sec_num=args.section, project=proj_override, all_sections=args.all or not args.section, force=args.force)
    elif args.command == "motion":
        ok = cmd_motion(sec_num=args.section, project=proj_override, all_sections=args.all or not args.section, run_id=args.run_id)
    elif args.command == "sfx":
        ok = cmd_sfx(sec_num=args.section, project=proj_override, all_sections=args.all or not args.section, run_id=args.run_id)
    elif args.command == "render":
        if not args.section and not args.all:
            parser.error("render requires --section or --all")
        ok = cmd_render(
            sec_num=args.section,
            engine=args.engine,
            project=proj_override,
            all_sections=args.all,
            pipeline=args.pipeline,
            run_id=args.run_id,
            use_gpu=not args.no_gpu,
            rollback_on_fail=not args.no_rollback,
            resolution=args.resolution,
        )
    elif args.command == "qa":
        ok = cmd_qa(sec_num=args.section, project=proj_override, all_sections=args.all or not args.section, run_id=args.run_id)
    elif args.command in ["auto", "loop", "run-all", "run"]:
        ok = cmd_auto(
            project=proj_override,
            start_sec=args.start,
            end_sec=args.end,
            engine=args.engine,
            skip_voice=args.skip_voice,
            skip_timing=args.skip_timing,
            skip_extract=args.skip_extract,
            skip_render=args.skip_render,
            skip_merge=args.skip_merge,
            force=args.force,
            from_stage=args.from_stage,
            to_stage=args.to_stage,
            resume=args.resume,
            run_id=args.run_id,
            pipeline=args.pipeline,
            mode=args.mode,
            use_gpu=not args.no_gpu,
            rollback_on_fail=not args.no_rollback,
            resolution=args.resolution,
        )
    elif args.command == "effects":
        from core_engine.effectcraft_motion_studio import EffectCraftMotionStudio, EFFECTS_CATALOG
        studio = EffectCraftMotionStudio()
        if args.all:
            studio.render_all_demos()
        elif args.demo:
            studio.create_demo(effect_name=args.demo)
        else:
            print("\n=== EFFECTCRAFT MOTION EFFECTS CATALOG ===")
            for k, v in EFFECTS_CATALOG.items():
                print(f"• {k:<20} | {v['name_ar']} ({v['category']})")
    elif args.command == "status":
        cmd_status(project=proj_override, detailed=args.detailed)
    elif args.command == "merge":
        ok = cmd_merge(project=proj_override, run_id=args.run_id, pipeline=args.pipeline, out_file=args.out)
    elif args.command == "enhance":
        ok = cmd_enhance(sec_num=args.section, all_sections=args.all, project=proj_override)
    elif args.command == "doctor":
        ok = cmd_doctor(as_json=args.json)
    elif args.command == "keys-check":
        from core.api.key_pool import get_key_pool
        rep = get_key_pool(force_reload=True).probe_keys(model=args.model)
        if args.json:
            print(json.dumps(rep, indent=2, ensure_ascii=False))
        else:
            print(f"=== GEMINI KEY LIMIT CHECK ({rep['model']}) ===")
            for k in rep["keys"]:
                print(f"  Key #{k['index']:02d} ({k['masked_key']}): {k['status']} [{k['latency_sec']}s] {k['detail']}")
            print(f"Summary: {rep['active_keys']}/{rep['total_keys']} active keys")
        ok = rep["active_keys"] > 0
    elif args.command == "cli-spec":
        ok = cmd_cli_spec(as_json=not args.write_docs, write_docs=args.write_docs)
    elif args.command == "studio":
        from core.aion import studio_cli

        sc = getattr(args, "studio_command", None)
        if sc == "doctor":
            ok = studio_cli.cmd_studio_doctor(as_json=args.json)
        elif sc == "capabilities":
            ok = studio_cli.cmd_studio_capabilities(probe=args.probe, only=args.only, as_json=args.json, use_gpu=args.gpu)
        elif sc == "fonts":
            ok = studio_cli.cmd_studio_fonts(probe=args.probe, verify_sha=args.verify_sha, as_json=args.json)
        elif sc == "graphics-test":
            ok = studio_cli.cmd_studio_graphics_test(mode=args.mode, out_dir=args.out_dir, render_preview=args.render_preview)
        elif sc == "compile":
            ok = studio_cli.cmd_studio_compile(
                project=proj_override,
                section=args.section,
                all_sections=args.all,
                style_mode=args.style_mode,
                video_format=args.video_format,
                aspect=args.aspect,
                story_genre=args.story_genre,
                run_id=args.run_id,
                preview_only=False,
                use_gpu=(not args.no_gpu),
                resolution=args.resolution,
                force=args.force,
                duration_override=args.duration,
                director_v4=args.director_v4,
            )
        elif sc == "preview":
            ok = studio_cli.cmd_studio_compile(
                project=proj_override,
                section=args.section,
                all_sections=args.all,
                style_mode=args.style_mode,
                video_format=args.video_format,
                aspect=args.aspect,
                story_genre=args.story_genre,
                run_id=args.run_id,
                preview_only=True,
                use_gpu=False,
                force=args.force,
                duration_override=args.duration,
                director_v4=args.director_v4,
            )
        elif sc == "resources":
            ok = studio_cli.cmd_studio_resources(
                query=args.query,
                kind=args.kind,
                project=proj_override,
                section=args.section,
                rebuild=args.rebuild,
                limit=args.limit,
                as_json=args.json,
            )
        elif sc == "qa":
            ok = studio_cli.cmd_studio_qa(
                project=proj_override,
                section=args.section,
                run_id=args.run_id,
                out_dir=args.out_dir,
            )
        elif sc == "merge":
            ok = studio_cli.cmd_studio_merge(
                project=proj_override,
                run_id=args.run_id,
                out_file=args.out,
            )
        elif sc == "shorts":
            ok = studio_cli.cmd_studio_shorts(
                action=args.action,
                project=proj_override,
                short_id=args.short,
                all_shorts=args.all,
                run_id=args.run_id,
                preview_only=args.preview_only,
                use_gpu=(not args.no_gpu),
                resolution=args.resolution,
                force=args.force,
            )
        elif sc == "export-720p":
            ok = studio_cli.cmd_studio_export_720p(
                inputs=args.input,
                out_dir=args.out_dir,
                crf=args.crf,
                force=args.force,
            )
        else:
            ok = studio_cli.cmd_studio_doctor(as_json=False)
    else:
        parser.print_help()

    if args.strict and ok is False:
        sys.exit(1)


if __name__ == "__main__":
    main()
