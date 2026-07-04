# VYAYAM — HANDOFF: PITCH-READY POLISH (Phases G0, G1, C, D, E, F)
**For Claude Code (Fable). Prepared 2026-06 by chat-Claude after direct code verification of the post-B2 snapshot. A major pitch is imminent — priority is: nothing broken on screen, pain pipeline provably correct, then the experience polish.**

---

## 0. STATE (verified against code, not summaries)

Done and verified — do NOT rebuild:
- Pain pipeline (Phases 1–3, B1, B2): `therapist_session_report_pain(idx)` + `_record_pain()` in `v1_therapist_session_views.py`. Server tiers are **type-blind severity**: `<= threshold` → PainEvent only (silent report); `threshold < sev < 8` → skip + system TherapistMessage; `>= 8` → pause + TherapistMessage + **Alert**. Both screens now POST to this one endpoint (guided modal; camera `submitPain` LIBRARY_MODE branch ends with `return;` before the athlete fetch — double-POST guard confirmed at ~:5139).
- Phase A: TEMPO_PARTS + all camera-screen JS constants are quoted/escaped (verified block at `v1_exercise_execute.html:440–471` — clean).
- `PrescriptionItem.notes` exists, `save_program` persists it, guided screen (`therapist_session_exercise.html:46`) + today list (`therapist_session_today.html:51`) render it. **The builder input box does not exist** (`grep -c 'data-k="notes"' patient_detail.html` → 0) and **the camera screen does not render the note at all**.
- VisitNote (T7) is live: private dated therapist-only note.
- Baseline: `manage.py check` clean, **251 tests OK**. Re-confirm before starting.

## Standing rules (all seven from the previous handoff apply verbatim)
Verify every find-string · quoted+`|escapejs` for anything entering inline JS · never touch pose-detection/form-scoring/MediaPipe · check + full test suite after every phase · end each phase with exact manual browser steps for Pawan · clinical wording flagged for the physio mentor · **one phase per run**.
Additional for this cycle: **squat's camera coach is the pitch showpiece** — every phase that edits `v1_exercise_execute.html` ends with "re-test squat" in the manual steps. If a phase risks detection in any way, STOP and report instead.

Sequencing: **G0 → G1 → C → D → E → F**. G0 and G1 are P0 (pitch-killers); C is 15 minutes; D/E/F are the experience.

---

## PHASE G0 — the dead-buttons bug + a permanent harness for its whole class (P0)

**Report from Pawan:** testing as Anika Patel (`9000000001 / patient`), *after the third exercise no button worked*. He has a console screenshot — **ask him to paste the console error text into this session before you start**; it may shortcut everything. Ambiguity to resolve while reproducing: "after the third exercise" = ON exercise #3's page, or on the page that loads AFTER finishing #3 (i.e. #4 / a transition page). Note his live protocol has Glute Bridge at #3, which differs from the seed order (glute bridge is #1 in `seed_therapist_demo.py:121`) — the therapist republished, so index-specific behavior matters more than exercise identity.

**Step 1 — build the harness (this is the durable deliverable):**
A test that walks a managed patient's session and syntax-checks every inline script of every rendered page:
1. Seed via `seed_therapist_demo` in the test DB (or create an equivalent 5-item published prescription: make sure it includes tempo values `'3-1-1'`, `'—'`, `'Hold'`, a note containing an apostrophe + `>` (e.g. `Don't rush. Stop if pain >3.`), and at least one camera exercise + one guided exercise — the hostile inputs of record).
2. Log the test client in as the patient; GET, in order: today page → each exercise page idx 0..4 (both screens will occur naturally) → the complete page. Also GET the pause page (`v1_pain_stop` route used by the pipeline).
3. For each response, extract every `<script>…</script>` block that has no `src`, write to a temp `.js` file, wrap bare blocks in `(function(){…})` ONLY if needed, and run **`node --check`** on each (node exists — the CV tests use it). Any syntax error = test failure printing the page URL + offending line.
4. Add the same walk for a coach + a self-serve patient's main pages (dashboard, session overview, one execute page) — cheap, same loop.
Name it `test_g0_inline_js_integrity.py`. This permanently kills the Phase-A bug class.

**Step 2 — reproduce and fix.** Run the harness; whatever page/line it flags for the idx-2/idx-3 region is almost certainly Pawan's bug. If the harness passes but his console text indicates a *runtime* (not syntax) error — e.g. a null element lookup that only exists on some screens, a function defined in one template variant but called in the shared footer — chase that: diff what's conditionally rendered between the exercise variants (guided vs camera vs hold-type), find the unconditional listener/call, and guard it. Known thin ice you should harden while there (even if not the culprit): `therapist_session_exercise.html:97–98` inject `{{ item.sets }}` / `{{ item.rest_seconds }}` bare — they're IntegerFields today, but wrap them in the quoted-string + parseInt pattern anyway (rule 2; one builder change away from breaking).

