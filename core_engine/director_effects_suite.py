"""Director Effects Suite for EffectCraft Motion Graphics.
Curated, calibrated, and production-tested motion effects based on list_effects.md:
- 1. Camera & Lighting: 3D Camera Push/Pan, Neon Glow, CC Light Sweep, CC Light Rays, CC Light Burst Flash.
- 2. Blur & Focus: Directional Motion Blur, Gaussian Blur, CC Radial Fast Blur.
- 3. Kinetic Physics: Continuous Idle Floating / Organic Breathing, Audio Scale Punch.
- 4. Energy & Simulation: Calibrated Radio Waves Shockwave Rings, Advanced Lightning Flash.
- 5. Transition & Kinetic: Style 1 RTL Handwriting with Glowing Pen Nib, Directional Flow.
"""

import math
from typing import Dict, List, Any, Optional, Tuple

class DirectorEffectsSuite:
    """Master director toolkit to inject calibrated professional effects into EffectCraft JSX."""

    @staticmethod
    def apply_neon_glow(layer_var: str, color_rgb: Tuple[float, float, float] = (0.176, 0.831, 0.749), radius: int = 24, intensity: float = 1.5) -> List[str]:
        """Compound Effect: Authentic Neon Light (Glow + Radial Shadow / Aura)."""
        r, g, b = color_rgb
        return [
            f"// --- Director Effect: Neon Glow ---",
            f"var fxGlow_{layer_var} = {layer_var}.property('Effects').addProperty('Glow');",
            f"fxGlow_{layer_var}.property('Glow Radius').setValue({radius});",
            f"fxGlow_{layer_var}.property('Glow Intensity').setValue({intensity:.2f});",
            f"fxGlow_{layer_var}.property('Glow Threshold').setValue(40.0);",
            f"var fxShadow_{layer_var} = {layer_var}.property('Effects').addProperty('Drop Shadow');",
            f"fxShadow_{layer_var}.property('Shadow Color').setValue([{r}, {g}, {b}, 1.0]);",
            f"fxShadow_{layer_var}.property('Opacity').setValue(75.0);",
            f"fxShadow_{layer_var}.property('Distance').setValue(0.0);",
            f"fxShadow_{layer_var}.property('Softness').setValue({radius * 1.5:.1f});",
        ]

    @staticmethod
    def apply_light_sweep(layer_var: str, start_t: float, duration: float = 0.45, angle: float = -35.0, width: int = 24, intensity: float = 22.0, color_rgb: Optional[Tuple[float, float, float]] = None) -> List[str]:
        """Kinetic Effect: Soft, refined CC Light Sweep passing gently across element bounds without harsh glare."""
        en_t = start_t + duration
        r, g, b = color_rgb if color_rgb else (0.90, 0.92, 0.95)
        return [
            f"// --- Director Effect: Soft CC Light Sweep ({start_t:.2f}s -> {en_t:.2f}s) ---",
            f"var fxSweep_{layer_var} = {layer_var}.property('Effects').addProperty('CC Light Sweep');",
            f"fxSweep_{layer_var}.property('Direction').setValue({angle});",
            f"fxSweep_{layer_var}.property('Width').setValue({width});",
            f"fxSweep_{layer_var}.property('Sweep Intensity').setValue({intensity});",
            f"fxSweep_{layer_var}.property('Edge Intensity').setValue(8.0);",
            f"fxSweep_{layer_var}.property('Light Color').setValue([{r}, {g}, {b}, 1.0]);",
            f"var lw_{layer_var} = {layer_var}.width || 300;",
            f"var lh_{layer_var} = {layer_var}.height || 300;",
            f"var pSweep_{layer_var} = fxSweep_{layer_var}.property('Center');",
            f"pSweep_{layer_var}.setValueAtTime({start_t:.2f}, [-60, lh_{layer_var} / 2.0]);",
            f"pSweep_{layer_var}.setValueAtTime({en_t:.2f}, [lw_{layer_var} + 60, lh_{layer_var} / 2.0]);",
        ]

    @staticmethod
    def apply_light_burst_flash(layer_var: str, burst_time: float, duration: float = 0.35, peak_ray_length: float = 35.0, peak_intensity: float = 220.0) -> List[str]:
        """Kinetic Impact Flash: CC Light Burst 2.5 explosive flare on impacts/reveals."""
        t0 = burst_time
        t_peak = t0 + 0.08
        t1 = t0 + duration
        return [
            f"// --- Director Effect: Kinetic Light Burst Flash at {t0:.2f}s ---",
            f"var fxBurst_{layer_var} = {layer_var}.property('Effects').addProperty('CC Light Burst 2.5');",
            f"var lw_{layer_var} = {layer_var}.width || 300;",
            f"var lh_{layer_var} = {layer_var}.height || 300;",
            f"fxBurst_{layer_var}.property('Center').setValue([lw_{layer_var} / 2.0, lh_{layer_var} / 2.0]);",
            f"var bRay_{layer_var} = fxBurst_{layer_var}.property('Ray Length');",
            f"bRay_{layer_var}.setValueAtTime({t0:.2f}, 0.0);",
            f"bRay_{layer_var}.setValueAtTime({t_peak:.2f}, {peak_ray_length});",
            f"bRay_{layer_var}.setValueAtTime({t1:.2f}, 0.0);",
            f"var bInten_{layer_var} = fxBurst_{layer_var}.property('Intensity');",
            f"bInten_{layer_var}.setValueAtTime({t0:.2f}, 100.0);",
            f"bInten_{layer_var}.setValueAtTime({t_peak:.2f}, {peak_intensity});",
            f"bInten_{layer_var}.setValueAtTime({t1:.2f}, 100.0);",
        ]

    @staticmethod
    def apply_scale_punch(layer_var: str, punch_time: float, base_scale: int = 100, punch_multiplier: float = 1.25, duration: float = 0.35, base_pos: Optional[List[int]] = None) -> List[str]:
        """Emphasis Effect: Audio-synchronized Scale Punch & Micro-Impact Shake."""
        peak_scale = int(base_scale * punch_multiplier)
        t0 = punch_time
        lines = [
            f"// --- Director Effect: Audio Scale Punch at {t0:.2f}s ---",
            f"var sProp_{layer_var} = {layer_var}.property('Transform').property('Scale');",
            f"sProp_{layer_var}.setValueAtTime({t0:.2f}, [{base_scale}, {base_scale}, 100]);",
            f"sProp_{layer_var}.setValueAtTime({t0 + 0.10:.2f}, [{peak_scale}, {peak_scale}, 100]);",
            f"sProp_{layer_var}.setValueAtTime({t0 + duration:.2f}, [{base_scale}, {base_scale}, 100]);",
        ]
        if base_pos:
            bx, by = base_pos[0], base_pos[1]
            lines.extend([
                f"var pProp_{layer_var} = {layer_var}.property('Transform').property('Position');",
                f"pProp_{layer_var}.setValueAtTime({t0:.2f}, [{bx}, {by}, 0]);",
                f"pProp_{layer_var}.setValueAtTime({t0 + 0.05:.2f}, [{bx + 14}, {by - 10}, 0]);",
                f"pProp_{layer_var}.setValueAtTime({t0 + 0.12:.2f}, [{bx - 12}, {by + 8}, 0]);",
                f"pProp_{layer_var}.setValueAtTime({t0 + 0.20:.2f}, [{bx + 6}, {by - 4}, 0]);",
                f"pProp_{layer_var}.setValueAtTime({t0 + duration:.2f}, [{bx}, {by}, 0]);",
            ])
        return lines

    @staticmethod
    def apply_idle_floating(layer_var: str, start_t: float, end_t: float, base_pos: Tuple[int, int], base_scale: int, bob_px: int = 7, cycle_sec: float = 2.4) -> List[str]:
        """Continuous Kinetic Physics: Subtle organic floating drift so assets never sit frozen."""
        bx, by = base_pos
        lines = [
            f"// --- Continuous Floating Idle Drift ({start_t:.2f}s -> {end_t:.2f}s) ---",
            f"var pIdle_{layer_var} = {layer_var}.property('Transform').property('Position');",
            f"var sIdle_{layer_var} = {layer_var}.property('Transform').property('Scale');",
        ]
        t = start_t
        while t < end_t:
            t_mid1 = min(t + cycle_sec * 0.25, end_t)
            t_mid2 = min(t + cycle_sec * 0.75, end_t)
            t_next = min(t + cycle_sec, end_t)
            lines.append(f"pIdle_{layer_var}.setValueAtTime({t:.2f}, [{bx}, {by}, 0]);")
            lines.append(f"pIdle_{layer_var}.setValueAtTime({t_mid1:.2f}, [{bx}, {by - bob_px}, 0]);")
            lines.append(f"pIdle_{layer_var}.setValueAtTime({t_mid2:.2f}, [{bx}, {by + bob_px}, 0]);")
            
            lines.append(f"sIdle_{layer_var}.setValueAtTime({t:.2f}, [{base_scale}, {base_scale}, 100]);")
            lines.append(f"sIdle_{layer_var}.setValueAtTime({t_mid1:.2f}, [{base_scale + 2}, {base_scale + 2}, 100]);")
            
            if t_next >= end_t:
                lines.append(f"pIdle_{layer_var}.setValueAtTime({end_t:.2f}, [{bx}, {by}, 0]);")
                lines.append(f"sIdle_{layer_var}.setValueAtTime({end_t:.2f}, [{base_scale}, {base_scale}, 100]);")
                break
            t = t_next
        return lines

    @staticmethod
    def apply_radio_waves(layer_var: str, start_t: float, end_t: float, wave_color: Tuple[float, float, float] = (0.2, 0.8, 1.0)) -> List[str]:
        """Simulation Effect: Expanding Radio Waves from layer center."""
        r, g, b = wave_color
        return [
            f"// --- Kinetic Radio Waves ({start_t:.2f}s -> {end_t:.2f}s) ---",
            f"var fxWave_{layer_var} = {layer_var}.property('Effects').addProperty('Radio Waves');",
            f"var lw_{layer_var} = {layer_var}.width || 300;",
            f"var lh_{layer_var} = {layer_var}.height || 300;",
            f"fxWave_{layer_var}.property('Producer Point').setValue([lw_{layer_var} / 2.0, lh_{layer_var} / 2.0]);",
            f"fxWave_{layer_var}.property('Wave Motion').property('Expansion').setValue(160);",
            f"fxWave_{layer_var}.property('Wave Motion').property('Frequency').setValue(2.0);",
            f"fxWave_{layer_var}.property('Wave Motion').property('Velocity').setValue(0.0);",
            f"fxWave_{layer_var}.property('Wave Motion').property('Lifespan (sec)').setValue(1.8);",
            f"fxWave_{layer_var}.property('Stroke').property('Color').setValue([{r}, {g}, {b}, 1.0]);",
            f"fxWave_{layer_var}.property('Stroke').property('Start Width').setValue(4.0);",
            f"fxWave_{layer_var}.property('Stroke').property('End Width').setValue(1.0);",
            f"fxWave_{layer_var}.property('Stroke').property('Fade-out Time').setValue(1.2);",
        ]

    @staticmethod
    def apply_directional_flow(layer_var: str, start_t: float, duration: float = 0.40, target_pos: Tuple[int, int] = (960, 540), base_scale: int = 100, dx: int = 250) -> List[str]:
        """Entrance Effect: Directional Slide with High Velocity and Directional Motion Blur."""
        en_t = start_t + duration
        bx, by = target_pos
        init_x = bx - dx if bx < 960 else bx + dx
        angle = 0.0 if bx < 960 else 180.0
        return [
            f"// --- Director Effect: Directional Flow Entrance ({start_t:.2f}s -> {en_t:.2f}s) ---",
            f"var pProp_{layer_var} = {layer_var}.property('Transform').property('Position');",
            f"pProp_{layer_var}.setValueAtTime({start_t:.2f}, [{init_x}, {by}, 0]);",
            f"pProp_{layer_var}.setValueAtTime({en_t:.2f}, [{bx}, {by}, 0]);",
            f"var sProp_{layer_var} = {layer_var}.property('Transform').property('Scale');",
            f"sProp_{layer_var}.setValueAtTime({start_t:.2f}, [{int(base_scale * 0.85)}, {int(base_scale * 0.85)}, 100]);",
            f"sProp_{layer_var}.setValueAtTime({en_t:.2f}, [{base_scale}, {base_scale}, 100]);",
            f"var fxBlur_{layer_var} = {layer_var}.property('Effects').addProperty('Directional Blur');",
            f"fxBlur_{layer_var}.property('Direction').setValue({angle});",
            f"var blurLen_{layer_var} = fxBlur_{layer_var}.property('Blur Length');",
            f"blurLen_{layer_var}.setValueAtTime({start_t:.2f}, 24);",
            f"blurLen_{layer_var}.setValueAtTime({en_t:.2f}, 0);",
        ]

    @staticmethod
    def apply_radial_fast_blur(layer_var: str, start_t: float, end_t: float, max_amount: float = 35.0) -> List[str]:
        """Blur Effect: CC Radial Fast Blur for sudden shocks and transitions."""
        return [
            f"// --- Director Effect: CC Radial Fast Blur ({start_t:.2f}s -> {end_t:.2f}s) ---",
            f"var fxRBlur_{layer_var} = {layer_var}.property('Effects').addProperty('CC Radial Fast Blur');",
            f"var rAmt_{layer_var} = fxRBlur_{layer_var}.property('Amount');",
            f"rAmt_{layer_var}.setValueAtTime({start_t:.2f}, {max_amount});",
            f"rAmt_{layer_var}.setValueAtTime({end_t:.2f}, 0.0);",
        ]

    @staticmethod
    def apply_lightning_flash(layer_var: str, start_t: float, duration: float = 0.40) -> List[str]:
        """Generate Effect: Advanced Lightning realistic electric synapse spark."""
        t0 = start_t
        t_peak = t0 + 0.08
        t1 = t0 + duration
        return [
            f"// --- Dynamic Electric Synapse Arc ({t0:.2f}s -> {t1:.2f}s) ---",
            f"var fxLightn_{layer_var} = {layer_var}.property('Effects').addProperty('Advanced Lightning');",
            f"var lw_{layer_var} = {layer_var}.width || 300;",
            f"var lh_{layer_var} = {layer_var}.height || 300;",
            f"fxLightn_{layer_var}.property('Origin').setValue([lw_{layer_var} * 0.60, lh_{layer_var} * 0.45]);",
            f"fxLightn_{layer_var}.property('Direction').setValue([lw_{layer_var} * 0.78, lh_{layer_var} * 0.40]);",
            f"fxLightn_{layer_var}.property('Lightning Type').setValue(1);",
            f"fxLightn_{layer_var}.property('Turbulence').setValue(0.20);",
            f"fxLightn_{layer_var}.property('Forking').setValue(3.0);",
            f"var core_{layer_var} = fxLightn_{layer_var}.property('Core Settings');",
            f"core_{layer_var}.property('Core Radius').setValue(0.60);",
            f"core_{layer_var}.property('Core Color').setValue([0.92, 0.98, 1.0, 1.0]);",
            f"var coreOp_{layer_var} = core_{layer_var}.property('Core Opacity');",
            f"coreOp_{layer_var}.setValueAtTime({t0:.2f}, 0.0);",
            f"coreOp_{layer_var}.setValueAtTime({t_peak:.2f}, 25.0);",
            f"coreOp_{layer_var}.setValueAtTime({t1:.2f}, 0.0);",
            f"var glow_{layer_var} = fxLightn_{layer_var}.property('Glow Settings');",
            f"glow_{layer_var}.property('Glow Radius').setValue(4.5);",
            f"glow_{layer_var}.property('Glow Color').setValue([0.25, 0.75, 1.0, 1.0]);",
            f"var glowOp_{layer_var} = glow_{layer_var}.property('Glow Opacity');",
            f"glowOp_{layer_var}.setValueAtTime({t0:.2f}, 0.0);",
            f"glowOp_{layer_var}.setValueAtTime({t_peak:.2f}, 20.0);",
            f"glowOp_{layer_var}.setValueAtTime({t1:.2f}, 0.0);",
            f"var lCond_{layer_var} = fxLightn_{layer_var}.property('Conductivity State');",
            f"lCond_{layer_var}.setValueAtTime({t0:.2f}, 1.0);",
            f"lCond_{layer_var}.setValueAtTime({t1:.2f}, 25.0);",
        ]

    @staticmethod
    def apply_camera_dolly_pan(comp_var: str, start_t: float, end_t: float, zoom_start: float = 1.0, zoom_end: float = 1.08, center_start: Tuple[int, int] = (960, 540), center_end: Tuple[int, int] = (960, 540)) -> List[str]:
        """Camera Movement: 3D Dolly Zoom & Pan using native EffectCraft camera."""
        cam_id = f"Cam_{int(start_t * 10)}"
        init_z = -2666.0 / zoom_start
        end_z = -2666.0 / zoom_end
        return [
            f"// --- Director Camera Dolly/Pan: {start_t:.2f}s -> {end_t:.2f}s (Zoom: {zoom_start} -> {zoom_end}) ---",
            f"var {cam_id} = {comp_var}.layers.addCamera('{cam_id}', [{center_start[0]}, {center_start[1]}]);",
            f"{cam_id}.inPoint = {start_t:.2f};",
            f"{cam_id}.outPoint = {end_t:.2f};",
            f"var {cam_id}_pos = {cam_id}.property('Transform').property('Position');",
            f"{cam_id}_pos.setValueAtTime({start_t:.2f}, [{center_start[0]}, {center_start[1]}, {init_z:.1f}]);",
            f"{cam_id}_pos.setValueAtTime({end_t:.2f}, [{center_end[0]}, {center_end[1]}, {end_z:.1f}]);",
        ]

    @staticmethod
    def apply_color_tint_flash(layer_var: str, flash_time: float, color_rgb: Tuple[float, float, float] = (0.2, 0.8, 1.0), duration: float = 0.22, peak_amount: float = 100.0) -> List[str]:
        """Chromatic Flash: Vibrant color tint flash on impact, revelations, or entrances."""
        r, g, b = color_rgb
        t0 = flash_time
        t_peak = t0 + 0.05
        t1 = t0 + duration
        return [
            f"// --- Director Effect: Color Tint Flash at {t0:.2f}s ---",
            f"var fxTint_{layer_var} = {layer_var}.property('Effects').addProperty('Tint');",
            f"fxTint_{layer_var}.property('Map White To').setValue([{r}, {g}, {b}, 1.0]);",
            f"var tAmt_{layer_var} = fxTint_{layer_var}.property('Amount to Tint');",
            f"tAmt_{layer_var}.setValueAtTime({t0:.2f}, 0.0);",
            f"tAmt_{layer_var}.setValueAtTime({t_peak:.2f}, {peak_amount});",
            f"tAmt_{layer_var}.setValueAtTime({t1:.2f}, 0.0);",
        ]

    @staticmethod
    def apply_white_strobe_flash(layer_var: str, flash_time: float, duration: float = 0.16) -> List[str]:
        """Lighting Strobe: High-contrast strobe flash that preserves crisp dark ink lines."""
        t0 = flash_time
        t_peak = t0 + 0.03
        t1 = t0 + duration
        return [
            f"// --- Director Effect: High-Contrast White Strobe Flash at {t0:.2f}s ---",
            f"var fxStrobe_{layer_var} = {layer_var}.property('Effects').addProperty('Tint');",
            f"fxStrobe_{layer_var}.property('Map White To').setValue([1.0, 1.0, 1.0, 1.0]);",
            f"fxStrobe_{layer_var}.property('Map Black To').setValue([0.05, 0.05, 0.05, 1.0]);",
            f"var sAmt_{layer_var} = fxStrobe_{layer_var}.property('Amount to Tint');",
            f"sAmt_{layer_var}.setValueAtTime({t0:.2f}, 0.0);",
            f"sAmt_{layer_var}.setValueAtTime({t_peak:.2f}, 55.0);",
            f"sAmt_{layer_var}.setValueAtTime({t1:.2f}, 0.0);",
        ]

    @staticmethod
    def apply_squash_and_stretch_drop(layer_var: str, start_t: float, target_pos: Tuple[int, int] = (960, 540), base_scale: int = 100) -> List[str]:
        """Physics Entrance: Gravity Drop with squash & stretch bouncy impact."""
        bx, by = target_pos
        return [
            f"// --- Director Effect: Squash & Stretch Gravity Drop ({start_t:.2f}s) ---",
            f"var pProp_{layer_var} = {layer_var}.property('Transform').property('Position');",
            f"pProp_{layer_var}.setValueAtTime({start_t:.2f}, [{bx}, {by - 420}, 0]);",
            f"pProp_{layer_var}.setValueAtTime({start_t + 0.32:.2f}, [{bx}, {by}, 0]);",
            f"pProp_{layer_var}.setValueAtTime({start_t + 0.44:.2f}, [{bx}, {by - 45}, 0]);",
            f"pProp_{layer_var}.setValueAtTime({start_t + 0.58:.2f}, [{bx}, {by}, 0]);",
            f"var sProp_{layer_var} = {layer_var}.property('Transform').property('Scale');",
            f"sProp_{layer_var}.setValueAtTime({start_t:.2f}, [{int(base_scale * 0.85)}, {int(base_scale * 1.25)}, 100]);",
            f"sProp_{layer_var}.setValueAtTime({start_t + 0.32:.2f}, [{int(base_scale * 1.30)}, {int(base_scale * 0.70)}, 100]);",
            f"sProp_{layer_var}.setValueAtTime({start_t + 0.44:.2f}, [{int(base_scale * 0.92)}, {int(base_scale * 1.10)}, 100]);",
            f"sProp_{layer_var}.setValueAtTime({start_t + 0.58:.2f}, [{base_scale}, {base_scale}, 100]);",
        ]

    @staticmethod
    def apply_wiggle_attention(layer_var: str, wiggle_time: float, duration: float = 0.45, max_angle: float = 12.0) -> List[str]:
        """Cartoon Dynamics: Playful jiggle/wiggle to draw instant visual focus."""
        t0 = wiggle_time
        return [
            f"// --- Director Effect: Attention Jiggle/Wiggle at {t0:.2f}s ---",
            f"var rProp_{layer_var} = {layer_var}.property('Transform').property('Rotation');",
            f"rProp_{layer_var}.setValueAtTime({t0:.2f}, 0);",
            f"rProp_{layer_var}.setValueAtTime({t0 + 0.08:.2f}, {-max_angle});",
            f"rProp_{layer_var}.setValueAtTime({t0 + 0.18:.2f}, {max_angle * 0.8});",
            f"rProp_{layer_var}.setValueAtTime({t0 + 0.28:.2f}, {-max_angle * 0.4});",
            f"rProp_{layer_var}.setValueAtTime({t0 + duration:.2f}, 0);",
        ]

    @staticmethod
    def apply_fly_away_exit(layer_var: str, start_t: float, current_pos: Tuple[int, int] = (960, 540), duration: float = 0.45) -> List[str]:
        """Exit Effect: Fast upward launch with directional motion blur and fade."""
        bx, by = current_pos
        en_t = start_t + duration
        return [
            f"// --- Director Effect: Fly Away Upward Exit ({start_t:.2f}s -> {en_t:.2f}s) ---",
            f"var pProp_{layer_var} = {layer_var}.property('Transform').property('Position');",
            f"pProp_{layer_var}.setValueAtTime({start_t:.2f}, [{bx}, {by}, 0]);",
            f"pProp_{layer_var}.setValueAtTime({en_t:.2f}, [{bx}, {by - 550}, 0]);",
            f"var fxBlur_{layer_var} = {layer_var}.property('Effects').addProperty('Directional Blur');",
            f"fxBlur_{layer_var}.property('Direction').setValue(90.0);",
            f"var blurLen_{layer_var} = fxBlur_{layer_var}.property('Blur Length');",
            f"blurLen_{layer_var}.setValueAtTime({start_t:.2f}, 0);",
            f"blurLen_{layer_var}.setValueAtTime({en_t:.2f}, 35);",
            f"var opProp_{layer_var} = {layer_var}.property('Transform').property('Opacity');",
            f"opProp_{layer_var}.setValueAtTime({start_t + 0.15:.2f}, 100);",
            f"opProp_{layer_var}.setValueAtTime({en_t:.2f}, 0);",
        ]

    @staticmethod
    def apply_camera_border_flash(comp_var: str, flash_time: float, vignette_type: str = "red", duration: float = 0.60, peak_opacity: float = 45.0, pulses: int = 2) -> List[str]:
        """Camera Edge Pulse: Subtle Rectangular 16:9 Camera Border Glow (Red Danger / Cyan Alert)."""
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        v_color = "red" if vignette_type in ["red", "crimson", "amber", "danger"] else "cyan"
        border_png = (root / "assets" / "vignettes" / f"camera_border_glow_{v_color}.png").as_posix()
        v_id = f"Vig_{int(flash_time * 100)}"
        t0 = flash_time
        lines = [
            f"// --- Camera Edge Rectangular Border Glow Pulse at {t0:.2f}s ---",
            f"var io_{v_id} = new ImportOptions(new File('{border_png}'));",
            f"var it_{v_id} = app.project.importFile(io_{v_id});",
            f"var {v_id} = {comp_var}.layers.add(it_{v_id});",
            f"{v_id}.inPoint = {t0:.2f};",
            f"{v_id}.outPoint = {t0 + duration:.2f};",
            f"{v_id}.property('Transform').property('Position').setValue([960, 540, 0]);",
            f"var op_{v_id} = {v_id}.property('Transform').property('Opacity');",
        ]
        if pulses == 2:
            t_p1 = t0 + 0.10
            t_dip = t0 + 0.24
            t_p2 = t0 + 0.36
            t_end = t0 + duration
            lines.extend([
                f"op_{v_id}.setValueAtTime({t0:.2f}, 0);",
                f"op_{v_id}.setValueAtTime({t_p1:.2f}, {peak_opacity});",
                f"op_{v_id}.setValueAtTime({t_dip:.2f}, {peak_opacity * 0.30:.1f});",
                f"op_{v_id}.setValueAtTime({t_p2:.2f}, {peak_opacity * 0.75:.1f});",
                f"op_{v_id}.setValueAtTime({t_end:.2f}, 0);",
            ])
        else:
            t_p = t0 + duration * 0.25
            lines.extend([
                f"op_{v_id}.setValueAtTime({t0:.2f}, 0);",
                f"op_{v_id}.setValueAtTime({t_p:.2f}, {peak_opacity});",
                f"op_{v_id}.setValueAtTime({t0 + duration:.2f}, 0);",
            ])
        return lines

    @staticmethod
    def apply_whip_motion_entrance(layer_var: str, start_t: float, target_pos: Tuple[int, int], base_scale: int, duration: float = 0.28, from_right: bool = True) -> List[str]:
        """Template 07: Whip Motion Entrance with ultra-fast snap and heavy directional blur."""
        bx, by = target_pos
        dx = 520 if from_right else -520
        angle = 180.0 if from_right else 0.0
        en_t = start_t + duration
        return [
            f"// --- Template 07: Whip Motion Entrance ({start_t:.2f}s -> {en_t:.2f}s) ---",
            f"var pProp_{layer_var} = {layer_var}.property('Transform').property('Position');",
            f"pProp_{layer_var}.setValueAtTime({start_t:.2f}, [{bx + dx}, {by}, 0]);",
            f"pProp_{layer_var}.setValueAtTime({en_t:.2f}, [{bx}, {by}, 0]);",
            f"var sProp_{layer_var} = {layer_var}.property('Transform').property('Scale');",
            f"sProp_{layer_var}.setValueAtTime({start_t:.2f}, [{int(base_scale * 0.70)}, {int(base_scale * 0.70)}, 100]);",
            f"sProp_{layer_var}.setValueAtTime({en_t:.2f}, [{base_scale}, {base_scale}, 100]);",
            f"var fxBlur_{layer_var} = {layer_var}.property('Effects').addProperty('Directional Blur');",
            f"fxBlur_{layer_var}.property('Direction').setValue({angle});",
            f"var blLen_{layer_var} = fxBlur_{layer_var}.property('Blur Length');",
            f"blLen_{layer_var}.setValueAtTime({start_t:.2f}, 65);",
            f"blLen_{layer_var}.setValueAtTime({en_t:.2f}, 0);",
            f"var opProp_{layer_var} = {layer_var}.property('Transform').property('Opacity');",
            f"opProp_{layer_var}.setValueAtTime({start_t:.2f}, 0);",
            f"opProp_{layer_var}.setValueAtTime({start_t + 0.10:.2f}, 100);",
        ]

    @staticmethod
    def apply_rotation_spin_reveal(layer_var: str, start_t: float, target_pos: Tuple[int, int], base_scale: int, duration: float = 0.42, start_angle: float = -90.0) -> List[str]:
        """Template 19: Rotation Spin Reveal with angular momentum and scale pop."""
        en_t = start_t + duration
        t_overshoot = start_t + duration * 0.75
        s_pop = int(base_scale * 1.14)
        return [
            f"// --- Template 19: Rotation Spin Reveal ({start_t:.2f}s -> {en_t:.2f}s) ---",
            f"var rProp_{layer_var} = {layer_var}.property('Transform').property('Rotation');",
            f"rProp_{layer_var}.setValueAtTime({start_t:.2f}, {start_angle});",
            f"rProp_{layer_var}.setValueAtTime({t_overshoot:.2f}, {-start_angle * 0.08});",
            f"rProp_{layer_var}.setValueAtTime({en_t:.2f}, 0);",
            f"var sProp_{layer_var} = {layer_var}.property('Transform').property('Scale');",
            f"sProp_{layer_var}.setValueAtTime({start_t:.2f}, [0, 0, 100]);",
            f"sProp_{layer_var}.setValueAtTime({t_overshoot:.2f}, [{s_pop}, {s_pop}, 100]);",
            f"sProp_{layer_var}.setValueAtTime({en_t:.2f}, [{base_scale}, {base_scale}, 100]);",
            f"var opProp_{layer_var} = {layer_var}.property('Transform').property('Opacity');",
            f"opProp_{layer_var}.setValueAtTime({start_t:.2f}, 0);",
            f"opProp_{layer_var}.setValueAtTime({start_t + 0.15:.2f}, 100);",
        ]

    @staticmethod
    def apply_elastic_overshoot(layer_var: str, start_t: float, base_scale: int, duration: float = 0.55) -> List[str]:
        """Template 20: Multi-stage Elastic Spring Overshoot."""
        s1 = int(base_scale * 1.28)
        s2 = int(base_scale * 0.90)
        s3 = int(base_scale * 1.05)
        return [
            f"// --- Template 20: Elastic Overshoot ({start_t:.2f}s) ---",
            f"var sProp_{layer_var} = {layer_var}.property('Transform').property('Scale');",
            f"sProp_{layer_var}.setValueAtTime({start_t:.2f}, [0, 0, 100]);",
            f"sProp_{layer_var}.setValueAtTime({start_t + 0.25:.2f}, [{s1}, {s1}, 100]);",
            f"sProp_{layer_var}.setValueAtTime({start_t + 0.38:.2f}, [{s2}, {s2}, 100]);",
            f"sProp_{layer_var}.setValueAtTime({start_t + 0.48:.2f}, [{s3}, {s3}, 100]);",
            f"sProp_{layer_var}.setValueAtTime({start_t + duration:.2f}, [{base_scale}, {base_scale}, 100]);",
            f"var opProp_{layer_var} = {layer_var}.property('Transform').property('Opacity');",
            f"opProp_{layer_var}.setValueAtTime({start_t:.2f}, 0);",
            f"opProp_{layer_var}.setValueAtTime({start_t + 0.12:.2f}, 100);",
        ]

    @staticmethod
    def apply_card_stack_entrance(layer_var: str, start_t: float, target_pos: Tuple[int, int], base_scale: int, duration: float = 0.40) -> List[str]:
        """Template 15: Card Stack Transition sliding up from bottom deck with angular settling."""
        bx, by = target_pos
        en_t = start_t + duration
        return [
            f"// --- Template 15: Card Stack Transition ({start_t:.2f}s -> {en_t:.2f}s) ---",
            f"var pProp_{layer_var} = {layer_var}.property('Transform').property('Position');",
            f"pProp_{layer_var}.setValueAtTime({start_t:.2f}, [{bx}, {by + 190}, 0]);",
            f"pProp_{layer_var}.setValueAtTime({en_t:.2f}, [{bx}, {by}, 0]);",
            f"var rProp_{layer_var} = {layer_var}.property('Transform').property('Rotation');",
            f"rProp_{layer_var}.setValueAtTime({start_t:.2f}, -4.5);",
            f"rProp_{layer_var}.setValueAtTime({en_t:.2f}, 0);",
            f"var sProp_{layer_var} = {layer_var}.property('Transform').property('Scale');",
            f"sProp_{layer_var}.setValueAtTime({start_t:.2f}, [{int(base_scale * 0.90)}, {int(base_scale * 0.90)}, 100]);",
            f"sProp_{layer_var}.setValueAtTime({en_t:.2f}, [{base_scale}, {base_scale}, 100]);",
            f"var opProp_{layer_var} = {layer_var}.property('Transform').property('Opacity');",
            f"opProp_{layer_var}.setValueAtTime({start_t:.2f}, 0);",
            f"opProp_{layer_var}.setValueAtTime({start_t + 0.14:.2f}, 100);",
        ]

    @staticmethod
    def apply_mask_reveal_wipe(layer_var: str, start_t: float, duration: float = 0.45, wipe_angle: float = 90.0) -> List[str]:
        """Template 05: Mask Reveal / Linear Wipe Transition across layer."""
        en_t = start_t + duration
        return [
            f"// --- Template 05: Mask Reveal Linear Wipe ({start_t:.2f}s -> {en_t:.2f}s) ---",
            f"var fxWipe_{layer_var} = {layer_var}.property('Effects').addProperty('Linear Wipe');",
            f"fxWipe_{layer_var}.property('Wipe Angle').setValue({wipe_angle});",
            f"fxWipe_{layer_var}.property('Feather').setValue(24);",
            f"var wComp_{layer_var} = fxWipe_{layer_var}.property('Transition Completion');",
            f"wComp_{layer_var}.setValueAtTime({start_t:.2f}, 100);",
            f"wComp_{layer_var}.setValueAtTime({en_t:.2f}, 0);",
        ]

    @staticmethod
    def apply_speed_blur_transition(layer_var: str, start_t: float, duration: float = 0.35, max_blur: float = 40.0) -> List[str]:
        """Template 17: Blur Speed Transition dissolving into focus."""
        en_t = start_t + duration
        return [
            f"// --- Template 17: Speed Blur Transition ({start_t:.2f}s -> {en_t:.2f}s) ---",
            f"var fxBlur_{layer_var} = {layer_var}.property('Effects').addProperty('Directional Blur');",
            f"fxBlur_{layer_var}.property('Direction').setValue(0.0);",
            f"var blLen_{layer_var} = fxBlur_{layer_var}.property('Blur Length');",
            f"blLen_{layer_var}.setValueAtTime({start_t:.2f}, {max_blur});",
            f"blLen_{layer_var}.setValueAtTime({en_t:.2f}, 0);",
            f"var opProp_{layer_var} = {layer_var}.property('Transform').property('Opacity');",
            f"opProp_{layer_var}.setValueAtTime({start_t:.2f}, 0);",
            f"opProp_{layer_var}.setValueAtTime({en_t:.2f}, 100);",
        ]

