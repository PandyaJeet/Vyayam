# PRINCIPLES_STATUS — VYAYAM 34 principles vs code (audit, 2026-11-17)

Spec audited: "VYAYAM Football Athlete Training System — Complete Principles Document V1"
(extracted text, 537 lines; cited below as `PDF:<line>`). Code base: `main` @ 0208e84.
Read-only audit: no code was changed. Nothing here resolves a contradiction; Pawan decides.

Verdict rule used throughout:
- `IMPLEMENTED` — the mechanism the PDF describes runs on the live path. Parameter
  differences (numbers, thresholds) are listed under Contradictions, not here.
- `PARTIAL` — some of the described mechanism exists; the "Missing" column says what does not.
- `NOT FOUND` — no live implementation; the evidence is the search that came back empty
  (repeated verbatim, unescaped, in "Searches" at the end).

A test is listed only if it calls the code that implements the behaviour and asserts on it.

| # | Principle (PDF wording) | Verdict | Evidence (path:line) | Covering test | Missing / note |
|---|---|---|---|---|---|
| P1 | Do No Harm | IMPLEMENTED | `strength_app/v1_prescription_engine.py:1140` (absolute stop → no session); `strength_app/v1_safety_logic.py:172` (red-flag/equipment filter); `strength_app/v1_prescription_engine.py:1311` (pattern paused after 3 pain sessions); `strength_app/v1_session_views.py:761` (severity ≥8 stops session) | `strength_app/tests/test_deep_audit.py::TestDAC6EmergencyScreening::test_da_c6_each_new_option_stops_with_urgent_copy` | — |
| P2 | Progressive Overload | IMPLEMENTED | `strength_app/v1_safety_logic.py:639` (2 consecutive comfortable sessions → ready); `strength_app/v1_prescription_engine.py:1442` (capability +1, capped by age) | `strength_app/tests/test_exam_2026_07_gaps.py::TestE6DosingModifiers::test_progression_two_for_two_rule` | Trigger is "comfortable/easy" rating, not "completed all prescribed reps" (see Contradictions C9) |
| P3 | Periodisation | IMPLEMENTED | `strength_app/v1_constants.py:264` (phase table); `strength_app/v1_safety_logic.py:752` (`advance_periodisation`, called at `strength_app/v1_session_views.py:1146`); `strength_app/v1_prescription_engine.py:943` (football season/competition phases) | none | No test calls `advance_periodisation` or `_get_football_periodisation_phase` |
| P4 | Deload | PARTIAL | `strength_app/v1_safety_logic.py:349` (4-week ceiling; 6 for novices); `strength_app/v1_safety_logic.py:359` (≥2 red lights trigger); `strength_app/v1_prescription_engine.py:340` (sets × 0.6) | `strength_app/tests/test_r2_ship.py::TestR2W2DeloadTrainingAge::test_r2_w2_intermediate_keeps_four_week_ceiling` | Intensity drop missing: `DELOAD_CONFIG['intensity_reduction']` (`strength_app/v1_constants.py:620`) is defined but never read. No "performance decline" trigger. ACWR trigger absent by design (C1) |
| P5 | Dosage | IMPLEMENTED | `strength_app/v1_constants.py:161` (bilateral), `:169` (unilateral), `:202` (holds), `:234` (power), `:252` (endurance); applied in `strength_app/v1_prescription_engine.py:268` | `strength_app/tests/test_deep_audit.py::TestDAP3DataIntegrity::test_da_p3_hold_exercises_dosed_as_holds` | Tables are capability-based (1–5), not the PDF's goal ranges (C10) |
| P6 | Joint Centration | PARTIAL | `therapist_app/exercise_catalog.py:21` (`v2_ghost_supported`); `strength_app/v1_therapist_session_views.py:274` (ghost path); form cues attached at `strength_app/v1_prescription_engine.py:396` | `strength_app/tests/test_deep_audit.py::TestDAH1FormCalculatorToleranceCurve::test_da_h1_monotone_in_error` (form-error scoring only) | Ghost only on the camera-supported subset. Cue text not shown on camera/library pages: views read non-existent `*_en` keys (`strength_app/v1_session_views.py:1340`; known ledger item A8, mentor-gated). Ghost rendering itself untested |
| P7 | Recovery | PARTIAL | `strength_app/v1_prescription_engine.py:183` (weekly split rotates patterns, `:193`–`:211`); sleep modifies volume at `strength_app/v1_prescription_engine.py:1206` | none | No elapsed-hours check between same-muscle sessions; with 5 sessions/week the squat/hinge day repeats (`:207` and `:210`) with no 48 h guard |
| P8 | Asymmetry Management | PARTIAL | `strength_app/v1_onboarding_views.py:357` (LSI from raw values, bands at `:367`); `strength_app/v1_prescription_engine.py:1407` (extra weak-side sets) | `strength_app/tests/test_r2_ship.py::TestR2W2AsymmetryRaw::test_r2_w2_same_raw_same_class_regardless_of_bands` (classification only) | Extra sets only for moderate/significant (LSI <70) and only on unilateral exercises (`:1408`); "mild" (70–84) gets none. Football `lsi_flag` (`strength_app/models.py:1346`) does not drive extra sets. No test of the extra-set step |
| P9 | Kinetic Chain | IMPLEMENTED | `strength_app/v1_prescription_engine.py:178` (squat↔hinge, push↔pull pairing); `strength_app/v1_constants.py:10` (pattern framework) | none | — |
| P10 | Proximal Before Distal | NOT FOUND | Search S10: `grep -n "core_score" strength_app/v1_prescription_engine.py strength_app/v1_safety_logic.py` → empty. `core_score` is collected (`strength_app/v1_onboarding_views.py:922`) but never gates explosive work | none | Nearest gate is football plyo lock on `squat_score < 4` (`strength_app/v1_football_views.py:465`), which is not a core test |
| P11 | New Exercise Gating | PARTIAL | `strength_app/v1_prescription_engine.py:1456` (max 2 new exercises/session) | none | No reduced load for first 2 sessions: `volume_reduction_when_introducing` (`strength_app/v1_constants.py:583`) is never read |
| P12 | Mind-Muscle Connection | PARTIAL | `strength_app/v1_prescription_engine.py:401` (`mind_muscle_cue` attached); football intent cue at `strength_app/v1_prescription_engine.py:853` | none | Camera page reads `mind_muscle_cue_en` (`strength_app/v1_session_views.py:1339`), which no entry has (A8). No irradiation / 5 s isometric cue |
| P13 | Warmup Protocol | IMPLEMENTED | `strength_app/v1_prescription_engine.py:465` (elevate/mobilise/activate/prime; FIFA 11+ branch for football) | `strength_app/tests/test_deep_audit.py::TestDAP3DataIntegrity::test_da_p3_warmup_respects_red_flags` | — |
| P14 | Cooldown Protocol | PARTIAL | `strength_app/v1_prescription_engine.py:583` (light movement, static stretch, breathing) | `strength_app/tests/test_r2_ship.py::TestR2W2ProtocolHygiene::test_r2_w2_cooldown_static_holds_within_acsm_band` (stretch data only) | No heart-rate-recovery monitoring; `_build_cooldown` itself untested |
| P15 | ACL Prevention | PARTIAL | `strength_app/v1_safety_logic.py:149` (female landing notes), applied at `strength_app/v1_prescription_engine.py:1473`; decel/landing drill content at `strength_app/exercise_content_gap_fill.py:3378` | `strength_app/tests/test_exam_2026_07_gaps.py::TestE4FemaleAclPrevention::test_female_gets_acl_notes` | Only a text note, only for females. No landing/deceleration training is prescribed; drills are content entries only |
| P16 | Drop-Off Protocol | NOT FOUND | Search S16: `grep -rniE "velocity.?loss\|terminate.*set\|form.?breakdown\|set_terminated\|consecutive ?red\|auto.?stop" strength_app/templates strength_app/static/strength_app/js strength_app/v1_session_views.py strength_app/v1_therapist_session_views.py strength_app/v1_prescription_engine.py` → empty | none | Code's "drop-off" (`strength_app/v1_safety_logic.py:801`) is return-after-a-break, a different thing. Legacy stub `strength_app/backend/form_tracking.py:188` stops a *simulated* set on a red rep (`:170` "Simulate set execution"); not wired to the camera |
| P17 | Traffic Light Pain | PARTIAL | `strength_app/v1_safety_logic.py:376` (green/yellow/red from feedback + per-exercise pain); next-session volume `strength_app/v1_prescription_engine.py:690`; in-session stop `strength_app/v1_session_views.py:761` | `strength_app/tests/test_deep_audit.py::TestDAF1PerExercisePain::test_da_f1_sharp_per_exercise_pain_overrides_mild_checkin`; `strength_app/tests/test_g1_pain_pipeline.py::TestG1aAthleteSeverityStopsServerSide::test_aching_8_stops_even_with_action_continue` | Red does not substitute pain-free alternatives; yellow is −15% not −30% (C11) |
| P18 | Nutrition | PARTIAL | `strength_app/v1_nutrition_engine.py:11` (goal macros), `:116` (targets); fuelling modifies volume at `strength_app/v1_prescription_engine.py:1241` | `strength_app/tests/test_deep_audit.py::TestDAC10NutritionSetupState::test_da_c10_with_profile_lights_work` | Protein is % of calories, not 1.6–2.2 g/kg. No pre/post-workout timing or hydration reminders |
| P19 | Sleep Modifiers | PARTIAL | `strength_app/v1_constants.py:523` (sleep_quality → volume/intensity); `strength_app/v1_safety_logic.py:424` (<5 h + low energy = red) | `strength_app/tests/test_r2_ship.py::TestR2W2SleepTrafficLight::test_r2_w2_under_5_always_at_least_yellow` | No "<5 h → active recovery only"; no RPE-7 cap; profile uses a quality label, not hours |
| P20 | Hormonal Adaptation | PARTIAL | `strength_app/v1_safety_logic.py:25` (phase calc), `:33` (contraceptive bypass); `strength_app/v1_constants.py:368` (modifiers) | `strength_app/tests/test_deep_audit.py::TestDAC15HormonalModifierConvention::test_da_c15_known_phase_values` | Follicular "higher intensity" deliberately omitted (`strength_app/v1_constants.py:361`); luteal cuts total volume, not plyo volume specifically |
| P21 | RFD / Contrast Pairs | PARTIAL | `strength_app/v1_prescription_engine.py:856` (pairs at level 3+); `strength_app/v1_football_constants.py:372` (12 pairs) | none | PAP rest not applied: prescribed `rest_seconds` is 90–120 s (`strength_app/v1_football_constants.py:377`, used at engine `:874`) while the note at engine `:882` says 5–6 min (C6). No >85% 1RM prescription |
| P22 | SSC Gating | PARTIAL | `strength_app/models.py:1363` (`check_plyometric_gate`: level/LSI/hop/Nordic/sprint/pain); `strength_app/v1_prescription_engine.py:886` (strip plyo if not cleared); contact cap `:902` | `strength_app/tests/test_exam_2026_07_gaps.py::TestE3P22PlyoGating::test_uncleared_gate_blocks_high_load_plyo` | Gate is NOT RSI-based (banned, C2). Contact cap is only a note: no contact counter, no 48 h rule, depth jumps not double-counted |
| P23 | APA | PARTIAL | `strength_app/v1_prescription_engine.py:544` (deep-core activation in every warm-up) | none | No bracing cue attached to explosive exercises; the "P23" note at `:933` is about reactive agility, not APA |
| P24 | HSR Tendon Protocol | PARTIAL | `strength_app/v1_football_constants.py:317` (3 phases, 6-0-6 tempo); `strength_app/v1_prescription_engine.py:1058` (auto-advance at 4 weeks); weeks tracked at `strength_app/v1_football_views.py:455` | none | Phase content differs: phase 1 is HSR, not isometric holds; phase 3 is 3-0-3, not high-speed eccentrics |
| P25 | Posterior Chain Ratio | PARTIAL | `strength_app/v1_prescription_engine.py:804` (share of posterior-chain exercises in session vs target `strength_app/v1_football_constants.py:227`) | none | No hamstring:quad *strength* ratio is measured; "ratio" is an exercise count |
| P26 | F-V Profiling | PARTIAL | `strength_app/models.py:1349` (tendency from hop vs sprint score); weights applied `strength_app/v1_prescription_engine.py:920`; 4-week reassessment `strength_app/v1_football_views.py:431` | none | Proxy only (no F-V curve); no %1RM load prescription |
| P27 | Energy Systems | IMPLEMENTED | `strength_app/v1_session_views.py:876` (conditioning view, route `strength_app/urls.py:71`); `strength_app/v1_football_constants.py:708` (zones, talk test, RSA), `:783` (season map) | `strength_app/tests/test_g0_inline_js_integrity.py::TestG0AssessmentFootballConditioningJS::test_g0_extended_pages_inline_js_parses` (page render + inline JS only) | Protocol selection logic untested |
| P28 | Sprint Mechanics | PARTIAL | `strength_app/exercise_content_gap_fill.py:3378` (9 `'sprint'` pattern content entries) | none | Content only; no split or engine path ever prescribes them. Scope fence: not to be built |
| P29 | Match Microcycle | PARTIAL | `strength_app/models.py:264` (`MatchDate`); `strength_app/v1_prescription_engine.py:991` (MD-5…MD+2 mapping), applied at `:1492` | none | Search S29: `grep -rnE "match_day_of_week\|next_match_date" --include='*.py' --exclude-dir=tests strength_app therapist_app` → empty; no recurring weekly match day, only dated calendar entries |
| P30 | Hip/Ankle Mobility | PARTIAL | `strength_app/warmup_library.py:101` (90/90 in squat-day mobilise); `strength_app/exercise_content_gap_fill.py:3487` (couch stretch), `:2156` (ankle DF wall) | none | Not auto-prescribed daily; not routed into MD+1/MD-1. Scope fence: not to be built |
| P31 | ACWR | NOT FOUND | Search S31: `grep -rniE "acwr\|acute.?chronic\|session_load" --include='*.py' --include='*.html' --include='*.js' --exclude-dir=tests --exclude-dir=migrations strength_app therapist_app` → only the removal comment `strength_app/v1_prescription_engine.py:1547`. `session_rpe` is captured (`strength_app/models.py:625`) | Absence pinned by `strength_app/tests/test_deep_audit.py::TestDAC4AcwrRemoved::test_da_c4_athlete_session_generates_without_acwr_meta` | Deliberately removed; banned by CLAUDE.md:50 (C1) |
| P32 | FIFA 11+ Warmup | IMPLEMENTED | `strength_app/v1_prescription_engine.py:468` (football routing), levels `:477`–`:483`; `strength_app/warmup_library.py:602` (3 parts × 3 levels) | none | No test asserts `is_fifa_11` |
| P33 | Tendon Timelines | NOT FOUND | Search S33: `grep -rniE "weeks_since_start\|tendon_category\|tendon_weeks" --include='*.py' --exclude-dir=tests --exclude-dir=migrations strength_app therapist_app` → empty | none | Only the P24 HSR 4-week counter exists. Scope fence: not to be built |
| P34 | Transfer Classification | NOT FOUND | Search S34: `grep -rnE "transfer_category\|Bondarchuk\|'SDE'\|\"SDE\"" --include='*.py' --exclude-dir=tests --exclude-dir=migrations strength_app therapist_app` → empty | none | Scope fence: not to be built |

