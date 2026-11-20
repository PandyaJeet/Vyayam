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
