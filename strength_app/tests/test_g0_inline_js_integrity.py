"""
G0 — inline-JS integrity harness.

One unescaped value entering an inline <script> is a SyntaxError that kills
EVERY handler declared after it on the page — the "dead buttons" class
(root cause of record, 2026-06: the Phase-A TEMPO_PARTS em-dash crash on
the camera screen, observed on a stale pre-fix server).

This suite renders every page a patient walks through in a real session —
seeded with the hostile inputs of record (tempo '—' / 'Hold', notes with
apostrophes, double quotes and a literal </script>) — extracts every inline
<script> block exactly the way a browser tokenizer would (content ends at
the first literal '</script>'), and runs `node --check` on each. Any
syntax error fails the test with the page URL and the offending line.

Walks covered:
  * managed patient (therapist session): today → start → exercise idx 0..4
    (camera AND guided screens occur naturally) → feedback idx 0..4 →
    complete → finished → pain-stop page
  * self-serve patient: dashboard, session overview, first execute page
  * coach: squad + athlete detail
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from strength_app.models import (
    CoachPatientLink,
    PatientProfile,
    StrengthProfile,
    TherapistProfile,
)
from therapist_app.models import PrescriptionItem


NODE = shutil.which('node')

# Mirrors the browser: an inline script's content ends at the FIRST literal
# '</script>' regardless of JS string/comment context, so an unescaped
# '</script>' inside a value truncates the block here exactly as it would
# in the real page.
_SCRIPT_RE = re.compile(r'<script\b([^>]*)>(.*?)</script\s*>',
                        re.IGNORECASE | re.DOTALL)
_SRC_RE = re.compile(r'\bsrc\s*=', re.IGNORECASE)
_TYPE_RE = re.compile(r'''\btype\s*=\s*["']?([^"'\s>]+)''', re.IGNORECASE)
_JS_TYPES = {'text/javascript', 'application/javascript', 'module'}


def _iter_inline_scripts(html):
    """Yield the body of every inline (no-src, JS-typed) <script> block."""
    for attrs, body in _SCRIPT_RE.findall(html):
        if _SRC_RE.search(attrs):
            continue
        type_match = _TYPE_RE.search(attrs)
        if type_match and type_match.group(1).lower() not in _JS_TYPES:
            continue  # JSON payloads / templates, not executed as JS
        if body.strip():
            yield body


def _node_check(body, workdir, name):
    """Return None if the script parses, else a failure detail string.

    Checks the bare block first; wraps in (function(){...}) only if needed
    (node's CJS parse is slightly laxer than a browser classic script, so
    the wrap almost never fires — kept per spec for safety).
    """
    def run(source, suffix):
        path = Path(workdir) / f'{name}{suffix}.js'
        path.write_text(source, encoding='utf-8')
        proc = subprocess.run(
            [NODE, '--check', str(path)],
            capture_output=True, text=True, timeout=30,
        )
        return proc

    proc = run(body, '')
    if proc.returncode == 0:
        return None
    wrapped = run('(function(){\n' + body + '\n})', '_wrapped')
    if wrapped.returncode == 0:
        return None

    # node stderr: "<path>:<line>\n<source line>\n ...\nSyntaxError: ..."
    stderr = proc.stderr.strip()
    line_match = re.search(r'\.js:(\d+)', stderr)
    offending = ''
    if line_match:
        lineno = int(line_match.group(1))
        lines = body.splitlines()
        if 0 < lineno <= len(lines):
            offending = f'\n  offending line {lineno}: {lines[lineno - 1].strip()}'
    error_match = re.search(r'^(SyntaxError:.*)$', stderr, re.MULTILINE)
    summary = error_match.group(1) if error_match else stderr.splitlines()[-1]
    return f'{summary}{offending}'


class InlineJSAuditMixin:
    """Shared page-audit plumbing for the three walks below."""

    def setUp(self):
        super().setUp()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._scripts_checked = 0
        self._failures = []

    def audit_page(self, url, label=None):
        """GET `url`, assert it renders, and node-check every inline script."""
        label = label or url
        resp = self.client.get(url, follow=True)
        self.assertEqual(
            resp.status_code, 200,
            f'{label}: expected 200, got {resp.status_code}',
        )
        html = resp.content.decode('utf-8')
        for i, body in enumerate(_iter_inline_scripts(html)):
            self._scripts_checked += 1
            slug = re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')
            detail = _node_check(body, self._tmpdir.name, f'{slug}_{i}')
            if detail:
                self._failures.append(f'{label} (script #{i}): {detail}')
        return resp

    def assert_all_js_clean(self, min_scripts):
        self.assertGreaterEqual(
            self._scripts_checked, min_scripts,
            'harness self-check: fewer inline scripts found than expected — '
            'the extraction regex or the walk is broken, not the templates',
        )
        self.assertEqual(
            self._failures, [],
            'Inline JS syntax errors (dead-buttons class):\n'
            + '\n'.join(self._failures),
        )


@unittest.skipUnless(NODE, 'node is required for inline-JS syntax checking')
class TestG0ManagedPatientSessionJS(InlineJSAuditMixin, TestCase):
    """Walk Anika's full therapist-managed session with hostile fixtures."""

    def setUp(self):
        super().setUp()
        # The login rate limiter counts POSTs per IP in the process-wide
        # test cache — clear it so suite-order can't 429 our login.
        cache.clear()
        call_command('seed_therapist_demo', stdout=StringIO())
        # Sharpen the seeded notes into the hostile inputs of record:
        # apostrophe + '>', double quotes, and a literal </script>.
        items = list(PrescriptionItem.objects.order_by('order'))
        items[0].notes = "Don't rush. Stop if pain >3."
        items[0].save(update_fields=['notes'])
        items[1].notes = 'Both sides — go "slow". </script><script>alert(1)'
        items[1].save(update_fields=['notes'])

        resp = self.client.post(
            reverse('patient_login'),
            {'phone': '9000000001', 'password': 'patient'},
        )
        self.assertEqual(resp.status_code, 302, 'patient login failed')

    def test_g0_full_session_walk_inline_js_parses(self):
        templates_seen = set()

        self.audit_page(reverse('therapist_session_today'), 'today')

        resp = self.client.post(reverse('therapist_session_start'))
        self.assertEqual(resp.status_code, 302, 'session start failed')

        for idx in range(5):
            resp = self.audit_page(
                reverse('therapist_session_exercise', args=[idx]),
                f'exercise idx {idx}',
            )
            templates_seen.update(t.name for t in resp.templates if t.name)
            self.audit_page(
                reverse('therapist_session_feedback', args=[idx]),
                f'feedback idx {idx}',
            )

        # The seed protocol must exercise BOTH screen variants: camera
        # (glute bridge / clamshell / step-up) and guided (balance / plank).
        self.assertIn('strength_app/v1_exercise_execute.html', templates_seen,
                      'walk never hit the camera screen — coverage regressed')
        self.assertIn('strength_app/therapist_session_exercise.html',
                      templates_seen,
                      'walk never hit the guided screen — coverage regressed')

        self.audit_page(reverse('therapist_session_complete'), 'complete')
        self.audit_page(reverse('v1_pain_stop'), 'pain-stop')

        resp = self.client.post(reverse('therapist_session_complete'),
                                {'overall_pain': 2})
        self.assertEqual(resp.status_code, 302, 'session complete POST failed')
        self.audit_page(reverse('therapist_session_finished'), 'finished')

        # The camera screen alone carries several inline blocks; a low bar
        # of 10 across 14 pages just proves extraction found real scripts.
        self.assert_all_js_clean(min_scripts=10)


