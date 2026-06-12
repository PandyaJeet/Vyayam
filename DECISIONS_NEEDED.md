# DECISIONS NEEDED — Deep Audit 2026-06

STOP-and-log items per the working agreement: each has a recommendation;
none block other work.

## D1 (from C4) — Optional plain-language load-spike note
ACWR is fully removed, no replacement metric (per Appendix B). The spec
allowed an *optional* plain note when this week's planned working sets
exceed last week's by >30%. Not built: a per-session generator doesn't
know "this week's planned" volume reliably, and any proxy (this session
vs last week's per-session average) risks false alarms — a pseudo-metric
by another name.
**Recommendation:** skip for V1. If wanted later, compute on completed
sessions only (trailing 7 days vs prior 7 days) and show the note on the
dashboard, not in the prescription.

## D2 (from C6) — Therapist-side emergency screening checklist
The spec says to wire the new emergency stop options into the
therapist-side health profile "if one exists".
`TherapistPatientHealthProfile` exists but is free-text clinical intake
(diagnosis, affected side, `other_conditions` text) — there is no
structured red-flag checklist to extend. Adding one would be a new
feature inside a working B2B2C flow.
**Recommendation:** keep the therapist side free-text (therapists are
qualified to screen); optionally show a read-only banner of the
patient's self-reported stop flags + RedFlagEvent history on the
therapist patient-detail page in a future iteration.

## D3 (from C5/C6) — Pre-existing rows store internal IDs in absolute_stop_reason
`absolute_stop_reason` now stores human-readable labels. Rows written
before this change store internal IDs (e.g. `acute_fracture`); the
stopped-card "Flagged:" line and checkbox pre-check won't render those
nicely. No data migration was written (SQLite dev DB; pilot DB assumed
fresh).
**Recommendation:** if any production patients have absolute_stop=True
at deploy time, run a one-off data migration mapping IDs → labels.

## D4 (from Phase 3B) — EXERCISE_TAGS 90-entry gap: documented, not filled
The tag layer (EXERCISE_TAGS → get_exercise_dosage/get_patient_modifier)
is consumed ONLY by the legacy gate-test dosage path (utils.py,
views.py). The V1 engine has its own `_calculate_dosage` driven by
EXERCISE_METADATA categories + the new HOLD_EXERCISE_IDS set, and its
red-flag/equipment logic uses red_flag_map + equipment_routing, not
tags. Filling 90 hand-authored tag entries would create a second,
unconsumed source of truth that can drift.
**Recommendation:** leave the tag layer scoped to the 68-exercise
legacy set (now documented in exercise_tags.py docstring); if the V1
engine ever needs per-exercise dosage tags, derive them from
EXERCISE_METADATA instead.

## D5 (from Phase 2/3 finding) — analyze_frame scores every exercise as a squat
The legacy web CV endpoint (views.py analyze_frame) computes form
scores and rep detection from KNEE angles only, for every exercise —
push-ups, rows and planks are scored as squats. The 264 per-exercise
modules are wired only to the desktop headless runner; the V1
patient flow uses a third, client-side JS implementation in
v1_exercise_execute.html.
**Recommendation:** route analyze_frame through the registered
exercise module for the given exercise_id (registry now instantiates
cleanly — DA-H3); until then, treat the legacy exercise_execute flow's
form scores for non-squat exercises as invalid.

---
# RUN 2 UPDATE (2026-06, ship-ready-2026-06)

## Dispositions of D1–D5
- **D1 (load-spike note): CLOSED — SKIPPED** per Pawan's confirmation.
- **D2 (therapist red-flag checklist): CLOSED-BY-T2** — red-flag clears now
  raise a reviewable Alert in the therapist inbox (the original concern was
  visibility; a structured intake checklist remains optional future work).
- **D3 (stop-reason backfill): STILL OPEN** — run the ID→label data
  migration ONLY if production rows with absolute_stop=True predate Run 1.
  Listed in DEPLOY_CHECKLIST.md.
- **D4 (tag layer): CLOSED** — tags are legacy-path metadata, documented in
  exercise_tags.py; the V1 engine never consults them. No entries authored.
- **D5 (three CV implementations): CLOSED** — Python registry is the single
  source of truth; the live JS consumes the generated exercise_targets.json;
  analyze_frame route removed. See docs/CV_ARCHITECTURE.md.

## New decisions made this run (flag if you disagree)
- **R2-A: Session lifetime** — 7-day persistent cookies, browser-close
  expiry OFF (was contradictory). Rationale in settings.py.
- **R2-B: Registration enumeration** — kept the helpful "already
  registered" copy (rate-limited 3/10 min); the reset flow is
  enumeration-safe. Documented in SECURITY_AUDIT.md #7.
- **R2-C: Conservative camera set** — 112 of 288 exercises camera-tracked;
  everything unverifiable runs in guided mode. Flip per-exercise in
  export_exercise_targets.py only after passing the filming protocol.

## New open questions (clinical — for the sports-physio review)
- The five questions in docs/FOOTBALL_METHODS.md §13 (scoring bands,
  Y-balance 94%, ovulation plyo block, Nordic density, novice deload
  ceiling).
