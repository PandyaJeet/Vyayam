"""S13 therapist inbox: what needs this therapist. Read only, except mark-read in notify.

Scope is the athletes this therapist has therapist authority over (same rule as
availability.resolve_role). Rows carry names, statuses and counts, never a raw
swelling, giving-way, tightness or locking value.
"""
from django.db.models import Count, Q

from . import availability as av
from .models import AvailabilityStatus, Checkpoint, CheckpointMeasure, CoachTherapistLink
from .notify import unread_for


def therapist_patients(therapist):
    from ..models import PatientProfile
    supervised = CoachTherapistLink.objects.filter(therapist=therapist, is_active=True
                                                   ).values('coach_id')
    return PatientProfile.objects.filter(
        Q(assigned_therapist=therapist)
        | Q(coaches__coach__in=supervised, coaches__is_active=True)).distinct()


def inbox_for(therapist):
    """None when RTP is off. Else the three lists the inbox shows."""
    if not av.enabled():
        return None
    patients = therapist_patients(therapist)
    checkpoints = (Checkpoint.objects.filter(patient__in=patients, passed_at__isnull=True)
                   .select_related('patient')
                   .annotate(pending=Count('measures', filter=Q(
                       measures__status=CheckpointMeasure.PENDING))))
    held = (AvailabilityStatus.objects.filter(patient__in=patients, medical_hold=True)
            .select_related('patient'))
    return {
        'notifications': list(unread_for(therapist)),
        'checkpoints': list(checkpoints),
        'clearances': list(held),
    }


def unread_count(therapist):
    return unread_for(therapist).count() if av.enabled() else None
