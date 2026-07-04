# VYAYAM — Deep Audit Report (2026-06)

**Branch:** `deep-audit-2026-06` (off `111b480`) · **37 commits** · all work test-verified
**Verification at close:** `manage.py check` 0 issues · `makemigrations --check` clean · **201 tests green** · scripted end-to-end smoke passed (emergency stop → audited clear → generate → sharp-pain skip → XP-0 unsafe session → real report numbers)

Spec: `VYAYAM_DEEP_AUDIT_PROMPT.md`. Open clinical decisions: `DECISIONS_NEEDED.md` (D1–D5).

---

## Phase 1 — Verified critical fixes (C1–C15)

| ID | Where | Severity | Status / commit |
|---|---|---|---|
| C1 | `v1_gamification.compute_session_xp` — `max(XP_PER_SESSION, …)` floor defeated the form-safety gate | S2 | fixed `06ef7c2` (0 XP when no exercise passes; `MAX_SESSION_XP` ceiling) |
| C2 | `v1_safety_logic.check_deload_needed` — wrong related_name `periodisation_state` swallowed by bare except; calendar check missing from primary branch | S2 | fixed `2bf870d` (max(counter, calendar) in both branches) |
| C3 | 22 modules scored back/hip-flexion angles against impossible targets (full squat bottom `avg_back: 155` vs real ~50–90°) | S2 | fixed `7e60850` — 67 target lines removed; **band targets** `(lo, hi)` introduced for moving phases in FormCalculator/AR overlay/validate_form. Kept only where plausible: planks, push_ups, clock_reaches |
| C4 | ACWR computed + surfaced (`_compute_acwr`, P31 block, help_text, generator hints) | R2 violation | removed `edf0e18`; **bonus S1**: `meta` UnboundLocalError crashed `generate_v1_session` for EVERY active football athlete (view swallowed it) — fixed same commit |
| C5 | Red flags self-clearable, no audit trail | S2 | fixed `5fa3440` — `RedFlagEvent` model (mig 0013), confirmation-gated clear, coach/therapist link notes, read-only admin |
| C6 | Missing emergency screens (cauda equina / DVT / cardiac / malignancy / progressive neuro) | S2 | fixed `be7dc94` — 5 symptom-based options (R4 copy), urgent-care escalation; `absolute_stop_reason` now stores labels not internal IDs |
| C7 | `generate_report` fabricated 75% adherence / 20 prescribed on every call (signature TypeError → fallback) | S2 | fixed `28ad8aa` — real DB aggregates; zero-session → "insufficient data"; `view_report` hint str→int |
| C8 | Legacy bridge crashed on `meta` dict in prescriptions | S1 | fixed `40c4b4a`; test_group3 flipped to assert the fix |
| C9 | "Clinical Reasoning" etc. in athlete tier (R1) | R1 violation | fixed `781d5ef` — Coaching Rationale / Athlete wording; field name unchanged |
| C10 | Nutrition light red with no targets set | S3 | fixed `c0fc315` — `'none'` + `needs_setup`; dashboard setup state |
| C11 | Deload weeks drift from calendar | S2 | fixed `3f3ad83` — `last_deload_date` anchored at state creation; rule "max(counter, calendar)" documented |
| C12 | Synthetic green/yellow/red rep counts presented as CV data | S2 | fixed `87d0b9e` — `rep_quality_source` ('cv'/'derived', mig 0014) set at all 3 creation sites; legacy CV flow marked 'cv' |
| C13 | Bare int()/float() on client JSON → 500s, no clamps | S1 | fixed `93d8f13` — shared `validation.py` (safe_int/safe_float + canonical ranges); 4 endpoints clamped; coach date parse |
| C14 | PFP excluded `step_ups` AND replaced 'step'→`step_ups`; `lateral_Hops` dupes | S2 | fixed `e34191e` — replacement `wall_sit`; `test_red_flag_map_integrity` covers ALL flags |
| C15 | Two hormonal-modifier key conventions; nested menstruation dict leaked | S2 | fixed `07b437f` — `get_hormonal_modifiers(phase, patient)` single source, engine delegates; per-phase shape test |

All C-items carry greppable tests `test_da_c*` in `strength_app/tests/test_deep_audit.py`.

## Phase 2 — Exercise system (264 modules) + harness

