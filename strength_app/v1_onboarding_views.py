"""
VYAYAM V1 — Onboarding Views (10-screen clinical assessment flow)

Screens:
  1. Start           onboarding_start
  2. Identity        onboarding_identity
  3. Training Hist.  onboarding_training_history
  4. Test Overview   onboarding_strength_test
  5. Test Execute    onboarding_strength_test_execute  (+save endpoint)
  6. Asymmetry       onboarding_asymmetry
  7. Goals           onboarding_goals
  8. Equipment       onboarding_equipment
  9. Hormonal        onboarding_hormonal  (female only)
 10. Red Flags       onboarding_red_flags
 11. Lifestyle       onboarding_lifestyle
 12. Mind-Muscle     onboarding_mind_muscle
 13. Complete        onboarding_complete
"""

import uuid
import re
import json
import logging
from datetime import date, datetime

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.hashers import make_password

from .models import PatientProfile, StrengthProfile, PeriodisationState
from .rate_limiter import rate_limit
from .v1_constants import GOAL_CONFIG, TRAINING_AGE_CONFIG
from .v1_football_constants import SPORT_TYPES, FOOTBALL_ASSESSMENT_TESTS
from .v1_safety_logic import compute_pattern_priorities, get_asymmetry_rules

TOTAL_ONBOARDING_STEPS = 10  # Default for males; females get 11

def _total_steps(patient):
    """Males = 10 steps (no hormonal), females = 11 steps."""
    if patient and getattr(patient, 'biological_sex', '') == 'female':
        return 11
    return 10

# ============================================================================
# 7 STRENGTH TESTS
# ============================================================================

V1_STRENGTH_TESTS = [
    {
        'index': 0,
        'test_id': 'squat_test',
        'name': 'Squat Assessment',
        'pattern': 'squat',
        'exercise': 'Bodyweight Squat Hold',
        'instructions': [
            'Stand with feet shoulder-width apart, toes slightly out.',
            'Squat as deep as comfortable.',
            'Hold the bottom position for 10 seconds.',
        ],
        'camera_view': 'front_and_side',
        'duration_seconds': 30,
        'is_bilateral': False,
        'scoring': {
            1: 'Holds under 5 seconds',
            2: 'Holds 5 to 15 seconds',
            3: 'Holds 15 to 25 seconds',
            4: 'Holds 30 seconds with good form',
            5: 'Holds 60 seconds with good form',
        },
    },
    {
        'index': 1,
        'test_id': 'hinge_test',
        'name': 'Hinge Assessment',
        'pattern': 'hinge',
        'exercise': 'Single Leg RDL Hold',
        'instructions': [
            'Stand on your dominant leg, hands on hips.',
            'Hinge forward keeping spine neutral.',
            'Hold when torso approaches horizontal, 5 seconds.',
            'Repeat on the other leg.',
        ],
        'camera_view': 'side',
        'duration_seconds': 30,
        'is_bilateral': True,
        'scoring': {
            1: 'Cannot balance on one leg for 5 seconds',
            2: 'Balances but back rounds when bending',
            3: 'Bends halfway with straight back',
            4: 'Bends fully, back straight, holds 5s',
            5: 'Perfect both sides, holds easily',
        },
    },
    {
        'index': 2,
        'test_id': 'push_test',
        'name': 'Push Assessment',
        'pattern': 'push',
        'exercise': 'Max Push-Ups in 60 Seconds',
        'instructions': [
            'Start in full plank position, hands shoulder-width.',
            'Chest must touch the floor for each rep to count.',
            'Complete as many strict push-ups as possible in 60 seconds.',
        ],
        'camera_view': 'side',
        'duration_seconds': 60,
        'is_bilateral': False,
        'scoring': {
            1: '0–4 reps (or 0–2 for female)',
            2: '5–14 reps (or 3–9)',
            3: '15–24 reps (or 10–17)',
            4: '25–34 reps (or 18–25)',
            5: '35+ reps (or 26+)',
        },
    },
    {
        'index': 3,
        'test_id': 'pull_test',
        'name': 'Pull Assessment',
        'pattern': 'pull',
        'has_variants': True,
        'variant_question': 'What can you hang from or pull against?',
        'variants': {
            'bar': {
                'label': 'Yes — pull-up bar available',
                'exercise': 'Dead Hang Hold',
                'instructions': [
                    'Grip a pull-up bar with arms fully extended.',
                    'Pack your shoulders — do not shrug into your ears.',
                    'Hold as long as possible without bending elbows.',
                ],
                'duration_seconds': 60,
                'scoring': {
                    1: 'Cannot hold 5 seconds',
                    2: '5–15 seconds',
                    3: '15–30 seconds',
                    4: '30–45 seconds',
                    5: '45+ seconds (or 1 strict pull-up)',
                },
            },
            'row': {
                'label': 'Table, doorframe, bed edge, railing, or bedsheet in a door',
                'exercise': 'Inverted Body Row',
                'instructions': [
                    'Find a sturdy surface you can grip and lean back from.',
                    'A table edge, doorframe, bed frame, railing, or a bedsheet knotted over a closed door all work.',
                    'Grip the surface. Lean back until your arms are straight and your body is at an angle.',
                    'Pull your chest toward the surface. Lower yourself slowly — 2 to 3 seconds down.',
                    'Do as many clean reps as you can in 60 seconds.',
                    'The more horizontal your body, the harder it is. Pick an angle you can do at least 5 reps at.',
                ],
                'duration_seconds': 60,
                'scoring': {
                    1: 'Cannot do 5 reps with straight body',
                    2: '5–10 reps',
                    3: '11–18 reps',
                    4: '19–25 reps',
                    5: '26+ reps',
                },
            },
        },
        # Fallback fields shown before variant is chosen
        'exercise': 'Pull Assessment',
        'instructions': ['Select your equipment option to begin.'],
        'camera_view': 'front',
        'duration_seconds': 60,
        'is_bilateral': False,
        'scoring': {
            1: 'Cannot hold 5 s / do 5 rows',
            2: '5–15 s / 5–10 rows',
            3: '15–30 s / 11–18 rows',
            4: '30–45 s / 19–25 rows',
            5: '45+ s / 26+ rows',
        },
    },
    {
        'index': 4,
        'test_id': 'core_test',
        'name': 'Core Assessment',
        'pattern': 'core',
        'exercise': 'Plank Hold',
        'instructions': [
            'Forearms or hands on floor, body in a straight line.',
            'Hold perfect position as long as possible.',
            'Stop when hips sag or pike significantly.',
        ],
        'camera_view': 'side',
        'duration_seconds': 120,
        'is_bilateral': False,
        'scoring': {
            1: 'Under 15 seconds',
            2: '15–29 seconds',
            3: '30–44 seconds',
            4: '45–59 seconds',
            5: '60 seconds or more',
        },
    },
    {
        'index': 5,
        'test_id': 'rotate_test',
        'name': 'Lateral Core Assessment',
        'pattern': 'rotate',
        'exercise': 'Side Plank Hold (each side)',
        'instructions': [
            'Side plank on forearm, body in a straight line.',
            'Hold each side separately.',
            'Record the weaker (shorter) side as your score.',
        ],
        'camera_view': 'front',
        'duration_seconds': 60,
        'is_bilateral': True,
        'scoring': {
            1: 'Under 10 seconds',
            2: '10–19 seconds',
            3: '20–29 seconds',
            4: '30–44 seconds',
            5: '45+ seconds',
        },
    },
    {
        'index': 6,
        'test_id': 'lunge_test',
        'name': 'Lunge / Stability Assessment',
        'pattern': 'lunge',
        'exercise': 'Split Squat Hold (each leg)',
        'instructions': [
            'Feet in split stance, back knee 2 inches from floor.',
            'Hold as long as possible with good posture.',
            'Test both legs — record each separately.',
        ],
        'camera_view': 'front',
        'duration_seconds': 60,
        'is_bilateral': True,
        'scoring': {
            1: 'Under 5 seconds',
            2: '5–14 seconds',
            3: '15–24 seconds',
            4: '25–39 seconds',
            5: '40+ seconds',
        },
    },
]

