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
import logging
from datetime import date, timedelta

from django.contrib import messages as flash
from django.db import transaction
from django.db.models import Avg, Count
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from django.conf import settings
from .models import PatientProfile, PainEvent, RestEvent
from .rate_limiter import rate_limit
from therapist_app.exercise_catalog import EXERCISES_BY_ID
from therapist_app.models import (
    Alert,
    ExerciseSetLog,
    Prescription,
    PrescriptionItem,
    SessionLog,
    SessionLogItem,
    SessionReport,
    TherapistMessage,
    TherapistPatientLink,
)

logger = logging.getLogger(__name__)


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
    from .cv_targets import get_video_mode_exercises
    filmed = set(get_video_mode_exercises())
    items = list(rx.items.all().order_by('order', 'id'))
    enriched = []
    for it in items:
        catalog = EXERCISES_BY_ID.get(it.exercise_id, {})
        v2_key = catalog.get('v2_exercise_key', '')
        enriched.append({
            'item': it,
            'catalog': catalog,
            'name': it.exercise_name or catalog.get('name', it.exercise_id),
            'description': catalog.get('description', ''),
            'equipment': catalog.get('equipment', '—'),
            'video_url': catalog.get('video_url', ''),
            'v2_ghost_supported': bool(catalog.get('v2_ghost_supported', False)),
            'v2_exercise_key': v2_key,
            # Filmed demo exists at static/strength_app/videos/<key>.mp4 —
            # same server-side scan that drives camera-page VIDEO_MODE.
            'local_video': bool(v2_key) and v2_key in filmed,
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


def _generate_report_safely(session_log):
    """R2 trigger wrapper: a report failure must NEVER block the patient's
    completion flow — log it and move on."""
    if session_log is None:
        return
    try:
        from .report_builder import generate_session_report
        generate_session_report(session_log)
    except Exception:
        logger.exception('session report generation failed (session_log=%s)',
                         getattr(session_log, 'id', None))


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
@transaction.atomic
def therapist_session_start(request):
    # B-T2 (2026-07 exam): SessionLog + its SessionLogItems are one unit —
    # a partial failure left an orphan "abandoned" session in the
    # therapist's history and a retry created a second log.
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

    # R1c: exercise start = page entry, stamped server-side (first GET wins).
    log_ids = state.get('log_item_ids') or []
    if 0 <= idx < len(log_ids):
        SessionLogItem.objects.filter(
            id=log_ids[idx], started_at__isnull=True,
        ).update(started_at=timezone.now())

    enriched = items[idx]
    item = enriched['item']
    is_last = (idx == len(items) - 1)

    # If the patient's exercise is V2-supported, render the existing
    # ghost-coach template with library_mode=True. The post-save redirect
    # is overridden via library_return_url so we land on the feedback page.
    if enriched['v2_ghost_supported'] and enriched['v2_exercise_key']:
        return _render_v2_ghost(request, patient, enriched, idx, len(items), is_last)

    # Otherwise render the simple (no-camera) page.
    # 2026-07 Part 4C: count-along pacer for the two PERMANENTLY guided
    # exercises (camera cannot honestly track them — catalog descriptions).
    # 'interval' = one count every 2 s (ankle pumps); 'squeeze_cycle' =
    # 5 s squeeze / 3 s relax per rep (prone glute squeeze). Purely visual
    # pacing — it never logs anything; set tracking stays self-reported.
    pacer_mode = {
        'ex_ankle_pumps': 'interval',
        'ex_prone_glute_squeeze': 'squeeze_cycle',
    }.get(item.exercise_id, '')

    ctx = {
        'patient': patient,
        'item': item,
        'enriched': enriched,
        'exercise_index': idx,
        'total_exercises': len(items),
        'is_last_exercise': is_last,
        'pacer_mode': pacer_mode,
        'feedback_url': reverse('therapist_session_feedback', args=[idx]),
        'report_pain_url': reverse('therapist_session_report_pain', args=[idx]),
        'set_log_url': reverse('therapist_session_set_log', args=[idx]),
        'rest_event_url': reverse('therapist_session_rest_event', args=[idx]),
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
    # Normalise en/em dashes to real hyphens so dash-separated tempos still split.
    # Parts stay as strings; the template quotes + parseInt's them, so no tempo value
    # (numbers, '—', 'Hold', …) can ever emit invalid inline JS.
    # NB: keep these as STRINGS, never ints — the tempo *display* cells render them
    # through Django's `|default:N` filter (`value or arg`), and an int 0 is falsy so
    # it would be swallowed by the default (e.g. 4-0-1-0 would show 4-1-1-0). '0' is truthy.
    tempo_parts = tempo.replace('–', '-').replace('—', '-').split('-')
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
        'report_pain_url':    reverse('therapist_session_report_pain', args=[idx]),
        # R1: capture endpoints (per-set batch POST + rest/pause events).
        'set_log_url':        reverse('therapist_session_set_log', args=[idx]),
        'rest_event_url':     reverse('therapist_session_rest_event', args=[idx]),
        # C2: the therapist's per-exercise cue, shown as escaped HTML on the
        # camera screen (never injected into an inline JS block).
        'therapist_note':     item.notes,
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
    # D3: the log-item list was frozen at session start; a same-week
    # republish can grow the CURRENT items past it — guard like the
    # sibling endpoints instead of a bare subscript (IndexError/500).
    log_ids = state.get('log_item_ids') or []
    if idx >= len(log_ids):
        flash.error(request, "Session expired — please start again.")
        return redirect('therapist_session_today')
    log_item = get_object_or_404(SessionLogItem, id=log_ids[idx])

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


@transaction.atomic
def _record_pain(link, patient, *, exercise_id, exercise_name, pain_type,
                 severity, set_number, threshold, outcome, rep_number=None):
    """Phase 2: log a PainEvent, post a SYSTEM message to the therapist chat
    (every time), and raise an Alert (only on skip/pause). Returns the body.
    B-T3 (2026-07 exam): atomic — the event and its therapist notification
    live or die together (a retry after partial failure duplicated
    PainEvents in the immutable pain record)."""
    when = timezone.localtime().strftime('%d %b %Y at %I:%M %p')
    where = f"set {set_number}" if set_number else "a set"
    ptype = (pain_type or '').strip()
    ptype_txt = ptype or 'unspecified'
    name = patient.name or 'Patient'
    if outcome == 'session_paused':
        body = (f"⚠ HIGH PAIN — {name} reported {ptype_txt} pain {severity}/10 on "
                f"{exercise_name} ({where}) on {when}. Session paused.")
    elif outcome == 'exercise_skipped':
        body = (f"{name} reported {ptype_txt} pain {severity}/10 on {exercise_name} "
                f"({where}) on {when}. Above their usual level ({threshold}) — "
                f"exercise skipped, session continued.")
    else:
        body = (f"{name} reported {ptype_txt} pain {severity}/10 on {exercise_name} "
                f"({where}) on {when}. Below the stop threshold ({threshold}) — continued.")

    PainEvent.objects.create(
        patient=patient, exercise_id=exercise_id or '', exercise_name=exercise_name or '',
        set_number=set_number or None, rep_number=rep_number or None,
        pain_type=ptype, pain_severity=severity,
        threshold_applied=threshold, outcome=outcome,
    )
    # Tiers: <= usual pain -> report only (PainEvent already saved, no ping);
    # above usual (skip) -> system message; >= 8 (pause) -> message + alert.
    if outcome in ('exercise_skipped', 'session_paused'):
        TherapistMessage.objects.create(link=link, sender=None, is_system=True, body=body)
    if outcome == 'session_paused':
        # F1 (deploy review): dedupe — an unreviewed pain Alert for the same
        # exercise within the last 10 minutes already has the therapist's
        # attention; suppress ONLY the duplicate Alert row (the PainEvent and
        # system message above are always recorded) to prevent inbox flooding
        # and alarm fatigue.
        duplicate = Alert.objects.filter(
            link=link,
            alert_type='pain',
            is_reviewed=False,
            created_at__gte=timezone.now() - timedelta(minutes=10),
            message__contains=exercise_name or '',
        ).exists() if exercise_name else False
        if not duplicate:
            Alert.objects.create(link=link, alert_type='pain', message=body)
    return body


# F1 (deploy review): 15/min allows every legitimate use (a few reports per
# exercise) while killing loops that would flood PainEvents/messages/alerts.
@rate_limit(max_attempts=15, window_seconds=60, key_prefix='report_pain')
@require_POST
def therapist_session_report_pain(request, idx):
    """Phase 2: real-time pain report from the exercise screen. Applies the
    two-tier rule and tells the client to continue / skip the exercise / pause."""
    patient, err = _require_patient(request)
    if err:
        return JsonResponse({'error': 'auth'}, status=401)

    link = _active_link(patient)
    rx = _latest_published_prescription(link)
    if rx is None or link is None:
        return JsonResponse({'error': 'no_active_prescription'}, status=400)

    state = _get_session_state(request)
    if not state or state.get('rx_id') != rx.id:
        return JsonResponse({'error': 'session_expired'}, status=400)

    items = _enriched_items(rx)
    if idx < 0 or idx >= len(items):
        return JsonResponse({'error': 'bad_index'}, status=400)

    try:
        data = json.loads(request.body or '{}')
    except ValueError:
        data = {}
    try:
        severity = max(0, min(10, int(data.get('severity'))))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'severity_required'}, status=400)
    pain_type = str(data.get('pain_type') or '')[:20]
    try:
        # A1: clamp like every sibling field — an out-of-range value would
        # 500 on Postgres (PositiveSmallIntegerField), not on dev SQLite.
        set_number = max(1, min(30, int(data.get('set_number'))))
    except (TypeError, ValueError):
        set_number = None
    # R1d: camera exercises pin pain to the rep the modal opened on;
    # guided sends nothing and rep_number stays null (honest set-level).
    try:
        rep_number = max(1, min(200, int(data.get('rep_number'))))
    except (TypeError, ValueError):
        rep_number = None

    item = items[idx]['item']
    # D2: `is not None`, not `or` — a therapist-set 0 means "skip above ANY
    # pain" (the most cautious setting) and must not collapse to the default.
    threshold = (item.pain_stop_threshold
                 if item.pain_stop_threshold is not None
                 else getattr(settings, 'PAIN_STOP_THRESHOLD_DEFAULT', 5))
    pause_at = getattr(settings, 'PAIN_SESSION_PAUSE_THRESHOLD', 8)

    if severity >= pause_at:
        outcome = 'session_paused'
    elif severity > threshold:
        # threshold = the patient's USUAL pain on this exercise; skip only ABOVE it
        outcome = 'exercise_skipped'
    else:
        outcome = 'continued'

    if outcome in ('exercise_skipped', 'session_paused'):
        log_ids = state.get('log_item_ids') or []
        if idx < len(log_ids):
            li = SessionLogItem.objects.filter(id=log_ids[idx]).first()
            if li:
                li.pain = severity
                li.sets_completed = set_number or li.sets_completed
                li.completed_at = timezone.now()
                li.save()

    _record_pain(link, patient,
                 exercise_id=getattr(item, 'exercise_id', ''),
                 exercise_name=item.exercise_name, pain_type=pain_type,
                 severity=severity, set_number=set_number, threshold=threshold,
                 outcome=outcome, rep_number=rep_number)

    # G1b: the patient-facing guidance is written HERE, mirroring
    # _record_pain's tiers, so the exercise screen and the therapist chat
    # can never disagree. (Clinical wording — flag for the physio mentor.)
    if outcome == 'session_paused':
        # R2 trigger (b): an aborted session is the report a therapist most
        # needs — generate it now, synchronously, never blocking the reply.
        _generate_report_safely(
            SessionLog.objects.filter(id=state.get('log_id')).first())
        return JsonResponse({
            'action': 'pause',
            'next_url': reverse('v1_pain_stop'),
            'guidance': ("Stop for today. Pain this severe — whatever the "
                         "type — is a signal to rest. Your physiotherapist "
                         "has been alerted and will follow up."),
        })
    if outcome == 'exercise_skipped':
        nxt = (reverse('therapist_session_complete') if idx + 1 >= len(items)
               else reverse('therapist_session_exercise', args=[idx + 1]))
        return JsonResponse({
            'action': 'skip',
            'next_url': nxt,
            'guidance': ("That's above your usual level on this exercise, so "
                         "we're skipping the rest of it. Your physiotherapist "
                         "has been notified — the session continues with the "
                         "next exercise."),
        })
    return JsonResponse({
        'action': 'continue',
        'guidance': ("Noted and shared with your physiotherapist. This is "
                     "within your usual range for this exercise — carry on, "
                     "and report again if it climbs."),
    })


# ---------------------------------------------------------------------------
# R1: capture endpoints (per-set logs + rest/pause events)
# ---------------------------------------------------------------------------

def _capture_context(request, idx):
    """Shared auth/state resolution for the R1 capture endpoints. Returns
    (patient, link, state, item, log) or (None, ..., JsonResponse error)."""
    patient, err = _require_patient(request)
    if err:
        return None, None, None, None, JsonResponse({'error': 'auth'}, status=401)
    link = _active_link(patient)
    rx = _latest_published_prescription(link)
    if rx is None or link is None:
        return None, None, None, None, JsonResponse(
            {'error': 'no_active_prescription'}, status=400)
    state = _get_session_state(request)
    if not state or state.get('rx_id') != rx.id:
        return None, None, None, None, JsonResponse(
            {'error': 'session_expired'}, status=400)
    items = _enriched_items(rx)
    if idx < 0 or idx >= len(items):
        return None, None, None, None, JsonResponse(
            {'error': 'bad_index'}, status=400)
    log = SessionLog.objects.filter(id=state.get('log_id')).first()
    if log is None:
        return None, None, None, None, JsonResponse(
            {'error': 'session_expired'}, status=400)
    return patient, link, state, items[idx]['item'], log


def _num(value, lo, hi):
    """Clamp a client-supplied number into [lo, hi]; None when unusable."""
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return None


def _sanitize_reps(raw):
    """R1a: bound and clamp a client per-rep array. Returns None when the
    payload isn't a list at all (caller logs + stores []); individually
    malformed items are skipped. Never raises."""
    if not isinstance(raw, list):
        return None
    out = []
    for entry in raw[:60]:
        if not isinstance(entry, dict):
            continue
        rep = {
            'rep_n': int(_num(entry.get('rep_n'), 0, 200) or 0),
            'partial': bool(entry.get('partial', False)),
        }
        form_pct = _num(entry.get('form_pct'), 0, 100)
        if form_pct is not None:
            rep['form_pct'] = round(form_pct, 1)
        bottom = _num(entry.get('bottom_angle'), 0, 360)
        if bottom is not None:
            rep['bottom_angle'] = round(bottom, 1)
        phase_ms = entry.get('phase_ms')
        if isinstance(phase_ms, dict):
            clean = {}
            for key in ('ecc', 'hold', 'con'):
                ms = _num(phase_ms.get(key), 0, 120000)
                if ms is not None:
                    clean[key] = int(ms)
            if clean:
                rep['phase_ms'] = clean
        phases_raw = entry.get('phases_raw')
        if isinstance(phases_raw, list):
            rep['phases_raw'] = [
                {'name': str(p.get('name', ''))[:30],
                 'ms': int(_num(p.get('ms'), 0, 120000) or 0)}
                for p in phases_raw[:12] if isinstance(p, dict)
            ]
        cues = entry.get('cues')
        if isinstance(cues, list):
            rep['cues'] = [
                {'cue_id': str(c.get('cue_id', ''))[:40],
                 'corrected': bool(c.get('corrected', False))}
                for c in cues[:12] if isinstance(c, dict) and c.get('cue_id')
            ]
        out.append(rep)
    return out


@rate_limit(max_attempts=60, window_seconds=60, key_prefix='set_log')
@require_POST
def therapist_session_set_log(request, idx):
    """R1a/R1c/R1e: persist one performed set (camera batch or guided tap).
    Idempotent on (session_log, exercise, set_number) so a client retry
    never duplicates a set."""
    patient, link, state, item, log = _capture_context(request, idx)
    if patient is None:
        return log  # the error JsonResponse

    try:
        data = json.loads(request.body or '{}')
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        return JsonResponse({'error': 'malformed'}, status=400)

    mode = data.get('mode')
    if mode not in ('camera', 'guided'):
        mode = 'guided'
    set_number = int(_num(data.get('set_number'), 1, 30) or 1)
    reps_count = int(_num(data.get('reps_count'), 0, 200) or 0)
    hold_raw = _num(data.get('hold_seconds'), 0, 3600)
    hold_seconds = int(hold_raw) if hold_raw else None
    duration_ms = int(_num(data.get('duration_ms'), 0, 3 * 3600 * 1000) or 0)
    demo_viewed = bool(data.get('demo_viewed', False))

    reps = _sanitize_reps(data.get('reps')) if 'reps' in data else []
    if reps is None:
        logger.warning('set_log: malformed reps array dropped '
                       '(patient=%s exercise=%s set=%s)',
                       patient.patient_id, item.exercise_id, set_number)
        reps = []

    now = timezone.now()
    ExerciseSetLog.objects.update_or_create(
        session_log=log,
        exercise_id=item.exercise_id,
        set_number=set_number,
        defaults={
            'link': link,
            'exercise_name': item.exercise_name,
            'mode': mode,
            'reps_count': reps_count,
            'hold_seconds': hold_seconds,
            'reps_json': reps,
            'demo_viewed': demo_viewed,
            'started_at': now - timedelta(milliseconds=duration_ms),
            'ended_at': now,
        },
    )
    return JsonResponse({'ok': True})


@rate_limit(max_attempts=60, window_seconds=60, key_prefix='rest_event')
@require_POST
def therapist_session_rest_event(request, idx):
    """R1b: rest extension (+30s), rest cut short, or session pause."""
    patient, link, state, item, log = _capture_context(request, idx)
    if patient is None:
        return log  # the error JsonResponse

    try:
        data = json.loads(request.body or '{}')
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        return JsonResponse({'error': 'malformed'}, status=400)

    kind = data.get('kind')
    if kind not in ('extension', 'pause', 'skip'):
        return JsonResponse({'error': 'bad_kind'}, status=400)
    set_raw = _num(data.get('set_number'), 1, 30)
    set_number = int(set_raw) if set_raw else None

    if kind == 'pause':
        seconds = int(_num(data.get('seconds'), 0, 3 * 3600) or 0)
        context, cut_short = 'pause', False
    elif kind == 'extension':
        seconds = int(_num(data.get('seconds'), 0, 600) or 0)
        context, cut_short = 'between_sets', False
    else:  # skip — rest cut short, no extra seconds
        seconds = 0
        context, cut_short = 'between_sets', True

    RestEvent.objects.create(
        patient=patient,
        session_log=log,
        exercise_id=item.exercise_id,
        exercise_name=item.exercise_name,
        set_number=set_number,
        context=context,
        extra_seconds=seconds,
        cut_short=cut_short,
    )
    return JsonResponse({'ok': True})


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

        # R2 trigger (a): the session just completed — build its report.
        _generate_report_safely(log)

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

    # R2 trigger (c): idempotent safety net — a completed session that
    # somehow missed generation gets its report here.
    _generate_report_safely(last_log)

    ctx = {
        'patient': patient,
        'link': link,
        'last_log': last_log,
        # R3: link straight to today's report when it exists.
        'last_report': (SessionReport.objects.filter(session_log=last_log).first()
                        if last_log else None),
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
        # R3: session history entries link to their rendered reports.
        'recent_reports': list(
            SessionReport.objects.filter(patient=patient)
            .order_by('-report_date', '-created_at')[:10]),
    }
    return render(request, 'strength_app/therapist_session_progress.html', ctx)


def therapist_session_report_view(request, report_id):
    """R3: the patient reads their OWN session report — the identical
    document the therapist sees (locked decision 1). Ownership: the report
    must belong to the logged-in patient, 404 otherwise (IDOR matrix)."""
    patient, err = _require_patient(request)
    if err:
        return err
    report_obj = get_object_or_404(SessionReport, id=report_id, patient=patient)
    return render(request, 'strength_app/therapist_session_report.html', {
        'patient': patient,
        'report_obj': report_obj,
        'report': report_obj.report_json,
    })


def therapist_session_report_pdf(request, report_id):
    """2026-07 burn P1: stream the immutable report as a PDF. Same ownership
    guard as therapist_session_report_view (patient's own report or 404) —
    the document is a render of report_json, identical to the therapist's."""
    patient, err = _require_patient(request)
    if err:
        return err
    report_obj = get_object_or_404(SessionReport, id=report_id, patient=patient)

    from .report_pdf import generate_report_pdf, pdf_filename
    buffer = generate_report_pdf(report_obj.report_json or {})
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="{pdf_filename(report_obj)}"')
    return response


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
