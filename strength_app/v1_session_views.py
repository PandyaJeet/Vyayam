"""
VYAYAM V1 — Session Execution Views

Views:
  v1_dashboard              — V1 home screen (radar + today's session)
  v1_session_overview       — Pre-session summary
  v1_warmup                 — Guided 4-phase warm-up
  v1_execute_exercise       — Camera + tempo + rest timer
  v1_save_exercise_result   — AJAX save
  v1_cooldown               — 3-phase cool-down with breathing
  v1_post_session_feedback  — 4-question check-in
  v1_session_complete       — Summary + next session
"""

import json
from datetime import date

from django.shortcuts import render, redirect
from django.http import JsonResponse

from .models import (
    PatientProfile, StrengthProfile, PeriodisationState,
    WorkoutSession, ExerciseExecution, SessionFeedback,
)
from .v1_prescription_engine import generate_v1_session
from .v1_safety_logic import compute_pattern_priorities, advance_periodisation


# ============================================================================
# HELPERS
# ============================================================================

def _get_patient(request):
    pid = request.session.get('patient_id')
    if not pid:
        return None
    try:
        return PatientProfile.objects.get(patient_id=pid)
    except PatientProfile.DoesNotExist:
        return None


def _require_patient(request):
    p = _get_patient(request)
    return (p, None) if p else (None, redirect('patient_login'))


_DEMO_SESSION = {
    'status': 'ready',
    'meta': {
        'patient_name': 'Demo User',
        'session_label': 'Strength Session',
        'is_deload': False,
        'difficulty': 'Beginner',
        'estimated_duration_minutes': 20,
    },
    'warmup': {
        'estimated_minutes': 5,
        'phases': {'elevate': [], 'mobilise': [], 'activate': [], 'prime': []},
    },
    'working_sets': [
        {
            'exercise_id': 'full_squats',
            'exercise_name': 'Full Squats',
            'movement_pattern': 'squat',
            'sets': 3,
            'reps': 10,
            'tempo': '3-1-2-0',
            'tempo_parts': ['3', '1', '2', '0'],
            'rest_seconds': 60,
            'prescribed_rest': 60,
            'capability_level': 2,
            'form_cues': ['Chest tall', 'Knees tracking over toes', 'Drive through mid-foot'],
            'mind_muscle_cue': '',
            'hold_duration': 0,
            'is_unilateral': False,
            'asymmetry': {},
        },
    ],
    'cooldown': {
        'estimated_minutes': 5,
        'phases': {'light_movement': [], 'static_stretch': [], 'breathing': []},
    },
    'modifiers_applied': {},
    'session_summary': {
        'session_type': 'Strength Session',
        'estimated_minutes': 20,
        'total_exercises': 1,
    },
}

_DEMO_PATIENT_IDS = {'DEMO_USER01'}


def _get_or_refresh_session_data(request, patient):
    """
    Return the stored v1_session dict. Regenerate if missing or stale (new day).
    Demo patients get a hardcoded minimal session regardless of profile.
    """
    stored = request.session.get('v1_session')
    stored_date = request.session.get('v1_session_date', '')
    today_str = str(date.today())

    if stored and stored_date == today_str:
        return stored

    if patient.patient_id in _DEMO_PATIENT_IDS:
        data = dict(_DEMO_SESSION)
        data['meta'] = dict(_DEMO_SESSION['meta'])
        data['meta']['patient_id'] = patient.patient_id
        data['meta']['patient_name'] = patient.name
        request.session['v1_session'] = data
        request.session['v1_session_date'] = today_str
        request.session['v1_exercise_results'] = []
        return data

    try:
        data = generate_v1_session(patient)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception('generate_v1_session failed for %s', patient.patient_id)
        data = {
            'status': 'error',
            'stop_reason': f'Session generation failed: {exc}',
            'meta': {'patient_id': patient.patient_id, 'patient_name': patient.name},
            'modifiers_applied': {}, 'warmup': {}, 'working_sets': [],
            'cooldown': {}, 'session_summary': {},
        }

    # Django sessions require JSON-serialisable values
    try:
        json.dumps(data)
    except (TypeError, ValueError):
        data = {'status': 'error', 'meta': {}}

    request.session['v1_session'] = data
    request.session['v1_session_date'] = today_str
    request.session['v1_exercise_results'] = []
    return data


def _pattern_to_category(pattern):
    """Map movement pattern to ExerciseExecution.category value."""
    mapping = {
        'squat': 'lower_body', 'lunge': 'lower_body', 'hinge': 'posterior_chain',
        'push': 'upper_body', 'pull': 'upper_body',
        'rotate': 'upper_body', 'carry': 'upper_body',
    }
    return mapping.get(pattern, 'lower_body')


