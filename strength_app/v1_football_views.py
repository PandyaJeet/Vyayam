"""
VYAYAM Football Module — Views
Sport selection, 8-test assessment battery (6 scored + 2 manual-entry
strength tests), results & level assignment.
"""

import json
from datetime import date

from django.http import JsonResponse
from .rate_limiter import rate_limit
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

from .models import PatientProfile, FootballProfile
from .v1_football_constants import (
    SPORT_TYPES, FOOTBALL_ASSESSMENT_TESTS, FOOTBALL_LEVELS,
    FV_TENDENCY_CONFIG,
)


def _get_patient(request):
    pid = request.session.get('patient_id')
    if not pid:
        return None, redirect('patient_login')
    try:
        return PatientProfile.objects.get(patient_id=pid), None
    except PatientProfile.DoesNotExist:
        return None, redirect('patient_login')


# ============================================================================
# SPORT SELECTION — shown after onboarding if athlete_tier_eligible
# ============================================================================

def football_sport_select(request):
    patient, err = _get_patient(request)
    if err:
        return err

    if not patient.athlete_tier_eligible:
        return redirect('v1_session_overview')

    # SPORT_TYPES is a list of (key, label) tuples
    valid_sport_keys = {key for key, _ in SPORT_TYPES}

    if request.method == 'POST':
        sport = request.POST.get('sport', '')
        if sport in valid_sport_keys:
            patient.athlete_sport = sport
            patient.save(update_fields=['athlete_sport'])
            return redirect('football_assessment')
        elif request.POST.get('skip') == '1':
            return redirect('v1_session_overview')

    sports = [{'key': key, 'label': label} for key, label in SPORT_TYPES]

    return render(request, 'strength_app/football_sport_select.html', {
        'patient': patient,
        'sports': sports,
    })


# ============================================================================
# FOOTBALL ASSESSMENT — intro page listing 6 tests
# ============================================================================

def football_assessment(request):
    patient, err = _get_patient(request)
    if err:
        return err

    if not patient.athlete_tier_eligible:
        return redirect('v1_session_overview')

    if request.method == 'POST':
        request.session['football_test_results'] = {}
        request.session['football_season_phase'] = request.POST.get('season_phase', 'in_season')
        return redirect(reverse('football_assessment_execute', args=[0]))

    return render(request, 'strength_app/football_assessment.html', {
        'patient': patient,
        'tests': FOOTBALL_ASSESSMENT_TESTS,
        'total_tests': len(FOOTBALL_ASSESSMENT_TESTS),
    })


# ============================================================================
# ASSESSMENT EXECUTE — one test at a time
# ============================================================================

def football_assessment_execute(request, test_index):
    patient, err = _get_patient(request)
    if err:
        return err

    if not patient.athlete_tier_eligible:
        return redirect('v1_session_overview')

    if test_index >= len(FOOTBALL_ASSESSMENT_TESTS):
        return redirect('football_assessment_results')

    test = FOOTBALL_ASSESSMENT_TESTS[test_index]
    side = request.GET.get('side', '')
    # C6 (2026-07 exam): side renders into inline JS — whitelist for every
    # test, not just the bilateral redirect below.
    if side not in ('left', 'right'):
        side = ''
    is_bilateral = test.get('is_bilateral', False)

    # Bilateral tests: redirect to ?side=left if no side specified
    if is_bilateral and side not in ('left', 'right'):
        return redirect(
            reverse('football_assessment_execute', args=[test_index]) + '?side=left'
        )

    progress_pct = round((test_index / len(FOOTBALL_ASSESSMENT_TESTS)) * 100)
    scoring_items = [
        {'score': k, 'desc': v}
        for k, v in sorted(test.get('scoring', {}).items())
    ]

    # Strength tests are equipment-dependent — offer a no-write skip so an
    # athlete without a bench/leg press can still finish the battery.
    skip_url = ''
    if test.get('entry_mode') == 'strength_manual':
        next_index = test_index + 1
        skip_url = (
            reverse('football_assessment_results')
            if next_index >= len(FOOTBALL_ASSESSMENT_TESTS)
            else reverse('football_assessment_execute', args=[next_index])
        )

    return render(request, 'strength_app/football_assessment_execute.html', {
        'test': test,
        'test_index': test_index,
        'total_tests': len(FOOTBALL_ASSESSMENT_TESTS),
        'side': side,
        'is_bilateral': is_bilateral,
        'progress_pct': progress_pct,
        'scoring_items': scoring_items,
        'skip_url': skip_url,
        'patient': patient,
    })


