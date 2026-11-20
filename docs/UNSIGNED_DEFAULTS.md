# Unsigned defaults (Mind Lab, step 2)

Every value here is a conservative placeholder for a blank in the G3 workbook
("Pawan Sets" sheet). None is signed off. All live in
`strength_app/mind_lab/config.py`. Conservative = more likely to hold, notify
or slow progression.

| Constant | Default | File:line | Workbook blank | Used by |
|---|---|---|---|---|
| `CHECKIN_FULL_MIN_SCORE` | 12 | `strength_app/mind_lab/config.py:11` | Check-In 4 day-label thresholds (Full) | Check-In 4 |
| `CHECKIN_LIGHT_MIN_SCORE` | 9 | `strength_app/mind_lab/config.py:13` | Check-In 4 day-label thresholds (Light; below = Recovery) | Check-In 4 |
| `YOUTH_AGE_CUTOFF` | 18 | `strength_app/mind_lab/config.py:20` | Youth age cut-off | Support-line wording only |
| `RESET_BREATH_SESSIONS_TO_LEVEL_UP` | 5 | `strength_app/mind_lab/config.py:24` | Reset Breath sessions before moving up | Nothing yet (Reset Breath not built) |
| `ROUTINE_BUILDER_RECALLS_TO_LEVEL_UP` | 5 | `strength_app/mind_lab/config.py:28` | Routine Builder correct recalls before moving up | Nothing yet |
| `ROUTINE_BUILDER_ERRORS_TO_LEVEL_DOWN` | 3 | `strength_app/mind_lab/config.py:30` | Routine Builder errors before moving down | Nothing yet |
| `STILL_SWITCH_ACCURACY_UP_PCT` | 90 | `strength_app/mind_lab/config.py:34` | Still-Switch accuracy % to go up | Nothing yet |
| `STILL_SWITCH_ACCURACY_DOWN_PCT` | 70 | `strength_app/mind_lab/config.py:36` | Still-Switch accuracy % to go down | Nothing yet |
| `STILL_SWITCH_STOP_EARLY_DROP_PCT` | 15 | `strength_app/mind_lab/config.py:38` | Still-Switch in-session drop % to stop early | Nothing yet |

Score for Check-In 4 is `energy + focus + (6 - stress)`, range 3 to 15 (`strength_app/mind_lab/checkin.py`, `checkin_score`). That formula is also a guess, not from the workbook.

## Other unsigned items (no constant)

- **Stress scale direction.** The workbook says "stress or energy at 1 shows the support line" but does not say which end of stress is bad. `show_support_line` (`strength_app/mind_lab/checkin.py:83`) shows the line for stress 1 or 5.
- **Guardian consent for under-18.** `[Pawan sets]`, unbuilt. No consent gate was added.
- **Pillar numbers per game.** `[Pawan sets]`, no number needed in code.
- **Visitor questions.** The workbook says 2 questions for visitors but not which. Built: sleep and energy (`strength_app/v1_mind_lab_visitor_views.py`).
- **Stale pain light.** The pain light is the latest `SessionFeedback.traffic_light` with no age limit (`pain_light_for`, `strength_app/mind_lab/day_mode.py`).
- **S3 hold.** No hold source exists. Hook: `s3_hold_active` at `strength_app/mind_lab/day_mode.py:31`, always False.
- **Athlete-facing wording** (`PLAN_TEXT`, `LABEL_TEXT`, form text in `mind_lab_checkin*.html`, `mind_lab_visitor.html`) needs physio mentor review before release.
- **Coach day-label opt-in.** Not built. No coach screen shows check-in data.

## Pass Window (step 3)

Blanks from the G2 Pass Window spec (`[Pawan sets]`). All in `strength_app/mind_lab/config.py`. None signed off. Conservative = more Time Assist, slower promotion, quicker demotion.

