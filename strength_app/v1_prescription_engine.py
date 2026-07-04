"""
VYAYAM V1 — Prescription Engine

Main public function: generate_v1_session(patient)

Implements the full prescription formula:
  absolute stop → context → deload check → session split →
  per-pattern dosage → all 12 modifier layers → warm-up → cool-down
"""

import logging

from datetime import date, timedelta

# ── Football module imports (P21-P26) ────────────────────────────────────────
try:
    from .v1_football_constants import (
        FOOTBALL_LEVELS, HSR_PHASES, CONTRAST_PAIRS,
        POSTERIOR_CHAIN_EXERCISES, PLYOMETRIC_GATES,
        FV_TENDENCY_CONFIG, FOOTBALL_PERIODISATION_PHASES,
    )
    _FOOTBALL_AVAILABLE = True
except ImportError:
    _FOOTBALL_AVAILABLE = False

from .v1_constants import (
    MOVEMENT_PATTERNS,
    GOAL_CONFIG,
    PERIODISATION_PHASES,
    DOSAGE_BILATERAL_STRENGTH,
    DOSAGE_UNILATERAL_STRENGTH,
    DOSAGE_ISOMETRIC_HOLD,
    DOSAGE_SLOW_ECCENTRIC,
    DOSAGE_STATIC_BALANCE,
    DOSAGE_CARDIO,
    DOSAGE_POWER,
    DOSAGE_ENDURANCE,
    REST_BY_PHASE,
    REST_BY_GOAL_OVERRIDE,
    AGE_CAPS,
    get_age_bracket,
    DELOAD_CONFIG,
    NEW_EXERCISE_RULES,
    SEX_MODIFIERS,
    HORMONAL_PHASE_MODIFIERS,
)
from .v1_progression_chains import V1_PROGRESSION_CHAINS
from .v1_safety_logic import (
    build_patient_context,
    filter_exercises_for_patient,
    get_alternative_for_excluded,
    get_pain_pattern_escalation,
    limit_new_exercises,
    apply_female_acl_prevention,
    get_asymmetry_rules,
    compute_pattern_priorities,
    check_deload_needed,
    calculate_hormonal_phase,
    get_hormonal_modifiers,
    get_sex_adjustments,
    get_age_limits,
    get_return_session_adjustments,
    check_progression_ready,
)
from .warmup_library import (
    ELEVATE_EXERCISES,
    MOBILISE_EXERCISES,
    ACTIVATE_EXERCISES,
    COOLDOWN_LIGHT_MOVEMENT,
    COOLDOWN_STATIC_STRETCHES,
    COOLDOWN_BREATHING,
)


# ============================================================================
# DOSAGE TABLE LOOKUP
# ============================================================================

_DOSAGE_TABLE_MAP = {
    'isometric_hold': DOSAGE_ISOMETRIC_HOLD,
    'slow_eccentric':  DOSAGE_SLOW_ECCENTRIC,
    'bilateral':       DOSAGE_BILATERAL_STRENGTH,
    'unilateral':      DOSAGE_UNILATERAL_STRENGTH,
    'balance':         DOSAGE_STATIC_BALANCE,
    'cardio':          DOSAGE_CARDIO,
    'power':           DOSAGE_POWER,
    'endurance':       DOSAGE_ENDURANCE,
}

_PATTERN_EXERCISE_TAGS = {'cardio', 'balance', 'power'}


def _get_base_dosage_key(exercise_id, is_unilateral, goal_emphasis, phase):
    """
    Select which dosage table to use for this exercise.
    Priority: AA phase override > exercise characteristics > goal emphasis.
    """
    phase_data = PERIODISATION_PHASES.get(phase, {})
    override = phase_data.get('dosage_override')
    if override:
        return override  # 'isometric_hold' or 'slow_eccentric'

    # Exercise-level classification
    try:
        from .exercise_system.exercise_registry_v2 import EXERCISE_METADATA
        meta = EXERCISE_METADATA.get(exercise_id, {})
        category = meta.get('category', '') if isinstance(meta, dict) else ''
    except Exception:
        category = ''

    from .v1_constants import HOLD_EXERCISE_IDS
    if exercise_id in HOLD_EXERCISE_IDS:
        return 'isometric_hold'  # DA-P2 item 6: holds are timed, not repped

    if category == 'cardio':
        return 'cardio'
    if category == 'power' or 'jump' in exercise_id or 'depth_jump' in exercise_id:
        return 'power'
    if 'balance' in exercise_id or 'single_leg_balance' in exercise_id:
        return 'balance'

    if goal_emphasis == 'endurance':
        return 'endurance'

    return 'unilateral' if is_unilateral else 'bilateral'


# ============================================================================
# HORMONAL MODIFIER — handles the nested 'menstruation' structure
# ============================================================================

def _resolve_hormonal_modifiers(patient, hormonal_phase):
    """Delegates to v1_safety_logic.get_hormonal_modifiers — the single
    source of truth for hormonal modifiers (DA-C15). Kept as a thin alias
    so existing engine call sites are untouched."""
    return get_hormonal_modifiers(hormonal_phase, patient=patient)


# ============================================================================
# PERIODISATION STATE MANAGEMENT
# ============================================================================

def _get_or_create_periodisation(patient):
    """
    Return the patient's PeriodisationState, creating one if needed.
    New patients start at anatomical_adaptation_iso week 1.
    """
    from .models import PeriodisationState
    state, created = PeriodisationState.objects.get_or_create(
        patient=patient,
        defaults={
            'current_phase': 'anatomical_adaptation_iso',
            'current_week': 1,
            'macrocycle_number': 1,
            'weeks_since_deload': 0,
            'phase_start_date': date.today(),
            # DA-C11: anchor the calendar deload gate at the start of
            # loading. Without this, a patient training less often than
            # sessions_per_week could go far beyond 4 calendar weeks
            # before the session-counted gate fired (no date to check).
            'last_deload_date': date.today(),
        },
    )
    return state


# ============================================================================
# SESSION SPLIT — which patterns to train today
# ============================================================================

def _determine_todays_patterns(patient, pattern_priorities, sessions_per_week=3):
    """
    Determine which movement patterns to train today based on:
    - sessions_per_week (3/4/5+)
    - which session number this is in the current week
    - pattern priority (add HIGH-priority pattern if absent)

    Kinetic chain principle: squat (quad) paired with hinge (posterior);
    push (anterior) paired with pull (posterior).
    """
    from .models import WorkoutSession
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    sessions_this_week = WorkoutSession.objects.filter(
        patient=patient,
        session_date__date__gte=week_start,
    ).count()

    spw = max(1, sessions_per_week)
    day_number = (sessions_this_week % spw) + 1

    if spw <= 3:
        splits = {
            1: ['squat', 'hinge', 'rotate'],
            2: ['push', 'pull', 'carry'],
            3: ['lunge', 'rotate'],
        }
    elif spw == 4:
        splits = {
            1: ['squat', 'hinge'],
            2: ['push', 'pull'],
            3: ['lunge', 'rotate'],
            4: ['push', 'pull', 'carry'],
        }
    else:
        splits = {
            1: ['squat', 'hinge'],
            2: ['push', 'pull'],
            3: ['lunge', 'rotate'],
            4: ['squat', 'hinge'],
            5: ['push', 'pull', 'carry', 'rotate'],
        }

    patterns_today = list(splits.get(day_number, ['squat', 'hinge', 'rotate']))

    # Add one HIGH-priority pattern if not already present
    high_patterns = [p for p in pattern_priorities if p not in patterns_today]
    if high_patterns:
        patterns_today.append(high_patterns[0])

    return patterns_today, day_number


# ============================================================================
# EXERCISE SELECTION PER PATTERN
# ============================================================================

def _select_exercises_for_pattern(pattern, capability, patient, age_limits):
    """
    Select 1-2 exercises for a pattern at the patient's capability level.
    Falls back one level if no safe exercises found at current level.
    Returns a list of exercise_id strings.
    """
    chain = V1_PROGRESSION_CHAINS.get(pattern)
    if not chain:
        return []

    capped_capability = min(capability, age_limits.get('max_capability', 5))
    capped_capability = max(1, capped_capability)

    # Red-flag level caps (e.g. ACL grade 1-2 → lunge ≤ level 3)
    from .red_flag_map import get_pattern_level_caps
    red_flags = patient.red_flags_json or []
    level_caps = get_pattern_level_caps(red_flags)
    if pattern in level_caps:
        capped_capability = min(capped_capability, level_caps[pattern])

    levels = chain.get('levels', [])
    if capped_capability > len(levels):
        capped_capability = len(levels)

    level_data = levels[capped_capability - 1]  # 0-indexed
    candidates = list(level_data.get('exercises', []))

    safe = filter_exercises_for_patient(patient, candidates)

    if not safe and capped_capability > 1:
        fallback_data = levels[capped_capability - 2]
        safe = filter_exercises_for_patient(patient, list(fallback_data.get('exercises', [])))

    return safe


