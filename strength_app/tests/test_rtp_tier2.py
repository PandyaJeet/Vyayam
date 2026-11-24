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

    def test_red_without_episode_is_not_held_and_shows_no_hold_text(self):
        from strength_app.rtp.config import ATHLETE_HOLD_TEXT
        f = self.submit(pain_reported='severe')
        self.assertEqual(f.traffic_light, 'red')
        self.assertFalse(av.is_held(self.athlete))
        self.assertFalse(AvailabilityStatus.objects.filter(patient=self.athlete,
                                                           medical_hold=True).exists())
        today = self.client.get('/athlete/today/')
        self.assertEqual(today.status_code, 200)
        self.assertNotContains(today, ATHLETE_HOLD_TEXT)
        self.assertNotContains(today, 'rtpAthleteStatus')

    def test_red_with_active_episode_is_held(self):
        from strength_app.rtp.config import ATHLETE_HOLD_TEXT
        self.open_episode()
        f = self.submit(pain_reported='severe')
        self.assertEqual(f.traffic_light, 'red')
        self.assertTrue(av.is_held(self.athlete))
        self.assertContains(self.client.get('/athlete/today/'), ATHLETE_HOLD_TEXT)

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


# --- S9 comparator ---------------------------------------------------------

from datetime import date, timedelta  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from unittest import mock  # noqa: E402

from strength_app.rtp import config  # noqa: E402
from strength_app.rtp.comparator import compare_pain_feedback as cmp  # noqa: E402

DAY0 = date(2026, 11, 1)


def rec(day=0, **kw):
    base = dict(traffic_light='green', pain_severity=0, pain_location='',
                swelling_today=None, giving_way=None, tightness_0_10=None,
                locking_or_catching=None)
    base.update(kw)
    base['session'] = SimpleNamespace(session_date=DAY0 + timedelta(days=day))
    return SimpleNamespace(**base)


