"""
VYAYAM — Football Athlete Tier Constants (Sprint 1)

Contains all configuration for the football performance module:
assessment battery, level thresholds, HSR protocol, contrast training,
plyometric gates, F-V tendency, periodisation phases, and sport types.
"""

# ============================================================================
# ASSESSMENT BATTERY — 6 tests, each scored 0-5
# ============================================================================

FOOTBALL_ASSESSMENT_TESTS = [
    {
        'test_id': 'hop_test',
        'name': 'Single-Leg Hop for Distance',
        'measure': 'Hop distance (cm) — best leg',
        'input_label': 'Distance hopped (cm)',
        'pattern': 'hop',
        'unit': 'cm',
        'is_bilateral': True,   # left and right recorded separately → LSI computed
        # scoring_thresholds: 4 boundary values separating bands 1/2, 2/3, 3/4, 4/5
        # higher is better
        'scoring_thresholds': [120, 150, 180, 210],
        'scoring_thresholds_reverse': False,
        'instructions': [
            'Stand on one leg, hop as far forward as possible.',
            'Stick the landing — hold 2 seconds.',
            'Record best of 3 trials each leg.',
        ],
        'scoring': {
            1: 'Cannot achieve single-leg stance',
            2: '<70 % LSI or <120 cm',
            3: '70-84 % LSI or 120-149 cm',
            4: '85-94 % LSI or 150-179 cm',
            5: '≥95 % LSI and ≥180 cm',
        },
    },
    {
        'test_id': 'nordic_test',
        'name': 'Nordic Hamstring Curl',
        'measure': 'Eccentric hold time (seconds)',
        'input_label': 'Hold time (seconds, self-timed)',  # R2-W2-6: self-reported, not a measured break-point angle
        'pattern': 'nordic',
        'unit': 'seconds_held',
        'is_bilateral': False,
        'scoring_thresholds': [1, 4, 7, 10],
        'scoring_thresholds_reverse': False,
        'instructions': [
            'Kneel, feet anchored. Lower body toward floor using hamstrings only.',
            'Hold the eccentric phase as long as possible.',
            'Record time until hands touch ground.',
        ],
        'scoring': {
            1: 'Cannot hold >1 s',
            2: '1-3 s',
            3: '4-6 s',
            4: '7-10 s',
            5: '>10 s',
        },
    },
    {
        'test_id': 'sprint_test',
        'name': '20 m Sprint',
        'measure': 'Sprint time (seconds) — lower is better',
        'input_label': 'Time (seconds)',
        'pattern': 'sprint',
        'unit': 'seconds',
        'is_bilateral': False,
        # lower is better — thresholds descend
        'scoring_thresholds': [4.0, 3.70, 3.40, 3.09],
        'scoring_thresholds_reverse': True,
        'instructions': [
            'Standing start, sprint 20 m at maximum effort.',
            'Timed with electronic gates or video review.',
            'Best of 2 attempts.',
        ],
        'scoring': {
            1: '>4.0 s',
            2: '3.71-4.0 s',
            3: '3.41-3.70 s',
            4: '3.10-3.40 s',
            5: '≤3.09 s',
        },
    },
    {
        # R2-W2-1 (SB-9): this is an APP-SPECIFIC reactivity count, NOT
        # Reactive Strength Index. True RSI = flight time / ground-contact
        # time, which requires a contact mat or force plate; a phone camera
        # and a self-count cannot measure 200 ms contacts. Labels and copy
        # must never use the term "RSI". See docs/FOOTBALL_METHODS.md.
        'test_id': 'pogo_test',
        'name': 'Pogo Hop (bilateral)',
        'measure': 'Springy reps in 10 seconds (app reactivity count)',
        'input_label': 'Springy reps counted (10 s window)',
        'pattern': 'pogo',
        'unit': 'clean_reps_in_10s',
        'is_bilateral': False,
        'scoring_thresholds': [10, 15, 20, 25],
        'scoring_thresholds_reverse': False,
        'instructions': [
            'Bilateral continuous ankle hops — bounce, don’t squat between hops.',
            'Count only springy reps: quick contact, knees nearly straight, heels barely touching.',
            'Athlete self-reports; coach verifies visually. This is an app metric, not a lab reactive-strength measurement.',
        ],
        'scoring': {
            1: '<10 clean reps',
            2: '10-14 clean reps',
            3: '15-19 clean reps',
            4: '20-24 clean reps',
            5: '≥25 clean reps',
        },
    },
    {
        'test_id': 'cod_test',
        'name': '505 Change-of-Direction Test',
        'measure': 'Best side time (seconds) — lower is better',
        'input_label': 'Time (seconds)',
        'pattern': 'cod',
        'unit': 'seconds',
        'is_bilateral': True,   # left and right pivots recorded separately
        'scoring_thresholds': [3.0, 2.70, 2.40, 2.09],
        'scoring_thresholds_reverse': True,
        'instructions': [
            'Sprint 10 m, plant and cut 180° at the 5 m mark.',
            'Sprint back through the start gate.',
            'Record time for each turn direction.',
        ],
        'scoring': {
            1: '>3.0 s either direction',
            2: '2.71-3.0 s',
            3: '2.41-2.70 s',
            4: '2.10-2.40 s',
            5: '≤2.09 s',
        },
    },
    {
        'test_id': 'ybalance_test',
        'name': 'Y-Balance Test (anterior reach)',
        'measure': 'Reach distance as % of limb length — best leg',
        'input_label': 'Reach distance (% of limb length)',
        'pattern': 'ybalance',
        'unit': 'percent_limb_length',
        'is_bilateral': True,
        'scoring_thresholds': [75, 85, 95, 105],
        'scoring_thresholds_reverse': False,
        'instructions': [
            'Stand on one leg, reach the free leg in anterior direction.',
            'Normalise reach distance to limb length × 100.',
            'Best of 3 trials each leg.',
        ],
        'scoring': {
            1: '<75 % either leg',
            2: '75-84 %',
            3: '85-94 %',
            4: '95-104 %',
            5: '≥105 %',
        },
    },
    # ── Tests 7 & 8: manual-entry strength (2026-07 Part 3) ────────────────
    # entry_mode='strength_manual': the athlete is under load / on a machine,
    # so this is weight×reps manual entry — no camera, no 0-5 band.
    # Estimated 1RM via Epley (1RM = w × (1 + reps/30)) is computed
    # SERVER-SIDE in football_save_test_result and persisted on
    # PatientProfile.raw_test_data_json['strength_tests'].
    # DELIBERATELY NOT part of football_level: compute_level() reads only the
    # six 0-5 score fields, and that scoring has known deferred bugs (SB-5a)
    # — these two are store-and-display only.
    {
        'test_id': 'bench_press_test',
        'name': 'Bench Press',
        'measure': 'Upper-limb strength — weight × reps, estimated 1RM (Epley)',
        'input_label': 'Weight (kg) and reps completed',
        'pattern': 'push',
        'unit': 'kg_x_reps',
        'is_bilateral': False,
        'entry_mode': 'strength_manual',
        'scoring_thresholds': [],
        'scoring_thresholds_reverse': False,
        'instructions': [
            'Warm up, then load a weight you can press for roughly 5-10 reps.',
            'Lower the bar to your chest under control and press to lockout.',
            'Stop the set when your form breaks — do not grind to failure.',
            'Always use a spotter or safety racks.',
            'Enter the weight and the number of clean reps completed.',
        ],
        'scoring': {},
    },
    {
        'test_id': 'leg_press_test',
        'name': 'Leg Press',
        'measure': 'Lower-limb strength — weight × reps, estimated 1RM (Epley)',
        'input_label': 'Weight (kg) and reps completed',
        'pattern': 'squat',
        'unit': 'kg_x_reps',
        'is_bilateral': False,
        'entry_mode': 'strength_manual',
        'scoring_thresholds': [],
        'scoring_thresholds_reverse': False,
        'instructions': [
            'Set the seat so your knees start near 90 degrees.',
            'Load a weight you can press for roughly 5-10 reps.',
            'Lower under control to 90 degrees, press without slamming the knees into lockout.',
            'Stop when depth or control degrades — no half reps.',
            'Enter the sled weight and the number of clean reps completed.',
        ],
        'scoring': {},
    },
]

