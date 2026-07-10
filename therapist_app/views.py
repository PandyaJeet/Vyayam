"""
Therapist console views — desktop-first, server-rendered.

Tab routing on the patient detail page is via ?tab=<key> rather than separate
URLs, so the Back button + analytics see one canonical patient URL.
"""

import json
import logging
import re
import secrets
from datetime import timedelta

from django.contrib import messages as flash
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.db import transaction

logger = logging.getLogger(__name__)
from django.http import FileResponse, HttpResponseBadRequest, JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from strength_app.rate_limiter import rate_limit

from .exercise_catalog import EXERCISES, EXERCISES_BY_ID, PATTERNS
from .models import (
    Prescription,
    PrescriptionItem,
    ProgressReport,
    SessionLog,
    SessionLogItem,
    TherapistMessage,
    TherapistPatientHealthProfile,
    TherapistPatientLink,
)
from .permissions import get_linked_patient_or_404, therapist_required


def _safe_int(value, default, lo, hi):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@rate_limit(max_attempts=5, window_seconds=300, key_prefix='therapist_login')
def therapist_login(request):
    """Therapist login form. Distinct from the patient PWA login (phone-based)."""
    if request.user.is_authenticated and hasattr(request.user, 'therapist'):
        return redirect('therapist_dashboard')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None and hasattr(user, 'therapist'):
            request.session.flush()
            login(request, user)
            return redirect('therapist_dashboard')
        if user is not None and not hasattr(user, 'therapist'):
            error = "This account is not registered as a therapist."
        else:
            error = "Invalid username or password."

    return render(request, 'therapist_app/login.html', {'error': error})


def therapist_logout(request):
    logout(request)
    return redirect('therapist_login')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _metrics_from_rows(has_profile, sessions, pain_events, today,
                       days_window=14):
    """Pure metric math per HANDOFF §3 (PatientCard) over pre-fetched rows —
    shared by the single-link path and the bulk path (B-N1). D8's pain trend
    from PainEvent (the locked pain source) is preserved."""
    sparkline_7d = [0] * 7
    pain_trend_7d = [0, 0, 0, 0, 0, 0, 0]
    compliance_pct = 0

    if has_profile:
        completed = sum(1 for s in sessions if s.total_exercises_completed > 0)
        prescribed = max(days_window, completed)  # rough heuristic; refined later
        compliance_pct = int(round((completed / prescribed) * 100)) if prescribed else 0

        for s in sessions:
            day_offset = (today - s.session_date.date()).days
            if 0 <= day_offset < 7 and s.total_exercises_completed > 0:
                sparkline_7d[6 - day_offset] = 1

        for event in pain_events:
            day_offset = (today - timezone.localtime(event.created_at).date()).days
            if 0 <= day_offset < 7:
                slot = 6 - day_offset
                pain_trend_7d[slot] = max(pain_trend_7d[slot], event.pain_severity)

    flags = []
    if compliance_pct and compliance_pct < 60:
        flags.append("Missed sessions")
    if any(p > 5 for p in pain_trend_7d):
        flags.append("Pain >5 last week")

    if compliance_pct >= 80:
        status_tone = 'green'
    elif compliance_pct >= 60:
        status_tone = 'yellow'
    elif compliance_pct > 0:
        status_tone = 'red'
    else:
        status_tone = 'neutral'

    return {
        'compliance_pct': compliance_pct,
        'sparkline_7d': sparkline_7d,
        'pain_trend_7d': pain_trend_7d,
        'flags': flags,
        'status_tone': status_tone,
        'last_session_label': '—',
    }


def _compute_link_metrics(link):
    """Single-link metrics (patient_detail). List pages use
    _bulk_link_metrics — keep the row filters in lockstep."""
    today = timezone.now().date()
    days_window = 14

    try:
        from strength_app.models import PatientProfile
        profile = None
        if link.patient_id:
            profile = PatientProfile.objects.filter(user_id=link.patient_id).first()
    except Exception:
        profile = None

    sessions, pain_events = [], []
    if profile is not None:
        from strength_app.models import PainEvent, WorkoutSession
        sessions = list(WorkoutSession.objects.filter(
            patient=profile,
            session_date__date__gte=today - timedelta(days=days_window),
        ))
        pain_events = list(PainEvent.objects.filter(
            patient=profile,
            created_at__date__gte=today - timedelta(days=6),
        ).only('created_at', 'pain_severity'))

    return _metrics_from_rows(profile is not None, sessions, pain_events,
                              today, days_window)


