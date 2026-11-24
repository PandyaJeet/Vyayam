"""S10 therapist notification, in-app. Nothing else in the app writes a Notification.

A hold is never silent: place_hold calls hold_placed, which writes one row per
therapist who has authority over the athlete (the assigned therapist and any
therapist supervising the athlete's coach). A coach never gets one.

The body is fixed text picked by the reason code. It never contains a raw answer
(swelling, giving way, tightness, locking), so the same row is safe on any screen.
"""
import logging

from django.utils import timezone

from . import audit
from . import availability as av
from .models import CoachTherapistLink, Notification

log = logging.getLogger(__name__)

# UNSIGNED wording, therapist-facing only. Needs physio mentor review. No raw values.
HOLD_BODIES = {
    'session_feedback': 'Training paused for {name}. Their latest session answers set off a hold.',
    'worse_feedback': 'Training paused for {name}. Their answers got worse since the last session.',
}
HOLD_BODY_DEFAULT = 'Training paused for {name}. A hold was placed.'


def recipients(patient):
    """Therapists with authority over this athlete. Never a coach."""
    ids = set()
    if patient.assigned_therapist_id:
        ids.add(patient.assigned_therapist_id)
    ids.update(CoachTherapistLink.objects.filter(
        is_active=True, coach__athletes__patient=patient, coach__athletes__is_active=True,
    ).values_list('therapist_id', flat=True))
    from ..models import TherapistProfile
    return [t for t in TherapistProfile.objects.filter(pk__in=ids)
            if av.resolve_role(t, patient) == av.THERAPIST]


def hold_placed(patient, reason=''):
    """Write the hold notices. Never raises: the hold must stand even if this fails."""
    if not av.enabled():
        return 0
    body = HOLD_BODIES.get(reason, HOLD_BODY_DEFAULT).format(name=patient.name)[:200]
    count = 0
    try:
        for therapist in recipients(patient):
            Notification.objects.create(therapist=therapist, patient=patient,
                                        kind=Notification.HOLD_PLACED, body=body)
            count += 1
        audit.log('notify_hold', 'allowed', role=av.SYSTEM, patient=patient, recipients=count)
    except Exception:
        log.exception('rtp notify failed for patient %s', patient.pk)
        return 0
    return count


def unread_for(therapist):
    return Notification.objects.filter(therapist=therapist, read_at__isnull=True
                                       ).select_related('patient')


def mark_read(notification, *, actor):
    """Only the therapist the notice was written for."""
    if actor is None or notification.therapist_id != actor.id:
        audit.log('notify_read', 'denied', actor=actor, role='', patient=notification.patient,
                  reason='not_recipient')
        return False
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=['read_at'])
    return True
