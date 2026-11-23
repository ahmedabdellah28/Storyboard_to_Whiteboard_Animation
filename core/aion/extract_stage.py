"""Stage 4: Unified Storyboard Asset Extraction (Grid Valley+PhotoCraft 3x HD & Pure Contour)."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT_DIR = Path(__file__).resolve().parents[2]
PC_CLI = ROOT_DIR / "craftApp" / "photocraft" / "target" / "release" / "photocraft-cli.exe"


def find_photocraft_cli() -> Optional[Path]:
    """Return existing `photocraft-cli.exe` path or None (portable env/bin/craftApp/PATH)."""
    env_p = os.environ.get("PHOTOCRAFT_CLI", "").strip()
    if env_p and Path(env_p).is_file():
        return Path(env_p)
    for cand in (
        ROOT_DIR / "bin" / "photocraft-cli.exe",
        PC_CLI,
    ):
        if cand.is_file():
            return cand
    which_p = shutil.which("photocraft-cli")
    return Path(which_p) if which_p else None


def _find_valley_cuts(profile: np.ndarray, num_bins: int) -> List[int]:
    L = len(profile)
    step = L / float(num_bins)
    cuts = [0]
    win = int(step * 0.24)
    for i in range(1, num_bins):
        nom = int(round(i * step))
        lo = max(cuts[-1] + int(step * 0.45), nom - win)
        hi = min(L - int(step * (num_bins - i) * 0.45), nom + win)
        if hi <= lo:
            cuts.append(nom)
            continue
        sub = profile[lo:hi + 1]
        min_val = float(sub.min())
        quiet = sub <= (min_val + max(2.0, min_val * 0.15))
        best_pos = nom
        best_score = -1.0
        idx = 0
        while idx < len(quiet):
            if quiet[idx]:
                start = idx
                while idx < len(quiet) and quiet[idx]:
                    idx += 1
                mid = (start + idx - 1) * 0.5
                run_len = idx - start
                dist_pen = abs((lo + mid) - nom) * 0.08
                score = run_len - dist_pen
                if score > best_score:
                    best_score = score
                    best_pos = int(round(lo + mid))
            else:
                idx += 1
        cuts.append(best_pos)
    cuts.append(L)
    return cuts


def _flood_fill_white_bg(rgb: np.ndarray, white_thresh: int = 238) -> np.ndarray:
    h, w, _ = rgb.shape
    fg_barrier = np.min(rgb, axis=2) < white_thresh
    fg_barrier = ndimage.binary_closing(fg_barrier, structure=np.ones((3, 3)))
    is_bg_cand = ~fg_barrier

    visited = np.zeros((h, w), dtype=bool)
    q: deque[Tuple[int, int]] = deque()
    for x in range(w):
        if is_bg_cand[0, x]:
            visited[0, x] = True
            q.append((0, x))
        if is_bg_cand[h - 1, x] and not visited[h - 1, x]:
            visited[h - 1, x] = True
            q.append((h - 1, x))
    for y in range(h):
        if is_bg_cand[y, 0] and not visited[y, 0]:
            visited[y, 0] = True
            q.append((y, 0))
        if is_bg_cand[y, w - 1] and not visited[y, w - 1]:
            visited[y, w - 1] = True
            q.append((y, w - 1))

    while q:
        cy, cx = q.popleft()
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_bg_cand[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))

    alpha = np.where(visited, 0, 255).astype(np.uint8)
    ys, xs = np.where(alpha > 0)
    if len(ys) == 0:
        return np.dstack([rgb, alpha])
    return np.dstack([
        rgb[max(0, int(ys.min()) - 3):min(h, int(ys.max()) + 4), max(0, int(xs.min()) - 3):min(w, int(xs.max()) + 4)],
        alpha[max(0, int(ys.min()) - 3):min(h, int(ys.max()) + 4), max(0, int(xs.min()) - 3):min(w, int(xs.max()) + 4)],
    ])


def _run_photocraft_3x_batch(in_dir: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pc_cli = find_photocraft_cli()
    if pc_cli is None or not pc_cli.is_file():
        for png in in_dir.glob("*.png"):
            im = Image.open(png).convert("RGBA")
            im.resize((im.width * 3, im.height * 3), Image.Resampling.LANCZOS).save(out_dir / png.name)
        return
    actions_path = out_dir / "_pc_3x_actions.json"
    actions = [
        {"command": "layer.matting.removeWhiteMatte", "params": {}},
        {"command": "layer.matting.defringe", "params": {"width": 1}},
        {"command": "filter.noise.reduceNoise", "params": {
            "strength": 4, "preserveDetails": 86, "reduceColorNoise": 60,
            "sharpenDetails": 32, "removeJpegArtifact": True,
        }},
        {"command": "image.imageSize", "params": {"percent": 300, "resample": "preserveDetails"}},
        {"command": "filter.sharpen.smartSharpen", "params": {"amount": 85, "radius": 0.9, "reduceNoise": 18}},
    ]
    actions_path.write_text(json.dumps(actions, indent=2), encoding="utf-8")
    res = subprocess.run(
        [str(pc_cli), "batch", "--actions", str(actions_path), "--in", str(in_dir), "--out", str(out_dir), "--format", "png"],
        capture_output=True, text=True,
    )
    actions_path.unlink(missing_ok=True)
    if res.returncode != 0:
        raise RuntimeError(f"PhotoCraft batch failed for {in_dir}: {res.stderr}")


def _cleanup_hd_png(png_path: Path) -> None:
    im = Image.open(png_path).convert("RGBA")
    arr = np.array(im)
    lbl, n = ndimage.label(arr[:, :, 3] > 18)
    if n <= 1:
        return
    counts = np.bincount(lbl.ravel())
    counts[0] = 0
    max_area = counts.max()
    keep = np.ones(n + 1, dtype=bool)
    keep[0] = False
    edge_ids = set(np.unique(np.concatenate([
        lbl[:5, :].ravel(), lbl[-5:, :].ravel(),
        lbl[:, :5].ravel(), lbl[:, -5:].ravel(),
    ])))
    for cid in range(1, n + 1):
        if counts[cid] < 60:
            keep[cid] = False
    for cid in edge_ids:
        if cid > 0 and counts[cid] < max_area * 0.12:
            keep[cid] = False
    if not np.all(keep[lbl] | (lbl == 0)):
        arr[:, :, 3] = np.where(keep[lbl], arr[:, :, 3], 0)
        ys, xs = np.where(arr[:, :, 3] > 0)
        if len(ys) > 0:
            arr = arr[max(0, int(ys.min()) - 4):int(ys.max()) + 5, max(0, int(xs.min()) - 4):int(xs.max()) + 5]
        Image.fromarray(arr, "RGBA").save(png_path)


def _build_contact_sheet(asset_paths: List[Path], out_path: Path, cols: int, title: str) -> None:
    rows = max(1, (len(asset_paths) + cols - 1) // cols)
    cw, ch = 300, 240
    canvas = Image.new("RGBA", (cols * cw, 44 + rows * ch), (22, 30, 44, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 12), title, fill=(130, 220, 255, 255))
    for i, p in enumerate(asset_paths):
        r, c = i // cols, i % cols
        x0, y0 = c * cw, 44 + r * ch
        draw.rectangle((x0 + 4, y0 + 4, x0 + cw - 4, y0 + ch - 4), fill=(36, 46, 64, 255), outline=(72, 95, 130, 255))
        im = Image.open(p).convert("RGBA")
        orig_sz = im.size
        im.thumbnail((cw - 24, ch - 44), Image.Resampling.LANCZOS)
        canvas.alpha_composite(im, (x0 + (cw - im.width) // 2, y0 + 30 + (ch - 36 - im.height) // 2))
        draw.rectangle((x0 + 6, y0 + 6, x0 + cw - 6, y0 + 28), fill=(18, 25, 38, 255))
        draw.text((x0 + 12, y0 + 11), f"{p.stem} ({orig_sz[0]}x{orig_sz[1]})", fill=(235, 244, 255, 255))
    canvas.convert("RGB").save(out_path)


def extract_grid_storyboard(
    sb_path: Path,
    out_dir: Path,
    rows: int = 4,
    cols: int = 5,
    prefix: str = "entity",
    title: Optional[str] = None,
) -> Dict[str, Any]:
    raw_dir = out_dir / "_raw_tmp"
    shutil.rmtree(raw_dir, ignore_errors=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    rgb = np.array(Image.open(sb_path).convert("RGB"))
    ink = (np.min(rgb, axis=2) < 238).astype(np.float32)
    y_cuts = _find_valley_cuts(ink.sum(axis=1), rows)

    records: List[Dict[str, Any]] = []
    idx = 1
    for r in range(rows):
        y0, y1 = y_cuts[r], y_cuts[r + 1]
        x_cuts = _find_valley_cuts(ink[y0:y1, :].sum(axis=0), cols)
        for c in range(cols):
            x0, x1 = x_cuts[c], x_cuts[c + 1]
            rgba = _flood_fill_white_bg(rgb[y0:y1, x0:x1], white_thresh=238)
            lbl, n = ndimage.label(rgba[:, :, 3] > 0)
            if n > 1:
                counts = np.bincount(lbl.ravel())
                counts[0] = 0
                max_area = counts.max()
                keep = np.ones(n + 1, dtype=bool)
                keep[0] = False
                edge_ids = set(np.unique(np.concatenate([
                    lbl[:5, :].ravel(), lbl[-5:, :].ravel(),
                    lbl[:, :5].ravel(), lbl[:, -5:].ravel(),
                ])))
                for cid in edge_ids:
                    if cid > 0 and counts[cid] < max_area * 0.08:
                        keep[cid] = False
                for cid in range(1, n + 1):
                    if counts[cid] < 6:
                        keep[cid] = False
                rgba[:, :, 3] = np.where(keep[lbl], rgba[:, :, 3], 0)
                ys, xs = np.where(rgba[:, :, 3] > 0)
                if len(ys) > 0:
                    rgba = rgba[max(0, int(ys.min()) - 2):int(ys.max()) + 3, max(0, int(xs.min()) - 2):int(xs.max()) + 3]

            fname = f"{prefix}_{idx:02d}.png"
            Image.fromarray(rgba, "RGBA").save(raw_dir / fname)
            records.append({
                "index": idx,
                "asset_key": f"{prefix}_{idx:02d}",
                "file": fname,
                "row": r + 1,
                "col": c + 1,
                "cell_box": [int(x0), int(y0), int(x1), int(y1)],
                "raw_size": [int(rgba.shape[1]), int(rgba.shape[0])],
            })
            idx += 1

    for old_p in out_dir.glob(f"{prefix}_*.png"):
        old_p.unlink()

    _run_photocraft_3x_batch(raw_dir, out_dir)
    shutil.rmtree(raw_dir, ignore_errors=True)

    hd_paths: List[Path] = []
    metadata: Dict[str, Any] = {}
    for rec in records:
        hp = out_dir / rec["file"]
        _cleanup_hd_png(hp)
        with Image.open(hp) as im:
            rec["hd_size"] = [im.width, im.height]
        metadata[rec["asset_key"]] = rec
        hd_paths.append(hp)

    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    _build_contact_sheet(hd_paths, out_dir / "contact_sheet.png", cols=cols, title=title or f"{sb_path.stem.upper()} — {len(records)} ASSETS")
    return {"assets_count": len(records), "metadata": str(out_dir / "metadata.json"), "contact_sheet": str(out_dir / "contact_sheet.png")}


def run_extract_stage(
    sec_dir: Path,
    storyboard_path: Path,
    mode: str = "grid",
    rows: int = 4,
    cols: int = 5,
) -> Any:
    """Unified extractor honoring per-section custom scripts, `grid` (PhotoCraft 3x), or `contour`."""
    custom = sec_dir / "extract_assets.py"
    if custom.is_file():
        spec = importlib.util.spec_from_file_location("sec_custom_extractor", str(custom))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "run_extraction"):
            return mod.run_extraction()

    out_dir = sec_dir / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    if mode == "grid":
        return extract_grid_storyboard(storyboard_path, out_dir, rows=rows, cols=cols)

    from core_engine.universal_craft_extractor import UniversalCraftExtractor
    return UniversalCraftExtractor.extract_storyboard(storyboard_path=storyboard_path, output_dir=out_dir)


def import_extracted_assets_zip(proj_dir: Path, zip_path: Path) -> Dict[str, Any]:
    """Import pre-extracted storyboard asset folders + manifest.json from a ZIP archive into project sections."""
    import io
    import zipfile

    proj_dir = Path(proj_dir)
    zip_path = Path(zip_path)
    if not zip_path.is_file():
        raise FileNotFoundError(f"Asset ZIP not found: {zip_path}")

    cat_out = proj_dir / "inputs" / "storyboard_catalog"
    cat_out.mkdir(parents=True, exist_ok=True)
    ar_cat = ROOT_DIR / "cache" / "storyboard_catalog_8"

    sec_map = {
        "001_ganzfeld_badge.png": ("section_01", "01_ganzfeld.json"),
        "001_choice_blindness_badge.png": ("section_02", "02_choice_blindness.json"),
        "001_pinocchio_illusion_badge.png": ("section_03", "03_pinocchio.json"),
        "001_bridge_effect_badge.png": ("section_04", "04_suspension_bridge.json"),
        "001_chronostasis_badge.png": ("section_05", "05_chronostasis.json"),
        "001_jamais_vu_badge.png": ("section_06", "06_jamais_vu.json"),
        "001_verbal_shadow_badge.png": ("section_07", "07_verbal_overshadowing.json"),
        "001_masked_lightbulb.png": ("section_08", "08_cryptomnesia.json"),
    }

    imported_sections: List[Dict[str, Any]] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        # 0. Import any custom illustrated BACKGROUNDS/*.png and background/script docs if present
        bg_out = proj_dir / "inputs" / "backgrounds"
        bg_out.mkdir(parents=True, exist_ok=True)
        imported_bgs: Dict[str, str] = {}
        for zname in sorted(zf.namelist()):
            low = zname.lower()
            if "/backgrounds/" in low and low.endswith(".png") and "/ankara_production/" in low or (low.endswith(".png") and "/backgrounds/" in low):
                fname = Path(zname).name
                if fname not in imported_bgs:
                    dst_bg = bg_out / fname
                    dst_bg.write_bytes(zf.read(zname))
                    imported_bgs[fname] = str(dst_bg.resolve())
            elif low.endswith("scene_backgrounds.json") or low.endswith("workflow.json"):
                (bg_out / Path(zname).name).write_bytes(zf.read(zname))

        mfs = sorted(n for n in zf.namelist() if n.endswith("manifest.json"))
        sec_jsons = sorted(n for n in zf.namelist() if n.endswith("/SECTION.json"))

        if mfs:
            for idx_m, mf_name in enumerate(mfs, 1):
                folder = mf_name.rsplit("/", 1)[0]
                mdata = json.loads(zf.read(mf_name).decode("utf-8"))
                assets_list = mdata.get("assets", [])
                if not assets_list:
                    continue
                first_fn = assets_list[0].get("filename", "")
                sec_id, cat_fn = sec_map.get(first_fn, (f"section_{idx_m:02d}", f"{idx_m:02d}_section.json"))

                ar_data = json.loads((ar_cat / cat_fn).read_text(encoding="utf-8")) if (ar_cat / cat_fn).is_file() else {"assets": []}
                ar_by_idx = {int(a.get("index", i + 1)): a for i, a in enumerate(ar_data.get("assets", []))}

                adir = proj_dir / "sections" / sec_id / "assets"
                raw_dir = adir / "_raw_zip"
                raw_dir.mkdir(parents=True, exist_ok=True)
                records: List[Dict[str, Any]] = []
                catalog_assets: List[Dict[str, Any]] = []

                raw_samples: List[Tuple[int, str, np.ndarray]] = []
                sum_r, sum_b = 0.0, 0.0
                for item in assets_list:
                    idx = int(item["id"])
                    fname = f"entity_{idx:02d}.png"
                    png_bytes = zf.read(f"{folder}/{item['filename']}")
                    with Image.open(io.BytesIO(png_bytes)) as im_in:
                        arr = np.array(im_in.convert("RGBA"))
                    fg = arr[:, :, 3] > 96
                    if np.any(fg):
                        sum_r += float(arr[:, :, 0][fg].mean())
                        sum_b += float(arr[:, :, 2][fg].mean())
                    raw_samples.append((idx, fname, arr))

                swap_rb = sum_b > (sum_r * 1.10)
                for (idx, fname, arr), item in zip(raw_samples, assets_list):
                    if swap_rb:
                        arr = arr[:, :, [2, 1, 0, 3]]
                    eid = f"entity_{idx:02d}"
                    rh, rw = arr.shape[:2]
                    Image.fromarray(arr, "RGBA").save(raw_dir / fname, format="PNG")

                    ar_item = ar_by_idx.get(idx, {})
                    role = ar_item.get("narrative_role", "illustrative_prop")
                    pos = item.get("original_position", {})
                    desc_en = str(item.get("description", eid))
                    desc_ar = str(ar_item.get("description_ar", desc_en))
                    records.append({
                        "index": idx,
                        "asset_key": eid,
                        "file": fname,
                        "original_filename": item["filename"],
                        "description": desc_en,
                        "name_ar": desc_en,
                        "description_ar": f"{desc_en} | {desc_ar}",
                        "narrative_role": role,
                        "rb_channel_fixed": swap_rb,
                        "row": int(pos.get("row", (idx - 1) // 5 + 1)),
                        "col": int(pos.get("column", (idx - 1) % 5 + 1)),
                        "cell_box": item.get("bounding_box", [0, 0, rw, rh]),
                        "raw_size": [rw, rh],
                    })
                    catalog_assets.append({
                        "index": idx,
                        "id": eid,
                        "filename": item["filename"],
                        "name_en": desc_en,
                        "name_ar": desc_en,
                        "description_en": desc_en,
                        "description_ar": f"{desc_en} | {desc_ar}",
                        "narrative_role": role,
                        "row": int(pos.get("row", (idx - 1) // 5 + 1)),
                        "col": int(pos.get("column", (idx - 1) % 5 + 1)),
                    })

                _run_photocraft_3x_batch(raw_dir, adir)
                shutil.rmtree(raw_dir, ignore_errors=True)

                hd_paths: List[Path] = []
                metadata: Dict[str, Any] = {}
                for rec in records:
                    hp = adir / rec["file"]
                    _cleanup_hd_png(hp)
                    with Image.open(hp) as im_hd:
                        rec["hd_size"] = [im_hd.width, im_hd.height]
                    metadata[rec["asset_key"]] = rec
                    hd_paths.append(hp)

                (adir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
                (adir / "manifest_extracted.json").write_text(json.dumps(mdata, indent=2, ensure_ascii=False), encoding="utf-8")
                _build_contact_sheet(hd_paths, adir / "contact_sheet.png", cols=5, title=f"{sec_id.upper()} — {len(records)} ASSETS")
                (cat_out / cat_fn).write_text(
                    json.dumps({"section_id": sec_id, "source_filename": mdata.get("source_filename"), "assets": catalog_assets}, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                imported_sections.append({"section_id": sec_id, "assets_count": len(records), "catalog": str(cat_out / cat_fn)})

        elif sec_jsons:
            # Support structured `SECTION_XX/SECTION.json` production packages (e.g. `ANKARA_PRODUCTION`)
            for idx_s, sj_name in enumerate(sec_jsons, 1):
                folder = sj_name.rsplit("/", 1)[0]
                sdata = json.loads(zf.read(sj_name).decode("utf-8"))
                raw_sec = str(sdata.get("section_id") or f"SECTION_{idx_s:02d}").lower()
                sec_id = raw_sec if raw_sec.startswith("section_") else f"section_{idx_s:02d}"
                sec_num = sec_id.replace("section_", "").zfill(2)
                cat_fn = f"{sec_num}_section.json"

                adir = proj_dir / "sections" / sec_id / "assets"
                raw_dir = adir / "_raw_zip"
                raw_dir.mkdir(parents=True, exist_ok=True)

                flat_assets: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
                for sc in sdata.get("scenes", []):
                    for a in sc.get("assets", []):
                        flat_assets.append((sc, a))
                flat_assets.sort(key=lambda pair: int(pair[1].get("number", 999)))

                records = []
                catalog_assets = []
                for sc, item in flat_assets:
                    idx = int(item["number"])
                    fname = f"entity_{idx:02d}.png"
                    rel_fn = Path(str(item["file"])).name
                    png_bytes = zf.read(f"{folder}/{rel_fn}")
                    with Image.open(io.BytesIO(png_bytes)) as im_in:
                        arr = np.array(im_in.convert("RGBA"))
                    rh, rw = arr.shape[:2]
                    Image.fromarray(arr, "RGBA").save(raw_dir / fname, format="PNG")

                    eid = f"entity_{idx:02d}"
                    title_en = str(item.get("title_en") or eid)
                    desc_en = str(item.get("description_en") or title_en)
                    label_ar = str(item.get("label_ar") or "").strip()
                    cue_ar = str(sc.get("entry_cue_ar") or "").strip()
                    nar_ar = str(sc.get("narration_fragment_ar") or "").strip()
                    desc_ar = f"{title_en} ({label_ar or cue_ar}) — {desc_en}".strip()
                    records.append({
                        "index": idx,
                        "asset_key": eid,
                        "file": fname,
                        "original_filename": rel_fn,
                        "description": desc_en,
                        "name_ar": label_ar or title_en,
                        "description_ar": desc_ar,
                        "narration_fragment_ar": nar_ar,
                        "entry_cue_ar": cue_ar,
                        "background_id": sc.get("background_id"),
                        "background_file": Path(str(sc.get("background_file", ""))).name if sc.get("background_file") else None,
                        "grounded": bool(item.get("grounded", False)),
                        "stage_x_px": item.get("stage_x_px"),
                        "stage_baseline_y_px": item.get("stage_baseline_y_px"),
                        "narrative_role": "hero" if idx == 1 else "illustrative_prop",
                        "row": (idx - 1) // 5 + 1,
                        "col": (idx - 1) % 5 + 1,
                        "raw_size": [rw, rh],
                    })
                    catalog_assets.append({
                        "index": idx,
                        "id": eid,
                        "filename": rel_fn,
                        "name_en": title_en,
                        "name_ar": label_ar or cue_ar or title_en,
                        "description_en": desc_en,
                        "description_ar": desc_ar,
                        "grounded": bool(item.get("grounded", False)),
                        "background_id": sc.get("background_id"),
                        "entry_cue_ar": cue_ar,
                        "narration_fragment_ar": nar_ar,
                        "narrative_role": "hero" if idx == 1 else "illustrative_prop",
                        "row": (idx - 1) // 5 + 1,
                        "col": (idx - 1) % 5 + 1,
                    })

                _run_photocraft_3x_batch(raw_dir, adir)
                shutil.rmtree(raw_dir, ignore_errors=True)

                hd_paths = []
                metadata = {}
                for rec in records:
                    hp = adir / rec["file"]
                    with Image.open(hp) as im_hd:
                        rec["hd_size"] = [im_hd.width, im_hd.height]
                    metadata[rec["asset_key"]] = rec
                    hd_paths.append(hp)

                (adir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
                (adir / "section_plan.json").write_text(json.dumps(sdata, indent=2, ensure_ascii=False), encoding="utf-8")
                _build_contact_sheet(hd_paths, adir / "contact_sheet.png", cols=5, title=f"{sec_id.upper()} — {len(records)} ASSETS")
                (cat_out / cat_fn).write_text(
                    json.dumps({"section_id": sec_id, "title_ar": sdata.get("title_ar"), "assets": catalog_assets}, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                imported_sections.append({"section_id": sec_id, "assets_count": len(records), "catalog": str(cat_out / cat_fn), "backgrounds": len(imported_bgs)})

    imported_sections.sort(key=lambda x: x["section_id"])
    return {"ok": True, "sections_imported": len(imported_sections), "backgrounds_imported": len(imported_bgs), "sections": imported_sections}
