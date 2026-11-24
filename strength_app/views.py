"""
VYAYAM Django Views - COMPLETE FILE
Includes: Registration, Login, Gate Testing, Prescription, Exercise Execution with REAL CV
"""

import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.contrib.auth.hashers import check_password
from django.views.decorators.http import require_POST
from .rate_limiter import rate_limit

logger = logging.getLogger(__name__)
from .models import (
    PatientProfile, GateTestResult,
    WorkoutSession, ExerciseExecution, ProgressReport,
    PatientFamilyCapability, StretchSession
)
from .utils import generate_prescription
import json
import base64
import time


# ============================================================================
# PATIENT AUTHENTICATION
# ============================================================================

@rate_limit(max_attempts=5, window_seconds=300, key_prefix='login')
def patient_login(request: HttpRequest):
    """Patient login view — phone + password"""
    if request.method == 'POST':
        import re as _re
        phone_raw = request.POST.get('phone', '').strip()
        phone = _re.sub(r'[^0-9]', '', phone_raw)
        password = request.POST.get('password', '')

        if len(phone) < 10 or len(phone) > 15:
            messages.error(request, 'Invalid phone number or password.')
            return render(request, 'strength_app/login.html')

        try:
            patient = PatientProfile.objects.get(phone=phone)
            if check_password(password, patient.password):
                # Flush old session to prevent data leakage / session fixation.
                request.session.flush()
                request.session['patient_id'] = patient.patient_id
                has_profile = patient.strength_profiles.exists()
                request.session['has_strength_profile'] = has_profile

                # R2-U1: therapist-issued temp password — force a change
                # before anything else.
                if patient.must_change_password:
                    messages.info(request, 'Please set a new password to continue.')
                    return redirect('change_password')

                # B2B2C: therapist-managed patients skip strength_app onboarding
                # entirely and land on their therapist-driven session today page.
                if patient.therapist_managed:
                    return redirect('therapist_session_today')

                # Football-track athletes with an active coach link get the
                # athlete PWA instead of the generic patient dashboard.
                from .v1_athlete_views import is_coached_football_athlete
                if is_coached_football_athlete(patient):
                    return redirect('athlete_today')

                if patient.gate_test_completed and has_profile:
                    return redirect('v1_dashboard')

                # Resume onboarding from where user left off
                if not patient.name:
                    return redirect('onboarding_start')
                if not has_profile:
                    return redirect('onboarding_strength_test')
                if not patient.gate_test_completed:
                    return redirect('onboarding_goals')
                return redirect('v1_dashboard')
            else:
                messages.error(request, 'Invalid phone number or password')
        except PatientProfile.DoesNotExist:
            messages.error(request, 'Invalid phone number or password')

    return render(request, 'strength_app/login.html')


def patient_register(request: HttpRequest):
    """Patient registration — redirects to V1 onboarding flow."""
    return redirect('onboarding_start')


def offline(request: HttpRequest):
    """R2-U9: standalone offline fallback page pre-cached by sw.js."""
    return render(request, 'strength_app/offline.html')


def healthz(request: HttpRequest):
    """R2-W6: trivial unauthenticated health check for uptime monitors.
    Touches the DB so a dead database shows as unhealthy, not a 200."""
    try:
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
        return JsonResponse({'status': 'ok'})
    except Exception:
        return JsonResponse({'status': 'degraded'}, status=503)


# ============================================================================
# R2-U1: FORGOT / RESET PASSWORD
# ============================================================================

@rate_limit(max_attempts=5, window_seconds=300, key_prefix='forgot_password')
def forgot_password(request: HttpRequest):
    """Self-serve password recovery by phone number.

    The response is IDENTICAL whether or not the phone matches an account
    (no user enumeration). When an account with an email exists, a
    single-use 1-hour reset link is emailed; therapist-managed patients are
    covered by the on-page copy ("ask your therapist") and the therapist
    console's reset button.
    """
    import re as _re
    sent = False
    if request.method == 'POST':
        phone = _re.sub(r'[^0-9]', '', request.POST.get('phone', '').strip())
        if 10 <= len(phone) <= 15:
            patient = PatientProfile.objects.filter(phone=phone).first()
            if patient and patient.email:
                import secrets
                from .models import PasswordResetToken
                token = secrets.token_urlsafe(32)
                # F2 (deploy review): only sha256(token) is stored — the raw
                # token exists solely in the email link below.
                PasswordResetToken.objects.create(
                    patient=patient, token=PasswordResetToken.hash_of(token))
                reset_url = request.build_absolute_uri(
                    reverse('reset_password', args=[token])
                )
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings as _settings
                    send_mail(
                        'VYAYAM — reset your password',
                        ('Hi {name},\n\nSomeone (hopefully you) asked to reset the '
                         'password for your VYAYAM account. Use this link within '
                         '1 hour:\n\n{url}\n\nIf this wasn\'t you, you can ignore '
                         'this email — your password is unchanged.').format(
                            name=patient.name or 'there', url=reset_url),
                        getattr(_settings, 'DEFAULT_FROM_EMAIL', 'noreply@vyayam.app'),
                        [patient.email],
                        fail_silently=True,
                    )
                except Exception:
                    logger.error('password reset email failed for %s',
                                 patient.patient_id, exc_info=True)
        sent = True  # always — identical response either way
    return render(request, 'strength_app/forgot_password.html', {'sent': sent})


@rate_limit(max_attempts=10, window_seconds=300, key_prefix='reset_password')
def reset_password(request: HttpRequest, token: str):
    """Set a new password from an emailed single-use token."""
    from django.contrib.auth.hashers import make_password
    from .models import PasswordResetToken

    # F2 (deploy review): tokens are stored hashed — look up by sha256(raw).
    prt = (PasswordResetToken.objects
           .filter(token=PasswordResetToken.hash_of(token))
           .select_related('patient').first())
    if not prt or not prt.is_valid():
        return render(request, 'strength_app/reset_password.html',
                      {'invalid': True})

    error = None
    if request.method == 'POST':
        new = request.POST.get('new_password', '')
        confirm = request.POST.get('confirm_password', '')
        # Same rules as registration
        if len(new) < 8:
            error = 'Password must be at least 8 characters.'
        elif new.isdigit() or new.isalpha():
            error = 'Password must mix letters and numbers.'
        elif new != confirm:
            error = 'Passwords do not match.'
        else:
            patient = prt.patient
            patient.password = make_password(new)
            patient.must_change_password = False
            patient.save(update_fields=['password', 'must_change_password'])
            prt.used = True
            prt.save(update_fields=['used'])
            # kill any other live tokens for this account
            PasswordResetToken.objects.filter(
                patient=patient, used=False
            ).update(used=True)
            messages.success(request, 'Password updated. Please sign in.')
            return redirect('patient_login')
    return render(request, 'strength_app/reset_password.html',
                  {'invalid': False, 'error': error})