def _bulk_link_metrics(links):
    """B-N1/B-N2 (2026-07 exam): metrics for every card in 3 flat queries
    (profiles, sessions, pain events) instead of ~4 per link. Returns
    {link.id: metrics}."""
    today = timezone.now().date()
    days_window = 14

    from strength_app.models import PainEvent, PatientProfile, WorkoutSession
    user_ids = [l.patient_id for l in links if l.patient_id]
    profiles = {p.user_id: p
                for p in PatientProfile.objects.filter(user_id__in=user_ids)}

    sessions_by_profile = {}
    for s in WorkoutSession.objects.filter(
            patient__in=profiles.values(),
            session_date__date__gte=today - timedelta(days=days_window),
    ).only('patient_id', 'session_date', 'total_exercises_completed'):
        sessions_by_profile.setdefault(s.patient_id, []).append(s)

    pain_by_profile = {}
    for e in PainEvent.objects.filter(
            patient__in=profiles.values(),
            created_at__date__gte=today - timedelta(days=6),
    ).only('patient_id', 'created_at', 'pain_severity'):
        pain_by_profile.setdefault(e.patient_id, []).append(e)

    out = {}
    for link in links:
        profile = profiles.get(link.patient_id) if link.patient_id else None
        out[link.id] = _metrics_from_rows(
            profile is not None,
            sessions_by_profile.get(profile.pk, []) if profile else [],
            pain_by_profile.get(profile.pk, []) if profile else [],
            today, days_window)
    return out


def _seed_demo_metrics(link):
    """The dashboard prototype shows specific metrics per patient. Until the
    strength_app session pipeline writes real data here, we hand-roll the
    metrics from the seed-fixture payload stored on the link.notes field
    (which we set in seed_therapist_demo)."""
    try:
        seed = json.loads(link.notes) if link.notes else {}
    except (ValueError, TypeError):
        seed = {}
    return seed.get('metrics') or {}


def _link_card(link, metrics=None):
    seed = _seed_demo_metrics(link)
    if seed:
        compliance = seed.get('compliance', 0)
        sparkline = seed.get('sparkline', [0] * 7)
        pain = seed.get('pain', [])
        flags = seed.get('flags', [])
        last_session = seed.get('last_session', '—')
    else:
        m = metrics if metrics is not None else _compute_link_metrics(link)
        compliance = m['compliance_pct']
        sparkline = m['sparkline_7d']
        pain = m['pain_trend_7d']
        flags = m['flags']
        last_session = m['last_session_label']

    if compliance >= 80:
        tone = 'green'
    elif compliance >= 60:
        tone = 'yellow'
    elif compliance > 0:
        tone = 'red'
    else:
        tone = 'neutral'

    return {
        'link': link,
        'id': str(link.id),
        'name': link.display_name,
        'initials': link.initials,
        'age': link.age,
        'sex': link.sex,
        'location': link.location,
        'condition': link.primary_condition,
        'condition_tone': link.condition_tone,
        'pending': link.status == 'pending',
        'week': link.current_week,
        'total_weeks': link.total_weeks,
        'compliance': compliance,
        'sparkline': sparkline,
        'pain_trend': pain,
        'flags': flags,
        'last_session': last_session,
        'status_tone': tone,
        'next_session': seed.get('next_session', '—'),
    }


def _build_progress_charts(link):
    """Builds the three Progress-tab datasets (last 14 days):
       1. Pain trend — one point per day with at least one logged pain reading
       2. Compliance — distinct days completed vs window size for 3 periods
       3. Difficulty distribution — counts across SessionLogItem.difficulty
    """
    today = timezone.now().date()
    window_days = 14
    window_start = today - timedelta(days=window_days - 1)

    logs_14d = list(
        link.session_logs
        .filter(started_at__date__gte=window_start)
        .prefetch_related('items')
    )

    # --- Chart 1: pain trend
    pain_by_day = {}
    for log in logs_14d:
        if log.overall_pain is None:
            continue
        d = log.started_at.date()
        pain_by_day.setdefault(d, []).append(log.overall_pain)

    pain_labels = []
    pain_values = []
    for offset in range(window_days):
        d = window_start + timedelta(days=offset)
        pain_labels.append(d.strftime('%b %-d'))
        if d in pain_by_day:
            vals = pain_by_day[d]
            pain_values.append(round(sum(vals) / len(vals), 1))
        else:
            pain_values.append(None)

    # --- Chart 2: compliance buckets
    logs_30d = list(
        link.session_logs
        .filter(started_at__date__gte=today - timedelta(days=29))
        .only('started_at', 'completed_at')
    )

    def _days_done(start, end):
        return len({
            l.started_at.date()
            for l in logs_30d
            if l.completed_at is not None and start <= l.started_at.date() <= end
        })

    this_week = _days_done(today - timedelta(days=6), today)
    last_week = _days_done(today - timedelta(days=13), today - timedelta(days=7))
    this_month = _days_done(today - timedelta(days=29), today)

    compliance = [
        {'label': 'This week', 'completed': this_week, 'total': 7},
        {'label': 'Last week', 'completed': last_week, 'total': 7},
        {'label': 'This month', 'completed': this_month, 'total': 30},
    ]
    for row in compliance:
        row['pct'] = int(round(100.0 * row['completed'] / row['total'])) if row['total'] else 0

    # --- Chart 3: difficulty distribution
    difficulty_counts = {'easy': 0, 'right': 0, 'hard': 0, 'too_hard': 0}
    for log in logs_14d:
        for item in log.items.all():
            if item.difficulty in difficulty_counts:
                difficulty_counts[item.difficulty] += 1
    total_items = sum(difficulty_counts.values())

    return {
        'has_data': bool(logs_14d),
        'pain': {'labels': pain_labels, 'values': pain_values},
        'compliance': compliance,
        'difficulty': {'counts': difficulty_counts, 'total': total_items},
    }


