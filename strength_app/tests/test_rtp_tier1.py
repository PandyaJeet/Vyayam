"""RTP Tier 1: authority, guards, engine hold, and SPINE_SPEC tests 18, 19, 20."""

import json
from io import StringIO
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings

from strength_app.models import (
    CoachPatientLink, PatientProfile, TherapistProfile, TherapistPrescription,
)
from strength_app.rtp import availability as av
from strength_app.rtp.models import (
    AuditLog, AvailabilityStatus, CoachTherapistLink, InjuryEpisode, RehabPathway,
)
from strength_app.tests.test_mind_lab import make_athlete


def make_therapist(tag):
    user = User.objects.create_user('rtpth' + tag, password='pw123456')
    return TherapistProfile.objects.create(
        user=user, therapist_id='RTPT' + tag, name='Th ' + tag,
        license_number='L' + tag, specialization='PT',
        email=tag + '@example.com', phone='98000' + tag.zfill(5),
    )


def fb(**kw):
    base = dict(traffic_light='green', locking_or_catching=None,
                swelling_today=None, giving_way=None)
    base.update(kw)
    return SimpleNamespace(**base)


@override_settings(RTP_ENABLED=True)
class RtpBase(TestCase):
    def setUp(self):
        self.athlete, self.coach_user = make_athlete()
        self.coach = self.coach_user.therapistprofile
        self.therapist = make_therapist('1')
        self.athlete.assigned_therapist = self.therapist
        self.athlete.save()

    def denied(self, action):
        return AuditLog.objects.filter(action=action, outcome='denied').count()


class TestAuthority(RtpBase):
    def test_roles(self):
        self.assertEqual(av.resolve_role(self.therapist, self.athlete), 'therapist')
        self.assertEqual(av.resolve_role(self.coach, self.athlete), 'coach')
        self.assertIsNone(av.resolve_role(make_therapist('2'), self.athlete))

    def test_supervising_therapist_counts_as_therapist(self):
        other = make_therapist('3')
        CoachTherapistLink.objects.create(coach=self.coach, therapist=other)
        self.assertEqual(av.resolve_role(other, self.athlete), 'therapist')

    def test_coach_cannot_lift_hold_or_set_stage_and_is_audited(self):
        av.place_hold(self.athlete, actor=self.coach, role='coach')
        self.assertEqual(av.effective_status(self.athlete), 'medical hold')
        self.assertFalse(av.lift_hold(self.athlete, actor=self.coach))
        self.assertFalse(av.set_stage(self.athlete, 2, actor=self.coach))
        self.assertTrue(av.is_held(self.athlete))
        self.assertEqual(self.denied('lift_hold'), 1)
        self.assertEqual(self.denied('set_stage'), 1)

    def test_therapist_lifts_hold_and_sets_stage(self):
        av.place_hold(self.athlete, role='system')
        self.assertTrue(av.set_stage(self.athlete, 2, actor=self.therapist))
        self.assertEqual(av.effective_status(self.athlete), 'medical hold')  # hold wins
        self.assertTrue(av.lift_hold(self.athlete, actor=self.therapist))
        self.assertEqual(av.effective_status(self.athlete), 'rehab stage 2')

    def test_coach_locked_out_in_rehab_stage_and_cannot_loosen(self):
        av.set_stage(self.athlete, 1, actor=self.therapist)
        self.assertFalse(av.set_base_status(self.athlete, 'available', actor=self.coach))
        av.set_base_status(self.athlete, 'restricted', actor=self.therapist)
        self.assertFalse(av.set_base_status(self.athlete, 'available', actor=self.coach))
        self.assertTrue(av.set_base_status(self.athlete, 'restricted', actor=self.coach))

    def test_app_never_declares_fit(self):
        av.place_hold(self.athlete, role='system')
        self.assertFalse(av.set_base_status(self.athlete, 'available', actor=None, role='system'))
        self.assertFalse(av.lift_hold(self.athlete, actor=None, role='system'))
        self.assertTrue(av.is_held(self.athlete))


