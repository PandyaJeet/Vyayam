# VYAYAM — MASTER TEST DAY (on-device walk)

The consolidated device test for everything shipped through the pitch-polish
(G0–F), security, and report/coaching (R1–R5) cycles. **The R4 coaching layer
is frozen until this passes.** Run on a real phone/laptop camera, console
open where possible. Tick every box; anything that fails gets a note with
what you saw. Budget ~90 minutes.

Credentials (after seeding): therapist `dr_shah / simple` at
`/therapist/login/` · patient `9000000001 / patient` (Anika) at `/login/`.

---

## Part A — Environment prep (10 min)

- [ ] `git pull` → branch `ship-ready-2026-06`, clean tree
- [ ] `python manage.py migrate` → "No migrations to apply"
- [ ] `python manage.py collectstatic --noinput` → exit 0 (manifest storage
      — camera pages 500 without this)
- [ ] `python manage.py test` → 312+ OK ·
      `node --test strength_app/tests/js/*.test.mjs` → 25+ pass
- [ ] `python manage.py seed_therapist_demo` (demo DB only, never prod)
- [ ] Fresh server start (`python manage.py runserver` or the deploy URL) —
      the G0 dead-buttons incident was a stale server; always restart
- [ ] Phone and laptop both reach the server over HTTPS or localhost
      (camera requires a secure context)

## Part B — PITCH_SMOKE walk (30 min)

- [ ] Run `PITCH_SMOKE.md` steps **1–23** in order, ticking there.
      Sections: therapist edit+publish (1–3) · full patient session, every
      button (4–14) · therapist message+alert (15–16) · squat showpiece
      (17–18) · self-serve stop parity (19) · report+coaching cycle (20–23).
- [ ] Extra G1 tier check while in step 10–11: severity **4** → green
      "within your usual range"; **6** → skip + chat message, NO alert;
      **8** → pause + chat ⚠ + one inbox alert. Repeat 8 on the same
      exercise within 10 min → chat message but NO duplicate alert;
      mark reviewed → next 8 alerts again.
- [ ] Phase D check at step 6: after Start Camera + framing, you land
      STRAIGHT in ("Ready. Step into the outline…"). **Show demo** works
      both before camera start (placeholder button) and mid-exercise
      (status-card button), and hands back to work.
- [ ] Phase E check at step 7: tempo chip colors — blue lowering, amber
      hold, green up; clamshell (`—` tempo) shows NO tempo card, no chip,
      no crash.
- [ ] Phase F check: the coach voice sounds natural on this device
      (Chrome/Android = Google voice; Safari = Samantha/Ava). Toggle the
      speaker icon off → silence; on → resumes.

## Part C — The deliberately-sloppy coaching session (R4, 20 min)

On a camera exercise (squat or glute bridge), one continuous set sequence:

- [ ] **Calibration**: first thing after "now you try" you hear "Let's see
      your natural movement first"; 2 reps with NEUTRAL skeleton (no
      green/amber/red), no cues; colors come alive on rep 3, scored to
      YOUR depth (a shallow mover should be able to reach green)
- [ ] **Safety cue + red**: let knees cave once → ONE "Knees toward the
      camera", skeleton may show red ONLY now
- [ ] **Correction praise**: fix it → next rep "Better — knees are
      tracking now", then silence on that cue
- [ ] **3-strike fade**: deliberately ignore a cue for 3 reps → one
      "Let's slow down — quality over count", then that cue stays silent
      for the set
- [ ] **One praise per set**: 3 clean reps → exactly one praise line;
      different wording next set
- [ ] **Confidence gate**: step half out of frame ~2 s → grey skeleton +
      "I can't see you clearly — step back a little" (once); no cues, no
      reds until you're back
- [ ] **Tempo loop (3-1-1 or similar)**: "Slowly down — 3… 2… 1 · Hold ·
      Up" every rep; counting PAUSES while a cue/praise speaks; resumes
      next rep; tempo deviation NEVER changes any color; at most one
      "a bit quick" adjust line per set
- [ ] **Fatigue tone**: extend rest +30s twice → next set opens "Last set —
      steady and controlled"; only safety cues after that
- [ ] **One voice throughout**: never two lines talking over each other
- [ ] **Assessment unchanged**: run one camera assessment — NO calibration
      line, NO adjusted targets, scores as before

## Part D — Capture rows in /admin (10 min)

As dr_shah at `/admin/` after the Part B/C sessions:

- [ ] `Therapist_app → Exercise set logs`: one row per set; camera rows
      have `reps_json` (per-rep form %, phase ms, bottom angle, cues with
      corrected flags); guided rows have count only, empty reps; the
      exercise you demoed has `demo_viewed=True`
- [ ] `Strength_app → Rest events`: your +30s taps (context between_sets),
      the skipped rest (`cut_short=True`), the pause (context `pause`,
      duration right ±5 s), all tied to the session log
- [ ] `Strength_app → Pain events`: severity/type/threshold/outcome rows;
      the camera-exercise report has BOTH `set_number` and `rep_number`;
      the guided one has rep_number empty
- [ ] `Therapist_app → Session reports`: one per finished session,
      statuses correct (`complete` / `ended early — pain`), no duplicates
      after revisiting the finished page

## Part E — The report, both sides + print (10 min)

- [ ] Patient: finished page → "View today's session report"; Progress →
      Session reports card → same report
- [ ] The pain line reads exactly like "aching 4/10 at rep 6 of set 2 —
      noted, session continued"
- [ ] Exercise header shows BOTH clocks: "N:NN elapsed · N:NN working"
- [ ] Your obeyed cue: "corrected within a rep each time"; the ignored
      one: "persisted after cueing — flagged for review" (+ in For review)
- [ ] Rest column: "+30s extended" on the right set, "paused Ns", "cut
      short" where you skipped
- [ ] Guided exercise block says "guided (self-reported)" with NO form/
      depth/tempo numbers (dashes)
- [ ] Therapist: patient → Reports tab → Session reports list (status
      chips, completion %, safety badge on the pain-stopped one) → Open →
      IDENTICAL document
- [ ] Safety-stopped session's report: red banner ABOVE the narrative
- [ ] Cmd+P print preview: nav/buttons gone, clean clinical document
- [ ] Footer disclaimer present on every report

## Part F — Final squat + console pass (10 min)

- [ ] Full squat set start→finish: framing → straight in → calibration →
      reps count on real movement → form % moves with depth → ghost
      tracks → voice coaches → Set done → rest → finish