# ---------------------------------------------------------------------------
# Top-level pages
# ---------------------------------------------------------------------------

@therapist_required
def dashboard(request):
    therapist = request.user.therapist
    links = list(
        therapist.patient_links
        .exclude(status='archived')
        .order_by('status', 'full_name')
    )
    metrics = _bulk_link_metrics(links)
    cards = [_link_card(link, metrics.get(link.id)) for link in links]

    # R2-T1: triage ordering — "who do I need to look at?" answered on
    # screen one. Unreviewed alerts (sharp pain / red-flag changes) first,
    # then red compliance, then flagged, then everyone else.
    from .models import Alert
    alert_counts = {}
    for row in (Alert.objects
                .filter(link__in=links, is_reviewed=False)
                .values('link_id')):
        alert_counts[row['link_id']] = alert_counts.get(row['link_id'], 0) + 1
    for c in cards:
        c['alert_count'] = alert_counts.get(c['link'].id, 0)
    cards.sort(key=lambda c: (
        -c['alert_count'],
        0 if c['status_tone'] == 'red' else 1,
        0 if c['flags'] else 1,
        c['name'],
    ))

    active = [c for c in cards if not c['pending']]
    flagged = [c for c in active if c['flags']]
    today_count = sum(1 for c in active if c['last_session'] == 'Today')
    unreviewed_alerts = sum(alert_counts.values())

    ctx = {
        'therapist': therapist,
        'cards': cards,
        'active_count': len(active),
        'flagged_count': len(flagged),
        'today_count': today_count,
        'unreviewed_alerts': unreviewed_alerts,  # R2-T2 badge
        'reports_due': 2,  # placeholder until we wire real report scheduling
        'active_section': 'dashboard',
    }
    return render(request, 'therapist_app/dashboard.html', ctx)


# ============================================================================
# R2-T2: ALERTS INBOX
# ============================================================================

@therapist_required
def alerts_inbox(request):
    """Global list of patient alerts, unreviewed first."""
    therapist = request.user.therapist
    from .models import Alert
    alerts = (
        Alert.objects
        .filter(link__therapist=therapist)
        .select_related('link')[:200]
    )
    return render(request, 'therapist_app/alerts_inbox.html', {
        'therapist': therapist,
        'alerts': alerts,
        'unreviewed_count': sum(1 for a in alerts if not a.is_reviewed),
        'active_section': 'alerts',
    })


@therapist_required
def session_report_detail(request, link_id, report_id):
    """R3: render one immutable session report for the therapist. Ownership
    via the cross-therapist firewall + link-scoped report lookup (IDOR)."""
    link = get_linked_patient_or_404(request.user.therapist, link_id)
    from .models import SessionReport
    report_obj = get_object_or_404(SessionReport, id=report_id, link=link)
    return render(request, 'therapist_app/session_report_detail.html', {
        'therapist': request.user.therapist,
        'link': link,
        'report_obj': report_obj,
        'report': report_obj.report_json,
        'active_section': 'patients',
    })


@therapist_required
@require_POST
def alert_mark_reviewed(request, alert_id):
    from .models import Alert
    alert = Alert.objects.filter(
        pk=alert_id, link__therapist=request.user.therapist
    ).first()
    if alert is None:
        raise Http404
    alert.is_reviewed = True
    alert.reviewed_at = timezone.now()
    alert.save(update_fields=['is_reviewed', 'reviewed_at'])
    return redirect(request.POST.get('next') or '/therapist/alerts/')


# ============================================================================
# R2-T3: COPY LAST WEEK'S PROGRAM
# ============================================================================

@therapist_required
@require_POST
@transaction.atomic
def copy_previous_week(request, link_id):
    """Clone the most recent week's prescription into a new draft for the
    next week — the single biggest time-saver in any prescription tool.
    B-T4 (2026-07 exam): atomic like its save_program/save_onboarding
    siblings — no half-copied draft week on failure."""
    therapist = request.user.therapist
    link = get_linked_patient_or_404(therapist, link_id)

    source = link.prescriptions.order_by('-week_number').first()
    if source is None or not source.items.exists():
        flash.error(request, "Nothing to copy yet — build this patient's first week in the program tab.")
        return redirect(f"/therapist/patient/{link.id}/?tab=program")

    target_week = source.week_number + 1
    target, created = Prescription.objects.get_or_create(
        link=link, week_number=target_week,
    )
    if target.items.exists():
        flash.error(request, f"Week {target_week} already has exercises — edit it directly instead of overwriting.")
        return redirect(f"/therapist/patient/{link.id}/?tab=program")

    for item in source.items.all():
        PrescriptionItem.objects.create(
            prescription=target, order=item.order,
            exercise_id=item.exercise_id, exercise_name=item.exercise_name,
            movement_pattern=item.movement_pattern,
            sets=item.sets, reps=item.reps, load=item.load,
            rest_seconds=item.rest_seconds, tempo=item.tempo, notes=item.notes,
            pain_stop_threshold=item.pain_stop_threshold,
        )
    # new week starts as an unpublished draft
    target.published_at = None
    target.notes_for_patient = source.notes_for_patient
    target.save(update_fields=['published_at', 'notes_for_patient'])

    flash.success(request, f"Copied week {source.week_number} into a week {target_week} draft — review and publish.")
    return redirect(f"/therapist/patient/{link.id}/?tab=program")


