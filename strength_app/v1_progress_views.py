"""
VYAYAM V1 — Progress tracking views.

Views:
  v1_progress_dashboard  — Radar + trend charts + adherence + milestones
  v1_progress_api        — AJAX JSON for Chart.js
"""

import json
from datetime import date, timedelta

from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone

from .models import (
    PatientProfile, StrengthProfile, WorkoutSession, SessionFeedback,
)
from .v1_session_views import _get_patient, _require_patient


# ============================================================================
# MILESTONES
# ============================================================================

def _streak_weeks(patient):
    """Return current consecutive-week training streak."""
    streak = 0
    check_date = date.today()
    while streak <= 52:
        week_start = check_date - timedelta(days=check_date.weekday())
        week_end = week_start + timedelta(days=6)
        count = WorkoutSession.objects.filter(
            patient=patient,
            session_date__date__gte=week_start,
            session_date__date__lte=week_end,
        ).count()
        if count > 0:
            streak += 1
            check_date = week_start - timedelta(days=1)
        else:
            break
    return streak


def _any_pattern_advanced(profiles):
    """True if any capability score improved between first and last assessment."""
    if len(profiles) < 2:
        return False
    first, last = profiles[0], profiles[-1]
    for attr in ('squat_score', 'hinge_score', 'push_score', 'pull_score',
                 'core_score', 'rotate_score', 'lunge_score'):
        if getattr(last, attr, 0) > getattr(first, attr, 0):
            return True
    return False


def _radar_balanced(profiles):
    """True if latest profile has all scores within 1 of each other."""
    if not profiles:
        return False
    p = profiles[-1]
    scores = [p.squat_score, p.hinge_score, p.push_score,
              p.pull_score, p.core_score, p.rotate_score, p.lunge_score]
    return (max(scores) - min(scores)) <= 1


def _pain_free_month(patient):
    """True if no pain reported in any session this month."""
    today = date.today()
    month_start = today.replace(day=1)
    return not SessionFeedback.objects.filter(
        patient=patient,
        created_at__date__gte=month_start,
    ).exclude(pain_reported__in=('none', '')).exists()


_MILESTONE_DEFS = [
    {'id': 'first_session',   'name': 'First Session Complete',         'icon': '🎯',
     'check': lambda p, ps: WorkoutSession.objects.filter(patient=p).exists()},
    {'id': 'sessions_10',     'name': '10 Sessions Complete',            'icon': '🏅',
     'check': lambda p, ps: WorkoutSession.objects.filter(patient=p).count() >= 10},
    {'id': 'sessions_50',     'name': '50 Sessions Complete',            'icon': '🏆',
     'check': lambda p, ps: WorkoutSession.objects.filter(patient=p).count() >= 50},
    {'id': 'week_streak_4',   'name': '4-Week Streak',                   'icon': '🔥',
     'check': lambda p, ps: _streak_weeks(p) >= 4},
    {'id': 'week_streak_8',   'name': '8-Week Streak',                   'icon': '💪',
     'check': lambda p, ps: _streak_weeks(p) >= 8},
    {'id': 'pattern_advance', 'name': 'First Pattern Level-Up',          'icon': '📈',
     'check': lambda p, ps: _any_pattern_advanced(ps)},
    {'id': 'balanced_radar',  'name': 'Balanced Radar (all within 1)',   'icon': '⚖️',
     'check': lambda p, ps: _radar_balanced(ps)},
    {'id': 'pain_free_month', 'name': 'Pain-Free Month',                 'icon': '💚',
     'check': lambda p, ps: _pain_free_month(p)},
]


def _compute_milestones(patient, profiles):
    result = []
    for m in _MILESTONE_DEFS:
        try:
            achieved = m['check'](patient, list(profiles))
        except Exception:
            achieved = False
        result.append({
            'id': m['id'],
            'name': m['name'],
            'icon': m['icon'],
            'achieved': achieved,
        })
    return result


def check_new_milestones(patient, profiles, previously_achieved_ids):
    """Return list of newly achieved milestones (dicts) not in previously_achieved_ids."""
    all_milestones = _compute_milestones(patient, profiles)
    return [
        m for m in all_milestones
        if m['achieved'] and m['id'] not in previously_achieved_ids
    ]


# ============================================================================
# VIEW: PROGRESS DASHBOARD
# ============================================================================

