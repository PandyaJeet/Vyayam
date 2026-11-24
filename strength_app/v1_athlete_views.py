"""
VYAYAM V1 — Athlete-Facing Views (football track)

The athlete PWA: a coach-linked football athlete's own home, distinct from
the generic patient dashboard and the therapist-managed rehab flow.

Views:
  athlete_today     — phase badge, next-match countdown, today's training,
                      tests-due card, weekly load indicator
  athlete_progress  — test battery scores, football level, consistency,
                      sRPE trend (performance framing only)
  athlete_profile   — identity, coach, phase/week, match calendar, logout

Routing: patient_login redirects here when the patient is football-track
(athlete_sport == 'football') AND has an active CoachPatientLink.
Training-readiness wording only — no clinical/rehab language.
"""

from datetime import date, timedelta

from django.shortcuts import redirect, render

from .models import (
    CoachPatientLink, FootballProfile, MatchDate, PatientProfile,
    PeriodisationState, SessionFeedback, WorkoutSession,
)


# ============================================================================
# HELPERS
# ============================================================================

def is_coached_football_athlete(patient):
    """The athlete-PWA routing predicate — shared with patient_login."""
    return (
        patient.athlete_sport == 'football'
        and CoachPatientLink.objects.filter(patient=patient, is_active=True).exists()
    )


def _require_athlete(request):
    """Resolve the session patient and require the football-athlete track."""
    pid = request.session.get('patient_id')
    if not pid:
        return None, redirect('patient_login')
    try:
        patient = PatientProfile.objects.get(patient_id=pid)
    except PatientProfile.DoesNotExist:
        return None, redirect('patient_login')
    if not is_coached_football_athlete(patient):
        # Not on the athlete track — send them to their own home.
        if patient.therapist_managed:
            return None, redirect('therapist_session_today')
        return None, redirect('v1_dashboard')
    return patient, None


def _first_name(patient):
    return (patient.name or '').split()[0] if patient.name else 'Athlete'


def _football(patient):
    return FootballProfile.objects.filter(patient=patient).first()


def _coach_link(patient):
    return (
        CoachPatientLink.objects.filter(patient=patient, is_active=True)
        .select_related('coach').first()
    )


def _next_match(patient):
    match = MatchDate.objects.filter(
        patient=patient, match_date__gte=date.today()
    ).order_by('match_date').first()
    if not match:
        return None
    return {'match': match, 'days_away': (match.match_date - date.today()).days}


def _sessions_this_week(patient):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    return WorkoutSession.objects.filter(
        patient=patient, session_date__date__gte=week_start
    ).count()


def _weekly_consistency(patient, weeks=4):
    """[{'week_start', 'sessions', 'avg_rpe'}] oldest-first, last N ISO weeks."""
    today = date.today()
    this_week_start = today - timedelta(days=today.weekday())
    out = []
    for i in range(weeks - 1, -1, -1):
        wk_start = this_week_start - timedelta(weeks=i)
        wk_end = wk_start + timedelta(days=6)
        sessions_qs = WorkoutSession.objects.filter(
            patient=patient,
            session_date__date__gte=wk_start,
            session_date__date__lte=wk_end,
        )
        rpes = list(
            SessionFeedback.objects.filter(patient=patient, session__in=sessions_qs)
            .values_list('session_rpe', flat=True)
        )
        out.append({
            'week_start': wk_start,
            'sessions': sessions_qs.count(),
            'avg_rpe': round(sum(rpes) / len(rpes), 1) if rpes else None,
        })
    return out


# ============================================================================
# TODAY
# ============================================================================

def _rtp_athlete_status(patient):
    from .rtp import visibility
    return visibility.athlete_status(patient)


def athlete_today(request):
    patient, err = _require_athlete(request)
    if err:
        return err

    football = _football(patient)

    # Today's prescribed training — same engine the session flow executes.
    session_data = None
    try:
        from .v1_prescription_engine import generate_v1_session
        session_data = generate_v1_session(patient)
    except Exception:
        session_data = None

    status = (session_data or {}).get('status', '')
    working_sets = (session_data or {}).get('working_sets', []) or []

    # Re-test due? (4+ weeks since the last battery.)
    from .v1_football_views import football_reassessment_check
    tests_due = football_reassessment_check(patient)

    planned = patient.sessions_per_week or 3
    done_this_week = _sessions_this_week(patient)

    context = {
        'patient': patient,
        'first_name': _first_name(patient),
        'football': football,
        'phase_label': football.get_season_phase_display() if football else None,
        'next_match': _next_match(patient),
        'session_status': status,
        'session_stop_reason': (session_data or {}).get('stop_reason', ''),
        'working_sets': working_sets,
        'session_summary': (session_data or {}).get('session_summary', {}),
        'tests_due': tests_due,
        'sessions_done': done_this_week,
        'sessions_planned': planned,
        'load_pct': min(100, round(done_this_week / planned * 100)) if planned else 0,
        'today': date.today(),
        'rtp_status': _rtp_athlete_status(patient),
    }
    return render(request, 'strength_app/athlete_today.html', context)


