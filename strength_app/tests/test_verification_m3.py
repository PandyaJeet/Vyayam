"""
MODULE 3 VERIFICATION — Patient session engine: pain pipeline, alert dedup,
R1 capture endpoints.

TEST-ONLY. Zero application-code changes. Each test proves the CURRENT behavior
of the codebase. Where a scenario exposes a gap it is asserted and commented,
never fixed.

Placement: strength_app/tests/ — the session engine lives in strength_app, and
strength_app tests live under strength_app/tests/ (Modules 1-2 covered the
therapist_app console, so those files sit at therapist_app root; this module's
subject is strength_app, so it belongs here).

No overlap with Module 1 (models/auth) or Module 2 (therapist console builder).
Subject here: strength_app/v1_therapist_session_views.py.

Clinical settings (confirmed live): PAIN_STOP_THRESHOLD_DEFAULT=5,
PAIN_SESSION_PAUSE_THRESHOLD=8.
"""

import json
from unittest import mock

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from strength_app.models import PainEvent, PatientProfile
from strength_app.v1_therapist_session_views import _sanitize_reps
from therapist_app.models import (
    Alert,
    ExerciseSetLog,
    Prescription,
    PrescriptionItem,
    SessionLog,
    SessionLogItem,
    Therapist,
    TherapistMessage,
    TherapistPatientLink,
)

VALID_ID = 'ex_bw_squat'
VALID_NAME = 'Bodyweight Squat'


