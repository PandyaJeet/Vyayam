# MENTOR REVIEW QUEUE — patient-facing clinical wording awaiting physio-mentor sign-off

Standing rule (CLAUDE.md): patient-facing clinical wording changes get flagged for
Pawan's physio mentor before shipping. Strings tagged **interim-live pending mentor**
are live in the product now (R6 demo) and must be reviewed at the next mentor session.
Remove a row once the mentor approves it (or replace the string and re-tag).

## R6-P2 — spoken exercise briefing, `commonMistake` lines (v1_exercise_execute.html)

| Exercise def | String | Tag |
|---|---|---|
| SQUAT | "Most common mistake: letting your knees drift past your toes. Sit your hips back and keep your knees behind your toes." | author: Pawan — live |
| SQUAT_PARTIAL | "Most common mistake: going deeper than feels comfortable. Only go as far down as you can without pain." | interim-live pending mentor |
| HINGE | "Most common mistake: bending the knees and turning it into a squat. Push your hips back and keep your knees only softly bent." | interim-live pending mentor |
| LUNGE | "Most common mistake: taking too short a step. Take a big step so your front knee stays over your foot." | interim-live pending mentor |
| SL_RDL | "Most common mistake: rushing and losing balance. Move slowly, and keep your standing foot pressed into the floor." | interim-live pending mentor |
| GLUTE_BRIDGE_SUPINE | "Most common mistake: pushing through your toes. Keep your heels down and drive through them as you lift." | interim-live pending mentor |

## R6-P2 — briefing frame lines

