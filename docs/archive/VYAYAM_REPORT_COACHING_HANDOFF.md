# VYAYAM — HANDOFF: DAILY SESSION REPORT + HUMAN-LIKE FORM COACHING
**Phases R1–R5. For Claude Code (Fable). Prepared by chat-Claude after design sign-off with Pawan. No pitch deadline — depth over speed, but the standing rules still apply in full.**

---

## 0. WHAT THIS BUILDS (one paragraph each)

**The report:** the moment a managed patient finishes (or is pain-stopped out of) the day's protocol, the server assembles ONE detailed session report — the same report the therapist sees in a Reports tab and the patient sees in their history. It reads like a therapist watched the whole session: narrative summary, safety events first, per-exercise per-set detail (reps, form %, depth/ROM, tempo adherence, rest taken and extended, cues fired and whether they were corrected, pain pinned to the exact rep on camera exercises), fatigue/warm-in trends, left-right asymmetry, perception-vs-performance notes, messages sent during the session, and comparisons to the last sessions. Stored as an immutable JSON snapshot; rendered from that snapshot forever.

**The coaching:** live form feedback that behaves like a human therapist standing in front of the patient — one cue at a time, instructive external-focus phrasing, praise at a human ratio, cues that fade instead of nag, silent calibration reps before any judgment, "I can't see you clearly" instead of false reds, softer coaching when fatigue shows, and a spoken tempo loop that paces every rep. **Locked rule: tempo NEVER colors form. Form color judges the quality of the phase the patient is actually in. Amber-first; red is reserved for safety-relevant faults only.**

## Locked design decisions (Pawan-confirmed — do not re-open)
1. One report, both audiences see the identical document. Language: professional but layman-readable throughout (patient eyes on everything).
2. Generated synchronously on session completion AND on pain-pause (an aborted session is the report a therapist most needs). No background workers.
3. Immutable: `report_json` snapshot at generation; views render from JSON only.
4. **PainEvent is the source of truth for pain in the report — never SessionLogItem.pain** (silent below-threshold reports must appear).
5. Rep-level precision on camera exercises; set-level on guided — and every exercise block is labeled `camera-tracked` or `guided (self-reported)`. Never fabricate rep-level data for guided work.
6. Rest/pause buttons get built in R1 (RestEvent model already exists, unused) — the report depends on them.
7. Per-patient range calibration on the first 2 reps; scoring is relative to their range with generous tolerance.
8. Footer on every report: auto-generated from camera estimates + self-reports; single-camera accuracy limits apply; not a clinical assessment; the therapist retains clinical judgment.

## Standing rules (verbatim from previous cycles, all seven, plus)
Verify every find-string against live code before editing · quoted + `|escapejs` for anything entering inline JS · `manage.py check` + full suite (268+) green after every phase · one phase per run · end each phase with exact manual browser steps · clinical wording flagged for the physio mentor · **detection boundary, spelled out for this cycle:** you MAY build the cue-arbitration layer, phrasing, praise, coloring thresholds, calibration wrapper, per-rep event capture, and tempo speech — you may NOT modify landmark math, angle computation, the rep state machine's phase-detection internals, or MediaPipe setup. Every phase here touches `v1_exercise_execute.html` → **squat re-test after every phase.**

Sequencing: **R1 → R2 → R3 → R4 → R5.** R1–R3 deliver the report end-to-end; R4 is the coaching humanization; R5 verifies everything together.

---

## PHASE R1 — CAPTURE LAYER (the data the report needs but doesn't exist yet)

Investigate first: read how camera set completion currently posts (the LIBRARY_MODE save path), where the guided screen's Done-per-set lives, what the rep state machine already exposes per rep in `cv_core.js` / the inline JS (phase timestamps? bottom angle? cue events?). Write findings before editing.

