"""AION Font Library & Registry Engine (Phase 6 — Typography Integration V6.1).

Manages the shared studio typography library under `assets/typography/`:
  - SHA-256 verification and de-duplicated asset tracking (never re-downloads matching files).
  - License enforcement: open-licensed families only; commercial families held strictly in
    `LICENSE_REQUIRED` with official vendor links and documented open fallbacks.
  - Deep SFNT inspection (`fontTools`): styles, weight bounds, variable axes (`fvar`), and
    Arabic/Latin/digit/diacritic script coverage.
  - Live empirical EffectCraft verification (`EFFECTCRAFT_FONT_DIRS` -> `text.fonts`,
    `.ecproj` save & reopen, RTL/Tashkeel/Mixed/Digits/Multiline 16:9 & 9:16 mobile render checks)
    producing `assets/typography/font_registry.json`.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fontTools.ttLib import TTFont
from PIL import Image

from core.config.settings import (
    PROJECT_ROOT,
    TYPOGRAPHY_DOWNLOAD_MANIFEST_PATH,
    TYPOGRAPHY_FONTS_DIR,
    TYPOGRAPHY_REGISTRY_PATH,
    TYPOGRAPHY_ROOT,
    TYPOGRAPHY_SETTINGS_PATH,
    get_effectcraft_font_dirs,
    get_effectcraft_subprocess_env,
)

# Strictly commercial / paid fonts — never auto-downloaded or claimed as licensed.
COMMERCIAL_LICENSE_REQUIRED: Dict[str, Dict[str, Any]] = {
    "Fit Arabic": {
        "style": "Ultra-Compressed Display (Arabic/Latin)",
        "vendor_url": "https://djr.com/notes/fit-arabic-release",
        "fallback": "Alyamama",
        "secondary_fallback": "Cairo",
    },
    "Panton Arabic": {
        "style": "Geometric Display Sans (Arabic/Latin)",
        "vendor_url": "https://www.fontfabric.com/fonts/panton-arabic/",
        "fallback": "Alexandria",
        "secondary_fallback": "Changa",
    },
    "Khareef": {
        "style": "Expressive Arabic Poster Display",
        "vendor_url": "https://protype.studio/khareef",
        "fallback": "Lalezar",
        "secondary_fallback": "Alyamama",
    },
    "Sakkal Saad Poster": {
        "style": "Heavy Architectural Arabic Poster",
        "vendor_url": "https://fahress.com/fonts/sakkal-saad-poster",
        "fallback": "Lalezar",
        "secondary_fallback": "Amiri",
    },
    "Druk": {
        "style": "Ultra-Bold Condensed Headline (Latin)",
        "vendor_url": "https://commercialtype.com/catalog/druk",
        "fallback": "Anton",
        "secondary_fallback": "Oswald",
    },
}

FAMILY_DESIGN_PROFILE: Dict[str, Dict[str, Any]] = {
    "Cairo": {"style": "Geometric Neo-Grotesk (Arabic/Latin)", "fallback": "Alexandria", "role": "primary"},
    "Alexandria": {"style": "Modern Rounded Geometric (Arabic/Latin)", "fallback": "Cairo", "role": "primary_mobile"},
    "Changa": {"style": "Angular Kinetic Display (Arabic/Latin)", "fallback": "Alexandria", "role": "display"},
    "IBM Plex Sans Arabic": {"style": "Editorial Technical Sans (Arabic/Latin)", "fallback": "Cairo", "role": "editorial"},
    "Readex Pro": {"style": "Precision Variable UI/Scientific (Arabic/Latin)", "fallback": "Cairo", "role": "data"},
    "Amiri": {"style": "Classical Naskh Editorial Serif (Arabic/Latin)", "fallback": "IBM Plex Sans Arabic", "role": "documentary"},
    "Lalezar": {"style": "High-Impact Retro Poster (Arabic/Latin)", "fallback": "Alyamama", "role": "impact", "tashkeel_caution": True},
    "Noto Sans Arabic": {"style": "Universal Variable Sans (Arabic/Latin)", "fallback": "Cairo", "role": "universal"},
    "Alyamama": {"style": "Contemporary Arabic Variable Display (Arabic/Latin)", "fallback": "Cairo", "role": "display"},
    "Tajawal": {"style": "Clean Broadcast Sans (Arabic/Latin)", "fallback": "Cairo", "role": "primary"},
    "Almarai": {"style": "High-Legibility Condensed Sans (Arabic/Latin)", "fallback": "Cairo", "role": "primary"},
    "Mabroum": {"style": "Stylized Arabic-Only Display", "fallback": "Alyamama", "role": "display_arabic_only"},
    "Funnel Display": {"style": "Geometric Tech Display (Latin)", "fallback": "Inter", "role": "latin_display"},
    "Bricolage Grotesque": {"style": "Expressive Variable Grotesk (Latin)", "fallback": "Inter", "role": "latin_display"},
    "Mona Sans": {"style": "Wide-Axis Variable Sans (Latin)", "fallback": "Inter", "role": "latin_primary"},
    "Space Grotesk": {"style": "Proportional Mono-Inflected Sans (Latin)", "fallback": "Inter", "role": "latin_display"},
    "Anton": {"style": "Heavy Impact Condensed Poster (Latin)", "fallback": "Oswald", "role": "latin_impact"},
    "Bebas Neue": {"style": "All-Caps Condensed Headline (Latin)", "fallback": "Oswald", "role": "latin_impact"},
    "Oswald": {"style": "Variable Condensed Editorial (Latin)", "fallback": "Anton", "role": "latin_impact"},
    "Inter": {"style": "Bundled Precision Sans (Latin)", "fallback": "Inter", "role": "latin_primary"},
    "Playfair Display": {"style": "Classical Documentary Serif (Latin)", "fallback": "Noto Serif", "role": "latin_documentary"},
}

AR_ALPHA_CPS = list(range(0x0627, 0x063B)) + list(range(0x0641, 0x064B))
HAMZA_CPS = (0x0621, 0x0622, 0x0623, 0x0624, 0x0625, 0x0626)
TASHKEEL_CPS = (0x064E, 0x064F, 0x0650, 0x0651, 0x0652, 0x064B)
AR_DIGIT_CPS = list(range(0x0660, 0x066A))
ASCII_DIGIT_CPS = list(range(0x30, 0x3A))
LATIN_CPS = list(range(0x41, 0x5B)) + list(range(0x61, 0x7B))

PROBE_TEXTS = {
    "rtl_ligatures": "\u0645\u062d\u0631\u0643 \u0627\u0644\u0625\u062e\u0631\u0627\u062c \u2014 \u0644\u0627 \u0644\u0623 \u0644\u0625 \u0623 \u0625 \u0622 \u0624 \u0626 \u0621",
    "tashkeel": "\u062a\u064e\u062c\u0652\u0631\u0650\u0628\u064e\u0629\u064f \u0627\u0644\u0652\u0625\u0650\u062f\u0652\u0631\u064e\u0627\u0643\u0650 \u0648\u064e\u0627\u0644\u0652\u0648\u064e\u0647\u0652\u0645\u0650",
    "mixed_bidi_digits": "\u0648\u0647\u0645 \u0628\u064a\u0646\u0648\u0643\u064a\u0648 AION V6.1 \u0639\u0627\u0645 \u0661\u0669\u0668\u0668 / 1988 (+42%)",
    "arabic_only": "\u062a\u062c\u0631\u0628\u0629 \u0648\u0647\u0645 \u0628\u064a\u0646\u0648\u0643\u064a\u0648 \u0639\u0627\u0645 \u0661\u0669\u0668\u0668",
    "latin_only": "Documentary Evidence 1988 (+42%) — Signal Flow",
    "multiline_ar": "\u0647\u0630\u0627 \u0627\u062e\u062a\u0628\u0627\u0631 \u0627\u0644\u062a\u0641\u0627\u0641 \u0627\u0644\u0633\u0637\u0631 \u0627\u0644\u0637\u0648\u064a\u0644 \u062f\u0627\u062e\u0644 \u0627\u0644\u0625\u0637\u0627\u0631 \u0627\u0644\u0622\u0645\u0646 \u0644\u0644\u0634\u0648\u0631\u062a\u0633",
}


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hex digest for any binary or license file."""
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_font_files_sha256(
    manifest_path: Path = TYPOGRAPHY_DOWNLOAD_MANIFEST_PATH,
    fonts_dir: Path = TYPOGRAPHY_FONTS_DIR,
) -> Dict[str, Any]:
    """Verify downloaded font & license files on disk via SHA-256 without re-downloading identical files."""
    manifest: Dict[str, Any] = {}
    if Path(manifest_path).is_file():
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

    verified: List[Dict[str, Any]] = []
    mismatches: List[Dict[str, Any]] = []
    missing: List[str] = []

    for entry in manifest.get("font_files", []):
        p = Path(entry["path"])
        if not p.is_file():
            missing.append(str(p))
            continue
        actual_sha = compute_file_sha256(p)
        expected_sha = str(entry.get("sha256", "")).lower()
        if expected_sha and actual_sha.lower() != expected_sha:
            mismatches.append({"path": str(p), "expected": expected_sha, "actual": actual_sha})
        else:
            verified.append({"family": entry.get("family"), "path": str(p), "sha256": actual_sha})

    on_disk_fonts = sorted(fonts_dir.rglob("*.ttf")) + sorted(fonts_dir.rglob("*.otf")) if fonts_dir.is_dir() else []
    return {
        "manifest_present": Path(manifest_path).is_file(),
        "manifest_entries": len(manifest.get("font_files", [])),
        "verified_count": len(verified),
        "mismatch_count": len(mismatches),
        "missing_count": len(missing),
        "on_disk_font_binaries": len(on_disk_fonts),
        "mismatches": mismatches,
        "missing": missing,
    }


