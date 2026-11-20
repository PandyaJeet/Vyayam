"""Check-In 4: validation, score, day label. Pure: no Django, no I/O.

Four answers, always four: sleep bucket, stress 1-5, energy 1-5, focus 1-5.
Self-report only. Not a screen, a diagnosis or a mental-health measure.
"""

from . import config

SLEEP_BUCKETS = ('under_5', '5_to_6', 'over_6')

# Day label the plan implies (worst state wins).
MODE_LABEL = {
    'full': 'full',
    'shortened': 'light',
    'recovery_only': 'recovery',
    'checkin_breath_only': 'recovery',
}
_LABEL_RANK = {'full': 0, 'light': 1, 'recovery': 2}

# Athlete-facing text. Wording needs mentor review before release (CLAUDE.md).
PLAN_TEXT = {
    'full': 'Full Mind Lab today.',
    'shortened': 'Shorter Mind Lab today. Your level holds.',
    'recovery_only': 'Recovery only today. Your level holds.',
    'checkin_breath_only': 'Check-In and Reset Breath only today.',
}
LABEL_TEXT = {'full': 'Full day', 'light': 'Light day', 'recovery': 'Recovery-only day'}
# Fixed line from the G3 workbook. Youth adds the trusted-adult clause.
SUPPORT_LINE = 'If you feel very low, please talk to your coach or a qualified professional.'
SUPPORT_LINE_YOUTH = ('If you feel very low, please talk to your coach, '
                      'a qualified professional or a trusted adult.')


def clean_rating(value):
    """Return an int 1..5, or raise ValueError. Rejects bools and non-integers."""
    if isinstance(value, bool):
        raise ValueError('rating must be 1-5')
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError('rating must be 1-5')
    if not 1 <= number <= 5:
        raise ValueError('rating must be 1-5')
    return number


def clean_sleep(value):
    if value not in SLEEP_BUCKETS:
        raise ValueError('bad sleep bucket')
    return value


def clean_answers(sleep, stress, energy, focus):
    """Return a dict of validated answers or raise ValueError."""
    return {
        'sleep_bucket': clean_sleep(sleep),
        'stress': clean_rating(stress),
        'energy': clean_rating(energy),
        'focus': clean_rating(focus),
    }


def checkin_score(stress, energy, focus):
    """3 (worst) .. 15 (best). Low stress is good, so stress is flipped."""
    return energy + focus + (6 - stress)


def score_label(score):
    if score >= config.CHECKIN_FULL_MIN_SCORE:
        return 'full'
    if score >= config.CHECKIN_LIGHT_MIN_SCORE:
        return 'light'
    return 'recovery'


def day_label(score, mode):
    """The worse of the score label and the label the gating mode implies."""
    from_score = score_label(score)
    from_mode = MODE_LABEL[mode]
    return max(from_score, from_mode, key=_LABEL_RANK.__getitem__)


def show_support_line(stress, energy):
    """Workbook: stress or energy at 1 shows the support line. Never blocks.

    shortcut: the workbook does not say which end of the stress scale is "bad",
    so stress at 5 shows the line too. Pawan to confirm; see UNSIGNED_DEFAULTS.
    """
    low = config.SUPPORT_LINE_AT_OR_BELOW
    return energy <= low or stress <= low or stress >= 6 - low
