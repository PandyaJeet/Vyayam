"""RTP Tier 2: S8 feedback fields, S9 hold wiring and comparator, S5 clearance,
S7 checkpoints, and SPINE_SPEC tests 15, 16, 17."""

from django.test import TestCase, override_settings
from django.urls import reverse

from strength_app.models import SessionFeedback
from strength_app.rtp import availability as av
from strength_app.rtp.models import AuditLog, AvailabilityStatus, InjuryEpisode
from strength_app.tests.test_mind_lab import make_athlete
from strength_app.tests.test_rtp_tier1 import make_therapist


class Tier2Base(TestCase):
    def setUp(self):
        self.athlete, self.coach_user = make_athlete()
        self.coach = self.coach_user.therapistprofile
        self.therapist = make_therapist('1')
        self.athlete.assigned_therapist = self.therapist
        self.athlete.save()
        s = self.client.session
        s['patient_id'] = self.athlete.patient_id
        s['v1_exercise_results'] = []
        s.save()

    def open_episode(self):
        return InjuryEpisode.objects.create(patient=self.athlete, opened_by=self.therapist)

    def submit(self, **extra):
        data = {'perceived_difficulty': 'just_right', 'pain_reported': 'none'}
        data.update(extra)
        resp = self.client.post(reverse('v1_post_session_feedback'), data=data)
        self.assertEqual(resp.status_code, 302)
        return SessionFeedback.objects.filter(patient=self.athlete).order_by('-pk').first()


@override_settings(RTP_ENABLED=True)
class TestS8FeedbackFields(Tier2Base):
    def test_questions_shown_only_with_active_episode(self):
        url = reverse('v1_post_session_feedback')
        self.assertNotContains(self.client.get(url), 'swelling_today')
        ep = self.open_episode()
        self.assertContains(self.client.get(url), 'swelling_today')
        from django.utils import timezone
        ep.closed_at = timezone.now()
        ep.save()
        self.assertNotContains(self.client.get(url), 'swelling_today')

    @override_settings(RTP_ENABLED=False)
    def test_questions_hidden_when_flag_off(self):
        self.open_episode()
        self.assertNotContains(self.client.get(reverse('v1_post_session_feedback')), 'swelling_today')

    def test_answers_saved_for_active_episode(self):
        self.open_episode()
        f = self.submit(swelling_today='no', giving_way='no', locking_or_catching='no',
                        tightness_0_10='4', tightness_location=' Left hamstring ')
        self.assertIs(f.swelling_today, False)
        self.assertIs(f.giving_way, False)
        self.assertIs(f.locking_or_catching, False)
        self.assertEqual(f.tightness_0_10, 4)
        self.assertEqual(f.tightness_location, 'Left hamstring')

    def test_blank_and_junk_stay_null(self):
        self.open_episode()
        f = self.submit(swelling_today='', giving_way='maybe', tightness_0_10='lots')
        self.assertIsNone(f.swelling_today)
        self.assertIsNone(f.giving_way)
        self.assertIsNone(f.locking_or_catching)
        self.assertIsNone(f.tightness_0_10)
        self.assertFalse(av.is_held(self.athlete))

    def test_posted_answers_ignored_without_episode(self):
        f = self.submit(swelling_today='yes', giving_way='yes', locking_or_catching='yes',
                        tightness_0_10='9')
        self.assertIsNone(f.swelling_today)
        self.assertIsNone(f.locking_or_catching)
        self.assertIsNone(f.tightness_0_10)


@override_settings(RTP_ENABLED=True)
class TestS9HoldEndToEnd(Tier2Base):
    """SPINE_SPEC test 19, through the real feedback view. No helper is called directly."""

    def test_swelling_yes_holds_athlete_with_episode(self):
        self.open_episode()
        self.assertFalse(AvailabilityStatus.objects.filter(patient=self.athlete).exists())
        self.submit(swelling_today='yes')
        self.assertTrue(av.is_held(self.athlete))
        self.assertEqual(av.effective_status(self.athlete), 'medical hold')
        self.assertTrue(AuditLog.objects.filter(action='place_hold', outcome='allowed',
                                                actor_role='system').exists())

    def test_giving_way_yes_holds_athlete_with_episode(self):
        self.open_episode()
        self.submit(giving_way='yes')
        self.assertTrue(av.is_held(self.athlete))

    def test_locking_yes_holds_athlete_with_episode(self):
        self.open_episode()
        self.submit(locking_or_catching='yes')
        self.assertTrue(av.is_held(self.athlete))

    def test_hold_means_no_session_and_stage_untouched(self):
        self.open_episode()
        av.set_stage(self.athlete, 2, actor=self.therapist)
        self.submit(swelling_today='yes')
        row = AvailabilityStatus.objects.get(patient=self.athlete)
        self.assertEqual((row.stage_number, row.base_status), (2, 'rehab_stage'))
        from strength_app.v1_prescription_engine import generate_v1_session
        self.assertEqual(generate_v1_session(self.athlete).get('status'), 'stopped')

    def test_no_answers_no_hold(self):
        self.open_episode()
        self.submit(swelling_today='no', giving_way='no', locking_or_catching='no')
        self.assertFalse(av.is_held(self.athlete))

    def test_swelling_yes_without_episode_never_holds(self):
        self.submit(swelling_today='yes', giving_way='yes')
        self.assertFalse(av.is_held(self.athlete))

    @override_settings(RTP_ENABLED=False)
    def test_flag_off_never_holds(self):
        self.open_episode()
        self.submit(swelling_today='yes')
        self.assertFalse(AvailabilityStatus.objects.filter(patient=self.athlete).exists())
