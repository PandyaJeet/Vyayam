"""
VYAYAM V1 — Coach/Therapist Dashboard Views

Views:
  coach_login               — Django auth login for coaches
  coach_logout              — Logout
  coach_squad               — All linked athletes with status indicators
  coach_athlete_detail      — Full athlete profile for one patient
  coach_override_prescription — Add/remove exercises from AI prescription
  coach_flag_review         — AJAX flag athlete for in-person review
  coach_set_competition     — Set athlete competition date
  coach_add_athlete         — Link a patient to this coach by patient_id
"""

import json
from datetime import date

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .rate_limiter import rate_limit

from .models import (
    PatientProfile, StrengthProfile, PeriodisationState,
    WorkoutSession, SessionFeedback, TherapistProfile,
    TherapistPrescription, CoachPatientLink,
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


def _athlete_status(patient, last_session, last_feedback):
    days_since = 999
    if last_session:
        try:
            sess_date = last_session.session_date.date()
        except AttributeError:
            sess_date = last_session.session_date
        days_since = (date.today() - sess_date).days

    traffic = last_feedback.traffic_light if last_feedback else 'green'

    if days_since > 14 or traffic == 'red':
        return 'red', 'Needs Attention', days_since
    elif days_since > 7 or traffic == 'yellow':
        return 'yellow', 'Monitor', days_since
    return 'green', 'On Track', days_since


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
        coach=request.therapist, is_active=True
    ).select_related('patient')

    athletes = []
    for link in links:
        patient = link.patient
        profile = StrengthProfile.objects.filter(patient=patient).order_by('-assessed_at').first()
        last_session = WorkoutSession.objects.filter(patient=patient).order_by('-session_date').first()
        last_feedback = SessionFeedback.objects.filter(patient=patient).order_by('-created_at').first()

        status, status_label, days_since = _athlete_status(patient, last_session, last_feedback)

        recent_pain = SessionFeedback.objects.filter(
            patient=patient,
            pain_reported__in=['moderate', 'severe'],
        ).order_by('-created_at').first()

        athletes.append({
            'patient': patient,
            'profile': profile,
            'status': status,
            'status_label': status_label,
            'last_session_date': last_session.session_date if last_session else None,
            'days_since': days_since,
            'traffic_light': last_feedback.traffic_light if last_feedback else 'green',
            'total_sessions': WorkoutSession.objects.filter(patient=patient).count(),
            'has_pain_flag': recent_pain is not None,
            'pain_location': recent_pain.pain_location if recent_pain else '',
            'current_phase': _get_phase(patient),
            'adherence': _calc_adherence(patient),
        })

    # Sort: red → yellow → green
    athletes.sort(key=lambda a: {'red': 0, 'yellow': 1, 'green': 2}[a['status']])

    context = {
        'athletes': athletes,
        'total_athletes': len(athletes),
        'needs_attention': sum(1 for a in athletes if a['status'] == 'red'),
        'on_track': sum(1 for a in athletes if a['status'] == 'green'),
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

    profile = StrengthProfile.objects.filter(patient=patient).order_by('-assessed_at').first()
    all_profiles = list(
        StrengthProfile.objects.filter(patient=patient)
        .order_by('assessed_at')
        .values('assessed_at', 'squat_score', 'hinge_score', 'push_score',
                'pull_score', 'core_score', 'rotate_score', 'lunge_score')
    )
    # Convert datetimes to strings for JSON
    for p in all_profiles:
        if p.get('assessed_at'):
            p['assessed_at'] = p['assessed_at'].isoformat()

    try:
        period_state = patient.periodisation
    except PeriodisationState.DoesNotExist:
        period_state = None

    recent_sessions = WorkoutSession.objects.filter(patient=patient).order_by('-session_date')[:20]
    recent_feedback = SessionFeedback.objects.filter(patient=patient).order_by('-created_at')[:10]

    pain_history = (
        SessionFeedback.objects
        .filter(patient=patient)
        .exclude(pain_reported__in=('none', '', 'mild'))
        .order_by('-created_at')[:15]
    )

    # Asymmetry data from latest profile
    asymmetry = {}
    if profile:
        for pat in ('hinge', 'lunge', 'rotate'):
            asym = getattr(profile, f'{pat}_asymmetry', 'none')
            if asym != 'none':
                asymmetry[pat] = {
                    'level': asym,
                    'weaker': getattr(profile, f'weaker_side_{pat}', ''),
                }

    # Radar data
    if profile:
        radar_data = {
            'Squat': profile.squat_score, 'Hinge': profile.hinge_score,
            'Push': profile.push_score, 'Pull': profile.pull_score,
            'Core': profile.core_score, 'Rotate': profile.rotate_score,
            'Lunge': profile.lunge_score,
        }
    else:
        radar_data = {k: 0 for k in ['Squat', 'Hinge', 'Push', 'Pull', 'Core', 'Rotate', 'Lunge']}

    # Active coach override
    active_override = (
        TherapistPrescription.objects
        .filter(patient=patient, therapist=request.therapist, active=True)
        .order_by('-created_date')
        .first()
    )

    # Coach notes from link
    link = CoachPatientLink.objects.filter(coach=request.therapist, patient=patient).first()

    context = {
        'patient': patient,
        'profile': profile,
        'all_profiles_json': json.dumps(all_profiles),
        'period_state': period_state,
        'recent_sessions': recent_sessions,
        'recent_feedback': recent_feedback,
        'pain_history': pain_history,
        'asymmetry': asymmetry,
        'red_flags': patient.red_flags_json or [],
        'equipment': patient.equipment_available_json or [],
        'radar_labels_json': json.dumps(list(radar_data.keys())),
        'radar_data_json': json.dumps(list(radar_data.values())),
        'active_override': active_override,
        'coach_notes': link.notes if link else '',
        'link': link,
        'coach': request.therapist,
        'adherence': _calc_adherence(patient),
        'current_phase': _get_phase(patient),
    }
    return render(request, 'strength_app/coach_athlete_detail.html', context)


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
            duration_weeks=int(request.POST.get('duration_weeks', 4)),
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
        patient.competition_date = comp_date_str
        patient.save(update_fields=['competition_date'])
    return redirect('coach_athlete_detail', patient_id=patient_id)


@coach_required
def coach_add_athlete(request):
    error = None
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        try:
            patient = PatientProfile.objects.get(phone=phone)
            CoachPatientLink.objects.get_or_create(
                coach=request.therapist, patient=patient,
                defaults={'is_active': True}
            )
            return redirect('coach_squad')
        except PatientProfile.DoesNotExist:
            error = 'No patient found with this phone number.'

    return render(request, 'strength_app/coach_add_athlete.html', {
        'coach': request.therapist,
        'error': error,
    })


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
