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


## Return-to-play Tier 3 (step 4)

All unsigned. Hold and notify only: nothing here changes load or a stage number.

| Constant / item | Default | File:line | Note |
|---|---|---|---|
| `HOLD_ON_WORSE` | True | `strength_app/rtp/config.py:15` | A "worse" comparator verdict holds an athlete with an active episode. Only for athletes with an episode, because `pain_severity` is noisy for the rest. Conservative side is True. |
| `HOLD_BODIES`, `HOLD_BODY_DEFAULT` | text | `strength_app/rtp/notify.py:20` | Therapist-facing notice wording. No raw values. Mentor review. |

- **S10:** a hold now writes one in-app notice per therapist with authority over the athlete (assigned therapist and supervising therapists). A coach gets none. A notice failure never undoes a hold. This removes the "holds are silent" caveat above.
- **S11:** `feedback_is_worse` in `strength_app/rtp/availability.py` compares the newest two feedback records right after the feedback is saved.
- **S13 inbox** at `/coach/inbox/` (404 when `RTP_ENABLED` is off) lists unread notices, due checkpoints with pending-result counts, and held athletes ("waiting for your decision"). It has no actions except Mark read. Lifting a hold, clearing and passing a gate still go through the services (shell).
- **S14:** coach squad line (`rtp-squad-line`), Inbox button, and athlete Today status line (`rtpAthleteStatus`). The athlete line shows the hold text when held, else "Status: X" and "Restrictions: ..." as the therapist stored them.
- **Wording to review (mentor):** the hold notices above; squad line "Medical hold · Injury signal: yes · Checkpoint due"; inbox headings "Notices", "Checkpoints due", "Waiting for your decision", "On hold", "N result(s) to confirm"; athlete "Status: ..." / "Restrictions: ...".
- **Holds are no longer silent** once `RTP_ENABLED` is on: S10 and S11 are built.

## Exhibition pages (`EXHIBITION_MODE`) — wording for Pawan's mentor

Every new athlete-facing string on `/exhibition/`, `/exhibition/squat/` and `/exhibition/bicep-curl/`. None is signed off. The strings live in `strength_app/v1_exhibition_views.py` (`SQUAT_TEXT`, `CURL_TEXT`) and `strength_app/templates/strength_app/exhibition_index.html`. Captions show the existing camera coach lines word for word; they add no new text.

