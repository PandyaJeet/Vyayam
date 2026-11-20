"""S3 availability service + S4 guards. The one place that decides who may change what.

Authority is therapist > coach > app.
- Only a therapist lifts a hold, changes a stage number, or loosens a status.
- A coach can add restriction or a hold, never remove one. A coach is locked out
  completely while the athlete is on medical hold or in a rehab stage.
- The app ('system') can only place a hold. It never lifts one, never declares an
  athlete fit, and never touches the stage number.
Every denied write is written to AuditLog as "denied".

Pain for gating comes from the session feedback record, never PainEvent.
Everything here is inert unless settings.RTP_ENABLED is on.
"""
from django.conf import settings

from . import audit, config
from .models import AvailabilityStatus, ClearanceRecord, CoachTherapistLink, InjuryEpisode

AVAILABLE, MODIFIED, REHAB_STAGE, RESTRICTED = 'available', 'modified', 'rehab_stage', 'restricted'
MEDICAL_HOLD = 'medical hold'

THERAPIST, COACH, SYSTEM = 'therapist', 'coach', 'system'

# Loosest to tightest. A coach may only move to an equal or higher rank.
_RANK = {AVAILABLE: 0, MODIFIED: 1, RESTRICTED: 2}

# Keys a flag review must never carry. A flag review cannot change status.
_STATUS_KEYS = {'status', 'set_status', 'override', 'stage', 'stage_number',
                'medical_hold', 'availability', 'base_status'}

LOCKED_MESSAGE = 'Locked. This athlete is under therapist control.'
REDUCE_ONLY_MESSAGE = 'This athlete is restricted. You can only remove exercises.'


def enabled():
    return bool(getattr(settings, 'RTP_ENABLED', False))


# --- reads ------------------------------------------------------------------

def _row(patient):
    return AvailabilityStatus.objects.filter(patient=patient).first()


def effective_status(patient):
    """'available', 'modified', 'rehab stage N', 'restricted' or 'medical hold'. Hold wins."""
    row = _row(patient)
    if row is None:
        return AVAILABLE
    if row.medical_hold:
        return MEDICAL_HOLD
    if row.base_status == REHAB_STAGE:
        return f'rehab stage {row.stage_number}' if row.stage_number else 'rehab stage'
    return row.base_status


def is_held(patient):
    if not enabled():
        return False
    row = _row(patient)
    return bool(row and row.medical_hold)


def has_active_episode(patient):
    return InjuryEpisode.objects.filter(patient=patient, closed_at__isnull=True).exists()


def resolve_role(actor, patient):
    """therapist, coach or None. `actor` is a TherapistProfile."""
    if actor is None:
        return None
    if patient.assigned_therapist_id == actor.id:
        return THERAPIST
    supervised = CoachTherapistLink.objects.filter(
        therapist=actor, is_active=True,
        coach__athletes__patient=patient, coach__athletes__is_active=True,
    ).exists()
    if supervised:
        return THERAPIST
    if patient.coaches.filter(coach=actor, is_active=True).exists():
        return COACH
    return None


# --- writes -----------------------------------------------------------------

def _deny(action, actor, role, patient, reason, **detail):
    audit.log(action, 'denied', actor=actor, role=role or '', patient=patient,
              reason=reason, **detail)
    return False


def _get_or_create(patient):
    row, _ = AvailabilityStatus.objects.get_or_create(patient=patient)
    return row


def place_hold(patient, *, actor=None, role=SYSTEM, reason=''):
    """Any known role may place a hold. Never touches the stage number."""
    if role != SYSTEM:
        role = resolve_role(actor, patient)
        if role is None:
            return _deny('place_hold', actor, None, patient, 'no_link')
    row = _get_or_create(patient)
    newly_held = not row.medical_hold
    if newly_held:
        row.medical_hold = True
        row.save(update_fields=['medical_hold', 'updated_at'])
    # S5: a red flag invalidates an approved clearance. The therapist must decide again.
    invalidated = ClearanceRecord.invalidate_active(patient, 'red_flag')
    audit.log('place_hold', 'allowed', actor=actor, role=role, patient=patient, reason=reason,
              clearances_invalidated=invalidated)
    if newly_held:
        from . import notify  # S10: a hold is never silent
        notify.hold_placed(patient, reason)
    return True


def lift_hold(patient, *, actor, role=None):
    """Therapist only."""
    role = role or resolve_role(actor, patient)
    if role != THERAPIST:
        return _deny('lift_hold', actor, role, patient, 'therapist_only')
    row = _get_or_create(patient)
    row.medical_hold = False
    row.save(update_fields=['medical_hold', 'updated_at'])
    audit.log('lift_hold', 'allowed', actor=actor, role=role, patient=patient)
    return True


