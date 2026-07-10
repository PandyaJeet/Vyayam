# CODEBASE HEALTH — Final Examination (2026-07 cycle, executed 2026-07-10)

Branch `ship-ready-2026-06`. Five parallel read-only audit agents (A clinical
content, B performance & data integrity, C deep JS, D security round 2,
E test-coverage gaps) + one main-session finding. Domains chosen to NOT
overlap the 2026-06 grand examination; every finding carries file:line +
proof in the agent reports (`/tmp/vyayam_final/AGENT_{A,B,C,D,E}_FINDINGS.md`,
transient — substance consolidated here). Baseline at start: 316 Django +
32 node tests green, export --check fresh, check clean (commit c90f113).

Severity: S1 data-loss/clinical-integrity break · S2 wrong behavior or
locked-rule violation · S3 degradation/risk · S4 polish.
Status legend: **FIXED** <hash> · **BATCHED** <hash> (S3/S4 batch commits) ·
**MENTOR** (docs/MENTOR_REVIEW_QUEUE.md — wording is the physio mentor's call) ·
**DEFERRED** (reason inline) · **DOCUMENTED** (accepted + written down).

## Commit map (Phase 2 fixes, 2026-07-10)

| Commit | Findings |
|--------|----------|
| 92b367e | B-X1 (S1) |
| 7de6667 | A1, A2 |
| 5920a93 | A4 (supersedes C5) |
| db05455 | A5 (label) |
| b0b9284 | B-X2 |
| afb761f | B-X3 + B-N3 |
| 2155228 | B-N1, B-N2 (dashboard 38→constant queries @8 patients) |
| 856fd47 | B-T1, B-T2 |
| 2449999 | D1 |
| 1bf6056 | C1, C2, C3, C4, C12 |
| 22273be | C6 |
| 1887c3e | S3 batch: B-D1, B-D2, B-I1, B-T3, B-T4, B-N4, C7, C8, C9, C10, C11 |
| 0205f48 | E9, E10 (partial), E11 |
| ca35156 | E1 (partial), E2, E3 (P22), E4, E5 |
| cc0bbcb | S4 batch: A12, A13, B-P1/P2, C13, C15-C22 (C14 documented), D2-D5 docs, E7, E12, E15 |

## Findings ledger (severity-ordered)

| ID | Sev | file:line (at finding time) | Finding | Status |
|----|-----|------------------------------|---------|--------|
| B-X1 | S1 | strength_app/views.py:1548 | Patient-reachable `delete_account` CASCADE-destroys all generated SessionReports + PainEvent/RedFlagEvent audit trails for therapist-managed patients (reports are clinically immutable) | **FIXED** — managed patients now blocked from self-serve delete (route via therapist); PROTECT-vs-data-rights policy → MENTOR queue |
| A1 | S2 | exercise_content_gap_fill.py:3268 | Banned term "RSI" in athlete content string (`'Build RSI by minimizing ground contact time'`); latent field but locked rule 2 is absolute | **FIXED** — reworded to "springiness"; RSI/ACWR guard test extended to both content files |
| A2 | S2 | football_assessment.html:21 | Live athlete page claims the battery "measure[s] … reactive strength" — contradicts R2-W2-1 (app metric cannot measure RSI without force plate) | **FIXED** — "reactivity" |
| A3 | S2 | therapist_app/exercise_catalog.py:370 | "ACL injury-prevention drill" renders to patients (prevention claim) | **MENTOR** (single_leg_landing description) |
| A4 | S2 | exercise_execute.html:451,565 + views.py:946 + urls.py:128,152 | Legacy camera flow still routed: red-for-poor-form palette + squat-derived scoring applied to EVERY exercise; results stored + shown as "Form Score" (same defect class as closed C1/D5, client-side sibling) | **FIXED** — legacy `dashboard`/`daily_workout`/`execute_exercise` redirect to their v1 equivalents (v1 is the login landing since R2); fabricated scoring unreachable; test added |
| A5 | S2 | _session_report.html:83,90 + report_builder.py:227-234 | Plyo camera sets rendered with generic Form% + `camera-tracked` label — locked rule says plyo camera = landing-check only, labeled as such | **FIXED (label)** — plyo sets now labeled `camera (landing checks)` in report mode chip; Form% suppression question → MENTOR |
| A6 | S2 | exercise_content_gap_fill.py:2861,2872,2874 | heel_drop content tells patients tendon pain is "safe and therapeutic" + "gold standard treatment for Achilles tendinopathy" (conflicts pain protocol + rule 1); latent (dead `*_en` keys) | **MENTOR** — blocks A8 |
| C1 | S2 | v1_exercise_execute.html:6222,6307 | Assessment save/skip POST without `X-CSRFToken` → 403 → silent score loss + fast-forward | **FIXED** + template-render test |
| C2 | S2 | v1_exercise_execute.html:6149 | Managed pain report: fetch failure silently closes modal — patient believes pain recorded, no PainEvent | **FIXED** — visible retry/"tell your therapist" state; modal no longer closes on failure |
| C3 | S2 | v1_exercise_execute.html:6180 | Self-serve pain fetch chain has no `.catch` — modal hangs forever on network error | **FIXED** — same visible-failure handling |
| C4 | S2 | v1_exercise_execute.html:6251 (+:494) | `Array("3")` — camera-failed manual path records 1 set instead of prescribed 3 | **FIXED** — PRESCRIBED_SETS/REPS/REST parseInt'd at declaration (also fixes C12) |
| C5 | S2 | exercise_execute.html:373-380 | Legacy execute page: bare `{{ exercise_name }}` + unquoted ints in script | **SUPERSEDED by A4** — page unreachable (redirects); template untouched by design |
| C6 | S2 | onboarding_strength_test_execute.html:202 + football_assessment_execute.html:119 | `request.GET` side/variant rendered bare into JS strings — `?side=%0A` kills the page | **FIXED** — `\|escapejs` + server-side whitelist; test |
| B-X2 | S2 | therapist_app/models.py:263,391-397 | No PROTECT on report chain: admin delete of Prescription/link cascades to SessionReports | **FIXED** — SessionReport.session_log/link/patient → on_delete=PROTECT (+migration); admin delete of a report-bearing chain now raises ProtectedError |
| B-N1 | S2 | therapist_app/views.py:312 | Therapist dashboard N+1 (~4 queries/patient card) | **FIXED** — batched maps; query-ceiling test; before/after in commit msg |
| B-N2 | S2 | therapist_app/views.py:472,486,489 | patient_list runs `_link_card` 3× per link | **FIXED** — single pass (same commit as B-N1) |
| B-T1 | S2 | v1_session_views.py:980-1056 | Self-serve completion multi-row write not atomic | **FIXED** — transaction.atomic + rollback test |
| B-T2 | S2 | v1_therapist_session_views.py:204-214 | SessionLog+items creation not atomic — orphan partial session on failure | **FIXED** — transaction.atomic + rollback test |
| B-X3 | S2 | therapist_app/views.py:793 | `'messages'` ctx key shadows flash framework — chat renders as banners; reset temp-password flash never shown | **FIXED** — `chat_messages` + template refs + test |
| D1 | S2 | vyayam_project/urls.py:12 | `/admin/login/` unthrottled (all app logins are 5/300s) | **FIXED** — admin login wrapped with rate_limit 5/300s + 429 test |
| E1 | S2 | v1_football_views.py:204 | Football scoring + readiness engine: zero assertions | **PARTIAL** — threshold-band edge tests added; full readiness/reassessment suite deferred (ledger E1 note) |
| E2 | S2 | v1_safety_logic.py:172 | Working-set red-flag exclusion untested | **FIXED (tests)** — red-flagged patient session contains no excluded ID; substitution path asserted |
| E3 | S2 | v1_prescription_engine.py:885 | P21–P32 athlete principle blocks unasserted (incl. P22 plyo gating) | **PARTIAL** — P22 gate-block test added; remaining principles deferred to next test cycle |
| E4 | S2 | v1_safety_logic.py:149 | `apply_female_acl_prevention` zero tests | **FIXED (tests)** |
| E5 | S2 | backend/gate_test_system.py:90,147 | 5-gate classify_capability/determine_prescription never asserted | **FIXED (tests)** — boundary matrix |
| E6 | S2 | v1_safety_logic.py (12 functions) | Dosing/progression modifier stack zero direct tests | **DEFERRED** — 16-function suite is its own cycle; highest-risk trio covered via E2/E4/E5 |
| A7 | S3 | gap_fill.py:2186,2252 + exercise_content.py:143 | Latent injury-risk/condition-name strings in `language_*` fields | **MENTOR** (batch with A1/A6 pass) |
| A8 | S3 | views.py:1360, v1_therapist_session_views.py:317, v1_session_views.py:1333 | Three views read `*_en` content keys that exist in ZERO entries — instructions/cues silently empty on therapist ghost + library flows (found independently by main session + Agent A) | **DEFERRED-BLOCKED on A6/A7 mentor pass** — the one-line key fix would make un-reviewed gap_fill wording live. docs/ADDING_AN_EXERCISE.md step 6 corrected to document the REAL keys |
| A9 | S3 | v1_therapist_session_views.py:878-886,929 + pdf_generator.py:175 | Pain shown on progress page + weekly PDF from SessionLogItem.pain/overall_pain, not PainEvent — rule-scope question (build_report itself is clean) | **MENTOR/Pawan ruling** — sources are direct patient-entered ratings, nothing fabricated; queue item states the question |
| B-D1 | S3 | therapist_app/models.py:369-371 | ExerciseSetLog idempotency claim has no unique constraint | **BATCHED** — UniqueConstraint(session_log, exercise_id, set_number) + dedupe migration |
| B-D2 | S3 | report_builder.py:795-807 | None profile → IntegrityError misread as race → report silently never generated | **BATCHED** — guard + logger.error |
| B-I1 | S3 | strength_app/models.py:1448-1461 | PainEvent missing (patient, created_at) index | **BATCHED** — index migration |
| B-T3 | S3 | v1_therapist_session_views.py:432-456 | `_record_pain` PainEvent+message+alert non-atomic | **BATCHED** — transaction.atomic |
| B-T4 | S3 | therapist_app/views.py:420-440 | copy_previous_week partial-copy window | **BATCHED** — transaction.atomic |
| B-N3 | S3 | therapist_app/views.py:736 | Messages tab unbounded + 1 query/message | **BATCHED** — select_related('sender__therapist') + last-200 slice |
| B-D3 | S3 | therapist_app/views.py:959 | Republish delete-all-recreate SET_NULLs historical prescription_item pointers | **DEFERRED** — diff-update of items is a publish-flow behavior change; needs its own test pass. Noted for next cycle |
| C7 | S3 | v1_exercise_execute.html:5962 | restInterval overwritten without clear — twin countdowns | **BATCHED** — clearInterval at startRest top |
| C8 | S3 | v1_exercise_execute.html:658 | startCamera no double-start guard → 2 streams, 2 Pose loops, double rep advance | **BATCHED** — in-flight guard |
| C9 | S3 | v1_exercise_execute.html (absence) | Mid-session camera loss indistinguishable from occlusion; session frozen | **BATCHED** — track `ended` handler → existing honest "Camera not available" fallback |
| C10 | S3 | v1_exercise_execute.html:5762 | form_score diluted by idle-frame `matchScore \|\| 50` pushes in non-rep states | **BATCHED** — push only in coaching states; explicit number check |
| C11 | S3 | v1_exercise_execute.html:3781,6395 | Hold timers tick while tab hidden (rAF frozen at last good score) — inflated holds/assessments | **BATCHED** — gated on `!document.hidden` |
| C12 | S3 | v1_exercise_execute.html:2739 | `count === targetReps` number-vs-string — set-completion speech dead | **FIXED with C4** (parseInt) |
| E7 | S3 | tests/clinical_audit/oracles/* | Clinical-audit harness is NotImplementedError stubs — looks like coverage, isn't | **DOCUMENTED** — README note in clinical_audit/ marking scaffolding status |
| E8 | S3 | urls.py (63 views) | 63/128 routed views zero test references | **PARTIAL** — E9/E10/E15 close the priority rows; sweep deferred |
| E9 | S3 | therapist_app/views.py:1080 + strength_app/views.py:1233 | ProgressReport download/view ownership gates untested (IDOR class) | **FIXED (tests)** — foreign therapist/patient → 404 |
| E10 | S3 | test_g0_inline_js_integrity.py | G0 misses 6 camera-template entry routes | **PARTIAL** — G0 extended to football assessment execute + onboarding strength-test execute + gate/conditioning/stretch pages (non-DEBUG routes); legacy exercise_execute superseded by A4 |
| E11 | S3 | therapist_app/exercise_catalog.py | No catalog↔registry integrity test; B1-class drift would ship silently | **FIXED (tests)** — every non-empty v2_exercise_key resolves in registry + targets artifact |
| A10 | S4 | football_assessment_results.html:102 | "…before explosive jump training is safe for your tendons" | **MENTOR** |
| A11 | S4 | v1_warmup.html:195 | "Skipping warm-up increases injury risk" | **MENTOR** |
| A12 | S4 | football_nordic_camera_test.html:32 | Dev-tuning copy ("tell Claude…") on athlete-facing page | **BATCHED** — removed |
| A13 | S4 | v1_progress.html:117-205 | Dead fabricated-data fallback rows (1240 XP / GOLD II) | **BATCHED** — deleted |
| A14 | S4 | v1_session_detail.html:39 | Red text for form_score<55 on history card — rule-7 scope question (stats vs live coaching) | **MENTOR** |
| B-P1/P2 | S4 | therapist_app/views.py:525,738 + strength_app/views.py:1095 | Unbounded report lists | **BATCHED** — [:100] slices (volumes are weekly; Paginator when needed) |
| B-N4 | S4 | report_builder.py:634-636 | items.all() run twice per report | **BATCHED** — single query |
| B-T5 | S4 | therapist_app/views.py:583-609 | invite/accept non-atomic (dev-mode flows) | **DEFERRED** — wrap when flows leave dev-mode |
| B-I2 | S4 | therapist_app/models.py:259 | SessionLog (link, started_at) index absent | **DEFERRED** — per-link volumes small |
| C13 | S4 | v1_exercise_execute.html (absence) | No pagehide teardown (camera+TTS run backgrounded) | **BATCHED** — pagehide stops tracks + TTS |
| C14 | S4 | v1_exercise_execute.html:4248,6423 | max_reps counter doubly dead (unreachable landmine) | **DEFERRED** — unreachable (server routes max_reps elsewhere); delete with the next template cleanup, documented here |
| C15 | S4 | v1_exercise_execute.html:6448 | `window.VoiceCoach` guard always false — completion speech dead | **BATCHED** — guard fixed |
| C16 | S4 | voice_core.js:147 + template:5597 | play() promises unhandled (autoplay rejection) | **BATCHED** — .catch handlers |
| C17 | S4 | v1_exercise_execute.html:3501 | voiceschanged re-init queues warmup utterance repeatedly | **BATCHED** — handler removed (voice_core owns re-pick) |
| C18/E14 | S4 | static js/exercise-analyzer.js | 510-line dead static file shipped every deploy | **BATCHED** — deleted (git history keeps it) |
| C19 | S4 | 8 templates (sweep list in Agent C report) | Bare number-context `{{ }}` in scripts — one None from a dead page | **BATCHED** — mechanical escapejs/quote+parseInt pass on non-legacy templates |
| C20 | S4 | v1_exercise_execute.html:3329 | SquatFaults heel baseline never resets (session-lifetime min) → false heel-rise ambers after reposition | **BATCHED** — reset at set start (cue layer, boundary-safe) |
| C21 | S4 | v1_exercise_execute.html:543,6421,670 | VYAYAM_DEBUG=true in prod; uncleared 200ms poll; raw-exception alert() at patients | **BATCHED** — debug off, poll cleared, alert → fallback card |
| C22 | S4 | v1_exercise_execute.html:2334-2496 | EXERCISE_TEMPLATE_MAP triple-defines 5 plyo keys with conflicting values (correct only by ordering luck) | **BATCHED** — deduped (legacy fallback map only) |
| D2 | S3 | requirements.txt | Transitive deps unpinned (no lockfile) | **DOCUMENTED** — DEPLOY_CHECKLIST + SECURITY_AUDIT row; lockfile is a deploy-pipeline task |
| D3 | S4 | transitive tree | pillow/protobuf/fonttools CVEs in transitive closure, reachability LOW | **DOCUMENTED** — SECURITY_AUDIT row (accept-and-document per audit brief) |
| D4 | S4 | strength_app/middleware.py:16 | CSP report-only + 'unsafe-inline' (no XSS value as written) | **DOCUMENTED** — already the transitional posture (SECURITY_AUDIT row 5); inline inventory attached to agent report |
| D5 | S4 | requirements.txt:4 | mediapipe 0.10.33 pin unresolvable on macOS/py3.12 (env drift; authoritative pip-audit must run in deploy image) | **DOCUMENTED** — DEPLOY_CHECKLIST note |
| E12 | S4 | cv_core.js:52 | findWorstJoint untested (pure) | **BATCHED** — node test added |
| E13 | S4 | coach_core.js:63-64 | Squat safety-fault ids lack by-name channel test | **DEFERRED** — after device walk per finding's own note |
| E15 | S4 | urls.py static routes | home/offline/legal/sw untested | **BATCHED** — 200 smoke loop |
| MAIN-1 | — | (= A8) | Main-session duplicate of A8 | see A8 |

**Counts:** S1 1 · S2 25 · S3 22 · S4 27 (75 findings).
Disposition: see per-row status; MENTOR-queued wording items live in
`docs/MENTOR_REVIEW_QUEUE.md` §2026-07.

## Clean bills (agents' verified-clean lists — do not re-audit)
Pain pipeline test coverage · absolute-stop coverage · camera-vs-guided
labeling in build_report (PainEvent-only confirmed again) · coach_core
arbitration logic · amber-first/red-safety wiring · session-fixation, reset
lifecycle, csrf_exempt absence, |safe usage (3, all constants), rate-limiter
coverage map (all sensitive POSTs limited — except D1 admin, now fixed) ·
localStorage absence · speech watchdog/queue bounds · report immutability
against mutation (write-once verified) · bounded hot lists (details in agent
reports).