| Context | String | Tag |
|---|---|---|
| Briefing, tempo (has tempo) | "We'll go slowly down [for a slow {three…ten} count], hold, then push up." | interim-live pending mentor |
| Briefing, tempo (no tempo) | "Move at a steady, controlled pace." | interim-live pending mentor |
| Briefing, therapist note | "Your therapist adds: {note}." | interim-live pending mentor (frame only — note text is the therapist's own) |
| Briefing, close | "When you're ready, begin." | interim-live pending mentor |
| Set 2+ | "Set {n}. Same rhythm." | interim-live pending mentor |

## R6-P3 — movement-synced tempo phrases (tier flow; tempo never affects form color/score)

| Context | String | Tag |
|---|---|---|
| Eccentric 1s / 2s / 3s+ | "Down." / "Slowly down." / "Slowly… all the way down." | interim-live pending mentor |
| Hold (+60% elapsed if ≥2s) | "Hold." / "…good." | interim-live pending mentor |
| Concentric 1s / 2s / 3s+ | "Up." / "Push up." / "Slowly push up, squeeze." | interim-live pending mentor |
| Pause/top (if >0s) | "Reset." | interim-live pending mentor |
| Pace nudge (ecc <50% prescribed ×2 consecutive reps, once/set) | "Slower on the way down — control it." | interim-live pending mentor |

## R6-P4 — squat named-fault cues (coach_core.js CUES; amber-first, never red)

| Cue id | String | Tag |
|---|---|---|
| squat_knee_over_toe | "Knees drifting past your toes — sit your hips back." | author: Pawan — live |
| squat_heel_rise | "Keep your heels down. Weight through mid-foot." | interim-live pending mentor |
| squat_depth_gentle | "You can go a little deeper if it's comfortable." | interim-live pending mentor (comfort-conditional — never commands depth) |

## R6-HOTFIX — squat SAFETY fault cues (safety class: red allowed while cue live)

| Cue id | String | Tag |
|---|---|---|
| squat_too_deep | "Too deep — come up a little. Stay in your range." | author: Pawan — live |
| squat_asymmetry | "Uneven — you're loading one side more. Even out both knees." | author: Pawan — live |

---

# §2026-07 — Final-examination clinical wording queue (Agent A audit, 2026-07-10)

Items below are NOT live changes — they are existing strings (or policy
questions) the audit flagged. Each row cites the ledger id in
CODEBASE_HEALTH_2026-07.md where the file:line + proof lives.

## Wording rulings needed

| Ledger | Surface | Current string (verbatim) | Question / proposed |
|---|---|---|---|
| A3 | exercise_catalog.py:370 (renders on patient session pages) | "ACL injury-prevention drill — trains single-leg deceleration without knee valgus." | Is a prevention claim acceptable in patient copy? Proposed: "Trains single-leg deceleration and landing control without knee collapse." |
| A5 | session report mode chip | plyo camera sets labeled `camera (landing checks)` as of this cycle (label fix shipped) | Should Form% ALSO be suppressed for PLYO_* sets, or is the qualified label sufficient? |
| A6 | gap_fill heel_drop content (LATENT — dead keys) | "This will be painful or achy in the tendon — this is safe and therapeutic." · "Stopping when it aches — mild tendon ache during the exercise is normal and therapeutic." · "Heel drops are the gold standard treatment for Achilles tendinopathy…" | Alfredson-protocol framing vs the app's own pain-stop protocol; needs mentor rewrite. **Blocks ledger A8** (content-key fix) — approving these unblocks a one-line fix that lights up instructions/cues on all camera + library pages. |
| A7 | gap_fill:2186,2252 + exercise_content.py:143 (LATENT `language_*` fields) | "Tight ankles limit squat depth and increase injury risk." · "Tight adductors increase groin injury risk." · "Useful for patellar tendinopathy rehab…" | Batch-review all `language_*` strings before any surface ever renders them. |
| A10 | football_assessment_results.html:102 | "You need a Nordic hold of 4+ seconds and a Pogo score of 3+ before explosive jump training is safe for your tendons." | Proposed readiness wording: "…before your programme unlocks explosive jump training." |
| A11 | v1_warmup.html:195 | "Skipping warm-up increases injury risk. Recommended only if you've already warmed up separately." | Proposed: "Warming up prepares your joints and tendons for loading. Skip only if you've already warmed up separately." |
| A14 | v1_session_detail.html:39 | History card colors form_score<55 red | Does rule 7 (red = safety only) bind stats displays, or only live coaching? If yes → amber floor. |

## Policy rulings needed (Pawan + mentor)

| Ledger | Question |
|---|---|
| B-X1 | Managed-patient self-serve account deletion is now BLOCKED (fix shipped: therapist-managed patients are told to ask their therapist). Ruling needed on the permanent policy: PROTECT clinical records vs patient data-rights deletion (anonymize-not-delete?). Self-serve (non-managed) patients retain full delete. |
| A9 | Does locked decision 4 (PainEvent is the only pain source in REPORTS) bind the patient progress page + weekly therapist PDF too? Both currently average direct patient-entered ratings (SessionLogItem.pain / SessionLog.overall_pain) — real data, but a different source than PainEvent. If yes → rebuild both from PainEvent next cycle. |

## Phase-3 dark-coach cue strings (2026-07-10 build — DARK, not patient-visible until flag flip)

All new coach cue ids ship dark behind per-exercise catalog flags that remain
False. Strings follow the ≤8-words/no-fault-label/amber-first rules; none are
safety/red class. Review before any flag flips:

| Cue id | String |
|---|---|
| wall_sit_slide_down | "Slide down — thighs level with the floor" |
| wall_sit_heels | "Keep both heels on the floor" |
| plank_hips_sag | "Lift your hips — straight line" |
| plank_hips_pike | "Lower your hips — straight line" |
| side_plank_hip_drop | "Push your hip up" |
| balance_foot_down | "Lift your foot to restart the clock" |
| slr_knee_straight | "Keep that knee locked straight" |
| prone_hips_flat | "Keep your hips on the floor" |
| pelvis_still | "Keep your pelvis still" |
| press_even | "Press both arms up together" |
| row_sit_tall | "Sit tall — pull with your back" |
