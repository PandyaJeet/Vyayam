# VYAYAM — DEEP CODEBASE AUDIT, BUG ELIMINATION & PHYSIO-GRADE POLISH
**Handoff prompt for Claude Code (Fable). Prepared 2026-06-11 by Claude (chat) after direct analysis of the repo snapshot.**

---

## 0. MISSION

You are working on VYAYAM, a Django/PostgreSQL physiotherapy-principled strength training platform with MediaPipe pose detection. Your job in this run:

1. Fix the **verified bugs** listed in Phase 1 (each was confirmed against the live code with file:line evidence — two of them are regressions inside fixes from the previous audit, so do not trust changelog claims; trust the code).
2. Perform a **systematic, patient, full-codebase pass** (Phases 2–4): every exercise module, every engine file, every view, every template that affects clinical behavior. Take hours if needed. Depth over speed.
3. Add the **physiotherapist-facing details** in Phase 5 — the small things a working physio would point out in two minutes of using the app.
4. Harden, verify, and produce a final report (Phases 6–7).

This is a solo founder's production codebase headed toward a clinical pilot. Every fix must be conservative, evidence-based, and verified. **Make no unverified edits. Confirm every find-string matches exactly once before replacing; if it doesn't, STOP on that item, log it, and move on.**

---

## 1. REPO STATE & WORKING AGREEMENTS

- **Repo root:** the `vyayam_django/` Django project. Branch at snapshot time: `audit-fixes-2026-04-20`, HEAD `111b480` (patient self-service change password).
- **Create a new working branch off current HEAD:** `deep-audit-2026-06`. All work happens there.
- **Checkpoint discipline:** `git add -A && git commit -m "checkpoint before <phase>"` before each phase. One commit per logical fix, message format: `fix(DA-<id>): <summary>`. Push to origin at the end of each phase only.
- **Never commit:** `db.sqlite3`, anything in `media/`, `.claude/`, `*.log`. (`.gitignore` already covers these — keep it that way.)
- **Environment for all commands:** `DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True` prefixed. SQLite is fine locally; do not point at any production DATABASE_URL.
- **Migrations are allowed** where a fix or feature requires one (Phase 5 will). Name them descriptively. Never edit an existing applied migration.
- **No scope creep:** do not touch the V2 Bayesian diagnostic staging code, do not build return-to-sport/rehab pathways, do not redesign UI aesthetics. V1 is **uninjured-only**: red-flag work is *screening and triage*, never treatment.
- **When clinically ambiguous → STOP and log.** Add the item to `DECISIONS_NEEDED.md` with your recommendation and continue with the next item. Do not guess on anything that changes what a patient is told or prescribed.

### Non-negotiable product rules (standing decisions from Pawan — treat as constraints)
- **R1 — Athlete/coach tier framing:** never use rehab/clinical/medical framing in the athlete tier. All gates are "training-readiness", never "medical clearance". (Phase 1 item C4 and C9 enforce this.)
- **R2 — No ACWR anywhere.** It was formally excluded as a discredited metric. Remove computation and all surfaced text (C4). Keep `session_rpe` capture — it's independently useful.
- **R3 — Positioning:** VYAYAM amplifies therapists, it does not replace them. No copy that diagnoses, no copy that overclaims.
- **R4 — Patient-facing tone:** plain, calm, non-alarmist; emergency screening copy must say "stop and seek urgent medical care / contact your doctor" — never name a suspected diagnosis to the patient.

---

