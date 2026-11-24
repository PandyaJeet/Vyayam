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
        self.assertEqual(self.client.get('/exhibition/games/').status_code, 404)

    @override_settings(MIND_LAB_ENABLED=True)
    def test_games_404_even_when_mind_lab_flag_is_on(self):
        self.assertEqual(self.client.get('/exhibition/games/').status_code, 404)

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
                       'videos/full_squats', 'EXH_CFG = JSON.parse("'):
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

    def test_demo_video_is_before_start_and_outside_failure_panel(self):
        html = self.client.get('/exhibition/squat/').content.decode()
        start = html[html.index('id="exhStart"'):html.index('id="exhFail"')]
        self.assertIn('id="exhDemo"', start)
        self.assertIn('videos/full_squats', start)
        self.assertRegex(start, r'<video id="exhDemo" muted loop playsinline autoplay')
        self.assertNotIn('exhFailVideo', start)
        fail = html[html.index('id="exhFail"'):html.index('id="exhCaption"')]
        self.assertNotIn('id="exhDemo"', fail)
        self.assertIn('id="exhFailVideo"', fail)   # still there on camera failure
        self.assertIn('id="exhRetry"', fail)

    def test_replay_controls_present_and_not_hidden_by_wrapper_css(self):
        html = self.client.get('/exhibition/squat/').content.decode()
        for bid in ('exhReplay', 'exhFailReplay'):
            self.assertRegex(html, r'<button id="%s"[^>]*>Show demo</button>' % bid)
        # The camera page's own Show demo buttons stay, and no wrapper rule hides them.
        self.assertIn('show-demo-label', html)
        css = html[html.index('<style>'):html.index('</style>')]
        self.assertNotIn('ghostStatusCard > button', css)
        self.assertNotRegex(css, r'show-demo[^{]*\{[^}]*display\s*:\s*none')
        self.assertNotRegex(css, r'#exh(Fail)?Replay[^{]*\{[^}]*display\s*:\s*none')

    def test_squat_page_runs_video_mode_and_uses_only_full_squats_clip(self):
        from strength_app.cv_targets import get_video_mode_exercises
        self.assertIn('full_squats', get_video_mode_exercises())
        html = self.client.get('/exhibition/squat/').content.decode()
        self.assertNotIn('squat_demo', html)
        self.assertIn('video_mode_exercises', (Path(__file__).resolve().parents[1]
                      / 'templates' / 'strength_app' / 'v1_exercise_execute.html').read_text())

    def test_squat_hint_text_present(self):
        self.assertContains(self.client.get('/exhibition/squat/'),
                            'Prop your phone at waist height')

    def test_squat_cue_box_fits_two_full_lines_at_375x667(self):
        # Cue: font .85rem (13.6 px), line-height 1.5 (20.4 px), padding 8+8, border-box.
        css = (Path(__file__).resolve().parents[1] / 'templates' / 'strength_app'
               / 'exhibition_squat.html').read_text()
        em = float(re.search(r'#alignmentCue \{ max-height: ([\d.]+)em', css).group(1))
        two_lines = 2 * 13.6 * 1.5 + 16
        self.assertGreaterEqual(em * 13.6, two_lines)        # nothing clipped
        self.assertLess(em * 13.6, two_lines + 20.4)         # a third line stays hidden
        # Height sum: 40 + 8 + 8 + 437 + (card 138 - 44 + 8 + two_lines) <= 667.
        self.assertLessEqual(631 + (two_lines - 36.4), 667)

    def test_every_exhibition_page_title_is_listed_in_unsigned_defaults(self):
        doc = (Path(__file__).resolve().parents[2] / 'docs' / 'UNSIGNED_DEFAULTS.md').read_text()
        row = re.search(r'\| Page titles \(<title>\) \|(.*)\|', doc).group(1)
        for url in ('/exhibition/', '/exhibition/squat/', '/exhibition/games/',
                    '/exhibition/progression/'):
            html = self.client.get(url).content.decode()
            title = re.search(r'<title>(.*?)</title>', html, re.S).group(1).strip()
            self.assertIn('`%s`' % title, row, (url, title))


STATIC_JS = Path(__file__).resolve().parents[1] / 'static' / 'strength_app' / 'js'


@override_settings(EXHIBITION_MODE=True, MIND_LAB_ENABLED=False)
class ExhibitionGamesTests(TestCase):
    def test_anonymous_200_without_the_mind_lab_flag(self):
        r = self.client.get('/exhibition/games/')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('login', (r.get('Location') or '').lower())

    def test_visit_stores_nothing(self):
        before = _row_counts()
        self.client.get('/exhibition/games/')
        self.assertEqual(before, _row_counts())

    def test_page_has_both_games_and_no_save_url(self):
        import json
        r = self.client.get('/exhibition/games/')
        html = r.content.decode()
        for needle in ('id="choosePw"', 'id="chooseGn"', 'Pass Window', 'Go / No-Go Pass',
                       'Demo scenarios', 'Not a test of reaction time, ability or readiness',
                       'touch-action: manipulation', '100dvh', 'exhibition_guard.'):
            self.assertIn(needle, html)
        self.assertNotIn('{% url', html)
        for bad in ('save/', 'v1_save', 'feedback', 'sendBeacon', 'XMLHttpRequest', '<form'):
            self.assertNotIn(bad, html)
        cfg = r.context['games_cfg_json']
        pw_cfg = json.loads(cfg)['pass_window']
        self.assertIsNone(pw_cfg['save_url'])
        self.assertEqual(pw_cfg['max_s'], 50)
        self.assertGreater(len(pw_cfg['order']), 8)   # scenarios repeat until time is up
        # Own view, not the Mind Lab visitor view.
        names = [t.name for t in r.templates]
        self.assertIn('strength_app/exhibition_games.html', names)
        self.assertNotIn('strength_app/mind_lab_pass_window.html', names)

    def test_games_view_does_not_import_the_mind_lab_visitor_view(self):
        src = (Path(__file__).resolve().parents[1] / 'v1_exhibition_views.py').read_text()
        self.assertNotIn('visitor_views', src)
        self.assertNotIn('MIND_LAB_ENABLED', src)

    def test_index_links_to_games(self):
        self.assertContains(self.client.get('/exhibition/'), reverse('exhibition_games'))

    def test_new_js_has_no_network_sound_or_fullscreen(self):
        for name in ('exhibition_games.js', 'exhibition_gonogo.js'):
            src = (STATIC_JS / name).read_text()
            for bad in ('XMLHttpRequest', 'sendBeacon', 'AudioContext', 'new Audio',
                        'speechSynthesis', 'requestFullscreen', 'localStorage',
                        'sessionStorage', 'document.cookie'):
                self.assertNotIn(bad, src, name)
        games = (STATIC_JS / 'exhibition_games.js').read_text()
        self.assertNotIn('fetch(', games)
        self.assertIn('pointerdown', games)
        self.assertIn('performance.now()', games)
