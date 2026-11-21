# Pre-merge fixes, round 3 (feat/rtp-tier3)

Date: 2026-11-21 IST. Worktree `/Users/pawandangarwala/Documents/vyayam/worktrees/t3`.

## Head on arrival

`d72ba5a docs(rtp): pre-merge fixes 2`, clean tree.

## Change: locking_or_catching holds only with an active episode

Pawan's ruling. This is the second knowing departure from SPINE_SPEC's hold rule (red was the first, commit 914e9b3). Guardrail 1: an athlete with no episode behaves exactly as today. The comparator's own locking rule (worse if yes in the newer record) is untouched; `comparator.py` is not changed.

### `git show 14dc9db`

```diff
commit 14dc9dbfe72ade5fdfbaaf7bef8c1cf9ebb72a0a
Author: Pawan Dangarwala <pawandangarwala@gmail.com>
Date:   Sat Nov 21 15:23:11 2026 +0530

    fix(rtp): locking_or_catching holds only with an active episode

diff --git a/strength_app/rtp/availability.py b/strength_app/rtp/availability.py
index 4302315..75e658d 100644
--- a/strength_app/rtp/availability.py
+++ b/strength_app/rtp/availability.py
@@ -224,13 +224,14 @@ def check_flag_review(patient, actor, post):
 
 def feedback_triggers_hold(patient, feedback):
     """Newest session feedback only. A null never holds. Swelling and giving way
-    count only for an athlete with an active episode. So does a red light."""
+    count only for an athlete with an active episode. So do a red light and locking."""
     if feedback is None:
         return False
-    if getattr(feedback, 'locking_or_catching', None) is True:
-        return True
     if has_active_episode(patient):
         # Pawan's ruling: red holds only with an active episode (guardrail 1 beats the spec list).
+        # Same ruling for locking_or_catching: SPINE_SPEC lists it unqualified; episode-only here.
+        if getattr(feedback, 'locking_or_catching', None) is True:
+            return True
         if getattr(feedback, 'traffic_light', None) == 'red':
             return True
         if config.HOLD_ON_SWELLING and getattr(feedback, 'swelling_today', None) is True:
diff --git a/strength_app/tests/test_rtp_tier1.py b/strength_app/tests/test_rtp_tier1.py
index 4a6a62e..ea69358 100644
--- a/strength_app/tests/test_rtp_tier1.py
+++ b/strength_app/tests/test_rtp_tier1.py
@@ -128,12 +128,18 @@ class TestSpine19SwellingGivingWay(RtpBase):
         self.assertFalse(av.apply_feedback_hold(self.athlete, fb()))
 
     def test_red_and_locking_hold(self):
-        # Red holds only with an active episode (Pawan's ruling); locking holds regardless.
+        # Red and locking hold only with an active episode (Pawan's rulings).
         self.assertFalse(av.feedback_triggers_hold(self.athlete, fb(traffic_light='red')))
+        self.assertFalse(av.feedback_triggers_hold(self.athlete, fb(locking_or_catching=True)))
         InjuryEpisode.objects.create(patient=self.athlete)
         self.assertTrue(av.feedback_triggers_hold(self.athlete, fb(traffic_light='red')))
         self.assertTrue(av.feedback_triggers_hold(self.athlete, fb(locking_or_catching=True)))
 
+    def test_locking_without_active_episode_does_not_hold(self):
+        self.assertFalse(av.feedback_triggers_hold(self.athlete, fb(locking_or_catching=True)))
+        self.assertFalse(av.apply_feedback_hold(self.athlete, fb(locking_or_catching=True)))
+        self.assertFalse(av.is_held(self.athlete))
+
 
 class TestCoachScreens(RtpBase):
     URL = '/coach/athlete/{}/override/'
```

### Post-change body of `feedback_triggers_hold` (`strength_app/rtp/availability.py`)

```python
def feedback_triggers_hold(patient, feedback):
    """Newest session feedback only. A null never holds. Swelling and giving way
    count only for an athlete with an active episode. So do a red light and locking."""
    if feedback is None:
        return False
    if has_active_episode(patient):
        # Pawan's ruling: red holds only with an active episode (guardrail 1 beats the spec list).
        # Same ruling for locking_or_catching: SPINE_SPEC lists it unqualified; episode-only here.
        if getattr(feedback, 'locking_or_catching', None) is True:
            return True
        if getattr(feedback, 'traffic_light', None) == 'red':
            return True
        if config.HOLD_ON_SWELLING and getattr(feedback, 'swelling_today', None) is True:
            return True
        if config.HOLD_ON_GIVING_WAY and getattr(feedback, 'giving_way', None) is True:
            return True
    return False
```