| Constant | Default | File:line | Spec blank |
|---|---|---|---|
| `PASS_WINDOW_BASE_CLOSING_MS` | 4000 | `strength_app/mind_lab/config.py:43` | Base closing time (closing = base / factor) |
| `PASS_WINDOW_SESSION_MAX_S` | 90 | `strength_app/mind_lab/config.py:45` | Session timer (spec max 90 s) |
| `PASS_WINDOW_TRIALS` | 8 | `strength_app/mind_lab/config.py:47` | Trial count |
| `PASS_WINDOW_BLOCK_SIZE` | 4 | `strength_app/mind_lab/config.py:49` | Block size |
| `PASS_WINDOW_ACCURACY_UP_PCT` | 90 | `strength_app/mind_lab/config.py:51` | Accuracy % to raise |
| `PASS_WINDOW_ACCURACY_DOWN_PCT` | 70 | `strength_app/mind_lab/config.py:53` | Accuracy % below which a block counts toward a drop |
| `PASS_WINDOW_BLOCKS_TO_RAISE` | 2 | `strength_app/mind_lab/config.py:55` | Blocks in a row to raise |
| `PASS_WINDOW_TIMEOUTS_TO_LOWER` | 2 | `strength_app/mind_lab/config.py:57` | Timeouts that drop a level |
| `PASS_WINDOW_L5_DECISION_LIMIT_MS` | 4000 | `strength_app/mind_lab/config.py:60` | Level 5 decision time limit (equals the base closing time, so no extra pressure yet) |
| `PASS_WINDOW_ACCEPTABLE_COUNTS_AS_CORRECT` | False | `strength_app/mind_lab/config.py:63` | Not a spec blank. My choice: an "acceptable" pass does not count toward the level rule |

Fixed by the spec, not blank: `PASS_WINDOW_FREEZE_MS` (2000, line 65), `PASS_WINDOW_VISITOR_TRIALS` (3, line 67), `PASS_WINDOW_VISITOR_LEVEL` (2, line 68).

Other unsigned Pass Window items (no constant):

- **All 8 scenarios are `UNREVIEWED`** (`strength_app/mind_lab/pass_window_scenarios.json`). A coach or physio must review every `correct` and `acceptable` before use. They are labelled "demo scenarios" in the UI.
- **Pillar mapping `[Pawan maps]`.** Not guessed. No pillar appears in code.
- **Youth guardian consent `[Pawan checks]`.** Unbuilt. No consent gate was added.
- **Intermediate Time Assist factors** 0.5, 0.7, 0.85 are the spec author's proposal (`LEVEL_FACTORS` in `strength_app/mind_lab/pass_window.py`).
- **Thin scenario pool.** Level 3 and Level 5 have one scenario each, Levels 1, 2 and 4 have two. A session repeats them. The visitor run (3 trials at Level 2) shows PD-004, PD-005, PD-004.
- **"2 blocks" for a drop** is read as the last 2 complete blocks.
- **Shortened day** holds the level (`PLAN_TEXT['shortened']` says "Your level holds").
- **Manual Assist High/Medium/Low/Off picker, last-5 trend and coach error-pattern view** from the spec are not built.
- **Athlete-facing wording** in `pass_window.js` and the Pass Window templates needs physio mentor review.

## Return-to-play Tier 1 (step 4)

`[Clinician sets]` values from SPINE_SPEC. All in `strength_app/rtp/config.py`. None signed off. Conservative = more likely to hold.

| Constant | Default | File:line | Spec blank |
|---|---|---|---|
| `HOLD_ON_SWELLING` | True | `strength_app/rtp/config.py:9` | "swelling today = yes" holds an athlete with an active episode |
| `HOLD_ON_GIVING_WAY` | True | `strength_app/rtp/config.py:11` | "giving way = yes" holds an athlete with an active episode |
| `ATHLETE_HOLD_TEXT` | "Your training is paused. Please check with your therapist." | `strength_app/rtp/config.py:15` | Not a spec blank. Athlete-facing wording, needs physio mentor review |

Other unsigned items (no constant):

