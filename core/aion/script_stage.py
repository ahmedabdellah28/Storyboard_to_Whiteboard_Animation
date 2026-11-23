"""Stage 1: Script Ingestion, Multi-Format Parsing, Validation & Splitting."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PLACEHOLDER_PATTERNS = (
    "[اكتب هنا نص السكربت الصوتي",
    "[عنوان المشهد",
    "TODO: write section script",
)


def is_placeholder_script(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return True
    for pat in PLACEHOLDER_PATTERNS:
        if pat in stripped:
            return True
    return False


def _strip_section_header_lines(raw: str) -> str:
    lines: List[str] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            lines.append("")
            continue
        if re.match(r"^(#|\[?SECTION\s+\d+|##\s+\d+\.)", s, re.I):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def split_master_script_sections(master_text: str) -> List[Tuple[int, str, str]]:
    """Parses `master_script.txt` / `.md` supporting:
    - `[SECTION 01: Title]`
    - `SECTION 01 - Title` / `SECTION 01`
    - `## 1. Title`
    Returns sorted list of `(section_num, title, clean_body)`.
    """
    body = master_text.split("\n---\n")[0]
    pat = re.compile(
        r"^(?:\[SECTION\s+0*(\d+)(?::\s*([^\]]+))?\]|SECTION\s+0*(\d+)(?:\s*[-–:]\s*(.+))?|##\s+0*(\d+)\.\s+(.+))\s*$",
        re.M | re.I,
    )
    matches = list(pat.finditer(body))
    if not matches:
        return []

    out: List[Tuple[int, str, str]] = []
    for i, m in enumerate(matches):
        num_str = m.group(1) or m.group(3) or m.group(5)
        title = (m.group(2) or m.group(4) or m.group(6) or f"Section {int(num_str):02d}").strip()
        st = m.end()
        en = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        chunk = body[st:en].strip()
        clean_lines = [ln for ln in chunk.splitlines() if not ln.strip().startswith("#")]
        clean_body = "\n".join(clean_lines).strip()
        if not is_placeholder_script(clean_body):
            out.append((int(num_str), title, clean_body))
    return out


def resolve_section_script(
    sec_num: int,
    sections_script_dir: Path,
    legacy_scripts_dir: Optional[Path],
    master_script: Optional[Path],
) -> str:
    """Loads validated narration text for `sec_num`, ignoring template stubs."""
    sec_id = f"section_{sec_num:02d}"
    candidates = [sections_script_dir / f"{sec_id}.txt"]
    if legacy_scripts_dir:
        candidates.append(legacy_scripts_dir / f"{sec_id}.txt")

    for cand in candidates:
        if cand.is_file():
            raw = cand.read_text(encoding="utf-8").strip()
            cleaned = _strip_section_header_lines(raw)
            if not is_placeholder_script(cleaned):
                return cleaned

    if master_script and master_script.is_file():
        ms_text = master_script.read_text(encoding="utf-8")
        for num, _title, body in split_master_script_sections(ms_text):
            if num == sec_num and not is_placeholder_script(body):
                return body
    return ""


def run_script_stage(
    proj_dir: Path,
    sec_num: Optional[int] = None,
    split: bool = True,
) -> Dict[str, Any]:
    """Splits master script into per-section files and validates word budgets."""
    inputs_dir = proj_dir / "inputs" if (proj_dir / "inputs").exists() else (proj_dir / "input")
    script_dir = inputs_dir / "script"
    sec_scripts_dir = script_dir / "sections"
    master_script = script_dir / "master_script.txt"
    if not master_script.is_file() and (inputs_dir / "master_script.txt").is_file():
        master_script = inputs_dir / "master_script.txt"

    split_written: List[str] = []
    if split and master_script.is_file():
        sec_scripts_dir.mkdir(parents=True, exist_ok=True)
        for num, _title, body in split_master_script_sections(master_script.read_text(encoding="utf-8")):
            if sec_num is not None and num != sec_num:
                continue
            target = sec_scripts_dir / f"section_{num:02d}.txt"
            target.write_text(body + "\n", encoding="utf-8")
            split_written.append(target.name)

    sections_report: Dict[str, Any] = {}
    targets = [sec_num] if sec_num is not None else sorted(
        {
            int(p.stem.split("_")[1])
            for p in (sec_scripts_dir.glob("section_*.txt") if sec_scripts_dir.is_dir() else [])
            if "_" in p.stem and p.stem.split("_")[1].isdigit()
        }
        or {n for n, _, _ in (split_master_script_sections(master_script.read_text(encoding="utf-8")) if master_script.is_file() else [])}
    )

    for num in targets:
        sid = f"section_{num:02d}"
        text = resolve_section_script(num, sec_scripts_dir, inputs_dir / "scripts", master_script)
        wc = len(text.split()) if text else 0
        sections_report[sid] = {
            "valid": bool(text) and wc >= 3,
            "words": wc,
            "warning": "Script missing or placeholder stub" if wc < 3 else None,
        }

    return {
        "ok": bool(sections_report) and all(v["valid"] for v in sections_report.values()),
        "split_written": split_written,
        "sections": sections_report,
    }