- [ ] Browser console: ZERO red errors across the entire session
      (screenshot anything red with the URL visible)
- [ ] `python manage.py test` once more after the device day — still green
- [ ] Sign here: date + device + browser + "PASS" or the failure list

**On full PASS: the camera/coaching freeze lifts.** File any failure as a
bug with console text + the exact step number from this document.

## Part G — New-exercise smoke (run once per exercise added)

Per `docs/ADDING_AN_EXERCISE.md` step 10 — after adding any exercise:

- [ ] `python manage.py export_exercise_targets --check` → "fresh"
      (camera adds only) and full suite + node green
- [ ] Therapist: builder shows it → add with sets/reps/note → Publish
- [ ] Patient: today list shows it with the note → open it
- [ ] GUIDED: description renders, Set-done taps post ExerciseSetLog rows
      (mode guided), rest/+30s/pause work
- [ ] CAMERA: Start Camera → framing → straight in → reps count on real
      movement → form % responds → per-rep rows in reps_json → tempo chip
      if prescribed → zero console errors
- [ ] Report: finish the session → the new exercise's block renders with
      the right mode label and numbers
- [ ] Squat re-test (any camera-table change warrants the showpiece check)
- [ ] Add the row to docs/EXERCISE_TEST_CHECKLIST.md with today's result

## Part H — R6-DEMO coaching feel (speech queue · briefing · synced tempo · squat faults)

10-step demo walk for the bodyweight squat (full_squats) camera page — what
you should HEAR at each moment. Prescribe full_squats with tempo 3-1-2-0 and
a therapist note first.

- [ ] 1. Open the exercise → HEAR "Next exercise. …", then setup cues one
      after another with NO mid-word cutoffs anywhere in the session (P1).
- [ ] 2. Demo plays twice ("Watch me…", "One more time…") → at demo end
      HEAR "Now you try. Step into me." then, in order, the BRIEFING (P2):
      "We'll go slowly down for a slow three count, hold, then push up." →
      "Most common mistake: letting your knees drift past your toes. Sit
      your hips back and keep your knees behind your toes." → "Your
      therapist adds: {your note}." → "When you're ready, begin."
- [ ] 3. Step into the outline DURING the briefing → verify NO rep starts
      and no ghost lead-off until the briefing finishes (max 20s).
- [ ] 4. Do a clean rep at the prescribed pace → HEAR phase words synced to
      YOUR movement, not a clock (P3): "Slowly… all the way down." as you
      descend → "Hold." at the bottom → "Push up." as you rise. NO spoken
      numbers ever; chip + pills recolor per phase (blue/amber/green).
- [ ] 5. Freeze mid-rep for a few seconds → tempo speech stays silent (no
      wall-clock counting while you're not moving).
- [ ] 6. Rush the descent (~1s) on two reps in a row → HEAR once: "Slower
      on the way down — control it." Form % must NOT change from tempo.
- [ ] 7. Turn SIDE-ON to the camera (fault checks are silent when front-on
      — that's the confidence gate, not a bug). Squat pushing your knees
      forward past your toes → within a rep HEAR "Knees drifting past your
      toes — sit your hips back." and SEE the knee/shin segments AMBER
      (never red). Repeat immediately → silent (8s cooldown, one per rep).
- [ ] 8. Still side-on, let your heels lift on the descent → HEAR "Keep
      your heels down. Weight through mid-foot." + shin/foot ambers.
- [ ] 9. Do 3 shallow-but-counted reps in a row → HEAR once, gently: "You
      can go a little deeper if it's comfortable." (encouragement, not a
      fault — nothing ambers).
- [ ] 10. Finish the set → "Set complete! Well done." → rest → set 2 starts
      with only "Set 2. Same rhythm." (no re-briefing). Voice toggle off →
      everything silent; back on → cues resume. Zero console errors.

### Part H addendum — R6-HOTFIX safety faults (red)

- [ ] H1. Squat well past your prescribed range (frontal or side-on) →
      knee+thigh segments go RED and you HEAR "Too deep — come up a
      little. Stay in your range." Red fades ~2.5s after the cue.
- [ ] H2. Face the camera, shift your weight hard onto one leg mid-squat →
      the MORE-bent leg goes RED + "Uneven — you're loading one side more.
      Even out both knees." Turn side-on and repeat → SILENT (occluded far
      leg = no guess, by design).
- [ ] H3. Clean reps in range → NO red anywhere; only earned ambers (P4
      knee-over-toe / heel-rise) appear.

---
*Every future phase appends its manual steps to this file (standing rule 8).*

---

## Part H-2026-07 — DARK camera coaches: filming-day QA walk (one block per coach)

These coaches are DARK: catalog flags are False, so the ONLY way to run them
is the therapist QA page (`/therapist/qa/dark-coaches/` → "Test this coach").
Nothing on these pages is recorded (QA banner confirms). Walk each block on
the filming day BEFORE flipping that exercise's flag.

### H26. wall_sit_rx — Wall Sit (hold, side view)
1. Camera to your SIDE at hip height, ~2.5m; whole body + wall in frame.
2. Slide down to thighs-parallel and hold: hold clock counts UP, skeleton
   stays green/neutral, no cues while you hold a clean 90°.
3. Deliberate fault — depth drift: slide UP ~20° (thighs clearly above
   parallel) and stay there. Within ~1s: thigh segments amber + spoken
   "Slide down — thighs level with the floor". Slide back down: amber clears,
   clock resumes.
4. Deliberate fault — heel rise: lift both heels onto your toes mid-hold.
   Within ~0.5s: shin/foot segments amber + "Keep both heels on the floor".
5. Break the hold entirely (stand up): clock pauses (⏸ shows), coach cue
   "Back into position" class behavior — no red at any point (no safety
   channel on this coach).

### H27. plank_hold_rx — Plank Hold (hold, side view)
1. Camera to your SIDE at floor level, ~2.5m; whole body in frame.
2. Clean forearm plank: hold clock counts up, skeleton neutral, no cues.
3. Deliberate fault — sag: let your hips drop toward the floor and hold.
   Within ~1s: hip segments amber + "Lift your hips — straight line".
4. Deliberate fault — pike: push your hips up into a tent. Within ~1s:
   hip segments amber + "Lower your hips — straight line".
5. Return to a straight line: amber clears, clock resumes. No red ever.

### H28. side_plank_rx — Side Plank (hold, front view)
1. Camera in FRONT at floor level, ~2.5m; whole side-on body in frame.
2. Clean side plank (elbow under shoulder, hips up): hold clock counts,
   skeleton neutral.
