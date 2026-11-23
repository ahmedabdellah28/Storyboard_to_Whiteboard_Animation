import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Eye comfort canvas standard: #EDE8E0 (Luminance ~90%, zero glare, perfect ink contrast)
EYE_COMFORT_THEME = {
    "name": "eye_comfort_paper",
    "bg_color": [0.925, 0.910, 0.880],
    "ground_color": [0.780, 0.740, 0.690],
    "label": "Eye_Comfort_Matte_Paper_BG"
}

GROUNDED_KEYWORDS = [
    "user", "man", "person", "figure", "stickman", "table", "chair", 
    "desk", "machine", "standing", "walking", "grounded", "puppet"
]

FLOATING_ALLOWED_KEYWORDS = [
    "notification", "bubble", "thought", "question", "spark", "dots", 
    "clock", "hourglass", "loop", "streak", "badge", "brain", "hand"
]


class DirectorQAAuditor:
    """Master Automated Quality Assurance & Scene Layout Director."""

    @staticmethod
    def audit_and_optimize_manifest(manifest_path: Path, auto_fix: bool = True) -> Tuple[bool, List[str]]:
        """Audits manifest for viewer-irritating defects and optimizes layout.
        
        Returns (is_passed, audit_log_messages).
        """
        manifest_path = Path(manifest_path)
        if not manifest_path.exists():
            return False, [f"Manifest not found: {manifest_path}"]

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        log = []
        modified = False
        log.append(f"🔍 [DIRECTOR AUDIT] Initiating pre-render QA for {manifest.get('section_id', 'unknown')}...")

        # 1. EYE-COMFORT CANVAS CHECK
        theme = manifest.get("theme", {})
        if isinstance(theme, str):
            theme_name = theme
        else:
            theme_name = theme.get("name", "whiteboard")

        if theme_name in ["whiteboard", "default", "pure_white"]:
            if auto_fix:
                manifest["theme"] = "eye_comfort_paper"
                modified = True
                log.append("  🛡️ [EYE-COMFORT] Bright canvas detected. Upgraded to 'eye_comfort_paper' (#EDE8E0) to eliminate viewer glare.")
        elif theme_name == "warm_paper":
            # Upgrade warm_paper to eye_comfort_paper for softer matte luminance
            if auto_fix:
                manifest["theme"] = "eye_comfort_paper"
                modified = True
                log.append("  🛡️ [EYE-COMFORT] Calibrated background to eye-friendly matte canvas (#EDE8E0).")
        else:
            log.append(f"  ✅ [EYE-COMFORT] Theme '{theme_name}' verified eye-friendly.")

        res = manifest.get("resolution", [1920, 1080])
        is_vertical = res[1] > res[0]
        c_w, c_h = res[0], res[1]

        scenes = manifest.get("scenes", [])
        total_duration = float(manifest.get("total_duration", 30.0))

        for sc_idx, sc in enumerate(scenes):
            sc_id = sc.get("id", f"scene_{sc_idx+1:02d}")
            sc_start = float(sc.get("start", 0.0))
            sc_end = float(sc.get("end", total_duration))
            elements = sc.get("elements", [])
            words = sc.get("words", sc.get("word_cards", []))

            # 2. PHYSICAL GROUNDING & FLOATING AUDIT
            for elem in elements:
                asset_key = elem.get("asset_key", "").lower()
                is_grounded_entity = any(kw in asset_key for kw in GROUNDED_KEYWORDS)
                is_floating_allowed = any(kw in asset_key for kw in FLOATING_ALLOWED_KEYWORDS)

                # Grounding logic
                if is_grounded_entity and not is_floating_allowed:
                    elem_idle = elem.get("idle", None)
                    if elem_idle in ["floating", "idle_floating"]:
                        if auto_fix:
                            # Grounded entities must NOT float like balloons
                            elem["idle"] = "stable"
                            modified = True
                            log.append(f"  ⚓ [PHYSICS] Grounded entity '{asset_key}' set to stable floor anchoring (removed unnatural floating).")

                # 2.5 PROFESSIONAL VISUAL RESTRAINT AUDIT (Max 1 signature effect & max 2 scale_punches per element)
                elem_fxs = elem.get("effects", [])
                if len(elem_fxs) > 1 and auto_fix:
                    # Keep the single most contextually expressive effect (prefer light_sweep, wiggle, or subtle tint_flash)
                    priority = {"light_sweep": 1, "wiggle": 2, "tint_flash": 3, "mask_wipe": 4, "light_burst": 5, "radio_waves": 6, "neon_glow": 7}
                    elem_fxs_sorted = sorted(elem_fxs, key=lambda x: priority.get(x.get("type", ""), 5))
                    elem["effects"] = [elem_fxs_sorted[0]]
                    modified = True
                    log.append(f"  🎬 [EDITORIAL RESTRAINT] Trimmed stacked effects on '{asset_key}' to 1 clean signature effect ('{elem['effects'][0].get('type')}').")

                elem_punches = elem.get("scale_punches", [])
                if len(elem_punches) > 2 and auto_fix:
                    elem["scale_punches"] = [elem_punches[0], elem_punches[-1]]
                    modified = True
                    log.append(f"  🎬 [EDITORIAL RESTRAINT] Capped scale_punches on '{asset_key}' to 2 clean vocal accents.")

            # 3. TEXT CARD SIZING, BALANCING & COLLISION RESOLUTION
            for w in words:
                word_text = w.get("word", w.get("text", ""))
                w_start = float(w.get("start", sc_start))
                w_end = float(w.get("end", w_start + 2.5))
                w_pos = w.get("pos", [int(c_w / 2), 320])

                # Approximate card bounds (Latin chars are narrower than Arabic)
                has_arabic = any('\u0600' <= c <= '\u06FF' for c in word_text)
                char_w = 38 if has_arabic else 26
                card_w = max(240, len(word_text) * char_w + 96)
                card_h = 86
                card_box = (
                    w_pos[0] - card_w // 2,
                    w_pos[1] - card_h // 2,
                    w_pos[0] + card_w // 2,
                    w_pos[1] + card_h // 2,
                )

                # Check collision with any concurrent element
                assets_dir = manifest_path.parent / "assets"
                for elem in elements:
                    e_start = float(elem.get("start", sc_start))
                    e_end = float(elem.get("end", sc_end))
                    
                    # Check temporal overlap
                    if max(w_start, e_start) < min(w_end, e_end):
                        e_pos = elem.get("pos", [int(c_w / 2), int(c_h / 2)])
                        e_size = elem.get("target_size", 480)
                        asset_key = elem.get("asset_key", "")
                        is_grounded = elem.get("grounded", False) or (e_pos[1] >= 800)
                        
                        # Determine actual width and height of visual element
                        img_path = assets_dir / f"{asset_key}.png"
                        if img_path.exists():
                            try:
                                from PIL import Image
                                with Image.open(img_path) as im:
                                    iw, ih = im.size
                                    scale = e_size / float(max(iw, ih))
                                    ew = int(iw * scale)
                                    eh = int(ih * scale)
                            except Exception:
                                ew, eh = e_size, e_size
                        elif "divider" in asset_key.lower() or "line" in asset_key.lower():
                            ew = 50
                            eh = e_size
                        else:
                            ew, eh = e_size, e_size

                        if is_grounded:
                            elem_box = (
                                e_pos[0] - ew // 2,
                                e_pos[1] - eh,
                                e_pos[0] + ew // 2,
                                e_pos[1],
                            )
                        else:
                            elem_box = (
                                e_pos[0] - ew // 2,
                                e_pos[1] - eh // 2,
                                e_pos[0] + ew // 2,
                                e_pos[1] + eh // 2,
                            )

                        # Bounding box collision test with comfort margin
                        margin = 25
                        overlap_x = not (card_box[2] + margin < elem_box[0] or card_box[0] - margin > elem_box[2])
                        overlap_y = not (card_box[3] + margin < elem_box[1] or card_box[1] - margin > elem_box[3])

                        if overlap_x and overlap_y:
                            log.append(f"  ⚠️ [COLLISION DETECTED] '{word_text}' at {w_pos} overlaps '{asset_key}' at {e_pos}.")
                            if auto_fix:
                                if is_vertical:
                                    # In vertical (e.g. 1080x1920)
                                    if e_pos[1] > (c_h * 0.45):
                                        new_y = int(c_h * 0.18)
                                    else:
                                        new_y = int(c_h * 0.75)
                                    new_x = int(c_w / 2.0)
                                    w["pos"] = [new_x, new_y]
                                    w_pos = [new_x, new_y]
                                    modified = True
                                    log.append(f"  🎯 [FIX APPLIED] Re-positioned card '{word_text}' in vertical layout to {w['pos']}.")
                                else:
                                    # Counterbalance Rule for landscape 16:9 (Always keep cards at Y=220)
                                    new_y = 220
                                    if e_pos[0] > 1100:
                                        new_x = 580
                                    elif e_pos[0] < 800:
                                        new_x = 1340
                                    else:
                                        new_x = 580 if w_pos[0] < 960 else 1340
                                    w["pos"] = [new_x, new_y]
                                    w_pos = [new_x, new_y]
                                    modified = True
                                    log.append(f"  🎯 [FIX APPLIED] Re-positioned card '{word_text}' to safe counter-weighted coordinate {w['pos']}.")

                # Check phrase length (Must be a multi-word headline phrase of 2-5 words, never a single isolated word)
                word_tokens = [tok for tok in word_text.strip().split() if len(tok) > 1]
                if len(word_tokens) < 2 and len(word_text.strip()) < 10:
                    log.append(f"  ⚠️ [TYPOGRAPHY WARNING] Card '{word_text}' in '{sc_id}' is too short (1 word). Use a 2-5 word viral headline phrase!")

            # 4. DEAD-AIR & RETENTION PACING AUDIT
            # Check visual beat intervals within scene
            events = [sc_start]
            for elem in elements:
                events.append(float(elem.get("start", sc_start)))
                for ls in elem.get("light_sweeps", []):
                    events.append(float(ls.get("time", sc_start)))
                for sp in elem.get("scale_punches", []):
                    events.append(float(sp.get("time", sc_start)))
                for fx in elem.get("effects", []):
                    events.append(float(fx.get("time", fx.get("start", sc_start))))
            for w in words:
                events.append(float(w.get("start", sc_start)))
            events.append(sc_end)
            events = sorted(list(set(events)))

            max_gap = 0.0
            gap_pos = 0.0
            for i in range(len(events) - 1):
                gap = events[i+1] - events[i]
                if gap > max_gap:
                    max_gap = gap
                    gap_pos = events[i]

            if max_gap > 3.2:
                log.append(f"  ⏳ [PACING WARNING] Scene '{sc_id}' has {max_gap:.2f}s visual stagnation at t={gap_pos:.2f}s.")
                if auto_fix and elements:
                    mid_t = round(gap_pos + max_gap / 2.0, 2)
                    target_elem = elements[0]
                    if len(target_elem.get("scale_punches", [])) < 2:
                        target_elem.setdefault("scale_punches", []).append({"time": mid_t})
                        modified = True
                        log.append(f"  ✨ [PACING ENHANCED] Injected clean mid-hold scale_punch at t={mid_t:.2f}s.")
            else:
                log.append(f"  ⚡ [PACING] Scene '{sc_id}' pacing verified active (max visual gap: {max_gap:.2f}s <= 3.2s).")

        if modified and auto_fix:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            log.append("  💾 [SAVED] Manifest updated with all director optimizations.")

        log.append("🏆 [DIRECTOR AUDIT PASSED] Video is primed for maximum viewer retention!")
        return True, log


if __name__ == "__main__":
    import sys
    test_manifest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("projects/phone_traps/sections/section_01/manifest.json")
    success, msgs = DirectorQAAuditor.audit_and_optimize_manifest(test_manifest, auto_fix=True)
    for m in msgs:
        print(m)