def v1_progress_dashboard(request):
    patient, err = _require_patient(request)
    if err:
        return err

    profiles = list(StrengthProfile.objects.filter(patient=patient).order_by('assessed_at'))
    milestones = _compute_milestones(patient, profiles)
    total_sessions = WorkoutSession.objects.filter(patient=patient).count()
    streak = _streak_weeks(patient)

    # Adherence this month
    today = date.today()
    month_start = today.replace(day=1)
    sessions_this_month = WorkoutSession.objects.filter(
        patient=patient, session_date__date__gte=month_start
    ).count()
    weeks_passed = max(1, (today - month_start).days // 7 + 1)
    prescribed = (patient.sessions_per_week or 3) * weeks_passed
    adherence = min(100, round(sessions_this_month / max(1, prescribed) * 100))

    # Current + first radar data
    current_profile = profiles[-1] if profiles else None
    first_profile = profiles[0] if len(profiles) > 1 else None

    def profile_to_radar(p):
        if not p:
            return [2, 2, 2, 2, 2, 2, 2]
        return [p.squat_score, p.hinge_score, p.push_score, p.pull_score,
                p.core_score, p.rotate_score, p.lunge_score]

    radar_labels = ['Squat', 'Hinge', 'Push', 'Pull', 'Core', 'Rotate', 'Lunge']
    radar_current = profile_to_radar(current_profile)
    radar_first = profile_to_radar(first_profile)

    adherence_ring_offset = round(283 - (adherence / 100 * 283))

    # ── Gamified radar + patterns ─────────────────────────────────────────
    from .v1_gamification import (
        compute_movement_patterns, compute_radar_path, compute_asymmetry,
    )
    movement_patterns = compute_movement_patterns(current_profile, first_profile)
    radar_path = compute_radar_path(movement_patterns)
    asymmetry = compute_asymmetry(current_profile)

    # ── DA-F1: pain by exercise (last 4 weeks) ────────────────────────────
    from .models import ExerciseExecution
    from datetime import timedelta as _td
    pain_rows = list(
        ExerciseExecution.objects.filter(
            session__patient=patient,
            pain_reported=True,
            session__session_date__gte=timezone.now() - _td(weeks=4),
        ).select_related('session').order_by('-session__session_date')[:10]
    )

    context = {
        'patient': patient,
        'profiles': profiles,
        'milestones': milestones,
        'total_sessions': total_sessions,
        'streak_weeks': streak,
        'adherence_percent': adherence,
        'adherence_ring_offset': adherence_ring_offset,
        'sessions_this_month': sessions_this_month,
        'radar_labels_json': json.dumps(radar_labels),
        'radar_current_json': json.dumps(radar_current),
        'radar_first_json': json.dumps(radar_first),
        'has_comparison': bool(first_profile),
        'has_strength_profile': True,
        # Gamified vars
        'movement_patterns': movement_patterns,
        'radar_path': radar_path,
        'asymmetry': asymmetry,
        'pain_rows': pain_rows,
    }
    return render(request, 'strength_app/v1_progress.html', context)


# ============================================================================
# VIEW: PROGRESS API (AJAX JSON for Chart.js)
# ============================================================================

def v1_progress_api(request):
    patient = _get_patient(request)
    if not patient:
        return JsonResponse({'error': 'not logged in'}, status=401)

    profiles = list(StrengthProfile.objects.filter(patient=patient).order_by('assessed_at'))

    history = []
    for p in profiles:
        history.append({
            'date': p.assessed_at.isoformat() if p.assessed_at else '',
            'squat': p.squat_score,
            'hinge': p.hinge_score,
            'push': p.push_score,
            'pull': p.pull_score,
            'core': p.core_score,
            'rotate': p.rotate_score,
            'lunge': p.lunge_score,
        })

    today = date.today()
    month_start = today.replace(day=1)
    sessions_this_month = WorkoutSession.objects.filter(
        patient=patient, session_date__date__gte=month_start
    ).count()
    weeks_passed = max(1, (today - month_start).days // 7 + 1)
    prescribed = (patient.sessions_per_week or 3) * weeks_passed
    adherence = min(100, round(sessions_this_month / max(1, prescribed) * 100))

    streak = _streak_weeks(patient)
    milestones = _compute_milestones(patient, profiles)
    total_sessions = WorkoutSession.objects.filter(patient=patient).count()

    return JsonResponse({
        'history': history,
        'adherence_percent': adherence,
        'streak_weeks': streak,
        'milestones': milestones,
        'total_sessions': total_sessions,
    })


# ============================================================================
# VIEW: PROFILE
# ============================================================================

def v1_profile(request):
    patient, err = _require_patient(request)
    if err:
        return err

    from .v1_gamification import (
        compute_xp_and_level, compute_streak_days, compute_achievements,
    )

    gam = compute_xp_and_level(patient)
    streak_days = compute_streak_days(patient)
    achievements = compute_achievements(patient, gam['sessions_count'], streak_days)

    context = {
        'patient': patient,
        'user_level': gam['user_level'],
        'level_title': gam['level_title'],
        'level_pct': gam['xp_percentage'],
        'total_xp': gam['total_xp'],
        'streak_days': streak_days,
        'sessions_count': gam['sessions_count'],
        'achievements': achievements,
        'has_strength_profile': True,
    }
    return render(request, 'strength_app/v1_profile.html', context)