def _add_tempo_parts(exercise):
    """Add tempo_parts list to an exercise dict (mutates a copy)."""
    ex = dict(exercise)
    parts = str(ex.get('tempo', '3-1-2-0')).split('-')
    while len(parts) < 4:
        parts.append('0')
    ex['tempo_parts'] = parts
    return ex


# ============================================================================
# VIEW 1: V1 DASHBOARD
# ============================================================================

def v1_dashboard(request):
    patient, err = _require_patient(request)
    if err:
        return err

    if patient.therapist_managed:
        return redirect('therapist_session_today')

    profile = patient.strength_profiles.order_by('-assessed_at').first()

    try:
        state = patient.periodisation
    except PeriodisationState.DoesNotExist:
        state = None

    session_data = _get_or_refresh_session_data(request, patient)
    request.session['has_strength_profile'] = bool(profile)

    # Absolute stop
    status = session_data.get('status', 'ready')
    if status == 'stopped':
        return render(request, 'strength_app/v1_stopped.html', {
            'patient': patient,
            'stop_reason': session_data.get('stop_reason', ''),
        })
    if status == 'reassess':
        return render(request, 'strength_app/v1_stopped.html', {
            'patient': patient,
            'stop_reason': session_data.get('stop_reason', ''),
            'reassess': True,
        })
    if status == 'error':
        return render(request, 'strength_app/v1_stopped.html', {
            'patient': patient,
            'stop_reason': session_data.get('stop_reason', 'An error occurred generating your session. Please try again.'),
        })

    # Radar data
    if profile:
        radar_data = {
            'Squat': profile.squat_score,
            'Hinge': profile.hinge_score,
            'Push':  profile.push_score,
            'Pull':  profile.pull_score,
            'Core':  profile.core_score,
            'Rotate': profile.rotate_score,
            'Lunge': profile.lunge_score,
        }
    else:
        radar_data = {k: 2 for k in ['Squat', 'Hinge', 'Push', 'Pull', 'Core', 'Rotate', 'Lunge']}

    recent_sessions = WorkoutSession.objects.filter(patient=patient).order_by('-session_date')[:5]

    meta       = session_data.get('meta', {})
    modifiers  = session_data.get('modifiers_applied', {})
    working    = session_data.get('working_sets', [])
    summary    = session_data.get('session_summary', {})
    is_deload  = meta.get('is_deload', False)
    is_mobility = session_data.get('status') == 'mobility_only'

    # Quick stats
    all_sessions = WorkoutSession.objects.filter(patient=patient)
    total_sessions = all_sessions.count()

    # ── Football context ─────────────────────────────────────────────────
    football_ctx = {}
    if hasattr(patient, 'athlete_tier_active') and patient.athlete_tier_active:
        try:
            fp = patient.football_profile
            from .v1_football_constants import FOOTBALL_LEVELS, FV_TENDENCY_CONFIG
            from .v1_football_views import football_reassessment_check
            reassessment_due = football_reassessment_check(patient)
            hsr_num = (fp.hsr_current_phase or 'hsr_phase_1').replace('hsr_phase_', '')
            football_ctx = {
                'is_football': True,
                'football_level': fp.football_level,
                'level_name': FOOTBALL_LEVELS.get(fp.football_level, {}).get('name', ''),
                'fv_tendency': fp.fv_tendency,
                'fv_label': FV_TENDENCY_CONFIG.get(fp.fv_tendency, {}).get('label', ''),
                'lsi_flag': fp.lsi_flag,
                'lsi_hop': fp.hop_lsi_pct,
                'lsi_ybalance': fp.ybalance_lsi_pct,
                'plyometric_cleared': fp.plyometric_cleared and fp.plyometric_cleared != 'none',
                'hsr_phase': hsr_num,
                'training_focus': FOOTBALL_LEVELS.get(fp.football_level, {}).get('training_focus', []),
                'reassessment_due': reassessment_due,
            }
        except Exception:
            football_ctx = {}

    # ── Gamification context ────────────────────────────────────────────────
    from .v1_gamification import (
        compute_xp_and_level, compute_streak_days, compute_phase_context,
    )
    gam = compute_xp_and_level(patient)
    streak_days = compute_streak_days(patient)
    phase_ctx = compute_phase_context(state)

    # Today's session display
    session_name = meta.get('session_label', summary.get('session_type', 'Strength Session'))
    duration = summary.get('estimated_minutes', 45)
    difficulty = meta.get('difficulty', 'Intermediate')
    today_session = {'name': session_name, 'duration_minutes': duration, 'difficulty': difficulty}

    context = {
        'patient': patient,
        'profile': profile,
        'state': state,
        'radar_data': radar_data,
        'session_data': session_data,
        'meta': meta,
        'modifiers': modifiers,
        'working_sets_preview': working[:4],
        'summary': summary,
        'recent_sessions': recent_sessions,
        'total_sessions': total_sessions,
        'is_deload': is_deload,
        'is_mobility': is_mobility,
        'today': date.today(),
        'has_strength_profile': bool(profile),
        'football': football_ctx,
        # Gamified vars
        'user_level': gam['user_level'],
        'xp_current': gam['xp_current'],
        'xp_next_level': gam['xp_next_level'],
        'xp_percentage': gam['xp_percentage'],
        'streak_days': streak_days,
        'today_session': today_session,
        'current_phase': phase_ctx['current_phase'],
        'current_week': phase_ctx['current_week'],
        'total_weeks': phase_ctx['total_weeks'],
        'phase_range': phase_ctx['phase_range'],
        'session_url': '/v1/session/',
    }
    return render(request, 'strength_app/v1_home_gamified.html', context)


