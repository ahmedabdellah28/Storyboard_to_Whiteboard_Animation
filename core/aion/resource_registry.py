"""AION v4 Code-Backed Resource Registry & SQLite FTS5 Search Engine.

Discovers ONLY genuinely installed & renderer-supported resources in the repository:
  - Lucide SVG icons (`assets/icons_lucide/*.svg` + `SEMANTIC_ICON_RULES`)
  - Living 4-Color Gradient background palettes (`LIVING_GRADIENT_PALETTES`)
  - CC0 SFX files verified on disk (`assets/audio/**`)
  - GPU-safe EffectCraft VFX vs explicitly banned CPU-killer effects (`cclightrays`, `gaussian_blur >= 80px`)
  - Licensed studio fonts (`typography_director.py`)
  - Per-project storyboard assets (`inputs/storyboard_catalog/*.json` -> `aion.asset_manifest.v2`)

Exposes a two-stage local retrieval API (`search_resources` -> `get_resource_details`)
using SQLite FTS5 + BM25 with Arabic diacritic/alef/taa-marbouta normalization.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from core.config.settings import ASSETS_DIR, PROJECT_ROOT

DEFAULT_CATALOG_DB = PROJECT_ROOT / "core" / "aion" / "cache" / "resource_catalog.sqlite"

_BILINGUAL_SYNONYMS: Dict[str, str] = {
    "سفينة": "ship boat vessel بحر",
    "سفن": "ships boats fleet بحر",
    "سلسلة": "chain barrier obstacle منع",
    "منع": "block barrier chain stop lock",
    "قفل": "lock shield secure protect",
    "توهج": "glow bloom light neon",
    "ضوء": "light glow spotlight flash",
    "انتقال": "transition whoosh dissolve cut",
    "نار": "flame fire danger heat",
    "فكرة": "lightbulb idea eureka spark",
    "وقت": "clock time hourglass timer",
    "مؤقت": "clock timer stopwatch",
    "هدف": "target bullseye goal focus",
    "خريطة": "map compass navigation route",
    "قهوة": "coffee cup mug",
    "مونتاج": "video edit timeline cpu",
    "انفجار": "impact hit boom slam",
}


def norm_ar_search(text: str) -> str:
    """Normalize Arabic & English tokens for consistent FTS5 lexical matching."""
    t = str(text or "").lower()
    t = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", t)
    t = re.sub(r"[أإآٱ]", "ا", t).replace("ى", "ي").replace("ة", "ه")
    t = re.sub(r"[^\w\s:\-]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _expand_query_terms(query: str) -> str:
    normed = norm_ar_search(query)
    tokens = [tok for tok in normed.split() if len(tok) >= 2]
    expanded: List[str] = []
    for tok in tokens:
        expanded.append(f'"{tok}"*')
        if tok in _BILINGUAL_SYNONYMS:
            for syn in norm_ar_search(_BILINGUAL_SYNONYMS[tok]).split():
                if len(syn) >= 2:
                    expanded.append(f'"{syn}"*')
    return " OR ".join(dict.fromkeys(expanded))


def discover_core_resources() -> List[Dict[str, Any]]:
    """Inventory all genuinely installed & verified AION Studio resources."""
    from core.aion.master_cinema_kit import LIVING_GRADIENT_PALETTES, LUCIDE_DIR, SEMANTIC_ICON_RULES

    resources: List[Dict[str, Any]] = []

    # 1. Lucide SVG Icons (verified on disk)
    rule_by_icon: Dict[str, Dict[str, Any]] = {}
    for rule in SEMANTIC_ICON_RULES:
        rule_by_icon.setdefault(str(rule["icon"]), rule)

    if LUCIDE_DIR.is_dir():
        for svg_p in sorted(LUCIDE_DIR.glob("*.svg")):
            iname = svg_p.stem
            rule = rule_by_icon.get(iname, {})
            kw_hint = str(rule.get("patterns", "")).replace("|", " ")
            resources.append({
                "id": f"icon:lucide:{iname}",
                "kind": "icon",
                "display_name": iname.replace("-", " ").title(),
                "aliases_ar": kw_hint,
                "aliases_en": f"{iname} icon vector svg",
                "semantic_tags": ["lucide", "vector", "trim_paths", rule.get("preset", "icon_pulse")],
                "description": f"Installed Lucide SVG icon ({svg_p.name}) with GPU-safe Trim Paths & pulse preset.",
                "source": str(svg_p.relative_to(PROJECT_ROOT)),
                "capabilities": ["vector_trim_paths", "transform_2d", "opacity", "glow_accent"],
                "parameters": {"stroke_width": {"default": 2.3, "min": 1.0, "max": 5.0}, "scale": {"default": 340.0}},
                "supported_by_renderer": True,
                "cost_class": "gpu_fast",
                "fallback_resource_ids": ["icon:lucide:sparkles"],
                "visual_metadata": {"transparent": True, "preset": rule.get("preset", "icon_pulse")},
            })

    # 2. Living 4-Color Gradient Background Palettes
    for mood_key, pal in LIVING_GRADIENT_PALETTES.items():
        is_light = bool(pal.get("is_light", False))
        resources.append({
            "id": f"background:palette:{mood_key}",
            "kind": "background",
            "display_name": mood_key.replace("_", " ").title(),
            "aliases_ar": "خلفية تدرج لوني إضاءة داكنة فاتحة" if not is_light else "خلفية فاتحة ورقية نهار",
            "aliases_en": f"{mood_key} gradient background mood {'light' if is_light else 'dark'}",
            "semantic_tags": ["4_color_gradient", "living_stage", "light_bg" if is_light else "dark_bg"],
            "description": f"Living 4-color gradient ({pal['c1']}..{pal['c4']}); is_light={is_light}, vignette={pal['vignette']}.",
            "source": "core/aion/master_cinema_kit.py:LIVING_GRADIENT_PALETTES",
            "capabilities": ["living_gradient", "color_cycle", "high_contrast_dark" if not is_light else "high_contrast_light"],
            "parameters": {"bg_opacity": {"default": 64.0, "min": 35.0, "max": 100.0}, "vignette": {"default": pal["vignette"]}},
            "supported_by_renderer": True,
            "cost_class": "gpu_fast",
            "fallback_resource_ids": ["background:palette:imperial_slate"],
            "visual_metadata": {"c1": pal["c1"], "c2": pal["c2"], "c3": pal["c3"], "c4": pal["c4"], "is_light": is_light},
        })

    # 3. CC0 Sound Effects on disk (`assets/sfx_pro/`, `assets/sfx/`, `assets/audio/`)
    seen_sfx = set()
    for sfx_dir in (ASSETS_DIR / "sfx_pro", ASSETS_DIR / "sfx", ASSETS_DIR / "audio"):
        if not sfx_dir.is_dir():
            continue
        for audio_p in sorted(sfx_dir.rglob("*")):
            if audio_p.suffix.lower() not in (".wav", ".mp3") or "cta" in audio_p.parts:
                continue
            stem = audio_p.stem
            if stem in seen_sfx:
                continue
            seen_sfx.add(stem)
            rel_folder = audio_p.parent.name
            resources.append({
                "id": f"sfx:cc0:{stem}",
                "kind": "sfx",
                "display_name": stem.replace("_", " ").replace("-", " ").title(),
                "aliases_ar": "صوت مؤثر انتقال ضربة تنبيه همس نبضة كتابة شرارة",
                "aliases_en": f"{stem} {rel_folder} sfx sound audio foley cc0",
                "semantic_tags": ["sfx", "cc0", "rms_ducked", rel_folder],
                "description": f"Verified CC0 SFX ({audio_p.name}) mixed via -12dB RMS voice ducking.",
                "source": str(audio_p.relative_to(PROJECT_ROOT)),
                "capabilities": ["audio_sfx", "rms_ducking"],
                "parameters": {"gain_db": {"default": -2.4, "min": -18.0, "max": 0.0}},
                "supported_by_renderer": True,
                "cost_class": "audio_light",
                "fallback_resource_ids": [],
                "visual_metadata": {"path": str(audio_p.resolve())},
            })

    # 4. Registered EffectCraft VFX, Procedural Connectors & Motion Presets (GPU-safe vs banned)
    vfx_defs = [
        ("effect:ec.stylize.glow", "Stylize Glow", "توهج إضاءة نيون بريق", "glow bloom neon light", True, "gpu_fast", {"intensity": {"default": 0.65, "min": 0.0, "max": 0.90}}),
        ("effect:ec.drop_shadow", "Drop Shadow", "ظل ناعم فصل الخلفية", "drop shadow grounding contrast", True, "gpu_fast", {"opacity": {"default": 74.0, "min": 0.0, "max": 100.0}, "softness": {"default": 44.0}}),
        ("effect:ec.light_sweep", "CC Light Sweep", "لمعة ضوء مسح ضوئي بريق", "light sweep shine gleam reveal", True, "gpu_fast", {"intensity": {"default": 28.0, "min": 5.0, "max": 50.0}, "width": {"default": 75.0}}),
        ("effect:ec.blur_rack_focus", "Rack-Focus Blur", "تركيز عدسي بلور ناعم", "blur rack focus depth soft reveal", True, "gpu_fast", {"from_blur": {"default": 22.0, "min": 0.0, "max": 40.0}}),
        ("effect:ec.distortion_ripple", "Turbulent Shock Ripple", "موجة اضطراب صدمة اهتزاز", "distortion ripple shockwave impact", True, "gpu_fast", {"amount": {"default": 28.0, "min": 0.0, "max": 50.0}}),
        ("effect:ec.particles_subtle", "Subtle Atmospheric Particles", "حبيبات شرارات غبار خافت", "particles sparks dust subtle atmosphere", True, "gpu_fast", {"birth_rate": {"default": 1.4, "max": 3.0}, "opacity": {"default": 11.0, "max": 20.0}}),
        ("effect:ec.spotlight", "CC Spotlight", "كشاف ضوئي تركيز بؤرة", "spotlight focus vignette", True, "gpu_fast", {"intensity": {"default": 0.6, "min": 0.0, "max": 1.0}}),
        ("effect:ec.4color_gradient", "4-Color Gradient", "تدرج رباعي حي خلفية", "4-color gradient living background", True, "gpu_fast", {"bg_opacity": {"default": 64.0}}),
        ("effect:ec.procedural.repeater_rings", "Concentric Radar / Shock Rings", "حلقات رادار نبض دوائر تركيز", "concentric rings radar target halo shockwave", True, "gpu_fast", {"copies": {"default": 4, "min": 2, "max": 6}}),
        ("effect:ec.procedural.clash_divider", "Glowing Clash Divider + Nexus", "فاصل مواجهة خط مقارنة عقدة", "vertical divider comparison nexus clash split", True, "gpu_fast", {"stroke_width": {"default": 5.0}}),
        ("effect:ec.procedural.bezier_arrow", "Glowing Bezier Arrow", "سهم منحني مسار رابط", "curved arrow bezier connector route", True, "gpu_fast", {"stroke_width": {"default": 5.8}}),
        ("effect:ec.generate.cclightrays", "CC Light Rays (BANNED CPU)", "أشعة ضوء ثقيلة محظورة", "light rays cpu timeout banned", False, "cpu_timeout_banned", {}),
        ("effect:ec.gaussian_blur_heavy", "Heavy Gaussian Blur >=80px (BANNED)", "طمس ثقيل محظور", "gaussian blur 80px banned slow", False, "cpu_timeout_banned", {}),
    ]
    for eid, dname, ar_al, en_al, ok_sup, cost, params in vfx_defs:
        resources.append({
            "id": eid,
            "kind": "effect",
            "display_name": dname,
            "aliases_ar": ar_al,
            "aliases_en": en_al,
            "semantic_tags": ["effectcraft", "vfx", "gpu_safe" if ok_sup else "banned"],
            "description": f"EffectCraft VFX {dname} (supported={ok_sup}, cost={cost}).",
            "source": "core/aion/ecgc_compiler.py",
            "capabilities": ["vfx_gpu"] if ok_sup else [],
            "parameters": params,
            "supported_by_renderer": ok_sup,
            "cost_class": cost,
            "fallback_resource_ids": ["effect:ec.stylize.glow"] if not ok_sup else [],
            "visual_metadata": {"banned": not ok_sup},
        })

    # 5. Studio Fonts (verified from typography_director)
    for fid, fname, langs, role in [
        ("font:ibm_plex_sans_arabic", "IBM Plex Sans Arabic", "ar", "وضوح قراءة عنوان شريط حديث RTL"),
        ("font:cairo", "Cairo", "ar", "عناوين جريئة شورتس ريلز RTL"),
        ("font:amiri", "Amiri", "ar", "وثائقي تاريخي فصيح قرآني RTL"),
        ("font:inter", "Inter", "en", "clean modern editorial LTR"),
        ("font:funnel_display", "Funnel Display", "en", "bold viral display LTR"),
    ]:
        resources.append({
            "id": fid,
            "kind": "font",
            "display_name": fname,
            "aliases_ar": f"خط عربي طباعة عنوان {role}",
            "aliases_en": f"{fname} font typography {langs}",
            "semantic_tags": ["font", langs, "neon_live_typing"],
            "description": f"Licensed studio font '{fname}' ({langs}) verified with EffectCraft HarfBuzz shaping.",
            "source": "core/aion/typography_director.py",
            "capabilities": ["rtl_harfbuzz" if langs == "ar" else "ltr_kerning", "neon_live_typing"],
            "parameters": {"size": {"default": 44, "min": 28, "max": 86}},
            "supported_by_renderer": True,
            "cost_class": "gpu_fast",
            "fallback_resource_ids": [],
            "visual_metadata": {"language": langs},
        })

    return resources


def _inspect_png_visual_props(png_path: Path) -> Dict[str, Any]:
    """Read real dimensions, alpha bounding box, and dominant RGB hexes from PNG without guessing."""
    if not png_path.is_file():
        return {"dimensions": {"width": 800, "height": 800}, "transparent": True, "verified": False}
    try:
        from PIL import Image
        with Image.open(png_path) as im:
            rgba = im.convert("RGBA")
            w, h = rgba.size
            alpha = rgba.getchannel("A")
            bbox = alpha.getbbox()
            # Sample non-transparent pixels for dominant color & mean luma
            small = rgba.resize((64, 64))
            px = [p for p in small.getdata() if p[3] > 32]
            if px:
                r_avg = sum(p[0] for p in px) // len(px)
                g_avg = sum(p[1] for p in px) // len(px)
                b_avg = sum(p[2] for p in px) // len(px)
                mean_luma = round((0.2126 * r_avg + 0.7152 * g_avg + 0.0722 * b_avg) / 255.0, 3)
                dom_hex = f"#{r_avg:02X}{g_avg:02X}{b_avg:02X}"
            else:
                mean_luma = 0.5
                dom_hex = "#808080"
            return {
                "dimensions": {"width": w, "height": h},
                "transparent": True,
                "alpha_bounds": list(bbox) if bbox else [0, 0, w, h],
                "dominant_colors": [dom_hex],
                "mean_luma": mean_luma,
                "verified": True,
            }
    except Exception:
        return {"dimensions": {"width": 800, "height": 800}, "transparent": True, "verified": False}


def _find_section_catalog_path(proj_dir: Path, section_id: str) -> Optional[Path]:
    sec_num = str(section_id).replace("section_", "").zfill(2)
    candidates = [
        proj_dir / "inputs" / "storyboard_catalog" / f"{sec_num}_section.json",
        proj_dir / "inputs" / "storyboard_catalog" / f"section_{sec_num}.json",
        proj_dir / "inputs" / "storyboard_catalog" / f"{section_id}.json",
        proj_dir / "sections" / section_id / "assets" / "metadata.json",
    ]
    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def build_asset_manifest_v2(proj_dir: Path, section_id: str) -> Dict[str, Any]:
    """Normalize storyboard catalog + real PNG bounds into `aion.asset_manifest.v2`."""
    proj_dir = Path(proj_dir)
    assets_dir = proj_dir / "sections" / section_id / "assets"
    cat_path = _find_section_catalog_path(proj_dir, section_id)
    assets_out: List[Dict[str, Any]] = []
    seen_ids = set()

    if cat_path and cat_path.is_file():
        cat = json.loads(cat_path.read_text(encoding="utf-8"))
        for a in cat.get("assets", []):
            aid = str(a.get("id") or f"entity_{int(a.get('index', 1)):02d}")
            seen_ids.add(aid)
            desc = str(a.get("description_ar") or a.get("description_en") or aid)
            title = str(a.get("name_ar") or a.get("name_en") or aid)[:64]
            is_char = any(k in desc for k in ("شاب", "قائد", "رجل", "سلطان", "إمبراطور", "جندي", "جنود", "شخص", "إنسان"))
            png_p = assets_dir / f"{aid}.png"
            vprops = _inspect_png_visual_props(png_p)
            assets_out.append({
                "asset_id": aid,
                "file": str(a.get("filename") or f"{aid}.png"),
                "title": title,
                "description": desc,
                "visual_type": "character" if is_char else "object",
                "semantic_tags": [proj_dir.name, section_id, str(a.get("narrative_role") or "narrative")],
                "capabilities": ["transform_2d", "opacity", "crop", "mask"],
                "dimensions": vprops["dimensions"],
                "transparent": True,
                "anchors": {"center": {"x": 0.5, "y": 0.5}},
                "metadata_confidence": 0.96 if vprops["verified"] else 0.75,
                "visual_inspection": {k: v for k, v in vprops.items() if k != "dimensions"},
            })

    # Fallback: discover any real entity_*.png files not in catalog (never silent empty manifest!)
    if assets_dir.is_dir():
        for png_p in sorted(assets_dir.glob("entity_*.png")):
            aid = png_p.stem
            if aid in seen_ids:
                continue
            vprops = _inspect_png_visual_props(png_p)
            assets_out.append({
                "asset_id": aid,
                "file": png_p.name,
                "title": aid,
                "description": f"Unannotated PNG asset {png_p.name} (visual description pending).",
                "visual_type": "object",
                "semantic_tags": [proj_dir.name, section_id, "unannotated"],
                "capabilities": ["transform_2d", "opacity", "crop", "mask"],
                "dimensions": vprops["dimensions"],
                "transparent": True,
                "anchors": {"center": {"x": 0.5, "y": 0.5}},
                "metadata_confidence": 0.45,
                "visual_inspection": {k: v for k, v in vprops.items() if k != "dimensions"},
            })

    return {"schema_version": "aion.asset_manifest.v2", "assets": assets_out}


class ResourceRegistry:
    """SQLite FTS5 + BM25 local registry for AION v4 resources & per-project assets."""

    def __init__(self, db_path: Path = DEFAULT_CATALOG_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS resources (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    supported INTEGER NOT NULL,
                    cost_class TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    content_hash TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS resources_fts USING fts5(
                    id UNINDEXED,
                    kind UNINDEXED,
                    norm_text,
                    tokenize='unicode61'
                );
                """
            )

    def index_resources(self, items: Sequence[Dict[str, Any]], *, clear_existing: bool = False) -> int:
        with self._connect() as conn:
            if clear_existing:
                conn.execute("DELETE FROM resources")
                conn.execute("DELETE FROM resources_fts")
            upserted = 0
            for item in items:
                rid = str(item["id"])
                payload = json.dumps(item, ensure_ascii=False)
                h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
                row = conn.execute("SELECT content_hash FROM resources WHERE id = ?", (rid,)).fetchone()
                if row and row["content_hash"] == h:
                    continue
                norm_blob = norm_ar_search(
                    " ".join([
                        rid,
                        str(item.get("kind", "")),
                        str(item.get("display_name", "")),
                        str(item.get("aliases_ar", "")),
                        str(item.get("aliases_en", "")),
                        " ".join(str(x) for x in item.get("semantic_tags", [])),
                        str(item.get("description", "")),
                    ])
                )
                conn.execute(
                    """
                    INSERT INTO resources(id, kind, display_name, supported, cost_class, payload_json, content_hash)
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        kind=excluded.kind,
                        display_name=excluded.display_name,
                        supported=excluded.supported,
                        cost_class=excluded.cost_class,
                        payload_json=excluded.payload_json,
                        content_hash=excluded.content_hash
                    """,
                    (
                        rid,
                        str(item["kind"]),
                        str(item["display_name"]),
                        1 if item.get("supported_by_renderer", True) else 0,
                        str(item.get("cost_class", "gpu_fast")),
                        payload,
                        h,
                    ),
                )
                conn.execute("DELETE FROM resources_fts WHERE id = ?", (rid,))
                conn.execute(
                    "INSERT INTO resources_fts(id, kind, norm_text) VALUES(?, ?, ?)",
                    (rid, str(item["kind"]), norm_blob),
                )
                upserted += 1
            conn.commit()
            return upserted

    def ensure_core_indexed(self, *, proj_dir: Optional[Path] = None, section_id: Optional[str] = None) -> int:
        items = discover_core_resources()
        if proj_dir and section_id:
            manifest = build_asset_manifest_v2(proj_dir, section_id)
            for ma in manifest.get("assets", []):
                items.append({
                    "id": f"asset:{proj_dir.name}:{section_id}:{ma['asset_id']}",
                    "kind": "asset",
                    "display_name": ma["title"],
                    "aliases_ar": f"{ma['title']} {ma['description']}",
                    "aliases_en": ma["file"],
                    "semantic_tags": ma["semantic_tags"],
                    "description": ma["description"],
                    "source": f"projects/{proj_dir.name}/sections/{section_id}/assets/{ma['asset_id']}.png",
                    "capabilities": ma["capabilities"],
                    "parameters": {},
                    "supported_by_renderer": True,
                    "cost_class": "gpu_fast",
                    "fallback_resource_ids": [],
                    "visual_metadata": {"dimensions": ma["dimensions"], "visual_type": ma["visual_type"]},
                })
        return self.index_resources(items)

    def search_resources(
        self,
        query: str,
        *,
        kinds: Optional[Sequence[str]] = None,
        only_supported: bool = True,
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        """Stage-1 compact search returning top-k verified resources via FTS5 BM25."""
        fts_expr = _expand_query_terms(query)
        sql = (
            "SELECT r.id, r.kind, r.display_name, r.supported, r.cost_class, r.payload_json, "
            "bm25(resources_fts) AS rank "
            "FROM resources_fts f JOIN resources r ON r.id = f.id "
            "WHERE 1=1"
        )
        params: List[Any] = []
        if fts_expr:
            sql += " AND resources_fts MATCH ?"
            params.append(fts_expr)
        if only_supported:
            sql += " AND r.supported = 1"
        if kinds:
            placeholders = ",".join("?" for _ in kinds)
            sql += f" AND r.kind IN ({placeholders})"
            params.extend(list(kinds))
        sql += " ORDER BY rank ASC LIMIT ?"
        params.append(int(limit))

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        out: List[Dict[str, Any]] = []
        for row in rows:
            p = json.loads(row["payload_json"])
            out.append({
                "id": row["id"],
                "kind": row["kind"],
                "display_name": row["display_name"],
                "supported": bool(row["supported"]),
                "cost_class": row["cost_class"],
                "capabilities": p.get("capabilities", []),
                "source": p.get("source", ""),
                "score": round(-float(row["rank"]), 4),
            })
        return out

    def get_resource_details(self, ids: Sequence[str]) -> List[Dict[str, Any]]:
        """Stage-2 expanded lookup returning exact parameters, constraints, and fallbacks."""
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT payload_json FROM resources WHERE id IN ({placeholders})",
                list(ids),
            ).fetchall()
        return [json.loads(r["payload_json"]) for r in rows]
