# Security Audit — Run 2 (2026-06)

Scope: full W5 checklist from the Run-2 spec — IDOR sweep, authN, CSRF,
XSS, rate limiting & proxy trust, enumeration, headers/CSP, sessions,
dependencies, secrets & history, prod behaviour, admin. Method: three
independent code sweeps (IDOR; CSRF/XSS; authN/sessions/headers) +
dependency audit + history grep. All Highs and Mediums found this run are
FIXED in commit `R2-W5`.

## Findings table

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | **IDOR sweep: 35+ ID-taking routes audited — zero holes.** Every patient route filters by the session patient (`patient=patient` / `_require_patient`); every therapist route goes through `get_linked_patient_or_404` (cross-therapist 404); every coach route verifies `CoachPatientLink`; new R2 routes (session detail, alerts, copy-week, notes, reset-password) were built with the same pattern and have cross-access tests (`test_r2_u4_other_patients_session_404s`, `test_r2_t2_other_therapists_alert_blocked`, group4 cross-therapist tests) | — | **VERIFIED CLEAN** |
| 2 | Therapist program-builder rendered DB-sourced free text (`load`, exercise name/pattern) into an `innerHTML` template literal unescaped — a stored payload could break out of the attribute context | Medium | **FIXED** — `esc()` helper escapes every interpolated value |
| 3 | `SESSION_COOKIE_AGE=7d` AND `SESSION_EXPIRE_AT_BROWSER_CLOSE=True` set together (contradictory) | Medium | **FIXED** — decision: 7-day persistent (personal-phone PWA; re-login friction kills adherence; browser-close rarely fires on mobile). Documented in settings.py |
| 4 | `save_gate_test_result` and `save_exercise_results` (legacy AJAX writes) had no rate limit | Medium | **FIXED** — 60/min each, matching the other data endpoints |
| 5 | No `Referrer-Policy`; no CSP | Medium | **FIXED** — `Referrer-Policy: same-origin` on every response; `Content-Security-Policy-Report-Only` with the target policy (enforcement path documented in `strength_app/middleware.py`: inline JS extraction → nonces → enforce; started with cv_core.js) |
| 6 | Django pinned at bare `4.2` (Apr 2023) — dozens of published fixes behind | **High** | **FIXED** — pinned to **4.2.30** (latest 4.2 LTS patch); full suite green on it |
| 7 | Registration says "This phone number is already registered. Please log in." — phone enumeration | Medium | **ACCEPTED (documented)** — judged: hiding this breaks legitimate re-registration UX; endpoint is rate-limited 3/10 min; phone numbers are a weaker secret than emails in this market; the new reset flow IS enumeration-safe (identical responses). Revisit if abuse appears |
| 8 | `_gen_patient_id` / coach IDs are guessable (name-derived / sequential) | Low | **ACCEPTED (documented)** — every route that accepts an ID also requires an authenticated session + ownership/link match and 404s otherwise, so a guessed ID discloses nothing. Opaque IDs noted as a future migration; not now |
| 9 | Dependencies: `pip-audit` of the production environment — **0 known vulnerabilities in the 7 pinned packages** (Django 4.2.30, dj-database-url, gunicorn, mediapipe, psycopg2-binary, reportlab, whitenoise). The dev machine's global env shows 72 findings in packages NOT in requirements.txt (torch, streamlit, keras, flask…) — not deployed | Info | **RECORDED** (.r2 run log) |
| 10 | Secrets: working tree + full `git log -p` grep — only test fixtures and the documented `dev-key` placeholder; `SECRET_KEY` fail-fast from env with no fallback; `.env*`/`db.sqlite3` git-ignored | — | **VERIFIED CLEAN** |
| 11 | XSS surfaces: all user text (therapist messages, visit notes, names, pain locations, notes_for_patient) renders through Django autoescape; the one `mark_safe` (invite credentials) pre-escapes every value; `cv_config_json`/`json_script` escape `<`; no `csrf_exempt` anywhere; every JS POST carries `X-CSRFToken` or a form token | — | **VERIFIED CLEAN** |
| 12 | AuthN: both logins + coach login `session.flush()` before establishing identity; logouts flush; login errors generic on all three; `change_password` rate-limited + `cycle_key()`; new reset flow: enumeration-safe, 1-hour single-use tokens, sibling tokens killed on use, rate-limited; therapist temp-passwords force a change at next sign-in | — | **VERIFIED** |
| 13 | Headers: HSTS (1y, preload) / SSL redirect / secure cookies gated on prod; `X-Frame-Options: DENY`; nosniff; Permissions-Policy camera=self | — | **VERIFIED** |
| 14 | Admin: no password hashes in any `list_display`; RedFlagEvent admin read-only. Operational note (no code): strong admin creds at deploy; consider moving `/admin/` later | Info | NOTED |
| 15 | Known limitation (carried from Run 1): password change does not invalidate OTHER live sessions (needs a server-side token registry) | Low | **OPEN** — documented |

## Cross-access test matrix (automated)

| Attacker → resource | Result | Test |
|---|---|---|
| Patient A → patient B's session detail | 404 | `test_r2_u4_other_patients_session_404s` |
| Patient A → patient B's report / stretch PDF / match | 404 (owner-filtered `get_object_or_404`) | group3/group4 + view filters |
| Therapist 1 → therapist 2's link | 404 | `test_get_linked_patient_or_404_blocks_other_therapist` |
| Therapist 1 → therapist 2's alert | 404 | `test_r2_t2_other_therapists_alert_blocked` |
| Coach without active link → athlete | 404 | coach views `get_object_or_404(CoachPatientLink, …)` |
| Anonymous → any patient/therapist route | redirect to login / 401 | `_require_patient` / decorators |

## What a deployer must still do (see DEPLOY_CHECKLIST.md)

set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS`,
`DJANGO_CSRF_ORIGINS`, `DJANGO_SSL_REDIRECT=1`, `DJANGO_TRUSTED_PROXY=1`
(behind Render's proxy), SMTP creds for password reset, strong admin
credentials.
