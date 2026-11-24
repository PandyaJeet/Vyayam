"""
Athlete PWA (2026-07) — seed_football_demo + /athlete/* front end.

Pins:
  - seed_football_demo is idempotent (run twice → identical row counts)
  - football-track + coach-linked login routes to /athlete/today/
  - all three athlete tabs render with the seeded data
  - therapist-managed login still routes to the rehab flow (no regression)
  - non-athlete self-serve patients cannot reach /athlete/* (redirected out)
"""

from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from strength_app.models import (
    CoachPatientLink, MatchDate, PatientProfile, WorkoutSession,
)


def _seed():
    call_command('seed_football_demo', stdout=StringIO())


class TestSeedFootballDemo(TestCase):

    def test_seed_is_idempotent(self):
        _seed()
        _seed()
        self.assertEqual(
            PatientProfile.objects.filter(phone='9000000005').count(), 1)
        patient = PatientProfile.objects.get(patient_id='FBDEMO_KABIR')
        self.assertEqual(
            WorkoutSession.objects.filter(patient=patient).count(), 14)
        self.assertEqual(MatchDate.objects.filter(patient=patient).count(), 3)
        self.assertEqual(
            CoachPatientLink.objects.filter(patient=patient, is_active=True).count(), 1)

    def test_seeded_level_is_mid_tier(self):
        _seed()
        patient = PatientProfile.objects.get(patient_id='FBDEMO_KABIR')
        self.assertEqual(patient.football_profile.football_level, 3)


class TestAthleteRouting(TestCase):

    def setUp(self):
        cache.clear()
        _seed()

    def _login_kabir(self):
        return self.client.post(
            reverse('patient_login'),
            {'phone': '9000000005', 'password': 'athlete'},
        )

    def test_athlete_login_routes_to_athlete_today(self):
        resp = self._login_kabir()
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('athlete_today'))

    def test_athlete_tabs_render(self):
        self._login_kabir()
        for name, probe in [
            ('athlete_today', "Today's Training, Kabir"),
            ('athlete_progress', 'Your Performance, Kabir'),
            ('athlete_profile', 'Arjun Mehta'),
        ]:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 200, name)
            self.assertContains(resp, probe)

    def test_anonymous_athlete_urls_redirect_to_login(self):
        resp = self.client.get(reverse('athlete_today'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('patient_login'))


class TestNoRehabRegression(TestCase):

    def setUp(self):
        cache.clear()
        _seed()
        call_command('seed_therapist_demo', stdout=StringIO())

    def test_therapist_managed_patient_still_routes_to_rehab(self):
        resp = self.client.post(
            reverse('patient_login'),
            {'phone': '9000000001', 'password': 'patient'},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('therapist_session_today'))

    def test_rehab_patient_cannot_enter_athlete_pwa(self):
        self.client.post(
            reverse('patient_login'),
            {'phone': '9000000001', 'password': 'patient'},
        )
        resp = self.client.get(reverse('athlete_today'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('therapist_session_today'))
