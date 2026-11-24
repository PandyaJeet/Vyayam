# VYAYAM exhibition demo — 3-minute click-through

Athlete: **Kabir Singh (DEMO)**, a fictional football midfielder. Everything
about him is seeded. A yellow "DEMO DATA · Not a real athlete" bar shows on
every athlete page, and "(DEMO)" is in his name on the coach pages.

**Logins**

| Who | Where | Login |
|---|---|---|
| Athlete | `/login/` | phone `9000000005` · password `athlete` |
| Coach | `/coach/login/` | `coach_arjun` · `simple` |

## Before the stall opens

1. Run the seed on the morning of the show (dates are relative to today):
   `DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True python manage.py seed_football_demo`
   On the hosted Space, restart it that morning with `DEMO_SEED=1` set.
   The next match is seeded **3 days from the day you seed**. Seed on the
   wrong day and the match countdown is wrong.
2. **Step 0, warm-up.** The first logged-in page took about 11 s in the host
   test (K1). Log in as the athlete and open `/athlete/today/` once,
   **before visitors arrive**. Then log out and start the script. Do the
   same once on the coach login (`/coach/squad/`).

## Click-through (≈3 min)

| # | Do | What appears | Say |
|---|---|---|---|
| 1 | Open `/login/`. Phone `9000000005`, password `athlete`. | Lands on `/athlete/today/`. Yellow DEMO bar on top. "Today's Training, Kabir". | "This is Kabir, a made-up midfielder. Four weeks of training are already behind him." |
| 2 | Point at the **Next match** card. | "3 days away", Rajkot Rovers. | "His match is in three days. The app knows, and shapes today around it." |
| 3 | Point at the amber **Deload** pill and the short session list. | Deload pill. A light session of a few exercises. | "He has trained hard for four weeks. The app's own rule says an easier week is due, so it planned one." |
| 4 | Tap bottom nav **Progress** (`/athlete/progress/`). | Level 3 card, six test bars, 14 sessions in four weeks, effort bars. | "Four weeks of sessions and his test scores. All fictional." |
| 5 | Open `/coach/login/`. Sign in `coach_arjun` / `simple`. Tap **Kabir Singh (DEMO)** on `/coach/squad/`. | Coach view of the same athlete. | "Now I am his coach. Same data, coach side." |
| 6 | Scroll to the **Asymmetry** card. | Hop symmetry **87.4 %**, below the 90 % target, flagged. | "His left leg hops 152 cm, the right 174. That gap is under our 90 % target, so it is flagged." |
| 7 | Say it, do not click. | — | "A home test showed his right leg weaker on lunges. The app adds a set for that side when it plans a lunge day." |
| 8 | Open `/athlete/profile/`, or log in as the athlete again. | Coach name, current block, three upcoming matches. | "His coach, his block and his matches, in one place." |
| 9 (optional) | On Today, tap **Start Training**. | The live session flow. | "This part is live. Pick an exercise and the camera coaches form in real time." |

## Live versus seeded

- **Live (real code running now):** login, page rendering, the deload
  decision, the match-day countdown, the asymmetry rules, and the camera
  session in step 9.
- **Seeded (fictional):** Kabir, his four weeks of sessions, test results,
  coach, matches and notes.
- **Derived by the app, then stored:** the hop flag (87.4 %), the lunge
  finding (63.6 %, "moderate"), one capability step-up in the lunge
  family (3 to 4, after three comfortable sessions), and the deload. The
  seed stops with an error if the app does not produce these.
- **Guided versus camera:** all 14 seeded sessions are self-counted guided
  work. They carry no rep-level or form data, by design. Do not say the
  camera scored them.
- **Not in the demo:** no pain history. No injury-risk score. Say
  "training readiness" only. Do not say "diagnosis".
- **Not visible on screen:** the lunge extra set (step 7) and the step-up
  in capability. Today shows a deload, which has no lunge work. Say them
  aloud only as described, not as something on screen.

## If something goes wrong

- Match shows the wrong day count: re-run the seed.
- Page slow on first tap: you skipped step 0. Wait it out and keep talking.
- Reset the demo rows only: `python manage.py seed_football_demo --reset`.