# ============================================================================
# VIEW 2: SESSION OVERVIEW
# ============================================================================

def v1_session_overview(request):
    patient, err = _require_patient(request)
    if err:
        return err

    session_data = _get_or_refresh_session_data(request, patient)

    if session_data.get('status') == 'stopped':
        return render(request, 'strength_app/v1_stopped.html', {
            'patient': patient,
            'stop_reason': session_data.get('stop_reason', ''),
        })

    working_sets = [_add_tempo_parts(ex) for ex in session_data.get('working_sets', [])]
    meta       = session_data.get('meta', {})
    modifiers  = session_data.get('modifiers_applied', {})
    warmup     = session_data.get('warmup', {})
    cooldown   = session_data.get('cooldown', {})
    summary    = session_data.get('session_summary', {})

    # Check previous session for pain follow-up
    pain_followup = None
    last_feedback = SessionFeedback.objects.filter(patient=patient).order_by('-created_at').first()
    if last_feedback and last_feedback.pain_reported not in ('none', '', None):
        location_display = (last_feedback.pain_location or 'an area').replace('_', ' ')
        pain_followup = {
            'location': location_display,
            'exercise': last_feedback.pain_exercise or '',
            'pain_type': last_feedback.pain_reported,
            'message': (
                f'You reported {last_feedback.pain_reported.replace("_", " ")} '
                f'in your {location_display} during your last session. '
                f'How does it feel today?'
            ),
        }

    context = {
        'patient': patient,
        'working_sets': working_sets,
        'meta': meta,
        'modifiers': modifiers,
        'warmup': warmup,
        'cooldown': cooldown,
        'summary': summary,
        'pain_followup': pain_followup,
        'has_strength_profile': True,
    }
    return render(request, 'strength_app/v1_session_overview.html', context)


# ============================================================================
# VIEW 3: WARMUP — redirects into coached V2 flow
# ============================================================================

# Warmup exercises that have V2 ghost templates in v1_exercise_execute.html.
# All three exercise IDs are confirmed in EXERCISE_TYPE_MAP in the template.
_COACHED_WARMUP = [
    {
        'exercise_id': 'marching_on_spot',
        'exercise_name': 'Marching on Spot',
        'movement_pattern': 'squat',
        'sets': 1,
        'reps': 20,
        'hold_duration': 0,
        'tempo': '1-0-1-0',
        'tempo_parts': ['1', '0', '1', '0'],
        'rest_seconds': 20,
        'prescribed_rest': 20,
        'capability_level': 1,
        'form_cues': ['Drive knees to hip height', 'Pump arms opposite to legs', 'Stay on balls of feet'],
        'mind_muscle_cue': '',
    },
    {
        'exercise_id': 'full_squats',
        'exercise_name': 'Bodyweight Squat',
        'movement_pattern': 'squat',
        'sets': 2,
        'reps': 8,
        'hold_duration': 0,
        'tempo': '2-1-2-0',
        'tempo_parts': ['2', '1', '2', '0'],
        'rest_seconds': 30,
        'prescribed_rest': 30,
        'capability_level': 1,
        'form_cues': ['Chest tall', 'Knees tracking over toes', 'Drive through mid-foot'],
        'mind_muscle_cue': '',
    },
    {
        'exercise_id': 'glute_bridge',
        'exercise_name': 'Glute Bridge',
        'movement_pattern': 'hinge',
        'sets': 1,
        'reps': 12,
        'hold_duration': 0,
        'tempo': '2-1-2-0',
        'tempo_parts': ['2', '1', '2', '0'],
        'rest_seconds': 20,
        'prescribed_rest': 20,
        'capability_level': 1,
        'form_cues': ['Squeeze glutes at top', 'Neutral spine throughout', 'Feet flat on floor'],
        'mind_muscle_cue': '',
    },
]

