"""
MODULE 5 VERIFICATION — Reports & PDF export.

TEST-ONLY. Zero application-code changes. Each test proves the CURRENT behavior
of the codebase. Where a scenario exposes a gap it is asserted and commented,
never fixed.

Subjects (all in strength_app except one therapist view):
  strength_app/report_builder.py  — build_report, generate_session_report, tempo_adherence
  strength_app/report_pdf.py       — generate_report_pdf, pdf_filename
  strength_app/v1_therapist_session_views.py — therapist_session_report_pdf (patient side)
  therapist_app/views.py           — session_report_pdf (therapist side)

Placement: strength_app/tests/ — the report engine lives here (M1/M2 console tests
live at therapist_app root; this module's bulk is strength_app).

Base: local HEAD == origin/main at 59d32ee (m4). The prompt mentioned 4 new
athlete/football commits on main; they are NOT present in this workspace — the
required check (local == origin) passes, so this runs against 59d32ee.
"""

import re
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from strength_app.models import PainEvent, PatientProfile
from strength_app.report_builder import (
    build_report,
    generate_session_report,
    tempo_adherence,
)
from strength_app.report_pdf import pdf_filename
from therapist_app.models import (
    ExerciseSetLog,
    Prescription,
    PrescriptionItem,
    SessionLog,
    SessionReport,
    Therapist,
    TherapistPatientLink,
)

VALID_ID = 'ex_bw_squat'
VALID_NAME = 'Bodyweight Squat'


