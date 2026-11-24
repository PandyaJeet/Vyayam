"""S5 clearance decisions. Therapist only. No auto-approve, ever.

A clearance records a therapist's decision and restrictions. It never lifts a
hold, never changes the stage number and is never read by a gate, so it cannot
loosen one. A red flag (any hold, see availability.place_hold) invalidates an
approved clearance; the therapist has to decide again.
"""
from . import audit
from . import availability as av
from .models import ClearanceRecord


def decide(patient, decision, *, actor, restrictions=(), note=''):
    """Record a therapist decision. Returns the ClearanceRecord, or None if denied."""
    role = av.resolve_role(actor, patient)

    def deny(reason):
        audit.log('clearance_decision', 'denied', actor=actor, role=role or '',
                  patient=patient, reason=reason, decision=str(decision)[:20])
        return None

    if role != av.THERAPIST:
        return deny('therapist_only')
    if decision not in (ClearanceRecord.APPROVED, ClearanceRecord.DECLINED):
        return deny('bad_decision')
    if decision == ClearanceRecord.APPROVED and av.is_held(patient):
        return deny('hold_active')  # lift the hold first; approval never lifts it
    # A new decision replaces any approval still standing.
    ClearanceRecord.invalidate_active(patient, 'superseded')
    row = ClearanceRecord.objects.create(
        patient=patient, decision=decision, restrictions=list(restrictions), note=note,
        decided_by=actor)
    audit.log('clearance_decision', 'allowed', actor=actor, role=role, patient=patient,
              decision=decision)
    return row


def active_clearance(patient):
    return ClearanceRecord.active_for(patient).first()
