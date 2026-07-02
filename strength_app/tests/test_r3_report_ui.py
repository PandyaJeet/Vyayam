"""
R3 — report UI tests: both audiences render the identical document from the
same include, ownership is enforced in both directions (IDOR matrix),
hostile report content renders escaped, and the new pages pass the G0
inline-JS integrity walk.
"""

import json
import unittest
from io import StringIO

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from strength_app.report_builder import generate_session_report
from strength_app.tests.test_g0_inline_js_integrity import (
    NODE,
    InlineJSAuditMixin,
)
from strength_app.tests.test_r2_report import make_session
from therapist_app.models import SessionReport


def login_as_profile(client, profile):
    session = client.session
    session['patient_id'] = profile.patient_id
    session.save()


class TestR3BothAudiencesIdentical(TestCase):
    """Locked decision 1: one report, both audiences see the identical
    document — including the rep-pinned pain line."""

    def setUp(self):
        self.log, self.profile, self.link = make_session(suffix='U1')
        self.report = generate_session_report(self.log)

    def test_patient_and_therapist_render_same_document(self):
        login_as_profile(self.client, self.profile)
        patient_resp = self.client.get(
            reverse('therapist_session_report', args=[self.report.id]))
        self.assertEqual(patient_resp.status_code, 200)
        self.assertTemplateUsed(patient_resp,
                                'strength_app/_session_report.html')

        therapist_client = self.client_class()
        therapist_client.force_login(User.objects.get(username='dr_gold_U1'))
        therapist_resp = therapist_client.get(reverse(
            'therapist_session_report_detail',
            args=[self.link.id, self.report.id]))
        self.assertEqual(therapist_resp.status_code, 200)
        self.assertTemplateUsed(therapist_resp,
                                'strength_app/_session_report.html')

        narrative = self.report.report_json['narrative']
        for resp in (patient_resp, therapist_resp):
            content = resp.content.decode('utf-8')
            self.assertIn(narrative, content)
            # The rep-pinned pain line, as the handoff words it:
            self.assertIn('aching 4/10 at rep 6 of set 2', content)
            # Both time clocks, labeled (Pawan's R2 addition):
            self.assertIn('12:00 elapsed', content)
            self.assertIn('6:00 working', content)
            # Footer disclaimer on every render (locked decision 8):
            self.assertIn('not a clinical assessment', content)

    def test_patient_entry_points_link_to_report(self):
        login_as_profile(self.client, self.profile)
        resp = self.client.get(reverse('therapist_session_progress'))
        self.assertContains(
            resp, reverse('therapist_session_report', args=[self.report.id]))


class TestR3IDORMatrix(TestCase):
    """Cross-access rows for the IDOR matrix: patient B -> patient A's
    report 404s; therapist 2 -> therapist 1's report 404s."""

    def setUp(self):
        self.log, self.profile, self.link = make_session(suffix='X1')
        self.report = generate_session_report(self.log)

    def test_other_patient_404s(self):
        _, other_profile, _ = make_session(suffix='X2')
        login_as_profile(self.client, other_profile)
        resp = self.client.get(
            reverse('therapist_session_report', args=[self.report.id]))
        self.assertEqual(resp.status_code, 404)

    def test_other_therapist_404s(self):
        _, _, other_link = make_session(suffix='X3')
        other_therapist = User.objects.get(username='dr_gold_X3')
        self.client.force_login(other_therapist)
        # Their own link id with someone else's report id -> 404 …
        resp = self.client.get(reverse(
            'therapist_session_report_detail',
            args=[other_link.id, self.report.id]))
        self.assertEqual(resp.status_code, 404)
        # … and the true owner's link id 404s at the link firewall.
        resp = self.client.get(reverse(
            'therapist_session_report_detail',
            args=[self.link.id, self.report.id]))
        self.assertEqual(resp.status_code, 404)

    def test_anonymous_redirects_to_login(self):
        resp = self.client.get(
            reverse('therapist_session_report', args=[self.report.id]))
        self.assertEqual(resp.status_code, 302)


class TestR3HostileDataRender(TestCase):
    """A report whose JSON carries script tags / quotes / em-dashes renders
    escaped on both pages — nothing report-derived executes."""

    HOSTILE = '</script><script>alert(1)</script> "quoted" — em-dash'

    def setUp(self):
        self.log, self.profile, self.link = make_session(suffix='H1')
        self.report = generate_session_report(self.log)
        data = self.report.report_json
        data['narrative'] = f'Narrative {self.HOSTILE}'
        data['messages'] = [{'time': '6:10 PM', 'body': self.HOSTILE}]
        data['review_points'] = [self.HOSTILE]
        data['exercises'][0]['name'] = f'Bridge {self.HOSTILE}'
        self.report.report_json = data
        self.report.save(update_fields=['report_json'])

    def test_hostile_content_is_escaped_on_both_pages(self):
        login_as_profile(self.client, self.profile)
        pages = [self.client.get(
            reverse('therapist_session_report', args=[self.report.id]))]
        therapist_client = self.client_class()
        therapist_client.force_login(User.objects.get(username='dr_gold_H1'))
        pages.append(therapist_client.get(reverse(
            'therapist_session_report_detail',
            args=[self.link.id, self.report.id])))
        for resp in pages:
            self.assertEqual(resp.status_code, 200)
            content = resp.content.decode('utf-8')
            self.assertNotIn('<script>alert(1)</script>', content)
            self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', content)
            self.assertIn('&quot;quoted&quot;', content)
            self.assertIn('— em-dash', content)  # em-dash is safe, kept as-is


@unittest.skipUnless(NODE, 'node is required for inline-JS syntax checking')
class TestR3ReportPagesInlineJS(InlineJSAuditMixin, TestCase):
    """G0 harness walk over the two new report pages with HOSTILE report
    content in place. Verified state of record: these pages carry ZERO
    inline scripts (both bases load JS via src= only) — the strongest form
    of the G0 guarantee for pages rendering patient-influenced content.
    The audit still runs so any future inline script gets syntax-checked;
    the zero-count is asserted so it can't silently regress unnoticed."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.log, self.profile, self.link = make_session(suffix='J1')
        self.report = generate_session_report(self.log)
        data = self.report.report_json
        data['narrative'] = 'Hostile </script><script>alert(1) — "x" \' y'
        self.report.report_json = data
        self.report.save(update_fields=['report_json'])

    def test_report_pages_inline_js_parses(self):
        login_as_profile(self.client, self.profile)
        self.audit_page(
            reverse('therapist_session_report', args=[self.report.id]),
            'patient report')
        self.client.session.flush()
        self.client.force_login(User.objects.get(username='dr_gold_J1'))
        self.audit_page(
            reverse('therapist_session_report_detail',
                    args=[self.link.id, self.report.id]),
            'therapist report')
        # No syntax failures — and no inline scripts AT ALL (see docstring):
        # escaped hostile content can never open a script context here.
        self.assertEqual(self._failures, [])
        self.assertEqual(self._scripts_checked, 0,
                         'report pages gained an inline script — it is now '
                         'auditable above, but confirm it renders NOTHING '
                         'report-derived (R3 rule)')
