# Group 5 - Feature Modules and Content Libraries

This file catalogs Group 5 (feature logic, content libraries, and domain configs) for the Vyayam codebase.

## Scope
- [strength_app/v1_nutrition_engine.py](strength_app/v1_nutrition_engine.py)
- [strength_app/v1_gamification.py](strength_app/v1_gamification.py)
- [strength_app/v1_football_constants.py](strength_app/v1_football_constants.py)
- [strength_app/v1_prescription_engine.py](strength_app/v1_prescription_engine.py)
- [strength_app/v1_safety_logic.py](strength_app/v1_safety_logic.py)
- [strength_app/exercise_content.py](strength_app/exercise_content.py)
- [strength_app/exercise_content_gap_fill.py](strength_app/exercise_content_gap_fill.py)
- [strength_app/exercise_tags.py](strength_app/exercise_tags.py)
- [strength_app/exercise_progressions.py](strength_app/exercise_progressions.py)
- [strength_app/red_flag_map.py](strength_app/red_flag_map.py)
- [strength_app/warmup_library.py](strength_app/warmup_library.py)
- [strength_app/stretching_protocol.py](strength_app/stretching_protocol.py)
- [strength_app/stretch_pdf.py](strength_app/stretch_pdf.py)
- [strength_app/equipment_routing.py](strength_app/equipment_routing.py)

## Purpose Summary
- Nutrition macro targets, daily log summary, and mess guidance text for athletes.
- Gamification metrics for XP, streaks, and pattern ranks.
- Football assessment thresholds and training protocol configuration.
- Safety and personalization logic used by the V1 prescription engine.
- Exercise content, progressions, and tagging metadata for prescriptions and UI.
- Warm-up, cool-down, stretching protocol content, and PDF reporting.

## Key Flows
1) Nutrition goal or training goal -> macro targets -> daily summary -> guidance text.
2) V1 session generation -> safety checks -> red-flag filtering -> dosage and warm-up/cool-down.
3) Pre-match stretching -> stretch execution -> PDF report download.
4) Exercise content lookup -> UI execution pages -> therapist/coach libraries.

## Known Issues / Risks
- reportlab is imported for PDF generation but is not listed in [requirements.txt](requirements.txt); the PDF endpoint will error and tests cannot import [strength_app/stretch_pdf.py](strength_app/stretch_pdf.py#L1-L16) unless the dependency is installed.
- compute_session_xp always returns at least base XP, even when all form scores are below MIN_FORM_SCORE_FOR_XP, which contradicts the safety gate comment and can reward unsafe form ([strength_app/v1_gamification.py](strength_app/v1_gamification.py#L226-L248)).
- red flag exclusions include mixed-case exercise IDs like lateral_Hops that do not match the lowercase IDs used elsewhere, so some exclusions may never apply ([strength_app/red_flag_map.py](strength_app/red_flag_map.py#L8-L16)).
- check_deload_needed falls back to patient.periodisation_state, but the related_name is periodisation; callers that do not pass a state will skip mandatory deload checks ([strength_app/v1_safety_logic.py](strength_app/v1_safety_logic.py#L286-L296), [strength_app/models.py](strength_app/models.py#L333-L343)).
- get_daily_nutrition_summary marks traffic_light as red when targets are missing (target_calories == 0), which can mislead new patients without profiles ([strength_app/v1_nutrition_engine.py](strength_app/v1_nutrition_engine.py#L202-L213)).

## Test Coverage Suggestions
- compute_session_xp returns 0 when all form scores are below MIN_FORM_SCORE_FOR_XP.
- red_flag_map get_pattern_level_caps caps progression levels as expected.
- exercise_progressions classify_performance uses dosage_by_capability when level_data is provided.
- generate_mess_guidance falls back to default text when nutrition_profile is missing.

## Tests Present (Targeted Group 5)
- [strength_app/tests/test_group5.py](strength_app/tests/test_group5.py)

## Test Details (Targeted Group 5)
- Nutrition macros: kidney protein cap, daily summary targets, mess guidance mode.
- Gamification: XP tally, streak count, asymmetry description.
- Safety logic: hormonal phase stale data, return-session adjustments, deload trigger, new exercise cap.
- Prescription engine: mobility-only session on severe menstruation.
- Stretching protocol totals and PDF generation output.
- Equipment routing mapping integrity.
- Red flag exclusion sample.
- Exercise content and tags baseline checks.
- Football assessment constants scoring bands.

## Test Execution Status
- Not run. reportlab is missing from the environment and from [requirements.txt](requirements.txt), so importing [strength_app/stretch_pdf.py](strength_app/stretch_pdf.py#L1-L16) fails.

Suggested command once the dependency is added:
```
DJANGO_SECRET_KEY=test DJANGO_DEBUG=True python manage.py test strength_app.tests.test_group5
```

## Security/Robustness Notes
- Treat reportlab as a required dependency or add a guarded import to prevent PDF endpoint failures.
- Normalize exercise IDs in red flag lists to match the registry and tags.

## Data Integrity
- Align periodisation fallback attribute naming with the related_name to ensure deload enforcement remains consistent when state is not passed.