# ── Assessment → Exercise ID mapping ─────────────────────────────────────────
ASSESSMENT_EXERCISE_MAP = {
    'squat_test':    {'exercise_id': 'squat_hold_assess', 'mode': 'hold',     'duration': 60},
    'hinge_test':    {'exercise_id': 'hinge_hold_assess', 'mode': 'hold',     'duration': 60},
    'push_test':     {'exercise_id': 'push_ups',          'mode': 'max_reps', 'duration': 60},
    'pull_test_bar': {'exercise_id': 'dead_hang',         'mode': 'hold',     'duration': 60},
    'pull_test_row': {'exercise_id': 'doorframe_row',     'mode': 'max_reps', 'duration': 60},
    'core_test':     {'exercise_id': 'planks',            'mode': 'hold',     'duration': 120},
    'rotate_test':   {'exercise_id': 'side_plank',        'mode': 'hold',     'duration': 60},
    'lunge_test':    {'exercise_id': 'lunge_hold_assess', 'mode': 'hold',     'duration': 60},
}

# R2-W2-4 (SB-13): the raw→1-5 cutoffs are documented in ONE table —
# V1_TEST_NORMALISATION in v1_constants.py (measure, rationale, evidence
# tag per test). This view-level dict is derived from it unchanged.
from .v1_constants import V1_TEST_NORMALISATION

ASSESSMENT_SCORING = {
    key: {'type': cfg['type'], 'thresholds': cfg['thresholds']}
    for key, cfg in V1_TEST_NORMALISATION.items()
}

# ============================================================================
# RED FLAG OPTIONS
# ============================================================================

RED_FLAG_OPTIONS = [
    ('acl_grade_1_2',          'ACL injury (Grade 1 or 2)'),
    ('knee_pain_patellofemoral','Knee pain / Patellofemoral syndrome'),
    ('hernia',                  'Hernia (inguinal or umbilical)'),
    ('lower_back_disc',         'Lower back disc bulge or herniation'),
    ('shoulder_impingement',    'Shoulder impingement'),
    ('rotator_cuff_partial',    'Partial rotator cuff tear'),
    ('osteoporosis',            'Osteoporosis or low bone density'),
    ('hypertension',            'High blood pressure (hypertension)'),
    ('ankle_sprain_acute',      'Acute ankle sprain'),
    ('wrist_pain',              'Wrist pain or injury'),
    ('elbow_tendinopathy',      'Elbow tendinopathy (tennis / golfer elbow)'),
]

ABSOLUTE_STOP_OPTIONS = [
    ('recent_cardiac_event',       'Recent cardiac event (heart attack, surgery) in last 3 months'),
    ('uncontrolled_epilepsy',      'Uncontrolled epilepsy with recent seizures'),
    ('acute_fracture',             'Acute fracture or bone stress injury'),
    ('post_surgery_under_6_weeks', 'Post-surgery (less than 6 weeks ago)'),
    ('currently_pregnant',         'Currently pregnant (please consult your doctor first)'),
    ('uncontrolled_hypertension',  'Uncontrolled high blood pressure'),
    ('active_cancer_treatment',    'Currently undergoing cancer treatment'),
    # DA-C6 emergency screening additions. Internal IDs are clinical
    # (cauda equina / DVT / cardiac / malignancy / progressive neuro
    # deficit screens); patient copy is symptom-based per rule R4 —
    # never name a suspected diagnosis to the patient.
    ('saddle_numbness_bladder',       'New numbness around the groin/inner thighs, or new trouble controlling bladder or bowels'),
    ('calf_swelling_one_side',        'One calf newly swollen, hot, or painful (especially after travel, surgery, or bed rest)'),
    ('chest_pain_exertion',           'Chest pain, pressure, or fainting during exercise'),
    ('night_pain_weight_loss',        "Constant night pain that doesn't change with position, or unexplained weight loss"),
    ('numbness_weakness_progressive', 'Numbness or weakness in a limb that is getting worse'),
]

# Stop options whose stopped-state copy must escalate to "seek urgent
# medical care" (DA-C6) — stronger than the generic clearance copy.
URGENT_STOP_IDS = {
    'saddle_numbness_bladder',
    'calf_swelling_one_side',
    'chest_pain_exertion',
    'night_pain_weight_loss',
    'numbness_weakness_progressive',
}

# ============================================================================
# HELPERS
# ============================================================================

def _get_patient(request):
    pid = request.session.get('patient_id')
    if not pid:
        return None
    try:
        return PatientProfile.objects.get(patient_id=pid)
    except PatientProfile.DoesNotExist:
        return None


def _require_patient(request):
    """Return (patient, None) or (None, redirect_response)."""
    patient = _get_patient(request)
    if patient is None:
        return None, redirect('patient_login')
    return patient, None


def _gen_patient_id(name):
    initials = ''.join(w[0].upper() for w in re.split(r'\s+', name.strip()) if w)[:3] or 'PT'
    pid = f"{initials}{uuid.uuid4().hex[:6].upper()}"
    while PatientProfile.objects.filter(patient_id=pid).exists():
        pid = f"{initials}{uuid.uuid4().hex[:6].upper()}"
    return pid


