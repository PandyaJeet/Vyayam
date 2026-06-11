"""
VYAYAM V1 — Master Constants
All dosage tables, periodisation phases, goal modifiers, tempo system, rest periods.
"""

# ============================================================================
# 7 MOVEMENT PATTERNS
# ============================================================================

MOVEMENT_PATTERNS = [
    'squat', 'hinge', 'lunge', 'push', 'pull', 'rotate', 'carry'
]

# ============================================================================
# 12 END GOALS
# ============================================================================

GOAL_CONFIG = {
    'general_strength': {
        'label': 'General Strength',
        'available_to': ['male', 'female', 'not_specified'],
        'primary_phase': 'strength',
        'pattern_weights': {
            'squat': 1.0, 'hinge': 1.0, 'lunge': 1.0,
            'push': 1.0, 'pull': 1.0, 'rotate': 1.0, 'carry': 1.0,
        },
        'dosage_emphasis': 'strength',
        'power_unlocked': True,
    },
    'hypertrophy': {
        'label': 'Build Muscle',
        'available_to': ['male', 'female', 'not_specified'],
        'primary_phase': 'hypertrophy',
        'pattern_weights': {
            'squat': 1.0, 'hinge': 1.0, 'lunge': 1.0,
            'push': 1.0, 'pull': 1.0, 'rotate': 0.8, 'carry': 0.7,
        },
        'dosage_emphasis': 'hypertrophy',
        'power_unlocked': False,
    },
    'endurance': {
        'label': 'Endurance',
        'available_to': ['male', 'female', 'not_specified'],
        'primary_phase': 'endurance',
        'pattern_weights': {
            'squat': 0.8, 'hinge': 0.8, 'lunge': 0.8,
            'push': 0.8, 'pull': 0.8, 'rotate': 0.8, 'carry': 1.0,
        },
        'dosage_emphasis': 'endurance',
        'power_unlocked': False,
    },
    'strength_endurance': {
        'label': 'Strength + Endurance',
        'available_to': ['male', 'female', 'not_specified'],
        'primary_phase': 'alternating',
        'pattern_weights': {
            'squat': 1.0, 'hinge': 1.0, 'lunge': 1.0,
            'push': 1.0, 'pull': 1.0, 'rotate': 0.9, 'carry': 0.9,
        },
        'dosage_emphasis': 'mixed',
        'power_unlocked': True,
    },
    'calisthenics': {
        'label': 'Calisthenics Skills',
        'available_to': ['male', 'female', 'not_specified'],
        'primary_phase': 'skill',
        'pattern_weights': {
            'squat': 1.0, 'hinge': 0.8, 'lunge': 0.9,
            'push': 1.2, 'pull': 1.2, 'rotate': 1.0, 'carry': 0.6,
        },
        'dosage_emphasis': 'strength',
        'power_unlocked': True,
    },
    'fat_loss': {
        'label': 'Fat Loss',
        'available_to': ['male', 'female', 'not_specified'],
        'primary_phase': 'metabolic',
        'pattern_weights': {
            'squat': 1.0, 'hinge': 1.0, 'lunge': 1.0,
            'push': 1.0, 'pull': 1.0, 'rotate': 1.0, 'carry': 1.0,
        },
        'dosage_emphasis': 'metabolic',
        'power_unlocked': False,
    },
    'female_physique': {
        'label': 'Female Physique',
        'available_to': ['female'],
        'primary_phase': 'hypertrophy',
        'pattern_weights': {
            'squat': 1.0, 'hinge': 1.5, 'lunge': 1.3,
            'push': 0.8, 'pull': 0.9, 'rotate': 1.2, 'carry': 0.8,
        },
        'dosage_emphasis': 'hypertrophy',
        'power_unlocked': False,
        'notes': 'Hinge highest priority for glute development. Rotate high for waist definition.',
    },
    'athletic': {
        'label': 'Athletic Performance',
        'available_to': ['male', 'female', 'not_specified'],
        'primary_phase': 'power',
        'pattern_weights': {
            'squat': 1.0, 'hinge': 1.0, 'lunge': 1.2,
            'push': 0.9, 'pull': 0.9, 'rotate': 1.2, 'carry': 1.0,
        },
        'dosage_emphasis': 'power',
        'power_unlocked': True,
    },
    'rehabilitation': {
        'label': 'Rehabilitation',
        'available_to': ['male', 'female', 'not_specified'],
        'primary_phase': 'anatomical_adaptation',
        'pattern_weights': {
            'squat': 1.0, 'hinge': 1.0, 'lunge': 0.8,
            'push': 0.8, 'pull': 0.8, 'rotate': 1.0, 'carry': 0.7,
        },
        'dosage_emphasis': 'conservative',
        'power_unlocked': False,
    },
    'mobility': {
        'label': 'Mobility and Movement',
        'available_to': ['male', 'female', 'not_specified'],
        'primary_phase': 'mobility',
        'pattern_weights': {
            'squat': 0.8, 'hinge': 0.8, 'lunge': 0.8,
            'push': 0.6, 'pull': 0.6, 'rotate': 1.0, 'carry': 0.5,
        },
        'dosage_emphasis': 'mobility',
        'power_unlocked': False,
    },
    'posture': {
        'label': 'Posture Correction',
        'available_to': ['male', 'female', 'not_specified'],
        'primary_phase': 'corrective',
        'pattern_weights': {
            'squat': 0.7, 'hinge': 1.0, 'lunge': 0.7,
            'push': 0.8, 'pull': 1.3, 'rotate': 1.2, 'carry': 0.8,
        },
        'dosage_emphasis': 'corrective',
        'power_unlocked': False,
        'notes': 'Pull highest priority for upper crossed syndrome. Hinge for lower crossed.',
    },
    'healthy_ageing': {
        'label': 'Healthy and Active (50+)',
        'available_to': ['male', 'female', 'not_specified'],
        'primary_phase': 'conservative',
        'pattern_weights': {
            'squat': 1.0, 'hinge': 1.0, 'lunge': 1.0,
            'push': 0.8, 'pull': 0.8, 'rotate': 0.9, 'carry': 1.0,
        },
        'dosage_emphasis': 'conservative',
        'power_unlocked': False,
        'notes': 'Balance in every session. Heavy enough for bone density. No high impact.',
    },
}

