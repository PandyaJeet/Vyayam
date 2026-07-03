# VYAYAM — Pitch Smoke List (run the night before)

One ordered walk, ~25 minutes. Every step lists the expected result — if any
step doesn't match, stop and investigate before the pitch. Console open
(F12) for the whole patient session. Run against the CURRENT code on a
freshly restarted server (`python manage.py runserver`) after
`python manage.py seed_therapist_demo`.

---

## 1 · Therapist: edit + publish Anika's program

1. Go to `/therapist/login/` → **dr_shah / simple**.
   → Dashboard shows Anika Patel's card.
2. Open Anika → **Program Builder** tab.
   → Each exercise row shows: Sets / Reps / Load / Rest / **Usual pain** / **Note**.
3. On **Glute Bridge** set: Note = `Squeeze top 2s`, Usual pain = `5`,
   tempo stays `3-1-1`. Press **Publish**.
   → Green success state; no console errors.

## 2 · Patient: full session, every button

4. New tab (or private window) → `/login/` → **9000000001 / patient**.
   → Lands on **Today's Rehabilitation Session**; Glute Bridge shows the
   amber "Therapist note: Squeeze top 2s".
5. Press **Start your session**.
   → Exercise 1 of 5 (Glute Bridge, camera screen). The same amber note
   sits under the title. Tempo card shows 3-1-1.
6. Press **Start Camera** and step back until your whole body is framed.
   → After the framing check: **"Ready. Step into the outline…"** —
   NO forced demo, no cue lecture.
7. Get into position and do 2–3 reps.
   → Reps count, form % updates, and the top-right tempo chip cycles
   **blue "Slowly down" 3-2-1 → amber "Hold" 1 → green "Up" 1**, each
   phase word spoken once in the picked voice.
8. Press **Show demo**.
   → Spoken guidance → ghost demos 2 reps → "Now you try" hands back.
9. Fill reps → **Set done** → rest timer → **Skip Rest**.
   → Chip disappears during rest, resumes on skip.
10. **Report Pain** → aching → any location → severity **4** → submit.
    → "Recording…", then the GREEN "within your usual range" message;
    panel closes; session continues. (No guidance text while sliding.)
11. **Report Pain** again → aching → severity **6** → submit.
    → Amber/red "above your usual level — skipping" message, then the
    NEXT exercise loads.
12. Exercise 2 (Clamshell, tempo `—`).
    → NO tempo card, NO chip, no tempo speech, zero console errors.
    Press **Skip this exercise** to advance.
13. Exercise 3 (Single-Leg Balance, guided screen — no camera).
    → Note renders; set buttons work; **Done** advances via feedback page.
14. Exercise 4 (Step-up, camera): **Report Pain** → **aching** →
    severity **8** → submit.
    → "Recording…", then the red **"Stop for today… Your physiotherapist
    has been alerted"** message → redirect to the calm session-ended page.

## 3 · Therapist: message + alert arrived

15. Back in the dr_shah tab: open Anika → **Messages**.
    → ⚠ HIGH PAIN system message: "aching pain 8/10 on Step-up… Session paused."
16. Open `/therapist/alerts/`.
    → The same alert listed unreviewed. Press **Mark reviewed** — it clears.

## 4 · The showpiece: squat camera coach

17. As the patient (or self-serve demo account), open the **squat**
    camera exercise. Start Camera → framing → straight in.
    → Detection locks, ghost guides, reps count, form % responds to depth,
    voice cues play in the friendlier voice (rate 0.95).
18. Press **Show demo** once.
    → Demo plays, hands back, scoring resumes.

## 5 · Self-serve stop parity (30 seconds)

19. As a SELF-SERVE patient on any camera exercise: Report Pain →
    aching → severity **9**.
    → Red stop guidance, "Ending today's session…", session-ended page.

## 6 · Report + coaching cycle (R1–R5)

20. **Rest + pause capture:** during a managed session, tap **+30s** on a
    rest timer and **Pause session** once (resume after ~30s).
    → Both appear later in the report: "+30s extended" on that set's rest
    column and "paused Ns" on the paused set.
21. **Mid-rep pain pin:** on a camera exercise, stop mid-rep and report
    aching **4**.
    → The report's pain line reads "aching 4/10 at rep R of set S" —
    the exact rep the modal opened on.
22. **The report, both sides:** finish the session → **View today's
    session report** on the finished page; then as dr_shah open
    Reports → Session reports → same session.
    → Identical document: narrative first, per-set tables with form/depth/
    tempo, elapsed AND working times, footer disclaimer. Print preview
    (Cmd+P) is clean.
23. **Coaching spot-check:** start a squat set — hear "Let's see your
    natural movement first" (2 uncolored reps), let your knees cave once
    → ONE "Knees toward the camera" (red only now); fix it → "Better —
    knees are tracking now"; ignore a cue 3 reps → one "Let's slow down —
    quality over count" then silence; step out of frame ~2s → grey
    skeleton + "I can't see you clearly". Tempo counts "Slowly down —
    3… 2… 1" pause while the coach speaks.

---

**If anything fails:** `python manage.py test` (310+ tests) — the inline-JS
harness (`test_g0_inline_js_integrity`) pinpoints any broken page + line;
`node --test strength_app/tests/js/` covers the CV, voice and coaching cores.