3. Deliberate fault — hip drop: let your hip sink toward the floor and stay.
   Within ~1s: hip segments amber + "Push your hip up". Lift back: clears.
4. Both sides: repeat lying on the other side — detection must work
   mirrored (the coach reads whichever side line is cleaner).
5. No red at any point.

### H29. single_leg_balance_rx — Single-Leg Balance (hold, front view)
1. Camera in FRONT at waist height, ~2.5m; both feet visible.
2. Lift one foot (knee toward hip height): hold clock counts, neutral color.
3. Deliberate fault — foot down: quietly put the foot back on the floor and
   stand on two feet. Within ~1s: both shins amber + "Lift your foot to
   restart the clock"; the hold clock pauses (score falls under the
   40-point hold gate).
4. Deliberate fault — hip drop: keep the knee up but let the free-side hip
   sag hard. Within ~1s: hip segments amber + "Keep your hips level".
5. Repeat on the other leg. No red at any point.

### H30. straight_leg_raise_rx — Straight Leg Raise (reps, side view)
1. Camera to your SIDE at floor level, ~2.5m; lie on your back, full body
   in frame.
2. Clean reps (knee locked, lift to bent-knee height, slow lower): rep
   counter advances once per full cycle; green through the movement.
3. Deliberate fault — bend the knee as you lift (heel drops toward your
   backside mid-raise). Within ~0.5s: working shin ambers + "Keep that knee
   locked straight". Max one fault cue per rep.
4. Too-shallow lift (a few degrees off the floor): the raise phase should
   NOT complete — the rep must not count.
5. No red at any point.

### H31. knee_to_chest_rx — Knee to Chest (hold, side view)
1. Camera to your SIDE at floor level; lie on your back, full body in frame.
2. Draw one knee to your chest and hold: hold clock counts while the knee
   stays drawn in; green/neutral skeleton.
3. Deliberate fault — let the knee drift halfway back out and keep it there:
   the clock pauses (⏸) because the match score falls below the hold gate;
   "Back into position" class cue. Draw back in: clock resumes.
4. Both sides. No red at any point.

### H32. prone_knee_bend_rx — Prone Knee Bend (reps, side view)
1. Camera to your SIDE at floor level; lie face down, full body in frame.
2. Clean reps (heel to buttock, slow lower, hips flat): rep counter
   advances once per full cycle.
3. Deliberate fault — lift your hips off the floor as you bend the knee
   (tent up through the pelvis). Within ~0.5s: hip segments amber + "Keep
   your hips on the floor".
4. Shallow bend (~30°): the bend phase must NOT complete — no rep counted.
5. Both legs. No red at any point.

### H33. supine_hip_abduction_rx — Supine Hip Abduction (reps, feet view)
1. Camera BEYOND YOUR FEET at floor level looking up your body; hips and
   both legs in frame.
2. Clean reps (leg slides out ~2x hip width, slides back): rep counter
   advances once per out-and-back cycle.
3. Deliberate fault — shift your whole pelvis sideways instead of sliding
   the leg. Within ~0.5s: hip segments amber + "Keep your pelvis still".
4. Half slide (barely past hip width): the out phase must NOT complete.
5. Both legs. No red at any point.

### H34. sidelying_hip_abduction_rx — Side-lying Hip Abduction (reps, front view)
1. Camera in FRONT at floor level; lie on your side facing it, full body
   in frame.
2. Clean reps (top leg to ~45°, slow lower, hips stacked): rep counter
   advances once per lift-and-lower cycle.
3. Deliberate fault — roll your torso back toward the ceiling as you lift.
   Within ~0.5s: trunk segments amber + "Stack your hips straight up".
4. Tiny lift (~10°): the lift phase must NOT complete — no rep.
5. Both sides. No red at any point.

### H35. db_shoulder_press_rx — Dumbbell Shoulder Press (reps, front view)
1. Camera in FRONT at chest height, ~2m; head, arms and hips in frame.
2. Clean reps (both dumbbells pressed together to near-straight, controlled
   lower): rep counter advances once per press-and-lower cycle.
3. Deliberate fault — press one arm fully while the other stays at the
   shoulder. Within ~0.5s: the lagging arm ambers + "Press both arms up
   together".
4. Shrug your shoulders to your ears at the rack: the soft stance warning
   appears ("Drop your shoulders away from your ears") — warning only.
5. Half press (elbows to ~120°): the press phase must NOT complete.
6. No red at any point.

### H36. band_row_rx — Resistance Band Row (reps, side view)
1. Camera to your SIDE, ~2m; sit with the band around your feet, torso and
   arms in frame.
2. Clean reps (pull to the ribs, squeeze, slow return, torso tall): rep
   counter advances once per pull-and-return cycle.
3. Deliberate fault — lean your torso back as you pull (rocking the weight
   back). Within ~0.5s: trunk segments amber + "Sit tall — pull with your
   back".
4. Half pull (elbows to ~120°): the pull phase must NOT complete.
5. No red at any point.

## Part I — CI pipeline verification (sdlc-2026-07 Phase 1, run once after push)
CI encodes the full gate in `.github/workflows/ci.yml` — push + PR, all branches.

### I1. First green run
1. Push any commit (the Phase 1 commit itself counts). Open the repo on
   GitHub → Actions tab → "CI" workflow.
2. A run appears for branch `ship-ready-2026-06` and completes GREEN in
   under 30 min (job timeout kills it at 30).
3. Open the run and confirm all steps present and green, in this order:
   checkout · Python 3.12.3 · install requirements · Node · Django system
   check · collectstatic · Django test suite (serial) · Node tests ·
   Exercise targets fresh · Prod-mode smoke (check --deploy).
4. In the "Django test suite (serial)" step log: "Ran 377 tests" (or more,
   never fewer) and "OK".
5. In the "Node tests" step log: `# pass 47` (or more) and `# fail 0`.
6. In "Exercise targets fresh": "exercise_targets.json is fresh".
7. In "Prod-mode smoke": "System check identified no issues (0 silenced)".
   Any warning here is a regression — nothing is accepted or silenced.
8. Note the "Install requirements" step duration. If it exceeds ~5 min,
   that is the trigger to consider a mediapipe-free requirements-ci.txt —
   ONLY after proving the suite green without mediapipe (CLAUDE.md
   landmine: 257 exercise modules import cv2 unguarded; today the suite
   hard-requires it, so this is a future refactor, not a quick edit).

