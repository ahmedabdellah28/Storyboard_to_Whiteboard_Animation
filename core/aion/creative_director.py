"""Model-Agnostic AI Creative Director & Audio-Visual Choreography (Phase 4 & 5 V5).

Builds Creative Scene Graph V2 plans (`aion.scene_graph.v2`) by combining narrative
grammar (`MotionDesignGrammarEngine`), vector/diagram synthesis (`ProceduralGraphicsEngine`),
2.5D staging & lighting (`CinematicCompositionEngine`), and audio-visual anchor
choreography — without locking to any single LLM backend.
"""
from __future__ import annotations

import copy
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

from core.aion.cinematic_composition import (
    CinematicCompositionEngine,
    DEPTH_PLANES_Z,
)
from core.aion.contracts import SCENE_GRAPH_V2, sync_scene_graph_v2_views
from core.aion.motion_grammar import MotionDesignGrammarEngine, PALETTES
from core.aion.procedural_graphics import ProceduralGraphicsEngine
from core.aion.semantic_storyboard_director import (
    plan_semantic_section_allocation,
    synthesize_editorial_headline,
)
from core.aion.typography_director import (
    plan_headline_treatment,
    select_project_typography_system,
)


class DirectorModelBackend(Protocol):
    """Pluggable LLM or heuristic creative planning backend interface."""

    def propose_treatment(self, brief: Dict[str, Any], capabilities: Dict[str, Any]) -> Dict[str, Any]:
        ...