# ============================================================================
# R2-T7: VISIT NOTES
# ============================================================================

@therapist_required
@require_POST
def add_visit_note(request, link_id):
    therapist = request.user.therapist
    link = get_linked_patient_or_404(therapist, link_id)
    note = (request.POST.get('note') or '').strip()
    if not note:
        flash.error(request, 'Note cannot be empty.')
    else:
        from .models import VisitNote
        VisitNote.objects.create(link=link, note=note[:5000])
        flash.success(request, 'Note saved.')
    return redirect(f"/therapist/patient/{link.id}/?tab=notes")


@therapist_required
def patient_list(request):
    therapist = request.user.therapist
    filter_kind = request.GET.get('filter', 'all')
    q = request.GET.get('q', '').strip()

    links = list(therapist.patient_links.exclude(status='archived').order_by('-invited_at'))
    # B-N2 (2026-07 exam): cards computed ONCE (was three times — the counts
    # comprehensions re-ran every card's queries and threw two passes away).
    metrics = _bulk_link_metrics(links)
    all_cards = [_link_card(link, metrics.get(link.id)) for link in links]

    counts = {
        'all': len(links),
        'active': sum(1 for l in links if l.status == 'active'),
        'pending': sum(1 for l in links if l.status == 'pending'),
        'flagged': sum(1 for c in all_cards if c['flags']),
    }

    cards = all_cards
    if filter_kind == 'active':
        cards = [c for c in cards if not c['pending']]
    elif filter_kind == 'pending':
        cards = [c for c in cards if c['pending']]
    elif filter_kind == 'flagged':
        cards = [c for c in cards if c['flags']]

    if q:
        ql = q.lower()
        cards = [c for c in cards if ql in (c['name'] or '').lower()]

    ctx = {
        'therapist': therapist,
        'cards': cards,
        'filter_kind': filter_kind,
        'q': q,
        'counts': counts,
        'active_section': 'patients',
    }
    return render(request, 'therapist_app/patient_list.html', ctx)


@therapist_required
def library(request):
    therapist = request.user.therapist
    pattern = request.GET.get('pattern', 'All')
    if pattern == 'All':
        visible = EXERCISES
    else:
        visible = [e for e in EXERCISES if e['movement_pattern'] == pattern]
    ctx = {
        'therapist': therapist,
        'patterns': PATTERNS,
        'pattern': pattern,
        'exercises': visible,
        'total_count': len(EXERCISES),
        'active_section': 'library',
    }
    return render(request, 'therapist_app/library.html', ctx)


@therapist_required
def reports(request):
    therapist = request.user.therapist
    # B-P1 (2026-07 exam): newest 100 — reports are weekly, so this is
    # years of history; Paginator when someone actually hits the bound.
    reports_qs = (
        ProgressReport.objects
        .filter(link__therapist=therapist)
        .select_related('link')
        .order_by('-created_at')[:100]
    )
    ctx = {
        'therapist': therapist,
        'reports': reports_qs,
        'active_section': 'reports',
    }
    return render(request, 'therapist_app/reports.html', ctx)


@therapist_required
def settings_page(request):
    therapist = request.user.therapist
    active_seats = therapist.active_link_count
    ctx = {
        'therapist': therapist,
        'active_seats': active_seats,
        'active_section': 'settings',
    }
    return render(request, 'therapist_app/settings.html', ctx)


# ---------------------------------------------------------------------------
# Invite flow (dev-mode: inline form + simulated accept)
# ---------------------------------------------------------------------------

@therapist_required
@require_POST
def invite_patient(request):
    therapist = request.user.therapist
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    phone_raw = request.POST.get('phone', '').strip()
    phone = re.sub(r'[^0-9]', '', phone_raw)
    if not (10 <= len(phone) <= 15):
        phone = ''
    condition = request.POST.get('primary_condition', '').strip()
    age_raw = request.POST.get('age', '').strip()
    sex = request.POST.get('sex', '').strip()

    if not name:
        flash.error(request, "Patient name is required.")
        return redirect('therapist_dashboard')
    if not email and not phone:
        flash.error(request, "Email or mobile number is required.")
        return redirect('therapist_dashboard')

    if therapist.active_link_count >= therapist.seat_limit:
        flash.error(request, f"Seat limit reached ({therapist.seat_limit}).")
        return redirect('therapist_dashboard')

    # Django username must be unique — use email when given, else phone-based key
    username = email if email else f'phone_{phone}@vyayam.local'

    user, _created = User.objects.get_or_create(
        username=username,
        defaults={'email': email, 'first_name': name.split()[0] if name else ''},
    )
    if _created:
        user.set_unusable_password()
        user.save()

    try:
        age = int(age_raw) if age_raw else None
    except ValueError:
        age = None

    link, link_created = TherapistPatientLink.objects.get_or_create(
        therapist=therapist,
        patient=user,
        defaults={
            'full_name': name,
            'email': email,
            'phone': phone,
            'age': age,
            'sex': sex,
            'primary_condition': condition,
            'condition_tone': 'primary',
            'status': 'pending',
        },
    )
    if link_created:
        flash.success(request, f"Invite ready for {name}. Click 'Simulate accept' on their card to activate their login.")
    else:
        flash.info(request, f"{name} is already linked.")
    return redirect('therapist_dashboard')