# ============================================================================
# 9 DOSAGE TABLES — Each: capability (1-5) → (sets, reps, eccentric_s, pause_s, concentric_s, top_pause_s, rest_s)
# Tempo format: E-P-C-T (eccentric, pause, concentric, top)
# ============================================================================

DOSAGE_BILATERAL_STRENGTH = {
    1: None,  # Cannot do — skip
    2: {'sets': 2, 'reps': 6,  'tempo': '4-1-3-0', 'rest': 90},
    3: {'sets': 2, 'reps': 10, 'tempo': '3-1-2-0', 'rest': 75},
    4: {'sets': 3, 'reps': 12, 'tempo': '3-0-2-0', 'rest': 75},
    5: {'sets': 3, 'reps': 15, 'tempo': '2-0-2-0', 'rest': 60},
}

DOSAGE_UNILATERAL_STRENGTH = {
    1: None,
    2: {'sets': 2, 'reps': 5,  'tempo': '4-1-3-0', 'rest': 90},
    3: {'sets': 2, 'reps': 8,  'tempo': '3-1-2-0', 'rest': 75},
    4: {'sets': 3, 'reps': 10, 'tempo': '3-0-2-0', 'rest': 75},
    5: {'sets': 3, 'reps': 12, 'tempo': '2-0-2-0', 'rest': 60},
}

# ── Canonical form-score bands (DA-P6) ──────────────────────────────────
# One definition for what a form score MEANS, used by the session summary
# and the XP gate. Clinical rationale: below 55 the movement was performed
# unsafely (no reward, surfaced red); 55-79 is acceptable-but-imperfect
# (counts, no quality bonus); 80+ is good movement (green, bonus).
# NOTE: FormCalculator's AR overlay uses its own REAL-TIME display bands
# (>=85 green / >=70 yellow) — those colour individual FRAMES during the
# set and are deliberately stricter than these per-EXERCISE bands.
FORM_SCORE_GREEN = 80    # >= green
FORM_SCORE_YELLOW = 55   # >= yellow, below green
                          # < 55 = red / unsafe (matches MIN_FORM_SCORE_FOR_XP)

