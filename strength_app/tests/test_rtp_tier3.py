"""RTP Tier 3: S10 notification, S11 auto-hold on worse, S13 inbox, S14 status views.
Also extends SPINE_SPEC tests 15 (visibility) and 18 (stage never changes)."""

from django.test import TestCase, override_settings

from strength_app.rtp import availability as av, notify
from strength_app.rtp.models import AuditLog, AvailabilityStatus, CoachTherapistLink, Notification
from strength_app.tests.test_rtp_tier1 import make_therapist
from strength_app.tests.test_rtp_tier2 import Tier2Base

RAW = 'zqxlocation'


@override_settings(RTP_ENABLED=True)
class TestS10Notification(Tier2Base):
    def test_hold_notifies_assigned_therapist_once(self):
        av.place_hold(self.athlete, role=av.SYSTEM, reason='session_feedback')
        av.place_hold(self.athlete, role=av.SYSTEM, reason='session_feedback')  # already held
        rows = Notification.objects.all()
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows[0].therapist, self.therapist)
        self.assertEqual(rows[0].patient, self.athlete)
        self.assertIsNone(rows[0].read_at)

    def test_supervising_therapist_is_notified_too(self):
        other = make_therapist('3')
        CoachTherapistLink.objects.create(coach=self.coach, therapist=other)
        av.place_hold(self.athlete, role=av.SYSTEM, reason='session_feedback')
        self.assertEqual(set(Notification.objects.values_list('therapist', flat=True)),
                         {self.therapist.pk, other.pk})

    def test_coach_never_gets_a_notification(self):
        av.place_hold(self.athlete, role=av.SYSTEM, reason='session_feedback')
        self.assertFalse(Notification.objects.filter(therapist=self.coach).exists())

    def test_feedback_hold_notifies_end_to_end_and_body_has_no_raw_values(self):
        self.open_episode()
        self.submit(swelling_today='yes', giving_way='yes', locking_or_catching='yes',
                    tightness_0_10='7', tightness_location=RAW)
        body = Notification.objects.get().body.lower()
        for word in ('swelling', 'giving', 'tightness', 'locking', 'catching', RAW, '7'):
            self.assertNotIn(word, body)

    def test_notify_failure_never_undoes_the_hold(self):
        from unittest import mock
        with mock.patch.object(Notification.objects, 'create', side_effect=RuntimeError('db')):
            self.assertTrue(av.place_hold(self.athlete, role=av.SYSTEM, reason='x'))
        self.assertTrue(av.is_held(self.athlete))

    @override_settings(RTP_ENABLED=False)
    def test_flag_off_writes_nothing(self):
        av.place_hold(self.athlete, role=av.SYSTEM, reason='session_feedback')
        self.assertEqual(Notification.objects.count(), 0)

    def test_mark_read_is_therapist_only(self):
        av.place_hold(self.athlete, role=av.SYSTEM, reason='session_feedback')
        row = Notification.objects.get()
        self.assertFalse(notify.mark_read(row, actor=self.coach))
        self.assertTrue(notify.mark_read(row, actor=self.therapist))
        row.refresh_from_db()
        self.assertIsNotNone(row.read_at)


@override_settings(RTP_ENABLED=True)
class TestS11AutoHoldOnWorse(Tier2Base):
    def stage(self):
        av.set_stage(self.athlete, 2, actor=self.therapist)

    def test_worse_holds_notifies_and_keeps_stage(self):
        self.open_episode()
        self.stage()
        self.submit(tightness_0_10='2', swelling_today='no')
        self.assertFalse(av.is_held(self.athlete))
        self.submit(tightness_0_10='6', swelling_today='no')
        self.assertTrue(av.is_held(self.athlete))
        self.assertEqual(AvailabilityStatus.objects.get(patient=self.athlete).stage_number, 2)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertIn('got worse', Notification.objects.get().body)
        self.assertFalse(AuditLog.objects.filter(action='set_stage', actor_role='system').exists())

    def test_same_or_better_does_not_hold(self):
        self.open_episode()
        self.submit(tightness_0_10='6', swelling_today='no')
        self.submit(tightness_0_10='3', swelling_today='no')
        self.assertFalse(av.is_held(self.athlete))

    def test_worse_without_episode_never_holds(self):
        self.submit(pain_reported='mild', pain_severity='2')
        f = self.submit(pain_reported='mild', pain_severity='5')
        self.assertNotEqual(f.traffic_light, 'red')  # red holds everyone by S9; not what is tested
        self.assertFalse(av.is_held(self.athlete))

    @override_settings(RTP_ENABLED=False)
    def test_flag_off_never_holds(self):
        self.open_episode()
        self.submit(tightness_0_10='2')
        self.submit(tightness_0_10='9')
        self.assertFalse(av.is_held(self.athlete))

    def test_coach_cannot_lift_the_hold(self):
        self.open_episode()
        av.place_hold(self.athlete, role=av.SYSTEM, reason='worse_feedback')
        self.assertFalse(av.lift_hold(self.athlete, actor=self.coach))
        self.assertTrue(av.is_held(self.athlete))