def _compute_asymmetry(left_score, right_score):
    """Band-gap fallback — used ONLY when raw L/R measurements are absent
    (R2-W2-3 / SB-12: raw values are preferred; see _compute_asymmetry_raw)."""
    gap = abs(left_score - right_score)
    if gap == 0:
        return 'none'
    if gap == 1:
        return 'mild'
    if gap == 2:
        return 'moderate'
    return 'significant'


def _compute_asymmetry_raw(left_raw, right_raw):
    """R2-W2-3 (SB-12): asymmetry from RAW measured values, not score bands.

    LSI = (weaker / stronger) × 100 on the raw hold-seconds / reps. Two
    different raw values that land in the same 1-5 band no longer hide the
    gap, and adjacent-band values no longer exaggerate it.

    Bands for time/rep-based HOME tests — deliberately wider than the ≥90 %
    hop-distance convention because self-timed holds are noisier
    (evidence: pragmatic — documented in docs/FOOTBALL_METHODS.md):
      ≥85 none · 70–84 mild · 55–69 moderate · <55 significant

    Returns (classification, lsi_pct) or (None, None) if raw data unusable.
    """
    try:
        left_raw, right_raw = float(left_raw), float(right_raw)
    except (TypeError, ValueError):
        return None, None
    if left_raw <= 0 or right_raw <= 0:
        return None, None
    lsi = round(min(left_raw, right_raw) / max(left_raw, right_raw) * 100, 1)
    if lsi >= 85:
        return 'none', lsi
    if lsi >= 70:
        return 'mild', lsi
    if lsi >= 55:
        return 'moderate', lsi
    return 'significant', lsi


def _weaker_side(left, right):
    if left < right:
        return 'left'
    if right < left:
        return 'right'
    return ''


def _sanitize_text(value, max_length=500):
    """Strip HTML tags and limit length for free-text fields."""
    if not isinstance(value, str):
        return ''
    value = re.sub(r'<[^>]+>', '', value)
    return value.strip()[:max_length]


# ============================================================================
# SCREEN 1: START
# ============================================================================

def onboarding_start(request):
    # If already logged in with a completed profile, redirect to dashboard
    existing_pid = request.session.get('patient_id')
    if existing_pid:
        try:
            patient = PatientProfile.objects.get(patient_id=existing_pid)
            if StrengthProfile.objects.filter(patient=patient).exists():
                return redirect('v1_dashboard')
            # If mid-onboarding, let them continue
        except PatientProfile.DoesNotExist:
            request.session.flush()
    return render(request, 'strength_app/onboarding_start.html', {
        'step': 1,
        'total': _total_steps(patient if 'patient' in locals() else None),
        'tests': V1_STRENGTH_TESTS,
    })


# ============================================================================
# SCREEN 2: IDENTITY
# ============================================================================

@rate_limit(max_attempts=3, window_seconds=600, key_prefix='register')
def onboarding_identity(request):
    if request.method == 'POST':
        name     = _sanitize_text(request.POST.get('name', ''), max_length=100)
        bio_sex  = request.POST.get('biological_sex', 'not_specified')
        email    = _sanitize_text(request.POST.get('email', ''), max_length=254)
        password = request.POST.get('password', '')
        confirm  = request.POST.get('confirm_password', '')

        # Name validation
        if not name or len(name) < 2:
            messages.error(request, 'Please enter a valid name (at least 2 characters).')
            return render(request, 'strength_app/onboarding_identity.html', {
                'step': 2, 'total': _total_steps(patient if 'patient' in locals() else None),
            })

        # Phone validation — strip non-digits then validate length
        phone_raw = request.POST.get('phone', '').strip()
        phone = re.sub(r'[^0-9]', '', phone_raw)
        if len(phone) < 10 or len(phone) > 15:
            messages.error(request, 'Please enter a valid phone number (10-15 digits).')
            return render(request, 'strength_app/onboarding_identity.html', {
                'step': 2, 'total': _total_steps(patient if 'patient' in locals() else None),
            })

        # Age validation
        try:
            from .validation import safe_int
            age = safe_int(request.POST.get('age'), 25, 1, 120)  # DA-P4: junk-proof
            if age < 18 or age > 120:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'You must be 18 or older to use VYAYAM.')
            return render(request, 'strength_app/onboarding_identity.html', {
                'step': 2, 'total': _total_steps(patient if 'patient' in locals() else None),
            })

        # Height/weight validation (optional fields)
        try:
            height = float(request.POST.get('height_cm') or 0) or None
            if height and (height < 50 or height > 300):
                raise ValueError
        except (ValueError, TypeError):
            height = None

        try:
            weight = float(request.POST.get('weight_kg') or 0) or None
            if weight and (weight < 20 or weight > 500):
                raise ValueError
        except (ValueError, TypeError):
            weight = None

        # Consent validation
        if not request.POST.get('consent_terms'):
            messages.error(request, 'You must agree to the Terms of Service to register.')
            return render(request, 'strength_app/onboarding_identity.html', {
                'step': 2, 'total': _total_steps(patient if 'patient' in locals() else None),
            })
        # Password validation
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return render(request, 'strength_app/onboarding_identity.html', {
                'step': 2, 'total': _total_steps(patient if 'patient' in locals() else None),
            })
        if password.isdigit() or password.isalpha():
            messages.error(request, 'Password must contain both letters and numbers.')
            return render(request, 'strength_app/onboarding_identity.html', {
                'step': 2, 'total': _total_steps(patient if 'patient' in locals() else None),
            })
        if password != confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'strength_app/onboarding_identity.html', {
                'step': 2, 'total': _total_steps(patient if 'patient' in locals() else None),
            })

        existing_pid = request.session.get('patient_id')
        if existing_pid:
            try:
                patient = PatientProfile.objects.get(patient_id=existing_pid)
                # If phone changed, check uniqueness against other profiles
                if patient.phone != phone and PatientProfile.objects.filter(phone=phone).exclude(patient_id=existing_pid).exists():
                    messages.error(request, 'This phone number is already registered. Please log in.')
                    return render(request, 'strength_app/onboarding_identity.html', {
                        'step': 2, 'total': _total_steps(patient if 'patient' in locals() else None),
                    })
                patient.name = name
                patient.age = age
                patient.biological_sex = bio_sex
                patient.phone = phone
                patient.email = email
                # Only update password if user actually entered a new one
                if password and len(password) >= 8:
                    patient.password = make_password(password)
                if height:
                    patient.height_cm = float(height)
                if weight:
                    patient.weight_kg = float(weight)
                from django.utils import timezone as _tz
                patient.data_consent = True
                patient.data_consent_date = _tz.now()
                patient.save()
                return redirect('onboarding_training_history')
            except PatientProfile.DoesNotExist:
                pass

        # Check phone uniqueness before creating
        if PatientProfile.objects.filter(phone=phone).exists():
            messages.error(request, 'This phone number is already registered. Please log in.')
            return render(request, 'strength_app/onboarding_identity.html', {
                'step': 2, 'total': _total_steps(patient if 'patient' in locals() else None),
            })

        from django.utils import timezone as _tz
        pid = _gen_patient_id(name)
        patient = PatientProfile.objects.create(
            patient_id=pid,
            name=name,
            age=age,
            biological_sex=bio_sex,
            data_consent=True,
            data_consent_date=_tz.now(),
            phone=phone,
            email=email,
            height_cm=float(height) if height else None,
            weight_kg=float(weight) if weight else None,
            goals='general_fitness',
            password=make_password(password),
        )
        request.session.flush()
        request.session['patient_id'] = pid
        return redirect('onboarding_training_history')

    return render(request, 'strength_app/onboarding_identity.html', {
        'step': 2,
        'total': _total_steps(patient if 'patient' in locals() else None),
    })


