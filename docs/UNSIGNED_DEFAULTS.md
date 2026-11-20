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
