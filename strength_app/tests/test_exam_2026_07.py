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
