# Group 2 - Data/ORM Layer

This file catalogs Group 2 (Django ORM models + key migrations) for the Vyayam codebase.

## Scope
- strength_app/models.py
- therapist_app/models.py
- strength_app/migrations/0001_initial.py
- strength_app/migrations/0010_patientprofile_therapist_managed.py
- therapist_app/migrations/0001_initial.py
- therapist_app/migrations/0003_add_phone_to_link.py

## Purpose Summary
- strength_app/models.py: Core patient, assessment, workout, progression, report, nutrition, football, and anonymised data models.
- therapist_app/models.py: B2B2C therapist console models (therapists, links, prescriptions, messaging, session logs, reports).
- migrations: Schema evolution for the above models.

## Key Models (strength_app)
- PatientProfile
- StrengthProfile
- PeriodisationState
- GateTestResult
- PatientFamilyCapability
- WorkoutSession
- SessionFeedback
- ExerciseExecution
- TherapistProfile
- TherapistPrescription
- ExerciseProgressionState
- ProgressReport
- AnonymisedSessionLog
- CoachPatientLink
- StretchSession
- NutritionProfile
- FoodItem
- DailyFoodLog
- MessEntry
- FootballProfile

## Key Models (therapist_app)
- Therapist
- TherapistPatientLink
- Prescription
- PrescriptionItem
- TherapistMessage
- TherapistPatientHealthProfile
- SessionLog
- SessionLogItem
- ProgressReport

## Known Issues / Risks
- PatientProfile stores a raw password field separate from Django auth; risk of plaintext storage and inconsistent auth flows (strength_app/models.py).
- Dual therapist concepts (strength_app.TherapistProfile vs therapist_app.Therapist) can diverge and cause data confusion.
- Validators mismatch between model and migration: PatientProfile age min is 13 in model, 10 in migration (strength_app/models.py vs 0001_initial.py).
- Choices mismatch in SessionFeedback pain_reported: model choices differ from migration values; legacy rows may become invalid in forms/admin (strength_app/models.py vs 0001_initial.py).
- Missing validators on numeric fields allow negative or zero values (FoodItem macros, ExerciseExecution prescribed_* fields, WorkoutSession xp_earned, GateTestResult depth_achieved, etc.).
- JSONField data has no schema validation (fitness_level_json, exercises_json, current_prescription_json, etc.); malformed data can crash downstream logic.
- PatientProfile.user is optional; therapist_app links patients to User while strength_app logic often uses PatientProfile, risking incomplete linkage.
- SessionFeedback.save always recomputes traffic_light; failures in v1_safety_logic can block saves.

## Test Coverage Suggestions
- Model validation tests for min/max constraints (age, difficulty_tolerance, pain).
- Ensure password handling uses Django User password hashing (no plaintext).
- JSON structure validation tests (prescriptions, fitness levels, progression history).
- Cross-model integrity tests (TherapistPatientLink -> User -> PatientProfile existence).
- Migration/data compatibility tests for SessionFeedback pain_reported values and PatientProfile age constraints.
- Food/nutrition logging tests for negative or zero quantities and macro calculations.

## Tests Added (Targeted Model Tests)
- strength_app/tests/test_models.py
- therapist_app/test_models.py

## Test Execution Status
- Targeted Group 2 model tests passed (10 tests).
- Full app test run failed due to missing staticfiles manifest entry for strength_app/manifest.json in template rendering.

Commands run:
```
DJANGO_SECRET_KEY=test DJANGO_DEBUG=True python manage.py test strength_app.tests.test_models therapist_app.test_models
```

## Security/Robustness Notes
- Remove or encrypt PatientProfile.password and rely on Django auth only.
- Add MinValueValidator(0 or 1) to numeric fields that should not be negative.
- Consider schema validation for JSONFields (pydantic, model clean(), or service layer validation).
- Normalize model choice values and ensure migrations reflect any changes.

## Data Integrity
- Ensure therapist-managed flows always create matching User + PatientProfile rows.
- Consider unique constraints where duplicates can occur (FoodItem name, daily food logs per meal/date).
- Add indexes on frequent query fields (patient, session_date, log_date) if performance issues appear.