class TestComparator(TestCase):
    def test_missing_record_is_no_comparison(self):
        self.assertEqual(cmp(None, rec()), 'no_comparison')
        self.assertEqual(cmp(rec(), None), 'no_comparison')
        self.assertEqual(cmp(None, None), 'no_comparison')

    def test_traffic_light_higher_is_worse_lower_is_better(self):
        self.assertEqual(cmp(rec(traffic_light='green'), rec(1, traffic_light='yellow')), 'worse')
        self.assertEqual(cmp(rec(traffic_light='yellow'), rec(1, traffic_light='red')), 'worse')
        self.assertEqual(cmp(rec(traffic_light='red'), rec(1, traffic_light='green')), 'better')
        self.assertEqual(cmp(rec(traffic_light='red'), rec(1, traffic_light='red')), 'same')

    def test_severity_worse_only_at_delta(self):
        # yellow + a location, so the green-and-empty noise gate does not apply
        y = dict(traffic_light='yellow', pain_location='knee')
        with mock.patch.object(config, 'SEVERITY_DELTA', 2):
            self.assertEqual(cmp(rec(pain_severity=3, **y), rec(1, pain_severity=4, **y)), 'same')
            self.assertEqual(cmp(rec(pain_severity=3, **y), rec(1, pain_severity=5, **y)), 'worse')
            self.assertEqual(cmp(rec(pain_severity=5, **y), rec(1, pain_severity=3, **y)), 'better')

    def test_severity_3_to_4_with_green_light_and_empty_location_is_not_worse(self):
        self.assertEqual(config.SEVERITY_DELTA, 1)
        self.assertEqual(cmp(rec(pain_severity=3, traffic_light='green', pain_location=''),
                             rec(1, pain_severity=4, traffic_light='green', pain_location='  ')), 'same')

    def test_severity_3_to_5_with_yellow_light_and_location_is_worse(self):
        y = dict(traffic_light='yellow', pain_location='left knee')
        self.assertEqual(cmp(rec(pain_severity=3, **y), rec(1, pain_severity=5, **y)), 'worse')

    def test_swelling_and_giving_way_no_to_yes_is_worse(self):
        for name in ('swelling_today', 'giving_way'):
            self.assertEqual(cmp(rec(**{name: False}), rec(1, **{name: True})), 'worse', name)
            self.assertEqual(cmp(rec(**{name: True}), rec(1, **{name: False})), 'better', name)
            self.assertEqual(cmp(rec(**{name: True}), rec(1, **{name: True})), 'same', name)

    def test_tightness_worse_only_at_delta(self):
        with mock.patch.object(config, 'TIGHTNESS_DELTA', 3):
            self.assertEqual(cmp(rec(tightness_0_10=2), rec(1, tightness_0_10=4)), 'same')
            self.assertEqual(cmp(rec(tightness_0_10=2), rec(1, tightness_0_10=5)), 'worse')
            self.assertEqual(cmp(rec(tightness_0_10=6), rec(1, tightness_0_10=2)), 'better')

    def test_locking_yes_in_newer_record_is_worse_even_if_older_also_yes_or_null(self):
        self.assertEqual(cmp(rec(locking_or_catching=False), rec(1, locking_or_catching=True)), 'worse')
        self.assertEqual(cmp(rec(locking_or_catching=True), rec(1, locking_or_catching=True)), 'worse')
        self.assertEqual(cmp(rec(locking_or_catching=None), rec(1, locking_or_catching=True)), 'worse')
        self.assertEqual(cmp(rec(locking_or_catching=True), rec(1, locking_or_catching=False)), 'better')

    def test_location_ignored_by_default(self):
        self.assertFalse(config.LOCATION_CHANGE_COUNTS)
        self.assertEqual(cmp(rec(pain_location='left knee'), rec(1, pain_location='right ankle')), 'same')

    def test_location_counts_when_on_and_uses_shared_normalisation(self):
        with mock.patch.object(config, 'LOCATION_CHANGE_COUNTS', True):
            self.assertEqual(cmp(rec(pain_location='Left Knee '), rec(1, pain_location=' left knee')), 'same')
            self.assertEqual(cmp(rec(pain_location='left knee'), rec(1, pain_location='right ankle')), 'worse')
            # blank on either side skips the field; nothing else compares, so no_comparison
            blank = dict(pain_severity=None, traffic_light=None)
            self.assertEqual(cmp(rec(pain_location='', **blank),
                                 rec(1, pain_location='left knee', **blank)), 'no_comparison')

    def test_normaliser_is_the_one_in_v1_safety_logic(self):
        from strength_app import v1_safety_logic
        from strength_app.rtp import comparator
        self.assertIs(comparator.normalise_pain_location, v1_safety_logic.normalise_pain_location)

    def test_gap_is_calendar_days_between_session_dates(self):
        limit = config.MAX_GAP_DAYS
        self.assertEqual(cmp(rec(0, traffic_light='green'), rec(limit, traffic_light='red')), 'worse')
        self.assertEqual(cmp(rec(0, traffic_light='green'), rec(limit + 1, traffic_light='red')),
                         'no_comparison')
        with mock.patch.object(config, 'MAX_GAP_DAYS', 3):
            self.assertEqual(cmp(rec(0, traffic_light='green'), rec(3, traffic_light='red')), 'worse')
            self.assertEqual(cmp(rec(0, traffic_light='green'), rec(4, traffic_light='red')),
                             'no_comparison')

    def test_gap_counts_dates_not_24_hour_blocks(self):
        from datetime import datetime
        from django.utils import timezone
        a, b = rec(traffic_light='green'), rec(traffic_light='red')
        a.session.session_date = timezone.make_aware(datetime(2026, 11, 1, 23, 50))
        b.session.session_date = timezone.make_aware(datetime(2026, 11, 2, 0, 10))
        with mock.patch.object(config, 'MAX_GAP_DAYS', 1):
            self.assertEqual(cmp(a, b), 'worse')  # 20 minutes apart, 1 calendar day
        with mock.patch.object(config, 'MAX_GAP_DAYS', 0):
            self.assertEqual(cmp(a, b), 'no_comparison')

    def test_missing_or_reversed_dates_are_no_comparison(self):
        a, b = rec(traffic_light='green'), rec(1, traffic_light='red')
        b.session = SimpleNamespace(session_date=None)
        self.assertEqual(cmp(a, b), 'no_comparison')
        self.assertEqual(cmp(rec(5, traffic_light='green'), rec(0, traffic_light='red')), 'no_comparison')

    def test_null_skips_only_that_field(self):
        # tightness null on one side is skipped, the light still decides
        self.assertEqual(cmp(rec(tightness_0_10=None, traffic_light='green'),
                             rec(1, tightness_0_10=9, traffic_light='red')), 'worse')
        self.assertEqual(cmp(rec(swelling_today=None), rec(1, swelling_today=True)), 'same')

    def test_all_fields_null_is_no_comparison_and_null_never_holds(self):
        null = dict(traffic_light=None, pain_severity=None, swelling_today=None,
                    giving_way=None, tightness_0_10=None, locking_or_catching=None)
        self.assertEqual(cmp(rec(**null), rec(1, **null)), 'no_comparison')

    def test_precedence_worse_beats_better_beats_same(self):
        self.assertEqual(cmp(rec(traffic_light='red', swelling_today=False),
                             rec(1, traffic_light='green', swelling_today=True)), 'worse')
        self.assertEqual(cmp(rec(traffic_light='red', swelling_today=False),
                             rec(1, traffic_light='green', swelling_today=False)), 'better')
        self.assertEqual(cmp(rec(), rec(1)), 'same')

    def test_pure_no_queries_no_writes_inputs_unchanged(self):
        a, b = rec(traffic_light='green'), rec(1, traffic_light='red')
        before = (dict(vars(a)), dict(vars(b)))
        with self.assertNumQueries(0):
            cmp(a, b)
        self.assertEqual((dict(vars(a)), dict(vars(b))), before)


