"""Mind Lab day mode: which plan today's Check-In 4 sets.

`resolve_day_mode` is pure. `mind_lab_day_mode(athlete)` reads today's
check-in and the existing traffic light. Gating table: G3 workbook, sheet
"Mind Lab Session". "Worst state wins"; "pain overrides sleep".
"""

MODES = ('full', 'shortened', 'recovery_only', 'checkin_breath_only')
PAIN_LIGHTS = ('green', 'yellow', 'red')


def resolve_day_mode(sleep_bucket, pain_light, hold=False):
    """Return exactly one of MODES. Most restrictive row wins, in this order:
    hold or red pain, sleep under 5 h, yellow pain, sleep 5-6 h, then full.
    sleep_bucket None (no check-in yet today) gives checkin_breath_only,
    because the check-in itself is still allowed.
    """
    if pain_light not in PAIN_LIGHTS:
        raise ValueError('bad pain light')
    if sleep_bucket not in (None, 'under_5', '5_to_6', 'over_6'):
        raise ValueError('bad sleep bucket')
    if hold or pain_light == 'red' or sleep_bucket is None:
        return 'checkin_breath_only'
    if sleep_bucket == 'under_5':
        return 'recovery_only'
    if pain_light == 'yellow' or sleep_bucket == '5_to_6':
        return 'shortened'
    return 'full'


def s3_hold_active(athlete):
    """HOOK for S3 (guardrail 6: a hold returns checkin_breath_only).

    S3 does not exist yet, so there is no hold source. Always False.
    Replace the body when S3 lands. Do not invent a source here.
    """
    return False


def pain_light_for(athlete):
    """The existing traffic light: the latest SessionFeedback.traffic_light.

    Not PainEvent, not a new question. No feedback yet means green.
    shortcut: no age limit on the latest feedback, add one if stale lights
    should expire.
    """
    fb = athlete.session_feedbacks.order_by('-created_at').first()
    return fb.traffic_light if fb else 'green'


def todays_checkin(athlete):
    from django.utils import timezone
    from strength_app.models import MindLabCheckIn
    return (MindLabCheckIn.objects
            .filter(athlete=athlete, created_at__date=timezone.localdate())
            .order_by('-created_at').first())


def mind_lab_day_mode(athlete):
    """Today's mode for this athlete: one of MODES."""
    checkin = todays_checkin(athlete)
    return resolve_day_mode(
        checkin.sleep_bucket if checkin else None,
        pain_light_for(athlete),
        hold=s3_hold_active(athlete),
    )
