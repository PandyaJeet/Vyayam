# PRE_MERGE_FIXES_2

Branch `feat/rtp-tier3`. Head on arrival: `4d38826` (clean tree, confirmed live). Change commit: `c4eef77`, pushed.

## Change
`compare_pain_feedback` skips `pain_severity` (only that field) when a record has traffic_light green AND an empty pain_location (after the shared `normalise_pain_location`). Athlete form untouched. `LOCATION_CHANGE_COUNTS` still False.

**Per-record reading:** the gate is evaluated on each record; if EITHER the older or the newer record is green with empty location, severity is skipped. Green+location, or yellow/red+empty, still counts. If all fields skip, the result is `no_comparison` as before.

## Tests
- `test_severity_3_to_4_with_green_light_and_empty_location_is_not_worse`
- `test_severity_3_to_5_with_yellow_light_and_location_is_worse`

Existing `test_severity_worse_only_at_delta` used the default `rec()` (green, empty location), which the new gate correctly skips. Its records now use yellow + location `knee`. Assertions are unchanged. This is the one existing test edited.

## Diff (`git show c4eef77 -- strength_app/rtp/comparator.py`)
```diff
commit c4eef7736ed3fdb59fb1892d5324bcd6133fa39a
Author: Pawan Dangarwala <pawandangarwala@gmail.com>
Date:   Sat Nov 21 10:41:20 2026 +0530

    fix(rtp): comparator ignores pain_severity when light is green and location empty

diff --git a/strength_app/rtp/comparator.py b/strength_app/rtp/comparator.py
index b4ab035..9949fde 100644
--- a/strength_app/rtp/comparator.py
+++ b/strength_app/rtp/comparator.py
@@ -7,7 +7,12 @@ Every threshold is read from config at call time.
 
 Rules, per field:
 - traffic_light: higher is worse.
-- pain_severity: up by SEVERITY_DELTA is worse.
+- pain_severity: up by SEVERITY_DELTA is worse. Ignored (skipped like a null)
+  when a record has a green traffic light AND an empty pain_location, because
+  the athlete form posts severity 3 by default when no pain is reported.
+  Reading: the gate is per record, so if EITHER record is green with an empty
+  location (after normalise_pain_location) the severity field is skipped.
+  Green with a location, or yellow/red with an empty location, still counts.
 - swelling_today, giving_way: no to yes is worse.
 - tightness_0_10: up by TIGHTNESS_DELTA is worse.
 - locking_or_catching: yes in the NEWER record is worse.
@@ -83,6 +88,18 @@ def _location(prev, curr):
     return SAME if p == c else WORSE
 
 
+def _severity_is_noise(rec):
+    return (getattr(rec, 'traffic_light', None) == 'green'
+            and not normalise_pain_location(getattr(rec, 'pain_location', None)))
+
+
+def _severity(prev, curr):
+    if _severity_is_noise(prev) or _severity_is_noise(curr):
+        return None
+    return _number(getattr(prev, 'pain_severity', None), getattr(curr, 'pain_severity', None),
+                   config.SEVERITY_DELTA)
+
+
 def compare_pain_feedback(prev, curr):
     if prev is None or curr is None:
         return NO_COMPARISON
@@ -98,7 +115,7 @@ def compare_pain_feedback(prev, curr):
 
     verdicts = [
         _light(g(prev, 'traffic_light'), g(curr, 'traffic_light')),
-        _number(g(prev, 'pain_severity'), g(curr, 'pain_severity'), config.SEVERITY_DELTA),
+        _severity(prev, curr),
         _no_to_yes(g(prev, 'swelling_today'), g(curr, 'swelling_today')),
         _no_to_yes(g(prev, 'giving_way'), g(curr, 'giving_way')),
         _number(g(prev, 'tightness_0_10'), g(curr, 'tightness_0_10'), config.TIGHTNESS_DELTA),
```

## Gate (run 10:41-10:50 IST, foreground, load 9.0 at start)
```
$ python manage.py check
System check identified no issues (0 silenced).

0 static files copied to '/Users/pawandangarwala/Documents/vyayam/worktrees/t3/staticfiles', 169 unmodified, 382 post-processed.
collectstatic exit 0
  File "/Users/pawandangarwala/Documents/vyayam/worktrees/t3/strength_app/v1_prescription_engine.py", line 1602, in generate_v1_session
    _advance_hsr_phase(patient, patient.football_profile)
                                ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/pawandangarwala/Library/Python/3.12/lib/python/site-packages/django/db/models/fields/related_descriptors.py", line 492, in __get__
    raise self.RelatedObjectDoesNotExist(
strength_app.models.PatientProfile.football_profile.RelatedObjectDoesNotExist: PatientProfile has no football_profile.
.....................Forbidden: /therapist/dashboard/
.Not Found: /therapist/patient/28c6d567-4c28-4e47-8143-1f53cae6ea7c/
.Not Found: /therapist/patient/c8957b66-fbe7-46c1-8882-f1c660377345/program/save/
............................................................................................................................................................................
----------------------------------------------------------------------
Ran 591 tests in 466.813s

OK
Destroying test database for alias 'default'...
  ...
1..68
# tests 68
# suites 0
# pass 68
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 403.129819
2026-11-21 10:49:53.871221: I tensorflow/core/platform/cpu_feature_guard.cc:210] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
To enable the following instructions: AVX2 FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
exercise_targets.json is fresh
```
Totals: Django 591 tests, 0 failures (baselines: Tier 2 561; last Tier 3 589 with 2 failures). Node 68/68 (baseline 68). The two IST/UTC date-bug failures did NOT appear. Date bug not touched.
`H2_RESULTS.md` restored with `git checkout --`.
