# INTEGRATION_PRE_SHOW — step 1 (2026-11-20)

Branch `integration/pre-show`, worktree `/Users/pawandangarwala/Documents/vyayam/worktrees/int`,
created from LOCAL `main` = `0208e844bb8f0a63c820e5e8d8df24b3d7b3f880`. No application code changed.
`deploy` was NOT merged. `main` was not pushed.

## 1. Merges (in order)

| # | Branch | Result | Merge commit |
|---|---|---|---|
| 1 | `origin/audit/principles-status` | clean (adds `docs/PRINCIPLES_STATUS.md`, 139 lines) | 2f3e4a3 |
| 2 | `origin/deploy-host-decision` | clean (Dockerfile, entrypoint.sh, fly.toml, docs/DEPLOY_DECISION.md, docs/deploy_measure/*, scripts/measure/*, MASTER_TEST_DAY Part M) | 031f74e |
| 3 | `origin/demo/football-4week` | CONFLICT in `MASTER_TEST_DAY.md` | c6887ff |
| 4 | `origin/feat/mind-lab-scaffold` | CONFLICT in `MASTER_TEST_DAY.md` | cc4aa78 |

Merge 2 was clean because only `deploy-host-decision` had added Part M by then. The first conflict is at merge 3.

### Conflict 1 (merge 3): two `## Part M` sections
Both branches appended a `## Part M` with `### M1`... at the end of the file.
Resolution: kept both in full.
- Part M stays the **host acceptance walk** (K1, `### M1`–`### M5`), unchanged.
- The **demo walk** (K3) is renamed **Part N** (`### N1`, `### N2`, `### N3`), text unchanged apart from the letter. A `---` separator was placed between the two Parts to match the file's style.
- Cross-references checked: `docs/DEMO_SCRIPT.md` and `seed_football_demo.py` contain no "Part M" / "M1–M3" reference, so nothing else needed renaming.
- **Part letter renamed: M → N, on the demo walk (K3).**

### Conflict 2 (merge 4): L4 vs the Part M/N tail  (NOT clean, unlike the brief)
`feat/mind-lab-scaffold` added `### L4` directly after `### L3`. Git conflicted because the other side had added Part M after the same L3 text. Resolution: kept every line from both sides. `### L4` now sits at the end of Part L (right after L3, before the `---` that starts Part M); Parts M and N follow it unchanged. Final heading order: L1, L2, L3, L4, Part M (M1–M5), Part N (N1–N3). No conflict markers remain.

`MASTER_TEST_DAY.md` was edited only to resolve these conflicts. No new section was added.

## 2. Gate (serial, one command at a time, `DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True`)

Full raw logs are committed next to this file in `docs/integration_pre_show/` (control characters stripped; the Django run used `-v 2`, so it lists every test name).

### 2.1 `python manage.py check`
```
System check identified no issues (0 silenced).
exit=0
```

### 2.2 `python manage.py collectstatic --noinput` — exit 0
Full output: `docs/integration_pre_show/2_collect.txt`. Last lines:
```
Found another file with the destination path 'strength_app/audio/coach/README.txt'. It will be ignored since only the first encountered file is collected. If this is not what you want, make sure every static file has a unique path.

168 static files copied to '/Users/pawandangarwala/Documents/vyayam/worktrees/int/staticfiles', 440 post-processed.
exit=0
```
(The "Found another file with the destination path" warnings are duplicate static paths; not checked whether `main` shows them too.)

### 2.3 `python manage.py test --parallel 1` — exit 0
Full output: `docs/integration_pre_show/3_django.txt`. Tail:
```
----------------------------------------------------------------------
Ran 427 tests in 544.820s

OK
Destroying test database for alias 'default' ('file:memorydb_default?mode=memory&cache=shared')...
⚠  Speech error: run loop already started
⚠  Speech error: run loop already started
⚠  Speech error: run loop already started
exit=0
```
Count of `... FAIL` / `... ERROR` result lines: 0. No OOM kill. The "Traceback" blocks in the log come from rollback tests (`test_bt1_self_serve_completion_rolls_back`, `test_bt2_managed_session_start_rolls_back`) that force an exception on purpose; both end `ok`.

### 2.4 `node --test strength_app/tests/js/*.test.mjs` — exit 0
Full output: `docs/integration_pre_show/4_node.txt`. Summary:
```
1..62
# tests 62
# suites 0
# pass 62
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 476.440502
exit=0
```

### 2.5 `python manage.py export_exercise_targets --check` — exit 0
```
2026-11-20 14:43:46.215990: I tensorflow/core/platform/cpu_feature_guard.cc:210] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
To enable the following instructions: AVX2 FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
exercise_targets.json is fresh
exit=0
```

## 3. Failures

**Failure count: 0 of 427.** Nothing to quote.

## 4. The two failures seen on 0208e84

Neither appeared. Both runs on this branch are green.

- `therapist_app/test_group4.py:116` (`assertIn('Pain >5 last week', metrics['flags'])`) ran and passed here: `therapist_app.test_group4.TherapistProgramBuilderTests.test_dashboard_pain_flag_fires_from_painevent ... ok` (log line 954). It ran right after `TherapistPermissionTests.test_therapist_required_redirects_anonymous`, `..._forbids_non_therapist` and `..._blocks_other_therapist`, and after `strength_app.tests.test_sentry` and `strength_app.tests.test_report_pdf`.
- The second failure's identity is not known to me; I was not given its name. No test failed in this run, so there is nothing to match against.

**Cause: not found.** I have no failing traceback to analyse, so I cannot say what made them fail on 0208e84. Your read (fails in a full run, passes alone) is consistent with order dependence or leaked state, but this run neither confirms nor refutes it: one green run is not proof of a fix. `git diff --name-only main..HEAD` shows no file under `therapist_app/`, so a green result here is not evidence that the branches fixed anything. Possible lead if it recurs: the test is date-window sensitive ("last week" over `PainEvent` rows), so check for time-of-day or timezone dependence; unverified.

## 5. Side effects
- Running the suite rewrites `strength_app/tests/clinical_audit/reports/H2_RESULTS.md` (known, K4 note). I restored it with `git checkout --` in this worktree only, so it is not part of the branch. Pawan's own checkout was not touched.
- `staticfiles/` was generated by `collectstatic` and is not committed.