@therapist_required
@require_POST
def simulate_accept_invite(request, link_id):
    """Dev-only: flips a pending link to active, sets Django password, and
    creates/updates a PatientProfile so the patient can use the PWA login."""
    therapist = request.user.therapist
    link = get_object_or_404(TherapistPatientLink, id=link_id, therapist=therapist)
    if link.status != 'pending':
        flash.info(request, "That invite is already accepted.")
        return redirect('therapist_dashboard')

    link.status = 'active'
    link.accepted_at = timezone.now()
    if not link.program_start:
        link.program_start = timezone.now().date()
    link.save()

    generated_password = secrets.token_urlsafe(6)[:8]

    link.patient.set_password(generated_password)
    link.patient.save()

    # Resolve login phone — use stored phone or fall back to synthetic number
    login_phone = link.phone
    if not login_phone:
        login_phone = f'9{link.patient.id:09d}'
        logger.warning("No phone on link %s — using synthetic: %s", link.id, login_phone)

    # Create (or repair) the PatientProfile so PWA phone-login works
    patient_id = f'TH_{link.patient.id:08d}'
    try:
        from strength_app.models import PatientProfile
        profile, created = PatientProfile.objects.get_or_create(
            user_id=link.patient.id,
            defaults={
                'patient_id': patient_id,
                'phone': login_phone,
                'password': make_password(generated_password),
                'name': link.full_name or 'Patient',
                'age': link.age or 30,
                'goals': 'Rehabilitation and recovery',
                'therapist_managed': True,
                'gate_test_completed': True,
                'prescription_mode': 'therapist_manual',
                'must_change_password': True,
            },
        )
        if not created:
            PatientProfile.objects.filter(user_id=link.patient.id).update(
                phone=login_phone,
                password=make_password(generated_password),
                name=link.full_name or profile.name,
                therapist_managed=True,
                gate_test_completed=True,
                prescription_mode='therapist_manual',
                must_change_password=True,
            )
    except Exception as exc:
        logger.error("PatientProfile creation failed for link %s: %s", link.id, exc)

    flash.success(
        request,
        mark_safe(
            f"<strong>Patient activated for {escape(link.display_name)}.</strong>"
            f"<br>Login phone:&nbsp;<code style='background:#d1fae5;padding:1px 6px;border-radius:4px;'>{escape(login_phone)}</code>"
            f"<br>Password:&nbsp;<code style='background:#fde68a;padding:1px 6px;border-radius:4px;font-weight:600;'>{escape(generated_password)}</code>"
            f"<br><strong style='color:#b91c1c;'>Save these now — they will not be shown again.</strong>"
            f"<br><span style='opacity:.75;font-size:.85em;'>Therapist must communicate these credentials to the patient through a secure channel.</span>"
        ),
    )
    return redirect('therapist_dashboard')


# ---------------------------------------------------------------------------
# Patient detail (tabbed)
# ---------------------------------------------------------------------------

VALID_TABS = ('today', 'builder', 'progress', 'history', 'messages', 'reports', 'notes')  # R2-T7


