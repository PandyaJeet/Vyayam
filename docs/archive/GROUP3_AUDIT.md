# Group 3 - Orchestration and Integration Layer

This file catalogs Group 3 (orchestration + integration glue) for the Vyayam codebase.

## Scope
- strength_app/utils.py
- strength_app/backend/main_coordinator.py
- strength_app/v1_data_collector.py
- strength_app/v1_progression_chains.py

Related dependencies (used by Group 3):
- strength_app/exercise_progressions.py
- strength_app/exercise_tags.py
- strength_app/v1_constants.py

## Purpose Summary
- utils.py: Bridges Django models to backend engines and back; gate testing, prescription generation, session execution, report generation.
- main_coordinator.py: In-memory orchestrator for the full patient journey (demo/runtime coordinator).
- v1_data_collector.py: Anonymised session logging for V2 data foundation (consent gated).
- v1_progression_chains.py: Legacy V1 movement pattern ladders and equipment map.

## Key Flows
1) Django patient -> backend patient conversion (utils.django_to_backend_patient)
2) Gate tests via backend engine -> persisted Django GateTestResult
3) Prescription generation from PatientFamilyCapability or GateTestResult fallback
4) Session execution via backend -> persisted WorkoutSession/ExerciseExecution
5) Progress report generation via backend -> persisted ProgressReport
6) Optional anonymised data capture post-session

## Known Issues / Risks
- execute_workout_session iterates over all prescription_data items including meta dict; iterating meta keys causes attribute errors (utils.py).
- Category mapping mismatch: generate_prescription uses movement_type (strength/balance/cardio), but django_to_backend_category expects lower_body/posterior_chain/upper_body/cardio/stretching; balance defaults to lower_body, misclassifying exercises (utils.py).
- Gate test persistence misses exercise_family/family_name/level_index/prescribed_exercise_id fields; prescription fallback via GateTestResult may use incomplete data (utils.py).
- Exercise ID mismatch between gate test inputs and progression chains (e.g., partial_squat vs partial_squats) can break chain lookups and dosage selection (utils.py, exercise_progressions.py).
- Two sources of progression truth (exercise_progressions.py vs v1_progression_chains.py) can drift; only exercise_progressions is used by utils/views.
- Non-deterministic gate test simulation (random) makes tests flaky and prescriptions non-reproducible (utils.py).
- No transaction boundaries when updating PatientFamilyCapability and generating prescription; concurrent requests can double-advance ladders (utils.py).
- main_coordinator uses in-memory state and placeholder password hashing; not safe for production, not durable or concurrent (backend/main_coordinator.py).
- main_coordinator uses current_week without incrementing, which can cause divide-by-zero in adherence and repeated week numbers (backend/main_coordinator.py).
- v1_data_collector swallows all exceptions silently; data issues are hidden and never surfaced (v1_data_collector.py).

## Test Coverage Suggestions
- Unit: django_to_backend_* mapping; ensure category conversions match expected enums.
- Unit: generate_prescription for meta handling, missing family data, capability caps, cardio ladder ceilings.
- Integration: gate test -> prescription -> session -> report; verify persisted Django models are populated correctly.
- Edge: prescription with balance exercises; ensure category mapping does not default to lower_body.
- Edge: gate tests with exercise IDs not in progression chains; ensure safe fallback without crash.
- Concurrency: two simultaneous prescriptions for same PatientFamilyCapability should not double-advance.
- Data collection: log_session_data no-throw behavior but verify entry creation when consent is true.

## Tests Added (Targeted Group 3)
- strength_app/tests/test_group3.py

## Test Details (Targeted Group 3)
- Utils mapping: django_to_backend_category handles lower_body/stretching/cardio.
- JSON sanitation: sanitize_json_field converts backend enums to strings.
- V1 progression chains: every family exposes non-empty levels and exercises.
- Orchestrator inference: _infer_clusteral_dimensions sets biomechanics/activity_pattern and goal_type/timeline.
- Prescription: PatientFamilyCapability-driven entry appears in strength prescription.
- Session execution: meta key in prescription triggers AttributeError (current bug surfaced).
- Session execution (valid payload): WorkoutSession created and 3 ExerciseExecution rows persisted.
- Data collection: log_session_data creates AnonymisedSessionLog with consent, skips without consent.

## Test Execution Status
- Targeted Group 3 tests passed (9 tests).

Commands run:
```
DJANGO_SECRET_KEY=test DJANGO_DEBUG=True python manage.py test strength_app.tests.test_group3
```

## Security/Robustness Notes
- Replace random gate test simulation with deterministic inputs in test paths.
- Add transactional updates around PatientFamilyCapability ladder changes.
- Add logging in v1_data_collector for failures (at least debug).
- Normalize exercise IDs across gate tests and progression chains (single source of truth).
- Ensure meta keys are skipped in session execution or strictly validated before execution.

## Data Integrity
- Ensure GateTestResult persistence includes exercise_family and prescribed_exercise_id when using family-based progressions.
- Validate JSON payloads used for prescription meta to prevent runtime conversion errors.