def set_stage(patient, number, *, actor, role=None):
    """Therapist only. The only path that writes a stage number."""
    role = role or resolve_role(actor, patient)
    if role != THERAPIST:
        return _deny('set_stage', actor, role, patient, 'therapist_only', stage=number)
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        return _deny('set_stage', actor, role, patient, 'bad_stage', stage=number)
    row = _get_or_create(patient)
    old = row.stage_number
    row.base_status, row.stage_number = REHAB_STAGE, number
    row.save(update_fields=['base_status', 'stage_number', 'updated_at'])
    audit.log('set_stage', 'allowed', actor=actor, role=role, patient=patient,
              old_stage=old, new_stage=number)
    return True


def set_base_status(patient, new_status, *, actor, role=None):
    """available / modified / restricted. Rehab stage goes through set_stage.
    The app can never call this successfully."""
    role = role or resolve_role(actor, patient)
    if new_status not in _RANK:
        return _deny('set_status', actor, role, patient, 'bad_status', requested=new_status)
    if role not in (THERAPIST, COACH):
        return _deny('set_status', actor, role, patient, 'not_permitted', requested=new_status)
    row = _get_or_create(patient)
    if role == COACH:
        if row.medical_hold or row.base_status == REHAB_STAGE:
            return _deny('set_status', actor, role, patient, 'coach_locked', requested=new_status)
        if _RANK[new_status] < _RANK.get(row.base_status, 0):
            return _deny('set_status', actor, role, patient, 'coach_cannot_loosen',
                         requested=new_status)
    old = row.base_status
    row.base_status = new_status
    if old == REHAB_STAGE:
        row.stage_number = None
    row.save(update_fields=['base_status', 'stage_number', 'updated_at'])
    audit.log('set_status', 'allowed', actor=actor, role=role, patient=patient,
              old=old, new=new_status)
    return True


# --- S4 guards on the coach screens -----------------------------------------
# These screens are coach screens, so the actor is always treated as a coach here.

def override_lock_message(patient):
    """Message when the override screen is fully locked, else None. Read-only, no audit."""
    if not enabled():
        return None
    row = _row(patient)
    if row and (row.medical_hold or row.base_status == REHAB_STAGE):
        return LOCKED_MESSAGE
    return None


def override_reduce_only(patient):
    if not enabled():
        return False
    row = _row(patient)
    return bool(row and not row.medical_hold and row.base_status == RESTRICTED)


def check_coach_override(patient, actor, items):
    """(allowed, message). Hold or rehab stage: reject all. Restricted: only
    'remove' (and 'keep', which changes nothing) pass."""
    if not enabled():
        return True, ''
    locked = override_lock_message(patient)
    if locked:
        _deny('coach_override', actor, COACH, patient, 'locked',
              status=effective_status(patient))
        return False, locked
    if override_reduce_only(patient):
        for item in items if isinstance(items, list) else []:
            action = item.get('action', 'add') if isinstance(item, dict) else 'add'
            if action not in ('remove', 'keep'):
                _deny('coach_override', actor, COACH, patient, 'restricted_reduce_only',
                      requested_action=str(action)[:20])
                return False, REDUCE_ONLY_MESSAGE
    return True, ''


def check_flag_review(patient, actor, post):
    """(allowed, message). A flag review may acknowledge, never change status."""
    if not enabled():
        return True, ''
    attempted = sorted(k for k in post.keys() if k in _STATUS_KEYS)
    if attempted:
        _deny('flag_review', actor, COACH, patient, 'status_change_attempt', keys=attempted)
        return False, 'A flag review cannot change status.'
    return True, ''


# --- hold rule (SPINE_SPEC S9 hold rule only; not wired to any view yet) -----

def feedback_triggers_hold(patient, feedback):
    """Newest session feedback only. A null never holds. Swelling and giving way
    count only for an athlete with an active episode."""
    if feedback is None:
        return False
    if getattr(feedback, 'traffic_light', None) == 'red':
        return True
    if getattr(feedback, 'locking_or_catching', None) is True:
        return True
    if has_active_episode(patient):
        if config.HOLD_ON_SWELLING and getattr(feedback, 'swelling_today', None) is True:
            return True
        if config.HOLD_ON_GIVING_WAY and getattr(feedback, 'giving_way', None) is True:
            return True
    return False


def apply_feedback_hold(patient, feedback):
    """Hold and notify only. Never changes the stage number or any load."""
    if not enabled() or not feedback_triggers_hold(patient, feedback):
        return False
    return place_hold(patient, role=SYSTEM, reason='session_feedback')
