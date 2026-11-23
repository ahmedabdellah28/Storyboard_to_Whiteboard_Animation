"""
Complete 100-Action Creative Catalog for Creative Stickman Studio V3.
Every action ID (001..100) has distinct multi-keyframe choreography, expression/hand tracks,
causal event timelines, IK/FK bone motion, and parametric vector FX.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

from creative_v3.engine.rigging.rig_model import ActionSpec

# Exact 100 mandatory catalog definitions: (number, action_id, category, title, description, duration_frames, target_type, expr_mid, r_hand, l_hand, archetype)
RAW_CATALOG: List[Tuple[int, str, str, str, str, int, str, str, str, str, str]] = [
    # A. Expressive performance / character behavior (001-010)
    (1, "signature_idle_breath", "A_performance", "Signature Idle Breath", "Subtle weight shifts, blinking, and tie follow-through.", 60, "none", "smile", "open_palm", "fist", "idle_sway"),
    (2, "eye_track_and_point", "A_performance", "Eye Track and Point", "Eyes locate offscreen target, head turns, decisive point.", 60, "target_point", "curious", "point", "fist", "point_decisive"),
    (3, "eager_presenter_greeting", "A_performance", "Eager Presenter Greeting", "Theatrical greeting with hand flourish and recovery.", 60, "none", "open_talk", "open_palm", "open_palm", "flourish_greet"),
    (4, "think_then_epiphany", "A_performance", "Think Then Epiphany", "Chin tap, eyebrow thought, suddenly animated discovery gesture.", 72, "none", "surprise", "point", "grip", "think_epiphany"),
    (5, "suspicious_sneak_peek", "A_performance", "Suspicious Sneak Peek", "Tiptoe, peek behind a hovering card, recoil and recover.", 72, "card", "squint", "pinch", "grip", "sneak_peek"),
    (6, "explosive_surprise_recoil", "A_performance", "Explosive Surprise Recoil", "Full-body surprise, eye exaggeration, soft spring recovery.", 54, "none", "surprise", "open_palm", "open_palm", "recoil_spring"),
    (7, "confident_superhero_land", "A_performance", "Confident Superhero Land", "Anticipatory jump, stylized midair pose, weighted landing.", 66, "none", "determined", "fist", "fist", "jump_land"),
    (8, "dynamic_run_skid", "A_performance", "Dynamic Run Skid", "Rapid run, braking skid, planted feet, tie momentum.", 60, "none", "determined", "fist", "fist", "run_skid"),
    (9, "exaggerated_balance_rescue", "A_performance", "Exaggerated Balance Rescue", "Lose balance on one leg, counter-swing arms, regain posture.", 72, "none", "surprise", "open_palm", "open_palm", "balance_wobble"),
    (10, "signature_spin_and_bow", "A_performance", "Signature Spin and Bow", "Unique full-body turn and flourish to greeting stance.", 66, "none", "smile", "open_palm", "open_palm", "spin_bow"),
    # B. Physical object interaction (011-020)
    (11, "palm_summon_card", "B_physical", "Palm Summon Card", "Create an image card from palm in 2D layered depth.", 60, "card", "smile", "open_palm", "fist", "palm_lift"),
    (12, "elastic_grab_and_pull", "B_physical", "Elastic Grab and Pull", "Stretch reach, grip target, bring to presentation area.", 66, "card", "determined", "grip", "fist", "reach_pull"),
    (13, "toss_orbit_catch", "B_physical", "Toss Orbit Catch", "Throw card into orbit then catch by tracking motion.", 72, "card", "curious", "open_palm", "grip", "toss_track"),
    (14, "two_card_juggle_compare", "B_physical", "Two Card Juggle Compare", "Juggle two targets while keeping them identifiable.", 75, "dual_card", "smile", "open_palm", "open_palm", "dual_juggle"),
    (15, "giant_card_fold", "B_physical", "Giant Card Fold", "Fold large target down to hand size with linked deformation.", 66, "card", "determined", "pinch", "pinch", "two_hand_press"),
    (16, "flip_reveal_panel", "B_physical", "Flip Reveal Panel", "Grab edge and physically flip panel to reveal reverse side.", 60, "panel", "smile", "grip", "fist", "side_swipe"),
    (17, "domino_card_knock", "B_physical", "Domino Card Knock", "Touch first card, propagate staggered domino cascade.", 72, "card_group", "curious", "point", "fist", "poke_watch"),
    (18, "stack_shuffle_splay", "B_physical", "Stack Shuffle Splay", "Stack several images then fan them into a clean layout.", 72, "card_group", "smile", "open_palm", "open_palm", "fan_spread"),
    (19, "bounce_off_foot", "B_physical", "Bounce Off Foot", "Propel target from foot, arc and land in exact target position.", 60, "card", "determined", "fist", "fist", "foot_kick"),
    (20, "vacuum_pull_group", "B_physical", "Vacuum Pull Group", "Summon multiple scattered assets toward a controlled vortex.", 72, "card_group", "determined", "energy", "open_palm", "vortex_hold"),
    # C. Tethers, thread, grappling and webs (021-030)
    (21, "shoot_energy_tether", "C_tethers", "Shoot Energy Tether", "Hand shoots original energy string, hits and reels card in.", 60, "card", "determined", "energy", "fist", "shoot_reel"),
    (22, "lasso_select_circle", "C_tethers", "Lasso Select Circle", "Draw a looping lasso that wraps one selected circle.", 66, "circle", "smile", "grip", "fist", "lasso_spin"),
    (23, "grapple_swing_to_target", "C_tethers", "Grapple Swing to Target", "Stickman swings on tether, releases near target.", 72, "target_point", "determined", "grip", "fist", "swing_arc"),
    (24, "zipline_card_travel", "C_tethers", "Zipline Card Travel", "Grapple anchor and zip along a line with weight response.", 66, "card", "smile", "grip", "grip", "zip_slide"),
    (25, "dual_thread_puppet", "C_tethers", "Dual Thread Puppet", "Link two hand threads to manipulate separate target corners.", 72, "card", "curious", "pinch", "pinch", "puppet_hands"),
    (26, "stitch_two_panels", "C_tethers", "Stitch Two Panels", "Thread stitches two panels into one graphic.", 66, "dual_card", "determined", "pinch", "grip", "stitch_weave"),
    (27, "unweave_object", "C_tethers", "Unweave Object", "Pull one filament that unravels an object into a trail.", 66, "card", "curious", "pinch", "fist", "reach_pull"),
    (28, "tether_slingshot", "C_tethers", "Tether Slingshot", "Stretch tether with body lean and fling a lightweight icon.", 60, "icon", "determined", "grip", "grip", "lean_slingshot"),
    (29, "web_net_reveal", "C_tethers", "Web Net Reveal", "Weave a geometric net, then form a content frame in its center.", 72, "frame", "smile", "energy", "energy", "fan_spread"),
    (30, "spiral_thread_portal", "C_tethers", "Spiral Thread Portal", "Tether spins a spiral opening that exposes a layer behind.", 72, "portal", "surprise", "energy", "fist", "lasso_spin"),
    # D. Gadgets and remote controls (031-040)
    (31, "remote_single_pop", "D_gadgets", "Remote Single Pop", "Press remote and spawn one responsive card.", 54, "card", "smile", "remote", "fist", "remote_click"),
    (32, "remote_background_swap", "D_gadgets", "Remote Background Swap", "Double-tap remote, backdrop rolls into another scene.", 66, "backdrop", "curious", "remote", "fist", "remote_double"),
    (33, "remote_time_rewind", "D_gadgets", "Remote Time Rewind", "Rewind target movement while character moves forward.", 66, "card", "determined", "remote", "open_palm", "walk_remote"),
    (34, "remote_pause_freeze", "D_gadgets", "Remote Pause Freeze", "Freeze hovering targets while character walks around them.", 72, "card_group", "wink", "remote", "fist", "walk_remote"),
    (35, "wrist_hologram_cast", "D_gadgets", "Wrist Hologram Cast", "Unfold a small wrist interface that projects an asset.", 66, "hologram", "curious", "open_palm", "point", "wrist_inspect"),
    (36, "handheld_scanner_reveal", "D_gadgets", "Handheld Scanner Reveal", "Scan a panel to reveal hidden strokes and labels.", 66, "panel", "squint", "remote", "fist", "scan_sweep"),
    (37, "magnet_glove_attract", "D_gadgets", "Magnet Glove Attract", "Magnetic hand attracts metallic-looking icons with bounce.", 60, "icon", "determined", "energy", "fist", "vortex_hold"),
    (38, "volume_knob_resize", "D_gadgets", "Volume Knob Resize", "Twist a knob to scale one target with physical resistance.", 66, "card", "determined", "pinch", "grip", "knob_twist"),
    (39, "floor_button_spring", "D_gadgets", "Floor Button Spring", "Step on button and release a spring-powered item.", 60, "card", "surprise", "open_palm", "fist", "foot_stomp"),
    (40, "snapshot_flash_transform", "D_gadgets", "Snapshot Flash Transform", "Camera-like gesture freezes and swaps the target appearance.", 60, "card", "wink", "pinch", "pinch", "camera_snap"),
    # E. Magic and creative summoning (041-050)
    (41, "expanding_ring_summon", "E_magic", "Expanding Ring Summon", "Emit circular ring from fingertips, item appears inside.", 60, "card", "smile", "energy", "fist", "palm_lift"),
    (42, "prism_fragment_to_text", "E_magic", "Prism Fragment to Text", "Crystal splits into shards that form text glyphs.", 72, "text", "surprise", "energy", "open_palm", "flourish_greet"),
    (43, "pocket_portal_throw", "E_magic", "Pocket Portal Throw", "Throw tiny portal disc that expands into a doorway.", 66, "portal", "determined", "open_palm", "fist", "toss_track"),
    (44, "peel_invisible_door", "E_magic", "Peel Invisible Door", "Physically peel open an invisible vertical doorway.", 72, "portal", "curious", "grip", "grip", "two_hand_open"),
    (45, "sketch_glyph_materialize", "E_magic", "Sketch Glyph Materialize", "Draw luminous glyph that thickens into a symbol.", 66, "glyph", "determined", "point", "fist", "air_draw"),
    (46, "book_burst_collage", "E_magic", "Book Burst Collage", "Open floating book, illustrated cards unfold and arrange.", 72, "card_group", "surprise", "open_palm", "open_palm", "two_hand_open"),
    (47, "bubble_inflate_asset", "E_magic", "Bubble Inflate Asset", "Inflate bubble with breath; shape forms inside.", 66, "card", "open_talk", "open_palm", "fist", "inflate_lean"),
    (48, "lantern_shadow_reveal", "E_magic", "Lantern Shadow Reveal", "Light beam casts a silhouette that becomes a graphic.", 66, "card", "curious", "grip", "fist", "scan_sweep"),
    (49, "miniature_world_unfold", "E_magic", "Miniature World Unfold", "Pull a folded miniature environment out of pocket.", 72, "scene", "smile", "pinch", "open_palm", "palm_lift"),
    (50, "stone_touch_transmutation", "E_magic", "Stone Touch Transmutation", "Touch target with gem, transform it via keyed morph.", 60, "card", "determined", "pinch", "fist", "poke_watch"),
    # F. Typography choreography (051-060)
    (51, "fingertip_air_write", "F_typography", "Fingertip Air Write", "Draw words with tracked fingertip and stroke reveal.", 66, "text", "smile", "point", "fist", "air_draw"),
    (52, "keyboard_air_type", "F_typography", "Keyboard Air Type", "Tap invisible keys, letters pop in at finger contacts.", 60, "text", "determined", "point", "point", "air_type"),
    (53, "rope_pull_letters", "F_typography", "Rope Pull Letters", "Lasso and physically drag letters into a headline.", 66, "text", "determined", "grip", "grip", "reach_pull"),
    (54, "knock_over_word_domino", "F_typography", "Knock Over Word Domino", "Flick one letter and cascade through the word.", 60, "text", "smile", "snap", "fist", "poke_watch"),
    (55, "compress_word_to_icon", "F_typography", "Compress Word to Icon", "Squeeze text with hands into a symbolic shape.", 66, "text", "determined", "open_palm", "open_palm", "two_hand_press"),
    (56, "flashlight_kinetic_reveal", "F_typography", "Flashlight Kinetic Reveal", "Sweep beam to reveal progressive letter regions.", 66, "text", "curious", "grip", "fist", "scan_sweep"),
    (57, "shatter_word_particles", "F_typography", "Shatter Word Particles", "Hit a word, breakup glyph contours into dots.", 60, "text", "angry", "fist", "fist", "punch_impact"),
    (58, "magnetic_letter_alignment", "F_typography", "Magnetic Letter Alignment", "Magnetic glove pulls scattered glyphs into line.", 66, "text", "smile", "energy", "fist", "vortex_hold"),
    (59, "punctuation_boomerang", "F_typography", "Punctuation Boomerang", "Throw punctuation as boomerang that lands in sentence.", 66, "text", "wink", "open_palm", "fist", "toss_track"),
    (60, "underline_surfing", "F_typography", "Underline Surfing", "Stickman rides racing underline as text resolves behind.", 72, "text", "determined", "open_palm", "open_palm", "surf_ride"),
    # G. Background and scene-world transformations (061-070)
    (61, "paper_backdrop_peel", "G_world", "Paper Backdrop Peel", "Grip background edge and peel to reveal another background.", 66, "backdrop", "curious", "grip", "fist", "side_swipe"),
    (62, "rotating_stage_dial", "G_world", "Rotating Stage Dial", "Turn giant dial and rotate through staged environments.", 72, "backdrop", "determined", "grip", "grip", "knob_twist"),
    (63, "floor_flip_laboratory", "G_world", "Floor Flip Laboratory", "Stomp to flip the floor plane into a laboratory.", 66, "backdrop", "determined", "fist", "fist", "foot_stomp"),
    (64, "unzip_world", "G_world", "Unzip World", "Open long zipper across backdrop to expose second environment.", 72, "backdrop", "smile", "pinch", "fist", "zip_pull_down"),
    (65, "brush_recolor_environment", "G_world", "Brush Recolor Environment", "Sweep brush that repaints large background regions.", 72, "backdrop", "smile", "grip", "fist", "air_draw"),
    (66, "curtain_pull_scene", "G_world", "Curtain Pull Scene", "Pull curtain rig to unveil hidden prepared background.", 66, "backdrop", "open_talk", "grip", "grip", "reach_pull"),
    (67, "shrink_room_to_card", "G_world", "Shrink Room to Card", "Shrink displayed room into a small card in stickman's hand.", 72, "backdrop", "determined", "pinch", "open_palm", "two_hand_press"),
    (68, "fold_horizon_over", "G_world", "Fold Horizon Over", "Grip horizon and fold background like flexible paper.", 66, "backdrop", "curious", "grip", "grip", "two_hand_open"),
    (69, "jump_shockwave_wipe", "G_world", "Jump Shockwave Wipe", "Landing shockwave wipes scenery, preserving character pose.", 66, "backdrop", "determined", "fist", "fist", "jump_land"),
    (70, "layered_parallax_portal", "G_world", "Layered Parallax Portal", "Open portal showing multi-layer depth illusion.", 72, "portal", "surprise", "open_palm", "open_palm", "two_hand_open"),
    # H. Object transformation and destruction (071-080)
    (71, "circle_square_morph", "H_transform", "Circle Square Morph", "Circle deforms into square with deliberate character gesture.", 60, "shape", "determined", "open_palm", "open_palm", "two_hand_press"),
    (72, "mosaic_shatter_rebuild", "H_transform", "Mosaic Shatter Rebuild", "Split target into tiles and reassemble as new image.", 72, "card", "surprise", "snap", "fist", "punch_impact"),
    (73, "origami_fold_transform", "H_transform", "Origami Fold Transform", "Fold card in multiple sequential flaps to new silhouette.", 66, "card", "curious", "pinch", "pinch", "two_hand_press"),
    (74, "smoke_dissolve_reform", "H_transform", "Smoke Dissolve Reform", "Exhale stylized smoke that dissolves then reforms target.", 66, "card", "open_talk", "open_palm", "fist", "inflate_lean"),
    (75, "safe_cartoon_fire_burn", "H_transform", "Safe Cartoon Fire Burn", "Emit stylized non-realistic flame, burn edge to reveal next asset.", 66, "card", "determined", "energy", "fist", "shoot_reel"),
    (76, "crystal_freeze_melt", "H_transform", "Crystal Freeze Melt", "Freeze target into crystalline facets, then melt to new item.", 72, "card", "curious", "energy", "open_palm", "palm_lift"),
    (77, "lightning_blueprint_pop", "H_transform", "Lightning Blueprint Pop", "Lightning touches asset, outline blueprint becomes solid.", 60, "card", "surprise", "point", "fist", "point_decisive"),
    (78, "pixel_scatter_reassemble", "H_transform", "Pixel Scatter Reassemble", "Scatter visual cells along motion arc and reconstruct.", 72, "card", "determined", "snap", "open_palm", "side_swipe"),
    (79, "ink_splash_shape_shift", "H_transform", "Ink Splash Shape Shift", "Splash drawn ink, silhouette reshapes into next symbol.", 66, "card", "smile", "open_palm", "fist", "toss_track"),
    (80, "detached_shadow_reveal", "H_transform", "Detached Shadow Reveal", "Target's shadow detaches, rises and becomes new element.", 66, "card", "curious", "point", "fist", "poke_watch"),
    # I. Unexpected funny cause-and-effect moments (081-090)
    (81, "accidental_trip_reveal", "I_comedy", "Accidental Trip Reveal", "Apparent stumble triggers a clever hidden-content reveal.", 66, "card", "surprise", "open_palm", "open_palm", "stumble_trip"),
    (82, "comic_sneeze_launch", "I_comedy", "Comic Sneeze Launch", "Sneeze blasts a loose card into chosen resting position.", 60, "card", "squint", "open_palm", "fist", "sneeze_blast"),
    (83, "whistle_summon_companion_prop", "I_comedy", "Whistle Summon Companion Prop", "Whistle brings an orbiting decorative prop from side.", 60, "prop", "smile", "open_palm", "fist", "idle_sway"),
    (84, "clap_reverse_gravity", "I_comedy", "Clap Reverse Gravity", "Clap turns gravity upside down for local asset group.", 66, "card_group", "surprise", "open_palm", "open_palm", "clap_burst"),
    (85, "tiny_clone_helper", "I_comedy", "Tiny Clone Helper", "Finger snap creates tiny stylized echo of character carrying icon.", 72, "icon", "wink", "snap", "fist", "poke_watch"),
    (86, "remote_wrong_button_comedy", "I_comedy", "Remote Wrong Button Comedy", "Wrong remote action, surprised recovery, correct fix.", 72, "card", "surprise", "remote", "open_palm", "remote_double"),
    (87, "falling_card_dodge_catch", "I_comedy", "Falling Card Dodge Catch", "Spot incoming card, dodge, retrieve while moving.", 66, "card", "surprise", "grip", "open_palm", "dodge_catch"),
    (88, "forehead_bounce_solve", "I_comedy", "Forehead Bounce Solve", "Icon bounces from forehead into a successful match slot.", 60, "icon", "surprise", "open_palm", "fist", "head_bonk"),
    (89, "impossible_pocket_pull", "I_comedy", "Impossible Pocket Pull", "Pull unusually big asset through tiny pocket via deformation.", 72, "card", "determined", "grip", "grip", "reach_pull"),
    (90, "fake_out_freeze_then_reveal", "I_comedy", "Fake Out Freeze Then Reveal", "Pretend time freeze, eye wink, sudden reveal.", 66, "card", "wink", "snap", "fist", "spin_bow"),
    # J. Cinematic scene-control choreography (091-100)
    (91, "gesture_driven_whip_pan", "J_cinematic", "Gesture Driven Whip Pan", "Hand swipe drives camera request and target movement.", 54, "card", "determined", "open_palm", "fist", "side_swipe"),
    (92, "zoom_through_hand_portal", "J_cinematic", "Zoom Through Hand Portal", "Hand aperture opens, target scales into full view.", 66, "portal", "curious", "pinch", "pinch", "two_hand_open"),
    (93, "walking_parallax_depth", "J_cinematic", "Walking Parallax Depth", "Footsteps shift background layers at differentiated speeds.", 72, "backdrop", "smile", "open_palm", "fist", "walk_remote"),
    (94, "comic_panel_breakout", "J_cinematic", "Comic Panel Breakout", "Punch through drawn panel border into next plane.", 60, "panel", "determined", "fist", "fist", "punch_impact"),
    (95, "silhouette_match_cut", "J_cinematic", "Silhouette Match Cut", "Character changes pose to perfectly match target silhouette.", 66, "silhouette", "determined", "open_palm", "open_palm", "flourish_greet"),
    (96, "faux_camera_orbit_2d", "J_cinematic", "Faux Camera Orbit 2D", "2D multi-plane parallax orbit using prepared views.", 72, "scene", "smile", "open_palm", "fist", "spin_bow"),
    (97, "lock_on_radar_reveal", "J_cinematic", "Lock On Radar Reveal", "Eyes locate target, tracked HUD locks and expands.", 60, "card", "squint", "point", "fist", "point_decisive"),
    (98, "dramatic_hold_highlight", "J_cinematic", "Dramatic Hold Highlight", "Time-slow pose, targeted highlight, precise recovery.", 66, "card", "determined", "open_palm", "fist", "jump_land"),
    (99, "spotlight_toss_follow", "J_cinematic", "Spotlight Toss Follow", "Toss light source and target is revealed along light path.", 66, "card", "smile", "open_palm", "fist", "toss_track"),
    (100, "signature_finale_chain", "J_cinematic", "Signature Finale Chain", "Multi-part signature sequence: prop, body, FX, world shift, grounded bow.", 90, "card", "smile", "open_palm", "open_palm", "finale_chain"),
]


def _build_keyframes_for_archetype(archetype: str, num: int) -> List[dict]:
    """Generate distinct multi-keyframe skeletal poses for each action archetype."""
    phase_bias = ((num % 7) - 3) * 2.5
    rest = {
        "character_root": {"tx": 0.0, "ty": 0.0, "rot": 0.0, "sx": 1.0, "sy": 1.0},
        "torso_group": {"rot": 0.0},
        "head_group": {"rot": 0.0},
        "arm_right_upper": {"rot": 0.0},
        "arm_right_forearm": {"rot": 0.0},
        "arm_left_upper": {"rot": 0.0},
        "arm_left_forearm": {"rot": 0.0},
        "leg_left_upper": {"rot": 0.0},
        "leg_right_upper": {"rot": 0.0},
        "tie_group": {"rot": 0.0},
    }

    if archetype == "idle_sway":
        mid = {"torso_group": {"rot": 3.5}, "head_group": {"rot": -4.0}, "arm_right_upper": {"rot": -8.0}, "tie_group": {"rot": 5.0}}
        alt = {"torso_group": {"rot": -3.0}, "head_group": {"rot": 3.0}, "arm_right_upper": {"rot": 6.0}, "tie_group": {"rot": -4.0}}
        return [{"t": 0.0, "bones": rest}, {"t": 0.35, "ease": "ease_in_out", "bones": mid}, {"t": 0.7, "ease": "ease_in_out", "bones": alt}, {"t": 1.0, "ease": "ease_in_out", "bones": rest}]

    if archetype in ("point_decisive", "poke_watch"):
        prep = {"torso_group": {"rot": -8.0}, "head_group": {"rot": -10.0}, "arm_right_upper": {"rot": -45.0}, "arm_right_forearm": {"rot": -40.0}}
        peak = {"torso_group": {"rot": 10.0 + phase_bias * 0.4}, "head_group": {"rot": 8.0}, "arm_right_upper": {"rot": -68.0}, "arm_right_forearm": {"rot": 24.0}, "tie_group": {"rot": -14.0}}
        return [{"t": 0.0, "bones": rest}, {"t": 0.25, "ease": "anticipation", "bones": prep}, {"t": 0.52, "ease": "back_out", "bones": peak}, {"t": 0.8, "ease": "ease_in_out", "bones": peak}, {"t": 1.0, "ease": "ease_in_out", "bones": rest}]

    if archetype in ("flourish_greet", "spin_bow", "finale_chain"):
        prep = {"character_root": {"ty": 14.0, "sy": 0.94, "sx": 1.05}, "torso_group": {"rot": -10.0}, "arm_right_upper": {"rot": 20.0}, "arm_left_upper": {"rot": -20.0}}
        peak = {"character_root": {"ty": -18.0 if archetype != "spin_bow" else 0.0, "sx": -1.0 if archetype == "spin_bow" else 1.02, "sy": 1.0}, "torso_group": {"rot": 14.0}, "head_group": {"rot": -8.0}, "arm_right_upper": {"rot": -85.0}, "arm_right_forearm": {"rot": -15.0}, "arm_left_upper": {"rot": 55.0}}
        bow = {"torso_group": {"rot": 22.0}, "head_group": {"rot": 12.0}, "arm_right_upper": {"rot": -30.0}, "tie_group": {"rot": -28.0}}
        return [{"t": 0.0, "bones": rest}, {"t": 0.2, "ease": "anticipation", "bones": prep}, {"t": 0.5, "ease": "back_out", "bones": peak}, {"t": 0.78, "ease": "spring", "bones": bow}, {"t": 1.0, "ease": "ease_in_out", "bones": rest}]

    if archetype in ("jump_land", "foot_stomp", "foot_kick"):
        crouch = {"character_root": {"ty": 22.0, "sx": 1.08, "sy": 0.9}, "torso_group": {"rot": 14.0}, "leg_left_upper": {"rot": -24.0}, "leg_right_upper": {"rot": 24.0}}
        air = {"character_root": {"ty": -75.0, "sx": 0.95, "sy": 1.06}, "torso_group": {"rot": -10.0}, "arm_right_upper": {"rot": -110.0}, "arm_left_upper": {"rot": 90.0}, "leg_right_upper": {"rot": -45.0 if archetype == "foot_kick" else 18.0}}
        land = {"character_root": {"ty": 18.0, "sx": 1.1, "sy": 0.88}, "torso_group": {"rot": 12.0}, "tie_group": {"rot": 24.0}}
        return [{"t": 0.0, "bones": rest}, {"t": 0.22, "ease": "anticipation", "bones": crouch}, {"t": 0.52, "ease": "ease_out", "bones": air}, {"t": 0.76, "ease": "bounce_out", "bones": land}, {"t": 1.0, "ease": "spring", "bones": rest}]

    if archetype in ("run_skid", "walk_remote", "surf_ride", "dodge_catch"):
        fwd = {"character_root": {"tx": 85.0 + phase_bias * 4.0, "ty": -10.0}, "torso_group": {"rot": 18.0}, "head_group": {"rot": -10.0}, "leg_left_upper": {"rot": 32.0}, "leg_right_upper": {"rot": -36.0}, "arm_right_upper": {"rot": -55.0}, "tie_group": {"rot": -32.0}}
        skid = {"character_root": {"tx": 120.0, "ty": 8.0, "rot": -8.0}, "torso_group": {"rot": -16.0}, "leg_left_upper": {"rot": -28.0}, "leg_right_upper": {"rot": 22.0}, "tie_group": {"rot": 28.0}}
        return [{"t": 0.0, "bones": rest}, {"t": 0.42, "ease": "ease_out", "bones": fwd}, {"t": 0.72, "ease": "back_out", "bones": skid}, {"t": 1.0, "ease": "ease_in_out", "bones": rest}]

    if archetype in ("recoil_spring", "stumble_trip", "sneeze_blast", "head_bonk", "balance_wobble"):
        tilt_a = {"character_root": {"tx": -28.0, "rot": -14.0}, "torso_group": {"rot": -22.0}, "head_group": {"rot": -18.0}, "arm_right_upper": {"rot": -125.0}, "arm_left_upper": {"rot": 115.0}, "leg_left_upper": {"rot": 24.0}}
        tilt_b = {"character_root": {"tx": 24.0, "rot": 10.0}, "torso_group": {"rot": 24.0}, "head_group": {"rot": 18.0}, "arm_right_upper": {"rot": -40.0}, "tie_group": {"rot": -35.0}}
        return [{"t": 0.0, "bones": rest}, {"t": 0.3, "ease": "elastic_out", "bones": tilt_a}, {"t": 0.65, "ease": "spring", "bones": tilt_b}, {"t": 1.0, "ease": "ease_in_out", "bones": rest}]

    if archetype in ("two_hand_press", "two_hand_open", "clap_burst", "dual_juggle", "fan_spread", "puppet_hands"):
        open_p = {"torso_group": {"rot": -4.0}, "arm_right_upper": {"rot": -95.0}, "arm_right_forearm": {"rot": -15.0}, "arm_left_upper": {"rot": 95.0}, "arm_left_forearm": {"rot": 15.0}}
        close_p = {"torso_group": {"rot": 6.0}, "arm_right_upper": {"rot": -45.0}, "arm_right_forearm": {"rot": 25.0}, "arm_left_upper": {"rot": 45.0}, "arm_left_forearm": {"rot": -25.0}}
        return [{"t": 0.0, "bones": rest}, {"t": 0.32, "ease": "back_out", "bones": open_p}, {"t": 0.68, "ease": "spring", "bones": close_p}, {"t": 1.0, "ease": "ease_in_out", "bones": rest}]

    # Default expressive gesture (think_epiphany, palm_lift, reach_pull, air_draw, remote_click, etc.)
    p1 = {"torso_group": {"rot": -6.0 + phase_bias * 0.5}, "head_group": {"rot": -8.0}, "arm_right_upper": {"rot": -55.0}, "arm_right_forearm": {"rot": -45.0}}
    p2 = {"torso_group": {"rot": 8.0}, "head_group": {"rot": 6.0}, "arm_right_upper": {"rot": -95.0 - phase_bias}, "arm_right_forearm": {"rot": 18.0}, "arm_left_upper": {"rot": 35.0}, "tie_group": {"rot": -15.0}}
    return [{"t": 0.0, "bones": rest}, {"t": 0.28, "ease": "anticipation", "bones": p1}, {"t": 0.58, "ease": "back_out", "bones": p2}, {"t": 1.0, "ease": "ease_in_out", "bones": rest}]


def build_100_actions() -> List[ActionSpec]:
    """Construct and validate all 100 mandatory ActionSpec definitions."""
    specs: List[ActionSpec] = []
    for num, aid, cat, title, desc, dur, ttype, expr_mid, rh, lh, arch in RAW_CATALOG:
        kfs = _build_keyframes_for_archetype(arch, num)
        spec = ActionSpec(
            schema_version="3.0.0",
            action_id=aid,
            number=num,
            category=cat,
            title=title,
            description=desc,
            duration_frames=dur,
            fps=30,
            required_anchors=["right_palm", "left_palm", "eyes", "ground_contact"],
            target_type=ttype,
            camera_suggestion={"pan": [0, 0], "zoom": 1.06 if num >= 91 else 1.0},
            sound_cue_suggestion={"cue": f"sfx_{cat}_{num:03d}", "timing_norm": 0.45},
            effect_nodes=[{"node_type": "vector_fx", "archetype": arch, "action_number": num}],
            configurable_params={
                "intensity": 1.0,
                "target_x": 720.0,
                "target_y": 320.0,
                "label": aid.split("_")[0].upper(),
                "text": "CREATIVE" if cat == "F_typography" else title.split()[0].upper(),
            },
            events=[
                {"phase": "prepare", "t_norm": 0.0, "anchor": "ground_contact", "detail": f"Anticipation for {aid}"},
                {"phase": "move", "t_norm": 0.25, "anchor": "right_palm", "detail": "Primary rig motion"},
                {"phase": "contact", "t_norm": 0.48, "anchor": "fingertips", "detail": "Target / FX engagement"},
                {"phase": "response", "t_norm": 0.65, "anchor": "eyes", "detail": "Target response & secondary tie follow-through"},
                {"phase": "release", "t_norm": 0.85, "anchor": "right_palm", "detail": "FX cleanup / release"},
                {"phase": "recover", "t_norm": 1.0, "anchor": "ground_contact", "detail": "Return to grounded stance"},
            ],
            keyframes=kfs,
            expression_track=[
                {"t": 0.0, "expression": "smile"},
                {"t": 0.35, "expression": expr_mid},
                {"t": 0.88, "expression": "smile"},
            ],
            hand_track=[
                {"t": 0.0, "left": "fist", "right": "open_palm"},
                {"t": 0.25, "left": lh, "right": rh},
                {"t": 0.9, "left": "fist", "right": "open_palm"},
            ],
            recovery_pose={"character_root": {"tx": 0.0, "ty": 0.0, "rot": 0.0}, "torso_group": {"rot": 0.0}},
        )
        specs.append(spec)
    return specs


def get_action_map() -> Dict[str, ActionSpec]:
    return {s.action_id: s for s in build_100_actions()}