class TestSpine18StageNeverAutomatic(RtpBase):
    """SPINE_SPEC test 18."""

    def test_auto_actions_never_change_stage_number(self):
        av.set_stage(self.athlete, 3, actor=self.therapist)
        InjuryEpisode.objects.create(patient=self.athlete)
        av.apply_feedback_hold(self.athlete, fb(traffic_light='red', swelling_today=True))
        av.place_hold(self.athlete, role='system')
        self.assertFalse(av.set_stage(self.athlete, 4, actor=None, role='system'))
        self.assertFalse(av.set_base_status(self.athlete, 'available', actor=None, role='system'))
        row = AvailabilityStatus.objects.get(patient=self.athlete)
        self.assertEqual((row.stage_number, row.base_status), (3, 'rehab_stage'))
        self.assertTrue(row.medical_hold)


class TestSpine19SwellingGivingWay(RtpBase):
    """SPINE_SPEC test 19."""

    def test_holds_athlete_with_active_episode(self):
        InjuryEpisode.objects.create(patient=self.athlete)
        self.assertTrue(av.apply_feedback_hold(self.athlete, fb(swelling_today=True)))
        self.assertTrue(av.is_held(self.athlete))

    def test_giving_way_holds_athlete_with_active_episode(self):
        InjuryEpisode.objects.create(patient=self.athlete)
        self.assertTrue(av.apply_feedback_hold(self.athlete, fb(giving_way=True)))

    def test_never_holds_athlete_without_episode(self):
        self.assertFalse(av.apply_feedback_hold(self.athlete, fb(swelling_today=True)))
        self.assertFalse(av.apply_feedback_hold(self.athlete, fb(giving_way=True)))
        self.assertFalse(av.is_held(self.athlete))

    def test_closed_episode_does_not_count_and_null_never_holds(self):
        from django.utils import timezone
        InjuryEpisode.objects.create(patient=self.athlete, closed_at=timezone.now())
        self.assertFalse(av.apply_feedback_hold(self.athlete, fb(swelling_today=True)))
        InjuryEpisode.objects.create(patient=self.athlete)
        self.assertFalse(av.apply_feedback_hold(self.athlete, fb()))

    def test_red_and_locking_hold(self):
        self.assertTrue(av.feedback_triggers_hold(self.athlete, fb(traffic_light='red')))
        self.assertTrue(av.feedback_triggers_hold(self.athlete, fb(locking_or_catching=True)))


class TestCoachScreens(RtpBase):
    URL = '/coach/athlete/{}/override/'
    FLAG = '/coach/athlete/{}/flag/'

    def setUp(self):
        super().setUp()
        self.client.force_login(self.coach_user)

    def post_override(self, items):
        return self.client.post(self.URL.format(self.athlete.patient_id),
                                {'exercises_json': json.dumps(items)})

    def test_hold_rejects_override_service_and_ui(self):
        av.place_hold(self.athlete, role='system')
        resp = self.post_override([{'exercise_id': 'x', 'action': 'remove'}])
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(TherapistPrescription.objects.count(), 0)
        self.assertEqual(self.denied('coach_override'), 1)
        page = self.client.get(self.URL.format(self.athlete.patient_id))
        self.assertContains(page, av.LOCKED_MESSAGE)
        self.assertNotContains(page, 'name="exercises_json"')
        detail = self.client.get('/coach/athlete/{}/'.format(self.athlete.patient_id))
        self.assertContains(detail, 'Override locked')

    def test_rehab_stage_rejects_override(self):
        av.set_stage(self.athlete, 1, actor=self.therapist)
        self.assertEqual(self.post_override([]).status_code, 403)

    def test_restricted_allows_reduce_only(self):
        av.set_base_status(self.athlete, 'restricted', actor=self.therapist)
        add = self.post_override([{'exercise_id': 'squat', 'action': 'add'}])
        self.assertEqual(add.status_code, 403)
        self.assertEqual(self.denied('coach_override'), 1)
        self.assertEqual(TherapistPrescription.objects.count(), 0)
        ok = self.post_override([{'exercise_id': 'squat', 'action': 'remove'}])
        self.assertEqual(ok.status_code, 302)
        self.assertEqual(TherapistPrescription.objects.count(), 1)

    def test_flag_review_acknowledges_but_never_changes_status(self):
        av.place_hold(self.athlete, role='system')
        ok = self.client.post(self.FLAG.format(self.athlete.patient_id), {'note': 'seen'})
        self.assertEqual(ok.status_code, 200)
        bad = self.client.post(self.FLAG.format(self.athlete.patient_id),
                               {'note': 'x', 'status': 'available'})
        self.assertEqual(bad.status_code, 403)
        self.assertEqual(self.denied('flag_review'), 1)
        self.assertTrue(av.is_held(self.athlete))

    @override_settings(RTP_ENABLED=False)
    def test_flag_off_guard_is_inert(self):
        AvailabilityStatus.objects.create(patient=self.athlete, medical_hold=True)
        resp = self.post_override([{'exercise_id': 'squat', 'action': 'remove'}])
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(AuditLog.objects.count(), 0)


