"""Mind Lab adaptive difficulty. Pure logic: no Django, no I/O.

Given how a game session went, return the next difficulty level. It knows
nothing about any specific game; "level" is just an integer the game maps to
its own difficulty. Every number Pawan owns is a module constant marked
PAWAN_SETS. Tune them here and nowhere else.
"""

# PAWAN_SETS: accuracy at or above this moves the athlete UP one step. (0..1)
LEVEL_UP_ACCURACY = 0.85

# PAWAN_SETS: accuracy strictly below this moves the athlete DOWN one step. (0..1)
# At exactly this value the level holds.
LEVEL_DOWN_ACCURACY = 0.60

# PAWAN_SETS: fewest trials before the level may change. Fewer trials = hold.
MIN_TRIALS_TO_ADAPT = 10

# PAWAN_SETS: lowest and highest level a game may be set to.
MIN_LEVEL = 1
MAX_LEVEL = 10

# PAWAN_SETS: how many levels one session can move the athlete.
LEVEL_STEP = 1


def next_level(level, accuracy, n_trials):
    """Return the next level (int) after a session.

    level     current level, clamped into [MIN_LEVEL, MAX_LEVEL] first.
    accuracy  fraction correct in [0, 1], or None when unknown (holds).
    n_trials  trials played; below MIN_TRIALS_TO_ADAPT the level holds.

    Raises ValueError for accuracy outside [0, 1] or negative n_trials.
    """
    if n_trials < 0:
        raise ValueError('n_trials must be >= 0')
    if accuracy is not None and not 0.0 <= accuracy <= 1.0:
        raise ValueError('accuracy must be within [0, 1]')

    current = max(MIN_LEVEL, min(MAX_LEVEL, level))
    if accuracy is None or n_trials < MIN_TRIALS_TO_ADAPT:
        return current
    if accuracy >= LEVEL_UP_ACCURACY:
        return min(MAX_LEVEL, current + LEVEL_STEP)
    if accuracy < LEVEL_DOWN_ACCURACY:
        return max(MIN_LEVEL, current - LEVEL_STEP)
    return current