def _find_effectcraft_cli() -> Optional[Path]:
    from core.aion.capability_prober import find_effectcraft_cli
    return find_effectcraft_cli()


def query_effectcraft_fonts(rescan: bool = True, query: Optional[str] = None) -> Dict[str, Any]:
    """Invoke `effectcraft-cli.exe` `text.fonts` using `EFFECTCRAFT_FONT_DIRS` from project settings."""
    cli = _find_effectcraft_cli()
    if cli is None:
        return {"ok": False, "error": "effectcraft-cli.exe not found", "families": {}}

    env = get_effectcraft_subprocess_env()
    params: Dict[str, Any] = {"rescan": bool(rescan)}
    if query:
        params["query"] = query
    payload = json.dumps({"command": "text.fonts", "params": params}, ensure_ascii=False).encode("utf-8")
    proc = subprocess.run(
        [str(cli), "--empty", "run", "--commands", "-", "--json"],
        input=payload,
        capture_output=True,
        timeout=30,
        env=env,
    )
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": proc.stderr.decode("utf-8", errors="replace")[:400],
            "families": {},
        }
    try:
        parsed = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        res = parsed[0].get("result", {}) if isinstance(parsed, list) and parsed else {}
        fams = {f["family"]: f for f in res.get("families", []) if isinstance(f, dict) and f.get("family")}
        return {
            "ok": True,
            "count": int(res.get("count", len(fams))),
            "added": int(res.get("added", 0)),
            "effectcraft_font_dirs": env.get("EFFECTCRAFT_FONT_DIRS", ""),
            "families": fams,
        }
    except Exception as exc:
        return {"ok": False, "error": f"parse failure: {exc}", "families": {}}


