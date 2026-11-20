"""RTP config: every [Clinician sets] value from SPINE_SPEC, as a plain constant.

No imports. Each default is the CONSERVATIVE one: the value more likely to hold,
notify or slow progression. None is signed off. Each is listed in
docs/UNSIGNED_DEFAULTS.md.
"""

# UNSIGNED: "swelling today = yes" holds an athlete who has an active episode.
HOLD_ON_SWELLING = True
# UNSIGNED: "giving way = yes" holds an athlete who has an active episode.
HOLD_ON_GIVING_WAY = True

# UNSIGNED, wording needs physio mentor review. Shown to the athlete when held.
# No clinical threshold or claim in it. Not a diagnosis.
ATHLETE_HOLD_TEXT = 'Your training is paused. Please check with your therapist.'

# --- S9 comparator (compare_pain_feedback). All UNSIGNED. -------------------

# UNSIGNED: two sessions further apart than this many calendar days are not compared.
# Larger is the conservative side: more pairs get compared, so more "worse" is seen.
MAX_GAP_DAYS = 14
# UNSIGNED: pain_severity (0-10) up by this much or more is "worse". Smaller is conservative.
SEVERITY_DELTA = 1
# UNSIGNED: tightness_0_10 up by this much or more is "worse". Smaller is conservative.
TIGHTNESS_DELTA = 1
# UNSIGNED: when True, a change of pain_location counts as "worse".
# Off by default per SPINE_SPEC (the conservative setting would be True).
LOCATION_CHANGE_COUNTS = False