| Where | String |
|---|---|
| Index, tagline | VYAYAM: a training plan that progresses on its own |
| Index, link | Try the squat coach |
| Squat, Start button | Start |
| Squat, placement hint (follows the SQUAT `cameraPosition` text in `v1_exercise_execute.html`) | Prop your phone at waist height, facing you. Step back so your whole body is on screen. |
| Squat, spoken unlock line (also shown as a caption) | Ready. |
| Squat, camera failure title | Camera not available |
| Squat, camera failure body | We could not start the camera. Watch the demo below. |
| Squat, retry button | Try again |
| Squat, demo line 1 (spoken and captioned on play 1; the camera page's own line) | Watch me first. I will show you the movement. |
| Squat, demo line 2 (spoken and captioned on play 2) | One more time. |
| Squat, demo replay button (failure panel only; the existing camera-page label) | Show demo |
| Squat, header | VYAYAM |
| Index, link (item 4) | Try the bicep curl coach |
| Bicep curl, placement hint (follows the CURL `cameraPosition` text in `coach_dark.js`) | Prop your phone at waist height, to your side. Stand side-on and step back so your whole body is on screen. |
| Bicep curl, camera failure body (no clip on this page) | We could not start the camera. |
| Bicep curl, other strings | Same as squat: Start · Ready. · Camera not available · Try again · VYAYAM (header). No demo lines: the demo is the camera page's own Show demo sequence, word for word. |
| Page titles (<title>) | `VYAYAM` (index) · `Full Squats — VYAYAM` (squat; the camera page's own title) · `Mind Games Prototype` (games; Pawan's own file, served unchanged) · `VYAYAM: How a plan changes` (progression) · `Bicep Curls — VYAYAM` (bicep curl; the camera page's own title) |

Other defaults: idle reset 60 s (`IDLE_SECONDS`), camera-frame timeout 10 s (`NO_FRAME_SECONDS`). The squat page runs `full_squats` as 1 set of 5 reps with tempo 3-1-2-0 (nothing is saved, so these only set the on-screen targets). The bicep curl page runs `bicep_curls`, 1 set of 5, tempo 2-1-2-0 (the registry tempo).

### `/exhibition/games/` (iPad)

Strings live in `strength_app/v1_exhibition_views.py` (`GAMES_TEXT`), shown by `exhibition_games.html` and `exhibition_games.js`. None is signed off. Pass Window keeps its own existing in-game text ("Demo scenario", "Demo scenarios", "Best pass.", and so on, unchanged in `pass_window.js`). The games are described as demo games, not a test of reaction time, ability or readiness.

| Where | String |
|---|---|
| Index, link | Play the demo games |
| Games, title | Demo games |
| Games, subtitle | Tap a game to start. |
| Pass Window, choice | Pass Window / Pick the best pass. About 60 seconds. |
| Pass Window, header | Pass Window · Demo scenarios |
| Go / No-Go, choice | Go / No-Go Pass / Tap teammates. Leave opponents. 45 seconds. |
| Go / No-Go, rules | Tap the blue circles. They are teammates. Do not tap the orange triangles. They are opponents. It gets a little faster when you get 3 right in a row. |
| Go / No-Go, legend | Teammate: tap · Opponent: do not tap |
| Go / No-Go, play bar | Blue circle: tap. Orange triangle: do not tap. |
| Go / No-Go, buttons and states | Start · Get ready · Round over · Play again · Choose a game |
| Go / No-Go, score table | This round · Your previous round · Accuracy · Mean response time · No earlier round yet · No taps counted · - |
| Go / No-Go, score note | Compared only with your own previous round on this page. |
| Every games screen | Demo games. Not a test of reaction time, ability or readiness. Nothing is saved. |
| QR box and caption | Scan to open this page, or type: · QR code for this page (the box stays hidden until the image file loads) |
| Pass Window, key under the pitch | Circle: you. Squares: teammates. Triangles: defenders. |
| Page title and heading | VYAYAM demo games · VYAYAM |
| Units | N s (clock) · N ms (response time) |
| Pass Window Done screen | The game's own sentence "Compare only with your own earlier sessions at the same level." is cut by the page; the rest of the game's text stays |

Defaults: Go / No-Go round 45 s; stimulus time starts at 1200 ms (ceiling), drops 100 ms after every 3 correct in a row, floor 600 ms (at most 1.67 screen changes a second, limit 3); taps under 150 ms are left out of the mean response time; Pass Window round: no new scenario starts after 50 s (a scenario is at most 8 s plus a 2 s reveal, so the round ends by 60 s); level 2 scenarios repeat. Idle reset 60 s.

### `/exhibition/progression/` (laptop)

Strings live in `strength_app/v1_exhibition_progression.py` (`TEXT`). None is signed off. The page runs the real engine twice per request on a demo history, inside a database transaction that is rolled back, so nothing is stored. The history is labelled "Illustrative demo data" and the two plans are labelled as computed live by the engine. The page shows nothing from the visitor.

**For the mentor:**
- The persona is a demo athlete who "returned to training". The page says nothing about why they stopped. Any fracture or injury context for the stall (spoken, not on the page) needs your wording first.
- The persona text says "Training state set for this demo". It means the phase, week count and date of the last lighter week are set by hand so the rules do not call a deload (the week count is the latest week in the history table, 6, and 2 for the earlier run). The demo athlete's session length is 90 minutes and training age 18 months, values the onboarding screens can send. The engine would otherwise call one after about 4 weeks of loading.
- The hop result (shown against the benchmark of 90 percent) is shown only. The plan uses the lunge result. The page says so.
- The extra-set bands are the engine's own: 85 and above none, 70 to 84 mild, 55 to 69 moderate, under 55 significant. Moderate adds 1 set on the weaker side. Significant adds 2 and blocks progression of that pattern.
- Pain column: shows the pain events logged (none in the demo data). Nothing is claimed about the cause of any change.

| Key in `TEXT` | String |
|---|---|
| title | How a plan changes |
| persona | Demo athlete, 24, returned to training. Trained, not new to lifting. One leg is weaker (the left), the same leg in both tests. Training state set for this demo: the phase, the week count and the date of the last lighter week are set by hand so the rules do not call a deload. |
| history_label | Illustrative demo data |
| hero_head | A training plan that progresses on its own. |
| hero_sub | Same athlete, 4 weeks apart. New numbers in, new plan out. |
| hero_balance | Leg balance |
| hero_extra | Extra sets, weaker leg |
| hero_level | Lunge level |
| hero_level_note | next session |
| hero_cue | How the plan decided |
| history_h | Last 6 weeks |
| week_cols | Week · Sessions · Sets · Note |
| light_note | Lighter week |
| days_h | Last 7 days |
| day_cols | Day · Exercises · Rest · Pain |
| pain_none | No pain logged |
| pain_some | Pain logged |
| sym_h | Symmetry tests (weaker side as % of stronger side) |
| sym_cols | Test · 4 weeks ago · Now · Benchmark |
| lunge | Lunge (used by the engine) |
| hop | Hop distance (shown here only) |
| hop_note | The hop result is not used by the plan. The lunge result is. |
| bands | Bands used by the plan: 85 and above none, 70 to 84 mild, 55 to 69 moderate, under 55 significant. |
| proto_h | Two runs of the same rules on the demo history |
| proto_label | Computed live by the engine on this request. Not a replay of the earlier plan. |
| run_a | 4 weeks ago |
| run_b | Now |
| diff_h | What changed |
| diff_cols | Exercise · Sets · Reps · Level · Weaker-side sets · Why |
| no_ex | Not in this run |
| same_side | same |
| status_other | The engine returned this status instead of a plan: |
| footer | Demo data and demo plans. Nothing is saved. The plans follow the same rules for every user. |
| back | Back |
| why_sym | Symmetry band {rule}: {extra} extra set(s) on the weaker side |
| why_blocked | Progression blocked while the band is significant |
| why_adv | Ready to progress: level {level} saved for the next session |
| why_deload | Deload |
| why_none | No rule changed this row |

Link text on `/exhibition/`: See how a plan changes. Page title: VYAYAM: How a plan changes. Week labels: "Week N", "Week 6 (latest)". Generated labels: "4 weeks ago: ..." and "Now: ..." prefixes in the Why column. Exercise names are the engine's own names.
