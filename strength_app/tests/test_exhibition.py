"""Exhibition pages: flag, anonymous access, nothing stored, full_squats only."""
import hashlib
import re
from pathlib import Path

from django.apps import apps
from django.test import TestCase, override_settings
from django.urls import reverse

from strength_app.models import PatientProfile, StrengthProfile

MIND_GAMES_SHA256 = '09cb359b149044accb6916f279afc68dbdd500fc0fc19c325fd7fd8e58a60468'
# SHA-256 of the <script> body of mind_games.html at 7ffa9f2: the game logic, pinned.
MIND_GAMES_SCRIPT_SHA256 = 'e01864bc76ba8b3ea851029b4b44a76e2e63cac8b0e5e4eb2d0402b63596f583'
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
        self.assertEqual(self.client.get('/exhibition/progression/').status_code, 404)

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

    def test_start_screen_has_no_video_and_demo_stage_does_not_autoplay(self):
        html = self.client.get('/exhibition/squat/').content.decode()
        start = html[html.index('id="exhStart"'):html.index('id="exhDemoStage"')]
        self.assertNotIn('<video', start)
        self.assertNotIn('exhReplay', html)
        stage = html[html.index('id="exhDemoStage"'):html.index('id="exhFail"')]
        tag = re.search(r'<video id="exhDemo"[^>]*>', stage).group(0)
        self.assertIn('muted', tag)
        self.assertIn('playsinline', tag)
        self.assertNotIn('autoplay', tag)
        self.assertNotIn('loop', tag)
        self.assertIn('videos/full_squats', stage)

    def test_failure_panel_keeps_clip_replay_and_retry(self):
        html = self.client.get('/exhibition/squat/').content.decode()
        fail = html[html.index('id="exhFail"'):html.index('id="exhCaption"')]
        self.assertRegex(fail, r'<video id="exhFailVideo" muted loop playsinline')
        self.assertIn('videos/full_squats', fail)
        self.assertRegex(fail, r'<button id="exhFailReplay"[^>]*>Show demo</button>')
        self.assertIn('id="exhRetry"', fail)

    def test_cameras_own_show_demo_stays_visible(self):
        html = self.client.get('/exhibition/squat/').content.decode()
        self.assertIn('show-demo-label', html)
        css = html[html.index('<style>'):html.index('</style>')]
        self.assertNotIn('ghostStatusCard > button', css)
        self.assertNotRegex(css, r'show-demo[^{]*\{[^}]*display\s*:\s*none')

    def test_start_handler_starts_camera_after_second_ended_and_never_showdemo(self):
        js = (STATIC_JS / 'exhibition_squat.js').read_text()
        self.assertNotIn('showDemo', js)
        self.assertIn('createSequencer(2,', js)
        self.assertIn("addEventListener('ended'", js)
        self.assertIn("act.do === 'camera'", js)
        self.assertEqual(js.count('window.startCamera()'), 1)
        # startCamera is only reached from startCameraNow, which only the sequencer calls.
        self.assertEqual(js.count('startCameraNow()'), 2)   # definition + one call
        self.assertIn('CFG.demo_line1', js)
        self.assertIn('CFG.demo_line2', js)

    def test_demo_wording_listed_in_unsigned_defaults(self):
        doc = (Path(__file__).resolve().parents[2] / 'docs' / 'UNSIGNED_DEFAULTS.md').read_text()
        from strength_app.v1_exhibition_views import SQUAT_TEXT
        self.assertIn(SQUAT_TEXT['demo_line2'], doc)

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
        # /exhibition/games/ is Pawan's own file, served unchanged (<title>Mind Games Prototype</title>).
        for url in ('/exhibition/', '/exhibition/squat/', '/exhibition/progression/'):
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

    def test_served_bytes_are_pawans_file_exactly(self):
        r = self.client.get('/exhibition/games/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(hashlib.sha256(r.content).hexdigest(), MIND_GAMES_SHA256)
        self.assertEqual(len(r.content), 22691)
        self.assertEqual(r['Content-Type'], 'text/html; charset=utf-8')

    def test_sha_check_catches_a_one_byte_change(self):
        from unittest import mock
        from strength_app import v1_exhibition_views as v
        data = bytearray(v.MIND_GAMES_FILE.read_bytes())
        data[100] ^= 1
        with mock.patch.object(Path, 'read_bytes', return_value=bytes(data)):
            r = self.client.get('/exhibition/games/')
        self.assertNotEqual(hashlib.sha256(r.content).hexdigest(), MIND_GAMES_SHA256)

    def test_missing_file_404s_only_that_page(self):
        from unittest import mock
        with mock.patch.object(Path, 'read_bytes', side_effect=FileNotFoundError):
            self.assertEqual(self.client.get('/exhibition/games/').status_code, 404)
        self.assertEqual(self.client.get('/exhibition/').status_code, 200)

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


# Every ID, class and attribute the game script queries or toggles.
MIND_GAMES_IDS = ('app', 'menu', 'play', 'res', 'bests', 'hud', 'back', 'hl', 'hr', 'cw', 'cv',
                  'bar', 'slow', 'sf', 'chk', 'rt', 'rs', 'stats', 'again', 'tomenu')
MIND_GAMES_CLASSES = ('screen', 'on', 'game', 'ab', 't', 'row', 'p', 'num', 'big')


@override_settings(EXHIBITION_MODE=True, MIND_LAB_ENABLED=False)
class ExhibitionRefreshGuardTests(TestCase):
    """Stall restyle: game logic, links and the squat style hook stay as they were."""

    def _games(self):
        return self.client.get('/exhibition/games/').content.decode()

    def test_mind_games_script_block_unchanged(self):
        body = re.search(r'<script>(.*?)</script>', self._games(), re.S).group(1)
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(), MIND_GAMES_SCRIPT_SHA256)

    def test_mind_games_keeps_script_ids(self):
        html = self._games()
        markup = html[:html.index('<script>')]
        for i in MIND_GAMES_IDS:
            self.assertEqual(markup.count('id="%s"' % i), 1, i)
        classes = set(' '.join(re.findall(r'class="([^"]*)"', markup)).split())
        for c in MIND_GAMES_CLASSES:
            self.assertIn(c, classes, c)
        self.assertIn('data-g="pass"', markup)
        self.assertIn('data-g="mem"', markup)
        self.assertIn('.screen.on{display:flex}', markup)
        self.assertIn('.stat{', markup)   # rows the script builds on the results screen
        self.assertIn('<title>Mind Games Prototype</title>', markup)

    def test_every_exhibition_subpage_links_back_to_index(self):
        for url in ('/exhibition/squat/', '/exhibition/games/', '/exhibition/progression/'):
            self.assertContains(self.client.get(url), 'href="/exhibition/"', msg_prefix=url)

    def test_index_links_exact(self):
        html = self.client.get('/exhibition/').content.decode()
        links = re.findall(r'<a class="big" href="([^"]+)">([^<]+)</a>', html)
        self.assertEqual(links, [
            (reverse('exhibition_squat'), 'Try the squat coach'),
            (reverse('exhibition_games'), 'Play the demo games'),
            (reverse('exhibition_progression'), 'See how a plan changes'),
        ])
        self.assertIn('id="exhibitionLinks"', html)
        self.assertNotIn('leadQr', html)
        self.assertNotIn('Lead form QR', html)

    def test_squat_hook_is_scoped(self):
        squat = self.client.get('/exhibition/squat/').content.decode()
        self.assertIn('exh-squat', re.search(r'<body[^>]*>', squat).group(0))
        src = (Path(__file__).resolve().parents[1] / 'templates' / 'strength_app'
               / 'exhibition_squat.html').read_text()
        self.assertNotIn('refresh_css', src)
        self.assertNotIn('vy_refresh', src)
        self.assertNotIn('vy_refresh', squat)
        # Every rule the wrapper adds after the camera layout block is scoped to body.exh-squat.
        tail = src[src.index('/* Stall restyle'):src.index('</style>')]
        tail = re.sub(r'/\*.*?\*/', '', tail, flags=re.S)
        rules = [s.strip() for s in re.findall(r'([^{}]+)\{', tail)]
        self.assertTrue(rules)
        for sel in rules:
            if sel.startswith('@media'):
                continue
            for part in re.sub(r'\([^()]*\)', '()', sel).split(','):
                self.assertTrue(part.strip().startswith('body.exh-squat'), sel)
        patient = _patient_execute_html(self.client)
        self.assertNotIn('exh-squat', patient)
        self.assertNotIn('exh-', patient)

    def test_squat_overlays_take_covered_controls_out_of_tab_order(self):
        # The CSS keys on the inline display values the wrapper scripts write; keep them in step.
        src = (Path(__file__).resolve().parents[1] / 'templates' / 'strength_app'
               / 'exhibition_squat.html').read_text()
        for rule in ('body.exh-squat:has(#exhStart:not([style*="none"])) .ex-wrap',
                     'body.exh-squat:has(#exhDemoStage[style*="flex"]) .ex-wrap',
                     'body.exh-squat:has(#exhFail[style*="flex"]) .ex-wrap { visibility: hidden; }',
                     'body.exh-squat:has(#exhCaption[style*="block"]) #voiceToggle { visibility: hidden; }',
                     'body.exh-squat .exh-header a:focus-visible { outline-offset: -7px; }',
                     'body.exh-squat #exhDemoStage, body.exh-squat #exhCaption { top: 40px; }'):
            self.assertIn(rule, src)
        self.assertIn("el.style.display = 'block'", src)   # caption shown
        js = (STATIC_JS / 'exhibition_squat.js').read_text()
        for needle in ("$('exhStart').style.display = 'none'", "$('exhDemoStage').style.display = 'flex'",
                       "$('exhDemoStage').style.display = 'none'", "$('exhFail').style.display = 'flex'"):
            self.assertIn(needle, js)


def _patient_execute_html(client):
    patient = PatientProfile.objects.create(
        patient_id='EXHP2', name='Exh Patient', phone='9000009982', age=30,
        goals='Strength', training_history='intermediate')
    StrengthProfile.objects.create(
        patient=patient, assessment_number=1, squat_score=3, hinge_score=3,
        push_score=3, pull_score=3, core_score=3, rotate_score=3, lunge_score=3)
    s = client.session
    s['patient_id'] = patient.patient_id
    s.save()
    client.get(reverse('v1_session_overview'))  # stores the session
    r = client.get(reverse('v1_execute_exercise', args=[0]))
    assert r.status_code == 200, r.status_code
    return r.content.decode()
