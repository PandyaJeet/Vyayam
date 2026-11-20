"""The desktop TTS engine must never start while the test runner is active."""
from unittest import mock

from django.test import SimpleTestCase

from strength_app.exercise_system.core import voice_coach_v2 as vc


class TestTtsGuardUnderTests(SimpleTestCase):
    def test_engine_never_initialised_under_tests(self):
        self.assertTrue(vc.UNDER_TESTS)
        self.assertFalse(vc.VoiceCoachV2._voice_enabled)
        with mock.patch.object(vc, 'pyttsx3', create=True) as fake:
            self.assertIsNone(vc.VoiceCoachV2._get_engine())
            coach = vc.VoiceCoachV2()
            self.assertIsNone(coach.speech_thread)
            fake.init.assert_not_called()
        self.assertIsNone(vc.VoiceCoachV2._tts_engine)