def dashboard(request: HttpRequest):
    """Patient dashboard — all patients use V1 dashboard now."""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')
    return redirect('v1_dashboard')


# ============================================================================
# GATE TESTING — Progression-Based System
# ============================================================================
# Flow:
#   gate_testing (GET)  → Shows all 6 exercise families to be tested
#   gate_testing (POST) → Initialises session, redirects to first family level 0
#   execute_gate_test(family_index, level_index) → Shows that level with camera
#       "Too Easy → Try Next"  → same family, level+1
#       "This is My Level"     → save result, next family at level 0
#       "Cannot Do This"       → save cannot_do, next family at level 0
#   gate_test_results   → Shows per-family results with prescribed exercise
# ============================================================================

from .exercise_progressions import (
    PROGRESSION_CHAINS, DEFAULT_GATE_TEST_FAMILIES,
    classify_performance, get_prescription_sets_reps,
)

# New progressive-loading helpers (added with capability system)
try:
    from .exercise_progressions import (
        classify_performance_numeric,
        get_dosage_for_level,
        CAPABILITY_STRING_TO_NUMERIC,
    )
    from .exercise_tags import (
        get_patient_modifier, apply_modifier, capability_str_to_numeric
    )
    CAPABILITY_SYSTEM_AVAILABLE = True
except ImportError:
    CAPABILITY_SYSTEM_AVAILABLE = False
    CAPABILITY_STRING_TO_NUMERIC = {
        'cannot_do': 1, 'struggling': 2, 'manageable': 3, 'easy': 4
    }
    def capability_str_to_numeric(s): return CAPABILITY_STRING_TO_NUMERIC.get(s, 3)


def _build_family_session_list():
    """Return the ordered list of family dicts to store in session."""
    families = []
    for fid in DEFAULT_GATE_TEST_FAMILIES:
        chain = PROGRESSION_CHAINS[fid]
        families.append({
            'family_id': fid,
            'name': chain['name'],
            'icon': chain['icon'],
            'description': chain['description'],
            'movement_type': chain['movement_type'],
            'status': 'pending',          # pending / completed / skipped
            'levels': chain['levels'],    # serialisable list of level dicts
            'result': None,               # filled when family is completed
        })
    return families


def _update_capability_after_session(patient, comfortable, difficulty_rating, exercise_results):
    """
    Progressive Loading System — called after every completed workout session.

    Logic:
      1. Increment sessions_at_current_level for each exercised family
      2. If patient reported comfortable AND difficulty ≤ 3 → increment
         consecutive_comfortable_sessions
      3. After 3 consecutive comfortable sessions → advance capability by +1
      4. If capability reaches 5 (Advanced) → flag ready_to_advance = True
         (next prescription will move to next exercise in the ladder)
      5. If uncomfortable (difficulty ≥ 4) → reset comfortable streak

    This is called automatically — no therapist input needed.
    """
    import datetime as _dt
    from .models import PatientFamilyCapability
    from .exercise_progressions import PROGRESSION_CHAINS, CAPABILITY_STRING_TO_NUMERIC

    # Determine which families were exercised in this session
    all_exercises = exercise_results or []
    exercised_ex_ids = {r.get('exercise_id', '') for r in all_exercises}

    # Build exercise_id → family_id lookup
    ex_to_family = {}
    for fid, chain in PROGRESSION_CHAINS.items():
        for lvl in chain['levels']:
            ex_to_family[lvl['exercise_id']] = fid

    # Find all families that were exercised
    exercised_families = set()
    for ex_id in exercised_ex_ids:
        fam = ex_to_family.get(ex_id)
        if fam:
            exercised_families.add(fam)

    # Update each family's capability record
    for pfc in PatientFamilyCapability.objects.filter(
        patient=patient, family_id__in=exercised_families
    ):
        pfc.sessions_at_current_level += 1

        # Comfortable = self-reported comfortable AND difficulty ≤ 3
        session_comfortable = comfortable and (difficulty_rating <= 3)

        if session_comfortable:
            pfc.consecutive_comfortable_sessions += 1
        else:
            # Hard session or discomfort — reset streak
            pfc.consecutive_comfortable_sessions = 0

        # Advance capability after 3 consecutive comfortable sessions
        if pfc.consecutive_comfortable_sessions >= 3:
            old_cap = pfc.capability_numeric
            if old_cap < 5:
                pfc.capability_numeric = old_cap + 1
                pfc.capability_string = {
                    1: 'cannot_do', 2: 'struggling', 3: 'manageable',
                    4: 'easy', 5: 'easy'
                }.get(pfc.capability_numeric, 'manageable')
                pfc.consecutive_comfortable_sessions = 0  # reset after advance

                # Log advancement
                history = pfc.progression_history_json or []
                history.append({
                    'date': _dt.datetime.now().isoformat(),
                    'type': 'capability_advance',
                    'from_capability': old_cap,
                    'to_capability': pfc.capability_numeric,
                    'trigger': 'consecutive_comfortable_sessions',
                })
                pfc.progression_history_json = history

        # At capability 5 → flag ready to advance to next ladder rung
        if pfc.capability_numeric >= 5:
            pfc.ready_to_advance = True
        
        # Update weeks (roughly every 7 sessions = 1 week if exercising daily)
        if pfc.sessions_at_current_level % 7 == 0:
            pfc.weeks_at_current_level += 1

        pfc.save()


