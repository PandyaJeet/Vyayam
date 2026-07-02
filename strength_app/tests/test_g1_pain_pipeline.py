"""
G1 — pain pipeline: severity beats type everywhere, and the alert is proven
end-to-end.

Pawan's confirmed spec: <= threshold → PainEvent only (silent report) ·
above-threshold to 7 → skip + system TherapistMessage · 8-10 → pause +
message + Alert, ALWAYS, regardless of pain type. Severe "burning/aching"
can be neuropathic, so type-based leniency caps out below 8 — these tests
encode that so a missing-alert regression can never return silently.
"""

import json
from io import StringIO

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from strength_app.models import PainEvent, PatientProfile
from therapist_app.models import Alert, TherapistMessage


class ManagedPainTierBase(TestCase):
    """Seeded managed patient (Anika, threshold 5 default) mid-session."""

    def setUp(self):
        # The login rate limiter counts POSTs per IP in the process-wide
        # test cache — clear it so suite-order can't 429 our login.
        cache.clear()
        call_command('seed_therapist_demo', stdout=StringIO())
        self.patient = PatientProfile.objects.get(phone='9000000001')

        resp = self.client.post(
            reverse('patient_login'),
            {'phone': '9000000001', 'password': 'patient'},
        )
        self.assertEqual(resp.status_code, 302, 'patient login failed')
        resp = self.client.post(reverse('therapist_session_start'))
        self.assertEqual(resp.status_code, 302, 'session start failed')

    def report(self, severity, pain_type='aching', idx=0):
        return self.client.post(
            reverse('therapist_session_report_pain', args=[idx]),
            data=json.dumps({
                'severity': severity,
                'pain_type': pain_type,
                'set_number': 1,
            }),
            content_type='application/json',
        )


class TestG1cManagedPainTiers(ManagedPainTierBase):

    def test_severity_4_is_silent_report_only(self):
        # Threshold is 5 (settings default; seed sets none per item) —
        # severity 4 is at-or-below the patient's usual pain.
        resp = self.report(severity=4)
        out = resp.json()
        self.assertEqual(out['action'], 'continue')
        self.assertTrue(out.get('guidance'), 'G1b: continue tier must carry '
                        'a server-written guidance string')

        events = PainEvent.objects.filter(patient=self.patient)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.get().outcome, 'continued')
        self.assertEqual(TherapistMessage.objects.count(), 0)
        self.assertEqual(Alert.objects.count(), 0)

    def test_severity_6_skips_and_messages_no_alert(self):
        resp = self.report(severity=6)
        out = resp.json()
        self.assertEqual(out['action'], 'skip')
        self.assertIn('next_url', out)
        self.assertTrue(out.get('guidance'))

        self.assertEqual(
            PainEvent.objects.get(patient=self.patient).outcome,
            'exercise_skipped')
        msgs = TherapistMessage.objects.all()
        self.assertEqual(msgs.count(), 1)
        self.assertTrue(msgs.get().is_system)
        self.assertEqual(Alert.objects.count(), 0,
                         'skip tier must NOT raise an Alert')

    def test_severity_8_aching_pauses_messages_and_alerts_in_inbox(self):
        # The spec's crux: 8-10 alerts ALWAYS, even for "aching/burning" —
        # type-based leniency must cap out below 8.
        resp = self.report(severity=8, pain_type='aching')
        out = resp.json()
        self.assertEqual(out['action'], 'pause')
        self.assertIn(reverse('v1_pain_stop'), out['next_url'])
        self.assertTrue(out.get('guidance'))

        self.assertEqual(
            PainEvent.objects.get(patient=self.patient).outcome,
            'session_paused')

        msg = TherapistMessage.objects.get()
        self.assertTrue(msg.is_system)
        self.assertIn('8/10', msg.body)

        alert = Alert.objects.get()
        self.assertEqual(alert.alert_type, 'pain')
        self.assertIn('aching', alert.message)

        # Prove it end-to-end: the alert APPEARS in dr_shah's inbox view,
        # and its body text (message and alert share one string) is on page.
        therapist_client = self.client_class()
        therapist_client.force_login(User.objects.get(username='dr_shah'))
        inbox = therapist_client.get(reverse('therapist_alerts'))
        self.assertEqual(inbox.status_code, 200)
        content = inbox.content.decode('utf-8')
        self.assertIn('HIGH PAIN', content)
        self.assertIn('aching pain 8/10', content)
        self.assertIn('Anika Patel', content)