# ============================================================================
# DOSAGE CALCULATION
# ============================================================================

def _calculate_dosage(exercise_id, capability, pattern, priority,
                      phase, goal_type, sex_adj, hormonal_mods,
                      recovery_vol_mod, age_limits, is_unilateral,
                      is_deload, patient_sex, goal_config=None):
    """
    Calculate final sets/reps/hold/tempo/rest after all modifier layers.
    Returns a dict: {sets, reps, hold_duration, tempo, rest_seconds}
    """
    if goal_config is None:
        goal_config = GOAL_CONFIG.get(goal_type, GOAL_CONFIG['general_strength'])
    goal_emphasis = goal_config.get('dosage_emphasis', 'strength')
    phase_data = PERIODISATION_PHASES.get(phase, {})

    # 1. Select base dosage table
    dosage_key = _get_base_dosage_key(exercise_id, is_unilateral, goal_emphasis, phase)
    table = _DOSAGE_TABLE_MAP.get(dosage_key, DOSAGE_BILATERAL_STRENGTH)

    cap = min(max(1, capability), 5)
    base = table.get(cap)
    if base is None:
        # capability 1 = cannot do — fallback to level 2
        base = table.get(2)
    if base is None:
        base = {'sets': 2, 'reps': 8, 'tempo': '3-1-2-0', 'rest': 75}

    sets = base.get('sets', 2)
    reps = base.get('reps', 8)
    hold = base.get('hold', 0)
    tempo = base.get('tempo', '3-1-2-0')
    rest = base.get('rest', 75)

    # 2. Phase modifier (sets / reps / tempo / rest)
    has_override = bool(phase_data.get('dosage_override'))
    if not has_override:
        sets += phase_data.get('sets_modifier', 0)
        reps += phase_data.get('reps_modifier', 0)
        tempo = phase_data.get('tempo_override', tempo)
        rest += phase_data.get('rest_modifier', 0)

    # 3. Goal → pattern weight → set count
    goal_weights = goal_config.get('pattern_weights', {})
    goal_weight = goal_weights.get(pattern, 1.0)
    sex_weights = sex_adj.get('pattern_weights_override', {})
    if patient_sex == 'female' and pattern in sex_weights:
        goal_weight *= sex_weights[pattern]
    if goal_weight >= 1.2:
        sets += 1
    elif goal_weight <= 0.7:
        sets -= 1

    # 4. Pattern priority modifier
    if priority == 'high':
        sets += 1
    elif priority == 'maintenance':
        sets = max(1, sets - 1)

    # 5. Sex modifier — hinge:squat ratio
    if patient_sex == 'female' and pattern == 'hinge':
        hsr = sex_adj.get('hinge_squat_ratio', 1.0)
        if hsr > 1.0:
            sets = round(sets * min(hsr, 1.5))

    # 6. Recovery modifier (combined sleep × stress × traffic light)
    sets = max(1, round(sets * recovery_vol_mod))

    # 7. Hormonal modifier
    h_vol = hormonal_mods.get('volume_modifier', 1.0)
    sets = max(1, round(sets * h_vol))
    rest += hormonal_mods.get('rest_modifier', 0)

    # 8. Deload modifier
    if is_deload:
        vol_red = DELOAD_CONFIG.get('volume_reduction', 0.6)
        sets = max(1, round(sets * vol_red))

    # 9. Age cap
    sets = min(sets, age_limits.get('max_sets', 5))
    reps = max(1, reps)

    # 10. Rest period (phase-based → goal override → age → sex → hormonal → traffic)
    base_rest = REST_BY_PHASE.get(phase, rest)
    goal_rest = REST_BY_GOAL_OVERRIDE.get(goal_emphasis)
    if goal_rest is not None:
        base_rest = goal_rest
    base_rest += age_limits.get('rest_modifier', 0)
    base_rest += sex_adj.get('rest_modifier', 0)
    base_rest += hormonal_mods.get('rest_modifier', 0)
    if recovery_vol_mod < 0.7:
        base_rest += 30

    return {
        'sets': sets,
        'reps': reps if hold == 0 else 0,
        'hold_duration': hold,
        'tempo': tempo,
        'rest_seconds': max(30, base_rest),
    }


# ============================================================================
# ASYMMETRY RULES FOR AN EXERCISE
# ============================================================================

def _get_exercise_asymmetry(pattern, asymmetry_rules):
    """Return asymmetry block for the working set dict."""
    rule_data = asymmetry_rules.get(pattern, {})
    asymmetry_level = rule_data.get('asymmetry', 'none')
    weaker_side = rule_data.get('weaker_side', '')
    is_unilateral = asymmetry_level != 'none'

    extra_sets = 0
    if asymmetry_level == 'moderate':
        extra_sets = 1
    elif asymmetry_level == 'significant':
        extra_sets = 2

    return {
        'rule': asymmetry_level,
        'weaker_side': weaker_side,
        'weaker_side_first': bool(weaker_side),
        'extra_sets_weak': extra_sets,
    }


# ============================================================================
# CONTENT ATTACHMENT
# ============================================================================

def _attach_content(exercise_dict):
    """Attach mind-muscle cues and form cues from exercise_content."""
    try:
        from .exercise_content import EXERCISE_CONTENT
        content = EXERCISE_CONTENT.get(exercise_dict.get('exercise_id', ''), {})
        exercise_dict['mind_muscle_cue'] = content.get('mind_muscle_cue', None)
        exercise_dict['form_cues'] = content.get('form_cues', [])
        exercise_dict['instructions'] = content.get('instructions', [])
        exercise_dict['language_beginner'] = content.get('language_beginner', '')
        exercise_dict['language_experienced'] = content.get('language_experienced', '')
        exercise_dict['language_athlete'] = content.get('language_athlete', '')
    except Exception:
        exercise_dict['mind_muscle_cue'] = None
        exercise_dict['form_cues'] = []
        exercise_dict['instructions'] = []
        exercise_dict['language_beginner'] = ''
        exercise_dict['language_experienced'] = ''
        exercise_dict['language_athlete'] = ''
    return exercise_dict


def _get_exercise_name(exercise_id):
    """Get display name from EXERCISE_METADATA."""
    try:
        from .exercise_system.exercise_registry_v2 import EXERCISE_METADATA
        meta = EXERCISE_METADATA.get(exercise_id)
        if meta is None:
            return exercise_id.replace('_', ' ').title()
        if isinstance(meta, dict):
            return meta.get('name', exercise_id.replace('_', ' ').title())
        # LazyRegistry — try the class attribute
        return getattr(meta, 'name', exercise_id.replace('_', ' ').title())
    except Exception:
        return exercise_id.replace('_', ' ').title()


def _is_unilateral(exercise_id):
    """Check unilateral flag from EXERCISE_METADATA."""
    try:
        from .exercise_system.exercise_registry_v2 import EXERCISE_METADATA
        meta = EXERCISE_METADATA.get(exercise_id)
        if meta is None:
            return False
        if isinstance(meta, dict):
            return bool(meta.get('unilateral', False))
        return bool(getattr(meta, 'unilateral', False))
    except Exception:
        return False


# ============================================================================
# WARM-UP BUILDER
# ============================================================================

def _determine_day_type(patterns_today):
    """Map today's patterns to a warm-up day type key."""
    if 'squat' in patterns_today or 'lunge' in patterns_today:
        if 'hinge' in patterns_today:
            return 'squat_day'
        return 'lunge_day' if 'lunge' in patterns_today else 'squat_day'
    if 'hinge' in patterns_today:
        return 'hinge_day'
    if 'push' in patterns_today or 'pull' in patterns_today:
        return 'push_pull_day'
    if 'rotate' in patterns_today:
        return 'rotate_day'
    return 'squat_day'