@override_settings(RTP_ENABLED=True)
class TestComparatorOnRealRecords(Tier2Base):
    def test_last_two_feedbacks_feed_the_comparator_without_writes(self):
        from strength_app.rtp import visibility
        self.open_episode()
        self.submit(swelling_today='no')
        self.submit(swelling_today='yes')
        prev, newest = visibility.last_two_feedbacks(self.athlete)
        self.assertEqual(cmp(prev, newest), 'worse')
        rows = AuditLog.objects.count()
        cmp(prev, newest)
        self.assertEqual(AuditLog.objects.count(), rows)


# --- SPINE_SPEC test 15: what the coach's response actually contains --------

RAW_PLACE = 'zqxlocation'


@override_settings(RTP_ENABLED=True)
class TestSpine15CoachNeverSeesRawValues(Tier2Base):
    def coach_page(self):
        self.client.force_login(self.coach_user)
        resp = self.client.get(f'/coach/athlete/{self.athlete.patient_id}/')
        self.assertEqual(resp.status_code, 200)
        return resp

    def test_coach_sees_allowed_fields_and_signal_but_no_raw_values(self):
        from strength_app.rtp import checkpoints, config as _c  # noqa: F401
        self.open_episode()
        av.set_base_status(self.athlete, 'restricted', actor=self.therapist)
        AvailabilityStatus.objects.filter(patient=self.athlete).update(restrictions=['no_plyo'])
        checkpoints.open_checkpoint(self.athlete, actor=self.therapist)
        self.submit(swelling_today='yes', giving_way='yes', locking_or_catching='yes',
                    tightness_0_10='7', tightness_location=RAW_PLACE)
        resp = self.coach_page()
        html = resp.content.decode()
        # allowed
        self.assertContains(resp, 'id="rtpCoachView"')
        self.assertIn('Injury signal</span> yes', html)
        self.assertIn('medical hold', html)
        self.assertIn('no_plyo', html)
        self.assertIn('Checkpoint</span> due', html)
        # forbidden: raw values and their labels, in the page and in the template context
        self.assertNotIn(RAW_PLACE, html)
        # The base page already contains some of these words in its own CSS/JS, so
        # compare with the same page rendered with RTP off: counts must not grow.
        with override_settings(RTP_ENABLED=False):
            base = self.coach_page().content.decode().lower()
        for word in ('swelling', 'giving way', 'giving_way', 'tightness', 'locking', 'catching'):
            self.assertEqual(html.lower().count(word), base.count(word), word)
        block = html[html.index('id="rtpCoachView"'):].split('</div>')[0].lower()
        for word in ('swelling', 'giving', 'tightness', 'locking', 'catching'):
            self.assertNotIn(word, block, word)
        self.assertEqual(set(resp.context['rtp_coach']),
                         {'traffic_light', 'status', 'restrictions', 'stage_name',
                          'checkpoint', 'injury_signal'})

    def test_signal_no_when_answers_are_no(self):
        self.open_episode()
        self.submit(swelling_today='no', giving_way='no', locking_or_catching='no', tightness_0_10='9')
        html = self.coach_page().content.decode()
        self.assertIn('Injury signal</span> no', html)
        block = html[html.index('id="rtpCoachView"'):].split('</div>')[0].lower()
        self.assertNotIn('tightness', block)

    def test_signal_yes_when_comparator_says_worse(self):
        """Worse verdict: injury signal shows AND (Tier 3 S11, Pawan's ruling) the athlete is held."""
        self.open_episode()
        self.submit(tightness_0_10='2', swelling_today='no')
        self.submit(tightness_0_10='6', swelling_today='no')
        self.assertTrue(av.is_held(self.athlete))  # Tier 3 S11: worse now holds (was signal only)
        self.assertIn('Injury signal</span> yes', self.coach_page().content.decode())

    def test_flag_off_or_no_episode_adds_nothing(self):
        self.assertNotContains(self.coach_page(), 'rtpCoachView')
        self.open_episode()
        with override_settings(RTP_ENABLED=False):
            self.assertNotContains(self.coach_page(), 'rtpCoachView')
