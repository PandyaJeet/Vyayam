# VYAYAM — MASTER HANDOFF (fresh Fable session, 2026-06)
**Read this whole file before touching anything. It replaces months of chat context. Written by chat-Claude, verified against the actual code at handoff time: branch `ship-ready-2026-06`, 312 Django + 25 node tests green, check clean.**

---

## 1 · WHAT THIS IS

VYAYAM: a Django 4.2 physiotherapy-principled strength/rehab platform. Solo founder (Pawan, BPT student — physio-literate, self-taught coder). B2B2C: a therapist prescribes; a managed patient executes at home with MediaPipe camera form-coaching; the system reports back like a therapist watched the session. Also a self-serve tier and a football/athlete tier (training-readiness framing ONLY — never clinical).

Two apps: `strength_app` (patient flows, camera/ghost system, football, engine) + `therapist_app` (console, builder, alerts, reports). The camera showpiece is `v1_exercise_execute.html` (6,059 lines at handoff — use live line numbers, it grows) — squat is the flagship demo.

**State:** every build cycle to date is DONE and pushed — deep audit (C1–C15), ship-readiness (all 15 SB clinical blockers closed, 112 camera / 176 guided exercises, football methodology doc), pitch polish (G0–F: pain tiers, notes, opt-in demo, spoken tempo, voice), security hardening (rate-limited pain endpoint + alert dedupe, hashed reset tokens), and the report/coaching cycle (R1–R5: per-rep capture, immutable daily session reports rendered identically for both sides, humanized coaching). Key docs live in repo root + `docs/` — `SECURITY_AUDIT.md`, `DEPLOY_CHECKLIST.md`, `PITCH_SMOKE.md`, `docs/REPORT_AND_COACHING.md`, `docs/FOOTBALL_METHODS.md`, `docs/CV_ARCHITECTURE.md`.

**Critical caveat:** Pawan has NOT yet run the on-device test day (`MASTER_TEST_DAY.md`). The R4 coaching layer is live and untested on a real camera. Therefore: **freeze all feel/behavior changes to the camera template and coaching until his test day passes** — bug fixes with evidence only. Do not add to the untested surface.

## 2 · STANDING RULES (non-negotiable, learned the hard way)
1. **Trust code, not summaries.** Two previous audits contained "fixes" that were broken or never shipped. Verify every claim at file:line before relying on it — including claims in this file.
2. **Verify every find-string** against the live file before editing; if the anchor drifted, reconcile and report — never force.
3. **Anything entering inline JS**: quoted string + `|escapejs`, parse in JS. Bare `{{ }}` in a JS slot killed every button on a page once (em-dash tempo). The `test_g0_inline_js_integrity` harness enforces this — keep it green, extend it to new pages.
4. **Detection boundary:** you may touch cue arbitration, phrasing, coloring, capture, tempo speech. You may NOT touch landmark math, angle computation, the rep state machine internals, or MediaPipe setup.
5. **Git discipline:** checkpoint commit before each phase; one commit per logical fix (`fix(<tag>): ...`); push at phase ends; never commit `db.sqlite3`, `staticfiles/`, `media/`, `.env*`. Canonical repo = the working directory you're in; the sibling folders are archives.
6. **After every phase:** `manage.py check` clean + full suite green (312+ Django, 25 node via `node --test strength_app/tests/js/*.test.mjs`). `collectstatic` before running the suite or camera pages 500 (manifest storage).
7. **Clinical integrity:** PainEvent is the only pain source in reports · camera vs guided always labeled, rep-level data never fabricated for guided work · tempo never affects form color · amber-first, red = safety cues only · no ACWR, no "RSI" claims, no diagnosis language anywhere · athlete tier says training-readiness, never clinical/medical · patient-facing clinical wording changes get flagged for Pawan's physio mentor.
8. **One phase per run.** End every phase with exact manual browser steps for Pawan, appended to `MASTER_TEST_DAY.md`. NOTE: that file was never committed — creating it is one of this mission's deliverables (see §3); Pawan holds an uncommitted draft he may hand you — if he does, verify it against reality and commit it rather than rewriting.
9. Pawan's style: terse, direct, hates fluff. Give him decisions and evidence, not essays.

## 3 · THE MISSION: GRAND CODEBASE EXAMINATION
Take your time — hours are fine. Examine the ENTIRE codebase and repair what you find. Pawan has tmux: **spawn parallel agents for the audit phase** (read-only), then apply fixes from the main session alone (one writer — no merge chaos). Suggested split:

**Agent A — Security.** Re-verify the full `SECURITY_AUDIT.md` against current code, then sweep everything added since: the R1 endpoints (`set-log/`, `rest-event/` — rate limits, clamps, IDOR), report views (both-direction IDOR), admin exposure, session settings, headers/CSP status, `check --deploy` under prod env, DEBUG=False route smoke, `pip-audit`, secrets grep of tree AND `git log -p`, G0 harness across every page. Output: findings table with severity + file:line.