@therapist_required
def patient_detail(request, link_id):
    therapist = request.user.therapist
    link = get_linked_patient_or_404(therapist, link_id)
    tab = request.GET.get('tab', 'today')
    if tab not in VALID_TABS:
        tab = 'today'

    card = _link_card(link)

    # The current week's prescription (latest by week_number).
    current_week = max(1, link.current_week)
    rx = (
        Prescription.objects
        .filter(link=link)
        .order_by('-week_number')
        .prefetch_related('items')
        .first()
    )
    rx_items = list(rx.items.all()) if rx else []

    history_sessions = []
    try:
        from strength_app.models import PatientProfile, WorkoutSession
        _profile = None
        if link.patient_id:
            _profile = PatientProfile.objects.filter(user_id=link.patient_id).first()
        if _profile is not None:
            history_sessions = list(
                WorkoutSession.objects
                .filter(patient=_profile)
                .order_by('-session_date')[:10]
            )
    except Exception:
        history_sessions = []

    seed = _seed_demo_metrics(link)
    history_seed = seed.get('history', []) if seed else []

    # B-X3/B-N3 (2026-07 exam): sender__therapist joined so the template's
    # is_from_therapist check doesn't fire one query per bubble; newest 200
    # only (chronological), so a long chat can't unbound the page.
    msgs = list(reversed(
        link.messages.select_related('sender', 'sender__therapist')
        .order_by('-sent_at')[:200]))

    reports_qs = list(link.progress_reports.all()[:100])  # B-P1: bounded

    # R3: per-session reports (newest first) for the Reports tab.
    session_reports = list(
        link.session_reports.order_by('-report_date', '-created_at')[:30])

    # Therapist-managed clinical fields + patient PWA workout logs.
    health_profile = getattr(link, 'health_profile', None)
    session_logs = list(
        link.session_logs
        .order_by('-started_at')
        .prefetch_related('items')[:20]
    )
    last_completed_log = next((s for s in session_logs if s.completed_at is not None), None)

    progress_charts = None
    if tab == 'progress':
        progress_charts = _build_progress_charts(link)

    patient_profile = None
    try:
        from strength_app.models import PatientProfile
        if link.patient_id:
            patient_profile = PatientProfile.objects.filter(user_id=link.patient_id).first()
    except Exception:
        patient_profile = None

    ctx = {
        'therapist': therapist,
        'link': link,
        'card': card,
        'tab': tab,
        'current_week': current_week,
        'rx': rx,
        'rx_items': rx_items,
        'rx_items_data': [
            {
                'id': i.id,
                'order': i.order,
                'exercise_id': i.exercise_id,
                'exercise_name': i.exercise_name,
                'movement_pattern': i.movement_pattern,
                'sets': i.sets,
                'reps': i.reps,
                'load': i.load,
                'rest_seconds': i.rest_seconds,
                'tempo': i.tempo,
                'notes': i.notes,
                'pain_stop_threshold': i.pain_stop_threshold,
            }
            for i in rx_items
        ],
        'catalog': EXERCISES,
        'history_sessions': history_sessions,
        'history_seed': history_seed,
        # B-X3 (2026-07 exam): 'messages' shadowed django.contrib.messages —
        # chat rendered as flash banners and every flash aimed at this page
        # (incl. the one-time reset temp password) was silently dropped.
        'chat_messages': msgs,
        'reports': reports_qs,
        'session_reports': session_reports,
        'active_section': 'patients',
        'health_profile': health_profile,
        'patient_profile': patient_profile,
        'visit_notes': list(link.visit_notes.all()[:50]),       # R2-T7
        'patient_alerts': list(link.alerts.all()[:20]),         # R2-T2
        'session_logs': session_logs,
        'last_completed_log': last_completed_log,
        'progress_charts': progress_charts,
    }
    return render(request, 'therapist_app/patient_detail.html', ctx)


@therapist_required
@require_POST
def save_onboarding(request, link_id):
    """Save therapist-driven clinical onboarding for a linked patient.

    Updates fields on:
      - TherapistPatientLink (display fields the therapist edits — name/age/sex/condition/etc.)
      - PatientProfile (height/weight/age/biological_sex — the strength_app side)
      - TherapistPatientHealthProfile (clinical-only fields the patient never sees)
    """
    therapist = request.user.therapist
    link = get_linked_patient_or_404(therapist, link_id)

    full_name = request.POST.get('full_name', '').strip() or link.full_name

    age_raw = request.POST.get('age', '').strip()
    age = None
    if age_raw:
        try:
            age = max(13, min(100, int(age_raw)))
        except ValueError:
            age = None

    sex = request.POST.get('sex', '').strip()
    height_raw = request.POST.get('height_cm', '').strip()
    weight_raw = request.POST.get('weight_kg', '').strip()
    height_cm = None
    weight_kg = None
    try:
        height_cm = float(height_raw) if height_raw else None
    except ValueError:
        height_cm = None
    try:
        weight_kg = float(weight_raw) if weight_raw else None
    except ValueError:
        weight_kg = None

    primary_condition = request.POST.get('primary_condition', '').strip()
    affected_side = request.POST.get('affected_side', '').strip()
    injury_date_raw = request.POST.get('injury_date', '').strip()
    surgery_date_raw = request.POST.get('surgery_date', '').strip()

    def _parse_date(s):
        if not s:
            return None
        try:
            from datetime import date as _date
            y, m, d = s.split('-')
            return _date(int(y), int(m), int(d))
        except (ValueError, TypeError):
            return None

    injury_date = _parse_date(injury_date_raw)
    surgery_date = _parse_date(surgery_date_raw)

    pain_medications = request.POST.get('pain_medications', '').strip()
    other_conditions = request.POST.get('other_conditions', '').strip()
    emergency_contact_name = request.POST.get('emergency_contact_name', '').strip()
    emergency_contact_phone = request.POST.get('emergency_contact_phone', '').strip()
    goals = request.POST.get('goals', '').strip()

    with transaction.atomic():
        # Update the link (visible therapist-facing fields).
        link.full_name = full_name
        if age is not None:
            link.age = age
        if sex:
            link.sex = sex
        if primary_condition:
            link.primary_condition = primary_condition
        if injury_date is not None:
            link.injury_date = injury_date
        link.save()

        # Update or create the clinical health profile.
        TherapistPatientHealthProfile.objects.update_or_create(
            link=link,
            defaults={
                'height_cm': height_cm,
                'weight_kg': weight_kg,
                'affected_side': affected_side if affected_side in ('left', 'right', 'bilateral', 'na') else '',
                'surgery_date': surgery_date,
                'pain_medications': pain_medications,
                'other_conditions': other_conditions,
                'emergency_contact_name': emergency_contact_name,
                'emergency_contact_phone': emergency_contact_phone,
                'goals': goals,
            },
        )

        # Mirror demographic fields onto the patient PWA profile, if it exists.
        try:
            from strength_app.models import PatientProfile
            pp = PatientProfile.objects.filter(user_id=link.patient_id).first()
            if pp is not None:
                pp.name = full_name or pp.name
                if age is not None:
                    pp.age = age
                if height_cm is not None:
                    pp.height_cm = height_cm
                if weight_kg is not None:
                    pp.weight_kg = weight_kg
                if sex:
                    bio_map = {'M': 'male', 'F': 'female'}
                    pp.biological_sex = bio_map.get(sex.upper(), pp.biological_sex)
                if goals:
                    pp.goals = goals
                pp.therapist_managed = True
                pp.gate_test_completed = True
                pp.save()
        except Exception:
            # D5: the engine reads age/sex/goals from PatientProfile — a
            # silent mirror failure means stale demographics drive dosing.
            logger.warning('onboarding mirror to PatientProfile failed for '
                           'link %s', link.id, exc_info=True)

    flash.success(request, "Patient details saved.")
    return redirect(f"/therapist/patient/{link.id}/?tab=today")


