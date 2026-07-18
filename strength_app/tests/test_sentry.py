"""Phase 2 (sdlc-2026-07) — Sentry error monitoring.

Backend contract: settings import cleanly with AND without SENTRY_DSN,
and when it is unset (dev/CI) sentry_sdk is never even imported — zero
behavior change. Import is proven in a subprocess because this test
process has already imported settings.

The browser-loader / |escapejs contract lives in
test_g0_inline_js_integrity.TestG0SentryLoaderJS (rule 2 harness).
"""

import os
import subprocess
import sys
from pathlib import Path

from django.test import TestCase, override_settings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Well-formed but inert DSN (sentry_sdk validates shape at init; no
# network happens at init — transport only fires on an actual event).
DUMMY_DSN = 'https://0123456789abcdef0123456789abcdef@o0.ingest.sentry.io/0'

_PROBE = (
    "import sys, vyayam_project.settings as s; "
    "print('IMPORT_OK', bool(s.SENTRY_DSN), 'sentry_sdk' in sys.modules)"
)


def _import_settings_subprocess(sentry_dsn):
    env = {
        **os.environ,
        'DJANGO_SECRET_KEY': 'test-key',
        'DJANGO_DEBUG': 'True',
    }
    env.pop('SENTRY_DSN', None)
    if sentry_dsn:
        env['SENTRY_DSN'] = sentry_dsn
    return subprocess.run(
        [sys.executable, '-c', _PROBE],
        cwd=BASE_DIR, env=env, capture_output=True, text=True, timeout=60,
    )


class TestSettingsImportWithAndWithoutDSN(TestCase):
    def test_settings_import_clean_without_dsn_and_sdk_untouched(self):
        proc = _import_settings_subprocess(sentry_dsn=None)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # DSN falsy AND sentry_sdk never imported → zero behavior change.
        self.assertIn('IMPORT_OK False False', proc.stdout)

    def test_settings_import_clean_with_dsn(self):
        proc = _import_settings_subprocess(sentry_dsn=DUMMY_DSN)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('IMPORT_OK True True', proc.stdout)


class TestSentryContextProcessor(TestCase):
    def test_unset_dsn_reaches_templates_as_empty(self):
        from vyayam_project.context_processors import sentry
        self.assertEqual(sentry(None), {'SENTRY_DSN': ''})

    @override_settings(SENTRY_DSN=DUMMY_DSN)
    def test_set_dsn_reaches_templates(self):
        from vyayam_project.context_processors import sentry
        self.assertEqual(sentry(None), {'SENTRY_DSN': DUMMY_DSN})
