"""Mind Lab config: every number the G3 workbook leaves blank ("Pawan Sets").

ONE module, plain constants, no imports. Each default is the CONSERVATIVE
value: the one more likely to hold, notify or slow progression. None is signed
off. Every constant here is listed in docs/UNSIGNED_DEFAULTS.md.
"""

# --- Check-In 4 -------------------------------------------------------------
# Score = energy + focus + (6 - stress), each answer 1..5, so the score is 3..15.
# UNSIGNED: score at or above this is a Full day. Set high so Full is hard to get.
CHECKIN_FULL_MIN_SCORE = 12
# UNSIGNED: score at or above this (and below Full) is a Light day. Below it: Recovery.
CHECKIN_LIGHT_MIN_SCORE = 9

# Stated by the workbook (not blank): stress or energy at this value shows the support line.
SUPPORT_LINE_AT_OR_BELOW = 1

# --- Youth ------------------------------------------------------------------
# UNSIGNED: below this age the youth wording applies. Guardian consent flow is NOT built.
YOUTH_AGE_CUTOFF = 18

# --- Reset Breath (not built yet; constants kept so the blank is not lost) ---
# UNSIGNED: completed sessions before moving up. Workbook example is 3; 5 is slower.
RESET_BREATH_SESSIONS_TO_LEVEL_UP = 5

# --- Routine Builder (not built; step 3+) -----------------------------------
# UNSIGNED: correct recalls before moving up.
ROUTINE_BUILDER_RECALLS_TO_LEVEL_UP = 5
# UNSIGNED: errors in one session before moving down. Workbook suggests 3 or more.
ROUTINE_BUILDER_ERRORS_TO_LEVEL_DOWN = 3

# --- Still-Switch (not built; step 3+) --------------------------------------
# UNSIGNED: accuracy % needed to go up (for 2 sessions in a row).
STILL_SWITCH_ACCURACY_UP_PCT = 90
# UNSIGNED: accuracy % below which the level goes down.
STILL_SWITCH_ACCURACY_DOWN_PCT = 70
# UNSIGNED: in-session accuracy drop (percentage points) that stops the game early.
STILL_SWITCH_STOP_EARLY_DROP_PCT = 15

# --- Pass Window (G2 spec; every [Pawan sets] blank, conservative defaults) --
# UNSIGNED: base closing time in ms. Closing time = this / Time Assist factor,
# so a bigger base means more time at every level.
PASS_WINDOW_BASE_CLOSING_MS = 4000
# UNSIGNED: session timer in seconds. The spec's own maximum is 90.
PASS_WINDOW_SESSION_MAX_S = 90
# UNSIGNED: trials in a session (the session also stops at the timer).
PASS_WINDOW_TRIALS = 8
# UNSIGNED: trials per block. The level rule is checked per block.
PASS_WINDOW_BLOCK_SIZE = 4
# UNSIGNED: accuracy % a block needs to count toward a raise (high = slow promotion).
PASS_WINDOW_ACCURACY_UP_PCT = 90
# UNSIGNED: accuracy % below which a block counts toward a drop (high = quick demotion).
PASS_WINDOW_ACCURACY_DOWN_PCT = 70
# UNSIGNED: blocks in a row at or above the up % (and no timeouts) before a raise.
PASS_WINDOW_BLOCKS_TO_RAISE = 2
# UNSIGNED: timeouts in a session that drop one level.
PASS_WINDOW_TIMEOUTS_TO_LOWER = 2
# UNSIGNED: Level 5 decision time limit in ms. Equal to the base closing time,
# so it adds no pressure until Pawan sets a shorter value.
PASS_WINDOW_L5_DECISION_LIMIT_MS = 4000
# UNSIGNED: does an "acceptable" (defensible) pass count as correct for the
# level rule? False = only the listed best pass counts (slower promotion).
PASS_WINDOW_ACCEPTABLE_COUNTS_AS_CORRECT = False
# Stated by the spec (not blank): the freeze-and-explain step lasts about 2 s.
PASS_WINDOW_FREEZE_MS = 2000
# Stated by the spec (not blank): exhibition visitor = 3 trials at Level 2, fixed.
PASS_WINDOW_VISITOR_TRIALS = 3
PASS_WINDOW_VISITOR_LEVEL = 2
