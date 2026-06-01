# VYAYAM Clinical Literature Audit
**Date**: 2026-04-23
**Auditors**: 4 parallel agents (Agent 1 Clinical Lead + Agent 2 Sports Physio / Football + Agent 3 Rehab Physio / RTS + Agent 4 Biomechanics)
**Scope**: V1 codebase at `strength_app/` (Django monolith). No PDF located (`find ... -name "*.pdf"` negative). Marketing claims were inferred from code comments, README, and Agents 2/3 notes.

---

## Executive Summary

**Finding counts (post-adjudication)**:
- Ship-blockers: **15** (cap enforced; weakest downgraded to High — see Adjudication)
- High: **24**
- Medium: **21**
- Low / polish: **11**
- Documented limitations: **9**
- PDF-vs-code / marketing divergences: **13**

**Top 5 ship-blockers** (ranked by patient-harm vector × frequency):

1. **SB-1 — No post-surgical / post-ACLR / time-since-injury gating on plyometric clearance; clearance gate is numerically circular.** A motivated 4–5 month post-ACL-reconstruction user with no injury-date capture passes Level 3 plyometrics on raw LSI/numbers alone. This is the single highest-harm finding and is duplicated across Agent 2 (SB2-4), Agent 3 (SB3-1, SB3-2, SB3-3, SB3-12) and confirmed by Agent 1.

2. **SB-2 — User can self-clear `absolute_stop` and red flags mid-session by editing the onboarding screen.** No clinician gate, no audit trail, no confirmation workflow, no state history. A user who marks "recent cardiac event / active cancer / uncontrolled hypertension" and then un-marks it proceeds straight to prescription. Found by Agent 1.

3. **SB-3 — Cauda equina, malignancy, DVT, and systemic "wind-of-change" red flags are absent from the onboarding screen.** Users with emergent neurological or oncological presentations receive full strength prescriptions. Found by Agent 3 (SB3-6), confirmed by Agent 1.

4. **SB-4 — Nordic hamstring is scored as seconds held rather than reps-to-breakpoint or eccentric peak force, and is prescribed without an eccentric-exposure gate to novices and females.** Time-hold is uncited in the NHE literature; prescribing heavy eccentrics to untrained users has documented rhabdomyolysis case reports. Agents 2 (SB2-1, SB2-5), 3 (SB3-9), Agent 4 (H4-3).

5. **SB-5 — Football `football_level = min(6 scores)` and `hsr_weeks_completed = max(..., current_week % 4)`.** The min-aggregation caps a player at the single-weakest-test level (uncited); the `% 4` bug caps the counter at 0–3 so the tendon-adaptation gate can never satisfy its own ≥4 requirement. Two unrelated faults in a single pathway. Agent 2 (SB2-2, SB2-13).

**Scope decision required before pilot (central go / no-go lever)**:

> **Is V1 a performance / training-optimisation product for uninjured, screened-healthy adults, or is V1 also a return-to-sport / rehabilitation product?**

Every ship-blocker in this report either disappears or becomes un-defensible depending on that answer. If V1 is **uninjured-only**:
- SB-1, SB-3, SB-6 (ACLR), SB-8 (RTS), SB-11 (LSI uniform), SB3-5 are in-scope to **remove the feature** (disable acl_grade_1_2, drop ankle_sprain_acute, drop rehabilitation goal, remove `return_to_sport` football phase, hide post-ACLR screening gaps).
- Marketing must not claim "AI physio" or "clinical-grade" — the tool is a training app.
- All pregnancy / cardiac / cancer paths become hard exclusions without modification logic.

If V1 is **RTS-inclusive**:
- Every ship-blocker must be fixed before pilot. Add clinician-gated unlock workflow, time-since-surgery capture, per-tendon tracking, ACL programme weekly tracking, injury-date-based time gates, post-surgery expiry review, and bidirectional clinician audit trail.
- This is a 6–12 month scope, not a 1-sprint pilot.

**Go / no-go recommendation for Sigma pilot**:

**Conditional no-go until scope is narrowed.** The current codebase markets a rehab / RTS / post-injury feature surface (ACL injury, acute ankle sprain, post-surgery, cardiac event, active cancer, hypertension, osteoporosis, hormonal cycle ACL-risk, female-specific ACL prevention, football RTS pathway) but implements none of the associated clinical logic defensibly. Pilot as-is exposes Sigma to foreseeable harm claims in at least eight documented clinical pathways (SB-1, SB-2, SB-3, SB-4, SB-6, SB-9, SB-10, SB-11).

**Recommended pre-pilot path (minimum)**:
1. Remove rehabilitation, return-to-sport, ACL-history, post-surgery, active-cancer, uncontrolled-hypertension, and acute-ankle-sprain paths from V1. Treat any positive response as a hard "see-your-clinician" exit.
2. Gate the Nordic hamstring behind ≥6 weeks eccentric-exposure history.
3. Fix `absolute_stop` self-clearing (freeze the field once set; require a support contact to clear).
4. Add cauda-equina / malignancy / DVT screening to onboarding with hard exit.
5. Remove "clinical-grade / AI-physio / Bayesian engine" claims from marketing until V2 ships.
6. Re-frame the 7-test screen as a self-rated training readiness screen, not a capability / asymmetry measurement, until sex/age/bodyweight normalisation is implemented.

---

## Ship-Blockers (15, post-adjudication)