# Demo-only warmup override — single partial_squat primer.
_DEMO_COACHED_WARMUP = [
    {
        'exercise_id': 'partial_squats',
        'exercise_name': 'Partial Squat',
        'movement_pattern': 'squat',
        'sets': 1,
        'reps': 8,
        'hold_duration': 0,
        'tempo': '2-1-1-0',
        'tempo_parts': ['2', '1', '1', '0'],
        'rest_seconds': 20,
        'prescribed_rest': 20,
        'capability_level': 1,
        'form_cues': ['Only go as deep as is comfortable', 'Chest tall throughout', 'Knees tracking over toes'],
        'mind_muscle_cue': '',
    },
]


def v1_warmup(request):
    patient, err = _require_patient(request)
    if err:
        return err

    warmup_list = _DEMO_COACHED_WARMUP if patient.patient_id in _DEMO_PATIENT_IDS else _COACHED_WARMUP
    request.session['v1_warmup_exercises'] = warmup_list
    request.session['v1_in_warmup_flow'] = True
    request.session.modified = True
    return redirect('v1_execute_warmup_exercise', warmup_index=0)


# ============================================================================
# VIEW 3b: EXECUTE WARMUP EXERCISE (V2 coached, same template as main)
# ============================================================================

def v1_execute_warmup_exercise(request, warmup_index):
    patient, err = _require_patient(request)
    if err:
        return err

    warmup_exercises = request.session.get('v1_warmup_exercises', [])
    if not warmup_exercises or warmup_index >= len(warmup_exercises):
        request.session.pop('v1_warmup_exercises', None)
        request.session['v1_in_warmup_flow'] = False
        return redirect('v1_execute_exercise', exercise_index=0)

    exercise = warmup_exercises[warmup_index]
    # Always show "Next Exercise" button — routing is controlled by save handler
    context = {
        'patient':          patient,
        'exercise':         exercise,
        'exercise_index':   warmup_index,
        'total_exercises':  len(warmup_exercises),
        'is_last_exercise': False,
        'next_exercise_index': warmup_index + 1,
        'has_strength_profile': True,
    }
    return render(request, 'strength_app/v1_exercise_execute.html', context)


# ============================================================================
# VIEW 4: EXECUTE EXERCISE
# ============================================================================

def v1_execute_exercise(request, exercise_index):
    patient, err = _require_patient(request)
    if err:
        return err

    # Entering main exercise flow — ensure warmup state is cleared
    request.session.pop('v1_warmup_exercises', None)
    request.session['v1_in_warmup_flow'] = False

    session_data = request.session.get('v1_session', {})
    working_sets = session_data.get('working_sets', [])

    if not working_sets:
        return redirect('v1_session_overview')

    if exercise_index >= len(working_sets):
        return redirect('v1_cooldown')

    exercise = _add_tempo_parts(working_sets[exercise_index])
    is_last  = (exercise_index >= len(working_sets) - 1)

    # Build scoring items for self-report form score
    context = {
        'patient':         patient,
        'exercise':        exercise,
        'exercise_index':  exercise_index,
        'total_exercises': len(working_sets),
        'is_last_exercise': is_last,
        'next_exercise_index': exercise_index + 1,
        'has_strength_profile': True,
    }
    return render(request, 'strength_app/v1_exercise_execute.html', context)


# ============================================================================
# VIEW 5: SAVE EXERCISE RESULT (AJAX)
# ============================================================================


