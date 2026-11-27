"""
Bicep curls as a GUIDED therapist exercise (engine key 'bicep_curls').

Pins:
  - catalog row ex_bicep_curl: Pull, Dumbbell, ghost False, key not '_rx'
  - targets artifact keeps bicep_curls manual with no js_type
  - gap-fill content exists and merges into EXERCISE_CONTENT
  - the therapist session renders the no-camera guided page, no pacer
  - a guided set persists once, and a retry of the same set stays one row
  - the QA dark-coach surface never lists it
"""

import json
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from therapist_app.models import ExerciseSetLog, PrescriptionItem

KEY = 'bicep_curls'
EX_ID = 'ex_bicep_curl'


class TestBicepCurlCatalogAndContent(SimpleTestCase):

    def test_catalog_row_is_guided_pull_dumbbell(self):
        from therapist_app.exercise_catalog import EXERCISES, EXERCISES_BY_ID
        entry = EXERCISES_BY_ID[EX_ID]
        self.assertEqual(entry['v2_exercise_key'], KEY)
        self.assertIs(entry['v2_ghost_supported'], False)
        self.assertFalse(entry['v2_exercise_key'].endswith('_rx'))
        self.assertEqual(entry['movement_pattern'], 'Pull')
        self.assertEqual(entry['equipment'], 'Dumbbell')
        self.assertEqual(entry['name'], 'Bicep Curl')
        # one row only, no alias key
        rows = [e for e in EXERCISES if e['v2_exercise_key'] == KEY]
        self.assertEqual(len(rows), 1)

    def test_targets_stay_manual(self):
        from strength_app.cv_targets import get_cv_config
        cfg = get_cv_config(KEY)
        self.assertEqual(cfg['tracking'], 'manual')
        self.assertIsNone(cfg['js_type'])

    def test_content_present_and_merged(self):
        from strength_app.exercise_content import EXERCISE_CONTENT
        from strength_app.exercise_content_gap_fill import (
            EXERCISE_CONTENT_GAP_FILL,
        )
        content = EXERCISE_CONTENT_GAP_FILL[KEY]
        self.assertTrue(content['instructions'])
        self.assertTrue(content['form_cues'])
        self.assertEqual(content['movement_pattern'], 'pull')
        self.assertIn(KEY, EXERCISE_CONTENT)
        self.assertEqual(EXERCISE_CONTENT[KEY]['form_cues'],
                         content['form_cues'])


class TestBicepCurlGuidedSession(TestCase):

    def setUp(self):
        cache.clear()
        call_command('seed_therapist_demo', stdout=StringIO())
        # Same fields the program builder copies from the catalog row.
        item = PrescriptionItem.objects.order_by('order').first()
        item.exercise_id = EX_ID
        item.exercise_name = 'Bicep Curl'
        item.movement_pattern = 'Pull'
        item.save(update_fields=[
            'exercise_id', 'exercise_name', 'movement_pattern'])
        resp = self.client.post(
            reverse('patient_login'),
            {'phone': '9000000001', 'password': 'patient'},
        )
        self.assertEqual(resp.status_code, 302, 'patient login failed')
        resp = self.client.post(reverse('therapist_session_start'))
        self.assertEqual(resp.status_code, 302, 'session start failed')

    def test_guided_page_has_no_camera_and_no_pacer(self):
        resp = self.client.get(reverse('therapist_session_exercise', args=[0]))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(
            resp, 'strength_app/therapist_session_exercise.html')
        self.assertTemplateNotUsed(
            resp, 'strength_app/v1_exercise_execute.html')
        self.assertContains(resp, 'Bicep Curl')
        self.assertContains(resp, '>Pull</span>')
        self.assertContains(resp, '>Dumbbell</span>')
        self.assertContains(resp, 'Video demo coming soon')
        self.assertNotContains(resp, 'Count-along pacer')
        self.assertNotContains(resp, 'getUserMedia')

    def test_guided_set_persists_once(self):
        self.client.get(reverse('therapist_session_exercise', args=[0]))
        url = reverse('therapist_session_set_log', args=[0])
        payload = {'mode': 'guided', 'set_number': 1, 'reps_count': 12}
        for _ in range(2):  # a client retry must not duplicate the set
            resp = self.client.post(url, data=json.dumps(payload),
                                    content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), {'ok': True})
        rows = ExerciseSetLog.objects.filter(exercise_id=EX_ID)
        self.assertEqual(rows.count(), 1)
        row = rows.get()
        self.assertEqual(row.mode, 'guided')
        self.assertEqual(row.reps_count, 12)
        self.assertEqual(row.set_number, 1)


class TestBicepCurlNotADarkCoach(TestCase):

    def test_excluded_from_dark_coach_qa_list(self):
        from django.contrib.auth.models import User
        from therapist_app.models import Therapist
        from therapist_app.views import _dark_coach_entries
        ids = [e['exercise_id'] for e in _dark_coach_entries()]
        self.assertNotIn(EX_ID, ids)
        self.assertEqual(len(ids), 11)
        user = User.objects.create_user('dr_curl_qa', password='x')
        Therapist.objects.create(user=user, full_name='Dr Curl QA')
        self.client.force_login(user)
        resp = self.client.get('/therapist/qa/dark-coaches/')
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertNotIn('Bicep Curl', body)
        self.assertEqual(body.count('>DARK<'), 11)