def _build_warmup(patterns_today, working_sets, hormonal_mods, patient=None):
    """Build the 4-phase warm-up sequence. Football athletes get FIFA 11+ (P32)."""

    # ── P32: FIFA 11+ for football athletes ──────────────────────────────
    if (patient and hasattr(patient, 'athlete_tier_active') and patient.athlete_tier_active
            and getattr(patient, 'athlete_sport', '') == 'football'):
        try:
            from .warmup_library import (
                FIFA_11_PART1_RUNNING, FIFA_11_PART2_STRENGTH, FIFA_11_PART3_RUNNING_ADVANCED
            )
            # Determine level from football profile
            fp = patient.football_profile
            level = getattr(fp, 'football_level', 1)
            if level >= 4:
                lvl_key = 'level_3'
            elif level >= 3:
                lvl_key = 'level_2'
            else:
                lvl_key = 'level_1'

            return {
                'estimated_minutes': 20,
                'is_fifa_11': True,
                'phases': {
                    'part1_running': FIFA_11_PART1_RUNNING.get(lvl_key, FIFA_11_PART1_RUNNING['level_1']),
                    'part2_strength': FIFA_11_PART2_STRENGTH.get(lvl_key, FIFA_11_PART2_STRENGTH['level_1']),
                    'part3_advanced_running': FIFA_11_PART3_RUNNING_ADVANCED.get(lvl_key, FIFA_11_PART3_RUNNING_ADVANCED['level_1']),
                },
            }
        except Exception:
            pass  # Fall through to standard warmup if FIFA data unavailable


    day_type = _determine_day_type(patterns_today)

    # DA-P3F: warm-up items must respect the patient's red-flag
    # exclusions too — a flagged patient must not get excluded movement
    # patterns injected via the warm-up ('jumping_jacks_light' is the
    # same movement as the excluded 'jumping_jacks').
    red_flag_excluded = set()
    if patient is not None:
        try:
            from .red_flag_map import get_excluded_exercises
            red_flag_excluded = set(get_excluded_exercises(patient.red_flags_json or []))
        except Exception:
            logging.getLogger(__name__).warning(
                'red-flag warmup filter unavailable', exc_info=True)

    def _warmup_ok(item):
        wid = item.get('id', '')
        return wid not in red_flag_excluded and wid.removesuffix('_light') not in red_flag_excluded

    # Phase 1: Elevate — first 3 exercises, skip high-impact if plyometric not cleared
    plyometric_ok = hormonal_mods.get('plyometric_clearance', True)
    elevate = []
    for ex in ELEVATE_EXERCISES:
        if not plyometric_ok and ex.get('id') in ('jumping_jacks_light', 'star_jumps_light'):
            continue
        if not _warmup_ok(ex):
            continue
        elevate.append(ex)
        if len(elevate) >= 3:
            break

    # Phase 2: Mobilise
    mobilise = [m for m in MOBILISE_EXERCISES.get(day_type, MOBILISE_EXERCISES.get('squat_day', []))
                if _warmup_ok(m)]
    if hormonal_mods.get('warmup_extended'):
        extra = [m for m in mobilise[:2]]
        mobilise = mobilise + extra

    # Phase 3: Activate
    activate = []
    if any(p in patterns_today for p in ('squat', 'hinge', 'lunge')):
        activate.extend(ACTIVATE_EXERCISES.get('glute_activation', []))
    if any(p in patterns_today for p in ('squat', 'lunge')):
        activate.extend(ACTIVATE_EXERCISES.get('vmo_activation', []))
    if any(p in patterns_today for p in ('push', 'pull')):
        activate.extend(ACTIVATE_EXERCISES.get('scapular_activation', []))
    activate.extend(ACTIVATE_EXERCISES.get('deep_core_activation', []))
    activate = [a for a in activate if _warmup_ok(a)]

    # Phase 4: Prime — first working exercise at 30% effort
    prime = []
    if working_sets:
        first = working_sets[0]
        prime_reps = max(1, round((first.get('reps') or 5) * 0.5))
        prime.append({
            'exercise_id': first['exercise_id'],
            'exercise_name': first['exercise_name'],
            'sets': 2,
            'reps': prime_reps,
            'hold_duration': 0,
            'intensity': '30%',
            'notes': 'Neural priming — light, controlled, perfect form',
        })

    elevate_mins = 4
    mobilise_mins = 5
    activate_mins = 4
    prime_mins = 2
    total_mins = elevate_mins + mobilise_mins + activate_mins + prime_mins

    return {
        'estimated_minutes': total_mins,
        'phases': {
            'elevate': elevate,
            'mobilise': mobilise,
            'activate': activate,
            'prime': prime,
        },
    }


# ============================================================================
# COOL-DOWN BUILDER
# ============================================================================

def _build_cooldown(patterns_today):
    """Build the 3-phase cool-down sequence."""
    day_type = _determine_day_type(patterns_today)

    light_movement = list(COOLDOWN_LIGHT_MOVEMENT[:3])
    static_stretch = list(
        COOLDOWN_STATIC_STRETCHES.get(day_type, COOLDOWN_STATIC_STRETCHES.get('squat_day', []))
    )
    breathing = list(COOLDOWN_BREATHING[:1])

    return {
        'estimated_minutes': 10,
        'phases': {
            'light_movement': light_movement,
            'static_stretch': static_stretch,
            'breathing': breathing,
        },
    }


# ============================================================================
# MOBILITY-ONLY SESSION
# ============================================================================

def _build_mobility_only_session(patient, meta):
    """Return a mobility/breathwork only session for severe menstrual pain."""
    from .models import PeriodisationState
    state = _get_or_create_periodisation(patient)

    warmup = {
        'estimated_minutes': 20,
        'phases': {
            'elevate': [ELEVATE_EXERCISES[0]],
            'mobilise': list(MOBILISE_EXERCISES.get('rotate_day', [])),
            'activate': list(ACTIVATE_EXERCISES.get('deep_core_activation', [])),
            'prime': [],
        },
    }
    cooldown = {
        'estimated_minutes': 15,
        'phases': {
            'light_movement': list(COOLDOWN_LIGHT_MOVEMENT[:3]),
            'static_stretch': list(
                COOLDOWN_STATIC_STRETCHES.get('rotate_day',
                COOLDOWN_STATIC_STRETCHES.get('squat_day', []))
            ),
            'breathing': list(COOLDOWN_BREATHING[:2]),
        },
    }
    return {
        'status': 'mobility_only',
        'stop_reason': '',
        'meta': meta,
        'modifiers_applied': {
            'volume_modifier': 0.0,
            'intensity_modifier': 0.0,
            'rest_modifier': 0,
            'hormonal_phase': 'menstruation',
            'traffic_light': 'green',
            'notes': ['Severe menstrual symptoms — mobility and breathwork only today.'],
        },
        'warmup': warmup,
        'working_sets': [],
        'cooldown': cooldown,
        'session_summary': {
            'total_exercises': 0,
            'total_sets': 0,
            'patterns_trained': [],
            'new_exercises_count': 0,
            'doms_warning': False,
            'deload_note': 'Mobility-only session. No strength loading today.',
        },
    }


# ============================================================================
# KNOWN EXERCISE SET (for new-exercise detection)
# ============================================================================

def _get_patient_known_exercises(patient):
    """
    Return set of exercise IDs this patient has already done at least once.
    Used for Principle 20: repeated-bout effect / new exercise limiting.
    """
    try:
        from .models import ExerciseExecution
        ids = ExerciseExecution.objects.filter(
            session__patient=patient
        ).values_list('exercise_id', flat=True).distinct()
        return set(ids)
    except Exception:
        return set()


# ============================================================================
# LAST SESSION TRAFFIC LIGHT
# ============================================================================

def _get_last_traffic_light(patient):
    """Return the traffic light string from the most recent session feedback."""
    try:
        fb = patient.session_feedbacks.order_by('-created_at').first()
        return fb.traffic_light if fb else 'green'
    except Exception:
        return 'green'


def _traffic_light_volume_modifier(traffic_light):
    if traffic_light == 'red':
        return 0.7
    if traffic_light == 'yellow':
        return 0.85
    return 1.0


# ============================================================================
# DURATION ESTIMATE
# ============================================================================

def _estimate_duration(warmup_mins, working_sets, cooldown_mins):
    """Estimate total session duration in minutes."""
    work_mins = 0
    for ex in working_sets:
        sets = ex.get('sets', 2)
        reps = ex.get('reps', 8) or 1
        hold = ex.get('hold_duration', 0)
        rest = ex.get('rest_seconds', 75)
        if hold > 0:
            active_s = sets * (hold + 5)  # hold + transition
        else:
            tempo_parts = ex.get('tempo', '3-1-2-0').split('-')
            try:
                rep_time = sum(int(x) if x.isdigit() else 2 for x in tempo_parts)
            except Exception:
                rep_time = 6
            active_s = sets * reps * rep_time
        rest_s = sets * rest
        work_mins += (active_s + rest_s) / 60
    return round(warmup_mins + work_mins + cooldown_mins)


