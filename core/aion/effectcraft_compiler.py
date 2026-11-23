"""Stage 10: General-Purpose EffectCraft AION Scene Graph Compiler & GPU Renderer.

Uses verified EffectCraft CLI command names (`effect.apply`, `layer.addItem`,
`layer.settings`, `effects/#1/positionsColors/color*`, `keys.select` + `keys.easyEase`,
`file.saveAs`, and `--gpu render`) and parameterizes typography for RTL (Cairo) & LTR (EN).
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.aion.capability_prober import find_effectcraft_cli
from core.aion.contracts import is_ecgc_v2_graph
from core.aion.motion_and_audio import prepare_asset_derivative
from core.config.settings import get_effectcraft_subprocess_env

ROOT_DIR = Path(__file__).resolve().parents[2]
EC_CLI = find_effectcraft_cli() or (ROOT_DIR / "craftApp" / "effectcraft" / "target" / "release" / "effectcraft-cli.exe")


def _hex_to_rgba_float(hex_str: str, alpha: float = 1.0) -> List[float]:
    h = (hex_str or "#141820").lstrip("#")
    return [int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha]


class EffectCraftSceneCompiler:
    """Translates AION `scene_graph.json` -> editable `.ecproj` + hardware GPU MP4."""

    def __init__(self, section_dir: Path, work_dir: Path) -> None:
        self.section_dir = Path(section_dir)
        self.assets_dir = self.section_dir / "assets"
        self.work_dir = Path(work_dir)
        self.derived_dir = self.work_dir / "derived_assets"
        self.derived_dir.mkdir(parents=True, exist_ok=True)

    def build_and_render(
        self,
        scene_graph: Dict[str, Any],
        char_seq_info: Optional[Dict[str, Any]],
        mixed_audio_wav: Path,
        out_ecproj: Path,
        out_mp4: Path,
        use_gpu: bool = True,
        resolution: str = "720p",
    ) -> Dict[str, Any]:
        if is_ecgc_v2_graph(scene_graph):
            from core.aion.ecgc_compiler import CreativeGraphicsCompiler

            return CreativeGraphicsCompiler().compile_scene(
                scene_graph,
                section_dir=self.section_dir,
                work_dir=self.work_dir,
                out_ecproj=out_ecproj,
                out_mp4=out_mp4,
                voice_wav=mixed_audio_wav if mixed_audio_wav and Path(mixed_audio_wav).is_file() else None,
                use_gpu=use_gpu,
                resolution=resolution,
            )

        if not EC_CLI.is_file():
            return {"ok": False, "stage": "preflight", "error": f"effectcraft-cli.exe missing at {EC_CLI}"}

        dur = float(scene_graph["source_timeline"]["duration_sec"])
        fps = int(scene_graph.get("fps", 30))
        comp_name = scene_graph.get("project_id", "AION_Comp")
        default_dir = (scene_graph.get("text_direction") or "rtl").lower()
        default_font = scene_graph.get("font") or ("Cairo" if default_dir == "rtl" else "Segoe UI")
        w, h = 1920, 1080

        cmds: List[Dict[str, Any]] = [
            {"command": "comp.new", "params": {"name": comp_name, "width": w, "height": h, "frameRate": fps, "duration": dur, "background": "#EDE8E0"}},
        ]
        three_d_layers: List[str] = []
        ease_keys: List[Dict[str, Any]] = []

        # 1. Atmospheric Stage Background + 4-Color Gradient + Vignette
        cmds.append({"command": "layer.newSolid", "params": {"name": "BG_Stage", "color": "#EDE8E0", "width": w, "height": h}})
        cmds.append({"command": "effect.apply", "params": {"effect": "4-Color Gradient", "layers": ["BG_Stage"]}})
        cmds.append({"command": "effect.apply", "params": {"effect": "Vignette", "layers": ["BG_Stage"]}})

        bg_moods = scene_graph.get("background_timeline", []) or [
            {"time": 0.0, "c1": "#F2EDE4", "c2": "#EBE4D8", "c3": "#E5DDD0", "c4": "#DDD3C4", "vignette": 14}
        ]
        for m in bg_moods:
            t_m = float(m["time"])
            for idx_c, key_c in enumerate(["c1", "c2", "c3", "c4"], start=1):
                if key_c in m:
                    cmds.append({
                        "command": "prop.addKey",
                        "params": {"layer": "BG_Stage", "path": f"effects/#1/positionsColors/color{idx_c}", "time": t_m, "timeBase": "comp", "value": _hex_to_rgba_float(m[key_c])},
                    })
            if "vignette" in m:
                cmds.append({
                    "command": "prop.addKey",
                    "params": {"layer": "BG_Stage", "path": "effects/#2/amount", "time": t_m, "timeBase": "comp", "value": float(m["vignette"])},
                })

        cmds.append({
            "command": "layer.newShape",
            "params": {"kind": "rect", "name": "Stage_Floor_Line", "size": [3400, 2], "position": [960, 868], "fill": "#9A8F7E", "fillOpacity": 40, "strokeType": "none"},
        })
        three_d_layers.append("Stage_Floor_Line")

        # 2. Import prepared assets once
        imported_items: Dict[str, str] = {}
        scene_layers_plan: List[Tuple[Dict[str, Any], Path, int, int]] = []
        for sc in scene_graph.get("scenes", []):
            sc_st = float(sc.get("time", {}).get("start", 0.0))
            sc_en = float(sc.get("time", {}).get("end", dur))
            sc_id = sc.get("scene_id", "sc")
            for idx_a, a_cfg in enumerate(sc.get("assets", [])):
                a_cfg_copy = dict(a_cfg)
                a_cfg_copy.setdefault("uid", f"{sc_id}_{idx_a}")
                prep_path, pw, ph = prepare_asset_derivative(a_cfg_copy, self.assets_dir, self.derived_dir)
                pos_str = prep_path.resolve().as_posix()
                if pos_str not in imported_items:
                    cmds.append({"command": "file.import", "params": {"paths": [pos_str], "addToComp": False}})
                    imported_items[pos_str] = prep_path.name
                scene_layers_plan.append(({**a_cfg_copy, "_scene_start": sc_st, "_scene_end": sc_en, "_scene_id": sc_id}, prep_path, pw, ph))

        # 3. Timeline Layers & Motion
        for idx_l, (cfg, prep_path, pw, ph) in enumerate(scene_layers_plan):
            lname = f"Asset_{cfg['_scene_id']}_{cfg['id']}_{idx_l}"
            st = float(cfg.get("in", cfg["_scene_start"]))
            en = float(cfg.get("out", cfg["_scene_end"]))
            pos = cfg.get("pos", [1100, 540])
            z = float(cfg.get("z", 0.0))
            if cfg.get("target_h"):
                base_sc = (float(cfg["target_h"]) / max(1, ph)) * 100.0
            elif cfg.get("target_w"):
                base_sc = (float(cfg["target_w"]) / max(1, pw)) * 100.0
            else:
                base_sc = float(cfg.get("scale", 100.0))

            anchor = [pw / 2.0, ph] if cfg.get("grounded", False) else [pw / 2.0, ph / 2.0]
            item_name = imported_items[prep_path.resolve().as_posix()]

            cmds.append({"command": "layer.addItem", "params": {"item": item_name, "position": [pos[0], pos[1]], "in": st, "out": en, "anchor": anchor}})
            cmds.append({"command": "layer.settings", "params": {"layer": "#1", "name": lname}})
            if abs(z) > 0.1:
                cmds.append({"command": "prop.set", "params": {"layer": lname, "path": "transform/position", "value": [pos[0], pos[1], z]}})

            entrance = cfg.get("entrance", "soft_fade")
            ent_dur = float(cfg.get("entrance_dur", 0.38))
            if entrance == "pop_settle":
                cmds.extend([
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": st, "timeBase": "comp", "value": [base_sc * 0.2, base_sc * 0.2, 100]}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": st + ent_dur * 0.68, "timeBase": "comp", "value": [base_sc * 1.07, base_sc * 1.07, 100]}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": st + ent_dur, "timeBase": "comp", "value": [base_sc, base_sc, 100]}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 0.0}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st + 0.16, "timeBase": "comp", "value": 100.0}},
                ])
            elif entrance == "slide_right":
                cmds.extend([
                    {"command": "prop.set", "params": {"layer": lname, "path": "transform/scale", "value": [base_sc, base_sc, 100]}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": st, "timeBase": "comp", "value": [pos[0] + 140, pos[1], z]}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": st + ent_dur, "timeBase": "comp", "value": [pos[0], pos[1], z]}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 0.0}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st + ent_dur * 0.7, "timeBase": "comp", "value": 100.0}},
                ])
                ease_keys.extend([{"layer": lname, "path": "transform/position", "time": st}, {"layer": lname, "path": "transform/position", "time": st + ent_dur}])
            elif entrance == "slide_down":
                cmds.extend([
                    {"command": "prop.set", "params": {"layer": lname, "path": "transform/scale", "value": [base_sc, base_sc, 100]}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": st, "timeBase": "comp", "value": [pos[0], pos[1] - 90, z]}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": st + ent_dur, "timeBase": "comp", "value": [pos[0], pos[1], z]}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 0.0}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st + ent_dur * 0.7, "timeBase": "comp", "value": 100.0}},
                ])
            else:
                cmds.extend([
                    {"command": "prop.set", "params": {"layer": lname, "path": "transform/scale", "value": [base_sc, base_sc, 100]}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 0.0}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": st + ent_dur, "timeBase": "comp", "value": 100.0}},
                ])

            for kf in cfg.get("keyframes", []):
                k_t = float(kf["time"])
                if "pos" in kf:
                    kz = float(kf.get("z", z))
                    cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/position", "time": k_t, "timeBase": "comp", "value": [kf["pos"][0], kf["pos"][1], kz]}})
                    ease_keys.append({"layer": lname, "path": "transform/position", "time": k_t})
                if "scale_mult" in kf:
                    sm = base_sc * float(kf["scale_mult"])
                    cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/scale", "time": k_t, "timeBase": "comp", "value": [sm, sm, 100]}})
                    ease_keys.append({"layer": lname, "path": "transform/scale", "time": k_t})
                if "opacity" in kf:
                    cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": k_t, "timeBase": "comp", "value": float(kf["opacity"])}})

            fade_out = float(cfg.get("fade_out", 0.28))
            if fade_out > 0 and (en - fade_out) > (st + ent_dur):
                cmds.extend([
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": en - fade_out, "timeBase": "comp", "value": 100.0}},
                    {"command": "prop.addKey", "params": {"layer": lname, "path": "transform/opacity", "time": en, "timeBase": "comp", "value": 0.0}},
                ])

            if cfg.get("shadow", True):
                cmds.append({"command": "effect.apply", "params": {"effect": "Drop Shadow", "layers": [lname]}})
                cmds.append({"command": "prop.set", "params": {"layer": lname, "path": "effects/Drop Shadow/opacity", "value": 34.0}})
                cmds.append({"command": "prop.set", "params": {"layer": lname, "path": "effects/Drop Shadow/distance", "value": 8.0}})
                cmds.append({"command": "prop.set", "params": {"layer": lname, "path": "effects/Drop Shadow/softness", "value": 18.0}})

            for fx in cfg.get("effects", []):
                ftype = fx["type"]
                if ftype == "Light Sweep":
                    ft = float(fx.get("time", st + 0.5))
                    fd = float(fx.get("duration", 0.65))
                    cmds.append({"command": "effect.apply", "params": {"effect": "Light Sweep", "layers": [lname]}})
                    cmds.append({"command": "prop.set", "params": {"layer": lname, "path": "effects/Light Sweep/sweepIntensity", "value": float(fx.get("intensity", 28.0))}})
                    cmds.append({"command": "prop.set", "params": {"layer": lname, "path": "effects/Light Sweep/width", "value": float(fx.get("width", 42.0))}})
                    if "color" in fx:
                        cmds.append({"command": "prop.set", "params": {"layer": lname, "path": "effects/Light Sweep/lightColor", "value": _hex_to_rgba_float(fx["color"])}})
                    cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "effects/Light Sweep/center", "time": ft, "timeBase": "comp", "value": [-40.0, ph / 2.0]}})
                    cmds.append({"command": "prop.addKey", "params": {"layer": lname, "path": "effects/Light Sweep/center", "time": ft + fd, "timeBase": "comp", "value": [pw + 40.0, ph / 2.0]}})
                elif ftype == "Radio Waves":
                    cmds.append({"command": "effect.apply", "params": {"effect": "Radio Waves", "layers": [lname]}})
                    cmds.append({"command": "prop.set", "params": {"layer": lname, "path": "effects/Radio Waves/producerPoint", "value": [pw * 0.5, ph * 0.45]}})
                    if "color" in fx:
                        cmds.append({"command": "prop.set", "params": {"layer": lname, "path": "effects/Radio Waves/waveStroke/color", "value": _hex_to_rgba_float(fx["color"])}})
                    if "frequency" in fx:
                        cmds.append({"command": "prop.set", "params": {"layer": lname, "path": "effects/Radio Waves/waveMotion/frequency", "value": float(fx["frequency"])}})
                    if "expansion" in fx:
                        cmds.append({"command": "prop.set", "params": {"layer": lname, "path": "effects/Radio Waves/waveMotion/expansion", "value": float(fx["expansion"])}})
                elif ftype == "Glow":
                    cmds.append({"command": "effect.apply", "params": {"effect": "Glow", "layers": [lname]}})
                    cmds.append({"command": "prop.set", "params": {"layer": lname, "path": "effects/Glow/radius", "value": float(fx.get("radius", 18.0))}})
                    cmds.append({"command": "prop.set", "params": {"layer": lname, "path": "effects/Glow/intensity", "value": float(fx.get("intensity", 0.65))}})

            if cfg.get("three_d", True):
                three_d_layers.append(lname)

        # 4. Procedural Vector Shapes & Trim Connectors
        for idx_s, sh in enumerate(scene_graph.get("procedural_shapes", [])):
            sname = sh.get("name", f"ProcShape_{idx_s}")
            st = float(sh["in"])
            en = float(sh["out"])
            kind = sh["kind"]
            if kind == "path":
                verts_local = [[float(v[0]) - 960.0, float(v[1]) - 540.0] for v in sh["vertices"]]
                cmds.append({"command": "layer.newShape", "params": {"kind": "none", "name": sname}})
                cmds.append({
                    "command": "shape.newPath",
                    "params": {
                        "layer": sname, "vertices": verts_local,
                        "inTangents": sh.get("inTangents", [[0, 0]] * len(verts_local)),
                        "outTangents": sh.get("outTangents", [[0, 0]] * len(verts_local)),
                        "closed": bool(sh.get("closed", False)), "fill": sh.get("fill", False),
                        "fillOpacity": float(sh.get("fillOpacity", 100.0)),
                        "stroke": sh.get("stroke", "#C0262D"), "strokeOpacity": float(sh.get("strokeOpacity", 100.0)),
                        "strokeWidth": float(sh.get("strokeWidth", 5.0)),
                    },
                })
                if sh.get("trim", False):
                    cmds.append({"command": "layer.addShapeItem", "params": {"layer": sname, "kind": "trim"}})
                    tdur = float(sh.get("trim_dur", 0.45))
                    cmds.append({"command": "prop.addKey", "params": {"layer": sname, "path": "contents/trim/end", "time": st, "timeBase": "comp", "value": 0.0}})
                    cmds.append({"command": "prop.addKey", "params": {"layer": sname, "path": "contents/trim/end", "time": st + tdur, "timeBase": "comp", "value": 100.0}})
                    ease_keys.extend([{"layer": sname, "path": "contents/trim/end", "time": st}, {"layer": sname, "path": "contents/trim/end", "time": st + tdur}])
            elif kind == "rounded_panel":
                cmds.append({
                    "command": "layer.newShape",
                    "params": {
                        "kind": "rounded", "name": sname, "size": sh["size"], "position": sh["pos"],
                        "fill": sh.get("fill", "#111827"), "fillOpacity": float(sh.get("fillOpacity", 92.0)),
                        "stroke": sh.get("stroke", "#F59E0B"), "strokeWidth": float(sh.get("strokeWidth", 3.0)),
                    },
                })
            if sh.get("blur"):
                cmds.append({"command": "effect.apply", "params": {"effect": "Gaussian Blur", "layers": [sname]}})
                cmds.append({"command": "prop.set", "params": {"layer": sname, "path": "effects/Gaussian Blur/blurriness", "value": float(sh["blur"])}})

            cmds.append({"command": "layer.timing", "params": {"layers": [sname], "in": st, "out": en}})
            max_op = float(sh.get("opacity", 100.0))
            cmds.append({"command": "prop.addKey", "params": {"layer": sname, "path": "transform/opacity", "time": st, "timeBase": "comp", "value": 0.0}})
            cmds.append({"command": "prop.addKey", "params": {"layer": sname, "path": "transform/opacity", "time": min(en, st + 0.25), "timeBase": "comp", "value": max_op}})
            cmds.append({"command": "prop.addKey", "params": {"layer": sname, "path": "transform/opacity", "time": max(st + 0.25, en - 0.25), "timeBase": "comp", "value": max_op}})
            cmds.append({"command": "prop.addKey", "params": {"layer": sname, "path": "transform/opacity", "time": en, "timeBase": "comp", "value": 0.0}})
            if sh.get("three_d", True):
                three_d_layers.append(sname)

        # 5. Optional Character Sequence Layer
        if char_seq_info and scene_graph.get("use_character", False):
            first_frame_posix = Path(char_seq_info["first_frame"]).resolve().as_posix()
            cmds.append({"command": "file.import", "params": {"paths": [first_frame_posix], "sequence": True, "frameRate": fps, "addToComp": True}})
            cmds.append({"command": "layer.settings", "params": {"layer": "#1", "name": "Host_Character"}})
            cmds.append({"command": "prop.set", "params": {"layer": "Host_Character", "path": "transform/anchor", "value": [320.0, 566.0, 0.0]}})
            for ck in scene_graph.get("character_motion_keys", [{"time": 0.0, "pos": [320, 868, -20], "scale": 122}]):
                kt, cp, cs = float(ck["time"]), ck["pos"], float(ck.get("scale", 122))
                cmds.append({"command": "prop.addKey", "params": {"layer": "Host_Character", "path": "transform/position", "time": kt, "timeBase": "comp", "value": [cp[0], cp[1], cp[2] if len(cp) > 2 else -20]}})
                cmds.append({"command": "prop.addKey", "params": {"layer": "Host_Character", "path": "transform/scale", "time": kt, "timeBase": "comp", "value": [cs, cs, 100]}})
                ease_keys.append({"layer": "Host_Character", "path": "transform/position", "time": kt})
            three_d_layers.append("Host_Character")

        # 6. Typography Overlays (Pill + Native RTL/LTR Text)
        for idx_t, txt_cfg in enumerate(scene_graph.get("typography", [])):
            tname, pname = f"Text_{idx_t}", f"TextPill_{idx_t}"
            st, en = float(txt_cfg["in"]), float(txt_cfg["out"])
            pos, text_val = txt_cfg["pos"], txt_cfg["text"]
            fsize = int(txt_cfg.get("size", 44))
            tdir = (txt_cfg.get("direction") or default_dir).lower()
            tfont = txt_cfg.get("font") or default_font
            bg_hex = txt_cfg.get("pill_bg", "#141820")
            bd_hex = txt_cfg.get("pill_border", "#E5A93C")
            txt_hex = txt_cfg.get("color", "#FFFFFF")

            if txt_cfg.get("pill", True):
                pill_w = int(txt_cfg.get("pill_w", max(320, min(960, len(text_val) * int(fsize * 0.62) + 90))))
                pill_h = int(txt_cfg.get("pill_h", fsize + 44))
                cmds.append({
                    "command": "layer.newShape",
                    "params": {
                        "kind": "rounded", "name": pname, "size": [pill_w, pill_h], "position": [pos[0], pos[1]],
                        "fill": bg_hex, "fillOpacity": float(txt_cfg.get("pill_opacity", 92.0)),
                        "stroke": bd_hex, "strokeWidth": float(txt_cfg.get("border_w", 3.5)),
                    },
                })
                cmds.append({"command": "layer.timing", "params": {"layers": [pname], "in": st, "out": en}})
                cmds.append({"command": "prop.addKey", "params": {"layer": pname, "path": "transform/scale", "time": st, "timeBase": "comp", "value": [60, 60, 100]}})
                cmds.append({"command": "prop.addKey", "params": {"layer": pname, "path": "transform/scale", "time": st + 0.16, "timeBase": "comp", "value": [104, 104, 100]}})
                cmds.append({"command": "prop.addKey", "params": {"layer": pname, "path": "transform/scale", "time": st + 0.26, "timeBase": "comp", "value": [100, 100, 100]}})
                cmds.append({"command": "prop.addKey", "params": {"layer": pname, "path": "transform/opacity", "time": max(st + 0.25, en - 0.22), "timeBase": "comp", "value": 100.0}})
                cmds.append({"command": "prop.addKey", "params": {"layer": pname, "path": "transform/opacity", "time": en, "timeBase": "comp", "value": 0.0}})

            txt_y = pos[1] + int(fsize * 0.30) if txt_cfg.get("pill", True) else pos[1]
            cmds.append({
                "command": "layer.newText",
                "params": {
                    "text": text_val, "name": tname, "font": tfont, "style": "Bold",
                    "size": fsize, "fill": txt_hex, "direction": tdir, "justify": "center",
                    "position": [pos[0], txt_y],
                },
            })
            cmds.append({"command": "layer.timing", "params": {"layers": [tname], "in": st + 0.04, "out": en}})
            cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": st + 0.06, "timeBase": "comp", "value": 0.0}})
            cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": st + 0.24, "timeBase": "comp", "value": 100.0}})
            cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": max(st + 0.3, en - 0.22), "timeBase": "comp", "value": 100.0}})
            cmds.append({"command": "prop.addKey", "params": {"layer": tname, "path": "transform/opacity", "time": en, "timeBase": "comp", "value": 0.0}})

        # 7. 3D Switch & Dynamic Camera
        if three_d_layers:
            cmds.append({"command": "layer.setSwitch", "params": {"layers": three_d_layers, "switch": "threeD", "value": True}})

        cam_cues = scene_graph.get("camera_timeline", [])
        if cam_cues:
            cmds.append({"command": "layer.newCamera", "params": {"name": "MainCam", "type": "twoNode", "zoom": 1800}})
            for ck in cam_cues:
                kt = float(ck["time"])
                cmds.append({"command": "prop.addKey", "params": {"layer": "MainCam", "path": "transform/position", "time": kt, "timeBase": "comp", "value": ck["pos"]}})
                cmds.append({"command": "prop.addKey", "params": {"layer": "MainCam", "path": "transform/poi", "time": kt, "timeBase": "comp", "value": ck.get("poi", [960, 540, 0])}})
                ease_keys.extend([{"layer": "MainCam", "path": "transform/position", "time": kt}, {"layer": "MainCam", "path": "transform/poi", "time": kt}])

        if ease_keys:
            cmds.append({"command": "keys.select", "params": {"keys": ease_keys}})
            cmds.append({"command": "keys.easyEase", "params": {"which": "both"}})

        # 8. Mixed Studio Audio
        if mixed_audio_wav.is_file():
            cmds.append({"command": "file.import", "params": {"paths": [mixed_audio_wav.resolve().as_posix()], "addToComp": True}})

        out_ecproj.parent.mkdir(parents=True, exist_ok=True)
        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        cmds.append({"command": "file.saveAs", "params": {"path": out_ecproj.resolve().as_posix()}})

        cmd_file = self.work_dir / f"{comp_name}_commands.json"
        cmd_file.write_text(json.dumps(cmds, ensure_ascii=False, indent=2), encoding="utf-8")

        t0 = time.time()
        ec_env = get_effectcraft_subprocess_env()
        build_res = subprocess.run([str(EC_CLI), "--empty", "run", "--commands", str(cmd_file), "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ec_env)
        if build_res.returncode != 0:
            return {"ok": False, "stage": "compile", "stderr": build_res.stderr, "stdout": build_res.stdout}

        from core.aion.ecgc_compiler import resolve_effectcraft_resolution

        t_ren = time.time()
        render_cmd = [str(EC_CLI), "--project", str(out_ecproj)]
        if use_gpu:
            render_cmd.append("--gpu")
        render_cmd.extend([
            "render", "--comp", comp_name, "--out", str(out_mp4),
            "--fps", str(fps), "--start", "0", "--end", f"{dur:.3f}",
            "--resolution", resolve_effectcraft_resolution(resolution),
            "--audio", "on", "--bitrate", "14000",
        ])
        render_res = subprocess.run(render_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=ec_env)
        return {
            "ok": render_res.returncode == 0 and out_mp4.is_file(),
            "ecproj": str(out_ecproj),
            "mp4": str(out_mp4),
            "compile_sec": round(time.time() - t0, 2),
            "render_sec": round(time.time() - t_ren, 2),
            "render_stdout": render_res.stdout.strip(),
            "render_stderr": render_res.stderr.strip(),
        }
