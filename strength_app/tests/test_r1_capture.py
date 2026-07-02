"""
R1 — capture layer tests: per-set logs (camera batch + guided tap), rest and
pause events, rep-pinned pain, exercise start stamps. Malformed input policy
throughout: clamp what can be clamped, drop what can't (with a warning),
never 500 the patient's flow.
"""

import json
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from strength_app.models import PainEvent, PatientProfile, RestEvent
from therapist_app.models import ExerciseSetLog, SessionLogItem


class CaptureBase(TestCase):
    """Seeded managed patient (Anika), logged in, session started.
    Seed exercise order: 0 glute bridge (camera), 1 clamshell (camera),
    2 single-leg balance (guided), 3 step-up (camera), 4 side plank."""

    def setUp(self):
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

    def post_json(self, url_name, idx, payload):
        return self.client.post(
            reverse(url_name, args=[idx]),
            data=json.dumps(payload),
            content_type='application/json',
        )


class TestR1aSetLog(CaptureBase):

    def test_camera_set_log_round_trip_with_clamps(self):
        payload = {
            'set_number': 1,
            'mode': 'camera',
            'reps_count': 12,
            'hold_seconds': 0,
            'duration_ms': 45000,
            'demo_viewed': True,
            'reps': [
                {'rep_n': 1, 'partial': False, 'form_pct': 88.4,
                 'bottom_angle': 92.3,
                 'phase_ms': {'ecc': 2800, 'hold': 900, 'con': 1600},
                 'phases_raw': [{'name': 'down', 'ms': 2800},
                                {'name': 'hold', 'ms': 900},
                                {'name': 'up', 'ms': 1600}],
                 'cues': [{'cue_id': 'knee_valgus', 'corrected': True}]},
                # Hostile values must clamp, not 500 and not persist junk.
                {'rep_n': 999999, 'form_pct': 250, 'bottom_angle': -40,
                 'phase_ms': {'ecc': 10 ** 9, 'junk_key': 5},
                 'cues': [{'cue_id': 'x' * 500, 'corrected': 'yes'},
                          'not-a-dict', {'no_id': True}]},
            ],
        }
        resp = self.post_json('therapist_session_set_log', 0, payload)
        self.assertEqual(resp.status_code, 200)

        row = ExerciseSetLog.objects.get()
        self.assertEqual(row.exercise_id, 'ex_glute_bridge')
        self.assertEqual(row.mode, 'camera')
        self.assertEqual(row.set_number, 1)
        self.assertEqual(row.reps_count, 12)
        self.assertTrue(row.demo_viewed)
        self.assertIsNotNone(row.started_at)
        self.assertIsNotNone(row.ended_at)
        self.assertEqual(
            round((row.ended_at - row.started_at).total_seconds()), 45)

        reps = row.reps_json
        self.assertEqual(len(reps), 2)
        self.assertEqual(reps[0]['phase_ms'], {'ecc': 2800, 'hold': 900, 'con': 1600})
        self.assertEqual(reps[0]['cues'], [{'cue_id': 'knee_valgus', 'corrected': True}])
        # Clamped hostile rep:
        self.assertEqual(reps[1]['rep_n'], 200)
        self.assertEqual(reps[1]['form_pct'], 100)
        self.assertEqual(reps[1]['bottom_angle'], 0)
        self.assertEqual(reps[1]['phase_ms'], {'ecc': 120000})
        self.assertEqual(len(reps[1]['cues']), 1)
        self.assertEqual(len(reps[1]['cues'][0]['cue_id']), 40)
        self.assertIs(reps[1]['cues'][0]['corrected'], True)

    def test_set_log_retry_is_idempotent(self):
        for reps_count in (10, 11):  # client retry with corrected count
            self.post_json('therapist_session_set_log', 0, {
                'set_number': 2, 'mode': 'camera', 'reps_count': reps_count,
                'duration_ms': 30000, 'reps': [],
            })
        rows = ExerciseSetLog.objects.filter(set_number=2)
        self.assertEqual(rows.count(), 1, 'retry must not duplicate the set')
        self.assertEqual(rows.get().reps_count, 11)

    def test_malformed_reps_array_dropped_never_500(self):
        for bad_reps in ('not-a-list', {'a': 1}, 42):
            resp = self.post_json('therapist_session_set_log', 0, {
                'set_number': 1, 'mode': 'camera', 'reps_count': 8,
                'reps': bad_reps,
            })
            self.assertEqual(resp.status_code, 200, f'reps={bad_reps!r}')
            self.assertEqual(ExerciseSetLog.objects.get().reps_json, [])

    def test_non_dict_body_is_400(self):
        resp = self.client.post(
            reverse('therapist_session_set_log', args=[0]),
            data=json.dumps([1, 2, 3]), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_guided_set_row(self):
        resp = self.post_json('therapist_session_set_log', 2, {
            'set_number': 1, 'mode': 'guided', 'reps_count': 30,
            'duration_ms': 40000, 'reps': [],
        })
        self.assertEqual(resp.status_code, 200)
        row = ExerciseSetLog.objects.get()
        self.assertEqual(row.exercise_id, 'ex_sl_balance')
        self.assertEqual(row.mode, 'guided')
        self.assertEqual(row.reps_json, [])

    def test_requires_live_session(self):
        fresh = self.client_class()
        fresh.post(reverse('patient_login'),
                   {'phone': '9000000001', 'password': 'patient'})
        resp = fresh.post(
            reverse('therapist_session_set_log', args=[0]),
            data=json.dumps({'set_number': 1}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(ExerciseSetLog.objects.count(), 0)


class TestR1bRestEvents(CaptureBase):

    def test_extension_pause_and_skip_rows(self):
        self.post_json('therapist_session_rest_event', 3,
                       {'kind': 'extension', 'seconds': 30, 'set_number': 2})
        self.post_json('therapist_session_rest_event', 1,
                       {'kind': 'pause', 'seconds': 220, 'set_number': 1})
        self.post_json('therapist_session_rest_event', 3,
                       {'kind': 'skip', 'seconds': 0, 'set_number': 3})

        ext = RestEvent.objects.get(context='between_sets', cut_short=False)
        self.assertEqual(ext.exercise_id, 'ex_step_up')
        self.assertEqual(ext.extra_seconds, 30)
        self.assertEqual(ext.set_number, 2)
        self.assertIsNotNone(ext.session_log)

        pause = RestEvent.objects.get(context='pause')
        self.assertEqual(pause.exercise_id, 'ex_clamshell')
        self.assertEqual(pause.extra_seconds, 220)

        skipped = RestEvent.objects.get(cut_short=True)
        self.assertEqual(skipped.extra_seconds, 0)
        self.assertEqual(skipped.set_number, 3)

    def test_bad_kind_is_400_and_seconds_clamped(self):
        resp = self.post_json('therapist_session_rest_event', 0,
                              {'kind': 'nonsense', 'seconds': 30})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(RestEvent.objects.count(), 0)

        self.post_json('therapist_session_rest_event', 0,
                       {'kind': 'extension', 'seconds': 999999})
        self.assertEqual(RestEvent.objects.get().extra_seconds, 600)


class TestR1dRepPinnedPain(CaptureBase):

    def report(self, idx=0, **extra):
        payload = {'severity': 4, 'pain_type': 'aching', 'set_number': 2}
        payload.update(extra)
        return self.post_json('therapist_session_report_pain', idx, payload)

    def test_rep_number_persisted(self):
        self.report(rep_number=6)
        event = PainEvent.objects.get()
        self.assertEqual(event.rep_number, 6)
        self.assertEqual(event.set_number, 2)

    def test_rep_number_clamped_and_optional(self):
        self.report(rep_number=99999)
        self.assertEqual(PainEvent.objects.latest('id').rep_number, 200)
        self.report(rep_number='abc')
        self.assertIsNone(PainEvent.objects.latest('id').rep_number)
        self.report()  # guided screens send nothing
        self.assertIsNone(PainEvent.objects.latest('id').rep_number)


class TestR1cTimestamps(CaptureBase):

    def test_exercise_page_stamps_started_at_once(self):
        item = SessionLogItem.objects.order_by('order').first()
        self.assertIsNone(item.started_at)
        self.client.get(reverse('therapist_session_exercise', args=[0]))
        item.refresh_from_db()
        first_stamp = item.started_at
        self.assertIsNotNone(first_stamp)
        # Revisiting must not move the start (first GET wins).
        self.client.get(reverse('therapist_session_exercise', args=[0]))
        item.refresh_from_db()
        self.assertEqual(item.started_at, first_stamp)


class TestR1CaptureUIRendered(CaptureBase):
    """The controls the events come from actually render on both screens."""

    def test_camera_screen_has_capture_controls(self):
        resp = self.client.get(reverse('therapist_session_exercise', args=[0]))
        self.assertTemplateUsed(resp, 'strength_app/v1_exercise_execute.html')
        content = resp.content.decode('utf-8')
        self.assertIn('Pause session', content)
        self.assertIn('+30s', content)
        self.assertIn('rep_number: painRepAtOpen', content)
        self.assertIn('RepCapture', content)

    def test_guided_screen_has_capture_controls(self):
        resp = self.client.get(reverse('therapist_session_exercise', args=[2]))
        self.assertTemplateUsed(
            resp, 'strength_app/therapist_session_exercise.html')
        content = resp.content.decode('utf-8')
        self.assertIn('Pause session', content)
        self.assertIn('rest-extend', content)
        self.assertIn("mode: 'guided'", content)