**Agent B — Exercise system.** Re-run the H2 ideal-trajectory harness across all modules; registry integrity; `exercise_targets.json` freshness (regenerate `export_exercise_targets` and diff — must be byte-identical); CUE_TEXT ↔ `coach_core.js` registry sync (a stated forever-rule); content/tags/equipment coverage tests; the camera-vs-guided split still honest. Output: pass/fail tables + drift list.

**Agent C — Repo hygiene (the pile-up).** The root has accumulated audit-era files: `GROUP1–6_AUDIT.md`, `AUDIT_FIXES_CHANGELOG.md`, `DEEP_AUDIT_REPORT.md`, `SHIP_READY_REPORT.md`, `DECISIONS_NEEDED.md`, old reports under `strength_app/tests/clinical_audit/reports/`, possibly stray zips/backups/`.DS_Store`/`__pycache__`/stale sqlite copies. Produce a three-column table — **KEEP (live) / ARCHIVE (historical) / DELETE (waste)** — then execute: `git mv` historical docs to `docs/archive/` (history preserved), delete only unambiguous waste, and add missing `.gitignore` entries. Rules: never delete migrations, tests, or any doc with unique content; `DECISIONS_NEEDED.md` gets resolved-items pruned, open items kept; live set stays at root (`SECURITY_AUDIT`, `DEPLOY_CHECKLIST`, `PITCH_SMOKE`, `MASTER_TEST_DAY`, `README`). Also: dead-code candidates (the legacy `strength_app/backend/` engine, the fenced `analyze_frame` view, dormant `cues:{}` strings, anything `grep` proves unreferenced) — list with proof, remove in separate single-purpose commits so any one is trivially revertable.

**Expected findings your sweep must not miss (pre-verified by chat-Claude):** (a) `mediapipe==0.10.33` in requirements.txt is imported ONLY by `exercise_system/core/pose_analyzer.py`, which serves only the unrouted `analyze_frame` view — dead weight in the WEB deploy (it's a huge wheel). But do NOT just delete: the Python exercise modules are also the therapist desktop-runner story, which needs mediapipe at desktop runtime. Correct fix: drop it from the web `requirements.txt`, move to a `requirements-desktop.txt` extra, document in README. (b) `pyttsx3`'s optional-import prints a "⚠️ not installed" warning on EVERY manage.py command (`voice_coach_v2.py:17`) — convert to `logging.debug` or a lazy first-use warning.

**Agent D — Engine & flow regression sweep.** Fresh eyes over `v1_prescription_engine`, `v1_session_views`, `v1_therapist_session_views`, `report_builder`, `therapist_app/views` — silent-except policy still held, input clamps still universal, no TODO rot, README still matches reality, `requirements.txt` pinned and minimal.

**Then, main session:** consolidate into `CODEBASE_HEALTH_2026-06.md` (one findings ledger, severity-ordered), fix S1/S2 items immediately (evidence + test each), batch S3/S4, run the full gate (check · suite · node · collectstatic · DEBUG=False smoke · `check --deploy`), commit in clean units, push.

**Deliverable — `MASTER_TEST_DAY.md` (repo root, committed):** the consolidated device-test walk that was never committed. Structure: Parts A–F (A: environment prep incl. migrate + collectstatic + fresh server; B: PITCH_SMOKE.md steps 1–23; C: the deliberately-sloppy R4 coaching session; D: /admin data verification of capture rows; E: report reading both sides + print; F: final squat + console pass), seeded from PITCH_SMOKE.md plus every phase-end manual step from the G0–F and R1–R5 reports. If Pawan supplies his uncommitted draft, verify it against current reality and commit that instead of rewriting. Every future phase appends its manual steps here.

**Last deliverable — the exercise-addition playbook (`docs/ADDING_AN_EXERCISE.md`):** Pawan will add new exercises in THIS chat next. Write the exact end-to-end recipe with file paths and verification commands: Python module (or content-only for guided) → registry → `export_exercise_targets` regen → content/equipment/tags entries → therapist catalog entry → camera-vs-guided decision rule (camera ONLY after the filming protocol passes; default guided) → the tests that must go green → the `EXERCISE_TEST_CHECKLIST.md` row. Make it so adding one exercise is a 30-minute mechanical task, not archaeology.

## 4 · AFTER THE EXAMINATION
Pawan's own queue (do not do these for him): the `MASTER_TEST_DAY.md` device walk · physio-mentor sign-off on the cue table · filming the camera exercises · SMTP + deploy env vars · GitHub default branch → `ship-ready-2026-06`. Fable's deferred queue (build only when Pawan says): PDF report export · per-side capture (unlocks the dormant asymmetry pattern) · athlete-flow report parity · stale-session partial reports · per-set RPE · strict-mode toggle · weekly roll-up · Tailwind local + CSP enforce · merge to main.

Now: baseline first (`migrate`, `collectstatic`, full suite — confirm the 312+25 green yourself), then launch the agents.
