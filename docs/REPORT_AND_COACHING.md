# VYAYAM — Session Report & Human-Like Coaching (R1–R5)

Reference for the daily session report and the coaching arbitration layer.
Code of record: `strength_app/report_builder.py` (report),
`strength_app/static/strength_app/js/coach_core.js` (coaching),
`strength_app/static/strength_app/js/voice_core.js` (voice),
capture endpoints in `strength_app/v1_therapist_session_views.py`.

## Architecture in one paragraph

The camera/guided screens capture per-set data (R1: `ExerciseSetLog` with a
per-rep array on camera work, `RestEvent` for +30s/skips/pauses, rep-pinned
`PainEvent`s, server-stamped exercise start times). On session completion or
pain-pause, a pure builder (`build_report`) assembles ONE immutable JSON
snapshot (`SessionReport`, R2) which both the therapist and the patient
render from the same include forever (R3). Live coaching (R4) is a pure
arbiter fed by a bridge in the execute template: it decides every spoken
line and every judgment color; the detection/scoring pipeline is untouched.

## Locked design decisions (Pawan-confirmed)

1. One report, identical for both audiences; layman-readable throughout.
2. Generated synchronously at completion AND pain-pause; no workers.
3. Immutable snapshot; views render from JSON only; regeneration skips.
4. **PainEvent is the only pain source** — never `SessionLogItem.pain`.
5. Rep-level detail only on camera work; guided is labeled self-reported
   and never carries fabricated rep data.
6. Rest/pause events feed the report (built in R1).
7. Per-patient range calibration on the first 2 reps; generous tolerance.
8. Fixed integrity footer on every report.
9. **Tempo NEVER colors form. Red is reserved for safety faults only.**

## Narrative rule table (report_builder docstring is authoritative)

| Sentence | Fires when | Template |
|---|---|---|
| S1 opener | always | by status: "completed all N in M minutes" / "stopped early after a high pain report" / "ended without a finish" |
| S2 positive | ≥1 camera exercise with form data | "Form was strongest on {ex} ({pct}%)." |
| S3 concern | fatigue pattern, else any camera avg <70% | pattern evidence / "…worth a look." |
| S4 warm-in | warm-in pattern and no S3 | pattern evidence |
| S5 pain | ≥1 PainEvent | worst event, rep/set-pinned, outcome in plain words |
| S6 close | trends exist | completion streak, else form delta |

## Pattern thresholds

| Pattern | Rule |
|---|---|
| fatigue | last-set form ≤ 85% of first-set (per exercise, ≥2 camera sets), OR avg rep duration slowed ≥15% first→last, OR ≥2 rest extensions in the protocol's second half |
| warm_in | last-set form ≥ 115% of first-set |
| perception_vs_performance | rated "easy" while form fell ≥20% first→last |
| tempo_tendency | same phase+direction missed on ≥60% of tempo-scored reps |
| L/R asymmetry | **DORMANT** — capture has no per-side split yet; activates when side-tagged data exists (never fabricated) |

Tempo adherence: a phase is on-tempo within ±40% of prescribed or ±0.7 s,
whichever is looser; adherence % = on-tempo phases / scored phases;
zero-tempo prescriptions score nothing and the section is omitted.

Trends (vs ≤3 prior snapshots): form delta (≥1%), ROM delta (best bottom
angle, ≥5°), pain recurrence (consecutive sessions, same exercise),
completion streak (≥2 at 100%).

## Coaching arbitration rules (coach_core.js, node-tested)

- **One active cue at a time.** Priority safety > primary > refinement. A
  spoken line owns the voice channel for 2.5 s; lower/equal priority is
  suppressed during it; **safety interrupts immediately, always**.
- Minimum **1 full rep between spoken cues** (safety exempt).
- **Refinement cues never fire in the final 2 reps** of a set.
- **3-strike fading:** the same cue uncorrected 3× in a set → one
  "Let's slow down — quality over count", then silence on that cue for the
  set; the set is flagged `cue_resistant` (the report renders it as
  "persisted after cueing — flagged for review").
- **Praise:** a corrected cue earns one specific reinforcement, then
  silence; independent praise needs ≥3 consecutive reps ≥75% form, max one
  per set, from a rotating 8-line pool.
- **Calibration (first 2 reps, first set):** no judgment colors, no cues
  except safety, "Let's see your natural movement first." Depth targets
  then shift to the patient's natural bottom −5°, never deeper than the
  textbook demand, floor-clamped at textbook+40°. **Assessments are never
  calibrated** (scores stay comparable).
- **Confidence gate:** key landmarks low-visibility >1 s (or no landmarks)
  → neutral skeleton, all cueing suspended, one "I can't see you clearly —
  step back a little" per episode.
- **Amber-first:** red skeleton/score colors appear only while a safety
  cue is live; every other deviation is amber.
- **Fatigue mode** (form ≤85% of set 1, or ≥2 rest extensions): safety
  cues + encouragement only; announced once: "Last set — steady and
  controlled."
- **Tempo speech:** "Slowly down — 3… 2… 1" → hold ≥2 s "Hold — 2… 1" /
  1 s bare "Hold" / 0 s nothing → "Up — 2… 1". Counts only for phases
  ≥2 s; tempo speech yields whenever a cue or praise owns the channel.

## Cue table (R4b) — **pending physio-mentor sign-off**

| cue_id | Spoken text | Priority |
|---|---|---|
| knee_valgus | Knees toward the camera | safety |
| knee_valgus_landing | Land with your knees wide | safety |
| soft_landing | Land soft and quiet | safety |
| orientation_supine / prone / sidelying | Lie on your back / face down / on your side | safety |
| hips_even | Hips level, like a tray | primary |
| stay_hinged | Push your hips back | primary |
| foot_forward | Front foot further forward | primary |
| chest_up | Chest proud | primary |
| hips_level | Keep your hips level | primary |
| hips_stacked | Stack your hips straight up | primary |
| hold_position | Back into position | primary |
| stand_tall | Grow tall on the step | refinement |
| feet_together | Glue your feet together | refinement |

Fixed lines: fade "Let's slow down — quality over count" · calibration
"Let's see your natural movement first" · confidence "I can't see you
clearly — step back a little" · fatigue "Last set — steady and controlled"
· tempo adjust "A bit quick — slow the lowering" / "A touch slow — keep it
moving". A node test enforces ≤8 words and bans fault-label vocabulary.
Not rewritten (out of scope, documented): SETUP instruction strings and the
dormant per-exercise `cues:{}` data (their speaker, `cueAlignment`, is
never called).

## Honest limits (rendered in every report footer)

- **Guided exercises cannot know** rep counts (self-reported), form, depth,
  tempo, or the rep a pain report belongs to — the report labels these
  "guided (self-reported)" and pins pain to the set only.
- **Single-camera pose estimation cannot see** spinal flexion/rounding,
  axial rotation, load/effort, or anything out of frame; depth/ROM numbers
  are estimates from landmark angles, not clinical measurements.
- `corrected` on a cue is operationalized as "the cue was not re-attempted
  during the following rep" — a sound proxy, not a per-metric measurement
  (per-metric predicates are the documented refinement path).
- A session paused at high pain and later resumed to completion keeps its
  `ended_early_pain` snapshot (immutability is locked; documented edge).

## P2 (spec only, not built)

PDF export button (reportlab) · stale-session partial reports ·
per-set RPE · therapist strict-mode tolerance toggle · weekly roll-up.