def gate_testing(request: 'HttpRequest'):
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')

    patient = get_object_or_404(PatientProfile, patient_id=patient_id)

    if request.method == 'POST':
        families = _build_family_session_list()
        request.session['gate_families'] = families
        request.session.modified = True
        return redirect('execute_gate_test', family_index=0, level_index=0)

    # GET — show overview
    families_overview = [
        {
            'family_id': fid,
            'name': PROGRESSION_CHAINS[fid]['name'],
            'icon': PROGRESSION_CHAINS[fid]['icon'],
            'description': PROGRESSION_CHAINS[fid]['description'],
            'num_levels': len(PROGRESSION_CHAINS[fid]['levels']),
            'first_exercise': PROGRESSION_CHAINS[fid]['levels'][0]['name'],
            'last_exercise': PROGRESSION_CHAINS[fid]['levels'][-1]['name'],
        }
        for fid in DEFAULT_GATE_TEST_FAMILIES
    ]
    return render(request, 'strength_app/gate_testing.html', {
        'patient': patient,
        'families_overview': families_overview,
        'total_families': len(DEFAULT_GATE_TEST_FAMILIES),
    })


def execute_gate_test(request: HttpRequest, family_index: int, level_index: int):
    """
    Show the current exercise level for the current family.
    Renders a camera page with three buttons:
      ① Too Easy → Try Next Level   (advances level_index)
      ② This is My Level            (records result, moves to next family)
      ③ Cannot Do This              (records cannot_do, moves to next family)
    """
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')

    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    families = request.session.get('gate_families')

    if not families or family_index >= len(families):
        messages.error(request, 'Gate test session not found. Please restart.')
        return redirect('gate_testing')

    family = families[family_index]
    levels = family['levels']

    # Safety: if level_index is past the last level, treat as final level
    if level_index >= len(levels):
        level_index = len(levels) - 1

    current_level = levels[level_index]
    is_last_level = (level_index == len(levels) - 1)
    is_last_family = (family_index == len(families) - 1)

    # Progress percentage across all families
    completed_count = sum(1 for f in families if f['status'] in ('completed', 'skipped'))
    overall_progress = int(completed_count / len(families) * 100)

    return render(request, 'strength_app/gate_test_execute.html', {
        'patient': patient,
        'family': family,
        'family_index': family_index,
        'total_families': len(families),
        'current_level': current_level,
        'level_index': level_index,
        'total_levels': len(levels),
        'is_last_level': is_last_level,
        'is_last_family': is_last_family,
        'overall_progress': overall_progress,
    })