# ============================================================================
# FOOTBALL LEVELS — weakest-link scoring (min of all 6 test scores)
# ============================================================================

FOOTBALL_LEVELS = {
    1: {
        'name': 'Foundation',
        'label': 'Foundation',
        'description': 'Significant deficits present — focus on tissue tolerance and bilateral strength base.',
        'primary_focus': 'anatomical_adaptation',
        'hsr_eligible': False,
        'plyometric_eligible': False,
        'contrast_eligible': False,
        'contrast_training': False,
        'reactive_agility': False,
        'hsr_phase': 'hsr_phase_1',
        'posterior_anterior_ratio': 0.50,
        'training_focus': [
            'Bilateral lower-body strength (leg press, hip thrust)',
            'Posterior chain endurance — Nordic assisted holds',
            'Ankle and knee stability drills',
            'No impact or jump loading yet',
        ],
    },
    2: {
        'name': 'Development',
        'label': 'Development',
        'description': 'Moderate deficits — HSR protocol entry, bilateral loaded patterns.',
        'primary_focus': 'hsr_phase_1',
        'hsr_eligible': True,
        'plyometric_eligible': False,
        'contrast_eligible': False,
        'contrast_training': False,
        'reactive_agility': False,
        'hsr_phase': 'hsr_phase_1',
        'posterior_anterior_ratio': 0.55,
        'training_focus': [
            'HSR Phase 1: 3×8-10 at 55 % 1RM, 6-0-6 tempo',
            'Slow eccentric training to build tendon tolerance',
            'Bilateral progressions before unilateral loading',
            'Pogo and skipping drills — low load only',
        ],
    },
    3: {
        'name': 'Consolidation',
        'label': 'Consolidation',
        'description': 'Competent base — HSR phase 2, introduce low-load plyometrics.',
        'primary_focus': 'hsr_phase_2',
        'hsr_eligible': True,
        'plyometric_eligible': True,
        'contrast_eligible': False,
        'contrast_training': False,
        'reactive_agility': False,
        'hsr_phase': 'hsr_phase_2',
        'posterior_anterior_ratio': 0.55,
        'training_focus': [
            'HSR Phase 2: 4×5-7 at 70 % 1RM with unilateral work',
            'Monitor LSI weekly — address asymmetry with single-leg variants',
            'Low-load plyometrics: box jumps, hurdle hops',
            'COD mechanics and deceleration drills',
        ],
    },
    4: {
        'name': 'Performance',
        'label': 'Performance',
        'description': 'Strong base — HSR phase 3, contrast training, moderate plyometrics.',
        'primary_focus': 'hsr_phase_3',
        'hsr_eligible': True,
        'plyometric_eligible': True,
        'contrast_eligible': True,
        'contrast_training': True,
        'reactive_agility': True,
        'hsr_phase': 'hsr_phase_3',
        'posterior_anterior_ratio': 0.60,
        'training_focus': [
            'HSR Phase 3: 4×3-6 at 80 % 1RM, peak strength block',
            'Contrast pairs: heavy squat → box jump, RDL → broad jump',
            'Moderate plyometrics: single-leg hops, depth drops',
            'Sprint mechanics and acceleration drills',
        ],
    },
    5: {
        'name': 'Elite',
        'label': 'Elite',
        'description': 'Full athletic expression — advanced contrast, high-intensity plyometrics, sprint work.',
        'primary_focus': 'sport_specific',
        'hsr_eligible': True,
        'plyometric_eligible': True,
        'contrast_eligible': True,
        'contrast_training': True,
        'reactive_agility': True,
        'hsr_phase': 'hsr_phase_3',
        'posterior_anterior_ratio': 0.60,
        'training_focus': [
            'Advanced contrast training with sport-specific movements',
            'High-intensity plyometrics: depth jumps, reactive single-leg hops',
            'Resisted sprint and overspeed work',
            'Periodised F-V profiling and in-season maintenance',
        ],
    },
}

