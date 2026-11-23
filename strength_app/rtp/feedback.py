"""S8: the five injury questions on the post-session form.

Asked, read and stored only for an athlete with an active episode, and only
when RTP_ENABLED is on. Everyone else gets today's form and null columns.
"""
from . import availability as av


def ask_injury_questions(patient):
    return av.enabled() and av.has_active_episode(patient)


def _yes_no(raw):
    """'yes' / 'no' -> True / False. Anything else (blank, junk) -> None, never a hold."""
    return {'yes': True, 'no': False}.get((raw or '').strip().lower())


def injury_fields_from_post(patient, post):
    """kwargs for SessionFeedback. Empty when the questions were not asked."""
    if not ask_injury_questions(patient):
        return {}
    from ..validation import safe_int
    tightness = safe_int(post.get('tightness_0_10'), None, 0, 10)  # junk or blank -> null
    return {
        'swelling_today': _yes_no(post.get('swelling_today')),
        'giving_way': _yes_no(post.get('giving_way')),
        'locking_or_catching': _yes_no(post.get('locking_or_catching')),
        'tightness_0_10': tightness,
        'tightness_location': (post.get('tightness_location') or '').strip()[:100],
    }
