"""
2026-07 final-examination fix regression tests.

One test class per ledger finding (CODEBASE_HEALTH_2026-07.md). Every class
docstring names the finding id so the ledger and the suite stay linked.
"""

from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse

from strength_app.models import PainEvent, PatientProfile, StrengthProfile


def _make_patient(patient_id, phone, managed=False):
    return PatientProfile.objects.create(
        patient_id=patient_id,
        name='Exam Fixture',
        phone=phone,
        age=30,
        goals='Strength',
        training_history='intermediate',
        therapist_managed=managed,
        password=make_password('pw12345'),
    )


class TestA1A2NoBannedTerms(TestCase):
    """A1/A2 (S2): locked rule 2 — zero 'RSI' / 'ACWR' anywhere in content
    files or templates; templates additionally must not claim to measure
    'reactive strength' (R2-W2-1: app metrics have no force plate)."""

    def _template_files(self):
        from pathlib import Path
        import strength_app, therapist_app
        roots = [Path(strength_app.__file__).parent / 'templates',
                 Path(therapist_app.__file__).parent / 'templates']
        for root in roots:
            yield from root.rglob('*.html')

    def test_content_files_carry_no_banned_terms(self):
        from pathlib import Path
        import strength_app
        base = Path(strength_app.__file__).parent
        for fname in ('exercise_content.py', 'exercise_content_gap_fill.py'):
            text = (base / fname).read_text()
            self.assertNotRegex(text, r'\bRSI\b', f'{fname} mentions RSI')
            self.assertNotRegex(text, r'\bACWR\b', f'{fname} mentions ACWR')

    def test_templates_carry_no_banned_terms(self):
        for path in self._template_files():
            text = path.read_text()
            self.assertNotRegex(text, r'\bRSI\b', f'{path.name} mentions RSI')
            self.assertNotRegex(text, r'\bACWR\b', f'{path.name} mentions ACWR')
            self.assertNotIn('reactive strength', text.lower(),
                             f'{path.name} claims reactive strength')


