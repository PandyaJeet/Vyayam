"""
Patient-side flow for therapist-managed patients.

Handles:
  /therapist-session/today/                  — list today's prescribed exercises
  /therapist-session/start/                  — POST, opens a SessionLog
  /therapist-session/exercise/<int:idx>/     — execute one PrescriptionItem
  /therapist-session/feedback/<int:idx>/     — per-exercise pain/difficulty form
  /therapist-session/complete/               — overall feedback form
  /therapist-session/finished/               — confirmation page

The session-execution flow is keyed off ``request.session['therapist_session']``,
which is set when the patient hits Start and cleared on Finished.
"""

import json
from datetime import date, timedelta

from django.contrib import messages as flash
from django.db.models import Avg, Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import PatientProfile
from therapist_app.exercise_catalog import EXERCISES_BY_ID
from therapist_app.models import (
    Prescription,
    PrescriptionItem,
    SessionLog,
    SessionLogItem,
    TherapistMessage,
    TherapistPatientLink,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _require_patient(request):
    pid = request.session.get('patient_id')
    if not pid:
        return None, redirect('patient_login')
    try:
        patient = PatientProfile.objects.get(patient_id=pid)
    except PatientProfile.DoesNotExist:
        return None, redirect('patient_login')
    if not patient.therapist_managed:
        return None, redirect('v1_dashboard')
    return patient, None


def _active_link(patient):
    """The patient's currently-active therapist link. We assume one — therapist
    apps that need multi-therapist routing can extend later."""
    if patient.user_id is None:
        return None
    return (
        TherapistPatientLink.objects
        .filter(patient_id=patient.user_id, status='active')
        .order_by('-accepted_at', '-invited_at')
        .first()
    )


def _latest_published_prescription(link):
    if link is None:
        return None
    return (
        Prescription.objects
        .filter(link=link, published_at__isnull=False)
        .order_by('-week_number', '-published_at')
        .prefetch_related('items')
        .first()
    )


def _enriched_items(rx):
    """Return prescription items with the catalog entry merged in. Used by
    both the Today list and the per-exercise pages so equipment/description/
    video_url/v2 flags come from the catalog."""
    items = list(rx.items.all().order_by('order', 'id'))
    enriched = []
    for it in items:
        catalog = EXERCISES_BY_ID.get(it.exercise_id, {})
        enriched.append({
            'item': it,
            'catalog': catalog,
            'name': it.exercise_name or catalog.get('name', it.exercise_id),
            'description': catalog.get('description', ''),
            'equipment': catalog.get('equipment', '—'),
            'video_url': catalog.get('video_url', ''),
            'v2_ghost_supported': bool(catalog.get('v2_ghost_supported', False)),
            'v2_exercise_key': catalog.get('v2_exercise_key', ''),
            'movement_pattern': it.movement_pattern or catalog.get('movement_pattern', ''),
        })
    return enriched


def _get_session_state(request):
    """Return the in-flight session state dict, or None."""
    return request.session.get('therapist_session') or None


def _set_session_state(request, state):
    request.session['therapist_session'] = state
    request.session.modified = True


def _clear_session_state(request):
    request.session.pop('therapist_session', None)
    request.session.modified = True


def _resolve_session_log(request, link, rx):
    """Return (state, log) — creates state lazily from a started SessionLog
    if the in-session dict has been cleared (e.g. after browser refresh)."""
    state = _get_session_state(request)
    log = None
    if state and state.get('log_id'):
        log = SessionLog.objects.filter(id=state['log_id']).first()
        if log and (log.is_complete or log.prescription_id != rx.id):
            log = None
            state = None
            _clear_session_state(request)
    return state, log


# ---------------------------------------------------------------------------
# views
# ---------------------------------------------------------------------------

def therapist_session_today(request):
    patient, err = _require_patient(request)
    if err:
        return err

    link = _active_link(patient)
    rx = _latest_published_prescription(link)
    items = _enriched_items(rx) if rx else []

    in_flight = None
    if rx:
        state, log = _resolve_session_log(request, link, rx)
        if state and log:
            in_flight = {'state': state, 'log': log}

    last_log = (
        SessionLog.objects
        .filter(link=link, completed_at__isnull=False)
        .order_by('-completed_at')
        .first()
        if link else None
    )

    ctx = {
        'patient': patient,
        'link': link,
        'rx': rx,
        'items': items,
        'in_flight': in_flight,
        'last_log': last_log,
        'today': date.today(),
    }
    return render(request, 'strength_app/therapist_session_today.html', ctx)


@require_POST
def therapist_session_start(request):
    patient, err = _require_patient(request)
    if err:
        return err

    link = _active_link(patient)
    rx = _latest_published_prescription(link)
    if rx is None or not rx.items.exists():
        flash.error(request, "Your therapist hasn't published a session for you yet.")
        return redirect('therapist_session_today')

    log = SessionLog.objects.create(link=link, prescription=rx)
    items = list(rx.items.all().order_by('order', 'id'))
    log_items = []
    for idx, it in enumerate(items):
        log_items.append(SessionLogItem.objects.create(
            session_log=log,
            prescription_item=it,
            order=idx,
            exercise_id=it.exercise_id,
            exercise_name=it.exercise_name,
        ))

    _set_session_state(request, {
        'log_id': log.id,
        'rx_id': rx.id,
        'item_ids': [i.id for i in items],
        'log_item_ids': [li.id for li in log_items],
        'current_index': 0,
    })

    return redirect('therapist_session_exercise', idx=0)


def therapist_session_exercise(request, idx):
    patient, err = _require_patient(request)
    if err:
        return err

    link = _active_link(patient)
    rx = _latest_published_prescription(link)
    if rx is None:
        return redirect('therapist_session_today')

    state = _get_session_state(request)
    if not state or state.get('rx_id') != rx.id:
        flash.error(request, "Session expired — please start again.")
        return redirect('therapist_session_today')

    items = _enriched_items(rx)
    if idx < 0 or idx >= len(items):
        return redirect('therapist_session_complete')

    state['current_index'] = idx
    _set_session_state(request, state)

    enriched = items[idx]
    item = enriched['item']
    is_last = (idx == len(items) - 1)

    # If the patient's exercise is V2-supported, render the existing
    # ghost-coach template with library_mode=True. The post-save redirect
    # is overridden via library_return_url so we land on the feedback page.
    if enriched['v2_ghost_supported'] and enriched['v2_exercise_key']:
        return _render_v2_ghost(request, patient, enriched, idx, len(items), is_last)

    # Otherwise render the simple (no-camera) page.
    ctx = {
        'patient': patient,
        'item': item,
        'enriched': enriched,
        'exercise_index': idx,
        'total_exercises': len(items),
        'is_last_exercise': is_last,
        'feedback_url': reverse('therapist_session_feedback', args=[idx]),
        'today_url': reverse('therapist_session_today'),
    }
    return render(request, 'strength_app/therapist_session_exercise.html', ctx)


def _render_v2_ghost(request, patient, enriched, idx, total, is_last):
    """Render v1_exercise_execute.html in library_mode with a custom
    return URL pointing at the feedback page for this PrescriptionItem."""
    from .exercise_system.exercise_registry_v2 import EXERCISE_METADATA
    from .exercise_content import EXERCISE_CONTENT
    from .exercise_content_gap_fill import EXERCISE_CONTENT_GAP_FILL as EXERCISE_CONTENT_GAP

    item = enriched['item']
    v2_key = enriched['v2_exercise_key']
    meta = EXERCISE_METADATA.get(v2_key, {})
    content = EXERCISE_CONTENT.get(v2_key) or EXERCISE_CONTENT_GAP.get(v2_key) or {}

    tempo = str(item.tempo or meta.get('tempo', '3-1-2-0'))
    tempo_parts = tempo.split('-')
    while len(tempo_parts) < 4:
        tempo_parts.append('0')

    exercise = {
        'exercise_id':    v2_key,
        'exercise_name':  item.exercise_name,
        'movement_pattern': item.movement_pattern or meta.get('movement_pattern', 'unknown'),
        'sets':           item.sets,
        'reps':           item.reps,
        'tempo':          tempo,
        'tempo_parts':    tempo_parts,
        'rest_seconds':   item.rest_seconds,
        'prescribed_rest': item.rest_seconds,
        'is_unilateral':  meta.get('unilateral', False),
        'mind_muscle_cue': content.get('mind_muscle_cue_en', ''),
        'form_cues':      content.get('form_cues_en', []),
        'instructions':   content.get('instructions_en', ''),
        'asymmetry':      {},
        'capability_level': meta.get('capability_level', 2),
    }

    feedback_url = reverse('therapist_session_feedback', args=[idx])
    ctx = {
        'patient':            patient,
        'exercise':           exercise,
        'exercise_index':     idx,
        'total_exercises':    total,
        'is_last_exercise':   is_last,
        'has_strength_profile': True,
        'library_mode':       True,
        'library_return_url': feedback_url,
        'therapist_mode':     True,
    }
    return render(request, 'strength_app/v1_exercise_execute.html', ctx)


def therapist_session_feedback(request, idx):
    patient, err = _require_patient(request)
    if err:
        return err

    link = _active_link(patient)
    rx = _latest_published_prescription(link)
    if rx is None:
        return redirect('therapist_session_today')

    state = _get_session_state(request)
    if not state or state.get('rx_id') != rx.id:
        flash.error(request, "Session expired — please start again.")
        return redirect('therapist_session_today')

    items = _enriched_items(rx)
    if idx < 0 or idx >= len(items):
        return redirect('therapist_session_complete')

    enriched = items[idx]
    item = enriched['item']
    log_item_id = state['log_item_ids'][idx]
    log_item = get_object_or_404(SessionLogItem, id=log_item_id)

    if request.method == 'POST':
        try:
            pain = int(request.POST.get('pain', 0))
        except (TypeError, ValueError):
            pain = 0
        pain = max(0, min(10, pain))
        difficulty = request.POST.get('difficulty', '')
        try:
            sets_completed = int(request.POST.get('sets_completed', item.sets))
        except (TypeError, ValueError):
            sets_completed = item.sets
        sets_completed = max(0, min(20, sets_completed))

        log_item.pain = pain
        log_item.difficulty = difficulty if difficulty in dict(SessionLogItem.DIFFICULTY_CHOICES) else ''
        log_item.sets_completed = sets_completed
        log_item.completed_at = timezone.now()
        log_item.save()

        if idx + 1 >= len(items):
            return redirect('therapist_session_complete')
        return redirect('therapist_session_exercise', idx=idx + 1)

    ctx = {
        'patient': patient,
        'item': item,
        'enriched': enriched,
        'exercise_index': idx,
        'total_exercises': len(items),
        'is_last_exercise': idx == len(items) - 1,
        'log_item': log_item,
        'difficulty_choices': SessionLogItem.DIFFICULTY_CHOICES,
    }
    return render(request, 'strength_app/therapist_session_feedback.html', ctx)


def therapist_session_complete(request):
    patient, err = _require_patient(request)
    if err:
        return err

    link = _active_link(patient)
    rx = _latest_published_prescription(link)
    if rx is None:
        return redirect('therapist_session_today')

    state = _get_session_state(request)
    if not state or state.get('rx_id') != rx.id:
        flash.error(request, "Session expired — please start again.")
        return redirect('therapist_session_today')

    log = get_object_or_404(SessionLog, id=state['log_id'])

    if request.method == 'POST':
        try:
            overall_pain = int(request.POST.get('overall_pain', 0))
        except (TypeError, ValueError):
            overall_pain = 0
        overall_pain = max(0, min(10, overall_pain))
        comment = request.POST.get('overall_comment', '').strip()

        log.overall_pain = overall_pain
        log.overall_comment = comment
        log.completed_at = timezone.now()
        log.save()

        _clear_session_state(request)
        return redirect('therapist_session_finished')

    items_count = len(state.get('log_item_ids', []))
    completed = log.items.filter(completed_at__isnull=False).count()

    ctx = {
        'patient': patient,
        'log': log,
        'items_count': items_count,
        'completed': completed,
    }
    return render(request, 'strength_app/therapist_session_complete.html', ctx)


def therapist_session_finished(request):
    patient, err = _require_patient(request)
    if err:
        return err

    link = _active_link(patient)
    last_log = (
        SessionLog.objects
        .filter(link=link, completed_at__isnull=False)
        .order_by('-completed_at')
        .first()
        if link else None
    )

    ctx = {
        'patient': patient,
        'link': link,
        'last_log': last_log,
    }
    return render(request, 'strength_app/therapist_session_finished.html', ctx)


def therapist_session_progress(request):
    patient, err = _require_patient(request)
    if err:
        return err

    link = _active_link(patient)
    completed_qs = (
        SessionLog.objects
        .filter(link=link, completed_at__isnull=False)
        .order_by('-completed_at')
        if link else SessionLog.objects.none()
    )

    total_sessions = completed_qs.count()
    today = date.today()

    # Streak
    streak = 0
    if total_sessions > 0:
        check_date = today
        done_dates = set(completed_qs.values_list('completed_at__date', flat=True))
        while check_date in done_dates:
            streak += 1
            check_date -= timedelta(days=1)

    # This week vs last week
    week_start = today - timedelta(days=6)
    last_week_start = today - timedelta(days=13)
    this_week_logs = completed_qs.filter(completed_at__date__gte=week_start)
    last_week_logs = completed_qs.filter(
        completed_at__date__gte=last_week_start,
        completed_at__date__lt=week_start,
    )
    week_sessions = this_week_logs.count()
    last_week_sessions = last_week_logs.count()

    # Per-exercise pain averages (more granular than overall_pain)
    week_log_ids = list(this_week_logs.values_list('id', flat=True))
    last_week_log_ids = list(last_week_logs.values_list('id', flat=True))
    week_items = SessionLogItem.objects.filter(
        session_log_id__in=week_log_ids, completed_at__isnull=False
    )
    last_week_items = SessionLogItem.objects.filter(
        session_log_id__in=last_week_log_ids, completed_at__isnull=False
    )

    _wap = week_items.filter(pain__isnull=False).aggregate(a=Avg('pain'))['a']
    _lwap = last_week_items.filter(pain__isnull=False).aggregate(a=Avg('pain'))['a']
    week_avg_pain = round(_wap, 1) if _wap is not None else None
    last_week_avg_pain = round(_lwap, 1) if _lwap is not None else None

    pain_trend_label = None
    if week_avg_pain is not None and last_week_avg_pain is not None:
        diff = _wap - _lwap
        pain_trend_label = 'better' if diff < -0.5 else 'worse' if diff > 0.5 else 'same'

    week_exercise_count = week_items.count()

    most_challenging = (
        week_items.filter(pain__isnull=False)
        .values('exercise_name')
        .annotate(avg_pain=Avg('pain'))
        .order_by('-avg_pain')
        .first()
    )
    most_consistent = (
        week_items.values('exercise_name')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
        .first()
    )

    # Compliance % since program start
    compliance_pct = None
    if link and link.program_start:
        days_since = max(1, (today - link.program_start).days + 1)
        compliance_pct = min(100, int(round(100 * total_sessions / days_since)))

    # Next 14-day check-in from program start
    next_checkin = None
    if link and link.program_start:
        days_since = (today - link.program_start).days
        days_to_next = 14 - (days_since % 14)
        next_checkin = today + timedelta(days=(0 if days_to_next == 14 else days_to_next))

    # Latest message sent by therapist to this patient
    latest_therapist_note = (
        TherapistMessage.objects
        .filter(link=link, sender__therapist__isnull=False)
        .order_by('-sent_at')
        .first()
        if link else None
    )

    # Pain trend — last 14 completed sessions with overall_pain
    pain_logs = list(
        completed_qs
        .filter(overall_pain__isnull=False)
        .order_by('completed_at')
        .values('completed_at', 'overall_pain')
    )[-14:]

    ctx = {
        'patient': patient,
        'link': link,
        'total_sessions': total_sessions,
        'streak': streak,
        'pain_logs': pain_logs,
        'week_sessions': week_sessions,
        'last_week_sessions': last_week_sessions,
        'week_avg_pain': week_avg_pain,
        'last_week_avg_pain': last_week_avg_pain,
        'pain_trend_label': pain_trend_label,
        'week_exercise_count': week_exercise_count,
        'most_challenging': most_challenging,
        'most_consistent': most_consistent,
        'compliance_pct': compliance_pct,
        'next_checkin': next_checkin,
        'latest_therapist_note': latest_therapist_note,
    }
    return render(request, 'strength_app/therapist_session_progress.html', ctx)


def therapist_session_profile(request):
    patient, err = _require_patient(request)
    if err:
        return err

    link = _active_link(patient)

    if request.method == 'POST':
        body = request.POST.get('message', '').strip()
        if body and link and patient.user_id:
            from django.contrib.auth.models import User as DjangoUser
            try:
                sender = DjangoUser.objects.get(id=patient.user_id)
                TherapistMessage.objects.create(link=link, sender=sender, body=body)
                flash.success(request, "Message sent to your therapist.")
            except DjangoUser.DoesNotExist:
                pass
        return redirect('therapist_session_profile')

    health_profile = None
    if link:
        try:
            health_profile = link.health_profile
        except Exception:
            pass

    ctx = {
        'patient': patient,
        'link': link,
        'health_profile': health_profile,
    }
    return render(request, 'strength_app/therapist_session_profile.html', ctx)