# ---------------------------------------------------------------------------
# Patient detail mutations
# ---------------------------------------------------------------------------

@therapist_required
@require_POST
def save_program(request, link_id):
    """Saves the Program Builder state. Accepts JSON: { week_number, items: [...], publish: bool }."""
    therapist = request.user.therapist
    link = get_linked_patient_or_404(therapist, link_id)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON.")

    week_number = _safe_int(payload.get('week_number'), max(1, link.current_week), 1, 200)
    items_raw = payload.get('items') or []
    publish = bool(payload.get('publish'))
    notes = payload.get('notes_for_patient', '') or ''

    with transaction.atomic():
        rx, _ = Prescription.objects.get_or_create(
            link=link,
            week_number=week_number,
            defaults={'notes_for_patient': notes},
        )
        rx.notes_for_patient = notes
        rx.draft_json = {'items': items_raw, 'updated_at': timezone.now().isoformat()}
        if publish:
            rx.published_at = timezone.now()
            rx.items.all().delete()
            for idx, item in enumerate(items_raw):
                ex_id = (item.get('exercise_id') or item.get('id') or '').strip()
                catalog_entry = EXERCISES_BY_ID.get(ex_id, {})
                PrescriptionItem.objects.create(
                    prescription=rx,
                    order=idx,
                    exercise_id=ex_id,
                    exercise_name=item.get('exercise_name') or catalog_entry.get('name', ex_id),
                    movement_pattern=catalog_entry.get('movement_pattern', ''),
                    sets=_safe_int(item.get('sets'), 3, 1, 10),
                    reps=_safe_int(item.get('reps'), 10, 1, 100),
                    load=str(item.get('load') or 'BW'),
                    rest_seconds=_safe_int(item.get('rest_seconds') or item.get('rest'), 60, 0, 600),
                    tempo=str(item.get('tempo') or ''),
                    notes=str(item.get('notes') or ''),
                    # D2: keep an explicit 0 (skip above ANY pain); only
                    # blank/absent means "no therapist value" → NULL.
                    pain_stop_threshold=(
                        _safe_int(item.get('pain_stop_threshold'), 5, 0, 10)
                        if item.get('pain_stop_threshold') not in (None, '')
                        else None
                    ),
                )
        rx.save()

    return JsonResponse({
        'ok': True,
        'published': publish,
        'week_number': rx.week_number,
        'item_count': rx.items.count(),
        'updated_at': timezone.now().isoformat(),
    })


@therapist_required
@require_POST
def send_message(request, link_id):
    therapist = request.user.therapist
    link = get_linked_patient_or_404(therapist, link_id)
    body = request.POST.get('body', '').strip()
    if not body:
        flash.error(request, "Message cannot be empty.")
        return redirect(f"/therapist/patient/{link.id}/?tab=messages")
    TherapistMessage.objects.create(link=link, sender=request.user, body=body)
    return redirect(f"/therapist/patient/{link.id}/?tab=messages")


@therapist_required
@require_POST
def reset_patient_password(request, link_id):
    """R2-U1: issue a one-time temporary password for a managed patient.

    The patient's account is phone+password (PatientProfile, not Django
    auth) with no self-serve email on file in most B2B2C cases — the
    therapist is their recovery path. The temp password is shown ONCE to
    the therapist; the patient is forced through change_password at next
    sign-in (must_change_password flag).
    """
    therapist = request.user.therapist
    link = get_linked_patient_or_404(therapist, link_id)

    from strength_app.models import PatientProfile
    profile = PatientProfile.objects.filter(user_id=link.patient_id).first()
    if profile is None:
        flash.error(request, "This patient hasn't activated their app account yet.")
        return redirect(f"/therapist/patient/{link.id}/")

    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    temp = ''.join(secrets.choice(alphabet) for _ in range(10))

    from django.contrib.auth.hashers import make_password
    profile.password = make_password(temp)
    profile.must_change_password = True
    profile.save(update_fields=['password', 'must_change_password'])

    flash.success(
        request,
        f"Temporary password for {link.full_name}: {temp} — share it securely. "
        "They must set their own password at next sign-in.",
    )
    return redirect(f"/therapist/patient/{link.id}/")