### I2. Red-path proof (once, then revert)
1. On a throwaway branch, break one Django test assertion, push.
2. Actions: the CI run goes RED at "Django test suite (serial)".
3. Delete the throwaway branch. Never merge it.

## Part J — Sentry error monitoring (sdlc-2026-07 Phase 2)
Loader ships in `strength_app/templates/strength_app/_sentry.html`, included by
`base_gamified.html` (patient, incl. camera page) and `base_therapist.html`
(console). Renders ONLY when SENTRY_DSN is set.

### J1. Dev/CI silence (no DSN)
1. Run the dev server WITHOUT SENTRY_DSN. Open the patient dashboard and the
   therapist console; View Source on both.
2. Zero hits for "sentry" in either page. DevTools Network: no request to
   any sentry-cdn.com host.

### J2. Prod wiring (after setting SENTRY_DSN on Render)
1. Render → service → Environment → add `SENTRY_DSN` (from the Sentry
   project's Client Keys page) → redeploy.
2. Open the deployed patient dashboard. View Source: one script from
   `browser.sentry-cdn.com/10.66.0/bundle.min.js` + one inline block whose
   DSN is the escaped string — no raw quotes/`</script>` visible.
3. DevTools console: `window.Sentry.getClient().getDsn()` returns the DSN;
   `Sentry.captureMessage('vyayam-smoke')` → event appears in the Sentry
   project within ~1 min.
4. Same check on the therapist console page.
5. In Sentry, open the smoke event: confirm NO user context, NO request
   body, NO cookies attached (clinical posture). If any of those appear,
   stop and treat as a shipping blocker.
6. Camera page (`v1_exercise_execute`): start a session, confirm the page
   still loads and coaches normally with the loader present (it extends
   base_gamified, so Sentry is on this page — watch for any console error).

---

## Part K — Athlete PWA + football demo seed (2026-07-18, LOCAL ONLY — not yet committed)

Prep once: `DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True python manage.py seed_football_demo`
(idempotent — safe to rerun; `--reset` removes only the FBDEMO rows).

### K1. Athlete login + Today tab
1. `/login/` → phone `9000000005`, password `athlete` → must land on
   `/athlete/today/` (NOT the generic dashboard).
2. Header reads "Today's Training, Kabir" with an "In-Season" phase pill.
3. Next-match card shows the nearest seeded match (opponent + N days away).
4. Amber "Performance tests due" card is visible (battery seeded 29 days ago).
5. Today's session card lists exercises with sets × reps; "Start Training"
   opens the existing session flow (`/v1/session/`).
6. "This week's training" bar shows completed vs 4 planned.

### K2. Progress tab
1. Bottom nav → Progress. Header "Your Performance, Kabir".
2. Level card shows L3 · Consolidation. Six battery bars (Single-Leg Hop,
   Nordic Hold, 20 m Sprint, Pogo Reactivity — never "RSI" — COD 505,
   Y-Balance) with 3/5-4/5 scores.
3. Consistency: this-week count, last-4-weeks total (14), 4 weekly bars.
4. sRPE bar chart shows the last-14-days sessions, values 4-7.
5. Confirm ZERO pain/rehab wording anywhere on the page.

### K3. Profile tab + nav states
1. Bottom nav → Profile: Kabir Singh, 21 yrs · Central Midfielder;
   "Your coach" = Arjun Mehta, S&C Coach · Vadodara United FC;
   current block (In-Season / Strength / Week 4 / L3); 3 upcoming matches.
2. Cycle all three tabs — active tab is highlighted sage each time.
3. Log out → back to `/login/`.

### K4. Coach side + no-regression
1. `/coach/login/` → `coach_arjun` / `simple` → squad shows Kabir Singh
   (L3, In-Season, green/on-track).
2. Kabir row → detail: 6-test battery with raw values, weekly load bars,
   recent sessions list, coach notes visible, 3 matches in calendar.
3. Rehab regression: `/login/` → `9000000001` / `patient` (anika) must still
   land on `/therapist-session/today/` and its 3 tabs still render.

---

## Part L — Strength tests (bench/leg press) + guided pacer (2026-07-19, LOCAL ONLY — not committed)

Prep: `DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True python manage.py seed_football_demo`

### L1. Athlete strength tests (manual entry)
1. `/login/` → `9000000005` / `athlete` → Progress tab: "Strength" card shows
   Bench Press 60 kg × 8 → est. 1RM 76 kg (1.09× BW) and Leg Press
   140 kg × 10 → 186.7 kg (2.67× BW), labelled "Estimated 1RM (Epley)".
2. `/football/assessment/` intro now lists 8 tests (bench + leg press last).
3. Walk to test 7 (`/football/assessment/6/`): weight + reps inputs (NO
   scoring guide, no camera), live e1RM preview appears as you type,
   "No equipment available — skip this test" link advances without writing.
4. Enter 60 / 8 → Save → lands on test 8; enter 140 / 10 → Save → results
   page renders normally; football level UNCHANGED by strength entries.
5. Coach console → Kabir detail: "Strength Tests — Manual Entry" table
   between the battery and HSR cards, with the "not used in the football
   level" footnote.

### L2. Guided pacer (ankle pumps / prone glute squeeze)
1. These two exercises must still be video-guided (no camera): catalog flags
   remain False — prescribe one to a test patient (therapist console) or
   verify via the seeded rehab flow after swapping a prescription item.
2. On the guided exercise page: "Count-along pacer" card with the pill
   "Guided exercise — follow the video".
   - Ankle Pumps: Start pacer → count climbs every 2 s to the prescribed
     reps → "SET DONE — MARK THE SET BELOW".
   - Prone Glute Squeeze: SQUEEZE 5s countdown → RELAX 3s, per rep.
3. Pacer start/stop writes nothing (set logging still via the set buttons).
4. Any other guided exercise (e.g. Single-Leg Balance): NO pacer card.

### L3. NOT done this session — dark-coach flip (deliberate)
Parts 4A/4B detection already exists in coach_dark.js (all 11 *_rx coaches,
integrity suite green). The v2_ghost_supported flip remains BLOCKED by the
documented gates: filming-protocol pass + this file's Part H-2026-07 walk +
mentor sign-off on MENTOR_REVIEW_QUEUE §2026-07 cue strings. Flip day per
exercise = one line in therapist_app/exercise_catalog.py + remove that
exercise's DARK assertions in strength_app/tests/test_camera_dark.py
(lines 99-101 invariant + '>DARK<' count).

### L4. Mind Lab scaffold (K4) — runner page + coach card
No game exists yet (games arrive with K5), so this walk checks the shell only.
1. Sign in as a coached football athlete (e.g. the seeded football demo
   athlete). Open `/athlete/mind-lab/anything_goes/` on the phone.
   Expect: page with a "Mind Lab" card and the line "No game is loaded."
   No console errors (a missing game is not an error).
2. Open `/athlete/mind-lab/Bad.Id/` → 404. Sign out and reopen step 1's URL →
   redirected to login.
3. Sign in as the athlete's coach. Open that athlete's detail page
   (Squad → athlete). Right column, under "Athlete Profile": card
   "Mind Lab — Latest Session" reads "No Mind Lab sessions yet."
4. Optional, to see the filled card: in `python manage.py shell` create
   `GameSession.objects.create(athlete=<PatientProfile>, game_id='demo',
   level=2, n_trials=20, accuracy=0.8, median_rt_ms=410)`; reload the coach
   page → card shows game, date, level 2, trials 20, accuracy 80%,
   median reaction 410 ms.
5. Athlete-visible text added: "Mind Lab", "No game is loaded.", "Saved.",
   "Could not save." — flagged for Pawan's physio mentor (cognitive-performance
   wording) before any wider release.

