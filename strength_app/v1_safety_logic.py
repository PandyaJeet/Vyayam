"""
VYAYAM V1 — Safety & Personalisation Logic Layer
18 functions covering: absolute stop, hormonal phase, sex adjustments,
exercise filtering, asymmetry, pattern priorities, deload, traffic light,
sleep/stress modifiers, age caps, training age, new exercise limits,
progression readiness, plateau detection, and master context builder.
"""

from datetime import date, timedelta


# ============================================================================
# 1. ABSOLUTE STOP CHECK
# ============================================================================

def check_absolute_stop(patient):
    """Return True if the patient has an absolute stop flag — no exercise at all."""
    return bool(patient.absolute_stop)


# ============================================================================
# 2. HORMONAL PHASE CALCULATION
# ============================================================================

def calculate_hormonal_phase(patient):
    """
    Determine current hormonal phase for cycle-tracking female patients.

    Returns one of: 'menstruation', 'follicular', 'ovulation', 'luteal', or None.
    Returns None if cycle tracking is disabled, patient is not female, or
    last_period_start is not set.
    """
    if getattr(patient, 'hormonal_contraceptive', False):
        return 'stable'  # No cycle phase variation for contraceptive users
    if patient.biological_sex != 'female':
        return None
    if not patient.cycle_tracking_enabled:
        return None
    if not patient.last_period_start:
        return None
    # Don't use stale period data (older than 90 days)
    days_since_last = (date.today() - patient.last_period_start).days
    if days_since_last < 0:
        return None  # Future date entered — cannot compute phase
    if days_since_last > 90:
        return 'unknown'  # Data too old to be reliable

    cycle_length = patient.cycle_length_days or 28
    today = date.today()
    days_since = (today - patient.last_period_start).days % cycle_length

    if days_since < 5:
        return 'menstruation'
    elif days_since < 13:
        return 'follicular'
    elif days_since < 16:
        return 'ovulation'
    else:
        return 'luteal'


# ============================================================================
# 3. HORMONAL PHASE MODIFIERS
# ============================================================================

def get_hormonal_modifiers(hormonal_phase, patient=None):
    """
    Single source of truth for hormonal-phase training modifiers (DA-C15).

    Returns a COMPLETE flat dict in the engine's key convention for every
    phase value (None, 'stable', 'unknown', 'follicular', 'ovulation',
    'luteal', 'menstruation'):

        volume_modifier (float)      multiply set counts
        rest_modifier (int seconds)  add to rest periods
        plyometric_clearance (bool)  False blocks plyo/power work
        warmup_extended (bool)       longer warm-up (e.g. ovulation/ACL risk)
        mobility_only (bool)         severe menstruation → mobility session
        notes (str)

    'menstruation' resolves the patient's menstrual_pain_level; with no
    patient supplied it defaults to 'minimal' (most-permissive sub-phase,
    matching the old engine behaviour).

    History: this function previously returned 'volume_multiplier'-style
    keys (with the raw nested menstruation dict unresolved) while the
    engine kept a parallel '_resolve_hormonal_modifiers' using
    'volume_modifier' keys. The engine convention won; the engine resolver
    now delegates here.
    """
    from .v1_constants import HORMONAL_PHASE_MODIFIERS

    neutral = {
        'volume_modifier': 1.0,
        'rest_modifier': 0,
        'plyometric_clearance': True,
        'warmup_extended': False,
        'mobility_only': False,
        'notes': '',
    }

    if hormonal_phase in (None, 'stable', 'unknown'):
        return dict(neutral)

    phase_data = HORMONAL_PHASE_MODIFIERS.get(hormonal_phase, {})

    if hormonal_phase == 'menstruation':
        pain = 'minimal'
        if patient is not None:
            pain = getattr(patient, 'menstrual_pain_level', None) or 'minimal'
        sub = phase_data.get(pain, phase_data.get('minimal', {}))
        out = dict(neutral)
        out['volume_modifier'] = sub.get('volume_modifier', 1.0)
        out['rest_modifier'] = sub.get('rest_modifier', 0)
        out['notes'] = sub.get('notes', '')
        if out['volume_modifier'] == 0.0:
            out['plyometric_clearance'] = False
            out['mobility_only'] = True
        return out

    out = dict(neutral)
    out['volume_modifier'] = phase_data.get('volume_modifier', 1.0)
    out['rest_modifier'] = phase_data.get('rest_modifier', 0)
    out['plyometric_clearance'] = phase_data.get('plyometric_clearance', True)
    out['warmup_extended'] = phase_data.get('warmup_extended', False)
    out['notes'] = phase_data.get('notes', '')
    return out


