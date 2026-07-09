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