# ============================================================================
# HEAVY SLOW RESISTANCE (HSR) PROTOCOL — 3 phases
# ============================================================================

HSR_PHASES = {
    'hsr_phase_1': {
        'name': 'HSR Phase 1 — Load Introduction',
        'weeks': 4,
        'sets': 3,
        'rep_range': '6-8',
        'tempo': '6-0-6-0',
        'frequency_per_week': 3,
        'exercises': [
            'heavy_calf_raise',
            'bodyweight_rdl',
            'nordic_hamstring_curl',
            'split_squat_static',
            'glute_bridge',
        ],
        'description': 'Tendon stiffness foundation. Achilles, patellar, hamstring tendons.',
    },
    'hsr_phase_2': {
        'name': 'HSR Phase 2 — Progressive Loading',
        'weeks': 4,
        'sets': 4,
        'rep_range': '4-6',
        'tempo': '6-0-6-0',
        'frequency_per_week': 3,
        'exercises': [
            'heavy_calf_raise',
            'barbell_rdl',
            'nordic_hamstring_curl',
            'bulgarian_split_squats',
            'barbell_hip_thrust',
        ],
        'description': 'Increased tendon loading. Heavier loads, longer eccentrics.',
    },
    'hsr_phase_3': {
        'name': 'HSR Phase 3 — Peak + Reactive',
        'weeks': 4,
        'sets': 4,
        'rep_range': '3-5',
        'tempo': '3-0-3-0',
        'frequency_per_week': 2,
        'exercises': [
            'single_leg_calf_raise',
            'trap_bar_deadlift',
            'nordic_hamstring_curl',
            'bulgarian_split_squats',
            'single_leg_hip_thrust',
        ],
        'description': 'Peak tendon stiffness + reactive work introduced.',
    },
}

