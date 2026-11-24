"""S1 helper: one place that writes AuditLog rows."""
from .models import AuditLog


def log(action, outcome, *, actor=None, role='', patient=None, **detail):
    """Write one audit row. `actor` is a TherapistProfile or None."""
    return AuditLog.objects.create(
        actor_user=getattr(actor, 'user', None), actor_role=role, action=action,
        outcome=outcome, patient=patient, detail=detail,
    )