# ============================================================================
# 4. SEX ADJUSTMENTS
# ============================================================================

def get_sex_adjustments(patient):
    """
    Return sex-based training adjustments.

    Returns a dict with: rest_multiplier, volume_multiplier, acl_prevention
    """
    from .v1_constants import SEX_MODIFIERS
    sex = patient.biological_sex or 'not_specified'
    return SEX_MODIFIERS.get(sex, SEX_MODIFIERS.get('not_specified', {}))


# ============================================================================
# 5. FEMALE ACL PREVENTION
# ============================================================================

def apply_female_acl_prevention(patient, exercise_list):
    """
    For female patients, prepend ACL prevention warm-up cues to the exercise list.

    Returns the (potentially modified) exercise list unchanged in content —
    the caller should use the returned notes to add coaching cues.
    Returns a tuple: (exercise_list, acl_notes)
    """
    if patient.biological_sex != 'female':
        return exercise_list, []

    acl_notes = [
        'Land with soft knees — avoid knee valgus (knees caving in)',
        'Activate glutes before any jump or landing exercise',
        'Nordic curl or glute bridge warm-up recommended before lower body session',
    ]
    return exercise_list, acl_notes


# ============================================================================
# 6. EXERCISE FILTER (RED FLAGS + EQUIPMENT)
# ============================================================================

def filter_exercises_for_patient(patient, candidate_exercise_ids):
    """
    Filter a list of exercise IDs by:
      1. Red flag exclusions
      2. Equipment availability

    Returns a filtered list of exercise IDs safe for this patient.
    """
    from .red_flag_map import get_excluded_exercises
    from .equipment_routing import EXERCISE_EQUIPMENT_REQUIRED

    red_flags = patient.red_flags_json or []
    excluded = get_excluded_exercises(red_flags)

    equipment_available = set(patient.equipment_available_json or [])
    # Always include bodyweight
    equipment_available.update({'none', 'bodyweight'})

    filtered = []
    for ex_id in candidate_exercise_ids:
        if ex_id in excluded:
            continue
        required = EXERCISE_EQUIPMENT_REQUIRED.get(ex_id, [])
        # Empty list means bodyweight — always available
        if not required or bool(equipment_available.intersection(set(required))):
            filtered.append(ex_id)
    return filtered


# ============================================================================
# 7. GET ALTERNATIVE FOR EXCLUDED EXERCISE
# ============================================================================

def get_alternative_for_excluded(patient, exercise_id, movement_pattern):
    """
    Given an excluded exercise, find the best safe alternative for this patient.

    Iterates through the patient's red flags and returns the first matching
    alternative for the given movement pattern. Returns None if no alternative found.
    """
    from .red_flag_map import get_alternative

    red_flags = patient.red_flags_json or []
    for flag_id in red_flags:
        alt = get_alternative(flag_id, movement_pattern)
        if alt:
            return alt
    return None


# ============================================================================
# 8. ASYMMETRY RULES
# ============================================================================

def get_asymmetry_rules(strength_profile):
    """
    Given a StrengthProfile instance, return asymmetry training rules.

    Returns a dict:
      {
        pattern: {
          'asymmetry': 'none'|'mild'|'moderate'|'significant',
          'weaker_side': 'left'|'right'|'',
          'unilateral_priority': bool,   # True = start with weaker side
          'volume_ratio': (weak, strong) # e.g. (1.2, 1.0)
        }
      }
    """
    rules = {}
    for pattern in ('hinge', 'lunge', 'rotate'):
        asymmetry = getattr(strength_profile, f'{pattern}_asymmetry', 'none')
        weaker_side = getattr(strength_profile, f'weaker_side_{pattern}', '')
        if asymmetry == 'none':
            rules[pattern] = {
                'asymmetry': 'none', 'weaker_side': '', 'unilateral_priority': False, 'volume_ratio': (1.0, 1.0)
            }
        elif asymmetry == 'mild':
            rules[pattern] = {
                'asymmetry': 'mild', 'weaker_side': weaker_side, 'unilateral_priority': True,
                'volume_ratio': (1.1, 1.0)
            }
        elif asymmetry == 'moderate':
            rules[pattern] = {
                'asymmetry': 'moderate', 'weaker_side': weaker_side, 'unilateral_priority': True,
                'volume_ratio': (1.2, 1.0)
            }
        else:  # significant
            rules[pattern] = {
                'asymmetry': 'significant', 'weaker_side': weaker_side, 'unilateral_priority': True,
                'volume_ratio': (1.3, 1.0)
            }
    return rules


