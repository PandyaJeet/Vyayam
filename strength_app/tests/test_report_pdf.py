"""
2026-07 burn P1 — session-report PDF export.

The PDF is a render of the immutable report_json snapshot; both endpoints
must be IDOR-safe and stream IDENTICAL bytes (both-sides-identical rule).
Content is asserted via report_pdf_sections() — the exact strings fed to
the document — because reportlab compresses page streams (the honest cheap
assertion the spec allows), plus the %PDF magic on the HTTP bytes.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from strength_app.report_builder import generate_session_report
from strength_app.report_pdf import report_pdf_sections
from strength_app.tests.test_r2_report import make_session


class TestReportPdfExport(TestCase):
    def setUp(self):
        self.log, self.profile, self.link = make_session(suffix='P1')
        self.report = generate_session_report(self.log)
        self.t_user = self.link.therapist.user

    def _login_patient(self, profile):
        session = self.client.session
        session['patient_id'] = profile.patient_id
        session.save()

    def test_patient_downloads_own_pdf(self):
        self._login_patient(self.profile)
        resp = self.client.get(
            reverse('therapist_session_report_pdf', args=[self.report.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))
        self.assertIn('attachment; filename="report_',
                      resp['Content-Disposition'])
        self.assertIn('_golden.pdf', resp['Content-Disposition'])

    def test_cross_patient_404(self):
        from strength_app.models import PatientProfile
        other = PatientProfile.objects.create(
            patient_id='PDFX1', name='Other Patient', phone='9000009941',
            age=30, goals='Rehab', therapist_managed=True)
        self._login_patient(other)
        resp = self.client.get(
            reverse('therapist_session_report_pdf', args=[self.report.id]))
        self.assertEqual(resp.status_code, 404)

    def test_therapist_linked_200_unlinked_404(self):
        self.client.force_login(self.t_user)
        resp = self.client.get(reverse(
            'therapist_session_report_pdf_dl',
            args=[self.link.id, self.report.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))

        from therapist_app.models import Therapist
        stranger = User.objects.create_user('dr_pdf_stranger', password='x')
        Therapist.objects.create(user=stranger, full_name='Dr Stranger')
        self.client.force_login(stranger)
        resp = self.client.get(reverse(
            'therapist_session_report_pdf_dl',
            args=[self.link.id, self.report.id]))
        self.assertEqual(resp.status_code, 404)

    def test_both_sides_identical_bytes(self):
        self._login_patient(self.profile)
        patient_pdf = self.client.get(reverse(
            'therapist_session_report_pdf', args=[self.report.id])).content
        self.client.force_login(self.t_user)
        therapist_pdf = self.client.get(reverse(
            'therapist_session_report_pdf_dl',
            args=[self.link.id, self.report.id])).content
        self.assertEqual(patient_pdf, therapist_pdf,
                         'patient and therapist PDFs must be identical')

    def test_pdf_content_carries_names_and_honest_labels(self):
        blob = ' '.join(
            line for _, lines in report_pdf_sections(self.report.report_json)
            for line in lines)
        self.assertIn('Glute Bridge', blob)
        self.assertIn('camera-tracked', blob)
        self.assertIn('guided (self-reported)', blob)
        self.assertIn('self-reported', blob)
        # pain events rendered verbatim from the snapshot
        self.assertIn('aching 4/10 at rep 6 of set 2', blob)
        # footer disclaimer verbatim
        self.assertIn('not a clinical assessment', blob)
        # first name only — never the full patient name in the header line
        header_lines = dict(report_pdf_sections(self.report.report_json))
        self.assertTrue(header_lines['header'][0].startswith('Golden —'))

    def test_plyo_label_passes_through_verbatim(self):
        sections = report_pdf_sections({
            'header': {'patient_name': 'Plyo Person', 'date': '10 Jul 2026'},
            'exercises': [{'name': 'Tuck Jumps',
                           'mode': 'camera (landing checks)'}],
        })
        blob = ' '.join(l for _, lines in sections for l in lines)
        self.assertIn('Tuck Jumps — camera (landing checks)', blob)