**R1a — Per-rep records (camera exercises only).** Client-side, accumulate per rep during the set: `{rep_n, phase_ms: {ecc, hold, con}, bottom_angle, form_pct, cues: [{cue_id, corrected: bool}]}`. `corrected` = the offending metric returned in-band within the next rep after the cue fired (compute client-side; you have the frames). Batch-POST the array at set end alongside the existing result payload — a few KB, negligible. Server: new model `ExerciseSetLog` (link/session FK, exercise_id, set_number, reps_json, started_at, ended_at, mode='camera'|'guided') — guided sets create a row too (self-reported reps count, no reps_json). Persist with the same `_safe_int`/clamp discipline; malformed rep arrays are dropped with a logged warning, never 500.

**R1b — Rest + pause, finally.** On both screens: the rest timer gains a **+30s** button (tap again = +30 more) and a **Pause session** button (pause anywhere, resume where left). Every extension → `RestEvent` row (exercise, set, seconds_added). Pauses → `RestEvent` with kind='pause' + duration. These render into the report as "extended rest +60s after set 2 of Step-ups" / "paused 3m 40s during Clamshell."

**R1c — Timestamps.** Stamp exercise start (page entry) and end (last set saved / skip / pain-exit) — simplest home: fields on `ExerciseSetLog` roll up, plus session start/end on the existing SessionLog. Total time and per-exercise time derive from these; no estimates in the report.

**R1d — Rep-pinned pain (camera).** The pain modal on camera exercises already sends `set_number`; add `rep_number` from the live rep counter at the moment the modal OPENED (not submit — the patient stops mid-rep to report). Server: add nullable `rep_number` to PainEvent (migration) + accept/clamp it in `therapist_session_report_pain`. Guided screen sends null — the report will say "during set 3" there, honestly.

**R1e — Small capture flags.** `demo_viewed` (Show demo pressed — boolean per exercise on ExerciseSetLog roll-up), tempo adherence inputs (per-rep phase_ms vs TEMPO_PARTS — computation happens in R2, capture here), and the existing per-exercise easy/tough + pain feedback confirmed flowing (it does — just verify the field names you'll read in R2).

Tests: model round-trips, clamps, malformed payloads → 400/dropped-not-500, RestEvent rows from both screens, rep-pinned PainEvent. Manual: do a real 2-exercise session on a phone, extend rest once, pause once, report pain mid-rep; verify rows in admin. **Squat re-test.**

---

## PHASE R2 — REPORT ENGINE (pure, deterministic, tested to death)

**Model:** `SessionReport(link FK, session_log FK unique, patient, report_date, status='complete'|'ended_early_pain'|'partial', report_json, created_at)` + index (patient, report_date). One per session-log.

**Builder:** new module `strength_app/report_builder.py` — a pure function `build_report(session_log) -> dict`. No request objects, no rendering. Unit-test it with fabricated inputs covering every branch. Sections of the dict:

1. `header`: patient name, date (IST), protocol week/day if known, session number, total duration mm:ss, completion % (exercises fully done / prescribed).
2. `safety`: list of 8+/pause events, threshold-crossing skips, early-end reason. **Empty list = section omitted in render; non-empty = rendered FIRST.**
3. `narrative`: a composed 3–6 sentence paragraph. Deterministic sentence templates selected by rules — no free generation, no invention. It must cover, when data supports it: overall completion + duration; the standout positive; the standout concern; fatigue or warm-in pattern; pain in one plain sentence; a closing trend vs last session. Example target register: *"Anika completed all 5 exercises in 31 minutes. Form was strongest on glute bridges (91%) and she held tempo well through the first half. She tired visibly during step-ups — form fell from 84% to 68% across the three sets and she added rest twice. She reported an aching 4/10 at rep 6 of set 2 of squats, inside her usual range, and finished the session. Squat depth matched Monday's session."* Every sentence traceable to a data rule; write the rule table in the module docstring.
4. `exercises[]` per prescribed item, in order: name, mode label (`camera-tracked` / `guided (self-reported)`), prescribed vs achieved (sets×reps, tempo, load), duration, per-set table (reps, avg form %, depth best/avg where camera, tempo adherence %, rest taken + extensions), `cues`: aggregated {cue text, times fired, corrected count} + a one-line responsiveness note ("corrected within a rep each time" / "persisted after cueing — flagged for review"), `pain[]` from **PainEvent** pinned as "severity/10, type, at rep R of set S" (rep omitted when null), `feedback` (easy/ok/tough), `skipped` + reason/tier, `demo_viewed`.
5. `patterns`: fatigue signature (form or rep-speed decline ≥15% first→last set on ≥1 exercise, or ≥2 late rest extensions), warm-in (inverse), L/R asymmetry on unilateral items (reps + form per side, side-specific pain), perception-vs-performance (rated easy + form fell ≥20%), tempo tendency (e.g., "rushes the lowering phase: avg 1.8s vs 3s prescribed"). Each pattern = {finding, evidence string}. Neutral, observational wording only — both audiences read this.
6. `trends`: vs the previous up-to-3 SessionReports: ROM delta per repeated camera exercise, avg form delta, pain recurrence ("3rd consecutive session with knee ache during step-ups, severity stable 3–4"), completion streak.
7. `messages`: patient→therapist messages timestamped inside the session window (body + time).
8. `review_points`: max 4 auto-observations distilled from safety/patterns/trends — phrased as neutral flags ("Right-side step-up form under cueing", "Recurring knee ache on step-ups"), NEVER advice, NEVER diagnosis (R3 rule: therapist owns decisions; patient reads this too).
9. `footer`: the fixed integrity disclaimer from locked decision 8.

**Triggers:** call the builder + persist inside (a) session completion, (b) the pain-pause path in `therapist_session_report_pain`, (c) `therapist_session_finished`. Idempotent — regenerating for the same session_log updates nothing (report exists → skip). Wrap in try/except that logs and NEVER blocks the patient's completion flow — a report failure must not break finishing a session. (P2, note only: stale abandoned sessions get a `partial` report when the today-page detects them — spec in report, don't build.)