# ============================================================================
# PROGRESS
# ============================================================================

def athlete_progress(request):
    patient, err = _require_athlete(request)
    if err:
        return err

    football = _football(patient)

    battery = []
    level_config = None
    if football:
        battery = [
            {'label': 'Single-Leg Hop', 'score': football.hop_score, 'icon': 'sprint'},
            {'label': 'Nordic Hold', 'score': football.nordic_score, 'icon': 'fitness_center'},
            {'label': '20 m Sprint', 'score': football.sprint_score, 'icon': 'bolt'},
            # App-specific reactivity count — never labelled RSI (SB-9).
            {'label': 'Pogo Reactivity', 'score': football.pogo_score, 'icon': 'trending_up'},
            {'label': 'COD 505', 'score': football.cod_score, 'icon': 'alt_route'},
            {'label': 'Y-Balance', 'score': football.ybalance_score, 'icon': 'balance'},
        ]
        for entry in battery:
            entry['pct'] = entry['score'] * 20
        from .v1_football_constants import FOOTBALL_LEVELS
        level_config = FOOTBALL_LEVELS.get(football.football_level)

    # Bench/leg press manual-entry strength tests (2026-07 Part 3) —
    # display only, never part of football_level (SB-5a deferred).
    strength_tests = []
    raw = patient.raw_test_data_json if isinstance(patient.raw_test_data_json, dict) else {}
    for key, label, icon in (('bench_press', 'Bench Press', 'fitness_center'),
                             ('leg_press', 'Leg Press', 'airline_seat_legroom_extra')):
        rec = (raw.get('strength_tests') or {}).get(key)
        if isinstance(rec, dict) and rec.get('e1rm'):
            strength_tests.append({
                'label': label,
                'icon': icon,
                'weight_kg': rec.get('weight_kg'),
                'reps': rec.get('reps'),
                'e1rm': rec.get('e1rm'),
                'rel_bw': rec.get('rel_bw'),
                'tested_at': rec.get('tested_at', ''),
            })

    weekly = _weekly_consistency(patient, weeks=4)
    four_week_total = sum(w['sessions'] for w in weekly)

    # sRPE trend, last 14 days — one point per completed training.
    cutoff = date.today() - timedelta(days=14)
    rpe_rows = (
        SessionFeedback.objects.filter(
            patient=patient, session__session_date__date__gte=cutoff
        )
        .select_related('session')
        .order_by('session__session_date')
    )
    srpe_trend = [
        {
            'date': fb.session.session_date,
            'rpe': fb.session_rpe,
            'pct': fb.session_rpe * 10,
        }
        for fb in rpe_rows
    ]

    context = {
        'patient': patient,
        'first_name': _first_name(patient),
        'football': football,
        'battery': battery,
        'level_config': level_config,
        'strength_tests': strength_tests,
        'weekly': weekly,
        'sessions_this_week': weekly[-1]['sessions'] if weekly else 0,
        'sessions_planned': patient.sessions_per_week or 3,
        'four_week_total': four_week_total,
        'srpe_trend': srpe_trend,
    }
    return render(request, 'strength_app/athlete_progress.html', context)


# ============================================================================
# PROFILE
# ============================================================================

def athlete_profile(request):
    patient, err = _require_athlete(request)
    if err:
        return err

    football = _football(patient)
    link = _coach_link(patient)

    periodisation = PeriodisationState.objects.filter(patient=patient).first()

    upcoming_matches = MatchDate.objects.filter(
        patient=patient, match_date__gte=date.today()
    ).order_by('match_date')[:8]

    position = ''
    if isinstance(patient.raw_test_data_json, dict):
        position = patient.raw_test_data_json.get('position', '')

    context = {
        'patient': patient,
        'first_name': _first_name(patient),
        'football': football,
        'phase_label': football.get_season_phase_display() if football else None,
        'coach': link.coach if link else None,
        'periodisation': periodisation,
        'upcoming_matches': upcoming_matches,
        'position': position,
        'today': date.today(),
    }
    return render(request, 'strength_app/athlete_profile.html', context)
