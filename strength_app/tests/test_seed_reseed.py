"""Reseeding the therapist demo after the demo was used.

Render's build_demo.sh reruns the seeders on every demo deploy. Session
history (SessionReport / SessionLog) is PROTECT (B-X2), so the demo wipe has
to delete demo-owned history itself before it deletes the demo Users, and
must leave non-demo history alone. See .r2_tmp/seed-wipe-plan/PLAN.md.
"""
from io import StringIO
from unittest import mock

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from strength_app.models import FoodItem, PatientProfile
from therapist_app.management.commands import seed_therapist_demo
from therapist_app.models import (
    Prescription,
    PrescriptionItem,
    SessionLog,
    SessionReport,
    Therapist,
    TherapistPatientLink,
)

BUILD_DEMO_ORDER = [
    'seed_food_database',
    'seed_therapist_demo',
    'seed_football_demo',
    'seed_demo_patient',
]


def _seed(name='seed_therapist_demo'):
    call_command(name, stdout=StringIO(), stderr=StringIO())


def _history(link, profile):
    rx = Prescription.objects.create(
        link=link, week_number=1, published_at=timezone.now())
    PrescriptionItem.objects.create(
        prescription=rx, exercise_id='ex_glute_bridge',
        exercise_name='Glute bridge')
    log = SessionLog.objects.create(link=link, prescription=rx)
    report = SessionReport.objects.create(
        link=link, session_log=log, patient=profile,
        report_date=log.started_at.date())
    return log, report


class SeedReseedTests(TestCase):
    def setUp(self):
        cache.clear()
        _seed()

    def _demo_session(self, phone='9000000001', password='patient'):
        """Login, start, complete, start again: 1 report and open logs, the
        shape seen on the live demo DB on 2026-11-28."""
        c = self.client_class()
        resp = c.post(reverse('patient_login'),
                      {'phone': phone, 'password': password})
        self.assertEqual(resp.status_code, 302)
        c.post(reverse('therapist_session_start'))
        c.post(reverse('therapist_session_complete'), {'overall_pain': 1})
        c.post(reverse('therapist_session_start'))

    def test_reseed_after_demo_session(self):
        self._demo_session()
        self.assertEqual(SessionReport.objects.count(), 1)
        self.assertGreaterEqual(SessionLog.objects.count(), 2)

        _seed()

        self.assertEqual(SessionReport.objects.count(), 0)
        self.assertEqual(SessionLog.objects.count(), 0)
        resp = self.client_class().post(
            reverse('patient_login'),
            {'phone': '9000000001', 'password': 'patient'})
        self.assertEqual(resp.status_code, 302)

    def test_reseed_with_invited_patient_history(self):
        c = self.client_class()
        self.assertTrue(c.login(username='dr_shah', password='simple'))
        c.post(reverse('therapist_invite_patient'),
               {'name': 'Judge Pat', 'email': 'judge@x.com',
                'phone': '9111111111', 'primary_condition': 'knee'})
        link = TherapistPatientLink.objects.get(patient__username='judge@x.com')
        c.post(reverse('therapist_simulate_accept', args=[link.id]))
        profile = PatientProfile.objects.get(user__username='judge@x.com')
        _history(link, profile)

        _seed()

        self.assertEqual(SessionReport.objects.count(), 0)
        self.assertEqual(SessionLog.objects.count(), 0)
        self.assertTrue(User.objects.filter(username='judge@x.com').exists())
        self.assertTrue(PatientProfile.objects.filter(pk=profile.pk).exists())

    def test_reseed_keeps_non_demo_history(self):
        therapist_user = User.objects.create_user('dr_real', password='x')
        therapist = Therapist.objects.create(
            user=therapist_user, full_name='Dr. Real')
        patient_user = User.objects.create_user('real_patient', password='x')
        profile = PatientProfile.objects.create(
            user=patient_user, patient_id='REAL_001', name='Real Patient',
            phone='9222222222', age=40, goals='Rehab',
            password=make_password('x'))
        link = TherapistPatientLink.objects.create(
            therapist=therapist, patient=patient_user, status='active',
            accepted_at=timezone.now())
        log, report = _history(link, profile)

        _seed()

        self.assertTrue(SessionReport.objects.filter(pk=report.pk).exists())
        self.assertTrue(SessionLog.objects.filter(pk=log.pk).exists())
        self.assertTrue(TherapistPatientLink.objects.filter(pk=link.pk).exists())

    def test_reseed_rolls_back_when_still_protected(self):
        self._demo_session()
        reports = SessionReport.objects.count()
        logs = SessionLog.objects.count()
        self.assertEqual(reports, 1)

        # Something else still protects a demo User: the wipe must be all or
        # nothing, so the history deletes before it roll back.
        with mock.patch.object(seed_therapist_demo, 'User') as fake_user:
            fake_user.objects.filter.return_value.delete.side_effect = (
                ProtectedError('still protected', set()))
            with self.assertRaises(ProtectedError):
                _seed()

        self.assertEqual(SessionReport.objects.count(), reports)
        self.assertEqual(SessionLog.objects.count(), logs)

    def test_build_order_twice(self):
        def run_build_seeders():
            for name in BUILD_DEMO_ORDER:
                _seed(name)
            return (
                User.objects.count(),
                PatientProfile.objects.count(),
                TherapistPatientLink.objects.count(),
                FoodItem.objects.count(),
            )

        self._demo_session()
        first = run_build_seeders()
        self._demo_session()
        second = run_build_seeders()
        self.assertEqual(first, second)
        self.assertEqual(SessionReport.objects.count(), 0)