**Harness (permanent infrastructure):** `tests/clinical_audit/generators/trajectory_generator.py` synthesizes each module's ideal trajectory from its own `get_target_poses()` and drives the real scoring/rep code. Django tests: `test_da_h2_*` (zero-crash invariant + green-set ratchet ≥165), `test_da_h3_*` (registry).

**H2 progression:** first run → **119/265 modules crashed**, 47 green. Final → **0 crashes**, **168/223 scored modules ≥85 mean**. Full per-module table: `strength_app/tests/clinical_audit/reports/H2_RESULTS.md`.

Systemic fixes (each affects tens of modules):
| Fix | Modules affected | Commit |
|---|---|---|
| `announce_rep` signature mismatch — TypeError on the FIRST COUNTED REP of every exercise | 234 | `defb91e` |
| `FormStatus.WARNING/GOOD/INFO` didn't exist; `TempoDetector.get_phase_duration` missing; `voice.say` missing; runner passed scalar to dict-modules | 63+13+40+30 | `48efb63` |
| State-machine phases missing from scored targets (push-ups crashed at 'bottom', pull-ups on FIRST FRAME at 'start', rows at 'top') | 28 | `a744b3d` |
| `JointFeedback` convention shim (38 kwarg + 29 positional-joint callers; the latter silently corrupted AR colors) | 67 | `a744b3d` |
| Modules discarding the scalar angle (`else {}` / hardcoded 175) — machines frozen forever, no rep ever counted | 78+27 | `a744b3d`, pull-up batch |
| Initial phase never handled by machine (pull-up family init 'start', machine keys 'hang') | 20 | `ebd2e47` |
| Moving-phase targets → bands (the C3 mechanism system-wide; diamond_push_up rejected 5/5 perfect practice reps) | 46 (+11 both-phase) | `ad9a848`+bands commit |
| H1: FormCalculator curve parameterized by exercise tolerance (≤15 was silently ignored) | all | `ad9a848` |
| H3: registry — all IDs instantiate, `lateral_Hops`→`lateral_hops` canonical | — | `b8f209a` |

**Target-angle changes:** every changed number is in the commit diffs of `7e60850`/`a744b3d`/bands commit with one-line reasoning in adjacent comments; the band conversion log (46 modules, exact old→new values) is printed in the `DA-EX-bands` commit message context and `/tmp/band_changes.json` at run time. Reasoning pattern throughout: *moving phases sweep their range — score bands, enforce ROM via the state machine; never score a synthetic proxy.*