# ============================================================================
# CONTRAST PAIRS — heavy strength + explosive superset (12 pairs)
# ============================================================================

CONTRAST_PAIRS = [
    {
        'id': 'cp_01',
        'strength_exercise': 'barbell_back_squat',
        'explosive_exercise': 'box_jumps',
        'rest_between_s': 90,
        'rest_after_pair_s': 180,
        'notes': 'Heavy squat → explosive box jump.',
    },
    {
        'id': 'cp_02',
        'strength_exercise': 'barbell_rdl',
        'explosive_exercise': 'broad_jump',
        'rest_between_s': 90,
        'rest_after_pair_s': 180,
        'notes': 'Posterior chain. Loaded RDL → broad jump.',
    },
    {
        'id': 'cp_03',
        'strength_exercise': 'barbell_hip_thrust',
        'explosive_exercise': 'jump_squats',
        'rest_between_s': 90,
        'rest_after_pair_s': 180,
        'notes': 'Glute power. Heavy hip thrust → jump squat.',
    },
    {
        'id': 'cp_04',
        'strength_exercise': 'bulgarian_split_squats',
        'explosive_exercise': 'single_leg_bound',
        'rest_between_s': 90,
        'rest_after_pair_s': 180,
        'notes': 'Unilateral contrast. Match working leg.',
    },
    {
        'id': 'cp_05',
        'strength_exercise': 'nordic_hamstring_curl',
        'explosive_exercise': 'b_skip_drill',
        'rest_between_s': 120,
        'rest_after_pair_s': 240,
        'notes': 'Eccentric hamstring → hamstring cycling speed drill.',
    },
    {
        'id': 'cp_06',
        'strength_exercise': 'goblet_squat',
        'explosive_exercise': 'jump_squats',
        'rest_between_s': 90,
        'rest_after_pair_s': 180,
        'notes': 'Loaded squat → explosive jump.',
    },
    {
        'id': 'cp_07',
        'strength_exercise': 'deadlift_dumbbell',
        'explosive_exercise': 'kettlebell_swing',
        'rest_between_s': 90,
        'rest_after_pair_s': 180,
        'notes': 'Heavy hinge → explosive hinge.',
    },
    {
        'id': 'cp_08',
        'strength_exercise': 'single_leg_rdl',
        'explosive_exercise': 'single_leg_hop_forward',
        'rest_between_s': 90,
        'rest_after_pair_s': 180,
        'notes': 'Single-leg hinge → single-leg hop.',
    },
    {
        'id': 'cp_09',
        'strength_exercise': 'dumbbell_walking_lunge',
        'explosive_exercise': 'plyometric_lunge',
        'rest_between_s': 90,
        'rest_after_pair_s': 180,
        'notes': 'Loaded lunge → explosive lunge.',
    },
    {
        'id': 'cp_10',
        'strength_exercise': 'step_ups',
        'explosive_exercise': 'lateral_bound',
        'rest_between_s': 90,
        'rest_after_pair_s': 180,
        'notes': 'Step-up → lateral bound for COD power.',
    },
    {
        'id': 'cp_11',
        'strength_exercise': 'heavy_calf_raise',
        'explosive_exercise': 'pogo_jump_single_leg',
        'rest_between_s': 90,
        'rest_after_pair_s': 180,
        'notes': 'Heavy calf → reactive ankle stiffness. Achilles tendon contrast.',
    },
    {
        'id': 'cp_12',
        'strength_exercise': 'push_ups',
        'explosive_exercise': 'explosive_push_up',
        'rest_between_s': 90,
        'rest_after_pair_s': 180,
        'notes': 'Upper body contrast.',
    },
]

