"""
Permission tests for the therapist console.

The fixtures here mirror what `seed_therapist_demo` produces, scoped to the
4 cases in the spec:

  1. Logged-out user → /therapist/dashboard/ redirects to login
  2. Authenticated patient (anika) → /therapist/dashboard/ returns 403
  3. dr_shah cannot see vikram's detail page (404 — vikram belongs to dr_iyer)
  4. dr_iyer cannot POST to anika's program save endpoint (404)
"""

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Therapist, TherapistPatientLink


class TherapistPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Therapists
        shah_user = User.objects.create_user(username='dr_shah', password='simple')
        cls.dr_shah = Therapist.objects.create(
            user=shah_user, full_name='Dr. Meera Shah',
            specialization='Sports Physio', clinic_name='Andheri',
        )
        iyer_user = User.objects.create_user(username='dr_iyer', password='simple')
        cls.dr_iyer = Therapist.objects.create(
            user=iyer_user, full_name='Dr. Karan Iyer',
            specialization='Sports Med', clinic_name='KMC',
        )

        # Patients (Django Users)
        cls.anika = User.objects.create_user(username='anika', password='patient')
        cls.vikram = User.objects.create_user(username='vikram', password='patient')

        cls.shah_anika_link = TherapistPatientLink.objects.create(
            therapist=cls.dr_shah, patient=cls.anika,
            full_name='Anika Patel', email='anika@example.com',
            primary_condition='Right meniscus tear', condition_tone='warn',
            status='active', accepted_at=timezone.now(),
        )
        cls.iyer_vikram_link = TherapistPatientLink.objects.create(
            therapist=cls.dr_iyer, patient=cls.vikram,
            full_name='Vikram Shetty', email='vikram@example.com',
            primary_condition='Hamstring strain', condition_tone='warn',
            status='active', accepted_at=timezone.now(),
        )

    def test_logged_out_redirects_to_login(self):
        """Case 1: anonymous → redirect to login."""
        client = Client()
        response = client.get('/therapist/dashboard/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/therapist/login/', response.url)

    def test_authenticated_patient_gets_403(self):
        """Case 2: anika (a patient, not a therapist) → 403 on dashboard."""
        client = Client()
        self.assertTrue(client.login(username='anika', password='patient'))
        response = client.get('/therapist/dashboard/')
        self.assertEqual(response.status_code, 403)

    def test_cross_therapist_detail_returns_404(self):
        """Case 3: dr_shah cannot view vikram's detail (vikram is dr_iyer's)."""
        client = Client()
        self.assertTrue(client.login(username='dr_shah', password='simple'))
        url = reverse('therapist_patient_detail', args=[self.iyer_vikram_link.id])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_cross_therapist_program_save_returns_404(self):
        """Case 4: dr_iyer cannot POST to anika's program save (anika is dr_shah's)."""
        client = Client()
        self.assertTrue(client.login(username='dr_iyer', password='simple'))
        url = reverse('therapist_save_program', args=[self.shah_anika_link.id])
        response = client.post(
            url,
            data=json.dumps({'week_number': 1, 'items': [], 'publish': False}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)
