from datetime import timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from therapist_app.models import (
    Prescription,
    SessionLog,
    SessionLogItem,
    Therapist,
    TherapistPatientLink,
)


class TherapistModelTests(TestCase):
    def test_initials_handles_dr_prefix(self):
        user = User.objects.create_user(username="dr_meera", password="testpass")
        therapist = Therapist.objects.create(user=user, full_name="Dr. Meera Shah")
        self.assertEqual(therapist.initials, "MS")


class TherapistPatientLinkTests(TestCase):
    def test_current_week_from_program_start(self):
        therapist_user = User.objects.create_user(username="dr_a", password="testpass")
        therapist = Therapist.objects.create(user=therapist_user, full_name="Dr. A")
        patient_user = User.objects.create_user(username="patient_a", password="testpass")
        start_date = timezone.now().date() - timedelta(days=15)
        link = TherapistPatientLink.objects.create(
            therapist=therapist,
            patient=patient_user,
            program_start=start_date,
            status="active",
        )
        self.assertEqual(link.current_week, 3)


class PrescriptionModelTests(TestCase):
    def test_unique_link_week_constraint(self):
        therapist_user = User.objects.create_user(username="dr_b", password="testpass")
        therapist = Therapist.objects.create(user=therapist_user, full_name="Dr. B")
        patient_user = User.objects.create_user(username="patient_b", password="testpass")
        link = TherapistPatientLink.objects.create(
            therapist=therapist,
            patient=patient_user,
            status="active",
        )
        Prescription.objects.create(link=link, week_number=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Prescription.objects.create(link=link, week_number=1)


class SessionLogTests(TestCase):
    def test_completion_pct_and_duration(self):
        therapist_user = User.objects.create_user(username="dr_c", password="testpass")
        therapist = Therapist.objects.create(user=therapist_user, full_name="Dr. C")
        patient_user = User.objects.create_user(username="patient_c", password="testpass")
        link = TherapistPatientLink.objects.create(
            therapist=therapist,
            patient=patient_user,
            status="active",
        )
        prescription = Prescription.objects.create(link=link, week_number=1)
        session = SessionLog.objects.create(link=link, prescription=prescription)
        now = timezone.now()
        session.started_at = now - timedelta(minutes=30)
        session.completed_at = now
        session.save(update_fields=["started_at", "completed_at"])

        SessionLogItem.objects.create(session_log=session, order=1, exercise_name="Squat")
        SessionLogItem.objects.create(
            session_log=session,
            order=2,
            exercise_name="Row",
            completed_at=now,
        )

        self.assertEqual(session.duration_minutes, 30)
        self.assertEqual(session.completion_pct, 50)