## 2. PHASE 0 — BASELINE (do this first, ~15 min)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # reportlab IS in requirements now
DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True python manage.py check
DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True python manage.py migrate
DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True python manage.py test strength_app.tests.test_models strength_app.tests.test_group3 strength_app.tests.test_group4 therapist_app.test_models therapist_app.test_group4 strength_app.tests.test_group5 2>&1 | tail -20
```

Record the baseline: which tests pass/fail BEFORE you change anything. If `mediapipe` install fails in this environment, note it and guard imports as the code already does (`CV_AVAILABLE` pattern) — do not let it block the rest of the audit. Read these before editing anything:

- `AUDIT_FIXES_CHANGELOG.md` and `GROUP1_AUDIT.md` … `GROUP6_AUDIT.md` (prior audit context — but remember: **two of its "fixes" are broken**, see C1/C2)
- `strength_app/tests/clinical_audit/` — there is an existing harness (core / generators / invariants / oracles / watchers). **Extend it; do not rebuild it.**

---

## 3. PHASE 1 — VERIFIED CRITICAL FIXES

Each item: WHERE (verified file:line at snapshot), WHAT'S WRONG, FIX, ACCEPTANCE. Re-verify line numbers yourself before editing (they may drift a few lines).

### C1 — XP form-safety gate is defeated by `max()` ⚠️ regression of changelog fix #12
**Where:** `strength_app/v1_gamification.py`, `compute_session_xp()` (~lines 230–251).
**Wrong:** Per-exercise gating is correct (`form_score < MIN_FORM_SCORE_FOR_XP → continue`), but the function ends with `return max(XP_PER_SESSION, total_xp)`. A session where **every** exercise scored below 55 still returns base XP — the gamification loop rewards unsafe movement, which is exactly what the gate was added to prevent.
**Fix:** If `exercise_results` is non-empty and *no* exercise passed the gate → return `0`. Keep the `XP_PER_SESSION` fallback **only** for the empty-results legacy case. Apply `min`/sanity clamp so XP can't exceed a sane ceiling either.
**Acceptance:** unit test: results = 3 exercises all form 40 → XP 0. Results = mixed (one ≥55) → XP = sum of passing exercises, no floor applied. Empty results → `XP_PER_SESSION`.

### C2 — Mandatory deload fallback silently never fires ⚠️ regression of changelog fix #11
**Where:** `strength_app/v1_safety_logic.py`, `check_deload_needed()` (~lines 290–303).
**Wrong:** Fallback accesses `patient.periodisation_state`, but the OneToOne related_name on `PeriodisationState` is **`periodisation`** (`strength_app/models.py` ~line 335). The `AttributeError` is swallowed by `except Exception: pass`, so whenever a caller omits the state, the mandatory 4-week time gate is skipped entirely.
**Fix:** Use `patient.periodisation`. Catch only `PeriodisationState.DoesNotExist` / `ObjectDoesNotExist`, not bare `Exception`. **Also**: in the branch where `periodisation_state` *is* passed, add the same `last_deload_date` calendar check that exists in the fallback — currently the primary branch only checks the session-driven counter, which drifts from calendar time (see C11).
**Acceptance:** unit tests: (a) patient with `weeks_since_deload=4`, called WITHOUT state → `(True, ...)`; (b) state passed with counter 2 but `last_deload_date` 5 weeks ago → `(True, ...)`; (c) new patient with no state → no crash, falls through to feedback checks.

### C3 — Form score systematically penalizes CORRECT deep squats (the surviving half of the old "back rounded" bug)
**Where:** `strength_app/exercise_system/exercises/full_squat_v2.py` — `get_target_poses()` sets `avg_back: 155` at `bottom` (tolerance 10) and 160 in descending/ascending; `calculate_real_time_form_score()` passes the full target dict to `FormCalculator`.
**Wrong:** `avg_back` is the shoulder→hip→knee angle (hip flexion — the file's own comment block says so and forbids using it for safety cues). At a *correct* deep squat bottom this angle is roughly 50–90°, not 155°. Error ≈ 65–105° → that component scores 0 in `FormCalculator.calculate_angle_accuracy`, dragging angle accuracy to ~50% and the composite score down ~25 points **on every correct rep**. The old alert *text* was removed; the scoring penalty was not. This is the live mechanism behind "false back-rounded / bad-form flags on correct deep squats".
**Fix (do this globally, not just full_squat):**
1. For every squat/hinge-pattern `_v2` module that includes a torso/`avg_back`/`back` key in `get_target_poses()`: either (a) set physiologically plausible per-phase hip-flexion targets with wide tolerance (e.g. full squat bottom ≈ 70°, tol 25), or (b) **drop the back key from the target dict entirely** so `FormCalculator` only scores what's actually measurable. Prefer (b) wherever the angle is a synthetic proxy (e.g. `lunges_v2.py` / `decline_squats_v2.py` fabricate `back_angle = 180 - lean_ratio*60`).
2. Keep the existing comment that spinal position is not measurable with MediaPipe's 33 landmarks; ensure no module re-introduces spine claims.
**Acceptance:** the ideal-trajectory invariant in Phase 2 (H2) must pass: a synthetic *perfect* deep squat trajectory scores ≥ 85 average. Add a regression test for full_squat specifically.

### C4 — ACWR still computed and surfaced (violates standing decision R2)
**Where:** `strength_app/v1_prescription_engine.py`: `_compute_acwr()` (~1050–1103) and the "P31: ACWR check" block (~1502–1523) that writes `meta['acwr']`, `meta['acwr_status']`, mutates set counts, and appends "P31: ACWR …" `modifier_notes`. `SessionFeedback.session_rpe` help text also says "for ACWR calculation (P31)".
**Fix:** Delete `_compute_acwr` and the entire P31 block including the meta keys and notes. Do **not** replace with another composite injury-risk metric. If a load-spike guard is wanted, the only acceptable form is a plain training-readiness note when this week's planned working-set count exceeds last week's by >30% — text like "Load is rising quickly this week — listen to your body", no acronym, no score, no auto volume cut. Update the `session_rpe` help_text to "Session RPE 1-10 — used for load and recovery trends" (model comment edit only; no migration needed for help_text, but if `makemigrations` generates one, commit it). Grep the whole repo (`grep -rni acwr --include='*.py' --include='*.html'`) and clear every reference outside `tests/clinical_audit` generators; update those generators to stop seeding ACWR hints.
**Acceptance:** repo-wide grep for `acwr` returns only this prompt/report files. Engine still generates sessions for an athlete-tier patient without error (test with the `9100000000+` demo seed block if present in the DB, else create one).

### C5 — Red flags are self-clearable with no audit trail
**Where:** `strength_app/v1_onboarding_views.py`, `onboarding_red_flags()` (~993–1042). POST overwrites `red_flags_json`, `absolute_stop`, `absolute_stop_reason` with whatever is submitted. A patient who was hard-stopped can revisit the URL, uncheck everything, and silently clear their own absolute stop. Nothing is recorded.
**Fix:**
1. New model `RedFlagEvent`: `patient FK, changed_at, source ('patient'|'therapist'|'system'), change_type ('flags_updated'|'absolute_stop_set'|'absolute_stop_cleared'), old_flags JSON, new_flags JSON, old_stop bool, new_stop bool, note text`. Migration. Register in admin (read-only).
2. In `onboarding_red_flags` POST: diff old vs new; create a `RedFlagEvent` on any change. Clearing `absolute_stop` requires an explicit extra confirmation field in the form (e.g. checkbox "I confirm my situation has changed / I have medical clearance to train") — if absent, re-render with the warning instead of clearing. Always log the clear event.
3. If `patient.assigned_therapist` or an active `CoachPatientLink`/`TherapistPatientLink` exists, append a flag note to that link (reuse the `coach_flag_review` note pattern) so the professional sees "Patient cleared absolute stop on <date>".
**Acceptance:** tests: setting a stop creates an event; clearing without confirmation does NOT clear and re-renders; clearing with confirmation clears + creates event + appends link note when linked.

### C6 — Emergency screening gaps (cauda equina, DVT, systemic red flags)
**Where:** `RED_FLAG_OPTIONS` / `ABSOLUTE_STOP_OPTIONS` in `strength_app/v1_onboarding_views.py` (~271–293) and template `onboarding_red_flags.html`.
**Fix:** Add to `ABSOLUTE_STOP_OPTIONS` (patient-facing copy in plain language, per R4 — describe the symptom, do not name the diagnosis in patient copy):
- `saddle_numbness_bladder` — "New numbness around the groin/inner thighs, or new trouble controlling bladder or bowels"
- `calf_swelling_one_side` — "One calf newly swollen, hot, or painful (especially after travel, surgery, or bed rest)"
- `chest_pain_exertion` — "Chest pain, pressure, or fainting during exercise"
- `night_pain_weight_loss` — "Constant night pain that doesn't change with position, or unexplained weight loss"
- `numbness_weakness_progressive` — "Numbness or weakness in a limb that is getting worse"
For each of these, the stopped-state screen must say: **"Please stop and seek urgent medical care before training."** (stronger than the generic stop copy). Keep internal IDs clinical (fine in code), patient copy symptom-based. Wire the same options into the therapist-side health profile screen if one exists in `therapist_app` (check `TherapistPatientHealthProfile` usage).
**Acceptance:** selecting any new option sets `absolute_stop`, renders urgent-care copy, creates the C5 audit event; engine refuses to generate a session (verify `check_absolute_stop` path → `v1_stopped`).

### C7 — `generate_report` fabricates progress data on every call
**Where:** `strength_app/views.py` `generate_report()` (~1294–1326): calls `gen_report(patient.patient_id, weeks=4)` but `utils.generate_progress_report` signature is `(patient)` (utils.py ~570). The TypeError is swallowed and the fallback creates a report with **hardcoded** `overall_adherence_rate=75.0`, `total_sessions_prescribed=20`, "Continue current program". Patients/therapists see fabricated clinical numbers.
**Fix:** Call with the correct signature (`gen_report(patient)`); inspect `utils.generate_progress_report` and make it compute real values from `WorkoutSession`/`SessionFeedback` in the window (sessions completed vs `sessions_per_week * weeks`, real average form score, real green-rep totals, pain summary). The fallback may remain for true failures but must **never invent numbers** — zero/None + "insufficient data" copy instead. Also fix `view_report(report_id: str)` type hint → `int` to match the URL.
**Acceptance:** integration test: patient with 3 real sessions → report numbers match DB aggregates exactly; patient with 0 sessions → "insufficient data" report, no fabricated 75%.

### C8 — Legacy session bridge crashes on `meta` key (GROUP3 finding, still live)
**Where:** `strength_app/utils.py` `execute_workout_session()` (~495–512): iterates `prescription_data.items()` and treats every value as a list of exercise dicts. A `meta` dict value yields string keys → `exercise.copy()` AttributeError. `tests/test_group3.py` asserts the bug exists — flip that test to assert the FIX.
**Fix:** Skip non-list sections (`if not isinstance(exercises, list): continue`) and skip non-dict items defensively.
**Acceptance:** updated test_group3 passes with a prescription containing `meta`.

### C9 — Athlete-tier wording: "Clinical Reasoning" (violates R1)
**Where:** `strength_app/templates/strength_app/coach_override.html` (~81–82 label + textarea), `coach_athlete_detail.html` (~331–332 display). Model field name `clinical_reasoning` can stay (no migration churn) — only the user-facing copy changes.
**Fix:** Label → "Coaching rationale"; placeholder → "Why are you overriding the AI session?"; detail display label likewise. Sweep all `coach_*` templates and `v1_coach_views.py` strings for "clinical", "rehab", "medical", "patient" (athlete tier should say "athlete") and adjust patient→athlete wording where it leaks. Do NOT touch therapist_app (that side is legitimately clinical).
**Acceptance:** `grep -rni "clinical\|rehab" strength_app/templates/strength_app/coach_*.html` → no user-facing hits.

### C10 — Nutrition traffic light shows RED for patients with no targets set
**Where:** `strength_app/v1_nutrition_engine.py` `get_daily_nutrition_summary` (~195–215): missing `NutritionProfile` → targets 0 → `pct_cal = 0` → `'red'`.
**Fix:** When no targets exist, return `traffic_light='none'` (or `'setup'`) plus a `needs_setup=True` flag; templates that render the light must show "Set your targets" state instead of red. Trace all consumers (`v1_nutrition_dashboard`, post-session nutrition card in `v1_session_complete`).
**Acceptance:** new patient, no profile → dashboard shows setup state, not red.

### C11 — Deload "weeks" drift from calendar time
**Where:** `strength_app/v1_session_views.py` `v1_session_complete` (~808–818): `current_week`/`weeks_since_deload` advance every `sessions_per_week` **sessions**, not per calendar week. A 3×/week-configured patient who actually trains 6×/week hits "4 weeks" in 2 calendar weeks; one training 1×/week hits it in 12.
**Fix:** Keep session counting for phase context, but make the deload gate calendar-aware: C2 already adds the `last_deload_date` check in both branches; additionally, when a week is advanced here, also stamp/refresh a `week_advanced_at` style anchor OR simply rely on `last_deload_date` math as the authoritative mandatory gate (preferred — least surface area). Document the chosen rule in a comment block: "Mandatory deload = max(counter, calendar) reaches limit."
**Acceptance:** test from C2(b) covers it; add the inverse: counter 5 but last_deload_date 1 week ago (shouldn't happen, but counter wins → deload True is acceptable; document).

### C12 — Fabricated green/yellow/red rep counts in self-serve flow
**Where:** `strength_app/v1_session_views.py` `v1_post_session_feedback` (~709–737): `green_reps = round(total_reps * form/100)`, yellow = remainder × 0.6, red = rest. These synthetic numbers are persisted to `ExerciseExecution` and later rendered in reports as if they were CV per-rep classifications.
**Fix (honesty over invention):** If the client actually sends per-rep quality (check `v1_exercise_execute.html` JS payload around line ~5221 — it currently sends form_score, reps_per_set, pain), use real counts. If it doesn't, **stop fabricating**: persist `overall_form_score` and rep totals, set green/yellow/red to the same derived numbers ONLY if clearly labeled — better: add `rep_quality_source` Char field ('cv'|'derived') via migration, set 'derived' here, and make report/template copy say "estimated from form score" wherever derived counts render (progress views, therapist report, pdf_generator). If extending the JS payload to carry the real per-rep colors from the CV layer is a ≤50-line change, do that instead and set 'cv'.
**Acceptance:** any UI/report surface showing rep colors for a derived session carries the "estimated" qualifier; tests assert the field is set.

### C13 — Input validation on JSON endpoints (crash + clamp pass)
**Where:** `strength_app/v1_session_views.py` `v1_save_exercise_result` (~528–551): bare `int()`/`float()` on client values → 500 on junk; no clamping (`pain_severity` 999, negative sets, form_score 10⁶). Same pattern in `v1_post_session_feedback` (`int(request.POST.get('pain_severity') or 0)`, `session_rpe`), `coach_set_competition` (raw string into DateField → ValidationError 500 on bad format), and nutrition `v1_quick_log_api` (verify).
**Fix:** Introduce one helper (mirror therapist_app's `_safe_int`) in a shared module; clamp: pain 0–10, severity 0–10, rpe 1–10, sets 0–20, reps 0–100, form_score 0–100, rest 0–600. `coach_set_competition`: parse with `datetime.strptime`/`date.fromisoformat` inside try, redirect with error message on failure. Return 400 JSON (not 500) on malformed bodies.
**Acceptance:** tests posting garbage to each endpoint → 400 or clamped persistence, never 500.

### C14 — Red-flag map internal contradiction
**Where:** `strength_app/red_flag_map.py` `knee_pain_patellofemoral`: excludes `'step_ups'` AND sets `replace_with {'step': 'step_ups'}` ("Low box only").
**Fix:** Replacement must be a non-excluded ID. If a distinct low-box variant exists in content (`step_ups` levels? check `exercise_content` for a low-step variant or `step_downs`), use it; else replace with `terminal_knee_extension` or `wall_sit` (both PFP-safe) and note "low box step-ups allowed under supervision" in `notes`. While in this file: remove the duplicate `'lateral_Hops'` entries (canonical ID per `exercise_tags.py:831` is `lateral_hops`) and add a module-level assertion/test that every `replace_with` target is absent from the same flag's `exclude_exercises` and exists in the content/tag layer.
**Acceptance:** new test `test_red_flag_map_integrity` passes for ALL flags.

### C15 — Hormonal modifier key-convention drift
**Where:** `strength_app/v1_safety_logic.py` `get_hormonal_modifiers` returns `volume_multiplier`-style keys (and its `None` branch returns ONLY those), while `v1_prescription_engine.py` has its own `_resolve_hormonal_modifiers` using `volume_modifier` keys (engine ~130–149, consumer ~347). Two parallel systems, mixed dual-key dicts in 'stable'/'unknown' branches.
**Fix:** Pick ONE convention (`volume_modifier`, the engine's), make `get_hormonal_modifiers` the single source returning a complete dict (including `plyometric_clearance`, `rest_modifier`) for every phase incl. None/stable/unknown, delete or delegate the engine-internal resolver, and update `v1_constants.HORMONAL_PHASE_MODIFIERS` keys to match. Trace every consumer before changing — this one has tentacles; do it in its own commit with tests for each phase value.
**Acceptance:** unit test asserts identical modifier dict shape for all 7 phase values; menstruation-severe still produces the mobility-only session (existing group5 behavior).

---

## 4. PHASE 2 — EXERCISE SYSTEM DEEP PASS (all 264 `_v2` modules)

This is the "go through all exercises" part. There are **264 modules** in `strength_app/exercise_system/exercises/`. Do them ALL, in batches of ~20, committing per batch (`fix(DA-EX-batch03): ...`). For each module check this list:

**Per-exercise checklist**
1. `get_target_poses()` includes every phase the state machine can be in (incl. `start`/`active` where the runner uses them) — missing phase = KeyError at runtime.
2. Target angles are **physiologically plausible for that exercise and phase** (the C3 class of bug). Sanity-check against the movement: e.g., plank hip angle ~170–180; hinge bottom hip flexion 60–100; overhead press top elbow ~170. Any synthetic/proxy angle (lean_ratio constructions, hardcoded 165s) either gets a realistic target+wide tolerance or is removed from the *scored* target dict. Log every changed number in the report with one-line reasoning.
3. `tolerance` present, > 0, and ≥ 8 for noisy landmarks (ankles/wrists at distance).
4. Landmark chains: correct `PoseLandmark` enums, correct side pairing; **no claims about spinal position** (grep the module for "spine", "back round", "lumbar" in cue strings).
5. Rep state machine: hysteresis between thresholds (entering vs leaving a phase must differ by ≥ ~10° or use distinct thresholds) so a single noisy frame can't double-count; rep increments exactly once per cycle; `rejected_count` path reachable.
6. Hold/isometric exercises (planks, wall sit, side planks, copenhagen, hollow holds…): rep counter replaced by a **duration timer**; `prescribed_hold_duration` is what the UI gets, not reps. Cross-check `_calculate_dosage`'s hold path delivers `hold` for these IDs and the execute template renders a countdown, not a rep counter.
7. Unilateral exercises: left/right tracked separately, `get_asymmetry()` or equivalent present where the plank-tap pattern was established; weaker-side-first ordering supported (ties to Phase 5 F6).
8. `validate_form()` not a `return {}` stub (29 were patched generically — verify the generic patch actually references that exercise's real target keys, not absent ones).
9. Voice cues (`voice_coach_v2` calls): cue text matches the actual thresholds (e.g., a "go deeper" cue keyed at 100° when the target is 90 is fine; keyed at 60 is not).
10. Division-by-zero in tempo/score math (`len(...)` denominators, `tolerance - 15` style — see H1 below).
11. No `print()` of patient data; logging only.

**Harness work (do BEFORE the manual batches — it will find most of this automatically):**
- **H1 — FormCalculator unit fixes:** `calculate_angle_accuracy` (a) divides by `(tolerance - 15)` → ZeroDivisionError at tolerance==16? No — verify the exact branch: it divides when `15 < error <= tolerance`; tolerance==15 makes the branch dead but any tolerance in (15,16) explodes the slope; tolerance ≤ 15 silently DISABLES strict tolerances (errors up to 15° still score ≥70 even when the exercise asked for ±8). Rework: piecewise curve parameterized by the exercise's own tolerance so tighter tolerance = stricter scoring; add unit tests at tolerance 5/8/10/15/20/25.
- **H2 — Ideal-trajectory invariant (the big one):** extend `tests/clinical_audit/` with a generator that, for every registered exercise, synthesizes the *ideal* angle trajectory from its own `get_target_poses()` phase sequence (interpolate phase→phase, sample ~20 frames/phase, neutral stability/tempo) and asserts: (a) no exception through the full cycle, (b) ≥1 rep counted for rep exercises, (c) mean form score ≥ 85. Every module failing (c) has a C3-class target bug — fix the module, not the test. Run it across all 264 and include the pass/fail table in the final report.
- **H3 — Registry integrity:** every ID in `exercise_registry_v2` instantiates lazily without error (try/except import sweep), casing consistent, no duplicate IDs differing only by case or plural (`partial_squat` vs `partial_squats` — GROUP3/4 flagged gate-test↔chain ID mismatches; build the canonical map and fix lookups in `utils.py` / `exercise_progressions.py`).

---

## 5. PHASE 3 — DATA INTEGRITY SWEEP (content / tags / equipment / chains)

I ran the cross-check already; exact gaps below. For each missing entry, **author real content** (sets of cues, common mistakes, contraindication notes — clinically sane, concise, original wording) or map to an existing canonical ID if it's a naming alias. Tag entries need pattern/level/unilateral/impact fields matching `exercise_tags.py`'s schema. Equipment entries: empty list = bodyweight.

**A. V1 progression-chain IDs (110 total) missing from `EXERCISE_CONTENT`+gap-fill (8):**
`deadlift_dumbbell, dragon_flag_progression, dumbbell_rowing, hollow_body_rock, nordic_curl_partner, single_arm_pull_up_prog, single_arm_push_up_prog, single_arm_single_leg_plank`
→ These are PRESCRIBABLE TODAY with a blank execute page. Highest priority.

**B. Missing from `EXERCISE_TAGS` (90 of 110 chain IDs!):** full list in Appendix A. The tag layer is how modifiers/red-flag logic reason about exercises — 82% coverage gap means most chain exercises bypass tag-based logic. Decide the actual role of tags first (read `get_patient_modifier`/`apply_modifier` call sites): if tags are only used for the 68-exercise legacy set, document that; if the V1 engine path consults them (it imports `exercise_tags` helpers in views.py), fill all 90 with at least `{pattern, unilateral, impact, equipment}`.

**C. Missing from `EXERCISE_EQUIPMENT_REQUIRED` (45):** Appendix A. Absent key = treated as bodyweight by `filter_exercises_for_patient` — wrong for `deadlift_dumbbell`, `dumbbell_rowing`, `nordic_curl_weighted`, `single_arm_farmer_heavy`, band/slider items. A bodyweight-only patient can currently be prescribed dumbbell work. Fill all 45.

**D. Legacy gate-test chains (`exercise_progressions.PROGRESSION_CHAINS`, 30 IDs):** 13 lack content (list in Appendix A) — mostly cardio/balance (`butt_kicks, jumping_jacks, planks, single_leg_balance…`). Several look like plural-alias problems (`planks` vs `plank`?, `tricep_extensions` vs `tricep_extensions_v2` module exists). Resolve alias-vs-missing per ID; add a unit test asserting full coverage so this never regresses.

**E. CV module coverage:** chain IDs with no matching `_v2` module: `deadlift_dumbbell, dumbbell_rowing, nordic_curl_partner, single_arm_pull_up_prog, single_arm_push_up_prog`. For these the execute page must gracefully run in **manual-count mode** (no camera promise). Verify the template/view fallback exists (`CV_AVAILABLE` analog per-exercise); if the UI claims AI tracking for them, gate the claim.

**F. Warm-up/cool-down library:** my loader found 0 structured ids in `warmup_library.py` — its schema differs. Read it properly, then run the same coverage check on every warm-up/cool-down item (name/cues present, durations sane, no excluded-by-red-flag items injected into a flagged patient's warm-up — check `_resolve` path in engine).

---

## 6. PHASE 4 — ENGINE & FLOW LINE-BY-LINE AUDIT

Work through these files completely (yes, every line — you have time). For each: read top-to-bottom, list every defect with severity (S1 crash / S2 wrong-clinical-output / S3 wrong-UX / S4 hygiene), fix S1–S2 immediately in scoped commits, batch S3–S4.

| # | File(s) | Specific watch-fors (beyond general reading) |
|---|---|---|
| 1 | `v1_prescription_engine.py` (1682 ln) | post-C4 cleanup; asymmetry block actually prevents advancement (verify fix #9 against `asymmetry_rules` shape); `_select_exercises_for_pattern` double-fallback can still return [] → what does caller do? (empty pattern silently dropped vs session with 0 exercises); deload week actually swaps to deload dosage; football extras respect red-flag exclusions (`_apply_football_principles` output goes through `filter_exercises_for_patient`? verify — if not, a flagged athlete gets plyo injected) |
| 2 | `v1_session_views.py` (1037) | the 12 `except Exception` blocks in `v1_session_complete` — narrow each (H4 policy below); session regeneration on refresh (does `_get_or_refresh_session_data` regenerate mid-session and orphan results?); warm-up flow index bounds; `_pattern_to_category` completeness |
| 3 | `v1_onboarding_views.py` (1265) | per-step input clamps (sitting hours, session minutes, cycle length 20–45); back-navigation doesn't duplicate StrengthProfile rows; `onboarding_save_test_result` validation; age model validator (13) vs onboarding rule (18) — align model to 18 with migration, document |
| 4 | `views.py` (1712) | legacy gate-test loop (re-enabled routes) end-to-end against current chains (the partial_squat/_s mismatch lives here); `save_exercise_results` route still commented — either restore safely or remove the dead view+template references; `session_analyzers` dict growth — add LRU/TTL eviction (≥30 min idle) since cleanup endpoint is best-effort; exercise_library/detail render for every content ID |
| 5 | `v1_coach_views.py` + coach templates | C9; override `exercises_json` schema validation (each item: known exercise_id, sets 1–10, reps 1–100) — reject invalid with inline error; squad athlete filter correctness (recent commit a9df06e) |
| 6 | `v1_football_views.py` + `v1_football_constants.py` | anchored HSR counter: `if not fp.hsr_phase_start_week` re-anchors when start week is legitimately 0 — use `is None` semantics (field default? check; migrate default to NULL if needed); Nordic camera diagnostic stays read-only/no-scoring; assessment thresholds vs constants bands; `plyometric_cleared='none'` string vs field choices |
| 7 | `v1_therapist_session_views.py` + therapist_app `views.py` (869) | already the best-validated flow — mirror its `_safe_int`/clamp patterns outward; `get_linked_patient_or_404` on EVERY patient-scoped route (grep for `link_id` routes missing it); pdf_generator: divide-by-zero on empty weeks, long-name overflow, None aggregates |
| 8 | `v1_safety_logic.py` remainder | post-C2/C15; `compute_traffic_light` ignores numeric `pain_severity` — add: severity ≥7 → red, 4–6 → at least yellow regardless of categorical answer; consider sharp `pain_type` from per-exercise results once Phase 5 F1 lands |
| 9 | `utils.py` (627) | post-C8; `django_to_backend_category` balance→lower_body misclass (GROUP3) — add 'balance' mapping; non-deterministic `random` gate simulation behind a flag/seed for tests; transaction.atomic around PatientFamilyCapability ladder advance |
| 10 | `backend/` (7 files) | this is the legacy in-memory engine the re-enabled routes touch: division-by-zero list from GROUP1 (adherence current_week 0; sets/reps 0; empty gate list; CapabilityLevel-vs-string in report_generator) — fix each with guards + tests; placeholder password hashing in main_coordinator must never be importable into an auth path (assert it isn't; add comment WALL) |
| 11 | `models.py` + therapist_app/models.py | add missing MinValueValidators (GROUP2 list: FoodItem macros, ExerciseExecution prescribed_*, xp_earned, depth_achieved); SessionFeedback pain choices vs migration values — write a data-check management command listing rows with out-of-choice values; indexes on (patient, session_date), (patient, log_date) — single migration |
| 12 | Templates (88) | every `{% url %}` resolves (write a smoke test client hitting all GET routes as an authed patient/coach/therapist → assert non-500); forms have CSRF; numeric inputs have min/max attrs matching server clamps; `v1_exercise_execute.html` (5507 ln) — DO NOT refactor wholesale; only targeted fixes (payload validation mirror, pain protocol step wiring, hold-timer UI from Phase 2 item 6) |

**H4 — Silent-exception policy (53 occurrences of `except Exception:` with pass/None):** For each, classify: (a) genuinely-optional enrichment (milestones, nutrition card) → keep but `logger.warning('context', exc_info=True)`; (b) clinical/safety path (periodisation update, deload, football update, data consent logging) → narrow to the specific expected exception, let the rest raise or surface a user-visible soft error. Zero bare swallows remain on safety paths. List the final disposition table in the report.

---

## 7. PHASE 5 — PHYSIOTHERAPIST-GRADE FEATURES
*The "small minute details a physiotherapist would point out". P1 = build now. P2 = build if time after P1+all fixes verified. P3 = spec in the report only, don't build.*

**F1 (P1) — Per-exercise pain actually persisted (self-serve flow).** The execute UI already collects type/location/severity/action per exercise; `v1_save_exercise_result` stores it in the session; `v1_post_session_feedback` then **drops it** — `ExerciseExecution` has no pain fields (models.py ~642–677). Add `pain_reported(bool), pain_type, pain_location, pain_severity(0-10), pain_action` to `ExerciseExecution` (migration), persist from results, and surface: (a) progress page "pain by exercise" list, (b) therapist/coach detail per-session expansion, (c) feed `compute_traffic_light` (a 'sharp' or severity ≥7 per-exercise report this session ⇒ red even if the post-session form says mild). The B2B2C flow already does this properly (`SessionLogItem.pain`) — bring the self-serve flow to parity.

**F2 (P1) — Server-side sharp-pain response mid-session.** Today the response to sharp pain is client-side guidance text only; the server happily serves the next exercise. In `v1_save_exercise_result`: if `pain_type=='sharp'` or `pain_severity>=7` → (a) mark remaining same-pattern exercises this session as auto-skipped with reason 'pain', (b) `next_url` jumps past them, (c) banner context on the next page "We've removed the remaining <pattern> work today because of the pain you reported." Severity ≥8 with action 'stop' → next_url = a stop page variant with rest-of-day guidance (reuse `v1_stopped` with a `pain_stop=True` mode; copy per R4). If a coach/therapist link exists, append a flag note (timestamp, exercise, severity).

**F3 (P1) — Pain-pattern follow-through across sessions.** `v1_session_overview` already shows a one-off follow-up question from the last feedback. Extend: same `pain_location` reported in 2 consecutive sessions ⇒ next generated session auto-regresses the implicated pattern one capability level (bounded, never below 1) with a visible note, and sets `ready_to_advance=False` for that family; 3 consecutive ⇒ pause that pattern entirely + "consider seeing a physiotherapist" copy + therapist note if linked. Implement in the engine's modifier stage; tests for 1/2/3-session escalation and reset on a pain-free session.

**F4 (P1) — Soreness-vs-pain education at feedback time.** On the post-session feedback pain question, one collapsible line: "Dull muscle soreness 24–48h after training is normal. Sharp pain, joint pain, or pain during the movement is not — tell us about that here." Tiny copy change, exactly what a physio asks for first.

**F5 (P1) — Deload-week visibility.** When `current_phase=='deload'` or deload was triggered: dashboard + session overview banner "Deload week — loads are intentionally lighter so your body can adapt. Don't add extra." Verify the dosage actually drops (Phase 4 row 1) so the banner never lies.

**F6 (P2) — Asymmetry made visible and enforced in-session.** Where `asymmetry_rules` mark a weaker side: unilateral exercise cards show "Start with your LEFT side" and the extra-volume ratio is reflected in displayed per-side reps; progress page shows the asymmetry trend across StrengthProfiles (gap closing?). Verify `UnilateralExerciseHandler.check_asymmetry_safe` is actually called in the live path, not just defined.

**F7 (P2) — Rest timer + tempo coach between sets.** Execute page: countdown from `prescribed_rest` after each set (skippable), and tempo display rendered as guided counts (the HSR 6-0-6-0 athletes especially — "6s down… 6s up"). Check what `_add_tempo_parts` already feeds the template and finish the loop. Isometric hold countdown from Phase 2 item 6 lands here too.

**F8 (P2) — Reassessment cadence for everyone.** Football has a 4-week nudge; general patients have nothing. Dashboard prompt when last StrengthProfile > 6 weeks old OR any family `weeks_at_current_level >= 6`: "Time for a quick re-test of <patterns>" linking the relevant gate tests. No auto-changes from the nudge itself.

**F9 (P2) — Skip-with-reason.** Skip button asks one tap: pain / no equipment / no time / too hard. Persist on the result; 'no equipment' twice for the same exercise ⇒ flag the equipment mapping for that patient and reroute via `equipment_routing` next session; 'too hard' feeds `consecutive_comfortable_sessions` reset.

**F10 (P2) — Session duration: actual vs estimated.** Stamp session start (first exercise GET) in the session store; on feedback, persist real elapsed minutes to `total_duration_minutes` instead of the estimate (fall back to estimate if missing). Physios read adherence partly through time-under-session.

**F11 (P3 — spec only)** — Patient-exportable PDF (self-serve) of last 4 weeks incl. pain history + red-flag status, "to show your physiotherapist"; body-weight log over time; therapist console alert strip unifying B2B2C pain>5 alerts with F1/F2 events; per-set RPE (vs session RPE) for the athlete tier.

---

## 8. PHASE 6 — HARDENING & CONSISTENCY SWEEP

1. **Threshold unification:** `v1_session_complete` per-exercise traffic light uses 80/60; XP gate uses 55; FormCalculator bands at 70/85. Define the canonical bands once in `v1_constants` (e.g. GREEN≥80, YELLOW 55–79, RED<55) and import everywhere; document the clinical rationale in a comment.
2. **`change_password` polish:** add `@rate_limit` (5/300s), and on success re-issue session (`cycle_key`) — cheap wins; full cross-session invalidation is out of scope, note as known limitation.
3. **Rate limiter:** X-Forwarded-For trust (GROUP4) — only honor XFF when `DJANGO_TRUSTED_PROXY=1` env is set; else use REMOTE_ADDR. Add `football_save_test_result` and `v1_quick_log_api` to limited endpoints; confirm the auth guard from commit 87d8442 covers all football POSTs.
4. **PWA/UI leftovers from GROUP6:** verify manifest colors, base_gamified SW registration, therapist responsive viewport actually shipped (status says fixed — confirm in files).
5. **Logging:** module-level `logger = logging.getLogger(__name__)` everywhere you touched; no patient names at INFO+.
6. **Dead code:** `get_alternative_for_excluded` (declared dead in changelog) — either wire it into `_select_exercises_for_pattern`'s empty-result fallback (better clinically: swap excluded exercise for its mapped alternative instead of dropping a level) or delete it. Prefer wiring it in, with tests.
7. **README refresh:** the README still describes the legacy 8-dimension flow; add a short "current architecture" section (V1 engine files, athlete tier, B2B2C) so the next audit doesn't re-learn the stack from scratch.

---

## 9. PHASE 7 — VERIFICATION PROTOCOL & FINAL REPORT

**Automated, all green before final push:**
```bash
DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True python manage.py check          # 0 issues
DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True python manage.py makemigrations --check --dry-run   # no missing migrations
DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True python manage.py test strength_app therapist_app    # all suites
# plus the H2 invariant run across all 264 exercises — include its table
```

**Manual smoke (use a fresh patient + the athlete demo seed):** full onboarding incl. a new emergency stop option → stopped screen → audited clear → session generate → execute 2 exercises with a sharp-pain report on #1 (verify F2 skip + note) → feedback → complete (XP 0 if all unsafe) → progress → report numbers real → coach override with rationale label → therapist B2B2C session unaffected.

**Deliverables in repo root:**
- `DEEP_AUDIT_REPORT.md` — for every phase: findings table (id, file:line, severity, status fixed/deferred, commit hash), the H2 pass/fail table, the H4 exception-disposition table, target-angle changes with reasoning, and a "what I did NOT do and why" section.
- `DECISIONS_NEEDED.md` — every STOP item with your recommendation.
- Updated tests proving each C-item (name them `test_da_c1_*` etc. so they're greppable).

**Handoff back:** end your run by printing a ≤30-line summary (counts: fixed S1/S2/S3, exercises corrected, features landed, tests added, open decisions) — Pawan will paste it back to chat-Claude for cross-review.

---

## APPENDIX A — EXACT MISSING-ID LISTS (computed 2026-06-11 from the live data modules)

**A1. Chain IDs missing CONTENT (8):** `deadlift_dumbbell, dragon_flag_progression, dumbbell_rowing, hollow_body_rock, nordic_curl_partner, single_arm_pull_up_prog, single_arm_push_up_prog, single_arm_single_leg_plank`

**A2. Chain IDs missing TAGS (90):** `archer_pull_up, archer_push_up, band_assisted_pull_up, band_woodchop, banded_rdl, bear_crawl, bear_crawl_with_reach, bedsheet_row, bird_dog, bodyweight_rdl, box_push_up, box_squat, change_of_direction, chin_up, close_grip_push_up, copenhagen_plank, copenhagen_with_movement, crab_walk, curtsy_lunge, dead_bug, decline_push_up, deficit_reverse_lunge, depth_jump, doorframe_row, dragon_flag_progression, elevated_table_row, farmer_carry, full_pull_up, goblet_squat, good_morning, handstand_wall_hold, hanging_leg_raise, heel_elevated_squat, hip_hinge_wall, hip_thrust_bodyweight, hollow_body_hold, hollow_body_rock, incline_push_up, knee_push_up, l_sit_pull_up, lateral_bear_crawl, lateral_bound, muscle_up_progression, negative_pull_up, negative_table_row, nordic_curl_partner, nordic_curl_weighted, nordic_hamstring_curl, pallof_press_dynamic, pallof_press_isometric, pause_squat, pike_push_up, pike_push_up_elevated, pistol_squat, plyometric_lunge, prone_hip_extension, prone_y_t_w, pseudo_planche_push_up, ring_push_up, russian_twist_bw, scapular_pull, side_plank, side_plank_hip_dip, side_plank_rotation, single_arm_farmer_heavy, single_arm_plank, single_arm_pull_up_prog, single_arm_push_up_prog, single_arm_single_leg_plank, single_arm_towel_row, single_leg_dead_bug, single_leg_hip_thrust, single_leg_landing, single_leg_slider_curl, single_leg_squat_to_box, sliding_leg_curl, split_squat_static, suitcase_carry, sumo_squat, superman_hold, table_row, towel_row, waiter_carry, waiter_farmer_combined, walking_lunge, wall_handstand_push_up, wall_push_up, wall_sit, weighted_pull_up, wide_grip_push_up`

**A3. Chain IDs missing EQUIPMENT mapping (45):** `bear_crawl_with_reach, box_push_up, change_of_direction, close_grip_push_up, copenhagen_with_movement, curtsy_lunge, deadlift_dumbbell, decline_squats, depth_jump, dragon_flag_progression, dumbbell_rowing, handstand_wall_hold, heel_elevated_squat, hip_hinge_wall, incline_push_up, knee_push_up, lateral_bear_crawl, lateral_bound, nordic_curl_partner, nordic_curl_weighted, pike_push_up_elevated, plyometric_lunge, prone_hip_extension, side_plank_hip_dip, side_plank_rotation, side_step_ups, single_arm_farmer_heavy, single_arm_plank, single_arm_pull_up_prog, single_arm_push_up_prog, single_arm_single_leg_plank, single_arm_towel_row, single_leg_dead_bug, single_leg_hip_thrust, single_leg_landing, single_leg_slider_curl, single_leg_squat_to_box, spanish_squat, split_squat_static, sumo_squat, waiter_farmer_combined, walking_lunge, wall_handstand_push_up, wall_push_up, wide_grip_push_up`

**A4. Legacy gate-test IDs missing content (13 — resolve alias vs truly missing):** `butt_kicks, clock_reaches, deadlift_dumbbell, double_leg_balance, high_knees, jumping_jacks, lateral_gait_training, marching_on_spot, mountain_climbers, planks, single_leg_balance, tandem_walking, tricep_extensions`

**A5. Chain IDs with no `_v2` CV module (manual-count fallback required):** `deadlift_dumbbell, dumbbell_rowing, nordic_curl_partner, single_arm_pull_up_prog, single_arm_push_up_prog`

## APPENDIX B — PRE-ANSWERED DECISIONS (don't re-ask these)
- ACWR: remove, no replacement metric (C4). Session RPE stays.
- Absolute-stop self-clear: allowed WITH explicit confirmation + audit event + therapist note when linked (C5).
- Age: V1 is 18+; align model validator to 18 via migration (Phase 4 row 3).
- Rep-quality honesty: 'derived' labeling acceptable for V1 if real per-rep CV plumbing exceeds ~50 lines (C12).
- `v1_exercise_execute.html`: targeted edits only, no rewrite.
- V2 Bayesian engine and anything tagged V2-staging: untouched.

Good hunting. Patience over speed, evidence over changelog, and log everything.