@unittest.skipUnless(NODE, 'node is required for inline-JS syntax checking')
class TestG0SelfServePatientJS(InlineJSAuditMixin, TestCase):
    """Self-serve (non-managed) patient: dashboard, overview, execute page."""

    def setUp(self):
        super().setUp()
        patient = PatientProfile.objects.create(
            patient_id='G0SELF1',
            name="Self O'Serve",
            phone='9000009971',
            age=30,
            goals='Strength',
            training_history='intermediate',
        )
        StrengthProfile.objects.create(
            patient=patient, assessment_number=1,
            squat_score=3, hinge_score=3, push_score=3,
            pull_score=3, core_score=3, rotate_score=3, lunge_score=3,
        )
        session = self.client.session
        session['patient_id'] = patient.patient_id
        session.save()

    def test_g0_self_serve_main_pages_inline_js_parses(self):
        self.audit_page(reverse('v1_dashboard'), 'dashboard')
        # Overview generates and stores the v1 session working sets…
        self.audit_page(reverse('v1_session_overview'), 'session overview')
        # …which the execute page needs (it redirects to overview otherwise).
        self.audit_page(reverse('v1_execute_exercise', args=[0]),
                        'execute idx 0')
        self.audit_page(reverse('v1_pain_stop'), 'pain-stop')
        self.assert_all_js_clean(min_scripts=4)


@unittest.skipUnless(NODE, 'node is required for inline-JS syntax checking')
class TestG0CoachPagesJS(InlineJSAuditMixin, TestCase):
    """Coach console: squad list + athlete detail."""

    def setUp(self):
        super().setUp()
        user = User.objects.create_user('g0coach', password='g0pass123')
        coach = TherapistProfile.objects.create(
            user=user,
            therapist_id='G0COACH1',
            name='G0 Coach',
            license_number='PT-G0-001',
            specialization='Sports Physiotherapy',
            email='g0coach@example.com',
            phone='9999900098',
        )
        athlete = PatientProfile.objects.create(
            patient_id='G0ATH1',
            name="Athlete O'Hostile",
            phone='9000009972',
            age=22,
            goals='Football',
            training_history='intermediate',
            athlete_tier_eligible=True,
        )
        CoachPatientLink.objects.create(
            coach=coach, patient=athlete, is_active=True,
        )
        self.athlete = athlete
        self.client.force_login(user)

    def test_g0_coach_pages_inline_js_parses(self):
        self.audit_page(reverse('coach_squad'), 'coach squad')
        self.audit_page(
            reverse('coach_athlete_detail', args=[self.athlete.patient_id]),
            'coach athlete detail',
        )
        self.assert_all_js_clean(min_scripts=1)
