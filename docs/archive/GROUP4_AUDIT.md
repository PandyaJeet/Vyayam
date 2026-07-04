# Group 4 - HTTP/API Surface and Security Controls

This file catalogs Group 4 (HTTP handlers, routing, and security middleware) for the Vyayam codebase.

## Scope
- strength_app/views.py
- strength_app/v1_onboarding_views.py
- strength_app/v1_football_views.py
- strength_app/v1_session_views.py
- strength_app/v1_progress_views.py
- strength_app/v1_coach_views.py
- strength_app/v1_nutrition_views.py
- strength_app/v1_therapist_session_views.py
- therapist_app/views.py
- therapist_app/permissions.py
- strength_app/middleware.py
- strength_app/rate_limiter.py
- strength_app/urls.py
- therapist_app/urls.py

## Purpose Summary
- Patient PWA flows: onboarding, gate testing, prescriptions, session execution, progress, and reporting.
- Athlete/football module: assessment battery, results, and match calendar.
- Coach dashboard: therapist profile-based athlete management and overrides.
- Nutrition module: logging, search, and mess guidance.
- Therapist console: invite, patient management, program builder, messaging, reports.
- Middleware: camera permissions policy; simple IP-based rate limiting.

## Key Flows
1) Patient auth: phone + password (PatientProfile), session-based access.
2) Onboarding → strength tests → asymmetry → goals/equipment → completion.
3) Gate test → session-stored families → DB GateTestResult → prescription generation.
4) V1 session: generate_v1_session → execute → feedback → WorkoutSession/ExerciseExecution.
5) Therapist-managed patient session flow (B2B2C): published Prescription → SessionLog.
6) Therapist console: invites → patient detail tabs → program save → reports.

## Known Issues / Risks
- analyze_frame endpoint does not enforce authentication or rate limiting; potential abuse/DoS vector (strength_app/views.py).
- football_save_test_result accepts POST without verifying a logged-in patient; allows session pollution by unauthenticated requests (strength_app/v1_football_views.py).
- session_analyzers is a global dict without cleanup except explicit endpoint; potential memory growth in long-running processes (strength_app/views.py).
- coach_override_prescription accepts raw JSON exercises without schema validation; bad payloads can reach TherapistPrescription (strength_app/v1_coach_views.py).
- save_program accepts arbitrary item fields; missing validation for exercise_id, sets, reps (therapist_app/views.py).
- exercise_results in the legacy workout flow lack exercise_id; progressive capability update uses exercise_id and may never advance (strength_app/views.py).
- generate_report calls utils.generate_progress_report with mismatched signature; always falls back to a placeholder report (strength_app/views.py).
- rate_limiter trusts X-Forwarded-For without proxy validation; spoofing can bypass limits (strength_app/rate_limiter.py).
- Multiple endpoints accept JSON and quietly fall back to request.POST; error handling is inconsistent across endpoints (various views).
- Session-based auth relies on patient_id only; no secondary verification or lockout beyond IP rate limiting.

## Test Coverage Suggestions
- Auth: patient_login rate limiting, session fixation protection, and therapist_required 403 behavior.
- Gate test: save_gate_test_result actions (too_easy/this_is_my_level/cannot_do/skip).
- analyze_frame: require auth, enforce request size, and error on malformed base64.
- Therapist console: get_linked_patient_or_404 cross-therapist access control.
- Coach views: ensure coach_required blocks non-coach users.
- Nutrition API: quick-log JSON validation and error responses.
- Session flows: v1_save_exercise_result and v1_post_session_feedback persistence.

## Tests Added (Targeted Group 4)
- strength_app/tests/test_group4.py
- therapist_app/test_group4.py

## Test Details (Targeted Group 4)
- PermissionsPolicyMiddleware header injection.
- rate_limit blocks POST after max attempts; GET bypass.
- save_gate_test_result creates GateTestResult and PatientFamilyCapability.
- analyze_frame rejects GET with POST-required error.
- nutrition APIs: food search and quick-log enforce auth; quick-log creates DailyFoodLog.
- therapist_required redirects anonymous, 403 for non-therapist; get_linked_patient_or_404 blocks cross-therapist access.
- therapist console: save_program publishes PrescriptionItem and draft-only saves do not publish.
- therapist console: send_message creates TherapistMessage and redirects.
- coach dashboard: coach_required redirects anonymous/non-coach; coach_add_athlete, coach_flag_review, coach_override_prescription, coach_set_competition succeed.

## Test Execution Status
- Targeted Group 4 tests passed (21 tests).

Commands run:
```
DJANGO_SECRET_KEY=test DJANGO_DEBUG=True python manage.py test strength_app.tests.test_group4 therapist_app.test_group4
```

## Security/Robustness Notes
- Require authentication and rate limiting on compute-heavy endpoints (analyze_frame).
- Validate and clamp all numeric inputs for JSON endpoints (reps, pain, duration).
- Consider CSRF coverage for JSON POST endpoints (ensure JS includes CSRF token).
- Use trusted proxy settings before relying on X-Forwarded-For for rate limiting.
- Add schema validation for therapist program payloads to prevent bad data entering prescriptions.

## Data Integrity
- Align gate test exercise IDs with progression chains (partial_squat vs partial_squats) to avoid broken lookups.
- Ensure patient session data contains exercise_id for capability updates.
- Normalize goal storage (goals text vs JSON array) to avoid inconsistent reads across modules.