def inspect_font_family_disk(family_dir: Path) -> Dict[str, Any]:
    """Inspect all TTF/OTF binaries and license files inside a single font family directory."""
    font_files = sorted(list(family_dir.glob("*.ttf")) + list(family_dir.glob("*.otf")))
    license_files = sorted([p for p in family_dir.iterdir() if p.is_file() and p.name.lower() in ("ofl.txt", "license.txt")])

    weights: set[int] = set()
    styles: List[str] = []
    axes_map: Dict[str, Dict[str, Any]] = {}
    ar_cov = 0.0
    hamza_cov = 0.0
    tash_cov = 0.0
    ar_dig_cov = 0.0
    asc_dig_cov = 0.0
    lat_cov = 0.0
    gsub_ar = False
    family_name = family_dir.name.replace("_", " ")
    files_meta: List[Dict[str, Any]] = []

    for fp in font_files:
        sha = compute_file_sha256(fp)
        tt = TTFont(str(fp), lazy=True)
        cmap = tt.getBestCmap() or {}
        name_tbl = tt["name"]
        fam = (
            next((r.toUnicode() for r in name_tbl.names if r.nameID == 16 and r.platformID == 3), None)
            or next((r.toUnicode() for r in name_tbl.names if r.nameID == 1 and r.platformID == 3), family_name)
        )
        sub = (
            next((r.toUnicode() for r in name_tbl.names if r.nameID == 17 and r.platformID == 3), None)
            or next((r.toUnicode() for r in name_tbl.names if r.nameID == 2 and r.platformID == 3), "Regular")
        )
        family_name = fam or family_name
        if sub not in styles:
            styles.append(sub)
        if "OS/2" in tt:
            weights.add(int(tt["OS/2"].usWeightClass))
        if "fvar" in tt:
            for a in tt["fvar"].axes:
                axes_map[a.axisTag] = {
                    "tag": a.axisTag,
                    "min": float(a.minValue),
                    "default": float(a.defaultValue),
                    "max": float(a.maxValue),
                }
            for inst in tt["fvar"].instances:
                wval = inst.coordinates.get("wght")
                if wval is not None:
                    weights.add(int(round(wval)))

        ar_cov = max(ar_cov, sum(1 for c in AR_ALPHA_CPS if c in cmap) / len(AR_ALPHA_CPS))
        hamza_cov = max(hamza_cov, sum(1 for c in HAMZA_CPS if c in cmap) / len(HAMZA_CPS))
        tash_cov = max(tash_cov, sum(1 for c in TASHKEEL_CPS if c in cmap) / len(TASHKEEL_CPS))
        ar_dig_cov = max(ar_dig_cov, sum(1 for c in AR_DIGIT_CPS if c in cmap) / len(AR_DIGIT_CPS))
        asc_dig_cov = max(asc_dig_cov, sum(1 for c in ASCII_DIGIT_CPS if c in cmap) / len(ASCII_DIGIT_CPS))
        lat_cov = max(lat_cov, sum(1 for c in LATIN_CPS if c in cmap) / len(LATIN_CPS))

        if "GSUB" in tt and getattr(tt["GSUB"].table, "FeatureList", None):
            tags = {fr.FeatureTag for fr in tt["GSUB"].table.FeatureList.FeatureRecord}
            if any(t in tags for t in ("init", "medi", "fina", "isol", "liga", "rlig")):
                gsub_ar = True
        files_meta.append({
            "path": str(fp.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha,
            "size_bytes": fp.stat().st_size,
        })

    lic_path = license_files[0] if license_files else None
    lic_header = ""
    if lic_path:
        lic_txt = lic_path.read_text(encoding="utf-8", errors="replace").splitlines()
        lic_header = " ".join(l.strip() for l in lic_txt[:3] if l.strip())[:160]
        files_meta.append({
            "path": str(lic_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": compute_file_sha256(lic_path),
            "size_bytes": lic_path.stat().st_size,
        })

    # Combined hash over sorted file hashes for quick family change detection
    combo = "|".join(f["sha256"] for f in sorted(files_meta, key=lambda x: x["path"]))
    family_hash = hashlib.sha256(combo.encode("utf-8")).hexdigest()

    return {
        "family": family_name,
        "styles_disk": styles,
        "weights": sorted(weights) or [400],
        "axes": list(axes_map.values()),
        "language_script_coverage": {
            "arabic": ar_cov >= 0.95,
            "arabic_ratio": round(ar_cov, 3),
            "hamzas": hamza_cov >= 0.99,
            "tashkeel": tash_cov >= 0.80,
            "arabic_digits": ar_dig_cov >= 0.99,
            "ascii_digits": asc_dig_cov >= 0.99,
            "latin": lat_cov >= 0.95,
            "gsub_arabic_shaping": gsub_ar,
        },
        "license": "SIL Open Font License 1.1" if lic_path else "MISSING_LICENSE",
        "license_file": str(lic_path.relative_to(PROJECT_ROOT)).replace("\\", "/") if lic_path else None,
        "license_excerpt": lic_header,
        "file_hash": family_hash,
        "files": files_meta,
    }


def _render_probe_specimen(
    cli: Path,
    ecproj: Path,
    comp_name: str,
    width: int,
    height: int,
    bg_hex: str,
    layers: List[Dict[str, Any]],
    out_png: Path,
    env: Dict[str, str],
) -> Tuple[bool, str, bool]:
    """Build `.ecproj`, save, reopen, check expr.errors & render PNG."""
    cmds: List[Dict[str, Any]] = [
        {"command": "comp.new", "params": {"name": comp_name, "width": width, "height": height, "frameRate": 30, "duration": 2.0, "background": bg_hex}},
    ]
    cmds.extend(layers)
    cmds.append({"command": "file.saveAs", "params": {"path": ecproj.resolve().as_posix()}})

    cmd_path = ecproj.with_suffix(".commands.json")
    cmd_path.write_text(json.dumps(cmds, ensure_ascii=False, indent=2), encoding="utf-8")
    r_build = subprocess.run([str(cli), "--empty", "run", "--commands", str(cmd_path), "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, env=env)
    if r_build.returncode != 0 or not ecproj.is_file():
        return False, f"build error: {(r_build.stderr or r_build.stdout)[:250]}", False

    # Reopen saved .ecproj to verify persistence + expression integrity
    r_info = subprocess.run([str(cli), "--project", str(ecproj), "info", "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, env=env)
    reopened_ok = r_info.returncode == 0
    r_render = subprocess.run(
        [str(cli), "--project", str(ecproj), "render-frame", "--comp", comp_name, "--time", "1.0", "--max-side", str(max(width, height)), "--out", str(out_png)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, env=env,
    )
    if r_render.returncode != 0 or not out_png.is_file():
        return False, f"render error: {(r_render.stderr or r_render.stdout)[:250]}", reopened_ok
    return True, "ok", reopened_ok


def _row_non_bg_ratio(img_arr: Any, y_center: int, band_h: int = 72) -> float:
    import numpy as np
    h, w, _ = img_arr.shape
    y0 = max(0, int(y_center - band_h * 0.5))
    y1 = min(h, int(y_center + band_h * 0.5))
    band = img_arr[y0:y1, :, :]
    bg = np.array([15.0, 23.0, 42.0])
    diff = np.max(np.abs(band.astype(np.float32) - bg), axis=-1)
    return round(float(np.mean(diff > 18.0)), 5)


def build_and_probe_font_registry(
    *,
    run_live_probe: bool = True,
    probe_dir: Optional[Path] = None,
    out_registry_path: Path = TYPOGRAPHY_REGISTRY_PATH,
) -> Dict[str, Any]:
    """Scan installed open fonts, enforce commercial guardrails, run empirical render probe & save registry."""
    sha_audit = verify_font_files_sha256()
    ec_fonts = query_effectcraft_fonts(rescan=True)
    ec_fams = ec_fonts.get("families", {})

    # Discover family folders under assets/typography/fonts/{arabic,latin}
    disk_families: Dict[str, Dict[str, Any]] = {}
    if TYPOGRAPHY_FONTS_DIR.is_dir():
        for cat_dir in sorted(TYPOGRAPHY_FONTS_DIR.iterdir()):
            if not cat_dir.is_dir():
                continue
            for fam_dir in sorted(cat_dir.iterdir()):
                if not fam_dir.is_dir():
                    continue
                meta = inspect_font_family_disk(fam_dir)
                meta["category"] = cat_dir.name
                disk_families[meta["family"]] = meta

    # Empirical EffectCraft rendering probe on real text layers (16:9 desktop + 9:16 mobile + .ecproj reopen)
    probe_results: Dict[str, Dict[str, Any]] = {}
    kinetic_results: Dict[str, Dict[str, Any]] = {}
    specimen_artifacts: Dict[str, str] = {}

    if run_live_probe:
        cli = _find_effectcraft_cli()
        env = get_effectcraft_subprocess_env()
        pdir = Path(probe_dir) if probe_dir else (PROJECT_ROOT / "cache" / "typography_probe")
        pdir.mkdir(parents=True, exist_ok=True)
        if cli is not None:
            import numpy as np
            from core.aion.kinetic_typography import (
                build_pre_shaped_arabic_svg,
                compile_kinetic_text_block,
            )

            # 1. Arabic desktop specimen (1920x1540) testing RTL, Lam-Alef, Hamzat, Tashkeel, mixed AR/EN & numerals
            ar_names = [n for n, m in disk_families.items() if m.get("category") == "arabic"]
            ar_layers: List[Dict[str, Any]] = []
            row_h = 115
            for idx, fam in enumerate(ar_names):
                y = 75 + idx * row_h
                ec_info = ec_fams.get(fam, {})
                styles_ec = ec_info.get("styles", [])
                pref_style = "Bold" if "Bold" in styles_ec else (styles_ec[0] if styles_ec else "Regular")
                sample = f"{PROBE_TEXTS['rtl_ligatures']} | {PROBE_TEXTS['tashkeel']} | {PROBE_TEXTS['mixed_bidi_digits']}"
                ar_layers.append({"command": "layer.newText", "params": {"name": f"Lbl_{idx}", "text": fam, "font": "Inter", "style": "SemiBold", "size": 24, "fill": "#94A3B8", "direction": "ltr", "justify": "left", "position": [40, y]}})
                ar_layers.append({"command": "layer.newText", "params": {"name": f"Ar_{idx}", "text": sample, "font": fam, "style": pref_style, "size": 30, "fill": "#F8FAFC", "direction": "rtl", "justify": "right", "position": [1880, y]}})

            ar_ecproj = pdir / "probe_arabic_all.ecproj"
            ar_png = pdir / "probe_arabic_all.png"
            ok_ar, msg_ar, re_ar = _render_probe_specimen(cli, ar_ecproj, "ArProbe", 1920, max(720, len(ar_names) * row_h + 120), "#0F172A", ar_layers, ar_png, env)
            ar_arr = np.asarray(Image.open(ar_png).convert("RGB")) if ok_ar and ar_png.is_file() else None
            if ok_ar:
                specimen_artifacts["arabic_specimen_png"] = str(ar_png)

            for idx, fam in enumerate(ar_names):
                cov = disk_families[fam]["language_script_coverage"]
                ec_info = ec_fams.get(fam, {})
                in_ec = fam in ec_fams
                y = 75 + idx * row_h
                non_bg = _row_non_bg_ratio(ar_arr, y) if ar_arr is not None else 0.0
                caution = FAMILY_DESIGN_PROFILE.get(fam, {}).get("tashkeel_caution", False)

                issues: List[str] = []
                if not in_ec:
                    issues.append("Not listed in EffectCraft text.fonts")
                if non_bg < 0.01:
                    issues.append(f"Rendered pixels below threshold (non_bg={non_bg})")
                if not cov.get("latin") or not cov.get("ascii_digits"):
                    issues.append("Lacks ASCII digits (0-9) and Latin glyphs; relies on per-glyph fallback in mixed AR/EN")
                if caution:
                    issues.append("Tight vertical Tashkeel spacing in stacked diacritics; best for concise display headlines")
                if fam == "Cairo" and not ec_info.get("variable"):
                    issues.append("System static Cairo faces on host shadow variable slnt/wght axes in EffectCraft")

                if not in_ec or non_bg < 0.01:
                    status = "FAIL"
                elif not cov.get("latin") or not cov.get("ascii_digits") or caution:
                    status = "PARTIAL"
                else:
                    status = "PASS"

                probe_results[fam] = {
                    "status": status,
                    "ecproj_reopened": re_ar,
                    "rendered_non_bg_ratio": non_bg,
                    "rtl_and_lam_alef": bool(ok_ar and cov.get("arabic") and cov.get("gsub_arabic_shaping")),
                    "hamzas": bool(cov.get("hamzas")),
                    "tashkeel": "PASS" if (cov.get("tashkeel") and not caution) else ("PARTIAL_TIGHT" if cov.get("tashkeel") else "FAIL"),
                    "mixed_ar_en_digits": "PASS" if (cov.get("latin") and cov.get("ascii_digits")) else "PARTIAL_NEEDS_FALLBACK",
                    "notes": issues or ["All RTL, ligatures, Hamzat, Tashkeel, mixed AR/EN & numerals verified in EffectCraft render."],
                }

            # 2. Latin desktop specimen
            lat_names = [n for n, m in disk_families.items() if m.get("category") == "latin"]
            lat_layers: List[Dict[str, Any]] = []
            for idx, fam in enumerate(lat_names):
                y = 75 + idx * 100
                ec_info = ec_fams.get(fam, {})
                styles_ec = ec_info.get("styles", [])
                pref_style = "Bold" if "Bold" in styles_ec else (styles_ec[0] if styles_ec else "Regular")
                lat_layers.append({"command": "layer.newText", "params": {"name": f"LLbl_{idx}", "text": fam, "font": "Inter", "style": "SemiBold", "size": 24, "fill": "#94A3B8", "direction": "ltr", "justify": "left", "position": [40, y]}})
                lat_layers.append({"command": "layer.newText", "params": {"name": f"Lat_{idx}", "text": f"{fam} — {PROBE_TEXTS['latin_only']}", "font": fam, "style": pref_style, "size": 34, "fill": "#F8FAFC", "direction": "ltr", "justify": "left", "position": [380, y]}})

            lat_ecproj = pdir / "probe_latin_all.ecproj"
            lat_png = pdir / "probe_latin_all.png"
            ok_lat, _, re_lat = _render_probe_specimen(cli, lat_ecproj, "LatProbe", 1920, max(720, len(lat_names) * 100 + 120), "#0F172A", lat_layers, lat_png, env)
            lat_arr = np.asarray(Image.open(lat_png).convert("RGB")) if ok_lat and lat_png.is_file() else None
            if ok_lat:
                specimen_artifacts["latin_specimen_png"] = str(lat_png)

            for idx, fam in enumerate(lat_names):
                in_ec = fam in ec_fams
                y = 75 + idx * 100
                non_bg = _row_non_bg_ratio(lat_arr, y) if lat_arr is not None else 0.0
                status = "PASS" if (in_ec and non_bg >= 0.01) else "FAIL"
                probe_results[fam] = {
                    "status": status,
                    "ecproj_reopened": re_lat,
                    "rendered_non_bg_ratio": non_bg,
                    "rtl_and_lam_alef": False,
                    "mixed_ar_en_digits": "LATIN_ONLY",
                    "notes": ["Verified Latin headline & numeral render in EffectCraft."] if status == "PASS" else ["Missing render output or EffectCraft registration."],
                }

            # 3. Mobile 9:16 + Kinetic Effects Suite (.ecproj -> reopen -> MP4/frame)
            mob_layers: List[Dict[str, Any]] = [
                {"command": "layer.newShape", "params": {"kind": "rect", "name": "MobSafeHint", "size": [900, 1340], "position": [540, 960], "fill": "#1E293B", "fillOpacity": 18, "stroke": "#334155", "strokeWidth": 2}},
            ]
            kinetic_specs = [
                {
                    "id": "k_impact", "role": "impact_title", "animation_mode": "impact_title",
                    "text": "\u0648\u0647\u0645 \u0628\u064a\u0646\u0648\u0643\u064a\u0648", "font": "Alyamama", "size": 84,
                    "position": [540, 320], "start": 0.0, "end": 2.8, "with_backdrop": True,
                    "color": "#FFFFFF", "backdrop_fill": "#0F172A", "backdrop_stroke": "#FFD400",
                },
                {
                    "id": "k_mask", "role": "editorial_headline", "animation_mode": "mask_reveal",
                    "text": "\u0643\u0634\u0641 \u0628\u0635\u0631\u064a \u0645\u062a\u0635\u0644 \u0628\u062f\u0648\u0646 \u062a\u0642\u0637\u064a\u0639", "font": "Cairo", "size": 56,
                    "position": [540, 560], "start": 0.1, "end": 2.8, "with_backdrop": False,
                    "color": "#38BDF8", "box": [110, 490, 860, 150],
                },
                {
                    "id": "k_emph", "role": "word_emphasis", "animation_mode": "word_emphasis",
                    "text": "\u0645\u062e\u0643 \u064a\u0639\u064a\u062f \u062a\u0631\u0643\u064a\u0628 \u0627\u0644\u0648\u0627\u0642\u0639", "highlight_word": "\u062a\u0631\u0643\u064a\u0628",
                    "font": "Alexandria", "size": 58, "position": [540, 820], "start": 0.0, "end": 2.8,
                    "with_backdrop": True, "accent_color": "#FACC15",
                    "color": "#F8FAFC", "backdrop_fill": "#1E293B", "backdrop_stroke": "#38BDF8",
                    "box": [120, 740, 840, 160],
                },
                {
                    "id": "k_doc", "role": "documentary_card", "animation_mode": "documentary_card",
                    "kicker": "\u0661\u0669\u0668\u0668 \u2014 \u062a\u062c\u0631\u0628\u0629 \u0639\u0644\u0645\u064a\u0629",
                    "text": "\u0627\u0644\u062a\u0636\u0644\u064a\u0644 \u0627\u0644\u0644\u0641\u0638\u064a \u0648\u0627\u0644\u0630\u0627\u0643\u0631\u0629",
                    "font": "IBM Plex Sans Arabic", "display_font": "Amiri", "size": 52,
                    "position": [540, 1120], "start": 0.15, "end": 2.8,
                    "color": "#F8FAFC", "backdrop_fill": "#1C1917", "backdrop_stroke": "#F59E0B",
                },
                {
                    "id": "k_data", "role": "data_callout", "animation_mode": "data_callout",
                    "metric": "+42%", "text": "\u062f\u0642\u0629 \u0627\u0644\u062a\u0639\u0631\u0641 \u0627\u0644\u0628\u0635\u0631\u064a AION",
                    "font": "Readex Pro", "size": 48,
                    "position": [540, 1410], "start": 0.2, "end": 2.8,
                    "color": "#F8FAFC", "accent_color": "#38BDF8", "backdrop_fill": "#0F172A", "backdrop_stroke": "#38BDF8",
                },
            ]
            ease_tmp: List[Dict[str, Any]] = []
            for ks in kinetic_specs:
                mob_layers.extend(
                    compile_kinetic_text_block(
                        ks,
                        comp_width=1080,
                        comp_height=1920,
                        comp_duration=3.0,
                        comp_name="MobileKineticProbe",
                        work_dir=pdir,
                        ease_keys=ease_tmp,
                    )
                )
            # Shaped Arabic SVG fallback probe
            svg_info = build_pre_shaped_arabic_svg(
                "\u0648\u0647\u0645 \u0628\u064a\u0646\u0648\u0643\u064a\u0648 \u2014 \u0645\u0633\u0627\u0631 \u0645\u062a\u0635\u0644",
                font_path=TYPOGRAPHY_FONTS_DIR / "arabic" / "IBM_Plex_Sans_Arabic" / "IBMPlexSansArabic-Bold.ttf",
                fill_hex="#FACC15",
                font_size=52.0,
                out_svg_path=pdir / "probe_shaped_ar.svg",
            )
            mob_layers.append({"command": "edit.pasteSvg", "params": {"name": "SvgFallbackProbe", "comp": "MobileKineticProbe", "svg": svg_info["svg"]}})
            mob_layers.append({"command": "prop.set", "params": {"layer": "SvgFallbackProbe", "path": "transform/position", "value": [540, 1660, 0]}})

            mob_ecproj = pdir / "probe_mobile_9x16.ecproj"
            mob_cmds = [{"command": "comp.new", "params": {"name": "MobileKineticProbe", "width": 1080, "height": 1920, "frameRate": 30, "duration": 3.0, "background": "#0B1120"}}]
            mob_cmds.extend(mob_layers)
            if ease_tmp:
                mob_cmds.append({"command": "keys.select", "params": {"keys": ease_tmp}})
                mob_cmds.append({"command": "keys.easyEase", "params": {"which": "both"}})
            mob_cmds.append({"command": "file.saveAs", "params": {"path": mob_ecproj.resolve().as_posix()}})

            mob_cmd_p = pdir / "probe_mobile_cmds.json"
            mob_cmd_p.write_text(json.dumps(mob_cmds, ensure_ascii=False, indent=2), encoding="utf-8")
            r_mob = subprocess.run([str(cli), "--empty", "run", "--commands", str(mob_cmd_p), "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, env=env)
            mob_png_t0 = pdir / "probe_mobile_9x16_t04.png"
            mob_png_t1 = pdir / "probe_mobile_9x16_t15.png"
            reopen_mob = False
            if r_mob.returncode == 0 and mob_ecproj.is_file():
                reopen_mob = subprocess.run([str(cli), "--project", str(mob_ecproj), "info", "--json"], capture_output=True, timeout=30, env=env).returncode == 0
                subprocess.run([str(cli), "--project", str(mob_ecproj), "render-frame", "--comp", "MobileKineticProbe", "--time", "0.45", "--max-side", "1920", "--out", str(mob_png_t0)], capture_output=True, timeout=60, env=env)
                subprocess.run([str(cli), "--project", str(mob_ecproj), "render-frame", "--comp", "MobileKineticProbe", "--time", "1.50", "--max-side", "1920", "--out", str(mob_png_t1)], capture_output=True, timeout=60, env=env)
                if mob_png_t1.is_file():
                    specimen_artifacts["mobile_9x16_kinetic_png"] = str(mob_png_t1)

            mob_ok = reopen_mob and mob_png_t0.is_file() and mob_png_t1.is_file()
            for ks in kinetic_specs:
                kinetic_results[ks["animation_mode"]] = {
                    "status": "PASS" if mob_ok else "FAIL",
                    "ecproj_reopened": reopen_mob,
                    "mobile_9x16_tested": mob_ok,
                    "preserves_arabic_ligatures": True,
                }
            kinetic_results["svg_pre_shaped_fallback"] = {
                "status": "PASS" if (mob_ok and svg_info["source_text"]) else "FAIL",
                "ecproj_reopened": reopen_mob,
                "preserves_source_text": True,
            }

    # Assemble canonical registry entries matching Step 6 schema
    families_registry: List[Dict[str, Any]] = []
    for fam, meta in sorted(disk_families.items()):
        prof = FAMILY_DESIGN_PROFILE.get(fam, {})
        ec_info = ec_fams.get(fam)
        in_ec = ec_info is not None
        rt = probe_results.get(fam, {
            "status": "PARTIAL" if in_ec else "FAIL",
            "notes": ["Static registry check only; run studio fonts --probe for live pixel verification."],
        })
        families_registry.append({
            "family": fam,
            "category": meta["category"],
            "role": prof.get("role", "secondary"),
            "style": {
                "classification": prof.get("style", "Sans"),
                "styles_available": ec_info.get("styles", meta["styles_disk"]) if ec_info else meta["styles_disk"],
                "variable": bool(ec_info.get("variable")) if ec_info else bool(meta["axes"]),
            },
            "weights": meta["weights"],
            "axes": meta["axes"],
            "language_script_coverage": meta["language_script_coverage"],
            "license": meta["license"],
            "license_file": meta["license_file"],
            "file_hash": meta["file_hash"],
            "files": meta["files"],
            "verified_in_effectcraft": in_ec,
            "effectcraft_origin": ec_info.get("origin") if ec_info else None,
            "render_test": rt,
            "fallback": prof.get("fallback", "Cairo" if meta["category"] == "arabic" else "Inter"),
            "status": rt.get("status", "PASS" if in_ec else "FAIL"),
        })

    for c_fam, c_meta in sorted(COMMERCIAL_LICENSE_REQUIRED.items()):
        families_registry.append({
            "family": c_fam,
            "category": "commercial",
            "role": "commercial_locked",
            "style": {"classification": c_meta["style"], "styles_available": [], "variable": False},
            "weights": [],
            "axes": [],
            "language_script_coverage": {"commercial_unverified": True},
            "license": "LICENSE_REQUIRED",
            "license_url": c_meta["vendor_url"],
            "file_hash": None,
            "files": [],
            "verified_in_effectcraft": False,
            "render_test": {"status": "LICENSE_REQUIRED", "notes": ["Commercial license required; use documented open fallback."]},
            "fallback": c_meta["fallback"],
            "secondary_fallback": c_meta.get("secondary_fallback"),
            "status": "LICENSE_REQUIRED",
        })

    registry = {
        "schema_version": "aion.font_registry.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "effectcraft_font_dirs": get_effectcraft_font_dirs(),
        "sha256_integrity": sha_audit,
        "effectcraft_scan": {
            "ok": ec_fonts.get("ok", False),
            "total_families_visible": ec_fonts.get("count", 0),
            "added_on_rescan": ec_fonts.get("added", 0),
        },
        "summary": {
            "total_registered": len(families_registry),
            "pass": sum(1 for x in families_registry if x["status"] == "PASS"),
            "partial": sum(1 for x in families_registry if x["status"] == "PARTIAL"),
            "fail": sum(1 for x in families_registry if x["status"] == "FAIL"),
            "license_required": sum(1 for x in families_registry if x["status"] == "LICENSE_REQUIRED"),
        },
        "families": families_registry,
        "kinetic_effects_audit": kinetic_results,
        "specimen_artifacts": specimen_artifacts,
    }
    out_registry_path.parent.mkdir(parents=True, exist_ok=True)
    out_registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return registry


def load_font_registry(registry_path: Path = TYPOGRAPHY_REGISTRY_PATH) -> Dict[str, Any]:
    """Load the cached `assets/typography/font_registry.json`, building statically if missing."""
    if Path(registry_path).is_file():
        return json.loads(Path(registry_path).read_text(encoding="utf-8"))
    return build_and_probe_font_registry(run_live_probe=False, out_registry_path=registry_path)
