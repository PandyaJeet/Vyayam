from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from strength_app.models import (
    DailyFoodLog,
    FoodItem,
    FootballProfile,
    PatientFamilyCapability,
    PatientProfile,
    SessionFeedback,
    WorkoutSession,
)


def make_patient(patient_id="P1000", phone="9000000000", age=25):
    return PatientProfile.objects.create(
        patient_id=patient_id,
        name="Test Patient",
        phone=phone,
        age=age,
        goals="Build strength",
    )


class PatientProfileModelTests(TestCase):
    def test_age_validator_blocks_under_13(self):
        profile = PatientProfile(
            patient_id="P0001",
            name="Under Age",
            phone="9000000001",
            age=12,
            goals="Strength",
        )
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_fitness_level_property_returns_json(self):
        profile = make_patient()
        profile.fitness_level_json = {"lower_body": "manageable"}
        profile.save(update_fields=["fitness_level_json"])
        self.assertEqual(profile.fitness_level["lower_body"], "manageable")


class SessionFeedbackModelTests(TestCase):
    def test_save_sets_traffic_light(self):
        patient = make_patient(patient_id="P1001", phone="9000000002")
        session = WorkoutSession.objects.create(patient=patient)
        feedback = SessionFeedback.objects.create(
            session=session,
            patient=patient,
            perceived_difficulty="too_hard",
            pain_reported="moderate",
            sleep_last_night="7_to_8",
            energy_level="good",
        )
        self.assertEqual(feedback.traffic_light, "red")


class NutritionModelTests(TestCase):
    def test_daily_food_log_caches_macros(self):
        patient = make_patient(patient_id="P1002", phone="9000000003")
        item = FoodItem.objects.create(
            name="Rice",
            category="grain",
            calories_per_100g=200,
            protein_per_100g=4,
            carbs_per_100g=45,
            fat_per_100g=1,
            serving_size_g=100,
        )
        log = DailyFoodLog.objects.create(
            patient=patient,
            food_item=item,
            log_date=date.today(),
            quantity_g=150,
            meal_type="lunch",
        )
        self.assertEqual(log.calories_logged, 300.0)
        self.assertEqual(log.protein_logged, 6.0)
        self.assertEqual(log.carbs_logged, 67.5)
        self.assertEqual(log.fat_logged, 1.5)


class FootballProfileModelTests(TestCase):
    def test_compute_lsi_sets_flag(self):
        patient = make_patient(patient_id="P1003", phone="9000000004")
        profile = FootballProfile.objects.create(
            patient=patient,
            hop_left_cm=100,
            hop_right_cm=80,
            cod_left_seconds=5.0,
            cod_right_seconds=6.0,
            ybalance_left_pct=90.0,
            ybalance_right_pct=80.0,
        )
        flag = profile.compute_lsi()
        self.assertTrue(flag)
        self.assertEqual(profile.hop_lsi_pct, 80.0)
        self.assertEqual(profile.cod_lsi_pct, 83.3)
        self.assertEqual(profile.ybalance_lsi_pct, 88.9)


class PatientFamilyCapabilityTests(TestCase):
    def test_to_summary_dict_has_expected_keys(self):
        patient = make_patient(patient_id="P1004", phone="9000000005")
        capability = PatientFamilyCapability.objects.create(
            patient=patient,
            family_id="squat_family",
            family_name="Squat",
            current_level_index=1,
            current_exercise_id="normal_squat",
            current_exercise_name="Normal Squat",
            capability_numeric=3,
            capability_string="manageable",
            prescribed_sets=3,
            prescribed_reps=10,
            prescribed_hold_duration=0,
        )
        summary = capability.to_summary_dict()
        self.assertEqual(summary["family_id"], "squat_family")
        self.assertEqual(summary["current_exercise_id"], "normal_squat")
        self.assertEqual(summary["capability_numeric"], 3)
