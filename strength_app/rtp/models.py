"""RTP Tier 1 models: S1 AuditLog, S2 CoachTherapistLink, S3 AvailabilityStatus,
S6 RehabPathway / RehabStage / InjuryEpisode.

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
