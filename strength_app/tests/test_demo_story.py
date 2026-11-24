"""K3 — seed_football_demo tells a 4-week story that the app's own logic confirms."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from strength_app.models import (
    ExerciseExecution, FootballProfile, PatientFamilyCapability, PatientProfile,
)


class DemoStoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_football_demo', stdout=StringIO())
        cls.patient = PatientProfile.objects.get(patient_id='FBDEMO_KABIR')

    def test_lsi_flag_from_model_logic(self):
        fp = FootballProfile.objects.get(patient=self.patient)
        self.assertTrue(fp.lsi_flag)
        self.assertLess(fp.hop_lsi_pct, 90)
        self.assertGreaterEqual(fp.hop_lsi_pct, 80)  # low-load plyo gate still passes

    def test_lunge_asymmetry_is_moderate_with_extra_set(self):
        sp = self.patient.strength_profiles.first()
        self.assertEqual(sp.lunge_asymmetry, 'moderate')
        self.assertEqual(sp.raw_test_data_json['lunge_test']['lsi_pct'], 63.6)

    def test_one_progression_one_deload(self):
        from strength_app.v1_safety_logic import check_deload_needed
        pfc = PatientFamilyCapability.objects.get(patient=self.patient)
        self.assertEqual(pfc.capability_numeric, 4)
        self.assertEqual(len(pfc.progression_history_json), 1)
        self.assertTrue(check_deload_needed(self.patient)[0])

    def test_guided_sessions_have_no_rep_level_data(self):
        for ex in ExerciseExecution.objects.filter(session__patient=self.patient):
            self.assertEqual(ex.rep_quality_source, 'manual')
            self.assertIsNone(ex.overall_form_score)

    def test_demo_labelled_and_idempotent(self):
        self.assertIn('DEMO', self.patient.name)
        call_command('seed_football_demo', stdout=StringIO())
        self.assertEqual(PatientFamilyCapability.objects.filter(patient=self.patient).count(), 1)
        self.client.post('/login/', {'phone': '9000000005', 'password': 'athlete'})
        html = self.client.get('/athlete/today/').content.decode()
        self.assertIn('DEMO DATA', html)
