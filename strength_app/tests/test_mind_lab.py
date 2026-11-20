"""Mind Lab scaffold: runner page, save endpoint, coach card."""

import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from strength_app.models import (
    CoachPatientLink, GameSession, PatientProfile, TherapistProfile,
)


def make_athlete(pid='MLATH1'):
    athlete = PatientProfile.objects.create(
        patient_id=pid, name='ML Athlete', phone='9000008001', age=22,
        goals='Football', training_history='intermediate',
        athlete_tier_eligible=True, athlete_tier_active=True,
        athlete_sport='football',
    )
    user = User.objects.create_user('mlcoach' + pid, password='pw123456')
    coach = TherapistProfile.objects.create(
        user=user, therapist_id='MLC' + pid, name='ML Coach',
        license_number='PT-ML-' + pid, specialization='S&C',
        email=pid + '@example.com', phone='9999900' + pid[-3:].zfill(3),
    )
    CoachPatientLink.objects.create(coach=coach, patient=athlete, is_active=True)
    return athlete, user


class TestMindLabRunner(TestCase):
    def setUp(self):
        self.athlete, self.coach_user = make_athlete()
        s = self.client.session
        s['patient_id'] = self.athlete.patient_id
        s.save()

    def post(self, payload, game='any_game'):
        return self.client.post(
            reverse('mind_lab_save', args=[game]),
            data=json.dumps(payload), content_type='application/json')

    def test_runner_renders_for_any_game_id(self):
        resp = self.client.get(reverse('mind_lab_runner', args=['whatever_9']))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'strength_app/mind_lab_runner.html')

    def test_runner_redirects_when_not_signed_in(self):
        s = self.client.session
        s.flush()
        resp = self.client.get(reverse('mind_lab_runner', args=['g']))
        self.assertEqual(resp.status_code, 302)

    def test_bad_game_id_404(self):
        resp = self.client.get(reverse('mind_lab_runner', args=['Bad.Id']))
        self.assertEqual(resp.status_code, 404)

    def test_save_creates_session(self):
        resp = self.post({'level': 3, 'n_trials': 20, 'accuracy': 0.85,
                          'median_rt_ms': 412.5, 'slowmo_factor': 0.5,
                          'summary': {'k': 'v'}})
        self.assertEqual(resp.status_code, 200)
        gs = GameSession.objects.get()
        self.assertEqual((gs.athlete_id, gs.game_id, gs.level, gs.n_trials),
                         (self.athlete.patient_id, 'any_game', 3, 20))
        self.assertEqual(gs.summary, {'k': 'v'})

    def test_save_rejects_bad_values(self):
        for bad in ({'accuracy': 1.5}, {'accuracy': 'x'}, {'level': 0},
                    {'n_trials': -1}, {'median_rt_ms': -5},
                    {'level': True}, {'summary': [1]},
                    {'summary': {'a': 'x' * 9000}}):
            self.assertEqual(self.post(bad).status_code, 400, bad)
        self.assertEqual(GameSession.objects.count(), 0)

    def test_save_rejects_non_json_and_signed_out(self):
        resp = self.client.post(reverse('mind_lab_save', args=['g']),
                                data='nope', content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        s = self.client.session
        s.flush()
        self.assertEqual(self.post({}).status_code, 403)

    def test_save_is_post_only(self):
        resp = self.client.get(reverse('mind_lab_save', args=['g']))
        self.assertEqual(resp.status_code, 405)


class TestMindLabCoachCard(TestCase):
    def setUp(self):
        self.athlete, self.coach_user = make_athlete('MLATH2')
        self.client.force_login(self.coach_user)
        self.url = reverse('coach_athlete_detail', args=[self.athlete.patient_id])

    def test_empty_state(self):
        self.assertContains(self.client.get(self.url), 'No Mind Lab sessions yet.')

    def test_latest_session_shown(self):
        GameSession.objects.create(athlete=self.athlete, game_id='old', level=1)
        GameSession.objects.create(
            athlete=self.athlete, game_id='newest_game', level=4, n_trials=30,
            accuracy=0.8, median_rt_ms=377.0)
        resp = self.client.get(self.url)
        self.assertContains(resp, 'newest_game')
        self.assertContains(resp, '80%')
        self.assertContains(resp, '377 ms')