class M3SessionBase(TestCase):
    """Builds a therapist-managed patient with an active link and drives the
    session endpoints via session state (patient auth is session-based on
    patient_id, not Django login)."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.tuser = User.objects.create_user('dr_m3', password='pass')
        self.therapist = Therapist.objects.create(user=self.tuser, full_name='Dr. M3')
        self.puser = User.objects.create_user('pt_m3', password='x')
        self.link = TherapistPatientLink.objects.create(
            therapist=self.therapist, patient=self.puser,
            status='active', accepted_at=timezone.now())
        self.patient = PatientProfile.objects.create(
            patient_id='M3P', name='Pat Ent', phone='9300000001', age=30,
            goals='rehab', user=self.puser, therapist_managed=True,
            password=make_password('x'))

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def publish(self, *, threshold=5, with_log=False, rx_id_override=None):
        """Publish a one-item prescription and prime the session state."""
        rx = Prescription.objects.create(
            link=self.link, week_number=1, published_at=timezone.now())
        PrescriptionItem.objects.create(
            prescription=rx, order=0, exercise_id=VALID_ID,
            exercise_name=VALID_NAME, pain_stop_threshold=threshold)
        state = {'rx_id': rx_id_override if rx_id_override is not None else rx.id}
        log = None
        if with_log:
            log = SessionLog.objects.create(link=self.link, prescription=rx)
            state['log_id'] = log.id
        session = self.client.session
        session['patient_id'] = self.patient.patient_id
        session['therapist_session'] = state
        session.save()
        return rx, log

    def report(self, idx=0, **body):
        return self.client.post(
            reverse('therapist_session_report_pain', args=[idx]),
            data=json.dumps(body), content_type='application/json')

    def set_log(self, idx=0, **body):
        return self.client.post(
            reverse('therapist_session_set_log', args=[idx]),
            data=json.dumps(body), content_type='application/json')


# ===========================================================================
# F — FUNCTIONAL / CLINICAL CORRECTNESS
# ===========================================================================

class F1TwoTierBoundaries(M3SessionBase):
    """F1 — outcome branching at exact boundaries with a normal threshold=5.
    severity>=8 → pause; severity>threshold → skip; else continue."""

    def test_f1_boundaries_5_6_7_8(self):
        self.publish(threshold=5)
        cases = [(5, 'continue'), (6, 'skip'), (7, 'skip'), (8, 'pause')]
        for severity, expected in cases:
            resp = self.report(severity=severity)
            self.assertEqual(resp.status_code, 200, f'sev={severity}')
            self.assertEqual(resp.json()['action'], expected,
                             f'severity={severity} expected {expected}')


class F2ExplicitZeroThreshold(M3SessionBase):
    """F2 — D2 bug class at the ORIGINAL call site. pain_stop_threshold=0 must
    mean 'skip above ANY pain' (via `is not None`, views.py:524-525), not
    collapse to the default 5."""

    def test_f2_zero_threshold_severity_one_skips(self):
        self.publish(threshold=0)
        resp = self.report(severity=1)
        self.assertEqual(resp.json()['action'], 'skip')  # 1 > 0 → skipped
        pe = PainEvent.objects.get(patient=self.patient)
        self.assertEqual(pe.outcome, 'exercise_skipped')
        self.assertEqual(pe.threshold_applied, 0)  # the 0 was applied, not 5


class F3PainEventAlwaysRecorded(M3SessionBase):
    """F3 — PainEvent is created unconditionally (views.py:447); the
    message/alert are conditional. A 'continued' report still lands a PainEvent
    and pings no therapist."""

    def test_f3_continued_records_event_no_message(self):
        self.publish(threshold=5)
        resp = self.report(severity=2)
        self.assertEqual(resp.json()['action'], 'continue')
        pe = PainEvent.objects.get(patient=self.patient)
        self.assertEqual(pe.outcome, 'continued')
        self.assertEqual(pe.pain_severity, 2)
        self.assertEqual(TherapistMessage.objects.filter(link=self.link).count(), 0)
        self.assertEqual(Alert.objects.filter(link=self.link).count(), 0)


class F4AlertDedup(M3SessionBase):
    """F4 — dedup suppresses only the duplicate Alert row; PainEvent + system
    message are always recorded (views.py:457-471)."""

    def test_f4_two_pauses_one_alert_two_events_two_messages(self):
        self.publish(threshold=5)
        self.report(severity=8)
        self.report(severity=8)  # same exercise, within 10 min
        self.assertEqual(PainEvent.objects.filter(patient=self.patient).count(), 2)
        self.assertEqual(TherapistMessage.objects.filter(link=self.link).count(), 2)
        self.assertEqual(Alert.objects.filter(link=self.link, alert_type='pain').count(), 1)


class F5DedupBoundaryReviewed(M3SessionBase):
    """F5 — a REVIEWED alert does not suppress (dedup filter is
    is_reviewed=False, views.py:466)."""

    def test_f5_reviewed_alert_does_not_suppress_new(self):
        self.publish(threshold=5)
        self.report(severity=8)
        first = Alert.objects.get(link=self.link, alert_type='pain')
        first.is_reviewed = True
        first.save(update_fields=['is_reviewed'])
        self.report(severity=8)  # same exercise, same 10-min window
        self.assertEqual(Alert.objects.filter(link=self.link, alert_type='pain').count(), 2)


class F6SetRepClamping(M3SessionBase):
    """F6 — set_number clamps to [1,30], rep_number to [1,200]; unparseable →
    None (A1 regression, views.py:508-519). PainEvent stores clamped-or-None."""

    def _latest_pe(self):
        return PainEvent.objects.filter(patient=self.patient).latest('created_at')

    def test_f6_set_number_clamped(self):
        self.publish(threshold=5)
        self.report(severity=2, set_number=999999)
        self.assertEqual(self._latest_pe().set_number, 30)   # clamped high
        self.report(severity=2, set_number=-3)
        self.assertEqual(self._latest_pe().set_number, 1)    # clamped low
        self.report(severity=2, set_number='junk')
        self.assertIsNone(self._latest_pe().set_number)      # unparseable → None

    def test_f6_rep_number_clamped(self):
        self.publish(threshold=5)
        self.report(severity=2, rep_number=999999)
        self.assertEqual(self._latest_pe().rep_number, 200)  # clamped high
        self.report(severity=2, rep_number=-9)
        self.assertEqual(self._latest_pe().rep_number, 1)    # clamped low
        self.report(severity=2, rep_number='junk')
        self.assertIsNone(self._latest_pe().rep_number)      # unparseable → None


class F7SanitizeReps(M3SessionBase):
    """F7 — _sanitize_reps: non-list → None; malformed entries inside a valid
    list are skipped, never erroring the batch (views.py:625-669)."""

    def test_f7_unit_non_list_returns_none(self):
        self.assertIsNone(_sanitize_reps('not a list'))
        self.assertIsNone(_sanitize_reps({'rep_n': 1}))
        self.assertIsNone(_sanitize_reps(None))

    def test_f7_unit_malformed_entry_dropped_others_kept(self):
        out = _sanitize_reps([{'rep_n': 1}, 'i-am-a-string', {'rep_n': 2}, 42])
        self.assertEqual(len(out), 2)  # only the two dicts survive
        self.assertEqual([r['rep_n'] for r in out], [1, 2])

    def test_f7_endpoint_non_list_reps_does_not_crash(self):
        """Driven through set_log: a non-list reps payload is dropped to [] and
        the set is still captured (no 500)."""
        self.publish(threshold=5, with_log=True)
        resp = self.set_log(mode='guided', set_number=1, reps_count=5,
                            reps='totally-not-a-list')
        self.assertEqual(resp.status_code, 200)
        row = ExerciseSetLog.objects.get(session_log__link=self.link)
        self.assertEqual(row.reps_json, [])  # malformed array → stored empty

    def test_f7_endpoint_list_with_bad_entry_captures_good_ones(self):
        self.publish(threshold=5, with_log=True)
        resp = self.set_log(mode='camera', set_number=2, reps_count=3,
                            reps=[{'rep_n': 1, 'form_pct': 90}, 'bad',
                                  {'rep_n': 2, 'form_pct': 80}])
        self.assertEqual(resp.status_code, 200)
        row = ExerciseSetLog.objects.get(session_log__link=self.link, set_number=2)
        self.assertEqual(len(row.reps_json), 2)
        self.assertEqual([r['rep_n'] for r in row.reps_json], [1, 2])


# ===========================================================================
# S — SECURITY
# ===========================================================================

class S1ReportPainRateLimit(M3SessionBase):
    """S1 — @rate_limit(15/60, 'report_pain') (views.py:477). 16th POST in the
    window is blocked."""

    def test_s1_sixteenth_report_blocked(self):
        self.publish(threshold=5)
        for _ in range(15):
            r = self.report(severity=2)
            self.assertEqual(r.status_code, 200)
        blocked = self.report(severity=2)
        self.assertEqual(blocked.status_code, 429)


class S2StaleSessionRejected(M3SessionBase):
    """S2 — a session state whose rx_id doesn't match the active prescription →
    session_expired (400), never a write against the wrong prescription
    (views.py:492-493 / 603-605)."""

    def test_s2_report_pain_stale_rx_id_rejected(self):
        rx, _ = self.publish(threshold=5, rx_id_override=987654321)  # bogus rx_id
        resp = self.report(severity=8)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'session_expired')
        self.assertEqual(PainEvent.objects.count(), 0)

    def test_s2_set_log_stale_rx_id_rejected(self):
        # with_log makes a real SessionLog, but the rx_id in state is wrong.
        rx = Prescription.objects.create(link=self.link, week_number=1,
                                         published_at=timezone.now())
        PrescriptionItem.objects.create(prescription=rx, order=0,
                                        exercise_id=VALID_ID, exercise_name=VALID_NAME)
        log = SessionLog.objects.create(link=self.link, prescription=rx)
        session = self.client.session
        session['patient_id'] = self.patient.patient_id
        session['therapist_session'] = {'rx_id': 987654321, 'log_id': log.id}
        session.save()
        resp = self.set_log(mode='guided', set_number=1, reps_count=5)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'session_expired')
        self.assertEqual(ExerciseSetLog.objects.count(), 0)


class S3AnonymousRejected(M3SessionBase):
    """S3 — anonymous (no patient_id in session) → 401, no rows written."""

    def test_s3_anon_report_pain_401(self):
        # No publish() → no session priming → anonymous.
        resp = self.report(severity=8)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(PainEvent.objects.count(), 0)

    def test_s3_anon_set_log_401(self):
        resp = self.set_log(mode='guided', set_number=1, reps_count=5)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(ExerciseSetLog.objects.count(), 0)


class S4PayloadAbuse(M3SessionBase):
    """S4 — report_pain payload validation (views.py:503-507)."""

    def test_s4_non_numeric_severity_400(self):
        self.publish(threshold=5)
        resp = self.report(severity='abc')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'severity_required')
        self.assertEqual(PainEvent.objects.count(), 0)

    def test_s4_huge_severity_clamped_to_10(self):
        """Precise current behavior: a huge severity is CLAMPED to 10 (not
        rejected) — max(0, min(10, int(...))) — so 99999 → pause."""
        self.publish(threshold=5)
        resp = self.report(severity=99999)
        self.assertEqual(resp.json()['action'], 'pause')  # 10 >= 8
        self.assertEqual(PainEvent.objects.get(patient=self.patient).pain_severity, 10)

    def test_s4_pain_type_truncated_to_20(self):
        self.publish(threshold=5)
        self.report(severity=2, pain_type='x' * 30)
        pe = PainEvent.objects.get(patient=self.patient)
        self.assertEqual(len(pe.pain_type), 20)


class S5RecordPainAtomic(M3SessionBase):
    """S5 — _record_pain is wrapped in @transaction.atomic (views.py:423), per
    the B-T3 comment (a retry after partial failure once duplicated PainEvents).
    Confirm the wrapper AND that a mid-function failure rolls the PainEvent back."""

    def test_s5_atomic_decorator_present(self):
        import inspect
        import strength_app.v1_therapist_session_views as v
        src = inspect.getsource(v._record_pain)
        # The function object carries the atomic wrapper; its source line above
        # def _record_pain is @transaction.atomic.
        full = inspect.getsource(v)
        idx = full.index('def _record_pain(')
        self.assertIn('@transaction.atomic', full[max(0, idx - 120):idx])

    def test_s5_message_failure_rolls_back_painevent(self):
        """Force TherapistMessage.objects.create to raise on a skip-tier report;
        the PainEvent created earlier in the same _record_pain call must roll
        back (0 PainEvents), proving the atomic boundary holds."""
        self.publish(threshold=5)
        silent = Client(raise_request_exception=False)
        # carry the primed session cookie into the silent client
        silent.cookies = self.client.cookies
        with mock.patch(
            'strength_app.v1_therapist_session_views.TherapistMessage.objects.create',
            side_effect=RuntimeError('boom')
        ):
            resp = silent.post(
                reverse('therapist_session_report_pain', args=[0]),
                data=json.dumps({'severity': 6}),  # skip tier → triggers message
                content_type='application/json')
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(PainEvent.objects.count(), 0)  # rolled back with the message