class TestF1PainRateLimitAndAlertDedupe(ManagedPainTierBase):
    """Deploy review F1: the pain endpoint is rate-limited (15/min) and a
    burst of severity-8 reports on the same exercise raises ONE alert —
    PainEvents and system messages are always recorded."""

    def test_sixteenth_post_in_a_minute_is_429(self):
        for i in range(15):
            resp = self.report(severity=1)
            self.assertNotEqual(resp.status_code, 429, f'throttled at #{i + 1}')
        resp = self.report(severity=1)
        self.assertEqual(resp.status_code, 429)
        # Only the 15 allowed requests wrote events.
        self.assertEqual(PainEvent.objects.count(), 15)

    def test_repeat_severity_8_same_exercise_dedupes_alert_only(self):
        self.report(severity=8, idx=0)
        self.report(severity=8, idx=0)
        self.assertEqual(PainEvent.objects.count(), 2)
        self.assertEqual(TherapistMessage.objects.count(), 2)
        self.assertEqual(Alert.objects.count(), 1,
                         'duplicate unreviewed pain alert must be suppressed')
        # Once the therapist reviews it, a new report alerts again.
        alert = Alert.objects.get()
        alert.is_reviewed = True
        alert.save(update_fields=['is_reviewed'])
        self.report(severity=8, idx=0)
        self.assertEqual(Alert.objects.count(), 2)

    def test_severity_8_on_different_exercise_alerts_again(self):
        self.report(severity=8, idx=0)   # Glute Bridge
        self.report(severity=8, idx=3)   # Step-up — different exercise
        self.assertEqual(PainEvent.objects.count(), 2)
        self.assertEqual(Alert.objects.count(), 2)


class TestG1aAthleteSeverityStopsServerSide(TestCase):
    """Self-serve parity: 8+ stops the session server-side regardless of
    pain type AND regardless of the action string the client sends —
    the old computeGuidance never sent 'stop' for aching, so a burning 10
    could not stop the session."""

    def setUp(self):
        self.patient = PatientProfile.objects.create(
            patient_id='G1ATH1', name='G1 Athlete', phone='9000009981',
            age=30, goals='Strength', training_history='intermediate',
        )
        session = self.client.session
        session['patient_id'] = self.patient.patient_id
        session['v1_session'] = {'working_sets': [
            {'exercise_id': 'full_squats', 'exercise_name': 'Full Squats',
             'movement_pattern': 'squat', 'sets': 3, 'reps': 10},
            {'exercise_id': 'push_ups', 'exercise_name': 'Push Ups',
             'movement_pattern': 'push', 'sets': 3, 'reps': 10},
        ]}
        session.save()

    def _post_result(self, **overrides):
        payload = {
            'exercise_index': 0, 'exercise_id': 'full_squats',
            'exercise_name': 'Full Squats', 'movement_pattern': 'squat',
            'prescribed_sets': 3, 'prescribed_reps': 10,
            'completed_sets': 1, 'reps_per_set': [10], 'form_score': 80,
        }
        payload.update(overrides)
        return self.client.post(
            reverse('v1_save_exercise_result'),
            data=json.dumps(payload), content_type='application/json',
        )

    def test_aching_10_with_lenient_client_action_still_stops(self):
        resp = self._post_result(
            pain_reported=True, pain_type='aching',
            pain_location='right_knee', pain_severity=10,
            pain_action='reduce_volume',  # what the pre-G1 client sent
        )
        self.assertIn(reverse('v1_pain_stop'), resp.json()['next_url'])
        self.assertTrue(self.client.session.get('v1_pain_stop'))

    def test_aching_8_stops_even_with_action_continue(self):
        resp = self._post_result(
            pain_reported=True, pain_type='aching',
            pain_location='right_knee', pain_severity=8,
            pain_action='continue',
        )
        self.assertIn(reverse('v1_pain_stop'), resp.json()['next_url'])

    def test_severity_7_does_not_stop_session(self):
        # 7 stays below the stop tier — same-pattern skip (DA-F2) still
        # applies, but the session itself continues.
        resp = self._post_result(
            pain_reported=True, pain_type='aching',
            pain_location='right_knee', pain_severity=7,
            pain_action='reduce_volume',
        )
        self.assertNotIn(reverse('v1_pain_stop'), resp.json()['next_url'])