## Tests

- New: `strength_app.tests.test_rtp_tier1.TestSpine19SwellingGivingWay.test_locking_without_active_episode_does_not_hold`. Locking yes, no episode: `feedback_triggers_hold` is False, `apply_feedback_hold` is False, athlete not held.
- Edited: `strength_app.tests.test_rtp_tier1.TestSpine19SwellingGivingWay.test_red_and_locking_hold`. The comment "locking holds regardless" is gone. It now also asserts locking does NOT hold before the episode opens, and still asserts it holds after.
- Searched all of `strength_app/tests/` for `locking`. No other test asserted the old rule. `test_rtp_tier2.TestFeedbackHold.test_locking_yes_holds_athlete_with_episode` and the Tier 3 tests that submit locking "yes" already open an episode first, so they are unchanged and still pass. The comparator locking test (`test_locking_yes_in_newer_record_is_worse_even_if_older_also_yes_or_null`) is unchanged.

## MASTER_TEST_DAY.md: Part T

Parts A to S are used (Part H twice), so this is Part T.

## Part T — Check-In 4 and Pass Window, phone walk (pre-merge round 3)

Needs `MIND_LAB_ENABLED=True`. Phone, portrait. Login: `/login/` → `9000000005` / `athlete` (seeded football demo athlete, Kabir Singh). Seeded: the athlete, his 14 sessions and the login. Live: today's check-in, the Pass Window game and its saved session. Pass Window scenarios are UNREVIEWED demo scenarios.

1. Log in, open `/athlete/mind-lab/checkin/`. Tap Done with no sleep choice: it refuses. Pick Sleep over 6 h, stress 2, energy 5, focus 5, tap Done: "Full day" shows.
2. Open `/athlete/mind-lab/pass_window/`. The rules card shows "Demo scenarios", "Time Assist: 0.3x" and the not-a-return-to-play line. Tap Start.
3. Tap a teammate square: the screen freezes about 2 s and a dashed amber line and a one-line reason ending "(Demo scenario)" show. Let one trial time out: "Time ran out" shows.
4. Finish the session: the end card shows "N of M best passes at 0.3x Time Assist" and the status line reads "Saved."
5. New check-in with Sleep under 5 h, then reopen `/athlete/mind-lab/pass_window/`: it shows "Recovery only today." and no game.

## Full gate (foreground, after 06:00 IST)

`uptime` before the run: `17:21  up 1 day, 23:09, 1 user, load averages: 4.14 3.85 3.96`.

Note: two earlier full runs (started 15:58 and 16:38) were cut by the 30-minute tool limit while the host was slow; neither showed a failure before it was cut. The run below is the complete one, started 17:21:07, finished 17:29:30.

```
$ export DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True
$ python manage.py check
System check identified no issues (0 silenced).
$ python manage.py collectstatic --noinput
0 static files copied to '/Users/pawandangarwala/Documents/vyayam/worktrees/t3/staticfiles', 169 unmodified, 382 post-processed.
$ python manage.py test --parallel 1
Found 592 test(s).
...
Ran 592 tests in 482.275s

OK
Destroying test database for alias 'default'...
$ node --test strength_app/tests/js/*.test.mjs
1..68
# tests 68
# suites 0
# pass 68
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 430.497804
$ python manage.py export_exercise_targets --check
exercise_targets.json is fresh
```

Totals against baseline: Django 592 run, 0 failures (baseline 591, +1 new test). Node 68 pass, 0 fail (baseline 68). Neither IST/UTC date-bug failure appeared. SPINE tests 15 to 20 are in the RTP modules and pass (RTP tier 1-3 modules alone: 98 OK). `H2_RESULTS.md` restored with `git checkout --`.

## UNVERIFIED

- Part T was not walked on a phone. That 9000000005 reaches Mind Lab with `MIND_LAB_ENABLED=True` is inferred from Parts N and O, not tried.
- `RTP_ENABLED` default False is unchanged by this round (no settings touched); not re-read live.
