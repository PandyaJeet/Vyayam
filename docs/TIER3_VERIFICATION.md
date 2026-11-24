# Tier 3 verification

Run 2026-11-21 ~02:30-02:50 IST, branch feat/rtp-tier3, foreground, load 4-5.

## Head on arrival
`3adfe3a46b39b6da46ee53e75c92884b8b1ed976` (confirmed live, tree clean). Commits over origin/feat/rtp-tier2:

```
3adfe3a test(rtp): tier 2 worse-signal test now expects the S11 hold
971a8fa docs(rtp): MASTER_TEST_DAY Part S, UNSIGNED_DEFAULTS tier 3
056fd75 feat(rtp): S14 athlete status line on Today screen
6df8fab feat(rtp): S14 coach status line on squad screen and inbox link
775f526 feat(rtp): S13 therapist inbox
be85c27 feat(rtp): S11 auto-hold on worse comparator verdict
8271bcb feat(rtp): S10 in-app therapist notification on hold
```

## Fix 1: red holds only with an active episode
`strength_app/rtp/availability.py` `feedback_triggers_hold`: the red check moved inside `has_active_episode`. Locking is unchanged (still holds without an episode, as before; the brief said it was episode-only, the code and test_rtp_tier1 say otherwise. Left as is, flagged).
New tests (`strength_app/tests/test_rtp_tier2.py`, class SPINE 19):
- `test_red_without_episode_is_not_held_and_shows_no_hold_text` (asserts is_held False, no medical_hold row, hold text and status line absent from rendered /athlete/today/)
- `test_red_with_active_episode_is_held` (held, hold text shown)
`test_red_and_locking_hold` in test_rtp_tier1 updated to the new rule. Commit 914e9b3.

## Fix 2: worse-verdict test
`test_signal_yes_when_comparator_says_worse` already expected `is_held` True (done in 3adfe3a, verified by diff); injury-signal assertion intact. Added docstring naming the S11 ruling (914e9b3).

## Fix 3: second stall
Not reproduced. Evidence: therapist_app modules 3-7s each; strength_app therapist/session modules (test_c_therapist_note 40s, test_f_voice 25s, test_guided_pacer 25s, test_d_show_demo 20s, test_r1_capture 87s, test_r5_integration 26s, test_r4_coaching 37s) all finished; full suite 589 tests in 569s with no hang. Slow tests are generate_v1_session at ~7-10s each (TensorFlow import and engine), not blocking calls. No code guard added. Likely cause of the earlier 30-minute hang: host load or the dead worker's backgrounded run. Unproven.

## Pre-existing time-of-day defect (found during the gate)
Two failures only between 00:00 and 05:30 IST (UTC date differs from IST date). With TIME_ZONE temporarily set to UTC, both modules pass (27 tests OK); settings restored, nothing committed.
- `therapist_app/views.py:141,172,271` use `timezone.now().date()` (UTC) against `timezone.localtime(...).date()` (IST) at line 108 -> pain flag dropped.
- `strength_app/v1_safety_logic.py:832` uses `date.today()` against UTC-based session dates -> return-after-break 10 days reads gentle_return.
Probable cause of the two unexplained failures in the Step 1 gate. Not fixed (out of scope). Rerun after 05:30 IST should be green.

## Gate (verbatim essentials)
```
python manage.py check -> System check identified no issues (0 silenced).
collectstatic --noinput -> 0 static files copied ..., 169 unmodified, 382 post-processed. exit=0
python manage.py test --parallel 1 -> Ran 589 tests in 569.375s / FAILED (failures=2)
FAIL: test_return_after_break_day_boundaries (strength_app.tests.test_exam_2026_07_gaps.TestE6DosingModifiers...)
  AssertionError: 'gentle_return' != 'none' : 10 days
FAIL: test_dashboard_pain_flag_fires_from_painevent (therapist_app.test_group4.TherapistProgramBuilderTests...)
  AssertionError: 'Pain >5 last week' not found in []
node --test -> tests 68, pass 68, fail 0
export_exercise_targets --check -> exercise_targets.json is fresh
```
Totals: Django 589 (Tier 2 561, Tier 3 partial 587), failures 2 (both time-of-day, above; 0 from RTP code). Node 68 (baseline 68). SPINE 15-20 tests all ok in the verbose log.
Full log: /tmp/t3_full.log.