**Tempo adherence math** (lives here, from R1 phase_ms): a rep phase is "on tempo" within ±40% of prescribed or ±0.7s, whichever is looser; adherence % = on-tempo phases / scored phases; direction of miss = the dominant off phase. Zero-tempo prescriptions → section omitted.

Tests: golden-file test for a full fabricated session (assert the whole dict), every pattern rule on/off, PainEvent-not-SessionLogItem assertion, idempotency, pain-pause trigger, builder never raises on missing/partial data (defensive `.get` everywhere — a session with no camera data still reports).

---

## PHASE R3 — REPORT UI (both sides, one template)

One shared include `_session_report.html` rendering `report_json` — used by BOTH views. HTML context only; all values escaped; nothing report-derived enters inline JS.
- **Therapist:** a "Reports" tab on patient detail — reverse-chronological list (date, status chip, completion %, safety badge if any) → detail view. Alert/message deep-links may link to the report.
- **Patient:** their session history entries (U4) link to the same rendered report.
- Design: clean clinical document — safety banner (red, only when present) → narrative → exercise blocks with per-set tables → patterns/trends → review points → footer. Print-friendly CSS (@media print) so a therapist can Cmd+P today; a reportlab PDF button is P2, spec only.
- Ownership: therapist route via `get_linked_patient_or_404`; patient route via session identity + own-report check (404 otherwise). Add both cross-access tests to the IDOR matrix.
- Hostile-data render test: report containing notes/messages with `<script>`, quotes, em-dashes renders escaped; run the page through the G0 inline-JS harness walk.

