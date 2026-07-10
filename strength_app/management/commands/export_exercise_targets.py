"""
R2-W1: export_exercise_targets — generate the live-path CV artifact.

The 264 Python exercise modules (exercise_system/) are the single source
of truth for exercise phases and target angles. The live patient path is
client-side JS in v1_exercise_execute.html. This command walks the Python
registry and emits strength_app/static/strength_app/js/exercise_targets.json,
which the execute views embed per-exercise (see strength_app/cv_targets.py).

Per exercise the artifact carries:
  display_name, unilateral, movement_pattern
  is_hold       — dosed/tracked as a timed hold rather than reps
  phases        — the Python module's get_target_poses() verbatim
                  (bands as [lo, hi]; post-C3 corrected values)
  js_type       — the audited EXERCISE_PHASES template key the JS ghost
                  coach uses, or null when no JS template matches the
                  real movement (R2-W1-2 audit below)
  tracking      — 'camera' (JS tracking verified plausible) or 'manual'
                  (guided mode: cue card + self-counted reps/hold timer,
                  NO camera score — honesty over fake tracking, R2-W1-4)
  js_overrides  — depth-phase angle overrides derived from the Python
                  bottom phase for the joints the JS template scores
                  (R2-W1-3; only emitted where the correspondence is
                  unambiguous — never guessed)

The committed JSON is covered by a freshness test (test_r2_w1) that
regenerates and diffs; edit THIS table, never the JSON.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

# ─────────────────────────────────────────────────────────────────────────
# R2-W1-2 — audited exercise_id → (js_type, tracking) table.
#
# Rules applied (documented in docs/CV_ARCHITECTURE.md):
#   camera  only when ALL hold: (1) the JS template's tracked joints match
#           the exercise's actual primary movement; (2) the movement stays
#           in frame (no walking/travel); (3) MediaPipe pose is reliable in
#           that body orientation (not inverted/heavily occluded).
#   manual  otherwise. Falling back to a generic tracker that scores the
#           wrong joints is the failure mode this table exists to kill.
#
# April-27 known-wrong mappings fixed here:
#   marching_on_spot  was JUMP_LANDING  → manual (a march is not a jump)
#   wall_sit          was PLANK_FRONT   → SQUAT_HOLD (isometric knee/hip hold)
#   mountain_climbers was PUSH_UP       → manual (plank + knee drive, no elbow cycle)
#   nordic_*          was HINGE         → manual (kneeling fall ≠ standing hinge;
#                                         Nordic page is positional diagnostic only, W2-6)
#   bicep_curls       was ROW           → manual (elbow signal matches but the
#                                         ghost would coach a rowing motion)
#   scapular_pull / hanging_leg_raise were HANG → manual (elbows never bend;
#                                         the HANG rep detector can never fire)
#   single_leg_glute_bridge family was HINGE_SINGLE (standing) → manual (supine)
#   hollow_body_hold  was PLANK         → manual (hollow ≠ flat body line)
#   all STRETCH-fallback exercises      → manual (the generic STRETCH tracker
#                                         scored shoulder flexion for everything)
# ─────────────────────────────────────────────────────────────────────────

CAMERA = {
    # ── Bilateral squats: front view, knee(/hip/trunk) cycle ──
    'full_squats': 'SQUAT', 'box_squat': 'SQUAT', 'sit_to_stand': 'SQUAT',
    'heel_elevated_squat': 'SQUAT', 'pause_squat': 'SQUAT', 'prisoner_squat': 'SQUAT',
    'sumo_squat': 'SQUAT', 'tempo_squat': 'SQUAT', 'hindu_squat': 'SQUAT',
    'decline_squats': 'SQUAT',
    'barbell_back_squat': 'SQUAT', 'barbell_front_squat': 'SQUAT',
    'partial_squats': 'SQUAT_PARTIAL',
    'mini_squats_with_band': 'SQUAT_PARTIAL',   # mini = partial depth, was full-depth SQUAT
    'goblet_squat': 'GOBLET_SQUAT',
    # ── Single-leg squats: workingKnee ──
    'pistol_squat': 'SQUAT_SINGLE', 'single_leg_squats': 'SQUAT_SINGLE',
    'single_leg_squat_to_box': 'SQUAT_SINGLE', 'skater_squat': 'SQUAT_SINGLE',
    'cossack_squat': 'SQUAT_SINGLE',            # lateral single-leg bend; min-knee tracking holds
    'bulgarian_split_squats': 'BSS',
    # ── Isometric lower holds ──
    'wall_sit': 'SQUAT_HOLD',                   # FIX: was PLANK_FRONT (body-line ≠ wall sit)
    'spanish_squat': 'SQUAT_HOLD',              # Python models it as an isometric hold
    'squat_hold_assess': 'SQUAT_HOLD', 'hinge_hold_assess': 'HINGE_HOLD',
    'lunge_hold_assess': 'LUNGE_HOLD',
    # ── Standing hinges: side view, hip cycle ──
    'good_morning': 'HINGE', 'deadlift_dumbbell': 'HINGE', 'banded_rdl': 'HINGE',
    'hip_hinge_wall': 'HINGE', 'barbell_rdl': 'HINGE', 'trap_bar_deadlift': 'HINGE',
    'bodyweight_rdl': 'BW_RDL',
    'single_leg_rdl': 'SL_RDL', 'b_stance_rdl': 'HINGE_SINGLE',
    # ── Supine glute bridge (dedicated supine template) ──
    'glute_bridge': 'GLUTE_BRIDGE_SUPINE',
    # ── Clamshells (dedicated side-lying template) ──
    'clamshells': 'CLAMSHELL', 'banded_clamshells': 'CLAMSHELL',
    # ── Lunges / step variants: stationary knee cycle ──
    'split_squat_static': 'LUNGE', 'lunges': 'LUNGE', 'reverse_lunges': 'LUNGE',
    'curtsy_lunge': 'LUNGE', 'slider_reverse_lunge': 'LUNGE',
    'deficit_reverse_lunge': 'LUNGE', 'lateral_lunges': 'LUNGE',
    'step_downs': 'LUNGE', 'side_step_ups': 'LUNGE', 'side_step_downs': 'LUNGE',
    'lateral_step_down': 'LUNGE',
    'step_ups': 'STEP_UPS',
    'step_up_with_knee_drive': 'STEP_UPS',      # FIX: it is a step-up, was LUNGE_SPLIT
    # ── Push-up family: prone elbow cycle ──
    'push_ups': 'PUSH_UP', 'knee_push_up': 'PUSH_UP', 'incline_push_up': 'PUSH_UP',
    'decline_push_up': 'PUSH_UP', 'diamond_push_up': 'PUSH_UP',
    'close_grip_push_up': 'PUSH_UP', 'wide_grip_push_up': 'PUSH_UP',
    'staggered_push_up': 'PUSH_UP', 'shoulder_tap_push_up': 'PUSH_UP',
    'spiderman_push_up': 'PUSH_UP', 'box_push_up': 'PUSH_UP', 'ring_push_up': 'PUSH_UP',
    'push_up_plus': 'PUSH_UP', 'elevated_push_up': 'PUSH_UP',
    'wall_push_up': 'WALL_PUSH_UP',
    'pike_push_up': 'PRESS_VERTICAL', 'pike_push_up_elevated': 'PRESS_VERTICAL',
    # ── Plank holds ──
    'planks': 'PLANK', 'single_arm_plank': 'PLANK', 'single_arm_single_leg_plank': 'PLANK',
    'side_plank': 'SIDE_PLANK', 'copenhagen_plank': 'SIDE_PLANK',
    # ── Balance holds ──
    'single_leg_balance': 'BALANCE', 'single_leg_eyes_closed': 'BALANCE',
    # ── Plyometrics with dedicated landing-check coaches ──
    'tuck_jumps': 'PLYO_TUCK_JUMPS', 'broad_jump': 'PLYO_BROAD_JUMP',
    'lateral_bound_stick': 'PLYO_LATERAL_BOUND_STICK',
    'lateral_bound_and_stick': 'PLYO_LATERAL_BOUND_STICK',
    'lateral_bound': 'PLYO_LATERAL_BOUND_STICK',
    'single_leg_hop_lateral': 'PLYO_SL_HOP_LATERAL',
    'single_leg_hop_forward': 'PLYO_SL_HOP_FORWARD',
    'single_leg_landing': 'PLYO_SL_LANDING',
    'single_leg_hop_and_stick': 'PLYO_SL_LANDING',  # same land-and-stick pattern
    'jump_squats': 'JUMP',
    # ── Pull-ups: hanging elbow cycle (vertical phone framing; verify on film) ──
    'chin_up': 'HANG', 'full_pull_up': 'HANG', 'close_grip_pull_up': 'HANG',
    'band_assisted_pull_up': 'HANG', 'jumping_pull_up': 'HANG',
    'negative_pull_up': 'HANG', 'archer_pull_up': 'HANG', 'commando_pull_up': 'HANG',
    'l_sit_pull_up': 'HANG', 'weighted_pull_up': 'HANG',
    'single_arm_pull_up_prog': 'HANG',
    'dead_hang': 'HANG_HOLD',
    # ── Rows: elbow pull cycle ──
    'dumbbell_rowing': 'ROW_BENT_OVER',
    'inverted_row': 'ROW', 'ring_row': 'ROW', 'australian_row': 'ROW',
    'table_row': 'ROW', 'elevated_table_row': 'ROW', 'doorframe_row': 'ROW',
    'bedsheet_row': 'ROW', 'towel_row': 'ROW', 'single_arm_towel_row': 'ROW',
    'renegade_row': 'ROW',
    # ── Band pulls: arm-spread ratio ──
    'band_pull_apart': 'BAND_PULL_APART', 'face_pull_band': 'PULL',
    # ── Supine core ──
    'dead_bug': 'DEAD_BUG', 'single_leg_dead_bug': 'DEAD_BUG',
    # ── 2026-07 DARK prescription-tier coaches (*_rx keys; catalog flags
    #    stay False — nothing patient-reachable routes here yet) ──
    'wall_sit_rx': 'WALL_SIT_RX',
    'plank_hold_rx': 'PLANK_RX',
    'side_plank_rx': 'SIDE_PLANK_RX',
}

# Manual — no JS template matches the real movement, the movement travels
# out of frame, pose detection is unreliable in that orientation, or the
# Python module itself has placeholder targets. One-line reason per group.
MANUAL = set()

# Stretch / mobility / activation: the old STRETCH fallback faked tracking.
MANUAL |= {
    'hip_flexor_stretch', 'hamstring_stretch', 'pigeon_stretch', 'frog_stretch',
    'groin_stretch_butterfly', 'quadriceps_stretch', 'calf_stretch', 'hip_cars',
    'shoulder_cars', 'shoulder_stretch', 'chest_stretch', 'wrist_forearm_stretch',
    'it_band_stretch', 'cat_cow', 'foam_rolling', 'pnf_hamstring_stretch',
    'loaded_progressive_stretch', 'ninety_ninety_hip_switch', 'thoracic_rotation',
    'seated_spinal_twist', 'trunk_rotation_stretch', 'prone_scorpion',
    'worlds_greatest_stretch', 'adductor_rock', 'wall_angel', 'wall_slide',
    'banded_shoulder_dislocate', 'scapular_setting', 'chin_tuck',
    'deep_neck_flexor_activation', 'pendulum_exercise', 'knee_circles',
    'ankle_dorsiflexion_wall', 'ankle_pumps', 'patellar_mobilisation',
    'heel_drop', 'quad_set_with_shr', 'static_glutei', 'static_hip_adductors',
    'static_quadriceps', 'isometric_shoulder_ir', 'isometric_shoulder_er',
    'isometric_quad_set',
}
# Seated / lying small-ROM rehab: no standing template applies.
MANUAL |= {
    'knee_extension_sitting', 'short_arc_quad', 'terminal_knee_extension',
    'straight_leg_raises', 'prone_hip_extension', 'hip_abduction_sideline',
    'heel_slides', 'seated_hip_flexion', 'supine_hip_abduction',
    'seated_hamstring_curl', 'hamstring_curls_standing', 'tricep_extensions',
}
# Supine bridges/thrusts without a matching template (HINGE_SINGLE is standing).
MANUAL |= {
    'single_leg_glute_bridge', 'single_leg_hip_thrust', 'single_leg_slider_curl',
    'hip_thrust_bodyweight', 'hip_thrust_banded', 'barbell_hip_thrust',
    'reverse_hyperextension', 'sliding_leg_curl',
}
# Nordics: kneeling eccentric — W2-6 keeps these positional/manual only.
MANUAL |= {'nordic_hamstring_curl', 'nordic_curl_weighted', 'nordic_curl_partner'}
# Travelling / locomotor: subject leaves or traverses the frame.
MANUAL |= {
    'walking_lunge', 'dumbbell_walking_lunge', 'tandem_walking', 'backward_walking',
    'sideways_walking', 'lateral_gait_training', 'shuttle_run', 'change_of_direction',
    'lateral_shuffle_drill', 'carioca_drill', 'a_skip_drill', 'b_skip_drill',
    'farmer_carry', 'suitcase_carry', 'overhead_carry', 'waiter_carry',
    'bottoms_up_carry', 'waiter_farmer_combined', 'single_arm_farmer_heavy',
    'bear_crawl', 'bear_crawl_cardio', 'bear_crawl_with_reach', 'lateral_bear_crawl',
    'crab_walk', 'crawl_drag', 'lateral_band_walks', 'single_leg_bound',
    'power_skip',
}
# Rhythmic cardio dosed by time, no clean rep geometry for the JUMP template.
MANUAL |= {
    'marching_on_spot', 'high_knees', 'jumping_jacks', 'sprint_in_place',
    'jumping_rope_simulation', 'butt_kicks', 'burpees', 'mountain_climbers',
    'skaters', 'lateral_hops', 'side_to_side_hops', 'sprint_start',
}
# Plyo with boxes/hurdles or mid-air turns: occlusion / unreliable phases.
MANUAL |= {
    'box_jumps', 'depth_jump', 'squat_jump_turn', 'hurdle_hop',
    'continuous_hurdle_hops', 'drop_landing', 'altitude_drop_landing',
    'pogo_jump_single_leg',   # contact-time claims need a force plate (W2-1)
    'skipping_lunge', 'plyometric_lunge', 'split_squat_jump', 'clock_lunge',
}
# Negative-only row: the ROW rep machine expects a concentric pull phase.
MANUAL |= {'negative_table_row'}
# Push-up variants whose geometry breaks the avg-elbow assumption.
MANUAL |= {
    'archer_push_up', 'hindu_push_up', 'explosive_push_up', 'clapping_push_up',
    'drop_push_up', 'negative_push_up', 'pseudo_planche_push_up',
    'typewriter_push_up', 'single_arm_push_up_progression', 'single_arm_push_up_prog',
    'serratus_wall_push', 'wall_handstand_push_up',  # inverted pose unreliable
    'dip_progression',  # PRESS_HORIZONTAL is a supine template; dips are upright
}
# Core/plank variants that are NOT a flat-body-line hold.
MANUAL |= {
    'hollow_body_hold', 'hollow_body_rock', 'superman_hold', 'l_sit_floor',
    'ab_wheel_rollout', 'dragon_flag_progression', 'planche_lean',
    'handstand_wall_hold', 'plank_shoulder_tap', 'side_plank_hip_dip',
    'side_plank_rotation', 'copenhagen_with_movement', 'wall_drive_hold',
    'bird_dog',  # quadruped; DEAD_BUG ghost would coach a supine motion
}
# Rotation family: the shoulder/hip X-ratio signal is unreliable (collapses
# when the user turns side-on) — all manual until a validated tracker exists.
MANUAL |= {
    'russian_twist_bw', 'bicycle_crunch', 'pallof_press_isometric',
    'pallof_press_dynamic', 'band_woodchop', 'rotational_throw',
    'rotational_swings', 'windshield_wiper', 'turkish_get_up',
}
# Pulls whose visible motion is too subtle or absent for the templates.
MANUAL |= {
    'scapular_pull', 'hanging_leg_raise', 'muscle_up_progression',
    'prone_y_t_w', 'prone_trap_raise', 'side_lying_external_rotation',
    'bicep_curls',
}
# Ballistic hinge / overhead: phase machine and ghost don't match.
MANUAL |= {'kettlebell_swing', 'medicine_ball_slam', 'hip_abduction_standing'}
# Balance variants the BALANCE hold template would mis-score.
MANUAL |= {
    'double_leg_balance',  # template requires a lifted knee
    'bosu_balance', 'bosu_squat', 'perturbation_training',
    'single_leg_reach', 'star_excursion', 'clock_reaches',  # dynamic reaches, not holds
}
# Small-ROM pulse: full-cycle rep machine can't count pulses.
MANUAL |= {'squat_pulse', 'sissy_squat'}
# Calf work: no template tracks ankle plantar-flexion.
MANUAL |= {'heavy_calf_raise', 'single_leg_calf_raise'}

# ─────────────────────────────────────────────────────────────────────────
# R2-W1-3 — depth-phase override correspondence.
# For each js_type: JS phase name → (python_phase, {js_joint: python_key}).
# Only the unambiguous depth/bottom targets are ported; everything else
# keeps the JS template default. Bands [lo, hi] are passed through.
# ─────────────────────────────────────────────────────────────────────────
JS_OVERRIDE_MAP = {
    'SQUAT':          {'down': ('bottom', {'knee': 'avg_knee'}),
                       'hold': ('bottom', {'knee': 'avg_knee'})},
    'SQUAT_PARTIAL':  {'down': ('bottom', {'knee': 'avg_knee'}),
                       'hold': ('bottom', {'knee': 'avg_knee'})},
    'SQUAT_SINGLE':   {'down': ('bottom', {'workingKnee': 'avg_knee'}),
                       'hold': ('bottom', {'workingKnee': 'avg_knee'})},
    'GOBLET_SQUAT':   {'down': ('bottom', {'knee': 'avg_knee'}),
                       'hold': ('bottom', {'knee': 'avg_knee'})},
    'LUNGE':          {'down': ('bottom', {'knee': 'front_knee'}),
                       'hold': ('bottom', {'knee': 'front_knee'})},
    'HINGE':          {'start': ('bottom', {'hip': 'avg_hip'}),
                       'down':  ('bottom', {'hip': 'avg_hip'})},
    'PUSH_UP':        {'down': ('bottom', {'elbow': 'avg_elbow'}),
                       'hold': ('bottom', {'elbow': 'avg_elbow'})},
    'WALL_PUSH_UP':   {'down': ('bottom', {'elbow': 'avg_elbow'}),
                       'hold': ('bottom', {'elbow': 'avg_elbow'})},
}


class Command(BaseCommand):
    help = "Export per-exercise CV targets from the Python module registry to static JSON (R2-W1)."

    def add_arguments(self, parser):
        parser.add_argument('--check', action='store_true',
                            help='Exit 1 if the committed JSON is stale (no write).')
        parser.add_argument('--output', default=None, help='Override output path (tests).')

    def handle(self, *args, **opts):
        from strength_app.exercise_system.exercise_registry_v2 import EXERCISE_METADATA
        from strength_app.v1_constants import HOLD_EXERCISE_IDS

        known_ids = set(EXERCISE_METADATA.keys())
        table_ids = set(CAMERA) | MANUAL

        # Integrity of the curated table itself
        overlap = set(CAMERA) & MANUAL
        if overlap:
            raise SystemExit(f"IDs in both CAMERA and MANUAL: {sorted(overlap)}")
        missing = known_ids - table_ids
        if missing:
            raise SystemExit(
                f"{len(missing)} registry IDs missing a tracking decision "
                f"(add to CAMERA or MANUAL): {sorted(missing)}"
            )
        # IDs curated here but absent from the registry (football extras,
        # assessment holds): emit a minimal entry so the live path still
        # gets the audited tracking decision — no phases (no Python truth).
        unknown = table_ids - known_ids
        export = {}
        for ex_id in sorted(unknown):
            js_type = CAMERA.get(ex_id)
            export[ex_id] = {
                'display_name': ex_id.replace('_', ' ').title(),
                'unilateral': False,
                'movement_pattern': '',
                'is_hold': (ex_id in HOLD_EXERCISE_IDS
                            or js_type in {'SQUAT_HOLD', 'HINGE_HOLD', 'LUNGE_HOLD'}
                            or ex_id.endswith('_hold')),
                'tracking': 'camera' if js_type else 'manual',
                'js_type': js_type,
                'phases': {},
            }

        for ex_id in sorted(known_ids):
            meta = EXERCISE_METADATA[ex_id]
            phases = {}
            try:
                inst = meta['class']()
                raw = inst.get_target_poses() if hasattr(inst, 'get_target_poses') else {}
                if isinstance(raw, dict):
                    for pname, pdata in raw.items():
                        if isinstance(pdata, dict):
                            phases[pname] = {
                                k: (list(v) if isinstance(v, (list, tuple)) else v)
                                for k, v in pdata.items()
                            }
            except Exception as exc:  # registry instantiates cleanly per DA-H3; belt & braces
                self.stderr.write(f"warn: {ex_id} get_target_poses failed: {exc}")

            js_type = CAMERA.get(ex_id)
            tracking = 'camera' if js_type else 'manual'

            # Hold semantics: dosing set wins; otherwise single-phase or
            # holding-style python modules and the *_HOLD/PLANK/BALANCE
            # JS templates are holds.
            hold_types = {'PLANK', 'SIDE_PLANK', 'BALANCE', 'HANG_HOLD',
                          'SQUAT_HOLD', 'HINGE_HOLD', 'LUNGE_HOLD',
                          # 2026-07 dark coaches (hold-type *_rx js_types)
                          'WALL_SIT_RX', 'PLANK_RX', 'SIDE_PLANK_RX',
                          'BALANCE_RX', 'KNEE_TO_CHEST_RX'}
            is_hold = (
                ex_id in HOLD_EXERCISE_IDS
                or (js_type in hold_types)
                or (tracking == 'manual' and (
                    len(phases) <= 1
                    or set(phases) in ({'rest', 'holding'}, {'ready', 'holding'},
                                       {'setup', 'holding'}, {'holding'},
                                       {'rest', 'hold'}, {'setup', 'hold'})
                ))
            )

            entry = {
                'display_name': meta.get('display_name', ex_id.replace('_', ' ').title()),
                'unilateral': bool(meta.get('unilateral')),
                'movement_pattern': meta.get('movement_pattern', ''),
                'is_hold': bool(is_hold),
                'tracking': tracking,
                'js_type': js_type,
                'phases': phases,
            }

            # Depth-phase overrides from Python ground truth
            if js_type in JS_OVERRIDE_MAP and phases:
                overrides = {}
                for js_phase, (py_phase, joint_map) in JS_OVERRIDE_MAP[js_type].items():
                    src = phases.get(py_phase) or {}
                    vals = {}
                    for js_joint, py_key in joint_map.items():
                        if py_key in src:
                            vals[js_joint] = src[py_key]
                    if vals:
                        overrides[js_phase] = vals
                if overrides:
                    entry['js_overrides'] = overrides

            export[ex_id] = entry

        out_path = Path(opts['output']) if opts['output'] else (
            Path(__file__).resolve().parents[2]
            / 'static' / 'strength_app' / 'js' / 'exercise_targets.json'
        )
        payload = json.dumps(export, indent=1, sort_keys=True) + '\n'

        if opts['check']:
            current = out_path.read_text() if out_path.exists() else ''
            if current != payload:
                raise SystemExit(f"{out_path} is STALE — run manage.py export_exercise_targets")
            self.stdout.write("exercise_targets.json is fresh")
            return

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload)
        n_cam = sum(1 for e in export.values() if e['tracking'] == 'camera')
        self.stdout.write(self.style.SUCCESS(
            f"Wrote {out_path} — {len(export)} exercises "
            f"({n_cam} camera-tracked, {len(export) - n_cam} manual)"
        ))