# ============================================================================
# SCREEN 3: TRAINING HISTORY
# ============================================================================

def onboarding_training_history(request):
    patient, err = _require_patient(request)
    if err:
        return err

    if request.method == 'POST':
        patient.training_history = request.POST.get('training_history', 'never')
        patient.last_trained     = request.POST.get('last_trained', 'never')
        patient.training_types_json = request.POST.getlist('training_types')

        months_map = {
            'never': 0, 'tried': 1, 'beginner': 6,
            'intermediate': 18, 'advanced': 36,
        }
        patient.training_age_months = months_map.get(patient.training_history, 0)
        patient.save()
        return redirect('onboarding_strength_test')

    return render(request, 'strength_app/onboarding_training_history.html', {
        'patient': patient,
        'step': 3,
        'total': _total_steps(patient if 'patient' in locals() else None),
        'training_types': PatientProfile.TRAINING_TYPES,
    })


# ============================================================================
# SCREEN 4: STRENGTH TEST OVERVIEW
# ============================================================================

def onboarding_strength_test(request):
    patient, err = _require_patient(request)
    if err:
        return err

    if request.method == 'POST':
        request.session['test_results'] = {}
        return redirect('onboarding_strength_test_execute', test_index=0)

    # Restore test results from database if session was lost
    if 'test_results' not in request.session and patient.raw_test_data_json:
        request.session['test_results'] = patient.raw_test_data_json

    return render(request, 'strength_app/onboarding_strength_test.html', {
        'tests': V1_STRENGTH_TESTS,
        'step': 4,
        'total': _total_steps(patient if 'patient' in locals() else None),
    })


# ============================================================================
# SCREEN 5: STRENGTH TEST EXECUTE
# ============================================================================

def onboarding_strength_test_execute(request, test_index):
    patient, err = _require_patient(request)
    if err:
        return err

    if test_index >= len(V1_STRENGTH_TESTS):
        return redirect('onboarding_asymmetry')

    test = V1_STRENGTH_TESTS[test_index]
    side = request.GET.get('side', '')
    variant = request.GET.get('variant', '')

    # ── Variant handling (pull test: bar vs row) ──────────────────────────
    has_variants = test.get('has_variants', False)
    active_test = dict(test)

    if has_variants:
        variants = test.get('variants', {})
        if variant in variants:
            active_test.update(variants[variant])
            active_test['selected_variant'] = variant
        else:
            # Show variant picker (old template, no ghost overlay)
            variant_options = [
                {'key': vkey, 'label': vcfg.get('label', vkey)}
                for vkey, vcfg in variants.items()
            ]
            progress_pct = round((test_index / len(V1_STRENGTH_TESTS)) * 100)
            scoring_items = [{'score': k, 'desc': v} for k, v in active_test.get('scoring', {}).items()]
            return render(request, 'strength_app/onboarding_strength_test_execute.html', {
                'test': active_test,
                'test_index': test_index,
                'total_tests': len(V1_STRENGTH_TESTS),
                'side': '',
                'variant': '',
                'is_bilateral': False,
                'progress_pct': progress_pct,
                'scoring_items': scoring_items,
                'patient': patient,
                'step': 5,
                'total': _total_steps(patient if 'patient' in locals() else None),
                'show_variant_picker': True,
                'variant_options': variant_options,
                'has_variants': True,
            })

    # ── Bilateral handling ────────────────────────────────────────────────
    is_bilateral = active_test.get('is_bilateral', False)
    if is_bilateral and side not in ('left', 'right'):
        from django.urls import reverse
        url = reverse('onboarding_strength_test_execute', args=[test_index])
        qs = f'?side=left&variant={variant}' if variant else '?side=left'
        return redirect(url + qs)

    progress_pct = round((test_index / len(V1_STRENGTH_TESTS)) * 100)

    # Map test to exercise for ghost overlay
    test_id = active_test.get('test_id', '')
    map_key = f'pull_test_{variant}' if (test_id == 'pull_test' and variant) else test_id
    ex_map = ASSESSMENT_EXERCISE_MAP.get(map_key, {})
    exercise_id = ex_map.get('exercise_id', '')
    assessment_mode = ex_map.get('mode', 'hold')
    assessment_duration = ex_map.get('duration', 60)

    # Max-reps tests (push-ups, rows) → assessment template with timer + self-report
    # Hold tests (squat, hinge, plank, lunge) → exercise template with ghost overlay
    if assessment_mode == 'max_reps':
        scoring_items = [{'score': k, 'desc': v} for k, v in active_test.get('scoring', {}).items()]
        return render(request, 'strength_app/onboarding_strength_test_execute.html', {
            'test': active_test,
            'test_index': test_index,
            'total_tests': len(V1_STRENGTH_TESTS),
            'side': side,
            'variant': variant,
            'is_bilateral': is_bilateral,
            'progress_pct': progress_pct,
            'scoring_items': scoring_items,
            'patient': patient,
            'step': 5,
            'total': _total_steps(patient if 'patient' in locals() else None),
            'show_variant_picker': False,
        })

    from .exercise_content import EXERCISE_CONTENT
    content = EXERCISE_CONTENT.get(exercise_id, {})

    exercise = {
        'exercise_id': exercise_id,
        'exercise_name': active_test.get('exercise', content.get('display_name', '')),
        'movement_pattern': active_test.get('pattern', ''),
        'sets': 1,
        'reps': 0,
        'hold_duration': assessment_duration,
        'tempo': '0-0-0-0',
        'rest_seconds': 0,
        'is_unilateral': is_bilateral,
        'asymmetry_side': side,
        'is_new_exercise': False,
        'notes': '',
        'mind_muscle_cue': content.get('mind_muscle_cue', {}),
        'instructions': content.get('instructions', active_test.get('instructions', [])),
        'form_cues': content.get('form_cues', []),
        'common_mistakes': content.get('common_mistakes', []),
    }

    scoring = dict(ASSESSMENT_SCORING.get(map_key, {}))
    # R2-W2-4: sex-adjusted cutoffs where the table provides them and the
    # code already collects biological sex (currently: push test).
    norm_cfg = V1_TEST_NORMALISATION.get(map_key, {})
    if (getattr(patient, 'biological_sex', '') == 'female'
            and norm_cfg.get('thresholds_female')):
        scoring['thresholds'] = norm_cfg['thresholds_female']

    context = {
        'patient': patient,
        'exercise': exercise,
        'exercise_index': test_index,
        'total_exercises': len(V1_STRENGTH_TESTS),
        'is_last_exercise': test_index >= len(V1_STRENGTH_TESTS) - 1,
        'next_exercise_index': test_index + 1,
        'has_strength_profile': False,
        'assessment_mode': True,
        'assessment_type': 'hold',
        'assessment_duration': assessment_duration,
        'assessment_test_id': test_id,
        'assessment_test_index': test_index,
        'assessment_side': side,
        'assessment_variant': variant,
        'assessment_scoring': scoring,
        'assessment_scoring_json': json.dumps(scoring),
        'progress_pct': progress_pct,
        'step': 5,
        'total': _total_steps(patient if 'patient' in locals() else None),
    }
    return render(request, 'strength_app/v1_exercise_execute.html', context)


