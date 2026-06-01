from django.test import SimpleTestCase, TestCase

from strength_app.backend.database_schema import ExerciseCategory as BackendExerciseCategory
from strength_app.backend.database_schema import CapabilityLevel as BackendCapabilityLevel
from strength_app.backend.main_coordinator import VyayamStrengthSystem
from strength_app.models import (
    AnonymisedSessionLog,
    PatientFamilyCapability,
    PatientProfile,
    WorkoutSession,
)
from strength_app.utils import (
    django_to_backend_category,
    execute_workout_session,
    generate_prescription,
    sanitize_json_field,
)
from strength_app.v1_data_collector import log_session_data
from strength_app.v1_progression_chains import V1_PROGRESSION_CHAINS


class UtilsMappingTests(SimpleTestCase):
    def test_django_to_backend_category_mapping(self):
        self.assertEqual(
            django_to_backend_category("lower_body"),
            BackendExerciseCategory.LOWER_BODY,
        )
        self.assertEqual(
            django_to_backend_category("stretching"),
            BackendExerciseCategory.STRETCHING,
        )
        self.assertEqual(
            django_to_backend_category("cardio"),
            BackendExerciseCategory.CARDIO,
        )

    def test_sanitize_json_field_converts_enum(self):
        payload = {
            "cap": BackendCapabilityLevel.EASY,
            "items": [BackendCapabilityLevel.MANAGEABLE],
        }
        sanitized = sanitize_json_field(payload)
        self.assertEqual(sanitized["cap"], "easy")
        self.assertEqual(sanitized["items"][0], "manageable")


class ProgressionChainTests(SimpleTestCase):
    def test_v1_progression_chains_have_levels(self):
        self.assertIn("squat", V1_PROGRESSION_CHAINS)
        for family in V1_PROGRESSION_CHAINS.values():
            self.assertTrue(family.get("levels"))
            for level in family["levels"]:
                self.assertTrue(level.get("exercises"))


class MainCoordinatorTests(SimpleTestCase):
    def test_infer_clusteral_dimensions(self):
        system = VyayamStrengthSystem()
        patient_id = system.create_patient(
            name="Test User",
            phone="9000000090",
            password="pass",
            age=30,
            goals="rehab for knee pain",
            occupation="Software Engineer",
            lifestyle="sedentary",
        )
        profile = system.patients[patient_id].patient_profile
        self.assertEqual(profile.biomechanics, "desk_job_posture")
        self.assertEqual(profile.activity_pattern, "desk_job")
        self.assertEqual(profile.goal_type, "rehabilitation")
        self.assertEqual(profile.timeline, "no_rush")


class PrescriptionAndSessionTests(TestCase):
    def setUp(self):
        self.patient = PatientProfile.objects.create(
            patient_id="P2001",
            name="Group3 Patient",
            phone="9000000100",
            age=28,
            goals="Build strength",
            lifestyle="moderately_active",
            goal_type="functional",
        )

    def test_generate_prescription_uses_family_capability(self):
        PatientFamilyCapability.objects.create(
            patient=self.patient,
            family_id="squat_family",
            family_name="Squat",
            current_level_index=1,
            current_exercise_id="partial_squats",
            current_exercise_name="Partial Squats",
            capability_numeric=3,
            capability_string="manageable",
            prescribed_sets=2,
            prescribed_reps=10,
            prescribed_hold_duration=0,
        )
        prescription = generate_prescription(self.patient)
        strength = [
            ex for ex in prescription["strength"]
            if ex.get("family_id") == "squat_family"
        ]
        self.assertTrue(strength)
        self.assertEqual(strength[0]["exercise_id"], "partial_squats")

    def test_execute_workout_session_rejects_meta(self):
        prescription = generate_prescription(self.patient)
        with self.assertRaises(AttributeError):
            execute_workout_session(self.patient, prescription)

    def test_execute_workout_session_without_meta(self):
        prescription = {
            "stretching": [
                {
                    "exercise_id": "hamstring_stretch",
                    "exercise_name": "Hamstring Stretch",
                    "sets": 1,
                    "reps": 1,
                    "hold_duration": 20,
                    "rest": 15,
                    "category": "stretching",
                }
            ],
            "strength": [
                {
                    "exercise_id": "partial_squats",
                    "exercise_name": "Partial Squats",
                    "sets": 1,
                    "reps": 1,
                    "hold_duration": 0,
                    "rest": 30,
                    "category": "lower_body",
                }
            ],
            "cardio": [
                {
                    "exercise_id": "walking",
                    "exercise_name": "Walking",
                    "sets": 1,
                    "reps": 1,
                    "hold_duration": 60,
                    "rest": 0,
                    "category": "cardio",
                }
            ],
        }
        session = execute_workout_session(self.patient, prescription)
        self.assertIsInstance(session, WorkoutSession)
        self.assertEqual(session.exercises.count(), 3)


class DataCollectorTests(TestCase):
    def setUp(self):
        self.patient = PatientProfile.objects.create(
            patient_id="P2002",
            name="Consent Patient",
            phone="9000000101",
            age=26,
            goals="Build strength",
            data_consent=True,
        )

    def test_log_session_data_records_entry_when_consented(self):
        session_data = {
            "meta": {"periodisation_phase": "strength"},
            "working_sets": [
                {
                    "movement_pattern": "squat",
                    "sets": 2,
                    "reps": 10,
                    "tempo": "3-1-2-0",
                    "rest_seconds": 60,
                }
            ],
        }
        log_session_data(self.patient, session_data, feedback=None)
        self.assertEqual(AnonymisedSessionLog.objects.count(), 1)

    def test_log_session_data_skips_without_consent(self):
        patient = PatientProfile.objects.create(
            patient_id="P2003",
            name="No Consent",
            phone="9000000102",
            age=26,
            goals="Build strength",
            data_consent=False,
        )
        log_session_data(patient, {"meta": {}, "working_sets": []}, feedback=None)
        self.assertEqual(AnonymisedSessionLog.objects.count(), 0)
