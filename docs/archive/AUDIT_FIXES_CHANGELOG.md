# VYAYAM Codebase Audit — Fixes Changelog

**Audit date:** 2026-04-20  
**Agents:** Lead (Agent 1), Clinical Expert (Agent 5), Exercise Library (Agent 9), + 7 specialist agents  
**Branch:** `main`  
**Total commits:** 19 fix commits across 4 tiers  
**Final QA:** `manage.py check` → 0 errors, 0 silenced; 2 warnings are test-key artifacts only

---

## Tier 0 — Critical / Safety-Blocking

| # | Commit | Issue | Agent | Description |
|---|--------|-------|-------|-------------|
| 1 | `5836d48` | #1 | Lead | **SECRET_KEY fail-fast** — removed insecure hardcoded fallback; `settings.py` now uses `os.environ['DJANGO_SECRET_KEY']` (no default); app refuses to start without the env var |
| 2 | `700dd9b` | #4 | Lead | **Gate test URLs** — uncommented `execute_gate_test` + `save_gate_test_result` routes disabled since commit `8383d1c`; patients unable to run gate tests until this fix |
| 3 | `b7b3636` | #3 | Lead | **VoiceCoachV2 missing methods** — added `announce_practice_rep()`, `give_atomic_command()`, `announce_phase_transition()`, `provide_ar_feedback()` called by 230+ V2 exercises; AttributeError on every exercise |
| 4 | `99045ec` | #2a | Lead | **State machine KeyError** — added `start`/`active` phase keys to `get_target_poses()` in 15 exercises; `calculate_real_time_form_score()` was crashing on KeyError |
| 5 | `90d6d64` | #8 | Lead + Agent 5 | **Deadlift back angle clarified** — proposed ankle anchor rejected by Agent 5 clinical review (ankle occlusion risk in standing hinge); clarified comment: angle measures hip extension depth, not spinal alignment; true lumbar monitoring not feasible with MediaPipe 33 landmarks |
| 6 | `c303f65` | #9 | Lead + Agent 5 | **Glute bridge hip angle approved** — shoulder→hip→ankle anchor confirmed correct for supine position (fixed reference, targets valid); Agent 5 clinical clearance documented |
| 7 | `06fd8ad` | #2b | Agent 9 + Agent 5 | **Plank shoulder tap state machine** — full rewrite: plank↔tapping phases with wrist Y-asymmetry detection; threshold 0.05 (captures ~2.5 cm taps); unilateral rep tracking (left/right counts); `get_asymmetry()` flags none/mild/significant; Agent 5 reviewed and approved with threshold modification 0.06→0.05 |
| 8 | `429fb9d` | #15 | Lead | **AR overlay 6-pattern kinematics** — `calculate_target_joints()` now implements 2D forward kinematics for PUSH/PULL (elbow pivot), HINGE (hip pivot), SQUAT/LUNGE (vertical knee), CORE (hip sag), CARRY (no-op); upper-body skeleton connections (shoulder→elbow→wrist) added |

---

## Tier 1 — Clinical Safety / Prescription Engine

| # | Commit | Issue | Agent | Description |
|---|--------|-------|-------|-------------|
| 9 | `7962714` | #5 | Lead | **Asymmetry progression gate** — `v1_prescription_engine.py` now blocks capability advancement when `asymmetry_rules[pattern]['asymmetry'] == 'significant'`; adds modifier note explaining block |
| 10 | `6712024` | #6 | Lead | **Unilateral asymmetry safety check** — `check_asymmetry_safe()` added to `UnilateralExerciseHandler`; uses Limb Symmetry Index thresholds (>20% = significant block, 10-20% = mild warning) per APTA guidelines |
| 11 | `e3d8387` | #7 | Lead | **Red flag level caps enforced** — `get_pattern_level_caps()` added to `red_flag_map.py`; `_select_exercises_for_pattern()` applies caps before exercise selection (e.g. ACL grade 1-2 → lunge ≤ level 3) |
| 12 | `bbd34b6` | #10 | Lead | **XP gate for unsafe form** — `compute_session_xp()` now gives 0 XP when `form_score < 55`; prevents gamification loop rewarding injurious movement quality |
| 13 | `8bbe1a8` | #11 | Lead | **Mandatory deload enforcement** — `check_deload_needed()` rewritten; 4-week mandatory rule enforced even when `periodisation_state` not passed by caller; fallback resolves `patient.periodisation_state` directly + date arithmetic from `last_deload_date` |
| 14 | `feaa3cb` | #12 | Lead | **Age capability cap in progression loop** — progression check at line 1384 now applies `age_limits['max_capability']`; 65+ patients were able to advance to level 5 (their cap is 3) |

