"""
VYAYAM V1 — Coach/Therapist Dashboard Views

Views:
  coach_login                 — Django auth login for coaches
  coach_logout                — Logout
  coach_squad                 — Football S&C squad dashboard, one row per athlete
  coach_athlete_detail        — Full S&C monitoring view for one athlete
  coach_override_prescription — Add/remove exercises from AI prescription
  coach_flag_review           — AJAX flag athlete for in-person review
  coach_set_competition       — Set next match / competition date
  coach_add_athlete           — Onboard a brand-new athlete and link to coach
  coach_save_notes            — AJAX save coach notes on an athlete
"""

import json
import secrets
import string
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .rate_limiter import rate_limit

from .models import (
    PatientProfile, StrengthProfile, PeriodisationState,
    WorkoutSession, SessionFeedback, TherapistProfile,
    TherapistPrescription, CoachPatientLink,
    FootballProfile, MatchDate,
)


# ============================================================================
# DECORATOR
# ============================================================================

def coach_required(view_func):
    """Requires authenticated Django User with a linked TherapistProfile."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('coach_login')
        try:
            request.therapist = request.user.therapistprofile
        except TherapistProfile.DoesNotExist:
            return redirect('coach_login')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ============================================================================
# HELPERS
# ============================================================================

def _get_phase(patient):
    try:
        return patient.periodisation.get_current_phase_display()
    except PeriodisationState.DoesNotExist:
        return '—'


def _calc_adherence(patient):
    today = date.today()
    month_start = today.replace(day=1)
    done = WorkoutSession.objects.filter(
        patient=patient, session_date__date__gte=month_start
    ).count()
    weeks_passed = max(1, (today - month_start).days // 7 + 1)
    prescribed = (patient.sessions_per_week or 3) * weeks_passed
    return min(100, round(done / max(1, prescribed) * 100))


def _athlete_status(patient, last_session, last_feedback, football, link):
    days_since = 999
    if last_session:
        try:
            sess_date = last_session.session_date.date()
        except AttributeError:
            sess_date = last_session.session_date
        days_since = (date.today() - sess_date).days

    traffic = last_feedback.traffic_light if last_feedback else 'green'

    flagged = bool(link and link.notes and '[FLAGGED' in link.notes)
    lsi_flag = bool(football and football.lsi_flag)
    plyo_not_cleared = bool(football and football.plyometric_cleared == 'none')

    if (
        days_since > 14
        or traffic == 'red'
        or flagged
        or lsi_flag
    ):
        return 'red', 'Needs Attention', days_since
    if days_since > 7 or traffic == 'yellow' or plyo_not_cleared:
        return 'yellow', 'Monitor', days_since
    return 'green', 'On Track', days_since


def _weekly_load(patient, weeks=4):
    """Return [{'week_start': date, 'sessions': int, 'avg_rpe': float|None}] for the last `weeks` ISO weeks (oldest first)."""
    today = date.today()
    week_start_of_today = today - timedelta(days=today.weekday())
    buckets = []
    for i in range(weeks - 1, -1, -1):
        wk_start = week_start_of_today - timedelta(weeks=i)
        wk_end = wk_start + timedelta(days=6)
        sessions_qs = WorkoutSession.objects.filter(
            patient=patient,
            session_date__date__gte=wk_start,
            session_date__date__lte=wk_end,
        )
        count = sessions_qs.count()
        rpes = list(
            SessionFeedback.objects.filter(
                patient=patient,
                session__in=sessions_qs,
            ).values_list('session_rpe', flat=True)
        )
        avg_rpe = round(sum(rpes) / len(rpes), 1) if rpes else None
        buckets.append({
            'week_start': wk_start,
            'sessions': count,
            'avg_rpe': avg_rpe,
        })
    return buckets


def _generate_athlete_phone():
    """Find the next 10-digit phone in the coach-onboard block 9100010000+ not held by any PatientProfile."""
    base = 9100010000
    # Scan PatientProfile phones in our block; pick smallest unused.
    used = set(
        PatientProfile.objects.filter(phone__startswith='9100010')
        .values_list('phone', flat=True)
    )
    for n in range(base, base + 100000):
        candidate = str(n)
        if candidate not in used:
            return candidate
    return None


def _generate_temp_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def _generate_patient_id():
    """Next CO-<n> id not taken. CO = Coach-Onboarded."""
    existing = set(
        PatientProfile.objects.filter(patient_id__startswith='CO-')
        .values_list('patient_id', flat=True)
    )
    n = 1
    while True:
        pid = f'CO-{n:05d}'
        if pid not in existing:
            return pid
        n += 1


# ============================================================================
# AUTH
# ============================================================================

@rate_limit(max_attempts=5, window_seconds=300, key_prefix='coach_login')
def coach_login(request):
    if request.user.is_authenticated and hasattr(request.user, 'therapistprofile'):
        return redirect('coach_squad')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user and hasattr(user, 'therapistprofile'):
            request.session.flush()
            login(request, user)
            return redirect('coach_squad')
        error = 'Invalid credentials or not a registered coach.'

    return render(request, 'strength_app/coach_login.html', {'error': error})


def coach_logout(request):
    logout(request)
    return redirect('coach_login')


# ============================================================================
# SQUAD VIEW
# ============================================================================

@coach_required
def coach_squad(request):
    links = CoachPatientLink.objects.filter(
        coach=request.therapist, is_active=True, patient__athlete_tier_eligible=True
    ).select_related('patient')

    athletes = []
    for link in links:
        patient = link.patient
        football = FootballProfile.objects.filter(patient=patient).first()
        last_session = WorkoutSession.objects.filter(patient=patient).order_by('-session_date').first()
        last_feedback = SessionFeedback.objects.filter(patient=patient).order_by('-created_at').first()

        status, status_label, days_since = _athlete_status(
            patient, last_session, last_feedback, football, link
        )

        flagged = bool(link.notes and '[FLAGGED' in link.notes)

        athletes.append({
            'patient': patient,
            'football': football,
            'status': status,
            'status_label': status_label,
            'last_session_date': last_session.session_date if last_session else None,
            'days_since': days_since,
            'traffic_light': last_feedback.traffic_light if last_feedback else 'green',
            'football_level': football.football_level if football else None,
            'hsr_phase_display': football.get_hsr_current_phase_display() if football else '—',
            'season_phase_display': football.get_season_phase_display() if football else '—',
            'lsi_flag': football.lsi_flag if football else False,
            'plyometric_cleared': football.plyometric_cleared if football else 'none',
            'plyometric_cleared_display': (
                football.get_plyometric_cleared_display() if football else 'Not Cleared'
            ),
            'flagged': flagged,
            'has_assessment': football is not None,
            'adherence': _calc_adherence(patient),
            'sport': patient.athlete_sport or patient.sport_type or 'football',
            'position': (
                patient.raw_test_data_json.get('position', '')
                if isinstance(patient.raw_test_data_json, dict) else ''
            ),
        })

    athletes.sort(key=lambda a: {'red': 0, 'yellow': 1, 'green': 2}[a['status']])

    context = {
        'athletes': athletes,
        'total_athletes': len(athletes),
        'needs_attention': sum(1 for a in athletes if a['status'] == 'red'),
        'monitor': sum(1 for a in athletes if a['status'] == 'yellow'),
        'on_track': sum(1 for a in athletes if a['status'] == 'green'),
        'no_assessment': sum(1 for a in athletes if not a['has_assessment']),
        'coach': request.therapist,
    }
    return render(request, 'strength_app/coach_squad.html', context)


# ============================================================================
# ATHLETE DETAIL
# ============================================================================

@coach_required
def coach_athlete_detail(request, patient_id):
    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    get_object_or_404(CoachPatientLink, coach=request.therapist, patient=patient, is_active=True)

    football = FootballProfile.objects.filter(patient=patient).first()

    # 1 — Baseline battery: six football tests + raw values + scores + last reassessment.
    if football:
        battery = [
            {
                'key': 'hop',
                'label': 'Hop (bilateral)',
                'score': football.hop_score,
                'raw': _format_lr(football.hop_left_cm, football.hop_right_cm, unit='cm'),
            },
            {
                'key': 'nordic',
                'label': 'Nordic',
                'score': football.nordic_score,
                'raw': _format_single(football.nordic_seconds, unit='s'),
            },
            {
                'key': 'sprint',
                'label': 'Sprint',
                'score': football.sprint_score,
                'raw': _format_single(football.sprint_seconds, unit='s'),
            },
            {
                'key': 'pogo',
                # R2-W2-1 (SB-9): app-specific reactivity count — never
                # labelled RSI/reactive-strength (needs a force plate).
                'label': 'Pogo (reactivity count — app metric)',
                'score': football.pogo_score,
                'raw': _format_single(football.pogo_clean_reps, unit='springy reps'),
            },
            {
                'key': 'cod',
                'label': 'Change-of-direction',
                'score': football.cod_score,
                'raw': _format_lr(football.cod_left_seconds, football.cod_right_seconds, unit='s'),
            },
            {
                'key': 'ybalance',
                'label': 'Y-Balance',
                'score': football.ybalance_score,
                'raw': _format_lr(football.ybalance_left_pct, football.ybalance_right_pct, unit='%'),
            },
        ]
    else:
        battery = []

    # 4 — Asymmetry / LSI panel. R2-W2-2 (SB-11): per-test bands from
    # LSI_THRESHOLDS; the messaging names each test's own benchmark.
    asymmetry_panel = []
    if football:
        from .v1_football_constants import LSI_THRESHOLDS
        for key, label, pct in [
            ('hop', 'Hop LSI', football.hop_lsi_pct),
            ('cod', 'COD LSI', football.cod_lsi_pct),
            ('ybalance', 'Y-Balance LSI', football.ybalance_lsi_pct),
        ]:
            threshold = LSI_THRESHOLDS[key]
            asymmetry_panel.append({
                'key': key,
                'label': f'{label} (benchmark ≥{threshold}%)',
                'pct': pct,
                'below_threshold': (pct is not None and pct < threshold),
            })

    # 5 — Plyometric readiness gate: what's blocking it.
    plyo_blockers = []
    if football:
        from .v1_football_constants import PLYOMETRIC_GATES
        # Show the requirements of the NEXT tier the athlete has not yet cleared.
        order = ['none', 'low_load', 'moderate_load', 'high_load']
        try:
            idx = order.index(football.plyometric_cleared)
        except ValueError:
            idx = 0
        next_tier = order[idx + 1] if idx + 1 < len(order) else None
        if next_tier:
            req = PLYOMETRIC_GATES[next_tier]['requirements']
            checks = []
            checks.append({
                'name': f"Football level ≥ {req['min_football_level']}",
                'ok': football.football_level >= req['min_football_level'],
                'current': f"L{football.football_level}",
            })
            lsi_now = football.hop_lsi_pct or 0
            checks.append({
                'name': f"Hop LSI ≥ {req['lsi_min_pct']}%",
                'ok': lsi_now >= req['lsi_min_pct'],
                'current': f"{lsi_now:.0f}%" if football.hop_lsi_pct is not None else 'no data',
            })
            checks.append({
                'name': f"Hop score ≥ {req['hop_score_min']}/5",
                'ok': football.hop_score >= req['hop_score_min'],
                'current': f"{football.hop_score}/5",
            })
            if 'nordic_score_min' in req:
                checks.append({
                    'name': f"Nordic score ≥ {req['nordic_score_min']}/5",
                    'ok': football.nordic_score >= req['nordic_score_min'],
                    'current': f"{football.nordic_score}/5",
                })
            if 'sprint_score_min' in req:
                checks.append({
                    'name': f"Sprint score ≥ {req['sprint_score_min']}/5",
                    'ok': football.sprint_score >= req['sprint_score_min'],
                    'current': f"{football.sprint_score}/5",
                })
            plyo_blockers = {
                'next_tier_label': PLYOMETRIC_GATES[next_tier]['label'],
                'checks': checks,
            }

    # 6 — Load + calendar.
    weekly_load = _weekly_load(patient, weeks=4)
    upcoming_matches = MatchDate.objects.filter(
        patient=patient, match_date__gte=date.today()
    ).order_by('match_date')[:8]

    # 7 — Adherence + form quality (last 12 sessions of WorkoutSession + SessionFeedback).
    recent_sessions = (
        WorkoutSession.objects.filter(patient=patient)
        .order_by('-session_date')[:12]
        # DA-F1: per-session pain expansion in the athlete detail view
        .prefetch_related('exercises')
    )
    recent_feedback = SessionFeedback.objects.filter(patient=patient).order_by('-created_at')[:10]

    avg_form = None
    form_scores = [s.overall_session_form_score for s in recent_sessions if s.overall_session_form_score]
    if form_scores:
        avg_form = round(sum(form_scores) / len(form_scores), 1)

    # Active coach override.
    active_override = (
        TherapistPrescription.objects
        .filter(patient=patient, therapist=request.therapist, active=True)
        .order_by('-created_date')
        .first()
    )

    link = CoachPatientLink.objects.filter(coach=request.therapist, patient=patient).first()

    context = {
        'patient': patient,
        'football': football,
        'battery': battery,
        'asymmetry_panel': asymmetry_panel,
        'plyo_blockers': plyo_blockers,
        'weekly_load': weekly_load,
        'upcoming_matches': upcoming_matches,
        'recent_sessions': recent_sessions,
        'recent_feedback': recent_feedback,
        'avg_form': avg_form,
        'active_override': active_override,
        'coach_notes': link.notes if link else '',
        'link': link,
        'coach': request.therapist,
        'adherence': _calc_adherence(patient),
    }
    return render(request, 'strength_app/coach_athlete_detail.html', context)


def _format_lr(left, right, unit=''):
    if left is None and right is None:
        return '—'
    l = f"{left:g}" if left is not None else '—'
    r = f"{right:g}" if right is not None else '—'
    return f"L {l} / R {r} {unit}".strip()


def _format_single(value, unit=''):
    if value is None:
        return '—'
    return f"{value:g} {unit}".strip()


# ============================================================================
# COACH ACTIONS
# ============================================================================

@coach_required
def coach_override_prescription(request, patient_id):
    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    get_object_or_404(CoachPatientLink, coach=request.therapist, patient=patient, is_active=True)

    if request.method == 'POST':
        exercises_raw = request.POST.get('exercises_json', '[]')
        try:
            exercises = json.loads(exercises_raw)
        except json.JSONDecodeError:
            exercises = []

        # DA-P4 (Phase 4 row 5): validate the override payload — every
        # item must reference a known exercise and carry sane dosage.
        # Invalid payloads re-render with an inline error instead of
        # writing junk into TherapistPrescription.
        from .validation import safe_int
        from .exercise_system.exercise_registry_v2 import EXERCISE_METADATA
        from .exercise_content import EXERCISE_CONTENT
        from .exercise_content_gap_fill import EXERCISE_CONTENT_GAP_FILL
        known_ids = (set(EXERCISE_METADATA) | set(EXERCISE_CONTENT)
                     | set(EXERCISE_CONTENT_GAP_FILL))

        if not isinstance(exercises, list):
            exercises = []
        validated, invalid = [], []
        for item in exercises:
            if not isinstance(item, dict) or not item.get('exercise_id'):
                invalid.append(str(item)[:60])
                continue
            ex_id = str(item['exercise_id'])[:100]
            action = item.get('action', 'add')
            if action not in ('add', 'remove'):
                action = 'add'
            if action == 'add' and ex_id not in known_ids:
                invalid.append(ex_id)
                continue
            validated.append({
                'exercise_id': ex_id,
                'action': action,
                'sets': safe_int(item.get('sets', 3), 3, 1, 10),
                'reps': safe_int(item.get('reps', 10), 10, 1, 100),
                'movement_pattern': str(item.get('movement_pattern', ''))[:50],
            })
        if invalid:
            return render(request, 'strength_app/coach_override.html', {
                'patient': patient,
                'error': 'Unknown or malformed exercises in override: '
                         + ', '.join(invalid[:5]),
            })
        exercises = validated

        prescription_id = (
            f"TP-{request.therapist.therapist_id}-{patient_id}-{date.today().isoformat()}"
        )
        # Deactivate old prescriptions
        TherapistPrescription.objects.filter(
            patient=patient, therapist=request.therapist, active=True
        ).update(active=False)

        TherapistPrescription.objects.create(
            prescription_id=prescription_id,
            patient=patient,
            therapist=request.therapist,
            exercises_json=exercises,
            duration_weeks=safe_int(request.POST.get('duration_weeks'), 4, 1, 16),  # DA-P4
            frequency_per_week=patient.sessions_per_week or 3,
            clinical_reasoning=request.POST.get('clinical_reasoning', ''),
            special_instructions=request.POST.get('special_instructions', ''),
        )
        return redirect('coach_athlete_detail', patient_id=patient_id)

    # GET — show AI session + exercise list
    ai_session = None
    try:
        from .v1_prescription_engine import generate_v1_session
        ai_session = generate_v1_session(patient)
    except Exception:
        pass

    context = {
        'patient': patient,
        'ai_session': ai_session,
        'coach': request.therapist,
    }
    return render(request, 'strength_app/coach_override.html', context)


@require_POST
@coach_required
def coach_flag_review(request, patient_id):
    link = get_object_or_404(
        CoachPatientLink, coach=request.therapist, patient__patient_id=patient_id
    )
    note = request.POST.get('note', '').strip()
    if note:
        link.notes = (link.notes or '') + f"\n[FLAGGED {date.today()}] {note}"
        link.save(update_fields=['notes'])
    return JsonResponse({'status': 'ok'})


@require_POST
@coach_required
def coach_set_competition(request, patient_id):
    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    get_object_or_404(CoachPatientLink, coach=request.therapist, patient=patient)
    comp_date_str = request.POST.get('competition_date', '')
    if comp_date_str:
        # DA-C13: parse explicitly — assigning a raw string to a DateField
        # raised ValidationError (500) on any malformed input.
        try:
            patient.competition_date = date.fromisoformat(comp_date_str)
        except ValueError:
            messages.error(request, 'Invalid competition date — use the date picker (YYYY-MM-DD).')
            return redirect('coach_athlete_detail', patient_id=patient_id)
        patient.save(update_fields=['competition_date'])
    return redirect('coach_athlete_detail', patient_id=patient_id)


SEASON_PHASE_CHOICES = FootballProfile.SEASON_PHASE_CHOICES


@coach_required
def coach_add_athlete(request):
    error = None
    credentials = None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        sport = (request.POST.get('sport') or 'football').strip().lower()
        position = request.POST.get('position', '').strip()
        season_phase = request.POST.get('season_phase', 'in_season')
        match_date_str = request.POST.get('match_date', '').strip()
        age_str = request.POST.get('age', '').strip()
        bio_sex = request.POST.get('biological_sex', 'not_specified')

        valid_phases = {key for key, _ in SEASON_PHASE_CHOICES}

        if not name:
            error = 'Athlete name is required.'
        elif season_phase not in valid_phases:
            error = 'Invalid season phase.'
        else:
            try:
                age = int(age_str) if age_str else 22
            except ValueError:
                age = 22
            if age < 18 or age > 100:  # DA-P4: V1 is 18+ (Appendix B)
                age = 22

            phone = _generate_athlete_phone()
            if phone is None:
                error = 'Could not generate a unique athlete phone — block 9100010000 exhausted.'
            else:
                try:
                    with transaction.atomic():
                        # Re-check phone collision inside the transaction.
                        if PatientProfile.objects.filter(phone=phone).exists():
                            raise _OnboardAbort(
                                f'Phone {phone} taken between selection and create — retry.'
                            )

                        patient_id = _generate_patient_id()
                        temp_pw = _generate_temp_password()

                        patient = PatientProfile.objects.create(
                            patient_id=patient_id,
                            name=name,
                            phone=phone,
                            email='',
                            password=make_password(temp_pw),
                            age=age,
                            biological_sex=bio_sex if bio_sex in {'male', 'female', 'not_specified'} else 'not_specified',
                            goals=f'Coach-onboarded {sport} athlete — S&C programme.',
                            goal_type='athletic',
                            sport_type=sport,
                            training_history='intermediate',
                            training_age_months=24,
                            lifestyle='very_active',
                            sessions_per_week=4,
                            session_duration_minutes=60,
                            training_location='gym',
                            gate_test_completed=True,
                            therapist_managed=False,
                            athlete_tier_eligible=True,
                            athlete_tier_active=False,
                            athlete_sport=sport,
                            raw_test_data_json={'position': position} if position else {},
                        )

                        StrengthProfile.objects.create(
                            patient=patient,
                            assessment_number=1,
                            squat_score=3, hinge_score=3, push_score=3,
                            pull_score=3, core_score=3, rotate_score=3,
                            lunge_score=3,
                        )

                        # Seed FootballProfile so the dashboard reads sensibly
                        # before the athlete runs the live assessment.
                        FootballProfile.objects.create(
                            patient=patient,
                            season_phase=season_phase,
                        )

                        CoachPatientLink.objects.create(
                            coach=request.therapist,
                            patient=patient,
                            is_active=True,
                        )

                        if match_date_str:
                            try:
                                from datetime import datetime
                                md = datetime.strptime(match_date_str, '%Y-%m-%d').date()
                                MatchDate.objects.create(
                                    patient=patient,
                                    match_date=md,
                                    opponent='',
                                    notes='Set during coach onboarding.',
                                )
                            except ValueError:
                                pass  # bad date — skip silently, athlete is still created

                    credentials = {
                        'name': name,
                        'phone': phone,
                        'password': temp_pw,
                        'patient_id': patient.patient_id,
                    }
                except _OnboardAbort as exc:
                    error = str(exc)

    return render(request, 'strength_app/coach_add_athlete.html', {
        'coach': request.therapist,
        'error': error,
        'credentials': credentials,
        'season_phase_choices': SEASON_PHASE_CHOICES,
    })


class _OnboardAbort(Exception):
    """Raised inside the onboarding atomic() block to roll back the create."""


@require_POST
@coach_required
def coach_save_notes(request, patient_id):
    """AJAX endpoint to save coach notes on an athlete."""
    link = get_object_or_404(
        CoachPatientLink, coach=request.therapist, patient__patient_id=patient_id
    )
    link.notes = request.POST.get('notes', link.notes)
    link.save(update_fields=['notes'])
    return JsonResponse({'status': 'ok'})