# ============================================================================
# AJAX: SAVE TEST RESULT
# ============================================================================


def onboarding_save_test_result(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = {k: v for k, v in request.POST.items()}

    from .validation import safe_int, safe_float
    # DA-P4: clamp — junk must not 500; score is a 1-5 scale; index must
    # stay inside the test battery (it was used unbounded below).
    test_index = safe_int(data.get('test_index', 0), 0, 0, len(V1_STRENGTH_TESTS) - 1)
    score      = safe_int(data.get('score', 3), 3, 1, 5)
    side       = str(data.get('side', ''))
    variant    = str(data.get('variant', ''))
    # R2-W2-3 (SB-12): the raw measurement (hold seconds / reps) was sent by
    # the client and DISCARDED here — asymmetry could then only ever be
    # computed from 1-5 score bands. Keep the raw value alongside the score.
    measured   = safe_float(data.get('measured_value', 0), 0.0, 0, 10000)

    if 'test_results' not in request.session:
        request.session['test_results'] = {}

    results = dict(request.session['test_results'])
    test = V1_STRENGTH_TESTS[test_index] if test_index < len(V1_STRENGTH_TESTS) else {}
    key  = test.get('test_id', f'test_{test_index}')

    if side in ('left', 'right'):
        sub = results.get(key, {})
        if not isinstance(sub, dict):
            sub = {}
        sub[side] = score
        sub[side + '_raw'] = measured
        results[key] = sub
    else:
        results[key] = score
        results[key + '_raw'] = measured

    request.session['test_results'] = results
    request.session.modified = True

    # Persist to database so progress survives browser close
    try:
        _patient, _ = _require_patient(request)
        if _patient:
            _patient.raw_test_data_json = results
            _patient.save(update_fields=['raw_test_data_json'])
    except Exception:
        pass

    # Determine next URL
    is_bilateral = test.get('is_bilateral', False)
    from django.urls import reverse as _reverse

    if is_bilateral:
        if side == 'left':
            next_url = _reverse('onboarding_strength_test_execute', args=[test_index]) + '?side=right'
        else:
            next_index = test_index + 1
            next_url = (
                _reverse('onboarding_asymmetry')
                if next_index >= len(V1_STRENGTH_TESTS)
                else _reverse('onboarding_strength_test_execute', args=[next_index])
            )
    else:
        next_index = test_index + 1
        next_url = (
            _reverse('onboarding_asymmetry')
            if next_index >= len(V1_STRENGTH_TESTS)
            else _reverse('onboarding_strength_test_execute', args=[next_index])
        )

    return JsonResponse({'status': 'saved', 'next_url': next_url})


# ============================================================================
# SCREEN 6: ASYMMETRY
# ============================================================================

def onboarding_asymmetry(request):
    patient, err = _require_patient(request)
    if err:
        return err

    test_results = request.session.get('test_results', {})

    def bilateral_scores(test_id):
        val = test_results.get(test_id)
        if isinstance(val, dict):
            return val.get('left', 3), val.get('right', 3)
        return 3, 3

    def bilateral_raw(test_id):
        val = test_results.get(test_id)
        if isinstance(val, dict):
            return val.get('left_raw'), val.get('right_raw')
        return None, None

    hinge_left,  hinge_right  = bilateral_scores('hinge_test')
    rotate_left, rotate_right = bilateral_scores('rotate_test')
    lunge_left,  lunge_right  = bilateral_scores('lunge_test')

    # R2-W2-3 (SB-12): asymmetry from RAW measured values wherever both
    # sides have one; the 1-5 band gap is only the fallback. Each result
    # is labelled with the method that produced it.
    def asymmetry_for(test_id, left_score, right_score):
        lraw, rraw = bilateral_raw(test_id)
        cls, lsi = _compute_asymmetry_raw(lraw, rraw)
        if cls is not None:
            return cls, {'method': 'raw', 'lsi_pct': lsi}
        return (_compute_asymmetry(left_score, right_score),
                {'method': 'band_gap', 'lsi_pct': None})

    hinge_cls,  hinge_meta  = asymmetry_for('hinge_test',  hinge_left,  hinge_right)
    lunge_cls,  lunge_meta  = asymmetry_for('lunge_test',  lunge_left,  lunge_right)
    rotate_cls, rotate_meta = asymmetry_for('rotate_test', rotate_left, rotate_right)

    auto = {
        'hinge_asymmetry':  hinge_cls,
        'lunge_asymmetry':  lunge_cls,
        'rotate_asymmetry': rotate_cls,
        'asymmetry_meta': {'hinge': hinge_meta, 'lunge': lunge_meta,
                           'rotate': rotate_meta},
        'hinge_left': hinge_left,   'hinge_right': hinge_right,
        'lunge_left': lunge_left,   'lunge_right': lunge_right,
        'rotate_left': rotate_left, 'rotate_right': rotate_right,
    }

    if request.method == 'POST':
        def get_score(test_id):
            v = test_results.get(test_id, 3)
            if isinstance(v, dict):
                return min(v.get('left', 3), v.get('right', 3))
            return int(v) if v else 3

        # DA-P4: update_or_create keyed on (patient, assessment_number=1)
        # — back-navigating through onboarding and resubmitting this step
        # used to create DUPLICATE baseline StrengthProfile rows,
        # corrupting assessment history and the radar chart.
        profile, _created = StrengthProfile.objects.update_or_create(
            patient=patient,
            assessment_number=1,
            defaults=dict(
                squat_score=get_score('squat_test'),
                hinge_score=min(hinge_left, hinge_right),
                push_score=get_score('push_test'),
                pull_score=get_score('pull_test'),
                core_score=get_score('core_test'),
                rotate_score=min(rotate_left, rotate_right),
                lunge_score=min(lunge_left, lunge_right),

                hinge_left=hinge_left,   hinge_right=hinge_right,
                lunge_left=lunge_left,   lunge_right=lunge_right,
                rotate_left=rotate_left, rotate_right=rotate_right,

                hinge_asymmetry=auto['hinge_asymmetry'],
                lunge_asymmetry=auto['lunge_asymmetry'],
                rotate_asymmetry=auto['rotate_asymmetry'],

                weaker_side_hinge=_weaker_side(hinge_left, hinge_right),
                weaker_side_lunge=_weaker_side(lunge_left, lunge_right),
                weaker_side_rotate=_weaker_side(rotate_left, rotate_right),

                fat_asymmetry_visible=request.POST.get('fat_asymmetry_visible', 'none'),
                fat_asymmetry_location=request.POST.get('fat_asymmetry_location', ''),
                fat_asymmetry_side=request.POST.get('fat_asymmetry_side', ''),

                # R2-W2-3: raw L/R measurements + per-pattern method/LSI
                # metadata persist with the profile (no schema change).
                raw_test_data_json={**test_results,
                                    '_asymmetry_meta': auto['asymmetry_meta']},
            ),
        )
        priorities = compute_pattern_priorities(patient, profile)
        profile.pattern_priority_json = {p: i for i, p in enumerate(priorities)}
        profile.save()
        return redirect('onboarding_goals')

    return render(request, 'strength_app/onboarding_asymmetry.html', {
        'patient': patient,
        'auto': auto,
        'step': 5,
        'total': _total_steps(patient if 'patient' in locals() else None),
    })


# ============================================================================
# SCREEN 7: GOALS
# ============================================================================

def onboarding_goals(request):
    patient, err = _require_patient(request)
    if err:
        return err

    if request.method == 'POST':
        patient.goal_type      = request.POST.get('goal_type', 'general_strength')
        patient.goal_secondary = request.POST.get('goal_secondary', '')
        goal_tertiary          = request.POST.get('goal_tertiary', '')
        patient.sport_type     = request.POST.get('sport_type', '')
        comp = request.POST.get('competition_date', '')
        if comp:
            try:
                patient.competition_date = datetime.strptime(comp, '%Y-%m-%d').date()
            except ValueError:
                pass
        import json as _json
        all_goals = [g for g in [patient.goal_type, patient.goal_secondary, goal_tertiary] if g]
        patient.goals = _json.dumps(all_goals)
        patient.save()
        return redirect('onboarding_equipment')

    goals_list = []
    for key, cfg in GOAL_CONFIG.items():
        if key == 'female_physique' and patient.biological_sex != 'female':
            continue
        goals_list.append({
            'key': key,
            'label': cfg['label'],
            'notes': cfg.get('notes', ''),
            'dosage_emphasis': cfg.get('dosage_emphasis', ''),
        })

    import json as _json
    goals_actually_set = False
    try:
        raw_goals = patient.goals
        if raw_goals and raw_goals.startswith('['):
            parsed = _json.loads(raw_goals)
            goals_actually_set = len(parsed) > 0
    except (ValueError, AttributeError):
        pass

    if not goals_actually_set and patient.goal_type == 'general_strength':
        initial_goal_type = ''
        initial_goal_secondary = ''
    else:
        initial_goal_type = patient.goal_type
        initial_goal_secondary = patient.goal_secondary or ''

    return render(request, 'strength_app/onboarding_goals.html', {
        'patient': patient,
        'goals': goals_list,
        'initial_goal_type': initial_goal_type,
        'initial_goal_secondary': initial_goal_secondary,
        'step': 6,
        'total': _total_steps(patient if 'patient' in locals() else None),
    })


# ============================================================================
# SCREEN 8: EQUIPMENT
# ============================================================================

def onboarding_equipment(request):
    patient, err = _require_patient(request)
    if err:
        return err

    if request.method == 'POST':
        patient.equipment_available_json   = request.POST.getlist('equipment')
        patient.training_location          = request.POST.get('training_location', 'home_none')
        from .validation import safe_int
        # DA-P4: clamp — 0 sessions/week breaks week advancement maths
        patient.session_duration_minutes   = safe_int(request.POST.get('session_duration_minutes'), 45, 15, 180)
        patient.sessions_per_week          = safe_int(request.POST.get('sessions_per_week'), 3, 1, 7)
        patient.save()
        if patient.biological_sex == 'female':
            return redirect('onboarding_hormonal')
        else:
            return redirect('onboarding_red_flags')

    return render(request, 'strength_app/onboarding_equipment.html', {
        'patient': patient,
        'equipment_choices': PatientProfile.EQUIPMENT_CHOICES,
        'location_choices':  PatientProfile.TRAINING_LOCATION_CHOICES,
        'sessions_per_week_options': [2, 3, 4, 5, 6],
        'step': 7,
        'total': _total_steps(patient if 'patient' in locals() else None),
    })


# ============================================================================
# SCREEN 9: HORMONAL (female only)
# ============================================================================

def onboarding_hormonal(request):
    patient, err = _require_patient(request)
    if err:
        return err

    if patient.biological_sex != 'female':
        return redirect('onboarding_red_flags')

    if request.method == 'POST':
        patient.cycle_tracking_enabled  = request.POST.get('cycle_tracking_enabled') == 'on'
        patient.hormonal_contraceptive  = request.POST.get('hormonal_contraceptive') == 'on'
        patient.menstrual_pain_level    = request.POST.get('menstrual_pain_level', '')

        cl = request.POST.get('cycle_length_days', '')
        if cl:
            try:
                from .validation import safe_int
                patient.cycle_length_days = safe_int(cl, 28, 20, 45)  # DA-P4: physiological range
            except ValueError:
                pass

        lp = request.POST.get('last_period_start', '')
        if lp:
            try:
                patient.last_period_start = datetime.strptime(lp, '%Y-%m-%d').date()
            except ValueError:
                pass
        patient.save()
        return redirect('onboarding_red_flags')

    return render(request, 'strength_app/onboarding_hormonal.html', {
        'patient': patient,
        'step': 8,
        'total': _total_steps(patient if 'patient' in locals() else None),
    })


# ============================================================================
# SCREEN 10: RED FLAGS
# ============================================================================

def _log_red_flag_change(patient, old_flags, new_flags, old_stop, new_stop):
    """DA-C5: audit every red-flag/absolute-stop change; notify linked pros.

    Creates a RedFlagEvent when anything changed, and appends a note to any
    active coach/therapist link when an absolute stop is cleared so the
    professional sees it on their next visit.
    """
    from .models import RedFlagEvent, CoachPatientLink

    flags_changed = sorted(old_flags) != sorted(new_flags)
    stop_changed = old_stop != new_stop
    if not flags_changed and not stop_changed:
        return

    if old_stop and not new_stop:
        change_type = 'absolute_stop_cleared'
        note = 'Patient confirmed their situation has changed / medical clearance to train.'
    elif new_stop and not old_stop:
        change_type = 'absolute_stop_set'
        note = ''
    else:
        change_type = 'flags_updated'
        note = ''

    RedFlagEvent.objects.create(
        patient=patient,
        source='patient',
        change_type=change_type,
        old_flags=old_flags,
        new_flags=new_flags,
        old_stop=old_stop,
        new_stop=new_stop,
        note=note,
    )

    if change_type != 'absolute_stop_cleared':
        return

    # Surface the clear to linked professionals (best-effort enrichment —
    # the audit event above is the durable record).
    stamp = f"\n[FLAGGED {date.today()}] Patient cleared absolute stop on {date.today()} (self-service)."
    try:
        for link in CoachPatientLink.objects.filter(patient=patient, is_active=True):
            link.notes = (link.notes or '') + stamp
            link.save(update_fields=['notes'])
        if patient.user_id:
            from therapist_app.models import TherapistPatientLink, Alert
            for tlink in TherapistPatientLink.objects.filter(
                    patient=patient.user, status='active'):
                tlink.notes = (tlink.notes or '') + stamp
                tlink.save(update_fields=['notes'])
                # R2-T2: reviewable alert alongside the note stamp
                Alert.objects.create(
                    link=tlink, alert_type='red_flag',
                    message='Patient cleared their absolute-stop flag '
                            '(self-service). Review the audit trail before '
                            'their next session.',
                )
    except Exception:
        logging.getLogger(__name__).warning(
            'Could not append stop-clear note to professional links for %s',
            patient.patient_id, exc_info=True,
        )


def onboarding_red_flags(request):
    patient, err = _require_patient(request)
    if err:
        return err

    if request.method == 'POST':
        red_flags    = request.POST.getlist('red_flags')
        abs_stops    = request.POST.getlist('absolute_stop_conditions')
        surgical_raw = request.POST.get('surgical_history', '')
        meds_raw     = request.POST.get('medications', '')

        # ── DA-C5: snapshot before mutating, gate stop-clearing ──────────
        old_flags = list(patient.red_flags_json or [])
        old_stop = patient.absolute_stop
        new_stop = bool(abs_stops)

        if old_stop and not new_stop:
            # Clearing an absolute stop requires an explicit confirmation —
            # a patient who was hard-stopped cannot silently uncheck it.
            # Re-render the form (NOT the stop card) with the warning so the
            # patient can tick the confirmation and resubmit.
            if not request.POST.get('confirm_stop_clear'):
                return render(request, 'strength_app/onboarding_red_flags.html', {
                    'patient': patient,
                    'red_flag_options': RED_FLAG_OPTIONS,
                    'absolute_stop_options': ABSOLUTE_STOP_OPTIONS,
                    'stopped': False,
                    'clear_confirmation_required': True,
                    'step': 8,
                    'total': _total_steps(patient),
                })

        patient.red_flags_json        = red_flags
        patient.surgical_history_json = [s.strip() for s in surgical_raw.split(',') if s.strip()]
        patient.medications_json      = [m.strip() for m in meds_raw.split(',') if m.strip()]

        if abs_stops:
            patient.absolute_stop        = True
            # Store human-readable labels — this field is patient-facing
            # (stopped card + v1_stopped page), so raw internal IDs like
            # 'saddle_numbness_bladder' must not leak into copy (R4).
            _stop_labels = dict(ABSOLUTE_STOP_OPTIONS)
            patient.absolute_stop_reason = '; '.join(
                _stop_labels.get(s, s) for s in abs_stops
            )
        else:
            patient.absolute_stop        = False
            patient.absolute_stop_reason = ''

        # Data consent (V2 data foundation)
        patient.data_consent = bool(request.POST.get('data_consent'))
        if patient.data_consent and not patient.data_consent_date:
            from django.utils import timezone as _tz
            patient.data_consent_date = _tz.now()

        patient.save()

        _log_red_flag_change(patient, old_flags, red_flags, old_stop, new_stop)

        if patient.absolute_stop:
            return render(request, 'strength_app/onboarding_red_flags.html', {
                'patient': patient,
                'red_flag_options': RED_FLAG_OPTIONS,
                'absolute_stop_options': ABSOLUTE_STOP_OPTIONS,
                'stopped': True,
                # DA-C6: emergency-pattern symptoms escalate the stop copy
                # to "seek urgent medical care" (stronger than clearance).
                'urgent_stop': any(s in URGENT_STOP_IDS for s in abs_stops),
                'step': 8,
                'total': _total_steps(patient if 'patient' in locals() else None),
            })

        return redirect('onboarding_lifestyle')

    return render(request, 'strength_app/onboarding_red_flags.html', {
        'patient': patient,
        'red_flag_options': RED_FLAG_OPTIONS,
        'absolute_stop_options': ABSOLUTE_STOP_OPTIONS,
        'stopped': False,
        'step': 8,
        'total': _total_steps(patient if 'patient' in locals() else None),
    })


# ============================================================================
# SCREEN 11: LIFESTYLE
# ============================================================================

def onboarding_lifestyle(request):
    patient, err = _require_patient(request)
    if err:
        return err

    if request.method == 'POST':
        patient.sleep_quality      = request.POST.get('sleep_quality', 'good')
        patient.stress_level       = request.POST.get('stress_level', 'moderate')
        patient.nutrition_quality  = request.POST.get('nutrition_quality', 'regular')
        patient.lifestyle          = request.POST.get('lifestyle', 'moderately_active')
        try:
            from .validation import safe_int
            patient.daily_sitting_hours = safe_int(request.POST.get('daily_sitting_hours'), 6, 0, 24)  # DA-P4
        except ValueError:
            patient.daily_sitting_hours = 6
        patient.save()
        return redirect('onboarding_nutrition')

    return render(request, 'strength_app/onboarding_lifestyle.html', {
        'patient': patient,
        'lifestyle_choices': PatientProfile.LIFESTYLE_CHOICES,
        'step': 9,
        'total': _total_steps(patient if 'patient' in locals() else None),
    })


# ============================================================================
# SCREEN 11b: NUTRITION (optional — between Lifestyle and Mind-Muscle)
# ============================================================================

def onboarding_nutrition(request):
    patient, err = _require_patient(request)
    if err:
        return err

    from .models import NutritionProfile
    from .v1_nutrition_engine import calculate_macro_targets, GOAL_NUTRITION, ACTIVITY_MULTIPLIERS, TRAINING_TO_NUTRITION_GOAL

    if request.method == 'POST':
        skip = request.POST.get('skip_nutrition')
        if skip:
            return redirect('onboarding_mind_muscle')

        # Auto-map from training goal if no explicit nutrition goal submitted
        submitted_goal = request.POST.get('nutrition_goal', '')
        if submitted_goal and submitted_goal in GOAL_NUTRITION:
            goal = submitted_goal
        else:
            goal = TRAINING_TO_NUTRITION_GOAL.get(patient.goal_type, 'maintenance')
        activity      = request.POST.get('activity_level', 'moderately_active')
        mess_mode     = bool(request.POST.get('mess_mode'))
        bio_sex       = patient.biological_sex or 'male'

        try:
            weight_kg = float(request.POST.get('weight_kg') or 0) or None
            height_cm = float(request.POST.get('height_cm') or 0) or None
        except ValueError:
            weight_kg = height_cm = None

        np_obj, _ = NutritionProfile.objects.get_or_create(patient=patient)
        np_obj.nutrition_goal  = goal
        np_obj.activity_level  = activity
        np_obj.mess_mode       = mess_mode
        np_obj.biological_sex  = bio_sex  # derived from patient profile

        if weight_kg:
            np_obj.weight_kg = weight_kg
        if height_cm:
            np_obj.height_cm = height_cm

        # Calculate macro targets if we have enough data
        if weight_kg and height_cm and patient.age:
            medical_conditions = list(patient.red_flags_json or [])
            targets = calculate_macro_targets(
                weight_kg=weight_kg,
                height_cm=height_cm,
                age=patient.age,
                sex=bio_sex,
                activity_level=activity,
                goal=goal,
                medical_conditions=medical_conditions,
            )
            np_obj.target_calories = targets['calories']
            np_obj.target_protein_g = targets['protein_g']
            np_obj.target_carbs_g   = targets['carbs_g']
            np_obj.target_fat_g     = targets['fat_g']

        np_obj.save()
        return redirect('onboarding_mind_muscle')

    # GET — build goal choices from engine
    goal_choices = [
        (key, cfg['label'], cfg['note'])
        for key, cfg in GOAL_NUTRITION.items()
    ]

    # Pre-fill if patient has an existing NutritionProfile
    try:
        existing_np = NutritionProfile.objects.get(patient=patient)
    except NutritionProfile.DoesNotExist:
        existing_np = None

    return render(request, 'strength_app/onboarding_nutrition.html', {
        'patient': patient,
        'goal_choices': goal_choices,
        'np': existing_np,
        'step': 10,
        'total': _total_steps(patient if 'patient' in locals() else None),
    })


# ============================================================================
# SCREEN 12: MIND-MUSCLE
# ============================================================================

def onboarding_mind_muscle(request):
    patient, err = _require_patient(request)
    if err:
        return err

    if request.method == 'POST':
        patient.mind_muscle_glute = request.POST.get('mind_muscle_glute', 'none')
        patient.mind_muscle_vmo   = request.POST.get('mind_muscle_vmo', 'none')
        patient.save()
        return redirect('onboarding_complete')

    return render(request, 'strength_app/onboarding_mind_muscle.html', {
        'patient': patient,
        'step': 11,
        'total': _total_steps(patient if 'patient' in locals() else None),
    })


# ============================================================================
# SCREEN 13: COMPLETE — REVEAL
# ============================================================================

def onboarding_complete(request):
    patient, err = _require_patient(request)
    if err:
        return err

    profile = patient.strength_profiles.order_by('-assessed_at').first()

    # Create PeriodisationState using training age config
    training_cfg = TRAINING_AGE_CONFIG.get(patient.training_history, TRAINING_AGE_CONFIG['never'])
    aa_weeks = training_cfg.get('aa_weeks', 4)

    state, _ = PeriodisationState.objects.get_or_create(
        patient=patient,
        defaults={
            'current_phase': 'anatomical_adaptation_iso',
            'current_week': 1,
            'macrocycle_number': 1,
            'phase_start_date': date.today(),
            'anatomical_adaptation_weeks': aa_weeks,
        },
    )

    # Radar chart data
    if profile:
        radar_data = {
            'Squat':  profile.squat_score,
            'Hinge':  profile.hinge_score,
            'Push':   profile.push_score,
            'Pull':   profile.pull_score,
            'Core':   profile.core_score,
            'Rotate': profile.rotate_score,
            'Lunge':  profile.lunge_score,
        }
        priorities = compute_pattern_priorities(patient, profile)
        top_3 = priorities[:3]
        asym  = get_asymmetry_rules(profile)
    else:
        radar_data = {k: 2 for k in ['Squat', 'Hinge', 'Push', 'Pull', 'Core', 'Rotate', 'Lunge']}
        top_3 = ['squat', 'hinge', 'push']
        asym  = {}

    from .v1_constants import PERIODISATION_PHASES
    phase_info = PERIODISATION_PHASES.get('anatomical_adaptation_iso', {})
    goal_info  = GOAL_CONFIG.get(patient.goal_type, {})

    # Athlete tier eligibility — ≥4 of 7 strength patterns scored 5
    if profile:
        top_scores = [
            profile.squat_score, profile.hinge_score, profile.push_score,
            profile.pull_score, profile.core_score, profile.rotate_score,
            profile.lunge_score,
        ]
        fives_count = sum(1 for s in top_scores if s >= 5)
        patient.athlete_tier_eligible = fives_count >= 4
    else:
        patient.athlete_tier_eligible = False

    # Mark gate test completed so dashboard shows correct state
    patient.gate_test_completed = True
    from django.utils import timezone as _tz
    patient.gate_test_completed_at = _tz.now()
    patient.save(update_fields=[
        'gate_test_completed', 'gate_test_completed_at', 'athlete_tier_eligible',
    ])

    request.session['has_strength_profile'] = True

    return render(request, 'strength_app/onboarding_complete.html', {
        'patient': patient,
        'profile': profile,
        'radar_data': radar_data,
        'top_3': top_3,
        'asym': asym,
        'state': state,
        'phase_info': phase_info,
        'goal_info': goal_info,
        'aa_weeks': aa_weeks,
        'athlete_tier_eligible': patient.athlete_tier_eligible,
        'step': 10,
        'total': _total_steps(patient if 'patient' in locals() else None),
    })