Manual: full session → open the report as patient and as therapist — identical content; check the pain line reads "aching 4/10 at rep 6 of set 2"; print preview looks sane. **Squat re-test not needed for R3 unless you touched the execute template (you shouldn't).**

---

## PHASE R4 — HUMAN-LIKE COACHING (the therapist in the room)

All within the allowed layer (arbitration/phrasing/coloring/speech). Investigate current cue firing + coloring first; map every existing cue string.

**R4a — Cue arbitration.** One active cue at a time. Priority: SAFETY (knee-valgus class, listed explicitly per exercise) > primary movement fault > refinement. A lower-priority cue never interrupts; a safety cue always does, immediately. Refinement cues never fire during the final 2 reps of a set (let them finish); safety always can. Minimum 1 full rep between spoken cues.

**R4b — Phrasing rewrite.** Every user-facing cue becomes a short (≤8 spoken words) instruction toward the fix, external-focus where possible: "push the floor away", "knees toward the camera", "chest proud", "slow and smooth" — never fault-labels ("wrong", "bad form", "rounding"). Keep an internal `cue_id` stable for R1's tracking. **The full before→after cue table goes in the phase report flagged for the physio mentor's sign-off before merge.**

**R4c — Praise + fading.** Cue corrected (R1a's `corrected`) → one specific reinforcement ("better — knees are tracking now"), then silence on that cue. Same cue fired 3× uncorrected in a set → stop repeating it; say once "let's slow down — quality over count", log `cue_resistant` on the set (feeds the report's responsiveness note), stay quiet on that cue for the set. Independent praise: max ONE per set, only after a genuinely good window (form above threshold for ≥3 consecutive reps or a post-cue correction), drawn from a varied pool of ~8 lines so it never feels canned.

**R4d — Calibration + smart range.** First 2 reps of the first set: no colors, no cues (except safety), one line: "Let's see your natural movement first." Record their top/bottom range; thereafter score depth/ROM relative to THEIR calibrated range with generous tolerance, not fixed textbook angles. Calibrated range also feeds the report's ROM numbers.

**R4e — Confidence gating.** Landmark confidence low / body partially out of frame for >1s: freeze coloring entirely (neutral skeleton), one gentle line ("I can't see you clearly — step back a little"), resume when confidence returns. NEVER color or cue on low-confidence frames.

**R4f — Amber-first coloring.** Red exclusively for the per-exercise SAFETY list; everything else ambers with its cue. Tempo deviation NEVER changes color (locked rule) — the tempo chip softens ("a bit quick — try 3 seconds down"), spoken tempo adjust max once per set, deviation logged to adherence %.

**R4g — Fatigue-aware tone.** When the R2 fatigue signature conditions trip live (form down ≥15% vs set 1, or 2+ rest extensions), coaching drops to safety cues + encouragement only for the remainder ("last set — steady and controlled").

**R4h — Tempo speech loop polish.** Per rep, matching Pawan's spec exactly: "Slowly down — 3… 2… 1" → (hold ≥2s: "hold — 2… 1"; hold 1s: just "hold"; hold 0: nothing) → "up — 2… 1". Counts spoken only for phases ≥2s; loop every rep; suppressed during any active cue or praise line (arbitration owns the voice channel — one speaker, like one human).

Tests: arbitration unit tests (priority, suppression windows, 3-strike fading, one-praise-per-set), calibration state machine, confidence-gate transitions — as node tests on the extracted JS where feasible, else documented manual matrix. Manual: a full deliberately-sloppy session on camera — confirm it feels like coaching, not judgment: one voice, one cue at a time, praise when earned, silence when hopeless, no reds except the safety fault you fake. **Squat re-test, thoroughly — this phase lives inside the showpiece.**

---

## PHASE R5 — INTEGRATION VERIFICATION + DOCS

- Full suite green; G0 harness green across the new pages; IDOR matrix extended; hostile-data report render.
- One real end-to-end on a device: sloppy 3-exercise session with a rest extension, a pause, a mid-rep pain 4, a cue you obey and one you ignore → open the report → **every one of those events appears, correctly pinned, in human-readable prose.** That sentence is the acceptance test for the whole cycle.
- Update PITCH_SMOKE.md with 4 new steps (rest+pause, mid-rep pain, report opens both sides, coaching behavior spot-check).
- `docs/REPORT_AND_COACHING.md`: the narrative rule table, pattern thresholds, cue table (post-mentor-signoff), arbitration rules, and the honest-limits section (what guided mode can't know, single-camera limits).
- Final report to Pawan: counts, the cue before→after table for his mentor, migrations list, and anything deferred.

---

## PARKED (spec only, do not build): PDF export button (reportlab) · stale-session partial reports · per-set RPE · therapist strict-mode tolerance toggle wiring into calibration · weekly roll-up report.