# ============================================================================
# POSTERIOR CHAIN EXERCISES — ordered by progression
# ============================================================================

POSTERIOR_CHAIN_EXERCISES = [
    # Glute max
    'glute_bridge', 'hip_thrust_bodyweight', 'hip_thrust_banded',
    'single_leg_glute_bridge', 'single_leg_hip_thrust',
    'barbell_hip_thrust',
    # Hamstrings
    'nordic_hamstring_curl', 'nordic_curl_weighted', 'nordic_curl_partner',
    'bodyweight_rdl', 'single_leg_rdl', 'banded_rdl', 'b_stance_rdl',
    'deadlift_dumbbell', 'barbell_rdl', 'trap_bar_deadlift',
    'sliding_leg_curl', 'single_leg_slider_curl',
    'hamstring_curls_standing', 'seated_hamstring_curl',
    # Glute med/min
    'copenhagen_plank', 'copenhagen_with_movement',
    'hip_abduction_standing', 'lateral_band_walks',
    # Explosive hinge
    'kettlebell_swing',
    # Calves
    'heavy_calf_raise', 'single_leg_calf_raise', 'heel_drop',
    # Posterior core
    'superman_hold', 'bird_dog', 'good_morning',
    'reverse_hyperextension',
    # Posterior-dominant compound
    'bulgarian_split_squats', 'step_ups', 'reverse_lunges',
    'barbell_back_squat', 'dumbbell_walking_lunge',
]

# ============================================================================
# LSI THRESHOLDS — per test category (R2-W2-2 / SB-11)
# ============================================================================
# A uniform symmetry band across all tests is wrong: measurement noise and
# the clinical meaning of a side-to-side gap differ by test type.
#   hop      ≥90 — hop-distance batteries conventionally use ≥90 % LSI as the
#                  symmetry benchmark (commonly cited from the ACL hop-test
#                  literature, e.g. Noyes et al. 1991 — verify edition).
#   cod      ≥90 — L/R 505-style times; no established band in common use —
#                  pragmatic: mirror the hop convention. evidence: pragmatic.
#   ybalance ≥94 — derived from the anterior-reach asymmetry >4 cm injury-risk
#                  marker (commonly cited as Plisky et al. 2006) expressed as
#                  a % of typical reach distance. evidence: pragmatic
#                  conversion of a cited cm threshold.
# KNOWN LIMITATION (shown to coaches in the methods doc): LSI is a ratio —
# a symmetrically WEAK athlete passes it. It screens asymmetry, not capacity.
LSI_THRESHOLDS = {
    'hop': 90,
    'cod': 90,
    'ybalance': 94,
}

# ============================================================================
# PLYOMETRIC GATES — safety clearance requirements
# ============================================================================

