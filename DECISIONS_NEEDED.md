# DECISIONS NEEDED

Open items only; closed decisions are one-line stubs (full histories:
`docs/archive/DEEP_AUDIT_REPORT.md`, git history of this file).

## OPEN

### D3 — Pre-existing rows store internal IDs in absolute_stop_reason
`absolute_stop_reason` now stores human-readable labels; rows written
before that change store internal IDs (e.g. `acute_fracture`) and won't
render nicely on the stopped card. **Action:** if any production patients
have `absolute_stop=True` predating Run 1 at deploy time, run a one-off
ID→label data migration. Listed in DEPLOY_CHECKLIST.md.

### Clinical review — FOOTBALL_METHODS §13
Five open questions for the sports-physio review (scoring bands, Y-balance
94%, ovulation plyo block, Nordic density, novice deload ceiling).

### Physio-mentor sign-off — R4 cue table
The rewritten coaching cue phrasing (docs/REPORT_AND_COACHING.md, cue
table) awaits Pawan's mentor's sign-off.

## CLOSED (stubs)

- **D1** load-spike note: CLOSED — SKIPPED per Pawan (no pseudo-metric).
- **D2** therapist red-flag checklist: CLOSED-BY-T2 — red-flag clears raise
  a reviewable therapist Alert; structured intake stays optional future work.
- **D4** EXERCISE_TAGS gap: CLOSED — tags are legacy-path-only metadata
  (documented in exercise_tags.py); the V1 engine never consults them.
- **D5** three CV implementations: CLOSED — Python registry is the single
  source of truth → generated exercise_targets.json → client JS; the
  legacy server-side analyze_frame stack was removed in the 2026-06 health
  sweep (C1). See docs/CV_ARCHITECTURE.md.

## Decisions of record (Run 2 — flag if you disagree)

- **R2-A** Session lifetime: 7-day persistent cookies, browser-close expiry
  OFF (rationale in settings.py).
- **R2-B** Registration enumeration: kept the helpful "already registered"
  copy (rate-limited 3/10 min, now at onboarding_identity); the reset flow
  is enumeration-safe. SECURITY_AUDIT.md #7.
- **R2-C** Conservative camera set: camera tracking only after the filming
  protocol passes; everything else guided. Flip per-exercise in
  export_exercise_targets.py (see docs/ADDING_AN_EXERCISE.md).
