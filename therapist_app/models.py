"""
VYAYAM THERAPIST CONSOLE — Django Models
Models for the B2B2C therapist dashboard. Kept isolated from strength_app
to avoid clashing with the legacy TherapistProfile / TherapistPrescription
/ ProgressReport / CoachPatientLink models still in use there.
"""

import uuid

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('active', 'Active'),
    ('archived', 'Archived'),
]

CONDITION_TONE_CHOICES = [
    ('primary', 'Primary'),
    ('warn', 'Warn'),
    ('error', 'Error'),
    ('neutral', 'Neutral'),
    ('green', 'Green'),
]

REPORT_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('ready', 'Ready'),
    ('flagged', 'Flagged'),
]

REPORT_GENERATED_BY = [
    ('auto', 'Auto'),
    ('therapist', 'Manual'),
]


class Therapist(models.Model):
    """A licensed physiotherapist with access to the therapist console."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='therapist')
    full_name = models.CharField(max_length=200)
    specialization = models.CharField(max_length=200, blank=True, default='')
    registration_number = models.CharField(max_length=100, blank=True, default='')
    clinic_name = models.CharField(max_length=200, blank=True, default='')
    seat_limit = models.IntegerField(default=12)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return self.full_name

    @property
    def initials(self):
        parts = [p for p in self.full_name.replace('Dr.', '').strip().split() if p]
        if not parts:
            return '?'
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @property
    def active_link_count(self):
        return self.patient_links.filter(status='active').count()

    @property
    def pending_link_count(self):
        return self.patient_links.filter(status='pending').count()


class TherapistPatientLink(models.Model):
    """Links a therapist to a patient. UUID PK so URLs don't leak ints."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    therapist = models.ForeignKey(Therapist, on_delete=models.CASCADE, related_name='patient_links')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='therapist_links')

    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    full_name = models.CharField(max_length=200, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=15, blank=True, default='')
    age = models.IntegerField(null=True, blank=True)
    sex = models.CharField(max_length=12, blank=True, default='')
    location = models.CharField(max_length=120, blank=True, default='')

    primary_condition = models.CharField(max_length=200, blank=True, default='')
    condition_tone = models.CharField(max_length=10, choices=CONDITION_TONE_CHOICES, default='primary')
    injury_date = models.DateField(null=True, blank=True)
    program_start = models.DateField(null=True, blank=True)
    total_weeks = models.IntegerField(default=12)

    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-invited_at']
        constraints = [
            models.UniqueConstraint(
                fields=['therapist', 'patient'],
                name='unique_therapist_patient',
            ),
        ]

    def __str__(self):
        return f"{self.therapist.full_name} → {self.full_name or self.patient.username}"

    @property
    def display_name(self):
        return self.full_name or self.patient.get_full_name() or self.patient.username

    @property
    def initials(self):
        name = self.display_name.strip()
        parts = [p for p in name.split() if p]
        if not parts:
            return '?'
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @property
    def current_week(self):
        if not self.program_start:
            return 0
        from django.utils import timezone
        days = (timezone.now().date() - self.program_start).days
        return max(1, (days // 7) + 1)


class Prescription(models.Model):
    """One prescription per program week, per patient link."""

    link = models.ForeignKey(TherapistPatientLink, on_delete=models.CASCADE, related_name='prescriptions')
    week_number = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    notes_for_patient = models.TextField(blank=True, default='')

    # Auto-save buffer for Program Builder. Mirrors the live edit state every 30s.
    draft_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-week_number', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['link', 'week_number'],
                name='unique_link_week',
            ),
        ]

    def __str__(self):
        return f"{self.link.display_name} · Week {self.week_number}"

    @property
    def is_published(self):
        return self.published_at is not None


class PrescriptionItem(models.Model):
    """A single exercise within a prescription. Uses exercise_id (CharField) +
    denormalized exercise_name to match the existing strength_app convention
    (no Exercise model row table; exercises live in exercise_content.py)."""

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    order = models.IntegerField(default=0)

    exercise_id = models.CharField(max_length=100)
    exercise_name = models.CharField(max_length=200)
    movement_pattern = models.CharField(max_length=60, blank=True, default='')

    sets = models.IntegerField(default=3)
    reps = models.IntegerField(default=10)
    load = models.CharField(max_length=80, blank=True, default='BW')
    rest_seconds = models.IntegerField(default=60)
    tempo = models.CharField(max_length=40, blank=True, default='')
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.prescription} · {self.order}. {self.exercise_name}"