class M5Base(TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.tuser = User.objects.create_user('dr_m5', password='pass')
        self.therapist = Therapist.objects.create(user=self.tuser, full_name='Dr. M5')

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def make_scenario(self, suffix, *, name='Pat Ent', completed=True,
                      with_item=True):
        """Build link + profile + prescription + SessionLog. Returns a namespace
        dict. `suffix` keeps usernames/phones/patient_ids unique per call."""
        puser = User.objects.create_user(f'pt_m5_{suffix}', password='x')
        link = TherapistPatientLink.objects.create(
            therapist=self.therapist, patient=puser,
            status='active', accepted_at=timezone.now())
        profile = PatientProfile.objects.create(
            patient_id=f'M5P{suffix}', name=name, phone=f'93000{suffix:0>5}',
            age=30, goals='rehab', user=puser, therapist_managed=True)
        rx = Prescription.objects.create(
            link=link, week_number=1, published_at=timezone.now())
        item = None
        if with_item:
            item = PrescriptionItem.objects.create(
                prescription=rx, order=0, exercise_id=VALID_ID,
                exercise_name=VALID_NAME, sets=3, reps=10, tempo='3-1-2-0')
        slog = SessionLog.objects.create(link=link, prescription=rx)
        if completed:
            slog.completed_at = slog.started_at + timedelta(seconds=300)
            slog.save(update_fields=['completed_at'])
        return {'puser': puser, 'link': link, 'profile': profile,
                'rx': rx, 'item': item, 'slog': slog}


# ===========================================================================
# F — FUNCTIONAL / REPORT-GENERATION CORRECTNESS
# ===========================================================================

class F1StatusBranches(M5Base):
    """F1 — build_report's three status branches + window_end
    (report_builder.py:667-678). window_end verified via header.duration_mmss."""

    def test_f1_complete(self):
        sc = self.make_scenario(1, completed=True)  # completed_at = start+300
        rep = build_report(sc['slog'])
        self.assertEqual(rep['header']['status'], 'complete')
        self.assertEqual(rep['header']['duration_mmss'], '5:00')  # window_end == completed_at

    def test_f1_ended_early_pain(self):
        sc = self.make_scenario(2, completed=False)
        pe = PainEvent.objects.create(
            patient=sc['profile'], exercise_id=VALID_ID, exercise_name=VALID_NAME,
            pain_type='sharp', pain_severity=9, outcome='session_paused')
        PainEvent.objects.filter(pk=pe.pk).update(
            created_at=sc['slog'].started_at + timedelta(seconds=120))
        rep = build_report(sc['slog'])
        self.assertEqual(rep['header']['status'], 'ended_early_pain')
        self.assertEqual(rep['header']['duration_mmss'], '2:00')  # first pause event time

    def test_f1_partial(self):
        sc = self.make_scenario(3, completed=False)
        # A set-log with an end time but no completion and no pause → partial.
        s = ExerciseSetLog.objects.create(
            session_log=sc['slog'], link=sc['link'], exercise_id=VALID_ID,
            exercise_name=VALID_NAME, set_number=1, mode='guided', reps_count=8)
        ExerciseSetLog.objects.filter(pk=s.pk).update(
            ended_at=sc['slog'].started_at + timedelta(seconds=180))
        rep = build_report(sc['slog'])
        self.assertEqual(rep['header']['status'], 'partial')
        self.assertEqual(rep['header']['duration_mmss'], '3:00')  # max(set ended_at, start)


class F2IdenticalBytesBothSides(M5Base):
    """F2 — therapist and patient PDF endpoints stream byte-identical documents
    from the same report_json (generate_report_pdf uses invariant=1)."""

    def test_f2_bytes_identical(self):
        sc = self.make_scenario(1)
        report = generate_session_report(sc['slog'])
        self.assertIsNotNone(report)

        # Therapist side.
        self.client.force_login(self.tuser)
        t_resp = self.client.get(
            f"/therapist/patient/{sc['link'].id}/session-reports/{report.id}/pdf/")
        self.assertEqual(t_resp.status_code, 200)

        # Patient side (session-based auth).
        pc = self.client
        pc.logout()
        session = pc.session
        session['patient_id'] = sc['profile'].patient_id
        session.save()
        p_resp = pc.get(f"/therapist-session/report/{report.id}/pdf/")
        self.assertEqual(p_resp.status_code, 200)

        self.assertTrue(t_resp.content.startswith(b'%PDF'))
        self.assertEqual(t_resp.content, p_resp.content)  # byte-identical


class F3FrozenReportJson(M5Base):
    """F3 — report_json is the frozen source. Mutating the underlying data after
    generation does NOT change the served output (generate is idempotent)."""

    def test_f3_mutation_after_generation_ignored(self):
        sc = self.make_scenario(1)
        report = generate_session_report(sc['slog'])
        original_json = report.report_json
        original_status = original_json['header']['status']

        # Mutate the underlying data: add a high-pain event for this patient.
        PainEvent.objects.create(
            patient=sc['profile'], exercise_id=VALID_ID, exercise_name=VALID_NAME,
            pain_type='sharp', pain_severity=10, outcome='session_paused')

        # Re-generate: idempotent → returns the SAME frozen snapshot.
        again = generate_session_report(sc['slog'])
        self.assertEqual(again.pk, report.pk)
        again.refresh_from_db()
        self.assertEqual(again.report_json, original_json)      # unchanged
        self.assertEqual(again.report_json['header']['status'], original_status)


class F4RegenerateSameSession(M5Base):
    """F4 — regenerating for a SessionLog that already has a report. session_log
    is OneToOne (PROTECT). ACTUAL behavior: generate_session_report is idempotent
    (filter-first, returns existing untouched) — a raw second .create() WOULD
    raise IntegrityError, which the filter-first guard avoids."""

    def test_f4_generate_is_idempotent(self):
        sc = self.make_scenario(1)
        r1 = generate_session_report(sc['slog'])
        r2 = generate_session_report(sc['slog'])
        self.assertEqual(r1.pk, r2.pk)  # same row, no second create
        self.assertEqual(SessionReport.objects.filter(session_log=sc['slog']).count(), 1)

    def test_f4_raw_second_create_raises_integrityerror(self):
        sc = self.make_scenario(2)
        generate_session_report(sc['slog'])
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                SessionReport.objects.create(
                    link=sc['link'], session_log=sc['slog'], patient=sc['profile'],
                    report_date=timezone.localtime(sc['slog'].started_at).date(),
                    status='partial', report_json={})


class F5TempoAdherenceEdges(M5Base):
    """F5 — tempo_adherence defensive edges (report_builder.py:163). No
    ZeroDivisionError / TypeError; sane None fallback when unscorable."""

    def test_f5_empty_reps(self):
        self.assertIsNone(tempo_adherence([], {'ecc': 3, 'hold': 1, 'con': 2}))

    def test_f5_prescribed_empty_zero_none(self):
        reps = [{'phase_ms': {'ecc': 3000}}]
        self.assertIsNone(tempo_adherence(reps, {}))          # empty dict
        self.assertIsNone(tempo_adherence(reps, None))        # None
        self.assertIsNone(tempo_adherence(reps, {'ecc': 0}))  # all zeros filtered out

    def test_f5_valid_case_returns_dict(self):
        # Sanity: a genuine scorable rep returns a pct dict, no error.
        out = tempo_adherence([{'phase_ms': {'ecc': 3000}}], {'ecc': 3})
        self.assertIsInstance(out, dict)
        self.assertIn('pct', out)


class F6NearEmptySession(M5Base):
    """F6 — a session with no items/sets/rests/pains still builds
    (report_builder.py:637 'a session with almost no data still builds')."""

    def test_f6_empty_prescription_builds(self):
        sc = self.make_scenario(1, completed=False, with_item=False)
        rep = build_report(sc['slog'])  # must not raise
        self.assertIsInstance(rep, dict)
        self.assertEqual(rep['exercises'], [])
        self.assertEqual(rep['header']['status'], 'partial')
        self.assertEqual(rep['header']['completion_pct'], 0)
        self.assertEqual(rep['header']['exercises_total'], 0)


# ===========================================================================
# S — SECURITY
# ===========================================================================

class S1IDOR(M5Base):
    """S1 — cross-owner report access is 404 on both sides (one case each)."""

    def test_s1_therapist_cannot_read_other_therapists_report(self):
        # Report belongs to therapist B.
        buser = User.objects.create_user('dr_m5_b', password='pass')
        therapist_b = Therapist.objects.create(user=buser, full_name='Dr. B')
        pu = User.objects.create_user('pt_m5_b', password='x')
        b_link = TherapistPatientLink.objects.create(
            therapist=therapist_b, patient=pu, status='active', accepted_at=timezone.now())
        b_profile = PatientProfile.objects.create(
            patient_id='M5B', name='Bee', phone='9300099001', age=30,
            goals='r', user=pu, therapist_managed=True)
        b_rx = Prescription.objects.create(link=b_link, week_number=1, published_at=timezone.now())
        PrescriptionItem.objects.create(prescription=b_rx, order=0, exercise_id=VALID_ID,
                                        exercise_name=VALID_NAME, sets=3, reps=10)
        b_slog = SessionLog.objects.create(link=b_link, prescription=b_rx,
                                           completed_at=timezone.now())
        b_report = generate_session_report(b_slog)

        # Therapist A (self.tuser) tries to reach B's link+report.
        self.client.force_login(self.tuser)
        resp = self.client.get(
            f"/therapist/patient/{b_link.id}/session-reports/{b_report.id}/pdf/")
        self.assertEqual(resp.status_code, 404)

    def test_s1_patient_cannot_read_other_patients_report(self):
        sc_b = self.make_scenario(2)  # patient B's report
        b_report = generate_session_report(sc_b['slog'])
        sc_a = self.make_scenario(1)  # patient A authenticated
        session = self.client.session
        session['patient_id'] = sc_a['profile'].patient_id
        session.save()
        resp = self.client.get(f"/therapist-session/report/{b_report.id}/pdf/")
        self.assertEqual(resp.status_code, 404)


class S2FilenameHeaderSafety(M5Base):
    """S2 — pdf_filename strips to isalnum() only (report_pdf.py:171), so a
    patient name with quote/newline/semicolon can never inject the
    Content-Disposition header."""

    def test_s2_pdf_filename_sanitized(self):
        # Unit: the raw sanitizer drops everything non-alnum from the first name.
        sc = self.make_scenario(1, name='Bad"\n;Name Evil')
        report = generate_session_report(sc['slog'])
        fname = pdf_filename(report)
        self.assertRegex(fname, r'^report_\d{8}_[a-z0-9]+\.pdf$')
        for bad in ('"', '\n', ';', ' '):
            self.assertNotIn(bad, fname)

    def test_s2_response_header_clean(self):
        sc = self.make_scenario(2, name='Ev"il;\nName')
        report = generate_session_report(sc['slog'])
        self.client.force_login(self.tuser)
        resp = self.client.get(
            f"/therapist/patient/{sc['link'].id}/session-reports/{report.id}/pdf/")
        self.assertEqual(resp.status_code, 200)
        cd = resp['Content-Disposition']
        # Exactly one clean filename token; no injected quote/newline.
        m = re.match(r'^attachment; filename="(report_\d{8}_[a-z0-9]+\.pdf)"$', cd)
        self.assertIsNotNone(m, f'unexpected Content-Disposition: {cd!r}')
        self.assertNotIn('\n', cd)


class S3AnonymousPDF(M5Base):
    """S3 — anonymous access to both PDF endpoints → redirect, no PDF, no trace."""

    def test_s3_anon_therapist_pdf(self):
        sc = self.make_scenario(1)
        report = generate_session_report(sc['slog'])
        resp = self.client.get(
            f"/therapist/patient/{sc['link'].id}/session-reports/{report.id}/pdf/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/therapist/login/', resp.url)
        self.assertFalse(resp.content.startswith(b'%PDF'))

    def test_s3_anon_patient_pdf(self):
        sc = self.make_scenario(2)
        report = generate_session_report(sc['slog'])
        resp = self.client.get(f"/therapist-session/report/{report.id}/pdf/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)
        self.assertFalse(resp.content.startswith(b'%PDF'))


class S4DraftStatusPDF(M5Base):
    """S4 — 'draft' is a ProgressReport status (REPORT_STATUS_CHOICES), NOT a
    SessionReport status (complete/ended_early_pain/partial). The PDF endpoints
    do not gate on status at all — even a hand-forced status='draft' SessionReport
    is served."""

    def test_s4_draft_not_a_sessionreport_status(self):
        statuses = {s for s, _ in SessionReport.STATUS_CHOICES}
        self.assertNotIn('draft', statuses)
        self.assertEqual(statuses, {'complete', 'ended_early_pain', 'partial'})

    def test_s4_pdf_served_regardless_of_status(self):
        sc = self.make_scenario(1)
        report = generate_session_report(sc['slog'])
        # Force an off-choices 'draft' status directly (choices aren't DB-enforced).
        SessionReport.objects.filter(pk=report.pk).update(status='draft')
        self.client.force_login(self.tuser)
        resp = self.client.get(
            f"/therapist/patient/{sc['link'].id}/session-reports/{report.id}/pdf/")
        self.assertEqual(resp.status_code, 200)  # no status gating
        self.assertTrue(resp.content.startswith(b'%PDF'))