# Isometric / timed exercises (DA-P2 item 6): prescribed as a HOLD
# (duration), never as reps. The engine previously only selected the
# hold dosage table via the AA-phase override, so a wall sit prescribed
# in the strength phase got "3 x 8 reps" and the UI showed a rep counter.
HOLD_EXERCISE_IDS = {
    'wall_sit', 'planks', 'side_plank', 'side_plank_hip_dip',
    'side_plank_rotation', 'copenhagen_plank', 'hollow_body_hold',
    'superman_hold', 'handstand_wall_hold', 'single_arm_plank',
    'single_arm_single_leg_plank', 'pallof_press_isometric',
    'farmer_carry', 'suitcase_carry', 'waiter_carry',
    'single_arm_farmer_heavy', 'waiter_farmer_combined',
}

DOSAGE_ISOMETRIC_HOLD = {
    1: None,
    2: {'sets': 3, 'reps': 1, 'hold': 30, 'rest': 45},
    3: {'sets': 3, 'reps': 1, 'hold': 40, 'rest': 45},
    4: {'sets': 3, 'reps': 1, 'hold': 45, 'rest': 45},
    5: {'sets': 3, 'reps': 1, 'hold': 60, 'rest': 60},
}

DOSAGE_SLOW_ECCENTRIC = {
    1: None,
    2: {'sets': 2, 'reps': 4, 'tempo': '6-2-3-0', 'rest': 90},
    3: {'sets': 3, 'reps': 5, 'tempo': '5-1-3-0', 'rest': 90},
    4: {'sets': 3, 'reps': 6, 'tempo': '5-1-2-0', 'rest': 75},
    5: {'sets': 4, 'reps': 8, 'tempo': '4-1-2-0', 'rest': 75},
}

DOSAGE_STATIC_BALANCE = {
    1: None,
    2: {'sets': 2, 'reps': 1, 'hold': 15, 'rest': 30},
    3: {'sets': 2, 'reps': 1, 'hold': 25, 'rest': 30},
    4: {'sets': 3, 'reps': 1, 'hold': 35, 'rest': 45},
    5: {'sets': 3, 'reps': 1, 'hold': 45, 'rest': 45},
}

DOSAGE_CARDIO = {
    1: None,
    2: {'sets': 1, 'reps': 1, 'duration': 60,  'rest': 90},
    3: {'sets': 1, 'reps': 1, 'duration': 90,  'rest': 90},
    4: {'sets': 2, 'reps': 1, 'duration': 90,  'rest': 90},
    5: {'sets': 2, 'reps': 1, 'duration': 120, 'rest': 90},
}

DOSAGE_POWER = {
    1: None,
    2: {'sets': 2, 'reps': 3, 'tempo': '1-0-X-0', 'rest': 120},
    3: {'sets': 3, 'reps': 4, 'tempo': '1-0-X-0', 'rest': 120},
    4: {'sets': 3, 'reps': 5, 'tempo': '1-0-X-0', 'rest': 90},
    5: {'sets': 4, 'reps': 5, 'tempo': '1-0-X-0', 'rest': 90},
}

DOSAGE_STRETCHING = {
    'sedentary':         {'sets': 2, 'hold': 30, 'rest': 20},
    'moderately_active': {'sets': 2, 'hold': 40, 'rest': 20},
    'active':            {'sets': 3, 'hold': 45, 'rest': 20},
    'very_active':       {'sets': 3, 'hold': 45, 'rest': 20},
}

DOSAGE_ENDURANCE = {
    1: None,
    2: {'sets': 2, 'reps': 15, 'tempo': '2-0-2-0', 'rest': 45},
    3: {'sets': 3, 'reps': 18, 'tempo': '2-0-2-0', 'rest': 40},
    4: {'sets': 3, 'reps': 20, 'tempo': '2-0-1-0', 'rest': 35},
    5: {'sets': 4, 'reps': 25, 'tempo': '2-0-1-0', 'rest': 30},
}