class TherapistMessage(models.Model):
    """A single message in the therapist↔patient async chat."""

    link = models.ForeignKey(TherapistPatientLink, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='therapist_messages_sent')
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['sent_at']

    def __str__(self):
        return f"{self.sender.username} @ {self.sent_at:%Y-%m-%d %H:%M}: {self.body[:40]}"

    @property
    def is_from_therapist(self):
        return hasattr(self.sender, 'therapist')


class TherapistPatientHealthProfile(models.Model):
    """Therapist-managed clinical intake. Filled by the therapist via the
    "Edit patient details" modal — the patient never sees this form. The
    therapist is the source of truth for diagnosis, side, and goals."""

    SIDE_CHOICES = [
        ('left', 'Left'),
        ('right', 'Right'),
        ('bilateral', 'Bilateral'),
        ('na', 'N/A'),
    ]

    link = models.OneToOneField(
        TherapistPatientLink, on_delete=models.CASCADE, related_name='health_profile'
    )

    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)

    affected_side = models.CharField(max_length=10, choices=SIDE_CHOICES, blank=True, default='')
    surgery_date = models.DateField(null=True, blank=True)
    pain_medications = models.TextField(blank=True, default='')
    other_conditions = models.TextField(blank=True, default='')
    emergency_contact_name = models.CharField(max_length=200, blank=True, default='')
    emergency_contact_phone = models.CharField(max_length=30, blank=True, default='')
    goals = models.TextField(blank=True, default='')

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Health profile · {self.link.display_name}"


class SessionLog(models.Model):
    """One workout session logged by a patient against a published Prescription.
    The therapist's History tab reads these rows; the Today tab shows the
    most recent one for the prescription's current week."""

    link = models.ForeignKey(
        TherapistPatientLink, on_delete=models.CASCADE, related_name='session_logs'
    )
    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name='session_logs'
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    overall_pain = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    overall_comment = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.link.display_name} · session @ {self.started_at:%Y-%m-%d %H:%M}"

    @property
    def is_complete(self):
        return self.completed_at is not None

    @property
    def duration_minutes(self):
        if not self.completed_at:
            return None
        return max(0, int((self.completed_at - self.started_at).total_seconds() / 60))

    @property
    def completion_pct(self):
        items = list(self.items.all())
        if not items:
            return 0
        done = sum(1 for i in items if i.completed_at is not None)
        return int(round(100.0 * done / len(items)))


class SessionLogItem(models.Model):
    """Per-exercise log inside a SessionLog. Captures pain (0-10) and
    a categorical difficulty rating per the user's spec."""

    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('right', 'Just right'),
        ('hard', 'Hard'),
        ('too_hard', 'Too hard'),
    ]

    session_log = models.ForeignKey(
        SessionLog, on_delete=models.CASCADE, related_name='items'
    )
    prescription_item = models.ForeignKey(
        PrescriptionItem, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='log_items',
    )
    order = models.IntegerField(default=0)
    exercise_id = models.CharField(max_length=100, blank=True, default='')
    exercise_name = models.CharField(max_length=200, blank=True, default='')

    sets_completed = models.IntegerField(default=0)
    pain = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    difficulty = models.CharField(
        max_length=10, choices=DIFFICULTY_CHOICES, blank=True, default='',
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.session_log} · {self.order}. {self.exercise_name}"


class ProgressReport(models.Model):
    """A generated progress report for a patient link."""

    link = models.ForeignKey(TherapistPatientLink, on_delete=models.CASCADE, related_name='progress_reports')
    title = models.CharField(max_length=200)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=REPORT_STATUS_CHOICES, default='draft')
    pdf = models.FileField(upload_to='therapist_reports/', blank=True, null=True)
    generated_by = models.CharField(max_length=10, choices=REPORT_GENERATED_BY, default='therapist')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.link.display_name} · {self.title}"