def v1_save_exercise_result(request):
    patient, err = _require_patient(request)
    if err:
        return JsonResponse({'success': False, 'error': 'Not logged in'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = {k: v for k, v in request.POST.items()}

    exercise_index  = int(data.get('exercise_index', 0))
    session_data    = request.session.get('v1_session', {})
    working_sets    = session_data.get('working_sets', [])
    total           = len(working_sets)

    # Accumulate results
    results = list(request.session.get('v1_exercise_results', []))
    result = {
        'exercise_id':          data.get('exercise_id', ''),
        'exercise_name':        data.get('exercise_name', ''),
        'movement_pattern':     data.get('movement_pattern', ''),
        'prescribed_sets':      int(data.get('prescribed_sets', 3)),
        'prescribed_reps':      int(data.get('prescribed_reps', 10)),
        'prescribed_rest':      int(data.get('prescribed_rest', 75)),
        'completed_sets':       int(data.get('completed_sets', 0)),
        'completed_reps_per_set': data.get('reps_per_set', []),
        'form_score':           float(data.get('form_score', 75)),
        'pain_reported':        bool(data.get('pain_reported', False)),
        'pain_type':            data.get('pain_type', ''),
        'pain_location':        data.get('pain_location', ''),
        'pain_severity':        int(data.get('pain_severity', 0)),
        'pain_action':          data.get('pain_action', 'continue'),
        'skipped':              bool(data.get('skipped', False)),
    }
    results.append(result)
    request.session['v1_exercise_results'] = results
    request.session.modified = True

    from django.urls import reverse

    if request.session.get('v1_in_warmup_flow'):
        warmup_exercises = request.session.get('v1_warmup_exercises', [])
        next_warmup = exercise_index + 1
        if next_warmup < len(warmup_exercises):
            next_url = reverse('v1_execute_warmup_exercise', args=[next_warmup])
        else:
            # Warmup complete — transition to main exercises
            request.session.pop('v1_warmup_exercises', None)
            request.session['v1_in_warmup_flow'] = False
            request.session.modified = True
            next_url = reverse('v1_execute_exercise', args=[0])
    else:
        next_index = exercise_index + 1
        if next_index >= total:
            next_url = reverse('v1_cooldown')
        else:
            next_url = reverse('v1_execute_exercise', args=[next_index])

    return JsonResponse({'status': 'saved', 'next_url': next_url})


# ============================================================================
# VIEW 6: COOLDOWN
# ============================================================================

def v1_cooldown(request):
    patient, err = _require_patient(request)
    if err:
        return err

    session_data = request.session.get('v1_session', {})
    cooldown = session_data.get('cooldown', {})
    phases   = cooldown.get('phases', {})

    context = {
        'patient':       patient,
        'cooldown':      cooldown,
        'light_movement': phases.get('light_movement', []),
        'static_stretch': phases.get('static_stretch', []),
        'breathing':      phases.get('breathing', []),
        'has_strength_profile': True,
    }
    return render(request, 'strength_app/v1_cooldown.html', context)


# ============================================================================
# VIEW: CONDITIONING SESSION (P27)
# ============================================================================

def v1_conditioning_session(request):
    """
    P27: Energy system conditioning session for football athletes.
    Timer-based protocols with talk test cues. Separate from strength sessions.
    """
    patient, err = _require_patient(request)
    if err:
        return err

    # Only for football athletes
    if not (hasattr(patient, 'athlete_tier_active') and patient.athlete_tier_active
            and patient.athlete_sport == 'football'):
        return redirect('v1_session_overview')

    from .v1_football_constants import CONDITIONING_PROTOCOLS, CONDITIONING_SEASON_MAP

    # Get season phase
    try:
        fp = patient.football_profile
        season = fp.season_phase or 'in_season'
    except Exception:
        season = 'in_season'

    # Get recommended protocols for this season
    recommended_keys = CONDITIONING_SEASON_MAP.get(season, ['zone_3_vo2max'])

    # If a specific protocol was requested via GET param
    selected_key = request.GET.get('protocol', '')
    if selected_key not in CONDITIONING_PROTOCOLS:
        selected_key = recommended_keys[0] if recommended_keys else 'zone_3_vo2max'

    protocol = CONDITIONING_PROTOCOLS[selected_key]

    # Build available protocols list for selection
    available = []
    for key in recommended_keys:
        p = CONDITIONING_PROTOCOLS.get(key)
        if p:
            available.append({
                'key': key,
                'name': p['name'],
                'description': p['description'],
                'rpe_target': p['rpe_target'],
                'is_selected': key == selected_key,
            })

    context = {
        'patient': patient,
        'protocol': protocol,
        'protocol_key': selected_key,
        'available_protocols': available,
        'season_phase': season,
    }
    return render(request, 'strength_app/v1_conditioning_session.html', context)


# ============================================================================
# VIEW 7: POST-SESSION FEEDBACK
# ============================================================================

def v1_post_session_feedback(request):
    patient, err = _require_patient(request)
    if err:
        return err

    session_data = request.session.get('v1_session', {})

    if request.method == 'POST':
        perceived_difficulty = request.POST.get('perceived_difficulty', 'just_right')
        sleep_last_night     = request.POST.get('sleep_last_night', '7_to_8')
        pain_reported        = request.POST.get('pain_reported', 'none')
        pain_location        = request.POST.get('pain_location', '')
        pain_exercise        = request.POST.get('pain_exercise', '')
        pain_severity        = int(request.POST.get('pain_severity') or 0)
        energy_level         = request.POST.get('energy_level', 'good')
        hormonal_phase       = session_data.get('modifiers_applied', {}).get('hormonal_phase', '')

        # --- Create WorkoutSession ---
        try:
            state = patient.periodisation
            week_number = state.current_week
        except Exception:
            week_number = 1

        exercise_results = request.session.get('v1_exercise_results', [])
        total_exercises  = len([r for r in exercise_results if not r.get('skipped')])
        meta             = session_data.get('meta', {})
        duration_mins    = meta.get('estimated_duration_minutes', 45)

        difficulty_num_map = {'too_easy': 1, 'just_right': 3, 'hard': 4, 'too_hard': 5}

        workout = WorkoutSession.objects.create(
            patient=patient,
            week_number=week_number,
            total_duration_minutes=duration_mins,
            total_exercises_completed=total_exercises,
            difficulty_rating=difficulty_num_map.get(perceived_difficulty, 3),
            patient_comfortable=(perceived_difficulty in ('too_easy', 'just_right')),
            prescription_mode='ai_auto',
        )

        # --- Create ExerciseExecution for each result ---
        for res in exercise_results:
            reps_list = res.get('completed_reps_per_set', [])
            total_reps = sum(int(r) for r in reps_list if isinstance(r, (int, float, str)) and str(r).isdigit())
            prescribed_reps = res.get('prescribed_reps', 10)
            prescribed_sets = res.get('prescribed_sets', 3)
            completion_pct  = round(
                min(100, (res.get('completed_sets', 0) / max(1, prescribed_sets)) * 100)
            )
            form_score = float(res.get('form_score', 75))
            green_reps  = round(total_reps * (form_score / 100))
            yellow_reps = round(total_reps * max(0, (1 - form_score / 100)) * 0.6)
            red_reps    = total_reps - green_reps - yellow_reps

            ExerciseExecution.objects.create(
                session=workout,
                exercise_id=res.get('exercise_id', ''),
                exercise_name=res.get('exercise_name', ''),
                category=_pattern_to_category(res.get('movement_pattern', 'lower_body')),
                prescribed_sets=prescribed_sets,
                prescribed_reps=prescribed_reps,
                prescribed_rest=res.get('prescribed_rest', 75),
                total_green_reps=max(0, green_reps),
                total_yellow_reps=max(0, yellow_reps),
                total_red_reps=max(0, red_reps),
                overall_form_score=form_score,
                completion_percentage=completion_pct,
            )

        # --- Create SessionFeedback (traffic light auto-computed by save()) ---
        feedback = SessionFeedback.objects.create(
            session=workout,
            patient=patient,
            perceived_difficulty=perceived_difficulty,
            sleep_last_night=sleep_last_night,
            pain_reported=pain_reported,
            pain_location=pain_location,
            pain_exercise=pain_exercise,
            pain_severity=pain_severity,
            energy_level=energy_level,
            hormonal_phase=hormonal_phase,
            session_rpe=int(request.POST.get('session_rpe', 5)),
        )

        # Update patient's sleep_quality from latest feedback for next session's modifier
        sleep_map = {'under_5': 'poor', '5_to_6': 'moderate', '7_to_8': 'good', 'over_8': 'good'}
        sleep_val = request.POST.get('sleep_last_night', '')
        if sleep_val in sleep_map:
            patient.sleep_quality = sleep_map[sleep_val]
            patient.save(update_fields=['sleep_quality'])

        # Store feedback id for session complete view
        request.session['v1_feedback_id']  = feedback.pk
        request.session['v1_workout_id']   = workout.pk
        request.session.modified = True

        return redirect('v1_session_complete')

    # GET
    hormonal_phase = session_data.get('modifiers_applied', {}).get('hormonal_phase', '')
    show_hormonal  = hormonal_phase in ('luteal', 'menstruation')
    working_sets   = session_data.get('working_sets', [])

    context = {
        'patient':        patient,
        'show_hormonal':  show_hormonal,
        'hormonal_phase': hormonal_phase,
        'working_sets':   working_sets,
        'has_strength_profile': True,
    }
    return render(request, 'strength_app/v1_post_session_feedback.html', context)


# ============================================================================
# VIEW 8: SESSION COMPLETE
# ============================================================================

def v1_session_complete(request):
    patient, err = _require_patient(request)
    if err:
        return err

    feedback_id  = request.session.get('v1_feedback_id')
    workout_id   = request.session.get('v1_workout_id')
    session_data = request.session.get('v1_session', {})

    feedback = None
    workout  = None
    if feedback_id:
        try:
            feedback = SessionFeedback.objects.get(pk=feedback_id)
        except SessionFeedback.DoesNotExist:
            pass
    if workout_id:
        try:
            workout = WorkoutSession.objects.get(pk=workout_id)
        except WorkoutSession.DoesNotExist:
            pass

    # --- Update PeriodisationState ---
    try:
        state = patient.periodisation
        state.total_sessions_this_cycle += 1

        # Advance week when enough sessions have been completed
        spw = max(1, patient.sessions_per_week or 3)
        if state.total_sessions_this_cycle % spw == 0:
            state.current_week += 1
            state.weeks_since_deload = (state.weeks_since_deload or 0) + 1

        state.save(update_fields=['total_sessions_this_cycle', 'current_week', 'weeks_since_deload'])

        # Phase advancement (uses the new advance_periodisation function)
        advance_periodisation(patient)

        # Re-read to get any updated phase from advance_periodisation
        state.refresh_from_db()
    except Exception:
        state = None

    # --- Build exercise results list from session storage ---
    exercise_results = request.session.get('v1_exercise_results', [])

    # Per-exercise summary with traffic light
    exe_summary = []
    for res in exercise_results:
        score = float(res.get('form_score', 75))
        if score >= 80:
            tl = 'green'
        elif score >= 60:
            tl = 'yellow'
        else:
            tl = 'red'
        exe_summary.append({
            'name':       res.get('exercise_name', ''),
            'pattern':    res.get('movement_pattern', ''),
            'sets':       res.get('completed_sets', 0),
            'form_score': round(score),
            'tl':         tl,
            'skipped':    res.get('skipped', False),
        })

    # Next session preview
    next_session_data = None
    try:
        from .v1_prescription_engine import _determine_todays_patterns, _get_or_create_periodisation
        # We don't call full generate here — just get pattern names
        spw = patient.sessions_per_week or 3
        profile = patient.strength_profiles.order_by('-assessed_at').first()
        priorities = compute_pattern_priorities(patient, profile)
        next_patterns, _ = _determine_todays_patterns(patient, priorities, spw)
        next_session_data = {'patterns': next_patterns}
    except Exception:
        next_session_data = {'patterns': []}

    meta    = session_data.get('meta', {})
    summary = session_data.get('session_summary', {})

    # V2 data collection (anonymised, consent-gated)
    try:
        from .v1_data_collector import log_session_data
        log_session_data(patient, session_data, feedback)
    except Exception:
        pass

    # Milestone celebration — detect newly achieved milestones
    new_milestones = []
    try:
        from .v1_progress_views import check_new_milestones
        profiles = list(patient.strength_profiles.order_by('assessed_at'))
        prev_achieved = set(request.session.get('achieved_milestone_ids', []))
        newly = check_new_milestones(patient, profiles, prev_achieved)
        if newly:
            new_milestones = newly
            # Update session cache with all currently achieved
            from .v1_progress_views import _compute_milestones
            all_now = _compute_milestones(patient, profiles)
            request.session['achieved_milestone_ids'] = [m['id'] for m in all_now if m['achieved']]
    except Exception:
        pass

    # Clear session data
    for key in ('v1_session', 'v1_session_date', 'v1_exercise_results',
                'v1_feedback_id', 'v1_workout_id'):
        request.session.pop(key, None)

    # Nutrition summary for post-session card
    nutrition_summary = None
    try:
        from .v1_nutrition_engine import get_daily_nutrition_summary
        nutrition_summary = get_daily_nutrition_summary(patient, date.today())
    except Exception:
        pass

    # ── Football post-session update (P21-P26) ────────────────────────────
    if hasattr(patient, 'athlete_tier_active') and patient.athlete_tier_active:
        try:
            from .v1_football_views import football_update_after_session
            football_update_after_session(patient)
        except Exception:
            pass

    # ── Gamification context ────────────────────────────────────────────────
    from .v1_gamification import compute_session_xp, compute_streak_days
    xp_earned = compute_session_xp(exercise_results)
    streak_days = compute_streak_days(patient)

    # Persist XP to WorkoutSession so compute_xp_and_level can sum real values
    if workout and xp_earned:
        workout.xp_earned = xp_earned
        workout.save(update_fields=['xp_earned'])

    # Rank-up detection — compare current vs previous StrengthProfile scores
    rank_up = None
    try:
        from .v1_gamification import RANK_MAP, PATTERN_FIELDS
        profiles = list(patient.strength_profiles.order_by('assessed_at'))
        if len(profiles) >= 2:
            prev_p, curr_p = profiles[-2], profiles[-1]
            for pattern_name, field in PATTERN_FIELDS:
                prev_score = getattr(prev_p, field, 0)
                curr_score = getattr(curr_p, field, 0)
                if curr_score > prev_score:
                    rank_up = {
                        'pattern_name': pattern_name,
                        'from_rank': RANK_MAP.get(prev_score, ('UNRANKED', 'unranked'))[0],
                        'to_rank': RANK_MAP.get(curr_score, ('UNRANKED', 'unranked'))[0],
                    }
                    break  # show the first pattern that ranked up
    except Exception:
        pass

    context = {
        'patient':           patient,
        'feedback':          feedback,
        'workout':           workout,
        'exe_summary':       exe_summary,
        'next_session':      next_session_data,
        'meta':              meta,
        'summary':           summary,
        'state':             state,
        'new_milestones':    new_milestones,
        'nutrition_summary': nutrition_summary,
        'has_strength_profile': True,
        # Gamified vars
        'xp_earned':         xp_earned,
        'sets_completed':    sum(r.get('completed_sets', 0) for r in exercise_results),
        'session_minutes':   summary.get('estimated_minutes', 42),
        'rank_up':           rank_up,
        'streak_days':       streak_days,
        'home_url':          '/v1/dashboard/',
    }
    return render(request, 'strength_app/v1_session_complete.html', context)


# ============================================================================
# DEV-ONLY TEST VIEWS — debug ghost overlay without session/login
# ============================================================================

def v1_test_exercise(request, exercise_id):
    """Dev-only: test ghost overlay for any exercise. Protected by DEBUG flag."""
    from django.conf import settings
    if not settings.DEBUG:
        from django.http import Http404
        raise Http404

    from .exercise_system.exercise_registry_v2 import EXERCISE_METADATA
    from .exercise_content import EXERCISE_CONTENT
    from .exercise_content_gap_fill import EXERCISE_CONTENT_GAP_FILL as EXERCISE_CONTENT_GAP

    meta = EXERCISE_METADATA.get(exercise_id, {})
    content = EXERCISE_CONTENT.get(exercise_id) or EXERCISE_CONTENT_GAP.get(exercise_id) or {}

    exercise = {
        'exercise_id': exercise_id,
        'exercise_name': meta.get('name', exercise_id.replace('_', ' ').title()),
        'movement_pattern': meta.get('movement_pattern', 'unknown'),
        'sets': 3,
        'reps': 10,
        'tempo': '3-1-2-0',
        'tempo_parts': ['3', '1', '2', '0'],
        'rest_seconds': 60,
        'prescribed_rest': 60,
        'is_unilateral': meta.get('unilateral', False),
        'mind_muscle_cue': content.get('mind_muscle_cue_en', ''),
        'form_cues': content.get('form_cues_en', []),
        'instructions': content.get('instructions_en', ''),
        'asymmetry': {},
        'capability_level': meta.get('capability_level', 2),
    }
    context = {
        'exercise': exercise,
        'exercise_index': 0,
        'total_exercises': 1,
        'next_index': None,
        'is_last_exercise': True,
    }
    return render(request, 'strength_app/v1_exercise_execute.html', context)


def v1_test_list(request):
    """Dev-only: list of 17 template exercises to test ghost overlay."""
    from django.conf import settings
    if not settings.DEBUG:
        from django.http import Http404
        raise Http404

    exercises = [
        {'id': 'full_squats',        'name': 'Bodyweight Squat',     'template': 'SQUAT_BILATERAL',  'type': 'rep'},
        {'id': 'pistol_squat',       'name': 'Pistol Squat',         'template': 'SQUAT_SINGLE',     'type': 'rep'},
        {'id': 'jump_squats',        'name': 'Jump Squats',          'template': 'JUMP_LANDING',     'type': 'rep'},
        {'id': 'push_ups',           'name': 'Push-Ups',             'template': 'PUSH_UP',          'type': 'rep'},
        {'id': 'planks',             'name': 'Plank Hold',           'template': 'PLANK_FRONT',      'type': 'hold'},
        {'id': 'side_plank',         'name': 'Side Plank',           'template': 'PLANK_SIDE',       'type': 'hold'},
        {'id': 'glute_bridge',       'name': 'Glute Bridge',         'template': 'HINGE_BILATERAL',  'type': 'rep'},
        {'id': 'single_leg_rdl',     'name': 'Single Leg RDL',       'template': 'HINGE_SINGLE',     'type': 'rep'},
        {'id': 'split_squat_static', 'name': 'Split Squat',          'template': 'LUNGE_SPLIT',      'type': 'rep'},
        {'id': 'single_leg_balance', 'name': 'Single Leg Balance',   'template': 'BALANCE_SINGLE',   'type': 'hold'},
        {'id': 'band_pull_apart',    'name': 'Band Pull Apart',      'template': 'PULL_HORIZONTAL',  'type': 'rep'},
        {'id': 'dead_hang',          'name': 'Dead Hang',            'template': 'HANG_PULL',        'type': 'hold'},
        {'id': 'dead_bug',           'name': 'Dead Bug',             'template': 'DEAD_BUG',         'type': 'rep'},
        {'id': 'russian_twist_bw',   'name': 'Russian Twist',        'template': 'ROTATION',         'type': 'rep'},
        {'id': 'farmer_carry',       'name': 'Farmer Carry',         'template': 'CARRY_UPRIGHT',    'type': 'hold'},
        {'id': 'bear_crawl',         'name': 'Bear Crawl',           'template': 'CRAWL',            'type': 'hold'},
        {'id': 'hamstring_stretch',  'name': 'Hamstring Stretch',    'template': 'STRETCH_MOBILITY', 'type': 'hold'},
        {'id': 'pike_push_up',    'name': 'Pike Push-Up (Vertical Press)',  'template': 'PRESS_VERTICAL',  'type': 'rep'},
        {'id': 'dip_progression', 'name': 'Dip Progression (Horiz Press)',  'template': 'PRESS_HORIZONTAL','type': 'rep'},
        {'id': 'wall_slide',      'name': 'Wall Slide (Mobility)',          'template': 'STRETCH_MOBILITY','type': 'hold'},
    ]
    return render(request, 'strength_app/v1_test_list.html', {'exercises': exercises})
