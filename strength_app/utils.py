"""
VYAYAM STRENGTH TRAINING - UTILS (REAL BACKEND INTEGRATION)
This file bridges Django models with the real backend logic
"""

from django.utils import timezone
from .models import (
    PatientProfile, GateTestResult, WorkoutSession,
    ExerciseExecution, ProgressReport
)

# Import REAL backend engines
from .backend.gate_test_system import GateTestEngine, GateTestCoordinator
from .backend.prescription_engine import PrescriptionEngine
from .backend.session_execution import SessionExecutor
from .backend.report_generator import ReportGenerator

# Import backend data structures
from .backend.database_schema import (
    CapabilityLevel as BackendCapabilityLevel,
    ExerciseCategory as BackendExerciseCategory,
    PrescriptionMode as BackendPrescriptionMode,
    PatientProfile as BackendPatientProfile,
    GateTestResult as BackendGateTestResult,
    GateTestSession as BackendGateTestSession,
    WorkoutSession as BackendWorkoutSession
)

import random


# ============================================================================
# CONVERSION HELPERS (Django ↔ Backend)
# ============================================================================

def django_to_backend_patient(django_patient):
    """Convert Django PatientProfile to backend PatientProfile"""
    
    return BackendPatientProfile(
        patient_id=django_patient.patient_id,
        name=django_patient.name,
        phone=django_patient.phone,
        password_hash="django_patient",
        age=django_patient.age,
        fitness_level=django_patient.fitness_level_json or {},
        goals=django_patient.goals,
        goal_type=django_patient.goal_type,
        biomechanics=django_patient.biomechanics or "",
        activity_pattern=django_patient.activity_pattern or "",
        difficulty_tolerance=django_patient.difficulty_tolerance,
        lifestyle=django_patient.lifestyle,
        occupation=django_patient.occupation or "",
        daily_sitting_hours=django_patient.daily_sitting_hours,
        compliance_proven=django_patient.compliance_proven,
        adherence_rate=django_patient.adherence_rate,
        timeline=django_patient.timeline,
        target_weeks=django_patient.target_weeks,
        medical_conditions=list(django_patient.medical_conditions_json) if django_patient.medical_conditions_json else [],
        contraindications=list(django_patient.contraindications_json) if django_patient.contraindications_json else [],
        prescription_mode=BackendPrescriptionMode.AI_AUTO if django_patient.prescription_mode == 'ai_auto' else BackendPrescriptionMode.THERAPIST_MANUAL,
        current_week=django_patient.current_week or 0,
        program_start_date=django_patient.program_start_date
    )


def backend_to_django_capability(backend_capability):
    """Convert backend CapabilityLevel enum to Django string"""
    mapping = {
        BackendCapabilityLevel.CANNOT_DO: 'cannot_do',
        BackendCapabilityLevel.STRUGGLING: 'struggling',
        BackendCapabilityLevel.MANAGEABLE: 'manageable',
        BackendCapabilityLevel.EASY: 'easy'
    }
    return mapping.get(backend_capability, 'manageable')


def django_to_backend_category(django_category_str):
    """Convert Django category string to backend ExerciseCategory enum"""
    mapping = {
        'lower_body': BackendExerciseCategory.LOWER_BODY,
        'posterior_chain': BackendExerciseCategory.POSTERIOR_CHAIN,
        'upper_body': BackendExerciseCategory.UPPER_BODY,
        'cardio': BackendExerciseCategory.CARDIO,
        'stretching': BackendExerciseCategory.STRETCHING
    }
    return mapping.get(django_category_str, BackendExerciseCategory.LOWER_BODY)


def django_to_backend_capability(django_capability_str):
    """Convert Django capability string to backend CapabilityLevel enum"""
    mapping = {
        'cannot_do': BackendCapabilityLevel.CANNOT_DO,
        'struggling': BackendCapabilityLevel.STRUGGLING,
        'manageable': BackendCapabilityLevel.MANAGEABLE,
        'easy': BackendCapabilityLevel.EASY
    }
    return mapping.get(django_capability_str, BackendCapabilityLevel.MANAGEABLE)