---

## Part M — Exhibition host acceptance walk, phone over mobile data (2026-11-17, K1)

Do this yourself after `docs/DEPLOY_DECISION.md` runbook step 8, before Wed 25 Nov.
Needs: the deployed `https://<name>.fly.dev` link, one phone, Wi-Fi OFF
(mobile data only), seeded demo (`DEMO_SEED=1`).

### M1. Reach + HTTPS
1. Phone browser (Chrome Android / Safari iOS): open `https://<name>.fly.dev/login/`.
2. Padlock shows, page loads in under 5 s. `http://` must jump to `https://`.
3. Open `/healthz/` → `{"status":"ok"}`.

### M2. Athlete login + first page (the slow one)
1. `/login/` → phone `9000000005`, password `athlete` → Log in.
2. Expected: lands on `/athlete/today/`, "Today's Training, Kabir", "In-Season" pill.
3. Time it. First visit after a deploy/restart may take 10–60 s (the registry
   import). Note the seconds: ______. Second visit must be under 3 s.

### M3. Football assessment on the phone
1. Bottom nav / Today → "Performance tests due" card → `/football/assessment/`:
   intro lists 8 tests.
2. Tap Start → test 1 (Single-Leg Hop) opens with `?side=left`. Enter a value,
   tap Save → goes to `?side=right`. Save → test 2.
3. Walk tests 2–6 the same way (Nordic, Sprint, Pogo, COD both sides, Y-Balance
   both sides). Each Save moves to the next test, no error banner.
4. Tests 7–8 (bench / leg press): enter 60 kg × 8, Save; tap "No equipment
   available — skip" on the last, or enter 140 × 10.
5. Results page renders with a football level. No pain/rehab wording.

### M4. Camera session over HTTPS on the phone
1. Today → "Start Training" → `/v1/session/` → open the first camera exercise.
2. Browser asks for camera permission → Allow. Camera must open (needs HTTPS).
3. Do 3 reps. Skeleton overlay follows you; rep counter climbs; a cue is spoken.
4. Finish the session, give feedback (sRPE) → Today shows the session done.
5. Tap Progress and Profile tabs: both render, active tab highlighted.

### M5. Stall conditions
1. Leave the phone idle on the page 20 minutes, then tap any link. Must
   respond in under 3 s (server must not have slept).
2. Second phone (or laptop) logs in as `9100000001 / athletepass123` at the same
   time and opens `/athlete/today/`. Both phones stay responsive.
3. Log out on both → back to `/login/`.

If any step fails, write what you saw and the time; run `fly logs` and look for
`Out of memory` / `Killed`. If seen: `fly scale memory 2048`.

---

## Part N — Exhibition demo walk: 4-week football athlete (K3)

Prep: `DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True python manage.py seed_football_demo`
(re-run on the day: the next match is seeded 3 days out). Script: `docs/DEMO_SCRIPT.md`.

### N1. Athlete side (phone)
1. Warm-up: `/login/` → `9000000005` / `athlete` → open `/athlete/today/` once. Note the load time.
2. Yellow "DEMO DATA · Not a real athlete" bar shows on Today, Progress and Profile.
3. Next-match card reads "3 DAYS AWAY" (Rajkot Rovers, "DEMO · League — home").
4. Amber "Deload" pill is on today's session; the list is short (about 3 exercises).
5. Progress tab: L3, six battery bars, 14 sessions in four weeks. No pain wording, no "RSI", no ACWR.

### N2. Coach side
1. `/coach/login/` → `coach_arjun` / `simple` → squad lists "Kabir Singh (DEMO)".
2. Athlete detail → Asymmetry card shows Hop LSI 87.4 % (below 90 %), flagged.
3. Coach notes begin "DEMO DATA — fictional athlete".

### N3. Honesty checks
1. No session shows green/yellow/red rep counts or a form score (all 14 are guided, self-counted).
2. Wording on every page is training-readiness only; none reads as diagnosis.
3. `seed_football_demo --reset` removes the athlete; rerun restores it with identical counts.

## Part O — Check-In 4, Mind Lab day gating, visitor mode (step 2)

Setup: start the server with `MIND_LAB_ENABLED=True`. Sign in as a coach-linked football athlete (phone, mobile data or Wi-Fi). Flag unset = every URL below is 404.

1. Open `/athlete/mind-lab/checkin/`. Expect 4 questions: sleep (3 choices) and three 1-5 sliders. Tap Done without a sleep choice. Expect it refuses.
2. Sleep over 6 h, stress 2, energy 5, focus 5, athlete's last traffic light green. Expect "Full day" and "Full Mind Lab today."
3. Sleep 5 to 6 h, same sliders. Expect "Light day" and the shorter-day line.
4. Sleep under 5 h, same sliders. Expect "Recovery-only day".
5. Last traffic light yellow (give a session feedback with joint pain), sleep over 6 h. Expect the shorter-day line.
6. Last traffic light red, sleep over 6 h. Expect "Recovery-only day" and "Check-In and Reset Breath only today." Red must win over good sleep.
7. Energy 1 (then stress 1 in a new check-in). Expect the line "If you feel very low, please talk to your coach or a qualified professional." The athlete is never blocked.
8. Coach dashboard for the same athlete. Expect NO check-in answers anywhere.
9. Visitor mode: signed OUT, open `/exhibition/mind-lab/`. Answer sleep and energy. Expect a day label and "Nothing was saved." Tap "Next visitor". Expect a blank form.
10. After step 9, open `/admin/` and confirm no new Mind Lab check-in row and no new game session from the visitor run. Energy 1 in the visitor run shows the support line.