# ============================================================================
# PERIODISATION PHASES — modifiers applied on top of base dosage
# ============================================================================

PERIODISATION_PHASES = {
    'anatomical_adaptation_iso': {
        'label': 'Anatomical Adaptation — Isometric',
        'weeks': [1, 2],
        'dosage_override': 'isometric_hold',
        'intensity_percent': '50-60%',
        'description': 'Isometric holds only. Preparing tendons and ligaments.',
    },
    'anatomical_adaptation_ecc': {
        'label': 'Anatomical Adaptation — Eccentric',
        'weeks': [3, 4],
        'dosage_override': 'slow_eccentric',
        'intensity_percent': '55-65%',
        'description': 'Slow eccentric loading for collagen remodelling.',
    },
    'hypertrophy': {
        'label': 'Hypertrophy',
        'weeks': [5, 6, 7],
        'sets_modifier': 0,
        'reps_modifier': 0,
        'tempo_override': '3-1-2-0',
        'rest_modifier': 0,
        'intensity_percent': '65-75%',
    },
    'hypertrophy_volume': {
        'label': 'Hypertrophy — Increased Volume',
        'weeks': [8, 9, 10],
        'sets_modifier': +1,
        'reps_modifier': -2,
        'tempo_override': '3-0-2-0',
        'rest_modifier': -15,
        'intensity_percent': '70-80%',
    },
    'strength': {
        'label': 'Strength',
        'weeks': [11],
        'sets_modifier': +1,
        'reps_modifier': -4,
        'tempo_override': '2-1-X-1',
        'rest_modifier': +60,
        'intensity_percent': '80-90%',
    },
    'deload': {
        'label': 'Deload',
        'weeks': [12],
        'sets_modifier': -1,
        'reps_modifier': 0,
        'tempo_override': '3-1-2-0',
        'rest_modifier': +15,
        'intensity_percent': '60%',
        'description': 'Active recovery. Volume reduced 40%. Movement maintained.',
    },
}

# ============================================================================
# SEX-SPECIFIC MODIFIERS
# ============================================================================

SEX_MODIFIERS = {
    'male': {
        'hinge_squat_ratio': 1.0,
        'pattern_weights_override': {},
        'rest_modifier': 0,
        'volume_modifier': 1.0,
        'notes': '',
    },
    'female': {
        'hinge_squat_ratio': 1.5,
        'pattern_weights_override': {
            'hinge': 1.2,
            'rotate': 1.1,
        },
        'rest_modifier': 0,
        'volume_modifier': 1.0,
        'acl_prevention_weight': 1.3,
        'notes': 'Glute med priority from day 1. Nordic hamstring earlier in progression.',
    },
    'not_specified': {
        'hinge_squat_ratio': 1.0,
        'pattern_weights_override': {},
        'rest_modifier': 0,
        'volume_modifier': 1.0,
        'notes': '',
    },
}

# ============================================================================
# HORMONAL PHASE MODIFIERS (female only)
# ============================================================================

HORMONAL_PHASE_MODIFIERS = {
    'follicular': {
        'volume_modifier': 1.0,
        'rest_modifier': 0,
        'plyometric_clearance': True,
        'notes': 'Oestrogen rising. Connective tissue stiffer. Best for strength work.',
    },
    'ovulation': {
        'volume_modifier': 1.0,
        'rest_modifier': 0,
        'plyometric_clearance': False,
        'warmup_extended': True,
        'notes': 'Peak ACL risk. Reduce plyometrics. Increase warm-up.',
    },
    'luteal': {
        'volume_modifier': 0.85,
        'rest_modifier': +20,
        'plyometric_clearance': True,
        'notes': 'Progesterone dominant. Fatigue more common. Volume reduced 15%.',
    },
    'menstruation': {
        'minimal':     {'volume_modifier': 1.0, 'rest_modifier': 0},
        'moderate':    {'volume_modifier': 0.6, 'rest_modifier': +30},
        'significant': {'volume_modifier': 0.4, 'rest_modifier': +30},
        'severe':      {'volume_modifier': 0.0, 'notes': 'Mobility and breathwork only.'},
    },
}

