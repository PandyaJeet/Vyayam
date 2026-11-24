"""Pass Window rules. Pure logic: no Django, no I/O. Only imports config.

Scores a chosen pass against a scenario and decides the next level from a
session's trials, in blocks. Chosen over reusing adaptive.next_level because
that function takes one session accuracy (no blocks, no timeouts, levels 1-10),
which cannot express "N blocks in a row with no timeouts". adaptive.py is left
untouched.

All scenarios are demo scenarios, review == "UNREVIEWED". Every number Pawan
owns lives in config.py (PASS_WINDOW_*), never here.
"""

from . import config

MIN_LEVEL = 1
MAX_LEVEL = 5

# Time Assist factor per level. 0.5, 0.7 and 0.85 are the spec author's proposal.
# 1.0x is the app's base speed, not "match speed".
LEVEL_FACTORS = {1: 0.3, 2: 0.5, 3: 0.7, 4: 0.85, 5: 1.0}

BEST, ACCEPTABLE, WRONG, TIMEOUT = 'best', 'acceptable', 'wrong', 'timeout'
MAX_DECISION_MS = 600000


def clamp_level(level):
    return max(MIN_LEVEL, min(MAX_LEVEL, level))


def score_choice(scenario, chosen):
    """BEST, ACCEPTABLE or WRONG. An option not offered by the scenario is WRONG."""
    if chosen == scenario['correct']:
        return BEST
    if chosen in scenario['acceptable']:
        return ACCEPTABLE
    return WRONG


def score_trial(scenario, chosen, timeout):
    """Outcome of one trial. A timeout has no choice and is never scored on it."""
    if timeout:
        return TIMEOUT
    return score_choice(scenario, chosen)


def counts_as_correct(outcome):
    if outcome == BEST:
        return True
    return outcome == ACCEPTABLE and config.PASS_WINDOW_ACCEPTABLE_COUNTS_AS_CORRECT


def trial_order(scenarios, level, n):
    """Scenario ids for n trials at a level: that level's pool in file order,
    cycled. Deterministic. Empty pool gives []. A small pool repeats.
    """
    pool = [s['id'] for s in scenarios if s['level'] == level]
    if not pool or n <= 0:
        return []
    return [pool[i % len(pool)] for i in range(n)]


def blocks(outcomes, size=None):
    """Split outcomes into complete blocks. A trailing partial block is dropped.
    Each block is {'n', 'correct', 'timeouts'}.
    """
    size = size or config.PASS_WINDOW_BLOCK_SIZE
    out = []
    for i in range(0, len(outcomes) - size + 1, size):
        chunk = outcomes[i:i + size]
        out.append({
            'n': size,
            'correct': sum(1 for o in chunk if counts_as_correct(o)),
            'timeouts': sum(1 for o in chunk if o == TIMEOUT),
        })
    return out


def next_level(level, outcomes, hold=False):
    """Level for the next session. Moves at most one level, never past 1..5.

    Drop one level when the last 2 complete blocks are both below the down %,
    or the session's timeouts reach the limit. Otherwise raise one level when
    the last N complete blocks are each at or above the up % with no timeouts.
    Otherwise hold. Drop is checked first. hold=True (a shortened day) holds.
    Integer maths on percentages, so 90% of 4 is exactly 3.6 and never rounds.
    """
    level = clamp_level(level)
    if hold:
        return level
    bs = blocks(outcomes)
    timeouts = sum(1 for o in outcomes if o == TIMEOUT)
    down = config.PASS_WINDOW_ACCURACY_DOWN_PCT
    up = config.PASS_WINDOW_ACCURACY_UP_PCT
    need = config.PASS_WINDOW_BLOCKS_TO_RAISE

    low_blocks = len(bs) >= 2 and all(b['correct'] * 100 < down * b['n'] for b in bs[-2:])
    if low_blocks or timeouts >= config.PASS_WINDOW_TIMEOUTS_TO_LOWER:
        return clamp_level(level - 1)
    last = bs[-need:]
    if len(last) == need and all(
            b['correct'] * 100 >= up * b['n'] and b['timeouts'] == 0 for b in last):
        return clamp_level(level + 1)
    return level


def _median(values):
    if not values:
        return None
    s = sorted(values)
    mid = len(s) // 2
    return float(s[mid]) if len(s) % 2 else (s[mid - 1] + s[mid]) / 2.0


def clean_trials(raw, scenarios, max_trials):
    """Validate untrusted trials from the browser. Return clean dicts or raise
    ValueError. A timeout carries no choice and no decision time. Rejects
    unknown scenarios, bad types, bools, NaN and out-of-range times.
    """
    if not isinstance(raw, list) or not 1 <= len(raw) <= max_trials:
        raise ValueError('bad trial list')
    known = {s['id'] for s in scenarios}
    clean = []
    for t in raw:
        if not isinstance(t, dict) or t.get('scenario_id') not in known:
            raise ValueError('bad scenario')
        timeout = t.get('timeout')
        chosen = t.get('chosen')
        ms = t.get('decision_ms')
        if not isinstance(timeout, bool):
            raise ValueError('bad timeout')
        if timeout:
            if chosen is not None or ms is not None:
                raise ValueError('timeout carries no choice')
        else:
            if not isinstance(chosen, str) or len(chosen) > 40:
                raise ValueError('bad choice')
            if (isinstance(ms, bool) or not isinstance(ms, (int, float))
                    or ms != ms or not 0 <= ms <= MAX_DECISION_MS):
                raise ValueError('bad decision time')
        clean.append({'scenario_id': t['scenario_id'], 'chosen': chosen,
                      'timeout': timeout, 'decision_ms': ms})
    return clean


def session_result(level, trials, scenarios, hold=False):
    """Rescore clean trials. Returns accuracy (fraction counted correct),
    median decision ms (own history only, real time), timeouts and next_level.
    """
    by_id = {s['id']: s for s in scenarios}
    outcomes = [score_trial(by_id[t['scenario_id']], t['chosen'], t['timeout'])
                for t in trials]
    n = len(outcomes)
    return {
        'n_trials': n,
        'accuracy': (sum(1 for o in outcomes if counts_as_correct(o)) / n) if n else None,
        'median_rt_ms': _median([t['decision_ms'] for t in trials if not t['timeout']]),
        'timeouts': sum(1 for o in outcomes if o == TIMEOUT),
        'next_level': next_level(level, outcomes, hold=hold),
    }
