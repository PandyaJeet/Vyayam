"""S7 checkpoints. Only a therapist can pass a gate or change a stage number.

A coach may enter hop, sprint and Nordic results. They stay pending until a
therapist confirms them. Range, manual strength and palpation are rejected from
a coach. Passing a gate does not touch the stage number; set_stage does that.
"""
from django.utils import timezone

from . import audit
from . import availability as av
from .models import Checkpoint, CheckpointMeasure

COACH_MEASURES = frozenset({'hop', 'sprint', 'nordic'})
THERAPIST_ONLY_MEASURES = frozenset({'range', 'manual_strength', 'palpation'})


def _deny(action, actor, role, patient, reason, **detail):
    audit.log(action, 'denied', actor=actor, role=role or '', patient=patient,
              reason=reason, **detail)
    return None


def open_checkpoint(patient, *, actor, stage_number=None):
    """Therapist only. The checkpoint is due until a therapist passes it."""
    role = av.resolve_role(actor, patient)
    if role != av.THERAPIST:
        return _deny('open_checkpoint', actor, role, patient, 'therapist_only')
    row = Checkpoint.objects.create(patient=patient, stage_number=stage_number, opened_by=actor)
    audit.log('open_checkpoint', 'allowed', actor=actor, role=role, patient=patient)
    return row


def enter_measure(checkpoint, measure, value, *, actor):
    """Returns the CheckpointMeasure, or None if denied."""
    patient = checkpoint.patient
    role = av.resolve_role(actor, patient)
    if role is None:
        return _deny('enter_measure', actor, role, patient, 'no_link', measure=str(measure)[:20])
    if measure not in COACH_MEASURES | THERAPIST_ONLY_MEASURES:
        return _deny('enter_measure', actor, role, patient, 'bad_measure', measure=str(measure)[:20])
    if checkpoint.passed_at:
        return _deny('enter_measure', actor, role, patient, 'checkpoint_closed', measure=measure)
    if role == av.COACH and measure in THERAPIST_ONLY_MEASURES:
        return _deny('enter_measure', actor, role, patient, 'coach_cannot_enter', measure=measure)
    row = CheckpointMeasure.objects.create(
        checkpoint=checkpoint, measure=measure, value=str(value)[:60],
        entered_by=actor, entered_by_role=role,
        status=(CheckpointMeasure.CONFIRMED if role == av.THERAPIST else CheckpointMeasure.PENDING),
        confirmed_by=actor if role == av.THERAPIST else None,
        confirmed_at=timezone.now() if role == av.THERAPIST else None,
    )
    audit.log('enter_measure', 'allowed', actor=actor, role=role, patient=patient,
              measure=measure, status=row.status)
    return row


def confirm_measure(measure_row, *, actor):
    """Therapist only."""
    patient = measure_row.checkpoint.patient
    role = av.resolve_role(actor, patient)
    if role != av.THERAPIST:
        return _deny('confirm_measure', actor, role, patient, 'therapist_only',
                     measure=measure_row.measure) or False
    measure_row.status = CheckpointMeasure.CONFIRMED
    measure_row.confirmed_by, measure_row.confirmed_at = actor, timezone.now()
    measure_row.save(update_fields=['status', 'confirmed_by', 'confirmed_at'])
    audit.log('confirm_measure', 'allowed', actor=actor, role=role, patient=patient,
              measure=measure_row.measure)
    return True


def pass_gate(checkpoint, *, actor):
    """Therapist only. Refused while the athlete is on hold or any measure is
    still pending. Never changes the stage number."""
    patient = checkpoint.patient
    role = av.resolve_role(actor, patient)
    if role != av.THERAPIST:
        return _deny('pass_gate', actor, role, patient, 'therapist_only') or False
    if checkpoint.passed_at:
        return _deny('pass_gate', actor, role, patient, 'already_passed') or False
    if av.is_held(patient):
        return _deny('pass_gate', actor, role, patient, 'hold_active') or False
    if checkpoint.measures.filter(status=CheckpointMeasure.PENDING).exists():
        return _deny('pass_gate', actor, role, patient, 'pending_measures') or False
    checkpoint.passed_by, checkpoint.passed_at = actor, timezone.now()
    checkpoint.save(update_fields=['passed_by', 'passed_at'])
    audit.log('pass_gate', 'allowed', actor=actor, role=role, patient=patient)
    return True


def checkpoint_state(patient):
    """'due', 'passed' or None, from the newest checkpoint. Safe to show a coach."""
    row = Checkpoint.objects.filter(patient=patient).first()
    if row is None:
        return None
    return 'passed' if row.passed_at else 'due'
