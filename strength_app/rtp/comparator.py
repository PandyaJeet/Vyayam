"""S9 comparator (SPINE_SPEC, Comparator). A pure function: reads two records, writes nothing.

compare_pain_feedback(prev, curr) -> 'worse' | 'same' | 'better' | 'no_comparison'

prev and curr are the athlete's last two session feedback records, older first.
Every threshold is read from config at call time.

Rules, per field:
- traffic_light: higher is worse.
- pain_severity: up by SEVERITY_DELTA is worse. Ignored (skipped like a null)
  when a record has a green traffic light AND an empty pain_location, because
  the athlete form posts severity 3 by default when no pain is reported.
  Reading: the gate is per record, so if EITHER record is green with an empty
  location (after normalise_pain_location) the severity field is skipped.
  Green with a location, or yellow/red with an empty location, still counts.
- swelling_today, giving_way: no to yes is worse.
- tightness_0_10: up by TIGHTNESS_DELTA is worse.
- locking_or_catching: yes in the NEWER record is worse.
- pain_location: counts only if LOCATION_CHANGE_COUNTS is on (default off).
A null skips only that field. If every field is skipped the answer is
no_comparison. A null never holds. A missing record, or a gap of more than
MAX_GAP_DAYS calendar days between the two session dates, is no_comparison.
Any worse field gives worse. Else any better gives better. Else same.
"""
from django.utils import timezone

from ..v1_safety_logic import normalise_pain_location
from . import config

WORSE, SAME, BETTER, NO_COMPARISON = 'worse', 'same', 'better', 'no_comparison'

_LIGHT_RANK = {'green': 0, 'yellow': 1, 'red': 2}


def _session_day(feedback):
    """Calendar date of the feedback's session, or None."""
    when = getattr(getattr(feedback, 'session', None), 'session_date', None)
    if when is None:
        return None
    if hasattr(when, 'hour') and timezone.is_aware(when):
        when = timezone.localtime(when)
    return when.date() if hasattr(when, 'date') else when


def _number(prev, curr, delta):
    if prev is None or curr is None:
        return None
    delta = max(1, delta)
    if curr - prev >= delta:
        return WORSE
    if prev - curr >= delta:
        return BETTER
    return SAME


def _no_to_yes(prev, curr):
    if prev is None or curr is None:
        return None
    if curr and not prev:
        return WORSE
    if prev and not curr:
        return BETTER
    return SAME


def _light(prev, curr):
    p, c = _LIGHT_RANK.get(prev), _LIGHT_RANK.get(curr)
    return _number(p, c, 1)


def _locking(prev, curr):
    # Yes in the newer record is worse whatever the older one says.
    if curr is None:
        return None
    if curr:
        return WORSE
    if prev is None:
        return None  # nothing to compare a "no" against
    return BETTER if prev else SAME


def _location(prev, curr):
    if not config.LOCATION_CHANGE_COUNTS:
        return None
    p, c = normalise_pain_location(prev), normalise_pain_location(curr)
    if not p or not c:
        return None
    return SAME if p == c else WORSE


def _severity_is_noise(rec):
    return (getattr(rec, 'traffic_light', None) == 'green'
            and not normalise_pain_location(getattr(rec, 'pain_location', None)))


def _severity(prev, curr):
    if _severity_is_noise(prev) or _severity_is_noise(curr):
        return None
    return _number(getattr(prev, 'pain_severity', None), getattr(curr, 'pain_severity', None),
                   config.SEVERITY_DELTA)


def compare_pain_feedback(prev, curr):
    if prev is None or curr is None:
        return NO_COMPARISON
    day_prev, day_curr = _session_day(prev), _session_day(curr)
    if day_prev is None or day_curr is None:
        return NO_COMPARISON
    gap = (day_curr - day_prev).days
    if gap < 0 or gap > config.MAX_GAP_DAYS:
        return NO_COMPARISON

    def g(obj, name):
        return getattr(obj, name, None)

    verdicts = [
        _light(g(prev, 'traffic_light'), g(curr, 'traffic_light')),
        _severity(prev, curr),
        _no_to_yes(g(prev, 'swelling_today'), g(curr, 'swelling_today')),
        _no_to_yes(g(prev, 'giving_way'), g(curr, 'giving_way')),
        _number(g(prev, 'tightness_0_10'), g(curr, 'tightness_0_10'), config.TIGHTNESS_DELTA),
        _locking(g(prev, 'locking_or_catching'), g(curr, 'locking_or_catching')),
        _location(g(prev, 'pain_location'), g(curr, 'pain_location')),
    ]
    verdicts = [v for v in verdicts if v is not None]
    if not verdicts:
        return NO_COMPARISON
    if WORSE in verdicts:
        return WORSE
    if BETTER in verdicts:
        return BETTER
    return SAME
