# VYAYAM — Security Audit Report

**Date:** 2026-06-23  
**Scope:** Full defensive security audit of the VYAYAM Django codebase (physiotherapy / clinical platform handling patient health data under India's DPDPA 2023).  
**Mode:** READ-ONLY. No source file was edited, renamed, or deleted; no data-mutating command was run. This report is the only file created.  
**Stack:** Django 4.2.30, Python 3.12, `vyayam_project/` settings, **two apps** — `strength_app/` (patient-facing + coach console) and `therapist_app/` (clinician console). SQLite in dev; Postgres (`DATABASE_URL`) in prod.

**Method:** Every `urls.py` was enumerated and each view read for (1) authentication, (2) role enforcement, (3) object-ownership scoping. Models, admin, templates, middleware, settings, and dependency pins were reviewed. `manage.py check --deploy` was run. Findings were produced by a fan-out of 13 read-only review agents over disjoint slices of the code; the single High finding was independently re-verified against the database contents, and the lead auditor independently re-read the highest-risk access-control, auth, and XSS code paths to confirm the conclusions below.

> **Two corrections to the engagement brief, established by reading the code:**
> 1. The app is **not** a single app — there are two: `strength_app` and `therapist_app`. Both are audited here.
> 2. The working tree is **not** a git repository (`git` is not initialized) and there is **no `.gitignore`** — this materially changes finding E-1 (below).

## 1. Executive Summary

**Overall posture: substantially hardened.** The prior remediation passes (SEC-1…7, the DA-* and R2-* series) are real and effective. The canonical threat for this platform — broken object-level access control (IDOR/BOLA) — is **well-defended**: across all 120 URL patterns, every patient data view resolves objects through the session-bound patient (`request.session['patient_id']` via `_require_patient`), every therapist view is gated by `@therapist_required` and routes patient access through the `get_linked_patient_or_404` cross-therapist firewall, and the coach console enforces a `CoachPatientLink` ownership check. Spot-checked IDOR candidates (`view_report`, `download_report`, `v1_session_detail`, `match_delete`, `alert_mark_reviewed`, `coach_athlete_detail`) are all correctly owner-scoped. Authentication is strong: Django PBKDF2-SHA256 hashing (confirmed in the DB), login/forgot/reset/change rate-limiting, `session.flush()` on login/logout, `cycle_key()` on password change, and a password-reset token that is 256-bit, single-use, 1-hour-expiry, with sibling-token invalidation. CSRF is enforced globally with **zero `@csrf_exempt`** and `{% csrf_token %}` present in all 35 POST forms.

**No Critical findings.** The single High is a data-at-rest / repository-hygiene exposure, not an application access-control hole. The remaining issues are 6 Medium and a tail of Low/Info hardening items.

### Counts by severity

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 1 |
| Medium | 6 |
| Low | 23 |
| Info | 16 |
| **Total** | **46** |

### Top 5 to fix first

1. **[High] Live patient PII/clinical data in `db.sqlite3` at repo root, no `.gitignore`, git uninitialized** (E-1). A 636 KB SQLite DB with real names, emails, phone-login identities, PBKDF2 hashes, and clinical tables (pain location/severity, hormonal phase, prescriptions, reports) sits in the project root. The instant anyone runs `git init && git add .`, this is captured into history. *Fix: add a `.gitignore` (covering `*.sqlite3`, `.env*`, `.DS_Store`, `/media`, `/staticfiles`) before any `git init`; remove the DB from the tree; use Postgres for any shared environment; treat the file as a potential breach.*
2. **[Medium] Therapist clinical PDF reports served from `/media/` with no auth/ownership gate** (E-2; see also category G). `ProgressReport.pdf` (`upload_to='therapist_reports/'`) is linked via raw `{{ r.pdf.url }}`; Django only serves `/media/` under `DEBUG`, so production serving is delegated to the web server with no `@therapist_required` / `get_linked_patient_or_404` check. *Fix: stream PDFs through an authenticated, ownership-scoped view (X-Accel-Redirect / FileResponse); deny direct `/media/therapist_reports/` access.*
3. **[Medium] Athlete-tier self-promotion** (H-1). `football_assessment_results` sets `patient.athlete_tier_active = True` with no re-check of the clinical `athlete_tier_eligible` gate (enforced only at `football_sport_select`); a non-eligible patient who navigates the assessment URLs directly is routed into higher-intensity athlete programming they were never cleared for. *Fix: replicate the eligibility guard across the whole football-assessment flow.*
4. **[Medium] Stored XSS via `rx_items_json`** (D-1). The Program Builder emits `const initial = {{ rx_items_json|safe }};` inside `<script>` from `json.dumps(...)` (which does not escape `</script>`); the serialized `notes`/`exercise_name`/`tempo` come verbatim from therapist POST in `save_program`. *Fix: use `{% json_script %}` (or the `.replace('<','\u003c')` guard already used in `vyayam_filters.cv_config_json`); enforce CSP.*
5. **[Medium] Transport & CSP hardening** (E-3 + F-1). `SECURE_SSL_REDIRECT` defaults False (deploy check emits `security.W008`) and no `SECURE_PROXY_SSL_HEADER` is set — behind Render's TLS-terminating proxy, HSTS/redirect/Secure-cookies may not engage (E-3); **and** CSP is `Report-Only` with `'unsafe-inline'`, so it provides no XSS backstop (F-1). *Fix: set `SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')`, `DJANGO_SSL_REDIRECT=true`; move toward an enforcing, nonce-based CSP.*

## 2. Deliverable 1 — Per-View Authorization Matrix

All 120 URL patterns across the three `urls.py` files. `Login` = authentication required; `Role` = role enforced (patient / coach / therapist / admin / none); `Own` = object-ownership scoping (N-A when the view takes no object id). Rows marked in the **Notes** as WEAK/finding are carried into §3.

### Project-level

| URL pattern | View | Methods | Login | Role | Own | Notes |
|---|---|---|---|---|---|---|
| `/admin/` | `django.contrib.admin` | GET,POST | yes | admin (is_staff) | N-A | Django admin, staff/superuser-gated; not reachable by patient/therapist/coach sessions. See I/E notes (password field editable; audit rows mutable). |
| `/sw.js` | `django.views.static.serve` (fixed path) | GET | public-by-design | none | N-A | PWA service worker served from a hard-coded static path; no user input. OK. |

### Patient — Authentication, Account & Legal

| URL pattern | View | Methods | Login | Role | Own | Notes |
|---|---|---|---|---|---|---|
| `/` | `strength_app.views.home` | GET | public-by-design | none | N-A | OK — flushes any stale patient session on landing (views.py:1413-1414); no object lookup. |
| `/register/` | `strength_app.views.patient_register` | GET | public-by-design | none | N-A | OK — pure redirect to onboarding_start (views.py:95-97). No rate_limit, but no mutation here; actual registration happens in onboarding flow (out of scope). |
| `/login/` | `strength_app.views.patient_login` | GET,POST | public-by-design | none | N-A | OK — check_password hashing (views.py:58), session.flush() before setting patient_id = fixation defense (views.py:60-61), rate_limit 5/5min (views.py:43), generic error messages (no enumeration). |
| `/logout/` | `strength_app.views.patient_logout` | GET | no | none | N-A | Logout flushes session correctly (views.py:1423) but is GET-accessible (no @require_POST) — CSRF logout possible (low impact). |
| `/forgot-password/` | `strength_app.views.forgot_password` | GET,POST | public-by-design | none | N-A | OK — no user enumeration (sent=True always, views.py:162), rate_limit 5/5min (views.py:121), token via secrets.token_urlsafe(32) (views.py:140). |
| `/reset-password/<token>/` | `strength_app.views.reset_password` | GET,POST | no (token-auth) | none | yes (token->patient FK) | OK — token entropy secrets.token_urlsafe(32), is_valid() enforces 1h expiry + single-use (models.py:1421-1425), used=True after reset, sibling tokens invalidated (views.py:193-198). rate_limit 10/5min. |
| `/change-password/` | `strength_app.views.change_password` | GET,POST | yes | patient | yes (session patient only) | Operates only on session patient (views.py:1846-1849); requires current password; cycle_key() after change (views.py:1871). WEAK: min length 6 and no complexity check (views.py:1860) vs 8+mix elsewhere. |
| `/delete-account/` | `strength_app.views.delete_account` | GET,POST | yes | patient | yes (session patient only) | OK — re-auth with password (views.py:1812), session flush before delete, deletes only session patient (views.py:1803,1816). Not @require_POST but destructive branch is POST-gated so CSRF token applies. |
| `/dashboard/` | `strength_app.views.dashboard` | GET | yes | patient | N-A | OK — checks session patient_id, redirects to login if absent (views.py:207-209), then redirects to v1_dashboard. No object lookup. |
| `/offline/` | `strength_app.views.offline` | GET | public-by-design | none | N-A | OK — static offline fallback page (views.py:100-102). |
| `/healthz/` | `strength_app.views.healthz` | GET | public-by-design | none | N-A | OK — unauthenticated by design, runs SELECT 1, returns ok/degraded only, no data leak (views.py:105-114). |
| `/privacy/` | `strength_app.views.privacy_policy` | GET | public-by-design | none | N-A | OK — static template render (views.py:1786-1787). |
| `/terms/` | `strength_app.views.terms_of_service` | GET | public-by-design | none | N-A | OK — static template render (views.py:1790-1791). |
| `/disclaimer/` | `strength_app.views.disclaimer` | GET | public-by-design | none | N-A | OK — static template render (views.py:1794-1795). |

### Patient — Onboarding (10-screen clinical assessment)

| URL pattern | View | Methods | Login | Role | Own | Notes |
|---|---|---|---|---|---|---|
| `/onboarding/start/` | `v1_onboarding_views.onboarding_start` | GET | public-by-design | none | N-A | OK — pre-auth entry; if a session patient_id exists with a StrengthProfile, redirects to dashboard; only looks up own session patient_id (line 409-417). |
| `/onboarding/identity/` | `v1_onboarding_views.onboarding_identity` | GET,POST | public-by-design | none | yes | Registration: creates PatientProfile (line 543) or updates the session's OWN existing_pid only (line 507) — scoped, no IDOR. Rate-limited 3/600s (line 429). biological_sex unvalidated (Finding E/H). No privileged fields from POST. |
| `/onboarding/training-history/` | `v1_onboarding_views.onboarding_training_history` | GET,POST | yes | patient | N-A | OK — _require_patient (line 572); mutates only the session-owned patient. No object id in URL. Only training fields set from POST. |
| `/onboarding/strength-test/` | `v1_onboarding_views.onboarding_strength_test` | GET,POST | yes | patient | N-A | OK — _require_patient (line 602); restores own raw_test_data_json into session. No object id. |
| `/onboarding/strength-test-execute/<int:test_index>/` | `v1_onboarding_views.onboarding_strength_test_execute` | GET | yes | patient | N-A | OK — _require_patient (line 626); test_index indexes a static in-code list V1_STRENGTH_TESTS with a bounds check (line 630), not a DB object — no IDOR. Render-only. |
| `/onboarding/save-test-result/` | `v1_onboarding_views.onboarding_save_test_result` | POST | no | none | N-A | WEAK — no _require_patient gate before writing request.session['test_results'] (lines 788-807); DB persist is best-effort and swallows errors (lines 810-816). Self-session only, no cross-patient access. test_index clamped via safe_int. See Finding B. |
| `/onboarding/asymmetry/` | `v1_onboarding_views.onboarding_asymmetry` | GET,POST | yes | patient | yes | OK — _require_patient (line 848); StrengthProfile.update_or_create keyed on (patient=session patient, assessment_number=1) (line 907) — scoped to owner. fat_asymmetry_* set from POST (non-privileged). |
| `/onboarding/goals/` | `v1_onboarding_views.onboarding_goals` | GET,POST | yes | patient | N-A | OK — _require_patient (line 959); only goal_type/secondary/sport/competition_date set on own patient. competition_date parse guarded. |
| `/onboarding/equipment/` | `v1_onboarding_views.onboarding_equipment` | GET,POST | yes | patient | N-A | OK — _require_patient (line 1023); equipment/location/durations set on own patient; numeric inputs clamped via safe_int (lines 1032-1033). |
| `/onboarding/hormonal/` | `v1_onboarding_views.onboarding_hormonal` | GET,POST | yes | patient | N-A | OK — _require_patient (line 1055); redirects non-female to red_flags (line 1059); cycle fields clamped/parsed; own patient only. |
| `/onboarding/red-flags/` | `v1_onboarding_views.onboarding_red_flags` | GET,POST | yes | patient | N-A | OK with note — _require_patient (line 1161); clearing absolute_stop requires confirm_stop_clear + audited via RedFlagEvent and clinician Alert (lines 1176-1190, 1217). Self-clear is by design — see Finding (Info, cat H). |
| `/onboarding/lifestyle/` | `v1_onboarding_views.onboarding_lifestyle` | GET,POST | yes | patient | N-A | OK — _require_patient (line 1249); lifestyle fields on own patient; daily_sitting_hours clamped (line 1260). |
| `/onboarding/mind-muscle/` | `v1_onboarding_views.onboarding_mind_muscle` | GET,POST | yes | patient | N-A | OK — _require_patient (line 1364); only mind_muscle_glute/vmo set on own patient. |
| `/onboarding/nutrition/` | `v1_onboarding_views.onboarding_nutrition` | GET,POST | yes | patient | N-A | OK — _require_patient (line 1279); NutritionProfile.get_or_create(patient=own patient) (line 1307); weight/height parse guarded; goal validated against GOAL_NUTRITION (line 1293). |
| `/onboarding/complete/` | `v1_onboarding_views.onboarding_complete` | GET | yes | patient | N-A | OK — _require_patient (line 1386); athlete_tier_eligible SERVER-computed from own profile scores, saved with update_fields whitelist (lines 1438-1448) — not mass-assignable. No object id in URL. |

### Patient — Session Execution

| URL pattern | View | Methods | Login | Role | Own | Notes |
|---|---|---|---|---|---|---|
| `/v1/dashboard/` | `v1_session_views.v1_dashboard` | GET | yes | patient | N-A | OK. _require_patient gate (line 234); no URL object id; therapist_managed patients redirected out (line 238). All DB reads scoped to patient (lines 284,294). |
| `/v1/session/` | `v1_session_views.v1_session_overview` | GET | yes | patient | N-A | OK. _require_patient gate (line 413); no URL id; SessionFeedback read scoped to patient (line 434). |
| `/v1/session/warmup/` | `v1_session_views.v1_warmup` | GET | yes | patient | N-A | OK. _require_patient gate (line 537); writes warmup list into the caller's own session (line 542); no object id. |
| `/v1/session/warmup/exercise/<int:warmup_index>/` | `v1_session_views.v1_execute_warmup_exercise` | GET | yes | patient | N-A | OK. warmup_index indexes into request.session['v1_warmup_exercises'] (session-scoped list, line 563), NOT a DB row. Bounds checked (line 558); <int:> blocks negatives. No IDOR. |
| `/v1/session/exercise/<int:exercise_index>/` | `v1_session_views.v1_execute_exercise` | GET | yes | patient | N-A | OK. exercise_index indexes into request.session['v1_session']['working_sets'] (session-scoped list, line 636), NOT a DB row. Bounds checked (lines 630,633). No IDOR. |
| `/v1/session/save-exercise/` | `v1_session_views.v1_save_exercise_result` | POST | yes | patient | N-A | OK. _require_patient -> 401 JSON if unauth (line 674); POST-only enforced -> 405 (line 676); no @csrf_exempt (CSRF middleware active). Results written to caller's own session; inputs clamped via safe_int/safe_float. |
| `/v1/session/undo-last/` | `v1_session_views.v1_undo_last_result` | POST | yes | patient | N-A | OK. _require_patient gate (line 817); non-POST -> redirect (line 819); mutates only the caller's own session list (line 830). CSRF protected. |
| `/v1/session/cooldown/` | `v1_session_views.v1_cooldown` | GET | yes | patient | N-A | OK. _require_patient gate (line 844); reads only session data; no DB object by id. |
| `/v1/session/conditioning/` | `v1_session_views.v1_conditioning_session` | GET | yes | patient | N-A | OK. _require_patient gate (line 877); non-football patients redirected (line 882); GET 'protocol' param validated against CONDITIONING_PROTOCOLS allowlist (line 900). No object id. |
| `/v1/session/feedback/` | `v1_session_views.v1_post_session_feedback` | GET,POST | yes | patient | N-A | OK. _require_patient gate (line 933); WorkoutSession/SessionFeedback/ExerciseExecution all created with patient=patient (lines 977,1015,1041); numeric POST clamped. CSRF protected. No sensitive mass-assignment (only sleep_quality via safe map, line 1056). |
| `/v1/session/complete/` | `v1_session_views.v1_session_complete` | GET | yes | patient | no | feedback/workout fetched by pk WITHOUT patient scoping (lines 1104,1109). Ids come from request.session (not URL), so not URL-tamperable, but missing defense-in-depth ownership filter. See finding. |
| `/v1/session/pain-stop/` | `v1_session_views.v1_pain_stop` | GET | yes | patient | N-A | OK. _require_patient gate (line 204); renders static stop page; no object id. |
| `/v1/test-exercises/` | `v1_session_views.v1_test_list` | GET | no | none | N-A | Dev-only: Http404 unless settings.DEBUG (line 1349). No login/patient check, but unreachable in prod (DEBUG=False). Static content only. See Info finding. |
| `/v1/test-exercise/<str:exercise_id>/` | `v1_session_views.v1_test_exercise` | GET | no | none | N-A | Dev-only: Http404 unless settings.DEBUG (line 1308). exercise_id is a content-dict key (EXERCISE_METADATA/EXERCISE_CONTENT lookup), not a DB row; no PII. Unreachable in prod. See Info finding. |

### Patient — Progress / History / Profile

| URL pattern | View | Methods | Login | Role | Own | Notes |
|---|---|---|---|---|---|---|
| `/v1/progress/` | `v1_progress_views.v1_progress_dashboard` | GET | yes | patient | N-A | OK — _require_patient gates; all queries filter patient=patient (lines 128-202). No URL object id. |
| `/v1/history/` | `v1_progress_views.v1_session_history` | GET | yes | patient | N-A | OK — _require_patient gates; WorkoutSession.objects.filter(patient=patient) (line 294). No URL object id. |
| `/v1/history/<int:session_id>/` | `v1_progress_views.v1_session_detail` | GET | yes | patient | yes | OK — fetch scoped: WorkoutSession.objects.filter(patient=patient, pk=session_id).first(); Http404 when not owned (lines 329-333). No IDOR. |
| `/v1/progress/api/` | `v1_progress_views.v1_progress_api` | GET | yes | patient | N-A | OK — _get_patient + 401 JSON if absent (210-212); all data filtered patient=patient (214,231,238-240). Returns only current patient's data. |
| `/v1/profile/` | `v1_progress_views.v1_profile` | GET | yes | patient | N-A | OK — _require_patient gates; gamification computed for the session patient only (256-279). No URL object id. |
| `/v1/profile/edit/` | `v1_progress_views.v1_edit_profile` | GET,POST | yes | patient | yes | Writes scoped to session patient via save(update_fields=[...]) allowlist — NO mass-assignment of privileged fields. No @require_POST/explicit CSRF decorator; weak email validation. See findings. |

### Patient — Legacy Workout & Progress Reports

| URL pattern | View | Methods | Login | Role | Own | Notes |
|---|---|---|---|---|---|---|
| `/gate-testing/` | `strength_app.views.gate_testing` | GET,POST | yes | patient | N-A | OK — session patient_id check (line 353-355); patient loaded by own id (357); POST only seeds session, no object id taken. |
| `/execute-gate-test/<family_index>/<level_index>/` | `strength_app.views.execute_gate_test` | GET | yes | patient | N-A | OK — indices address into the caller's own session list (gate_families), not DB rows by id; auth checked (393-395). |
| `/save-gate-test-result/` | `strength_app.views.save_gate_test_result` | POST | yes | patient | N-A | Auth checked (462-464); writes scoped to own patient (GateTestResult/PFC created with patient=self). reps_completed not clamped (difficulty/pain are). Self-scoped business-logic note; no IDOR. |
| `/gate-test-results/` | `strength_app.views.gate_test_results` | GET | yes | patient | yes | OK — GateTestResult.objects.filter(patient=patient) (696); auth checked (685-687). |
| `/prescription/` | `strength_app.views.prescription` | GET,POST | yes | patient | N-A | OK — auth checked (759-761); operates on own patient only; no object id from URL. |
| `/daily-workout/` | `strength_app.views.daily_workout` | GET | yes | patient | N-A | OK — auth checked (825-827); reads own prescription from session/own patient row; no id taken. |
| `/execute-exercise/<exercise_index>/` | `strength_app.views.execute_exercise` | GET | yes | patient | N-A | OK — index addresses caller's own session list (workout_exercises); auth checked (925-927). |
| `/save-exercise-results/` | `strength_app.views.save_exercise_results` | POST (not enforced via decorator) | no | none | N-A | WEAK — reads patient_id but never rejects None (959); no @require_POST. Data written only to caller's own session, so no IDOR; see Low finding. |
| `/workout-complete/` | `strength_app.views.workout_complete` | GET,POST | yes | patient | N-A | Auth checked (990-992); WorkoutSession/ExerciseExecution created with patient=self. Persists client-trusted session metrics unvalidated (business-logic Low). No cross-patient access. |
| `/progress-reports/` | `strength_app.views.progress_reports` | GET | yes | patient | yes | OK — ProgressReport.objects.filter(patient=patient) (1363); auth checked (1358-1360). |
| `/generate-report/` | `strength_app.views.generate_report` | GET,POST | yes | patient | N-A | OK — auth checked (1442-1445); report created/owned by self; redirects to own report id. Not POST-restricted but only creates self-owned data. |
| `/view-report/<report_id>/` | `strength_app.views.view_report` | GET | yes | patient | yes | OK — get_object_or_404(ProgressReport, id=report_id, patient=patient) (1491) scopes to owner; canonical IDOR pattern correctly defended. |
| `/download-report/<report_id>/` | `strength_app.views.download_report` | GET | yes | patient | yes | OK — get_object_or_404(ProgressReport, id=report_id, patient=patient) (1511); no path traversal (text built in-memory). Cosmetic str/int annotation mismatch only (Info). |
| `/exercises/` | `strength_app.views.exercise_library` | GET | yes | patient | N-A | OK — auth checked (1377-1379); renders static registry metadata only, no per-patient object. |
| `/exercises/<exercise_id>/` | `strength_app.views.exercise_detail` | GET | yes | patient | N-A | OK — auth checked (1562-1564); exercise_id keys into static EXERCISE_METADATA dict, not a DB row by owner; no clinical data. |
| `/exercises/<exercise_id>/execute/` | `strength_app.views.exercise_execute` | GET | yes | patient | N-A | OK — auth checked (1595-1597); reads static exercise registry/content; no patient-owned object fetched by id. |
| `/stretch-protocol/` | `strength_app.views.stretch_protocol` | GET,POST | yes | patient | yes | OK — auth checked (1657-1659); past_sessions = StretchSession.objects.filter(patient=patient) (1667). |
| `/stretch-execute/<stretch_index>/` | `strength_app.views.stretch_execute` | GET | yes | patient | N-A | OK — index addresses static PRE_MATCH_STRETCHES list; auth checked (1681-1683). |
| `/save-stretch-result/` | `strength_app.views.save_stretch_result` | POST | yes | patient | N-A | OK — auth checked with 401 (1710-1712); POST enforced (1707); writes only to caller's own session, no DB object by id. |
| `/stretch-complete/` | `strength_app.views.stretch_complete` | GET,POST(consumes session) | yes | patient | N-A | OK — auth checked (1750-1752); StretchSession created with patient=self from own session results. |
| `/stretch-download-pdf/<session_id>/` | `strength_app.views.stretch_download_pdf` | GET | yes | patient | yes | OK — get_object_or_404(StretchSession, id=session_id, patient=patient) (1830) scopes to owner; PDF generated in-memory (no path traversal / arbitrary file read). |

### Patient — Football / Athlete Tier & Nutrition

| URL pattern | View | Methods | Login | Role | Own | Notes |
|---|---|---|---|---|---|---|
| `/football/sport-select/` | `v1_football_views.football_sport_select` | GET,POST | yes | patient | N-A | OK — session patient resolved via _get_patient (l.36-38); sport value whitelisted against SPORT_TYPES (l.48) before patient.save; athlete_tier_eligible read-only gate (l.40). |
| `/football/assessment/` | `v1_football_views.football_assessment` | GET,POST | yes | patient | N-A | OK — _get_patient gate (l.68-70); POST only writes to request.session, no DB object by id. |
| `/football/assessment/<int:test_index>/` | `v1_football_views.football_assessment_execute` | GET | yes | patient | N-A | OK — _get_patient gate (l.89-91); test_index bounds-checked against constant list (l.93), indexes a static constant array, not a per-user DB row. |
| `/football/save-test-result/` | `v1_football_views.football_save_test_result` | POST | yes | patient | N-A | OK — explicit anon-write rejection 401 (l.131-132), POST-only 405 (l.133-134), rate-limited (l.128); all writes go to request.session for the current session only, values clamped via safe_int (l.144-146). No DB object fetched by url id. |
| `/football/results/` | `v1_football_views.football_assessment_results` | GET | yes | patient | N-A | FootballProfile via get_or_create(patient=patient) (l.236) — owner-scoped; sets patient.athlete_tier_active=True (l.301) from own session flow (self-service tier unlock, no cross-user effect). See finding F-FB1. |
| `/football/nordic-camera-test/` | `v1_football_views.football_nordic_camera_test` | GET | yes | patient | N-A | OK — _get_patient gate (l.460-462); renders template only, saves nothing, takes no object id. |
| `/football/matches/` | `v1_football_views.match_calendar` | GET | yes | patient | yes | OK — MatchDate query filtered patient=patient (l.405); only the session patient's matches are listed. |
| `/football/matches/add/` | `v1_football_views.match_add` | POST | yes | patient | yes | OK — get_or_create(patient=patient, match_date=...) (l.434-438) binds new MatchDate to session patient; opponent string accepted unvalidated but stored as data only (no injection sink in view). |
| `/football/matches/delete/<int:match_id>/` | `v1_football_views.match_delete` | POST | yes | patient | yes | OK — NOT an IDOR. delete() filtered by BOTH id=match_id AND patient=patient (l.455); deleting another patient's match silently matches 0 rows. POST-only enforced (l.451-452). Relies on global CSRF middleware (no @csrf_exempt). |
| `/nutrition/` | `v1_nutrition_views.v1_nutrition_dashboard` | GET | yes | patient | N-A | OK — _require_patient gate (l.41-43); all summaries computed for the session patient only (l.48-61). |
| `/nutrition/log/` | `v1_nutrition_views.v1_food_log` | GET,POST | yes | patient | yes | OK — _require_patient gate (l.77-79); DailyFoodLog.create binds patient=patient (l.100-106); food_id looked up only within is_active catalog (l.99); quantity clamped (l.91-94). |
| `/nutrition/mess/` | `v1_nutrition_views.v1_mess_mode` | GET,POST | yes | patient | yes | OK — _require_patient gate (l.128-130); MessEntry.create binds patient=patient (l.149-155); recent list filtered patient=patient (l.161); food_ids resolved within is_active catalog (l.146). |
| `/nutrition/api/search/` | `v1_nutrition_views.v1_food_search_api` | GET | yes | patient | N-A | OK — anon read rejected 401 (l.177-178); returns only the shared, non-personal FoodItem catalog (l.184-202), no patient PII; query length-gated (l.181). |
| `/nutrition/api/quick-log/` | `v1_nutrition_views.v1_quick_log_api` | POST | yes | patient | yes | OK — @require_POST (l.209) + rate_limit (l.210) + _require_patient 401 (l.213-214); DailyFoodLog.create binds patient=patient (l.250-256); qty/meal/date all validated (l.220-239). Returned summary scoped to session patient (l.258). Relies on global CSRF middleware (no @csrf_exempt). |

### Patient (in-clinic, therapist-driven) Session

| URL pattern | View | Methods | Login | Role | Own | Notes |
|---|---|---|---|---|---|---|
| `/therapist-session/today/` | `v1_therapist_session_views.therapist_session_today` | GET | yes | patient | yes | OK. _require_patient gates on session patient_id + therapist_managed; _active_link scopes the link to patient.user_id; all SessionLog/Prescription reads flow from that link. No URL object id. |
| `/therapist-session/start/` | `v1_therapist_session_views.therapist_session_start` | POST | yes | patient | yes | OK as @require_POST (line 171). SessionLog created against the patient's own _active_link / _latest_published_prescription. Minor: link may be None -> see finding TS-1. |
| `/therapist-session/exercise/<int:idx>/` | `v1_therapist_session_views.therapist_session_exercise` | GET | yes | patient | yes | OK. idx is a bounds-checked list index (line 222), not a DB id; state validated against own rx.id (line 217). No object fetched by URL id. |
| `/therapist-session/feedback/<int:idx>/` | `v1_therapist_session_views.therapist_session_feedback` | GET,POST | yes | patient | yes | Ownership OK: log_item_id comes from server-side state['log_item_ids'][idx] (line 323), idx bounds-checked (line 318), state matched to own rx (line 313). POST mutation (pain/difficulty/sets) on GET-allowed view; see TS-2. |
| `/therapist-session/complete/` | `v1_therapist_session_views.therapist_session_complete` | GET,POST | yes | patient | yes | Ownership OK: log fetched by state['log_id'] (line 377), state matched to own rx (line 373). POST mutates SessionLog without @require_POST; see TS-2. |
| `/therapist-session/finished/` | `v1_therapist_session_views.therapist_session_finished` | GET | yes | patient | N-A | OK. Read-only confirmation; last_log scoped to own link (lines 413-419). No object id in URL. |
| `/therapist-session/progress/` | `v1_therapist_session_views.therapist_session_progress` | GET | yes | patient | N-A | OK. All aggregates filtered by link=_active_link(patient); SessionLogItem queries scoped to own-link log ids (lines 466-473). No object id in URL. |
| `/therapist-session/profile/` | `v1_therapist_session_views.therapist_session_profile` | GET,POST | yes | patient | yes | Ownership OK: TherapistMessage created against own link with sender=own user_id (lines 560-565); link from _active_link. POST mutation without @require_POST; see TS-2. Manual POST read of 'message' only (no sensitive fields). |

### Coach Console (`@coach_required`, Django auth + TherapistProfile)

| URL pattern | View | Methods | Login | Role | Own | Notes |
|---|---|---|---|---|---|---|
| `/coach/login/` | `v1_coach_views.coach_login` | GET,POST | public-by-design | none | N-A | OK — rate-limited (5/300s), session.flush() on login, requires user with strength_app.TherapistProfile. Lines 172-188. |
| `/coach/logout/` | `v1_coach_views.coach_logout` | GET,POST | no | none | N-A | Logout via GET (no @require_POST). Low-risk logout CSRF only; clears session. Lines 191-193. |
| `/coach/squad/` | `v1_coach_views.coach_squad` | GET | yes | coach | yes | OK — lists ONLY CoachPatientLink rows for request.therapist (is_active=True). Lines 200-256. |
| `/coach/athlete/<str:patient_id>/` | `v1_coach_views.coach_athlete_detail` | GET | yes | coach | yes | OK — second get_object_or_404 on CoachPatientLink(coach=request.therapist, patient, is_active=True) enforces cross-coach firewall. Lines 263-266. |
| `/coach/athlete/<str:patient_id>/override/` | `v1_coach_views.coach_override_prescription` | GET,POST | yes | coach | yes | Ownership enforced (line 451). No @require_POST but branches on method; CSRF via global middleware. Exercise payload validated. Lines 448-533. |
| `/coach/athlete/<str:patient_id>/flag/` | `v1_coach_views.coach_flag_review` | POST | yes | coach | yes | Ownership by coach FK match, but filter OMITS is_active=True (line 539-541) — a deactivated coach can still flag. Minor scope gap. |
| `/coach/athlete/<str:patient_id>/competition/` | `v1_coach_views.coach_set_competition` | POST | yes | coach | yes | Ownership by coach FK match, filter OMITS is_active=True (line 553). Writes shared PatientProfile.competition_date. Date parsed safely. Minor scope gap. |
| `/coach/athlete/<str:patient_id>/notes/` | `v1_coach_views.coach_save_notes` | POST | yes | coach | yes | Ownership by coach FK match, filter OMITS is_active=True (line 697-699). Minor scope gap; notes scoped to this coach's own link. |
| `/coach/add-athlete/` | `v1_coach_views.coach_add_athlete` | GET,POST | yes | coach | N-A | Creates new PatientProfile + CoachPatientLink to self. No @require_POST but branches on method; CSRF via global middleware. Sets athlete_tier_eligible=True hardcoded (not from POST). Lines 570-686. |

### Therapist Console (`@therapist_required`, Django auth + Therapist)

| URL pattern | View | Methods | Login | Role | Own | Notes |
|---|---|---|---|---|---|---|
| `/therapist/login/` | `therapist_app.views.therapist_login` | GET,POST | public-by-design | none | N-A | OK. Rate-limited (5/300s). authenticate() then requires hasattr(user,'therapist') before login; session.flush() on success prevents fixation. |
| `/therapist/logout/` | `therapist_app.views.therapist_logout` | GET,POST | no | none | N-A | Logout via GET (not @require_POST). logout() of an unauthenticated session is a no-op, so impact is nil, but a GET logout is CSRF-able (nuisance only). Low. |
| `/therapist/ and /therapist/dashboard/` | `therapist_app.views.dashboard` | GET | yes | therapist | N-A | OK. Links scoped to therapist.patient_links; Alert counts filtered link__in=links (own patients only). |
| `/therapist/patients/` | `therapist_app.views.patient_list` | GET | yes | therapist | N-A | OK. therapist.patient_links scoped to current therapist. |
| `/therapist/library/` | `therapist_app.views.library` | GET | yes | therapist | N-A | OK. Static exercise catalog only; no patient data. |
| `/therapist/reports/` | `therapist_app.views.reports` | GET | yes | therapist | N-A | OK. ProgressReport filtered link__therapist=therapist. |
| `/therapist/settings/` | `therapist_app.views.settings_page` | GET | yes | therapist | N-A | OK. Read-only own-therapist data. |
| `/therapist/patients/invite/` | `therapist_app.views.invite_patient` | POST | yes | therapist | N-A | OK. @require_POST + therapist-scoped link create; seat-limit enforced; phone validated. CSRF protected. Reuses existing User on username collision (see finding H-13). |
| `/therapist/patients/<link_id>/accept/` | `therapist_app.views.simulate_accept_invite` | POST | yes | therapist | yes | Auth'd + @require_POST. Ownership via get_object_or_404(...therapist=therapist). Generates 8-char activation password shown in flash; does NOT set must_change_password on new profile (see E-5, B-5). |
| `/therapist/patient/<link_id>/` | `therapist_app.views.patient_detail` | GET | yes | therapist | yes | OK. get_linked_patient_or_404 enforces cross-therapist firewall; UUID link_id. |
| `/therapist/patient/<link_id>/onboarding/save/` | `therapist_app.views.save_onboarding` | POST | yes | therapist | yes | OK. get_linked_patient_or_404 + @require_POST. Manual field assignment but only clinical/demographic fields; no privilege fields. affected_side whitelisted. |
| `/therapist/patient/<link_id>/program/save/` | `therapist_app.views.save_program` | POST | yes | therapist | yes | OK. get_linked_patient_or_404 + @require_POST. JSON body validated via _safe_int clamps; exercise metadata resolved from server catalog, not client. |
| `/therapist/patient/<link_id>/messages/send/` | `therapist_app.views.send_message` | POST | yes | therapist | yes | OK. Thread scoped to link via get_linked_patient_or_404; message attached to that link only. No cross-pair leakage. CSRF protected. |
| `/therapist/patient/<link_id>/reports/generate/` | `therapist_app.views.generate_report` | POST | yes | therapist | yes | OK. get_linked_patient_or_404 + @require_POST. PDF built only from this link's data. |
| `/therapist/patient/<link_id>/reset-password/` | `therapist_app.views.reset_patient_password` | POST | yes | therapist | yes | Auth'd + scoped + @require_POST. Sets must_change_password=True (good). Temp password shown in plaintext flash message (see E-4). |
| `/therapist/alerts/` | `therapist_app.views.alerts_inbox` | GET | yes | therapist | N-A | OK. Alert.objects.filter(link__therapist=therapist) — own patients only. |
| `/therapist/alerts/<alert_id>/reviewed/` | `therapist_app.views.alert_mark_reviewed` | POST | yes | therapist | yes | OK. INT alert_id but scoped: Alert.objects.filter(pk=alert_id, link__therapist=request.user.therapist); 404 if not owned. @require_POST + CSRF. Open-redirect note in A-3. |
| `/therapist/patient/<link_id>/program/copy-week/` | `therapist_app.views.copy_previous_week` | POST | yes | therapist | yes | OK. get_linked_patient_or_404 + @require_POST. Source/target prescriptions tied to the scoped link. |
| `/therapist/patient/<link_id>/notes/add/` | `therapist_app.views.add_visit_note` | POST | yes | therapist | yes | OK. get_linked_patient_or_404 + @require_POST. Note truncated to 5000 chars. |

## 3. Deliverable 2 — Findings by Category

Severity order within each category: Critical → High → Medium → Low → Info. Every finding cites file:line. `(NEEDS VERIFICATION)` marks claims that depend on runtime/deployment state not provable from source alone.

### A. Access Control / IDOR

#### A-1 · 🔵 Low — v1_session_complete fetches SessionFeedback/WorkoutSession by pk without patient scoping (missing defense-in-depth)
- **Location:** `strength_app/v1_session_views.py:1102-1111`
- **What:** In v1_session_complete the feedback and workout objects are fetched with SessionFeedback.objects.get(pk=feedback_id) and WorkoutSession.objects.get(pk=workout_id) where feedback_id/workout_id come from request.session ('v1_feedback_id'/'v1_workout_id'). There is no patient=patient filter on either get(), so the lookup does not enforce that the fetched record belongs to the logged-in patient.
- **How it could be abused:** Because the ids are read from the server-side session (written only by the same patient's own POST in v1_post_session_feedback at lines 1063-1064), this is not directly reachable by URL tampering. The residual risk is defense-in-depth only: if a session were ever populated with another patient's workout/feedback id (e.g. a future session-reuse bug or session fixation), the completion page would render that other patient's session metrics. No id is taken from the URL here.
- **Recommended fix (not applied):** Scope both lookups to the authenticated owner: SessionFeedback.objects.get(pk=feedback_id, patient=patient) and WorkoutSession.objects.get(pk=workout_id, patient=patient), falling back to None on DoesNotExist as already done.

#### A-2 · 🔵 Low — Three coach mutation endpoints scope by coach FK but omit is_active=True, unlike athlete_detail/override
- **Location:** `strength_app/v1_coach_views.py:539-541 (coach_flag_review), 553 (coach_set_competition), 697-699 (coach_save_notes)`
- **What:** coach_athlete_detail (line 266) and coach_override_prescription (line 451) require the CoachPatientLink to be is_active=True, but coach_flag_review, coach_set_competition, and coach_save_notes only match get_object_or_404(CoachPatientLink, coach=request.therapist, patient...) WITHOUT is_active=True. The cross-coach firewall (coach FK match) still holds, so this is NOT a cross-coach IDOR — a coach can only touch links that belong to them. The gap is that a coach whose link to an athlete was deactivated (is_active=False) can still flag, set a competition date, or rewrite notes on that athlete, where the read view would 404. Inconsistent enforcement of the active-link contract.
- **How it could be abused:** A coach who has been removed from an athlete (link deactivated) could still POST to the flag, competition, or notes endpoints for that athlete and mutate their record, even though they can no longer open the athlete detail page. Limited blast radius: only that coach's own previously-linked athletes, not other coaches' athletes.
- **Recommended fix (not applied):** Add is_active=True to the get_object_or_404 filters in coach_flag_review (line 539), coach_set_competition (line 553), and coach_save_notes (line 697) so all coach mutations require an active link, matching coach_athlete_detail and coach_override_prescription.

#### A-3 · 🔵 Low — Unvalidated 'next' redirect target on alert_mark_reviewed
- **Location:** `therapist_app/views.py:371 (alert_mark_reviewed)`
- **What:** After marking an alert reviewed, the view redirects to request.POST.get('next') with no allow-list or is_safe_url() check (line 371). The fallback is a safe local path, but a supplied 'next' is followed verbatim.
- **How it could be abused:** An attacker who can craft a POST form (e.g. via a CSRF-style lure, though CSRF tokens are required) or otherwise control the 'next' param could send a logged-in therapist to an attacker-controlled site after the action — a phishing/open-redirect vector. Impact is limited because CSRF protection guards the POST.
- **Recommended fix (not applied):** Validate next with django.utils.http.url_has_allowed_host_and_scheme(next, allowed_hosts={request.get_host()}) and fall back to /therapist/alerts/ when it fails.

#### A-4 · ⚪ Info — download_report signature annotates report_id as str but URL uses <int>; no security impact
- **Location:** `strength_app/views.py:1501 (download_report signature) vs strength_app/urls.py:136`
- **What:** download_report is declared `def download_report(request, report_id: str)` yet urls.py routes it via `<int:report_id>`, so Django coerces the value to int before the view runs. The ownership filter `get_object_or_404(ProgressReport, id=report_id, patient=patient)` still scopes correctly. The annotation mismatch is cosmetic and does not weaken access control.
- **How it could be abused:** No abuse path — the int converter rejects non-numeric input at routing time and the query is owner-scoped, so cross-patient report download is not possible.
- **Recommended fix (not applied):** Correct the type annotation to `report_id: int` for clarity; no functional change required.

#### A-5 · ⚪ Info — Local _require_patient duplicates the shared helper and adds a therapist_managed gate; verify parity with v1_session_views._require_patient
- **Location:** `strength_app/v1_therapist_session_views.py:43-53`
- **What:** This module defines its own _require_patient (lines 43-53) instead of importing strength_app/v1_session_views.py's helper. It returns (patient, error) like the canonical one, gates on session patient_id, and additionally redirects non-therapist_managed patients to v1_dashboard (line 52). Functionally it correctly enforces a patient session and the right sub-role, so access control is sound for this module. The note is that having two divergent copies of the auth helper risks future drift (e.g. if the canonical one gains an account-status/lockout check that this copy lacks).
- **How it could be abused:** No direct abuse; divergence could later allow a disabled/suspended patient account to retain access here if the canonical helper adds a status check that this duplicate omits.
- **Recommended fix (not applied):** Consolidate on the shared helper (import from v1_session_views) and layer the therapist_managed check on top, so future auth changes apply uniformly.

### B. Auth & Session

#### B-1 · 🔵 Low — Weaker password policy in change_password than register/reset
- **Location:** `strength_app/views.py:1860`
- **What:** The change_password view only requires a new password of length >= 6 with no complexity check, whereas registration and reset_password require >= 8 characters AND a mix of letters and numbers (views.py:182-185). A logged-in patient can downgrade their account to a 6-character, all-digit or all-letter password.
- **How it could be abused:** A patient (or an attacker who has hijacked a session) can set a trivially guessable 6-character password, weakening resistance to credential-stuffing or offline brute-force if the hash leaks. It also creates policy drift that undermines the stronger rules enforced elsewhere.
- **Recommended fix (not applied):** Apply a single shared password-policy helper across register, reset_password, and change_password: minimum 8 chars and require a mix of letters and digits (mirror the checks at views.py:182-185).

#### B-2 · 🔵 Low — save_exercise_results does not reject unauthenticated requests and is not POST-restricted
- **Location:** `strength_app/views.py:952-985 (save_exercise_results)`
- **What:** Unlike sibling endpoints, save_exercise_results reads request.session.get('patient_id') into a variable but never checks for None. An unauthenticated client can POST and have their submitted rep counts written into their own session under 'exercise_results'. The handler also lacks @require_POST (only an inner `if request.method == 'POST'`). Data impact is bounded because the values are written ONLY to the caller's own session (request.session['exercise_results']) and no object is fetched or written by id, so there is no cross-patient (IDOR) exposure here.
- **How it could be abused:** An anonymous user can seed arbitrary green/yellow/red rep and form-score values into their own session; if they later authenticate and reach workout_complete those self-reported numbers are persisted to their own WorkoutSession/ExerciseExecution, inflating their own progress metrics. There is no path to read or write another patient's data through this view.
- **Recommended fix (not applied):** Add the same early guard used elsewhere (`if not patient_id: return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)`) and decorate with @require_POST so non-POST verbs are rejected before any body parsing.

#### B-3 · 🔵 Low — onboarding_save_test_result writes to session before any auth gate; no @require_POST / inconsistent patient scoping
- **Location:** `strength_app/v1_onboarding_views.py:767-816`
- **What:** This AJAX endpoint has no _require_patient() gate at the top. It parses test_index/score/side/variant/measured_value from the request body and writes them into request.session['test_results'] unconditionally (lines 788-807). Only the optional DB persistence at lines 810-816 calls _require_patient, and that call is wrapped in a bare try/except that swallows all errors. So an unauthenticated visitor can populate onboarding test-result session state without ever having a patient_id, and the DB write silently no-ops for them.
- **How it could be abused:** An unauthenticated client can seed arbitrary 1-5 strength scores and raw values into their own session before/without registering, which later feed StrengthProfile creation in onboarding_asymmetry. Impact is limited to the attacker's own session (no cross-patient access), so this is data-integrity/self-inflation only, not an IDOR. The bare except also masks DB save failures.
- **Recommended fix (not applied):** Add patient, err = _require_patient(request) at the top and return 401 when err, mirroring v1_save_exercise_result. Decorate with @require_POST instead of the manual 405 check, and avoid swallowing the persistence exception silently (log it).

#### B-4 · 🔵 Low — therapist_session_start can attempt to create SessionLog with link=None (non-nullable FK) for a therapist_managed patient with no active link
- **Location:** `strength_app/v1_therapist_session_views.py:177-183`
- **What:** _require_patient permits any patient whose therapist_managed flag is True (line 51). _active_link (lines 56-66) returns None when patient.user_id is None or no active TherapistPatientLink exists. _latest_published_prescription(None) returns None, so the rx-None guard at line 179 normally redirects away. However if a published Prescription somehow exists while the active link has been deactivated/removed between page render and POST, link could be None while rx is non-None, and SessionLog.objects.create(link=link, ...) (line 183) would hit a non-nullable FK (models.py:251, no null=True). This is a robustness/data-integrity edge, not a cross-patient exposure.
- **How it could be abused:** A therapist_managed patient whose link was just deactivated could trigger an unhandled IntegrityError (500) on Start, a denial-of-service / error-disclosure nuisance rather than data leakage. No other patient's data is reachable.
- **Recommended fix (not applied):** Add an explicit guard: if link is None, flash an error and redirect to therapist_session_today before creating the SessionLog; or make the rx lookup also require a live link.
- **Confidence:** NEEDS VERIFICATION

#### B-5 · 🔵 Low — Activation flow does not force a password change on first patient login
- **Location:** `therapist_app/views.py:587-655 (simulate_accept_invite)`
- **What:** simulate_accept_invite creates/updates the PatientProfile (lines 619-641) with the therapist-generated activation password but never sets must_change_password=True, unlike reset_patient_password (line 986) which does. The PWA login enforces must_change_password (strength_app/views.py:67), so a patient who never resets keeps using a password the therapist generated and saw in plaintext.
- **How it could be abused:** The therapist (and anyone who saw the activation flash) retains knowledge of a working patient password indefinitely, since the patient is never compelled to rotate it. This undermines patient-account confidentiality of clinical/PII data under DPDPA.
- **Recommended fix (not applied):** Set must_change_password=True in the PatientProfile defaults and the update() branch in simulate_accept_invite, mirroring reset_patient_password, so the patient is forced to set a private password on first sign-in.

#### B-6 · ⚪ Info — change_password cannot invalidate other live sessions after a password change
- **Location:** `strength_app/views.py:1868-1872`
- **What:** After a successful password change, the view calls request.session.cycle_key() which only rotates the current session's key. Because patient auth is custom session-based with no server-side token/version registry, any other concurrently authenticated sessions for the same patient remain valid. The code comment at views.py:1868-1870 acknowledges this limitation.
- **How it could be abused:** If an attacker already holds a stolen/active patient session, a victim changing their password will not evict the attacker's existing session; the attacker retains access until that session naturally expires.
- **Recommended fix (not applied):** Add a session-invalidation mechanism, e.g., store a password/session version on PatientProfile, embed it in the session, and reject sessions whose stored version no longer matches after a password change or delete.

### C. CSRF

#### C-1 · 🟡 Medium — v1_edit_profile mutates patient PII via POST with no explicit method/CSRF decorator (relies solely on global middleware)
- **Location:** `strength_app/v1_progress_views.py:373-417; strength_app/urls.py:79`
- **What:** v1_edit_profile accepts POST and writes name, email, weight_kg and equipment to the current patient's PatientProfile. The view has no @require_POST and no view-level CSRF decorator; it depends entirely on the global CsrfViewMiddleware. Because patient auth is a custom session (not Django auth), if any code path or future change disables CSRF for this app's session, this write would be unprotected. The write is correctly scoped to the session-bound patient (patient.save), so it is not an IDOR.
- **How it could be abused:** If CSRF protection were bypassed or disabled for the custom patient session, an attacker could craft a cross-site form POST that silently changes a logged-in patient's name/email/weight/equipment, including overwriting the contact email surfaced to clinicians.
- **Recommended fix (not applied):** Add @require_http_methods(["GET","POST"]) and confirm CsrfViewMiddleware applies to the patient session flow (the login/session response must set a CSRF token). Consider an explicit @csrf_protect to make the requirement local and intentional.

#### C-2 · 🔵 Low — Logout is reachable via GET (no @require_POST), enabling CSRF logout
- **Location:** `strength_app/views.py:1421-1425`
- **What:** patient_logout flushes the session on any request method including GET; the URL is a plain GET route (urls.py:112) with no @require_POST guard. A third-party page can force-load /logout/ (e.g., via an <img>/redirect) and terminate the victim's session.
- **How it could be abused:** An attacker can embed a reference to /logout/ on any page the patient visits; loading it silently logs the patient out. Impact is limited to denial-of-session (annoyance), not data disclosure.
- **Recommended fix (not applied):** Decorate patient_logout with @require_POST and trigger logout from a CSRF-protected POST form/button, or verify a CSRF token before flushing.

#### C-3 · 🔵 Low — Logout served over GET (not POST-only), CSRF-able
- **Location:** `therapist_app/views.py:79-81 (therapist_logout), urls.py:8`
- **What:** therapist_logout has no @require_POST and is wired to a plain path, so it responds to GET. Django logout() clears the session unconditionally.
- **How it could be abused:** A third-party page could embed <img src=/therapist/logout/> to forcibly log a therapist out (CSRF logout / denial-of-session). Nuisance-level only; no data exposure.
- **Recommended fix (not applied):** Decorate with @require_POST and submit logout via a form carrying the CSRF token; or accept the minor risk as logout is non-destructive.

#### C-4 · ⚪ Info — coach_logout accepts GET and is not @require_POST
- **Location:** `strength_app/v1_coach_views.py:191-193 (coach_logout)`
- **What:** coach_logout calls django.contrib.auth.logout on any request method including GET (no @require_POST, no CSRF-protected POST). This is a logout-CSRF: a third-party page could force-log-out a coach via an <img>/GET. Impact is limited to denial of the coach session; no data is mutated or exposed.
- **How it could be abused:** An attacker page could embed a request to /coach/logout/ to terminate a coach's session unexpectedly (nuisance DoS of the session). No clinical data is affected.
- **Recommended fix (not applied):** Decorate coach_logout with @require_POST and submit logout via a CSRF-protected form/button, matching Django logout-CSRF guidance.

#### C-5 · ⚪ Info — State-changing POST endpoints rely entirely on global CsrfViewMiddleware (no view-level reinforcement)
- **Location:** `strength_app/v1_football_views.py:128-134 (football_save_test_result), :445-455 (match_delete); strength_app/v1_nutrition_views.py:209-211 (v1_quick_log_api)`
- **What:** These POST handlers (one deletes a MatchDate, one logs food, one writes assessment results to session) carry no @csrf_exempt and therefore inherit the project's global django.middleware.csrf.CsrfViewMiddleware (settings.py:49). No defect is present — protection is active. Noting it explicitly because these are JS-fetch endpoints whose CSRF safety depends solely on that middleware plus the client sending the token; there is no second-layer guard.
- **How it could be abused:** If CsrfViewMiddleware were ever removed/exempted, or a fetch path omitted the X-CSRFToken header while the cookie remained Lax-SameSite, an attacker could forge a cross-site POST to delete matches or create food-log rows for the victim. Not currently exploitable with the middleware in place.
- **Recommended fix (not applied):** No change required. If desired, keep CSRF middleware global and verify the JS fetch helpers attach the CSRF token to all three POST endpoints; do not add @csrf_exempt anywhere.

#### C-6 · ⚪ Info — Fetch POST sends no X-CSRFToken and base_gamified.html has no global fetch patch
- **Location:** `strength_app/templates/strength_app/stretch_execute.html:504-514; exercise_execute.html:727-733`
- **What:** stretch_execute.html (POST /save-stretch-result/) and exercise_execute.html (POST /save-exercise-results/) issue fetch() POSTs that set only Content-Type and no X-CSRFToken, define no local getCsrf helper, and extend base_gamified.html which (unlike base.html:541-558) contains no window.fetch CSRF-injection patch. The server views save_stretch_result (views.py:1705) and save_exercise_results (views.py:953) are NOT @csrf_exempt, so with the global CSRF middleware enabled these POSTs should be rejected (403) rather than silently bypassing CSRF. This is therefore a reliability/functional gap rather than a CSRF weakness, but it should be confirmed that no project-level exemption or alternate CSRF transport (e.g. a hidden token elsewhere) is in play. Note other execute templates (v1_exercise_execute, football_assessment_execute, gate_test_execute, onboarding_strength_test_execute) DO set X-CSRFToken explicitly.
- **How it could be abused:** No CSRF abuse if the middleware enforces the token (request simply fails). If a future change adds @csrf_exempt to these endpoints, the absence of any token would make them CSRF-able state-changing POSTs.
- **Recommended fix (not applied):** Add X-CSRFToken to these two fetch calls (reuse a getCsrf cookie reader) or add the same global window.fetch CSRF-injection patch to base_gamified.html so all descendant AJAX is covered consistently. Verify via the view layer that neither endpoint is csrf_exempt.
- **Confidence:** NEEDS VERIFICATION

### D. Injection / XSS

#### D-1 · 🟡 Medium — Stored XSS via rx_items_json: json.dumps + |safe inside <script> without '<' escaping
- **Location:** `therapist_app/templates/therapist_app/patient_detail.html:709 (sink); therapist_app/views.py:737-752 (json.dumps), 922-934 (tainted write)`
- **What:** The Program Builder script block emits `const initial = {{ rx_items_json|safe }};` directly inside an inline <script>. rx_items_json is built in the view with plain `json.dumps([... 'exercise_name': i.exercise_name, 'load': i.load, 'tempo': i.tempo, 'notes': i.notes ...])`. Those PrescriptionItem fields are written verbatim from therapist-controlled POST JSON in save_program (exercise_name=item.get('exercise_name'), notes=str(item.get('notes') or ''), load=str(item.get('load') or 'BW'), tempo=str(item.get('tempo') or '')) with no HTML/'<' sanitisation. Python's json.dumps does NOT escape '<', '>' or '/', so a value such as </script><script>... stored in notes/exercise_name breaks out of the script element when re-rendered with |safe and executes. This is the exact bug the codebase already guards against elsewhere (vyayam_filters.py:60 does json.dumps(...).replace('<','<')); that escaping is absent here.
- **How it could be abused:** A therapist (or any future actor who can write a patient's prescription items) can plant a script-breakout payload in an exercise note/name; it executes in the therapist console session that next opens that patient_detail page, running in the authenticated clinician context over patient clinical/PII data. Reach is currently limited to the same therapist's own patients (largely self-XSS), so impact is bounded unless prescription items can be seeded from another actor.
- **Recommended fix (not applied):** Ship the JSON via {% json_script %} (e.g. {{ rx_items|json_script:"rx-items" }} then JSON.parse) instead of |safe, or apply the same `.replace('<','<').replace('>','>').replace('&','&')` escaping used in vyayam_filters.cv_config_json before mark_safe. Additionally enforce CSP (currently report-only) so inline-script breakout is blocked at runtime.

#### D-2 · 🔵 Low — Email field accepted with only an '@' substring check, then stored and rendered
- **Location:** `strength_app/v1_progress_views.py:387,396-397,399-400`
- **What:** The email is validated only by `email and '@' not in email`. Any string containing '@' (including markup, up to 254 chars) is stored on patient.email. The model field is EmailField (models.py:27) but this manual POST path bypasses model-field validation since there are no ModelForms. Output safety then depends entirely on template auto-escaping.
- **How it could be abused:** A patient could store a malformed or markup-bearing email. If any therapist/coach console template renders patient.email with autoescape disabled or |safe, this becomes a stored-XSS sink reaching a clinician. Email is not used for login (login is by patient_id), so account-takeover impact is low.
- **Recommended fix (not applied):** Validate with django.core.validators.validate_email / EmailValidator and reject invalid input instead of the '@' substring heuristic; confirm every surface rendering patient.email relies on Django auto-escaping.
- **Confidence:** NEEDS VERIFICATION

### E. Sensitive Data / Config

#### E-1 · 🟠 High — Live patient PII and clinical data committed as SQLite DB at rest in repo root with no .gitignore
- **Location:** `db.sqlite3 (repo root, 651264 bytes / ~636KB); referenced settings.py:88-91`
- **What:** A 636KB db.sqlite3 sits in the project root. Inspecting its raw contents confirms it holds live, identifiable data: real person names (e.g. 'Meera Shah', 'Karan Iyer'), email addresses (meera.shah@andhericlinic.com, karan.iyer@kmcsports.in, sara@example.com), phone-derived login identities (phone_9876543210@vyayam.local, phone_9900000001@vyayam.local), PBKDF2-SHA256 password hashes, and clinical tables (sessionfeedback with pain_location/pain_severity/hormonal_phase, strengthprofile assessments, therapistprescription, progressreport, footballprofile). Under DPDPA 2023 this is sensitive personal/health data. There is NO .gitignore and git is not initialized, so the moment `git init && git add .` is run this DB (and any future .env) is captured into version control history.
- **How it could be abused:** Anyone who obtains a copy of the repo (a pushed git remote, a backup, a shared zip, or a leaked laptop) gains the full patient roster, contact details, and clinical records without authenticating to the app at all. Because there is no .gitignore, a routine `git add .` permanently embeds this PII into commit history where it survives later deletion.
- **Recommended fix (not applied):** Remove db.sqlite3 from the repo and never commit it; add a .gitignore covering db.sqlite3, *.sqlite3, .env, .env.*, *.DS_Store, /media, /staticfiles, venv/, __pycache__/ BEFORE initializing git. Use Postgres (DATABASE_URL) in any shared/prod environment, encrypt backups at rest, and treat the existing file as a potential breach (rotate any credentials whose hashes it contains).

#### E-2 · 🟡 Medium — Patient clinical PDF reports stored under MEDIA_ROOT and served via unauthenticated /media/ URL (no Django access control)
- **Location:** `therapist_app/models.py:337; therapist_app/views.py:1018-1022; therapist_app/templates/therapist_app/patient_detail.html:542; vyayam_project/urls.py:18-19`
- **What:** Generated progress reports contain patient PII and clinical data (name, age, condition, affected side, weekly pain scores, exercise compliance, therapist notes). They are persisted as a Django FileField (ProgressReport.pdf, upload_to='therapist_reports/') under MEDIA_ROOT and surfaced to the browser as a raw link href='{{ r.pdf.url }}' resolving to /media/therapist_reports/week-<date>-<link_id>.pdf. There is NO Django view that auth-gates or ownership-scopes the file download; the file is fetched directly from the media path. In vyayam_project/urls.py the Django static() media handler is wired only under DEBUG, so in production the actual serving of /media/ is delegated entirely to the deployment web server (nginx/WhiteNoise/etc.) with no @therapist_required check and no get_linked_patient_or_404 firewall. The filename embeds a UUID link_id which provides obscurity but is not an access-control boundary.
- **How it could be abused:** Anyone who obtains or guesses a media URL (e.g. via referer leakage, browser history, shared link, proxy/CDN cache, directory listing if the web server allows it, or because the URL embeds a UUID that may appear in logs) can retrieve another patient's clinical report without authenticating as the owning therapist. Because serving bypasses Django auth, even an unauthenticated party with the path can download DPDPA-regulated clinical PII.
- **Recommended fix (not applied):** Serve these PDFs through an authenticated Django view decorated with @therapist_required that calls get_linked_patient_or_404(therapist, link_id) and streams the file (e.g. FileResponse or an X-Accel-Redirect/X-Sendfile internal-redirect to a protected location) only after the ownership check passes. Do not expose report.pdf.url directly. Ensure the production web server denies direct access to /media/therapist_reports/ and confirm MEDIA is never publicly listable.
- **Confidence:** NEEDS VERIFICATION

#### E-3 · 🟡 Medium — No SECURE_PROXY_SSL_HEADER set behind Render reverse proxy — HSTS, SSL-redirect and Secure cookies may not engage
- **Location:** `vyayam_project/settings.py:155-161 (HSTS/secure-cookie/redirect block); no SECURE_PROXY_SSL_HEADER anywhere in vyayam_project/ or app code`
- **What:** The prod block sets SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE, SECURE_HSTS_SECONDS=31536000 (1yr) with INCLUDE_SUBDOMAINS and PRELOAD, but no SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO','https') is configured. On a TLS-terminating reverse proxy like Render, gunicorn sees the request as HTTP, so request.is_secure() returns False. That can suppress HSTS header emission, defeat SECURE_SSL_REDIRECT if it were enabled, and (depending on proxy) undermine Secure-cookie enforcement. Compounded by SECURE_SSL_REDIRECT defaulting False (settings.py:158) — `manage.py check --deploy` flags security.W008.
- **How it could be abused:** If HSTS is not actually emitted to browsers and HTTP is reachable, a network attacker on the path can attempt SSL-stripping / downgrade, exposing session cookies and patient data in transit on first or fallback connections.
- **Recommended fix (not applied):** Add SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') (Render sets this header reliably) and set DJANGO_SSL_REDIRECT=true in prod so SECURE_SSL_REDIRECT is True. Re-run `manage.py check --deploy` to confirm W008 clears, and verify the Strict-Transport-Security header appears on a live HTTPS response.
- **Confidence:** NEEDS VERIFICATION

#### E-4 · 🔵 Low — Plaintext patient passwords delivered via Django flash messages
- **Location:** `therapist_app/views.py:645-654 (simulate_accept_invite), 989-993 (reset_patient_password)`
- **What:** Both simulate_accept_invite (generated_password, line 604/648-650) and reset_patient_password (temp, line 982/991) place the patient's cleartext password into a django.contrib.messages flash, which is rendered into the HTML response and (with the default FallbackStorage over DB-backed sessions, settings.py:127) may transit through the session/cookie store before display. The credential lands in the therapist's browser page, browser history/back-button cache, and any intermediary that logs response bodies.
- **How it could be abused:** An attacker with access to the therapist's browser cache/history, a shoulder-surfer, or anyone who can read proxy/CDN logs of the rendered page can recover a patient's app password. Because the same page is reachable via the browser Back button, the credential persists client-side after the therapist navigates away.
- **Recommended fix (not applied):** Avoid rendering cleartext credentials in HTML. Prefer an out-of-band delivery (SMS/email to the patient directly, or a one-time tokenized set-password link). If on-screen display is unavoidable for the dev/demo flow, render it from a one-time server token consumed on first view, set Cache-Control: no-store on that response, and never route it through the messages framework.

#### E-5 · 🔵 Low — Generated patient temp passwords surfaced in cleartext via flash message / template context
- **Location:** `therapist_app/views.py:982-993 (temp-password reset) and v1_coach_views.py:672-677 (coach onboarding credentials)`
- **What:** When a therapist issues a temporary password (therapist_app/views.py:982 generates `temp` and surfaces it at line 991 in a flash message) and when a coach onboards an athlete (v1_coach_views.py:611 generates temp_pw, returned in the `credentials` dict at 672-677 and rendered in coach_add_athlete.html), the cleartext password is shown in the response HTML. The stored copy is correctly hashed with make_password, but the plaintext transits in the rendered page and any logging/caching layer that captures response bodies or Django messages.
- **How it could be abused:** A shoulder-surfer, a shared/kiosk therapist workstation, browser history, or any intermediate proxy/log capturing the response could expose a patient's initial credential. must_change_password mitigates persistence, but the window between issue and first login is exploitable.
- **Recommended fix (not applied):** Display the temp password only once on a dedicated minimal screen (no flash persistence), avoid embedding it in messages that may be re-rendered, and prefer an out-of-band delivery (SMS/email reset link, which already exists via PasswordResetToken) over showing the secret in the console UI.
- **Confidence:** NEEDS VERIFICATION

#### E-6 · 🔵 Low — macOS .DS_Store files throughout tree and stale 'Change SECRET_KEY in settings.py' README guidance — repo hygiene
- **Location:** `Repo root and subdirs: .DS_Store at repo root, strength_app/, therapist_app/, staticfiles/, templates/, static/, exercise_system/, management/ (10+ files); README.md:346`
- **What:** Numerous .DS_Store metadata files exist across the tree (repo root, both apps, staticfiles, templates). With no .gitignore these would be committed, leaking directory listings/filenames. Separately, README.md:346 instructs 'Change SECRET_KEY in settings.py', which is stale/misleading guidance: settings.py:14 correctly reads SECRET_KEY from os.environ['DJANGO_SECRET_KEY'] with no in-file key. No actual hardcoded secret is present in README; this is a documentation hygiene issue that could lead an operator to reintroduce an in-file key.
- **How it could be abused:** .DS_Store files can disclose internal file/directory names if served or committed. The stale README step could mislead a deployer into hardcoding a SECRET_KEY back into settings.py, reintroducing a committed-secret risk.
- **Recommended fix (not applied):** Add .DS_Store to .gitignore and remove existing ones; correct README.md:346 to direct operators to set the DJANGO_SECRET_KEY environment variable instead of editing settings.py.

#### E-7 · ⚪ Info — No hardcoded production secrets found in code/scripts/docs (clean) — only dev test/seed passwords
- **Location:** `vyayam_project/settings.py:14 (SECRET_KEY), :16 (DEBUG), :77-92 (DATABASE_URL); build.sh:1-5; setup.sh; runtime.txt; docs/; README.md; therapist_app/management/commands/seed_therapist_demo.py:58,67,79..`
- **What:** A full grep across *.py/*.sh/*.txt/*.md/docs for secret_key/password/api_key/token/connection-strings found NO production secrets. SECRET_KEY is os.environ['DJANGO_SECRET_KEY'] with no fallback (settings.py:14; AUDIT_FIXES_CHANGELOG.md:15 confirms the old hardcoded fallback was removed). No committed DATABASE_URL/Neon/Postgres connection string, no SMTP creds (all from env: settings.py:188-198). The only literal passwords are in test files (therapist_app/test_*.py, tests.py) and the dev seed command seed_therapist_demo.py ('simple'/'patient'), which are hashed via make_password/set_password and intended for local seeding only. PatientProfile.password (models.py:28) is consistently hashed (make_password/check_password across views.py:58,190,1812,1865, v1_onboarding_views.py:521,555, v1_coach_views.py:618).
- **How it could be abused:** No direct abuse from code secrets; included to document that the secrets-in-code task came back clean. The dev seed passwords ('simple'/'patient') would be dangerous only if seed_therapist_demo is ever run against a production database.
- **Recommended fix (not applied):** Keep SECRET_KEY and all credentials in environment variables (already done). Ensure seed_therapist_demo is never executed against production data; gate it to DEBUG or a non-prod guard if not already.

#### E-8 · ⚪ Info — Logging and DEBUG do not leak raw PII; DEBUG defaults False so tracebacks are not exposed
- **Location:** `vyayam_project/settings.py:16,166-185 (LOGGING); strength_app/views.py:160-161; therapist_app/views.py:609-613; strength_app/backend/form_tracking.py:256+; strength_app/backend/database_schema.py:463,485`
- **What:** DEBUG defaults to False (settings.py:16) so production returns Django's generic 500 (handler500 = django.views.defaults.server_error, urls.py:29) with no traceback. Logging is console-only at WARNING (settings.py:166-185). Audited log statements use the opaque patient_id (the PK, not phone/email) e.g. views.py:160-161, and exc_info for stack traces. therapist_app/views.py:613 logs only a SYNTHETIC fallback phone (f'9{link.patient.id:09d}') inside a dev-only accept function, not a real patient phone. print() PII appears only in non-request CLI/demo blocks: form_tracking.py (form scores, no identity) and database_schema.py:485 under `if __name__ == '__main__'` (line 463). No phone numbers or names appear in URL path patterns; coach uses opaque <str:patient_id> (urls.py:94-98), therapist uses UUID link_id.
- **How it could be abused:** No material PII-in-logs/URLs/errors exposure identified. Residual: at-WARNING level a synthetic phone is logged (not real PII); if log level were lowered to DEBUG in future, review for over-logging.
- **Recommended fix (not applied):** Maintain DEBUG=False in prod (already the default) and keep PII out of log messages. Optionally avoid logging even synthetic phone numbers. Confirm no operator overrides DJANGO_DEBUG=true in production.

### F. Security Headers

#### F-1 · 🟡 Medium — CSP is Report-Only and allows 'unsafe-inline' in script-src and style-src — provides no real XSS mitigation
- **Location:** `strength_app/middleware.py:15-24,33 (Content-Security-Policy-Report-Only with 'unsafe-inline')`
- **What:** PermissionsPolicyMiddleware emits Content-Security-Policy-Report-Only (line 33), not an enforcing Content-Security-Policy. The policy's script-src includes 'unsafe-inline' (line 17) and style-src includes 'unsafe-inline' (line 18), plus CDN hosts. A Report-Only header never blocks anything in the browser, and even if flipped to enforcing, 'unsafe-inline' on script-src negates CSP's core XSS protection. The middleware docstring acknowledges this is interim pending nonce migration.
- **How it could be abused:** If any reflected/stored XSS sink exists (e.g. an unescaped user field), the browser will not block injected inline script: Report-Only mode only reports, and 'unsafe-inline' would permit the payload even under an enforcing policy. CSP therefore does not function as a defense-in-depth backstop today.
- **Recommended fix (not applied):** Move inline scripts to static files, introduce per-response nonces (or hashes), remove 'unsafe-inline' from script-src, then switch the header name from Content-Security-Policy-Report-Only to Content-Security-Policy. Keep a separate report-uri/report-to for telemetry.

#### F-2 · 🔵 Low — Executable Tailwind CDN <script> loaded without Subresource Integrity (and unpinned)
- **Location:** `strength_app/templates/strength_app/base_gamified.html:12; base.html:19; coach_base.html:32; therapist_session_base.html:7`
- **What:** The Tailwind runtime is loaded as an executable third-party script from https://cdn.tailwindcss.com (e.g. base_gamified.html:12 `?plugins=forms,container-queries`, base.html:19, coach_base.html:32, therapist_session_base.html:7) with no integrity= attribute. It is also unversioned, so it is a moving target that cannot be SRI-pinned in its current form.
- **How it could be abused:** A compromise of the CDN or a TLS-stripping MITM could serve attacker-controlled JavaScript that runs with full DOM access on authenticated patient, coach, and therapist pages, enabling session/PII theft and clinical-data tampering. The Tailwind play-CDN is intended for prototyping, not production.
- **Recommended fix (not applied):** Replace the play-CDN with a build-time compiled, version-pinned Tailwind stylesheet served from the app's own origin (no remote execution), or at minimum pin a versioned CDN asset and add integrity= + crossorigin=anonymous.

#### F-3 · 🔵 Low — Third-party CDN scripts/styles loaded without Subresource Integrity (chart.js, MediaPipe, Font Awesome)
- **Location:** `strength_app/templates/strength_app/v1_dashboard.html:253; onboarding_complete.html:145; therapist_app/templates/therapist_app/base_therapist.html:91; v1_exercise_execute.html:432-434; stretch_execute.html:365-368; exercise_execute.html:365-368; gate_test_execute.html:316-318; onboarding_strength_test_execute.html:192-194; football_nordic_camera_test.html:37-39; coach_base.html:33; base_therapist.html:11; coach_login.html:7`
- **What:** Numerous executable script and stylesheet tags are loaded from CDNs without integrity= attributes: chart.js (cdn.jsdelivr.net/npm/chart.js at v1_dashboard.html:253, onboarding_complete.html:145, base_therapist.html:91), MediaPipe pose/camera/drawing/control utils (multiple *_execute.html and football_nordic_camera_test.html), and Font Awesome CSS from cdnjs.cloudflare.com (coach_base.html:33, base_therapist.html:11, coach_login.html:7). Across templates roughly 42 external CDN resource tags lack SRI; only the two Bootstrap tags in base.html (lines 16, 515) carry integrity=.
- **How it could be abused:** If any of these CDNs is compromised or the connection is MITM'd, attacker-controlled code/CSS is delivered to authenticated patient, coach, and therapist pages. The chart.js and MediaPipe entries are executable JavaScript, giving full script execution in the user's authenticated session.
- **Recommended fix (not applied):** Add integrity= (SRI hash) plus crossorigin=anonymous to each version-pinned CDN asset, or self-host the libraries from the app origin. Pin exact versions (chart.js and the @mediapipe packages are currently unversioned, which prevents SRI).

### G. File Upload / Media

_No user-facing file-upload feature exists in the app (no `FileField`/`ImageField`/`request.FILES` patient input path). The only `FileField` is `ProgressReport.pdf`, written server-side by the PDF generator — its **serving** is covered under finding E-3._

### H. Business Logic / Privilege Escalation

#### H-1 · 🟡 Medium — Athlete-tier self-promotion: athlete_tier_active set True without re-checking athlete_tier_eligible
- **Location:** `strength_app/v1_football_views.py:301-302 (set) reached via football_assessment:67, football_assessment_execute:88, football_save_test_result:129, football_assessment_results:227; gate exists only at football_sport_select:40`
- **What:** athlete_tier_eligible is a server-derived clinical gate (set in v1_onboarding_views.py:1438 only when >=4 of 7 strength patterns score 5, or by a coach at v1_coach_views.py:632). The football assessment flow that flips the patient INTO the athlete training track only verifies authentication via _get_patient(); it never checks athlete_tier_eligible. Only football_sport_select (line 40) enforces the eligibility gate. football_assessment_results unconditionally executes patient.athlete_tier_active = True; patient.save(update_fields=['athlete_tier_active']). athlete_tier_active is the switch the prescription engine reads (v1_prescription_engine.py:469, 1488) to route a patient into FIFA 11+ warmups and the football plyometric/sprint/HSR program.
- **How it could be abused:** An authenticated but non-eligible (e.g. deconditioned or rehab) patient who navigates directly to /v1/football/assessment/ instead of through the gated sport-select page can complete the assessment and have the app flip them into the higher-intensity athlete training track they were never cleared for. The hardest dangerous loads (plyometrics/sprint) remain independently gated by FootballProfile.check_plyometric_gate() on actual LSI/hop/Nordic scores (v1_models check_plyometric_gate), which limits the worst-case, but the athlete program selection itself is escalated.
- **Recommended fix (not applied):** Add the same athlete_tier_eligible guard used in football_sport_select (redirect to v1_session_overview if not patient.athlete_tier_eligible) to football_assessment, football_assessment_execute, football_save_test_result, and football_assessment_results so the entire flow is gated, not just the entry page.

#### H-2 · 🔵 Low — Self-reported workout/gate metrics written to DB with no server-side validation (client-trusted clinical data)
- **Location:** `strength_app/views.py:996-1055 (workout_complete) and 459-595 (save_gate_test_result)`
- **What:** workout_complete persists green/yellow/red rep totals, form scores, comfort and difficulty directly from session data that originated from client POSTs in save_exercise_results, with no bounds checking. save_gate_test_result similarly takes reps_completed / difficulty_reported / pain_during from the JSON body and feeds them into the prescription/capability engine; only difficulty and pain are clamped (lines 587-588), reps_completed is not. Because these drive the auto-progression engine (_update_capability_after_session) and the clinical ProgressReport, a patient can manipulate their own clinical trajectory. This is self-scoped (no cross-patient access), so it is a data-integrity / business-logic issue, not IDOR.
- **How it could be abused:** A patient could submit fabricated rep counts and comfort ratings to make the system auto-advance their capability level or generate a flattering progress report shown to their therapist, undermining clinical decisions. Cannot affect another patient's records.
- **Recommended fix (not applied):** Validate and clamp all numeric inputs server-side (reps within prescribed bounds, form_score 0-100) and treat client-reported form/rep data as untrusted; ideally derive authoritative rep counts from a server-side source rather than the browser.

#### H-3 · 🔵 Low — biological_sex accepted from POST without choices validation (manual mass-assignment)
- **Location:** `strength_app/v1_onboarding_views.py:433, 516, 547`
- **What:** biological_sex is read straight from request.POST.get('biological_sex', 'not_specified') and assigned to patient.biological_sex on both the update path (line 516) and the create path (line 547). There are no ModelForms, and Django model choices are NOT enforced on save(), so any arbitrary string is persisted. biological_sex drives step count (_total_steps), the female-only hormonal screen, female physique goal visibility, and sex-adjusted scoring thresholds.
- **How it could be abused:** A user (or an attacker who controls the registration POST) can submit a value outside BIOLOGICAL_SEX_CHOICES, producing inconsistent branching (e.g. skipping or forcing the hormonal screen, mis-applying sex-adjusted push-up cutoffs). No privilege escalation, but it can corrupt the clinical assessment branch logic and downstream nutrition/macro math.
- **Recommended fix (not applied):** Validate biological_sex against PatientProfile.BIOLOGICAL_SEX_CHOICES before assignment and fall back to 'not_specified' on any other value.

#### H-4 · 🔵 Low — Coach sets shared PatientProfile.competition_date — value also drives clinical periodisation/taper logic
- **Location:** `strength_app/v1_coach_views.py:551-564 (coach_set_competition)`
- **What:** coach_set_competition writes to PatientProfile.competition_date (line 559-563), a field on the shared patient record (not on the coach link). competition_date feeds the prescription engine's taper/periodisation. A coach is authorized for THEIR linked athletes (ownership is checked), so this is in-scope by design, but the value lives on the patient profile rather than being coach-scoped. If an athlete can be linked to more than one professional, the last writer wins. Date input is parsed via date.fromisoformat with a try/except (line 559-561), so malformed input does not 500. No mass-assignment of other fields here.
- **How it could be abused:** A linked coach can set a competition_date that alters the athlete's training periodisation/taper. Within authorization scope, but because the field is on the shared profile there is no audit of which professional set it, and a coach link does not require the athlete to actually be the coach's competitor.
- **Recommended fix (not applied):** Acceptable as-is given ownership is enforced; optionally store competition/match dates as MatchDate rows (already used elsewhere, lines 663-668) keyed to the coach link rather than overwriting the shared PatientProfile.competition_date, and audit-log the mutation.

#### H-5 · 🔵 Low — Self-service athlete-tier activation flips own athlete_tier_active without re-checking athlete_tier_eligible at results time
- **Location:** `strength_app/v1_football_views.py:301 (and gate read at :40); set vs gate authority in strength_app/v1_onboarding_views.py:1438`
- **What:** football_assessment_results unconditionally sets patient.athlete_tier_active = True (l.301) once a session has football_test_results, without re-verifying patient.athlete_tier_eligible. The eligibility gate is only enforced in football_sport_select (l.40); a patient who reaches the assessment flow another way (e.g. by directly POSTing football_assessment then walking save-test-result, then loading /football/results/) can self-activate athlete tier. The flag only changes the patient's OWN prescription-engine output (v1_prescription_engine.py:469,1488) — it does not cross a tenant or role boundary or expose other users' data.
- **How it could be abused:** A non-eligible patient could unlock the football/athlete training programming intended to be gated behind the strength-test eligibility threshold, by completing the assessment flow even though athlete_tier_eligible was never set true. Impact is confined to the abuser's own training plan; no other patient's data or privileges are affected.
- **Recommended fix (not applied):** In football_assessment_results, gate the athlete_tier_active assignment behind a re-check of patient.athlete_tier_eligible (mirror the l.40 check from football_sport_select), or refuse to compute/save FootballProfile when the patient is not eligible.
- **Confidence:** NEEDS VERIFICATION

#### H-6 · 🔵 Low — State-mutating actions (feedback, complete, profile message) are served on GET-or-POST handlers without @require_POST
- **Location:** `strength_app/v1_therapist_session_views.py:302,362,552`
- **What:** therapist_session_feedback (line 302), therapist_session_complete (line 362) and therapist_session_profile (line 552) perform writes (SessionLogItem.save, SessionLog.save, TherapistMessage.create) only inside an if request.method == 'POST' branch but are not decorated @require_POST, unlike therapist_session_start (line 171). The write itself is correctly gated on POST, so this is a hardening gap rather than a GET-side-effect bug. CSRF protection still applies (no csrf_exempt anywhere in the file; Django CSRF middleware enforced per settings), so cross-site forgery is mitigated. The risk is reduced consistency/clarity and reliance on the method check rather than an explicit decorator.
- **How it could be abused:** Low: a malformed or replayed POST is the only write path; CSRF token is still required so an attacker cannot silently submit feedback/messages on a victim's behalf. Mainly a defense-in-depth and POST-only-violation hygiene issue.
- **Recommended fix (not applied):** Add @require_POST to the POST-only logic or split the POST branch into a dedicated @require_POST view; keep CSRF enforced.

#### H-7 · ⚪ Info — delete_account performs destructive deletion without @require_POST decorator
- **Location:** `strength_app/views.py:1798-1820`
- **What:** delete_account is not decorated with @require_POST; the destructive PatientProfile.delete() only runs inside the 'if request.method == POST' branch (views.py:1805-1818) and additionally requires the correct password plus a confirmation checkbox, so CSRF token enforcement still applies via Django's CSRF middleware on the POST. The decorator absence is a defense-in-depth gap, not an exploitable bug here.
- **How it could be abused:** No practical abuse: deletion requires a valid CSRF token (POST), the account password, and an explicit confirmation checkbox, all bound to the session patient. Noted only for hardening consistency.
- **Recommended fix (not applied):** Add @require_POST to delete_account for explicitness and to prevent future refactors from accidentally exposing the destructive path on GET.

#### H-8 · ⚪ Info — Patient can self-clear their own absolute_stop clinical hard-stop (by design, gated by confirmation)
- **Location:** `strength_app/v1_onboarding_views.py:1192-1217`
- **What:** In onboarding_red_flags a patient who previously had absolute_stop=True can uncheck all absolute_stop_conditions and clear the hard-stop themselves. This is explicitly gated: clearing requires the confirm_stop_clear checkbox (lines 1176-1190), is audited via RedFlagEvent in _log_red_flag_change, and notifies linked coaches/therapists with an Alert. So the clinical-safety bypass is intentional and instrumented, not silent.
- **How it could be abused:** A patient could untruthfully clear a contraindication (e.g. recent cardiac event) to resume training, but they must explicitly confirm and the action is logged and surfaced to their clinician. Residual clinical risk is inherent to self-service screening rather than a code defect.
- **Recommended fix (not applied):** No code change required; this is working as designed. If stricter safety is desired, certain URGENT_STOP_IDS could be made non-self-clearable (require clinician action) rather than patient-confirmable.

#### H-9 · ⚪ Info — athlete_tier_eligible is server-computed, NOT mass-assignable from POST (control confirmed)
- **Location:** `strength_app/v1_onboarding_views.py:1430-1448`
- **What:** Reviewed specifically for the privilege-escalation concern: athlete_tier_eligible is set only in onboarding_complete from the patient's own StrengthProfile scores (fives_count >= 4 across the 7 patterns) and saved via an explicit update_fields whitelist. No request.POST value reaches this field, and gate_test_completed is likewise server-set. No POST-driven path sets tier/role/is_staff/is_superuser/therapist_managed in the onboarding module.
- **How it could be abused:** Not abusable via onboarding: the eligibility flag cannot be forced from client input.
- **Recommended fix (not applied):** None needed. Confirmed safe.

#### H-10 · ⚪ Info — Dev test views (v1_test_exercise, v1_test_list) have no login/role check, gated only by DEBUG
- **Location:** `strength_app/v1_session_views.py:1305-1310, 1346-1351`
- **What:** Both v1_test_exercise and v1_test_list skip _require_patient entirely and are reachable by any unauthenticated caller, gated solely by raising Http404 when settings.DEBUG is False. They render exercise template/content metadata (no patient PII, no DB rows fetched by id).
- **How it could be abused:** In production DEBUG must be False (per audited settings, DEBUG env default False), so these raise 404 and are unreachable. The risk only materialises if DEBUG is ever true in a deployed environment, exposing the exercise-execution template and content library to anonymous users. No clinical/PII data is exposed by these views.
- **Recommended fix (not applied):** Acceptable as dev-only given the DEBUG gate. For hardening, also add @login_required-equivalent session check or remove these routes from production URL conf entirely so they cannot be exposed even if DEBUG is misconfigured.

#### H-11 · ⚪ Info — Pain notification writes to coach/therapist links scoped to current patient (no cross-tenant write) — confirmed safe, noted for completeness
- **Location:** `strength_app/v1_session_views.py:164-196`
- **What:** _notify_linked_professionals_of_pain, invoked from v1_save_exercise_result, appends a note and creates an Alert on CoachPatientLink and TherapistPatientLink rows. All link queries are filtered by the current patient (CoachPatientLink.objects.filter(patient=patient,...) line 175; TherapistPatientLink.objects.filter(patient=patient.user,...) line 180), so a patient can only flag their own links.
- **How it could be abused:** No cross-tenant write is possible: the patient is the authenticated session patient and the link queryset is bound to that patient. A patient cannot inject notes/alerts into another patient's professional links. Listed as Info to record that this write path was reviewed and is owner-scoped.
- **Recommended fix (not applied):** No change required. Confirmed owner-scoped.

#### H-12 · ⚪ Info — Coach role = any user with a strength_app.TherapistProfile; distinct model from therapist_app.Therapist
- **Location:** `strength_app/v1_coach_views.py:42-53 (coach_required) vs therapist_app/permissions.py:19-29 (therapist_required)`
- **What:** coach_required gates on request.user.therapistprofile (reverse accessor of strength_app.TherapistProfile, models.py:733), whereas the clinician console gates on request.user.therapist (therapist_app.Therapist, therapist_app/models.py:44). These are two separate OneToOne-to-User records. There is no separate 'Coach' model and no per-coach capability flag: any User that has a strength_app.TherapistProfile is a full coach who can onboard athletes and override prescriptions. A patient (custom session auth, no Django User by default) cannot reach these views because request.user.is_authenticated is false for a session-only patient, so the patient->coach privilege-escalation path is closed by the decorator (line 45). Worth confirming no flow grants a patient both a Django User login AND a TherapistProfile.
- **How it could be abused:** Not directly exploitable from the code read: a patient session does not carry an authenticated Django User, so coach_required redirects to coach_login. Privilege escalation would require a patient to additionally obtain a Django User with a linked TherapistProfile, which no coach view creates.
- **Recommended fix (not applied):** No change required for the IDOR threat. Document that coach authority is granted solely by presence of strength_app.TherapistProfile and ensure account-provisioning never attaches a TherapistProfile to a patient-owned User.

#### H-13 · ⚪ Info — Invite reuses an existing Django User by username (email/phone), enabling link to a foreign account
- **Location:** `therapist_app/views.py:551-559 (invite_patient)`
- **What:** invite_patient does User.objects.get_or_create(username=email or phone-key) (lines 551-556). If a User with that email/phone-derived username already exists (e.g. created by another therapist's invite or a real patient account), the new TherapistPatientLink is attached to that pre-existing User rather than a fresh one. The unique_therapist_patient constraint only prevents the SAME therapist re-linking; a different therapist can create a link to the same underlying User.
- **How it could be abused:** A therapist could invite an email/phone already belonging to a patient managed elsewhere; the two therapists would then share the same underlying User account. simulate_accept_invite would reset that shared User's password and overwrite the single PatientProfile (keyed by user_id), letting one therapist hijack/clobber another's patient credentials. Requires knowing/guessing the target email or phone.
- **Recommended fix (not applied):** Before linking, verify the matched User isn't already an active patient of a different therapist (or isn't a privileged/staff account), and treat a pre-existing User as an error requiring explicit confirmation rather than silently linking. Consider keying invites to a per-link identity instead of a shared global User.
- **Confidence:** NEEDS VERIFICATION

#### H-14 · ⚪ Info — Mutation views silently 404 on pending/archived links due to status='active' filter
- **Location:** `therapist_app/permissions.py:32-40 (get_linked_patient_or_404)`
- **What:** get_linked_patient_or_404 hardcodes status='active' (line 39). All patient-detail mutations (save_onboarding, save_program, send_message, reset_patient_password, generate_report, copy_previous_week, add_visit_note, patient_detail) therefore cannot operate on a pending or archived link. This is correct security-wise (a sound firewall) but is noted because it conflates the ownership check with a lifecycle filter; an archived patient's clinical record becomes unreachable even for legitimate read.
- **How it could be abused:** Not directly exploitable. Worth flagging only as a robustness/availability observation: a status flip to 'archived' instantly hides data without an explicit access decision, and a future view that needs pending-link access must not bypass this helper.
- **Recommended fix (not applied):** Consider splitting the firewall (therapist+link ownership) from the lifecycle gate (status) so each view chooses which statuses it permits, while keeping the therapist scoping mandatory.

### I. Dependencies / Hygiene

#### I-1 · 🔵 Low — Django 4.2.30 pinned — verify it is the latest 4.2.x LTS security patch
- **Location:** `requirements.txt:2 (Django==4.2.30)`
- **What:** requirements.txt pins Django==4.2.30 (4.2 LTS line). The audit environment has no live package index ('pip list --outdated' returned nothing, which only means the local env had no newer cached wheel, not that 4.2.30 is current). Django 4.2 LTS receives security fixes through ~April 2026; whether 4.2.30 is the newest published 4.2.x at audit time (2026-06-23) cannot be confirmed offline. SHIP_READY_REPORT.md:55 notes a prior 4.2->4.2.30 bump and a clean pip-audit, but that was at an earlier date.
- **How it could be abused:** If a newer 4.2.x security release exists, running 4.2.30 could leave a known, patched Django CVE unaddressed (e.g. SQL/ORM, file-handling, or DoS classes typical of Django advisories).
- **Recommended fix (not applied):** Check the official Django security releases / PyPI for the latest 4.2.x at deploy time and bump if a newer patch exists; run pip-audit/safety against a live index in CI. Note Django 4.2 LTS extended support ends around April 2026 — plan a move to a supported LTS (5.2) thereafter.
- **Confidence:** NEEDS VERIFICATION

#### I-2 · 🔵 Low — Dependency currency / CVE-class review needs a live index — flag reportlab and psycopg2-binary
- **Location:** `requirements.txt:5 (psycopg2-binary==2.9.11), :3 (gunicorn==25.3.0), :4 (mediapipe==0.10.33), :6 (reportlab==4.4.4), :7 (whitenoise==6.12.0), :1 (dj-database-url==3.1.2)`
- **What:** Pins are reasonable and modern. Two warrant CVE-class attention that cannot be confirmed offline: reportlab (4.4.4) has historically had RCE/code-injection advisories in its PDF/RML text evaluation when rendering untrusted input (relevant since this app generates patient PDF reports), and psycopg2-binary is the binary wheel (carries bundled libpq, so it tracks libpq CVEs and is discouraged for production vs source psycopg2/psycopg3). gunicorn 25.3.0, whitenoise 6.12.0, mediapipe 0.10.33, dj-database-url 3.1.2 appear current but were not verified against a live advisory feed.
- **How it could be abused:** If reportlab renders any attacker-influenced field into a PDF and a code-injection CVE applies to 4.4.4, it could enable code execution during report generation. An outdated psycopg2-binary could ship a vulnerable bundled libpq.
- **Recommended fix (not applied):** Run pip-audit/safety against a live advisory database in CI; confirm reportlab 4.4.4 is free of known injection CVEs and that any PDF inputs are not user-controlled in unsafe RML/eval contexts; prefer source psycopg2 or psycopg3 in production and keep it patched.
- **Confidence:** NEEDS VERIFICATION

## 4. `manage.py check --deploy` — Raw Output

Run with `DJANGO_DEBUG=False` and a throwaway `DJANGO_SECRET_KEY` (read-only; no data touched):

```
$ DJANGO_DEBUG=False python manage.py check --deploy
System check identified some issues:

WARNINGS:
?: (security.W008) Your SECURE_SSL_REDIRECT setting is not set to True. Unless your
   site should be available over both SSL and non-SSL connections, you may want to
   either set this setting True or configure a load balancer or reverse-proxy server
   to redirect all connections to HTTPS.

System check identified 1 issue (0 silenced).
```

Interpretation: the cookie/HSTS/`X-Frame-Options`/`nosniff` deploy checks all **pass** under `DEBUG=False`. The single `W008` corresponds to finding **E-2** (see also the missing `SECURE_PROXY_SSL_HEADER`). `pip list --outdated` returned no upgrades in the offline audit environment, which only means no newer wheel was cached locally — see **I-1/I-2** (dependency currency needs a live advisory index).

## 5. Controls Confirmed Present / OK (reality check)

Per the brief, controls were verified against current code rather than assumed from history. The following are confirmed **in place and effective** (representative, with file:line):

- **Object-level access control (the canonical threat):** owner-scoped fetches throughout — `view_report`/`download_report` (`get_object_or_404(ProgressReport, id=report_id, patient=patient)`, `views.py:1491,1511`), `v1_session_detail` (`WorkoutSession.objects.filter(patient=patient, pk=session_id)`, `v1_progress_views.py:330`), `match_delete` (`MatchDate.objects.filter(id=match_id, patient=patient).delete()`, `v1_football_views.py:455`), `stretch_download_pdf` (scoped by `id=session_id`+patient).
- **Therapist cross-tenant firewall:** every therapist view carries `@therapist_required` and resolves patients via `get_linked_patient_or_404(therapist, link_id)` (`permissions.py:32`); `alert_mark_reviewed` scopes by `link__therapist=request.user.therapist` (`therapist_app/views.py:363`). UUID `link_id`s are non-guessable. All mutations are `@require_POST`.
- **Coach ownership:** `coach_athlete_detail` enforces `get_object_or_404(CoachPatientLink, coach=request.therapist, patient=patient, is_active=True)` (`v1_coach_views.py:266`); `coach_squad` lists only the coach's own links.
- **Password hashing:** Django PBKDF2-SHA256 (600,000 iterations) confirmed in `db.sqlite3` contents; `check_password`/`make_password` used at all set/verify sites (`views.py:58,190,1865`). No plaintext or weak hashing.
- **Session fixation / lifecycle:** `session.flush()` on login (`views.py:60`) and logout (`views.py:1423`); `cycle_key()` on password change (`views.py:1871`).
- **Password-reset token:** 256-bit `secrets.token_urlsafe(32)` (`views.py:140`), single-use + 1-hour expiry + sibling invalidation (`models.py:1421-1425`, `views.py:193-198`).
- **Brute-force throttling:** `@rate_limit(5/300s)` on patient login, forgot-password, change-password, coach login, therapist login; `X-Forwarded-For` trusted only behind an explicit `DJANGO_TRUSTED_PROXY=1` (`rate_limiter.py:56`).
- **CSRF:** `CsrfViewMiddleware` enabled; **zero `@csrf_exempt`** in the entire codebase; `{% csrf_token %}` present in all 35 POST-form templates.
- **No SQL injection surface:** no `.raw()`/`.extra()`/`cursor.execute` string-building; ORM only. No `subprocess`/`os.system`/`eval`/`exec`/`pickle` on user input.
- **Mass-assignment:** no `ModelForm`s; the privileged `athlete_tier_eligible` flag is server-computed only (`v1_onboarding_views.py:1438`) — never set from POST (confirmed).
- **Secrets:** `SECRET_KEY=os.environ['DJANGO_SECRET_KEY']` with no fallback (`settings.py:14`); no hardcoded production secrets / DB URL / SMTP creds in code, scripts, or docs.
- **Headers:** `X-Frame-Options: DENY`, `SECURE_CONTENT_TYPE_NOSNIFF`, HSTS 1yr+subdomains+preload (prod), Secure+HttpOnly+SameSite cookies (prod), `Referrer-Policy: same-origin`, `Permissions-Policy: camera=(self)` (`settings.py`, `middleware.py`).
- **Info disclosure:** `DEBUG` defaults False (generic 500 page); logging is console-only at WARNING and uses opaque `patient_id`, not phone/email; no user enumeration on login/forgot-password.

_(The review agents recorded 165 individual 'present/OK' control confirmations across the codebase; the above is the consolidated set.)_

## 6. Appendix — Items marked NEEDS VERIFICATION

These require runtime/deployment confirmation beyond static source review:

- **[Medium] Patient clinical PDF reports stored under MEDIA_ROOT and served via unauthenticated /media/ URL (no Django access control)** (`therapist_app/models.py:337`) — Serve these PDFs through an authenticated Django view decorated with @therapist_required that calls get_linked_patient_or_404(therapist, link_id) and streams the file (e.g. FileResponse or an X-Accel-
- **[Medium] No SECURE_PROXY_SSL_HEADER set behind Render reverse proxy — HSTS, SSL-redirect and Secure cookies may not engage** (`vyayam_project/settings.py:155-161 (HSTS/secure-cookie/redirect block)`) — Add SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') (Render sets this header reliably) and set DJANGO_SSL_REDIRECT=true in prod so SECURE_SSL_REDIRECT is True. Re-run `manage.py check --
- **[Low] Email field accepted with only an '@' substring check, then stored and rendered** (`strength_app/v1_progress_views.py:387,396-397,399-400`) — Validate with django.core.validators.validate_email / EmailValidator and reject invalid input instead of the '@' substring heuristic; confirm every surface rendering patient.email relies on Django aut
- **[Low] Self-service athlete-tier activation flips own athlete_tier_active without re-checking athlete_tier_eligible at results time** (`strength_app/v1_football_views.py:301 (and gate read at :40)`) — In football_assessment_results, gate the athlete_tier_active assignment behind a re-check of patient.athlete_tier_eligible (mirror the l.40 check from football_sport_select), or refuse to compute/save
- **[Low] therapist_session_start can attempt to create SessionLog with link=None (non-nullable FK) for a therapist_managed patient with no active link** (`strength_app/v1_therapist_session_views.py:177-183`) — Add an explicit guard: if link is None, flash an error and redirect to therapist_session_today before creating the SessionLog; or make the rx lookup also require a live link.
- **[Low] Generated patient temp passwords surfaced in cleartext via flash message / template context** (`therapist_app/views.py:982-993 (temp-password reset) and v1_coach_views.py:672-677 (coach onboarding credentials)`) — Display the temp password only once on a dedicated minimal screen (no flash persistence), avoid embedding it in messages that may be re-rendered, and prefer an out-of-band delivery (SMS/email reset li
- **[Low] Django 4.2.30 pinned — verify it is the latest 4.2.x LTS security patch** (`requirements.txt:2 (Django==4.2.30)`) — Check the official Django security releases / PyPI for the latest 4.2.x at deploy time and bump if a newer patch exists; run pip-audit/safety against a live index in CI. Note Django 4.2 LTS extended s
- **[Low] Dependency currency / CVE-class review needs a live index — flag reportlab and psycopg2-binary** (`requirements.txt:5 (psycopg2-binary==2.9.11), :3 (gunicorn==25.3.0), :4 (mediapipe==0.10.33), :6 (reportlab==4.4.4), :7 (whitenoise==6.12.0), :1 (dj-database-url==3.1.2)`) — Run pip-audit/safety against a live advisory database in CI; confirm reportlab 4.4.4 is free of known injection CVEs and that any PDF inputs are not user-controlled in unsafe RML/eval contexts; prefer
- **[Info] Invite reuses an existing Django User by username (email/phone), enabling link to a foreign account** (`therapist_app/views.py:551-559 (invite_patient)`) — Before linking, verify the matched User isn't already an active patient of a different therapist (or isn't a privileged/staff account), and treat a pre-existing User as an error requiring explicit con
- **[Info] Fetch POST sends no X-CSRFToken and base_gamified.html has no global fetch patch** (`strength_app/templates/strength_app/stretch_execute.html:504-514`) — Add X-CSRFToken to these two fetch calls (reuse a getCsrf cookie reader) or add the same global window.fetch CSRF-injection patch to base_gamified.html so all descendant AJAX is covered consistently.

**Specifically recommended verification steps:**
1. **E-3 / Media serving:** on the live host, request `/media/therapist_reports/<known-file>.pdf` (a) unauthenticated and (b) as a different therapist; confirm both are denied. If the web server serves it directly, finding E-3 is High.
2. **E-2 / Transport:** curl a production URL and confirm a `Strict-Transport-Security` header is present and HTTP→HTTPS redirects; if absent, set `SECURE_PROXY_SSL_HEADER` + `DJANGO_SSL_REDIRECT`.
3. **I-1/I-2 / Dependencies:** run `pip-audit`/`safety` against a live advisory DB; confirm Django 4.2.30 is the newest 4.2.x LTS patch and that reportlab 4.4.4 has no applicable PDF/RML code-injection CVE (the app renders patient fields into PDFs).

---

*End of report. No source files were modified during this audit.*
