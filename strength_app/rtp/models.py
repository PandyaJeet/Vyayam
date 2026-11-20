"""RTP models. Tier 1: S1 AuditLog, S2 CoachTherapistLink, S3 AvailabilityStatus,
S6 RehabPathway / RehabStage / InjuryEpisode. Tier 2: S5 ClearanceRecord,
S7 Checkpoint / CheckpointMeasure.

Registered under the strength_app app label (imported at the bottom of
strength_app/models.py). FKs are strings so this module imports nothing from it.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditLog(models.Model):
    """S1. Append-only record of RTP writes, allowed or denied."""
    OUTCOME_CHOICES = [('allowed', 'Allowed'), ('denied', 'Denied')]

    created_at = models.DateTimeField(auto_now_add=True)
    actor_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='+')
    actor_role = models.CharField(max_length=12, blank=True, default='')  # therapist / coach / system
    action = models.CharField(max_length=40)
    outcome = models.CharField(max_length=10, choices=OUTCOME_CHOICES)
    patient = models.ForeignKey('strength_app.PatientProfile', null=True, blank=True,
                                on_delete=models.SET_NULL, related_name='+')
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.actor_role} {self.action} {self.outcome}"


class CoachTherapistLink(models.Model):
    """S2. A coach is supervised by a therapist. The therapist-athlete link is the
    existing PatientProfile.assigned_therapist; the coach-athlete link is the
    existing CoachPatientLink."""
    coach = models.ForeignKey('strength_app.TherapistProfile', on_delete=models.CASCADE,
                              related_name='supervising_links')
    therapist = models.ForeignKey('strength_app.TherapistProfile', on_delete=models.CASCADE,
                                  related_name='supervised_links')
    is_active = models.BooleanField(default=True)
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('coach', 'therapist')

    def clean(self):
        if self.coach_id and self.coach_id == self.therapist_id:
            raise ValidationError('A coach cannot supervise themselves.')

    def __str__(self):
        return f"{self.coach.name} supervised by {self.therapist.name}"


class AvailabilityStatus(models.Model):
    """S3. One row per athlete. A hold overlays the base status, so the stage
    number survives a hold and is never touched by it."""
    BASE_CHOICES = [
        ('available', 'Available'),
        ('modified', 'Modified'),
        ('rehab_stage', 'Rehab stage'),
        ('restricted', 'Restricted'),
    ]
    patient = models.OneToOneField('strength_app.PatientProfile', on_delete=models.CASCADE,
                                   related_name='availability')
    base_status = models.CharField(max_length=12, choices=BASE_CHOICES, default='available')
    stage_number = models.PositiveSmallIntegerField(null=True, blank=True)
    medical_hold = models.BooleanField(default=False)
    restrictions = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient_id}: {'medical_hold' if self.medical_hold else self.base_status}"


class RehabPathway(models.Model):
    """S6. A pathway container. Content is blank until the clinician provides it."""
    key = models.SlugField(max_length=30, unique=True)
    name = models.CharField(max_length=80, blank=True, default='')

    def __str__(self):
        return self.key


class RehabStage(models.Model):
    """S6. One rung of the generic ladder. Criteria are BLANK by spec."""
    pathway = models.ForeignKey(RehabPathway, on_delete=models.CASCADE, related_name='stages')
    number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=80, blank=True, default='')
    entry_criteria = models.JSONField(default=list, blank=True)
    exit_criteria = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ('pathway', 'number')
        ordering = ['pathway', 'number']

    def __str__(self):
        return f"{self.pathway.key} stage {self.number}"


class InjuryEpisode(models.Model):
    """S6. An athlete has an active episode while closed_at is null. The stage
    number lives on AvailabilityStatus and changes only by therapist action."""
    patient = models.ForeignKey('strength_app.PatientProfile', on_delete=models.CASCADE,
                                related_name='injury_episodes')
    pathway = models.ForeignKey(RehabPathway, null=True, blank=True, on_delete=models.PROTECT,
                                related_name='episodes')
    opened_by = models.ForeignKey('strength_app.TherapistProfile', null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name='+')
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-opened_at']

    def __str__(self):
        return f"{self.patient_id} episode {'open' if self.closed_at is None else 'closed'}"


class ClearanceRecord(models.Model):
    """S5. A therapist's decision. Only a therapist writes one; nothing approves
    automatically. A red flag or a hold invalidates an approved row. A clearance
    never loosens a gate or lifts a hold: no gate reads it."""
    APPROVED, DECLINED = 'approved', 'declined'
    DECISION_CHOICES = [(APPROVED, 'Approved'), (DECLINED, 'Declined')]

    patient = models.ForeignKey('strength_app.PatientProfile', on_delete=models.CASCADE,
                                related_name='clearances')
    decision = models.CharField(max_length=10, choices=DECISION_CHOICES)
    restrictions = models.JSONField(default=list, blank=True)
    note = models.TextField(blank=True, default='')
    decided_by = models.ForeignKey('strength_app.TherapistProfile', null=True,
                                   on_delete=models.SET_NULL, related_name='+')
    decided_at = models.DateTimeField(auto_now_add=True)
    invalidated_at = models.DateTimeField(null=True, blank=True)
    invalidated_reason = models.CharField(max_length=40, blank=True, default='')

    class Meta:
        ordering = ['-decided_at', '-id']

    @classmethod
    def active_for(cls, patient):
        return cls.objects.filter(patient=patient, decision=cls.APPROVED,
                                  invalidated_at__isnull=True)

    @classmethod
    def invalidate_active(cls, patient, reason):
        """Returns how many approved clearances were invalidated."""
        from django.utils import timezone
        return cls.active_for(patient).update(invalidated_at=timezone.now(),
                                              invalidated_reason=reason)

    def __str__(self):
        return f"{self.patient_id} {self.decision}"


class Checkpoint(models.Model):
    """S7. A gate check opened by a therapist. Due while passed_at is null.
    Passing it never changes the stage number: set_stage is a separate act."""
    patient = models.ForeignKey('strength_app.PatientProfile', on_delete=models.CASCADE,
                                related_name='checkpoints')
    stage_number = models.PositiveSmallIntegerField(null=True, blank=True)
    opened_by = models.ForeignKey('strength_app.TherapistProfile', null=True,
                                  on_delete=models.SET_NULL, related_name='+')
    opened_at = models.DateTimeField(auto_now_add=True)
    passed_by = models.ForeignKey('strength_app.TherapistProfile', null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name='+')
    passed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-opened_at', '-id']

    def __str__(self):
        return f"{self.patient_id} checkpoint {'passed' if self.passed_at else 'due'}"


class CheckpointMeasure(models.Model):
    """S7. One measure on a checkpoint. A coach-entered measure stays pending
    until a therapist confirms it."""
    PENDING, CONFIRMED = 'pending', 'confirmed'
    STATUS_CHOICES = [(PENDING, 'Pending'), (CONFIRMED, 'Confirmed')]
    MEASURE_CHOICES = [
        ('hop', 'Hop'), ('sprint', 'Sprint'), ('nordic', 'Nordic'),
        ('range', 'Range'), ('manual_strength', 'Manual strength'), ('palpation', 'Palpation'),
    ]

    checkpoint = models.ForeignKey(Checkpoint, on_delete=models.CASCADE, related_name='measures')
    measure = models.CharField(max_length=20, choices=MEASURE_CHOICES)
    value = models.CharField(max_length=60)
    entered_by = models.ForeignKey('strength_app.TherapistProfile', null=True,
                                   on_delete=models.SET_NULL, related_name='+')
    entered_by_role = models.CharField(max_length=12)  # therapist / coach
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    confirmed_by = models.ForeignKey('strength_app.TherapistProfile', null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='+')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f"{self.measure} {self.status}"
