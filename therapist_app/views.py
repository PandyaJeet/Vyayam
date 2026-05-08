"""
Therapist console views — desktop-first, server-rendered.

Tab routing on the patient detail page is via ?tab=<key> rather than separate
URLs, so the Back button + analytics see one canonical patient URL.
"""

import json
import logging
import re
from datetime import timedelta

from django.contrib import messages as flash
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.db import transaction

logger = logging.getLogger(__name__)
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

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


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

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

def _compute_link_metrics(link):
    """Returns the computed dashboard metrics per HANDOFF §3 (PatientCard).

    Counts WorkoutSessions for the linked patient. The strength_app session is
    keyed to PatientProfile (not Django User), so we look up the profile via
    the user's email — best-effort. If no profile is found, we return zeros.
    """
    today = timezone.now().date()
    days_window = 14

    sparkline_7d = [0] * 7
    pain_trend_7d = [0, 0, 0, 0, 0, 0, 0]
    compliance_pct = 0

    try:
        from strength_app.models import PatientProfile
        profile = None
        if link.patient_id:
            profile = PatientProfile.objects.filter(user_id=link.patient_id).first()
    except Exception:
        profile = None

    if profile is not None:
        from strength_app.models import WorkoutSession
        sessions = WorkoutSession.objects.filter(
            patient=profile,
            session_date__date__gte=today - timedelta(days=days_window),
        )
        completed = sessions.filter(total_exercises_completed__gt=0).count()
        prescribed = max(days_window, completed)  # rough heuristic; refined later
        compliance_pct = int(round((completed / prescribed) * 100)) if prescribed else 0

        for s in sessions:
            day_offset = (today - s.session_date.date()).days
            if 0 <= day_offset < 7 and s.total_exercises_completed > 0:
                sparkline_7d[6 - day_offset] = 1

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


def _link_card(link):
    seed = _seed_demo_metrics(link)
    if seed:
        compliance = seed.get('compliance', 0)
        sparkline = seed.get('sparkline', [0] * 7)
        pain = seed.get('pain', [])
        flags = seed.get('flags', [])
        last_session = seed.get('last_session', '—')
    else:
        m = _compute_link_metrics(link)
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
    cards = [_link_card(link) for link in links]
    active = [c for c in cards if not c['pending']]
    flagged = [c for c in active if c['flags']]
    today_count = sum(1 for c in active if c['last_session'] == 'Today')

    ctx = {
        'therapist': therapist,
        'cards': cards,
        'active_count': len(active),
        'flagged_count': len(flagged),
        'today_count': today_count,
        'reports_due': 2,  # placeholder until we wire real report scheduling
        'active_section': 'dashboard',
    }
    return render(request, 'therapist_app/dashboard.html', ctx)


@therapist_required
def patient_list(request):
    therapist = request.user.therapist
    filter_kind = request.GET.get('filter', 'all')
    q = request.GET.get('q', '').strip()

    links = list(therapist.patient_links.exclude(status='archived').order_by('-invited_at'))
    cards = [_link_card(link) for link in links]

    if filter_kind == 'active':
        cards = [c for c in cards if not c['pending']]
    elif filter_kind == 'pending':
        cards = [c for c in cards if c['pending']]
    elif filter_kind == 'flagged':
        cards = [c for c in cards if c['flags']]

    if q:
        ql = q.lower()
        cards = [c for c in cards if ql in (c['name'] or '').lower()]

    counts = {
        'all': len([c for c in [_link_card(l) for l in links]]),
        'active': sum(1 for l in links if l.status == 'active'),
        'pending': sum(1 for l in links if l.status == 'pending'),
        'flagged': sum(1 for c in [_link_card(l) for l in links] if c['flags']),
    }

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
    reports_qs = (
        ProgressReport.objects
        .filter(link__therapist=therapist)
        .select_related('link')
        .order_by('-created_at')
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

    link.patient.set_password('patient')
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
                'password': make_password('patient'),
                'name': link.full_name or 'Patient',
                'age': link.age or 30,
                'goals': 'Rehabilitation and recovery',
                'therapist_managed': True,
                'gate_test_completed': True,
                'prescription_mode': 'therapist_manual',
            },
        )
        if not created:
            PatientProfile.objects.filter(user_id=link.patient.id).update(
                phone=login_phone,
                password=make_password('patient'),
                name=link.full_name or profile.name,
                therapist_managed=True,
                gate_test_completed=True,
                prescription_mode='therapist_manual',
            )
    except Exception as exc:
        logger.error("PatientProfile creation failed for link %s: %s", link.id, exc)

    flash.success(
        request,
        mark_safe(
            f"<strong>{escape(link.display_name)} activated.</strong>"
            f"<br>Patient login credentials:"
            f"<br>&nbsp;&nbsp;Phone:&nbsp;<code style='background:#d1fae5;padding:1px 6px;border-radius:4px;'>{escape(login_phone)}</code>"
            f"<br>&nbsp;&nbsp;Password:&nbsp;<code style='background:#d1fae5;padding:1px 6px;border-radius:4px;'>patient</code>"
            f"<br><span style='opacity:.75;font-size:.85em;'>Share with the patient — they can sign in at /login/ on any device.</span>"
        ),
    )
    return redirect('therapist_dashboard')


# ---------------------------------------------------------------------------
# Patient detail (tabbed)
# ---------------------------------------------------------------------------

VALID_TABS = ('today', 'builder', 'progress', 'history', 'messages', 'reports')


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

    msgs = list(link.messages.select_related('sender').all())

    reports_qs = list(link.progress_reports.all())

    # Therapist-managed clinical fields + patient PWA workout logs.
    health_profile = getattr(link, 'health_profile', None)
    session_logs = list(
        link.session_logs
        .order_by('-started_at')
        .prefetch_related('items')[:20]
    )
    last_completed_log = next((s for s in session_logs if s.completed_at is not None), None)

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
        'rx_items_json': json.dumps([
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
            }
            for i in rx_items
        ]),
        'catalog': EXERCISES,
        'history_sessions': history_sessions,
        'history_seed': history_seed,
        'messages': msgs,
        'reports': reports_qs,
        'active_section': 'patients',
        'health_profile': health_profile,
        'patient_profile': patient_profile,
        'session_logs': session_logs,
        'last_completed_log': last_completed_log,
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
            pass

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

    week_number = int(payload.get('week_number') or max(1, link.current_week))
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
                    sets=int(item.get('sets') or 3),
                    reps=int(item.get('reps') or 10),
                    load=str(item.get('load') or 'BW'),
                    rest_seconds=int(item.get('rest_seconds') or item.get('rest') or 60),
                    tempo=str(item.get('tempo') or ''),
                    notes=str(item.get('notes') or ''),
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
def generate_report(request, link_id):
    """Stubbed: creates a ProgressReport row with status='ready' but no PDF."""
    therapist = request.user.therapist
    link = get_linked_patient_or_404(therapist, link_id)
    today = timezone.now().date()
    week = max(1, link.current_week)
    ProgressReport.objects.create(
        link=link,
        title=f"Week {week} Progress Report",
        period_start=today - timedelta(days=7),
        period_end=today,
        status='ready',
        generated_by='therapist',
    )
    flash.success(request, "Report generated. PDF rendering will land in the follow-up.")
    return redirect(f"/therapist/patient/{link.id}/?tab=reports")
