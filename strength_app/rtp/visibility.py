"""What a coach may see (SPINE_SPEC Visibility).

A coach gets: traffic light, status, restrictions, stage name, "checkpoint
due/passed" and "injury signal: yes/no". Nothing else. Raw swelling, giving way,
tightness and locking values never leave this module: injury_signal is a bool.
"""
from . import availability as av
from .checkpoints import checkpoint_state
from .comparator import compare_pain_feedback
from .models import AvailabilityStatus, RehabStage


def last_two_feedbacks(patient):
    """(previous, newest) SessionFeedback, either may be None. Read only."""
    from ..models import SessionFeedback
    rows = list(SessionFeedback.objects.filter(patient=patient).select_related('session')
                .order_by('-session__session_date', '-pk')[:2])
    newest = rows[0] if rows else None
    previous = rows[1] if len(rows) > 1 else None
    return previous, newest


def injury_signal(patient):
    """True if the comparator says worse, or the newest record has locking,
    swelling or giving way = yes."""
    previous, newest = last_two_feedbacks(patient)
    if newest is None:
        return False
    if True in (newest.locking_or_catching, newest.swelling_today, newest.giving_way):
        return True
    return compare_pain_feedback(previous, newest) == 'worse'


def _stage_name(patient):
    row = AvailabilityStatus.objects.filter(patient=patient).first()
    if not row or not row.stage_number:
        return ''
    episode = patient.injury_episodes.filter(closed_at__isnull=True, pathway__isnull=False).first()
    if episode is None:
        return ''
    stage = RehabStage.objects.filter(pathway=episode.pathway, number=row.stage_number).first()
    return stage.name if stage else ''


def coach_summary(patient):
    """The whole coach view of an injured athlete, or None when RTP is off or the
    athlete has no episode and no availability row (then the screen is unchanged)."""
    if not av.enabled():
        return None
    row = AvailabilityStatus.objects.filter(patient=patient).first()
    if row is None and not av.has_active_episode(patient):
        return None
    _, newest = last_two_feedbacks(patient)
    return {
        'traffic_light': newest.traffic_light if newest else '',
        'status': av.effective_status(patient),
        'restrictions': list(row.restrictions) if row else [],
        'stage_name': _stage_name(patient),
        'checkpoint': checkpoint_state(patient) or '',
        'injury_signal': injury_signal(patient),
    }