**Acceptance:** harness in the suite and green; the specific dead-button repro fixed; `check` clean; 251+new tests OK.
**Manual for Pawan:** log in as the managed patient, run the FULL protocol start→finish, every exercise, pressing every button (Start camera / Set done / Report pain / Skip / Done / Finish), console open. Then squat re-test.

---

## PHASE G1 — pain pipeline: severity beats type everywhere + prove the alert (P0)

Pawan's confirmed spec (matches the managed-flow server already): **≤ threshold → report only · above-threshold to 7 → auto message · 8–10 → Alert, ALWAYS, regardless of pain type.** Clinical rationale for the record: low/moderate burning-or-aching is normal exertional/metabolite discomfort, but *severe* "burning" can be neuropathic (nerve) pain and true exertional burn essentially never rates 9–10 — so type-based leniency must cap out below 8. Three pieces:

**G1a — athlete/self-serve parity.** The camera screen's ATHLETE (non-library) branch still uses client `computeGuidance` (`v1_exercise_execute.html:5084`) where `aching` at ANY severity → `reduce_volume`, never stop. Fix both layers:
- Server (`v1_save_exercise_result`, `v1_session_views.py` ~746–761): the session-stop currently requires `pain_severity >= 8 AND pain_action == 'stop'` — but computeGuidance never sends `'stop'` for aching, so a burning 10 can't stop the session. Change: `pain_severity >= 8` alone → `v1_pain_stop` (server decides; ignore client action for the stop tier). Keep the existing DA-F2 sharp-or-≥7 same-pattern skip as is.
- Client `computeGuidance`: add a top guard — any type with `severity >= 8` → stop message ("Stop for today. Pain this severe — whatever the type — is a signal to rest and, if it repeats, see a physiotherapist.") with `action='stop'`. Aching keeps its reduce-volume coaching for 6–7 only. Keep all existing education copy below 8 (it's clinically sound); flag the new wording for the physio mentor.

**G1b — kill the stale client flash on the managed camera screen.** Known B2 leftover: LIBRARY_MODE briefly shows the OLD `computeGuidance` text before the server responds. Replace: on submit show a neutral "Recording…" state, then render the message/action FROM THE SERVER RESPONSE (`action` ∈ continue/skip/pause + a `guidance` string you add to the JsonResponse — write the three patient-facing strings server-side in `therapist_session_report_pain`, mirroring `_record_pain`'s tiers, so client and chat can never disagree). Do not touch the athlete branch's local display (it stays client-decided by design).

**G1c — prove the alert end-to-end, permanently.** New tests: managed patient POSTs severity 4 (threshold 5) → PainEvent only, no message, no Alert; severity 6 → +system TherapistMessage, no Alert; severity 8 with `pain_type='aching'` → paused + message + **Alert row exists and appears in the therapist alerts inbox view** (GET the inbox as the therapist, assert the body text present). This encodes "8–10 alert ALWAYS, even burning" so Pawan's missing-alert experience can never silently return.

**Acceptance:** the three tests green; athlete burning-10 stops server-side; managed camera screen shows server-decided guidance only. Manual: as managed patient on a camera exercise report aching 8 → session pauses, therapist chat shows the ⚠ system message, therapist alerts inbox shows it; as a SELF-SERVE patient report aching 9 → session stops. Squat re-test (this touches the camera template).

---

## PHASE C — therapist note: input in the builder + visible on the camera screen

**C1 (the original tiny spec).** In `therapist_app/templates/therapist_app/patient_detail.html`, in the builder row immediately AFTER the "Usual pain" input span (`data-k="pain_stop_threshold"`), add:
`<span class="t-presc-field"><span class="k">Note:</span><input data-k="notes" class="w-wide" value="${esc(item.notes || '')}" placeholder="cue shown to patient" /></span>`
Confirm the live row markup first and anchor on the pain_stop_threshold line; save logic already exists — add ONLY the input. Verify `grep -c 'data-k="notes"'` == 1.

**C2 (gap found in review — the note is invisible exactly where it matters most).** The camera screen never shows the note. In `_render_v2_ghost()` add `'therapist_note': item.notes` to the context; in `v1_exercise_execute.html` render it as plain escaped HTML (a small strip near the exercise title / under the set tracker): `{% if therapist_note %}<div class="therapist-note"><strong>Therapist note:</strong> {{ therapist_note }}</div>{% endif %}` — **HTML context only, never into a JS block**. Style consistent with the guided screen's note.

**Acceptance:** builder shows Note box → type, Publish → patient sees it on the today list, the guided screen, AND the camera screen. Tests: save_program round-trips notes (may exist — extend), camera page response contains the note text escaped. Manual: exactly Pawan's flow — add "Squeeze top 2s" to Glute Bridge, publish, open as patient, see it on the exercise itself. Squat re-test (template touched).

---

## PHASE D — demo becomes opt-in ("Show demo" button)

Pawan's words: starting an exercise (or an assessment) should go STRAIGHT in — no forced demo. A "Show demo" button (default name `Show demo`, single easily-renamed string) that, when pressed, runs: form guidance (how to stand / key form points) → the video/gif if one exists → the whole-body-in-frame check.

**Investigate first (read, don't assume):** in `v1_exercise_execute.html` and the guided template, map the current entry sequence — where the demo/calibration/"how to stand"/framing steps trigger relative to `startCamera` and scoring. Write the findings as a comment block or in your phase report BEFORE editing.

**Implement:**
- Default path: entering an exercise lands on the working view (set tracker / camera ready) with no forced sequence. Applies to exercises AND assessment mode (he explicitly said "when I start assessment").
- "Show demo" runs guidance → media → framing check, then returns to the working view.
- **Scoring must survive skipping the demo.** If the camera pipeline needs framing/calibration to score, that step belongs to the SCORING path (runs on Start camera / first detection), not gated behind the demo button. State your resolution explicitly in the report.

**Acceptance:** camera exercise → straight in, button present, demo plays on demand, scoring works with demo skipped; guided exercise → same minus camera; assessment → same. Manual steps + squat re-test mandatory (this is deep in the showpiece template — smallest possible diff, no detection edits).

---

## PHASE E — spoken + visual tempo guidance (the coach, not a robot)

Tempo like `3-1-2-0` (down-hold-up-pause seconds) should be GUIDED: speak the phase, count it down on screen. `TEMPO_PARTS` is already a sanitized 4-int array — read its current uses first (there's an existing tempo guide + video-rate sync + counter).

**Implement (per rep):** for each phase with duration > 0: speak the cue once ("slowly down" / "hold" / "up" — natural phrasing, NOT a tick per second), show a countdown for that phase's seconds top-right in a distinct colour — eccentric blue, hold amber, concentric green. Phase of 0 s is skipped entirely. Tempo blank/0-0-0-0 → no tempo UI, exercise unchanged. Numbers count 3-2-1 visually; speech is the phase word (optionally the final "1" if it feels natural — your call, keep it un-spammy).

**Acceptance:** 3-1-2-0 → "down" + blue 3-2-1, "up" + green 2-1, no hold; 3-1-2 (4th part absent → 0) same plus amber "hold" 1. No tempo → silent. Never crashes on legacy `'—'`/`'Hold'` (rides the sanitized parts). Manual steps + squat re-test.

---

## PHASE F — friendlier voice

**Part 1 (now, free):** wherever speech is produced, pick the best available system voice — prefer names containing `Google`, `Natural`, `Enhanced`, `Samantha`, `Ava` (in that order of preference), matching the page language; fall back to default. Rate ~0.95, pitch 1.0. Voices load async in some browsers — handle `onvoiceschanged`.

**Part 2 (scaffold only):** the coaching vocabulary is a fixed ~30-clip set (phase cues, numbers, short encouragements). Build the phrase→file map + a player that plays `static/strength_app/audio/coach/<key>.mp3` when present and falls back to speechSynthesis when absent. **Do NOT fabricate audio files** — generating them (ElevenLabs / Google Neural2) needs Pawan's account; list the exact clip filenames he must produce in your phase report. Ship Part 2 dormant-but-wired.

**Acceptance:** Part 1 — better voice on any Chrome/Android device, graceful default elsewhere. Part 2 — drop one test mp3 in, that cue plays the file; remove it, falls back. Manual steps; squat re-test if the template changed.

---

## PARKED (explicitly, so it isn't picked up by accident)
- "Code some exercises too" (expanding the 112-exercise camera set): **frozen until after the pitch.** New camera exercises change detection surface — exactly what must stay stable now. Post-pitch: per-exercise via `export_exercise_targets` + the filming protocol, one at a time.
- The known-deferred items (DOMS-vs-injury triage, detailed report, rest/pause buttons) stay deferred.

## FINAL — pitch smoke list (produce as `PITCH_SMOKE.md` after Phase F)
A one-page ordered manual walk for Pawan the night before: therapist login → edit + publish Anika's program (with a note + a tempo + a usual-pain value) → patient login → full session start-to-finish touching every button → pain report at 4 / 6 / 8 verifying report / message / alert → squat camera coach demo → therapist inbox review. Every step with the expected result on screen.

One phase per run. Verify, report, hand Pawan his browser steps, wait.