# ============================================================================
# AJAX: SAVE FOOTBALL TEST RESULT
# ============================================================================

@rate_limit(max_attempts=60, window_seconds=60, key_prefix='football_save')  # DA-P6
def football_save_test_result(request):
    # G4-2 fix: reject anonymous writes before touching the session.
    if not request.session.get('patient_id'):
        return JsonResponse({'error': 'Authentication required'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    # Athlete-tier guard (parity with the navigational football views): an
    # ineligible authenticated patient must not write assessment state by
    # POSTing directly to this AJAX endpoint.
    patient = PatientProfile.objects.filter(
        patient_id=request.session['patient_id']
    ).first()
    if patient is None or not patient.athlete_tier_eligible:
        return JsonResponse({'error': 'Not eligible'}, status=403)

    try:
        data = json.loads(request.body)
    except Exception:
        data = {k: v for k, v in request.POST.items()}

    from .validation import safe_int
    # DA-P4: clamp — junk must not 500; negative index would silently
    # read FOOTBALL_ASSESSMENT_TESTS[-1].
    test_index = safe_int(data.get('test_index', 0), 0, 0, len(FOOTBALL_ASSESSMENT_TESTS) - 1)
    raw_value = str(data.get('raw_value', ''))[:100]
    score = safe_int(data.get('score', 0), 0, 0, 5)
    side = str(data.get('side', ''))

    if 'football_test_results' not in request.session:
        request.session['football_test_results'] = {}

    results = dict(request.session['football_test_results'])
    test = FOOTBALL_ASSESSMENT_TESTS[test_index] if test_index < len(FOOTBALL_ASSESSMENT_TESTS) else {}
    key = test.get('test_id', f'test_{test_index}')

    # Tests 7 & 8 (bench/leg press): weight×reps manual entry. Epley e1RM is
    # computed HERE (server-side, authoritative) — the client preview is
    # display-only. No 0-5 score: these never enter football_level (SB-5a).
    if test.get('entry_mode') == 'strength_manual':
        from .validation import safe_float
        weight_kg = safe_float(data.get('weight_kg', 0), 0, 0, 500)
        reps = safe_int(data.get('reps', 0), 0, 0, 30)
        if weight_kg <= 0 or reps <= 0:
            return JsonResponse({'error': 'Weight and reps are required'}, status=400)
        e1rm = round(weight_kg * (1 + reps / 30.0), 1)
        results[key] = {'weight_kg': weight_kg, 'reps': reps, 'e1rm': e1rm}
        request.session['football_test_results'] = results
        request.session.modified = True
        next_index = test_index + 1
        next_url = (
            reverse('football_assessment_results')
            if next_index >= len(FOOTBALL_ASSESSMENT_TESTS)
            else reverse('football_assessment_execute', args=[next_index])
        )
        return JsonResponse({'status': 'saved', 'next_url': next_url, 'e1rm': e1rm})

    if side in ('left', 'right'):
        sub = results.get(key, {})
        if not isinstance(sub, dict):
            sub = {}
        sub[side] = {'score': score, 'raw': raw_value}
        results[key] = sub
    else:
        results[key] = {'score': score, 'raw': raw_value}

    request.session['football_test_results'] = results
    request.session.modified = True

    # Determine next URL
    is_bilateral = test.get('is_bilateral', False)
    next_index = test_index + 1
    done_url = reverse('football_assessment_results')
    next_test_url = (
        done_url if next_index >= len(FOOTBALL_ASSESSMENT_TESTS)
        else reverse('football_assessment_execute', args=[next_index])
    )

    if is_bilateral and side == 'left':
        next_url = reverse('football_assessment_execute', args=[test_index]) + '?side=right'
    else:
        next_url = next_test_url

    return JsonResponse({'status': 'saved', 'next_url': next_url})


# ============================================================================
# SCORE CALCULATION HELPER
# ============================================================================

def _score_from_thresholds(test, raw_value):
    """
    Calculate score 1-5 from raw value using test scoring_thresholds.
    scoring_thresholds is a list of 4 boundary values [t1, t2, t3, t4].
    score = index of first threshold that raw_value does NOT clear + 1.
    """
    try:
        val = float(raw_value)
    except (ValueError, TypeError):
        return 1

    thresholds = test.get('scoring_thresholds', [])
    if not thresholds:
        return int(test.get('scoring', {}).get(1, 1))

    is_reverse = test.get('scoring_thresholds_reverse', False)

    if is_reverse:
        # Lower is better (sprint times, COD times)
        # t1=4.0, t2=3.70, t3=3.40, t4=3.09
        # val > t1 → score 1, val > t2 → score 2 ... val ≤ t4 → score 5
        for i, t in enumerate(thresholds):
            if val > t:
                return i + 1
        return 5
    else:
        # Higher is better (distance, reps, percentage)
        # val < t1 → score 1, val < t2 → score 2 ... val ≥ t4 → score 5
        for i, t in enumerate(thresholds):
            if val < t:
                return i + 1
        return 5


# ============================================================================
# ASSESSMENT RESULTS — compute level, LSI, F-V tendency
# ============================================================================

def football_assessment_results(request):
    patient, err = _get_patient(request)
    if err:
        return err

    if not patient.athlete_tier_eligible:
        return redirect('v1_session_overview')

    results = request.session.get('football_test_results', {})
    if not results:
        return redirect('football_assessment')

    fp, _ = FootballProfile.objects.get_or_create(patient=patient)
    test_map = {t['test_id']: t for t in FOOTBALL_ASSESSMENT_TESTS}

    def _raw(entry, key='raw'):
        if isinstance(entry, dict):
            return entry.get(key, 0)
        return entry or 0

    # --- Hop (bilateral) ---
    hop_data = results.get('hop_test', {})
    if isinstance(hop_data, dict) and 'left' in hop_data:
        fp.hop_left_cm = float(_raw(hop_data['left']))
        fp.hop_right_cm = float(_raw(hop_data['right']))
        best = max(fp.hop_left_cm, fp.hop_right_cm)
        fp.hop_score = _score_from_thresholds(test_map['hop_test'], best)
    elif isinstance(hop_data, dict) and 'score' in hop_data:
        fp.hop_score = int(hop_data['score'])

    # --- Nordic ---
    nordic_data = results.get('nordic_test', {})
    if isinstance(nordic_data, dict):
        fp.nordic_seconds = float(_raw(nordic_data))
        fp.nordic_score = _score_from_thresholds(test_map['nordic_test'], fp.nordic_seconds)

    # --- Sprint ---
    sprint_data = results.get('sprint_test', {})
    if isinstance(sprint_data, dict):
        fp.sprint_seconds = float(_raw(sprint_data))
        fp.sprint_score = _score_from_thresholds(test_map['sprint_test'], fp.sprint_seconds)

    # --- Pogo ---
    pogo_data = results.get('pogo_test', {})
    if isinstance(pogo_data, dict):
        fp.pogo_clean_reps = int(float(_raw(pogo_data)))
        fp.pogo_score = _score_from_thresholds(test_map['pogo_test'], fp.pogo_clean_reps)

    # --- COD (bilateral) ---
    cod_data = results.get('cod_test', {})
    if isinstance(cod_data, dict) and 'left' in cod_data:
        fp.cod_left_seconds = float(_raw(cod_data['left']))
        fp.cod_right_seconds = float(_raw(cod_data['right']))
        best_cod = min(fp.cod_left_seconds, fp.cod_right_seconds)  # lower is better
        fp.cod_score = _score_from_thresholds(test_map['cod_test'], best_cod)
    elif isinstance(cod_data, dict) and 'score' in cod_data:
        fp.cod_score = int(cod_data['score'])

    # --- Y-Balance (bilateral) ---
    yb_data = results.get('ybalance_test', {})
    if isinstance(yb_data, dict) and 'left' in yb_data:
        fp.ybalance_left_pct = float(_raw(yb_data['left']))
        fp.ybalance_right_pct = float(_raw(yb_data['right']))
        best_yb = max(fp.ybalance_left_pct, fp.ybalance_right_pct)
        fp.ybalance_score = _score_from_thresholds(test_map['ybalance_test'], best_yb)
    elif isinstance(yb_data, dict) and 'score' in yb_data:
        fp.ybalance_score = int(yb_data['score'])

    # Compute derived fields
    fp.compute_level()
    fp.compute_lsi()
    fp.compute_fv_tendency()
    fp.check_plyometric_gate()
    fp.season_phase = request.session.pop('football_season_phase', 'in_season')
    fp.save()

    # Tests 7 & 8 (bench/leg press, 2026-07 Part 3): persist to
    # raw_test_data_json — store-and-display ONLY. Deliberately kept out of
    # football_level / compute_level(): that scoring has known deferred bugs
    # (SB-5a) and must not gain new inputs this cycle.
    strength_tests = {}
    for sid, label in (('bench_press_test', 'bench_press'),
                       ('leg_press_test', 'leg_press')):
        entry = results.get(sid)
        if isinstance(entry, dict) and entry.get('e1rm'):
            rec = {
                'weight_kg': entry.get('weight_kg'),
                'reps': entry.get('reps'),
                'e1rm': entry.get('e1rm'),
                'tested_at': str(date.today()),
            }
            # Optional relative strength — only when bodyweight is on file.
            if patient.weight_kg:
                rec['rel_bw'] = round(entry['e1rm'] / patient.weight_kg, 2)
            strength_tests[label] = rec
    if strength_tests:
        raw = patient.raw_test_data_json if isinstance(patient.raw_test_data_json, dict) else {}
        merged = dict(raw.get('strength_tests') or {})
        merged.update(strength_tests)
        raw['strength_tests'] = merged
        patient.raw_test_data_json = raw

    # Mark patient as athlete tier active
    patient.athlete_tier_active = True
    patient.save(update_fields=['athlete_tier_active', 'raw_test_data_json'])

    level_config = FOOTBALL_LEVELS.get(fp.football_level, FOOTBALL_LEVELS[1])
    fv_config = FV_TENDENCY_CONFIG.get(fp.fv_tendency, FV_TENDENCY_CONFIG['balanced'])

    test_scores = [
        {'name': 'Single-Leg Hop',     'score': fp.hop_score,     'icon': 'fas fa-shoe-prints'},
        {'name': 'Nordic Hold',         'score': fp.nordic_score,  'icon': 'fas fa-dumbbell'},
        {'name': '20 m Sprint',         'score': fp.sprint_score,  'icon': 'fas fa-bolt'},
        {'name': 'Pogo Reactivity (app metric)', 'score': fp.pogo_score, 'icon': 'fas fa-arrow-up'},  # R2-W2-1: never 'RSI'
        {'name': 'COD 505',             'score': fp.cod_score,     'icon': 'fas fa-random'},
        {'name': 'Y-Balance',           'score': fp.ybalance_score,'icon': 'fas fa-balance-scale'},
    ]

    return render(request, 'strength_app/football_assessment_results.html', {
        'patient': patient,
        'fp': fp,
        'level_config': level_config,
        'fv_config': fv_config,
        'test_scores': test_scores,
        'lsi_flag': fp.lsi_flag,
        'lsi_hop': fp.hop_lsi_pct,
        'lsi_ybalance': fp.ybalance_lsi_pct,
        'plyometric_cleared': fp.plyometric_cleared,
    })


# ============================================================================
# FOOTBALL REASSESSMENT — periodic re-test every 4 weeks
# ============================================================================

def football_reassessment_check(patient):
    """
    Return True if the patient is due for a football reassessment (4+ weeks
    since last assessment or last_reassessment). Called from dashboard view.
    """
    try:
        fp = patient.football_profile
    except Exception:
        return False

    reference = fp.last_reassessment or fp.assessed_at
    if not reference:
        return False

    weeks_since = (timezone.now() - reference).days / 7
    return weeks_since >= 4


def football_update_after_session(patient):
    """
    Called after each workout session completes.
    Updates HSR weeks tracking, re-checks plyometric gate, and records
    last activity timestamp for reassessment scheduling.
    """
    try:
        fp = patient.football_profile
    except Exception:
        return

    # Track weeks completed in the CURRENT HSR phase, anchored to phase start (SB-5b fix).
    # Old `current_week % 4` capped this at 0-3 so the >=4 advance gate never fired.
    try:
        state = patient.periodisation
        # DA-P4: 'is None' semantics — the falsy check re-anchored every
        # session when the phase began at week 0, freezing weeks_in_phase
        # at 0 so the >=4-week HSR advance gate never fired.
        if fp.hsr_phase_start_week is None:
            fp.hsr_phase_start_week = state.current_week
        weeks_in_phase = max(0, state.current_week - fp.hsr_phase_start_week)
        fp.hsr_weeks_completed = max(fp.hsr_weeks_completed, weeks_in_phase)
    except Exception:
        pass

    # Re-check plyometric gate
    fp.check_plyometric_gate()

    # If no SLS (single-leg squat) capability, keep plyometrics locked
    try:
        sp = patient.strength_profiles.order_by('-assessed_at').first()
        if sp and sp.squat_score < 4:
            fp.plyometric_cleared = 'none'
    except Exception:
        pass

    fp.save(update_fields=['hsr_weeks_completed', 'hsr_phase_start_week', 'plyometric_cleared'])


# ============================================================================
# MATCH CALENDAR — P29 Microcycle Management
# ============================================================================

def match_calendar(request):
    """Display and manage upcoming match dates."""
    patient, err = _get_patient(request)
    if err:
        return err

    if not patient.athlete_tier_eligible:
        return redirect('v1_session_overview')

    from .models import MatchDate
    from datetime import date, timedelta

    today = date.today()
    matches = MatchDate.objects.filter(
        patient=patient,
        match_date__gte=today - timedelta(days=7)
    ).order_by('match_date')

    return render(request, 'strength_app/match_calendar.html', {
        'patient': patient,
        'matches': matches,
        'today': today,
    })


def match_add(request):
    """Add a match date via POST."""
    patient, err = _get_patient(request)
    if err:
        return err

    if not patient.athlete_tier_eligible:
        return redirect('v1_session_overview')

    if request.method != 'POST':
        return redirect('match_calendar')

    from .models import MatchDate
    from datetime import datetime

    match_date_str = request.POST.get('match_date', '')
    opponent = request.POST.get('opponent', '')

    if match_date_str:
        try:
            md = datetime.strptime(match_date_str, '%Y-%m-%d').date()
            MatchDate.objects.get_or_create(
                patient=patient,
                match_date=md,
                defaults={'opponent': opponent}
            )
        except (ValueError, Exception):
            pass

    return redirect('match_calendar')


def match_delete(request, match_id):
    """Delete a match date via POST."""
    patient, err = _get_patient(request)
    if err:
        return err

    if not patient.athlete_tier_eligible:
        return redirect('v1_session_overview')

    if request.method != 'POST':
        return redirect('match_calendar')

    from .models import MatchDate
    MatchDate.objects.filter(id=match_id, patient=patient).delete()
    return redirect('match_calendar')


def football_nordic_camera_test(request):
    """Standalone camera diagnostic for the Nordic break-point method.
    Read-only: shows live trunk tilt, body straightness, fall speed, deepest
    controlled tilt and a 1-5 score. Saves nothing. Login-gated.
    """
    patient, err = _get_patient(request)
    if err:
        return err
    if not patient.athlete_tier_eligible:
        return redirect('v1_session_overview')
    return render(request, 'strength_app/football_nordic_camera_test.html', {})
