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
