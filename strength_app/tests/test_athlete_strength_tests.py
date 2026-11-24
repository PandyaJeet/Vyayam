"""
2026-07 Part 3 — bench press / leg press manual-entry strength tests.

Pins:
  - the battery now lists 8 tests, strength tests last (indices 6, 7)
  - football_save_test_result computes Epley e1RM server-side
  - football_assessment_results persists to raw_test_data_json['strength_tests']
    with optional rel_bw, and does NOT alter football_level (SB-5a: display only)
  - both display surfaces render (athlete Progress, coach athlete detail)
  - seed_football_demo gives Kabir both entries
"""

import json
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from strength_app.models import PatientProfile, StrengthProfile
from strength_app.v1_football_constants import FOOTBALL_ASSESSMENT_TESTS


class TestBatteryShape(TestCase):
    def test_eight_tests_strength_last(self):
        self.assertEqual(len(FOOTBALL_ASSESSMENT_TESTS), 8)
        self.assertEqual(FOOTBALL_ASSESSMENT_TESTS[6]['test_id'], 'bench_press_test')
        self.assertEqual(FOOTBALL_ASSESSMENT_TESTS[7]['test_id'], 'leg_press_test')
        for i in (6, 7):
            self.assertEqual(
                FOOTBALL_ASSESSMENT_TESTS[i]['entry_mode'], 'strength_manual')


class TestStrengthManualEntry(TestCase):
    def setUp(self):
        cache.clear()
        self.patient = PatientProfile.objects.create(
            patient_id='STRTEST1',
            name='Strength Tester',
            phone='9000009975',
            age=24,
            weight_kg=70.0,
            goals='Football',
            training_history='intermediate',
            athlete_tier_eligible=True,
            athlete_sport='football',
        )
        StrengthProfile.objects.create(
            patient=self.patient, assessment_number=1,
            squat_score=3, hinge_score=3, push_score=3,
            pull_score=3, core_score=3, rotate_score=3, lunge_score=3,
        )
        session = self.client.session
        session['patient_id'] = self.patient.patient_id
        session.save()

    def _save(self, test_index, weight, reps):
        return self.client.post(
            reverse('football_save_test_result'),
            data=json.dumps(
                {'test_index': test_index, 'weight_kg': weight, 'reps': reps}),
            content_type='application/json',
        )

    def test_save_computes_epley_e1rm_server_side(self):
        resp = self._save(6, 60, 8)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['e1rm'], 76.0)   # 60 × (1 + 8/30)
        stored = self.client.session['football_test_results']['bench_press_test']
        self.assertEqual(stored, {'weight_kg': 60.0, 'reps': 8, 'e1rm': 76.0})

    def test_save_rejects_missing_values(self):
        resp = self._save(6, 0, 8)
        self.assertEqual(resp.status_code, 400)

    def test_results_persists_and_level_untouched(self):
        # Full battery: six scored tests all landing on 3, plus both
        # strength entries — mirrors the only state the real flow can
        # reach results in.
        session = self.client.session
        session['football_test_results'] = {
            'hop_test': {'score': 3},
            'nordic_test': {'raw': 5},       # 4-6 s → 3
            'sprint_test': {'raw': 3.5},     # 3.41-3.70 s → 3
            'pogo_test': {'raw': 17},        # 15-19 → 3
            'cod_test': {'score': 3},
            'ybalance_test': {'score': 3},
        }
        session.save()
        self._save(6, 60, 8)
        self._save(7, 140, 10)
        resp = self.client.get(reverse('football_assessment_results'))
        self.assertEqual(resp.status_code, 200)
        self.patient.refresh_from_db()
        st = self.patient.raw_test_data_json['strength_tests']
        self.assertEqual(st['bench_press']['e1rm'], 76.0)
        self.assertEqual(st['bench_press']['rel_bw'], 1.09)   # 76.0 / 70
        self.assertEqual(st['leg_press']['e1rm'], 186.7)      # 140 × (1 + 10/30)
        self.assertEqual(st['leg_press']['rel_bw'], 2.67)
        # SB-5a guard: strength entries never feed the level — six 3s must
        # average to exactly level 3 regardless of the big leg-press e1RM.
        self.assertEqual(self.patient.football_profile.football_level, 3)

    def test_strength_page_renders_weight_reps_inputs(self):
        resp = self.client.get(reverse('football_assessment_execute', args=[6]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'weightKg')
        self.assertContains(resp, 'repsDone')
        self.assertContains(resp, 'skip this test')


class TestStrengthDisplaySurfaces(TestCase):
    def setUp(self):
        cache.clear()
        call_command('seed_football_demo', stdout=StringIO())

    def test_kabir_seeded_with_strength_tests(self):
        kabir = PatientProfile.objects.get(patient_id='FBDEMO_KABIR')
        st = kabir.raw_test_data_json['strength_tests']
        self.assertEqual(st['bench_press']['e1rm'], 76.0)
        self.assertEqual(st['leg_press']['e1rm'], 186.7)

    def test_athlete_progress_shows_strength_card(self):
        self.client.post(reverse('patient_login'),
                         {'phone': '9000000005', 'password': 'athlete'})
        resp = self.client.get(reverse('athlete_progress'))
        self.assertContains(resp, 'Bench Press')
        self.assertContains(resp, 'Leg Press')
        self.assertContains(resp, '76')
        self.assertContains(resp, 'Estimated 1RM (Epley)')

    def test_coach_detail_shows_strength_table(self):
        self.client.post(reverse('coach_login'),
                         {'username': 'coach_arjun', 'password': 'simple'})
        resp = self.client.get(
            reverse('coach_athlete_detail', args=['FBDEMO_KABIR']))
        self.assertContains(resp, 'Strength Tests — Manual Entry')
        self.assertContains(resp, 'Bench Press')
        self.assertContains(resp, '186.7')