# ============================================================================
# 9. PATTERN PRIORITIES
# ============================================================================

def compute_pattern_priorities(patient, strength_profile=None):
    """
    Compute ordered list of movement pattern priorities for this patient.

    Priority order derived from:
      1. Goal-based pattern preferences (GOAL_PRIORITY_PATTERNS)
      2. Strength profile weaknesses (lowest scores first)

    Returns list of pattern names ordered by training priority.
    """
    from .exercise_tags import GOAL_PRIORITY_PATTERNS

    goal = patient.goal_type or 'general_strength'
    goal_order = GOAL_PRIORITY_PATTERNS.get(goal, list(GOAL_PRIORITY_PATTERNS.get('general_strength', [])))

    if strength_profile is None:
        return goal_order

    # Build score map from strength profile
    score_map = {
        'squat': strength_profile.squat_score,
        'hinge': strength_profile.hinge_score,
        'push': strength_profile.push_score,
        'pull': strength_profile.pull_score,
        'rotate': strength_profile.rotate_score,
        'lunge': strength_profile.lunge_score,
        'carry': 3,  # No direct carry score — default to mid-range
    }

    # Within each goal-ordered group, surface weaker patterns earlier
    # Simple approach: stable-sort by score ascending within first 3 slots
    prioritised = sorted(goal_order, key=lambda p: score_map.get(p, 3))
    return prioritised


# ============================================================================
# 10. DELOAD CHECK
# ============================================================================

def check_deload_needed(patient, periodisation_state=None):
    """
    Determine whether a deload week is warranted.

    Mandatory 4-week rule: deload is non-negotiable once max_weeks of loading
    has elapsed since the last deload, regardless of how the caller provides state.

    Checks (in priority order):
      1. weeks_since_deload via PeriodisationState (mandatory, cannot be bypassed)
      2. Fallback: date arithmetic from last_deload_date if state missing
      3. Consecutive red traffic lights (≥ 2)
      4. Moderate/severe pain in recent sessions (≥ 2)

    Returns: (bool: needs_deload, str: reason)
    """
    from django.core.exceptions import ObjectDoesNotExist
    from .v1_constants import DELOAD_CONFIG
    from datetime import date

    # R2-W2-5 (SB-14): deload ceiling by training age. Novices get 6 weeks
    # (less accumulated systemic fatigue at novice loads); trained users
    # keep 4. Feedback triggers below are unchanged and fire earlier.
    novice = getattr(patient, 'training_history', '') in ('never', 'tried', 'beginner')
    max_weeks = (DELOAD_CONFIG.get('trigger_every_n_weeks_novice', 6) if novice
                 else DELOAD_CONFIG.get('trigger_every_n_weeks', 4))

    # Resolve state: supplied by caller, else from the patient's OneToOne
    # (related_name is 'periodisation' — see models.PeriodisationState).
    state = periodisation_state
    if state is None:
        try:
            state = patient.periodisation
        except ObjectDoesNotExist:
            state = None  # No periodisation state yet — new patient, skip time gate

    # Mandatory time gate = max(session-driven counter, calendar weeks since
    # last deload) reaching the limit. Both checks run regardless of how the
    # state was obtained, so a caller passing a state with a stale counter
    # cannot bypass the calendar rule and vice versa (DA-C2 / DA-C11).
    if state is not None:
        if state.weeks_since_deload >= max_weeks:
            return True, f'Mandatory deload: {state.weeks_since_deload} weeks of progressive loading (limit {max_weeks})'
        if state.last_deload_date:
            weeks_elapsed = (date.today() - state.last_deload_date).days // 7
            if weeks_elapsed >= max_weeks:
                return True, f'Mandatory deload: {weeks_elapsed} weeks elapsed since last deload (limit {max_weeks})'

    # Check recent session feedback
    recent_feedbacks = patient.session_feedbacks.order_by('-created_at')[:5]
    red_count = sum(1 for fb in recent_feedbacks if fb.traffic_light == 'red')
    if red_count >= 2:
        return True, 'Two or more red traffic lights in recent sessions'

    pain_count = sum(
        1 for fb in recent_feedbacks
        if fb.pain_reported in ('moderate', 'severe')
    )
    if pain_count >= 2:
        return True, 'Repeated pain reports — deload and reassess'

    return False, ''