class TestA4LegacyCameraFlowRetired(TestCase):
    """A4 (S2): legacy exercise_execute.html squat-scored every exercise and
    painted red for poor form. The routes must redirect, never render."""

    def _login(self, patient):
        session = self.client.session
        session['patient_id'] = patient.patient_id
        session.save()

    def test_v1_patient_routes_to_v1_flow(self):
        patient = _make_patient('A4V1', '9000009983')
        StrengthProfile.objects.create(
            patient=patient, assessment_number=1,
            squat_score=3, hinge_score=3, push_score=3,
            pull_score=3, core_score=3, rotate_score=3, lunge_score=3,
        )
        self._login(patient)
        resp = self.client.get(reverse('execute_exercise', args=[0]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('v1_execute_exercise', args=[0]))
        resp = self.client.get(reverse('daily_workout'))
        self.assertRedirects(resp, reverse('v1_session_overview'),
                             fetch_redirect_response=False)

    def test_pre_v1_patient_routes_to_onboarding(self):
        patient = _make_patient('A4LEG', '9000009984')
        self._login(patient)
        for name, args in (('execute_exercise', [0]), ('daily_workout', [])):
            resp = self.client.get(reverse(name, args=args))
            self.assertEqual(resp.status_code, 302, name)
            self.assertEqual(resp.url, reverse('onboarding_start'), name)

    def test_legacy_template_never_renders(self):
        patient = _make_patient('A4TPL', '9000009985')
        self._login(patient)
        resp = self.client.get(reverse('execute_exercise', args=[2]),
                               follow=True)
        used = {t.name for t in resp.templates if t.name}
        self.assertNotIn('strength_app/exercise_execute.html', used)


class TestA5PlyoLandingCheckLabel(TestCase):
    """A5 (S2): plyo camera exercises must be labeled landing-check, never
    generic camera form tracking (locked clinical rule)."""

    def test_plyo_camera_set_mode_label(self):
        from django.contrib.auth.models import User
        from therapist_app.models import (
            ExerciseSetLog, Prescription, PrescriptionItem, SessionLog,
            SessionLogItem, Therapist, TherapistPatientLink,
        )
        from strength_app.report_builder import build_report

        t_user = User.objects.create_user('dr_a5', password='x')
        therapist = Therapist.objects.create(user=t_user, full_name='Dr A5')
        p_user = User.objects.create_user('a5_patient', password='x')
        PatientProfile.objects.create(
            patient_id='A5PLYO', name='Plyo Patient', phone='9000009986',
            age=22, goals='Football', therapist_managed=True, user=p_user)
        link = TherapistPatientLink.objects.create(
            therapist=therapist, patient=p_user, full_name='Plyo Patient',
            email='a5@x.com', status='active')
        rx = Prescription.objects.create(link=link, week_number=1,
                                         draft_json={})
        item = PrescriptionItem.objects.create(
            prescription=rx, order=0, exercise_id='ex_plyo_tuck_jumps',
            exercise_name='Tuck Jumps', sets=1, reps=5, load='BW',
            rest_seconds=60, tempo='')
        log = SessionLog.objects.create(link=link, prescription=rx)
        SessionLogItem.objects.create(
            session_log=log, prescription_item=item, order=0,
            exercise_id='ex_plyo_tuck_jumps', exercise_name='Tuck Jumps',
            sets_completed=1)
        ExerciseSetLog.objects.create(
            session_log=log, link=link, exercise_id='ex_plyo_tuck_jumps',
            exercise_name='Tuck Jumps', set_number=1, mode='camera',
            reps_count=5, reps_json=[])

        report = build_report(log)
        block = next(e for e in report['exercises']
                     if e['exercise_id'] == 'ex_plyo_tuck_jumps')
        self.assertEqual(block['mode'], 'camera (landing checks)')


class TestBX2ReportChainProtected(TestCase):
    """B-X2 (S2): generated SessionReports are immutable — deleting any
    upstream row (Prescription, link, profile, log) must raise
    ProtectedError, never cascade."""

    def setUp(self):
        from django.contrib.auth.models import User
        from therapist_app.models import (
            Prescription, SessionLog, SessionReport, Therapist,
            TherapistPatientLink,
        )
        t_user = User.objects.create_user('dr_bx2', password='x')
        therapist = Therapist.objects.create(user=t_user, full_name='Dr BX2')
        p_user = User.objects.create_user('bx2_patient', password='x')
        self.profile = PatientProfile.objects.create(
            patient_id='BX2P', name='BX2', phone='9000009987', age=30,
            goals='Rehab', therapist_managed=True, user=p_user)
        self.link = TherapistPatientLink.objects.create(
            therapist=therapist, patient=p_user, full_name='BX2',
            email='bx2@x.com', status='active')
        self.rx = Prescription.objects.create(link=self.link, week_number=1,
                                              draft_json={})
        self.log = SessionLog.objects.create(link=self.link,
                                             prescription=self.rx)
        self.report = SessionReport.objects.create(
            link=self.link, session_log=self.log, patient=self.profile,
            report_date='2026-07-10', status='complete', report_json={})

    def test_upstream_deletes_are_blocked(self):
        from django.db.models import ProtectedError
        for obj in (self.rx, self.log, self.link, self.profile):
            with self.assertRaises(ProtectedError,
                                   msg=type(obj).__name__):
                obj.delete()

    def test_report_itself_remains_deletable_by_explicit_intent(self):
        from therapist_app.models import SessionReport
        self.report.delete()
        self.assertFalse(SessionReport.objects.exists())


class TestBX3FlashNotShadowedByChat(TestCase):
    """B-X3 (S2): the 'messages' ctx key shadowed django.contrib.messages on
    patient_detail — flashes (incl. the one-time reset temp password) were
    dropped and chat rendered as flash banners."""

    def setUp(self):
        from django.contrib.auth.models import User
        from therapist_app.models import (Therapist, TherapistMessage,
                                          TherapistPatientLink)
        self.t_user = User.objects.create_user('dr_bx3', password='x')
        Therapist.objects.create(user=self.t_user, full_name='Dr BX3')
        p_user = User.objects.create_user('bx3_patient', password='x')
        PatientProfile.objects.create(
            patient_id='BX3P', name='BX3', phone='9000009988', age=30,
            goals='Rehab', therapist_managed=True, user=p_user)
        self.link = TherapistPatientLink.objects.create(
            therapist=self.t_user.therapist, patient=p_user,
            full_name='BX3 Patient', email='bx3@x.com', status='active')
        TherapistMessage.objects.create(
            link=self.link, sender=p_user, is_system=False,
            body='Knee felt fine today')
        self.client.force_login(self.t_user)

    def test_reset_password_flash_is_visible(self):
        resp = self.client.post(
            f'/therapist/patient/{self.link.id}/reset-password/', follow=True)
        self.assertContains(resp, 'Temporary password for BX3 Patient')

    def test_chat_renders_in_messages_tab_not_as_flash(self):
        resp = self.client.get(f'/therapist/patient/{self.link.id}/?tab=messages')
        self.assertContains(resp, 'Knee felt fine today')
        self.assertIn('chat_messages', resp.context)


class TestBN1DashboardQueriesFlat(TestCase):
    """B-N1/B-N2 (S2): dashboard + patient_list card queries must be flat in
    the number of patients (was ~4/card on dashboard, ~12/link on the list)."""

    def _mk_link(self, n):
        from django.contrib.auth.models import User
        from django.utils import timezone
        from therapist_app.models import TherapistPatientLink
        from strength_app.models import WorkoutSession
        p_user = User.objects.create_user(f'bn1_p{n}', password='x')
        profile = PatientProfile.objects.create(
            patient_id=f'BN1P{n}', name=f'P{n}', phone=f'900000997{n}',
            age=30, goals='Rehab', therapist_managed=True, user=p_user)
        link = TherapistPatientLink.objects.create(
            therapist=self.therapist, patient=p_user, full_name=f'P{n}',
            email=f'bn1p{n}@x.com', status='active')
        WorkoutSession.objects.create(
            patient=profile, session_date=timezone.now(),
            total_exercises_completed=3)
        PainEvent.objects.create(patient=profile, pain_severity=6,
                                 outcome='continued')
        return link

    def setUp(self):
        from django.contrib.auth.models import User
        from therapist_app.models import Therapist
        self.t_user = User.objects.create_user('dr_bn1', password='x')
        self.therapist = Therapist.objects.create(user=self.t_user,
                                                  full_name='Dr BN1')
        self.client.force_login(self.t_user)

    def _count(self, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
        return len(ctx)

    def test_dashboard_and_list_query_counts_do_not_scale_with_patients(self):
        for n in range(2):
            self._mk_link(n)
        dash_2 = self._count('/therapist/dashboard/')
        list_2 = self._count('/therapist/patients/')
        for n in range(2, 8):
            self._mk_link(n)
        dash_8 = self._count('/therapist/dashboard/')
        list_8 = self._count('/therapist/patients/')
        self.assertEqual(
            dash_2, dash_8,
            f'dashboard queries scale with N: {dash_2} @2 vs {dash_8} @8')
        self.assertEqual(
            list_2, list_8,
            f'patient_list queries scale with N: {list_2} @2 vs {list_8} @8')


class TestBT1BT2AtomicWrites(TestCase):
    """B-T1/B-T2 (S2): multi-row session writes are single transactions — a
    mid-write failure must leave zero rows, not a partial session."""

    def test_bt1_self_serve_completion_rolls_back(self):
        from unittest import mock
        from strength_app.models import (ExerciseExecution, SessionFeedback,
                                         WorkoutSession)
        patient = _make_patient('BT1P', '9000009989')
        StrengthProfile.objects.create(
            patient=patient, assessment_number=1,
            squat_score=3, hinge_score=3, push_score=3,
            pull_score=3, core_score=3, rotate_score=3, lunge_score=3)
        session = self.client.session
        session['patient_id'] = patient.patient_id
        session['v1_session'] = {'meta': {}, 'modifiers_applied': {}}
        session['v1_exercise_results'] = [
            {'exercise_id': 'full_squats', 'exercise_name': 'Full Squats',
             'completed_sets': 3, 'prescribed_sets': 3,
             'completed_reps_per_set': [10, 10, 10]},
        ]
        session.save()

        with mock.patch.object(SessionFeedback.objects, 'create',
                               side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse('v1_post_session_feedback'), {
                    'perceived_difficulty': 'just_right',
                })
        self.assertEqual(WorkoutSession.objects.count(), 0,
                         'partial WorkoutSession survived a failed POST')
        self.assertEqual(ExerciseExecution.objects.count(), 0)

    def test_bt2_managed_session_start_rolls_back(self):
        from io import StringIO
        from unittest import mock
        from django.core.cache import cache
        from django.core.management import call_command
        from therapist_app.models import SessionLog, SessionLogItem
        cache.clear()
        call_command('seed_therapist_demo', stdout=StringIO())
        resp = self.client.post(reverse('patient_login'),
                                {'phone': '9000000001', 'password': 'patient'})
        self.assertEqual(resp.status_code, 302)

        with mock.patch.object(SessionLogItem.objects, 'create',
                               side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse('therapist_session_start'))
        self.assertEqual(SessionLog.objects.count(), 0,
                         'orphan SessionLog survived a failed start')


class TestD1AdminLoginRateLimited(TestCase):
    """D1 (S2): /admin/login/ POSTs are rate-limited like every other login
    (5 per 300s per IP)."""

    def test_sixth_post_is_throttled(self):
        from django.core.cache import cache
        cache.clear()
        for _ in range(5):
            resp = self.client.post('/admin/login/',
                                    {'username': 'x', 'password': 'y'})
            self.assertNotEqual(resp.status_code, 429)
        resp = self.client.post('/admin/login/',
                                {'username': 'x', 'password': 'y'})
        self.assertEqual(resp.status_code, 429)
        cache.clear()

    def test_get_login_form_unaffected(self):
        from django.core.cache import cache
        cache.clear()
        resp = self.client.get('/admin/login/')
        self.assertEqual(resp.status_code, 200)


class TestC1C2C3CameraTemplateFetchSafety(TestCase):
    """C1-C3 (S2): template-source guards — assessment POSTs carry the CSRF
    header; both pain-report fetch chains carry a visible-failure .catch."""

    def _template(self):
        from pathlib import Path
        import strength_app
        return (Path(strength_app.__file__).parent / 'templates' /
                'strength_app' / 'v1_exercise_execute.html').read_text()

    def test_assessment_fetches_send_csrf(self):
        text = self._template()
        blocks = text.split("fetch(\"{% url 'onboarding_save_test_result' %}\"")
        self.assertGreaterEqual(len(blocks), 3,
                                'assessment fetches went missing')
        for i, block in enumerate(blocks[1:]):
            self.assertIn("'X-CSRFToken': getCsrf()", block[:400],
                          f'assessment fetch #{i} missing CSRF header (C1)')

    def test_pain_fetch_chains_fail_visibly(self):
        text = self._template()
        self.assertEqual(text.count("We couldn't record this."), 2,
                         'both pain chains must carry the visible-failure '
                         'state (C2 managed, C3 self-serve)')


class TestBX1DeleteAccountManagedBlock(TestCase):
    """B-X1 (S1): therapist-managed patients must not be able to cascade-
    delete their clinical record (SessionReports, PainEvent/RedFlagEvent audit
    trails) via self-serve delete_account."""

    def _login(self, patient):
        session = self.client.session
        session['patient_id'] = patient.patient_id
        session.save()

    def test_managed_patient_delete_is_blocked(self):
        patient = _make_patient('BX1MGD', '9000009981', managed=True)
        PainEvent.objects.create(patient=patient, pain_severity=6,
                                 outcome='exercise_skipped')
        self._login(patient)

        resp = self.client.get(reverse('delete_account'))
        self.assertContains(resp, 'managed by your therapist')

        resp = self.client.post(reverse('delete_account'), {
            'password': 'pw12345',
            'confirm_delete': 'on',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            PatientProfile.objects.filter(patient_id='BX1MGD').exists(),
            'managed patient must NOT be deletable from self-serve')
        self.assertTrue(
            PainEvent.objects.filter(patient__patient_id='BX1MGD').exists(),
            'pain audit trail must survive')

    def test_self_serve_patient_can_still_delete(self):
        patient = _make_patient('BX1SELF', '9000009982', managed=False)
        self._login(patient)

        resp = self.client.post(reverse('delete_account'), {
            'password': 'pw12345',
            'confirm_delete': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(
            PatientProfile.objects.filter(patient_id='BX1SELF').exists(),
            'self-serve data-rights deletion must keep working')