@therapist_required
@require_POST
def generate_report(request, link_id):
    """Generate a 1-2 page PDF progress report for the most recent 7-day window."""
    therapist = request.user.therapist
    link = get_linked_patient_or_404(therapist, link_id)
    today = timezone.localdate()
    week_start = today - timedelta(days=6)
    week_end = today
    week = max(1, link.current_week)

    report = ProgressReport.objects.create(
        link=link,
        title=f"Week {week} Progress Report",
        period_start=week_start,
        period_end=week_end,
        status='draft',
        generated_by='therapist',
    )

    try:
        from .pdf_generator import generate_patient_pdf
        pdf_file = generate_patient_pdf(link, week_start, week_end)
        report.pdf.save(pdf_file.name, pdf_file, save=False)
        report.status = 'ready'
        report.save()
        flash.success(request, "Report generated.")
    except Exception:
        logger.exception("Failed to render PDF for report %s", report.id)
        flash.error(request, "Report row created but PDF rendering failed.")

    return redirect(f"/therapist/patient/{link.id}/?tab=reports")


@therapist_required
def download_report(request, report_id):
    """E-2: stream a progress-report PDF only to the therapist who owns the link.
    Replaces the raw /media/ link, which had no auth/ownership gate."""
    therapist = request.user.therapist
    report = get_object_or_404(
        ProgressReport, id=report_id, link__therapist=therapist
    )
    if not report.pdf:
        raise Http404("No PDF for this report.")
    return FileResponse(
        report.pdf.open('rb'),
        as_attachment=True,
        filename=f"{report.title.replace(' ', '_')}.pdf",
        content_type='application/pdf',
    )


# ---------------------------------------------------------------------------
# 2026-07 DARK CAMERA COACHES — therapist QA surface (the only new route of
# the final session). Read-only with respect to patient data: the run page
# passes NO capture endpoints (SET_LOG_URL / REST_EVENT_URL / REPORT_PAIN_URL
# all empty), so nothing a therapist does here writes a single row — the
# simplest of the two allowed designs, chosen over is_qa-flagged rows.
# ---------------------------------------------------------------------------

def _dark_coach_entries():
    """Catalog entries carrying a *_rx dark-coach key, in catalog order."""
    from .exercise_catalog import EXERCISES
    return [e for e in EXERCISES
            if (e.get('v2_exercise_key') or '').endswith('_rx')]


@therapist_required
def qa_dark_coaches(request):
    from strength_app.cv_targets import get_cv_config
    rows = []
    for e in _dark_coach_entries():
        key = e['v2_exercise_key']
        cfg = get_cv_config(key)
        rows.append({
            'name': e['name'],
            'exercise_id': e['exercise_id'],
            'key': key,
            'js_type': cfg.get('js_type') or '—',
            'is_hold': bool(cfg.get('is_hold')),
            'live': bool(e.get('v2_ghost_supported')),
        })
    return render(request, 'therapist_app/qa_dark_coaches.html', {
        'therapist': request.user.therapist,
        'rows': rows,
        'active_section': 'settings',
    })


@therapist_required
def qa_dark_coach_run(request, key):
    """Run one dark coach through the real camera flow, flagged QA MODE.
    No patient, no capture rows — library_mode returns to the QA list."""
    from django.urls import reverse as _reverse
    from strength_app.cv_targets import get_cv_config
    from strength_app.exercise_content_gap_fill import EXERCISE_CONTENT_GAP_FILL

    entry = next((e for e in _dark_coach_entries()
                  if e['v2_exercise_key'] == key), None)
    if entry is None:
        raise Http404
    content = EXERCISE_CONTENT_GAP_FILL.get(key, {})
    cfg = get_cv_config(key)

    exercise = {
        'exercise_id': key,
        'exercise_name': entry['name'],
        'movement_pattern': entry['movement_pattern'],
        'sets': entry['default_sets'],
        'reps': entry['default_reps'],
        'tempo': '3-1-2-0',
        'tempo_parts': ['3', '1', '2', '0'],
        'rest_seconds': entry['default_rest_seconds'],
        'prescribed_rest': entry['default_rest_seconds'],
        'is_unilateral': False,
        'mind_muscle_cue': content.get('mind_muscle_cue', {}),
        'form_cues': content.get('form_cues', []),
        'instructions': ' '.join(content.get('instructions', [])),
        'asymmetry': {},
        'capability_level': 2,
        'is_hold': bool(cfg.get('is_hold')),
    }
    ctx = {
        'exercise': exercise,
        'exercise_index': 0,
        'total_exercises': 1,
        'is_last_exercise': True,
        'has_strength_profile': True,
        'library_mode': True,
        'library_return_url': _reverse('therapist_qa_dark_coaches'),
        'qa_mode': True,
    }
    return render(request, 'strength_app/v1_exercise_execute.html', ctx)
