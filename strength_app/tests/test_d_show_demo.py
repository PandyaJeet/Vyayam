"""
Phase D — the demo is opt-in. The camera screen lands straight on the
working view; a "Show demo" button (single renameable string) runs
guidance → demo on demand. These tests pin the server-renderable half:
the button is present on every camera-screen variant and the old forced
"Watch Demo Again" entry point is gone. The state-machine behavior
(CALIBRATING → WAITING default) is exercised manually + via the G0
inline-JS harness.
"""

from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse


class TestPhaseDShowDemoButton(TestCase):

    def setUp(self):
        cache.clear()
        call_command('seed_therapist_demo', stdout=StringIO())
        resp = self.client.post(
            reverse('patient_login'),
            {'phone': '9000000001', 'password': 'patient'},
        )
        self.assertEqual(resp.status_code, 302, 'patient login failed')
        resp = self.client.post(reverse('therapist_session_start'))
        self.assertEqual(resp.status_code, 302, 'session start failed')

    def test_camera_screen_has_opt_in_demo_no_forced_entry(self):
        resp = self.client.get(reverse('therapist_session_exercise', args=[0]))
        self.assertTemplateUsed(resp, 'strength_app/v1_exercise_execute.html')
        content = resp.content.decode('utf-8')

        # The opt-in button exists (placeholder + status card = 2 spots),
        # driven by the single renameable label string.
        self.assertEqual(content.count('onclick="showDemo()"'), 2)
        self.assertIn("var SHOW_DEMO_LABEL = 'Show demo';", content)

        # The old always-forced sequence entry points are gone: no direct
        # mode='DEMO' onclick, and calibration hands over via demoRequested.
        self.assertNotIn('Watch Demo Again', content)
        self.assertIn('demoRequested', content)