PLYOMETRIC_GATES = {
    'low_load': {
        'label': 'Low-Load Plyometrics',
        'examples': ['pogo_hop', 'skipping', 'lateral_shuffle', 'hurdle_step_over'],
        'requirements': {
            'min_football_level': 2,
            'lsi_min_pct': 80,
            'hop_score_min': 2,
            'pain_nrs_max': 2,
        },
    },
    'moderate_load': {
        'label': 'Moderate-Load Plyometrics',
        'examples': ['box_jump', 'hurdle_hop', 'broad_jump', 'single_leg_hop'],
        'requirements': {
            'min_football_level': 3,
            'lsi_min_pct': 85,
            'hop_score_min': 3,
            'nordic_score_min': 3,
            'pain_nrs_max': 1,
        },
    },
    'high_load': {
        'label': 'High-Load Plyometrics',
        'examples': ['depth_jump', 'reactive_single_leg_hop', 'resisted_sprint', 'single_leg_bound_series'],
        'requirements': {
            'min_football_level': 4,
            'lsi_min_pct': 90,
            'hop_score_min': 4,
            'nordic_score_min': 4,
            'sprint_score_min': 3,
            'pain_nrs_max': 0,
        },
    },
}

# ============================================================================
# FORCE-VELOCITY TENDENCY CONFIG
# ============================================================================
# R2-W2-7 annotation: individualised F-V profiling (train your deficit) is
# commonly cited from Morin & Samozino's force-velocity work — but their
# method uses measured sprint/jump kinetics, not 1-5 test bands. Our
# hop-vs-sprint score diff is a crude proxy; the ±10-20% emphasis weights
# are pragmatic — uncited, revisit. Direction (train the weaker quality)
# is the defensible part.

FV_TENDENCY_CONFIG = {
    # tendency is derived by comparing hop_score vs sprint_score
    'force_dominant': {
        'condition': 'hop_score > sprint_score + 1',
        'label': 'Force-Dominant',
        'description': 'Strong but slow — prioritise velocity and reactive work.',
        'training_emphasis': ['sprint_mechanics', 'reactive_plyometrics', 'contrast_speed'],
        # Set count multipliers: strength volume ×0.9, speed/contrast ×1.2
        'training_weight': {'strength': 0.9, 'plyometric': 1.2, 'speed': 1.2},
    },
    'velocity_dominant': {
        'condition': 'sprint_score > hop_score + 1',
        'label': 'Velocity-Dominant',
        'description': 'Fast but lacks strength — prioritise loaded eccentric and HSR.',
        'training_emphasis': ['hsr_posterior_chain', 'eccentric_overload', 'isometric_strength'],
        # More strength volume, less speed
        'training_weight': {'strength': 1.2, 'plyometric': 0.8, 'speed': 0.8},
    },
    'balanced': {
        'condition': 'abs(hop_score - sprint_score) <= 1',
        'label': 'Balanced F-V Profile',
        'description': 'Well-balanced — apply periodised variation of strength and speed.',
        'training_emphasis': ['contrast_training', 'periodised_hsr', 'sport_specific_speed'],
        'training_weight': {'strength': 1.0, 'plyometric': 1.0, 'speed': 1.0},
    },
}

# ============================================================================
# R2-W2-7 annotation (phases below): block-periodisation volume/intensity
# waves (accumulation -> intensification -> realisation -> deload) follow
# standard periodisation convention (commonly cited: Issurin's block
# periodisation reviews; Bompa's texts) — convention, not RCT evidence.
# All modifiers are within ±30% and the aggressive ones REDUCE load
# approaching competition (conservative direction). Exact percentages
# pragmatic — uncited, revisit.
# ============================================================================
# FOOTBALL PERIODISATION PHASES
# ============================================================================