# ============================================================================
# 11. TRAFFIC LIGHT COMPUTATION
# ============================================================================

def compute_traffic_light(session_feedback):
    """
    Compute traffic light colour from a SessionFeedback instance.

    RED conditions (any one triggers red):
      - Sharp / concerning pain reported
      - Perceived difficulty == 'too_hard' AND pain present
      - Sleep < 5 hours AND energy == 'low'

    YELLOW conditions:
      - Perceived difficulty == 'too_hard'
      - Joint pain reported
      - Sleep < 5 hours (alone), or 5-6 hours combined with energy != good
        (R2-W2-9: one slightly-short night with good energy is not yellow)
      - Energy == 'low'
      - Luteal / menstruation phase (mild modifier — not auto-yellow alone)

    GREEN otherwise.
    """
    fb = session_feedback
    severity = getattr(fb, 'pain_severity', 0) or 0

    # DA-F1: per-exercise pain reports from the session override a mild
    # post-session answer — a 'sharp' report or 7+/10 during ANY exercise
    # makes the session red regardless of the check-in form.
    per_ex_sharp = False
    per_ex_max_severity = 0
    try:
        for ex in fb.session.exercises.all():
            if getattr(ex, 'pain_type', '') == 'sharp':
                per_ex_sharp = True
            per_ex_max_severity = max(
                per_ex_max_severity, getattr(ex, 'pain_severity', 0) or 0
            )
    except Exception:
        pass  # feedback not yet attached to a session (unit tests)

    # --- RED ---
    if per_ex_sharp or per_ex_max_severity >= 7:
        return 'red'
    if fb.pain_reported == 'severe':
        return 'red'
    # DA-P4 (Phase 4 row 8): the numeric severity scale must triage too —
    # a patient can answer 'mild' categorically while rating pain 8/10.
    if severity >= 7:
        return 'red'
    if fb.perceived_difficulty == 'too_hard' and fb.pain_reported not in ('none', 'mild'):
        return 'red'
    if fb.sleep_last_night == 'under_5' and fb.energy_level == 'low':
        return 'red'

    # --- YELLOW ---
    if fb.perceived_difficulty == 'too_hard':
        return 'yellow'
    if fb.pain_reported == 'moderate':
        return 'yellow'
    if 4 <= severity <= 6:
        return 'yellow'
    if 4 <= per_ex_max_severity <= 6:  # DA-F1
        return 'yellow'
    # R2-W2-9: <5 h is yellow on its own; 5–6 h only when energy is also
    # not good — one slightly-short night with good energy shouldn't
    # down-regulate the session (the rule was too trigger-happy).
    if fb.sleep_last_night == 'under_5':
        return 'yellow'
    if fb.sleep_last_night == '5_to_6' and fb.energy_level != 'good':
        return 'yellow'
    if fb.energy_level == 'low':
        return 'yellow'

    return 'green'


# ============================================================================
# 11b. PAIN-PATTERN FOLLOW-THROUGH (DA-F3)
# ============================================================================

