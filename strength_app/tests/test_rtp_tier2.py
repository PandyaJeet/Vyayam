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


@override_settings(RTP_ENABLED=True)
class TestS5Clearance(Tier2Base):
    def test_therapist_approves_and_it_is_recorded(self):
        from strength_app.rtp import clearance
        row = clearance.decide(self.athlete, 'approved', actor=self.therapist,
                               restrictions=['no_plyo'])
        self.assertEqual(clearance.active_clearance(self.athlete), row)
        self.assertEqual(row.restrictions, ['no_plyo'])

    def test_coach_cannot_decide_and_is_audited(self):
        from strength_app.rtp import clearance
        self.assertIsNone(clearance.decide(self.athlete, 'approved', actor=self.coach))
        self.assertIsNone(clearance.active_clearance(self.athlete))
        self.assertTrue(AuditLog.objects.filter(action='clearance_decision', outcome='denied',
                                                actor_role='coach').exists())

    def test_nothing_in_the_app_approves_on_its_own(self):
        from strength_app.rtp import clearance
        from strength_app.rtp.models import ClearanceRecord
        self.open_episode()
        self.submit(swelling_today='no', giving_way='no', locking_or_catching='no')
        av.apply_feedback_hold(self.athlete, SessionFeedback.objects.first())
        self.assertEqual(ClearanceRecord.objects.count(), 0)
        self.assertIsNone(clearance.decide(self.athlete, 'maybe', actor=self.therapist))

    def test_red_flag_invalidates_clearance_end_to_end(self):
        from strength_app.rtp import clearance
        self.open_episode()
        clearance.decide(self.athlete, 'approved', actor=self.therapist)
        self.assertIsNotNone(clearance.active_clearance(self.athlete))
        self.submit(giving_way='yes')  # through the real view
        self.assertTrue(av.is_held(self.athlete))
        self.assertIsNone(clearance.active_clearance(self.athlete))

    def test_cannot_approve_while_held_and_approval_never_lifts_hold(self):
        from strength_app.rtp import clearance
        av.place_hold(self.athlete, role='system')
        self.assertIsNone(clearance.decide(self.athlete, 'approved', actor=self.therapist))
        self.assertTrue(av.is_held(self.athlete))
        declined = clearance.decide(self.athlete, 'declined', actor=self.therapist)
        self.assertIsNotNone(declined)
        self.assertTrue(av.is_held(self.athlete))

    def test_new_decision_supersedes_old_approval(self):
        from strength_app.rtp import clearance
        first = clearance.decide(self.athlete, 'approved', actor=self.therapist)
        second = clearance.decide(self.athlete, 'approved', actor=self.therapist)
        first.refresh_from_db()
        self.assertEqual(first.invalidated_reason, 'superseded')
        self.assertEqual(clearance.active_clearance(self.athlete), second)


@override_settings(RTP_ENABLED=True)
class TestS7Checkpoints(Tier2Base):
    def setUp(self):
        super().setUp()
        from strength_app.rtp import checkpoints
        self.cp = checkpoints
        self.point = checkpoints.open_checkpoint(self.athlete, actor=self.therapist, stage_number=2)

    def test_spine16_coach_entry_stays_pending_and_cannot_pass_gate(self):
        for m in ('hop', 'sprint', 'nordic'):
            row = self.cp.enter_measure(self.point, m, '1.0', actor=self.coach)
            self.assertEqual((row.status, row.entered_by_role), ('pending', 'coach'))
        self.assertFalse(self.cp.pass_gate(self.point, actor=self.coach))
        self.assertFalse(self.cp.pass_gate(self.point, actor=self.therapist))  # still pending
        self.point.refresh_from_db()
        self.assertIsNone(self.point.passed_at)
        self.assertEqual(self.cp.checkpoint_state(self.athlete), 'due')
        self.assertTrue(AuditLog.objects.filter(action='pass_gate', outcome='denied',
                                                actor_role='coach').exists())

    def test_coach_cannot_confirm_therapist_can_then_pass(self):
        row = self.cp.enter_measure(self.point, 'hop', '150', actor=self.coach)
        self.assertFalse(self.cp.confirm_measure(row, actor=self.coach))
        row.refresh_from_db()
        self.assertEqual(row.status, 'pending')
        self.assertTrue(self.cp.confirm_measure(row, actor=self.therapist))
        self.assertTrue(self.cp.pass_gate(self.point, actor=self.therapist))
        self.assertEqual(self.cp.checkpoint_state(self.athlete), 'passed')

    def test_spine17_coach_cannot_enter_range_strength_palpation(self):
        from strength_app.rtp.models import CheckpointMeasure
        for m in ('range', 'manual_strength', 'palpation'):
            self.assertIsNone(self.cp.enter_measure(self.point, m, 'x', actor=self.coach))
        self.assertEqual(CheckpointMeasure.objects.count(), 0)
        self.assertEqual(AuditLog.objects.filter(action='enter_measure', outcome='denied',
                                                 actor_role='coach').count(), 3)

    def test_therapist_enters_any_measure_as_confirmed(self):
        for m in ('range', 'manual_strength', 'palpation', 'hop'):
            row = self.cp.enter_measure(self.point, m, 'x', actor=self.therapist)
            self.assertEqual((row.status, row.entered_by_role), ('confirmed', 'therapist'))

    def test_unlinked_user_and_junk_measure_rejected(self):
        stranger = make_therapist('9')
        self.assertIsNone(self.cp.enter_measure(self.point, 'hop', '1', actor=stranger))
        self.assertIsNone(self.cp.enter_measure(self.point, 'bogus', '1', actor=self.therapist))

    def test_coach_cannot_open_checkpoint(self):
        self.assertIsNone(self.cp.open_checkpoint(self.athlete, actor=self.coach))

    def test_pass_gate_refused_while_held_and_never_changes_stage(self):
        av.set_stage(self.athlete, 2, actor=self.therapist)
        av.place_hold(self.athlete, role='system')
        self.assertFalse(self.cp.pass_gate(self.point, actor=self.therapist))
        av.lift_hold(self.athlete, actor=self.therapist)
        self.assertTrue(self.cp.pass_gate(self.point, actor=self.therapist))
        self.assertEqual(AvailabilityStatus.objects.get(patient=self.athlete).stage_number, 2)