## Part P — Pass Window + exhibition visitor mode (step 3)

Needs `MIND_LAB_ENABLED=True` in the environment. Phone, portrait. The 8 scenarios are demo scenarios and still UNREVIEWED: do not treat any answer as coaching advice.

1. Log in as an athlete. Open `/athlete/mind-lab/checkin/` and answer Sleep over 6 h, others 3 to 5. Open `/athlete/mind-lab/pass_window/`. The rules card shows "Demo scenarios", the shape key (circle you, squares teammates, triangles defenders), "Time Assist: 0.3x" and the not-a-return-to-play line.
2. Tap Start. A pitch appears. The triangle(s) slide toward you slowly. Nothing flashes. Tap a teammate square. The screen freezes about 2 s, shows a dashed amber line to the best teammate and a one-line reason ending "(Demo scenario)".
3. Let one trial run out without tapping. It says "Time ran out" and shows the best pass.
4. Finish all 8 trials (or 90 s). End card says "N of M best passes at 0.3x Time Assist" and "Compare only with your own earlier sessions at the same level". Status line below reads "Saved." Check no text mentions learning speed, leaderboards or match speed.
5. Gating, no check-in today (delete today's check-in or use a new athlete): `/athlete/mind-lab/pass_window/` shows "Check-In and Reset Breath only today." and no game. Repeat with Sleep under 5 h: "Recovery only today." and no game.
6. Sleep 5 to 6 h: game plays. After a perfect session the level does not rise (shortened day holds the level).
7. Level 3 and up (set by perfect sessions on full days, or edit nothing and trust the node/Django tests): after tapping a teammate a lane choice appears (Direct, or through the gap). Level 5 layouts may be mirrored left to right.
8. Visitor mode, signed out, phone: open `/exhibition/mind-lab/pass-window/`. It plays exactly 3 trials at Level 2 (0.5x), then reads "Nothing was saved." No login prompt. In the coach view and Django admin, no new GameSession appears.

Unsigned wording and numbers: see `docs/UNSIGNED_DEFAULTS.md` "Pass Window".


## Part Q — Return-to-play Tier 1: holds and coach lock (step 4)

Needs `RTP_ENABLED=True`. Laptop, coach login plus Django admin. There is no therapist screen yet, so set status in `python manage.py shell` with `strength_app.rtp.availability` (functions `place_hold`, `lift_hold`, `set_stage`, `set_base_status`). Wording of the athlete hold text is UNSIGNED: physio mentor must review it.

1. Flag off (`RTP_ENABLED` unset): coach athlete page, Override page and athlete Today look exactly as before. No "Override locked" anywhere.
2. Flag on, athlete with no hold: same screens, same session as step 1.
3. Place a hold (shell: `place_hold(patient, role='system')`). Athlete Today shows "Training paused" with the hold text. Starting a session shows the stopped page. A session cached earlier the same day is also stopped.
4. Coach athlete page: "Override locked" shows instead of the Override button. Open `/coach/athlete/<id>/override/` by URL: a red locked message, no form. Admin > Audit logs shows a "denied" row only after a POST attempt.
5. Flag for Review with a note still works while held. The athlete stays on hold.
6. As therapist (shell: `lift_hold(patient, actor=<assigned TherapistProfile>)`): hold lifts, athlete gets a session again. Try the same call as the coach profile: returns False and a "denied" audit row appears.
7. `set_stage(patient, 2, actor=<assigned therapist>)`: coach Override is locked again (rehab stage). Place and lift a hold: stage stays 2.
8. `set_base_status(patient, 'restricted', ...)`: Override opens with "you can only remove exercises". Adding an exercise is rejected (denied row). Removing is saved.
9. Admin: Audit logs, Availability statuses and Injury episodes are listed. Rehab pathways shows `hamstring` and `ankle` with no stages.

## Part R — Return-to-play Tier 2: injury questions, hold on feedback, coach view (step 4)

Needs `RTP_ENABLED=True`. Laptop for the coach and Django admin, phone for the athlete. There is no therapist screen yet: open an episode in Django admin (Injury episodes > Add, tick nothing for closed) or `python manage.py shell` with `strength_app.rtp.availability`, `clearance` and `checkpoints`. The wording of the five athlete questions is UNSIGNED: physio mentor must review it.

1. Flag off: the post-session feedback page has no injury questions and the coach athlete page has no status strip. Same as before.
2. Flag on, athlete with NO episode: feedback page has no injury questions. Submit with pain "None": no hold, coach page unchanged.
3. Open an episode for the athlete (admin). Flag on. Do a session and reach the feedback page: a card "A few quick questions about your injury" shows swelling, giving way, locking, tightness (0 to 10) and where. Answer all "No" and tightness 2, submit. Athlete is not on hold. Admin > Session feedbacks shows the five values saved.
4. Next session, answer swelling "Yes", submit. Athlete Today now shows "Training paused" and a new session is refused. Admin > Audit logs shows `place_hold` allowed, role system, reason `session_feedback`. Stage number unchanged.
5. Repeat on a second athlete with an active episode using giving way "Yes". Same result. Repeat with locking "Yes". Same result.
6. Leave every question blank and submit: no hold (blank never holds).
7. Coach login, athlete page: a strip shows Status, Traffic light, Stage (blank until W1 content exists), Restrictions, Checkpoint (due or passed) and "Injury signal yes/no". Injury signal is "yes" after step 4. View page source and search for "swelling", "giving way", "tightness", "locking": none of the athlete's answers appear.
8. Shell: `clearance.decide(patient, 'approved', actor=<assigned therapist>)` while held returns None. Lift the hold (`lift_hold`), approve: returns a row. Submit feedback with swelling "Yes": hold is placed and the clearance shows `invalidated_reason = red_flag` in admin shell.
9. Shell: `cp = checkpoints.open_checkpoint(patient, actor=<therapist>)`. As the coach profile: `enter_measure(cp, 'hop', '150', actor=<coach>)` stays pending. `enter_measure(cp, 'range', 'x', actor=<coach>)` returns None. `pass_gate(cp, actor=<coach>)` returns False. Coach page shows "Checkpoint due". Therapist `confirm_measure` then `pass_gate`: coach page shows "Checkpoint passed". Stage number unchanged. Audit logs list each denied attempt.

## Part S — Return-to-play Tier 3: notices, auto-hold on worse, inbox, status lines (step 4)

Needs `RTP_ENABLED=True`. Laptop for coach and therapist logins (both use `/coach/login/`), phone for the athlete. New wording is UNSIGNED: physio mentor must review it (list in the Tier 3 report). The therapist is the athlete's assigned therapist (admin > Patient profiles).

1. Flag off: coach squad has no Inbox button and no status line under athlete names. `/coach/inbox/` is a 404. Athlete Today has no status line.
2. Flag on, athlete with no episode and no hold: athlete Today has no status line. Squad shows no status line for that athlete.
3. Open an episode (admin). Athlete does a session, feedback: tightness 2, swelling No. Next session: tightness 6, swelling No. Athlete is put on hold (answers got worse). Athlete Today shows the hold text. Stage number in admin is unchanged.
4. Log in as the assigned therapist at `/coach/login/`, open Squad: Inbox button shows (1). Open it: the notice "Training paused for <name>. Their answers got worse since the last session." is under Notices, the athlete is under "Waiting for your decision". No swelling, giving way, tightness or locking values anywhere. Click Mark read: the notice goes, the count clears.
5. Shell: open a checkpoint, coach enters a hop result. Therapist Inbox shows it under "Checkpoints due" with "1 result to confirm". Confirm and pass: it leaves the list.
6. Log in as the coach: Squad shows "Medical hold · Injury signal: yes" under the athlete. No raw answers in the page source. Coach `/coach/inbox/` lists nothing about the athlete.
7. Coach cannot lift the hold or mark the therapist's notice read (shell `lift_hold` with the coach profile returns False, audit row denied).
8. Athlete with a "restricted" status and restriction `no_plyo` (shell `set_base_status`, then admin edit): Today shows "Status: Restricted" and "Restrictions: no_plyo".
9. Therapist lifts the hold (`lift_hold`): Today status line clears, session available again.

## Part T — Check-In 4 and Pass Window, phone walk (pre-merge round 3)

Needs `MIND_LAB_ENABLED=True`. Phone, portrait. Login: `/login/` → `9000000005` / `athlete` (seeded football demo athlete, Kabir Singh). Seeded: the athlete, his 14 sessions and the login. Live: today's check-in, the Pass Window game and its saved session. Pass Window scenarios are UNREVIEWED demo scenarios.

1. Log in, open `/athlete/mind-lab/checkin/`. Tap Done with no sleep choice: it refuses. Pick Sleep over 6 h, stress 2, energy 5, focus 5, tap Done: "Full day" shows.
2. Open `/athlete/mind-lab/pass_window/`. The rules card shows "Demo scenarios", "Time Assist: 0.3x" and the not-a-return-to-play line. Tap Start.
3. Tap a teammate square: the screen freezes about 2 s and a dashed amber line and a one-line reason ending "(Demo scenario)" show. Let one trial time out: "Time ran out" shows.
4. Finish the session: the end card shows "N of M best passes at 0.3x Time Assist" and the status line reads "Saved."
5. New check-in with Sleep under 5 h, then reopen `/athlete/mind-lab/pass_window/`: it shows "Recovery only today." and no game.

## Part U — Exhibition squat page, phone walk (`/exhibition/squat/`)

Needs `EXHIBITION_MODE=True` and HTTPS (or `localhost`): camera access needs a secure context. Phone, portrait, no login. Nothing on this page is saved.

1. Start the server with `EXHIBITION_MODE=True` (for example `EXHIBITION_MODE=True DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True python manage.py runserver 0.0.0.0:8000` behind an HTTPS tunnel). Without the flag, `/exhibition/` and `/exhibition/squat/` must give 404.
2. On the phone open `/exhibition/`. See the line "VYAYAM: a training plan that progresses on its own", a large "Try the squat coach" link and the dashed QR box. Tap the link.
3. `/exhibition/squat/` opens on the Start screen: a large Start button and the placement hint. No voice and no camera yet.
4. Tap Start. Allow the camera. You hear "Ready." and see it as a large caption. The header, camera box and rep card fit a 375 x 667 screen with no scrolling, and the rep count and position cue are visible. There is no "Show demo" button under 860 px.
5. Do 3 squats. Every spoken coach line appears as a large black caption bar at the TOP of the screen (it must never cover the rep card), in step with the voice. Turn the phone volume off: you can still follow every line.
6. On an iPhone in Safari, repeat steps 3 to 5: the voice must be audible after the first tap (known to fail without the tap unlock).
7. Reload, tap Start, and choose Don't Allow on the camera prompt: a "Camera not available" panel shows with a looped muted demo video (`full_squats.mp4`) and "Try again". "Try again" returns to the Start screen.
8. Block `cdn.jsdelivr.net` (airplane mode after loading the page, or a content blocker), reload, tap Start: the same failure panel shows.
9. Back on the Start screen, tap Start and leave the phone untouched, out of frame, for 60 s: the page returns to the Start screen on its own and the camera light goes off. Squat in frame instead: the reset does not fire while reps change.
10. In the browser network tab (or server log) confirm no POST request happens during the whole walk, and `db.sqlite3` row counts do not change.
11. Squat fixes (2026-11 review): while the camera runs, unplug or disable it (iPad: revoke camera in Settings, or cover and switch app so the track ends): the "Camera not available" panel shows within a few seconds, not a frozen frame.
12. Stand in frame but do not squat for 50 s, move to a different phase (go down, then up) at 50 s: the 60 s clock restarts on the phase change, so no reload at 60 s.
13. Phone layout: on a 375 x 667 phone (or browser device mode) there is no bottom gap and no scroll after the camera starts. Measure: header about 40 px, camera box 100dvh minus 230 px, rep card about 135 px.

## Part U2 — Exhibition games page, iPad walk (`/exhibition/games/`)

Needs `EXHIBITION_MODE=True`. iPad, Safari, landscape and portrait, no login. Nothing is saved. Optional: put a QR image at `strength_app/static/strength_app/exhibition/games_qr.png` and run `collectstatic`.

1. With the flag off, `/exhibition/games/` gives 404. With it on, `/exhibition/` shows a large "Play the demo games" link. Tap it.
2. The choice screen fills the iPad screen with no scrolling and no bounce: two large buttons (Pass Window, Go / No-Go Pass), the demo note, a QR box (dashed "QR code goes here" until the image exists, the image after) and the page URL in large text.
3. Tap Pass Window once. The round starts at once (no rules screen). Tap teammate squares. Each scenario shows the labels "Demo scenario". Scenarios repeat. Let the round run to its end: it must end by 60 s at most.
4. The "Done" text shows, with "Play again" and "Choose a game". Tap Play again: a new round starts. Tap Choose a game: back to the choice screen.
5. Tap Go / No-Go Pass. See the legend (blue circle = tap, orange triangle = do not tap) and Start. Tap Start. After a short "Get ready" the shapes appear one after another in the middle. Tap blue circles; do not tap orange triangles. The whole screen never flashes and the shape never changes more than about twice a second.
6. After 3 right in a row the shapes stay up a little less time. Make an error: the speed stays the same. Keep going: it never gets faster than 0.6 s per shape.
7. At 45 s the score screen shows accuracy and mean response time. Tap Play again, Start, play a second round: the table now shows the first round beside the second. Tap fast on every blue circle (under 0.15 s is hard): the mean must not count those. Tap an orange triangle: it must not count in the mean.
8. Tap Choose a game, then play Pass Window, then return: the Go / No-Go comparison is still there. Leave the iPad untouched for 60 s on any screen: the page reloads to the choice screen and the earlier round is gone (next visitor starts fresh).
9. Taps register on touch down (no 300 ms wait) and double-tap does not zoom the page. Rotate the iPad: the layout fits (100dvh), the Safari address bar changing size does not cut anything off.
10. No sound plays anywhere. In the network tab or server log no POST happens during the walk, and `db.sqlite3` row counts do not change.


## Part U3 — Games and squat review fixes (2026-11, slice 1)

1. iPad, `/exhibition/games/`, Pass Window: the teammate squares are at least 40 px wide (about 6 percent of a pitch up to 92 vw or 68 dvh wide). A finger hits them without missing.
2. A line under the pitch reads "Circle: you. Squares: teammates. Triangles: defenders."
3. Finish a round. Tap "Play again" with a finger placed where a teammate square will appear. The first scenario must not be answered by that tap (no instant "best" or "other" reveal at once).
4. On the "Done" screen the sentence about "your own earlier sessions" is gone. "Demo scenarios. Not a return-to-play test." stays.
5. Go / No-Go: no white ring appears on a tap. The shape never changes more than 3 times a second.
6. Play a Go / No-Go round, tap "Choose a game", then start Go / No-Go again: the table still shows the first round under "Your previous round". Leave the iPad alone for 60 s: the page reloads and the earlier round is gone.
7. With no QR file in the build, the dashed QR box is not shown. With the file, the image shows.
8. Phone 375 x 667, squat page: say a long cue so it wraps to 2 lines. The page does not scroll. The partial-rep line does not show.

## Part U4 — Progression page, laptop walk (`/exhibition/progression/`)

Needs `EXHIBITION_MODE=True`. Laptop, any browser, no login.

1. With the flag off, `/exhibition/progression/` gives 404. With it on, `/exhibition/` shows a link "See how a plan changes". Click it.
2. The page loads. The very first load after a server start can take about 10 seconds while the engine loads. Later loads take well under a second. The persona text says "returned to training" and "Training state set for this demo".
3. "Last 6 weeks" table: 6 rows, 3 sessions each, Week 4 (the lighter week) has fewer sets. Tagged "Illustrative demo data". "Last 7 days": 3 rows, the last one yesterday, pain column "No pain logged".
4. Symmetry table: lunge 50.0% then 63.6%, hop about 78% then 87.4% against 90%. The note says the hop result is not used by the plan.
5. Two plans side by side, tagged as computed live. Lunge rows: weaker-side sets are sets + 2 in "4 weeks ago" and sets + 1 in "Now". In "What changed" the Why column says "Symmetry band significant" and "Progression blocked" for the first run, and "Symmetry band moderate" and "Ready to progress" for the second.
6. No word like fracture, cleared, healing or diagnosis appears anywhere. The page has no script and no form.
7. Reload 5 times: the numbers stay the same (the non-lunge rows can change with the day of the week). In the Django admin the counts of patients, sessions and strength profiles do not change. No patient named EXHDEMO_ exists.
8. Open the page in two browser tabs at the same moment: both load, neither shows an error.

## Part U5 — Progression review fixes (2026-11)

1. `/exhibition/progression/`, "What changed", lunge row, Now column: Level reads 2 and the Why line says "Ready to progress: level 3 saved for the next session". Nothing on the page says the level is already 3.
2. The lunge rows are still in both plans (persona session length is 90 minutes, the top of the onboarding slider). The weaker-side sets are still sets + 2 and sets + 1.
3. The history table's last row reads "Week 6 (latest)". No other week number is on the page.
4. Phone 375 x 667, `/exhibition/squat/`, camera on: let a cue wrap to 2 lines. Both lines show in full, nothing is cut, the page does not scroll. A third line is not shown.
5. Page tab titles: index "VYAYAM", squat "Full Squats — VYAYAM", games "VYAYAM demo games", progression "VYAYAM: How a plan changes".
6. On Render free plan (512 MB), after deploy, open each page once. Compare with the memory table in `audit/EXHIBITION_FIXES2.md`. Order to try: `/exhibition/`, `/exhibition/squat/`, `/exhibition/games/`, `/exhibition/progression/`. Check the Render memory graph does not hit the limit.

## Part U6 — Squat demo first (`/exhibition/squat/`)

Needs `EXHIBITION_MODE=True` and HTTPS. Phone 375 x 667, portrait, no login. The clip is `strength_app/static/strength_app/videos/full_squats.mp4`.

1. Open `/exhibition/squat/`. Before any tap, the squat demo plays (muted, looped) above the Start button. No camera prompt appears. Start, "Show demo" and the hint all show without scrolling.
2. Tap "Show demo" on the Start screen: the clip restarts from the top.
3. Tap Start and allow the camera. Tap "Show demo" under the rep count: the coach runs its demo and the small Reference video plays. The page does not scroll, and the rep count is not covered.
4. Let a long cue wrap. The caption bar shows at most 3 lines and does not cover the rep count.
5. Reload, tap Start, choose Don't Allow: the "Camera not available" panel shows the message, the playing demo, "Show demo" and "Try again". "Show demo" restarts the clip.
6. Leave the page alone for 60 s after Start: it reloads to the Start screen.
7. With the flag off, `/exhibition/squat/` gives 404.