def get_pain_pattern_escalation(patient):
    """Escalate repeated pain in the same location across sessions.

    Looks at the patient's most recent completed sessions (newest first)
    and counts the CONSECUTIVE streak of sessions reporting pain in the
    same location (per-exercise reports from DA-F1, falling back to the
    post-session check-in location). A pain-free session resets the
    streak.

    Returns {'regress': set(patterns), 'pause': set(patterns)}:
      streak == 2  → regress the implicated pattern one capability level
      streak >= 3  → pause the pattern entirely this session
    """
    from .models import WorkoutSession

    def _patterns_for_location(session, location):
        patterns = set()
        for ex in session.exercises.filter(pain_reported=True):
            if (ex.pain_location or '').strip().lower() == location:
                pattern = _pattern_for_exercise_id(ex.exercise_id)
                if pattern:
                    patterns.add(pattern)
        return patterns

    sessions = list(
        WorkoutSession.objects.filter(patient=patient)
        .order_by('-session_date')[:4]
        .prefetch_related('exercises', 'feedback')
    )
    if not sessions:
        return {'regress': set(), 'pause': set()}

    def _locations(session):
        locs = {
            (ex.pain_location or '').strip().lower()
            for ex in session.exercises.filter(pain_reported=True)
            if (ex.pain_location or '').strip()
        }
        try:
            fb = session.feedback
            if fb.pain_reported not in ('', 'none') and fb.pain_location:
                locs.add(fb.pain_location.strip().lower())
        except Exception:
            pass
        return locs

    newest_locs = _locations(sessions[0])
    if not newest_locs:
        return {'regress': set(), 'pause': set()}  # pain-free → streak reset

    regress, pause = set(), set()
    for location in newest_locs:
        streak = 1
        for older in sessions[1:]:
            if location in _locations(older):
                streak += 1
            else:
                break
        if streak < 2:
            continue
        patterns = set()
        for s in sessions[:streak]:
            patterns |= _patterns_for_location(s, location)
        if not patterns:
            continue
        if streak >= 3:
            pause |= patterns
        else:
            regress |= patterns
    return {'regress': regress, 'pause': pause}


def _pattern_for_exercise_id(exercise_id):
    """Movement pattern for an exercise ID via the registry metadata."""
    try:
        from .exercise_system.exercise_registry_v2 import EXERCISE_METADATA
        return EXERCISE_METADATA.get(exercise_id, {}).get('movement_pattern', '')
    except Exception:
        return ''


# ============================================================================
# 12. SESSION RECOVERY MODIFIERS
# ============================================================================

def get_session_recovery_modifiers(session_feedback):
    """
    Return volume/intensity multipliers for the NEXT session based on current feedback.

    Returns dict: { volume_multiplier, intensity_multiplier, extra_rest_seconds }
    """
    light = compute_traffic_light(session_feedback)
    if light == 'red':
        return {'volume_multiplier': 0.7, 'intensity_multiplier': 0.7, 'extra_rest_seconds': 60}
    elif light == 'yellow':
        return {'volume_multiplier': 0.85, 'intensity_multiplier': 0.85, 'extra_rest_seconds': 30}
    else:
        return {'volume_multiplier': 1.0, 'intensity_multiplier': 1.0, 'extra_rest_seconds': 0}


# ============================================================================
# 13. AGE CAPS
# ============================================================================

def get_age_limits(patient):
    """
    Return age-appropriate training caps.

    Returns dict: { max_capability, power_allowed, max_sets, rest_modifier }
    """
    from .v1_constants import AGE_CAPS, get_age_bracket

    age = patient.age or 30
    bracket = get_age_bracket(age)
    return AGE_CAPS.get(bracket, AGE_CAPS['18_29'])


# ============================================================================
# 14. TRAINING AGE CONFIG
# ============================================================================

def get_training_age_config(patient):
    """
    Return training-age-appropriate progression config.

    Returns dict from TRAINING_AGE_CONFIG keyed by patient.training_history.
    """
    from .v1_constants import TRAINING_AGE_CONFIG

    history = getattr(patient, 'training_history', 'never') or 'never'
    return TRAINING_AGE_CONFIG.get(history, TRAINING_AGE_CONFIG['never'])


# ============================================================================
# 15. LIMIT NEW EXERCISES
# ============================================================================

