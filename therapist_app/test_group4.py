import json

from django.contrib.auth.models import AnonymousUser, User
from django.http import Http404, HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

from therapist_app.models import (
    Prescription,
    PrescriptionItem,
    Therapist,
    TherapistMessage,
    TherapistPatientLink,
)
from therapist_app.permissions import get_linked_patient_or_404, therapist_required


class TherapistPermissionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_therapist_required_redirects_anonymous(self):
        @therapist_required
        def view(_request):
            return HttpResponse("ok")

        request = self.factory.get("/therapist/dashboard/")
        request.user = AnonymousUser()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/therapist/login/", response.url)

    def test_therapist_required_forbids_non_therapist(self):
        @therapist_required
        def view(_request):
            return HttpResponse("ok")

        user = User.objects.create_user(username="patient_user", password="pass")
        request = self.factory.get("/therapist/dashboard/")
        request.user = user
        response = view(request)
        self.assertEqual(response.status_code, 403)

    def test_get_linked_patient_or_404_blocks_other_therapist(self):
        therapist_user_1 = User.objects.create_user(username="dr_1", password="pass")
        therapist_user_2 = User.objects.create_user(username="dr_2", password="pass")
        therapist_1 = Therapist.objects.create(user=therapist_user_1, full_name="Dr. One")
        therapist_2 = Therapist.objects.create(user=therapist_user_2, full_name="Dr. Two")
        patient_user = User.objects.create_user(username="patient", password="pass")
        link = TherapistPatientLink.objects.create(
            therapist=therapist_1,
            patient=patient_user,
            status="active",
        )
        with self.assertRaises(Http404):
            get_linked_patient_or_404(therapist_2, link.id)


class TherapistProgramBuilderTests(TestCase):
    def setUp(self):
        self.therapist_user = User.objects.create_user(username="dr_prog", password="pass")
        self.therapist = Therapist.objects.create(user=self.therapist_user, full_name="Dr. Program")
        self.patient_user = User.objects.create_user(username="patient_prog", password="pass")
        self.link = TherapistPatientLink.objects.create(
            therapist=self.therapist,
            patient=self.patient_user,
            status="active",
        )
        self.client.force_login(self.therapist_user)

    def test_save_program_publishes_items(self):
        payload = {
            "week_number": 1,
            "publish": True,
            "items": [
                {
                    "exercise_id": "ex_bw_squat",
                    "exercise_name": "Bodyweight Squat",
                    "sets": 3,
                    "reps": 10,
                    "rest_seconds": 60,
                    "tempo": "3-1-2-0",
                }
            ],
        }
        response = self.client.post(
            reverse("therapist_save_program", args=[self.link.id]),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("ok"))
        rx = Prescription.objects.get(link=self.link, week_number=1)
        self.assertIsNotNone(rx.published_at)
        self.assertEqual(PrescriptionItem.objects.filter(prescription=rx).count(), 1)

    def test_save_program_draft_only(self):
        payload = {
            "week_number": 2,
            "publish": False,
            "items": [
                {"exercise_id": "ex_bw_squat", "sets": 2, "reps": 8}
            ],
        }
        response = self.client.post(
            reverse("therapist_save_program", args=[self.link.id]),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        rx = Prescription.objects.get(link=self.link, week_number=2)
        self.assertIsNone(rx.published_at)
        self.assertEqual(rx.items.count(), 0)


class TherapistMessagingTests(TestCase):
    def setUp(self):
        self.therapist_user = User.objects.create_user(username="dr_msg", password="pass")
        self.therapist = Therapist.objects.create(user=self.therapist_user, full_name="Dr. Message")
        self.patient_user = User.objects.create_user(username="patient_msg", password="pass")
        self.link = TherapistPatientLink.objects.create(
            therapist=self.therapist,
            patient=self.patient_user,
            status="active",
        )
        self.client.force_login(self.therapist_user)

    def test_send_message_creates_record(self):
        response = self.client.post(
            reverse("therapist_send_message", args=[self.link.id]),
            data={"body": "Hello from therapist"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TherapistMessage.objects.count(), 1)