Counts: IMPLEMENTED 8 (P1, P2, P3, P5, P9, P13, P27, P32) · PARTIAL 21 · NOT FOUND 5 (P10, P16, P31, P33, P34).

## Contradictions

**C0 — headline. The PDF asks for two things CLAUDE.md bans outright.**
`CLAUDE.md:50` (locked "Clinical integrity" section, which "overrides any instruction that
conflicts"): "no ACWR, no "RSI" claims". The PDF makes both part of the spec (C1, C2). The code
follows CLAUDE.md, not the PDF. Not resolved here.

**C1 — ACWR (P4, P31).**
- PDF:23–24 "Acute:chronic workload ratio … ACWR 0.8-1.3 sweet spot."
- PDF:66 "ACWR NEW Session load tracking. Sweet spot 0.8-1.3. Spike prevention."
- PDF:82–83 (P4) deload "auto-triggered if … ACWR exceeds 1.5".
- PDF:366–367 "Above 1.5 Danger Zone Acute spike. Injury risk 2-3x higher"; PDF:377–378 "ACWR computed daily. ACWR > 1.5 triggers auto-volume-reduction. Dashboard trend graph."
- PDF:488 roadmap lists "ACWR Computation" as priority 5.
- Code: `strength_app/v1_prescription_engine.py:1547`–`1550` "P31 (ACWR) removed by standing decision R2 … must not be computed or surfaced anywhere … Do not reintroduce a replacement score." `strength_app/v1_safety_logic.py:309` deload has no ACWR trigger. Test `strength_app/tests/test_deep_audit.py::TestDAC4AcwrRemoved` pins the absence. `docs/FOOTBALL_METHODS.md:323` "ACWR deliberately excluded".

**C2 — RSI gate (P22).**
- PDF:56 "P22 SSC Gating Existing RSI gate before plyometrics."
- PDF:151–152 "readiness assessed via Reactive Strength Index before plyometric progression. RSI must exceed threshold before depth jumps are prescribed."
- Code: `strength_app/v1_football_constants.py:87`–`91` "this is an APP-SPECIFIC reactivity count, NOT Reactive Strength Index … must never use the term "RSI"." The real gate (`strength_app/models.py:1363`, thresholds `strength_app/v1_football_constants.py:527`) uses level, hop LSI, hop/Nordic/sprint scores and pain — no RSI. Test `strength_app/tests/test_r2_ship.py::TestR2W2ProtocolHygiene::test_r2_w2_no_rsi_claim_anywhere_user_facing` enforces the ban.

**C3 — PDF status column says "Existing" for principles the code does not have.**
PDF:44 "P10 Proximal Before Distal Existing", PDF:50 "P16 Drop-Off Protocol Existing" — both NOT FOUND above (S10, S16).

**C4 — "Drop-off" means two different things.** PDF:122 "If rep quality drops below threshold within a set (velocity loss >20% or visible form breakdown), the set is terminated." Code's drop-off is return-after-a-gap: `strength_app/v1_safety_logic.py:801` "DROP-OFF RECOVERY — GAP DETECTION".

**C5 — Asymmetry threshold.** PDF:95 "If any LSI falls below 90%, extra sets are prescribed". Code bands `strength_app/v1_onboarding_views.py:367` "≥85 none · 70–84 mild · 55–69 moderate"; extra sets start at moderate (`strength_app/v1_prescription_engine.py:380`–`382`).

**C6 — PAP rest window.** PDF:144 "PAP … rest window: 4-8 minutes between heavy set and explosive set." Code prescribes `'rest_between_s': 90` (`strength_app/v1_football_constants.py:377`), used as `rest_seconds` at `strength_app/v1_prescription_engine.py:874`; the note at `:882` tells the athlete "Rest 5-6 min". The code disagrees with itself as well as with the PDF.

**C7 — New-exercise load.** PDF:104 "introduced at reduced load (60-70% of target) for first 2 sessions." Code caps the count only (`strength_app/v1_prescription_engine.py:1456`); `strength_app/v1_constants.py:583` (0.75) is unused.

**C8 — Deload intensity.** PDF:82 "intensity drops 10-20%". `strength_app/v1_constants.py:620` `'intensity_reduction': 0.7` (a 30% drop) and it is never applied.

**C9 — 2-for-2 criterion.** PDF:75 "if the athlete completes all prescribed reps for 2 consecutive sessions". Code: `strength_app/v1_safety_logic.py:629`–`639` "achieved 'comfortable' or 'easy' in 2 consecutive sessions".

**C10 — Dosage ranges.** PDF:86 "Strength: 3-5 sets x 3-6 reps, 2-4 min rest." Code strength table is 2–3 sets × 6–15 reps, 60–90 s (`strength_app/v1_constants.py:161`–`166`); strength-phase rest 150 s (`strength_app/v1_constants.py:548`).

**C11 — Traffic-light yellow.** PDF:126 "Yellow = pain present but manageable, reduce volume 30%". Code: `strength_app/v1_prescription_engine.py:693`–`694` yellow → 0.85 (−15%).

**C12 — Sleep.** PDF:133 "below 6 hours: volume reduced 20%, intensity capped at RPE 7. Below 5 hours: active recovery session only." Code: `strength_app/v1_constants.py:524` `'poor': volume 0.6, intensity 0.7`; no active-recovery-only path.

**C13 — Hormonal follicular phase.** PDF:136 "follicular phase … = higher intensity tolerated". Code: `strength_app/v1_constants.py:361`–`362` "V1 keeps only CONSERVATIVE adaptations: nothing increases load".

**C14 — Proximal-before-distal gate.** PDF:102 "core test score determines when explosive lower/upper body work is introduced." No code reads `core_score` for gating (S10).

**C15 — Match-day fields.** PDF:315 "Two new fields on FootballProfile: match_day_of_week (recurring weekly) and next_match_date". Code uses a `MatchDate` calendar (`strength_app/models.py:264`); S29 empty.

**C16 — HSR phases.** PDF:165–166 "Phase 1: isometric holds. Phase 2: slow eccentrics (Nordic progression). Phase 3: high-speed eccentrics." Code phase 1 is 6-0-6 HSR including Nordic (`strength_app/v1_football_constants.py:318`–`330`); phase 3 tempo 3-0-3 (`:355`).

**C17 — Posterior chain ratio.** PDF:169 "Hamstring-to-quadriceps strength ratio monitoring. Target: conventional ratio >0.6". Code ratio = posterior-chain exercise count / session size (`strength_app/v1_prescription_engine.py:802`–`806`).

**C18 — Protein.** PDF:130 "Protein intake guidance (1.6-2.2g/kg/day for athletes)". Code: protein as % of calories (`strength_app/v1_nutrition_engine.py:14`).

## Principles whose implementation would cross CLAUDE.md's locked clinical rules

Rules quoted from `CLAUDE.md:47`–`53`.

- **P31 ACWR** — "no ACWR". Any implementation is banned. PDF:366–367 also asks for an "Injury risk 2-3x higher" warning to the user, which is risk-prediction wording on the football tier ("training-readiness wording only").
- **P22 RSI gate** — "no "RSI" claims". A phone camera / self-count cannot measure RSI (`strength_app/v1_football_constants.py:88`–`90`); a gate labelled RSI would be a false claim.
- **P4 ACWR deload trigger** — same ban as P31.
- **P16 Drop-off (velocity loss >20%)** — needs per-rep velocity. For guided (non-camera) work that data does not exist, and inventing it breaks "rep-level data never fabricated for guided work". For camera work it would touch rep detection, which standing rule 3 (`CLAUDE.md:34`) forbids, and the camera feel-layer freeze is still on (`CLAUDE.md:86`).
- **P17 / P33 pain triggers** — PDF:432 "Knee/Achilles pain triggers auto-reduce plyometrics". Any pain shown in reports must come from PainEvent only ("PainEvent is the only pain source in reports"). Today the engine reads `SessionFeedback`/`ExerciseExecution` pain for prescribing (`strength_app/v1_safety_logic.py:364`, `:453`); report display already uses PainEvent (`strength_app/tests/test_r2_report.py::TestR2PainSourceOfTruth::test_item_pain_is_ignored_painevent_is_used`). New pain-driven features must keep that split.
- **P30 / P25 injury-prediction claims** — PDF:318–320 "Hip IR <35 degrees predicts hamstring injury … increases ACL risk". Surfacing this to football users goes beyond training-readiness wording. Existing content already leans this way: `strength_app/exercise_content_gap_fill.py:2186` "increase injury risk" (athlete language; gap_fill wording is mentor-gated per ledger A6/A7).
- **P32 / P15 injury-reduction percentages** — PDF:380 "30-46% overall injury reduction". Today this appears only in a code comment (`strength_app/warmup_library.py:605`); showing it to users would be an outcome claim on the football tier.
- **P27 performance claim** — `strength_app/v1_football_constants.py:748` (live, athlete-facing): "This improves your maximum oxygen uptake by up to 11% in 8 weeks." Flagged for Pawan / mentor: an outcome promise, arguably beyond training-readiness wording.
- **P20 hormonal notes** — `strength_app/v1_constants.py:380` "Peak ACL risk." If this string reaches patients, it is risk language that needs mentor sign-off (not verified whether it is displayed; see UNVERIFIED).

## Searches (raw, for re-running)

```
# S10 (P10)
grep -n "core_score" strength_app/v1_prescription_engine.py strength_app/v1_safety_logic.py
# S16 (P16)
grep -rniE "velocity.?loss|terminate.*set|form.?breakdown|set_terminated|consecutive ?red|auto.?stop" strength_app/templates strength_app/static/strength_app/js strength_app/v1_session_views.py strength_app/v1_therapist_session_views.py strength_app/v1_prescription_engine.py
# S29 (P29 fields)
grep -rnE "match_day_of_week|next_match_date" --include='*.py' --exclude-dir=tests strength_app therapist_app
# S31 (P31) — only hit is the removal comment at v1_prescription_engine.py:1547-1548
grep -rniE "acwr|acute.?chronic|session_load" --include='*.py' --include='*.html' --include='*.js' --exclude-dir=tests --exclude-dir=migrations strength_app therapist_app
# S33 (P33)
grep -rniE "weeks_since_start|tendon_category|tendon_weeks" --include='*.py' --exclude-dir=tests --exclude-dir=migrations strength_app therapist_app
# S34 (P34)
grep -rnE "transfer_category|Bondarchuk|'SDE'|\"SDE\"" --include='*.py' --exclude-dir=tests --exclude-dir=migrations strength_app therapist_app
```

All run from the repo root at 0208e84; all returned nothing except S31 as noted.
