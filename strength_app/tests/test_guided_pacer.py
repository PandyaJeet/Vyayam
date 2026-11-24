"""
2026-07 Part 4C — honest count-along pacer for the two PERMANENTLY guided
exercises (ankle pumps, prone glute squeeze).

Pins:
  - both exercises stay v2_ghost_supported=False (guided by design)
  - their guided session page carries the pacer + honest label
  - every other guided exercise renders WITHOUT the pacer (inert elsewhere)
"""

from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from therapist_app.models import PrescriptionItem


class TestGuidedPacer(TestCase):
    def setUp(self):
        cache.clear()
        call_command('seed_therapist_demo', stdout=StringIO())
        items = list(PrescriptionItem.objects.order_by('order'))
        items[0].exercise_id = 'ex_ankle_pumps'
        items[0].exercise_name = 'Ankle Pumps'
        items[0].save(update_fields=['exercise_id', 'exercise_name'])
        items[1].exercise_id = 'ex_prone_glute_squeeze'
        items[1].exercise_name = 'Prone Glute Squeeze'
        items[1].save(update_fields=['exercise_id', 'exercise_name'])

        resp = self.client.post(
            reverse('patient_login'),
            {'phone': '9000000001', 'password': 'patient'},
        )
        self.assertEqual(resp.status_code, 302, 'patient login failed')
        resp = self.client.post(reverse('therapist_session_start'))
        self.assertEqual(resp.status_code, 302, 'session start failed')

    def test_both_exercises_stay_guided(self):
        from therapist_app.exercise_catalog import EXERCISES_BY_ID
        self.assertFalse(EXERCISES_BY_ID['ex_ankle_pumps']['v2_ghost_supported'])
        self.assertFalse(
            EXERCISES_BY_ID['ex_prone_glute_squeeze']['v2_ghost_supported'])

    def test_ankle_pumps_gets_interval_pacer(self):
        resp = self.client.get(reverse('therapist_session_exercise', args=[0]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Count-along pacer')
        self.assertContains(resp, 'Guided exercise — follow the video')
        self.assertContains(resp, 'One pump every 2 seconds.')

    def test_glute_squeeze_gets_squeeze_cycle_pacer(self):
        resp = self.client.get(reverse('therapist_session_exercise', args=[1]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Count-along pacer')
        self.assertContains(resp, 'Each rep: squeeze 5s, relax 3s.')

    def test_other_guided_exercises_have_no_pacer(self):
        # Item 2 is ex_sl_balance — dark, so it renders the guided page.
        resp = self.client.get(reverse('therapist_session_exercise', args=[2]))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'Count-along pacer')