FOOTBALL_PERIODISATION_PHASES = {
    # ── Competition-relative phases (used by _get_football_periodisation_phase) ──
    'accumulation': {
        'label': 'Accumulation',
        'name': 'Accumulation Block (7+ weeks to competition)',
        'weeks': None,
        'focus': 'High volume HSR — build work capacity and posterior chain',
        'sessions_per_week': 3,
        'intensity': 'moderate_high',
        'volume_modifier': 1.1,
        'intensity_modifier': 0.85,
    },
    'intensification': {
        'label': 'Intensification',
        'name': 'Intensification Block (4-6 weeks to competition)',
        'weeks': 3,
        'focus': 'Peak strength — HSR phase 3, contrast training',
        'sessions_per_week': 3,
        'intensity': 'high',
        'volume_modifier': 0.9,
        'intensity_modifier': 1.1,
    },
    'realisation': {
        'label': 'Realisation',
        'name': 'Realisation Block (1-3 weeks to competition)',
        'weeks': 2,
        'focus': 'Speed and power expression — reduce volume, sharpen movement quality',
        'sessions_per_week': 2,
        'intensity': 'very_high',
        'volume_modifier': 0.7,
        'intensity_modifier': 1.15,
    },
    'deload': {
        'label': 'Deload',
        'name': 'Competition Deload (0-1 week to competition)',
        'weeks': 1,
        'focus': 'Freshen up — activation only, no heavy loading',
        'sessions_per_week': 1,
        'intensity': 'low',
        'volume_modifier': 0.4,
        'intensity_modifier': 0.7,
    },
    # ── Season-based phases (for long-term planning) ──
    'pre_season_strength': {
        'label': 'Pre-Season Strength',
        'name': 'Pre-Season Strength Block',
        'weeks': 6,
        'focus': 'Max strength accumulation via HSR phase 2-3',
        'sessions_per_week': 3,
        'intensity': 'high',
        'volume_modifier': 1.0,
        'intensity_modifier': 1.0,
    },
    'pre_season_power': {
        'label': 'Pre-Season Power',
        'name': 'Pre-Season Power Block',
        'weeks': 4,
        'focus': 'Contrast training, plyometrics, sprint mechanics',
        'sessions_per_week': 3,
        'intensity': 'very_high',
        'volume_modifier': 0.85,
        'intensity_modifier': 1.1,
    },
    'in_season_maintenance': {
        'label': 'In-Season',
        'name': 'In-Season Maintenance',
        'weeks': None,
        'focus': 'HSR phase 1-2 to maintain gains; 1-2 sessions/week',
        'sessions_per_week': 2,
        'intensity': 'moderate',
        'volume_modifier': 0.75,
        'intensity_modifier': 0.9,
    },
    'post_season_recovery': {
        'label': 'Post-Season',
        'name': 'Post-Season Recovery',
        'weeks': 3,
        'focus': 'Active recovery, tissue tolerance restoration',
        'sessions_per_week': 2,
        'intensity': 'low',
        'volume_modifier': 0.6,
        'intensity_modifier': 0.7,
    },
}

# ============================================================================
# SPORT TYPES — used by athlete_sport field on PatientProfile
# ============================================================================

# ============================================================================
# P27: CONDITIONING PROTOCOLS — Energy System Training
# Prescribed by Talk Test (no HR monitor required).
# Research: Platonov three-zone model, Helgerud et al. 2007 (4x4), Hoff 2002.
# Persinger et al. 2004: Talk Test correlates r=0.84 with ventilatory threshold.
# ============================================================================