def limit_new_exercises(patient, exercise_plan, periodisation_state=None):
    """
    Apply NEW_EXERCISE_RULES: limit how many new exercises appear per session.

    For AA phase or beginners, cap at 2 new exercises per session.
    For all phases, cap at NEW_EXERCISE_RULES['max_new_per_session'].

    Returns the exercise_plan list with excess new exercises replaced/removed.
    The exercise_plan is expected to be a list of dicts with key 'is_new' (bool).
    """
    from .v1_constants import NEW_EXERCISE_RULES

    phase = getattr(periodisation_state, 'current_phase', '') if periodisation_state else ''
    is_aa_phase = 'anatomical_adaptation' in phase

    if is_aa_phase or patient.training_age_months < 3:
        max_new = NEW_EXERCISE_RULES.get('max_new_per_session_aa', 2)
    else:
        max_new = NEW_EXERCISE_RULES.get('max_new_per_session', 3)

    new_count = 0
    result = []
    for ex in exercise_plan:
        if ex.get('is_new', False):
            if new_count < max_new:
                result.append(ex)
                new_count += 1
            # else: skip this new exercise (drop it from plan)
        else:
            result.append(ex)
    return result


# ============================================================================
# 16. PROGRESSION READINESS CHECK
# ============================================================================

def check_progression_ready(family_capability):
    """
    Apply the 2-for-2 rule: patient is ready to progress if they have achieved
    'comfortable' or 'easy' in 2 consecutive sessions at the current level.

    family_capability: PatientFamilyCapability instance

    Returns bool.
    """
    from .v1_constants import PROGRESSION_RULES

    required_sessions = PROGRESSION_RULES.get('consecutive_comfortable_for_advance', 2)
    return family_capability.consecutive_comfortable_sessions >= required_sessions


# ============================================================================
# 17. PLATEAU DETECTION
# ============================================================================

def detect_plateau(family_capability):
    """
    Detect a plateau: patient has been at same level for too many sessions
    without progression.

    Returns (bool: is_plateau, str: suggestion)
    """
    from .v1_constants import PROGRESSION_RULES

    plateau_threshold = PROGRESSION_RULES.get('plateau_sessions_threshold', 8)
    sessions = family_capability.sessions_at_current_level

    if sessions >= plateau_threshold and not family_capability.ready_to_advance:
        return True, (
            f'Plateau detected after {sessions} sessions at current level. '
            'Consider: tempo variation, unilateral focus, or technique refinement.'
        )
    return False, ''


# ============================================================================
# 18. BUILD PATIENT CONTEXT (MASTER FUNCTION)
# ============================================================================

def build_patient_context(patient):
    """
    Build the complete personalisation context for a patient in one call.

    Returns a dict with all safety and personalisation data needed to
    generate a session prescription:

    {
        'absolute_stop': bool,
        'hormonal_phase': str|None,
        'hormonal_modifiers': dict,
        'sex_adjustments': dict,
        'acl_notes': list,
        'age_limits': dict,
        'training_age_config': dict,
        'sleep_modifiers': dict,
        'stress_modifiers': dict,
        'deload_needed': bool,
        'deload_reason': str,
        'pattern_priorities': list,
        'asymmetry_rules': dict,
    }
    """
    from .v1_constants import SLEEP_MODIFIERS, STRESS_MODIFIERS

    if check_absolute_stop(patient):
        return {'absolute_stop': True}

    hormonal_phase = calculate_hormonal_phase(patient)
    hormonal_modifiers = get_hormonal_modifiers(hormonal_phase, patient=patient)
    sex_adjustments = get_sex_adjustments(patient)
    _, acl_notes = apply_female_acl_prevention(patient, [])
    age_limits = get_age_limits(patient)
    training_age_config = get_training_age_config(patient)

    sleep_modifiers = SLEEP_MODIFIERS.get(patient.sleep_quality or 'good', {})
    stress_modifiers = STRESS_MODIFIERS.get(patient.stress_level or 'moderate', {})

    # Periodisation state (may not exist yet)
    try:
        periodisation_state = patient.periodisation
    except Exception:
        periodisation_state = None

    deload_needed, deload_reason = check_deload_needed(patient, periodisation_state)

    # Strength profile (most recent)
    strength_profile = patient.strength_profiles.order_by('-assessed_at').first()
    pattern_priorities = compute_pattern_priorities(patient, strength_profile)
    asymmetry_rules = get_asymmetry_rules(strength_profile) if strength_profile else {}

    return {
        'absolute_stop': False,
        'hormonal_phase': hormonal_phase,
        'hormonal_modifiers': hormonal_modifiers,
        'sex_adjustments': sex_adjustments,
        'acl_notes': acl_notes,
        'age_limits': age_limits,
        'training_age_config': training_age_config,
        'sleep_modifiers': sleep_modifiers,
        'stress_modifiers': stress_modifiers,
        'deload_needed': deload_needed,
        'deload_reason': deload_reason,
        'pattern_priorities': pattern_priorities,
        'asymmetry_rules': asymmetry_rules,
    }