### SB-1 — Plyometric clearance gate is numerically circular and has no time-since-injury floor
**Location**: `v1_football_constants.py:451-485`; `models.py:1202-1285, 1248-1290`; `v1_football_views.py:367-371`.
**Current behaviour**: `plyometric_cleared` is derived from hop LSI, Y-balance anterior LSI, and `squat_score` (movement quality), with cutoffs 80 % / 85 % / 90 % for low / medium / high plyo tiers. There is no injury-date field, no time-since-surgery field, and no structured-rehab-weeks field. The "readiness for plyometrics" is defined by the plyometric-adjacent test results themselves. A 4-month post-ACL-reconstruction player who is motivated, has normal hop LSI, and squat_score ≥ 3 passes into depth-drops and lateral bounds.
**Literature consensus**: RTS readiness post-ACLR requires ≥9 months post-surgery, quadriceps LSI ≥ 90 % isokinetic, hop-battery LSI ≥ 90 %, validated psychological readiness (ACL-RSI), and completion of structured criterion-based rehab — *not* a single numeric LSI threshold and definitely not 80 %.
**Citation**: Grindem 2016 BJSM 50:804; Kyritsis 2016 BJSM 50:946; Wellsandt 2017 JOSPT 47:334; Ardern 2016 BJSM RTS consensus; Beischer 2020 JOSPT 50:83; Kotsifaki 2022 BJSM 56:490.
**Why ship-blocker**: Direct catastrophic-harm pathway (ACL re-rupture, meniscal injury, bone bruise). Re-rupture rate at 9 months is ~4×that at 12 months.
**Defensible behaviour**: V1 must either (a) exclude everyone with `acl_grade_1_2` from the plyometric pathway entirely and hide it in the UI, or (b) collect injury-type, injury-date, surgery-date, and clinician-gated readiness before any plyometric is prescribed. LSI alone is not sufficient. Plyo tiers at 80 % LSI are below every published safety threshold and must not exist.
**Agents**: Agent 2 (SB2-4), Agent 3 (SB3-1, SB3-12), Agent 4 (H4-1 depth_jump), Agent 1 (confirmed).

### SB-2 — Users can self-clear `absolute_stop` flags; no clinician gate, no audit trail
**Location**: `v1_onboarding_views.py:998-1013`; `models.py:164-165`.
**Current behaviour**: Absolute stops (recent cardiac event, currently pregnant, active cancer treatment, uncontrolled hypertension, acute fracture, post-surgery < 6 weeks, uncontrolled epilepsy) are set to `True` when any checkbox is ticked, and reset to `False` the next time the user re-submits the screen with the checkboxes un-ticked. No audit log, no confirmation, no support ticket, no lock-out. The `acl_programme_week_4` unlock criterion (`red_flag_map.py:19`) has no reader — restrictions vanish if the user simply de-selects "ACL injury" in red flags.
**Literature consensus**: Screening for absolute exercise contraindication must be lockable and clinician-reviewed; cardiac-event / active-cancer users should not be permitted to self-override.
**Citation**: ACSM's Guidelines for Exercise Testing and Prescription 11e (2021); Riebe 2015 MSSE pre-exercise screening algorithm; Fletcher 2013 AHA statement.
**Why ship-blocker**: Directly enables a user post-MI from four weeks ago to generate a 45-min strength session by un-ticking a checkbox. No clinical software can ship with a self-clearing safety gate. This is also a litigation vector.
**Defensible behaviour**: Any `absolute_stop` set to True must be permanent until an out-of-band unlock (support email, clinician portal, or time-based expiry with explicit re-attestation). Changes must be timestamped and immutable in an audit log. On the red-flag screen, previously ticked red flags must remain ticked on re-render — unticking must require confirmation prose plus date of clinician clearance.
**Agents**: Agent 1 (originated); overlaps Agent 3's SB3-3 and H3-8.

### SB-3 — Cauda equina, malignancy, DVT, and systemic red flags are absent from the onboarding screen
**Location**: `v1_onboarding_views.py:271-293` (RED_FLAG_OPTIONS / ABSOLUTE_STOP_OPTIONS).
**Current behaviour**: The red-flag screen offers 11 musculoskeletal flags (knee, disc, shoulder, ankle, wrist, elbow, ACL, hernia, osteoporosis, hypertension, rotator cuff) and 7 absolute stops (cardiac, epilepsy, fracture, post-surgery, pregnancy, uncontrolled BP, cancer). Missing: saddle anaesthesia / bladder / bowel disturbance (cauda equina), unexplained weight loss / night sweats / rest pain (malignancy), unilateral calf pain / swelling (DVT), thunderclap headache / new neurology, inflammatory red flags (morning stiffness > 1 h, constitutional symptoms).
**Literature consensus**: Any musculoskeletal screening tool used without clinician oversight must capture the "core four" sinister red flags. Failure to screen cauda equina within 48 hours risks permanent incontinence.
**Citation**: Finucane 2020 JOSPT 50(7):350 (red flag consensus); Greenhalgh & Selfe 2010 BJSM 44:918; Henschke 2013 BJSM 47(14):920; Downie 2013 BMJ 347:f7095.
**Why ship-blocker**: A back-pain user with cauda equina gets a loaded deadlift prescription from this app. The screening gap is population-wide (affects every patient who touches the onboarding flow) — not a subgroup risk.
**Defensible behaviour**: Add a "serious-symptom" screen prior to the musculoskeletal red-flag screen, with plain-language items covering bladder/bowel change with back pain, saddle anaesthesia, unexplained weight loss, night pain, unilateral calf swelling, new neurological weakness, fever with back pain, rest pain unrelieved by position. Any positive response triggers immediate "see your doctor today / go to A&E" exit and locks the app until clinician clears.
**Agents**: Agent 3 (SB3-6), Agent 1 (confirmed scope).

### SB-4 — Nordic hamstring: time-hold scoring is uncited; no eccentric-exposure gate; rhabdomyolysis risk in novices
**Location**: `v1_football_constants.py:40-61`; `models.py:1124, 1192-1200`; `v1_football_views.py:247-250`; `v1_progression_chains.py:67`; `nordic_hamstring_curl_v2.py:42`.
**Current behaviour**: Nordic is scored by seconds-held. NHE appears in HSR Phase 1/2/3 and as early as Level 3 hinge progression. Rep-count and eccentric-exposure history are not gated. `SLOW_FALL_THRESHOLD = 2.0 s` in the v2 exercise file — less than half the eccentric duration used in any published NHE protocol.
**Literature consensus**: NHE is validated via reps-to-breakpoint or eccentric peak force (NordBord). Time-hold is not a recognised outcome. Protocols require progressive exposure because untrained users sustain large force decrements and symptomatic DOMS; rhabdomyolysis case reports exist in novice heavy-eccentric cohorts.
**Citation**: Opar 2013 MSSE 45(4):636; van der Horst 2015 AJSM 43(6):1316; Al Attar 2017 Sports Med 47(5):907; Petersen & Hölmich 2005 BJSM; Clarkson 2002 AJPMR 81:S52; Baird 2012 J Nutr Metab (rhabdo cases).
**Why ship-blocker**: Population-wide (every football user, every Level-3 hinge user, every female ACL-prevention user — and per `SEX_MODIFIERS`, "Nordic hamstring earlier in progression" is explicitly the female pathway). The dose is miscalibrated, the scoring is invented, and the contraindication logic is absent.
**Defensible behaviour**: (1) Drop time-hold scoring; if the home-app cannot measure NordBord force or reps-to-breakpoint reliably, declare NHE not measurable and remove it from progression testing. (2) Require ≥ 6 weeks of eccentric-exposure history (Romanian deadlifts, glute-ham raises, slow-eccentric leg curls) before the first Nordic session. (3) Cap rep volume at 2 × 3 in week 1 with 6-second eccentric timing, ramping over 4 weeks. (4) Screen for prior hamstring injury / active tendon pain before prescription.
**Agents**: Agent 2 (SB2-1, SB2-5), Agent 3 (SB3-9), Agent 4 (H4-3), Agent 1 (confirmed).

