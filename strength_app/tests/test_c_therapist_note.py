"""
Phase C — the therapist's per-exercise note is editable in the builder and
visible on EVERY patient surface: the today list, the guided screen, and
(the C2 gap) the camera screen, always as escaped HTML.
"""

from io import StringIO

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from therapist_app.models import PrescriptionItem


HOSTILE_NOTE = "Don't rush. Stop if pain >3."
# django.utils.html.escape renders ' as &#x27; and > as &gt;
HOSTILE_NOTE_ESCAPED = "Don&#x27;t rush. Stop if pain &gt;3."


class TestPhaseCTherapistNoteVisibility(TestCase):
    """Seeded managed patient; note set on the camera exercise (idx 0,
    glute bridge) and on the guided exercise (idx 2, single-leg balance)."""

    def setUp(self):
        # The login rate limiter counts POSTs per IP in the process-wide
        # test cache — clear it so suite-order can't 429 our login.
        cache.clear()
        call_command('seed_therapist_demo', stdout=StringIO())
        items = list(PrescriptionItem.objects.order_by('order'))
        for it in (items[0], items[2]):
            it.notes = HOSTILE_NOTE
            it.save(update_fields=['notes'])

        resp = self.client.post(
            reverse('patient_login'),
            {'phone': '9000000001', 'password': 'patient'},
        )
        self.assertEqual(resp.status_code, 302, 'patient login failed')

    def _start_session(self):
        resp = self.client.post(reverse('therapist_session_start'))
        self.assertEqual(resp.status_code, 302, 'session start failed')

    def test_note_on_today_list_escaped(self):
        resp = self.client.get(reverse('therapist_session_today'))
        self.assertContains(resp, HOSTILE_NOTE_ESCAPED)

    def test_note_on_camera_screen_escaped(self):
        # C2: idx 0 (glute bridge) renders v1_exercise_execute.html.
        self._start_session()
        resp = self.client.get(reverse('therapist_session_exercise', args=[0]))
        self.assertTemplateUsed(resp, 'strength_app/v1_exercise_execute.html')
        self.assertContains(resp, 'Therapist note:')
        self.assertContains(resp, HOSTILE_NOTE_ESCAPED)
        # And never unescaped anywhere on the page (would be a JS/HTML break risk).
        self.assertNotContains(resp, HOSTILE_NOTE)

    def test_note_on_guided_screen_escaped(self):
        self._start_session()
        resp = self.client.get(reverse('therapist_session_exercise', args=[2]))
        self.assertTemplateUsed(
            resp, 'strength_app/therapist_session_exercise.html')
        self.assertContains(resp, HOSTILE_NOTE_ESCAPED)

    def test_blank_note_renders_no_strip_on_camera_screen(self):
        # idx 1 (clamshell) keeps its seed note; blank it to prove the strip
        # disappears rather than rendering an empty amber box.
        item = PrescriptionItem.objects.order_by('order')[1]
        item.notes = ''
        item.save(update_fields=['notes'])
        self._start_session()
        resp = self.client.get(reverse('therapist_session_exercise', args=[1]))
        self.assertTemplateUsed(resp, 'strength_app/v1_exercise_execute.html')
        self.assertNotContains(resp, 'Therapist note:')


class TestPhaseCBuilderNoteInput(TestCase):
    """C1: the builder page carries exactly one notes input, anchored in the
    prescription row template."""

    def test_builder_page_contains_notes_input(self):
        call_command('seed_therapist_demo', stdout=StringIO())
        self.client.force_login(User.objects.get(username='dr_shah'))
        from therapist_app.models import TherapistPatientLink
        link = TherapistPatientLink.objects.get(
            therapist__user__username='dr_shah',
            patient__username='anika',
        )
        resp = self.client.get(
            reverse('therapist_patient_detail', args=[link.id]),
            {'tab': 'builder'})
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertEqual(content.count('data-k="notes"'), 1)
        self.assertIn('cue shown to patient', content)
