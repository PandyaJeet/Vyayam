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