**Remaining tail (documented, not defects-at-rest):** 55 modules at mean 67–84 (boundary frames at late machine transitions; pause_squat is a real-time-dependent machine the harness can't pace), alternating-leg/hold machines that can't count synthetic reps, 21 `no_targets` + 21 `no_scoring` hold/carry modules pending checklist item 6 UI work. The ratchet test prevents regressions while these are worked.

## Phase 3 — Data integrity

- **8 prescribable chain IDs had a BLANK execute page** → full content authored (deadlift_dumbbell, dragon_flag_progression, dumbbell_rowing, hollow_body_rock, nordic_curl_partner, single_arm_pull_up_prog, single_arm_push_up_prog, single_arm_single_leg_plank).
- **12 legacy gate-test IDs** had no content and no alias → authored.
- **45 equipment mappings missing** → a bodyweight-only patient could be prescribed dumbbell work; all mapped.
- **Tags (90 missing):** consumed ONLY by the legacy dosage path — documented in `exercise_tags.py`, decision D4 (don't create a second source of truth).
- **Warm-ups now respect red-flag exclusions** (`jumping_jacks_light` is `jumping_jacks` by another name) — engine `_build_warmup` filter + test.
- **HOLD_EXERCISE_IDS**: wall sits/planks/carries now dosed as timed holds in every phase (previously reps outside the AA override).
- Coverage locked by `test_da_p3_*`.

## Phase 4 — Engine & flow audit (12 file groups)

S1/S2 fixed (commits `03d21fc`, `a63356b`):
- Football extras (HSR/plyo) **bypassed red-flag filtering** → now filtered, drops surfaced.
- Empty pattern selection silently dropped → tries `get_alternative_for_excluded` (Phase-6 item 6 wired), surfaces skips.
- `compute_traffic_light` ignored numeric `pain_severity` → ≥7 red, 4–6 yellow.
- HSR anchor: default 0 + falsy check **re-anchored every session at week 0** — the ≥4-week advance gate could never fire → nullable + `is None` (mig 0015 converts sentinels).
- Onboarding back-nav created duplicate baseline StrengthProfiles → `update_or_create`.
- `_pattern_to_category`: 7 of 14 patterns fell to 'lower_body' → full mapping + new category choices (mig 0017).
- Legacy gate IDs normalised (`partial_squat`→`partial_squats` etc.) so chain lookups match.
- Backend: 3 division-by-zero guards; report_generator enum/string; `balance`→BALANCE (was LOWER_BODY).
- Age validator 13→18 (Appendix B; mig 0016).
- Clamps: onboarding (test_index was an unbounded IndexError, score, age, minutes, sessions/week, cycle 20–45, sitting 0–24), football test save, coach override (known IDs, sets 1–10, reps 1–100, inline error).
- `analyze_frame` 5 MB payload cap; `session_analyzers` 30-min idle eviction.
- `save-exercise-results` route restored — **the legacy execute page was 404ing every save**.
- Ladder advance atomic; gate simulation seeded per patient.
- Model validators + composite indexes (mig 0018); `check_data_integrity` management command; route smoke test (immediately caught `/v1/profile/` 500 on stale staticfiles manifest).

**H4 disposition (`v1_session_complete` + engine):** engine's 17 broad excepts = graceful-fallback S4 (left, documented). Session-complete: periodisation update narrowed to `DoesNotExist` + ERROR log (clinical); football update ERROR log (clinical for athletes); data collection / milestones / nutrition card / next-preview → WARNING logs (enrichment). Zero silent swallows remain on safety paths.

## Phase 5 — Physio-grade features

**Built (P1):** F1 per-exercise pain persisted (mig 0019) + progress-page list + coach detail expansion + traffic-light override (sharp/7+ during ANY exercise ⇒ red even if check-in says mild) · F2 server-side sharp-pain response (same-pattern auto-skip, banner, pain-stop page with R4 copy, professional flag note) · F3 pain follow-through (2 consecutive same-location ⇒ regress one level + freeze advancement; 3 ⇒ pause + physio-referral copy + note; pain-free resets) · F4 soreness-vs-pain education · F5 deload banner **on the live dashboard** (v1_home_gamified — v1_dashboard.html is a dead template).
**Built (P2):** F8 reassessment nudge (>6-week profile or stalled family) · F10 real session duration persisted · F6 partial ("START LEFT — weaker side first" badge; `check_asymmetry_safe` remains desktop-runner-only) · F7 verified already present (rest timer + tempo in execute template).
**Spec-only (F9, F11):** skip-with-reason UI (fields `skipped`/`skip_reason` already in the model and persisted — only the one-tap picker in the 5.5k-line execute template remains); patient-exportable PDF; therapist alert strip; per-set RPE.

## Phase 6 — Hardening

Canonical form bands (GREEN≥80 / YELLOW≥55) in `v1_constants`, imported by session summary + XP gate; FormCalculator's stricter per-frame AR bands documented as intentionally separate · `change_password` rate-limited + `cycle_key()` · XFF trusted only behind `DJANGO_TRUSTED_PROXY=1` · football/quick-log endpoints rate-limited · **GROUP6's "fixes applied" were never shipped** — manifest colors, base_gamified PWA tags/SW, therapist responsive viewport all actually fixed now · README "Current Architecture" section.

## What I did NOT do, and why

1. **`analyze_frame` still scores every exercise as a squat** (D5). The live patient path is client-side JS; rerouting the legacy endpoint through the 264 modules is a feature build, not a fix. Logged with a concrete recommendation.
2. **90 tag entries not authored** (D4) — the V1 engine doesn't read them; filling them creates an unconsumed second source of truth.
3. **The H2 tail** (55 sub-85 modules, synthetic-rep counting for alternating/timed machines) — time-boxed; ratchet test holds the line; per-module data in H2_RESULTS.md.
4. **Therapist-side red-flag checklist** (D2) — no structured screen exists to extend; free-text intake is clinically defensible.
5. **Cross-session invalidation after password change** — needs a server-side token registry; noted as known limitation.
6. **V2 Bayesian staging, return-to-sport pathways, UI redesign** — out of scope per the working agreement.
7. **test_group5.py** — referenced by GROUP5_AUDIT but never committed to the repo; its described coverage now exists in `test_deep_audit.py` (C1/C2/C10/C15 etc.) rather than recreating the file from prose.
