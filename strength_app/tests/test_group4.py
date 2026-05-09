import json

from datetime import date

from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from strength_app.middleware import PermissionsPolicyMiddleware
from strength_app.models import (
    CoachPatientLink,
    DailyFoodLog,
    FoodItem,
    GateTestResult,
    PatientFamilyCapability,
    PatientProfile,
    TherapistPrescription,
    TherapistProfile,
)
from strength_app.rate_limiter import rate_limit
from strength_app.v1_coach_views import coach_required
from strength_app.views import _build_family_session_list


class MiddlewareTests(SimpleTestCase):
    def test_permissions_policy_header(self):
        factory = RequestFactory()
        request = factory.get("/")

        def get_response(_request):
            return HttpResponse("ok")

        middleware = PermissionsPolicyMiddleware(get_response)
        response = middleware(request)
        self.assertEqual(
            response["Permissions-Policy"],
            "camera=(self), microphone=(self)",
        )


class RateLimiterTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def test_rate_limit_blocks_after_max_attempts(self):
        @rate_limit(max_attempts=2, window_seconds=60, key_prefix="test")
        def view(request):
            return HttpResponse("ok")

        request = self.factory.post("/", HTTP_ACCEPT="application/json")
        request.META["REMOTE_ADDR"] = "1.2.3.4"
        self.assertEqual(view(request).status_code, 200)
        self.assertEqual(view(request).status_code, 200)
        response = view(request)
        self.assertEqual(response.status_code, 429)

    def test_rate_limit_skips_get(self):
        @rate_limit(max_attempts=1, window_seconds=60, key_prefix="test_get")
        def view(request):
            return HttpResponse("ok")

        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = "5.6.7.8"
        self.assertEqual(view(request).status_code, 200)


class GateTestEndpointTests(TestCase):
    def setUp(self):
        self.patient = PatientProfile.objects.create(
            patient_id="P4001",
            name="Gate Test Patient",
            phone="9000000200",
            age=25,
            goals="Strength",
        )

    def test_save_gate_test_result_creates_records(self):
        session = self.client.session
        session["patient_id"] = self.patient.patient_id
        session["gate_families"] = _build_family_session_list()
        session.save()

        payload = {
            "family_index": 0,
            "level_index": 0,
            "action": "this_is_my_level",
            "reps_completed": 10,
            "difficulty_reported": 3,
            "pain_during": 0,
        }
        response = self.client.post(
            reverse("save_gate_test_result"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body.get("success"))
        self.assertEqual(GateTestResult.objects.count(), 1)
        self.assertEqual(PatientFamilyCapability.objects.count(), 1)


class CVEndpointTests(SimpleTestCase):
    def test_analyze_frame_requires_post(self):
        response = self.client.get(reverse("analyze_frame"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("error"), "POST required")


class NutritionApiTests(TestCase):
    def setUp(self):
        self.patient = PatientProfile.objects.create(
            patient_id="P4002",
            name="Nutrition Patient",
            phone="9000000201",
            age=24,
            goals="Strength",
        )
        self.food = FoodItem.objects.create(
            name="Rice",
            category="grain",
            calories_per_100g=200,
            protein_per_100g=4,
            carbs_per_100g=45,
            fat_per_100g=1,
            serving_size_g=100,
        )

    def _login_session(self):
        session = self.client.session
        session["patient_id"] = self.patient.patient_id
        session.save()

    def test_food_search_requires_auth(self):
        response = self.client.get(reverse("v1_food_search_api"), {"q": "ri"})
        self.assertEqual(response.status_code, 401)

    def test_food_search_returns_results(self):
        self._login_session()
        response = self.client.get(reverse("v1_food_search_api"), {"q": "ri"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json().get("results", [])), 1)

    def test_quick_log_requires_auth(self):
        response = self.client.post(
            reverse("v1_quick_log_api"),
            data=json.dumps({"food_id": self.food.id, "quantity_g": 100}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_quick_log_creates_entry(self):
        self._login_session()
        response = self.client.post(
            reverse("v1_quick_log_api"),
            data=json.dumps({"food_id": self.food.id, "quantity_g": 150}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"))
        self.assertEqual(DailyFoodLog.objects.count(), 1)


class CoachViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.coach_user = User.objects.create_user(username="coach_user", password="pass")
        self.coach_profile = TherapistProfile.objects.create(
            user=self.coach_user,
            therapist_id="T2001",
            name="Coach User",
            license_number="LIC-1",
            specialization="Sports",
            email="coach@example.com",
            phone="9000000300",
        )
        self.patient = PatientProfile.objects.create(
            patient_id="P4003",
            name="Coach Patient",
            phone="9000000301",
            age=25,
            goals="Strength",
        )
        self.link = CoachPatientLink.objects.create(
            coach=self.coach_profile,
            patient=self.patient,
            is_active=True,
        )

    def test_coach_required_redirects_anonymous(self):
        @coach_required
        def view(_request):
            return HttpResponse("ok")

        request = self.factory.get("/coach/squad/")
        request.user = AnonymousUser()
        response = view(request)
        self.assertEqual(response.status_code, 302)

    def test_coach_required_redirects_non_coach(self):
        @coach_required
        def view(_request):
            return HttpResponse("ok")

        user = User.objects.create_user(username="noncoach", password="pass")
        request = self.factory.get("/coach/squad/")
        request.user = user
        response = view(request)
        self.assertEqual(response.status_code, 302)

    def test_coach_add_athlete_creates_link(self):
        self.client.force_login(self.coach_user)
        response = self.client.post(
            reverse("coach_add_athlete"),
            data={"phone": self.patient.phone},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            CoachPatientLink.objects.filter(
                coach=self.coach_profile, patient=self.patient
            ).exists()
        )

    def test_coach_flag_review_appends_note(self):
        self.client.force_login(self.coach_user)
        response = self.client.post(
            reverse("coach_flag_review", args=[self.patient.patient_id]),
            data={"note": "Needs follow-up"},
        )
        self.assertEqual(response.status_code, 200)
        self.link.refresh_from_db()
        self.assertIn("Needs follow-up", self.link.notes)

    def test_coach_override_prescription_creates_rx(self):
        self.client.force_login(self.coach_user)
        exercises = json.dumps(
            [
                {
                    "exercise_id": "partial_squats",
                    "exercise_name": "Partial Squats",
                    "sets": 3,
                    "reps": 10,
                }
            ]
        )
        response = self.client.post(
            reverse("coach_override_prescription", args=[self.patient.patient_id]),
            data={"exercises_json": exercises},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            TherapistPrescription.objects.filter(
                patient=self.patient, therapist=self.coach_profile
            ).count(),
            1,
        )

    def test_coach_set_competition_sets_date(self):
        self.client.force_login(self.coach_user)
        response = self.client.post(
            reverse("coach_set_competition", args=[self.patient.patient_id]),
            data={"competition_date": "2026-06-01"},
        )
        self.assertEqual(response.status_code, 302)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.competition_date, date(2026, 6, 1))
