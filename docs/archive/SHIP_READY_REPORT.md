# VYAYAM — Run 2 Ship-Readiness Report (2026-06)

**Branch:** `ship-ready-2026-06` (off `deep-audit-2026-06` @ c2a5753) · spec: the Run-2 handoff prompt
**Verification at close:** `manage.py check` 0 issues · `check --deploy` clean (2 env-only warnings) · **251 Django tests green** · **8/8 node CV tests green** · fresh-DB migrate OK · DEBUG=False smoke all routes clean · export artifact freshness test-enforced

---

## Ship-blocker ledger — final verified state

| SB | Item | Final status |
|----|------|--------------|
| SB-1 | Plyo circular gate | **CLOSED** (verified: linear fail-closed cascade, models.py; gate tree documented FOOTBALL_METHODS §7) |
| SB-2 | Self-clearing red flags | **CLOSED** (verified test_da_c5; now ALSO raises a therapist Alert — T2) |
| SB-3 | Emergency screens | **CLOSED** (verified test_da_c6, 5 symptom-based options) |
| SB-4 | Nordic time-hold scoring | **CLOSED** — self-timed hold labelled as such; live page is guided/manual (no fake camera score); methods doc §5 |
| SB-5 | HSR weeks counter | **CLOSED** (verified: nullable anchor + is-None, mig 0015) |
| SB-6 | ACL-R pathway | **CLOSED** — no pathway exists; `acl_grade_1_2` red flag is a legitimate condition modifier, kept |
| SB-7 | HSR tempos | **CLOSED** (verified 6-0-6-0 in both phases) |
| SB-8 | RTS scaffolding | **CLOSED** (verified zero refs) |
| SB-9 | POGO labelled RSI | **CLOSED** — relabelled app reactivity count everywhere; un-measurable "<200 ms" instruction removed; test enforces no RSI claim |
| SB-10 | ACWR | **CLOSED** (verified repo-wide: docs/tests only) |
| SB-11 | Uniform LSI | **CLOSED** — per-test bands (hop 90 / cod 90 / ybalance 94) in `LSI_THRESHOLDS` with citations/limitation; coach + results surfaces updated |
| SB-12 | Asymmetry from score bands | **CLOSED** — raw `measured_value` no longer discarded; LSI on raw values with band-gap fallback, method labelled |
| SB-13 | 7-test normalisation | **CLOSED** — `V1_TEST_NORMALISATION` table (measure/rationale/evidence tag per test); sex-adjusted push bands now actually applied |
| SB-14 | Universal deload | **CLOSED** — training-age ceilings (novice 6 wk / trained 4 wk), feedback triggers unchanged |
| SB-15 | "BACK ROUNDED" false positive | **CLOSED in BOTH paths** — Python (Run 1 C3) + JS: scored `back` target renamed `hinge` (what it measures), measurement cues no longer claim rounding, artifact test forbids back/spine overrides |

**High/Medium findings:** partial reps counting **CLOSED** (W1-5: partials get their own counter, never count as reps; +250 ms debounce) · stretch holds **CLOSED** (pre-match fully dynamic, statics capped 30 s ACSM-style) · uncited multipliers **CLOSED** (every family annotated cited/pragmatic/contested; no uncited >20% load increase exists) · sleep traffic-light **CLOSED** (5–6 h yellow only with non-good energy) · marketing copy **CLOSED** (AI-powered/AI-guided removed from all user surfaces).

---

## W1 — Live CV parity (commits 79e99b2, e967a50, d55375e)

- **D5 resolved**: Python registry = source of truth → `export_exercise_targets` command + curated audit table → committed `exercise_targets.json` (288 entries: **112 camera / 176 manual**) → per-page `CV_CONFIG` via template tag. Freshness + integrity test-enforced.
- Mapping audit fixes: marching≠jump, wall_sit→SQUAT_HOLD, mountain climbers≠push-up, nordics manual, STRETCH fake-tracking fallback killed, step_up_with_knee_drive→STEP_UPS, cossack→SQUAT_SINGLE, + ~40 more (rationale in the command).
- **Honest manual mode**: guided card + hold timer, `form_score=NULL` + `rep_quality_source='manual'` end-to-end (mig 0020), completion-based XP, no fabricated 75s anywhere (incl. camera-failure fallback).
- Partial-rep rule + phase debounce; ghost only renders for audited camera exercises; Python depth targets override JS conservatively.
- `analyze_frame` route **removed** (W1-7); view fenced as reference.
- Pure CV math extracted to `cv_core.js` + node harness; docs: CV_ARCHITECTURE, EXERCISE_TEST_CHECKLIST (288 rows, generated), FILMING_PROTOCOL.

## W2 — Football & sports-physio methodology (469e725, d848319)

All 9 code items closed (see SB table) + **docs/FOOTBALL_METHODS.md**: 13-section study document, every claim tagged [cited]/[pragmatic]/[contested], honesty table (clinic vs VYAYAM), open questions for a real physio. MD-x microcycle sanity-checked against common practice (passes).

## W3 — User-POV pass (c33c612 + 2775755)

Built: **U1** password recovery (email token + therapist temp-password + forced change), **U2** resume banner, **U3** set undo + redo-previous, **U4** session history/detail (ownership-404), **U5** why-lines, **U7** profile/equipment edit (regenerates session), **U8** empty states (partial), **U9** offline page. U6 already existed. Full findings: docs/UX_FINDINGS.md (11 patient + 10 therapist findings with dispositions).

## W4 — Therapist-POV pass (3aed29a)

Built: **T1** triage-ordered dashboard + alerts stat, **T2** Alert model/inbox/mark-reviewed (pain + red-flag events now reviewable, not buried in notes), **T3** copy-last-week, **T7** visit notes; + fixed a 500 for not-yet-activated patients. Spec'd (UX_FINDINGS): T4 templates, T5 prescription PDF, T6 ring polish, T8 discharge.

## W5 — Security (59a50e0) — SECURITY_AUDIT.md

**IDOR: 35+ routes audited, zero holes** (cross-access test matrix). Fixed: Django 4.2→**4.2.30** (High), builder innerHTML escaping (Med), session contradiction → 7-day persistent (Med), 2 missing rate limits (Med), Referrer-Policy + CSP-Report-Only (Med). Accepted+documented: registration enumeration copy, guessable-but-gated IDs. pip-audit: 0 vulns in pinned production deps. Open: cross-session invalidation after password change (Run-1 known limitation).

## W6 — Deploy (00f4b41) — DEPLOY_CHECKLIST.md

`/healthz/` (DB-touching), full env-var table (incl. new SMTP set), gunicorn command + logging rationale, backup note. Final gate all green (header of this report).

---

## What Pawan must do by hand

1. **Film the camera exercises** per docs/FILMING_PROTOCOL.md, most-prescribed first (docs/EXERCISE_TEST_CHECKLIST.md, fill the last column).
2. **SMTP account** + the 4 email env vars (password reset emails are silent no-ops without it).
3. Set the production env vars (DEPLOY_CHECKLIST.md table) and strong admin credentials.
4. Read **docs/FOOTBALL_METHODS.md** end-to-end; take §13's five questions to a sports physio.
5. D3 only if pre-Run-1 production rows exist with `absolute_stop=True`.