def sanitize_json_field(data):
    """
    Sanitize data for JSON serialization - convert Enums to strings
    Recursively handles dicts and lists
    
    FIXES: "TypeError: Object of type CapabilityLevel is not JSON serializable"
    """
    if isinstance(data, dict):
        return {k: sanitize_json_field(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_json_field(item) for item in data]
    elif isinstance(data, BackendCapabilityLevel):
        # Convert CapabilityLevel enum to string
        return backend_to_django_capability(data)
    elif hasattr(data, 'value') and hasattr(data, 'name'):
        # Generic enum handling - use value
        return data.value
    elif isinstance(data, (str, int, float, bool, type(None))):
        # Already JSON serializable
        return data
    else:
        # Fallback - convert to string
        return str(data)



# ============================================================================
# GATE TESTING (Using REAL Backend)
# ============================================================================

def conduct_gate_testing(patient):
    """
    Conduct gate tests using REAL backend logic
    Returns list of Django GateTestResult objects
    """
    
    # Initialize REAL backend engines
    gate_engine = GateTestEngine()
    coordinator = GateTestCoordinator()
    
    # Convert Django patient to backend format
    backend_patient = django_to_backend_patient(patient)
    
    results = []
    backend_results = []
    
    # Test all 4 categories
    categories = [
        ('lower_body', 'partial_squat', BackendExerciseCategory.LOWER_BODY),
        ('posterior_chain', 'hip_hinge', BackendExerciseCategory.POSTERIOR_CHAIN),
        ('upper_body', 'bent_over_row', BackendExerciseCategory.UPPER_BODY),
        ('cardio', 'walking', BackendExerciseCategory.CARDIO),
    ]
    
    for category_str, test_exercise, backend_category in categories:
        # Simulate test performance (in production: get from actual test)
        reps, depth, difficulty = _simulate_performance(patient, category_str)
        
        # Use REAL backend engine to conduct test and classify
        backend_result = gate_engine.conduct_gate_test(
            patient_id=patient.patient_id,
            category=backend_category,
            test_exercise=test_exercise,
            reps_completed=reps,
            depth_achieved=depth,
            difficulty_reported=difficulty,
            pain_during=1
        )
        
        backend_results.append(backend_result)
        
        # Save to Django database
        django_result = GateTestResult.objects.create(
            patient=patient,
            category=category_str,
            test_exercise=test_exercise,
            reps_completed=backend_result.reps_completed,
            depth_achieved=backend_result.depth_achieved,
            difficulty_reported=backend_result.difficulty_reported,
            pain_during=backend_result.pain_during,
            capability_level=backend_to_django_capability(backend_result.capability_level),
            starting_sets=backend_result.starting_sets,
            starting_reps=backend_result.starting_reps,
            starting_phase=backend_result.starting_phase,
            notes=backend_result.notes
        )
        
        results.append(django_result)
        
        # Update patient fitness level
        fitness = patient.fitness_level_json
        fitness[category_str] = backend_to_django_capability(backend_result.capability_level)
        patient.fitness_level_json = fitness
    
    # Create backend gate session
    backend_session = coordinator.create_gate_test_session(
        patient_id=patient.patient_id,
        test_results=backend_results
    )
    
    # Update patient from backend
    backend_patient = coordinator.update_patient_fitness_levels(
        patient=backend_patient,
        gate_session=backend_session
    )
    
    # Update Django patient
    patient.compliance_proven = backend_patient.compliance_proven
    patient.difficulty_tolerance = backend_patient.difficulty_tolerance
    
    # Sanitize JSON fields before saving (convert any enums to strings)
    patient.fitness_level_json = sanitize_json_field(patient.fitness_level_json)
    
    patient.save()
    
    return results


def _simulate_performance(patient, category):
    """Simulate gate test performance based on patient age/lifestyle"""
    if patient.age < 30 and patient.lifestyle == 'active':
        return random.randint(10, 15), random.uniform(75, 90), random.randint(1, 3)
    elif patient.age < 40 and patient.lifestyle == 'sedentary':
        return random.randint(5, 8), random.uniform(45, 60), random.randint(3, 5)
    elif patient.age >= 60:
        return random.randint(2, 4), random.uniform(25, 40), random.randint(5, 7)
    else:
        return random.randint(6, 10), random.uniform(50, 70), random.randint(3, 5)


# ============================================================================
# PRESCRIPTION GENERATION (Using REAL Backend)
# ============================================================================

def generate_prescription(patient):
    """
    Generate a smart prescription using:
      1. Gate test results (PatientFamilyCapability — most accurate)
         or GateTestResult DB records (fallback)
      2. Patient AGE          → adjust volume/intensity
      3. Patient LIFESTYLE    → adjust starting load and cardio ceiling
      4. Patient GOAL TYPE    → prioritise families, adjust conservatism
      5. Progressive Loading  → 5-level dosage system (sets × reps × hold)

    Progressive Loading Dosage:
      1 = Unable          → skip
      2 = Partial/Assisted → 2 sets × 6 reps
      3 = Basic/Building   → 2 sets × 10 reps
      4 = Comfortable      → 3 sets × 12 reps
      5 = Advanced         → 3 sets × 15 reps (+ flag ready_to_advance)
    """
    from .exercise_progressions import (
        PROGRESSION_CHAINS, DEFAULT_GATE_TEST_FAMILIES,
        get_dosage_for_level, CAPABILITY_STRING_TO_NUMERIC,
    )
    from .exercise_tags import (
        get_patient_modifier, apply_modifier, STRETCH_DOSAGE,
        GOAL_PRIORITY_FAMILIES, get_max_cardio_level,
        FAMILY_WARMUP_STRETCHES,
    )
    from .models import PatientFamilyCapability

    age       = patient.age or 35
    lifestyle = patient.lifestyle or 'moderately_active'
    goal      = patient.goal_type or 'functional'

    # Patient-specific modifier (sets/reps delta based on age+lifestyle+goal)
    modifier = get_patient_modifier(age, lifestyle, goal)

    # Age safety cap — never prescribe above this capability level
    if age >= 65:
        age_cap = 3
    elif age >= 50:
        age_cap = 4
    else:
        age_cap = 5

    # Cardio ceiling from lifestyle
    max_cardio_ladder = get_max_cardio_level(lifestyle)

    # Goal-based family priority order
    priority_order = GOAL_PRIORITY_FAMILIES.get(goal, DEFAULT_GATE_TEST_FAMILIES)
    # Fill in any families not in priority list
    ordered_families = priority_order + [f for f in DEFAULT_GATE_TEST_FAMILIES if f not in priority_order]

    prescription = {
        'stretching': [],
        'strength': [],
        'cardio': [],
        'balance': [],
        'meta': {
            'age': age,
            'lifestyle': lifestyle,
            'goal_type': goal,
            'modifier': modifier,
            'age_cap': age_cap,
            'max_cardio_ladder': max_cardio_ladder,
        }
    }

    # ── Live capability from PatientFamilyCapability (preferred source) ───────
    live_caps = {
        pfc.family_id: pfc
        for pfc in PatientFamilyCapability.objects.filter(patient=patient)
    }

    # ── Fallback: gate test results (one per family, most recent) ─────────────
    recent_tests = GateTestResult.objects.filter(
        patient=patient,
        exercise_family__in=DEFAULT_GATE_TEST_FAMILIES
    ).order_by('-test_date')
    tested_families = {}
    for t in recent_tests:
        if t.exercise_family not in tested_families:
            tested_families[t.exercise_family] = t

    # ── Stretching warm-up — personalised by goal and active families ─────────
    # Collect relevant stretches for the families being trained today
    stretch_ids_seen = set()
    stretch_families = ordered_families  # All trained families get their stretches
    for fid in stretch_families:
        for s_id in FAMILY_WARMUP_STRETCHES.get(fid, []):
            if s_id not in stretch_ids_seen:
                stretch_ids_seen.add(s_id)
                # Stretch hold scales with lifestyle (more active = longer hold)
                stretch_caps = {
                    'sedentary': 2, 'moderately_active': 3,
                    'active': 4, 'very_active': 4,
                }
                s_cap = stretch_caps.get(lifestyle, 3)
                s_sets, _, s_hold = STRETCH_DOSAGE.get(s_cap, STRETCH_DOSAGE[3])
                # Reduce hold for 65+ (joint sensitivity)
                if age >= 65:
                    s_hold = max(20, s_hold - 10)
                s_name = s_id.replace('_', ' ').title()
                prescription['stretching'].append({
                    'exercise_id':   s_id,
                    'exercise_name': s_name,
                    'sets':          s_sets,
                    'reps':          1,
                    'hold_duration': s_hold,
                    'rest':          15,
                    'category':      'stretching',
                    'capability_numeric': s_cap,
                })

    # ── Strength / balance / cardio from gate tests ───────────────────────────
    for fid in ordered_families:
        chain = PROGRESSION_CHAINS.get(fid)
        if not chain:
            continue

        movement_type = chain['movement_type']  # 'strength' | 'balance' | 'cardio'

        # ── Resolve capability for this family ────────────────────────────────
        if fid in live_caps:
            # Most up-to-date source — PatientFamilyCapability
            pfc        = live_caps[fid]
            cap_numeric  = pfc.capability_numeric
            cap_string   = pfc.capability_string
            lvl_index    = pfc.current_level_index
            ex_id        = pfc.current_exercise_id or chain['levels'][0]['exercise_id']
            ex_name      = pfc.current_exercise_name or chain['levels'][0]['name']

            # ── Ladder advancement: if capability = 5, step up the ladder ──────
            # (capability resets to 3 at the new rung — patient starts fresh)
            if pfc.ready_to_advance and cap_numeric >= 5:
                next_idx = lvl_index + 1
                if next_idx < len(chain['levels']):
                    lvl_index  = next_idx
                    next_lvl   = chain['levels'][next_idx]
                    ex_id      = next_lvl['exercise_id']
                    ex_name    = next_lvl['name']
                    cap_numeric = 3     # Reset to "Basic" at new exercise
                    cap_string  = 'manageable'
                    # Update PatientFamilyCapability for next session
                    pfc.current_level_index  = next_idx
                    pfc.current_exercise_id  = ex_id
                    pfc.current_exercise_name = ex_name
                    pfc.capability_numeric   = cap_numeric
                    pfc.capability_string    = cap_string
                    pfc.ready_to_advance     = False
                    pfc.consecutive_comfortable_sessions = 0
                    from django.utils import timezone
                    pfc.last_advancement_date = timezone.now()
                    # Log
                    hist = pfc.progression_history_json or []
                    hist.append({
                        'type': 'ladder_advance',
                        'from_level_index': lvl_index - 1,
                        'to_level_index': next_idx,
                        'new_exercise': ex_id,
                    })
                    pfc.progression_history_json = hist
                    pfc.save()

        elif fid in tested_families:
            # Fallback: gate test result record
            gate       = tested_families[fid]
            cap_numeric  = getattr(gate, 'capability_numeric', None) or \
                           CAPABILITY_STRING_TO_NUMERIC.get(gate.capability_level, 3)
            cap_string   = gate.capability_level
            lvl_index    = gate.level_index
            ex_id        = gate.prescribed_exercise_id or gate.test_exercise
            ex_name      = gate.prescribed_exercise_name or ex_id.replace('_', ' ').title()

        else:
            # No data — prescribe Level 1 at capability 2 (cautious start)
            first_lvl  = chain['levels'][0]
            cap_numeric  = 2   # Partial/Assisted
            cap_string   = 'struggling'
            lvl_index    = 0
            ex_id        = first_lvl['exercise_id']
            ex_name      = first_lvl['name']

        # ── Safety caps ───────────────────────────────────────────────────────
        cap_numeric = min(cap_numeric, age_cap)

        # Cardio: never prescribe past lifestyle ceiling on the ladder
        if movement_type == 'cardio':
            levels_in_chain = chain['levels']
            # Find the exercise's ladder position (0-based lvl_index)
            if lvl_index >= max_cardio_ladder:
                lvl_index = max(0, max_cardio_ladder - 1)
                if lvl_index < len(levels_in_chain):
                    ex_id   = levels_in_chain[lvl_index]['exercise_id']
                    ex_name = levels_in_chain[lvl_index]['name']

        # Cannot do → skip this family
        if cap_numeric <= 1 or cap_string == 'cannot_do':
            continue

        # Find level data from the chain
        levels_in_chain = chain['levels']
        lvl_data = {}
        for lvl in levels_in_chain:
            if lvl['exercise_id'] == ex_id:
                lvl_data = lvl
                break
        if not lvl_data and levels_in_chain:
            lvl_data = levels_in_chain[min(lvl_index, len(levels_in_chain) - 1)]

        # ── Get base dosage from progressive loading table ─────────────────────
        sets_base, reps_base, hold_base = get_dosage_for_level(lvl_data, cap_numeric)

        # ── Apply age × lifestyle × goal modifier ─────────────────────────────
        is_hold = lvl_data.get('hold_duration', 0) > 0 or hold_base > 0
        sets_final, reps_final, hold_final = apply_modifier(
            (sets_base, reps_base, hold_base), modifier, age=age, is_hold=is_hold
        )

        # ── Hold-based overrides ──────────────────────────────────────────────
        if hold_final > 0:
            reps_final = 1

        rest_time = 90 if movement_type == 'cardio' else 60

        entry = {
            'exercise_id':        ex_id,
            'exercise_name':      ex_name,
            'sets':               sets_final,
            'reps':               reps_final,
            'hold_duration':      hold_final,
            'rest':               rest_time,
            'category':           movement_type,
            'family_id':          fid,
            'family_name':        chain['name'],
            'capability_numeric': cap_numeric,
            'capability_string':  cap_string,
            'ladder_level':       lvl_index + 1,
            'ladder_total':       len(levels_in_chain),
            'ready_to_advance':   (cap_numeric >= 4 and cap_string == 'easy'),
            'dosage_label':       {1:'Unable',2:'Partial',3:'Basic',4:'Comfortable',5:'Advanced'}.get(cap_numeric, 'Basic'),
        }

        # Route to correct section
        if fid == 'cardio_family':
            prescription['cardio'].append(entry)
        elif fid == 'balance_family':
            prescription['balance'].append(entry)
        else:
            prescription['strength'].append(entry)

    return prescription


# ============================================================================
# SESSION EXECUTION (Using REAL Backend)
# ============================================================================

# 🔧 ADDITIONAL FIX FOR utils.py
# Update the execute_workout_session function to handle category as either string or enum

# Find this function in strength_app/utils.py and update it:

def execute_workout_session(patient, prescription_data):
    """
    Execute workout using REAL backend logic
    """
    
    # Initialize backend executor
    session_executor = SessionExecutor()
    
    # Convert category strings back to enums if needed
    prescription_with_enums = {}
    for section, exercises in prescription_data.items():
        prescription_with_enums[section] = []
        for exercise in exercises:
            exercise_copy = exercise.copy()
            # Convert category string to enum if it's a string
            if 'category' in exercise_copy and isinstance(exercise_copy['category'], str):
                exercise_copy['category'] = django_to_backend_category(exercise_copy['category'])
            prescription_with_enums[section].append(exercise_copy)
    
    # Convert prescription mode
    backend_mode = BackendPrescriptionMode.AI_AUTO if patient.prescription_mode == 'ai_auto' else BackendPrescriptionMode.THERAPIST_MANUAL
    
    # Execute session using REAL backend
    backend_session = session_executor.execute_workout_session(
        patient_id=patient.patient_id,
        week_number=patient.current_week or 1,
        prescription=prescription_with_enums,
        prescription_mode=backend_mode
    )
    
    # Save to Django database
    django_session = WorkoutSession.objects.create(
        patient=patient,
        week_number=patient.current_week or 1,
        total_duration_minutes=backend_session.total_duration_minutes,
        total_exercises_completed=backend_session.total_exercises_completed,
        total_green_reps_all=backend_session.total_green_reps_all,
        overall_session_form_score=backend_session.overall_session_form_score,
        prescription_mode=patient.prescription_mode
    )
    
    # Save all exercise executions
    all_exercises = (
        backend_session.stretching_exercises +
        backend_session.strength_exercises +
        backend_session.cardio_exercises
    )
    
    for backend_ex in all_exercises:
        ExerciseExecution.objects.create(
            session=django_session,
            exercise_id=backend_ex.exercise_id,
            exercise_name=backend_ex.exercise_name,
            category=backend_ex.category.value if hasattr(backend_ex.category, 'value') else backend_ex.category,
            prescribed_sets=backend_ex.prescribed_sets,
            prescribed_reps=backend_ex.prescribed_reps,
            prescribed_hold_duration=backend_ex.prescribed_hold_duration,
            prescribed_rest=backend_ex.prescribed_rest,
            total_green_reps=backend_ex.total_green_reps,
            total_yellow_reps=backend_ex.total_yellow_reps,
            total_red_reps=backend_ex.total_red_reps,
            overall_form_score=backend_ex.overall_form_score,
            completion_percentage=backend_ex.completion_percentage,
            practice_mode_entered=backend_ex.practice_mode_entered,
            practice_reps_done=backend_ex.practice_reps_done,
            went_back_one_level=backend_ex.went_back_one_level
        )
    
    return django_session


# ============================================================================
# PROGRESS REPORT GENERATION (computed from real DB aggregates — DA-C7)
# ============================================================================

def generate_progress_report(patient, weeks=4):
    """Generate a ProgressReport from REAL WorkoutSession / SessionFeedback
    aggregates over the last `weeks` weeks.

    Never invents numbers (DA-C7): a patient with no sessions in the
    window gets a zeroed report with "insufficient data" copy, not a
    fabricated 75% adherence.
    """
    from datetime import timedelta
    from django.utils import timezone

    window_start = timezone.now() - timedelta(weeks=weeks)
    sessions = list(
        patient.workout_sessions
        .filter(session_date__gte=window_start)
        .order_by('session_date')
    )

    sessions_per_week = patient.sessions_per_week or 3
    prescribed = sessions_per_week * weeks
    completed = len(sessions)

    period_label = f"Last {weeks} weeks"

    if completed == 0:
        return ProgressReport.objects.create(
            patient=patient,
            report_period=period_label,
            total_sessions_completed=0,
            total_sessions_prescribed=prescribed,
            overall_adherence_rate=0.0,
            total_green_reps_period=0,
            average_form_score_period=0.0,
            form_improvement=0.0,
            continue_current_program=True,
            patient_feedback_summary='Insufficient data — no completed sessions in this period.',
            recommended_next_steps=(
                'Insufficient data for meaningful trends. Complete a few '
                'sessions and generate the report again.'
            ),
        )

    adherence = min(100.0, round(completed / prescribed * 100, 1)) if prescribed else 0.0
    green_total = sum(s.total_green_reps_all for s in sessions)
    scored = [s.overall_session_form_score for s in sessions if s.overall_session_form_score > 0]
    avg_form = round(sum(scored) / len(scored), 1) if scored else 0.0

    # Form improvement: first vs last scored session in the window
    form_improvement = round(scored[-1] - scored[0], 1) if len(scored) >= 2 else 0.0

    # Pain summary from SessionFeedback in the window (factual counts only)
    feedbacks = patient.session_feedbacks.filter(created_at__gte=window_start)
    pain_counts = {}
    for fb in feedbacks:
        if fb.pain_reported and fb.pain_reported != 'none':
            pain_counts[fb.pain_reported] = pain_counts.get(fb.pain_reported, 0) + 1
    if pain_counts:
        parts = [f"{count}× {level}" for level, count in sorted(pain_counts.items())]
        pain_summary = 'Pain reported in this period: ' + ', '.join(parts) + '.'
    else:
        pain_summary = 'No pain reported in this period.'

    # Current capability levels (source of truth for the V1 engine)
    current_levels = {
        cap.family_id: {
            'exercise': cap.current_exercise_id,
            'level_index': cap.current_level_index,
            'capability': cap.capability_numeric,
        }
        for cap in patient.family_capabilities.all()
    }

    return ProgressReport.objects.create(
        patient=patient,
        report_period=period_label,
        total_sessions_completed=completed,
        total_sessions_prescribed=prescribed,
        overall_adherence_rate=adherence,
        total_green_reps_period=green_total,
        average_form_score_period=avg_form,
        form_improvement=form_improvement,
        current_fitness_levels_json=current_levels,
        patient_feedback_summary=pain_summary,
        continue_current_program=True,
        recommended_next_steps=(
            f'{completed} of {prescribed} planned sessions completed '
            f'({adherence:.0f}% adherence). Average form score {avg_form:.0f}. '
            'Review with your therapist or coach for programme changes.'
        ),
    )