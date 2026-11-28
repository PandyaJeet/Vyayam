"""
Bicep curls as a CAMERA therapist exercise (engine key 'bicep_curls',
js_type 'CURL', coach in coach_dark.js).

Pins:
  - catalog row ex_bicep_curl: Pull, Dumbbell, ghost True, key not '_rx'
  - targets artifact: bicep_curls camera, js_type CURL, phases, no overrides
  - gap-fill content exists and merges into EXERCISE_CONTENT
  - the therapist session renders the camera page with the CURL config
  - a camera set persists once, and a retry of the same set stays one row
  - the library route opens the same camera config
  - the legacy ROW map line is gone from the template
  - the 3 curl cue ids are synced in coach_core CUES and report CUE_TEXT
  - the QA dark-coach surface never lists it
"""

import json
import re
from io import StringIO
from pathlib import Path

from django.core.cache import cache
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

import strength_app
from therapist_app.models import ExerciseSetLog, PrescriptionItem

KEY = 'bicep_curls'
EX_ID = 'ex_bicep_curl'
CURL_CUE_IDS = ['curl_elbows_still', 'curl_stand_tall', 'curl_full_range']
APP_DIR = Path(strength_app.__file__).parent


def _compact(resp):
    return re.sub(r'\s+', '', resp.content.decode())


class TestBicepCurlCatalogAndContent(SimpleTestCase):

    def test_catalog_row_is_camera_pull_dumbbell(self):
        from therapist_app.exercise_catalog import EXERCISES, EXERCISES_BY_ID
        entry = EXERCISES_BY_ID[EX_ID]
        self.assertEqual(entry['v2_exercise_key'], KEY)
        self.assertIs(entry['v2_ghost_supported'], True)
        self.assertFalse(entry['v2_exercise_key'].endswith('_rx'))
        self.assertEqual(entry['movement_pattern'], 'Pull')
        self.assertEqual(entry['equipment'], 'Dumbbell')
        self.assertEqual(entry['name'], 'Bicep Curl')
        # one row only, no alias key
        rows = [e for e in EXERCISES if e['v2_exercise_key'] == KEY]
        self.assertEqual(len(rows), 1)

    def test_targets_are_camera_curl(self):
        from strength_app.cv_targets import get_cv_config
        cfg = get_cv_config(KEY)
        self.assertEqual(cfg['tracking'], 'camera')
        self.assertEqual(cfg['js_type'], 'CURL')
        self.assertTrue(cfg.get('phases'))
        self.assertFalse(cfg.get('is_hold'))
        self.assertFalse(cfg.get('js_overrides'))

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

    def test_template_has_no_legacy_row_mapping(self):
        text = (APP_DIR / 'templates' / 'strength_app' /
                'v1_exercise_execute.html').read_text(encoding='utf-8')
        self.assertNotIn("'bicep_curls': 'ROW_HORIZONTAL'", text)

    def test_curl_cue_ids_synced(self):
        from strength_app.tests.test_camera_dark import (
            _coach_core_cue_ids, _report_cue_ids,
        )
        core_ids = _coach_core_cue_ids()
        report_ids = _report_cue_ids()
        dark_js = (APP_DIR / 'static' / 'strength_app' / 'js' /
                   'coach_dark.js').read_text(encoding='utf-8')
        self.assertIn('PHASES.CURL = {', dark_js)
        for cue_id in CURL_CUE_IDS:
            self.assertIn(cue_id, core_ids, cue_id)
            self.assertIn(cue_id, report_ids, cue_id)
            self.assertIn(f"'{cue_id}'", dark_js, cue_id)


