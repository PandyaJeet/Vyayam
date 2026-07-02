"""
Phase F — friendlier voice. Pins the server-renderable half: every
speech-producing page loads voice_core.js, TTS settings route through
VyayamVoice.applyTo, and the dormant clip scaffold is wired. The
pickVoice ordering itself is covered by node
(strength_app/tests/js/voice_core.test.mjs).
"""

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse


class TestPhaseFVoiceWiring(TestCase):

    def setUp(self):
        cache.clear()
        call_command('seed_therapist_demo', stdout=StringIO())
        resp = self.client.post(
            reverse('patient_login'),
            {'phone': '9000000001', 'password': 'patient'},
        )
        self.assertEqual(resp.status_code, 302, 'patient login failed')

    def test_camera_screen_uses_voice_core(self):
        self.client.post(reverse('therapist_session_start'))
        resp = self.client.get(reverse('therapist_session_exercise', args=[0]))
        content = resp.content.decode('utf-8')
        # Manifest static storage hashes the filename (voice_core.<hash>.js).
        self.assertIn('js/voice_core.', content)
        self.assertIn('VyayamVoice.applyTo(utt)', content)
        self.assertIn('VyayamVoice.tryPlayClip(text)', content)
        # The old hand-rolled voice pick and split rates are gone.
        self.assertNotIn("utt.rate = priority ? 0.95 : 0.88", content)

    def test_voice_core_module_and_clip_scaffold_exist(self):
        js = Path(settings.BASE_DIR, 'strength_app', 'static',
                  'strength_app', 'js', 'voice_core.js')
        self.assertTrue(js.exists())
        source = js.read_text(encoding='utf-8')
        self.assertIn("['Google', 'Natural', 'Enhanced', 'Samantha', 'Ava']",
                      source)
        self.assertIn('voiceschanged', source)
        self.assertIn('/static/strength_app/audio/coach/', source)

        readme = Path(settings.BASE_DIR, 'strength_app', 'static',
                      'strength_app', 'audio', 'coach', 'README.txt')
        self.assertTrue(readme.exists(), 'clip recording list must ship')
        # Dormant: no mp3 files are fabricated.
        coach_dir = readme.parent
        self.assertEqual(list(coach_dir.glob('*.mp3')), [],
                         'Phase F ships with NO audio files')