# ============================================================================
# 19. PHASE ADVANCEMENT
# ============================================================================

_PHASE_ORDER = [
    'anatomical_adaptation_iso',
    'anatomical_adaptation_ecc',
    'hypertrophy',
    'hypertrophy_volume',
    'strength',
    'deload',
]


def advance_periodisation(patient):
    """
    Check if the current periodisation phase should advance based on weeks completed.
    If current_week has moved beyond the phase's week range, advance to the next phase.
    Called from v1_session_complete after incrementing total_sessions_this_cycle.
    """
    try:
        state = patient.periodisation
    except Exception:
        return

    from .v1_constants import PERIODISATION_PHASES
    phase_config = PERIODISATION_PHASES.get(state.current_phase, {})
    phase_weeks = phase_config.get('weeks', [])

    if not phase_weeks:
        return

    if state.current_week <= max(phase_weeks):
        return  # Still inside this phase

    # Advance to next phase
    try:
        current_idx = _PHASE_ORDER.index(state.current_phase)
    except ValueError:
        current_idx = 0

    next_idx = current_idx + 1
    # If we just completed a deload phase, reset the deload counter
    if state.current_phase == 'deload':
        state.weeks_since_deload = 0
        state.last_deload_date = date.today()

    if next_idx >= len(_PHASE_ORDER):
        # Macrocycle complete — restart
        state.current_phase = _PHASE_ORDER[0]
        state.macrocycle_number = (state.macrocycle_number or 1) + 1
    else:
        state.current_phase = _PHASE_ORDER[next_idx]

    state.current_week = 1
    state.phase_start_date = date.today()
    state.save(update_fields=[
        'current_phase', 'current_week', 'macrocycle_number',
        'phase_start_date', 'weeks_since_deload', 'last_deload_date',
    ])


# ============================================================================
# 20. DROP-OFF RECOVERY — GAP DETECTION
# ============================================================================

def get_return_session_adjustments(patient):
    """
    Detect how long since the patient's last session and return appropriate
    adjustments. Integrates into generate_v1_session as a volume/tempo modifier.

    Adjustment levels:
      ≤10 days  → none
      11-14 days → gentle_return (volume 0.7, no new exercises)
      15-28 days → moderate_return (volume 0.5, no new, slow tempo)
      29-56 days → partial_reassessment (volume 0.5, flag for reassessment)
      57+ days   → full_reassessment (redirect to onboarding)
    """
    try:
        from .models import WorkoutSession
        last = WorkoutSession.objects.filter(patient=patient).order_by('-session_date').first()
    except Exception:
        return {'adjustment': 'none', 'message': ''}

    if not last:
        return {'adjustment': 'none', 'message': ''}

    try:
        last_date = last.session_date.date() if hasattr(last.session_date, 'date') else last.session_date
        days_since = (date.today() - last_date).days
    except Exception:
        return {'adjustment': 'none', 'message': ''}

    if days_since <= 10:
        return {'adjustment': 'none', 'message': ''}
    elif days_since <= 14:
        return {
            'adjustment': 'gentle_return',
            'volume_modifier': 0.7,
            'no_new_exercises': True,
            'message': "Welcome back. We've adjusted today's session for your return. Your progress is all still here.",
        }
    elif days_since <= 28:
        return {
            'adjustment': 'moderate_return',
            'volume_modifier': 0.5,
            'no_new_exercises': True,
            'tempo_slow': True,
            'message': "Welcome back. Volume is reduced and tempo slowed for a smooth return.",
        }
    elif days_since <= 56:
        return {
            'adjustment': 'partial_reassessment',
            'volume_modifier': 0.5,
            'reassess_patterns': True,
            'message': "A lot can change in a month. Let's quickly check where you are now.",
        }
    else:
        return {
            'adjustment': 'full_reassessment',
            'redirect_to_onboarding': True,
            'message': "It's been a while. Your body has likely changed. Let's reassess fully.",
        }