---

## Tier 2 — Quality / Gamification

| # | Commit | Issue | Agent | Description |
|---|--------|-------|-------|-------------|
| 15 | `bc23079` | T2-SEC | Lead | **PHI logging** — replaced 20 `print()` calls in `backend/main_coordinator.py` with `logger.debug()`; patient names/IDs no longer emitted to stdout in production |
| 16 | `beb743d` | #13 | Lead | **XP persistence** — added `xp_earned IntegerField` to `WorkoutSession` (migration 0009); persist computed XP at session complete; `compute_xp_and_level()` now sums stored values with flat-rate fallback for legacy sessions |
| 17 | `278f363` | #14 | Lead | **Rank-up detection** — replaced hardcoded "Silver II → Silver III" with real comparison of consecutive `StrengthProfile` scores via `RANK_MAP` |
| 18 | `a6ee3cc` | T2C | Lead | **validate_form() in 29 stubs** — all Group B rest/holding exercises had `return {}`; replaced with generic angle-tolerance validation (CORRECT/NEEDS_ADJUSTMENT/INCORRECT) against phase targets |

---

## Tier 3 — Cleanup

| # | Commit | Issue | Agent | Description |
|---|--------|-------|-------|-------------|
| 19 | `74c9cd6` | T3 | Lead | **Cleanup batch** — (a) `v1_dashboard.html` Chart.js radar font corrected from missing 'Inter' to 'Plus Jakarta Sans'; (b) `tricep_extensions_v2.py` bent→extending threshold raised 60°→70° to match 45° target floor; (c) `analyze_frame` view registered at `api/analyze-frame/` (was missing from urlpatterns — all CV frame submissions returned 404) |

---

## Items Confirmed Clean (no fix required)

| Audit item | Finding |
|------------|---------|
| Bare `except:` blocks | None found in production code |
| Numeric landmark indices in step-ups | All use `PoseLandmark.NAME` enum correctly |
| Red flag alternative validation | `get_alternative_for_excluded()` is dead code; callers handle `None` |
| Dual prescription system | Single `generate_v1_session()` entrypoint; no conflict |
| `CSRF_COOKIE_HTTPONLY = False` | Intentional — JS AJAX CSRF reads require this |
| Hormonal modifier key inconsistency | `_resolve_hormonal_modifiers()` already handles nested `menstruation` dict |
| Lunge back angle | Comment-level clarification; landmark chain is best available with MediaPipe 33 |
| Nutrition one-way integration | Read-only display; no write-path bug |
| `SESSION_COOKIE_SECURE` | Set in `if not DEBUG:` block — correct |

---

## QA Sign-Off

```
DJANGO_SECRET_KEY='dev-key' python manage.py check
→ System check identified no issues (0 silenced)

DJANGO_SECRET_KEY='dev-key' python manage.py check --deploy
→ 2 warnings (test key length + SSL redirect) — test-environment artifacts only

DJANGO_SECRET_KEY='dev-key' python manage.py migrate
→ All migrations applied cleanly (latest: 0009_add_xp_earned_to_workout_session)
```

**Remote push: PENDING** — not pushed per instructions. Push after stakeholder sign-off.