### SB-5 — `football_level = min(6 scores)` and `hsr_weeks_completed = max(..., current_week % 4)` — two unrelated bugs in one pipeline
**Location**: `models.py:1181, 1192-1200`; `v1_football_views.py:354-360`.
**Current behaviour**: Player football-level is the minimum of six assessment scores, so one low score caps the entire prescription. Separately, the HSR week counter uses `current_week % 4`, which capped the counter to 0–3 — the "≥ 4 weeks before progressing to Phase 2" gate cannot ever be satisfied. Both flaws are undocumented.
**Literature consensus**: Aggregation by min() has no defensible clinical basis — it discards information about sport-specific strengths and over-restricts training. Per-tendon and per-week tracking are needed for tendon-loading protocols.
**Citation**: Kongsgaard 2009 SJMSS 19(6):790; Silbernagel & Crossley 2015 JOSPT 45(11):876; Askling 2014 BJSM 48(7):532.
**Why ship-blocker**: The HSR progression gate literally cannot fire. Players are stuck in Phase 1 indefinitely, or inverse: skip phases if the engine recovers from the bug silently. Either direction is un-defensible for a tendon-loading protocol.
**Defensible behaviour**: Aggregate football-level with a documented, sport-validated weighting (Premier-League-derived batteries use composite scores, not min). Fix the counter to monotonically increment across weeks and persist per-tendon. If the fix is out-of-scope for V1, remove the football Level and HSR pathway from V1 and expose only the standard strength pipeline.
**Agents**: Agent 2 (SB2-2, SB2-13), Agent 1 (confirmed).

### SB-6 — No post-ACLR pathway; no injury-date capture; dead `acl_programme_week_4` unlock criterion
**Location**: `red_flag_map.py:8-21`; `v1_onboarding_views.py:272`.
**Current behaviour**: Only "ACL injury (Grade 1 or 2)" is offered. No ACLR (reconstruction) option, no injury date, no surgery date, no time-since-surgery. The `unlock_criteria: 'acl_programme_week_4'` has no reader anywhere — restrictions either stay forever (if the user leaves the flag set) or vanish if the user de-selects it (see SB-2).
**Literature consensus**: Post-ACLR management requires weeks-since-surgery tracking, criterion-based phase progression, and structured NM training for 9 months minimum.
**Citation**: Van Melick 2016 BJSM 50:1506; Grindem 2016; Kyritsis 2016.
**Why ship-blocker**: ACL-R patients are a documented target population (app exposes "ACL injury" as a flag and offers lunge cap + plyo exclusions) but the clinical pathway is absent. The `unlock_criteria` is a label with no reader — definitive dead code in a safety path.
**Defensible behaviour**: Either (a) remove ACL-injury as a selectable flag in V1 and require a "cleared by your clinician" attestation, or (b) implement injury-date + programme-week tracking and wire `acl_programme_week_4` to an actual reader.
**Agents**: Agent 3 (SB3-2, SB3-3), Agent 1 (confirmed).

### SB-7 — HSR tempos 3-0-3-0 / 4-0-4-0 do not match Kongsgaard; protocol is "Kongsgaard" in label only
**Location**: `v1_football_constants.py:269, 285, 301` (tempos); `:194, 213, 232` (descriptions).
**Current behaviour**: Three HSR phases use 3-0-3-0, 4-0-4-0, 3-0-3-0 (6 s / 8 s / 6 s per rep). Phase 1 is 55 % 1RM. Agent 4 independently confirmed: no phase reaches the 12-second-per-rep Kongsgaard protocol; Phase 2 is closest at 8 s (33 % short).
**Literature consensus**: Kongsgaard HSR is 6-0-6-0 (12 s / rep) at 70 % 1RM in Phase 1, progressing to 85 % over 12 weeks. Beyer 2015 confirms dose-dependence.
**Citation**: Kongsgaard 2009 SJMSS 19(6):790; Beyer 2015 AJSM 43(7):1704.
**Why ship-blocker**: Under-dosed protocol labelled as the validated protocol is a marketing-vs-reality gap that is independently confirmable by any clinician reading the code. Patient gets insufficient tendon adaptation while believing they received Kongsgaard. Truth-in-marketing plus efficacy gap.
**Defensible behaviour**: Either correctly implement 6-0-6-0 at 70–85 % 1RM with measurable load (most home users cannot), or relabel as "slow-heavy-style tendon loading" and cite the ACSM general loading-parameter ranges instead of Kongsgaard.
**Agents**: Agent 2 (SB2-7), Agent 4 (HSR cross-audit confirmation).

