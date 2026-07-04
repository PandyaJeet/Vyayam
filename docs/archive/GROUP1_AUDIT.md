# Group 1 - Core Engine and Registry

This file catalogs everything in Group 1 (core domain engine + exercise registry) for the Vyayam codebase.

## Scope
- strength_app/backend/database_schema.py
- strength_app/backend/gate_test_system.py
- strength_app/backend/prescription_engine.py
- strength_app/backend/form_tracking.py
- strength_app/backend/session_execution.py
- strength_app/backend/report_generator.py
- strength_app/backend/main_coordinator.py
- strength_app/exercise_system/exercise_registry_v2.py

## Purpose Summary
- database_schema.py: Domain data models for patients, gate tests, sessions, progression, reports, and system state.
- gate_test_system.py: Classifies capability by category and determines starting prescription from gate tests.
- prescription_engine.py: Builds AI auto-prescriptions or formats therapist prescriptions; handles advancement/regression.
- form_tracking.py: Rep-level form scoring (green/yellow/red), set analysis, and practice mode coordination.
- session_execution.py: Executes a session from a prescription and aggregates form/completion metrics.
- report_generator.py: Aggregates sessions into weekly summaries and professional report text.
- main_coordinator.py: Orchestrates patient lifecycle end-to-end; stores in-memory system state.
- exercise_registry_v2.py: Exercise metadata registry and lazy instantiation helpers.

## Key Data Structures
- PatientProfile, GateTestResult, GateTestSession
- RepData, SetData, ExerciseData, WorkoutSession
- ExerciseProgressionState, WeeklyProgress, ProgressReport
- TherapistProfile, TherapistPrescription
- SystemState

## Primary Flows
1) Gate test classification -> starting phase/sets/reps
2) Auto or therapist prescription generation
3) Session execution with form tracking and practice mode
4) Daily feedback loop (comfort-based adjustments)
5) Weekly summaries and progress report generation

## Known Issues (from Group 1 review)
- Division by zero when adherence uses current_week = 0 (main_coordinator.py)
- Division by zero when sets or reps are 0 (session_execution.py)
- Cardio gate tests ignore duration thresholds (gate_test_system.py)
- Empty gate test list can yield invalid fitness level and divide by zero (gate_test_system.py)
- Report generator assumes CapabilityLevel objects; fails on strings (report_generator.py)
- Unknown exercise_type can raise IndexError in get_starting_exercise_from_phase (prescription_engine.py)
- Therapist prescription missing required fields can raise KeyError (prescription_engine.py)
- Missing prescription sections cause KeyError (session_execution.py)
- Weekly summary trusts session order; start/end dates can be wrong (report_generator.py)
- Exercise registry key casing mismatch for lateral_hops (exercise_registry_v2.py)
- In-memory state store and placeholder password hashing are not secure or scalable (main_coordinator.py)
- Lazy registry is not thread-safe (exercise_registry_v2.py)

## Test Coverage Suggestions
- Unit: classify_capability thresholds (squat, cardio), determine_prescription, exercise progression helpers
- Unit: form tracking scoring and practice mode triggers
- Unit: report generation with empty sessions and mixed fitness_level types
- Integration: gate test -> prescription -> session -> report flow
- Edge: empty gate tests, zero sets/reps, missing prescription sections, unknown exercise types
- Stress: large session lists, long report periods, repeated registry lookups

## Security/Robustness Notes
- Validate and clamp input ranges for reps, duration, pain, and difficulty
- Guard all divisions with zero checks
- Normalize enum vs string handling for fitness levels
- Avoid placeholder password hashing in production paths
- Ensure thread safety for registry and state management if running concurrently