class TestEngineHold(RtpBase):
    """S12."""

    def test_held_athlete_gets_no_session(self):
        from strength_app.v1_prescription_engine import generate_v1_session
        av.place_hold(self.athlete, role='system')
        data = generate_v1_session(self.athlete)
        self.assertEqual(data['status'], 'stopped')
        self.assertEqual(data['working_sets'], [])

    @override_settings(RTP_ENABLED=False)
    def test_flag_off_hold_row_is_ignored(self):
        from strength_app.v1_prescription_engine import generate_v1_session
        AvailabilityStatus.objects.create(patient=self.athlete, medical_hold=True)
        self.assertNotEqual(generate_v1_session(self.athlete).get('stop_reason'),
                            __import__('strength_app.rtp.config', fromlist=['x']).ATHLETE_HOLD_TEXT)


class TestStructures(TestCase):
    def test_pathways_exist_with_no_clinical_content(self):
        self.assertEqual(set(RehabPathway.objects.values_list('key', flat=True)),
                         {'hamstring', 'ankle'})
        for p in RehabPathway.objects.all():
            self.assertEqual(p.stages.count(), 0)
            self.assertEqual(p.name, '')


class TestSpine20NoEpisodeNoHoldUnchanged(TestCase):
    """SPINE_SPEC test 20: output comparison, flag on versus flag off."""

    def setUp(self):
        call_command('seed_football_demo', stdout=StringIO())
        self.athlete = PatientProfile.objects.get(phone='9000000005')
        self.coach_user, _ = make_athlete('T20')
        self.coach_user = _
        coach = self.coach_user.therapistprofile
        CoachPatientLink.objects.create(coach=coach, patient=self.athlete, is_active=True)

    def _capture(self):
        from strength_app.v1_prescription_engine import generate_v1_session
        out = {'session': json.dumps(generate_v1_session(self.athlete),
                                     sort_keys=True, default=str)}
        self.client.logout()
        self.client.post('/login/', {'phone': '9000000005', 'password': 'athlete'})
        out['today'] = self.client.get('/athlete/today/').content.decode()
        self.client.logout()
        self.client.force_login(self.coach_user)
        pid = self.athlete.patient_id
        out['detail'] = self.client.get(f'/coach/athlete/{pid}/').content.decode()
        out['override'] = self.client.get(f'/coach/athlete/{pid}/override/').content.decode()
        return out

    def test_identical_prescription_and_screens(self):
        with override_settings(RTP_ENABLED=False):
            off = self._capture()
        with override_settings(RTP_ENABLED=True):
            on = self._capture()
        self.assertNotEqual(json.loads(off['session']).get('status'), 'stopped')
        self.assertTrue(json.loads(off['session']).get('working_sets'))
        for key in off:
            # CSRF tokens differ per render; strip them before comparing.
            import re
            strip = lambda h: re.sub(r'csrfmiddlewaretoken" value="[^"]+"', '', h)
            self.assertEqual(strip(off[key]), strip(on[key]), key)
        self.assertEqual(AuditLog.objects.count(), 0)