### SB-8 — `return_to_sport` phase live with no clinician clearance gate
**Location**: `v1_football_constants.py:605-615`.
**Current behaviour**: A "return-to-sport" phase exists in the football constants and is reachable via level/week progression. There is no clinician attestation, no gate-based progression validated by objective criteria beyond LSI, no psychological readiness screen, and no "cleared for contact" flag. The label "gate-based progression" appears in code but the gates are app-internal numeric thresholds, not clinician-signed.
**Literature consensus**: RTS is a shared-decision clinical act (Shrier's 3-step StARRT framework; Ardern 2016 BJSM consensus). It cannot be self-administered from a mobile app.
**Citation**: Shrier 2015 BJSM 49:1311; Ardern 2016 BJSM 50:853 (BJSM RTS consensus).
**Why ship-blocker**: Presenting "return to sport" as an app-driven pathway misrepresents scope. Harm is downstream (re-injury, insurance exposure).
**Defensible behaviour**: Remove `return_to_sport` phase from V1. Replace with a "maintain fitness while you work with your physio" low-risk pathway. Add a clinician-clearance field that only a coach / physio can set (not the user).
**Agents**: Agent 3 (SB3-5), Agent 1 (agreed).

### SB-9 — Pogo branded as "RSI" but is rep-count; true RSI never computed
**Location**: `v1_football_constants.py:87-108`; `exercise_content_gap_fill.py:3268, 3216`.
**Current behaviour**: The "RSI test" records number of pogo jumps completed. RSI is defined in the UI and internal labelling but never computed (jump height / contact time has no measurement path). The plyometric decision tree cites "RSI" thresholds while the stored quantity is rep-count.
**Literature consensus**: Reactive Strength Index requires flight-time and contact-time measurement (contact mat, OptoGait, IMU, or 240 fps camera with computer vision). Rep-counts have no mechanistic relationship with reactive strength.
**Citation**: Flanagan & Comyns 2008 SCJ 30(5):32; Healy 2018 IJSPP 13(4):458; Ebben & Petushek 2010 JSCR 24(12):3341.
**Why ship-blocker**: The plyometric-progression decision is made on a quantity that is mislabelled. Either the threshold is defensible (and is being applied to the wrong input) or it's not — either way the prescription is wrong.
**Defensible behaviour**: Either (a) measure true RSI with MediaPipe flight-time + contact-time and cite Flanagan bands, or (b) drop the "RSI" label and use pogo rep-count as a general plyometric-tolerance test with explicit uncited caveat.
**Agents**: Agent 2 (SB2-6), Agent 1 (agreed).

### SB-10 — ACWR pipeline: silent imputation, disputed construct, default RPE = 5 masking missing data
**Location**: `v1_prescription_engine.py:1050-1103, 1497-1517`; `models.py:611-616`; `v1_session_views.py:582`.
**Current behaviour**: ACWR auto-reduces volume 30 % at sweet-spot breach. Missing RPE silently defaults to 5 and missing duration to 30 min. sRPE is captured immediately post-session (Foster recommends ≥30 min post).
**Literature consensus**: ACWR as a construct is contested. Even where used, imputation masks missing data and invalidates the ratio; sRPE timing matters; 4-week deload cadence is not RCT-validated across populations.
**Citation**: Impellizzeri 2020 Sports Med 50(4):779; Lolli 2019 BJSM 53(24):1528; Kalkhoven 2021 Sports Med; Foster 2001 MSSE 33(7):1164; Impellizzeri 2019 IJSPP 14(2):270.
**Why ship-blocker**: A silent 30 % volume cut based on a disputed-and-imputed ratio is "clinical-grade" in marketing but "guessed-then-reduced" in code. Users whose data is incomplete get the same auto-cut as users with dangerous actual loads.
**Defensible behaviour**: Require explicit sRPE capture ≥ 30 min post; do not impute missing values — skip the ACWR calculation and fall back to traffic-light logic. Label the auto-cut as "advisory" not "automatic." Remove "load management" from marketing copy until the pipeline is watertight.
**Agents**: Agent 2 (SB2-10, SB2-14), Agent 3 (SB3-11), Agent 1 (agreed).

### SB-11 — LSI 90 % cut-off applied uniformly to uninjured, post-sprain, and post-ACLR
**Location**: `models.py:1213, 1221, 1228`; `v1_football_constants.py:459, 469, 479`.
**Current behaviour**: The same 90 % LSI cut-off gates plyometric clearance regardless of injury history.
**Literature consensus**: Pre-injury LSI baselining is needed; 90 % of a deconditioned post-injury limb is not equivalent to 90 % of a healthy bilateral athlete. Post-ACLR recommendations are ≥ 90 % and often ≥ 95 % on multiple tests with a ≥ 9-month floor.
**Citation**: Wellsandt 2017 JOSPT 47:334; Myer 2013 AJSM; Grindem 2016; Kyritsis 2016.
**Why ship-blocker**: Users who have had a unilateral injury — the population most in need of stringent gating — receive the most permissive gate.
**Defensible behaviour**: Uninjured: LSI not used as a gate (not interpretable without baseline). Post-injury: require ≥ 95 % LSI across hop-test battery plus time-since-surgery floor, and require prior baseline for interpretation, or do not offer the feature.
**Agents**: Agent 2 (SB2-9), Agent 3 (SB3-4), Agent 1 (agreed).

### SB-12 — Asymmetry tiers derived from 1-5 score-band gaps, not percentage raw differences
**Location**: `v1_onboarding_views.py:325-334`; `v1_safety_logic.py:182-219`; `v1_prescription_engine.py:1386-1392`.
**Current behaviour**: `_compute_asymmetry(left, right)` operates on score-band integers 1–5. `gap == 1 → mild`, `gap == 2 → moderate`, `gap ≥ 3 → significant`. Two score-band gap (e.g. left = 20 s hold, right = 10 s hold — 100 % raw difference) is labelled "moderate". Two sides both scoring band 3 (15 s / 25 s — 40 % difference) is labelled "none". Conversely, a true 8 % raw asymmetry that crosses a band boundary (e.g. 15 s vs 14 s) can be labelled "mild" or "none" at random depending on where the bands fall.
**Literature consensus**: Asymmetry is reported as percentage raw difference of the performance variable, typically ≥ 10 % flag, ≥ 15 % concern, ≥ 20 % significant.
**Citation**: Bishop 2018 SCJ 40:1; Impellizzeri 2007 MSSE 39:2044; Plisky 2006 JOSPT 36:911.
**Why ship-blocker**: Directly mislabels asymmetry in both directions — silences real asymmetry and flags imaginary ones. "Progression BLOCKED: significant asymmetry" downstream (`v1_prescription_engine.py:1386-1392`) fires on score-band arithmetic. Cited by the app as a clinical signal.
**Defensible behaviour**: Record raw seconds/reps per side at the raw_test_data_json layer (already present), compute asymmetry as `|left-right|/max(left,right)*100`, and map to 10 %/15 %/20 % tiers. Score-band arithmetic is a UI convenience, not a clinical measure.
**Agents**: Agent 3 (SB3-13), Agent 1 (confirmed with first-hand reading).

### SB-13 — 7-test screen has no carry test yet `carry` is a prescribable pattern; no age / sex / bodyweight normalisation
**Location**: `v1_onboarding_views.py:48-242` (V1_STRENGTH_TESTS); `v1_safety_logic.py:252` (carry score hard-coded to 3).
**Current behaviour**: Movement patterns are listed as seven (`squat, hinge, lunge, push, pull, rotate, carry`). The onboarding battery tests only six patterns (`squat, hinge, push, pull, core, rotate, lunge`) — `core` replaces `carry`, and carry is simply not tested. `compute_pattern_priorities` hard-codes `carry: 3`. Every user, regardless of sex, age, height, weight, or training history, gets the same 1–5 band thresholds for push-ups, holds, and rows. The push-test displays a female-adjusted band in the prose ("0–4 reps (or 0–2 for female)") but the code does no automatic sex adjustment — the user self-classifies.
**Literature consensus**: Strength and capacity tests are bodyweight-, sex-, and age-stratified. ACSM, FMS, Y-Balance, and all validated field tests use normative tables keyed to demographic strata.
**Citation**: ACSM Guidelines 11e (2021); Cook 2014 IJSPT (FMS); Plisky 2021 IJSPT 16:925 (Y-Balance); Tomkinson 2017 BJSM 51:1545 (youth field-test norms); Reid 2017 SCJ (age-stratified norms).
**Why ship-blocker**: The headline screening tool of V1 claims to produce a clinical capability profile but (a) silently skips one of the seven patterns it claims to assess, (b) applies unadjusted thresholds to a 22-year-old male and a 55-year-old female, (c) downstream prescription and "weakness priority" logic is computed from this biased output. This is a product-integrity problem at the foundation layer.
**Defensible behaviour**: (a) Add a farmer-carry assessment OR remove `carry` from the prescribable pattern set and from `MOVEMENT_PATTERNS`. (b) Apply sex-stratified thresholds server-side for push-up, row, hang, hold tests. (c) Apply age-stratified multipliers per ACSM norms. (d) Relabel the output as "training-readiness bands" not "capability assessment" until normalisation is implemented.
**Agents**: Agent 1 (originated). Agent 2 flagged the normalisation gap in football tests (SB2-3) — confirmed here in the V1 strength screen too.

### SB-14 — Mandatory 4-week deload enforcement without literature grounding; also, the counter can drift
**Location**: `v1_constants.py:475-480` (DELOAD_CONFIG); `v1_safety_logic.py:265-317` (check_deload_needed); `v1_session_views.py:642-651` (counter increment).
**Current behaviour**: `trigger_every_n_weeks = 4` is treated as a universal deload cadence for novices, intermediates, advanced, and athletes alike. `weeks_since_deload` is incremented when `total_sessions_this_cycle % sessions_per_week == 0`, which drifts whenever a patient's actual session frequency diverges from their declared frequency.
**Literature consensus**: Deload cadence is individualised (recovery status, training age, intensity proxies). No RCT validates 4 weeks as a universal trigger. Novices rarely need scheduled deloads in the first 12 weeks; advanced lifters often need them every 3 weeks; mobility/endurance-focused goals may need none.
**Citation**: Helms 2017 JSCR; Bompa Periodisation 6e; Schoenfeld 2016 JSCR (volume-fatigue individualisation).
**Why ship-blocker**: Universal 4-wk deload applied to a rehabilitation user or a novice undertrains the precise population that should be progressing. Applied to an advanced athlete at mid-peaking cycle it can disrupt a competition taper.
**Defensible behaviour**: Make deload advisory (recommend based on traffic-light frequency and sRPE trend), not mandatory. Fix the counter to increment on true calendar weeks, not on session modulus.
**Agents**: Agent 3 (SB3-10), Agent 1 (confirmed counter drift).

### SB-15 — Squat and deadlift "back rounded" false-positive fires on every correct deep rep
**Location**: `full_squat_v2.py:178`; `dumbbell_deadlift_v2.py:95-96, 179`.
**Current behaviour**: `avg_back = angle(shoulder, hip, knee)` (i.e. hip flexion angle, not thoracolumbar curvature). When < 150° the app displays "BACK ROUNDED — STOP!". At deep squat or full hip-hinge the hip angle is normally well below 150° due to correct hip flexion. The deadlift file itself documents "True lumbar alignment not measurable with MediaPipe's 33 landmarks" — yet uses the misleading threshold anyway.
**Literature consensus**: Thoracolumbar curvature is not derivable from hip-shoulder-knee angle on sagittal-view MediaPipe. Squat depth below parallel is safe and performance-recommended; deep hip flexion is not back rounding.
**Citation**: Escamilla 2001 MSSE 33(1):127; McGill 2015 Low Back Disorders 3e; Schoenfeld 2010 JSCR.
**Why ship-blocker**: Every correct deep squat generates a "STOP" alert. Every deadlift a competent user performs gets flagged unsafe. This degrades patient confidence, undermines prescription compliance, and is user-facing evidence that the form-analysis claims are not backed by the math in the files.
**Defensible behaviour**: Remove the `avg_back < 150°` warning from both files. Replace with a neutrality indicator based on shoulder-hip vs. hip-knee relative deflection, or retire the cue entirely with a documented limitation of MediaPipe's landmark set.
**Agents**: Agent 4 (SB4-1, SB4-2), Agent 1 (agreed — upgrade retained).

---

## High Findings

### Agent 1 — own (Part A)
- **H-A1.1 Scope creep in onboarding options**: Rehabilitation is an available goal (`GOAL_CONFIG['rehabilitation']`), and ACL-injury, post-surgery, hypertension, cancer are selectable — but none of the downstream rehabilitation logic works. Marketing language on goal labels claims "Rehabilitation" as a valid V1 use case; code does not support it. Decide and remove.
- **H-A1.2 Core vs. carry confusion**: `MOVEMENT_PATTERNS` lists seven items including `carry` but testing uses `core`. Confusion between spine-stabiliser core and loaded-carry is unresolved across code, UI, and constants.
- **H-A1.3 `female_physique` pattern weights override safety priorities**: Hinge weight 1.5 / rotate 1.2 for female_physique is aesthetic aggregated; asymmetry-driven priorities can be masked by these weights (noted also by Agent 3 M3-4, agreed).
- **H-A1.4 No bodyweight capture for any strength test**: Push-up and row tests are bodyweight-dependent but no bodyweight scaling is applied, and bodyweight is optional on screen 2.
- **H-A1.5 "Plyometric clearance" semantics inconsistent**: `hormonal_phase` returns `plyometric_clearance` key; `plyometric_cleared` on football profile is a separate field; ovulation-phase plyometric block is wired but does not write to the football profile (Agent 3 M3-5 related, agreed).
- **H-A1.6 Training-age → start_capability mapping can set a trained user to capability 3 immediately**: Advanced users skip anatomical adaptation phases entirely. No pretesting confirms they can sustain the volume.
- **H-A1.7 Bayesian engine marketing label elsewhere vs. pure rule-based engine in code**: Confirmed V2-only in `models.py:856` and `v1_data_collector.py`. If marketing or pitch decks describe "AI / Bayesian" in V1, remove. (See PDF/marketing section.)

### Agent 2 — football (high)
- H2-1 F-V ±10–20 % volume multipliers are uncited. AGREE.
- H2-2 posterior_anterior_ratio 0.50 / 0.55 / 0.60 uncited. AGREE.
- H2-3 POGO thresholds 10 / 15 / 20 / 25 uncited. AGREE.
- H2-4 training_history not consulted before HSR / plyos / contrast. AGREE.
- H2-5 Reassessment cadence 4 weeks conflicts with 12-wk tendon and 8–10 wk NHE plateau. AGREE.
- H2-6 No ACL-history branch in football module. AGREE.

### Agent 3 — rehab (high)
- H3-1 Hormonal-phase ovulation plyo block on weak evidence. AGREE.
- H3-2 Traffic light RED requires severe pain; isolated moderate pain only YELLOW. AGREE.
- H3-3 Hormonal phase silently 'unknown' at 90 days stale. AGREE.
- H3-4 `apply_female_acl_prevention` called with `[]`. AGREE.
- H3-5 `full_reassessment` after long gap re-runs strength tests, ambiguous red-flag re-screen. AGREE.
- H3-6 Hypertension `max_intensity_percent: 80` uses a dimension engine doesn't expose. AGREE.
- H3-7 Osteoporosis flag doesn't screen vertebral-fracture history. AGREE.
- H3-8 Post-surgery absolute stop auto-expires calendar day 43 without clinician capture. AGREE — merged semantics with SB-2.

### Agent 4 — biomech (high)
- H4-1 depth_jump no contraindication gate; reactive cue at wrong phase. AGREE.
- H4-2 inverted_row body_align computed but never returned. AGREE.
- H4-3 nordic SLOW_FALL_THRESHOLD 2.0 s vs 6 s minimum. AGREE — merged into SB-4.
- H4-4 hamstring_stretch 10 s vs ACSM 30 s. AGREE.
- H4-5 banded_shoulder_dislocate form on avg_knee 170°. AGREE.

### Overflow ship-blocker class (Agent 2 OVF-1…6): promoted to High in this report because ship-blocker cap is held at 15
- OVF-1 COD LSI 90 % too low vs 93–97 %. AGREE (High).
- OVF-2 squat_score conflated with plyo readiness. AGREE (High).
- OVF-3 CONTRAST_PAIRS rest 90 s vs Tillin & Bishop 4–8 min; in-code text inconsistent. AGREE (High).
- OVF-4 FIFA 11+ branching on football_level not weeks exposure. AGREE (High).
- OVF-5 No acute-injury / pain gates on re-assessment. AGREE (High).
- OVF-6 Pogo "visual verification by coach" assumed; app is self-serve. AGREE (High).

---

## Medium Findings

### Agent 2 (medium)
- M2-1 Nordic "score 1 = <1 s" universal floor biases against untrained females. AGREE.
- M2-2 200-ms contact threshold unverifiable by eye. AGREE.
- M2-3 `plyometric_cleared='none'` blocks only 4 keywords; misses many plyo names. AGREE.
- M2-4 `check_plyometric_gate(pain_nrs=0)` called without pain data. AGREE.
- M2-5 `% 4` bug on hsr_weeks_completed. AGREE — merged into SB-5.
- M2-6 athlete_tier_eligible entry gate not surfaced. AGREE.

### Agent 3 (medium)
- M3-1 2-for-2 progression too aggressive in rehab. AGREE.
- M3-2 `max_new_per_session` 2/3 not red-flag-gated. AGREE.
- M3-3 Pregnancy as blanket absolute stop ignores ACOG 804 (2020). AGREE.
- M3-4 female_physique goal weights override asymmetry logic. AGREE — merged with H-A1.3.
- M3-5 plyometric_cleared persists on football profile; not demoted on regression. AGREE.

### Agent 4 (medium)
- M4-1 dumbell_rowing 100 px hardcoded. AGREE.
- M4-2 clock_lunge validate_form wrong keys. AGREE.
- M4-3 bicep_curls 65° transition vs 40° target; partial reps count. AGREE.
- M4-4 calf_stretch 10 s sub-ACSM. AGREE.
- M4-5 thoracic_rotation shoulder-rotation proxy uncited. AGREE.
- M4-6 cat_cow whole-trunk angle not segmental. AGREE.
- M4-7 hip_cars 25-px pelvis stability resolution-dependent. AGREE.

### Agent 1 own (medium)
- **M-A1.1 Traffic-light composite mixes sleep and difficulty into the same RED rule**: `sleep < 5 hours AND energy_level == 'low'` → red. Sleep duration is self-reported and noisy; this can flip a patient to red on a single bad night and then silently deload.
- **M-A1.2 Push-test sex band exists in prose only**: `'0–4 reps (or 0–2 for female)'`. UI shows it; code does not enforce it. Self-classification is not validated.
- **M-A1.3 `not_specified` biological sex defaults to male modifiers implicitly**: no female ACL prevention, no hinge-squat ratio 1.5.
- **M-A1.4 Recent-session count `[:5]` hard-coded in `check_deload_needed`**: users with irregular session frequency trigger deload on different actual time windows.

---

## Low / Polish

- Agent 2 L2-1 POSTERIOR_CHAIN_EXERCISES includes non-posterior-dominant movements. AGREE.
- Agent 2 L2-2 rsa_repeat_sprint 3 × 6 × 30 m / 25 s uncited. AGREE.
- Agent 2 L2-3 Seasonal in-season zone_3_vo2max; Helgerud 4×4 is pre-season. AGREE.
- Agent 2 L2-4 FV_TENDENCY_CONFIG.condition fields are docstrings, not callables. AGREE.
- Agent 3 L3-1 Grade 1/2 sprain lumped. AGREE.
- Agent 3 L3-2 `stable` vs `unknown` dual semantics. AGREE.
- Agent 3 L3-3 sleep modifier dose-response flat. AGREE.
- Agent 3 L3-4 "waist definition" aesthetic claim in goal notes. AGREE.
- Agent 4 L4-1 pike_push_up hip angle not gated. AGREE.
- Agent 4 L4-3 single_leg_squats back angle unused in validate_form. AGREE.
- Agent 4 L4-4 single_leg_balance sway pixel units uncalibrated. AGREE.

(Agent 4 L4-2 — full_pull_up chin clearance — REJECTED as a finding; even Agent 4 flags it "acceptable given MediaPipe".)

---

## Documented Limitations (engineering approximations — disclose, don't fix)

- **MediaPipe 2D sagittal only**: no 3D joint angles; frontal-plane angles are pixel proxies. Many downstream findings (SB-15, H4-1, H4-5, M4-7) are manifestations.
- **No mid-spine landmarks in MediaPipe Pose**: thoracolumbar curvature and true lumbar alignment are not measurable. Quantity `avg_back` in squat/deadlift files is a misnomer for hip angle.
- **Tempo detection not hard-gated** — 20 % weight, no minimum duration gate. Users can rep fast through a 3-0-2-0 target and still score.
- **Resolution-dependent pixel thresholds** — at least six exercises (Agent 4 M4-1, M4-7; SB4-3 boxjump knee threshold; L4-4 balance).
- **NordBord force measurement out of scope** for home app — explicit limitation, but the current time-hold substitute is not a validated alternative.
- **Cardiac synthetic probabilities** — V1 cardiac-event exclusion is binary; no ECG / HR-variability / exercise-tolerance metric is collected.
- **Per-tendon tracking** requires per-tendon state that models do not currently carry.
- **Bayesian engine explicitly V2** — `v1_data_collector.py` logs anonymised sessions for V2 training. V1 is pure rule-based. Document, don't claim otherwise.
- **Onboarding `age >= 18` gate** excludes under-18s — means under-18 age cap (`under_18: max_capability=3`) is dead code, but harmless.

---

## PDF vs. Code / Marketing Divergences (no PDF found — inferred from code labels and marketing copy)

1. **DIV-1 Bayesian engine**: labelled as future V2. If pitch-deck / README claims V1 uses a Bayesian engine, that is a divergence. Code is a deterministic modifier pipeline (see `_calculate_dosage` in `v1_prescription_engine.py:281-377` — 10-layer additive and multiplicative modifiers, no probabilistic inference).
2. **DIV-2 "AI-guided physio"** — same as DIV-1: V1 is a rule engine with form-analysis overlays.
3. **DIV-3 Kongsgaard HSR**: tempos wrong, loads wrong (SB-7).
4. **DIV-4 RSI gate**: not computed — rep-count labelled as RSI (SB-9).
5. **DIV-5 ACWR auto-modulation**: imputed and disputed (SB-10).
6. **DIV-6 Per-tendon tracking**: scalar counter only.
7. **DIV-7 ACL prevention landing mechanics**: three cues and a dead 1.3× multiplier — not FIFA 11+ / PEP / structured NM.
8. **DIV-8 sRPE monitoring**: timing & imputation issues.
9. **DIV-9 F-V profiling**: integer score-delta heuristic, not Morin–Samozino.
10. **DIV-10 "Clinical-grade asymmetry"**: score-band arithmetic, not percentage asymmetry (SB-12).
11. **DIV-11 "Return-to-sport pathway"**: no clinician gate (SB-8).
12. **DIV-12 Post-ACLR management**: no pathway; no injury date; no week counter (SB-6).
13. **DIV-13 "10-test functional movement screen"**: V1_STRENGTH_TESTS is seven tests covering six patterns; the marketing-visible "7 pattern" label does not match the "6 tested + 1 hard-coded-to-3" reality (SB-13).

---

## Cross-Agent Adjudication

**Defaults to agreement.** Exceptions below.

### Mergers (two agents same finding)
- **Plyometric circularity**: Agent 2 SB2-4 + Agent 3 SB3-1 + partial Agent 4 H4-1 → merged as SB-1. All upstream agents retained authorship credit.
- **HSR tempos**: Agent 2 SB2-7 + Agent 4 HSR cross-audit → merged as SB-7.
- **Nordic time-hold + eccentric-exposure**: Agent 2 SB2-1 + SB2-5 + Agent 3 SB3-9 + Agent 4 H4-3 → merged as SB-4.
- **HSR weeks counter bug + football_level min()**: Agent 2 SB2-2 + SB2-13 → merged as SB-5.
- **Post-surgery absolute-stop auto-expiry**: Agent 3 H3-8 → semantic merge with SB-2 (self-clearing gate).
- **ACL-R pathway absent + dead unlock**: Agent 3 SB3-2 + SB3-3 → merged as SB-6.
- **ACWR pipeline + sRPE timing**: Agent 2 SB2-10 + SB2-14 + Agent 3 SB3-11 → merged as SB-10.
- **LSI uniform**: Agent 2 SB2-9 + Agent 3 SB3-4 → merged as SB-11.
- **Female ACL prevention token cues**: Agent 3 SB3-14 → DOWNGRADED to High (now classified under DIV-7 + H-A1.3 + H3-4). Reasoning: the clinical consequence is truth-in-marketing (not direct harm), because female users who execute the 3 cues + the Nordic progression at least land on the right *neuromuscular-direction*. Not harmless, but not a "prevents injury path from functioning" ship-blocker given the other gates.

### Downgrades (ship-blocker → high)
- **Agent 2 SB2-3** (football hop/sprint/COD unnormalised): DOWNGRADED to High and absorbed into SB-13. Reasoning: the core normalisation-absent problem is population-wide and captured at SB-13; duplicating at SB level under-weights the systemic gap. Agent 2 credit retained.
- **Agent 2 SB2-8** (F-V integer-score heuristic): DOWNGRADED to High (also DIV-9). Reasoning: the F-V tendency is a research construct — its misapplication is a marketing / citation problem rather than a harm pathway.
- **Agent 2 SB2-11** (Y-balance anterior-only): DOWNGRADED to High. Reasoning: critical for research-grade Y-balance assessment but not a direct harm pathway in V1 scope.
- **Agent 2 SB2-12** (505 ignores COD deficit): DOWNGRADED to High. Same reasoning — research-grade test-interpretation gap, not acute harm.
- **Agent 2 SB2-15** (HSR Phase 1 eligibility at football_level=2): DOWNGRADED to High. Reasoning: reachable only through SB-1 / SB-4 / SB-5 upstream artefacts; fixing the upstream resolves it.
- **Agent 3 SB3-7** (acute ankle sprain excludes single_leg_balance): DOWNGRADED to High. Reasoning: Delahunt ROAST recommends early graded balance, but single_leg_balance is a reasonable exclusion in the *acute* phase (first 72 h) — the harm is under-prescription, not over-prescription. Merge with the "remove acute-ankle-sprain pathway in V1 scope" recommendation.
- **Agent 3 SB3-8** (hypertension modifications dead): DOWNGRADED to High. Reasoning: there is no downstream reader of `max_hold_seconds` or `max_intensity_percent` for hypertension; the flag at least excludes no exercise, so a HTN user gets unmodified prescription. Documented-limitation severity, not ship-blocker.
- **Agent 3 SB3-14** (female ACL prevention = 3 cues + dead multiplier): DOWNGRADED to High (see mergers above).
- **Agent 3 SB3-15** (65+ power_allowed=False, max_sets=2): DOWNGRADED to High. Reasoning: conservative age-cap is not a harm pathway — it is an under-prescription pathway. Remove the cap or cite Fragala 2019 position stand.
- **Agent 4 SB4-3** (box_jumps landing threshold 140° too lenient; no plyo contraindication gate): RETAINED as upstream exposure but DOWNGRADED to High. Reasoning: the absence of plyometric gating is already ship-blocker at SB-1; box-jump-specific threshold is a downstream parameter tuning issue.
- **Agent 4 SB4-4** (ankle DF unmeasurable, form scored on knee 170°): DOWNGRADED to High. Reasoning: test-invalid, but this is a single exercise's form cue, not a harm pathway. Documented limitation + remove the score.

### Upgrades
- **Agent 1 originated SB-2 (absolute_stop self-clearing)**: elevated from documented-limitation class because the pathway directly enables a post-MI / pregnant / active-cancer user to bypass a safety gate with a checkbox un-click.
- **Agent 1 originated SB-13 (7-test screen coverage + normalisation)**: elevated from high to ship-blocker because the entire downstream prescription + asymmetry engine reads from this biased output.

### Rejections (not reflected in final report)
- **Agent 4 L4-2** (full_pull_up chin clearance via nose-wrist y-coord). Reasoning: Agent 4 themselves flagged as "acceptable given MediaPipe"; no clinical finding.

### Agreed without change
All remaining Agent 2 / 3 / 4 findings adopted as stated, with only renumbering into the unified framework above.

---

## Part A Pointer — Agent 1 Own Findings

Agent 1 (Clinical Lead) originated or confirmed first-hand:

- **Ship-blocker**: SB-2 (self-clearing absolute_stop), SB-13 (7-test screen scope + normalisation), co-confirmed SB-1, SB-3, SB-4, SB-5, SB-12, SB-14 from code reads.
- **High**: H-A1.1 through H-A1.7 above.
- **Medium**: M-A1.1 through M-A1.4 above.

Part A audit covered:
1. **7-test functional movement screen** — score bands 1–5 are time-held or rep-count thresholds, hard-coded in `v1_onboarding_views.py:48-242` with no sex/age/weight normalisation (SB-13). Carry is prescribable but untested.
2. **Bayesian diagnostic engine** — confirmed **absent in V1**. `models.py:856` comment "V2 data foundation — anonymised session data for Bayesian engine training" is the only reference. V1 is a deterministic 10-layer modifier pipeline in `_calculate_dosage`. PDF/marketing divergence (DIV-1).
3. **Asymmetry thresholds (5 % / 10 % / 20 %)** — DO NOT EXIST. The actual V1 asymmetry logic runs on 1–5 score-band arithmetic in `_compute_asymmetry(left, right)` (`v1_onboarding_views.py:325-333`). The "5/10/20 %" marketing claim is fabricated relative to the code. SB-12.
4. **Red flag routing beyond Agent 3's coverage** — Users can self-clear any flag (SB-2). No audit trail. `unlock_criteria` key is unread by any code path.
5. **Prescription engine dosage modifiers by phase** — 9 DOSAGE tables (bilateral / unilateral strength, iso, slow-eccentric, balance, cardio, power, stretching, endurance) × 6 PERIODISATION_PHASES (aa_iso, aa_ecc, hypertrophy, hypertrophy_volume, strength, deload). Modifiers are additive/multiplicative integers/floats with no primary-literature citation attached anywhere. Numbers are plausible but uncited (confirms Agent 2's H-class citation gaps). Dosage values themselves (`sets 2, reps 6, tempo 4-1-3-0, rest 90 s` etc.) map broadly onto ACSM 2011 and Schoenfeld hypertrophy literature but the mapping is not documented in the code. Flag as High-class citation gap.
6. **Deload triggers & 4-week enforcement** — SB-14. Universal 4-week cadence, counter-drift bug, no evidence for universality.
7. **Age / sex / bodyweight normalisation** — Absent in V1 7-test screen. Push-test sex adjustment is prose-only. Carry score hard-coded to 3. Bodyweight not required in onboarding. (SB-13, H-A1.4, M-A1.2.)

End of Part A pointer. All findings are integrated above.

---
*Report produced by Agent 1 (Clinical Audit Lead) with adjudicated inputs from Agent 2 (Sports Physio — Football), Agent 3 (Rehab Physio — RTS), Agent 4 (Biomechanics — Exercise files). Date: 2026-04-23.*
