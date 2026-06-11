"""Shared input validation helpers (DA-C13).

Mirrors therapist_app's _safe_int pattern so every JSON/form endpoint
clamps client-supplied numbers instead of crashing (500) on junk or
persisting absurd values (pain 999, negative sets, form_score 10**6).

Canonical clamp ranges:
    pain / severity   0–10
    session RPE       1–10
    sets              0–20
    reps              0–100
    form score        0–100
    rest seconds      0–600
"""


def safe_int(value, default, lo, hi):
    """Parse int with clamping; junk → default."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def safe_float(value, default, lo, hi):
    """Parse float with clamping; junk/NaN/inf → default."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v != v or v in (float('inf'), float('-inf')):  # NaN / inf guard
        return default
    return max(lo, min(hi, v))