# ============================================================================
# GOAL BLENDING
# ============================================================================

def _get_blended_goal_config(patient):
    """
    Blend pattern_weights from up to 3 goals.
    Primary: 60% weight, Secondary: 30%, Tertiary: 10%.
    Returns (blended_goal_config, primary_goal_key).
    """
    import json

    all_goals = []
    try:
        raw = patient.goals
        if raw and raw.startswith('['):
            all_goals = json.loads(raw)
    except (json.JSONDecodeError, AttributeError):
        pass

    if not all_goals:
        all_goals = [g for g in [patient.goal_type, getattr(patient, 'goal_secondary', '')] if g]
    if not all_goals:
        all_goals = ['general_strength']

    primary_key = all_goals[0]
    primary_config = GOAL_CONFIG.get(primary_key, GOAL_CONFIG['general_strength'])

    if len(all_goals) == 1:
        return primary_config, primary_key

    # Blend pattern weights
    blend_weights = [0.6, 0.3, 0.1]
    blended_patterns = {}
    for pattern in ['squat', 'hinge', 'lunge', 'push', 'pull', 'rotate', 'carry']:
        total = 0.0
        weight_sum = 0.0
        for i, goal_key in enumerate(all_goals[:3]):
            cfg = GOAL_CONFIG.get(goal_key, GOAL_CONFIG['general_strength'])
            pw = cfg.get('pattern_weights', {}).get(pattern, 1.0)
            w = blend_weights[i] if i < len(blend_weights) else 0.0
            total += pw * w
            weight_sum += w
        blended_patterns[pattern] = round(total / max(weight_sum, 0.01), 2)

    blended_config = dict(primary_config)
    blended_config['pattern_weights'] = blended_patterns
    blended_config['_blended_goals'] = all_goals[:3]
    return blended_config, primary_key


# ============================================================================
# FOOTBALL P21-P26 — Session Modifier for Athlete Tier
# ============================================================================

def _apply_football_principles(patient, working_sets, meta, modifier_notes, vol_modifier):
    """
    Apply P21-P26 football principles on top of the standard session.
    Called only when patient.athlete_tier_active and patient.athlete_sport == 'football'.
    Modifies working_sets in place; returns additional exercises to append.
    """
    if not _FOOTBALL_AVAILABLE:
        return []

    try:
        fp = patient.football_profile
    except Exception:
        return []

    level = fp.football_level or 1
    level_config = FOOTBALL_LEVELS.get(level, FOOTBALL_LEVELS[1])
    fv_config = FV_TENDENCY_CONFIG.get(fp.fv_tendency, FV_TENDENCY_CONFIG['balanced'])
    fv_weights = fv_config.get('training_weight', {})

    additional_exercises = []

    # ── P25: Posterior Chain Emphasis ────────────────────────────────────────
    posterior_ids = set(POSTERIOR_CHAIN_EXERCISES)
    posterior_count = sum(1 for ex in working_sets if ex['exercise_id'] in posterior_ids)
    total_count = max(len(working_sets), 1)
    current_ratio = posterior_count / total_count
    target_ratio = level_config.get('posterior_anterior_ratio', 0.55)

    if current_ratio < target_ratio - 0.1:
        hsr_phase_key = fp.hsr_current_phase or level_config.get('hsr_phase', 'hsr_phase_1')
        hsr_config = HSR_PHASES.get(hsr_phase_key, HSR_PHASES['hsr_phase_1'])
        hsr_exercises = hsr_config.get('exercises', [])
        for hsr_ex in hsr_exercises:
            if not any(ex['exercise_id'] == hsr_ex for ex in working_sets):
                hsr_phase_num = hsr_phase_key.replace('hsr_phase_', '')
                additional_exercises.append({
                    'exercise_id': hsr_ex,
                    'exercise_name': hsr_ex.replace('_', ' ').title(),
                    'movement_pattern': 'hinge',
                    'pattern_priority': 'high',
                    'capability_level': min(level + 1, 5),
                    'sets': hsr_config.get('sets', 3),
                    'reps': int(hsr_config.get('rep_range', '6-8').split('-')[0]),
                    'hold_duration': 0,
                    'tempo': hsr_config.get('tempo', '3-0-3'),
                    'rest_seconds': 120,
                    'is_unilateral': 'single' in hsr_ex or 'nordic' in hsr_ex,
                    'asymmetry': {},
                    'is_new_exercise': False,
                    'notes': f'HSR Phase {hsr_phase_num} — tendon stiffness development (P24)',
                    'priority_rank': 0,
                    'football_tag': 'hsr',
                })
                modifier_notes.append(f'P25: Added posterior chain exercise {hsr_ex} (ratio {current_ratio:.0%} → target {target_ratio:.0%})')
                break

    # ── P24: HSR Protocol — mark existing HSR exercises with correct tempo ──
    hsr_phase_key = fp.hsr_current_phase or level_config.get('hsr_phase', 'hsr_phase_1')
    hsr_config = HSR_PHASES.get(hsr_phase_key, HSR_PHASES['hsr_phase_1'])
    hsr_tempo = hsr_config.get('tempo', '3-0-3')
    hsr_phase_num = hsr_phase_key.replace('hsr_phase_', '')
    hsr_exercise_set = set(hsr_config.get('exercises', []))
    for ex in working_sets:
        if ex['exercise_id'] in hsr_exercise_set:
            ex['tempo'] = hsr_tempo
            existing = ex.get('notes', '')
            ex['notes'] = (existing + ' | ' if existing else '') + f'HSR Phase {hsr_phase_num} tempo (P24)'

    # ── P21: Compensatory Acceleration Intent Cues ────────────────────────
    explosive_patterns = {'squat', 'hinge', 'lunge'}
    for ex in working_sets:
        if ex.get('movement_pattern') in explosive_patterns:
            existing = ex.get('notes', '')
            if 'INTENT:' not in existing:
                ex['notes'] = (existing + ' | ' if existing else '') + 'INTENT: Move as fast as possible on every rep (P21 — compensatory acceleration)'

    # ── P21: Contrast Training Pairs (Level 3+) ──────────────────────────
    if level_config.get('contrast_training', False):
        for pair in CONTRAST_PAIRS:
            strength_id = pair.get('strength_exercise', '')
            explosive_id = pair.get('explosive_exercise', '')
            if any(ex['exercise_id'] == strength_id for ex in working_sets):
                if not any(ex['exercise_id'] == explosive_id for ex in working_sets):
                    plyo_weight = fv_weights.get('plyometric', 1.0)
                    contrast_sets = max(2, round(3 * plyo_weight))
                    additional_exercises.append({
                        'exercise_id': explosive_id,
                        'exercise_name': explosive_id.replace('_', ' ').title(),
                        'movement_pattern': 'power',
                        'pattern_priority': 'high',
                        'capability_level': level,
                        'sets': contrast_sets,
                        'reps': 5,
                        'hold_duration': 0,
                        'tempo': 'X-0-X-0',
                        'rest_seconds': int(pair.get('rest_between_s', 90)),
                        'is_unilateral': 'single' in explosive_id,
                        'asymmetry': {},
                        'is_new_exercise': False,
                        'notes': f'Contrast pair with {strength_id} — rest {pair.get("rest_between_s", 90)}s between (P21)',
                        'priority_rank': 0,
                        'football_tag': 'contrast',
                    })
                    modifier_notes.append(f'P21: Contrast pair — {strength_id} → {explosive_id}. Rest 5-6 min between heavy and explosive set (PAP window 4-8 min).')
                    break

    # ── P22: Plyometric Gating ────────────────────────────────────────────
    if not fp.plyometric_cleared or fp.plyometric_cleared == 'none':
        blocked_keywords = ['depth_jump', 'drop_jump', 'hurdle_hop', 'box_jump']
        before = len(working_sets)
        working_sets[:] = [
            ex for ex in working_sets
            if not any(kw in ex['exercise_id'] for kw in blocked_keywords)
        ]
        removed = before - len(working_sets)
        if removed:
            modifier_notes.append(f'P22: Blocked {removed} high-load plyometric(s) — gate not cleared')
        additional_exercises = [
            ex for ex in additional_exercises
            if not any(kw in ex['exercise_id'] for kw in blocked_keywords)
        ]

    # ── P22 ext: Plyometric volume cap per session ────────────────────────
    plyo_contact_limit = 100  # beginner default
    if hasattr(fp, 'football_level'):
        if fp.football_level >= 4:
            plyo_contact_limit = 200
        elif fp.football_level >= 3:
            plyo_contact_limit = 150
    # Match week reduction: check via microcycle helper
    try:
        _mc_days, _mc_type = _get_microcycle_day(patient)
        if _mc_days is not None and 0 < _mc_days <= 5:
            plyo_contact_limit = int(plyo_contact_limit * 0.6)
            modifier_notes.append(f'P22: Match week — plyometric contacts capped at {plyo_contact_limit} (40% reduction)')
        else:
            modifier_notes.append(f'P22: Plyometric volume cap: {plyo_contact_limit} contacts this session')
    except Exception:
        modifier_notes.append(f'P22: Plyometric volume cap: {plyo_contact_limit} contacts this session')

    # ── P26: F-V Tendency Weighting ──────────────────────────────────────
    strength_weight = fv_weights.get('strength', 1.0)
    speed_weight = fv_weights.get('speed', 1.0)
    if strength_weight != 1.0:
        for ex in working_sets:
            if ex.get('movement_pattern') in explosive_patterns:
                ex['sets'] = max(1, round(ex['sets'] * strength_weight))
    if speed_weight != 1.0:
        for ex in additional_exercises:
            if ex.get('football_tag') == 'contrast':
                ex['sets'] = max(2, round(ex['sets'] * speed_weight))

    # ── P23: Reactive Agility Flag (Level 4+) ────────────────────────────
    if level_config.get('reactive_agility', False):
        modifier_notes.append('P23: Reactive agility unlocked — add visual-cue response drills in warmup')

    meta['football_level'] = level
    meta['football_fv_tendency'] = fp.fv_tendency
    meta['football_hsr_phase'] = hsr_phase_num
    meta['is_football_session'] = True

    return additional_exercises