- **W1 content is missing.** `W1_output.md` was never delivered. `RehabPathway` has two empty rows (`hamstring`, `ankle`), no `RehabStage` rows, no stage names, no criteria. Nothing clinical was written.
- **The hold rule is built but not wired.** `feedback_triggers_hold` in `strength_app/rtp/availability.py` reads `swelling_today`, `giving_way`, `locking_or_catching` with `getattr`. Those fields do not exist yet (S8). Nothing calls `apply_feedback_hold` from a view, so no athlete is held automatically. Red light holds every athlete once wired; that is the spec, confirm before wiring.
- **Holds are silent.** S10 (notify) is not built, so a hold writes an AuditLog row only.
- **No therapist screen.** Status changes by a therapist go through the service functions only (shell). Admin pages for status and audit are read-only on purpose.
- **Restricted = remove or keep only.** On `restricted`, a coach override with any action other than `remove` or `keep` is rejected. "Reduce load" is not measured by sets or reps.
- **Coach screens treat every user as a coach**, even the assigned therapist. A therapist acts through the service, not those screens.
- **Rehab stage blocks coach overrides but not the athlete's session.** Only medical hold stops the session.


## Return-to-play Tier 2 (step 4)

`[Clinician sets]` values from SPINE_SPEC, comparator parameters. All in `strength_app/rtp/config.py`. None signed off.

| Constant | Default | File:line | Spec blank |
|---|---|---|---|
| `MAX_GAP_DAYS` | 14 | `strength_app/rtp/config.py:21` | Two sessions further apart than this (calendar days between session dates) give `no_comparison`. Larger is more conservative. |
| `SEVERITY_DELTA` | 1 | `strength_app/rtp/config.py:23` | `pain_severity` up by this much is "worse". Smaller is more conservative. |
| `TIGHTNESS_DELTA` | 1 | `strength_app/rtp/config.py:25` | `tightness_0_10` up by this much is "worse". Smaller is more conservative. |
| `LOCATION_CHANGE_COUNTS` | False | `strength_app/rtp/config.py:28` | Off per SPINE_SPEC. The conservative setting would be True. |

Other unsigned items (no constant):

- **The hold rule is now wired.** `v1_post_session_feedback` calls `apply_feedback_hold` after saving the feedback (`strength_app/v1_session_views.py`). With `RTP_ENABLED` on, **a red traffic light holds any athlete, with or without an episode** (SPINE_SPEC: "Hold if traffic light red"). Swelling and giving way hold only an athlete with an active episode. Confirm the red-light-holds-everyone reading.
- **Athlete-facing wording** of the five injury questions (`strength_app/templates/strength_app/v1_post_session_feedback.html`, block `rtpInjuryQuestions`) needs physio mentor review. It says "Any swelling today?", "Did it give way?", "Any locking or catching?", "Tightness today (0 to 10)", "Where is the tightness?".
- **A location change counts as "worse"** when `LOCATION_CHANGE_COUNTS` is on. SPINE_SPEC gives no direction. Blank on either side skips the field.
- **`pain_severity` is compared as stored.** It is not nullable and the form posts a default of 3 even when pain is "none", so the severity part of the comparator is noisy until the form stops posting it for "none". Not changed (outside this step).
- **Locking:** yes in the newer record is "worse" even if the older record is yes or null. A "no" with a null older record is skipped.
- **A negative gap** (older record dated after the newer) and a **missing session date** give `no_comparison`.
- **Clearance (S5):** approving is refused while the athlete is on hold. Any hold (`place_hold`, from any role) invalidates the approved clearance with reason `red_flag`. A new decision supersedes the old approval. No gate reads a clearance, so it cannot loosen one.
- **Checkpoint pass (S7):** `pass_gate` is refused while the athlete is on hold or any measure is still pending. With no measures a therapist may still pass it. Criteria stay blank (W1 missing). Passing never changes the stage number.
- **No therapist screen for S5 or S7.** Decisions, checkpoints and measures go through `strength_app/rtp/clearance.py` and `checkpoints.py` only (shell). S13 is not built.
- **Holds are still silent** (S10 not built). A hold writes an AuditLog row only. S11 (auto-hold on "worse") is not built: "worse" feeds the coach's "injury signal" only.
- **Coach view** shows on `coach_athlete_detail` only, and only when the athlete has an episode or an availability row. The coach squad list is unchanged.
- **Minors** need a legal check before the injury questions go to under-18 athletes (SPINE_SPEC). No age gate was added.