class TestBicepCurlCameraSession(TestCase):

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

    def test_therapist_page_is_camera_curl(self):
        resp = self.client.get(reverse('therapist_session_exercise', args=[0]))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'strength_app/v1_exercise_execute.html')
        body = _compact(resp)
        self.assertIn('"tracking":"camera"', body)
        self.assertIn('"js_type":"CURL"', body)
        self.assertIn('coach_dark.js', body)
        self.assertNotContains(resp, 'Video demo coming soon')

    def test_camera_set_persists_once(self):
        self.client.get(reverse('therapist_session_exercise', args=[0]))
        url = reverse('therapist_session_set_log', args=[0])
        payload = {'mode': 'camera', 'set_number': 1, 'reps_count': 12,
                   'reps': [{'rep_n': 1, 'partial': False}]}
        for _ in range(2):  # a client retry must not duplicate the set
            resp = self.client.post(url, data=json.dumps(payload),
                                    content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), {'ok': True})
        rows = ExerciseSetLog.objects.filter(exercise_id=EX_ID)
        self.assertEqual(rows.count(), 1)
        row = rows.get()
        self.assertEqual(row.mode, 'camera')
        self.assertEqual(row.reps_count, 12)
        self.assertEqual(row.set_number, 1)

    def test_library_route_is_camera_curl(self):
        resp = self.client.get(f'/exercises/{KEY}/execute/')
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'strength_app/v1_exercise_execute.html')
        body = _compact(resp)
        self.assertIn('"tracking":"camera"', body)
        self.assertIn('"js_type":"CURL"', body)

    def test_library_route_tempo_is_2_1_2_0(self):
        body = _compact(self.client.get(f'/exercises/{KEY}/execute/'))
        self.assertIn('constTEMPO_PARTS=["2","1","2","0"]', body)

    def test_other_exercise_keeps_default_tempo(self):
        resp = self.client.get('/exercises/full_squats/execute/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('constTEMPO_PARTS=["3","1","2","0"]', _compact(resp))

    def test_therapist_tempo_blank_uses_curl_metadata(self):
        # The seeded first item carries glute bridge tempo '3-1-1'; blank it.
        item = PrescriptionItem.objects.order_by('order').first()
        item.tempo = ''
        item.save(update_fields=['tempo'])
        resp = self.client.get(reverse('therapist_session_exercise', args=[0]))
        self.assertIn('constTEMPO_PARTS=["2","1","2","0"]', _compact(resp))

    def test_therapist_item_tempo_wins(self):
        item = PrescriptionItem.objects.order_by('order').first()
        item.tempo = '4-1-3-0'
        item.save(update_fields=['tempo'])
        resp = self.client.get(reverse('therapist_session_exercise', args=[0]))
        self.assertIn('constTEMPO_PARTS=["4","1","3","0"]', _compact(resp))


class TestBicepCurlExactTempo(SimpleTestCase):

    def test_template_reads_exact_tempo_and_keeps_floors(self):
        text = (APP_DIR / 'templates' / 'strength_app' /
                'v1_exercise_execute.html').read_text(encoding='utf-8')
        # DEMO floor, GHOST_LEADS floor, between-rep gate.
        self.assertEqual(text.count('exactTempo'), 3)
        self.assertIn('Math.max(phase.duration || 0, 1500)', text)
        self.assertIn('Math.max(phase.duration || 0, 2000)', text)
        self.assertIn('restModeUntil = Date.now() + 3000', text)

    def test_registry_tempo(self):
        from strength_app.exercise_system.exercise_registry_v2 import (
            EXERCISE_METADATA,
        )
        self.assertEqual(EXERCISE_METADATA[KEY]['tempo'], '2-1-2-0')

    def test_text_has_no_old_tempo(self):
        from therapist_app.exercise_catalog import EXERCISES_BY_ID
        from strength_app.exercise_content_gap_fill import (
            EXERCISE_CONTENT_GAP_FILL,
        )
        desc = EXERCISES_BY_ID[EX_ID]['description']
        self.assertNotIn('2-3 seconds', desc)
        self.assertIn('squeeze for 1 second', desc)
        content = EXERCISE_CONTENT_GAP_FILL[KEY]
        lines = ' '.join(content['instructions'] + content['form_cues'])
        self.assertNotIn('2 to 3 seconds', lines)
        self.assertNotIn('briefly', lines)


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