class AICreativeDirector:
    """High-level visual thinker: brief + timing + assets -> Scene Graph V2 -> QA refine loop."""

    def __init__(
        self,
        *,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        model_backend: Optional[DirectorModelBackend] = None,
    ):
        self.width = int(width)
        self.height = int(height)
        self.fps = int(fps)
        self.grammar = MotionDesignGrammarEngine()
        self.proc = ProceduralGraphicsEngine(self.width, self.height)
        self.comp = CinematicCompositionEngine(self.width, self.height, safe_margin_px=96)
        self.model_backend = model_backend

    def direct_scene(
        self,
        brief: Dict[str, Any],
        *,
        capabilities: Optional[Dict[str, Any]] = None,
        external_plan_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate a complete `aion.scene_graph.v2` ready for ECGC compilation."""
        if external_plan_fn is not None:
            proposed = external_plan_fn(brief)
            if isinstance(proposed, dict) and proposed.get("schema_version") == SCENE_GRAPH_V2:
                return proposed
        if self.model_backend is not None:
            proposed = self.model_backend.propose_treatment(brief, capabilities or {})
            if isinstance(proposed, dict) and proposed.get("schema_version") == SCENE_GRAPH_V2:
                return proposed

        video_format = str(brief.get("video_format") or "legacy").strip().lower()
        if video_format in ("educational", "narrative", "auto", "auto_master"):
            from core.aion.master_cinema_kit import build_master_format_section

            return build_master_format_section(
                brief,
                video_format="auto" if video_format == "auto_master" else video_format,
                width=self.width,
                height=self.height,
                fps=int(brief.get("fps") or self.fps),
            )

        style_mode = str(brief.get("style_mode", "auto")).lower()
        section_id = str(brief.get("section_id") or brief.get("project_id") or "studio_v5_scene")
        fps = int(brief.get("fps") or self.fps)
        dur = max(1.5, float(brief.get("duration_sec", 6.0)))
        audio_file = str(brief.get("audio_file", ""))
        beats = brief.get("beats") or [
            {"id": "beat_01", "start": 0.0, "end": dur, "text": str(brief.get("text", "العقل البشري يبني الواقع"))}
        ]

        palette_name = brief.get("palette")
        if not palette_name:
            if style_mode == "scientific_explanation":
                palette_name = "scientific_obsidian"
            elif style_mode == "cinematic_2_5d":
                palette_name = "cinematic_amber_noir"
            elif style_mode == "editorial_motion_graphics":
                palette_name = "deep_studio_slate"
        planned_beats = self.grammar.plan_section_grammar(beats, palette_override=palette_name)
        lead_treatment = planned_beats[0]["treatment"]
        palette = dict(lead_treatment["palette"])

        asset_refs: List[Dict[str, Any]] = []
        proc_graphics: List[Dict[str, Any]] = []
        motion_paths: List[Dict[str, Any]] = []
        typo_blocks: List[Dict[str, Any]] = []
        vfx_blocks: List[Dict[str, Any]] = []
        sfx_cues: List[Dict[str, Any]] = []
        timing_anchors: List[Dict[str, Any]] = []
        scenes_list: List[Dict[str, Any]] = []
        relationships_list: List[Dict[str, Any]] = []
        tool_reqs = set(["shape_layer", "arabic_rtl_text", "render_and_reopen"])

        input_assets = list(brief.get("assets") or [])
        input_words = list(brief.get("words") or [])
        headline = str(brief.get("headline") or beats[0].get("text") or "AION Creative Studio V5")
        subline = str(brief.get("subline") or "")
        bg_timeline: List[Dict[str, Any]] = []
        aspect_ratio = str(brief.get("aspect_ratio") or ("9:16" if self.height > self.width else "16:9"))
        story_genre = str(brief.get("story_genre") or "auto")
        script_full = str(brief.get("text") or " ".join(str(b.get("text", "")) for b in beats))
        typing_system = select_project_typography_system(
            story_genre=story_genre,
            aspect_ratio=aspect_ratio,
            language=str(brief.get("language") or "ar"),
            script_text=script_full,
            style_mode=style_mode,
        )

        if style_mode == "scientific_explanation":
            self._build_scientific_explanation(
                dur=dur,
                palette=palette,
                input_assets=input_assets,
                headline=headline,
                subline=subline,
                asset_refs=asset_refs,
                proc_graphics=proc_graphics,
                motion_paths=motion_paths,
                typo_blocks=typo_blocks,
                vfx_blocks=vfx_blocks,
                sfx_cues=sfx_cues,
                timing_anchors=timing_anchors,
                tool_reqs=tool_reqs,
                planned_beats=planned_beats,
            )
            cam = self.comp.build_camera_choreography("slow_push_in", 0.0, dur, focus_poi=[self.width * 0.5, self.height * 0.48, 0.0])
            lighting = self.comp.build_lighting_rig("target_spotlight_shift", 0.0, dur, accent_color=palette["accent"], is_light_bg=bool(palette.get("is_light_bg")), target_xy=(self.width * 0.66, self.height * 0.48))
            enable_3d_stage = True
            metaphor = "scientific_network_with_targeted_spotlight"
            nested_badge = None

        elif style_mode == "cinematic_2_5d":
            self._build_cinematic_2_5d(
                dur=dur,
                palette=palette,
                input_assets=input_assets,
                headline=headline,
                asset_refs=asset_refs,
                proc_graphics=proc_graphics,
                motion_paths=motion_paths,
                typo_blocks=typo_blocks,
                vfx_blocks=vfx_blocks,
                sfx_cues=sfx_cues,
                timing_anchors=timing_anchors,
                tool_reqs=tool_reqs,
            )
            cam = self.comp.build_camera_choreography("establishing_orbit", 0.0, dur, focus_poi=[self.width * 0.5, self.height * 0.48, 0.0])
            lighting = self.comp.build_lighting_rig("dramatic_key_spot", 0.0, dur, accent_color=palette["accent"], is_light_bg=False, target_xy=(self.width * 0.5, self.height * 0.48))
            enable_3d_stage = True
            metaphor = "multi_plane_2_5d_parallax_diorama"
            nested_badge = None

        elif style_mode == "editorial_motion_graphics":
            self._build_editorial_motion_graphics(
                dur=dur,
                palette=palette,
                headline=headline,
                subline=subline,
                planned_beats=planned_beats,
                asset_refs=asset_refs,
                proc_graphics=proc_graphics,
                motion_paths=motion_paths,
                typo_blocks=typo_blocks,
                vfx_blocks=vfx_blocks,
                sfx_cues=sfx_cues,
                timing_anchors=timing_anchors,
                tool_reqs=tool_reqs,
            )
            cam = self.comp.build_camera_choreography("lateral_pan_track", 0.0, dur)
            lighting = self.comp.build_lighting_rig("soft_editorial_sweep", 0.0, dur, accent_color=palette["accent"], is_light_bg=True)
            enable_3d_stage = False
            metaphor = "editorial_infographic_and_kinetic_arabic_typography"
            nested_badge = {"comp_name": "EditorialCrest", "text": "الإدراك البصري", "fill": palette["surface"], "stroke": palette["accent"], "position": [self.width * 0.85, self.height * 0.13], "scale": 58.0}
            tool_reqs.add("nested_compositions")

        else:
            # Multi-beat full section orchestration when multiple sentences or assets are present
            if len(planned_beats) >= 2 or len(input_assets) >= 4:
                cam, lighting, enable_3d_stage, metaphor, bg_timeline, scenes_list, relationships_list = self._build_multi_beat_section(
                    section_id=section_id,
                    dur=dur,
                    palette=palette,
                    planned_beats=planned_beats,
                    input_assets=input_assets,
                    input_words=input_words,
                    asset_refs=asset_refs,
                    proc_graphics=proc_graphics,
                    motion_paths=motion_paths,
                    typo_blocks=typo_blocks,
                    vfx_blocks=vfx_blocks,
                    sfx_cues=sfx_cues,
                    timing_anchors=timing_anchors,
                    tool_reqs=tool_reqs,
                    typing_system=typing_system,
                )
                nested_badge = None
            else:
                self._build_editorial_motion_graphics(
                    dur=dur,
                    palette=palette,
                    headline=headline,
                    subline=subline,
                    planned_beats=planned_beats,
                    asset_refs=asset_refs,
                    proc_graphics=proc_graphics,
                    motion_paths=motion_paths,
                    typo_blocks=typo_blocks,
                    vfx_blocks=vfx_blocks,
                    sfx_cues=sfx_cues,
                    timing_anchors=timing_anchors,
                    tool_reqs=tool_reqs,
                )
                cam = self.comp.build_camera_choreography(lead_treatment["camera_profile"], 0.0, dur)
                lighting = self.comp.build_lighting_rig(lead_treatment["lighting_profile"], 0.0, dur, accent_color=palette["accent"], is_light_bg=bool(palette.get("is_light_bg")))
                enable_3d_stage = not bool(palette.get("is_light_bg"))
                metaphor = lead_treatment["visual_metaphor"]
                nested_badge = None

        if not scenes_list:
            scenes_list = [{
                "scene_id": f"{section_id}_main",
                "intent": planned_beats[0]["classification"]["intent"],
                "time": {"start": 0.0, "end": round(dur, 3)},
                "assets": copy.deepcopy(asset_refs),
            }]

        # Apply coherent project typography font choice onto non-multi-beat single blueprints if generic Cairo was set
        if style_mode in ("scientific_explanation", "cinematic_2_5d", "editorial_motion_graphics") or not (len(planned_beats) >= 2 or len(input_assets) >= 4):
            for idx_tb, tb in enumerate(typo_blocks):
                if idx_tb == 0:
                    tb.setdefault("role", "editorial_headline")
                    tb["font"] = typing_system["display"]
                    tb["font_style"] = typing_system["display_style"]
                else:
                    tb.setdefault("role", "editorial_headline")
                    tb["font"] = typing_system["primary"]
                    tb["font_style"] = typing_system["primary_style"]

        sg_out = {
            "schema_version": SCENE_GRAPH_V2,
            "project_id": section_id,
            "section_id": section_id,
            "fps": fps,
            "width": self.width,
            "height": self.height,
            "aspect_ratio": aspect_ratio,
            "typography_system": typing_system,
            "source_timeline": {"audio_file": audio_file, "duration_sec": round(dur, 3)},
            "narrative_intent": {
                "primary": planned_beats[0]["classification"]["intent"],
                "style_mode": style_mode,
                "beats": planned_beats,
            },
            "asset_references": asset_refs,
            "relationships": relationships_list,
            "subtitles": [],
            "visual_metaphor": {"name": metaphor, "style": style_mode},
            "composition": {
                "resolution": [self.width, self.height],
                "fps": fps,
                "layout_mode": style_mode,
                "safe_margin_px": 96,
                "bg_color": bg_timeline[0]["c1"] if bg_timeline else palette["bg"],
                "palette": palette,
                "enable_3d_stage": enable_3d_stage,
            },
            "procedural_graphics": proc_graphics,
            "motion_paths": motion_paths,
            "camera": cam,
            "lighting": lighting,
            "vfx": vfx_blocks,
            "typography": typo_blocks,
            "sfx": sfx_cues,
            "timing_anchors": timing_anchors,
            "tool_requirements": sorted(tool_reqs),
            "fallbacks": [],
            "quality_constraints": {
                "use_character": False,
                "zero_bgm": True,
                "never_truncate_voiceover": True,
                "no_harsh_glow_on_bright_bg": True,
                "require_arabic_rtl_shaping": True,
            },
            **({"nested_badge": nested_badge} if nested_badge else {}),
            **({"background_timeline": bg_timeline} if bg_timeline else {}),
            "scenes": scenes_list,
        }
        return sync_scene_graph_v2_views(sg_out)

    def _build_scientific_explanation(
        self,
        *,
        dur: float,
        palette: Dict[str, Any],
        input_assets: List[Dict[str, Any]],
        headline: str,
        subline: str,
        asset_refs: List[Dict[str, Any]],
        proc_graphics: List[Dict[str, Any]],
        motion_paths: List[Dict[str, Any]],
        typo_blocks: List[Dict[str, Any]],
        vfx_blocks: List[Dict[str, Any]],
        sfx_cues: List[Dict[str, Any]],
        timing_anchors: List[Dict[str, Any]],
        tool_reqs: set,
        planned_beats: List[Dict[str, Any]],
    ) -> None:
        """Test A blueprint: Original visual assets + Bezier splines + network nodes + animated arrows + spotlight."""
        w, h = self.width, self.height
        # Left side: Original extracted hero asset(s) (or procedural brain vector fallback)
        if input_assets:
            for idx, a in enumerate(input_assets[:2]):
                pos = [w * 0.22, h * (0.35 if idx == 0 else 0.65)]
                asset_refs.append({
                    "id": a.get("id", f"sci_asset_{idx}"),
                    "path": a.get("path"),
                    "icon": a.get("icon", "brain"),
                    "in": round(idx * 0.4, 3),
                    "out": round(dur, 3),
                    "position": pos,
                    "scale": 70.0 if idx == 0 else 48.0,
                    "three_d": True,
                    "z": 0.0,
                })
                motion_paths.append({
                    "layer": f"Asset_{a.get('id', f'sci_asset_{idx}')}" if a.get("path") else f"SvgAsset_{a.get('id', f'sci_asset_{idx}')}",
                    "keyframes": [
                        {"time": round(idx * 0.4, 3), "pos": [pos[0] - 25.0, pos[1], 0.0]},
                        {"time": round(dur * 0.8, 3), "pos": [pos[0] + 15.0, pos[1], 0.0]},
                    ],
                    "idle_expression": True,
                    "amplitude": 6.0,
                })
        else:
            asset_refs.append({"id": "hero_brain", "icon": "brain", "in": 0.0, "out": round(dur, 3), "position": [w * 0.25, h * 0.45], "scale": 250.0, "three_d": True, "z": 0.0})

        # Right side: 3-node Scientific Signal Network aligned cleanly in coherent Z=0 3D plane above headline zone
        nodes = [
            {"position": [w * 0.54, h * 0.23], "radius": 54, "icon": "eyes", "label": "استقبال الإشارة", "three_d": True, "z": 0.0},
            {"position": [w * 0.78, h * 0.42], "radius": 62, "icon": "neuron_network", "label": "معالجة عصبية", "three_d": True, "z": 0.0},
            {"position": [w * 0.56, h * 0.60], "radius": 54, "icon": "wave_signal", "label": "بناء الإدراك", "three_d": True, "z": 0.0},
        ]
        proc_graphics.extend(
            self.proc.build_network_diagram(nodes, [(0, 1), (1, 2)], palette=palette, t_start=0.25, t_end=dur, prefix="sci")
        )
        # Main curved explanatory arrow connecting original hero asset -> network top node rim
        proc_graphics.append(
            self.proc.build_bezier_connector(
                "hero_to_network_arrow",
                (w * 0.31, h * 0.35),
                (w * 0.48, h * 0.24),
                curvature=-0.20,
                stroke_color=palette["accent"],
                stroke_width=10.0,
                start_time=0.45,
                draw_duration=0.75,
                end_time=dur,
                with_arrow=True,
                layer_3d=True,
                z_depth=0.0,
            )
        )
        proc_graphics.append(
            self.proc.build_concentric_rings("sci_radar", (w * 0.78, h * 0.42), copies=4, base_size=132.0, stroke_color=palette["primary"], t_start=0.5, t_end=dur)
        )

        # Headline RTL card at bottom safe zone
        typo_blocks.append(
            self.proc.build_kinetic_typography_block(
                "sci_headline", headline, position=(w * 0.5, h * 0.87), palette=palette, t_start=0.2, t_end=dur, font_size=50
            )
        )
        if subline:
            typo_blocks.append(
                self.proc.build_kinetic_typography_block(
                    "sci_subline", subline, position=(w * 0.5, h * 0.12), palette=palette, t_start=0.5, t_end=dur, font_size=36, with_backdrop=False
                )
            )

        vfx_blocks.extend([
            {"type": "glow", "target": "Node_sci_node_1", "intensity": 0.75, "radius": 38.0, "start": 0.8, "end": dur},
            {"type": "light sweep", "target": "Path_hero_to_network_arrow", "start": 1.1, "end": dur},
        ])
        sfx_cues.extend([
            {"time": 0.25, "cue": "pop", "gain": 0.34},
            {"time": 0.50, "cue": "whoosh", "gain": 0.36},
            {"time": 1.15, "cue": "glint", "gain": 0.32},
        ])
        timing_anchors.extend([
            {"anchor_id": "asset_in", "time": 0.0, "type": "entrance"},
            {"anchor_id": "arrow_draw", "time": 0.45, "type": "bezier_reveal"},
            {"anchor_id": "network_lock", "time": 1.2, "type": "peak"},
        ])
        tool_reqs.update(["bezier_path", "trim_paths", "arrow_path", "repeaters", "expressions", "lights_and_shadows", "camera_motion", "glow", "animated_svg"])

    def _build_cinematic_2_5d(
        self,
        *,
        dur: float,
        palette: Dict[str, Any],
        input_assets: List[Dict[str, Any]],
        headline: str,
        asset_refs: List[Dict[str, Any]],
        proc_graphics: List[Dict[str, Any]],
        motion_paths: List[Dict[str, Any]],
        typo_blocks: List[Dict[str, Any]],
        vfx_blocks: List[Dict[str, Any]],
        sfx_cues: List[Dict[str, Any]],
        timing_anchors: List[Dict[str, Any]],
        tool_reqs: set,
    ) -> None:
        """Test B blueprint: 2.5D multi-plane depth + Camera + Mask Reveal + Lighting + Parallax + Transition."""
        w, h = self.width, self.height
        # Deep 2.5D architectural depth planes
        proc_graphics.extend([
            {"kind": "depth_plane", "id": "far_frame", "shape": "rounded", "size": [980, 560], "position": [w * 0.5, h * 0.48], "z": DEPTH_PLANES_Z["far_backdrop"] * 0.7, "fill": "#1A1625", "stroke": palette["secondary"], "start": 0.0, "end": dur},
            {"kind": "depth_plane", "id": "mid_accent_left", "shape": "rounded", "size": [340, 420], "position": [w * 0.28, h * 0.50], "z": DEPTH_PLANES_Z["mid_stage"], "fill": palette["surface"], "stroke": palette["primary"], "start": 0.15, "end": dur},
            {"kind": "badge_card", "id": "transition_callout", "title": "عمق المشهد البصري", "subtitle": "طبقة أمامية بتأثير التتبع", "position": [w * 0.72, h * 0.56], "size": [380, 150], "fill": palette["surface"], "stroke": palette["accent"], "text_color": palette["text"], "use_track_matte": True, "start": round(dur * 0.32, 3), "end": dur},
        ])

        if input_assets:
            hero = input_assets[0]
            asset_refs.append({
                "id": hero.get("id", "cinematic_hero"),
                "path": hero.get("path"),
                "icon": hero.get("icon", "crystal"),
                "in": 0.2,
                "out": round(dur, 3),
                "position": [w * 0.46, h * 0.46],
                "scale": 96.0,
                "three_d": True,
                "z": -40.0,
                "mask_reveal": True,
            })
            target_layer = f"Asset_{hero.get('id', 'cinematic_hero')}" if hero.get("path") else f"SvgAsset_{hero.get('id', 'cinematic_hero')}"
        else:
            asset_refs.append({"id": "cinematic_hero", "icon": "crystal", "in": 0.2, "out": round(dur, 3), "position": [w * 0.46, h * 0.46], "scale": 270.0, "three_d": True, "z": -40.0, "mask_reveal": True})
            target_layer = "SvgAsset_cinematic_hero"

        motion_paths.append({
            "layer": target_layer,
            "keyframes": [
                {"time": 0.2, "pos": [w * 0.43, h * 0.46, -40.0]},
                {"time": round(dur * 0.9, 3), "pos": [w * 0.50, h * 0.44, -90.0]},
            ],
        })
        typo_blocks.append(
            self.proc.build_kinetic_typography_block(
                "cin_title", headline, position=(w * 0.5, h * 0.87), palette=palette, t_start=0.35, t_end=dur, font_size=52
            )
        )
        vfx_blocks.extend([
            {"type": "blur", "target": "Plane_mid_accent_left", "from_blur": 26.0, "to_blur": 0.0, "start": 0.15, "end": min(dur, 1.2)},
            {"type": "particles", "color": palette["primary"], "birth_rate": 7.0, "velocity": 1.6, "opacity": 42.0, "start": 0.2, "end": dur},
        ])
        sfx_cues.extend([
            {"time": 0.2, "cue": "whoosh", "gain": 0.35},
            {"time": round(dur * 0.32, 3), "cue": "card_snap", "gain": 0.36},
            {"time": round(dur * 0.70, 3), "cue": "glint", "gain": 0.30},
        ])
        timing_anchors.extend([
            {"anchor_id": "mask_reveal_start", "time": 0.2, "type": "mask_reveal"},
            {"anchor_id": "matte_card_in", "time": round(dur * 0.32, 3), "type": "transition"},
        ])
        tool_reqs.update(["layer_2_5d", "camera_motion", "masks", "track_mattes", "lights_and_shadows", "blur", "particles"])

    def _build_editorial_motion_graphics(
        self,
        *,
        dur: float,
        palette: Dict[str, Any],
        headline: str,
        subline: str,
        planned_beats: List[Dict[str, Any]],
        asset_refs: List[Dict[str, Any]],
        proc_graphics: List[Dict[str, Any]],
        motion_paths: List[Dict[str, Any]],
        typo_blocks: List[Dict[str, Any]],
        vfx_blocks: List[Dict[str, Any]],
        sfx_cues: List[Dict[str, Any]],
        timing_anchors: List[Dict[str, Any]],
        tool_reqs: set,
    ) -> None:
        """Test C blueprint: Procedural icons + vector shapes + Arabic RTL typography + word emphasis + layout shift."""
        w, h = self.width, self.height
        # Procedurally generated vector SVG icons via creative_v3/asset_factory
        asset_refs.extend([
            {"id": "icon_lightbulb", "icon": "lightbulb", "in": 0.1, "out": round(dur, 3), "position": [w * 0.13, h * 0.29], "scale": 165.0, "three_d": False},
            {"id": "icon_chart", "icon": "chart", "in": 0.35, "out": round(dur, 3), "position": [w * 0.87, h * 0.29], "scale": 165.0, "three_d": False},
        ])
        motion_paths.append({
            "layer": "SvgAsset_icon_lightbulb",
            "keyframes": [
                {"time": 0.1, "pos": [w * 0.13, h * 0.29, 0.0]},
                {"time": round(dur * 0.55, 3), "pos": [w * 0.16, h * 0.29, 0.0]},
            ],
        })

        # Layout shifts / dual modules: Timeline spine + Animated Comparison / Bar Chart
        milestones = [
            {"label": "المؤثر الأول", "detail": "تشتت الانتباه"},
            {"label": "الفلتر الذهني", "detail": "إعادة التركيب"},
            {"label": "النتيجة الواعية", "detail": "رؤية متكاملة"},
        ]
        proc_graphics.extend(
            self.proc.build_timeline_diagram(milestones, palette=palette, t_start=0.25, t_end=round(dur, 3), y_center=h * 0.57, rtl=True)
        )
        proc_graphics.append(
            self.proc.build_bezier_connector(
                "editorial_connector",
                (w * 0.21, h * 0.29),
                (w * 0.79, h * 0.29),
                curvature=0.04,
                stroke_color=palette["accent"],
                stroke_width=6.0,
                start_time=0.4,
                draw_duration=0.7,
                end_time=dur,
                with_arrow=True,
            )
        )

        # Hero Arabic RTL Kinetic Headline + Emphasis Subtitle (no overlap with top-right crest!)
        typo_blocks.append(
            self.proc.build_kinetic_typography_block(
                "ed_hero_ar", headline, position=(w * 0.5, h * 0.87), palette=palette, t_start=0.15, t_end=dur, font_size=54, with_backdrop=True
            )
        )
        typo_blocks.append(
            self.proc.build_kinetic_typography_block(
                "ed_top_ar", subline or "التركيز يغيّر ما يراه عقلك", position=(w * 0.36, h * 0.13), palette=palette, t_start=0.65, t_end=dur, font_size=32, with_backdrop=True
            )
        )

        vfx_blocks.append({"type": "light sweep", "target": "TextCard_ed_hero_ar", "start": 0.9, "end": dur})
        sfx_cues.extend([
            {"time": 0.15, "cue": "card_snap", "gain": 0.36},
            {"time": 0.45, "cue": "pop", "gain": 0.32},
            {"time": 0.95, "cue": "glint", "gain": 0.32},
        ])
        timing_anchors.extend([
            {"anchor_id": "hero_title_in", "time": 0.15, "type": "word_emphasis"},
            {"anchor_id": "timeline_draw", "time": 0.25, "type": "layout_transform"},
            {"anchor_id": "callout_peak", "time": 0.65, "type": "emphasis"},
        ])
        tool_reqs.update(["animated_svg", "shape_layer", "trim_paths", "arrow_path", "text_animators", "arabic_rtl_text"])

    def _concise_headline(self, text: str, max_words: int = 6) -> str:
        return synthesize_editorial_headline(text)

    def _build_multi_beat_section(
        self,
        *,
        section_id: str,
        dur: float,
        palette: Dict[str, Any],
        planned_beats: List[Dict[str, Any]],
        input_assets: List[Dict[str, Any]],
        input_words: List[Dict[str, Any]],
        asset_refs: List[Dict[str, Any]],
        proc_graphics: List[Dict[str, Any]],
        motion_paths: List[Dict[str, Any]],
        typo_blocks: List[Dict[str, Any]],
        vfx_blocks: List[Dict[str, Any]],
        sfx_cues: List[Dict[str, Any]],
        timing_anchors: List[Dict[str, Any]],
        tool_reqs: set,
        typing_system: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any], bool, str, List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Editorial scene-grouped V5 choreography restoring Gold clarity, motion diversity & restraint."""
        w, h = self.width, self.height
        is_mobile = h > w
        cx, cy = w * 0.5, h * 0.5
        stage_y = round(h * (0.56 if is_mobile else 0.528), 1)
        t_sys = typing_system or select_project_typography_system(
            aspect_ratio="9:16" if is_mobile else "16:9",
            script_text=" ".join(str(p.get("text", "")) for p in planned_beats),
        )

        raw_beats = [{"id": p["beat_id"], "start": p["start"], "end": p["end"], "text": p["text"]} for p in planned_beats]
        sem_alloc = plan_semantic_section_allocation(
            section_id=section_id,
            beats=raw_beats,
            input_assets=input_assets,
            words=input_words,
        )
        scene_groups = sem_alloc.get("scene_groups") or []
        bg_timeline: List[Dict[str, Any]] = []
        cam_keys: List[Dict[str, Any]] = []
        scenes_list: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []
        base_z = -1800.0

        # Track SFX timing discipline (never spam > 15 cues or stack < 0.55s)
        last_sfx_time = -10.0
        sfx_budget = min(15, max(8, int(dur * 0.32)))

        def _emit_sfx(t_cue: float, cue_name: str, gain: float = 0.28, pan: float = 0.0, allow_close: bool = False) -> None:
            nonlocal last_sfx_time
            if len(sfx_cues) >= sfx_budget:
                return
            t_c = round(max(0.02, min(dur - 0.15, float(t_cue))), 3)
            if not allow_close and (t_c - last_sfx_time) < 0.55:
                return
            entry: Dict[str, Any] = {"time": t_c, "cue": cue_name, "gain": round(gain, 2)}
            if abs(pan) >= 0.05:
                entry["pan"] = round(max(-0.6, min(0.6, pan)), 2)
            sfx_cues.append(entry)
            last_sfx_time = t_c

        last_entrance: Optional[str] = None
        same_ent_run = 0
        slide_down_used = False

        def _pick_entrance(role: str, comp_mode: str, slot_idx: int, total_in_wave: int, is_dramatic: bool, is_mask: bool) -> Tuple[str, float]:
            nonlocal last_entrance, same_ent_run, slide_down_used
            if is_mask:
                cand, edur = "mask_reveal", 0.45
            elif is_dramatic:
                cand, edur = "soft_fade", 0.32
            elif not slide_down_used and role in ("research_context", "illustrative_prop") and slot_idx == 0 and total_in_wave >= 2:
                cand, edur = "slide_down", 0.36
                slide_down_used = True
            elif slot_idx == total_in_wave - 1 and total_in_wave >= 2:
                cand, edur = "slide_right", 0.36
            elif role == "human_example" and comp_mode == "split_polarity" and slot_idx == 0:
                cand, edur = "soft_fade", 0.30
            else:
                cand, edur = "pop_settle", 0.36

            if cand == last_entrance:
                same_ent_run += 1
                if same_ent_run >= 3:
                    cand = "slide_right" if cand != "slide_right" else "soft_fade"
                    same_ent_run = 0
            else:
                last_entrance = cand
                same_ent_run = 1
            return cand, edur

        def _card_style_for_mood(mood_key: str, is_light: bool) -> str:
            if is_light:
                return "warm"
            if mood_key == "crimson_suspense":
                return "dark_crimson"
            if mood_key == "historical_amber":
                return "amber"
            return "arctic"

        prev_mood_key: Optional[str] = None
        for s_idx, sc in enumerate(scene_groups):
            sc_id = sc["scene_id"]
            st = max(0.0, float(sc["start"]))
            en = min(dur, float(scene_groups[s_idx + 1]["start"]) if s_idx + 1 < len(scene_groups) else dur)
            if en <= st + 0.35:
                en = min(dur, st + 0.9)
            sc_dur = en - st
            mood = sc["mood"]
            mood_key = sc["mood_key"]
            is_light = bool(mood["is_light_bg"])
            comp_mode = sc["composition_mode"]
            sub_beats = sc["sub_beats"]

            # Clean scene-boundary background mood transitions completing right at the cut (zero blank grey mid-frame)
            if s_idx == 0:
                bg_timeline.append({
                    "time": 0.0,
                    "c1": mood["c1"], "c2": mood["c2"], "c3": mood["c3"], "c4": mood["c4"],
                    "vignette": mood["vignette"], "mood": mood_key,
                })
            elif mood_key != prev_mood_key:
                prev_m = scene_groups[s_idx - 1]["mood"]
                bg_timeline.append({
                    "time": round(max(0.05, st - 0.35), 3),
                    "c1": prev_m["c1"], "c2": prev_m["c2"], "c3": prev_m["c3"], "c4": prev_m["c4"],
                    "vignette": prev_m["vignette"], "mood": prev_mood_key,
                })
                bg_timeline.append({
                    "time": round(min(en - 0.05, st + 0.08), 3),
                    "c1": mood["c1"], "c2": mood["c2"], "c3": mood["c3"], "c4": mood["c4"],
                    "vignette": mood["vignette"], "mood": mood_key,
                })
            prev_mood_key = mood_key

            # Flatten items inside this editorial scene while honoring each sub-beat's spoken timing
            scene_items: List[Dict[str, Any]] = []
            for sb in sub_beats:
                sb_st = float(sb["beat"]["start"])
                sb_en = float(sb["beat"]["end"])
                for idx_it, it in enumerate(sb.get("items", [])):
                    it_copy = dict(it)
                    it_copy["_sub_start"] = sb_st
                    it_copy["_sub_end"] = sb_en
                    scene_items.append(it_copy)

            # Group into non-crowded compositional waves (1..3 items per wave, never drop assets)
            if len(scene_items) >= 4:
                split_k = 2 if len(scene_items) == 4 else 3
                mid_t = round(st + sc_dur * 0.50, 3)
                waves = [
                    (scene_items[:split_k], st, mid_t),
                    (scene_items[split_k:], mid_t, en),
                ]
            else:
                waves = [(scene_items, st, en)]

            scene_assets_out: List[Dict[str, Any]] = []
            scene_rels_out: List[Dict[str, Any]] = []
            focal_x = cx

            # Scene opening SFX
            open_sfx = str(sub_beats[0].get("beat_sfx", "card_snap"))
            _emit_sfx(st + 0.08, open_sfx, gain=0.28)

            for w_idx, (wave_items, w_st, w_en) in enumerate(waves):
                w_dur = max(0.8, w_en - w_st)
                n_w = len(wave_items)

                if n_w == 0:
                    # Conceptual network fallback ONLY if 0 assets matched
                    nodes = [
                        {"position": [w * 0.36, stage_y - 20.0], "radius": 60, "icon": "brain", "label": "", "three_d": True, "z": 0.0},
                        {"position": [w * 0.64, stage_y - 20.0], "radius": 60, "icon": "eyes", "label": sc["headline"], "label_color": "#0F172A" if is_light else "#F8FAFC", "three_d": True, "z": 0.0},
                    ]
                    proc_graphics.extend(
                        self.proc.build_network_diagram(nodes, [(0, 1)], palette={"surface": mood["card_bg"], "primary": mood["card_border"], "accent": mood["card_border"], "text": mood["text_color"]}, t_start=w_st + 0.1, t_end=w_en, prefix=f"{sc_id}_w{w_idx}")
                    )
                    continue

                # Determine semantic slot coordinates & scale bounds per composition_mode & aspect ratio
                slot_specs: List[Dict[str, Any]] = []
                if is_mobile:
                    if n_w == 1:
                        slot_specs = [{"pos": [cx, stage_y], "target_h": 540, "max_w": 820}]
                    elif n_w == 2:
                        slot_specs = [
                            {"pos": [cx, round(h * 0.44, 1)], "target_h": 380, "max_w": 720, "solo_center_shift": True},
                            {"pos": [cx, round(h * 0.67, 1)], "target_h": 380, "max_w": 720},
                        ]
                    else:
                        slot_specs = [
                            {"pos": [round(w * 0.30, 1), round(h * 0.46, 1)], "target_h": 330, "max_w": 390},
                            {"pos": [round(w * 0.70, 1), round(h * 0.46, 1)], "target_h": 330, "max_w": 390},
                            {"pos": [cx, round(h * 0.68, 1)], "target_h": 350, "max_w": 520},
                        ]
                elif n_w == 1:
                    slot_specs = [{"pos": [cx, stage_y], "target_h": 465, "max_w": 780}]
                elif n_w == 2:
                    if comp_mode == "split_polarity":
                        slot_specs = [
                            {"pos": [540.0, stage_y], "target_h": 430, "max_w": 540, "solo_center_shift": True},
                            {"pos": [1380.0, stage_y], "target_h": 430, "max_w": 540},
                        ]
                    elif comp_mode == "living_diagram":
                        slot_specs = [
                            {"pos": [550.0, stage_y], "target_h": 420, "max_w": 520, "solo_center_shift": True},
                            {"pos": [1370.0, stage_y], "target_h": 420, "max_w": 520},
                        ]
                    else:
                        # hero_solo_then_shift: hero starts centered if companion enters >= 0.72s later!
                        slot_specs = [
                            {"pos": [600.0, stage_y], "target_h": 435, "max_w": 530, "solo_center_shift": True},
                            {"pos": [1320.0, stage_y], "target_h": 425, "max_w": 530},
                        ]
                else:
                    # 3 assets: when living_diagram, put concept_explanation/head on left, prop/lens mid-top, outcome right
                    if comp_mode == "living_diagram":
                        if len(wave_items) == 3:
                            roles_w = [str(it["catalog_meta"].get("narrative_role", "")) for it in wave_items]
                            if "concept_explanation" in roles_w and roles_w[0] != "concept_explanation":
                                idx_c = roles_w.index("concept_explanation")
                                wave_items = [wave_items[idx_c]] + [it for k_i, it in enumerate(wave_items) if k_i != idx_c]
                        slot_specs = [
                            {"pos": [470.0, stage_y], "target_h": 405, "max_w": 430},
                            {"pos": [970.0, stage_y - 125.0], "target_h": 270, "max_w": 360},
                            {"pos": [1460.0, stage_y], "target_h": 400, "max_w": 430},
                        ]
                    else:
                        # Dynamic editorial pyramid triad (avoids flat horizontal shelf)
                        slot_specs = [
                            {"pos": [455.0, stage_y + 28.0], "target_h": 380, "max_w": 420},
                            {"pos": [960.0, stage_y - 34.0], "target_h": 430, "max_w": 460},
                            {"pos": [1465.0, stage_y + 28.0], "target_h": 380, "max_w": 420},
                        ]

                # Compute clean stagger timestamps anchored within [w_st, w_en] (zero dead gap on first frame of scene/wave)
                in_times: List[float] = []
                for j, it in enumerate(wave_items[:len(slot_specs)]):
                    raw_in = float(it.get("in_time", w_st))
                    if j == 0:
                        t_in = round(w_st, 3)
                    else:
                        min_gap_in = in_times[-1] + min(1.35, max(0.75, w_dur * 0.28))
                        t_in = round(min(max(min_gap_in, raw_in), max(w_st + 0.3, w_en - 1.15)), 3)
                    in_times.append(t_in)

                placed_wave: List[Dict[str, Any]] = []
                for j, it in enumerate(wave_items[:len(slot_specs)]):
                    spec = slot_specs[j]
                    a = it["src_asset"]
                    cat = it["catalog_meta"]
                    role = str(cat.get("narrative_role", "illustrative_prop"))
                    name_desc = normalize_text = f"{cat.get('name_ar', '')} {cat.get('description_ar', '')}"
                    src_id = str(a.get("id", f"entity_{it['entity_index']:02d}"))
                    inst_id = f"{sc_id}_w{w_idx}_{src_id}"
                    lname = f"Asset_{inst_id}" if a.get("path") else f"SvgAsset_{inst_id}"

                    in_t = in_times[j]
                    out_t = round(w_en, 3)
                    pos = list(spec["pos"])
                    th = int(spec["target_h"])
                    z_depth = 0.0 if j == 0 else 12.0
                    if j == 0:
                        focal_x = pos[0]

                    fx_prof = dict(it["fx_profile"])
                    use_card = bool(fx_prof.get("card_wrap"))
                    card_style = _card_style_for_mood(mood_key, is_light) if use_card else None
                    is_dramatic = (mood_key == "crimson_suspense") or role == "human_example" and comp_mode == "spotlight_focus"
                    ent_name, ent_dur = _pick_entrance(
                        role, comp_mode, j, min(n_w, len(slot_specs)),
                        is_dramatic=is_dramatic,
                        is_mask=bool(fx_prof.get("mask_reveal")),
                    )

                    # Purposeful keyframes (zero mechanical +-14px drift!)
                    asset_kfs: List[Dict[str, Any]] = []
                    start_pos = list(pos)
                    if spec.get("solo_center_shift") and len(in_times) >= 2 and (in_times[1] - in_t) >= 0.72:
                        # Enter centered at stage center, then glide smoothly to target position before companion arrives
                        start_pos = [cx, stage_y if is_mobile else pos[1]]
                        t_shift_0 = round(max(in_t + ent_dur + 0.08, in_times[1] - 0.46), 3)
                        t_shift_1 = round(in_times[1], 3)
                        if t_shift_1 > t_shift_0 + 0.12:
                            asset_kfs.append({"time": t_shift_0, "pos": [start_pos[0], start_pos[1], z_depth]})
                            asset_kfs.append({"time": t_shift_1, "pos": [pos[0], pos[1], z_depth]})
                    elif n_w == 1 and w_dur >= 2.6:
                        # Subtle tension push on solo focal or blank perception reveal
                        asset_kfs.append({"time": round(in_t + ent_dur + 0.05, 3), "scale_mult": 1.0})
                        asset_kfs.append({"time": round(max(in_t + ent_dur + 0.4, out_t - 0.25), 3), "scale_mult": 1.12})
                    elif n_w == 3 and j == 1 and w_dur >= 3.2 and role in ("illustrative_prop", "concept_explanation", "data_callout"):
                        # Gentle emphasis beat on central lens/evidence prop
                        peak_t = round(min(out_t - 0.5, in_t + 0.65), 3)
                        asset_kfs.append({"time": peak_t, "scale_mult": 1.12})
                        asset_kfs.append({"time": round(min(out_t - 0.15, peak_t + 0.55), 3), "scale_mult": 1.0})

                    asset_entry: Dict[str, Any] = {
                        "id": inst_id,
                        "asset_id": src_id,
                        "path": a.get("path"),
                        "icon": a.get("icon", "brain"),
                        "in": in_t,
                        "out": out_t,
                        "pos": start_pos,
                        "position": start_pos,
                        "target_h": th,
                        **({"max_w": int(spec["max_w"])} if spec.get("max_w") else {}),
                        "entrance": ent_name,
                        "entrance_dur": ent_dur,
                        "fade_out": 0.14,
                        "three_d": True,
                        "z": z_depth,
                        "role": role,
                        "shadow": bool(fx_prof.get("drop_shadow") and not use_card),
                        **({"keyframes": asset_kfs} if asset_kfs else {}),
                        **({"preprocess": ["exhibit_card"], "card_style": card_style} if use_card else {}),
                    }
                    scene_assets_out.append(asset_entry)
                    asset_refs.append(copy.deepcopy(asset_entry))
                    placed_wave.append({"lname": lname, "id": inst_id, "pos": pos, "in": in_t, "out": out_t, "desc": name_desc, "role": role})
                    timing_anchors.append({"anchor_id": f"{inst_id}_in", "time": in_t, "type": "asset_entrance"})

                    # Restrained VFX reconciled against actual scene mood brightness
                    for fx_item in fx_prof.get("fx", []):
                        fx_entry = dict(fx_item)
                        ftype = str(fx_entry.get("type", ""))
                        if ftype.lower() == "glow" and is_light:
                            fx_entry = {"type": "Light Sweep", "intensity": 24.0, "width": 44.0, "delay": 0.65}
                            ftype = "Light Sweep"
                        if ftype == "Light Sweep":
                            sweep_t = round(min(out_t - 0.35, in_t + float(fx_entry.pop("delay", 0.65))), 3)
                            fx_entry["time"] = sweep_t
                            fx_entry["start"] = sweep_t
                            fx_entry["end"] = out_t
                            fx_entry.setdefault("color", mood["card_border"])
                            _emit_sfx(sweep_t, "glint", gain=0.25)
                        else:
                            fx_entry["start"] = in_t
                            fx_entry["end"] = out_t
                        fx_entry["target"] = lname
                        vfx_blocks.append(fx_entry)

                    # Stereo-panned arrival SFX for notable companions (only if spaced >= 0.55s)
                    if j >= 1 and ent_name in ("slide_right", "pop_settle"):
                        pan_val = 0.35 if pos[0] > cx + 100 else (-0.35 if pos[0] < cx - 100 else 0.0)
                        cue_sfx = "whoosh" if ent_name == "slide_right" else fx_prof.get("sfx", "pop")
                        _emit_sfx(in_t, cue_sfx, gain=0.22, pan=pan_val)

                    # Subtle 3D contact shadow ONLY for un-carded grounded cutout props (follows shifting hero cleanly)
                    if not use_card and role != "section_identifier":
                        sh_id = f"{inst_id}_sh"
                        proc_graphics.append({
                            "kind": "ground_shadow",
                            "id": sh_id,
                            "position": [round(start_pos[0], 1), round(start_pos[1] + th * 0.50 + 10.0, 1)],
                            "size": [round(max(150.0, th * 0.55), 1), 18.0],
                            "fill": "#04070D",
                            "opacity": 28.0 if is_light else 42.0,
                            "three_d": True,
                            "z": z_depth + 2.0,
                            "start": in_t,
                            "end": out_t,
                        })
                        if start_pos[0] != pos[0] and len(asset_kfs) >= 2:
                            motion_paths.append({
                                "layer": f"GroundShadow_{sh_id}",
                                "keyframes": [
                                    {"time": asset_kfs[0]["time"], "pos": [round(start_pos[0], 1), round(start_pos[1] + th * 0.50 + 10.0, 1), z_depth + 2.0]},
                                    {"time": asset_kfs[1]["time"], "pos": [round(pos[0], 1), round(pos[1] + th * 0.50 + 10.0, 1), z_depth + 2.0]},
                                ],
                            })

                # Purposeful Procedural Relationship Graphics (ONLY when semantically warranted!)
                if len(placed_wave) == 2 and comp_mode == "split_polarity":
                    t_div = max(placed_wave[0]["in"], placed_wave[1]["in"])
                    div_pts = ((w * 0.16, round(h * 0.555, 1)), (w * 0.84, round(h * 0.555, 1))) if is_mobile else ((cx, 285.0), (cx, 815.0))
                    div = self.proc.build_bezier_connector(
                        f"{sc_id}_w{w_idx}_divider",
                        div_pts[0],
                        div_pts[1],
                        curvature=0.0,
                        stroke_color="#64748B" if not is_light else "#94A3B8",
                        stroke_width=3.5,
                        start_time=t_div,
                        draw_duration=0.40,
                        end_time=w_en,
                        with_arrow=False,
                        layer_3d=True,
                        z_depth=0.0,
                    )
                    proc_graphics.append(div)
                    rel = {"id": div["id"], "kind": "comparison_divider", "from": placed_wave[0]["id"], "to": placed_wave[1]["id"]}
                    relationships.append(rel)
                    scene_rels_out.append(rel)

                elif len(placed_wave) >= 2 and comp_mode == "living_diagram":
                    for e_i in range(len(placed_wave) - 1):
                        p_a, p_b = placed_wave[e_i], placed_wave[e_i + 1]
                        x0, y0 = p_a["pos"]
                        x1, y1 = p_b["pos"]
                        dx, dy = x1 - x0, y1 - y0
                        if abs(dy) > abs(dx) and abs(dx) < 120.0:
                            start_pt = (x0, y0 + (155.0 if dy > 0 else -155.0))
                            end_pt = (x1, y1 - (155.0 if dy > 0 else -155.0))
                        else:
                            start_pt = (x0 + (155.0 if dx > 0 else -155.0), y0 - 15.0)
                            end_pt = (x1 - (155.0 if dx > 0 else -155.0), y1 - 15.0)
                        arrow = self.proc.build_bezier_connector(
                            f"{sc_id}_w{w_idx}_link_{e_i}",
                            start_pt,
                            end_pt,
                            curvature=-0.18 if e_i % 2 == 0 else 0.16,
                            stroke_color=mood["card_border"] if e_i == 0 else "#F59E0B",
                            stroke_width=5.5,
                            start_time=round(max(p_a["in"], p_b["in"]) + 0.08, 3),
                            draw_duration=0.45,
                            end_time=w_en,
                            with_arrow=True,
                            layer_3d=True,
                            z_depth=0.0,
                        )
                        proc_graphics.append(arrow)
                        rel = {"id": arrow["id"], "kind": "causal_link", "from": p_a["id"], "to": p_b["id"]}
                        relationships.append(rel)
                        scene_rels_out.append(rel)

                # Spotlight cone ONLY behind literal studio spotlight props (not helmet headlamps)
                for pw_item in placed_wave:
                    dl = pw_item["desc"].lower()
                    if any(k in dl for k in ("كشاف الضوء", "مصباح استوديو", "red spotlight", "spotlight")) and not any(x in dl for x in ("خوذة", "helmet")):
                        px, py = pw_item["pos"]
                        proc_graphics.append({
                            "kind": "spotlight_cone",
                            "id": f"{pw_item['id']}_cone",
                            "vertices": [[px + 40.0, py], [min(w - 140.0, px + 620.0), py + 110.0], [min(w - 180.0, px + 560.0), py + 390.0], [px + 120.0, py + 380.0]],
                            "fill": "#E11D48" if mood_key == "crimson_suspense" else mood["card_border"],
                            "fill_opacity": 24.0,
                            "blur": 42.0,
                            "opacity": 70.0,
                            "three_d": True,
                            "z": 18.0,
                            "start": pw_item["in"] + 0.1,
                            "end": pw_item["out"],
                        })
                        break

            # Story-driven Editorial Headlines per sub-beat (cleanly separated from subtitles)
            for sb_idx, sb in enumerate(sub_beats):
                sb_st = max(0.0, float(sb["beat"]["start"]))
                sb_en = min(en, float(sub_beats[sb_idx + 1]["beat"]["start"]) if sb_idx + 1 < len(sub_beats) else en)
                hl_text = str(sb.get("editorial_headline") or synthesize_editorial_headline(str(sb["beat"].get("text", ""))))
                hl_out = round(max(sb_st + 0.65, sb_en), 3)
                typo_blocks.append(
                    plan_headline_treatment(
                        text=hl_text,
                        beat_index=len(typo_blocks),
                        scene_index=s_idx,
                        t_start=round(sb_st + (0.04 if sb_idx > 0 else 0.0), 3),
                        t_end=hl_out,
                        mood=mood,
                        mood_key=mood_key,
                        typing_system=t_sys,
                        comp_width=w,
                        comp_height=h,
                        headline_id=f"{sc_id}_hl_{sb_idx}",
                    )
                )

            # Breathing 2.5D Camera Choreography per Scene (reset on cut + smooth focal push-in)
            cam_poi_x = round(cx + (focal_x - cx) * 0.16, 1)
            if s_idx == 0 or sc["continuity"] != "analytical_focus":
                cam_keys.append({"time": round(st, 3), "pos": [cx, cy, base_z], "poi": [cx, cy, 0.0]})
            else:
                cam_keys.append({"time": round(st, 3), "pos": [cam_poi_x, cy - 5.0, base_z + 60.0], "poi": [cam_poi_x, cy - 5.0, 0.0]})
            push_z = base_z + (210.0 if mood_key == "crimson_suspense" or comp_mode == "spotlight_focus" else 140.0)
            cam_keys.append({"time": round(max(st + 0.4, en - 0.18), 3), "pos": [cam_poi_x, round(cy - 12.0, 1), push_z], "poi": [cam_poi_x, round(cy - 12.0, 1), 0.0]})

            timing_anchors.append({"anchor_id": f"{sc_id}_{mood_key}", "time": round(st, 3), "mood": mood_key})
            scenes_list.append({
                "scene_id": sc_id,
                "intent": sub_beats[0].get("intent") or comp_mode,
                "headline": sc["headline"],
                "mood": mood_key,
                "composition_mode": comp_mode,
                "continuity": sc["continuity"],
                "time": {"start": round(st, 3), "end": round(en, 3)},
                "camera": {"start_z": base_z, "end_z": push_z, "poi_x": cam_poi_x},
                "assets": scene_assets_out,
                "relationships": scene_rels_out,
            })

        tool_reqs.update(["bezier_path", "trim_paths", "arrow_path", "masks", "camera_motion", "text_animators", "blur", "distortion"])
        cam = {"enabled": True, "mode": "scene_breathing_2_5d", "zoom": 1800.0, "preset": "35mm", "keyframes": cam_keys}
        lighting = {"enabled": False, "lights": [], "sweeps": [], "drop_shadows": True}
        return cam, lighting, True, "editorial_scene_choreography_v5", bg_timeline, scenes_list, relationships

    def refine_scene_graph_from_qa(self, sg: Dict[str, Any], qa_report: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """Apply targeted non-destructive visual improvements based on `creative_quality_report` findings."""
        refined = copy.deepcopy(sg)
        actions: List[str] = []
        codes = {f.get("code") for f in qa_report.get("findings", [])}

        if "STATIC_FROZEN_ANIMATION" in codes or "SUBTLE_MOTION" in codes:
            cam = refined.setdefault("camera", {"enabled": True, "keyframes": []})
            keys = cam.get("keyframes", [])
            if len(keys) >= 2:
                keys[-1]["pos"][2] = float(keys[-1]["pos"][2]) + 220.0
                keys[-1]["pos"][0] = float(keys[-1]["pos"][0]) + 110.0
                actions.append("Amplified camera push/pan delta to eliminate static frame risk.")

        if "WHITE_BLOWOUT" in codes:
            for fx in refined.get("vfx", []):
                if str(fx.get("type", "")).lower() == "glow":
                    fx["type"] = "Light Sweep"
                    fx["intensity"] = 0.55
            actions.append("Replaced intense Glow with soft Light Sweep to curb white glare.")

        if "EDGE_CLIPPING_RISK" in codes:
            margin_x = 120.0
            w = float(refined.get("width", 1920))
            h = float(refined.get("height", 1080))
            for tb in refined.get("typography", []):
                pos = tb.get("position", [w / 2.0, min(260.0, h * 0.85)])
                tb["position"] = [max(margin_x, min(w - margin_x, float(pos[0]))), max(120.0, min(h - 140.0, float(pos[1])))]
            actions.append("Tightened typography safe margins inside viewport.")

        return refined, actions