def _get_football_periodisation_phase(patient):
    """
    Determine football periodisation phase.
    Priority:
    1. competition_date set → weeks-to-competition micro-phases
    2. No competition_date → season_phase from FootballProfile
    3. Fallback → in_season_maintenance
    """
    if not _FOOTBALL_AVAILABLE:
        return None, None

    # Priority 1: competition date drives micro-periodisation
    comp_date = patient.competition_date
    if comp_date:
        weeks_to_comp = (comp_date - date.today()).days / 7
        if weeks_to_comp <= 0:
            key = 'in_season_maintenance'
        elif weeks_to_comp <= 1:
            key = 'deload'
        elif weeks_to_comp <= 3:
            key = 'realisation'
        elif weeks_to_comp <= 6:
            key = 'intensification'
        else:
            key = 'accumulation'
        return key, FOOTBALL_PERIODISATION_PHASES.get(key, {})

    # Priority 2: season context from FootballProfile
    try:
        fp = patient.football_profile
        season = fp.season_phase
        season_map = {
            'off_season': 'accumulation',
            'pre_season': 'pre_season_strength',
            'in_season': 'in_season_maintenance',
            'post_season': 'post_season_recovery',
        }
        key = season_map.get(season, 'in_season_maintenance')
        return key, FOOTBALL_PERIODISATION_PHASES.get(key, {})
    except Exception:
        pass

    # Fallback
    return 'in_season_maintenance', FOOTBALL_PERIODISATION_PHASES.get('in_season_maintenance', {})


def _get_microcycle_day(patient):
    """
    P29: Match microcycle management.
    Reads MatchDate calendar, calculates days to next match.
    Returns (days_to_match: int or None, session_type: str).
    Session types: 'strength', 'power_speed', 'light_activation',
                   'neural_prime', 'match_day', 'recovery',
                   'return_to_training', 'standard'.
    """
    from .models import MatchDate

    try:
        fp = patient.football_profile
        if fp.season_phase in ('off_season', 'post_season'):
            return None, 'standard'
    except Exception:
        return None, 'standard'

    today = date.today()

    # Next upcoming match
    next_match = MatchDate.objects.filter(
        patient=patient, match_date__gte=today
    ).order_by('match_date').first()

    if not next_match:
        return None, 'standard'

    days_to = (next_match.match_date - today).days

    # Most recent past match for MD+1/MD+2
    last_match = MatchDate.objects.filter(
        patient=patient, match_date__lt=today
    ).order_by('-match_date').first()

    days_since_last = None
    if last_match:
        days_since_last = (today - last_match.match_date).days

    # MD+1 and MD+2 take priority if very recent
    if days_since_last == 1:
        return -1, 'recovery'
    if days_since_last == 2:
        return -2, 'return_to_training'

    # Double gameweek: match just played AND next match within 3 days
    if days_since_last is not None and days_since_last <= 2 and days_to <= 3:
        if days_to <= 1:
            return days_to, 'neural_prime'
        return days_to, 'light_activation'

    # Standard microcycle
    if days_to == 0:
        return 0, 'match_day'
    elif days_to == 1:
        return 1, 'neural_prime'
    elif days_to == 2:
        return 2, 'light_activation'
    elif days_to == 3:
        return 3, 'power_speed'
    elif days_to == 4:
        return 4, 'strength'
    elif days_to == 5:
        return 5, 'recovery'
    else:
        # 6+ days: standard periodised session
        return days_to, 'standard'


def _advance_hsr_phase(patient, fp):
    """
    Auto-advance HSR phase after 4 weeks of completion.
    Works with string phase keys ('hsr_phase_1', 'hsr_phase_2', 'hsr_phase_3').
    """
    if not _FOOTBALL_AVAILABLE:
        return False

    PHASE_ORDER = ['hsr_phase_1', 'hsr_phase_2', 'hsr_phase_3']
    current = fp.hsr_current_phase
    if current not in PHASE_ORDER:
        return False

    hsr_config = HSR_PHASES.get(current, {})
    phase_weeks = hsr_config.get('weeks', 4)
    current_idx = PHASE_ORDER.index(current)

    if fp.hsr_weeks_completed >= phase_weeks and current_idx < len(PHASE_ORDER) - 1:
        fp.hsr_current_phase = PHASE_ORDER[current_idx + 1]
        fp.hsr_weeks_completed = 0
        # Re-anchor phase-start so the next phase counts from zero (SB-5b).
        try:
            fp.hsr_phase_start_week = patient.periodisation.current_week
        except Exception:
            # DA-P4: None (not 0) = unanchored; re-anchors on next session
            fp.hsr_phase_start_week = None
        fp.save(update_fields=['hsr_current_phase', 'hsr_weeks_completed', 'hsr_phase_start_week'])
        return True
    return False


# ============================================================================
# MAIN PUBLIC FUNCTION
# ============================================================================

def _freeze_advancement_for_patterns(patient, patterns):
    """DA-F3: pain follow-through — block ladder advancement for the
    implicated families until sessions are pain-free."""
    try:
        from .models import PatientFamilyCapability
        family_ids = [f'{p}_family' for p in patterns]
        PatientFamilyCapability.objects.filter(
            patient=patient, family_id__in=family_ids
        ).update(ready_to_advance=False)
    except Exception:
        logging.getLogger(__name__).warning(
            'could not freeze advancement for %s', patterns, exc_info=True)


def _note_pain_pause_to_professionals(patient, patterns):
    """DA-F3: tell the linked coach/therapist when a pattern is paused."""
    stamp = (
        f"\n[FLAGGED {date.today()}] Pattern(s) paused after pain in 3 "
        f"consecutive sessions: {', '.join(sorted(patterns))}. Patient "
        f"advised to consider physiotherapy review."
    )
    try:
        from .models import CoachPatientLink
        for link in CoachPatientLink.objects.filter(patient=patient, is_active=True):
            if stamp.strip() not in (link.notes or ''):
                link.notes = (link.notes or '') + stamp
                link.save(update_fields=['notes'])
        if patient.user_id:
            from therapist_app.models import TherapistPatientLink
            for tlink in TherapistPatientLink.objects.filter(
                    patient=patient.user, status='active'):
                if stamp.strip() not in (tlink.notes or ''):
                    tlink.notes = (tlink.notes or '') + stamp
                    tlink.save(update_fields=['notes'])
    except Exception:
        logging.getLogger(__name__).warning(
            'pain pause note failed', exc_info=True)