@rate_limit(max_attempts=60, window_seconds=60, key_prefix='save_gate_test')  # R2-W5
def save_gate_test_result(request: HttpRequest):
    """
    AJAX endpoint called when patient clicks any of the three buttons.

    Expected JSON body:
    {
        "family_index": 0,
        "level_index": 1,
        "action": "too_easy" | "this_is_my_level" | "cannot_do",
        "reps_completed": 8,
        "difficulty_reported": 4,
        "pain_during": 0,
        "notes": ""
    }

    Returns:
    {
        "success": true,
        "next_url": "/execute-gate-test/0/2/"  or "/gate-test-results/"
    }
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})

    try:
        data = json.loads(request.body)
        patient_id = request.session.get('patient_id')
        if not patient_id:
            return JsonResponse({'success': False, 'error': 'Not authenticated'})

        patient = get_object_or_404(PatientProfile, patient_id=patient_id)
        families = request.session.get('gate_families', [])

        family_index = int(data.get('family_index', 0))
        level_index  = int(data.get('level_index', 0))
        action       = data.get('action', 'this_is_my_level')   # too_easy | this_is_my_level | cannot_do | skip

        if family_index >= len(families):
            return JsonResponse({'success': False, 'error': 'Invalid family index'})

        family = families[family_index]
        levels = family['levels']

        # ── ACTION: Too Easy → advance to next level ─────────────────────────
        if action == 'too_easy':
            next_level_index = level_index + 1
            if next_level_index >= len(levels):
                # Already at last level — patient is classified as 'easy' at max level.
                # Do NOT fall through to this_is_my_level (reps_completed may be 0 from
                # the camera, causing classify_performance to return 'cannot_do').
                final_level_index = level_index
                final_level = levels[final_level_index]
                capability = 'easy'
                sets, reps = 3, 12
                hold_dur = final_level.get('hold_duration', 0)
                if hold_dur > 0:
                    reps = 1
                reps_completed = int(data.get('reps_completed', final_level['target_reps']) or final_level['target_reps'])
                difficulty = int(data.get('difficulty_reported', 3))
                pain = int(data.get('pain_during', 0))
                notes = data.get('notes', 'Patient progressed through all levels — prescribing at max level.')
                # Jump to the DB save section
                action = '__max_level_easy__'
            else:
                next_url = f'/execute-gate-test/{family_index}/{next_level_index}/'
                return JsonResponse({'success': True, 'next_url': next_url, 'action': 'too_easy'})

        if action == '__max_level_easy__':
            pass  # Variables already set above; fall through to DB save

        # ── ACTION: Cannot Do ─────────────────────────────────────────────────
        if action == 'cannot_do':
            # If they cannot do level 0 (the easiest) → truly cannot_do
            # If they cannot do level N > 0 → they were at N-1
            final_level_index = max(0, level_index - 1) if level_index > 0 else 0
            final_level = levels[final_level_index]
            capability = 'cannot_do'
            sets, reps = 0, 0
            reps_completed = 0
            difficulty = 10
            pain = int(data.get('pain_during', 0))
            notes = data.get('notes', 'Patient could not perform this exercise.')

        # ── ACTION: Skip ──────────────────────────────────────────────────────
        elif action == 'skip':
            families[family_index]['status'] = 'skipped'
            families[family_index]['result'] = None
            request.session['gate_families'] = families
            request.session.modified = True

            next_family_index = family_index + 1
            if next_family_index >= len(families):
                next_url = '/gate-test-results/'
            else:
                next_url = f'/execute-gate-test/{next_family_index}/0/'
            return JsonResponse({'success': True, 'next_url': next_url, 'action': 'skip'})

        # ── ACTION: This is My Level ──────────────────────────────────────────
        else:  # this_is_my_level
            final_level_index = level_index
            final_level = levels[final_level_index]
            reps_completed = int(data.get('reps_completed', 0))
            difficulty = int(data.get('difficulty_reported', 5))
            pain = int(data.get('pain_during', 0))
            notes = data.get('notes', '')

            capability, sets, reps, _ = classify_performance(
                reps_completed, final_level['target_reps'], difficulty, pain,
                level_data=final_level  # pass level so dosage table is used → agrees with prescription
            )

            # If pain is too high → regress to previous level if possible
            if capability == 'cannot_do' and final_level_index > 0:
                final_level_index -= 1
                final_level = levels[final_level_index]
                capability = 'struggling'
                sets, reps = 2, 7

        # ── Save to DB ─────────────────────────────────────────────────────────
        levels_advanced = final_level_index  # 0-based = number of "too easy" clicks

        # Map family_id → legacy category (for backwards compatibility)
        family_to_category = {
            'squat_family': 'lower_body',
            'hip_hinge_family': 'lower_body',
            'lunge_family': 'lower_body',
            'push_family': 'upper_body',
            'pull_family': 'upper_body',
            'balance_family': 'lower_body',
            'cardio_family': 'cardio',
        }
        legacy_category = family_to_category.get(family['family_id'], 'lower_body')

        hold_dur = final_level.get('hold_duration', 0)
        if hold_dur > 0:
            reps = 1  # Hold-based exercises always 1 rep

        # ── Map capability string → numeric (1-5) ──────────────────────────────
        cap_numeric = CAPABILITY_STRING_TO_NUMERIC.get(capability, 3)

        GateTestResult.objects.create(
            patient=patient,
            exercise_family=family['family_id'],
            family_name=family['name'],
            category=legacy_category,
            test_exercise=final_level['exercise_id'],
            level_index=final_level_index,
            levels_advanced_through=levels_advanced,
            prescribed_exercise_id=final_level['exercise_id'],
            prescribed_exercise_name=final_level['name'],
            reps_completed=reps_completed if action != 'cannot_do' else 0,
            difficulty_reported=max(1, min(10, difficulty)),
            pain_during=max(0, min(10, pain)),
            capability_level=capability,
            capability_numeric=cap_numeric,
            starting_sets=sets,
            starting_reps=reps,
            starting_phase=f'level_{final_level_index + 1}',
            notes=notes,
        )

        # ── Update (or create) PatientFamilyCapability ─────────────────────────
        # This is the live health profile that the prescription engine reads from
        import datetime as _dt
        pfc, _created = PatientFamilyCapability.objects.update_or_create(
            patient=patient,
            family_id=family['family_id'],
            defaults={
                'family_name': family['name'],
                'current_level_index': final_level_index,
                'current_exercise_id': final_level['exercise_id'],
                'current_exercise_name': final_level['name'],
                'capability_numeric': cap_numeric,
                'capability_string': capability,
                'prescribed_sets': sets,
                'prescribed_reps': reps,
                'prescribed_hold_duration': hold_dur,
                'weeks_at_current_level': 0,
                'sessions_at_current_level': 0,
                'consecutive_comfortable_sessions': 0,
                'ready_to_advance': (capability == 'easy'),
            }
        )

        # Log the gate test assessment in progression history
        history_entry = {
            'date': _dt.datetime.now().isoformat(),
            'type': 'gate_test',
            'level_index': final_level_index,
            'exercise_id': final_level['exercise_id'],
            'capability_numeric': cap_numeric,
            'capability_string': capability,
            'sets': sets,
            'reps': reps,
        }
        history = pfc.progression_history_json or []
        history.append(history_entry)
        pfc.progression_history_json = history
        pfc.save(update_fields=['progression_history_json'])

        # ── Update patient fitness_level_json with numeric + string per family ──
        fitness = patient.fitness_level_json or {}
        fitness[family['family_id']] = {
            'capability_numeric': cap_numeric,
            'capability_string': capability,
            'level_index': final_level_index,
            'exercise_id': final_level['exercise_id'],
        }
        patient.fitness_level_json = fitness
        patient.save(update_fields=['fitness_level_json'])

        # ── Update session ─────────────────────────────────────────────────────
        families[family_index]['status'] = 'completed'
        families[family_index]['result'] = {
            'exercise_id': final_level['exercise_id'],
            'exercise_name': final_level['name'],
            'level_index': final_level_index,
            'level_label': final_level['label'],
            'capability': capability,
            'sets': sets,
            'reps': reps,
            'hold_duration': hold_dur,
        }
        request.session['gate_families'] = families
        request.session.modified = True

        # ── Determine next URL ─────────────────────────────────────────────────
        next_family_index = family_index + 1
        if next_family_index >= len(families):
            next_url = '/gate-test-results/'
        else:
            next_url = f'/execute-gate-test/{next_family_index}/0/'

        return JsonResponse({
            'success': True,
            'next_url': next_url,
            'capability': capability,
            'prescribed_exercise': final_level['name'],
            'sets': sets,
            'reps': reps,
        })

    except Exception:
        logger.exception('Error in save_gate_test_result')
        return JsonResponse({'success': False, 'error': 'Something went wrong. Please try again.'}, status=500)


def gate_test_results(request: HttpRequest):
    """Display gate test results — one card per exercise family with prescribed exercise."""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')

    patient = get_object_or_404(PatientProfile, patient_id=patient_id)

    # Read completed families from session
    families = request.session.get('gate_families', [])

    # Also pull latest DB results (one per family, most recent)
    db_results = {}
    for dbr in GateTestResult.objects.filter(patient=patient).order_by('-test_date')[:12]:
        fid = dbr.exercise_family
        if fid and fid not in db_results:
            db_results[fid] = dbr

    if not families and not db_results:
        messages.error(request, 'No gate test results found.')
        return redirect('gate_testing')

    # Build rich results list for template
    results_list = []
    for f in families:
        result = f.get('result')
        if result:
            results_list.append({
                'family_id': f['family_id'],
                'family_name': f['name'],
                'icon': f['icon'],
                'status': f['status'],
                'prescribed_exercise': result.get('exercise_name', '—'),
                'level_label': result.get('level_label', '—'),
                'capability': result.get('capability', '—'),
                'sets': result.get('sets', 0),
                'reps': result.get('reps', 0),
                'hold_duration': result.get('hold_duration', 0),
                'levels_advanced': result.get('level_index', 0),
            })
        else:
            results_list.append({
                'family_id': f['family_id'],
                'family_name': f['name'],
                'icon': f['icon'],
                'status': f.get('status', 'skipped'),
                'prescribed_exercise': '—',
                'capability': 'skipped',
                'sets': 0, 'reps': 0,
            })

    # ── Mark gate tests as completed on the patient's health profile ────────
    # This persists in DB so the dashboard always shows the correct state
    # even after a server restart or session expiry.
    from django.utils import timezone as _tz
    completed_count_now = sum(1 for r in results_list if r['status'] == 'completed')
    if completed_count_now > 0:
        patient.gate_test_completed = True
        patient.gate_test_completed_at = _tz.now()
        patient.save(update_fields=['gate_test_completed', 'gate_test_completed_at'])

    # Clear session gate test data (keep patient_id)
    request.session.pop('gate_families', None)
    request.session.modified = True

    return render(request, 'strength_app/gate_test_results.html', {
        'patient': patient,
        'results_list': results_list,
        'completed_count': sum(1 for r in results_list if r['status'] == 'completed'),
        'total_count': len(results_list),
    })



def prescription(request: HttpRequest):
    """Generate AI-auto prescription"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')
    
    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    
    if request.method == 'POST':
        # Generate prescription using real backend
        prescription_data = generate_prescription(patient)
        
        # Convert ExerciseCategory enums to strings for JSON serialization
        # Sections that contain lists of exercise dicts
        EXERCISE_SECTIONS = {'stretching', 'strength', 'cardio', 'balance'}

        serializable_prescription = {}
        for section, value in prescription_data.items():
            if section not in EXERCISE_SECTIONS:
                # e.g. 'meta' is a plain dict, not a list — preserve as-is
                serializable_prescription[section] = value
                continue
            serializable_prescription[section] = []
            for exercise in value:
                if not isinstance(exercise, dict):
                    # Defensive: skip anything that isn't a dict
                    continue
                serializable_exercise = exercise.copy()
                # Convert category enum to string if needed
                if 'category' in serializable_exercise:
                    if hasattr(serializable_exercise['category'], 'value'):
                        serializable_exercise['category'] = serializable_exercise['category'].value
                serializable_prescription[section].append(serializable_exercise)
        
        # ── Persist prescription to DB (survives session loss / server restart) ─
        from django.utils import timezone as _tz
        patient.current_prescription_json = serializable_prescription
        patient.prescription_generated_at = _tz.now()
        # Ensure gate_test_completed is set (in case they arrived here directly)
        if not patient.gate_test_completed:
            from .models import PatientFamilyCapability
            if PatientFamilyCapability.objects.filter(patient=patient).exists():
                patient.gate_test_completed = True
                patient.gate_test_completed_at = _tz.now()
        patient.save(update_fields=[
            'current_prescription_json', 'prescription_generated_at',
            'gate_test_completed', 'gate_test_completed_at',
        ])

        # Also store in session for fast access during the current session
        request.session['prescription'] = serializable_prescription

        return render(request, 'strength_app/prescription_display.html', {
            'patient': patient,
            'prescription': serializable_prescription
        })
    
    return render(request, 'strength_app/prescription.html', {
        'patient': patient
    })