# ============================================================================
# AGE CAPS
# ============================================================================

AGE_CAPS = {
    'under_18': {'max_capability': 3, 'power_allowed': False, 'max_sets': 3, 'rest_modifier': 0},
    '18_29':    {'max_capability': 5, 'power_allowed': True,  'max_sets': 5, 'rest_modifier': 0},
    '30_49':    {'max_capability': 5, 'power_allowed': True,  'max_sets': 5, 'rest_modifier': 0},
    '50_64':    {'max_capability': 4, 'power_allowed': False, 'max_sets': 3, 'rest_modifier': +20},
    '65_plus':  {'max_capability': 3, 'power_allowed': False, 'max_sets': 2, 'rest_modifier': +40},
}


def get_age_bracket(age):
    if age < 18: return 'under_18'
    if age < 30: return '18_29'
    if age < 50: return '30_49'
    if age < 65: return '50_64'
    return '65_plus'


# ============================================================================
# TRAINING AGE → MINIMUM EFFECTIVE DOSE + AA PHASE DURATION
# ============================================================================

TRAINING_AGE_CONFIG = {
    'never':        {'min_sets': 2, 'aa_weeks': 4, 'start_capability_range': (1, 2)},
    'tried':        {'min_sets': 2, 'aa_weeks': 4, 'start_capability_range': (1, 2)},
    'beginner':     {'min_sets': 2, 'aa_weeks': 3, 'start_capability_range': (2, 3)},
    'intermediate': {'min_sets': 3, 'aa_weeks': 2, 'start_capability_range': (2, 3)},
    'advanced':     {'min_sets': 3, 'aa_weeks': 1, 'start_capability_range': (3, 4)},
}

# ============================================================================
# SLEEP / STRESS SESSION MODIFIERS
# ============================================================================

SLEEP_MODIFIERS = {
    'poor':     {'volume_modifier': 0.6, 'intensity_modifier': 0.7},
    'moderate': {'volume_modifier': 0.8, 'intensity_modifier': 0.85},
    'good':     {'volume_modifier': 1.0, 'intensity_modifier': 1.0},
    'variable': {'volume_modifier': 0.85, 'intensity_modifier': 0.9},
}

STRESS_MODIFIERS = {
    'low':       {'volume_modifier': 1.0},
    'moderate':  {'volume_modifier': 1.0},
    'high':      {'volume_modifier': 0.85},
    'very_high': {'volume_modifier': 0.7},
}

# ============================================================================
# REST PERIODS BY GOAL/PHASE (seconds between sets)
# ============================================================================

REST_BY_PHASE = {
    'anatomical_adaptation_iso': 60,
    'anatomical_adaptation_ecc': 90,
    'hypertrophy': 75,
    'hypertrophy_volume': 60,
    'strength': 150,
    'deload': 90,
}

REST_BY_GOAL_OVERRIDE = {
    'endurance': 40,
    'fat_loss': 50,
    'power': 120,
}

# ============================================================================
# TRAFFIC LIGHT LOAD MANAGEMENT
# ============================================================================

TRAFFIC_LIGHT_RULES = {
    'green': {
        'criteria': 'No pain, recovery >= 7/10, no new symptoms, sleep adequate',
        'action': 'Progress as planned',
    },
    'yellow': {
        'criteria': 'Mild soreness > 48h, recovery 4-6/10, slight stiffness',
        'action': 'Maintain current load. Do not advance. Monitor 3 sessions.',
    },
    'red': {
        'criteria': 'Pain > 4/10, new symptoms, recovery < 4/10',
        'action': 'Reduce volume 40%. Remove painful exercises. Flag for review if persists > 3 sessions.',
    },
}

# ============================================================================
# NEW EXERCISE INTRODUCTION LIMITS
# ============================================================================