def generate_v1_session(patient):
    """
    Generate a complete V1 training session for a patient.

    Returns a session dict conforming to the spec. All 20 physio principles
    are encoded in this function and its helpers.
    """
    # ── 0. Absolute stop (Principle 0 — do no harm) ──────────────────────
    if patient.absolute_stop:
        return {
            'status': 'stopped',
            'stop_reason': patient.absolute_stop_reason or 'Absolute stop flag is set. Please consult your clinician.',
            'meta': {'patient_id': patient.patient_id, 'patient_name': patient.name},
            'modifiers_applied': {}, 'warmup': {}, 'working_sets': [],
            'cooldown': {}, 'session_summary': {},
        }

    # ── 0b. Drop-off / gap detection (Task 4) ────────────────────────────
    gap_adj = get_return_session_adjustments(patient)
    if gap_adj.get('redirect_to_onboarding'):
        return {
            'status': 'reassess',
            'stop_reason': gap_adj['message'],
            'meta': {'patient_id': patient.patient_id, 'patient_name': patient.name},
            'modifiers_applied': {'gap_adjustment': 'full_reassessment'},
            'warmup': {}, 'working_sets': [], 'cooldown': {}, 'session_summary': {},
        }

    # ── 1. Build full patient context ────────────────────────────────────
    context = build_patient_context(patient)

    # ── 2. Periodisation state ───────────────────────────────────────────
    state = _get_or_create_periodisation(patient)
    current_phase = state.current_phase
    is_deload = current_phase == 'deload'

    # Deload override — Principle 6
    deload_needed, deload_reason = check_deload_needed(patient, state)
    if deload_needed and not is_deload:
        current_phase = 'deload'
        is_deload = True

    phase_data = PERIODISATION_PHASES.get(current_phase, {})

    # ── 3. Age caps ──────────────────────────────────────────────────────
    age_bracket = get_age_bracket(patient.age)
    age_limits = AGE_CAPS.get(age_bracket, AGE_CAPS['18_29'])

    # ── 4. Hormonal modifiers — Principle 18 (female integration) ────────
    hormonal_phase = calculate_hormonal_phase(patient)
    hormonal_mods = _resolve_hormonal_modifiers(patient, hormonal_phase)

    # Mobility-only session for severe menstrual pain
    meta_pre = {
        'patient_id': patient.patient_id,
        'patient_name': patient.name,
        'goal_type': patient.goal_type,
        'periodisation_phase': current_phase,
        'current_week': state.current_week,
        'macrocycle': state.macrocycle_number,
        'is_deload': is_deload,
        'session_number': state.total_sessions_this_cycle + 1,
        'estimated_duration_minutes': 35,
    }
    if hormonal_mods.get('mobility_only'):
        return _build_mobility_only_session(patient, meta_pre)

    # ── 5. Sex adjustments ───────────────────────────────────────────────
    sex_adj = get_sex_adjustments(patient)
    patient_sex = patient.biological_sex or 'not_specified'

    # ── 6. Sleep / stress / traffic light recovery modifiers ─────────────
    # Principle 16 (sleep), 19 (traffic light)
    from .v1_constants import SLEEP_MODIFIERS, STRESS_MODIFIERS
    sleep_mod = SLEEP_MODIFIERS.get(patient.sleep_quality or 'good', {})
    stress_mod = STRESS_MODIFIERS.get(patient.stress_level or 'moderate', {})
    last_tl = _get_last_traffic_light(patient)
    tl_vol_mod = _traffic_light_volume_modifier(last_tl)

    gap_vol_mod = gap_adj.get('volume_modifier', 1.0)
    vol_modifier = (
        sleep_mod.get('volume_modifier', 1.0)
        * stress_mod.get('volume_modifier', 1.0)
        * tl_vol_mod
        * gap_vol_mod
    )
    int_modifier = sleep_mod.get('intensity_modifier', 1.0)

    # Gap adjustment flags
    if gap_adj.get('no_new_exercises'):
        _gap_max_new = 0  # Override: no new exercises for returning patients
    else:
        _gap_max_new = None  # Will use default from NEW_EXERCISE_RULES
    request_slow_tempo = bool(gap_adj.get('tempo_slow'))

    modifier_notes = []
    if vol_modifier < 0.9:
        modifier_notes.append(f'Volume reduced (sleep: {patient.sleep_quality}, stress: {patient.stress_level}, traffic: {last_tl})')
    if gap_adj.get('message'):
        modifier_notes.append(gap_adj['message'])
    if is_deload and deload_reason:
        modifier_notes.append(f'Deload triggered: {deload_reason}')
    if hormonal_phase:
        modifier_notes.append(f'Hormonal phase: {hormonal_phase}')

    # ── Nutrition traffic light adjustment ────────────────────────────────
    try:
        from datetime import date as _date, timedelta as _td
        from .v1_nutrition_engine import get_daily_nutrition_summary as _get_nutrition
        yesterday_nutrition = _get_nutrition(patient, _date.today() - _td(days=1))
        if yesterday_nutrition['traffic_light'] == 'red' and yesterday_nutrition['log_count'] > 0:
            vol_modifier *= 0.90
            modifier_notes.append('Volume reduced 10%: yesterday\'s nutrition was under-fuelled (red).')
        elif yesterday_nutrition['traffic_light'] == 'yellow' and yesterday_nutrition['log_count'] > 0:
            modifier_notes.append('Nutrition yesterday was slightly under target (yellow) — consider eating more today.')
    except Exception:
        pass  # Nutrition module not set up for this patient — skip silently

    # ── 7. Strength profile & pattern priorities ──────────────────────────
    strength_profile = patient.strength_profiles.order_by('-assessed_at').first()

    score_map = {'squat': 2, 'hinge': 2, 'lunge': 2, 'push': 2, 'pull': 2, 'rotate': 2, 'carry': 2}
    if strength_profile:
        score_map = {
            'squat':  strength_profile.squat_score or 2,
            'hinge':  strength_profile.hinge_score or 2,
            'push':   strength_profile.push_score or 2,
            'pull':   strength_profile.pull_score or 2,
            'rotate': strength_profile.rotate_score or 2,
            'lunge':  strength_profile.lunge_score or 2,
            'carry':  2,
        }

    pattern_priorities_ordered = compute_pattern_priorities(patient, strength_profile)
    # Build priority dict: first 2 = high, last 2 = maintenance, rest = standard
    n = len(pattern_priorities_ordered)
    priority_map = {}
    for i, p in enumerate(pattern_priorities_ordered):
        if i < 2:
            priority_map[p] = 'high'
        elif i >= n - 2:
            priority_map[p] = 'maintenance'
        else:
            priority_map[p] = 'standard'

    # ── 8. Asymmetry rules ────────────────────────────────────────────────
    asymmetry_rules = get_asymmetry_rules(strength_profile) if strength_profile else {}

    # ── 9. Session split — which patterns today ───────────────────────────
    # Principle 11 (kinetic chain antagonist pairing)
    spw = patient.sessions_per_week or 3
    patterns_today, day_number = _determine_todays_patterns(patient, pattern_priorities_ordered, spw)

    # ── 10. Known exercises (for new-exercise detection) ─────────────────
    known_exercises = _get_patient_known_exercises(patient)
    goal_config, goal_type = _get_blended_goal_config(patient)

    # ── 10b. Pain-pattern follow-through (DA-F3) ──────────────────────────
    # Same pain location in 2 consecutive sessions → regress the implicated
    # pattern one capability level and freeze advancement; 3 consecutive →
    # pause the pattern entirely and suggest a physiotherapist.
    pain_escalation = {'regress': set(), 'pause': set()}
    try:
        pain_escalation = get_pain_pattern_escalation(patient)
    except Exception:
        logging.getLogger(__name__).warning(
            'pain escalation check failed', exc_info=True)
    if pain_escalation['regress'] or pain_escalation['pause']:
        _freeze_advancement_for_patterns(
            patient, pain_escalation['regress'] | pain_escalation['pause'])
    if pain_escalation['pause']:
        _note_pain_pause_to_professionals(patient, pain_escalation['pause'])

    # ── 11. Build working sets ────────────────────────────────────────────
    raw_working_sets = []
    for pattern in patterns_today:
        capability = min(score_map.get(pattern, 2), age_limits.get('max_capability', 5))
        priority = priority_map.get(pattern, 'standard')

        if pattern in pain_escalation['pause']:
            modifier_notes.append(
                f'{pattern.title()} work paused — you have reported pain '
                f'there in 3 sessions in a row. Please consider seeing a '
                f'physiotherapist before loading it again.'
            )
            continue
        if pattern in pain_escalation['regress']:
            capability = max(1, capability - 1)
            modifier_notes.append(
                f'{pattern.title()} eased back a level — pain reported in '
                f'2 sessions in a row. It will rebuild once sessions are '
                f'pain-free.'
            )

        exercise_ids = _select_exercises_for_pattern(pattern, capability, patient, age_limits)
        if not exercise_ids:
            # DA-P4-2 (wires Phase-6 item 6): every exercise for this
            # pattern was excluded (red flags / equipment). Instead of
            # silently dropping the pattern, try the red-flag map's safe
            # alternative; if none, surface the drop in the notes.
            alt = get_alternative_for_excluded(patient, '', pattern)
            if alt and filter_exercises_for_patient(patient, [alt]):
                exercise_ids = [alt]
                modifier_notes.append(
                    f'{pattern.title()} swapped to a safer alternative '
                    f'based on your screening.'
                )
            else:
                modifier_notes.append(
                    f'{pattern.title()} work skipped today — no safe '
                    f'exercise available for your current screening/equipment.'
                )
                continue

        # How many exercises per pattern
        num_to_pick = 2 if priority == 'high' else 1
        selected_ids = exercise_ids[:num_to_pick]

        for ex_id in selected_ids:
            unilateral = _is_unilateral(ex_id)

            # Block power exercises if not allowed
            if 'jump' in ex_id or 'depth' in ex_id:
                if not age_limits.get('power_allowed', True):
                    continue
                if not goal_config.get('power_unlocked', True):
                    continue
                if not hormonal_mods.get('plyometric_clearance', True):
                    continue

            dosage = _calculate_dosage(
                exercise_id=ex_id,
                capability=capability,
                pattern=pattern,
                priority=priority,
                phase=current_phase,
                goal_type=goal_type,
                sex_adj=sex_adj,
                hormonal_mods=hormonal_mods,
                recovery_vol_mod=vol_modifier,
                age_limits=age_limits,
                is_unilateral=unilateral,
                is_deload=is_deload,
                patient_sex=patient_sex,
                goal_config=goal_config,
            )

            is_new = ex_id not in known_exercises
            asym = _get_exercise_asymmetry(pattern, asymmetry_rules)

            # Apply slow tempo for returning patients
            if request_slow_tempo:
                dosage['tempo'] = '4-2-3-1'

            ex_dict = {
                'exercise_id': ex_id,
                'exercise_name': _get_exercise_name(ex_id),
                'movement_pattern': pattern,
                'pattern_priority': priority,
                'capability_level': capability,
                'sets': dosage['sets'],
                'reps': dosage['reps'],
                'hold_duration': dosage['hold_duration'],
                'tempo': dosage['tempo'],
                'rest_seconds': dosage['rest_seconds'],
                'is_unilateral': unilateral,
                'asymmetry': asym,
                'is_new_exercise': is_new,
                'notes': '',
                'priority_rank': len(raw_working_sets),
            }
            ex_dict = _attach_content(ex_dict)

            # Apply asymmetry extra sets (Principle 8)
            asym_data = asym
            extra = asym_data.get('extra_sets_weak', 0)
            if extra > 0 and unilateral:
                ex_dict['sets_weak_side'] = dosage['sets'] + extra
                ex_dict['sets_strong_side'] = dosage['sets']
                modifier_notes.append(
                    f"{ex_dict.get('exercise_name', '')}: +{extra} set(s) on weaker side"
                )
            if asym_data.get('weaker_side'):
                ex_dict['asymmetry_side'] = asym_data['weaker_side']

            raw_working_sets.append(ex_dict)

    # ── Progression check (Principle 3: 2-for-2 rule) ──────────────────
    if strength_profile and not is_deload:
        from .models import PatientFamilyCapability
        seen_patterns = set()
        for ex_dict in raw_working_sets:
            pattern = ex_dict.get('movement_pattern', '')
            if pattern in seen_patterns:
                continue
            seen_patterns.add(pattern)
            capability = score_map.get(pattern, 2)
            age_max_cap = age_limits.get('max_capability', 5)
            # Block progression when significant asymmetry exists (safety gate)
            asym_rule = asymmetry_rules.get(pattern, {})
            if asym_rule.get('asymmetry') == 'significant':
                modifier_notes.append(
                    f'{pattern.title()} progression BLOCKED: significant asymmetry — '
                    f'resolve bilateral deficit before advancing.'
                )
                continue
            if capability < age_max_cap:
                fc = patient.family_capabilities.filter(
                    family_id__startswith=pattern
                ).first()
                if fc and check_progression_ready(fc):
                    new_cap = min(capability + 1, age_max_cap)  # never exceed age cap
                    score_map[pattern] = new_cap
                    setattr(strength_profile, f'{pattern}_score', new_cap)
                    strength_profile.save(update_fields=[f'{pattern}_score'])
                    modifier_notes.append(f'{pattern.title()} pattern advanced to level {new_cap}!')
                elif fc:
                    from .v1_safety_logic import detect_plateau
                    is_plateau, plateau_msg = detect_plateau(fc)
                    if is_plateau:
                        modifier_notes.append(plateau_msg)

    # ── 12. Limit new exercises — Principle 20 (repeated bout effect) ────
    # Gap adjustment can override to 0 (no new exercises for returning patients)
    max_new = _gap_max_new if _gap_max_new is not None else NEW_EXERCISE_RULES.get('max_new_per_session', 2)
    working_sets = []
    new_count = 0
    for ex in raw_working_sets:
        if ex['is_new_exercise']:
            if new_count < max_new:
                new_count += 1
                working_sets.append(ex)
            else:
                # Replace with a known exercise from the same pattern
                # (silently drop for now — future: swap to known exercise)
                pass
        else:
            working_sets.append(ex)

    # ── 13. Female ACL prevention — add nordic cue if applicable ─────────
    # Principle 17 (ACL prevention for females)
    _, acl_notes = apply_female_acl_prevention(patient, working_sets)
    if acl_notes:
        for ex in working_sets:
            if ex.get('movement_pattern') in ('lunge', 'squat', 'hinge'):
                existing = ex.get('notes', '')
                ex['notes'] = (existing + ' | ' if existing else '') + acl_notes[0]
                break

    # Session meta — created BEFORE the football block, which writes into it
    # (microcycle/HSR/periodisation keys). It previously didn't exist until
    # after this block, so every active football athlete crashed with
    # UnboundLocalError and silently got no session (DA-C4 follow-on find).
    meta = {}

    # ── 13b. Football P21-P26 integration ─────────────────────────────────
    if (hasattr(patient, 'athlete_tier_active') and patient.athlete_tier_active
            and patient.athlete_sport == 'football' and _FOOTBALL_AVAILABLE):

        # ── P29: Match microcycle management ──────────────────────────────
        days_to_match, microcycle_type = _get_microcycle_day(patient)
        meta['microcycle_type'] = microcycle_type
        if days_to_match is not None:
            meta['days_to_match'] = days_to_match

        # Match day: no training
        if microcycle_type == 'match_day':
            return {
                'status': 'match_day',
                'stop_reason': 'Match day — no training prescribed. Good luck!',
                'meta': {'patient_id': patient.patient_id, 'patient_name': patient.name,
                         'microcycle_type': 'match_day'},
                'modifiers_applied': {'notes': ['P29: Match day — rest.']},
                'warmup': {}, 'working_sets': [], 'cooldown': {}, 'session_summary': {},
            }

        # Light days: MD-2, MD-1 — strip to mobility/activation only
        if microcycle_type in ('light_activation', 'neural_prime'):
            modifier_notes.append(f'P29: {microcycle_type.replace("_", " ").title()} day — minimal loading')
            # Keep only stretching/mobility exercises, drop all strength
            working_sets[:] = [
                ex for ex in working_sets
                if ex.get('movement_pattern') in ('stretching', 'mobility', 'balance')
            ]
            # Cap at 3 exercises max
            working_sets[:] = working_sets[:3]
            for ex in working_sets:
                ex['sets'] = min(ex['sets'], 2)

        # Recovery: MD+1, MD-5 — very light
        elif microcycle_type == 'recovery':
            modifier_notes.append('P29: Recovery day — light mobility only')
            working_sets[:] = [
                ex for ex in working_sets
                if ex.get('movement_pattern') in ('stretching', 'mobility', 'balance')
            ]
            working_sets[:] = working_sets[:2]

        # Return to training: MD+2
        elif microcycle_type == 'return_to_training':
            modifier_notes.append('P29: Return to training day — reduced volume')
            vol_modifier *= 0.7

        # Power/speed day: MD-3
        elif microcycle_type == 'power_speed':
            modifier_notes.append('P29: Power/speed day (MD-3) — plyometrics and contrast pairs prioritised')
            # Reduce heavy strength sets, keep explosive work
            for ex in working_sets:
                if ex.get('movement_pattern') not in ('power', 'plyometric'):
                    ex['sets'] = max(1, ex['sets'] - 1)

        # Strength day: MD-4 — standard heavy session, no modification needed
        elif microcycle_type == 'strength':
            modifier_notes.append('P29: Strength day (MD-4) — full loading')

        # P31 (ACWR) removed by standing decision R2 (2026-06 deep audit):
        # ACWR is a discredited composite injury-risk metric and must not be
        # computed or surfaced anywhere. session_rpe capture stays (useful
        # for load/recovery trends). Do not reintroduce a replacement score.

        # ── Apply football principles P21-P26 ────────────────────────────
        football_extras = _apply_football_principles(
            patient, working_sets, meta, modifier_notes, vol_modifier
        )
        # DA-P4-1: football extras (HSR / plyo contrast pairs) must respect
        # red-flag and equipment exclusions like every other exercise — a
        # flagged athlete must not get excluded plyometrics injected.
        if football_extras:
            extra_ids = [fx['exercise_id'] for fx in football_extras]
            safe_extra_ids = set(filter_exercises_for_patient(patient, extra_ids))
            dropped = [eid for eid in extra_ids if eid not in safe_extra_ids]
            if dropped:
                modifier_notes.append(
                    'Removed for safety based on your screening: '
                    + ', '.join(d.replace('_', ' ') for d in dropped)
                )
            for fx in football_extras:
                if fx['exercise_id'] not in safe_extra_ids:
                    continue
                fx = _attach_content(fx)
                working_sets.append(fx)

        # Competition periodisation — adjust volume if competition date is set
        fb_phase_key, fb_phase_cfg = _get_football_periodisation_phase(patient)
        if fb_phase_key and fb_phase_cfg:
            fb_vol_mod = fb_phase_cfg.get('volume_modifier', 1.0)
            for ex in working_sets:
                ex['sets'] = max(1, round(ex['sets'] * fb_vol_mod))
            meta['football_periodisation_phase'] = fb_phase_key
            modifier_notes.append(
                f'Football periodisation: {fb_phase_cfg.get("label", fb_phase_key)} '
                f'(vol ×{fb_vol_mod})'
            )

        # HSR phase advancement check
        try:
            _advance_hsr_phase(patient, patient.football_profile)
        except Exception:
            # D4: a failed tendon-loading progression must leave a trace.
            logging.getLogger(__name__).warning(
                'HSR phase advancement failed for %s',
                getattr(patient, 'patient_id', '?'), exc_info=True)

    # ── 14. Warm-up (Principle 14 / P32 FIFA 11+ for football) ───────────
    warmup = _build_warmup(patterns_today, working_sets, hormonal_mods, patient=patient)

    # ── 15. Cool-down (Principle 15) ──────────────────────────────────────
    cooldown = _build_cooldown(patterns_today)

    # ── 16. Session duration estimate ────────────────────────────────────
    # ── Duration enforcement — trim exercises to fit patient's time budget ──
    target_duration = patient.session_duration_minutes or 60
    warmup_mins = warmup['estimated_minutes']
    cooldown_mins = cooldown['estimated_minutes']
    estimated_duration = _estimate_duration(warmup_mins, working_sets, cooldown_mins)

    # Trim lowest-priority exercises until we fit the time budget
    if estimated_duration > target_duration and len(working_sets) > 1:
        indexed = [(i, ex.get('priority_rank', 99)) for i, ex in enumerate(working_sets)]
        indexed.sort(key=lambda x: -x[1])  # highest priority_rank (lowest priority) first
        while estimated_duration > target_duration and len(working_sets) > 1:
            drop_idx = indexed.pop(0)[0]
            dropped = working_sets.pop(drop_idx)
            modifier_notes.append(f"Dropped {dropped['exercise_id']} to fit {target_duration}-min session")
            # Rebuild indices after removal
            indexed = [(i, ex.get('priority_rank', 99)) for i, ex in enumerate(working_sets)]
            indexed.sort(key=lambda x: -x[1])
            estimated_duration = _estimate_duration(warmup_mins, working_sets, cooldown_mins)

    estimated_duration = min(estimated_duration, target_duration)

    # ── 17. Session summary ──────────────────────────────────────────────
    total_sets = sum(ex['sets'] for ex in working_sets)
    new_count_final = sum(1 for ex in working_sets if ex['is_new_exercise'])
    patterns_trained = list({ex['movement_pattern'] for ex in working_sets})
    doms_warning = new_count_final > 0 and NEW_EXERCISE_RULES.get('doms_warning', True)

    # update(), not assignment — the football block above already wrote
    # microcycle/HSR keys into meta and they must survive.
    meta.update({
        'patient_id': patient.patient_id,
        'patient_name': patient.name,
        'goal_type': goal_type,
        'goal_all': goal_config.get('_blended_goals', [goal_type]),
        'periodisation_phase': current_phase,
        'current_phase': current_phase,
        'current_week': state.current_week,
        'macrocycle': state.macrocycle_number,
        'is_deload': is_deload,
        'session_number': state.total_sessions_this_cycle + 1,
        'estimated_duration_minutes': estimated_duration,
        'patterns_today': patterns_today,
        'hormonal_phase': hormonal_phase or '',
    })

    rest_modifier_secs = (
        age_limits.get('rest_modifier', 0)
        + sex_adj.get('rest_modifier', 0)
        + hormonal_mods.get('rest_modifier', 0)
        + (30 if tl_vol_mod < 0.7 else 0)
    )

    # ── Coach override check ─────────────────────────────────────────────────
    try:
        from django.utils import timezone as _tz
        from .models import TherapistPrescription
        active_override = (
            TherapistPrescription.objects
            .filter(patient=patient, active=True,
                    created_date__gte=_tz.now() - timedelta(weeks=4))
            .order_by('-created_date')
            .first()
        )
        if active_override and active_override.exercises_json:
            remove_ids = {
                e['exercise_id'] for e in active_override.exercises_json
                if e.get('action') == 'remove'
            }
            if remove_ids:
                working_sets = [ws for ws in working_sets if ws['exercise_id'] not in remove_ids]

            for add_ex in active_override.exercises_json:
                if add_ex.get('action') == 'add':
                    from .exercise_system.exercise_registry_v2 import EXERCISE_METADATA
                    ex_meta = EXERCISE_METADATA.get(add_ex['exercise_id'], {})
                    display_name = (
                        ex_meta.get('display_name') or
                        add_ex['exercise_id'].replace('_', ' ').title()
                    )
                    working_sets.append({
                        'exercise_id':      add_ex['exercise_id'],
                        'exercise_name':    display_name,
                        'movement_pattern': add_ex.get('movement_pattern', ex_meta.get('movement_pattern', '')),
                        'sets':             add_ex.get('sets', 3),
                        'reps':             add_ex.get('reps', 10),
                        'hold_duration':    0,
                        'tempo':            add_ex.get('tempo', '3-1-2-0'),
                        'rest_seconds':     add_ex.get('rest', 75),
                        'load_description': 'Coach prescribed',
                        'coach_prescribed': True,
                        'coach_notes':      active_override.special_instructions,
                        'is_new_exercise':  False,
                        'is_unilateral':    ex_meta.get('unilateral', False),
                        'asymmetry_side':   '',
                    })
            meta['has_coach_override'] = True
            meta['coach_name'] = active_override.therapist.name
    except Exception:
        # D1: a clinician's override silently vanishing is exactly the kind
        # of failure someone must see — the session still generates, but loud.
        logging.getLogger(__name__).warning(
            'coach override application failed for %s — serving the '
            'un-overridden session', getattr(patient, 'patient_id', '?'),
            exc_info=True)

    return {
        'status': 'ready' if not is_deload else 'deload',
        'stop_reason': '',

        'meta': meta,

        'modifiers_applied': {
            'volume_modifier': round(vol_modifier, 2),
            'intensity_modifier': round(int_modifier, 2),
            'rest_modifier': rest_modifier_secs,
            'hormonal_phase': hormonal_phase or '',
            'traffic_light': last_tl,
            'notes': modifier_notes,
        },

        'warmup': warmup,
        'working_sets': working_sets,
        'cooldown': cooldown,

        'session_summary': {
            'total_exercises': len(working_sets),
            'total_sets': total_sets,
            'patterns_trained': patterns_trained,
            'new_exercises_count': new_count_final,
            'doms_warning': doms_warning,
            'deload_note': deload_reason if is_deload else '',
        },
    }