# ============================================================================
# WORKOUT EXECUTION
# ============================================================================

def daily_workout(request: HttpRequest):
    """Start workout - shows exercise list and preparation"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')
    
    patient = get_object_or_404(PatientProfile, patient_id=patient_id)

    # V1 patients (have StrengthProfile) use the V1 session flow
    from .models import StrengthProfile
    if StrengthProfile.objects.filter(patient=patient).exists():
        return redirect('v1_session_overview')

    # A4 (2026-07 exam): the legacy workout list only led to the retired
    # exercise_execute camera page (see execute_exercise). Pre-v1 patients
    # complete v1 onboarding instead — same destination the login flow
    # already gives them.
    return redirect('onboarding_start')


def execute_exercise(request: HttpRequest, exercise_index: int):
    """A4 (2026-07 exam): legacy camera page RETIRED. exercise_execute.html
    squat-scored every exercise and painted red for poor form — both locked-
    rule violations (ledger A4; same defect class as the removed server-side
    analyze_frame stack, 2026-06 C1). Patients route to the honest v1 flow;
    the pre-v1 cohort (no StrengthProfile) completes v1 onboarding instead."""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')

    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    from .models import StrengthProfile
    if StrengthProfile.objects.filter(patient=patient).exists():
        return redirect('v1_execute_exercise', exercise_index=exercise_index)
    return redirect('onboarding_start')



@rate_limit(max_attempts=60, window_seconds=60, key_prefix='save_exercise')  # R2-W5
def save_exercise_results(request: HttpRequest):
    """Save results from a single exercise execution"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            patient_id = request.session.get('patient_id')
            exercise_index = data.get('exercise_index')
            
            # Store results in session
            if 'exercise_results' not in request.session:
                request.session['exercise_results'] = []
            
            exercise_results = request.session.get('exercise_results', [])
            exercise_results.append({
                'exercise_index': exercise_index,
                'green_reps': data.get('green_reps', 0),
                'yellow_reps': data.get('yellow_reps', 0),
                'red_reps': data.get('red_reps', 0),
                'form_score': data.get('form_score', 0),
                'sets_completed': data.get('sets_completed', 0),
                'practice_mode': data.get('practice_mode', False)
            })
            
            request.session['exercise_results'] = exercise_results
            request.session.modified = True
            
            return JsonResponse({'success': True})
        except Exception:
            logger.exception('Error saving exercise results')
            return JsonResponse({'success': False, 'error': 'Could not save results. Please try again.'}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request'})


def workout_complete(request: HttpRequest):
    """Show workout complete page and collect feedback"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')
    
    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    
    if request.method == 'POST':
        # Collect post-workout feedback
        comfortable = request.POST.get('comfortable') == 'yes'
        difficulty = int(request.POST.get('difficulty_rating', 3))
        notes = request.POST.get('notes', '')
        
        # Get exercise results
        exercise_results = request.session.get('exercise_results', [])
        
        # Create workout session in database
        total_green = sum(r.get('green_reps', 0) for r in exercise_results)
        total_yellow = sum(r.get('yellow_reps', 0) for r in exercise_results)
        total_red = sum(r.get('red_reps', 0) for r in exercise_results)
        
        form_scores = [r.get('form_score', 0) for r in exercise_results if r.get('form_score', 0) > 0]
        avg_form = sum(form_scores) / len(form_scores) if form_scores else 0
        
        session = WorkoutSession.objects.create(
            patient=patient,
            week_number=patient.current_week or 1,
            total_duration_minutes=30,
            total_exercises_completed=len(exercise_results),
            total_green_reps_all=total_green,
            overall_session_form_score=avg_form,
            patient_comfortable=comfortable,
            difficulty_rating=difficulty,
            patient_notes=notes,
            prescription_mode=patient.prescription_mode
        )
        
        # Save individual exercise executions
        all_exercises = request.session.get('workout_exercises', [])
        for result in exercise_results:
            idx = result.get('exercise_index', 0)
            if idx < len(all_exercises):
                exercise = all_exercises[idx]
                ExerciseExecution.objects.create(
                    session=session,
                    exercise_id=exercise['exercise_id'],
                    exercise_name=exercise['exercise_name'],
                    category=exercise['type'],
                    prescribed_sets=exercise['sets'],
                    prescribed_reps=exercise['reps'],
                    total_green_reps=result.get('green_reps', 0),
                    total_yellow_reps=result.get('yellow_reps', 0),
                    total_red_reps=result.get('red_reps', 0),
                    # Legacy CV flow: per-rep colors came from the
                    # (since-removed) analyze_frame classification (DA-C12).
                    rep_quality_source='cv',
                    overall_form_score=result.get('form_score', 0),
                    completion_percentage=100 if result.get('green_reps', 0) >= exercise['reps'] else 0
                )
        
        # Clear session data
        request.session.pop('workout_exercises', None)
        request.session.pop('exercise_results', None)
        request.session.pop('current_exercise_index', None)
        
        # ── Progressive Loading: update PatientFamilyCapability after session ──
        _update_capability_after_session(patient, comfortable, difficulty, exercise_results)

        messages.success(request, 'Workout completed successfully!')
        return redirect('dashboard')
    
    # GET request - show summary
    exercise_results = request.session.get('exercise_results', [])
    all_exercises = request.session.get('workout_exercises', [])
    
    return render(request, 'strength_app/workout_complete.html', {
        'patient': patient,
        'exercise_results': exercise_results,
        'all_exercises': all_exercises
    })


# ============================================================================
# COMPUTER VISION — all pose analysis is client-side MediaPipe JS
# (v1_exercise_execute.html). The legacy server-side analyze_frame stack
# was removed in the 2026-06 health sweep (C1) — git history has it;
# the desktop runner path lives in strength_app/exercise_system/.
# ============================================================================

# ============================================================================
# PROGRESS REPORTS
# ============================================================================

def progress_reports(request: HttpRequest):
    """View progress reports"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')
    
    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    reports = ProgressReport.objects.filter(patient=patient).order_by('-report_date')[:100]  # B-P2: bounded
    
    return render(request, 'strength_app/progress_reports.html', {
        'patient': patient,
        'reports': reports
    })


# ============================================================================
# EXERCISE LIBRARY
# ============================================================================

def exercise_library(request: HttpRequest):
    """Browse all 68 exercises in the VYAYAM registry, organised by category."""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')

    patient = get_object_or_404(PatientProfile, patient_id=patient_id)

    from .exercise_system.exercise_registry_v2 import EXERCISE_METADATA, get_exercise_count

    # get_exercises_by_category returns class *instances* (EXERCISE_REGISTRY),
    # but the template needs metadata fields (display_name, level, unilateral,
    # new_in_v2). Pass the metadata dict directly — it has everything the
    # template reads, and no instantiation is needed for the library view.
    def _by_category(cat):
        return {
            key: meta
            for key, meta in EXERCISE_METADATA.items()
            if meta['category'] == cat
        }

    return render(request, 'strength_app/exercise_library.html', {
        'patient': patient,
        'counts':               get_exercise_count(),
        'strength_exercises':   _by_category('strength'),
        'cardio_exercises':     _by_category('cardio'),
        'stretching_exercises': _by_category('stretching'),
        'balance_exercises':    _by_category('balance'),
        'mobility_exercises':   _by_category('mobility'),
    })


# ============================================================================
# HOME
# ============================================================================

def home(request: HttpRequest):
    """Homepage — always clears any stale patient session"""
    if request.session.get('patient_id'):
        request.session.flush()
    return render(request, 'strength_app/home.html')

# ============================================================================
# AUTHENTICATION - LOGOUT (ADDED)
# ============================================================================

def patient_logout(request: HttpRequest):
    """Log out the current patient"""
    request.session.flush()
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


# ============================================================================
# REGISTRATION ALIAS (for template compatibility)
# ============================================================================

# Create alias - templates use 'register_patient' but function is 'patient_register'
register_patient = patient_register


# ============================================================================
# PROGRESS REPORTS - ADDITIONAL VIEWS (ADDED)
# ============================================================================

def generate_report(request: HttpRequest):
    """Generate a new progress report"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        messages.error(request, 'Please log in to generate reports')
        return redirect('patient_login')
    
    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    
    try:
        from .utils import generate_progress_report as gen_report
        # DA-C7: correct signature — was gen_report(patient.patient_id,
        # weeks=4), whose TypeError silently routed EVERY report through a
        # fallback with fabricated numbers (75% adherence, 20 prescribed).
        report = gen_report(patient, weeks=4)
        messages.success(request, 'Progress report generated successfully!')
        return redirect('view_report', report_id=report.id)
    except Exception:
        logging.getLogger(__name__).exception(
            'generate_progress_report failed for %s', patient.patient_id
        )
        # True-failure fallback: never invent numbers (DA-C7) — zeroes +
        # insufficient-data copy only.
        report = ProgressReport.objects.create(
            patient=patient,
            report_period='Last 4 weeks',
            total_sessions_completed=0,
            total_sessions_prescribed=0,
            overall_adherence_rate=0.0,
            total_green_reps_period=0,
            average_form_score_period=0.0,
            form_improvement=0.0,
            continue_current_program=True,
            patient_feedback_summary='Report generation failed — data unavailable.',
            recommended_next_steps=(
                'Insufficient data — the report could not be generated. '
                'Please try again later.'
            ),
        )
        messages.warning(request, 'Report generated with limited data.')
        return redirect('view_report', report_id=report.id)


def view_report(request: HttpRequest, report_id: int):
    """View a specific progress report"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        messages.error(request, 'Please log in to view reports')
        return redirect('patient_login')
    
    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    report = get_object_or_404(ProgressReport, id=report_id, patient=patient)
    
    context = {
        'patient': patient,
        'report': report,
    }
    
    return render(request, 'strength_app/view_report.html', context)


def download_report(request: HttpRequest, report_id: str):
    """Download progress report as text file"""
    from django.http import HttpResponse
    from datetime import datetime
    
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')
    
    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    report = get_object_or_404(ProgressReport, id=report_id, patient=patient)
    
    # Generate text report
    report_text = f"""
================================================================================
VYAYAM STRENGTH TRAINING - PROGRESS REPORT
================================================================================

PATIENT INFORMATION
────────────────────────────────────────────────────────────────────────────────
Name: {patient.name}
Age: {patient.age} years
Patient ID: {patient.patient_id}
Program Start: {patient.created_at.strftime('%B %d, %Y')}

REPORT PERIOD
────────────────────────────────────────────────────────────────────────────────
Report Date: {report.report_date.strftime('%B %d, %Y')}
Generated: {report.report_date.strftime('%B %d, %Y at %I:%M %p')}

OVERALL OUTCOMES
────────────────────────────────────────────────────────────────────────────────
Sessions Completed: {report.total_sessions_completed}/{report.total_sessions_prescribed}
Overall Adherence: {report.overall_adherence_rate:.1f}%
Total Green Reps: {report.total_green_reps_period}
Average Form Score: {report.average_form_score_period:.1f}%
Form Improvement: {report.form_improvement:+.1f}%

RECOMMENDATIONS
────────────────────────────────────────────────────────────────────────────────
Continue Current Program: {"Yes" if report.continue_current_program else "No"}
Next Steps: {report.recommended_next_steps}

================================================================================
END OF REPORT
================================================================================
"""
    
    # Create HTTP response
    response = HttpResponse(report_text, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="vyayam_report_{patient.patient_id}_{datetime.now().strftime("%Y%m%d")}.txt"'
    
    return response


# ============================================================================
# EXERCISE LIBRARY - ADDITIONAL VIEWS (ADDED)
# ============================================================================

def exercise_detail(request: HttpRequest, exercise_id: str):
    """View single exercise details"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')
    
    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    
    # Try to get exercise from registry
    try:
        from .exercise_system.exercise_registry_v2 import EXERCISE_METADATA
        exercise_info = EXERCISE_METADATA.get(exercise_id)
        if not exercise_info:
            messages.error(request, f'Exercise "{exercise_id}" not found')
            return redirect('exercise_library')
    except ImportError:
        # Fallback if registry not available
        exercise_info = {
            'display_name': exercise_id.replace('_', ' ').title(),
            'category': 'strength',
            'level': 'intermediate',
            'unilateral': False,
        }
    
    context = {
        'patient': patient,
        'exercise_id': exercise_id,
        'exercise': exercise_info,
    }
    
    return render(request, 'strength_app/exercise_detail.html', context)


def exercise_execute(request, exercise_id):
    """Execute exercise with camera (from exercise library) — V1 template with ghost + voice."""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')

    patient = get_object_or_404(PatientProfile, patient_id=patient_id)

    from .exercise_system.exercise_registry_v2 import EXERCISE_METADATA
    from .exercise_content import EXERCISE_CONTENT
    from .exercise_content_gap_fill import EXERCISE_CONTENT_GAP_FILL as EXERCISE_CONTENT_GAP

    meta = EXERCISE_METADATA.get(exercise_id, {})
    if not meta:
        messages.error(request, f'Exercise "{exercise_id}" not found')
        return redirect('exercise_library')

    content = EXERCISE_CONTENT.get(exercise_id) or EXERCISE_CONTENT_GAP.get(exercise_id) or {}

    tempo = str(meta.get('tempo', '3-1-2-0'))
    tempo_parts = tempo.split('-')
    while len(tempo_parts) < 4:
        tempo_parts.append('0')

    exercise = {
        'exercise_id': exercise_id,
        'exercise_name': meta.get('display_name', exercise_id.replace('_', ' ').title()),
        'movement_pattern': meta.get('movement_pattern', 'unknown'),
        'sets': 3,
        'reps': 10,
        'tempo': tempo,
        'tempo_parts': tempo_parts,
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
        'patient': patient,
        'exercise': exercise,
        'exercise_index': 0,
        'total_exercises': 1,
        'is_last_exercise': True,
        'has_strength_profile': True,
        'library_mode': True,
    }

    return render(request, 'strength_app/v1_exercise_execute.html', context)


# ============================================================================
# PRE-MATCH STRETCHING MODULE
# ============================================================================

from .stretching_protocol import PRE_MATCH_STRETCHES, TOTAL_STRETCHES, TOTAL_PROTOCOL_DURATION


def stretch_protocol(request: HttpRequest):
    """Overview of the pre-match stretching protocol + past sessions."""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')

    patient = get_object_or_404(PatientProfile, patient_id=patient_id)

    if request.method == 'POST':
        request.session['stretch_results'] = []
        return redirect('stretch_execute', stretch_index=0)

    past_sessions = StretchSession.objects.filter(patient=patient)[:10]

    context = {
        'patient': patient,
        'stretches': PRE_MATCH_STRETCHES,
        'total_stretches': TOTAL_STRETCHES,
        'total_duration': TOTAL_PROTOCOL_DURATION,
        'past_sessions': past_sessions,
    }
    return render(request, 'strength_app/stretch_protocol.html', context)


def stretch_execute(request: HttpRequest, stretch_index: int):
    """Camera page for a single stretch."""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')

    if stretch_index >= TOTAL_STRETCHES:
        return redirect('stretch_complete')

    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    stretch = PRE_MATCH_STRETCHES[stretch_index]
    is_last = stretch_index == TOTAL_STRETCHES - 1
    progress_percent = round((stretch_index / TOTAL_STRETCHES) * 100)

    context = {
        'patient': patient,
        'stretch': stretch,
        'stretch_index': stretch_index,
        'total_stretches': TOTAL_STRETCHES,
        'is_last_stretch': is_last,
        'progress_percent': progress_percent,
    }
    return render(request, 'strength_app/stretch_execute.html', context)



def save_stretch_result(request: HttpRequest):
    """AJAX POST — save one stretch result and return the next URL."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    patient_id = request.session.get('patient_id')
    if not patient_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    stretch_index = data.get('stretch_index', 0)
    stretch = PRE_MATCH_STRETCHES[stretch_index] if stretch_index < TOTAL_STRETCHES else {}

    result = {
        'stretch_id': stretch.get('stretch_id', ''),
        'name': stretch.get('name', ''),
        'side': stretch.get('side', ''),
        'muscle_group': stretch.get('muscle_group', ''),
        'prescribed_duration': stretch.get('duration_seconds', 0),
        'actual_duration': data.get('actual_duration', 0),
        'completed': data.get('completed', False),
        'posture_note': data.get('posture_note', ''),
        'camera_used': data.get('camera_used', False),
    }

    results = request.session.get('stretch_results', [])
    results.append(result)
    request.session['stretch_results'] = results
    request.session.modified = True

    next_index = stretch_index + 1
    if next_index >= TOTAL_STRETCHES:
        next_url = '/stretch-complete/'
    else:
        next_url = f'/stretch-execute/{next_index}/'

    return JsonResponse({'success': True, 'next_url': next_url})


def stretch_complete(request: HttpRequest):
    """Read session results, persist to DB, show summary."""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')

    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    results = request.session.pop('stretch_results', [])

    stretches_completed = sum(1 for r in results if r.get('completed'))
    total_duration = sum(r.get('actual_duration', 0) for r in results)
    camera_used = any(r.get('camera_used') for r in results)

    session_obj = StretchSession.objects.create(
        patient=patient,
        total_stretches=TOTAL_STRETCHES,
        stretches_completed=stretches_completed,
        total_duration_seconds=total_duration,
        stretch_results_json=results,
        camera_used=camera_used,
    )

    context = {
        'patient': patient,
        'session': session_obj,
        'results': results,
        'stretches_completed': stretches_completed,
        'total_stretches': TOTAL_STRETCHES,
        'total_duration': total_duration,
        'camera_used': camera_used,
    }
    return render(request, 'strength_app/stretch_complete.html', context)


# ============================================================================
# LEGAL PAGES
# ============================================================================

def privacy_policy(request: HttpRequest):
    return render(request, 'strength_app/privacy_policy.html')


def terms_of_service(request: HttpRequest):
    return render(request, 'strength_app/terms_of_service.html')


def disclaimer(request: HttpRequest):
    return render(request, 'strength_app/disclaimer.html')


def delete_account(request: HttpRequest):
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')

    patient = get_object_or_404(PatientProfile, patient_id=patient_id)

    # B-X1 (2026-07 exam): a therapist-managed patient's account anchors the
    # therapist's clinical record — generated SessionReports and the
    # PainEvent/RedFlagEvent audit trails all CASCADE off PatientProfile, and
    # reports are clinically immutable. Managed deletion goes through the
    # therapist (retention-vs-erasure policy: MENTOR_REVIEW_QUEUE §2026-07).
    if patient.therapist_managed:
        if request.method == 'POST':
            messages.error(
                request,
                'Your account is managed by your therapist, so it cannot be '
                'deleted from here. Please ask your therapist to close your '
                'account — this protects your treatment records.')
        return render(request, 'strength_app/delete_account.html',
                      {'managed_blocked': True})

    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirmed = request.POST.get('confirm_delete')
        if not confirmed:
            messages.error(request, 'Please tick the confirmation checkbox.')
            return render(request, 'strength_app/delete_account.html')
        from django.contrib.auth.hashers import check_password as _check
        if not _check(password, patient.password):
            messages.error(request, 'Incorrect password. Account not deleted.')
            return render(request, 'strength_app/delete_account.html')
        # B-X2 defense in depth: SessionReport FKs are PROTECT — a profile
        # that somehow carries generated reports (e.g. was managed once)
        # cannot be cascade-deleted even from here.
        from django.db import transaction
        from django.db.models import ProtectedError
        try:
            with transaction.atomic():
                patient.delete()
        except ProtectedError:
            messages.error(
                request,
                'Your account has treatment records with a therapist and '
                'cannot be deleted from here. Please ask your therapist to '
                'close your account.')
            return render(request, 'strength_app/delete_account.html',
                          {'managed_blocked': True})
        request.session.flush()
        messages.success(request, 'Your account and all associated data have been permanently deleted.')
        return redirect('home')

    return render(request, 'strength_app/delete_account.html')


def stretch_download_pdf(request: HttpRequest, session_id: int):
    """Generate and stream the PDF report for a StretchSession."""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_login')

    patient = get_object_or_404(PatientProfile, patient_id=patient_id)
    session_obj = get_object_or_404(StretchSession, id=session_id, patient=patient)

    from .stretch_pdf import generate_stretch_pdf
    buffer = generate_stretch_pdf(patient, session_obj)

    date_str = session_obj.session_date.strftime('%Y%m%d')
    filename = f'vyayam_stretch_report_{patient.patient_id}_{date_str}.pdf'

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@rate_limit(max_attempts=5, window_seconds=300, key_prefix='change_password')
def change_password(request):
    """Lets a logged-in patient change their own password (current + new + confirm)."""
    from django.contrib.auth.hashers import make_password
    pid = request.session.get('patient_id')
    if not pid:
        return redirect('patient_login')
    patient = PatientProfile.objects.filter(patient_id=pid).first()
    if not patient:
        return redirect('patient_login')
    error = None
    success = False
    if request.method == 'POST':
        old = request.POST.get('old_password', '')
        new = request.POST.get('new_password', '')
        confirm = request.POST.get('confirm_password', '')
        if not check_password(old, patient.password):
            error = 'Current password is incorrect.'
        elif len(new) < 8:
            error = 'New password must be at least 8 characters.'
        elif new.isdigit() or new.isalpha():
            error = 'New password must mix letters and numbers.'
        elif new != confirm:
            error = 'New passwords do not match.'
        else:
            patient.password = make_password(new)
            patient.must_change_password = False  # R2-U1: temp-password flow complete
            patient.save(update_fields=['password', 'must_change_password'])
            # DA-P6: rotate the session key after a credential change.
            # (Cross-session invalidation is a known limitation — patient
            # auth is session-based without a server-side token registry.)
            request.session.cycle_key()
            success = True
    return render(request, 'strength_app/change_password.html', {'error': error, 'success': success})