NEW_EXERCISE_RULES = {
    'max_new_per_session': 2,
    'volume_reduction_when_introducing': 0.75,
    'doms_warning': True,
}

# ============================================================================
# PROGRESSION RULES
# ============================================================================

PROGRESSION_RULES = {
    'two_for_two': {
        'description': 'Complete 2 reps above target for 2 consecutive sessions to advance',
        'extra_reps_required': 2,
        'consecutive_sessions_required': 2,
    },
    'ladder_advance': {
        'description': 'Capability 5 → next exercise in chain. Reset to capability 3.',
        'reset_capability': 3,
        'volume_reduction_first_session': 0.8,
    },
    'plateau_detection_weeks': 3,
}

# ============================================================================
# DELOAD RULES
# ============================================================================

DELOAD_CONFIG = {
    'trigger_every_n_weeks': 4,
    'volume_reduction': 0.6,
    'intensity_reduction': 0.7,
    'duration_weeks': 1,
}

# ============================================================================
# CALISTHENICS SKILL MILESTONES
# ============================================================================

CALISTHENICS_PATHWAYS = {
    'pull_up': {
        'name': 'Pull-Up Pathway',
        'milestones': [
            {'id': 'dead_hang_45s', 'name': 'Dead Hang 45s', 'prerequisite': None},
            {'id': 'scapular_pulls_10', 'name': '10 Scapular Pulls', 'prerequisite': 'dead_hang_45s'},
            {'id': 'negative_pull_up_5', 'name': '5 Negative Pull-Ups (5s lowering)', 'prerequisite': 'scapular_pulls_10'},
            {'id': 'band_assisted_5', 'name': '5 Band-Assisted Pull-Ups', 'prerequisite': 'negative_pull_up_5'},
            {'id': 'full_pull_up_1', 'name': 'First Full Pull-Up', 'prerequisite': 'band_assisted_5'},
            {'id': 'full_pull_up_5', 'name': '5 Full Pull-Ups', 'prerequisite': 'full_pull_up_1'},
            {'id': 'weighted_pull_up', 'name': 'Weighted Pull-Up', 'prerequisite': 'full_pull_up_5'},
        ],
    },
    'pistol_squat': {
        'name': 'Pistol Squat Pathway',
        'milestones': [
            {'id': 'single_leg_balance_30s', 'name': 'Single Leg Balance 30s', 'prerequisite': None},
            {'id': 'assisted_pistol_5', 'name': '5 Assisted Pistols (hand on wall)', 'prerequisite': 'single_leg_balance_30s'},
            {'id': 'skater_squat_8', 'name': '8 Skater Squats', 'prerequisite': 'assisted_pistol_5'},
            {'id': 'pistol_to_box_5', 'name': '5 Pistol Squats to Box', 'prerequisite': 'skater_squat_8'},
            {'id': 'full_pistol_1', 'name': 'First Full Pistol', 'prerequisite': 'pistol_to_box_5'},
            {'id': 'full_pistol_5', 'name': '5 Full Pistols Each Leg', 'prerequisite': 'full_pistol_1'},
        ],
    },
    'handstand': {
        'name': 'Handstand Pathway',
        'milestones': [
            {'id': 'wall_plank_30s', 'name': 'Wall Plank 30s (feet on wall)', 'prerequisite': None},
            {'id': 'pike_push_up_10', 'name': '10 Pike Push-Ups', 'prerequisite': 'wall_plank_30s'},
            {'id': 'elevated_pike_8', 'name': '8 Elevated Pike Push-Ups', 'prerequisite': 'pike_push_up_10'},
            {'id': 'wall_handstand_10s', 'name': 'Wall Handstand Hold 10s', 'prerequisite': 'elevated_pike_8'},
            {'id': 'wall_handstand_30s', 'name': 'Wall Handstand Hold 30s', 'prerequisite': 'wall_handstand_10s'},
            {'id': 'wall_hspu_1', 'name': 'First Wall Handstand Push-Up', 'prerequisite': 'wall_handstand_30s'},
        ],
    },
}