@override_settings(RTP_ENABLED=True)
class TestS13Inbox(Tier2Base):
    def get_inbox(self, user):
        self.client.force_login(user)
        return self.client.get('/coach/inbox/')

    def setUp(self):
        super().setUp()
        from strength_app.rtp import checkpoints
        self.open_episode()
        cp = checkpoints.open_checkpoint(self.athlete, actor=self.therapist, stage_number=2)
        checkpoints.enter_measure(cp, 'hop', '150', actor=self.coach)  # pending
        self.submit(swelling_today='yes', giving_way='yes', locking_or_catching='yes',
                    tightness_0_10='7', tightness_location=RAW)

    def test_therapist_sees_notice_checkpoint_and_decision(self):
        resp = self.get_inbox(self.therapist.user)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Training paused for')
        self.assertContains(resp, '1 result to confirm')
        self.assertContains(resp, 'On hold')
        self.assertContains(resp, self.athlete.name)

    def test_coach_inbox_shows_nothing_about_the_athlete(self):
        resp = self.get_inbox(self.coach_user)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, self.athlete.name)
        self.assertContains(resp, 'No new notices.')

    def test_no_raw_values_on_the_therapist_inbox_either(self):
        html = self.get_inbox(self.therapist.user).content.decode().lower()
        block = html[html.index('id="rtpinbox"'):]
        for word in ('swelling', 'giving', 'tightness', 'locking', 'catching', RAW):
            self.assertNotIn(word, block)

    def test_mark_read_only_by_recipient(self):
        n = Notification.objects.get(therapist=self.therapist)
        self.client.force_login(self.coach_user)
        self.client.post(f'/coach/inbox/{n.id}/read/')
        n.refresh_from_db()
        self.assertIsNone(n.read_at)
        self.assertTrue(AuditLog.objects.filter(action='notify_read', outcome='denied').exists())
        self.client.force_login(self.therapist.user)
        self.client.post(f'/coach/inbox/{n.id}/read/')
        n.refresh_from_db()
        self.assertIsNotNone(n.read_at)
        self.assertContains(self.client.get('/coach/inbox/'), 'No new notices.')

    @override_settings(RTP_ENABLED=False)
    def test_flag_off_is_404(self):
        self.assertEqual(self.get_inbox(self.therapist.user).status_code, 404)

    def test_logged_out_is_redirected(self):
        self.client.logout()
        self.assertEqual(self.client.get('/coach/inbox/').status_code, 302)


@override_settings(RTP_ENABLED=True)
class TestS14CoachSquad(Tier2Base):
    """SPINE test 15, extended to the squad screen and the notice/inbox rows."""

    def squad(self, user):
        self.client.force_login(user)
        resp = self.client.get('/coach/squad/')
        self.assertEqual(resp.status_code, 200)
        return resp

    def test_squad_line_has_signal_but_no_raw_values(self):
        self.open_episode()
        self.submit(swelling_today='yes', giving_way='yes', locking_or_catching='yes',
                    tightness_0_10='7', tightness_location=RAW)
        resp = self.squad(self.coach_user)
        html = resp.content.decode()
        self.assertIn('Injury signal: yes', html)
        self.assertIn('Medical hold', html)
        self.assertNotIn(RAW, html)
        with override_settings(RTP_ENABLED=False):
            base = self.squad(self.coach_user).content.decode().lower()
        for word in ('swelling', 'giving way', 'giving_way', 'tightness', 'locking', 'catching'):
            self.assertEqual(html.lower().count(word), base.count(word), word)
        line = html[html.index('rtp-squad-line">'):].split('</div>')[0].lower()
        for word in ('swelling', 'giving', 'tightness', 'locking', 'catching'):
            self.assertNotIn(word, line)
        for a in resp.context['athletes']:
            if a['rtp_coach']:
                self.assertEqual(set(a['rtp_coach']),
                                 {'traffic_light', 'status', 'restrictions', 'stage_name',
                                  'checkpoint', 'injury_signal'})

    def test_squad_unchanged_without_episode_or_with_flag_off(self):
        self.assertNotContains(self.squad(self.coach_user), 'rtp-squad-line')
        self.open_episode()
        with override_settings(RTP_ENABLED=False):
            off = self.squad(self.coach_user)
            self.assertNotContains(off, 'rtp-squad-line')
            self.assertNotContains(off, 'rtpInboxLink')

    def test_inbox_link_shows_unread_count_for_therapist(self):
        av.place_hold(self.athlete, role=av.SYSTEM, reason='session_feedback')
        self.assertContains(self.squad(self.therapist.user), 'Inbox (1)')
