"""Exhibition pages: flag, anonymous access, nothing stored, full_squats only."""
import re
from pathlib import Path

from django.apps import apps
from django.test import TestCase, override_settings
from django.urls import reverse

from strength_app.models import PatientProfile, StrengthProfile

CSRF_INPUT = re.compile(r'name="csrfmiddlewaretoken" value="[^"]*"')


def _row_counts():
    return {m._meta.label: m.objects.count() for m in apps.get_models()
            if m._meta.managed and not m._meta.proxy}


@override_settings(EXHIBITION_MODE=False)
class ExhibitionFlagOffTests(TestCase):
    def test_urls_404(self):
        self.assertEqual(self.client.get('/exhibition/').status_code, 404)
        self.assertEqual(self.client.get('/exhibition/squat/').status_code, 404)

    def test_default_is_off(self):
        from django.conf import settings
        import os
        if 'EXHIBITION_MODE' not in os.environ:
            self.assertFalse(settings.EXHIBITION_MODE)

    def test_patient_camera_page_same_with_flag_on_and_off(self):
        patient = PatientProfile.objects.create(
            patient_id='EXHP1', name='Exh Patient', phone='9000009981', age=30,
            goals='Strength', training_history='intermediate')
        StrengthProfile.objects.create(
            patient=patient, assessment_number=1, squat_score=3, hinge_score=3,
            push_score=3, pull_score=3, core_score=3, rotate_score=3, lunge_score=3)
        s = self.client.session
        s['patient_id'] = patient.patient_id
        s.save()
        self.client.get(reverse('v1_session_overview'))  # stores the session
        url = reverse('v1_execute_exercise', args=[0])

        def page():
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200)
            # Only stripped: the per-request CSRF form value.
            return CSRF_INPUT.sub('CSRF', r.content.decode())

        off = page()
        with override_settings(EXHIBITION_MODE=True):
            on = page()
        self.assertEqual(off, on)
        self.assertIn('startCamera', off)


@override_settings(EXHIBITION_MODE=True)
class ExhibitionFlagOnTests(TestCase):
    def test_anonymous_200_no_login_redirect(self):
        for url in ('/exhibition/', '/exhibition/squat/'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
        self.assertContains(self.client.get('/exhibition/'),
                            'a training plan that progresses on its own')
        self.assertContains(self.client.get('/exhibition/'), reverse('exhibition_squat'))

    def test_visit_stores_nothing(self):
        before = _row_counts()
        self.client.get('/exhibition/')
        self.client.get('/exhibition/squat/')
        self.assertEqual(before, _row_counts())

    def test_squat_page_is_full_squats_wrapper(self):
        r = self.client.get('/exhibition/squat/')
        html = r.content.decode()
        names = [t.name for t in r.templates]
        self.assertIn('strength_app/exhibition_squat.html', names)
        self.assertIn('strength_app/v1_exercise_execute.html', names)
        self.assertIn('const EXERCISE_ID', html)
        self.assertRegex(html, r'EXERCISE_ID\s*=\s*"full_squats"')
        self.assertNotIn('QA — not patient mode', html)
        self.assertRegex(html, r'const LIBRARY_MODE = true')
        # Endpoints the template would POST to are empty (library mode skips them).
        self.assertIn('const SET_LOG_URL = ""', html)
        self.assertIn('const REST_EVENT_URL = ""', html)
        self.assertIn('const REPORT_PAIN_URL = ""', html)
        # Wrapper parts.
        for needle in ('id="exhGo"', 'id="exhCaption"', 'id="exhFail"',
                       'squat_demo.mp4', 'videos/full_squats', 'EXH_CFG = JSON.parse("'):
            self.assertIn(needle, html)
        # Wrapper-level guard against any non-GET request.
        self.assertIn('exhibition_guard.js', html)
        # The page drops the base template's pb-32 bottom padding.
        self.assertNotIn('pb-32', re.search(r'<body[^>]*>', html).group(0))

    def test_wrapper_adds_no_save_or_feedback_url(self):
        """The inherited camera script still names the save URL in code that is
        unreachable in library mode (it returns before the fetch). The wrapper
        itself must add none, and the views module must not name any."""
        html = (Path(__file__).resolve().parents[1] / 'templates' / 'strength_app'
                / 'exhibition_squat.html').read_text()
        for bad in ('{% url', 'v1_save', 'save_', 'feedback', 'POST'):
            self.assertNotIn(bad, html)
        views_src = (Path(__file__).resolve().parents[1]
                     / 'v1_exhibition_views.py').read_text()
        for bad in ('.save(', '.create(', 'objects.', 'session[', 'v1_save', 'feedback'):
            self.assertNotIn(bad, views_src)

    def test_mind_lab_routes_still_resolve_to_their_views(self):
        from django.urls import resolve
        self.assertEqual(resolve('/exhibition/mind-lab/').url_name, 'mind_lab_visitor')
        self.assertEqual(resolve('/exhibition/mind-lab/pass-window/').url_name,
                         'pass_window_visitor')

    def test_squat_hint_text_present(self):
        self.assertContains(self.client.get('/exhibition/squat/'),
                            'Prop your phone at waist height')