CONDITIONING_PROTOCOLS = {
    'zone_1_aerobic_base': {
        'name': 'Aerobic Base (Zone 1)',
        'zone': 1,
        'talk_test': 'You should be able to hold a full conversation comfortably throughout. If you cannot, slow down.',
        'rpe_target': '3-4 out of 10',
        'description': 'Build your aerobic engine. This feels easy — that is correct. Without this base, your body cannot recover between sprints during a match.',
        'protocol': {
            'type': 'continuous',
            'duration_minutes': 30,
            'instructions': 'Choose any activity: jogging, cycling, brisk walking, skipping rope. Maintain an easy pace for 30 minutes. You should be able to talk in full sentences the entire time.',
        },
        'modality_options': ['Easy jog', 'Cycling', 'Brisk walking', 'Skipping rope', 'Swimming'],
        'season': ['off_season', 'post_season'],
    },

    'zone_2_lactate_threshold': {
        'name': 'Lactate Threshold (Zone 2)',
        'zone': 2,
        'talk_test': 'You can speak in short sentences only — not full paragraphs. Breathing is noticeably harder.',
        'rpe_target': '5-6 out of 10',
        'description': 'Raise the speed at which your body accumulates fatigue. This is the pace where talking becomes difficult.',
        'protocol': {
            'type': 'intervals',
            'rounds': 4,
            'work_seconds': 480,
            'rest_seconds': 120,
            'work_label': 'Threshold pace — short sentences only',
            'rest_label': 'Easy jog — recover your breathing',
            'instructions': '4 rounds of 8 minutes at threshold pace with 2 minutes easy jog between rounds. Or: 2 x 15-20 minutes steady at threshold pace with 3 minutes rest.',
        },
        'modality_options': ['Running', 'Cycling', 'Football dribbling at pace'],
        'season': ['pre_season'],
    },

    'zone_3_vo2max': {
        'name': 'VO2max — Norwegian 4x4 (Zone 3)',
        'zone': 3,
        'talk_test': 'You can only say a few words. Cannot hold a conversation. Very hard breathing.',
        'rpe_target': '7-8 out of 10',
        'description': 'The Norwegian 4x4 protocol — the most researched VO2max method in existence. 4 rounds of 4 minutes hard, with 3 minutes easy between rounds. This improves your maximum oxygen uptake by up to 11% in 8 weeks.',
        'protocol': {
            'type': 'intervals',
            'rounds': 4,
            'work_seconds': 240,
            'rest_seconds': 180,
            'work_label': 'HARD — only a few words possible',
            'rest_label': 'Easy walking or light jog — recover',
            'instructions': '4 rounds of 4 minutes at very hard effort with 3 minutes easy walking/jogging between rounds. Start each round by building up to target intensity in the first minute.',
        },
        'modality_options': ['Running (uphill is best)', 'Cycling', 'Football dribbling at high intensity'],
        'season': ['off_season', 'pre_season', 'in_season'],
    },

    'rsa_repeat_sprint': {
        'name': 'Repeat Sprint Ability (RSA)',
        'zone': 4,
        'talk_test': 'Maximum effort. No talking possible. All-out sprint.',
        'rpe_target': '9-10 out of 10',
        'description': 'This is what separates general fitness from football fitness. RSA is your ability to sprint at maximum speed, recover in 25-30 seconds, and sprint again. When this is trained, you do not slow down in the second half.',
        'protocol': {
            'type': 'sprint_intervals',
            'sets': 3,
            'sprints_per_set': 6,
            'sprint_distance_metres': 30,
            'rest_between_sprints_seconds': 25,
            'rest_between_sets_seconds': 180,
            'instructions': '3 sets of 6 x 30-metre all-out sprints. 25-30 seconds passive rest (walk back) between sprints. 3 minutes full rest between sets. Every sprint must be maximum effort.',
        },
        'modality_options': ['Flat grass or track', 'Indoor court'],
        'season': ['pre_season', 'in_season'],
    },
}

# Maps season_phase to which conditioning protocols to recommend
CONDITIONING_SEASON_MAP = {
    'off_season': ['zone_1_aerobic_base', 'zone_3_vo2max'],
    'pre_season': ['zone_2_lactate_threshold', 'zone_3_vo2max', 'rsa_repeat_sprint'],
    'in_season': ['zone_3_vo2max'],
    'post_season': ['zone_1_aerobic_base'],
}


SPORT_TYPES = [
    ('football', 'Football (Soccer)'),
    ('rugby', 'Rugby'),
    ('basketball', 'Basketball'),
    ('cricket', 'Cricket'),
    ('athletics_sprints', 'Athletics — Sprints'),
    ('athletics_field', 'Athletics — Field Events'),
    ('tennis', 'Tennis'),
    ('badminton', 'Badminton'),
    ('swimming', 'Swimming'),
    ('cycling', 'Cycling'),
    ('martial_arts', 'Martial Arts / Combat Sports'),
    ('other_team', 'Other Team Sport'),
    ('other_individual', 'Other Individual Sport'),
]
